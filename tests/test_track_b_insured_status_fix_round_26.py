"""Round 26: an exit already reached gives a range where it gave a refusal.

Verification class: statutory conformance on invented declarations; no
population, behavioral or forecast claim.

With an exit already reached and an unknown ending, the date last insured runs
past the query. The disability status reads no ending, so the rule reports it
with the range the endings allow. A later ending can take a QC of the exit year
off the clock (404.146(d)), so the date can fall through the first quarter
after that year. From there a later ending only skips empty quarters, so the
date can't fall, and that quarter's ending and the last one bound the rest.

tests/test_track_b_insured_status_status_stress.py checks these ranges against
independent arithmetic. The property here compares them with the rule's own
answer for each declared ending, on a wider space of records.
"""

import random
from dataclasses import replace
from datetime import date

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
DISABILITY = i.InsuredTest.DISABILITY

MONTH = date(2021, 2, 1)
EXIT = date(2021, 1, 1)
ANNUAL = {
    2012: 4,
    2014: 1,
    2015: 2,
    **dict.fromkeys(range(2016, 2020), 4),
    2021: 3,
}


def _worker(**changes):
    values = dict(
        sex=i.Sex.FEMALE,
        disability_onset=date(2021, 2, 1),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    values.update(changes)
    return i.Person(date(1985, 2, 2), **values)


def _years(annual=ANNUAL, last=2021):
    return {
        year: i.CoverageYear(OBSERVED, qc_count=annual.get(year, 0))
        for year in range(1985, last + 1)
    }


def _status(person, exit_month=EXIT, test=DISABILITY, years=None):
    return i.insured_status(
        person,
        _years() if years is None else years,
        MONTH,
        coverage_end_month=exit_month,
        test=test,
    )


def _dli(result):
    return result.dli.lower, result.dli.upper, result.dli.right_censored


def _ended(person, ending):
    return replace(
        person,
        current_disability_period_end=ending,
        current_disability_period_end_provenance=OBSERVED,
    )


# An ending in 2021 leaves at least two of 2021's three QCs on the clock, and the
# date holds at 2025Q4. An ending in 2022Q1 makes the rest of 2021 interior
# (404.146(d)), which leaves one QC, and the date falls to 2025Q3. Each later
# ending skips one more empty quarter and adds a quarter to the date.


@pytest.mark.parametrize("exit_month", (EXIT, MONTH))
def test_the_range_runs_from_the_lowest_ending_to_retirement_age(exit_month):
    result = _status(_worker(), exit_month)
    assert result.current_disability_period_start == date(2021, 2, 1)
    assert result.disability.insured
    assert _dli(result) == (date(2025, 9, 30), date(2051, 12, 31), False)
    assert result.unknown_facts == ("current_disability_period_end",)
    assert result.decided_despite_unknowns


@pytest.mark.parametrize(
    ("ending", "last"),
    (
        (date(2021, 3, 31), date(2025, 12, 31)),
        (date(2021, 12, 31), date(2025, 12, 31)),
        (date(2022, 3, 31), date(2025, 9, 30)),
        (date(2022, 6, 30), date(2025, 12, 31)),
        (date(2023, 6, 30), date(2026, 12, 31)),
        (date(2052, 1, 31), date(2051, 12, 31)),
    ),
)
def test_each_declared_ending_has_the_date_the_range_bounds(ending, last):
    result = _status(_ended(_worker(), ending))
    assert _dli(result) == (last, last, False)


def test_all_reports_each_status_and_the_other_tests_take_no_date():
    result = _status(_worker(), test=i.InsuredTest.ALL)
    assert (
        result.fully.insured,
        result.currently.insured,
        result.disability.insured,
    ) == (True, True, True)
    assert _dli(result) == (date(2025, 9, 30), date(2051, 12, 31), False)
    for test in (i.InsuredTest.FULLY, i.InsuredTest.CURRENTLY):
        assert _status(_worker(), test=test).dli is None


def _running(through):
    return _worker(
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=OBSERVED,
    )


@pytest.mark.parametrize(
    ("through", "lower"),
    (
        # Inside the list, the observation leaves the low in place or removes it.
        (date(2022, 3, 1), date(2025, 9, 30)),
        (date(2022, 4, 15), date(2025, 12, 31)),
        # Past the list, its own quarter sets the low.
        (date(2023, 6, 30), date(2026, 12, 31)),
    ),
)
def test_a_continuity_observation_raises_the_low(through, lower):
    result = _status(_running(through))
    assert _dli(result) == (lower, date(2051, 12, 31), False)


def test_an_ending_after_the_query_alone_can_refuse_the_low():
    # Six QCs in the 12 quarters ending 2022Q1 begin the period there, and that
    # start needs 2022's one QC in 2022Q1. The period runs at least to July,
    # so every ending falls after the May query. With that QC in 2022Q4, an
    # ending in 2022Q3 dates 2023Q2, the lowest date any ending allows. With it
    # in 2022Q1, no filling passes 2023Q1 there, so the rule refuses the low.
    person = i.Person(
        date(2000, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(2021, 10, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_continues_through=date(2022, 7, 1),
        current_disability_period_continues_through_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    annual = {2019: 1, 2020: 1, 2021: 3, 2022: 1}
    month = date(2022, 5, 1)
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(
            person,
            {
                year: i.CoverageYear(OBSERVED, qc_count=annual.get(year, 0))
                for year in range(2000, 2023)
            },
            month,
            coverage_end_month=month,
            test=DISABILITY,
        )
    assert (
        error.value.reason is i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
    )
    assert error.value.detail.startswith(
        "A period ending cannot reach the lower date"
    )


def test_an_unknown_exit_year_can_split_the_cap_after_the_query():
    # The period begins in 2021Q3 on 404.130(c) alone and runs at least to
    # July, so every ending falls after the May query. The range's high end
    # reads the unknown 2022 with four QCs. For an ending in 2022Q3, with the
    # periods set aside, 23 of the 47 quarters from age 21 through 2024Q4 hold
    # QCs, half of them rounded down, but only 19 of the last 40 do. The two
    # readings of the subsequent-special cap differ there, so the rule refuses.
    person = i.Person(
        date(1992, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(2021, 7, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_continues_through=date(2022, 7, 1),
        current_disability_period_continues_through_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    years = {
        year: i.CoverageYear(OBSERVED, qc_count=2 if year >= 2013 else 0)
        for year in range(1992, 2021)
    }
    years[2021] = i.CoverageYear(OBSERVED, qc_count=3)
    years[2022] = i.CoverageYear(UNKNOWN)
    month = date(2022, 5, 1)
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(
            person, years, month, coverage_end_month=month, test=DISABILITY
        )
    assert (
        error.value.reason is i.InsuredUnsupportedReason.SUBSEQUENT_LONG_PERIOD
    )


@pytest.mark.parametrize(
    ("death", "lower", "upper"),
    (
        (date(2030, 5, 10), date(2025, 9, 30), date(2030, 6, 30)),
        (date(2021, 8, 10), date(2021, 9, 30), date(2021, 9, 30)),
    ),
)
def test_death_caps_the_range_and_the_list(death, lower, upper):
    result = _status(_worker(death_date=death))
    assert _dli(result) == (lower, upper, False)


@pytest.mark.parametrize("exit_month", (None, date(2021, 3, 1)))
def test_no_exit_by_the_query_keeps_the_date_at_the_query(exit_month):
    result = _status(_worker(), exit_month)
    assert _dli(result) == (date(2021, 3, 31), date(2021, 3, 31), True)


def test_an_unknown_year_widens_the_range_past_every_filling():
    # 2016's row can hold up to four QCs. Without them at least 23 QCs sit in
    # the 40 quarters ending 2021Q1, so each filling gives the same start.
    annual = {**ANNUAL, 2013: 4}
    years = _years(annual)
    years[2016] = i.CoverageYear(UNKNOWN)
    result = _status(_worker(), years=years)
    assert result.current_disability_period_start == date(2021, 2, 1)
    assert result.disability.insured
    found = []
    for count in range(5):
        filled = {**years, 2016: i.CoverageYear(OBSERVED, qc_count=count)}
        assert _status(_worker(), years=filled).dli.lower >= result.dli.lower
        for ending in (
            date(2021, 3, 31),
            date(2021, 12, 31),
            date(2022, 3, 31),
            date(2022, 6, 30),
            date(2052, 1, 31),
        ):
            dated = _status(_ended(_worker(), ending), years=filled)
            found.append(dated.dli.lower)
    assert result.dli.lower == min(found)
    assert result.dli.upper == max(found) == date(2051, 12, 31)
    assert not result.dli.right_censored


def _frozen_record(seed):
    """Draw a record across ages, sexes, priors, blindness and observation."""
    draw = random.Random(f"round-26-{seed}")
    birth = date(
        draw.randint(1955, 1990), draw.randint(1, 12), draw.choice((2, 15))
    )
    year = birth.year + draw.randint(24, 60)
    month = date(year, draw.randint(1, 12), 1)
    exit_month = date(year - draw.choice((0, 0, 0, 1, 2)), 1, 1)
    exit_month = exit_month.replace(
        month=draw.randint(1, month.month if exit_month.year == year else 12)
    )
    quarter = i._qid(month) - draw.choice((0, 0, 1, 1, 2, 3, 4, 6, 8))
    onset = date(
        quarter // 4,
        3 * (quarter % 4) + draw.randint(1, 3),
        draw.choice((1, 15)),
    )
    onset = min(onset, month)
    style = draw.choice(("recent", "recent", "gappy", "thin"))
    annual = {}
    for credited in range(birth.year + 18, exit_month.year + 1):
        share = {
            "recent": 0.9 if credited >= exit_month.year - 9 else 0.3,
            "gappy": 0.5,
            "thin": 0.2 if credited < exit_month.year - 5 else 0.9,
        }[style]
        if draw.random() < share:
            annual[credited] = draw.choice((4, 4, 3, 2, 1))
    prior = ()
    if draw.random() < 0.15 and birth.year + 22 < onset.year - 4:
        begins = date(
            birth.year + 22 + draw.randint(0, onset.year - birth.year - 27),
            draw.choice((1, 4, 7, 10)),
            1,
        )
        ends = date(begins.year + draw.randint(0, 2), 12, 31)
        if ends < onset:
            special = begins.year < birth.year + 30 and draw.random() < 0.5
            prior = (
                i.DisabilityPeriod(begins, ends, special_insured=special),
            )
    changes = dict(
        sex=draw.choice((i.Sex.FEMALE, i.Sex.MALE)),
        disability_onset=onset,
        prior_disability_periods=prior,
        statutory_blindness=draw.random() < 0.05,
    )
    if draw.random() < 0.2:
        changes.update(
            current_disability_period_continues_through=date(
                onset.year + draw.randint(1, 3), 6, 30
            ),
            current_disability_period_continues_through_provenance=OBSERVED,
        )
    person = i.Person(
        birth,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        **changes,
    )
    years = {
        credited: (
            i.CoverageYear(OBSERVED, qc_count=annual.get(credited, 0))
            if credited >= 1978
            else i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
        )
        for credited in range(birth.year, exit_month.year + 1)
    }
    return person, years, month, exit_month


def _endings(person, years, month, exit_month):
    """Each ending through the list's last quarter, then a sample to the cap.

    The sample starts with that quarter, so it runs where no date can fall.
    """
    credits = {
        year: i._credits(year, row, False) for year, row in years.items()
    }
    completed, start = i._with_current_period(
        person, credits, month, exit_month
    )
    cap = completed.prior_disability_periods[-1].end
    first = i._qid(start)
    through = person.current_disability_period_continues_through
    if through is not None:
        first = max(first, i._qid(through))
    last = max(i._qid(month), (exit_month.year + 1) * 4, first)
    listed = [
        *(i._qend(quarter) for quarter in range(first, last + 1)),
        *(i._qend(quarter) for quarter in range(last + 1, i._qid(cap), 5)),
    ]
    ends = [end for end in listed if end < cap] + [cap]
    return ends, min(i._qend(last), cap)


@settings(max_examples=12, deadline=None, derandomize=True)
@example(seed=30)
@example(seed=54)
@example(seed=82)
@given(seed=st.integers(0, 2**32 - 1))
def test_every_declared_ending_fits_the_range(seed):
    person, years, month, exit_month = _frozen_record(seed)

    def status(completed):
        return i.insured_status(
            completed,
            years,
            month,
            coverage_end_month=exit_month,
            test=DISABILITY,
        )

    try:
        result = status(person)
    except (i.InsuredConfigurationUnsupported, InvalidFamilyInput):
        return
    start = result.current_disability_period_start
    ends, settled = _endings(person, years, month, exit_month)
    dates, refused = {}, 0
    for ending in ends:
        try:
            found = status(_ended(person, ending))
        except i.InsuredConfigurationUnsupported:
            refused += 1
            continue
        assert found.current_disability_period_start == start, (seed, ending)
        assert found.disability.insured == result.disability.insured, (
            seed,
            ending,
        )
        assert found.dli.lower == found.dli.upper, (seed, ending, found.dli)
        dates[ending] = found.dli.lower or date.min
    assert dates, seed
    found = list(dates.values())
    lower = result.dli.lower or date.min
    upper = result.dli.upper or date.min
    assert lower <= min(found), (seed, result.dli, dates)
    assert max(found) <= upper, (seed, result.dli, dates)
    later = [dates[end] for end in dates if end >= settled]
    assert later == sorted(later), (seed, dates)
    if not refused:
        assert (lower, upper) == (min(found), max(found)), (seed, dates)
