"""Expose only OP1 gate requests with a fixed horizon and no target field.

Implement ``docs/design/open_population.md`` §§2.9, 3.1 (OP1) and 5.1,
approved in ruling d1925. Gate requests reject unknown keywords through their
dataclass constructor. Keep future scenario producers outside this closure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from populace_dynamics.engine.loop import PeriodModules
    from populace_dynamics.open_population.harness import OpenPopulationResult


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
    **kwargs: Any,
) -> OpenPopulationResult:
    """Run the fixed gate horizon through the OP1 accounting harness."""
    if type(request) is not GateRunRequest:
        raise TypeError("run_gate requires a GateRunRequest")
    # Load the numerical runtime only when executing an admitted request.
    # The static import-closure test also inspects this deferred import.
    from populace_dynamics.open_population.harness import _project

    return _project(
        initial_slice,
        modules,
        end_year=request.horizon,
        draw_index=request.draw_index,
        start_year=request.start_year,
        **kwargs,
    )
