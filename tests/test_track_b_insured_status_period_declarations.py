"""Statutory conformance: administrative period facts and unknown histories.

Invented declarations only; no population, behavioral, or forecast claim.
"""

from dataclasses import replace
from datetime import date

import pytest

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
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

    # No established period can overcome the universal six-QC minimum.
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            person,
            history(person, month),
            month,
            test=i.InsuredTest.FULLY,
        )

    for foreign_credits, conditions in (
        (("invented-foreign-credit",), frozenset()),
        ((), frozenset({i.CoverageCondition.RAILROAD_CREDITS})),
    ):
        invalid_person = replace(person, conditions=conditions)
        with pytest.raises(InvalidFamilyInput):
            i.insured_status(
                invalid_person,
                history(invalid_person, month),
                month,
                test=i.InsuredTest.FULLY,
                totalization_credits=foreign_credits,
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


def test_established_current_period_refuses_unobserved_future_dli_only():
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
    years = history(person, month, {2021: 4, 2022: 2})
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(
            person,
            years,
            month,
            coverage_end_month=month,
            test=i.InsuredTest.DISABILITY,
        )
    assert error.value.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_DLI
    fully = i.insured_status(
        person,
        years,
        month,
        coverage_end_month=month,
        test=i.InsuredTest.FULLY,
    )
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
