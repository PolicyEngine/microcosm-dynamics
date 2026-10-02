"""From a candidate's generated panels to the EPUF gate's verdict.

The post-lock run generates a candidate panel for each of the gate's 20
registered holdouts and hands them here. This module is the whole path
from those panels to a verdict, fixed and tested before lock, so the
run script adds only the generator call and the reproduction check.

A candidate panel is gate 1's candidate-panel shape: the holdout's
persons on their observed periods, with generated ``earnings``
(``person_id``, ``period``, ``earnings``; other columns are ignored).
The gate's support is fixed by the real panel alone (who is present in
every window year, whose last period is 2006 or later, sex, birth
year, the 2004 weight), so it is read from the support frame the floor
builder computed, never from the candidate.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import (
    WINDOW_YEARS,
    WindowArrays,
    window_frame,
)
from populace_dynamics.harness.epuf_operator import (
    disclosure_constants,
    epuf_measure,
)

__all__ = ["candidate_window_cells", "score_candidate"]


def _wage_bases() -> dict[int, float]:
    return {
        year: float(row["wage_base"])
        for year, row in disclosure_constants().items()
    }


def candidate_window_cells(
    candidate: pd.DataFrame, support: pd.DataFrame
) -> dict[str, float]:
    """One seed's window cells from its generated candidate panel.

    ``support`` is the gate's support frame (``person_id``, ``sex``,
    ``birth_year``, ``weight``). The seed's scored persons are the
    support persons the candidate panel holds; each must have a
    generated row at every window year, because a support person is
    present at all four and none of the four is their anchor.
    """
    held = support[support["person_id"].isin(candidate["person_id"])]
    if held.empty:
        raise ValueError("the candidate panel holds no support person")
    rows = candidate[
        candidate["period"].isin(WINDOW_YEARS)
        & candidate["person_id"].isin(held["person_id"])
    ]
    if rows.duplicated(["person_id", "period"]).any():
        raise ValueError("candidate panel has duplicate person-periods")
    per_person = rows.groupby("person_id")["period"].nunique()
    complete = per_person.reindex(held["person_id"], fill_value=0)
    if (complete != len(WINDOW_YEARS)).any():
        raise ValueError(
            "a support person lacks a generated row in a window year; the "
            "candidate panel is not the holdout's observed periods"
        )
    earnings = rows["earnings"].to_numpy(dtype=np.float64)
    periods = rows["period"].to_numpy()
    measured = np.empty(len(rows), dtype=np.float64)
    for year in WINDOW_YEARS:
        select = periods == year
        measured[select] = epuf_measure(earnings[select], year)
    long = pd.DataFrame(
        {
            "person_id": rows["person_id"].to_numpy(),
            "year": periods,
            "earnings": measured,
        }
    )
    wage_bases = _wage_bases()
    frame = window_frame(
        long,
        held[["person_id", "sex", "birth_year", "weight"]],
        wage_bases=wage_bases,
    )
    cells = WindowArrays(frame, wage_bases=wage_bases).cells()
    return {cell_id: cell.value for cell_id, cell in cells.items()}


def score_candidate(
    candidates: Mapping[int, pd.DataFrame],
    support: pd.DataFrame,
    registered: Mapping[str, Mapping[str, float]],
) -> dict[str, object]:
    """Score the 20 generated panels against the registered intervals.

    ``candidates`` maps each gate seed to its candidate panel and
    ``registered`` is the floor artifact's ``registered`` block. Returns
    :func:`populace_dynamics.harness.epuf_gate.score_run`'s result with
    every cell's 20 per-seed values attached (gated or not).
    """
    per_seed = {
        int(seed): candidate_window_cells(panel, support)
        for seed, panel in candidates.items()
    }
    scored = gate.score_run(per_seed, registered)
    scored["per_seed_values"] = {
        str(seed): values for seed, values in sorted(per_seed.items())
    }
    return scored
