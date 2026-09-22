"""Opt-in, exact-identity observations of the existing mortality step.

Records describe simulated removal at a projection step, not death dates or
source admission. Registered engine and assembly behavior remain unchanged.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, replace
from hashlib import sha256
from numbers import Integral
from types import MappingProxyType

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    apply_mortality,
)
from populace_dynamics.person_identity import PersonIdentityMap

_SCHEMA = "populace_dynamics.mortality_step.v1"


def _integer(value: object, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("integer required without coercion")
    value = int(value)
    if not minimum <= value <= 2**63 - 1:
        raise ValueError("integer outside supported range")
    return value


def _parse_integer(value: object) -> int:
    if type(value) is not str:
        raise ValueError("canonical integer string required")
    result = _integer(int(value))
    if str(result) != value:
        raise ValueError("noncanonical integer")
    return result


def _optional_integer(value: object) -> int | None:
    return None if value is None else _parse_integer(value)


def _text(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("nonempty string required")
    value.encode("utf-8")
    return value


def _digest(value: object) -> str:
    if not re.fullmatch("[0-9a-f]{64}", _text(value)):
        raise ValueError("lowercase SHA-256 digest required")
    return value


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MortalityModelSnapshot:
    """Ordered (lower, upper, female hex, male hex) effective model cells."""

    cells: tuple[tuple[int, int, str, str], ...]

    def __post_init__(self) -> None:
        cells = []
        for lower, upper, female, male in self.cells:
            for value in (female, male):
                if type(value) is not str:
                    raise ValueError("probability must be canonical float hex")
                try:
                    number = float.fromhex(value)
                except (ValueError, OverflowError) as exc:
                    raise ValueError("invalid canonical probability") from exc
                if (
                    not math.isfinite(number)
                    or not 0 <= number <= 1
                    or number.hex() != value
                ):
                    raise ValueError("invalid canonical probability")
            cells.append((_integer(lower), _integer(upper), female, male))
        object.__setattr__(self, "cells", tuple(cells))
        self.to_model()  # Validate the existing model's structural contract.

    @classmethod
    def from_model(cls, model: AgeSexMortalityModel) -> MortalityModelSnapshot:
        if type(model) is not AgeSexMortalityModel:
            raise ValueError("the existing AgeSexMortalityModel is required")
        # Validate exact keys too, including mappings mutated after creation.
        detached = AgeSexMortalityModel(
            tuple(model.bands), dict(model.probability)
        )
        cells = []
        for lower, upper in detached.bands:
            label = detached.band_label(lower, upper)
            values = tuple(
                float(detached.probability[(label, sex)]).hex()
                for sex in ("female", "male")
            )
            cells.append((lower, upper, *values))
        return cls(tuple(cells))

    def to_model(self) -> AgeSexMortalityModel:
        """Construct the unchanged evaluator with a detached read-only map."""
        bands, probabilities = [], {}
        for lower, upper, female, male in self.cells:
            bands.append((lower, upper))
            label = AgeSexMortalityModel.band_label(lower, upper)
            probabilities[(label, "female")] = float.fromhex(female)
            probabilities[(label, "male")] = float.fromhex(male)
        return AgeSexMortalityModel(
            tuple(bands), MappingProxyType(probabilities)
        )

    def document(self) -> list[list[str]]:
        return [
            [str(lower), str(upper), female, male]
            for lower, upper, female, male in self.cells
        ]

    @property
    def digest(self) -> str:
        return _hash(_json(self.document()))


@dataclass(frozen=True)
class MortalityObservation:
    """Pre-aging inputs and the actual simulated survival outcome."""

    dynamics_person_key: int
    age: int
    sex: str
    survived: bool
    person_ordinal: int | None = None

    def __post_init__(self) -> None:
        for name in ("dynamics_person_key", "age"):
            object.__setattr__(self, name, _integer(getattr(self, name)))
        if type(self.sex) is not str or self.sex not in ("female", "male"):
            raise ValueError("unsupported mortality sex")
        if type(self.survived) is not bool:
            raise ValueError("survival outcome must be boolean")
        if self.person_ordinal is not None:
            object.__setattr__(
                self, "person_ordinal", _integer(self.person_ordinal)
            )


@dataclass(frozen=True)
class MortalityStepObservation:
    """An immutable step; no death-date, exposure or longitudinal inference."""

    identity_map: PersonIdentityMap
    realization_id: str
    source_contract_digest: str
    model: MortalityModelSnapshot
    target_year: int
    period_index: int
    draw_index: int
    registry_n_periods: int | None
    rows: tuple[MortalityObservation, ...]

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("MortalityStepObservation cannot be subclassed")

    def __post_init__(self) -> None:
        if type(self.identity_map) is not PersonIdentityMap:
            raise ValueError("explicit identity map required")
        _text(self.realization_id)
        _digest(self.source_contract_digest)
        if type(self.model) is not MortalityModelSnapshot:
            raise ValueError("explicit effective model snapshot required")
        for name in ("target_year", "period_index", "draw_index"):
            minimum = 0 if name == "draw_index" else 1
            object.__setattr__(
                self, name, _integer(getattr(self, name), minimum)
            )
        if self.registry_n_periods is not None:
            object.__setattr__(
                self,
                "registry_n_periods",
                _integer(self.registry_n_periods, 1),
            )
            if self.period_index > self.registry_n_periods:
                raise ValueError("period outside registry bounds")
        rows = tuple(self.rows)
        if any(type(row) is not MortalityObservation for row in rows):
            raise ValueError("explicit observation rows required")
        keys = tuple(row.dynamics_person_key for row in rows)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("rows must have sorted unique private keys")
        self.identity_map.reverse_rows(keys)
        ordinals = []
        for row in rows:
            if row.age > self.model.cells[-1][1]:
                raise ValueError("age outside configured mortality bands")
            if (row.person_ordinal is None) != (
                self.registry_n_periods is None
            ):
                raise ValueError("ordinal and RNG mode mismatch")
            if row.person_ordinal is not None:
                ordinals.append(row.person_ordinal)
        if len(set(ordinals)) != len(ordinals):
            raise ValueError("person ordinals must be unique")
        object.__setattr__(self, "rows", rows)

    @property
    def pre_keys(self) -> tuple[int, ...]:
        return tuple(row.dynamics_person_key for row in self.rows)

    @property
    def post_keys(self) -> tuple[int, ...]:
        return tuple(
            row.dynamics_person_key for row in self.rows if row.survived
        )

    def to_json(self) -> str:
        """Canonical JSON binds an external exact identity map by digest."""
        return _json(
            {
                "schema": _SCHEMA,
                "identity_map_digest": self.identity_map.digest,
                "realization_id": self.realization_id,
                "source_contract_digest": self.source_contract_digest,
                "model": self.model.document(),
                "model_digest": self.model.digest,
                "target_year": str(self.target_year),
                "period_index": str(self.period_index),
                "draw_index": str(self.draw_index),
                "registry_n_periods": (
                    None
                    if self.registry_n_periods is None
                    else str(self.registry_n_periods)
                ),
                "rows": [
                    {
                        "dynamics_person_key": str(row.dynamics_person_key),
                        "age": str(row.age),
                        "sex": row.sex,
                        "survived": row.survived,
                        "person_ordinal": (
                            None
                            if row.person_ordinal is None
                            else str(row.person_ordinal)
                        ),
                    }
                    for row in self.rows
                ],
            }
        )

    @property
    def digest(self) -> str:
        return _hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        identity_map: PersonIdentityMap,
        expected_digest: str | None = None,
    ) -> MortalityStepObservation:
        """Load against the caller's trusted map and optional record digest."""

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON field")
                result[key] = value
            return result

        def reject(value):
            raise ValueError(f"invalid JSON constant: {value}")

        document = json.loads(
            text, object_pairs_hook=unique, parse_constant=reject
        )
        if type(identity_map) is not PersonIdentityMap:
            raise ValueError("explicit identity map required")
        if (
            not isinstance(document, dict)
            or document.get("identity_map_digest") != identity_map.digest
        ):
            raise ValueError("identity map digest mismatch")
        try:
            model = MortalityModelSnapshot(
                tuple(
                    (_parse_integer(lo), _parse_integer(hi), female, male)
                    for lo, hi, female, male in document["model"]
                )
            )
            result = cls(
                identity_map,
                document["realization_id"],
                document["source_contract_digest"],
                model,
                *(
                    _parse_integer(document[key])
                    for key in ("target_year", "period_index", "draw_index")
                ),
                _optional_integer(document["registry_n_periods"]),
                tuple(
                    MortalityObservation(
                        _parse_integer(row["dynamics_person_key"]),
                        _parse_integer(row["age"]),
                        row["sex"],
                        row["survived"],
                        _optional_integer(row["person_ordinal"]),
                    )
                    for row in document["rows"]
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("invalid mortality record structure") from exc
        # Also rejects unknown fields, schema/model-digest changes and shapes.
        if result.to_json() != _json(document):
            raise ValueError("noncanonical or inconsistent mortality record")
        if expected_digest is not None and result.digest != _digest(
            expected_digest
        ):
            raise ValueError("mortality record digest mismatch")
        return result


def observe_mortality(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    model: AgeSexMortalityModel,
    identity_map: PersonIdentityMap,
    realization_id: str,
    source_contract_digest: str,
) -> tuple[pd.DataFrame, MortalityStepObservation]:
    """Validate before RNG use, invoke actual mortality once and retain IDs."""
    if type(context) is not PeriodContext or not isinstance(
        rng, np.random.Generator
    ):
        raise ValueError(
            "existing period context and NumPy generator required"
        )
    if not frame.columns.is_unique or not {
        "person_id",
        "age",
        "year",
        "sex",
    }.issubset(frame.columns):
        raise ValueError("unique mortality input columns required")
    for name in ("person_id", "age", "year"):
        if frame[name].dtype != np.dtype("int64"):
            raise ValueError(f"{name} must preserve int64 dtype")
    if not (frame["year"] == _integer(context.year, 1) - 1).all():
        raise ValueError("frame year must immediately precede target year")
    snapshot = MortalityModelSnapshot.from_model(model)
    ordinals, periods = {}, None
    registry = context.rng_registry
    if registry is not None:
        if type(registry) is not ProjectionRNGRegistry:
            raise ValueError("existing RNG registry required")
        periods = _integer(registry.n_periods, 1)
        if _integer(registry.draw_index) != _integer(context.draw_index):
            raise ValueError("context and registry draw mismatch")
        ordinals = {
            _integer(key): _integer(value)
            for key, value in context.person_ordinals.items()
        }
        if len(set(ordinals.values())) != len(ordinals):
            raise ValueError("person ordinals must be unique")
        if not set(frame["person_id"]).issubset(ordinals):
            raise ValueError("missing person RNG ordinal")
    ordered = frame.sort_values("person_id", kind="stable")
    rows = tuple(
        MortalityObservation(key, age, sex, True, ordinals.get(key))
        for key, age, sex in zip(
            ordered["person_id"], ordered["age"], ordered["sex"], strict=True
        )
    )
    # Constructing the provisional record completes validation before drawing.
    record = MortalityStepObservation(
        identity_map,
        realization_id,
        source_contract_digest,
        snapshot,
        context.year,
        context.period_index,
        context.draw_index,
        periods,
        rows,
    )
    survivors = apply_mortality(frame, context, rng, model=snapshot.to_model())
    survivor_keys = set(survivors["person_id"])
    record = replace(
        record,
        rows=tuple(
            replace(row, survived=row.dynamics_person_key in survivor_keys)
            for row in rows
        ),
    )
    return survivors, record
