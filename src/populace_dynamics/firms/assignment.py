"""Synthetic roster assignment — connecting observed workers to observed
firms (#192, phase 0).

This is the seam where the two sides meet. Both sides are **observed
microdata**: people and job spells come from SIPP/CPS
(``data/sipp_jobs.py``, ``data/asec_firm_size.py``), firms come from
Form 5500 (``firms/frame.py``). Nothing on either side is generated.

**The link between them is not observed, and never can be from public
data.** No public source connects a SIPP or CPS respondent to their
actual employer. What this module builds is a *simulated* roster: a
reproducible, capacity-constrained allocation of real workers to real
firm records within pre-registered compatibility cells. Every function
here is named to keep that distinction visible, and
:func:`assign_workers` deliberately returns ``firm_instance_id`` — an
artificial key — never an EIN or sponsor name.

Therefore the output does **not**: reveal any worker's real employer,
identify actual coworkers, support identified firm effects, worker
sorting, spillovers, or AKM-style decompositions. That boundary is the
one recorded on #282 and it is unchanged by having observed firm
records on the other side.

**The weighted-to-discrete step is a registered design choice.** The
calibrated frame carries fractional weights: a sponsor with weight 15.5
represents 15.5 firms. A roster needs discrete employers, so
:func:`expand_to_firm_instances` replicates each observed record into
integer instances. This is ordinary weighted representation — the same
move that treats a CPS person with weight 1,200 as 1,200 people — but
it has a consequence worth stating plainly: **the replicates of one
sponsor are not distinct real firms.** They share an observed size and
sector, and any statistic that treats them as independent employers
(coworker correlation, between-firm variance) is measuring the
replication, not the economy. Such statistics are exactly what E12
covers and what phase 2 does not certify.

Residual weight is allocated by a seeded Bernoulli draw rather than
rounding, so the expected instance count is the weight and the frame's
firm margin survives expansion in expectation instead of drifting
systematically downward.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .frame import CELL_KEYS

__all__ = [
    "expand_to_firm_instances",
    "assign_workers",
]


def expand_to_firm_instances(
    frame: pd.DataFrame,
    *,
    seed: int,
    size_column: str = "active_participants",
    weight_column: str = "weight",
) -> pd.DataFrame:
    """Replicate weighted sponsor records into discrete firm instances.

    Each record contributes ``floor(weight)`` instances plus one more
    with probability ``weight - floor(weight)``, so the expected count
    equals the weight exactly. Rounding instead would bias the firm
    margin downward, because most weights in the calibrated frame sit
    between 1 and 4.

    Returns one row per firm instance with ``firm_instance_id`` (an
    artificial key), the source ``sponsor_ein``, the cell keys, and
    ``capacity`` taken from the observed size. ``seed`` is required:
    an unseeded expansion is not reproducible, and the pre-registration
    discipline needs the roster to be re-derivable exactly.
    """
    for column in (size_column, weight_column, *CELL_KEYS):
        if column not in frame.columns:
            raise ValueError(f"Frame lacks {column!r}; use calibrate_*().")

    rng = np.random.default_rng(seed)
    weights = frame[weight_column].to_numpy(dtype=float)
    if (weights < 0).any():
        raise ValueError("Negative weights cannot be expanded.")
    whole = np.floor(weights).astype(int)
    extra = (rng.random(len(weights)) < (weights - whole)).astype(int)
    counts = whole + extra

    repeated = frame.loc[frame.index.repeat(counts)].reset_index(drop=True)
    out = pd.DataFrame(
        {
            "firm_instance_id": np.arange(len(repeated), dtype=np.int64),
            "sponsor_ein": repeated.get("sponsor_ein"),
            "naics_sector": repeated["naics_sector"].to_numpy(),
            "canonical_band": repeated["canonical_band"].to_numpy(),
            "capacity": repeated[size_column].to_numpy(),
        }
    )
    out.attrs["seed"] = int(seed)
    out.attrs["source_records"] = int(len(frame))
    out.attrs["expected_instances"] = float(weights.sum())
    out.attrs["actual_instances"] = int(len(out))
    out.attrs["total_capacity"] = float(out["capacity"].sum())
    return out


def assign_workers(
    workers: pd.DataFrame,
    firm_instances: pd.DataFrame,
    *,
    seed: int,
    worker_weight_column: str | None = None,
) -> pd.DataFrame:
    """Allocate workers to firm instances within compatibility cells.

    Workers and firms are matched **only** on the pre-registered cell
    keys (NAICS sector x canonical firm-size band). No earnings,
    tenure, geography or demographic field enters the match: adding one
    would make the assignment informative about attributes the design
    has not registered, and would quietly turn a capacity allocation
    into an imputation.

    Within each cell the allocation is a seeded permutation of workers
    against firm slots, filling each instance up to ``capacity``. A
    worker in a cell with no firm instance is returned with a null
    ``firm_instance_id`` rather than being dropped or reassigned to a
    neighbouring cell — silently relocating them would fabricate
    cross-cell mobility that the data does not support.

    Returns the worker frame with ``firm_instance_id`` attached, and
    diagnostics on ``attrs``: assignment rate, unassigned counts by
    cell, and capacity utilisation. A low fill rate is a real finding
    about frame-vs-panel scale, not something to paper over.
    """
    for column in CELL_KEYS:
        if column not in workers.columns:
            raise ValueError(f"Workers lack {column!r}.")
        if column not in firm_instances.columns:
            raise ValueError(f"Firm instances lack {column!r}.")
    if "capacity" not in firm_instances.columns:
        raise ValueError("Firm instances lack 'capacity'.")

    rng = np.random.default_rng(seed)
    assigned = pd.Series(pd.NA, index=workers.index, dtype="Int64")
    unassigned: list[dict[str, object]] = []
    used_capacity = 0.0
    offered_capacity = 0.0

    firms_by_cell = dict(list(firm_instances.groupby(list(CELL_KEYS))))
    for cell, group in workers.groupby(list(CELL_KEYS)):
        firms = firms_by_cell.get(cell)
        if firms is None or firms.empty:
            unassigned.append(
                {
                    "cell": "/".join(map(str, cell)),
                    "workers": int(len(group)),
                    "reason": "no firm instance in cell",
                }
            )
            continue
        # One slot per unit of capacity, shuffled so the allocation does
        # not follow record order (which is EIN order, i.e. correlated
        # with filing vintage).
        capacity = firms["capacity"].to_numpy(dtype=float)
        slots = np.repeat(
            firms["firm_instance_id"].to_numpy(),
            np.maximum(capacity, 0).astype(int),
        )
        offered_capacity += float(capacity.sum())
        if len(slots) == 0:
            unassigned.append(
                {
                    "cell": "/".join(map(str, cell)),
                    "workers": int(len(group)),
                    "reason": "zero capacity in cell",
                }
            )
            continue
        rng.shuffle(slots)
        take = min(len(group), len(slots))
        order = rng.permutation(len(group))[:take]
        assigned.iloc[
            [workers.index.get_loc(i) for i in group.index[order]]
        ] = slots[:take]
        used_capacity += take
        if take < len(group):
            unassigned.append(
                {
                    "cell": "/".join(map(str, cell)),
                    "workers": int(len(group) - take),
                    "reason": "cell capacity exhausted",
                }
            )

    out = workers.copy()
    out["firm_instance_id"] = assigned
    matched = int(out["firm_instance_id"].notna().sum())
    out.attrs["seed"] = int(seed)
    out.attrs["assigned_workers"] = matched
    out.attrs["total_workers"] = int(len(out))
    out.attrs["assignment_rate"] = matched / len(out) if len(out) else 0.0
    out.attrs["unassigned"] = unassigned
    out.attrs["offered_capacity"] = offered_capacity
    out.attrs["capacity_utilisation"] = (
        used_capacity / offered_capacity if offered_capacity else 0.0
    )
    out.attrs["observed_link"] = False
    return out
