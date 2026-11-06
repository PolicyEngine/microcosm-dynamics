"""Statutory conformance: administrative period facts and unknown histories.

Invented declarations only; no population, behavioral, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import (
    InvalidFamilyInput,
    count_family_outcomes,
)
from tests.test_track_b_insured_status import history


def test_established_current_period_with_unknown_prior_periods_uses_bounds():
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        current_disability_period_established=True,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    month = date(2022, 4, 1)
    years = history(person, month, {2021: 4, 2022: 2})
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.current_disability_period_start is None
    assert result.unknown_facts == (
        "prior_disability_periods",
        "current_disability_period_start",
        "current_disability_period_end",
    )
    assert result.decided_despite_unknowns
    disability = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert disability.disability.insured
    assert disability.current_disability_period_start is None
    assert disability.unknown_facts == result.unknown_facts
    assert disability.decided_despite_unknowns
    assert disability.dli.lower == disability.dli.upper == date(2022, 6, 30)
    assert disability.dli.right_censored

    concrete_person = replace(
        person,
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
    )
    concrete = i.insured_status(concrete_person, years, month)
    assert concrete.fully.insured == result.fully.insured
    assert concrete.disability.insured == disability.disability.insured
    assert concrete.current_disability_period_start == date(2022, 4, 1)
    assert disability.dli.lower <= concrete.dli.lower <= disability.dli.upper

    # Without foreign credits, these ordinary declarations lack six QCs.
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            person,
            history(person, month),
            month,
            test=i.InsuredTest.FULLY,
        )

    foreign_row = i.evaluate_insured_status(
        "unknown-prior-foreign-credits",
        Fraction(11, 5),
        lambda: i.insured_status(
            person,
            history(person, month),
            month,
            test=i.InsuredTest.FULLY,
            totalization_credits=("invented-foreign-credit",),
        ),
    )
    assert foreign_row.result is None
    assert (
        foreign_row.unsupported.reason
        is i.InsuredUnsupportedReason.TOTALIZATION
    )
    denominator = count_family_outcomes((foreign_row,))
    assert denominator.rows == denominator.unsupported_rows == 1
    assert (
        denominator.weight == denominator.unsupported_weight == Fraction(11, 5)
    )

    railroad_person = replace(
        person, conditions=(i.CoverageCondition.RAILROAD_CREDITS,)
    )
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            railroad_person,
            history(railroad_person, month),
            month,
            test=i.InsuredTest.FULLY,
        )


def test_unknown_earnings_deciding_established_current_start_refuse_by_name():
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    month = date(2022, 4, 1)
    years = history(person, month, {2022: 2})
    years[2021] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS


def test_requirement_calendar_error_precedes_unknown_period_refusal():
    person = i.Person(
        date(2000, 2, 2),
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        current_disability_period_established=False,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    with pytest.raises(InvalidFamilyInput):
        i.fully_insured_requirement(person, date(1999, 1, 1))


def test_unknown_period_dli_capped_before_query_is_not_right_censored():
    person = i.Person(
        date(1950, 2, 2),
        prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        current_disability_period_established=False,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    month = date(2026, 1, 1)
    counts = {year: 4 for year in (*range(2000, 2010), *range(2017, 2027))}
    years = history(person, month, counts)
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert result.disability.insured
    assert result.dli.upper < month
    assert not result.dli.right_censored


def test_established_current_period_ranges_an_unobserved_future_dli():
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    month = date(2022, 10, 1)

    def result(annual, test):
        return i.insured_status(
            person,
            history(person, month, annual),
            month,
            coverage_end_month=month,
            test=test,
        )

    # Six QCs fill the 12 quarters ending 2022Q2, so the period begins there.
    # With the period set aside (404.130(f)), the 15 elapsed quarters through
    # 2024Q4 hold seven QCs and the next quarter needs eight, so no ending's
    # date falls below 2024Q4. An ending at retirement age holds it at 2066Q4.
    ranged = result({2021: 4, 2022: 4}, i.InsuredTest.DISABILITY)
    assert ranged.current_disability_period_start == date(2022, 4, 1)
    assert ranged.disability.insured
    assert (
        ranged.dli.lower,
        ranged.dli.upper,
        ranged.dli.right_censored,
    ) == (date(2024, 12, 31), date(2066, 12, 31), False)
    # 2022's two QCs can sit later, where they move the start and the date, so
    # no filling with the reported start reaches every ending's date.
    annual = {2021: 4, 2022: 2}
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        result(annual, i.InsuredTest.DISABILITY)
    assert (
        error.value.reason is i.InsuredUnsupportedReason.ASSIGNMENT_COMPLEXITY
    )
    fully = result(annual, i.InsuredTest.FULLY)
    assert fully.fully.insured
    assert fully.dli is None


def test_requirement_current_period_establishment_requires_coverage_history():
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=i.EarningsProvenance.OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=i.EarningsProvenance.OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=i.EarningsProvenance.OBSERVED,
    )
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.fully_insured_requirement(person, date(2022, 10, 1))
    assert (
        error.value.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_HISTORY
    )
