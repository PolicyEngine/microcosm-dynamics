"""Round 8: the PIA as a RIB's cap, zero thresholds and the first reduced DIB.

Every record is invented or built from a captured SSA rule. Nothing here
admits a population, behavioral or forecast claim.
"""

from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_ret_ledger_fix_round_7 import (
    AGE_FREE_HOLDS,
    AMOUNT_TEST_ROLES,
    DUAL,
    OWN_HISTORY,
    PRE_1978_REASONS,
    PRIOR_REDUCED_HOLDS,
    RC,
    REDUCED_HISTORY,
    UR,
    _assert_invalid,
    _assert_preflight_neutral,
    _assert_refusal,
    _deferred,
    _dib_record,
    _f6_settled,
    _mother_record,
    _rib_record,
)
from tests.track_b_gross_benefit_support import source_text, ssa_params

ENTITLEMENT = "auxiliary entitlement facts differ"
BC = g.BeneficiaryCondition
HOLDS_PLUS_NONE = (None, OWN_HISTORY, REDUCED_HISTORY, DUAL)
# Each row: cohort, payment year, payment month, whether a reduced benefit
# could precede that month. RS 00615.005A.1-A.4 date the routes, and the
# route each row turns on sits in its comment.
ROUTE_ROWS = (
    # No reduced DIB exists before A.3's 9/65, on any route.
    (1900, 1965, 8, False),
    (None, 1965, 8, False),
    (1908, 1958, 2, False),
    # A.1: a RIB at 62 from 11/56. Its first month need only come first.
    (1903, 1965, 9, True),
    (None, 1965, 9, True),
    (1904, 1965, 9, False),
    # A.3: a WIB at 60 from 9/65, one month before the DIB.
    (1904, 1965, 10, True),
    (1905, 1965, 10, True),
    (1907, 1967, 1, False),
    (1907, 1967, 2, True),
    (1908, 1968, 1, False),
    (1908, 1968, 2, True),
    # A.4: a disabled WIB at 50 from 2/68, one month before the DIB.
    (1916, 1966, 2, False),
    (1918, 1968, 2, False),
    (1918, 1968, 3, True),
    (1910, 1968, 2, False),
    (1910, 1968, 3, True),
    (1974, 2024, 1, False),
    (1974, 2024, 2, True),
    (None, 2024, 1, True),
)


def _first_month_dib(pia, gross, birth, year, month, *, maximum=None, **holds):
    return _dib_record(
        pia,
        gross,
        birth=birth,
        year=year,
        month=month,
        maximum=maximum,
        first=g.YearMonth(year, month),
        **holds,
    )


def test_the_captures_carry_each_quoted_rule():
    reduced = source_text("poms_rs_00615_005")
    for quote in (
        "1956 Amendments Effective 11/56",
        "1965 Amendments Effective 9/65",
        "Allowed entitlement to reduced DIB after entitlement to reduced "
        "RIB or reduced WIB.",
        "1967 Amendments Effective 2/68",
        "The new money amount of reduction is subtracted from the new PIA",
    ):
        assert quote in reduced
    assert (
        "months of WIB entitlement before the first MOET to DIB."
        in source_text("poms_rs_00615_010")
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize("cohort", [None, 1900, 1915])
@pytest.mark.parametrize(
    "pia,gross,months",
    [("333.30", "333.40", 8), ("1000", "1000.10", 2), ("0.10", "0.20", 1)],
)
def test_history_leaves_a_rib_at_or_below_its_pia(
    reason, cohort, pia, gross, months
):
    _assert_invalid(
        _rib_record(
            F(pia), F(gross), reason=reason, cohort=cohort, months=months
        )
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
@pytest.mark.parametrize("cohort", [None, 1915])
def test_a_rate_at_the_pia_keeps_its_history_row(reason, cohort):
    pia = F("333.30")
    case = _rib_record(pia, pia, reason=reason, cohort=cohort)
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("cohort", [1900, 1915])
def test_a_known_cohort_keeps_the_pia_cap_with_no_declaration(cohort):
    pia = F("333.30")
    _assert_invalid(_rib_record(pia, pia + F(1, 10), cohort=cohort))
    _assert_refusal(_rib_record(pia, pia, cohort=cohort), OWN_HISTORY)


@pytest.mark.parametrize(
    "conditions,reason",
    [
        ({RC.WORKERS_COMPENSATION_OFFSET}, None),
        ((), UR.WORKERS_COMPENSATION_OFFSET),
        ((), DUAL),
        ((), UR.DELAYED_CREDITS_BEFORE_1917),
    ],
)
def test_no_other_hold_lifts_a_known_cohort_past_the_pia(conditions, reason):
    pia = F("333.30")
    _assert_invalid(
        _rib_record(
            pia,
            pia + F(1, 10),
            conditions=conditions,
            reason=reason,
            cohort=1915,
        )
    )


@pytest.mark.parametrize("reason", (None,) + PRE_1978_REASONS)
@pytest.mark.parametrize("cohort", [None, 1915])
def test_finality_can_lift_a_rib_past_its_pia(reason, cohort):
    pia = F("333.30")
    case = _rib_record(
        pia,
        pia + F(1, 10),
        conditions={RC.ADMINISTRATIVE_FINALITY},
        reason=reason,
        cohort=cohort,
    )
    _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("cohort", [None, 1915])
def test_a_deferred_finality_can_lift_a_rib_past_its_pia(cohort):
    pia = F("333.30")
    _assert_refusal(
        _rib_record(
            pia,
            pia + F(1, 10),
            reason=UR.ADMINISTRATIVE_FINALITY,
            cohort=cohort,
        ),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_delayed_credits_can_lift_a_history_rib_past_its_pia(reason):
    pia = F("333.30")
    case = _rib_record(
        pia, pia + F(1, 10), reason=reason, cohort=1915, credits=12
    )
    _assert_refusal(case, reason)
    _assert_preflight_neutral(case)


def test_a_month_before_1983_leaves_the_rate_unsettled_past_the_pia():
    pia = F("333.30")
    case = _rib_record(
        pia, pia + F(1, 10), reason=OWN_HISTORY, cohort=1915, year=1982
    )
    _assert_refusal(case, OWN_HISTORY)


@given(
    pia=st.integers(1, 30_000).map(lambda n: F(n, 10)),
    months=st.integers(1, 36),
    cohort=st.sampled_from((None, 1900, 1913, 1915)),
    reason=st.sampled_from(PRE_1978_REASONS + (None,)),
    gap=st.integers(1, 40).map(lambda n: F(n, 10)),
)
@example(
    pia=F("0.10"), months=1, cohort=None, reason=OWN_HISTORY, gap=F(1, 10)
)
@settings(max_examples=150, deadline=None)
def test_no_history_admits_a_rib_above_its_pia(
    pia, months, cohort, reason, gap
):
    case = _rib_record(
        pia, pia + gap, reason=reason, cohort=cohort, months=months
    )
    _assert_invalid(case)


@pytest.mark.parametrize("reason", HOLDS_PLUS_NONE)
@pytest.mark.parametrize("cohort", [1900, 1915])
@pytest.mark.parametrize("own,months", [("0.10", 1), ("400", 12)])
def test_a_zero_pia_fails_a_known_cohorts_rib(reason, cohort, own, months):
    _assert_invalid(
        _mother_record(
            reason,
            cohort=cohort,
            pia=F(0),
            own=F(own),
            months=months,
            gross=F(0),
        ),
        ENTITLEMENT,
    )


@pytest.mark.parametrize("reason", (None, UR.DELAYED_CREDITS_BEFORE_1917))
def test_a_zero_pia_fails_a_rib_with_early_credits(reason):
    _assert_invalid(
        _mother_record(
            reason, cohort=1915, pia=F(0), months=0, credits=12, gross=F(0)
        ),
        ENTITLEMENT,
    )


@pytest.mark.parametrize("reason", (None, OWN_HISTORY))
@pytest.mark.parametrize("pia", ["0.10", "480"])
def test_a_positive_threshold_keeps_the_own_history_row(reason, pia):
    case = _mother_record(
        reason, cohort=1915, pia=F(pia), own=F("0.10"), months=1, gross=F(0)
    )
    _assert_refusal(case, OWN_HISTORY)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("pia", ["0.10", "480"])
def test_early_credits_keep_their_row_on_a_positive_threshold(pia):
    case = _mother_record(
        None,
        cohort=1915,
        pia=F(pia),
        own=F("0.10"),
        months=0,
        credits=12,
        gross=F(0),
    )
    _assert_refusal(case, UR.DELAYED_CREDITS_BEFORE_1917)


@pytest.mark.parametrize(
    "holds,named",
    [
        (
            {"conditions": {RC.ADMINISTRATIVE_FINALITY}},
            UR.ADMINISTRATIVE_FINALITY,
        ),
        ({"member_conditions": {BC.RATE_PROTECTED_BY_FINALITY}}, OWN_HISTORY),
    ],
)
def test_finality_keeps_a_zero_threshold_row(holds, named):
    case = _mother_record(
        None,
        cohort=1915,
        pia=F(0),
        own=F("0.10"),
        months=1,
        gross=F(0),
        **holds,
    )
    _assert_refusal(case, named)


def test_a_deferred_finality_keeps_a_zero_threshold_row():
    case = _mother_record(
        UR.ADMINISTRATIVE_FINALITY,
        cohort=1915,
        pia=F(0),
        own=F("0.10"),
        months=1,
        gross=F(0),
    )
    _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)


@pytest.mark.parametrize("role", AMOUNT_TEST_ROLES)
@pytest.mark.parametrize("reason", (None, OWN_HISTORY))
def test_a_zero_threshold_settles_every_actual_rib_test(role, reason):
    assert _f6_settled(role, reason, 1915, pia=F(0), months=1) is True
    assert _f6_settled(role, reason, 1915, pia=F("0.10"), months=1) is False


@pytest.mark.parametrize("role", AMOUNT_TEST_ROLES)
def test_only_a_zero_threshold_settles_a_rib_with_early_credits(role):
    def settled(pia):
        return _f6_settled(
            role,
            UR.DELAYED_CREDITS_BEFORE_1917,
            1915,
            pia=pia,
            months=0,
            credits=12,
        )

    assert settled(F(0)) is True
    assert settled(F("0.10")) is False


def test_a_deemed_pia_keeps_a_known_cohorts_history_open():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(0),
        F(0),
        eligibility_year=1990,
        widow_drc_savings_clause=False,
    )
    member = g.Beneficiary(
        "w",
        g.Role.DISABLED_WIDOW,
        birth_year=1915,
        original_benefit_basis=F(100),
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(400),
            reduction_months=12,
            birth_year=1915,
        ),
    )
    assert not g._fact_is_settled(
        "F6",
        state,
        member,
        payment_month=g.YearMonth(2000, 1),
        beneficiaries=(member,),
        params=ssa_params(),
    )


@given(
    pia=st.integers(0, 30_000).map(lambda n: F(n, 10)),
    own=st.integers(1, 30_000).map(lambda n: F(n, 10)),
    months=st.integers(1, 36),
    cohort=st.integers(1900, 1915),
    reason=st.sampled_from(HOLDS_PLUS_NONE),
)
@example(pia=F(0), own=F("0.10"), months=1, cohort=1915, reason=None)
@example(pia=F("0.10"), own=F("0.10"), months=1, cohort=1915, reason=None)
@settings(max_examples=120, deadline=None)
def test_only_a_zero_threshold_rules_out_a_history_rib(
    pia, own, months, cohort, reason
):
    case = _mother_record(
        reason, cohort=cohort, pia=pia, own=own, months=months, gross=F(0)
    )
    if pia == 0:
        _assert_invalid(case, ENTITLEMENT)
    else:
        _assert_refusal(case, reason or OWN_HISTORY)


@pytest.mark.parametrize("birth,year,month,possible", ROUTE_ROWS)
def test_each_route_dates_the_first_reduced_dib(birth, year, month, possible):
    assert (
        g._prior_reduced_benefit_possible(birth, g.YearMonth(year, month))
        is possible
    )


def test_an_unknown_month_leaves_every_route_open():
    assert g._prior_reduced_benefit_possible(1990, None) is True
    assert g._prior_reduced_benefit_possible(None, None) is True


@given(
    birth=st.one_of(st.none(), st.integers(1880, 2005)),
    year=st.integers(1955, 2060),
    month=st.integers(1, 12),
)
@example(birth=1974, year=2024, month=1)
@example(birth=1903, year=1965, month=9)
@example(birth=1905, year=1965, month=10)
@settings(max_examples=400, deadline=None)
def test_the_floor_matches_month_counts_written_from_the_sources(
    birth, year, month
):
    payment = year * 12 + month
    if payment < 1965 * 12 + 9:
        expected = False
    elif birth is None:
        expected = True
    else:
        rib = max(1956 * 12 + 11, (birth + 62) * 12 + 1)
        widow = max(1965 * 12 + 9, (birth + 60) * 12 + 1)
        disabled_widow = max(1968 * 12 + 2, (birth + 50) * 12 + 1)
        expected = min(rib, widow, disabled_widow) < payment
    assert (
        g._prior_reduced_benefit_possible(birth, g.YearMonth(year, month))
        is expected
    )


@pytest.mark.parametrize("conditions,reason,named", PRIOR_REDUCED_HOLDS)
@pytest.mark.parametrize(
    "pia,gross", [(F(405), F("404.90")), (F("0.10"), F(0))]
)
def test_a_modern_january_of_cohort_plus_50_has_one_dib_rate(
    conditions, reason, named, pia, gross
):
    holds = {"conditions": conditions, "reason": reason, "maximum": pia}
    _assert_invalid(_first_month_dib(pia, gross, 1974, 2024, 1, **holds))
    _assert_refusal(_first_month_dib(pia, pia, 1974, 2024, 1, **holds), named)
    case = _first_month_dib(pia, gross, 1974, 2024, 2, **holds)
    _assert_refusal(case, named)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("conditions,reason,named", PRIOR_REDUCED_HOLDS)
@pytest.mark.parametrize(
    "birth,year", [(1908, 1958), (1916, 1966), (1918, 1968)]
)
@pytest.mark.parametrize(
    "pia,gross", [(F(100), F("99.90")), (F("0.10"), F(0))]
)
def test_before_a_route_exists_a_dib_rate_equals_its_pia_or_raises(
    conditions, reason, named, birth, year, pia, gross
):
    holds = {"conditions": conditions, "reason": reason}
    _assert_invalid(_first_month_dib(pia, gross, birth, year, 2, **holds))
    case = _first_month_dib(pia, pia, birth, year, 2, **holds)
    _assert_refusal(case, UR.ELIGIBILITY_BEFORE_1983)


@pytest.mark.parametrize("conditions,reason,named", PRIOR_REDUCED_HOLDS)
def test_a_historical_route_keeps_its_row_once_it_opens(
    conditions, reason, named
):
    case = _first_month_dib(
        F(100), F("99.90"), 1918, 1968, 3, conditions=conditions, reason=reason
    )
    _assert_refusal(case, UR.ELIGIBILITY_BEFORE_1983)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("conditions,reason,named", AGE_FREE_HOLDS)
@pytest.mark.parametrize(
    "birth,year", [(1908, 1958), (1918, 1968), (1974, 2024)]
)
def test_a_hold_that_needs_no_predecessor_keeps_its_row(
    conditions, reason, named, birth, year
):
    case = _first_month_dib(
        F(100),
        F("99.90"),
        birth,
        year,
        1,
        conditions=conditions,
        reason=reason,
    )
    outcome_reason = UR.ELIGIBILITY_BEFORE_1983 if year < 1983 else named
    _assert_refusal(case, outcome_reason)
    _assert_preflight_neutral(case)


@pytest.mark.parametrize("reason", PRE_1978_REASONS)
def test_a_pre_1978_hold_shares_the_first_route(reason):
    assert (
        g._fact_is_settled(
            "F2",
            g.RecordState(
                g.FamilyKind.DISABILITY,
                F(100),
                F(150),
                worker_birth_year=1918,
                eligibility_year=1968,
                first_dib_entitlement=g.YearMonth(1968, 2),
                deferred_refusal=_deferred(reason),
            ),
            payment_month=g.YearMonth(1968, 2),
            params=ssa_params(),
        )
        is True
    )
