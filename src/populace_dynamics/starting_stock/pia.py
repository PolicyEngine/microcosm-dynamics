"""The primary insurance amount (PIA) behind a benefit in payment.

A retired worker's monthly benefit is the PIA at eligibility, raised by
each cost-of-living adjustment (COLA) since then, times the factor for
the claim age. A disabled worker's benefit carries no claim-age factor.
This module holds that forward rule and its inverse, as pure functions
of plain values.

COLA timing. ``cola_rates`` maps a year to the adjustment determined in
December of that year, as a fraction (``0.028`` for 2.8 percent). The
increase of the year of eligibility and every later one applies to a
PIA first computed in that year (42 USC 415(i)(2)(A)(iii), as cited in
``bridge/policyengine_us.py``'s ``carry_pia_forward``). A December
adjustment is first paid in the next year, so a benefit paid in
``payment_year`` carries the adjustments of ``eligibility_year`` through
``payment_year - 1``.

Statutory rounding, where the forward rule applies it:

* the PIA itself is a multiple of ten cents (42 USC 415(g), as cited in
  ``ss/benefits.py``);
* after each adjustment the PIA is rounded down to the next lower
  multiple of ten cents (42 USC 415(i)(2)(A)(ii), as cited in
  ``carry_pia_forward``);
* the claim factor then applies (42 USC 402(q) and 402(w), through
  :func:`populace_dynamics.claiming.benefit_factor`);
* the monthly benefit is rounded down to the dollar. None of the files
  this package was built from cites a provision for that step, so this
  module cites none.

Both floors use the oracle's guard against binary representation error,
the ``+ 1e-9`` of ``ss.benefits.pia``: a product that lies a hair under
a whole dime (or dollar) only because of floating point is not dropped
a whole step. The oracle applies that guard to the dime; this module
carries the same guard to the dollar step. The guard is ``1e-10``
dollars at the dime, and float error in one product stays under it
while the product is below about $300,000 a month, far above any
benefit. Past that size a product that lies exactly on a whole dime can
floor one dime low.
"""

from __future__ import annotations

import math
import numbers
import operator
from collections.abc import Mapping

from populace_dynamics import claiming
from populace_dynamics.ss.params import SSAParameters

__all__ = [
    "cola_factor",
    "benefit_from_pia",
    "infer_pia",
    "rounding_bound",
    "retired_worker_claim_factor",
    "disabled_worker_claim_factor",
]

#: The oracle's guard in ``ss.benefits.pia``: ``floor(x * 10 + 1e-9)``.
_FLOOR_GUARD = 1e-9
#: Largest drop one dime floor can make, in dollars.
_DIME = 0.1
#: Largest drop the dollar floor can make, in dollars.
_DOLLAR = 1.0


def _year(label: str, value: object) -> int:
    """An integer year, refusing booleans and non-integers."""
    if isinstance(value, bool):
        raise TypeError(f"{label} must be an integer year, not a bool")
    try:
        return operator.index(value)
    except TypeError as error:
        raise TypeError(f"{label} must be an integer year") from error


def _real(label: str, value: object) -> float:
    """A finite real number, refusing booleans and strings."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{label} must be a real number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite, got {out!r}")
    return out


def _positive_factor(label: str, value: object) -> float:
    """A finite factor above zero."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError(f"{label} must be positive, got {out!r}")
    return out


def _nonnegative_amount(label: str, value: object) -> float:
    """A finite amount of zero or more."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError(f"{label} must not be negative, got {out!r}")
    return out


def _rates(
    cola_rates: Mapping[int, float],
    eligibility_year: object,
    payment_year: object,
) -> list[float]:
    """The adjustments a benefit in ``payment_year`` carries, in order."""
    first = _year("eligibility_year", eligibility_year)
    last = _year("payment_year", payment_year)
    if last < first:
        raise ValueError(
            f"payment_year {last} is before eligibility_year {first}"
        )
    out = []
    for year in range(first, last):
        if year not in cola_rates:
            raise KeyError(f"no COLA for year {year}")
        rate = cola_rates[year]
        if isinstance(rate, bool) or not isinstance(rate, numbers.Real):
            raise TypeError(f"COLA for {year} must be a real number")
        rate = float(rate)
        if not math.isfinite(rate):
            raise ValueError(f"COLA for {year} must be finite, got {rate!r}")
        if rate <= -1.0:
            raise ValueError(
                f"COLA for {year} is {rate!r}; one plus it must be positive"
            )
        out.append(rate)
    return out


def _floor_to_dime(amount: float) -> float:
    """Round down to the next lower multiple of ten cents.

    The expression is the oracle's (``ss.benefits.pia``), guard included.
    """
    return math.floor(amount * 10.0 + _FLOOR_GUARD) / 10.0


def _floor_to_dollar(amount: float) -> float:
    """Round down to the dollar, with the oracle's guard."""
    return float(math.floor(amount + _FLOOR_GUARD))


def cola_factor(
    cola_rates: Mapping[int, float],
    eligibility_year: int,
    payment_year: int,
) -> float:
    """The product of one plus each COLA a benefit in ``payment_year`` carries.

    The factor multiplies one plus each rate from ``eligibility_year``
    through ``payment_year - 1``; it is 1 when the two years are equal.

    Raises:
        KeyError: a year in that range is missing from ``cola_rates``.
        ValueError: a rate is not finite, a rate is -1 or less (so one
            plus it is not positive), or ``payment_year`` is before
            ``eligibility_year``.
        TypeError: a year is not an integer, or a rate is not a number.
    """
    factor = 1.0
    for rate in _rates(cola_rates, eligibility_year, payment_year):
        factor *= 1.0 + rate
    return factor


def benefit_from_pia(
    pia: float,
    *,
    cola_rates: Mapping[int, float],
    eligibility_year: int,
    payment_year: int,
    claim_factor: float,
    statutory_rounding: bool,
) -> float:
    """The monthly benefit in ``payment_year`` for a PIA at eligibility.

    Unrounded, the benefit is ``pia * cola_factor * claim_factor``. With
    ``statutory_rounding``, the PIA is rounded down to the dime after
    each adjustment, the claim factor applies, and the monthly benefit
    is rounded down to the dollar (see the module docstring for the
    provisions). The PIA passed in is taken as given: a PIA computed
    under 415(g) is already a whole number of dimes, and an inferred PIA
    is not rounded before the first adjustment. With no adjustment
    (``payment_year == eligibility_year``) no dime floor applies.

    Raises:
        ValueError: ``pia`` is negative or not finite, or
            ``claim_factor`` is zero, negative or not finite, and every
            error :func:`cola_factor` raises.
    """
    amount = _nonnegative_amount("pia", pia)
    claim = _positive_factor("claim_factor", claim_factor)
    rates = _rates(cola_rates, eligibility_year, payment_year)
    if not statutory_rounding:
        return amount * _total_factor(rates, claim)
    for rate in rates:
        amount = _floor_to_dime(amount * (1.0 + rate))
    return _floor_to_dollar(amount * claim)


def _total_factor(rates: list[float], claim: float) -> float:
    """The COLA factor times the claim factor, shared by both directions."""
    factor = 1.0
    for rate in rates:
        factor *= 1.0 + rate
    return factor * claim


def infer_pia(
    monthly_benefit: float,
    *,
    cola_rates: Mapping[int, float],
    eligibility_year: int,
    payment_year: int,
    claim_factor: float,
) -> float:
    """The PIA at eligibility behind a monthly benefit, unrounded.

    It is the benefit over the product of the COLA factor and the claim
    factor: the exact inverse of :func:`benefit_from_pia` without
    statutory rounding. A zero benefit returns zero.

    Raises:
        ValueError: the benefit is negative or not finite; the claim
            factor, or its product with the COLA factor, is zero,
            negative or not finite; and every error :func:`cola_factor`
            raises.
    """
    benefit = _nonnegative_amount("monthly_benefit", monthly_benefit)
    claim = _positive_factor("claim_factor", claim_factor)
    rates = _rates(cola_rates, eligibility_year, payment_year)
    factor = _total_factor(rates, claim)
    if not math.isfinite(factor) or factor <= 0.0:
        raise ValueError(
            f"the combined factor must be positive and finite, got {factor!r}"
        )
    if benefit == 0.0:
        return 0.0
    return benefit / factor


def rounding_bound(
    *,
    cola_rates: Mapping[int, float],
    eligibility_year: int,
    payment_year: int,
    claim_factor: float,
) -> float:
    """The largest gap statutory rounding can open, in dollars a month.

    The gap is between a benefit ``b`` and ``benefit_from_pia(infer_pia(b),
    statutory_rounding=True)`` under the same COLA path and claim factor.

    Derivation. Write ``r_1, ..., r_n`` for the adjustments in order,
    ``g_k = 1 + r_k`` and ``c`` for the claim factor. ``infer_pia``
    returns ``p = b / (g_1 ... g_n c)``, so the unrounded forward rule
    gives back exactly ``b``. The rounded rule computes ``D_0 = p`` and
    ``D_k = floor_dime(D_{k-1} g_k)``, then ``floor_dollar(c D_n)``.

    1. Each adjustment can drop the PIA by less than ten cents:
       ``D_{k-1} g_k - 0.1 < D_k <= D_{k-1} g_k``.
    2. Later factors scale that drop. A drop at step ``k`` is carried
       through ``g_{k+1} ... g_n`` and then ``c``, so
       ``c D_n > b - 0.1 c S_n``, where
       ``S_n = sum over k of g_{k+1} ... g_n`` (the empty product is 1).
       Equivalently ``S_0 = 0`` and ``S_k = S_{k-1} g_k + 1``.
    3. The last step can drop less than one dollar, so the rounded
       benefit exceeds ``b - 0.1 c S_n - 1``.

    No step rounds up, so the rounded benefit never exceeds ``b``
    (the floors' ``1e-9`` guard moves a product by far less than the
    next whole dollar). The gap is therefore less than
    ``0.1 c S_n + 1``, which this function returns. With no adjustment
    the bound is 1. Its error paths are those of :func:`infer_pia`'s
    factors.
    """
    claim = _positive_factor("claim_factor", claim_factor)
    scale = 0.0
    for rate in _rates(cola_rates, eligibility_year, payment_year):
        scale = scale * (1.0 + rate) + 1.0
    return _DIME * claim * scale + _DOLLAR


def retired_worker_claim_factor(
    claim_age_months: int, birth_year: int, params: SSAParameters
) -> float:
    """The benefit-to-PIA factor for a retired worker's claim age.

    A thin wrapper on :func:`populace_dynamics.claiming.benefit_factor`
    (402(q) before full retirement age, 402(w) after, capped at 70), so
    callers of this package import one module.
    """
    return claiming.benefit_factor(claim_age_months, birth_year, params)


def disabled_worker_claim_factor() -> float:
    """A disabled worker's benefit carries no claim-age factor: 1."""
    return 1.0
