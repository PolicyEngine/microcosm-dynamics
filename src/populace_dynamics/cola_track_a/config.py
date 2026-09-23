"""Configuration, registered rows, rulings and builder defaults (A5).

Every Track A convention is an explicit field of :class:`TrackAConfig`.
Two kinds are kept apart:

* **Max's rulings.**  Max ruled the plan's section 6 decisions 1-3
  (``critical-path-cola-20260922.md``; decision record d074) and A1
  referee question 11 (the opening-stock basis; d075) on 2026-09-23,
  adopting each proposed default (the A1 specification,
  ``docs/design/urban2010_cola_comparison.md`` sections 21-22, records
  them).  :data:`MAX_RULINGS` holds the ones that are assembly fields and
  :func:`max_rulings` reports, for a configuration, whether each field
  follows its ruling.  A ``registered_real`` run refuses a configuration
  that departs from one.  (Referee question 10, the page-3 contact, is a
  specification matter with no assembly field.)
* **Builder defaults.**  Conventions no ruling covers default to an A5
  builder choice (or to the A1 text where it speaks);
  :func:`builder_defaults` lists each with its source.  They are fixed
  only by A1 ratification and the issue #42 registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from populace_dynamics.cohorts.psid2010 import ANCHOR_LAYOUTS
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
    "MAX_RULINGS",
    "OPENING_STOCK_BASIS",
    "POPULATIONS",
    "REGISTERED_ROWS",
    "ROWS_NOT_BUILT",
    "TRACK_A_LABELS",
    "AuxiliaryEntitlementClock",
    "LevelPolicy",
    "Population",
    "RegisteredRow",
    "SpouseEntitlementRule",
    "SurvivorEntitlementRule",
    "TrackAConfig",
    "builder_defaults",
    "max_rulings",
    "rulings_departures",
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
    included, since A7 membership needs a positive baseline amount.
    A1 (section 22) says R3 could still include new DI awards
    under this alternative; the assembly does not implement that.
    """

    DISCLOSED_ORACLE_APPROXIMATION = "disclosed_oracle_approximation"
    EXCLUDE = "exclude"


class AuxiliaryEntitlementClock(str, Enum):
    """Which entitlement year starts an auxiliary's reform exposure (R2).

    ``AUXILIARY_OWN`` is A1's R2 (section 6): the auxiliary's
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
class Population:
    """A registered population of A1 section 14 (its ``population`` block).

    The anchor wave's income year is the opening year; the cohort is
    projected from it to the reference year.
    """

    anchor_wave: int
    weight_variable: str
    family_unit_variable: str
    born_max: int = 1980

    @property
    def start_year(self) -> int:
        return self.anchor_wave - 1

    def periods(self, reference_year: int) -> int:
        return reference_year - self.start_year

    def as_dict(self, reference_year: int = 2030) -> dict[str, Any]:
        return {
            "wave": self.anchor_wave,
            "weight": self.weight_variable,
            "born_max": self.born_max,
            "start_year": self.start_year,
            "periods": self.periods(reference_year),
            "family_unit_id": self.family_unit_variable,
        }


#: A1 sections 14 and 21: R0's 2011 wave and R6's 2009 wave, with the
#: variables the A3 layouts verify.
POPULATIONS: dict[int, Population] = {
    wave: Population(
        anchor_wave=wave,
        weight_variable=ANCHOR_LAYOUTS[wave].weight_variable,
        family_unit_variable=ANCHOR_LAYOUTS[wave].family_unit_variable,
    )
    for wave in (2011, 2009)
}


@dataclass(frozen=True)
class RegisteredRow:
    """One registered row of the A1 specification (section 18)."""

    row_id: str
    field_changed: str | None
    first_reduced_determination_year: int
    exposure_clock: ExposureClock
    benefit_period: BenefitPeriod
    components: tuple[str, ...]
    headline_statistic: str
    anchor_wave: int = 2011

    @property
    def population(self) -> Population:
        return POPULATIONS[self.anchor_wave]

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
            "population": self.population.as_dict(),
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


#: A1 section 18: each alternative differs from R0 in one field.
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
    "R6": _row("R6", "population_and_vintage", anchor_wave=2009),
}
#: Registered rows this assembly cannot produce, with the reason (none:
#: R6 projects the A3 2009-wave cohort).
ROWS_NOT_BUILT: dict[str, str] = {}
#: A1 section 11 rule 4 and Max's ruling on referee question 11 (d075):
#: an opening-stock person's benefit basis is frozen at the opening year.
OPENING_STOCK_BASIS = "fixed_at_opening_year"


@dataclass(frozen=True)
class TrackAConfig:
    """Every A5 assembly convention.

    :func:`max_rulings` reports the fields Max ruled on (2026-09-23) and
    :func:`builder_defaults` the others.
    """

    reference_year: int = 2030
    draw_indices: tuple[int, ...] = tuple(range(20))
    floor_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    rows: tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
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
    # --- plan section 6 decisions, ruled by Max 2026-09-23 (d074) -------
    claim_class: str = "track_a_reported_not_gated_psid_oracle"
    oracle_cola_horizon_extension_to_2030: bool = True
    di_benefit_level: LevelPolicy = LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
    acceptance_rule: str | None = None
    # --- A1 referee question 11, ruled by Max 2026-09-23 (d075) --------
    #: The only basis the assembly implements (A1 section 11, rule 4).
    opening_stock_basis: str = OPENING_STOCK_BASIS
    # --- A5 builder defaults (no ruling covers them) -------------------
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
    #: Opening-stock survivors at or above this age are labelled aged
    #: widow(er)s, younger ones disabled widow(er)s (A7 vocabulary): at
    #: the opening-year age for the opening record, and again at the
    #: reference-year age for the tabulated component.
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
        object.__setattr__(self, "rows", tuple(self.rows))
        if not self.rows or len(set(self.rows)) != len(self.rows):
            # A repeated row would add each draw's benefit rows to the
            # same tabulation input twice.
            raise ValueError("rows must be non-empty and unique")
        unknown = [row for row in self.rows if row not in REGISTERED_ROWS]
        if unknown:
            raise ValueError(
                f"unknown or unbuildable rows {unknown}; buildable rows are "
                f"{sorted(REGISTERED_ROWS)} ({ROWS_NOT_BUILT})"
            )
        if self.opening_stock_basis != OPENING_STOCK_BASIS:
            raise ValueError(
                f"opening_stock_basis {self.opening_stock_basis!r} is not "
                f"implemented; the assembly freezes the basis at the "
                f"opening year ({OPENING_STOCK_BASIS!r}, A1 section 11 rule "
                "4, ruled by Max on 2026-09-23, d075)"
            )
        start = min(self.start_years.values())
        if self.reference_year <= max(self.start_years.values()):
            raise ValueError("reference_year must follow every start year")
        if self.tr2008_first_rate_year > start:
            raise ValueError(
                "tr2008_first_rate_year must not follow the earliest start "
                f"year of the configured rows ({start})"
            )

    @property
    def anchor_waves(self) -> tuple[int, ...]:
        """The anchor waves the configured rows project, R0's first."""
        waves = [REGISTERED_ROWS[row].anchor_wave for row in self.rows]
        return tuple(dict.fromkeys(sorted(waves, reverse=True)))

    @property
    def start_years(self) -> dict[int, int]:
        """Opening year by anchor wave for the configured rows."""
        return {
            wave: POPULATIONS[wave].start_year for wave in self.anchor_waves
        }

    def rows_for_wave(self, anchor_wave: int) -> tuple[str, ...]:
        return tuple(
            row
            for row in self.rows
            if REGISTERED_ROWS[row].anchor_wave == anchor_wave
        )

    def check_runnable(self) -> None:
        """Refuse settings under which Track A has nothing to compute.

        Each refusal departs from a ruling of Max (2026-09-23, d074).
        ``di_benefit_level="exclude"`` departs from one too, but it still
        computes something, so it runs as an invented-data sensitivity and
        only a ``registered_real`` run refuses it
        (:func:`rulings_departures`).
        """
        if self.claim_class != "track_a_reported_not_gated_psid_oracle":
            raise ValueError(
                f"claim_class {self.claim_class!r} holds the first score for "
                "another track; Max ruled Track A the first scored "
                "comparison (d074) and this assembly computes Track A only"
            )
        if not self.oracle_cola_horizon_extension_to_2030:
            raise ValueError(
                "without the oracle COLA horizon extension (decision 2(a), "
                "ruled yes by Max, d074) the oracle COLA path stops at 2022 "
                "and no 2030 benefit exists"
            )
        if self.acceptance_rule is not None:
            raise ValueError(
                "an acceptance rule was supplied, but Max ruled no numerical "
                "acceptance threshold (decision 3, d074); A1 section 17 "
                "reports gaps only"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "populations": {
                str(wave): POPULATIONS[wave].as_dict(self.reference_year)
                for wave in self.anchor_waves
            },
            "reference_year": self.reference_year,
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
            "opening_stock_basis": self.opening_stock_basis,
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


#: Max's rulings of 2026-09-23 that are assembly fields: the plan's
#: section 6 decisions (decision record d074) and A1 referee question 11
#: (d075); A1 sections 21-22 record them.  Each adopts the proposed
#: default; ``declined`` lists the alternatives Max did not choose, in the
#: A1 block's vocabulary (``declined_config_value`` gives the
#: configuration value where the two differ).
MAX_RULINGS: dict[str, dict[str, Any]] = {
    "claim_class": {
        "ruling": "track_a_reported_not_gated_psid_oracle",
        "declined": ["hold_for_track_b_m6_forward", "hold_for_track_c_axiom"],
        "decided": "plan section 6, decision 1",
        "decision_record": "d074",
    },
    "oracle_cola_horizon_extension_to_2030": {
        "ruling": True,
        "declined": [False],
        "decided": "plan section 6, decision 2(a)",
        "decision_record": "d074",
    },
    "di_benefit_level": {
        "ruling": LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION.value,
        "declined": ["exclude_until_axiom_di_rule"],
        "declined_config_value": LevelPolicy.EXCLUDE.value,
        "decided": "plan section 6, decision 2(b)",
        "decision_record": "d074",
        "note": (
            "the declined alternative (di_benefit_level='exclude') runs "
            "only as an invented-data sensitivity: under exclude, projected "
            "DI awards leave every row, R3 included (A1 section 22 says R3 "
            "could keep them, which this assembly does not implement)"
        ),
    },
    "acceptance_rule": {
        "ruling": None,
        "declined": ["numerical_rule_set_by_max_before_registration"],
        "decided": "plan section 6, decision 3",
        "decision_record": "d074",
    },
    "opening_stock_basis": {
        "ruling": OPENING_STOCK_BASIS,
        "declined": ["rebased_on_later_simulated_events"],
        "decided": "A1 referee question 11",
        "decision_record": "d075",
        "note": (
            "a named delta (A1 section 12); later simulated widowhood, a "
            "spouse's entitlement or conversion at FRA change neither an "
            "opening-stock person's level path nor the reduced increases"
        ),
    },
}
_RULED_BY = "Max, 2026-09-23 (A1 section 22)"


def _config_value(config: TrackAConfig, name: str) -> Any:
    value = getattr(config, name)
    return value.value if isinstance(value, Enum) else value


def max_rulings(config: TrackAConfig | None = None) -> list[dict]:
    """Max's rulings, each with the configured value and whether it follows.

    These are not pending: Max ruled them on 2026-09-23 (d074, d075).  A
    configuration may still depart from one for an invented-data
    sensitivity (``di_benefit_level``), and the entry then says so.
    """

    config = config or TrackAConfig()
    out = []
    for name, ruling in MAX_RULINGS.items():
        value = _config_value(config, name)
        out.append(
            {
                "field": name,
                "value": value,
                **ruling,
                "ruled_by": _RULED_BY,
                "follows_ruling": value == ruling["ruling"],
            }
        )
    return out


def rulings_departures(config: TrackAConfig) -> list[str]:
    """The fields whose configured value departs from Max's ruling."""

    return [
        item["field"]
        for item in max_rulings(config)
        if not item["follows_ruling"]
    ]


_A5_BUILDER = "A5 builder choice; no ruling covers it"
_FIXED_BY = (
    "A1 ratification (plan section 6 item 4) and the issue #42 registration"
)


def builder_defaults(config: TrackAConfig | None = None) -> list[dict]:
    """Each A5 builder default no ruling covers, with the value used.

    Max did not rule on these (his 2026-09-23 rulings are
    :func:`max_rulings`).  ``source`` says where the default comes from;
    ``fixed_by`` names the steps that freeze it.
    """

    config = config or TrackAConfig()
    return [
        {
            "field": "preeligibility_death_level",
            "value": config.preeligibility_death_level.value,
            "source": (
                _A5_BUILDER + "; mirrors Max's ruling on the DI benefit "
                "level (decision 2(b)) because A6 routes it to the same kind "
                "of ruling, which the ruling itself does not name"
            ),
            "alternatives": [LevelPolicy.EXCLUDE.value],
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "auxiliary_entitlement_clock",
            "value": config.auxiliary_entitlement_clock.value,
            "source": "A1 section 6, R2 text",
            "alternatives": [AuxiliaryEntitlementClock.WORKER.value],
            "fixed_by": f"{_FIXED_BY}; A1 referee question 8 is open",
            "note": (
                "under worker, R2 has no exposure start for the widow(er) "
                "of a worker who was never entitled (A6 leaves it "
                "undefined), so that widow(er)'s benefit is dropped from R2 "
                "only (counted as entitlement_clock_undefined) and R2's "
                "membership can differ from R0's; opening-stock "
                "auxiliaries use their own entitlement year instead "
                "(counted as opening_worker_entitlement_unobserved_used_own)"
            ),
        },
        {
            "field": "survivor_entitlement_rule",
            "value": config.survivor_entitlement_rule.value,
            "source": _A5_BUILDER,
            "alternatives": [],
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "spouse_entitlement_rule",
            "value": config.spouse_entitlement_rule.value,
            "source": _A5_BUILDER,
            "alternatives": [],
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "opening_aged_widow_min_age",
            "value": config.opening_aged_widow_min_age,
            "source": (
                _A5_BUILDER + "; A1 section 11 lists aged widow(er)s from "
                "60 and disabled widow(er)s under 60"
            ),
            "alternatives": [],
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "mortality_base_year",
            "value": config.mortality_base_year,
            "source": "A2 PENDING_RULINGS base_year default",
            "alternatives": [2007],
            "fixed_by": f"{_FIXED_BY} (A1 section 15 substitute)",
        },
        {
            "field": "claim_table_max_year",
            "value": config.claim_table_max_year,
            "source": "plan item A5 (<=2008 PMF snap)",
            "alternatives": [],
            "fixed_by": _FIXED_BY,
        },
        {
            "field": "wage_base_2009_2010",
            "value": "realized",
            "source": (
                _A5_BUILDER + "; the oracle's contribution and benefit base "
                "for 2009-2010 is the realized base (policyengine-us), which "
                "differs from TR2008 V.C1's projected 2009-2010 bases; the "
                "registered-run statutory check records the difference as "
                "documented. Weights only"
            ),
            "alternatives": ["tr2008_projected"],
            "fixed_by": _FIXED_BY,
        },
    ]
