"""POMS conformance and properties on invented retirement accounts only.

The one source example supplies a $4,000 balance and a qualitative
penalty; its dollar penalty and owner age below are explicitly invented.
No fixture or generated input describes a survey record or real account.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from populace_dynamics.income_resources.retirement_resources import (
    AdditionalTaxTreatment,
    PeriodicPaymentStatus,
    RetirementFundOwner,
    assess_retirement_fund,
    retirement_fund_countable_value,
)

INVENTED_BASE = {
    "balance": 4_000,
    "lump_sum_available": True,
    "periodic_payment_status": PeriodicPaymentStatus.NOT_ELIGIBLE,
    "owner_age": 45,
    "separated_from_employer": False,
    "withdrawal_requires_separation": False,
    "early_withdrawal_penalty": 200,
    "additional_tax_amount": 400,
    "additional_tax_treatment": AdditionalTaxTreatment.DO_NOT_DEDUCT_TAX,
    "owner": RetirementFundOwner.ELIGIBLE_INDIVIDUAL,
}
INVENTED_AMOUNTS = st.floats(
    min_value=0, max_value=1e12, allow_nan=False, allow_infinity=False
)


def test_poms_jeff_grant_current_access_despite_future_annuity_forfeiture():
    """SI 01120.210 F: employed owner can withdraw $4,000 less penalty.

    F specifies no penalty amount; $200 and age 45 are invented inputs.
    The example's future-annuity forfeiture does not remove current access.
    """
    result = assess_retirement_fund(**INVENTED_BASE)
    assert result.countable_value == 3_800
    assert result.reason == "available_lump_sum"
    assert not result.must_apply_for_periodic_benefits


def test_both_additional_tax_readings_require_explicit_selection():
    """SI 01120.210 A.3 leaves the characterization of 72(t) open."""
    assert retirement_fund_countable_value(**INVENTED_BASE) == 3_800
    assert (
        retirement_fund_countable_value(
            **{
                **INVENTED_BASE,
                "additional_tax_treatment": (
                    AdditionalTaxTreatment.DEDUCT_AS_EARLY_WITHDRAWAL_PENALTY
                ),
            }
        )
        == 3_400
    )
    kwargs = dict(INVENTED_BASE)
    del kwargs["additional_tax_treatment"]
    with pytest.raises(TypeError):
        assess_retirement_fund(**kwargs)


def test_current_partial_access_defines_value():
    """SI 01120.210 A.3, D.2: use currently available portion only."""
    assert (
        retirement_fund_countable_value(
            **INVENTED_BASE, maximum_lump_sum=1_000
        )
        == 800
    )


def test_separation_changes_current_access():
    """SI 01120.210 C.1: cannot require the owner to leave the job."""
    kwargs = {**INVENTED_BASE, "withdrawal_requires_separation": True}
    assert retirement_fund_countable_value(**kwargs) == 0
    kwargs["separated_from_employer"] = True
    assert retirement_fund_countable_value(**kwargs) == 3_800


def test_periodic_benefits_obligation_without_lump_sum():
    """SI 01120.210 B, E.1: apply and choose periodic benefits."""
    result = assess_retirement_fund(
        **{
            **INVENTED_BASE,
            "lump_sum_available": False,
            "periodic_payment_status": (
                PeriodicPaymentStatus.ELIGIBLE_ELECTION_UNRESOLVED
            ),
        }
    )
    assert result.countable_value == 0
    assert result.must_apply_for_periodic_benefits
    assert result.must_choose_periodic_over_lump_sum


def test_periodic_eligibility_does_not_silently_decide_resource_status():
    """SI 01120.210 B says 'may not'; E.1 requires the election first."""
    with pytest.raises(ValueError, match="election unresolved"):
        assess_retirement_fund(
            **{
                **INVENTED_BASE,
                "periodic_payment_status": (
                    PeriodicPaymentStatus.ELIGIBLE_ELECTION_UNRESOLVED
                ),
            }
        )


@pytest.mark.parametrize(
    "status", [PeriodicPaymentStatus.RECEIVING, PeriodicPaymentStatus.DENIED]
)
def test_periodic_state_uses_current_lump_sum_rights(status):
    """SI 01120.210 C.3, D.2: actual available rights determine value.

    Receiving payments does not prove the absence of a separate lump sum.
    The caller applies C.3's next-month timing following a denied claim.
    """
    result = assess_retirement_fund(
        **{**INVENTED_BASE, "periodic_payment_status": status}
    )
    assert result.countable_value == 3_800
    assert not result.must_apply_for_periodic_benefits


@given(
    balance=INVENTED_AMOUNTS,
    access_fraction=st.floats(min_value=0, max_value=1, allow_nan=False),
    penalty=INVENTED_AMOUNTS,
    additional_tax=INVENTED_AMOUNTS,
    treatment=st.sampled_from(list(AdditionalTaxTreatment)),
)
def test_value_bounds_and_numeric_assessment_differential(
    balance, access_fraction, penalty, additional_tax, treatment
):
    """SI 01120.210 A.3, D.2: 0 <= value <= accessible balance."""
    kwargs = {
        **INVENTED_BASE,
        "balance": balance,
        "maximum_lump_sum": balance * access_fraction,
        "early_withdrawal_penalty": penalty,
        "additional_tax_amount": additional_tax,
        "additional_tax_treatment": treatment,
    }
    result = assess_retirement_fund(**kwargs)
    assert 0 <= result.countable_value <= balance * access_fraction <= balance
    assert retirement_fund_countable_value(**kwargs) == result.countable_value


@given(
    balance=INVENTED_AMOUNTS,
    penalty=INVENTED_AMOUNTS,
    status=st.sampled_from(list(PeriodicPaymentStatus)),
)
def test_no_lump_sum_always_zero(balance, penalty, status):
    """SI 01120.210 B, D.2: no current lump-sum access means zero."""
    assert (
        retirement_fund_countable_value(
            **{
                **INVENTED_BASE,
                "balance": balance,
                "early_withdrawal_penalty": penalty,
                "lump_sum_available": False,
                "periodic_payment_status": status,
            }
        )
        == 0
    )


@given(balance=INVENTED_AMOUNTS, penalty=INVENTED_AMOUNTS)
def test_fund_requiring_current_job_termination_is_zero(balance, penalty):
    """SI 01120.210 C.1: employment termination is not required."""
    assert (
        retirement_fund_countable_value(
            **{
                **INVENTED_BASE,
                "balance": balance,
                "early_withdrawal_penalty": penalty,
                "withdrawal_requires_separation": True,
            }
        )
        == 0
    )


@given(
    balance=INVENTED_AMOUNTS,
    owner=st.sampled_from(
        [
            RetirementFundOwner.INELIGIBLE_SPOUSE,
            RetirementFundOwner.INELIGIBLE_PARENT,
            RetirementFundOwner.INELIGIBLE_PARENTS_SPOUSE,
        ]
    ),
    status=st.sampled_from(list(PeriodicPaymentStatus)),
)
def test_ineligible_family_funds_excluded_from_deeming(balance, owner, status):
    """SI 01120.210 E.4 expressly excludes all three owner roles."""
    result = assess_retirement_fund(
        **{
            **INVENTED_BASE,
            "balance": balance,
            "owner": owner,
            "periodic_payment_status": status,
        }
    )
    assert result.countable_value == 0
    assert not result.must_apply_for_periodic_benefits
    assert not result.must_choose_periodic_over_lump_sum


@given(
    balance=INVENTED_AMOUNTS,
    first_penalty=INVENTED_AMOUNTS,
    penalty_increase=INVENTED_AMOUNTS,
    treatment=st.sampled_from(list(AdditionalTaxTreatment)),
)
def test_higher_penalty_never_raises_value(
    balance, first_penalty, penalty_increase, treatment
):
    """SI 01120.210 A.3: increasing deductible penalty lowers value."""
    kwargs = {
        **INVENTED_BASE,
        "balance": balance,
        "early_withdrawal_penalty": first_penalty,
        "additional_tax_treatment": treatment,
    }
    before = retirement_fund_countable_value(**kwargs)
    kwargs["early_withdrawal_penalty"] += penalty_increase
    assert retirement_fund_countable_value(**kwargs) <= before


@given(taxes=INVENTED_AMOUNTS)
def test_ordinary_taxes_never_reduce_value(taxes):
    """SI 01120.210 A.3: ordinary taxes are never deductible."""
    assert (
        retirement_fund_countable_value(
            **INVENTED_BASE, ordinary_taxes_due=taxes
        )
        == 3_800
    )


@pytest.mark.parametrize(
    "name",
    [
        "balance",
        "early_withdrawal_penalty",
        "additional_tax_amount",
        "ordinary_taxes_due",
        "owner_age",
        "maximum_lump_sum",
    ],
)
@pytest.mark.parametrize(
    "invalid", [-1, float("nan"), float("inf"), True, "1"]
)
def test_invalid_amounts_raise(name, invalid):
    with pytest.raises(ValueError, match="finite nonnegative"):
        assess_retirement_fund(**{**INVENTED_BASE, name: invalid})


@pytest.mark.parametrize(
    "name",
    [
        "lump_sum_available",
        "separated_from_employer",
        "withdrawal_requires_separation",
    ],
)
@pytest.mark.parametrize("invalid", [0, 1, None, "false"])
def test_invalid_booleans_raise(name, invalid):
    with pytest.raises(ValueError, match="boolean"):
        assess_retirement_fund(**{**INVENTED_BASE, name: invalid})


@pytest.mark.parametrize(
    "name", ["periodic_payment_status", "additional_tax_treatment", "owner"]
)
@pytest.mark.parametrize("invalid", ["unknown", None, 1])
def test_unsupported_options_raise(name, invalid):
    with pytest.raises(ValueError, match="unsupported"):
        assess_retirement_fund(**{**INVENTED_BASE, name: invalid})


def test_age_above_coverage_raises():
    with pytest.raises(ValueError, match="outside coverage"):
        assess_retirement_fund(**{**INVENTED_BASE, "owner_age": 120.01})


def test_access_exceeding_balance_raises():
    with pytest.raises(ValueError, match="exceeds balance"):
        assess_retirement_fund(**INVENTED_BASE, maximum_lump_sum=4_001)
