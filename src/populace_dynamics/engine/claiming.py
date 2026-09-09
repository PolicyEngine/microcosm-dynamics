"""Opt-in claiming state adapter that excludes observed benefit entrants.

The registered historical adapter remains in ``engine.steps``. Import this
module explicitly and inject its adapter into ``PeriodModules.claiming`` to
use the corrected no-new-draw partition; historical assembly is unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionModule
from populace_dynamics.engine.steps import ClaimingSchedule


def apply_claiming(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    schedule: ClaimingSchedule,
) -> pd.DataFrame:
    """Draw behavioral plans only for unclaimed, nonconverted people.

    ``claim_age`` is a planned behavioral age, not the age of every benefit
    entry. A conversion with no plan keeps a null age and becomes claimed;
    the carried ``claimed`` state prevents a later draw after the conversion
    event flag clears. Existing plans and previously claimed years remain.

    The historical age-50 threshold, PMFs, nearest-year selection, and keyed
    claiming streams are retained. Without a registry, excluding rows changes
    batch RNG consumption and can change other people's same-seed draws.
    """
    missing = {"age", "sex"} - set(frame.columns)
    if missing:
        raise ValueError(
            f"claiming frame is missing columns {sorted(missing)}"
        )
    out = frame.copy()
    if "claim_age" not in out:
        out["claim_age"] = pd.array([pd.NA] * len(out), dtype="Int64")
    age = out["age"].to_numpy(dtype=np.int64)
    converted = (
        out.get("di_converted", pd.Series(False, index=out.index))
        .fillna(False)
        .to_numpy(dtype=bool)
    )
    previously_claimed = (
        out.get("claimed", pd.Series(False, index=out.index))
        .fillna(False)
        .to_numpy(dtype=bool)
    )
    unassigned = (
        out["claim_age"].isna().to_numpy()
        & (age >= 50)
        & ~converted
        & ~previously_claimed
    )
    sex_labels = out["sex"].astype(str).to_numpy()
    for sex in sorted(np.unique(sex_labels[unassigned])):
        rows = unassigned & (sex_labels == sex)
        ages, probability = schedule.distribution(sex, context.year)
        row_indices = np.flatnonzero(rows)
        if context.rng_registry is None:
            chosen = rng.choice(ages, size=len(row_indices), p=probability)
        else:
            chosen = np.asarray(
                [
                    context.person_generator(
                        ProjectionModule.CLAIMING,
                        out.iloc[index]["person_id"],
                    ).choice(ages, p=probability)
                    for index in row_indices
                ]
            )
        out.loc[rows, "claim_age"] = chosen

    assigned = out["claim_age"].notna().to_numpy()
    plan_reached = np.zeros(len(out), dtype=bool)
    plan_reached[assigned] = age[assigned] >= out.loc[
        assigned, "claim_age"
    ].to_numpy(dtype=np.int64)
    out["claimed"] = previously_claimed | converted | plan_reached
    new_claim = out["claimed"].to_numpy(dtype=bool) & ~previously_claimed
    if "claim_year" not in out:
        out["claim_year"] = pd.array([pd.NA] * len(out), dtype="Int64")
    out.loc[new_claim, "claim_year"] = context.year
    return out
