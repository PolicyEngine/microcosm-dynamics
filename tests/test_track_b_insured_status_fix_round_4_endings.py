"""Statutory conformance: unknown administrative endings cover all quarters.

Invented cases and captured statutory authority only; no population,
behavioral, or forecast claim.
"""

import calendar
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED


def _person(**facts):
    return i.Person(
        date(2000, 2, 2),
        disability_onset=date(2022, 1, 15),
        statutory_blindness=True,
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
        **facts,
    )


def _declared(person, ending):
    return replace(
        person,
        current_disability_period_end=ending,
        current_disability_period_end_provenance=OBSERVED,
    )


def _qend(quarter):
    year, within_year = divmod(quarter, 4)
    month = within_year * 3 + 3
    return date(year, month, calendar.monthrange(year, month)[1])


def _endings(start, month, cap=date(2067, 1, 31)):
    """Enumerate the brief's quarter completions, independently of the rule."""
    first = start.year * 4 + (start.month - 1) // 3
    last = min(
        month.year * 4 + (month.month - 1) // 3,
        cap.year * 4 + (cap.month - 1) // 3,
    )
    values = [min(_qend(quarter), cap) for quarter in range(first, last + 1)]
    # One completion strictly past the query represents a running period.
    if cap > _qend(month.year * 4 + (month.month - 1) // 3):
        values.append(min(_qend(last + 1), cap))
    return tuple(values)


@pytest.mark.parametrize(
    "month,kind,counts,early_insured,early_required",
    [
        (
            date(2026, 3, 1),
            i.InsuredTest.CURRENTLY,
            {2017: 1, 2020: 4, 2021: 1, 2025: 1},
            True,
            6,
        ),
        (
            date(2067, 2, 1),
            i.InsuredTest.FULLY,
            {2017: 1, 2020: 4, 2021: 1},
            False,
            37,
        ),
    ],
    ids=["earlier-administrative-end", "fra-is-only-an-upper-bound"],
)
def test_unknown_end_retains_disagreeing_earlier_end_and_denominator_row(
    month, kind, counts, early_insured, early_required
):
    person = _person()
    years = history(person, month, counts)
    early = i.insured_status(
        _declared(person, date(2024, 12, 31)), years, month, test=kind
    )
    decision = getattr(early, kind.value)
    assert decision.insured is early_insured
    assert decision.required == early_required
    assert decision.qc_count_lower == decision.qc_count_upper == 6

    running = i.insured_status(
        _declared(person, date(2067, 1, 31)), years, month, test=kind
    )
    assert getattr(running, kind.value).insured is not early_insured
    if kind is i.InsuredTest.CURRENTLY:
        assert running.currently.qc_count_lower == 5
        assert running.currently.qc_count_upper == 5
    else:
        assert running.fully.required == 6
        assert (
            running.fully.qc_count_lower == running.fully.qc_count_upper == 6
        )

    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=kind)
    assert error.value.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_END
    row = i.evaluate_insured_status(
        "unknown-administrative-end",
        Fraction(1),
        lambda: i.insured_status(person, years, month, test=kind),
    )
    assert row.unsupported.reason is error.value.reason
    denominator = count_family_outcomes([row])
    assert denominator.rows == denominator.unsupported_rows == 1
    assert denominator.weight == denominator.unsupported_weight == 1


def _assert_count_envelope(unknown, concrete, kind):
    bound = getattr(unknown, kind.value)
    exact = getattr(concrete, kind.value)
    assert bound.insured is exact.insured
    assert bound.qc_count_lower <= exact.qc_count_lower
    assert exact.qc_count_upper <= bound.qc_count_upper
    assert bound.fully_qc_count_lower <= exact.fully_qc_count_lower
    assert exact.fully_qc_count_upper <= bound.fully_qc_count_upper
    for year, (lower, upper) in concrete.qcs_by_year.items():
        assert unknown.qcs_by_year[year][0] <= lower
        assert upper <= unknown.qcs_by_year[year][1]


def test_unknown_end_count_envelope_contains_earliest_currently_completion():
    person = _person()
    month = date(2026, 3, 1)
    years = history(person, month, {2017: 1, 2020: 4, 2021: 1})
    unknown = i.insured_status(
        person, years, month, test=i.InsuredTest.CURRENTLY
    )
    assert not unknown.currently.insured
    assert "current_disability_period_end" in unknown.unknown_facts
    for ending in _endings(person.disability_onset, month):
        concrete = i.insured_status(
            _declared(person, ending),
            years,
            month,
            test=i.InsuredTest.CURRENTLY,
        )
        _assert_count_envelope(unknown, concrete, i.InsuredTest.CURRENTLY)


def test_unknown_end_annual_count_envelope_contains_earlier_completions():
    person = _person()
    month = date(2026, 3, 1)
    years = history(person, month, {2017: 1, 2020: 4, 2021: 1, 2025: 1})
    unknown = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert unknown.fully.insured
    for ending in _endings(person.disability_onset, month):
        concrete = i.insured_status(
            _declared(person, ending), years, month, test=i.InsuredTest.FULLY
        )
        _assert_count_envelope(unknown, concrete, i.InsuredTest.FULLY)


@pytest.mark.parametrize("month", [date(2067, 2, 1), date(2068, 2, 1)])
@pytest.mark.parametrize("unknown_prior", [False, True])
def test_unknown_end_remains_unknown_at_and_after_fra_when_status_agrees(
    month,
    unknown_prior,
):
    person = _person()
    if unknown_prior:
        person = replace(
            person,
            prior_disability_periods_provenance=i.EarningsProvenance.UNKNOWN,
        )
    years = history(person, month, {year: 4 for year in range(2012, 2022)})
    result = i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert "current_disability_period_end" in result.unknown_facts
    assert result.decided_despite_unknowns
    for ending in (date(2022, 3, 31), date(2024, 12, 31), date(2067, 1, 31)):
        concrete = i.insured_status(
            _declared(person, ending), years, month, test=i.InsuredTest.FULLY
        )
        _assert_count_envelope(result, concrete, i.InsuredTest.FULLY)


@settings(max_examples=12, deadline=None)
@example(
    query_quarters=16, late=1, kind=i.InsuredTest.CURRENTLY, birth_shift=0
)
@given(
    query_quarters=st.integers(1, 16),
    late=st.integers(0, 4),
    kind=st.sampled_from([i.InsuredTest.FULLY, i.InsuredTest.CURRENTLY]),
    birth_shift=st.integers(0, 3),
)
def test_unknown_end_status_and_every_count_cover_all_quarter_completions(
    query_quarters, late, kind, birth_shift
):
    person = replace(
        _person(),
        birth_date=date(2000 + birth_shift, 2, 2),
        disability_onset=date(2022 + birth_shift, 1, 15),
    )
    query = (2022 + birth_shift) * 4 + query_quarters
    year, quarter = divmod(query, 4)
    month = date(year, quarter * 3 + 1, 1)
    years = history(
        person,
        month,
        {
            2017 + birth_shift: 1,
            2020 + birth_shift: 4,
            2021 + birth_shift: 1,
            month.year: late,
        },
    )
    concrete = [
        i.insured_status(_declared(person, ending), years, month, test=kind)
        for ending in _endings(person.disability_onset, month)
    ]
    try:
        result = i.insured_status(person, years, month, test=kind)
    except i.InsuredConfigurationUnsupported as error:
        assert error.reason is i.InsuredUnsupportedReason.CURRENT_PERIOD_END
        assert (
            len({getattr(value, kind.value).insured for value in concrete}) > 1
        )
        return
    assert "current_disability_period_end" in result.unknown_facts
    for value in concrete:
        _assert_count_envelope(result, value, kind)


def _assert_dli_envelope(unknown, concrete):
    if concrete.lower is not None:
        assert unknown.lower is None or unknown.lower <= concrete.lower
    else:
        assert unknown.lower is None
    if concrete.upper is not None:
        assert unknown.upper is not None
        assert concrete.upper <= unknown.upper
    if concrete.right_censored:
        assert unknown.right_censored


@settings(max_examples=8, deadline=None)
@example(query_quarters=8, late=0, blind=False)
@given(
    query_quarters=st.integers(1, 8),
    late=st.integers(0, 4),
    blind=st.booleans(),
)
def test_unknown_end_dli_contains_every_administrative_end_completion(
    query_quarters, late, blind
):
    person = replace(_person(), statutory_blindness=blind)
    query = 2022 * 4 + query_quarters
    year, quarter = divmod(query, 4)
    month = date(year, quarter * 3 + 1, 1)
    years = history(
        person,
        month,
        {2020: 4, 2021: 2, month.year: late},
    )
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert result.disability.insured
    assert "current_disability_period_end" in result.unknown_facts
    for ending in _endings(person.disability_onset, month):
        concrete = i.insured_status(
            _declared(person, ending),
            years,
            month,
            test=i.InsuredTest.DISABILITY,
        )
        _assert_count_envelope(result, concrete, i.InsuredTest.DISABILITY)
        _assert_dli_envelope(result.dli, concrete.dli)


def test_earlier_administrative_ending_is_quoted_from_captured_authority():
    sources = Path(__file__).parent / "data/track_b/insured_status_sources"
    cfr = "".join(
        ET.fromstring(
            (sources / "ecfr_20cfr404_321.xml").read_text()
        ).itertext()
    )
    assert "whichever of the following is the earliest" in cfr
    assert "If you perform substantial gainful activity" in cfr
    assert "the last month for which you received benefits" in cfr
    act = (sources / "lii_usc_42_416_excerpts.txt").read_text()
    assert "whichever of the following months is the earlier" in act
    assert "the first month for which no benefit is payable" in act
