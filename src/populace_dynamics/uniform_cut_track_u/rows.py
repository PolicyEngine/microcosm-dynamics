"""The registered Track U rows as builder and income-concept parameters.

Each row of the exercise-2 specification
(``docs/design/boomers2004_uniform_cut_comparison.md``, sections 11 and
15) differs from the primary U0 in one field; U1 (all ten birth years)
and U0-F (U0 restricted to the birth years 1941, 1943 and 1945) change
the population itself.  Each one-field alternative defined on U0 (U2,
U3, U4, U5, U7, U8, U9, U10) is also registered on U0-F's population as
its ``-F`` row (U2-F ... U10-F; :data:`FALLBACK_ALTERNATIVES`), so that
the registration carries its alternatives whether or not the 2005 and
2007 wealth supplements are staged (second referee, S8).  A row here is a set
of overrides of :class:`populace_dynamics.cohorts.age67.Age67Spec` and
:class:`populace_dynamics.estimates.adjusted_poverty.
AdjustedPovertySpec`; the defaults of those two classes are U0.

Rows U6 (the cut's start year, on U1) and U-inst (institutions admitted)
of u1-draft-3 and -4 are withdrawn in u1-draft-5 (second referee, S5 and
S7): the primary now starts the cut in 2004 (``cut_start_year``), so U6
would equal U1; the Census cannot determine poverty status for people in
institutional group quarters, and on the staged PSID U-inst would add one
U0 observation (born 1937) and none to U0-F.

:data:`HEADLINE_RULE` is the specification's fallback rule: U0 is the
headline when the 2005 and 2007 wealth supplements are staged,
adjudicated and read before the #42 registration, U0-F otherwise, by
staging status only.  Plan section 10 decision 3 (Max downloads the
supplements) is decided (cos decision d189), and since u1-draft-6 the
supplements are staged and adjudicated, so on the staged PSID the rule
gives U0.  Since u1-draft-7 the rule is resolved on that source: U0 is
the headline, and U0-F and the -F rows stay registered as alternatives
(the second referee's S8 default), so they no longer carry an
``awaiting`` note; Max ruled both at ratification (cos decision d411
item (a), u1-ratified-1).

:func:`check_rows_against_block` holds :data:`REGISTERED_ROWS` to the
specification's machine-readable block, so a row a run computes is the
row the specification registers, and :func:`check_rulings_against_block`
holds :data:`MAX_RULINGS` to its ``decisions``.  U7 (employer DC
balances; built in u1-draft-7 after the label investigation of the PSID
pension section, :mod:`populace_dynamics.data.employer_dc`) adds the
head's and wife's employer DC account balances the pension section
observes to WEALTH1 (``financial_assets="wealth1_plus_employer_dc"``).
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
    "FALLBACK_ALTERNATIVES",
    "FALLBACK_ROW",
    "HEADLINE_RULE",
    "MAX_RULINGS",
    "PRIMARY_ROW",
    "REGISTERED_ROWS",
    "SPECIFICATION_PATH",
    "TrackURow",
    "check_rows_against_block",
    "check_rulings_against_block",
    "row_from_block",
    "specification_block",
]

_ROOT = Path(__file__).resolve().parents[3]
SPECIFICATION_PATH = (
    _ROOT / "docs" / "design" / "boomers2004_uniform_cut_comparison.md"
)
PRIMARY_ROW = "U0"
#: The registered fallback row (U0 on 1941, 1943 and 1945).
FALLBACK_ROW = "U0-F"
#: The specification's headline rule (section 11; ruled by Max, d411
#: item (a)).
HEADLINE_RULE = "u0_if_2005_2007_wealth_staged_before_registration_else_u0f"
#: Block ``population`` values and the builder row they select.
_POPULATION_ROWS = {
    "all_ten_birth_years": "U1",
    "birth_years_1941_1943_1945": FALLBACK_ROW,
}
_AGE67_FIELDS = frozenset(f.name for f in fields(age67.Age67Spec))
_INCOME_FIELDS = frozenset(f.name for f in fields(ap.AdjustedPovertySpec))
#: Block keys that describe a row without being a parameter.
_METADATA_KEYS = frozenset({"status", "awaiting"})


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


#: The one-field alternatives defined on U0 that are also registered on
#: U0-F's population, and the name of each ``-F`` row (second referee S8;
#: U7-F since U7 is built, u1-draft-7).
FALLBACK_ALTERNATIVES: dict[str, str] = {
    row_id: f"{row_id}-F"
    for row_id in ("U2", "U3", "U4", "U5", "U7", "U8", "U9", "U10")
}

_BASE_ROWS: tuple[TrackURow, ...] = (
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
        "full static SSI recomputation (the largest SSI response of "
        "the three registered rules, not a bound on DYNASIM's "
        "simulation)",
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
        "U0-F",
        "population",
        "U0 restricted to the birth years 1941, 1943 and 1945 (the "
        "blocked 1937 and 1939 left out and counted); the headline when "
        "the 2005 and 2007 wealth supplements are not staged before "
        "the #42 registration",
        age67={"row": FALLBACK_ROW},
    ),
    TrackURow(
        "U7",
        "financial assets",
        "WEALTH1 plus the head's and wife's employer DC account balances "
        "the PSID pension section observes (the current job's account; "
        "previous employers' accounts left to accumulate)",
        income={"financial_assets": "wealth1_plus_employer_dc"},
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
)


def _on_fallback(row: TrackURow) -> TrackURow:
    """``row``'s field and value on U0-F's population (its -F row)."""

    return TrackURow(
        FALLBACK_ALTERNATIVES[row.row_id],
        row.field_changed,
        f"{row.description}, on U0-F's population (birth years 1941, "
        "1943 and 1945)",
        age67={**dict(row.age67), "row": FALLBACK_ROW},
        income=dict(row.income),
    )


REGISTERED_ROWS: dict[str, TrackURow] = {
    row.row_id: row
    for row in (
        *_BASE_ROWS,
        *(
            _on_fallback(row)
            for row in _BASE_ROWS
            if row.row_id in FALLBACK_ALTERNATIVES
        ),
    )
}


#: Max's rulings on exercise 2 (cos decisions d189, 2026-09-24, and d411,
#: 2026-09-26; specification section 16).  The section 15 block records
#: the same rulings under ``decisions``; a registered run refuses a block
#: whose rulings differ (:func:`check_rulings_against_block`).  d411 adopts
#: the defaults filed with the ``u1-draft-7`` card, except that item (g)
#: adds the comparison memo's small-cell rule (``memo_small_cells``), a
#: reporting rule for the memo that changes no computation here.
MAX_RULINGS: dict[str, dict[str, Any]] = {
    "claim_class": {
        "ruling": "track_u_psid_realized_measurement_not_a_projection",
        "declined": ["hold_exercise_2_for_track_v"],
        "plan_section_10": "decision 1",
        "decision_record": "d189",
    },
    "ssi_rule": {
        "ruling": "offset_existing_recipients",
        "declined_as_primary": ["none", "full_static_recomputation"],
        "registered_as": ["U2", "U3"],
        "plan_section_10": "decision 5",
        "decision_record": "d189",
    },
    "wealth_supplements": {
        "ruling": "downloaded_by_max",
        "plan_section_10": "decision 3",
        "decision_record": "d189",
    },
    "ratification_and_registration": {
        "ruling": "ratify_by_merge_post_42_registration_run_one_shot",
        "publishes_regardless": True,
        "registration_describes": (
            "static_simulation_on_psid_observed_incomes"
        ),
        "plan_section_10": "decision 7",
        "decision_record": "d411",
    },
    "headline_row": {
        "ruling": "U0",
        "rule": "u0_if_2005_2007_wealth_staged_before_registration_else_u0f",
        "registration_states": [
            "u1_matches_the_report_birth_year_mix",
            "u0_omits_the_uncut_1936_birth_year",
        ],
        "decision_record": "d411",
        "item": "(a)",
    },
    "rows": {
        "ruling": [
            "U0",
            "U1",
            "U2",
            "U3",
            "U4",
            "U5",
            "U0-F",
            "U7",
            "U8",
            "U9",
            "U10",
            "U2-F",
            "U3-F",
            "U4-F",
            "U5-F",
            "U7-F",
            "U8-F",
            "U9-F",
            "U10-F",
        ],
        "declined": ["alternatives_on_u0_only"],
        "decision_record": "d411",
        "item": "(a)",
    },
    "financial_assets": {
        "ruling": "wealth1",
        "declined_as_primary": ["wealth1_plus_employer_dc"],
        "registered_as": ["U7", "U7-F"],
        "decision_record": "d411",
        "item": "(b)",
    },
    "acceptance_rule": {
        "ruling": None,
        "declined": ["numerical_rule_set_by_max_before_registration"],
        "plan_section_10": "decision 6",
        "decision_record": "d411",
        "item": "(c)",
    },
    "cut_start_year": {
        "ruling": 2004,
        "declined": [None],
        "plan_section_10": "decision 8",
        "decision_record": "d411",
        "item": "(d)",
    },
    "definitions_extract": {
        "ruling": "cleared_extract_used_as_builder_input",
        "sha256": (
            "a3978b683b4275424b6d12e9fe45f021fae277ccf9731a7883952564b6ed0384"
        ),
        "plan_section_10": "decision 2",
        "decision_record": "d411",
        "item": "(e)",
    },
    "rules_implementation": {
        "ruling": "python_income_concept_not_axiom",
        "declined": ["axiom_executed_ssi"],
        "plan_section_10": "decision 4",
        "decision_record": "d411",
        "item": "(e)",
        "named_in": "d189 as filed",
    },
    "clarification_request": {
        "ruling": "none_before_the_one_shot_gaps_reported_as_results",
        "declined": ["urban_clarification_request"],
        "plan_section_10": "decision 9",
        "decision_record": "d411",
        "item": "(f)",
    },
    "freeze_defaults": {
        "ruling": "specification_section_16_frozen_list",
        "except": ["memo_small_cells"],
        "decision_record": "d411",
        "item": "(g)",
    },
    "memo_small_cells": {
        "ruling": {
            "flag_unweighted_n_below": 30,
            "unweighted_n": "n_observations",
            "no_switcher_cell": "uncertainty_not_estimable",
        },
        "declined": ["no_small_cell_flag"],
        "basis": "second referee O1; independent skeptic check, 2026-09-25",
        "decision_record": "d411",
        "item": "(g)",
    },
}


def check_rulings_against_block(block: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse a block whose ``decisions`` differ from :data:`MAX_RULINGS`.

    The block must record ``ruled_by`` "Max" and a ``ruled_on`` date, and
    exactly the fields of :data:`MAX_RULINGS`, each equal to the code's.
    """

    decisions = dict(block.get("decisions") or {})
    if decisions.pop("ruled_by", None) != "Max" or not decisions.pop(
        "ruled_on", None
    ):
        raise ValueError("the block records no ruling by Max")
    if decisions != MAX_RULINGS:
        raise ValueError(
            "the block's decisions differ from the code's MAX_RULINGS: "
            f"{sorted(set(decisions) ^ set(MAX_RULINGS))} or their values"
        )
    return {"rulings_checked": sorted(MAX_RULINGS), "rulings_equal": True}


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
    population; ``population: birth_years_1941_1943_1945`` selects U0-F
    (with ``on: U0``, which names its base and changes nothing); keys
    naming an :class:`~populace_dynamics.cohorts.age67.Age67Spec` or
    :class:`~populace_dynamics.estimates.adjusted_poverty.
    AdjustedPovertySpec` field are overrides; ``status: not_built`` marks
    a row not built.  Any other key is refused.
    """

    age67_overrides: dict[str, Any] = {}
    income: dict[str, Any] = {}
    for key, value in entry.items():
        if key == "population":
            if value not in _POPULATION_ROWS:
                raise ValueError(f"{row_id}: {key}={value!r} is not known")
            age67_overrides["row"] = _POPULATION_ROWS[value]
        elif key == "on":
            if value not in ("U0", "U1"):
                raise ValueError(f"{row_id}: {key}={value!r} is not known")
            if value == "U1":
                age67_overrides.setdefault("row", "U1")
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
