"""Statutory conformance: the alternate scan requires a pre-FRA month.

Invented declarations only; no population, behavioral, payment, or forecast
claim. Public evaluator rows retain refusals and their exact weights.
"""

from dataclasses import replace
from datetime import date, timedelta
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(7, 3)
QUERY = date(1968, 1, 1)


def _case(*, fra_year=1960, fra_month=4, witness_year=1960, witness_quarter=2):
    # Birth on day two makes FRA day one of the same month, 65 years later.
    fra_month_start = date(fra_year, fra_month, 1)
    person = i.Person(
        date(fra_year - 65, fra_month, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1955, 7, 15),
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=fra_month_start - timedelta(days=1),
        current_disability_period_end_provenance=OBSERVED,
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
    years[witness_year] = i.CoverageYear(
        OBSERVED,
        qc_quarters=tuple(q == witness_quarter for q in range(1, 5)),
    )
    return person, years


def _row(person, years, *, test=i.InsuredTest.FULLY, coverage_end_month=None):
    return i.evaluate_insured_status(
        "round-seven-fra",
        WEIGHT,
        lambda: i.insured_status(
            person,
            years,
            QUERY,
            test=test,
            coverage_end_month=coverage_end_month,
        ),
    )


def _assert_row(row, reason=None):
    denominator = count_family_outcomes((row,))
    assert denominator.rows == 1
    assert denominator.weight == WEIGHT
    if reason is None:
        assert row.unsupported is None
        assert denominator.unsupported_rows == 0
        assert denominator.unsupported_weight == 0
    else:
        assert row.unsupported is not None
        assert row.unsupported.reason is reason
        assert denominator.unsupported_rows == 1
        assert denominator.unsupported_weight == WEIGHT


@pytest.mark.parametrize("variant", ["reviewer", "op12", "deferred-1937"])
def test_fra_month_witness_keeps_reviewed_refusal_and_denominator(variant):
    person, years = _case()
    coverage_end_month = None
    reason = i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    if variant == "op12":
        coverage_end_month = date(1960, 6, 1)
        years = {year: row for year, row in years.items() if year <= 1960}
    elif variant == "deferred-1937":
        years[1937] = i.CoverageYear(
            OBSERVED,
            quarterly_wages=(Fraction(50),) + (Fraction(0),) * 3,
        )
        reason = i.InsuredUnsupportedReason.EARNINGS_1937
    _assert_row(
        _row(person, years, coverage_end_month=coverage_end_month), reason
    )


@pytest.mark.parametrize("fra_month", [3, 5])
def test_reviewed_fra_neighbours_preserve_their_public_results(fra_month):
    person, years = _case(fra_month=fra_month)
    row = _row(person, years)
    # Even the May-FRA ending admits February recovery, before April's
    # first 20/40 witness. It cannot exclude the alternate in every filling.
    _assert_row(row, i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956)


@pytest.mark.parametrize("fra_month", range(1, 13))
def test_fra_quarter_stays_only_when_it_begins_before_fra_month(fra_month):
    # FRA in 1959 exercises October independently of the October 1960 cap.
    quarter = (fra_month - 1) // 3 + 1
    person, years = _case(
        fra_year=1959,
        fra_month=fra_month,
        witness_year=1959,
        witness_quarter=quarter,
    )
    row = _row(person, years)
    # A possible recovery two months before the FRA ending precedes this
    # quarter even when it begins before FRA. The FRA bound still applies.
    _assert_row(row, i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956)


def _unestablished(person, state):
    return replace(
        person,
        current_disability_period_established=(
            False if state == "none" else None
        ),
        current_disability_period_provenance=(
            OBSERVED if state == "none" else UNKNOWN
        ),
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
    )


@pytest.mark.parametrize("state", ["none", "unknown"])
@pytest.mark.parametrize("witness_quarter", [2, 3])
def test_unestablished_period_keeps_alternate_after_fra(
    state, witness_quarter
):
    person, years = _case(witness_quarter=witness_quarter)
    row = _row(
        _unestablished(person, state), years, test=i.InsuredTest.DISABILITY
    )
    _assert_row(row, i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956)


def test_unestablished_period_pre_fra_neighbour_keeps_ordinary_result():
    person, years = _case(fra_month=5)
    row = _row(
        _unestablished(person, "none"), years, test=i.InsuredTest.DISABILITY
    )
    _assert_row(row)
    assert row.result.disability.insured
    assert row.result.disability.qualifying_quarter == date(1960, 4, 1)


def test_unknown_establishment_pre_fra_neighbour_keeps_alternate_refusal():
    person, years = _case(fra_month=5)
    row = _row(
        _unestablished(person, "unknown"), years, test=i.InsuredTest.DISABILITY
    )
    _assert_row(row, i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956)


@settings(max_examples=16, deadline=None)
@example(fra_month=1, witness_year=1960, witness_quarter=1)
@example(fra_month=2, witness_year=1960, witness_quarter=1)
@example(fra_month=3, witness_year=1960, witness_quarter=1)
@example(fra_month=10, witness_year=1960, witness_quarter=4)
@example(fra_month=11, witness_year=1960, witness_quarter=4)
@given(
    fra_month=st.integers(1, 12),
    witness_year=st.sampled_from([1959, 1960]),
    witness_quarter=st.integers(1, 4),
)
def test_independent_date_oracle_classifies_both_alternate_scan_directions(
    fra_month, witness_year, witness_quarter
):
    # The oracle uses calendar dates alone, not production FRA/quarter helpers.
    # The 19 recent QCs become 20 only in the supplied witness quarter.
    witness_start = date(witness_year, (witness_quarter - 1) * 3 + 1, 1)
    end = date(1960, fra_month, 1) - timedelta(days=1)
    index = end.year * 12 + end.month - 1 - 2
    covered = date(index // 12, index % 12 + 1, 1)
    excludes_alternate = (
        witness_start <= covered
        and witness_start < date(1960, fra_month, 1)
        and witness_start < date(1960, 10, 1)
    )
    person, years = _case(
        fra_month=fra_month,
        witness_year=witness_year,
        witness_quarter=witness_quarter,
    )
    rows = []
    try:
        rows.append(_row(person, years))
    except i.InvalidFamilyInput:
        assert excludes_alternate
        assert count_family_outcomes(rows).rows == 0
    else:
        if excludes_alternate:
            _assert_row(rows[0])
            assert rows[0].result.fully.insured
        else:
            _assert_row(
                rows[0], i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
            )
