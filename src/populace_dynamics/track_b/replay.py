"""Copied candidate-3 earnings loop retaining annual fixed-roster history.

The scored path is copied from ``harness.m6_projection`` at 9cee2423f048.
Snapshots are detached before they leave the loop. No mortality, entrants,
identity remapping, fitted-state change, or change to RNG addresses is added.
This adapter supplies reproduction evidence only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from populace_dynamics.engine.earnings_domain import wrap_earnings_domain
from populace_dynamics.engine.forward_earnings import SUBSTREAM_CODES
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import (
    MODULE_ORDER,
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import apply_earnings
from populace_dynamics.harness.m6_cells import GATED_EARN_YEARS
from populace_dynamics.harness.m6_scoring import (
    restrict_earnings_domain_support,
)

REPLAY_START_YEAR = 2014
REPLAY_END_YEAR = 2018
# Candidate 3 uses the full 2014--2022 registry even on this shorter surface.
RNG_N_PERIODS = 8


@dataclass(frozen=True)
class AnnualEarningsReplay:
    """Detached annual state, unchanged scored rows, and RNG coordinates."""

    history: pd.DataFrame
    scored: pd.DataFrame
    rng_signature: dict[str, object]


def _rng_signature(
    registry: ProjectionRNGRegistry,
    ordinals: Mapping[object, int],
) -> dict[str, object]:
    periods = []
    for period in range(1, REPLAY_END_YEAR - REPLAY_START_YEAR + 1):
        sequence = registry.seed_sequence(period, ProjectionModule.EARNINGS)
        periods.append(
            {
                "period_index": period,
                "year": REPLAY_START_YEAR + period,
                "entropy": list(sequence.entropy),
                "spawn_key": list(sequence.spawn_key),
                "pool_size": sequence.pool_size,
            }
        )
    return {
        "draw_index": registry.draw_index,
        "draw_seed": registry.draw_seed,
        "n_periods": registry.n_periods,
        "module": ProjectionModule.EARNINGS.value,
        "module_order": [module.value for module in MODULE_ORDER],
        "person_ordinals": [
            {
                "person_id": (
                    person_id.item()
                    if isinstance(person_id, np.generic)
                    else person_id
                ),
                "ordinal": ordinal,
            }
            for person_id, ordinal in ordinals.items()
        ],
        "periods": periods,
        "person_spawn_key": (
            "module_seed_sequence.spawn_key + (person_ordinal,)"
        ),
        "bit_generator": type(
            registry.generator(0, ProjectionModule.EARNINGS).bit_generator
        ).__name__,
        "earnings_seed_bridge": (
            "person_rng.integers(0, uint64.max, dtype=uint64)"
        ),
        "earnings_substream_entropy": "[earnings_seed, substream_code]",
        "earnings_substream_codes": dict(SUBSTREAM_CODES),
    }


def earnings_rng_signature(
    *, all_person_ids: Iterable[object], draw_index: int
) -> dict[str, object]:
    """Describe the candidate-3 addresses without consuming any draw."""
    ordinals = {
        person_id: index
        for index, person_id in enumerate(sorted(set(all_person_ids)))
    }
    return _rng_signature(
        ProjectionRNGRegistry(int(draw_index), RNG_N_PERIODS), ordinals
    )


def _earnings_state_frame(initial_slice: pd.DataFrame) -> pd.DataFrame:
    required = {"person_id", "year", "age", "sex", "earnings_domain"}
    missing = required - set(initial_slice)
    if missing:
        raise ValueError(
            f"earnings initial slice is missing columns {sorted(missing)}"
        )
    # Copy the incumbent's leakage fence, including exclusion of realized NAWI.
    return initial_slice[
        ["person_id", "year", "age", "sex", "earnings_domain"]
    ].copy()


def replay_earnings_on_realized_support(
    *,
    initial_slice: pd.DataFrame,
    truth_support: pd.DataFrame,
    generator: object,
    domain_person_ids: Iterable[object],
    all_person_ids: Iterable[object],
    draw_index: int,
) -> AnnualEarningsReplay:
    """Replay original scored earnings and keep all five annual snapshots.

    The fixed roster is the original earnings domain. Realized presence and
    F6 weights restrict only ``scored`` after generation; annual ``history``
    retains every in-domain person even when absent from scored support.
    """
    domain = frozenset(domain_person_ids)
    state = _earnings_state_frame(initial_slice)
    state = state[state["person_id"].isin(domain)].copy()
    if set(state["person_id"]) != set(domain):
        missing = sorted(set(domain) - set(state["person_id"]))[:10]
        raise ValueError(
            f"earnings domain is not present at the 2014 anchor: {missing}"
        )
    model = wrap_earnings_domain(generator)
    materialize = getattr(model, "materialize_initial_frame", None)
    if materialize is None:
        raise TypeError("scored earnings generator has no initializer")
    state = materialize(state)

    all_ids = sorted(set(all_person_ids))
    ordinals = {person_id: index for index, person_id in enumerate(all_ids)}
    if not set(domain).issubset(ordinals):
        raise ValueError("earnings domain lies outside the RNG population")
    registry = ProjectionRNGRegistry(
        draw_index=int(draw_index), n_periods=RNG_N_PERIODS
    )
    history = [state.copy().assign(period=2014)]
    rows = [
        state[["person_id", "earnings"]]
        .assign(period=2014)
        .loc[:, ["person_id", "period", "earnings"]]
    ]
    for period_index, year in enumerate(range(2015, 2019), start=1):
        state = state.copy()
        state["age"] = state["age"].to_numpy(dtype=np.int64) + 1
        state["year"] = year
        context = PeriodContext(
            period_index=period_index,
            year=year,
            draw_index=int(draw_index),
            metadata={},
            rng_registry=registry,
            person_ordinals=ordinals,
        )
        state = apply_earnings(
            state,
            context,
            registry.generator(period_index, ProjectionModule.EARNINGS),
            model=model,
        )
        history.append(state.copy().assign(period=year))
        if year in GATED_EARN_YEARS:
            rows.append(
                state[["person_id", "earnings"]]
                .assign(period=year)
                .loc[:, ["person_id", "period", "earnings"]]
            )
    projected = pd.concat(rows, ignore_index=True)
    support_columns = [
        column
        for column in truth_support.columns
        if column not in {"earnings"}
    ]
    projected = projected.merge(
        truth_support[support_columns],
        on=["person_id", "period"],
        how="inner",
        validate="one_to_one",
    )
    projected, _truth = restrict_earnings_domain_support(
        projected,
        truth_support,
        domain,
    )
    return AnnualEarningsReplay(
        history=pd.concat(history, ignore_index=True),
        scored=projected,
        rng_signature=_rng_signature(registry, ordinals),
    )
