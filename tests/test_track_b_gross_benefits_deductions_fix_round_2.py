"""Statutory conformance: invented deduction-input counterexamples.

Act 203(c)(2) excludes age-reduced spouse benefits. GN 02603.050A.1/B.3
redistributes actual deductions only. No population or forecast claim.
"""

from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text as g_source_text
from tests.track_b_gross_benefit_support import ssa_params
from tests.track_b_ret_ledger_support import source_text as r2_source_text

PARAMS = ssa_params()
MONTH = g.YearMonth(2024, 1)


def retirement(pia=4, maximum=6, children=2, reduction=60):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(pia),
        F(maximum),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(pia)),
    )
    members = (g.Beneficiary("B", g.Role.SPOUSE, reduction_months=reduction),)
    members += tuple(
        g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(1, children + 1)
    )
    return state, members


def compute(state, members, deductions, household=False):
    kwargs = dict(
        payment_month=MONTH,
        params=PARAMS,
        deductions=deductions,
        households={member.beneficiary_id: "home" for member in members},
    )
    if household:
        return g.household_benefits_after_deductions(
            {"record": g.HouseholdRecord("worker", state, members)},
            **kwargs,
        )
    return g.family_benefits_after_deductions(
        state, members, standalone=True, **kwargs
    )


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("held_refusal", (False, True))
def test_age_reduced_no_care_is_input_error_before_refusal(
    household, held_refusal
):
    state, members = retirement(children=0)
    baseline = compute(state, members, {}, household)
    family = baseline.records["record"] if household else baseline
    assert family.by_id()["B"].auxiliary_payable == F("1.30")
    assert family.by_id()["B"].whole_dollar_auxiliary == 1
    if held_refusal:
        state = replace(
            state, conditions={g.RecordCondition.ADMINISTRATIVE_FINALITY}
        )
        with pytest.raises(g.FamilyConfigurationUnsupported) as held:
            compute(state, members, {}, household)
        assert held.value.reason is g.UnsupportedReason.ADMINISTRATIVE_FINALITY
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.evaluate_family(
                "invalid",
                7,
                lambda: compute(
                    state,
                    members,
                    {
                        "B": g.BenefitDeduction(
                            g.DeductionReason.NO_CHILD_IN_CARE
                        )
                    },
                    household,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("case", ("small", "large", "survivor"))
def test_reviewed_zero_deduction_cases_are_input_errors(case, household):
    if case == "survivor":
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(1),
            F("1.10"),
            widow_drc_savings_clause=False,
        )
        members = tuple(g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(3))
        events = {}
        zero_id, zero_payable = "C0", F(".30")
        expected = {f"C{i}": F(".30") for i in range(3)}
    else:
        state, members = retirement(
            4 if case == "small" else 48,
            6 if case == "small" else 78,
            2 if case == "small" else 3,
        )
        events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
        zero_id, zero_payable = "C1", F(".60" if case == "small" else "7.50")
        expected = {"B": F(0)} | {
            member.beneficiary_id: F(1 if case == "small" else 10)
            for member in members[1:]
        }
    baseline = compute(state, members, events, household)
    family = baseline.records["record"] if household else baseline
    assert {
        b.beneficiary_id: b.auxiliary_payable for b in family.beneficiaries
    } == expected
    assert {
        b.beneficiary_id: b.whole_dollar_auxiliary
        for b in family.beneficiaries
    } == {bid: int(amount) for bid, amount in expected.items()}
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.evaluate_family(
                "zero",
                3,
                lambda: compute(
                    state,
                    members,
                    events
                    | {
                        zero_id: g.BenefitDeduction(
                            g.DeductionReason.OWN_EARNINGS_TEST, zero_payable
                        )
                    },
                    household,
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0
    assert compute(state, members, events, household) == baseline


@pytest.mark.parametrize("household", (False, True))
@given(
    scale=st.integers(1, 100),
    reduction=st.integers(1, 60),
    permanent=st.booleans(),
)
@settings(max_examples=15, deadline=None)
def test_zero_event_cannot_change_existing_full_deduction_output(
    household, scale, reduction, permanent
):
    state, members = retirement(48 * scale, 78 * scale, 3, reduction)
    ordinary = compute(state, members, {}, household)
    ordinary_family = ordinary.records["record"] if household else ordinary
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    baseline = compute(state, members, events, household)
    zero = g.BenefitDeduction(
        g.DeductionReason.OWN_EARNINGS_TEST,
        ordinary_family.by_id()["C1"].auxiliary_payable,
        permanent,
    )
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(
            g.evaluate_family(
                "zero",
                5,
                lambda: compute(
                    state, members, events | {"C1": zero}, household
                ),
            )
        )
    assert g.count_family_outcomes(outcomes).rows == 0
    assert compute(state, members, events, household) == baseline


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("under_fra", (None, False, True))
@given(pia=st.integers(2, 1000), birth_year=st.integers(1930, 1950))
@example(pia=4, birth_year=1950)
@settings(max_examples=8, deadline=None)
def test_no_care_spouse_requires_unreduced_under_fra_attestation(
    household, under_fra, pia, birth_year
):
    state, members = retirement(pia, 2 * pia, 0, 0)
    event = g.BenefitDeduction(
        g.DeductionReason.NO_CHILD_IN_CARE,
        under_full_retirement_age=under_fra,
    )
    if under_fra is True:
        result = compute(state, members, {"B": event}, household)
        family = result.records["record"] if household else result
        assert family.by_id()["B"].auxiliary_payable == 0
        # A supplied cohort can make the separate age attestation impossible.
        older = (replace(members[0], birth_year=birth_year),)
        with pytest.raises(g.InvalidFamilyInput, match="birth cohort"):
            compute(state, older, {"B": event}, household)
        younger = (replace(members[0], birth_year=1960),)
        result = compute(state, younger, {"B": event}, household)
        family = result.records["record"] if household else result
        assert family.by_id()["B"].auxiliary_payable == 0
    else:
        outcomes = []
        with pytest.raises(g.InvalidFamilyInput):
            outcomes.append(
                g.evaluate_family(
                    "missing-age",
                    3,
                    lambda: compute(state, members, {"B": event}, household),
                )
            )
        assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("household", (False, True))
@given(reduction=st.integers(1, 60))
@example(reduction=60)
@settings(max_examples=8, deadline=None)
def test_under_fra_attestation_cannot_admit_an_age_reduced_spouse(
    household, reduction
):
    state, members = retirement(reduction=reduction)
    event = g.BenefitDeduction(
        g.DeductionReason.NO_CHILD_IN_CARE,
        under_full_retirement_age=True,
    )
    with pytest.raises(g.InvalidFamilyInput, match="age-reduced"):
        compute(state, members, {"B": event}, household)


def test_zero_event_is_measured_after_nh_reservation():
    state, members = retirement()
    with pytest.raises(g.InvalidFamilyInput, match="positive amount"):
        g.family_benefits_after_deductions(
            state,
            members,
            payment_month=MONTH,
            params=PARAMS,
            deductions={
                "C1": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F(".50")
                )
            },
            households={},
            worker_deductions={"C1": F(".10")},
            standalone=True,
        )


def test_no_care_age_exclusion_is_quoted_from_existing_captures():
    text = g_source_text("ssa_act_203")
    assert "if a wife or husband under retirement age" in text
    assert (
        "and such wife's or husband's insurance benefit for such month "
        "was not reduced under the provisions of section 202(q)"
    ) in text
    text = r2_source_text("ecfr_20cfr404_subpart_e")
    assert "if he or she is under full retirement age" in text
    assert (
        "there is in effect a certificate of election for him or her to "
        "receive actuarially reduced wife's or husband's benefits for such month"
    ) in text


@pytest.mark.parametrize("household", (False, True))
@given(scale=st.integers(1, 100))
@example(scale=1)
@settings(max_examples=8, deadline=None)
def test_zero_event_validation_precedes_an_unsupported_deduction(
    household, scale
):
    state, members = retirement(4 * scale, 6 * scale)
    ordinary = compute(state, members, {}, household)
    family = ordinary.records["record"] if household else ordinary
    with pytest.raises(g.InvalidFamilyInput):
        compute(
            state,
            members,
            {
                "B": g.BenefitDeduction(g.DeductionReason.PRISONER_SUSPENSION),
                "C1": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST,
                    family.by_id()["C1"].auxiliary_payable,
                ),
            },
            household,
        )
    if household:
        # The unique child's zero deduction is computable independently of
        # the shared child's combined-maximum coverage refusal.
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            F(4 * scale),
            F(6 * scale),
            widow_drc_savings_clause=False,
        )
        shared = g.Beneficiary("shared", g.Role.CHILD)
        unique = g.Beneficiary("unique", g.Role.CHILD)
        records = {
            "a": g.HouseholdRecord("deceased-a", state, (shared, unique)),
            "b": g.HouseholdRecord("deceased-b", state, (shared,)),
        }
        with pytest.raises(g.InvalidFamilyInput, match="positive amount"):
            g.household_benefits_after_deductions(
                records,
                payment_month=MONTH,
                params=PARAMS,
                deductions={
                    "unique": g.BenefitDeduction(
                        g.DeductionReason.OWN_EARNINGS_TEST, F(3 * scale)
                    )
                },
                households={},
            )
