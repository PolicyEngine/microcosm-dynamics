"""Round 20: a start's later years stay open.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

Whether a filling keeps a period's start turns only on quarters through it
(404.321(a)), so no later year can move it, and each status places those years
favorably (RS 00301.230; source conflict
us:oasdi-insured-one-filling-first-start).

The round 19 mutation rerun left four mutations alive, and a test below kills
each. A result every placement attains needs no search of a split prior. A
period's establishment counts no quarter of its own. The worst filling is
exact only with no period in force (404.146(d) keeps a period's credited
endpoints). A special prior that every placement carries binds nothing.
"""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_2 import (
    _person as _declared_person,
)
from tests.test_track_b_insured_status_fix_round_17 import (
    ASSIGNMENT,
    OBSERVED,
    _history,
    _person,
    _result,
)
from tests.test_track_b_insured_status_fix_round_19 import (
    ANNUAL,
    DATE_ANNUAL,
    DATE_BIRTH,
    DATE_PRIOR,
    SPECIAL_BASE,
    UNKNOWN_ESTABLISHMENT,
    _credits,
    _date_person,
    _lawful_prior,
    _special_person,
    _unknown_year,
)
from tests.test_track_b_insured_status_status_stress import (
    disability,
    placements,
    quarter,
)

FULLY = i.InsuredTest.FULLY
DISABILITY = i.InsuredTest.DISABILITY
MONTH = date(2005, 1, 1)
LISTED_PRIOR = (
    "Annual placement decides a listed prior's first insured quarter"
)


def _qdate(credit):
    return date(credit // 4, 3 * (credit % 4) + 1, 1)


def _qend(credit):
    return _qdate(credit + 1) - timedelta(days=1)


def _filling(annual, credits):
    """One placement of ``annual`` as fixed quarters for each year."""
    return {
        year: (tuple(sorted(c for c in credits if c // 4 == year)), 0)
        for year in annual
    }


def _refusal(person, years, month, **options):
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, **options)
    return error.value


# Later years.


def test_partial_years_after_the_start_stay_open():
    # A 2004 start rests on 1990 to 1999, so the 5,184 placements of 2016 to
    # 2020 can't move it. With the period through the query, the 40 QCs of
    # 1990 to 1999 meet the eight elapsed years 1992 to 1999.
    person = _declared_person(
        date(1970, 2, 2),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2000, 4, 2), date(2003, 9, 30)),
        ),
        disability_onset=date(2004, 1, 15),
        current_disability_period_established=True,
    )
    month = date(2020, 12, 1)
    counts = dict.fromkeys(range(1990, 2000), 4)
    counts.update(zip(range(2016, 2021), (2, 3, 2, 2, 2), strict=True))
    result = i.insured_status(
        person, history(person, month, counts), month, test=FULLY
    )
    assert result.current_disability_period_start == date(2004, 1, 15)
    assert result.fully.insured
    assert (result.fully.qc_count_lower, result.fully.required) == (40, 8)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(
    onset=st.dates(date(1996, 1, 1), date(2002, 12, 31)),
    full=st.sets(st.integers(-8, -1), min_size=4, max_size=6),
    near=st.integers(-1, 0),
    count=st.integers(1, 3),
    later=st.dictionaries(
        st.integers(1, 5), st.integers(1, 3), min_size=1, max_size=2
    ),
    prior=st.booleans(),
)
def test_a_filling_keeps_its_start_whatever_later_years_hold(
    onset, full, near, count, later, prior
):
    # Four to six full years before the onset, a partial year at or just
    # before it and one or two partial years after it, so the start sits
    # near the 20-of-40 edge and the later years hold placements to vary.
    annual = {
        **{onset.year + offset: 4 for offset in full},
        onset.year + near: count,
        **{onset.year + offset: n for offset, n in later.items()},
    }
    person = i.Person(
        date(1964, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=onset,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=(
            (i.DisabilityPeriod(date(1990, 1, 1), date(1991, 12, 31)),)
            if prior
            else ()
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    starts = {}
    for credits in placements(annual):
        try:
            starts[credits] = i._with_current_period(
                person, _filling(annual, credits), date(2008, 1, 1), None
            )[1]
        except (InvalidFamilyInput, i.InsuredConfigurationUnsupported):
            starts[credits] = None
    for credits, start in starts.items():
        if start is None:
            continue
        through = {c for c in credits if c // 4 <= start.year}
        for other, found in starts.items():
            if {c for c in other if c // 4 <= start.year} == through:
                assert found == start, (annual, onset, sorted(other))


# A result every placement attains.


def test_an_unknown_year_leaves_a_proven_result_to_the_proof():
    # Every placement attains this result with no period in force, on every
    # completion of an UNKNOWN 1997 too, so the split prior can't move it.
    annual = {**DATE_ANNUAL, **dict.fromkeys(range(2004, 2008), 4)}
    result = _result(
        _date_person(
            **UNKNOWN_ESTABLISHMENT,
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _unknown_year(_history(1961, 2008, annual), 1997),
        date(2008, 1, 1),
    )
    assert result.dli.lower == date(2008, 3, 31)
    assert result.fully.insured
    assert result.currently.insured


# A period's own quarters.


def test_an_establishment_counts_no_quarter_of_its_own_period():
    # The prior holds the 1998 QC in 1998Q1, so it binds, and DISABILITY joins
    # the search. Counting the prior skips its six interior quarters, so the
    # 40 quarters through 2004Q1 reach 1992Q4 and hold 26 QCs. The period
    # begins in 2004Q1, which holds no QC. Excluding that quarter would reach
    # 1992Q3 for 27, and the period would rest on its own exclusion.
    result = _result(
        _date_person(
            disability_onset=date(2004, 1, 1),
            current_disability_period_end=date(2004, 12, 31),
            prior_disability_periods=(DATE_PRIOR,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2005, DATE_ANNUAL),
        date(2005, 1, 1),
        test=DISABILITY,
    )
    assert result.current_disability_period_start == date(2004, 1, 1)
    assert result.assigned_quarters[1998] == (1998 * 4,)
    found = result.disability
    assert (found.qc_count_lower, found.qc_count_upper) == (26, 26)
    assert found.qualifying_quarter == date(2004, 1, 1)


# A later prior on an earlier period's credited endpoint.

ENDPOINT_ANNUAL = {1987: 4, 1992: 4, 1993: 4, 1994: 4, 1999: 1}
EARLIER = i.DisabilityPeriod(date(1999, 1, 1), date(2000, 9, 30))
LATER = i.DisabilityPeriod(date(2002, 4, 1), date(2003, 9, 30))


def _endpoint_person():
    return replace(
        _person(EARLIER, LATER, disability_onset=None), birth_date=DATE_BIRTH
    )


def _later_holds(birth, credits, earlier, later):
    """Past blindness asks for fully insured status at the later start."""
    at = quarter(later.start)
    return disability(
        birth, credits, at, ((earlier.start, earlier.end),), True
    ) or disability(birth, credits, at, (), True)


def test_a_later_prior_on_an_earlier_endpoint_binds():
    # Counting the 1999 period leaves 17 elapsed years before 2002, and 16 QCs
    # fall in 1987 and 1992 to 1994. The 1999 QC counts only in 1999Q1, the
    # period's credited first quarter (404.146(d)), and disregarding the
    # period asks for 19. The worst filling puts that QC in 1999Q1, so with
    # the period listed it passes where a 1999Q2 filling fails.
    person = _endpoint_person()
    held = {
        _later_holds(DATE_BIRTH, credits, EARLIER, LATER)
        for credits in placements(ENDPOINT_ANNUAL)
    }
    assert held == {False, True}
    credits = _credits(ENDPOINT_ANNUAL)
    listed = replace(
        person, statutory_blindness=True, prior_disability_periods=(EARLIER,)
    )
    assert i._every_placement_passes(
        listed, credits, LATER.start, MONTH, None, DISABILITY
    )
    interior = {**credits, 1999: ((1999 * 4 + 1,), 0)}
    assert not i._prior_passes(person, interior, 1, None)
    assert i._prior_start_binds(person, credits, credits, 1, MONTH, None)


def test_an_unknown_year_refuses_that_later_prior():
    # An UNKNOWN 1997 runs from none, where only a 1999Q1 QC holds the later
    # prior, to four, where every placement does.
    refused = _refusal(
        _endpoint_person(),
        _unknown_year(_history(1961, 2004, ENDPOINT_ANNUAL), 1997),
        date(2004, 1, 1),
    )
    assert refused.reason is ASSIGNMENT
    assert refused.detail == LISTED_PRIOR


@settings(max_examples=60, deadline=None, derandomize=True)
@example(
    annual=ENDPOINT_ANNUAL,
    earlier_start=quarter(EARLIER.start),
    earlier_length=quarter(EARLIER.end) - quarter(EARLIER.start),
    gap=quarter(LATER.start) - quarter(EARLIER.end),
    later_length=quarter(LATER.end) - quarter(LATER.start),
)
@given(
    annual=ANNUAL,
    earlier_start=st.integers(1986 * 4, 2000 * 4 + 3),
    earlier_length=st.integers(0, 7),
    gap=st.integers(1, 16),
    later_length=st.integers(0, 6),
)
def test_a_later_prior_placement_splits_binds(
    annual, earlier_start, earlier_length, gap, later_length
):
    later_start = earlier_start + earlier_length + gap
    assume(later_start + later_length <= 2004 * 4 + 3)
    earlier = i.DisabilityPeriod(
        _qdate(earlier_start), _qend(earlier_start + earlier_length)
    )
    later = i.DisabilityPeriod(
        _qdate(later_start), _qend(later_start + later_length)
    )
    person = replace(
        _person(earlier, later, disability_onset=None), birth_date=DATE_BIRTH
    )
    held = set()
    for credits in placements(annual):
        expected = _later_holds(DATE_BIRTH, credits, earlier, later)
        assert (
            i._prior_passes(person, _filling(annual, credits), 1, None)
            is expected
        ), (annual, earlier, later, sorted(credits))
        held.add(expected)
    credits = _credits(annual)
    binds = i._prior_start_binds(person, credits, credits, 1, MONTH, None)
    assert binds or len(held) == 1, (annual, earlier, later)
    assert not binds or True in held, (annual, earlier, later)


# A special prior every placement carries.


def test_an_unknown_year_leaves_a_special_prior_every_placement_carries():
    # Eighteen QCs pass the route on every placement, and one 1990 QC can't
    # reach 20 of 40. An UNKNOWN 1993 follows the prior and can't reach its
    # start, so the prior binds nothing and the status computes.
    result = _result(
        _special_person(),
        _unknown_year(_history(1960, 1995, {**SPECIAL_BASE, 1990: 1}), 1993),
        date(1995, 1, 1),
        test=FULLY,
    )
    assert result.fully.insured


@settings(max_examples=100, deadline=None, derandomize=True)
@example(
    annual={1985: 4, 1986: 4, 1987: 4, 1988: 4, 1989: 3},
    begins_year=1990,
    begins_quarter=3,
)
@given(
    annual=ANNUAL,
    begins_year=st.integers(1986, 1990),
    begins_quarter=st.integers(0, 3),
)
def test_a_special_prior_every_placement_carries_binds_nothing(
    annual, begins_year, begins_quarter
):
    # 404.130(d)(1)'s holder "were only insured under paragraph (c)". When
    # every placement passes the route and stays short of 20 of 40, no
    # placement can unseat the prior.
    birth = date(1960, 2, 2)
    begins = date(begins_year, 3 * begins_quarter + 1, 1)
    prior = i.DisabilityPeriod(
        begins, date(begins_year, 12, 31), special_insured=True
    )
    person = i.Person(
        birth,
        sex=i.Sex.FEMALE,
        prior_disability_periods=(prior,),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    held = {
        _lawful_prior(birth, credits, begins, True)
        for credits in placements(annual)
    }
    credits = _credits(annual)
    binds = i._prior_start_binds(person, credits, credits, 0, MONTH, None)
    assert held != {True} or not binds, (annual, begins)
