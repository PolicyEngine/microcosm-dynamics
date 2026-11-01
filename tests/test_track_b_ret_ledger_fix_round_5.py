"""Round 5: settled facts before coverage, invented-data conformance only.

Protected rates remain counted refusals. Contradictions in settled facts
never become rows. No population, behavioral or forecast claim is admitted.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import ret_ledger as r
from populace_dynamics.track_b.ret_grace import BenefitType as T
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import (
    SOURCES,
    manifest,
    source_text,
    ssa_params,
)

PARAMS = load_ret_parameters()
FACTS = ("F1", "F2", "F3", "F4", "F5", "F6")
RC = g.RecordCondition
BC = g.BeneficiaryCondition
UR = g.UnsupportedReason
RECORD_HOLDS = (
    RC.ADMINISTRATIVE_FINALITY,
    RC.DIB_AFTER_REDUCED_RIB,
    RC.WORKERS_COMPENSATION_OFFSET,
    RC.DIB_GUARANTEE_PIA,
    RC.NON_AIME_FORMULA_PIA,
)
BENEFICIARY_HOLDS = tuple(BC)


def _person(key, kind, gross, original, month):
    return r.RETBeneficiary(
        key,
        (kind,) * 12,
        {month},
        tuple(F(gross) if m == month else F(0) for m in range(1, 13)),
        (F(original),) * 12,
        fra_month=0,
    )


def _case(fact, money=4, *, month=1, held=None, contradiction=False):
    """Keep every declaration except the selected fact consistent."""
    pia = F(money)
    if contradiction and money == 0 and fact in ("F2", "F3"):
        # The minimized review row has zero gross against a $.10 PIA.
        pia = F(1, 10)
    deceased = fact == "F6"
    disability = fact == "F2"
    kind = (
        g.FamilyKind.SURVIVOR
        if deceased
        else (
            g.FamilyKind.DISABILITY if disability else g.FamilyKind.RETIREMENT
        )
    )
    conditions = {held} if isinstance(held, RC) else set()
    state = g.RecordState(
        kind,
        pia,
        g.floor_dime(pia * (2 if deceased else F(3, 2))),
        worker=(
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia)
            if kind is g.FamilyKind.RETIREMENT
            else None
        ),
        widow_drc_savings_clause=False if deceased else None,
        conditions=conditions,
    )
    people = []
    members = []
    if not deceased:
        gross = pia
        original = pia
        if contradiction and fact == "F1":
            original += F(1, 10)
        if contradiction and fact in ("F2", "F3"):
            # Zero money still admits a rate contradiction without a
            # positive-gross/zero-original constructor contradiction.
            gross = pia - (F(1) if fact == "F3" and money else F(1, 10))
        people.append(
            _person(
                "nh", T.DIB if disability else T.RIB, gross, original, month
            )
        )
    if fact in ("F4", "F5", "F6") or isinstance(held, BC):
        role = (
            g.Role.WIDOW
            if deceased
            else (g.Role.SPOUSE if fact == "F5" else g.Role.CHILD)
        )
        own = None
        if contradiction and fact in ("F5", "F6"):
            own = g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE,
                pia / 2 if fact == "F5" else pia,
            )
        member = g.Beneficiary(
            "a",
            role,
            own_benefit=own,
            own_benefit_first=(
                True if own is not None and fact == "F5" else None
            ),
            birth_year=1950 if deceased else None,
            child_in_care=False if deceased else None,
            conditions={held} if isinstance(held, BC) else (),
        )
        members.append(member)
        original = pia if deceased else g.floor_dime(pia / 2)
        gross = F(0) if own is not None else original
        if contradiction and fact == "F4":
            original += F(1, 10)
        people.append(
            _person(
                "a",
                (
                    T.WIDOW
                    if deceased
                    else (T.SPOUSE if fact == "F5" else T.CHILD)
                ),
                gross,
                original,
                month,
            )
        )
    return r.RecordYear(
        2023 if held is BC.GOVERNMENT_PENSION_OFFSET else 2024,
        "nh",
        (
            r.RecordKind.DECEASED
            if deceased
            else (
                r.RecordKind.DISABILITY
                if disability
                else r.RecordKind.RETIREMENT
            )
        ),
        tuple(people),
        family_months={
            month: r.RETFamilyMonth(
                state,
                tuple(members),
                ssa_params(),
                {m.beneficiary_id: "h" for m in members},
            )
        },
        fiscal_year=held == "fiscal_year",
    )


def _outcome(case):
    return r.evaluate_ret(
        "round5", F(7), lambda: r.apply_ret_year(case, PARAMS)
    )


def _assert_refusal(case, reason):
    outcome = _outcome(case)
    assert not outcome.supported
    assert outcome.unsupported.reason is reason
    counts = r.count_ret_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)
    assert (g.count_family_outcomes([outcome]).rows) == 1


def _assert_invalid(case):
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(_outcome(case))
    counts = r.count_ret_outcomes(rows)
    assert (counts.rows, counts.weight) == (0, 0)


def _unsettled(fact, held):
    """The held condition's scope on the record built by ``_case``."""
    return (
        held is RC.ADMINISTRATIVE_FINALITY
        or held is BC.RATE_PROTECTED_BY_FINALITY
        and fact in ("F4", "F5", "F6")
        or held is RC.DIB_AFTER_REDUCED_RIB
        and fact == "F2"
        or held is RC.WORKERS_COMPENSATION_OFFSET
        and fact in ("F2", "F3")
    )


def _reason(held):
    if isinstance(held, RC):
        return g._RECORD_CONDITION_REASONS[held][0]
    if isinstance(held, BC):
        return g._BENEFICIARY_CONDITION_REASONS[held][0]
    return r.RETUnsupportedReason.FISCAL_YEAR


@pytest.mark.parametrize("fact", FACTS)
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize(
    "held",
    [None, RC.ADMINISTRATIVE_FINALITY, RC.NON_AIME_FORMULA_PIA, "fiscal_year"],
)
def test_each_fact_contradiction_is_classified_by_its_declared_condition(
    fact, money, held
):
    case = _case(fact, money, held=held, contradiction=True)
    if _unsettled(fact, held):
        _assert_refusal(case, _reason(held))
    else:
        _assert_invalid(case)


@pytest.mark.parametrize(
    "held,gross",
    [(RC.DIB_AFTER_REDUCED_RIB, 800), (RC.WORKERS_COMPENSATION_OFFSET, 600)],
)
def test_lawful_dib_gross_changes_remain_counted_refusals(held, gross):
    case = _case("F2", 1000, held=held)
    case = replace(
        case,
        beneficiaries=(
            replace(
                case.beneficiaries[0], gross_rates=(F(gross),) + (F(0),) * 11
            ),
        ),
    )
    _assert_refusal(case, _reason(held))


@pytest.mark.parametrize("fact", ["F3", "F4", "F6"])
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize(
    "held",
    [
        RC.ADMINISTRATIVE_FINALITY,
        RC.NON_AIME_FORMULA_PIA,
        BC.ENTITLED_ON_ANOTHER_RECORD,
        "fiscal_year",
    ],
)
def test_review_counterexamples_follow_finality_ruling(fact, money, held):
    case = _case(fact, money, held=held, contradiction=True)
    if held is RC.ADMINISTRATIVE_FINALITY:
        _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)
    else:
        _assert_invalid(case)


@pytest.mark.parametrize("fact", ["F4", "F5", "F6"])
def test_beneficiary_finality_protects_its_own_unsettled_fact(fact):
    _assert_refusal(
        _case(fact, held=BC.RATE_PROTECTED_BY_FINALITY, contradiction=True),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("fact", ["F1", "F3"])
def test_one_beneficiary_finality_does_not_protect_the_nh(fact):
    _assert_invalid(
        _case(fact, held=BC.RATE_PROTECTED_BY_FINALITY, contradiction=True)
    )


def test_first_administrative_finality_example_keeps_nh_rate():
    case = _case("F4", 750, held=RC.ADMINISTRATIVE_FINALITY)
    context = case.family_months[1]
    case = replace(
        case,
        beneficiaries=(
            replace(
                case.beneficiaries[0],
                gross_rates=(F(1000),) + (F(0),) * 11,
                original_rates=(F(1000),) * 12,
            ),
            replace(
                case.beneficiaries[1],
                gross_rates=(F("375.50"),) + (F(0),) * 11,
                original_rates=(F("375.50"),) * 12,
            ),
        ),
        family_months={
            1: replace(
                context,
                state=replace(context.state, family_maximum=F("1312.50")),
            )
        },
    )
    _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)


def test_second_administrative_finality_example_keeps_two_protected_rates():
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(750),
        F("1312.50"),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(750)),
        conditions={RC.ADMINISTRATIVE_FINALITY},
    )
    members = (
        g.Beneficiary(
            "old", g.Role.CHILD, conditions={BC.RATE_PROTECTED_BY_FINALITY}
        ),
        g.Beneficiary("new", g.Role.CHILD),
    )
    case = r.RecordYear(
        2024,
        "nh",
        beneficiaries=(
            _person("nh", T.RIB, 1000, 1000, 1),
            _person("old", T.CHILD, 375, 500, 1),
            _person("new", T.CHILD, F("281.20"), 375, 1),
        ),
        family_months={
            1: r.RETFamilyMonth(
                state, members, ssa_params(), {"old": "h", "new": "h"}
            )
        },
        family_maximum_binding_months={1},
    )
    _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)


def test_finality_examples_are_verbatim_and_the_capture_hash_matches():
    source_id = "poms_rs_00615_754"
    entry = next(
        row for row in manifest()["sources"] if row["id"] == source_id
    )
    assert (
        hashlib.sha256((SOURCES / entry["file"]).read_bytes()).hexdigest()
        == entry["sha256"]
    )
    text = source_text(source_id)
    quotes = (
        "the correct PIA is really $750.00 with a maximum of $1,312.50.",
        "the rate to the NH is protected by administrative finality and cannot be changed.",
        "to show the PIA and maximum used to arrive at those rates.",
        "The rates payable will then be $1,000.00 to the NH and $375.50 to the new child.",
        "The total payable to the family will then be $1,375.50",
        "the rates to the NH and the first child are protected by administrative finality and must be based on the protected PIA and maximum.",
        "$1,750 minus $1,000 is $750 divided by 2 or $375.00.",
        "We divide that by the number of children (2) and get $281.20 as the correct rate for the new child.",
        "$1,000.00 to the NH, $375.00 to the first child and $281.20 to the new child.",
        "The total payable to the family will then be $1,656.20",
    )
    for quote in quotes:
        assert quote in text
    # These are the published declarations, preserved as refusals; the
    # capture's $375.50 is not silently replaced by half of $750.
    assert F(1000) + F("375.50") == F("1375.50")
    assert F(1000) + F(375) + F("281.20") == F("1656.20")


def test_fact_table_explicitly_covers_all_conditions_and_held_g_reasons():
    table = g._PREFLIGHT_FACT_UNSETTLERS
    assert set(table) == set(RC) | set(BC) | set(UR)
    assert all(
        type(facts) is frozenset and facts <= set(FACTS)
        for facts in table.values()
    )
    for held in (*RECORD_HOLDS, *BENEFICIARY_HOLDS):
        expected = (
            frozenset({"F4"})
            if held is BC.WIDOW_DRC_SAVINGS_CLAUSE
            else frozenset(fact for fact in FACTS if _unsettled(fact, held))
        )
        assert table[held] == expected


def test_spouse_sequence_condition_does_not_unsettle_other_own_eligibility():
    _assert_invalid(
        _case(
            "F6",
            held=BC.DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB,
            contradiction=True,
        )
    )


@settings(max_examples=90, deadline=None)
@given(
    fact=st.sampled_from(FACTS),
    held=st.sampled_from((*RECORD_HOLDS, *BENEFICIARY_HOLDS, "fiscal_year")),
    money=st.integers(0, 30).map(lambda n: n * 4),
    month=st.integers(1, 12),
)
@example(fact="F2", held=RC.DIB_AFTER_REDUCED_RIB, money=4, month=12)
@example(fact="F3", held=RC.WORKERS_COMPENSATION_OFFSET, money=4, month=1)
@example(fact="F4", held=BC.RATE_PROTECTED_BY_FINALITY, money=0, month=6)
@example(fact="F1", held=RC.NON_AIME_FORMULA_PIA, money=4, month=1)
@example(fact="F4", held=BC.WIDOW_DRC_SAVINGS_CLAUSE, money=4, month=12)
@example(
    fact="F6",
    held=BC.DIB_BETWEEN_SPOUSE_BENEFIT_AND_RIB,
    money=4,
    month=1,
)
def test_held_against_unheld_fact_classification(fact, held, money, month):
    _assert_invalid(_case(fact, money, month=month, contradiction=True))
    held_case = _case(fact, money, month=month, held=held, contradiction=True)
    if _unsettled(fact, held):
        _assert_refusal(held_case, _reason(held))
    else:
        _assert_invalid(held_case)


@settings(max_examples=70, deadline=None)
@given(
    fact=st.sampled_from(FACTS),
    held=st.sampled_from(
        (None, *RECORD_HOLDS, *BENEFICIARY_HOLDS, "fiscal_year")
    ),
    money=st.integers(0, 30).map(lambda n: n * 4),
    month=st.integers(1, 12),
)
def test_matching_declarations_never_raise_input_errors(
    fact, held, money, month
):
    outcome = _outcome(_case(fact, money, month=month, held=held))
    counts = r.count_ret_outcomes([outcome])
    assert (counts.rows, counts.weight) == (1, 7)
    assert outcome.supported == (held is None)
    if held is not None:
        assert outcome.unsupported.reason is _reason(held)


@pytest.mark.parametrize("fact", FACTS)
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("contradiction", [False, True])
def test_wep_declaration_alone_changes_none_of_the_six_facts(
    fact, money, contradiction
):
    case = _case(fact, money, contradiction=contradiction)
    context = case.family_months[1]
    state = replace(
        context.state, conditions={RC.WINDFALL_ELIMINATION_PROVISION}
    )
    case = replace(case, family_months={1: replace(context, state=state)})
    if contradiction:
        _assert_invalid(case)
        return
    outcome = _outcome(case)
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7


@pytest.mark.parametrize("money", [0, 4])
def test_worker_not_entitled_declares_an_ieds_record_without_nh_rate(money):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(money),
        F(3 * money, 2),
        conditions={RC.WORKER_NOT_ENTITLED},
    )
    member = g.Beneficiary(
        "a",
        g.Role.DIVORCED_SPOUSE,
        child_in_care=False,
        first_entitlement_child_in_care=False,
    )
    case = r.RecordYear(
        2024,
        "nh",
        beneficiaries=(
            replace(_person("nh", T.RIB, 0, money, 1), entitled_months=()),
            _person("a", T.DIVORCED_SPOUSE, F(money, 2), F(money, 2), 1),
        ),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"a": "h"})
        },
    )
    outcome = _outcome(case)
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7


@pytest.mark.parametrize("fact", ["F4", "F5"])
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("wep", [False, True])
def test_ieds_does_not_mask_settled_auxiliary_facts(fact, money, wep):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(money),
        F(3 * money, 2),
        conditions={RC.WORKER_NOT_ENTITLED}
        | ({RC.WINDFALL_ELIMINATION_PROVISION} if wep else set()),
    )
    own = (
        g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(money, 2))
        if fact == "F5"
        else None
    )
    member = g.Beneficiary(
        "a",
        g.Role.DIVORCED_SPOUSE,
        own_benefit=own,
        own_benefit_first=True if own else None,
        child_in_care=False,
        first_entitlement_child_in_care=False,
    )
    original = F(money, 2) + (F(1, 10) if fact == "F4" else 0)
    case = r.RecordYear(
        2023,
        "nh",
        beneficiaries=(
            replace(_person("nh", T.RIB, 0, money, 1), entitled_months=()),
            _person(
                "a", T.DIVORCED_SPOUSE, 0 if own else F(money, 2), original, 1
            ),
        ),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"a": "h"})
        },
    )
    _assert_invalid(case)


def test_implicit_widow_history_remains_unsettled_behind_explicit_hold():
    case = _case("F6", held=BC.ENTITLED_ON_ANOTHER_RECORD, contradiction=True)
    context = case.family_months[1]
    member = replace(context.beneficiaries[0], birth_year=1920)
    case = replace(
        case, family_months={1: replace(context, beneficiaries=(member,))}
    )
    _assert_refusal(case, UR.COMBINED_FAMILY_MAXIMUM)


@settings(max_examples=60, deadline=None)
@given(
    fact=st.sampled_from(FACTS),
    held=st.sampled_from(
        (None, *RECORD_HOLDS, *BENEFICIARY_HOLDS, "fiscal_year")
    ),
    money=st.integers(0, 15).map(lambda n: n * 4),
    month=st.integers(1, 12),
)
def test_preflight_changes_no_valid_outcome_or_refusal(
    fact, held, money, month
):
    case = _case(fact, money, month=month, held=held)
    actual = _outcome(case)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(r, "_check_settled_family_facts", lambda record: None)
        without = _outcome(case)
    assert actual.supported == without.supported
    if actual.supported:
        assert actual.ledger == without.ledger
    else:
        assert actual.unsupported.reason is without.unsupported.reason
        assert actual.unsupported.detail == without.unsupported.detail
    assert r.count_ret_outcomes([actual]) == r.count_ret_outcomes([without])


def test_historical_rib_gross_rule_refusal_leaves_original_reason():
    case = _case("F3", contradiction=True)
    context = case.family_months[1]
    state = replace(
        context.state,
        worker=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(4), reduction_months=1, birth_year=1915
        ),
    )
    case = replace(case, family_months={1: replace(context, state=state)})
    _assert_refusal(case, UR.OWN_RIB_HISTORY_BEFORE_1978)


def test_two_declared_conditions_preserve_finality_protection():
    case = _case("F1", held=RC.NON_AIME_FORMULA_PIA, contradiction=True)
    context = case.family_months[1]
    state = replace(
        context.state,
        conditions={RC.NON_AIME_FORMULA_PIA, RC.ADMINISTRATIVE_FINALITY},
    )
    _assert_refusal(
        replace(case, family_months={1: replace(context, state=state)}),
        UR.ADMINISTRATIVE_FINALITY,
    )


@pytest.mark.parametrize("contradiction_in_unprotected_month", [False, True])
def test_finality_is_resolved_for_each_month(
    contradiction_in_unprotected_month,
):
    first = _case("F1", held=RC.ADMINISTRATIVE_FINALITY, contradiction=True)
    second = _case(
        "F1", month=2, contradiction=contradiction_in_unprotected_month
    )
    rates = list(first.beneficiaries[0].original_rates)
    rates[1] = second.beneficiaries[0].original_rates[1]
    person = replace(
        first.beneficiaries[0],
        entitled_months={1, 2},
        gross_rates=(F(4), F(4)) + (F(0),) * 10,
        original_rates=tuple(rates),
    )
    case = replace(
        first,
        beneficiaries=(person,),
        family_months={**first.family_months, **second.family_months},
    )
    if contradiction_in_unprotected_month:
        _assert_invalid(case)
    else:
        _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)


def test_protected_auxiliary_does_not_protect_another_auxiliary():
    case = _case("F4", held=BC.RATE_PROTECTED_BY_FINALITY, contradiction=True)
    context = case.family_months[1]
    other = g.Beneficiary("other", g.Role.CHILD)
    state = replace(context.state, family_maximum=F(8))
    case = replace(
        case,
        beneficiaries=case.beneficiaries
        + (_person("other", T.CHILD, 2, F("2.10"), 1),),
        family_months={
            1: r.RETFamilyMonth(
                state,
                context.beneficiaries + (other,),
                context.params,
                {"a": "h", "other": "h"},
            )
        },
    )
    _assert_invalid(case)


@pytest.mark.parametrize(
    "fact,helper",
    [
        ("F3", "_own_monthly_benefit_validated"),
        ("F4", "_original_benefit_validated"),
    ],
)
def test_canonical_input_error_is_never_caught_as_a_coverage_refusal(
    monkeypatch, fact, helper
):
    case = _case(fact, held=RC.NON_AIME_FORMULA_PIA)

    def invalid_rule(*args, **kwargs):
        raise g.InvalidFamilyInput("canonical fact rule rejected the input")

    monkeypatch.setattr(g, helper, invalid_rule)
    with pytest.raises(
        g.InvalidFamilyInput, match="canonical fact rule rejected"
    ):
        _outcome(case)


@pytest.mark.parametrize(
    "role,kind",
    [(g.Role.WIDOW, T.WIDOW), (g.Role.MOTHER_FATHER, T.MOTHER_FATHER)],
)
@pytest.mark.parametrize(
    "held", [None, RC.NON_AIME_FORMULA_PIA, RC.ADMINISTRATIVE_FINALITY]
)
def test_other_own_entitlement_uses_real_reduced_monthly_benefit(
    role, kind, held
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(20), F(40), widow_drc_savings_clause=False
    )
    member = g.Beneficiary(
        "a",
        role,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE,
            F(20 if role is g.Role.WIDOW else 19),
            reduction_months=48,
            birth_year=1950,
        ),
        birth_year=1950,
        child_in_care=False if role is g.Role.WIDOW else None,
    )
    baseline = g.family_benefits(
        state,
        (member,),
        payment_month=g.YearMonth(2024, 1),
        params=ssa_params(),
        standalone=True,
    )
    row = baseline.by_id()["a"]
    assert row.entitled
    assert row.own_benefit == (15 if role is g.Role.WIDOW else F("14.20"))
    state = replace(state, conditions={held} if held else ())
    case = r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DECEASED,
        (_person("a", kind, row.auxiliary_payable, row.original_benefit, 1),),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"a": "h"})
        },
    )
    outcome = _outcome(case)
    assert r.count_ret_outcomes([outcome]).weight == 7
    assert outcome.supported == (held is None)
    if held:
        assert outcome.unsupported.reason is _reason(held)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize(
    "protection", [RC.ADMINISTRATIVE_FINALITY, BC.RATE_PROTECTED_BY_FINALITY]
)
@pytest.mark.parametrize(
    "payable,reserved",
    [(F(375), F(0)), (F(400), F(0)), (F(200), F(200)), (F(0), F(400))],
)
def test_protected_deduction_rate_is_not_bounded_by_correct_pia_ob(
    household, protection, payable, reserved
):
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(750),
        F("1312.50"),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(750)),
        conditions={protection} if isinstance(protection, RC) else (),
    )
    member = g.Beneficiary(
        "c",
        g.Role.CHILD,
        conditions={protection} if isinstance(protection, BC) else (),
    )
    deductions = {
        "c": g.BenefitDeduction(g.DeductionReason.OWN_EARNINGS_TEST, payable)
    }
    kwargs = dict(
        payment_month=g.YearMonth(2024, 1),
        params=ssa_params(),
        deductions=deductions,
        households={"c": "h"},
        worker_deductions={"c": reserved},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, (member,))}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, (member,), standalone=True, **kwargs
        )

    outcome = g.evaluate_family("protected-deduction", 7, compute)
    assert outcome.unsupported.reason is UR.ADMINISTRATIVE_FINALITY
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@pytest.mark.parametrize("household", [False, True])
def test_disqualified_widow_does_not_unsettle_a_child_original_benefit(
    household,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(4), F(6), eligibility_year=2020
    )
    members = (
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=1950,
            original_benefit_basis=F(8),
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(8)),
            child_in_care=False,
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )
    baseline = g.family_benefits(
        state,
        members,
        payment_month=g.YearMonth(2024, 1),
        params=ssa_params(),
        standalone=True,
    )
    assert not baseline.by_id()["w"].entitled
    assert baseline.by_id()["c"].original_benefit == 3
    kwargs = dict(
        payment_month=g.YearMonth(2024, 1),
        params=ssa_params(),
        deductions={
            "c": g.BenefitDeduction(
                g.DeductionReason.OWN_EARNINGS_TEST, F("3.10")
            )
        },
        households={"w": "h", "c": "h"},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, members)}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, members, standalone=True, **kwargs
        )

    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(g.evaluate_family("settled-child", 7, compute))
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.weight) == (0, 0)


@pytest.mark.parametrize(
    "path", ["ret", "deduction", "deduction_disqualified_widow"]
)
def test_unrelated_refused_child_does_not_invent_widow_protection(path):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(4), F(8), eligibility_year=2024
    )
    members = (
        g.Beneficiary(
            "a",
            g.Role.CHILD,
            own_benefit=g.OwnBenefit(
                g.OwnBenefitKind.DISABILITY, F(1), reduction_months=1
            ),
        ),
        g.Beneficiary("b", g.Role.CHILD),
    )
    if path == "deduction_disqualified_widow":
        members += (
            g.Beneficiary(
                "w",
                g.Role.WIDOW,
                birth_year=1950,
                original_benefit_basis=F(5),
                own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(5)),
                child_in_care=False,
            ),
        )
    if path == "ret":
        case = r.RecordYear(
            2024,
            "nh",
            r.RecordKind.DECEASED,
            (
                _person("a", T.CHILD, 0, 3, 1),
                _person("b", T.CHILD, 3, F("3.10"), 1),
            ),
            family_months={
                1: r.RETFamilyMonth(
                    state, members, ssa_params(), {"a": "h", "b": "h"}
                )
            },
        )
        _assert_invalid(case)
        return

    def compute():
        return g.family_benefits_after_deductions(
            state,
            members,
            payment_month=g.YearMonth(2024, 1),
            params=ssa_params(),
            standalone=True,
            households={member.beneficiary_id: "h" for member in members},
            deductions={
                "b": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F("3.10")
                )
            },
        )

    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(g.evaluate_family("no-widow", 7, compute))
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.weight) == (0, 0)


@pytest.mark.parametrize(
    "held", [None, RC.NON_AIME_FORMULA_PIA, RC.ADMINISTRATIVE_FINALITY]
)
def test_widow_own_cohort_alone_matches_the_resolved_cohort_control(held):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        widow_drc_savings_clause=False,
        conditions={held} if held else (),
    )
    member = g.Beneficiary(
        "w",
        g.Role.WIDOW,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(1), birth_year=1950
        ),
        child_in_care=False,
    )
    case = r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DECEASED,
        (_person("w", T.WIDOW, 3, 4, 1),),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"w": "h"})
        },
    )
    outcome = _outcome(case)
    context = case.family_months[1]
    control = _outcome(
        replace(
            case,
            family_months={
                1: replace(
                    context, beneficiaries=(replace(member, birth_year=1950),)
                )
            },
        )
    )
    assert outcome.supported == control.supported == (held is None)
    assert r.count_ret_outcomes([outcome]).weight == 7
    if held:
        assert (
            outcome.unsupported.reason
            is control.unsupported.reason
            is _reason(held)
        )
    else:
        assert outcome.ledger == control.ledger


def test_auxiliary_cohort_supplies_own_rib_historical_refusal():
    state = g.RecordState(
        g.FamilyKind.SURVIVOR, F(4), F(8), widow_drc_savings_clause=False
    )
    member = g.Beneficiary(
        "a",
        g.Role.MOTHER_FATHER,
        birth_year=1915,
        own_benefit=g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE, F(4), reduction_months=1
        ),
    )
    case = r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DECEASED,
        (_person("a", T.MOTHER_FATHER, 0, 3, 1),),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"a": "h"})
        },
    )
    _assert_refusal(case, UR.OWN_RIB_HISTORY_BEFORE_1978)


_FACT_TABLE_QUOTES = (
    (
        "tests/data/track_b/ret_ledger_sources/poms_rs_02501_110.html",
        "their original benefit is equal to 100% of the PIA",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_101.html",
        "The MBA is equal to the PIA reduced by 5/9 of 1%",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "the rate to the NH is protected by administrative finality and cannot be changed",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "the PIA and maximum used to arrive at those rates",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "the protected PIA and maximum",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/ssa_act_202_215_excerpts.txt",
        "such disability insurance benefit for each month shall be reduced by the amount such old-age insurance benefit would be reduced",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/ssa_act_202_215_excerpts.txt",
        "after any reduction under sections 203(a) and 224",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_gn_02603_050.html",
        "Workers’ compensation (WC) or public disability benefit (PDB) offset amount",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_736.html",
        "To establish a family maximum for a DIB Guarantee PIA",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_740.html",
        "The PIA is an AIME, OS, Special Minimum or Frozen Minimum PIA.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_740.html",
        "determining the total amount of the family maximum benefit",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00202_100.html",
        "the NH is eligible but has not filed for benefits",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00202_100.html",
        "is subject to the number holder’s (NH) WEP PIA although the NH is not yet entitled",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "which rates are protected by administrative finality",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_712.html",
        "beneficiaries who were entitled for the month of 5/78",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_712.html",
        "the child is protected by the savings clause and the child's rate will remain at $300",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_770.html",
        "Maximums from all SSNs that the child is entitled on may be combined on the SSN where payment is actually made.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_684.html",
        "The deemed or putative spouse and all other beneficiaries on the record are reduced for the maximum.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_684.html",
        "the legal spouse is paid outside the family maximum",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_684.html",
        "the legal spouse will receive the OB",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_gn_02608_100.html",
        "a reduction of spouse's benefits due to the receipt of a federal, state, or local government pension",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_gn_02608_100.html",
        "proven his or her rights to them for a given period",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_260.html",
        "Reduce the spouse's reduced benefit further by the amount of the RIB reduction.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_005.html",
        "all cases involving single entitlement to actuarially reduced benefits prior to 1/78",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_692.html",
        "Before 01/02/17",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_692.html",
        "1/12%",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_101.html",
        "Round the result down to the next dime for benefits after 5/82 and up to the next dime for benefits prior to 6/82.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_740.html",
        "The NH was ever entitled to DIB before July 1980",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00209_001.html",
        "equal to or exceeding the amount of the parent's original benefit (One parent = 82 1/2%; Two parents = 75%)",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00209_015.html",
        "Benefit rate equals 75% of the worker's PIA for each month both are entitled.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_310.html",
        "Determine the WIB OB",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_020.html",
        "First benefit calculated independently",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_315.html",
        "if all eligibility requirements are met",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_766.html",
        "after reduction for the maximum",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_768.html",
        "Beneficiaries will still be limited by the original benefit amount.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_340.html",
        "receiving a reduced widow(er) benefit",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_340.html",
        "The benefit amount is raised for all months the child is in care.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00630_400.html",
        "Any person's benefit may not exceed the original benefit (OB)",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00630_400.html",
        "the new PIA in a life case",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_320.html",
        "deductions",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "the correct PIA is really $750.00",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_754.html",
        "cannot be changed",
    ),
)


def test_fact_table_source_quotations_and_capture_hashes():
    root = Path(__file__).resolve().parents[1]
    manifests = {}
    for relative, quote in _FACT_TABLE_QUOTES:
        capture = root / relative
        if capture.parent not in manifests:
            manifests[capture.parent] = json.loads(
                (capture.parent / "manifest.json").read_text()
            )["sources"]
        entry = next(
            row
            for row in manifests[capture.parent]
            if row["file"] == capture.name
        )
        raw = capture.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        text = raw.decode()
        if capture.suffix == ".html":
            text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", html.unescape(text))
        assert quote in text


@pytest.mark.parametrize("path", ["ret", "deduction"])
@pytest.mark.parametrize("basis", [F(5), None])
@pytest.mark.parametrize("history", [None, False])
def test_protected_widow_cannot_be_excluded_from_unknown_drc_history(
    path, basis, history
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        eligibility_year=2024,
        widow_drc_savings_clause=history,
    )
    members = (
        g.Beneficiary(
            "w",
            g.Role.WIDOW,
            birth_year=1950,
            original_benefit_basis=basis,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(5)),
            child_in_care=False,
            conditions={BC.RATE_PROTECTED_BY_FINALITY},
        ),
        g.Beneficiary("c", g.Role.CHILD),
    )
    if path == "ret":
        case = r.RecordYear(
            2024,
            "nh",
            r.RecordKind.DECEASED,
            (
                _person("w", T.WIDOW, 0, 5, 1),
                _person("c", T.CHILD, 3, F("3.10"), 1),
            ),
            family_months={
                1: r.RETFamilyMonth(
                    state, members, ssa_params(), {"w": "h", "c": "h"}
                )
            },
        )
        if history is False:
            _assert_invalid(case)
        else:
            _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)
        return

    def compute():
        return g.family_benefits_after_deductions(
            state,
            members,
            payment_month=g.YearMonth(2024, 1),
            params=ssa_params(),
            standalone=True,
            deductions={
                "c": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F("3.10")
                )
            },
            households={"w": "h", "c": "h"},
        )

    if history is False:
        rows = []
        with pytest.raises(g.InvalidFamilyInput):
            rows.append(g.evaluate_family("settled-history", 7, compute))
        counts = g.count_family_outcomes(rows)
        assert (counts.rows, counts.weight) == (0, 0)
        return
    outcome = g.evaluate_family(
        "protected-widow-history",
        7,
        compute,
    )
    assert outcome.unsupported.reason is UR.ADMINISTRATIVE_FINALITY
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@pytest.mark.parametrize(
    "held", [None, RC.NON_AIME_FORMULA_PIA, RC.ADMINISTRATIVE_FINALITY]
)
def test_missing_both_widow_cohorts_remains_canonical_input_error(held):
    case = _case("F6", held=held, contradiction=True)
    context = case.family_months[1]
    member = replace(context.beneficiaries[0], birth_year=None)
    case = replace(
        case, family_months={1: replace(context, beneficiaries=(member,))}
    )
    rows = []
    with pytest.raises(g.InvalidFamilyInput, match="needs birth_year"):
        rows.append(_outcome(case))
    counts = r.count_ret_outcomes(rows)
    assert (counts.rows, counts.weight) == (0, 0)


@pytest.mark.parametrize("cohort", [1920, 1928])
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("held", [None, BC.ENTITLED_ON_ANOTHER_RECORD])
def test_aged_widow_sequence_refusal_only_unsettles_possible_carryover(
    cohort, money, held
):
    case = _case("F6", money, held=held, contradiction=True)
    context = case.family_months[1]
    member = replace(context.beneficiaries[0], birth_year=cohort)
    case = replace(
        case, family_months={1: replace(context, beneficiaries=(member,))}
    )
    if cohort < 1928 and money > 0:
        _assert_refusal(
            case,
            (
                UR.COMBINED_FAMILY_MAXIMUM
                if held
                else UR.DUAL_ENTITLEMENT_SEQUENCE
            ),
        )
    else:
        _assert_invalid(case)


@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize(
    "held",
    [
        None,
        RC.NON_AIME_FORMULA_PIA,
        RC.ADMINISTRATIVE_FINALITY,
        BC.ENTITLED_ON_ANOTHER_RECORD,
    ],
)
def test_modern_disabled_widow_own_rib_eligibility_is_settled(money, held):
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        F(money),
        reduction_months=12,
        birth_year=1950,
    )
    own_mba = g.own_monthly_benefit(own, ssa_params())[1]
    assert own_mba == (F("3.70") if money else 0)
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        own_mba,
        2 * own_mba,
        widow_drc_savings_clause=False,
        conditions={held} if isinstance(held, RC) else (),
    )
    member = g.Beneficiary(
        "w",
        g.Role.DISABLED_WIDOW,
        birth_year=1950,
        own_benefit=own,
        child_in_care=False,
        conditions={held} if isinstance(held, BC) else (),
    )
    case = r.RecordYear(
        2015,
        "nh",
        r.RecordKind.DECEASED,
        (replace(_person("w", T.DWB, 0, own_mba, 6), fra_month=None),),
        family_months={
            6: r.RETFamilyMonth(state, (member,), ssa_params(), {"w": "h"})
        },
    )
    if held is RC.ADMINISTRATIVE_FINALITY:
        _assert_refusal(case, UR.ADMINISTRATIVE_FINALITY)
    else:
        _assert_invalid(case)


def test_eligible_disabled_widow_retains_own_sequence_refusal():
    own = g.OwnBenefit(
        g.OwnBenefitKind.OLD_AGE,
        F(4),
        reduction_months=12,
        birth_year=1950,
    )
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        widow_drc_savings_clause=False,
    )
    member = g.Beneficiary(
        "w",
        g.Role.DISABLED_WIDOW,
        birth_year=1950,
        own_benefit=own,
        child_in_care=False,
    )
    case = r.RecordYear(
        2015,
        "nh",
        r.RecordKind.DECEASED,
        (replace(_person("w", T.DWB, 0, 4, 6), fra_month=None),),
        family_months={
            6: r.RETFamilyMonth(state, (member,), ssa_params(), {"w": "h"})
        },
    )
    _assert_refusal(case, UR.DUAL_ENTITLEMENT_SEQUENCE)


_FACT_TABLE_QUOTES += (
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_005.html",
        "Eliminated the carry-over reduction in RIB or DIB due to WIB before age 62.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_005.html",
        "This applies to RIB for workers born 1/2/28 or later",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_010.html",
        "RIB After Reduced WIB (D then A) with date of birth of 1/2/1928 or later Reduce the RIB in the usual manner without regard to the WIB",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_010.html",
        "RIB After Reduced WIB (D then A) with date of birth before 1/2/1928 If there was prior entitlement to a reduced WIB in any month before the month of attainment of age 62 reduce the RIB",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_315.html",
        "When an eligible person elects to switch from WIB to DWB or DWB to WIB the PIA and the reduction factors remain the same.",
    ),
)


@pytest.mark.parametrize("year", [1973, 2024])
@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
def test_legacy_widow_later_payment_gross_retains_eligibility_refusal(
    year, household, event
):
    _legacy_widow_gross_refusal(year, household, event, deferred=False)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
@pytest.mark.parametrize(
    "reason",
    [UR.ELIGIBILITY_BEFORE_1983, UR.DI_ENTITLEMENT_BEFORE_JULY_1980],
)
def test_deferred_legacy_eligibility_gross_retains_its_original_refusal(
    household, event, reason
):
    _legacy_widow_gross_refusal(
        2024, household, event, deferred=True, reason=reason
    )


def _legacy_widow_gross_refusal(
    year, household, event, *, deferred, reason=UR.ELIGIBILITY_BEFORE_1983
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        eligibility_year=None if deferred else 1972,
        deferred_refusal=(reason, "legacy eligibility") if deferred else None,
        widow_drc_savings_clause=False,
    )
    members = (
        g.Beneficiary("w", g.Role.WIDOW, birth_year=1910, child_in_care=False),
    )
    kwargs = dict(
        payment_month=g.YearMonth(year, 1),
        params=ssa_params(),
        deductions=(
            {
                "w": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F("4.10")
                )
            }
            if event == "payable"
            else {}
        ),
        worker_deductions={"w": F("4.10")} if event == "reservation" else {},
        households={"w": "h"},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, members)}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, members, standalone=True, **kwargs
        )

    outcome = g.evaluate_family("legacy-widow-gross", 7, compute)
    assert outcome.unsupported.reason is reason
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
def test_old_first_dib_history_does_not_unsettle_current_child_upper_bound(
    household, event
):
    state = g.RecordState(
        g.FamilyKind.DISABILITY,
        F(4),
        F(8),
        eligibility_year=2024,
        first_dib_entitlement=g.YearMonth(1979, 1),
    )
    members = (g.Beneficiary("c", g.Role.CHILD),)
    kwargs = dict(
        payment_month=g.YearMonth(2024, 1),
        params=ssa_params(),
        deductions=(
            {
                "c": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, F("2.10")
                )
            }
            if event == "payable"
            else {}
        ),
        worker_deductions={"c": F("2.10")} if event == "reservation" else {},
        households={"c": "h"},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, members)}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, members, standalone=True, **kwargs
        )

    _assert_no_family_row(compute)


_FACT_TABLE_QUOTES += (
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_010.html",
        "Sole Surviving Widow(er) $84.50 reduced for months of entitlement, if any, prior to age 62 or, if higher, the WIB computed without regard to this sole survivor's provision",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_010.html",
        "The sole survivor's rate was eliminated when NH died after 1981 and was not eligible for RIB or DIB",
    ),
)


def _historical_child_uncertainty_case(year, *, scale=0, month=1):
    pia = F(2 * scale + 1, 10)
    current_ob = g.original_benefit(g.Role.CHILD, g.FamilyKind.RETIREMENT, pia)
    declared = current_ob + F(1, 10)
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        2 * pia,
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia, birth_year=1910),
        eligibility_year=1972,
    )
    member = g.Beneficiary("c", g.Role.CHILD)
    return r.RecordYear(
        year,
        "nh",
        beneficiaries=(
            _person("nh", T.RIB, pia, pia, month),
            replace(
                _person("c", T.CHILD, declared, declared, month),
                fra_month=None,
            ),
        ),
        family_months={
            month: r.RETFamilyMonth(state, (member,), ssa_params(), {"c": "h"})
        },
    )


@pytest.mark.parametrize("year", [1981, 1983])
def test_child_ob_uncertainty_is_limited_to_pre1983_payment_months(year):
    case = _historical_child_uncertainty_case(year)
    if year < 1983:
        _assert_refusal(case, UR.ELIGIBILITY_BEFORE_1983)
    else:
        _assert_invalid(case)


@settings(max_examples=40, deadline=None)
@given(scale=st.integers(0, 10), month=st.integers(1, 12))
@example(scale=0, month=1)
@example(scale=10, month=12)
def test_child_ob_uncertainty_preserves_old_refusals_for_odd_dime_pias(
    scale, month
):
    _assert_refusal(
        _historical_child_uncertainty_case(1981, scale=scale, month=month),
        UR.ELIGIBILITY_BEFORE_1983,
    )
    _assert_invalid(
        _historical_child_uncertainty_case(1983, scale=scale, month=month)
    )


def _historical_widow_gross_uncertainty_computation(
    household,
    event,
    *,
    scale=1,
    month=1,
    year=1972,
    amount=None,
    finality=False,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4 * scale),
        F(8 * scale),
        eligibility_year=None if finality else 1972,
        widow_drc_savings_clause=False,
        conditions={RC.ADMINISTRATIVE_FINALITY} if finality else (),
    )
    members = (
        g.Beneficiary("w", g.Role.WIDOW, birth_year=1910, child_in_care=False),
    )
    if amount is None:
        amount = F(4 * scale) + F(1, 10)
    kwargs = dict(
        payment_month=g.YearMonth(year, month),
        params=ssa_params(),
        deductions=(
            {
                "w": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, amount
                )
            }
            if event == "payable"
            else {}
        ),
        worker_deductions={"w": amount} if event == "reservation" else {},
        households={"w": "h"},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, members)}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, members, standalone=True, **kwargs
        )

    return compute


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
@pytest.mark.parametrize("zero", [False, True])
def test_historical_widow_gross_uncertainty_retains_original_refusal(
    household, event, zero
):
    compute = _historical_widow_gross_uncertainty_computation(
        household, event, amount=F(0) if zero else None
    )
    outcome = g.evaluate_family("zero-historical-widow", 7, compute)
    assert outcome.unsupported.reason is UR.ELIGIBILITY_BEFORE_1983
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
def test_historical_widow_finality_keeps_its_original_refusal(
    household, event
):
    outcome = g.evaluate_family(
        "protected-historical-widow",
        7,
        _historical_widow_gross_uncertainty_computation(
            household, event, finality=True
        ),
    )
    assert outcome.unsupported.reason is UR.ADMINISTRATIVE_FINALITY
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@settings(max_examples=40, deadline=None)
@given(
    year=st.sampled_from((1972, 1973, 2024)),
    scale=st.integers(1, 10),
    month=st.integers(1, 12),
    household=st.booleans(),
    event=st.sampled_from(("payable", "reservation")),
)
@example(year=1972, scale=1, month=1, household=False, event="payable")
@example(year=1973, scale=1, month=1, household=False, event="payable")
@example(year=2024, scale=10, month=12, household=True, event="reservation")
def test_historical_widow_gross_uncertainty_preserves_refusals_across_months(
    year, scale, month, household, event
):
    outcome = g.evaluate_family(
        "historical-widow-uncertainty",
        7,
        _historical_widow_gross_uncertainty_computation(
            household, event, scale=scale, month=month, year=year
        ),
    )
    assert outcome.unsupported.reason is UR.ELIGIBILITY_BEFORE_1983
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


def _parent_upper_bound_computation(
    household,
    event,
    *,
    scale=1,
    month=1,
    deferred=True,
    finality=False,
    amount=None,
):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4 * scale),
        F(8 * scale),
        widow_drc_savings_clause=False,
        deferred_refusal=(UR.PARENT_BENEFIT, "count") if deferred else None,
        conditions={RC.ADMINISTRATIVE_FINALITY} if finality else (),
    )
    members = tuple(
        g.Beneficiary(
            key,
            g.Role.PARENT,
            own_benefit=g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE,
                F(31 * scale, 10),
                birth_year=1950,
            ),
            birth_year=1950,
        )
        for key in ("p", "q")
    )
    if amount is None:
        amount = F(33 * scale, 10) + F(1, 10)
    kwargs = dict(
        payment_month=g.YearMonth(2024, month),
        params=ssa_params(),
        deductions=(
            {
                "p": g.BenefitDeduction(
                    g.DeductionReason.OWN_EARNINGS_TEST, amount
                )
            }
            if event == "payable"
            else {}
        ),
        worker_deductions={"p": amount} if event == "reservation" else {},
        households={"p": "h", "q": "h"},
    )

    def compute():
        if household:
            return g.household_benefits_after_deductions(
                {"record": g.HouseholdRecord("nh", state, members)}, **kwargs
            )
        return g.family_benefits_after_deductions(
            state, members, standalone=True, **kwargs
        )

    return compute


def _assert_no_family_row(compute):
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput):
        outcomes.append(g.evaluate_family("parent-bound", 7, compute))
    counts = g.count_family_outcomes(outcomes)
    assert (counts.rows, counts.weight) == (0, 0)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
@pytest.mark.parametrize("deferred", [False, True])
def test_parent_count_uncertainty_keeps_the_one_parent_upper_bound(
    household, event, deferred
):
    _assert_no_family_row(
        _parent_upper_bound_computation(household, event, deferred=deferred)
    )


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("deferred", [False, True])
def test_zero_parent_deduction_retains_parent_count_refusal(
    household, deferred
):
    outcome = g.evaluate_family(
        "zero-parent",
        7,
        _parent_upper_bound_computation(
            household, "payable", deferred=deferred, amount=F(0)
        ),
    )
    assert outcome.unsupported.reason is UR.PARENT_BENEFIT
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@pytest.mark.parametrize("household", [False, True])
@pytest.mark.parametrize("event", ["payable", "reservation"])
def test_finality_can_unsettle_the_parent_upper_bound(household, event):
    outcome = g.evaluate_family(
        "protected-parent",
        7,
        _parent_upper_bound_computation(household, event, finality=True),
    )
    assert outcome.unsupported.reason is UR.ADMINISTRATIVE_FINALITY
    counts = g.count_family_outcomes([outcome])
    assert (counts.rows, counts.weight, counts.unsupported_weight) == (1, 7, 7)


@settings(max_examples=40, deadline=None)
@given(
    scale=st.integers(1, 10),
    month=st.integers(1, 12),
    household=st.booleans(),
    event=st.sampled_from(("payable", "reservation")),
)
@example(scale=1, month=1, household=False, event="payable")
@example(scale=10, month=12, household=True, event="reservation")
def test_parent_upper_bound_holds_across_scales_months_and_deferred_holds(
    scale, month, household, event
):
    for deferred in (False, True):
        _assert_no_family_row(
            _parent_upper_bound_computation(
                household,
                event,
                scale=scale,
                month=month,
                deferred=deferred,
            )
        )


@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("contradiction", [False, True])
def test_widow_drc_condition_on_a_living_child_keeps_ob_settled(
    money, contradiction
):
    case = _case(
        "F4",
        money,
        held=BC.WIDOW_DRC_SAVINGS_CLAUSE,
        contradiction=contradiction,
    )
    if contradiction:
        _assert_invalid(case)
    else:
        _assert_refusal(case, UR.WIDOW_DRC_SAVINGS_CLAUSE)


def test_survivor_widow_drc_protection_keeps_its_original_refusal():
    case = _case("F6", held=BC.WIDOW_DRC_SAVINGS_CLAUSE)
    context = case.family_months[1]
    member = replace(context.beneficiaries[0], birth_year=1910)
    state = replace(context.state, widow_drc_savings_clause=None)
    person = replace(case.beneficiaries[0], original_rates=(F("4.10"),) * 12)
    case = replace(
        case,
        beneficiaries=(person,),
        family_months={
            1: replace(context, state=state, beneficiaries=(member,))
        },
    )
    _assert_refusal(case, UR.WIDOW_DRC_SAVINGS_CLAUSE)


@pytest.mark.parametrize(
    "fact,reason",
    [
        ("F4", UR.PARENT_BENEFIT),
        ("F3", UR.OWN_RIB_HISTORY_BEFORE_1978),
        ("F6", UR.OWN_RIB_HISTORY_BEFORE_1978),
        ("F3", UR.DELAYED_CREDITS_BEFORE_1917),
        ("F6", UR.DELAYED_CREDITS_BEFORE_1917),
        ("F3", UR.PAYMENT_MONTH_BEFORE_1983),
        ("F6", UR.PAYMENT_MONTH_BEFORE_1983),
        ("F4", UR.WIDOW_DRC_SAVINGS_CLAUSE),
        ("F4", UR.WIDOW_DRC_SAVINGS_CLAUSE_HISTORY_UNKNOWN),
    ],
)
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("contradiction", [False, True])
def test_deferred_reason_unsettles_only_the_fact_within_its_scope(
    fact, reason, money, contradiction
):
    case = _case(fact, money, contradiction=contradiction)
    context = case.family_months[1]
    state = context.state
    if fact == "F3":
        state = replace(
            state,
            worker=replace(state.worker, birth_year=1950),
            worker_birth_year=1950,
        )
    state = replace(state, deferred_refusal=(reason, "declared deferred hold"))
    case = replace(case, family_months={1: replace(context, state=state)})
    if contradiction:
        _assert_invalid(case)
    else:
        _assert_refusal(case, reason)


@pytest.mark.parametrize("year", [1972, 1973])
def test_historical_widow_original_benefit_uses_the_payment_period(year):
    state = g.RecordState(
        g.FamilyKind.SURVIVOR,
        F(4),
        F(8),
        eligibility_year=1972,
        widow_drc_savings_clause=False,
    )
    member = g.Beneficiary(
        "w", g.Role.WIDOW, birth_year=1910, child_in_care=False
    )
    case = r.RecordYear(
        year,
        "nh",
        r.RecordKind.DECEASED,
        (
            replace(
                _person("w", T.WIDOW, F("3.30"), F("3.30"), 1),
                fra_month=None,
            ),
        ),
        family_months={
            1: r.RETFamilyMonth(state, (member,), ssa_params(), {"w": "h"})
        },
    )
    if year == 1972:
        _assert_refusal(case, UR.ELIGIBILITY_BEFORE_1983)
    else:
        _assert_invalid(case)


_FACT_TABLE_QUOTES += (
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_005.html",
        "Raised the unreduced benefit amount for widow(er)s to 82 1/2% at age 62. This benefit was not subject to reduction for age.",
    ),
    (
        "tests/data/track_b/gross_benefit_sources/poms_rs_00615_005.html",
        "5. 1972 Amendments Effective 1/73 • Provided for reduced widower's benefits at age 60. • Changed age for unreduced widow(er)'s benefits to 65. • Changed WIB to 100% of the deceased worker's PIA unless the DNH was entitled to a reduced RIB.",
    ),
)
