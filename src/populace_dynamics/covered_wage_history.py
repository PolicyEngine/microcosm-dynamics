"""Attach explicit covered-wage source observations to a labor history.

This opt-in sidecar records declarations, not statutory coverage decisions.
It never infers wages from labor income, imputes missing values, or computes
creditable earnings. Source digests identify caller-retained receipts; their
contents and admission are not verified here.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from numbers import Integral

from .forward_earnings_history import ForwardEarningsHistory
from .person_identity import PersonIdentity

_SCHEMA = "populace_dynamics.covered_wage_history.v1"
_CONCEPT = "source_reported_uncapped_employee_wages_covered"
_MISSING = frozenset(
    {
        "source_field_unavailable",
        "coverage_unresolved",
        "crosswalk_registration_required",
    }
)


def _digest(value: object) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("source digest must be lowercase SHA-256")


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("coordinate must be an integer without coercion")
    return int(value)


def _load_integer(value: object) -> int:
    if type(value) is not str or re.fullmatch(r"0|[1-9][0-9]*", value) is None:
        raise ValueError("coordinate must be a canonical integer string")
    return int(value)


def _fields(document: object, expected: set[str]) -> None:
    if type(document) is not dict or set(document) != expected:
        raise ValueError("invalid document fields")


@dataclass(frozen=True)
class SourceAmount:
    """Nonnegative amount retaining its source dtype and exact serialization."""

    logical_dtype: str
    serialization: str

    def __post_init__(self) -> None:
        kind, value = self.logical_dtype, self.serialization
        if type(kind) is not str or type(value) is not str:
            raise ValueError(
                "explicit dtype and source serialization required"
            )
        if kind in ("int64", "uint64"):
            amount = _load_integer(value)
            if amount >= 2 ** (63 if kind == "int64" else 64):
                raise ValueError("amount exceeds source integer dtype")
        elif kind == "decimal":
            if (
                re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value)
                is None
            ):
                raise ValueError("decimal must retain plain source text")
            if Decimal(value) < 0:
                raise ValueError("covered wages cannot be negative")
        elif kind == "binary64":
            try:
                amount = float.fromhex(value)
            except (ValueError, OverflowError) as exc:
                raise ValueError("invalid binary64 source amount") from exc
            if (
                not math.isfinite(amount)
                or amount < 0
                or amount.hex() != value
            ):
                raise ValueError(
                    "binary64 must be canonical, finite and nonnegative"
                )
        else:
            raise ValueError("unsupported source amount dtype")

    @property
    def is_zero(self) -> bool:
        if self.logical_dtype == "binary64":
            return float.fromhex(self.serialization) == 0
        return Decimal(self.serialization) == 0


@dataclass(frozen=True)
class CoveredWageObservation:
    """Explicit source amount or unavailability for one private person/year."""

    dynamics_person_key: int
    year: int
    amount: SourceAmount | None
    missing_reason: str | None
    source_digest: str

    def __post_init__(self) -> None:
        key, year = _integer(self.dynamics_person_key), _integer(self.year)
        if not 0 <= key < 2**63 or not 2014 <= year <= 2022:
            raise ValueError("coordinate outside forward-history scope")
        _digest(self.source_digest)
        if self.amount is None:
            if (
                type(self.missing_reason) is not str
                or self.missing_reason not in _MISSING
            ):
                raise ValueError(
                    "unavailable amount needs an explicit missing reason"
                )
        elif (
            type(self.amount) is not SourceAmount
            or self.missing_reason is not None
        ):
            raise ValueError("typed source amount requires no missing reason")
        object.__setattr__(self, "dynamics_person_key", key)
        object.__setattr__(self, "year", year)

    @property
    def amount_state(self) -> str:
        if self.amount is None:
            return "unavailable"
        return "known_zero" if self.amount.is_zero else "known_amount"


@dataclass(frozen=True)
class CoveredWageHistory:
    """Dense source observations bound to one exact forward history.

    The source contract must declare uncapped covered employee wages in the
    history's nominal unit. Each source receipt must bind the artifact,
    record/field locator, original value/dtype, reference year, unit and
    information date. This class validates representation, not those claims.
    """

    history: ForwardEarningsHistory
    source_contract_digest: str
    observations: tuple[CoveredWageObservation, ...]

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("CoveredWageHistory cannot be subclassed")

    def __post_init__(self) -> None:
        if type(self.history) is not ForwardEarningsHistory:
            raise ValueError("explicit forward history required")
        _digest(self.source_contract_digest)
        rows = tuple(self.observations)
        if any(type(row) is not CoveredWageObservation for row in rows):
            raise ValueError("typed covered-wage observations required")
        coordinates = [(r.year, r.dynamics_person_key) for r in rows]
        required = {
            (r.year, r.dynamics_person_key) for r in self.history.observations
        }
        if len(coordinates) != len(required) or set(coordinates) != required:
            raise ValueError(
                "observations must cover the exact history envelope once"
            )
        object.__setattr__(
            self,
            "observations",
            tuple(sorted(rows, key=lambda r: (r.year, r.dynamics_person_key))),
        )

    def for_person(
        self, identity: PersonIdentity
    ) -> tuple[CoveredWageObservation, ...]:
        """Select exact source identities without inferring identity from order."""
        key = self.history.identity_map.map_rows([identity])[0]
        rows = tuple(
            r for r in self.observations if r.dynamics_person_key == key
        )
        if not rows:
            raise ValueError("person is outside the history roster")
        return rows

    @property
    def missing_coordinates(self) -> tuple[tuple[int, int], ...]:
        """Return (private key, year) for explicit unavailable observations."""
        return tuple(
            (r.dynamics_person_key, r.year)
            for r in self.observations
            if r.amount is None
        )

    def _metadata(self) -> dict[str, str]:
        return {
            "schema": _SCHEMA,
            "concept": _CONCEPT,
            "history_digest": self.history.digest,
            "identity_map_digest": self.history.identity_map.digest,
            "realization_id": self.history.realization_id,
            "unit": self.history.unit,
            "price_basis": self.history.price_basis,
        }

    def to_json(self) -> str:
        """Serialize source strings without monetary or identity conversion."""
        document = {
            **self._metadata(),
            "source_contract_digest": self.source_contract_digest,
            "observations": [
                {
                    "dynamics_person_key": str(r.dynamics_person_key),
                    "year": str(r.year),
                    "amount": (
                        None
                        if r.amount is None
                        else {
                            "logical_dtype": r.amount.logical_dtype,
                            "serialization": r.amount.serialization,
                        }
                    ),
                    "missing_reason": r.missing_reason,
                    "source_digest": r.source_digest,
                }
                for r in self.observations
            ],
        }
        return json.dumps(
            document,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

    @property
    def digest(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        history: ForwardEarningsHistory,
        expected_digest: str | None = None,
    ) -> CoveredWageHistory:
        """Load only against the bound history; never fill missing rows."""

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON member")
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError(f"nonfinite JSON constant: {value}")

        if type(history) is not ForwardEarningsHistory:
            raise ValueError("explicit forward history required")
        document = json.loads(
            text, object_pairs_hook=unique, parse_constant=reject_constant
        )
        metadata = {
            "schema": _SCHEMA,
            "concept": _CONCEPT,
            "history_digest": history.digest,
            "identity_map_digest": history.identity_map.digest,
            "realization_id": history.realization_id,
            "unit": history.unit,
            "price_basis": history.price_basis,
        }
        _fields(
            document,
            set(metadata) | {"source_contract_digest", "observations"},
        )
        if any(
            type(document[k]) is not str or document[k] != v
            for k, v in metadata.items()
        ):
            raise ValueError(
                "document does not bind the supplied history and scope"
            )
        if type(document["observations"]) is not list:
            raise ValueError("observations must be an array")
        rows = []
        for row in document["observations"]:
            _fields(
                row,
                {
                    "dynamics_person_key",
                    "year",
                    "amount",
                    "missing_reason",
                    "source_digest",
                },
            )
            amount = row["amount"]
            if amount is not None:
                _fields(amount, {"logical_dtype", "serialization"})
                amount = SourceAmount(**amount)
            rows.append(
                CoveredWageObservation(
                    _load_integer(row["dynamics_person_key"]),
                    _load_integer(row["year"]),
                    amount,
                    row["missing_reason"],
                    row["source_digest"],
                )
            )
        result = cls(history, document["source_contract_digest"], tuple(rows))
        if expected_digest is not None:
            _digest(expected_digest)
            if result.digest != expected_digest:
                raise ValueError(
                    "covered-wage digest differs from expected digest"
                )
        return result
