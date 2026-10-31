"""Statutory conformance: saving-clause coverage, invented families only.

RS 00630.400's four conditions do not exempt a concurrent membership
change. Its captured payment procedures do not establish protection from
prior or current dual-entitlement rates. No population or forecast claim.
"""

from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()
JAN = g.YearMonth(2026, 1)
FEB = g.YearMonth(2026, 2)


def family(
    month,
    pia,
    maximum,
    *,
    names=("C0", "C1"),
    own=None,
    own_role=g.Role.CHILD,
    reverse=False,
):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(pia),
        F(maximum),
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(pia), reduction_months=60
        ),
    )
    rows = [
        g.Beneficiary(
            name,
            own_role if index == 0 else g.Role.CHILD,
            own_benefit=(
                g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(own))
                if own is not None and index == 0
                else None
            ),
            own_benefit_first=(
                True if own is not None and index == 0 else None
            ),
        )
        for index, name in enumerate(names)
    ]
    return g.family_benefits(
        state,
        rows[::-1] if reverse else rows,
        payment_month=g.YearMonth(2026, month),
        params=PARAMS,
        standalone=True,
    )


def guard():
    return g.SavingsClauseGuard(JAN, earlier_months_unknown=False)


def assert_refused_with_history(value, after, reason, *, protected=None):
    outcome = value.evaluate("concurrent change", F(7), lambda: after)
    assert outcome.benefits is None
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(7)
    assert counts.unsupported_by_reason == {reason: (1, F(7))}
    assert value.protected_total == protected
    assert value.unknown_since == after.payment_month
    assert value.next_month == g.YearMonth(2026, after.payment_month.month + 1)
    return outcome


@pytest.mark.parametrize(
    "pia,new_pia,maximum,names,ordinary_total",
    (
        (F(".40"), F(".50"), F(".60"), ("C0", "C2"), F(".30")),
        (F(1000), F(1010), F(1500), ("C0", "C2"), F(1197)),
        (F(1000), F(1010), F(1500), ("C0", "C1", "C2"), F("1196.90")),
        (F(1000), F(1010), F(1500), ("C0",), F(1197)),
    ),
)
def test_first_trigger_membership_change_refuses_and_retains_denominator(
    pia, new_pia, maximum, names, ordinary_total
):
    before = family(1, pia, maximum)
    after = family(2, new_pia, maximum, names=names)
    assert before.record_total == (F(".40") if pia < 1 else F(1200))
    assert after.record_total == ordinary_total < before.record_total
    value = guard()
    assert value.admit(before) is before
    assert_refused_with_history(
        value, after, g.UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE
    )
    # Once a possible protection is lost, a later ordinary month cannot
    # certify that the unseen successor protection has disappeared.
    later = family(3, new_pia, maximum, names=names)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        value.admit(later)
    assert (
        caught.value.reason
        is g.UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE
    )
    assert value.unknown_since == FEB


@pytest.mark.parametrize("role", (g.Role.SPOUSE, g.Role.CHILD))
@pytest.mark.parametrize(
    "pia,new_pia,maximum,own,before_total,prior_diagnostic,after_total",
    (
        (
            F(1),
            F("1.10"),
            F("1.50"),
            F(".10"),
            F("1.20"),
            F("1.30"),
            F("1.10"),
        ),
        (F(1000), F(1010), F(1500), F(100), F(1200), F(1300), F(1197)),
    ),
)
def test_prior_own_benefit_cessation_refuses_before_setting_protection(
    role,
    pia,
    new_pia,
    maximum,
    own,
    before_total,
    prior_diagnostic,
    after_total,
):
    before = family(1, pia, maximum, own=own, own_role=role)
    after = family(2, new_pia, maximum, own_role=role)
    assert before.record_total == before_total
    assert g.savings_clause_total(before) == prior_diagnostic
    assert after.record_total == after_total
    value = guard()
    assert value.admit(before) is before
    assert_refused_with_history(
        value, after, g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )
    later = family(3, new_pia, maximum, own_role=role)
    with pytest.raises(g.FamilyConfigurationUnsupported) as caught:
        value.admit(later)
    assert (
        caught.value.reason
        is g.UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )


@pytest.mark.parametrize("role", (g.Role.SPOUSE, g.Role.CHILD))
def test_current_own_benefit_refuses_before_setting_protection(role):
    before = family(1, 1000, 1500, own_role=role)
    after = family(2, 1010, 1500, own=1, own_role=role)
    assert g.savings_clause_total(after) < before.record_total
    value = guard()
    value.admit(before)
    assert_refused_with_history(
        value, after, g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )


@pytest.mark.parametrize("role", (g.Role.SPOUSE, g.Role.CHILD))
@pytest.mark.parametrize("dormant", (False, True))
def test_current_own_benefit_refuses_carried_and_dormant_protection(
    role, dormant
):
    value = guard()
    value.admit(family(1, 1000, 1500, own_role=role))
    assert (
        value.admit(family(2, 1010, 1500, own_role=role)).record_total == 1200
    )
    after = family(3, 1010, 1600 if dormant else 1500, own=100, own_role=role)
    assert (after.record_total >= F(1200)) is dormant
    assert_refused_with_history(
        value,
        after,
        g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
        protected=F(1200),
    )


@settings(max_examples=20, deadline=None, derandomize=True)
@given(
    st.integers(100, 2000),
    st.sampled_from((("C0", "C2"), ("C0", "C1", "C2"), ("C0",))),
    st.booleans(),
)
def test_qualifying_membership_change_is_order_independent_refusal(
    pia, names, reverse
):
    maximum = F(3 * pia, 2)
    before = family(1, pia, maximum, reverse=reverse)
    after = family(2, pia + 10, maximum, names=names, reverse=reverse)
    assert after.record_total < before.record_total
    value = guard()
    value.admit(before)
    assert_refused_with_history(
        value, after, g.UnsupportedReason.SAVINGS_CLAUSE_MEMBERSHIP_CHANGE
    )


@settings(max_examples=20, deadline=None, derandomize=True)
@given(
    st.integers(100, 2000),
    st.sampled_from((g.Role.SPOUSE, g.Role.CHILD)),
    st.booleans(),
)
def test_prior_own_benefit_cessation_always_preserves_uncertain_history(
    pia, role, reverse
):
    maximum = F(3 * pia, 2)
    before = family(
        1, pia, maximum, own=F(pia, 10), own_role=role, reverse=reverse
    )
    after = family(2, pia + 10, maximum, own_role=role, reverse=reverse)
    assert after.record_total < g.savings_clause_total(before)
    value = guard()
    value.admit(before)
    assert_refused_with_history(
        value, after, g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE
    )


@settings(max_examples=20, deadline=None, derandomize=True)
@given(
    st.integers(100, 2000),
    st.sampled_from((g.Role.SPOUSE, g.Role.CHILD)),
    st.booleans(),
)
def test_current_own_benefit_never_certifies_candidate_or_carried_protection(
    pia, role, carried
):
    maximum = F(3 * pia, 2)
    before = family(1, pia, maximum, own_role=role)
    value = guard()
    value.admit(before)
    if carried:
        value.admit(family(2, pia + 10, maximum, own_role=role))
    after = family(
        3 if carried else 2,
        pia + 10,
        maximum + (100 if carried else 0),
        own=F(".10"),
        own_role=role,
    )
    assert_refused_with_history(
        value,
        after,
        g.UnsupportedReason.SAVINGS_CLAUSE_RATE_PROCEDURE,
        protected=before.record_total if carried else None,
    )


@settings(max_examples=20, deadline=None, derandomize=True)
@given(st.integers(100, 2000), st.booleans())
def test_membership_decline_without_pia_increase_stays_admitted(pia, reverse):
    maximum = F(3 * pia, 2)
    before = family(1, pia, maximum, reverse=reverse)
    after = family(2, pia, maximum, names=(), reverse=reverse)
    assert after.record_total < before.record_total
    value = guard()
    value.admit(before)
    assert value.admit(after) is after
    assert value.protected_total is None
    assert value.unknown_since is None
