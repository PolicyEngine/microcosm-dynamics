"""Round 24: an input error holds on every completion of the record.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

``InvalidFamilyInput`` drops a row, so an established current period with no
possible insured quarter raises it only where every completion of the
record's UNKNOWN years would. Each listed prior then needs support on every
completion, not just one: where a year open by a prior's start can leave it
unsupported, the record refuses by name. Before 1978 a year credits fixed
quarters, so each set of its quarters makes a completion, and a 1953 quarter
after a pre-1956 prior's start can exclude RS 00301.480 B.1's route where a
count the rule places to suit each test can't. A middle count can have more
boundary assignments than either bound, so the record also refuses where
some completion could exceed the 4,096 cap.
"""

import random
from dataclasses import replace
from datetime import date, timedelta
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_23 import (
    ALL,
    DISABILITY,
    FEMALE,
    MALE,
    OBSERVED,
    UNKNOWN,
    UNSUPPORTED_PRIOR,
    Reason,
    _person,
    _refused,
    _row,
)

NO_POSSIBLE = "no possible insured disabled quarter"
UNDECIDED = "Unknown earnings decide a listed prior's support"
BOUNDARY_CAP = "More than 4096 boundary assignments"
BOUNDARY_GUARD = "A completion may have more than 4096 boundary assignments"
COMPLETION_CAP = "More than 4096 completions decide a listed prior's support"
PROPERTY = settings(max_examples=25, deadline=None, derandomize=True)
MONTH = date(2006, 1, 1)


def _year(year, fill):
    """An UNKNOWN row, a count from 1978, or quarter flags before."""
    if fill is None:
        return i.CoverageYear(UNKNOWN)
    if year < 1978:
        return i.CoverageYear(OBSERVED, qc_quarters=fill)
    return i.CoverageYear(OBSERVED, qc_count=fill)


def _invalid(person, years, month, **options):
    with pytest.raises(i.InvalidFamilyInput, match=NO_POSSIBLE):
        _row(person, years, month, **options)


def _expect(outcome, person, years, month, **options):
    """Check an input error, or a refusal's reason and detail."""
    if outcome is None:
        _invalid(person, years, month, **options)
        return
    reason, detail = outcome
    assert _refused(reason, person, years, month, **options) == detail


UNSUPPORTED = (Reason.ASSIGNMENT_COMPLEXITY, UNSUPPORTED_PRIOR)
OPEN = (Reason.UNKNOWN_EARNINGS, UNDECIDED)


# A year open by a listed prior's start that can leave it unsupported.


def _unflagged(fill, counts):
    person = _person(
        date(1950, 2, 2),
        i.DisabilityPeriod(date(1990, 1, 1), date(1991, 12, 31)),
        onset=date(2005, 1, 15),
        established=True,
    )
    years = history(person, MONTH, counts)
    years[1989] = _year(1989, fill)
    return person, years


SIXTEEN = {year: 4 for year in range(1981, 1985)}


@pytest.mark.parametrize(
    "fill,outcome",
    (
        (None, OPEN),
        (0, UNSUPPORTED),
        (1, UNSUPPORTED),
        (2, None),
        (3, None),
        (4, None),
    ),
)
def test_a_year_that_can_leave_an_unflagged_prior_unsupported_refuses(
    fill, outcome
):
    # Plain arithmetic: born 1950-02-02, she needs 18 QCs to be fully insured
    # at 1990Q1, and 1981 to 1984 give 16. 404.130(b) counts those 16 in the
    # 40 quarters ending 1990Q1, and four 1989 QCs bring it to 20; past
    # blindness asks only the 18. So two or more 1989 QCs support the prior,
    # and none or one leaves it unsupported. No QC follows 1989, so no
    # completion insures the 2005 period.
    _expect(outcome, *_unflagged(fill, SIXTEEN), MONTH)


def _flagged(fill, counts):
    person = _person(
        date(1965, 6, 15),
        i.DisabilityPeriod(
            date(1990, 4, 1), date(1990, 12, 31), special_insured=True
        ),
        onset=date(2005, 1, 15),
        established=True,
    )
    years = history(person, MONTH, counts)
    years[1990] = _year(1990, fill)
    return person, years


EIGHTEEN = {1983: 4, 1984: 4, 1985: 2, 1987: 4, 1988: 4}
ROUTE_SHORT = {**EIGHTEEN, 1987: 3}


@pytest.mark.parametrize(
    "counts,fill,outcome",
    (
        (EIGHTEEN, None, OPEN),
        (EIGHTEEN, 0, None),
        (EIGHTEEN, 3, None),
        (EIGHTEEN, 4, UNSUPPORTED),
        (ROUTE_SHORT, None, OPEN),
        (ROUTE_SHORT, 0, UNSUPPORTED),
        (ROUTE_SHORT, 1, None),
        (ROUTE_SHORT, 4, None),
    ),
)
def test_either_bound_of_a_start_year_can_unseat_a_flagged_prior(
    counts, fill, outcome
):
    # Plain arithmetic: born 1965-06-15, she attains 21 in 1986Q2, so
    # 404.130(c) at 1990Q2 counts the 16 quarters from 1986Q3 and asks
    # eight. 404.130(b) counts the 40 quarters ending 1990Q2. With 1987 and
    # 1988's eight, 404.130(c) holds, and 1983 to 1988 give 404.130(b) 18:
    # four 1990 QCs fill 1990Q1 and 1990Q2 and bring it to 20, so no
    # placement fits the flag, while three or fewer can leave one or none
    # there. With three in 1987, 404.130(b) can't reach 20, and 404.130(c)
    # needs a 1990 QC in 1990Q1 or 1990Q2.
    _expect(outcome, *_flagged(fill, counts), MONTH)


@pytest.mark.parametrize("fill", (None, 0, 1, 2, 3, 4))
@pytest.mark.parametrize(
    "record,counts",
    (
        pytest.param(_unflagged, {**SIXTEEN, 1985: 4}, id="unflagged"),
        pytest.param(_flagged, {**EIGHTEEN, 1983: 3}, id="flagged"),
    ),
)
def test_a_prior_every_completion_supports_keeps_the_input_error(
    record, counts, fill
):
    # Plain arithmetic: four 1985 QCs give the unflagged prior 20 of the 40
    # quarters ending 1990Q1, and 20 QCs, whatever 1989 holds. Three 1983
    # QCs hold the flagged prior's 404.130(b) count at 19 or fewer whatever
    # 1990 holds, and 1987 and 1988 keep 404.130(c)'s eight.
    _invalid(*record(fill, counts), MONTH)


@pytest.mark.parametrize("fill", (None, 0, 1, 4))
def test_a_flag_that_carries_the_prior_keeps_the_input_error(fill):
    # Plain arithmetic: a deemed fully insured status supplies the 18 QCs
    # past blindness asks for, so the flag carries the prior on every
    # completion of 1989, and still no completion insures the 2005 period.
    person, years = _unflagged(fill, SIXTEEN)
    deemed = replace(
        person,
        conditions=frozenset({i.CoverageCondition.DEEMED_FULLY_INSURED}),
    )
    _invalid(deemed, years, MONTH)


# A 1953 quarter after a pre-1956 prior's start.


PRE1956_PRIOR = i.DisabilityPeriod(date(1953, 1, 1), date(1953, 3, 31))


def _pre1956(flags, open_years=(), prior=PRE1956_PRIOR):
    person = _person(
        date(1915, 3, 2),
        prior,
        onset=date(1965, 6, 15),
        established=True,
    )
    month = date(1966, 1, 1)
    years = history(person, month)
    for year, quarters in {
        1942: (True, False, False, False),
        1943: (False, False, True, True),
        1944: (True,) * 4,
        1945: (True,) * 4,
        1946: (True, False, False, False),
        1951: (True,) * 4,
        1952: (True,) * 4,
    }.items():
        years[year] = _year(year, quarters)
    years[1953] = _year(1953, flags)
    for year in open_years:
        years[year] = _year(year, None)
    return person, years, month


@pytest.mark.parametrize("flags", (None, *product((False, True), repeat=4)))
def test_a_quarter_after_the_start_can_exclude_the_pre1956_route(flags):
    # Plain arithmetic: she has 20 QCs before 1953 and one in every quarter
    # of 1951 and 1952, so RS 00301.480 B.1's counts hold at her prior's
    # start in 1953Q1. The 40 quarters ending 1953Q1 hold 19, so a 1953Q1 QC
    # meets 404.130(b) there. Without one, a 1953Q2 QC brings the 40
    # quarters ending 1953Q2 to 20, a quarter after the one the prior
    # covers, so only the any-quarter reading of RS 00301.480 A excludes
    # B.1's route, and that completion refuses by the route's name. No other
    # quarter reaches 20, and a count the rule places to suit each test would
    # put its QC in 1953Q1 and hide that completion.
    if flags is None:
        outcome = OPEN
    elif flags[1] and not flags[0]:
        outcome = (
            Reason.DISABILITY_BEFORE_1956,
            "RS00301.480 may have begun a listed prior before 1956",
        )
    else:
        outcome = None
    _expect(outcome, *_pre1956(flags))


def test_more_completions_than_the_cap_refuse_by_their_number():
    # Plain arithmetic: four UNKNOWN years from 1947 through 1950 give 16
    # quarter sets each and 65,536 completions in all, past the cap. Their
    # upper bound gives 404.130(b) 35 of the 40 quarters ending 1953Q1, so
    # some completion supports the prior.
    person, years, month = _pre1956((False,) * 4, range(1947, 1951))
    assert _refused(Reason.UNKNOWN_EARNINGS, person, years, month) == (
        COMPLETION_CAP
    )


def test_years_after_a_pre1956_start_count_at_their_upper_credits():
    # Plain arithmetic: a 1953Q1 QC brings the 40 quarters ending 1953Q1 to
    # 20, so 404.130(b) supports the prior on every completion. QCs from
    # 1956 to 1959 can only add to a later 20 of 40, so their upper credits
    # speak for their 65,536 completions, and the rule lists none of them.
    _invalid(*_pre1956((True, False, False, False), range(1956, 1960)))


def test_a_prior_before_july_1952_rests_on_lower_credits():
    # Plain arithmetic: RS 00301.480 B.1 begins no period before July 1952,
    # so a prior from January 1952 rests on 404.130(b), which more credits
    # only help. The 40 quarters ending 1952Q1 hold 16 on lower credits, so
    # the rule refuses on those without listing the 65,536 completions of
    # 1947 to 1950.
    prior = i.DisabilityPeriod(date(1952, 1, 1), date(1952, 3, 31))
    person, years, month = _pre1956((False,) * 4, range(1947, 1951), prior)
    assert _refused(Reason.UNKNOWN_EARNINGS, person, years, month) == (
        UNDECIDED
    )


# A middle completion past the boundary cap.

BOUNDARY_PRIORS = tuple(
    i.DisabilityPeriod(date(year, 10, 1), date(year + 1, 3, 31))
    for year in (1980, 1984, 1988)
)
ENDPOINT_YEARS = (1980, 1981, 1984, 1985, 1988, 1989)
FOUR_ENDPOINTS = {1980: 2, 1981: 2, 1984: 2, 1985: 2}


def _boundary(counts, fills):
    person = _person(
        date(1955, 2, 2),
        *BOUNDARY_PRIORS,
        onset=date(2005, 6, 15),
        established=True,
    )
    years = history(person, MONTH, {1977: 4, 1978: 4, 1979: 4, **counts})
    for year, fill in fills.items():
        years[year] = _year(year, fill)
    return person, years


def test_a_middle_completion_past_the_boundary_cap_refuses():
    # Plain arithmetic: each prior runs from a fourth quarter to the next
    # first quarter, so each of its two years keeps four quarters open, and
    # two QCs there have six assignments. Four such years give 1,296, and two
    # QCs in each of 1988 and 1989 make 46,656, past the cap, though none or
    # four in each leave one assignment there. Past blindness supports each
    # prior on the 12 QCs from 1977 to 1979, and no QC follows 1989.
    person, years = _boundary(FOUR_ENDPOINTS, {1988: None, 1989: None})
    assert (
        _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, MONTH)
        == BOUNDARY_GUARD
    )
    person, years = _boundary(FOUR_ENDPOINTS, {1988: 2, 1989: 2})
    assert (
        _refused(Reason.ASSIGNMENT_COMPLEXITY, person, years, MONTH)
        == BOUNDARY_CAP
    )
    for fills in product((0, 4), repeat=2):
        fills = dict(zip((1988, 1989), fills, strict=True))
        _invalid(*_boundary(FOUR_ENDPOINTS, fills), MONTH)


def test_endpoint_years_within_the_cap_keep_the_input_error():
    # Plain arithmetic: two endpoint years with two QCs give 36, and the two
    # open years can multiply that by at most 36, to 1,296.
    counts = {1980: 2, 1981: 2}
    _invalid(*_boundary(counts, {1988: None, 1989: None}), MONTH)
    for fills in product(range(5), repeat=2):
        fills = dict(zip((1988, 1989), fills, strict=True))
        _invalid(*_boundary(counts, fills), MONTH)


def _one_each(changes=None):
    """One QC in each endpoint year, with its four assignments."""
    credits = dict.fromkeys(ENDPOINT_YEARS, ((), 1))
    credits.update(changes or {})
    return credits


def test_the_boundary_guard_refuses_only_past_4096():
    # Plain arithmetic: one QC in four open quarters has four assignments, so
    # six endpoint years give exactly 4,096, which the cap allows. A 1989
    # that can hold two has six, and 6,144 exceeds the cap.
    person = _person(date(1955, 2, 2), *BOUNDARY_PRIORS)
    lower = _one_each({1989: ((), 0)})
    i._refuse_boundary_completions(person, lower, _one_each())
    with pytest.raises(
        i.InsuredConfigurationUnsupported, match=BOUNDARY_GUARD
    ):
        i._refuse_boundary_completions(
            person, lower, _one_each({1989: ((), 2)})
        )


def test_known_endpoint_years_leave_the_cap_to_the_record():
    # Plain arithmetic: two QCs in each of six endpoint years have 46,656
    # assignments, but with no year open every world is the record's own,
    # and ``_boundary_variants`` counts its assignments.
    person = _person(date(1955, 2, 2), *BOUNDARY_PRIORS)
    known = dict.fromkeys(ENDPOINT_YEARS, ((), 2))
    i._refuse_boundary_completions(person, known, known)


def test_the_boundary_guard_leaves_fixed_quarters_out():
    # Plain arithmetic: a deferred year before 1978 with two fixed quarters
    # can add none, one or both of the other two, so it has at most two
    # assignments, and six such endpoint years give 64. Counting all four
    # quarters as open would give six each and 46,656.
    priors = tuple(
        i.DisabilityPeriod(date(year, 10, 1), date(year + 1, 3, 31))
        for year in (1960, 1964, 1968)
    )
    person = _person(date(1935, 2, 2), *priors)
    endpoints = (1960, 1961, 1964, 1965, 1968, 1969)
    lower = {year: ((year * 4, year * 4 + 1), 0) for year in endpoints}
    upper = {year: ((year * 4, year * 4 + 1), 2) for year in endpoints}
    i._refuse_boundary_completions(person, lower, upper)


def test_the_boundary_guard_counts_no_quarter_after_death():
    # Plain arithmetic: a death in 1989Q2 leaves 1989 two quarters, where one
    # QC has two assignments and two have one, so 1,024 times two stays
    # within the cap.
    person = _person(
        date(1955, 2, 2), *BOUNDARY_PRIORS, death_date=date(1989, 5, 10)
    )
    lower = _one_each({1989: ((), 0)})
    i._refuse_boundary_completions(person, lower, _one_each({1989: ((), 2)}))


# The completions of open years.


def test_completions_list_quarter_sets_before_1978_and_counts_after():
    lower = {1977: ((), 0), 1978: ((), 0), 1979: ((), 2)}
    upper = {1977: ((), 4), 1978: ((), 4), 1979: ((), 2)}
    found = list(i._completions(lower, upper, 1979))
    assert len(found) == 16 * 5
    assert {c[1977] for c in found} == {
        (tuple(1977 * 4 + q for q in range(4) if flags[q]), 0)
        for flags in product((False, True), repeat=4)
    }
    assert {c[1978] for c in found} == {((), n) for n in range(5)}
    assert all(c[1979] == ((), 2) for c in found)
    # Years after ``last`` keep their upper credits.
    later = {c[1978] for c in i._completions(lower, upper, 1977)}
    assert later == {((), 4)}


def test_completions_keep_a_deferred_year_s_fixed_quarters():
    # A deferred year before 1978 credits its fixed quarters on every
    # completion and may add any of the other three.
    fixed = (1960 * 4 + 1,)
    found = list(i._completions({1960: (fixed, 0)}, {1960: (fixed, 3)}, 1960))
    assert len(found) == 8
    assert all(set(fixed) <= set(c[1960][0]) for c in found)


@pytest.mark.parametrize(
    "first,years,refused",
    ((1978, 5, False), (1978, 6, True), (1960, 3, False), (1960, 4, True)),
)
def test_completions_refuse_past_4096(first, years, refused):
    # Plain arithmetic: five counts a year give 3,125 for five years and
    # 15,625 for six; 16 quarter sets a year give 4,096 for three years and
    # 65,536 for four.
    span = range(first, first + years)
    lower = dict.fromkeys(span, ((), 0))
    upper = dict.fromkeys(span, ((), 4))
    completions = i._completions(lower, upper, first + years)
    if refused:
        with pytest.raises(
            i.InsuredConfigurationUnsupported, match=COMPLETION_CAP
        ):
            next(completions)
    else:
        assert next(completions).keys() == upper.keys()


# Properties on invented records.


def _draw(rng):
    """Listed priors before an established current period, with open years."""
    early = rng.random() < 0.25
    if early:
        birth = date(rng.randint(1900, 1925), rng.randint(1, 12), 2)
        start = max(
            date(rng.randint(1952, 1955), rng.choice((1, 4, 7, 10)), 1),
            date(1952, 7, 1),
        )
    else:
        birth = date(rng.randint(1925, 1972), rng.randint(1, 12), 2)
        start = date(
            birth.year + rng.randint(22, 44), rng.choice((1, 4, 7, 10)), 1
        )
    priors = []
    for _ in range(1 if rng.random() < 0.7 else 2):
        end = start + timedelta(days=rng.randint(60, 900))
        young = start < date(birth.year + 31, birth.month, birth.day)
        flagged = young and not early and rng.random() < 0.5
        priors.append(i.DisabilityPeriod(start, end, special_insured=flagged))
        later = end + timedelta(days=rng.randint(200, 2000))
        start = date(later.year, rng.choice((1, 4, 7, 10)), 1)
    onset = date(
        priors[-1].end.year + rng.randint(6, 14), rng.randint(1, 12), 15
    )
    month = date(onset.year + 1, 1, 1)
    person = _person(
        birth,
        *priors,
        onset=onset,
        established=True,
        sex=rng.choice((FEMALE, MALE)),
    )
    years = history(person, month)
    first = max(1937, birth.year + 16)
    density = rng.choice((0.3, 0.6, 0.85))
    for year in range(first, min(priors[-1].end.year + 1, month.year) + 1):
        if rng.random() < density:
            if year < 1978:
                fill = tuple(rng.random() < 0.75 for _ in range(4))
            else:
                fill = rng.randint(1, 4)
            years[year] = _year(year, fill)
    span = range(first, priors[-1].start.year + 1)
    unknown = sorted(rng.sample(span, rng.choice((1, 1, 2))))
    if unknown[0] < 1978:
        unknown = unknown[:1]
    for year in unknown:
        years[year] = _year(year, None)
    return person, years, month, unknown, rng.choice((ALL, DISABILITY))


def _record(seed):
    """The first record the seed's draws give that a Person accepts."""
    rng = random.Random(seed)
    while True:
        try:
            return _draw(rng)
        except i.InvalidFamilyInput:
            continue


def _fills(year):
    if year < 1978:
        return list(product((False, True), repeat=4))
    return list(range(5))


def _input_error(person, years, month, test):
    try:
        _row(person, years, month, test=test)
    except i.InvalidFamilyInput:
        return True
    return False


@PROPERTY
@given(seed=st.integers(0, 2**32 - 1))
def test_an_input_error_holds_on_every_completion(seed):
    person, years, month, unknown, test = _record(seed)
    if not _input_error(person, years, month, test):
        return
    for fills in product(*map(_fills, unknown)):
        filled = dict(years)
        for year, fill in zip(unknown, fills, strict=True):
            filled[year] = _year(year, fill)
        assert _input_error(person, filled, month, test), (unknown, fills)


def _supported(person, credits, index, month):
    try:
        i._prior_basis(person, credits, credits, index, month, None)
    except i.InsuredConfigurationUnsupported:
        return False
    return True


@PROPERTY
@given(seed=st.integers(0, 2**32 - 1))
def test_lower_credits_speak_for_every_completion_of_an_unflagged_prior(seed):
    # ``_refuse_undecided_priors`` reads an unflagged prior from 1956 on
    # lower credits alone; a search of every completion agrees.
    person, years, month, _, _ = _record(seed)
    lower = {y: i._credits(y, row, False) for y, row in years.items()}
    upper = {y: i._credits(y, row, True) for y, row in years.items()}
    for index, period in enumerate(person.prior_disability_periods):
        if period.special_insured or period.start < date(1956, 1, 1):
            continue
        every = all(
            _supported(person, credits, index, month)
            for credits in i._completions(lower, upper, period.start.year)
        )
        assert _supported(person, lower, index, month) is every
