"""Statutory conformance: adversarial public-surface audit on invented cases.

No population, behavioral, or forecast claim is admitted. Round 10 already
enumerates every G constructor field and function argument; round 13's R3
file enumerates every R2/R3 declaration field. This audit pins that complete
surface, adds mutable numeric subclasses at public boundaries, and attacks
every sealed class through construction, serialization, and forged state.
"""

import ast
import copyreg
import inspect
import pickle
from collections.abc import Mapping
from copy import copy, deepcopy
from dataclasses import fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum
from fractions import Fraction as F
from functools import cache
from pathlib import Path

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import _provenance as provenance
from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import recompute as c
from populace_dynamics.track_b import ret_grace as grace
from populace_dynamics.track_b import ret_ledger as ret
from populace_dynamics.track_b.ret_params import load_ret_parameters
from tests.test_track_b_gross_benefits_fix_round_10_api import (
    CLASS_ERRORS,
    FUNCTION_ARGUMENTS,
    METHOD_ARGUMENTS,
    READ_MEMBERS,
    _world,
)
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE,
    EVALUATE,
    _outcome,
)
from tests.test_track_b_r3_fix_round_13 import MUTATION_CASES
from tests.track_b_gross_benefit_support import ssa_params

# Every module-owned public definition is classified explicitly. G's larger
# inventory has its own argument/field-level assertions in the round-10 API
# file. New R2/R3 functions or classes must be added here deliberately.
PUBLIC_NAMES = {
    grace: {
        "BenefitType",
        "GraceKind",
        "DisabilityGraceReading",
        "TerminationReason",
        "GraceMonth",
        "GraceYearState",
        "TerminationEvent",
        "GraceYearDecision",
        "grace_year",
    },
    ret: {
        "RETUnsupportedReason",
        "RETConfigurationUnsupported",
        "RecordKind",
        "SuspensionMethod",
        "MonthlyLimitPolicy",
        "NESEProrationPolicy",
        "WorkEarnings",
        "RETBeneficiary",
        "RecordYear",
        "calculated_excess",
        "countable_earnings",
        "PartialPaymentAllocation",
        "partial_payments",
        "BeneficiaryMonth",
        "WorkerLedger",
        "RETLedger",
        "apply_ret_year",
        "RETOutcome",
        "evaluate_ret",
        "count_ret_outcomes",
        "weighted_ret_total",
    },
    a: {
        "ARFBenefitKind",
        "ARFUnsupportedReason",
        "ARFConfigurationUnsupported",
        "SpouseOwnSequence",
        "age_attainment_month",
        "full_retirement_age_month",
        "SpouseOwnBenefit",
        "ARFClaim",
        "ARFResult",
        "ARFOutcome",
        "apply_arf",
        "evaluate_arf",
        "count_arf_outcomes",
    },
    c: {
        "EarningsAvailability",
        "PIAFormula",
        "RecomputationCondition",
        "RecomputationUnsupportedReason",
        "RecomputationConfigurationUnsupported",
        "RecomputationBasis",
        "RecomputationDecision",
        "RecomputationResult",
        "RecomputationOutcome",
        "evaluate_recomputation",
        "weighted_recomputed_pia",
        "eligibility_bend_points",
        "exact_pia",
        "earnings_aime",
        "recomputation_decision",
        "annual_recomputation",
        "recompute_sequence",
    },
    provenance: {"InvalidFamilyInput"},
}
PUBLIC_MEMBERS = {
    "RETLedger": {"for_beneficiary"},
    "RETOutcome": {"supported"},
    "ARFOutcome": {"supported"},
    "RecomputationOutcome": {"supported"},
}
SURFACE_TESTS = {
    grace: ("test_track_b_ret_grace.py", "test_track_b_r3_fix_round_13.py"),
    ret: ("test_track_b_ret_ledger.py", "test_track_b_r3_fix_round_13.py"),
    a: ("test_track_b_arf.py", "test_track_b_r3_fix_round_13.py"),
    c: ("test_track_b_recompute.py", "test_track_b_r3_fix_round_13.py"),
    provenance: ("test_track_b_gross_benefits_fix_round_12_contract.py",),
}


def _public_definitions(module):
    tree = ast.parse(Path(module.__file__).read_text())
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    }


def test_cross_layer_public_names_and_members_have_explicit_audit_coverage():
    assert _public_definitions(g) == (
        set(FUNCTION_ARGUMENTS)
        | set(CLASS_ERRORS)
        | {
            "UnsupportedReason",
            "FamilyTargetBlocked",
            "FamilyKind",
            "Role",
            "RecordCondition",
            "BeneficiaryCondition",
            "OwnBenefitKind",
        }
    )
    for module, names in PUBLIC_NAMES.items():
        assert _public_definitions(module) == names
        assert all(
            (Path(__file__).parent / path).is_file()
            for path in SURFACE_TESTS[module]
        )
    for module in (g, *PUBLIC_NAMES):
        for name in _public_definitions(module):
            cls = getattr(module, name)
            if not inspect.isclass(cls) or issubclass(cls, Enum):
                continue
            observed = {
                key
                for key, value in vars(cls).items()
                if not key.startswith("_")
                and (inspect.isfunction(value) or isinstance(value, property))
            }
            expected = READ_MEMBERS.get(name, PUBLIC_MEMBERS.get(name, set()))
            if cls is g.SavingsClauseGuard:
                expected = expected | set(METHOD_ARGUMENTS)
            assert observed == expected, name


class BuiltinEquality(type(F)):
    """Type membership must not trust caller-defined metaclass equality."""

    def __eq__(cls, other):
        if other is cls.spoofed_builtin:
            return True
        return super().__eq__(other)

    __hash__ = type.__hash__


class MutableInt(int, metaclass=BuiltinEquality):
    spoofed_builtin = int


class MutableFraction(F, metaclass=BuiltinEquality):
    spoofed_builtin = F

    def __mul__(self, other):
        return self.value * other

    def __radd__(self, other):
        return other + self.value


class MutableDecimal(Decimal, metaclass=BuiltinEquality):
    spoofed_builtin = Decimal


def _mutable(kind, value):
    if kind is MutableDecimal:
        exact = F(value)
        result = kind(Decimal(exact.numerator) / Decimal(exact.denominator))
    else:
        result = kind(value)
    result.value = F(value)
    return result


def _assert_builtin_numbers(value):
    if isinstance(value, Enum):
        return
    if isinstance(value, (int, float, F, Decimal)):
        assert any(
            type(value) is kind for kind in (bool, int, float, F, Decimal)
        )
    elif is_dataclass(value):
        for field in fields(value):
            _assert_builtin_numbers(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_builtin_numbers(key)
            _assert_builtin_numbers(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _assert_builtin_numbers(item)


G_NUMERIC_ARGUMENTS = (
    ("floor_dime", "amount"),
    ("ceil_dime", "amount"),
    ("whole_dollars", "amount"),
    ("family_maximum_formula", "pia"),
    ("family_maximum_formula", "eligibility_year"),
    ("family_maximum_bend_points", "eligibility_year"),
    ("retirement_survivor_family_maximum", "pia"),
    ("retirement_survivor_family_maximum", "eligibility_year"),
    ("disability_family_maximum", "pia"),
    ("disability_family_maximum", "aime"),
    ("increase_by_colas", "amount"),
    ("applicable_cola_percents", "eligibility_year"),
    ("worker_reduction_fraction", "months"),
    ("spouse_reduction_fraction", "months"),
    ("survivor_reduction_fraction", "months"),
    ("survivor_reduction_fraction", "reduction_period_months"),
    ("delayed_credit_window_months", "birth_year"),
    ("worker_age_adjusted", "pia"),
    ("worker_age_adjusted", "reduction_months"),
    ("worker_age_adjusted", "delayed_credit_months"),
    ("worker_age_adjusted", "birth_year"),
    ("spouse_age_reduced", "amount"),
    ("spouse_age_reduced", "reduction_months"),
    ("survivor_age_reduced", "amount"),
    ("survivor_age_reduced", "reduction_months"),
    ("survivor_age_reduced", "reduction_period_months"),
    ("original_benefit", "pia"),
    ("maximum_redistribution_rates", "available"),
    ("evaluate_family", "weight"),
    ("household_month_outcome", "weight"),
)


@pytest.mark.parametrize("name,argument", G_NUMERIC_ARGUMENTS)
@pytest.mark.parametrize("kind", (MutableInt, MutableFraction, MutableDecimal))
@settings(max_examples=2, deadline=None)
@given(pia=st.integers(1, 2000))
def test_g_numeric_arguments_canonicalize_or_reject_mutable_subclasses(
    name, argument, kind, pia
):
    _, world, _ = _world(pia)
    inputs = {key: world[key] for key in FUNCTION_ARGUMENTS[name]}
    raw = inputs[argument]
    # Fraction weights need a nonintegral constructor for Fraction/Decimal;
    # integer subclasses use an equally valid whole-number weight instead.
    raw = int(raw) if kind is MutableInt else raw
    value = _mutable(kind, raw)
    inputs[argument] = value
    try:
        result = getattr(g, name)(**inputs)
    except g.InvalidFamilyInput:
        return
    _assert_builtin_numbers(result)
    before = repr(result)
    value.value = F(0)
    assert repr(result) == before
    _assert_builtin_numbers(result)


@pytest.mark.parametrize("kind", (MutableInt, MutableFraction, MutableDecimal))
@settings(max_examples=12, deadline=None)
@given(index=st.integers(0, 11))
def test_nested_ssa_and_ret_parameter_numbers_are_rejected_before_refusal(
    kind, index
):
    params = ssa_params(nawi=dict(ssa_params().nawi))
    params.nawi[1977] = _mutable(kind, 9779)
    # An early eligibility year would otherwise be a coverage refusal.
    with pytest.raises(g.InvalidFamilyInput):
        g.retirement_survivor_family_maximum(1000, 1982, params)
    parameters = load_ret_parameters()
    year = parameters.for_year(2026)
    object.__setattr__(
        year.lower_exempt_amount, "value", _mutable(kind, 24480 + index)
    )
    member = ret.RETBeneficiary(
        "nh",
        (grace.BenefitType.RIB,) * 12,
        frozenset(range(1, 13)),
        (F(1),) * 12,
        (F(1),) * 12,
    )
    with pytest.raises(g.InvalidFamilyInput):
        ret.apply_ret_year(
            ret.RecordYear(
                2026, "nh", beneficiaries=(member,), foreign_work=True
            ),
            parameters,
        )
    # These private helpers implement the shared declared-number policy;
    # exercise their type checks directly as well as the public entries.
    number = _mutable(kind, 1500)
    with pytest.raises(g.InvalidFamilyInput):
        provenance._exact_number(number, "number")
    with pytest.raises(g.InvalidFamilyInput):
        provenance._rebuild_declared(number)
    with pytest.raises(g.InvalidFamilyInput):
        provenance._seal_value(number)

    # Equality of a subclass's metaclass with int cannot make an altered
    # public whole-dollar field compare equal to its original seal.
    result = COMPUTE["g"]()
    object.__setattr__(
        result,
        "record_total_whole_dollars",
        _mutable(MutableInt, result.record_total_whole_dollars),
    )
    with pytest.raises(g.InvalidFamilyInput):
        g.evaluate_family("metaclass-field", 1, lambda: result)


def _declaration_cases():
    objects, _, _ = _world(100)
    cases = {
        name: value
        for name, value in objects.items()
        if is_dataclass(value)
        and not isinstance(value, provenance._SealedResult)
    }
    for _, factory, _, _, _ in MUTATION_CASES:
        value = factory()
        cases[type(value).__name__] = value
    return cases


@pytest.mark.parametrize("name", tuple(_declaration_cases()))
@settings(max_examples=8, deadline=None, derandomize=True)
@given(
    collection=st.sampled_from((set, frozenset, tuple, list)),
    condition_index=st.integers(0, 50),
)
@example(collection=set, condition_index=0)
def test_declaration_subclasses_cannot_override_constructor_validation(
    name, collection, condition_index
):
    value = _declaration_cases()[name]
    subtype = type(f"Forged{name}", (type(value),), {})
    arguments = {
        field.name: getattr(value, field.name) for field in fields(value)
    }
    with pytest.raises(g.InvalidFamilyInput):
        subtype(**arguments)
    if any(
        type(value) is declaration
        for declaration in (g.Beneficiary, g.WorkerRecord, g.RecordState)
    ):

        class ChangingConditions(metaclass=BuiltinEquality):
            spoofed_builtin = collection

            def __init__(self):
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                first = (
                    g.BeneficiaryCondition.ENTITLED_ON_ANOTHER_RECORD
                    if type(value) is g.Beneficiary
                    else g.RecordCondition.ADMINISTRATIVE_FINALITY
                )
                conditions = (
                    first,
                    *(c for c in type(first) if c is not first),
                )
                condition = conditions[condition_index % len(conditions)]
                return iter((condition,) if self.iterations == 1 else ())

        # Unknown iterable types cannot impersonate a declared condition
        # collection, then change between validation and normalization.
        with pytest.raises(g.InvalidFamilyInput):
            type(value)(**{**arguments, "conditions": ChangingConditions()})


@pytest.mark.parametrize("case", MUTATION_CASES, ids=lambda case: case[0])
def test_object_new_declarations_do_not_hide_missing_fields(case):
    _, factory, consumer, field, _ = case
    original = factory()
    forged = object.__new__(type(original))
    for item in fields(original):
        if item.name != field:
            object.__setattr__(forged, item.name, getattr(original, item.name))
    # Dataclass defaults are class attributes. Plant a sentinel so the
    # deliberately missing field cannot fall back to an innocent default.
    object.__setattr__(forged, field, object())
    with pytest.raises(g.InvalidFamilyInput):
        consumer(forged)


@cache
def _sealed_samples():
    objects, _, _ = _world(100)
    samples = {
        type(value).__name__: value
        for value in objects.values()
        if isinstance(value, provenance._SealedResult)
    }
    for layer in COMPUTE:
        for refused in (False, True):
            outcome = _outcome(layer, refused=refused)
            samples[type(outcome).__name__] = outcome
            result = (
                outcome.unsupported
                if refused
                else getattr(
                    outcome,
                    {"ret": "ledger", "recompute": "result"}.get(
                        layer, "benefits"
                    ),
                )
            )
            samples[type(result).__name__] = result
    ledger = COMPUTE["ret"]()
    samples["WorkerLedger"] = ledger.workers[0]
    samples["BeneficiaryMonth"] = ledger.months[0]
    samples["PartialPaymentAllocation"] = ret.partial_payments(
        1, {"nh": 2}, {"nh": 2}
    )
    samples["GraceYearDecision"] = grace.grace_year(
        2026, grace.GraceYearState(), [grace.GraceMonth()] * 12
    )
    samples["RecomputationDecision"] = c.recomputation_decision(1, 2)
    return samples


SEALED_NAMES = (
    "BeneficiaryBenefit",
    "FamilyBenefits",
    "HouseholdBenefits",
    "FamilyOutcome",
    "FamilyDenominator",
    "FamilyConfigurationUnsupported",
    "RETConfigurationUnsupported",
    "PartialPaymentAllocation",
    "BeneficiaryMonth",
    "WorkerLedger",
    "RETLedger",
    "RETOutcome",
    "GraceYearDecision",
    "ARFConfigurationUnsupported",
    "ARFResult",
    "ARFOutcome",
    "RecomputationConfigurationUnsupported",
    "RecomputationDecision",
    "RecomputationResult",
    "RecomputationOutcome",
)


def test_every_declared_sealed_class_has_an_adversarial_sample():
    assert set(_sealed_samples()) == set(SEALED_NAMES)
    assert {cls.__name__ for cls in provenance._RESULT_TYPES} == set(
        SEALED_NAMES
    )


@pytest.mark.parametrize("name", SEALED_NAMES)
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_every_sealed_value_refuses_every_pickle_protocol(name, protocol):
    value = _sealed_samples()[name]
    with pytest.raises(g.InvalidFamilyInput):
        pickle.dumps(value, protocol=protocol)


@pytest.mark.parametrize("name", SEALED_NAMES)
@pytest.mark.parametrize(
    "operation",
    (
        copy,
        deepcopy,
        lambda value: copyreg._reduce_ex(value, 0),
        lambda value: copyreg._reduce_ex(value, 1),
    ),
)
def test_copy_and_copyreg_cannot_export_sealed_state(name, operation):
    value = _sealed_samples()[name]
    with pytest.raises(g.InvalidFamilyInput):
        operation(value)


@pytest.mark.parametrize("name", SEALED_NAMES)
def test_object_new_and_subclasses_cannot_admit_sealed_values(name):
    original = _sealed_samples()[name]
    cls = type(original)
    with pytest.raises(g.InvalidFamilyInput):
        cls()
    subtype = type(f"Forged{name}", (cls,), {})
    with pytest.raises(g.InvalidFamilyInput):
        subtype()
    for forged_type in (cls, subtype):
        forged = (
            Exception.__new__(forged_type)
            if issubclass(cls, Exception)
            else object.__new__(forged_type)
        )
        # Copy all public fields without obtaining any private capability.
        values = (
            {
                key: getattr(original, key)
                for key in ("reason", "detail", "beneficiary_id", "record_id")
            }
            if isinstance(original, g.FamilyConfigurationUnsupported)
            else {
                field.name: getattr(original, field.name)
                for field in fields(original)
            }
        )
        for key, value in values.items():
            object.__setattr__(forged, key, value)
        for evaluate in EVALUATE.values():
            with pytest.raises(g.InvalidFamilyInput):
                if isinstance(forged, g.FamilyConfigurationUnsupported):

                    def compute(forged=forged):
                        raise forged

                else:

                    def compute(forged=forged):
                        return forged

                evaluate("forged", 1, compute)


@pytest.mark.parametrize("layer", tuple(COMPUTE))
def test_wrong_layer_reason_cannot_be_counted_as_refusal(layer):
    refusal = _outcome(layer, refused=True).unsupported
    wrong = (
        a.ARFUnsupportedReason.OTHER_SUSPENSION
        if layer != "arf"
        else ret.RETUnsupportedReason.FOREIGN_WORK
    )
    object.__setattr__(refusal, "reason", wrong)

    def refuse():
        raise refusal

    with pytest.raises(g.InvalidFamilyInput):
        EVALUATE[layer]("wrong-reason", 1, refuse)


RESULT_ACCESSORS = tuple(
    (name, member)
    for name, members in {**READ_MEMBERS, **PUBLIC_MEMBERS}.items()
    if name in SEALED_NAMES
    for member in sorted(members)
)


@pytest.mark.parametrize("name,member", RESULT_ACCESSORS)
def test_every_result_accessor_rejects_unsealed_public_fields(name, member):
    original = _sealed_samples()[name]
    forged = object.__new__(type(original))
    for field in fields(original):
        object.__setattr__(forged, field.name, getattr(original, field.name))
    with pytest.raises(g.InvalidFamilyInput):
        result = getattr(forged, member)
        if callable(result):
            result("worker") if member == "for_beneficiary" else result()


def test_family_by_id_returns_detached_beneficiary_rows():
    result = COMPUTE["g"]()
    first = result.by_id()
    twin = result.by_id()
    key = next(iter(first))
    assert first == twin
    assert first[key] is not twin[key]
    object.__setattr__(first[key], "auxiliary_payable", F(9999))
    assert result.by_id() == twin
    assert g.evaluate_family("unchanged", 1, lambda: result).supported


@pytest.mark.parametrize(
    "field", tuple(item.name for item in fields(ssa_params()))
)
def test_every_ssa_field_is_revalidated_before_historical_coverage(field):
    params = ssa_params(nawi=dict(ssa_params().nawi))
    object.__setattr__(params, field, object())
    with pytest.raises(g.InvalidFamilyInput):
        g.retirement_survivor_family_maximum(1000, 1982, params)


def test_ssa_parameter_validation_checks_the_actual_mapping_snapshot():
    class ChangingMapping(Mapping):
        def __init__(self):
            self.reads = 0

        def __iter__(self):
            return iter((1951,))

        def __len__(self):
            return 1

        def __getitem__(self, key):
            return 1000

        def items(self):
            self.reads += 1
            return ((1951 if self.reads == 1 else "invalid year", 1000),)

    params = ssa_params(wage_base=ChangingMapping())
    with pytest.raises(g.InvalidFamilyInput):
        g.statutory_rates(params)


def _numeric_leaves(value, path=()):
    if type(value) in (int, float, F, Decimal):
        yield path, value
    elif is_dataclass(value):
        for field in fields(value):
            yield from _numeric_leaves(
                getattr(value, field.name), (*path, ("field", field.name))
            )
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _numeric_leaves(key, (*path, ("key", key)))
            yield from _numeric_leaves(item, (*path, ("value", key)))
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            yield from _numeric_leaves(item, (*path, ("index", index)))


def _replace_leaf(value, path, replacement):
    if not path:
        return replacement
    (kind, key), *rest = path
    if kind == "field":
        return replace(
            value,
            **{key: _replace_leaf(getattr(value, key), rest, replacement)},
        )
    if kind in ("key", "value"):
        return {
            (
                _replace_leaf(k, rest, replacement)
                if kind == "key" and k == key
                else k
            ): (
                _replace_leaf(v, rest, replacement)
                if kind == "value" and k == key
                else v
            )
            for k, v in value.items()
        }
    return type(value)(
        _replace_leaf(item, rest, replacement) if index == key else item
        for index, item in enumerate(value)
    )


SSA_NUMERIC_LEAVES = tuple(
    _numeric_leaves(ssa_params(wage_base={1951: 1_000_000}))
)


@pytest.mark.parametrize(
    "path,plain", SSA_NUMERIC_LEAVES, ids=lambda value: str(value)
)
@pytest.mark.parametrize("kind", (MutableInt, MutableFraction, MutableDecimal))
def test_every_ssa_numeric_leaf_rejects_subclasses_before_coverage(
    path, plain, kind
):
    params = ssa_params(wage_base={1951: 1_000_000})
    value = _mutable(kind, int(plain) if kind is MutableInt else plain)
    altered = _replace_leaf(params, path, value)
    with pytest.raises(g.InvalidFamilyInput):
        g.retirement_survivor_family_maximum(1000, 1982, altered)


@pytest.mark.parametrize(
    "layer,field",
    (
        ("g", "beneficiaries"),
        ("ret", "months"),
        ("ret", "workers"),
        ("recompute", "decision"),
    ),
)
@settings(max_examples=3, deadline=None)
@given(weight=st.integers(0, 20))
def test_forged_nested_rows_cannot_enter_evaluators_or_denominators(
    layer, field, weight
):
    result = COMPUTE[layer]()
    outcome = EVALUATE[layer]("original", weight, lambda: result)
    container = getattr(result, field)
    original = container[0] if isinstance(container, tuple) else container
    forged = object.__new__(type(original))
    for item in fields(original):
        object.__setattr__(forged, item.name, getattr(original, item.name))
    replacement = (
        (forged, *container[1:]) if isinstance(container, tuple) else forged
    )
    object.__setattr__(result, field, replacement)
    with pytest.raises(g.InvalidFamilyInput):
        EVALUATE[layer]("changed", weight, lambda: result)
    with pytest.raises(g.InvalidFamilyInput):
        g.count_family_outcomes([outcome])
