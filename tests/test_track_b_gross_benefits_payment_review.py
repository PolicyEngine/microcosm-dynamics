"""Payment review regressions on statutory and invented configurations.

Verification class: statutory conformance. This module admits supported
gross-payment mechanics only, with no population or forecast claim.
RS 00615.320A.3 settles when the RIB-LIM applies; RS 00615.740B settles
the disability-maximum entitlement boundary. Invented cases test both.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
MONTH = g.YearMonth(2000, 1)


def _family(state, members, payment_month=MONTH):
    return g.family_benefits(
        state,
        members,
        payment_month=payment_month,
        params=PARAMS,
        standalone=True,
    )


def _widow_and_children(pia=F(1000), reduction_months=0):
    return (
        g.Beneficiary(
            "W",
            g.Role.WIDOW,
            birth_year=1935,
            reduction_months=reduction_months,
            reduction_period_months=60 if reduction_months else None,
            own_benefit=g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE, pia / 5, birth_year=1935
            ),
            child_in_care=False,
        ),
        g.Beneficiary("C1", g.Role.CHILD),
        g.Beneficiary("C2", g.Role.CHILD),
    )


def test_considered_nonlimiting_rib_lim_preserves_parisi_payments():
    """Executed review case: the $825 limit cannot lower the $700 rate."""
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(1000),
        F(1750),
        rib_lim_benefit=F(100),
        widow_drc_savings_clause=False,
    )
    result = _family(state, _widow_and_children())
    assert result.family_maximum_binding
    assert result.by_id()["W"].standard_rate == 700
    assert result.by_id()["W"].auxiliary_payable == 500
    assert result.by_id()["C1"].auxiliary_payable == 625
    assert result.by_id()["C2"].auxiliary_payable == 625
    assert result == _family(
        dataclasses.replace(state, rib_lim_benefit=None),
        _widow_and_children(),
    )


@pytest.mark.parametrize(
    "maximum,reduction_months,widow_payable,child_payable",
    [(F("2062.5"), 0, F(625), F("718.7")), (F(2250), 60, F("443.5"), F(750))],
    ids=["equals-limit", "age-reduction-precedes-limit"],
)
def test_rib_lim_is_nonlimiting_at_equality_or_after_age_reduction(
    maximum, reduction_months, widow_payable, child_payable
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(1000),
        maximum,
        rib_lim_benefit=F(100),
        widow_drc_savings_clause=False,
    )
    members = _widow_and_children(reduction_months=reduction_months)
    result = _family(state, members)
    assert result.by_id()["W"].auxiliary_payable == widow_payable
    assert result.by_id()["C1"].auxiliary_payable == child_payable
    assert result.by_id()["C2"].auxiliary_payable == child_payable
    assert result == _family(
        dataclasses.replace(state, rib_lim_benefit=None), members
    )


def test_limiting_rib_lim_parisi_case_stays_refused_in_denominators():
    """The initial $900 widow rate exceeds both $100 and $825."""
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(1000),
        F(2250),
        rib_lim_benefit=F(100),
        widow_drc_savings_clause=False,
    )
    outcome = g.evaluate_family(
        "limiting", F(7, 3), lambda: _family(state, _widow_and_children())
    )
    assert not outcome.supported
    assert outcome.unsupported.reason is g.UnsupportedReason.PARISI_AMBIGUOUS
    denominator = g.count_family_outcomes([outcome])
    assert denominator.rows == denominator.unsupported_rows == 1
    assert denominator.weight == denominator.unsupported_weight == F(7, 3)
    with pytest.raises(g.FamilyTargetBlocked):
        g.weighted_record_total([outcome])


def test_direct_pre_july_1980_dib_snapshot_is_refused():
    """Executed review case: a known historical date requires refusal."""
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(1000),
        F(1500),
        first_dib_entitlement=g.YearMonth(1980, 6),
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as error:
        _family(
            state,
            [g.Beneficiary("c", g.Role.CHILD)],
            g.YearMonth(2026, 1),
        )
    assert error.value.reason is (
        g.UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980
    )


def test_payment_review_rules_are_quoted_from_the_captures():
    assert (
        "The RIB LIM will apply when the WIB after adjustment for the "
        "family maximum and reduction for age is more than BOTH 82 1/2 "
        "percent of the NH's death PIA and the RIB or DIB if they were alive."
    ) in source_text("poms_rs_00615_320")
    assert (
        "The DMAX does not apply if • The NH was ever entitled to DIB "
        "before July 1980"
    ) in source_text("poms_rs_00615_740")
    assert (
        "An independently entitled divorced spouse (IEDS) is subject to "
        "the number holder's (NH) WEP PIA although the NH is not yet "
        "entitled to Social Security benefits."
    ) in source_text("poms_rs_00202_100")


@settings(max_examples=50, deadline=None, derandomize=True)
@given(
    units=st.integers(1, 100),
    reduction_months=st.integers(0, 60),
    maximum_factor=st.sampled_from((F(7, 4), F(33, 16), F(9, 4))),
)
def test_nonlimiting_rib_lim_has_no_effect_for_every_generated_age_rate(
    units, reduction_months, maximum_factor
):
    """A considered limit below the 82.5% floor changes no G output."""
    pia = F(80 * units)
    if maximum_factor == F(9, 4):
        # The 90% initial widow share falls below 82.5% after 18 RFs.
        reduction_months = max(18, reduction_months)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        pia * maximum_factor,
        widow_drc_savings_clause=False,
    )
    members = _widow_and_children(pia, reduction_months)
    baseline = _family(state, members)
    declared = _family(
        dataclasses.replace(state, rib_lim_benefit=pia / 10), members
    )
    assert declared == baseline
    assert _family(state, tuple(reversed(members))) == dataclasses.replace(
        baseline, beneficiaries=tuple(reversed(baseline.beneficiaries))
    )


@settings(max_examples=30, deadline=None, derandomize=True)
@given(units=st.integers(1, 100), weight=st.integers(1, 20))
def test_limiting_rib_lim_refusal_retains_every_generated_weight(
    units, weight
):
    pia = F(20 * units)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        pia,
        pia * F(9, 4),
        rib_lim_benefit=pia / 10,
        widow_drc_savings_clause=False,
    )
    outcome = g.evaluate_family(
        "limiting",
        F(weight, 3),
        lambda: _family(state, _widow_and_children(pia)),
    )
    assert not outcome.supported
    assert outcome.unsupported.reason is g.UnsupportedReason.PARISI_AMBIGUOUS
    denominator = g.count_family_outcomes([outcome])
    assert denominator.rows == denominator.unsupported_rows == 1
    assert denominator.weight == denominator.unsupported_weight == F(weight, 3)


@settings(max_examples=50, deadline=None, derandomize=True)
@given(month=st.integers(1, 12), units=st.integers(1, 100))
def test_direct_and_built_dib_snapshots_share_the_july_1980_boundary(
    month, units
):
    """The direct/builder shared surface agrees exactly, without tolerance."""
    pia = F(20 * units)
    entitlement = g.YearMonth(1980, month)
    built = g.record_state(
        g.WorkerRecord(
            g.FamilyKind.DISABILITY,
            eligibility_year=1983,
            eligibility_pia=pia,
            aime=2 * pia,
            first_dib_entitlement=entitlement,
        ),
        PARAMS,
    )
    direct = g.RecordState(
        g.FamilyKind.DISABILITY,
        built.pia,
        built.family_maximum,
        eligibility_year=1983,
        first_dib_entitlement=entitlement,
    )
    members = [g.Beneficiary("c", g.Role.CHILD)]
    outcomes = [
        g.evaluate_family(
            str(index), 1, lambda state=state: _family(state, members)
        )
        for index, state in enumerate((direct, built))
    ]
    assert outcomes[0].supported == outcomes[1].supported == (month >= 7)
    if month < 7:
        assert (
            outcomes[0].unsupported.reason
            is outcomes[1].unsupported.reason
            is (g.UnsupportedReason.DI_ENTITLEMENT_BEFORE_JULY_1980)
        )
    else:
        assert outcomes[0].benefits == dataclasses.replace(
            outcomes[1].benefits,
            state_source=outcomes[0].benefits.state_source,
        )


@settings(max_examples=20, deadline=None, derandomize=True)
@given(entitlement_month=st.integers(2, 6))
def test_historical_dib_impossible_dates_are_invalid_before_refusal(
    entitlement_month,
):
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(1000),
        F(1500),
        first_dib_entitlement=g.YearMonth(1980, entitlement_month),
    )
    with pytest.raises(g.InvalidFamilyInput, match="after the payment month"):
        _family(state, [], g.YearMonth(1980, entitlement_month - 1))
