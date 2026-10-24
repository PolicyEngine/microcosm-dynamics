"""Metadata-verified PSID income and wealth beyond the 2005–2013 reader.

PSID use follows the project's data-access record. Income refers to the
preceding calendar year only where a registry entry says so; early raw
responses retain their reporting periods. The registry records exact
labels, inclusive columns, numeric domains, codebook pages and SHA-256
pins. No variable is inferred from its position beside another variable.

Invariants, exercised with invented records in tests/income_resources:

* Only registered waves, concepts, labels, columns and setup bytes pass.
* Every physical record produces exactly one family, in input order;
  duplicate or nonpositive interview numbers raise rather than disappear.
* Amounts retain documented top codes, losses and decimal precision.
  Documented missing codes become null; blanks and unverified codes raise.
* Each registered income identity uses its wave's components and the
  original reader's dollar tolerance. A missing component never becomes 0.
* WEALTH1 equals its wave's assets less debts; WEALTH2 adds home equity.
  Reconciliation reports exact matches separately from tolerance matches.

The existing family_income and employer_dc readers remain unchanged.
The private family_income._identity_counts and _normalized helpers are
imported deliberately to share reconciliation and label normalization.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import TextIO

import pandas as pd

from populace_dynamics.data import family_income, psid
from populace_dynamics.data.family_income import _identity_counts, _normalized
from populace_dynamics.data.psid_income_wealth_registry import REGISTRY

__all__ = [
    "INCOME_WAVES",
    "WEALTH_WAVES",
    "RECONCILIATION_TOLERANCE",
    "UnverifiedMetadataError",
    "income_variables",
    "wealth_variables",
    "wave_registry",
    "verify_setup",
    "read_family_income",
    "read_family_wealth",
    "reconcile_family_income",
    "reconcile_wealth1",
]

INCOME_WAVES = (1999, 2001, 2003, 2015, 2017, 2019, 2021, 2023)
WEALTH_WAVES = (2015, 2017, 2019, 2021, 2023)
RECONCILIATION_TOLERANCE = family_income.RECONCILIATION_TOLERANCE
_INTEGER = re.compile(r"-?\d+\Z", re.ASCII)


class UnverifiedMetadataError(ValueError):
    """A wave, concept, setup file or code has no verified interpretation."""


def wave_registry(wave: int) -> dict:
    """Return a detached copy of one wave's metadata and definitions."""

    return deepcopy(_registry(wave))


def _registry(wave: int) -> dict:
    if wave not in REGISTRY:
        raise UnverifiedMetadataError(f"Unregistered PSID wave {wave}")
    return REGISTRY[wave]


def _table(wave: int, kind: str) -> dict:
    registry = _registry(wave)
    if kind not in ("income", "wealth") or kind not in registry:
        raise UnverifiedMetadataError(
            f"No verified {kind} registry for PSID wave {wave}"
        )
    table = registry[kind]
    if kind == "wealth":
        table = {"interview": registry["income"]["interview"], **table}
    return table


def income_variables(wave: int) -> dict[str, tuple[str, str]]:
    """Return registered income concepts with exact variable IDs and labels."""

    return {
        concept: (item["variable"], item["label"])
        for concept, item in _table(wave, "income").items()
    }


def wealth_variables(wave: int) -> dict[str, tuple[str, str]]:
    """Return registered wealth concepts, including the family interview ID."""

    return {
        concept: (item["variable"], item["label"])
        for concept, item in _table(wave, "wealth").items()
    }


def verify_setup(wave: int, setup_path: str | Path) -> None:
    """Verify pinned setup bytes, every registered label and every column.

    This function reads metadata only. A pin mismatch raises before parsing
    the file and before a reader can open its record stream.
    """

    registry = _registry(wave)
    path = Path(setup_path)
    if path.suffix.lower() != ".sps":
        raise UnverifiedMetadataError("Expected a pinned SPSS setup file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != registry["setup"]["sha256"]:
        raise UnverifiedMetadataError(f"Unpinned PSID {wave} setup file")
    every = {**registry["income"], **registry.get("wealth", {})}
    signature = tuple(
        (
            concept,
            item["variable"],
            _normalized(item["label"]),
            item["start"],
            item["end"],
        )
        for concept, item in every.items()
    )
    _verify_layout(wave, str(path.resolve()), digest, signature)


@lru_cache(maxsize=32)
def _verify_layout(
    wave: int, path: str, digest: str, signature: tuple
) -> None:
    # Every call hashes the bytes first. Cached parsing is valid only for
    # those same bytes and the same expected labels and column positions.
    labels = psid.parse_sps_labels(path)
    layout = psid.parse_sps_layout(path).set_index("name")
    by_label: dict[str, list[str]] = {}
    for variable, label in labels.items():
        by_label.setdefault(_normalized(label), []).append(variable)
    for concept, variable, label, start, end in signature:
        if (
            _normalized(labels.get(variable, "")) != label
            or by_label.get(label) != [variable]
            or variable not in layout.index
        ):
            raise UnverifiedMetadataError(
                f"PSID {wave}: unverified label or variable for {concept}"
            )
        row = layout.loc[variable]
        if int(row["start"]) != start or int(row["end"]) != end:
            raise UnverifiedMetadataError(
                f"PSID {wave}: unverified columns for {concept}"
            )


def _decode_column(
    values: list[int | float], item: Mapping, concept: str
) -> pd.Series:
    decimals = item.get("decimals", 0)
    series = pd.Series(values, dtype="float64" if decimals else "int64")
    missing = series.isin(item.get("missing_codes", []))
    active = series[~missing]
    codes = item.get("allowed_codes")
    if codes is not None:
        valid = active.isin(codes)
    elif "valid_ranges" in item:
        valid = active.isin(item.get("top_codes", []))
        for lower, upper in item["valid_ranges"]:
            valid |= active.between(lower, upper)
    else:
        top_codes = item.get("top_codes", [])
        if "valid_min" not in item or "valid_max" not in item:
            raise UnverifiedMetadataError(f"No numeric domain for {concept}")
        lower = item["valid_min"]
        upper = item["valid_max"]
        if not item.get("negative", False):
            lower = max(lower, 0)
        valid = active.between(lower, upper) | active.isin(top_codes)
    if not valid.all():
        raise UnverifiedMetadataError(f"Unverified value code for {concept}")
    if item.get("missing_codes"):
        return series.astype("Float64" if decimals else "Int64").mask(missing)
    return series


def _read(
    wave: int,
    kind: str,
    *,
    setup_path: str | Path,
    records_path: str | Path | TextIO,
    concepts: Sequence[str] | None,
    nrows: int | None,
) -> pd.DataFrame:
    table = _table(wave, kind)
    selected = list(table) if concepts is None else list(concepts)
    if len(set(selected)) != len(selected):
        raise UnverifiedMetadataError("Duplicate requested concepts")
    for concept in selected:
        if concept not in table:
            raise UnverifiedMetadataError(
                f"No verified {kind} concept {concept!r} for PSID {wave}"
            )
    if "interview" not in selected:
        selected.insert(0, "interview")
    if nrows is not None and (type(nrows) is not int or nrows < 0):
        raise ValueError("nrows must be a nonnegative integer or None")
    verify_setup(wave, setup_path)
    columns: dict[str, list[int | float]] = {c: [] for c in selected}
    required_width = max(table[c]["end"] for c in selected)
    context = (
        nullcontext(records_path)
        if hasattr(records_path, "read")
        else Path(records_path).open(encoding="ascii")
    )
    with context as stream:
        count = 0
        while nrows is None or count < nrows:
            try:
                record = stream.readline()
            except (UnicodeError, OSError):
                raise ValueError(
                    "Cannot decode PSID fixed-width record"
                ) from None
            if record == "":
                break
            record = record.rstrip("\r\n")
            if len(record) < required_width:
                raise ValueError("Truncated PSID fixed-width record")
            for concept in selected:
                item = table[concept]
                token = record[item["start"] - 1 : item["end"]].strip()
                decimals = item.get("decimals", 0)
                valid_token = (
                    re.fullmatch(
                        rf"-?\d+(?:\.\d{{1,{decimals}}})?\Z",
                        token,
                        flags=re.ASCII,
                    )
                    if decimals
                    else _INTEGER.fullmatch(token)
                )
                if not valid_token:
                    raise ValueError(
                        f"Blank or invalid numeric field for {concept}"
                    )
                columns[concept].append(
                    float(token) if decimals else int(token)
                )
            count += 1
    frame = pd.DataFrame(
        {
            concept: _decode_column(columns[concept], table[concept], concept)
            for concept in selected
        }
    )
    ids = frame["interview"]
    if ids.isna().any() or (ids <= 0).any() or ids.duplicated().any():
        raise ValueError(
            "Nonpositive, missing or duplicate family interview ID"
        )
    if "head_sex" in frame:
        frame["head_sex"] = (
            frame["head_sex"].map({1: "male", 2: "female"}).astype("string")
        )
    if "wife_age" in frame:
        raw_age = pd.Series(columns["wife_age"], dtype="int64")
        frame["wife_present"] = raw_age.ne(0)
        frame["wife_age"] = (
            frame["wife_age"].astype("Int64").mask(raw_age.eq(0))
        )
    if "head_age" in frame:
        frame["head_age"] = frame["head_age"].astype("Int64")
    if kind == "income":
        frame.insert(0, "income_year", wave - 1)
    frame.insert(0, "wave", wave)
    return frame


def read_family_income(
    wave: int,
    *,
    setup_path: str | Path,
    records_path: str | Path | TextIO,
    concepts: Sequence[str] | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read registered income fields from an explicitly supplied record file.

    ``records_path`` may also be a text stream, for invented fixtures.
    Amounts named ``*_reported`` retain their source reporting periods;
    they cannot substitute for unavailable generated annual concepts.
    """

    return _read(
        wave,
        "income",
        setup_path=setup_path,
        records_path=records_path,
        concepts=concepts,
        nrows=nrows,
    )


def read_family_wealth(
    wave: int,
    *,
    setup_path: str | Path,
    records_path: str | Path | TextIO,
    concepts: Sequence[str] | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read registered imputed wealth, its components and accuracy flags."""

    return _read(
        wave,
        "wealth",
        setup_path=setup_path,
        records_path=records_path,
        concepts=concepts,
        nrows=nrows,
    )


def reconcile_family_income(frame: pd.DataFrame) -> dict[str, dict]:
    """Count exact and within-tolerance matches for registered identities.

    Legacy waves delegate to family_income's public reconciliation
    function. New waves use only identities documented in their registry.
    A partial frame missing an identity's inputs raises.
    """

    out: dict[str, dict] = {}
    for wave, rows in frame.groupby("wave", sort=True):
        wave = int(wave)
        if wave in family_income.INCOME_WAVES:
            _require_identity_inputs(
                rows,
                {
                    "total_family_income",
                    *family_income.FAMILY_INCOME_AGGREGATES,
                    *family_income.HW_EARNED_CONCEPTS,
                    *family_income.ASSET_INCOME_CONCEPTS,
                    *family_income.HW_TRANSFER_COMPONENTS[wave],
                    *family_income.OFUM_TRANSFER_COMPONENTS,
                    "ofum_labor",
                },
            )
            out.update(family_income.reconcile_family_income(rows))
            continue
        definitions = wave_registry(wave)["income_identities"]
        _require_identity_inputs(
            rows,
            {
                *definitions,
                *(
                    component
                    for parts in definitions.values()
                    for component in parts
                ),
            },
        )
        out[str(wave)] = {
            aggregate: _identity_counts(
                rows[aggregate], rows[components].sum(axis=1, skipna=False)
            )
            for aggregate, components in definitions.items()
        }
    return out


def reconcile_wealth1(frame: pd.DataFrame) -> dict[str, dict]:
    """Check each wave's WEALTH1 and WEALTH2 definitions without filling gaps."""

    out: dict[str, dict] = {}
    for wave, rows in frame.groupby("wave", sort=True):
        wave = int(wave)
        if wave in family_income.WEALTH1_ASSETS:
            _require_identity_inputs(
                rows,
                {
                    "wealth1",
                    "wealth2",
                    "home_equity",
                    *family_income.WEALTH1_ASSETS[wave],
                    *family_income.WEALTH1_DEBTS[wave],
                },
            )
            out.update(family_income.reconcile_wealth1(rows))
            continue
        registry = wave_registry(wave)
        if "wealth" not in registry:
            raise UnverifiedMetadataError(f"No wealth definition for {wave}")
        _require_identity_inputs(
            rows,
            {
                "wealth1",
                "wealth2",
                "home_equity",
                *registry["wealth_assets"],
                *registry["wealth_debts"],
            },
        )
        assets = rows[registry["wealth_assets"]].sum(axis=1, skipna=False)
        debts = rows[registry["wealth_debts"]].sum(axis=1, skipna=False)
        out[str(wave)] = {
            "wealth1": _identity_counts(rows["wealth1"], assets - debts),
            "wealth2": _identity_counts(
                rows["wealth2"], rows["wealth1"] + rows["home_equity"]
            ),
        }
    return out


def _require_identity_inputs(rows: pd.DataFrame, names: set[str]) -> None:
    for name in sorted(names):
        values = pd.to_numeric(rows[name], errors="coerce")
        if values.isna().any() or values.mod(1).ne(0).any():
            raise UnverifiedMetadataError(
                f"Missing or noninteger reconciliation component {name}"
            )
