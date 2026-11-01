"""Wrap OP1 mortality with survivor-only emigration and explicit exits.

Implement ``docs/design/open_population.md`` §§3.1 (OP1), 5.4, 6.4 and 7,
approved in ruling d1925. The sealed loop calls mortality before marital
state (``engine/loop.py:297–315``). The wrapper passes its mortality call
through unchanged and uses the tagged person stream pattern read at
``baselines/fertility.py:118–123`` only after that call returns.

Track A infers widowhood from a linked spouse's absence
(``cola_track_a/adapters.py:104–117``), so any non-null emigration hazard
requires the explicit no-relational adapter below. OP4 supplies relational
updates; an arbitrary adapter's compatibility cannot be inferred here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.loop import (
    FrameStep,
    MaritalStep,
    MaritalStepResult,
    PeriodContext,
)
from populace_dynamics.engine.rng import ProjectionModule
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    EmigrationMaritalIncompatibility,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.events import EventLedger
from populace_dynamics.open_population.streams import DirectRNGStreams

EmigrationHazard = Callable[
    [pd.DataFrame, PeriodContext], Sequence[float] | np.ndarray
]
EMIGRATION_STREAM_TAG = 0x4F5045


def no_marital_transitions(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
) -> MaritalStepResult:
    """Return empty marital updates without inspecting absent spouses."""
    del context, rng
    return MaritalStepResult(
        sim_years=frame.iloc[0:0].copy(),
        births=pd.DataFrame(
            {
                "parent_person_id": pd.Series(dtype="int64"),
                "birth_year": pd.Series(dtype="int64"),
            }
        ),
    )


def require_emigration_compatible(
    marital_core: MaritalStep, hazard: EmigrationHazard | None
) -> None:
    """Refuse non-null hazards with unverified relational adapters."""
    if hazard is not None and marital_core is not no_marital_transitions:
        raise EmigrationMaritalIncompatibility(
            "non-null emigration requires no_marital_transitions until OP4 "
            "supplies exit-aware relational updates; Track A detects "
            "widowhood from spouse absence "
            "(cola_track_a/adapters.py:104–117)"
        )


@dataclass(frozen=True)
class _ExitAdapter:
    """Declare deaths and survivor exits inside the OP1 harness (§5.4).

    Only ``harness._project`` constructs this harness-only adapter, after
    ``require_emigration_compatible`` checks the marital slot. Direct use
    does not establish relational compatibility (design §§5.4 and 7).
    """

    step: FrameStep
    ledger: EventLedger
    hazard: EmigrationHazard | None = None

    def __call__(
        self,
        frame: pd.DataFrame,
        context: PeriodContext,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        """Pass mortality its original arguments before drawing emigration."""
        opening = frame.copy(deep=True)
        survivors = self.step(frame, context, rng)
        if not isinstance(survivors, pd.DataFrame):
            raise AccountingIdentityError("mortality returned no roster frame")
        required = {"person_id", "weight"}
        if not required.issubset(survivors.columns):
            raise AccountingIdentityError(
                "mortality survivors lack person_id or weight"
            )
        if survivors["person_id"].duplicated().any() or not set(
            survivors["person_id"]
        ).issubset(set(opening["person_id"])):
            raise AccountingIdentityError(
                "mortality must return unique IDs drawn from its input"
            )
        expected_weights = survivors["person_id"].map(
            opening.set_index("person_id")["weight"]
        )
        if not (
            survivors["weight"]
            .reset_index(drop=True)
            .eq(expected_weights.reset_index(drop=True))
            .fillna(False)
            .all()
        ):
            raise AccountingIdentityError(
                "mortality changed a survivor's weight"
            )
        deaths = opening.loc[
            ~opening["person_id"].isin(survivors["person_id"])
        ]
        self.ledger.record(
            deaths, year=context.year, kind=PopulationEventKind.DEATH
        )
        if self.hazard is None or survivors.empty:
            return survivors

        probabilities = np.asarray(
            self.hazard(survivors.copy(deep=True), context), dtype=np.float64
        )
        if probabilities.shape != (len(survivors),):
            raise ValueError(
                "emigration hazard needs one probability per survivor"
            )
        if (
            not np.isfinite(probabilities).all()
            or ((probabilities < 0) | (probabilities > 1)).any()
        ):
            raise ValueError("emigration probabilities must lie in [0, 1]")
        if context.rng_registry is None:
            raise IdOrStreamCollision(
                "emigration needs the projection's person-keyed RNG registry"
            )
        streams = DirectRNGStreams(
            context.rng_registry.draw_index,
            context.rng_registry.n_periods,
        )
        try:
            uniforms = np.asarray(
                [
                    streams.tagged_child_generator(
                        context.period_index,
                        ProjectionModule.MORTALITY,
                        EMIGRATION_STREAM_TAG,
                        context.person_ordinals[person_id],
                    ).random()
                    for person_id in survivors["person_id"]
                ],
                dtype=np.float64,
            )
        except KeyError as error:
            raise IdOrStreamCollision(
                "emigration survivor has no projection RNG ordinal"
            ) from error
        emigration = uniforms < probabilities
        self.ledger.record(
            survivors.loc[emigration],
            year=context.year,
            kind=PopulationEventKind.EMIGRATION,
        )
        return survivors.loc[~emigration].copy()
