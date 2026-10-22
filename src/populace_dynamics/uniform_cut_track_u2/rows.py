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
  specification, and every later U2 ruling: d637 and its confirmation
  d745 (section 16b), d1090 (section 16c), d1242 (section 19), d1597
  (section 13), d1649 (section 20 step 4) and d1724 (section 16d).  The
  entries for the registry-applied rulings are built from the registry
  module's own scopes (:data:`~populace_dynamics.data.u2_source_registry.
  RATIFIED_AMENDMENTS` and ``RATIFIED_EXCLUSIONS``), and
  :func:`check_rulings_against_code` holds the rest to the code and the
  committed registries.  :func:`check_u2_rulings_against_block` refuses a
  block whose ``decisions`` differ, and refuses U1's ``MAX_RULINGS``
  outright: copying U1's authorization is insufficient (section 14).
* :func:`expected_specification_block` -- the complete section 15 block
  as the code states it, and :func:`check_block_against_code`, which
  refuses a block that differs in any key or leaf (section 20 step 5:
  exact code/specification agreement).  Section 20 step 5 materialized
  the final block, ``u2-ratified-1``, so the committed block passes it.
"""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from populace_dynamics.data import family_income
from populace_dynamics.data import u2_source_registry as _registry
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.estimates import career
from populace_dynamics.estimates import uniform_cut_tabulation as ut
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    identity,
    loader,
    memo,
    parameters,
    sources,
    tabulation,
)
from populace_dynamics.uniform_cut_track_u2.cohort import U2CohortSpec
from populace_dynamics.uniform_cut_track_u2.estimator import U2IncomeSpec

__all__ = [
    "HEADLINE_ROW",
    "HEADLINE_RULE",
    "NAMED_DELTAS",
    "REGISTERED_ROWS",
    "ROW_IDS",
    "RULING_DECISIONS",
    "SENSITIVITIES_UNSCORED",
    "SPECIFICATION_STATUS",
    "SPECIFICATION_VERSION",
    "U2_RULINGS",
    "U2Row",
    "check_block_against_code",
    "check_named_deltas_against_specification",
    "check_rows_against_block",
    "check_rulings_against_code",
    "check_u2_rulings_against_block",
    "expected_specification_block",
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

#: The specification's version and status once section 20 step 5
#: materialized the final block (ratified by merge, section 20 step 6).
SPECIFICATION_VERSION = "u2-ratified-1"
SPECIFICATION_STATUS = "ratified_frozen"
#: U1's ratified specification version, which U2 inherits (section 15
#: ``inherits``; the U1 block's ``version``).
_U1_VERSION = "u1-ratified-1"
#: The structure-only U1 load's pin (section 13; d1597).
_U1_INPUT_FRAMES_SHA256 = (
    "43c41f444128ecf72ce9f8c5e64a7cda61a6fccaa2a58ff60ae7ce91356c4271"
)
#: The two section 20 step-4 passes (section 20 step 4; section 16d).
_STEP_4_FIRST_HEAD = "640adccf84f9f68c0fb893a834cfdfaca20e7888"
_STEP_4_SECOND_HEAD = "1e739d328b73c99d259a72952b3452546721bfb8"
_STEP_4_SECOND_TESTS_RUN = 39502262845


def _ruled(scope: Mapping[str, Any], **record: Any) -> dict[str, Any]:
    """A rulings-record entry for one registry scope of a ruling.

    ``scope`` is a :data:`~populace_dynamics.data.u2_source_registry.
    RATIFIED_AMENDMENTS` value: the entry names the registry entries the
    ruling governs and copies the ruling's decision, date, section and
    any confirmation or draft-3 lines exactly as the registry validator
    holds them.
    """

    ruling = scope["ruling"]
    entry = {
        **record,
        "registry_entries": [
            f"{scope['registry']}:{name}" for name in scope["entries"]
        ],
        "specification_section": ruling["specification_section"],
        "decision_record": ruling["decision"],
        "ruled_on": ruling["date"],
    }
    for key in ("confirmed_by", "confirmed_on", "option"):
        if key in ruling:
            entry[key] = ruling[key]
    for key in ("amends_draft_3_lines", "replaces_draft_3_lines"):
        if key in ruling:
            entry[key] = list(ruling[key])
    return entry


def _excluded(disposition: str, **record: Any) -> dict[str, Any]:
    """A rulings-record entry for one family-unit exclusion (d1090).

    Built from :data:`~populace_dynamics.data.u2_source_registry.
    RATIFIED_EXCLUSIONS`, the scope the registry validator holds each role
    entry to.
    """

    scope = _registry.RATIFIED_EXCLUSIONS[disposition]
    ruling = scope["ruling"]
    entry = {
        **record,
        "disposition": disposition,
        "excluded_from": "every_row",
        "member_condition": (
            None if scope["condition"] is None else dict(scope["condition"])
        ),
        "registry_entries": [f"roles:{name}" for name in scope["entries"]],
        "option": ruling["option"],
        "amends_draft_3_lines": list(ruling["amends_draft_3_lines"]),
        "specification_section": ruling["specification_section"],
        "decision_record": ruling["decision"],
        "ruled_on": ruling["date"],
    }
    if "amended_waves" in ruling:
        entry["amended_waves"] = list(ruling["amended_waves"])
    return entry


_AMENDMENTS = _registry.RATIFIED_AMENDMENTS

#: U2's own rulings record.  The first eleven entries are d514
#: (specification header and section 20 step 1: Max approved the section
#: 16 defaults and ratification); their keys follow section 16's decision
#: table and section 15's identity.  The later entries record d637 and its
#: confirmation d745 (section 16b), d1090 (section 16c), d1242, d1597,
#: d1649 and d1724 (section 16d); section 20 step 5 materialized them in
#: the section 15 block's ``decisions``.
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
    # d637 (2026-09-30) and d745 (2026-10-12): section 16b.
    "amendment_1a_documented_routes": _ruled(
        _AMENDMENTS["1a"],
        ruling="ratified_as_written",
        registration_discloses=(
            "ofum_route_documented_reporting_completeness_for_withheld_"
            "answers_not_documented"
        ),
    ),
    "amendment_1b_2013_inherited_meanings": _ruled(
        _AMENDMENTS["1b"], ruling="ratified_as_written"
    ),
    "amendment_1c_first_year_cohabitor": _ruled(
        _AMENDMENTS["1c"],
        ruling="ratified_as_written",
        convention=(
            "ofum_family_basis_outside_the_spouse_slot_no_legal_spouse_"
            "life_no_marital_resolution_inherited_birth_support"
        ),
    ),
    "amendment_2_annuitant_input_precedence": _ruled(
        _AMENDMENTS["2"],
        ruling="ratified_as_written",
        rule=(
            "recorded_sex_er32000_and_derived_income_year_age_family_file_"
            "spouse_age_and_sex_slot_metadata_only"
        ),
    ),
    "amendment_3_spouse_retirement_crosswalk": _ruled(
        _AMENDMENTS["3"],
        ruling="ratified_as_written",
        rule="non_executable_metadata_components_counted_once_in_money_income",
    ),
    "amendment_4_wealth_accuracy_flags": _ruled(
        _AMENDMENTS["4"],
        ruling="ratified_as_written",
        rule="imputation_diagnostics_only_never_amounts_or_sample_inclusion",
    ),
    "amendment_5a_later_pension_routes": _ruled(
        _AMENDMENTS["5a"],
        ruling="ratified_as_written",
        previous_routes="income_concept.employer_dc.previous_routes",
    ),
    "amendment_5b_2015_checkpoint": _ruled(
        _AMENDMENTS["5b"],
        ruling="ratified_as_written",
        refused_branch=_AMENDMENTS["5b"]["fields"]["refused_branch"],
        off_route_disposition=_AMENDMENTS["5b"]["fields"][
            "off_route_disposition"
        ],
    ),
    "amendment_6_blocker_b3_2017_weight": _ruled(
        _AMENDMENTS["6"],
        ruling="use_the_released_weight_and_disclose",
        weight=_AMENDMENTS["6"]["fields"]["variable"],
        registration_discloses=(
            "weights:2017.cross_section_weight.registration_disclosure"
        ),
    ),
    "psid_documentary_questions": {
        "ruling": "send_all_three_now_as_a_held_draft_for_max",
        "sent_on": "2026-09-30",
        "answered_on": "2026-10-07",
        "research_record": "docs/design/u2_m1b_psid_research.md",
        "specification_section": "16b",
        "decision_record": "d637",
        "ruled_on": "2026-09-30",
    },
    # d1090 (2026-10-10): section 16c.
    "blocker_b1_male_code_20_2015": _excluded(
        sources.MALE_CODE_20_2015,
        ruling="exclude_and_disclose",
        supersedes="d637_hold_for_psid",
        disclosed_count=(
            "persons_recorded_male_with_2015_code_20_in_family_units_that_"
            "would_otherwise_supply_an_observation"
        ),
        count_decides="nothing",
    ),
    "blocker_b2_codes_90_92_2019_2023": _excluded(
        sources.UNCOOPERATIVE_SPOUSE_OR_PARTNER,
        ruling="exclude_and_disclose",
        supersedes="d637_hold_for_psid",
        disclosed_count=(
            "persons_with_code_90_or_92_in_2019_2021_2023_family_units_"
            "that_would_otherwise_supply_an_observation"
        ),
        count_decides="nothing",
    ),
    "amendment_5c_u7_2015_spouse_slot": {
        "ruling": "follows_blocker_b1",
        "registry_entries": ["pension:2015.route.respondent_slots"],
        "option": "1d-2",
        "specification_section": "16c",
        "decision_record": "d1090",
        "ruled_on": "2026-10-10",
    },
    # d1242 (2026-10-16): recorded in section 19.
    "b2_disclosed_count": {
        "ruling": (
            "persons_with_code_90_or_92_in_2019_2021_2023_family_units_that_"
            "would_otherwise_supply_an_observation"
        ),
        "person_counted_exclusions": list(sources.PERSON_COUNTED_EXCLUSIONS),
        "disclosed_per_row": ["per_wave", "distinct_persons"],
        "count_decides": "nothing",
        "specification_section": "19",
        "decision_record": "d1242",
        "ruled_on": "2026-10-16",
    },
    # d1597 (2026-10-16): section 13's optional structure-only U1 load,
    # run before each step-4 pass (d1649's condition, which d1724's rerun
    # keeps).
    "u1_input_pin_check": {
        "ruling": "run_the_optional_structure_only_u1_load_before_step_4",
        "u1_input_frames_sha256": _U1_INPUT_FRAMES_SHA256,
        "statistic_computed": None,
        "authorization_used": [
            {
                "on": "2026-10-19",
                "head": _STEP_4_FIRST_HEAD,
                "before": "the_d1649_pass",
                "result": "pin_matched",
            },
            {
                "on": "2026-10-21",
                "head": _STEP_4_SECOND_HEAD,
                "before": "the_d1724_pass",
                "result": "pin_matched",
            },
        ],
        "specification_section": "13",
        "decision_record": "d1597",
        "ruled_on": "2026-10-16",
    },
    # d1649 (2026-10-16): the section 20 step-4 pass.
    "preregistration_pass": {
        "ruling": "authorize_the_step_4_pass_once",
        "scope": [
            "structural_counts",
            "dispositions",
            "join_and_reconciliation_counts",
            "named_f17_component_summaries",
        ],
        "not_computed": [
            "income_concept",
            "poverty_threshold_assignment",
            "poverty_status",
        ],
        "registered_run_frame_environment": (
            "the_preregistration_evidence_pandas_version_and_string_"
            "inference_setting"
        ),
        "authorization_used": [
            {
                "on": "2026-10-19",
                "head": _STEP_4_FIRST_HEAD,
                "result": "stopped_in_the_birth_law_without_output",
            }
        ],
        "specification_section": "20",
        "decision_record": "d1649",
        "ruled_on": "2026-10-16",
    },
    # d1724 (2026-10-19; widening approved 2026-10-20): section 16d.
    "seed_birth_year_support": {
        "ruling": "count_out_or_reseed_before_the_birth_law_then_rerun_once",
        "support": [career.DERIVED_BIRTH_MIN, career.DERIVED_BIRTH_MAX],
        "counted_out": list(cohort.SEED_BIRTH_COUNTED_OUT),
        "disclosure_keys": [
            "n_seed_birth_year_counted_out",
            "n_seed_birth_year_reseeded",
        ],
        "count_decides": "nothing",
        "estimates_career": "unchanged",
        "widening_approved_on": "2026-10-20",
        "authorization_used": [
            {
                "on": "2026-10-21",
                "head": _STEP_4_SECOND_HEAD,
                "tests_run": _STEP_4_SECOND_TESTS_RUN,
                "result": "completed",
            }
        ],
        "specification_section": "16d",
        "decision_record": "d1724",
        "ruled_on": "2026-10-19",
    },
}
_RULED_ON = "2026-09-28"
#: Every decision the rulings record must cover (section 20 step 5).
RULING_DECISIONS: tuple[str, ...] = (
    "d514",
    "d637",
    "d745",
    "d1090",
    "d1242",
    "d1597",
    "d1649",
    "d1724",
)
_BLOCK_SECTION = "\n## 15. Machine-readable parameter block"


def _no_repeated_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """A JSON object, refused if it names a key twice: ``json.loads``
    would keep the last silently, so an earlier draft value could stand
    in the text while the check saw the later one."""

    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"the section 15 block repeats keys {repeated}")
    return dict(pairs)


def specification_block(
    path: Path = identity.SPECIFICATION_PATH,
) -> dict[str, Any]:
    """The U2 specification's machine-readable JSON block (section 15).

    Only section 15 is searched, and it must hold exactly one JSON block,
    in which no object may name a key twice.
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
    block = json.loads(blocks[0], object_pairs_hook=_no_repeated_keys)
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


def check_rulings_against_code(
    registries: sources.RegistrySet | None = None,
) -> dict[str, Any]:
    """Hold :data:`U2_RULINGS` to the code and the committed registries.

    Every decision in :data:`RULING_DECISIONS` has an entry and no entry
    names another; each registry entry a ruling names exists, is RESOLVED
    and records that ruling's decision (and option, for d1090); the d637
    entries are exactly the registry module's ratified scopes, and each
    d1090 exclusion names exactly the role entries that carry it in the
    committed roles registry; B2's disclosed count is a person count the
    structural pass makes (d1242); and the d1724 support and reasons are
    the cohort code's.  Refuses on the first difference.
    """

    registries = (
        sources.RegistrySet.committed() if registries is None else registries
    )
    named = sorted(
        {entry["decision_record"] for entry in U2_RULINGS.values()}
        | {
            entry["confirmed_by"]
            for entry in U2_RULINGS.values()
            if "confirmed_by" in entry
        },
        key=lambda d: int(d[1:]),
    )
    if named != list(RULING_DECISIONS):
        raise ValueError(
            f"the rulings record names {named}, not {list(RULING_DECISIONS)}"
        )
    by_id = {
        name: {entry["id"]: entry for entry in registries.entries(name)}
        for name in _registry.REGISTRY_NAMES
    }
    for key, entry in U2_RULINGS.items():
        for reference in entry.get("registry_entries", ()):
            name, entry_id = reference.split(":", 1)
            found = by_id.get(name, {}).get(entry_id)
            if found is None or found.get("status") != "RESOLVED":
                raise ValueError(
                    f"{key}: {reference} is not a RESOLVED registry entry"
                )
            recorded = found.get("ruling") or {}
            if recorded.get("decision") != entry["decision_record"]:
                raise ValueError(
                    f"{key}: {reference} records "
                    f"{recorded.get('decision')!r}, not "
                    f"{entry['decision_record']!r}"
                )
            if "option" in entry and recorded.get("option") != entry["option"]:
                raise ValueError(f"{key}: {reference} records another option")
    applied = sorted(
        reference
        for entry in U2_RULINGS.values()
        if entry["decision_record"] == "d637"
        for reference in entry.get("registry_entries", ())
    )
    scoped = sorted(
        f"{scope['registry']}:{entry}"
        for scope in _AMENDMENTS.values()
        for entry in scope["entries"]
    )
    if applied != scoped:
        raise ValueError(
            "the d637 entries differ from the registry's ratified scopes: "
            f"{sorted(set(applied) ^ set(scoped))}"
        )
    for disposition in sources.FAMILY_UNIT_EXCLUSIONS:
        entry = next(
            e
            for e in U2_RULINGS.values()
            if e.get("disposition") == disposition
        )
        carrying = sorted(
            f"roles:{role['id']}"
            for role in registries.entries("roles")
            if (role.get("family_unit_exclusion") or {}).get("disposition")
            == disposition
        )
        if carrying != sorted(entry["registry_entries"]):
            raise ValueError(
                f"{disposition!r}: the roles registry carries it on "
                f"{carrying}, the rulings record on {entry['registry_entries']}"
            )
    if set(sources.PERSON_COUNTED_EXCLUSIONS) != set(
        sources.FAMILY_UNIT_EXCLUSIONS
    ) or U2_RULINGS["b2_disclosed_count"]["person_counted_exclusions"] != (
        list(sources.PERSON_COUNTED_EXCLUSIONS)
    ):
        raise ValueError("B2's disclosed person count is not made (d1242)")
    support = U2_RULINGS["seed_birth_year_support"]
    if support["support"] != [
        career.DERIVED_BIRTH_MIN,
        career.DERIVED_BIRTH_MAX,
    ] or support["counted_out"] != list(cohort.SEED_BIRTH_COUNTED_OUT):
        raise ValueError("the d1724 support or reasons differ from the code")
    return {
        "decisions": list(RULING_DECISIONS),
        "entries": len(U2_RULINGS),
        "rulings_equal_the_code": True,
    }


def _relative(path: Path) -> str:
    return str(Path(path).resolve().relative_to(identity.ROOT))


def _existing(relative: str) -> str:
    """``relative``, refused unless it names a file in the repository."""

    if not (identity.ROOT / relative).is_file():
        raise ValueError(f"the block names {relative}, which does not exist")
    return relative


def _registry_variable(
    entries: Mapping[str, Mapping[str, Any]], entry_id: str
) -> str:
    entry = entries[entry_id]
    if entry.get("status") != "RESOLVED":
        raise ValueError(f"{entry_id} is not RESOLVED")
    return str(entry["variable"])


def _block_row(row: U2Row) -> dict[str, Any]:
    """A row as the section 15 block writes it (the inverse of
    :func:`_parse_block_row`)."""

    inverse = {
        (target, name, override): (key, value)
        for (key, value), (target, name, override) in (
            _BLOCK_KEY_OVERRIDES.items()
        )
    }
    entry: dict[str, Any] = {}
    for target, overrides in (("cohort", row.cohort), ("income", row.income)):
        for name, value in overrides.items():
            key, written = inverse.get((target, name, value), (name, value))
            entry[key] = written
    return entry


def expected_specification_block(
    registries: sources.RegistrySet | None = None,
) -> dict[str, Any]:
    """The complete section 15 block as the code states it.

    Every value the code holds comes from the code: the identity, plans,
    support waves and their registry variables, the income-concept,
    annuity, threshold, cut and SSI parameters and their capture pins,
    the cells, floor and design settings, the memo rules, the rows, the
    entry points, the pre-registration evidence pin, the labels and U2's
    rulings record.  The descriptive
    values the code does not otherwise hold (the Report's citation, the
    unit and financial-asset definitions, the comparator boundary, the
    cleared extracts' hashes and the wording keys) are written here once,
    so that :func:`check_block_against_code` holds the whole block, not
    only its executable part.
    """

    registries = (
        sources.RegistrySet.committed() if registries is None else registries
    )
    individual = {e["id"]: e for e in registries.entries("individual")}
    wealth = {e["id"]: e for e in registries.entries("wealth")}
    design = {e["id"]: e for e in registries.entries("design")}
    pension = registries.entries("pension")
    if any(entry.get("status") != "RESOLVED" for entry in pension):
        raise ValueError("a pension registry entry is not RESOLVED")
    spec = U2IncomeSpec()
    population = U2CohortSpec()
    tabulated = tabulation.U2TabulationConfig().as_dict()
    refused = _AMENDMENTS["5b"]
    (refused_wave,) = {
        entry["wave"] for entry in pension if entry["id"] in refused["entries"]
    }
    reader = inspect.getsourcefile(sources.employer_dc_balances)
    thresholds = parameters.load_u2_thresholds()
    ssi = parameters.load_u2_ssi_parameters()
    return {
        "specification": identity.SPECIFICATION_ID,
        "target_id": identity.TARGET_ID,
        "version": SPECIFICATION_VERSION,
        "status": SPECIFICATION_STATUS,
        "inherits": {
            "file": _relative(identity.U1_SPECIFICATION_PATH),
            "version": _U1_VERSION,
            "sha256": identity.U1_SPECIFICATION_SHA256,
        },
        "claim_class": {"class": U2_RULINGS["claim_class"]["ruling"]},
        "target": {
            "report": (
                "Butrica and Uccello (2004), How Will Boomers Fare at "
                "Retirement?, AARP PPI #2004-05"
            ),
            "tables": ["19", "21"],
            "column": identity.COMPARATOR_COLUMN,
            "birth_years": [identity.BIRTH_YEARS[0], identity.BIRTH_YEARS[-1]],
            "age": identity.TARGET_AGE,
            "cut_rate": spec.cut_rate,
            "report_rows": len(tabulation.REPORT_ROWS)
            + sum(
                len(entry["rows"])
                for entry in tabulation.NOT_COMPUTED_REPORT_ROWS.values()
            ),
            "unit": "individual_with_household_income_and_wealth_including_"
            "spouse",
            "financial_assets": "non_pension_wealth_plus_ira_keogh_401k_"
            "balances",
            "comparator_values": "sealed_comparator_side_not_opened_by_"
            "builder",
            "printed_precision": "whole_numbers",
            "definitions_extract": [
                {
                    "file": "EVID/exercise2-definitions-cleared-20260924.md",
                    "sha256": "a3978b683b4275424b6d12e9fe45f021fae277ccf9"
                    "731a7883952564b6ed0384",
                },
                {
                    "file": "EVID/u2-target-availability-cleared-20260928.md",
                    "sha256": "2ffa3092d297418c58868f7e5326c3e4c8047b1291"
                    "71b40b66fde5ee07702211",
                },
            ],
        },
        "population": {
            "primary_row": HEADLINE_ROW,
            "headline": {"rule": HEADLINE_RULE, "fallback_row": None},
            "support_waves": list(cohort.SUPPORT_WAVES),
            "primary_waves": list(cohort.PRIMARY_WAVES),
            "primary_birth_years": list(cohort.PRIMARY_BIRTH_YEARS),
            "u1_birth_years": [
                cohort.ALL_BIRTH_YEARS[0],
                cohort.ALL_BIRTH_YEARS[-1],
            ],
            "u1_even_birth_year_weight": cohort.U1_EVEN_BIRTH_YEAR_WEIGHT,
            "u1_single_observation_weight": (
                cohort.U1_SINGLE_OBSERVATION_WEIGHT
            ),
            "u1_even_birth_ages": list(cohort.U1_EVEN_BIRTH_AGES),
            "missing_observation_reweighting": (
                population.missing_observation_reweighting
            ),
            "waves": {
                str(wave): {
                    "income_year": wave - 1,
                    "weight": _registry_variable(individual, f"{wave}.weight"),
                    "family_unit_id": _registry_variable(
                        individual, f"{wave}.interview"
                    ),
                    "wealth1": _registry_variable(
                        wealth, f"wealth.{wave}.wealth1"
                    ),
                    "wealth_source": "family_file",
                }
                for wave in cohort.SUPPORT_WAVES
            },
            "presence": population.presence,
            "birth_year_law": (
                f"estimates.career.{career.derive_birth_years.__name__}"
            ),
            "seed_wave_rule": population.seed_wave_rule,
            "separated_is_married": population.separated_is_married,
            "unresolved_marital_status": population.unresolved_marital_status,
            "annuitant_age_source": population.annuitant_age_source,
            "institution_income_rule": population.institution_income_rule,
            "relationship_rules": (
                "section_3_role_amendment_with_section_16a_amendment_1"
            ),
            "relationship_codes_tested": list(sources.RELATIONSHIP_CODES),
            "design": {
                "stratum": _registry_variable(design, "common.stratum"),
                "cluster": _registry_variable(design, "common.cluster"),
            },
        },
        "income_concept": {
            "income_unit": spec.income_unit,
            "money_income": "TOTAL FAMILY INCOME",
            "asset_income_rule": spec.asset_income_rule,
            "asset_income_items": list(family_income.ASSET_INCOME_CONCEPTS),
            "retirement_account_income_rule": (
                spec.retirement_account_income_rule
            ),
            "retirement_account_income_items": list(
                ap.RETIREMENT_ACCOUNT_INCOME_CONCEPTS
            ),
            "farm_asset_share": spec.farm_asset_share,
            "farm_loss": ap.FARM_LOSS_RULE,
            "financial_assets": spec.financial_assets,
            "employer_dc": {
                "row": "U7",
                "reader": str(
                    Path(reader)
                    .resolve()
                    .relative_to(identity.ROOT / "src" / "populace_dynamics")
                ),
                "persons": list(sources.DC_PERSONS),
                "role_meaning": (
                    "reference_person_and_designated_spouse_income_slot"
                ),
                "current_job": "account_amount_when_plan_type_has_an_account",
                "previous_plans": list(sources.DC_PLANS),
                "previous_routes": {
                    "both_items": ["both"],
                    "account_items_by_wave": {
                        str(wave): list(items)
                        for wave, items in (
                            sources.DECLARED_PREVIOUS_ACCOUNT_ITEMS.items()
                        )
                    },
                    "refused_branches": {
                        str(refused_wave): refused["fields"]["refused_branch"]
                    },
                },
                "unreported_amount": "zero_counted",
                "route_source": "later_wave_questionnaire_adjudication",
                "later_wave_mapping_status": (
                    "resolved_in_the_pension_registry_under_amendment_5"
                ),
                "counted_disposition": "left_to_accumulate",
                "excluded": [
                    "rolled_over_into_ira",
                    "both_plan_account_items_reasked",
                    refused["fields"]["off_route_disposition"],
                ],
                "top_code": "as_recorded",
                "brackets": "not_used",
            },
            "annuitized_share": spec.annuitized_share,
            "annuity": {
                "real_interest_rate": spec.real_interest_rate,
                "timing": spec.annuity_timing,
                "load": spec.annuity_load,
                "survivor_share": spec.survivor_share,
                "mortality_basis": spec.mortality_basis,
                "terminal_closure": spec.terminal_closure,
                "lives": spec.annuity_lives,
                "negative_wealth": spec.negative_wealth_rule,
            },
            "sensitivities_unscored": {
                key: list(value)
                for key, value in SENSITIVITIES_UNSCORED.items()
            },
        },
        "threshold": {
            "rule": spec.threshold_rule,
            "years": [
                parameters.REQUIRED_INCOME_YEARS[0],
                parameters.REQUIRED_INCOME_YEARS[-1],
            ],
            "required_income_years": list(parameters.REQUIRED_INCOME_YEARS),
            "values": "weighted_averages_as_printed_in_thresh_workbooks",
            "capture_status": "captured",
            "capture": {
                "file": _relative(parameters.THRESHOLDS_PATH),
                "sha256": parameters.THRESHOLDS_SHA256,
            },
            "overlap_2012": thresholds.provenance["overlap_2012"],
            "poor_if": "income_below_threshold",
        },
        "cut": {
            "rate": spec.cut_rate,
            "base": "all_social_security_of_the_unit",
            "behavior": "none",
            "start_year": spec.cut_start_year,
            "start_year_rule": ap.CUT_START_YEAR_RULE,
        },
        "ssi": {
            "rule": spec.ssi_rule,
            "deeming": spec.ssi_deeming,
            "ofum_unit": spec.ofum_ssi_unit,
            "parameters": {
                "file": _relative(parameters.SSI_PATH),
                "sha256": parameters.SSI_SHA256,
                "years": list(parameters.SSI_YEARS),
                "checked_against": "section_8_federal_register_cola_notices",
                "revision_rule": "refuse_missing_empty_or_unknown",
                "overlap_2012": ssi.provenance["overlap_2012"],
            },
        },
        "statistic": {
            "headline": "delta",
            "secondary": ["baseline_rate", "reform_rate"],
            "unit": "percentage_points",
        },
        "cells": {
            "column": identity.COMPARATOR_COLUMN,
            "scored": list(tabulation.DEFAULT_CELLS),
            "secondary": list(tabulation.OPTIONAL_CELLS),
            "diagnostic": "birth_year",
            "report_labels": "tables_19_21_stub_labels_cleared_extract",
            "unclassified_marital_cells": (
                tabulated["unclassified_marital_cells"]
            ),
            "not_computed": list(tabulation.NOT_COMPUTED_REPORT_ROWS),
        },
        "uncertainty": {
            "draws": tabulated["draws"],
            "floor": {
                "seeds": tabulated["floor_seeds"],
                "fraction": ut.FLOOR_FRACTION,
                "split_unit": ut.FLOOR_SPLIT_UNIT,
                "summary": ["mean", "sample_sd"],
                "min_usable_seeds": ut.MIN_FLOOR_SEEDS,
            },
            "design_se": {
                "method": "taylor_linearization",
                "domain": tabulated["design_se_domain"],
                "outside_cell": "zero",
                "singleton_strata": "excluded_counted_and_listed",
            },
        },
        "comparison": {
            "gap": "model_minus_report",
            "comparator_interval": memo.INTERVAL_ID,
            "acceptance": {
                "rule": U2_RULINGS["comparison_publication"]["acceptance_rule"]
            },
            "memo_small_cells": {
                "flag_unweighted_n_below": memo.SMALL_CELL_THRESHOLD,
                "unweighted_n": "n_observations",
                "no_switcher_cell": memo.NO_SWITCHER_WORDING.replace(" ", "_"),
            },
        },
        "rows": {
            row_id: _block_row(row) for row_id, row in REGISTERED_ROWS.items()
        },
        "diagnostics_f17": {
            "row": "headline",
            "official_concept_poverty_rate": "registered_run_only",
            "components": [
                "social_security",
                "ssi",
                "wealth1",
                "fu_size_record_counts",
            ],
            "component_timing": "permitted_before_registration",
            "social_security_published": (
                "ssa_supplement_2025_table_5a4_december_retired_workers"
            ),
            "ssi_published": "federal_benefit_rate_capture_only",
            "wealth1_published": None,
        },
        "entry_points": {
            "dry_run": _existing("scripts/track_u2_dry_run.py"),
            "registered_run": _existing("scripts/run_track_u2_registered.py"),
            "registered_artifact": _relative(identity.ARTIFACT_PATH),
            "environment": _relative(identity.SIDECAR_PATH),
            "structure": _existing("scripts/track_u2_structure.py"),
            "component_diagnostics": _existing(
                "scripts/track_u2_component_diagnostics.py"
            ),
        },
        "preregistration_evidence": {
            "file": _relative(loader.PREREGISTRATION_EVIDENCE_PATH),
            "sha256": loader.PREREGISTRATION_EVIDENCE_SHA256,
            "schema_version": loader.PREREGISTRATION_SCHEMA,
            "written_by": _existing("scripts/track_u2_structure.py"),
            "authorized_by": U2_RULINGS["seed_birth_year_support"][
                "decision_record"
            ],
            "pinned_from": "EV/track-u2-step4-pass-20261021-run2/MANIFEST.md",
        },
        "acceptance_rule": None,
        "labels": list(ap.OUTPUT_LABELS),
        "decisions": {"ruled_by": "Max", "ruled_on": _RULED_ON, **U2_RULINGS},
        "blocked_by": [],
    }


def _differing_paths(
    observed: Any, expected: Any, path: str = ""
) -> list[str]:
    """The paths at which ``observed`` and ``expected`` differ, comparing
    keys, list lengths, types and values, each leaf as canonical JSON
    (``True`` is not ``1``, ``1`` is not ``1.0`` and ``-0.0`` is not
    ``0.0``)."""

    if isinstance(expected, Mapping) and isinstance(observed, Mapping):
        found: list[str] = []
        for key in sorted(set(observed) | set(expected), key=str):
            where = f"{path}.{key}" if path else str(key)
            if key not in observed or key not in expected:
                found.append(where)
            else:
                found += _differing_paths(observed[key], expected[key], where)
        return found
    if isinstance(expected, list) and isinstance(observed, list):
        if len(observed) != len(expected):
            return [path]
        found = []
        for index, (a, b) in enumerate(zip(observed, expected, strict=True)):
            found += _differing_paths(a, b, f"{path}[{index}]")
        return found
    if type(observed) is not type(expected) or observed != expected:
        return [path]
    if json.dumps(observed) != json.dumps(expected):
        return [path]
    return []


def check_block_against_code(
    block: Mapping[str, Any],
    registries: sources.RegistrySet | None = None,
) -> dict[str, Any]:
    """Refuse a section 15 block that differs from the code in any way.

    The block must equal :func:`expected_specification_block` exactly:
    the same keys at every level, the same list lengths and the same
    values of the same JSON types (equal under ``==`` and as canonical
    JSON).  The refusal names every differing path.
    """

    expected = expected_specification_block(registries)
    differing = _differing_paths(block, expected)
    if differing or _canonical(block) != _canonical(expected):
        raise ValueError(
            "the section 15 block differs from the code at "
            f"{differing or ['(canonical encoding)']}"
        )
    return {
        "specification_version": block["version"],
        "block_equals_code": True,
    }


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
