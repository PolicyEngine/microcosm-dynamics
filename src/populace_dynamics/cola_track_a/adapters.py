"""The eight injected adapters of the Track A 2010 -> 2030 projection.

``engine.loop.ProjectionEngine`` is used unmodified.  Its binding order is
mortality, aging, marital core, fertility, disability, earnings, claiming
and household composition.  Track A (plan item A5) fills the slots with:

1. **Mortality** -- A4 :func:`~populace_dynamics.engine.di_entitlement.
   apply_di_aware_mortality` over the A2 year-aware population model
   (:class:`~populace_dynamics.cola_track_a.mortality.
   Tr2008YearAwareMortality`), or over any injected population model with
   ``bands`` (for example the engine's ``AgeSexMortalityModel``, which has
   no year axis; the runner records that gap).
2. **Aging** -- :func:`populace_dynamics.engine.steps.advance_age`.
3. **Marital core** -- :func:`widowhood_marital_step`: marital state
   passes through, except that a married person whose linked spouse was
   in the opening roster and is no longer present has been widowed by the
   spouse's simulated death in this year.  No marriage, divorce or
   remarriage is drawn.
4. **Fertility** -- :func:`adopt_marital_state`: writes the step-3 result
   into the frame (the merge point the certified assembly also uses) and
   draws no births.  Everyone aged 50+ in 2030 was alive in 2010 (plan
   section 3), so the closed cohort needs none.
5. **Disability** -- A4 :func:`~populace_dynamics.engine.di_entitlement.
   apply_di_entitlement` (awards, recoveries, conversions at FRA).
6. **Earnings** -- :func:`no_earnings`: no post-2010 earnings are drawn
   (the certified forward law is fit for 2015-2022 from a 2014 boundary;
   plan section 2).  The benefit step reads 1968-2010 careers only.
7. **Claiming** -- :func:`di_aware_claiming`: the opt-in successor
   :func:`populace_dynamics.engine.claiming.apply_claiming` (no new draw
   for conversions or prior claimants) applied to every row except
   entitled disabled workers, as the A4 integration note requires, with a
   :class:`~populace_dynamics.engine.steps.ClaimingSchedule` restricted to
   table rows at or before the plan's cap (2008), so every projection year
   snaps to that row.
8. **Household composition** -- :func:`no_household_composition`.

Every draw is person-keyed: the loop's ordinal streams for mortality and
claiming, and the A4 tagged child streams for DI.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.cola_track_a.opening import MARITAL_COLUMNS
from populace_dynamics.engine import claiming as engine_claiming
from populace_dynamics.engine.di_entitlement import (
    apply_di_aware_mortality,
    apply_di_entitlement,
    prepare_opening_di_state,
)
from populace_dynamics.engine.di_entitlement_rates import DIEntitlementRates
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
)
from populace_dynamics.engine.steps import ClaimingSchedule, advance_age

__all__ = [
    "adopt_marital_state",
    "build_period_modules",
    "claiming_schedule",
    "di_aware_claiming",
    "no_earnings",
    "no_household_composition",
    "widowhood_marital_step",
]

_EMPTY_BIRTHS = pd.DataFrame(
    {
        "parent_person_id": pd.Series(dtype="int64"),
        "birth_year": pd.Series(dtype="int64"),
    }
)


def widowhood_marital_step(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    roster_ids: frozenset[int],
) -> MaritalStepResult:
    """Pass marital state through; widow the survivors of this year's deaths.

    The loop runs mortality first, so a linked spouse from the opening
    roster who is absent from ``frame`` died in ``context.year`` (the
    cohort is closed: death is the only exit).  Spouses outside the
    opening roster have no simulated death, so their partners stay
    married; the runner counts them.  Consumes no random numbers.
    """

    del rng
    missing = {"person_id", "year", *MARITAL_COLUMNS} - set(frame.columns)
    if missing:
        raise ValueError(f"marital frame is missing columns {sorted(missing)}")
    state = frame[["person_id", "year", *MARITAL_COLUMNS]].copy()
    present = set(int(pid) for pid in state["person_id"])
    spouse = state["spouse_person_id"]
    married = (state["marital_status"] == "married").to_numpy()
    linked = spouse.notna().to_numpy() & spouse.isin(roster_ids).to_numpy(
        dtype=bool
    )
    absent = ~spouse.isin(present).to_numpy(dtype=bool)
    widowed = married & linked & absent
    if widowed.any():
        state.loc[widowed, "marital_status"] = "widowed"
        state.loc[widowed, "widowhood_year"] = int(context.year)
        state.loc[widowed, "late_spouse_person_id"] = spouse[widowed]
        state.loc[widowed, "spouse_person_id"] = pd.NA
        state.loc[widowed, "widowed_in_projection"] = True
    return MaritalStepResult(sim_years=state, births=_EMPTY_BIRTHS)


def adopt_marital_state(
    frame: pd.DataFrame,
    context: PeriodContext,
    marital: MaritalStepResult,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Step 4: write the step-3 marital columns into the frame; no births."""

    del context, rng
    state = marital.sim_years.set_index("person_id")
    if set(state.index) != set(frame["person_id"]):
        raise ValueError("the marital state does not cover the frame")
    out = frame.copy()
    for column in MARITAL_COLUMNS:
        values = out["person_id"].map(state[column])
        out[column] = values.astype(frame[column].dtype)
    return out


def no_earnings(
    frame: pd.DataFrame, context: PeriodContext, rng: np.random.Generator
) -> pd.DataFrame:
    """Step 6: Track A draws no post-2010 earnings (named gap)."""

    del context, rng
    return frame


def no_household_composition(
    frame: pd.DataFrame,
    context: PeriodContext,
    marital: MaritalStepResult,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Step 8: household composition is not simulated."""

    del context, marital, rng
    return frame


def claiming_schedule(
    pmf: Mapping[tuple[str, int], Mapping[int, float]],
    *,
    max_table_year: int,
) -> ClaimingSchedule:
    """The claiming PMF restricted to table rows at or before the cap."""

    table = {
        (str(sex), int(year)): dict(values)
        for (sex, year), values in pmf.items()
        if int(year) <= int(max_table_year)
    }
    if not table:
        raise ValueError("no claiming table rows at or before the cap")
    return ClaimingSchedule(table)


def di_aware_claiming(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    schedule: ClaimingSchedule,
) -> pd.DataFrame:
    """Step 7: ``engine.claiming.apply_claiming`` except for DI rows.

    Entitled disabled workers keep their claiming state untouched and draw
    no retirement plan.  A conversion at FRA (the A4 ``di_converted`` flag)
    reaches the successor adapter, which marks it claimed without a draw.
    With the loop's RNG registry every draw is person-keyed, so excluding
    rows does not change anyone else's draw.
    """

    if context.rng_registry is None:
        raise RuntimeError(
            "Track A claiming needs the loop's person-keyed RNG registry"
        )
    entitled = frame["di_entitled"].to_numpy(dtype=bool)
    if not entitled.any():
        return engine_claiming.apply_claiming(
            frame, context, rng, schedule=schedule
        )
    others = engine_claiming.apply_claiming(
        frame.loc[~entitled], context, rng, schedule=schedule
    )
    out = pd.concat([others, frame.loc[entitled]], sort=False)
    return out.loc[frame.index]


def build_period_modules(
    *,
    roster_ids: frozenset[int],
    population_model: Any,
    di_rates: DIEntitlementRates,
    fra_schedule: Any,
    schedule: ClaimingSchedule,
    death_log: MutableMapping[int, pd.DataFrame] | None = None,
    cell_log: MutableMapping[int, pd.DataFrame] | None = None,
    weight_column: str = "weight",
) -> PeriodModules:
    """Assemble the Track A adapters in the loop's binding order."""

    return PeriodModules(
        mortality=partial(
            apply_di_aware_mortality,
            population_model=population_model,
            rates=di_rates,
            death_log=death_log,
            weight_column=weight_column,
            cell_log=cell_log,
        ),
        aging=advance_age,
        marital_core=partial(widowhood_marital_step, roster_ids=roster_ids),
        fertility=adopt_marital_state,
        disability=partial(
            apply_di_entitlement, rates=di_rates, fra_schedule=fra_schedule
        ),
        earnings=no_earnings,
        claiming=partial(di_aware_claiming, schedule=schedule),
        household_composition=no_household_composition,
        initialize=partial(
            prepare_opening_di_state,
            rates=di_rates,
            fra_schedule=fra_schedule,
        ),
    )
