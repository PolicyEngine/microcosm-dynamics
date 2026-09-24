"""Opt-in scenario COLA benefit paths for the transitional oracle (plan A6).

Python oracle; not Axiom.  This module generalizes the first-estimates
ledger's annual benefit path (``ledgers._monthly_benefit_path``) so that a
scenario can run past the sealed 2015-2022 report window, to 2030, under a
baseline and a reformed cost-of-living-adjustment (COLA) series.  It is an
opt-in successor in the ``engine.claiming`` pattern: the sealed ledger
module is not edited, nothing in the historical first-estimates call graph
imports this module, it sits outside ``estimates/`` so the registered
estimator surface (``coordinator._ESTIMATOR_SURFACE_SOURCES``) is
unchanged, and with default arguments
:func:`monthly_benefit_path` reproduces the sealed function's output
exactly (the tests pin this bit for bit).

Scope (plan ``critical-path-cola-20260922.md`` section 4, item A6):

1. **Scenario COLA series.**  :func:`extend_cola_series` splices a supplied
   projected path onto the realized determination-year history: realized
   rates for every determination year before the first projected year,
   projected rates from then on.  :class:`COLAReform` subtracts a supplied
   annual reduction from each increase starting with a supplied first
   reduced increase (identified by its determination year; 42 USC
   415(i)(2)(A)(ii) makes each increase effective with December of that
   year, paid in January of the next).
2. **Exposure clock.**  :class:`ExposureClock` selects which increases a
   reform reduces for a given primary insurance amount (PIA): those from
   the statutory eligibility year (the year the worker attains 62, or the
   year the period of disability began; 42 USC 415(a)(3)(B)) or those from
   the entitlement year.  The baseline path always credits every increase
   from the eligibility year (415(i)(2)(A)(iii)); the switch changes only
   the reform's exposure.
3. **Auxiliary benefits on the worker's clock.**  Spouse and widow(er)
   paths rest on the *worker's* PIA path, so they inherit the worker's
   eligibility (or entitlement) clock.  The auxiliary arithmetic is the
   existing oracle's :func:`~populace_dynamics.ss.benefits.spousal_benefit`
   and :func:`~populace_dynamics.ss.benefits.widow_benefit`, evaluated at
   each payment year's increased PIAs.
4. **Horizon.**  Every path takes an explicit ``horizon_year``.  The
   generalized core defaults to the sealed ledger's 2022; the scenario
   helpers default to :data:`SCENARIO_HORIZON_YEAR` (2030).
5. **Opening stock weighted by an observed amount.**
   :func:`opening_stock_scenario_paths` carries a beneficiary who is
   already receiving benefits when the projection starts from an observed
   monthly amount (the plan's observed 2010 Social Security amount)
   rather than from an AIME/PIA computation.  The amount is a weight: the
   reform ratio still comes only from the reformed increases on the clock
   of the worker whose PIA the benefit rests on, including any reformed
   increase already embedded in the observed amount.

Not in scope, and deliberately so:

* **No new statutory rule coverage** (``ss/__init__.py``: "Do not extend
  this module's rule coverage").  Disabled-worker benefit levels (the DI
  AIME/PIA with elapsed and dropout years) are not computed:
  :func:`di_benefit_level` raises ``NotImplementedError("awaiting ruling:
  DI benefit level")``.  Max ruled plan section 6 decision 2(b) on
  2026-09-23 (a disclosed oracle approximation, which the Track A
  assembly supplies in ``cola_track_a.benefits.approximate_pia``); this
  module still computes no DI level.  The
  benefit level of a worker who died before eligibility is likewise a
  raising hook (:func:`survivor_of_preeligibility_death_benefit_level`).
  Callers may supply any PIA to the path functions; this module does not
  say where a DI or survivor PIA comes from.  (The statutory computation
  years for those cases exist in :mod:`populace_dynamics.ss.statutory_aime`;
  neither hook uses them without a ruling.)
* No family maximum, earnings test, recomputation, payment-month timing,
  whole-dollar payment rounding, or pre-1983 June-effective COLA timing.
  The annual convention is the sealed ledger's: the amount for payment
  year ``t`` reflects the increases determined in years up to ``t - 1``,
  floored to the dime after each increase and again after the claim-age
  factor.

Choices that await Max's rulings are explicit parameters whose defaults are
the plan's *proposed, not adopted* primaries (plan section 4, "Proposed
specification entries for A1"; section 6 decisions 2(a) and 2(b)):

* :class:`ExposureClock` -- default ``ELIGIBILITY``; registered alternative
  ``ENTITLEMENT``.
* :attr:`COLAReform.first_reduced_determination_year` -- default 2009
  (effective December 2009, first paid January 2010); registered
  alternative 2010.
* :attr:`COLAReform.annual_reduction` -- default 0.01.
* :attr:`COLAReform.negative_rate_policy` -- default ``REFUSE`` (the plan
  expects the floor to be nonbinding and asks the freeze to verify it);
  alternative ``FLOOR_AT_ZERO``.
* :class:`BenefitPeriod` -- default ``CALENDAR_YEAR``; registered
  alternative ``DECEMBER``.
* ``observed_payment_year`` of :func:`opening_stock_scenario_paths` --
  default :data:`PLAN_PROPOSED_OPENING_STOCK_PAYMENT_YEAR` (2010, the PSID
  2011 wave's income year); registered alternative 2008 (the 2009 wave).
* DI benefit level -- :func:`di_benefit_level` raises until ruled on.  The
  plan names no specific approximation, so there is no proposed primary
  to default to; a caller may still pass any PIA to the path functions.

The age-62 AIME's benefit computation years are an explicit parameter of
:func:`eligibility_pia_for_clock` (``computation_years``).  The default is
the statute, :attr:`~populace_dynamics.ss.statutory_aime.ComputationYears.
STATUTORY` (42 USC 415(b)(2): elapsed years less 5, fewer than 35 for
workers born before 1929).  ``LEGACY_FIXED_35`` is the sealed ledger's
``benefits.aime`` (always 35), which Track A's Registration 13 used and
which the Track A assembly still passes explicitly.

One convention inside the ``ENTITLEMENT`` alternative is fixed here and
not named in the plan, so the specification freeze (plan item A1) must
confirm it: for a spouse or widow(er), "entitlement" is the insured
*worker's* entitlement year, not the auxiliary's own.  Under that reading
the alternative is undefined for the survivor of a worker who was never
entitled, and the functions raise rather than choose.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from numbers import Integral, Real
from typing import Any, NoReturn, Protocol

from populace_dynamics.estimates.ledgers import REPORT_YEARS, floor_to_dime
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import ComputationYears

__all__ = [
    "DI_BENEFIT_LEVEL_RULING",
    "LEDGER_HORIZON_YEAR",
    "PLAN_PROPOSED_ANNUAL_REDUCTION",
    "PLAN_PROPOSED_FIRST_REDUCED_DETERMINATION_YEAR",
    "PLAN_PROPOSED_OPENING_STOCK_PAYMENT_YEAR",
    "PLAN_PROPOSED_REFORM",
    "PREELIGIBILITY_DEATH_LEVEL_RULING",
    "SCENARIO_EVIDENCE_LABELS",
    "SCENARIO_HORIZON_YEAR",
    "BenefitPeriod",
    "COLARateSource",
    "COLAReform",
    "EligibilityBasis",
    "ExposureClock",
    "NegativeRatePolicy",
    "OwnBenefit",
    "ScenarioCOLARates",
    "ScenarioPaths",
    "WorkerClock",
    "di_benefit_level",
    "eligibility_pia_for_clock",
    "extend_cola_series",
    "increased_pia_path",
    "minimum_reformed_rate",
    "monthly_benefit_path",
    "opening_stock_scenario_paths",
    "payment_year_for_reference",
    "reduced_increase_count",
    "scenario_rates",
    "spouse_excess_path",
    "spouse_scenario_paths",
    "survivor_of_preeligibility_death_benefit_level",
    "widow_benefit_path",
    "widow_scenario_paths",
    "worker_benefit_path",
    "worker_scenario_paths",
]

#: The sealed first-estimates ledger's last payment year (2022).  The
#: generalized core path defaults to it so default calls reproduce the
#: sealed ``ledgers._monthly_benefit_path`` exactly.
LEDGER_HORIZON_YEAR = REPORT_YEARS[-1]
#: DynaSim scorecard exercise 1 reads 2030 payments.
SCENARIO_HORIZON_YEAR = 2030
#: Plan A1 proposal (not adopted): subtract one percentage point, as a
#: fraction, from each reformed annual increase.
PLAN_PROPOSED_ANNUAL_REDUCTION = 0.01
#: Plan A1 proposal (not adopted): the first reduced increase is the one
#: determined in 2009 (effective December 2009, first paid January 2010).
#: The registered alternative is 2010.
PLAN_PROPOSED_FIRST_REDUCED_DETERMINATION_YEAR = 2009
#: Plan section 3 recommendation (not adopted): the PSID 2011 wave, whose
#: income year the plan gives as 2010, so the opening stock's observed
#: amount is a 2010 payment-year amount.  The registered alternative (the
#: 2009 wave, income year 2008) observes 2008.
PLAN_PROPOSED_OPENING_STOCK_PAYMENT_YEAR = 2010
#: Message of the disabled-worker benefit-level hook (plan section 6, 2(b)).
DI_BENEFIT_LEVEL_RULING = "awaiting ruling: DI benefit level"
#: Message of the hook for a worker who died before becoming eligible.
PREELIGIBILITY_DEATH_LEVEL_RULING = (
    "awaiting ruling: survivor benefit level for a worker who died before "
    "eligibility"
)
#: Labels every scenario result carries (plan section 4, Track A).
SCENARIO_EVIDENCE_LABELS = (
    "Python oracle (not Axiom)",
    "fixed-path mechanical incidence",
)
#: 42 USC 415(i)(2)(A)(ii): from determination year 1983 on, an increase is
#: effective with December of its determination year.  The committed COLA
#: history records June-effective timing for 1975-1982, which the annual
#: convention here does not model, so a reform may not start before 1983.
_FIRST_DECEMBER_EFFECTIVE_DETERMINATION_YEAR = 1983


class ExposureClock(str, Enum):
    """Which increases a reform reduces for a given PIA.

    ``ELIGIBILITY`` (plan primary): every reformed increase from the
    statutory eligibility year of the worker whose PIA it is -- the year
    the worker attains 62, the year the period of disability began, or the
    year of death before eligibility (42 USC 415(a)(3)(B), 415(i)(2)(A)
    (iii)).  Auxiliary benefits follow the worker's clock.

    ``ENTITLEMENT`` (registered alternative): only reformed increases
    determined in or after the worker's entitlement year, i.e. increases
    received once the worker's benefits begin.  Increases between
    eligibility and entitlement stay at the baseline rate; the baseline
    path itself is statutory under either setting.
    """

    ELIGIBILITY = "eligibility"
    ENTITLEMENT = "entitlement"


class EligibilityBasis(str, Enum):
    """The event that starts a PIA's statutory COLA clock."""

    #: 42 USC 415(a)(3)(B)(i): months beginning with attaining age 62.
    AGE_62 = "age_62"
    #: 42 USC 415(a)(3)(B)(ii): months beginning with the month the period
    #: of disability began.  The prior-period exception is not modeled.
    DI_ONSET = "di_onset"
    #: 42 USC 415(i)(2)(A)(iii): an individual "who dies prior to becoming
    #: so eligible" receives increases from the year of death.
    DEATH_BEFORE_ELIGIBILITY = "death_before_eligibility"


class NegativeRatePolicy(str, Enum):
    """What to do when a reformed increase would fall below zero."""

    #: Plan primary: the floor must be nonbinding, so refuse the case.
    REFUSE = "refuse"
    #: Alternative: a reformed increase below zero becomes no increase.
    FLOOR_AT_ZERO = "floor_at_zero"


class BenefitPeriod(str, Enum):
    """Which monthly amount represents a reference year."""

    #: Plan primary: the annual model's payment-year amount, which
    #: reflects increases determined through the prior year.
    CALENDAR_YEAR = "calendar_year"
    #: Registered alternative: the December amount of the reference year,
    #: which also includes the increase effective that December.
    DECEMBER = "december"


class COLARateSource(Protocol):
    """Anything that returns a COLA fraction for a determination year."""

    def rate_for_determination_year(
        self, determination_year: int
    ) -> float: ...


def _year(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{label} must be an integer year.")
    return int(value)


def _fraction(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _unrounded(value: float) -> float:
    """Validate like ``floor_to_dime`` but keep every digit."""

    amount = _fraction(value, "amount")
    if amount < 0:
        raise ValueError("A benefit amount cannot be negative.")
    return amount


def _rounder(round_to_dime: bool) -> Callable[[float], float]:
    if not isinstance(round_to_dime, bool):
        raise TypeError("round_to_dime must be a boolean.")
    return floor_to_dime if round_to_dime else _unrounded


# ---------------------------------------------------------------------------
# (1) Scenario COLA series
# ---------------------------------------------------------------------------
def _canonical_sha256(rates: Mapping[int, float]) -> str:
    encoded = (
        json.dumps(
            {str(year): rate for year, rate in sorted(rates.items())},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def extend_cola_series(
    realized: COLASeries,
    projected_rates: Mapping[int, float],
    *,
    projection_label: str,
) -> COLASeries:
    """Splice a projected path onto the realized determination-year history.

    ``projected_rates`` maps consecutive determination years to COLA
    fractions (0.028 means 2.8 percent).  Realized rates are kept for every
    determination year before the first projected year; realized rates for
    later years, if any, are superseded by the projection and listed in the
    provenance.  The result must cover consecutive determination years.
    Projected rates must lie in [0, 1), the range the committed history
    loader enforces; 415(i) provides no negative baseline increase.

    ``projection_label`` names the path's source (for example a Trustees
    Report table).  This function does not know or check any Trustees
    values; the caller supplies them.
    """

    if not isinstance(realized, COLASeries):
        raise TypeError("realized must be a COLASeries.")
    if not isinstance(projection_label, str) or not projection_label:
        raise ValueError("projection_label must be a nonempty string.")
    if not isinstance(projected_rates, Mapping) or not projected_rates:
        raise ValueError("projected_rates must be a nonempty mapping.")
    projected: dict[int, float] = {}
    for raw_year, raw_rate in projected_rates.items():
        year = _year(raw_year, "projected determination year")
        rate = _fraction(raw_rate, f"projected COLA for {year}")
        if not 0.0 <= rate < 1.0:
            raise ValueError(
                f"projected COLA for {year} is {rate!r}; expected a "
                "fraction in [0, 1)."
            )
        projected[year] = rate
    projected = dict(sorted(projected.items()))
    first_projected = next(iter(projected))
    last_projected = next(reversed(projected))
    if tuple(projected) != tuple(range(first_projected, last_projected + 1)):
        raise ValueError("projected determination years must be consecutive.")

    kept = {
        year: rate
        for year, rate in realized.by_determination_year.items()
        if year < first_projected
    }
    superseded = sorted(
        year
        for year in realized.by_determination_year
        if year >= first_projected
    )
    combined = dict(sorted({**kept, **projected}.items()))
    years = tuple(combined)
    if years != tuple(range(years[0], years[-1] + 1)):
        raise ValueError(
            "realized history and projected path leave a gap in "
            f"determination years; the projection starts in "
            f"{first_projected}."
        )
    provenance = {
        "schema_version": "scenario_cola_series.v1",
        "realized": dict(realized.provenance),
        "realized_through_determination_year": (
            first_projected - 1 if kept else None
        ),
        "superseded_realized_determination_years": superseded,
        "projection_label": projection_label,
        "projected_first_determination_year": first_projected,
        "projected_last_determination_year": last_projected,
        "projected_rates_sha256": _canonical_sha256(projected),
        "projected_rates_hash_basis": (
            "sha256 of canonical JSON {determination_year: fraction} "
            "(sorted keys, compact separators, trailing newline)"
        ),
        "runtime_unit": "fraction",
        "year_basis": "determination_year",
    }
    return COLASeries(by_determination_year=combined, provenance=provenance)


@dataclass(frozen=True)
class COLAReform:
    """Subtract a fixed amount from each increase from a first increase on.

    Defaults are the plan's proposed, not adopted, primaries.  The first
    reduced increase is named by its determination year: under 42 USC
    415(i)(2)(A)(ii) it is effective with December of that year and first
    paid in January of the next.
    """

    annual_reduction: float = PLAN_PROPOSED_ANNUAL_REDUCTION
    first_reduced_determination_year: int = (
        PLAN_PROPOSED_FIRST_REDUCED_DETERMINATION_YEAR
    )
    negative_rate_policy: NegativeRatePolicy = NegativeRatePolicy.REFUSE

    def __post_init__(self) -> None:
        reduction = _fraction(self.annual_reduction, "annual_reduction")
        if not 0.0 <= reduction < 1.0:
            raise ValueError("annual_reduction must be a fraction in [0, 1).")
        first = _year(
            self.first_reduced_determination_year,
            "first_reduced_determination_year",
        )
        if first < _FIRST_DECEMBER_EFFECTIVE_DETERMINATION_YEAR:
            raise ValueError(
                "A reform may not start before determination year 1983; "
                "earlier increases were effective in June, which the annual "
                "convention does not model."
            )
        policy = NegativeRatePolicy(self.negative_rate_policy)
        object.__setattr__(self, "annual_reduction", reduction)
        object.__setattr__(self, "first_reduced_determination_year", first)
        object.__setattr__(self, "negative_rate_policy", policy)

    @classmethod
    def from_effective_month(
        cls,
        effective_month: date,
        *,
        annual_reduction: float = PLAN_PROPOSED_ANNUAL_REDUCTION,
        negative_rate_policy: NegativeRatePolicy = NegativeRatePolicy.REFUSE,
    ) -> COLAReform:
        """Build a reform from the first reduced increase's effective month.

        The month must be a December (415(i)(2)(A)(ii)).
        """

        if not isinstance(effective_month, date):
            raise TypeError("effective_month must be a datetime.date.")
        if effective_month.month != 12:
            raise ValueError(
                "A post-1982 COLA is effective with December; received "
                f"{effective_month.isoformat()}."
            )
        return cls(
            annual_reduction=annual_reduction,
            first_reduced_determination_year=effective_month.year,
            negative_rate_policy=negative_rate_policy,
        )

    @property
    def first_reduced_effective_month(self) -> date:
        """December of the first reduced increase's determination year."""

        return date(self.first_reduced_determination_year, 12, 1)

    @property
    def first_reduced_payment_month(self) -> date:
        """January after the first reduced increase takes effect."""

        return date(self.first_reduced_determination_year + 1, 1, 1)

    def reduced_rate(
        self, baseline_rate: float, determination_year: int
    ) -> float:
        """Return the reformed fraction for one reduced increase."""

        rate = (
            _fraction(baseline_rate, "baseline COLA") - self.annual_reduction
        )
        if rate >= 0.0:
            return rate
        if self.negative_rate_policy is NegativeRatePolicy.FLOOR_AT_ZERO:
            return 0.0
        raise ValueError(
            f"The reformed COLA for determination year {determination_year} "
            f"would be {rate!r}; the plan expects the zero floor to be "
            "nonbinding. Choose NegativeRatePolicy.FLOOR_AT_ZERO explicitly "
            "to floor it."
        )


#: The reform with every plan-proposed default (not adopted).
PLAN_PROPOSED_REFORM = COLAReform()


def minimum_reformed_rate(
    baseline: COLARateSource,
    reform: COLAReform,
    *,
    through_determination_year: int,
) -> float:
    """Smallest unfloored reformed fraction from the first reduced year.

    This is the freeze check the plan asks for: a nonnegative result means
    the zero floor never binds through ``through_determination_year``.
    """

    last = _year(through_determination_year, "through_determination_year")
    first = reform.first_reduced_determination_year
    if last < first:
        raise ValueError(
            "through_determination_year precedes the first reduced increase."
        )
    return min(
        _fraction(baseline.rate_for_determination_year(year), "baseline COLA")
        - reform.annual_reduction
        for year in range(first, last + 1)
    )


# ---------------------------------------------------------------------------
# (2) Clocks and the per-PIA scenario rate source
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkerClock:
    """The statutory COLA clock of the worker whose PIA a benefit rests on.

    ``eligibility_year`` starts the baseline clock: every increase
    determined in or after it raises the PIA.  ``entitlement_year`` is the
    first year the worker's own benefit is payable, or ``None`` if the
    worker is never entitled (for example, died before claiming).
    """

    basis: EligibilityBasis
    eligibility_year: int
    entitlement_year: int | None = None

    def __post_init__(self) -> None:
        basis = EligibilityBasis(self.basis)
        eligibility = _year(self.eligibility_year, "eligibility_year")
        entitlement = self.entitlement_year
        if entitlement is not None:
            entitlement = _year(entitlement, "entitlement_year")
            if entitlement < eligibility:
                raise ValueError(
                    "entitlement_year precedes the eligibility year."
                )
        if (
            basis is EligibilityBasis.DEATH_BEFORE_ELIGIBILITY
            and entitlement is not None
        ):
            raise ValueError(
                "A worker who died before eligibility has no own entitlement."
            )
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "eligibility_year", eligibility)
        object.__setattr__(self, "entitlement_year", entitlement)

    @classmethod
    def at_age_62(
        cls, birth_year: int, *, entitlement_year: int | None = None
    ) -> WorkerClock:
        """Old-age clock: the year the worker attains 62."""

        return cls(
            basis=EligibilityBasis.AGE_62,
            eligibility_year=_year(birth_year, "birth_year") + 62,
            entitlement_year=entitlement_year,
        )

    @classmethod
    def at_di_onset(
        cls, onset_year: int, *, entitlement_year: int | None = None
    ) -> WorkerClock:
        """Disability clock: the year the period of disability began."""

        return cls(
            basis=EligibilityBasis.DI_ONSET,
            eligibility_year=onset_year,
            entitlement_year=entitlement_year,
        )

    @classmethod
    def at_death_before_eligibility(cls, death_year: int) -> WorkerClock:
        """Survivor-only clock for a worker who died before eligibility."""

        return cls(
            basis=EligibilityBasis.DEATH_BEFORE_ELIGIBILITY,
            eligibility_year=death_year,
        )

    def exposure_start_year(self, exposure_clock: ExposureClock) -> int:
        """First determination year whose increase the reform may reduce."""

        clock = ExposureClock(exposure_clock)
        if clock is ExposureClock.ELIGIBILITY:
            return self.eligibility_year
        if self.entitlement_year is None:
            raise ValueError(
                "The entitlement exposure clock is undefined for a worker "
                "who was never entitled; the plan does not define it."
            )
        return self.entitlement_year


@dataclass(frozen=True)
class ScenarioCOLARates:
    """COLA fractions applied to one PIA in one scenario.

    With ``reform=None`` this is the baseline series unchanged.  Otherwise
    an increase is reduced when its determination year is at or after both
    the reform's first reduced year and ``exposure_start_year``.
    """

    baseline: COLARateSource
    reform: COLAReform | None
    exposure_start_year: int

    def __post_init__(self) -> None:
        if self.reform is not None and not isinstance(self.reform, COLAReform):
            raise TypeError("reform must be a COLAReform or None.")
        object.__setattr__(
            self,
            "exposure_start_year",
            _year(self.exposure_start_year, "exposure_start_year"),
        )

    def is_reduced(self, determination_year: int) -> bool:
        """Whether this scenario reduces the given year's increase."""

        return (
            self.reform is not None
            and determination_year
            >= self.reform.first_reduced_determination_year
            and determination_year >= self.exposure_start_year
        )

    def rate_for_determination_year(self, determination_year: int) -> float:
        """Return the scenario fraction for one determination year."""

        try:
            baseline_rate = self.baseline.rate_for_determination_year(
                determination_year
            )
        except KeyError as error:
            raise ValueError(
                "The baseline COLA series lacks determination year "
                f"{determination_year}; extend it with a projected path "
                "(extend_cola_series) or lower the horizon."
            ) from error
        if not self.is_reduced(determination_year):
            return baseline_rate
        assert self.reform is not None
        return self.reform.reduced_rate(baseline_rate, determination_year)


def scenario_rates(
    baseline: COLARateSource,
    reform: COLAReform | None,
    *,
    clock: WorkerClock,
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY,
) -> ScenarioCOLARates:
    """Rates for the PIA of the worker on ``clock`` in one scenario."""

    if reform is None:
        return ScenarioCOLARates(
            baseline=baseline,
            reform=None,
            exposure_start_year=clock.eligibility_year,
        )
    return ScenarioCOLARates(
        baseline=baseline,
        reform=reform,
        exposure_start_year=clock.exposure_start_year(exposure_clock),
    )


def reduced_increase_count(
    clock: WorkerClock,
    rates: ScenarioCOLARates,
    payment_year: int,
) -> int:
    """Reduced increases in a PIA's amount for ``payment_year``.

    The amount for payment year ``t`` rests on the increases determined in
    ``clock.eligibility_year`` through ``t - 1``.
    """

    year = _year(payment_year, "payment_year")
    return sum(
        rates.is_reduced(determination_year)
        for determination_year in range(clock.eligibility_year, year)
    )


# ---------------------------------------------------------------------------
# Generalized core path (default arguments reproduce the sealed ledger)
# ---------------------------------------------------------------------------
def increased_pia_path(
    *,
    eligibility_pia: float,
    eligibility_year: int,
    cola: COLARateSource,
    horizon_year: int = LEDGER_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> dict[int, float]:
    """The PIA by payment year, increased stepwise from eligibility.

    Floors the eligibility PIA to the dime, then applies each
    determination-year increase and floors again (415(i)(2)(A)(ii)).
    ``round_to_dime=False`` keeps every digit; it exists for arithmetic
    diagnostics, not for benefit amounts.
    """

    rounder = _rounder(round_to_dime)
    eligibility = _year(eligibility_year, "eligibility_year")
    horizon = _year(horizon_year, "horizon_year")
    increased_pia = rounder(eligibility_pia)
    result = {eligibility: increased_pia}
    for payment_year in range(eligibility + 1, horizon + 1):
        determination_year = payment_year - 1
        rate = cola.rate_for_determination_year(determination_year)
        increased_pia = rounder(increased_pia * (1.0 + rate))
        result[payment_year] = increased_pia
    return result


def monthly_benefit_path(
    *,
    eligibility_pia: float,
    claim_age_factor: float,
    eligibility_year: int,
    cola: COLARateSource,
    horizon_year: int = LEDGER_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> dict[int, float]:
    """Generalization of the sealed ``ledgers._monthly_benefit_path``.

    Increase the PIA stepwise, then apply the claim-age factor and floor the
    product to the dime for each payment year.  With the default horizon and
    rounding, and a ``COLASeries`` as ``cola``, the result equals the
    sealed function's for the same inputs, bit for bit.
    """

    rounder = _rounder(round_to_dime)
    pia_path = increased_pia_path(
        eligibility_pia=eligibility_pia,
        eligibility_year=eligibility_year,
        cola=cola,
        horizon_year=horizon_year,
        round_to_dime=round_to_dime,
    )
    return {
        payment_year: rounder(increased_pia * claim_age_factor)
        for payment_year, increased_pia in pia_path.items()
    }


# ---------------------------------------------------------------------------
# Benefit levels: existing oracle only; hooks where a ruling is pending
# ---------------------------------------------------------------------------
def di_benefit_level(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Disabled-worker PIA level: not implemented pending a ruling.

    Computing a DI AIME and PIA (elapsed and dropout computation years,
    onset-year bend points) would extend the oracle's statutory coverage.
    The plan asked Max (section 6, decision 2(b)) whether a disclosed
    approximation may be used instead, or DI levels excluded; he ruled
    for the disclosed approximation on 2026-09-23, which the Track A
    assembly supplies (``cola_track_a.benefits.approximate_pia``).  This
    function stays unimplemented: this module adds no statutory coverage.
    """

    raise NotImplementedError(DI_BENEFIT_LEVEL_RULING)


def survivor_of_preeligibility_death_benefit_level(
    *_args: Any, **_kwargs: Any
) -> NoReturn:
    """PIA level of a worker who died before eligibility: not implemented.

    Computing it (computation years ending with death) would extend the
    oracle's statutory coverage, so it waits on the same kind of ruling as
    :func:`di_benefit_level`.
    """

    raise NotImplementedError(PREELIGIBILITY_DEATH_LEVEL_RULING)


def eligibility_pia_for_clock(
    clock: WorkerClock,
    *,
    history: Mapping[int, float],
    birth_year: int,
    params: SSAParameters,
    computation_years: ComputationYears = ComputationYears.STATUTORY,
) -> float:
    """The PIA at eligibility for the worker on ``clock``.

    Only the old-age case is computed: the oracle AIME, then
    ``benefits.pia`` in the year the worker attains 62.  The AIME counts
    its benefit computation years by ``computation_years``
    (:func:`populace_dynamics.ss.statutory_aime.oracle_aime`):
    ``STATUTORY`` (the default) follows 42 USC 415(b)(2) and equals the
    sealed ledger's ``benefits.aime`` for workers born 1929 or later; it
    refuses workers attaining 62 before 1975 and history years before
    1951.  ``LEGACY_FIXED_35`` is ``benefits.aime`` exactly as the sealed
    ledger calls it, for every birth year.  ``history`` is used as
    supplied; the caller applies any cutoff law.  The other bases route to
    hooks that raise ``NotImplementedError``.
    """

    birth = _year(birth_year, "birth_year")
    if clock.basis is EligibilityBasis.DI_ONSET:
        di_benefit_level(clock=clock, history=history, birth_year=birth)
    if clock.basis is EligibilityBasis.DEATH_BEFORE_ELIGIBILITY:
        survivor_of_preeligibility_death_benefit_level(
            clock=clock, history=history, birth_year=birth
        )
    if clock.eligibility_year != birth + 62:
        raise ValueError(
            "An age-62 clock must start in the year the worker attains 62."
        )
    aime_value = statutory_aime.oracle_aime(
        history, birth, params, computation_years=computation_years
    )
    return benefits.pia(aime_value, clock.eligibility_year, params)


# ---------------------------------------------------------------------------
# (3) Worker, spouse and widow(er) paths
# ---------------------------------------------------------------------------
def _payable_years(entitlement_year: int, horizon_year: int) -> range:
    return range(
        _year(entitlement_year, "entitlement_year"),
        _year(horizon_year, "horizon_year") + 1,
    )


def _amount_at(path: Mapping[int, float], year: int, label: str) -> float:
    try:
        return path[year]
    except KeyError as error:
        raise ValueError(f"{label} has no amount for {year}.") from error


def worker_benefit_path(
    *,
    eligibility_pia: float,
    claim_age_factor: float,
    clock: WorkerClock,
    rates: ScenarioCOLARates,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> dict[int, float]:
    """A worker's own monthly benefit for payment years from entitlement.

    Survival and presence filtering is the caller's job.
    """

    if clock.entitlement_year is None:
        raise ValueError("A worker benefit needs an entitlement year.")
    path = monthly_benefit_path(
        eligibility_pia=eligibility_pia,
        claim_age_factor=claim_age_factor,
        eligibility_year=clock.eligibility_year,
        cola=rates,
        horizon_year=horizon_year,
        round_to_dime=round_to_dime,
    )
    return {
        year: path[year]
        for year in _payable_years(clock.entitlement_year, horizon_year)
    }


def spouse_excess_path(
    *,
    worker_pia_by_year: Mapping[int, float],
    own_pia_by_year: Mapping[int, float] | None,
    months_early: int,
    entitlement_year: int,
    params: SSAParameters,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> dict[int, float]:
    """Excess spouse's benefit by payment year from the spouse's entitlement.

    Each year applies the existing oracle's ``benefits.spousal_benefit`` to
    that year's increased worker PIA (on the worker's clock) and the
    spouse's own increased PIA (on the spouse's own clock; ``None`` means
    no own PIA), then floors to the dime as the worker path does.  The
    spouse's own retirement benefit, if any, is a separate worker path.
    """

    rounder = _rounder(round_to_dime)
    result = {}
    for year in _payable_years(entitlement_year, horizon_year):
        worker_pia = _amount_at(worker_pia_by_year, year, "worker PIA path")
        own_pia = (
            0.0
            if own_pia_by_year is None
            else _amount_at(own_pia_by_year, year, "own PIA path")
        )
        result[year] = rounder(
            benefits.spousal_benefit(own_pia, worker_pia, months_early, params)
        )
    return result


def widow_benefit_path(
    *,
    deceased_pia_by_year: Mapping[int, float],
    own_amount_by_year: Mapping[int, float] | None,
    survivor_months_early: int,
    deceased_claim_age_factor: float,
    entitlement_year: int,
    params: SSAParameters,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> dict[int, float]:
    """Widow(er)'s payable amount by payment year from entitlement.

    Each year applies the existing oracle's ``benefits.widow_benefit`` (the
    larger of the survivor's own amount or the widow(er)'s benefit, with the
    RIB-LIM) to that year's increased deceased-worker PIA and the survivor's
    own amount, then floors to the dime.  ``deceased_claim_age_factor`` is
    1.0 for a worker who never claimed.  Years absent from
    ``own_amount_by_year`` count as no own benefit.
    """

    rounder = _rounder(round_to_dime)
    result = {}
    for year in _payable_years(entitlement_year, horizon_year):
        deceased_pia = _amount_at(
            deceased_pia_by_year, year, "deceased worker PIA path"
        )
        own_amount = (
            0.0
            if own_amount_by_year is None
            else own_amount_by_year.get(year, 0.0)
        )
        result[year] = rounder(
            benefits.widow_benefit(
                own_amount,
                deceased_pia,
                survivor_months_early,
                deceased_claim_age_factor,
                params,
            )
        )
    return result


@dataclass(frozen=True)
class OwnBenefit:
    """A beneficiary's own worker record, used for dual entitlement."""

    eligibility_pia: float
    claim_age_factor: float
    clock: WorkerClock


@dataclass(frozen=True)
class ScenarioPaths:
    """Baseline and reform monthly amounts for one benefit.

    ``reduced_increases_by_payment_year`` counts reformed increases in the
    worker PIA the benefit rests on (the worker's own PIA for a worker, the
    insured worker's PIA for a spouse or widow(er)).  When a widow(er)'s own
    benefit is the larger amount, or a spouse's own PIA offsets the excess,
    the payable amount also depends on the beneficiary's own PIA and clock;
    the count still describes the insured worker's PIA.  Tabulations should
    compare the two amount paths directly rather than infer ratios from
    the count.
    """

    beneficiary_type: str
    exposure_clock: ExposureClock
    worker_clock: WorkerClock
    reform: COLAReform
    exposure_start_year: int
    baseline_monthly_by_payment_year: Mapping[int, float]
    reform_monthly_by_payment_year: Mapping[int, float]
    reduced_increases_by_payment_year: Mapping[int, int]
    evidence_labels: tuple[str, ...] = SCENARIO_EVIDENCE_LABELS


def _scenario_pair(
    baseline: COLARateSource,
    reform: COLAReform,
    clock: WorkerClock,
    exposure_clock: ExposureClock,
) -> tuple[ScenarioCOLARates, ScenarioCOLARates]:
    if not isinstance(reform, COLAReform):
        raise TypeError("reform must be a COLAReform.")
    return (
        scenario_rates(baseline, None, clock=clock),
        scenario_rates(
            baseline, reform, clock=clock, exposure_clock=exposure_clock
        ),
    )


def _reduced_counts(
    clock: WorkerClock,
    rates: ScenarioCOLARates,
    years: Mapping[int, float],
) -> dict[int, int]:
    return {year: reduced_increase_count(clock, rates, year) for year in years}


def worker_scenario_paths(
    *,
    eligibility_pia: float,
    claim_age_factor: float,
    clock: WorkerClock,
    baseline: COLARateSource,
    reform: COLAReform = PLAN_PROPOSED_REFORM,
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> ScenarioPaths:
    """A worker's own benefit under the baseline and the reform."""

    exposure_clock = ExposureClock(exposure_clock)
    base_rates, reform_rates = _scenario_pair(
        baseline, reform, clock, exposure_clock
    )
    kwargs = {
        "eligibility_pia": eligibility_pia,
        "claim_age_factor": claim_age_factor,
        "clock": clock,
        "horizon_year": horizon_year,
        "round_to_dime": round_to_dime,
    }
    base_path = worker_benefit_path(rates=base_rates, **kwargs)
    reform_path = worker_benefit_path(rates=reform_rates, **kwargs)
    return ScenarioPaths(
        beneficiary_type="worker",
        exposure_clock=exposure_clock,
        worker_clock=clock,
        reform=reform,
        exposure_start_year=reform_rates.exposure_start_year,
        baseline_monthly_by_payment_year=base_path,
        reform_monthly_by_payment_year=reform_path,
        reduced_increases_by_payment_year=_reduced_counts(
            clock, reform_rates, reform_path
        ),
    )


def _pia_path_for(
    pia: float,
    clock: WorkerClock,
    rates: ScenarioCOLARates,
    horizon_year: int,
    round_to_dime: bool,
) -> dict[int, float]:
    return increased_pia_path(
        eligibility_pia=pia,
        eligibility_year=clock.eligibility_year,
        cola=rates,
        horizon_year=horizon_year,
        round_to_dime=round_to_dime,
    )


def spouse_scenario_paths(
    *,
    worker_eligibility_pia: float,
    worker_clock: WorkerClock,
    own: OwnBenefit | None,
    months_early: int,
    entitlement_year: int,
    params: SSAParameters,
    baseline: COLARateSource,
    reform: COLAReform = PLAN_PROPOSED_REFORM,
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> ScenarioPaths:
    """Excess spouse's benefit under the baseline and the reform.

    The worker's PIA follows ``worker_clock``; a spouse's own PIA, when
    present, follows the spouse's own clock under the same exposure
    setting.  The spouse's own retirement benefit is not included; compute
    it with :func:`worker_scenario_paths` on ``own``.
    """

    exposure_clock = ExposureClock(exposure_clock)
    if worker_clock.entitlement_year is None:
        raise ValueError(
            "A spouse's benefit rests on an entitled worker; the worker "
            "clock has no entitlement year."
        )
    # The spouse's benefit rests on an entitled worker (checked above), so
    # it cannot be payable before that entitlement.  Divorced spouses, who
    # can be entitled independently, are on the plan's omitted list.
    if _year(entitlement_year, "entitlement_year") < (
        worker_clock.entitlement_year
    ):
        raise ValueError(
            "A spouse's entitlement year precedes the worker's entitlement "
            "year."
        )
    worker_rates = _scenario_pair(
        baseline, reform, worker_clock, exposure_clock
    )
    own_rates = (
        None
        if own is None
        else _scenario_pair(baseline, reform, own.clock, exposure_clock)
    )
    paths = []
    for index in (0, 1):
        worker_pia = _pia_path_for(
            worker_eligibility_pia,
            worker_clock,
            worker_rates[index],
            horizon_year,
            round_to_dime,
        )
        own_pia = (
            None
            if own is None
            else _pia_path_for(
                own.eligibility_pia,
                own.clock,
                own_rates[index],
                horizon_year,
                round_to_dime,
            )
        )
        paths.append(
            spouse_excess_path(
                worker_pia_by_year=worker_pia,
                own_pia_by_year=own_pia,
                months_early=months_early,
                entitlement_year=entitlement_year,
                params=params,
                horizon_year=horizon_year,
                round_to_dime=round_to_dime,
            )
        )
    return ScenarioPaths(
        beneficiary_type="spouse",
        exposure_clock=exposure_clock,
        worker_clock=worker_clock,
        reform=reform,
        exposure_start_year=worker_rates[1].exposure_start_year,
        baseline_monthly_by_payment_year=paths[0],
        reform_monthly_by_payment_year=paths[1],
        reduced_increases_by_payment_year=_reduced_counts(
            worker_clock, worker_rates[1], paths[1]
        ),
    )


def widow_scenario_paths(
    *,
    deceased_eligibility_pia: float,
    deceased_clock: WorkerClock,
    deceased_claim_age_factor: float,
    own: OwnBenefit | None,
    survivor_months_early: int,
    entitlement_year: int,
    params: SSAParameters,
    baseline: COLARateSource,
    reform: COLAReform = PLAN_PROPOSED_REFORM,
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> ScenarioPaths:
    """Widow(er)'s payable amount under the baseline and the reform.

    The deceased worker's PIA follows ``deceased_clock``.  The survivor's
    own amount, when present, is the survivor's own worker benefit path
    (zero before the survivor's own entitlement year).
    """

    exposure_clock = ExposureClock(exposure_clock)
    # A worker entitled in some year was alive then, so a survivor's
    # entitlement, which follows the death, cannot precede it.
    if (
        deceased_clock.entitlement_year is not None
        and _year(entitlement_year, "entitlement_year")
        < deceased_clock.entitlement_year
    ):
        raise ValueError(
            "A widow(er)'s entitlement year precedes the deceased worker's "
            "entitlement year."
        )
    deceased_rates = _scenario_pair(
        baseline, reform, deceased_clock, exposure_clock
    )
    own_rates = (
        None
        if own is None
        else _scenario_pair(baseline, reform, own.clock, exposure_clock)
    )
    paths = []
    for index in (0, 1):
        deceased_pia = _pia_path_for(
            deceased_eligibility_pia,
            deceased_clock,
            deceased_rates[index],
            horizon_year,
            round_to_dime,
        )
        own_amount = (
            None
            if own is None
            else worker_benefit_path(
                eligibility_pia=own.eligibility_pia,
                claim_age_factor=own.claim_age_factor,
                clock=own.clock,
                rates=own_rates[index],
                horizon_year=horizon_year,
                round_to_dime=round_to_dime,
            )
        )
        paths.append(
            widow_benefit_path(
                deceased_pia_by_year=deceased_pia,
                own_amount_by_year=own_amount,
                survivor_months_early=survivor_months_early,
                deceased_claim_age_factor=deceased_claim_age_factor,
                entitlement_year=entitlement_year,
                params=params,
                horizon_year=horizon_year,
                round_to_dime=round_to_dime,
            )
        )
    return ScenarioPaths(
        beneficiary_type="widow(er)",
        exposure_clock=exposure_clock,
        worker_clock=deceased_clock,
        reform=reform,
        exposure_start_year=deceased_rates[1].exposure_start_year,
        baseline_monthly_by_payment_year=paths[0],
        reform_monthly_by_payment_year=paths[1],
        reduced_increases_by_payment_year=_reduced_counts(
            deceased_clock, deceased_rates[1], paths[1]
        ),
    )


# ---------------------------------------------------------------------------
# Opening stock weighted by an observed amount (scope item 5)
# ---------------------------------------------------------------------------
def opening_stock_scenario_paths(
    *,
    observed_monthly_amount: float,
    clock: WorkerClock,
    baseline: COLARateSource,
    observed_payment_year: int = PLAN_PROPOSED_OPENING_STOCK_PAYMENT_YEAR,
    reform: COLAReform = PLAN_PROPOSED_REFORM,
    exposure_clock: ExposureClock = ExposureClock.ELIGIBILITY,
    horizon_year: int = SCENARIO_HORIZON_YEAR,
    round_to_dime: bool = True,
) -> ScenarioPaths:
    """An already-receiving beneficiary's amounts from an observed amount.

    Plan item A6 asks for the opening stock to be "weighted by observed
    2010 SS amount".  For someone already receiving benefits when the
    projection starts, the reform ratio depends only on the reformed
    increases in the PIA the benefit rests on (plan section 1), so the
    level serves as a weight and is taken from an observation instead of
    from an AIME/PIA computation:

    * ``observed_monthly_amount`` is the baseline scenario's amount for
      ``observed_payment_year``.  Converting a survey amount (for example
      a PSID annual Social Security income amount) to a monthly amount is
      the caller's job.
    * ``clock`` is the COLA clock of the worker whose PIA the benefit
      rests on: the beneficiary's own for a worker, the insured worker's
      for a spouse or widow(er).  Deciding which applies is the caller's
      job (plan section 3 found no benefit-type item in the PSID 2011
      family file; plan item A3 owns the opening-status rule).  The clock
      must have started, and any entitlement it records must have begun,
      by ``observed_payment_year``.
    * The baseline path increases the observed amount by each baseline
      increase determined in ``observed_payment_year`` or later.
    * The reform path starts from the observed amount scaled by
      ``(1 + reformed rate) / (1 + baseline rate)`` for each reformed
      increase determined before ``observed_payment_year`` -- with the
      plan-proposed 2009 first reduced increase and a 2010 observation,
      the increase effective December 2009 -- and then increases by the
      reformed rates.  So the unrounded reform/baseline ratio for payment
      year ``t`` is the product over every reformed increase from the
      clock's start through ``t - 1``, the same as for a computed PIA.

    Disclosed approximations, not statutory computation: the observed
    amount is increased as if it were a PIA with claim-age factor 1,
    floored to the dime after each increase; it is treated as the
    baseline scenario's amount even where the baseline rate path (for
    example a Trustees projection) differs from the increases actually
    paid before the observation; and a dual-entitled beneficiary's whole
    amount is carried on one clock.
    """

    exposure_clock = ExposureClock(exposure_clock)
    observed_year = _year(observed_payment_year, "observed_payment_year")
    horizon = _year(horizon_year, "horizon_year")
    observed = _unrounded(observed_monthly_amount)
    if not isinstance(clock, WorkerClock):
        raise TypeError("clock must be a WorkerClock.")
    if clock.eligibility_year > observed_year:
        raise ValueError(
            "An opening-stock benefit observed in "
            f"{observed_year} cannot rest on a PIA whose clock starts in "
            f"{clock.eligibility_year}."
        )
    if (
        clock.entitlement_year is not None
        and clock.entitlement_year > observed_year
    ):
        raise ValueError(
            "An opening-stock benefit observed in "
            f"{observed_year} cannot rest on a worker first entitled in "
            f"{clock.entitlement_year}."
        )
    if horizon < observed_year:
        raise ValueError("horizon_year precedes observed_payment_year.")
    base_rates, reform_rates = _scenario_pair(
        baseline, reform, clock, exposure_clock
    )
    reform_start = observed
    for determination_year in range(clock.eligibility_year, observed_year):
        if reform_rates.is_reduced(determination_year):
            reform_start *= (
                1.0
                + reform_rates.rate_for_determination_year(determination_year)
            ) / (
                1.0
                + base_rates.rate_for_determination_year(determination_year)
            )
    base_path, reform_path = (
        increased_pia_path(
            eligibility_pia=start,
            eligibility_year=observed_year,
            cola=rates,
            horizon_year=horizon,
            round_to_dime=round_to_dime,
        )
        for start, rates in (
            (observed, base_rates),
            (reform_start, reform_rates),
        )
    )
    return ScenarioPaths(
        beneficiary_type="opening_stock",
        exposure_clock=exposure_clock,
        worker_clock=clock,
        reform=reform,
        exposure_start_year=reform_rates.exposure_start_year,
        baseline_monthly_by_payment_year=base_path,
        reform_monthly_by_payment_year=reform_path,
        reduced_increases_by_payment_year=_reduced_counts(
            clock, reform_rates, reform_path
        ),
    )


# ---------------------------------------------------------------------------
# (4) Horizon and benefit period
# ---------------------------------------------------------------------------
def payment_year_for_reference(
    reference_year: int,
    period: BenefitPeriod = BenefitPeriod.CALENDAR_YEAR,
) -> int:
    """The payment-year key that represents ``reference_year``.

    ``CALENDAR_YEAR`` reads that year's annual amount.  ``DECEMBER`` reads
    the next payment year's amount, which in this annual convention equals
    the December amount of ``reference_year`` (it adds the increase
    determined in ``reference_year``).  The returned year is also the
    horizon a path must reach.
    """

    year = _year(reference_year, "reference_year")
    if BenefitPeriod(period) is BenefitPeriod.DECEMBER:
        return year + 1
    return year
