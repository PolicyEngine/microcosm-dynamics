"""One person has one SSA cohort across optional duplicate metadata.

Verification class: statutory conformance. Invented families only; no
population, behavioral or forecast claim. Cohort-placement differentials
use exact equality, with no rounding tolerance.
"""

from dataclasses import replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
NOW = g.YearMonth(2023, 12)
WEIGHT = F(7, 3)
STYLES = ("direct", "built")
ENTRIES = (
    "family",
    "household",
    "evaluate-family",
    "evaluate-household",
    "household-month-outcome",
)
PLACEMENTS = ("beneficiary", "own", "both")
CASES = ("widow-own", "spouse-own", "spouse-auxiliary")


def _member(case, months, placement, cohort=1935, *, gpo=False):
    widow = case == "widow-own"
    return g.Beneficiary(
        "person",
        g.Role.WIDOW if widow else g.Role.SPOUSE,
        reduction_months=months if case == "spouse-auxiliary" else 0,
        birth_year=cohort if placement != "own" else None,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(100),
            reduction_months=months if case != "spouse-auxiliary" else 0,
            birth_year=cohort if placement != "beneficiary" else None,
        ),
        own_benefit_first=None if widow else True,
        conditions=(
            {g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET}
            if gpo
            else set()
        ),
    )


def _run(style, entry, member, *, pia=F(1000)):
    kind = (
        g.FamilyKind.SURVIVOR
        if member.role is g.Role.WIDOW
        else g.FamilyKind.RETIREMENT
    )
    if style == "built":
        state = g.record_state(g.WorkerRecord(kind, 2020, pia), PARAMS)
        state = replace(state, widow_drc_savings_clause=False)
    else:
        state = g.RecordState(
            kind,
            pia,
            g.floor_dime(
                pia * (F(7, 4) if kind is g.FamilyKind.SURVIVOR else F(3, 2))
            ),
            worker=(
                None
                if kind is g.FamilyKind.SURVIVOR
                else g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia)
            ),
            widow_drc_savings_clause=False,
        )
    records = {"record": g.HouseholdRecord("worker", state, (member,))}

    def family():
        return g.family_benefits(
            state, [member], payment_month=NOW, params=PARAMS, standalone=True
        )

    def household():
        return g.household_benefits(records, payment_month=NOW, params=PARAMS)

    if entry == "household-month-outcome":
        guard = g.SavingsClauseGuard(
            NOW,
            earlier_months_unknown=False,
            reading=g.SavingsClauseReading.LITERAL_REFUSAL,
        )
        try:
            result = g.household_month_outcome(
                records,
                payment_month=NOW,
                params=PARAMS,
                guards={"record": guard},
                weight=WEIGHT,
            )
        except g.InvalidFamilyInput:
            assert guard.next_month == NOW
            raise
    elif entry.startswith("evaluate-"):
        result = g.evaluate_family(
            "person",
            WEIGHT,
            family if entry == "evaluate-family" else household,
        )
    else:
        result = family() if entry == "family" else household()
    if isinstance(result, g.FamilyOutcome):
        if not result.supported:
            counts = g.count_family_outcomes([result])
            assert (counts.rows, counts.weight) == (1, WEIGHT)
            assert (counts.unsupported_rows, counts.unsupported_weight) == (
                1,
                WEIGHT,
            )
            return result.unsupported.reason
        result = result.benefits
    if isinstance(result, g.HouseholdBenefits):
        result = result.records["record"]
    return result.by_id()["person"]


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("placement", PLACEMENTS)
@pytest.mark.parametrize("gpo", (False, True))
def test_review_rf37_is_invalid_before_any_refusal(
    style, entry, case, placement, gpo
):
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _run(style, entry, _member(case, 37, placement, gpo=gpo))


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_review_rf36_control_is_supported_with_either_cohort_field(
    style, entry, case, placement
):
    actual = _run(style, entry, _member(case, 36, placement))
    assert actual == _run(style, entry, _member(case, 36, "both"))
    if case == "widow-own":
        assert actual.own_benefit == F(80)
        assert actual.auxiliary_payable == F(920)


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_valid_rf36_gpo_control_retains_refusal_and_weight(
    style, entry, case, placement
):
    expected = g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
    if entry in ("family", "household"):
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _run(style, entry, _member(case, 36, placement, gpo=True))
        assert caught.value.reason is expected
    else:
        assert (
            _run(style, entry, _member(case, 36, placement, gpo=True))
            is expected
        )


@given(
    st.integers(1929, 1965),
    st.integers(0, 60),
    st.sampled_from(CASES),
    st.sampled_from(STYLES),
    st.sampled_from(ENTRIES),
    st.booleans(),
)
@settings(deadline=None)
def test_property_cohort_placement_has_identical_outcome(
    cohort, months, case, style, entry, gpo
):
    outcomes = []
    for placement in PLACEMENTS:
        member = _member(case, months, placement, cohort, gpo=gpo)
        original = member
        if months > PARAMS.fra_months(cohort) - 744:
            with pytest.raises(g.InvalidFamilyInput):
                _run(style, entry, member)
        elif gpo and entry in ("family", "household"):
            with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
                _run(style, entry, member)
            outcomes.append(caught.value.reason)
        else:
            result = _run(style, entry, member)
            outcomes.append(result)
            if not gpo:
                expected_own = g.worker_age_adjusted(
                    F(100),
                    months if case != "spouse-auxiliary" else 0,
                    0,
                    cohort,
                    PARAMS,
                )[1]
                assert result.own_benefit == expected_own
        assert member == original
        assert member.birth_year == (None if placement == "own" else cohort)
        assert member.own_benefit.birth_year == (
            None if placement == "beneficiary" else cohort
        )
    assert all(outcome == outcomes[0] for outcome in outcomes)


@given(
    st.integers(1929, 1965),
    st.integers(1, 30),
    st.sampled_from(CASES),
    st.sampled_from(STYLES),
    st.sampled_from(ENTRIES),
)
@settings(deadline=None)
def test_property_conflicting_cohorts_are_input_errors(
    cohort, difference, case, style, entry
):
    member = _member(case, 0, "both", cohort, gpo=True)
    member = replace(
        member,
        own_benefit=replace(
            member.own_benefit, birth_year=cohort + difference
        ),
    )
    with pytest.raises(g.InvalidFamilyInput, match="differs"):
        _run(style, entry, member)


@given(
    st.integers(1929, 1965), st.sampled_from(STYLES), st.sampled_from(ENTRIES)
)
@settings(deadline=None)
def test_property_own_only_cohort_fixes_widow_auxiliary_period(
    cohort, style, entry
):
    period = g.widow_reduction_period_months(date(cohort, 1, 2))
    for placement in PLACEMENTS:
        member = replace(
            _member("widow-own", 0, placement, cohort),
            reduction_months=period,
            reduction_period_months=period,
        )
        actual = _run(style, entry, member)
        assert actual.auxiliary_payable == F(615)
        with pytest.raises(g.InvalidFamilyInput, match="cohort"):
            _run(
                style,
                entry,
                replace(
                    member,
                    reduction_period_months=(62 if period == 60 else 60),
                ),
            )


def test_cohort_bound_rules_are_present_in_manifest_captures():
    assert (
        "People Born 1/1/38 or Earlier FRA for retirement or spouse's "
        "benefits is age 65." in source_text("poms_rs_00615_003")
    )
    assert (
        "The RIB is equal to the PIA reduced by the number of months of "
        "entitlement to RIB before full retirement age (FRA)."
        in source_text("poms_rs_00615_010")
    )


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
def test_review_minimized_positive_dime_rf37_is_invalid(style, entry):
    member = _member("widow-own", 37, "beneficiary", gpo=True)
    member = replace(
        member, own_benefit=replace(member.own_benefit, pia=F("0.10"))
    )
    with pytest.raises(g.InvalidFamilyInput, match="between 0 and 36"):
        _run(style, entry, member, pia=F("0.10"))


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("entry", ENTRIES)
def test_own_only_cohort_preserves_pre_1929_widow_sequence_refusal(
    style, entry
):
    member = _member("widow-own", 0, "own", 1928)
    if entry in ("family", "household"):
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _run(style, entry, member)
        assert (
            caught.value.reason
            is g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE
        )
    else:
        assert (
            _run(style, entry, member)
            is g.UnsupportedReason.DUAL_ENTITLEMENT_SEQUENCE
        )
