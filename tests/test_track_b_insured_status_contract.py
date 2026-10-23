"""Statutory conformance: event timing and explicit refusal boundaries.

Invented declarations only; no population, behavioral, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import (
    InvalidFamilyInput,
    count_family_outcomes,
)
from tests.test_track_b_insured_status import declared, history


def test_future_exit_does_not_remove_dli_censoring():
    person = i.Person(date(1980, 1, 2))
    month = date(2026, 1, 1)
    years = history(person, month, {y: 4 for y in range(2015, 2025)})
    result = i.insured_status(person, years, month)
    future = i.insured_status(
        person, years, month, coverage_end_month=date(2027, 12, 1)
    )
    assert result == future
    assert future.dli.right_censored


def test_currently_insured_uses_death_quarter_after_death():
    person = i.Person(date(1980, 1, 2), death_date=date(2020, 12, 15))
    years = history(person, date(2020, 12, 1), {2019: 4, 2020: 4})
    at_death = i.insured_status(person, years, date(2020, 12, 1))
    later = i.insured_status(person, years, date(2026, 1, 1))
    assert at_death.currently == later.currently
    assert later.currently.insured
    assert later.currently.window[-1] == 2020 * 4 + 3


@pytest.mark.parametrize(
    "field", ["rib_entitlement_month", "dib_entitlement_month"]
)
def test_currently_insured_preserves_actual_entitlement_event(field):
    person = i.Person(date(1960, 1, 2), **{field: date(2020, 12, 1)})
    month = date(2026, 1, 1)
    years = history(person, month, {2019: 4, 2020: 4})
    actual = i.insured_status(person, years, month)
    hypothetical = i.insured_status(
        replace(person, **{field: None}), years, month
    )
    assert actual.currently.insured
    assert not hypothetical.currently.insured


def test_currently_insured_accepts_any_statutory_event():
    person = i.Person(
        date(1960, 1, 2),
        dib_entitlement_month=date(2000, 12, 1),
        rib_entitlement_month=date(2022, 12, 1),
        death_date=date(2025, 12, 10),
    )
    month = date(2026, 1, 1)
    years = history(person, month, {1999: 4, 2000: 4})
    result = i.insured_status(person, years, month)
    assert result.currently.insured
    assert result.currently.window[-1] == 2000 * 4 + 3

    # RS00301.110 excludes prior periods, not the period containing the
    # historical entitlement event itself. Its later end is known here.
    person = i.Person(
        date(1960, 2, 2),
        dib_entitlement_month=date(2000, 7, 1),
        prior_disability_periods=(
            i.DisabilityPeriod(date(2000, 1, 1), date(2005, 12, 31)),
        ),
    )
    month = date(2010, 1, 1)
    years = history(
        person, month, {1991: 4, 1992: 4, 1993: 4, 1994: 4, 1997: 4, 1998: 2}
    )
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert not result.currently.insured
    assert result.currently.qc_count_lower == 4


@pytest.mark.parametrize("condition", list(i.CoverageCondition))
def test_each_declared_specialist_condition_has_named_retained_refusal(
    condition,
):
    person = i.Person(date(1980, 2, 2), conditions=(condition,))
    month = date(2026, 1, 1)
    years = history(person, month)
    row = i.evaluate_insured_status(
        condition.value,
        Fraction(2),
        lambda: i.insured_status(person, years, month),
    )
    assert row.unsupported.reason is i.InsuredUnsupportedReason[condition.name]
    count = count_family_outcomes((row,))
    assert count.rows == count.unsupported_rows == 1
    assert count.unsupported_weight == 2
    del years[2000]
    with pytest.raises(InvalidFamilyInput):
        i.evaluate_insured_status(
            condition.value,
            Fraction(2),
            lambda: i.insured_status(person, years, month),
        )


def test_alien_sspa_requirement_has_explicit_trigger():
    month = date(2026, 1, 1)
    early = i.Person(
        date(1980, 2, 2),
        alien_worker=True,
        ssn_assignment_date=date(2003, 12, 31),
    )
    late = replace(early, ssn_assignment_date=date(2004, 1, 1))
    years = history(early, month)
    assert not i.insured_status(early, years, month).fully.insured
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(late, years, month)
    assert error.value.reason is i.InsuredUnsupportedReason.ALIEN_WORKER
    with pytest.raises(InvalidFamilyInput):
        replace(early, ssn_assignment_date=date(1979, 1, 1))


@pytest.mark.parametrize(
    "year,values,reason",
    [
        (
            1937,
            {"quarterly_wages": (50, 0, 0, 0)},
            i.InsuredUnsupportedReason.EARNINGS_1937,
        ),
        (
            1950,
            {"self_employment": 400},
            i.InsuredUnsupportedReason.PRE1951_SELF_EMPLOYMENT,
        ),
        (
            1954,
            {"agricultural_wages": 100},
            i.InsuredUnsupportedReason.PRE1955_AGRICULTURE,
        ),
        (2028, {"wages": 10000}, i.InsuredUnsupportedReason.QC_YEAR),
    ],
)
def test_raw_earnings_refusals_are_own_layer(year, values, reason):
    person = i.Person(date(1914, 2, 2))
    month = date(2028, 1, 1)
    years = history(person, month)
    years[year] = i.CoverageYear(i.EarningsProvenance.OBSERVED, **values)
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month)
    assert error.value.reason is reason


def test_input_calendar_errors_precede_totalization_refusal():
    person = i.Person(date(1950, 8, 2))
    month = date(1970, 12, 1)
    years = history(person, month)
    years[1950] = i.CoverageYear(
        i.EarningsProvenance.OBSERVED, qc_quarters=(True, False, False, False)
    )
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, month, totalization_credits=("UK",))
    years = history(person, month)
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            replace(person, disability_onset=date(1971, 1, 1)), years, month
        )
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            replace(person, rib_entitlement_month=date(1971, 1, 1)),
            years,
            month,
        )


@settings(max_examples=15, deadline=None)
@given(st.integers(1, 4), st.integers(0, 4))
def test_unknown_birth_and_exit_year_cap_is_sound(quarter, count):
    person = i.Person(date(2000, 2, 2))
    month = date(2026, quarter * 3, 1)
    years = history(person, month, {2024: 4, 2025: 4})
    years[2026] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    result = i.insured_status(
        person,
        years,
        month,
        test=i.InsuredTest.FULLY,
        coverage_end_month=month,
    )
    assert result.qcs_by_year[2026] == (0, quarter)
    years[2026] = declared(count)
    concrete = i.insured_status(
        person,
        years,
        month,
        test=i.InsuredTest.FULLY,
        coverage_end_month=month,
    )
    assert concrete.fully.insured == result.fully.insured
    assert (
        result.fully.qc_count_lower
        <= concrete.fully.qc_count_lower
        <= result.fully.qc_count_upper
    )


def test_dli_unknown_year_is_a_range_not_an_undocumented_point():
    person = i.Person(date(1980, 2, 2))
    month = date(2026, 12, 1)
    years = history(person, month, {y: 4 for y in range(2000, 2005)})
    years[2005] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert not result.disability.insured
    assert result.dli.lower == date(2009, 12, 31)
    assert result.dli.upper == date(2010, 12, 31)
    for count in range(5):
        concrete = dict(years)
        concrete[2005] = declared(count)
        value = i.insured_status(
            person, concrete, month, test=i.InsuredTest.DISABILITY
        )
        assert result.dli.lower <= value.dli.lower <= result.dli.upper


def test_pre1911_male_dib_fully_requirement_uses_1975_cap_cfr_404_132():
    person = i.Person(date(1900, 2, 2), sex=i.Sex.MALE)
    month = date(1974, 12, 1)
    years = history(person, month, {year: 4 for year in range(1969, 1974)})
    result = i.insured_status(person, years, month)
    assert result.fully.required == 14
    assert result.fully.insured
    assert result.disability.qc_count_lower == 20
    assert not result.disability.insured  # DIB fully test needs23, not14.


def test_requirement_helper_rejects_future_prior_period_and_onset():
    person = i.Person(date(1980, 2, 2))
    month = date(2020, 1, 1)
    for changed in (
        replace(person, disability_onset=date(2021, 1, 1)),
        replace(
            person,
            prior_disability_periods=(
                i.DisabilityPeriod(date(2020, 1, 1), date(2020, 12, 1)),
            ),
        ),
    ):
        with pytest.raises(InvalidFamilyInput):
            i.fully_insured_requirement(changed, month)


@settings(max_examples=10, deadline=None)
@given(st.lists(st.integers(0, 4), min_size=8, max_size=8))
def test_unknown_bounds_with_prior_disability_period(counts):
    person = i.Person(
        date(1980, 2, 2),
        prior_disability_periods=(
            i.DisabilityPeriod(
                date(2004, 4, 15), date(2006, 9, 15), special_insured=True
            ),
        ),
    )
    month = date(2012, 12, 1)
    years = history(
        person, month, dict(zip(range(2005, 2013), counts, strict=True))
    )
    years[2006] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    for kind in (
        i.InsuredTest.FULLY,
        i.InsuredTest.CURRENTLY,
        i.InsuredTest.DISABILITY,
    ):
        try:
            result = i.insured_status(person, years, month, test=kind)
        except i.InsuredConfigurationUnsupported as refusal:
            assert (
                refusal.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS
            )
            continue
        for count in range(5):
            concrete = dict(years)
            concrete[2006] = declared(count)
            value = i.insured_status(person, concrete, month, test=kind)
            assert (
                getattr(value, kind.value).insured
                == getattr(result, kind.value).insured
            )
            if result.dli is not None:
                lower = result.dli.lower or date.min
                upper = result.dli.upper or date.min
                assert lower <= (value.dli.lower or date.min) <= upper
