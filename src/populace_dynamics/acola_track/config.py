"""Registration 18's independent rows and projection configuration."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

from populace_dynamics.cola_track_a.config import (
    OPENING_STOCK_BASIS,
    POPULATIONS,
    TRACK_A_LABELS,
    AuxiliaryEntitlementClock,
    LevelPolicy,
    RegisteredRow,
    SpouseEntitlementRule,
    SurvivorEntitlementRule,
    TrackAConfig,
    rulings_departures,
)
from populace_dynamics.engine.di_entitlement_rates import DIEntitlementSpec
from populace_dynamics.estimates.cola_age_profile import PRIMARY_COMPONENTS
from populace_dynamics.scenario_benefits import (
    BenefitPeriod,
    ExposureClock,
    NegativeRatePolicy,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRATION_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5919983573"
)
SPECIFICATION_PATH = ROOT / "docs/design/acola_registration18.md"
SPECIFICATION_SHA256 = (
    "02287d54f12285c8dffcb94ba7dae9cbe3cc34ba338c602a5ad4afe14d598f20"
)
LABELS = (*TRACK_A_LABELS, "report-only")
AUTHORIZATION = {
    "decision": "d658",
    "ruling": (
        "Yes: register today a report-only blind test of OACT provision A1 "
        "(COLA -1pt from Dec 2027), 2030 cost effect, vs OACT and PWBM, "
        "with MINT5 as third comparator on the COLA row; report our ratio "
        "of means and a median beside MINT's median; FRA-68 rows secondary "
        "later. Build + independent review + post the #42 registration today."
    ),
    "carried_conventions": (
        "Registered by Registration 18, citing cola_track_a/config.py: "
        "d074 claim class, COLA horizon and disclosed oracle DI levels; "
        "d075 opening-stock basis."
    ),
}


@dataclass(frozen=True)
class ACOLARow:
    """A row built outside the legacy registry; D remains deferred."""

    row_id: str
    sub_row: str
    field_changed: str | None
    first_reduced_determination_year: int
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY
    benefit_period: BenefitPeriod = BenefitPeriod.CALENDAR_YEAR
    mechanism: str = "L"
    age_rule: str = "reference_year_minus_birth_year"
    components: tuple[str, ...] = PRIMARY_COMPONENTS
    anchor_wave: int = 2011

    @property
    def di_computation(self) -> str:
        return (
            "statutory_415_b_2" if self.mechanism == "D" else "legacy_fixed_35"
        )

    @property
    def statistics(self) -> tuple[str, ...]:
        if self.sub_row == "cost":
            return ("P", "ratio_of_scenario_means", "P_OASI", "P_DI")
        return (
            "ratio_of_scenario_means",
            "median_individual_pct_change",
            "difference_of_weighted_medians_pct",
            "baseline_falling_share",
            "median_benefit_base",
            "median_benefit_reform",
        )

    @property
    def population(self):
        return POPULATIONS[self.anchor_wave]

    def track_row(self) -> RegisteredRow:
        """Supply only the legacy benefit interface, without its registry."""
        return RegisteredRow(
            row_id=self.row_id,
            field_changed=self.field_changed,
            first_reduced_determination_year=(
                self.first_reduced_determination_year
            ),
            exposure_clock=self.exposure_clock,
            benefit_period=self.benefit_period,
            components=self.components,
            headline_statistic=(
                "ratio_of_all_alive_weighted_totals"
                if self.sub_row == "cost"
                else "ratio_of_scenario_means"
            ),
            anchor_wave=self.anchor_wave,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "sub_row": self.sub_row,
            "field_changed": self.field_changed,
            "first_reduced_determination_year": (
                self.first_reduced_determination_year
            ),
            "exposure_clock": self.exposure_clock.value,
            "benefit_period": self.benefit_period.value,
            "benefit_scale": "annual_12_times_monthly",
            "mechanism": self.mechanism,
            "di_computation": self.di_computation,
            "age_rule": self.age_rule,
            "components": list(self.components),
            "statistics": list(self.statistics),
            "population": self.population.as_dict(),
            "negative_rate_policy": NegativeRatePolicy.REFUSE.value,
        }


_C0 = ACOLARow("C0", "cost", None, 2027)
_M0 = ACOLARow("M0", "mint5", None, 2011)
REGISTERED_ROWS = {
    "C0": _C0,
    "C1": replace(
        _C0,
        row_id="C1",
        field_changed="benefit_period",
        benefit_period=BenefitPeriod.DECEMBER,
    ),
    "C0-D": replace(
        _C0, row_id="C0-D", field_changed="mechanism", mechanism="D"
    ),
    "M0": _M0,
    "M1": replace(
        _M0,
        row_id="M1",
        field_changed="first_reduced_increase",
        first_reduced_determination_year=2010,
    ),
    "M2": replace(
        _M0,
        row_id="M2",
        field_changed="benefit_period",
        benefit_period=BenefitPeriod.DECEMBER,
    ),
    "M3": replace(
        _M0,
        row_id="M3",
        field_changed="exposure_clock",
        exposure_clock=ExposureClock.ENTITLEMENT,
    ),
    "M4": replace(
        _M0,
        row_id="M4",
        field_changed="age_rule",
        age_rule="reference_year_minus_birth_year_minus_one",
    ),
}
RUNNABLE_ROWS = tuple(k for k in REGISTERED_ROWS if k != "C0-D")
DEFERRED_ROWS = {
    "C0-D": {
        "status": "deferred",
        "row": REGISTERED_ROWS["C0-D"].as_dict(),
        "reason": (
            "Runs once Track A v2's own real-data run artifact is committed "
            "to master, at a commit that a further issue #42 comment "
            "registers before D runs. If run after the primary comparison, "
            "label: registered before the comparator was public, run after it."
        ),
    }
}


def check_specification(path: Path = SPECIFICATION_PATH) -> dict[str, Any]:
    """Bind the verbatim posted specification, without a ratification test."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != SPECIFICATION_SHA256:
        raise ValueError("A-COLA specification SHA-256 differs from its pin")
    return {
        "path": "docs/design/acola_registration18.md",
        "sha256": digest,
        "registration_pointer": REGISTRATION_POINTER,
        "authorization": AUTHORIZATION,
    }


@dataclass(frozen=True)
class ACOLAConfig:
    """Compose R0's projection conventions; never pass new ids to Track A."""

    reference_year: int = 2030
    draw_indices: tuple[int, ...] = tuple(range(20))
    floor_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    rows: tuple[str, ...] = RUNNABLE_ROWS
    annual_reduction: float = 0.01
    tr2008_alternative: str = "intermediate"
    tr2008_first_rate_year: int = 2008
    mortality_base_year: int = 2004
    claim_table_max_year: int = 2008
    di_spec: DIEntitlementSpec = field(default_factory=DIEntitlementSpec)
    claim_class: str = "track_a_reported_not_gated_psid_oracle"
    oracle_cola_horizon_extension_to_2030: bool = True
    di_benefit_level: LevelPolicy = LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
    acceptance_rule: str | None = None
    opening_stock_basis: str = OPENING_STOCK_BASIS
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
    opening_aged_widow_min_age: int = 60
    opening_stock_dime_floor: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        if not self.rows or len(set(self.rows)) != len(self.rows):
            raise ValueError("rows must be non-empty and unique")
        if "C0-D" in self.rows:
            raise ValueError("C0-D is registered but deferred")
        if set(self.rows) - set(RUNNABLE_ROWS):
            raise ValueError("unknown A-COLA row")
        if self.reference_year != 2030:
            raise ValueError("Registration 18 reads calendar 2030 only")
        if (
            not math.isfinite(self.annual_reduction)
            or self.annual_reduction < 0
        ):
            raise ValueError(
                "annual_reduction must be finite and non-negative"
            )
        for name in ("draw_indices", "floor_seeds"):
            indices = tuple(getattr(self, name))
            if (
                not indices
                or any(type(k) is not int or k < 0 for k in indices)
                or len(set(indices)) != len(indices)
            ):
                raise ValueError(
                    f"{name} must be unique non-negative integers"
                )
            object.__setattr__(self, name, tuple(sorted(indices)))
        # Track A performs the shared enum and opening-basis validation.
        track = self.track_a_config()
        for name in (
            "di_benefit_level",
            "preeligibility_death_level",
            "auxiliary_entitlement_clock",
            "survivor_entitlement_rule",
            "spouse_entitlement_rule",
        ):
            object.__setattr__(self, name, getattr(track, name))

    @property
    def anchor_waves(self) -> tuple[int, ...]:
        return (2011,)

    @property
    def start_years(self) -> dict[int, int]:
        return {2011: 2010}

    def rows_for_wave(self, anchor_wave: int) -> tuple[str, ...]:
        return self.rows if anchor_wave == 2011 else ()

    def track_a_config(self) -> TrackAConfig:
        values = {
            f.name: getattr(self, f.name)
            for f in fields(TrackAConfig)
            if f.name != "rows"
        }
        return TrackAConfig(rows=("R0",), **values)

    def check_runnable(self) -> None:
        if self.acceptance_rule is not None:
            raise ValueError(
                "A-COLA is report-only; no acceptance rule exists"
            )
        self.track_a_config().check_runnable()

    def check_registered(self) -> None:
        """Invented sensitivities never change the registered one shot."""
        self.check_runnable()
        expected = ACOLAConfig()
        mismatches = [
            f.name
            for f in fields(self)
            if getattr(self, f.name) != getattr(expected, f.name)
        ]
        if mismatches:
            raise ValueError(
                "Registration 18 settings differ: " + ", ".join(mismatches)
            )
        departures = rulings_departures(self.track_a_config())
        if departures:
            raise ValueError(f"carried Track A rulings differ: {departures}")

    def as_dict(self) -> dict[str, Any]:
        values = self.track_a_config().as_dict()
        values.update(
            rows=list(self.rows),
            registered_rows={
                k: row.as_dict() for k, row in REGISTERED_ROWS.items()
            },
            negative_rate_policy=NegativeRatePolicy.REFUSE.value,
            labels=list(LABELS),
            authorization=AUTHORIZATION,
        )
        return values
