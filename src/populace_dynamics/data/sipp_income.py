"""Metadata-verified SIPP income and resources on person-month records.

Reads the pipe-delimited public-use files of the SIPP 2018-2025 releases
(reference years 2017-2024; one row per ``SSUID`` x ``PNUM`` x
``MONTHCODE``) for the concepts in
:mod:`populace_dynamics.data.sipp_income_registry`: SSI and Social
Security receipt and amounts, assets, debts and net worth with their
ownership levels, retirement accounts, pension coverage and income by
source, disability, citizenship and nativity, household roster and living
arrangement, and the design and linkage variables (panel, wave, month,
person and household keys, the monthly person weight, the variance
stratum and half sample, and the calendar-year replicate weights).

Invariants:

* Read only a release and concepts in the frozen, release-specific
  registry; an unknown name, code, type, or required column refuses the
  file before any value is used.
* A value is admitted only if every verified Census source for that
  release admits it (variable API and dictionary from 2022; the dictionary
  before), checked on its exact decimal text; missing codes count only
  where that release lists them for that variable.
* One input person-month produces one output row, in input order.
  Duplicate panel/person/reference-month keys refuse; no join expands or
  shrinks the roster.
* ``SSUID`` and other opaque identifiers stay strings. ``person_id`` is
  ``panel:SSUID:PNUM``, never wave or release, so a person links across
  months, waves and releases within a panel; ``household_id`` is
  ``panel:SSUID:ERESIDENCEID`` for the month.
* Weights and source codes are carried unchanged, documented missing codes
  included. Nothing here infers receipt, allocates a joint amount,
  annualizes income or redistributes household wealth to a person.
* A concept Census corrected by re-release (2018-2021 ``TSSSAMT``) is read
  only when ``downloaded_on`` shows the staged file postdates the fix.
* A separate replicate-weight file must have a verified layout and unique,
  complete linkage keys, and its ``REPWGT0`` must equal ``WPFINWGT``,
  before the many-to-one join is made.

``concepts`` selects canonical column names from :func:`income_variables`;
the design and linkage core is always read. By default all concepts
verified for that release are required. An unavailable concept is an
error when requested, not an all-missing column. Consult each variable's
ownership, period, universe, codes, user notes and exact Census label
before using it: annual and year-end items repeat on monthly rows and must
not be summed across months, and ``release_changes.json`` beside the
evidence lists every change in a concept between consecutive releases.

The registry pins metadata only. This module performs no network access,
model fitting, holdout selection or population statistic. Staging follows
``sipp_jobs``: ``pu{year}.csv[.gz]`` in ``~/PolicyEngine/sipp-data``,
overridden by ``POPULACE_DYNAMICS_SIPP_DIR`` or an explicit path/directory.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from populace_dynamics.data.sipp_income_registry import (
    CORE_CONCEPTS,
    SENTINEL_LABELS,
    SippVariable,
    corrected_on,
    domain_contains,
    income_variables,
    replicate_variables,
    user_notes,
)

__all__ = ["read_sipp_income_months", "validate_sipp_values"]

_KEYS = (
    "panel",
    "sample_unit_id",
    "person_number",
    "wave",
    "month",
    "household_id_at_interview",
    "monthly_address_id",
)
_PU_YEAR = re.compile(r"pu(\d{4})\.csv(?:\.gz)?$", re.I)
_RW_YEAR = re.compile(r"rw(\d{4})\.csv(?:\.gz)?$", re.I)


def validate_sipp_values(
    values: pd.Series, spec: SippVariable, *, year: int
) -> pd.Series:
    """Validate against the exact released domain; retain source codes.

    A token is admitted only if :func:`domain_contains` admits its exact
    decimal value: every verified source for the release must allow it,
    and missing codes count only where that release lists them for that
    variable. A blank is distinct from an explicit missing code and is
    accepted only for registry-verified structural blanks. Integer codes
    must be integral, and every token must be finite. Error messages omit
    record values.
    """
    text = values.astype("string")
    blank = text.isna() | text.isin(spec.structural_missing)
    storage = (
        spec.storage_type
        or {"int": "integer", "float": "float", "string": "string"}[
            spec.predicate_type
        ]
    )
    has_domain = any(
        label not in SENTINEL_LABELS for _, label in spec.items
    ) or bool(spec.ranges or spec.check_items or spec.check_ranges)
    if storage == "string" and not has_domain:
        # An opaque identifier with no documented value domain.
        result = text.mask(blank)
        bad = blank & (not spec.allow_blank)
    else:
        integral = storage != "float" and spec.period != "weight"

        def verified(token: str) -> bool:
            try:
                number = Decimal(token)
            except InvalidOperation:
                return False
            if not number.is_finite():
                return False
            if integral and number != number.to_integral_value():
                return False
            return domain_contains(spec, number)

        # Validate unique source tokens exactly before floating conversion:
        # otherwise a long decimal close to 1 can round into code 1, or an
        # amount just beyond a range edge can round back inside its domain.
        known = {token: verified(token) for token in text[~blank].unique()}
        valid = text.map(known).eq(True)
        bad = ~valid & ~(blank & spec.allow_blank)
        if not bad.any():
            if storage == "string":
                result = text.mask(blank)
            else:
                dtype = "Int64" if integral else "Float64"
                result = pd.to_numeric(
                    text.mask(blank), errors="raise"
                ).astype(dtype)
    if bad.any():
        raise ValueError(
            f"SIPP {year} {spec.name}: {int(bad.sum())} "
            "out-of-dictionary value(s); refusing unverified codes/types."
        )
    return result


def _path(
    year: int, path: str | Path | None, data_dir: str | Path | None
) -> Path:
    if path is not None:
        result = Path(path).expanduser()
    else:
        root = Path(
            data_dir
            if data_dir is not None
            else os.environ.get(
                "POPULACE_DYNAMICS_SIPP_DIR", "~/PolicyEngine/sipp-data"
            )
        ).expanduser()
        candidates = [root / f"pu{year}{ext}" for ext in (".csv", ".csv.gz")]
        result = next((p for p in candidates if p.is_file()), candidates[0])
    match = _PU_YEAR.fullmatch(result.name)
    if match and int(match.group(1)) != year:
        raise ValueError(f"SIPP {year}: path filename identifies another year")
    if not result.is_file():
        raise FileNotFoundError(
            f"No staged SIPP {year} file; stage pu{year}.csv[.gz] under "
            "~/PolicyEngine/sipp-data or POPULACE_DYNAMICS_SIPP_DIR."
        )
    return result


def _read(
    path: Path, year: int, specs: dict[str, SippVariable]
) -> pd.DataFrame:
    wanted = [spec.name for spec in specs.values()]
    try:
        raw = pd.read_csv(
            path,
            sep="|",
            usecols=wanted,
            dtype="string",
            keep_default_na=False,
            skip_blank_lines=False,
        )
    except (ValueError, pd.errors.ParserError):
        raise ValueError(
            f"SIPP {year}: missing required column(s) or invalid "
            "pipe-delimited layout for selected verified concepts."
        ) from None
    return pd.DataFrame(
        {
            concept: validate_sipp_values(raw[spec.name], spec, year=year)
            for concept, spec in specs.items()
        }
    )


def _require_keys(frame: pd.DataFrame, year: int) -> None:
    for concept in _KEYS:
        values = frame[concept]
        if (
            values.isna().any()
            or values.astype("string").isin(["-9", "-999"]).any()
        ):
            raise ValueError(f"SIPP {year}: missing structural key {concept}")
    keys = ["panel", "sample_unit_id", "person_number", "month"]
    if frame.duplicated(keys).any():
        raise ValueError(f"SIPP {year}: duplicate person-month key")


def _check_vintage(
    year: int, concepts: Iterable[str], downloaded_on: date | str | None
) -> None:
    """Refuse a concept Census corrected after the staged file's download.

    Census re-released the 2018-2021 files on 2025-07-24 with a corrected
    ``TSSSAMT`` under the same names and metadata, so only the caller can
    say which vintage is staged.
    """
    corrected = {
        concept: corrected_on(year, concept)
        for concept in concepts
        if corrected_on(year, concept) is not None
    }
    if not corrected:
        return
    if downloaded_on is None:
        raise ValueError(
            f"SIPP {year}: {sorted(corrected)} were corrected by a Census "
            "re-release; pass downloaded_on (the date the staged files "
            "were downloaded) to read them."
        )
    when = (
        date.fromisoformat(downloaded_on)
        if isinstance(downloaded_on, str)
        else downloaded_on
    )
    if not isinstance(when, date):
        raise ValueError("downloaded_on must be a date or an ISO date string")
    stale = sorted(
        concept
        for concept, fixed in corrected.items()
        if when < date.fromisoformat(fixed)
    )
    if stale:
        raise ValueError(
            f"SIPP {year}: files downloaded on {when.isoformat()} predate "
            f"Census's correction of {stale}; download the re-released "
            "files or leave these concepts out."
        )


def read_sipp_income_months(
    year: int,
    *,
    path: str | Path | None = None,
    data_dir: str | Path | None = None,
    concepts: Iterable[str] | None = None,
    replicate_path: str | Path | None = None,
    downloaded_on: date | str | None = None,
) -> pd.DataFrame:
    """Read selected verified concepts without changing the monthly roster.

    ``year`` is the release/interview year; ``reference_year = year - 1``.
    Output source values retain Census codes and missing sentinels. Column
    metadata in ``frame.attrs['sipp_variables']`` records their definitions,
    ``frame.attrs['sipp_user_notes']`` the Census user notes that name each
    variable in this release, and ``frame.attrs['sipp_corrected_on']`` any
    re-release that corrected one. ``downloaded_on`` is required to read a
    concept Census corrected by re-release (2018-2021 ``TSSSAMT``) and must
    not predate the correction. Separate replicate files are optional,
    never searched for implicitly; requesting one refuses unless its
    release-specific layout is verified.
    """
    table = income_variables(year)
    requested = tuple(table) if concepts is None else tuple(concepts)
    if isinstance(concepts, str):
        raise ValueError("concepts must be an iterable of concept names")
    if any(not isinstance(name, str) for name in requested):
        raise ValueError("concepts must contain only verified concept names")
    unknown = set(requested) - table.keys()
    if unknown:
        raise ValueError(
            f"SIPP {year}: unverified concept(s) {sorted(unknown)}"
        )
    specs = {
        key: table[key] for key in dict.fromkeys((*CORE_CONCEPTS, *requested))
    }
    _check_vintage(year, specs, downloaded_on)
    # Resolve all metadata, including requested sidecars, before opening data.
    replicate_specs = (
        replicate_variables(year) if replicate_path is not None else None
    )
    if replicate_path is not None:
        match = _RW_YEAR.fullmatch(Path(replicate_path).name)
        if match and int(match.group(1)) != year:
            raise ValueError(
                f"SIPP {year}: replicate filename identifies another year"
            )
    result = _read(_path(year, path, data_dir), year, specs)
    _require_keys(result, year)
    if replicate_specs is not None:
        result = _attach_replicates(
            result, year, replicate_path, replicate_specs
        )
        specs |= {
            name: spec
            for name, spec in replicate_specs.items()
            if name not in specs
        }
    result.insert(0, "reference_year", year - 1)
    result.insert(0, "release_year", year)
    result.insert(
        0,
        "household_id",
        result["panel"].astype("string")
        + ":"
        + result["sample_unit_id"]
        + ":"
        + result["monthly_address_id"].astype("string"),
    )
    result.insert(
        0,
        "person_id",
        result["panel"].astype("string")
        + ":"
        + result["sample_unit_id"]
        + ":"
        + result["person_number"].astype("string"),
    )
    result.attrs["sipp_variables"] = specs
    result.attrs["sipp_user_notes"] = {
        concept: notes
        for concept in specs
        if (notes := user_notes(year, concept))
    }
    result.attrs["sipp_corrected_on"] = {
        concept: fixed
        for concept in specs
        if (fixed := corrected_on(year, concept)) is not None
    }
    if replicate_specs is not None:
        result.attrs["sipp_replicate_variables"] = replicate_specs
    return result


def _attach_replicates(
    frame: pd.DataFrame,
    year: int,
    path: str | Path,
    specs: dict[str, SippVariable],
) -> pd.DataFrame:
    """Attach a verified unique sidecar without inventing or losing rows."""
    weights = _read(Path(path).expanduser(), year, specs)
    keys = [concept for concept in CORE_CONCEPTS if concept in specs]
    if not keys or weights[keys].isna().any().any():
        raise ValueError(f"SIPP {year}: missing replicate linkage keys")
    if weights.duplicated(keys).any():
        raise ValueError(f"SIPP {year}: duplicate replicate linkage keys")
    if frame.duplicated(keys).any():
        raise ValueError(f"SIPP {year}: ambiguous replicate linkage keys")
    out = frame.merge(
        weights,
        on=keys,
        how="left",
        sort=False,
        validate="many_to_one",
        indicator=True,
    )
    if not out["_merge"].eq("both").all() or len(out) != len(frame):
        raise ValueError(f"SIPP {year}: incomplete replicate linkage")
    if not out["replicate_weight_0"].eq(out["weight"]).all():
        raise ValueError(f"SIPP {year}: replicate base weight disagrees")
    return out.drop(columns="_merge")
