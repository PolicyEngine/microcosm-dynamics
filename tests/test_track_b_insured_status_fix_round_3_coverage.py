"""Statutory conformance: observable specialist coverage boundaries.

Invented records and captured RS 00301.315 figures only. No population,
behavioral, payment, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from tests.test_track_b_insured_status import declared, history
from tests.test_track_b_insured_status_sources import source_text

PROPERTY = settings(max_examples=30, deadline=None)


def _person(birth=date(1896, 2, 2), **values):
    declarations = {
        "sex": i.Sex.FEMALE,
        "prior_disability_periods_provenance": i.EarningsProvenance.OBSERVED,
        "current_disability_period_established": False,
        "current_disability_period_provenance": i.EarningsProvenance.OBSERVED,
        "sspa211_applies": False,
        "sspa211_provenance": i.EarningsProvenance.OBSERVED,
    }
    declarations.update(values)
    return i.Person(birth, **declarations)


def _wages(amount):
    return i.CoverageYear(
        i.EarningsProvenance.OBSERVED,
        quarterly_wages=(
            Fraction(amount),
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ),
    )


def _refusal(person, years, month, *, test=i.InsuredTest.FULLY):
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=test)
    return error.value.reason


def test_raw_pre1951_wages_automatically_refuse_simplified_alternative():
    """Executed reviewer case: ordinary one QC versus seven deemed QCs."""
    month = date(1968, 2, 1)
    person = _person(rib_entitlement_month=month)
    years = history(person, month)
    years[1940] = _wages(2800)
    assert person.conditions == frozenset()
    assert i.fully_insured_requirement(person, month) == 7
    assert Fraction(2800) // 400 == 7
    assert (
        _refusal(person, years, month)
        is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
    )


def test_unknown_pre1951_wages_can_qualify_when_four_ordinary_qcs_cannot():
    month = date(1968, 2, 1)
    person = _person()
    years = history(person, month)
    years[1940] = declared(provenance=i.EarningsProvenance.UNKNOWN, year=1940)
    assert (
        _refusal(person, years, month)
        is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
    )


@pytest.mark.parametrize("amount,refuses", [(5700, True), (5500, False)])
def test_poms315_john_doe_aggregate_boundary_without_specialist_flag(
    amount, refuses
):
    """RS .315 C.1: 23+14=37; 23+13=36 invokes ordinary-credit fallback."""
    person = _person(date(1926, 9, 8))
    month = date(1991, 9, 1)
    years = history(
        person, month, {**{year: 4 for year in range(1980, 1985)}, 1985: 3}
    )
    for year in (1948, 1949):
        years[year] = _wages(1900)
    years[1950] = _wages(amount - 3800)
    assert i.fully_insured_requirement(person, month) == 37
    assert amount // 400 == (14 if refuses else 13)
    if refuses:
        assert (
            _refusal(person, years, month)
            is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
        )
    else:
        result = i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        )
        assert not result.fully.insured
        assert result.fully.qc_count_lower == 26


@PROPERTY
@given(st.integers(min_value=0, max_value=299999))
def test_pre1951_refusal_tracks_exact_400_dollar_status_boundary(cents):
    person = _person()
    month = date(1968, 2, 1)
    years = history(person, month)
    years[1940] = _wages(Fraction(cents, 100))
    if cents >= 280000:
        assert (
            _refusal(person, years, month)
            is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
        )
    else:
        result = i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        )
        assert not result.fully.insured
        assert result.fully.qc_count_lower == int(cents >= 5000)


@PROPERTY
@given(st.integers(min_value=2800, max_value=2999), st.integers(0, 1))
def test_pre1951_refusal_is_independent_of_mapping_order_and_provenance(
    wages, convention
):
    person = _person()
    month = date(1968, 2, 1)
    years = history(person, month)
    row = _wages(wages)
    if convention:
        row = replace(
            row,
            provenance=i.EarningsProvenance.CONVENTION_FILLED,
            convention_id="invented-wages",
        )
    years[1940] = row
    forward = _refusal(person, years, month)
    reverse = _refusal(person, dict(reversed(tuple(years.items()))), month)
    assert forward is reverse is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951


def test_pre1951_alternative_does_not_change_already_fully_insured_status():
    person = _person()
    month = date(1968, 2, 1)
    years = history(person, month, {1960: 4, 1961: 3})
    years[1940] = _wages(2800)
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.fully.qc_count_lower == 8


@pytest.mark.parametrize(
    "test", [i.InsuredTest.CURRENTLY, i.InsuredTest.DISABILITY]
)
def test_simplified_pre1951_credits_do_not_apply_to_other_requested_tests(
    test,
):
    person = _person()
    month = date(1968, 2, 1)
    years = history(person, month)
    years[1940] = _wages(2800)
    result = i.insured_status(person, years, month, test=test)
    assert not getattr(result, test.value).insured


@pytest.mark.parametrize("month", [date(1968, 2, 1), date(1992, 6, 1)])
def test_potential_simplified_method_refuses_unresolved_seven_ey_applicability(
    month,
):
    person = _person(date(1895, 2, 2))
    years = history(person, month)
    years[1940] = _wages(2400)
    assert i.fully_insured_requirement(person, month) == 6
    assert (
        _refusal(person, years, month)
        is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
    )


def test_raw_pre1951_refusal_follows_complete_input_validation():
    person = _person()
    month = date(1968, 2, 1)
    years = history(person, month)
    years[1940] = _wages(2800)
    del years[1951]
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)


def test_pre1956_alternate_disability_path_is_detected_from_onset_and_qcs():
    person = _person(date(1900, 2, 2), disability_onset=date(1952, 7, 15))
    month = date(1968, 2, 1)
    years = history(
        person, month, {1938: 4, 1939: 4, 1940: 4, 1941: 2, 1951: 4, 1952: 2}
    )
    assert (
        _refusal(person, years, month, test=i.InsuredTest.DISABILITY)
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )


def test_pre1956_onset_without_twenty_possible_qcs_needs_no_special_refusal():
    person = _person(date(1900, 2, 2), disability_onset=date(1952, 7, 15))
    month = date(1968, 2, 1)
    years = history(person, month, {1951: 4, 1952: 2})
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert not result.disability.insured


@PROPERTY
@given(st.integers(0, 16), st.lists(st.booleans(), min_size=6, max_size=6))
@example(14, [True] * 6)
@example(13, [True] * 6)
@example(16, [True, True, False, True, True, True])
def test_pre1956_refusal_requires_twenty_qcs_and_the_continuous_window(
    earlier, continuous
):
    person = _person(date(1900, 2, 2), disability_onset=date(1952, 7, 15))
    month = date(1968, 2, 1)
    counts = {
        year: min(4, max(0, earlier - 4 * n))
        for n, year in enumerate(range(1938, 1942))
    }
    years = history(person, month, counts)
    for year, flags in (
        (1951, continuous[:4]),
        (1952, continuous[4:] + [False, False]),
    ):
        years[year] = i.CoverageYear(
            i.EarningsProvenance.OBSERVED, qc_quarters=tuple(flags)
        )
    if earlier >= 14 and all(continuous):
        assert (
            _refusal(person, years, month, test=i.InsuredTest.DISABILITY)
            is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
        )
    else:
        result = i.insured_status(
            person, years, month, test=i.InsuredTest.DISABILITY
        )
        assert not result.disability.insured


def test_observable_specialist_rules_and_worked_figures_are_in_captures():
    statute = source_text("lii_usc_42_413")
    assert (
        "an individual shall be deemed to have one quarter of coverage "
        "for each $400 of his total wages prior to 1951"
    ) in statute
    regulation = source_text("ecfr_20cfr404_subpart_b")
    assert "if you have at least 7 elapsed years" in regulation
    assert "If you file an application in June 1992 or later" in regulation
    simplified = source_text("poms_rs_00301_315")
    for quote in (
        "Under the 1967 Amendments, use the simplified method if:",
        "there are at least seven EYs; and",
        "The 1990 Amendments eliminated the seven EY test.",
        "The simplified method does not apply to disability claims.",
        "applications effectively filed 06/1992 or later.",
        "$5,700 divided by $400 = 14",
        "$5,500",
        "13 QCs",
        "23 QCs after 1950",
        "37 QCs",
    ):
        assert quote in simplified
    alternate = source_text("poms_rs_00301_480")
    for quote in (
        "the wage earner had at least 20 quarters of coverage (QC) by the end of that quarter;",
        "all quarters beginning with 03/51 up to (but not including) that quarter are QCs and there are at least six such QCs.",
        "the last day on which it can begin is 12/31/55.",
    ):
        assert quote in alternate


def _simplified_with_freeze(ending_year=1960, cents=920000, *, current=False):
    period = i.DisabilityPeriod(
        date(1945, 1, 1), date(ending_year, 12, 31), special_insured=True
    )
    declarations = {"prior_disability_periods": (period,)}
    if current:
        declarations = {
            "disability_onset": period.start,
            "current_disability_period_established": True,
            "current_disability_period_end": period.end,
            "current_disability_period_end_provenance": (
                i.EarningsProvenance.OBSERVED
            ),
        }
    person = _person(date(1920, 2, 2), **declarations)
    month = date(1990, 2, 1)
    years = history(person, month)
    # These eight quarters establish a valid under31 period in 1945Q1.
    for year, amounts in {
        1941: (0, 50, 50, 50),
        1942: (50, 50, 50, 50),
        1943: (50, 0, 0, 0),
    }.items():
        years[year] = i.CoverageYear(
            i.EarningsProvenance.OBSERVED,
            quarterly_wages=tuple(map(Fraction, amounts)),
        )
    # Equal fractions preserve twelve ordinary QCs and the exact aggregate.
    amount = (Fraction(cents, 100) - 400) / 12
    for year in (1946, 1947, 1948):
        years[year] = i.CoverageYear(
            i.EarningsProvenance.OBSERVED,
            quarterly_wages=(amount,) * 4,
        )
    return person, years, month


@pytest.mark.parametrize("current", [False, True])
def test_pre1951_refusal_considers_lower_frozen_fully_requirement(current):
    person, years, month = _simplified_with_freeze(current=current)
    credits = {
        year: i._credits(year, row, False) for year, row in years.items()
    }
    plain = replace(
        person,
        prior_disability_periods=(),
        current_disability_period_established=False,
        current_disability_period_end=None,
        current_disability_period_end_provenance=i.EarningsProvenance.UNKNOWN,
    )
    prior = i._witness(
        plain, credits, date(1945, 1, 1), None, i.InsuredTest.DISABILITY
    )
    assert prior[0] and prior[1:3] == (8, 8)
    assert prior[5] == "under31_special"
    ordinary = i._witness(plain, credits, month, None, i.InsuredTest.FULLY)
    assert not ordinary[0] and ordinary[1:3] == (20, 31)
    frozen_required = i._requirement(
        person, month, ((date(1945, 1, 1), date(1960, 12, 31)),)
    )
    assert frozen_required == 21
    assert Fraction(9200) // 400 == 23
    assert (
        _refusal(person, years, month)
        is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
    )


@PROPERTY
@given(st.integers(1953, 1962), st.integers(100000, 1239999))
@example(1960, 839999)
@example(1960, 840000)
def test_pre1951_refusal_bounds_every_known_freeze_requirement(
    ending_year, cents
):
    person, years, month = _simplified_with_freeze(ending_year, cents)
    required = max(6, 31 - (ending_year - 1950))
    assert i.fully_insured_requirement(person, month) == required
    if cents // 40000 >= required:
        assert (
            _refusal(person, years, month)
            is i.InsuredUnsupportedReason.SIMPLIFIED_PRE1951
        )
    else:
        result = i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY
        )
        assert not result.fully.insured
