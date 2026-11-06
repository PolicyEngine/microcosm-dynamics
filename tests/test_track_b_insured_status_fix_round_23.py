"""Round 23: a period keeps the basis it began on; an exit bars later years.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

A current period that began before age 31 on 404.130(c) alone, where
404.130(b) fails at its first quarter, is one "for which you were only
insured under paragraph (c)" (404.130(d)(1)). Once it ends, the rule counts it
as a flagged prior, so 404.130(d) reaches the quarters after it at 31 or
later; where annual placement or an UNKNOWN year decides that basis and the
two bases give different dates, the date refuses by name. A period begins on
its onset day or on the first day of a later insured quarter (404.321(a)),
so it can share the quarter a prior ended in, as RS 00301.140 example 7
shows. A coverage exit or a birth bars no quarter of its own year: an annual
QC takes any begun quarter through death (404.146).

Where a listed prior binds, DISABILITY's qualifying quarters span every basis
the record leaves open, and under UNKNOWN priors they reach the onset quarter.
The rule ends a living man's elapsed years at his retirement age once he
reaches 62 (404.110(b)(2)(iii)-(iv)). A flagged prior needs one placement
where 404.130(c) holds and 404.130(b) fails. A listed prior that no
completion supports refuses by name before any input error or UNKNOWN-earnings
refusal the record would raise. Past blindness can begin a listed prior only
from January 1973 (RS 00301.150 A).
"""

import re
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _pre1956_case,
)
from tests.test_track_b_insured_status_sources import source_text

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
FEMALE = i.Sex.FEMALE
MALE = i.Sex.MALE
ALL = i.InsuredTest.ALL
FULLY = i.InsuredTest.FULLY
CURRENTLY = i.InsuredTest.CURRENTLY
DISABILITY = i.InsuredTest.DISABILITY
Reason = i.InsuredUnsupportedReason
WEIGHT = Fraction(5, 2)
PROPERTY = settings(max_examples=25, deadline=None)
UNSUPPORTED_PRIOR = (
    "No annual placement supports a listed prior's first insured quarter"
)
LISTED_PRIOR = (
    "Annual placement decides a listed prior's first insured quarter"
)


def _person(birth, *priors, onset=None, established=False, **changes):
    values = dict(
        sex=FEMALE,
        prior_disability_periods=priors,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    if onset is not None:
        values.update(
            disability_onset=onset,
            current_disability_period_established=established,
            current_disability_period_provenance=OBSERVED,
        )
    values.update(changes)
    return i.Person(birth, **values)


def _ended(birth, onset, end, *priors, **changes):
    return _person(
        birth,
        *priors,
        onset=onset,
        established=True,
        current_disability_period_end=end,
        current_disability_period_end_provenance=OBSERVED,
        **changes,
    )


def _row(person, years, month, **options):
    return i.evaluate_insured_status(
        "round-23",
        WEIGHT,
        lambda: i.insured_status(person, years, month, **options),
    )


def _computed(person, years, month, **options):
    row = _row(person, years, month, **options)
    assert row.unsupported is None, row.unsupported
    return row.result


def _refused(reason, person, years, month, **options):
    row = _row(person, years, month, **options)
    assert row.result is None, row.result
    assert row.unsupported.reason is reason, row.unsupported
    counts = count_family_outcomes((row,))
    assert (counts.rows, counts.weight) == (1, WEIGHT)
    assert (counts.unsupported_rows, counts.unsupported_weight) == (1, WEIGHT)
    return row.unsupported.detail


def _dli(result):
    return result.dli.lower, result.dli.upper, result.dli.right_censored


def _month_end(year, month):
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


# A current period begun on 404.130(c) alone.

M1_BIRTH = date(1980, 2, 2)
M1_ONSET = date(2003, 1, 15)
M1_END = date(2004, 12, 31)
M1_MONTH = date(2013, 1, 1)
M1_ANNUAL = {2001: 2, 2002: 4, 2009: 4, 2010: 4, 2011: 4, 2012: 1}


def _m1_years(annual=M1_ANNUAL, month=M1_MONTH, **options):
    return history(_person(M1_BIRTH), month, annual, **options)


def test_a_period_begun_on_paragraph_c_alone_opens_paragraph_d_after_it():
    # Plain arithmetic: she attains 21 in 2001Q1. At 2003Q1 the 12 quarters
    # from 2000Q2 hold the six QCs of 2001 and 2002, so 404.130(c) holds, and
    # 404.130(b) finds six of 40: the period began on 404.130(c) alone. At
    # 2012Q4, past the 2011Q1 quarter she attains 31, 404.130(d) counts the
    # 47 quarters from 2001Q2 less the period's eight, an odd 39 it reduces to
    # 38, and the 19 QCs meet half. At 2013Q1 its cap asks 20 of 40.
    person = _ended(M1_BIRTH, M1_ONSET, M1_END)
    result = _computed(person, _m1_years(), M1_MONTH)
    assert result.current_disability_period_start == M1_ONSET
    assert result.disability.insured
    assert result.disability.rule == "under31_special"
    assert _dli(result) == (date(2012, 12, 31), date(2012, 12, 31), False)


def test_the_flag_reaches_a_frozen_exit_and_a_later_record():
    # The frozen exit keeps the same QCs, so the same 2012Q4 holds.
    person = _ended(M1_BIRTH, M1_ONSET, M1_END)
    exit_month = date(2012, 12, 1)
    years = _m1_years(end=exit_month)
    result = _computed(
        person, years, date(2027, 1, 1), coverage_end_month=exit_month
    )
    assert _dli(result) == (date(2012, 12, 31), date(2012, 12, 31), False)
    # A second record: eight QCs in 2003 and 2004 begin a 2005 period on
    # 404.130(c), and 404.130(d) holds through the 2016Q1 query quarter.
    person = _ended(date(1980, 2, 15), date(2005, 6, 1), date(2013, 12, 31))
    month = date(2016, 1, 1)
    years = history(person, month, {2003: 4, 2004: 4, 2014: 4, 2015: 4})
    result = _computed(person, years, month)
    assert result.disability.rule == "under31_special"
    assert _dli(result) == (date(2016, 3, 31), date(2016, 3, 31), True)


def test_an_unknown_end_spans_the_flagged_period_lengths():
    # Ending 2003-06-30, the period leaves 404.130(c) 13 counted quarters at
    # 2004Q4, reduced to 12, and the six QCs meet half; 2005Q1 asks seven.
    # Ending in 2005 or later, 404.130(d) holds through the query quarter.
    person = _person(
        M1_BIRTH,
        onset=M1_ONSET,
        established=True,
        current_disability_period_continues_through=date(2003, 6, 30),
        current_disability_period_continues_through_provenance=OBSERVED,
    )
    result = _computed(person, _m1_years(), M1_MONTH)
    assert _dli(result) == (date(2004, 12, 31), date(2013, 3, 31), True)


def test_one_more_qc_can_bring_the_dli_earlier_intended():
    # Intended violation of QC monotonicity, under the law: with 19 QCs
    # before the onset, 404.130(b) fails at 2003Q1, the period rests on
    # 404.130(c) alone, and 404.130(d) holds through 2012Q4. A second 1997
    # QC makes 20 of 40 at 2003Q1, so 404.130(b) began the period and
    # 404.130(d) never applies; 20 of 40 then last holds at 2012Q3.
    person = _ended(M1_BIRTH, M1_ONSET, M1_END)
    dlis = []
    for qcs_1997 in (1, 2):
        annual = {**M1_ANNUAL, 1997: qcs_1997, 1998: 4, 1999: 4, 2000: 4}
        dlis.append(_dli(_computed(person, _m1_years(annual), M1_MONTH)))
    assert dlis == [
        (date(2012, 12, 31), date(2012, 12, 31), False),
        (date(2012, 9, 30), date(2012, 9, 30), False),
    ]


BASIS_DECIDED = (
    "Annual placement or an unknown year decides whether the current period "
    "rested on 404.130(c) alone"
)


def test_a_placement_or_year_that_decides_the_basis_refuses():
    # Differential: 404.130(b) at 2003Q1 counts 1993Q2 to 2003Q1, so 19 QCs
    # there leave the period on 404.130(c) alone and 20 begin it on
    # 404.130(b); 1993 enters no later count. One 1993 QC therefore gives the
    # 19-QC date in 1993Q1 and the 20-QC date in 1993Q2 to Q4, so its
    # placement decides the date, as an UNKNOWN 1997 does. FULLY reports no
    # date, and computes.
    person = _ended(M1_BIRTH, M1_ONSET, M1_END)
    base = {**M1_ANNUAL, 1997: 1, 1998: 4, 1999: 4, 2000: 4}
    late, early = date(2012, 12, 31), date(2012, 9, 30)
    for qcs_1997, dli in ((0, late), (1, late), (2, early), (4, early)):
        years = _m1_years({**base, 1997: qcs_1997})
        assert _dli(_computed(person, years, M1_MONTH)) == (dli, dli, False)
    placed = _m1_years({**base, 1993: 1})
    unknown = _m1_years(base)
    unknown[1997] = i.CoverageYear(UNKNOWN)
    for years, reason in (
        (placed, Reason.ASSIGNMENT_COMPLEXITY),
        (unknown, Reason.UNKNOWN_EARNINGS),
    ):
        for test in (DISABILITY, ALL):
            detail = _refused(reason, person, years, M1_MONTH, test=test)
            assert detail == BASIS_DECIDED
        _computed(person, years, M1_MONTH, test=FULLY)


M1_ENDS = tuple(
    _month_end(year, month)
    for year in range(2003, 2013)
    for month in (3, 6, 9, 12)
    if (year, month) >= (2003, 6)
)


@PROPERTY
@example(qcs_1997=0, qcs_2001=2, qcs_2002=4, qcs_2012=1, end=M1_END)
@given(
    qcs_1997=st.integers(0, 4),
    qcs_2001=st.integers(1, 4),
    qcs_2002=st.integers(2, 4),
    qcs_2012=st.integers(0, 4),
    end=st.sampled_from(M1_ENDS),
)
def test_an_ended_current_period_counts_as_the_prior_it_becomes(
    qcs_1997, qcs_2001, qcs_2002, qcs_2012, end
):
    # Differential: the 1997 to 2002 QCs all sit in the 40 quarters ending
    # 2003Q1, so 404.130(b) holds there on every placement or on none, and
    # the period's flag follows. The same period listed as a prior with that
    # flag has the same DLI. The example adds four QCs in each of 1998 to
    # 2000 to the review's record, which leaves 18 of 40 at 2003Q1; without
    # the flag, 7b5b126a ended its DLI at 2012-09-30 rather than 2012-12-31.
    annual = {
        1997: qcs_1997,
        1998: 4,
        1999: 4,
        2000: 4,
        2001: qcs_2001,
        2002: qcs_2002,
        2009: 4,
        2010: 4,
        2011: 4,
        2012: qcs_2012,
    }
    years = _m1_years(annual)
    row = _row(_ended(M1_BIRTH, M1_ONSET, end), years, M1_MONTH)
    if row.result is None:
        return
    special = qcs_1997 + 12 + qcs_2001 + qcs_2002 < 20
    listed = _person(
        M1_BIRTH,
        i.DisabilityPeriod(
            row.result.current_disability_period_start,
            end,
            special_insured=special,
        ),
    )
    assert _dli(_computed(listed, years, M1_MONTH)) == _dli(row.result)


def test_a_period_begun_in_the_age_31_quarter_rests_on_paragraph_d():
    # She attains 31 on 2006-02-14, in 2006Q1, the quarter of her January 20
    # onset, so 404.130(c)(1) fails there and 404.130(d)(1) finds her
    # disabled again at 31. Her prior rested on 404.130(c) alone, so
    # 404.130(d) counts the 40 quarters from 1996Q2 less the ten inside the
    # prior after its first: 17 QCs (three in 1996, the two of 1997 in Q1
    # and Q2, and twelve from 2003) meet half of 30, and the period begins
    # on the onset day.
    prior = i.DisabilityPeriod(
        date(1997, 4, 1), date(1999, 12, 31), special_insured=True
    )
    person = _ended(
        date(1975, 2, 15), date(2006, 1, 20), date(2007, 12, 31), prior
    )
    month = date(2008, 1, 1)
    annual = {1996: 4, 1997: 2, 2003: 4, 2004: 4, 2005: 4}
    result = _computed(person, history(person, month, annual), month)
    found = result.disability
    assert result.current_disability_period_start == date(2006, 1, 20)
    assert (found.insured, found.rule, found.qualifying_quarter) == (
        True,
        "subsequent_special",
        date(2006, 1, 1),
    )
    assert (found.qc_count_lower, found.required) == (17, 15)
    assert _dli(result) == (date(2008, 3, 31), date(2008, 3, 31), True)


def test_an_open_flag_keeps_paragraph_b_where_every_placement_meets_it():
    # Her listed prior leaves the flag open, but 404.130(b) holds at the
    # 2007Q3 onset quarter on every placement. Counting the prior's
    # quarters, as 404.130(f) allows where that helps, the 40 quarters from
    # 1997Q4 hold 24 QCs, or 25 when her one 2007 QC comes before Q4, and
    # leaving them out still leaves at least 22. So the period never rested on
    # 404.130(c) alone, 404.130(d) doesn't reach the quarters after it, and
    # 20 of 40 last holds at 2012Q2. Read as 404.130(c) alone, the open flag
    # would bring in 404.130(d) more than 40 quarters after 21, where the
    # readings of its cap differ and the record refuses.
    prior = i.DisabilityPeriod(date(2002, 3, 19), date(2006, 1, 31))
    person = _ended(
        date(1976, 12, 8), date(2007, 7, 5), date(2008, 1, 31), prior
    )
    month, exit_month = date(2017, 3, 1), date(2008, 5, 1)
    annual = {
        1996: 4,
        1997: 4,
        1998: 3,
        1999: 2,
        2000: 1,
        2001: 4,
        2002: 2,
        2004: 4,
        2005: 3,
        2006: 4,
        2007: 1,
        2008: 4,
    }
    years = history(person, month, annual, end=exit_month)
    result = _computed(
        person, years, month, test=DISABILITY, coverage_end_month=exit_month
    )
    found = result.disability
    assert result.current_disability_period_start == date(2007, 7, 5)
    assert (found.insured, found.rule, found.qualifying_quarter) == (
        True,
        "disability_20_of_40",
        date(2007, 7, 1),
    )
    assert (found.qc_count_lower, found.required) == (25, 20)
    assert _dli(result) == (date(2012, 6, 30), date(2012, 6, 30), False)


# A period that shares the quarter a prior ended in.

JANE = i.DisabilityPeriod(
    date(1988, 3, 29), date(1990, 10, 31), special_insured=True
)
JANE_ANNUAL = {1986: 3, 1987: 3}
JANE_MONTH = date(1991, 1, 1)


def test_rs00301_140_example_7_quotes_the_shared_quarter():
    quote = (
        "Their period of disability ceased 8/90 and terminated the last day "
        "of 10/90. They became disabled again 12/3/90."
    )
    assert quote in source_text("poms_rs_00301_140")


def test_rs00301_140_example_7_begins_on_the_onset_day():
    # Plain arithmetic: the prior's quarters 1988Q1 to 1990Q4 hold no QC, so
    # 404.130(c) reaches back to the 12 quarters 1985Q1 to 1987Q4, which hold
    # the six QCs. The period begins on the onset day, in the quarter the
    # prior ended.
    for established in (True, False):
        person = _person(
            date(1967, 3, 16),
            JANE,
            onset=date(1990, 12, 3),
            established=established,
        )
        result = _computed(
            person, history(person, JANE_MONTH, JANE_ANNUAL), JANE_MONTH
        )
        assert result.disability.insured
        assert result.disability.rule == "under31_special"
        assert result.disability.qualifying_quarter == date(1990, 10, 1)
        assert result.current_disability_period_start == (
            date(1990, 12, 3) if established else None
        )


@PROPERTY
@given(onset=st.dates(date(1990, 11, 1), date(1990, 12, 31)))
def test_any_onset_after_the_prior_day_keeps_its_own_start(onset):
    person = _person(date(1967, 3, 16), JANE, onset=onset, established=True)
    result = _computed(
        person, history(person, JANE_MONTH, JANE_ANNUAL), JANE_MONTH
    )
    assert result.current_disability_period_start == onset


def test_periods_still_may_not_share_a_day():
    person = _person(
        date(1967, 3, 16), JANE, onset=date(1990, 10, 31), established=True
    )
    years = history(person, JANE_MONTH, JANE_ANNUAL)
    with pytest.raises(i.InvalidFamilyInput, match="must precede"):
        i.insured_status(person, years, JANE_MONTH)
    with pytest.raises(i.InvalidFamilyInput, match="overlap"):
        _person(
            date(1967, 3, 16),
            JANE,
            i.DisabilityPeriod(date(1990, 10, 31), date(1990, 12, 31)),
        )
    # A second listed period may begin in 1990Q4 the day after.
    second = i.DisabilityPeriod(
        date(1990, 12, 3), date(1991, 6, 30), special_insured=True
    )
    person = _person(date(1967, 3, 16), JANE, second)
    month = date(1992, 1, 1)
    result = _computed(person, history(person, month, JANE_ANNUAL), month)
    assert result.disability.insured


# A coverage exit bars only later years.


def test_an_exit_year_credits_any_begun_quarter():
    # Plain arithmetic: $6,000 of 2020 wages give four QCs at $1,410 each,
    # and every 2020 quarter has begun by 2024, so 2019's two make six.
    person = _person(date(2000, 6, 15))
    month = date(2024, 1, 1)
    results = []
    for exit_month in (date(2020, 2, 1), date(2020, 12, 1)):
        years = history(person, month, {2019: 2}, end=exit_month)
        years[2020] = i.CoverageYear(OBSERVED, wages=Fraction(6000))
        results.append(
            _computed(
                person,
                years,
                month,
                test=FULLY,
                coverage_end_month=exit_month,
            )
        )
    assert [r.qcs_by_year[2020] for r in results] == [(4, 4), (4, 4)]
    assert [
        (r.fully.insured, r.fully.qc_count_lower, r.fully.required)
        for r in results
    ] == [(True, 6, 6), (True, 6, 6)]


def test_forty_qcs_need_no_later_quarter():
    # Act 214(a)(2): 40 QCs make anyone fully insured, and the April 2005 exit
    # leaves all four 2005 QCs.
    person = _person(date(1955, 6, 15))
    exit_month = date(2005, 4, 1)
    month = date(2016, 6, 1)
    years = history(
        person, month, {y: 4 for y in range(1996, 2006)}, end=exit_month
    )
    result = _computed(
        person, years, month, test=FULLY, coverage_end_month=exit_month
    )
    assert result.fully.insured
    assert result.fully.qc_count_lower == 40


def test_an_unknown_exit_year_refuses_whatever_its_exit_month():
    person = _person(date(2000, 2, 2))
    month = date(2027, 1, 1)
    for exit_month in (date(2026, 4, 1), date(2026, 12, 1)):
        years = history(person, month, {2024: 3}, end=exit_month)
        years[2026] = i.CoverageYear(UNKNOWN)
        _refused(
            Reason.UNKNOWN_EARNINGS,
            person,
            years,
            month,
            coverage_end_month=exit_month,
        )


def test_an_established_period_keeps_its_row_after_a_february_exit():
    # Plain arithmetic: 2020's four QCs and 2016 to 2019's 16 make 20 of the
    # 40 quarters ending 2021Q1, so the period begins on the onset day. Ended
    # in April 2021, it leaves 2016 to 2020's 20 QCs in the 40 counted
    # quarters through 2026Q2, and 2026Q3 loses 2016Q1.
    month = date(2021, 6, 1)
    exit_month = date(2020, 2, 1)
    annual = {y: 4 for y in (*range(2001, 2011), *range(2016, 2020))}

    def years(person):
        out = history(person, month, annual, end=exit_month)
        out[2020] = i.CoverageYear(OBSERVED, wages=Fraction(6000))
        return out

    onset = date(2021, 1, 15)
    person = _person(date(1970, 6, 15), onset=onset, established=True)
    for test in (FULLY, CURRENTLY):
        result = _computed(
            person,
            years(person),
            month,
            test=test,
            coverage_end_month=exit_month,
        )
        assert result.current_disability_period_start == onset
    for test in (DISABILITY, ALL):
        _refused(
            Reason.CURRENT_PERIOD_DLI,
            person,
            years(person),
            month,
            test=test,
            coverage_end_month=exit_month,
        )
    person = _ended(date(1970, 6, 15), onset, date(2021, 4, 30))
    result = _computed(
        person, years(person), month, coverage_end_month=exit_month
    )
    assert result.disability.insured
    assert _dli(result) == (date(2026, 6, 30), date(2026, 6, 30), False)


@PROPERTY
@example(qcs_2019=0, qcs_2020=4, exit_month=2)
@given(
    qcs_2019=st.integers(0, 4),
    qcs_2020=st.integers(0, 4),
    exit_month=st.integers(1, 12),
)
def test_the_exit_month_moves_nothing_in_its_year(
    qcs_2019, qcs_2020, exit_month
):
    # An exit bars later years only, so every exit month of 2020 gives the
    # December exit's result. In the example, 7b5b126a cut a February exit's
    # four 2020 QCs to one.
    person = _person(date(2000, 6, 15))
    month = date(2024, 1, 1)

    def result(exit_day):
        years = history(
            person, month, {2019: qcs_2019, 2020: qcs_2020}, end=exit_day
        )
        found = i.insured_status(
            person, years, month, coverage_end_month=exit_day
        )
        return (
            found.fully,
            found.currently,
            found.disability,
            _dli(found),
            dict(found.qcs_by_year),
        )

    assert result(date(2020, exit_month, 1)) == result(date(2020, 12, 1))


def test_a_birth_year_credits_quarters_before_the_birth():
    # 404.143(a) credits $3,120 of 2000 wages as four QCs, and 404.146 bars
    # no quarter for a birth.
    person = _person(date(2000, 12, 15), death_date=date(2003, 3, 10))
    month = date(2004, 1, 1)
    years = history(person, month, {2001: 2})
    years[2000] = i.CoverageYear(OBSERVED, wages=Fraction(3120))
    result = _computed(person, years, month, test=FULLY)
    assert result.qcs_by_year[2000] == (4, 4)
    assert (result.fully.insured, result.fully.qc_count_lower) == (True, 6)


# A listed prior's qualifying quarters on every basis.

M4_PRIOR = i.DisabilityPeriod(date(1998, 1, 1), date(1999, 12, 31))
M4_ANNUAL = {
    **{y: 4 for y in range(1989, 1993)},
    1993: 3,
    1998: 1,
    **{y: 4 for y in range(1999, 2003)},
    2003: 2,
}


def test_a_binding_prior_keeps_the_earliest_qualifying_quarter():
    # Plain arithmetic: the filling 1990Q3, 1991Q1-Q3, 1992Q2-Q4 and 2000Q1
    # begins the prior on 404.130(b) at 2000Q2, with 20 of 40, and holds 20
    # in the 40 counted quarters ending 2007Q1.
    prior = i.DisabilityPeriod(date(2000, 4, 1), date(2005, 3, 31))
    annual = {
        1990: 1,
        1991: 3,
        1992: 3,
        1994: 4,
        1997: 4,
        1998: 4,
        2000: 1,
        2006: 4,
        2009: 4,
        2010: 4,
    }
    month = date(2011, 9, 1)
    for established in (False, True):
        person = _person(
            date(1959, 2, 28),
            prior,
            onset=date(2007, 1, 1),
            established=established,
        )
        result = _computed(person, history(person, month, annual), month)
        assert result.disability.qualifying_quarter == date(2007, 1, 1)
        assert result.disability.upper_qualifying_quarter == date(2007, 1, 1)
        assert result.current_disability_period_start == (
            date(2007, 1, 1) if established else None
        )
        assert "prior_disability_period_basis" not in result.unknown_facts


def test_a_prior_basis_split_widens_the_qualifying_quarters():
    # On 404.130(b) the 1998 QC sits in 1998Q1, and 2008Q2 first holds 20 of
    # 40. On past blindness it may sit later, and 2008Q1 holds 20.
    person = _person(date(1968, 2, 2), M4_PRIOR, onset=date(2008, 1, 1))
    month = date(2008, 4, 1)
    years = history(person, month, {**M4_ANNUAL, 2008: 2})
    result = _computed(person, years, month)
    assert result.disability.qualifying_quarter == date(2008, 4, 1)
    assert result.disability.upper_qualifying_quarter == date(2008, 1, 1)
    # The result names the fact the record leaves open.
    assert result.unknown_facts == ("prior_disability_period_basis",)
    assert result.decided_despite_unknowns


def test_a_prior_basis_split_widens_the_count():
    person = _person(date(1955, 2, 2), M4_PRIOR, onset=date(2008, 1, 1))
    month = date(2008, 1, 1)
    annual = {
        **{y: 4 for y in (*range(1980, 1985), *range(1989, 1993))},
        **{y: 4 for y in range(1999, 2004)},
        1993: 3,
        1998: 1,
    }
    result = _computed(person, history(person, month, annual), month)
    assert result.disability.insured
    assert (
        result.disability.qc_count_lower,
        result.disability.qc_count_upper,
    ) == (20, 21)
    assert result.unknown_facts == ("prior_disability_period_basis",)


def test_a_split_start_names_the_listed_prior():
    # Established, the same split moves the period's start, and the detail
    # names the prior that decides it.
    person = _person(
        date(1968, 2, 2), M4_PRIOR, onset=date(2008, 1, 1), established=True
    )
    month = date(2008, 4, 1)
    years = history(person, month, {**M4_ANNUAL, 2008: 2})
    detail = _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, month)
    assert detail == LISTED_PRIOR


# UNKNOWN priors.


def test_unknown_priors_reach_the_onset_quarter():
    # Plain arithmetic: with no prior, 2007Q2 first holds 20 of 40. A prior
    # 1990-01-01 to 1999-12-31 begins on 404.130(b) with 20 QCs in 1985 to
    # 1989 and lets the 40 counted quarters ending 2007Q1 hold 30.
    onset = date(2007, 1, 1)
    month = date(2008, 10, 1)
    annual = {
        **{y: 4 for y in range(1985, 1990)},
        **{y: 3 for y in range(2000, 2006)},
        2007: 4,
        2008: 4,
    }
    unknown = _person(
        date(1961, 2, 2),
        onset=onset,
        prior_disability_periods_provenance=UNKNOWN,
    )
    years = history(unknown, month, annual)
    found = _computed(unknown, years, month, test=DISABILITY).disability
    completions = [
        _computed(
            _person(date(1961, 2, 2), *priors, onset=onset),
            years,
            month,
            test=DISABILITY,
        ).disability.qualifying_quarter
        for priors in (
            (),
            (i.DisabilityPeriod(date(1990, 1, 1), date(1999, 12, 31)),),
        )
    ]
    assert completions == [date(2007, 4, 1), date(2007, 1, 1)]
    assert (found.upper_qualifying_quarter, found.qualifying_quarter) == (
        date(2007, 1, 1),
        date(2007, 4, 1),
    )


def test_unknown_priors_may_end_before_a_later_onset_in_its_quarter():
    # A prior can end at a month's end, so a February or March onset can
    # follow one in its own quarter; a January 15 onset can't.
    for onset, invalid in (
        (date(2022, 1, 15), True),
        (date(2022, 2, 15), False),
        (date(2022, 3, 15), False),
    ):
        person = _ended(
            date(1993, 2, 2),
            onset,
            date(2022, 12, 31),
            prior_disability_periods_provenance=UNKNOWN,
        )
        month = date(2023, 1, 1)
        years = history(person, month, {2016: 4, 2017: 2})
        if invalid:
            with pytest.raises(i.InvalidFamilyInput, match="no possible"):
                i.insured_status(person, years, month, test=FULLY)
        else:
            _refused(Reason.UNKNOWN_PERIODS, person, years, month, test=FULLY)


# A man's elapsed years.


def _table_404_115():
    text = source_text("ecfr_20cfr404_subpart_b")
    table = text[
        text.index("§ 404.115 Table") : text.index("1 Number of QCs required")
    ]
    return {
        int(match[1]): tuple(int(n) for n in match[2].split())
        for match in re.finditer(
            r"Jan\. 2, (\d{4}) to Jan\. 1, \d{4}((?: \d+)+)", table
        )
    }


def test_the_404_115_table_gives_each_cohort_its_count():
    # Column II for a living worker, by sex; columns III and IV for a death
    # before retirement age by year, born before 1930; column V by age at
    # death, born 1930 or later.
    table = _table_404_115()
    assert sorted(table) == list(range(1893, 1929))
    deaths = 0
    for year, numbers in table.items():
        for sex, expected in ((MALE, numbers[0]), (FEMALE, numbers[1])):
            person = _person(date(year, 7, 1), sex=sex)
            for age in (62, 63, 64, 66):
                month = date(year + age, 12, 1)
                assert i.fully_insured_requirement(person, month) == expected
        if len(numbers) != 5:
            continue
        death_year, required, age = numbers[2:]
        for birth, died in (
            (date(1929, 7, 1), date(death_year, 6, 30)),
            (date(1940, 7, 1), date(1940 + age, 6, 30)),
        ):
            person = _person(birth, death_date=died)
            month = date(died.year, 12, 1)
            assert i.fully_insured_requirement(person, month) == required
            deaths += 1
    # The 33 rows for 1893 through 1925 carry the death columns.
    assert deaths == 2 * 33


def test_a_man_who_reached_62_before_1973_counts_to_65():
    # 404.110(b)(2)(iv): he became 62 in 1970, so 1951 to 1972 elapse, and
    # 20 QCs fall two short, with or without an RIB month. A death in 1971
    # ends the count at 1970 (404.110(b)(3)).
    month = date(1971, 12, 1)
    for changes in ({}, {"rib_entitlement_month": date(1971, 12, 1)}):
        person = _person(date(1908, 7, 1), sex=MALE, **changes)
        years = history(person, month, {y: 1 for y in range(1951, 1971)})
        fully = _computed(person, years, month, test=FULLY).fully
        assert (fully.insured, fully.qc_count_lower, fully.required) == (
            False,
            20,
            22,
        )
    person = _person(date(1908, 7, 1), sex=MALE, death_date=date(1971, 6, 15))
    years = history(person, month, {y: 1 for y in range(1951, 1971)})
    fully = _computed(person, years, month, test=FULLY).fully
    assert (fully.insured, fully.required) == (True, 20)
    # 404.110(b)(2)(iii): he became 62 in 1974, so 1951 to 1974 elapse.
    person = _person(date(1912, 7, 1), sex=MALE)
    month = date(1974, 12, 1)
    years = history(person, month, {y: 1 for y in range(1951, 1974)})
    fully = _computed(person, years, month, test=FULLY).fully
    assert (fully.insured, fully.qc_count_lower, fully.required) == (
        False,
        23,
        24,
    )


def test_a_death_after_the_query_keeps_the_living_count():
    # On 1971-12-01 he is alive unless he died by that day, so a death later
    # that month leaves 404.110(b)(2)(iv)'s count to 1972, and a death that
    # day ends it at 1970 (404.110(b)(3)).
    month = date(1971, 12, 1)
    for died, expected in (
        (date(1971, 12, 2), (False, 22)),
        (date(1971, 12, 15), (False, 22)),
        (date(1971, 12, 1), (True, 20)),
    ):
        person = _person(date(1908, 7, 1), sex=MALE, death_date=died)
        years = history(person, month, {y: 1 for y in range(1951, 1971)})
        fully = _computed(person, years, month, test=FULLY).fully
        assert (fully.insured, fully.required) == expected, died


# A flagged prior needs one placement for both halves.


def test_a_flagged_prior_needs_paragraph_c_without_paragraph_b():
    # Plain arithmetic: she attains 21 in 1983Q2, so 404.130(c) at 1990Q2
    # counts 28 quarters and asks 14, and every placement reaches at most 11.
    # 404.130(b) holds on some placements, but none passes 404.130(c) alone.
    prior = i.DisabilityPeriod(
        date(1990, 4, 1), date(1990, 6, 30), special_insured=True
    )
    annual = {
        1980: 3,
        1981: 4,
        1982: 2,
        1983: 3,
        1986: 4,
        1987: 4,
        1990: 1,
        2005: 4,
        2006: 4,
        2007: 4,
        2010: 4,
        2011: 4,
    }
    month = date(2011, 10, 1)
    for established in (True, False, None):
        person = _person(
            date(1962, 6, 28),
            prior,
            onset=date(2010, 2, 10),
            established=established,
            current_disability_period_provenance=(
                UNKNOWN if established is None else OBSERVED
            ),
        )
        detail = _refused(
            Reason.ASSIGNMENT_COMPLEXITY,
            person,
            history(person, month, annual),
            month,
        )
        assert detail == UNSUPPORTED_PRIOR


@pytest.mark.parametrize(
    "qcs_2004,test,outcome,detail",
    (
        (None, ALL, Reason.UNKNOWN_EARNINGS, None),
        (None, FULLY, Reason.ASSIGNMENT_COMPLEXITY, LISTED_PRIOR),
        (0, ALL, Reason.ASSIGNMENT_COMPLEXITY, UNSUPPORTED_PRIOR),
        (1, ALL, Reason.ASSIGNMENT_COMPLEXITY, UNSUPPORTED_PRIOR),
        (2, ALL, None, None),
        (3, ALL, None, None),
        (4, ALL, Reason.ASSIGNMENT_COMPLEXITY, UNSUPPORTED_PRIOR),
    ),
)
def test_only_a_middle_completion_fits_a_flag(qcs_2004, test, outcome, detail):
    # Plain arithmetic: at 2006Q1, 404.130(c) counts the 20 quarters from
    # 2001Q2 and asks ten, so 2004 needs two QCs beside 2002 and 2003's
    # eight. 404.130(b) finds 16 more from 1998 and 1999, so four 2004 QCs
    # reach 20 of 40. Only two or three fit the flag. UNKNOWN, the two give
    # different dates; FULLY alone holds on both, and the open year still
    # decides where the prior begins, which neither bound shows.
    prior = i.DisabilityPeriod(
        date(2006, 1, 1), date(2006, 12, 31), special_insured=True
    )
    person = _person(date(1980, 2, 2), prior)
    month = date(2008, 1, 1)
    years = history(person, month, {1998: 4, 1999: 4, 2002: 4, 2003: 4})
    years[2004] = (
        i.CoverageYear(UNKNOWN)
        if qcs_2004 is None
        else i.CoverageYear(OBSERVED, qc_count=qcs_2004)
    )
    if outcome is None:
        _computed(person, years, month, test=test)
        return
    found = _refused(outcome, person, years, month, test=test)
    assert detail is None or found == detail


@pytest.mark.parametrize("unknown_years", (5, 6))
def test_a_flag_every_completion_contradicts_refuses_by_that_name(
    unknown_years,
):
    # Plain arithmetic: 1999 to 2003's 20 QCs fill 20 of the 40 quarters
    # ending 2004Q1 on every placement, so 404.130(b) held there whatever the
    # UNKNOWN years before 1999 hold, and no completion fits the flag. Six
    # such years have 15,625 completions, and the refusal still names the
    # flag rather than their number.
    prior = i.DisabilityPeriod(
        date(2004, 1, 1), date(2005, 12, 31), special_insured=True
    )
    person = _person(date(1975, 2, 2), prior)
    month = date(2007, 1, 1)
    years = history(person, month, {y: 4 for y in range(1999, 2004)})
    for year in range(1999 - unknown_years, 1999):
        years[year] = i.CoverageYear(UNKNOWN)
    detail = _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, month)
    assert detail == UNSUPPORTED_PRIOR


# A listed prior no completion supports refuses first.


@pytest.mark.parametrize("fill", (None, 0, 4))
def test_an_unsupported_prior_refuses_before_unknown_earnings(fill):
    # Plain arithmetic: born 1940, she can reach 20 of 40 at 1970Q1 only with
    # QCs before 1968, and the record declares none; past blindness counts
    # only from 1973. No completion of 1974 to 1977 can begin the prior.
    person = _ended(
        date(1940, 2, 2),
        date(1977, 2, 15),
        date(1977, 4, 30),
        i.DisabilityPeriod(date(1970, 1, 1), date(1977, 1, 31)),
    )
    month = date(1978, 1, 1)
    years = history(person, month, {1968: 4, 1969: 4})
    for year in range(1974, 1978):
        years[year] = (
            i.CoverageYear(UNKNOWN)
            if fill is None
            else i.CoverageYear(
                OBSERVED, qc_quarters=tuple(n < fill for n in range(4))
            )
        )
    detail = _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, month)
    assert detail == UNSUPPORTED_PRIOR


@pytest.mark.parametrize(
    "start,supported",
    ((date(1972, 12, 1), False), (date(1973, 1, 1), True)),
)
def test_past_blindness_begins_a_prior_only_from_1973(start, supported):
    # RS00301.150 A dates blindness with fully insured status alone from
    # benefits payable January 1973. Born 1940, she was 31 in 1971, and her
    # 12 QCs from 1962 to 1964 make her fully insured in 1972 or 1973 (10 or
    # 11 elapsed years) but never give 20 of 40 there.
    person = _person(
        date(1940, 2, 2), i.DisabilityPeriod(start, date(1973, 12, 31))
    )
    month = date(1980, 1, 1)
    years = history(person, month, {1962: 4, 1963: 4, 1964: 4})
    if supported:
        result = _computed(person, years, month)
        fully = result.fully
        assert (fully.insured, fully.qc_count_lower, fully.required) == (
            False,
            12,
            17,
        )
        assert _dli(result) == (date(1967, 6, 30), date(1967, 6, 30), False)
        return
    detail = _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, month)
    assert detail == UNSUPPORTED_PRIOR


@pytest.mark.parametrize("test", (FULLY, ALL))
def test_a_1965_prior_cannot_rest_on_past_blindness(test):
    # Born 1930, her 16 QCs from 1952 to 1955 make her fully insured in 1965
    # (13 elapsed years) but leave 3 QCs in the 40 quarters ending 1965Q1.
    person = _person(
        date(1930, 2, 2),
        i.DisabilityPeriod(date(1965, 1, 1), date(1966, 12, 31)),
    )
    month = date(1980, 1, 1)
    years = history(person, month, {y: 4 for y in range(1952, 1956)})
    detail = _refused(
        Reason.ASSIGNMENT_COMPLEXITY, person, years, month, test=test
    )
    assert detail == UNSUPPORTED_PRIOR


# Listed priors before 1956.

PRE1956_PRIOR = i.DisabilityPeriod(date(1952, 7, 15), date(1958, 12, 31))
PRE1956_BASE = {1938: 4, 1939: 4, 1940: 4, 1941: 2, 1951: 4, 1952: 2}


@pytest.mark.parametrize(
    "later,reason,detail",
    (
        (
            {1953: 4, 1954: 4, 1955: 4, 1956: 4},
            Reason.ASSIGNMENT_COMPLEXITY,
            UNSUPPORTED_PRIOR,
        ),
        (
            {1953: 4, 1954: 4, 1959: 4, 1960: 3},
            Reason.DISABILITY_BEFORE_1956,
            "RS00301.480 may have begun a listed prior before 1956",
        ),
        ({1961: 4, 1962: 4}, None, None),
    ),
)
def test_a_pre1956_listed_prior_rests_on_rs00301_480(later, reason, detail):
    # RS00301.480 B.1: the 20 QCs through 1952Q2 include six continuous from
    # 1951Q1. 20 of 40 inside the prior, at 1956Q2, excludes the route on
    # both readings of A; 20 of 40 at 1960Q2, after it, excludes it on one;
    # none before October 1960 leaves it.
    person = _person(date(1910, 2, 2), PRE1956_PRIOR, sex=MALE)
    month = date(1968, 1, 1)
    years = history(person, month, {**PRE1956_BASE, **later})
    if reason is None:
        result = _computed(person, years, month)
        assert result.fully.insured
        assert not result.disability.insured
        return
    assert _refused(reason, person, years, month) == detail


def test_a_listed_alternate_prior_lets_a_later_period_begin():
    # The current period begins in 1964 on 404.130(b), after a prior that
    # B.1 alone began in 1952.
    person, _, month = _pre1956_case()
    onset = date(1964, 7, 15)
    annual = {
        **PRE1956_BASE,
        1961: 4,
        1962: 4,
        1963: 4,
        1964: 2,
    }
    for end in (1959, 1960):
        listed = _person(
            person.birth_date,
            i.DisabilityPeriod(date(1952, 7, 15), date(end, 12, 31)),
            onset=onset,
            established=True,
        )
        years = history(listed, month, annual)
        result = _computed(listed, years, month, test=FULLY)
        assert result.current_disability_period_start == onset
    for annual, end in (
        (
            {
                1938: 4,
                1939: 4,
                1940: 4,
                1941: 2,
                1961: 4,
                1962: 4,
                1963: 4,
                1964: 2,
            },
            1959,
        ),
        (
            {
                1938: 4,
                1939: 4,
                1940: 4,
                1941: 2,
                **{y: 4 for y in range(1955, 1964)},
                1964: 2,
            },
            1954,
        ),
    ):
        listed = _person(
            person.birth_date,
            i.DisabilityPeriod(date(1952, 7, 15), date(end, 12, 31)),
            onset=onset,
            established=True,
        )
        years = history(listed, month, annual)
        detail = _refused(
            Reason.ASSIGNMENT_COMPLEXITY, listed, years, month, test=FULLY
        )
        assert detail == UNSUPPORTED_PRIOR


# Published first onsets.


def _patterned(person, month, patterns):
    years = history(person, month)
    for year, pattern in patterns.items():
        flags = tuple(letter == "C" for letter in pattern)
        years[year] = i.CoverageYear(
            OBSERVED,
            **(
                {"qc_quarters": flags}
                if year < 1978
                else {"qc_count": sum(flags)}
            ),
        )
    return years


@pytest.mark.parametrize(
    "source,quote,birth,onset,patterns,counts",
    (
        (
            "poms_rs_00301_140",
            "There are 14 QTRS elapsing after the QTR of age 21 up to and "
            "including onset date. Joseph requires and has 7 QC's",
            date(1956, 9, 16),
            date(1981, 2, 3),
            {1978: "CCNN", 1979: "CCCN", 1980: "CCCC", 1981: "NNNN"},
            (14, 7, 9),
        ),
        (
            "poms_rs_00301_140",
            "Jane requires and has 6 QC's to be insured for DIB.",
            date(1967, 3, 16),
            date(1988, 3, 29),
            {1986: "CCCN", 1987: "CCCN", 1988: "NNNN"},
            (12, 6, 6),
        ),
        (
            "poms_rs_00301_140",
            "Ralph requires and has 6 QC's to be insured for DIB.",
            date(1967, 4, 12),
            date(1988, 2, 16),
            {1986: "CNNN", 1987: "CCCC", 1988: "CNNN"},
            (12, 6, 6),
        ),
        (
            "poms_rs_00301_140",
            "Sam requires and has 6 QC's to be insured for DIB.",
            date(1964, 2, 16),
            date(1985, 12, 16),
            {1983: "CCNN", 1984: "CCCC", 1985: "NNNN"},
            (12, 6, 6),
        ),
        (
            "poms_rs_00301_147",
            "Mary required 8 QCs to meet the special insured status earnings "
            "test. Mary had 8 QC's during that period",
            date(1950, 4, 16),
            date(1975, 5, 16),
            {
                1970: "NNNC",
                1971: "NNCC",
                1972: "CCCN",
                1973: "CNNC",
                1974: "NNCC",
                1975: "NNNN",
            },
            (16, 8, 9),
        ),
        (
            "poms_rs_00301_147",
            "John required 13 QC's to meet the special insured status "
            "earnings test. Since John had 13 QC's during this period",
            date(1940, 7, 16),
            date(1968, 3, 4),
            {
                1961: "NNNC",
                1962: "NCCN",
                1963: "NNCC",
                1964: "CCNC",
                1965: "NNNN",
                1966: "CCNN",
                1967: "CNCC",
                1968: "NNNN",
            },
            (26, 13, 13),
        ),
        (
            "poms_rs_00301_147",
            "There were 17 QTRs elapsing after the QTR of attainment of age "
            "21 up to and including the QTR of onset, Frank required 8 QC's",
            date(1945, 7, 14),
            date(1970, 12, 13),
            {
                1966: "NNNN",
                1967: "CNCN",
                1968: "NNCC",
                1969: "NNNC",
                1970: "CCCN",
            },
            (17, 8, 8),
        ),
    ),
    ids=(
        "rs140-joseph-6",
        "rs140-jane-7",
        "rs140-ralph-8",
        "rs140-sam-9",
        "rs147-mary-1",
        "rs147-john-2",
        "rs147-frank-3",
    ),
)
def test_each_published_first_onset_reproduces(
    source, quote, birth, onset, patterns, counts
):
    # Each example's first onset, before any prior period: the quarters
    # counted, the QCs required and the QCs the printed pattern puts there.
    # Joseph "requires and has 7" of the nine his pattern holds. Mary "had 8
    # QC's", but her pattern holds nine (1971Q3-Q4, 1972Q1-Q3, 1973Q1 and
    # Q4, 1974Q3-Q4), a slip the example registry logs.
    assert quote in source_text(source)
    person = _person(birth, onset=onset)
    month = onset.replace(day=1)
    years = _patterned(person, month, patterns)
    found = _computed(person, years, month, test=DISABILITY).disability
    assert found.insured
    assert found.rule == "under31_special"
    assert (len(found.window), found.required, found.qc_count_lower) == counts


# Lows.


def test_declared_dates_past_the_statutory_end_are_input_errors():
    # 404.321(c)(1) ends a period by the month before FRA. A June 1950 birth
    # attains FRA in June 2016, so a period ends by 2016-05-31, and the end
    # binds the current period and a listed prior alike.
    birth = date(1950, 6, 15)
    for end, valid in (
        (date(2016, 5, 31), True),
        (date(2016, 6, 30), False),
        (date(2017, 12, 31), False),
    ):
        prior = i.DisabilityPeriod(date(2010, 1, 1), end)
        if valid:
            _ended(birth, date(2010, 1, 15), end)
            _person(birth, prior)
            continue
        with pytest.raises(i.InvalidFamilyInput, match="statutory FRA end"):
            _ended(birth, date(2010, 1, 15), end)
        with pytest.raises(i.InvalidFamilyInput, match="statutory FRA end"):
            _person(birth, prior)


@pytest.mark.parametrize(
    "field,month,message",
    (
        ("dib_entitlement_month", date(2005, 7, 1), None),
        ("dib_entitlement_month", date(2005, 8, 1), "at or after FRA"),
        ("dib_entitlement_month", date(2010, 1, 1), "at or after FRA"),
        ("rib_entitlement_month", date(2002, 2, 1), None),
        ("rib_entitlement_month", date(2002, 1, 1), "before age 62"),
        ("rib_entitlement_month", date(1964, 3, 1), "before age 62"),
    ),
)
def test_entitlement_months_must_be_possible(field, month, message):
    # Born 1940-02-02, FRA arrives in August 2005 and 62 on 2002-02-01.
    if message is None:
        assert getattr(_person(date(1940, 2, 2), **{field: month}), field)
        return
    with pytest.raises(i.InvalidFamilyInput, match=message):
        _person(date(1940, 2, 2), **{field: month})


def test_the_pre_1983_refusal_needs_31_before_may_1983():
    # 404.130(c) decides a second onset before 31 under pre-1983 law too, so
    # the rule refuses only a holder whose age-31 quarter begins before May
    # 1983.
    person = _person(
        date(1956, 9, 16),
        i.DisabilityPeriod(
            date(1978, 10, 2), date(1979, 12, 31), special_insured=True
        ),
        onset=date(1982, 3, 1),
    )
    month = date(1982, 3, 1)
    years = history(
        person, month, {1976: 4, 1977: 4, 1978: 3, 1980: 2, 1981: 4}
    )
    result = _computed(person, years, month)
    assert result.disability.rule == "under31_special"
    person = _person(
        date(1950, 1, 2),
        i.DisabilityPeriod(
            date(1975, 1, 1), date(1976, 12, 31), special_insured=True
        ),
        onset=date(1982, 6, 1),
    )
    month = date(1982, 6, 1)
    years = history(
        person,
        month,
        {y: 4 for y in (*range(1971, 1975), *range(1977, 1982))},
    )
    _refused(Reason.HISTORICAL_SUBSEQUENT, person, years, month)


def test_the_requirement_helper_checks_what_insured_status_checks():
    person = _person(date(1960, 2, 2), dib_entitlement_month=date(2006, 1, 1))
    for call in (
        lambda: i.fully_insured_requirement(person, date(2005, 1, 1)),
        lambda: i.insured_status(
            person,
            history(person, date(2005, 1, 1)),
            date(2005, 1, 1),
        ),
    ):
        with pytest.raises(i.InvalidFamilyInput, match="follows query"):
            call()
    with pytest.raises(i.InvalidFamilyInput, match="outside"):
        i.fully_insured_requirement(
            _person(date(1960, 2, 2)), date(1959, 1, 1)
        )


def test_wages_paid_after_death_count_toward_the_year():
    # Act 213(a)(2)(B): no quarter after the death quarter is a QC, but the
    # $7,770 paid in 1968Q2 brings the year to the $7,800 maximum, so 1968Q1
    # becomes a QC though it holds $30.
    person = _person(date(1930, 2, 2), death_date=date(1968, 2, 15))
    month = date(1970, 1, 1)
    found = []
    for wages in ((30, 7770, 0, 0), (30, 0, 0, 0), (7700, 100, 0, 0)):
        years = history(person, month, {y: 4 for y in range(1950, 1968)})
        years[1968] = i.CoverageYear(
            OBSERVED, quarterly_wages=tuple(Fraction(w) for w in wages)
        )
        found.append(
            _computed(person, years, month, test=FULLY).qcs_by_year[1968]
        )
    assert found == [(1, 1), (0, 0), (1, 1)]


@pytest.mark.parametrize(
    "year,declared,message",
    (
        (1960, (True, False, False, False), "QCs declared before birth"),
        (1966, (False, False, False, True), "QCs declared after coverage"),
        (1966, (Fraction(0),) * 3 + (Fraction(100),), "earnings declared"),
    ),
)
def test_quarterly_bounds_name_themselves(year, declared, message):
    person = _person(date(1960, 8, 15))
    exit_month = date(1966, 8, 1)
    years = history(person, date(1968, 1, 1), end=exit_month)
    years[year] = i.CoverageYear(
        OBSERVED,
        **(
            {"qc_quarters": declared}
            if isinstance(declared[0], bool)
            else {"quarterly_wages": declared}
        ),
    )
    with pytest.raises(i.InvalidFamilyInput, match=message):
        i.insured_status(
            person, years, date(1968, 1, 1), coverage_end_month=exit_month
        )
    # The exit quarter itself takes a flag.
    years[1966] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, False, True, False)
    )
    years[1960] = i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
    result = i.insured_status(
        person,
        years,
        date(1968, 1, 1),
        test=FULLY,
        coverage_end_month=exit_month,
    )
    assert result.fully.qc_count_lower == 1


# The design note's evidence.


def test_the_note_cites_only_tests_that_exist():
    # The note names tests as its evidence, so each must still run, and it
    # cites no uncommitted scratch file. That evidence lives in the insured
    # status modules, so the check opens those and no other test file.
    tests = Path(__file__).resolve().parent
    note = (tests.parent / "docs/design/track_b_insured_status.md").read_text()
    defined = set()
    for module in tests.glob("test_track_b_insured_status*.py"):
        defined.add(module.stem)
        defined.update(
            re.findall(r"^\s*def (test_\w+)", module.read_text(), re.M)
        )
    assert sorted(set(re.findall(r"`(test_\w+)", note)) - defined) == []
    assert "scratch/" not in note


def test_the_note_check_reads_only_the_note_and_insured_modules(
    monkeypatch,
):
    # Blind roles run these modules, so the note check may list only the
    # tests folder itself and open only the note and the insured status
    # modules. The guard checks each Path listing and open before it runs.
    tests = Path(__file__).resolve().parent
    note = tests.parent / "docs/design/track_b_insured_status.md"
    path_open, glob, iterdir = Path.open, Path.glob, Path.iterdir
    opened = []

    def checked_open(path, *args, **kwargs):
        resolved = path.resolve()
        assert resolved == note or (
            resolved.parent == tests
            and resolved.name.startswith("test_track_b_insured_status")
        ), resolved
        opened.append(resolved)
        return path_open(path, *args, **kwargs)

    def flat_glob(path, pattern, *args, **kwargs):
        assert path.resolve() == tests, path
        assert "**" not in pattern and "/" not in pattern, pattern
        return glob(path, pattern, *args, **kwargs)

    def flat_iterdir(path):
        assert path.resolve() == tests, path
        return iterdir(path)

    def recursive(path, *args, **kwargs):
        raise AssertionError(f"recursive search of {path}")

    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(Path, "glob", flat_glob)
    monkeypatch.setattr(Path, "iterdir", flat_iterdir)
    monkeypatch.setattr(Path, "rglob", recursive)
    monkeypatch.setattr(Path, "walk", recursive)
    test_the_note_cites_only_tests_that_exist()
    assert note in opened and Path(__file__).resolve() in opened
