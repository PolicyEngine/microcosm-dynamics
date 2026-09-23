"""Configuration, registered rows and pending choices for the A5 assembly.

Every choice that awaits a ruling is an explicit field of
:class:`TrackAConfig`.  Where the plan
(``critical-path-cola-20260922.md`` section 6) or the draft A1
specification (``docs/design/urban2010_cola_comparison.md`` section 21)
proposes a default, the field defaults to it; where neither does, the
default is an A5 builder choice and :func:`pending_decisions` says so.
Nothing here is ratified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from populace_dynamics.engine.di_entitlement_rates import DIEntitlementSpec
from populace_dynamics.estimates.cola_age_profile import (
    MEAN_OF_INDIVIDUAL_RATIOS,
    PRIMARY_COMPONENTS,
    RATIO_OF_SCENARIO_MEANS,
    WORKERS_ONLY_COMPONENTS,
)
from populace_dynamics.scenario_benefits import (
    PLAN_PROPOSED_ANNUAL_REDUCTION,
    PLAN_PROPOSED_FIRST_REDUCED_DETERMINATION_YEAR,
    BenefitPeriod,
    ExposureClock,
)

__all__ = [
    "DRY_RUN_HEADER",
    "INVENTED_COHORT_LABEL",
    "REGISTERED_ROWS",
    "ROWS_NOT_BUILT",
    "TRACK_A_LABELS",
    "AuxiliaryEntitlementClock",
    "LevelPolicy",
    "RegisteredRow",
    "SpouseEntitlementRule",
    "SurvivorEntitlementRule",
    "TrackAConfig",
    "pending_decisions",
]

#: The labels every Track A output carries (plan section 4).
TRACK_A_LABELS: tuple[str, ...] = (
    "PSID-seeded closed cohort",
    "Python oracle (not Axiom)",
    "fixed-path mechanical incidence",
)
#: Replaces the PSID label on outputs built from the invented cohort.
INVENTED_COHORT_LABEL = (
    "INVENTED closed cohort in the PSID 2010 cohort schema (not PSID data)"
)
#: Heading of every dry-run output (task instruction).
DRY_RUN_HEADER = "INVENTED DATA - NOT A COMPARISON"


class LevelPolicy(str, Enum):
    """How a benefit level the oracle does not compute is supplied.

    ``DISCLOSED_ORACLE_APPROXIMATION`` reuses the oracle's retirement
    AIME and PIA functions (see
    :func:`populace_dynamics.cola_track_a.benefits.approximate_pia`);
    ``EXCLUDE`` leaves the PIA without a level.  A spouse's or
    widow(er)'s benefit resting on an excluded worker level is dropped
    and counted; a person whose own worker level is excluded is dropped
    whole (``person_excluded_own_level_unavailable``), because the own
    level decides dual entitlement.  The drop applies to every row, R3
    included, since A7 membership needs a positive baseline amount.  The
    A1 draft (section 22) says R3 could still include new DI awards
    under this alternative; the assembly does not implement that.
    """

    DISCLOSED_ORACLE_APPROXIMATION = "disclosed_oracle_approximation"
    EXCLUDE = "exclude"


class AuxiliaryEntitlementClock(str, Enum):
    """Which entitlement year starts an auxiliary's reform exposure (R2).

    ``AUXILIARY_OWN`` is the A1 draft's R2 (section 6): the auxiliary's
    own first entitlement year.  ``WORKER`` is the convention the A6
    module docstring fixes (the insured worker's entitlement year).  A1
    referee question 8 asks which is intended.
    """

    AUXILIARY_OWN = "auxiliary_own"
    WORKER = "worker"


class SurvivorEntitlementRule(str, Enum):
    """When a projected aged widow(er) becomes entitled (A5 choice)."""

    #: The later of the year of widowhood and the year of attaining the
    #: oracle's earliest aged-survivor claim age (60).
    EARLIEST_ELIGIBILITY = "earliest_eligibility"


class SpouseEntitlementRule(str, Enum):
    """When a projected spouse becomes entitled (A5 choice)."""

    #: The later of the spouse's own simulated claim year and the insured
    #: worker's entitlement year.
    OWN_CLAIM_NOT_BEFORE_WORKER = "own_claim_not_before_worker_entitlement"


@dataclass(frozen=True)
class RegisteredRow:
    """One registered row of the A1 draft (section 18)."""

    row_id: str
    field_changed: str | None
    first_reduced_determination_year: int
    exposure_clock: ExposureClock
    benefit_period: BenefitPeriod
    components: tuple[str, ...]
    headline_statistic: str

    @property
    def tabulation_benefit_period(self) -> str:
        """The A7 ``benefit_period`` label for this row."""
        if self.benefit_period is BenefitPeriod.DECEMBER:
            return "december_monthly_amount"
        return "calendar_year_payments"

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "field_changed": self.field_changed,
            "first_reduced_determination_year": (
                self.first_reduced_determination_year
            ),
            "exposure_clock": self.exposure_clock.value,
            "benefit_period": self.benefit_period.value,
            "benefit_scale": "annual_12_times_monthly",
            "components": list(self.components),
            "headline_statistic": self.headline_statistic,
        }


def _row(row_id: str, field_changed: str | None, **changes: Any):
    values: dict[str, Any] = {
        "first_reduced_determination_year": (
            PLAN_PROPOSED_FIRST_REDUCED_DETERMINATION_YEAR
        ),
        "exposure_clock": ExposureClock.ELIGIBILITY,
        "benefit_period": BenefitPeriod.CALENDAR_YEAR,
        "components": PRIMARY_COMPONENTS,
        "headline_statistic": RATIO_OF_SCENARIO_MEANS,
    }
    values.update(changes)
    return RegisteredRow(row_id=row_id, field_changed=field_changed, **values)


#: A1 draft section 18: each alternative differs from R0 in one field.
REGISTERED_ROWS: dict[str, RegisteredRow] = {
    "R0": _row("R0", None),
    "R1": _row(
        "R1",
        "first_reduced_increase",
        first_reduced_determination_year=2010,
    ),
    "R2": _row(
        "R2", "exposure_clock", exposure_clock=ExposureClock.ENTITLEMENT
    ),
    "R3": _row(
        "R3", "statistic", headline_statistic=MEAN_OF_INDIVIDUAL_RATIOS
    ),
    "R4": _row("R4", "benefit_period", benefit_period=BenefitPeriod.DECEMBER),
    "R5": _row("R5", "components", components=WORKERS_ONLY_COMPONENTS),
}
#: Registered rows this assembly cannot produce, with the reason.
ROWS_NOT_BUILT: dict[str, str] = {
    "R6": (
        "PSID 2009 wave (ER34046), 2008 -> 2030: the A3 builder "
        "(cohorts.psid2010) materializes the 2011 wave only, so R6 needs "
        "a 2009-wave cohort builder that does not exist"
    ),
}


@dataclass(frozen=True)
class TrackAConfig:
    """Every A5 assembly convention; see :func:`pending_decisions`."""

    start_year: int = 2010
    reference_year: int = 2030
    draw_indices: tuple[int, ...] = tuple(range(20))
    floor_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    rows: tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5")
    annual_reduction: float = PLAN_PROPOSED_ANNUAL_REDUCTION
    # --- A2 (TR2008) inputs -------------------------------------------
    tr2008_alternative: str = "intermediate"
    #: First determination year that takes the TR2008 rate (A1 section 21
    #: ``rate_path.baseline`` starts in 2008); earlier years keep the
    #: realized series, which enters levels only (A1 section 4 splice).
    tr2008_first_rate_year: int = 2008
    #: A2 ``mortality_improvement_ratio`` base year (A2 pending ruling).
    mortality_base_year: int = 2004
    # --- A3/A4/A5 conventions -----------------------------------------
    #: Plan A5: claiming uses the table rows at or before this year, so
    #: every projection year snaps to it.
    claim_table_max_year: int = 2008
    di_spec: DIEntitlementSpec = field(default_factory=DIEntitlementSpec)
    # --- plan section 6 decisions (A1 section 21 defaults) -------------
    claim_class: str = "track_a_reported_not_gated_psid_oracle"
    oracle_cola_horizon_extension_to_2030: bool = True
    di_benefit_level: LevelPolicy = LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
    acceptance_rule: str | None = None
    # --- A5 builder choices (no plan or A1 default exists) -------------
    preeligibility_death_level: LevelPolicy = (
        LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
    )
    auxiliary_entitlement_clock: AuxiliaryEntitlementClock = (
        AuxiliaryEntitlementClock.AUXILIARY_OWN
    )
    survivor_entitlement_rule: SurvivorEntitlementRule = (
        SurvivorEntitlementRule.EARLIEST_ELIGIBILITY
    )
    spouse_entitlement_rule: SpouseEntitlementRule = (
        SpouseEntitlementRule.OWN_CLAIM_NOT_BEFORE_WORKER
    )
    #: Opening-stock survivors at or above this 2010 age are labelled
    #: aged widow(er)s, younger ones disabled widow(er)s (A7 vocabulary).
    opening_aged_widow_min_age: int = 60
    #: A1 section 21 ``amounts.opening_stock_dime_floor``.
    opening_stock_dime_floor: bool = False

    def __post_init__(self) -> None:
        for name, enum in (
            ("di_benefit_level", LevelPolicy),
            ("preeligibility_death_level", LevelPolicy),
            ("auxiliary_entitlement_clock", AuxiliaryEntitlementClock),
            ("survivor_entitlement_rule", SurvivorEntitlementRule),
            ("spouse_entitlement_rule", SpouseEntitlementRule),
        ):
            object.__setattr__(self, name, enum(getattr(self, name)))
        draws = tuple(int(k) for k in self.draw_indices)
        if not draws or len(set(draws)) != len(draws) or min(draws) < 0:
            raise ValueError("draw_indices must be unique and non-negative")
        object.__setattr__(self, "draw_indices", tuple(sorted(draws)))
        unknown = [row for row in self.rows if row not in REGISTERED_ROWS]
        if unknown:
            raise ValueError(
                f"unknown or unbuildable rows {unknown}; buildable rows are "
                f"{sorted(REGISTERED_ROWS)} ({ROWS_NOT_BUILT})"
            )
        if self.reference_year <= self.start_year:
            raise ValueError("reference_year must follow start_year")
        if self.tr2008_first_rate_year > self.start_year:
            raise ValueError(
                "tr2008_first_rate_year must not follow the start year"
            )

    @property
    def n_periods(self) -> int:
        return self.reference_year - self.start_year

    def check_runnable(self) -> None:
        """Refuse settings under which Track A has nothing to compute."""
        if self.claim_class != "track_a_reported_not_gated_psid_oracle":
            raise ValueError(
                f"claim_class {self.claim_class!r} holds the first score for "
                "another track; this assembly computes Track A only"
            )
        if not self.oracle_cola_horizon_extension_to_2030:
            raise ValueError(
                "without decision 2(a) the oracle COLA path stops at 2022 "
                "and no 2030 benefit exists"
            )
        if self.acceptance_rule is not None:
            raise ValueError(
                "an acceptance rule was supplied, but this assembly applies "
                "none; A1 section 17 reports gaps only"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "start_year": self.start_year,
            "reference_year": self.reference_year,
            "periods": self.n_periods,
            "draw_indices": list(self.draw_indices),
            "draw_seed_convention": "5200 + k (engine.rng.DRAW_SEED_BASE)",
            "floor_seeds": list(self.floor_seeds),
            "rows": list(self.rows),
            "annual_reduction": self.annual_reduction,
            "tr2008_alternative": self.tr2008_alternative,
            "tr2008_first_rate_year": self.tr2008_first_rate_year,
            "mortality_base_year": self.mortality_base_year,
            "claim_table_max_year": self.claim_table_max_year,
            "di_spec": self.di_spec.as_dict(),
            "claim_class": self.claim_class,
            "oracle_cola_horizon_extension_to_2030": (
                self.oracle_cola_horizon_extension_to_2030
            ),
            "di_benefit_level": self.di_benefit_level.value,
            "acceptance_rule": self.acceptance_rule,
            "preeligibility_death_level": (
                self.preeligibility_death_level.value
            ),
            "auxiliary_entitlement_clock": (
                self.auxiliary_entitlement_clock.value
            ),
            "survivor_entitlement_rule": self.survivor_entitlement_rule.value,
            "spouse_entitlement_rule": self.spouse_entitlement_rule.value,
            "opening_aged_widow_min_age": self.opening_aged_widow_min_age,
            "opening_stock_dime_floor": self.opening_stock_dime_floor,
        }


_PLAN_SECTION_6 = "plan section 6 (Max has not ruled)"
_A5_BUILDER = "A5 builder choice; neither the plan nor the A1 draft names one"


def pending_decisions(config: TrackAConfig | None = None) -> list[dict]:
    """Each open A5 choice with the value used and where it comes from."""

    config = config or TrackAConfig()
    return [
        {
            "field": "claim_class",
            "value": config.claim_class,
            "default_source": "A1 section 21 decisions_awaiting_max",
            "alternatives": [
                "hold_for_track_b_m6_forward",
                "hold_for_track_c_axiom",
            ],
            "awaiting": _PLAN_SECTION_6 + ", decision 1",
        },
        {
            "field": "oracle_cola_horizon_extension_to_2030",
            "value": config.oracle_cola_horizon_extension_to_2030,
            "default_source": "A1 section 21 decisions_awaiting_max",
            "alternatives": [False],
            "awaiting": _PLAN_SECTION_6 + ", decision 2(a)",
        },
        {
            "field": "di_benefit_level",
            "value": config.di_benefit_level.value,
            "default_source": "A1 section 21 decisions_awaiting_max",
            "alternatives": [LevelPolicy.EXCLUDE.value],
            "awaiting": _PLAN_SECTION_6 + ", decision 2(b)",
            "note": (
                "under exclude, projected DI awards leave every row, R3 "
                "included; A1 section 22 says R3 could keep them, which "
                "this assembly does not implement"
            ),
        },
        {
            "field": "acceptance_rule",
            "value": config.acceptance_rule,
            "default_source": "A1 section 21 decisions_awaiting_max",
            "alternatives": ["numerical_rule_set_by_max_before_registration"],
            "awaiting": _PLAN_SECTION_6 + ", decision 3",
        },
        {
            "field": "preeligibility_death_level",
            "value": config.preeligibility_death_level.value,
            "default_source": (
                _A5_BUILDER + "; mirrors the decision 2(b) default because "
                "A6 routes it to the same kind of ruling"
            ),
            "alternatives": [LevelPolicy.EXCLUDE.value],
            "awaiting": "A1 ratification and a Max ruling",
        },
        {
            "field": "auxiliary_entitlement_clock",
            "value": config.auxiliary_entitlement_clock.value,
            "default_source": "A1 draft section 6, R2 text",
            "alternatives": [AuxiliaryEntitlementClock.WORKER.value],
            "awaiting": "A1 referee question 8",
        },
        {
            "field": "survivor_entitlement_rule",
            "value": config.survivor_entitlement_rule.value,
            "default_source": _A5_BUILDER,
            "alternatives": [],
            "awaiting": "A1 ratification",
        },
        {
            "field": "spouse_entitlement_rule",
            "value": config.spouse_entitlement_rule.value,
            "default_source": _A5_BUILDER,
            "alternatives": [],
            "awaiting": "A1 ratification",
        },
        {
            "field": "opening_aged_widow_min_age",
            "value": config.opening_aged_widow_min_age,
            "default_source": (
                _A5_BUILDER + "; A1 section 11 lists aged widow(er)s from "
                "60 and disabled widow(er)s under 60"
            ),
            "alternatives": [],
            "awaiting": "A1 ratification",
        },
        {
            "field": "mortality_base_year",
            "value": config.mortality_base_year,
            "default_source": "A2 PENDING_RULINGS base_year default",
            "alternatives": [2007],
            "awaiting": "A2 ruling (A1 section 15 substitute)",
        },
        {
            "field": "claim_table_max_year",
            "value": config.claim_table_max_year,
            "default_source": "plan item A5 (<=2008 PMF snap)",
            "alternatives": [],
            "awaiting": "A1 ratification",
        },
    ]
