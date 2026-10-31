"""Statutory conformance: both directions of period possibility.

Invented declarations only; no population, behavioral, or forecast claim.
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
from tests.test_track_b_insured_status import declared, history
from tests.test_track_b_insured_status_fix_round_4_routes import (
    _pre1956_case,
    _prior_overlap_unknown_earnings_case,
    _short_period_case,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN


def _fixed_end_case(*, previous=4, ending_month=1, query_month=4):
    ending = date(
        2022, ending_month, calendar.monthrange(2022, ending_month)[1]
    )
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=ending,
        current_disability_period_end_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2022, query_month, 1)
    years = history(person, month, {2021: previous})
    years[2022] = i.CoverageYear(UNKNOWN)
    return person, years, month


def _classification(person, years, month):
    rows = []
    try:
        rows.append(
            i.evaluate_insured_status(
                "possibility",
                Fraction(3, 2),
                lambda: i.insured_status(
                    person, years, month, test=i.InsuredTest.FULLY
                ),
            )
        )
    except i.InvalidFamilyInput:
        assert not rows
        return False
    denominator = count_family_outcomes(rows)
    assert denominator.rows == 1
    assert denominator.weight == Fraction(3, 2)
    return True


def test_impossible_fixed_end_raises_from_evaluator_without_a_row():
    person, years, month = _fixed_end_case()
    for count in range(5):
        concrete = dict(years)
        concrete[2022] = declared(count)
        assert not _classification(person, concrete, month)
    assert not _classification(person, years, month)


def test_six_qcs_by_fixed_end_preserve_valid_unknown_declaration():
    person, years, month = _fixed_end_case(ending_month=6, query_month=10)
    assert _assert_exact_classification(person, years, month) == [
        False,
        False,
        True,
        True,
        True,
    ]


@pytest.mark.parametrize("previous", [2, 3, 4])
@pytest.mark.parametrize("ending_month", [1, 2, 3])
def test_no_unknown_filling_can_start_before_fixed_first_quarter_end(
    previous, ending_month
):
    person, years, month = _fixed_end_case(
        previous=previous, ending_month=ending_month, query_month=10
    )
    assert not any(
        _classification(person, {**years, 2022: declared(count)}, month)
        for count in range(5)
    )
    assert not _classification(person, years, month)


def _concrete_histories(years, month):
    unknown = [
        year for year, row in years.items() if row.provenance is UNKNOWN
    ]
    options = []
    for year in unknown:
        if year < 1978:
            allowed = min(4, i._qid(month) - year * 4 + 1)
            options.append(
                [
                    i.CoverageYear(
                        OBSERVED,
                        qc_quarters=flags + (False,) * (4 - allowed),
                    )
                    for flags in product((False, True), repeat=allowed)
                ]
            )
        else:
            options.append([declared(count) for count in range(5)])
    for filling in product(*options):
        yield {**years, **dict(zip(unknown, filling, strict=True))}


def _assert_exact_classification(person, years, month):
    # Enumerate every filling, rather than stopping at the first witness.
    valid = [
        _classification(person, filling, month)
        for filling in _concrete_histories(years, month)
    ]
    assert _classification(person, years, month) == any(valid)
    return valid


@settings(max_examples=24, deadline=None)
@given(
    previous=st.integers(0, 4),
    ending_month=st.sampled_from([1, 3, 6, 12]),
    second_unknown=st.booleans(),
    blind=st.booleans(),
)
def test_unknown_declaration_exactly_matches_all_concrete_qc_fillings(
    previous, ending_month, second_unknown, blind
):
    """Both classifications match all five or25 annual-count fillings."""
    person, years, month = _fixed_end_case(
        previous=previous, ending_month=ending_month, query_month=10
    )
    person = replace(person, statutory_blindness=blind)
    if second_unknown:
        years[2020] = i.CoverageYear(UNKNOWN)
    _assert_exact_classification(person, years, month)


@settings(max_examples=6, deadline=None)
@given(
    missing_year=st.integers(1968, 1971),
    ending=st.sampled_from(
        [date(1972, 3, 31), date(1972, 12, 31), date(1973, 1, 31)]
    ),
    prior_ends_in_onset_quarter=st.booleans(),
)
def test_overlap_declaration_exactly_matches_every_quarter_filling(
    missing_year, ending, prior_ends_in_onset_quarter
):
    """A single filling must satisfy the fixed end and derived overlap."""
    person, years, month = _prior_overlap_unknown_earnings_case(
        missing_year=missing_year
    )
    prior = person.prior_disability_periods[0]
    if not prior_ends_in_onset_quarter:
        prior = replace(prior, end=date(1971, 12, 31))
    person = replace(
        person,
        prior_disability_periods=(prior,),
        current_disability_period_end=ending,
        current_disability_period_end_provenance=OBSERVED,
    )
    assert len(_assert_exact_classification(person, years, month)) == 16


def test_different_fillings_cannot_separately_satisfy_end_and_overlap():
    person, years, month = _prior_overlap_unknown_earnings_case()
    person = replace(
        person,
        current_disability_period_end=date(1972, 3, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    valid = _assert_exact_classification(person, years, month)
    assert valid == [False] * 16


def test_later_quarter_filling_can_clear_overlap_before_fixed_end():
    person, years, month = _prior_overlap_unknown_earnings_case()
    person = replace(
        person,
        current_disability_period_end=date(1972, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    valid = _assert_exact_classification(person, years, month)
    assert valid == [False] + [True] * 7 + [False] * 8


@pytest.mark.parametrize("condition", [None, *i.CoverageCondition])
def test_exact_classification_keeps_automatic_and_every_flagged_route(
    condition,
):
    person, years, month = _pre1956_case()
    if condition is not None:
        person = replace(person, conditions=(condition,))
    years[1953] = i.CoverageYear(UNKNOWN)
    # The captured alternate rule supplies a possible establishment for
    # every concrete quarter filling; each flagged route stays independent.
    assert _assert_exact_classification(person, years, month) == [True] * 16


@pytest.mark.parametrize("condition", list(i.CoverageCondition))
def test_exact_classification_keeps_each_independent_flagged_route(condition):
    if condition is i.CoverageCondition.RAILROAD_CREDITS:
        person = i.Person(
            date(1930, 2, 2),
            disability_onset=date(1952, 7, 15),
            prior_disability_periods_provenance=OBSERVED,
            current_disability_period_established=True,
            current_disability_period_provenance=OBSERVED,
            current_disability_period_end=date(1952, 8, 31),
            current_disability_period_end_provenance=OBSERVED,
            sspa211_applies=False,
            sspa211_provenance=OBSERVED,
            conditions=(condition,),
        )
        month = date(1968, 2, 1)
        years = history(person, month)
        # Ordinary wages are known; separately flagged RR compensation
        # is unresolved, so these are not final credited-QC declarations.
        years[1950] = i.CoverageYear(
            OBSERVED, quarterly_wages=(Fraction(0),) * 4
        )
        years[1953] = i.CoverageYear(UNKNOWN)
        expected_fillings = 16
    else:
        person, years, month = _fixed_end_case()
        person = replace(person, conditions=(condition,))
        expected_fillings = 5
    upper = {year: i._credits(year, row, True) for year, row in years.items()}
    assert not i._pre1956_alternate_possible(person, upper, month, None)
    assert (
        _assert_exact_classification(person, years, month)
        == [True] * expected_fillings
    )


def test_exact_classification_keeps_short_dib_entitled_prior_filling():
    person, years, month = _short_period_case()
    concrete = []
    for periods in (
        (),
        *(
            (i.DisabilityPeriod(date(2028, 10, 1), ending),)
            for ending in (
                date(2028, 10, 31),
                date(2028, 11, 30),
                date(2028, 12, 31),
            )
        ),
    ):
        filled = replace(
            person,
            prior_disability_periods_provenance=OBSERVED,
            prior_disability_periods=periods,
        )
        concrete.append(_classification(filled, years, month))
    assert concrete == [False, True, True, True]
    assert _classification(person, years, month) == any(concrete)


def test_large_unresolved_overlap_has_explicit_complexity_refusal():
    person, years, month = _prior_overlap_unknown_earnings_case()
    person = replace(
        person,
        current_disability_period_end=date(1972, 12, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    for year in range(1965, 1971):
        years[year] = i.CoverageYear(UNKNOWN)
    row = i.evaluate_insured_status(
        "large-overlap",
        Fraction(3, 2),
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        ),
    )
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
    )
    assert "overlap fillings" in row.unsupported.detail
    assert count_family_outcomes((row,)).rows == 1


@pytest.mark.parametrize("fact", ["end", "continuity"])
@pytest.mark.parametrize(
    "bound",
    [
        date(1952, 3, 31),
        date(1952, 6, 30),
        date(1952, 7, 31),
        date(1952, 9, 30),
    ],
)
def test_automatic_pre1956_start_obeys_fixed_end_and_continuity(fact, bound):
    person, years, month = _pre1956_case()
    values = {"disability_onset": date(1952, 1, 15)}
    if fact == "end":
        values.update(
            current_disability_period_end=bound,
            current_disability_period_end_provenance=OBSERVED,
        )
    else:
        values.update(
            current_disability_period_continues_through=bound,
            current_disability_period_continues_through_provenance=OBSERVED,
        )
    person = replace(person, **values)
    upper = {year: i._credits(year, row, True) for year, row in years.items()}
    assert not i._decision_witness(
        person, upper, bound, None, i.InsuredTest.DISABILITY
    )[0][0]
    possible = bound >= date(1952, 7, 1)
    assert _classification(person, years, month) is possible
    assert (
        i._pre1956_alternate_possible(person, upper, month, None) is possible
    )


@settings(max_examples=12, deadline=None)
@example(month=6, fact="end")
@example(month=6, fact="continuity")
@example(month=7, fact="end")
@example(month=7, fact="continuity")
@given(month=st.integers(1, 12), fact=st.sampled_from(["end", "continuity"]))
def test_automatic_pre1956_start_respects_immutable_bound_property(
    month, fact
):
    bound = date(1952, month, calendar.monthrange(1952, month)[1])
    test_automatic_pre1956_start_obeys_fixed_end_and_continuity(fact, bound)


@pytest.mark.parametrize("birth_month,possible", [(7, False), (8, True)])
def test_automatic_pre1956_start_must_precede_fra_month(birth_month, possible):
    person, years, month = _pre1956_case()
    person = replace(
        person,
        birth_date=date(1887, birth_month, 2),
        disability_onset=date(1952, 1, 15),
    )
    assert i._fra_date(person) == date(1952, birth_month, 1)
    assert _classification(person, years, month) is possible


@settings(max_examples=11, deadline=None)
@example(birth_month=7)
@example(birth_month=8)
@given(birth_month=st.integers(2, 12))
def test_automatic_pre1956_start_respects_fra_cap_property(birth_month):
    test_automatic_pre1956_start_must_precede_fra_month(
        birth_month, birth_month >= 8
    )
