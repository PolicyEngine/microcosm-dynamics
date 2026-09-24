"""Configuration, registered rows F0-F8 and pending decisions (exercise 3).

Every exercise-3 convention is an explicit field of :class:`FRA68Config`.
Nothing here is ratified.  Two kinds are kept apart:

* **Decisions awaiting Max** (decision record d188, open; plan
  ``critical-path-fra68-20260923.md`` section 11): the claim class, the
  oracle's scope (the FRA-schedule override, the per-cohort survivor
  reduction span and the carried-over DI-level approximation), the two
  other exercise-1 rulings E1 relies on (the oracle COLA horizon, d074
  decision 2(a), and the opening-stock basis, d075), the acceptance rule,
  the primary phase-in schedule and the registered row set.  Each is a
  field whose default is the plan's recommendation;
  :func:`pending_decisions` lists them with the configured value.  The
  survivor span and the two carry-overs are not named in d188 as filed
  (``named_in_d188_as_filed``; E1 referee report, required change 7).  A
  ``registered_real`` run refuses to start while any is open
  (:mod:`~populace_dynamics.fra68_track.runner`).
* **Builder conventions** that no ruling covers yet (the C1 anchor age,
  the survivor mapping of row F0, the claim age the claiming transforms
  read, the union statistic of F3/F4): :func:`builder_defaults` lists
  each with its source and the referee question of the E1 specification
  (``docs/design/urban2010_fra68_comparison.md``) that asks about it.

The A7 tabulation conventions E1 fixes (statistic, membership, age,
benefit period, components, draws and floor) are :data:`E1_RULINGS`,
exercise 3's :class:`~populace_dynamics.estimates.cola_age_profile.
SpecificationRulings` table: every exercise-3 tabulation records them
against the E1 block header, which also decides whether each is fixed by
a ratified E1 or still awaits ratification.

The projection conventions (TR2008 inputs, mortality, DI, the claim table,
the benefit-level and auxiliary rules) are Track A's, ruled or ratified
for exercise 1 (``cola_track_a.config``); :meth:`FRA68Config.
track_a_config` builds the Track A configuration the shared projection
runs under.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from populace_dynamics.cola_track_a.config import (
    INVENTED_COHORT_LABEL,
    OPENING_STOCK_BASIS,
    POPULATIONS,
    TRACK_A_LABELS,
    LevelPolicy,
    Population,
    TrackAConfig,
)
from populace_dynamics.engine.di_entitlement_rates import DIEntitlementSpec
from populace_dynamics.estimates.cola_age_profile import (
    DEFAULT_DRAW_INDICES,
    DEFAULT_FLOOR_SEEDS,
    FAMILY_UNIT,
    FLAGGED_RECIPIENT_INCLUDING_ZERO,
    MEAN_OF_INDIVIDUAL_RATIOS,
    POSITIVE_BENEFIT,
    PRIMARY_COMPONENTS,
    RATIO_OF_SCENARIO_MEANS,
    SCENARIO_SPECIFIC,
    WORKERS_ONLY_COMPONENTS,
    SpecificationRulings,
)
from populace_dynamics.fra68_track.reform import (
    PLAN_RECOMMENDED_PRIMARY_SCHEDULE,
    SCHEDULE_ORDER,
    SCHEDULES,
)

__all__ = [
    "DRY_RUN_HEADER",
    "E1_RATIFICATION",
    "E1_RULINGS",
    "FRA68_LABELS",
    "INVENTED_COHORT_LABEL",
    "MECHANICAL_INCIDENCE_LABEL",
    "PENDING_DECISIONS",
    "SPECIFICATION_ID",
    "STATISTIC_ID",
    "STYLIZED_RESPONSE_LABEL",
    "TRACK_A_ROW_BY_WAVE",
    "ClaimingResponse",
    "FRA68Config",
    "FRA68Row",
    "SurvivorRetirementAge",
    "builder_defaults",
    "decision_value",
    "pending_decisions",
    "registered_rows",
    "row_labels",
]

#: The A7 statistic identifier of exercise 3 (plan section 8, item 4).
STATISTIC_ID = "dynasim_exercise3_fra68_reference_year_age_profile"
#: The identifier of the E1 specification's section 21 block
#: (``docs/design/urban2010_fra68_comparison.md``).
SPECIFICATION_ID = "urban2010_fra68_exercise3"
#: Heading of every dry-run output (task instruction).
DRY_RUN_HEADER = "INVENTED DATA - NOT A COMPARISON"
#: Plan section 12: every output carries the Track A labels.
FRA68_LABELS: tuple[str, ...] = TRACK_A_LABELS
MECHANICAL_INCIDENCE_LABEL = TRACK_A_LABELS[2]
#: Plan section 6: rows F3 and F4 replace the mechanical-incidence label.
STYLIZED_RESPONSE_LABEL = (
    "fixed paths; stylized claiming response (registered sensitivity)"
)
#: The Track A row whose population and benefit period each anchor wave
#: reads: R0 (2011 wave, opening 2010) and R6 (2009 wave, opening 2008).
#: Both use the eligibility clock and calendar-2030 payments; exercise 3
#: applies no COLA reform, so neither clock nor first reduced increase
#: enters any amount.
TRACK_A_ROW_BY_WAVE: dict[int, str] = {2011: "R0", 2009: "R6"}


class ClaimingResponse(str, Enum):
    """Plan section 6: how a projected retirement claim responds."""

    #: C0 (primary): every claimant keeps the projection's claim age.
    FIXED = "c0_fixed_claim_ages"
    #: C1: claimants whose claim age is at least the anchor age (the
    #: claim table's at-FRA age, 65 for the 2008 row) delay by the FRA
    #: increase, capped at 70.
    AT_OR_AFTER_ANCHOR_DELAY = "c1_claimants_at_or_after_anchor_delay"
    #: C2: every projected claimant delays by the FRA increase, capped at
    #: 70.
    ALL_DELAY = "c2_all_claimants_delay"


class SurvivorRetirementAge(str, Enum):
    """The widow(er)'s retirement age in a scenario (plan sections 3, 7)."""

    #: 416(l)(2): the scenario's worker schedule two cohorts earlier (F0,
    #: and the baseline of every row).
    STATUTORY_MAPPING = "statutory_416l2_mapping"
    #: F7's reform scenario: the baseline schedule two cohorts earlier (the
    #: reform reaches old-age and spouse's benefits only).
    UNCHANGED_FROM_BASELINE = "unchanged_from_baseline"
    #: Track A's fixed 84-month span (exercise 1).  Not registered for
    #: exercise 3; it exists for the null-reform identity test.
    TRACK_A_FIXED_84 = "track_a_fixed_84_months"


@dataclass(frozen=True)
class FRA68Row:
    """One registered row of the exercise-3 specification (plan section 7).

    ``schedule_id`` names the reform schedule; ``survivor_retirement_age``
    the reform scenario's survivor rule (the baseline always uses the
    statutory mapping on the baseline schedule).
    """

    row_id: str
    field_changed: str | None
    schedule_id: str
    survivor_retirement_age: SurvivorRetirementAge
    claiming_response: ClaimingResponse
    components: tuple[str, ...]
    headline_statistic: str
    anchor_wave: int = 2011

    @property
    def population(self) -> Population:
        return POPULATIONS[self.anchor_wave]

    @property
    def reform_key(self) -> tuple[int, str, str, str]:
        """Rows with the same key share one reform-scenario computation."""
        return (
            self.anchor_wave,
            self.schedule_id,
            self.survivor_retirement_age.value,
            self.claiming_response.value,
        )

    @property
    def behavior(self) -> str:
        if self.claiming_response is ClaimingResponse.FIXED:
            return "fixed_paths_shared_draws"
        return "fixed_paths_shared_draws_stylized_claiming_response"

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "field_changed": self.field_changed,
            "schedule": self.schedule_id,
            "survivor_retirement_age": self.survivor_retirement_age.value,
            "claiming_response": self.claiming_response.value,
            "statistic": self.headline_statistic,
            "components": list(self.components),
            "benefit_period": "calendar_2030_payments",
            "benefit_scale": "annual_12_times_monthly",
            "behavior": self.behavior,
            "population": self.population.as_dict(),
        }


def registered_rows(
    primary_schedule_id: str = PLAN_RECOMMENDED_PRIMARY_SCHEDULE,
) -> dict[str, FRA68Row]:
    """Rows F0-F8 (plan section 7) for a primary phase-in schedule.

    F0 is the headline row.  F1 and F2 hold the two other schedules in the
    order P1, P2, P3: under the plan's recommended primary P3 they are P1
    and P2, as the plan's table gives them.  Each alternative differs from
    F0 in one field.
    """

    if primary_schedule_id not in SCHEDULES:
        raise ValueError(
            f"unknown primary schedule {primary_schedule_id!r}; "
            f"expected one of {list(SCHEDULES)}"
        )
    others = [sid for sid in SCHEDULE_ORDER if sid != primary_schedule_id]
    base: dict[str, Any] = {
        "schedule_id": primary_schedule_id,
        "survivor_retirement_age": SurvivorRetirementAge.STATUTORY_MAPPING,
        "claiming_response": ClaimingResponse.FIXED,
        "components": PRIMARY_COMPONENTS,
        "headline_statistic": RATIO_OF_SCENARIO_MEANS,
        "anchor_wave": 2011,
    }

    def row(row_id: str, field_changed: str | None, **changes: Any):
        return FRA68Row(
            row_id=row_id,
            field_changed=field_changed,
            **{**base, **changes},
        )

    return {
        "F0": row("F0", None),
        "F1": row("F1", "fra_schedule", schedule_id=others[0]),
        "F2": row("F2", "fra_schedule", schedule_id=others[1]),
        "F3": row(
            "F3",
            "claiming_response",
            claiming_response=ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY,
        ),
        "F4": row(
            "F4",
            "claiming_response",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
        "F5": row(
            "F5", "statistic", headline_statistic=MEAN_OF_INDIVIDUAL_RATIOS
        ),
        "F6": row("F6", "components", components=WORKERS_ONLY_COMPONENTS),
        "F7": row(
            "F7",
            "survivor_retirement_age",
            survivor_retirement_age=(
                SurvivorRetirementAge.UNCHANGED_FROM_BASELINE
            ),
        ),
        "F8": row("F8", "population_and_vintage", anchor_wave=2009),
    }


def row_labels(row: FRA68Row, cohort_labels: tuple[str, ...]) -> tuple:
    """The labels of a row's outputs (plan section 12).

    The cohort's labels, with the mechanical-incidence label replaced by
    the stylized-response label for rows with a claiming response.
    """

    if row.claiming_response is ClaimingResponse.FIXED:
        return tuple(cohort_labels)
    return tuple(
        (
            STYLIZED_RESPONSE_LABEL
            if label == MECHANICAL_INCIDENCE_LABEL
            else label
        )
        for label in cohort_labels
    )


_D188 = "Max, decision record d188 (open; plan section 11)"
#: The survivor reduction span of E1 section 11 rule 5: exact by the
#: survivor's cohort (416(l)(2) mapping) in both scenarios, and exercise
#: 1's alternative, the oracle's fixed 84 months.
SURVIVOR_REDUCTION_SPAN = "exact_by_cohort_both_scenarios"
TRACK_A_SURVIVOR_REDUCTION_SPAN = SurvivorRetirementAge.TRACK_A_FIXED_84.value


#: Decisions awaiting Max for exercise 3 (d188; plan section 11).  Each
#: ``proposed_default`` is the plan's recommendation and the configuration
#: default; nothing here is ruled.
PENDING_DECISIONS: dict[str, dict[str, Any]] = {
    "claim_class": {
        "proposed_default": "track_a_reported_not_gated_psid_oracle",
        "alternatives": ["hold_for_track_b", "hold_for_track_c_axiom"],
        "awaiting": _D188 + ", item (a); plan item 1",
    },
    "oracle_fra_schedule_override": {
        "proposed_default": True,
        "alternatives": [False],
        "awaiting": _D188 + ", item (a); plan item 2(a)",
        "note": (
            "the reform runs as an override of SSAParameters."
            "fra_months_by_birth_year; it adds no statutory rule coverage. "
            "The per-cohort survivor reduction span the 416(l)(2) mapping "
            "needs is its own field (survivor_reduction_span)"
        ),
    },
    "survivor_reduction_span": {
        "proposed_default": SURVIVOR_REDUCTION_SPAN,
        "alternatives": [TRACK_A_SURVIVOR_REDUCTION_SPAN],
        "awaiting": (
            _D188 + ", item (a); plan item 2(a); not named in d188 as filed"
        ),
        "named_in_d188_as_filed": False,
        "note": (
            "an override of SSAParameters.survivor_reduction_period_months "
            "by the survivor's cohort (the 416(l)(2) mapping) in both "
            "scenarios; it adds no statutory rule coverage. It also changes "
            "baseline amounts relative to exercise 1 for survivors born "
            "before 1962 entitled after 60; exercise 1's fixed 84 months in "
            "both scenarios would keep the reform from reaching survivors' "
            "reduction at all (E1 referee question 7)"
        ),
    },
    "oracle_cola_horizon_extension_to_2030": {
        "proposed_default": True,
        "alternatives": [False],
        "awaiting": (
            _D188 + ", item (a); carries over d074 decision 2(a); not named "
            "in d188 as filed"
        ),
        "carries_over": "d074 decision 2(a)",
        "named_in_d188_as_filed": False,
        "note": (
            "the oracle COLA path runs to 2030 as a parameter override that "
            "adds no statutory coverage, as Max ruled for exercise 1; "
            "without it no 2030 benefit exists"
        ),
    },
    "opening_stock_basis": {
        "proposed_default": OPENING_STOCK_BASIS,
        "alternatives": ["rebased_on_later_simulated_events"],
        "awaiting": (
            _D188 + ", item (a); carries over d075 (A1 referee question "
            "11); not named in d188 as filed"
        ),
        "carries_over": "d075 referee question 11",
        "named_in_d188_as_filed": False,
        "note": (
            "an opening-stock person's benefit basis is frozen at the "
            "opening year (A1 section 11 rule 4), as Max ruled for exercise "
            "1; the only basis Track A implements"
        ),
    },
    "di_benefit_level": {
        "proposed_default": LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION.value,
        "alternatives": [LevelPolicy.EXCLUDE.value],
        "awaiting": _D188 + ", item (a); plan item 2(b)",
        "note": (
            "carries over exercise 1's ruling (d074, decision 2(b)); DI "
            "levels are weights only, and every DI ratio is 1"
        ),
    },
    "acceptance_rule": {
        "proposed_default": None,
        "alternatives": ["numerical_rule_set_by_max_before_registration"],
        "awaiting": _D188 + ", item (a); plan item 3",
    },
    "primary_schedule_id": {
        "proposed_default": PLAN_RECOMMENDED_PRIMARY_SCHEDULE,
        "alternatives": [
            sid
            for sid in SCHEDULE_ORDER
            if sid != PLAN_RECOMMENDED_PRIMARY_SCHEDULE
        ],
        "awaiting": _D188 + ", item (b); plan item 4",
        "note": "the other two schedules are registered as F1 and F2",
    },
    "rows": {
        "proposed_default": [f"F{index}" for index in range(9)],
        "alternatives": [],
        "awaiting": _D188 + ", item (b); plan item 4 (confirm F0-F8)",
    },
}


#: What ratifies E1 (E1 section 22 item 5): Max's ruling on d188 item
#: (c), ratifying the specification by merging.
E1_RATIFICATION = (
    "E1 specification ratification (decision record d188 item (c); E1 "
    "section 22 item 5)"
)
#: The A7 tabulation conventions the E1 specification fixes, each with
#: E1's proposed primary (what the runner passes to A7 for row F0), its
#: registered alternatives and the E1 section that fixes it.  Every
#: exercise-3 tabulation records its conventions against this table and
#: the E1 block header, not A1's: E1 follows A1's section numbering, but
#: its membership is scenario-specific, it registers no December-amount
#: row and the DI-level approximation awaits d188.  The E1 ratification
#: test also refuses a ``referee`` marker, on top of A7's markers (the
#: drafts' statuses were ``draft_for_referee_not_ratified`` and, after the
#: referee pass, ``draft_refereed_not_ratified``; the marker matches
#: both).  Nothing here is ratified: the tabulation derives each status
#: from the header.
E1_RULINGS = SpecificationRulings(
    specification=SPECIFICATION_ID,
    statistic_id=STATISTIC_ID,
    name="E1",
    ratification=E1_RATIFICATION,
    section_field="e1_section",
    extra_unratified_markers=("referee",),
    rulings=(
        {
            "parameter": "headline_statistic",
            "proposed_primary": RATIO_OF_SCENARIO_MEANS,
            "registered_alternatives": [MEAN_OF_INDIVIDUAL_RATIOS],
            "e1_section": "section 7 (F0) and section 18 (F5)",
            "note": (
                "both statistics are always computed; this sets which one "
                "is labelled primary (row F5 labels the mean of individual "
                "ratios primary)"
            ),
        },
        {
            "parameter": "recipient_rule",
            "proposed_primary": POSITIVE_BENEFIT,
            "registered_alternatives": [],
            "e1_section": "section 8",
            "note": (
                "E1 section 8 carries over A1 section 8: alive in the 2030 "
                "state of the draw with a positive benefit in the scenario; "
                f"{FLAGGED_RECIPIENT_INCLUDING_ZERO} is available, not "
                "registered"
            ),
        },
        {
            "parameter": "allow_membership_difference",
            "proposed_primary": True,
            "registered_alternatives": [],
            "e1_section": "section 7",
            "note": (
                "E1 section 7 makes membership scenario-specific: under "
                "the claiming responses C1 and C2 (rows F3, F4) the "
                "memberships can differ; under C0 they coincide, and the "
                "exercise-3 runner (not A7) refuses a C0 row whose "
                "memberships differ"
            ),
        },
        {
            "parameter": "membership_basis",
            "proposed_primary": SCENARIO_SPECIFIC,
            "registered_alternatives": [],
            "e1_section": "section 7",
            "note": (
                "E1 section 7: S_base is the set of baseline recipients "
                "and S_reform the set of reform recipients; under "
                "identical membership (C0) every basis gives the same sets"
            ),
        },
        {
            "parameter": "age_rule",
            "proposed_primary": "reference_year_minus_birth_year",
            "registered_alternatives": [],
            "e1_section": "section 9",
            "note": (
                "E1 section 9 carries over A1 section 9: age in the "
                "reference year is the reference year minus the birth "
                "year; no alternative is registered"
            ),
        },
        {
            "parameter": "benefit_period",
            "proposed_primary": "calendar_year_payments",
            "registered_alternatives": [],
            "e1_section": "section 10",
            "note": (
                "declared label only: the input amounts must already "
                "measure the declared period; the tabulation cannot check "
                "it. E1 section 10 registers no December-amount row (A1's "
                "R4), which in the annual model equals F0 up to dime "
                "flooring; december_monthly_amount is available, not "
                "registered"
            ),
        },
        {
            "parameter": "components",
            "proposed_primary": list(PRIMARY_COMPONENTS),
            "registered_alternatives": [list(WORKERS_ONLY_COMPONENTS)],
            "e1_section": "section 11 (F0) and section 18 (F6)",
            "note": (
                "component vocabulary is closed; unknown names are "
                "refused. DI benefit levels enter as the disclosed oracle "
                "approximation of exercise 1's ruling (d074 decision "
                "2(b)); whether it carries over to exercise 3 awaits Max "
                "(decision record d188 item (a); E1 section 22 item 2)"
            ),
        },
        {
            "parameter": "draw_indices",
            "proposed_primary": list(DEFAULT_DRAW_INDICES),
            "registered_alternatives": [],
            "e1_section": "section 16",
            "note": (
                "E1 section 16 carries over A1 section 16: K = 20 draws, "
                "mean and sample SD over draws"
            ),
        },
        {
            "parameter": "floor_seeds",
            "proposed_primary": list(DEFAULT_FLOOR_SEEDS),
            "registered_alternatives": [],
            "e1_section": "section 16",
            "note": "five-seed family-unit-disjoint half-split floor",
        },
        {
            "parameter": "floor_split_unit",
            "proposed_primary": FAMILY_UNIT,
            "registered_alternatives": [],
            "e1_section": "section 16",
            "note": (
                "E1 section 16 keeps each opening-wave family unit of the "
                "row's population on one side (ER34101 for the 2011 wave, "
                "ER34001 for row F8's 2009 wave; E1 section 14); person_id "
                "is available and not registered"
            ),
        },
    ),
)


@dataclass(frozen=True)
class FRA68Config:
    """Every exercise-3 convention; defaults are the plan's proposals."""

    reference_year: int = 2030
    draw_indices: tuple[int, ...] = tuple(range(20))
    floor_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    rows: tuple[str, ...] = tuple(f"F{index}" for index in range(9))
    # --- decisions awaiting Max (d188) ---------------------------------
    claim_class: str = "track_a_reported_not_gated_psid_oracle"
    oracle_fra_schedule_override: bool = True
    di_benefit_level: LevelPolicy = LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
    acceptance_rule: str | None = None
    primary_schedule_id: str = PLAN_RECOMMENDED_PRIMARY_SCHEDULE
    #: Not named in d188 as filed (E1 referee report, required change 7);
    #: each is runnable only at its proposed default.
    survivor_reduction_span: str = SURVIVOR_REDUCTION_SPAN
    oracle_cola_horizon_extension_to_2030: bool = True
    opening_stock_basis: str = OPENING_STOCK_BASIS
    # --- builder conventions (E1 referee questions) ----------------------
    #: C1 anchor: the claim table's at-FRA age for its 2008 row (plan
    #: section 6; E1 referee question 3).
    c1_anchor_age: int = 65
    # --- Track A projection conventions (exercise 1, carried over) ------
    tr2008_alternative: str = "intermediate"
    tr2008_first_rate_year: int = 2008
    mortality_base_year: int = 2004
    claim_table_max_year: int = 2008
    di_spec: DIEntitlementSpec = field(default_factory=DIEntitlementSpec)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "di_benefit_level", LevelPolicy(self.di_benefit_level)
        )
        draws = tuple(int(k) for k in self.draw_indices)
        if not draws or len(set(draws)) != len(draws) or min(draws) < 0:
            raise ValueError("draw_indices must be unique and non-negative")
        object.__setattr__(self, "draw_indices", tuple(sorted(draws)))
        object.__setattr__(self, "rows", tuple(self.rows))
        if not self.rows or len(set(self.rows)) != len(self.rows):
            raise ValueError("rows must be non-empty and unique")
        known = registered_rows(self.primary_schedule_id)
        unknown = [row for row in self.rows if row not in known]
        if unknown:
            raise ValueError(
                f"unknown rows {unknown}; registered rows are {sorted(known)}"
            )
        if not 62 <= int(self.c1_anchor_age) <= 70:
            raise ValueError("c1_anchor_age must lie in 62-70")

    @property
    def registered(self) -> dict[str, FRA68Row]:
        return registered_rows(self.primary_schedule_id)

    def row(self, row_id: str) -> FRA68Row:
        return self.registered[row_id]

    @property
    def anchor_waves(self) -> tuple[int, ...]:
        waves = [self.row(row).anchor_wave for row in self.rows]
        return tuple(dict.fromkeys(sorted(waves, reverse=True)))

    def rows_for_wave(self, anchor_wave: int) -> tuple[str, ...]:
        return tuple(
            row
            for row in self.rows
            if self.row(row).anchor_wave == anchor_wave
        )

    @property
    def schedule_ids(self) -> tuple[str, ...]:
        """Every schedule a configured row reads, in the order P1-P3."""
        used = {self.row(row).schedule_id for row in self.rows}
        return tuple(sid for sid in SCHEDULE_ORDER if sid in used)

    def track_a_config(self) -> TrackAConfig:
        """The Track A configuration the shared projection runs under.

        Its rows are R0 (2011 wave) and R6 (2009 wave) as the configured
        rows need them; the runner uses it for the projection, the
        parameter-consistency checks and the benefit conventions only.
        """

        rows = tuple(TRACK_A_ROW_BY_WAVE[wave] for wave in self.anchor_waves)
        return TrackAConfig(
            reference_year=self.reference_year,
            draw_indices=self.draw_indices,
            floor_seeds=self.floor_seeds,
            rows=rows,
            tr2008_alternative=self.tr2008_alternative,
            tr2008_first_rate_year=self.tr2008_first_rate_year,
            mortality_base_year=self.mortality_base_year,
            claim_table_max_year=self.claim_table_max_year,
            di_spec=self.di_spec,
            di_benefit_level=self.di_benefit_level,
            oracle_cola_horizon_extension_to_2030=(
                self.oracle_cola_horizon_extension_to_2030
            ),
            opening_stock_basis=self.opening_stock_basis,
        )

    def check_runnable(self) -> None:
        """Refuse settings under which exercise 3 has nothing to compute."""

        if (
            self.claim_class
            != PENDING_DECISIONS["claim_class"]["proposed_default"]
        ):
            raise ValueError(
                f"claim_class {self.claim_class!r} holds the first score for "
                "another track; this assembly computes the Track A class only"
            )
        if not self.oracle_fra_schedule_override:
            raise ValueError(
                "without the oracle FRA-schedule override (d188 item (a)) "
                "the reform has no implementation in this assembly"
            )
        if self.acceptance_rule is not None:
            raise ValueError(
                "an acceptance rule was supplied; the plan proposes none "
                "(d188 item (a)), and none may be set after registration"
            )
        if self.survivor_reduction_span != SURVIVOR_REDUCTION_SPAN:
            raise ValueError(
                f"survivor_reduction_span {self.survivor_reduction_span!r} "
                "is not implemented for exercise 3; this assembly spreads "
                "the widow(er) reduction over the survivor cohort's exact "
                f"span in both scenarios ({SURVIVOR_REDUCTION_SPAN!r}, E1 "
                "section 11 rule 5, awaiting Max)"
            )
        if not self.oracle_cola_horizon_extension_to_2030:
            raise ValueError(
                "without the oracle COLA horizon extension (d074 decision "
                "2(a), carried over pending d188) the oracle COLA path stops "
                "at 2022 and no 2030 benefit exists"
            )
        if self.opening_stock_basis != OPENING_STOCK_BASIS:
            raise ValueError(
                f"opening_stock_basis {self.opening_stock_basis!r} is not "
                "implemented; the assembly freezes the basis at the opening "
                f"year ({OPENING_STOCK_BASIS!r}, d075, carried over pending "
                "d188)"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_year": self.reference_year,
            "draw_indices": list(self.draw_indices),
            "draw_seed_convention": "5200 + k (engine.rng.DRAW_SEED_BASE)",
            "floor_seeds": list(self.floor_seeds),
            "rows": list(self.rows),
            "populations": {
                str(wave): POPULATIONS[wave].as_dict(self.reference_year)
                for wave in self.anchor_waves
            },
            "claim_class": self.claim_class,
            "oracle_fra_schedule_override": self.oracle_fra_schedule_override,
            "di_benefit_level": self.di_benefit_level.value,
            "acceptance_rule": self.acceptance_rule,
            "primary_schedule_id": self.primary_schedule_id,
            "survivor_reduction_span": self.survivor_reduction_span,
            "oracle_cola_horizon_extension_to_2030": (
                self.oracle_cola_horizon_extension_to_2030
            ),
            "opening_stock_basis": self.opening_stock_basis,
            "c1_anchor_age": self.c1_anchor_age,
            "tr2008_alternative": self.tr2008_alternative,
            "tr2008_first_rate_year": self.tr2008_first_rate_year,
            "mortality_base_year": self.mortality_base_year,
            "claim_table_max_year": self.claim_table_max_year,
            "di_spec": self.di_spec.as_dict(),
            "statistic_id": STATISTIC_ID,
        }


def _config_value(config: FRA68Config, name: str) -> Any:
    value = getattr(config, name)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


def decision_value(config: FRA68Config, name: str) -> Any:
    """A d188 decision field's configured value, in the block's vocabulary."""

    if name not in PENDING_DECISIONS:
        raise KeyError(f"{name!r} is not a d188 decision field")
    return _config_value(config, name)


def pending_decisions(config: FRA68Config | None = None) -> list[dict]:
    """The d188 decisions with the configured value; none is ruled."""

    config = config or FRA68Config()
    out = []
    for name, decision in PENDING_DECISIONS.items():
        value = _config_value(config, name)
        out.append(
            {
                "field": name,
                "value": value,
                **decision,
                "ruled": False,
                "is_proposed_default": value == decision["proposed_default"],
            }
        )
    return out


_BUILDER = "exercise-3 builder default; no ruling covers it"
_FIXED_BY = (
    "E1 ratification (Max merges the specification PR) and the issue #42 "
    "registration"
)


def builder_defaults(config: FRA68Config | None = None) -> list[dict]:
    """Each exercise-3 builder convention, with its source and question."""

    config = config or FRA68Config()
    return [
        {
            "field": "c1_anchor_age",
            "value": config.c1_anchor_age,
            "source": (
                _BUILDER + "; plan section 6: the at-FRA age of the claim "
                "table row the projection reads (fra_at.at_age of the 2008 "
                "row, 65 for both sexes)"
            ),
            "alternatives": ["the cohort's own FRA age"],
            "referee_question": 3,
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "survivor_retirement_age_f0",
            "value": SurvivorRetirementAge.STATUTORY_MAPPING.value,
            "source": (
                "plan section 3: 416(l)(2) applies the amended schedule to "
                "widow(er)s through the year they turn 60; F7 registers the "
                "alternative (unchanged)"
            ),
            "alternatives": [
                SurvivorRetirementAge.UNCHANGED_FROM_BASELINE.value
            ],
            "referee_question": 2,
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "claiming_transform_claim_age",
            "value": "realized_claim_age_claim_year_minus_birth_year_cap_70",
            "source": (
                _BUILDER + "; C1 and C2 transform the claim age Track A's "
                "factor reads (claim year minus birth year, at most 70). It "
                "equals the drawn plan age except for a plan drawn after "
                "its age had passed, which claims the next year"
            ),
            "alternatives": ["drawn_plan_age"],
            "referee_question": None,
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "stylized_response_statistic",
            "value": "ratio_of_scenario_means_scenario_specific_membership",
            "source": (
                "plan section 7: F3 and F4 use the headline statistic with "
                "scenario-specific membership; the ratio of weighted totals "
                "over the union of recipients is a reported diagnostic"
            ),
            "alternatives": ["ratio_of_weighted_totals_over_the_union"],
            "referee_question": 6,
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "opening_stock_factor_ratio",
            "value": "retired_worker_and_spouse_records_claimed_at_62_plus",
            "source": (
                "plan section 8: the observed opening-year amount times the "
                "component's reform-to-baseline age-factor ratio; 1 for "
                "disabled-worker and survivor records. A spouse's whole "
                "observed amount takes the spouse's ratio (it cannot be "
                "split into own and excess)"
            ),
            "alternatives": [],
            "referee_question": None,
            "fixed_by": _FIXED_BY,
        },
    ]
