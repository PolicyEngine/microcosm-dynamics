"""Per-person baseline and reform benefits for exercise 3 (FRA to 68).

Python oracle (not Axiom).  Both scenarios read the *same* projected state
of a draw (Track A's projection, unchanged) and the *same* COLA path (the
TR2008 intermediate baseline; exercise 3 changes no increase).  They
differ only in the oracle parameter bundle the age factors read
(:mod:`~populace_dynamics.fra68_track.reform`): the reform is applied at
benefit computation, with claim ages fixed under the primary claiming
convention C0.

:class:`ScenarioCalculator` computes one scenario.  It is Track A's
per-person calculator (``cola_track_a.benefits._Calculator``, which decides
from the projected state which PIA a benefit rests on and when it starts)
with the COLA reform removed, so its amounts follow the baseline COLA path,
and with these scenario rules layered on:

* **Retired worker**: the claim-age factor is ``claiming.benefit_factor``
  under the scenario's bundle.  Under C1 and C2 (plan section 6) a
  projected claim is moved to the claim month ``min(12 a + D, 840)``,
  ``D`` the reform-minus-baseline FRA in months, entitled in the calendar
  year A4's July birth-month convention gives; claims made at or before
  the opening year keep their age.
* **Spouse's excess**: months early are counted against the scenario's
  FRA for the spouse's birth year (Track A's rule, on the scenario
  bundle), from the later of the spouse's own claim and the worker's
  entitlement.  When C1 or C2 moved the spouse's own claim, that claim
  enters at its exact moved claim month, the month the spouse's own
  factor reads (E1 section 13; referee required change 1), not at the
  whole year it falls in (``reform.spouse_excess_months_early``).  When
  the spouse is a converted disabled worker whose own claim is the
  conversion, the baseline start of the excess moves by the FRA increase
  ``D`` (``reform.conversion_claim_excess_months_early``; E1 section 11,
  the review of ``e1-draft-4``): the count is Track A's baseline count in
  every scenario, so the reform leaves it unchanged, as 42 USC 402(q)(1)
  does a benefit that starts at FRA.  :data:`CONVERSION_CLAIM_EXCESS`
  and :data:`CONVERSION_CLAIM_MONTHS_EARLY` count these excesses and the
  ones Track A's whole-year count reduces (a named delta, E1 section 12).
* **Aged widow(er)**: the oracle's ``widow_benefit`` with the reduction
  span of the survivor's cohort (``reform.survivor_parameters``): the
  416(l)(2) mapping on the scenario schedule (row F0 and every baseline),
  on the baseline schedule (row F7's reform), or Track A's fixed 84 months
  (the null-reform identity test only).  The deceased's claim-age factor,
  which sets the RIB-LIM and the inherited credits, is the scenario's.  A
  deceased who never claimed carries factor 1.0 in both scenarios, so the
  credits 402(e)(2)(C) and 402(f)(2)(C) pass to the survivor of a worker
  who died unclaimed after retirement age are not modeled (a named delta,
  E1 section 12); :data:`CREDITS_NOT_INHERITED` counts the paid
  widow(er)'s excesses it touches (not a bound; see
  :meth:`ScenarioCalculator._count_credits_not_inherited`).
* **Disabled worker**: factor 1 in both scenarios.  A worker the
  projection converted at the baseline FRA is still a disabled worker in a
  scenario whose FRA is attained later than the state's year: only the
  component label changes (and, by Track A's convention, a disabled
  worker still entitled to DI draws no spouse's excess).  A converted
  worker's own claim for the spouse's excess enters the scenario in its
  conversion year and is counted as above.
* **Opening stock** (the basis frozen at the opening year, Max's ruling
  d075 for exercise 1, whose carry-over awaits him as the
  ``opening_stock_basis`` field of d188): the observed amount carried on
  the baseline path, times the component's reform-to-baseline age-factor
  ratio for a retired-worker or spouse record claimed at 62 or later
  (``reform.opening_stock_factor_ratio``); 1 for every other record.

:func:`union_benefit_rows` pairs a baseline and a reform scenario into A7
input rows: one row per person alive in the reference year with a
positive benefit in either scenario, with honest ``beneficiary_base`` and
``beneficiary_reform`` flags (Track A refused a zero reform amount;
exercise 3's claiming rows need it).  Amounts are annual, 12 times the
monthly amount (A1 section 10).
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    PiaRecord,
    StateLookups,
)
from populace_dynamics.cola_track_a.config import RegisteredRow
from populace_dynamics.cola_track_a.opening import OpeningStockRecord
from populace_dynamics.engine.di_entitlement import fra_attainment_year
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.fra68_track.config import (
    ClaimingResponse,
    SurvivorRetirementAge,
)
from populace_dynamics.fra68_track.reform import (
    AGE_70_MONTHS,
    conversion_claim_excess_months_early,
    fra_increase_months,
    opening_stock_factor_ratio,
    spouse_excess_months_early,
    survivor_parameters,
)
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "CONVERSION_CLAIM_EXCESS",
    "CONVERSION_CLAIM_MONTHS_EARLY",
    "CREDITS_NOT_INHERITED",
    "CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH",
    "MovedClaimRecord",
    "PersonScenario",
    "Scenario",
    "ScenarioCalculator",
    "scenario_benefits",
    "union_benefit_rows",
]

_MONTHS = 12
_RETIREMENT_AGE = 62
_MAX_CLAIM_AGE = 70
#: Scenario counters of the named delta "credits of a worker who died
#: unclaimed" (E1 section 12; 402(e)(2)(C), 402(f)(2)(C)): paid aged
#: widow(er)'s excesses resting on a never-entitled decedent who died in or
#: after the calendar year of attaining the scenario's retirement age, and
#: the subset whose claim C1 or C2 moved past death.  Diagnostics only
#: (the ``fra68_`` prefix marks counters Track A does not keep).
CREDITS_NOT_INHERITED = "fra68_widow_credits_not_inherited"
CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH = (
    "fra68_widow_credits_not_inherited_claim_moved_past_death"
)
#: Scenario counters of the named delta "whole-year conversion claim"
#: (E1 section 12): paid spouse's excesses resting on a converted disabled
#: worker's conversion claim, and the subset whose months early are
#: positive.  402(q)(1) reduces none of them (they start at FRA); Track
#: A's whole-year count reduces the second, by 2 months for spouses born
#: in 1955 and 4 for 1956 under the statutory schedule and A4's July birth
#: month, in every scenario alike.  Diagnostics only.
CONVERSION_CLAIM_EXCESS = "fra68_spouse_excess_on_conversion_claim"
CONVERSION_CLAIM_MONTHS_EARLY = (
    "fra68_spouse_excess_on_conversion_claim_months_early"
)


def _nullable_int(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)


@dataclass(frozen=True)
class Scenario:
    """One scenario's age-factor rules.

    ``params`` is the bundle every worker and spouse factor reads (the
    baseline bundle, or ``reform.reform_parameters`` of it);
    ``baseline_params`` is always the baseline bundle (the FRA increase
    and the opening-stock ratio are measured against it).
    """

    name: str
    params: SSAParameters
    baseline_params: SSAParameters
    survivor_retirement_age: SurvivorRetirementAge = (
        SurvivorRetirementAge.STATUTORY_MAPPING
    )
    claiming_response: ClaimingResponse = ClaimingResponse.FIXED
    c1_anchor_age: int = 65
    schedule_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "survivor_retirement_age",
            SurvivorRetirementAge(self.survivor_retirement_age),
        )
        object.__setattr__(
            self, "claiming_response", ClaimingResponse(self.claiming_response)
        )

    @property
    def survivor_schedule(self) -> SSAParameters | None:
        """The bundle whose FRA schedule maps survivors (416(l)(2)).

        ``None`` keeps the bundle's own fixed span (Track A's 84 months).
        """
        rule = self.survivor_retirement_age
        if rule is SurvivorRetirementAge.STATUTORY_MAPPING:
            return self.params
        if rule is SurvivorRetirementAge.UNCHANGED_FROM_BASELINE:
            return self.baseline_params
        return None


@dataclass(frozen=True)
class MovedClaimRecord(PiaRecord):
    """A projected retirement claim that C1 or C2 moved (E1 section 13).

    ``reform_claim_month`` is the exact reform claim month
    ``m' = min(12 a + D, 840)`` that ``claim_age_factor`` reads;
    ``entitlement_year`` is the calendar year it falls in under A4's July
    birth month.  The spouse's excess counts its months early from
    ``reform_claim_month`` (:meth:`ScenarioCalculator._spouse_excess`).
    ``baseline_entitlement_year`` is the projected claim's own year before
    the move (the worker's entitlement a conversion claim's count reads,
    :meth:`ScenarioCalculator.excess_months_early`).
    """

    reform_claim_month: int
    baseline_entitlement_year: int | None = None


@dataclass(frozen=True)
class PersonScenario:
    """One person's reference-year benefit in one scenario (monthly)."""

    components: dict[str, float]
    basis: str
    own_kind: str | None
    own_entitlement_year: int | None
    own_claim_age: int | None
    opening_factor_ratio: float | None = None

    @property
    def total(self) -> float:
        return sum(self.components.values())


class ScenarioCalculator(track_benefits._Calculator):
    """Track A's per-person calculator for one exercise-3 scenario.

    Reuses the private ``cola_track_a.benefits._Calculator`` by
    inheritance (plan section 8: "reused by import or by a documented
    copy"): the COLA reform is removed (``self.reform = None``), so both
    of Track A's rate paths are the baseline one, and the methods below
    add the scenario rules of the module docstring.  ``_spouse_excess``
    and ``_widow_excess`` are documented copies of Track A's: the first
    changed only in the months-early count (a moved claim's from its
    exact claim month, a conversion claim's from its baseline start moved
    by the FRA increase) and to count the excesses on a conversion claim,
    the second to read the survivor's cohort span and to count the
    survivors whose inherited credits the model omits.  With
    the baseline bundle and Track A's fixed 84-month survivor span, every
    amount equals Track A's baseline amount bit for bit (the null-reform
    identity test).
    """

    def __init__(
        self,
        context: BenefitContext,
        track_row: RegisteredRow,
        lookups: StateLookups,
        counters: Counter,
        pia_cache: dict,
        scenario: Scenario,
        *,
        assumed_birth_month: int,
    ) -> None:
        if context.params is not scenario.params:
            raise ValueError("the context must carry the scenario's bundle")
        super().__init__(context, track_row, lookups, counters, pia_cache)
        # Exercise 3 reforms no increase: both Track A rate paths are the
        # baseline COLA path.
        self.reform = None
        self.scenario = scenario
        self.assumed_birth_month = int(assumed_birth_month)
        self._conversion_years: dict[int, int] = {}

    # ---- scenario helpers --------------------------------------------
    def _birth(self, person_id: int) -> int:
        return int(self.statics.at[person_id, "birth_year"])

    def conversion_year(self, birth_year: int) -> int:
        """The scenario's FRA attainment year (A4's conversion year)."""

        birth_year = int(birth_year)
        if birth_year not in self._conversion_years:
            self._conversion_years[birth_year] = int(
                fra_attainment_year(
                    np.array([birth_year]),
                    self.ctx.params,
                    assumed_birth_month=self.assumed_birth_month,
                )[0]
            )
        return self._conversion_years[birth_year]

    def converted_in_scenario(self, birth_year: int, state: Any) -> bool:
        """Whether a worker the projection converted is converted here.

        The projection converts at the baseline FRA; in a scenario whose
        FRA is attained after the state's year the worker is still a
        disabled worker.
        """

        if _nullable_int(state["di_conversion_year"]) is None:
            return False
        return self.conversion_year(birth_year) <= int(state["year"])

    def _claim_response(
        self, record: PiaRecord, birth: int, state: Any
    ) -> PiaRecord:
        """C1/C2: move a projected claim by the FRA increase (plan s. 6).

        A moved claim is a :class:`MovedClaimRecord` carrying its exact
        reform claim month; an unmoved one is returned as it is.
        """

        response = self.scenario.claiming_response
        if response is ClaimingResponse.FIXED:
            return record
        claim_year = _nullable_int(state["claim_year"])
        if claim_year is None or claim_year <= self.ctx.cohort.start_year:
            return record
        age = min(record.entitlement_year - birth, _MAX_CLAIM_AGE)
        if (
            response is ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY
            and age < self.scenario.c1_anchor_age
        ):
            return record
        increase = fra_increase_months(
            self.scenario.baseline_params, self.ctx.params, birth
        )
        if increase <= 0:
            return record
        months = min(_MONTHS * age + increase, AGE_70_MONTHS)
        shift = (self.assumed_birth_month - 1 + months) // _MONTHS - age
        fields = {
            item.name: getattr(record, item.name)
            for item in dataclasses.fields(PiaRecord)
        }
        fields.update(
            entitlement_year=record.entitlement_year + shift,
            claim_age_factor=claiming.benefit_factor(
                months, birth, self.ctx.params
            ),
        )
        return MovedClaimRecord(
            **fields,
            reform_claim_month=months,
            baseline_entitlement_year=record.entitlement_year,
        )

    # ---- PIA records ---------------------------------------------------
    def own_record_uncounted(
        self, person_id: int, state: Any
    ) -> PiaRecord | None:
        """:meth:`worker_record` without adding to the counters.

        ``projected_person`` has already looked the person's own record up
        and counted any level it could not compute (``_level`` counts on
        every call); the second lookup that labels the person's row must
        not count it again, so the counters mean what Track A's do.
        """

        counters = self.counters
        self.counters = Counter()
        try:
            return self.worker_record(person_id, state)
        finally:
            self.counters = counters

    def worker_record(self, person_id: int, state: Any) -> PiaRecord | None:
        record = super().worker_record(person_id, state)
        if record is None:
            return None
        birth = self._birth(person_id)
        if record.kind == "converted" and not self.converted_in_scenario(
            birth, state
        ):
            return dataclasses.replace(
                record, kind="disabled", component="disabled_worker"
            )
        if record.kind == "retired":
            return self._claim_response(record, birth, state)
        return record

    def deceased_record(self, person_id: int) -> PiaRecord | None:
        """Track A's decedent record; a claim moved past death is undone.

        Under C1/C2 a worker who dies before the scenario's claim year is
        a never-entitled decedent in that scenario (Track A's
        ``deceased_unentitled`` record, factor 1.0: no RIB-LIM and no
        inherited credits; E1 section 12).
        """

        return self._decedent(person_id)[0]

    def _decedent(self, person_id: int) -> tuple[PiaRecord | None, bool]:
        """:meth:`deceased_record`, and whether it undid a moved claim."""

        record = super().deceased_record(person_id)
        death = self.lookups.death_year(person_id)
        if (
            record is not None
            and record.kind == "retired"
            and death is not None
            and record.entitlement_year >= death
        ):
            birth = self._birth(person_id)
            undone = PiaRecord(
                person_id=person_id,
                kind="deceased_unentitled",
                component="retired_worker",
                basis=sb.EligibilityBasis.AGE_62,
                eligibility_year=birth + _RETIREMENT_AGE,
                entitlement_year=None,
                eligibility_pia=record.eligibility_pia,
                claim_age_factor=1.0,
                level_basis=record.level_basis,
            )
            return undone, True
        return record, False

    @staticmethod
    def conversion_claim_year(own: PiaRecord, state: Any) -> int | None:
        """Track A's own claim year of a conversion claim, else ``None``.

        A converted disabled worker's own claim is the conversion unless a
        retirement claim preceded it (a claim year before the projection's
        conversion year).  The year returned is Track A's
        (``_Calculator._own_claim_year``: the claiming step's claim year,
        else the conversion year), so it is the baseline conversion claim
        in every scenario.
        """

        if own.kind != "converted":
            return None
        baseline_year = _nullable_int(state["di_conversion_year"])
        claim = _nullable_int(state["claim_year"])
        if baseline_year is None or (
            claim is not None and claim < baseline_year
        ):
            return None
        return track_benefits._Calculator._own_claim_year(own, state)

    def _own_claim_year(self, own: PiaRecord, state: Any) -> int | None:
        """Track A's rule; a conversion claim enters the scenario's year.

        The year gates the spouse's excess (entitled by the reference
        year, at 62 or older); a conversion claim's months early are
        counted by :func:`reform.conversion_claim_excess_months_early`.
        """

        if self.conversion_claim_year(own, state) is not None:
            scenario_year = self.conversion_year(int(state["birth_year"]))
            if scenario_year != _nullable_int(state["di_conversion_year"]):
                return scenario_year
        return track_benefits._Calculator._own_claim_year(own, state)

    # ---- spouses ---------------------------------------------------------
    @staticmethod
    def own_claim_month(own: PiaRecord, own_claim: int, birth: int) -> int:
        """The month of age at which the person's own claim starts.

        A claim C1 or C2 moved starts at its exact reform claim month (the
        month its factor reads); any other claim at 12 times its year
        minus the birth year, Track A's whole-year count.  (A conversion
        claim's excess is counted by
        :func:`reform.conversion_claim_excess_months_early` instead.)
        """

        if isinstance(own, MovedClaimRecord):
            return int(own.reform_claim_month)
        return _MONTHS * (int(own_claim) - int(birth))

    def excess_months_early(
        self,
        own: PiaRecord,
        state: Any,
        own_claim: int,
        worker: PiaRecord,
        birth: int,
    ) -> int:
        """Months early of the person's spouse's excess in this scenario.

        A conversion claim (:meth:`conversion_claim_year`): Track A's
        baseline count in every scenario and under every claiming
        response, the baseline start moved by the FRA increase
        (:func:`reform.conversion_claim_excess_months_early`; E1 section
        11).  The start reads the worker's baseline entitlement year: a
        worker's claim C1 or C2 moved enters at its year before the move
        (``MovedClaimRecord.baseline_entitlement_year``), so the move does
        not change the count (it still gates the excess through the
        worker's reform entitlement year).  Any other claim: from the
        later of the own claim month (:meth:`own_claim_month`) and the
        worker's entitlement in this scenario
        (:func:`reform.spouse_excess_months_early`).
        """

        conversion = self.conversion_claim_year(own, state)
        if conversion is not None:
            worker_year = worker.entitlement_year
            if isinstance(worker, MovedClaimRecord) and (
                worker.baseline_entitlement_year is not None
            ):
                worker_year = worker.baseline_entitlement_year
            return conversion_claim_excess_months_early(
                conversion_claim_year=conversion,
                worker_entitlement_year=worker_year,
                birth_year=birth,
                baseline=self.scenario.baseline_params,
                params=self.ctx.params,
            )
        return spouse_excess_months_early(
            own_claim_month=self.own_claim_month(own, own_claim, birth),
            worker_entitlement_year=worker.entitlement_year,
            birth_year=birth,
            params=self.ctx.params,
        )

    def _spouse_excess(
        self, person_id: int, state: Any, own: PiaRecord
    ) -> tuple[float, float] | None:
        # A documented copy of Track A's ``_Calculator._spouse_excess``;
        # the changes are the months-early count
        # (:meth:`excess_months_early`) and the two diagnostic
        # counters of excesses on a conversion claim, which change no
        # amount.  The count reads the exact moved claim month of a claim
        # C1 or C2 moved (E1 section 13, referee required change 1):
        # counting from the whole year the moved claim falls in changed a
        # moved spouse's reduction by D - 12 x (the year shift) months with
        # no response behind it.  A conversion claim keeps Track A's
        # baseline count in every scenario (E1 section 11, the review of
        # ``e1-draft-4``): counting from the whole scenario conversion year
        # changed its reduction by the change in FRA mod 12 with nothing in
        # the statute behind it.  In the baseline scenario the count is
        # Track A's, bit for bit.
        spouse_id = _nullable_int(state["spouse_person_id"])
        # Named gap (Track A): a spouse's excess needs the worker's
        # simulated state and career, which exist only for a linked spouse
        # in the opening roster.  Each claimant this leaves unassessed is
        # counted.
        if spouse_id is None:
            self.counters["spouse_unlinked"] += 1
            return None
        if spouse_id not in self.ctx.cohort.roster_ids:
            self.counters["spouse_outside_roster"] += 1
            return None
        if not self.lookups.alive(spouse_id):
            # The marital step widows the partner of a rostered spouse who
            # dies, so this state should not occur; count it if it does.
            self.counters["spouse_rostered_but_absent"] += 1
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
        own_claim = self._own_claim_year(own, state)
        if own_claim is None:
            self.counters["spouse_own_claim_year_missing"] += 1
            return None
        # SpouseEntitlementRule.OWN_CLAIM_NOT_BEFORE_WORKER: the later of
        # the person's own simulated claim and the worker's entitlement.
        entitlement = max(own_claim, worker.entitlement_year)
        if entitlement > self.ctx.config.reference_year:
            return None
        if entitlement - birth < _RETIREMENT_AGE:
            self.counters["spouse_entitlement_before_62"] += 1
            return None
        worker_start = self._exposure_start(worker, entitlement)
        own_start = self._exposure_start(own)
        if worker_start is None or own_start is None:
            return None
        worker_pia = self._pia_paths(worker, worker_start)
        own_pia = self._pia_paths(own, own_start)
        months_early = self.excess_months_early(
            own, state, own_claim, worker, birth
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
        if self.conversion_claim_year(own, state) is not None:
            self.counters[CONVERSION_CLAIM_EXCESS] += 1
            if months_early > 0:
                self.counters[CONVERSION_CLAIM_MONTHS_EARLY] += 1
        return amounts[0], amounts[1]

    # ---- widow(er)s ------------------------------------------------------
    def survivor_bundle(self, birth_year: int) -> SSAParameters:
        """The scenario bundle with the survivor cohort's reduction span."""

        schedule = self.scenario.survivor_schedule
        if schedule is None:
            return self.ctx.params
        return survivor_parameters(
            self.ctx.params, birth_year, schedule=schedule
        )

    def _widow_excess(
        self,
        person_id: int,
        state: Any,
        own: PiaRecord | None,
        own_paths: tuple[dict[int, float], dict[int, float]] | None,
    ) -> tuple[tuple[float, float], int] | None:
        # A documented copy of Track A's ``_Calculator._widow_excess``;
        # the changes are ``params = self.survivor_bundle(birth)`` in
        # place of ``self.ctx.params``, so the widow(er)'s months early and
        # reduction span follow the survivor's cohort, and the diagnostic
        # count of survivors whose inherited credits the model omits
        # (:meth:`_count_credits_not_inherited`), which changes no amount.
        deceased_id = _nullable_int(state["late_spouse_person_id"])
        widowhood = _nullable_int(state["widowhood_year"])
        if deceased_id is None or widowhood is None:
            self.counters["widow_without_linked_deceased"] += 1
            return None
        if deceased_id not in self.ctx.cohort.roster_ids:
            self.counters["widow_deceased_outside_roster"] += 1
            return None
        if self.lookups.death_year(deceased_id) != widowhood:
            self.counters["widow_death_year_disagrees_with_roster"] += 1
            return None
        birth = int(self.statics.at[person_id, "birth_year"])
        params = self.survivor_bundle(birth)
        entitlement = max(
            widowhood, birth + params.survivor_earliest_claim_age
        )
        if entitlement > self.ctx.config.reference_year:
            return None
        deceased, undone = self._decedent(deceased_id)
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
        self._count_credits_not_inherited(
            deceased, deceased_id, widowhood, undone
        )
        return excess, self.reduced_count(deceased.eligibility_year, start)

    def _count_credits_not_inherited(
        self,
        deceased: PiaRecord,
        deceased_id: int,
        death_year: int,
        undone: bool,
    ) -> None:
        """Diagnostic for a named delta (E1 section 12; changes no amount).

        402(e)(2)(C) and 402(f)(2)(C) base a widow(er)'s benefit on the
        old-age benefit, with delayed retirement credits, that a deceased
        worker "was (or upon application would have been) entitled to",
        counting increment months through the month before death.  The
        model's never-entitled decedent (Track A's ``deceased_unentitled``
        record) carries factor 1.0, so a paid widow(er)'s excess that rests
        on one who died in or after the calendar year of attaining the
        scenario's retirement age (A4's July birth month) inherits no
        credits where the statute would pass some.
        :data:`CREDITS_NOT_INHERITED` counts these paid excesses;
        :data:`CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH` counts the
        subset whose decedent claimed in the projection and whose claim C1
        or C2 moved past death (reform scenario only).  The count is not a
        bound on the survivors the statute would pass credits to: the death
        year is annual, so it can include a decedent who died in the
        attainment year before the retirement-age month (no credits due),
        and it omits a survivor paid no excess without the credits whom the
        credits would have given one.
        """

        if deceased.kind != "deceased_unentitled":
            return
        if death_year < self.conversion_year(self._birth(deceased_id)):
            return
        self.counters[CREDITS_NOT_INHERITED] += 1
        if undone:
            self.counters[CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH] += 1

    # ---- opening stock ---------------------------------------------------
    def opening_claim_age_months(
        self, record: OpeningStockRecord
    ) -> int | None:
        """The claim age an opening-stock factor ratio reads, in months.

        A3's ``opening_claim_age`` for a retired-worker record (its
        ``opening_claim_year`` minus the birth year), else the record's
        entitlement year minus the birth year; for a spouse record, the
        entitlement year (A3's receipt start) minus the birth year.
        """

        birth = self._birth(record.person_id)
        if record.component == "retired_worker":
            age = _nullable_int(
                self.statics.at[record.person_id, "opening_claim_age"]
            )
            if age is None:
                age = record.entitlement_year - birth
            return _MONTHS * age
        if record.component == "spouse":
            return _MONTHS * (record.entitlement_year - birth)
        return None

    def opening_scenario(
        self, record: OpeningStockRecord, state: Any
    ) -> tuple[dict[str, float], float]:
        """Monthly amount and label of an opening-stock person, and ratio."""

        components, _count = super().opening_person(record, state)
        ((label, (amount, _same)),) = components.items()
        birth = int(state["birth_year"])
        if (
            record.component == "disabled_worker"
            and label == "retired_worker"
            and not self.converted_in_scenario(birth, state)
        ):
            label = "disabled_worker"
        ratio = opening_stock_factor_ratio(
            record.component,
            self.opening_claim_age_months(record),
            birth,
            self.scenario.baseline_params,
            self.ctx.params,
        )
        return {label: amount * ratio}, ratio


def scenario_benefits(
    result: ProjectionResult,
    *,
    context: BenefitContext,
    track_row: RegisteredRow,
    scenario: Scenario,
    lookups: StateLookups,
    pia_cache: dict,
    assumed_birth_month: int,
) -> tuple[dict[int, PersonScenario], Counter]:
    """Every person alive in the reference year, in one scenario.

    ``context.params`` must be ``scenario.params``.  The opening-basis
    rule is Track A's: an opening-stock record stays the person's basis
    unless a simulated DI recovery ended a disabled worker's basis.
    """

    del result  # the lookups carry the projected state
    counters: Counter = Counter()
    calculator = ScenarioCalculator(
        context,
        track_row,
        lookups,
        counters,
        pia_cache,
        scenario,
        assumed_birth_month=assumed_birth_month,
    )
    reference = context.config.reference_year
    out: dict[int, PersonScenario] = {}
    for person_id in sorted(int(pid) for pid in lookups.final.index):
        state = lookups.final.loc[person_id]
        opener = context.cohort.opening.get(person_id)
        intact = opener is not None and not (
            opener.status == "disabled_worker"
            and _nullable_int(state["di_recovery_year"]) is not None
        )
        if intact:
            components, ratio = calculator.opening_scenario(opener, state)
            label = next(iter(components))
            if opener.component == "disabled_worker" and (
                label == "retired_worker"
            ):
                label = "converted_di"
            out[person_id] = PersonScenario(
                components=components,
                basis="opening_stock",
                own_kind=f"opening_{label}",
                own_entitlement_year=opener.entitlement_year,
                own_claim_age=None,
                opening_factor_ratio=ratio,
            )
            continue
        pairs, _count = calculator.projected_person(person_id, state)
        own = calculator.own_record_uncounted(person_id, state)
        own_paid = own is not None and own.entitlement_year <= reference
        birth = int(state["birth_year"])
        out[person_id] = PersonScenario(
            components={name: value[0] for name, value in pairs.items()},
            basis="projected",
            own_kind=own.kind if own_paid else None,
            own_entitlement_year=own.entitlement_year if own_paid else None,
            own_claim_age=(
                min(own.entitlement_year - birth, _MAX_CLAIM_AGE)
                if own_paid and own.kind == "retired"
                else None
            ),
        )
    return out, counters


def union_benefit_rows(
    baseline: Mapping[int, PersonScenario],
    reform: Mapping[int, PersonScenario],
    *,
    draw: int,
    context: BenefitContext,
    lookups: StateLookups,
    baseline_params: SSAParameters,
    reform_params: SSAParameters,
) -> tuple[list[dict[str, Any]], Counter]:
    """A7 input rows pairing a baseline and a reform scenario.

    One row per person alive in the reference year whose benefit is
    positive in either scenario.  ``benefit_*`` and the components are
    annual (12 times monthly).  Extra columns are diagnostics A7 ignores.
    """

    if set(baseline) != set(reform):
        raise ValueError("the two scenarios cover different persons")
    counters: Counter = Counter()
    rows = []
    for person_id in sorted(baseline):
        base, new = baseline[person_id], reform[person_id]
        base_total, reform_total = base.total, new.total
        if base_total <= 0 and reform_total <= 0:
            continue
        state = lookups.final.loc[person_id]
        statics = context.cohort.persons_by_id.loc[person_id]
        receipt = statics["ss_receipt_opening"]
        opener = context.cohort.opening.get(person_id)
        if opener is not None and base.basis != "opening_stock":
            counters["opening_di_basis_ended_by_recovery"] += 1
        if opener is None and not pd.isna(receipt) and bool(receipt):
            counters["opening_recipient_without_record"] += 1
        counters[f"beneficiaries_{base.basis}"] += 1
        if pd.isna(receipt):
            counters["beneficiaries_ss_opening_year_unobserved"] += 1
        if base_total > 0 and reform_total <= 0:
            counters["baseline_only_beneficiaries"] += 1
        if reform_total > 0 and base_total <= 0:
            counters["reform_only_beneficiaries"] += 1
        if base.own_kind != new.own_kind:
            counters[f"own_kind_{base.own_kind}_to_{new.own_kind}"] += 1
        names = list(dict.fromkeys([*base.components, *new.components]))
        birth = int(state["birth_year"])
        rows.append(
            {
                "draw": int(draw),
                "person_id": int(person_id),
                "family_unit_id": int(statics["family_unit_id"]),
                "weight": float(state["weight"]),
                "birth_year": birth,
                "beneficiary_base": bool(base_total > 0),
                "beneficiary_reform": bool(reform_total > 0),
                "benefit_base": _MONTHS * base_total,
                "benefit_reform": _MONTHS * reform_total,
                "benefit_components": {
                    name: {
                        "base": _MONTHS * base.components.get(name, 0.0),
                        "reform": _MONTHS * new.components.get(name, 0.0),
                    }
                    for name in names
                },
                "basis": base.basis,
                "fra_increase_months": fra_increase_months(
                    baseline_params, reform_params, birth
                ),
                "own_kind_base": base.own_kind,
                "own_kind_reform": new.own_kind,
                "claim_age_base": base.own_claim_age,
                "claim_age_reform": new.own_claim_age,
                "opening_factor_ratio": new.opening_factor_ratio,
            }
        )
    return rows, counters
