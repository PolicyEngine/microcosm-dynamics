"""Public-reader provenance; statutory conformance on invented cases only.

The evaluator checks computation provenance, not freshness or attribution.
"""

from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.track_b import _provenance as provenance
from populace_dynamics.track_b import gross_benefits as g
from tests.test_track_b_gross_benefits_fix_round_12_contract import (
    COMPUTE,
    EVALUATE,
    LAYERS,
    _outcome,
)


class Foreign:
    """An invalid receiver that turns any user hook into a genuine refusal."""

    def __init__(self, refusal, calls, *, lie=False):
        object.__setattr__(self, "refusal", refusal)
        object.__setattr__(self, "calls", calls)
        object.__setattr__(self, "lie", lie)

    def _hook(self, *args, **kwargs):
        object.__getattribute__(self, "calls").append("hook")
        if object.__getattribute__(self, "lie"):
            return 1
        raise object.__getattribute__(self, "refusal")

    __getattribute__ = _hook
    __getattr__ = _hook
    __iter__ = _hook
    __len__ = _hook
    __getitem__ = _hook
    __eq__ = _hook
    __hash__ = _hook
    __repr__ = _hook
    __str__ = _hook
    __bool__ = _hook
    __int__ = _hook
    __index__ = _hook
    __float__ = _hook
    __format__ = _hook


def _read_then_compute(reader, receiver, args=(), layer="g", kwargs=None):
    # A reader's ordinary int/None return must not itself cause rejection.
    reader(receiver, *args, **({} if kwargs is None else kwargs))
    return COMPUTE[layer]()


@pytest.mark.parametrize("layer", LAYERS)
def test_review_four_layer_getter_rejects_receiver_before_any_hook(layer):
    refusal = _outcome(layer, refused=True).unsupported
    calls, rows = [], []
    receiver = Foreign(refusal, calls)
    outcome_class = type(_outcome(layer))
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE[layer](
                "foreign-getter",
                1,
                lambda: _read_then_compute(
                    outcome_class.supported.fget, receiver, layer=layer
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


METHOD_ARGUMENTS = {
    "__new__": (),
    "__init__": (),
    "__getattribute__": ("value",),
    "__setattr__": ("value", None),
    "__delattr__": ("value",),
    "__eq__": (None,),
    "__ne__": (None,),
    "__lt__": (None,),
    "__le__": (None,),
    "__gt__": (None,),
    "__ge__": (None,),
    "__format__": ("",),
    "__reduce_ex__": (4,),
    "__deepcopy__": ({},),
    "__getitem__": ("worker",),
    "__contains__": ("worker",),
    "__setstate__": ({},),
    "get": ("worker",),
    "for_beneficiary": ("worker",),
    "with_traceback": (None,),
    "add_note": ("note",),
    "admit": (None,),
    "skip": (None,),
    "evaluate": ("key", 1, lambda: None),
}


def _reader_cases():
    classes = (
        provenance._RESULT_TYPES
        | provenance._DECLARATION_TYPES
        | {g.SavingsClauseGuard}
    )
    for cls in sorted(classes, key=lambda item: item.__name__):
        for name in dir(cls):
            if name.startswith("_") and not (
                name.startswith("__") and name.endswith("__")
            ):
                continue
            if name in {
                "__class__",
                "__class_getitem__",
                "__init_subclass__",
                "__subclasshook__",
            }:
                continue
            member = getattr(cls, name)
            if isinstance(member, property):
                yield cls, name, member.fget, ()
            elif callable(member):
                yield cls, name, member, METHOD_ARGUMENTS.get(name, ())


READER_CASES = tuple(_reader_cases())


@pytest.mark.parametrize(
    "cls,name,reader,args",
    READER_CASES,
    ids=[f"{cls.__name__}.{name}" for cls, name, _, _ in READER_CASES],
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_every_public_reader_rejects_foreign_receiver_without_hooks(
    cls, name, reader, args, lie
):
    calls, rows = [], []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls, lie=lie)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "bad-reader",
                1,
                lambda: _read_then_compute(reader, foreign, args),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("layer", LAYERS)
@settings(max_examples=6, deadline=None, derandomize=True)
@given(weight=st.integers(0, 100), key=st.text(min_size=1, max_size=10))
def test_evaluator_accepts_precomputed_genuine_result_with_declared_metadata(
    layer, weight, key
):
    result = COMPUTE[layer]()
    row = EVALUATE[layer](key, Fraction(weight, 3), lambda: result)
    assert row.key == key
    assert row.supported
    count = g.count_family_outcomes([row])
    assert count.rows == count.supported_rows == 1
    assert count.supported_weight == Fraction(weight, 3)


@pytest.mark.parametrize("layer", LAYERS)
@settings(max_examples=6, deadline=None, derandomize=True)
@given(weight=st.integers(0, 100))
def test_evaluator_counts_reraised_genuine_refusal_with_its_own_reason(
    layer, weight
):
    refusal = _outcome(layer, refused=True).unsupported

    def reraised():
        raise refusal

    row = EVALUATE[layer](
        "declared-attribution", Fraction(weight, 3), reraised
    )
    assert row.unsupported is refusal
    count = g.count_family_outcomes([row])
    assert count.rows == count.unsupported_rows == 1
    assert count.unsupported_by_reason == {
        refusal.reason: (1, Fraction(weight, 3))
    }


def test_nested_evaluator_rejects_foreign_callback_result_without_class_hook():
    refusal = _outcome("g", refused=True).unsupported
    calls, rows = [], []
    foreign = Foreign(refusal, calls)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "outer",
                1,
                lambda: g.evaluate_family("inner", 1, lambda: foreign),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.fixture(scope="module")
def reader_samples():
    from tests.test_track_b_gross_benefits_fix_round_10_api import _world
    from tests.test_track_b_gross_benefits_fix_round_13_audit import (
        _sealed_samples,
    )
    from tests.test_track_b_r3_fix_round_13 import MUTATION_CASES

    samples, _, guard = _world(100)
    samples.update(_sealed_samples())
    samples[type(guard).__name__] = guard
    for _, factory, _, _, _ in MUTATION_CASES:
        value = factory()
        samples[type(value).__name__] = value
    return samples


ARGUMENT_READERS = tuple(
    (cls, name, reader, args, index)
    for cls, name, reader, args in READER_CASES
    if name not in {"__init__", "__new__"}
    for index in range(len(args))
)


@pytest.mark.parametrize(
    "cls,name,reader,args,index",
    ARGUMENT_READERS,
    ids=[
        f"{cls.__name__}.{name}[{index}]"
        for cls, name, _, _, index in ARGUMENT_READERS
    ],
)
def test_public_reader_arguments_reject_foreign_values_before_hooks(
    cls, name, reader, args, index, reader_samples
):
    calls, rows = [], []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls)
    arguments = list(args)
    arguments[index] = foreign
    # A correctly typed uninitialized receiver also must validate arguments
    # before a field read; all initialized classes available are used below.
    receiver = reader_samples.get(cls.__name__)
    if receiver is None:
        receiver = cls.__new__(cls)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "bad-argument",
                1,
                lambda: _read_then_compute(reader, receiver, arguments),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize(
    "cls",
    sorted(
        provenance._RESULT_TYPES | provenance._DECLARATION_TYPES,
        key=lambda cls: cls.__name__,
    ),
)
def test_public_new_rejects_foreign_constructor_argument(cls):
    calls = []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls)
    with pytest.raises(g.InvalidFamilyInput):
        cls.__new__(cls, foreign)
    assert calls == []


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize(
    "reader",
    ("__repr__", "__str__", "__eq__", "__hash__", "__dir__", "__sizeof__"),
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_sealed_reader_checks_mutated_fields_before_hooks(layer, reader, lie):
    result = COMPUTE[layer]()
    # Every result has at least one public dataclass field.
    from dataclasses import fields

    name = fields(result)[0].name
    calls, rows = [], []
    foreign = Foreign(
        _outcome(layer, refused=True).unsupported, calls, lie=lie
    )
    object.__setattr__(result, name, foreign)
    args = (None,) if reader == "__eq__" else ()
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE[layer](
                "tampered-reader",
                1,
                lambda: _read_then_compute(
                    getattr(type(result), reader), result, args, layer
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize(
    "reader",
    (
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__lt__",
        "__getstate__",
        "__reduce__",
        "__reduce_ex__",
    ),
)
def test_declaration_reader_checks_mutated_fields_before_hooks(reader):
    value = g.YearMonth(2026, 1)
    calls, rows = [], []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls)
    object.__setattr__(value, "year", foreign)
    args = (g.YearMonth(2026, 2),) if reader in {"__eq__", "__lt__"} else ()
    if reader == "__reduce_ex__":
        args = (4,)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "tampered-declaration",
                1,
                lambda: _read_then_compute(
                    getattr(type(value), reader), value, args
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("reader", ("__str__", "__repr__"))
def test_refusal_reader_seal_covers_exception_arguments(layer, reader):
    refusal = _outcome(layer, refused=True).unsupported
    calls, rows = [], []
    foreign = Foreign(_outcome(layer, refused=True).unsupported, calls)
    object.__setattr__(refusal, "args", (foreign,))
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE[layer](
                "exception-args",
                1,
                lambda: _read_then_compute(
                    getattr(type(refusal), reader), refusal, layer=layer
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


def test_direct_post_init_revalidates_declaration_before_collection_hooks():
    from populace_dynamics.track_b import ret_ledger as ret

    value = ret.WorkEarnings()
    calls, rows = [], []
    foreign = Foreign(_outcome("ret", refused=True).unsupported, calls)
    object.__setattr__(value, "wages", foreign)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE["ret"](
                "post-init",
                1,
                lambda: _read_then_compute(
                    ret.WorkEarnings.__post_init__, value, layer="ret"
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("layer", LAYERS)
def test_direct_post_init_revalidates_sealed_result_before_field_hooks(layer):
    from dataclasses import fields

    value = COMPUTE[layer]()
    calls, rows = [], []
    foreign = Foreign(_outcome(layer, refused=True).unsupported, calls)
    object.__setattr__(value, fields(value)[0].name, foreign)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE[layer](
                "post-init",
                1,
                lambda: _read_then_compute(
                    type(value).__post_init__, value, layer=layer
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


def test_valid_guard_identity_and_month_membership_comparisons_stay_usable():
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1), earlier_months_unknown=False
    )
    assert guard == guard
    assert not (guard != guard)
    assert hash(guard) == hash(guard)
    assert len({g.YearMonth(2026, 1), (2026, 1)}) == 2


@pytest.mark.parametrize(
    "reader,bad", (("__format__", 1), ("__reduce_ex__", "4"))
)
def test_declaration_protocol_arguments_use_their_declared_kinds(reader, bad):
    value = g.YearMonth(2026, 1)
    with pytest.raises(g.InvalidFamilyInput):
        getattr(g.YearMonth, reader)(value, bad)


@pytest.mark.parametrize(
    "reader,bad", (("add_note", 1), ("with_traceback", "tb"))
)
def test_refusal_protocol_arguments_use_their_declared_kinds(reader, bad):
    value = _outcome("g", refused=True).unsupported
    with pytest.raises(g.InvalidFamilyInput):
        getattr(type(value), reader)(value, bad)
    assert value.with_traceback(None) is value
    value.add_note("An invented test note")
    assert value.reason.value in str(value)


class ForeignKeyword(str):
    """String encoding whose keyword-name matching must never be executed."""

    def __new__(cls, name, refusal, calls):
        value = str.__new__(cls, name)
        value.refusal = refusal
        value.calls = calls
        return value

    def __eq__(self, other):
        self.calls.append("keyword-equality")
        raise self.refusal

    def __str__(self):
        self.calls.append("keyword-string")
        raise self.refusal

    __hash__ = str.__hash__


@pytest.mark.parametrize(
    "cls,name,reader,args",
    READER_CASES,
    ids=[f"{cls.__name__}.{name}" for cls, name, _, _ in READER_CASES],
)
def test_public_reader_keyword_names_reject_before_binding_hooks(
    cls, name, reader, args, reader_samples
):
    receiver = reader_samples.get(cls.__name__)
    if name == "__new__":
        receiver = cls
    elif receiver is None:
        receiver = cls.__new__(cls)
    refusal = _outcome("g", refused=True).unsupported
    for name in ("self", "name", "other", "declared", "key"):
        calls, rows = [], []
        keyword = ForeignKeyword(name, refusal, calls)
        arguments = {keyword: None}
        with pytest.raises(g.InvalidFamilyInput):
            rows.append(
                g.evaluate_family(
                    "keyword-reader",
                    1,
                    lambda arguments=arguments: _read_then_compute(
                        reader, receiver, args, kwargs=arguments
                    ),
                )
            )
        assert calls == []
        assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize(
    "cls",
    sorted(
        provenance._RESULT_TYPES
        | provenance._DECLARATION_TYPES
        | {g.SavingsClauseGuard},
        key=lambda cls: cls.__name__,
    ),
)
def test_public_constructor_keyword_names_reject_before_binding_hooks(cls):
    refusal = _outcome("g", refused=True).unsupported
    for name in ("self", "name", "other", "declared", "key"):
        calls, rows = [], []
        arguments = {ForeignKeyword(name, refusal, calls): None}

        def construct_then_compute(arguments=arguments):
            cls(**arguments)
            return COMPUTE["g"]()

        with pytest.raises(g.InvalidFamilyInput):
            rows.append(
                g.evaluate_family(
                    "keyword-constructor", 1, construct_then_compute
                )
            )
        assert calls == []
        assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize(
    "reader,args", (("__reduce_ex__", (4,)), ("__getstate__", ()))
)
def test_sealed_serialization_readers_reject_instance_method_shadowing(
    reader, args
):
    value = COMPUTE["g"]()
    calls, rows = [], []
    refusal = _outcome("g", refused=True).unsupported

    def shadow():
        calls.append("shadow")
        raise refusal

    object.__setattr__(value, "__reduce__", shadow)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "shadowed-reader",
                1,
                lambda: _read_then_compute(
                    getattr(type(value), reader), value, args
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


def test_sealed_mapping_comparison_rejects_instance_method_shadowing():
    from populace_dynamics.track_b import ret_ledger as ret

    value = ret.partial_payments(1, {"nh": 2}, {"nh": 2})
    calls, rows = [], []
    refusal = _outcome("ret", refused=True).unsupported

    def shadow():
        calls.append("shadow")
        raise refusal

    object.__setattr__(value, "items", shadow)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            EVALUATE["ret"](
                "shadowed-mapping",
                1,
                lambda: _read_then_compute(
                    type(value).__eq__, value, ({"nh": 1},), "ret"
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


CLASS_READER_CASES = tuple(
    (cls, name, getattr(cls, name).__func__)
    for cls in sorted(
        provenance._RESULT_TYPES
        | provenance._DECLARATION_TYPES
        | {g.SavingsClauseGuard},
        key=lambda item: item.__name__,
    )
    for name in ("__class_getitem__", "__init_subclass__", "__subclasshook__")
    if hasattr(cls, name)
)


@pytest.mark.parametrize("cls,name,reader", CLASS_READER_CASES)
def test_public_class_readers_reject_foreign_receivers_arguments_and_keywords(
    cls, name, reader
):
    refusal = _outcome("g", refused=True).unsupported
    calls, rows = [], []
    foreign = Foreign(refusal, calls)
    for receiver, arguments, keywords in (
        (foreign, (), {}),
        (cls, (foreign,), {}),
        (cls, (), {ForeignKeyword("cls", refusal, calls): None}),
    ):
        with pytest.raises(g.InvalidFamilyInput):
            rows.append(
                g.evaluate_family(
                    "class-reader",
                    1,
                    lambda receiver=receiver, arguments=arguments, keywords=keywords: _read_then_compute(
                        reader, receiver, arguments, kwargs=keywords
                    ),
                )
            )
        assert calls == []
        assert g.count_family_outcomes(rows).rows == 0


def test_valid_class_metadata_hooks_keep_generic_alias_and_subclass_behavior():
    from populace_dynamics.track_b import ret_ledger as ret

    alias = ret.PartialPaymentAllocation[str, Fraction]
    assert alias.__origin__ is ret.PartialPaymentAllocation
    assert alias.__args__ == (str, Fraction)
    assert g.YearMonth.__subclasshook__(int) is NotImplemented

    class UnsupportedSubclass(g.YearMonth):
        pass

    with pytest.raises(g.InvalidFamilyInput):
        UnsupportedSubclass(2026, 1)


@settings(max_examples=20, deadline=None, derandomize=True)
@given(name=st.text(max_size=12), shadow=st.booleans())
def test_keyword_names_and_instance_shape_reject_before_hooks(name, shadow):
    value = COMPUTE["g"]()
    refusal = _outcome("g", refused=True).unsupported
    calls, rows = [], []
    if shadow:
        object.__setattr__(value, "extra_" + name, Foreign(refusal, calls))
        reader, args, kwargs = type(value).__repr__, (), {}
    else:
        reader, args = type(value).__getattribute__, ("record_total",)
        kwargs = {ForeignKeyword(name, refusal, calls): None}
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "shape",
                1,
                lambda: _read_then_compute(reader, value, args, kwargs=kwargs),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("as_argument", (False, True))
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_class_metadata_rejects_foreign_metaclass_before_descriptor_hooks(
    as_argument,
    lie,
):
    from populace_dynamics.track_b import ret_ledger as ret

    calls, rows = [], []
    refusal = _outcome("g", refused=True).unsupported

    class ForeignMeta(type):
        @property
        def __mro__(cls):
            calls.append("metaclass-mro")
            if lie:
                return (ret.PartialPaymentAllocation, object)
            raise refusal

        @property
        def __dict__(cls):
            calls.append("metaclass-dict")
            if lie:
                return {}
            raise refusal

    class ForeignClass(metaclass=ForeignMeta):
        pass

    reader = ret.PartialPaymentAllocation.__subclasshook__.__func__
    receiver = ret.PartialPaymentAllocation if as_argument else ForeignClass
    args = (ForeignClass,) if as_argument else (int,)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "foreign-metaclass",
                1,
                lambda: _read_then_compute(reader, receiver, args),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@settings(max_examples=20, deadline=None, derandomize=True)
@given(case=st.sampled_from(ARGUMENT_READERS), lie=st.booleans())
def test_public_reader_argument_schema_property(case, lie, reader_samples):
    cls, name, reader, args, index = case
    calls, rows = [], []
    arguments = list(args)
    arguments[index] = Foreign(
        _outcome("g", refused=True).unsupported, calls, lie=lie
    )
    receiver = reader_samples.get(cls.__name__)
    if receiver is None:
        receiver = cls.__new__(cls)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "reader-argument-property",
                1,
                lambda: _read_then_compute(reader, receiver, arguments),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("sealed", (False, True))
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_public_post_init_rejects_extra_foreign_arguments_before_field_reads(
    sealed, lie
):
    receiver = COMPUTE["g"]() if sealed else g.YearMonth(2026, 1)
    calls, rows = [], []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls, lie=lie)
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "post-init-argument",
                1,
                lambda: _read_then_compute(
                    type(receiver).__post_init__, receiver, (foreign,)
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("name", ("__notes__", "__dict__"))
@settings(max_examples=4, deadline=None, derandomize=True)
@given(lie=st.booleans(), nested=st.booleans())
def test_public_dunder_writers_reject_foreign_values_before_hooks(
    name, lie, nested
):
    receiver = _outcome("g", refused=True).unsupported
    calls, rows = [], []
    foreign = Foreign(_outcome("g", refused=True).unsupported, calls, lie=lie)
    if nested:
        foreign = [foreign] if name == "__notes__" else {"foreign": foreign}
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "dunder-writer",
                1,
                lambda: _read_then_compute(
                    type(receiver).__setattr__, receiver, (name, foreign)
                ),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@settings(max_examples=9, deadline=None, derandomize=True)
@given(depth=st.integers(0, 8))
def test_public_reader_rejects_cyclic_mapping_as_invalid_input(depth):
    receiver = COMPUTE["g"]()
    memo = {}
    nested = memo
    for _ in range(depth):
        nested["next"] = {}
        nested = nested["next"]
    nested["cycle"] = memo
    rows = []
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "cyclic-reader",
                1,
                lambda: _read_then_compute(
                    type(receiver).__deepcopy__, receiver, (memo,)
                ),
            )
        )
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize("name", ("YearMonth", "OwnBenefit", "WorkEarnings"))
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_public_declaration_init_rejects_instance_method_shadowing(name, lie):
    from populace_dynamics.track_b import ret_ledger as ret

    cls, arguments = {
        "YearMonth": (g.YearMonth, (2026, 1)),
        "OwnBenefit": (g.OwnBenefit, (g.OwnBenefitKind.OLD_AGE, 100)),
        "WorkEarnings": (ret.WorkEarnings, ()),
    }[name]
    receiver = cls(*arguments)
    refusal = _outcome("g", refused=True).unsupported
    calls, rows = [], []

    def shadow():
        calls.append("post-init-shadow")
        if lie:
            return None
        raise refusal

    receiver.__dict__["__post_init__"] = shadow
    with pytest.raises(g.InvalidFamilyInput):
        rows.append(
            g.evaluate_family(
                "shadowed-init",
                1,
                lambda: _read_then_compute(cls.__init__, receiver, arguments),
            )
        )
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


def test_direct_declaration_init_preserves_inert_extra_metadata():
    receiver = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, 100)
    receiver.__dict__["caller_metadata"] = 123
    g.OwnBenefit.__init__(receiver, g.OwnBenefitKind.OLD_AGE, 200)
    assert receiver.pia == 200
    assert receiver.__dict__["caller_metadata"] == 123


@pytest.mark.parametrize(
    "kind",
    (
        "statutory-input",
        "declaration-reader",
        "sealed-reader",
        "stateful-reader",
        "stateful-property",
        "stateful-reinitialize",
        "external-input",
        "nested-declaration",
    ),
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_public_attribute_dictionary_keys_reject_before_lookup_hooks(
    kind, lie
):
    from dataclasses import fields
    from functools import partial

    from tests.track_b_gross_benefit_support import ssa_params

    calls, rows = [], []
    refusal = _outcome("g", refused=True).unsupported

    class Key(str):
        __hash__ = str.__hash__

        def __eq__(self, other):
            calls.append("key-equality")
            if lie:
                return str.__eq__(self, other)
            raise refusal

    own = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, 100)
    result = COMPUTE["g"]()
    guard = g.SavingsClauseGuard(
        g.YearMonth(2026, 1), earlier_months_unknown=False
    )
    params = ssa_params()
    if kind == "statutory-input":
        value, field = own, "pia"
        action = partial(g.own_monthly_benefit, own, params)
    elif kind == "declaration-reader":
        value, field = own, "pia"
        action = partial(type(own).__getattribute__, own, "pia")
    elif kind == "sealed-reader":
        value, field = result, "record_total"
        action = partial(type(result).__getattribute__, result, "record_total")
    elif kind == "stateful-reader":
        value, field = guard, "admit"
        action = partial(type(guard).__getattribute__, guard, "admit")
    elif kind == "stateful-property":
        value, field = guard, "_next"
        action = partial(type(guard).next_month.fget, guard)
    elif kind == "stateful-reinitialize":
        value, field = guard, "_next"
        action = partial(
            type(guard).__init__,
            guard,
            g.YearMonth(2026, 1),
            earlier_months_unknown=False,
        )
    elif kind == "external-input":
        value, field = params, fields(params)[0].name
        action = partial(g.statutory_rates, params)
    else:
        value, field = result.payment_month, "year"
        action = partial(type(result).__repr__, result)
    raw = object.__getattribute__(value, "__dict__")
    replacement = {key: item for key, item in raw.items() if key != field}
    replacement[Key(field)] = raw.get(field)
    object.__setattr__(value, "__dict__", replacement)

    def compute():
        action()
        return COMPUTE["g"]()

    with pytest.raises(g.InvalidFamilyInput):
        rows.append(g.evaluate_family("dictionary-key", 1, compute))
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


@pytest.mark.parametrize(
    "kind", ("reader-argument", "sealed-field", "constructor")
)
@settings(max_examples=2, deadline=None, derandomize=True)
@given(lie=st.booleans())
def test_foreign_enum_rejects_before_metaclass_iteration(kind, lie):
    from enum import Enum, EnumType

    calls, rows = [], []
    refusal = _outcome("g", refused=True).unsupported

    class ForeignEnumType(EnumType):
        def __iter__(cls):
            calls.append("enum-iteration")
            if lie:
                return EnumType.__iter__(cls)
            raise refusal

    class ForeignEnum(Enum, metaclass=ForeignEnumType):
        MEMBER = "foreign"

    receiver = COMPUTE["g"]()
    if kind == "sealed-field":
        object.__setattr__(receiver, "kind", ForeignEnum.MEMBER)

    def compute():
        if kind == "reader-argument":
            type(receiver).__eq__(receiver, ForeignEnum.MEMBER)
        elif kind == "sealed-field":
            type(receiver).__repr__(receiver)
        else:
            g.OwnBenefit.__new__(g.OwnBenefit, ForeignEnum.MEMBER, 100)
        return COMPUTE["g"]()

    with pytest.raises(g.InvalidFamilyInput):
        rows.append(g.evaluate_family("foreign-enum", 1, compute))
    assert calls == []
    assert g.count_family_outcomes(rows).rows == 0


def test_reader_enum_schema_rejects_foreign_enums_and_keeps_canonical_members():
    from enum import Enum

    class ForeignEnum(Enum):
        MEMBER = "foreign"

    month = g.YearMonth(2026, 1)
    with pytest.raises(g.InvalidFamilyInput):
        g.YearMonth.__eq__(month, ForeignEnum.MEMBER)
    assert g.YearMonth.__eq__(month, g.Role.SPOUSE) is NotImplemented
    assert g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, 100).pia == 100
