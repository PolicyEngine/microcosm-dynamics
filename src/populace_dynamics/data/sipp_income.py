"""Metadata-verified SIPP income and resources on person-month records.

Invariants:

* Read only a release and concepts in the frozen, release-specific registry;
  an unknown name, code, type, or required column refuses the file.
* One input person-month produces one output row, in input order. Duplicate
  panel/person/reference-month keys refuse; no joins expand the roster.
* ``SSUID`` and other opaque identifiers stay strings. ``person_id`` uses
  panel, sample unit and person number, never wave or release, so a person
  links across months and waves within a panel.
* Carry weights and source codes unchanged, including documented missing
  codes. Never infer receipt, allocate a joint amount, annualize income,
  or redistribute household wealth to a person.
* A separate replicate-weight file must have a verified layout and unique,
  complete linkage keys before a many-to-one join can be made.

``concepts`` selects canonical column names from :func:`income_variables`;
the design/linkage core is always read. By default all concepts verified
for that release are required. An unavailable concept is an error when
requested, not an all-missing column. Consult each variable's ownership,
period, codes and exact Census label before using it: annual and year-end
items repeat on monthly rows and must not be summed across months.

The registry pins metadata only. This module performs no network access,
model fitting, holdout selection or population statistic. Staging follows
``sipp_jobs``: ``pu{year}.csv[.gz]`` in ``~/PolicyEngine/sipp-data``,
overridden by ``POPULACE_DYNAMICS_SIPP_DIR`` or an explicit path/directory.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from populace_dynamics.data.sipp_income_registry import (
    CORE_CONCEPTS,
    SippVariable,
    income_variables,
    replicate_variables,
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

    Missing sentinels belong to the domain only when Census lists them for
    this particular variable and release. A blank is distinct from an
    explicit sentinel and is accepted only for registry-verified structural
    blanks. Error messages deliberately omit record values.
    """
    text = values.astype("string")
    blank = text.isna() | text.isin(spec.structural_missing)
    storage = (
        spec.storage_type
        or {"int": "integer", "float": "float", "string": "string"}[
            spec.predicate_type
        ]
    )
    ranges = spec.domain_ranges or spec.ranges
    # Some API releases call coded numeric columns strings. A string with
    # documented ranges/positive codes still has a closed numeric domain;
    # opaque identifiers with only a missing sentinel have no such domain.
    numeric_domain = (
        storage != "string"
        or bool(ranges)
        or any(not code.startswith("-") for code, _ in spec.items)
    )
    if not numeric_domain:
        result = text.mask(blank)
        bad = blank & (not spec.allow_blank)
    else:
        allowed = {Decimal(code) for code, _ in spec.items}
        bounds = [(Decimal(low), Decimal(high)) for low, high, _ in ranges]
        is_weight = spec.period == "weight"

        def verified(token: str) -> bool:
            try:
                number = Decimal(token)
            except InvalidOperation:
                return False
            if not number.is_finite():
                return False
            if storage != "float" and not is_weight:
                if number != number.to_integral_value():
                    return False
            return number in allowed or any(
                low <= number <= high for low, high in bounds
            )

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
                dtype = (
                    "Float64" if is_weight or storage == "float" else "Int64"
                )
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


def read_sipp_income_months(
    year: int,
    *,
    path: str | Path | None = None,
    data_dir: str | Path | None = None,
    concepts: Iterable[str] | None = None,
    replicate_path: str | Path | None = None,
) -> pd.DataFrame:
    """Read selected verified concepts without changing the monthly roster.

    ``year`` is the release/interview year; ``reference_year = year - 1``.
    Output source values retain Census codes and missing sentinels. Column
    metadata in ``frame.attrs['sipp_variables']`` records their definitions.
    Separate replicate files are optional, never searched for implicitly;
    requesting one refuses unless its release-specific layout is verified.
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
