"""Statutory conformance: operational 203(a)(5), invented families only.

No population, behavioral or forecast claim. Captures pin RS 00630.400's
conditions and two life-case procedures; invented arithmetic pins dimes.
"""

import os
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
JAN = g.YearMonth(2026, 1)
OPERATIONAL = g.SavingsClauseReading.SSA_OPERATIONAL
LITERAL = g.SavingsClauseReading.LITERAL_REFUSAL


def family(
    month=1,
    pia=F(1000),
    maximum=F(1500),
    *,
    reduction=60,
    spouse=False,
    spouse_months=60,
    children=2,
    reverse=False,
):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        maximum,
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, pia, reduction_months=reduction
        ),
    )
    rows = [g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(children)]
    if spouse:
        rows.append(
            g.Beneficiary("S", g.Role.SPOUSE, reduction_months=spouse_months)
        )
    return g.family_benefits(
        state,
        rows[::-1] if reverse else rows,
        payment_month=g.YearMonth(2026, month),
        params=PARAMS,
        standalone=True,
    )


def guard(reading=OPERATIONAL):
    return g.SavingsClauseGuard(
        JAN, earlier_months_unknown=False, reading=reading
    )


def refusal_case(reason):
    """Public-computation witnesses used by the complete refusal catalog."""
    value = guard()
    value.admit(family())
    if reason is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE:
        # One reduced spouse alone has no remaining auxiliaries for .400's
        # final division. A deliberately falling formula MAX exposes it.
        value = guard()
        value.admit(family(spouse=True, children=0, maximum=F(1400)))
        return value.admit(
            family(2, F(1010), F(1300), spouse=True, children=0)
        )
    value.admit(family(2, F(1010)))
    return value.admit(family(3, F(1010), children=1))


def test_operational_source_rules_are_quoted_from_captures():
    text = source_text("poms_rs_00630_400")
    for quote in (
        "Two or more persons are entitled to monthly benefits;",
        "Benefits for that month are reduced for the MAX and at least one beneficiary is reduced for age;",
        "PIA is increased the following month;",
        "Total family payment is less after the PIA increase than it was before.",
        "Family Payments Before PIA Increase, less Reduced Rate After Increase = Difference.",
        "Difference ÷ By the Number of Auxiliaries (rounded) = Auxiliary Rate;",
        "Reduce Increase by spouse appropriate reduction factor (RF).",
        "Difference ÷ the Number of Auxiliaries Rounded = Increase.",
        "Difference ÷ the Number of Remaining Auxiliaries (rounded).",
        "The established FMAX will not change—only total benefits payable are affected.",
    ):
        assert quote in text
    assert (
        "Once a saving clause is established, it will continue in effect "
        "until the table or formula maximum becomes larger."
    ) in source_text("poms_rs_00615_801")
    assert (
        "it is possible that the savings clause maximum may again become "
        "payable if the total payable under the savings clause exceeds "
        "that payable using the table or formula maximum."
    ) in source_text("poms_rs_00615_801")
    assert (
        "smallest amount that would have been required in order to assure "
        "that the total of monthly benefits payable on the basis of such "
        "wages and self-employment income for any such subsequent month "
        "will not be less"
    ) in source_text("ssa_act_203")


def test_default_is_operational_and_literal_is_explicit():
    assert (
        g.SavingsClauseGuard(JAN, earlier_months_unknown=False).reading
        is OPERATIONAL
    )
    assert guard(LITERAL).reading is LITERAL
    for bad in ("ssa_operational", None, True, g.FamilyKind.RETIREMENT):
        with pytest.raises(g.InvalidFamilyInput):
            guard(bad)


def test_first_guard_constructor_registers_its_enum_in_fresh_process():
    script = """
from populace_dynamics.track_b import gross_benefits as g
value = g.SavingsClauseGuard(g.YearMonth(2026, 1),
    earlier_months_unknown=False,
    reading=g.SavingsClauseReading.LITERAL_REFUSAL)
assert value.reading is g.SavingsClauseReading.LITERAL_REFUSAL
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[1],
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_operational_worker_reduction_protects_payment_not_maximum():
    before, after = family(), family(2, F(1010))
    assert before.record_total == F(1200)
    assert after.record_total == F(1197)
    value = guard()
    assert value.admit(before) is before
    outcome = value.evaluate("February", F(3), lambda: after)
    paid = outcome.benefits
    assert paid.record_total == F(1200)
    assert paid.worker_benefit == F(707)
    assert [row.auxiliary_payable for row in paid.beneficiaries] == [
        F("246.50")
    ] * 2
    assert [row.family_maximum_rate for row in paid.beneficiaries] == [
        F(245)
    ] * 2
    assert paid.family_maximum == after.family_maximum == F(1500)
    assert paid.subject_total == after.subject_total == F(1500)
    assert paid.record_total_whole_dollars == 1199
    assert value.protected_total == F(1200)
    assert value.protected_since == JAN
    assert g.count_family_outcomes([outcome]).supported_weight == F(3)
    with pytest.raises(g.InvalidFamilyInput):
        replace(paid, record_total=F(1201))


def test_operational_spouse_procedure_uses_unrounded_declared_factor():
    before = family(spouse=True)
    after = family(2, F(1010), spouse=True)
    assert before.record_total == F("1141.40")
    assert after.record_total == F("1139.70")
    assert after.by_id()["S"].age_reduction_factor == F(65, 100)
    value = guard()
    value.admit(before)
    paid = value.admit(after)
    # 1.70 / 3 -> .60; spouse increase floor(.60*.65)=.30.
    # Children: (1141.40 - 707 - 106.40)/2 = 164 each.
    assert paid.by_id()["S"].auxiliary_payable == F("106.40")
    assert paid.by_id()["C0"].auxiliary_payable == F(164)
    assert paid.by_id()["C1"].auxiliary_payable == F(164)
    assert paid.record_total == F("1141.40")
    assert paid.record_total_whole_dollars == 1141


def test_operational_rounding_is_minimum_equal_dime_that_preserves_total():
    value = guard()
    value.admit(family())
    paid = value.admit(family(2, F(1001)))
    # 1200 - 700.70 = 499.30; equal rates 249.65 round up to 249.70.
    # Rounding down to 249.60 would pay 1199.90, below 1200.
    assert paid.record_total == F("1200.10")
    assert paid.by_id()["C0"].auxiliary_payable == F("249.70")
    assert paid.record_total - F("0.20") < F(1200)


def test_operational_carries_and_can_become_payable_again():
    value = guard()
    value.admit(family())
    assert value.admit(family(2, F(1010))).record_total == F(1200)
    assert value.admit(family(3, F(1010))).record_total == F(1200)
    above = family(4, F(1010), F(1600))
    assert value.admit(above) is above
    assert value.protected_total == F(1200)
    assert value.admit(family(5, F(1010))).record_total == F(1200)


@pytest.mark.parametrize(
    "reason",
    [
        g.UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE,
        g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
    ],
)
def test_operational_named_refusals_stay_in_denominator(reason):
    outcome = g.evaluate_family("refused", F(7), lambda: refusal_case(reason))
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert counts.unsupported_by_reason == {reason: (1, F(7))}


def test_operational_child_departure_never_starts_without_pia_increase():
    value = guard()
    value.admit(family())
    after = family(2, children=1)
    assert value.admit(after) is after
    assert value.protected_total is None


def test_round_11_cola_fall_requires_age_reduction_operationally():
    # Actual formula/COLA witness from #530 round 11: unequal survivor
    # shares change from 2.40 + 2.40 + 1.80 to 2.40 + 2.40 + 1.70.
    members = [
        g.Beneficiary(f"W{i}", g.Role.WIDOW, child_in_care=False)
        for i in range(2)
    ] + [g.Beneficiary("M", g.Role.MOTHER_FATHER)]
    results = []
    for month, colas in ((1, ()), (2, (F("2.3"),))):
        state = replace(
            g.record_state(
                g.WorkerRecord(
                    g.FamilyKind.SURVIVOR,
                    2026,
                    F("4.40"),
                    cola_percents=colas,
                ),
                PARAMS,
            ),
            widow_drc_savings_clause=False,
        )
        results.append(
            g.family_benefits(
                state,
                members,
                payment_month=g.YearMonth(2026, month),
                params=PARAMS,
                standalone=True,
            )
        )
    before, after = results
    assert (before.pia, after.pia) == (F("4.40"), F("4.50"))
    assert (before.family_maximum, after.family_maximum) == (
        F("6.60"),
        F("6.70"),
    )
    assert (before.record_total, after.record_total) == (F("6.60"), F("6.50"))
    value = guard()
    value.admit(before)
    assert value.admit(after) is after
    assert value.protected_total is None
    literal = guard(LITERAL)
    literal.admit(before)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        literal.admit(after)
    assert caught.value.reason is g.UnsupportedReason.SAVINGS_CLAUSE


@settings(max_examples=60, deadline=None, derandomize=True)
@given(
    st.integers(100, 2000),
    st.integers(0, 60),
    st.integers(0, 20),
    st.sampled_from((OPERATIONAL, LITERAL)),
)
def test_both_readings_start_exactly_on_their_conditions(
    pia, reduction, rise, reading
):
    before = family(pia=F(pia), maximum=F(3 * pia, 2), reduction=reduction)
    after = family(2, F(pia) + F(rise, 10), F(3 * pia, 2), reduction=reduction)
    value = guard(reading)
    value.admit(before)
    falls = after.record_total < before.record_total
    if reading is LITERAL and rise and falls:
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            value.admit(after)
        assert caught.value.reason is g.UnsupportedReason.SAVINGS_CLAUSE
    else:
        paid = value.admit(after)
        starts = (
            bool(rise and reduction and falls)
            if reading is OPERATIONAL
            else bool(rise)
        )
        assert (value.protected_total is not None) is starts
        if starts and reading is OPERATIONAL:
            assert paid.record_total >= before.record_total
            assert paid.family_maximum == after.family_maximum
            assert paid.subject_total == after.subject_total
            assert paid.record_total - before.record_total < F("0.20")
        else:
            assert paid is after


@settings(max_examples=30, deadline=None, derandomize=True)
@given(st.integers(100, 2000), st.booleans())
def test_operational_is_deterministic_order_independent_and_sealed(
    pia, spouse
):
    outputs = []
    for reverse in (False, True, False):
        value = guard()
        value.admit(
            family(
                pia=F(pia),
                maximum=F(3 * pia, 2),
                spouse=spouse,
                reverse=reverse,
            )
        )
        paid = value.admit(
            family(
                2, F(pia + 1), F(3 * pia, 2), spouse=spouse, reverse=reverse
            )
        )
        outputs.append(
            (paid.by_id(), paid.record_total, value.protected_total)
        )
        if value.protected_total is not None:
            assert paid.record_total >= value.protected_total
            assert paid.record_total - value.protected_total < F("0.20")
            assert paid.family_maximum == F(3 * pia, 2)
            assert paid.subject_total <= paid.family_maximum
            assert paid.record_total == (paid.worker_benefit or 0) + sum(
                row.auxiliary_payable for row in paid.beneficiaries
            )
            assert all(
                row.auxiliary_payable <= row.original_benefit
                for row in paid.beneficiaries
            )
    assert outputs[0] == outputs[1] == outputs[2]


@settings(max_examples=20, deadline=None, derandomize=True)
@example(pia=1000, weight=1)
@given(st.integers(100, 2000), st.integers(1, 9))
def test_operational_carry_membership_refusal_and_denominator_properties(
    pia, weight
):
    value = guard()
    before = family(pia=F(pia), maximum=F(3 * pia, 2))
    value.admit(before)
    paid = value.admit(family(2, F(pia + 1), F(3 * pia, 2)))
    assert value.protected_total is not None
    carried = value.admit(family(3, F(pia + 1), F(3 * pia, 2)))
    assert carried.record_total == paid.record_total
    outcome = value.evaluate(
        "changed membership",
        F(weight),
        lambda: family(4, F(pia + 1), F(3 * pia, 2), children=1),
    )
    reason = g.UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.unsupported_by_reason == {reason: (1, F(weight))}

    dormant = guard()
    dormant.admit(before)
    protected = dormant.admit(family(2, F(pia + 1), F(3 * pia, 2)))
    established_total = dormant.protected_total
    established_month = dormant.protected_since
    expanded_maximum = F(3 * pia, 2) + 100
    ordinary = family(3, F(pia + 1), expanded_maximum)
    assert ordinary.record_total > established_total
    assert dormant.admit(ordinary) is ordinary
    assert dormant.protected_total == established_total
    assert dormant.protected_since == established_month == JAN
    membership_change = family(4, F(pia + 1), expanded_maximum, children=1)
    assert membership_change.record_total > established_total
    dormant_outcome = dormant.evaluate(
        "changed membership during dormant protection",
        F(weight),
        lambda: membership_change,
    )
    assert dormant_outcome.unsupported.reason is reason
    dormant_counts = g.count_family_outcomes([dormant_outcome])
    assert dormant_counts.rows == dormant_counts.unsupported_rows == 1
    assert dormant_counts.unsupported_by_reason == {reason: (1, F(weight))}
    if pia == 1000 and weight == 1:
        assert (
            before.record_total,
            protected.record_total,
            ordinary.record_total,
            membership_change.record_total,
            established_total,
        ) == (F(1200), F("1200.10"), F("1299.70"), F("1201.20"), F(1200))

    lower = guard()
    lower.admit(before)
    lower.admit(family(2, F(pia + 1), F(3 * pia, 2)))
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        lower.admit(family(3, F(pia, 2), g.floor_dime(F(3 * pia, 4))))
    assert (
        caught.value.reason
        is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )

    def deducted(month, current_pia):
        return g.family_benefits_after_deductions(
            g.RecordState(
                g.FamilyKind.RETIREMENT,
                current_pia,
                F(3 * pia, 2),
                worker=g.OwnBenefit(
                    g.OwnBenefitKind.OLD_AGE,
                    current_pia,
                    reduction_months=60,
                ),
            ),
            [g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(2)],
            payment_month=g.YearMonth(2026, month),
            params=PARAMS,
            standalone=True,
            households={},
            deductions={
                "C0": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)
            },
        )

    earlier_deduction = deducted(1, F(pia))
    history = guard()
    # A first month with no candidate protection preserves its result.
    assert history.admit(earlier_deduction) is earlier_deduction
    assert history.unknown_since is None
    assert (
        g.savings_clause_total(earlier_deduction)
        > earlier_deduction.record_total
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        history.admit(family(2, F(pia + 1), F(3 * pia, 2)))
    assert (
        caught.value.reason
        is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )
    assert history.protected_total is None
    assert history.unknown_since == g.YearMonth(2026, 2)

    active = guard()
    active.admit(before)
    active.admit(family(2, F(pia + 1), F(3 * pia, 2)))
    current_deduction = deducted(3, F(pia + 1))
    # An inflated pre-offset sum must not bypass an active protection's
    # unsupported deduction interaction just because the sum exceeds it.
    assert g.savings_clause_total(current_deduction) > active.protected_total
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        active.admit(current_deduction)
    assert (
        caught.value.reason
        is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )
    assert active.unknown_since == g.YearMonth(2026, 3)


@settings(max_examples=20, deadline=None, derandomize=True)
@given(st.integers(100, 2000), st.integers(1, 60))
def test_membership_declines_without_pia_increases_never_start_protection(
    pia, months
):
    value = guard()
    value.admit(family(pia=F(pia), maximum=F(3 * pia, 2), reduction=months))
    after = family(2, F(pia), F(3 * pia, 2), reduction=months, children=0)
    assert value.admit(after) is after
    assert value.protected_total is None


@pytest.mark.parametrize("changed", ("worker", "spouse"))
@settings(max_examples=20, deadline=None, derandomize=True)
@example(pia=100, months=37)
@example(pia=100, months=59)
@given(st.integers(100, 2000), st.integers(1, 59))
def test_simultaneous_basis_change_refuses_ambiguous_fall(
    changed, pia, months
):
    options = (
        {"reduction": months}
        if changed == "worker"
        else {"spouse": True, "spouse_months": months}
    )
    after_options = {
        **options,
        "reduction" if changed == "worker" else "spouse_months": months + 1,
    }
    for before_options, new_options, rise in (
        (options, after_options, F(1, 10)),
        (after_options, options, F(2)),
    ):
        before = family(pia=F(pia), maximum=F(3 * pia, 2), **before_options)
        after = family(2, F(pia) + rise, F(3 * pia, 2), **new_options)
        # Both worsening and improving age factors can accompany a fall.
        # PIA100/RF60 -> PIA102/RF59: 120 ->119.80; the improved age
        # factor alone raises payment, so ignoring that fall underprotects.
        value = guard()
        value.admit(before)
        if after.record_total < before.record_total:
            with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
                value.admit(after)
            assert (
                caught.value.reason
                is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
            )
            assert value.unknown_since == g.YearMonth(2026, 2)
        else:
            assert value.admit(after) is after
        assert value.protected_total is None
    if changed == "worker" and pia == 100 and months == 59:
        before = family(
            pia=F(100),
            maximum=F(150),
            reduction=0,
            spouse=True,
            spouse_months=36,
        )
        after = family(
            2, F(101), F(140), reduction=0, spouse=True, spouse_months=36
        )
        pia_only = family(
            2, F(101), F(150), reduction=0, spouse=True, spouse_months=36
        )
        assert (
            before.record_total,
            after.record_total,
            pia_only.record_total,
        ) == (F("145.60"), F("136.70"), F("145.80"))
        value = guard()
        value.admit(before)
        with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
            value.admit(after)
        assert (
            caught.value.reason
            is g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
        )
