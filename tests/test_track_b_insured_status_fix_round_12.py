"""Statutory conformance: flags cannot supply missing recent credits.

Invented declarations only; no population, behavioral, or forecast claim.
The recent-rule oracle enumerates placements with plain quarter arithmetic.
"""

from dataclasses import replace
from datetime import date, timedelta
from fractions import Fraction
from itertools import combinations, product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _pre1956_case,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(11, 5)
FULLY_ROUTES = (
    i.CoverageCondition.DEEMED_FULLY_INSURED,
    i.CoverageCondition.TRANSITIONAL_INSURED,
    i.CoverageCondition.EARNED_BASIS,
    i.CoverageCondition.SIMPLIFIED_PRE1951,
)
PRE1956 = i.CoverageCondition.DISABILITY_BEFORE_1956
RAW = (
    i.CoverageCondition.RAILROAD_CREDITS,
    i.CoverageCondition.FISCAL_TAXABLE_YEAR,
    i.CoverageCondition.SHORT_TAXABLE_YEAR,
)
CREDIT = (
    i.CoverageCondition.MILITARY_CREDITS,
    i.CoverageCondition.MEDICARE_GOVERNMENT_EMPLOYMENT,
)


def _person(
    *,
    birth=date(1960, 2, 2),
    onset=date(2000, 1, 15),
    end=date(2000, 12, 31),
    conditions=(),
    **kwargs,
):
    return i.Person(
        birth,
        sex=i.Sex.FEMALE,
        disability_onset=onset,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=end,
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        conditions=conditions,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        **kwargs,
    )


def _evaluate(person, years, month=date(2001, 1, 1), **kwargs):
    return i.evaluate_insured_status(
        "round-twelve-recent-rule",
        WEIGHT,
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY, **kwargs
        ),
    )


def _refusal(person, years, reason, month=date(2001, 1, 1), **kwargs):
    row = _evaluate(person, years, month, **kwargs)
    assert row.result is None
    assert row.unsupported.reason is reason
    counts = count_family_outcomes((row,))
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == WEIGHT
    return row


def _invalid(person, years, month=date(2001, 1, 1), **kwargs):
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match="no possible insured"):
        rows.append(_evaluate(person, years, month, **kwargs))
    counts = count_family_outcomes(rows)
    assert counts.rows == counts.unsupported_rows == 0
    assert counts.weight == counts.unsupported_weight == 0


def _reason(condition):
    return i.InsuredUnsupportedReason[condition.name]


def _q(value):
    return value.year * 4 + (value.month - 1) // 3


def _fixed_history(person, month, quarters, *, end=None):
    """All credited quarters here precede 1978, so no placement is hidden."""
    years = history(person, month, end=end)
    for year in years:
        flags = tuple(year * 4 + quarter in quarters for quarter in range(4))
        assert year < 1978 or not any(flags)
        if year < 1978:
            years[year] = i.CoverageYear(OBSERVED, qc_quarters=flags)
    return years


def _recent_oracle(
    person, years, horizon, *, exit_month=None, prior_treatment=None
):
    """Existence under 404.130(b)-(d), without implementation helpers.

    Annual counts are assigned to every possible eligible set. Each prior
    period is considered together with all the others, or all are ignored.
    Credited endpoints remain in the clock; uncredited period quarters do
    not. Candidate quarters inside any represented prior period are barred.
    """
    first_candidate = _q(person.disability_onset)
    last_candidate = _q(horizon)
    age31 = person.birth_date.replace(year=person.birth_date.year + 31)
    age31 -= timedelta(days=1)
    age21 = person.birth_date.replace(year=person.birth_date.year + 21)
    age21 -= timedelta(days=1)
    for candidate in range(first_candidate, last_candidate + 1):
        if any(
            _q(period.start) <= candidate <= _q(period.end)
            for period in person.prior_disability_periods
        ):
            continue
        treatments = (
            (True, False) if person.prior_disability_periods else (True,)
        )
        if prior_treatment is not None:
            treatments = (prior_treatment,)
        for use_periods in treatments:
            periods = person.prior_disability_periods if use_periods else ()
            options = []
            for year, row in years.items():
                last = min(
                    candidate,
                    _q(person.death_date) if person.death_date else candidate,
                    _q(exit_month) if exit_month else candidate,
                )
                eligible = tuple(
                    quarter
                    for quarter in range(year * 4, year * 4 + 4)
                    if _q(person.birth_date) <= quarter <= last
                    and not any(
                        _q(period.start) < quarter < _q(period.end)
                        for period in periods
                    )
                )
                if row.qc_quarters is not None:
                    fixed = tuple(
                        year * 4 + quarter
                        for quarter, flag in enumerate(row.qc_quarters)
                        if flag and year * 4 + quarter in eligible
                    )
                    options.append((fixed,))
                else:
                    count = 4 if row.provenance is UNKNOWN else row.qc_count
                    assert count is not None
                    options.append(
                        tuple(
                            combinations(eligible, min(count, len(eligible)))
                        )
                    )
            for placement in product(*options):
                credits = {
                    quarter for annual in placement for quarter in annual
                }

                def allowed(quarter, *, credits=credits, periods=periods):
                    return not any(
                        _q(period.start) <= quarter <= _q(period.end)
                        and quarter not in credits
                        for period in periods
                    )

                ordinary = []
                quarter = candidate
                while len(ordinary) < 40:
                    if allowed(quarter):
                        ordinary.append(quarter)
                    quarter -= 1
                if len(credits.intersection(ordinary)) >= 20:
                    return True
                if candidate >= _q(age31) and not any(
                    period.special_insured
                    for period in person.prior_disability_periods
                ):
                    continue
                elapsed = [
                    quarter
                    for quarter in range(
                        max(1937 * 4, _q(age21) + 1), candidate + 1
                    )
                    if allowed(quarter)
                ]
                if len(elapsed) < 12:
                    special, needed = ordinary[:12], 6
                elif len(elapsed) > 40:
                    special, needed = elapsed[-40:], 20
                else:
                    special, needed = elapsed, max(6, len(elapsed) // 2)
                if len(credits.intersection(special)) >= needed:
                    return True
    return False


@pytest.mark.parametrize("condition", FULLY_ROUTES)
@pytest.mark.parametrize("total", [19, 20])
@pytest.mark.parametrize("flagged", [False, True])
def test_old_lifetime_credits_cannot_supply_any_recent_window(
    condition, total, flagged
):
    person = _person(conditions=(condition,) if flagged else ())
    counts = {year: 4 for year in range(1978, 1983)}
    counts[1982] -= 20 - total
    years = history(person, date(2001, 1, 1), counts)
    assert not _recent_oracle(
        person, years, person.current_disability_period_end
    )
    _invalid(person, years)


@pytest.mark.parametrize("condition", FULLY_ROUTES)
def test_fully_route_relaxes_only_fully_insured_when_recent_rule_passes(
    condition,
):
    person = _person(birth=date(1940, 2, 2))
    years = history(
        person, date(2001, 1, 1), {year: 4 for year in range(1995, 2000)}
    )
    assert _recent_oracle(person, years, person.current_disability_period_end)
    _invalid(person, years)
    _refusal(
        replace(person, conditions=(condition,)), years, _reason(condition)
    )


@pytest.mark.parametrize("old_by_one", [False, True])
def test_scan_includes_onset_and_the_earliest_quarter_of_forty(old_by_one):
    person = _person(
        birth=date(1910, 2, 2),
        onset=date(1962, 1, 15),
        end=date(1962, 5, 31),
        conditions=(FULLY_ROUTES[0],),
    )
    month = date(1968, 1, 1)
    onset = 1962 * 4
    credited = set(range(1957 * 4, 1961 * 4 + 3))
    assert len(credited) == 19
    credited.add(onset - 39 - old_by_one)
    years = _fixed_history(person, month, credited)
    if old_by_one:
        _invalid(person, years, month)
    else:
        _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


@pytest.mark.parametrize("after_recovery", [False, True])
def test_scan_includes_horizon_quarter_and_stops_at_recovery_bound(
    after_recovery,
):
    person = _person(
        birth=date(1910, 2, 2),
        onset=date(1962, 1, 15),
        end=date(1962, 5, 31),
        conditions=(FULLY_ROUTES[0],),
    )
    month = date(1968, 1, 1)
    credited = set(range(1957 * 4, 1961 * 4 + 3))
    credited.add(1962 * 4 + after_recovery)
    years = _fixed_history(person, month, credited)
    if after_recovery:
        _invalid(person, years, month)
    else:
        _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


@pytest.mark.parametrize("short", [False, True])
def test_scan_reaches_last_candidate_quarter_even_with_end_inside_quarter(
    short,
):
    person = _person(
        birth=date(1910, 2, 2),
        onset=date(1962, 1, 15),
        end=date(1962, 8, 31),
        conditions=(FULLY_ROUTES[0],),
    )
    month = date(1968, 1, 1)
    credited = set(range(1957 * 4, 1961 * 4 + 3))
    credited.add(1962 * 4 + (2 if short else 1))
    years = _fixed_history(person, month, credited)
    if short:
        _invalid(person, years, month)
    else:
        _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


@pytest.mark.parametrize("special", ["under31", "subsequent"])
@pytest.mark.parametrize("short", [False, True])
def test_special_recent_requirement_and_one_short(special, short):
    prior = (
        ()
        if special == "under31"
        else (
            i.DisabilityPeriod(
                date(2010, 1, 1), date(2010, 12, 31), special_insured=True
            ),
        )
    )
    person = _person(
        birth=date(1993 if special == "under31" else 1980, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
        conditions=(FULLY_ROUTES[0],),
        prior_disability_periods=prior,
    )
    month = date(2023, 1, 1)
    required = 16 if special == "under31" else 20
    total = required - short
    counts = {}
    for year in range(2021, 2005, -1):
        counts[year], total = min(total, 4), max(0, total - 4)
    years = history(person, month, counts)
    assert _recent_oracle(
        person, years, person.current_disability_period_end
    ) is (not short)
    if short:
        _invalid(person, years, month)
    else:
        _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


@pytest.mark.parametrize("short", [False, True])
def test_subsequent_special_recent_rule_can_pass_below_twenty_qcs(short):
    person = _person(
        birth=date(1990, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
        conditions=(FULLY_ROUTES[0],),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(2015, 1, 1), date(2017, 12, 31), special_insured=True
            ),
        ),
    )
    month = date(2023, 1, 1)
    counts = {year: 4 for year in range(2018, 2022)}
    counts[2021] -= short
    years = history(person, month, counts)
    # After the age-21 quarter, 44 elapsed quarters minus the 12-quarter
    # prior period leave 32: Rule III needs 16, while Rule I still needs 20.
    assert sum(row.qc_count or 0 for row in years.values()) == 16 - short
    assert _recent_oracle(person, years, date(2022, 1, 1)) is (not short)
    if short:
        _invalid(person, years, month)
    else:
        _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


def _prior_case(*, disregard):
    person = _person(
        birth=date(1910, 2, 2),
        onset=date(1970, 1, 15),
        end=date(1970, 12, 31),
        conditions=(FULLY_ROUTES[0],),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1960, 1, 1), date(1965, 12, 31)),
        ),
    )
    month = date(1973, 1, 1)
    if disregard:
        credited = set(range(1961 * 4, 1966 * 4))
    else:
        credited = set(range(1955 * 4, 1960 * 4))
    return person, _fixed_history(person, month, credited), month


@pytest.mark.parametrize("disregard", [False, True])
def test_recent_window_uses_all_prior_periods_or_disregards_all(disregard):
    person, years, month = _prior_case(disregard=disregard)
    assert _recent_oracle(person, years, date(1970, 10, 1))
    assert _recent_oracle(
        person, years, date(1970, 10, 1), prior_treatment=not disregard
    )
    assert not _recent_oracle(
        person, years, date(1970, 10, 1), prior_treatment=disregard
    )
    _refusal(person, years, _reason(FULLY_ROUTES[0]), month)


def test_candidate_inside_prior_period_does_not_supply_recent_witness():
    person = _person(
        birth=date(1910, 2, 2),
        onset=date(1970, 2, 15),
        end=date(1970, 12, 31),
        conditions=(FULLY_ROUTES[0],),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1960, 1, 1), date(1970, 1, 31)),
        ),
    )
    month = date(1973, 1, 1)
    # Disregard yields twenty at the overlapped onset quarter only. The
    # first of those QCs ages out before the first usable candidate.
    credited = {1960 * 4 + 1, *range(1965 * 4, 1969 * 4 + 3)}
    years = _fixed_history(person, month, credited)
    assert not _recent_oracle(person, years, date(1970, 10, 1))
    _invalid(person, years, month)


@pytest.mark.parametrize("condition", FULLY_ROUTES)
def test_fully_route_keeps_alternate_when_ordinary_recent_rule_is_closed(
    condition,
):
    person, years, month = _pre1956_case()
    person = replace(person, conditions=(condition,))
    assert not _recent_oracle(person, years, person.disability_onset)
    _refusal(person, years, _reason(condition), month)


@pytest.mark.parametrize("condition", FULLY_ROUTES)
@pytest.mark.parametrize("exception", ["blindness", "unknown-prior"])
def test_empty_windows_keep_fully_route_blindness_and_unknown_prior_bypasses(
    condition, exception
):
    person = _person(conditions=(condition,))
    if exception == "blindness":
        person = replace(person, statutory_blindness=True)
    else:
        person = replace(person, prior_disability_periods_provenance=UNKNOWN)
    # Missing prior history can move a window, but cannot remove its floor.
    # Six old credits keep this fixture about the empty recent windows.
    counts = {1980: 4, 1981: 2} if exception == "unknown-prior" else {}
    years = history(person, date(2001, 1, 1), counts)
    _refusal(person, years, _reason(condition))
    if exception == "unknown-prior":
        _invalid(person, history(person, date(2001, 1, 1)))


@pytest.mark.parametrize("condition", FULLY_ROUTES)
def test_unknown_recent_years_and_every_surviving_filling_keep_flag_reason(
    condition,
):
    person = _person(conditions=(condition,))
    years = history(
        person, date(2001, 1, 1), {year: 4 for year in range(1995, 1999)}
    )
    years[1999] = i.CoverageYear(UNKNOWN)
    _refusal(person, years, _reason(condition))
    for count in range(5):
        filling = {**years, 1999: i.CoverageYear(OBSERVED, qc_count=count)}
        if count == 4:
            _refusal(person, filling, _reason(condition))
        else:
            _invalid(person, filling)


def test_deferred_conversion_keeps_original_refusal_with_possible_recent_rule():
    person = _person(
        birth=date(1900, 2, 2),
        onset=date(1957, 1, 15),
        end=date(1957, 12, 31),
        conditions=(FULLY_ROUTES[0],),
    )
    month = date(1968, 1, 1)
    years = history(person, month, {year: 4 for year in range(1952, 1957)})
    years[1937] = i.CoverageYear(OBSERVED, quarterly_wages=(Fraction(50),) * 4)
    _refusal(person, years, i.InsuredUnsupportedReason.EARNINGS_1937, month)


def test_pre1956_flag_cannot_open_a_route_after_1955():
    person = _person(conditions=(PRE1956,))
    years = history(
        person, date(2001, 1, 1), {year: 4 for year in range(1978, 1983)}
    )
    _invalid(person, years)


def test_pre1956_flag_keeps_named_refusal_when_alternate_conditions_hold():
    person, years, month = _pre1956_case()
    _refusal(
        replace(person, conditions=(PRE1956,)), years, _reason(PRE1956), month
    )


def test_pre1956_flag_keeps_named_refusal_when_ordinary_route_is_open():
    person = _person(conditions=(PRE1956,))
    years = history(
        person, date(2001, 1, 1), {year: 4 for year in range(1995, 2000)}
    )
    _refusal(person, years, _reason(PRE1956))


def test_complexity_preserves_fully_route_reason():
    periods = tuple(
        i.DisabilityPeriod(date(year, 1, 1), date(year, 6, 30))
        for year in range(1980, 1988)
    )
    person = _person(
        conditions=(FULLY_ROUTES[0],), prior_disability_periods=periods
    )
    counts = {year: 2 for year in range(1980, 1988)}
    counts[1999] = 4
    years = history(person, date(2001, 1, 1), counts)
    _refusal(person, years, _reason(FULLY_ROUTES[0]))


@pytest.mark.parametrize("condition", (*CREDIT, *RAW))
def test_credit_and_unbounded_raw_earnings_flags_can_add_recent_credits(
    condition,
):
    person = _person(conditions=(condition,))
    years = history(person, date(2001, 1, 1))
    if condition in RAW:
        years[1999] = i.CoverageYear(OBSERVED, wages=Fraction(0))
    _refusal(person, years, _reason(condition))


@settings(max_examples=48, deadline=None)
@example(age=29, recent=0, old=20, condition=FULLY_ROUTES[0])
@example(age=42, recent=0, old=20, condition=PRE1956)
@given(
    age=st.sampled_from([24, 29, 31, 42]),
    recent=st.integers(0, 24),
    old=st.integers(0, 24),
    condition=st.sampled_from((*FULLY_ROUTES, *RAW, PRE1956)),
)
def test_independent_recent_oracle_proves_no_credit_flag_impossibility(
    age, recent, old, condition
):
    person = _person(
        birth=date(2022 - age, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
        conditions=(condition,),
    )
    counts = {}
    for year in range(2021, 2015, -1):
        counts[year], recent = min(recent, 4), max(0, recent - 4)
    # Older QCs are outside every candidate 40-quarter window. Some young
    # records have no room for this old history and simply retain zero.
    for year in range(2009, max(1937, person.birth_date.year) - 1, -1):
        counts[year], old = min(old, 4), max(0, old - 4)
    month = date(2023, 1, 1)
    years = history(person, month, counts)
    possible = _recent_oracle(
        person, years, person.current_disability_period_end
    )
    if not possible:
        _invalid(person, years, month)
    elif condition in FULLY_ROUTES:
        _refusal(person, years, _reason(condition), month)


@settings(max_examples=40, deadline=None)
@example(age=42, recent=0, old=24, condition=FULLY_ROUTES[0])
@example(age=60, recent=20, old=0, condition=FULLY_ROUTES[0])
@given(
    age=st.sampled_from([24, 29, 42, 60]),
    recent=st.integers(0, 24),
    old=st.integers(0, 24),
    condition=st.sampled_from(FULLY_ROUTES),
)
def test_fully_flag_changes_fully_only_against_unflagged_recent_oracle(
    age, recent, old, condition
):
    person = _person(
        birth=date(2022 - age, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
    )
    counts = {}
    for year in range(2021, 2015, -1):
        counts[year], recent = min(recent, 4), max(0, recent - 4)
    for year in range(2009, max(1937, person.birth_date.year) - 1, -1):
        counts[year], old = min(old, 4), max(0, old - 4)
    month = date(2023, 1, 1)
    years = history(person, month, counts)
    recent_possible = _recent_oracle(
        person, years, person.current_disability_period_end
    )
    flagged = replace(person, conditions=(condition,))
    if recent_possible:
        _refusal(flagged, years, _reason(condition), month)
    else:
        _invalid(flagged, years, month)


@settings(max_examples=40, deadline=None)
@example(age=60, count=4, quarter=0)
@given(
    age=st.sampled_from([24, 29, 42, 60]),
    count=st.integers(0, 4),
    quarter=st.integers(0, 3),
)
def test_witness_keyword_only_relaxes_fully_prerequisite(age, count, quarter):
    person = _person(
        birth=date(2022 - age, 2, 2),
        onset=date(2022, 1, 15),
        end=date(2022, 12, 31),
    )
    years = history(
        person, date(2023, 1, 1), {year: count for year in range(2017, 2022)}
    )
    credits = {
        year: i._credits(year, row, True) for year, row in years.items()
    }
    at = date(2022, quarter * 3 + 1, 1)
    ordinary = i._witness(person, credits, at, None, i.InsuredTest.DISABILITY)
    relaxed = i._witness(
        person,
        credits,
        at,
        None,
        i.InsuredTest.DISABILITY,
        ignore_fully_insured=True,
    )
    assert not ordinary[0] or relaxed[0]
    assert relaxed[1:] == ordinary[1:]
    # An explicit divergent surface makes a no-op keyword fail too.
    if age == 60 and count == 4:
        assert not ordinary[0] and relaxed[0]


@settings(max_examples=40, deadline=None)
@example(old=14, continuous=6, condition=FULLY_ROUTES[0])
@example(old=13, continuous=6, condition=FULLY_ROUTES[0])
@given(
    old=st.integers(0, 16),
    continuous=st.integers(0, 6),
    condition=st.sampled_from(FULLY_ROUTES),
)
def test_fully_flag_exactness_includes_independent_alternate_oracle(
    old, continuous, condition
):
    person = _person(
        birth=date(1900, 2, 2),
        onset=date(1952, 7, 15),
        end=date(1953, 12, 31),
        conditions=(condition,),
    )
    month = date(1968, 1, 1)
    credited = set(range(1938 * 4, 1938 * 4 + old))
    credited.update(range(1951 * 4, 1951 * 4 + continuous))
    years = _fixed_history(person, month, credited)
    recent_possible = _recent_oracle(person, years, date(1953, 10, 1))
    assert not recent_possible
    # RS00301.480 B.1 opens in July 1952. With these fixed records the
    # only possible continuous clock consists of 1951Q1 through 1952Q2;
    # every later clock contains an uncredited quarter. Old QCs are all
    # outside 40-quarter windows, and cannot exclude the alternate.
    alternate_possible = old + continuous >= 20 and continuous == 6
    if recent_possible or alternate_possible:
        _refusal(person, years, _reason(condition), month)
    else:
        _invalid(person, years, month)
