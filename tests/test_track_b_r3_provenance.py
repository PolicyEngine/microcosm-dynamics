"""Statutory conformance: R3 provenance over invented inputs only.

No population, behavioral or forecast claim is admitted. These tests pin
package contracts, leaving ARF and recomputation dollar rules unchanged.
"""

import copy
import pickle
from dataclasses import fields, replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import recompute as r
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params(wage_base={1951: 1_000_000})


def arf_result(amount=1300, conditions=()):
    return a.apply_arf(
        a.ARFClaim(
            a.ARFBenefitKind.RIB,
            date(1960, 1, 2),
            g.YearMonth(2022, 1),
            F(amount),
            conditions=conditions,
        ),
        payment_month=g.YearMonth(2027, 1),
        params=PARAMS,
    )


def recomputation_result(amount=42000, refused=False):
    basis = r.RecomputationBasis(
        2020,
        2018,
        35,
        (960, 5785),
        g.YearMonth(2020, 6),
        formula=r.PIAFormula.AMW if refused else r.PIAFormula.AIME,
    )
    history = dict.fromkeys(range(1951, 2021), 0)
    history[2020] = amount
    return r.annual_recomputation(basis, history, 2020, 0, PARAMS, {2020: 0})


def unsealed_clone(result):
    clone = object.__new__(type(result))
    for field in fields(result):
        if field.init:
            object.__setattr__(clone, field.name, getattr(result, field.name))
    return clone


@pytest.mark.parametrize("factory", [arf_result, recomputation_result])
@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, replace])
def test_r3_results_cannot_be_copied_or_replaced(factory, operation):
    with pytest.raises(g.InvalidFamilyInput):
        operation(factory())


@pytest.mark.parametrize("factory", [arf_result, recomputation_result])
def test_r3_results_cannot_be_constructed_directly(factory):
    result = factory()
    with pytest.raises(g.InvalidFamilyInput):
        type(result)(
            **{
                field.name: getattr(result, field.name)
                for field in fields(result)
                if field.init
            }
        )


def test_arf_money_input_rejects_unsealed_and_altered_results():
    for result in (unsealed_clone(arf_result()), arf_result()):
        object.__setattr__(result, "benefit", F(999))
        with pytest.raises(g.InvalidFamilyInput):
            a.apply_arf(
                result, payment_month=g.YearMonth(2027, 1), params=PARAMS
            )


@pytest.mark.parametrize(
    "factory,evaluator,foreign",
    [
        (arf_result, a.evaluate_arf, recomputation_result),
        (recomputation_result, r.evaluate_recomputation, arf_result),
    ],
)
def test_r3_evaluators_only_admit_their_own_unchanged_results(
    factory, evaluator, foreign
):
    result = factory()
    assert evaluator("supported", 2, lambda: result).supported
    altered = factory()
    field = "benefit" if factory is arf_result else "aime"
    object.__setattr__(altered, field, getattr(altered, field) + 1)
    for invalid in (unsealed_clone(result), altered, foreign()):
        with pytest.raises(g.InvalidFamilyInput):
            evaluator("invalid", 2, lambda invalid=invalid: invalid)


@pytest.mark.parametrize(
    "evaluator", [a.evaluate_arf, r.evaluate_recomputation]
)
@pytest.mark.parametrize("key,weight", [("", 1), ("invalid", -1)])
def test_r3_metadata_errors_precede_computation(evaluator, key, weight):
    invoked = []
    with pytest.raises(g.InvalidFamilyInput):
        evaluator(key, weight, lambda: invoked.append(True))
    assert invoked == []


def test_r3_declared_refusals_bind_exact_reason_enums():
    arf = a.evaluate_arf(
        "arf",
        1,
        lambda: arf_result(
            conditions=(a.ARFUnsupportedReason.OTHER_SUSPENSION,)
        ),
    ).unsupported
    recompute = r.evaluate_recomputation(
        "recompute", 1, lambda: recomputation_result(refused=True)
    ).unsupported
    assert type(arf) is a.ARFConfigurationUnsupported
    assert type(recompute) is r.RecomputationConfigurationUnsupported
    assert type(arf.reason) is a.ARFUnsupportedReason
    assert type(recompute.reason) is r.RecomputationUnsupportedReason
    for refusal in (arf, recompute):
        assert isinstance(refusal, g.FamilyConfigurationUnsupported)
        assert refusal.code == "FAMILY_CONFIG_UNSUPPORTED"
        with pytest.raises(g.InvalidFamilyInput):
            type(refusal)(refusal.reason, refusal.detail)


@given(st.integers(0, 10000), st.integers(0, 10000))
@settings(max_examples=20, deadline=None)
def test_r3_shared_counter_differential_and_pickle_round_trip(left, right):
    rows = (
        a.evaluate_arf("arf", F(left, 10), arf_result),
        r.evaluate_recomputation(
            "recompute", F(right, 10), recomputation_result
        ),
        a.evaluate_arf(
            "arf-refused",
            3,
            lambda: arf_result(
                conditions=(a.ARFUnsupportedReason.OTHER_SUSPENSION,)
            ),
        ),
        r.evaluate_recomputation(
            "recompute-refused",
            5,
            lambda: recomputation_result(refused=True),
        ),
    )
    expected = g.count_family_outcomes(rows)
    assert expected == a.count_arf_outcomes(rows)
    assert expected == g.count_family_outcomes(reversed(rows))
    assert expected.rows == 4
    assert expected.weight == F(left + right, 10) + 8
    assert expected.unsupported_rows == 2
    assert expected.unsupported_weight == 8
    restored = pickle.loads(pickle.dumps(rows))
    assert expected == g.count_family_outcomes(restored)
    assert restored[0].benefits == rows[0].benefits
    assert restored[1].result == rows[1].result
    for row in rows:
        for operation in (copy.copy, copy.deepcopy, replace):
            with pytest.raises(g.InvalidFamilyInput):
                operation(row)
        with pytest.raises(g.InvalidFamilyInput):
            g.count_family_outcomes([unsealed_clone(row)])
    object.__setattr__(rows[0], "weight", F(9000))
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes(rows)


def test_r3_outcome_cannot_be_constructed_directly_or_used_as_g_money():
    arf = arf_result()
    recompute = recomputation_result()
    with pytest.raises(g.InvalidFamilyInput):
        a.ARFOutcome("arf", F(1), arf, None)
    with pytest.raises(g.InvalidFamilyInput):
        r.RecomputationOutcome("recompute", F(1), recompute, None)
    for outcome in (
        a.evaluate_arf("arf", 1, lambda: arf),
        r.evaluate_recomputation("recompute", 1, lambda: recompute),
    ):
        with pytest.raises(g.InvalidFamilyInput):
            g.weighted_record_total([outcome])


@pytest.mark.parametrize("factory", [arf_result, recomputation_result])
def test_r3_altered_result_cannot_be_pickled(factory):
    value = factory()
    field = "benefit" if factory is arf_result else "aime"
    object.__setattr__(value, field, getattr(value, field) + 1)
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(value)


@pytest.mark.parametrize(
    "module,factory,evaluator",
    [
        (a, arf_result, a.evaluate_arf),
        (r, recomputation_result, r.evaluate_recomputation),
    ],
)
def test_r3_evaluator_rejects_before_outcome_construction(
    monkeypatch, module, factory, evaluator
):
    """The evaluator itself validates before invoking the outcome builder."""
    invalid = unsealed_clone(factory())

    def unexpected_construction(*args, **kwargs):
        raise AssertionError("an invalid result reached outcome construction")

    monkeypatch.setattr(module, "_computed", unexpected_construction)
    with pytest.raises(g.InvalidFamilyInput):
        evaluator("invalid", 1, lambda: invalid)


@given(
    st.integers(0, 60),
    st.integers(0, 100000),
    st.integers(0, 100000),
    st.integers(0, 100000),
    st.booleans(),
)
@settings(max_examples=50, deadline=None)
def test_r3_sealed_result_identities_and_round_trips(
    credits, dimes, old_dimes, new_dimes, has_earnings
):
    claim = a.ARFClaim(
        a.ARFBenefitKind.RIB,
        date(1960, 1, 2),
        g.YearMonth(2022, 1),
        F(dimes, 10),
        full_work_deduction_months=[
            g.YearMonth(2022 + offset // 12, offset % 12 + 1)
            for offset in range(credits)
        ],
    )
    result = a.apply_arf(
        claim, payment_month=g.YearMonth(2027, 1), params=PARAMS
    )
    assert (
        result.adjusted_reduction_months + len(result.crediting_months)
        == result.original_reduction_months
        == 60
    )
    assert result.benefit + result.reduction == claim.unreduced_benefit
    assert result.whole_dollar_benefit == g.whole_dollars(result.benefit)
    restored = pickle.loads(pickle.dumps(result))
    assert restored == result
    assert (
        a.apply_arf(
            restored, payment_month=g.YearMonth(2027, 1), params=PARAMS
        )
        == result
    )
    decision = r.recomputation_decision(
        F(old_dimes, 10), F(new_dimes, 10), has_earnings=has_earnings
    )
    assert decision.increase == decision.candidate_pia - decision.pia_of_record
    assert decision.applied == (has_earnings and decision.increase >= 1)
    assert decision.pia_in_force == (
        decision.candidate_pia if decision.applied else decision.pia_of_record
    )
    assert pickle.loads(pickle.dumps(decision)) == decision
    for value, field in ((result, "benefit"), (decision, "increase")):
        for operation in (copy.copy, copy.deepcopy, replace):
            with pytest.raises(g.InvalidFamilyInput):
                operation(value)
        restore, (kind, values) = value.__reduce__()
        values[field] += F(1, 10)
        with pytest.raises(g.InvalidFamilyInput):
            restore(kind, values)
