"""Statutory conformance: observed continuity restricts possible endings.

Invented declarations only; no population, behavioral, or forecast claim.
"""

import calendar
from dataclasses import fields, replace
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import InvalidFamilyInput
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_fix_round_4_endings import (
    _declared,
    _person,
)

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
CONVENTION = i.EarningsProvenance.CONVENTION_FILLED


def _running(person, through, **facts):
    return replace(
        person,
        current_disability_period_continues_through=through,
        current_disability_period_continues_through_provenance=OBSERVED,
        **facts,
    )


@pytest.mark.parametrize("through", [date(2026, 3, 1), date(2026, 3, 31)])
def test_query_quarter_continuity_retains_ending_ambiguity(through):
    person = _running(_person(), through)
    month = date(2026, 3, 1)
    years = history(person, month, {2017: 1, 2020: 4, 2021: 1, 2026: 1})
    with pytest.raises(i.InsuredConfigurationUnsupported) as exc:
        i.insured_status(person, years, month, test=i.InsuredTest.CURRENTLY)
    assert exc.value.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_END
    end_of_query = i.insured_status(
        _declared(person, date(2026, 3, 31)),
        years,
        month,
        test=i.InsuredTest.CURRENTLY,
    ).currently
    later = i.insured_status(
        _declared(person, date(2026, 6, 30)),
        years,
        month,
        test=i.InsuredTest.CURRENTLY,
    ).currently
    assert end_of_query.insured and end_of_query.qc_count_lower == 6
    assert not later.insured and later.qc_count_lower == 5


@pytest.mark.parametrize("through", [date(2026, 4, 1), date(2027, 1, 1)])
def test_later_continuity_makes_query_quarter_interior(through):
    person = _running(_person(), through)
    month = date(2026, 3, 1)
    result = i.insured_status(
        person,
        history(person, month, {2017: 1, 2020: 4, 2021: 1, 2026: 1}),
        month,
        test=i.InsuredTest.CURRENTLY,
    )
    assert not result.currently.insured
    assert (
        result.currently.qc_count_lower == result.currently.qc_count_upper == 5
    )
    assert "current_disability_period_end" in result.unknown_facts


def test_age62_continuity_settles_full_insurance_without_an_end():
    person = _running(_person(), date(2062, 2, 1))
    month = date(2062, 2, 1)
    result = i.insured_status(
        person,
        history(person, month, {2017: 1, 2020: 4, 2021: 1}),
        month,
        test=i.InsuredTest.FULLY,
    )
    assert result.fully.insured
    assert result.fully.required == result.fully.upper_required == 6
    assert result.fully.qc_count_lower == result.fully.qc_count_upper == 6
    assert person.current_disability_period_end is None


@pytest.mark.parametrize(
    "facts",
    [
        {"current_disability_period_continues_through": date(2026, 1, 1)},
        {"current_disability_period_continues_through_provenance": OBSERVED},
        {
            "current_disability_period_continues_through": date(2026, 1, 1),
            "current_disability_period_continues_through_provenance": CONVENTION,
        },
        {
            "current_disability_period_continues_through_convention_id": "unused"
        },
    ],
)
def test_continuity_fact_must_match_its_provenance(facts):
    with pytest.raises(InvalidFamilyInput):
        replace(_person(), **facts)


@pytest.mark.parametrize(
    "facts,through",
    [
        ({}, date(2022, 1, 14)),
        ({}, date(2067, 2, 1)),
        (
            {
                "current_disability_period_established": False,
            },
            date(2026, 1, 1),
        ),
        (
            {
                "current_disability_period_end": date(2025, 12, 31),
                "current_disability_period_end_provenance": OBSERVED,
            },
            date(2026, 1, 1),
        ),
        ({"death_date": date(2025, 12, 31)}, date(2026, 1, 1)),
    ],
)
def test_continuity_requires_a_possible_established_period(facts, through):
    with pytest.raises(InvalidFamilyInput):
        _running(replace(_person(), **facts), through)


def test_continuity_cannot_precede_the_first_insured_start():
    person = _running(_person(), date(2022, 1, 31))
    month = date(2022, 10, 1)
    with pytest.raises(InvalidFamilyInput):
        i.insured_status(
            person,
            history(person, month, {2021: 4, 2022: 4}),
            month,
            test=i.InsuredTest.FULLY,
        )


def test_continuity_convention_is_reported_and_old_positional_fields_stay():
    person = replace(
        _person(),
        current_disability_period_continues_through=date(2026, 4, 1),
        current_disability_period_continues_through_provenance=CONVENTION,
        current_disability_period_continues_through_convention_id="running-v1",
    )
    names = [field.name for field in fields(i.Person)]
    assert names[-4] == "current_disability_period_end_convention_id"
    assert names[-3:] == [
        "current_disability_period_continues_through",
        "current_disability_period_continues_through_provenance",
        "current_disability_period_continues_through_convention_id",
    ]
    result = i.insured_status(
        person,
        history(person, date(2026, 3, 1), {2020: 4, 2021: 2}),
        date(2026, 3, 1),
        test=i.InsuredTest.FULLY,
    )
    assert (
        result.convention_facts["current_disability_period_continues_through"]
        == "running-v1"
    )


@settings(max_examples=20, deadline=None)
@given(
    through_month=st.integers(1, 12),
    recent=st.integers(0, 4),
    kind=st.sampled_from([i.InsuredTest.FULLY, i.InsuredTest.CURRENTLY]),
)
def test_continuity_only_narrows_candidates_and_all_concrete_ends_agree(
    through_month, recent, kind
):
    person = _person()
    through = date(2026, through_month, 1)
    running = _running(person, through)
    month = date(2026, 3, 1)
    years = history(person, month, {2017: 1, 2020: 4, 2021: 1, 2026: recent})
    credits = {
        year: i._credits(year, row, False) for year, row in years.items()
    }
    completed, start = i._with_current_period(person, credits, month, None)
    candidates = i._current_period_completions(person, completed, start, month)
    narrowed = i._current_period_completions(running, completed, start, month)
    all_ends = {p.prior_disability_periods[-1].end for p in candidates}
    ends = {p.prior_disability_periods[-1].end for p in narrowed}
    assert ends == {end for end in all_ends if end >= through}
    assert ends <= all_ends
    try:
        result = i.insured_status(running, years, month, test=kind)
    except i.InsuredConfigurationUnsupported as exc:
        assert exc.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_END
        return
    decision = getattr(result, kind.value)
    # Quarter endpoints are independent concrete administrative declarations.
    for year in (2026, 2027):
        for end_month in (3, 6, 9, 12):
            ending = date(
                year, end_month, calendar.monthrange(year, end_month)[1]
            )
            if ending < through:
                continue
            concrete = i.insured_status(
                _declared(running, ending), years, month, test=kind
            )
            concrete_decision = getattr(concrete, kind.value)
            assert decision.insured == concrete_decision.insured
            assert (
                decision.qc_count_lower
                <= concrete_decision.qc_count_lower
                <= concrete_decision.qc_count_upper
                <= decision.qc_count_upper
            )
