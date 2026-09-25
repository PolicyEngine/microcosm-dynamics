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

The years that define each record (the M1 specification's section 4a,
referee R3) come from :func:`record_years`: the window year, the threshold
and bend-point year, and the last year of *Y* and of *P*'s history, by the
record's basis (old age, disability origin, or a worker who died before
any own entitlement).

The PIA (G5) comes from the oracle, called unchanged, over that history:
``ss.statutory_aime.aime`` (42 USC 415(b)(2)) and ``ss.benefits.pia`` at
the bend points of the section 4a threshold year.  An old-age history runs
through the year before the first year of entitlement (415(b)(2)(B)(ii)(I));
a disability-origin record uses the statutory DI computation years
(``disability_year=onset``; MS6: Track A's disclosed ``cola_track_a.
benefits.approximate_pia``); a worker who died before any own entitlement
uses the statutory death computation (``death_year=death``).  Nothing is
added to ``ss/``.

The threshold (G8) is the Census weighted average for one person aged 65
and over, read from the pinned capture of the 2003-2022 Census workbooks
(:func:`load_aged_thresholds`); a threshold year the capture lacks raises
:class:`ThresholdYearMissingError`, and :func:`check_threshold_years`
refuses a cohort that needs one before anything is computed.

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
    THRESHOLD_ROW,
    TRACK_M_THRESHOLD_YEARS,
    TRACK_M_THRESHOLDS_PATH,
    TRACK_M_THRESHOLDS_SHA256,
    AgedThresholds,
    ThresholdsNotCapturedError,
    ThresholdYearMissingError,
    check_threshold_years,
    load_aged_thresholds,
)
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "BASES",
    "BASIS_DEATH",
    "BASIS_DISABILITY",
    "BASIS_OLD_AGE",
    "AgedThresholds",
    "LAST_COLA_DETERMINATION_YEAR",
    "LinkedBenefit",
    "OptionOutcome",
    "PiaRecord",
    "Receipt",
    "RecordYears",
    "THRESHOLD_ROW",
    "TRACK_M_THRESHOLDS_PATH",
    "TRACK_M_THRESHOLDS_SHA256",
    "TRACK_M_THRESHOLD_YEARS",
    "ThresholdYearMissingError",
    "ThresholdsNotCapturedError",
    "WorkerInputs",
    "benefit_implied_pia",
    "check_threshold_years",
    "claim_factor",
    "cola_factor",
    "evaluate_worker",
    "history_pia",
    "in_window",
    "load_aged_thresholds",
    "minimum_threshold",
    "monthly_minimum",
    "prorated_work_years",
    "receives_minimum",
    "record_years",
    "relative_to_option_1",
    "spouse_excess_paid",
    "survivor_excess_paid",
    "survivor_own_amount",
]

_RETIREMENT_ELIGIBILITY_AGE = 62
_MONTHS = 12
#: MS5's COLA factor runs through the COLA determined in 2021: from 1983
#: each COLA is "effective in December of the determination year and first
#: reflected in January payments of the following year"
#: (``data/external/ssa_cola_history.json``, ``historical_timing``), so the
#: 2022 determination first reaches January 2023 payments.
LAST_COLA_DETERMINATION_YEAR = 2021


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
    threshold year's dollars.  ``work_years`` is *Y* (G6).
    ``first_pia_year`` is section 4a's window year (G4, G11).
    ``threshold_year`` is section 4a's threshold year (G8: the year of
    attaining 62, a disability-origin record's onset year, or the earlier
    of death and attaining 62).  ``di_onset_year`` marks a DI-origin
    worker, whose work years are prorated (G12) and whose flag carries
    over at conversion.
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
BASIS_OLD_AGE = "old_age"
BASIS_DISABILITY = "disability"
BASIS_DEATH = "death"
#: The three bases of section 4a.
BASES: tuple[str, ...] = (BASIS_OLD_AGE, BASIS_DISABILITY, BASIS_DEATH)


@dataclass(frozen=True)
class RecordYears:
    """The years that define a worker record (M1 specification, section 4a).

    ``window_year`` is G4's "first calculated" year: the first year of the
    worker's own entitlement (old age, or DI for a disability-origin
    record), or, for a worker who died before any own entitlement, the
    first year a person in the universe is entitled to a benefit on the
    record.  ``threshold_year`` is G8's threshold year and the PIA's
    bend-point year.  ``last_year`` is the last year of *Y* (G6) and of
    *P*'s history (G5).
    """

    basis: str
    birth_year: int
    window_year: int
    threshold_year: int
    last_year: int
    onset_year: int | None = None
    death_year: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "basis": self.basis,
            "birth_year": self.birth_year,
            "window_year": self.window_year,
            "threshold_year": self.threshold_year,
            "last_year": self.last_year,
            "onset_year": self.onset_year,
            "death_year": self.death_year,
        }


def record_years(
    *,
    basis: str,
    birth_year: int,
    window_year: int,
    onset_year: int | None = None,
    death_year: int | None = None,
) -> RecordYears:
    """Section 4a: the window, threshold and last years of a worker record.

    * **Old age.**  Threshold and bend-point year: the year of attaining
      62.  *Y* and *P*'s history end with the window year less one (42 USC
      415(b)(2)(B)(ii)(I): an old-age PIA's computation base years end
      before the year of first entitlement).  The window year may not
      precede the year of attaining 62.
    * **Disability origin.**  Threshold and bend-point year: the onset
      year.  *Y* and *P*'s history end with onset less one (G12;
      413(a)(2)(B)(i)).  Onset may not follow the window year.
    * **Died before any own entitlement.**  Threshold and bend-point year:
      the earlier of the death year and the year of attaining 62.  *Y* and
      *P*'s history end with the death year less one (a named
      approximation: 415(b)(2)(B)(ii)(II) would include the death year).
      Death may not follow the window year.
    """

    birth = _int_year(birth_year, "birth_year")
    window = _int_year(window_year, "window_year")
    attains_62 = birth + _RETIREMENT_ELIGIBILITY_AGE
    if basis == BASIS_OLD_AGE:
        if onset_year is not None or death_year is not None:
            raise ValueError("an old-age record takes no onset or death year")
        if window < attains_62:
            raise ValueError(
                f"old-age entitlement in {window} precedes the year of "
                f"attaining 62 ({attains_62})"
            )
        return RecordYears(basis, birth, window, attains_62, window - 1)
    if basis == BASIS_DISABILITY:
        if onset_year is None or death_year is not None:
            raise ValueError(
                "a disability-origin record needs onset_year only"
            )
        onset = _int_year(onset_year, "onset_year")
        if not birth < onset <= window:
            raise ValueError(
                f"onset {onset} must follow birth {birth} and not follow "
                f"the window year {window}"
            )
        return RecordYears(
            basis, birth, window, onset, onset - 1, onset_year=onset
        )
    if basis == BASIS_DEATH:
        if death_year is None or onset_year is not None:
            raise ValueError("a death-basis record needs death_year only")
        death = _int_year(death_year, "death_year")
        if not birth < death <= window:
            raise ValueError(
                f"death {death} must follow birth {birth} and not follow "
                f"the window year {window}"
            )
        return RecordYears(
            basis,
            birth,
            window,
            min(death, attains_62),
            death - 1,
            death_year=death,
        )
    raise ValueError(f"basis must be one of {BASES}, not {basis!r}")


@dataclass(frozen=True)
class PiaRecord:
    """A worker's PIA at first calculation and how it was computed.

    ``eligibility_year`` is the bend-point year (section 4a's threshold
    year); ``computation_end_year`` the last year of the history passed to
    the oracle.
    """

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
    basis: str = BASIS_OLD_AGE,
    window_year: int | None = None,
    onset_year: int | None = None,
    death_year: int | None = None,
    policy: TrackMPolicy | None = None,
) -> PiaRecord:
    """*P* from a realized history through the oracle, unchanged (G5).

    The history is cut at :func:`record_years`' last year and the PIA is
    computed at its threshold year's bend points (section 4a).  ``basis``:

    * ``"old_age"``: ``window_year`` (the first year of entitlement) is
      required; ``ss.statutory_aime.aime`` over the history through the
      window year less one (for birth years 1929 and later its docstring
      says it equals ``ss.benefits.aime`` exactly; earnings from the year
      of attaining 60 enter unindexed) and ``ss.benefits.pia`` at the year
      of attaining 62.  No recomputation for later earnings.
    * ``"disability"``: ``onset_year`` is required (``window_year``
      defaults to it).  ``di_pia_rule`` ``statutory_computation_years``
      (frozen, referee R5) calls ``ss.statutory_aime.aime(...,
      disability_year=onset)`` (415(b)(2)(A)(ii): elapsed years less
      one-fifth, at most 5, at least 2) and ``ss.benefits.pia`` at the
      onset year's bend points; ``approximate_pia`` (MS6) calls Track A's
      ``cola_track_a.benefits.approximate_pia`` (the oracle's 35-year AIME
      indexed to the second year before onset).  Either reads the history
      through onset less one.
    * ``"death"``: a worker who died before any own entitlement;
      ``death_year`` is required (``window_year`` defaults to it).  The
      statutory death computation, ``ss.statutory_aime.aime(...,
      death_year=death)`` (415(b)(2)(A)(i): elapsed years less 5), over the
      history through the death year less one, and ``ss.benefits.pia`` at
      the earlier of the death year and the year of attaining 62.
    """

    policy = policy or TrackMPolicy()
    birth = _int_year(birth_year, "birth_year")
    if basis == BASIS_OLD_AGE:
        if window_year is None:
            raise ValueError(
                "an old-age PIA needs window_year, the first year of "
                "entitlement (section 4a)"
            )
        years = record_years(
            basis=basis, birth_year=birth, window_year=window_year
        )
        kept = _through(history, years.last_year)
        aime = statutory_aime.aime(kept, birth, params)
        return PiaRecord(
            benefits.pia(aime, years.threshold_year, params),
            float(aime),
            basis,
            "ss.statutory_aime.aime + ss.benefits.pia",
            years.threshold_year,
            years.last_year,
        )
    if basis == BASIS_DISABILITY:
        if onset_year is None:
            raise ValueError("a disability basis needs onset_year")
        onset = _int_year(onset_year, "onset_year")
        years = record_years(
            basis=basis,
            birth_year=birth,
            window_year=onset if window_year is None else window_year,
            onset_year=onset,
        )
        kept = _through(history, years.last_year)
        if policy.di_pia_rule == DI_PIA_APPROXIMATE:
            from populace_dynamics.cola_track_a.benefits import (
                approximate_pia,
            )

            return PiaRecord(
                approximate_pia(
                    kept,
                    birth_year=birth,
                    computation_end_year=years.last_year,
                    eligibility_year=years.threshold_year,
                    params=params,
                ),
                None,
                basis,
                "cola_track_a.benefits.approximate_pia",
                years.threshold_year,
                years.last_year,
            )
        aime = statutory_aime.aime(kept, birth, params, disability_year=onset)
        return PiaRecord(
            benefits.pia(aime, years.threshold_year, params),
            float(aime),
            basis,
            "ss.statutory_aime.aime(disability_year) + ss.benefits.pia",
            years.threshold_year,
            years.last_year,
        )
    if basis == BASIS_DEATH:
        if death_year is None:
            raise ValueError("a death basis needs death_year")
        death = _int_year(death_year, "death_year")
        years = record_years(
            basis=basis,
            birth_year=birth,
            window_year=death if window_year is None else window_year,
            death_year=death,
        )
        kept = _through(history, years.last_year)
        aime = statutory_aime.aime(kept, birth, params, death_year=death)
        return PiaRecord(
            benefits.pia(aime, years.threshold_year, params),
            float(aime),
            basis,
            "ss.statutory_aime.aime(death_year) + ss.benefits.pia",
            years.threshold_year,
            years.last_year,
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
    benefit-to-PIA factor of the claim age (402(q) or 402(w),
    :func:`claim_factor`; 1 for a disability-origin record) and
    ``cola_factor`` the product of the COLAs from the December of the
    section 4a threshold year through December 2021 (:func:`cola_factor`).
    No rounding.  Section 6 of the M1 specification defines which records
    use it (MS5) and where *B* comes from.
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


def claim_factor(
    birth_year: int, entitlement_year: int, params: SSAParameters
) -> float:
    """A worker's benefit-to-PIA factor at a whole-year claim age.

    Section 4b rule 5: the claim age is ``entitlement_year - birth_year``
    in whole years, against the cohort's full retirement age
    (``params.fra_months``).  Before it, one less the oracle's 402(q)
    reduction (``ss.benefits.early_reduction``); after it, one plus the
    oracle's 402(w) credit (``ss.benefits.delayed_credit``, which stops at
    70).  A disability-origin record's factor is 1 and is not computed
    here.
    """

    birth = _int_year(birth_year, "birth_year")
    entitlement = _int_year(entitlement_year, "entitlement_year")
    months = _MONTHS * (entitlement - birth) - params.fra_months(birth)
    if months < 0:
        return 1.0 - benefits.early_reduction(-months, params)
    return 1.0 + benefits.delayed_credit(months, birth, params)


def cola_factor(
    first_year: int,
    rates: Mapping[int, float],
    *,
    last_determination_year: int = LAST_COLA_DETERMINATION_YEAR,
) -> float:
    """The product of the COLAs determined ``first_year`` through 2021.

    MS5's COLA factor (section 6): 42 USC 415(i)(2)(A)(iii) raises the PIA
    of an individual who becomes eligible, or dies before becoming
    eligible, in a year with an increase by that increase and every later
    one; benefits paid for 2022 reflect those determined through 2021
    (:data:`LAST_COLA_DETERMINATION_YEAR`).  ``rates`` maps a determination
    year to a fraction (``estimates.parameters.load_cola_history``).  A
    first year after 2021 gives 1.
    """

    first = _int_year(first_year, "first_year")
    factor = 1.0
    for year in range(first, last_determination_year + 1):
        if year not in rates:
            raise ValueError(f"no COLA determined in {year}")
        factor *= 1.0 + float(rates[year])
    return factor


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
    deceased's record when it exceeds the own amount.  ``own_amount`` is
    :func:`survivor_own_amount` (the own benefit after 402(q); section 4b
    rule 5).
    """

    paid = benefits.widow_benefit(
        own_amount,
        deceased_option_pia,
        survivor_months_early,
        deceased_claim_factor,
        params,
    )
    return paid > own_amount


def survivor_own_amount(
    own_option_pia: float | None,
    own_claim_factor: float | None,
    *,
    receives_own_benefit: bool,
) -> float:
    """A survivor's own amount for the widow(er)'s test (section 4b rule 5).

    The own old-age or disability benefit after the 402(q) reduction under
    the option: the own option PIA times the own claim factor, or 0 when
    the survivor receives no own benefit in 2022 (42 USC 402(k)(3)(A)
    reduces the other benefit by the own benefit "after reduction under
    such subsection (q)").
    """

    if not receives_own_benefit:
        return 0.0
    if own_option_pia is None or own_claim_factor is None:
        raise ValueError(
            "a survivor who receives an own benefit needs the own option "
            "PIA and claim factor"
        )
    if own_claim_factor <= 0 or own_option_pia < 0:
        raise ValueError("own PIA and claim factor must be positive")
    return float(own_option_pia) * float(own_claim_factor)


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
