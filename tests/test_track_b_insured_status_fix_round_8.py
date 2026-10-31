"""Statutory conformance: alternate witnesses must cover every completion.

Invented declarations and captured rules only. No population, behavioral,
payment, or forecast claim. Every public outcome retains its row and weight.
"""

import calendar
from dataclasses import replace
from datetime import date, timedelta
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_6_routes import (
    _ordinary_pre1956_case,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
QUERY = date(1968, 1, 1)
WEIGHT = Fraction(11, 5)
ALTERNATE = i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956


def _case(witness=date(1956, 4, 1), *, fra_month=5, end=None, through=None):
    person = i.Person(
        date(1895, fra_month, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1955, 7, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=end,
        current_disability_period_end_provenance=(
            OBSERVED if end is not None else UNKNOWN
        ),
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=(
            OBSERVED if through is not None else UNKNOWN
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    years = history(person, QUERY, {year: 4 for year in range(1951, 1955)})
    years[1940] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, False, False, False)
    )
    years[1955] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, False)
    )
    quarter = (witness.month - 1) // 3
    years[witness.year] = i.CoverageYear(
        OBSERVED, qc_quarters=tuple(q == quarter for q in range(4))
    )
    return person, years


def _row(person, years, *, test=i.InsuredTest.FULLY):
    return i.evaluate_insured_status(
        "round-eight-covered-witness",
        WEIGHT,
        lambda: i.insured_status(person, years, QUERY, test=test),
    )


def _assert_row(row, *, refused):
    counts = count_family_outcomes((row,))
    assert counts.rows == 1
    assert counts.weight == WEIGHT
    if refused:
        assert row.result is None
        assert row.unsupported.reason is ALTERNATE
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == WEIGHT
    else:
        assert row.unsupported is None
        assert counts.unsupported_rows == 0
        assert counts.unsupported_weight == 0
        decision = row.result.fully or row.result.disability
        assert decision.insured


@pytest.mark.parametrize("end", [date(1956, 6, 30), date(1956, 5, 31)])
@pytest.mark.parametrize("witness_month", [4, 7])
def test_declared_end_quarter_includes_witness_but_next_quarter_refuses(
    end, witness_month
):
    person, years = _case(date(1956, witness_month, 1), end=end)
    row = _row(person, years)
    _assert_row(row, refused=witness_month == 7)
    if witness_month == 4:
        assert row.result.current_disability_period_start == date(1956, 4, 1)


@pytest.mark.parametrize("later", [False, True])
def test_unknown_end_keeps_onset_witness_but_refuses_later_quarter(later):
    # Round 5's birth-1920 case already has 20/40 in the onset quarter.
    person, years, _ = _ordinary_pre1956_case()
    if later:
        years[1950] = i.CoverageYear(
            OBSERVED, qc_quarters=(False, True, True, True)
        )
        years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
        years[1955] = i.CoverageYear(
            OBSERVED, qc_quarters=(False, True, False, False)
        )
    row = _row(person, years)
    _assert_row(row, refused=later)
    if not later:
        assert row.result.current_disability_period_start == date(1955, 1, 15)


@pytest.mark.parametrize("witness_month", [4, 7])
def test_continuity_quarter_includes_witness_but_later_quarter_refuses(
    witness_month,
):
    person, years = _case(
        date(1956, witness_month, 1), through=date(1956, 5, 15)
    )
    _assert_row(_row(person, years), refused=witness_month == 7)


def test_later_disabled_quarters_with_unknown_end_keep_named_refusal():
    person, years, _ = _ordinary_pre1956_case()
    years[1950] = i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1956] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    _assert_row(_row(person, years), refused=True)


@pytest.mark.parametrize("quarter", [3, 4])
def test_october_1960_boundary_with_unknown_end_keeps_named_refusal(quarter):
    person, years, _ = _ordinary_pre1956_case()
    years[1950] = i.CoverageYear(OBSERVED, qc_quarters=(False,) * 4)
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1955] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, True, False)
    )
    years[1960] = i.CoverageYear(
        OBSERVED, qc_quarters=tuple(q == quarter for q in range(1, 5))
    )
    _assert_row(_row(person, years), refused=True)


def test_round_seven_declared_end_comparison_retains_named_refusal():
    person = i.Person(
        date(1888, 5, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1952, 7, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1952, 9, 30),
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    years = history(
        person, QUERY, {1938: 2, 1944: 4, 1945: 4, 1946: 4, 1951: 4}
    )
    years[1952] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, False, True)
    )
    years[1953] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, True, False, False)
    )
    _assert_row(_row(person, years), refused=True)


@settings(max_examples=30, deadline=None)
@example(
    mode="declared",
    covered=date(1956, 5, 31),
    witness_year=1956,
    witness_quarter=3,
    fra_month=5,
)
@example(
    mode="continuity",
    covered=date(1956, 5, 31),
    witness_year=1956,
    witness_quarter=3,
    fra_month=5,
)
@example(
    mode="unknown",
    covered=date(1956, 5, 31),
    witness_year=1956,
    witness_quarter=2,
    fra_month=5,
)
@example(
    mode="declared",
    covered=date(1960, 12, 31),
    witness_year=1960,
    witness_quarter=4,
    fra_month=12,
)
@example(
    mode="declared",
    covered=date(1960, 5, 31),
    witness_year=1960,
    witness_quarter=2,
    fra_month=4,
)
@example(
    mode="continuity",
    covered=date(1956, 5, 31),
    witness_year=1956,
    witness_quarter=2,
    fra_month=5,
)
@given(
    mode=st.sampled_from(["declared", "unknown", "continuity"]),
    covered=st.dates(min_value=date(1955, 7, 31), max_value=date(1960, 1, 31)),
    witness_year=st.sampled_from([1956, 1959, 1960]),
    witness_quarter=st.integers(1, 4),
    fra_month=st.integers(1, 12),
)
def test_independent_date_oracle_classifies_covered_quarters_both_directions(
    mode, covered, witness_year, witness_quarter, fra_month
):
    # The oracle uses plain dates only. No production quarter, FRA, coverage,
    # possibility, or witness helper participates in its expected result.
    fra_month_start = date(1960, fra_month, 1)
    if mode == "continuity":
        covered = min(covered, fra_month_start - timedelta(days=1))
    if mode == "declared":
        covered = date(
            covered.year,
            covered.month,
            calendar.monthrange(covered.year, covered.month)[1],
        )
    if mode == "unknown":
        covered = date(1955, 7, 15)
    witness = date(witness_year, (witness_quarter - 1) * 3 + 1, 1)
    excludes = (
        witness <= covered
        and witness < fra_month_start
        and witness < date(1960, 10, 1)
    )
    person, years = _case(
        witness,
        fra_month=fra_month,
        end=covered if mode == "declared" else None,
        through=covered if mode == "continuity" else None,
    )
    row = _row(person, years)
    _assert_row(row, refused=not excludes)
    assert (row.result is not None) == excludes
    assert (row.unsupported is not None) == (not excludes)


@settings(max_examples=12, deadline=None)
@given(witness_month=st.integers(1, 12), ending_month=st.integers(7, 12))
def test_unknown_end_cannot_return_status_when_declared_completion_refuses(
    witness_month, ending_month
):
    person, years = _case(date(1956, witness_month, 1))
    endings = (
        date(1955, ending_month, calendar.monthrange(1955, ending_month)[1]),
        date(1956, 12, 31),
    )
    completions = [
        _row(
            replace(
                person,
                current_disability_period_end=end,
                current_disability_period_end_provenance=OBSERVED,
            ),
            years,
        )
        for end in endings
    ]
    assert any(row.unsupported is not None for row in completions)
    for row in completions:
        _assert_row(row, refused=row.unsupported is not None)
    _assert_row(_row(person, years), refused=True)
