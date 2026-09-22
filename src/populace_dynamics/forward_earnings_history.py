"""Record annual outputs of the existing 2014–22 forward earnings law.

This opt-in observer does not invoke or change a generator. It records one
realization on a fixed roster, preserves binary64 values, and never treats
labor income as covered earnings. Source digests establish identity, not
empirical admission, legal authority, or acceptance of the PSID crosswalk.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from numbers import Integral

import numpy as np
import pandas as pd

from .person_identity import PersonIdentity, PersonIdentityMap

_SCHEMA = "populace_dynamics.forward_earnings_history.v1"
_FIRST_YEAR = 2014
_LAST_YEAR = 2022
_COVERAGE = "not_materialized"
_REGISTRY = "registration_required"


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be valid UTF-8") from exc
    return value


def _digest(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{label} must be an integer without coercion")
    return int(value)


def _canonical_integer(value: object, label: str) -> int:
    if type(value) is not str:
        raise ValueError(f"{label} must be a canonical integer string")
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be a canonical integer string"
        ) from exc
    if str(result) != value:
        raise ValueError(f"{label} must be a canonical integer string")
    return result


@dataclass(frozen=True)
class ForwardEarningsObservation:
    """One realized annual labor amount, or an explicit unsupported record."""

    dynamics_person_key: int
    year: int
    amount_hex: str | None
    earnings_domain: bool
    lineage_digest: str

    def __post_init__(self) -> None:
        key = _integer(self.dynamics_person_key, "person key")
        year = _integer(self.year, "reference year")
        if not 0 <= key < 2**63:
            raise ValueError("person key must be nonnegative int64")
        if not _FIRST_YEAR <= year <= _LAST_YEAR:
            raise ValueError("reference year must be within 2014–2022")
        if type(self.earnings_domain) is not bool:
            raise ValueError("earnings domain must be an explicit bool")
        _digest(self.lineage_digest, "lineage digest")
        if not self.earnings_domain:
            if self.amount_hex is not None:
                raise ValueError("outside-domain amount must be unavailable")
        else:
            if type(self.amount_hex) is not str:
                raise ValueError("supported amount needs binary64 hex")
            try:
                amount = float.fromhex(self.amount_hex)
            except (ValueError, OverflowError) as exc:
                raise ValueError("invalid binary64 amount") from exc
            if (
                not math.isfinite(amount)
                or amount < 0
                or amount.hex() != self.amount_hex
            ):
                raise ValueError(
                    "amount must be canonical nonnegative binary64"
                )
        object.__setattr__(self, "dynamics_person_key", key)
        object.__setattr__(self, "year", year)

    @property
    def amount_state(self) -> str:
        if self.amount_hex is None:
            return "unavailable"
        return (
            "known_zero"
            if float.fromhex(self.amount_hex) == 0
            else "known_amount"
        )

    @property
    def missing_reason(self) -> str | None:
        return (
            None if self.earnings_domain else "outside_forward_earnings_domain"
        )

    @property
    def generation_method(self) -> str:
        if not self.earnings_domain:
            return "not_materialized"
        if self.year == _FIRST_YEAR:
            return "boundary_method"
        return "odd_year_carry" if self.year % 2 else "biennial_draw"


def _snapshot(
    mapping: PersonIdentityMap, frame: pd.DataFrame, lineage_digest: str
) -> tuple[ForwardEarningsObservation, ...]:
    if type(mapping) is not PersonIdentityMap:
        raise ValueError("explicit PersonIdentityMap required")
    _digest(lineage_digest, "lineage digest")
    if not isinstance(frame, pd.DataFrame) or not frame.columns.is_unique:
        raise ValueError("frame requires unique columns")
    required = ("person_id", "year", "earnings", "earnings_domain")
    if not set(required).issubset(frame.columns) or frame.empty:
        raise ValueError(
            "nonempty frame requires identity/year/earnings/domain"
        )
    for name in ("person_id", "year"):
        if frame[name].dtype != np.dtype("int64"):
            raise ValueError(
                f"{name} must be int64, without implicit conversion"
            )
    if frame["earnings"].dtype != np.dtype("float64"):
        raise ValueError(
            "earnings must preserve the generator's float64 dtype"
        )
    if frame["earnings_domain"].dtype != np.dtype("bool"):
        raise ValueError(
            "earnings_domain must be bool, with no missing values"
        )
    if frame["person_id"].duplicated().any():
        raise ValueError("duplicate person in annual frame")
    if frame["year"].nunique() != 1:
        raise ValueError("annual frame must have exactly one reference year")
    keys = frame["person_id"].tolist()
    mapping.reverse_rows(keys)  # Check private keys without float conversion.
    rows = []
    for key, year, amount, domain in frame[list(required)].itertuples(
        index=False, name=None
    ):
        if not domain and amount != 0:
            raise ValueError("outside-domain output must be its control zero")
        rows.append(
            ForwardEarningsObservation(
                key,
                year,
                float(amount).hex() if domain else None,
                bool(domain),
                lineage_digest,
            )
        )
    return tuple(sorted(rows, key=lambda row: row.dynamics_person_key))


@dataclass(frozen=True)
class ForwardEarningsHistory:
    """Dense append-only 2014–22 snapshot history for one fixed-roster draw.

    A history may cover a subset of an identity map, but its roster and domain
    cannot change during append. Death, entrant and domain-transition records
    need a separately defined extension. Historical years before 2014 and
    coverage classification are deliberately absent from this version.
    """

    identity_map: PersonIdentityMap
    realization_id: str
    generator_digest: str
    source_contract_digest: str
    unit: str
    price_basis: str
    roster_keys: tuple[int, ...]
    last_year: int
    observations: tuple[ForwardEarningsObservation, ...]

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("ForwardEarningsHistory cannot be subclassed")

    def __post_init__(self) -> None:
        if type(self.identity_map) is not PersonIdentityMap:
            raise ValueError("explicit PersonIdentityMap required")
        _text(self.realization_id, "realization ID")
        _text(self.unit, "unit")
        if self.price_basis != "nominal" or type(self.price_basis) is not str:
            raise ValueError("forward earnings require explicit nominal basis")
        _digest(self.generator_digest, "generator digest")
        _digest(self.source_contract_digest, "source contract digest")
        roster = tuple(_integer(key, "roster key") for key in self.roster_keys)
        if not roster or len(set(roster)) != len(roster):
            raise ValueError("declared roster must be nonempty and unique")
        self.identity_map.reverse_rows(roster)
        roster = tuple(sorted(roster))
        last_year = _integer(self.last_year, "last reference year")
        if not _FIRST_YEAR <= last_year <= _LAST_YEAR:
            raise ValueError("last reference year must be within 2014–2022")
        rows = tuple(self.observations)
        if not rows or any(
            type(r) is not ForwardEarningsObservation for r in rows
        ):
            raise ValueError("nonempty typed observations required")
        rows = tuple(
            sorted(rows, key=lambda r: (r.year, r.dynamics_person_key))
        )
        self.identity_map.reverse_rows(r.dynamics_person_key for r in rows)
        by_year: dict[int, dict[int, ForwardEarningsObservation]] = {}
        for row in rows:
            annual = by_year.setdefault(row.year, {})
            if row.dynamics_person_key in annual:
                raise ValueError("duplicate person/year observation")
            annual[row.dynamics_person_key] = row
        years = sorted(by_year)
        if years != list(range(_FIRST_YEAR, last_year + 1)):
            raise ValueError("history must contain dense years beginning 2014")
        initial = by_year[_FIRST_YEAR]
        if tuple(sorted(initial)) != roster:
            raise ValueError("observations must cover the declared roster")
        previous = initial
        for year in years:
            annual = by_year[year]
            if annual.keys() != initial.keys():
                raise ValueError("fixed roster must be complete in every year")
            if len({row.lineage_digest for row in annual.values()}) != 1:
                raise ValueError(
                    "annual snapshot must have one lineage digest"
                )
            for key, row in annual.items():
                if row.earnings_domain != initial[key].earnings_domain:
                    raise ValueError("fixed earnings domain cannot change")
                if year % 2 and row.amount_hex != previous[key].amount_hex:
                    raise ValueError(
                        "odd-year carry must preserve exact source bits"
                    )
            previous = annual
        object.__setattr__(self, "observations", rows)
        object.__setattr__(self, "roster_keys", roster)
        object.__setattr__(self, "last_year", last_year)

    @property
    def source_registry_status(self) -> str:
        return _REGISTRY

    @property
    def coverage_status(self) -> str:
        return _COVERAGE

    @classmethod
    def start(
        cls,
        identity_map: PersonIdentityMap,
        frame: pd.DataFrame,
        *,
        realization_id: str,
        generator_digest: str,
        source_contract_digest: str,
        unit: str,
        price_basis: str,
        lineage_digest: str,
    ) -> ForwardEarningsHistory:
        """Snapshot an already materialized 2014 frame without changing it."""
        rows = _snapshot(identity_map, frame, lineage_digest)
        return cls(
            identity_map,
            realization_id,
            generator_digest,
            source_contract_digest,
            unit,
            price_basis,
            tuple(row.dynamics_person_key for row in rows),
            _FIRST_YEAR,
            rows,
        )

    def append(
        self, frame: pd.DataFrame, *, lineage_digest: str
    ) -> ForwardEarningsHistory:
        """Return a new history containing exactly the following year's rows."""
        if self.last_year == _LAST_YEAR:
            raise ValueError("2014–2022 contract cannot extend beyond 2022")
        rows = _snapshot(self.identity_map, frame, lineage_digest)
        if rows[0].year != self.last_year + 1:
            raise ValueError("append requires exactly the next reference year")
        return type(self)(
            self.identity_map,
            self.realization_id,
            self.generator_digest,
            self.source_contract_digest,
            self.unit,
            self.price_basis,
            self.roster_keys,
            self.last_year + 1,
            self.observations + rows,
        )

    def for_person(
        self, identity: PersonIdentity
    ) -> tuple[ForwardEarningsObservation, ...]:
        """Look up source IDs exactly, independently of private key ordering."""
        key = self.identity_map.map_rows([identity])[0]
        result = tuple(
            r for r in self.observations if r.dynamics_person_key == key
        )
        if not result:
            raise ValueError("person is not in this history's fixed roster")
        return result

    def require_extension_of(self, previous: ForwardEarningsHistory) -> None:
        """Reject a loaded successor that changes provenance or any old row."""
        if type(previous) is not ForwardEarningsHistory:
            raise ValueError("previous history must be ForwardEarningsHistory")
        metadata = (
            "identity_map",
            "realization_id",
            "generator_digest",
            "source_contract_digest",
            "unit",
            "price_basis",
            "roster_keys",
        )
        if any(getattr(self, k) != getattr(previous, k) for k in metadata):
            raise ValueError(
                "history extension changed identity or provenance"
            )
        if (
            self.observations[: len(previous.observations)]
            != previous.observations
        ):
            raise ValueError("history extension changed or removed prior rows")

    def to_json(self) -> str:
        """Serialize without JSON floating-point numbers or numeric ID loss."""
        document = {
            "schema": _SCHEMA,
            "identity_map": json.loads(self.identity_map.to_json()),
            "identity_map_digest": self.identity_map.digest,
            "realization_id": self.realization_id,
            "generator_digest": self.generator_digest,
            "source_contract_digest": self.source_contract_digest,
            "unit": self.unit,
            "price_basis": self.price_basis,
            "calendar": "calendar_year",
            "roster_keys": [str(key) for key in self.roster_keys],
            "last_year": str(self.last_year),
            "source_registry_status": _REGISTRY,
            "coverage_status": _COVERAGE,
            "observations": [
                {
                    "dynamics_person_key": str(r.dynamics_person_key),
                    "year": str(r.year),
                    "amount_hex": r.amount_hex,
                    "earnings_domain": r.earnings_domain,
                    "lineage_digest": r.lineage_digest,
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
        expected_digest: str | None = None,
        previous: ForwardEarningsHistory | None = None,
    ) -> ForwardEarningsHistory:
        """Load and revalidate every annual row and the embedded identity map."""

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON member")
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError(f"nonfinite JSON constant: {value}")

        document = json.loads(
            text, object_pairs_hook=unique, parse_constant=reject_constant
        )
        fields = {
            "schema",
            "identity_map",
            "identity_map_digest",
            "realization_id",
            "generator_digest",
            "source_contract_digest",
            "unit",
            "price_basis",
            "calendar",
            "source_registry_status",
            "coverage_status",
            "observations",
            "roster_keys",
            "last_year",
        }
        if not isinstance(document, Mapping) or set(document) != fields:
            raise ValueError("invalid history document fields")
        constants = {
            "schema": _SCHEMA,
            "calendar": "calendar_year",
            "coverage_status": _COVERAGE,
            "source_registry_status": _REGISTRY,
        }
        if any(document[k] != value for k, value in constants.items()):
            raise ValueError("unsupported history scope or status")
        _digest(document["identity_map_digest"], "identity map digest")
        mapping = PersonIdentityMap.from_json(
            json.dumps(document["identity_map"]),
            expected_digest=document["identity_map_digest"],
        )
        if type(document["observations"]) is not list:
            raise ValueError("observations must be an array")
        if type(document["roster_keys"]) is not list:
            raise ValueError("roster keys must be an array")
        rows = []
        row_fields = {
            "dynamics_person_key",
            "year",
            "amount_hex",
            "earnings_domain",
            "lineage_digest",
        }
        for row in document["observations"]:
            if type(row) is not dict or set(row) != row_fields:
                raise ValueError("invalid observation fields")
            rows.append(
                ForwardEarningsObservation(
                    _canonical_integer(
                        row["dynamics_person_key"], "person key"
                    ),
                    _canonical_integer(row["year"], "reference year"),
                    row["amount_hex"],
                    row["earnings_domain"],
                    row["lineage_digest"],
                )
            )
        result = cls(
            mapping,
            document["realization_id"],
            document["generator_digest"],
            document["source_contract_digest"],
            document["unit"],
            document["price_basis"],
            tuple(
                _canonical_integer(key, "roster key")
                for key in document["roster_keys"]
            ),
            _canonical_integer(document["last_year"], "last reference year"),
            tuple(rows),
        )
        if expected_digest is not None:
            _digest(expected_digest, "expected digest")
            if result.digest != expected_digest:
                raise ValueError(
                    "history digest does not match expected digest"
                )
        if previous is not None:
            result.require_extension_of(previous)
        return result
