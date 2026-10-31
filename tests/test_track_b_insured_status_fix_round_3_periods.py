"""Statutory conformance: ongoing period endpoints and retirement limits.

Invented cases and captured statutory rules only; no population, behavioral,
or forecast claim.
"""

from dataclasses import replace
from datetime import date

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED


def _person(birth=date(2000, 2, 2), **facts):
    return i.Person(
        birth,
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        **facts,
    )


def _endpoint_case():
    person = _person(
        disability_onset=date(2022, 1, 15),
        statutory_blindness=True,
        dib_entitlement_month=date(2026, 1, 1),
    )
    month = date(2026, 3, 1)
    years = history(person, month, {2017: 1, 2020: 4, 2021: 1, 2026: 1})
    return person, years, month


def test_ongoing_period_end_cannot_invent_a_credited_query_endpoint():
    person, years, month = _endpoint_case()
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.CURRENTLY)
    assert error.value.reason.value == (
        "ongoing_disability_period_end_decides_status"
    )
    later = i.insured_status(
        person, years, date(2026, 4, 1), test=i.InsuredTest.CURRENTLY
    )
    assert not later.currently.insured
    assert later.currently.qc_count_lower == 5
    assert later.currently.window == tuple(range(2018 * 4 + 3, 2022 * 4))


def _fra_person(onset=date(2026, 1, 15), blind=False):
    return _person(
        date(1960, 1, 2),
        disability_onset=onset,
        statutory_blindness=blind,
        rib_entitlement_month=date(2028, 10, 1),
    )


def test_current_period_ends_before_fra_even_when_medical_disability_continues():
    person = _fra_person()
    month = date(2028, 10, 1)
    years = history(person, month, {y: 4 for y in range(2016, 2026)})
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert not result.currently.insured
    assert result.currently.qc_count_lower == 5


def test_known_established_period_cannot_begin_at_or_after_fra():
    with pytest.raises(InvalidFamilyInput):
        person = _fra_person(date(2028, 1, 15), True)
        month = date(2028, 10, 1)
        years = history(person, month, {y: 4 for y in range(2016, 2026)})
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)


def test_post_fra_establishment_is_invalid_before_unknown_period_refusal():
    with pytest.raises(InvalidFamilyInput):
        person = replace(
            _fra_person(date(2028, 1, 15), True),
            prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        )
        i.fully_insured_requirement(person, date(2028, 10, 1))


def test_declared_period_end_resolves_the_query_quarter_ambiguity():
    person, years, month = _endpoint_case()
    ended = replace(
        person,
        current_disability_period_end=date(2026, 3, 31),
        current_disability_period_end_provenance=OBSERVED,
    )
    continuing = replace(
        ended, current_disability_period_end=date(2026, 6, 30)
    )
    first = i.insured_status(ended, years, month, test=i.InsuredTest.CURRENTLY)
    second = i.insured_status(
        continuing, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert first.currently.insured
    assert first.currently.qc_count_lower == 6
    assert not second.currently.insured
    assert second.currently.qc_count_lower == 5
    assert first.unknown_facts == second.unknown_facts == ()
    conventional = replace(
        continuing,
        current_disability_period_end_provenance=(
            i.EarningsProvenance.CONVENTION_FILLED
        ),
        current_disability_period_end_convention_id="invented-end-convention",
    )
    value = i.insured_status(
        conventional, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert value.currently == second.currently
    assert value.convention_facts["current_disability_period_end"] == (
        "invented-end-convention"
    )


@pytest.mark.parametrize(
    "facts",
    [
        {"current_disability_period_end": date(2026, 3, 31)},
        {"current_disability_period_end_provenance": OBSERVED},
        {
            "current_disability_period_end": date(2026, 3, 1),
            "current_disability_period_end_provenance": OBSERVED,
        },
        {
            "current_disability_period_end": date(2021, 12, 31),
            "current_disability_period_end_provenance": OBSERVED,
        },
    ],
)
def test_current_period_end_requires_consistent_month_end_and_provenance(
    facts,
):
    person, _, _ = _endpoint_case()
    with pytest.raises(InvalidFamilyInput):
        replace(person, **facts)


def _act_fra(birth):
    """Independent 416(l)(1)-(3) calculation from attainment of age62."""
    import calendar
    from datetime import timedelta

    early = date(birth.year + 62, birth.month, birth.day) - timedelta(days=1)
    if early.year < 2000:
        months = 65 * 12
    elif early.year < 2005:
        months = 65 * 12 + 2 * (early.year - 1999)
    elif early.year < 2017:
        months = 66 * 12
    elif early.year < 2022:
        months = 66 * 12 + 2 * (early.year - 2016)
    else:
        months = 67 * 12
    year, month = divmod(birth.year * 12 + birth.month - 1 + months, 12)
    day = min(birth.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day) - timedelta(days=1)


@pytest.mark.parametrize("early_year", range(1999, 2023))
@pytest.mark.parametrize("day", [1, 2])
def test_fra_stepup_cohorts_and_first_second_birthdays_follow_416_l(
    early_year, day
):
    birth = date(early_year - 62, 1, day)
    person = _person(birth, disability_onset=date(1990, 1, 15))
    assert i._fra_date(person) == _act_fra(birth)
    expected = _act_fra(birth)
    assert (
        i._fra_quarter(person) == expected.year * 4 + (expected.month - 1) // 3
    )


@settings(max_examples=35, deadline=None)
@given(
    year=st.integers(1914, 1970),
    month=st.integers(1, 12),
    day=st.sampled_from([1, 2]),
)
def test_fra_date_and_quarter_match_independent_act_calendar(year, month, day):
    birth = date(year, month, day)
    person = _person(birth, disability_onset=date(year + 30, 1, 15))
    expected = _act_fra(birth)
    assert i._fra_date(person) == expected
    assert (
        i._fra_quarter(person) == expected.year * 4 + (expected.month - 1) // 3
    )


def test_prior_period_is_capped_at_fra_for_status_and_requirement_helper():
    birth = date(1960, 1, 2)
    common = dict(
        birth_date=birth,
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=False,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        rib_entitlement_month=date(2028, 10, 1),
    )
    overlong = i.Person(
        **common,
        prior_disability_periods=(
            i.DisabilityPeriod(date(2026, 1, 15), date(2028, 9, 30)),
        ),
    )
    assert overlong.prior_disability_periods[0].end == date(2026, 12, 31)
    month = date(2028, 10, 1)
    years = history(overlong, month, {y: 4 for y in range(2016, 2026)})
    result = i.insured_status(
        overlong, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert not result.currently.insured
    assert result.currently.qc_count_lower == 5
    assert i.fully_insured_requirement(overlong, month) == 40


@settings(max_examples=12, deadline=None)
@given(
    counts=st.tuples(st.integers(0, 4), st.integers(0, 4)),
    current=st.integers(0, 4),
    kind=st.sampled_from([i.InsuredTest.FULLY, i.InsuredTest.CURRENTLY]),
)
def test_ongoing_period_completion_status_and_count_bounds_are_sound(
    counts, current, kind
):
    person, _, month = _endpoint_case()
    years = history(
        person,
        month,
        {2016: 4, 2017: 4, 2020: counts[0], 2021: counts[1], 2026: current},
    )
    concrete = []
    for ending in [date(2026, 3, 31), date(2026, 6, 30), date(2027, 12, 31)]:
        value = i.insured_status(
            replace(
                person,
                current_disability_period_end=ending,
                current_disability_period_end_provenance=OBSERVED,
            ),
            years,
            month,
            test=kind,
        )
        concrete.append(getattr(value, kind.value))
    try:
        result = i.insured_status(person, years, month, test=kind)
    except i.InsuredConfigurationUnsupported as refusal:
        assert refusal.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_END
        assert len({value.insured for value in concrete}) == 2
        return
    decision = getattr(result, kind.value)
    for value in concrete:
        assert value.insured == decision.insured
        assert (
            decision.qc_count_lower
            <= value.qc_count_lower
            <= decision.qc_count_upper
        )
        assert (
            decision.fully_qc_count_lower
            <= value.fully_qc_count_lower
            <= decision.fully_qc_count_upper
        )
    assert "current_disability_period_end" in result.unknown_facts


@settings(max_examples=15, deadline=None)
@given(
    birth_year=st.integers(1938, 1960),
    birth_month=st.integers(1, 12),
    birth_day=st.sampled_from([1, 2]),
    extra_years=st.integers(1, 5),
)
def test_every_supplied_prior_period_has_the_statutory_fra_cap(
    birth_year, birth_month, birth_day, extra_years
):
    from datetime import timedelta

    birth = date(birth_year, birth_month, birth_day)
    fra = _act_fra(birth)
    cap = fra.replace(day=1) - timedelta(days=1)
    person = i.Person(
        birth,
        prior_disability_periods=(
            i.DisabilityPeriod(
                cap.replace(year=cap.year - 2, day=1),
                cap.replace(year=cap.year + extra_years, day=1),
            ),
        ),
        prior_disability_periods_provenance=OBSERVED,
    )
    assert person.prior_disability_periods[0].end == cap
    with pytest.raises(InvalidFamilyInput):
        replace(
            person,
            prior_disability_periods=(i.DisabilityPeriod(fra, fra),),
        )


def test_unknown_current_period_after_fra_cannot_create_freeze_uncertainty():
    person = i.Person(
        date(1960, 1, 2),
        disability_onset=date(2028, 1, 15),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=None,
        current_disability_period_provenance=i.EarningsProvenance.UNKNOWN,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2028, 10, 1)
    assert i.fully_insured_requirement(person, month) == 40
    years = history(person, month, {y: 4 for y in range(2016, 2026)})
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.unknown_facts == ()
    assert result.current_disability_period_start is None


@pytest.mark.parametrize("unknown", [False, True])
def test_later_insurance_after_fra_cannot_establish_period_before_refusal(
    unknown,
):
    person = replace(
        _fra_person(),
        conditions=frozenset({i.CoverageCondition.RAILROAD_CREDITS}),
    )
    month = date(2028, 10, 1)
    years = history(person, month, {2027: 4, 2028: 4})
    if unknown:
        years[2028] = i.CoverageYear(i.EarningsProvenance.UNKNOWN)
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)


def test_period_calendar_rules_are_quoted_from_captured_authority():
    import xml.etree.ElementTree as ET
    from pathlib import Path

    sources = Path(__file__).parent / "data/track_b/insured_status_sources"
    act = (sources / "lii_usc_42_416_excerpts.txt").read_text()
    cfr = "".join(
        ET.fromstring(
            (sources / "ecfr_20cfr404_321.xml").read_text()
        ).itertext()
    )
    for literal in [
        "no such period shall begin as to any individual after such individual attains retirement age",
        "the month preceding the month in which the individual attains retirement age",
        "the calendar years 2000 through 2004",
        "the calendar years 2017 through 2021",
    ]:
        assert literal in act
    for literal in [
        "Your period of disability may not begin after you have attained full retirement age",
        "The month before the month in which you attain full retirement age",
        "The month immediately preceding your termination month",
        "the last month for which you received benefits",
    ]:
        assert literal in cfr


@settings(max_examples=15, deadline=None)
@given(
    birth_year=st.integers(1938, 1960),
    birth_month=st.integers(1, 12),
    birth_day=st.sampled_from([1, 2]),
    days_later=st.integers(0, 366),
    unknown_prior=st.booleans(),
)
def test_known_establishment_at_or_after_fra_is_always_invalid(
    birth_year, birth_month, birth_day, days_later, unknown_prior
):
    from datetime import timedelta

    birth = date(birth_year, birth_month, birth_day)
    onset = _act_fra(birth).replace(day=1) + timedelta(days=days_later)
    with pytest.raises(InvalidFamilyInput):
        i.Person(
            birth,
            disability_onset=onset,
            current_disability_period_established=True,
            current_disability_period_provenance=OBSERVED,
            prior_disability_periods_provenance=(
                i.EarningsProvenance.UNKNOWN if unknown_prior else OBSERVED
            ),
        )


def test_fra_month_onset_cannot_begin_after_statutory_period_end():
    # A March1 birth attainsFRA onFebruary28. Act216(i)(2)(D)(i)
    # ends any periodJanuary31, before thisFebruary15 onset.
    with pytest.raises(InvalidFamilyInput):
        person = _person(date(1960, 3, 1), disability_onset=date(2027, 2, 15))
        i.fully_insured_requirement(person, date(2027, 3, 1))


def test_unknown_fra_month_onset_cannot_supply_freeze_uncertainty():
    person = i.Person(
        date(1960, 3, 1),
        disability_onset=date(2027, 2, 15),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=None,
        current_disability_period_provenance=i.EarningsProvenance.UNKNOWN,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2027, 3, 1)
    assert i.fully_insured_requirement(person, month) == 40
    result = i.insured_status(
        person,
        history(person, month, {y: 4 for y in range(2016, 2026)}),
        month,
        test=i.InsuredTest.FULLY,
    )
    assert result.fully.insured
    assert result.unknown_facts == ()
    assert result.current_disability_period_start is None


@settings(max_examples=15, deadline=None)
@example(year=2023, month=1, convention=False)
@given(
    year=st.integers(2023, 2030),
    month=st.integers(1, 12),
    convention=st.booleans(),
)
def test_declared_period_end_provenance_roundtrip_and_invalid_combinations(
    year, month, convention
):
    import calendar

    person, _, _ = _endpoint_case()
    ending = date(year, month, calendar.monthrange(year, month)[1])
    # Preserve the original twenty positional constructor slots.
    original_positional = i.Person(
        person.birth_date,
        person.sex,
        person.death_date,
        person.disability_onset,
        person.prior_disability_periods,
        person.statutory_blindness,
        person.conditions,
        person.alien_worker,
        person.ssn_assignment_date,
        person.ssn_never_assigned,
        person.rib_entitlement_month,
        person.dib_entitlement_month,
        person.prior_disability_periods_provenance,
        person.prior_disability_periods_convention_id,
        person.current_disability_period_established,
        person.current_disability_period_provenance,
        person.current_disability_period_convention_id,
        person.sspa211_applies,
        person.sspa211_provenance,
        person.sspa211_convention_id,
    )
    assert original_positional == person
    provenance = (
        i.EarningsProvenance.CONVENTION_FILLED if convention else OBSERVED
    )
    identifier = "invented-calendar-end" if convention else None
    declared = replace(
        person,
        current_disability_period_end=ending,
        current_disability_period_end_provenance=provenance,
        current_disability_period_end_convention_id=identifier,
    )
    assert declared.current_disability_period_end == ending
    assert declared.current_disability_period_end_provenance is provenance
    assert replace(declared) == declared
    with pytest.raises(InvalidFamilyInput):
        replace(declared, current_disability_period_end=None)
    with pytest.raises(InvalidFamilyInput):
        replace(
            declared,
            current_disability_period_end_provenance=(
                i.EarningsProvenance.UNKNOWN
            ),
            current_disability_period_end_convention_id=None,
        )
    with pytest.raises(InvalidFamilyInput):
        replace(declared, current_disability_period_end=ending.replace(day=1))
