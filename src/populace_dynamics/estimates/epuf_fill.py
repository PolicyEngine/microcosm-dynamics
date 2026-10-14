"""Career fills learned from SSA's Earnings Public-Use File (EPUF).

The career assembler (:func:`populace_dynamics.estimates.career.build_career`)
fills the years the PSID did not record with two fixed rules: each odd
income year from 1997 is the mean of its neighbours, and nothing counts
before ``max(1968, birth_year + 22)``. This module holds the learned
replacements registered by ``gate_epuf_fill``
(``docs/amendments/gate_epuf_fill_registration_proposal.md``, section 7),
fitted on the gate's TRAIN persons only:

- :class:`OddForestFill` (odd years, primary; fitted per sex through
  :class:`BySexFill`): a two-part draw from random forests. A probability
  forest gives the chance of a zero year, and a quantile regression forest
  gives the positive share. Both condition on the recorded shares around
  ``t``, sex, age and year. A person-level Gaussian copula, calibrated on
  held-out TRAIN persons, carries the persistence across a person's masked
  years.
- :class:`OddKnnFill` (odd years, alternative): the share at ``t`` copied
  from one of the ``k`` nearest TRAIN person-years in the shares at ``t-1``
  and ``t+1``, by sex and age.
- :class:`PreDonorFill` (pre-career years, primary): rank-kNN donor
  careers. The whole masked block is copied from one of the ``k`` TRAIN
  donors of the same sex and birth year nearest in percentile rank over
  the first five recorded years and two career-wide summaries.
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


def _to_npz(arrays: Mapping[str, np.ndarray]) -> bytes:
    """A compressed ``.npz`` whose bytes depend only on the arrays.

    ``numpy.savez_compressed`` stamps each member with the time of writing,
    so two writes of the same fill differ. This writer fixes every member's
    timestamp and order, so a fill's SHA-256 can be registered and refit.
    """

    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(arrays):
            member = io.BytesIO()
            np.lib.format.write_array(
                member, np.asanyarray(arrays[name]), allow_pickle=False
            )
            info = zipfile.ZipInfo(
                f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, member.getvalue())
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
_RHO_GRID = tuple(np.round(np.arange(0.0, 0.91, 0.05), 2))
#: TRAIN persons held out of the forest to calibrate the copula.
_CALIBRATION_SHARE = 0.1
_CALIBRATION_YEARS = (1997, 1999, 2001, 2003, 2005)


def _copula_band(age: np.ndarray) -> np.ndarray:
    """0 under 22, 1 for 22-29, 2 for 30-44, 3 for 45-59, 4 for 60-74, 5 on."""

    return np.digitize(np.asarray(age), _COPULA_BAND_EDGES)


@dataclass(frozen=True)
class OddForestFill:
    """A quantile regression forest draw (Meinshausen 2006), with a copula.

    Two parts, both random forests (scikit-learn) on :func:`odd_features`
    of TRAIN units inside the career, whose contexts see the career only:

    1. a probability forest for a zero year: ``p0`` is the mean over trees
       of the zero share of the unit's leaves;
    2. a quantile regression forest on positive shares (split target
       ``log share``): every positive TRAIN unit used in the fit is passed
       down every tree, and each leaf keeps the sorted true shares that
       reach it (the cap included, stored as shares times 65,535).

    A draw maps the copula uniform ``u`` to zero below ``p0``; otherwise a
    second seeded uniform picks a tree, and the share is that tree's leaf
    value at the quantile ``(u - p0) / (1 - p0)``.

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
    zero_tree_offsets: np.ndarray
    zero_node_left: np.ndarray
    zero_node_right: np.ndarray
    zero_node_feature: np.ndarray
    zero_node_threshold: np.ndarray
    zero_node_leaf: np.ndarray
    zero_leaf_p: np.ndarray
    stream: str = "epuf_fill.odd_forest.v4"
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
        # Units lie inside the career, and their contexts see the career
        # only, as a fill's do (pre-career years are unknown to it).
        inside = unit_year >= career_start(birth_year[rows])
        rows, unit_year = rows[inside], unit_year[inside]
        pre_career = years[None, :] < career_start(birth_year)[:, None]
        known = np.isfinite(shares) & ~pre_career
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
        x_all = odd_features(context)
        y_all = target[chosen]
        # Part one: the probability of a zero year, a probability forest.
        from sklearn.ensemble import RandomForestClassifier

        zero_forest = RandomForestClassifier(
            n_estimators=n_trees,
            min_samples_leaf=4 * min_leaf,
            max_features=max_features,
            bootstrap=True,
            max_samples=0.5,
            random_state=seed,
            n_jobs=n_jobs,
        )
        zero_forest.fit(x_all, (y_all <= 0).astype(np.int8))
        zero_arrays = _forest_arrays(
            zero_forest, x_all, (y_all <= 0).astype(np.float64)
        )
        # Part two: the positive share, a quantile regression forest.
        positive = y_all > 0
        x = x_all[positive]
        y = y_all[positive]
        forest = RandomForestRegressor(
            n_estimators=n_trees,
            min_samples_leaf=min_leaf,
            max_features=max_features,
            bootstrap=True,
            max_samples=0.5,
            random_state=seed,
            n_jobs=n_jobs,
        )
        forest.fit(x, np.log(y))
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
            if (counts == 0).any():
                raise ValueError(
                    "a forest leaf holds no TRAIN unit under the stored "
                    "traversal"
                )
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
            **zero_arrays,
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
            "n_units": int(len(y_all)),
            "n_positive_units": int(len(y)),
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

    def _p_zero(self, x) -> np.ndarray:
        """The probability forest's zero-year probability (mean over trees)."""

        x = np.asarray(x, dtype=np.float32)
        n_trees = len(self.zero_tree_offsets) - 1
        total = np.zeros(len(x))
        for tree in range(n_trees):
            start = self.zero_tree_offsets[tree]
            stop = self.zero_tree_offsets[tree + 1]
            node = _tree_leaves(
                self.zero_node_left[start:stop].astype(np.int64),
                self.zero_node_right[start:stop].astype(np.int64),
                self.zero_node_feature[start:stop].astype(np.int64),
                self.zero_node_threshold[start:stop],
                x,
            )
            total += self.zero_leaf_p[
                self.zero_node_leaf[start:stop][node].astype(np.int64)
            ]
        return total / n_trees

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
            p_zero = np.ones(len(rows))
            if valid.any():
                features = odd_features(
                    OddContext(
                        **{k: v[valid] for k, v in context.__dict__.items()}
                    )
                )
                leaves[valid] = self._chosen_leaves(features, tree_u[valid])
                p_zero[valid] = self._p_zero(features)
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
                    "p_zero": p_zero,
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
            u = ndtr(z)
            p0 = unit["p_zero"]
            valid = valid & (u >= p0)
            v = (u[valid] - p0[valid]) / np.maximum(1.0 - p0[valid], 1e-12)
            drawn[valid] = self._value(unit["leaves"][valid], v)
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
        pre_career = years[None, :] < start[:, None]
        mask &= ~pre_career
        given = np.where(mask | pre_career, np.nan, shares)
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


def _forest_arrays(forest, x, y) -> dict[str, np.ndarray]:
    """A fitted probability forest as arrays: nodes, and each leaf's mean y."""

    offsets = [0]
    lefts, rights, features, thresholds, leaf_index, means = (
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
        n_leaves = int(is_leaf.sum())
        index = np.full(tree.node_count, -1, dtype=np.int64)
        index[is_leaf] = leaf_count + np.arange(n_leaves)
        nodes = _tree_leaves(
            left,
            right,
            tree.feature.astype(np.int64),
            tree.threshold.astype(np.float32),
            x,
        )
        local = index[nodes] - leaf_count
        total = np.bincount(local, minlength=n_leaves)
        hits = np.bincount(local, weights=y, minlength=n_leaves)
        means.append(hits / np.maximum(total, 1))
        lefts.append(left)
        rights.append(right)
        features.append(tree.feature.astype(np.int16))
        thresholds.append(tree.threshold.astype(np.float32))
        leaf_index.append(index)
        leaf_count += n_leaves
        offsets.append(offsets[-1] + tree.node_count)
    return {
        "zero_tree_offsets": np.asarray(offsets, dtype=np.int64),
        "zero_node_left": np.concatenate(lefts).astype(np.int32),
        "zero_node_right": np.concatenate(rights).astype(np.int32),
        "zero_node_feature": np.concatenate(features),
        "zero_node_threshold": np.concatenate(thresholds),
        "zero_node_leaf": np.concatenate(leaf_index).astype(np.int32),
        "zero_leaf_p": np.concatenate(means).astype(np.float32),
    }


_FOREST_ARRAYS = (
    "zero_tree_offsets",
    "zero_node_left",
    "zero_node_right",
    "zero_node_feature",
    "zero_node_threshold",
    "zero_node_leaf",
    "zero_leaf_p",
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
        # Units inside the career; contexts see the career only.
        start = career_start(np.asarray(birth_year))
        inside = unit_year >= start[rows]
        rows, unit_year = rows[inside], unit_year[inside]
        known = np.isfinite(shares) & ~(
            np.asarray(years)[None, :] < start[:, None]
        )
        context = odd_context(
            shares, years, rows, unit_year, birth_year, sex, known
        )
        centre = _take(shares, rows, _column_of(years, unit_year))
        # A missing neighbour takes the other's value, as in the draw.
        left = np.where(np.isnan(context.left), context.right, context.left)
        right = np.where(np.isnan(context.right), context.left, context.right)
        usable = np.isfinite(left) & np.isfinite(right)
        stratum = context.sex * 16 + _age_band(context.age)
        rng = np.random.default_rng(seed)
        keep = []
        for value in np.unique(stratum[usable]):
            members = np.flatnonzero((stratum == value) & usable)
            if len(members) > _KNN_BANK:
                members = rng.choice(members, _KNN_BANK, replace=False)
            keep.append(np.sort(members))
        keep = np.concatenate(keep)
        fill = cls(
            bank_stratum=stratum[keep].astype(np.int64),
            bank_left=left[keep].astype(np.float32),
            bank_right=right[keep].astype(np.float32),
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


#: Nearest-donor lists by input and bank content, reused across draw seeds.
_NEAREST_CACHE: dict = {}
#: Bank digests by fill (the fill is held so its id cannot be reused).
_BANK_DIGESTS: dict = {}
#: The match vector: the first MATCH_YEARS shares from the career start,
#: then the mean share and the share of positive years over every known
#: career year.
MATCH_DIMS = MATCH_YEARS + 2
#: Odd years the PSID never records (1997 on); hidden when a bank's match
#: vectors are built, so they are built as a recipient's are.
_UNRECORDED_ODD_FROM = 1997
#: EPUF's last year, the last year a donor bank records.
_BANK_LAST_YEAR = 2006


def match_vector(
    shares: np.ndarray, years: np.ndarray, birth_year: np.ndarray
) -> np.ndarray:
    """Persons by MATCH_DIMS: the donor-match features; NaN where unknown."""

    shares = np.asarray(shares, dtype=np.float64)
    years = np.asarray(years, dtype=np.int64)
    first = _first_recorded(shares, years, birth_year)
    # The career summaries cover the bank's years (through 2006) only, so a
    # PSID recipient's later years do not enter them.
    career = (years[None, :] >= career_start(birth_year)[:, None]) & (
        years[None, :] <= _BANK_LAST_YEAR
    )
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

    if len(reference) == 0:
        return np.full(len(values), np.nan)
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


@dataclass(frozen=True)
class PreDonorFill:
    """Whole pre-career blocks copied from rank-matched TRAIN donors.

    Per sex and birth year, a bank of up to ``bank_size`` TRAIN donors
    (those with a positive share from their career start through 2006,
    chosen by the lowest hash of their person id; the registered fill keeps
    them all) holds each donor's shares in the years from
    :func:`block_first_year` to the year before the career start (at most
    the 17 years 1951-1967, stored as shares times 65,535, rounded) and the
    donor's match vector (:func:`match_vector`). The match vector has seven
    features: the shares in the first five years from the career start,
    and the mean share and share of positive years over the known career
    years through 2006.

    A recipient's features are its percentile mid-ranks within the bank in
    each feature it has. Distance is Euclidean over the features both have,
    scaled by seven over their number. One of the ``k`` nearest donors is
    chosen by the seeded uniform and its block copied; masked years before
    :func:`block_first_year` are zero. A recipient with no feature takes a
    donor chosen at random from its group.
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
        bank_size=_DONOR_BANK,
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
                members = members[np.argsort(order_key[members])][:bank_size]
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
            bank_block=np.round(
                np.clip(values, 0.0, 1.0) * _SHARE_SCALE
            ).astype(np.uint16),
            k=k,
        )
        return fill, {"bank": int(len(chosen))}

    @property
    def bank_digest(self) -> str:
        """SHA-256 of the bank and k, the cache's key for this fill."""

        cached = _BANK_DIGESTS.get(id(self))
        if cached is not None and cached[0] is self:
            return cached[1]
        digest = hashlib.sha256(
            np.ascontiguousarray(self.bank_sex).tobytes()
            + np.ascontiguousarray(self.bank_birth_year).tobytes()
            + np.ascontiguousarray(self.bank_match).tobytes()
            + np.ascontiguousarray(self.bank_block).tobytes()
            + str(self.k).encode()
        ).hexdigest()
        _BANK_DIGESTS[id(self)] = (self, digest)
        return digest

    def _nearest(self, match, birth_year, sex, targets):
        """Each target's ``k`` nearest bank rows, and its group's bank rows.

        Seed-free, so it is computed once for a matrix and reused across
        draw seeds (cached by the content of its inputs).
        """

        digest = hashlib.sha256(
            np.ascontiguousarray(match[targets]).tobytes()
            + np.ascontiguousarray(birth_year[targets]).tobytes()
            + np.ascontiguousarray(sex[targets]).tobytes()
            + np.ascontiguousarray(targets).tobytes()
            + self.bank_digest.encode()
        ).hexdigest()
        if digest in _NEAREST_CACHE:
            return _NEAREST_CACHE[digest]
        nearest = np.full((len(targets), self.k), -1, dtype=np.int64)
        group_first = np.full(len(targets), -1, dtype=np.int64)
        group_size = np.zeros(len(targets), dtype=np.int64)
        no_match = np.zeros(len(targets), dtype=bool)
        for s, b in sorted(
            set(
                zip(
                    sex[targets].tolist(),
                    birth_year[targets].tolist(),
                    strict=True,
                )
            )
        ):
            local = np.flatnonzero(
                (sex[targets] == s) & (birth_year[targets] == b)
            )
            recipients = targets[local]
            donors = np.flatnonzero(
                (self.bank_sex == s) & (self.bank_birth_year == b)
            )
            if len(donors) == 0:
                continue
            group_first[local] = donors[0]
            group_size[local] = len(donors)
            donor_match = self.bank_match[donors].astype(np.float64)
            ranks_donor = np.empty_like(donor_match)
            ranks_recipient = np.full((len(recipients), MATCH_DIMS), np.nan)
            for j in range(MATCH_DIMS):
                finite = np.isfinite(donor_match[:, j])
                column = np.sort(donor_match[finite, j])
                ranks_donor[:, j] = np.where(
                    finite,
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
                order = np.argpartition(distance, k - 1, axis=1)[:, :k]
                near_distance = np.take_along_axis(distance, order, 1)
                ranked = np.lexsort((order, near_distance), axis=1)
                order = np.take_along_axis(order, ranked, 1)
                rows = local[block]
                nearest[rows, :k] = donors[order]
                no_match[rows] = count.max(axis=1) == 0
        result = (nearest, group_first, group_size, no_match)
        if len(_NEAREST_CACHE) >= 4:
            _NEAREST_CACHE.pop(next(iter(_NEAREST_CACHE)))
        _NEAREST_CACHE[digest] = result
        return result

    def donors(
        self, shares, years, birth_year, sex, person_key, fill_mask, seed
    ):
        """The bank row each recipient (a row with a masked cell) copies.

        One of the ``k`` nearest bank donors of the recipient's sex and
        birth year, chosen by the seeded uniform; a recipient with no
        recorded match feature takes a random donor of its group. -1 for
        rows with no masked cell or no bank donor of their group.
        """

        years = np.asarray(years, dtype=np.int64)
        birth_year = np.asarray(birth_year, dtype=np.int64)
        sex = np.asarray(sex, dtype=np.int64)
        readable = np.where(fill_mask, np.nan, shares)
        match = match_vector(readable, years, birth_year)
        u = hash_uniform(self.stream, seed, person_key, 0)
        targets = np.flatnonzero(fill_mask.any(axis=1))
        nearest, group_first, group_size, no_match = self._nearest(
            match, birth_year, sex, targets
        )
        out = np.full(len(shares), -1, dtype=np.int64)
        has_group = group_size > 0
        k_available = (nearest >= 0).sum(axis=1)
        pick = np.minimum(
            (u[targets] * np.maximum(k_available, 1)).astype(np.int64),
            np.maximum(k_available - 1, 0),
        )
        chosen = nearest[np.arange(len(targets)), pick]
        random_donor = group_first + np.minimum(
            (u[targets] * np.maximum(group_size, 1)).astype(np.int64),
            np.maximum(group_size - 1, 0),
        )
        chosen = np.where(no_match, random_donor, chosen)
        out[targets[has_group]] = chosen[has_group]
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
                take = level == index
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
                # Rows of uncoded sex take this part's sex, so its copula
                # (calibrated for that sex) applies to them.
                np.full(len(rows), value),
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
