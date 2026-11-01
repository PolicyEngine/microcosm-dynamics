"""RET round 4: statutory conformance on invented declarations only.

Contradictory entitlement or one person with two known SSA cohorts is an
input error before coverage, with no outcome row. Missing cohorts remain
valid. No population, behavioral, or forecast claim is admitted.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import replace
from fractions import Fraction as F

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
HELD_CONDITIONS = (
    g.RecordCondition.ADMINISTRATIVE_FINALITY,
    g.RecordCondition.NON_AIME_FORMULA_PIA,
    g.RecordCondition.WORKERS_COMPENSATION_OFFSET,
    "fiscal_year",
    "short_taxable_year",
    "foreign_work",
    "vocational_rehabilitation_refusal",
    r.SuspensionMethod.PRORATED,
    r.SuspensionMethod.DEFERRED,
    r.SuspensionMethod.PROTEST_PARTIAL,
)


def _person(key, kind, money, months, *, entitled=True):
    return r.RETBeneficiary(
        key,
        (kind,) * 12,
        set(months) if entitled else (),
        tuple(
            F(money) if entitled and m in months else F(0)
            for m in range(1, 13)
        ),
        (F(money),) * 12,
        fra_month=0,
    )


def _entitlement_case(
    month, money, ret_entitled, held=None, *, matching=False
):
    g_entitled = ret_entitled if matching else not ret_entitled
    conditions = {held} if isinstance(held, g.RecordCondition) else set()
    if not g_entitled:
        conditions.add(g.RecordCondition.WORKER_NOT_ENTITLED)
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(money),
        F(3 * money, 2),
        worker=(
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(money))
            if g_entitled
            else None
        ),
        worker_birth_year=1950,
        conditions=conditions,
    )
    return r.RecordYear(
        2024,
        "nh",
        beneficiaries=(
            _person("nh", T.RIB, money, {month}, entitled=ret_entitled),
        ),
        family_months={month: r.RETFamilyMonth(state, (), ssa_params(), {})},
        **(
            {held: True}
            if isinstance(held, str)
            else (
                {"suspension_method": held}
                if isinstance(held, r.SuspensionMethod)
                else {}
            )
        ),
    )


def _expect_no_row(compute, match):
    outcomes = []
    with pytest.raises(g.InvalidFamilyInput, match=match):
        outcomes.append(r.evaluate_ret("contradiction", 7, compute))
    denominator = r.count_ret_outcomes(outcomes)
    assert (denominator.rows, denominator.weight) == (0, 0)
    assert g.count_family_outcomes(outcomes).rows == 0


@pytest.mark.parametrize("month", range(1, 13))
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("ret_entitled", [False, True])
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
def test_nh_entitlement_contradiction_never_becomes_held_refusal(
    month, money, ret_entitled, held
):
    _expect_no_row(
        lambda: r.apply_ret_year(
            _entitlement_case(month, money, ret_entitled, held), PARAMS
        ),
        "G and RET NH entitlement facts differ",
    )


@pytest.mark.parametrize("ret_entitled", [False, True])
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize("held", [None, *HELD_CONDITIONS])
def test_matching_nh_entitlement_preserves_computation_or_counted_refusal(
    ret_entitled, money, held
):
    outcome = r.evaluate_ret(
        "consistent",
        7,
        lambda: r.apply_ret_year(
            _entitlement_case(1, money, ret_entitled, held, matching=True),
            PARAMS,
        ),
    )
    denominator = r.count_ret_outcomes([outcome])
    assert (denominator.rows, denominator.weight) == (1, 7)
    assert outcome.supported == (held is None)
    assert denominator.unsupported_weight == (0 if held is None else 7)
    if held is None:
        assert sum(row.payment for row in outcome.ledger.months) == (
            money if ret_entitled else 0
        )


@settings(max_examples=70, deadline=None)
@given(
    month=st.integers(1, 12),
    money=st.integers(0, 1000),
    ret_entitled=st.booleans(),
    held=st.sampled_from(HELD_CONDITIONS),
)
@example(
    month=1,
    money=0,
    ret_entitled=False,
    held=g.RecordCondition.ADMINISTRATIVE_FINALITY,
)
@example(
    month=12,
    money=4,
    ret_entitled=True,
    held=g.RecordCondition.ADMINISTRATIVE_FINALITY,
)
def test_no_held_coverage_condition_masks_nh_contradiction(
    month, money, ret_entitled, held
):
    for condition in (None, held):
        _expect_no_row(
            lambda condition=condition: r.apply_ret_year(
                _entitlement_case(month, money, ret_entitled, condition),
                PARAMS,
            ),
            "G and RET NH entitlement facts differ",
        )


@pytest.mark.parametrize("ret_entitled", [False, True])
def test_later_nh_contradiction_precedes_every_g_computation(
    monkeypatch, ret_entitled
):
    first = _entitlement_case(
        1,
        4,
        ret_entitled,
        g.RecordCondition.ADMINISTRATIVE_FINALITY,
        matching=True,
    )
    last = _entitlement_case(12, 4, ret_entitled)
    case = replace(
        first,
        beneficiaries=(
            _person("nh", T.RIB, 4, {1, 12}, entitled=ret_entitled),
        ),
        family_months={**first.family_months, **last.family_months},
    )
    calls = []

    def unexpected(*args, **kwargs):
        calls.append(args)
        pytest.fail("G computation ran before declared NH validation")

    monkeypatch.setattr(g, "_family_benefits_validated", unexpected)
    _expect_no_row(
        lambda: r.apply_ret_year(case, PARAMS),
        "G and RET NH entitlement facts differ",
    )
    assert calls == []


@pytest.mark.parametrize("money", [0, 4])
def test_disability_nh_entitlement_comes_from_record_kind(money):
    state = g.RecordState(g.FamilyKind.DISABILITY, F(money), F(money))
    record = r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DISABILITY,
        (_person("nh", T.DIB, money, {1}),),
        family_months={1: r.RETFamilyMonth(state, (), ssa_params(), {})},
    )
    outcome = r.evaluate_ret(
        "dib", 7, lambda: r.apply_ret_year(record, PARAMS)
    )
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7
    assert sum(row.payment for row in outcome.ledger.months) == money


def _cohort_case(
    nh,
    fields,
    years,
    *,
    months=(1, 2),
    money=1,
    held="none",
    reverse=False,
    unclaimed=False,
):
    key = "nh" if nh else "w"
    contexts = {}
    entries = list(zip(months, fields, years, strict=True))
    if reverse:
        entries.reverse()
    for month, field, cohort in entries:
        own = g.OwnBenefit(
            g.OwnBenefitKind.OLD_AGE if nh else g.OwnBenefitKind.DISABILITY,
            F(money if nh else 0),
            birth_year=cohort if field == "own" else None,
        )
        conditions = (
            {g.RecordCondition.ADMINISTRATIVE_FINALITY}
            if held == "g"
            else set()
        )
        if unclaimed:
            conditions.add(g.RecordCondition.WORKER_NOT_ENTITLED)
        state = g.RecordState(
            g.FamilyKind.RETIREMENT if nh else g.FamilyKind.SURVIVOR,
            F(money if nh else 4 * money),
            F(money if nh else 4 * money),
            worker=own if nh and not unclaimed else None,
            worker_birth_year=cohort if nh and field == "record" else None,
            conditions=conditions,
            widow_drc_savings_clause=False,
        )
        members = (
            ()
            if nh
            else (
                g.Beneficiary(
                    key,
                    g.Role.CHILD,
                    birth_year=cohort if field == "beneficiary" else None,
                    own_benefit=own if field == "own" else None,
                ),
            )
        )
        contexts[month] = r.RETFamilyMonth(
            state, members, ssa_params(), {} if nh else {key: "h"}
        )
    return r.RecordYear(
        2024,
        "nh",
        r.RecordKind.RETIREMENT if nh else r.RecordKind.DECEASED,
        (
            replace(
                _person(
                    key,
                    T.RIB if nh else T.CHILD,
                    money if nh else 3 * money,
                    set(months),
                    entitled=not unclaimed,
                ),
                original_rates=(F(money if nh else 3 * money),) * 12,
            ),
        ),
        fiscal_year=held == "ret",
        family_months=contexts,
    )


@pytest.mark.parametrize("held", [False, True])
@pytest.mark.parametrize("field", ["birth", "own", "mixed"])
def test_review_widow_cross_month_probe_has_no_row(field, held):
    def compute():
        contexts = {}
        for month, cohort in ((1, 1950), (2, 1951)):
            is_own = field == "own" or (field == "mixed" and month == 1)
            own = g.OwnBenefit(
                g.OwnBenefitKind.OLD_AGE,
                F(0),
                birth_year=cohort if is_own else None,
            )
            state = g.RecordState(
                g.FamilyKind.SURVIVOR,
                F(1),
                F(1),
                widow_drc_savings_clause=False,
            )
            member = g.Beneficiary(
                "w",
                g.Role.WIDOW,
                birth_year=None if is_own else cohort,
                own_benefit=own if is_own else None,
            )
            contexts[month] = r.RETFamilyMonth(
                state, (member,), ssa_params(), {"w": "h"}
            )
        return r.apply_ret_year(
            r.RecordYear(
                2024,
                "nh",
                r.RecordKind.DECEASED,
                (_person("w", T.WIDOW, 1, {1, 2}),),
                fiscal_year=held,
                family_months=contexts,
            ),
            PARAMS,
        )

    _expect_no_row(compute, "birth_year differs across monthly contexts")


FIELD_PAIRS = (
    (False, ("beneficiary", "beneficiary")),
    (False, ("own", "own")),
    (False, ("beneficiary", "own")),
    (False, ("own", "beneficiary")),
    (True, ("record", "record")),
    (True, ("own", "own")),
    (True, ("record", "own")),
    (True, ("own", "record")),
)


@pytest.mark.parametrize("nh,fields", FIELD_PAIRS)
@pytest.mark.parametrize("money", [0, 1])
@pytest.mark.parametrize("held", ["none", "g", "ret"])
@pytest.mark.parametrize("reverse", [False, True])
def test_two_known_monthly_cohorts_are_input_error_before_any_refusal(
    nh, fields, money, held, reverse
):
    _expect_no_row(
        lambda: r.apply_ret_year(
            _cohort_case(
                nh,
                fields,
                (1950, 1951),
                money=money,
                held=held,
                reverse=reverse,
            ),
            PARAMS,
        ),
        "birth_year differs across monthly contexts",
    )


@pytest.mark.parametrize("held", ["none", "g", "ret"])
def test_unclaimed_nh_keeps_cross_month_worker_cohort_identity(held):
    _expect_no_row(
        lambda: r.apply_ret_year(
            _cohort_case(
                True,
                ("record", "record"),
                (1950, 1951),
                money=0,
                held=held,
                unclaimed=True,
            ),
            PARAMS,
        ),
        "birth_year differs across monthly contexts",
    )


@pytest.mark.parametrize("nh,fields", FIELD_PAIRS)
@pytest.mark.parametrize(
    "years", [(1950, 1950), (1950, None), (None, 1950), (None, None)]
)
@pytest.mark.parametrize("money", [0, 1])
@pytest.mark.parametrize("held", ["none", "g", "ret"])
def test_same_and_missing_monthly_cohorts_remain_valid(
    nh, fields, years, money, held
):
    outcome = r.evaluate_ret(
        "valid-cohort",
        7,
        lambda: r.apply_ret_year(
            _cohort_case(
                nh,
                fields,
                years,
                money=money,
                held=held,
            ),
            PARAMS,
        ),
    )
    denominator = r.count_ret_outcomes([outcome])
    assert (denominator.rows, denominator.weight) == (1, 7)
    assert outcome.supported == (held == "none")
    assert denominator.unsupported_weight == (0 if held == "none" else 7)
    if held == "none":
        assert sum(row.payment for row in outcome.ledger.months) == (
            2 * money if nh else 6 * money
        )


@settings(max_examples=100, deadline=None)
@given(
    identity=st.sampled_from(FIELD_PAIRS),
    months=st.lists(st.integers(1, 12), min_size=2, max_size=2, unique=True),
    cohorts=st.lists(
        st.integers(1930, 1956), min_size=2, max_size=2, unique=True
    ),
    money=st.integers(0, 100),
    held=st.sampled_from(("none", "g", "ret")),
    unclaimed=st.booleans(),
)
@example(
    identity=(False, ("own", "own")),
    months=[1, 2],
    cohorts=[1950, 1951],
    money=1,
    held="ret",
    unclaimed=False,
)
@example(
    identity=(True, ("record", "record")),
    months=[1, 12],
    cohorts=[1950, 1951],
    money=0,
    held="g",
    unclaimed=True,
)
def test_one_cohort_across_every_month_and_field_pair(
    identity, months, cohorts, money, held, unclaimed
):
    nh, fields = identity
    unclaimed = nh and unclaimed
    if unclaimed:
        fields = ("record", "record")
    for reverse in (False, True):
        _expect_no_row(
            lambda reverse=reverse: r.apply_ret_year(
                _cohort_case(
                    nh,
                    fields,
                    cohorts,
                    months=months,
                    money=money,
                    held=held,
                    reverse=reverse,
                    unclaimed=unclaimed,
                ),
                PARAMS,
            ),
            "birth_year differs across monthly contexts",
        )


@settings(max_examples=70, deadline=None)
@given(
    nh=st.booleans(),
    cohort=st.integers(1930, 1956),
    months=st.lists(st.integers(1, 12), min_size=2, max_size=12, unique=True),
    data=st.data(),
)
def test_one_known_cohort_with_gaps_never_errors(nh, cohort, months, data):
    options = ("record", "own") if nh else ("beneficiary", "own")
    fields = tuple(data.draw(st.sampled_from(options)) for _ in months)
    known_index = data.draw(st.integers(0, len(months) - 1))
    years = tuple(
        cohort if index == known_index else None
        for index in range(len(months))
    )
    result = r.evaluate_ret(
        "gapped-cohort",
        7,
        lambda: r.apply_ret_year(
            _cohort_case(
                nh,
                fields,
                years,
                months=months,
                money=1,
            ),
            PARAMS,
        ),
    )
    assert result.supported
    assert r.count_ret_outcomes([result]).supported_weight == 7
    assert sum(row.payment for row in result.ledger.months) == (
        len(months) if nh else 3 * len(months)
    )


SPOUSE_ROLES = (
    g.Role.SPOUSE,
    g.Role.SPOUSE_CHILD_IN_CARE,
    g.Role.DIVORCED_SPOUSE,
)


def _spouse_entitlement_case(
    role,
    money,
    *,
    month=1,
    held=None,
    reverse=False,
    own_kind=g.OwnBenefitKind.OLD_AGE,
    own_amount=None,
    own_present=True,
):
    """Own PIA settles spouse eligibility before any monthly rate math."""
    amount = F(money, 2) if own_amount is None else F(own_amount)
    conditions = {held} if isinstance(held, g.RecordCondition) else ()
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        F(money),
        F(3 * money, 2),
        worker=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(money)),
        conditions=conditions,
    )
    own = g.OwnBenefit(own_kind, amount) if own_present else None
    spouse = g.Beneficiary(
        "s",
        role,
        own_benefit=own,
        own_benefit_first=True if own_present else None,
        **(
            {"child_in_care": False, "first_entitlement_child_in_care": False}
            if role is g.Role.DIVORCED_SPOUSE
            else {}
        ),
    )
    spouse_rate = max(F(0), F(money, 2) - (amount if own_present else 0))
    people = (
        replace(_person("nh", T.RIB, money, {month}), fra_month=None),
        replace(
            _person(
                "s",
                (
                    T.DIVORCED_SPOUSE
                    if role is g.Role.DIVORCED_SPOUSE
                    else T.SPOUSE
                ),
                spouse_rate,
                {month},
            ),
            original_rates=(F(money, 2),) * 12,
            fra_month=None,
        ),
    )
    return r.RecordYear(
        2024,
        "nh",
        beneficiaries=people[::-1] if reverse else people,
        family_months={
            month: r.RETFamilyMonth(
                state,
                (spouse,),
                ssa_params(),
                {"s": "h"},
            )
        },
        **(
            {held: True}
            if isinstance(held, str)
            else (
                {"suspension_method": held}
                if isinstance(held, r.SuspensionMethod)
                else {}
            )
        ),
    )


def _expect_fact_classification(call, fact, held, message):
    """Round 5: a protected fact retains its precise counted refusal."""
    unsettled = held is g.RecordCondition.ADMINISTRATIVE_FINALITY or (
        held is g.RecordCondition.WORKERS_COMPENSATION_OFFSET and fact == "F2"
    )
    if not unsettled:
        _expect_no_row(call, message)
        return
    outcome = r.evaluate_ret("protected-fact", 7, call)
    denominator = r.count_ret_outcomes([outcome])
    assert not outcome.supported
    assert outcome.unsupported.reason is g._RECORD_CONDITION_REASONS[held][0]
    assert (denominator.rows, denominator.weight) == (1, 7)
    assert denominator.unsupported_weight == 7


@pytest.mark.parametrize("role", SPOUSE_ROLES)
@pytest.mark.parametrize("own_kind", list(g.OwnBenefitKind))
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_declared_spouse_pia_disqualification_precedes_held_refusal(
    role, own_kind, money, held, reverse
):
    _expect_fact_classification(
        lambda: r.apply_ret_year(
            _spouse_entitlement_case(
                role,
                money,
                held=held,
                reverse=reverse,
                own_kind=own_kind,
            ),
            PARAMS,
        ),
        "F5",
        held,
        "G and RET auxiliary entitlement facts differ",
    )


@pytest.mark.parametrize("role", SPOUSE_ROLES)
@pytest.mark.parametrize("own_kind", list(g.OwnBenefitKind))
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
def test_strictly_lower_spouse_own_pia_preserves_eligible_entitlement(
    role, own_kind, held
):
    outcome = r.evaluate_ret(
        "strict",
        7,
        lambda: r.apply_ret_year(
            _spouse_entitlement_case(
                role, 4, own_kind=own_kind, own_amount=1, held=held
            ),
            PARAMS,
        ),
    )
    denominator = r.count_ret_outcomes([outcome])
    assert (denominator.rows, denominator.weight) == (1, 7)
    assert outcome.supported == (held is None)
    if held is None:
        assert sum(row.payment for row in outcome.ledger.months) == 5


@pytest.mark.parametrize("role", SPOUSE_ROLES)
@pytest.mark.parametrize("money", [0, 4])
def test_spouse_without_own_entitlement_keeps_zero_and_positive_payments(
    role, money
):
    outcome = r.evaluate_ret(
        "no-own",
        7,
        lambda: r.apply_ret_year(
            _spouse_entitlement_case(role, money, own_present=False), PARAMS
        ),
    )
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7
    assert sum(row.payment for row in outcome.ledger.months) == F(3 * money, 2)


@settings(max_examples=70, deadline=None)
@given(
    role=st.sampled_from(SPOUSE_ROLES),
    own_kind=st.sampled_from(list(g.OwnBenefitKind)),
    scale=st.integers(0, 100),
    extra=st.integers(0, 100),
    month=st.integers(1, 12),
    held=st.sampled_from(HELD_CONDITIONS),
    reverse=st.booleans(),
)
@example(
    role=g.Role.SPOUSE,
    own_kind=g.OwnBenefitKind.OLD_AGE,
    scale=0,
    extra=0,
    month=1,
    held=g.RecordCondition.ADMINISTRATIVE_FINALITY,
    reverse=False,
)
def test_no_held_coverage_condition_masks_spouse_pia_contradiction(
    role, own_kind, scale, extra, month, held, reverse
):
    for condition in (None, held):
        _expect_fact_classification(
            lambda condition=condition: r.apply_ret_year(
                _spouse_entitlement_case(
                    role,
                    4 * scale,
                    own_kind=own_kind,
                    own_amount=2 * scale + extra,
                    month=month,
                    held=condition,
                    reverse=reverse,
                ),
                PARAMS,
            ),
            "F5",
            condition,
            "G and RET auxiliary entitlement facts differ",
        )


@settings(max_examples=45, deadline=None)
@given(
    role=st.sampled_from(SPOUSE_ROLES),
    own_kind=st.sampled_from(list(g.OwnBenefitKind)),
    scale=st.integers(1, 100),
    month=st.integers(1, 12),
)
def test_own_pia_strictly_below_half_never_triggers_spouse_preflight(
    role, own_kind, scale, month
):
    outcome = r.evaluate_ret(
        "eligible",
        7,
        lambda: r.apply_ret_year(
            _spouse_entitlement_case(
                role,
                4 * scale,
                own_kind=own_kind,
                own_amount=scale,
                month=month,
            ),
            PARAMS,
        ),
    )
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7
    assert sum(row.payment for row in outcome.ledger.months) == 5 * scale


def test_spouse_entitlement_premise_is_verbatim_and_capture_hashes_match():
    quotes = {
        "ssa_act_202_215": "based on a primary insurance amount which is less than one-half of the primary insurance amount of such individual",
        "poms_rs_00202_005": "not be entitled to an RIB or DIB based on a PIA which equals or exceeds one-half the PIA of the worker.",
    }
    for source_id, quote in quotes.items():
        entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
        assert (
            hashlib.sha256((SOURCES / entry["file"]).read_bytes()).hexdigest()
            == entry["sha256"]
        )
        assert quote in source_text(source_id)


def _direct_nh_rate_case(kind, pia, declared, *, month=1, held=None):
    disability = kind == "dib_gross"
    state = g.RecordState(
        g.FamilyKind.DISABILITY if disability else g.FamilyKind.RETIREMENT,
        F(pia),
        F(pia) if disability else F(3 * pia, 2),
        worker=(
            None
            if disability
            else g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(pia))
        ),
        conditions=({held} if isinstance(held, g.RecordCondition) else ()),
    )
    person = replace(
        _person(
            "nh",
            T.DIB if disability else T.RIB,
            declared if disability else pia,
            {month},
        ),
        original_rates=(F(pia) if disability else F(declared),) * 12,
    )
    return r.RecordYear(
        2024,
        "nh",
        r.RecordKind.DISABILITY if disability else r.RecordKind.RETIREMENT,
        (person,),
        family_months={month: r.RETFamilyMonth(state, (), ssa_params(), {})},
        **(
            {held: True}
            if isinstance(held, str)
            else (
                {"suspension_method": held}
                if isinstance(held, r.SuspensionMethod)
                else {}
            )
        ),
    )


@pytest.mark.parametrize("pia", [0, 4])
@pytest.mark.parametrize("month", [1, 12])
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
def test_declared_nh_original_pia_mismatch_precedes_held_refusal(
    pia, month, held
):
    _expect_fact_classification(
        lambda: r.apply_ret_year(
            _direct_nh_rate_case(
                "original",
                pia,
                F(pia) + F(1, 10),
                month=month,
                held=held,
            ),
            PARAMS,
        ),
        "F1",
        held,
        "G context does not match RET rates",
    )


@pytest.mark.parametrize("gross", [0, 3])
@pytest.mark.parametrize("month", [1, 12])
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
def test_declared_dib_nh_gross_pia_mismatch_precedes_held_refusal(
    gross, month, held
):
    _expect_fact_classification(
        lambda: r.apply_ret_year(
            _direct_nh_rate_case(
                "dib_gross",
                4,
                gross,
                month=month,
                held=held,
            ),
            PARAMS,
        ),
        "F2",
        held,
        "G context does not match RET rates",
    )


@pytest.mark.parametrize("kind", ["original", "dib_gross"])
@pytest.mark.parametrize("money", [0, 4])
@pytest.mark.parametrize(
    "held", [None, g.RecordCondition.ADMINISTRATIVE_FINALITY]
)
def test_matching_direct_nh_rates_keep_zero_and_positive_payments(
    kind, money, held
):
    outcome = r.evaluate_ret(
        "matching-rates",
        7,
        lambda: r.apply_ret_year(
            _direct_nh_rate_case(kind, money, money, held=held), PARAMS
        ),
    )
    denominator = r.count_ret_outcomes([outcome])
    assert (denominator.rows, denominator.weight) == (1, 7)
    assert outcome.supported == (held is None)
    if held is None:
        assert sum(row.payment for row in outcome.ledger.months) == money


def test_unentitled_nh_original_share_is_not_a_payable_rate_declaration():
    case = _entitlement_case(1, 4, False, matching=True)
    case = replace(
        case,
        beneficiaries=(
            replace(
                case.beneficiaries[0],
                original_rates=(F(5),) * 12,
            ),
        ),
    )
    outcome = r.evaluate_ret(
        "unentitled-original", 7, lambda: r.apply_ret_year(case, PARAMS)
    )
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7
    assert sum(row.payment for row in outcome.ledger.months) == 0


@settings(max_examples=70, deadline=None)
@given(
    kind=st.sampled_from(("original", "dib_gross")),
    scale=st.integers(1, 100),
    gap=st.integers(1, 9),
    direction=st.sampled_from((-1, 1)),
    month=st.integers(1, 12),
    held=st.sampled_from(HELD_CONDITIONS),
)
@example(
    kind="original",
    scale=1,
    gap=1,
    direction=1,
    month=1,
    held=g.RecordCondition.ADMINISTRATIVE_FINALITY,
)
@example(
    kind="dib_gross",
    scale=1,
    gap=1,
    direction=-1,
    month=12,
    held=g.RecordCondition.ADMINISTRATIVE_FINALITY,
)
def test_no_held_coverage_condition_masks_direct_nh_rate_contradiction(
    kind, scale, gap, direction, month, held
):
    pia = 4 * scale
    declared = F(pia) + direction * F(gap, 10)
    for condition in (None, held):
        _expect_fact_classification(
            lambda condition=condition: r.apply_ret_year(
                _direct_nh_rate_case(
                    kind, pia, declared, month=month, held=condition
                ),
                PARAMS,
            ),
            ("F1" if kind == "original" else "F2"),
            condition,
            "G context does not match RET rates",
        )


@settings(max_examples=40, deadline=None)
@given(
    kind=st.sampled_from(("original", "dib_gross")),
    scale=st.integers(0, 100),
    month=st.integers(1, 12),
)
def test_direct_nh_rate_preflight_preserves_every_matching_declaration(
    kind, scale, month
):
    outcome = r.evaluate_ret(
        "valid-direct-rates",
        7,
        lambda: r.apply_ret_year(
            _direct_nh_rate_case(
                kind,
                4 * scale,
                4 * scale,
                month=month,
            ),
            PARAMS,
        ),
    )
    assert outcome.supported
    assert r.count_ret_outcomes([outcome]).supported_weight == 7
    assert sum(row.payment for row in outcome.ledger.months) == 4 * scale


def test_direct_nh_rate_premises_are_verbatim_and_capture_hashes_match():
    source_id = "ssa_ssb_v75n3_family_maximum"
    entry = next(s for s in manifest()["sources"] if s["id"] == source_id)
    assert (
        hashlib.sha256((SOURCES / entry["file"]).read_bytes()).hexdigest()
        == entry["sha256"]
    )
    assert "100% of the worker's PIA" in source_text(source_id)

    folder = SOURCES.parent / "ret_ledger_sources"
    evidence = json.loads((folder / "manifest.json").read_text())
    entry = next(
        s for s in evidence["sources"] if s["id"] == "poms_rs_02501_110"
    )
    raw = (folder / entry["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    text = re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw.decode()))
    )
    assert "because their original benefit is equal to 100% of the PIA" in text
