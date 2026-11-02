"""Round 17: the long subsequent-special period and the lower date.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

Act 223(c)(1)(B)(iii) and 216(i)(3)(B)(iii) count "the quarters beginning
after such individual attained age 21", with no cap. 404.130(d)(2) adds "up to
a maximum of 20 QCs out of 40 calendar quarters". Past 40 counted quarters the
Act takes half the whole period and the regulation takes 20 of the last 40, and
the rule refuses by name wherever they differ (source conflict
us:oasdi-insured-subsequent-special-long-period).

Each period ending's favorable date last insured can rest on a placement that
moves the reported start, so a lower bound must hold on every ending with that
start (404.321(a); RS 00301.230; source conflict
us:oasdi-insured-one-filling-first-start).
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import (
    InvalidFamilyInput,
    count_family_outcomes,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
LONG = i.InsuredUnsupportedReason.SUBSEQUENT_LONG_PERIOD
ASSIGNMENT = i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
WEIGHT = Fraction(5, 2)
BIRTH = date(1960, 2, 2)
ONSET = date(1991, 10, 15)
# The prior holds five full months, and neither endpoint is a QC.
SPECIAL = i.DisabilityPeriod(
    date(1983, 1, 15), date(1983, 6, 30), special_insured=True
)
# 1981Q2 through 1991Q4 leaves 41 counted quarters, so half is 20. These 20 QCs
# all sit in that period, and only 19 sit in its last 40 quarters.
TWENTY = {1981: 3, 1982: 3, 1984: 4, 1985: 4, 1986: 4, 1987: 2}
# Nineteen QCs through 1999 leave the 2000 QC to reach 20 of 40, so a first
# insured quarter of 2000Q1 holds that QC there.
LOWER_ANNUAL = {
    1995: 3,
    1996: 4,
    1997: 4,
    1998: 4,
    1999: 4,
    2000: 1,
    2001: 4,
    2002: 4,
    2003: 4,
    2004: 4,
    2005: 3,
}
TWO_FILLINGS_ANNUAL = {1979: 3, 1980: 2, 1981: 1, 1982: 3, 1984: 4}


def _history(first, last, counts):
    return {
        year: (
            i.CoverageYear(OBSERVED, qc_count=counts.get(year, 0))
            if year >= 1978
            else i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
        )
        for year in range(first, last + 1)
    }


def _person(*priors, **changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=ONSET,
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=priors,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    values.update(changes)
    return i.Person(BIRTH, **values)


def _established(*priors, **changes):
    values = dict(
        current_disability_period_established=True,
        current_disability_period_end=date(1992, 6, 30),
        current_disability_period_end_provenance=OBSERVED,
    )
    values.update(changes)
    return _person(*priors, **values)


def _rows(person, years, month, **options):
    try:
        return (
            i.evaluate_insured_status(
                "case",
                WEIGHT,
                lambda: i.insured_status(person, years, month, **options),
            ),
        )
    except InvalidFamilyInput:
        return ()


def _refused_with(reason, person, years, month, **options):
    rows = _rows(person, years, month, **options)
    assert len(rows) == 1, rows
    assert rows[0].result is None, rows[0].result
    assert rows[0].unsupported.reason is reason
    counted = count_family_outcomes(rows)
    assert (counted.rows, counted.weight) == (1, WEIGHT)
    assert (counted.unsupported_rows, counted.unsupported_weight) == (
        1,
        WEIGHT,
    )


def _result(person, years, month, **options):
    rows = _rows(person, years, month, **options)
    assert len(rows) == 1, rows
    assert rows[0].result is not None, rows[0].unsupported
    return rows[0].result


# The long subsequent-special period.


@pytest.mark.parametrize(
    "exit_month,last", ((None, 1991), (date(1987, 12, 1), 1987))
)
def test_a_long_period_refuses_where_its_readings_differ(exit_month, last):
    _refused_with(
        LONG,
        _person(SPECIAL),
        _history(1960, last, TWENTY),
        date(1991, 10, 1),
        coverage_end_month=exit_month,
    )


@pytest.mark.parametrize(
    "test", (i.InsuredTest.ALL, i.InsuredTest.FULLY, i.InsuredTest.DISABILITY)
)
@pytest.mark.parametrize(
    "exit_month,last", ((None, 1992), (date(1987, 12, 1), 1987))
)
def test_an_established_period_keeps_its_row(test, exit_month, last):
    # Only the whole-period reading insures this start, so no input error can
    # stand: 404.321(a) gives the period a start on that reading.
    _refused_with(
        LONG,
        _established(SPECIAL),
        _history(1960, last, TWENTY),
        date(1992, 12, 1),
        coverage_end_month=exit_month,
        test=test,
    )


@pytest.mark.parametrize(
    "exit_month,last", ((None, 2022), (date(2009, 12, 1), 2009))
)
def test_an_age_62_fully_request_keeps_its_row(exit_month, last):
    counts = {**TWENTY, **dict.fromkeys(range(2000, 2010), 4)}
    _refused_with(
        LONG,
        _established(SPECIAL),
        _history(1960, last, counts),
        date(2022, 3, 1),
        coverage_end_month=exit_month,
        test=i.InsuredTest.FULLY,
    )


def test_unknown_prior_history_keeps_its_row_on_the_whole_period():
    # Fixed QCs sit in 1965Q2, 1965Q3, 1967Q1 to Q3 and 1971Q3 to 1975Q2. The
    # joint proof's clock drops uncredited quarters after the first possible
    # prior, which leaves 42 quarters at 1975Q3. The 21 QCs meet half of those
    # and only 19 sit in the last 40, so the proof must not reject the row.
    person = i.Person(
        date(1944, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1975, 8, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1976, 6, 30),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=UNKNOWN,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    flags = {
        1965: (False, True, True, False),
        1967: (True, True, True, False),
        1971: (False, False, True, True),
        1972: (True,) * 4,
        1973: (True,) * 4,
        1974: (True,) * 4,
        1975: (True, True, False, False),
    }
    years = {
        year: (
            i.CoverageYear(OBSERVED, qc_quarters=flags.get(year, (False,) * 4))
            if year < 1978
            else i.CoverageYear(OBSERVED, qc_count=0)
        )
        for year in range(1944, 1977)
    }
    assert len(_rows(person, years, date(1976, 12, 1))) == 1


def test_fully_alone_needs_no_reading():
    result = _result(
        _person(SPECIAL),
        _history(1960, 1991, TWENTY),
        date(1991, 10, 1),
        test=i.InsuredTest.FULLY,
    )
    assert result.fully.insured
    assert result.dli is None


def test_a_period_without_special_status_opens_no_reading():
    result = _result(
        _person(replace(SPECIAL, special_insured=False)),
        _history(1960, 1991, TWENTY),
        date(1991, 10, 1),
    )
    assert not result.disability.insured
    assert result.disability.rule == "disability_20_of_40"


def test_nineteen_qcs_fail_on_every_reading():
    short = {**TWENTY, 1987: 1}
    result = _result(
        _person(SPECIAL), _history(1960, 1991, short), date(1991, 10, 1)
    )
    assert not result.disability.insured


def test_forty_counted_quarters_leave_one_reading():
    # 1991Q3 counts exactly 40 quarters, so the cap has nothing to do.
    onset = date(1991, 8, 15)
    result = _result(
        _person(SPECIAL, disability_onset=onset),
        _history(1960, 1991, TWENTY),
        date(1991, 8, 1),
    )
    assert result.disability.insured
    assert result.disability.rule == "subsequent_special"
    assert (result.disability.qc_count_lower, result.disability.required) == (
        20,
        20,
    )


def test_twenty_of_forty_needs_no_reading():
    counts = {**TWENTY, 1987: 4, 1988: 4, 1989: 4, 1990: 4}
    result = _result(
        _person(SPECIAL), _history(1960, 1991, counts), date(1991, 10, 1)
    )
    assert result.disability.insured


def test_a_later_date_last_insured_can_turn_on_a_reading():
    # The onset status holds on both readings, but past the 40-quarter rule's
    # last date the whole-period reading still insures.
    counts = {**TWENTY, 1987: 4, 1988: 4, 1989: 4, 1990: 4}
    _refused_with(
        LONG,
        _person(SPECIAL),
        _history(1960, 2003, counts),
        date(2003, 1, 1),
    )


def test_twenty_qcs_short_of_half_the_period_compute():
    # The 20th QC arrives in 1994, when half the 53 counted quarters is 26, and
    # the last 40 hold 10. Only a parse that drops "out of 40 calendar
    # quarters" insures this record, and the rule takes no such parse. The 14
    # QCs through 1985 last meet half in 1988Q4, where 29 quarters reduce to 28.
    counts = {1981: 3, 1982: 3, 1984: 4, 1985: 4, 1993: 4, 1994: 2}
    result = _result(
        _person(SPECIAL, disability_onset=date(1994, 11, 15)),
        _history(1960, 1994, counts),
        date(1994, 11, 1),
    )
    assert not result.disability.insured
    assert result.dli.upper == date(1988, 12, 31)


def test_poms_mary_brown_keeps_a_computed_date_last_insured():
    # RS 00301.147 C.1 prints 16 of 32 at the 11/2/82 onset and no date last
    # insured, so this rule derives the date below. In 1983Q1 the 33 quarters
    # reduce to 32. In 1983Q2 the 34 quarters need 17, and counting the prior's
    # quarters under 404.130(f) leaves 20 QCs against 24.
    patterns = {
        1970: "NNNC",
        1971: "NNCC",
        1972: "CCCN",
        1973: "CNNC",
        1974: "NNCC",
        1976: "CNNN",
        1978: "CCCC",
        1979: "CNNN",
        1980: "CNNN",
        1981: "CNNN",
        1982: "CCCN",
    }
    person = i.Person(
        date(1950, 4, 16),
        disability_onset=date(1982, 11, 2),
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(1975, 5, 16), date(1978, 12, 31), special_insured=True
            ),
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    years = {
        year: (
            i.CoverageYear(
                OBSERVED,
                qc_quarters=tuple(
                    letter == "C" for letter in patterns.get(year, "NNNN")
                ),
            )
            if year < 1978
            else i.CoverageYear(
                OBSERVED, qc_count=patterns.get(year, "").count("C")
            )
        )
        for year in range(1950, 1984)
    }
    result = _result(person, years, date(1983, 6, 1))
    assert result.disability.insured
    assert result.dli.upper == date(1983, 3, 31)


def test_counting_the_prior_quarters_reaches_the_same_refusal():
    # 404.130(f) counts the prior's quarters when that insures. Excluding them
    # leaves 7 of 17, the last 40 quarters hold 16, and the whole 47 hold 23.
    prior = i.DisabilityPeriod(
        date(1983, 1, 15), date(1990, 6, 30), special_insured=True
    )
    counts = {1981: 3, 1982: 4, 1983: 4, 1984: 4, 1985: 4, 1986: 4}
    _refused_with(
        LONG,
        _person(prior, disability_onset=date(1992, 10, 15)),
        _history(1960, 1992, counts),
        date(1992, 10, 1),
    )


def _quarter(value):
    return value.year * 4 + (value.month - 1) // 3


@settings(max_examples=300, deadline=None, derandomize=True)
@given(
    birth_year=st.integers(1905, 1990),
    birth_month=st.integers(1, 12),
    age=st.integers(31, 72),
    month=st.sampled_from((1, 4, 7, 10)),
    prior_age=st.integers(22, 30),
    span=st.integers(0, 30),
)
def test_half_a_long_period_clears_the_fully_insured_count(
    birth_year, birth_month, age, month, prior_age, span
):
    # The refusal reads no fully insured test, because half of more than 40
    # counted quarters holds at least the 404.132 requirement. No QC sits in
    # the prior here, which leaves the fewest counted quarters.
    birth = date(birth_year, birth_month, 2)
    at = date(birth_year + age, month, 1)
    start = date(birth_year + prior_age, 3, 15)
    end = date(birth_year + prior_age + span, 6, 30)
    assume(end < at)
    first = max(1937 * 4, birth_year * 4 + 84 + (birth_month - 1) // 3 + 1)
    counted = [
        quarter
        for quarter in range(first, _quarter(at) + 1)
        if not _quarter(start) <= quarter <= _quarter(end)
    ]
    assume(len(counted) > 40)
    person = i.Person(birth, sex=i.Sex.FEMALE)
    required = i._requirement(
        person, at, ((start, end),), onset=True, for_disability=True
    )
    assert len(counted) // 2 >= required


def _placed(counts, at):
    """Latest quarters through ``at``, the best for every suffix window."""
    return {
        min(year * 4 + 3, at) - offset
        for year, count in counts.items()
        if year * 4 <= at
        for offset in range(min(count, at - year * 4 + 1))
    }


def _insured(counts, at, reading):
    """One reading of 404.130(a), (b), (d) and (f), from the source text."""
    credits = _placed(counts, at)
    first = 1981 * 4 + 1
    prior = (1983 * 4, 1983 * 4 + 1)
    for excluded in (prior, ()):
        # 404.132: elapsed years stop at the year of the tested quarter.
        elapsed_years = sum(
            year != 1983 or not excluded for year in range(1982, at // 4)
        )
        if len(credits) < max(6, min(40, elapsed_years)):
            continue
        counted = [
            quarter
            for quarter in range(first - 40, at + 1)
            if quarter not in excluded
        ]
        since_21 = [quarter for quarter in counted if quarter >= first]
        recent = len(credits & set(counted[-40:]))
        if recent >= 20:
            return True
        if len(since_21) < 12:
            if len(credits & set(counted[-12:])) >= 6:
                return True
        elif len(since_21) <= 40:
            if len(credits & set(since_21)) >= len(since_21) // 2:
                return True
        elif reading == "whole_period":
            if len(credits & set(since_21)) >= len(since_21) // 2:
                return True
    return False


def _last_date(counts, at, reading):
    return next(
        (
            quarter
            for quarter in range(at, 1984 * 4 - 1, -1)
            if _insured(counts, quarter, reading)
        ),
        None,
    )


READINGS = ("last_40", "whole_period")


@settings(max_examples=250, deadline=None, derandomize=True)
@example(tail=(4, 4, 4, 2, 0, 0, 0), year=1991)
@example(tail=(4, 4, 4, 1, 0, 0, 0), year=1991)
@example(tail=(4, 4, 4, 4, 4, 4, 4), year=1991)
@example(tail=(4, 4, 4, 4, 4, 4, 4), year=2003)
@given(
    tail=st.tuples(*[st.sampled_from((0, 1, 2, 4))] * 7),
    year=st.integers(1989, 2003),
)
def test_computed_exactly_when_every_reading_agrees(tail, year):
    counts = {1981: 3, 1982: 3}
    counts.update(zip(range(1984, 1991), tail, strict=True))
    at = year * 4
    month = date(year, 1, 1)
    answers = {
        (_insured(counts, at, reading), _last_date(counts, at, reading))
        for reading in READINGS
    }
    rows = _rows(
        _person(SPECIAL, disability_onset=date(year, 1, 15)),
        _history(1960, year, counts),
        month,
    )
    assert len(rows) == 1
    if len(answers) > 1:
        assert rows[0].result is None, (answers, rows[0])
        assert rows[0].unsupported.reason is LONG
    else:
        ((insured, last),) = answers
        assert rows[0].result is not None, (answers, rows[0])
        assert rows[0].result.disability.insured == insured
        upper = rows[0].result.dli.upper
        assert (None if upper is None else _quarter(upper)) == last


# The lower date last insured.


def _lower_person(**changes):
    values = dict(
        disability_onset=date(2000, 1, 1),
        current_disability_period_established=True,
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
    )
    values.update(changes)
    return _person(**values)


@pytest.mark.parametrize("through", (None, date(2005, 12, 31)))
@pytest.mark.parametrize("exit_month", (None, date(2011, 1, 1)))
def test_every_ending_must_reach_the_lower_date(through, exit_month):
    # A 2005Q4 ending keeps the 2000Q1 start only on placements whose date is
    # 2009Q4, so a lower date of 2010Q1 speaks for a filling that can't exist.
    person = _lower_person()
    if through is not None:
        person = replace(
            person,
            current_disability_period_continues_through=through,
            current_disability_period_continues_through_provenance=OBSERVED,
        )
    _refused_with(
        ASSIGNMENT,
        person,
        _history(1960, 2010, LOWER_ANNUAL),
        date(2010, 1, 1),
        test=i.InsuredTest.DISABILITY,
        coverage_end_month=exit_month,
    )


@pytest.mark.parametrize(
    "onset,month", ((date(1999, 6, 15), date(2012, 4, 1)),)
)
def test_an_earlier_onset_reaches_the_same_check(onset, month):
    _refused_with(
        ASSIGNMENT,
        _lower_person(disability_onset=onset),
        _history(1960, month.year, LOWER_ANNUAL),
        month,
        test=i.InsuredTest.DISABILITY,
    )


def test_a_frozen_exit_reaches_the_same_check():
    person = replace(
        _lower_person(),
        current_disability_period_continues_through=date(2000, 1, 1),
        current_disability_period_continues_through_provenance=OBSERVED,
    )
    _refused_with(
        ASSIGNMENT,
        person,
        _history(1960, 2005, LOWER_ANNUAL),
        date(2027, 1, 1),
        test=i.InsuredTest.DISABILITY,
        coverage_end_month=date(2005, 12, 1),
    )


@pytest.mark.parametrize("ending", (None, date(2005, 12, 31)))
def test_unknown_prior_history_reaches_the_same_check(ending):
    # UNKNOWN priors include the completion with none, and that completion
    # holds these placements, so the lower date has to hold for it too.
    person = replace(
        _lower_person(), prior_disability_periods_provenance=UNKNOWN
    )
    if ending is not None:
        person = replace(
            person,
            current_disability_period_end=ending,
            current_disability_period_end_provenance=OBSERVED,
        )
    _refused_with(
        ASSIGNMENT,
        person,
        _history(1960, 2010, LOWER_ANNUAL),
        date(2010, 1, 1),
        test=i.InsuredTest.DISABILITY,
    )


def test_a_fixed_start_needs_no_placement_search():
    # Forty early QCs insure the start on every placement, and ten years of
    # two QCs each hold more placements than the search would ever try.
    counts = dict.fromkeys(range(1985, 1996), 4)
    counts.update(dict.fromkeys(range(1996, 2006), 2))
    result = _result(
        _lower_person(),
        _history(1960, 2010, counts),
        date(2010, 1, 1),
        test=i.InsuredTest.DISABILITY,
    )
    assert result.current_disability_period_start == date(2000, 1, 1)
    assert result.dli.lower is not None


def _settle(monkeypatch, fillings, lowest):
    """Run the settlement on written-out dates, one tuple per filling."""
    monkeypatch.setattr(i, "_start_fixed", lambda *args: False)
    monkeypatch.setattr(
        i,
        "_fillings_keeping_start",
        lambda *args: ((dates, None) for dates in fillings),
    )
    monkeypatch.setattr(
        i,
        "_period_outcomes",
        lambda person, completed, start, filling, *rest: (
            ((), last, ()) for last in filling
        ),
    )
    i._settle_lower_date(
        _lower_person(), {}, date(2000, 1, 1), None, None, lowest, frozenset()
    )


def test_each_ending_can_reach_the_date_on_its_own_filling(monkeypatch):
    early, late = date(2009, 12, 31), date(2010, 3, 31)
    _settle(monkeypatch, ((early, late), (late, early)), late)


def test_a_record_can_need_a_different_filling_for_each_ending():
    # No one placement holds this date on every ending, and each ending holds
    # it on a placement of its own, so the date stands.
    result = _result(
        _lower_person(disability_onset=date(1982, 8, 15)),
        _history(1960, 1989, TWO_FILLINGS_ANNUAL),
        date(1989, 1, 1),
        test=i.InsuredTest.DISABILITY,
    )
    assert result.dli.lower == date(1985, 9, 30)


def test_an_ending_with_no_date_reaches_nothing(monkeypatch):
    with pytest.raises(i.InsuredConfigurationUnsupported):
        _settle(monkeypatch, ((None, date(2010, 3, 31)),), date(2009, 12, 31))


def test_a_lower_date_every_ending_reaches_computes():
    # Fixed credits leave one placement, so each ending keeps its own date.
    counts = dict.fromkeys(range(1990, 2005), 4)
    result = _result(
        _lower_person(),
        _history(1960, 2010, counts),
        date(2010, 1, 1),
        test=i.InsuredTest.DISABILITY,
    )
    assert result.current_disability_period_start == date(2000, 1, 1)
    assert result.dli.lower is not None
    assert result.dli.lower <= result.dli.upper


def test_unknown_years_reach_the_same_check():
    # Unknown 2006 credits can only raise the date, so the lower world alone
    # decides the bound, and it holds the same placements.
    years = _history(1960, 2010, LOWER_ANNUAL)
    years[2006] = i.CoverageYear(UNKNOWN)
    _refused_with(
        ASSIGNMENT,
        _lower_person(),
        years,
        date(2010, 1, 1),
        test=i.InsuredTest.DISABILITY,
    )
