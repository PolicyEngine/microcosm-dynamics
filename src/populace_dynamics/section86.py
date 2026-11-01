"""Independent, exact-decimal Social Security inclusion tiers under §86.

The inputs are annual tax-unit benefits and modified adjusted gross income
as defined by 26 U.S.C. 86(b)(2), before including Social Security benefits.
Benefits must already reflect the adjustments in §86(d). The optional
lump-sum election in §86(e) is outside this annual-tier calculation.

Source: https://www.law.cornell.edu/uscode/text/26/86, §86(a)–(c), read
24 October 2026. This module does not call PolicyEngine-US. Its arithmetic
runs in a fixed decimal context of its own, so the caller's decimal context
changes no result. ``exact_decimal_context`` states the validated domain.
"""

from dataclasses import dataclass
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    MIN_ETINY,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    localcontext,
)

Amount = Decimal | int | float | str

# The validated domain's three limits; exact_decimal_context explains them.
MAX_DIGIT_SPAN = 100_000
MAX_PLACE = MAX_EMAX - 1
MIN_PLACE = MIN_ETINY + 3

_ZERO = Decimal("0")
_HALF = Decimal("0.5")
_EIGHTY_FIVE_PERCENT = Decimal("0.85")
_SUPPORTED_STATUSES = ("SINGLE", "JOINT", "HEAD_OF_HOUSEHOLD", "SEPARATE")


@dataclass(frozen=True)
class Section86Inclusions:
    """Amounts before any rounding to return-line dollars or cents.

    ``pre_1993`` applies §86(a)(1) without the paragraph (2) override;
    ``current`` applies both paragraphs. ``combined_income`` is the
    §86(b)(1)(A) sum, modified AGI plus half of benefits. The first amount
    is not the limited paragraph (1) contribution inside §86(a)(2)(A)(ii).
    """

    pre_1993: Decimal
    current: Decimal
    combined_income: Decimal


def exact_decimal_context(*amounts: Decimal) -> Context:
    """Return a fresh decimal context that ignores the caller's own.

    Validated domain. The ``amounts`` are finite. A zero holds no digits,
    so it may sit at any exponent and counts toward no limit. Among the
    nonzero amounts, the highest leading-digit place (``adjusted()``) is
    at most ``MAX_PLACE``, ``decimal.MAX_EMAX - 1``; the lowest place (the
    exponent) is at least ``MIN_PLACE``, ``decimal.MIN_ETINY + 3``; and
    the span from lowest to highest, both places counted, is at most
    ``MAX_DIGIT_SPAN`` places. The span sets the storage a call needs; the
    absolute exponent doesn't.

    Inside the domain, F1's sums and differences of the amounts and its
    products of them by 0.5 and 0.85 are exact: they reach at most one
    place above the highest place and three below the lowest, and this
    context holds every place between. Computed with the operands that
    ``exact_decimal_operands`` returns, no such call raises ``Inexact``,
    ``Overflow`` or ``MemoryError``. Outside the domain, this raises a
    ``ValueError`` that names the limit, before any arithmetic, leaving
    the caller's context as it was.

    The precision is never below 28. It covers every place from three
    below the lowest nonzero place to one above the highest, and it is
    large enough that the smallest exponent, ``Etiny()``, is at least
    three places below the lowest. The exponent limits are the widest the
    module allows, so no caller limit can overflow an ordinary amount.
    Rounding is half-even, and ``Inexact`` is trapped with the default
    traps, so a result that would need rounding raises instead.
    """
    precision = 28
    if not all(amount.is_finite() for amount in amounts):
        raise ValueError("Exact decimal arithmetic needs finite amounts")
    nonzero = [amount for amount in amounts if not amount.is_zero()]
    if nonzero:
        highest_place = max(amount.adjusted() for amount in nonzero)
        lowest_place = min(amount.as_tuple().exponent for amount in nonzero)
        _check_places(highest_place, lowest_place)
        precision = max(
            precision,
            highest_place - lowest_place + 5,
            # Etiny = MIN_EMIN - precision + 1 <= lowest_place - 3.
            MIN_EMIN - lowest_place + 4,
        )
    return Context(
        prec=precision,
        rounding=ROUND_HALF_EVEN,
        Emax=MAX_EMAX,
        Emin=MIN_EMIN,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow, Inexact],
    )


def _check_places(highest_place: int, lowest_place: int) -> None:
    # Refuse by name before any context or arithmetic exists.
    if highest_place > MAX_PLACE:
        raise ValueError(
            "Exact decimal arithmetic needs every nonzero amount's leading "
            f"digit at or below place MAX_PLACE = {MAX_PLACE} "
            "(decimal.MAX_EMAX - 1), so that a sum cannot overflow; an "
            f"amount reaches place {highest_place}"
        )
    if lowest_place < MIN_PLACE:
        raise ValueError(
            "Exact decimal arithmetic needs every nonzero amount's lowest "
            f"digit at or above place MIN_PLACE = {MIN_PLACE} "
            "(decimal.MIN_ETINY + 3), so that a statutory product stays "
            f"representable; an amount reaches place {lowest_place}"
        )
    span = highest_place - lowest_place + 1
    if span > MAX_DIGIT_SPAN:
        raise ValueError(
            "Exact decimal arithmetic supports nonzero amounts spanning at "
            f"most MAX_DIGIT_SPAN = {MAX_DIGIT_SPAN:,} digit places; these "
            f"span {span:,}, from place {lowest_place} to {highest_place}"
        )


def exact_decimal_operands(
    *amounts: Decimal,
) -> tuple[Context, tuple[Decimal, ...]]:
    """Return ``exact_decimal_context(*amounts)`` and the amounts to use.

    A zero below the context's smallest exponent, ``Etiny()``, moves up to
    it with its sign; every other amount comes back unchanged. No result
    in the context can sit below ``Etiny()``, so the move changes none.
    Without it, when the lowest nonzero place has raised the precision, an
    addend aligned with such a zero takes a digit for every place between.
    """
    context = exact_decimal_context(*amounts)
    etiny = context.Etiny()
    return context, tuple(
        (
            Decimal((amount.as_tuple().sign, (0,), etiny))
            if amount.is_zero() and amount.as_tuple().exponent < etiny
            else amount
        )
        for amount in amounts
    )


def _finite_decimal(value: Amount, name: str) -> Decimal:
    # Converting in a fixed context, malformed input always raises here and
    # never sets a flag in the caller's context.
    try:
        with localcontext(exact_decimal_context()):
            amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not amount.is_finite():
        raise ValueError(f"{name} must be a finite number")
    return amount


def section86_inclusions(
    benefits: Amount,
    modified_adjusted_gross_income: Amount,
    filing_status: str,
    *,
    lived_apart_all_year: bool | None = None,
) -> Section86Inclusions:
    """Return §86(a)(1) and current-law taxable benefit amounts.

    ``SINGLE`` and ``HEAD_OF_HOUSEHOLD`` use the general $25,000/$34,000
    thresholds; ``JOINT`` uses $32,000/$44,000 (§86(c)). ``SEPARATE`` is
    supported only with ``lived_apart_all_year=True``. Married separate
    filers who lived together at any time (§86(c)(1)(C)(ii)) are refused.
    Other filing statuses are refused by name.

    ``modified_adjusted_gross_income`` is the caller's §86(b)(2) amount:
    exclude the Social Security inclusion, disregard that subsection's
    named exclusions/deductions, and add tax-exempt interest. Negative
    modified AGI is allowed. Benefits must be nonnegative. String-based
    decimal conversion preserves the stated decimal value of float inputs.
    """
    if filing_status not in _SUPPORTED_STATUSES:
        raise ValueError(f"Unsupported filing status: {filing_status!r}")
    if filing_status == "SEPARATE" and lived_apart_all_year is not True:
        if lived_apart_all_year is False:
            raise ValueError(
                "SEPARATE filers who lived together at any time are "
                "unsupported (§86(c)(1)(C)(ii))"
            )
        raise ValueError("SEPARATE requires lived_apart_all_year=True")

    benefit_amount = _finite_decimal(benefits, "benefits")
    modified_agi = _finite_decimal(
        modified_adjusted_gross_income, "modified_adjusted_gross_income"
    )
    if benefit_amount < _ZERO:
        raise ValueError("benefits must be nonnegative")

    base, adjusted_base = (
        (Decimal("32000"), Decimal("44000"))
        if filing_status == "JOINT"
        else (Decimal("25000"), Decimal("34000"))
    )
    # Every intermediate is exact in this context, whatever the caller's:
    # the products by 0.5 and 0.85 reach at most three places below the
    # lowest input place, and combined income and the upper-tier sum at
    # most one place above the highest (the adjusted base included).
    context, (benefit_amount, modified_agi, adjusted_base) = (
        exact_decimal_operands(benefit_amount, modified_agi, adjusted_base)
    )
    with localcontext(context):
        combined_income = modified_agi + _HALF * benefit_amount
        # §86(a)(1), applied without the paragraph (2) override.
        pre_1993 = min(
            _HALF * benefit_amount,
            _HALF * max(_ZERO, combined_income - base),
        )
        current = pre_1993
        if combined_income > adjusted_base:
            # §86(a)(2)(A)(ii) retains the lesser of paragraph (1) and
            # half the distance between the two statutory thresholds.
            current = min(
                _EIGHTY_FIVE_PERCENT * benefit_amount,
                _EIGHTY_FIVE_PERCENT * (combined_income - adjusted_base)
                + min(pre_1993, _HALF * (adjusted_base - base)),
            )
    return Section86Inclusions(pre_1993, current, combined_income)
