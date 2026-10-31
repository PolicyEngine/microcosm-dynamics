"""Statutory conformance: input errors precede unrelated QC refusals.

Invented declarations only; no population, behavioral, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import declared, history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _prior_overlap_unknown_earnings_case,
)
from tests.test_track_b_insured_status_fix_round_5_possibility import (
    _classification,
    _fixed_end_case,
)

OBSERVED = i.EarningsProvenance.OBSERVED


def _evaluate(person, years, month, **kwargs):
    return i.evaluate_insured_status(
        "deferred-qc",
        Fraction(3, 2),
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY, **kwargs
        ),
    )


def _no_row(person, years, month, **kwargs):
    rows = []
    with pytest.raises(i.InvalidFamilyInput):
        rows.append(_evaluate(person, years, month, **kwargs))
    denominator = count_family_outcomes(rows)
    assert denominator.rows == denominator.unsupported_rows == 0
    assert denominator.weight == denominator.unsupported_weight == 0


@pytest.mark.parametrize("birth", [date(2000, 2, 2), date(1965, 2, 2)])
@pytest.mark.parametrize("wages", [0, 1, 10000])
@pytest.mark.parametrize("exit_declared", [False, True])
def test_unrelated_uncaptured_increment_cannot_hide_impossible_fixed_end(
    birth, wages, exit_declared
):
    person, _, _ = _fixed_end_case(previous=0)
    person = replace(person, birth_date=birth)
    month = date(2028, 1, 1)
    years = history(person, month)
    for count in range(5):
        _no_row(person, {**years, 2028: declared(count)}, month)
    years[2028] = i.CoverageYear(OBSERVED, wages=Fraction(wages))
    kwargs = {"coverage_end_month": month} if exit_declared else {}
    _no_row(person, years, month, **kwargs)


EARLY = (
    (2028, {"wages": Fraction(10000)}, i.InsuredUnsupportedReason.QC_YEAR),
    (
        1937,
        {"quarterly_wages": (Fraction(50),) * 4},
        i.InsuredUnsupportedReason.EARNINGS_1937,
    ),
    (
        1950,
        {"self_employment": Fraction(400)},
        i.InsuredUnsupportedReason.PRE1951_SELF_EMPLOYMENT,
    ),
    (
        1953,
        {"agricultural_wages": Fraction(400)},
        i.InsuredUnsupportedReason.PRE1955_AGRICULTURE,
    ),
)


def _early_case(year, *, relevant):
    if year == 2028:
        birth, onset, end, counts = (
            date(2000, 2, 2),
            date(2028, 1, 15),
            date(2028, 12, 31),
            {2026: 4, 2027: 1},
        )
    else:
        birth = date(1930, 2, 2)
        onset = date(1952, 7, 15) if year < 1952 else date(year + 1, 4, 15)
        end = date(onset.year, 12, 31)
        counts = {1951 if year < 1952 else year + 1: 2}
    if not relevant:
        # No credits precede this early bound. The historical ending has
        # the required two-month onset gap; later facts cannot repair it.
        onset, end, counts = birth, date(birth.year, 4, 30), {}
    person = i.Person(
        birth,
        disability_onset=onset,
        statutory_blindness=True,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=end,
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2028, 12, 1) if year == 2028 else date(1973, 1, 1)
    return person, history(person, month, counts), month


@pytest.mark.parametrize("year,values,reason", EARLY)
def test_every_early_qc_refusal_preserves_possible_declaration(
    year, values, reason
):
    person, years, month = _early_case(year, relevant=True)
    if year < 1978:
        concrete = [
            {**years, year: i.CoverageYear(OBSERVED, qc_quarters=flags)}
            for flags in product((False, True), repeat=4)
        ]
    else:
        concrete = [{**years, year: declared(n)} for n in range(5)]
    fillings = [_classification(person, filled, month) for filled in concrete]
    assert any(fillings)
    assert not all(fillings)
    row = _evaluate(
        person, {**years, year: i.CoverageYear(OBSERVED, **values)}, month
    )
    assert row.unsupported.reason is reason
    assert count_family_outcomes((row,)).unsupported_weight == Fraction(3, 2)
    # Deferred conversion keeps the original reason and explanatory note.
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i._credits(year, i.CoverageYear(OBSERVED, **values), False)
    assert row.unsupported.detail == error.value.detail


@settings(max_examples=12, deadline=None)
@given(index=st.integers(0, len(EARLY) - 1), reverse=st.booleans())
def test_irrelevant_early_refusal_fact_preserves_all_invalid_grid_case(
    index, reverse
):
    year, values, _ = EARLY[index]
    if year == 2028:
        person, _, _ = _fixed_end_case(previous=0)
        month = date(2028, 12, 1)
        years = history(person, month, {2021: 4})
    else:
        person, years, month = _early_case(year, relevant=False)
    # Start with an all-invalid exactness-grid declaration, then add the
    # coverage fact. Every concrete filling still produces no row.
    assert not _classification(person, years, month)
    years[year] = i.CoverageYear(OBSERVED, **values)
    if reverse:
        years = dict(reversed(tuple(years.items())))
    _no_row(person, years, month)
    test_every_early_qc_refusal_preserves_possible_declaration(
        year, values, EARLY[index][2]
    )


@pytest.mark.parametrize("wages", [0, 1, 3939, 3940, 10000])
def test_uncaptured_increment_bounds_preserve_both_classifications(wages):
    person, _, _ = _fixed_end_case(previous=0)
    person = replace(
        person,
        statutory_blindness=True,
        disability_onset=date(2028, 1, 15),
        current_disability_period_end=date(2028, 6, 30),
    )
    month = date(2028, 12, 1)
    years = history(person, month, {2027: 4})
    years[2028] = i.CoverageYear(OBSERVED, wages=Fraction(wages))
    if wages < 3940:
        _no_row(person, years, month)
    else:
        row = _evaluate(person, years, month)
        assert row.unsupported.reason is i.InsuredUnsupportedReason.QC_YEAR


@pytest.mark.parametrize("reverse", [False, True])
def test_deferred_refusals_keep_original_sorted_year_priority(reverse):
    person, years, month = _early_case(1950, relevant=True)
    years[1937] = i.CoverageYear(OBSERVED, quarterly_wages=(Fraction(50),) * 4)
    years[1950] = i.CoverageYear(OBSERVED, self_employment=Fraction(400))
    if reverse:
        years = dict(reversed(tuple(years.items())))
    row = _evaluate(person, years, month)
    assert row.unsupported.reason is i.InsuredUnsupportedReason.EARNINGS_1937
    assert row.unsupported.detail == "1937_earnings_allocation_unsupported"


def test_unresolved_overlap_keeps_original_deferred_refusal():
    person, years, month = _prior_overlap_unknown_earnings_case()
    person = replace(
        person,
        current_disability_period_end=date(1972, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    for year in range(1965, 1971):
        years[year] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    years[1937] = i.CoverageYear(OBSERVED, quarterly_wages=(Fraction(50),) * 4)
    row = _evaluate(person, years, month)
    assert row.unsupported.reason is i.InsuredUnsupportedReason.EARNINGS_1937
    assert row.unsupported.detail == "1937_earnings_allocation_unsupported"


@settings(max_examples=4, deadline=None)
@given(fixed_first=st.booleans(), reverse=st.booleans())
def test_deferred_quarter_fillings_keep_fixed_minimum_and_valid_middle(
    fixed_first, reverse
):
    person = i.Person(
        date(1920, 2, 2),
        disability_onset=date(1954, 2, 15),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1952, 7, 15), date(1954, 1, 31)),
        ),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=date(1954, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 1, 1)
    years = history(
        person,
        month,
        {
            1938: 1,
            1946: 4,
            1947: 4,
            1948: 4,
            1949: 1,
            1951: 4,
            1952: 2,
        },
    )
    # The supplied prior has the captured alternate's 20 total QCs and
    # all six continuous 1951 Q1--1952 Q2 credits. For the current onset,
    # Removing prior-period gaps opens the alternate for 0000 too. All
    # eight Q1-uncredited fillings remain possible; credited Q1 overlaps.
    flags = [
        flags
        for flags in product((False, True), repeat=4)
        if not fixed_first or flags[0]
    ]
    valid = [
        _classification(
            person,
            {**years, 1954: i.CoverageYear(OBSERVED, qc_quarters=f)},
            month,
        )
        for f in flags
    ]
    assert valid == ([False] * 8 if fixed_first else [True] * 8 + [False] * 8)
    years[1954] = i.CoverageYear(
        OBSERVED,
        agricultural_wages=Fraction(100),
        quarterly_wages=(Fraction(50) if fixed_first else Fraction(0),)
        + (Fraction(0),) * 3,
    )
    if reverse:
        years = dict(reversed(tuple(years.items())))
    if any(valid):
        row = _evaluate(person, years, month)
        assert (
            row.unsupported.reason
            is i.InsuredUnsupportedReason.PRE1955_AGRICULTURE
        )
        assert count_family_outcomes((row,)).weight == Fraction(3, 2)
    else:
        _no_row(person, years, month)


@pytest.mark.parametrize("year,values,reason", EARLY)
def test_schema_validation_precedes_deferred_qc_refusals(year, values, reason):
    person, years, month = _early_case(year, relevant=True)
    years[year] = i.CoverageYear(OBSERVED, **values)
    years.pop(max(years))
    with pytest.raises(i.InvalidFamilyInput, match="Every coverage year"):
        _evaluate(person, years, month)
