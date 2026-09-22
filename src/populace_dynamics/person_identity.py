"""Lossless, opt-in identities for integer-keyed Dynamics consumers.

This module transports identities. It does not admit a population, infer an
identity from household membership, or change an earnings generator's inputs.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from numbers import Integral
from types import MappingProxyType

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1
_UINT64_MAX = 2**64 - 1
_SCHEMA = "populace_dynamics.person_identity_map.v1"


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{label} must be an integer, not a coerced value")
    return int(value)


def _canonical_integer(value: object, label: str) -> int:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a canonical decimal string")
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be a canonical decimal string"
        ) from exc
    if str(result) != value:
        raise ValueError(f"{label} must be a canonical decimal string")
    return result


@dataclass(frozen=True)
class PersonIdentity:
    """An explicitly typed source identity, with no numeric/string coercion."""

    logical_type: str
    value: int | str

    def __post_init__(self) -> None:
        if not isinstance(self.logical_type, str):
            raise ValueError("unsupported person identity logical type")
        object.__setattr__(
            self, "logical_type", str.__str__(self.logical_type)
        )
        if self.logical_type not in ("int64", "uint64", "string"):
            raise ValueError("unsupported person identity logical type")
        if self.logical_type == "string":
            if not isinstance(self.value, str):
                raise ValueError("string identity requires a string value")
            # Copy the underlying string, bypassing mutable subclass methods.
            value = str.__str__(self.value)
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError(
                    "string identity requires valid UTF-8"
                ) from exc
            object.__setattr__(self, "value", value)
            return
        value = _integer(self.value, "identity")
        lower, upper = (
            (_INT64_MIN, _INT64_MAX)
            if self.logical_type == "int64"
            else (0, _UINT64_MAX)
        )
        if not lower <= value <= upper:
            raise ValueError(f"identity is outside {self.logical_type} range")
        object.__setattr__(self, "value", value)

    @property
    def canonical_value(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class IdentityEntry:
    identity: PersonIdentity
    dynamics_person_key: int

    def __post_init__(self) -> None:
        if type(self.identity) is not PersonIdentity:
            raise ValueError("entry requires an explicit PersonIdentity")
        key = _integer(self.dynamics_person_key, "dynamics person key")
        if not 0 <= key <= _INT64_MAX:
            raise ValueError(
                "dynamics person key is outside nonnegative int64"
            )
        object.__setattr__(self, "dynamics_person_key", key)


@dataclass(frozen=True)
class PersonIdentityMap:
    """Immutable dense private keys; extensions preserve every prior entry.

    New identities are sorted by (logical type, canonical value) within each
    admission batch. Sorting is lexical, not numeric. Batch order is therefore
    irrelevant, while the sequence of admission batches is part of identity.
    """

    entries: tuple[IdentityEntry, ...] = ()
    _forward: Mapping[PersonIdentity, int] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("PersonIdentityMap cannot be subclassed")

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        forward = {}
        for position, entry in enumerate(entries):
            if type(entry) is not IdentityEntry:
                raise ValueError("map entries must be IdentityEntry values")
            if entry.dynamics_person_key != position:
                raise ValueError(
                    "private keys must be unique and dense from 0"
                )
            if entry.identity in forward:
                raise ValueError("duplicate person identity")
            forward[entry.identity] = entry.dynamics_person_key
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "_forward", MappingProxyType(forward))

    @classmethod
    def from_identities(
        cls, identities: Iterable[PersonIdentity]
    ) -> "PersonIdentityMap":
        return cls().append(identities)

    def append(
        self, identities: Iterable[PersonIdentity]
    ) -> "PersonIdentityMap":
        """Admit only new identities; duplicate or previously admitted IDs fail."""
        pending = list(identities)
        seen: set[PersonIdentity] = set()
        for identity in pending:
            if type(identity) is not PersonIdentity:
                raise ValueError("admission requires explicit PersonIdentity")
            if identity in seen or identity in self._forward:
                raise ValueError(
                    "duplicate or already admitted person identity"
                )
            seen.add(identity)
        if len(pending) > _INT64_MAX + 1 - len(self.entries):
            raise ValueError("private int64 identity space exhausted")
        if not pending:
            return self
        pending.sort(
            key=lambda item: (item.logical_type, item.canonical_value)
        )
        start = len(self.entries)
        return type(self)(
            self.entries
            + tuple(
                IdentityEntry(identity, start + offset)
                for offset, identity in enumerate(pending)
            )
        )

    def map_rows(
        self, identities: Iterable[PersonIdentity]
    ) -> tuple[int, ...]:
        """Map in caller row order; repeated observations of an ID are valid."""
        result = []
        for identity in identities:
            if type(identity) is not PersonIdentity:
                raise ValueError("mapping requires explicit PersonIdentity")
            try:
                result.append(self._forward[identity])
            except KeyError as exc:
                raise ValueError(
                    "person identity has not been admitted"
                ) from exc
        return tuple(result)

    def reverse_rows(self, keys: Iterable[int]) -> tuple[PersonIdentity, ...]:
        """Reverse private keys without changing order, type or source value."""
        result = []
        for value in keys:
            key = _integer(value, "dynamics person key")
            if not 0 <= key < len(self.entries):
                raise ValueError("dynamics person key has not been admitted")
            result.append(self.entries[key].identity)
        return tuple(result)

    def require_extension_of(self, previous: "PersonIdentityMap") -> None:
        """Reject a loaded manifest that deletes, reorders or remaps old IDs."""
        if type(previous) is not PersonIdentityMap:
            raise ValueError("previous manifest must be a PersonIdentityMap")
        if self.entries[: len(previous.entries)] != previous.entries:
            raise ValueError(
                "identity map does not preserve the prior manifest"
            )

    def to_json(self) -> str:
        """Canonical UTF-8 JSON, with integer values encoded as decimal strings."""
        document = {
            "schema": _SCHEMA,
            "entries": [
                {
                    "logical_type": entry.identity.logical_type,
                    "value": entry.identity.canonical_value,
                    "dynamics_person_key": str(entry.dynamics_person_key),
                }
                for entry in self.entries
            ],
        }
        return json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @property
    def digest(self) -> str:
        """SHA-256 of canonical JSON; this is integrity, not admission authority."""
        return sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        expected_digest: str | None = None,
        previous: "PersonIdentityMap | None" = None,
    ) -> "PersonIdentityMap":
        def unique_object(pairs: list[tuple[str, object]]) -> dict:
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON field")
                result[key] = value
            return result

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-JSON numeric constant: {value}")

        document = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        if not isinstance(document, dict) or set(document) != {
            "schema",
            "entries",
        }:
            raise ValueError("invalid identity map document fields")
        if document["schema"] != _SCHEMA:
            raise ValueError("unsupported identity map schema")
        if not isinstance(document["entries"], list):
            raise ValueError("identity map entries must be an array")
        entries = []
        for row in document["entries"]:
            if not isinstance(row, dict) or set(row) != {
                "logical_type",
                "value",
                "dynamics_person_key",
            }:
                raise ValueError("invalid identity entry fields")
            value = row["value"]
            if row["logical_type"] != "string":
                value = _canonical_integer(value, "identity")
            entries.append(
                IdentityEntry(
                    PersonIdentity(row["logical_type"], value),
                    _canonical_integer(row["dynamics_person_key"], "key"),
                )
            )
        result = cls(tuple(entries))
        if expected_digest is not None and result.digest != expected_digest:
            raise ValueError("identity map digest mismatch")
        if previous is not None:
            result.require_extension_of(previous)
        return result
