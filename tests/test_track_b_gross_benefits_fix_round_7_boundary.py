"""Disclose the deliberately narrow own-RIB widow support boundary.

Verification class: statutory conformance. Invented cases and captured
POMS text only; no population, behavioral or forecast claim.
"""

from fractions import Fraction as F

import pytest

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params


def _widow_family(cohort):
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(1000),
            F(1000),
            widow_drc_savings_clause=False,
        ),
        [
            g.Beneficiary(
                "widow",
                g.Role.WIDOW,
                birth_year=cohort,
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(200)),
            )
        ],
        payment_month=g.YearMonth(2023, 12),
        params=ssa_params(),
        standalone=True,
    )


def test_review_1928_widow_refusal_discloses_implementation_boundary():
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _widow_family(1928)
    assert caught.value.reason is g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE
    assert "implementation boundary" in caught.value.detail
    assert "January 2, 1928" in caught.value.detail


def test_review_1929_widow_control_keeps_exact_own_and_auxiliary_payment():
    benefit = _widow_family(1929).beneficiaries[0]
    assert benefit.own_benefit == F(200)
    assert benefit.auxiliary_payable == F(800)
    assert benefit.whole_dollar_own == 200
    assert benefit.whole_dollar_auxiliary == 800


@pytest.mark.parametrize(
    ("source", "quote"),
    [
        (
            "poms_rs_00615_010",
            "RIB After Reduced WIB (D then A) with date of birth of "
            "1/2/1928 or later",
        ),
        (
            "poms_rs_00615_010",
            "Reduce the RIB in the usual manner without regard to the WIB",
        ),
        (
            "poms_rs_00615_020",
            "D/W prior to age 62 then A or HA. If the date of birth is "
            "prior to 1/2/1928 a carry-over reduction applies and the "
            "calculation type is d.",
        ),
    ],
)
def test_1928_source_boundary_is_quoted_from_captures(source, quote):
    assert quote in source_text(source)
