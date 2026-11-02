"""Round 21: a listed prior's basis, and a prior no placement supports.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

A period begins in a quarter its holder was insured (404.320(b)(2), 404.321(a)).
A DisabilityPeriod records no blindness, and Person.statutory_blindness speaks
only for the present, so a record doesn't say whether an unflagged prior rested
on past blindness, which asks only for fully insured status (404.130(e)), or on
404.130(b) or (c), which ask for that and more. A computed result has to stand
on each basis some placement allows.

Every placement 404.130(b) or (c) allows also passes 404.130(e), so a filling
that keeps the prior on them speaks for both. A result none attains refuses by
name. A prior no placement supports on any basis rests on credits or facts the
record omits, and those could move other results, so it refuses by name too.
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
    _history,
    _person,
    _refused_with,
    _result,
)
from tests.test_track_b_insured_status_fix_round_19 import (
    DATE_ANNUAL,
    DATE_BIRTH,
    DATE_PRIOR,
    SPECIAL_BASE,
    UNKNOWN_ESTABLISHMENT,
    _credits,
    _date_person,
    _special_person,
    _unknown_year,
)
from tests.test_track_b_insured_status_fix_round_20 import (
    LISTED_PRIOR,
    _filling,
    _refusal,
)
from tests.test_track_b_insured_status_status_stress import (
    BASIS_PRIOR,
    LAST_40,
    basis_prior_declaration,
    check_no_period,
    last_insured,
    listed_prior_declaration,
    placements,
    prior_holds,
    quarter,
    two_basis_declaration,
    two_prior_declaration,
)

ALL = i.InsuredTest.ALL
FULLY = i.InsuredTest.FULLY
CURRENTLY = i.InsuredTest.CURRENTLY
DISABILITY = i.InsuredTest.DISABILITY
NO_SUPPORT = (
    "No annual placement supports a listed prior's first insured quarter"
)
BIRTH = BASIS_PRIOR["birth"]
ANNUAL = BASIS_PRIOR["annual"]
MONTH = BASIS_PRIOR["month"]
PRIOR = i.DisabilityPeriod(*BASIS_PRIOR["prior"][0])
# 1985Q1 finds 28 QCs in its 40 quarters. 1996Q1 finds 20 only by counting the
# 1985 to 1989 period and holding the 1996 QC in that quarter.
EARLIER = i.DisabilityPeriod(date(1985, 1, 1), date(1989, 12, 31))
LATER = i.DisabilityPeriod(date(1996, 1, 1), date(1997, 12, 31))
LATER_ANNUAL = {
    **dict.fromkeys(range(1978, 1985), 4),
    1990: 4,
    1996: 1,
}
# Every placement holds 20 of 40 at the 1998Q1 prior.
OPEN_ANNUAL = {
    **dict.fromkeys(range(1985, 1998), 4),
    1998: 1,
    **dict.fromkeys(range(1999, 2003), 4),
    2003: 3,
}


def _basis_person(*priors, **changes):
    values = dict(disability_onset=None)
    values.update(changes)
    return replace(_person(*(priors or (PRIOR,)), **values), birth_date=BIRTH)


def _years(annual=ANNUAL):
    return _history(BIRTH.year, MONTH.year, annual)


def _basis(person, annual, index=0, month=MONTH):
    credits = _credits(annual)
    return i._prior_basis(person, credits, credits, index, month, None)


# The two bases.


def test_the_two_bases_split_the_date():
    # Plain arithmetic: the 1998 QC falls anywhere on past blindness, and in
    # 1998Q1 on 404.130(b). The 40 quarters through 2008Q1 hold 20 only with
    # that QC later, and 2007Q4 counts the 1998Q1 QC.
    every = tuple(placements(ANNUAL))
    blind = [c for c in every if prior_holds(BASIS_PRIOR, c, 0, True)]
    nonblind = [c for c in every if prior_holds(BASIS_PRIOR, c, 0, False)]
    assert len(blind) == len(every)
    assert nonblind
    assert all(quarter(PRIOR.start) in credits for credits in nonblind)

    def best(fillings):
        return max(
            last_insured(
                BIRTH, credits, quarter(MONTH), periods, False, False, LAST_40
            )
            for credits in fillings
            for periods in (BASIS_PRIOR["prior"], ())
        )

    assert best(blind) == quarter(date(2008, 1, 1))
    assert best(nonblind) == quarter(date(2007, 10, 1))


@pytest.mark.parametrize("test", (DISABILITY, ALL))
def test_a_date_only_blindness_reaches_refuses(test):
    refused = _refusal(_basis_person(), _years(), MONTH, test=test)
    assert refused.reason is ASSIGNMENT
    assert refused.detail == LISTED_PRIOR


def test_that_refusal_keeps_the_row():
    _refused_with(
        ASSIGNMENT, _basis_person(), _years(), MONTH, test=DISABILITY
    )


def test_a_status_only_blindness_reaches_refuses():
    # DISABILITY at 2008Q1 needs the same 20 of 40.
    refused = _refusal(
        _basis_person(disability_onset=MONTH),
        _years(),
        MONTH,
        test=DISABILITY,
    )
    assert refused.detail == LISTED_PRIOR


def test_a_current_period_after_that_prior_refuses():
    refused = _refusal(
        _basis_person(
            disability_onset=date(2004, 1, 1),
            current_disability_period_established=True,
            current_disability_period_end=date(2004, 12, 31),
            current_disability_period_end_provenance=OBSERVED,
        ),
        _years(),
        MONTH,
    )
    assert refused.reason is ASSIGNMENT


def test_a_frozen_exit_after_that_prior_refuses():
    # An exit keeps the credits through 2003, and the date past it still turns
    # on where the prior puts the 1998 QC.
    refused = _refusal(
        _basis_person(),
        _history(BIRTH.year, 2003, ANNUAL),
        date(2027, 1, 1),
        test=DISABILITY,
        coverage_end_month=date(2003, 12, 1),
    )
    assert refused.detail == LISTED_PRIOR


def test_an_unknown_year_refuses_a_prior_placement_decides():
    refused = _refusal(
        _basis_person(),
        _unknown_year(_years(), 2005),
        MONTH,
        test=DISABILITY,
    )
    assert refused.detail == LISTED_PRIOR


# Where the bases agree.


def test_a_nonblind_filling_that_reaches_the_date_computes():
    # Four 2003 QCs put 20 in the 40 quarters through 2008Q1 with the 1998 QC
    # in its first quarter, so 404.130(b) reaches what blindness reaches.
    annual = {**ANNUAL, 2003: 4}
    result = _result(_basis_person(), _years(annual), MONTH, test=DISABILITY)
    assert result.dli.upper == date(2008, 3, 31)
    assert check_no_period({**BASIS_PRIOR, "annual": annual}) == "computed"


def test_a_prior_only_blindness_can_begin_keeps_that_basis():
    # Fourteen QCs precede 1998Q1, short of 20 of 40 on every placement, and
    # a prior beginning there needs 15. The record then implies past blindness.
    person = replace(
        _person(DATE_PRIOR, disability_onset=None), birth_date=DATE_BIRTH
    )
    assert _basis(person, DATE_ANNUAL) is True


def test_every_nonblind_placement_binds_nothing():
    person = _basis_person()
    credits = _credits(OPEN_ANNUAL)
    assert _basis(person, OPEN_ANNUAL) is False
    assert not i._prior_start_binds(
        person, credits, credits, 0, MONTH, None, False
    )
    case = {**BASIS_PRIOR, "annual": OPEN_ANNUAL}
    assert check_no_period(case) == "computed"


def test_one_placement_can_decide_a_nonblind_prior_alone():
    # Blindness leaves ANNUAL's 1998 QC open on every placement, so only the
    # nonblind basis binds.
    person = _basis_person()
    credits = _credits(ANNUAL)
    assert _basis(person, ANNUAL) is False
    assert not i._prior_start_binds(
        person, credits, credits, 0, MONTH, None, True
    )
    assert i._prior_start_binds(
        person, credits, credits, 0, MONTH, None, False
    )


def test_a_filling_keeps_a_prior_on_its_own_basis():
    person = _basis_person()
    first, later = (
        _filling(
            ANNUAL,
            next(
                credits
                for credits in placements(ANNUAL)
                if (quarter(PRIOR.start) in credits) is wanted
            ),
        )
        for wanted in (True, False)
    )
    assert i._keeps_priors(person, first, ((0, False),), None)
    assert i._keeps_priors(person, first, ((0, True),), None)
    assert i._keeps_priors(person, later, ((0, True),), None)
    assert not i._keeps_priors(person, later, ((0, False),), None)


def test_a_later_prior_can_rest_on_an_earlier_one_on_either_basis():
    # Only counting the earlier period puts 20 of 40 within the later prior's
    # reach, so its nonblind basis needs that period.
    person = _basis_person(EARLIER, LATER)
    assert _basis(person, LATER_ANNUAL, 0) is False
    assert _basis(person, LATER_ANNUAL, 1) is False
    bare = _basis_person(LATER)
    assert _basis(bare, LATER_ANNUAL) is True


def test_a_flagged_prior_has_one_basis():
    assert _basis(_special_person(), {**SPECIAL_BASE, 1990: 1}) is False


# The bases against every placement.


@settings(max_examples=60, deadline=None, derandomize=True)
@given(
    seed=st.integers(0, 2**32 - 1),
    declare=st.sampled_from(
        (
            basis_prior_declaration,
            two_basis_declaration,
            listed_prior_declaration,
            two_prior_declaration,
        )
    ),
)
def test_each_basis_matches_every_placement(seed, declare):
    case = declare(seed)
    annual = case["annual"]
    every = tuple(placements(annual))
    assume(len(every) <= 96)
    person = replace(
        _person(
            *(i.DisabilityPeriod(*period) for period in case["prior"]),
            disability_onset=None,
        ),
        birth_date=case["birth"],
    )
    credits = _credits(annual)
    month = case["month"]
    for index in range(len(case["prior"])):
        held = {}
        for blind in (False, True):
            held[blind] = [
                prior_holds(case, filling, index, blind) for filling in every
            ]
            for filling, expected in zip(every, held[blind], strict=True):
                assert (
                    i._prior_passes(
                        person,
                        _filling(annual, filling),
                        index,
                        None,
                        blind=blind,
                    )
                    is expected
                ), (case, sorted(filling), index, blind)
        # 404.130(b) and (c) ask for fully insured status too.
        assert all(
            passes or not strict
            for strict, passes in zip(held[False], held[True], strict=True)
        ), (case, index)
        if not any(held[True]):
            with pytest.raises(i.InsuredConfigurationUnsupported) as error:
                i._prior_basis(person, credits, credits, index, month, None)
            assert error.value.detail == NO_SUPPORT
            continue
        basis = i._prior_basis(person, credits, credits, index, month, None)
        assert basis is (not any(held[False])), (case, index)
        binds = i._prior_start_binds(
            person, credits, credits, index, month, None, basis
        )
        assert binds or all(held[basis]), (case, index)
        if index == 0:
            assert binds is not all(held[basis]), (case, index)


# A prior no placement supports.


@pytest.mark.parametrize("test", (ALL, FULLY, CURRENTLY, DISABILITY))
def test_a_prior_no_placement_supports_refuses_for_each_test(test):
    # Nine QCs are required at 1992Q1 and three can fall by then.
    prior = i.DisabilityPeriod(date(1992, 1, 1), date(1992, 12, 31))
    refused = _refusal(
        _date_person(
            prior_disability_periods=(prior,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        _history(1961, 2008, DATE_ANNUAL),
        date(2008, 1, 1),
        test=test,
    )
    assert refused.reason is ASSIGNMENT
    assert refused.detail == NO_SUPPORT


@pytest.mark.parametrize(
    "annual",
    (
        pytest.param(
            {**SPECIAL_BASE, 1985: 4}, id="reaches_the_ordinary_rule"
        ),
        pytest.param({**SPECIAL_BASE, 1985: 1}, id="short_of_its_route"),
    ),
)
def test_a_flagged_prior_no_placement_supports_names_why(annual):
    refused = _refusal(
        _special_person(), _history(1960, 1995, annual), date(1995, 1, 1)
    )
    assert refused.reason is ASSIGNMENT
    assert refused.detail == NO_SUPPORT


def test_unknown_establishment_refuses_a_prior_no_placement_supports():
    # Later QCs carry FULLY with no period in force, so the proof over UNKNOWN
    # periods passes, and only the check can name this prior.
    prior = i.DisabilityPeriod(date(1992, 1, 1), date(1992, 12, 31))
    annual = {1991: 2, 1992: 1, **dict.fromkeys(range(1993, 2001), 4)}
    refused = _refusal(
        _date_person(
            prior_disability_periods=(prior,),
            prior_disability_periods_provenance=OBSERVED,
            **UNKNOWN_ESTABLISHMENT,
        ),
        _history(1961, 2001, annual),
        date(2001, 1, 1),
        test=FULLY,
    )
    assert refused.detail == NO_SUPPORT


def test_an_unknown_year_can_support_a_prior():
    # Three UNKNOWN years could hold the nine QCs that start needs, so the
    # record could support it, and placement then decides.
    prior = i.DisabilityPeriod(date(1992, 1, 1), date(1992, 12, 31))
    years = _history(1961, 2008, DATE_ANNUAL)
    for year in (1985, 1986, 1987):
        years = _unknown_year(years, year)
    refused = _refusal(
        _date_person(
            prior_disability_periods=(prior,),
            prior_disability_periods_provenance=OBSERVED,
        ),
        years,
        date(2008, 1, 1),
        test=DISABILITY,
    )
    assert refused.detail == LISTED_PRIOR


def test_an_unknown_year_can_carry_a_flagged_prior_past_the_ordinary_rule():
    # Eighteen QCs pass the route on every placement and fall short of 20 of 40,
    # and an UNKNOWN 1984 can add four. Upper credits speak for that completion.
    annual = {1985: 2, **dict.fromkeys(range(1986, 1990), 4)}
    person = _special_person()
    credits = _credits(annual)
    assert i._every_placement_begins(
        person, credits, 0, date(1995, 1, 1), None, blind=False
    )
    refused = _refusal(
        person,
        _unknown_year(_history(1960, 1995, annual), 1984),
        date(1995, 1, 1),
        test=FULLY,
    )
    assert refused.detail == LISTED_PRIOR


def test_an_unknown_year_can_leave_a_flagged_prior_short_of_the_ordinary_rule():
    # An UNKNOWN 1985 runs from 16 QCs, short of 20 of 40, to 20. Lower credits
    # speak for every completion, so the ordinary rule doesn't rule this out.
    refused = _refusal(
        _special_person(),
        _unknown_year(_history(1960, 1995, SPECIAL_BASE), 1985),
        date(1995, 1, 1),
        test=FULLY,
    )
    assert refused.detail == LISTED_PRIOR
