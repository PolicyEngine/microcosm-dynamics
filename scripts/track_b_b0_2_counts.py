#!/usr/bin/env python3
"""Track B B0.2: structural counts under protocol version 1.

Run once from the clean protocol-freezing commit. Family values are
immediately reduced by B0.1's validity_frame; all counting functions
accept frames and inspect only structural columns. Collection-wave ages
are used throughout; reference year is collection wave minus one.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import traceback
import warnings
from collections import Counter
from collections.abc import Callable, Mapping
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, hstack, vstack

from populace_dynamics.cohorts import age67, psid2010
from populace_dynamics.data import family, panels, psid
from scripts.track_b_b0_1_counts import (
    AGE_SUPPORT,
    BOUNDARY_YEAR,
    DISPOSITIONS,
    EARN_COHORTS,
    HORIZON_YEARS,
    WAVE_OFFSET,
    _cohort,
    _disposition,
    _family_variables,
    _individual_variables,
    cluster_worst_n_eff,
    earnings_rows,
    kish_n_eff,
    validity_frame,
)
from scripts.track_b_b0_1_counts import (
    structural_counts as b0_1_structural_counts,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
DEFAULT_OUT = ROOT / "docs/design/track_b_b0_2_counts.json"
B0_1_COUNTS = ROOT / "docs/design/track_b_b0_1_counts.json"
EVIDENCE_DIR = (
    Path.home()
    / "microcosm-launch-evidence/dynasim-parity-20260909/trackb-b0-2-20261021"
)
PROTOCOL_PATH = ROOT / "docs/design/track_b_b0_2_protocol.md"
PROTOCOL_SHA256 = (
    "a92539b27121f8d6c903f763537405a1fb992491cff45bdb0626a23de8169871"
)
SCHEMA = "track_b_b0_2_counts.v1"
DISCLOSURE_THRESHOLD = 10
DISCLOSURE_BASE = 10
PROTECTION_WIDTH = 4
PROGRAM_SECONDS = 300.0
POOL_SEED = 20261024
POOL_DIRECTIONS = 8
POOL_LIMIT = 1024
RELATIONS = ("at_most", "nonempty")
COARSENING_RULE = (
    "0 stays 0; 1 to B-1 is <B; otherwise the nearest multiple of B, "
    "halves up; effective sizes alike, from their own values"
)
PROTECTION_RULE = (
    "every atom and published-set difference of true size 1-9 has an "
    "integer range of width >= 4, shown by two exactly verified integer "
    "points, under the published values, the guaranteed cross-type "
    "relations and every target the release discloses to lie outside 1-9; "
    "every program is set from the publication alone, and a target not "
    "shown wide within 300 seconds per program is narrow"
)
CellPath = tuple[str, ...]
WAVES = tuple(range(1999, 2024, 2))
LAGS = (2, 4)
ANCHOR_WAVE = 2011
B3L_ORIGIN_WAVE = 2007
OLDER_BANDS = (("62_64", 62, 64), ("65_66", 65, 66), ("67_69", 67, 69))
CONTEXT_BANDS = (("25_44", 25, 44), ("45_61", 45, 61))
ROSTER_BANDS = (
    ("1_24", 1, 24),
    *CONTEXT_BANDS,
    *OLDER_BANDS,
    ("70_79", 70, 79),
    ("80_plus", 80, age67._MAX_AGE_CODE),
)
PERSON_COLUMNS = (
    "person_id",
    "period",
    "age",
    "sequence",
    "relationship",
    "weight",
    "interview",
)
INDIVIDUAL_CONCEPTS = (
    "age",
    "sequence",
    "relationship",
    "weight",
    "interview",
)


# --------------------------------------------------------------------------
# Pure structural counting
# --------------------------------------------------------------------------
def valid_rows(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
) -> pd.DataFrame:
    """Apply B0.1's valid-row law, then attach wave weights/households."""
    people = person_wave[list(PERSON_COLUMNS)]
    rows = earnings_rows(
        people, validity_by_wave, (wave - 1 for wave in WAVES)
    )
    selected = rows.loc[
        rows["valid"], ["person_id", "reference_year", "acc_flag"]
    ].copy()
    selected["period"] = selected.pop("reference_year") + 1
    return people.merge(
        selected, on=["person_id", "period"], validate="one_to_one"
    )


def _present(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[
        frame["sequence"].between(1, 20) & (frame["weight"] > 0)
    ].copy()


def _full(person_wave: pd.DataFrame, wave: int) -> pd.DataFrame:
    return _present(
        person_wave.loc[person_wave["period"] == wave, list(PERSON_COLUMNS)]
    )


def _with_design(frame: pd.DataFrame, design: pd.DataFrame) -> pd.DataFrame:
    return frame.merge(
        design[["person_id", "stratum", "cluster"]],
        on="person_id",
        how="left",
        validate="many_to_one",
    )


def _known_age(ages: pd.Series) -> pd.Series:
    """Readers' accepted integer ages; sentinels and fractions are unknown."""
    numeric = pd.to_numeric(ages, errors="coerce")
    return (
        numeric.between(1, age67._MAX_AGE_CODE) & numeric.mod(1).eq(0)
    ).fillna(False)


def _age_band(ages: pd.Series, low: int, high: int) -> pd.Series:
    numeric = pd.to_numeric(ages, errors="coerce")
    return _known_age(ages) & numeric.between(low, high)


def _summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Count persons and units; effective sizes use positive weights only.

    Sampling-error clusters are identified within stratum, as in age67.
    An empty positive-weight subset has effective sizes zero, without
    changing B0.1's helpers (which reject supplied nonpositive weights).
    """
    positive = frame[frame["weight"] > 0]
    weights = positive["weight"].to_numpy(dtype=float)
    design_clusters = pd.MultiIndex.from_frame(
        positive[["stratum", "cluster"]]
    ).to_numpy()
    return {
        "persons": int(frame["person_id"].nunique()),
        "households": int(frame["interview"].nunique()),
        "design_strata": int(frame["stratum"].nunique()),
        "design_clusters": int(
            len(frame[["stratum", "cluster"]].drop_duplicates())
        ),
        "kish_n_eff": kish_n_eff(weights),
        "household_cluster_worst_n_eff": cluster_worst_n_eff(
            weights, positive["interview"].to_numpy()
        ),
        "design_cluster_worst_n_eff": cluster_worst_n_eff(
            weights, design_clusters
        ),
    }


def _roster_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "overall": _summary(frame),
        "by_age_band": {
            name: _summary(frame[_age_band(frame["age"], low, high)])
            for name, low, high in ROSTER_BANDS
        },
        "unknown_age": _summary(frame[~_known_age(frame["age"])]),
    }


def _b2_roster(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
) -> pd.DataFrame:
    full = _full(person_wave, ANCHOR_WAVE)
    rows = valid_rows(person_wave, validity_by_wave)
    ids = rows.loc[rows["period"] == ANCHOR_WAVE, "person_id"]
    return full[full["person_id"].isin(ids)].copy()


def roster_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    anchor: pd.DataFrame,
    design: pd.DataFrame,
) -> dict[str, Any]:
    """H's three candidate rosters, with each roster's own 2011 weight."""
    proxy = _present(
        anchor[[column for column in PERSON_COLUMNS if column != "period"]]
    )
    proxy = proxy[_known_age(proxy["age"]) & (proxy["age"] >= 30)]
    frames = {
        "R_FULL": _full(person_wave, ANCHOR_WAVE),
        "R_B2": _b2_roster(person_wave, validity_by_wave),
        "R_TA_PROXY": proxy,
    }
    return {
        name: _roster_summary(_with_design(frame, design))
        for name, frame in frames.items()
    }


def b3_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    design: pd.DataFrame,
) -> dict[str, Any]:
    """B3's valid-row support and same-person lag pairs at later-wave age."""
    rows = _with_design(valid_rows(person_wave, validity_by_wave), design)
    by_wave = {}
    for wave in WAVES:
        by_band = {}
        for name, low, high in OLDER_BANDS:
            cell = rows[
                (rows["period"] == wave) & _age_band(rows["age"], low, high)
            ]
            by_band[name] = {
                **_summary(cell),
                "valid_rows": int(len(cell)),
                "accuracy_positive_rows": int(cell["acc_flag"].sum()),
            }
        by_wave[str(wave)] = by_band
    pairs = {}
    for lag in LAGS:
        by_pair = {}
        for wave in WAVES:
            later = wave + lag
            if later not in WAVES:
                continue
            earlier_ids = rows.loc[rows["period"] == wave, "person_id"]
            both = rows[
                (rows["period"] == later) & rows["person_id"].isin(earlier_ids)
            ]
            by_pair[f"{wave}_{later}"] = {
                name: int(
                    both.loc[
                        _age_band(both["age"], low, high), "person_id"
                    ].nunique()
                )
                for name, low, high in OLDER_BANDS
            }
        pairs[str(lag)] = by_pair
    return {
        "by_wave": by_wave,
        "distinct_persons_by_band": {
            name: int(
                rows.loc[
                    _age_band(rows["age"], low, high), "person_id"
                ].nunique()
            )
            for name, low, high in OLDER_BANDS
        },
        "lag_pairs": pairs,
    }


def b3l_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    design: pd.DataFrame,
) -> dict[str, Any]:
    """B3L's 2006-reference roster and later support with fixed weights."""
    full = _full(person_wave, B3L_ORIGIN_WAVE)
    rows = valid_rows(person_wave, validity_by_wave)
    origin_ids = rows.loc[rows["period"] == B3L_ORIGIN_WAVE, "person_id"]
    domain = full[full["person_id"].isin(origin_ids)]
    later_rows = rows[rows["person_id"].isin(domain["person_id"])].copy()
    later_rows["weight"] = later_rows["person_id"].map(
        domain.set_index("person_id")["weight"]
    )
    support = {}
    for wave in WAVES:
        if wave < 2009:
            continue
        support[str(wave)] = {}
        for name, low, high in (*CONTEXT_BANDS, *OLDER_BANDS):
            cell = later_rows[
                (later_rows["period"] == wave)
                & _age_band(later_rows["age"], low, high)
            ]
            support[str(wave)][name] = {
                "persons": int(cell["person_id"].nunique()),
                "kish_n_eff": kish_n_eff(cell["weight"].to_numpy(dtype=float)),
            }
    return {
        "origin_wave": B3L_ORIGIN_WAVE,
        "rosters": {
            "R2006_FULL": _roster_summary(_with_design(full, design)),
            "D2006": _roster_summary(_with_design(domain, design)),
        },
        "later_support": support,
    }


def outside_b2_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    design: pd.DataFrame,
) -> dict[str, Any]:
    """Exclude every 2011 household containing an R_B2 person."""
    full = _full(person_wave, ANCHOR_WAVE)
    domain = _b2_roster(person_wave, validity_by_wave)
    outside = full[~full["interview"].isin(domain["interview"])]
    later_households = {}
    for wave in (2013, 2015):
        containing = person_wave[
            (person_wave["period"] == wave)
            & person_wave["sequence"].between(1, 20)
            & person_wave["person_id"].isin(domain["person_id"])
        ]
        later_households[str(wave)] = int(containing["interview"].nunique())
    return {
        **_roster_summary(_with_design(outside, design)),
        "b2_households_by_wave": later_households,
    }


def structural_counts(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    anchor: pd.DataFrame,
    design: pd.DataFrame,
) -> dict[str, Any]:
    """Return only protocol-v1 counts; never return person identifiers."""
    return {
        "rosters": roster_counts(
            person_wave, validity_by_wave, anchor, design
        ),
        "b3": b3_counts(person_wave, validity_by_wave, design),
        "b3l": b3l_counts(person_wave, validity_by_wave, design),
        "outside_b2": outside_b2_counts(person_wave, validity_by_wave, design),
    }


# --------------------------------------------------------------------------
# Disclosure: unit sets stay in memory; only counts and audit sizes go local
# --------------------------------------------------------------------------
def _cell(record: dict, path: CellPath) -> Any:
    for key in path:
        record = record[key]
    return record


def _put(record: dict, path: CellPath, value: Any) -> None:
    for key in path[:-1]:
        record = record[key]
    record[path[-1]] = value


def _leaves(record: dict, prefix: CellPath = ()):
    for key, value in record.items():
        path = (*prefix, key)
        if isinstance(value, dict):
            yield from _leaves(value, path)
        elif key != "origin_wave":  # geometry, not a count
            yield path, value


class SetRegistry:
    """Every count's private unit set, its effective-size count bound and
    the relations between counts of different unit types, and the sets an
    earlier release published with their exact public values."""

    def __init__(self):
        self.sets: dict[CellPath, tuple[str, frozenset]] = {}
        self.effective_bounds: dict[CellPath, CellPath] = {}
        self.relations: list[tuple[str, CellPath, CellPath]] = []
        self.prior: dict[CellPath, tuple[str, frozenset, int]] = {}

    def _new(self, path: CellPath) -> None:
        if (
            path in self.sets
            or path in self.effective_bounds
            or path in self.prior
        ):
            raise ValueError(f"duplicate registry path: {path}")

    def add(self, path: CellPath, unit_type: str, units) -> None:
        self._new(path)
        self.sets[path] = (unit_type, frozenset(units))

    def add_prior(
        self, path: CellPath, unit_type: str, units, value: int
    ) -> None:
        """Record a set an earlier release published, with the exact count
        it published. It constrains the audit like any published count but
        is not this release's: see ``build_model`` for its targets."""
        self._new(path)
        self.prior[path] = (unit_type, frozenset(units), int(value))

    def effective(self, path: CellPath, count_path: CellPath) -> None:
        self._new(path)
        if count_path not in self.sets:
            raise ValueError("effective-size bound needs a registered count")
        self.effective_bounds[path] = count_path

    def relate(self, kind: str, left: CellPath, right: CellPath) -> None:
        """Record that ``count(left) <= count(right)`` ("at_most"), or that
        ``count(left) >= 1`` implies ``count(right) >= 1`` ("nonempty").
        Only relations the rows guarantee are recorded (``frame_relations``),
        and the audit uses every one of them."""
        if kind not in RELATIONS:
            raise ValueError(f"unknown relation: {kind}")
        if left not in self.sets or right not in self.sets:
            raise ValueError("a relation needs two registered counts")
        self.relations.append((kind, left, right))


def coarsen(value: int | float, base: int) -> int | str:
    """Round halves up, preserving zero and hiding positive values below B."""
    if value < 0 or not np.isfinite(value):
        raise ValueError(
            "counts and effective sizes must be finite and nonnegative"
        )
    if value == 0:
        return 0
    if value < base:
        return f"<{base}"
    return int((Decimal(str(value)) / base + Decimal("0.5")) // 1) * base


def count_interval(value: int | str, base: int) -> tuple[int, int]:
    """The integers whose coarsening at ``base`` is ``value``. A published
    multiple covers the half-open band around it, except that ``base``
    itself starts at ``base``: smaller values are written ``"<B"``."""
    if value == 0:
        return 0, 0
    if value == f"<{base}":
        return 1, base - 1
    return max(int(value - base // 2), base), int(value + base // 2 - 1)


def effective_count_bound(value: int | str, base: int) -> int:
    """The least count of units consistent with a published effective
    size: an effective size never exceeds the count it is computed over,
    and a positive one needs at least one unit."""
    if value == 0:
        return 0
    if value == f"<{base}":
        return 1
    return max(base, math.ceil(value - base / 2))


def build_model(registry: SetRegistry) -> dict:
    """Rows, atoms and targets for the audit.

    A row is one distinct set, this release's or an earlier release's;
    paths with identical sets of one unit type share it. An atom is the
    class of units of one type that belong to exactly the same rows, so
    every count is a sum of atom sizes.

    The targets are this release's: each class of units that belong to
    exactly the same rows of this release (a union of atoms), and every
    difference between a row and a proper subset of it of the same type.
    The one exception is a difference that is not between two of this
    release's rows, when an earlier release published both rows exactly
    and so already fixed it. Each target is audited once whatever its true
    size. Which targets are this release's own (a class, or a difference
    of two of its rows), and their order, depend on this release's sets
    alone. No unit identifier or membership leaves memory."""
    grouped: dict[tuple[str, frozenset], list[CellPath]] = {}
    for path, key in registry.sets.items():
        grouped.setdefault(key, []).append(path)
    for path, (unit_type, units, _) in registry.prior.items():
        grouped.setdefault((unit_type, units), []).append(path)
    keys = list(grouped)
    path_rows = {
        path: row for row, key in enumerate(keys) for path in grouped[key]
    }
    current = [
        any(path in registry.sets for path in grouped[key]) for key in keys
    ]
    earlier = [
        any(path in registry.prior for path in grouped[key]) for key in keys
    ]
    memberships: dict[tuple[str, Any], list[int]] = {}
    for row, (unit_type, units) in enumerate(keys):
        for unit in units:
            memberships.setdefault((unit_type, unit), []).append(row)
    sizes = Counter(
        (unit_type, tuple(rows))
        for (unit_type, _), rows in memberships.items()
    )
    atoms = sorted(sizes)
    row_indices: list[int] = []
    col_indices: list[int] = []
    for column, (_, signature) in enumerate(atoms):
        row_indices.extend(signature)
        col_indices.extend([column] * len(signature))
    matrix = csr_matrix(
        (
            np.ones(len(row_indices), dtype=np.int64),
            (row_indices, col_indices),
        ),
        shape=(len(keys), len(atoms)),
    )
    true_sizes = np.array([sizes[atom] for atom in atoms], dtype=np.int64)
    unit_types = [unit_type for unit_type, _ in atoms]
    row_atoms = [
        matrix.indices[matrix.indptr[row] : matrix.indptr[row + 1]]
        for row in range(len(keys))
    ]
    own: dict[tuple[str, tuple[int, ...]], list[int]] = {}
    for column, (unit_type, signature) in enumerate(atoms):
        rows = tuple(row for row in signature if current[row])
        if rows:
            own.setdefault((unit_type, rows), []).append(column)
    targets: dict[tuple[int, ...], dict] = {}
    for (unit_type, rows), columns in sorted(own.items()):
        held = set(rows)
        targets[tuple(columns)] = {
            "kind": "atom",
            "unit_type": unit_type,
            # The paths of this release's sets that hold the class, in the
            # release's order.
            "sets": [
                list(path) for path in registry.sets if path_rows[path] in held
            ],
            "earlier": False,
        }
    shared = (matrix @ matrix.T).toarray()
    pairs = []
    for subset in range(len(keys)):
        if shared[subset, subset] == 0:
            continue
        for superset in np.flatnonzero(
            shared[subset] == shared[subset, subset]
        ):
            if superset == subset or keys[superset][0] != keys[subset][0]:
                continue
            if (
                earlier[subset]
                and earlier[superset]
                and not (current[subset] and current[superset])
            ):
                # The earlier release published both exactly, which already
                # fixes the difference, and it is not one of this release's
                # own: two of this release's sets always make a target.
                continue
            pairs.append((subset, int(superset)))
    # Differences of this release's own sets come first, so that one which
    # holds the same units as a difference involving an earlier set is
    # this release's, and their order does not depend on the earlier sets.
    pairs.sort(key=lambda pair: not (current[pair[0]] and current[pair[1]]))
    for subset, superset in pairs:
        inner = set(row_atoms[subset].tolist())
        # A distinct row holding every atom of ``subset`` is a proper
        # superset, so the difference is nonempty.
        columns = tuple(
            int(c) for c in row_atoms[superset] if int(c) not in inner
        )
        targets.setdefault(
            columns,
            {
                "kind": "difference",
                "unit_type": keys[subset][0],
                "superset": list(grouped[keys[superset]][0]),
                "subset": list(grouped[keys[subset]][0]),
                # It involves a set only the earlier release counts.
                "earlier": not (current[superset] and current[subset]),
            },
        )
    target_list = [
        {
            "columns": columns,
            **detail,
            "true_size": int(true_sizes[list(columns)].sum()),
        }
        for columns, detail in targets.items()
    ]
    return {
        "paths": [grouped[key][0] for key in keys],
        "path_rows": path_rows,
        "matrix": matrix,
        "sizes": true_sizes,
        "unit_types": unit_types,
        "targets": target_list,
    }


def published_bounds(
    counts: dict, registry: SetRegistry, model: dict, base: int
) -> tuple[np.ndarray, np.ndarray]:
    """Each row's count interval from its published value, raised by any
    published effective size computed over it. An earlier release's
    count fixes its row exactly."""
    rows = model["matrix"].shape[0]
    lower = np.zeros(rows, dtype=np.int64)
    upper = np.full(rows, np.iinfo(np.int64).max, dtype=np.int64)
    for path in registry.sets:
        row = model["path_rows"][path]
        low, high = count_interval(coarsen(_cell(counts, path), base), base)
        lower[row] = max(lower[row], low)
        upper[row] = min(upper[row], high)
    for path, (_, _, value) in registry.prior.items():
        row = model["path_rows"][path]
        lower[row] = max(lower[row], value)
        upper[row] = min(upper[row], value)
    for path, count_path in registry.effective_bounds.items():
        row = model["path_rows"][count_path]
        bound = effective_count_bound(coarsen(_cell(counts, path), base), base)
        lower[row] = max(lower[row], bound)
    return lower, upper


def model_relations(
    registry: SetRegistry, model: dict
) -> list[tuple[str, int, int]]:
    """The registry's relations as rows. They are guaranteed by the rows
    that built them, so a true set violating one is a defect, not data."""
    relations = set()
    for kind, left, right in registry.relations:
        a = len(registry.sets[left][1])
        b = len(registry.sets[right][1])
        if not ((a <= b) if kind == "at_most" else (a == 0 or b >= 1)):
            raise ValueError(f"a guaranteed relation fails: {kind} {left}")
        relations.add(
            (kind, model["path_rows"][left], model["path_rows"][right])
        )
    return sorted(relations)


class AuditSystem:
    """The published constraints, the cross-type relations and the targets
    disclosed to lie outside 1 to 9, over integer atom sizes.

    The reader is assumed to know which atoms are possible but not their
    sizes, so any atom may be empty.

    Variables are the atom sizes, then one binary per disclosed target:
    0 forces that target's size to 0, 1 forces it to at least the
    threshold. Every solver answer used as a witness is rounded and checked
    here in exact integer arithmetic, so a protection claim never rests on
    solver tolerances."""

    def __init__(
        self, model, lower, upper, relations, disclosed, before_program=None
    ):
        self.before_program = before_program
        matrix = model["matrix"]
        self.matrix = matrix
        self.atoms = matrix.shape[1]
        self.lower = lower
        self.upper = upper
        self.relations = relations
        self.disclosed = [tuple(target["columns"]) for target in disclosed]
        csc = matrix.tocsc()
        self.cap = np.array(
            [
                int(
                    upper[csc.indices[csc.indptr[c] : csc.indptr[c + 1]]].min()
                )
                for c in range(self.atoms)
            ],
            dtype=np.int64,
        )
        binaries = len(self.disclosed)
        blocks = [hstack([matrix, csr_matrix((matrix.shape[0], binaries))])]
        low = [lower.astype(float)]
        high = [upper.astype(float)]
        for kind, a, b in relations:
            if kind == "at_most":
                row = matrix[a] - matrix[b]
            else:
                # count(a) <= upper(a) * count(b): count(b) = 0 forces
                # count(a) = 0.
                row = matrix[a] - int(upper[a]) * matrix[b]
            blocks.append(hstack([row, csr_matrix((1, binaries))]))
            low.append(np.array([-np.inf]))
            high.append(np.array([0.0]))
        for index, columns in enumerate(self.disclosed):
            indicator = np.zeros(self.atoms)
            indicator[list(columns)] = 1
            bound = float(self.cap[list(columns)].sum())
            for coefficient, lo, hi in (
                (-bound, -np.inf, 0.0),
                (-float(DISCLOSURE_THRESHOLD), 0.0, np.inf),
            ):
                binary = np.zeros(binaries)
                binary[index] = coefficient
                blocks.append(csr_matrix(np.concatenate([indicator, binary])))
                low.append(np.array([lo]))
                high.append(np.array([hi]))
        self.constraint = LinearConstraint(
            vstack(blocks).tocsr(), np.concatenate(low), np.concatenate(high)
        )
        self.variables = self.atoms + binaries
        self.bounds = Bounds(
            0, np.concatenate([self.cap, np.ones(binaries)]).astype(float)
        )

    def feasible(self, sizes: np.ndarray) -> bool:
        """Whether integer atom sizes satisfy every constraint exactly."""
        if sizes.shape != (self.atoms,) or np.any(sizes < 0):
            return False
        totals = self.matrix @ sizes
        if np.any(totals < self.lower) or np.any(totals > self.upper):
            return False
        for kind, a, b in self.relations:
            if kind == "at_most" and totals[a] > totals[b]:
                return False
            if kind == "nonempty" and totals[a] >= 1 and totals[b] < 1:
                return False
        for columns in self.disclosed:
            size = int(sizes[list(columns)].sum())
            if 1 <= size < DISCLOSURE_THRESHOLD:
                return False
        return True

    def _program(self, objective, extra, seconds, integral=True, gap=0.0):
        if self.before_program is not None:
            # The run's conditions, checked and waited out between
            # programs, never during one.
            self.before_program()
        with warnings.catch_warnings():
            # HiGHS receives threads verbatim. Both its internal threads
            # and the required BLAS environment stay at one.
            warnings.filterwarnings(
                "ignore",
                message="Unrecognized options detected.*",
                category=RuntimeWarning,
            )
            return milp(
                objective,
                integrality=np.full(self.variables, int(integral)),
                bounds=self.bounds,
                constraints=[self.constraint, *extra],
                options={
                    "disp": False,
                    "time_limit": seconds,
                    "mip_rel_gap": gap,
                    "threads": 1,
                },
            )

    def _witness(self, result, columns=None, low=None, high=None):
        if result.x is None:
            return None
        values = np.asarray(result.x[: self.atoms], dtype=float)
        sizes = np.rint(values)
        if np.any(np.abs(values - sizes) > 1e-6):
            return None
        sizes = sizes.astype(np.int64)
        if not self.feasible(sizes):
            return None
        if columns is not None:
            size = int(sizes[list(columns)].sum())
            if (low is not None and size < low) or (
                high is not None and size > high
            ):
                return None
        return sizes

    def _window(self, columns, low, high):
        row = np.zeros(self.variables)
        row[list(columns)] = 1
        return LinearConstraint(
            row,
            -np.inf if low is None else low,
            np.inf if high is None else high,
        )

    def search(self, columns, low=None, high=None, *, seconds):
        """A verified integer point whose target size is in [low, high],
        and the solver's status: 2 proves that no such point exists."""
        result = self._program(
            np.zeros(self.variables),
            [self._window(columns, low, high)],
            seconds,
        )
        return int(result.status), self._witness(result, columns, low, high)

    def extreme(self, columns, sense, low, high, *, seconds):
        """The proven optimum of the target size (sense 1 maximizes, -1
        minimizes) within [low, high], with its verified witness, or None
        when the solver proves no optimum."""
        objective = np.zeros(self.variables)
        objective[list(columns)] = -sense
        result = self._program(
            objective, [self._window(columns, low, high)], seconds
        )
        witness = self._witness(result, columns, low, high)
        if int(result.status) != 0 or witness is None:
            return None
        return int(witness[list(columns)].sum()), witness

    def relaxed_minimum(self, columns, *, seconds) -> float | None:
        """The continuous relaxation's minimum of the target size, a lower
        bound on every integer value, or None."""
        objective = np.zeros(self.variables)
        objective[list(columns)] = 1
        result = self._program(objective, [], seconds, integral=False)
        return float(result.fun) if int(result.status) == 0 else None

    def direction(self, weights, *, seconds):
        """A verified point pushed along a fixed linear direction. It only
        seeds the witness pool, so the first integer point HiGHS accepts
        will do; no optimum is needed."""
        objective = np.concatenate(
            [weights, np.zeros(self.variables - self.atoms)]
        )
        return self._witness(self._program(objective, [], seconds, gap=1.0))


class WitnessPool:
    """Verified feasible points, kept as rows so that a target's values over
    all of them are one vectorized sum. Every point comes from a program
    that uses no true size, so the pool is the same for every table with
    the same publication; at most ``POOL_LIMIT`` points are kept."""

    def __init__(self, atoms: int):
        self.points = np.empty((16, atoms), dtype=np.int64)
        self.size = 0

    def add(self, point: np.ndarray) -> None:
        if self.size >= POOL_LIMIT:
            return
        if self.size == len(self.points):
            grown = np.empty((2 * self.size, self.points.shape[1]), np.int64)
            grown[: self.size] = self.points[: self.size]
            self.points = grown
        self.points[self.size] = point
        self.size += 1

    def keep(self, system: AuditSystem) -> None:
        """Drop points that a newly disclosed target makes infeasible."""
        kept = [
            row
            for row in range(self.size)
            if system.feasible(self.points[row])
        ]
        self.points[: len(kept)] = self.points[kept]
        self.size = len(kept)

    def values(self, columns: list[int]) -> tuple[int, int]:
        """The least and greatest target size over the pool."""
        values = self.points[: self.size, columns].sum(axis=1)
        return int(values.min()), int(values.max())


def seed_pool(system: AuditSystem, pool: WitnessPool, *, seconds) -> None:
    """Add the seed programs' verified points: any feasible vector, then
    one pushed along each of the fixed seeded directions. The directions
    depend only on the number of atoms, so every seeding draws the same
    ones."""
    generator = np.random.default_rng(POOL_SEED)
    seeds = [np.zeros(system.atoms)] + [
        generator.choice([-1.0, 1.0], size=system.atoms)
        for _ in range(POOL_DIRECTIONS)
    ]
    for weights in seeds:
        point = system.direction(weights, seconds=seconds)
        if point is not None:
            pool.add(point)


def classify(system: AuditSystem, target: dict, pool: WitnessPool, *, seconds):
    """Whether one target's integer range under ``system`` is at least the
    protection width ("wide"), cannot reach 1 to 9 ("irrelevant"), or is
    neither proven ("narrow"). A wide verdict always rests on two verified
    integer points; anything unproven is narrow.

    Every program here is set from the pool and the system alone, never
    from the target's true size, so a reader holding the publication can
    rerun it. An empty pool sets no window, so the target is unproven:
    narrow."""
    record = {"programs": []}
    if pool.size == 0:
        return {**record, "result": "narrow", "proof": "undetermined"}, None
    columns = list(target["columns"])
    low, high = pool.values(columns)
    if high - low >= PROTECTION_WIDTH:
        return {**record, "result": "wide", "proof": "pool"}, None
    if low >= DISCLOSURE_THRESHOLD:
        relaxed = system.relaxed_minimum(columns, seconds=seconds)
        record["programs"].append("relaxation")
        # Every integer value is at least the relaxation's minimum; the
        # half-unit margin absorbs solver tolerance.
        if relaxed is not None and relaxed > DISCLOSURE_THRESHOLD - 0.5:
            return {**record, "result": "irrelevant"}, None
    proven_absent = True
    for window_low, window_high in (
        (low + PROTECTION_WIDTH, None),
        (None, high - PROTECTION_WIDTH),
    ):
        if window_high is not None and window_high < 0:
            continue
        status, witness = system.search(
            columns, window_low, window_high, seconds=seconds
        )
        record["programs"].append(status)
        if witness is not None:
            return {**record, "result": "wide", "proof": "search"}, witness
        proven_absent = proven_absent and status == 2
    if not proven_absent:
        return {**record, "result": "narrow", "proof": "undetermined"}, None
    # No size lies outside this window, which holds every pool value.
    window = (max(0, high - PROTECTION_WIDTH + 1), low + PROTECTION_WIDTH - 1)
    extremes = [
        system.extreme(columns, sense, *window, seconds=seconds)
        for sense in (1, -1)
    ]
    record["programs"].extend(["maximum", "minimum"])
    if any(extreme is None for extreme in extremes):
        return {**record, "result": "narrow", "proof": "undetermined"}, None
    (maximum, upper_point), (minimum, lower_point) = extremes
    record["range"] = [minimum, maximum]
    if maximum - minimum >= PROTECTION_WIDTH:
        return {**record, "result": "wide", "proof": "optima"}, upper_point
    if minimum >= DISCLOSURE_THRESHOLD or maximum == 0:
        return {**record, "result": "irrelevant", "proof": "optima"}, None
    return {**record, "result": "narrow", "proof": "optima"}, None


def audit_counts(
    counts: dict,
    registry: SetRegistry,
    base: int = DISCLOSURE_BASE,
    *,
    seconds: float = PROGRAM_SECONDS,
    before_program: Callable[[], None] | None = None,
) -> dict:
    """Decide whether the counts may be released at ``base``.

    Every program, its window and the order of targets depend only on the
    publication, the registry's structure and the targets disclosed so
    far. True sizes enter only the test that withholds: a target of true
    size 1 to 9 found narrow. So each round's narrow targets are the same
    for every table with this publication, and a release tells a reader
    exactly that every narrow target lies outside 1 to 9. Each narrow
    target is therefore added to the constraints as disclosed, and every
    target not yet disclosed is classified again, until a round adds none.
    Every target of true size 1 to 9 is then wide under everything a
    release discloses. A round whose disclosures rule out every pool
    point seeds the pool again under them; if no seed program then finds
    a point, nothing can be shown wide and the release is withheld.

    Each target's final decision is its classification in the round that
    ended the audit, or in the round that disclosed it or proved it
    irrelevant, which no later round changes. A target the ending round
    did not reach is "unreached", whichever round that was, so the
    decisions show no round. ``before_program`` is called before every
    program (``RunConditions.before_program``)."""
    started = time.monotonic()
    _validate_registry(counts, registry)
    model = build_model(registry)
    lower, upper = published_bounds(counts, registry, model, base)
    relations = model_relations(registry, model)
    targets = model["targets"]
    truth = model["sizes"]
    disclosed: list[int] = []
    settled: dict[int, dict] = {}
    rounds = []
    status = "released"
    pool = WitnessPool(len(truth))
    if targets:
        system = AuditSystem(
            model, lower, upper, relations, [], before_program
        )
        if not system.feasible(truth):
            raise ValueError(
                "true atom sizes violate the published constraints"
            )
        seed_pool(system, pool, seconds=seconds)
        if pool.size == 0:
            # No program found a point, so nothing can be shown wide.
            status = "withheld"
    # With no atom there is nothing to protect and no program to run.
    while status == "released" and targets:
        system = AuditSystem(
            model,
            lower,
            upper,
            relations,
            [targets[i] for i in disclosed],
            before_program,
        )
        pool.keep(system)
        reseeded = pool.size == 0
        if reseeded:
            # The disclosures ruled out every point: seed again under them.
            seed_pool(system, pool, seconds=seconds)
            if pool.size == 0:
                status = "withheld"
                rounds.append(
                    {
                        "round": len(rounds) + 1,
                        "disclosed": [],
                        "reseeded": True,
                    }
                )
                break
        added = []
        for index in range(len(targets)):
            if index in disclosed:
                continue
            if settled.get(index, {}).get("result") == "irrelevant":
                # Constraints only tighten, so it stays out of 1 to 9.
                continue
            outcome, witness = classify(
                system, targets[index], pool, seconds=seconds
            )
            settled[index] = {**outcome, "round": len(rounds) + 1}
            if witness is not None:
                pool.add(witness)
            if outcome["result"] != "narrow":
                continue
            if 1 <= targets[index]["true_size"] < DISCLOSURE_THRESHOLD:
                status = "withheld"
                break
            added.append(index)
        rounds.append(
            {
                "round": len(rounds) + 1,
                "disclosed": added,
                "reseeded": reseeded,
            }
        )
        if not added:
            break
        disclosed.extend(added)
    ending = len(rounds)

    def decision(index: int) -> dict:
        outcome = settled.get(index)
        if outcome is not None and (
            outcome["round"] == ending
            or index in disclosed
            or outcome["result"] == "irrelevant"
        ):
            return outcome
        return {"result": "unreached"}

    return {
        "base": base,
        "status": status,
        "rounds": rounds,
        "disclosed": disclosed,
        "targets": [
            {
                "unit_type": target["unit_type"],
                "kind": target["kind"],
                "columns": list(target["columns"]),
                **{
                    key: target[key]
                    for key in ("sets", "superset", "subset")
                    if key in target
                },
                "true_size": target["true_size"],
                "earlier": target["earlier"],
                **decision(index),
            }
            for index, target in enumerate(targets)
        ],
        "relations": len(relations),
        "pool": pool.size,
        "seconds": round(time.monotonic() - started, 3),
        "atom_sizes": {
            unit_type: [
                int(size)
                for size, kind in zip(
                    model["sizes"], model["unit_types"], strict=True
                )
                if kind == unit_type
            ]
            for unit_type in dict.fromkeys(model["unit_types"])
        },
    }


def _validate_registry(counts: dict, registry: SetRegistry) -> None:
    if set(dict(_leaves(counts))) != set(registry.sets) | set(
        registry.effective_bounds
    ):
        raise ValueError(
            "every published statistic must be registered exactly once"
        )
    for path, (_, units) in registry.sets.items():
        if _cell(counts, path) != len(units):
            raise ValueError(
                f"registered set size disagrees with count: {path}"
            )
    for path, (_, units, value) in registry.prior.items():
        if value != len(units):
            raise ValueError(
                f"an earlier release's count disagrees with its set: {path}"
            )


#: What the local copy records of each of this release's targets: what it
#: is (its unit type and kind, and its sets: those of this release that
#: hold a class, or a difference's superset and subset), its true size,
#: and the audit's final decision about it.
TARGET_FIELDS = (
    "unit_type",
    "kind",
    "sets",
    "superset",
    "subset",
    "true_size",
    "result",
)


def local_audit(audit: dict) -> dict:
    """The audit as the local copy records it: this release's own counts and
    the audit's decisions, and nothing else.

    B0.1's sets enter the audit in memory only (protocol, "What this audit
    may and may not compute"), so nothing about them beyond B0.1's own
    counts is written. The record holds the base and the status; for each
    target of this release (a class of its units, or a difference of two
    of its sets), what it is, its true size and its final classification
    ("unreached" when the round that ended the audit did not reach it);
    and its classes' sizes, by unit type. Targets that involve a set only
    B0.1 counts are left out. So are the rounds: which round disclosed or
    settled a target, whether the pool was seeded again and how many
    rounds ran would add resolution to the one channel the decisions
    open, and a rerun of the frozen code on the frozen inputs gives them
    again. So are the atoms, which B0.1's sets refine, and everything
    computed from them that is not a decision: each target's atom
    columns, proof, programs and range, the pool's size, the relation
    count and the timing."""
    targets = [
        {key: target[key] for key in TARGET_FIELDS if key in target}
        for target in audit["targets"]
        if not target["earlier"]
    ]
    class_sizes: dict[str, list[int]] = {}
    for target in targets:
        if target["kind"] == "atom":
            class_sizes.setdefault(target["unit_type"], []).append(
                target["true_size"]
            )
    return {
        "base": audit["base"],
        "status": audit["status"],
        "targets": targets,
        "class_sizes": class_sizes,
    }


def release_counts(
    counts: dict,
    registry: SetRegistry,
    base: int = DISCLOSURE_BASE,
    *,
    before_program: Callable[[], None] | None = None,
) -> tuple[dict, dict, dict]:
    """Coarsen and audit once at the fixed base. The public block holds the
    base, the rules and the status, and nothing the audit computed; the
    local copy holds ``local_audit``'s record."""
    audit = audit_counts(counts, registry, base, before_program=before_program)
    published = {}
    if audit["status"] == "released":
        published = deepcopy(counts)
        for path, value in _leaves(counts):
            _put(published, path, coarsen(value, base))
    disclosure = {
        "base": base,
        "coarsening_rule": COARSENING_RULE,
        "protection_rule": PROTECTION_RULE,
        "status": audit["status"],
    }
    return published, disclosure, {"audit": local_audit(audit)}


def frame_relations(frame: pd.DataFrame) -> dict[tuple[str, str, str], bool]:
    """Which cross-type relations the frame's rows guarantee, whatever the
    counts. A relation is registered only where its rows guarantee it, so
    the audit's relations are structure, fixed before any size is used.

    A household, or a design cluster, comes from at least one row, so when
    every such row carries a person and no person has two rows, distinct
    households (clusters) hold distinct persons. A stratum always comes
    with a cluster of its own, and any row yields a cluster."""
    has_person = frame["person_id"].notna()
    one_row_each = bool(frame.loc[has_person, "person_id"].is_unique)
    return {
        ("at_most", "households", "persons"): one_row_each
        and bool((has_person | frame["interview"].isna()).all()),
        ("at_most", "design_clusters", "persons"): one_row_each
        and bool(has_person.all()),
        ("at_most", "design_strata", "design_clusters"): True,
        ("nonempty", "persons", "households"): bool(
            frame.loc[has_person, "interview"].notna().all()
        ),
        ("nonempty", "persons", "design_clusters"): True,
        ("nonempty", "persons", "design_strata"): bool(
            frame.loc[has_person, "stratum"].notna().all()
        ),
    }


def disclosure_registry(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    anchor: pd.DataFrame,
    design: pd.DataFrame,
) -> SetRegistry:
    """Register every count by persons, wave households, strata or clusters."""
    registry = SetRegistry()

    def register(prefix, frame, wave):
        def clean(value):
            return None if pd.isna(value) else value

        units = {
            "persons": ("persons", frame["person_id"].dropna()),
            "households": (f"households_{wave}", frame["interview"].dropna()),
            "design_strata": ("strata", frame["stratum"].dropna()),
            "design_clusters": (
                "clusters",
                [
                    (clean(stratum), clean(cluster))
                    for stratum, cluster in frame[["stratum", "cluster"]]
                    .drop_duplicates()
                    .itertuples(index=False, name=None)
                ],
            ),
        }
        for metric, (unit_type, members) in units.items():
            registry.add((*prefix, metric), unit_type, members)
        for (kind, left, right), guaranteed in frame_relations(frame).items():
            if guaranteed:
                registry.relate(kind, (*prefix, left), (*prefix, right))
        for effective, count in (
            ("kish_n_eff", "persons"),
            ("household_cluster_worst_n_eff", "households"),
            ("design_cluster_worst_n_eff", "design_clusters"),
        ):
            registry.effective((*prefix, effective), (*prefix, count))

    def roster(prefix, frame, wave):
        register((*prefix, "overall"), frame, wave)
        for name, low, high in ROSTER_BANDS:
            register(
                (*prefix, "by_age_band", name),
                frame[_age_band(frame["age"], low, high)],
                wave,
            )
        register(
            (*prefix, "unknown_age"), frame[~_known_age(frame["age"])], wave
        )

    full = _with_design(_full(person_wave, ANCHOR_WAVE), design)
    domain = _with_design(_b2_roster(person_wave, validity_by_wave), design)
    proxy = _present(
        anchor[[column for column in PERSON_COLUMNS if column != "period"]]
    )
    proxy = _with_design(
        proxy[_known_age(proxy["age"]) & (proxy["age"] >= 30)], design
    )
    for name, frame in (
        ("R_FULL", full),
        ("R_B2", domain),
        ("R_TA_PROXY", proxy),
    ):
        roster(("rosters", name), frame, ANCHOR_WAVE)
    rows = _with_design(valid_rows(person_wave, validity_by_wave), design)
    for wave in WAVES:
        for name, low, high in OLDER_BANDS:
            frame = rows[
                (rows["period"] == wave) & _age_band(rows["age"], low, high)
            ]
            prefix = ("b3", "by_wave", str(wave), name)
            register(prefix, frame, wave)
            registry.add(
                (*prefix, "valid_rows"), "persons", frame["person_id"]
            )
            registry.add(
                (*prefix, "accuracy_positive_rows"),
                "persons",
                frame.loc[frame["acc_flag"], "person_id"],
            )
    for name, low, high in OLDER_BANDS:
        registry.add(
            ("b3", "distinct_persons_by_band", name),
            "persons",
            rows.loc[_age_band(rows["age"], low, high), "person_id"],
        )
    for lag in LAGS:
        for wave in WAVES:
            later = wave + lag
            if later not in WAVES:
                continue
            earlier = rows.loc[rows["period"] == wave, "person_id"]
            both = rows[
                (rows["period"] == later) & rows["person_id"].isin(earlier)
            ]
            for name, low, high in OLDER_BANDS:
                registry.add(
                    ("b3", "lag_pairs", str(lag), f"{wave}_{later}", name),
                    "persons",
                    both.loc[_age_band(both["age"], low, high), "person_id"],
                )
    origin = _with_design(_full(person_wave, B3L_ORIGIN_WAVE), design)
    origin_ids = rows.loc[rows["period"] == B3L_ORIGIN_WAVE, "person_id"]
    origin_domain = origin[origin["person_id"].isin(origin_ids)]
    for name, frame in (("R2006_FULL", origin), ("D2006", origin_domain)):
        roster(("b3l", "rosters", name), frame, B3L_ORIGIN_WAVE)
    for wave in WAVES:
        if wave < 2009:
            continue
        for name, low, high in (*CONTEXT_BANDS, *OLDER_BANDS):
            frame = rows[
                (rows["period"] == wave)
                & rows["person_id"].isin(origin_domain["person_id"])
                & _age_band(rows["age"], low, high)
            ]
            prefix = ("b3l", "later_support", str(wave), name)
            registry.add((*prefix, "persons"), "persons", frame["person_id"])
            registry.effective((*prefix, "kish_n_eff"), (*prefix, "persons"))
    outside = full[~full["interview"].isin(domain["interview"])]
    roster(("outside_b2",), outside, ANCHOR_WAVE)
    for wave in (2013, 2015):
        frame = person_wave[
            (person_wave["period"] == wave)
            & person_wave["sequence"].between(1, 20)
            & person_wave["person_id"].isin(domain["person_id"])
        ]
        registry.add(
            ("outside_b2", "b2_households_by_wave", str(wave)),
            f"households_{wave}",
            frame["interview"].dropna(),
        )
    return registry


# --------------------------------------------------------------------------
# The earlier release: B0.1's published counts, as exact constraints
# --------------------------------------------------------------------------
#: B0.1's ledger-support fields and the B0.1 count each must equal. B0.1
#: copied them from the M6 ledgers. The M6 fit's ``fit_input_rows``, a
#: count over every reference year to 2010, is not modeled (protocol,
#: "What the audit assumes, and its limits").
B0_1_LEDGER_FIELDS = {
    "n_full_anchor": ("full_anchor_persons",),
    "n_domain": ("domain_persons",),
    "truth_support_rows": ("scored_rows_total",),
    "anchor_wave": ("anchor_wave",),
}
B0_1_EFFECTIVE = ("kish_n_eff", "cluster_worst_n_eff")


def b0_1_sums() -> dict[CellPath, list[CellPath]]:
    """B0.1's counts that are sums of its other published counts."""
    scored = [
        ("scored_support", str(year), "scored_rows")
        for year in (BOUNDARY_YEAR, *HORIZON_YEARS)
    ]
    sums = {
        ("scored_rows_total",): scored,
        ("domain_weights", "rows"): [("domain_persons",)],
        ("level_cells", "pooled", "rows"): scored[1:],
        ("change_pairs", "pooled_two_step", "rows"): [
            ("change_pairs", "pooled_two_step", "persons")
        ],
    }
    for name, _, _ in EARN_COHORTS:
        sums[("level_cells", name, "rows")] = [
            ("scored_support", str(year), "rows_by_cohort", name)
            for year in HORIZON_YEARS
        ]
    return sums


def b0_1_sets(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
) -> dict[CellPath, tuple[str, frozenset, tuple[tuple[int, CellPath], ...]]]:
    """B0.1's published counts as the sets they count, rebuilt by B0.1's
    own rules (``structural_counts`` in ``scripts/track_b_b0_1_counts.py``)
    from this script's inputs.

    Each entry maps a B0.1 count's path to its unit type, its set, and the
    published counts whose signed sum is the set's size. Households are
    2011 households, each person's from the full anchor. A change-pair
    count of rows adds two persons' sets, the one-step pairs from 2010 to
    2012 and from 2012 to 2014; given its persons, the union, it is fixed
    by the persons in both, whose size is rows minus persons. Every other
    count B0.1 publishes is a sum of these (``b0_1_sums``), an effective
    size of a count published exactly, or a wave label."""
    low, high = AGE_SUPPORT
    years = (BOUNDARY_YEAR, *HORIZON_YEARS)
    anchor_wave = BOUNDARY_YEAR + WAVE_OFFSET
    households = f"households_{anchor_wave}"
    at_anchor = person_wave[person_wave["period"] == anchor_wave]
    full = at_anchor[
        at_anchor["sequence"].between(1, 20)
        & (pd.to_numeric(at_anchor["weight"], errors="coerce") > 0)
    ]
    anchor_ids = frozenset(full["person_id"].astype("int64"))
    home = dict(
        zip(full["person_id"].astype("int64"), full["interview"], strict=True)
    )
    rows = earnings_rows(person_wave, validity_by_wave, years)
    valid = rows[rows["valid"]]
    domain = (
        frozenset(
            valid.loc[
                valid["reference_year"] == BOUNDARY_YEAR, "person_id"
            ].astype("int64")
        )
        & anchor_ids
    )
    valid = valid.assign(
        cohort=valid["age"].map(_cohort),
        in_support=valid["age"].between(low, high).to_numpy(),
        in_domain=valid["person_id"].isin(domain).to_numpy(),
    )

    def ids(frame):
        return frozenset(frame["person_id"].astype("int64"))

    def homes(persons):
        return frozenset(
            home[person] for person in persons if pd.notna(home[person])
        )

    scored = {
        year: valid[
            (valid["reference_year"] == year)
            & valid["in_support"]
            & valid["in_domain"]
        ]
        for year in years
    }
    cohorts = {
        (year, name): ids(scored[year][scored[year]["cohort"] == name])
        for year in years
        for name, _, _ in EARN_COHORTS
    }
    sets = {}

    def put(path, units, unit_type="persons", terms=None):
        sets[path] = (unit_type, frozenset(units), terms or ((1, path),))

    put(("full_anchor_persons",), anchor_ids)
    put(("full_anchor_households",), full["interview"].dropna(), households)
    put(("domain_persons",), domain)
    boundary = valid[
        (valid["reference_year"] == BOUNDARY_YEAR) & valid["in_domain"]
    ]
    for role in ("head", "spouse"):
        put(("domain_by_role", role), ids(boundary[boundary["role"] == role]))
    in_domain = full[full["person_id"].astype("int64").isin(domain)]
    age = in_domain["age"].astype("float64")
    for name, rule in (
        ("under_25", age < low),
        ("25_44", age.between(25, 44)),
        ("45_64", age.between(45, high)),
        ("65_plus", age > high),
    ):
        put(("domain_by_anchor_wave_age", name), ids(in_domain[rule]))
    put(("domain_weights", "persons"), domain)
    put(("domain_weights", "households"), homes(domain), households)
    for year in years:
        key = ("scored_support", str(year))
        put((*key, "scored_rows"), ids(scored[year]))
        for name, _, _ in EARN_COHORTS:
            put((*key, "rows_by_cohort", name), cohorts[year, name])
        outside = valid[
            (valid["reference_year"] == year)
            & valid["in_domain"]
            & ~valid["in_support"]
        ]
        put((*key, "valid_domain_rows_outside_age_support"), ids(outside))
        put(
            (*key, "assigned_or_edited_rows"),
            ids(scored[year][scored[year]["acc_flag"]]),
        )
    cells = [
        (name, [cohorts[year, name] for year in HORIZON_YEARS])
        for name, _, _ in EARN_COHORTS
    ]
    cells.append(("pooled", [ids(scored[year]) for year in HORIZON_YEARS]))
    for name, parts in cells:
        persons = frozenset().union(*parts)
        put(("level_cells", name, "persons"), persons)
        put(("level_cells", name, "households"), homes(persons), households)
    step = HORIZON_YEARS[0] - BOUNDARY_YEAR
    one_step = [(year, year + step) for year in years if year + step in years]
    if len(one_step) != 2:
        raise ValueError("B0.1's one-step pairs are not two")
    pairs = [
        (name, [cohorts[a, name] & cohorts[b, name] for a, b in one_step])
        for name, _, _ in EARN_COHORTS
    ]
    pairs.append(
        (
            "pooled_one_step",
            [ids(scored[a]) & ids(scored[b]) for a, b in one_step],
        )
    )
    for name, (first, second) in pairs:
        key = ("change_pairs", name)
        put((*key, "persons"), first | second)
        put((*key, "households"), homes(first | second), households)
        put(
            (*key, "rows"),
            first & second,
            terms=((1, (*key, "rows")), (-1, (*key, "persons"))),
        )
    both = ids(scored[BOUNDARY_YEAR]) & ids(scored[HORIZON_YEARS[-1]])
    put(("change_pairs", "pooled_two_step", "persons"), both)
    put(
        ("change_pairs", "pooled_two_step", "households"),
        homes(both),
        households,
    )
    for year in HORIZON_YEARS:
        wave = year + WAVE_OFFSET
        at_wave = person_wave[
            (person_wave["period"] == wave)
            & person_wave["person_id"].isin(domain)
        ].set_index("person_id")
        year_rows = rows[
            (rows["reference_year"] == year) & rows["person_id"].isin(domain)
        ].set_index("person_id")
        head_codes, spouse_codes = family._relationship_codes(wave)
        codes = frozenset((*head_codes, *spouse_codes))
        labels = {
            person: _disposition(person, at_wave, year_rows, codes, low, high)
            for person in sorted(domain)
        }
        for name in DISPOSITIONS:
            put(
                ("domain_dispositions", str(year), name),
                [person for person, label in labels.items() if label == name],
            )
        entering = valid[
            (valid["reference_year"] == year)
            & valid["in_support"]
            & ~valid["in_domain"]
        ]
        inside = entering["person_id"].isin(anchor_ids)
        for name, _, _ in EARN_COHORTS:
            cohort = entering["cohort"] == name
            key = ("entrants_not_scored", str(year))
            put(
                (*key, "in_2011_anchor_without_valid_boundary_row", name),
                ids(entering[cohort & inside]),
            )
            put(
                (*key, "outside_2011_anchor", name),
                ids(entering[cohort & ~inside]),
            )
    return sets


def _b0_1_leaves(record: Mapping, prefix: CellPath = ()):
    for key, value in record.items():
        if isinstance(value, Mapping):
            yield from _b0_1_leaves(value, (*prefix, key))
        else:
            yield (*prefix, key), value


def check_b0_1_record(record: Mapping, rerun: Mapping, sets: Mapping) -> None:
    """Stop unless the B0.1 record this audit constrains by is the one these
    inputs give, and every number it publishes is modeled.

    B0.1's own ``structural_counts``, rerun on this script's inputs, must
    equal its committed counts exactly, and each rebuilt set's size must be
    the signed sum of published counts its entry names. Every committed
    count must be one of ``sets``, a sum of published counts
    (``b0_1_sums``, checked), an effective size, or a wave label. Each
    copied ledger count must equal the B0.1 count it repeats. This is the
    rerun gate: it runs before any set enters the audit, and a failure
    names a path, never a value."""
    counts = record["counts"]
    if rerun != counts:
        raise AssertionError(
            "B0.1's counts rerun on these inputs differ from its record"
        )
    sums = b0_1_sums()
    labels = {("anchor_wave",)} | {
        ("scored_support", str(year), "collection_wave")
        for year in (BOUNDARY_YEAR, *HORIZON_YEARS)
    }
    leaves = dict(_b0_1_leaves(counts))
    for path, (_, units, terms) in sets.items():
        if any(part not in leaves for _, part in terms):
            raise AssertionError(f"B0.1 publishes no count for {path}")
        if len(units) != sum(sign * leaves[part] for sign, part in terms):
            raise AssertionError(
                f"a rebuilt B0.1 set is not its count: {path}"
            )
    for path, value in leaves.items():
        if path in sets or path in labels or path[-1] in B0_1_EFFECTIVE:
            continue
        if path not in sums:
            raise AssertionError(f"B0.1 count is not modeled: {path}")
        if value != sum(leaves[part] for part in sums[path]):
            raise AssertionError(f"B0.1 sum does not hold: {path}")
    if missing := set(sets) - set(leaves):
        raise AssertionError(f"B0.1 publishes no count for {sorted(missing)}")
    horizon = [str(year) for year in HORIZON_YEARS]
    for name, ledger in record["ledger_support_counts"].items():
        expected = {
            field: leaves[path] for field, path in B0_1_LEDGER_FIELDS.items()
        }
        expected["truth_support_rows_by_period"] = {
            str(year): leaves[("scored_support", str(year), "scored_rows")]
            for year in (BOUNDARY_YEAR, *HORIZON_YEARS)
        }
        expected["endpoint_support_rows"] = sum(
            leaves[("scored_support", year, "scored_rows")] for year in horizon
        )
        expected["support_age_min"] = AGE_SUPPORT[0]
        expected["support_age_max"] = AGE_SUPPORT[1]
        copied = {
            field: value
            for field, value in ledger.items()
            if field != "fit_input_rows"
        }
        if copied != expected:
            raise AssertionError(f"B0.1 ledger counts differ: {name}")


def register_b0_1(registry: SetRegistry, sets: Mapping, counts: Mapping):
    """Add B0.1's sets to the registry with their exact published sizes."""
    for path, (unit_type, units, terms) in sets.items():
        value = sum(sign * _cell(counts, part) for sign, part in terms)
        registry.add_prior(("b0_1", *path), unit_type, units, value)


# --------------------------------------------------------------------------
# Thin readers and requested-label provenance
# --------------------------------------------------------------------------
def read_inputs(
    data_dir: Path,
) -> tuple[
    pd.DataFrame, dict[int, pd.DataFrame], pd.DataFrame, pd.DataFrame, dict
]:
    """Read only the named protocol inputs; immediately reduce raw fields."""
    concepts = {
        name: panels.DEMOGRAPHIC_CONCEPTS[name] for name in INDIVIDUAL_CONCEPTS
    }
    person_wave = panels.ind_person_period(
        concepts, data_dir=data_dir, waves=list(WAVES)
    )[list(PERSON_COLUMNS)]
    anchor = psid2010.read_anchor_wave(
        data_dir=data_dir, anchor_wave=ANCHOR_WAVE
    ).drop(columns="reported_birth_year")
    design = age67.read_design_variables(data_dir=data_dir)
    validity = {
        wave: validity_frame(family.read_family_labor(wave, data_dir=data_dir))
        for wave in WAVES
    }
    identifiers = {
        "interview_1968": {
            "variable": "ER30001",
            "label": "1968 INTERVIEW NUMBER",
        },
        "person_number": {"variable": "ER30002", "label": "PERSON NUMBER 68"},
    }
    layout = psid2010.ANCHOR_LAYOUTS[ANCHOR_WAVE]
    allowlist = {
        "individual": {
            "identifiers": identifiers,
            "concepts": {
                name: list(patterns) for name, patterns in concepts.items()
            },
            "by_wave": _individual_variables(data_dir, WAVES),
        },
        "anchor_2011": {
            **identifiers,
            **{
                role: {"variable": var, "label": label}
                for role, (var, label) in layout.variables.items()
            },
        },
        "design": {
            **identifiers,
            "stratum": {
                "variable": "ER31996",
                "label": "SAMPLING ERROR STRATUM",
            },
            "cluster": {
                "variable": "ER31997",
                "label": "SAMPLING ERROR CLUSTER",
            },
        },
        "family": {
            str(wave): _family_variables(data_dir, wave) for wave in WAVES
        },
    }
    return person_wave, validity, anchor, design, allowlist


def _require_unit_identifiers(
    person_wave: pd.DataFrame, anchor: pd.DataFrame, design: pd.DataFrame
) -> None:
    """Every unit a published set counts has its identifiers: each present
    row (sequence 1 to 20, positive weight) its person and interview
    numbers, and each present person a design stratum and cluster. A row
    without one would be counted as a person but in no household or
    design cluster, so an effective size could exceed the count it
    bounds and stop the audit. The readers give integer columns, so this
    never fires on them; it stops the run while reading, before any set
    is built, rather than in the release."""
    rows = {"person-wave": _present(person_wave), "anchor": _present(anchor)}
    for name, present in rows.items():
        if present[["person_id", "interview"]].isna().any(axis=None):
            raise ValueError(
                f"a present {name} row has no person or interview number"
            )
    complete = design.dropna(subset=["person_id", "stratum", "cluster"])
    persons = pd.concat([present["person_id"] for present in rows.values()])
    if not persons.isin(complete["person_id"]).all():
        raise ValueError("a present person has no design stratum or cluster")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _check_protocol() -> None:
    """Require the reviewed block and an explicit version-1 freeze."""
    protocol = PROTOCOL_PATH.read_bytes()
    status = [
        line
        for line in protocol.decode("utf-8").splitlines()
        if line.startswith("**Status:")
    ]
    if (
        len(status) != 1
        or len(status[0].split(",")) < 2
        or status[0].split(",")[1].strip() != "FROZEN"
    ):
        raise SystemExit("B0.2 requires protocol status FROZEN")
    begin = b"<!-- protocol:begin -->"
    end = b"<!-- protocol:end -->"
    if protocol.count(begin) != 1 or protocol.count(end) != 1:
        raise SystemExit("B0.2 protocol block does not match its SHA-256 pin")
    start, stop = protocol.index(begin), protocol.index(end) + len(end)
    if stop <= start or hashlib.sha256(protocol[start:stop]).hexdigest() != (
        PROTOCOL_SHA256
    ):
        raise SystemExit("B0.2 protocol block does not match its SHA-256 pin")


def _attempt_path(local_copy: Path) -> Path:
    """One name per protocol version, independent of output filenames."""
    return local_copy.parent / f"{SCHEMA}.attempt.json"


def _start_attempt(
    local_copy: Path, repository_head: str, script_sha256: str
) -> None:
    attempt = _attempt_path(local_copy)
    record = {
        "repository_head": repository_head,
        "script_sha256": script_sha256,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with attempt.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise SystemExit(
            f"B0.2 protocol version already has an attempt record: {attempt}"
        ) from error


#: macOS's power-management and Core Foundation libraries, which the run's
#: conditions call through ``ctypes``.
IOKIT = "/System/Library/Frameworks/IOKit.framework/IOKit"
CORE_FOUNDATION = (
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)
#: The power source IOKit names while the host draws from the mains.
AC_POWER = "AC Power"
#: The sleep assertions the run holds on its own process: no idle sleep,
#: and no system sleep while on AC power. The system releases both when
#: the process ends.
SLEEP_ASSERTIONS = ("PreventUserIdleSystemSleep", "PreventSystemSleep")
#: ``PRIO_DARWIN_PROCESS`` in <sys/resource.h>, which Python names only
#: from 3.12: ``getpriority`` reads 1 for it under the Darwin background
#: policy (``taskpolicy -b``) and 0 otherwise.
PRIO_DARWIN_PROCESS = 4
#: The run's QoS class must be unspecified, or the default or above
#: (<sys/qos.h>: user-initiated is 0x19 and user-interactive 0x21). Below
#: the default are utility (0x11), background (0x09) and maintenance
#: (0x05); a process clamped to one (``taskpolicy -c``) reads it as its
#: thread's class, with niceness and Darwin priority both still 0.
QOS_CLASS_UNSPECIFIED = 0x00
QOS_CLASS_DEFAULT = 0x15
#: The run's conditions, by the fixed name a refusal or a stop reports,
#: in the order they are checked (Output and stop rules, "One run").
RUN_CONDITIONS = (
    "ac_power",
    "sleep_assertions",
    "nice",
    "background",
    "qos",
    "load",
)
#: Before a program, a failed condition is rechecked every
#: ``RECHECK_SECONDS``, and the run stops when ``RECHECKS`` rechecks in a
#: row, 24 hours, have found one failing (Output and stop rules, "One
#: run").
RECHECK_SECONDS = 60
RECHECKS = 1440
#: kCFStringEncodingUTF8 and kIOPMAssertionLevelOn.
_UTF8 = 0x08000100
_ASSERTION_ON = 255


class _Host:
    """The macOS calls the run's conditions make: the providing power
    source, this process's sleep assertions and the calling thread's QoS
    class."""

    def __init__(self):
        pointer, uint32 = ctypes.c_void_p, ctypes.c_uint32
        try:
            self.iokit = ctypes.CDLL(IOKIT)
            self.cf = ctypes.CDLL(CORE_FOUNDATION)
            self.libc = ctypes.CDLL(None)
            for library, name, arguments, result in (
                (
                    self.cf,
                    "CFStringCreateWithCString",
                    [pointer, ctypes.c_char_p, uint32],
                    pointer,
                ),
                (
                    self.cf,
                    "CFStringGetCString",
                    [pointer, ctypes.c_char_p, ctypes.c_long, uint32],
                    ctypes.c_bool,
                ),
                (self.cf, "CFRelease", [pointer], None),
                (self.iokit, "IOPSCopyPowerSourcesInfo", [], pointer),
                (
                    self.iokit,
                    "IOPSGetProvidingPowerSourceType",
                    [pointer],
                    pointer,
                ),
                (
                    self.iokit,
                    "IOPMAssertionCreateWithName",
                    [pointer, uint32, pointer, ctypes.POINTER(uint32)],
                    ctypes.c_int,
                ),
                (
                    self.iokit,
                    "IOPMAssertionCopyProperties",
                    [uint32],
                    pointer,
                ),
                (self.iokit, "IOPMAssertionRelease", [uint32], ctypes.c_int),
                (self.libc, "pthread_self", [], pointer),
                (
                    self.libc,
                    "pthread_get_qos_class_np",
                    [
                        pointer,
                        ctypes.POINTER(ctypes.c_uint),
                        ctypes.POINTER(ctypes.c_int),
                    ],
                    ctypes.c_int,
                ),
            ):
                function = getattr(library, name)
                function.argtypes = arguments
                function.restype = result
        except (OSError, AttributeError):
            raise SystemExit(
                "B0.2 needs macOS IOKit for its run conditions"
            ) from None

    def power_source(self) -> str:
        """The providing power source's name, or "" when none is read."""
        snapshot = self.iokit.IOPSCopyPowerSourcesInfo()
        if not snapshot:
            return ""
        try:
            # The snapshot owns the name.
            source = self.iokit.IOPSGetProvidingPowerSourceType(snapshot)
            text = ctypes.create_string_buffer(64)
            if not source or not self.cf.CFStringGetCString(
                source, text, len(text), _UTF8
            ):
                return ""
            return text.value.decode()
        finally:
            self.cf.CFRelease(snapshot)

    def hold(self, kind: str) -> int:
        """Take a sleep assertion of ``kind`` on this process: its ID, or
        0 when IOKit refuses it."""
        strings = [
            self.cf.CFStringCreateWithCString(None, text.encode(), _UTF8)
            for text in (kind, "B0.2 structural counts")
        ]
        try:
            if not all(strings):
                return 0
            assertion = ctypes.c_uint32(0)
            status = self.iokit.IOPMAssertionCreateWithName(
                strings[0], _ASSERTION_ON, strings[1], ctypes.byref(assertion)
            )
            return assertion.value if status == 0 else 0
        finally:
            for string in strings:
                if string:
                    self.cf.CFRelease(string)

    def held(self, assertion: int) -> bool:
        """Whether this process still holds the assertion."""
        if not assertion:
            return False
        properties = self.iokit.IOPMAssertionCopyProperties(assertion)
        if not properties:
            return False
        self.cf.CFRelease(properties)
        return True

    def release(self, assertion: int) -> None:
        if assertion:
            self.iokit.IOPMAssertionRelease(assertion)

    def qos_class(self) -> int:
        """The calling thread's QoS class."""
        qos, relative = ctypes.c_uint(0), ctypes.c_int(0)
        self.libc.pthread_get_qos_class_np(
            self.libc.pthread_self(), ctypes.byref(qos), ctypes.byref(relative)
        )
        return qos.value


def _host_state(host: _Host) -> tuple[int, int, int, float, int]:
    """This process's niceness and Darwin priority, the calling thread's
    QoS class, the five-minute load average and the number of CPUs."""
    return (
        os.getpriority(os.PRIO_PROCESS, 0),
        os.getpriority(PRIO_DARWIN_PROCESS, 0),
        host.qos_class(),
        os.getloadavg()[1],
        os.cpu_count() or 1,
    )


class RunConditions:
    """The host conditions under which each program's limit, which is
    wall-clock time, measures that program alone: AC power; this
    process's sleep assertions; nice 0, no Darwin background policy and
    a QoS class of default or above; and a five-minute load below the
    CPU count.

    ``main()`` checks them before the attempt record, where a failure
    refuses the run, and the audit before every program, where a failure
    is waited out between programs. The sleep assertions are taken at
    construction, and a lapsed one is taken again before each check.
    Waiting delays a program and changes nothing it is given, so it
    cannot change an answer."""

    def __init__(self, host: _Host):
        self.host = host
        self.assertions = {kind: host.hold(kind) for kind in SLEEP_ASSERTIONS}

    def failing(self) -> str | None:
        """The fixed name of the first condition that does not hold, or
        None when all hold."""
        for kind, assertion in self.assertions.items():
            if not self.host.held(assertion):
                self.assertions[kind] = self.host.hold(kind)
        niceness, background, qos, load, cpus = _host_state(self.host)
        holds = {
            "ac_power": self.host.power_source() == AC_POWER,
            "sleep_assertions": all(
                self.host.held(assertion)
                for assertion in self.assertions.values()
            ),
            "nice": niceness == 0,
            "background": background == 0,
            "qos": qos == QOS_CLASS_UNSPECIFIED or qos >= QOS_CLASS_DEFAULT,
            "load": load < cpus,
        }
        return next((name for name in RUN_CONDITIONS if not holds[name]), None)

    def before_program(self) -> None:
        """Return once every condition holds. While one fails, recheck
        every ``RECHECK_SECONDS``; once ``RECHECKS`` rechecks in a row have
        found one failing, stop the run with the name of the one the last
        recheck found."""
        name = self.failing()
        rechecks = 0
        while name is not None:
            if rechecks == RECHECKS:
                raise SystemExit(
                    f"run condition {name} still failed after {RECHECKS}"
                    f" rechecks, {RECHECK_SECONDS} seconds apart, between"
                    " programs"
                )
            time.sleep(RECHECK_SECONDS)
            rechecks += 1
            name = self.failing()

    def release(self) -> None:
        for assertion in self.assertions.values():
            self.host.release(assertion)


def _check_runtime() -> None:
    if _git("status", "--porcelain"):
        raise SystemExit("B0.2 requires a clean protocol-freezing worktree")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        try:
            threads = int(os.environ.get(name, ""))
        except ValueError:
            threads = 0
        if not 1 <= threads <= 4:
            raise SystemExit(f"set {name} to an integer from 1 to 4")
    if os.environ.get("OMP_WAIT_POLICY") != "PASSIVE":
        raise SystemExit("set OMP_WAIT_POLICY=PASSIVE")
    _check_protocol()


def _start_conditions() -> RunConditions:
    """Take the sleep assertions and refuse to start unless every run
    condition holds: before the attempt record, so a refusal spends no
    version."""
    conditions = RunConditions(_Host())
    name = conditions.failing()
    if name is not None:
        conditions.release()
        raise SystemExit(f"B0.2 refuses to start: run condition {name} fails")
    return conditions


def write_new(path: Path, data: bytes) -> None:
    """Write ``data`` to a new file at ``path`` in one step.

    The bytes go to a temporary file in the same directory, which is
    flushed to disk and then hard-linked to ``path``; the link fails if
    ``path`` exists. A failure up to the link removes the temporary file
    and leaves nothing at ``path``. The directory is flushed after the
    link, so a failure there leaves the complete file. No partial file
    ever has a final name."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
    )
    try:
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def release_outputs(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    anchor: pd.DataFrame,
    design: pd.DataFrame,
    committed: Mapping,
    provenance: Mapping,
    before_program: Callable[[], None] | None = None,
) -> tuple[bytes, bytes]:
    """The local copy's bytes and the published file's.

    B0.1's record must pass the rerun gate (``check_b0_1_record``) before
    any of its sets enters the audit. ``provenance`` describes the run and
    its inputs and holds no count; each file adds to it only this
    release's counts (exact in the local copy, coarsened in the published
    file when released), the audit's decisions (``local_audit``) and the
    disclosure block."""
    counts = structural_counts(person_wave, validity_by_wave, anchor, design)
    domain_size = counts["rosters"]["R_B2"]["overall"]["persons"]
    if domain_size != committed["counts"]["domain_persons"]:
        raise AssertionError(
            "R_B2 size differs from B0.1 counts.domain_persons"
        )
    earlier = b0_1_sets(person_wave, validity_by_wave)
    check_b0_1_record(
        committed,
        b0_1_structural_counts(person_wave, validity_by_wave),
        earlier,
    )
    registry = disclosure_registry(
        person_wave, validity_by_wave, anchor, design
    )
    register_b0_1(registry, earlier, committed["counts"])
    coarsened, disclosure, audit = release_counts(
        counts, registry, before_program=before_program
    )
    payload = {**provenance, "counts": counts, "disclosure_audit": audit}
    public_payload = {**provenance, "disclosure": disclosure}
    if coarsened:
        public_payload["counts"] = coarsened
    return tuple(
        (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
        for record in (payload, public_payload)
    )


#: The run's phases. Reading and reducing the inputs builds no set, B0.1's
#: disposition sets included, and no atom; writing starts once both files'
#: bytes are fixed. A failure in either names its type and this script's
#: line. The release (the rebuild of B0.1's sets, the rerun gate, the
#: counts and the audit) is where dispositions and atom sizes enter, so a
#: failure there names the phase alone.
READING = "reading the inputs"
RELEASE = "the release"
WRITING = "writing the outputs"
LOCATED_PHASES = (READING, WRITING)


def _failure_text(error: BaseException, phase: str) -> str:
    """A failure's text with no value in it.

    The message is kept only when this script's own ``raise`` statement
    made it: those name paths, never values (a test checks every one), and
    which check fired is a gate decision. Any other message may quote a
    size, a value or an identifier, so it is dropped. Outside the release
    the text then names the error's type and the last line of this script
    that led to it; inside the release, or in a phase not listed, it names
    the phase alone, since where a failure strikes there can depend on
    dispositions."""
    frames = traceback.extract_tb(error.__traceback__)
    here = Path(__file__).resolve()
    own = [frame for frame in frames if Path(frame.filename).resolve() == here]
    raised_here = (
        frames
        and own
        and frames[-1] is own[-1]
        and (frames[-1].line or "").lstrip().startswith("raise ")
    )
    if raised_here:
        where = f"{own[-1].name}, line {own[-1].lineno}"
        return f"B0.2 stopped in {where}: {type(error).__name__}: {error}"
    if phase not in LOCATED_PHASES:
        return f"B0.2 stopped in {RELEASE}"
    where = f"{own[-1].name}, line {own[-1].lineno}" if own else "unknown"
    return f"B0.2 stopped in {where}: {type(error).__name__}"


def _flush_streams() -> None:
    """Flush Python's streams and the C library's, so that what they hold
    goes to the descriptors they point at now."""
    for stream in {
        id(stream): stream
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)
        if stream is not None
    }.values():
        stream.flush()
    ctypes.CDLL(None).fflush(None)


@contextmanager
def _silenced():
    """Point file descriptors 1 and 2, and Python's own streams, at the
    null device, so that nothing printed inside, by Python code or by a
    compiled library, reaches the terminal or a log. Every stream is
    flushed before the descriptors are restored, so nothing printed inside
    comes out after."""
    _flush_streams()
    saved = (os.dup(1), os.dup(2))
    null = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, 1)
        os.dup2(null, 2)
        with open(os.devnull, "w") as python_null:
            with redirect_stdout(python_null), redirect_stderr(python_null):
                yield
    finally:
        try:
            _flush_streams()
        finally:
            os.dup2(saved[0], 1)
            os.dup2(saved[1], 2)
            for descriptor in (null, *saved):
                os.close(descriptor)


@contextmanager
def count_free_failures(phase: str):
    """Run one phase of the steps that read data so that nothing they
    print or raise can show a value. Nothing printed inside is seen
    (``_silenced``), and a warning is dropped unseen: whether one fires,
    and where, can depend on the data. A failure stops the run with
    ``_failure_text``; that includes an interruption or a library's own
    exit, whose default report would print the chain of errors before it,
    and a failure to restore the descriptors. The report is printed after
    they are restored."""
    failure = None
    try:
        with _silenced(), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            yield
    except BaseException as error:
        failure = _failure_text(error, phase)
    if failure is not None:
        raise SystemExit(failure) from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--local-copy",
        type=Path,
        required=True,
        help="exclusive unsuppressed JSON in B0.2's evidence folder, outside the repository",
    )
    args = parser.parse_args(argv)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    local = args.local_copy
    local = local if local.is_absolute() else ROOT / local
    repository = ROOT.resolve()
    if Path(os.path.abspath(local)).is_relative_to(
        repository
    ) or local.resolve().is_relative_to(repository):
        raise SystemExit("local copy must be outside the repository")
    if out.resolve() == local.resolve():
        raise SystemExit(
            "published output and local copy must be separate files"
        )
    for destination in (out, local):
        if destination.exists() or destination.is_symlink():
            raise SystemExit(f"refusing to overwrite {destination}")
        if (
            RUNS_DIR.resolve() in destination.resolve().parents
            or "runs" in destination.resolve().parts
        ):
            raise SystemExit("B0.2 writes no file under runs/")
    if local.parent.resolve() != EVIDENCE_DIR.resolve():
        raise SystemExit("local copy must be in B0.2 evidence folder")
    attempt = _attempt_path(local)
    if attempt.exists() or attempt.is_symlink():
        raise SystemExit(
            f"B0.2 protocol version already has an attempt record: {attempt}"
        )
    _check_runtime()
    repository_head = _git("rev-parse", "HEAD")
    script_sha256 = _sha256_file(Path(__file__))
    conditions = _start_conditions()
    _start_attempt(local, repository_head, script_sha256)
    with count_free_failures(READING):
        data_dir = psid._resolve_data_dir(None).resolve()
        with psid2010.record_files_read(data_dir) as opened:
            person_wave, validity, anchor, design, allowlist = read_inputs(
                data_dir
            )
        _require_unit_identifiers(person_wave, anchor, design)
        committed = json.loads(B0_1_COUNTS.read_text(encoding="utf-8"))
        provenance = {
            "schema": SCHEMA,
            "repository_head": repository_head,
            "worktree_clean": True,
            "script_sha256": script_sha256,
            "psid_files_opened_sha256": dict(sorted(opened.items())),
            "b0_1_counts_sha256": _sha256_file(B0_1_COUNTS),
            "requested_label_allowlist": allowlist,
            "geometry": {
                "collection_waves": list(WAVES),
                "reference_years": [wave - 1 for wave in WAVES],
                "age_convention": "collection_wave",
                "lag_years": list(LAGS),
            },
        }
    with count_free_failures(RELEASE):
        local_bytes, public_bytes = release_outputs(
            person_wave,
            validity,
            anchor,
            design,
            committed,
            provenance,
            conditions.before_program,
        )
    with count_free_failures(WRITING):
        write_new(local, local_bytes)
        write_new(out, public_bytes)
    print(out)
    conditions.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
