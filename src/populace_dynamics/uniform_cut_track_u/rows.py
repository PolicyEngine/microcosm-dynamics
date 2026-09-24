"""The registered Track U rows as builder and income-concept parameters.

Each row of the exercise-2 specification
(``docs/design/boomers2004_uniform_cut_comparison.md``, sections 11 and
15) differs from the primary U0 in one field, except U6, which is defined
on U1 (plan ``critical-path-uniform-cut-20260923.md`` section 7).  A row
here is a set of overrides of :class:`populace_dynamics.cohorts.age67.
Age67Spec` and :class:`populace_dynamics.estimates.adjusted_poverty.
AdjustedPovertySpec`; the defaults of those two classes are U0.

:func:`check_rows_against_block` holds :data:`REGISTERED_ROWS` to the
specification's machine-readable block, so a row a run computes is the
row the specification registers.  U7 (employer DC balances) is not
built: it needs a label investigation of the PSID P-section items.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from populace_dynamics.cohorts import age67
from populace_dynamics.estimates import adjusted_poverty as ap

__all__ = [
    "PRIMARY_ROW",
    "REGISTERED_ROWS",
    "SPECIFICATION_PATH",
    "TrackURow",
    "check_rows_against_block",
    "row_from_block",
    "specification_block",
]

_ROOT = Path(__file__).resolve().parents[3]
SPECIFICATION_PATH = (
    _ROOT / "docs" / "design" / "boomers2004_uniform_cut_comparison.md"
)
PRIMARY_ROW = "U0"
_AGE67_FIELDS = frozenset(f.name for f in fields(age67.Age67Spec))
_INCOME_FIELDS = frozenset(f.name for f in fields(ap.AdjustedPovertySpec))
#: Block keys that describe a row without being a parameter.
_METADATA_KEYS = frozenset({"status", "awaiting", "financial_assets"})


@dataclass(frozen=True)
class TrackURow:
    """One registered row: its overrides of the two specs, and status."""

    row_id: str
    field_changed: str
    description: str
    age67: Mapping[str, Any] = field(default_factory=dict)
    income: Mapping[str, Any] = field(default_factory=dict)
    built: bool = True
    not_built_reason: str | None = None
    awaiting: str | None = None

    def __post_init__(self) -> None:
        unknown = (set(self.age67) - _AGE67_FIELDS) | (
            set(self.income) - _INCOME_FIELDS
        )
        if unknown:
            raise ValueError(f"{self.row_id}: unknown fields {unknown}")
        if self.built:
            self.age67_spec()
            self.income_spec()
        elif not self.not_built_reason:
            raise ValueError(f"{self.row_id}: a row not built needs a reason")

    def age67_spec(self) -> age67.Age67Spec:
        return age67.Age67Spec(**dict(self.age67))

    def income_spec(self) -> ap.AdjustedPovertySpec:
        return ap.AdjustedPovertySpec(**dict(self.income))

    def as_dict(self) -> dict[str, Any]:
        return {
            "row": self.row_id,
            "field": self.field_changed,
            "description": self.description,
            "age67_overrides": dict(self.age67),
            "income_overrides": dict(self.income),
            "built": self.built,
            "not_built_reason": self.not_built_reason,
            "awaiting": self.awaiting,
        }


REGISTERED_ROWS: dict[str, TrackURow] = {
    row.row_id: row
    for row in (
        TrackURow(
            "U0",
            "-",
            "primary: exact age (odd birth years 1937-1945 at 67), family "
            "unit, reported asset income replaced by the annuity, Census "
            "weighted-average 65+ thresholds, SSI offset for existing "
            "recipients",
        ),
        TrackURow(
            "U1",
            "population",
            "all ten birth years: even birth years at 66 and 68 with half "
            "weight each, 1936 at 68 only",
            age67={"row": "U1"},
        ),
        TrackURow(
            "U2",
            "SSI",
            "no SSI response",
            income={"ssi_rule": "none"},
        ),
        TrackURow(
            "U3",
            "SSI",
            "full static SSI recomputation (upper bound)",
            income={"ssi_rule": "full_static_recomputation"},
        ),
        TrackURow(
            "U4",
            "income unit",
            "head and wife income only",
            income={"income_unit": "head_wife"},
        ),
        TrackURow(
            "U5",
            "asset income",
            "keep reported asset income and add the annuity",
            income={"asset_income_rule": "keep"},
        ),
        TrackURow(
            "U6",
            "cut (on U1)",
            "U1 with the 1936 birth year uncut if the cut starts in 2004 "
            "(the cut reaches an observation only when its member turns 67 "
            "in or after 2004)",
            age67={"row": "U1"},
            income={"cut_start_year": 2004},
            awaiting=(
                "Max, plan section 10 decision 8 (the scenario's start "
                "year; the scorecard's 'from 2004' has no readable source)"
            ),
        ),
        TrackURow(
            "U7",
            "financial assets",
            "WEALTH1 plus employer DC balances",
            built=False,
            not_built_reason=(
                "needs a label investigation of the PSID P-section pension "
                "account items (plan section 4); not built"
            ),
        ),
        TrackURow(
            "U8",
            "threshold",
            "PSID CENSUS NEEDS STANDARD",
            income={"threshold_rule": "psid_census_needs_standard"},
        ),
        TrackURow(
            "U9",
            "mortality",
            "SSA period life table for 2004",
            income={"mortality_basis": "ssa_period_2004"},
        ),
        TrackURow(
            "U10",
            "threshold",
            "Census size-by-related-children matrix (65+ rows for sizes 1 "
            "and 2)",
            income={"threshold_rule": "census_matrix_65plus"},
        ),
        TrackURow(
            "U-inst",
            "universe",
            "add persons in institutions (sequence 51-59) with the "
            "family-of-record income rule",
            age67={
                "presence": "in_family_or_institution",
                "institution_income_rule": "family_of_record",
            },
            awaiting=(
                "the referee (the institution income rule is a builder "
                "default)"
            ),
        ),
    )
}


def specification_block(path: Path = SPECIFICATION_PATH) -> dict[str, Any]:
    """The specification's machine-readable JSON block (section 15)."""

    text = Path(path).read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    if len(blocks) != 1:
        raise ValueError(
            f"{path} must hold exactly one JSON block, found {len(blocks)}"
        )
    return json.loads(blocks[0])


def row_from_block(row_id: str, entry: Mapping[str, Any]) -> dict[str, Any]:
    """A block row's overrides: ``age67``, ``income``, ``built``, ``awaiting``.

    ``population: all_ten_birth_years`` and ``on: U1`` select the U1
    population; keys naming an :class:`~populace_dynamics.cohorts.age67.
    Age67Spec` or :class:`~populace_dynamics.estimates.adjusted_poverty.
    AdjustedPovertySpec` field are overrides; ``status: not_built`` marks
    a row not built.  Any other key is refused.
    """

    age67_overrides: dict[str, Any] = {}
    income: dict[str, Any] = {}
    for key, value in entry.items():
        if key in ("population", "on"):
            expected = "all_ten_birth_years" if key == "population" else "U1"
            if value != expected:
                raise ValueError(f"{row_id}: {key}={value!r} is not known")
            age67_overrides["row"] = "U1"
        elif key in _AGE67_FIELDS:
            age67_overrides[key] = value
        elif key in _INCOME_FIELDS:
            income[key] = value
        elif key not in _METADATA_KEYS:
            raise ValueError(f"{row_id}: unknown block key {key!r}")
    status = entry.get("status")
    if status not in (None, "not_built"):
        raise ValueError(f"{row_id}: unknown status {status!r}")
    return {
        "age67": age67_overrides,
        "income": income,
        "built": status != "not_built",
        "awaiting": entry.get("awaiting"),
    }


def check_rows_against_block(
    block: Mapping[str, Any],
    rows: Mapping[str, TrackURow] | None = None,
) -> dict[str, Any]:
    """Refuse rows that differ from the specification block's rows.

    Every block row must be a row here with the same overrides, built
    status and awaiting note, and no row here may be missing from the
    block.
    """

    rows = REGISTERED_ROWS if rows is None else rows
    registered = dict(block.get("rows") or {})
    if set(registered) != set(rows):
        raise ValueError(
            f"rows {sorted(rows)} differ from the block's "
            f"{sorted(registered)}"
        )
    for row_id, entry in registered.items():
        parsed = row_from_block(row_id, entry)
        row = rows[row_id]
        mine = {
            "age67": dict(row.age67),
            "income": dict(row.income),
            "built": row.built,
            "awaiting": row.awaiting is not None,
        }
        theirs = {**parsed, "awaiting": parsed["awaiting"] is not None}
        if mine != theirs:
            raise ValueError(
                f"row {row_id} differs from the specification block: "
                f"code {mine} != block {theirs}"
            )
    return {
        "specification_version": block.get("version"),
        "rows_checked": sorted(registered),
        "rows_equal_the_block": True,
    }
