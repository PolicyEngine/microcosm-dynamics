"""Package-private provenance for Track B statutory computations.

Verification class: statutory conformance on invented and published cases
only. This is an API contract, with no population or forecast claim and no
security boundary against access to Python's private implementation names.
Public arguments and declaration fields have explicit schemas. Raw scalar
kinds and declaration types use identity, enum values must be canonical
members, and containers must be exact built-ins. Raw container contents are
checked before hashing or reconstruction. Callback slots are executable,
not data. Each public call owns a fresh snapshot; private helpers reuse it.
The contract excludes code accessing private names, monkeypatching modules,
or mutating an input from another thread during a call.
One private capability seals every declared G, R2 and R3 result, refusal,
outcome and denominator. Public construction and copying are input errors;
serialization is rejected. Persist declared inputs and recompute instead.
"""

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import MISSING, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import cache, wraps
from inspect import signature
from types import MappingProxyType, UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

__all__ = []


class InvalidFamilyInput(ValueError):
    """The inputs do not describe a legal family (not a coverage gap)."""


class _InvalidInputType(InvalidFamilyInput, TypeError):
    """An input error, also retaining the constructor's TypeError contract."""


_RESULT_SEAL = object()
_RESULT_TYPES = set()
_REFUSAL_REASONS = {}


def _has_declared_type(value, types):
    """Do not let a user-defined metaclass spoof type membership."""
    return any(type(value) is expected for expected in types)


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


def _result_values(value):
    names = (
        [item.name for item in fields(value)]
        if is_dataclass(value)
        else ("reason", "detail", "beneficiary_id", "record_id")
    )
    return {name: getattr(value, name) for name in names}


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
        payload = value._g_seal[2]
    elif _has_declared_type(value, _DECLARATION_TYPES):
        payload = tuple(
            (item.name, _seal_value(getattr(value, item.name)))
            for item in fields(value)
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
    elif isinstance(cls, type) and issubclass(cls, Enum):
        payload = _enum_schema(cls)(value, "sealed enum")
    else:
        raise _InvalidInputType("Undeclared computed-result field")
    return cls, payload


def _seal_payload(value):
    try:
        return type(value), tuple(
            (key, _seal_value(item))
            for key, item in _result_values(value).items()
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
    seal = getattr(value, "_g_seal", None)
    if (
        not _has_declared_type(value, _RESULT_TYPES)
        or not isinstance(seal, tuple)
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
    initialize = getattr(cls.__init__, "__wrapped__", cls.__init__)
    _RESULT_TYPES.add(cls)

    @wraps(initialize)
    def initialize_computed(self, *args, _seal=None, **kwargs):
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
    return cls


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
    if not isinstance(value, _SealedOutcome):
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


_DECLARATION_TYPES = set()


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
        return type(value)(items)

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

    return (
        SSAParameters,
        ParameterValue,
        ProjectionInputs,
        RETParameters,
        RETYear,
        SourcePin,
    )


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
    if origin in (tuple, list, set, frozenset, Iterable, Sequence):
        pair = origin is tuple and len(args) > 1 and args[-1] is not Ellipsis
        elements = args if pair else args[:1]
        return _collection_schema(
            tuple(_schema(a, module) for a in elements),
            pair=pair,
            unordered=origin in (set, frozenset, Iterable),
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
    values = {
        name: read(getattr(value, name), name)
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
    values = {
        item.name: getattr(value, item.name)
        for item in fields(value)
        if item.init
    }
    values.update(changes)
    return _construct_declared(type(value), **values)


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
    initialize = cls.__init__
    _INITIALIZERS[cls] = initialize
    bind = _call_binder(initialize, defaults=False)
    defaults = {item.name: item for item in fields(cls)}

    @wraps(initialize)
    def initialize_declared(self, *args, **kwargs):
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
            initialize(self, **values)

        _translate_input_error(construct)

    cls.__init__ = initialize_declared
    return cls


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
        if isinstance(cls, type) and issubclass(cls, Enum):
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
