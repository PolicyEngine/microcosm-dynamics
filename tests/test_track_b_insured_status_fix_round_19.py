"""Round 19: a period's own start limits the placements.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

A period begins in a quarter its holder was insured (404.320(b)(2), 404.321(a)),
so a period can force an annual QC into one quarter (RS 00301.230; source
conflict us:oasdi-insured-one-filling-first-start). Past blindness asks only
for fully insured status (404.130(e)), and a special prior's holder "were only
insured under paragraph (c)" (404.130(d)(1)).

UNKNOWN priors and UNKNOWN establishment stand for periods no one has placed,
so no filling chosen here speaks for every completion. Disregarding all periods
stays open on any placement (404.130(f), RS 00301.120), so a result stands when
every placement attains it with no period in force. A listed prior can stand
on some placements only, so one filling of its years must keep it and attain
the result, or the rule refuses by name.
"""

from dataclasses import replace
from datetime import date

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from tests.test_track_b_insured_status_fix_round_17 import (
    ASSIGNMENT,
    OBSERVED,
    UNKNOWN,
    _history,
    _person,
    _refused_with,
    _result,
)
from tests.test_track_b_insured_status_status_stress import (
    disability,
    last_insured,
    placements,
    quarter,
    recent,
    requirement,
    usable,
)

ALL = i.InsuredTest.ALL
FULLY = i.InsuredTest.FULLY
CURRENTLY = i.InsuredTest.CURRENTLY
DISABILITY = i.InsuredTest.DISABILITY
START = date(2000, 1, 1)
# Fourteen QCs precede 1998, and a prior beginning 1998Q1 needs 15, so it holds
# the 1998 QC in that quarter. The 40 quarters through 2008Q1 then hold 19.
DATE_BIRTH = date(1961, 2, 2)
DATE_ANNUAL = {
    1991: 2,
    1992: 4,
    1993: 4,
    1994: 4,
    1998: 1,
    1999: 4,
    2000: 4,
    2001: 4,
    2002: 4,
    2003: 3,
}
DATE_PRIOR = i.DisabilityPeriod(date(1998, 1, 1), date(1999, 12, 31))
# Five QCs precede 1990, and a prior beginning 1990Q1 needs six. With that QC
# out of the 40 quarters through 2000Q1, a 2000Q1 start needs the 2000 QC there,
# and the 13 quarters through 2003Q2 then hold five.
STATUS_BIRTH = date(1965, 2, 2)
STATUS_ANNUAL = {
    1986: 4,
    1987: 1,
    1990: 1,
    1995: 3,
    1996: 4,
    1997: 4,
    1998: 4,
    1999: 4,
    2000: 1,
    2001: 4,
    2002: 1,
}
STATUS_PRIOR = i.DisabilityPeriod(date(1990, 1, 1), date(1999, 12, 31))
# Only the 2000 QC in 2000Q1 reaches 20 of 40 in any quarter through 2003Q2.
ESTABLISH_ANNUAL = {
    1990: 4,
    1991: 4,
    1992: 4,
    1993: 4,
    1994: 4,
    2000: 1,
    2001: 4,
    2002: 1,
}


def _date_person(**changes):
    values = dict(
        disability_onset=START,
        current_disability_period_established=True,
        current_disability_period_end=date(2000, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=UNKNOWN,
    )
    values.update(changes)
    return replace(_person(**values), birth_date=DATE_BIRTH)


def _status_person(**changes):
    values = dict(
        disability_onset=START,
        current_disability_period_established=True,
        current_disability_period_end=date(2002, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        current_disability_period_continues_through=START,
        current_disability_period_continues_through_provenance=OBSERVED,
        prior_disability_periods_provenance=UNKNOWN,
    )
    values.update(changes)
    return replace(_person(**values), birth_date=STATUS_BIRTH)


UNKNOWN_END = dict(
    current_disability_period_end=None,
    current_disability_period_end_provenance=UNKNOWN,
    current_disability_period_continues_through=date(2000, 12, 31),
    current_disability_period_continues_through_provenance=OBSERVED,
)
UNKNOWN_ESTABLISHMENT = dict(
    current_disability_period_established=None,
    current_disability_period_provenance=UNKNOWN,
    current_disability_period_end=None,
    current_disability_period_end_provenance=UNKNOWN,
)


def _unknown_year(years, year):
    return {**years, year: i.CoverageYear(UNKNOWN)}


# UNKNOWN priors: the date.


def test_that_prior_holds_the_date_at_2007q4():
    prior = (DATE_PRIOR.start, DATE_PRIOR.end)
    current = (START, date(2000, 12, 31))
    at = quarter(date(2008, 1, 1))
    held = [
        credits
        for credits in placements(DATE_ANNUAL)
        if disability(DATE_BIRTH, credits, quarter(prior[0]), (), True)
    ]
    assert len(held) == 24
    for credits in held:
        assert disability(DATE_BIRTH, credits, quarter(START), (), False)
        use = usable(credits, at, (prior, current))
        assert recent(usable(credits, at, ()), at, (), 40) == 19
        assert recent(use, at, (prior, current), 40) == 15
        best = max(
            last_insured(DATE_BIRTH, credits, at, periods, False, False, None)
            for periods in ((), (prior, current))
        )
        assert best == 2007 * 4 + 3


@pytest.mark.parametrize(
    "changes,unknown_year",
    (
        ({}, None),
        (dict(disability_onset=date(2000, 1, 15)), None),
        (UNKNOWN_END, None),
        ({}, 2004),
        (UNKNOWN_END, 2004),
        (UNKNOWN_ESTABLISHMENT, None),
        (UNKNOWN_ESTABLISHMENT, 2004),
    ),
    ids=(
        "known_end",
        "onset_day_15",
        "unknown_end",
        "unknown_year",
        "unknown_end_and_year",
        "unknown_establishment",
        "unknown_establishment_and_year",
    ),
)
def test_a_prior_can_undercut_the_date(changes, unknown_year):
    years = _history(1961, 2008, DATE_ANNUAL)
    if unknown_year is not None:
        years = _unknown_year(years, unknown_year)
    _refused_with(
        ASSIGNMENT,
        _date_person(**changes),
        years,
        date(2008, 1, 1),
        test=DISABILITY,
    )


@pytest.mark.parametrize(
    "changes", ({}, UNKNOWN_END), ids=("known", "unknown")
)
def test_a_frozen_exit_keeps_the_same_refusal(changes):
    _refused_with(
        ASSIGNMENT,
        _date_person(**changes),
        _history(1961, 2003, DATE_ANNUAL),
        date(2027, 1, 1),
        test=DISABILITY,
        coverage_end_month=date(2003, 12, 1),
    )


def test_a_date_on_every_placement_computes():
    # Four 1998 QCs leave 22 of the 40 quarters through 2008Q1 on every
    # placement.
    result = _result(
        _date_person(),
        _history(1961, 2008, {**DATE_ANNUAL, 1998: 4}),
        date(2008, 1, 1),
        test=DISABILITY,
    )
    assert result.current_disability_period_start == START
    assert result.dli.lower == date(2008, 3, 31)


# UNKNOWN priors: the statuses.


def test_that_prior_denies_the_status():
    prior = (STATUS_PRIOR.start, STATUS_PRIOR.end)
    current = (START, date(2002, 12, 31))
    at = quarter(date(2003, 4, 1))
    held = [
        credits
        for credits in placements(STATUS_ANNUAL)
        if disability(STATUS_BIRTH, credits, quarter(prior[0]), (), True)
        and disability(STATUS_BIRTH, credits, quarter(START), (), False)
    ]
    assert len(held) == 64
    for credits in held:
        for periods in ((), (prior, current)):
            use = usable(credits, at, periods)
            assert recent(use, at, periods, 13) < 6


@pytest.mark.parametrize("test", (ALL, CURRENTLY))
@pytest.mark.parametrize(
    "changes",
    ({}, dict(disability_onset=date(2000, 1, 15))),
    ids=("first_day", "day_15"),
)
def test_a_prior_can_undercut_the_status(test, changes):
    if "disability_onset" in changes:
        changes = {
            **changes,
            "current_disability_period_continues_through": changes[
                "disability_onset"
            ],
        }
    _refused_with(
        ASSIGNMENT,
        _status_person(**changes),
        _history(1965, 2003, STATUS_ANNUAL),
        date(2003, 4, 1),
        test=test,
    )


def test_a_frozen_exit_reaches_the_status():
    _refused_with(
        ASSIGNMENT,
        _status_person(),
        _history(1965, 2003, STATUS_ANNUAL),
        date(2003, 4, 1),
        test=CURRENTLY,
        coverage_end_month=date(2003, 4, 1),
    )


def test_a_status_on_every_placement_computes():
    result = _result(
        _status_person(),
        _history(1965, 2003, {**STATUS_ANNUAL, 2000: 2}),
        date(2003, 4, 1),
        test=CURRENTLY,
    )
    assert result.current_disability_period_start is None
    assert result.currently.insured


# The start.

START_EDGE = {
    1995: 3,
    **dict.fromkeys(range(1996, 2000), 4),
    2000: 1,
    **dict.fromkeys(range(2001, 2008), 4),
}


@pytest.mark.parametrize("test", (FULLY, CURRENTLY))
def test_a_start_some_placement_moves_stays_open(test):
    # The 2000 QC reaches 20 of 40 in 2000Q1 only there, and the 1995 QCs can
    # fall past the back edge. Every placement still holds the status.
    result = _result(
        _date_person(),
        _history(1961, 2008, START_EDGE),
        date(2008, 1, 1),
        test=test,
    )
    assert result.current_disability_period_start is None
    assert "current_disability_period_start" in result.unknown_facts


def test_a_status_stands_at_the_quarter_it_reports():
    # Every placement reaches 20 of 40 by 2001Q4. The result reports 2000Q1,
    # the first favorable quarter, and only some placements hold that one.
    _refused_with(
        ASSIGNMENT,
        _date_person(),
        _history(1961, 2002, START_EDGE),
        date(2002, 1, 1),
        test=DISABILITY,
    )


def test_a_fixed_start_is_the_onset():
    result = _result(
        _date_person(),
        _history(1961, 2008, dict.fromkeys(range(1985, 2008), 4)),
        date(2008, 1, 1),
    )
    assert result.current_disability_period_start == START
    assert "current_disability_period_start" not in result.unknown_facts


# UNKNOWN establishment, with no prior.


def _open_person(**changes):
    values = dict(
        disability_onset=START,
        prior_disability_periods_provenance=OBSERVED,
        **{
            key: value
            for key, value in UNKNOWN_ESTABLISHMENT.items()
            if key not in changes
        },
    )
    values.update(changes)
    return replace(_person(**values), birth_date=STATUS_BIRTH)


def test_a_period_on_that_record_holds_the_qc_at_2000q1():
    at = quarter(date(2003, 4, 1))
    horizon = range(quarter(START), at + 1)
    held = [
        credits
        for credits in placements(ESTABLISH_ANNUAL)
        if any(
            disability(STATUS_BIRTH, credits, candidate, (), False)
            for candidate in horizon
        )
    ]
    assert held
    for credits in held:
        assert 2000 * 4 in credits
        assert recent(usable(credits, at, ()), at, (), 13) == 5
    assert any(
        recent(usable(credits, at, ()), at, (), 13) == 6
        for credits in placements(ESTABLISH_ANNUAL)
    )


@pytest.mark.parametrize("test", (ALL, CURRENTLY))
def test_unknown_establishment_alone_refuses(test):
    _refused_with(
        ASSIGNMENT,
        _open_person(),
        _history(1965, 2003, ESTABLISH_ANNUAL),
        date(2003, 4, 1),
        test=test,
    )


def test_a_known_absence_keeps_the_status():
    # With no period declared, nothing holds the 2000 QC in 2000Q1.
    result = _result(
        _open_person(
            current_disability_period_established=False,
            current_disability_period_provenance=OBSERVED,
            current_disability_period_end=None,
            current_disability_period_end_provenance=UNKNOWN,
        ),
        _history(1965, 2003, ESTABLISH_ANNUAL),
        date(2003, 4, 1),
        test=CURRENTLY,
    )
    assert result.currently.insured


def test_unknown_establishment_needs_the_disregard():
    # Counting the listed prior reaches back through 1995 for seven of 13, and
    # the disregard finds three. A period on this record joins that prior in
    # any count, so the listed prior alone can't carry the status. The 1990 QCs
    # give that prior the ten fully insured status asks at its start.
    annual = {
        1990: 4,
        1995: 4,
        1996: 2,
        2000: 1,
        2001: 1,
        2002: 1,
        2003: 1,
        2004: 1,
    }
    prior = i.DisabilityPeriod(date(1997, 1, 1), date(2003, 12, 31))
    _refused_with(
        ASSIGNMENT,
        _open_person(
            disability_onset=date(2004, 6, 15),
            prior_disability_periods=(prior,),
        ),
        _history(1965, 2005, annual),
        date(2005, 1, 1),
        test=CURRENTLY,
    )


def test_unknown_establishment_leaves_a_split_prior_to_the_proof():
    # The 1998 QC splits the listed prior, and every placement attains this
    # result with no period in force, so the prior can't move it.
    annual = {**DATE_ANNUAL, **dict.fromkeys(range(2004, 2008), 4)}
    result = _result(
        _date_person(
            **UNKNOWN_ESTABLISHMENT,
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, annual),
        date(2008, 1, 1),
    )
    assert result.dli.lower == date(2008, 3, 31)


# Listed priors.


def test_a_listed_prior_can_undercut_the_date():
    _refused_with(
        ASSIGNMENT,
        _date_person(
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )


def test_a_listed_prior_can_undercut_the_status():
    _refused_with(
        ASSIGNMENT,
        _status_person(
            prior_disability_periods=(STATUS_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1965, 2003, STATUS_ANNUAL),
        date(2003, 4, 1),
        test=CURRENTLY,
    )


def test_a_listed_prior_binds_without_a_current_period():
    _refused_with(
        ASSIGNMENT,
        _date_person(
            current_disability_period_established=False,
            current_disability_period_end=None,
            current_disability_period_end_provenance=UNKNOWN,
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )


def test_a_prior_limits_what_a_status_reports():
    # The prior holds the 1990 QC in 1990Q1. The 40 quarters through 2000Q1
    # then hold 1995's three, 16 more through 1999 and the 2000 QC, so 20 and
    # not the 21 that a later 1990 QC would give.
    result = _result(
        _status_person(
            prior_disability_periods=(STATUS_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1965, 2003, {**STATUS_ANNUAL, 2002: 2}),
        date(2003, 4, 1),
    )
    assert result.current_disability_period_start == START
    assert result.assigned_quarters[1990] == (1990 * 4,)
    assert result.disability.qc_count_lower == 20


def test_a_prior_holds_a_qc_in_its_first_quarter():
    # Six of 12 through 1988Q1 need the 1988 QC in that quarter. The result
    # rests on 1993 to 1996, so that placement costs it nothing.
    prior = i.DisabilityPeriod(
        date(1988, 2, 16), date(1990, 12, 31), special_insured=True
    )
    annual = {1986: 1, 1987: 4, 1988: 1, 1993: 2, 1994: 3, 1995: 4, 1996: 3}
    result = _result(
        replace(
            _person(prior, disability_onset=date(1997, 3, 16)),
            birth_date=date(1967, 4, 12),
        ),
        _history(1967, 1997, annual),
        date(1997, 3, 1),
    )
    assert result.assigned_quarters[1988] == (1988 * 4,)
    assert result.disability.insured
    assert result.disability.qc_count_lower == 12


def test_a_prior_reaches_a_year_the_start_cannot():
    # The 12 quarters through 1988Q1 hold six only with the 1985 QC after
    # 1985Q1, and the 13 through the entitlement month hold six only with it
    # there. Only the flagged prior brings 1985 into the first-start search.
    prior = i.DisabilityPeriod(
        date(1988, 1, 15), date(1990, 12, 31), special_insured=True
    )
    annual = {
        1983: 2,
        1984: 3,
        1985: 1,
        1986: 1,
        1987: 4,
        **dict.fromkeys(range(1991, 2003), 4),
    }
    _refused_with(
        ASSIGNMENT,
        replace(
            _person(
                prior,
                disability_onset=date(2000, 1, 15),
                current_disability_period_established=True,
                current_disability_period_end=date(2002, 12, 31),
                current_disability_period_end_provenance=OBSERVED,
                dib_entitlement_month=date(1985, 1, 1),
            ),
            birth_date=date(1965, 2, 2),
        ),
        _history(1965, 2003, annual),
        date(2003, 4, 1),
        test=CURRENTLY,
    )


# 26 elapsed years ask for 26 QCs at 1998Q1, and 25 precede 1998, so the
# prior holds the 1998 QC in that quarter. A long ending's freeze reaches the
# 1990s, and the shortest leaves 18 or 19 QCs at 2008Q1 either way.
EVERY_ENDING_BIRTH = date(1950, 2, 2)
EVERY_ENDING_ANNUAL = {
    **dict.fromkeys(range(1991, 1997), 4),
    1997: 1,
    1998: 1,
    **dict.fromkeys(range(1999, 2003), 4),
    2003: 3,
}


def test_the_shortest_ending_misses_2008q1_on_that_prior():
    prior = (DATE_PRIOR.start, DATE_PRIOR.end)
    short = (START, date(2000, 12, 31))
    at = quarter(date(2008, 1, 1))
    held = [
        credits
        for credits in placements(EVERY_ENDING_ANNUAL)
        if disability(EVERY_ENDING_BIRTH, credits, quarter(prior[0]), (), True)
    ]
    assert len(held) == 16
    for credits in held:
        assert 1998 * 4 in credits
        for periods in ((), (prior, short)):
            assert recent(usable(credits, at, periods), at, periods, 40) < 20


def test_a_listed_prior_holds_every_ending_to_the_date():
    # Every ending keeps the onset start, and the lower date has to hold on
    # the fillings the prior allows for each of them.
    _refused_with(
        ASSIGNMENT,
        replace(
            _person(
                DATE_PRIOR,
                disability_onset=START,
                current_disability_period_established=True,
                current_disability_period_end=None,
                current_disability_period_end_provenance=UNKNOWN,
                current_disability_period_continues_through=date(2000, 12, 31),
                current_disability_period_continues_through_provenance=(
                    OBSERVED
                ),
            ),
            birth_date=EVERY_ENDING_BIRTH,
        ),
        _history(1950, 2008, EVERY_ENDING_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )


def test_a_prior_every_placement_supports_binds_nothing():
    # By 1999Q1 the 1998 QC has fallen on every placement, and 16 QCs meet the
    # 16 required, so the prior leaves the 1998 QC free.
    prior = i.DisabilityPeriod(date(1999, 1, 1), date(1999, 12, 31))
    result = _result(
        _date_person(
            prior_disability_periods=(prior,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )
    assert result.dli.upper == date(2008, 3, 31)


def test_a_prior_no_placement_supports_refuses():
    # Nine QCs are required at 1992Q1 and three can fall by then. The prior
    # rests on credits or facts the record omits, and those could move the
    # other results.
    prior = i.DisabilityPeriod(date(1992, 1, 1), date(1992, 12, 31))
    _refused_with(
        ASSIGNMENT,
        _date_person(
            prior_disability_periods=(prior,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )


def test_a_later_prior_can_rest_on_an_earlier_one():
    # 14 QCs fall by 1998Q1 on every placement, and only counting the 1995
    # prior brings the requirement down to them. The filling then leaves the
    # start to the QCs of 2000: 14 and the 1999 four miss 20 at 2000Q1.
    earlier = i.DisabilityPeriod(date(1995, 1, 1), date(1995, 12, 31))
    annual = {year: n for year, n in DATE_ANNUAL.items() if year != 1998}
    result = _result(
        _date_person(
            prior_disability_periods=(earlier, DATE_PRIOR),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, annual),
        date(2008, 1, 1),
        test=DISABILITY,
    )
    assert result.current_disability_period_start == date(2000, 4, 1)
    assert result.disability.insured


def test_a_later_prior_counts_the_earlier_one_on_every_filling():
    # Counting the 1995 prior lowers the 1998Q1 requirement to 14, which every
    # placement meets, so the 1998 QC stays free. The worst filling reads no
    # period in force and asks for 15, and that alone would refuse.
    earlier = i.DisabilityPeriod(date(1995, 1, 1), date(1995, 12, 31))
    result = _result(
        _date_person(
            prior_disability_periods=(earlier, DATE_PRIOR),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=DISABILITY,
    )
    assert result.dli.upper == date(2008, 3, 31)


@pytest.mark.parametrize(
    "annual",
    (
        DATE_ANNUAL,
        {year: n for year, n in DATE_ANNUAL.items() if year != 1998},
    ),
    ids=("every_needs_lower_credits", "some_needs_upper_credits"),
)
def test_an_unknown_year_reaches_a_listed_prior(annual):
    # UNKNOWN 1997 credits run from none, where no placement or only some pass
    # 1998Q1, to four, where all do.
    _refused_with(
        ASSIGNMENT,
        _date_person(
            current_disability_period_established=False,
            current_disability_period_end=None,
            current_disability_period_end_provenance=UNKNOWN,
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _unknown_year(_history(1961, 2008, annual), 1997),
        date(2008, 1, 1),
        test=FULLY,
    )


# A listed special prior.

SPECIAL_START = date(1990, 4, 1)
SPECIAL_BASE = dict.fromkeys(range(1985, 1990), 4)
SPECIAL_BASE[1985] = 2


def _special_person():
    prior = i.DisabilityPeriod(
        SPECIAL_START, date(1991, 12, 31), special_insured=True
    )
    return _person(prior, disability_onset=None)


def test_a_special_prior_needs_a_quarter_of_its_route():
    # Eighteen of 37 elapsed quarters are required. One QC below that, a 1990
    # QC has to fall by 1990Q2.
    result = _result(
        _special_person(),
        _history(1960, 1995, {**SPECIAL_BASE, 1985: 1, 1990: 2}),
        date(1995, 1, 1),
    )
    assert result.assigned_quarters[1990][0] <= 1990 * 4 + 1


def test_a_special_prior_stays_short_of_the_ordinary_rule():
    # Eighteen QCs pass the route on every placement, and two more in the
    # first quarters of 1990 reach 20 of 40. 404.130(d)(1) asks for a holder
    # "only insured" under paragraph (c), so one 1990 QC falls after 1990Q2.
    result = _result(
        _special_person(),
        _history(1960, 1995, {**SPECIAL_BASE, 1990: 2}),
        date(1995, 1, 1),
    )
    held = [q for q in result.assigned_quarters[1990] if q <= 1990 * 4 + 1]
    assert len(held) == 1


def test_a_special_prior_on_every_placement_binds_nothing():
    # One 1990 QC can't reach 20 of 40, and 18 pass the route on every
    # placement.
    result = _result(
        _special_person(),
        _history(1960, 1995, {**SPECIAL_BASE, 1990: 1}),
        date(1995, 1, 1),
    )
    assert result.fully.insured


def test_a_special_prior_no_placement_supports_refuses():
    # Twenty QCs reach 20 of 40 on every placement, so the holder was never
    # "only insured" under paragraph (c).
    _refused_with(
        ASSIGNMENT,
        _special_person(),
        _history(1960, 1995, {**SPECIAL_BASE, 1985: 4}),
        date(1995, 1, 1),
    )


def test_a_special_prior_short_of_its_route_refuses():
    # Seventeen QCs miss the 18 required on every placement.
    _refused_with(
        ASSIGNMENT,
        _special_person(),
        _history(1960, 1995, {**SPECIAL_BASE, 1985: 1}),
        date(1995, 1, 1),
    )


# The worst filling.


def _credits(annual):
    return {
        year: i._credits(year, i.CoverageYear(OBSERVED, qc_count=count), False)
        for year, count in annual.items()
    }


YEARS = st.integers(1985, 2004)
ANNUAL = st.builds(
    lambda full, partial: {**dict.fromkeys(full, 4), **partial},
    st.sets(YEARS, min_size=3, max_size=14),
    st.dictionaries(YEARS, st.integers(1, 3), max_size=3),
)


@settings(max_examples=150, deadline=None, derandomize=True)
@given(
    annual=ANNUAL,
    back=st.integers(0, 80),
    blind=st.booleans(),
    birth_year=st.integers(1945, 1975),
)
def test_the_worst_filling_matches_every_placement(
    annual, back, blind, birth_year
):
    birth = date(birth_year, 2, 2)
    at = 2004 * 4 + 3 - back
    assume(at >= (birth_year + 22) * 4)
    day = date(at // 4, 3 * (at % 4) + 1, 1)
    person = i.Person(
        birth,
        sex=i.Sex.FEMALE,
        statutory_blindness=blind,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2005, 1, 1)
    every = {
        FULLY: all(
            len(usable(c, at, ())) >= requirement(birth, at // 4, ())
            for c in placements(annual)
        ),
        CURRENTLY: all(
            recent(usable(c, at, ()), at, (), 13) >= 6
            for c in placements(annual)
        ),
        DISABILITY: all(
            disability(birth, c, at, (), blind) for c in placements(annual)
        ),
    }
    for kind, expected in every.items():
        assert (
            i._every_placement_passes(
                person, _credits(annual), day, month, None, kind
            )
            is expected
        ), (annual, day, kind)


def _lawful_prior(birth, credits, begins, special, blind=True):
    at = quarter(begins)
    if not special:
        return disability(birth, credits, at, (), blind)
    return (
        disability(birth, credits, at, (), False)
        and recent(usable(credits, at, ()), at, (), 40) < 20
    )


@settings(max_examples=150, deadline=None, derandomize=True)
@given(
    annual=ANNUAL,
    begins_year=st.integers(1986, 1995),
    begins_quarter=st.integers(0, 3),
    special=st.booleans(),
)
def test_placement_binds_a_prior_only_when_it_splits_them(
    annual, begins_year, begins_quarter, special
):
    birth = date(1960, 2, 2)
    begins = date(begins_year, 3 * begins_quarter + 1, 1)
    assume(not special or begins < date(1991, 2, 2))
    prior = i.DisabilityPeriod(
        begins, date(begins_year, 12, 31), special_insured=special
    )
    person = i.Person(
        birth,
        sex=i.Sex.FEMALE,
        prior_disability_periods=(prior,),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2005, 1, 1)
    # A prior rests on the strictest basis some placement allows.
    for blind in (False, True):
        held = {
            _lawful_prior(birth, credits, begins, special, blind)
            for credits in placements(annual)
        }
        if True in held or special:
            break
    credits = _credits(annual)
    if True not in held:
        with pytest.raises(i.InsuredConfigurationUnsupported):
            i._prior_basis(person, credits, credits, 0, month, None)
        return
    assert i._prior_basis(person, credits, credits, 0, month, None) is blind
    binds = i._prior_start_binds(
        person, credits, credits, 0, month, None, blind
    )
    assert binds is (len(held) == 2), (annual, begins)
