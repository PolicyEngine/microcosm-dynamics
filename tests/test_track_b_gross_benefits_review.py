"""G review regressions over invented statutory reference families.

Verification class: statutory conformance. These tests admit gross benefits
only for supported configurations; no population, behavioral or forecast
claim is admitted.
All amounts are exact fractions, and the captured rules determine the input
windows. The late survivor departure is the reviewer's invented example.
"""

from __future__ import annotations

import dataclasses
import re
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2030, 1)
OLD_AGE = g.OwnBenefitKind.OLD_AGE


def _family(state, beneficiaries=(), month=NOW):
    return g.family_benefits(
        state,
        beneficiaries,
        payment_month=month,
        params=PARAMS,
        standalone=True,
    )


def _retired(**worker):
    return g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(1000),
        F(1750),
        worker=g.OwnBenefit(OLD_AGE, F(1000), **worker),
    )


def _refused_record(case, pia=F(1000)):
    if case == "eligibility":
        return (
            g.WorkerRecord(g.FamilyKind.RETIREMENT, 1979, pia),
            g.UnsupportedReason.ELIGIBILITY_BEFORE_1983,
        )
    if case == "disability":
        return (
            g.WorkerRecord(
                g.FamilyKind.DISABILITY,
                1990,
                pia,
                aime=2000,
                first_dib_entitlement=g.YearMonth(1980, 6),
            ),
            g.UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980,
        )
    return (
        g.WorkerRecord(
            g.FamilyKind.RETIREMENT,
            2020,
            pia,
            conditions={g.RecordCondition.WORKERS_COMPENSATION_OFFSET},
        ),
        g.UnsupportedReason.WORKERS_COMPENSATION_OFFSET,
    )


@pytest.mark.parametrize("prebuilt", [False, True])
def test_review_minimized_duplicate_input_precedes_record_refusal(prebuilt):
    record = g.WorkerRecord(g.FamilyKind.RETIREMENT, 1979, F(1000))
    child = g.Beneficiary("c", g.Role.CHILD)
    state = g.record_state(record, PARAMS) if prebuilt else None
    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        g.evaluate_family(
            "minimized",
            1,
            lambda: _family(
                state if prebuilt else g.record_state(record, PARAMS),
                [child, child],
            ),
        )


@given(
    st.sampled_from(["eligibility", "disability", "condition"]),
    st.booleans(),
    st.integers(1, 30_000),
    st.text(alphabet="abc123", min_size=1, max_size=8),
)
@settings(deadline=None)
def test_review_record_refusals_defer_to_inputs_in_both_entry_styles(
    case, prebuilt, dimes, child_id
):
    """Deferred coverage refusals never absorb an invalid family as a gap."""
    record, reason = _refused_record(case, F(dimes, 10))
    state = g.record_state(record, PARAMS) if prebuilt else None
    child = g.Beneficiary(child_id, g.Role.CHILD)

    def compute(members):
        return _family(
            state if prebuilt else g.record_state(record, PARAMS), members
        )

    with pytest.raises(g.InvalidFamilyInput, match="unique"):
        g.evaluate_family("invalid", 1, lambda: compute([child, child]))
    outcome = g.evaluate_family("valid", F(3, 2), lambda: compute([child]))
    assert not outcome.supported and outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight) == (1, F(3, 2))
    assert counts.unsupported_by_reason == {reason: (1, F(3, 2))}


def _cohort_route(route, birth, months):
    if route == "primitive":
        return g.worker_age_adjusted(F(1000), months, 0, birth, PARAMS)
    if route == "record":
        state = g.record_state(
            g.WorkerRecord(
                g.FamilyKind.RETIREMENT,
                birth + 62,
                F(1000),
                worker_reduction_months=months,
                worker_birth_year=birth,
            ),
            PARAMS,
        )
        return _family(state)
    if route == "worker_state":
        return _family(_retired(reduction_months=months, birth_year=birth))
    if route == "own_auxiliary":
        spouse = g.Beneficiary(
            "s",
            g.Role.SPOUSE,
            own_benefit=g.OwnBenefit(
                OLD_AGE, F(100), reduction_months=months, birth_year=birth
            ),
            own_benefit_first=True,
            birth_year=birth,
        )
    else:
        spouse = g.Beneficiary(
            "s", g.Role.SPOUSE, reduction_months=months, birth_year=birth
        )
    return _family(_retired(), [spouse])


COHORT_ROUTES = [
    "primitive",
    "record",
    "worker_state",
    "own_auxiliary",
    "spouse",
]


@pytest.mark.parametrize("route", COHORT_ROUTES)
def test_review_fra_65_allows_36_reduction_months_but_not_37(route):
    _cohort_route(route, 1935, 36)
    with pytest.raises(g.InvalidFamilyInput):
        _cohort_route(route, 1935, 37)


@given(
    st.integers(1921, 1964),
    st.sampled_from(COHORT_ROUTES),
    st.integers(1917, 1964),
)
@settings(deadline=None)
def test_review_cohort_reduction_bound_is_closed_at_fra_minus_62(
    birth, route, drc_birth
):
    """Reduction and DRC windows admit their endpoint, never the next month."""
    maximum = PARAMS.fra_months(birth) - 744
    _cohort_route(route, birth, maximum)
    with pytest.raises(g.InvalidFamilyInput):
        _cohort_route(route, birth, maximum + 1)
    credit_window = 840 - PARAMS.fra_months(drc_birth)
    assert g.delayed_credit_window_months(drc_birth, PARAMS) == credit_window
    monthly_credit = F(repr(PARAMS.delayed_credit_annual_rate(drc_birth))) / 12
    base, credited = g.worker_age_adjusted(
        F(1000), 0, credit_window, drc_birth, PARAMS
    )
    assert base == F(1000)
    assert credited == base + g.floor_dime(
        base * credit_window * monthly_credit
    )
    with pytest.raises(g.InvalidFamilyInput, match="age 70"):
        g.worker_age_adjusted(F(1000), 0, credit_window + 1, drc_birth, PARAMS)


def test_review_reduction_cohorts_and_pre_1917_windows_are_captured():
    assert "FRA for retirement or spouse's benefits is age 65" in source_text(
        "poms_rs_00615_003"
    )
    assert "number of months of entitlement before FRA" in source_text(
        "poms_rs_00615_010"
    )
    text = source_text("poms_rs_00615_692")
    # 1912 and 1913 have monthly DOB bands. A birth year alone identifies
    # their largest possible window, not each person's exact DOB window.
    rows = re.findall(
        r"(Before 02/02/12|\d{2}/\d{2}/\d{2} thru \d{2}/\d{2}/\d{2}) "
        r"65 1/12% 1% (\d+) [\d.]+%",
        text,
    )
    assert len(rows) == 25
    windows = dict(rows)
    assert windows["Before 02/02/12"] == "84"
    assert windows["01/02/13 thru 02/01/13"] == "72"
    assert windows["01/02/14 thru 01/01/17"] == "60"


@pytest.mark.parametrize(
    ("birth", "maximum"),
    [(1911, 84), (1912, 84), (1913, 72), (1914, 60), (1915, 60), (1916, 60)],
)
def test_review_pre_1917_credits_refuse_inside_window_and_error_beyond(
    birth, maximum
):
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        g.worker_age_adjusted(F(1000), 0, maximum, birth, PARAMS)
    assert (
        caught.value.reason is g.UnsupportedReason.DELAYED_CREDITS_BEFORE_1917
    )
    with pytest.raises(g.InvalidFamilyInput):
        g.worker_age_adjusted(F(1000), 0, maximum + 1, birth, PARAMS)


@given(st.integers(1914, 1916), st.integers(1, 60), st.integers(61, 84))
@settings(deadline=None)
def test_review_pre_1917_impossible_credits_are_input_errors(
    birth, legal, impossible
):
    with pytest.raises(g.FamilyConfigurationUnsupported):
        g.worker_age_adjusted(F(1000), 0, legal, birth, PARAMS)
    with pytest.raises(g.InvalidFamilyInput):
        g.worker_age_adjusted(F(1000), 0, impossible, birth, PARAMS)


@given(st.integers(1929, 1964), st.integers(1, 10))
@settings(deadline=None)
def test_review_own_and_auxiliary_birth_years_must_agree(birth, difference):
    own = g.OwnBenefit(OLD_AGE, F(100), birth_year=birth)
    spouse = g.Beneficiary(
        "s",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=own,
        own_benefit_first=True,
        birth_year=birth,
    )
    _family(_retired(), [spouse])
    with pytest.raises(g.InvalidFamilyInput):
        _family(
            _retired(),
            [dataclasses.replace(spouse, birth_year=birth + difference)],
        )


@given(st.integers(1921, 1964), st.integers(1, 10))
@settings(deadline=None)
def test_review_retirement_eligibility_cannot_follow_age_62(birth, later):
    record = g.WorkerRecord(
        g.FamilyKind.RETIREMENT,
        birth + 62,
        F(1000),
        worker_birth_year=birth,
    )
    g.record_state(record, PARAMS)
    with pytest.raises(g.InvalidFamilyInput):
        g.record_state(
            dataclasses.replace(record, eligibility_year=birth + 62 + later),
            PARAMS,
        )
    # Earlier DIB eligibility can govern a retirement record, 403(a)(2)(D).
    earlier = g.record_state(
        dataclasses.replace(record, eligibility_year=birth + 61), PARAMS
    )
    assert earlier.eligibility_year == birth + 61


@given(st.integers(1922, 1964), st.integers(1, 10))
@settings(deadline=None)
def test_review_direct_state_eligibility_cannot_follow_worker_age_62(
    birth, later
):
    """Direct states enforce the same cross-field identity as WorkerRecord."""
    state = dataclasses.replace(
        _retired(birth_year=birth), eligibility_year=birth + 62
    )
    # Keep the payment month beyond both years so this specifically checks
    # first eligibility by age 62, rather than eligibility after payment.
    month = g.YearMonth(2050, 1)
    _family(state, month=month)
    with pytest.raises(g.InvalidFamilyInput):
        _family(
            dataclasses.replace(state, eligibility_year=birth + 62 + later),
            month=month,
        )
    _family(
        dataclasses.replace(state, eligibility_year=birth + 61), month=month
    )


@given(
    st.one_of(
        st.integers(1929, 1939),
        st.integers(1946, 1956),
        st.integers(1963, 1990),
    ),
    st.integers(60, 84),
)
@settings(deadline=None)
def test_review_year_decided_widow_periods_must_match_the_birth_year(
    birth, supplied
):
    expected = g.widow_reduction_period_months(date(birth, 1, 2))
    assert expected == g.widow_reduction_period_months(date(birth + 1, 1, 1))

    def compute():
        widow = g.Beneficiary(
            "w",
            g.Role.WIDOW,
            reduction_months=1,
            reduction_period_months=supplied,
            birth_year=birth,
            child_in_care=False,
        )
        return _family(state, [widow])

    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(1000), F(1750), widow_drc_savings_clause=False
    )
    if supplied == expected:
        compute()
    else:
        with pytest.raises(g.InvalidFamilyInput):
            compute()


def _months_between(first, last):
    month = first
    while month <= last:
        yield month
        month = g.YearMonth(
            month.year + (month.month == 12), month.month % 12 + 1
        )


def test_review_child_departure_six_months_after_cola_refuses_later_widow():
    """Review reference: 1,500/2,584.20; 2.5% COLA; June child departure.

    Three survivor shares after COLA are 882.90 each, totaling 2,648.70.
    Two unreduced original benefits are 1,153.10 each, totaling 2,306.20.
    This fall is conservatively refused under 403(a)(5), including every
    later governed month after the family returns to a larger total.
    """
    state = g.record_state(
        g.WorkerRecord(g.FamilyKind.SURVIVOR, 2020, F(1500)), PARAMS
    )
    assert state.family_maximum == F("2584.20")
    members = [
        g.Beneficiary("m", g.Role.MOTHER_FATHER),
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
    ]
    guard = g.SavingsClauseGuard(
        g.YearMonth(2020, 1),
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    for month in _months_between(g.YearMonth(2020, 1), g.YearMonth(2025, 11)):
        guard.admit(_family(state, members, month))
    state = dataclasses.replace(
        state,
        pia=g.increase_by_colas(state.pia, [F("2.5")]),
        family_maximum=g.increase_by_colas(state.family_maximum, [F("2.5")]),
    )
    for month in _months_between(g.YearMonth(2025, 12), g.YearMonth(2026, 5)):
        result = _family(state, members, month)
        assert g.savings_clause_total(result) == F("2648.70")
        guard.admit(result)
    departure = _family(state, [members[0], members[2]], g.YearMonth(2026, 6))
    assert g.savings_clause_total(departure) == F("2306.20")
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        guard.admit(departure)
    assert caught.value.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    assert guard.refused_since == g.YearMonth(2026, 6)
    for month in _months_between(g.YearMonth(2026, 7), g.YearMonth(2027, 1)):
        future = (
            members
            if month.year == 2026
            else [
                g.Beneficiary("m", g.Role.WIDOW, child_in_care=False),
                *members[1:],
            ]
        )
        result = _family(state, future, month)
        assert g.savings_clause_total(result) >= guard.protected_total
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            guard.admit(result)
        assert caught.value.reason is g.UnsupportedReason.SAVINGS_CLAUSE


@given(st.integers(100, 20_000), st.booleans())
@settings(max_examples=40, deadline=None)
def test_review_guarded_household_keeps_refused_record_and_denominator(
    dimes, reverse
):
    """A household month is refused when any per-record guard refuses it."""
    first, second = g.YearMonth(2025, 11), g.YearMonth(2025, 12)
    pia = F(dimes, 10)
    kids = tuple(g.Beneficiary(c, g.Role.CHILD) for c in ("c1", "c2", "c3"))
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        g.floor_dime(pia * F(3, 2)),
        widow_drc_savings_clause=False,
    )
    records = {
        "protected": g.HouseholdRecord("dead", state, kids),
        "unaffected": g.HouseholdRecord("worker", _retired()),
    }
    if reverse:
        records = dict(reversed(list(records.items())))
    guards = {
        key: g.SavingsClauseGuard(
            first,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        for key in records
    }
    admitted = g.household_month_outcome(
        records, payment_month=first, params=PARAMS, guards=guards, key="first"
    )
    assert admitted.supported
    # A PIA rise protects the preceding three-child total. One child now
    # receives only .75 of the slightly higher PIA, below that total.
    higher = dataclasses.replace(
        state,
        pia=state.pia + F("0.1"),
        family_maximum=state.family_maximum + F("0.1"),
    )
    records["protected"] = g.HouseholdRecord("dead", higher, kids[:1])
    refused = g.household_month_outcome(
        records,
        payment_month=second,
        params=PARAMS,
        guards=guards,
        key="second",
    )
    assert not refused.supported
    assert refused.unsupported.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    assert refused.unsupported.record_id == "protected"
    assert all(
        guard.next_month == g.YearMonth(2026, 1) for guard in guards.values()
    )
    counts = g.count_family_outcomes([admitted, refused])
    assert (counts.rows, counts.supported_rows, counts.unsupported_rows) == (
        2,
        1,
        1,
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_review_guarded_household_input_error_does_not_advance_guards(reverse):
    month = g.YearMonth(2026, 1)
    child = g.Beneficiary("c", g.Role.CHILD)
    records = {
        "a_good": g.HouseholdRecord("good", _retired()),
        "z_bad": g.HouseholdRecord("bad", _retired(), [child, child]),
    }
    if reverse:
        records = dict(reversed(list(records.items())))
    guards = {
        key: g.SavingsClauseGuard(
            month,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        for key in records
    }
    with pytest.raises(g.InvalidFamilyInput):
        g.household_month_outcome(
            records, payment_month=month, params=PARAMS, guards=guards
        )
    assert all(guard.next_month == month for guard in guards.values())


@given(st.integers(2000, 2030), st.integers(1, 12), st.booleans())
@settings(deadline=None)
def test_review_guard_aliases_are_input_errors_before_any_advance(
    year, month_number, reverse
):
    """One mutable guard cannot carry two records' independent histories."""
    month = g.YearMonth(year, month_number)
    records = {
        "first": g.HouseholdRecord("a", _retired()),
        "second": g.HouseholdRecord("b", _retired()),
    }
    if reverse:
        records = dict(reversed(list(records.items())))
    shared = g.SavingsClauseGuard(
        month,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    with pytest.raises(g.InvalidFamilyInput):
        g.household_month_outcome(
            records,
            payment_month=month,
            params=PARAMS,
            guards={key: shared for key in records},
        )
    assert shared.next_month == month
    assert shared.protected_total is None
    assert shared.refused_since is None
    assert shared.unknown_since is None
    child = g.Beneficiary("c", g.Role.CHILD)
    records["second"] = g.HouseholdRecord("b", _retired(), [child, child])
    distinct_guards = {
        key: g.SavingsClauseGuard(
            month,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        for key in records
    }
    with pytest.raises(g.InvalidFamilyInput):
        g.household_month_outcome(
            records, payment_month=month, params=PARAMS, guards=distinct_guards
        )
    for guard in distinct_guards.values():
        assert guard.next_month == month
        assert guard.protected_total is None
        assert guard.refused_since is None
        assert guard.unknown_since is None
