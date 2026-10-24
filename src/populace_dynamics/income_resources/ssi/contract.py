"""Resolve SSI inputs against the versioned source contract.

Invariants: each inventoried input has a decision for each population;
missing values never inherit an engine default; assumptions require an
explicit opt-in and leave an audit trail; caller-supplied values survive
unchanged after scalar validation; resource balances and counts are
nonnegative, and ages lie in [0, 125]. The runner counts
``ContractRefusal`` at the case boundary.
Source cells describe acquisition routes, not implemented survey readers.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).with_name("input_contract.json")


class ContractRefusal(ValueError):
    """A missing contract input, retained in the runner's denominator."""

    def __init__(
        self, condition: str, inputs: tuple[str, ...], detail: str
    ) -> None:
        self.condition = condition
        self.inputs = inputs
        self.detail = detail
        super().__init__(f"{condition}: {', '.join(inputs)}: {detail}")


@dataclass(frozen=True)
class ResolvedInputs:
    values: dict[str, Any]
    assumptions: tuple[str, ...]


def load_contract(path: Path | None = None) -> dict[str, Any]:
    """Read the committed contract without importing a rules engine."""
    with (path or CONTRACT_PATH).open(encoding="utf-8") as stream:
        return json.load(stream)


def _validate_value(row: Mapping[str, Any], value: Any) -> None:
    """Validate scalars without changing units or coercing their values."""
    value_type = row.get("value_type")
    if value_type is None:
        # Context facts are validated by their typed-record runner guards.
        return
    name = row["name"]
    valid = False
    if value_type == "bool":
        valid = isinstance(value, bool)
    elif value_type == "Enum":
        # A row names its pinned enum's members, read from source by the
        # inventory. A row without them admits no value, so an invalid name
        # refuses its own case here instead of failing inside the engine.
        valid = isinstance(value, str) and value in row.get("enum_members", ())
    elif value_type in ("float", "int"):
        try:
            valid = (
                isinstance(value, Real)
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
        except (TypeError, OverflowError):
            valid = False
        if valid and value_type == "int":
            valid = value >= 0 and value == int(value)
        if valid and name in (
            "bank_account_assets",
            "bond_assets",
            "stock_assets",
        ):
            valid = value >= 0
        if valid and name == "age":
            valid = 0 <= value <= 125
    if not valid:
        raise ContractRefusal(
            "INPUT_CONTRACT_GAP",
            (name,),
            f"Invalid {value_type} input; supply its explicit finite scalar "
            "with nonnegative counts/resources and age in [0, 125]",
        )


def resolve_inputs(
    population: str,
    values: Mapping[str, Any],
    *,
    entity: str = "Person",
    enabled_assumptions: tuple[str, ...] = (),
    input_names: tuple[str, ...] | None = None,
) -> ResolvedInputs:
    """Require explicit values or opted-in registered assumptions.

    Explicit inputs can fill a population's documented acquisition gap;
    their provenance and case applicability remain the runner's concern.
    Context rows describe typed records and are resolved only when the
    caller selects ``entity="Context"``. They are never sent as variables
    to the engine. ``input_names`` narrows resolution for a typed record.
    """
    contract = load_contract()
    aliases = {name.lower(): name for name in contract["populations"]}
    aliases["frame"] = "Microcosm"
    try:
        population_name = aliases[population.lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown starting population: {population}") from exc
    registered = contract["assumptions"]
    unknown = set(enabled_assumptions) - registered.keys()
    if unknown:
        raise ValueError(f"Unregistered assumptions: {sorted(unknown)}")
    rows = [
        row
        for row in contract["rows"]
        if row["entity"].lower() == entity.lower()
    ]
    if input_names is not None:
        wanted = set(input_names)
        rows = [row for row in rows if row["name"] in wanted]
        unknown_names = wanted - {row["name"] for row in rows}
        if unknown_names:
            raise ValueError(
                f"Unknown contract inputs: {sorted(unknown_names)}"
            )
    unknown_values = set(values) - {row["name"] for row in rows}
    if unknown_values:
        raise ContractRefusal(
            "INPUT_CONTRACT_GAP",
            tuple(sorted(unknown_values)),
            "Uncontracted inputs cannot be passed through or silently dropped",
        )
    resolved: dict[str, Any] = {}
    applied: set[str] = set()
    missing: list[str] = []
    conditions: list[str] = []
    for row in rows:
        name = row["name"]
        if name in values and values[name] is not None:
            _validate_value(row, values[name])
            resolved[name] = values[name]
            continue
        cell = row["populations"][population_name]
        assumption = cell.get("assumption_id")
        if cell["status"] == "assumption" and assumption in (
            enabled_assumptions
        ):
            _validate_value(row, registered[assumption]["value"])
            resolved[name] = registered[assumption]["value"]
            applied.add(assumption)
            continue
        missing.append(name)
        conditions.append(cell.get("condition", "INPUT_CONTRACT_GAP"))
    if missing:
        # One attempted case produces one refusal; all missing names remain
        # available for its diagnostic record rather than disappearing.
        priority = (
            "FRAME_LACKS_RESOURCES",
            "RULES_ENGINE_GAP",
            "INPUT_CONTRACT_GAP",
        )
        condition = next(item for item in priority if item in conditions)
        raise ContractRefusal(
            condition,
            tuple(missing),
            "Supply validated inputs or enable their registered assumptions",
        )
    return ResolvedInputs(resolved, tuple(sorted(applied)))
