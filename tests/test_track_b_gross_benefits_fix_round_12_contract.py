"""Cross-layer provenance: statutory conformance on invented cases only.

The tests admit API provenance and denominator accounting, without any
population, behavioral, payment-timing or forecast claim.
"""

import pickle
from copy import copy, deepcopy
from dataclasses import fields, replace
from datetime import date
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import recompute as r
from populace_dynamics.track_b import ret_ledger as ret
from populace_dynamics.track_b.ret_grace import BenefitType
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params(wage_base={1951: 1_000_000})
RET_PARAMS = load_ret_parameters()
JAN = g.YearMonth(2026, 1)
LAYERS = ("g", "ret", "arf", "recompute")


def _family(*, refused=False):
    if refused:
        return g.retirement_survivor_family_maximum(F(1000), 1982, PARAMS)
    return g.family_benefits(
        g.RecordState(
            g.FamilyKind.RETIREMENT,
            F(1000),
            F(1800),
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, F(1000)),
        ),
        (g.Beneficiary("child", g.Role.CHILD),),
        payment_month=JAN,
        params=PARAMS,
        standalone=True,
    )


def _arf(*, refused=False):
    return a.apply_arf(
        a.ARFClaim(
            a.ARFBenefitKind.RIB,
            date(1960, 1, 2),
            g.YearMonth(2022, 1),
            F(1300),
            full_work_deduction_months={g.YearMonth(2022, 1)},
            conditions=(
                (a.ARFUnsupportedReason.OTHER_SUSPENSION,) if refused else ()
            ),
        ),
        payment_month=g.YearMonth(2027, 1),
        params=PARAMS,
    )


def _recomputation(*, refused=False):
    basis = r.RecomputationBasis(
        2020,
        2018,
        35,
        r.eligibility_bend_points(2020, PARAMS),
        g.YearMonth(2020, 6),
        formula=r.PIAFormula.GUARANTEE if refused else r.PIAFormula.AIME,
    )
    history = dict.fromkeys(range(1951, 2021), 0)
    history.update({2018: 21000, 2019: 42000, 2020: 63000})
    return r.annual_recomputation(basis, history, 2020, 135, PARAMS, {2020: 0})


def _ret(*, refused=False):
    beneficiary = ret.RETBeneficiary(
        "worker",
        (BenefitType.RIB,) * 12,
        frozenset(range(1, 13)),
        (F(600),) * 12,
        (F(600),) * 12,
    )
    return ret.apply_ret_year(
        ret.RecordYear(
            2026, "worker", beneficiaries=(beneficiary,), fiscal_year=refused
        ),
        RET_PARAMS,
    )


COMPUTE = {"g": _family, "ret": _ret, "arf": _arf, "recompute": _recomputation}
EVALUATE = {
    "g": g.evaluate_family,
    "ret": ret.evaluate_ret,
    "arf": a.evaluate_arf,
    "recompute": r.evaluate_recomputation,
}


def _outcome(layer, *, refused=False, weight=F(1), key=None):
    return EVALUATE[layer](
        key or f"{layer}-{refused}",
        weight,
        lambda: COMPUTE[layer](refused=refused),
    )


def _values(value):
    if isinstance(value, g.FamilyConfigurationUnsupported):
        return {
            key: getattr(value, key)
            for key in ("reason", "detail", "beneficiary_id", "record_id")
        }
    return {field.name: getattr(value, field.name) for field in fields(value)}


def _unsealed(value):
    forged = object.__new__(type(value))
    for key, item in _values(value).items():
        object.__setattr__(forged, key, item)
    return forged


@pytest.mark.parametrize("layer", LAYERS)
def test_each_refusal_has_one_exact_layer_reason_enum(layer):
    refusal = _outcome(layer, refused=True).unsupported
    assert isinstance(refusal, g.FamilyConfigurationUnsupported)
    assert refusal.code == "FAMILY_CONFIG_UNSUPPORTED"
    expected = {
        "g": g.UnsupportedReason,
        "ret": ret.UnsupportedReason,
        "arf": a.ARFUnsupportedReason,
        "recompute": r.RecomputationUnsupportedReason,
    }
    assert type(refusal.reason) is expected[layer]
    for other_layer in set(LAYERS) - {layer}:
        other_reason = next(iter(expected[other_layer]))
        # The internal constructor simulates a computation;
        # public constructors fail earlier because they lack the capability.
        with pytest.raises(g.InvalidFamilyInput):
            g._computed(type(refusal), other_reason, "wrong layer reason")
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(type(refusal), refusal.reason.value, "raw string reason")


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("evaluator", LAYERS)
def test_every_evaluator_retains_a_genuine_refusal_family(layer, evaluator):
    refusal = _outcome(layer, refused=True).unsupported

    def refuse():
        raise refusal

    row = EVALUATE[evaluator]("refused", F(7, 3), refuse)
    assert not row.supported
    counts = g.count_family_outcomes([row])
    assert counts.rows == counts.unsupported_rows == 1
    assert counts.weight == counts.unsupported_weight == F(7, 3)
    assert counts.unsupported_by_reason == {refusal.reason: (1, F(7, 3))}


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    st.lists(st.integers(0, 1000), min_size=8, max_size=8),
    st.permutations(range(8)),
)
def test_common_denominator_partition_order_and_layer_counter_differential(
    weights, order
):
    rows = [
        _outcome(layer, refused=refused, weight=F(weights[index], 7))
        for index, (layer, refused) in enumerate(
            (layer, refused) for layer in LAYERS for refused in (False, True)
        )
    ]
    expected = g.count_family_outcomes(rows)
    reordered = [rows[index] for index in order]
    for counter in (
        g.count_family_outcomes,
        a.count_arf_outcomes,
        ret.count_ret_outcomes,
    ):
        assert counter(reordered) == expected
    assert expected.rows == 8
    assert expected.supported_rows == expected.unsupported_rows == 4
    assert expected.weight == sum(weights, F(0)) / 7
    assert expected.weight == (
        expected.supported_weight + expected.unsupported_weight
    )
    assert expected.unsupported_weight == sum(weights[1::2], F(0)) / 7
    assert expected.unsupported_rows == sum(
        count for count, _ in expected.unsupported_by_reason.values()
    )
    assert expected.unsupported_weight == sum(
        weight for _, weight in expected.unsupported_by_reason.values()
    )
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(expected)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("altered", (False, True))
def test_common_counter_rejects_unsealed_or_altered_outcomes(layer, altered):
    row = _outcome(layer)
    if altered:
        object.__setattr__(row, "weight", F(0))
    else:
        row = _unsealed(row)
    for counter in (
        g.count_family_outcomes,
        a.count_arf_outcomes,
        ret.count_ret_outcomes,
    ):
        with pytest.raises(g.InvalidFamilyInput):
            counter([row])


@pytest.mark.parametrize("layer", LAYERS)
def test_transplanted_outcome_seals_do_not_prove_computation(layer):
    original = _outcome(layer)
    forged = _unsealed(original)
    object.__setattr__(forged, "_g_seal", original._g_seal)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([forged])


def test_nested_credit_month_mutation_invalidates_result_and_outcome():
    result = _arf()
    row = a.evaluate_arf("arf", 1, lambda: result)
    credit = next(iter(result.crediting_months))
    object.__setattr__(credit, "year", credit.year + 1)
    with pytest.raises(g.InvalidFamilyInput):
        a.apply_arf(result, payment_month=g.YearMonth(2027, 1), params=PARAMS)
    with pytest.raises(g.InvalidFamilyInput):
        a.evaluate_arf("changed", 1, lambda: result)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([row])
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(result)


@pytest.mark.parametrize("field", ("rates", "original_rates"))
@pytest.mark.parametrize("altered", (False, True))
def test_partial_payment_money_inputs_reject_unsealed_or_altered_allocations(
    field, altered
):
    allocation = ret.partial_payments(1, {"worker": 2}, {"worker": 2})
    if altered:
        object.__setattr__(allocation, "shares", {"worker": F(9)})
    else:
        allocation = _unsealed(allocation)
    inputs = {"rates": {"worker": 2}, "original_rates": {"worker": 2}}
    inputs[field] = allocation
    with pytest.raises(g.InvalidFamilyInput):
        ret.partial_payments(1, **inputs)


@pytest.mark.parametrize(
    "factory,field,year",
    (
        (_arf, "payment_month", 2027),
        (_recomputation, "effective_month", 2020),
    ),
)
@pytest.mark.parametrize("month", (0, 13))
def test_r3_private_capability_revalidates_nested_calendar_months(
    factory, field, year, month
):
    original = factory()
    cls, values = type(original), _values(original)
    # Private capability tests seal-time checks; public restoration is forbidden.
    invalid = g.YearMonth(year, 1)
    object.__setattr__(invalid, "month", month)
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(cls, **(values | {field: invalid}))


def test_arf_private_capability_cannot_admit_a_refused_original_claim():
    result = _arf()
    refused_claim = replace(
        result.claim, conditions=(a.ARFUnsupportedReason.OTHER_SUSPENSION,)
    )
    with pytest.raises(g.FamilyConfigurationUnsupported) as refusal:
        a.apply_arf(
            refused_claim, payment_month=result.payment_month, params=PARAMS
        )
    assert refusal.value.reason is a.ARFUnsupportedReason.OTHER_SUSPENSION
    cls, values = type(result), _values(result)
    # Private capability tests seal-time checks; public restoration is forbidden.
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(cls, **(values | {"claim": refused_claim}))


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("kind", ("result", "outcome", "refusal", "counts"))
@pytest.mark.parametrize(
    "operation", ("direct", "copy", "deepcopy", "replace")
)
def test_all_layer_outputs_require_the_shared_private_capability(
    layer, kind, operation
):
    result = COMPUTE[layer]()
    outcome = _outcome(layer)
    refusal = _outcome(layer, refused=True).unsupported
    value = {
        "result": result,
        "outcome": outcome,
        "refusal": refusal,
        "counts": g.count_family_outcomes([outcome]),
    }[kind]
    if kind == "refusal" and operation == "replace":
        # Exceptions are not dataclasses; replacement is meaningful for the
        # frozen dataclass types, and their refusals have three other checks.
        return
    with pytest.raises(g.InvalidFamilyInput):
        if operation == "direct":
            type(value)(**_values(value))
        else:
            {"copy": copy, "deepcopy": deepcopy, "replace": replace}[
                operation
            ](value)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("refused", (False, True))
def test_all_layer_pickle_rejection_retains_denominator_and_copy_protection(
    layer, refused
):
    original = _outcome(layer, refused=refused, weight=F(11, 3))
    expected = g.count_family_outcomes([original])
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(original)
    recomputed = _outcome(layer, refused=refused, weight=F(11, 3))
    assert g.count_family_outcomes([original]) == expected
    assert g.count_family_outcomes([recomputed]) == expected
    assert recomputed.supported == original.supported
    with pytest.raises(g.InvalidFamilyInput):
        copy(recomputed)
    with pytest.raises(g.InvalidFamilyInput):
        deepcopy(recomputed)
    cls, values = type(recomputed), _values(recomputed)
    # Use the private capability solely to exercise seal-time validation.
    with pytest.raises(g.InvalidFamilyInput):
        g._computed(cls, **(values | {"weight": F(-1)}))


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    st.sampled_from(LAYERS),
    st.booleans(),
    st.integers(0, 1000),
    st.sampled_from((copy, deepcopy)),
)
def test_layer_provenance_is_deterministic_and_rejects_serialization(
    layer, refused, numerator, duplicate
):
    weight = F(numerator, 17)
    first = _outcome(layer, refused=refused, weight=weight)
    second = _outcome(layer, refused=refused, weight=weight)
    expected = g.count_family_outcomes([first])
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(first)
    assert g.count_family_outcomes([first]) == expected
    assert g.count_family_outcomes([second]) == expected
    with pytest.raises(g.InvalidFamilyInput):
        duplicate(second)
    with pytest.raises(g.InvalidFamilyInput):
        replace(second, weight=weight)


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("key,weight", (("", 1), ("valid", -1), (None, 1)))
def test_invalid_evaluator_metadata_precedes_computation(layer, key, weight):
    calls = []

    def compute():
        calls.append(True)
        return COMPUTE[layer](refused=True)

    with pytest.raises(g.InvalidFamilyInput):
        EVALUATE[layer](key, weight, compute)
    assert calls == []


@pytest.mark.parametrize("layer", LAYERS)
def test_invalid_computation_is_never_a_denominator_row(layer):
    def invalid():
        raise g.InvalidFamilyInput("invented malformed input")

    with pytest.raises(g.InvalidFamilyInput, match="invented malformed"):
        EVALUATE[layer]("invalid", 0, invalid)


@pytest.mark.parametrize("layer", ("ret", "arf", "recompute"))
def test_g_money_consumers_reject_other_layer_results_and_outcomes(layer):
    result = COMPUTE[layer]()
    row = _outcome(layer)
    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family("wrong-result", 1, lambda: result)
    with pytest.raises(g.InvalidFamilyInput):
        g.savings_clause_total(result)
    with pytest.raises(g.InvalidFamilyInput):
        guard.admit(result)
    for aggregate in (g.weighted_record_total, g.weighted_mean_record_total):
        with pytest.raises(g.InvalidFamilyInput):
            aggregate([row])


@pytest.mark.parametrize("layer", ("ret", "arf", "recompute"))
def test_g_guard_and_report_reject_sibling_refusal_reasons(layer, monkeypatch):
    from scripts import track_b_g_conformance_report as report

    error = _outcome(layer, refused=True).unsupported

    def refuse():
        raise error

    guard = g.SavingsClauseGuard(
        JAN,
        earlier_months_unknown=False,
        reading=g.SavingsClauseReading.LITERAL_REFUSAL,
    )
    with pytest.raises(g.InvalidFamilyInput):
        guard.evaluate("wrong-reason", 1, refuse)
    monkeypatch.setattr(
        report,
        "refusal_witnesses",
        lambda: {
            reason: ("sibling", refuse) for reason in g.UnsupportedReason
        },
    )
    with pytest.raises(g.InvalidFamilyInput):
        report.execute_refusal_witnesses()


@pytest.mark.parametrize("layer", ("g", "arf", "recompute", "ret"))
def test_common_counter_rejects_uninitialized_outcome_before_reading_metadata(
    layer,
):
    outcome_type = type(_outcome(layer, key="template", weight=F(1)))
    uninitialized = object.__new__(outcome_type)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([uninitialized])


def test_ret_evaluator_rejects_before_outcome_construction(monkeypatch):
    invalid = _unsealed(_ret())

    def unexpected_construction(*args, **kwargs):
        raise AssertionError("an invalid ledger reached outcome construction")

    monkeypatch.setattr(ret, "_computed", unexpected_construction)
    with pytest.raises(g.InvalidFamilyInput):
        ret.evaluate_ret("invalid", 1, lambda: invalid)


@given(st.sampled_from(LAYERS))
@settings(max_examples=8, deadline=None, derandomize=True)
def test_deleted_outcome_fields_are_input_errors(layer):
    outcome = _outcome(layer)
    object.__delattr__(outcome, "weight")
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([outcome])
