"""Independent, exact-decimal Social Security inclusion tiers under §86.

The inputs are annual tax-unit benefits and modified adjusted gross income
as defined by 26 U.S.C. 86(b)(2), before including Social Security benefits.
Benefits must already reflect the adjustments in §86(d). The optional
lump-sum election in §86(e) is outside this annual-tier calculation.

Source: https://www.law.cornell.edu/uscode/text/26/86, §86(a)–(c), read
24 October 2026. This module does not call PolicyEngine-US.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

Amount = Decimal | int | float | str

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


def _finite_decimal(value: Amount, name: str) -> Decimal:
    try:
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
    # Reserve enough significant digits to align both inputs and multiply
    # by the two statutory percentages without inheriting caller rounding.
    amounts = (benefit_amount, modified_agi, adjusted_base)
    highest_place = max(amount.adjusted() for amount in amounts)
    lowest_place = min(amount.as_tuple().exponent for amount in amounts)
    with localcontext() as context:
        context.prec = max(28, highest_place - lowest_place + 5)
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
