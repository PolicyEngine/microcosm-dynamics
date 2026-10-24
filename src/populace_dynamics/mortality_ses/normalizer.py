"""Deterministic cell accounting for differential mortality.

The coefficients used here carry no empirical claim.  This module only
redistributes each cell's baseline expected deaths, subject to prescribed
fixed probabilities and the probability bounds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, localcontext
from math import fsum

import numpy as np
import pandas as pd

CELL_LOG_COLUMNS = (
    "year",
    "sex",
    "age",
    "persons",
    "fixed_persons",
    "weight",
    "fixed_weight",
    "baseline_expected_deaths",
    "applied_expected_deaths",
    "factor",
    "clipped_persons",
    "clipping_residual",
    "infeasible",
    "unclassified_refuse",
    "unclassified_reference",
)


def _stable_sum(values: np.ndarray) -> np.longdouble:
    """Sum nonnegative values without a row-order-dependent reduction.

    Scaling before ``fsum`` avoids an overflowing intermediate sum.
    ``fsum`` gives the same result after a row permutation.  Cells whose
    products need a wider exponent range use the Decimal path below.
    """
    if not values.size:
        return np.longdouble(0)
    maximum = np.max(values)
    if maximum == 0:
        return np.longdouble(0)
    return maximum * np.longdouble(fsum(float(x / maximum) for x in values))


def _decimal_cell(base, rr, w, is_fixed, prescribed):
    """Handle extreme finite float64 inputs without platform assumptions.

    On some supported platforms ``longdouble`` has float64's exponent
    range.  Decimal's exponent range retains positive q*RR support even
    when that product would underflow, and avoids overflowing products.
    This slower path is restricted to cells containing extreme magnitudes.
    """
    with localcontext() as decimal_context:
        # Enough to retain exact products of three finite binary64 inputs,
        # including subnormals, before the normalization division.
        decimal_context.prec = 2400
        zero, one = Decimal(0), Decimal(1)
        base, rr, w, prescribed = (
            [Decimal.from_float(float(value)) for value in values]
            for values in (base, rr, w, prescribed)
        )

        def total(values):
            return sum(sorted(values), zero)

        free = [i for i, fixed in enumerate(is_fixed) if not fixed]
        fixed = [i for i, fixed in enumerate(is_fixed) if fixed]
        result = [
            prescribed[i] if is_fixed[i] else zero for i in range(len(w))
        ]
        baseline_deaths = total(
            wi * qi for wi, qi in zip(w, base, strict=True)
        )
        fixed_deaths = total(w[i] * prescribed[i] for i in fixed)
        fixed_at_baseline = all(prescribed[i] == base[i] for i in fixed)
        target = (
            total(w[i] * base[i] for i in free)
            if fixed_at_baseline
            else baseline_deaths - fixed_deaths
        )
        support = [i for i in free if base[i] > zero]
        capacity = total(w[i] for i in support)
        capped = set()
        infeasible = False
        factor = one
        if fixed_at_baseline and (
            not free or all(rr[i] == rr[free[0]] for i in free)
        ):
            result = base.copy()
            factor = one / rr[free[0]] if free else one
        elif target < zero:
            infeasible, factor = True, zero
        elif target == zero:
            factor = zero
        elif target >= capacity:
            infeasible = target > capacity
            for i in support:
                result[i] = one
            capped = set(support)
            factor = max(
                (one / (base[i] * rr[i]) for i in support), default=one
            )
        else:
            raw = [qi * ri for qi, ri in zip(base, rr, strict=True)]
            active = {i for i in support if w[i] > zero}
            remaining = target
            while active:
                factor = remaining / total(w[i] * raw[i] for i in active)
                next_capped = {i for i in active if raw[i] * factor > one}
                if not next_capped:
                    break
                capped |= next_capped
                active -= next_capped
                remaining = target - total(w[i] for i in capped)
            for i in free:
                result[i] = min(one, raw[i] * factor)
            capped = {i for i in free if raw[i] * factor > one}
        probabilities = np.asarray([float(value) for value in result])
        applied = total(
            wi * Decimal.from_float(float(qi))
            for wi, qi in zip(w, probabilities, strict=True)
        )
        residual = baseline_deaths - applied if infeasible or capped else zero
        return probabilities, {
            "weight": float(total(w)),
            "fixed_weight": float(total(w[i] for i in fixed)),
            "baseline_expected_deaths": float(baseline_deaths),
            "applied_expected_deaths": float(applied),
            "factor": float(factor),
            "clipped_persons": len(capped),
            "clipping_residual": float(residual),
            "infeasible": infeasible,
        }


def _normalize_cell(base, rr, w, is_fixed, prescribed):
    # Within these magnitudes, coefficients, weighted products, and capped
    # scaling products remain representable even on float64-only platforms.
    if any(
        np.any((values > 0) & (values < 1e-80)) or np.any(values > 1e80)
        for values in (base, rr, w, prescribed)
    ):
        return _decimal_cell(base, rr, w, is_fixed, prescribed)
    free = ~is_fixed
    result = np.zeros(len(base), dtype=np.longdouble)
    result[is_fixed] = prescribed[is_fixed]
    baseline_deaths = _stable_sum(w * base)
    fixed_deaths = _stable_sum(w[is_fixed] * prescribed[is_fixed])
    fixed_at_baseline = np.array_equal(prescribed[is_fixed], base[is_fixed])
    # Avoid cancellation of small free totals when fixed rows dominate.
    target = (
        _stable_sum(w[free] * base[free])
        if fixed_at_baseline
        else baseline_deaths - fixed_deaths
    )
    support = free & (base > 0)
    capacity = _stable_sum(w[support])
    capped = np.zeros(len(base), dtype=bool)
    infeasible = False
    factor = np.longdouble(1)
    if fixed_at_baseline and (
        not np.any(free) or np.all(rr[free] == rr[free][0])
    ):
        result = base.copy()
        if np.any(free):
            factor = np.longdouble(1) / rr[free][0]
    elif target < 0:
        infeasible = True
        factor = np.longdouble(0)
    elif target == 0:
        factor = np.longdouble(0)
    elif target >= capacity:
        # Baseline fixed rows are feasible by construction.  Independent
        # floating reductions can differ by a rounding bit at capacity.
        infeasible = bool(target > capacity) and not fixed_at_baseline
        result[support] = 1
        capped[support] = True
        factor = (
            np.max(1 / (base[support] * rr[support]))
            if np.any(support)
            else np.longdouble(1)
        )
    else:
        raw = base * rr
        active = support & (w > 0)
        remaining = target
        while np.any(active):
            denominator = _stable_sum(w[active] * raw[active])
            factor = remaining / denominator
            next_capped = active & (raw * factor > 1)
            if not np.any(next_capped):
                break
            capped |= next_capped
            active &= ~next_capped
            remaining = target - _stable_sum(w[capped])
        result[free] = np.minimum(1, raw[free] * factor)
        capped[free] = raw[free] * factor > 1

    probabilities = result.astype(float)
    applied_deaths = _stable_sum(w * probabilities)
    residual = baseline_deaths - applied_deaths
    if not infeasible and not np.any(capped):
        residual = np.longdouble(0)
    return probabilities, {
        "weight": _stable_sum(w),
        "fixed_weight": _stable_sum(w[is_fixed]),
        "baseline_expected_deaths": baseline_deaths,
        "applied_expected_deaths": applied_deaths,
        "factor": factor,
        "clipped_persons": int(np.count_nonzero(capped)),
        "clipping_residual": residual,
        "infeasible": infeasible,
    }


def _vector(value, name: str, size: int | None = None) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or (size is not None and len(array) != size):
        raise ValueError(f"{name} must be a one-dimensional matching array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def normalize_probabilities(
    q_base: np.ndarray,
    relative_risk: np.ndarray,
    fixed_mask: np.ndarray,
    fixed_probabilities: np.ndarray,
    cell_ids: Sequence[tuple[int, str, int]],
    weights: np.ndarray,
    *,
    unclassified_counts: Mapping[str, np.ndarray] | None = None,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Normalize risks to baseline weighted expected deaths in each cell.

    Free rows receive ``min(1, q_base * relative_risk * factor)``.  The
    factor is recomputed after each capped group until the remaining
    target can be allocated without further capping.  Zero-weight rows
    receive the same factor as other rows but do not affect its value.

    Fixed probabilities above the entire baseline target are infeasible;
    free probabilities are then zero.  A target above the free rows'
    positive-probability support is also infeasible; those rows saturate
    at one.  The signed residual is baseline minus applied deaths.  On
    feasible cells without capping it is explicitly zero: arithmetic
    roundoff is covered by the accounting tolerance, rather than being
    described as a clipping loss.

    All relative risks must be finite and strictly positive, including
    those on fixed rows.  Probabilities lie in [0, 1], weights are finite
    and nonnegative, and each cell id is a (year, sex, age) triple.
    Optional per-row unclassified counts are summed into each cell log.
    No input array is mutated and no randomness is consumed.
    """
    baseline = _vector(q_base, "baseline probabilities")
    size = len(baseline)
    risk = _vector(relative_risk, "relative risks", size)
    fixed_q = _vector(fixed_probabilities, "fixed probabilities", size)
    weight = _vector(weights, "weights", size)
    fixed = np.asarray(fixed_mask)
    if fixed.ndim != 1 or len(fixed) != size or fixed.dtype.kind != "b":
        raise ValueError("fixed_mask must be a matching boolean array")
    if np.any((baseline < 0) | (baseline > 1)):
        raise ValueError("baseline probabilities must lie in [0, 1]")
    if np.any((fixed_q < 0) | (fixed_q > 1)):
        raise ValueError("fixed probabilities must lie in [0, 1]")
    if np.any(risk <= 0):
        raise ValueError("relative risks must be strictly positive")
    if np.any(weight < 0):
        raise ValueError("weights must be nonnegative")

    ids = list(cell_ids)
    if len(ids) != size:
        raise ValueError("cell_ids must match the input arrays")
    groups: dict[tuple, list[int]] = {}
    for index, cell in enumerate(ids):
        if not isinstance(cell, (tuple, list, np.ndarray)) or len(cell) != 3:
            raise ValueError("cell ids must be (year, sex, age) triples")
        key = tuple(cell)
        if any(pd.isna(value) for value in key):
            raise ValueError("cell ids must not contain missing values")
        try:
            groups.setdefault(key, []).append(index)
        except TypeError as error:
            raise ValueError(
                "cell ids must contain hashable values"
            ) from error

    counts = {
        "unclassified_refuse": np.zeros(size, dtype=np.int64),
        "unclassified_reference": np.zeros(size, dtype=np.int64),
    }
    for name, values in (unclassified_counts or {}).items():
        if not isinstance(name, str) or (
            name in CELL_LOG_COLUMNS and name not in counts
        ):
            raise ValueError(
                "unclassified count names must be distinct log columns"
            )
        array = _vector(values, f"{name} counts", size)
        if np.any(array < 0) or np.any(array != np.floor(array)):
            raise ValueError(
                "unclassified counts must be nonnegative integers"
            )
        counts[name] = array

    out = baseline.copy()
    logs = []
    for cell in sorted(groups):
        positions = np.asarray(groups[cell], dtype=np.int64)
        base = baseline[positions].astype(np.longdouble)
        rr = risk[positions].astype(np.longdouble)
        w = weight[positions].astype(np.longdouble)
        is_fixed = fixed[positions]
        prescribed = fixed_q[positions].astype(np.longdouble)
        out[positions], accounting = _normalize_cell(
            base, rr, w, is_fixed, prescribed
        )
        row = dict(
            zip(("year", "sex", "age"), cell, strict=True),
            persons=len(positions),
            fixed_persons=int(np.count_nonzero(is_fixed)),
            **accounting,
        )
        row.update(
            {
                name: int(fsum(values[positions]))
                for name, values in counts.items()
            }
        )
        logs.append(row)
    columns = list(CELL_LOG_COLUMNS) + [
        name for name in counts if name not in CELL_LOG_COLUMNS
    ]
    return out, pd.DataFrame(logs, columns=columns)
