"""Expose only OP1 gate requests with a fixed horizon and no target field.

Implement ``docs/design/open_population.md`` §§2.9, 3.1 (OP1) and 5.1,
approved in ruling d1925. Gate requests reject unknown keywords through their
dataclass constructor. Keep future scenario producers outside this closure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import pandas as pd

    from populace_dynamics.engine.entrant_schedule import EntrantSchedule
    from populace_dynamics.engine.loop import (
        PeriodModules,
        SyntheticPersonIdAllocator,
    )
    from populace_dynamics.open_population.exits import EmigrationHazard
    from populace_dynamics.open_population.harness import OpenPopulationResult


# advance_age reads only these economic inputs (engine/steps.py:149–162).
# They supply annual wage levels, rather than reconciliation targets.
GATE_METADATA_KEYS = frozenset({"nawi_by_year", "wage_base_by_year"})


@dataclass(frozen=True, slots=True)
class GateRunRequest:
    """Hold the gate's own fixed horizon, draw index and starting coordinate."""

    horizon: int
    draw_index: int = 0
    start_year: int | None = None

    def __post_init__(self) -> None:
        if type(self.horizon) is not int:
            raise ValueError("gate horizon must be an integer")


def run_gate(
    initial_slice: pd.DataFrame,
    modules: PeriodModules,
    request: GateRunRequest,
    *,
    scheduled_entries: Mapping[int, pd.DataFrame] | None = None,
    schedule_builder: (
        Callable[
            [SyntheticPersonIdAllocator],
            EntrantSchedule | Mapping[int, pd.DataFrame],
        ]
        | None
    ) = None,
    emigration_hazard: EmigrationHazard | None = None,
    reserved_real_ids: Iterable[int] = (),
    metadata: Mapping[str, Any] | None = None,
    rng_streams: Literal["registry", "direct"] = "direct",
) -> OpenPopulationResult:
    """Run the fixed gate horizon through the OP1 accounting harness.

    ``rng_streams="registry"`` is for differential checks; both classes give
    the same projection (design §§2.1, 5.4).
    """
    if type(request) is not GateRunRequest:
        raise TypeError("run_gate requires a GateRunRequest")
    from populace_dynamics.open_population.errors import GateTargetRefused

    gate_metadata = dict(metadata or {})
    unknown = set(gate_metadata) - GATE_METADATA_KEYS
    if unknown:
        raise GateTargetRefused(
            f"gate metadata keys are not allowed: {sorted(unknown, key=str)!r}"
        )
    # Load the numerical runtime only when executing an admitted request.
    # The static import-closure test also inspects this deferred import.
    from populace_dynamics.open_population.harness import _project

    return _project(
        initial_slice,
        modules,
        end_year=request.horizon,
        draw_index=request.draw_index,
        start_year=request.start_year,
        scheduled_entries=scheduled_entries,
        schedule_builder=schedule_builder,
        emigration_hazard=emigration_hazard,
        reserved_real_ids=reserved_real_ids,
        metadata=gate_metadata,
        kind="gate",
        scenario=None,
        rng_streams=rng_streams,
    )
