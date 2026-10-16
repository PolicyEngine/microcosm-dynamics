"""Package-private provenance for Track B statutory computations.

Verification class: statutory conformance on invented and published cases
only. This is an API contract, with no population or forecast claim and no
security boundary against access to Python's private implementation names.
One private capability seals every declared G, R2 and R3 result, refusal,
outcome and denominator. Public construction and copying are input errors;
pickle reconstruction repeats the declared type's accounting validation.
"""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from functools import wraps

__all__ = []


class InvalidFamilyInput(ValueError):
    """The inputs do not describe a legal family (not a coverage gap)."""


class _InvalidInputType(InvalidFamilyInput, TypeError):
    """An input error, also retaining the constructor's TypeError contract."""


_RESULT_SEAL = object()
_RESULT_TYPES = set()
_REFUSAL_REASONS = {}


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
        _check_seal(self)
        values = {
            key: dict(value) if isinstance(value, Mapping) else value
            for key, value in _result_values(self).items()
        }
        return _restore_sealed, (type(self), values)


def _result_values(value):
    names = (
        [item.name for item in fields(value)]
        if is_dataclass(value)
        else ("reason", "detail", "beneficiary_id", "record_id")
    )
    return {name: getattr(value, name) for name in names}


def _seal_value(value):
    """An immutable, type-sensitive snapshot, including nested seals."""
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
        return tuple(
            (key, _seal_value(item))
            for key, item in _result_values(value).items()
        )
    except (AttributeError, TypeError) as error:
        raise InvalidFamilyInput("Malformed computed-result fields") from error


def _check_seal(value):
    seal = getattr(value, "_g_seal", None)
    if (
        type(value) not in _RESULT_TYPES
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


def _restore_sealed(cls, values):
    """Private pickle reconstruction repeats all seal-time identities."""
    if cls not in _RESULT_TYPES:
        raise InvalidFamilyInput("Unknown Track B result type")
    return _computed(cls, **values)


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
    if is_dataclass(value):
        return replace(value)
    return value


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
    if type(value) not in _REFUSAL_REASONS:
        raise InvalidFamilyInput("Expected a declared Track B refusal")
    _check_reason(value, value.reason)
    _check_seal(value)
    return value


def _check_outcome(value):
    if not isinstance(value, _SealedOutcome):
        raise InvalidFamilyInput("Expected a declared Track B outcome")
    _check_seal(value)
    return value


def _check_denominator_reason(reason):
    if type(reason) not in _REFUSAL_REASONS.values():
        raise InvalidFamilyInput("Unknown Track B refusal reason enum")
