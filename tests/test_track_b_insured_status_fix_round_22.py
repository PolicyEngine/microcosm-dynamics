"""Round 22: an unflagged prior before age 31 can't rest on 404.130(c).

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

404.130(d)(1) reaches someone "disabled again at age 31 or later after having
had a prior period of disability established which began before age 31 and
for which you were only insured under paragraph (c)". DisabilityPeriod records
that fact as ``special_insured``, so an unflagged prior's holder wasn't only
insured under 404.130(c), and 404.130(c) can't begin that prior alone. It rests
on 404.130(b), on 404.130(d) after a flagged prior, or on past blindness
(404.130(e)), and a computed result has to stand on each basis some placement
allows.

Before this round 404.130(c) could begin an unflagged prior. It can hold a
prior on every placement while 404.130(b) holds a QC in the prior's first
quarter, so the prior bound nothing, and a date only past blindness reaches
came back computed.
"""

from datetime import date

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from tests.test_track_b_insured_status_fix_round_17 import (
    ASSIGNMENT,
    LONG,
    OBSERVED,
    _history,
    _refused_with,
    _result,
)
from tests.test_track_b_insured_status_fix_round_19 import (
    _credits,
    _unknown_year,
)
from tests.test_track_b_insured_status_fix_round_20 import (
    LISTED_PRIOR,
    _filling,
    _refusal,
)
from tests.test_track_b_insured_status_status_stress import (
    LAST_40,
    YOUNG_PRIOR,
    check_no_period,
    disability,
    flags,
    last_insured,
    mixed_flag_declaration,
    placements,
    prior_holds,
    quarter,
    two_basis_declaration,
    young_basis_declaration,
)

ALL = i.InsuredTest.ALL
DISABILITY = i.InsuredTest.DISABILITY
BIRTH = YOUNG_PRIOR["birth"]
ANNUAL = YOUNG_PRIOR["annual"]
MONTH = YOUNG_PRIOR["month"]
PRIOR = i.DisabilityPeriod(*YOUNG_PRIOR["prior"][0])
FLAGGED = i.DisabilityPeriod(PRIOR.start, PRIOR.end, special_insured=True)
# Without the 1998 QC, 404.130(c) finds 18 of 36 at 1998Q1 and 404.130(b) 19 of
# 40, on the one placement.
NO_1998 = {year: n for year, n in ANNUAL.items() if year != 1998}
# Two 1993 QCs leave 404.130(c) the 1998 QC to hold in 1998Q1, and 404.130(b)
# 19 of 40 at most.
TWO_1993 = {**ANNUAL, 1993: 2}
# 18 of the 24 quarters 1989Q2 to 1995Q1 pass 404.130(c), and 19 of 40 fall
# short of 404.130(b), so a flag fits this prior.
EARLY_FLAG = i.DisabilityPeriod(
    date(1995, 1, 1), date(1995, 12, 31), special_insured=True
)
# A flagged 1993 prior finds 9 of the 16 quarters 1989Q2 to 1993Q1 and 10 of
# 40. At 1999Q2, past the 1999Q1 quarter she attains 31, 404.130(d) counts 37
# quarters with that prior's four set aside, and finds 18 only with the 1999 QC
# by then. 404.130(b) finds 19 of 40 at most.
D_FLAG = i.DisabilityPeriod(
    date(1993, 1, 1), date(1993, 12, 31), special_insured=True
)
D_PRIOR = i.DisabilityPeriod(date(1999, 4, 1), date(1999, 12, 31))
D_ANNUAL = {1989: 4, 1990: 4, 1991: 2, 1994: 4, 1995: 4, 1999: 1}


def _young(*priors, **changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=None,
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods=priors or (PRIOR,),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    values.update(changes)
    return i.Person(BIRTH, **values)


def _years(annual=ANNUAL, last=MONTH.year):
    return _history(BIRTH.year, last, annual)


def _basis(person, annual, index=0, month=MONTH):
    credits = _credits(annual)
    return i._prior_basis(person, credits, credits, index, month, None)


def _case(*priors, annual=ANNUAL):
    return {
        **YOUNG_PRIOR,
        "annual": annual,
        "prior": tuple((p.start, p.end) for p in priors),
        "flags": tuple(p.special_insured for p in priors),
    }


# The reviewed record.


def test_paragraph_c_holds_every_placement_and_paragraph_b_one_quarter():
    # Plain arithmetic: 404.130(c) finds 18 of the 36 quarters from 1989Q2 on
    # every placement. 404.130(b) finds 19 of 40 there, so it holds the 1998 QC
    # in 1998Q1. The 40 quarters through 2008Q1 reach 20 only with that QC
    # later, and 2007Q4 counts it.
    every = tuple(placements(ANNUAL))
    at = quarter(PRIOR.start)
    either = [c for c in every if disability(BIRTH, c, at, (), False)]
    nonblind = [c for c in every if prior_holds(YOUNG_PRIOR, c, 0, False)]
    blind = [c for c in every if prior_holds(YOUNG_PRIOR, c, 0, True)]
    assert len(either) == len(blind) == len(every)
    assert nonblind
    assert all(at in credits for credits in nonblind)

    def best(fillings):
        return max(
            last_insured(
                BIRTH, credits, quarter(MONTH), periods, False, False, LAST_40
            )
            for credits in fillings
            for periods in (YOUNG_PRIOR["prior"], ())
        )

    assert best(either) == best(blind) == quarter(date(2008, 1, 1))
    assert best(nonblind) == quarter(date(2007, 10, 1))


@pytest.mark.parametrize("test", (DISABILITY, ALL))
def test_a_date_only_blindness_reaches_refuses(test):
    refused = _refusal(
        _young(disability_onset=MONTH), _years(), MONTH, test=test
    )
    assert refused.reason is ASSIGNMENT
    assert refused.detail == LISTED_PRIOR


def test_that_refusal_keeps_the_row():
    _refused_with(
        ASSIGNMENT,
        _young(disability_onset=MONTH),
        _years(),
        MONTH,
        test=DISABILITY,
    )


def test_with_no_onset_the_date_refuses():
    assert _refusal(_young(), _years(), MONTH).detail == LISTED_PRIOR
    assert check_no_period(YOUNG_PRIOR) == "refused"


def test_a_frozen_exit_refuses():
    # The exit keeps the QCs through 2003, and the date past it still turns
    # on where the prior puts the 1998 QC.
    refused = _refusal(
        _young(),
        _years(last=2003),
        date(2027, 1, 1),
        test=DISABILITY,
        coverage_end_month=date(2003, 12, 1),
    )
    assert refused.detail == LISTED_PRIOR


def test_an_unknown_year_refuses():
    refused = _refusal(
        _young(), _unknown_year(_years(), 2005), MONTH, test=DISABILITY
    )
    assert refused.detail == LISTED_PRIOR


def test_a_current_period_after_that_prior_refuses():
    # Disregarding the prior (404.130(f)), every placement insures the 2004Q1
    # onset, so the prior's basis is what placement decides, and the detail
    # names it (round 23).
    refused = _refusal(
        _young(
            disability_onset=date(2004, 1, 1),
            current_disability_period_established=True,
            current_disability_period_end=date(2004, 12, 31),
            current_disability_period_end_provenance=OBSERVED,
        ),
        _years(),
        MONTH,
    )
    assert refused.reason is ASSIGNMENT
    assert refused.detail == LISTED_PRIOR


def test_a_flagged_prior_there_computes():
    # A flag rules 404.130(b) out at 1998Q1, so the 1998 QC falls later, and
    # the 40 quarters through 2008Q1 hold 20.
    result = _result(
        _young(FLAGGED, disability_onset=MONTH),
        _years(),
        MONTH,
        test=DISABILITY,
    )
    assert result.disability.insured
    assert result.dli.upper == date(2008, 3, 31)
    assert check_no_period({**YOUNG_PRIOR, "special": True}) == "computed"


# Where 404.130(c) alone could begin the prior.


def test_a_prior_only_paragraph_c_begins_rests_on_past_blindness():
    assert _basis(_young(), NO_1998) is True
    assert _basis(_young(FLAGGED), NO_1998) is False


def test_a_prior_paragraph_c_splits_computes_on_past_blindness():
    # Past blindness holds the prior on every placement, so the date reaches
    # 2008Q1. Read on 404.130(c), the prior held the 1998 QC in 1998Q1, and
    # the rule refused.
    assert _basis(_young(), TWO_1993) is True
    result = _result(_young(), _years(TWO_1993), MONTH, test=DISABILITY)
    assert result.dli.upper == date(2008, 3, 31)
    assert check_no_period({**YOUNG_PRIOR, "annual": TWO_1993}) == "computed"


def test_only_paragraph_b_binds_the_prior():
    person = _young()
    credits = _credits(ANNUAL)
    assert _basis(person, ANNUAL) is False
    assert i._prior_start_binds(
        person, credits, credits, 0, MONTH, None, False
    )
    assert not i._prior_start_binds(
        person, credits, credits, 0, MONTH, None, True
    )
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
    assert not i._keeps_priors(person, later, ((0, False),), None)
    assert i._keeps_priors(person, later, ((0, True),), None)


# After a flagged prior.


def test_a_young_prior_after_a_flagged_one_rests_on_paragraph_b():
    # 404.130(d) opens only at 31, so the flagged 1995 prior leaves the 1998Q1
    # prior where it was: on 404.130(b), with the 1998 QC in 1998Q1.
    person = _young(EARLY_FLAG, PRIOR)
    case = _case(EARLY_FLAG, PRIOR)
    assert _basis(person, ANNUAL, 0) is False
    for credits in placements(ANNUAL):
        expected = quarter(PRIOR.start) in credits
        filling = _filling(ANNUAL, credits)
        assert prior_holds(case, credits, 1, False) is expected
        assert i._prior_passes(person, filling, 1, None, blind=False) is (
            expected
        )
    assert _basis(person, ANNUAL, 1) is False
    credits = _credits(ANNUAL)
    assert i._prior_start_binds(
        person, credits, credits, 1, MONTH, None, False
    )


def test_a_prior_past_31_after_a_flagged_one_can_rest_on_paragraph_d():
    person = _young(D_FLAG, D_PRIOR)
    case = _case(D_FLAG, D_PRIOR, annual=D_ANNUAL)
    assert _basis(person, D_ANNUAL, 0) is False
    held = set()
    for credits in placements(D_ANNUAL):
        expected = bool(credits & {quarter(date(1999, m, 1)) for m in (1, 4)})
        filling = _filling(D_ANNUAL, credits)
        assert prior_holds(case, credits, 1, False) is expected
        assert i._prior_passes(person, filling, 1, None, blind=False) is (
            expected
        )
        assert not i._prior_passes(
            person, filling, 1, None, blind=False, ordinary_only=True
        )
        held.add(expected)
    assert held == {False, True}
    assert _basis(person, D_ANNUAL, 1) is False
    credits = _credits(D_ANNUAL)
    assert i._prior_start_binds(
        person, credits, credits, 1, MONTH, None, False
    )


def test_without_the_flag_that_prior_rests_on_past_blindness():
    plain = i.DisabilityPeriod(D_FLAG.start, D_FLAG.end)
    assert _basis(_young(plain, D_PRIOR), D_ANNUAL, 1) is True


# Each basis against every placement.


def _case_person(case):
    return i.Person(
        case["birth"],
        sex=i.Sex.FEMALE,
        prior_disability_periods=tuple(
            i.DisabilityPeriod(a, b, special_insured=flag)
            for (a, b), flag in zip(case["prior"], flags(case), strict=True)
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )


def _check_unflagged_bases(case):
    """Each unflagged prior's basis, against every placement."""
    annual = case["annual"]
    every = tuple(placements(annual))
    person = _case_person(case)
    credits = _credits(annual)
    for index, flag in enumerate(flags(case)):
        if flag:
            continue
        held = {
            blind: [prior_holds(case, c, index, blind) for c in every]
            for blind in (False, True)
        }
        for blind, expected in held.items():
            for filling, holds in zip(every, expected, strict=True):
                try:
                    passes = i._keeps_priors(
                        person,
                        _filling(annual, filling),
                        ((index, blind),),
                        None,
                    )
                except i.InsuredConfigurationUnsupported as error:
                    # Past 40 counted quarters the readings of 404.130(d)
                    # part ways, and the rule refuses by name.
                    assert error.reason is LONG
                    continue
                assert passes is holds, (case, sorted(filling), index, blind)
        if not any(held[True]):
            continue
        try:
            basis = i._prior_basis(
                person, credits, credits, index, case["month"], None
            )
        except i.InsuredConfigurationUnsupported as error:
            assert error.reason is LONG
            continue
        assert basis is (not any(held[False])), (case, index)
        binds = i._prior_start_binds(
            person, credits, credits, index, case["month"], None, basis
        )
        assert binds or all(held[basis]), (case, index)
        if index == 0:
            assert binds is not all(held[basis]), (case, index)


@settings(max_examples=60, deadline=None, derandomize=True)
@given(
    seed=st.integers(0, 2**32 - 1),
    declare=st.sampled_from(
        (
            young_basis_declaration,
            mixed_flag_declaration,
            two_basis_declaration,
        )
    ),
)
def test_each_basis_matches_every_placement(seed, declare):
    case = declare(seed)
    assume(sum(1 for _ in placements(case["annual"])) <= 96)
    _check_unflagged_bases(case)


YEARS = st.integers(1988, 2000)
ANNUALS = st.builds(
    lambda full, partial: {**dict.fromkeys(full, 4), **partial},
    st.sets(YEARS, min_size=2, max_size=8),
    st.dictionaries(YEARS, st.integers(1, 3), max_size=2),
)


@settings(max_examples=150, deadline=None, derandomize=True)
@given(
    annual=ANNUALS,
    flagged_at=st.integers(1990 * 4, 1998 * 4 + 3),
    gap=st.integers(1, 12),
)
def test_a_later_prior_after_a_flagged_one_matches_every_placement(
    annual, flagged_at, gap
):
    # The flagged prior begins before the 1999Q1 quarter she attains 31 and
    # runs through its year. The later prior then falls on either side of it.
    begins = date(flagged_at // 4, 3 * (flagged_at % 4) + 1, 1)
    later_at = (flagged_at // 4 + 1) * 4 + gap - 1
    later = date(later_at // 4, 3 * (later_at % 4) + 1, 1)
    case = {
        **YOUNG_PRIOR,
        "annual": annual,
        "prior": (
            (begins, date(begins.year, 12, 31)),
            (later, date(later.year, 12, 31)),
        ),
        "flags": (True, False),
    }
    _check_unflagged_bases(case)
