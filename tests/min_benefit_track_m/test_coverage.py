"""Years of coverage (plan field G6) on INVENTED histories and amounts.

The quarter-of-coverage amounts, the wage index and every history here are
**INVENTED**; no PSID value, SSA value or comparator value.  Each expected
count is worked by hand beside it.
"""

from __future__ import annotations

import math

import pytest

from populace_dynamics.min_benefit_track_m import coverage
from populace_dynamics.min_benefit_track_m import policy as pol

#: INVENTED: 100 dollars a quarter in 1978, rising 10 a year.
QC = coverage.QuarterOfCoverageAmounts(
    {year: 100.0 + 10.0 * (year - 1978) for year in range(1978, 2031)},
    {"kind": "INVENTED"},
)
#: INVENTED wage index growing 5 percent a year from 1951.
NAWI = {year: 1_000.0 * 1.05 ** (year - 1951) for year in range(1951, 2031)}
ZERO_GAPS = pol.TrackMPolicy(gap_year_rule=pol.GAP_YEARS_ZERO)


def test_annual_amount_is_four_quarters_from_1978():
    # 1990: 4 x (100 + 120) = 880.
    assert coverage.annual_coverage_amount(1990, QC, NAWI) == 880.0


def test_before_1978_the_1978_amount_is_scaled_back_by_awi():
    # 1977: 4 x 100 x AWI(1977) / AWI(1978) = 400 / 1.05 = 380.95.
    assert coverage.annual_coverage_amount(1977, QC, NAWI) == pytest.approx(
        400 / 1.05
    )
    with pytest.raises(KeyError):
        coverage.annual_coverage_amount(1950, QC, NAWI)


def test_before_1978_the_statute_credits_fifty_dollars_a_quarter():
    # 42 USC 413(a)(2)(A)(i): $50 of wages in a quarter; 4 x 50 = 200 a
    # year whatever the wage index.  From 1978 the rule is unchanged.
    statute = pol.TrackMPolicy(
        pre_1978_coverage_rule=pol.PRE_1978_STATUTE_50_PER_QUARTER
    )
    for year in (1951, 1968, 1977):
        assert coverage.annual_coverage_amount(year, QC, NAWI, statute) == 200
    assert coverage.annual_coverage_amount(1990, QC, NAWI, statute) == 880.0
    # The default stays the plan's convention: 1976 needs 362.81 there.
    history = {1976: 300.0, 1977: 199.0}
    default = coverage.count_coverage_years(
        history,
        birth_year=1950,
        through_year=1980,
        qc=QC,
        nawi=NAWI,
        policy=ZERO_GAPS,
    )
    assert default.years == 0
    literal = coverage.count_coverage_years(
        history,
        birth_year=1950,
        through_year=1980,
        qc=QC,
        nawi=NAWI,
        policy=pol.TrackMPolicy(
            gap_year_rule=pol.GAP_YEARS_ZERO,
            pre_1978_coverage_rule=pol.PRE_1978_STATUTE_50_PER_QUARTER,
        ),
    )
    assert literal.counted_years == (1976,)
    assert pol.TrackMPolicy().pre_1978_coverage_rule == (
        pol.PRE_1978_SCALED_BY_AWI
    )


def test_a_year_counts_at_four_quarters_amount():
    history = {1990: 880.0, 1991: 889.99, 1977: 381.0, 1976: 362.0}
    # 1991 needs 4 x 230 = 920; 1976 needs 400 / 1.05^2 = 362.81.
    count = coverage.count_coverage_years(
        history,
        birth_year=1950,
        through_year=2011,
        qc=QC,
        nawi=NAWI,
        policy=ZERO_GAPS,
    )
    assert count.counted_years == (1977, 1990)
    assert count.years == 2


def test_the_count_ends_at_through_year_and_counts_all_ages():
    # Earnings at 16 (1966) count (G6: all ages); 2012 is after the end.
    history = {1966: 10_000.0, 1990: 10_000.0, 2012: 10_000.0}
    count = coverage.count_coverage_years(
        history,
        birth_year=1950,
        through_year=2011,
        qc=QC,
        nawi=NAWI,
        policy=ZERO_GAPS,
    )
    assert count.counted_years == (1966, 1990)
    assert 2012 not in count.observed_years


def test_unobserved_years_count_as_zero_and_are_flagged():
    history = {year: 10_000.0 for year in range(1972, 1990)}
    history[1980] = math.nan
    count = coverage.count_coverage_years(
        history,
        birth_year=1950,
        through_year=1995,
        qc=QC,
        nawi=NAWI,
        policy=ZERO_GAPS,
    )
    # 1972-1989 observed except 1980: 17 counted years.
    assert count.years == 17
    # Flag window 1972 (age 22) to 1995: 1980 and 1990-1995 are unobserved.
    assert count.unobserved_years == (1980, 1990, 1991, 1992, 1993, 1994, 1995)
    assert count.flagged
    with pytest.raises(ValueError):
        coverage.count_coverage_years(
            {1990: -1.0},
            birth_year=1950,
            through_year=1995,
            qc=QC,
            nawi=NAWI,
        )


def test_biennial_gap_years_take_the_neighbor_law():
    # Observed even years 1996-2010 at 5,000 with 2004 at 1,000.  Gap years
    # 1997-2009 (odd) take the mean of their neighbors: 2003 and 2005 get
    # (5,000 + 1,000) / 2 = 3,000, still above 4 x (100 + 10 x 25) = 1,400.
    history = {year: 5_000.0 for year in range(1996, 2011, 2)}
    history[2004] = 1_000.0
    count = coverage.count_coverage_years(
        history,
        birth_year=1970,
        through_year=2010,
        qc=QC,
        nawi=NAWI,
    )
    assert count.imputed_years == (1997, 1999, 2001, 2003, 2005, 2007, 2009)
    # 2004 needs 4 x 360 = 1,440 > 1,000: it does not count.
    assert 2004 not in count.counted_years
    assert count.years == 8 + 7 - 1
    # G6 read literally: the gap years count as zero.
    literal = coverage.count_coverage_years(
        history,
        birth_year=1970,
        through_year=2010,
        qc=QC,
        nawi=NAWI,
        policy=ZERO_GAPS,
    )
    assert literal.years == 7
    assert literal.imputed_years == ()
    assert 1997 in literal.unobserved_years


def test_a_gap_year_never_uses_a_neighbor_after_the_count():
    # 2011's right neighbor 2012 is after through_year 2011, so the left
    # neighbor 2010 (at 0) is used alone; with 2012 it would be
    # (0 + 50,000) / 2 = 25,000 and count.  2009 takes 2010 alone too.
    history = {2010: 0.0, 2012: 50_000.0}
    count = coverage.count_coverage_years(
        history,
        birth_year=1970,
        through_year=2011,
        qc=QC,
        nawi=NAWI,
    )
    assert count.imputed_years == (2009, 2011)
    assert count.years == 0


def test_invented_amounts_are_validated():
    with pytest.raises(ValueError):
        coverage.QuarterOfCoverageAmounts({1978: 0.0}, {})
    with pytest.raises(TypeError):
        coverage.QuarterOfCoverageAmounts({"1978": 1.0}, {})
    with pytest.raises(KeyError):
        QC.amount(1977)
