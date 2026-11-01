"""Context-aware mortality frame step using the engine's mortality streams."""

from __future__ import annotations

from collections.abc import MutableMapping

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionModule

from .model import DifferentialMortality


def apply_differential_mortality(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    model: DifferentialMortality,
    weight_column: str | None,
    death_log: MutableMapping[int, pd.DataFrame] | None = None,
    cell_log: MutableMapping[int, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Draw the engine's uniforms and return survivors in person-ID order.

    As in ``engine.steps.apply_mortality``, uniforms are drawn in stable
    person-ID order before evaluating the mortality model. With a registry,
    each person uses ``ProjectionModule.MORTALITY`` and the injected generator
    is untouched. Logs are mappings indexed by projection year.
    """
    if weight_column != model.weight_column:
        raise ValueError("step weight_column must match model.weight_column")
    if "person_id" not in frame:
        raise ValueError("mortality frame is missing column 'person_id'")
    ordered = frame.sort_values("person_id", kind="stable")
    if context.rng_registry is None:
        uniform = rng.random(len(ordered))
    else:
        uniform = np.asarray(
            [
                context.person_generator(
                    ProjectionModule.MORTALITY, person_id
                ).random()
                for person_id in ordered["person_id"]
            ]
        )
    probability, cells = model.evaluate(ordered, context)
    death = uniform < probability
    year = int(context.year)
    if cell_log is not None:
        cell_log[year] = cells
    if death_log is not None:
        death_log[year] = pd.DataFrame(
            {
                "person_id": ordered["person_id"].to_numpy()[death],
                "sex": ordered["sex"].to_numpy()[death],
                "start_age": ordered["age"].to_numpy()[death],
                "q_applied": probability[death],
            }
        )
    return ordered.loc[~death].reset_index(drop=True)
