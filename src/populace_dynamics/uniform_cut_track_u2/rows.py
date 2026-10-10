"""The ten registered U2 rows, the literal named deltas and U2's rulings.

Specification sections 11, 12, 15, 16 and 20.  Each row differs from the
primary U0 in one field (U1 in its population).  A row is a set of
overrides of :class:`~populace_dynamics.uniform_cut_track_u2.cohort.
U2CohortSpec` and :class:`~populace_dynamics.uniform_cut_track_u2.
estimator.U2IncomeSpec`; the defaults of those classes are U0.

* :data:`REGISTERED_ROWS` -- U0, U1, U2, U3, U4, U5, U7, U8, U9 and U10.
  U0-F and the eight ``-F`` rows are omitted (section 3 amendment); U6
  and U-inst stay withdrawn.  :func:`check_rows_against_block` holds them
  equal to the section 15 block.
* :data:`HEADLINE_ROW` -- fixed U0, no fallback (section 11).
* :data:`NAMED_DELTAS` -- the section 12 literal strings D01-D26, without
  terminal periods; :func:`check_named_deltas_against_specification`
  holds them byte-equal to the specification text.  U1's tuple
  (``uniform_cut_track_u.runner.NAMED_DELTAS``) is untouched.
* :data:`U2_RULINGS` -- U2's own rulings record: Max's decision d514
  (2026-09-28) adopting every section 16 default and ratification of the
  specification, as the specification's header and section 20 step 1
  record it.  :func:`check_u2_rulings_against_block` refuses a block
  whose ``decisions`` differ, and refuses U1's ``MAX_RULINGS`` outright:
  copying U1's authorization is insufficient (section 14).  The current
  ``u2-draft-4`` block still records ``u2_ratification: pending_Max``
  (and section 16a's amendments await Max's ruling); section 20 step 5
  materializes the final block, so a registered run refuses.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from populace_dynamics.uniform_cut_track_u2 import identity
from populace_dynamics.uniform_cut_track_u2.cohort import U2CohortSpec
from populace_dynamics.uniform_cut_track_u2.estimator import U2IncomeSpec

__all__ = [
    "HEADLINE_ROW",
    "HEADLINE_RULE",
    "NAMED_DELTAS",
    "REGISTERED_ROWS",
    "ROW_IDS",
    "SENSITIVITIES_UNSCORED",
    "U2_RULINGS",
    "U2Row",
    "check_named_deltas_against_specification",
    "check_rows_against_block",
    "check_u2_rulings_against_block",
    "named_deltas_in_specification",
    "specification_block",
]

HEADLINE_ROW = "U0"
#: Section 15 ``population.headline.rule``.
HEADLINE_RULE = "fixed_u0_no_fallback"
ROW_IDS: tuple[str, ...] = (
    "U0",
    "U1",
    "U2",
    "U3",
    "U4",
    "U5",
    "U7",
    "U8",
    "U9",
    "U10",
)
#: Section 5 and section 15 ``sensitivities_unscored``: two percent real
#: interest, reported on U0 and never scored.
SENSITIVITIES_UNSCORED: dict[str, tuple[float, ...]] = {
    "real_interest_rate": (0.02,),
}
_COHORT_FIELDS = frozenset(f.name for f in fields(U2CohortSpec))
_INCOME_FIELDS = frozenset(f.name for f in fields(U2IncomeSpec))
#: Section 15 row keys that are not field names, and the override each
#: stands for.
_BLOCK_KEY_OVERRIDES: dict[tuple[str, str], tuple[str, str, Any]] = {
    ("population", "all_ten_birth_years"): ("cohort", "row", "U1"),
    ("income_unit", "head_wife"): ("income", "income_unit", "head_wife"),
}


@dataclass(frozen=True)
class U2Row:
    """One registered U2 row: its overrides of the two specs."""

    row_id: str
    field_changed: str
    description: str
    cohort: Mapping[str, Any] = field(default_factory=dict)
    income: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = (set(self.cohort) - _COHORT_FIELDS) | (
            set(self.income) - _INCOME_FIELDS
        )
        if unknown:
            raise ValueError(f"{self.row_id}: unknown fields {unknown}")
        self.cohort_spec()
        self.income_spec()

    def cohort_spec(self) -> U2CohortSpec:
        return U2CohortSpec(**dict(self.cohort))

    def income_spec(self) -> U2IncomeSpec:
        return U2IncomeSpec(**dict(self.income))

    def as_dict(self) -> dict[str, Any]:
        return {
            "row": self.row_id,
            "field": self.field_changed,
            "description": self.description,
            "cohort_overrides": dict(self.cohort),
            "income_overrides": dict(self.income),
        }


REGISTERED_ROWS: dict[str, U2Row] = {
    row.row_id: row
    for row in (
        U2Row(
            "U0",
            "-",
            "primary and fixed headline: odd birth years 1947-1955 at "
            "exact age 67, family unit, reported asset income replaced by "
            "the annuity, Census weighted-average 65+ thresholds, SSI "
            "offset for existing recipients",
        ),
        U2Row(
            "U1",
            "population",
            "all ten birth years: even birth years 1946-1954 at 66 and 68 "
            "with half weight each (1946 included at both ages)",
            cohort={"row": "U1"},
        ),
        U2Row("U2", "SSI", "no SSI response", income={"ssi_rule": "none"}),
        U2Row(
            "U3",
            "SSI",
            "full static SSI response: the offset plus new enrollment of "
            "newly income-eligible head/spouse-slot units",
            income={"ssi_rule": "full_static_recomputation"},
        ),
        U2Row(
            "U4",
            "income unit",
            "head/reference-person-and-spouse-slot income basis; OFUM "
            "members (codes 90 and 92 included) keep the family basis",
            income={"income_unit": "head_wife"},
        ),
        U2Row(
            "U5",
            "asset income",
            "keep reported asset, retirement-account and farm income and "
            "add the annuity",
            income={"asset_income_rule": "keep"},
        ),
        U2Row(
            "U7",
            "financial assets",
            "WEALTH1 plus the verified employer DC balances of the "
            "reference person and spouse income slot",
            income={"financial_assets": "wealth1_plus_employer_dc"},
        ),
        U2Row(
            "U8",
            "threshold",
            "PSID CENSUS NEEDS STANDARD",
            income={"threshold_rule": "psid_census_needs_standard"},
        ),
        U2Row(
            "U9",
            "mortality",
            "SSA period life table for 2004",
            income={"mortality_basis": "ssa_period_2004"},
        ),
        U2Row(
            "U10",
            "threshold",
            "Census size-by-related-children matrix (65+ rows for sizes 1 "
            "and 2)",
            income={"threshold_rule": "census_matrix_65plus"},
        ),
    )
}

#: Section 12, D01-D26: the literal output texts, no terminal periods.
NAMED_DELTAS: tuple[str, ...] = (
    "PSID and SIPP differ in population coverage and in the collection "
    "and measurement of income and wealth",
    "U2 uses realized 2014–2022 incomes, with income year 2012 "
    "additionally entering row U1, rather than DYNASIM3's projection from "
    "the 1990–93 SIPP under 2002 Trustees assumptions",
    "Realized COLAs, asset histories and economic conditions enter the "
    "observed PSID inputs; the Report uses its stated projection "
    "assumptions",
    "income year 2020: pandemic-era transfers (expanded UI; how the PSID "
    "records Economic Impact Payments) under the PSID money-income concept",
    "The observed universe reflects attrition, survival to the interview "
    "after the income year, immigrant coverage and later immigrant "
    "refreshment; registered cross-section weights are used without "
    "additional calibration",
    "Institutionalized persons are outside the observation universe and "
    "appear only in counted dispositions",
    "The primary assigns family-unit resources to individuals, while the "
    "Report establishes inclusion of spouse resources without fully "
    "specifying poverty-family membership or nonspouse co-resident "
    "treatment",
    "Family wealth includes OFUM-owned assets and stands in for an OFUM "
    "cohort member's resources; the primary does not identify and "
    "allocate each asset to its individual owner",
    "The primary retains PSID money-income sources other than the "
    "explicitly replaced asset, reference-person retirement-account and "
    "imputed farm components; the Report's treatment of every "
    "corresponding poverty-income source is not established",
    "Members whose marital state remains unresolved are retained in all "
    "and applicable sex cells but excluded and counted in marital cells",
    "Social Security is self-reported and may reflect Medicare-premium "
    "netting; the cut is applied to the reported amount rather than a "
    "reconstructed gross entitlement",
    "Reference-person annuity and IRA income is removed while spouse and "
    "OFUM pension-annuity combinations remain under the inherited "
    "convention; balance-income overlap and annuities already in payment "
    "are not fully identified",
    "WEALTH1 excludes employer DC balances outside IRAs; row U7 adds only "
    "the reference-person and spouse balances covered by verified "
    "questionnaire routes, retaining documented omissions and "
    "unreported-amount dispositions",
    "PSID other-assets coverage includes categories whose correspondence "
    "to the Report's stated financial-asset definition is not established",
    "Interview-time wealth is paired with income from the preceding "
    "calendar year",
    "Annuities use fixed population period life tables, the registered "
    "real interest rate and terminal closure, and family-head/legal-spouse "
    "lives rather than individually projected mortality histories",
    "Row U0 samples five alternate birth years at exact age 67 and does "
    "not represent all ten birth years in the Report's column",
    "Row U1 represents even birth years with half-weighted observations "
    "at ages 66 and 68; income, claiming, family composition and survival "
    "need not vary linearly between those ages",
    "Row U1 includes the 1946 birth year's age-66 observation in income "
    "year 2012; all U2 rows share identification support waves 2013–2023 "
    "while retaining row-specific observation and design frames",
    "Farm asset income is imputed using the registered positive-income "
    "share and whole-loss rule; business labor and asset income retain "
    "the PSID allocation convention",
    "SSI units are approximated from reference-person, spouse-slot and "
    "OFUM totals, with full attribution of spouse-slot Social Security and "
    "one aggregate OFUM individual unit",
    "SSI response uses annual amounts against twelve times the January "
    "federal benefit rate; reported SSI can include state supplements, "
    "while the response cap uses the federal rate",
    "Row U3 adds deterministic enrollment only for newly income-eligible "
    "head/spouse units under the inherited countable-income and resource "
    "proxies; OFUM new enrollment, complete resource ownership and full "
    "legal deeming are not modeled",
    "PSID children-in-family is a proxy for related children; "
    "weighted-average Census thresholds, the size-by-children matrix and "
    "the PSID needs standard use distinct composition conventions",
    "Relationship labels change in 2015 and 2017; U2 explicitly separates "
    "income-slot membership, legal-spouse annuity lives and marital "
    "resolution, with required source-routing ambiguities resolved before "
    "registration",
    "WEALTH1 uses seven asset components in 2015/2017 and eight from "
    "2019, with separately identified debts; each wave's documented "
    "identity is preserved",
)

#: U2's own rulings record (d514; specification header and section 20
#: step 1: Max approved the section 16 defaults and ratification).  The
#: keys follow section 16's decision table and section 15's identity.
U2_RULINGS: dict[str, dict[str, Any]] = {
    "claim_class": {
        "ruling": "track_u_psid_realized_measurement_not_a_projection",
        "decision_record": "d514",
    },
    "observation_convention": {
        "ruling": (
            "u0_exact_age_five_births_u1_both_half_weighted_observations"
        ),
        "decision_record": "d514",
    },
    "common_identification_support": {
        "ruling": "earliest_presence_in_common_support_waves",
        "support_waves": [2013, 2015, 2017, 2019, 2021, 2023],
        "decision_record": "d514",
    },
    "rows_and_fallback": {
        "ruling": list(ROW_IDS),
        "omitted": ["U0-F", "eight_-F_rows"],
        "headline": "fixed_u0_no_fallback",
        "decision_record": "d514",
    },
    "income_and_mortality": {
        "ruling": (
            "inherited_concept_and_life_tables_with_section_3_role_"
            "amendment_and_later_wealth_identities"
        ),
        "decision_record": "d514",
    },
    "ssi_capture": {
        "ruling": "separate_verified_2012_2022_capture_exact_2012_overlap",
        "decision_record": "d514",
    },
    "downloads": {
        "ruling": "no_approval_required_Max_2026_09_28",
        "decision_record": "d514",
    },
    "comparison_publication": {
        "ruling": (
            "fifteen_cells_inherited_precision_no_acceptance_threshold_"
            "publish_regardless"
        ),
        "acceptance_rule": None,
        "decision_record": "d514",
    },
    "process": {
        "ruling": (
            "mapping_review_invented_differential_tests_and_preregistration_"
            "pass_before_forecast_and_registration"
        ),
        "decision_record": "d514",
    },
    "ratification": {
        "ruling": "ratify_by_merge_after_section_20_steps_2_to_5",
        "decision_record": "d514",
    },
    "rulings_record": {
        "ruling": "separate_u2_record",
        "u1_rulings": "precedent_not_u2_execution_authorization",
        "decision_record": "d514",
    },
}
_RULED_ON = "2026-09-28"
_BLOCK_SECTION = "\n## 15. Machine-readable parameter block"


def specification_block(
    path: Path = identity.SPECIFICATION_PATH,
) -> dict[str, Any]:
    """The U2 specification's machine-readable JSON block (section 15).

    Only section 15 is searched, and it must hold exactly one JSON block.
    Other sections may quote JSON fragments (``u2-draft-4``'s section 16a
    proposes a replacement ``previous_routes`` fragment); a proposal is
    not the contract, so it is never read as the block.
    """

    identity.refuse_u1_identity({"path": path}, what="specification_block")
    text = Path(path).read_text(encoding="utf-8")
    start = text.find(_BLOCK_SECTION)
    end = text.find("\n## 16.", start + 1)
    if start < 0 or end < 0:
        raise ValueError(
            f"{path} has no section 15 ({_BLOCK_SECTION!r}) followed by "
            "section 16"
        )
    blocks = re.findall(r"```json\n(.*?)\n```", text[start:end], re.DOTALL)
    if len(blocks) != 1:
        raise ValueError(
            f"{path} section 15 must hold exactly one JSON block, found "
            f"{len(blocks)}"
        )
    block = json.loads(blocks[0])
    identity.refuse_u1_identity(
        {"specification": block.get("specification")},
        what="the specification block",
    )
    if block.get("specification") != identity.SPECIFICATION_ID:
        raise ValueError(
            f"the block names {block.get('specification')!r}, not "
            f"{identity.SPECIFICATION_ID!r}"
        )
    identity.check_target(block.get("target_id"), "the specification block")
    return block


def _parse_block_row(row_id: str, entry: Mapping[str, Any]) -> dict:
    cohort: dict[str, Any] = {}
    income: dict[str, Any] = {}
    for key, value in entry.items():
        mapped = _BLOCK_KEY_OVERRIDES.get((key, value))
        if mapped is not None:
            target, name, override = mapped
            (cohort if target == "cohort" else income)[name] = override
        elif key in _INCOME_FIELDS:
            income[key] = value
        elif key in _COHORT_FIELDS:
            cohort[key] = value
        else:
            raise ValueError(f"{row_id}: unknown block key {key!r}")
    return {"cohort": cohort, "income": income}


def check_rows_against_block(
    block: Mapping[str, Any],
    rows: Mapping[str, U2Row] | None = None,
) -> dict[str, Any]:
    """Refuse rows that differ from the section 15 block's rows."""

    rows = REGISTERED_ROWS if rows is None else rows
    registered = dict(block.get("rows") or {})
    if list(registered) != list(rows):
        raise ValueError(
            f"rows {list(rows)} differ from the block's {list(registered)}"
        )
    for row_id, entry in registered.items():
        parsed = _parse_block_row(row_id, entry)
        mine = {
            "cohort": dict(rows[row_id].cohort),
            "income": dict(rows[row_id].income),
        }
        if parsed != mine:
            raise ValueError(
                f"row {row_id} differs from the specification block: code "
                f"{mine} != block {parsed}"
            )
    headline = (block.get("population") or {}).get("headline") or {}
    if headline != {"rule": HEADLINE_RULE, "fallback_row": None}:
        raise ValueError(
            f"the block's headline {headline} is not the fixed U0 headline"
        )
    return {
        "specification_version": block.get("version"),
        "rows_checked": list(registered),
        "rows_equal_the_block": True,
        "headline": HEADLINE_ROW,
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False)


def check_u2_rulings_against_block(
    block: Mapping[str, Any],
) -> dict[str, Any]:
    """Refuse a block whose ``decisions`` are not U2's rulings record.

    The block must record ``ruled_by`` "Max", ``ruled_on`` 2026-09-28 and
    exactly :data:`U2_RULINGS` (equal under ``==`` and as canonical JSON).
    U1's ``MAX_RULINGS`` (or any record naming U1's decision records d189
    or d411 as authority) is refused: U2 has its own record.
    """

    recorded = block.get("decisions")
    if not isinstance(recorded, Mapping):
        raise ValueError("the U2 block records no rulings")
    decisions = dict(recorded)
    text = _canonical(decisions)
    if '"d189"' in text or '"d411"' in text:
        raise ValueError(
            "the block's decisions cite U1's rulings (d189/d411); copying "
            "U1's authorization is insufficient for U2 (section 14)"
        )
    ruled_by = decisions.pop("ruled_by", None)
    ruled_on = decisions.pop("ruled_on", None)
    if ruled_by != "Max" or ruled_on != _RULED_ON:
        raise ValueError(
            "the U2 block records no ruling by Max on d514 "
            f"(ruled_by={ruled_by!r}, ruled_on={ruled_on!r}); section 20 "
            "step 5 materializes the rulings record before a run"
        )
    if decisions != U2_RULINGS or _canonical(decisions) != _canonical(
        U2_RULINGS
    ):
        differing = sorted(set(decisions) ^ set(U2_RULINGS), key=str)
        raise ValueError(
            "the block's decisions differ from U2_RULINGS: "
            f"{differing} or their values"
        )
    return {"rulings_checked": sorted(U2_RULINGS), "rulings_equal": True}


_DELTA = re.compile(r"^- \*\*D(\d{2}):\*\* (.+)$", re.MULTILINE)


def named_deltas_in_specification(
    path: Path = identity.SPECIFICATION_PATH,
) -> tuple[str, ...]:
    """The section 12 bullets D01-D26 as literal strings."""

    text = Path(path).read_text(encoding="utf-8")
    start = text.index("## 12. Named deltas")
    end = text.index("## 13.", start)
    found = _DELTA.findall(text[start:end])
    numbers = [int(number) for number, _ in found]
    if numbers != list(range(1, 27)):
        raise ValueError(f"section 12 holds deltas {numbers}")
    return tuple(delta for _, delta in found)


def check_named_deltas_against_specification(
    path: Path = identity.SPECIFICATION_PATH,
) -> dict[str, Any]:
    """Refuse unless :data:`NAMED_DELTAS` equals section 12 byte for byte."""

    documented = named_deltas_in_specification(path)
    if documented != NAMED_DELTAS:
        differing = [
            i + 1
            for i, (a, b) in enumerate(
                zip(documented, NAMED_DELTAS, strict=True)
            )
            if a != b
        ]
        raise ValueError(f"named deltas differ from section 12: {differing}")
    if any(delta.endswith(".") for delta in NAMED_DELTAS):
        raise ValueError("a literal named delta carries a terminal period")
    return {"n_deltas": len(NAMED_DELTAS), "equal_to_section_12": True}
