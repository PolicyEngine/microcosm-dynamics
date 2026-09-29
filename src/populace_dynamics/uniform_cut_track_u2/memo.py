"""The U2 comparison-memo rules of section 10a (no comparator values).

The validation-only lane writes the comparison memo after the registered
artifact is committed; this module fixes, in code and before any
comparator is opened, how a memo classifies a model statistic against a
printed Report level or change.  No Report value is held anywhere in the
repository: every function takes the printed values as arguments, and the
tests pass INVENTED ones.

Rules (section 10a; the cleared U2 statement: percentages for levels,
percentage points for changes, whole-number printed levels, the inherited
rounding allowance):

* gap = model statistic minus Report statistic, on **unrounded** model
  values (display rounding never changes a classification);
* a printed level carries a +/-0.5 percentage-point rounding allowance;
* a derived change (Table 21 minus Table 19) uses the open interval
  ``(printed difference - 1, printed difference + 1)``; an exact
  endpoint is **on the edge**, not inside (the conservative reading
  applies the same endpoint rule to the level allowance);
* rounding intervals appear only in the memo, never in the artifact;
* no acceptance threshold or pass/fail certification;
* every cell with ``n_observations < 30`` is flagged;
* a cell where no observation changes poverty status reports the change's
  uncertainty as **"uncertainty not estimable"**, keeping the mechanical
  values and the level uncertainty;
* a gap is never divided by an undefined or zero uncertainty measure;
* an undefined cell is reported with its reason, never imputed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from populace_dynamics.uniform_cut_track_u2 import identity

__all__ = [
    "INTERVAL_ID",
    "LEVEL_ALLOWANCE",
    "CHANGE_ALLOWANCE",
    "NO_SWITCHER_WORDING",
    "SMALL_CELL_THRESHOLD",
    "change_interval",
    "classify",
    "level_interval",
    "memo_cell",
]

INTERVAL_ID = identity.COMPARATOR_INTERVAL
LEVEL_ALLOWANCE = 0.5
CHANGE_ALLOWANCE = 1.0
SMALL_CELL_THRESHOLD = 30
NO_SWITCHER_WORDING = "uncertainty not estimable"
INSIDE = "inside"
EDGE = "on the edge"
OUTSIDE = "outside"


def _printed(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{what} must be a whole-number printed level")
    return int(value)


def level_interval(printed: int) -> tuple[float, float]:
    """``(printed - 0.5, printed + 0.5)`` for a printed level."""

    level = _printed(printed, "a printed level")
    return (level - LEVEL_ALLOWANCE, level + LEVEL_ALLOWANCE)


def change_interval(
    printed_baseline: int, printed_reform: int
) -> tuple[float, float]:
    """The open interval around Table 21 minus Table 19."""

    difference = _printed(printed_reform, "the reform level") - _printed(
        printed_baseline, "the baseline level"
    )
    return (difference - CHANGE_ALLOWANCE, difference + CHANGE_ALLOWANCE)


def classify(value: float, interval: tuple[float, float]) -> str:
    """``inside`` (strictly), ``on the edge`` (an endpoint) or ``outside``.

    ``value`` is the unrounded model statistic.
    """

    value = float(value)
    if not math.isfinite(value):
        raise ValueError("a model statistic must be finite")
    low, high = interval
    if value == low or value == high:
        return EDGE
    if low < value < high:
        return INSIDE
    return OUTSIDE


def _uncertainty(cell: Mapping[str, Any], statistic: str) -> dict[str, Any]:
    se = ((cell.get("design_se") or {}).get(statistic) or {}).get("se")
    floor = (cell.get("floor") or {}).get(statistic) or {}
    return {
        "design_se": se,
        "floor_mean": floor.get("mean") if floor.get("defined") else None,
        "floor_defined": bool(floor.get("defined")),
    }


def _ratio(gap: float, measure: Any) -> float | None:
    if measure is None:
        return None
    measure = float(measure)
    if not math.isfinite(measure) or measure <= 0:
        return None
    return gap / measure


def memo_cell(
    cell: Mapping[str, Any], printed_baseline: int, printed_reform: int
) -> dict[str, Any]:
    """One memo line: gaps, classifications and uncertainty wording.

    ``cell`` is a U2 tabulation cell (with ``n_switchers``);
    ``printed_baseline`` and ``printed_reform`` are the printed Table 19
    and Table 21 levels (invented in tests).
    """

    out: dict[str, Any] = {
        "cell": cell.get("cell"),
        "interval_id": INTERVAL_ID,
        "n_observations": int(cell.get("n_observations", 0)),
        "small_cell": int(cell.get("n_observations", 0))
        < SMALL_CELL_THRESHOLD,
    }
    if not cell.get("defined"):
        out.update(
            defined=False,
            undefined_reason=cell.get("undefined_reason"),
            classification=None,
        )
        return out
    out["defined"] = True
    change = change_interval(printed_baseline, printed_reform)
    levels = {
        "baseline_rate": level_interval(printed_baseline),
        "reform_rate": level_interval(printed_reform),
    }
    report = {
        "baseline_rate": printed_baseline,
        "reform_rate": printed_reform,
        "delta": printed_reform - printed_baseline,
    }
    no_switcher = int(cell.get("n_switchers", -1)) == 0
    for statistic in ("baseline_rate", "reform_rate", "delta"):
        model = float(cell[statistic])
        gap = model - report[statistic]
        interval = change if statistic == "delta" else levels[statistic]
        uncertainty = _uncertainty(cell, statistic)
        entry = {
            "model": model,
            "report": report[statistic],
            "gap": gap,
            "interval": list(interval),
            "classification": classify(model, interval),
            "gap_over_design_se": _ratio(gap, uncertainty["design_se"]),
            "gap_over_floor": _ratio(gap, uncertainty["floor_mean"]),
            **uncertainty,
        }
        if statistic == "delta" and no_switcher:
            entry.update(
                uncertainty=NO_SWITCHER_WORDING,
                gap_over_design_se=None,
                gap_over_floor=None,
            )
        out[statistic] = entry
    return out
