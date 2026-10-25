"""Missing pre-1978 reduction histories across every reduced role.

Verification class: statutory conformance. Invented families only; no
population, behavioral, or forecast claim. Historical rates are refused,
not imputed from present reduction months.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
REASON = "reduced_benefit_history_before_1978"
ROLES = (
    g.Role.SPOUSE,
    g.Role.DIVORCED_SPOUSE,
    g.Role.WIDOW,
    g.Role.SURVIVING_DIVORCED_SPOUSE,
    g.Role.DISABLED_WIDOW,
)
ENTRIES = ("family", "household", "household-month-outcome")


def _case(role, cohort=1912, months=1, pia=F(1000)):
    spouse = role in (g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE)
    state = g.RecordState(
        g.FamilyKind.RETIREMENT if spouse else g.FamilyKind.SURVIVOR,
        pia,
        g.floor_dime(pia * F(3, 2)),
        worker=(
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia) if spouse else None
        ),
        widow_drc_savings_clause=False,
    )
    member = g.Beneficiary(
        "member",
        role,
        birth_year=cohort,
        reduction_months=0 if role is g.Role.DISABLED_WIDOW else months,
        reduction_period_months=(
            60 if not spouse and role is not g.Role.DISABLED_WIDOW else None
        ),
        child_in_care=False if role is not g.Role.SPOUSE else None,
        first_entitlement_child_in_care=(
            False if role is g.Role.DIVORCED_SPOUSE else None
        ),
    )
    return state, member


def _outcome(state, members, entry, weight=F(7, 3)):
    records = {"record": g.HouseholdRecord("worker", state, tuple(members))}
    if entry == "household-month-outcome":
        guard = g.SavingsClauseGuard(NOW, earlier_months_unknown=False)
        try:
            outcome = g.household_month_outcome(
                records,
                payment_month=NOW,
                params=PARAMS,
                guards={"record": guard},
                weight=weight,
            )
        except g.InvalidFamilyInput:
            assert guard.next_month == NOW
            raise
        assert guard.next_month == g.YearMonth(2024, 1)
        return outcome
    return g.evaluate_family(
        "case",
        weight,
        lambda: (
            g.family_benefits(
                state,
                members,
                payment_month=NOW,
                params=PARAMS,
                standalone=True,
            )
            if entry == "family"
            else g.household_benefits(
                records, payment_month=NOW, params=PARAMS
            )
        ),
    )


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("role", (g.Role.SPOUSE, g.Role.WIDOW))
def test_review_1912_rf1_auxiliary_requires_money_history(role, entry):
    state, member = _case(role)
    outcome = _outcome(state, [member], entry)
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON
    assert outcome.unsupported.beneficiary_id == "member"
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(7, 3)
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_record_total([outcome])


@pytest.mark.parametrize("role", ROLES)
@settings(max_examples=70, deadline=None)
@given(
    cohort=st.integers(1900, 1937),
    months=st.integers(0, 36),
    dollars=st.integers(0, 10_000),
    entry=st.sampled_from(ENTRIES),
    weight=st.integers(1, 100).map(lambda value: F(value, 3)),
)
def test_property_history_refusal_exactly_tracks_role_cohort_and_amount(
    role, cohort, months, dollars, entry, weight
):
    """For a single, unclipped award, the absent history matters iff below.

    This domain has no own offset, care minimum or RIB-LIM. It does not
    claim every endpoint in a conservative interval is reachable for a
    more constrained award.
    """
    state, member = _case(role, cohort, months, F(dollars * 2))
    outcome = _outcome(state, [member], entry, weight)
    first_age = 62 if role in (g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE) else 50
    expected = (
        cohort + first_age < 1978
        and dollars > 0
        and (months > 0 or role is g.Role.DISABLED_WIDOW)
    )
    assert outcome.supported is not expected
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == 1
    assert counts.weight == weight
    if expected:
        assert outcome.unsupported.reason.value == REASON
        assert counts.unsupported_rows == 1
        assert counts.unsupported_weight == weight
        with pytest.raises(g.FamilyTargetBlocked):
            g.weighted_record_total([outcome])


@pytest.mark.parametrize(
    "role,boundary,expected",
    (
        (g.Role.SPOUSE, 1916, F("496.50")),
        (g.Role.DIVORCED_SPOUSE, 1916, F("496.50")),
        (g.Role.WIDOW, 1928, F("995.20")),
        (g.Role.SURVIVING_DIVORCED_SPOUSE, 1928, F("995.20")),
        (g.Role.DISABLED_WIDOW, 1928, F(715)),
    ),
)
def test_role_specific_1978_boundary_is_not_rounded_to_own_rib_boundary(
    role, boundary, expected
):
    state, member = _case(role, boundary - 1)
    before = _outcome(state, [member], "family")
    assert not before.supported
    assert before.unsupported.reason.value == REASON
    for cohort in (boundary, None):
        after = _outcome(state, [replace(member, birth_year=cohort)], "family")
        assert after.supported
        assert after.benefits.by_id()["member"].auxiliary_payable == expected


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("entry", ENTRIES)
@settings(max_examples=20, deadline=None)
@given(cohort=st.integers(1900, 1915), bad_rf=st.integers(37, 60))
def test_property_invalid_family_member_precedes_every_history_refusal(
    role, entry, cohort, bad_rf
):
    state, member = _case(role, cohort)
    invalid = g.Beneficiary(
        "invalid",
        g.Role.SPOUSE,
        birth_year=1912,
        reduction_months=bad_rf,
        conditions=frozenset(
            {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
        ),
    )
    # On survivor records the wrong role is already an input error; on
    # retirement records the historical cohort's RF limit is an error.
    for members in ([member, invalid], [invalid, member]):
        with pytest.raises(g.InvalidFamilyInput):
            _outcome(state, members, entry)


@pytest.mark.parametrize("entry", ENTRIES)
@settings(max_examples=30, deadline=None)
@given(cohort=st.integers(1900, 1915), months=st.integers(1, 36))
def test_property_zero_spousal_excess_survives_parisi_redistribution(
    entry, cohort, months
):
    state, spouse = _case(g.Role.SPOUSE, cohort, months)
    spouse = replace(
        spouse,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
        own_benefit_first=True,
    )
    child = g.Beneficiary("child", g.Role.CHILD)
    outcome = _outcome(state, [spouse, child], entry)
    assert outcome.supported
    result = outcome.benefits
    if entry != "family":
        result = result.records["record"]
    assert result.by_id()["member"].auxiliary_payable == 0
    assert result.by_id()["member"].age_adjusted_rate == 250
    assert result.by_id()["child"].auxiliary_payable == 500
    assert result.redistribution_applied


@pytest.mark.parametrize("entry", ENTRIES)
def test_settled_subject_payable_does_not_fabricate_savings_clause_rate(entry):
    state, spouse = _case(g.Role.SPOUSE)
    spouse = replace(
        spouse,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
        own_benefit_first=False,
    )
    outcome = _outcome(
        state, [spouse, g.Beneficiary("child", g.Role.CHILD)], entry
    )
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON


@settings(max_examples=40, deadline=None)
@given(
    cohort=st.integers(1900, 1915),
    months=st.integers(1, 36),
    entry=st.sampled_from(ENTRIES),
)
def test_property_current_divorced_care_exemption_settles_historical_rate(
    cohort, months, entry
):
    state, spouse = _case(g.Role.DIVORCED_SPOUSE, cohort, months)
    spouse = replace(spouse, child_in_care="child")
    outcome = _outcome(
        state, [spouse, g.Beneficiary("child", g.Role.CHILD)], entry
    )
    assert outcome.supported
    result = outcome.benefits
    if entry != "family":
        result = result.records["record"]
    assert result.by_id()["member"].auxiliary_payable == 500


@pytest.mark.parametrize("role", (g.Role.WIDOW, g.Role.DISABLED_WIDOW))
def test_current_formula_zero_from_rounding_does_not_prove_history_zero(role):
    state, member = _case(role, pia=F(1, 10))
    outcome = _outcome(state, [member], "family")
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON


@settings(max_examples=40, deadline=None)
@given(
    cohort=st.integers(1900, 1917),
    dimes=st.integers(1, 100_000),
    entry=st.sampled_from(ENTRIES),
)
def test_property_zero_rib_lim_settles_positive_outside_maximum_history(
    cohort, dimes, entry
):
    state, member = _case(g.Role.SURVIVING_DIVORCED_SPOUSE, cohort, pia=F(0))
    state = replace(state, rib_lim_benefit=F(0))
    member = replace(member, original_benefit_basis=F(dimes, 10))
    outcome = _outcome(state, [member], entry)
    assert outcome.supported
    result = outcome.benefits
    if entry != "family":
        result = result.records["record"]
    assert result.by_id()["member"].auxiliary_payable == 0


def test_historical_scope_and_earliest_ages_are_quoted_from_captures():
    history = source_text("poms_rs_00615_005")
    for quote in (
        "all cases involving single entitlement to actuarially reduced "
        "benefits prior to 1/78",
        "Provided for the payment of reduced retirement, reduced spouse's "
        "and unreduced widow's benefits to women at age 62.",
        "Provided for reduced widower's benefits at age 60.",
        "The money amount of reduction in the month before the month in "
        "which a PIA or an original rate increases, is increased by the "
        "percentage increase applicable to the increased PIA and rate.",
    ):
        assert quote in history
    assert (
        "Benefits are payable as early as age 50 to widow(er)s who meet "
        "disability requirements."
    ) in source_text("poms_rs_00615_310")
    assert (
        "Round the MAR up to the next dime for benefits after 5/82 and "
        "down to the next dime for benefits prior to 6/82."
    ) in source_text("poms_rs_00615_301")
    assert (
        "Method C - First benefit calculated independently; reduce excess "
        "of second benefit for age (if larger)."
    ) in source_text("poms_rs_00615_020")
    assert (
        "For initial entitlement to the reduced benefit prior to 1/78, "
        "separately reduce any increases before 1/78 but apply the basic "
        "formula for post 1977 increases in PIAs or spouse's original rate."
    ) in source_text("poms_rs_00615_240")
    # .005C.2 expressly covers single entitlement; the general modern
    # method-C instruction alone does not settle all historical dual
    # interactions. Pin the alternative without imputing missing history.
    state, member = _case(g.Role.SPOUSE)
    member = replace(
        member,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(400)),
        own_benefit_first=True,
    )
    historical = _outcome(state, [member], "family")
    assert not historical.supported
    assert historical.unsupported.reason.value == REASON
    assert g.spouse_age_reduced(F(500) - F(400), 1, PARAMS) == F("99.30")
    modern = _outcome(state, [replace(member, birth_year=1916)], "family")
    assert modern.benefits.by_id()["member"].auxiliary_payable == F("99.30")


@pytest.mark.parametrize(
    "role", (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE)
)
def test_aged_widow_can_carry_pre_1978_dwb_history_after_conversion(role):
    # Cohort 1920 cannot start aged WIB before 1980, but may have DWB from
    # 1970 and carry that earlier award through conversion at FRA.
    state, member = _case(role, cohort=1920)
    outcome = _outcome(state, [member], "family")
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON
    assert (
        "All DWB benefits are converted to reduced aged widow(er)'s "
        "benefits at FRA."
    ) in source_text("poms_rs_00615_310")


def test_historical_dwb_specific_fixed_rate_alternative_is_explicit():
    text = source_text("poms_rs_00615_301")
    assert (
        "all disabled widow(er)s under age 60 receive .715 of the full "
        "unreduced WIB for 1/84 and later."
    ) in text
    state, member = _case(g.Role.DISABLED_WIDOW, cohort=1927)

    # January 1984 keeps both cohorts under 60, matching the specific
    # captured instruction rather than relying on an aged DWB snapshot.
    def at_reset(beneficiary):
        return g.family_benefits(
            state,
            [beneficiary],
            payment_month=g.YearMonth(1984, 1),
            params=PARAMS,
            standalone=True,
        )

    historical = g.evaluate_family("case", F(7, 3), lambda: at_reset(member))
    assert not historical.supported
    assert historical.unsupported.reason.value == REASON
    # Explicit alternative reading of the specific rule, not an imputed
    # historical award in production. Needs Max's judgment against .005C.2.
    assert F(1000) * F(715, 1000) == F(715)
    modern = at_reset(replace(member, birth_year=1928))
    assert modern.by_id()["member"].auxiliary_payable == F(715)


def test_historical_rounding_can_defeat_a_nominal_75_percent_care_floor():
    # Invented scalar history, not a sourced worked example. The captured
    # pre-6/82 MAR rounding plus .005C.2 can carry a zero money reduction.
    historical_unreduced = F(1, 10)
    historical_mar = g.floor_dime(historical_unreduced * F(285, 1000))
    new_unreduced = F(1000)
    new_mar = new_unreduced * historical_mar / historical_unreduced
    assert historical_mar == new_mar == 0
    assert new_unreduced - new_mar == F(1000)
    assert g.survivor_age_reduced(F(1000), 60, 60, PARAMS) == F(715)
    assert max(F(750), F(715)) != max(F(750), new_unreduced - new_mar)
    state, member = _case(g.Role.DISABLED_WIDOW)
    member = replace(member, child_in_care="child")
    state = replace(state, family_maximum=F(2000))
    outcome = _outcome(
        state, [member, g.Beneficiary("child", g.Role.CHILD)], "family"
    )
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON
