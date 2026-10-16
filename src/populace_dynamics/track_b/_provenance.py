"""Package-private provenance for Track B statutory computations.

Verification class: statutory conformance on invented and published cases
only. This is an API contract, with no population or forecast claim and no
security boundary against access to Python's private implementation names.
One private capability seals every declared G, R2 and R3 result, refusal,
outcome and denominator. Public construction and copying are input errors;
serialization is rejected. Persist declared inputs and recompute instead.
"""

import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import wraps
from inspect import signature
from types import MappingProxyType

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
    if isinstance(value, (int, float, Fraction, Decimal)) and not isinstance(
        value, bool
    ):
        if not _has_declared_type(value, (int, float, Fraction, Decimal)):
            raise InvalidFamilyInput(
                "Numeric subclasses are not declared inputs"
            )
        if type(value) is Fraction:
            return Fraction, _fraction_parts(value, "sealed number")
    if isinstance(value, _SealedResult):
        _check_seal(value)
        payload = value._g_seal[2]
    elif is_dataclass(value):
        payload = tuple(
            (item.name, _seal_value(getattr(value, item.name)))
            for item in fields(value)
        )
    elif isinstance(value, Mapping):
        payload = tuple(
            (_seal_value(key), _seal_value(item))
            for key, item in value.items()
        )
    elif isinstance(value, (tuple, list)):
        payload = tuple(_seal_value(item) for item in value)
    elif isinstance(value, (set, frozenset)):
        payload = frozenset(_seal_value(item) for item in value)
    else:
        payload = value
    return type(value), payload


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
    if expected is None or type(reason) is not expected:
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
    if not _has_declared_type(reason, _REFUSAL_REASONS.values()):
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


def _declared_input(cls):
    """Register an exact declaration and detach its entire validated tree."""
    _DECLARATION_TYPES.add(cls)
    initialize = cls.__init__
    constructor = signature(initialize)

    @wraps(initialize)
    def initialize_declared(self, *args, **kwargs):
        if type(self) is not cls:
            raise InvalidFamilyInput("Undeclared Track B input subclass")
        try:
            bound = constructor.bind(self, *args, **kwargs)
            bound.apply_defaults()
            for name, value in tuple(bound.arguments.items()):
                if name != "self":
                    bound.arguments[name] = _rebuild_declared(value)
            initialize(*bound.args, **bound.kwargs)
        except InvalidFamilyInput:
            raise
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            raise _InvalidInputType("Malformed declared input") from error

    cls.__init__ = initialize_declared
    return cls


def _rebuild_declared(value):
    """Recursively rebuild declarations before any coverage decision.

    Sealed evidence is checked, never treated as a declaration. The two
    external parameter schemas retain their builtin float encodings;
    layer-specific statutory checks still validate their meaning.
    """
    try:
        return _rebuild_declared_value(value)
    except InvalidFamilyInput:
        raise
    except (
        AttributeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        # Limit translation to traversing declared data. Exceptions raised
        # by a caller's computation remain programming errors.
        raise _InvalidInputType("Malformed declared input tree") from error


def _rebuild_declared_value(value):
    """Copy one tree node; recursive children use the checked traversal."""
    value_type = type(value)
    if (
        value_type is bool
        or value_type is int
        or value_type is float
        or value_type is str
        or value_type is bytes
        or value is None
    ):
        return value
    if isinstance(value, _SealedResult):
        _check_seal(value)
        return value
    if isinstance(value, Enum):
        return value
    if isinstance(value, (int, float, Fraction, Decimal)):
        if type(value) is bool:
            return value
        if not _has_declared_type(value, (int, float, Fraction, Decimal)):
            raise _InvalidInputType(
                "Numeric subclasses are not declared inputs"
            )
        if type(value) is Fraction or type(value) is Decimal:
            return _exact_number(value, "declared number")
        return value
    if isinstance(value, (str, bytes)):
        if type(value) is not str and type(value) is not bytes:
            raise _InvalidInputType("Text subclasses are not declared inputs")
        return value
    if isinstance(value, Mapping):
        rebuilt = {
            _rebuild_declared(key): _rebuild_declared(item)
            for key, item in value.items()
        }
        return (
            MappingProxyType(rebuilt)
            if type(value) is MappingProxyType
            else rebuilt
        )
    if isinstance(value, (tuple, list, set, frozenset)):
        if not _has_declared_type(value, (tuple, list, set, frozenset)):
            raise _InvalidInputType(
                "Collection subclasses are not declared inputs"
            )
        return type(value)(_rebuild_declared(item) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        # Parameter schemas are shared with other tracks, so registration
        # here must not change their public constructors elsewhere.
        from populace_dynamics.ss.params import SSAParameters
        from populace_dynamics.track_b.ret_params import (
            ParameterValue,
            ProjectionInputs,
            RETParameters,
            RETYear,
            SourcePin,
        )

        allowed = _DECLARATION_TYPES | {
            SSAParameters,
            ParameterValue,
            ProjectionInputs,
            RETParameters,
            RETYear,
            SourcePin,
        }
        if not _has_declared_type(value, allowed):
            raise _InvalidInputType("Undeclared Track B input subclass")
        registered = _has_declared_type(value, _DECLARATION_TYPES)
        try:
            if type(value) is SSAParameters:
                _check_parameter_shape(value)
            rebuilt = type(value)(
                **{
                    item.name: (
                        getattr(value, item.name)
                        if registered
                        else _rebuild_declared(getattr(value, item.name))
                    )
                    for item in fields(value)
                    if item.init
                }
            )
            if type(value) is SSAParameters:
                # A user-supplied Mapping can change between reads. Check
                # the detached snapshot that the computation will consume,
                # as well as the original for field-specific diagnostics.
                _check_parameter_shape(rebuilt)
            return rebuilt
        except InvalidFamilyInput:
            raise
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            raise _InvalidInputType("Malformed declared input") from error
    return value


def _validated_entry(function):
    """Compute from rebuilt declared inputs, before any coverage branch."""

    @wraps(function)
    def validated(*args, **kwargs):
        return function(
            *(_rebuild_declared(value) for value in args),
            **{key: _rebuild_declared(value) for key, value in kwargs.items()},
        )

    return validated


def _check_number_encoding(value, label):
    """Check a parameter leaf without allocating a discarded exact value."""
    if type(value) is int:
        return
    if type(value) is float and math.isfinite(value):
        return
    try:
        _exact_number(value, label)
    except _InvalidInputType:
        raise
    except InvalidFamilyInput as error:
        # Preserve both existing nonfinite-parameter diagnostics and G's
        # statutory-mismatch diagnostic at this earlier shared boundary.
        raise InvalidFamilyInput(
            f"{error}; parameter value disagrees with the statutory domain"
        ) from error


def _check_parameter_shape(params):
    """Validate the full external SSA declaration, including unused fields.

    SSAParameters has no validating constructor. This checks its declared
    structure and finite numeric encodings; each layer still checks the
    statutory domains it consumes. Empty series retain missing-data errors.
    """
    for item in fields(params):
        name, value = item.name, getattr(params, item.name)
        if name == "pe_us_revision":
            if type(value) is not str or not value:
                raise _InvalidInputType("pe_us_revision must be nonempty text")
        elif name in ("nawi", "wage_base"):
            if not isinstance(value, Mapping):
                raise _InvalidInputType(f"{name} must be a mapping")
            for year, amount in value.items():
                if type(year) is not int or not 1 <= year <= 9999:
                    raise _InvalidInputType(f"{name} needs calendar-year keys")
                _check_number_encoding(amount, name)
        elif name in (
            "pia_factors",
            "early_monthly_rates",
            "spousal_early_monthly_rates",
        ):
            length = 3 if name == "pia_factors" else 2
            if (
                not _has_declared_type(value, (tuple, list))
                or len(value) != length
            ):
                raise _InvalidInputType(f"{name} needs {length} numbers")
            for index, number in enumerate(value):
                _check_number_encoding(number, f"{name}[{index}]")
        elif name in (
            "fra_months_by_birth_year",
            "delayed_credit_by_birth_year",
        ):
            if not _has_declared_type(value, (tuple, list)):
                raise _InvalidInputType(f"{name} must be a schedule")
            for entry in value:
                if (
                    not _has_declared_type(entry, (tuple, list))
                    or len(entry) != 2
                ):
                    raise _InvalidInputType(f"{name} needs year/value pairs")
                year, number = entry
                if type(year) is not int or not 1 <= year <= 9999:
                    raise _InvalidInputType(f"{name} needs calendar years")
                _check_number_encoding(number, name)
                if (
                    name == "fra_months_by_birth_year"
                    and type(number) is not int
                ):
                    raise _InvalidInputType(
                        "FRA months must be a built-in int"
                    )
        elif item.type == "int":
            _check_number_encoding(value, name)
            if type(value) is not int:
                raise _InvalidInputType(f"{name} must be a built-in int")
        else:
            _check_number_encoding(value, name)


def _fraction_parts(value, label):
    """Copy only validated immutable components into a numeric snapshot."""
    numerator, denominator = value.numerator, value.denominator
    if type(numerator) is not int or type(denominator) is not int:
        raise _InvalidInputType(f"{label} needs built-in integer components")
    if denominator <= 0:
        raise InvalidFamilyInput(f"{label} needs a positive denominator")
    return numerator, denominator
