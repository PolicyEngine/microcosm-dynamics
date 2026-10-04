"""The algebra of the proposed EPUF covered-earnings gate.

Everything that turns floors into tolerances, partitions cells into
gated and report-only, and scores a run lives here, so that the floor
builder, the post-lock runner and the binding tests share one
derivation. Nothing in this module reads data.

**The scored quantity.** A candidate generates earnings for the gate's
20 registered holdouts (seeds 0-19). For each cell the candidate's
estimate is the mean of its 20 per-seed values, put on the cell's metric
scale (log for shares, identity for rank correlations), and its distance
from EPUF is ``G = estimate - EPUF value``.

**The bridge.** Real PSID earnings sit at their own distance from EPUF,
``B = PSID value - EPUF value``, for reasons no generator trained on the
PSID controls (who the PSID samples, what it counts as earnings, how
people report). The gate neither subtracts ``B`` (that would cancel
EPUF out of the comparison and re-run gate 1) nor ignores it (then a
faithful generator fails wherever the PSID itself differs from EPUF).
It accepts a candidate that lies between EPUF and the PSID's own
position, plus noise::

    min(0, B) - t  <=  G  <=  max(0, B) + t

**The noise.** A faithful generator's 20-seed mean differs from the
real PSID value by two things. One averages down across seeds (which
persons fall in each holdout, each seed's draws, each seed's fit). The
other does not: every seed scores generated values against the same
realised PSID sample, whose own deviation from its conditional law is
common to all 20. For floor replicate ``b`` the real-data analogue is::

    e_b = [m(A_b) - m(B_b)] / 2
          + pooled(m(H_b0), ..., m(H_b19)) - pooled(m(T_b0), ..., m(T_b19))

where ``A_b``/``B_b`` are person-disjoint halves of the PSID support
(the common term) and ``H_bj``/``T_bj`` are a 20% holdout and its 80%
complement under the gate's own split function (the term that averages
down). ``t`` is the house tolerance on ``|e_b|``: mean plus four
standard deviations, rounded to three decimals.

**Which cells gate.** A cell gates only if a candidate whose distance
from EPUF reaches the metric's cap would fail it with probability at
least 0.8, that is ``|B| + t + 0.8416 * sigma <= cap``. A pass therefore
always means "within the cap of EPUF". Cells whose bridge or noise is
too large for that are reported with the reason.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from populace_dynamics.harness.epuf_cells import (
    COHORT_BANDS,
    SEXES,
    metric,
    transform,
)

__all__ = [
    "CAPS",
    "EPUF_NOISE_SHARE_MAX",
    "FAMILIES",
    "GATE_SEEDS",
    "HALF_FRACTION",
    "HOLDOUT_FRACTION",
    "K_TOLERANCE",
    "MIN_EVENTS",
    "N_FLOOR_REPLICATES",
    "OC_PAUSE",
    "ROUNDING",
    "Z_POWER_80",
    "CellFloor",
    "adopt_ladder",
    "demotion_reason",
    "faithful_pass_probability",
    "floor_replicate",
    "floor_terms",
    "half_split_seed",
    "holdout_split_seed",
    "hull",
    "minimum_detectable_gap",
    "pooled_estimate",
    "realized_sigma",
    "score_cell",
    "score_run",
    "tolerance",
]

K_TOLERANCE = 4.0
ROUNDING = 3
#: The standard normal's 80th percentile.
Z_POWER_80 = 0.8416212335729143
#: Power caps by metric, the house values (gates.yaml gate_m6
#: ``metric_caps``): ln(1.5) for log ratios, 0.15 for correlation gaps.
CAPS: dict[str, float] = {"log_ratio": math.log(1.5), "abs_gap": 0.15}
MIN_EVENTS = 20
N_FLOOR_REPLICATES = 100
GATE_SEEDS: tuple[int, ...] = tuple(range(20))
HOLDOUT_FRACTION = 0.2
HALF_FRACTION = 0.5
#: The ceremony pauses if the faithful-candidate pass probability of the
#: gated surface is below this (gates.yaml gate_m6 ``oc_before_lock``).
OC_PAUSE = 0.90
#: A cell is demoted if EPUF's own sampling sd exceeds this share of the
#: cell's realised sigma, because the floor does not price it.
EPUF_NOISE_SHARE_MAX = 0.1

#: The gate's families and the order in which each tries its cells.
FAMILIES: dict[str, tuple[str, ...]] = {
    "persistence": ("r6",),
    "participation": ("zint", "d_anyzero"),
    "tail": ("q_atmax", "mpers", "q_sexratio"),
}


def half_split_seed(replicate: int) -> int:
    """Split seed of floor replicate ``b``'s person-disjoint halves."""
    return int(replicate)


def holdout_split_seed(replicate: int, draw: int) -> int:
    """Split seed of floor replicate ``b``'s ``j``-th 20%/80% split.

    Offset by 1000 so that no floor split reuses a gate seed (0-19).
    """
    return 1000 + len(GATE_SEEDS) * int(replicate) + int(draw)


def pooled_estimate(cell_id: str, values: Sequence[float]) -> float:
    """The 20-seed estimate: the mean of the values, then the transform.

    Averaging before the log keeps a share cell stable when one seed has
    few events; a mean of logs would not be.
    """
    values = np.asarray(values, dtype=np.float64)
    if not np.isfinite(values).all():
        return float("nan")
    return transform(cell_id, float(values.mean()))


def floor_terms(
    cell_id: str,
    half_a: float,
    half_b: float,
    holdouts: Sequence[float],
    complements: Sequence[float],
) -> tuple[float, float]:
    """The two terms of a floor replicate (module docstring).

    The first is the noise the 20 seeds share, the second the noise that
    averages down across them.
    """
    common = (transform(cell_id, half_a) - transform(cell_id, half_b)) / 2.0
    averaging = pooled_estimate(cell_id, holdouts) - pooled_estimate(
        cell_id, complements
    )
    return float(common), float(averaging)


def floor_replicate(
    cell_id: str,
    half_a: float,
    half_b: float,
    holdouts: Sequence[float],
    complements: Sequence[float],
) -> float:
    """One real-data floor replicate ``e_b`` of a cell: the terms' sum."""
    return float(
        sum(floor_terms(cell_id, half_a, half_b, holdouts, complements))
    )


def tolerance(replicates: Sequence[float]) -> float:
    """``round(mean|e| + 4 * sd|e|, 3)``, the house floor formula."""
    magnitude = np.abs(np.asarray(replicates, dtype=np.float64))
    return round(
        float(magnitude.mean() + K_TOLERANCE * magnitude.std(ddof=1)),
        ROUNDING,
    )


def realized_sigma(replicates: Sequence[float]) -> float:
    """Root mean square of the floor replicates."""
    values = np.asarray(replicates, dtype=np.float64)
    return float(np.sqrt(np.mean(values * values)))


def hull(bridge: float, t: float) -> tuple[float, float]:
    """The acceptance interval for ``G``, rounded outward to 3 decimals."""
    scale = 10**ROUNDING
    lower = math.floor((min(0.0, bridge) - t) * scale + 1e-9) / scale
    upper = math.ceil((max(0.0, bridge) + t) * scale - 1e-9) / scale
    return lower, upper


def minimum_detectable_gap(bridge: float, t: float, sigma: float) -> float:
    """The distance from EPUF that fails with probability at least 0.8."""
    return abs(bridge) + t + Z_POWER_80 * sigma


def faithful_pass_probability(
    bridge: float, sigma: float, lower: float, upper: float
) -> float:
    """Pass probability of a candidate centred on the PSID's position."""
    if sigma <= 0.0:
        return float(lower <= bridge <= upper)
    return float(
        norm.cdf((upper - bridge) / sigma) - norm.cdf((lower - bridge) / sigma)
    )


@dataclass(frozen=True)
class CellFloor:
    """What the floor builder knows about one cell before partitioning."""

    cell_id: str
    defined: bool
    min_events: int
    bridge: float
    t: float
    sigma: float
    epuf_sampling_sd: float


def demotion_reason(cell: CellFloor) -> str | None:
    """Why a cell cannot gate, or ``None`` if it can.

    The checks run in this order, so a reason names the first failure.
    """
    cap = CAPS[metric(cell.cell_id)]
    if not cell.defined:
        return "undefined_on_some_split"
    if cell.min_events < MIN_EVENTS:
        return "below_20_events"
    if cell.epuf_sampling_sd > EPUF_NOISE_SHARE_MAX * cell.sigma:
        return "epuf_sampling_not_negligible"
    if minimum_detectable_gap(0.0, cell.t, cell.sigma) > cap:
        return "noise_exceeds_cap"
    if minimum_detectable_gap(cell.bridge, cell.t, cell.sigma) > cap:
        return "bridge_exceeds_budget"
    return None


def adopt_ladder(
    reasons: Mapping[str, str | None],
) -> tuple[list[str], dict[str, str]]:
    """Choose the gated cells from each cell's demotion reason.

    Returns the gated cell ids and a reason for every other cell. The
    rules, fixed before any PSID floor existed:

    - ``r6``: gate all six sex-by-cohort cells if every one is eligible;
      otherwise gate each eligible sex-level cell.
    - participation: per sex, gate ``zint`` if eligible, else
      ``d_anyzero`` if eligible.
    - tail: gate each eligible sex-level ``q_atmax`` and ``mpers`` cell
      and ``q_sexratio``.
    - every other cohort-level cell is reported, never gated.
    """
    gated: list[str] = []
    report: dict[str, str] = {}

    def note(cell_id: str, default: str) -> None:
        report[cell_id] = reasons[cell_id] or default

    band_r6 = [f"r6.{sex}.{band}" for sex in SEXES for band in COHORT_BANDS]
    if all(reasons[cell_id] is None for cell_id in band_r6):
        gated.extend(band_r6)
        for sex in SEXES:
            note(f"r6.{sex}", "superseded_by_cohort_rung")
    else:
        for cell_id in band_r6:
            note(cell_id, "cohort_rung_not_adopted")
        for sex in SEXES:
            cell_id = f"r6.{sex}"
            if reasons[cell_id] is None:
                gated.append(cell_id)
            else:
                note(cell_id, "")

    for sex in SEXES:
        zint, d_any = f"zint.{sex}", f"d_anyzero.{sex}"
        if reasons[zint] is None:
            gated.append(zint)
            note(d_any, "superseded_by_zint")
        else:
            note(zint, "")
            if reasons[d_any] is None:
                gated.append(d_any)
            else:
                note(d_any, "")

    tail = [f"{stat}.{sex}" for stat in ("q_atmax", "mpers") for sex in SEXES]
    for cell_id in [*tail, "q_sexratio"]:
        if reasons[cell_id] is None:
            gated.append(cell_id)
        else:
            note(cell_id, "")

    for cell_id in reasons:
        if cell_id not in gated and cell_id not in report:
            note(cell_id, "reported_by_cohort")
    return gated, report


def score_cell(
    cell_id: str,
    per_seed_values: Sequence[float],
    *,
    epuf_value: float,
    lower: float,
    upper: float,
) -> dict[str, object]:
    """Score one cell of a run against its registered interval."""
    estimate = pooled_estimate(cell_id, per_seed_values)
    gap = estimate - transform(cell_id, epuf_value)
    passed = bool(np.isfinite(gap) and lower <= gap <= upper)
    return {
        "estimate": estimate,
        "gap_from_epuf": gap,
        "lower": lower,
        "upper": upper,
        "pass": passed,
    }


def score_run(
    per_seed_cells: Mapping[int, Mapping[str, float]],
    gated: Mapping[str, Mapping[str, float]],
) -> dict[str, object]:
    """Score a candidate's 20 per-seed cell values against the gate.

    ``per_seed_cells`` maps each gate seed to its cell values on the
    natural scale. ``gated`` maps each gated cell id to its registered
    ``epuf_value``, ``psid_value``, ``lower`` and ``upper``. The gate
    passes iff every gated cell passes. Each cell also reports the
    decomposition of its gap into the model's distance from the PSID and
    the PSID's distance from EPUF.
    """
    if set(per_seed_cells) != set(GATE_SEEDS):
        raise ValueError(
            f"a run scores exactly seeds {GATE_SEEDS[0]}-{GATE_SEEDS[-1]}; "
            f"got {sorted(per_seed_cells)}"
        )
    cells = {}
    for cell_id, registered in gated.items():
        values = [per_seed_cells[seed][cell_id] for seed in GATE_SEEDS]
        result = score_cell(
            cell_id,
            values,
            epuf_value=registered["epuf_value"],
            lower=registered["lower"],
            upper=registered["upper"],
        )
        source = transform(cell_id, registered["psid_value"]) - transform(
            cell_id, registered["epuf_value"]
        )
        result["source_term_psid_minus_epuf"] = source
        result["model_term_candidate_minus_psid"] = (
            result["gap_from_epuf"] - source
        )
        cells[cell_id] = result
    return {
        "cells": cells,
        "n_gated": len(cells),
        "n_pass": sum(bool(cell["pass"]) for cell in cells.values()),
        "pass": bool(cells) and all(cell["pass"] for cell in cells.values()),
    }
