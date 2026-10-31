"""Statutory conformance: every possible establishment route survives.

Invented declarations and captured statutory rules only; no population,
behavioral, payment, or forecast claim.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history
from tests.test_track_b_insured_status_sources import source_text

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN


def _short_period_case():
    person = i.Person(
        date(2000, 2, 2),
        disability_onset=date(2029, 1, 15),
        statutory_blindness=True,
        dib_entitlement_month=date(2028, 10, 1),
        prior_disability_periods_provenance=UNKNOWN,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2029, 4, 1)
    return person, history(person, month, {2027: 2, 2028: 4}), month


def _pre1956_case(*, established=True, unknown_prior=False, earlier=14):
    person = i.Person(
        date(1900, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1952, 7, 15),
        prior_disability_periods_provenance=(
            UNKNOWN if unknown_prior else OBSERVED
        ),
        current_disability_period_established=established,
        current_disability_period_provenance=(
            UNKNOWN if established is None else OBSERVED
        ),
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 2, 1)
    counts = {
        year: min(4, max(0, earlier - 4 * n))
        for n, year in enumerate(range(1938, 1942))
    }
    counts.update({1951: 4, 1952: 2})
    return person, history(person, month, counts), month


def _declared_end_unknown_earnings_case(*, first=2, ending=date(2022, 3, 31)):
    person = i.Person(
        date(2000, 2, 2),
        statutory_blindness=True,
        disability_onset=date(2022, 1, 15),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=ending,
        current_disability_period_end_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(2023, 1, 1)
    years = history(person, month, {2020: first, 2021: 5 - first, 2023: 1})
    years[2022] = i.CoverageYear(UNKNOWN)
    return person, years, month


def _prior_overlap_unknown_earnings_case(*, missing_year=1971):
    person = i.Person(
        date(1910, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=date(1972, 2, 15),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1952, 7, 15), date(1972, 1, 31)),
        ),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1973, 1, 1)
    counts = {
        1938: 4,
        1939: 4,
        1940: 4,
        1941: 2,
        1951: 4,
        1952: 2,
        **{year: 4 for year in range(1967, 1972)},
        1973: 1,
    }
    counts[missing_year] = 3
    years = history(person, month, counts)
    years[1972] = i.CoverageYear(UNKNOWN)
    # RS .480 permits this prior start with 20 total QCs and all six
    # 1951Q1--1952Q2 QCs; its application alternative admits 1964 filing.
    # The prior period exceeds five months and ends before FRA (.321).
    assert (
        sum(counts[year] for year in (1938, 1939, 1940, 1941, 1951, 1952))
        == 20
    )
    assert years[1951].qc_quarters == (True,) * 4
    assert years[1952].qc_quarters[:2] == (True,) * 2
    return person, years, month


def _retained_row(person, years, month, test, *, reason=None):
    row = i.evaluate_insured_status(
        "invented-route",
        Fraction(1),
        lambda: i.insured_status(person, years, month, test=test),
    )
    denominator = count_family_outcomes((row,))
    assert denominator.rows == 1
    assert denominator.weight == 1
    if reason is not None:
        assert row.unsupported.reason is reason
    if row.unsupported is not None:
        assert denominator.unsupported_rows == 1
        assert denominator.unsupported_weight == 1
    else:
        assert denominator.unsupported_rows == 0
        assert denominator.unsupported_weight == 0
    return row


def test_unknown_earnings_can_place_insured_start_before_declared_end():
    person, years, month = _declared_end_unknown_earnings_case()
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS


def test_unknown_earnings_before_declared_end_retains_denominator_row():
    person, years, month = _declared_end_unknown_earnings_case()
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.FULLY,
        reason=i.InsuredUnsupportedReason.UNKNOWN_EARNINGS,
    )


@settings(max_examples=8, deadline=None)
@example(first=2, ending_month=3)
@given(
    first=st.integers(1, 4),
    ending_month=st.sampled_from([1, 3, 12]),
)
def test_possible_unknown_earnings_filling_prevents_declared_end_input_error(
    first, ending_month
):
    """An invalid lower completion never disproves a valid upper one."""
    person, years, month = _declared_end_unknown_earnings_case(
        first=first, ending=date(2022, ending_month, 31)
    )
    concrete_validity = []
    for count in range(5):
        concrete = dict(years)
        concrete[2022] = i.CoverageYear(OBSERVED, qc_count=count)
        try:
            result = i.insured_status(
                person, concrete, month, test=i.InsuredTest.FULLY
            )
        except i.InvalidFamilyInput:
            concrete_validity.append(False)
        else:
            concrete_validity.append(True)
            assert result.current_disability_period_start == date(2022, 1, 15)
    assert concrete_validity == [False, True, True, True, True]
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.FULLY,
        reason=i.InsuredUnsupportedReason.UNKNOWN_EARNINGS,
    )


def test_unknown_earnings_can_avoid_derived_prior_quarter_overlap():
    person, years, month = _prior_overlap_unknown_earnings_case()
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason is i.InsuredUnsupportedReason.UNKNOWN_EARNINGS
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.FULLY,
        reason=i.InsuredUnsupportedReason.UNKNOWN_EARNINGS,
    )


@settings(max_examples=4, deadline=None)
@example(missing_year=1971)
@given(missing_year=st.integers(1968, 1971))
def test_possible_lower_earnings_filling_prevents_upper_overlap_input_error(
    missing_year,
):
    """An invalid upper-credit period cannot disprove every completion.

    The declared prior start meets the captured pre1956 alternate test.
    Zero 1972 QCs yields an insured new start in 1973Q1. More 1972 QCs
    move that start into the prior ending quarter, which the interface's
    nonoverlapping-quarter representation rejects for that completion.
    """
    person, years, month = _prior_overlap_unknown_earnings_case(
        missing_year=missing_year
    )
    concrete_validity = []
    for count in range(5):
        concrete = dict(years)
        concrete[1972] = i.CoverageYear(
            OBSERVED, qc_quarters=tuple(n < count for n in range(4))
        )
        try:
            result = i.insured_status(
                person, concrete, month, test=i.InsuredTest.FULLY
            )
        except i.InvalidFamilyInput:
            concrete_validity.append(False)
        else:
            concrete_validity.append(True)
            assert result.fully.insured
            assert result.current_disability_period_start == date(1973, 1, 1)
    assert concrete_validity == [True, False, False, False, False]
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.FULLY,
        reason=i.InsuredUnsupportedReason.UNKNOWN_EARNINGS,
    )


def test_short_dib_entitled_prior_period_keeps_unknown_history_refusal():
    """Reviewer's ALS-waiver filling defeats a five-month emptiness proof."""
    person, years, month = _short_period_case()
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.FULLY)
    assert error.value.reason is i.InsuredUnsupportedReason.UNKNOWN_PERIODS


def test_short_dib_entitled_unknown_history_keeps_one_denominator_row():
    person, years, month = _short_period_case()
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.FULLY,
        reason=i.InsuredUnsupportedReason.UNKNOWN_PERIODS,
    )


@pytest.mark.parametrize(
    "ending", [date(2028, 10, 31), date(2028, 11, 30), date(2028, 12, 31)]
)
def test_short_dib_entitled_concrete_prior_period_is_valid(ending):
    person, years, month = _short_period_case()
    filled = replace(
        person,
        prior_disability_periods_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(2028, 10, 1), ending),
        ),
    )
    result = i.insured_status(filled, years, month, test=i.InsuredTest.FULLY)
    assert result.fully.insured
    assert result.fully.required == 6
    assert result.fully.qc_count_lower == result.fully.qc_count_upper == 6
    assert result.current_disability_period_start == date(2029, 1, 15)
    row = _retained_row(filled, years, month, i.InsuredTest.FULLY)
    assert row.supported
    assert row.result == result


def test_pre1956_established_period_retains_automatic_specialist_refusal():
    person, years, month = _pre1956_case()
    with pytest.raises(i.InsuredConfigurationUnsupported) as error:
        i.insured_status(person, years, month, test=i.InsuredTest.DISABILITY)
    assert (
        error.value.reason is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )


@pytest.mark.parametrize("test", list(i.InsuredTest))
@pytest.mark.parametrize("unknown_prior", [False, True])
def test_pre1956_established_period_retains_denominator_for_every_request(
    test, unknown_prior
):
    person, years, month = _pre1956_case(unknown_prior=unknown_prior)
    _retained_row(
        person,
        years,
        month,
        test,
        reason=i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
    )


@pytest.mark.parametrize("test", list(i.InsuredTest))
@pytest.mark.parametrize("unknown_prior", [False, True])
def test_pre1956_unknown_establishment_cannot_remove_denominator(
    test, unknown_prior
):
    person, years, month = _pre1956_case(
        established=None, unknown_prior=unknown_prior
    )
    row = _retained_row(person, years, month, test)
    if row.unsupported is not None:
        assert row.unsupported.reason in {
            i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
            i.InsuredUnsupportedReason.UNKNOWN_CURRENT_PERIOD,
            i.InsuredUnsupportedReason.UNKNOWN_PERIODS,
        }
    else:
        # The direct-QC record is fully insured even without a freeze.
        assert test is i.InsuredTest.FULLY
        assert row.result.fully.insured


@pytest.mark.parametrize("condition", list(i.CoverageCondition))
def test_flagged_specialist_route_precedes_ordinary_establishment_rejection(
    condition,
):
    person, years, month = _pre1956_case()
    person = replace(person, conditions=(condition,))
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.ALL,
        reason=i.InsuredUnsupportedReason[condition.name],
    )


def test_unresolved_railroad_compensation_retains_independent_flagged_route():
    """Unreported pre1978 RR compensation can establish a freeze (.350)."""
    person = i.Person(
        date(1930, 2, 2),
        disability_onset=date(1952, 7, 15),
        conditions=(i.CoverageCondition.RAILROAD_CREDITS,),
        prior_disability_periods_provenance=OBSERVED,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 2, 1)
    years = history(person, month)
    # Ordinary wages are observed; the separately flagged RR compensation
    # is unresolved. This is not a declaration of final credited QCs.
    years[1950] = i.CoverageYear(OBSERVED, quarterly_wages=(Fraction(0),) * 4)
    _retained_row(
        person,
        years,
        month,
        i.InsuredTest.ALL,
        reason=i.InsuredUnsupportedReason.RAILROAD_CREDITS,
    )


@settings(max_examples=6, deadline=None)
@example(ending_year=1959, extra=0)
@given(ending_year=st.integers(1959, 1960), extra=st.integers(0, 2))
def test_unknown_prior_history_preserves_pre1956_alternate_prior_start(
    ending_year, extra
):
    """An earlier specialist freeze may rescue an ordinary later start.

    Current medical onset is after 1955, so checking only the current
    onset for the alternate test cannot prove the prior history empty.
    The earlier period satisfies the independently pinned RS .480 test.
    """
    person, _, month = _pre1956_case(unknown_prior=True)
    person = replace(person, disability_onset=date(1964, 7, 15))
    years = history(
        person,
        month,
        {
            1938: 4,
            1939: 4,
            1940: 4,
            1941: 2,
            1951: 4,
            1952: 2,
            1961: 4,
            1962: 4,
            1963: 4,
            1964: 2 + extra,
        },
    )
    filled = replace(
        person,
        prior_disability_periods_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(1952, 7, 15), date(ending_year, 12, 31)),
        ),
    )
    concrete = i.insured_status(filled, years, month, test=i.InsuredTest.FULLY)
    assert concrete.fully.insured
    assert concrete.current_disability_period_start == date(1964, 7, 15)
    _retained_row(person, years, month, i.InsuredTest.FULLY)
    assert _retained_row(filled, years, month, i.InsuredTest.FULLY).supported


@settings(max_examples=18, deadline=None)
@example(route="short_dib", ending_month=12, earlier=14, flag=None)
@example(route="pre1956", ending_month=10, earlier=14, flag=None)
@example(
    route="flagged",
    ending_month=10,
    earlier=14,
    flag=i.CoverageCondition.RAILROAD_CREDITS,
)
@given(
    route=st.sampled_from(["short_dib", "pre1956", "flagged"]),
    ending_month=st.integers(10, 12),
    earlier=st.integers(14, 16),
    flag=st.one_of(st.none(), st.sampled_from(list(i.CoverageCondition))),
)
def test_invalid_declaration_has_no_short_or_specialist_valid_filling(
    route, ending_month, earlier, flag
):
    """One-way soundness includes short entitlement and specialist routes.

    A valid short DIB-entitled filling is checked through the public rule.
    For the pre1956 fillings, the independent RS .480 criterion supplies
    20 total QCs and all six preceding 1951Q1--1952Q2 QCs. A named
    specialist refusal therefore represents a possible declaration rather
    than evidence that every filling is invalid. Explicit flags retain
    their own refusal, including when the ordinary predicate fails.
    """
    possible = []
    if route == "short_dib":
        import calendar

        person, years, month = _short_period_case()
        end = date(
            2028, ending_month, calendar.monthrange(2028, ending_month)[1]
        )
        fillings = [
            replace(person, prior_disability_periods_provenance=OBSERVED),
            replace(
                person,
                prior_disability_periods_provenance=OBSERVED,
                prior_disability_periods=(
                    i.DisabilityPeriod(date(2028, 10, 1), end),
                ),
            ),
        ]
        requested = i.InsuredTest.FULLY
    else:
        person, years, month = _pre1956_case(
            unknown_prior=True, earlier=earlier
        )
        if route == "flagged":
            flag = flag or i.CoverageCondition.MILITARY_CREDITS
            person = replace(person, conditions=(flag,))
        fillings = [
            replace(person, prior_disability_periods_provenance=OBSERVED)
        ]
        requested = i.InsuredTest.DISABILITY
        assert sum(sum(row.qc_quarters or ()) for row in years.values()) >= 20
        assert years[1951].qc_quarters == (True,) * 4
        assert years[1952].qc_quarters[:2] == (True,) * 2
        possible.append(True)

    invalid = False
    try:
        i.insured_status(person, years, month, test=requested)
    except i.InvalidFamilyInput:
        invalid = True
    except i.InsuredConfigurationUnsupported:
        pass
    for filled in fillings:
        try:
            i.insured_status(filled, years, month, test=requested)
        except i.InvalidFamilyInput:
            possible.append(False)
        except i.InsuredConfigurationUnsupported as refusal:
            if route != "short_dib":
                assert refusal.reason in {
                    i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
                    *(
                        i.InsuredUnsupportedReason[c.name]
                        for c in person.conditions
                    ),
                }
                possible.append(True)
        else:
            possible.append(True)
    if invalid:
        assert not any(possible)
    if any(possible):
        assert not invalid


def test_short_entitlement_and_specialist_premises_are_captured():
    act = source_text("lii_usc_42_416")
    assert (
        "or such individual was entitled to benefits under section 423 of this title for one or more months in such period"
        in act
    )
    waiting = source_text("ecfr_20cfr404_315")
    assert (
        "You have been medically determined to have amyotrophic lateral sclerosis"
        in waiting
    )
    alternate = source_text("poms_rs_00301_480")
    assert (
        "the wage earner had at least 20 quarters of coverage (QC) by the end of that quarter;"
        in alternate
    )
    assert (
        "all quarters beginning with 03/51 up to (but not including) that quarter are QCs and there are at least six such QCs."
        in alternate
    )
    railroad = source_text("poms_rs_00301_350")
    assert (
        "We may also use compensation in determining the number of QCs in freeze cases, regardless of entitlement to, or eligibility for an RR annuity."
        in railroad
    )
