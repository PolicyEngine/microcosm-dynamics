"""Package-private provenance for Track B statutory computations.

Verification class: statutory conformance on invented and published cases
only. This is an API contract, with no population or forecast claim and no
security boundary against access to Python's private implementation names.
Public arguments and declaration fields have explicit schemas. Raw scalar
kinds and declaration types use identity, enum values must be canonical
members, and containers must be exact built-ins. Raw container contents are
checked before hashing or reconstruction. Callback slots are executable,
not data. Each public call owns a fresh snapshot; private helpers reuse it.
Ordered schemas admit tuple/list and retain every element in a tuple;
membership schemas admit built-in collections and become frozensets.
Evaluators establish provenance, layer and integrity, not freshness or
caller-declared attribution of an earlier genuine result or refusal.
The contract excludes code accessing private names, monkeypatching modules,
or mutating an input from another thread during a call.
One private capability seals every declared G, R2 and R3 result, refusal,
outcome and denominator. Public construction and copying are input errors;
serialization is rejected. Persist declared inputs and recompute instead.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import MISSING, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import cache, wraps
from inspect import signature
from types import GenericAlias, MappingProxyType, UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

__all__ = []


class InvalidFamilyInput(ValueError):
    """The inputs do not describe a legal family (not a coverage gap)."""


class _InvalidInputType(InvalidFamilyInput, TypeError):
    """An input error, also retaining the constructor's TypeError contract."""


class _TypeRegistry(set):
    """Trusted class metadata indexed without hashing an incoming class."""

    def __init__(self):
        super().__init__()
        self.by_identity = {}

    def add(self, cls):
        super().add(cls)
        self.by_identity[id(cls)] = cls


_RESULT_SEAL = object()
_RESULT_TYPES = _TypeRegistry()
_RESULT_ATTRIBUTE_NAMES = {}
_RESULT_FIELD_NAMES = {}
_REFUSAL_REASONS = {}
_ENUM_TYPES = _TypeRegistry()
_STATEFUL_TYPES = _TypeRegistry()
_INITIALIZING = object()
_MISSING_ARGUMENT = object()


def _has_declared_type(value, types):
    """Do not let a user-defined metaclass spoof type membership."""
    actual = type(value)
    if type(types) is _TypeRegistry:
        return types.by_identity.get(id(actual)) is actual
    for expected in types:
        if actual is expected:
            return True
    return False


def _register_annotation_enums(annotation):
    """Register trusted declaration metadata, never an incoming value's type."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        _ENUM_TYPES.add(annotation)
    elif issubclass(type(annotation), Enum):
        _ENUM_TYPES.add(type(annotation))
    for part in get_args(annotation):
        _register_annotation_enums(part)


def _register_declaration_enums(cls):
    for annotation in get_type_hints(
        cls, localns={cls.__name__: cls}
    ).values():
        _register_annotation_enums(annotation)


class _SealedResult:
    """Computed values cannot be constructed or copied through public APIs.

    The seal is an API provenance check, not a security boundary against
    code accessing module-private machinery. It is outside dataclass fields
    so public read access, equality and constructor introspection stay stable.
    """

    def __copy__(self):
        raise InvalidFamilyInput(
            "Track B results can only be created by their computation"
        )

    def __deepcopy__(self, memo):
        raise InvalidFamilyInput(
            "Track B results can only be created by their computation"
        )

    def __reduce__(self):
        raise InvalidFamilyInput(
            "Track B sealed values cannot be serialized; persist inputs "
            "and recompute"
        )

    def __reduce_ex__(self, protocol):
        return self.__reduce__()

    def __getstate__(self):
        # copyreg._reduce_ex calls getstate directly, bypassing __reduce__.
        return self.__reduce__()


def _checked_instance_dict(value):
    """Read instance storage without dispatching any instance-key protocol.

    Callers first establish a registered exact receiver type. A custom
    dictionary key can otherwise run equality even in a built-in attribute
    lookup. Inert metadata with exact string keys remains permitted here.
    """
    attributes = object.__getattribute__(value, "__dict__")
    if type(attributes) is not dict:
        raise InvalidFamilyInput("Instance attributes need a built-in dict")
    for name in attributes:
        if type(name) is not str:
            raise InvalidFamilyInput(
                "Instance attribute names must be strings"
            )
    return attributes


def _result_values(value):
    # Private callers have established exact registered result type. Field
    # names are class metadata; field values are read afresh every time.
    return {
        name: object.__getattribute__(value, name)
        for name in _RESULT_FIELD_NAMES[type(value)]
    }


@cache
def _dataclass_field_names(cls):
    return tuple(item.name for item in fields(cls))


@cache
def _dataclass_init_field_names(cls):
    return tuple(item.name for item in fields(cls) if item.init)


def _seal_value(value):
    """An immutable, type-sensitive snapshot, including nested seals."""
    cls = type(value)
    if cls is Fraction:
        return Fraction, _fraction_parts(value, "sealed number")
    if _has_declared_type(
        value, (bool, int, float, str, bytes, Decimal, date, type(None))
    ):
        return cls, value
    if _has_declared_type(value, _RESULT_TYPES):
        _check_seal(value)
        payload = object.__getattribute__(value, "_g_seal")[2]
    elif _has_declared_type(value, _DECLARATION_TYPES):
        _checked_instance_dict(value)
        payload = tuple(
            (name, _seal_value(object.__getattribute__(value, name)))
            for name in _dataclass_field_names(cls)
        )
    elif cls is dict or cls is MappingProxyType:
        if cls is MappingProxyType:
            from gc import get_referents

            backing = get_referents(value)
            if len(backing) != 1 or type(backing[0]) is not dict:
                raise _InvalidInputType("Sealed mappings need a built-in dict")
            value = backing[0]
        payload = tuple(
            (_seal_value(key), _seal_value(item))
            for key, item in value.items()
        )
    elif cls is tuple or cls is list:
        payload = tuple(_seal_value(item) for item in value)
    elif cls is set or cls is frozenset:
        items = [_seal_value(item) for item in value]
        payload = frozenset(items)
    elif _has_declared_type(value, _ENUM_TYPES):
        payload = _enum_schema(cls)(value, "sealed enum")
    else:
        raise _InvalidInputType("Undeclared computed-result field")
    return cls, payload


def _seal_payload(value):
    try:
        values = _result_values(value)
        if _has_declared_type(value, _REFUSAL_REASONS):
            # Exception string/repr readers consume args as well as the
            # declared refusal fields. Tracebacks remain caller composition.
            values["args"] = object.__getattribute__(value, "args")
        return type(value), tuple(
            (key, _seal_value(item)) for key, item in values.items()
        )
    except InvalidFamilyInput:
        raise
    except (
        AttributeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise InvalidFamilyInput("Malformed computed-result fields") from error


def _check_seal(value):
    if not _has_declared_type(value, _RESULT_TYPES):
        raise InvalidFamilyInput(
            "Expected an unaltered result computed by Track B"
        )
    attributes = _checked_instance_dict(value)
    allowed_names = _RESULT_ATTRIBUTE_NAMES[type(value)]
    if any(name not in allowed_names for name in attributes):
        raise InvalidFamilyInput(
            "Computed values cannot add instance attributes"
        )
    if "__notes__" in attributes:
        notes = attributes["__notes__"]
        if type(notes) is not list or any(
            type(note) is not str for note in notes
        ):
            raise InvalidFamilyInput(
                "Exception notes must be built-in strings"
            )
    seal = attributes.get("_g_seal")
    if (
        type(seal) is not tuple
        or len(seal) != 3
        or seal[0] is not _RESULT_SEAL
        or seal[1] != id(value)
        or seal[2] != _seal_payload(value)
    ):
        raise InvalidFamilyInput(
            "Expected an unaltered result computed by Track B"
        )


def _sealed_result(cls):
    """Require the package capability, validate, and seal a declared result."""
    # A declared refusal subclass inherits the base validator, not its wrapper.
    initialize = _during_initialization(
        getattr(cls.__init__, "__wrapped__", cls.__init__)
    )
    _RESULT_TYPES.add(cls)
    if is_dataclass(cls):
        _register_declaration_enums(cls)
    names = (
        _dataclass_field_names(cls)
        if is_dataclass(cls)
        else ("reason", "detail", "beneficiary_id", "record_id")
    )
    _RESULT_FIELD_NAMES[cls] = names
    _RESULT_ATTRIBUTE_NAMES[cls] = set(names) | {"_g_seal"}
    if cls in _REFUSAL_REASONS:
        _RESULT_ATTRIBUTE_NAMES[cls].add("__notes__")

    @wraps(initialize)
    def initialize_computed(*arguments, **keywords):
        self, args, kwargs = _public_receiver(arguments, keywords)
        _seal = kwargs.pop("_seal", None)
        if _seal is not _RESULT_SEAL:
            raise InvalidFamilyInput(
                "Track B results can only be created by their computation"
            )
        if type(self) is not cls:
            raise InvalidFamilyInput("Undeclared Track B result subclass")
        initialize(self, *args, **kwargs)
        object.__setattr__(
            self, "_g_seal", (_RESULT_SEAL, id(self), _seal_payload(self))
        )

    cls.__init__ = initialize_computed
    return _checked_public_methods(cls)


def _computed(cls, *args, **kwargs):
    return cls(*args, _seal=_RESULT_SEAL, **kwargs)


def _detached_result(value):
    """Keep guard history independent of caller-held result objects."""
    if isinstance(value, _SealedResult):
        _check_seal(value)
        return _computed(
            type(value),
            **{
                key: _detached_result(item)
                for key, item in _result_values(value).items()
            },
        )
    if isinstance(value, Mapping):
        return {key: _detached_result(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_detached_result(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return type(value)(_detached_result(item) for item in value)
    return _rebuild_declared(value)


class _SealedOutcome(_SealedResult):
    """Marker for declared rows accepted by the common denominator."""


def _checked_result(value, expected_type, label="result"):
    if type(value) is not expected_type:
        raise InvalidFamilyInput(
            f"{label} must be an {expected_type.__name__}"
        )
    _check_seal(value)
    return value


def _sealed_refusal(reason_type):
    """Bind one declared refusal class to exactly one layer's reason enum."""

    def declare(cls):
        _ENUM_TYPES.add(reason_type)
        _REFUSAL_REASONS[cls] = reason_type
        return _sealed_result(cls)

    return declare


def _check_reason(refusal, reason):
    expected = _REFUSAL_REASONS.get(type(refusal))
    if expected is None or not any(reason is member for member in expected):
        raise InvalidFamilyInput("reason must use the declared layer's enum")


def _check_refusal(value):
    if not _has_declared_type(value, _REFUSAL_REASONS):
        raise InvalidFamilyInput("Expected a declared Track B refusal")
    _check_seal(value)
    _check_reason(value, value.reason)
    return value


def _check_outcome(value):
    if not _has_declared_type(value, _RESULT_TYPES) or not issubclass(
        type(value), _SealedOutcome
    ):
        raise InvalidFamilyInput("Expected a declared Track B outcome")
    _check_seal(value)
    return value


def _check_denominator_reason(reason):
    if not any(
        reason is member
        for enum in _REFUSAL_REASONS.values()
        for member in enum
    ):
        raise InvalidFamilyInput("Unknown Track B refusal reason enum")


def _public_reader_argument(value):
    """Check protocol arguments without executing an undeclared protocol.

    The dunder surface has no callback slots. Its values are the same
    declared data as ordinary calls, plus Python's exact traceback type for
    exception chaining. Attribute names and mapping keys are checked more
    narrowly by their individual protocols.
    """
    from types import TracebackType

    if _has_declared_type(value, _STATEFUL_TYPES):
        value._check_initialized()
        return value
    if type(value) is TracebackType:
        return value
    if type(value) is dict or type(value) is MappingProxyType:
        if type(value) is MappingProxyType:
            from gc import get_referents

            backing = get_referents(value)
            if len(backing) != 1 or type(backing[0]) is not dict:
                raise InvalidFamilyInput(
                    "Reader mappings need a built-in dict"
                )
            value = backing[0]
        pairs = [
            (_public_reader_argument(key), _public_reader_argument(item))
            for key, item in value.items()
        ]
        result = dict(pairs)
        if len(result) != len(pairs):
            raise InvalidFamilyInput("Reader mapping keys cannot collide")
        return result
    return _rebuild_declared(value)


def _checked_keyword_names(keywords):
    # Variadic wrappers let us reject before Python matches parameter names.
    if any(type(name) is not str for name in keywords):
        raise InvalidFamilyInput(
            "Reader argument names must be built-in strings"
        )


def _public_receiver(arguments, keywords, receiver_name="self"):
    if not keywords and arguments:
        return arguments[0], arguments[1:], keywords
    _checked_keyword_names(keywords)
    if arguments:
        if receiver_name in keywords:
            raise _InvalidInputType("Receiver was supplied twice")
        return arguments[0], arguments[1:], keywords
    if receiver_name not in keywords:
        raise _InvalidInputType("Missing Track B receiver")
    keywords = dict(keywords)
    return keywords.pop(receiver_name), (), keywords


def _public_fixed_arguments(arguments, keywords, names):
    if not keywords and len(arguments) == len(names):
        return arguments
    _checked_keyword_names(keywords)
    if len(arguments) > len(names):
        raise _InvalidInputType("Too many Track B protocol arguments")
    supplied = dict(zip(names, arguments, strict=False))
    for name, value in keywords.items():
        if name not in names or name in supplied:
            raise _InvalidInputType("Unknown or duplicate protocol argument")
        supplied[name] = value
    if len(supplied) != len(names):
        raise _InvalidInputType("Missing Track B protocol argument")
    return tuple(supplied[name] for name in names)


def _public_class_argument(value):
    """Metadata accepts class objects without consulting their protocols."""
    if _has_declared_type(value, (type, type(Mapping), type(Enum))):
        return value
    if issubclass(type(value), type):
        raise InvalidFamilyInput("Undeclared Track B metadata metaclass")
    if value is Ellipsis:
        return value
    if type(value) is tuple:
        return tuple(_public_class_argument(item) for item in value)
    if type(value) is GenericAlias or type(value) is UnionType:
        for item in object.__getattribute__(value, "__args__"):
            _public_class_argument(item)
        return value
    return _public_reader_argument(value)


def _checked_class_method(cls, method, name):
    """Class metadata hooks use class receivers, including new subclasses."""
    method = getattr(method, "_track_b_class_reader", method)

    @wraps(method)
    def checked(*arguments, **keywords):
        receiver, args, kwargs = _public_receiver(arguments, keywords, "cls")
        if type(receiver) is not type(cls) or not any(
            base is cls for base in type.__getattribute__(receiver, "__mro__")
        ):
            raise InvalidFamilyInput("Undeclared Track B class receiver")
        args = tuple(_public_class_argument(arg) for arg in args)
        kwargs = {
            key: _public_class_argument(arg) for key, arg in kwargs.items()
        }
        if name == "__class_getitem__":
            if len(args) != 1 or kwargs:
                raise _InvalidInputType("Expected one generic alias argument")
            return GenericAlias(receiver, args[0])
        return method(*args, **kwargs)

    checked._track_b_class_reader = method
    return classmethod(checked)


def _during_initialization(initialize):
    """Distinguish internal dataclass post-init from its public direct call."""
    initialize = getattr(initialize, "_track_b_initializing", initialize)

    @wraps(initialize)
    def checked(self, *args, **kwargs):
        object.__setattr__(self, "_g_initializing", _INITIALIZING)
        try:
            return initialize(self, *args, **kwargs)
        finally:
            object.__delattr__(self, "_g_initializing")

    checked._track_b_initializing = initialize
    return checked


def _checked_public_methods(cls):
    """Guard every instance API, including generated and inherited readers.

    A direct ``Class.reader(foreign)`` or ``property.fget(foreign)`` must
    reject before reading even ``foreign.__class__``. Attribute lookup is
    deliberately only a type/name check: recursively checking a seal on
    each field read would recurse into its own seal and repeat snapshots.
    Ordinary decorated methods retain their full field/argument schemas.
    """

    if cls not in _RESULT_TYPES and cls not in _DECLARATION_TYPES:
        _STATEFUL_TYPES.add(cls)

    def guard(method, name):
        # Inherited wrappers belong to their declaring class. Rewrap the
        # underlying implementation for each exact registered subclass.
        method = getattr(method, "_track_b_reader", method)
        protocol_kind = {
            "__format__": str,
            "__reduce_ex__": int,
            "__deepcopy__": dict,
            "__setstate__": dict,
            "__getitem__": str,
            "__contains__": str,
            "add_note": str,
        }.get(name)

        # This is immutable method metadata, never cached caller state.
        is_post_init = name == "__post_init__"
        is_get = name == "get"
        is_traceback = name == "with_traceback"
        snapshot_arguments = (
            name.startswith("__")
            or name
            in {"get", "keys", "items", "values", "add_note", "with_traceback"}
        ) and name != "__init__"
        check_integrity = name in {
            "__eq__",
            "__ne__",
            "__lt__",
            "__le__",
            "__gt__",
            "__ge__",
            "__repr__",
            "__str__",
            "__hash__",
            "__format__",
            "__iter__",
            "__len__",
            "__getitem__",
            "__contains__",
            "__getstate__",
            "__dir__",
            "__sizeof__",
            "add_note",
            "with_traceback",
            "__reduce__",
            "__reduce_ex__",
            "get",
            "keys",
            "items",
            "values",
        }
        sealed = cls in _RESULT_TYPES
        declaration = cls in _DECLARATION_TYPES

        @wraps(method)
        def checked(*arguments, **keywords):
            self, args, kwargs = _public_receiver(arguments, keywords)
            if type(self) is not cls:
                raise InvalidFamilyInput("Undeclared Track B reader receiver")
            if protocol_kind is not None and any(
                type(value) is not protocol_kind
                for value in (*args, *kwargs.values())
            ):
                raise InvalidFamilyInput("Invalid Track B protocol argument")
            if is_get and (
                (args and type(args[0]) is not str)
                or ("key" in kwargs and type(kwargs["key"]) is not str)
            ):
                raise InvalidFamilyInput("Mapping lookup keys must be strings")
            if is_traceback:
                from types import TracebackType

                if any(
                    value is not None and type(value) is not TracebackType
                    for value in (*args, *kwargs.values())
                ):
                    raise InvalidFamilyInput("Expected a built-in traceback")
            if snapshot_arguments:
                if args:
                    args = tuple(_public_reader_argument(arg) for arg in args)
                if kwargs:
                    kwargs = {
                        key: _public_reader_argument(arg)
                        for key, arg in kwargs.items()
                    }
            if is_post_init and (
                getattr(self, "_g_initializing", None) is not _INITIALIZING
            ):
                if sealed:
                    _check_seal(self)
                else:
                    self = _translate_input_error(
                        lambda: _snapshot_declaration(self)
                    )
            if check_integrity:
                if sealed:
                    _check_seal(self)
                elif declaration:
                    self = _translate_input_error(
                        lambda: _snapshot_declaration(self)
                    )
            return method(self, *args, **kwargs)

        checked._track_b_reader = method
        return checked

    for name in dir(cls):
        if name.startswith("_") and not (
            name.startswith("__") and name.endswith("__")
        ):
            continue
        if name in {
            "__class__",
            "__init__",
            "__new__",
            "__getattribute__",
            "__setattr__",
            "__delattr__",
        }:
            continue
        member = getattr(cls, name)
        if name in {
            "__class_getitem__",
            "__init_subclass__",
            "__subclasshook__",
        }:
            setattr(cls, name, _checked_class_method(cls, member, name))
        elif isinstance(member, property):
            setattr(
                cls,
                name,
                property(guard(member.fget, name), doc=member.__doc__),
            )
        elif callable(member):
            setattr(cls, name, guard(member, name))

    attribute_reader = getattr(
        cls.__getattribute__, "_track_b_reader", cls.__getattribute__
    )

    def getattribute(
        self=_MISSING_ARGUMENT,
        name=_MISSING_ARGUMENT,
        /,
        *arguments,
        **keywords,
    ):
        # Positional-only slots cannot match hostile keyword-name objects.
        # The uncommon keyword spelling still uses the checked binder.
        if (
            arguments
            or keywords
            or self is _MISSING_ARGUMENT
            or name is _MISSING_ARGUMENT
        ):
            supplied = (
                tuple(
                    value
                    for value in (self, name)
                    if value is not _MISSING_ARGUMENT
                )
                + arguments
            )
            self, name = _public_fixed_arguments(
                supplied, keywords, ("self", "name")
            )
        if type(self) is not cls or type(name) is not str:
            raise InvalidFamilyInput("Invalid Track B attribute reader")
        _checked_instance_dict(self)
        return attribute_reader(self, name)

    getattribute._track_b_reader = attribute_reader
    cls.__getattribute__ = getattribute

    def attribute_writer(method, names):
        method = getattr(method, "_track_b_reader", method)

        def checked(*arguments, **keywords):
            self, name, *args = _public_fixed_arguments(
                arguments, keywords, names
            )
            if type(self) is not cls or type(name) is not str:
                raise InvalidFamilyInput("Invalid Track B attribute writer")
            # Private guard state is written by its own implementation.
            # Access to private implementation names is outside this API.
            private = name.startswith("_") and not (
                name.startswith("__") and name.endswith("__")
            )
            if not private:
                if name == "__notes__":
                    # BaseException.add_note installs a list, then appends
                    # to that same list. Validate its complete schema while
                    # preserving this caller-owned metadata's identity.
                    notes = args[0]
                    if type(notes) is not list or any(
                        type(note) is not str for note in notes
                    ):
                        raise InvalidFamilyInput(
                            "Exception notes must be a built-in list of strings"
                        )
                else:
                    args = tuple(_public_reader_argument(arg) for arg in args)
            _checked_instance_dict(self)
            return method(self, name, *args)

        checked._track_b_reader = method
        return checked

    cls.__setattr__ = attribute_writer(
        cls.__setattr__, ("self", "name", "value")
    )
    cls.__delattr__ = attribute_writer(cls.__delattr__, ("self", "name"))
    construct = getattr(cls.__new__, "_track_b_reader", cls.__new__)

    def new(*arguments, **keywords):
        declared, args, kwargs = _public_receiver(
            arguments, keywords, "declared"
        )
        if declared is not cls:
            raise InvalidFamilyInput("Undeclared Track B constructor receiver")
        # Reject foreign raw kinds even when __new__ is called directly.
        # __init__ owns the field-by-field schema; no field is read here.
        for value in (*args, *kwargs.values()):
            if value is _RESULT_SEAL:
                continue
            if (
                _has_declared_type(
                    value,
                    (
                        int,
                        float,
                        str,
                        bool,
                        bytes,
                        date,
                        Decimal,
                        Fraction,
                        tuple,
                        list,
                        dict,
                        set,
                        frozenset,
                        MappingProxyType,
                        type(None),
                    ),
                )
                or _has_declared_type(value, _RESULT_TYPES)
                or _has_declared_type(value, _DECLARATION_TYPES)
                or _has_declared_type(value, _external_declarations())
                or _has_declared_type(value, _ENUM_TYPES)
            ):
                continue
            raise InvalidFamilyInput("Undeclared Track B constructor argument")
        # object.__new__ ignores constructor arguments when __init__ owns
        # them. Exception.__new__ stores args; its public constructor still
        # requires the private computation capability in __init__.
        if construct is object.__new__:
            return construct(declared)
        return construct(declared, *args, **kwargs)

    # Preserve the declared constructor API while the variadic runtime
    # binder checks keyword kinds before Python can invoke their hooks.
    new.__signature__ = signature(cls.__init__)
    new._track_b_reader = construct
    cls.__new__ = staticmethod(new)
    return cls


_DECLARATION_TYPES = _TypeRegistry()


def _exact_number(value, label):
    """Normalize exact money without retaining user-defined numeric behavior.

    Only built-in int, Fraction, Decimal, float and str encodings are
    admitted. Floats use their shortest decimal repr, as G always has.
    Fraction components must themselves be built-in integers. Returning a
    fresh Fraction also detaches a caller's object.__setattr__ mutations.
    """
    if not _has_declared_type(value, (int, Fraction, Decimal, float, str)):
        raise _InvalidInputType(f"{label} must be a built-in exact number")
    try:
        if type(value) is Fraction:
            numerator, denominator = _fraction_parts(value, label)
            return Fraction(numerator, denominator)
        if type(value) is float:
            if not math.isfinite(value):
                raise InvalidFamilyInput(f"{label} must be finite")
            value = repr(value)
        # This branch constructs a fresh built-in Fraction already. The
        # Fraction-input branch above separately detaches caller-held state.
        return Fraction(value)
    except (ValueError, OverflowError, ZeroDivisionError) as error:
        raise InvalidFamilyInput(f"{label} must be a finite number") from error


# Schemas are compiled once; caller values are never cached. An annotation is
# a declaration of shape, with the few legacy numeric aliases resolved below.
_INITIALIZERS = {}


def _numeric_schema(value, label, *, floats=True):
    if not floats and type(value) is float:
        raise _InvalidInputType(f"{label} requires an exact number")
    return _exact_number(value, label)


def _parameter_encoding_schema(value, label):
    """Preserve immutable external SSA encodings, as before this boundary."""
    if type(value) is int:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    try:
        exact = _exact_number(value, label)
    except _InvalidInputType:
        raise
    except InvalidFamilyInput as error:
        raise InvalidFamilyInput(
            f"{error}; parameter value disagrees with the statutory domain"
        ) from error
    return value if type(value) is str else exact


def _calendar_schema(value, label):
    if type(value) is not int or not 1 <= value <= 9999:
        raise _InvalidInputType(
            f"{label} needs calendar-year keys (built-in int)"
        )
    return value


def _scalar_schema(expected):
    def read(value, label):
        if expected is int and (
            (type(value) is float and not math.isfinite(value))
            or (type(value) is Decimal and not value.is_finite())
        ):
            raise _InvalidInputType(f"{label} must be finite")
        if type(value) is not expected:
            raise _InvalidInputType(f"{label} must be an {expected.__name__}")
        return value

    return read


def _enum_schema(expected):
    members = tuple(expected)

    def read(value, label):
        if not any(value is member for member in members):
            raise _InvalidInputType(
                f"{label} must be a canonical {expected.__name__} member"
            )
        return value

    return read


def _union_schema(readers):
    def read(value, label):
        first = None
        for reader in readers:
            try:
                return reader(value, label)
            except InvalidFamilyInput as error:
                if first is None:
                    first = error
        raise first

    return read


def _optional_schema(reader):
    def read(value, label):
        return None if value is None else reader(value, label)

    return read


def _collection_schema(readers, *, pair=False, unordered=False):
    allowed = (tuple, list, set, frozenset) if unordered else (tuple, list)

    def read(value, label):
        if not _has_declared_type(value, allowed):
            raise _InvalidInputType(f"{label} must be a built-in collection")
        if pair and len(value) != len(readers):
            raise _InvalidInputType(f"{label} needs {len(readers)} values")
        # No hashing/deduplication until EVERY raw element has been checked.
        items = [
            (readers[index] if pair else readers[0])(item, f"{label}[{index}]")
            for index, item in enumerate(value)
        ]
        return frozenset(items) if unordered else tuple(items)

    return read


def _mapping_schema(key_reader, value_reader, *, r1_proxy=False):
    def read(value, label):
        if r1_proxy and type(value) is MappingProxyType:
            # R1 stores its declared dictionary behind a read-only view.
            # Inspect the backing object before invoking mapping methods;
            # a proxy around a custom Mapping is not a declared dictionary.
            from gc import get_referents

            backing = get_referents(value)
            if len(backing) != 1 or type(backing[0]) is not dict:
                raise _InvalidInputType(f"{label} needs a built-in dict")
            value = backing[0]
        if type(value) is not dict:
            raise _InvalidInputType(f"{label} must be a built-in dict")
        length = len(value)
        items = [
            (key_reader(key, label + " key"), value_reader(item, label))
            for key, item in value.items()
        ]
        result = dict(items)
        if len(items) != length or len(result) != length:
            raise _InvalidInputType(f"{label} needs distinct valid keys")
        return result

    return read


def _callback_schema(value, label):
    if not callable(value):
        raise _InvalidInputType(f"{label} must be callable")
    return value


@cache
def _external_declarations():
    from populace_dynamics.ss.params import SSAParameters
    from populace_dynamics.track_b.ret_params import (
        ParameterValue,
        ProjectionInputs,
        RETParameters,
        RETYear,
        SourcePin,
    )

    declarations = (
        SSAParameters,
        ParameterValue,
        ProjectionInputs,
        RETParameters,
        RETYear,
        SourcePin,
    )
    for cls in declarations:
        _register_declaration_enums(cls)
    return declarations


def _schema(annotation, module, *, name="", owner=None):
    origin, args = get_origin(annotation), get_args(annotation)
    exact = module.endswith((".arf", ".recompute", ".ret_ledger"))
    if annotation is object or annotation is Fraction:
        return lambda value, label: _numeric_schema(
            value,
            label,
            floats=not exact
            or (name == "weight" and not module.endswith(".ret_ledger")),
        )
    if annotation in (int, str, bool, bytes, date, type(None)):
        return _scalar_schema(annotation)
    if annotation in (float, Decimal):
        return _parameter_encoding_schema
    if origin in (Union, UnionType):
        optional = type(None) in args
        readers = tuple(
            _schema(a, module) for a in args if a is not type(None)
        )
        reader = readers[0] if len(readers) == 1 else _union_schema(readers)
        return _optional_schema(reader) if optional else reader
    if origin is Literal:

        def literal(value, label):
            if not any(type(value) is type(a) and value == a for a in args):
                raise _InvalidInputType(f"{label} must be one of {args}")
            return value

        return literal
    if origin is Callable or annotation is Callable:
        return _callback_schema
    if origin in (tuple, list, set, frozenset, Sequence):
        pair = origin is tuple and len(args) > 1 and args[-1] is not Ellipsis
        elements = args if pair else args[:1]
        return _collection_schema(
            tuple(_schema(a, module) for a in elements),
            pair=pair,
            unordered=origin in (set, frozenset),
        )
    if origin in (dict, Mapping):
        key, item = args
        item_reader = _schema(item, module)
        if module.endswith(".recompute") and name in (
            "history",
            "december_cola_percent",
        ):
            from populace_dynamics.track_b.recompute import (
                EarningsAvailability,
            )

            item_reader = _union_schema(
                (
                    _enum_schema(EarningsAvailability),
                    item_reader,
                )
            )
        return _mapping_schema(
            _schema(key, module),
            item_reader,
            r1_proxy=owner in _external_declarations()[1:],
        )
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        _ENUM_TYPES.add(annotation)
        return _enum_schema(annotation)
    if (
        annotation in _DECLARATION_TYPES
        or annotation in _external_declarations()
    ):

        def declaration(value, label):
            if type(value) is not annotation:
                raise _InvalidInputType(
                    f"{label} must be an {annotation.__name__}"
                )
            return _snapshot_declaration(value)

        return declaration
    if annotation in _RESULT_TYPES or annotation is _SealedOutcome:

        def result(value, label):
            if annotation is _SealedOutcome:
                if not any(
                    type(value) is t and issubclass(t, _SealedOutcome)
                    for t in _RESULT_TYPES
                ):
                    raise _InvalidInputType(
                        f"{label} needs a declared outcome"
                    )
            elif type(value) is not annotation:
                raise _InvalidInputType(
                    f"{label} must be an {annotation.__name__}"
                )
            _check_seal(value)
            return value

        return result
    # Guards are stateful public receivers, not declaration data. Their
    # identity must survive a household call; their state is checked by them.
    from populace_dynamics.track_b.gross_benefits import SavingsClauseGuard

    if annotation is SavingsClauseGuard:

        def guard(value, label):
            if type(value) is not SavingsClauseGuard:
                raise _InvalidInputType(
                    f"{label} must be a SavingsClauseGuard"
                )
            value._check_initialized()
            return value

        return guard
    raise TypeError(f"No Track B input schema for {annotation!r}")


@cache
def _declaration_schemas(cls):
    hints = get_type_hints(cls)
    schemas = {
        item.name: _schema(
            hints[item.name], cls.__module__, name=item.name, owner=cls
        )
        for item in fields(cls)
        if item.init
    }
    if cls is _external_declarations()[0]:
        for name in ("nawi", "wage_base"):
            schemas[name] = _mapping_schema(
                _calendar_schema, _parameter_encoding_schema
            )
        schemas["fra_months_by_birth_year"] = _collection_schema(
            (
                _collection_schema(
                    (_calendar_schema, _scalar_schema(int)), pair=True
                ),
            )
        )
        schemas["delayed_credit_by_birth_year"] = _collection_schema(
            (
                _collection_schema(
                    (_calendar_schema, _parameter_encoding_schema), pair=True
                ),
            )
        )

        def revision(value, label):
            if type(value) is not str or not value:
                raise _InvalidInputType("pe_us_revision must be nonempty text")
            return value

        schemas["pe_us_revision"] = revision
    if cls.__name__ == "WorkerRecord":
        # The AIME declaration has always admitted only integers or exact
        # integral Fractions, unlike the more general money encodings.
        number = schemas["aime"]

        def aime(value, label):
            if value is not None and not _has_declared_type(
                value, (int, Fraction)
            ):
                raise _InvalidInputType(
                    "AIME must be an int or an integral Fraction"
                )
            return number(value, label)

        schemas["aime"] = aime
    return schemas


def _snapshot_declaration(value):
    cls = type(value)
    _checked_instance_dict(value)
    read_attribute = (
        object.__getattribute__
        if _has_declared_type(value, _DECLARATION_TYPES)
        else getattr
    )
    values = {
        name: read(read_attribute(value, name), name)
        for name, read in _declaration_schemas(cls).items()
    }
    result = object.__new__(cls)
    initialize = _INITIALIZERS.get(cls, cls.__init__)
    initialize(result, **values)
    return result


def _construct_declared(cls, *args, **kwargs):
    """Build derived private data without re-entering its public schema.

    Callers supply already-owned fields or internally derived values. The
    original initializer still executes the declaration's domain checks.
    """
    result = object.__new__(cls)
    _INITIALIZERS[cls](result, *args, **kwargs)
    return result


def _replace_declared(value, **changes):
    """Replace fields of owned private data, retaining domain checks."""
    cls = type(value)
    values = {
        name: object.__getattribute__(value, name)
        for name in _dataclass_init_field_names(cls)
    }
    values.update(changes)
    return _construct_declared(cls, **values)


def _translate_input_error(action):
    try:
        return action()
    except InvalidFamilyInput:
        raise
    except (
        AttributeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise _InvalidInputType(
            f"Malformed declared input: {error}"
        ) from error


def _call_binder(function, *, defaults):
    """Compile call layouts, never retaining any caller's argument values."""
    declared = signature(function)
    # Track B has fixed, keyword-addressable public signatures. Keeping this
    # invariant explicit avoids quietly mishandling a future variadic API.
    if any(
        parameter.kind
        not in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY)
        for parameter in declared.parameters.values()
    ):
        raise TypeError("Track B public calls need fixed declared arguments")

    @cache
    def layout(positional_count, keyword_names):
        # signature.bind supplies Python's missing/duplicate/unknown-argument
        # checks once per layout. The placeholders contain no caller data.
        positional = [None] * positional_count
        keywords = dict.fromkeys(keyword_names)
        bound = declared.bind(*positional, **keywords)
        positional_names = tuple(bound.arguments)[:positional_count]
        entries = tuple(enumerate(positional_names))
        supplied = set(bound.arguments)
        omitted = (
            tuple(
                (name, parameter.default)
                for name, parameter in declared.parameters.items()
                if name not in supplied
            )
            if defaults
            else ()
        )
        return entries, omitted

    def bind(args, kwargs):
        if any(type(name) is not str for name in kwargs):
            raise _InvalidInputType("Argument names must be built-in strings")
        entries, omitted = layout(len(args), tuple(kwargs))
        values = {name: args[index] for index, name in entries}
        values.update(kwargs)
        values.update(omitted)
        return values

    return bind


def _declared_input(cls):
    """Declare a field schema and validate each constructor exactly once."""
    _DECLARATION_TYPES.add(cls)
    _register_declaration_enums(cls)
    initialize = _during_initialization(cls.__init__)
    _INITIALIZERS[cls] = initialize
    bind = _call_binder(initialize, defaults=False)
    defaults = {item.name: item for item in fields(cls)}
    public_readers = frozenset(
        name
        for name in dir(cls)
        if (not name.startswith("_") or name.startswith("__"))
        and (
            callable(getattr(cls, name))
            or isinstance(getattr(cls, name), property)
        )
    )

    @wraps(initialize)
    def initialize_declared(*arguments, **keywords):
        self, args, kwargs = _public_receiver(arguments, keywords)
        if type(self) is not cls:
            raise InvalidFamilyInput("Undeclared Track B input subclass")

        def construct():
            arguments = bind((self, *args), kwargs)
            values = {}
            for name, read in _declaration_schemas(cls).items():
                if name in arguments:
                    value = arguments[name]
                else:
                    item = defaults[name]
                    value = (
                        item.default_factory()
                        if item.default_factory is not MISSING
                        else item.default
                    )
                values[name] = read(value, name)
            # Reinitializing a declaration must not dispatch a caller's
            # instance shadow of a generated/public constructor reader.
            # Inert caller metadata remains outside the declaration schema.
            attributes = object.__getattribute__(self, "__dict__")
            if type(attributes) is not dict or any(
                type(name) is not str or name in public_readers
                for name in attributes
            ):
                raise InvalidFamilyInput(
                    "Declaration methods cannot be shadowed"
                )
            initialize(self, **values)

        _translate_input_error(construct)

    cls.__init__ = initialize_declared
    return _checked_public_methods(cls)


@cache
def _argument_schemas(function):
    hints = get_type_hints(function)
    declared = signature(function)
    schemas = {}
    for name, parameter in declared.parameters.items():
        annotation = hints.get(name)
        if name == "self":
            cls_name = function.__qualname__.split(".")[0]
            annotation = function.__globals__[cls_name]
        if annotation is None:
            raise TypeError(
                f"Missing Track B input schema: {function.__qualname__}.{name}"
            )
        schemas[name] = (
            _scalar_schema(annotation)
            if name == "self" and function.__name__ == "__init__"
            else _schema(annotation, function.__module__, name=name)
        )
        if parameter.default is None and annotation is object:
            schemas[name] = _optional_schema(schemas[name])
    return schemas


def _validated_entry(function):
    """Validate a public call once, then run on its owned snapshot.

    Internal callers use private helpers. A callback is an executable slot;
    it is checked with callable(), never inspected or reconstructed as data.
    """
    bind = _call_binder(function, defaults=True)

    @wraps(function)
    def validated(*args, **kwargs):
        def snapshot():
            values = bind(args, kwargs)
            readers = _argument_schemas(function)
            return {
                name: readers[name](value, name)
                for name, value in values.items()
            }

        values = _translate_input_error(snapshot)
        return function(**values)

    return validated


def _rebuild_declared(value):
    """Private snapshot adapter, with no undeclared pass-through case."""

    def snapshot():
        cls = type(value)
        if _has_declared_type(value, _DECLARATION_TYPES) or _has_declared_type(
            value, _external_declarations()
        ):
            return _snapshot_declaration(value)
        if _has_declared_type(value, _RESULT_TYPES):
            _check_seal(value)
            return value
        if _has_declared_type(value, (Fraction, Decimal)):
            return _exact_number(value, "declared number")
        if _has_declared_type(
            value, (int, float, str, bool, bytes, date, type(None))
        ):
            return value
        if _has_declared_type(value, _ENUM_TYPES):
            return _enum_schema(cls)(value, "declared enum")
        if _has_declared_type(value, (tuple, list, set, frozenset)):
            items = [_rebuild_declared(item) for item in value]
            return cls(items)
        raise _InvalidInputType("Undeclared Track B input")

    return _translate_input_error(snapshot)


def _fraction_parts(value, label):
    """Copy only validated immutable components into a numeric snapshot."""
    numerator, denominator = value.numerator, value.denominator
    if type(numerator) is not int or type(denominator) is not int:
        raise _InvalidInputType(f"{label} needs built-in integer components")
    if denominator <= 0:
        raise InvalidFamilyInput(f"{label} needs a positive denominator")
    return numerator, denominator
