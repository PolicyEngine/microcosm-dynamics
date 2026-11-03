"""Statutory conformance: every route uses one feasible insured start.

Invented declarations only; no population, behavioral, or forecast claim.
The zero-credit blind and credit-adding cases, six-credit boundary,
clear alternate candidate, credited endpoint, and undeclared-period cases
pin unchanged behavior. The other cases expose the round-thirteen defects.
Round 23: 404.321(b)-(c) end a period on a month's last day, so a new
period can begin in the quarter a prior ended (RS00301.140 example 7); the
shared-quarter cases now refuse by the route's name or compute.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction

import pytest

from populace_dynamics.track_b import insured_status as i
from populace_dynamics.track_b.gross_benefits import count_family_outcomes
from tests.test_track_b_insured_status import history

OBSERVED = i.EarningsProvenance.OBSERVED
UNKNOWN = i.EarningsProvenance.UNKNOWN
WEIGHT = Fraction(11, 5)
FULLY_ROUTES = (
    i.CoverageCondition.DEEMED_FULLY_INSURED,
    i.CoverageCondition.TRANSITIONAL_INSURED,
    i.CoverageCondition.EARNED_BASIS,
    i.CoverageCondition.SIMPLIFIED_PRE1951,
)
CREDIT_ROUTES = (
    i.CoverageCondition.MILITARY_CREDITS,
    i.CoverageCondition.MEDICARE_GOVERNMENT_EMPLOYMENT,
)
RAW_ROUTES = (
    i.CoverageCondition.RAILROAD_CREDITS,
    i.CoverageCondition.FISCAL_TAXABLE_YEAR,
    i.CoverageCondition.SHORT_TAXABLE_YEAR,
)


def _person(**kwargs):
    facts = {
        "disability_onset": date(2000, 1, 15),
        "current_disability_period_established": True,
        "current_disability_period_provenance": OBSERVED,
        "current_disability_period_end": date(2000, 12, 31),
        "current_disability_period_end_provenance": OBSERVED,
        "prior_disability_periods_provenance": UNKNOWN,
        "conditions": (FULLY_ROUTES[0],),
        "sspa211_applies": False,
        "sspa211_provenance": OBSERVED,
    }
    facts.update(kwargs)
    return i.Person(date(1960, 2, 2), **facts)


def _evaluate(person, years, month, **kwargs):
    return i.evaluate_insured_status(
        "round-thirteen-common-start",
        WEIGHT,
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.FULLY, **kwargs
        ),
    )


def _invalid(person, years, month, **kwargs):
    rows = []
    with pytest.raises(i.InvalidFamilyInput, match="no possible insured"):
        rows.append(_evaluate(person, years, month, **kwargs))
    counts = count_family_outcomes(rows)
    assert counts.rows == counts.unsupported_rows == 0
    assert counts.weight == counts.unsupported_weight == 0


def _refusal(person, years, month, reason, **kwargs):
    row = _evaluate(person, years, month, **kwargs)
    assert row.result is None
    assert row.unsupported.reason is reason
    counts = count_family_outcomes((row,))
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == WEIGHT
    return row


def _alternate(*, onset, prior_end, end=date(1956, 3, 31), endpoint=False):
    person = i.Person(
        date(1900, 2, 2),
        sex=i.Sex.FEMALE,
        disability_onset=onset,
        current_disability_period_established=True,
        current_disability_period_provenance=OBSERVED,
        current_disability_period_end=end,
        current_disability_period_end_provenance=OBSERVED,
        prior_disability_periods=(
            i.DisabilityPeriod(date(1952, 7, 1), prior_end),
        ),
        prior_disability_periods_provenance=OBSERVED,
        sspa211_applies=False,
        sspa211_provenance=OBSERVED,
    )
    month = date(1968, 1, 1)
    credited = set(range(1938 * 4, 1938 * 4 + 14))
    credited.update(range(1951 * 4, 1951 * 4 + 6))
    if endpoint:
        credited.add(prior_end.year * 4 + (prior_end.month - 1) // 3)
    years = history(person, month)
    for year in years:
        if year < 1978:
            years[year] = i.CoverageYear(
                OBSERVED,
                qc_quarters=tuple(
                    year * 4 + quarter in credited for quarter in range(4)
                ),
            )
    return person, years, month


@pytest.mark.parametrize("coverage_end", [None, date(2000, 12, 1)])
def test_review_unknown_prior_cannot_remove_six_qc_floor(coverage_end):
    """Sol's first case, on direct and coverage-end public paths."""
    person = _person()
    month = date(2001, 1, 1)
    _invalid(
        person,
        history(person, month, end=coverage_end),
        month,
        coverage_end_month=coverage_end,
    )


@pytest.mark.parametrize("coverage_end", [None, date(1956, 3, 1)])
@pytest.mark.parametrize(
    "end", [date(1956, 3, 31), date(1956, 12, 31), date(1959, 12, 31)]
)
def test_an_alternate_start_can_share_the_quarter_a_prior_ended(
    coverage_end, end
):
    """Sol's second case and its two longer-period controls.

    The prior ends 1955-11-30, a month before the onset, so the period can
    begin in 1955Q4, where RS00301.480 may begin it; the rule refuses by
    that route's name.
    """
    person, years, month = _alternate(
        onset=date(1955, 12, 15), prior_end=date(1955, 11, 30), end=end
    )
    if coverage_end:
        years = {
            year: row
            for year, row in years.items()
            if year <= coverage_end.year
        }
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
        coverage_end_month=coverage_end,
    )


@pytest.mark.parametrize("condition", FULLY_ROUTES)
@pytest.mark.parametrize(
    "by_horizon,after_horizon",
    [(5, 0), (6, 0), (5, 1)],
    ids=["five", "six", "sixth-one-quarter-late"],
)
def test_unknown_prior_fully_route_floor_uses_horizon_credits(
    condition, by_horizon, after_horizon
):
    person = _person(conditions=(condition,))
    month = date(2001, 1, 1)
    years = history(
        person,
        month,
        {1980: 4, 1981: by_horizon - 4, 2001: after_horizon},
    )
    # Early QCs permit an under-31 prior start in an UNKNOWN completion;
    # the six-QC control therefore has one joint special-prior filling.
    # End 12/2000 permits a latest recovery/start in 10/2000 (2000Q4).
    # The sole 2001 QC is therefore one quarter after every possible start.
    if by_horizon < 6:
        _invalid(person, years, month)
    else:
        _refusal(
            person, years, month, i.InsuredUnsupportedReason[condition.name]
        )


@pytest.mark.parametrize("condition", FULLY_ROUTES)
def test_twenty_future_credits_cannot_repair_zero_by_start_horizon(condition):
    """The review's temporal-floor probe cannot use lifetime totals."""
    person = _person(conditions=(condition,))
    month = date(2007, 1, 1)
    years = history(person, month, {year: 4 for year in range(2002, 2007)})
    _invalid(person, years, month)


@pytest.mark.parametrize("condition", FULLY_ROUTES)
def test_blind_fully_route_with_zero_credits_keeps_named_refusal(condition):
    """Unchanged: 404.130(e) dispenses with the recent-credit test."""
    person = _person(conditions=(condition,), statutory_blindness=True)
    month = date(2001, 1, 1)
    _refusal(
        person,
        history(person, month),
        month,
        i.InsuredUnsupportedReason[condition.name],
    )


def test_blind_without_fully_route_still_needs_six_own_credits():
    """Unchanged: blindness alone does not supply fully insured status."""
    person = _person(conditions=(), statutory_blindness=True)
    month = date(2001, 1, 1)
    _invalid(person, history(person, month, {1998: 4, 1999: 1}), month)


@pytest.mark.parametrize("condition", (None, *CREDIT_ROUTES, *RAW_ROUTES))
def test_foreign_and_credit_adding_routes_precede_floor(condition):
    """Unchanged: these unresolved routes can add undeclared QCs."""
    person = _person(conditions=(condition,) if condition else ())
    month = date(2001, 1, 1)
    years = history(person, month)
    if condition in RAW_ROUTES:
        years[2000] = i.CoverageYear(OBSERVED, wages=Fraction(0))
    kwargs = {} if condition else {"totalization_credits": ("invented",)}
    _refusal(
        person,
        years,
        month,
        (
            i.InsuredUnsupportedReason[condition.name]
            if condition
            else i.InsuredUnsupportedReason.TOTALIZATION
        ),
        **kwargs,
    )


@pytest.mark.parametrize("endpoint", [False, True])
def test_alternate_uses_one_clear_candidate_after_prior_ending_quarter(
    endpoint,
):
    """A prior ending 1955-08-31 shares 1955Q3 with the onset, so 1955Q3
    and 1955Q4 may each start the period on the alternate."""
    person, years, month = _alternate(
        onset=date(1955, 9, 15),
        prior_end=date(1955, 8, 31),
        endpoint=endpoint,
    )
    _refusal(
        person,
        years,
        month,
        i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956,
    )


@pytest.mark.parametrize(
    "test",
    [i.InsuredTest.ALL, i.InsuredTest.CURRENTLY, i.InsuredTest.DISABILITY],
)
@pytest.mark.parametrize("end", [date(1956, 3, 31), date(1959, 12, 31)])
def test_every_test_refuses_a_shared_quarter_alternate_by_name(end, test):
    """No post-1955 start replaces the 1955Q4 alternate for any test."""
    person, years, month = _alternate(
        onset=date(1955, 12, 15), prior_end=date(1955, 11, 30), end=end
    )
    row = i.evaluate_insured_status(
        "round-thirteen-shared-alternate",
        WEIGHT,
        lambda: i.insured_status(person, years, month, test=test),
    )
    assert row.result is None
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )


@pytest.mark.parametrize(
    "established", [False, None], ids=["false", "unknown"]
)
def test_unestablished_alternate_keeps_prior_treatment(established):
    """Unestablished or UNKNOWN establishment keeps the named refusal."""
    person, years, month = _alternate(
        onset=date(1955, 12, 15), prior_end=date(1955, 11, 30)
    )
    person = replace(
        person,
        current_disability_period_established=established,
        current_disability_period_provenance=(
            UNKNOWN if established is None else OBSERVED
        ),
        current_disability_period_end=None,
        current_disability_period_end_provenance=UNKNOWN,
    )
    row = i.evaluate_insured_status(
        "round-thirteen-unestablished-control",
        WEIGHT,
        lambda: i.insured_status(
            person, years, month, test=i.InsuredTest.DISABILITY
        ),
    )
    assert row.result is None
    assert (
        row.unsupported.reason
        is i.InsuredUnsupportedReason.DISABILITY_BEFORE_1956
    )
    counts = count_family_outcomes((row,))
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == WEIGHT


def test_disability_witness_counts_the_quarter_a_prior_ended():
    """The prior ends a month before the onset, so 2000Q1 can begin the
    period (404.321(b)-(c)). Disregarding the prior (404.130(f)) leaves
    1999's three QCs and 2000's one in the window: 20 of 40 at 2000Q1. Past
    blindness can begin the prior with a 1999Q1 QC on that same filling.
    """
    person = _person(
        disability_onset=date(2000, 2, 15),
        conditions=(),
        prior_disability_periods=(
            i.DisabilityPeriod(date(1999, 1, 1), date(2000, 1, 31)),
        ),
        prior_disability_periods_provenance=OBSERVED,
    )
    month = date(2001, 1, 1)
    years = history(
        person,
        month,
        {1995: 4, 1996: 4, 1997: 4, 1998: 4, 1999: 3, 2000: 1},
    )
    result = i.insured_status(
        person, years, month, test=i.InsuredTest.DISABILITY
    )
    assert result.current_disability_period_start == date(2000, 2, 15)
    decision = result.disability
    assert decision.insured
    assert decision.rule == "disability_20_of_40"
    assert (
        decision.qc_count_lower,
        decision.qc_count_upper,
        decision.required,
    ) == (20, 20, 20)
    assert decision.qualifying_quarter == date(2000, 1, 1)
