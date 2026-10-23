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
from collections.abc import Mapping
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

import pandas as pd

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
SCHEMA = "track_b_b0_2_counts.v1"
DISCLOSURE_THRESHOLD = 10
SUPPRESSED = "<10"
CellPath = tuple[str, ...]
Relation = tuple[CellPath, tuple[CellPath, ...]] | Mapping[CellPath, int]
WAVES = tuple(range(1999, 2024, 2))
LAGS = (2, 4)
ANCHOR_WAVE = 2011
B3L_ORIGIN_WAVE = 2007
OLDER_BANDS = (("62_64", 62, 64), ("65_66", 65, 66), ("67_69", 67, 69))
CONTEXT_BANDS = (("25_44", 25, 44), ("45_61", 45, 61))
ROSTER_BANDS = (
    ("0_24", 0, 24),
    *CONTEXT_BANDS,
    *OLDER_BANDS,
    ("70_79", 70, 79),
    ("80_plus", 80, float("inf")),
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
        "kish_n_eff": round(kish_n_eff(weights), 3),
        "household_cluster_worst_n_eff": round(
            cluster_worst_n_eff(weights, positive["interview"].to_numpy()),
            3,
        ),
        "design_cluster_worst_n_eff": round(
            cluster_worst_n_eff(weights, design_clusters), 3
        ),
    }


def _roster_summary(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "overall": _summary(frame),
        "by_age_band": {
            name: _summary(frame[frame["age"].between(low, high)])
            for name, low, high in ROSTER_BANDS
        },
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
    proxy = proxy[proxy["age"] >= 30]
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
                (rows["period"] == wave) & rows["age"].between(low, high)
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
                        both["age"].between(low, high), "person_id"
                    ].nunique()
                )
                for name, low, high in OLDER_BANDS
            }
        pairs[str(lag)] = by_pair
    return {
        "by_wave": by_wave,
        "distinct_persons_by_band": {
            name: int(
                rows.loc[rows["age"].between(low, high), "person_id"].nunique()
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
                & later_rows["age"].between(low, high)
            ]
            support[str(wave)][name] = {
                "persons": int(cell["person_id"].nunique()),
                "kish_n_eff": round(
                    kish_n_eff(cell["weight"].to_numpy(dtype=float)), 3
                ),
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
# Disclosure, applied only after all raw counts have been computed
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


def _subtract(row: dict, other: dict, scale: Fraction) -> None:
    for key, value in other.items():
        result = row.get(key, 0) - scale * value
        if result:
            row[key] = result
        else:
            row.pop(key, None)


def _equation(relation: Relation) -> dict[CellPath, Fraction]:
    if isinstance(relation, Mapping):
        return {path: Fraction(c) for path, c in relation.items() if c}
    total, parts = relation
    result = {total: Fraction(1)}
    for part in parts:
        result[part] = result.get(part, 0) - 1
    return {path: c for path, c in result.items() if c}


def _recoverable(equations: list[dict], hidden: set) -> dict[CellPath, dict]:
    """Find hidden cells determined even by combinations of equations.

    Exact rational elimination avoids both floating-point rank decisions
    and the assumption that two hidden cells in every equation suffice.
    """
    basis = {}
    for equation in equations:
        row = {path: c for path, c in equation.items() if path in hidden}
        witness = equation.copy()
        while row:
            pivot = min(row)
            if pivot not in basis:
                scale = row[pivot]
                basis[pivot] = (
                    {key: c / scale for key, c in row.items()},
                    {key: c / scale for key, c in witness.items()},
                )
                break
            other_row, other_witness = basis[pivot]
            scale = row[pivot]
            _subtract(row, other_row, scale)
            _subtract(witness, other_witness, scale)
    for pivot in sorted(basis, reverse=True):
        row, witness = basis[pivot]
        for key in sorted(set(row) - {pivot}):
            if key in basis and key in row:
                other_row, other_witness = basis[key]
                scale = row[key]
                _subtract(row, other_row, scale)
                _subtract(witness, other_witness, scale)
    return {
        pivot: witness
        for pivot, (row, witness) in basis.items()
        if len(row) == 1
    }


def suppress_counts(
    counts: dict[str, Any], relations: tuple[Relation, ...] = ()
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return publishable counts and an audit of each suppression pass.

    Relations are exact total/parts identities or signed count equations.
    They stay private: neither unit sets nor residual counts are emitted.
    Effective sizes below ten are conservatively suppressed even when
    their supporting set is larger. Empty-set zeros remain zero.
    """
    published = deepcopy(counts)
    values = dict(_leaves(counts))
    hidden = set()

    def suppress(path):
        hidden.add(path)
        _put(published, path, SUPPRESSED)

    for path, value in values.items():
        parent = _cell(counts, path[:-1])
        support = parent.get("valid_rows", parent.get("persons", 0))
        small_support = (
            path[-1].endswith("_n_eff") and 0 < support < DISCLOSURE_THRESHOLD
        )
        if 0 < value < DISCLOSURE_THRESHOLD or small_support:
            suppress(path)
    primary = len(hidden)
    equations = [_equation(relation) for relation in relations]

    def smallest(equation):
        available = [
            path
            for path in equation
            if path not in hidden and values[path] > 0
        ]
        parts = [path for path in available if equation[path] < 0]
        candidates = parts or available
        return min(
            candidates, key=lambda path: (values[path], path), default=None
        )

    passes = []
    while True:
        extra = set()
        for equation in equations:
            if len(hidden.intersection(equation)) == 1:
                candidate = smallest(equation)
                if candidate is not None:
                    extra.add(candidate)
        # Coupled tables can disclose a cell without any single equation
        # having just one hidden term. Close those paths as well.
        if not extra:
            proposals = []
            for witness in _recoverable(equations, hidden).values():
                candidate = smallest(witness)
                if candidate is not None:
                    proposals.append(candidate)
            if proposals:
                # One complement can close several recovery equations;
                # recompute before choosing another cell.
                extra.add(
                    min(proposals, key=lambda path: (values[path], path))
                )
        # A complementary person-count suppression must not be undone by
        # a published Kish size (equal to n for constant weights).
        for path in values:
            if path not in hidden and path[-1].endswith("_n_eff"):
                parent = _cell(published, path[:-1])
                if parent.get("persons") == SUPPRESSED:
                    extra.add(path)
        if not extra:
            break
        for path in extra:
            suppress(path)
        passes.append(len(extra))
    return published, {
        "threshold": DISCLOSURE_THRESHOLD,
        "rule": (
            "1-9 and statistics on nonempty sets below 10: <10; empty "
            "zeros retained; positive effective sizes below 10 also hidden. "
            "Complementary: hide the smallest remaining positive part, "
            "or its total if no positive part remains; repeat to a fixed "
            "point, including aliases and coupled subtraction identities."
        ),
        "primary_suppressed": primary,
        "complementary_suppressed": sum(passes),
        "complementary_passes": passes,
    }


def _incidence_relations(cells: dict[CellPath, frozenset]) -> list[dict]:
    """All exact additive identities among these private unit sets.

    Units with identical cell membership share one incidence column.
    Reducing its rows yields a basis of every cardinality identity,
    including disjoint partitions, aliases and inclusion/exclusion when
    intersections are present. Overlapping unions are never just summed.
    Only coefficients on existing output cells leave this function.
    """
    memberships = {}
    paths = list(cells)
    for index, units in enumerate(cells.values()):
        for unit in units:
            memberships.setdefault(unit, []).append(index)
    columns = sorted({tuple(indices) for indices in memberships.values()})
    vectors = {path: {} for path in paths}
    for column in columns:
        for index in column:
            vectors[paths[index]][column] = Fraction(1)
    basis = {}
    relations = []
    for path, row in vectors.items():
        if not row:  # zero counts are public; no useful suppression alias
            continue
        terms = {path: Fraction(1)}
        while row:
            pivot = min(row)
            if pivot not in basis:
                scale = row[pivot]
                basis[pivot] = (
                    {key: c / scale for key, c in row.items()},
                    {key: c / scale for key, c in terms.items()},
                )
                break
            other_row, other_terms = basis[pivot]
            scale = row[pivot]
            _subtract(row, other_row, scale)
            _subtract(terms, other_terms, scale)
        if not row and terms:
            relations.append(terms)
    return relations


def disclosure_relations(
    person_wave: pd.DataFrame,
    validity_by_wave: Mapping[int, pd.DataFrame],
    anchor: pd.DataFrame,
    design: pd.DataFrame,
) -> tuple[Relation, ...]:
    """Explicitly register every output table and its unit-set relations.

    Person IDs link waves, rosters, lag intersections and pooled unions.
    Household IDs are wave-specific; design clusters include stratum.
    No earnings value, new statistic or unreported remainder is computed.
    """
    cells = {}
    partitions = []

    def register(prefix, frame, wave):
        def clean(value):
            return None if pd.isna(value) else value

        units = {
            "persons": frozenset(
                ("person", value) for value in frame["person_id"].dropna()
            ),
            "households": frozenset(
                ("household", wave, value)
                for value in frame["interview"].dropna()
            ),
            "design_strata": frozenset(
                ("stratum", value) for value in frame["stratum"].dropna()
            ),
            "design_clusters": frozenset(
                ("cluster", clean(stratum), clean(cluster))
                for stratum, cluster in frame[["stratum", "cluster"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            ),
        }
        for metric, members in units.items():
            cells[(*prefix, metric)] = members

    def partition(total, parts):
        # A union is additive only with exhaustive, disjoint parts.
        members = set()
        for part in parts:
            if members.intersection(cells[part]):
                return
            members.update(cells[part])
        if members == cells[total]:
            partitions.append((total, tuple(parts)))

    def roster(prefix, frame, wave):
        register((*prefix, "overall"), frame, wave)
        for name, low, high in ROSTER_BANDS:
            register(
                (*prefix, "by_age_band", name),
                frame[frame["age"].between(low, high)],
                wave,
            )
        for metric in (
            "persons",
            "households",
            "design_strata",
            "design_clusters",
        ):
            partition(
                (*prefix, "overall", metric),
                [
                    (*prefix, "by_age_band", name, metric)
                    for name, _, _ in ROSTER_BANDS
                ],
            )

    full = _with_design(_full(person_wave, ANCHOR_WAVE), design)
    domain = _with_design(_b2_roster(person_wave, validity_by_wave), design)
    proxy = _present(
        anchor[[column for column in PERSON_COLUMNS if column != "period"]]
    )
    proxy = _with_design(proxy[proxy["age"] >= 30], design)
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
                (rows["period"] == wave) & rows["age"].between(low, high)
            ]
            prefix = ("b3", "by_wave", str(wave), name)
            register(prefix, frame, wave)
            cells[(*prefix, "valid_rows")] = cells[(*prefix, "persons")]
            cells[(*prefix, "accuracy_positive_rows")] = frozenset(
                ("person", value)
                for value in frame.loc[frame["acc_flag"], "person_id"]
            )
    for name, low, high in OLDER_BANDS:
        total = ("b3", "distinct_persons_by_band", name)
        cells[total] = frozenset(
            ("person", value)
            for value in rows.loc[rows["age"].between(low, high), "person_id"]
        )
        partition(
            total,
            [("b3", "by_wave", str(wave), name, "persons") for wave in WAVES],
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
                cells[
                    ("b3", "lag_pairs", str(lag), f"{wave}_{later}", name)
                ] = frozenset(
                    ("person", value)
                    for value in both.loc[
                        both["age"].between(low, high), "person_id"
                    ]
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
                & rows["age"].between(low, high)
            ]
            cells[("b3l", "later_support", str(wave), name, "persons")] = (
                frozenset(("person", value) for value in frame["person_id"])
            )
    outside = full[~full["interview"].isin(domain["interview"])]
    roster(("outside_b2",), outside, ANCHOR_WAVE)
    for wave in (2013, 2015):
        frame = person_wave[
            (person_wave["period"] == wave)
            & person_wave["sequence"].between(1, 20)
            & person_wave["person_id"].isin(domain["person_id"])
        ]
        cells[("outside_b2", "b2_households_by_wave", str(wave))] = frozenset(
            ("household", wave, value) for value in frame["interview"].dropna()
        )
    partition(
        ("rosters", "R_FULL", "overall", "households"),
        [
            ("rosters", "R_B2", "overall", "households"),
            ("outside_b2", "overall", "households"),
        ],
    )
    return tuple([*partitions, *_incidence_relations(cells)])


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
    _check_runtime()
    repository_head = _git("rev-parse", "HEAD")
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
        "script_sha256": _sha256_file(Path(__file__)),
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
    relations = disclosure_relations(person_wave, validity, anchor, design)
    suppressed, disclosure = suppress_counts(counts, relations)
    public_payload = {
        **payload,
        "counts": suppressed,
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
