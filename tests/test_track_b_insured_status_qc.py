"""QC statutory conformance on invented and published cases; no real data.

Source quotations and capture hashes are checked by the insured-status
source tests. These tests execute the covered-earnings and assignment rules
independently of the public declaration/seal/status boundary.
"""

from datetime import date
from fractions import Fraction as F
from itertools import permutations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import _insured_status_qc as qc


def _quarters(year, *numbers):
    return tuple(qc._quarter_id(year, value) for value in numbers)


@settings(deadline=None)
@given(
    year=st.integers(1978, 2027),
    wages=st.integers(0, 10000000),
    sei=st.integers(0, 10000000),
    additional=st.integers(0, 10000000),
)
def test_qcs_bounded_and_monotone_in_earnings(year, wages, sei, additional):
    count = qc._post1977_qc_count(year, F(wages, 100), F(sei, 100))
    raised = qc._post1977_qc_count(
        year, F(wages + additional, 100), F(sei, 100)
    )
    assert 0 <= count <= raised <= 4


@pytest.mark.parametrize("year", range(1978, 2028))
@pytest.mark.parametrize("multiple", range(1, 5))
def test_published_increment_exact_boundary(year, multiple):
    threshold = qc.QC_AMOUNTS[year] * multiple
    assert qc._post1977_qc_count(year, F(threshold) - F(1, 100), F(0)) == (
        multiple - 1
    )
    assert qc._post1977_qc_count(year, F(threshold), F(0)) == multiple
    assert qc._post1977_qc_count(year, F(0), F(threshold)) == multiple


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(F(-1, 100), 250), (F(0), 260), (F(1, 100), 260)],
)
def test_qc_amount_ties_round_up(delta, expected):
    nawi = (255 + delta) * F("9226.48") / 250
    assert qc._qc_amount_from_nawi(nawi, 250) == expected


@settings(deadline=None)
@given(
    low=st.integers(1, 100000000),
    increase=st.integers(0, 100000000),
    prior=st.integers(25, 1000),
)
def test_qc_amount_prior_floor_and_nawi_monotonicity(low, increase, prior):
    first = qc._qc_amount_from_nawi(F(low, 100), prior * 10)
    second = qc._qc_amount_from_nawi(F(low + increase, 100), prior * 10)
    assert prior * 10 <= first <= second
    assert first % 10 == second % 10 == 0


def test_oact_2027_published_determination():
    unrounded = 250 * F("72800.33") / F("9226.48")
    # OACT displays the intermediate to cents; statute rounds the exact ratio.
    assert (unrounded * 100 + F(1, 2)) // 1 == 197259
    assert qc._qc_amount_from_nawi(F("72800.33"), 1890) == 1970
    assert qc.QC_AMOUNTS[2027] == 1970


def test_cfr404_143_two_and_fraction_increments():
    # The CFR's example is symbolic: greater than twice, below three times.
    for year, increment in qc.QC_AMOUNTS.items():
        assert qc._post1977_qc_count(year, F(5, 2) * increment, F(0)) == 2


@pytest.mark.parametrize("year", range(1938, 1978))
def test_pre1978_fifty_dollar_quarter_boundary(year):
    fixed, flexible = qc._pre1978_qc_credits(
        year, (F("49.99"), F(50), F(0), F("50.01")), F(0), F(0)
    )
    assert fixed == _quarters(year, 2, 4)
    assert flexible == 0


@pytest.mark.parametrize("year", range(1951, 1978))
def test_pre1978_calendar_sei_four_hundred_boundary(year):
    zeros = (F(0),) * 4
    assert qc._pre1978_qc_credits(year, zeros, F("399.99"), F(0)) == (
        (),
        0,
    )
    assert qc._pre1978_qc_credits(year, zeros, F(400), F(0)) == (
        qc._year_quarters(year),
        0,
    )


@pytest.mark.parametrize(
    ("first", "last", "limit"),
    [
        (1937, 1950, 3000),
        (1951, 1954, 3600),
        (1955, 1958, 4200),
        (1959, 1965, 4800),
        (1966, 1967, 6600),
        (1968, 1971, 7800),
        (1972, 1972, 9000),
        (1973, 1973, 10800),
        (1974, 1974, 13200),
        (1975, 1975, 14100),
        (1976, 1976, 15300),
        (1977, 1977, 16500),
    ],
)
def test_maximum_taxable_wages_give_four_gift_qcs(first, last, limit):
    for year in range(first, last + 1):
        assert qc._annual_wage_limit(year) == limit
        if year == 1937:
            # The annual wage threshold is captured; raw earnings also
            # require Act 213(b)'s half-year/age-65 allocation and refuse.
            continue
        assert qc._pre1978_qc_credits(
            year, (F(limit), F(0), F(0), F(0)), F(0), F(0)
        ) == (qc._year_quarters(year), 0)
        assert qc._pre1978_qc_credits(
            year, (F(limit) - F(1, 100), F(0), F(0), F(0)), F(0), F(0)
        ) == (_quarters(year, 1), 0)


@settings(deadline=None)
@given(
    year=st.integers(1955, 1977),
    wages=st.tuples(*(st.integers(0, 100000) for _ in range(4))),
    ag=st.integers(0, 100000),
    increase=st.integers(0, 100000),
)
def test_pre1978_qcs_bounded_and_monotone(year, wages, ag, increase):
    normalized = tuple(F(value, 100) for value in wages)
    fixed, flexible = qc._pre1978_qc_credits(
        year, normalized, F(0), F(ag, 100)
    )
    more_fixed, more_flexible = qc._pre1978_qc_credits(
        year, normalized, F(0), F(ag + increase, 100)
    )
    assert 0 <= len(fixed) + flexible <= len(more_fixed) + more_flexible <= 4


def test_rs00301_320_jane_agricultural_example():
    # Covered agricultural wages: Brown 101+59, Black150, Green90.
    fixed, flexible = qc._pre1978_qc_credits(
        1973, (F(0), F(0), F(50), F(0)), F(0), F(101 + 150 + 90 + 59)
    )
    assert fixed == _quarters(1973, 3)
    assert flexible == 3
    assert qc._assign_qcs(fixed, flexible, qc._year_quarters(1973)) == (
        qc._year_quarters(1973)
    )


@pytest.mark.parametrize("ag_count", range(5))
def test_agricultural_qcs_fill_quarters_not_already_credited(ag_count):
    fixed, flexible = qc._pre1978_qc_credits(
        1973, (F(0), F(0), F(50), F(0)), F(0), F(100 * ag_count)
    )
    candidates = qc._assignment_candidates(
        fixed, flexible, qc._year_quarters(1973)
    )
    assert all(len(value) == min(1 + ag_count, 4) for value in candidates)
    assert all(qc._quarter_id(1973, 3) in value for value in candidates)


def test_agricultural_assignment_ordinary_latest_and_favorable_exception():
    fixed = _quarters(1973, 3)
    allowed = qc._year_quarters(1973)
    assert qc._assign_qcs(fixed, 1, allowed) == _quarters(1973, 3, 4)
    assert qc._assign_qcs(fixed, 1, allowed, _quarters(1973, 1)) == (
        _quarters(1973, 1, 3)
    )


def test_rs00301_230_henry_and_325_john_retroactive_assignment():
    # Both published 2010 examples require the one annual QC in Q1.
    for wages in (F(1500), F(1200)):
        count = qc._post1977_qc_count(2010, wages, F(0))
        assert count == 1
        assert qc._assign_qcs(
            (), count, qc._year_quarters(2010), _quarters(2010, 1)
        ) == _quarters(2010, 1)


@settings(deadline=None)
@given(
    fixed_flags=st.tuples(*(st.booleans() for _ in range(4))),
    permitted_flags=st.tuples(*(st.booleans() for _ in range(4))),
    target_flags=st.tuples(*(st.booleans() for _ in range(4))),
    flexible=st.integers(0, 4),
)
def test_assignment_maximizes_window_and_is_order_independent(
    fixed_flags, permitted_flags, target_flags, flexible
):
    quarters = qc._year_quarters(2000)
    fixed = tuple(
        q for q, flag in zip(quarters, fixed_flags, strict=True) if flag
    )
    allowed = tuple(
        q for q, flag in zip(quarters, permitted_flags, strict=True) if flag
    )
    window = tuple(
        q for q, flag in zip(quarters, target_flags, strict=True) if flag
    )
    actual = qc._assign_qcs(fixed, flexible, allowed, window)
    candidates = qc._assignment_candidates(fixed, flexible, allowed)
    assert len(actual) <= 4
    assert len(actual) == len(set(actual))
    assert set(actual) <= set(allowed)
    assert set(fixed) & set(allowed) <= set(actual)
    assert len(set(actual) & set(window)) == max(
        len(set(candidate) & set(window)) for candidate in candidates
    )
    assert actual == qc._assign_qcs(
        tuple(reversed(fixed)),
        flexible,
        tuple(reversed(allowed)),
        tuple(reversed(window)),
    )
    assert actual == qc._assign_qcs(fixed, flexible, allowed, window)


def test_assignment_all_six_two_credit_combinations_are_reachable():
    candidates = qc._assignment_candidates((), 2, qc._year_quarters(2020))
    assert len(candidates) == 6
    for target in candidates:
        assert qc._assign_qcs((), 2, qc._year_quarters(2020), target) == target
    for permuted in permutations(qc._year_quarters(2020)):
        assert qc._assignment_candidates((), 2, permuted) == candidates


@settings(deadline=None)
@given(
    year=st.integers(1937, 2027),
    start=st.integers(0, 3),
    length=st.integers(0, 6),
    count=st.integers(0, 4),
)
def test_disability_exclusion_never_adds_qc(year, start, length, count):
    quarters = qc._year_quarters(year)
    first = quarters[start]
    end = first + length
    allowed = qc._allowed_quarters(
        year,
        through_quarter=quarters[-1],
        disability_periods=((first, end),),
    )
    assert set(allowed) <= set(quarters)
    assert first in allowed
    if end in quarters:
        assert end in allowed
    assert all(not first < value < end for value in allowed)
    assert len(qc._assign_qcs((), count, allowed)) <= len(
        qc._assign_qcs((), count, quarters)
    )


def test_death_future_exit_and_disability_endpoint_exclusions():
    quarters = qc._year_quarters(2026)
    assert (
        qc._allowed_quarters(
            2026,
            through_quarter=quarters[2],
            death_quarter=quarters[1],
            coverage_end_quarter=quarters[3],
        )
        == quarters[:2]
    )
    assert (
        qc._allowed_quarters(
            2026, through_quarter=quarters[3], coverage_end_quarter=quarters[0]
        )
        == quarters[:1]
    )
    assert qc._allowed_quarters(
        2026,
        through_quarter=quarters[3],
        disability_periods=((quarters[0], quarters[3]),),
    ) == (quarters[0], quarters[3])
    # A disallowed fixed wage quarter does not migrate to another quarter.
    assert qc._assign_qcs(quarters[1:2], 0, (quarters[0], quarters[3])) == ()


def test_rs00301_220_ann_calendar_year_sei_allocation():
    assert qc._allocate_sei_post1977(
        date(1987, 10, 1), date(1988, 9, 30), F(12000)
    ) == ((1987, F(3000)), (1988, F(9000)))


def test_cfr404_144_partial_month_taxable_year_example():
    assert qc._allocate_sei_post1977(
        date(1978, 5, 15), date(1979, 5, 14), F(1200)
    ) == ((1978, F(700)), (1979, F(500)))


def test_rs00301_340_john_fiscal_sei_allocation():
    assert qc._allocate_sei_pre1978(
        date(1973, 4, 1), date(1974, 3, 31), F(10800)
    ) == tuple(
        (quarter, F(2700))
        for quarter in (*_quarters(1973, 2, 3, 4), *_quarters(1974, 1))
    )


def test_rs00301_340_short_year_source_erratum_is_not_imitated():
    actual = qc._allocate_sei_pre1978(
        date(1973, 9, 1), date(1974, 1, 3), F(10900)
    )
    assert actual == tuple(
        (quarter, F(10900, 3))
        for quarter in (*_quarters(1973, 3, 4), *_quarters(1974, 1))
    )
    assert sum(amount for _, amount in actual) == 10900
    # POMS labels $10,900 as SEI but prints $3,600 each. Literal equal
    # allocation under 404.142 is $10,900/3. An omitted contribution-base
    # cap explains the printed figure if $10,900 meant net earnings:
    # 213(a)(2)(B)(iii) gives the 1973 taxable year a $10,800 maximum.
    assert 3 * F(3600) == 10800 != F(10900)
    assert all(amount >= 100 for _, amount in actual)
    covered = min(F(10900), F(qc._annual_wage_limit(1973)))
    capped = qc._allocate_sei_pre1978(
        date(1973, 9, 1), date(1974, 1, 3), covered
    )
    assert covered == 10800
    assert all(amount == 3600 for _, amount in capped)
    assert len(capped) == len(actual) == 3


@pytest.mark.parametrize(
    ("start", "end", "sei", "wages", "expected"),
    [
        (
            date(1973, 7, 1),
            date(1974, 6, 30),
            F(8100),
            F(2700),
            (*_quarters(1973, 3, 4), *_quarters(1974, 1, 2)),
        ),
        (
            date(1973, 6, 1),
            date(1974, 5, 31),
            F(10800),
            F(0),
            (*_quarters(1973, 2, 3, 4), *_quarters(1974, 1, 2)),
        ),
        (
            date(1973, 6, 1),
            date(1974, 5, 31),
            F(10620),
            F(180),
            (*_quarters(1973, 2, 3, 4), *_quarters(1974, 1, 2)),
        ),
    ],
)
def test_rs00301_345_fiscal_gift_credit_examples(
    start, end, sei, wages, expected
):
    assert qc._pre1978_taxable_qcs(start, end, sei, wages) == expected


@settings(deadline=None)
@given(
    amount=st.integers(40000, 10000000),
    start_month=st.integers(1, 12),
    duration=st.integers(0, 3),
)
def test_exact_sei_allocation_conserves_income(amount, start_month, duration):
    start = date(1973, start_month, 1)
    end_month = start_month - 1 + duration
    end = date(1973 + end_month // 12, end_month % 12 + 1, 28)
    allocations = qc._allocate_sei_pre1978(start, end, F(amount, 100))
    assert sum(value for _, value in allocations) == F(amount, 100)
    assert 1 <= len(allocations) <= 4
    assert len({value for _, value in allocations}) == 1
    post = qc._allocate_sei_post1977(start, end, F(amount, 100))
    assert sum(value for _, value in post) == F(amount, 100)


@pytest.mark.parametrize(
    ("year", "sei", "ag", "reason"),
    [
        (1954, F(0), F(100), "pre1955_agricultural_allocation_unsupported"),
        (1950, F(400), F(0), "pre1951_self_employment_unsupported"),
    ],
)
def test_precoverage_earnings_need_explicit_resolution(year, sei, ag, reason):
    with pytest.raises(qc._UnsupportedQC) as error:
        qc._pre1978_qc_credits(year, (F(0),) * 4, sei, ag)
    assert error.value.reason == reason


def test_1937_raw_earnings_refuse_but_zero_does_not_need_allocation():
    with pytest.raises(qc._UnsupportedQC) as error:
        qc._pre1978_qc_credits(1937, (F(50), F(0), F(0), F(0)), F(0), F(0))
    assert error.value.reason == "1937_earnings_allocation_unsupported"
    assert qc._pre1978_qc_credits(1937, (F(0),) * 4, F(0), F(0)) == ((), 0)
