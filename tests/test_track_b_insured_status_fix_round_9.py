"""Statutory conformance: UNKNOWN establishment covers every completion.

Invented declarations only. No population, behavioral, payment, or forecast
claim. Public evaluator rows retain each refusal and its exact weight.
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
from tests.test_track_b_insured_status_fix_round_7 import _case

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
QUERY = date(1968, 1, 1)
WEIGHT = Fraction(7, 3)
ALTERNATE = i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956


def _declaration(person, established):
    return replace(
        person,
        current_disability_period_established=established,
        current_disability_period_provenance=(
            UNKNOWN if established is None else OBSERVED
        ),
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
        current_disability_period_continues_through=None,
        current_disability_period_continues_through_provenance=UNKNOWN,
    )


def _row(person, years, *, test=i.InsuredTest.DISABILITY):
    return i.evaluate_insured_status(
        "round-nine-unknown-establishment",
        WEIGHT,
        lambda: i.insured_status(person, years, QUERY, test=test),
    )


def _assert_row(row, reason=None):
    counts = count_family_outcomes((row,))
    assert counts.rows == 1
    assert counts.weight == WEIGHT
    if reason is None:
        assert row.unsupported is None
        assert row.result is not None
        assert counts.unsupported_rows == 0
        assert counts.unsupported_weight == 0
    else:
        assert row.result is None
        assert row.unsupported.reason is reason
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == WEIGHT


@pytest.mark.parametrize(
    "established", [None, False], ids=["unknown", "absent"]
)
@pytest.mark.parametrize("test", list(i.InsuredTest))
def test_reviewed_status_table_retains_rows_and_weights(established, test):
    person, years = _case(fra_month=5)
    row = _row(_declaration(person, established), years, test=test)
    reason = None
    if established is None:
        if test is i.InsuredTest.DISABILITY:
            reason = ALTERNATE
        elif test in (i.InsuredTest.CURRENTLY, i.InsuredTest.ALL):
            reason = i.InsuredUnsupportedReason.UNKNOWN_CURRENT_PERIOD
    _assert_row(row, reason)
    if reason is None:
        for kind, expected in (
            (i.InsuredTest.FULLY, True),
            (i.InsuredTest.CURRENTLY, False),
            (i.InsuredTest.DISABILITY, True),
        ):
            if test in (i.InsuredTest.ALL, kind):
                assert getattr(row.result, kind.value).insured is expected


def test_unknown_fully_keeps_favorable_ordinary_witness():
    # An established completion cannot take away favorable disregard.
    person, years = _case(fra_month=5)
    row = _row(_declaration(person, None), years, test=i.InsuredTest.FULLY)
    _assert_row(row)
    assert row.result.fully.insured


def _onset_case(*, later_quarter=False, witness_year=1955, witness_quarter=2):
    person, years, _ = _ordinary_pre1956_case()
    if later_quarter:
        years[1950] = i.CoverageYear(
            OBSERVED, qc_quarters=(False, True, True, True)
        )
        years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
        years[witness_year] = i.CoverageYear(
            OBSERVED,
            qc_quarters=tuple(q == witness_quarter for q in range(1, 5)),
        )
    return _declaration(person, None), years


def test_unknown_establishment_keeps_round_five_onset_quarter_witness():
    person, years = _onset_case()
    row = _row(person, years)
    _assert_row(row)
    assert row.result.disability.insured
    assert row.result.disability.qualifying_quarter == date(1955, 1, 1)


def test_unknown_establishment_refuses_witness_one_quarter_after_onset():
    person, years = _onset_case(later_quarter=True)
    _assert_row(_row(person, years), ALTERNATE)


def test_unknown_establishment_post1955_onset_keeps_ordinary_status():
    person, years = _onset_case()
    person = replace(person, disability_onset=date(1956, 1, 15))
    row = _row(person, years)
    _assert_row(row)
    assert row.result.disability.insured


@pytest.mark.parametrize("days_after_fra", [0, 14])
def test_unknown_establishment_at_or_after_fra_keeps_existing_refusal(
    days_after_fra,
):
    person, years = _case(fra_month=5)
    person = replace(
        _declaration(person, None),
        birth_date=date(1890, 7, 2),
        disability_onset=date(1955, 7, 1) + timedelta(days=days_after_fra),
    )
    _assert_row(_row(person, years), ALTERNATE)


def _completion(person, end):
    return replace(
        _declaration(person, True),
        current_disability_period_end=end,
        current_disability_period_end_provenance=(
            UNKNOWN if end is None else OBSERVED
        ),
    )


@settings(max_examples=6, deadline=None)
@example(witness_year=1955, witness_quarter=2)
@given(
    witness_year=st.sampled_from([1955, 1956]),
    witness_quarter=st.integers(2, 4),
)
def test_unknown_establishment_cannot_compute_when_completion_refuses(
    witness_year, witness_quarter
):
    person, years = _onset_case(
        later_quarter=True,
        witness_year=witness_year,
        witness_quarter=witness_quarter,
    )
    # Both endings are valid through the alternate route. The ordinary
    # witness occurs after the earliest possible declared ending.
    completions = [
        _row(_completion(person, end), years)
        for end in (date(1955, 3, 31), None)
    ]
    assert any(
        row.unsupported is not None and row.unsupported.reason is ALTERNATE
        for row in completions
    )
    for row in completions:
        _assert_row(row, ALTERNATE)
    covered = _row(_completion(person, date(1956, 12, 31)), years)
    _assert_row(covered)
    assert covered.result.disability.insured
    unknown = _row(person, years)
    _assert_row(unknown, ALTERNATE)
    assert unknown.result is None


@settings(max_examples=6, deadline=None)
@given(ending_month=st.integers(3, 12))
def test_unknown_establishment_keeps_agreed_completion_status(ending_month):
    person, years = _onset_case()
    end = date(1955, ending_month, calendar.monthrange(1955, ending_month)[1])
    # The onset-quarter witness lies within every possible established
    # completion, including the unobserved-ending declaration.
    completed = [
        _row(_completion(person, ending), years) for ending in (end, None)
    ]
    absent = _row(_declaration(person, False), years)
    for row in (*completed, absent):
        _assert_row(row)
        assert row.result.disability.insured
    unknown = _row(person, years)
    _assert_row(unknown)
    assert unknown.result.disability.insured


def _date_oracle_case(witness, fra_month):
    person = i.Person(
        date(1895, fra_month, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1955, 7, 15),
        current_disability_period_established=None,
        current_disability_period_provenance=UNKNOWN,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    years = history(person, QUERY, {year: 4 for year in range(1951, 1955)})
    years[1940] = i.CoverageYear(OBSERVED, qc_quarters=(True,) * 4)
    years[1950] = i.CoverageYear(
        OBSERVED, qc_quarters=(False, False, False, True)
    )
    years[1955] = i.CoverageYear(
        OBSERVED, qc_quarters=(True, True, False, False)
    )
    flags = list(years[witness.year].qc_quarters)
    flags[(witness.month - 1) // 3] = True
    years[witness.year] = i.CoverageYear(OBSERVED, qc_quarters=tuple(flags))
    return person, years


@settings(max_examples=12, deadline=None)
@example(witness_year=1955, witness_quarter=3, fra_month=5)
@example(witness_year=1955, witness_quarter=4, fra_month=5)
@example(witness_year=1960, witness_quarter=2, fra_month=5)
@example(witness_year=1960, witness_quarter=4, fra_month=12)
@given(
    witness_year=st.sampled_from([1955, 1956, 1959, 1960]),
    witness_quarter=st.integers(3, 4),
    fra_month=st.integers(1, 12),
)
def test_independent_date_oracle_classifies_unknown_establishment_both_ways(
    witness_year, witness_quarter, fra_month
):
    # Plain dates determine the expectation. No production date, coverage,
    # alternate-route, or disability-witness helper supplies the oracle.
    onset = date(1955, 7, 15)
    witness = date(witness_year, (witness_quarter - 1) * 3 + 1, 1)
    excludes_alternate = (
        witness <= onset
        and witness < date(1960, fra_month, 1)
        and witness < date(1960, 10, 1)
    )
    person, years = _date_oracle_case(witness, fra_month)
    row = _row(person, years)
    _assert_row(row, None if excludes_alternate else ALTERNATE)
    assert (row.result is not None) is excludes_alternate
    assert (row.unsupported is not None) is (not excludes_alternate)
    if excludes_alternate:
        assert row.result.disability.insured
