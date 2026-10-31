"""Statutory conformance: outside deductions and A.1/A.2 composition.

Invented families only; no population, behavioral or forecast claim.
Act 203(a)(3)(C) and GN 02603.020B exclude outside beneficiaries from
readjustment. The ruled GN 02603.050A.1/A.2 conflict refuses only when
the two readings change payments.
"""

import hashlib
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import Phase, assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params
from tests.track_b_ret_ledger_support import manifest as deduction_manifest
from tests.track_b_ret_ledger_support import source_text as deduction_text

PARAMS = ssa_params()
MONTH = g.YearMonth(2024, 1)
COMPOSITION = "sole_full_deduction_zero_dual_composition"


def state_and_members(
    pia, maximum, *, survivor=False, children=1, reduction=36, disability=False
):
    state = g.RecordState(
        (
            g.FamilyKind.SURVIVOR
            if survivor
            else (
                g.FamilyKind.DISABILITY
                if disability
                else g.FamilyKind.RETIREMENT
            )
        ),
        pia,
        maximum,
        worker=(
            None
            if survivor or disability
            else g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia)
        ),
        widow_drc_savings_clause=False,
        first_dib_entitlement=g.YearMonth(2024, 1) if disability else None,
    )
    members = [
        g.Beneficiary(
            "B",
            g.Role.WIDOW if survivor else g.Role.SPOUSE,
            birth_year=1960,
            reduction_months=reduction,
            reduction_period_months=80 if survivor else None,
            child_in_care=False if survivor else None,
        )
    ] + [g.Beneficiary(f"C{i}", g.Role.CHILD) for i in range(children)]
    return state, members


def outside_member(survivor=False):
    return g.Beneficiary(
        "D",
        (
            g.Role.SURVIVING_DIVORCED_SPOUSE
            if survivor
            else g.Role.DIVORCED_SPOUSE
        ),
        birth_year=1962,
        reduction_months=60,
        reduction_period_months=84 if survivor else None,
        child_in_care=False,
        first_entitlement_child_in_care=None if survivor else False,
    )


def compute(
    state, members, events, *, household=False, reverse=False, **kwargs
):
    members = tuple(reversed(members)) if reverse else tuple(members)
    arguments = dict(
        payment_month=MONTH,
        params=PARAMS,
        deductions=events,
        households={b.beneficiary_id: "home" for b in members},
        **kwargs,
    )
    if household:
        return g.household_benefits_after_deductions(
            {"r": g.HouseholdRecord("nh", state, members)}, **arguments
        )
    return g.family_benefits_after_deductions(
        state, members, standalone=True, **arguments
    )


def outcome(state, members, events, **kwargs):
    value = g.evaluate_family(
        "invented family", 7, lambda: compute(state, members, events, **kwargs)
    )
    counts = g.count_family_outcomes([value])
    assert counts.rows == 1
    assert counts.supported_weight + counts.unsupported_weight == 7
    return value


def family(value, household=False):
    assert value.supported
    counts = g.count_family_outcomes([value])
    assert counts.supported_weight == 7
    return value.benefits.records["r"] if household else value.benefits


def subject_payments(result):
    return (
        result.worker_benefit,
        {
            b.beneficiary_id: (b.auxiliary_payable, b.whole_dollar_auxiliary)
            for b in result.beneficiaries
            if b.subject_to_family_maximum
        },
    )


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_outside_only_event_cannot_activate_subject_nh_deduction(
    household, reverse
):
    state, _ = state_and_members(F(400), F(600))
    members = [g.Beneficiary(name, g.Role.CHILD) for name in ("B", "C0")]
    plain = family(
        outcome(
            state,
            members,
            {},
            household=household,
            worker_deductions={"B": F(10)},
        ),
        household,
    )
    paid = family(
        outcome(
            state,
            members + [outside_member()],
            {"D": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
            household=household,
            reverse=reverse,
            worker_deductions={"B": F(10)},
        ),
        household,
    )
    assert subject_payments(plain) == subject_payments(paid)
    assert plain.by_id()["B"].auxiliary_payable == 90
    assert plain.by_id()["C0"].auxiliary_payable == 100


@pytest.mark.parametrize("household", (False, True))
@given(
    n=st.integers(1, 500),
    share=st.sampled_from((F(0), F(1, 4), F(1, 2), F(1))),
    charged=st.booleans(),
)
@example(n=1, share=F(1), charged=True)
@settings(
    max_examples=6, deadline=None, phases=(Phase.explicit, Phase.generate)
)
def test_outside_independence_with_nh_only_reservations(
    household, n, share, charged
):
    state, _ = state_and_members(F(4 * n, 10), F(6 * n, 10))
    members = [g.Beneficiary(name, g.Role.CHILD) for name in ("B", "C0")]
    gross = F(n, 10)
    reserve = gross * share
    plain = family(
        outcome(
            state,
            members,
            {},
            household=household,
            worker_deductions={"B": reserve},
        ),
        household,
    )
    assert plain.by_id()["B"].auxiliary_payable == gross - reserve
    assert plain.by_id()["C0"].auxiliary_payable == gross
    assert plain.by_id()["B"].counted_against_maximum == gross
    assert plain.by_id()["B"].reserved_work_deduction == reserve
    for reverse in (False, True):
        paid = family(
            outcome(
                state,
                members + [outside_member()],
                (
                    {
                        "D": g.BenefitDeduction(
                            g.DeductionReason.OWN_EARNINGS_TEST
                        )
                    }
                    if charged
                    else {}
                ),
                household=household,
                reverse=reverse,
                worker_deductions={"B": reserve},
            ),
            household,
        )
        assert subject_payments(paid) == subject_payments(plain)


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("held", (False, True))
def test_nh_only_acceptance_still_rejects_impossible_reservation(
    household, held
):
    state, _ = state_and_members(F(400), F(600))
    if held:
        state = replace(
            state, conditions={g.RecordCondition.ADMINISTRATIVE_FINALITY}
        )
    members = [g.Beneficiary(name, g.Role.CHILD) for name in ("B", "C0")]
    for outside in (False, True):
        outcomes = []
        with pytest.raises(g.InvalidFamilyInput):
            outcomes.append(
                outcome(
                    state,
                    members + ([outside_member()] if outside else []),
                    (
                        {
                            "D": g.BenefitDeduction(
                                g.DeductionReason.OWN_EARNINGS_TEST
                            )
                        }
                        if outside
                        else {}
                    ),
                    household=household,
                    worker_deductions={"B": F(201)},
                )
            )
        assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("outside_reserve", (False, True))
def test_outside_age_and_nh_reservation_do_not_trigger_subject_coverage(
    household, reverse, outside_reserve
):
    state, members = state_and_members(F(400), F(600))
    if not outside_reserve:
        members = [g.Beneficiary(name, g.Role.CHILD) for name in ("B", "C0")]
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    reserve = {} if outside_reserve else {"C0": F(10)}
    plain = family(
        outcome(
            state,
            members,
            events,
            household=household,
            worker_deductions=reserve,
        ),
        household,
    )
    paid = family(
        outcome(
            state,
            members + [outside_member()],
            events
            | {"D": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
            household=household,
            reverse=reverse,
            worker_deductions=reserve
            | ({"D": F(10)} if outside_reserve else {}),
        ),
        household,
    )
    assert subject_payments(paid) == subject_payments(plain)


@pytest.mark.parametrize("household", (False, True))
def test_subject_nh_reservation_with_subject_age_still_refuses_without_events(
    household,
):
    state, members = state_and_members(F(400), F(600))
    for outside in (False, True):
        value = outcome(
            state,
            members + ([outside_member()] if outside else []),
            {},
            household=household,
            worker_deductions={"C0": F(10)},
        )
        assert not value.supported
        assert (
            value.unsupported.reason
            is g.UnsupportedReason.DEDUCTION_AGE_WORK_INTERACTION
        )
        assert g.count_family_outcomes([value]).unsupported_weight == 7


@pytest.mark.parametrize("pia", (F(".8"), F(400)))
@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_review_outside_deduction_cannot_lower_governed_child(
    pia, household, reverse
):
    state, members = state_and_members(pia, 3 * pia / 2)
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    plain = family(
        outcome(state, members, events, household=household), household
    )
    for outside_event in (False, True):
        augmented = events | (
            {"D": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
            if outside_event
            else {}
        )
        paid = family(
            outcome(
                state,
                members + [outside_member()],
                augmented,
                household=household,
                reverse=reverse,
            ),
            household,
        )
        assert subject_payments(paid) == subject_payments(plain)
        assert paid.worker_benefit == pia
        assert paid.by_id()["B"].auxiliary_payable == 0
        assert paid.by_id()["C0"].auxiliary_payable == pia / 2
        if outside_event:
            assert paid.by_id()["D"].auxiliary_payable == 0
            assert paid.by_id()["D"].deduction == (
                F(".2") if pia == F(".8") else F(130)
            )
            assert paid.record_total == 3 * pia / 2


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_surviving_divorced_deduction_cannot_lower_governed_children(
    household, reverse
):
    state, members = state_and_members(
        F(400), F(600), survivor=True, children=3
    )
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    plain = family(
        outcome(state, members, events, household=household), household
    )
    for charged in (False, True):
        paid = family(
            outcome(
                state,
                members + [outside_member(True)],
                events
                | (
                    {
                        "D": g.BenefitDeduction(
                            g.DeductionReason.OWN_EARNINGS_TEST
                        )
                    }
                    if charged
                    else {}
                ),
                household=household,
                reverse=reverse,
            ),
            household,
        )
        assert subject_payments(paid) == subject_payments(plain)
        assert all(
            paid.by_id()[f"C{i}"].auxiliary_payable == 200 for i in range(3)
        )
        if charged:
            assert paid.record_total == 600
            assert paid.by_id()["D"].auxiliary_payable == 0


@pytest.mark.parametrize("kind", tuple(g.FamilyKind))
@pytest.mark.parametrize("household", (False, True))
@given(
    pia=st.integers(8, 1000).map(F),
    maximum_share=st.integers(6, 12).map(lambda n: F(n, 5)),
    children=st.integers(1, 3),
    reduction=st.integers(0, 60),
    permanent=st.booleans(),
    partial=st.booleans(),
)
@example(
    pia=F(400),
    maximum_share=F(3, 2),
    children=1,
    reduction=36,
    permanent=True,
    partial=False,
)
@example(
    pia=F(400),
    maximum_share=F(3, 2),
    children=3,
    reduction=36,
    permanent=True,
    partial=False,
)
@settings(
    max_examples=8, deadline=None, phases=(Phase.explicit, Phase.generate)
)
def test_outside_independence_in_any_beneficiary_order(
    kind,
    household,
    pia,
    maximum_share,
    children,
    reduction,
    permanent,
    partial,
):
    """Valid supported outside facts cannot alter governed payment rows.

    Invalid declarations and an outside event with its own named coverage
    refusal still invalidate/refuse the complete public result by design.
    """
    survivor = kind is g.FamilyKind.SURVIVOR
    state, members = state_and_members(
        pia,
        pia * maximum_share,
        survivor=survivor,
        children=children,
        reduction=reduction,
        disability=kind is g.FamilyKind.DISABILITY,
    )
    baseline = family(
        outcome(state, members, {}, household=household), household
    )
    gross = baseline.by_id()["B"].auxiliary_payable
    assume(gross > 0)
    payable = g.floor_dime(gross / 2) if partial else F(0)
    events = {
        "B": g.BenefitDeduction(
            g.DeductionReason.OWN_EARNINGS_TEST, payable, permanent
        )
    }
    plain = family(
        outcome(state, members, events, household=household), household
    )
    outside = outside_member(survivor)
    for charged in (False, True):
        augmented = events | (
            {
                "D": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F(0), permanent
                )
            }
            if charged
            else {}
        )
        for reverse in (False, True):
            paid = family(
                outcome(
                    state,
                    members + [outside],
                    augmented,
                    household=household,
                    reverse=reverse,
                ),
                household,
            )
            assert subject_payments(paid) == subject_payments(plain)
            assert not paid.by_id()["D"].subject_to_family_maximum


def zero_dual(pia, name="Z"):
    return g.Beneficiary(
        name,
        g.Role.CHILD,
        own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, pia),
    )


def competing_payments(state, members, events, *, household=False):
    """Execute A.2-first publicly and compute strict A.1 from GN .050C.

    All remaining nondeductees here are unreduced children. The strict
    reading reserves B's pre-deduction age amount; A.2-first removes Z
    before the ordinary public sole-full-permanent calculation.
    """
    ordinary = g.family_benefits(
        state, members, payment_month=MONTH, params=PARAMS, standalone=True
    )
    b = ordinary.by_id()["B"]
    assert b.auxiliary_payable > 0
    zero_ids = {
        row.beneficiary_id
        for row in ordinary.beneficiaries
        if row.subject_to_family_maximum
        and row.own_benefit is not None
        and row.auxiliary_payable == row.counted_against_maximum == 0
    }
    retained = [b for b in members if b.beneficiary_id not in zero_ids]
    a2_first = family(
        outcome(state, retained, events, household=household), household
    )
    children = [
        row
        for row in ordinary.beneficiaries
        if row.role is g.Role.CHILD and row.beneficiary_id not in zero_ids
    ]
    total_ob = sum((row.original_benefit for row in children), F(0))
    reserve = max(F(0), b.counted_against_maximum - b.auxiliary_payable)
    pool = max(F(0), ordinary.available_for_auxiliaries - reserve)
    strict = {
        row.beneficiary_id: (
            g.floor_dime(
                min(
                    row.original_benefit,
                    row.original_benefit * pool / total_ob,
                )
            )
            if ordinary.family_maximum_binding
            else row.auxiliary_payable
        )
        for row in children
    } | {"B": F(0)}
    alternative = {
        bid: a2_first.by_id()[bid].auxiliary_payable for bid in strict
    }
    return strict, alternative


@pytest.mark.parametrize("pia", (F(".8"), F(400)))
@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("marker", (False, True))
def test_review_zero_dual_composition_refuses_with_preserved_denominator(
    pia, household, reverse, marker
):
    state, members = state_and_members(pia, 3 * pia / 2)
    members += [zero_dual(pia)]
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    if marker:
        events["Z"] = g.BenefitDeduction(g.DeductionReason.DUAL_ENTITLEMENT)
    reference_events = {"B": events["B"]}
    strict, alternative = competing_payments(
        state, members, reference_events, household=household
    )
    assert strict["C0"] == (F(".3") if pia == F(".8") else F(175))
    assert alternative["C0"] == pia / 2
    value = outcome(
        state, members, events, household=household, reverse=reverse
    )
    assert not value.supported
    assert value.unsupported.reason.value == COMPOSITION
    assert g.count_family_outcomes([value]).unsupported_weight == 7


@pytest.mark.parametrize("household", (False, True))
@given(
    n=st.integers(8, 5000),
    extra=st.integers(0, 10000),
    reduction=st.integers(0, 60),
    children=st.integers(1, 3),
    zeros=st.integers(1, 3),
    reverse=st.booleans(),
)
@example(n=4000, extra=2000, reduction=36, children=1, zeros=1, reverse=False)
@example(n=4000, extra=5000, reduction=36, children=1, zeros=2, reverse=True)
@example(n=4000, extra=2000, reduction=0, children=1, zeros=3, reverse=False)
@settings(
    max_examples=12, deadline=None, phases=(Phase.explicit, Phase.generate)
)
def test_composition_refusal_exactly_matches_competing_payment_readings(
    household, n, extra, reduction, children, zeros, reverse
):
    pia, maximum = F(n, 10), F(n + extra, 10)
    state, members = state_and_members(
        pia, maximum, children=children, reduction=reduction
    )
    members += [zero_dual(pia, f"Z{i}") for i in range(zeros)]
    baseline = g.family_benefits(
        state, members, payment_month=MONTH, params=PARAMS, standalone=True
    )
    assume(baseline.by_id()["B"].auxiliary_payable > 0)
    events = {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)}
    strict, alternative = competing_payments(
        state, members, events, household=household
    )
    value = outcome(
        state, members, events, household=household, reverse=reverse
    )
    assert (not value.supported) == (strict != alternative)
    if value.supported:
        paid = family(value, household)
        assert {
            bid: paid.by_id()[bid].auxiliary_payable for bid in strict
        } == strict
    else:
        assert value.unsupported.reason.value == COMPOSITION
        assert g.count_family_outcomes([value]).unsupported_weight == 7


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize(
    "control",
    (
        "unbound",
        "unreduced",
        "partial",
        "temporary",
        "positive_dual",
        "positive_dual_with_zero",
        "nh_reservation",
        "two_events",
    ),
)
def test_composition_valid_controls_keep_computing(
    household, reverse, control
):
    state, members = state_and_members(
        F(400),
        F(900 if control == "unbound" else 600),
        reduction=0 if control in ("unreduced", "nh_reservation") else 36,
    )
    z = zero_dual(F(400))
    if control == "positive_dual":
        z = replace(
            z, own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(20))
        )
    members += [z]
    if control == "positive_dual_with_zero":
        members += [
            replace(
                z,
                beneficiary_id="P",
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.DISABILITY, F(20)),
            )
        ]
    events = {
        "B": g.BenefitDeduction(
            g.DeductionReason.OWN_EARNINGS_TEST,
            F(1) if control == "partial" else F(0),
            control != "temporary",
        )
    }
    if control == "two_events":
        events["C0"] = g.BenefitDeduction(
            g.DeductionReason.OWN_EARNINGS_TEST, F(1)
        )
    paid = family(
        outcome(
            state,
            members,
            events,
            household=household,
            reverse=reverse,
            worker_deductions=(
                {"C0": F(10)} if control == "nh_reservation" else {}
            ),
        ),
        household,
    )
    assert paid.by_id()["Z"].auxiliary_payable == (
        F("46.6") if control == "positive_dual" else 0
    )
    if control in ("unbound", "unreduced"):
        assert paid.by_id()["C0"].auxiliary_payable == 200
    if control == "positive_dual_with_zero":
        assert paid.by_id()["P"].auxiliary_payable > 0
    if control == "nh_reservation":
        assert paid.by_id()["C0"].auxiliary_payable == 190


@pytest.mark.parametrize("household", (False, True))
@pytest.mark.parametrize("reverse", (False, True))
def test_composition_agrees_when_only_counted_reservation_changes(
    household, reverse
):
    state, members = state_and_members(F(400), F(500), children=0)
    members += [zero_dual(F(400))]
    paid = family(
        outcome(
            state,
            members,
            {"B": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST)},
            household=household,
            reverse=reverse,
        ),
        household,
    )
    assert paid.family_maximum_binding
    assert paid.record_total == 400
    assert paid.by_id()["B"].counted_against_maximum == 25
    assert (
        paid.by_id()["B"].auxiliary_payable
        == paid.by_id()["Z"].auxiliary_payable
        == 0
    )


def test_composition_and_outside_rules_are_verbatim_in_hashed_captures():
    rules = {
        "poms_gn_02603_020": (
            "When any auxiliary or survivor is entitled to benefits that are not subject to the family maximum; i.e., a divorced spouse or surviving divorced spouse, consider only the auxiliaries or survivors who are subject to the maximum in calculating a benefit readjustment.",
        ),
        "poms_gn_02603_050": (
            "If a beneficiary is subject to a full permanent deduction for any reason and no other deduction is involved for any beneficiary, disregard that beneficiary when distributing the family maximum.",
            "If dual entitlement reduces a beneficiary's rate to $0.00 (technically entitled) regardless of other deductions that may apply for any other beneficiary on record disregard the dually entitled beneficiary when distributing the family maximum.",
        ),
        "poms_gn_02603_040": (
            "Deduction because of entitlement to a benefit on another record",
        ),
    }
    folder = (
        Path(__file__).with_name("data") / "track_b" / "ret_ledger_sources"
    )
    for source_id, quotes in rules.items():
        entry = next(
            row
            for row in deduction_manifest()["sources"]
            if row["id"] == source_id
        )
        raw = (folder / entry["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        for quote in quotes:
            assert quote in deduction_text(source_id)
    assert "consider only the benefit actually payable" in source_text(
        "poms_gn_02603_045"
    )
