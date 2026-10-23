"""Private quarter-of-coverage arithmetic for the statutory reference.

Verification class: statutory conformance on invented and published cases.
These helpers admit no population, behavioral, or forecast claim. The
public insured-status boundary validates and owns its inputs once; helpers
consume those normalized primitives and do not establish public provenance.

Authority: Act 213, 20 CFR 404.140-.146, and POMS RS 00301.200-.350.
Integer quarter identifiers are ``4 * year + quarter - 1``. Flexible
credits are assigned separately for each statutory window, as RS 00301.230
requires, rather than silently fixing all annual credits to year-end.
"""

from datetime import date
from fractions import Fraction
from itertools import combinations
from types import MappingProxyType

__all__ = []

# POMS RS 00301.250 (1978-2026) and captured OACT QC history (2027).
QC_AMOUNTS = MappingProxyType(
    dict(
        zip(
            range(1978, 2028),
            (
                250,
                260,
                290,
                310,
                340,
                370,
                390,
                410,
                440,
                460,
                470,
                500,
                520,
                540,
                570,
                590,
                620,
                630,
                640,
                670,
                700,
                740,
                780,
                830,
                870,
                890,
                900,
                920,
                970,
                1000,
                1050,
                1090,
                1120,
                1120,
                1130,
                1160,
                1200,
                1220,
                1260,
                1300,
                1320,
                1360,
                1410,
                1470,
                1510,
                1640,
                1730,
                1810,
                1890,
                1970,
            ),
            strict=True,
        )
    )
)


class _UnsupportedQC(Exception):
    """Private indication translated to the public layer's own refusal."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _quarter_id(year: int, quarter: int) -> int:
    return year * 4 + quarter - 1


def _year_quarters(year: int) -> tuple[int, ...]:
    return tuple(range(year * 4, year * 4 + 4))


def _date_quarter(value: date) -> int:
    return _quarter_id(value.year, (value.month - 1) // 3 + 1)


def _qc_amount_from_nawi(nawi: Fraction, prior_amount: int) -> int:
    """Act 213(d)(2): exact index, nearest $10 with $5 ties upward."""
    indexed = Fraction(250) * nawi / Fraction("9226.48")
    rounded = ((indexed + 5) // 10) * 10
    return max(prior_amount, rounded)


def _post1977_qc_count(
    year: int, wages: Fraction, self_employment: Fraction
) -> int:
    """Act 213(a)(2)(A)(ii); earnings are already calendar-year credited."""
    return min(4, (wages + self_employment) // QC_AMOUNTS[year])


def _annual_wage_limit(year: int) -> int:
    """POMS RS 00301.345B.1's pre-1978 maximum taxable wage chart."""
    for last, amount in (
        (1950, 3000),
        (1954, 3600),
        (1958, 4200),
        (1965, 4800),
        (1967, 6600),
        (1971, 7800),
        (1972, 9000),
        (1973, 10800),
        (1974, 13200),
        (1975, 14100),
        (1976, 15300),
        (1977, 16500),
    ):
        if year <= last:
            return amount
    raise _UnsupportedQC("pre1978_wage_limit_year_unsupported")


def _pre1978_qc_credits(
    year: int,
    quarterly_wages: tuple[Fraction, ...],
    self_employment: Fraction,
    agricultural_wages: Fraction,
) -> tuple[tuple[int, ...], int]:
    """Fixed wage/SE quarters and additional flexible agricultural QCs.

    Quarterly wages are covered nonagricultural wages (also covered
    agricultural wages in 1951-54). Calendar-year SEI >= $400 covers four
    quarters. Separate annual agricultural wages are supported for 1955-77;
    their floor-$100 QCs occupy quarters not otherwise credited. Maximum
    taxable wages, or combined wages and SEI, give four gift QCs. Exclusions
    are applied afterwards and cannot turn an excluded fixed QC flexible.
    """
    if year == 1937 and (
        any(quarterly_wages) or self_employment or agricultural_wages
    ):
        # Act 213(b) half-year allocation has an age-65 exception. The
        # annual interface can consume explicitly credited quarter flags,
        # but cannot infer this historical allocation from wages alone.
        raise _UnsupportedQC("1937_earnings_allocation_unsupported")
    if year < 1955 and agricultural_wages:
        raise _UnsupportedQC("pre1955_agricultural_allocation_unsupported")
    if year < 1951 and self_employment:
        raise _UnsupportedQC("pre1951_self_employment_unsupported")
    quarters = _year_quarters(year)
    wages = sum(quarterly_wages) + agricultural_wages
    if (
        wages + self_employment >= _annual_wage_limit(year)
        or self_employment >= 400
    ):
        return quarters, 0
    fixed = tuple(
        quarter
        for quarter, wages in zip(quarters, quarterly_wages, strict=True)
        if wages >= 50
    )
    flexible = min(4 - len(fixed), agricultural_wages // 100)
    return fixed, flexible


def _allowed_quarters(
    year: int,
    *,
    through_quarter: int,
    death_quarter: int | None = None,
    coverage_end_quarter: int | None = None,
    disability_periods: tuple[tuple[int, int], ...] = (),
) -> tuple[int, ...]:
    """404.146: begun, not after death/exit, outside disability interiors.

    Disability endpoints themselves remain eligible. A caller that elects
    not to take a period into consideration under 404.146(d)(2) omits it.
    Coverage-end is the explicit entrant/emigrant contract, not an additional
    statutory disability exclusion.
    """
    last = min(
        value
        for value in (through_quarter, death_quarter, coverage_end_quarter)
        if value is not None
    )
    return tuple(
        quarter
        for quarter in _year_quarters(year)
        if quarter <= last
        and not any(start < quarter < end for start, end in disability_periods)
    )


def _assignment_candidates(
    fixed: tuple[int, ...],
    flexible_count: int,
    allowed: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    """All feasible assignments, after exclusions and without duplicates."""
    permitted = frozenset(allowed)
    retained = frozenset(fixed) & permitted
    vacant = tuple(sorted(permitted - retained))
    count = min(flexible_count, len(vacant))
    return tuple(
        tuple(sorted((*retained, *choice)))
        for choice in combinations(vacant, count)
    )


def _assign_qcs(
    fixed: tuple[int, ...],
    flexible_count: int,
    allowed: tuple[int, ...],
    window: tuple[int, ...] = (),
) -> tuple[int, ...]:
    """Maximize this window; otherwise keep ordinary agricultural order.

    Act 213(a)(2)(B)(iv) assigns pre-1978 agricultural credits to the last
    uncredited quarters, with reassignment to meet the stated tests. The
    post-1977 rule has no ordinary latest-quarter preference, so its ties
    use the earliest assignment deterministically.
    """
    target = frozenset(window)
    latest = bool(allowed) and allowed[0] // 4 < 1978
    return min(
        _assignment_candidates(fixed, flexible_count, allowed),
        key=lambda candidate: (
            -len(target.intersection(candidate)),
            tuple(-q for q in reversed(candidate)) if latest else candidate,
        ),
    )


def _allocate_sei_pre1978(
    start: date, end: date, self_employment: Fraction
) -> tuple[tuple[int, Fraction], ...]:
    """404.142 / RS 00301.340: equal shares in last at most four quarters.

    This is allocation arithmetic for already declared covered SEI, not a
    determination of taxable income. The public annual interface requires
    calendar-year declarations and does not infer a fiscal taxable year.
    """
    last = _date_quarter(end)
    first = max(_date_quarter(start), last - 3)
    amount = self_employment / (last - first + 1)
    return tuple((quarter, amount) for quarter in range(first, last + 1))


def _allocate_sei_post1977(
    start: date, end: date, self_employment: Fraction
) -> tuple[tuple[int, Fraction], ...]:
    """404.144: full months, including the month in which the year ends."""
    if start.year == end.year:
        return ((start.year, self_employment),)
    months_first = 12 - start.month + (start.day == 1)
    months_last = end.month
    total = months_first + months_last
    return (
        (start.year, self_employment * months_first / total),
        (end.year, self_employment * months_last / total),
    )


def _pre1978_taxable_qcs(
    start: date,
    end: date,
    self_employment: Fraction,
    wages: Fraction = Fraction(0),
) -> tuple[int, ...]:
    """404.141(d)(2), .142: fiscal-year SE/gift-credit worked arithmetic.

    At the maximum, every partly included quarter is credited, including a
    fifth calendar quarter; otherwise SEI is allocated to at most four.
    Wage QCs themselves are supplied separately by their actual quarters.
    """
    limit_year = start.year if start.year >= 1972 else end.year
    if self_employment + wages >= _annual_wage_limit(limit_year):
        return tuple(range(_date_quarter(start), _date_quarter(end) + 1))
    return tuple(
        quarter
        for quarter, amount in _allocate_sei_pre1978(
            start, end, self_employment
        )
        if amount >= 100
    )
