"""Benefit-only D/S versions; a2-ratified-1 §§3–5, with untouched v1 code.

The mixin intercepts only DI levels and DI-origin spouse calculations.
Ordinary retirement and death keep the v1 level code and conventions.
"""

import hashlib
import json
from collections import Counter

import pandas as pd

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a import benefits as legacy
from populace_dynamics.cola_track_a.config import LevelPolicy
from populace_dynamics.fra68_track import benefits as fra
from populace_dynamics.ss import benefits as ss_benefits
from populace_dynamics.ss import statutory_aime
from populace_dynamics.track_a_v2.filing import (
    FilingRefusal,
    application_month,
    classify_ordering,
    spouse_timing,
)
from populace_dynamics.track_a_v2.histories import HistoryValidator, nullable

# §4.3 pins retirement to the unchanged inherited Track A convention.
TRACK_A_COMPUTATION_YEARS = statutory_aime.ComputationYears.LEGACY_FIXED_35


def statutory_di_aime(history, *, birth_year, eligibility_year, params):
    """D retains the eligibility year itself (§4.3), including its earnings."""
    kept = {
        int(year): float(value)
        for year, value in history.items()
        if int(year) <= eligibility_year
    }
    return statutory_aime.aime(
        kept, int(birth_year), params, disability_year=int(eligibility_year)
    )


def statutory_di_pia(history, *, birth_year, eligibility_year, params):
    """D changes only computation years, retaining e's bend points."""
    return ss_benefits.pia(
        statutory_di_aime(
            history,
            birth_year=birth_year,
            eligibility_year=eligibility_year,
            params=params,
        ),
        eligibility_year,
        params,
    )


def attach_attempt(error, counters, person_id):
    """§10: an interrupted person keeps its counters and identity.

    Any failure or interruption inside a per-person body carries the
    collector's cumulative counters. An inner person attribution, such as
    a linked spouse's refusal, is kept rather than replaced.
    """
    error.counters = dict(counters)
    if not hasattr(error, "person_id"):
        error.person_id = person_id


def pia_parameter_fingerprint(params, eligibility_year):
    """§4.3: bind AWI, wage bases, actual bend points, and PIA factors."""
    return hashlib.sha256(
        json.dumps(
            [
                sorted(params.nawi.items()),
                sorted(params.wage_base.items()),
                params.bend_points(eligibility_year),
                params.pia_factors,
            ],
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


class _Mechanisms:
    def __init__(
        self,
        *args,
        mechanism="L",
        history_validator=None,
        di_computation=None,
        **kwargs,
    ):
        self.mechanism = str(getattr(mechanism, "value", mechanism))
        if self.mechanism not in ("L", "D", "S", "DS"):
            raise ValueError("unknown Track A v2 mechanism")
        self.history_validator = history_validator
        self.di_computation = di_computation or (
            "statutory_415_b_2"
            if self.mechanism in ("D", "DS")
            else "legacy_fixed_35"
        )
        if self.di_computation not in ("legacy_fixed_35", "statutory_415_b_2"):
            raise ValueError("unknown DI computation convention")
        super().__init__(*args, **kwargs)

    def _level(self, person_id, tag, year, policy):
        if year < legacy.FIRST_ORACLE_ELIGIBILITY_YEAR:
            return super()._level(person_id, tag, year, policy)
        if policy is LevelPolicy.EXCLUDE:
            return super()._level(person_id, tag, year, policy)
        convention = self.di_computation if tag == "di" else "legacy_fixed_35"
        if tag == "di" and convention == "statutory_415_b_2":
            if self.history_validator is None:
                raise ValueError("D requires immutable projection histories")
            proxy = self.history_validator.validate(person_id, year)
            # Counters count level requests consistently across cache hits;
            # §4.4 is silent on deduplication, so row/scenario scope is kept.
            self.counters[proxy] += 1
        birth = int(self.statics.at[person_id, "birth_year"])
        history = tuple(sorted(self._history(person_id).items()))
        fingerprint = pia_parameter_fingerprint(self.ctx.params, year)
        key = ("track_a_v2", convention, fingerprint, birth, history)
        outer = self.cache
        scoped = outer.setdefault(key, {})
        if tag == "di" and convention == "statutory_415_b_2":
            inner = (person_id, tag, year)
            if inner not in scoped:
                scoped[inner] = statutory_di_pia(
                    self._history(person_id),
                    birth_year=birth,
                    eligibility_year=year,
                    params=self.ctx.params,
                )
            return scoped[inner], "statutory_di_computation_years"
        self.cache = scoped
        try:
            return super()._level(person_id, tag, year, policy)
        finally:
            self.cache = outer

    def projected_person(self, person_id, state):
        try:
            return self._projected_person(person_id, state)
        except ValueError as exc:
            exc.counters = dict(self.counters)
            if not hasattr(exc, "person_id"):
                exc.person_id = person_id
            raise

    def _projected_person(self, person_id, state):
        components, count = super().projected_person(person_id, state)
        if self.mechanism not in ("S", "DS"):
            return components, count
        # v1's dispatch suppresses active DI spouses at benefits.py:571.
        # Converted DI already dispatches through our _spouse_excess.
        saved = self.counters
        self.counters = Counter()
        try:
            own = self.worker_record(person_id, state)
        finally:
            self.counters = saved
        if (
            state["marital_status"] == "married"
            and own is not None
            and own.kind == "disabled"
            and own.eligibility_pia is not None
            and own.entitlement_year <= self.ctx.config.reference_year
        ):
            excess = self._spouse_excess(person_id, state, own)
            if excess is not None:
                components["spouse"] = excess
        return components, count

    def _spouse_excess(self, person_id, state, own):
        if self.mechanism not in ("S", "DS") or own.kind not in (
            "disabled",
            "converted",
        ):
            return super()._spouse_excess(person_id, state, own)
        if self.history_validator is None:
            raise ValueError("S requires immutable projection histories")
        # §5.4's ended-spell row refuses every reached DI-origin spell.
        # Conservatively apply that explicit predicate before payment gates;
        # the later amount-step scope limits ordering classes, not recovery.
        if self.history_validator.event_counts(person_id)["recovery"]:
            raise FilingRefusal(
                person_id, "earlier DI spell ended before re-award"
            )
        baseline_state = self.history_validator.lookups.final.loc[person_id]
        _, entitlement, _ = self.history_validator.baseline_di_record(
            person_id, baseline_state
        )
        birth = int(self.statics.at[person_id, "birth_year"])
        claim = nullable(baseline_state.claim_year)
        receipt = self.statics.at[person_id, "ss_receipt_opening"]
        params = (
            self.scenario.baseline_params
            if hasattr(self, "scenario")
            else self.ctx.params
        )
        application = application_month(
            birth_year=birth,
            claim_year=claim,
            entitlement_year=entitlement,
            conversion_year=nullable(baseline_state.di_conversion_year),
            baseline_params=params,
            opening_prior_claim=(
                claim is not None
                and claim <= self.ctx.cohort.start_year
                and not pd.isna(receipt)
                and bool(receipt)
            ),
            reference_year=self.ctx.config.reference_year,
            person_id=person_id,
        )
        self.counters.update(application.counters)
        spouse_id = nullable(state["spouse_person_id"])
        if spouse_id is None:
            self.counters["spouse_unlinked"] += 1
            return None
        if spouse_id not in self.ctx.cohort.roster_ids:
            self.counters["spouse_outside_roster"] += 1
            return None
        if not self.lookups.alive(spouse_id):
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
        worker_year, move = (
            fra.ScenarioCalculator.worker_entitlement_start(worker)
            if hasattr(self, "scenario")
            else (worker.entitlement_year, 0)
        )
        timing = spouse_timing(
            application,
            birth_year=birth,
            worker_entitlement_year=worker.entitlement_year,
            worker_baseline_entitlement_year=worker_year,
            worker_move_months=move,
            fra_months=self.ctx.params.fra_months(birth),
            reference_year=self.ctx.config.reference_year,
        )
        if timing.deferred:
            self.counters["s_entitlement_deferred_to_62"] += 1
        if not timing.payable:
            return None
        ordering = classify_ordering(
            application,
            entitlement_year=timing.year,
            di_entitlement_year=entitlement,
            claim_year=claim,
            recoveries=self.history_validator.event_counts(person_id)[
                "recovery"
            ],
            person_id=person_id,
        )
        self.counters[f"s_ordering_{ordering}"] += 1
        if application.case == "P":
            self.counters["s_rib_to_di_own_reduction_not_modeled"] += 1
        worker_start = self._exposure_start(worker, timing.year)
        own_start = self._exposure_start(own)
        if worker_start is None or own_start is None:
            return None
        worker_pia = self._pia_paths(worker, worker_start)
        own_pia = self._pia_paths(own, own_start)
        amounts = tuple(
            sb.spouse_excess_path(
                worker_pia_by_year=worker_pia[index],
                own_pia_by_year=own_pia[index],
                months_early=timing.months_early,
                entitlement_year=timing.year,
                params=self.ctx.params,
                horizon_year=self.payment_year,
            )[self.payment_year]
            for index in (0, 1)
        )
        if amounts[0] <= 0 and amounts[1] <= 0:
            return None
        self.counters["spouse_excess_paid"] += 1
        return amounts


class TrackACalculator(_Mechanisms, legacy._Calculator):
    """Exercise 1's v2 benefit-only subclass (§4.3)."""


class ScenarioCalculator(_Mechanisms, fra.ScenarioCalculator):
    """Exercise 3's v2 benefit-only subclass (§4.3)."""


def collect_reference_benefit_rows(
    result,
    *,
    draw,
    row,
    context,
    pia_cache=None,
    lookups=None,
    mechanism="L",
    history_validator=None,
    di_computation=None,
):
    """Unfiltered alive-person components for the pre-filter §9 guard.

    Unlike v1 reference_benefit_rows (benefits.py:840–841), baseline-zero
    persons reach the caller. The caller must guard before filtering.
    """
    counters = Counter()
    lookups = lookups or legacy.StateLookups(
        result, context.config.reference_year
    )
    validator = history_validator or HistoryValidator(result, context.cohort)
    calculator = TrackACalculator(
        context,
        row,
        lookups,
        counters,
        {} if pia_cache is None else pia_cache,
        mechanism=mechanism,
        history_validator=validator,
        di_computation=di_computation,
    )
    rows = []
    for pid in sorted(int(i) for i in lookups.final.index):
        try:
            state = lookups.final.loc[pid]
            opener = context.cohort.opening.get(pid)
            intact = opener is not None and not (
                opener.status == "disabled_worker"
                and nullable(state.di_recovery_year) is not None
            )
            statics = context.cohort.persons_by_id.loc[pid]
            receipt = statics.ss_receipt_opening
            if opener is not None and not intact:
                counters["opening_di_basis_ended_by_recovery"] += 1
            if opener is None and not pd.isna(receipt) and bool(receipt):
                counters["opening_recipient_without_record"] += 1
            components, count = (
                calculator.opening_person(opener, state)
                if intact
                else calculator.projected_person(pid, state)
            )
            basis = "opening_stock" if intact else "projected"
            base = sum(pair[0] for pair in components.values())
            reform = sum(pair[1] for pair in components.values())
            if base > 0:
                counters[f"beneficiaries_{basis}"] += 1
                if (
                    intact
                    and opener.entitlement_clamped
                    and row.exposure_clock is sb.ExposureClock.ENTITLEMENT
                ):
                    counters["beneficiaries_opening_entitlement_clamped"] += 1
                if pd.isna(receipt):
                    counters["beneficiaries_ss_opening_year_unobserved"] += 1
            rows.append(
                {
                    "draw": int(draw),
                    "person_id": pid,
                    "family_unit_id": int(statics.family_unit_id),
                    "weight": float(state.weight),
                    "birth_year": int(state.birth_year),
                    "beneficiary_base": base > 0,
                    "beneficiary_reform": reform > 0,
                    "benefit_base": 12 * base,
                    "benefit_reform": 12 * reform,
                    "benefit_components": {
                        name: {"base": 12 * pair[0], "reform": 12 * pair[1]}
                        for name, pair in components.items()
                    },
                    "basis": basis,
                    "reduced_increases": count,
                }
            )
        except (Exception, KeyboardInterrupt) as error:
            attach_attempt(error, counters, pid)
            raise
    return rows, counters


def scenario_benefits(
    result,
    *,
    context,
    track_row,
    scenario,
    lookups,
    pia_cache,
    assumed_birth_month=7,
    mechanism="L",
    history_validator=None,
    di_computation=None,
):
    """Every alive person's scenario components, retaining zeros (§9)."""
    counters = Counter()
    calculator = ScenarioCalculator(
        context,
        track_row,
        lookups,
        counters,
        pia_cache,
        scenario,
        assumed_birth_month=assumed_birth_month,
        mechanism=mechanism,
        history_validator=history_validator
        or HistoryValidator(result, context.cohort),
        di_computation=di_computation,
    )
    out = {}
    for pid in sorted(int(i) for i in lookups.final.index):
        try:
            state = lookups.final.loc[pid]
            opener = context.cohort.opening.get(pid)
            intact = opener is not None and not (
                opener.status == "disabled_worker"
                and nullable(state.di_recovery_year) is not None
            )
            if intact:
                components, ratio = calculator.opening_scenario(opener, state)
                label = next(iter(components))
                if (
                    opener.component == "disabled_worker"
                    and label == "retired_worker"
                ):
                    label = "converted_di"
                out[pid] = fra.PersonScenario(
                    components,
                    "opening_stock",
                    f"opening_{label}",
                    opener.entitlement_year,
                    None,
                    ratio,
                )
                continue
            pairs, _ = calculator.projected_person(pid, state)
            own = calculator.own_record_uncounted(pid, state)
            paid = (
                own is not None
                and own.entitlement_year <= context.config.reference_year
            )
            out[pid] = fra.PersonScenario(
                {name: value[0] for name, value in pairs.items()},
                "projected",
                own.kind if paid else None,
                own.entitlement_year if paid else None,
                (
                    min(own.entitlement_year - int(state.birth_year), 70)
                    if paid and own.kind == "retired"
                    else None
                ),
            )
        except (Exception, KeyboardInterrupt) as error:
            attach_attempt(error, counters, pid)
            raise
    return out, counters
