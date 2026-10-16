"""Statutory conformance: invented schema-boundary adversarial cases.

These cases admit input-contract and denominator claims only, without any
population, behavioral, forecast or administrative-payment claim.
"""

import inspect
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, replace
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction as F
from types import MappingProxyType, UnionType
from typing import Union, get_args, get_origin, get_type_hints

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import _provenance as provenance
from populace_dynamics.track_b import arf as a
from populace_dynamics.track_b import gross_benefits as g
from populace_dynamics.track_b import recompute as r
from populace_dynamics.track_b import ret_grace as grace
from populace_dynamics.track_b import ret_ledger as ret
from tests.test_track_b_gross_benefits_fix_round_10_api import (
    FUNCTION_ARGUMENTS,
    METHOD_ARGUMENTS,
    _world,
)
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE,
    EVALUATE,
    LAYERS,
    PARAMS,
    RET_PARAMS,
)


def _zero_rows(layer, compute):
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(EVALUATE[layer]("invalid", 1, compute))
    counts = g.count_family_outcomes(rows)
    assert counts.rows == counts.unsupported_rows == counts.supported_rows == 0
    assert counts.weight == counts.unsupported_weight == 0


def _g_case(*, kind=g.FamilyKind.RETIREMENT, conditions=()):
    return g.family_benefits(
        g.RecordState(
            kind,
            1000,
            1500,
            g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, 1000),
            conditions=conditions,
        ),
        (g.Beneficiary("child", g.Role.CHILD),),
        payment_month=g.YearMonth(2026, 1),
        params=PARAMS,
        standalone=True,
    )


def _ret_case(*, work=None, params=RET_PARAMS):
    member = ret.RETBeneficiary(
        "nh",
        (ret.BenefitType.RIB,) * 12,
        frozenset(range(1, 13)),
        (F(0),) * 12,
        (F(0),) * 12,
        earnings=ret.WorkEarnings() if work is None else work,
    )
    return ret.apply_ret_year(
        ret.RecordYear(2026, "nh", beneficiaries=(member,), foreign_work=True),
        params,
    )


def _arf_case(*, kind=a.ARFBenefitKind.RIB, conditions=()):
    return a.apply_arf(
        a.ARFClaim(
            kind,
            date(1960, 1, 2),
            g.YearMonth(2022, 1),
            1300,
            conditions=conditions,
        ),
        payment_month=g.YearMonth(2027, 1),
        params=PARAMS,
    )


def _recompute_case(*, formula=r.PIAFormula.AIME, conditions=(), colas=None):
    return r.annual_recomputation(
        r.RecomputationBasis(
            2020,
            2018,
            35,
            (960, 5785),
            g.YearMonth(2020, 6),
            formula=formula,
            conditions=conditions,
        ),
        dict.fromkeys(range(1951, 2021), 0),
        2020,
        0,
        PARAMS,
        {2020: 0} if colas is None else colas,
    )


@pytest.mark.parametrize("layer", LAYERS)
def test_forged_enum_is_input_error_before_any_denominator_row(layer):
    def compute():
        if layer == "g":
            return g.family_benefits(
                g.RecordState(
                    object.__new__(g.FamilyKind),
                    1000,
                    1500,
                    eligibility_year=1982,
                ),
                (),
                payment_month=g.YearMonth(2026, 1),
                params=PARAMS,
                standalone=True,
            )
        if layer == "ret":
            ret.countable_earnings(
                ret.WorkEarnings(nese=-1, self_employment_months={1, 2}),
                2,
                nese_proration_policy=object.__new__(ret.NESEProrationPolicy),
            )
            return _ret_case()
        if layer == "arf":
            return _arf_case(
                kind=object.__new__(a.ARFBenefitKind),
                conditions=(a.ARFUnsupportedReason.OTHER_SUSPENSION,),
            )
        return _recompute_case(formula=str.__new__(r.PIAFormula, "aime"))

    _zero_rows(layer, compute)


class PretendDeclaration:
    def __init__(self, declaration_type):
        self.declaration_type = declaration_type

    @property
    def __class__(self):
        return self.declaration_type


@pytest.mark.parametrize("layer", LAYERS)
def test_class_property_cannot_impersonate_a_declaration(layer):
    def compute():
        if layer == "ret":
            return _ret_case(work=PretendDeclaration(ret.WorkEarnings))
        if layer == "g":
            return g.family_benefits(
                PretendDeclaration(g.RecordState),
                (),
                payment_month=g.YearMonth(2026, 1),
                params=PARAMS,
                standalone=True,
            )
        if layer == "arf":
            return a.apply_arf(
                PretendDeclaration(a.ARFClaim),
                payment_month=g.YearMonth(2027, 1),
                params=PARAMS,
            )
        return r.annual_recomputation(
            PretendDeclaration(r.RecomputationBasis),
            dict.fromkeys(range(1951, 2021), 0),
            2020,
            0,
            PARAMS,
            {2020: 0},
        )

    _zero_rows(layer, compute)


class RawYearMapping(Mapping):
    def __init__(self, year, reverse=False, value=0):
        self.keys = (float(year), year) if reverse else (year, float(year))
        self.value = value

    def __iter__(self):
        return iter(self.keys)

    def __len__(self):
        return 2

    def __getitem__(self, key):
        return self.value


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("reverse", (False, True))
def test_raw_mapping_keys_are_validated_before_deduplication(layer, reverse):
    def compute():
        if layer == "g":
            return g.applicable_cola_percents(
                1982, g.YearMonth(1983, 1), RawYearMapping(1982, reverse)
            )
        if layer == "ret":
            params = replace(RET_PARAMS)
            object.__setattr__(
                params,
                "years",
                RawYearMapping(2026, reverse, RET_PARAMS.for_year(2026)),
            )
            return _ret_case(params=params)
        if layer == "arf":
            params = replace(PARAMS)
            object.__setattr__(params, "nawi", RawYearMapping(1982, reverse))
            a.full_retirement_age_month(
                date(1960, 1, 2), a.ARFBenefitKind.RIB, params
            )
            return COMPUTE[layer]()
        return _recompute_case(
            formula=r.PIAFormula.GUARANTEE,
            colas=RawYearMapping(2020, reverse),
        )

    _zero_rows(layer, compute)


class ChangingHash:
    def __init__(self, canonical, bucket):
        self.canonical = canonical
        self.bucket = bucket

    def __hash__(self):
        return self.bucket

    def __eq__(self, other):
        return other is self.canonical


def _raw_collision(canonical):
    # Select an insertion bucket that puts the canonical member first.
    # This removes the reviewer's dependence on PYTHONHASHSEED=0.
    for padding in (0, 32, 256):
        for bucket in range(1024):
            if bucket == hash(canonical):
                continue
            invalid = ChangingHash(canonical, bucket)
            raw = {canonical, invalid}
            # Preserve a larger set table when the canonical member would
            # otherwise occupy its final bucket; removal does not shrink it.
            fillers = [object() for _ in range(padding)]
            raw.update(fillers)
            for filler in fillers:
                raw.remove(filler)
            if len(raw) == 2 and next(iter(raw)) is canonical:
                invalid.bucket = hash(canonical)
                assert len(raw) == 2
                return raw
    raise AssertionError("could not construct the reviewer's collision")


@pytest.mark.parametrize("layer", LAYERS)
def test_raw_set_elements_are_validated_before_rehashing(layer):
    def compute():
        if layer == "g":
            return _g_case(
                conditions=_raw_collision(
                    g.RecordCondition.ADMINISTRATIVE_FINALITY
                )
            )
        if layer == "ret":
            return _ret_case(
                work=ret.WorkEarnings(self_employment_months=_raw_collision(1))
            )
        if layer == "arf":
            return _arf_case(
                conditions=_raw_collision(
                    a.ARFUnsupportedReason.OTHER_SUSPENSION
                )
            )
        return _recompute_case(
            conditions=_raw_collision(
                r.RecomputationCondition.ADMINISTRATIVE_FINALITY
            )
        )

    _zero_rows(layer, compute)


@dataclass
class DataclassCommand:
    layer: str
    calls: int = 0

    def __call__(self):
        self.calls += 1
        return COMPUTE[self.layer]()


@pytest.mark.parametrize("layer", LAYERS)
def test_callable_dataclass_is_invoked_once_and_result_is_checked(layer):
    command = DataclassCommand(layer)
    row = EVALUATE[layer]("dataclass", 1, command)
    assert command.calls == 1
    assert row.supported
    expected = EVALUATE[layer]("dataclass", 1, COMPUTE[layer])
    assert row == expected
    counts = g.count_family_outcomes([row])
    assert counts.rows == counts.supported_rows == 1
    assert counts.weight == counts.supported_weight == 1


@pytest.mark.parametrize("layer", LAYERS)
def test_callable_dataclass_cannot_return_an_undeclared_result(layer):
    @dataclass
    class InvalidCommand:
        calls: int = 0

        def __call__(self):
            self.calls += 1
            return object()

    command = InvalidCommand()
    _zero_rows(layer, command)
    assert command.calls == 1


@pytest.mark.parametrize("layer", LAYERS)
def test_valid_float_evaluator_weights_keep_their_exact_decimal_value(layer):
    if layer == "ret":
        calls = []

        def compute():
            calls.append(True)
            return COMPUTE[layer]()

        rows = []
        with pytest.raises(g.InvalidFamilyInput):
            rows.append(EVALUATE[layer]("float-weight", 0.1, compute))
        assert calls == []
        assert g.count_family_outcomes(rows).rows == 0
        row = EVALUATE[layer]("exact-weight", F(1, 10), compute)
        assert calls == [True]
    else:
        row = EVALUATE[layer]("decimal-weight", 0.1, COMPUTE[layer])
    assert row.weight == F(1, 10)
    counts = g.count_family_outcomes([row])
    assert counts.rows == counts.supported_rows == 1
    assert counts.weight == counts.supported_weight == F(1, 10)


class ProtocolMapping(Mapping):
    def __init__(self, values):
        self.values = dict(values)
        self.calls = []

    def __iter__(self):
        self.calls.append("iter")
        return iter(self.values)

    def __len__(self):
        self.calls.append("len")
        return len(self.values)

    def __getitem__(self, key):
        self.calls.append("getitem")
        return self.values[key]


@pytest.mark.parametrize(
    "layer,field",
    (("g", "records"), ("ret", "crediting_months"), ("ret", "reconciliation")),
)
def test_sealed_mapping_proxy_cannot_hide_a_custom_mapping(layer, field):
    if layer == "g":
        objects, _, _ = _world(1000)
        result = objects["HouseholdBenefits"]
    else:
        result = COMPUTE[layer]()
    raw = ProtocolMapping(getattr(result, field))
    object.__setattr__(result, field, MappingProxyType(raw))
    _zero_rows(layer, lambda: result)
    assert raw.calls == []


@pytest.mark.parametrize("layer", LAYERS)
def test_valid_review_controls_keep_their_original_refusal_and_money(layer):
    row = EVALUATE[layer]("supported", 1, COMPUTE[layer])
    assert row.supported
    refused = EVALUATE[layer](
        "refused", 1, lambda: COMPUTE[layer](refused=True)
    )
    assert not refused.supported
    assert g.count_family_outcomes([row, refused]).rows == 2
    if layer == "g":
        administrative = EVALUATE[layer](
            "administrative",
            1,
            lambda: _g_case(
                conditions={g.RecordCondition.ADMINISTRATIVE_FINALITY}
            ),
        )
        assert administrative.unsupported.reason is (
            g.UnsupportedReason.ADMINISTRATIVE_FINALITY
        )
    if layer == "ret":
        work = ret.WorkEarnings(nese=-1, self_employment_months={1, 2})
        assert (
            ret.countable_earnings(
                work, 2, nese_proration_policy=ret.NESEProrationPolicy.FLOOR
            )
            == -1
        )


MODULES = (g, grace, ret, a, r)
GUARD_PROPERTIES = tuple(
    name
    for name, descriptor in vars(g.SavingsClauseGuard).items()
    if type(descriptor) is property and not name.startswith("_")
)
PUBLIC_FUNCTIONS = tuple(
    (module, name, function)
    for module in MODULES
    for name, function in vars(module).items()
    if inspect.isfunction(function)
    and function.__module__ == module.__name__
    and not name.startswith("_")
)
PUBLIC_ARGUMENTS = tuple(
    (module, name, argument)
    for module, name, function in PUBLIC_FUNCTIONS
    for argument in inspect.signature(function).parameters
)
DECLARATION_FIELDS = tuple(
    (cls, item.name)
    for cls in sorted(
        provenance._DECLARATION_TYPES, key=lambda cls: cls.__name__
    )
    for item in fields(cls)
)


@pytest.fixture(scope="module")
def public_world():
    _, g_world, _ = _world(1000)
    work = ret.WorkEarnings()
    member = ret.RETBeneficiary(
        "nh",
        (grace.BenefitType.RIB,) * 12,
        frozenset(range(1, 13)),
        (F(1),) * 12,
        (F(1),) * 12,
    )
    record = ret.RecordYear(2026, "nh", beneficiaries=(member,))
    claim = a.ARFClaim(
        a.ARFBenefitKind.RIB, date(1960, 1, 2), g.YearMonth(2022, 1), 1300
    )
    basis = r.RecomputationBasis(
        2020, 2018, 35, (960, 5785), g.YearMonth(2020, 6)
    )
    outcomes = {
        layer: (EVALUATE[layer]("valid", 1, COMPUTE[layer]),)
        for layer in LAYERS
    }
    return {
        g: g_world,
        grace: {
            "year": 2026,
            "state": grace.GraceYearState(),
            "months": (grace.GraceMonth(),) * 12,
            "fra_month": None,
            "termination_events": (),
            "disability_reading": (
                grace.DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION
            ),
        },
        ret: {
            "earnings": work,
            "exempt": F(1),
            "rate": F(1, 2),
            "fra_month": None,
            "nese_proration_policy": ret.NESEProrationPolicy.FLOOR,
            "total": F(1),
            "rates": {"nh": F(1)},
            "original_rates": {"nh": F(1)},
            "record": record,
            "parameters": RET_PARAMS,
            "monthly_limit_policy": ret.MonthlyLimitPolicy.EXACT_TWELFTH,
            "key": "valid",
            "weight": F(1),
            "compute": COMPUTE["ret"],
            "outcomes": outcomes["ret"],
        },
        a: {
            "birth_date": date(1960, 1, 2),
            "age_months": 804,
            "kind": a.ARFBenefitKind.RIB,
            "params": PARAMS,
            "claim": claim,
            "payment_month": g.YearMonth(2027, 1),
            "key": "valid",
            "weight": F(1),
            "compute": COMPUTE["arf"],
            "outcomes": outcomes["arf"],
        },
        r: {
            "key": "valid",
            "weight": F(1),
            "compute": COMPUTE["recompute"],
            "outcomes": outcomes["recompute"],
            "eligibility_year": 2020,
            "params": PARAMS,
            "aime": 0,
            "bend_points": (960, 5785),
            "history": dict.fromkeys(range(1951, 2021), 0),
            "basis": basis,
            "earnings_year": 2020,
            "earnings_years": (2020,),
            "pia_of_record": 0,
            "candidate_pia": 0,
            "has_earnings": True,
            "eligibility_pia_of_record": 0,
            "december_cola_percent": {2020: 0},
            "death_month": None,
            "fra_month": None,
        },
    }


def _arguments(module, name, world):
    result = {
        argument: world[module][argument]
        for argument in inspect.signature(getattr(module, name)).parameters
    }
    if module is ret and name == "calculated_excess":
        result["earnings"] = F(2)
    return result


class AdversarialMetaclass(type):
    def __instancecheck__(cls, instance):
        raise AssertionError("untrusted __instancecheck__ executed")

    def __eq__(cls, other):
        return other is int or super().__eq__(other)

    __hash__ = type.__hash__


class MetaclassSpoof(metaclass=AdversarialMetaclass):
    pass


class GenericGetterUnknown:
    """Respond to any missing attribute without knowing private names."""

    def __init__(self):
        self.calls = 0

    def __getattr__(self, name):
        self.calls += 1
        return (lambda: None) if self.calls == 1 else None


class GuardSubclass(g.SavingsClauseGuard):
    pass


class LyingMapping(Mapping):
    """Reject the type before untrusted collection protocols run."""

    def __init__(self):
        self.calls = []

    def __iter__(self):
        self.calls.append("iter")
        return iter((1982, 1982.0))

    def __len__(self):
        self.calls.append("len")
        return 1

    def __getitem__(self, key):
        self.calls.append("getitem")
        return 0

    def __hash__(self):
        self.calls.append("hash")
        return len(self.calls)

    def __eq__(self, other):
        self.calls.append("eq")
        return True


class ChangingIterator:
    def __init__(self):
        self.calls = []

    def __iter__(self):
        self.calls.append("iter")
        return iter((0,) if len(self.calls) == 1 else (object(),))

    def __len__(self):
        self.calls.append("len")
        return len(self.calls)


SUBCLASSES = {
    name: type(f"Undeclared{name}", (kind,), {})
    for name, kind in (
        ("tuple", tuple),
        ("list", list),
        ("dict", dict),
        ("set", set),
        ("frozenset", frozenset),
        ("int", int),
        ("float", float),
        ("str", str),
        ("bytes", bytes),
        ("Fraction", F),
        ("Decimal", Decimal),
        ("date", date),
    )
}
ATTACKS = (
    "unknown",
    "class-property",
    "metaclass",
    "lying-mapping",
    "changing-iterator",
    "enum-object-new",
    "enum-str-new",
    *SUBCLASSES,
)


def _attack(kind, valid):
    if kind == "unknown":
        return object()
    if kind == "class-property":
        return PretendDeclaration(type(valid))
    if kind == "metaclass":
        return MetaclassSpoof()
    if kind == "lying-mapping":
        return LyingMapping()
    if kind == "changing-iterator":
        return ChangingIterator()
    if kind == "enum-object-new":
        return object.__new__(g.FamilyKind)
    if kind == "enum-str-new":
        return str.__new__(r.PIAFormula, "aime")
    if kind == "date":
        return SUBCLASSES[kind](1960, 1, 2)
    if kind in ("Fraction", "Decimal"):
        return SUBCLASSES[kind](1)
    return SUBCLASSES[kind]()


@pytest.mark.parametrize(
    "module,name,argument",
    PUBLIC_ARGUMENTS,
    ids=[
        f"{module.__name__.rsplit('.', 1)[-1]}.{name}.{argument}"
        for module, name, argument in PUBLIC_ARGUMENTS
    ],
)
@settings(max_examples=len(ATTACKS), deadline=None, derandomize=True)
@given(attack=st.sampled_from(ATTACKS))
def test_every_public_argument_rejects_undeclared_types_without_rows(
    module, name, argument, public_world, attack
):
    inputs = _arguments(module, name, public_world)
    invalid = _attack(attack, inputs[argument])
    inputs[argument] = invalid
    emitted = []
    with pytest.raises(g.InvalidFamilyInput):
        emitted.append(getattr(module, name)(**inputs))
    assert g.count_family_outcomes(emitted).rows == 0
    if type(invalid) in (LyingMapping, ChangingIterator):
        assert invalid.calls == []


@pytest.mark.parametrize("method", tuple(METHOD_ARGUMENTS))
@settings(max_examples=len(ATTACKS), deadline=None, derandomize=True)
@given(attack=st.sampled_from(ATTACKS), selected=st.integers(0, 3))
def test_guard_arguments_use_the_same_strict_boundary(
    method, attack, selected
):
    _, world, guard = _world(1000)
    arguments = METHOD_ARGUMENTS[method]
    inputs = {argument: world[argument] for argument in arguments}
    argument = arguments[selected % len(arguments)]
    inputs[argument] = _attack(attack, inputs[argument])
    before = vars(guard).copy()
    with pytest.raises(g.InvalidFamilyInput):
        getattr(guard, method)(**inputs)
    assert vars(guard) == before


@pytest.mark.parametrize("argument", ("first_month", "earlier_months_unknown"))
@settings(max_examples=len(ATTACKS), deadline=None, derandomize=True)
@given(attack=st.sampled_from(ATTACKS))
def test_guard_constructor_uses_the_same_strict_boundary(argument, attack):
    inputs = {
        "first_month": g.YearMonth(2026, 1),
        "earlier_months_unknown": False,
    }
    inputs[argument] = _attack(attack, inputs[argument])
    with pytest.raises(g.InvalidFamilyInput):
        g.SavingsClauseGuard(**inputs)


class KeywordName(str):
    def __hash__(self):
        self.hash_calls += 1
        return str.__hash__(self)


def _assert_call_binding_matches_inspect(function, seed):
    declared = inspect.signature(function)
    parameters = tuple(declared.parameters.values())
    positional = tuple(
        item.name
        for item in parameters
        if item.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    all_names = tuple(item.name for item in parameters)
    required = tuple(
        item.name
        for item in parameters
        if item.default is inspect.Parameter.empty
    )
    split = seed % (len(positional) + 1)
    styles = [
        ((), all_names),
        ((), tuple(reversed(all_names))),
        (
            positional,
            tuple(name for name in all_names if name not in positional),
        ),
        (
            positional[:split],
            tuple(
                name for name in all_names if name not in positional[:split]
            ),
        ),
        ((), required),
        ((), (*all_names, "_unknown_argument")),
        ((*positional, "_extra_positional"), ()),
    ]
    if required:
        styles.append(
            ((), tuple(name for name in all_names if name != required[0]))
        )
    if positional:
        styles.append(((positional[0],), all_names))
    for defaults in (False, True):
        bind = provenance._call_binder(function, defaults=defaults)
        keyword = KeywordName(all_names[0])
        keyword.hash_calls = 0
        untrusted_keywords = {keyword: object()}
        keyword.hash_calls = 0
        with pytest.raises(g.InvalidFamilyInput):
            bind((), untrusted_keywords)
        assert keyword.hash_calls == 0
        for positional_names, keyword_names in styles:
            # Reuse each cached layout with fresh values. The second call
            # must return its new caller values, never the first call's data.
            for _ in range(2):
                args = tuple(object() for _ in positional_names)
                kwargs = {name: object() for name in keyword_names}
                try:
                    expected = declared.bind(*args, **kwargs)
                except TypeError:
                    with pytest.raises(TypeError):
                        bind(args, kwargs)
                else:
                    if defaults:
                        expected.apply_defaults()
                    actual = bind(args, kwargs)
                    assert actual.keys() == expected.arguments.keys()
                    assert all(
                        actual[name] is value
                        for name, value in expected.arguments.items()
                    )


@settings(max_examples=8, deadline=None, derandomize=True)
@example(seed=0)
@given(seed=st.integers(0, 1000))
def test_every_public_argument_and_declaration_field_declares_a_schema(seed):
    for _, _, function in PUBLIC_FUNCTIONS:
        schemas = provenance._argument_schemas(inspect.unwrap(function))
        assert set(schemas) == set(inspect.signature(function).parameters)
        _assert_call_binding_matches_inspect(inspect.unwrap(function), seed)
    for cls in provenance._DECLARATION_TYPES:
        schemas = provenance._declaration_schemas(cls)
        assert set(schemas) == set(inspect.signature(cls).parameters)
        _assert_call_binding_matches_inspect(
            inspect.unwrap(cls.__init__), seed
        )
    for name in ("__init__", *METHOD_ARGUMENTS):
        method = getattr(g.SavingsClauseGuard, name)
        schemas = provenance._argument_schemas(inspect.unwrap(method))
        assert set(schemas) == set(inspect.signature(method).parameters)
        _assert_call_binding_matches_inspect(inspect.unwrap(method), seed)
    getter_errors = []
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1), earlier_months_unknown=False
    )
    assert len(GUARD_PROPERTIES) == 5
    for name in GUARD_PROPERTIES:
        getter = getattr(g.SavingsClauseGuard, name).fget
        schemas = provenance._argument_schemas(inspect.unwrap(getter))
        assert set(schemas) == {"self"}
        _assert_call_binding_matches_inspect(inspect.unwrap(getter), seed)
        invalid = [(_kind, _attack(_kind, guard)) for _kind in ATTACKS]
        invalid.extend(
            (
                ("generic-getattr", GenericGetterUnknown()),
                ("guard-subclass", object.__new__(GuardSubclass)),
            )
        )
        for kind, receiver in invalid:
            emitted = []
            try:
                emitted.append(getter(receiver))
            except g.InvalidFamilyInput:
                assert g.count_family_outcomes(emitted).rows == 0
            except Exception as error:
                getter_errors.append((name, kind, type(error).__name__))
            else:
                getter_errors.append((name, kind, "admitted unknown"))
            if type(receiver) is GenericGetterUnknown and receiver.calls:
                getter_errors.append((name, kind, "__getattr__ invoked"))
    assert getter_errors == []
    lookup = ret.RETLedger.for_beneficiary
    schemas = provenance._argument_schemas(inspect.unwrap(lookup))
    assert set(schemas) == {"self", "beneficiary_id"}
    _assert_call_binding_matches_inspect(inspect.unwrap(lookup), seed)
    lookup_inputs = {"self": COMPUTE["ret"](), "beneficiary_id": "worker"}
    for argument, valid in lookup_inputs.items():
        invalid = [(_kind, _attack(_kind, valid)) for _kind in ATTACKS]
        invalid.extend(
            (
                ("generic-getattr", GenericGetterUnknown()),
                ("guard-subclass", object.__new__(GuardSubclass)),
            )
        )
        for _, value in invalid:
            inputs = lookup_inputs | {argument: value}
            emitted = []
            with pytest.raises(g.InvalidFamilyInput):
                emitted.append(lookup(**inputs))
            assert g.count_family_outcomes(emitted).rows == 0
            if type(value) is GenericGetterUnknown:
                assert value.calls == 0


@pytest.fixture(scope="module")
def declaration_samples():
    from tests.test_track_b_gross_benefits_fix_round_13_audit import (
        _declaration_cases,
    )

    samples = {type(value): value for value in _declaration_cases().values()}
    assert provenance._DECLARATION_TYPES <= samples.keys()
    return samples


@pytest.mark.parametrize(
    "cls,field",
    DECLARATION_FIELDS,
    ids=[f"{cls.__name__}.{field}" for cls, field in DECLARATION_FIELDS],
)
@settings(max_examples=len(ATTACKS), deadline=None, derandomize=True)
@given(attack=st.sampled_from(ATTACKS))
def test_every_declaration_field_rejects_undeclared_types(
    cls, field, declaration_samples, attack
):
    sample = declaration_samples[cls]
    inputs = {item.name: getattr(sample, item.name) for item in fields(cls)}
    invalid = _attack(attack, inputs[field])
    inputs[field] = invalid
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(cls(**inputs))
    assert g.count_family_outcomes(rows).rows == 0
    if type(invalid) in (LyingMapping, ChangingIterator):
        assert invalid.calls == []


def _sample_annotation(annotation, samples):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        return _sample_annotation(
            next(item for item in args if item is not type(None)), samples
        )
    if origin in (Mapping, dict):
        return {
            _sample_annotation(args[0], samples): _sample_annotation(
                args[1], samples
            )
        }
    if origin in (Iterable, Sequence, tuple, list, set, frozenset):
        elements = (
            [_sample_annotation(args[0], samples)]
            if len(args) == 1 or args[-1] is Ellipsis
            else [_sample_annotation(item, samples) for item in args]
        )
        container = origin if origin in (list, set, frozenset) else tuple
        return container(elements)
    if annotation in samples:
        return samples[annotation]
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return next(iter(annotation))
    return {
        int: 1,
        str: "valid",
        bool: True,
        F: F(1),
        Decimal: Decimal(1),
        float: 1.0,
        date: date(1960, 1, 2),
        object: F(1),
    }[annotation]


def _container_annotation(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        return next(
            (item for item in args if _container_annotation(item) is not None),
            None,
        )
    if origin in (
        Mapping,
        dict,
        Iterable,
        Sequence,
        tuple,
        list,
        set,
        frozenset,
    ):
        return annotation
    return None


@pytest.mark.parametrize(
    "cls,field",
    DECLARATION_FIELDS,
    ids=[f"{cls.__name__}.{field}" for cls, field in DECLARATION_FIELDS],
)
@settings(max_examples=5, deadline=None, derandomize=True)
@given(container=st.sampled_from((tuple, list, set, frozenset, dict)))
def test_every_container_field_checks_raw_contents_before_reconstruction(
    cls, field, declaration_samples, container
):
    annotation = _container_annotation(get_type_hints(cls)[field])
    if annotation is None:
        return
    reader = provenance._declaration_schemas(cls)[field]
    valid = _sample_annotation(annotation, declaration_samples)
    if type(valid) is dict:
        key, value = next(iter(valid.items()))
        invalid = ChangingHash(key, hash(key) + 1)
        raw = {key: value, invalid: value}
        if container is not tuple:
            invalid.bucket = hash(key)
        assert len(raw) == 2
    else:
        if container is dict:
            raw = {object(): 1}
        elif container in (set, frozenset):
            raw = container(_raw_collision(next(iter(valid))))
            # A set-to-frozenset conversion may itself erase the witness;
            # preserve the raw two elements using a tuple until the API.
            if len(raw) == 1:
                raw = _raw_collision(next(iter(valid)))
        else:
            raw = container((*valid, object()))
    with pytest.raises(g.InvalidFamilyInput):
        reader(raw, field)


@pytest.mark.parametrize(
    "module,name,argument",
    PUBLIC_ARGUMENTS,
    ids=[
        f"{module.__name__.rsplit('.', 1)[-1]}.{name}.{argument}"
        for module, name, argument in PUBLIC_ARGUMENTS
    ],
)
@settings(max_examples=3, deadline=None, derandomize=True)
@given(shape=st.sampled_from((tuple, set, frozenset)))
def test_every_public_container_argument_checks_raw_contents(
    module, name, argument, public_world, shape
):
    function = getattr(module, name)
    annotation = _container_annotation(get_type_hints(function)[argument])
    if annotation is None:
        return
    reader = provenance._argument_schemas(inspect.unwrap(function))[argument]
    value = _arguments(module, name, public_world)[argument]
    if type(value) is g.YearMonth:
        # ARF MonthInput also admits a raw (year, month) pair.
        value = value.as_tuple()
    if value is None:
        value = {}
    if type(value) is dict:
        key, item = next(iter(value.items()), ("valid", F(1)))
        invalid = ChangingHash(key, hash(key) + 1)
        raw = {key: item, invalid: item}
        if shape is not tuple:
            invalid.bucket = hash(key)
        assert len(raw) == 2
    elif shape is tuple or not value:
        raw = (*value, object())
    else:
        canonical = next(iter(value))
        try:
            hash(canonical)
        except TypeError:
            raw = (*value, object())
        else:
            raw = shape(_raw_collision(canonical))
            if len(raw) == 1:
                raw = _raw_collision(canonical)
    with pytest.raises(g.InvalidFamilyInput):
        reader(raw, argument)


def test_every_enum_schema_rejects_forged_identity(declaration_samples):
    count = 0
    for cls, field in DECLARATION_FIELDS:
        annotation = get_type_hints(cls)[field]
        if get_origin(annotation) in (Union, UnionType):
            candidates = get_args(annotation)
        else:
            candidates = (annotation,)
        for enum in candidates:
            if not inspect.isclass(enum) or not issubclass(enum, Enum):
                continue
            count += 1
            reader = provenance._declaration_schemas(cls)[field]
            for member in enum:
                assert reader(member, field) is member
                forged = (
                    str.__new__(enum, member.value)
                    if issubclass(enum, str)
                    else object.__new__(enum)
                )
                with pytest.raises(g.InvalidFamilyInput):
                    reader(forged, field)
    assert count > 0


@settings(max_examples=len(ATTACKS), deadline=None, derandomize=True)
@given(attack=st.sampled_from(ATTACKS))
def test_external_parameter_declaration_fields_use_the_same_schema(attack):
    from populace_dynamics.track_b.ret_params import ProjectionInputs

    year = RET_PARAMS.for_year(2026)
    amount = year.lower_exempt_amount
    values = (
        PARAMS,
        RET_PARAMS,
        year,
        amount,
        amount.sources[0],
        ProjectionInputs("invented", {2024: amount}, {2025: amount}),
    )
    assert {type(value) for value in values} == set(
        provenance._external_declarations()
    )
    for value in values:
        schemas = provenance._declaration_schemas(type(value))
        assert set(schemas) == {item.name for item in fields(value)}
        for item in fields(value):
            raw = _attack(attack, getattr(value, item.name))
            with pytest.raises(g.InvalidFamilyInput):
                schemas[item.name](raw, item.name)
            if type(raw) in (LyingMapping, ChangingIterator):
                assert raw.calls == []


@settings(max_examples=3, deadline=None, derandomize=True)
@example(pia=1)
@given(pia=st.integers(1, 1000))
def test_all_valid_public_argument_controls_still_compute(pia):
    assert set(FUNCTION_ARGUMENTS) == {
        name for module, name, _ in PUBLIC_FUNCTIONS if module is g
    }
    world = public_world.__wrapped__()
    _, world[g], _ = _world(pia)
    schemas = provenance._argument_schemas
    repeated = []

    def check(function, arguments, expected_error=None):
        arguments = dict(arguments)
        if "compute" in arguments:
            # A caller's callback may deliberately call another public API.
            # Precompute it so this check isolates internal implementation.
            result = arguments["compute"]()
            arguments["compute"] = lambda: result
        calls = []

        def counted(original):
            calls.append(original)
            return schemas(original)

        with pytest.MonkeyPatch.context() as patcher:
            patcher.setattr(provenance, "_argument_schemas", counted)
            if expected_error is None:
                outcome = function(**arguments)
            else:
                emitted = []
                with pytest.raises(expected_error):
                    emitted.append(function(**arguments))
                outcome = None
        if expected_error is not None:
            assert g.count_family_outcomes(emitted).rows == 0
        if calls != [inspect.unwrap(function)]:
            repeated.append([original.__qualname__ for original in calls])
        return outcome

    for module, name, _ in PUBLIC_FUNCTIONS:
        check(getattr(module, name), _arguments(module, name, world))
    for name, names in METHOD_ARGUMENTS.items():
        _, values, guard = _world(1000)
        check(getattr(guard, name), {key: values[key] for key in names})
    month = g.YearMonth(2026, 1)
    for name in ("as_tuple", "__str__"):
        check(getattr(month, name), {})
    guard = g.SavingsClauseGuard(month, earlier_months_unknown=False)
    for name in GUARD_PROPERTIES:
        result = check(
            getattr(g.SavingsClauseGuard, name).fget, {"self": guard}
        )
        assert result == (month if name == "next_month" else None)
    ledger = world[ret]["outcomes"][0].ledger
    selected = check(
        ret.RETLedger.for_beneficiary,
        {"self": ledger, "beneficiary_id": "worker"},
    )
    assert selected == tuple(
        row for row in ledger.months if row.beneficiary_id == "worker"
    )
    check(
        g.applicable_cola_percents,
        {
            "eligibility_year": 2027,
            "payment_month": month,
            "december_cola_percent": {},
        },
        g.InvalidFamilyInput,
    )
    guard = g.SavingsClauseGuard(month, earlier_months_unknown=False)
    check(
        guard.skip,
        {"month": g.YearMonth(2026, 2), "pia": pia},
        g.InvalidFamilyInput,
    )
    assert guard.next_month == month
    result = world[g]["result"]
    guard = g.SavingsClauseGuard(
        result.payment_month, earlier_months_unknown=True
    )
    refused = check(
        guard.evaluate,
        {"key": "unknown-history", "weight": 1, "compute": lambda: result},
    )
    assert refused.unsupported.reason is (
        g.UnsupportedReason.SAVINGS_CLAUSE_HISTORY_UNKNOWN
    )
    assert g.count_family_outcomes([refused]).unsupported_rows == 1
    # Result readers retain their sealed-value contract. Unbound public
    # getters/methods must not accept a receiver impersonating that result.
    for cls in provenance._RESULT_TYPES:
        for name, member in vars(cls).items():
            if name.startswith("_"):
                continue
            reader = member.fget if type(member) is property else member
            if not inspect.isfunction(reader):
                continue
            arguments = set(inspect.signature(reader).parameters) - {"self"}
            assert arguments <= {"beneficiary_id"}
            kwargs = {key: "nh" for key in arguments}
            for receiver in (
                PretendDeclaration(cls),
                MetaclassSpoof(),
                GenericGetterUnknown(),
            ):
                emitted = []
                with pytest.raises(g.InvalidFamilyInput):
                    emitted.append(reader(receiver, **kwargs))
                assert g.count_family_outcomes(emitted).rows == 0
    assert not repeated


@settings(max_examples=8, deadline=None, derandomize=True)
@given(pia=st.integers(1, 1000))
def test_family_parameters_are_snapshotted_once_and_not_cached_by_identity(
    pia,
):
    calls = []
    snapshot = provenance._snapshot_declaration

    def counted(value, *args, **kwargs):
        if type(value) is type(PARAMS):
            calls.append(id(value))
        return snapshot(value, *args, **kwargs)

    params = replace(PARAMS, nawi=dict(PARAMS.nawi))
    state = g.RecordState(
        g.FamilyKind.RETIREMENT,
        pia,
        2 * pia,
        g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
    )
    beneficiaries = (
        g.Beneficiary(
            "spouse",
            g.Role.SPOUSE,
            own_benefit=g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, pia),
            own_benefit_first=True,
            birth_year=1960,
        ),
    )
    payment_month = g.YearMonth(2026, 1)
    initializers = []

    def counted_initializer(cls):
        initialize = cls.__init__

        def initialize_counted(*args, **kwargs):
            initializers.append(cls.__name__)
            return initialize(*args, **kwargs)

        return initialize_counted

    def compute():
        return g.family_benefits(
            state,
            beneficiaries,
            payment_month=payment_month,
            params=params,
            standalone=True,
        )

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(provenance, "_snapshot_declaration", counted)
        for cls in provenance._DECLARATION_TYPES:
            patcher.setattr(cls, "__init__", counted_initializer(cls))
        assert compute().record_total == pia
        assert calls == [id(params)]
        assert initializers == []
        params.nawi[1977] = object()
        with pytest.raises(g.InvalidFamilyInput):
            compute()
        assert calls == [id(params), id(params)]
        assert initializers == []


def test_every_declared_enum_reader_requires_canonical_member_identity():
    enums = {
        value
        for module in MODULES
        for value in vars(module).values()
        if inspect.isclass(value)
        and issubclass(value, Enum)
        and value is not Enum
    }
    for enum in enums:
        read = provenance._enum_schema(enum)
        for member in enum:
            assert read(member, "enum") is member
            forged = (
                str.__new__(enum, member.value)
                if issubclass(enum, str)
                else object.__new__(enum)
            )
            with pytest.raises(g.InvalidFamilyInput):
                read(forged, "enum")
            with pytest.raises(g.InvalidFamilyInput):
                read(PretendDeclaration(enum), "enum")
        # There are no IntEnum declarations in this API. CPython rejects
        # the reviewer's int.__new__ construction before an API call.
        with pytest.raises(TypeError):
            int.__new__(enum, 1)
