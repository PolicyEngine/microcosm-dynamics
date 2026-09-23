"""Reference-year baseline and reform benefits per person (A6 paths).

Python oracle (not Axiom).  After each draw's projection, every person
alive in the reference-year state gets a baseline and a reform benefit
for each registered row, computed from the *same* projected state (fixed
paths, mechanical incidence).  The arithmetic is the A6 module's
(:mod:`populace_dynamics.scenario_benefits`): :class:`ScenarioCOLARates`
for the per-PIA rate path, ``increased_pia_path`` and
``monthly_benefit_path`` for dime-floored increases, and
``spouse_excess_path`` / ``widow_benefit_path`` for the auxiliaries, which
call the oracle's ``spousal_benefit`` and ``widow_benefit``.  This module
only decides, from the projected state, which PIA a benefit rests on,
when it starts, and which increases the reform reaches.  Amounts are on
the annual scale, 12 times the monthly amount (A1 section 10).

Who receives what (A5 conventions; A1 section 11 where it speaks):

* **Opening stock** (A1 section 11, rule 4): a 2010 recipient with an
  :class:`~populace_dynamics.cola_track_a.opening.OpeningStockRecord`
  keeps the observed 2010 amount carried forward on the baseline path,
  with the reform ratio from the reformed increases on the record's
  clock.  Later simulated widowhood, a spouse's entitlement or conversion
  at FRA change neither the amount nor the reduced increases; a disabled
  worker converted at FRA is reported under the retired-worker component
  (A1 section 11 counts converted disabled workers as retired workers).
  A simulated DI recovery ends a disabled worker's opening basis (rule 4
  does not list recovery); the person is then treated like anyone else.
* **Own worker benefit**: an entitled disabled worker (A4), a converted
  disabled worker (retired-worker component, disability clock kept), or
  a simulated retirement claimant (age-62 clock, claim-age factor from
  the oracle's ``claiming.benefit_factor``).  A disability clock never
  starts after the year the worker attains 62.  This is an A5 reading of
  the A1 statute excerpts, not an A1 ruling: 415(a)(3)(B)(i) deems a
  worker eligible for old-age benefits from the month of attaining 62,
  and 415(i)(2)(A)(iii) increases the primary insurance amount of an
  individual who becomes eligible for an old-age or disability benefit
  by that year's and later increases "without regard to the time of
  entitlement".  So an A4 award at 62 or later (A4 exposes retirement
  claimants below FRA) keeps the age-62 clock the PIA already runs on.
  Under the entitlement clock (R2) the award year is kept, as the A1
  section 6 table gives it for a disabled worker.
* **Spouse's excess**: a claimant married, in the reference state, to a
  living worker with an own benefit, from the later of the two
  entitlement years, at 62 or older.
* **Aged widow(er)'s benefit**: a widow(er) of a worker in the opening
  roster, from the later of widowhood and age 60, paid as the excess over
  the survivor's own benefit (dual entitlement through
  ``widow_benefit``).  The deceased's PIA is taken from the last state
  before death.

Levels the oracle does not compute (decision 2(b) and the A6
pre-eligibility-death hook) follow :class:`LevelPolicy`;
:func:`approximate_pia` is the disclosed approximation.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a.config import (
    AuxiliaryEntitlementClock,
    LevelPolicy,
    RegisteredRow,
    TrackAConfig,
)
from populace_dynamics.cola_track_a.opening import (
    OpeningStockRecord,
    TrackACohort,
)
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.ss import benefits
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "BenefitContext",
    "StateLookups",
    "PiaRecord",
    "approximate_pia",
    "opening_stock_amounts",
    "reference_benefit_rows",
]

#: The oracle's PIA formula covers eligibility from 1979 (plan section 10).
FIRST_ORACLE_ELIGIBILITY_YEAR = 1979
_RETIREMENT_AGE = 62
_MONTHS = 12
_OPENING_AUX = ("survivor", "spouse", "other", "unclassified")


@dataclass(frozen=True)
class BenefitContext:
    """Inputs shared by every draw and row."""

    cohort: TrackACohort
    params: SSAParameters
    baseline: sb.COLARateSource
    config: TrackAConfig


@dataclass(frozen=True)
class PiaRecord:
    """The PIA a benefit rests on, with its statutory clock.

    ``eligibility_pia`` is ``None`` when the level policy excludes it.
    ``entitlement_year`` is the worker's own first entitlement, ``None``
    for a worker who was never entitled.
    """

    person_id: int
    kind: str
    component: str
    basis: sb.EligibilityBasis
    eligibility_year: int
    entitlement_year: int | None
    eligibility_pia: float | None
    claim_age_factor: float
    level_basis: str


def approximate_pia(
    history: Mapping[int, float],
    *,
    birth_year: int,
    computation_end_year: int,
    eligibility_year: int,
    params: SSAParameters,
) -> float:
    """Disclosed approximation for a level the oracle does not compute.

    The oracle's AIME (``benefits.aime``: highest 35 indexed years,
    missing years as zero) over the career through
    ``computation_end_year``, then the oracle's PIA formula at
    ``eligibility_year``'s bend points.  The oracle indexes earnings to
    the year its ``birth_year`` argument attains 60; this function passes
    ``min(birth_year, eligibility_year - 62)``, so earnings are indexed
    to the second year before ``eligibility_year`` (the oracle's own
    age-60 year when ``eligibility_year`` is the year of attaining 62).
    The AIME and the bend points are then on the same year's wage level.
    Indexing to age 60 with an earlier year's bend points would put the
    AIME on a later wage level than the bend points and overstate the
    level of an early onset or death.

    It is not the statutory DI or pre-eligibility-death computation: the
    divisor is always 35 years (no elapsed or dropout years), so it
    understates short careers.  It sets a weight, never a reform ratio.
    """

    kept = {
        int(year): float(earnings)
        for year, earnings in history.items()
        if int(year) <= int(computation_end_year)
    }
    indexing_birth_year = min(
        int(birth_year), int(eligibility_year) - _RETIREMENT_AGE
    )
    aime = benefits.aime(kept, indexing_birth_year, params)
    return benefits.pia(aime, int(eligibility_year), params)


def _nullable_int(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)


class StateLookups:
    """Per-draw state lookups built once from the projection slices."""

    def __init__(self, result: ProjectionResult, reference_year: int):
        final = result.slices[-1]
        if len(final) and set(final["year"].unique()) != {reference_year}:
            raise ValueError("the last slice is not the reference year")
        self.final = final.set_index("person_id", drop=False)
        panel = result.panel.sort_values(["person_id", "year"], kind="stable")
        last = panel.groupby("person_id", sort=False).tail(1)
        self.last = last.set_index("person_id", drop=False)
        self.reference_year = reference_year

    def alive(self, person_id: int) -> bool:
        return person_id in self.final.index

    def death_year(self, person_id: int) -> int | None:
        if person_id not in self.last.index or self.alive(person_id):
            return None
        return int(self.last.at[person_id, "year"]) + 1


class _Calculator:
    """Builds PIA records and amounts for one draw and one row."""

    def __init__(
        self,
        context: BenefitContext,
        row: RegisteredRow,
        lookups: StateLookups,
        counters: Counter,
        pia_cache: dict,
    ) -> None:
        self.ctx = context
        self.row = row
        self.lookups = lookups
        self.counters = counters
        self.cache = pia_cache
        self.statics = context.cohort.persons_by_id
        self.reform = sb.COLAReform(
            annual_reduction=context.config.annual_reduction,
            first_reduced_determination_year=(
                row.first_reduced_determination_year
            ),
        )
        self.payment_year = sb.payment_year_for_reference(
            context.config.reference_year, row.benefit_period
        )

    # ---- levels -------------------------------------------------------
    def _history(self, person_id: int) -> Mapping[int, float]:
        return self.ctx.cohort.careers.get(person_id, {})

    def _level(
        self,
        person_id: int,
        tag: str,
        year: int,
        policy: LevelPolicy | None,
    ) -> tuple[float | None, str]:
        if year < FIRST_ORACLE_ELIGIBILITY_YEAR:
            self.counters["level_unavailable_eligibility_before_1979"] += 1
            return None, "unavailable_eligibility_before_1979"
        if policy is LevelPolicy.EXCLUDE:
            self.counters[f"level_excluded_{tag}"] += 1
            return None, f"excluded_{tag}"
        key = (person_id, tag, year)
        if key not in self.cache:
            birth = int(self.statics.at[person_id, "birth_year"])
            if tag == "retirement":
                clock = sb.WorkerClock.at_age_62(birth)
                self.cache[key] = sb.eligibility_pia_for_clock(
                    clock,
                    history=self._history(person_id),
                    birth_year=birth,
                    params=self.ctx.params,
                )
            else:
                self.cache[key] = approximate_pia(
                    self._history(person_id),
                    birth_year=birth,
                    computation_end_year=year,
                    eligibility_year=year,
                    params=self.ctx.params,
                )
        basis = (
            "oracle_retirement_pia"
            if tag == "retirement"
            else f"disclosed_oracle_approximation_{tag}"
        )
        return self.cache[key], basis

    # ---- PIA records --------------------------------------------------
    def worker_record(self, person_id: int, state: Any) -> PiaRecord | None:
        """The person's own worker PIA in ``state``, if they have one."""

        statics = self.statics.loc[person_id]
        birth = int(statics["birth_year"])
        opener = self.ctx.cohort.opening.get(person_id)
        status = str(statics["opening_status"])
        recovered = _nullable_int(state["di_recovery_year"]) is not None
        entitled = bool(state["di_entitled"])
        converted = _nullable_int(state["di_conversion_year"]) is not None
        config = self.ctx.config
        if (
            status == "disabled_worker"
            and not recovered
            and (entitled or converted)
        ):
            onset = opener.clock_year if opener else config.start_year
            entitlement = opener.entitlement_year if opener else onset
            return self._di_record(person_id, onset, entitlement, converted)
        if entitled or converted:
            award = _nullable_int(state["di_award_year"])
            if award is None:
                raise ValueError(
                    f"person {person_id} is DI-origin without an award year"
                )
            # The PIA already runs on the age-62 clock when A4 awards at
            # 62 or later (module docstring); the award year stays the
            # entitlement year that R2 reads.
            eligibility = min(award, birth + _RETIREMENT_AGE)
            return self._di_record(person_id, eligibility, award, converted)
        if status in _OPENING_AUX:
            return None
        if not bool(state["claimed"]):
            return None
        claim_year = _nullable_int(state["claim_year"])
        if claim_year is None and opener is not None:
            claim_year = opener.entitlement_year
        if claim_year is None:
            self.counters["claimant_without_claim_year"] += 1
            return None
        claim_year = max(claim_year, birth + _RETIREMENT_AGE)
        pia, level_basis = self._level(
            person_id, "retirement", birth + _RETIREMENT_AGE, None
        )
        factor = claiming.benefit_factor(
            _MONTHS * min(claim_year - birth, 70), birth, self.ctx.params
        )
        return PiaRecord(
            person_id=person_id,
            kind="retired",
            component="retired_worker",
            basis=sb.EligibilityBasis.AGE_62,
            eligibility_year=birth + _RETIREMENT_AGE,
            entitlement_year=claim_year,
            eligibility_pia=pia,
            claim_age_factor=factor,
            level_basis=level_basis,
        )

    def _di_record(
        self, person_id: int, onset: int, entitlement: int, converted: bool
    ) -> PiaRecord:
        pia, level_basis = self._level(
            person_id, "di", onset, self.ctx.config.di_benefit_level
        )
        return PiaRecord(
            person_id=person_id,
            kind="converted" if converted else "disabled",
            component="retired_worker" if converted else "disabled_worker",
            basis=sb.EligibilityBasis.DI_ONSET,
            eligibility_year=onset,
            entitlement_year=entitlement,
            eligibility_pia=pia,
            claim_age_factor=1.0,
            level_basis=level_basis,
        )

    def deceased_record(self, person_id: int) -> PiaRecord | None:
        """The deceased worker's PIA from the last state before death."""

        death = self.lookups.death_year(person_id)
        if death is None:
            raise ValueError(f"person {person_id} is not a projected decedent")
        state = self.lookups.last.loc[person_id]
        record = self.worker_record(person_id, state)
        if record is not None:
            return record
        birth = int(self.statics.at[person_id, "birth_year"])
        if death >= birth + _RETIREMENT_AGE:
            pia, level_basis = self._level(
                person_id, "retirement", birth + _RETIREMENT_AGE, None
            )
            return PiaRecord(
                person_id=person_id,
                kind="deceased_unentitled",
                component="retired_worker",
                basis=sb.EligibilityBasis.AGE_62,
                eligibility_year=birth + _RETIREMENT_AGE,
                entitlement_year=None,
                eligibility_pia=pia,
                claim_age_factor=1.0,
                level_basis=level_basis,
            )
        pia, level_basis = self._level(
            person_id,
            "death_before_eligibility",
            death,
            self.ctx.config.preeligibility_death_level,
        )
        return PiaRecord(
            person_id=person_id,
            kind="deceased_before_eligibility",
            component="retired_worker",
            basis=sb.EligibilityBasis.DEATH_BEFORE_ELIGIBILITY,
            eligibility_year=death,
            entitlement_year=None,
            eligibility_pia=pia,
            claim_age_factor=1.0,
            level_basis=level_basis,
        )

    # ---- rates --------------------------------------------------------
    def _exposure_start(
        self, record: PiaRecord, auxiliary_entitlement: int | None = None
    ) -> int | None:
        if self.row.exposure_clock is sb.ExposureClock.ELIGIBILITY:
            return record.eligibility_year
        if auxiliary_entitlement is not None and (
            self.ctx.config.auxiliary_entitlement_clock
            is AuxiliaryEntitlementClock.AUXILIARY_OWN
        ):
            return auxiliary_entitlement
        if record.entitlement_year is None:
            self.counters["entitlement_clock_undefined"] += 1
            return None
        return record.entitlement_year

    def _rates(
        self, eligibility_year: int, exposure_start: int
    ) -> tuple[sb.ScenarioCOLARates, sb.ScenarioCOLARates]:
        return (
            sb.ScenarioCOLARates(
                baseline=self.ctx.baseline,
                reform=None,
                exposure_start_year=eligibility_year,
            ),
            sb.ScenarioCOLARates(
                baseline=self.ctx.baseline,
                reform=self.reform,
                exposure_start_year=exposure_start,
            ),
        )

    def _worker_paths(
        self, record: PiaRecord, exposure_start: int
    ) -> tuple[dict[int, float], dict[int, float]]:
        paths = []
        for rates in self._rates(record.eligibility_year, exposure_start):
            path = sb.monthly_benefit_path(
                eligibility_pia=record.eligibility_pia,
                claim_age_factor=record.claim_age_factor,
                eligibility_year=record.eligibility_year,
                cola=rates,
                horizon_year=self.payment_year,
            )
            paths.append(
                {
                    year: amount
                    for year, amount in path.items()
                    if year >= record.entitlement_year
                }
            )
        return paths[0], paths[1]

    def _pia_paths(
        self, record: PiaRecord, exposure_start: int
    ) -> tuple[dict[int, float], dict[int, float]]:
        return tuple(  # type: ignore[return-value]
            sb.increased_pia_path(
                eligibility_pia=record.eligibility_pia,
                eligibility_year=record.eligibility_year,
                cola=rates,
                horizon_year=self.payment_year,
            )
            for rates in self._rates(record.eligibility_year, exposure_start)
        )

    def reduced_count(self, eligibility_year: int, exposure_start: int) -> int:
        reform_rates = self._rates(eligibility_year, exposure_start)[1]
        return sum(
            reform_rates.is_reduced(year)
            for year in range(eligibility_year, self.payment_year)
        )

    # ---- people -------------------------------------------------------
    def opening_person(
        self, record: OpeningStockRecord, state: Any
    ) -> tuple[dict[str, tuple[float, float]], int]:
        component = record.component
        if (
            component == "disabled_worker"
            and _nullable_int(state["di_conversion_year"]) is not None
        ):
            # A1 section 11: retired workers include disabled workers
            # converted at FRA.  The amount and T_i stay on the opening
            # basis (rule 4); only the component label follows the
            # conversion.
            component = "retired_worker"
        exposure = record.clock_year
        if self.row.exposure_clock is sb.ExposureClock.ENTITLEMENT:
            exposure = record.entitlement_year
            if record.component in ("spouse", "aged_widow", "disabled_widow"):
                if (
                    self.ctx.config.auxiliary_entitlement_clock
                    is AuxiliaryEntitlementClock.WORKER
                ):
                    # The insured worker's entitlement is not observed.
                    self.counters[
                        "opening_worker_entitlement_unobserved_used_own"
                    ] += 1
        base, reform = opening_stock_amounts(
            record,
            baseline=self.ctx.baseline,
            reform=self.reform,
            exposure_start_year=exposure,
            observed_payment_year=self.ctx.config.start_year,
            payment_year=self.payment_year,
            round_to_dime=self.ctx.config.opening_stock_dime_floor,
        )
        return (
            {component: (base, reform)},
            self.reduced_count(record.clock_year, exposure),
        )

    def projected_person(
        self, person_id: int, state: Any
    ) -> tuple[dict[str, tuple[float, float]], int | None]:
        reference = self.ctx.config.reference_year
        components: dict[str, tuple[float, float]] = {}
        primary_count: int | None = None
        own = self.worker_record(person_id, state)
        own_paths = None
        if own is not None and own.entitlement_year <= reference:
            if own.eligibility_pia is None:
                # The own level decides dual entitlement, so a person
                # whose own level is excluded cannot be placed at all.
                self.counters["person_excluded_own_level_unavailable"] += 1
                return {}, None
            else:
                start = self._exposure_start(own)
                if start is None:
                    return {}, None
                own_paths = self._worker_paths(own, start)
                components[own.component] = (
                    own_paths[0][self.payment_year],
                    own_paths[1][self.payment_year],
                )
                primary_count = self.reduced_count(own.eligibility_year, start)
        elif own is not None:
            own = None
        status = str(state["marital_status"])
        if status == "married" and own is not None and own.kind != "disabled":
            spouse = self._spouse_excess(person_id, state, own)
            if spouse is not None:
                components["spouse"] = spouse
        elif status == "widowed":
            widow = self._widow_excess(person_id, state, own, own_paths)
            if widow is not None:
                components["aged_widow"], count = widow
                if primary_count is None:
                    primary_count = count
        return components, primary_count

    def _spouse_excess(
        self, person_id: int, state: Any, own: PiaRecord
    ) -> tuple[float, float] | None:
        spouse_id = _nullable_int(state["spouse_person_id"])
        if spouse_id is None or not self.lookups.alive(spouse_id):
            return None
        worker = self.worker_record(
            spouse_id, self.lookups.final.loc[spouse_id]
        )
        if worker is None:
            return None
        if worker.eligibility_pia is None:
            self.counters["spouse_worker_level_unavailable"] += 1
            return None
        birth = int(self.statics.at[person_id, "birth_year"])
        entitlement = max(own.entitlement_year, worker.entitlement_year)
        if entitlement > self.ctx.config.reference_year:
            return None
        if entitlement - birth < _RETIREMENT_AGE:
            return None
        worker_start = self._exposure_start(worker, entitlement)
        own_start = self._exposure_start(own)
        if worker_start is None or own_start is None:
            return None
        worker_pia = self._pia_paths(worker, worker_start)
        own_pia = self._pia_paths(own, own_start)
        months_early = max(
            0,
            self.ctx.params.fra_months(birth)
            - _MONTHS * (entitlement - birth),
        )
        amounts = [
            sb.spouse_excess_path(
                worker_pia_by_year=worker_pia[index],
                own_pia_by_year=own_pia[index],
                months_early=months_early,
                entitlement_year=entitlement,
                params=self.ctx.params,
                horizon_year=self.payment_year,
            )[self.payment_year]
            for index in (0, 1)
        ]
        if amounts[0] <= 0:
            return None
        self.counters["spouse_excess_paid"] += 1
        return amounts[0], amounts[1]

    def _widow_excess(
        self,
        person_id: int,
        state: Any,
        own: PiaRecord | None,
        own_paths: tuple[dict[int, float], dict[int, float]] | None,
    ) -> tuple[tuple[float, float], int] | None:
        deceased_id = _nullable_int(state["late_spouse_person_id"])
        widowhood = _nullable_int(state["widowhood_year"])
        if deceased_id is None or widowhood is None:
            self.counters["widow_without_linked_deceased"] += 1
            return None
        if deceased_id not in self.ctx.cohort.roster_ids:
            self.counters["widow_deceased_outside_roster"] += 1
            return None
        if self.lookups.death_year(deceased_id) != widowhood:
            # A3 dated this widowhood before 2011 although the late spouse
            # is in the opening roster: the two records disagree.
            self.counters["widow_death_year_disagrees_with_roster"] += 1
            return None
        birth = int(self.statics.at[person_id, "birth_year"])
        params = self.ctx.params
        entitlement = max(
            widowhood, birth + params.survivor_earliest_claim_age
        )
        if entitlement > self.ctx.config.reference_year:
            return None
        deceased = self.deceased_record(deceased_id)
        if deceased is None or deceased.eligibility_pia is None:
            self.counters["widow_deceased_level_unavailable"] += 1
            return None
        start = self._exposure_start(deceased, entitlement)
        if start is None:
            return None
        deceased_pia = self._pia_paths(deceased, start)
        survivor_months_early = max(
            0,
            params.survivor_reduction_period_months
            - _MONTHS
            * (entitlement - birth - params.survivor_earliest_claim_age),
        )
        payable = [
            sb.widow_benefit_path(
                deceased_pia_by_year=deceased_pia[index],
                own_amount_by_year=(
                    None if own_paths is None else own_paths[index]
                ),
                survivor_months_early=survivor_months_early,
                deceased_claim_age_factor=deceased.claim_age_factor,
                entitlement_year=entitlement,
                params=params,
                horizon_year=self.payment_year,
            )[self.payment_year]
            for index in (0, 1)
        ]
        own_now = (
            (0.0, 0.0)
            if own_paths is None
            else (
                own_paths[0][self.payment_year],
                own_paths[1][self.payment_year],
            )
        )
        excess = (payable[0] - own_now[0], payable[1] - own_now[1])
        if excess[0] <= 0:
            return None
        self.counters["aged_widow_excess_paid"] += 1
        return excess, self.reduced_count(deceased.eligibility_year, start)


def opening_stock_amounts(
    record: OpeningStockRecord,
    *,
    baseline: sb.COLARateSource,
    reform: sb.COLAReform,
    exposure_start_year: int,
    observed_payment_year: int,
    payment_year: int,
    round_to_dime: bool,
) -> tuple[float, float]:
    """Monthly baseline and reform amounts for an opening-stock record.

    A1 section 11, rule 4: the observed amount for the opening payment
    year (annual / 12) carried forward on the baseline path, and the
    reform amount scaled by ``(1 + reformed) / (1 + baseline)`` for each
    reformed increase determined before the opening year, then carried on
    the reformed path.  This is the arithmetic of A6
    ``opening_stock_scenario_paths``; it is composed here from the same
    A6 pieces because that function takes a ``WorkerClock``, which cannot
    carry an entitlement exposure for a worker who died before
    eligibility.  A test pins the two to each other where both apply.
    """

    if record.clock_year > observed_payment_year:
        raise ValueError("an opening-stock clock starts after the opening")
    observed = record.observed_annual_amount / _MONTHS
    base_rates = sb.ScenarioCOLARates(
        baseline=baseline, reform=None, exposure_start_year=record.clock_year
    )
    reform_rates = sb.ScenarioCOLARates(
        baseline=baseline,
        reform=reform,
        exposure_start_year=exposure_start_year,
    )
    reform_start = observed
    for year in range(record.clock_year, observed_payment_year):
        if reform_rates.is_reduced(year):
            reform_start *= (
                1.0 + reform_rates.rate_for_determination_year(year)
            ) / (1.0 + base_rates.rate_for_determination_year(year))
    amounts = [
        sb.increased_pia_path(
            eligibility_pia=start,
            eligibility_year=observed_payment_year,
            cola=rates,
            horizon_year=payment_year,
            round_to_dime=round_to_dime,
        )[payment_year]
        for start, rates in (
            (observed, base_rates),
            (reform_start, reform_rates),
        )
    ]
    return amounts[0], amounts[1]


def reference_benefit_rows(
    result: ProjectionResult,
    *,
    draw: int,
    row: RegisteredRow,
    context: BenefitContext,
    pia_cache: dict | None = None,
    lookups: StateLookups | None = None,
) -> tuple[list[dict[str, Any]], Counter]:
    """A7 input rows for one draw and one registered row.

    One row per person alive in the reference-year state with a positive
    baseline benefit; ``benefit_*`` and the components are annual (12
    times the monthly amount).  Extra columns (``basis``,
    ``reduced_increases``) are diagnostics; A7 ignores and lists them.
    """

    counters: Counter = Counter()
    if lookups is None:
        lookups = StateLookups(result, context.config.reference_year)
    calculator = _Calculator(
        context, row, lookups, counters, {} if pia_cache is None else pia_cache
    )
    rows = []
    for person_id in sorted(int(pid) for pid in lookups.final.index):
        state = lookups.final.loc[person_id]
        opener = context.cohort.opening.get(person_id)
        opening_intact = opener is not None and not (
            opener.status == "disabled_worker"
            and _nullable_int(state["di_recovery_year"]) is not None
        )
        if opener is not None and not opening_intact:
            counters["opening_di_basis_ended_by_recovery"] += 1
        receipt = context.cohort.persons_by_id.at[person_id, "ss_receipt_2010"]
        if opener is None and not pd.isna(receipt) and bool(receipt):
            counters["opening_recipient_without_record"] += 1
        if opening_intact:
            components, count = calculator.opening_person(opener, state)
            basis = "opening_stock"
        else:
            components, count = calculator.projected_person(person_id, state)
            basis = "projected"
        base = sum(value[0] for value in components.values())
        reform = sum(value[1] for value in components.values())
        if base <= 0:
            continue
        if reform <= 0:
            raise ValueError(
                f"person {person_id} has a positive baseline and no reform "
                "benefit; fixed-path membership would differ"
            )
        counters[f"beneficiaries_{basis}"] += 1
        rows.append(
            {
                "draw": int(draw),
                "person_id": person_id,
                "weight": float(state["weight"]),
                "birth_year": int(state["birth_year"]),
                "beneficiary_base": True,
                "beneficiary_reform": True,
                "benefit_base": _MONTHS * base,
                "benefit_reform": _MONTHS * reform,
                "benefit_components": {
                    name: {
                        "base": _MONTHS * value[0],
                        "reform": _MONTHS * value[1],
                    }
                    for name, value in components.items()
                },
                "basis": basis,
                "reduced_increases": count,
            }
        )
    return rows, counters
