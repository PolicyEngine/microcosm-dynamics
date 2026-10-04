"""From a candidate's generated panels to the EPUF comparison report.

``gate_epuf`` is registered and unlocked: referee round 1 ruled that it
gates nothing (``docs/amendments/gate_epuf_registration_proposal.md``).
What a run publishes is therefore a report, not a verdict. For every
window cell, :func:`report_candidate` gives the candidate's 20-seed
estimate, its distance from EPUF, and that distance split into the
candidate's distance from the PSID and the PSID's distance from EPUF. It
returns no pass or fail.

A candidate panel is gate 1's candidate-panel shape: the holdout's
persons on their observed periods, with generated ``earnings``
(``person_id``, ``period``, ``earnings``; other columns are ignored).
The support is fixed by the real panel alone (who is present in every
window year, whose last period is 2006 or later, sex, birth year, the
2004 weight), so it is read from the support frame the floor builder
computed, never from the candidate.

No run script calls this module yet. A run that regenerates a gate-1
candidate's 20 panels hands them here.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import (
    WINDOW_YEARS,
    WindowArrays,
    transform,
    window_frame,
)
from populace_dynamics.harness.epuf_operator import (
    disclosure_constants,
    epuf_measure,
)

__all__ = ["candidate_window_cells", "report_candidate"]


def _wage_bases() -> dict[int, float]:
    return {
        year: float(row["wage_base"])
        for year, row in disclosure_constants().items()
    }


def candidate_window_cells(
    candidate: pd.DataFrame, support: pd.DataFrame
) -> dict[str, float]:
    """One seed's window cells from its generated candidate panel.

    ``support`` is the support frame (``person_id``, ``sex``,
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


def _on_scale(cell_id: str, value: float | None) -> float:
    return float("nan") if value is None else transform(cell_id, value)


def report_candidate(
    candidates: Mapping[int, pd.DataFrame],
    support: pd.DataFrame,
    cells: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Report every window cell of a candidate's 20 generated panels.

    ``candidates`` maps each gate seed to its candidate panel and
    ``cells`` is the floor artifact's ``cells`` block, which holds each
    cell's EPUF and PSID values. For every cell the report gives, on the
    cell's metric scale (log for shares, identity for rank correlations):

    - ``estimate``: the transform of the mean of the 20 per-seed values;
    - ``gap_from_epuf``: the estimate less EPUF's value;
    - ``source_term_psid_minus_epuf``: the PSID's distance from EPUF;
    - ``model_term_candidate_minus_psid``: the rest of the gap.

    A value that is undefined (a cell with no events on some seed, or no
    PSID value) is NaN. The report carries no pass or fail: the gate is
    unlocked and gates no cell.
    """
    if set(candidates) != set(gate.GATE_SEEDS):
        raise ValueError(
            f"a run reports exactly seeds {gate.GATE_SEEDS[0]}-"
            f"{gate.GATE_SEEDS[-1]}; got {sorted(candidates)}"
        )
    per_seed = {
        int(seed): candidate_window_cells(panel, support)
        for seed, panel in candidates.items()
    }
    report = {}
    for cell_id, registered in cells.items():
        values = [per_seed[seed][cell_id] for seed in gate.GATE_SEEDS]
        estimate = gate.pooled_estimate(cell_id, values)
        epuf = _on_scale(cell_id, registered["epuf_value"])
        source = _on_scale(cell_id, registered["psid_value"]) - epuf
        gap = estimate - epuf
        report[cell_id] = {
            "estimate": estimate,
            "gap_from_epuf": gap,
            "source_term_psid_minus_epuf": source,
            "model_term_candidate_minus_psid": gap - source,
            "per_seed_values": values,
        }
    return {
        "status": "report_only",
        "n_cells": len(report),
        "cells": report,
    }
