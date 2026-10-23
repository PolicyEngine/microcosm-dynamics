#!/usr/bin/env python3
"""Track B B0.2: structural counts under protocol version 1.

Run once from the clean protocol-freezing commit. Family values are
immediately reduced by B0.1's validity_frame; all counting functions
accept frames and inspect only structural columns. Collection-wave ages
are used throughout; reference year is collection wave minus one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import warnings
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix

from populace_dynamics.cohorts import age67, psid2010
from populace_dynamics.data import family, panels, psid
from scripts.track_b_b0_1_counts import (
    _family_variables,
    _individual_variables,
    cluster_worst_n_eff,
    earnings_rows,
    kish_n_eff,
    validity_frame,
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
    "f2fd0a3eaf7cbfd99da21d7f885ca05e9e6b62764fe4db895b0f28b84ccd4bc6"
)
SCHEMA = "track_b_b0_2_counts.v1"
DISCLOSURE_THRESHOLD = 10
DISCLOSURE_BASES = (10, 50, 100, 500)
PROTECTION_WIDTH = 4
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
    """Every count's private unit set and effective-size count bound."""

    def __init__(self):
        self.sets: dict[CellPath, tuple[str, frozenset]] = {}
        self.effective_bounds: dict[CellPath, CellPath] = {}

    def add(self, path: CellPath, unit_type: str, units) -> None:
        if path in self.sets or path in self.effective_bounds:
            raise ValueError(f"duplicate registry path: {path}")
        self.sets[path] = (unit_type, frozenset(units))

    def effective(self, path: CellPath, count_path: CellPath) -> None:
        if path in self.sets or path in self.effective_bounds:
            raise ValueError(f"duplicate registry path: {path}")
        if count_path not in self.sets:
            raise ValueError("effective-size bound needs a registered count")
        self.effective_bounds[path] = count_path


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


def build_atom_models(registry: SetRegistry) -> dict[str, dict]:
    """Group identical sets, then identical unit memberships, using sparse A.

    Atoms partition the union of registered sets for each unit type. No
    unit identifiers or memberships are serialized. scipy's milp API has
    no initial-solution argument; the true sizes are retained and checked
    as a feasible witness before solving instead.
    """
    grouped = {}
    for path, (unit_type, units) in registry.sets.items():
        grouped.setdefault(unit_type, {}).setdefault(units, []).append(path)
    models = {}
    for unit_type, groups in grouped.items():
        sets = list(groups)
        paths = [groups[units][0] for units in sets]
        path_rows = {
            path: i for i, units in enumerate(sets) for path in groups[units]
        }
        memberships = {}
        for i, units in enumerate(sets):
            for unit in units:
                memberships.setdefault(unit, []).append(i)
        sizes = Counter(tuple(signature) for signature in memberships.values())
        signatures = sorted(sizes)
        row_indices = []
        col_indices = []
        for column, signature in enumerate(signatures):
            row_indices.extend(signature)
            col_indices.extend([column] * len(signature))
        matrix = csc_matrix(
            (np.ones(len(row_indices)), (row_indices, col_indices)),
            shape=(len(sets), len(signatures)),
        )
        targets = {}
        true_sizes = np.array([sizes[s] for s in signatures], dtype=int)
        for i, size in enumerate(true_sizes):
            if 1 <= size < DISCLOSURE_THRESHOLD:
                targets[(i,)] = {"kind": "atom"}
        # Identical objectives denote the same sensitive unit set and are
        # audited once, including differences that are themselves atoms.
        for i, superset in enumerate(sets):
            for j, subset in enumerate(sets):
                if not 1 <= len(superset) - len(subset) < DISCLOSURE_THRESHOLD:
                    continue
                if subset.issubset(superset):
                    objective = tuple(
                        k
                        for k, signature in enumerate(signatures)
                        if i in signature and j not in signature
                    )
                    targets.setdefault(
                        objective,
                        {
                            "kind": "difference",
                            "superset": list(paths[i]),
                            "subset": list(paths[j]),
                        },
                    )
        models[unit_type] = {
            "paths": paths,
            "path_rows": path_rows,
            "signatures": signatures,
            "sizes": true_sizes,
            "matrix": matrix,
            "targets": targets,
        }
    return models


def _audit_models(
    counts: dict, registry: SetRegistry, models: dict, base: int
) -> dict:
    quantities = []
    for unit_type, model in models.items():
        matrix = model["matrix"]
        lower, upper = np.array(
            [
                count_interval(coarsen(_cell(counts, path), base), base)
                for path in model["paths"]
            ],
            dtype=float,
        ).T
        for path, count_path in registry.effective_bounds.items():
            if registry.sets[count_path][0] != unit_type:
                continue
            effective = coarsen(_cell(counts, path), base)
            # An effective size never exceeds its count, so the count is
            # at least the smallest effective size that coarsens to the
            # published value: 1 under "<B", B for B itself.
            if effective == f"<{base}":
                bound = 1
            elif effective == 0:
                bound = 0
            else:
                bound = max(base, effective - base / 2)
            row = model["path_rows"][count_path]
            lower[row] = max(lower[row], bound)
        actual = matrix @ model["sizes"]
        if np.any(actual < lower) or np.any(actual > upper):
            raise ValueError(
                "true atom sizes violate the published constraints"
            )
        constraints = LinearConstraint(matrix, lower, upper)
        for atoms, detail in model["targets"].items():
            objective = np.zeros(matrix.shape[1])
            objective[list(atoms)] = 1
            extrema = []
            statuses = []
            for sign in (1, -1):
                # HiGHS receives threads verbatim. Both its internal
                # threads and the required BLAS environment stay at one.
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="Unrecognized options detected.*",
                        category=RuntimeWarning,
                    )
                    result = milp(
                        sign * objective,
                        integrality=np.ones(matrix.shape[1]),
                        bounds=Bounds(0, np.inf),
                        constraints=constraints,
                        options={
                            "time_limit": 60.0,
                            "mip_rel_gap": 0.0,
                            "threads": 1,
                        },
                    )
                optimal = result.status == 0 and result.success
                statuses.append(int(result.status))
                extrema.append(float(sign * result.fun) if optimal else None)
            minimum, maximum = extrema
            protected = (
                minimum is not None
                and maximum is not None
                and maximum - minimum >= PROTECTION_WIDTH
            )
            quantities.append(
                {
                    "unit_type": unit_type,
                    "atoms": list(atoms),
                    **detail,
                    "true_size": int(model["sizes"][list(atoms)].sum()),
                    "minimum": minimum,
                    "maximum": maximum,
                    "solver_status": statuses,
                    "protected": protected,
                }
            )
    return {
        "base": base,
        "quantities": quantities,
        "audited": len(quantities),
        "failed": sum(not quantity["protected"] for quantity in quantities),
        "atom_sizes": {
            kind: model["sizes"].tolist() for kind, model in models.items()
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


def audit_counts(counts: dict, registry: SetRegistry, base: int) -> dict:
    """Run both integer optimizations for every sensitive quantity at B."""
    _validate_registry(counts, registry)
    return _audit_models(counts, registry, build_atom_models(registry), base)


def release_counts(
    counts: dict, registry: SetRegistry
) -> tuple[dict, dict, dict]:
    """Use the first passing base; public metadata never names a quantity."""
    _validate_registry(counts, registry)
    models = build_atom_models(registry)
    audits = []
    published = {}
    selected = None
    for base in DISCLOSURE_BASES:
        audit = _audit_models(counts, registry, models, base)
        audits.append(audit)
        if audit["failed"] == 0:
            selected = base
            published = deepcopy(counts)
            for path, value in _leaves(counts):
                _put(published, path, coarsen(value, base))
            break
    disclosure = {
        "base": selected,
        "coarsening_rule": "0 stays 0; 1 to B-1 is <B; otherwise nearest multiple of B, halves up; applies also to effective sizes",
        "protection_rule": "integer maximum minus minimum >= 4; both proven optimal within 60 seconds per program",
        "attempts": [
            {key: audit[key] for key in ("base", "audited", "failed")}
            for audit in audits
        ],
    }
    return published, disclosure, {"audits": audits}


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
    _start_attempt(local, repository_head, script_sha256)
    data_dir = psid._resolve_data_dir(None).resolve()
    with psid2010.record_files_read(data_dir) as opened:
        person_wave, validity, anchor, design, allowlist = read_inputs(
            data_dir
        )
    counts = structural_counts(person_wave, validity, anchor, design)
    committed = json.loads(B0_1_COUNTS.read_text(encoding="utf-8"))
    domain_size = counts["rosters"]["R_B2"]["overall"]["persons"]
    if domain_size != committed["counts"]["domain_persons"]:
        raise AssertionError(
            "R_B2 size differs from B0.1 counts.domain_persons"
        )
    payload = {
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
        "counts": counts,
    }
    registry = disclosure_registry(person_wave, validity, anchor, design)
    coarsened, disclosure, local_audit = release_counts(counts, registry)
    payload["disclosure_audit"] = local_audit
    public_payload = {"disclosure": disclosure}
    if coarsened:
        public_payload = {
            **{
                key: value
                for key, value in payload.items()
                if key != "disclosure_audit"
            },
            "counts": coarsened,
            "disclosure": disclosure,
        }
    # Reserve both paths exclusively before writing either payload. If the
    # second reservation fails, remove only the first file we just created.
    with out.open("x", encoding="utf-8") as stream:
        try:
            local_stream = local.open("x", encoding="utf-8")
        except OSError:
            out.unlink()
            raise
        with local_stream:
            local_stream.write(
                json.dumps(payload, indent=2, sort_keys=True) + "\n"
            )
            stream.write(
                json.dumps(public_payload, indent=2, sort_keys=True) + "\n"
            )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
