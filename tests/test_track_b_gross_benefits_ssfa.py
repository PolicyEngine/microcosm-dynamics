"""SSFA conformance at the benefit-month boundary over invented families.

Verification class: statutory conformance. These tests admit gross benefits
for supported configurations only; they make no population or forecast claim.
Captured GN 02608.100 and RS 00605.360 pin the repeal effective for benefits
due January 2024, paid February 2024. G accepts the caller's PIA; it does not
derive a WEP-adjusted PIA or restore one from an earnings history.
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
GPO = g.BeneficiaryCondition.GOVERNMENT_PENSION_OFFSET
ROLE_CASES = [
    (g.FamilyKind.RETIREMENT, g.Role.SPOUSE, F(500)),
    (g.FamilyKind.RETIREMENT, g.Role.SPOUSE_CHILD_IN_CARE, F(500)),
    (g.FamilyKind.RETIREMENT, g.Role.DIVORCED_SPOUSE, F(500)),
    (g.FamilyKind.SURVIVOR, g.Role.WIDOW, F(1000)),
    (g.FamilyKind.SURVIVOR, g.Role.SURVIVING_DIVORCED_SPOUSE, F(1000)),
    (g.FamilyKind.SURVIVOR, g.Role.MOTHER_FATHER, F(750)),
    (g.FamilyKind.SURVIVOR, g.Role.DISABLED_WIDOW, F(715)),
]


def _state(kind, pia=F(1000)):
    return g.RecordState(
        kind,
        pia,
        g.floor_dime(pia * F(7, 4)),
        widow_drc_savings_clause=False,
        worker=(
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia)
            if kind is g.FamilyKind.RETIREMENT
            else None
        ),
    )


def _beneficiary(role, reductions=0, *, flagged=True):
    fields = dict(conditions={GPO} if flagged else set())
    if role in (
        g.Role.WIDOW,
        g.Role.SURVIVING_DIVORCED_SPOUSE,
        g.Role.DISABLED_WIDOW,
    ):
        fields["child_in_care"] = False
    if role in (g.Role.SPOUSE, g.Role.DIVORCED_SPOUSE):
        fields.update(reduction_months=min(reductions, 60), birth_year=1960)
    elif role in (g.Role.WIDOW, g.Role.SURVIVING_DIVORCED_SPOUSE):
        fields.update(
            reduction_months=reductions,
            reduction_period_months=84,
            birth_year=1963,
        )
    return g.Beneficiary("affected", role, **fields)


def _family(state, members, month):
    return g.family_benefits(
        state,
        members,
        payment_month=month,
        params=PARAMS,
        standalone=True,
    )


def test_ssfa_effective_month_and_payment_month_are_quoted_from_captures():
    for capture in ("poms_gn_02608_100", "poms_rs_00605_360"):
        text = source_text(capture)
        assert (
            "On January 5, 2025, the President signed the Social Security Fairness Act of 2023 (SSFA)"
            in text
        )
        assert "for benefits payable for months after December 2023." in text
        assert (
            "Beginning with benefits due for January 2024 (paid in February 2024)"
            in text
        )
    assert (
        "eliminates the offset of Social Security benefits under GPO"
        in source_text("poms_gn_02608_100")
    )
    assert "eliminates the WEP reduction" in source_text("poms_rs_00605_360")


@pytest.mark.parametrize(
    ("kind", "role", "expected"),
    ROLE_CASES,
    ids=[role.value for _, role, _ in ROLE_CASES],
)
def test_gpo_refuses_december_2023_and_computes_january_2024(
    kind, role, expected
):
    """Unreduced PIA1,000 examples; DWB alone pays 71.5% =715 exactly."""
    state = _state(kind)
    member = _beneficiary(role)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        _family(state, [member], g.YearMonth(2023, 12))
    assert caught.value.reason is g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
    assert caught.value.beneficiary_id == "affected"
    flagged = _family(state, [member], g.YearMonth(2024, 1))
    clear = _family(
        state,
        [dataclasses.replace(member, conditions=set())],
        g.YearMonth(2024, 1),
    )
    assert flagged == clear
    assert flagged.by_id()["affected"].auxiliary_payable == expected
    assert (
        flagged.by_id()["affected"].whole_dollar_auxiliary
        == expected.numerator // expected.denominator
    )


@given(
    st.sampled_from(ROLE_CASES),
    st.integers(1984, 2030),
    st.integers(1, 12),
    st.integers(100, 40_000),
)
@settings(deadline=None)
def test_gpo_repeal_is_decided_by_benefit_month(
    case, year, month_number, dimes
):
    """Every supported spouse form uses the same inclusive January boundary."""
    kind, role, _ = case
    month = g.YearMonth(year, month_number)
    state = _state(kind, F(dimes, 10))
    member = _beneficiary(role)
    if month < g.YearMonth(2024, 1):
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            _family(state, [member], month)
        assert (
            caught.value.reason
            is g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
        )
    else:
        assert _family(state, [member], month) == _family(
            state, [dataclasses.replace(member, conditions=set())], month
        )


@given(
    st.sampled_from(ROLE_CASES),
    st.integers(2024, 2035),
    st.integers(1, 12),
    st.integers(100, 40_000),
    st.integers(0, 84),
    st.integers(0, 4),
    st.booleans(),
)
@settings(deadline=None)
def test_post_repeal_gpo_flag_has_no_effect_in_families_and_households(
    case, year, month_number, dimes, reductions, child_count, household
):
    """Flagged and unflagged families are exactly equal after repeal."""
    kind, role, _ = case
    month = g.YearMonth(year, month_number)
    state = _state(kind, F(dimes, 10))
    member = _beneficiary(role, reductions)
    children = [
        g.Beneficiary(f"c{i}", g.Role.CHILD) for i in range(child_count)
    ]

    def compute(person):
        if not household:
            return _family(state, [person, *children], month)
        return g.household_benefits(
            {
                "affected": g.HouseholdRecord(
                    "insured", state, [person, *children]
                ),
                "other": g.HouseholdRecord(
                    "other", _state(g.FamilyKind.RETIREMENT)
                ),
            },
            payment_month=month,
            params=PARAMS,
        )

    assert compute(member) == compute(
        dataclasses.replace(member, conditions=set())
    )


@given(
    st.sampled_from(ROLE_CASES),
    st.integers(1984, 2023),
    st.integers(1, 12),
    st.integers(0, 2),
    st.integers(1, 2000),
)
@settings(deadline=None)
def test_pre_repeal_gpo_refusals_stay_in_denominators_at_any_member_position(
    case, year, month_number, position, weight_dimes
):
    kind, role, _ = case
    month = g.YearMonth(year, month_number)
    members = [
        g.Beneficiary("c1", g.Role.CHILD),
        g.Beneficiary("c2", g.Role.CHILD),
    ]
    members.insert(position, _beneficiary(role))
    weight = F(weight_dimes, 10)
    outcome = g.evaluate_family(
        "gpo", weight, lambda: _family(_state(kind), members, month)
    )
    assert not outcome.supported
    assert (
        outcome.unsupported.reason
        is g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET
    )
    assert outcome.unsupported.beneficiary_id == "affected"
    counts = g.count_family_outcomes([outcome])
    assert (
        counts.rows,
        counts.weight,
        counts.unsupported_rows,
        counts.unsupported_weight,
    ) == (1, weight, 1, weight)
    assert counts.unsupported_by_reason == {
        g.UnsupportedReason.GOVERNMENT_PENSION_OFFSET: (1, weight)
    }


@given(st.sampled_from(ROLE_CASES), st.integers(0, 2), st.booleans())
@settings(deadline=None)
def test_wrong_family_role_is_an_input_error_before_gpo_refusal(
    case, position, after_repeal
):
    kind, role, _ = case
    wrong = g.Role.SPOUSE if kind is g.FamilyKind.SURVIVOR else g.Role.WIDOW
    members = [
        g.Beneficiary("c", g.Role.CHILD),
        g.Beneficiary("wrong", wrong),
    ]
    members.insert(position, _beneficiary(role))
    month = g.YearMonth(2024, 1) if after_repeal else g.YearMonth(2023, 12)
    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family(
            "invalid", 1, lambda: _family(_state(kind), members, month)
        )


def test_wep_pia_is_supplied_by_caller_and_regular_pia_applies_after_repeal():
    """Invented caller PIAs850 before repeal and1,000 regular afterwards.

    G takes these amounts as input, so it preserves them exactly. Restoring
    the regular PIA is the caller's task; no earnings history enters G.
    """
    reduced = g.record_state(
        g.WorkerRecord(g.FamilyKind.RETIREMENT, 2020, F(850)), PARAMS
    )
    regular = g.record_state(
        g.WorkerRecord(g.FamilyKind.RETIREMENT, 2020, F(1000)), PARAMS
    )
    before = _family(reduced, [], g.YearMonth(2023, 12))
    after = _family(regular, [], g.YearMonth(2024, 1))
    assert before.pia == before.worker_benefit == F(850)
    assert after.pia == after.worker_benefit == F(1000)
    assert (before.whole_dollar_worker, after.whole_dollar_worker) == (
        850,
        1000,
    )
