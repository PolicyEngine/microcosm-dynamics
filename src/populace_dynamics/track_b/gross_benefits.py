"""Track B milestone G: the gross-benefit layer (Python statutory reference).

Verification class: statutory conformance (Track B design revision 3, §3.2
row G). Success admits gross monthly benefits for the supported family
configurations below, and nothing else: no population claim, no payment
timing, no earnings-test deductions (R2), no ARF or recomputation (R3).
Max's ruling d515 (2026-09-28) adopted §10 question 9's default: a Python
reference now, with Axiom differential checks as diagnostics once a pinned
rule exists. At this module's creation rulespec-us had no 42 U.S.C. 403
encoding, so no Axiom differential is run.

What this layer computes, for one insured worker's record and one month:

1. **Family maximum.** 42 U.S.C. 403(a)(1)-(2): 150/272/134/175 percent of
   the PIA across three bend points, the 1979 amounts $230/$332/$433 scaled
   by NAWI(eligibility year - 2) / NAWI(1977) and rounded to the nearest
   dollar with 50-cent ties upward (215(a)(1)(B)(iii)); the total is
   decreased to the next lower multiple of $0.10. The PIA used is the PIA
   for the year of first eligibility before COLAs, and the COLAs are then
   applied to the maximum (POMS RS 00615.736A.1; 215(i)(2)(A)(ii)(III),
   dime-floored after each increase). Disability families use 403(a)(6):
   the smaller of 85 percent of AIME (or 100 percent of the PIA, if larger)
   and 150 percent of the PIA, rounded down to a dime (SSA, Social Security
   Bulletin 75(3), 2015), for initial DIB entitlement after June 1980 (POMS
   RS 00615.740-.742).
2. **Original benefits.** 402(b)/(c)(2) spouse 1/2, 402(d)(2) child 1/2
   (3/4 of a deceased worker's PIA), 402(e)/(f)(2)(A) widow(er) 100 percent
   of the PIA as determined under (2)(B)-(C) (windexing, or the PIA deemed
   equal to the deceased's credit-increased benefit; RS 00615.301A.3),
   402(g)(2) mother/father 3/4; each rounded down to a dime.
3. **Family-maximum reduction.** 403(a)(4): every benefit other than the
   worker's own is decreased proportionately (POMS RS 00615.756: OB x
   available / total OB, not to exceed OB, dime-floored). In a life case the
   worker's PIA (never the DRC-increased benefit, RS 00615.695) is deducted
   from the maximum first. Divorced spouses and surviving divorced spouses
   are paid outside the maximum and ignored in everyone else's computation
   (403(a)(3)(C); RS 00615.680-.682).
4. **Dual-entitlement redistribution.** For payment months from October
   1999, other auxiliaries are reduced only by what a dually entitled
   beneficiary is actually paid before any age reduction; the maximum is
   redistributed to the others, each capped at their OB (POMS RS 00615.768,
   the Parisi rule). If every subject beneficiary is dually entitled, the
   rule is disregarded (RS 00615.768C). Where "payable before any age
   reduction" has more than one reading (the offsetting own benefit is
   itself reduced under 402(q) or increased under 402(w), or a widow(er)
   is RIB-LIM limited), the case is refused rather than guessed.
5. **Age reductions after the family maximum** (RS 00615.754A.1, .210,
   .301B.1.c): spouse 25/36 of 1 percent for 36 months and 5/12 of 1 percent
   beyond, dime-floored (RS 00615.201); widow(er) 28.5 percent spread over
   the reduction period, the reduction amount rounded *up* to a dime (RS
   00615.301); the RIB-LIM afterwards (402(e)(2)(D); RS 00615.320).
6. **Dual entitlement.** 402(k)(3)(A): the auxiliary benefit, after 402(q)
   and 403(a), is reduced (not below zero) by the person's own old-age or
   disability benefit after 402(q). For an aged spouse entitled to the own
   benefit in or before the spouse benefit's first month, 402(q)(3)(B)/(C)
   reduce only the excess of the spouse benefit over the own PIA (POMS RS
   00615.250, method C), with delayed credits handled per RS 00615.694. A
   spouse entitled first and to the RIB later keeps the spouse benefit as
   reduced under 402(q)(1) and is paid its excess over the RIB (RS
   00615.240, method B). A widow(er)'s benefit and own benefit are reduced
   independently (method B, 402(q)(3)(E); RS 00615.020A.3). A spouse with
   a child in care is never reduced for age (402(q)(5)(A)(ii)) and is paid
   the excess over the reduced RIB (RS 00615.020A.3 note).
7. **Monthly family payment.** Every benefit amount is kept as an exact
   dime multiple; 215(g) rounds each monthly benefit down to a whole dollar.
   Gross means before 203(b) earnings-test deductions and the 1840(a)(1)
   Medicare premium; 215(g) rounds after those, so the whole-dollar gross
   here is not a net check. Gross rates assume no beneficiary on the record
   has a deduction or suspension: 203(a)(4) makes the maximum reduction
   after deductions, so a deduction can raise the others' rates (POMS RS
   00615.766). That ordering belongs to the RET ledger (R2).

Which record and PIA to supply. The family maximum is computed once, from
the PIA for the year of first eligibility before COLAs (RS 00615.736A.1),
and COLAs then raise it with the PIA. The eligibility year is the year the
worker initially became eligible for old-age or disability benefits, or
died before becoming so eligible (403(a)(2)(A)-(B)), except that a worker entitled to DIB in any of the 12 months before
eligibility or death keeps the DIB eligibility year (403(a)(2)(D)). The
403(a)(6) disability maximum applies only while DIB entitlement continues;
when the DIB converts to a RIB or the worker dies, build a retirement or
survivor record, whose maximum is the ordinary AIME maximum (RS
00615.742.2).

All arithmetic is exact (``fractions.Fraction``). SSA requires fractions,
not decimal equivalents, because decimals often yield an answer 10 cents
lower (POMS RS 00615.005B). Statutory rates are cross-checked at use
against the repository's parameter bundle (``ss.params.SSAParameters``,
loaded from policyengine-us), and the exact statutory fraction is then
used; NAWI and delayed-credit rates come from that bundle.

Unsupported configurations raise :class:`FamilyConfigurationUnsupported`
(code ``FAMILY_CONFIG_UNSUPPORTED``, design §7) and never fall back to a
single-worker computation. :func:`evaluate_family`,
:func:`count_family_outcomes` and the weighted aggregates keep such rows in
every denominator and block totals that would need them.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from numbers import Rational
from types import MappingProxyType

from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "BASE_NAWI_YEAR",
    "DI_MAXIMUM_FIRST_ENTITLEMENT",
    "FAMILY_MAXIMUM_BASE_BEND_POINTS",
    "FAMILY_MAXIMUM_PERCENTS",
    "FIRST_SUPPORTED_ELIGIBILITY_YEAR",
    "FIRST_SUPPORTED_PAYMENT_MONTH",
    "GROSS_BENEFITS_VERSION",
    "PARISI_FIRST_PAYMENT_MONTH",
    "Beneficiary",
    "BeneficiaryBenefit",
    "BeneficiaryCondition",
    "FamilyBenefits",
    "FamilyConfigurationUnsupported",
    "FamilyDenominator",
    "FamilyKind",
    "FamilyOutcome",
    "FamilyTargetBlocked",
    "InvalidFamilyInput",
    "OwnBenefit",
    "OwnBenefitKind",
    "RecordCondition",
    "RecordState",
    "Role",
    "StatutoryRates",
    "UnsupportedReason",
    "WorkerRecord",
    "YearMonth",
    "applicable_cola_percents",
    "ceil_dime",
    "count_family_outcomes",
    "disability_family_maximum",
    "evaluate_family",
    "family_benefits",
    "family_maximum_bend_points",
    "family_maximum_formula",
    "floor_dime",
    "increase_by_colas",
    "original_benefit",
    "own_monthly_benefit",
    "record_state",
    "retirement_survivor_family_maximum",
    "spouse_age_reduced",
    "spouse_reduction_fraction",
    "statutory_rates",
    "survivor_reduction_fraction",
    "survivor_age_reduced",
    "weighted_mean_record_total",
    "weighted_record_total",
    "whole_dollars",
    "widow_reduction_period_months",
    "worker_age_adjusted",
    "worker_reduction_fraction",
]

GROSS_BENEFITS_VERSION = "track-b-g-v1"

# ---------------------------------------------------------------------------
# Statutory constants (each cited; none is a fitted or chosen value)
# ---------------------------------------------------------------------------

#: 42 U.S.C. 403(a)(2)(A): the 1979 family-maximum bend points.
FAMILY_MAXIMUM_BASE_BEND_POINTS = (230, 332, 433)
#: 42 U.S.C. 403(a)(1)(A)-(D): 150, 272, 134 and 175 percent.
FAMILY_MAXIMUM_PERCENTS = (
    Fraction(150, 100),
    Fraction(272, 100),
    Fraction(134, 100),
    Fraction(175, 100),
)
#: 403(a)(2)(B) via 215(a)(1)(B)(ii): the base-year wage index.
BASE_NAWI_YEAR = 1977
#: 42 U.S.C. 403(a)(6): 85 percent of AIME, floor 100 and cap 150 percent
#: of the PIA.
_DI_AIME_SHARE = Fraction(85, 100)
_DI_PIA_CAP = Fraction(150, 100)
#: POMS RS 00615.740B: the 1980 disability maximum applies only to initial
#: DIB entitlement after June 1980.
DI_MAXIMUM_FIRST_ENTITLEMENT = (1980, 7)
#: Eligibility years before 1983 are refused: a maximum fixed before June
#: 1982 was rounded up to the next dime (POMS RS 00615.736B.3 examples;
#: RS 00615.201B.1.c), and pre-1979 eligibility used the table maximums.
FIRST_SUPPORTED_ELIGIBILITY_YEAR = 1983
#: Benefits for months after May 1982 round reductions down to the dime
#: (RS 00615.101, .201); this layer computes months from January 1983.
FIRST_SUPPORTED_PAYMENT_MONTH = (1983, 1)
#: POMS RS 00615.768D.2: the dual-entitlement redistribution applies to
#: benefits payable for 10/99 or later (First Circuit cases earlier are
#: not modeled; months before 10/99 that need the rule are refused).
PARISI_FIRST_PAYMENT_MONTH = (1999, 10)

_DIME = Fraction(1, 10)
_HALF = Fraction(1, 2)
_MAX_WORKER_REDUCTION_MONTHS = 60
_MAX_SPOUSE_REDUCTION_MONTHS = 60
_SURVIVOR_PERIOD_RANGE = (60, 84)
#: POMS RS 00615.020B chart: a widow(er) born before 1/2/1928 who took
#: widow(er)'s benefits before 62 and then RIB carries a reduction over
#: (method D). The earliest whole birth year clear of it is 1929.
_FIRST_METHOD_B_WIDOW_BIRTH_YEAR = 1929


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class InvalidFamilyInput(ValueError):
    """The inputs do not describe a legal family (not a coverage gap)."""


class UnsupportedReason(Enum):
    """Why a statutory configuration is outside this layer (design §7)."""

    ELIGIBILITY_BEFORE_1983 = "eligibility_before_1983"
    PAYMENT_MONTH_BEFORE_1983 = "payment_month_before_1983"
    DI_ENTITLEMENT_BEFORE_JULY_1980 = "di_entitlement_before_july_1980"
    COMBINED_FAMILY_MAXIMUM = "combined_family_maximum"
    DEEMED_SPOUSE = "deemed_or_putative_spouse"
    PARENT_BENEFIT = "parent_benefit"
    DISABLED_WIDOW_UNDER_60 = "disabled_widow_under_60"
    DIB_GUARANTEE_PIA = "dib_guarantee_pia"
    DIB_AFTER_REDUCED_RIB = "dib_after_reduced_rib"
    WORKERS_COMPENSATION_OFFSET = "workers_compensation_offset"
    GOVERNMENT_PENSION_OFFSET = "government_pension_offset"
    ADMINISTRATIVE_FINALITY = "administrative_finality"
    DUAL_ENTITLEMENT_SEQUENCE = "dual_entitlement_sequence"
    PARISI_AMBIGUOUS = "parisi_redistribution_ambiguous"
    PARISI_BEFORE_OCTOBER_1999 = "parisi_before_october_1999"
    INDEPENDENT_DIVORCED_SPOUSE = "independently_entitled_divorced_spouse"
    NON_AIME_FORMULA_PIA = "non_aime_formula_pia"


class FamilyConfigurationUnsupported(Exception):
    """``FAMILY_CONFIG_UNSUPPORTED``: a configuration G cannot compute.

    Rows raising this stay in every denominator (use
    :func:`evaluate_family` and :func:`count_family_outcomes`); a target
    that needs them is blocked (:class:`FamilyTargetBlocked`).
    """

    code = "FAMILY_CONFIG_UNSUPPORTED"

    def __init__(
        self,
        reason: UnsupportedReason,
        detail: str,
        *,
        beneficiary_id: str | None = None,
    ):
        self.reason = reason
        self.detail = detail
        self.beneficiary_id = beneficiary_id
        where = f" (beneficiary {beneficiary_id})" if beneficiary_id else ""
        super().__init__(f"{self.code}[{reason.value}]{where}: {detail}")


class FamilyTargetBlocked(RuntimeError):
    """An aggregate would need rows whose configuration is unsupported."""


# ---------------------------------------------------------------------------
# Exact money helpers
# ---------------------------------------------------------------------------
def _exact(value: object, label: str) -> Fraction:
    """Convert to an exact Fraction; floats go through their shortest repr.

    ``repr(492.9)`` is ``'492.9'``, so a float PIA from the float oracle
    becomes the decimal it prints as, never its binary expansion.
    """
    if isinstance(value, bool):
        raise TypeError(f"{label} must be a number, not a bool")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, (int, Rational)):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} must be finite")
        return Fraction(repr(value))
    if isinstance(value, (str, Decimal)):
        result = Fraction(value)
        return result
    raise TypeError(f"{label} must be an exact number, got {type(value)}")


def _dimes(value: object, label: str) -> Fraction:
    """A nonnegative amount that the statute keeps in whole dimes."""
    amount = _exact(value, label)
    if amount < 0:
        raise InvalidFamilyInput(f"{label} must be nonnegative")
    if (amount * 10).denominator != 1:
        raise InvalidFamilyInput(f"{label} must be a multiple of $0.10")
    return amount


def floor_dime(amount: Fraction) -> Fraction:
    """Decrease to the next lower multiple of $0.10 (exact)."""
    return Fraction(math.floor(amount * 10), 10)


def ceil_dime(amount: Fraction) -> Fraction:
    """Increase to the next higher multiple of $0.10 (exact)."""
    return Fraction(math.ceil(amount * 10), 10)


def whole_dollars(amount: Fraction) -> int:
    """42 U.S.C. 415(g): round a monthly benefit down to a whole dollar."""
    if amount < 0:
        raise ValueError("A benefit amount cannot be negative")
    return math.floor(amount)


def _nearest_dollar_ties_up(amount: Fraction) -> int:
    """215(a)(1)(B)(iii): nearest $1; a multiple of $0.50 rounds up."""
    return math.floor(amount + _HALF)


@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month (the benefit month being computed)."""

    year: int
    month: int

    def __post_init__(self):
        if type(self.year) is not int or type(self.month) is not int:
            raise TypeError("YearMonth fields must be integers")
        if not 1 <= self.month <= 12:
            raise ValueError("month must be 1-12")

    def as_tuple(self) -> tuple[int, int]:
        return (self.year, self.month)


# ---------------------------------------------------------------------------
# Statutory rates, cross-checked against the repository's parameter bundle
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StatutoryRates:
    """Exact 402(q), 402(b)-(g) and 402(e)(2)(D) fractions."""

    worker_first: Fraction
    worker_later: Fraction
    worker_bracket_months: int
    spouse_first: Fraction
    spouse_later: Fraction
    spouse_bracket_months: int
    survivor_max_reduction: Fraction
    rib_lim_share: Fraction
    spouse_share: Fraction
    widow_share: Fraction
    pe_us_revision: str


_STATUTE = {
    # 402(q)(1)(A): 5/9 of 1 percent; 5/12 of 1 percent beyond 36 months
    # (POMS RS 00615.101B.1).
    "worker_first": Fraction(5, 900),
    "worker_later": Fraction(5, 1200),
    # 402(q)(1)(A): 25/36 of 1 percent; 5/12 of 1 percent beyond 36 months
    # (POMS RS 00615.201B.1).
    "spouse_first": Fraction(25, 3600),
    "spouse_later": Fraction(5, 1200),
    # A 28.5 percent maximum widow(er) reduction for every FRA: 402(q)(1)(A)'s
    # 19/40 of 1 percent over the 60 months from 60 to 65, kept at 28.5
    # percent as FRA rose (POMS RS 00615.301B.1).
    "survivor_max_reduction": Fraction(285, 1000),
    # 402(e)(2)(D)(ii): 82 1/2 percent.
    "rib_lim_share": Fraction(165, 200),
    # 402(b)(2)/(c)(2): one-half.
    "spouse_share": Fraction(1, 2),
    # 402(e)(2)(A)/(f)(3)(A): the PIA itself.
    "widow_share": Fraction(1),
}
_RATE_TOLERANCE = 1e-7


def _agrees(observed: float, expected: Fraction, label: str) -> None:
    if abs(float(observed) - float(expected)) > _RATE_TOLERANCE:
        raise ValueError(
            f"Parameter bundle {label}={observed!r} disagrees with the "
            f"statutory {expected}; refusing to compute gross benefits."
        )


def statutory_rates(params: SSAParameters) -> StatutoryRates:
    """Cross-check the bundle against the statute; return exact fractions.

    policyengine-us stores 5/9 of 1 percent as the decimal 0.00555556, and
    SSA computes with the fraction (POMS RS 00615.005B), so the fraction is
    what is used once the bundle is confirmed to encode the same rate.
    """
    worker_first, worker_later = params.early_monthly_rates
    _agrees(worker_first, _STATUTE["worker_first"], "early_monthly_rates[0]")
    _agrees(worker_later, _STATUTE["worker_later"], "early_monthly_rates[1]")
    spouse_first, spouse_later = params.spousal_early_monthly_rates
    _agrees(spouse_first, _STATUTE["spouse_first"], "spousal rate[0]")
    _agrees(spouse_later, _STATUTE["spouse_later"], "spousal rate[1]")
    _agrees(
        1 - params.survivor_reduction_floor,
        _STATUTE["survivor_max_reduction"],
        "1 - survivor_reduction_floor",
    )
    _agrees(params.rib_lim_pia_share, _STATUTE["rib_lim_share"], "rib_lim")
    _agrees(params.spousal_pia_share, _STATUTE["spouse_share"], "spouse")
    _agrees(params.survivor_pia_share, _STATUTE["widow_share"], "widow")
    if params.early_first_bracket_months != 36:
        raise ValueError("early_first_bracket_months must be 36 (402(q))")
    if params.spousal_early_first_bracket_months != 36:
        raise ValueError("spousal first bracket must be 36 months (402(q))")
    return StatutoryRates(
        worker_first=_STATUTE["worker_first"],
        worker_later=_STATUTE["worker_later"],
        worker_bracket_months=36,
        spouse_first=_STATUTE["spouse_first"],
        spouse_later=_STATUTE["spouse_later"],
        spouse_bracket_months=36,
        survivor_max_reduction=_STATUTE["survivor_max_reduction"],
        rib_lim_share=_STATUTE["rib_lim_share"],
        spouse_share=_STATUTE["spouse_share"],
        widow_share=_STATUTE["widow_share"],
        pe_us_revision=params.pe_us_revision,
    )


# ---------------------------------------------------------------------------
# Family maximum
# ---------------------------------------------------------------------------
def _nawi(params: SSAParameters, year: int) -> Fraction:
    if year not in params.nawi:
        raise KeyError(
            f"NAWI for {year} is not in the parameter bundle "
            f"(revision {params.pe_us_revision})."
        )
    return _exact(params.nawi[year], f"NAWI({year})")


def family_maximum_bend_points(
    eligibility_year: int, params: SSAParameters
) -> tuple[int, int, int]:
    """403(a)(2): the three family-maximum bend points for a year.

    Each 1979 amount times NAWI(year - 2) / NAWI(1977), rounded to the
    nearest dollar with 50-cent ties upward (215(a)(1)(B)(iii)).
    """
    if type(eligibility_year) is not int or eligibility_year < 1979:
        raise ValueError("The 403(a)(1) formula starts with 1979 eligibility")
    ratio = _nawi(params, eligibility_year - 2) / _nawi(params, BASE_NAWI_YEAR)
    first, second, third = (
        _nearest_dollar_ties_up(base * ratio)
        for base in FAMILY_MAXIMUM_BASE_BEND_POINTS
    )
    return first, second, third


def family_maximum_formula(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1)(A)-(D) before rounding: the exact formula amount."""
    amount = _dimes(pia, "PIA")
    points = family_maximum_bend_points(eligibility_year, params)
    lower = (0, *points)
    upper = (*points, None)
    total = Fraction(0)
    for percent, low, high in zip(
        FAMILY_MAXIMUM_PERCENTS, lower, upper, strict=True
    ):
        top = amount if high is None else min(amount, Fraction(high))
        if top > low:
            total += percent * (top - low)
    return total


def retirement_survivor_family_maximum(
    pia: object, eligibility_year: int, params: SSAParameters
) -> Fraction:
    """403(a)(1): the retirement/survivor maximum at eligibility.

    ``pia`` is the PIA for the year of first eligibility before any COLA
    (POMS RS 00615.736A.1). The result is dime-floored (403(a)(1), last
    sentence). Apply COLAs with :func:`increase_by_colas`.
    """
    _require_supported_eligibility(eligibility_year)
    return floor_dime(family_maximum_formula(pia, eligibility_year, params))


def disability_family_maximum(pia: object, aime: object) -> Fraction:
    """403(a)(6): min(max(85% AIME, PIA), 150% PIA), dime-floored.

    Both amounts are those before COLAs (POMS RS 00615.742.1); apply the
    intervening COLAs afterwards with :func:`increase_by_colas`.
    """
    amount = _dimes(pia, "PIA")
    earnings = _exact(aime, "AIME")
    if earnings < 0 or earnings.denominator != 1:
        raise InvalidFamilyInput("AIME must be a nonnegative whole dollar")
    return floor_dime(
        min(max(_DI_AIME_SHARE * earnings, amount), _DI_PIA_CAP * amount)
    )


def increase_by_colas(amount: object, percents: Iterable[object]) -> Fraction:
    """215(i)(2)(A)(ii): apply each COLA in order, dime-floored each time.

    ``percents`` are percentages (``"2.8"`` for a 2.8 percent COLA), exact
    or float. A zero COLA leaves the amount unchanged; negative COLAs do
    not exist under 215(i) and are refused.
    """
    value = _dimes(amount, "amount")
    for index, percent in enumerate(percents):
        rate = _exact(percent, f"COLA percent #{index}")
        if rate < 0:
            raise InvalidFamilyInput("A COLA percentage cannot be negative")
        value = floor_dime(value * (1 + rate / 100))
    return value


def applicable_cola_percents(
    eligibility_year: int,
    payment_month: YearMonth,
    december_cola_percent: Mapping[int, object],
) -> tuple[Fraction, ...]:
    """The COLAs that have raised a PIA and maximum by ``payment_month``.

    Increases start with the one effective in December of the eligibility
    year (215(i)(2)(A)(ii)-(iii), the convention
    ``scenario_benefits.increased_pia_path`` already uses); each is
    effective with December of its year. ``december_cola_percent`` maps
    that December's year to the percentage (for example R1's
    ``ret_history.json`` ``december_cola_percent``). A missing year raises
    rather than counting as zero.
    """
    _require_supported_eligibility(eligibility_year)
    if not isinstance(payment_month, YearMonth):
        raise TypeError("payment_month must be a YearMonth")
    last = payment_month.year - (0 if payment_month.month == 12 else 1)
    percents = []
    for year in range(eligibility_year, last + 1):
        if year not in december_cola_percent:
            raise KeyError(f"No COLA percentage for December {year}")
        percents.append(_exact(december_cola_percent[year], f"COLA {year}"))
    return tuple(percents)


def _require_supported_eligibility(eligibility_year: int) -> None:
    if type(eligibility_year) is not int:
        raise TypeError("eligibility_year must be an int")
    if eligibility_year < FIRST_SUPPORTED_ELIGIBILITY_YEAR:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.ELIGIBILITY_BEFORE_1983,
            f"eligibility year {eligibility_year}: maximums fixed before "
            "June 1982 were rounded up to the dime (POMS RS 00615.736B.3) "
            "and pre-1979 eligibility used table maximums; neither is "
            "implemented",
        )


# ---------------------------------------------------------------------------
# Age adjustments (exact fractions, POMS RS 00615.101/.201/.301/.692)
# ---------------------------------------------------------------------------
def _months(value: int, label: str, upper: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{label} must be an int")
    if not 0 <= value <= upper:
        raise InvalidFamilyInput(f"{label} must be between 0 and {upper}")
    return value


def _worker_reduction(months: int, rates: StatutoryRates) -> Fraction:
    first = min(months, rates.worker_bracket_months)
    later = max(0, months - rates.worker_bracket_months)
    return first * rates.worker_first + later * rates.worker_later


def _spouse_reduction(months: int, rates: StatutoryRates) -> Fraction:
    first = min(months, rates.spouse_bracket_months)
    later = max(0, months - rates.spouse_bracket_months)
    return first * rates.spouse_first + later * rates.spouse_later


def worker_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) old-age reduction for ``months`` months (RS 00615.101)."""
    months = _months(months, "months", _MAX_WORKER_REDUCTION_MONTHS)
    return _worker_reduction(months, statutory_rates(params))


def spouse_reduction_fraction(months: int, params: SSAParameters) -> Fraction:
    """402(q)(1) spouse's reduction for ``months`` months (RS 00615.201)."""
    months = _months(months, "months", _MAX_SPOUSE_REDUCTION_MONTHS)
    return _spouse_reduction(months, statutory_rates(params))


def survivor_reduction_fraction(
    months: int, reduction_period_months: int, params: SSAParameters
) -> Fraction:
    """Widow(er)'s reduction: 28.5 percent spread over the period.

    This is the fraction before SSA's rounding of the reduction amount;
    :func:`survivor_age_reduced` applies it to a benefit.
    """
    period = _survivor_period(reduction_period_months)
    months = _months(months, "months", period)
    return statutory_rates(params).survivor_max_reduction * months / period


def _drc_monthly_rate(birth_year: int, params: SSAParameters) -> Fraction:
    """402(w) monthly credit: the cohort's annual rate over 12, exactly."""
    annual = _exact(
        params.delayed_credit_annual_rate(birth_year), "DRC annual rate"
    )
    return annual / 12


def worker_age_adjusted(
    pia: object,
    reduction_months: int,
    delayed_credit_months: int,
    birth_year: int | None,
    params: SSAParameters,
) -> tuple[Fraction, Fraction]:
    """An old-age benefit before and after delayed credits.

    Reduction: PIA x (180 - RF)/180 or (192 - ARM)/240, dime-floored (POMS
    RS 00615.101). Credits: base x months x monthly rate, dime-floored and
    added to the base, which is the PIA or, after a reduced RIB, the MBA
    (RS 00615.692A, C). Returns ``(without_credits, with_credits)``.
    """
    rates = statutory_rates(params)
    amount = _dimes(pia, "PIA")
    reduction_months = _months(
        reduction_months, "reduction_months", _MAX_WORKER_REDUCTION_MONTHS
    )
    delayed_credit_months = _months(
        delayed_credit_months,
        "delayed_credit_months",
        params.max_delayed_months,
    )
    base = floor_dime(
        amount * (1 - _worker_reduction(reduction_months, rates))
    )
    if delayed_credit_months == 0:
        return base, base
    if birth_year is None:
        raise InvalidFamilyInput("Delayed credits need the birth year")
    credit = floor_dime(
        base * delayed_credit_months * _drc_monthly_rate(birth_year, params)
    )
    return base, base + credit


def spouse_age_reduced(
    amount: object, reduction_months: int, params: SSAParameters
) -> Fraction:
    """A spouse's benefit (after the maximum) reduced for age, dime-floored.

    RF 1-36: x (144 - RF)/144; RF 37-60: x (180 - ARM)/240 (POMS RS
    00615.201B.1.c). ``amount`` is the OB, or the family-maximum share when
    the maximum applies.
    """
    rates = statutory_rates(params)
    value = _dimes(amount, "spouse benefit")
    months = _months(
        reduction_months, "reduction_months", _MAX_SPOUSE_REDUCTION_MONTHS
    )
    return floor_dime(value * (1 - _spouse_reduction(months, rates)))


def survivor_age_reduced(
    amount: object,
    reduction_months: int,
    reduction_period_months: int,
    params: SSAParameters,
) -> Fraction:
    """A widow(er)'s benefit (after the maximum) reduced for age.

    MAR = amount x RF x .285 / total possible RF, rounded *up* to the dime;
    MBA = amount - MAR (POMS RS 00615.301B.1.c-d).
    """
    rates = statutory_rates(params)
    value = _dimes(amount, "widow(er) benefit")
    period = _survivor_period(reduction_period_months)
    months = _months(reduction_months, "reduction_months", period)
    reduction = ceil_dime(
        value * months * rates.survivor_max_reduction / period
    )
    return value - reduction


def _survivor_period(value: int) -> int:
    low, high = _SURVIVOR_PERIOD_RANGE
    if type(value) is not int or not low <= value <= high:
        raise InvalidFamilyInput(
            "reduction_period_months must be an int between 60 and 84"
        )
    return value


#: POMS RS 00615.301B.2: widow(er) full retirement age by date of birth,
#: as (last birth date in the band, months from age 60 to that FRA).
_WIDOW_PERIOD_BY_BIRTH = (
    (date(1940, 1, 1), 60),
    (date(1941, 1, 1), 62),
    (date(1942, 1, 1), 64),
    (date(1943, 1, 1), 66),
    (date(1944, 1, 1), 68),
    (date(1945, 1, 1), 70),
    (date(1957, 1, 1), 72),
    (date(1958, 1, 1), 74),
    (date(1959, 1, 1), 76),
    (date(1960, 1, 1), 78),
    (date(1961, 1, 1), 80),
    (date(1962, 1, 1), 82),
)


def widow_reduction_period_months(birth_date: date) -> int:
    """Total possible widow(er) reduction months for a date of birth.

    POMS RS 00615.301B.2: FRA 65 through 1/1/40, rising two months per
    year to 66 (born 1/2/45-1/1/57), then to 67 for births on or after
    1/2/62. The period runs from age 60 to that FRA.
    """
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a datetime.date")
    for last_birth_date, period in _WIDOW_PERIOD_BY_BIRTH:
        if birth_date <= last_birth_date:
            return period
    return 84


# ---------------------------------------------------------------------------
# Family inputs
# ---------------------------------------------------------------------------
class FamilyKind(Enum):
    """Whose record: a living retired worker, a disabled worker, a death."""

    RETIREMENT = "retirement"
    DISABILITY = "disability"
    SURVIVOR = "survivor"


class Role(Enum):
    """The auxiliary or survivor benefit a beneficiary claims."""

    SPOUSE = "spouse"  # 402(b)/(c), aged
    SPOUSE_CHILD_IN_CARE = "spouse_child_in_care"  # 402(b)/(c), not reduced
    DIVORCED_SPOUSE = "divorced_spouse"  # outside the maximum
    CHILD = "child"  # 402(d)
    WIDOW = "widow"  # 402(e)/(f), aged widow(er)
    SURVIVING_DIVORCED_SPOUSE = "surviving_divorced_spouse"  # outside
    MOTHER_FATHER = "mother_father"  # 402(g), incl. surviving divorced
    PARENT = "parent"  # 402(h): refused
    DISABLED_WIDOW = "disabled_widow"  # 402(e)/(f) under 60: refused


_LIFE_ROLES = frozenset(
    {Role.SPOUSE, Role.SPOUSE_CHILD_IN_CARE, Role.DIVORCED_SPOUSE, Role.CHILD}
)
_SURVIVOR_ROLES = frozenset(
    {
        Role.WIDOW,
        Role.SURVIVING_DIVORCED_SPOUSE,
        Role.MOTHER_FATHER,
        Role.CHILD,
        Role.PARENT,
        Role.DISABLED_WIDOW,
    }
)
_OUTSIDE_MAXIMUM = frozenset(
    {Role.DIVORCED_SPOUSE, Role.SURVIVING_DIVORCED_SPOUSE}
)
_SPOUSE_ROLES = frozenset(
    {Role.SPOUSE, Role.SPOUSE_CHILD_IN_CARE, Role.DIVORCED_SPOUSE}
)
_WIDOW_ROLES = frozenset({Role.WIDOW, Role.SURVIVING_DIVORCED_SPOUSE})
_AGE_REDUCED_ROLES = frozenset({Role.SPOUSE, Role.DIVORCED_SPOUSE}) | (
    _WIDOW_ROLES
)


class RecordCondition(Enum):
    """Record-level conditions the caller must declare when present."""

    DIB_GUARANTEE_PIA = "dib_guarantee_pia"  # RS 00615.736B.2, .738
    DIB_AFTER_REDUCED_RIB = "dib_after_reduced_rib"  # 402(q)(2)
    WORKERS_COMPENSATION_OFFSET = "workers_compensation_offset"  # 224
    ADMINISTRATIVE_FINALITY = "administrative_finality"  # RS 00615.754A.3
    #: The living worker is not entitled to a RIB or DIB; only a divorced
    #: spouse can be entitled on the record (402(b)(4)(A), (c)(4)(A)).
    WORKER_NOT_ENTITLED = "worker_not_entitled"
    #: The PIA is not an AIME-formula PIA (for example an old-start,
    #: special-minimum or frozen-minimum PIA; RS 00615.740B.1 lists them).
    NON_AIME_FORMULA_PIA = "non_aime_formula_pia"


class BeneficiaryCondition(Enum):
    """Beneficiary-level conditions the caller must declare when present."""

    ENTITLED_ON_ANOTHER_RECORD = "entitled_on_another_record"  # 203(a)(3)(A)
    DEEMED_OR_PUTATIVE_SPOUSE = "deemed_or_putative_spouse"  # 203(a)(3)(D)
    LEGAL_SPOUSE_WITH_DEEMED_SPOUSE = "legal_spouse_with_deemed_spouse"
    GOVERNMENT_PENSION_OFFSET = "government_pension_offset"  # 202(k)(5)
    RATE_PROTECTED_BY_FINALITY = "rate_protected_by_finality"
    #: A DIB between a reduced spouse's benefit and a later RIB, which
    #: changes the later spouse excess (RS 00615.260B.2).
    DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB = "dib_between_spouse_benefit_and_rib"


_RECORD_CONDITION_REASONS = {
    RecordCondition.DIB_GUARANTEE_PIA: (
        UnsupportedReason.DIB_GUARANTEE_PIA,
        "DIB guarantee PIA maximums (POMS RS 00615.736B.2, .738)",
    ),
    RecordCondition.DIB_AFTER_REDUCED_RIB: (
        UnsupportedReason.DIB_AFTER_REDUCED_RIB,
        "a DIB reduced for prior reduced RIB (402(q)(2))",
    ),
    RecordCondition.WORKERS_COMPENSATION_OFFSET: (
        UnsupportedReason.WORKERS_COMPENSATION_OFFSET,
        "the section 224 workers' compensation offset",
    ),
    RecordCondition.ADMINISTRATIVE_FINALITY: (
        UnsupportedReason.ADMINISTRATIVE_FINALITY,
        "rates protected by administrative finality (RS 00615.754A.3)",
    ),
    RecordCondition.WORKER_NOT_ENTITLED: (
        UnsupportedReason.INDEPENDENT_DIVORCED_SPOUSE,
        "a divorced spouse entitled while the living worker is not "
        "entitled (402(b)(4)(A), (c)(4)(A)) is not implemented",
    ),
    RecordCondition.NON_AIME_FORMULA_PIA: (
        UnsupportedReason.NON_AIME_FORMULA_PIA,
        "maximums for PIAs other than the AIME formula PIA (old-start, "
        "special minimum, frozen minimum; RS 00615.740B.1) are not "
        "implemented",
    ),
}
_BENEFICIARY_CONDITION_REASONS = {
    BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD: (
        UnsupportedReason.COMBINED_FAMILY_MAXIMUM,
        "a child entitled on more than one record may need a combined "
        "family maximum (403(a)(3)(A); POMS RS 00615.770)",
    ),
    BeneficiaryCondition.DEEMED_OR_PUTATIVE_SPOUSE: (
        UnsupportedReason.DEEMED_SPOUSE,
        "deemed or putative spouse (403(a)(3)(D); RS 00615.684)",
    ),
    BeneficiaryCondition.LEGAL_SPOUSE_WITH_DEEMED_SPOUSE: (
        UnsupportedReason.DEEMED_SPOUSE,
        "legal spouse paid outside the maximum because a deemed spouse "
        "is entitled (403(a)(3)(D); RS 00615.684)",
    ),
    BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET: (
        UnsupportedReason.GOVERNMENT_PENSION_OFFSET,
        "the 402(k)(5) government pension offset",
    ),
    BeneficiaryCondition.RATE_PROTECTED_BY_FINALITY: (
        UnsupportedReason.ADMINISTRATIVE_FINALITY,
        "a rate protected by administrative finality (RS 00615.754A.3)",
    ),
    BeneficiaryCondition.DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB: (
        UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
        "a DIB between a reduced spouse's benefit and the RIB carries the "
        "RIB reduction into the spouse excess (RS 00615.260B.2); not "
        "implemented",
    ),
}


class OwnBenefitKind(Enum):
    OLD_AGE = "old_age"
    DISABILITY = "disability"


@dataclass(frozen=True)
class OwnBenefit:
    """A person's own old-age (RIB) or disability (DIB) benefit.

    ``pia`` is that person's current PIA (after COLAs). Reduction months
    are the 402(q) worker months after any ARF; delayed-credit months need
    ``birth_year`` for the 402(w) rate. A DIB is unreduced and has no
    credits here (402(q)(2) cases are refused).
    """

    kind: OwnBenefitKind
    pia: Fraction
    reduction_months: int = 0
    delayed_credit_months: int = 0
    birth_year: int | None = None

    def __post_init__(self):
        if not isinstance(self.kind, OwnBenefitKind):
            raise TypeError("kind must be an OwnBenefitKind")
        object.__setattr__(self, "pia", _dimes(self.pia, "own PIA"))
        if self.kind is OwnBenefitKind.DISABILITY:
            if self.reduction_months:
                raise FamilyConfigurationUnsupported(
                    UnsupportedReason.DIB_AFTER_REDUCED_RIB,
                    "a DIB reduced for prior reduced RIB (402(q)(2))",
                )
            if self.delayed_credit_months:
                raise InvalidFamilyInput("A DIB earns no delayed credits")


def own_monthly_benefit(
    own: OwnBenefit, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """The own benefit ``(without_credits, with_credits)`` after 402(q)/(w)."""
    return worker_age_adjusted(
        own.pia,
        own.reduction_months,
        own.delayed_credit_months,
        own.birth_year,
        params,
    )


@dataclass(frozen=True)
class Beneficiary:
    """One auxiliary or survivor on the worker's record for the month.

    * ``reduction_months``: 402(q) months (after any ARF) for an aged
      spouse, divorced spouse or widow(er); zero for other roles.
    * ``reduction_period_months``: a widow(er)'s total possible reduction
      months (60-84, :func:`widow_reduction_period_months`); required when
      ``reduction_months`` is positive.
    * ``original_benefit_basis``: a widow(er)'s OB when it exceeds the death
      PIA (deceased's delayed credits or windexing, POMS RS 00615.301A.3,
      .302, .710); defaults to the PIA.
    * ``own_benefit`` / ``own_benefit_first``: dual entitlement, and whether
      the own benefit began in or before the auxiliary benefit's first month.
      For an aged spouse this selects method C (True: A then B, or A with
      B; RS 00615.250) or method B (False: B then A; RS 00615.240); a
      spouse's DIB after the spouse benefit is refused (RS 00615.260).
    * ``birth_year``: needed for a widow(er) with an own old-age benefit.
    * ``conditions``: declared special conditions (all refused).
    """

    beneficiary_id: str
    role: Role
    reduction_months: int = 0
    reduction_period_months: int | None = None
    original_benefit_basis: Fraction | None = None
    own_benefit: OwnBenefit | None = None
    own_benefit_first: bool = True
    birth_year: int | None = None
    conditions: frozenset[BeneficiaryCondition] = field(
        default_factory=frozenset
    )

    def __post_init__(self):
        if not isinstance(self.beneficiary_id, str) or not self.beneficiary_id:
            raise InvalidFamilyInput("beneficiary_id must be a nonempty str")
        if not isinstance(self.role, Role):
            raise TypeError("role must be a Role")
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        for condition in self.conditions:
            if not isinstance(condition, BeneficiaryCondition):
                raise TypeError("conditions must be BeneficiaryConditions")
        if self.original_benefit_basis is not None:
            if self.role not in _WIDOW_ROLES:
                raise InvalidFamilyInput(
                    "Only a widow(er) OB can differ from the PIA share"
                )
            object.__setattr__(
                self,
                "original_benefit_basis",
                _dimes(self.original_benefit_basis, "OB basis"),
            )
        if self.own_benefit is not None and not isinstance(
            self.own_benefit, OwnBenefit
        ):
            raise TypeError("own_benefit must be an OwnBenefit")
        if type(self.reduction_months) is not int:
            raise TypeError("reduction_months must be an int")
        if self.reduction_months < 0:
            raise InvalidFamilyInput("reduction_months must be nonnegative")
        if self.reduction_months and self.role not in _AGE_REDUCED_ROLES:
            raise InvalidFamilyInput(
                f"A {self.role.value} benefit is not reduced for age"
            )
        if self.reduction_period_months is not None:
            if self.role not in _WIDOW_ROLES:
                raise InvalidFamilyInput(
                    "Only a widow(er) has a survivor reduction period"
                )
            _survivor_period(self.reduction_period_months)


@dataclass(frozen=True)
class WorkerRecord:
    """The insured worker's record, from which the maximum is computed.

    ``eligibility_pia`` is the PIA for the year of first eligibility before
    COLAs; ``cola_percents`` are the increases from then through the
    payment month, in order (:func:`applicable_cola_percents` selects them
    from a December-COLA history). The eligibility year of a worker who was
    entitled to DIB within the 12 preceding months is the DIB eligibility
    year (403(a)(2)(D)); the caller supplies it. A disability record needs
    the AIME and the month of the worker's initial DIB entitlement ever
    (the RS 00615.740B test for the 1980 disability maximum). A DIB that
    has converted to a RIB, or a worker who has died, takes a retirement or
    survivor record (RS 00615.742.2). ``worker_*`` fields
    describe the living worker's own RIB (retirement records only).
    ``rib_lim_benefit`` is, for a death, the reduced RIB or DIB the
    deceased would receive if alive (402(e)(2)(D)); None when the deceased
    never received a reduced benefit.
    """

    kind: FamilyKind
    eligibility_year: int
    eligibility_pia: Fraction
    cola_percents: tuple[Fraction, ...] = ()
    aime: int | None = None
    first_dib_entitlement: YearMonth | None = None
    worker_reduction_months: int = 0
    worker_delayed_credit_months: int = 0
    worker_birth_year: int | None = None
    rib_lim_benefit: Fraction | None = None
    conditions: frozenset[RecordCondition] = field(default_factory=frozenset)

    def __post_init__(self):
        if not isinstance(self.kind, FamilyKind):
            raise TypeError("kind must be a FamilyKind")
        object.__setattr__(
            self, "eligibility_pia", _dimes(self.eligibility_pia, "PIA")
        )
        object.__setattr__(
            self,
            "cola_percents",
            tuple(
                _exact(p, "COLA percent") for p in tuple(self.cola_percents)
            ),
        )
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        if self.rib_lim_benefit is not None:
            if self.kind is not FamilyKind.SURVIVOR:
                raise InvalidFamilyInput("A RIB-LIM applies only to deaths")
            object.__setattr__(
                self,
                "rib_lim_benefit",
                _dimes(self.rib_lim_benefit, "RIB-LIM benefit"),
            )
        if self.kind is not FamilyKind.RETIREMENT and (
            self.worker_reduction_months or self.worker_delayed_credit_months
        ):
            raise InvalidFamilyInput(
                "Own-RIB months describe a living retired worker only"
            )
        if self.first_dib_entitlement is not None and not isinstance(
            self.first_dib_entitlement, YearMonth
        ):
            raise TypeError("first_dib_entitlement must be a YearMonth")


@dataclass(frozen=True)
class RecordState:
    """A record's current PIA and family maximum for the payment month.

    Built by :func:`record_state` from a :class:`WorkerRecord`, or directly
    when a published example (or SSA's master record) gives both amounts.
    For a retirement record ``worker`` is the worker's own RIB.
    """

    kind: FamilyKind
    pia: Fraction
    family_maximum: Fraction
    worker: OwnBenefit | None = None
    rib_lim_benefit: Fraction | None = None
    conditions: frozenset[RecordCondition] = field(default_factory=frozenset)
    source: str = "given"

    def __post_init__(self):
        if not isinstance(self.kind, FamilyKind):
            raise TypeError("kind must be a FamilyKind")
        pia = _dimes(self.pia, "PIA")
        maximum = _dimes(self.family_maximum, "family maximum")
        if maximum < pia:
            raise InvalidFamilyInput("The family maximum is below the PIA")
        object.__setattr__(self, "pia", pia)
        object.__setattr__(self, "family_maximum", maximum)
        object.__setattr__(self, "conditions", frozenset(self.conditions))
        if self.kind is FamilyKind.RETIREMENT:
            if self.worker is None:
                raise InvalidFamilyInput("A retirement record needs a worker")
            if self.worker.kind is not OwnBenefitKind.OLD_AGE:
                raise InvalidFamilyInput("A retired worker receives a RIB")
            if self.worker.pia != pia:
                raise InvalidFamilyInput("The worker's PIA must be the PIA")
        elif self.worker is not None:
            raise InvalidFamilyInput("Only a retirement record has a RIB")
        if self.rib_lim_benefit is not None:
            if self.kind is not FamilyKind.SURVIVOR:
                raise InvalidFamilyInput("A RIB-LIM applies only to deaths")
            object.__setattr__(
                self,
                "rib_lim_benefit",
                _dimes(self.rib_lim_benefit, "RIB-LIM benefit"),
            )


def _raise_record_conditions(conditions: Iterable[RecordCondition]) -> None:
    for condition in sorted(conditions, key=lambda c: c.value):
        reason, detail = _RECORD_CONDITION_REASONS[condition]
        raise FamilyConfigurationUnsupported(reason, detail)


def record_state(record: WorkerRecord, params: SSAParameters) -> RecordState:
    """Compute the record's current PIA and family maximum."""
    _raise_record_conditions(record.conditions)
    _require_supported_eligibility(record.eligibility_year)
    if record.kind is FamilyKind.DISABILITY:
        if record.aime is None or record.first_dib_entitlement is None:
            raise InvalidFamilyInput(
                "A disability record needs aime and first_dib_entitlement"
            )
        if record.first_dib_entitlement.as_tuple() < (
            DI_MAXIMUM_FIRST_ENTITLEMENT
        ):
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980,
                "DIB first entitled before July 1980 keeps the pre-1980 "
                "maximum (POMS RS 00615.740B.2)",
            )
        base_maximum = disability_family_maximum(
            record.eligibility_pia, record.aime
        )
    else:
        base_maximum = retirement_survivor_family_maximum(
            record.eligibility_pia, record.eligibility_year, params
        )
    pia = increase_by_colas(record.eligibility_pia, record.cola_percents)
    maximum = increase_by_colas(base_maximum, record.cola_percents)
    worker = None
    if record.kind is FamilyKind.RETIREMENT:
        worker = OwnBenefit(
            kind=OwnBenefitKind.OLD_AGE,
            pia=pia,
            reduction_months=record.worker_reduction_months,
            delayed_credit_months=record.worker_delayed_credit_months,
            birth_year=record.worker_birth_year,
        )
    return RecordState(
        kind=record.kind,
        pia=pia,
        family_maximum=maximum,
        worker=worker,
        rib_lim_benefit=record.rib_lim_benefit,
        conditions=record.conditions,
        source=(
            f"computed: eligibility {record.eligibility_year}, "
            f"{len(record.cola_percents)} COLA(s)"
        ),
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BeneficiaryBenefit:
    """One beneficiary's gross amounts for the month (exact dimes).

    * ``original_benefit``: OB before the maximum.
    * ``standard_rate``: the proportional family-maximum share over every
      subject beneficiary (equal to OB when the maximum does not bind).
    * ``family_maximum_rate``: the rate after redistribution (differs from
      ``standard_rate`` only for non-dually-entitled beneficiaries when
      the RS 00615.768 rule redistributes).
    * ``counted_against_maximum``: what this beneficiary uses of the
      maximum; zero for a beneficiary outside it.
    * ``age_adjusted_rate``: after 402(q) and the RIB-LIM, before the
      dual-entitlement offset.
    * ``auxiliary_payable``: paid on this record after 402(k)(3)(A).
    * ``own_benefit``: the own RIB/DIB paid on the person's own record.
    """

    beneficiary_id: str
    role: Role
    entitled: bool
    subject_to_family_maximum: bool
    original_benefit: Fraction
    standard_rate: Fraction
    family_maximum_rate: Fraction
    counted_against_maximum: Fraction
    age_adjusted_rate: Fraction
    auxiliary_payable: Fraction
    own_benefit: Fraction | None
    whole_dollar_auxiliary: int
    whole_dollar_own: int | None
    note: str = ""

    @property
    def total_received(self) -> Fraction:
        """Auxiliary plus own benefit (the person's gross monthly total)."""
        return self.auxiliary_payable + (self.own_benefit or Fraction(0))


@dataclass(frozen=True)
class FamilyBenefits:
    """Gross monthly benefits on one record for one month."""

    kind: FamilyKind
    payment_month: YearMonth
    pia: Fraction
    family_maximum: Fraction
    available_for_auxiliaries: Fraction
    total_original_benefits: Fraction
    family_maximum_binding: bool
    redistribution_applied: bool
    worker_benefit: Fraction | None
    whole_dollar_worker: int | None
    beneficiaries: tuple[BeneficiaryBenefit, ...]
    record_total: Fraction
    record_total_whole_dollars: int
    subject_total: Fraction
    state_source: str
    pe_us_revision: str
    version: str = GROSS_BENEFITS_VERSION

    def by_id(self) -> Mapping[str, BeneficiaryBenefit]:
        return MappingProxyType(
            {row.beneficiary_id: row for row in self.beneficiaries}
        )


# ---------------------------------------------------------------------------
# The family computation
# ---------------------------------------------------------------------------
def original_benefit(
    role: Role,
    kind: FamilyKind,
    pia: Fraction,
    basis: Fraction | None = None,
) -> Fraction:
    """The OB: the statutory share of the PIA, dime-floored.

    402(b)/(c)(2) 1/2; 402(d)(2) 1/2, or 3/4 after the worker's death;
    402(e)/(f)(2)(A) 100 percent (or the widow(er)'s larger OB basis);
    402(g)(2) 3/4.
    """
    if role in _SPOUSE_ROLES:
        share = Fraction(1, 2)
    elif role is Role.CHILD:
        share = (
            Fraction(3, 4) if kind is FamilyKind.SURVIVOR else Fraction(1, 2)
        )
    elif role in _WIDOW_ROLES:
        if basis is not None:
            if basis < pia:
                raise InvalidFamilyInput(
                    "A widow(er) OB basis cannot be below the death PIA"
                )
            return basis
        share = Fraction(1)
    elif role is Role.MOTHER_FATHER:
        share = Fraction(3, 4)
    else:
        raise ValueError(f"No original benefit is defined for {role}")
    return floor_dime(share * pia)


def _validate_beneficiary(beneficiary: Beneficiary, kind: FamilyKind) -> None:
    allowed = _SURVIVOR_ROLES if kind is FamilyKind.SURVIVOR else _LIFE_ROLES
    if beneficiary.role not in allowed:
        raise InvalidFamilyInput(
            f"A {beneficiary.role.value} cannot be entitled on a "
            f"{kind.value} record"
        )
    bid = beneficiary.beneficiary_id
    if beneficiary.role is Role.PARENT:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PARENT_BENEFIT,
            "parent's benefits (402(h)) are not implemented",
            beneficiary_id=bid,
        )
    if beneficiary.role is Role.DISABLED_WIDOW:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.DISABLED_WIDOW_UNDER_60,
            "disabled widow(er)'s benefits before 60 are not implemented",
            beneficiary_id=bid,
        )
    for condition in sorted(beneficiary.conditions, key=lambda c: c.value):
        reason, detail = _BENEFICIARY_CONDITION_REASONS[condition]
        raise FamilyConfigurationUnsupported(
            reason, detail, beneficiary_id=bid
        )
    own = beneficiary.own_benefit
    if beneficiary.role in _WIDOW_ROLES:
        if beneficiary.reduction_months and (
            beneficiary.reduction_period_months is None
        ):
            raise InvalidFamilyInput(
                "A reduced widow(er) needs reduction_period_months"
            )
        if (
            beneficiary.reduction_period_months is not None
            and beneficiary.reduction_months
            > beneficiary.reduction_period_months
        ):
            raise InvalidFamilyInput("reduction_months exceed the period")
        if own is not None:
            if own.kind is OwnBenefitKind.DISABILITY:
                raise FamilyConfigurationUnsupported(
                    UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                    "a widow(er) also entitled to DIB (402(q)(3)(C); POMS "
                    "RS 00615.350) is not implemented",
                    beneficiary_id=bid,
                )
            if beneficiary.birth_year is None:
                raise InvalidFamilyInput(
                    "A dually entitled widow(er) needs birth_year"
                )
            if beneficiary.birth_year < _FIRST_METHOD_B_WIDOW_BIRTH_YEAR:
                raise FamilyConfigurationUnsupported(
                    UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
                    "widow(er)s born before 1929 may carry a WIB reduction "
                    "into RIB (POMS RS 00615.020B, method D)",
                    beneficiary_id=bid,
                )
    if (
        beneficiary.role in (Role.SPOUSE, Role.DIVORCED_SPOUSE)
        and own is not None
        and not beneficiary.own_benefit_first
        and own.kind is OwnBenefitKind.DISABILITY
    ):
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE,
            "a spouse entitled to spouse's benefits before a DIB (B then "
            "HA; POMS RS 00615.260: deemed RIB filing and a later RIB "
            "change the excess) is not implemented",
            beneficiary_id=bid,
        )


@dataclass
class _Row:
    beneficiary: Beneficiary
    entitled: bool
    subject: bool
    ob: Fraction
    own_base: Fraction | None
    own_mba: Fraction | None
    standard: Fraction = Fraction(0)
    rate: Fraction = Fraction(0)
    counted: Fraction = Fraction(0)
    note: str = ""

    @property
    def dual(self) -> bool:
        return self.own_mba is not None


def _is_entitled(
    beneficiary: Beneficiary, pia: Fraction, own_mba: Fraction | None
) -> tuple[bool, str]:
    own = beneficiary.own_benefit
    if own is None:
        return True, ""
    if beneficiary.role in _SPOUSE_ROLES and own.pia * 2 >= pia:
        return False, "own PIA at least one-half of the PIA (402(b)(1)(D))"
    if beneficiary.role in _WIDOW_ROLES and own.kind is (
        OwnBenefitKind.OLD_AGE
    ):
        # 402(e)(1)(D) compares with the PIA "as determined after
        # application of subparagraphs (B) and (C) of paragraph (2)": the
        # windexed PIA, or the PIA deemed equal to the deceased's
        # credit-increased benefit, i.e. the widow(er)'s OB basis.
        deemed_pia = beneficiary.original_benefit_basis or pia
        if own_mba >= deemed_pia:
            return False, "own RIB not less than the PIA (402(e)(1)(D))"
    if (
        beneficiary.role is Role.MOTHER_FATHER
        and own.kind is OwnBenefitKind.OLD_AGE
        and own_mba * 4 >= pia * 3
    ):
        return False, "own RIB not less than 3/4 of the PIA (402(g)(1)(C))"
    return True, ""


def _proportional(rows: Sequence[_Row], available: Fraction) -> list[Fraction]:
    """RS 00615.756: OB x available / total OB, not above OB, dime-floored."""
    total = sum((row.ob for row in rows), Fraction(0))
    if total <= available:
        return [row.ob for row in rows]
    return [
        max(Fraction(0), min(row.ob, floor_dime(row.ob * available / total)))
        for row in rows
    ]


def _parisi_counted(row: _Row, state: RecordState) -> Fraction:
    """What a dually entitled beneficiary uses of the maximum (RS 00615.768).

    "Other beneficiaries on a record will be reduced only by the amount
    payable to the dually entitled beneficiary before any age reduction."
    That amount is the family-maximum share less the own benefit, not
    below zero, when the own benefit is neither reduced under 402(q) nor
    increased under 402(w). Otherwise "before any age reduction" has two
    readings (offset by the own PIA, or by the own benefit as paid; under
    method C the own RIB's reduction is itself part of the spouse
    reduction, 402(q)(3)(B)(i)), and a RIB-LIM limited widow(er) has a
    third, so those cases are refused for every role rather than guessed.
    """
    beneficiary = row.beneficiary
    own = beneficiary.own_benefit
    bid = beneficiary.beneficiary_id
    if row.own_mba != own.pia or row.own_base != own.pia:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PARISI_AMBIGUOUS,
            "redistribution around a dually entitled beneficiary whose own "
            "benefit is reduced for age or increased by delayed credits",
            beneficiary_id=bid,
        )
    if beneficiary.role in _WIDOW_ROLES and state.rib_lim_benefit is not None:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PARISI_AMBIGUOUS,
            "redistribution around a RIB-LIM limited widow(er)",
            beneficiary_id=bid,
        )
    return max(Fraction(0), row.standard - own.pia)


def _reduce_and_offset(
    row: _Row, state: RecordState, params: SSAParameters
) -> tuple[Fraction, Fraction]:
    """402(q) (and the RIB-LIM), then 402(k)(3)(A).

    Returns ``(age_adjusted, payable)``: the auxiliary benefit after its
    age reduction, and the amount payable on this record after the
    dual-entitlement offset.
    """
    beneficiary = row.beneficiary
    own = beneficiary.own_benefit
    rate = row.rate
    if beneficiary.role in (Role.SPOUSE, Role.DIVORCED_SPOUSE):
        if own is None or not beneficiary.own_benefit_first:
            reduced = spouse_age_reduced(
                rate, beneficiary.reduction_months, params
            )
            if own is None:
                return reduced, reduced
            # B then A (method B, POMS RS 00615.240): 402(q)(3)(A) does not
            # apply, so the spouse benefit keeps its 402(q)(1) reduction
            # and is paid in excess of the RIB (with any credits, RS
            # 00615.694A).
            return reduced, max(Fraction(0), reduced - row.own_mba)
        # 402(q)(3)(B)/(C), method C (POMS RS 00615.250): the spouse
        # benefit is reduced by the own benefit's 402(q) reduction plus the
        # spousal reduction of the excess over the own PIA.
        excess = max(Fraction(0), rate - own.pia)
        reduced_excess = spouse_age_reduced(
            excess, beneficiary.reduction_months, params
        )
        age_adjusted = max(
            Fraction(0),
            rate - (own.pia - row.own_base) - (excess - reduced_excess),
        )
        # 402(k)(3)(A) subtracts the own benefit with any delayed credits
        # (RS 00615.694: combined amount without credits, less the RIB
        # with credits).
        return age_adjusted, max(Fraction(0), age_adjusted - row.own_mba)
    if beneficiary.role in _WIDOW_ROLES:
        reduced = rate
        if beneficiary.reduction_months:
            reduced = survivor_age_reduced(
                rate,
                beneficiary.reduction_months,
                beneficiary.reduction_period_months,
                params,
            )
        if state.rib_lim_benefit is not None:
            rates = statutory_rates(params)
            limit = max(
                state.rib_lim_benefit,
                floor_dime(rates.rib_lim_share * state.pia),
            )
            reduced = min(reduced, limit)
    else:
        reduced = rate
    if own is None:
        return reduced, reduced
    return reduced, max(Fraction(0), reduced - row.own_mba)


def family_benefits(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
) -> FamilyBenefits:
    """Gross monthly benefits on one record for one payment month.

    Order (see the module docstring): OB, family-maximum reduction,
    RS 00615.768 redistribution, 402(q) age reduction and RIB-LIM,
    402(k)(3)(A) dual entitlement, 215(g) whole dollars.
    """
    if not isinstance(state, RecordState):
        raise TypeError("state must be a RecordState")
    if not isinstance(payment_month, YearMonth):
        raise TypeError("payment_month must be a YearMonth")
    rates = statutory_rates(params)
    _raise_record_conditions(state.conditions)
    if payment_month.as_tuple() < FIRST_SUPPORTED_PAYMENT_MONTH:
        raise FamilyConfigurationUnsupported(
            UnsupportedReason.PAYMENT_MONTH_BEFORE_1983,
            "months before 1983 are outside the post-May-1982 rounding "
            "rules this layer implements",
        )
    ids = [b.beneficiary_id for b in beneficiaries]
    if len(set(ids)) != len(ids):
        raise InvalidFamilyInput("beneficiary_id values must be unique")
    for beneficiary in beneficiaries:
        if not isinstance(beneficiary, Beneficiary):
            raise TypeError("beneficiaries must be Beneficiary objects")
        _validate_beneficiary(beneficiary, state.kind)

    life_case = state.kind is not FamilyKind.SURVIVOR
    worker_benefit = None
    if state.kind is FamilyKind.RETIREMENT:
        worker_benefit = own_monthly_benefit(state.worker, params)[1]
    elif state.kind is FamilyKind.DISABILITY:
        worker_benefit = state.pia

    rows: list[_Row] = []
    for beneficiary in beneficiaries:
        own_base = own_mba = None
        if beneficiary.own_benefit is not None:
            own_base, own_mba = own_monthly_benefit(
                beneficiary.own_benefit, params
            )
        entitled, note = _is_entitled(beneficiary, state.pia, own_mba)
        ob = original_benefit(
            beneficiary.role,
            state.kind,
            state.pia,
            beneficiary.original_benefit_basis,
        )
        rows.append(
            _Row(
                beneficiary=beneficiary,
                entitled=entitled,
                subject=entitled and beneficiary.role not in _OUTSIDE_MAXIMUM,
                ob=ob if entitled else Fraction(0),
                own_base=own_base,
                own_mba=own_mba,
                note=note,
            )
        )

    available = state.family_maximum - (state.pia if life_case else 0)
    subject = [row for row in rows if row.subject]
    total_ob = sum((row.ob for row in subject), Fraction(0))
    binding = total_ob > available
    for row, share in zip(
        subject, _proportional(subject, available), strict=True
    ):
        row.standard = row.rate = row.counted = share
    for row in rows:
        if row.entitled and not row.subject:
            row.standard = row.rate = row.ob

    dual = [row for row in subject if row.dual]
    nondual = [row for row in subject if not row.dual]
    redistributed = bool(binding and dual and nondual)
    if redistributed:
        if payment_month.as_tuple() < PARISI_FIRST_PAYMENT_MONTH:
            raise FamilyConfigurationUnsupported(
                UnsupportedReason.PARISI_BEFORE_OCTOBER_1999,
                "a binding maximum with dual entitlement before 10/99 used "
                "the pre-Parisi rule (POMS RS 00615.768D), not implemented",
            )
        for row in dual:
            row.counted = _parisi_counted(row, state)
        pool = available - sum((row.counted for row in dual), Fraction(0))
        for row, share in zip(
            nondual, _proportional(nondual, pool), strict=True
        ):
            row.rate = row.counted = share

    results = []
    for row in rows:
        beneficiary = row.beneficiary
        if row.entitled:
            age_adjusted, payable = _reduce_and_offset(row, state, params)
        else:
            age_adjusted = payable = Fraction(0)
        results.append(
            BeneficiaryBenefit(
                beneficiary_id=beneficiary.beneficiary_id,
                role=beneficiary.role,
                entitled=row.entitled,
                subject_to_family_maximum=row.subject,
                original_benefit=row.ob,
                standard_rate=row.standard,
                family_maximum_rate=row.rate,
                counted_against_maximum=(
                    row.counted if row.subject else Fraction(0)
                ),
                age_adjusted_rate=age_adjusted,
                auxiliary_payable=payable,
                own_benefit=row.own_mba,
                whole_dollar_auxiliary=whole_dollars(payable),
                whole_dollar_own=(
                    None if row.own_mba is None else whole_dollars(row.own_mba)
                ),
                note=row.note,
            )
        )

    subject_total = (state.pia if life_case else Fraction(0)) + sum(
        (row.counted for row in subject), Fraction(0)
    )
    if subject_total > state.family_maximum:
        raise AssertionError(
            "family-maximum invariant violated: "
            f"{subject_total} > {state.family_maximum}"
        )
    record_total = (worker_benefit or Fraction(0)) + sum(
        (row.auxiliary_payable for row in results), Fraction(0)
    )
    record_whole = (
        0 if worker_benefit is None else whole_dollars(worker_benefit)
    ) + sum(row.whole_dollar_auxiliary for row in results)
    return FamilyBenefits(
        kind=state.kind,
        payment_month=payment_month,
        pia=state.pia,
        family_maximum=state.family_maximum,
        available_for_auxiliaries=available,
        total_original_benefits=total_ob,
        family_maximum_binding=binding,
        redistribution_applied=redistributed,
        worker_benefit=worker_benefit,
        whole_dollar_worker=(
            None if worker_benefit is None else whole_dollars(worker_benefit)
        ),
        beneficiaries=tuple(results),
        record_total=record_total,
        record_total_whole_dollars=record_whole,
        subject_total=subject_total,
        state_source=state.source,
        pe_us_revision=rates.pe_us_revision,
    )


# ---------------------------------------------------------------------------
# Denominators: unsupported rows stay in, and block totals that need them
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FamilyOutcome:
    """One record-month: its benefits, or why it is unsupported."""

    key: str
    weight: Fraction
    benefits: FamilyBenefits | None
    unsupported: FamilyConfigurationUnsupported | None

    def __post_init__(self):
        if (self.benefits is None) == (self.unsupported is None):
            raise ValueError("Exactly one of benefits/unsupported is set")
        weight = _exact(self.weight, "weight")
        if weight < 0:
            raise ValueError("weight must be nonnegative")
        object.__setattr__(self, "weight", weight)

    @property
    def supported(self) -> bool:
        return self.benefits is not None


def evaluate_family(
    key: str, weight: object, compute: Callable[[], FamilyBenefits]
) -> FamilyOutcome:
    """Run ``compute``; keep an unsupported configuration as an outcome.

    Only :class:`FamilyConfigurationUnsupported` is caught. Invalid inputs
    and bugs still raise, so an error never masquerades as a coverage gap.
    """
    try:
        benefits = compute()
    except FamilyConfigurationUnsupported as error:
        return FamilyOutcome(key, weight, None, error)
    if not isinstance(benefits, FamilyBenefits):
        raise TypeError("compute must return FamilyBenefits")
    return FamilyOutcome(key, weight, benefits, None)


@dataclass(frozen=True)
class FamilyDenominator:
    """Counts over every outcome, supported or not."""

    rows: int
    weight: Fraction
    supported_rows: int
    supported_weight: Fraction
    unsupported_rows: int
    unsupported_weight: Fraction
    unsupported_by_reason: Mapping[UnsupportedReason, tuple[int, Fraction]]

    @property
    def supported_weight_share(self) -> Fraction:
        if self.weight == 0:
            raise ZeroDivisionError("No weight in the denominator")
        return self.supported_weight / self.weight


def count_family_outcomes(
    outcomes: Iterable[FamilyOutcome],
) -> FamilyDenominator:
    """Tabulate outcomes; unsupported rows are counted, never dropped."""
    outcomes = tuple(outcomes)
    keys = Counter(outcome.key for outcome in outcomes)
    duplicates = sorted(key for key, count in keys.items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate outcome keys: {duplicates[:5]}")
    by_reason: dict[UnsupportedReason, tuple[int, Fraction]] = {}
    for outcome in outcomes:
        if outcome.unsupported is not None:
            count, weight = by_reason.get(
                outcome.unsupported.reason, (0, Fraction(0))
            )
            by_reason[outcome.unsupported.reason] = (
                count + 1,
                weight + outcome.weight,
            )
    supported = [outcome for outcome in outcomes if outcome.supported]
    unsupported = [outcome for outcome in outcomes if not outcome.supported]
    return FamilyDenominator(
        rows=len(outcomes),
        weight=sum((o.weight for o in outcomes), Fraction(0)),
        supported_rows=len(supported),
        supported_weight=sum((o.weight for o in supported), Fraction(0)),
        unsupported_rows=len(unsupported),
        unsupported_weight=sum((o.weight for o in unsupported), Fraction(0)),
        unsupported_by_reason=MappingProxyType(dict(by_reason)),
    )


def _require_all_supported(outcomes: Sequence[FamilyOutcome]) -> None:
    blocked = [o for o in outcomes if not o.supported]
    if blocked:
        denominator = count_family_outcomes(outcomes)
        reasons = ", ".join(
            f"{reason.value}={count}"
            for reason, (count, _) in sorted(
                denominator.unsupported_by_reason.items(),
                key=lambda item: item[0].value,
            )
        )
        raise FamilyTargetBlocked(
            f"{len(blocked)} of {len(outcomes)} rows are "
            f"FAMILY_CONFIG_UNSUPPORTED ({reasons}); the total would drop "
            "them from its denominator"
        )


def weighted_record_total(outcomes: Iterable[FamilyOutcome]) -> Fraction:
    """Weighted sum of record totals; blocked if any row is unsupported."""
    outcomes = tuple(outcomes)
    _require_all_supported(outcomes)
    return sum(
        (o.weight * o.benefits.record_total for o in outcomes), Fraction(0)
    )


def weighted_mean_record_total(outcomes: Iterable[FamilyOutcome]) -> Fraction:
    """Weighted mean over *all* rows; blocked if any row is unsupported."""
    outcomes = tuple(outcomes)
    denominator = count_family_outcomes(outcomes)
    _require_all_supported(outcomes)
    if denominator.weight == 0:
        raise ZeroDivisionError("No weight in the denominator")
    return weighted_record_total(outcomes) / denominator.weight
