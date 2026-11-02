"""Round 18: UNKNOWN priors and the current freeze.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

UNKNOWN priors stand for every prior history. 404.130(f) and RS 00301.120
count all periods or disregard all of them. Counting an added prior can take a
credited quarter from the record, and disregarding it drops the current period
too. Only the disregard speaks for every history, so a reported status or
lower date needs one filling with the reported start that attains it with no
period in force (404.321(a); RS 00301.230; source conflict
us:oasdi-insured-one-filling-first-start).
"""

from dataclasses import replace
from datetime import date

import pytest

from populace_dynamics.track_b import insured_status as i
from tests.test_track_b_insured_status_fix_round_17 import (
    ASSIGNMENT,
    LOWER_ANNUAL,
    OBSERVED,
    UNKNOWN,
    _history,
    _lower_person,
    _person,
    _refused_with,
    _result,
)

DISABILITY = i.InsuredTest.DISABILITY
CURRENTLY = i.InsuredTest.CURRENTLY
# The 2000Q1 start needs the QC of 2000 in that quarter, and the 13 quarters
# through 2003Q2 then hold five QCs with no period in force. The freeze lifts
# them, and a prior over 1996 to 1999 takes that lift away.
FREEZE_ANNUAL = {
    1986: 4,
    1987: 4,
    1992: 1,
    1996: 4,
    1997: 4,
    1998: 4,
    1999: 4,
    2000: 1,
    2001: 4,
    2002: 1,
}


def _unknown_priors(end=date(2007, 12, 31), **changes):
    return _lower_person(
        prior_disability_periods_provenance=UNKNOWN,
        current_disability_period_end=end,
        current_disability_period_end_provenance=OBSERVED,
        **changes,
    )


def _unknown_ending(through=date(2007, 12, 31)):
    return _lower_person(
        prior_disability_periods_provenance=UNKNOWN,
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=OBSERVED,
    )


def _unknown_year(year):
    years = _history(1960, 2010, LOWER_ANNUAL)
    years[year] = i.CoverageYear(UNKNOWN)
    return years


# The lower date.


@pytest.mark.parametrize(
    "person,years",
    (
        (_unknown_priors(), _history(1960, 2010, LOWER_ANNUAL)),
        (_unknown_ending(), _history(1960, 2010, LOWER_ANNUAL)),
        (_unknown_priors(), _unknown_year(2007)),
        (_unknown_ending(), _unknown_year(2007)),
    ),
    ids=("known_end", "unknown_end", "unknown_year", "unknown_end_and_year"),
)
def test_the_freeze_cannot_carry_a_lower_date(person, years):
    # A prior over 1999Q2 to 1999Q4 begins fully insured. With the 2000 QC in
    # 2000Q1, counting both periods leaves 19 QCs, and disregarding both leaves
    # 19 in the quarters through 2010Q1, so 2010-03-31 overstates that history.
    _refused_with(ASSIGNMENT, person, years, date(2010, 1, 1), test=DISABILITY)


@pytest.mark.parametrize("person", (_unknown_priors(), _unknown_ending()))
def test_a_frozen_exit_cannot_carry_it_either(person):
    _refused_with(
        ASSIGNMENT,
        person,
        _history(1960, 2005, LOWER_ANNUAL),
        date(2027, 1, 1),
        test=DISABILITY,
        coverage_end_month=date(2005, 12, 1),
    )


def test_a_date_with_no_period_in_force_computes():
    # A fourth 2005 QC gives the quarters through 2010Q1 their 20 with the
    # 2000 QC in 2000Q1, so every prior history holds this date.
    result = _result(
        _unknown_priors(),
        _history(1960, 2010, {**LOWER_ANNUAL, 2005: 4}),
        date(2010, 1, 1),
        test=DISABILITY,
    )
    assert result.current_disability_period_start == date(2000, 1, 1)
    assert result.dli.lower == date(2010, 3, 31)


def test_every_ending_shares_that_date():
    # With no period in force the ending changes nothing.
    result = _result(
        _unknown_ending(through=date(2000, 1, 1)),
        _history(1960, 2010, {**LOWER_ANNUAL, 2005: 4}),
        date(2010, 1, 1),
        test=DISABILITY,
    )
    assert result.dli.lower == date(2010, 3, 31)


def test_a_known_history_keeps_the_freeze():
    # An OBSERVED empty history has no added prior to fear, and the current
    # period carries the date on the same placements.
    result = _result(
        _lower_person(
            current_disability_period_end=date(2007, 12, 31),
            current_disability_period_end_provenance=OBSERVED,
        ),
        _history(1960, 2010, LOWER_ANNUAL),
        date(2010, 1, 1),
        test=DISABILITY,
    )
    assert result.dli.lower == date(2010, 3, 31)


def test_a_fixed_start_needs_no_search_on_unknown_priors(monkeypatch):
    def no_search(*args):
        raise AssertionError("A fixed start needs no placement search")

    monkeypatch.setattr(i, "_fillings_keeping_start", no_search)
    counts = dict.fromkeys(range(1985, 1996), 4)
    counts.update(dict.fromkeys(range(1996, 2006), 2))
    result = _result(
        _unknown_priors(),
        _history(1960, 2010, counts),
        date(2010, 1, 1),
        test=DISABILITY,
    )
    assert result.dli.lower is not None


# The statuses.


def _freeze_person(**changes):
    values = dict(
        disability_onset=date(2000, 1, 1),
        current_disability_period_established=True,
        current_disability_period_end=date(2002, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=UNKNOWN,
    )
    values.update(changes)
    return replace(_person(**values), birth_date=date(1970, 2, 2))


@pytest.mark.parametrize("test", (i.InsuredTest.ALL, CURRENTLY))
@pytest.mark.parametrize("unknown_end", (False, True))
def test_a_status_resting_on_the_freeze_refuses(test, unknown_end):
    person = _freeze_person()
    if unknown_end:
        person = _freeze_person(
            current_disability_period_end=None,
            current_disability_period_end_provenance=UNKNOWN,
        )
    _refused_with(
        ASSIGNMENT,
        person,
        _history(1970, 2003, FREEZE_ANNUAL),
        date(2003, 4, 1),
        test=test,
    )


def test_a_status_with_no_period_in_force_computes():
    result = _result(
        _freeze_person(),
        _history(1970, 2003, {**FREEZE_ANNUAL, 2002: 2}),
        date(2003, 4, 1),
        test=CURRENTLY,
    )
    assert result.current_disability_period_start == date(2000, 1, 1)
    assert result.currently.insured


def test_a_known_history_keeps_the_status():
    result = _result(
        _freeze_person(prior_disability_periods_provenance=OBSERVED),
        _history(1970, 2003, FREEZE_ANNUAL),
        date(2003, 4, 1),
        test=CURRENTLY,
    )
    assert result.current_disability_period_start == date(2000, 1, 1)
    assert result.currently.insured
