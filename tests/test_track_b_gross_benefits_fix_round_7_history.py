"""Historical own-RIB reductions require their missing money history.

Verification class: statutory conformance. Invented cases only; no
population, behavioral or forecast claim. The capture establishes a
history requirement, not a replacement historical dollar amount.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
REASON = "own_rib_history_before_1978"
ENTRIES = ("family", "household", "household-month-outcome")


def _case(cohort=1912, months=1, *, own_pia=F(1000), placement="own"):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(2000),
        F(3000),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(2000)),
    )
    member = g.Beneficiary(
        "spouse",
        g.Role.SPOUSE,
        birth_year=cohort if placement == "beneficiary" else None,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            own_pia,
            reduction_months=months,
            birth_year=cohort if placement == "own" else None,
        ),
        own_benefit_first=True,
    )
    return state, member


def _outcome(state, member, entry, *, weight=F(7, 3)):
    records = {"record": g.HouseholdRecord("worker", state, (member,))}
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
                [member],
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
@pytest.mark.parametrize("placement", ("own", "beneficiary"))
def test_review_1912_rf1_own_rib_requires_history(entry, placement):
    state, member = _case(placement=placement)
    outcome = _outcome(state, member, entry)
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight) == (1, F(7, 3))
    assert (counts.unsupported_rows, counts.unsupported_weight) == (
        1,
        F(7, 3),
    )
    assert counts.unsupported_by_reason == {
        outcome.unsupported.reason: (1, F(7, 3))
    }
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_record_total([outcome])


@pytest.mark.parametrize("entry", ("worker", "own"))
def test_review_1912_rf1_primitive_requires_history(entry):
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        if entry == "worker":
            g.worker_age_adjusted(F(1000), 1, 0, 1912, PARAMS)
        else:
            g.own_monthly_benefit(_case()[1].own_benefit, PARAMS)
    assert caught.value.reason.value == REASON


@pytest.mark.parametrize("entry", ENTRIES)
@settings(max_examples=60, deadline=None)
@example(cohort=1912, months=37)
@given(cohort=st.integers(1900, 1915), months=st.integers(37, 60))
def test_history_refusal_follows_all_family_input_errors(
    entry, cohort, months
):
    state, member = _case(cohort)
    member = replace(member, reduction_months=months)
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _outcome(state, member, entry)


@pytest.mark.parametrize("months,credits", ((37, 0), (1, 85)))
def test_historical_primitive_invalid_months_precede_refusal(months, credits):
    with pytest.raises(g.InvalidFamilyInput):
        g.worker_age_adjusted(F(1000), months, credits, 1912, PARAMS)


@pytest.mark.parametrize("cohort", (1916, 1917, 1935))
def test_post_1977_own_rib_control_preserves_exact_amount(cohort):
    state, member = _case(cohort)
    outcome = _outcome(state, member, "family")
    assert outcome.supported
    assert outcome.benefits.by_id()["spouse"].own_benefit == F("994.40")
    assert g.worker_age_adjusted(F(1000), 1, 0, cohort, PARAMS) == (
        F("994.40"),
        F("994.40"),
    )


@pytest.mark.parametrize("months,own_pia", ((0, F(1000)), (1, F(0))))
def test_historical_cohort_with_no_money_reduction_is_supported(
    months, own_pia
):
    state, member = _case(months=months, own_pia=own_pia)
    outcome = _outcome(state, member, "family")
    assert outcome.supported
    assert outcome.benefits.by_id()["spouse"].own_benefit == own_pia


def test_undated_own_rib_retains_current_formula_domain():
    # This amount is the current formula, not a validated historical award.
    state, member = _case(cohort=None)
    outcome = _outcome(state, member, "family")
    assert outcome.supported
    assert outcome.benefits.by_id()["spouse"].own_benefit == F("994.40")


def test_historical_cohort_unreduced_dib_remains_supported():
    state, member = _case(months=0)
    member = replace(
        member,
        own_benefit=replace(
            member.own_benefit, kind=g.OwnBenefitKind.DISABILITY
        ),
    )
    outcome = _outcome(state, member, "family")
    assert outcome.supported
    assert outcome.benefits.by_id()["spouse"].own_benefit == F(1000)


def test_historical_own_rib_rule_is_quoted_from_capture():
    text = source_text("poms_rs_00615_005")
    for quote in (
        "Initial Entitlement 1/78 or Later",
        "Subsequent higher PIAs or unreduced amounts (adjusted for family "
        "maximum if necessary) are reduced by the original reduction "
        "factor (ORF).",
        "Initial Entitlement Before 1/78",
        "(NPIA or NUR) x CMAR = NMAR (CPIA or CUR)",
        "The new money amount of reduction is subtracted from the new PIA "
        "or the new unreduced rate to obtain the new monthly benefit "
        "amount.",
    ):
        assert quote in text


@settings(max_examples=60, deadline=None)
@given(
    cohort=st.integers(1900, 1915),
    months=st.integers(1, 36),
    dimes=st.integers(1, 50_000),
    weight=st.integers(1, 100).map(lambda value: F(value, 3)),
    entry=st.sampled_from(ENTRIES),
    placement=st.sampled_from(("own", "beneficiary")),
)
def test_property_historical_reduction_refusal_preserves_denominators(
    cohort, months, dimes, weight, entry, placement
):
    state, member = _case(
        cohort, months, own_pia=F(dimes, 10), placement=placement
    )
    outcome = _outcome(state, member, entry, weight=weight)
    assert not outcome.supported
    assert outcome.unsupported.reason.value == REASON
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == weight
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_record_total([outcome])


@settings(max_examples=50, deadline=None)
@given(
    cohort=st.integers(1916, 1937),
    months=st.integers(1, 36),
    dimes=st.integers(1, 50_000),
)
def test_property_1978_boundary_preserves_post_1977_formula(
    cohort, months, dimes
):
    pia = F(dimes, 10)
    expected = g.floor_dime(pia * F(180 - months, 180))
    assert g.worker_age_adjusted(pia, months, 0, cohort, PARAMS) == (
        expected,
        expected,
    )


@settings(max_examples=50, deadline=None)
@given(
    cohort=st.integers(1900, 1915),
    dimes=st.integers(0, 50_000),
    months=st.integers(0, 36),
)
def test_property_zero_pia_or_zero_reduction_needs_no_history(
    cohort, dimes, months
):
    pia = F(dimes, 10)
    assert g.worker_age_adjusted(pia, 0, 0, cohort, PARAMS) == (pia, pia)
    assert g.worker_age_adjusted(F(0), months, 0, cohort, PARAMS) == (0, 0)
