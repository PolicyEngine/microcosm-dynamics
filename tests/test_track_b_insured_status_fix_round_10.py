"""Statutory conformance for recovery months and the alternate clock.

Invented declarations only. No population, behavioral, payment, or forecast
claim. Public evaluator rows retain every refusal and its exact weight.
"""

import calendar
from dataclasses import replace
from datetime import date
from fractions import Fraction
from itertools import product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
QUERY = date(1968, 1, 1)
WEIGHT = Fraction(11, 5)
ALTERNATE = i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956


def _person(
    *,
    birth=date(1906, 1, 2),
    onset=date(1956, 7, 15),
    end=None,
    through=None,
    death=None,
    prior=(),
    prior_provenance=OBSERVED,
):
    return i.Person(
        birth,
        sex=i.Sex.FEMALE,
        death_date=death,
        disability_onset=onset,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=end,
        current_disability_period_end_provenance=(
            OBSERVED if end else UNKNOWN
        ),
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=(
            OBSERVED if through else UNKNOWN
        ),
        prior_disability_periods=prior,
        prior_disability_periods_provenance=prior_provenance,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )


def _row(person, years, month=QUERY, test=i.InsuredTest.FULLY):
    return i.evaluate_insured_status(
        "round-ten-recovery-clock",
        WEIGHT,
        lambda: i.insured_status(person, years, month, test=test),
    )


def _assert_row(row, reason=None, *, start=None):
    counts = count_family_outcomes((row,))
    assert counts.rows == 1
    assert counts.weight == WEIGHT
    if reason is None:
        assert row.unsupported is None
        assert row.result is not None
        assert counts.unsupported_rows == 0
        assert counts.unsupported_weight == 0
        if start is not None:
            assert row.result.current_disability_period_start == start
    else:
        assert row.result is None
        assert row.unsupported.reason is reason
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == WEIGHT


def _assert_invalid(call):
    rows = []
    with pytest.raises(i.InvalidFamilyInput):
        rows.append(call())
    counts = count_family_outcomes(rows)
    assert counts.rows == 0
    assert counts.weight == 0


def _twentieth_at(person, first_twenty, month=QUERY):
    years = history(person, month)
    last = first_twenty.year * 4 + (first_twenty.month - 1) // 3
    credited = set(range(last - 19, last + 1))
    for year in years:
        flags = tuple(year * 4 + q in credited for q in range(4))
        years[year] = (
            i.CoverageYear(OBSERVED, qc_quarters=flags)
            if year < 1978
            else i.CoverageYear(OBSERVED, qc_count=sum(flags))
        )
    return years


def test_review_recovery_grace_quarter_cannot_establish_current_period():
    person = _person(end=date(1962, 5, 31))
    years = history(person, QUERY, {year: 4 for year in range(1958, 1962)})
    years[1957] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, False)
    )
    years[1962] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, True, False, False)
    )
    _assert_invalid(lambda: _row(person, years))


def _alternate_case(
    witness=date(1957, 4, 1), *, end=None, through=None, fra_month=5
):
    person = _person(
        birth=date(1895, fra_month, 2),
        onset=date(1955, 7, 15),
        end=end,
        through=through,
    )
    years = history(person, QUERY, {year: 4 for year in range(1951, 1955)})
    years[1940] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, False, False, False)
    )
    years[1955] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, False)
    )
    years[witness.year] = i.CoverageYear(
        OBSERVED,
        qc_quarters=tuple(q == (witness.month - 1) // 3 for q in range(4)),
    )
    return person, years


@pytest.mark.parametrize(
    "test", [i.InsuredTest.FULLY, i.InsuredTest.DISABILITY]
)
@pytest.mark.parametrize("mode", ["declared", "continuity"])
def test_review_recovery_grace_witness_keeps_alternate_refusal(mode, test):
    person, years = _alternate_case(
        end=date(1957, 5, 31) if mode == "declared" else None,
        through=date(1957, 5, 15) if mode == "continuity" else None,
    )
    _assert_row(_row(person, years, test=test), ALTERNATE)


@pytest.mark.parametrize("end", [date(1962, 5, 31), date(1962, 6, 30)])
@pytest.mark.parametrize("next_quarter", [False, True])
def test_recovery_quarter_counts_but_next_quarter_cannot_start(
    end, next_quarter
):
    # May's recovery month is March; June's is April. A quarter qualifies
    # when any of its months is still a disabled month.
    recovery_quarter_month = 1 if end.month == 5 else 4
    start = date(1962, recovery_quarter_month + 3 * next_quarter, 1)
    person = _person(end=end)
    years = _twentieth_at(person, start)
    if next_quarter:
        _assert_invalid(lambda: _row(person, years))
    else:
        _assert_row(_row(person, years), start=start)


@pytest.mark.parametrize("paragraph_c", [False, True])
def test_january_1981_recovery_bound_stops_at_first_paragraph_c_end(
    paragraph_c,
):
    end = date(1981, 2, 28) if paragraph_c else date(1981, 1, 31)
    person = _person(birth=date(1940, 2, 2), onset=date(1975, 7, 15), end=end)
    month = date(1982, 1, 1)
    start = date(1981, 1, 1)
    years = _twentieth_at(person, start, month)
    if paragraph_c:
        _assert_row(_row(person, years, month), start=start)
    else:
        _assert_invalid(lambda: _row(person, years, month))


@pytest.mark.parametrize("fra_ending", [False, True])
def test_fra_ending_month_does_not_imply_recovery(fra_ending):
    # June FRA: May is an FRA ending, but April implies February recovery.
    end = date(1971, 5, 31) if fra_ending else date(1971, 4, 30)
    person = _person(birth=date(1906, 6, 2), onset=date(1960, 7, 15), end=end)
    month = date(1972, 1, 1)
    start = date(1971, 4, 1)
    years = _twentieth_at(person, start, month)
    if fra_ending:
        _assert_row(_row(person, years, month), start=start)
    else:
        _assert_invalid(lambda: _row(person, years, month))


@pytest.mark.parametrize("death_ending", [False, True])
def test_death_ending_month_does_not_imply_recovery(death_ending):
    # Death in May does not imply recovery in March. An April end does.
    end = date(1971, 5, 31) if death_ending else date(1971, 4, 30)
    person = _person(
        birth=date(1930, 2, 2),
        onset=date(1960, 7, 15),
        end=end,
        death=date(1971, 5, 15),
    )
    month = date(1972, 1, 1)
    start = date(1971, 4, 1)
    years = _twentieth_at(person, start, month)
    if death_ending:
        _assert_row(_row(person, years, month), start=start)
    else:
        _assert_invalid(lambda: _row(person, years, month))


@pytest.mark.parametrize("valid_gap", [False, True])
def test_recovery_month_onset_requires_smallest_two_month_gap(valid_gap):
    def evaluate():
        person = _person(
            birth=date(1930, 2, 2),
            onset=date(1960, 1, 15),
            end=date(1960, 3, 31) if valid_gap else date(1960, 2, 29),
        )
        years = history(person, QUERY, {year: 4 for year in range(1955, 1960)})
        return _row(person, years)

    if valid_gap:
        _assert_row(evaluate(), start=date(1960, 1, 15))
    else:
        _assert_invalid(evaluate)


@pytest.mark.parametrize("can_start", [False, True])
def test_recovery_horizon_cannot_open_first_statutory_alternate_quarter(
    can_start,
):
    person = _person(
        birth=date(1906, 2, 2),
        onset=date(1951, 9, 15),
        end=date(1952, 9, 30) if can_start else date(1952, 8, 31),
    )
    years = history(
        person, QUERY, {year: 4 for year in (1938, 1939, 1940, 1951)}
    )
    for year in (1941, 1952):
        years[year] = i.CoverageYear(
            OBSERVED, qc_quarters=(True, True, False, False)
        )
    # The statutory alternate first permits a July 1952 start. An August
    # end implies recovery in June; September permits that July quarter.
    if can_start:
        _assert_row(_row(person, years), ALTERNATE)
    else:
        _assert_invalid(lambda: _row(person, years))


def _continuous_case(*, prior_unknown=False):
    person = _person(
        birth=date(1906, 2, 2),
        onset=date(1955, 1, 15),
        end=date(1956, 7, 31),
        prior=(
            ()
            if prior_unknown
            else (i.DisabilityPeriod(date(1952, 7, 1), date(1954, 12, 31)),)
        ),
        prior_provenance=UNKNOWN if prior_unknown else OBSERVED,
    )
    month = date(1968, 2, 1)
    years = history(
        person, month, {year: 4 for year in (1938, 1939, 1940, 1951)}
    )
    for year in (1941, 1952):
        years[year] = i.CoverageYear(
            OBSERVED, qc_quarters=(True, True, False, False)
        )
    return person, years, month


def test_unknown_prior_continuous_clock_preserves_favorable_full_and_refuses_dib():
    person, years, month = _continuous_case(prior_unknown=True)
    empty = replace(person, prior_disability_periods_provenance=OBSERVED)
    _assert_invalid(lambda: _row(empty, years, month))
    _assert_row(_row(_continuous_case()[0], years, month), ALTERNATE)
    # Removing the hidden gaps opens the alternate route, but favorable
    # disregard already guarantees FULLY independently of prior history.
    # DISABILITY retains the unknown-period refusal rather than treating
    # the unfilled prior history as empty.
    row = _row(person, years, month)
    _assert_row(row)
    assert row.result.fully.insured
    _assert_row(
        _row(person, years, month, test=i.InsuredTest.DISABILITY),
        i.InsuredUnsupportedReason.UNKNOWN_PERIODS,
    )


def test_review_prior_period_exclusions_open_alternate_continuous_clock():
    person, years, month = _continuous_case()
    _assert_row(_row(person, years, month), ALTERNATE)


@pytest.mark.parametrize("deleted", range(20))
def test_continuous_alternate_clock_requires_each_of_twenty_qcs(deleted):
    person, years, month = _continuous_case()
    _assert_row(_row(person, years, month), ALTERNATE)
    credited = [
        (year, q)
        for year, row in years.items()
        for q, flag in enumerate(row.qc_quarters)
        if flag
    ]
    year, quarter = credited[deleted]
    flags = list(years[year].qc_quarters)
    flags[quarter] = False
    years[year] = i.CoverageYear(OBSERVED, qc_quarters=tuple(flags))
    _assert_invalid(lambda: _row(person, years, month))


@settings(max_examples=24, deadline=None)
@example(
    mode="declared",
    ending_year=1957,
    ending_month=5,
    witness_year=1957,
    witness_quarter=2,
    fra_month=5,
)
@example(
    mode="continuity",
    ending_year=1957,
    ending_month=5,
    witness_year=1957,
    witness_quarter=2,
    fra_month=5,
)
@example(
    mode="declared",
    ending_year=1957,
    ending_month=8,
    witness_year=1957,
    witness_quarter=2,
    fra_month=5,
)
@example(
    mode="continuity",
    ending_year=1957,
    ending_month=8,
    witness_year=1957,
    witness_quarter=2,
    fra_month=5,
)
@given(
    mode=st.sampled_from(["declared", "continuity", "unknown"]),
    ending_year=st.integers(1956, 1960),
    ending_month=st.integers(1, 12),
    witness_year=st.integers(1956, 1960),
    witness_quarter=st.integers(1, 4),
    fra_month=st.integers(1, 12),
)
def test_plain_date_oracle_applies_two_month_offset_in_both_directions(
    mode, ending_year, ending_month, witness_year, witness_quarter, fra_month
):
    # All expected dates are plain calendar arithmetic. The only production
    # operation used to classify the declaration is the public entry point.
    end = date(
        ending_year,
        ending_month,
        calendar.monthrange(ending_year, ending_month)[1],
    )
    if mode == "continuity":
        end = min(
            end,
            date.fromordinal(date(1960, fra_month, 1).toordinal() - 1),
        )
    onset = date(1955, 7, 15)
    index = end.year * 12 + end.month - 1 - 2
    guaranteed = max(
        onset.replace(day=1), date(index // 12, index % 12 + 1, 1)
    )
    if mode == "unknown":
        guaranteed = onset
    witness = date(witness_year, (witness_quarter - 1) * 3 + 1, 1)
    excludes = (
        witness <= guaranteed
        and witness < date(1960, fra_month, 1)
        and witness < date(1960, 10, 1)
    )
    person, years = _alternate_case(
        witness,
        fra_month=fra_month,
        end=end if mode == "declared" else None,
        through=end if mode == "continuity" else None,
    )
    row = _row(person, years)
    _assert_row(row, None if excludes else ALTERNATE)
    assert (row.result is not None) == excludes


@settings(max_examples=12, deadline=None)
@example(ending_month=4, fixed_previous=18)
@given(
    ending_month=st.sampled_from([3, 4, 5, 6, 9, 12]),
    fixed_previous=st.integers(16, 19),
)
def test_historical_end_exact_classification_matches_every_witness_filling(
    ending_month, fixed_previous
):
    person = _person(
        end=date(
            1962, ending_month, calendar.monthrange(1962, ending_month)[1]
        )
    )
    years = history(person, QUERY)
    # Credits just below twenty force a first insured quarter in 1962.
    fixed = list(range(1957 * 4, 1962 * 4))[-fixed_previous:]
    for year in range(1957, 1962):
        years[year] = i.CoverageYear(
            OBSERVED,
            qc_quarters=tuple(year * 4 + q in fixed for q in range(4)),
        )
    years[1962] = i.CoverageYear(UNKNOWN)
    index = 1962 * 12 + ending_month - 1 - 2
    recovery = date(index // 12, index % 12 + 1, 1)
    last_quarter = recovery.year * 4 + (recovery.month - 1) // 3
    any_valid = False
    for flags in product((False, True), repeat=4):
        filling = {**years, 1962: i.CoverageYear(OBSERVED, qc_quarters=flags)}
        credits = {
            year: i._credits(year, row, False) for year, row in filling.items()
        }
        # Enumerate the existing witness path directly; do not invoke the
        # new proof or public validation to determine the expected answer.
        valid = any(
            i._witness(
                person,
                credits,
                date(q // 4, (q % 4) * 3 + 1, 1),
                None,
                i.InsuredTest.DISABILITY,
            )[0]
            for q in range(1956 * 4 + 2, last_quarter + 1)
        )
        any_valid |= valid
        if valid:
            _assert_row(_row(person, filling))
        else:
            _assert_invalid(lambda filling=filling: _row(person, filling))
    if any_valid:
        row = _row(person, years)
        assert row.result is not None or row.unsupported is not None
        counts = count_family_outcomes((row,))
        assert counts.rows == 1 and counts.weight == WEIGHT
    else:
        _assert_invalid(lambda: _row(person, years))
