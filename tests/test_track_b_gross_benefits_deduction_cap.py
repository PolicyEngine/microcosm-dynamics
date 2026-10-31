"""Statutory conformance: positive own-work events on invented records.

GN 02603.050A caps deduction-before-reduction rates at OB. Invalid events
precede coverage refusals and never enter the shared denominator. No
population, behavioral or forecast claim.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params
from tests.track_b_ret_ledger_support import source_text

PARAMS = ssa_params()
MONTH = g.YearMonth(2024, 1)


def compute(
    *,
    household=False,
    combined=False,
    pia=F(4),
    reservation=F(0),
    payable=None,
    role=g.Role.CHILD,
    reason=g.DeductionReason.OWN_EARNINGS_TEST,
    permanent=True,
    member=None,
    held=True,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        pia * F(3, 2),
        widow_drc_savings_clause=False,
        conditions=(
            {g.RecordCondition.ADMINISTRATIVE_FINALITY}
            if held and not combined
            else set()
        ),
    )
    member = member or g.Beneficiary("C", role)
    if combined:
        member = replace(
            member,
            conditions={g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD},
        )
    upper = g.original_benefit(
        member.role, state.kind, pia, member.original_benefit_basis
    )
    if payable is None:
        payable = upper - reservation
    kwargs = dict(
        payment_month=MONTH,
        params=PARAMS,
        deductions={"C": g.BenefitDeduction(reason, payable, permanent)},
        households={"C": "home"},
        worker_deductions={"C": reservation},
    )
    if household:
        return g.household_benefits_after_deductions(
            {"r": g.HouseholdRecord("nh", state, (member,))}, **kwargs
        )
    return g.family_benefits_after_deductions(
        state, (member,), standalone=True, **kwargs
    )


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("combined", (False, True))
@pytest.mark.parametrize("reservation", (F(0), F(1)))
@pytest.mark.parametrize("permanent", (False, True))
def test_own_event_at_ob_cap_errors_before_coverage_and_has_no_row(
    household, combined, reservation, permanent
):
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match="positive"):
        outcomes.append(
            g.evaluate_family(
                "zero cap",
                7,
                lambda: compute(
                    household=household,
                    combined=combined,
                    reservation=reservation,
                    permanent=permanent,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("combined", (False, True))
@settings(max_examples=20, deadline=None)
@given(
    pia=st.integers(0, 100),
    role=st.sampled_from((g.Role.CHILD, g.Role.PARENT, g.Role.WIDOW)),
    reserved_fraction=st.fractions(min_value=0, max_value=1),
)
def test_upper_bound_equality_is_invalid_for_every_exact_reservation(
    household, combined, pia, role, reserved_fraction
):
    upper = g.original_benefit(role, g.FamilyKind.SURVIVOR, F(pia))
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match="positive"):
        outcomes.append(
            g.evaluate_family(
                "exact cap",
                7,
                lambda: compute(
                    household=household,
                    combined=combined,
                    pia=F(pia),
                    role=role,
                    reservation=upper * reserved_fraction,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("household", (False, True))
def test_zero_pia_maximum_and_ob_cannot_hide_own_event(household):
    with pytest.raises(g.InvalidFamilyInput, match="positive"):
        compute(household=household, pia=F(0))


@pytest.mark.parametrize("household", (False, True))
def test_parent_bound_preserves_legitimate_rate_above_two_parent_ob(household):
    result = compute(
        household=household,
        role=g.Role.PARENT,
        payable=F(3),
        held=False,
    )
    family = result.records["r"] if household else result
    row = family.by_id()["C"]
    assert row.original_benefit == F("3.30")
    assert row.auxiliary_payable == F(3)
    assert row.deduction == F(".30")


@pytest.mark.parametrize("household", (False, True))
def test_widow_larger_original_basis_preserves_positive_event(household):
    result = compute(
        household=household,
        member=g.Beneficiary("C", g.Role.WIDOW, original_benefit_basis=F(5)),
        payable=F(4),
        held=False,
    )
    family = result.records["r"] if household else result
    row = family.by_id()["C"]
    assert row.original_benefit == F(5)
    assert row.auxiliary_payable == F(4)
    assert row.deduction == F(1)


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize(
    "reason",
    (
        g.DeductionReason.DUAL_ENTITLEMENT,
        g.DeductionReason.PRISONER_SUSPENSION,
    ),
)
def test_other_event_equality_keeps_existing_named_refusal(household, reason):
    member = g.Beneficiary(
        "C",
        g.Role.CHILD,
        own_benefit=(
            g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(0))
            if reason is g.DeductionReason.DUAL_ENTITLEMENT
            else None
        ),
    )
    outcome = g.evaluate_family(
        "other event",
        7,
        lambda: compute(household=household, reason=reason, member=member),
    )
    assert (
        outcome.unsupported.reason
        is g.UnsupportedReason.ADMINISTRATIVE_FINALITY
    )
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.unsupported_weight == F(7)


@pytest.mark.parametrize("household", (False, True))
def test_dual_marker_at_original_benefit_stays_supported(household):
    result = compute(
        household=household,
        reason=g.DeductionReason.DUAL_ENTITLEMENT,
        member=g.Beneficiary(
            "C",
            g.Role.CHILD,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(0)),
        ),
        held=False,
    )
    family = result.records["r"] if household else result
    assert family.by_id()["C"].auxiliary_payable == F(3)
    assert family.by_id()["C"].deduction == 0


def test_original_benefit_cap_rule_is_quoted_from_capture():
    assert (
        "In all cases, beneficiaries are still limited to the original "
        "benefit amount."
    ) in source_text("poms_gn_02603_050")
