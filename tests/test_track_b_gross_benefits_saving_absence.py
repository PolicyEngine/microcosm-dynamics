"""Statutory conformance: outside-maximum saving-clause independence.

Invented families only; no population, behavioral or forecast claim. Act
203(a)(3)(C)'s as-if-absent rule governs every operational predicate, while
the separately selected literal refusal reading retains its old semantics.
"""

from fractions import Fraction as F

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

PARAMS = ssa_params()
JAN = g.YearMonth(2026, 1)


def family(
    month,
    pia,
    maximum,
    *,
    outside=False,
    reduction=0,
    outside_reduction=60,
    kind=g.FamilyKind.RETIREMENT,
    sole_widow=False,
    reverse=False,
):
    worker = (
        g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia, reduction_months=reduction)
        if kind is g.FamilyKind.RETIREMENT
        else None
    )
    state = g.RecordState(
        kind,
        pia,
        maximum,
        worker=worker,
        widow_drc_savings_clause=False,
    )
    rows = (
        [
            g.Beneficiary(
                "W",
                g.Role.WIDOW,
                original_benefit_basis=2 * pia,
                reduction_months=reduction,
                reduction_period_months=60,
                child_in_care=False,
            )
        ]
        if sole_widow
        else [g.Beneficiary(name, g.Role.CHILD) for name in ("C1", "C2")]
    )
    if outside:
        life = kind is g.FamilyKind.RETIREMENT
        rows.append(
            g.Beneficiary(
                "D",
                (
                    g.Role.DIVORCED_SPOUSE
                    if life
                    else g.Role.SURVIVING_DIVORCED_SPOUSE
                ),
                reduction_months=outside_reduction,
                reduction_period_months=None if life else 60,
                child_in_care=False,
                first_entitlement_child_in_care=False if life else None,
            )
        )
    return g.family_benefits(
        state,
        rows[::-1] if reverse else rows,
        payment_month=g.YearMonth(2026, month),
        params=PARAMS,
        standalone=True,
    )


def guard():
    return g.SavingsClauseGuard(JAN, earlier_months_unknown=False)


def test_outside_maximum_operational_rules_are_quoted_from_captures():
    assert (
        "shall be determined as if no such divorced spouse or surviving "
        "divorced spouse were entitled to benefits for such month."
    ) in source_text("ssa_act_203")
    assert (
        "Benefits for that month are reduced for the MAX and at least one "
        "beneficiary is reduced for age;"
    ) in source_text("poms_rs_00630_400")


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize(
    "pia,maximum,child,divorced,total,whole",
    (
        (F(4), F(6), F(".90"), F("1.30"), F("7.20"), 5),
        (F(".4"), F(".6"), F(0), F(".1"), F(".6"), 0),
    ),
)
def test_review_outside_divorced_age_reduction_cannot_start_protection(
    reverse, pia, maximum, child, divorced, total, whole
):
    before = family(1, pia, maximum, outside=True, reverse=reverse)
    after = family(2, pia + F(".1"), maximum, outside=True, reverse=reverse)
    value = guard()
    value.admit(before)
    outcome = value.evaluate(
        "outside age only", F(7), lambda after=after: after
    )
    assert outcome.supported
    paid = outcome.benefits
    assert paid.by_id()["C1"].auxiliary_payable == child
    assert paid.by_id()["C2"].auxiliary_payable == child
    assert paid.by_id()["D"] == after.by_id()["D"]
    assert paid.by_id()["D"].auxiliary_payable == divorced
    assert not paid.by_id()["D"].subject_to_family_maximum
    assert paid.record_total == total
    assert paid.record_total_whole_dollars == whole
    assert value.protected_total is None
    counts = g.count_family_outcomes([outcome])
    assert counts.rows == counts.supported_rows == 1
    assert counts.weight == counts.supported_weight == F(7)


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("presence", ((False, True), (True, False)))
def test_outside_membership_changes_preserve_active_and_dormant_protection(
    reverse, presence
):
    plain, decorated = guard(), guard()
    for month, pia, maximum in (
        (1, F(1000), F(1500)),
        (2, F(1010), F(1500)),
        (3, F(1010), F(1600)),
        (4, F(1010), F(1500)),
    ):
        options = dict(reduction=60, reverse=reverse)
        baseline = plain.admit(family(month, pia, maximum, **options))
        ordinary = family(
            month,
            pia,
            maximum,
            outside=presence[(month - 1) % 2],
            **options,
        )
        out = decorated.evaluate(
            "outside membership", F(7), lambda ordinary=ordinary: ordinary
        )
        assert out.supported
        assert decorated.protected_total == plain.protected_total
        assert decorated.protected_since == plain.protected_since
        for name, row in baseline.by_id().items():
            assert out.benefits.by_id()[name] == row
        if "D" in ordinary.by_id():
            assert out.benefits.by_id()["D"] == ordinary.by_id()["D"]
    assert plain.protected_total == F(1200)


@pytest.mark.parametrize("reverse", (False, True))
def test_outside_age_basis_change_does_not_hide_worker_protection(reverse):
    value = guard()
    value.admit(
        family(
            1, F(1000), F(1500), outside=True, reduction=60, reverse=reverse
        )
    )
    after = family(
        2,
        F(1010),
        F(1500),
        outside=True,
        outside_reduction=0,
        reduction=60,
        reverse=reverse,
    )
    out = value.evaluate("outside age changes", 1, lambda after=after: after)
    assert out.supported
    assert value.protected_total == F(1200)
    assert out.benefits.by_id()["C1"].auxiliary_payable == F("246.50")
    assert out.benefits.by_id()["C2"].auxiliary_payable == F("246.50")
    assert out.benefits.by_id()["D"] == after.by_id()["D"]


@pytest.mark.parametrize("reverse", (False, True))
def test_surviving_divorced_person_cannot_supply_operational_membership(
    reverse,
):
    # Only W is governed. Adding D must not turn W's independent age change
    # into a two-person saving-clause event or a rate-procedure refusal.
    for outside in (False, True):
        value = guard()
        value.admit(
            family(
                1,
                F(4),
                F(6),
                outside=outside,
                reduction=12,
                kind=g.FamilyKind.SURVIVOR,
                sole_widow=True,
                reverse=reverse,
            )
        )
        after = family(
            2,
            F("4.1"),
            F(6),
            outside=outside,
            reduction=60,
            kind=g.FamilyKind.SURVIVOR,
            sole_widow=True,
            reverse=reverse,
        )
        out = value.evaluate(
            "one governed widow", 1, lambda after=after: after
        )
        assert out.supported
        assert out.benefits == after
        assert value.protected_total is None


@pytest.mark.parametrize("reverse", (False, True))
def test_outside_surviving_divorced_age_cannot_trigger_survivor_protection(
    reverse,
):
    rows = [
        g.Beneficiary(name, g.Role.WIDOW, child_in_care=False)
        for name in ("W1", "W2")
    ] + [
        g.Beneficiary("M", g.Role.MOTHER_FATHER),
        g.Beneficiary(
            "D",
            g.Role.SURVIVING_DIVORCED_SPOUSE,
            reduction_months=60,
            reduction_period_months=60,
            child_in_care=False,
        ),
    ]
    value = guard()
    for month, pia, maximum, expected in (
        (1, F("4.4"), F("6.6"), F("6.6")),
        (2, F("4.5"), F("6.7"), F("6.5")),
    ):
        state = g.RecordState(
            g.FamilyKind.SURVIVOR,
            pia,
            maximum,
            widow_drc_savings_clause=False,
        )
        ordinary = g.family_benefits(
            state,
            rows[::-1] if reverse else rows,
            payment_month=g.YearMonth(2026, month),
            params=PARAMS,
            standalone=True,
        )
        assert g.savings_clause_total(ordinary) == expected
        out = value.evaluate(
            "surviving divorced age only",
            1,
            lambda ordinary=ordinary: ordinary,
        )
        assert out.supported
        assert out.benefits == ordinary
        assert value.protected_total is None


@settings(max_examples=60, deadline=None, derandomize=True)
@example(
    base=1000,
    retirement=True,
    sole_widow=False,
    history=[
        (0, 0, 60, False, 60),
        (10, 0, 60, True, 0),
        (10, 10, 60, False, 30),
        (10, 0, 60, True, 60),
    ],
)
@example(
    base=20,
    retirement=True,
    sole_widow=False,
    history=[(0, 0, 0, True, 60), (1, 0, 0, True, 60)],
)
@given(
    base=st.integers(20, 2000),
    retirement=st.booleans(),
    sole_widow=st.booleans(),
    history=st.lists(
        st.tuples(
            st.integers(0, 30),
            st.integers(-10, 10),
            st.integers(0, 60),
            st.booleans(),
            st.integers(0, 60),
        ),
        min_size=2,
        max_size=6,
    ),
)
def test_property_operational_histories_treat_outside_people_as_absent(
    base, retirement, sole_widow, history
):
    kind = g.FamilyKind.RETIREMENT if retirement else g.FamilyKind.SURVIVOR
    snapshots = []
    for reverse in (False, True):
        plain, decorated = guard(), guard()
        results = []
        for month, (
            rise,
            max_change,
            reduction,
            present,
            outside_rf,
        ) in enumerate(history, 1):
            pia = F(base, 5) + F(rise, 10)
            maximum = max(pia, F(3 * base, 10) + F(max_change, 10))
            options = dict(
                reduction=reduction,
                kind=kind,
                sole_widow=sole_widow and not retirement,
                reverse=reverse,
            )
            baseline = family(month, pia, maximum, **options)
            ordinary = family(
                month,
                pia,
                maximum,
                outside=present,
                outside_reduction=outside_rf,
                **options,
            )
            plain_out = plain.evaluate(
                "plain", F(7), lambda baseline=baseline: baseline
            )
            out = decorated.evaluate(
                "outside", F(7), lambda ordinary=ordinary: ordinary
            )
            assert out.supported == plain_out.supported
            assert decorated.protected_total == plain.protected_total
            assert decorated.protected_since == plain.protected_since
            assert decorated.unknown_since == plain.unknown_since
            assert decorated.refused_since == plain.refused_since
            if out.supported:
                expected = plain_out.benefits.by_id()
                assert {
                    name: row
                    for name, row in out.benefits.by_id().items()
                    if name != "D"
                } == expected
                assert g.savings_clause_total(out.benefits) == (
                    g.savings_clause_total(plain_out.benefits)
                )
                if present:
                    assert out.benefits.by_id()["D"] == ordinary.by_id()["D"]
                results.append((expected, decorated.protected_total))
            else:
                assert out.unsupported.reason is plain_out.unsupported.reason
                results.append(
                    (out.unsupported.reason, decorated.protected_total)
                )
        snapshots.append(results)
    assert snapshots[0] == snapshots[1]
