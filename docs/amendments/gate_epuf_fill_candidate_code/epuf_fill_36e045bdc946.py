"""Career fills learned from SSA's Earnings Public-Use File (EPUF).

The career assembler (:func:`populace_dynamics.estimates.career.build_career`)
fills the years the PSID did not record with two fixed rules: each odd
income year from 1997 is the mean of its neighbours, and nothing counts
before ``max(1968, birth_year + 22)``. This module holds the learned
replacements registered by ``gate_epuf_fill``
(``docs/amendments/gate_epuf_fill_registration_proposal.md``, section 7),
fitted on the gate's TRAIN persons only:

- :class:`OddQuantileFill` (odd years, primary): a two-part conditional
  draw. The probability of a zero year and the conditional quantiles of a
  positive share, relative to the neighbours' level, by sex, age, the
  shares at ``t-1`` and ``t+1`` and the context at ``t-3``, ``t+3`` and
  further; a Gaussian AR(1) copula correlates a person's draws across
  masked years.
- :class:`OddKnnFill` (odd years, alternative): the share at ``t`` copied
  from one of the ``k`` nearest TRAIN person-years in the shares at ``t-1``
  and ``t+1``, by sex and age.
- :class:`PreDonorFill` (pre-career years, primary): rank-kNN donor
  careers. The whole masked block is copied from one of the ``k`` TRAIN
  donors of the same sex and birth year nearest in percentile rank over
  the first five recorded years.
- :class:`PreChainFill` (pre-career years, alternative): a chained
  one-sided draw of year ``y`` given year ``y+1``, sex and age, backward
  from the career start.

Every fill works on **shares**: capped earnings over the year's wage base,
in [0, 1], NaN where a year is unknown. It fills only the cells of
``fill_mask`` and leaves every other cell as given. Draws come from
counter-based uniforms keyed by the fill, the draw seed, the person key and
the year (:func:`hash_uniform`), so a person's draw never depends on which
other persons are filled or in what order.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.special import ndtr, ndtri

__all__ = [
    "BySexFill",
    "FILL_CLASSES",
    "OddForestFill",
    "OddKnnFill",
    "OddQuantileFill",
    "PreChainFill",
    "PreDonorFill",
    "block_first_year",
    "career_start",
    "hash_uniform",
    "load_fill",
    "odd_context",
]

CAREER_FIRST_YEAR = 1968
CAREER_START_AGE = 22
#: EPUF has no earnings below this age for cohorts born after 1937.
FIRST_EARNING_AGE = 15
QUANTILE_POINTS = 65
MIN_CELL = 200

_MASK64 = np.uint64(0xFFFFFFFFFFFFFFFF)
_GOLDEN = np.uint64(0x9E3779B97F4A7C15)
_MIX1 = np.uint64(0xBF58476D1CE4E5B9)
_MIX2 = np.uint64(0x94D049BB133111EB)


def _splitmix64(values: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        z = values.astype(np.uint64) + _GOLDEN
        z = (z ^ (z >> np.uint64(30))) * _MIX1
        z = (z ^ (z >> np.uint64(27))) * _MIX2
        return z ^ (z >> np.uint64(31))


def _tag(name: str) -> np.uint64:
    digest = hashlib.sha256(name.encode()).digest()[:8]
    return np.uint64(int.from_bytes(digest, "big"))


def hash_uniform(
    stream: str, seed: int, person_key: np.ndarray, year: np.ndarray
) -> np.ndarray:
    """Uniforms in (0, 1) keyed by stream, seed, person and year.

    A splitmix64 chain over ``(stream tag XOR seed, person key, year)``;
    broadcasting ``person_key`` against ``year`` gives one uniform per
    person-year.
    """

    person_key = np.asarray(person_key, dtype=np.int64).astype(np.uint64)
    year = np.asarray(year, dtype=np.int64).astype(np.uint64)
    base = _splitmix64(np.asarray(_tag(stream) ^ np.uint64(seed)))
    with np.errstate(over="ignore"):
        state = _splitmix64(base ^ person_key)
        state = _splitmix64(state ^ (year * _GOLDEN))
    return ((state >> np.uint64(11)).astype(np.float64) + 0.5) / 2.0**53


def career_start(birth_year: np.ndarray) -> np.ndarray:
    """The assembler's first career year, ``max(1968, birth_year + 22)``."""

    return np.maximum(
        CAREER_FIRST_YEAR, np.asarray(birth_year, dtype=np.int64) + 22
    )


def _age_band(age: np.ndarray) -> np.ndarray:
    """0 below 15; 1 for 15-19 through 14 for 80-84; 15 from 85."""

    age = np.asarray(age, dtype=np.int64)
    return np.where(age < 15, 0, np.minimum((age - 15) // 5 + 1, 15))


def _column_of(years: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Column of each target year, -1 outside the matrix's years."""

    years = np.asarray(years, dtype=np.int64)
    target = np.asarray(target, dtype=np.int64)
    column = target - years[0]
    return np.where((column >= 0) & (column < len(years)), column, -1)


def _take(shares: np.ndarray, rows: np.ndarray, column: np.ndarray):
    """Shares at (row, column), NaN where the column is -1."""

    safe = np.maximum(column, 0)
    out = shares[rows, safe]
    return np.where(column >= 0, out, np.nan)


def _quantile_table(
    keys: np.ndarray, values: np.ndarray, points: int = QUANTILE_POINTS
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per key: sorted unique keys, counts, and ``points`` quantiles.

    The quantiles are at levels ``j / (points - 1)`` with linear
    interpolation, so they include each key's minimum and maximum.
    """

    order = np.lexsort((values, keys))
    keys = keys[order]
    values = values[order]
    unique, start, count = np.unique(
        keys, return_index=True, return_counts=True
    )
    levels = np.linspace(0.0, 1.0, points)
    position = levels[None, :] * (count[:, None] - 1)
    low = np.floor(position).astype(np.int64)
    high = np.minimum(low + 1, count[:, None] - 1)
    weight = position - low
    base = start[:, None]
    table = (1.0 - weight) * values[base + low] + weight * values[base + high]
    return unique, count, table.astype(np.float32)


def _lookup(table_keys: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Index of each key in sorted ``table_keys``, -1 where absent."""

    if len(table_keys) == 0:
        return np.full(len(keys), -1, dtype=np.int64)
    position = np.searchsorted(table_keys, keys)
    position = np.minimum(position, len(table_keys) - 1)
    return np.where(table_keys[position] == keys, position, -1)


def _interpolate(table: np.ndarray, rows: np.ndarray, level: np.ndarray):
    """Row-wise linear interpolation of quantile tables at levels in [0, 1]."""

    points = table.shape[1]
    position = np.clip(level, 0.0, 1.0) * (points - 1)
    low = np.minimum(np.floor(position).astype(np.int64), points - 2)
    weight = position - low
    return (1.0 - weight) * table[rows, low] + weight * table[rows, low + 1]


def _invert(table: np.ndarray, rows: np.ndarray, value: np.ndarray):
    """The level at which each row's quantile function reaches ``value``.

    Where the function is flat at ``value`` (a run of equal quantiles), the
    middle of the run's levels.
    """

    points = table.shape[1]
    levels = np.linspace(0.0, 1.0, points)
    out = np.empty(len(rows))
    for start in range(0, len(rows), 200_000):
        block = slice(start, start + 200_000)
        curve = table[rows[block]].astype(np.float64)
        target = np.asarray(value[block], dtype=np.float64)[:, None]
        below = (curve < target).sum(axis=1)
        above = (curve <= target).sum(axis=1)
        flat = below < above
        result = np.empty(len(curve))
        result[above == 0] = 0.0
        result[below >= points] = 1.0
        middle = flat & (above > 0) & (below < points)
        result[middle] = 0.5 * (
            levels[below[middle]] + levels[above[middle] - 1]
        )
        between = ~flat & (below > 0) & (below < points)
        index = np.flatnonzero(between)
        left = curve[index, below[index] - 1]
        right = curve[index, below[index]]
        share = np.where(
            right > left,
            (target[index, 0] - left)
            / np.where(right > left, right - left, 1),
            0.5,
        )
        result[index] = levels[below[index] - 1] + share * (
            levels[below[index]] - levels[below[index] - 1]
        )
        out[block] = result
    return out


def _to_npz(arrays: Mapping[str, np.ndarray]) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Odd years: the context of a masked unit
# --------------------------------------------------------------------------
#: Offsets whose positivity forms the wider context ``W``.
_WIDE_OFFSETS = (-9, -7, -5, 5, 7, 9)


@dataclass(frozen=True)
class OddContext:
    """The recorded neighbourhood of masked units (one row per unit)."""

    left: np.ndarray
    right: np.ndarray
    left3: np.ndarray
    right3: np.ndarray
    wide: np.ndarray
    sex: np.ndarray
    age: np.ndarray
    wide_mean: np.ndarray
    wide_positive: np.ndarray
    wide_known: np.ndarray
    year: np.ndarray


def odd_context(
    shares: np.ndarray,
    years: np.ndarray,
    rows: np.ndarray,
    unit_year: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    known: np.ndarray,
) -> OddContext:
    """Neighbour shares of units ``(rows, unit_year)``; NaN where unknown.

    ``known`` (persons by years) flags the cells a fill may read: recorded
    and not masked. ``wide`` is 1 if any known share at offsets 5, 7 or 9
    on either side is positive.
    """

    readable = np.where(known, shares, np.nan)

    def at(offset: int) -> np.ndarray:
        return _take(readable, rows, _column_of(years, unit_year + offset))

    wide = np.zeros(len(rows), dtype=np.int64)
    total = np.zeros(len(rows))
    positive = np.zeros(len(rows))
    count = np.zeros(len(rows))
    for offset in _WIDE_OFFSETS:
        value = at(offset)
        known_value = np.isfinite(value)
        is_positive = np.nan_to_num(value, nan=0.0) > 0
        wide |= is_positive.astype(np.int64)
        count += known_value
        positive += is_positive
        total += np.where(is_positive, value, 0.0)
    return OddContext(
        left=at(-1),
        right=at(1),
        left3=at(-3),
        right3=at(3),
        wide=wide,
        sex=np.asarray(sex)[rows].astype(np.int64),
        age=unit_year - np.asarray(birth_year)[rows],
        wide_mean=np.where(
            positive > 0, total / np.maximum(positive, 1), -1.0
        ),
        wide_positive=np.where(
            count > 0, positive / np.maximum(count, 1), -1.0
        ),
        wide_known=count,
        year=np.asarray(unit_year, dtype=np.int64),
    )


# --------------------------------------------------------------------------
# Odd years, primary: the two-part conditional draw
# --------------------------------------------------------------------------
_N_SHARE_BINS = 20


def _share_bin(value: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """0 zero, 1..20 quantile bins of a positive share below the cap, 21 cap."""

    bins = np.searchsorted(edges, value, side="right") + 1
    bins = np.where(value <= 0, 0, bins)
    return np.where(value >= 1.0, _N_SHARE_BINS + 1, bins)


def _coarse_age(band: np.ndarray) -> np.ndarray:
    """Age bands grouped: under 30, 30-44, 45-59, 60 and over."""

    return np.digitize(band, [4, 7, 10])


@dataclass(frozen=True)
class OddQuantileFill:
    """Two-part conditional draw for masked odd years, with an AR(1) copula.

    A unit's reference level ``m`` is the geometric mean of its positive
    neighbours' shares (the one positive neighbour's share if only one is,
    1 if neither is). Its cell is the finest of seven nested keys with at
    least ``MIN_CELL`` TRAIN units, built from sex, five-year age band, the
    bins of the shares at ``t-1`` and ``t+1`` (zero, 20 quantile bins of a
    positive share below the cap, at the cap), the context at ``t-3`` and
    ``t+3`` (missing, zero, below or above the median positive share), and
    whether any share at offsets 5, 7 or 9 is positive. In the cell: ``p0``
    the share of zero years, and 65 quantiles of ``log(x_t / m)`` among
    positive years. A uniform ``u`` maps to zero if ``u < p0``, else to
    ``min(m * exp(Q((u - p0) / (1 - p0))), 1)``. The uniforms of a person's
    consecutive masked years (two years apart) are joined by a Gaussian
    AR(1) copula with correlation ``rho`` by sex and age band, learned on
    TRAIN from the probability integral transforms of consecutive units.
    """

    share_edges: np.ndarray
    context_median: float
    level_keys: tuple[np.ndarray, ...]
    level_p0: tuple[np.ndarray, ...]
    level_quantiles: tuple[np.ndarray, ...]
    rho: np.ndarray
    stream: str = "epuf_fill.odd_quantile.v1"
    name: str = "odd_quantile"

    # -- keys ---------------------------------------------------------------
    @staticmethod
    def _parts(context: OddContext, share_edges, median):
        left = np.nan_to_num(context.left, nan=-1.0)
        right = np.nan_to_num(context.right, nan=-1.0)
        # A missing neighbour takes the other's value (the PSID fallback).
        left = np.where(left < 0, right, left)
        right = np.where(right < 0, left, right)
        positive_left = np.where(left > 0, left, 1.0)
        positive_right = np.where(right > 0, right, 1.0)
        level = np.where(
            (left > 0) & (right > 0),
            np.sqrt(positive_left * positive_right),
            np.where(left > 0, positive_left, positive_right),
        )

        def context_code(value):
            return np.where(
                np.isnan(value),
                0,
                np.where(value <= 0, 1, np.where(value < median, 2, 3)),
            )

        return {
            "sex": context.sex,
            "age": _age_band(context.age),
            "left_bin": _share_bin(left, share_edges),
            "right_bin": _share_bin(right, share_edges),
            "context3": 4 * context_code(context.left3)
            + context_code(context.right3),
            "wide": context.wide,
            "level": level,
            "valid": ~(np.isnan(context.left) & np.isnan(context.right)),
        }

    @staticmethod
    def _keys(parts) -> list[np.ndarray]:
        sex = parts["sex"]
        age = parts["age"]
        coarse = _coarse_age(age)
        left = parts["left_bin"]
        right = parts["right_bin"]
        context3 = parts["context3"]
        wide = parts["wide"]

        # Nested keys from finest to coarsest; a dropped component is held
        # at a sentinel (age 16-20 marks the coarse bands, 21 none).
        def key(s, a, lb, rb, c3, w):
            return ((((s * 22 + a) * 23 + lb) * 23 + rb) * 17 + c3) * 3 + w

        return [
            key(sex, age, left, right, context3, wide),
            key(sex, age, left, right, context3, 2),
            key(sex, age, left, right, 16, 2),
            key(sex, 16 + coarse, left, right, 16, 2),
            key(sex, 21, left, right, 16, 2),
            key(0 * sex, 21, left, right, 16, 2),
            key(0 * sex, 21, np.minimum(left, 1), np.minimum(right, 1), 16, 2),
        ]

    def _cells(self, parts) -> tuple[np.ndarray, np.ndarray]:
        """(level, row) of each unit's finest populated cell."""

        keys = self._keys(parts)
        level = np.full(len(keys[0]), -1, dtype=np.int64)
        row = np.full(len(keys[0]), -1, dtype=np.int64)
        for index, key in enumerate(keys):
            found = _lookup(self.level_keys[index], key)
            take = (level < 0) & (found >= 0)
            level[take] = index
            row[take] = found[take]
        if (level < 0).any():
            raise ValueError("a unit has no populated cell at any level")
        return level, row

    def _quantile(self, parts, u: np.ndarray) -> np.ndarray:
        level, row = self._cells(parts)
        out = np.zeros(len(u))
        for index in np.unique(level):
            take = level == index
            p0 = self.level_p0[index][row[take]]
            positive = u[take] >= p0
            v = np.where(
                positive, (u[take] - p0) / np.maximum(1.0 - p0, 1e-12), 0.0
            )
            residual = _interpolate(self.level_quantiles[index], row[take], v)
            share = np.minimum(parts["level"][take] * np.exp(residual), 1.0)
            out[take] = np.where(positive, share, 0.0)
        return out

    # -- fitting --------------------------------------------------------------
    @classmethod
    def fit(
        cls,
        shares: np.ndarray,
        years: np.ndarray,
        birth_year: np.ndarray,
        sex: np.ndarray,
        unit_years: tuple[int, ...],
        rho_seed: int = 0,
    ) -> tuple[OddQuantileFill, dict[str, object]]:
        """Fit on complete TRAIN shares; every year of ``unit_years`` a unit.

        Every person-year of ``unit_years`` whose two neighbours are inside
        the matrix is a training unit (all years are recorded on TRAIN).
        """

        shares = np.asarray(shares, dtype=np.float64)
        known = np.isfinite(shares)
        n = len(shares)
        rows_list, years_list = [], []
        for year in unit_years:
            rows_list.append(np.arange(n))
            years_list.append(np.full(n, year))
        rows = np.concatenate(rows_list)
        unit_year = np.concatenate(years_list)
        context = odd_context(
            shares, years, rows, unit_year, birth_year, sex, known
        )
        target = _take(shares, rows, _column_of(years, unit_year))
        neighbours = np.concatenate([context.left, context.right])
        inside = neighbours[(neighbours > 0) & (neighbours < 1.0)]
        share_edges = np.quantile(
            inside, np.linspace(0, 1, _N_SHARE_BINS + 1)[1:-1]
        )
        median = float(np.median(inside))
        parts = cls._parts(context, share_edges, median)
        keys = cls._keys(parts)
        positive = target > 0
        residual = np.log(np.where(positive, target, 1.0)) - np.log(
            parts["level"]
        )
        level_keys, level_p0, level_quantiles = [], [], []
        for key in keys:
            unique, count = np.unique(key, return_counts=True)
            populated = unique[count >= MIN_CELL]
            in_cells = np.isin(key, populated)
            zeros_unique, zeros = np.unique(
                key[in_cells & ~positive], return_counts=True
            )
            totals = count[count >= MIN_CELL]
            p0 = np.zeros(len(populated))
            p0[np.searchsorted(populated, zeros_unique)] = zeros
            p0 = p0 / totals
            q_keys, _, table = _quantile_table(
                key[in_cells & positive], residual[in_cells & positive]
            )
            # A populated cell with no positive unit draws only zeros.
            full = np.zeros((len(populated), QUANTILE_POINTS), np.float32)
            full[np.searchsorted(populated, q_keys)] = table
            level_keys.append(populated.astype(np.int64))
            level_p0.append(p0.astype(np.float64))
            level_quantiles.append(full)
        provisional = cls(
            share_edges=share_edges,
            context_median=median,
            level_keys=tuple(level_keys),
            level_p0=tuple(level_p0),
            level_quantiles=tuple(level_quantiles),
            rho=np.zeros((4, 16)),
        )
        rho, rho_diagnostics = provisional._fit_rho(
            parts, target, rows, unit_year, rho_seed
        )
        fill = cls(
            share_edges=share_edges,
            context_median=median,
            level_keys=tuple(level_keys),
            level_p0=tuple(level_p0),
            level_quantiles=tuple(level_quantiles),
            rho=rho,
        )
        cells = [len(k) for k in level_keys]
        return fill, {
            "n_units": int(len(target)),
            "cells_per_level": cells,
            **rho_diagnostics,
        }

    def _pit(self, parts, target, rows, unit_year, seed) -> np.ndarray:
        """Randomised probability integral transforms of true shares."""

        level, row = self._cells(parts)
        jitter = hash_uniform(
            "epuf_fill.odd_quantile.pit", seed, rows, unit_year
        )
        out = np.empty(len(target))
        for index in np.unique(level):
            take = np.flatnonzero(level == index)
            p0 = self.level_p0[index][row[take]]
            zero = target[take] <= 0
            out[take[zero]] = jitter[take[zero]] * p0[zero]
            positive = take[~zero]
            residual = np.log(target[positive]) - np.log(
                parts["level"][positive]
            )
            # At the cap the residual is censored: spread it over the mass
            # the quantile function puts at or above the cap.
            at_cap = target[positive] >= 1.0
            v = _invert(self.level_quantiles[index], row[positive], residual)
            cap_v = v.copy()
            cap_v[at_cap] = v[at_cap] + jitter[positive][at_cap] * (
                1.0 - v[at_cap]
            )
            p0_positive = p0[~zero]
            out[positive] = p0_positive + (1.0 - p0_positive) * cap_v
        return np.clip(out, 1e-9, 1.0 - 1e-9)

    def _fit_rho(self, parts, target, rows, unit_year, seed):
        """AR(1) correlation of consecutive units' normal scores (t, t+2).

        On a 5 percent sample of persons (by seed): every unit's
        probability integral transform under the fitted cells, its normal
        score, and the correlation of the scores of ``t`` and ``t+2`` for
        the same person, by sex and age band at ``t``.
        """

        persons = np.unique(rows)
        rng = np.random.default_rng(seed)
        chosen = persons[rng.random(len(persons)) < 0.05]
        index = np.flatnonzero(np.isin(rows, chosen))
        sub = {k: v[index] for k, v in parts.items()}
        z = ndtri(
            self._pit(sub, target[index], rows[index], unit_year[index], seed)
        )
        first_year = int(unit_year.min())
        n_years = int(unit_year.max()) - first_year + 1
        position = np.searchsorted(chosen, rows[index])
        grid = np.full((len(chosen), n_years), np.nan)
        grid[position, unit_year[index] - first_year] = z
        sex_grid = np.zeros((len(chosen), n_years), dtype=np.int64)
        sex_grid[position, unit_year[index] - first_year] = sub["sex"]
        age_grid = np.zeros((len(chosen), n_years), dtype=np.int64)
        age_grid[position, unit_year[index] - first_year] = sub["age"]
        now = grid[:, :-2].ravel()
        later = grid[:, 2:].ravel()
        sex = sex_grid[:, :-2].ravel()
        age = age_grid[:, :-2].ravel()
        both = np.isfinite(now) & np.isfinite(later)
        rho = np.zeros((4, 16))
        for s in (1, 2):
            for a in range(16):
                take = both & (sex == s) & (age == a)
                if take.sum() >= MIN_CELL:
                    rho[s, a] = np.corrcoef(now[take], later[take])[0, 1]
        overall = float(np.corrcoef(now[both], later[both])[0, 1])
        four_now = grid[:, :-4].ravel()
        four_later = grid[:, 4:].ravel()
        four = np.isfinite(four_now) & np.isfinite(four_later)
        lag4 = float(np.corrcoef(four_now[four], four_later[four])[0, 1])
        return rho, {
            "rho_persons": int(len(chosen)),
            "rho_pairs": int(both.sum()),
            "rho_overall": overall,
            "lag4_normal_score_correlation": lag4,
            "lag4_ar1_prediction": overall**2,
        }

    # -- filling --------------------------------------------------------------
    def fill(
        self,
        shares: np.ndarray,
        years: np.ndarray,
        birth_year: np.ndarray,
        sex: np.ndarray,
        person_key: np.ndarray,
        fill_mask: np.ndarray,
        seed: int,
    ) -> np.ndarray:
        """Fill the masked cells; masked cells with no known neighbour stay NaN."""

        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        known = np.isfinite(shares) & ~fill_mask
        out = np.where(fill_mask, np.nan, shares)
        latent = np.full(len(shares), np.nan)
        last_year = np.full(len(shares), -10, dtype=np.int64)
        for column in np.flatnonzero(fill_mask.any(axis=0)):
            year = int(years[column])
            rows = np.flatnonzero(fill_mask[:, column])
            unit_year = np.full(len(rows), year)
            context = odd_context(
                shares, years, rows, unit_year, birth_year, sex, known
            )
            parts = self._parts(context, self.share_edges, self.context_median)
            epsilon = ndtri(
                hash_uniform(self.stream, seed, person_key[rows], unit_year)
            )
            rho = self.rho[np.clip(parts["sex"], 0, 3), parts["age"]]
            follows = last_year[rows] == year - 2
            z = np.where(
                follows,
                rho * np.nan_to_num(latent[rows])
                + np.sqrt(1.0 - rho**2) * epsilon,
                epsilon,
            )
            valid = parts["valid"]
            drawn = np.full(len(rows), np.nan)
            if valid.any():
                sub = {k: v[valid] for k, v in parts.items()}
                drawn[valid] = self._quantile(sub, ndtr(z[valid]))
            out[rows, column] = drawn
            latent[rows] = np.where(valid, z, np.nan)
            last_year[rows] = np.where(valid, year, -10)
        return out

    # -- persistence ----------------------------------------------------------
    def to_bytes(self) -> bytes:
        arrays = {
            "kind": np.array(self.name),
            "share_edges": self.share_edges,
            "context_median": np.array(self.context_median),
            "rho": self.rho,
        }
        for index, (k, p, q) in enumerate(
            zip(
                self.level_keys,
                self.level_p0,
                self.level_quantiles,
                strict=True,
            )
        ):
            arrays[f"keys_{index}"] = k
            arrays[f"p0_{index}"] = p
            arrays[f"quantiles_{index}"] = q
        return _to_npz(arrays)

    @classmethod
    def from_arrays(cls, arrays) -> OddQuantileFill:
        n_levels = sum(1 for name in arrays.files if name.startswith("keys_"))
        return cls(
            share_edges=arrays["share_edges"],
            context_median=float(arrays["context_median"]),
            level_keys=tuple(arrays[f"keys_{i}"] for i in range(n_levels)),
            level_p0=tuple(arrays[f"p0_{i}"] for i in range(n_levels)),
            level_quantiles=tuple(
                arrays[f"quantiles_{i}"] for i in range(n_levels)
            ),
            rho=arrays["rho"],
        )


# --------------------------------------------------------------------------
# Odd years, primary: a quantile regression forest (QRF) draw
# --------------------------------------------------------------------------


def odd_features(context: OddContext) -> np.ndarray:
    """Forest features of masked units; -1 marks an unknown share.

    Sex, age, the shares at ``t-1`` and ``t+1`` (a missing one takes the
    other's value, and a flag records it), at ``t-3`` and ``t+3``; the
    mean, the geometric mean of the positive ones, and the number positive
    of the known shares among those four; the mean positive share and the
    share of positive years among the known shares at offsets 5, 7 and 9
    on both sides, and the number of those known.
    """

    left = context.left
    right = context.right
    missing = np.isnan(left) | np.isnan(right)
    left = np.where(np.isnan(left), right, left)
    right = np.where(np.isnan(right), context.left, right)
    near = np.column_stack([left, right, context.left3, context.right3])
    known = np.isfinite(near)
    values = np.where(known, near, 0.0)
    count = known.sum(axis=1)
    positive = (values > 0) & known
    n_positive = positive.sum(axis=1)
    mean = np.where(count > 0, values.sum(axis=1) / np.maximum(count, 1), -1)
    log_positive = np.where(positive, np.log(np.where(positive, values, 1)), 0)
    geometric = np.where(
        n_positive > 0,
        np.exp(log_positive.sum(axis=1) / np.maximum(n_positive, 1)),
        -1.0,
    )
    return np.column_stack(
        [
            context.sex.astype(np.float64),
            context.age.astype(np.float64),
            np.nan_to_num(left, nan=-1.0),
            np.nan_to_num(right, nan=-1.0),
            missing.astype(np.float64),
            np.nan_to_num(context.left3, nan=-1.0),
            np.nan_to_num(context.right3, nan=-1.0),
            mean,
            geometric,
            n_positive.astype(np.float64),
            context.wide_mean,
            context.wide_positive,
            context.wide_known,
            context.year.astype(np.float64),
        ]
    ).astype(np.float32)


#: The reference level of a unit with no positive share around it.
_DEFAULT_LEVEL = 0.3


def reference_level(context: OddContext) -> np.ndarray:
    """The level a unit's share is drawn relative to.

    The geometric mean of the positive shares at ``t-1`` and ``t+1``; else
    of those at ``t-3`` and ``t+3``; else the mean positive share at
    offsets 5-9; else 0.3.
    """

    def geometric(a, b):
        a = np.nan_to_num(a, nan=0.0)
        b = np.nan_to_num(b, nan=0.0)
        both = (a > 0) & (b > 0)
        one = np.where(a > 0, a, b)
        value = np.where(both, np.sqrt(np.where(both, a * b, 1.0)), one)
        return np.where((a > 0) | (b > 0), value, np.nan)

    level = geometric(context.left, context.right)
    level = np.where(
        np.isnan(level), geometric(context.left3, context.right3), level
    )
    level = np.where(
        np.isnan(level) & (context.wide_mean > 0), context.wide_mean, level
    )
    return np.where(np.isnan(level), _DEFAULT_LEVEL, level)


def _tree_leaves(
    left: np.ndarray,
    right: np.ndarray,
    feature: np.ndarray,
    threshold: np.ndarray,
    x: np.ndarray,
) -> np.ndarray:
    """Leaf node of each row, following ``x[feature] <= threshold`` left."""

    node = np.zeros(len(x), dtype=np.int64)
    while True:
        internal = left[node] >= 0
        if not internal.any():
            return node
        rows = np.flatnonzero(internal)
        current = node[rows]
        go_left = x[rows, feature[current]] <= threshold[current]
        node[rows] = np.where(go_left, left[current], right[current])


_SHARE_SCALE = 65_535


#: Age bands of the person-level copula (the gate's odd-year bands).
_COPULA_BAND_EDGES = (22, 30, 45, 60, 75)
_RHO_GRID = tuple(np.round(np.arange(0.0, 0.61, 0.05), 2))
#: TRAIN persons held out of the forest to calibrate the copula.
_CALIBRATION_SHARE = 0.1
_CALIBRATION_YEARS = (1997, 1999, 2001, 2003, 2005)


def _copula_band(age: np.ndarray) -> np.ndarray:
    """0 under 22, 1 for 22-29, 2 for 30-44, 3 for 45-59, 4 for 60-74, 5 on."""

    return np.digitize(np.asarray(age), _COPULA_BAND_EDGES)


@dataclass(frozen=True)
class OddForestFill:
    """A quantile regression forest draw (Meinshausen 2006), with a copula.

    A random forest (scikit-learn; split target ``log(share + 0.01)``)
    partitions TRAIN units by :func:`odd_features`. Every TRAIN unit used
    in the fit is passed down every tree, and each leaf keeps the sorted
    true shares of the units that reach it (zeros and the cap included,
    stored as shares times 65,535). The forest's conditional law of a unit
    is the average over trees of its leaves' empirical laws, so the draw is
    two-part by construction: zero, the cap and every share between keep
    their own mass. A draw picks a tree by one seeded uniform and takes the
    leaf's value at the quantile of a second, the copula uniform.

    The copula is person-level: a unit's normal score is ``sqrt(rho) * eta
    + sqrt(1 - rho) * eps``, with ``eta`` one draw per person and ``eps``
    one per unit, and ``rho`` by sex and age band at the unit. It carries
    the persistence across a person's masked years that the conditioning
    leaves. ``rho`` is calibrated on TRAIN persons held out of the forest
    (one in ten, by hash): their odd years 1997-2005 are masked as the
    gate masks them, and each band's ``rho`` is the grid value whose fills
    best match their true two- and four-year rank persistence between
    masked years.
    """

    tree_offsets: np.ndarray
    node_left: np.ndarray
    node_right: np.ndarray
    node_feature: np.ndarray
    node_threshold: np.ndarray
    node_leaf: np.ndarray
    leaf_offsets: np.ndarray
    leaf_values: np.ndarray
    rho: np.ndarray
    stream: str = "epuf_fill.odd_forest.v3"
    name: str = "odd_forest"

    @classmethod
    def fit(
        cls,
        shares,
        years,
        birth_year,
        sex,
        unit_years,
        person_key=None,
        *,
        n_units=3_000_000,
        n_trees=10,
        min_leaf=15,
        max_features=0.8,
        seed=0,
        n_jobs=10,
    ):
        from sklearn.ensemble import RandomForestRegressor

        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        sex = np.asarray(sex)
        n = len(shares)
        key = np.arange(n) if person_key is None else np.asarray(person_key)
        calibration = (
            hash_uniform(cls.stream + ".calibration", seed, key, 0)
            < _CALIBRATION_SHARE
        )
        fitting = np.flatnonzero(~calibration)
        rows = np.concatenate([fitting for _ in unit_years])
        unit_year = np.concatenate(
            [np.full(len(fitting), y) for y in unit_years]
        )
        known = np.isfinite(shares)
        target = _take(shares, rows, _column_of(years, unit_year))
        rng = np.random.default_rng(seed)
        chosen = np.sort(
            rng.choice(len(rows), size=min(n_units, len(rows)), replace=False)
        )
        context = odd_context(
            shares,
            years,
            rows[chosen],
            unit_year[chosen],
            birth_year,
            sex,
            known,
        )
        x = odd_features(context)
        y = target[chosen]
        forest = RandomForestRegressor(
            n_estimators=n_trees,
            min_samples_leaf=min_leaf,
            max_features=max_features,
            bootstrap=True,
            max_samples=0.5,
            random_state=seed,
            n_jobs=n_jobs,
        )
        forest.fit(x, np.log(y + 0.01))
        stored = np.round(np.clip(y, 0.0, 1.0) * _SHARE_SCALE).astype(
            np.uint16
        )
        tree_offsets = [0]
        leaf_offsets = [0]
        lefts, rights, features, thresholds, leaf_index, values = (
            [],
            [],
            [],
            [],
            [],
            [],
        )
        leaf_count = 0
        for estimator in forest.estimators_:
            tree = estimator.tree_
            left = tree.children_left.astype(np.int64)
            right = tree.children_right.astype(np.int64)
            is_leaf = left < 0
            index = np.full(tree.node_count, -1, dtype=np.int64)
            n_leaves = int(is_leaf.sum())
            index[is_leaf] = leaf_count + np.arange(n_leaves)
            nodes = _tree_leaves(
                left,
                right,
                tree.feature.astype(np.int64),
                tree.threshold.astype(np.float32),
                x,
            )
            local = index[nodes] - leaf_count
            order = np.lexsort((stored, local))
            counts = np.bincount(local, minlength=n_leaves)
            leaf_offsets.extend(
                (leaf_offsets[-1] + np.cumsum(counts)).tolist()
            )
            values.append(stored[order])
            lefts.append(left)
            rights.append(right)
            features.append(tree.feature.astype(np.int16))
            thresholds.append(tree.threshold.astype(np.float32))
            leaf_index.append(index)
            leaf_count += n_leaves
            tree_offsets.append(tree_offsets[-1] + tree.node_count)
        provisional = cls(
            tree_offsets=np.asarray(tree_offsets, dtype=np.int64),
            node_left=np.concatenate(lefts).astype(np.int32),
            node_right=np.concatenate(rights).astype(np.int32),
            node_feature=np.concatenate(features),
            node_threshold=np.concatenate(thresholds),
            node_leaf=np.concatenate(leaf_index).astype(np.int32),
            leaf_offsets=np.asarray(leaf_offsets, dtype=np.int64),
            leaf_values=np.concatenate(values),
            rho=np.zeros((4, 6)),
        )
        rho, calibration_record = provisional._calibrate(
            shares[calibration],
            years,
            birth_year[calibration],
            sex[calibration],
            key[calibration],
            seed,
        )
        fill = cls(**{**provisional.__dict__, "rho": rho})
        return fill, {
            "n_units": int(len(y)),
            "n_trees": n_trees,
            "min_leaf": min_leaf,
            "n_leaves": int(leaf_count),
            "n_nodes": int(tree_offsets[-1]),
            "calibration_persons": int(calibration.sum()),
            "rho": rho.tolist(),
            "calibration": calibration_record,
        }

    # -- the conditional law ----------------------------------------------------
    @property
    def n_trees(self) -> int:
        return len(self.tree_offsets) - 1

    def _leaves(self, x: np.ndarray, tree: int) -> np.ndarray:
        start, stop = self.tree_offsets[tree], self.tree_offsets[tree + 1]
        node = _tree_leaves(
            self.node_left[start:stop].astype(np.int64),
            self.node_right[start:stop].astype(np.int64),
            self.node_feature[start:stop].astype(np.int64),
            self.node_threshold[start:stop],
            np.asarray(x, dtype=np.float32),
        )
        return self.node_leaf[start:stop][node].astype(np.int64)

    def _chosen_leaves(self, x, tree_u) -> np.ndarray:
        """Each unit's leaf in the tree its uniform picks."""

        tree = np.minimum(
            (tree_u * self.n_trees).astype(np.int64), self.n_trees - 1
        )
        leaves = np.empty(len(tree_u), dtype=np.int64)
        for t in range(self.n_trees):
            rows = np.flatnonzero(tree == t)
            if len(rows):
                leaves[rows] = self._leaves(x[rows], t)
        return leaves

    def _value(self, leaves, u) -> np.ndarray:
        """The leaf's stored share at quantile ``u``."""

        start = self.leaf_offsets[leaves]
        count = self.leaf_offsets[leaves + 1] - start
        pick = start + np.minimum((u * count).astype(np.int64), count - 1)
        return self.leaf_values[pick] / _SHARE_SCALE

    def _units(self, shares, years, birth_year, sex, person_key, mask, seed):
        """Per masked unit: row, year, leaf, epsilon, eta, sex and band."""

        known = np.isfinite(shares) & ~mask
        eta = ndtri(hash_uniform(self.stream + ".person", seed, person_key, 0))
        out = []
        for column in np.flatnonzero(mask.any(axis=0)):
            year = int(years[column])
            rows = np.flatnonzero(mask[:, column])
            unit_year = np.full(len(rows), year)
            context = odd_context(
                shares, years, rows, unit_year, birth_year, sex, known
            )
            valid = ~(np.isnan(context.left) & np.isnan(context.right))
            tree_u = hash_uniform(
                self.stream + ".tree", seed, person_key[rows], unit_year
            )
            leaves = np.full(len(rows), -1, dtype=np.int64)
            if valid.any():
                features = odd_features(
                    OddContext(
                        **{k: v[valid] for k, v in context.__dict__.items()}
                    )
                )
                leaves[valid] = self._chosen_leaves(features, tree_u[valid])
            out.append(
                {
                    "column": column,
                    "rows": rows,
                    "leaves": leaves,
                    "epsilon": ndtri(
                        hash_uniform(
                            self.stream, seed, person_key[rows], unit_year
                        )
                    ),
                    "eta": eta[rows],
                    "sex": np.clip(context.sex, 0, 3),
                    "band": _copula_band(context.age),
                }
            )
        return out

    def _apply(self, units, shares, mask, rho):
        out = np.where(mask, np.nan, shares)
        for unit in units:
            r = rho[unit["sex"], unit["band"]]
            z = np.sqrt(r) * unit["eta"] + np.sqrt(1.0 - r) * unit["epsilon"]
            drawn = np.zeros(len(unit["rows"]))
            valid = unit["leaves"] >= 0
            drawn[valid] = self._value(unit["leaves"][valid], ndtr(z[valid]))
            # A unit with no known neighbour is filled with zero, the
            # assembler's treatment of a year it cannot fill.
            out[unit["rows"], unit["column"]] = drawn
        return out

    def _calibrate(self, shares, years, birth_year, sex, key, seed):
        """Choose rho by sex and band to match masked-year persistence."""

        from scipy.stats import spearmanr

        mask = np.zeros(shares.shape, dtype=bool)
        columns = _column_of(years, np.asarray(_CALIBRATION_YEARS))
        mask[:, columns[columns >= 0]] = True
        start = career_start(birth_year)
        mask &= years[None, :] >= start[:, None]
        given = np.where(mask, np.nan, shares)
        units = self._units(given, years, birth_year, sex, key, mask, seed)
        age = years[None, :] - birth_year[:, None]
        band = _copula_band(age)

        def persistence(matrix):
            out = {}
            for s in (1, 2):
                for b in range(1, 5):
                    values = []
                    for lag in (2, 4):
                        pairs = []
                        for year in _CALIBRATION_YEARS:
                            if year + lag not in _CALIBRATION_YEARS:
                                continue
                            c0 = year - years[0]
                            c1 = year + lag - years[0]
                            take = (
                                (sex == s)
                                & (band[:, c0] == b)
                                & mask[:, c0]
                                & mask[:, c1]
                            )
                            a = matrix[take, c0]
                            d = matrix[take, c1]
                            ok = (a > 0) & (d > 0)
                            if ok.sum() > 50:
                                pairs.append(spearmanr(a[ok], d[ok])[0])
                        values.append(np.mean(pairs) if pairs else np.nan)
                    out[(s, b)] = values
            return out

        truth = persistence(shares)
        record = {}
        rho = np.zeros((4, 6))
        best = {key_: (np.inf, 0.0) for key_ in truth}
        for value in _RHO_GRID:
            trial = np.full((4, 6), value)
            filled = self._apply(units, given, mask, trial)
            scores = persistence(filled)
            for key_, (r2, r4) in scores.items():
                t2, t4 = truth[key_]
                loss = abs(r2 - t2) + 0.5 * abs(r4 - t4)
                if np.isfinite(loss) and loss < best[key_][0]:
                    best[key_] = (loss, value)
                record[f"{key_[0]}.{key_[1]}.rho_{value}"] = [
                    float(r2 - t2),
                    float(r4 - t4),
                ]
        for (s, b), (_, value) in best.items():
            rho[s, b] = value
        # Bands outside the gate's take their neighbour's value.
        rho[:, 0] = rho[:, 1]
        rho[:, 5] = rho[:, 4]
        return rho, record

    def fill(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        units = self._units(
            shares,
            years,
            birth_year,
            sex,
            np.asarray(person_key),
            fill_mask,
            seed,
        )
        return self._apply(units, shares, fill_mask, self.rho)

    def to_bytes(self) -> bytes:
        return _to_npz(
            {
                "kind": np.array(self.name),
                **{name: getattr(self, name) for name in _FOREST_ARRAYS},
            }
        )

    @classmethod
    def from_arrays(cls, arrays) -> OddForestFill:
        return cls(**{name: arrays[name] for name in _FOREST_ARRAYS})


_FOREST_ARRAYS = (
    "tree_offsets",
    "node_left",
    "node_right",
    "node_feature",
    "node_threshold",
    "node_leaf",
    "leaf_offsets",
    "leaf_values",
    "rho",
)


# --------------------------------------------------------------------------
# Odd years, alternative: kNN triples
# --------------------------------------------------------------------------
_KNN_BANK = 40_000
_JITTER = 1e-4


@dataclass(frozen=True)
class OddKnnFill:
    """The share at ``t`` copied from one of ``k`` nearest TRAIN units.

    Per sex and age band, a bank of up to 40,000 TRAIN person-years holds
    the shares at ``t-1``, ``t``, ``t+1``. A masked unit's ``k`` nearest
    bank units in (``t-1``, ``t+1``) are found after a deterministic jitter
    of 1e-4 on both sides (so ties are broken at random), and one is chosen
    by the seeded uniform. A missing neighbour takes the other's value.
    """

    bank_stratum: np.ndarray
    bank_left: np.ndarray
    bank_right: np.ndarray
    bank_centre: np.ndarray
    k: int = 10
    stream: str = "epuf_fill.odd_knn.v1"
    name: str = "odd_knn"

    @classmethod
    def fit(cls, shares, years, birth_year, sex, unit_years, k=10, seed=0):
        shares = np.asarray(shares, dtype=np.float64)
        n = len(shares)
        rows = np.concatenate([np.arange(n) for _ in unit_years])
        unit_year = np.concatenate([np.full(n, y) for y in unit_years])
        known = np.isfinite(shares)
        context = odd_context(
            shares, years, rows, unit_year, birth_year, sex, known
        )
        centre = _take(shares, rows, _column_of(years, unit_year))
        stratum = context.sex * 16 + _age_band(context.age)
        rng = np.random.default_rng(seed)
        keep = []
        for value in np.unique(stratum):
            members = np.flatnonzero(stratum == value)
            if len(members) > _KNN_BANK:
                members = rng.choice(members, _KNN_BANK, replace=False)
            keep.append(np.sort(members))
        keep = np.concatenate(keep)
        fill = cls(
            bank_stratum=stratum[keep].astype(np.int64),
            bank_left=context.left[keep].astype(np.float32),
            bank_right=context.right[keep].astype(np.float32),
            bank_centre=centre[keep].astype(np.float32),
            k=k,
        )
        return fill, {"n_units": int(len(centre)), "bank": int(len(keep))}

    def fill(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        from scipy.spatial import cKDTree

        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        known = np.isfinite(shares) & ~fill_mask
        out = np.where(fill_mask, np.nan, shares)
        bank_index = np.arange(len(self.bank_stratum))
        jitter_bank = (
            hash_uniform(self.stream + ".bank", 0, bank_index, 0) - 0.5,
            hash_uniform(self.stream + ".bank", 1, bank_index, 0) - 0.5,
        )
        trees = {}
        for value in np.unique(self.bank_stratum):
            members = np.flatnonzero(self.bank_stratum == value)
            points = np.column_stack(
                [
                    self.bank_left[members]
                    + _JITTER * jitter_bank[0][members],
                    self.bank_right[members]
                    + _JITTER * jitter_bank[1][members],
                ]
            )
            trees[int(value)] = (cKDTree(points), members)
        for column in np.flatnonzero(fill_mask.any(axis=0)):
            year = int(years[column])
            rows = np.flatnonzero(fill_mask[:, column])
            unit_year = np.full(len(rows), year)
            context = odd_context(
                shares, years, rows, unit_year, birth_year, sex, known
            )
            left = np.where(
                np.isnan(context.left), context.right, context.left
            )
            right = np.where(
                np.isnan(context.right), context.left, context.right
            )
            stratum = context.sex * 16 + _age_band(context.age)
            u = hash_uniform(self.stream, seed, person_key[rows], unit_year)
            jitter = (
                hash_uniform(
                    self.stream + ".q0", seed, person_key[rows], unit_year
                )
                - 0.5,
                hash_uniform(
                    self.stream + ".q1", seed, person_key[rows], unit_year
                )
                - 0.5,
            )
            drawn = np.full(len(rows), np.nan)
            for value in np.unique(stratum):
                take = (stratum == value) & np.isfinite(left)
                if not take.any():
                    continue
                if int(value) not in trees:
                    trees[int(value)] = trees[self._nearest(int(value))]
                tree, members = trees[int(value)]
                query = np.column_stack(
                    [
                        left[take] + _JITTER * jitter[0][take],
                        right[take] + _JITTER * jitter[1][take],
                    ]
                )
                k = min(self.k, len(members))
                _, neighbours = tree.query(query, k=k)
                neighbours = np.asarray(neighbours).reshape(len(query), k)
                pick = np.minimum((u[take] * k).astype(np.int64), k - 1)
                chosen = members[neighbours[np.arange(len(query)), pick]]
                drawn[take] = self.bank_centre[chosen]
            out[rows, column] = drawn
        return out

    def _nearest(self, value: int) -> int:
        strata = np.unique(self.bank_stratum)
        same_sex = strata[strata // 16 == value // 16]
        if len(same_sex) == 0:
            same_sex = strata[strata // 16 == 1]
            value = 16 + value % 16
        return int(same_sex[np.argmin(np.abs(same_sex - value))])

    def to_bytes(self) -> bytes:
        return _to_npz(
            {
                "kind": np.array(self.name),
                "bank_stratum": self.bank_stratum,
                "bank_left": self.bank_left,
                "bank_right": self.bank_right,
                "bank_centre": self.bank_centre,
                "k": np.array(self.k),
            }
        )

    @classmethod
    def from_arrays(cls, arrays) -> OddKnnFill:
        return cls(
            bank_stratum=arrays["bank_stratum"],
            bank_left=arrays["bank_left"],
            bank_right=arrays["bank_right"],
            bank_centre=arrays["bank_centre"],
            k=int(arrays["k"]),
        )


# --------------------------------------------------------------------------
# Pre-career, primary: rank-kNN donor careers
# --------------------------------------------------------------------------
MATCH_YEARS = 5
_DONOR_BANK = 2_000


def _first_recorded(
    shares: np.ndarray, years: np.ndarray, birth_year: np.ndarray
) -> np.ndarray:
    """Shares in the first MATCH_YEARS years from the career start."""

    start = career_start(birth_year)
    columns = _column_of(
        years, start[:, None] + np.arange(MATCH_YEARS)[None, :]
    )
    rows = np.repeat(np.arange(len(shares)), MATCH_YEARS).reshape(
        len(shares), MATCH_YEARS
    )
    return _take(shares, rows.ravel(), columns.ravel()).reshape(
        len(shares), MATCH_YEARS
    )


#: The match vector: the first MATCH_YEARS shares from the career start,
#: then the mean share and the share of positive years over every known
#: career year.
MATCH_DIMS = MATCH_YEARS + 2
#: Odd years the PSID never records (1997 on); hidden when a bank's match
#: vectors are built, so they are built as a recipient's are.
_UNRECORDED_ODD_FROM = 1997


def match_vector(
    shares: np.ndarray, years: np.ndarray, birth_year: np.ndarray
) -> np.ndarray:
    """Persons by MATCH_DIMS: the donor-match features; NaN where unknown."""

    shares = np.asarray(shares, dtype=np.float64)
    years = np.asarray(years, dtype=np.int64)
    first = _first_recorded(shares, years, birth_year)
    career = years[None, :] >= career_start(birth_year)[:, None]
    known = career & np.isfinite(shares)
    count = known.sum(axis=1)
    values = np.where(known, shares, 0.0)
    mean = np.where(
        count > 0, values.sum(axis=1) / np.maximum(count, 1), np.nan
    )
    positive = np.where(
        count > 0,
        ((values > 0) & known).sum(axis=1) / np.maximum(count, 1),
        np.nan,
    )
    return np.column_stack([first, mean, positive])


def _midrank(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Percentile mid-rank of each value in a sorted reference sample."""

    below = np.searchsorted(reference, values, side="left")
    above = np.searchsorted(reference, values, side="right")
    return (below + 0.5 * (above - below)) / len(reference)


def block_first_year(birth_year: np.ndarray) -> np.ndarray:
    """First year a pre-career block can be positive in EPUF.

    1951 for cohorts born by 1937; the year of age 15 for later cohorts,
    whose earnings at 14 and under SSA zeroed.
    """

    birth_year = np.asarray(birth_year, dtype=np.int64)
    return np.where(birth_year <= 1937, 1951, birth_year + FIRST_EARNING_AGE)


#: The widest block: 1951-1967.
BLOCK_WIDTH = CAREER_FIRST_YEAR - 1951
_SHARE_SCALE = 65_535


@dataclass(frozen=True)
class PreDonorFill:
    """Whole pre-career blocks copied from rank-matched TRAIN donors.

    Per sex and birth year, a bank of up to 2,000 TRAIN donors (those with
    a positive share from their career start through 2006, chosen by the
    lowest hash of their person id) holds each donor's shares in the years
    from :func:`block_first_year` to the year before the career start (at
    most the 17 years 1951-1967; stored as shares times 65,535, rounded),
    and their shares in the first five years from the career start. A
    recipient's match vector is its percentile mid-rank, within the bank,
    in each of those five years it has recorded; distance is Euclidean over
    the recorded years, scaled by five over their number. One of the ``k``
    nearest donors is chosen by the seeded uniform and its block copied;
    masked years before :func:`block_first_year` are zero. A recipient with
    no recorded match year takes a donor chosen at random from the bank.
    """

    bank_sex: np.ndarray
    bank_birth_year: np.ndarray
    bank_match: np.ndarray
    bank_block: np.ndarray
    k: int = 10
    stream: str = "epuf_fill.pre_donor.v1"
    name: str = "pre_donor"

    @classmethod
    def fit(
        cls,
        shares,
        years,
        birth_year,
        sex,
        person_key,
        k=10,
        birth_years=(1905, 1985),
    ):
        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        sex = np.asarray(sex, dtype=np.int64)
        start = career_start(birth_year)
        recorded = years[None, :] >= start[:, None]
        universe = ((shares > 0) & recorded).any(axis=1) & np.isin(sex, (1, 2))
        universe &= (birth_year >= birth_years[0]) & (
            birth_year <= birth_years[1]
        )
        order_key = hash_uniform(cls.stream + ".bank", 0, person_key, 0)
        chosen = []
        for s in (1, 2):
            for b in np.unique(birth_year[universe & (sex == s)]):
                members = np.flatnonzero(
                    universe & (sex == s) & (birth_year == b)
                )
                members = members[np.argsort(order_key[members])][:_DONOR_BANK]
                chosen.append(np.sort(members))
        chosen = np.concatenate(chosen)
        first = block_first_year(birth_year[chosen])
        offsets = np.arange(BLOCK_WIDTH)
        block_years = first[:, None] + offsets[None, :]
        inside = block_years < start[chosen][:, None]
        columns = _column_of(years, block_years)
        values = _take(
            shares,
            np.repeat(chosen, BLOCK_WIDTH),
            columns.ravel(),
        ).reshape(len(chosen), BLOCK_WIDTH)
        values = np.where(inside, np.nan_to_num(values), 0.0)
        hidden = (years[None, :] >= _UNRECORDED_ODD_FROM) & (
            years[None, :] % 2 == 1
        )
        fill = cls(
            bank_sex=sex[chosen],
            bank_birth_year=birth_year[chosen],
            bank_match=match_vector(
                np.where(hidden, np.nan, shares[chosen]),
                years,
                birth_year[chosen],
            ).astype(np.float32),
            bank_block=np.round(values * _SHARE_SCALE).astype(np.uint16),
            k=k,
        )
        return fill, {"bank": int(len(chosen))}

    def donors(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        """The bank row each recipient (a row with a masked cell) copies.

        -1 for rows with no masked cell or no bank donor of their sex and
        birth year.
        """

        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        sex = np.asarray(sex, dtype=np.int64)
        readable = np.where(fill_mask, np.nan, shares)
        match = match_vector(readable, years, birth_year)
        u = hash_uniform(self.stream, seed, person_key, 0)
        targets = np.flatnonzero(fill_mask.any(axis=1))
        out = np.full(len(shares), -1, dtype=np.int64)
        for s, b in sorted(
            set(
                zip(
                    sex[targets].tolist(),
                    birth_year[targets].tolist(),
                    strict=True,
                )
            )
        ):
            recipients = targets[
                (sex[targets] == s) & (birth_year[targets] == b)
            ]
            donors = np.flatnonzero(
                (self.bank_sex == s) & (self.bank_birth_year == b)
            )
            if len(donors) == 0:
                continue
            donor_match = self.bank_match[donors].astype(np.float64)
            ranks_donor = np.empty_like(donor_match)
            ranks_recipient = np.full((len(recipients), MATCH_DIMS), np.nan)
            for j in range(MATCH_DIMS):
                column = np.sort(
                    donor_match[:, j][np.isfinite(donor_match[:, j])]
                )
                ranks_donor[:, j] = np.where(
                    np.isfinite(donor_match[:, j]),
                    _midrank(column, np.nan_to_num(donor_match[:, j])),
                    np.nan,
                )
                values = match[recipients, j]
                ok = np.isfinite(values)
                ranks_recipient[ok, j] = _midrank(column, values[ok])
            k = min(self.k, len(donors))
            for start in range(0, len(recipients), 1_000):
                block = slice(start, start + 1_000)
                diff = (
                    ranks_recipient[block][:, None, :]
                    - ranks_donor[None, :, :]
                )
                available = np.isfinite(diff)
                count = available.sum(axis=2)
                distance = np.where(available, diff**2, 0.0).sum(axis=2)
                distance = distance * MATCH_DIMS / np.maximum(count, 1)
                nearest = np.argpartition(distance, k - 1, axis=1)[:, :k]
                nearest_distance = np.take_along_axis(distance, nearest, 1)
                order = np.lexsort((nearest, nearest_distance), axis=1)
                nearest = np.take_along_axis(nearest, order, 1)
                pick = np.minimum(
                    (u[recipients[block]] * k).astype(np.int64), k - 1
                )
                no_match = count.max(axis=1) == 0
                random_donor = np.minimum(
                    (u[recipients[block]] * len(donors)).astype(np.int64),
                    len(donors) - 1,
                )
                out[recipients[block]] = donors[
                    np.where(
                        no_match,
                        random_donor,
                        nearest[np.arange(len(nearest)), pick],
                    )
                ]
        return out

    def fill(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        out = np.where(fill_mask, np.nan, shares)
        donor = self.donors(
            shares, years, birth_year, sex, person_key, fill_mask, seed
        )
        rows = np.flatnonzero(donor >= 0)
        first = block_first_year(birth_year[rows])
        block = self.bank_block[donor[rows]].astype(np.float64) / _SHARE_SCALE
        for offset in range(BLOCK_WIDTH):
            columns = _column_of(years, first + offset)
            ok = columns >= 0
            target_rows = rows[ok]
            target_columns = columns[ok]
            masked = fill_mask[target_rows, target_columns]
            out[target_rows[masked], target_columns[masked]] = block[ok][
                masked, offset
            ]
        # Masked years outside a donor block are zero, and so are those of a
        # recipient with no bank of its sex and birth year (the current
        # rule; the bank covers coded sex and births 1905-1985).
        before = fill_mask & (
            years[None, :] < block_first_year(birth_year)[:, None]
        )
        out[before] = 0.0
        out[fill_mask & (donor < 0)[:, None]] = 0.0
        return out

    def to_bytes(self) -> bytes:
        return _to_npz(
            {
                "kind": np.array(self.name),
                "bank_sex": self.bank_sex,
                "bank_birth_year": self.bank_birth_year,
                "bank_match": self.bank_match,
                "bank_block": self.bank_block,
                "k": np.array(self.k),
            }
        )

    @classmethod
    def from_arrays(cls, arrays) -> PreDonorFill:
        return cls(
            bank_sex=arrays["bank_sex"],
            bank_birth_year=arrays["bank_birth_year"],
            bank_match=arrays["bank_match"],
            bank_block=arrays["bank_block"],
            k=int(arrays["k"]),
        )


# --------------------------------------------------------------------------
# Pre-career, alternative: the chained one-sided draw
# --------------------------------------------------------------------------
def _chain_age(age: np.ndarray) -> np.ndarray:
    """0 below 15; single years 15-24 as 1-10; then five-year bands."""

    age = np.asarray(age, dtype=np.int64)
    return np.where(
        age < 15,
        0,
        np.where(age <= 24, age - 14, np.minimum((age - 25) // 5 + 11, 22)),
    )


@dataclass(frozen=True)
class PreChainFill:
    """Year ``y`` drawn from year ``y+1``, sex and age, backward to 1951.

    Cells are the finest of (sex, age (single years 15-24, then five-year
    bands), bin of the next known share),
    (sex, bin), (bin) with at least ``MIN_CELL`` TRAIN units; in a cell,
    ``p0`` and 65 quantiles of ``log(x_y / x_{y+1})`` (of ``log x_y`` when
    ``x_{y+1}`` is zero). Each year's uniform is independent.
    """

    level_edges: np.ndarray
    level_keys: tuple[np.ndarray, ...]
    level_p0: tuple[np.ndarray, ...]
    level_quantiles: tuple[np.ndarray, ...]
    stream: str = "epuf_fill.pre_chain.v1"
    name: str = "pre_chain"

    @staticmethod
    def _keys(sex, age, following, edges):
        bins = np.where(
            following <= 0,
            0,
            np.where(
                following >= 1.0,
                len(edges) + 2,
                np.searchsorted(edges, following, side="right") + 1,
            ),
        )
        band = _chain_age(age)

        def key(s, a, b):
            return (s * 40 + a) * 32 + b

        return [
            key(sex, band, bins),
            key(sex, 39, bins),
            key(0 * sex, 39, bins),
        ]

    @classmethod
    def fit(cls, shares, years, birth_year, sex, unit_years):
        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        n = len(shares)
        rows = np.concatenate([np.arange(n) for _ in unit_years])
        unit_year = np.concatenate([np.full(n, y) for y in unit_years])
        target = _take(shares, rows, _column_of(years, unit_year))
        following = _take(shares, rows, _column_of(years, unit_year + 1))
        sex_u = np.asarray(sex)[rows].astype(np.int64)
        age = unit_year - np.asarray(birth_year)[rows]
        inside = following[(following > 0) & (following < 1.0)]
        edges = np.quantile(inside, np.linspace(0, 1, 21)[1:-1])
        keys = cls._keys(sex_u, age, following, edges)
        positive = target > 0
        base = np.where(following > 0, following, 1.0)
        residual = np.log(np.where(positive, target, 1.0)) - np.log(base)
        level_keys, level_p0, level_quantiles = [], [], []
        for key in keys:
            unique, count = np.unique(key, return_counts=True)
            populated = unique[count >= MIN_CELL]
            in_cells = np.isin(key, populated)
            zu, zc = np.unique(key[in_cells & ~positive], return_counts=True)
            p0 = np.zeros(len(populated))
            p0[np.searchsorted(populated, zu)] = zc
            p0 = p0 / count[count >= MIN_CELL]
            q_keys, _, table = _quantile_table(
                key[in_cells & positive], residual[in_cells & positive]
            )
            full = np.zeros((len(populated), QUANTILE_POINTS), np.float32)
            full[np.searchsorted(populated, q_keys)] = table
            level_keys.append(populated.astype(np.int64))
            level_p0.append(p0)
            level_quantiles.append(full)
        fill = cls(
            level_edges=edges,
            level_keys=tuple(level_keys),
            level_p0=tuple(level_p0),
            level_quantiles=tuple(level_quantiles),
        )
        return fill, {"n_units": int(len(target))}

    def fill(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        shares = np.asarray(shares, dtype=np.float64)
        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        sex = np.asarray(sex, dtype=np.int64)
        out = np.where(fill_mask, np.nan, shares)
        for column in np.flatnonzero(fill_mask.any(axis=0))[::-1]:
            year = int(years[column])
            rows = np.flatnonzero(fill_mask[:, column])
            # The next known (or already drawn) later year's share.
            later = out[rows, column + 1 :]
            if later.shape[1]:
                finite = np.isfinite(later)
                first = np.argmax(finite, axis=1)
                following = np.where(
                    finite.any(axis=1),
                    later[np.arange(len(rows)), first],
                    np.nan,
                )
            else:
                following = np.full(len(rows), np.nan)
            # With no known later year (a career starting after the file's
            # last year), the chain starts from a zero year.
            following = np.nan_to_num(following, nan=0.0)
            ok = np.ones(len(rows), dtype=bool)
            age = year - birth_year[rows]
            keys = self._keys(
                sex[rows], age, np.nan_to_num(following), self.level_edges
            )
            u = hash_uniform(self.stream, seed, person_key[rows], year)
            level = np.full(len(rows), -1)
            row = np.full(len(rows), -1)
            for index, key in enumerate(keys):
                found = _lookup(self.level_keys[index], key)
                take = (level < 0) & (found >= 0)
                level[take] = index
                row[take] = found[take]
            drawn = np.full(len(rows), np.nan)
            for index in np.unique(level[level >= 0]):
                take = (level == index) & ok
                p0 = self.level_p0[index][row[take]]
                positive = u[take] >= p0
                v = np.where(
                    positive, (u[take] - p0) / np.maximum(1.0 - p0, 1e-12), 0.0
                )
                residual = _interpolate(
                    self.level_quantiles[index], row[take], v
                )
                base = np.where(following[take] > 0, following[take], 1.0)
                drawn[take] = np.where(
                    positive, np.minimum(base * np.exp(residual), 1.0), 0.0
                )
            # EPUF has no earnings below age 15.
            drawn = np.where(age < FIRST_EARNING_AGE, 0.0, drawn)
            out[rows, column] = drawn
        return out

    def to_bytes(self) -> bytes:
        arrays = {"kind": np.array(self.name), "level_edges": self.level_edges}
        for index, (k, p, q) in enumerate(
            zip(
                self.level_keys,
                self.level_p0,
                self.level_quantiles,
                strict=True,
            )
        ):
            arrays[f"keys_{index}"] = k
            arrays[f"p0_{index}"] = p
            arrays[f"quantiles_{index}"] = q
        return _to_npz(arrays)

    @classmethod
    def from_arrays(cls, arrays) -> PreChainFill:
        n_levels = sum(1 for name in arrays.files if name.startswith("keys_"))
        return cls(
            level_edges=arrays["level_edges"],
            level_keys=tuple(arrays[f"keys_{i}"] for i in range(n_levels)),
            level_p0=tuple(arrays[f"p0_{i}"] for i in range(n_levels)),
            level_quantiles=tuple(
                arrays[f"quantiles_{i}"] for i in range(n_levels)
            ),
        )


@dataclass(frozen=True)
class BySexFill:
    """One fill per coded sex; persons of uncoded sex use the men's.

    Each part is any fill of this module, fitted on TRAIN persons of that
    sex only, and fills only rows of that sex.
    """

    parts: dict
    name: str = "by_sex"

    @classmethod
    def fit(cls, fill_class, shares, years, birth_year, sex, *args, **kwargs):
        parts, diagnostics = {}, {}
        sex = np.asarray(sex)
        for value in (1, 2):
            rows = sex == value
            extra = [
                (
                    a[rows]
                    if isinstance(a, np.ndarray) and len(a) == len(sex)
                    else a
                )
                for a in args
            ]
            part, diagnostic = fill_class.fit(
                shares[rows],
                years,
                birth_year[rows],
                sex[rows],
                *extra,
                **kwargs,
            )
            parts[value] = part
            diagnostics[str(value)] = diagnostic
        return cls(parts=parts), diagnostics

    def fill(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        shares = np.asarray(shares, dtype=np.float64)
        sex = np.asarray(sex)
        out = np.where(fill_mask, np.nan, shares)
        for value, part in self.parts.items():
            rows = np.flatnonzero(
                (sex == value) | ((value == 1) & ~np.isin(sex, (1, 2)))
            )
            if not len(rows):
                continue
            out[rows] = part.fill(
                shares[rows],
                years,
                np.asarray(birth_year)[rows],
                sex[rows],
                np.asarray(person_key)[rows],
                fill_mask[rows],
                seed,
            )
        return out

    def to_bytes(self) -> bytes:
        return _to_npz(
            {
                "kind": np.array(self.name),
                **{
                    f"part_{value}": np.frombuffer(part.to_bytes(), np.uint8)
                    for value, part in self.parts.items()
                },
            }
        )

    @classmethod
    def from_arrays(cls, arrays) -> BySexFill:
        parts = {}
        for name in arrays.files:
            if name.startswith("part_"):
                with np.load(
                    io.BytesIO(arrays[name].tobytes()), allow_pickle=False
                ) as nested:
                    kind = str(nested["kind"])
                    parts[int(name[5:])] = FILL_CLASSES[kind].from_arrays(
                        nested
                    )
        return cls(parts=parts)


FILL_CLASSES = {
    "by_sex": BySexFill,
    "odd_forest": OddForestFill,
    "odd_quantile": OddQuantileFill,
    "odd_knn": OddKnnFill,
    "pre_donor": PreDonorFill,
    "pre_chain": PreChainFill,
}


def load_fill(path: Path, *, sha256: str | None = None):
    """Load a fitted fill from its ``.npz``; refuse other bytes than ``sha256``."""

    data = Path(path).read_bytes()
    if sha256 is not None:
        observed = hashlib.sha256(data).hexdigest()
        if observed != sha256:
            raise ValueError(
                f"{path} has SHA-256 {observed}, not the registered {sha256}"
            )
    with np.load(io.BytesIO(data), allow_pickle=False) as arrays:
        kind = str(arrays["kind"])
        return FILL_CLASSES[kind].from_arrays(arrays)
