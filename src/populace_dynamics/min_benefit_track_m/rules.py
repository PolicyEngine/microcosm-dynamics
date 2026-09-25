"""The Track M minimum-benefit rules (plan fields G5 and G7-G13, G22, G23).

Python rules (not Axiom).  Every rule below is the plan's proposal
(``EV/critical-path-minimum-benefit-20260924.md``, revision 2, section 7)
applied to Table 5's printed options (cleared extract; ruling C1), with
each open choice read from :class:`~.policy.TrackMPolicy`:

* **Schedule (G7).** Option *k*'s share of the threshold by work years,
  zero below 10 (:class:`~.policy.Schedule`).
* **Threshold and indexing (G8, G9).** The price-indexed minimum uses the
  threshold of the worker's threshold year (the eligibility year; a DI
  worker's onset year).  The wage-indexed minimum carries the policy
  year's threshold forward by the average wage index,
  ``T(Y0) * AWI(e - 2) / AWI(Y0 - 2)``.  The monthly minimum is
  ``M = s(Y*) * T / 12``.
* **DI proration (G12).** ``Y* = Y * 40 / D``, ``D`` the elapsed years from
  the year of attaining 22 through the year before onset, bounded to
  [1, 40]; the schedule applies to ``min(Y*, 40)``, the 10-year floor
  included.
* **Scope (G4, G11).** Only a PIA first calculated in the window (in or
  after the policy year; MS4: after) is cut or floored.
* **Order (G10).** ``max((1 - c) P, M)``; MS2: ``max(P, M) (1 - c)``.
* **Worker flag (G22).** ``Y* >= 10`` and ``M > (1 - c) P`` (MS2:
  ``M > P``), fixed at the first PIA calculation.
* **Who receives (G13, G23).** A person paid their own worker benefit on a
  flagged PIA, or (unless MS3) an auxiliary benefit that is actually paid
  from a linked worker's flagged PIA.  Whether a spouse's or survivor's
  benefit is paid is decided by the oracle's ``spousal_benefit`` and
  ``widow_benefit`` (dual entitlement included); no couples' cap.

The PIA (G5) comes from the oracle, called unchanged: for a retired worker
``ss.statutory_aime.aime`` (42 USC 415(b)(2); for anyone born 1929 or later
it equals ``ss.benefits.aime``, its docstring says) and ``ss.benefits.pia``
at the eligibility year's bend points; for a DI worker Track A's disclosed
``cola_track_a.benefits.approximate_pia`` (MS6: the statutory DI
computation years).  Nothing is added to ``ss/``.

The threshold (G8) is the Census weighted average for one person aged 65
and over, from the pinned 2003-2022 capture (:mod:`.thresholds`).

What this module does not do: read PSID, classify entitlement, link
spouses or tabulate a share.  Those are plan items M3, M4 and M8.  It
never sees a comparator value.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from populace_dynamics.min_benefit_track_m.policy import (
    COUNT_OWN_ONLY,
    DI_PIA_APPROXIMATE,
    MINIMUM_ROUNDING_DIME,
    OPTIONS,
    ORDER_FLOOR_AFTER_CUT,
    PRORATED_YEARS_FLOOR,
    WINDOW_IN_OR_AFTER,
    Option,
    TrackMPolicy,
)
from populace_dynamics.min_benefit_track_m.thresholds import (
    AgedThresholds,
    ThresholdsNotCapturedError,
    ThresholdYearMissingError,
    check_threshold_years,
    load_aged_thresholds,
)
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "AgedThresholds",
    "LinkedBenefit",
    "OptionOutcome",
    "PiaRecord",
    "Receipt",
    "ThresholdYearMissingError",
    "ThresholdsNotCapturedError",
    "WorkerInputs",
    "benefit_implied_pia",
    "check_threshold_years",
    "evaluate_worker",
    "history_pia",
    "in_window",
    "load_aged_thresholds",
    "minimum_threshold",
    "monthly_minimum",
    "prorated_work_years",
    "receives_minimum",
    "relative_to_option_1",
    "spouse_excess_paid",
    "survivor_excess_paid",
]

_RETIREMENT_ELIGIBILITY_AGE = 62
_MONTHS = 12


# ---------------------------------------------------------------------------
# Work years, threshold and minimum
# ---------------------------------------------------------------------------
def _int_year(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer year, not {value!r}")
    return int(value)


def prorated_work_years(
    work_years: float,
    *,
    birth_year: int,
    onset_year: int,
    policy: TrackMPolicy | None = None,
) -> float:
    """A DI worker's prorated work years, ``Y*`` (G12).

    ``D`` counts the elapsed years from the year of attaining
    ``policy.di_proration_start_age`` (22) through the year before
    ``onset_year``, bounded to [1, 40]; ``Y* = Y * 40 / D``, capped at 40.
    ``policy.di_prorated_years_rounding`` is ``"exact"`` (the plan's
    INVENTED case D) or ``"floor"``.
    """

    policy = policy or TrackMPolicy()
    birth = _int_year(birth_year, "birth_year")
    onset = _int_year(onset_year, "onset_year")
    years = float(work_years)
    if not math.isfinite(years) or years < 0:
        raise ValueError(f"work years must be nonnegative, not {work_years}")
    cap = policy.di_proration_cap_years
    elapsed = onset - (birth + policy.di_proration_start_age)
    possible = min(max(elapsed, 1), cap)
    prorated = years * cap / possible
    if policy.di_prorated_years_rounding == PRORATED_YEARS_FLOOR:
        prorated = float(math.floor(prorated + 1e-9))
    return min(prorated, float(cap))


def minimum_threshold(
    threshold_year: int,
    option: Option,
    thresholds: AgedThresholds,
    nawi: Mapping[int, float],
    policy: TrackMPolicy | None = None,
) -> float:
    """The annual threshold option ``option`` applies in ``threshold_year``.

    Price indexing (G8, G9): the threshold of the year itself (thresholds
    move with prices, D5).  Wage indexing (G9): the policy year's threshold
    times ``AWI(year - lag) / AWI(policy year - lag)``, with the lag of 2
    years the plan proposes as a builder default.
    """

    policy = policy or TrackMPolicy()
    year = _int_year(threshold_year, "threshold_year")
    if option.indexing == "price":
        return thresholds.for_year(year)
    if option.indexing == "wage":
        base = policy.policy_year
        lag = policy.wage_index_lag_years
        for needed in (year - lag, base - lag):
            if needed not in nawi:
                raise KeyError(f"no average wage index for {needed}")
        return (
            thresholds.for_year(base)
            * float(nawi[year - lag])
            / float(nawi[base - lag])
        )
    raise ValueError(f"option {option.number} has no minimum")


def monthly_minimum(
    option: Option,
    work_years_star: float,
    annual_threshold: float,
    policy: TrackMPolicy | None = None,
) -> float:
    """``M = s(Y*) * T / 12`` (G7, G8), rounded per ``minimum_rounding``."""

    policy = policy or TrackMPolicy()
    if option.schedule is None:
        return 0.0
    amount = option.schedule.share(work_years_star) * annual_threshold
    amount /= _MONTHS
    if policy.minimum_rounding == MINIMUM_ROUNDING_DIME:
        amount = math.floor(amount * 10.0 + 1e-9) / 10.0
    return amount


def in_window(first_pia_year: int, policy: TrackMPolicy | None = None) -> bool:
    """Whether a PIA first calculated in ``first_pia_year`` is reached.

    G4: in or after the policy year; MS4: after it.
    """

    policy = policy or TrackMPolicy()
    year = _int_year(first_pia_year, "first_pia_year")
    if policy.window_rule == WINDOW_IN_OR_AFTER:
        return year >= policy.policy_year
    return year > policy.policy_year


# ---------------------------------------------------------------------------
# One worker under one option
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkerInputs:
    """What the worker flag needs about one worker (the cohort supplies it).

    ``pia`` is *P* (G5), monthly, at the first calculation, in the
    eligibility year's dollars.  ``work_years`` is *Y* (G6).
    ``first_pia_year`` is the year the PIA was first calculated (the
    entitlement year; G4, G11).  ``threshold_year`` is the year whose
    threshold the minimum uses (G8: the eligibility year; a DI worker's
    onset year).  ``di_onset_year`` marks a DI-origin worker, whose work
    years are prorated (G12) and whose flag carries over at conversion.
    """

    pia: float
    work_years: float
    first_pia_year: int
    threshold_year: int
    birth_year: int
    di_onset_year: int | None = None

    def __post_init__(self) -> None:
        if not (math.isfinite(float(self.pia)) and self.pia >= 0):
            raise ValueError("pia must be finite and nonnegative")
        if not (
            math.isfinite(float(self.work_years)) and self.work_years >= 0
        ):
            raise ValueError("work_years must be finite and nonnegative")
        for label in ("first_pia_year", "threshold_year", "birth_year"):
            _int_year(getattr(self, label), label)
        if self.di_onset_year is not None:
            _int_year(self.di_onset_year, "di_onset_year")


@dataclass(frozen=True)
class OptionOutcome:
    """A worker's PIA under one option, and whether it rests on the minimum.

    ``cut_pia`` is the PIA after the option's uniform cut (the PIA itself
    outside the window); ``minimum`` is the monthly minimum (0 when the
    option has none or ``work_years_star`` is below the floor);
    ``option_pia`` is the PIA the option pays; ``on_minimum`` is the worker
    flag *O* (G22).  ``reason`` is one of ``pia_before_window``,
    ``no_minimum_option``, ``below_floor_years``, ``benefit_above_minimum``
    and ``on_minimum``.
    """

    option: int
    in_window: bool
    work_years_star: float
    minimum: float
    cut_pia: float
    option_pia: float
    on_minimum: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "option": self.option,
            "in_window": self.in_window,
            "work_years_star": self.work_years_star,
            "minimum": self.minimum,
            "cut_pia": self.cut_pia,
            "option_pia": self.option_pia,
            "on_minimum": self.on_minimum,
            "reason": self.reason,
        }


def evaluate_worker(
    worker: WorkerInputs,
    option_number: int,
    *,
    thresholds: AgedThresholds,
    nawi: Mapping[int, float],
    policy: TrackMPolicy | None = None,
) -> OptionOutcome:
    """Apply option ``option_number`` to ``worker`` (G4, G7-G12, G22).

    Outside the window the PIA is unchanged and the flag is 0 (plan
    section 1: a PIA first calculated before the policy year has *O* = 0
    under every option).  The threshold is looked up only when a minimum
    can apply.
    """

    policy = policy or TrackMPolicy()
    if option_number not in OPTIONS:
        raise ValueError(f"option must be one of {sorted(OPTIONS)}")
    option = OPTIONS[option_number]
    pia = float(worker.pia)
    if worker.di_onset_year is None:
        years_star = float(worker.work_years)
    else:
        years_star = prorated_work_years(
            worker.work_years,
            birth_year=worker.birth_year,
            onset_year=worker.di_onset_year,
            policy=policy,
        )
    if not in_window(worker.first_pia_year, policy):
        return OptionOutcome(
            option_number,
            False,
            years_star,
            0.0,
            pia,
            pia,
            False,
            "pia_before_window",
        )
    cut = option.uniform_cut
    cut_pia = (1.0 - cut) * pia
    if option.schedule is None:
        return OptionOutcome(
            option_number,
            True,
            years_star,
            0.0,
            cut_pia,
            cut_pia,
            False,
            "no_minimum_option",
        )
    if years_star < option.schedule.floor_years:
        return OptionOutcome(
            option_number,
            True,
            years_star,
            0.0,
            cut_pia,
            cut_pia,
            False,
            "below_floor_years",
        )
    annual = minimum_threshold(
        worker.threshold_year, option, thresholds, nawi, policy
    )
    minimum = monthly_minimum(option, years_star, annual, policy)
    if policy.order == ORDER_FLOOR_AFTER_CUT:
        on_minimum = minimum > cut_pia
        option_pia = max(cut_pia, minimum)
    else:
        on_minimum = minimum > pia
        option_pia = max(pia, minimum) * (1.0 - cut)
    return OptionOutcome(
        option_number,
        True,
        years_star,
        minimum,
        cut_pia,
        option_pia,
        on_minimum,
        "on_minimum" if on_minimum else "benefit_above_minimum",
    )


def relative_to_option_1(
    outcome: OptionOutcome, baseline: OptionOutcome
) -> float:
    """``option PIA / option-1 PIA - 1`` (fn. 33's distinction; not *S*).

    Footnote 33 says receiving the minimum is not the same as being better
    off than under option 1; the plan's INVENTED case H is on option 2's
    minimum and still below option 1.  ``baseline`` must be option 1.
    """

    if baseline.option != 1:
        raise ValueError("the baseline must be option 1")
    if baseline.option_pia <= 0:
        raise ValueError("the option-1 PIA must be positive")
    return outcome.option_pia / baseline.option_pia - 1.0


# ---------------------------------------------------------------------------
# The PIA through the oracle (G5, MS5, MS6)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PiaRecord:
    """A worker's PIA at first calculation and how it was computed."""

    pia: float
    aime: float | None
    basis: str
    method: str
    eligibility_year: int
    computation_end_year: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pia": self.pia,
            "aime": self.aime,
            "basis": self.basis,
            "method": self.method,
            "eligibility_year": self.eligibility_year,
            "computation_end_year": self.computation_end_year,
        }


def _through(history: Mapping[int, float], last: int) -> dict[int, float]:
    return {
        int(year): float(value)
        for year, value in history.items()
        if int(year) <= last and not math.isnan(float(value))
    }


def history_pia(
    history: Mapping[int, float],
    *,
    birth_year: int,
    params: SSAParameters,
    basis: str = "old_age",
    onset_year: int | None = None,
    death_year: int | None = None,
    policy: TrackMPolicy | None = None,
) -> PiaRecord:
    """*P* from a realized history through the oracle, unchanged (G5).

    ``basis``:

    * ``"old_age"``: the history through the year before the eligibility
      year (the year of attaining 62), ``ss.statutory_aime.aime`` (the
      statutory computation years; for birth years 1929 and later its
      docstring says it equals ``ss.benefits.aime`` exactly) and
      ``ss.benefits.pia`` at the eligibility year's bend points.  No
      recomputation for later earnings (G5).
    * ``"disability"``: eligibility is the onset year.  ``di_pia_rule``
      ``approximate_pia`` (G5) calls Track A's
      ``cola_track_a.benefits.approximate_pia`` through the year before
      onset; ``statutory_computation_years`` (MS6) calls
      ``ss.statutory_aime.aime(..., disability_year=onset)`` and
      ``ss.benefits.pia`` at the onset year's bend points.
    * ``"death"``: a worker who died before eligibility, whose PIA is first
      calculated for a survivor; ``approximate_pia`` through the year
      before death at the death year's bend points (``death_pia_rule``,
      a builder default: the plan is silent on it).
    """

    policy = policy or TrackMPolicy()
    birth = _int_year(birth_year, "birth_year")
    if basis == "old_age":
        eligibility = birth + _RETIREMENT_ELIGIBILITY_AGE
        kept = _through(history, eligibility - 1)
        aime = statutory_aime.aime(kept, birth, params)
        return PiaRecord(
            benefits.pia(aime, eligibility, params),
            float(aime),
            basis,
            "ss.statutory_aime.aime + ss.benefits.pia",
            eligibility,
            eligibility - 1,
        )
    if basis == "disability":
        if onset_year is None:
            raise ValueError("a disability basis needs onset_year")
        onset = _int_year(onset_year, "onset_year")
        kept = _through(history, onset - 1)
        if policy.di_pia_rule == DI_PIA_APPROXIMATE:
            from populace_dynamics.cola_track_a.benefits import (
                approximate_pia,
            )

            return PiaRecord(
                approximate_pia(
                    kept,
                    birth_year=birth,
                    computation_end_year=onset - 1,
                    eligibility_year=onset,
                    params=params,
                ),
                None,
                basis,
                "cola_track_a.benefits.approximate_pia",
                onset,
                onset - 1,
            )
        aime = statutory_aime.aime(kept, birth, params, disability_year=onset)
        return PiaRecord(
            benefits.pia(aime, onset, params),
            float(aime),
            basis,
            "ss.statutory_aime.aime(disability_year) + ss.benefits.pia",
            onset,
            onset - 1,
        )
    if basis == "death":
        if death_year is None:
            raise ValueError("a death basis needs death_year")
        death = _int_year(death_year, "death_year")
        if policy.death_pia_rule != DI_PIA_APPROXIMATE:
            raise ValueError(policy.death_pia_rule)
        from populace_dynamics.cola_track_a.benefits import approximate_pia

        kept = _through(history, death - 1)
        return PiaRecord(
            approximate_pia(
                kept,
                birth_year=birth,
                computation_end_year=death - 1,
                eligibility_year=death,
                params=params,
            ),
            None,
            basis,
            "cola_track_a.benefits.approximate_pia",
            death,
            death - 1,
        )
    raise ValueError("basis must be old_age, disability or death")


def benefit_implied_pia(
    observed_monthly_benefit: float,
    *,
    claim_factor: float,
    cola_factor: float,
) -> float:
    """MS5: the PIA implied by an observed benefit.

    ``observed / (claim_factor * cola_factor)``: ``claim_factor`` is the
    benefit-to-PIA factor of the claim age (402(q) or 402(w); the cohort
    brackets the claim age from first receipt) and ``cola_factor`` the
    cumulative COLA from the eligibility year to the observed year.  No
    rounding.
    """

    for label, value in (
        ("observed_monthly_benefit", observed_monthly_benefit),
        ("claim_factor", claim_factor),
        ("cola_factor", cola_factor),
    ):
        if not math.isfinite(float(value)):
            raise ValueError(f"{label} must be finite")
    if claim_factor <= 0 or cola_factor <= 0:
        raise ValueError("claim_factor and cola_factor must be positive")
    if observed_monthly_benefit < 0:
        raise ValueError("observed_monthly_benefit must be nonnegative")
    return float(observed_monthly_benefit) / (claim_factor * cola_factor)


# ---------------------------------------------------------------------------
# Auxiliaries and who counts as receiving (G13, G23)
# ---------------------------------------------------------------------------
def spouse_excess_paid(
    own_amount: float,
    worker_option_pia: float,
    months_early: int,
    params: SSAParameters,
) -> bool:
    """Whether a spouse's benefit on the worker's option PIA is paid.

    ``ss.benefits.spousal_benefit`` (unchanged): one-half of the worker's
    PIA less the spouse's own PIA (dual entitlement), reduced for early
    claiming.  Paid when positive.
    """

    return (
        benefits.spousal_benefit(
            own_amount, worker_option_pia, months_early, params
        )
        > 0.0
    )


def survivor_excess_paid(
    own_amount: float,
    deceased_option_pia: float,
    survivor_months_early: int,
    deceased_claim_factor: float,
    params: SSAParameters,
) -> bool:
    """Whether a widow(er)'s benefit on the deceased's option PIA is paid.

    ``ss.benefits.widow_benefit`` (unchanged) returns the larger of the
    survivor's own amount and the widow(er)'s benefit; it is paid on the
    deceased's record when it exceeds the own amount.
    """

    paid = benefits.widow_benefit(
        own_amount,
        deceased_option_pia,
        survivor_months_early,
        deceased_claim_factor,
        params,
    )
    return paid > own_amount


@dataclass(frozen=True)
class LinkedBenefit:
    """An auxiliary benefit from a linked worker's record (G13).

    ``kind`` is ``"spouse"`` or ``"survivor"``; ``worker_on_minimum`` is the
    linked worker's flag under the option; ``paid`` is whether the
    auxiliary benefit is actually paid under the option
    (:func:`spouse_excess_paid`, :func:`survivor_excess_paid`).
    """

    kind: str
    worker_on_minimum: bool
    paid: bool

    def __post_init__(self) -> None:
        if self.kind not in ("spouse", "survivor"):
            raise ValueError("kind must be spouse or survivor")


@dataclass(frozen=True)
class Receipt:
    """Whether a person counts as receiving the minimum (*A*, G23).

    ``basis`` is ``own_worker_pia``, ``linked_worker_pia``, ``none`` or
    ``unlinked_auxiliary`` (an auxiliary beneficiary with no linked worker:
    counted as not receiving and reported separately, G13).
    """

    receives: bool
    basis: str


def receives_minimum(
    *,
    own_on_minimum: bool,
    paid_own_worker_benefit: bool,
    linked: Sequence[LinkedBenefit] = (),
    unlinked_auxiliary: bool = False,
    policy: TrackMPolicy | None = None,
) -> Receipt:
    """*A* for one person under one option (G23; MS3 own PIA only)."""

    policy = policy or TrackMPolicy()
    if own_on_minimum and paid_own_worker_benefit:
        return Receipt(True, "own_worker_pia")
    if policy.counting_rule == COUNT_OWN_ONLY:
        return Receipt(False, "none")
    if any(link.worker_on_minimum and link.paid for link in linked):
        return Receipt(True, "linked_worker_pia")
    if unlinked_auxiliary:
        return Receipt(False, "unlinked_auxiliary")
    return Receipt(False, "none")
