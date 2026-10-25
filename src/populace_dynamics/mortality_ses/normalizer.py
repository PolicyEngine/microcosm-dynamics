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
    "normalization_basis",
    "persons_target",
    "unclassified_refuse",
    "unclassified_reference",
)

# The float path leaves a cell to the Decimal path when cancellation
# leaves too little to compute reliably: a target within this relative
# margin m of zero or of capacity, or a capping round that leaves a
# remaining target within it of zero, relative to the totals the target
# is taken from.  Each total errs by at most about 4u of the totals it
# sums (u = 2**-53), so outside the margin the factor and every returned
# probability err by at most about 12u/m, roughly 1.3e-12, relative.
_FLOAT_MARGIN = 1e-3
# Under that error a row whose scaled probability is this close to one
# may cap or not, and which it does decides the factor every other row
# gets, or, for a zero-allocation row, the log's clipped count.  Such a
# cell also goes to the Decimal path.  The margin is far above the error
# bound, so every other cap decision and clip count is the exact one.
_CAP_MARGIN = 1e-9
# A feasible float cell that misses conservation by more than this,
# relative to its expected deaths, is recomputed on the Decimal path.
_CONSERVATION_RTOL = 1e-12


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
    scaled = (values / maximum).astype(np.float64).tolist()
    return maximum * np.longdouble(fsum(scaled))


def _ambiguous(difference, scale) -> bool:
    """Whether a float difference is too close to zero to decide on."""
    return bool(scale > 0 and abs(difference) <= _FLOAT_MARGIN * scale)


def _decimal_cell(base, rr, w, is_fixed, prescribed):
    """Handle extreme or ambiguous cells without platform assumptions.

    On some supported platforms ``longdouble`` has float64's exponent
    range.  Decimal's exponent range retains positive q*RR support even
    when that product would underflow, and avoids overflowing products.
    Its precision also settles the comparisons and cancellations that the
    float path refers here.  This slower path is used only for those
    cells.
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
        allocation = w
        persons_target = None
        if target == zero and support and total(w[i] for i in support) == zero:
            allocation = [one] * len(w)
            target = persons_target = total(base[i] for i in support)
        capacity = total(allocation[i] for i in support)
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
        elif target > capacity:
            infeasible = True
            for i in support:
                result[i] = one
            capped = set(support)
            factor = max(
                (one / (base[i] * rr[i]) for i in support), default=one
            )
        elif target == capacity:
            # Any factor that caps the whole weighted support conserves the
            # cell.  The smallest is the capping loop's limit as the target
            # rises to capacity; zero-allocation rows take it too.
            weighted = [i for i in support if allocation[i] > zero]
            factor = max(one / (base[i] * rr[i]) for i in weighted)
            for i in free:
                result[i] = min(one, base[i] * rr[i] * factor)
            for i in weighted:
                result[i] = one
            capped = {i for i in free if base[i] * rr[i] * factor > one}
        else:
            raw = [qi * ri for qi, ri in zip(base, rr, strict=True)]
            active = {i for i in support if allocation[i] > zero}
            remaining = target
            while active:
                factor = remaining / total(
                    allocation[i] * raw[i] for i in active
                )
                next_capped = {i for i in active if raw[i] * factor > one}
                if not next_capped:
                    break
                capped |= next_capped
                active -= next_capped
                remaining = target - total(allocation[i] for i in capped)
            for i in free:
                result[i] = one if i in capped else min(one, raw[i] * factor)
            capped |= {i for i in free if raw[i] * factor > one}
        probabilities = np.asarray([float(value) for value in result])
        applied = total(
            wi * Decimal.from_float(float(qi))
            for wi, qi in zip(w, probabilities, strict=True)
        )
        # Feasible cells conserve exactly; only the conversion of the
        # returned probabilities to float64 rounds.
        residual = baseline_deaths - applied if infeasible else zero
        return probabilities, {
            "weight": float(total(w)),
            "fixed_weight": float(total(w[i] for i in fixed)),
            "baseline_expected_deaths": float(baseline_deaths),
            "applied_expected_deaths": float(applied),
            "factor": float(factor),
            "clipped_persons": len(capped),
            "clipping_residual": float(residual),
            "infeasible": infeasible,
            "normalization_basis": (
                "weights" if persons_target is None else "persons"
            ),
            "persons_target": (
                float("nan")
                if persons_target is None
                else float(persons_target)
            ),
        }


def _normalize_cell(base, rr, w, is_fixed, prescribed):
    def exact():
        return _decimal_cell(base, rr, w, is_fixed, prescribed)

    # Within these magnitudes, coefficients, weighted products, and capped
    # scaling products remain representable even on float64-only platforms.
    if any(
        np.any((values > 0) & (values < 1e-80)) or np.any(values > 1e80)
        for values in (base, rr, w, prescribed)
    ):
        return exact()
    free = ~is_fixed
    result = np.zeros(len(base), dtype=np.longdouble)
    result[is_fixed] = prescribed[is_fixed]
    baseline_deaths = _stable_sum(w * base)
    fixed_deaths = _stable_sum(w[is_fixed] * prescribed[is_fixed])
    fixed_at_baseline = np.array_equal(prescribed[is_fixed], base[is_fixed])
    # ``scale`` is the size of the totals the target is taken from, which
    # bounds its rounding error.
    if fixed_at_baseline:
        # Avoid cancellation of small free totals when fixed rows dominate.
        target = scale = _stable_sum(w[free] * base[free])
    else:
        target = baseline_deaths - fixed_deaths
        scale = max(baseline_deaths, fixed_deaths)
        if _ambiguous(target, scale):
            return exact()
    support = free & (base > 0)
    # Weightless support leaves a zero weighted target silent on the
    # factor: every factor conserves the cell.  Count persons equally to
    # set it, rather than letting zero weight decide a probability.
    allocation = w
    persons_target = None
    if target == 0 and np.any(support) and _stable_sum(w[support]) == 0:
        allocation = np.ones(len(base), dtype=np.longdouble)
        target = persons_target = scale = _stable_sum(base[support])
    capacity = _stable_sum(allocation[support])
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
    elif _ambiguous(target - capacity, capacity):
        return exact()
    elif target > capacity:
        # Ties went to the Decimal path, so this cell is infeasible.
        infeasible = True
        result[support] = 1
        capped[support] = True
        factor = (
            np.max(1 / (base[support] * rr[support]))
            if np.any(support)
            else np.longdouble(1)
        )
    else:
        raw = base * rr
        active = support & (allocation > 0)
        remaining = target
        while np.any(active):
            denominator = _stable_sum(allocation[active] * raw[active])
            factor = remaining / denominator
            scaled = raw * factor
            # A row this close to one may be capped or not; which it is
            # decides the factor every other row gets.
            if np.any(active & (np.abs(scaled - 1) <= _CAP_MARGIN)):
                return exact()
            next_capped = active & (scaled > 1)
            if not np.any(next_capped):
                break
            capped |= next_capped
            active &= ~next_capped
            remaining = target - _stable_sum(allocation[capped])
            if remaining <= _FLOAT_MARGIN * scale:
                return exact()
        # The loop checked every row that sets the factor.  Zero-allocation
        # rows take the factor without setting it, so whether one clips
        # changes only the log's count, but that count must be exact too.
        if np.any(free & ~capped & (np.abs(raw * factor - 1) <= _CAP_MARGIN)):
            return exact()
        result[free] = np.minimum(1, raw[free] * factor)
        result[capped] = 1
        capped |= free & (raw * factor > 1)

    probabilities = result.astype(float)
    applied_deaths = _stable_sum(w * probabilities)
    residual = baseline_deaths - applied_deaths
    if not infeasible:
        # Iterative capping conserves every feasible cell, so a material
        # float residual is an arithmetic failure, never a clipping loss.
        if abs(residual) > _CONSERVATION_RTOL * max(
            baseline_deaths, applied_deaths
        ):
            return exact()
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
        "normalization_basis": (
            "weights" if persons_target is None else "persons"
        ),
        "persons_target": (
            float("nan") if persons_target is None else float(persons_target)
        ),
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
    at one.  These rules hold whatever the free rows' weights.  A target
    that exactly fills the weighted support conserves with any factor
    that caps it; the cell takes the smallest such factor, so zero-weight
    rows keep ``min(1, q_base * relative_risk * factor)``.

    When every free row with positive baseline probability has zero
    weight and the weighted target is zero, every factor conserves the
    cell, so the weights cannot set it.  The cell then counts persons
    equally: the factor makes those rows' unweighted expected deaths equal
    their unweighted baseline total, which the log reports as
    ``persons_target`` with ``normalization_basis == "persons"``.  Every
    other cell has basis ``"weights"`` and a missing persons target.
    With fixed rows at baseline, such a cell gets the probabilities it
    would get if every weight were one.

    The log's ``clipped_persons`` counts free rows whose scaled probability
    ``q_base * relative_risk * factor`` exceeds one at the cell's exact
    final factor (the logged ``factor`` approximates it in float64, within
    the stated error bound on the float path, so a row at one can appear
    to exceed it); a row exactly at one is not counted.  In a cell whose
    target exceeds its free capacity, it counts every free row with
    positive baseline probability, since all of them saturate.

    The signed residual is baseline minus applied deaths.  It is nonzero
    only on infeasible cells; iterative capping conserves feasible cells.
    The float path verifies that within the accounting tolerance, and
    recomputes on the Decimal path any cell it cannot decide or conserve
    in float arithmetic.

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
        try:
            groups.setdefault(tuple(cell), []).append(index)
        except TypeError as error:
            raise ValueError(
                "cell ids must contain hashable values"
            ) from error
    # Every row's key is one of the distinct keys, so checking each
    # distinct key once checks every row.
    if any(pd.isna(value) for key in groups for value in key):
        raise ValueError("cell ids must not contain missing values")

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
