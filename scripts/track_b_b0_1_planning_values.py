#!/usr/bin/env python3
"""Track B B0.1 addendum: pseudo-origin planning values (protocol v2).

This script implements the planning-value protocol that
``docs/design/track_b_b0_1_addendum.md`` froze (its ``protocol-v2`` block)
before any computation. Max's ruling d693 adopted B0.1's Q5 option (a): B2's
planning values come from B2's own estimation window, reference years 2010
and earlier. There are two variance-only values per cell, from one
pseudo-origin household bootstrap:

- the shared-anchor ratio r: the gap's true full-support standard error
  over the audit's upper bound ``sigma * sqrt(1 + 1/K) / 2``;
- the estimation variance: what re-estimating the forward law adds to the
  gap's variance.

The pseudo-origin is 2006: candidate 3's law is fitted on rows dated 2006
and earlier and projected to 2008 and 2010, B2's geometry moved back four
years. Every row it reads is dated 2010 or earlier. It opens no family file
for collection wave 2013 or later, reads the cross-year individual file only
for collection waves 2011 and earlier, and reads NAWI only through 2006. It
computes nothing on reference years 2012 or 2014.

It records only variance-type quantities, floor dispersion summaries,
counts, hashes and provenance. No truth moment, projected moment, cell level,
gap, mean gap or per-replicate value is written to the record or printed.
Replicate checkpoints hold per-replicate gaps (never a truth or projected
value). They live outside the repository, are bound to the freeze commit
and protocol hash, and are deleted when the run completes or fails; only an
infrastructure interruption keeps them, for a logged resume.

Run once, from a clean worktree at the protocol-freeze commit, in the pinned
runtime (see ``RUNTIME``), for example::

    PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS='ignore::FutureWarning' \\
      PYTHONPATH=src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \\
      VECLIB_MAXIMUM_THREADS=1 POPULACE_FIT_N_JOBS=4 \\
      POPULACE_DYNAMICS_PSID_DIR=/Users/maxghenis/PolicyEngine/psid-data \\
      POPULACE_DYNAMICS_PE_US_DIR=/path/to/site-packages \\
      /path/to/runtime/bin/python scripts/track_b_b0_1_planning_values.py \\
      --freeze-commit <sha> --workers-f 8 --workers-r 4 \\
      --checkpoint-dir /private/scratch/b01-planning
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import dataclasses
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import select_m6_qstar_train_only as selector  # noqa: E402

from populace_dynamics.cohorts.age67 import (  # noqa: E402
    read_design_variables,
)
from populace_dynamics.cohorts.psid2010 import record_files_read  # noqa: E402
from populace_dynamics.data import family, panels  # noqa: E402
from populace_dynamics.engine import forward_earnings as fe  # noqa: E402
from populace_dynamics.engine.candidates import CANDIDATE_3  # noqa: E402
from populace_dynamics.engine.earnings_domain import (  # noqa: E402
    EARNINGS_DOMAIN_COLUMN,
    earnings_domain_person_ids,
)
from populace_dynamics.engine.refit import (  # noqa: E402
    refit_earnings_chained_generator,
    truncate_estimation_frame,
)
from populace_dynamics.harness.m6_cells import (  # noqa: E402
    FLOOR_SEEDS,
    GATEABLE_METRICS,
    earnings_cells,
    run_floor,
)
from populace_dynamics.harness.m6_cells import (
    MIN_EVENTS_FOR_GATE as MIN_EVENTS,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b0_1_planning_values.v1"
PROTOCOL = "track_b_b0_1_addendum protocol-v2"
OUTPUT = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
ADDENDUM = ROOT / "docs" / "design" / "track_b_b0_1_addendum.md"
PROTOCOL_BEGIN, PROTOCOL_END = (
    "<!-- protocol-v2:begin -->",
    "<!-- protocol-v2:end -->",
)
#: SHA-256 of the protocol-v2 block at the freeze commit (markers included).
PROTOCOL_V2_SHA256 = (
    "2a1681cdb3b6e28f30a8c1a319895b95f25c2fb27a175c50ded8a196d8488fe9"
)
COUNTS = ROOT / "docs" / "design" / "track_b_b0_1_counts.json"

# --------------------------------------------------------------------------
# Geometry (protocol v2, "Definitions")
# --------------------------------------------------------------------------
PSEUDO_ORIGIN = 2006
ANCHOR_WAVE = PSEUDO_ORIGIN + 1
LEVEL_YEARS = (PSEUDO_ORIGIN + 2, PSEUDO_ORIGIN + 4)
CHANGE_YEARS = (PSEUDO_ORIGIN, PSEUDO_ORIGIN + 2, PSEUDO_ORIGIN + 4)
SCORED_PERIODS = CHANGE_YEARS
#: The latest reference year any row may carry, and its collection wave.
MAX_REFERENCE_YEAR = 2010
MAX_COLLECTION_WAVE = MAX_REFERENCE_YEAR + 1
COLLECTION_WAVES = tuple(
    wave
    for wave in family.FAMILY_WAVES
    if 1969 <= wave and wave - 1 <= MAX_REFERENCE_YEAR
)
#: B2's own anchor wave, read only for the source-reproduction counts.
B2_ANCHOR_WAVE = 2011
B2_BOUNDARY = 2010

# --------------------------------------------------------------------------
# Law, seeds and replicate counts (protocol v2, "Computations")
# --------------------------------------------------------------------------
FIT_SEED = selector.FIT_SEED
DRAW_SEEDS = selector.SELECTION_DRAW_SEEDS
K = len(DRAW_SEEDS)
B_F = 4000
B_D = 1000
#: Arm R runs replicates 0..B_R_MAX-1 in index order and keeps the longest
#: completed prefix once ARM_R_BUDGET_SECONDS have passed since arm R first
#: started (across resumes); fewer than B_R_MIN replicates void the run.
B_R_MAX = 200
B_R_MIN = 60
ARM_R_BUDGET_SECONDS = 36 * 3600
#: How arm R resamples households before refitting: "copies" (with
#: replacement, the bootstrap) or "half" (without replacement).
REFIT_SCHEME = "half"
#: Root of every resampling stream, with SeedSequence words
#: [ROOT, b, 0] arm F and arm R full-anchor households (multinomial);
#: [ROOT, b, 1] arm R other clusters (multinomial);
#: [ROOT, b, 2] and [ROOT, b, 3] the same two strata under "half";
#: [ROOT, b, 4] arm D design clusters; [ROOT, 2**20] the limits.
BOOTSTRAP_ROOT_SEED = 20260930
N_CI_RESAMPLES = 2000
CI_BATCH = 250
CI_LEVELS = (0.05, 0.95)
#: Upper limits use this percentile (see ``summarize_cell``).
UCL_LEVEL = 0.975
#: A cell needs this share of arm F's replicates defined, and every arm R
#: replicate, to have planning values.
MIN_DEFINED_SHARE_F = 0.99
#: Household resampling stands if every cell's design-ratio upper limit is
#: at most this.
DESIGN_RATIO_LIMIT = 1.10
#: Copies of one person are numbered 0..ID_SCALE-1 under new identifiers
#: person_id * ID_SCALE + copy.
ID_SCALE = 1000
#: An arm whose in-replicate failures exceed this share of its used
#: replicates is void, and the run's planning values are undefined.
MAX_FAILED_SHARE = 0.10
#: The paired arms' truth statistics must agree to this relative tolerance.
TRUTH_AGREEMENT_RTOL = 1e-9

#: B2's recorded 2010-boundary counts (frozen record, protocol-v1 run).
B2_EXPECTED = {
    "fit_input_rows": 321_500,
    "n_full_anchor": 23_134,
    "n_domain": 13_542,
}

RUNTIME = {
    "python": "3.14.4",
    "numpy": "2.5.1",
    "pandas": "3.0.3",
    "scikit_learn": "1.8.0",
    "scipy": "1.18.0",
    "quantile_forest": "1.4.2",
    "populace_fit": "0.1.0",
    "populace_frame": "0.1.0",
}
#: Thread settings the run must fix; a resume must repeat them.
THREAD_ENV = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "POPULACE_FIT_N_JOBS",
)
POLICYENGINE_US_VERSION = "1.752.2"
NAWI_RELATIVE = Path("policyengine_us/parameters/gov/ssa/nawi.yaml")

#: Keys that must never appear anywhere in the written record.
FORBIDDEN_RECORD_KEYS = frozenset(
    {
        "truths",
        "tdev",
        "delta",
        "gap_refit",
        "gap_fixed",
        "n_obs",
        "n_events",
        "n_events_a",
        "n_events_b",
        "min_events_weaker_half",
        "realized_sigma",
        "sigma",
        "se_up",
        "value",
        "values",
        "truth",
        "truth_moments",
        "truth_value",
        "projected",
        "projected_moments",
        "projected_value",
        "gap",
        "gaps",
        "mean_gap",
        "gap_mean",
        "per_replicate",
        "moments",
        "level",
        "levels",
    }
)


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _canonical_sha256(value: Any) -> str:
    return selector._canonical_sha256(value)


# --------------------------------------------------------------------------
# Cells and gaps
# --------------------------------------------------------------------------
def gateable_cells() -> dict[str, str]:
    """The 16 gateable earnings cells and their metrics, read from the
    reducer's own metadata."""
    probe = earnings_cells(
        _schema_frame(),
        level_years=LEVEL_YEARS,
        change_years=CHANGE_YEARS,
    )
    return {
        name: str(record["metric"])
        for name, record in sorted(probe.items())
        if record.get("metric") in GATEABLE_METRICS
    }


def _schema_frame() -> pd.DataFrame:
    """A tiny invented frame, used only to read the reducer's cell names."""
    rows = []
    for person, cohort, age in ((1, "prime", 30), (2, "older", 50)):
        for index, period in enumerate(CHANGE_YEARS):
            rows.append(
                {
                    "person_id": person,
                    "period": period,
                    "earnings": 100.0 + 10 * index + person,
                    "age": age + 2 * index,
                    "weight": 1.0,
                    "cohort": cohort,
                }
            )
    return pd.DataFrame(rows)


CELL_METRICS = gateable_cells()
CELLS = tuple(CELL_METRICS)


def cell_values(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Each gateable cell's value and metric; value None when undefined."""
    reduced = earnings_cells(
        frame,
        level_years=LEVEL_YEARS,
        change_years=CHANGE_YEARS,
    )
    out: dict[str, dict[str, Any]] = {}
    for name in CELLS:
        record = reduced[name]
        out[name] = {
            "metric": str(record["metric"]),
            "value": selector._selection_cell_value(record),
        }
    return out


def signed_gap(
    metric: str, draw_values: Sequence[float | None], truth: float | None
) -> float | None:
    """M6's score before the absolute value; None when M6 leaves it undefined.

    The projected statistic is the mean of the draws' values
    (``select_m6_qstar_train_only._aggregate_boundary``). Log-ratio cells
    take ln(projected / truth); the others take projected - truth.
    """
    if truth is None or any(value is None for value in draw_values):
        return None
    if not draw_values:
        return None
    projected = float(np.mean(np.asarray(draw_values, dtype=np.float64)))
    if not math.isfinite(projected) or not math.isfinite(truth):
        return None
    if metric == "log_ratio":
        if projected <= 0 or truth <= 0:
            return None
        return math.log(projected / truth)
    return projected - truth


def replicate_gaps(
    truth: pd.DataFrame, draws: Sequence[pd.DataFrame]
) -> tuple[dict[str, float | None], dict[str, float | None]]:
    """Per-cell signed gaps and truth values for one replicate frame set.

    The truth values are returned only for the paired arms' in-memory
    agreement check; they are never written.
    """
    truth_cells = cell_values(truth)
    draw_cells = [cell_values(frame) for frame in draws]
    gaps: dict[str, float | None] = {}
    truths: dict[str, float | None] = {}
    for name in CELLS:
        metric = truth_cells[name]["metric"]
        truths[name] = truth_cells[name]["value"]
        gaps[name] = signed_gap(
            metric,
            [cells[name]["value"] for cells in draw_cells],
            truth_cells[name]["value"],
        )
    return gaps, truths


# --------------------------------------------------------------------------
# Sources (protocol v2, "Inputs")
# --------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Sources:
    """Field-capped sources. Every row is dated 2010 or earlier."""

    person_wave: pd.DataFrame
    earnings: pd.DataFrame


def build_sources(
    person_wave: pd.DataFrame,
    labor_by_wave: Mapping[int, pd.DataFrame],
    relationship_codes: Callable[[int], tuple[tuple[int, ...], ...]],
) -> Sources:
    """Build the selectors' earnings rows from already-read fields.

    This mirrors ``select_m6_qstar_train_only._load_field_capped_psid`` with
    the cap moved from reference year 2014 to 2010.
    """
    waves = sorted(int(wave) for wave in labor_by_wave)
    if not waves or max(waves) > MAX_COLLECTION_WAVE:
        raise AssertionError("a collection wave after 2011 was supplied")
    if int(person_wave["period"].max()) > MAX_COLLECTION_WAVE:
        raise AssertionError("individual-file rows after 2011 were supplied")
    present = person_wave["sequence"].between(1, 20)
    person_wave = person_wave.loc[present].reset_index(drop=True)
    frames: list[pd.DataFrame] = []
    for wave in waves:
        labor = labor_by_wave[wave]
        wave_people = person_wave.loc[person_wave["period"] == wave]
        merged = wave_people.merge(labor, on="interview", how="inner")
        head_codes, spouse_codes = relationship_codes(wave)
        is_head = merged["relationship"].isin(head_codes)
        is_spouse = merged["relationship"].isin(spouse_codes)
        merged = merged.loc[is_head | is_spouse].copy()
        head_mask = merged["relationship"].isin(head_codes)
        merged["earnings"] = (
            merged["head_labor"]
            .where(head_mask, merged["spouse_labor"])
            .astype("float64")
        )
        merged["period"] = wave - 1
        frames.append(
            merged[["person_id", "period", "earnings", "age", "weight"]]
        )
    earnings = pd.concat(frames, ignore_index=True)
    keep = (earnings["earnings"] < family._MISSING) & (earnings["weight"] > 0)
    earnings = (
        earnings.loc[keep]
        .sort_values(["person_id", "period"], kind="stable")
        .reset_index(drop=True)
    )
    if earnings.duplicated(["person_id", "period"]).any():
        raise ValueError("earnings rows repeat a person-period")
    if int(earnings["period"].max()) > MAX_REFERENCE_YEAR:
        raise AssertionError("an earnings row is dated after 2010")
    return Sources(person_wave=person_wave, earnings=earnings)


def load_sources(psid_dir: Path) -> Sources:
    """Read the field-capped PSID sources (waves 1969-2011 only)."""
    if max(COLLECTION_WAVES) != MAX_COLLECTION_WAVE:
        raise AssertionError("the collection-wave cap is not 2011")
    concepts = {
        name: panels.DEMOGRAPHIC_CONCEPTS[name]
        for name in ("age", "sequence", "relationship", "weight", "interview")
    }
    person_wave = panels.ind_person_period(
        concepts, data_dir=psid_dir, waves=list(COLLECTION_WAVES)
    )
    labor = {
        wave: selector._read_family_labor_levels(wave, data_dir=psid_dir)
        for wave in COLLECTION_WAVES
    }
    return build_sources(person_wave, labor, family._relationship_codes)


_GUARD: dict[str, Any] = {"roots": None, "installed": False}


def psid_path_allowed(relative: Path) -> bool:
    """Protocol v2's PSID read set: the individual file and family waves
    1969-2011, nothing else."""
    parts = Path(relative).parts
    if parts in (
        ("ind2023er", "IND2023ER.txt"),
        ("ind2023er", "IND2023ER.sps"),
    ):
        return True
    return (
        len(parts) == 3
        and parts[0] == "family"
        and parts[1].isdigit()
        and 1969 <= int(parts[1]) <= MAX_COLLECTION_WAVE
    )


def _guard_hook(event: str, args: tuple) -> None:
    if event != "open":
        return
    roots = _GUARD["roots"]
    if roots is None or not args or isinstance(args[0], int):
        return
    literal = Path(os.path.abspath(os.fsdecode(os.fspath(args[0]))))
    for candidate in (literal, literal.resolve()):
        for root in roots:
            if candidate.is_relative_to(root):
                relative = candidate.relative_to(root)
                if not psid_path_allowed(relative):
                    raise PermissionError(
                        f"protocol v2 forbids reading {relative}"
                    )
                return


@contextmanager
def psid_read_guard(psid_dir: Path) -> Iterator[None]:
    """Refuse, before it happens, any PSID open outside the read set."""
    if not _GUARD["installed"]:
        sys.addaudithook(_guard_hook)
        _GUARD["installed"] = True
    literal = Path(os.path.abspath(psid_dir))
    _GUARD["roots"] = (literal, literal.resolve())
    try:
        yield
    finally:
        _GUARD["roots"] = None


def anchor_frame(person_wave: pd.DataFrame, wave: int) -> pd.DataFrame:
    """Full anchor at ``wave``: present, positive weight; fixed weight and
    household identifier from that wave."""
    rows = person_wave.loc[
        (person_wave["period"] == wave)
        & person_wave["sequence"].between(1, 20)
        & (pd.to_numeric(person_wave["weight"], errors="coerce") > 0),
        ["person_id", "interview", "weight"],
    ]
    anchor = rows.rename(columns={"interview": "household_id"})
    anchor = anchor.sort_values("person_id", kind="stable").reset_index(
        drop=True
    )
    if anchor.empty or anchor["person_id"].duplicated().any():
        raise ValueError(f"the {wave} full anchor is empty or duplicated")
    return anchor


def source_checks(sources: Sources) -> dict[str, Any]:
    """Reproduce B2's recorded 2010-boundary counts from these sources.

    These are counts on reference years through 2010 and the 2011 wave,
    which the frozen record already holds. A mismatch means this loader
    differs from the selectors' and aborts the run.
    """
    earnings = sources.earnings
    fit_rows = truncate_estimation_frame(
        earnings,
        boundary_year=B2_BOUNDARY,
        year_column="period",
        flow=False,
        label="b2 source check",
    )
    anchor = anchor_frame(sources.person_wave, B2_ANCHOR_WAVE)
    with_row = set(
        earnings.loc[earnings["period"] == B2_BOUNDARY, "person_id"].astype(
            int
        )
    )
    observed = {
        "fit_input_rows": int(len(fit_rows)),
        "n_full_anchor": int(len(anchor)),
        "n_domain": int(len(set(anchor["person_id"].astype(int)) & with_row)),
    }
    if observed != B2_EXPECTED:
        raise AssertionError(
            f"source reproduction failed: {observed} != {B2_EXPECTED}"
        )
    return {
        "expected": dict(B2_EXPECTED),
        "observed": observed,
        "equal": True,
        "anchor_forward_pairs_2010": anchor_forward_pairs(
            earnings, B2_BOUNDARY
        ),
    }


def anchor_forward_pairs(earnings: pd.DataFrame, boundary: int) -> int:
    """The forward-pair count a fit at ``boundary`` trains its gates and
    donor pools on (``fit_forward_earnings``: ages 25-64, rows dated at or
    before the boundary, persons with a boundary-year row). A count only."""
    cutoff = earnings.loc[
        (earnings["period"] <= boundary) & (earnings["weight"] > 0)
    ]
    estimation = cutoff.loc[cutoff["age"].between(fe.AGE_MIN, fe.AGE_MAX)]
    anchors = set(
        cutoff.loc[cutoff["period"] == boundary, "person_id"].astype(int)
    )
    pairs = fe._forward_pairs(estimation)
    return int(pairs["person_id"].isin(anchors).sum())


def cluster_table(
    person_wave: pd.DataFrame,
    fit_person_ids: Iterable[int],
    full_anchor: pd.DataFrame,
) -> pd.DataFrame:
    """Assign every resampled person one household cluster and stratum.

    A person's cluster is the household (collection wave, interview number)
    of their last present wave at or before the anchor wave. Clusters at
    the anchor wave that hold a full-anchor person form the anchor stratum;
    every other cluster forms the other stratum.
    """
    persons = set(int(value) for value in fit_person_ids) | set(
        int(value) for value in full_anchor["person_id"]
    )
    present = person_wave.loc[
        person_wave["sequence"].between(1, 20)
        & (person_wave["period"] <= ANCHOR_WAVE)
        & person_wave["person_id"].isin(persons),
        ["person_id", "period", "interview"],
    ]
    last = (
        present.sort_values(["person_id", "period"], kind="stable")
        .groupby("person_id", sort=True)
        .tail(1)
        .reset_index(drop=True)
    )
    missing = persons - set(last["person_id"].astype(int))
    if missing:
        raise AssertionError(
            f"{len(missing)} resampled persons have no present wave <= 2007"
        )
    last["cluster"] = last["period"].astype("int64") * 100_000 + last[
        "interview"
    ].astype("int64")
    anchor_ids = set(int(value) for value in full_anchor["person_id"])
    anchor_clusters = set(
        last.loc[last["person_id"].isin(anchor_ids), "cluster"].astype(int)
    )
    if not set(
        last.loc[last["person_id"].isin(anchor_ids), "period"].astype(int)
    ) <= {ANCHOR_WAVE}:
        raise AssertionError("a full-anchor person's last wave is not 2007")
    last["stratum"] = np.where(
        last["cluster"].isin(anchor_clusters), "anchor", "other"
    )
    return (
        last[["person_id", "cluster", "stratum"]]
        .sort_values("person_id", kind="stable")
        .reset_index(drop=True)
    )


def _stream(*words: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(list(words)))


def stratum_multiplicities(
    clusters: pd.DataFrame, stratum: str, replicate: int, word: int
) -> dict[int, int]:
    """Multinomial cluster multiplicities for one stratum and replicate."""
    ids = np.sort(
        clusters.loc[clusters["stratum"] == stratum, "cluster"]
        .astype("int64")
        .unique()
    )
    if not len(ids):
        return {}
    counts = _stream(BOOTSTRAP_ROOT_SEED, int(replicate), word).multinomial(
        len(ids), np.full(len(ids), 1.0 / len(ids))
    )
    return {
        int(cluster): int(count)
        for cluster, count in zip(ids, counts, strict=False)
    }


def person_multiplicities(
    clusters: pd.DataFrame, by_cluster: Mapping[int, int]
) -> dict[int, int]:
    """Each person's multiplicity, from their cluster's."""
    return {
        int(person): int(by_cluster.get(int(cluster), 0))
        for person, cluster in zip(
            clusters["person_id"].astype("int64"),
            clusters["cluster"].astype("int64"),
            strict=False,
        )
    }


def copy_persons(
    frame: pd.DataFrame, multiplicity: Mapping[int, int]
) -> pd.DataFrame:
    """Copy each person's rows c times under ids ``person * ID_SCALE + k``.

    Persons absent from ``multiplicity`` are dropped, as are persons with
    multiplicity zero. Row order within a person is kept, and copies of one
    person are adjacent in person order.
    """
    counts = (
        frame["person_id"]
        .astype("int64")
        .map(lambda person: multiplicity.get(int(person), 0))
        .to_numpy(dtype=np.int64)
    )
    if counts.size and int(counts.max()) >= ID_SCALE:
        raise AssertionError("a multiplicity reached the identifier scale")
    repeated = frame.loc[frame.index.repeat(counts)].copy()
    copy = repeated.groupby(level=0).cumcount().to_numpy(dtype=np.int64)
    repeated["person_id"] = (
        repeated["person_id"].astype("int64") * ID_SCALE + copy
    )
    return repeated.sort_values(
        ["person_id", "period"] if "period" in repeated else ["person_id"],
        kind="stable",
    ).reset_index(drop=True)


# --------------------------------------------------------------------------
# Fit, context and projection
# --------------------------------------------------------------------------
@contextmanager
def forests_skipped() -> Iterator[None]:
    """Fit RegimeGatedQRF without its per-sign quantile forests.

    The forward law draws a sign from each fitted gate's classifier
    (``forward_earnings._gate_sign_draw``, lines 1161-1179, called at
    1780-1800 and 1962-1980) and draws levels from its donor pools; it never
    reads the per-sign forests. ``RegimeGatedQRF._fit_target`` fits the
    classifier before the forests, so skipping the forests leaves the
    classifier and every projection unchanged. The startup check in
    ``main`` and ``tests/test_track_b_b0_1_planning_values.py`` verify that
    byte for byte. The forests hold almost all of a fit's memory (about
    60 GB on a PSID-sized invented panel) and half its time.
    """
    qrf = importlib.import_module("populace.fit.qrf")
    original = qrf._fit_forest

    def skipped(*_args: Any, **_kwargs: Any) -> None:
        return None

    qrf._fit_forest = skipped
    try:
        yield
    finally:
        qrf._fit_forest = original


def fit_law(
    fit_input: pd.DataFrame,
    nawi: Mapping[int, float],
    *,
    qrf_factory: Any = None,
    skip_forests: bool = False,
) -> Any:
    """Candidate 3's registered law at the pseudo-origin."""
    with redirect_stdout(sys.stderr):
        if skip_forests:
            with forests_skipped():
                return refit_earnings_chained_generator(
                    fit_input,
                    nawi,
                    seed=FIT_SEED,
                    boundary_year=PSEUDO_ORIGIN,
                    qrf_factory=qrf_factory,
                    candidate_spec=CANDIDATE_3,
                )
        return refit_earnings_chained_generator(
            fit_input,
            nawi,
            seed=FIT_SEED,
            boundary_year=PSEUDO_ORIGIN,
            qrf_factory=qrf_factory,
            candidate_spec=CANDIDATE_3,
        )


def gate_surfaces(fitted: Any) -> dict[str, Any]:
    """Both fitted gates' classifier state and probability surface hashes."""
    return {
        name: selector._participation_gate_audit(
            getattr(fitted.generator, name),
            fitted.forward_pairs,
            name=name,
        )
        for name in ("shared_gate", "zero_anchor_gate")
    }


def forest_skip_check(
    full: Any,
    fit_input: pd.DataFrame,
    nawi: Mapping[int, float],
    context: selector.BoundaryContext,
    full_draws: Sequence[pd.DataFrame],
    *,
    qrf_factory: Any = None,
) -> dict[str, Any]:
    """Refit the full sample without forests; require identical gates and
    identical projections for the first two draw seeds."""
    lean = fit_law(fit_input, nawi, qrf_factory=qrf_factory, skip_forests=True)
    gates_equal = gate_surfaces(lean) == gate_surfaces(full)
    draws_equal = True
    for index, seed in enumerate(DRAW_SEEDS[:2]):
        scored, _ = selector._project(lean.generator, context, seed)
        scored = scored.sort_values(["person_id", "period"], kind="stable")
        draws_equal &= np.array_equal(
            scored["earnings"].to_numpy(dtype=np.float64),
            full_draws[index]["earnings"].to_numpy(dtype=np.float64),
        )
    if not (gates_equal and draws_equal):
        raise AssertionError("skipping the forests changed the law")
    return {
        "gate_states_and_surfaces_equal": True,
        "projections_equal_draw_seeds": list(DRAW_SEEDS[:2]),
    }


def build_context(
    fitted: Any,
    earnings: pd.DataFrame,
    full_anchor: pd.DataFrame,
) -> selector.BoundaryContext:
    """The selectors' boundary context at 2006, without floor or truth cells.

    Mirrors ``select_m6_qstar_train_only._boundary_context`` lines
    1416-1502 (anchor, domain equality, fixed weight, truth support and the
    initial slice).
    """
    fitted_domain = earnings_domain_person_ids(fitted.generator)
    domain_ids = frozenset(
        int(value)
        for value in set(full_anchor["person_id"].astype(int)) & fitted_domain
    )
    fitted_anchor_ids = frozenset(fitted.anchors["person_id"].astype(int))
    if domain_ids != fitted_anchor_ids:
        raise AssertionError(
            "full-anchor/domain mismatch at the pseudo-origin"
        )
    fixed_weight = full_anchor.set_index("person_id")["weight"]
    truth = earnings.loc[
        earnings["period"].isin(SCORED_PERIODS)
        & earnings["person_id"].isin(domain_ids)
    ].copy()
    truth["raw_row_weight"] = truth["weight"].astype("float64")
    truth["weight"] = truth["person_id"].map(fixed_weight).astype("float64")
    truth["cohort"] = truth["age"].map(selector._cohort)
    truth = truth[truth["cohort"].notna()].copy()
    truth = truth.sort_values(["person_id", "period"], kind="stable")
    truth = truth.reset_index(drop=True)
    if truth.duplicated(["person_id", "period"]).any():
        raise ValueError("truth support has duplicate person-period rows")
    anchor_state = fitted.anchors[
        fitted.anchors["person_id"].isin(domain_ids)
    ][["person_id", "age"]].copy()
    anchor_state = anchor_state.sort_values("person_id", kind="stable")
    initial_slice = anchor_state.assign(
        year=PSEUDO_ORIGIN,
        sex=selector.SCHEMA_SEX_SENTINEL,
        **{EARNINGS_DOMAIN_COLUMN: True},
    )
    return selector.BoundaryContext(
        boundary=PSEUDO_ORIGIN,
        full_anchor=full_anchor,
        domain_ids=domain_ids,
        initial_slice=initial_slice,
        truth_support=truth,
        truth_cells={},
        floor={},
        floor_gate_seed_detail=(),
        standardizers={},
        support_audit={},
        rng_manifest={},
    )


def project_draws(
    generator: Any, context: selector.BoundaryContext
) -> list[pd.DataFrame]:
    """The K scored projection frames (selectors' loop, registered seeds)."""
    frames = []
    for seed in DRAW_SEEDS:
        scored, _ = selector._project(generator, context, seed)
        frames.append(
            scored.sort_values(
                ["person_id", "period"], kind="stable"
            ).reset_index(drop=True)
        )
    return frames


# --------------------------------------------------------------------------
# Household-split floor at the pseudo-origin
# --------------------------------------------------------------------------
def household_floor(
    full_anchor: pd.DataFrame, truth: pd.DataFrame
) -> dict[str, dict[str, float]]:
    """``run_floor`` on 2007 households (Q3(b)), seeds 0-99, truth only."""
    domain = set(int(value) for value in truth["person_id"].unique())

    def compute(person_ids: set[object]) -> dict[str, Any]:
        selected = set(int(value) for value in person_ids) & domain
        return earnings_cells(
            truth[truth["person_id"].isin(selected)],
            level_years=LEVEL_YEARS,
            change_years=CHANGE_YEARS,
        )

    floor, _ = run_floor(full_anchor, compute, "household_id")
    return {name: floor[name] for name in CELLS}


def floor_eligible(record: Mapping[str, Any]) -> bool:
    """M6's gating condition: all 100 seeds defined, >= 20 weaker-half events."""
    return (
        int(record["n_defined_seeds"]) == len(FLOOR_SEEDS)
        and int(record["min_events_weaker_half"]) >= MIN_EVENTS
        and float(record["realized_sigma"]) > 0
    )


def se_upper(sigma: float) -> float:
    """The audit's full-support gap standard-error bound (section 11)."""
    return float(sigma) * math.sqrt(1.0 + 1.0 / K) / 2.0


# --------------------------------------------------------------------------
# Replicates
# --------------------------------------------------------------------------
def draw_cell_values(
    truth: pd.DataFrame, draws: Sequence[pd.DataFrame]
) -> tuple[dict[str, float | None], list[dict[str, float | None]]]:
    """Truth and per-draw cell values on one frame set (in memory only)."""
    truth_cells = {
        name: cell["value"] for name, cell in cell_values(truth).items()
    }
    draw_cells = [
        {name: cell["value"] for name, cell in cell_values(frame).items()}
        for frame in draws
    ]
    return truth_cells, draw_cells


def gaps_from(
    truth_cells: Mapping[str, float | None],
    draw_cells: Sequence[Mapping[str, float | None]],
) -> dict[str, float | None]:
    return {
        name: signed_gap(
            CELL_METRICS[name],
            [cells[name] for cells in draw_cells],
            truth_cells[name],
        )
        for name in CELLS
    }


def truth_deviation(
    metric: str, value: float | None, reference: float | None
) -> float | None:
    """A replicate truth statistic's deviation from the full sample's, in
    the gap's own scale. It is a centered quantity, not a level."""
    if value is None or reference is None:
        return None
    if metric == "log_ratio":
        if value <= 0 or reference <= 0:
            return None
        return math.log(value / reference)
    return value - reference


def anchor_multiplicities(clusters: pd.DataFrame, replicate: int) -> dict:
    """Arm F's person multiplicities: full-anchor households only."""
    return person_multiplicities(
        clusters, stratum_multiplicities(clusters, "anchor", replicate, 0)
    )


def half_sample(ids: np.ndarray, replicate: int, word: int) -> dict[int, int]:
    """A without-replacement half of ``ids`` (floor(n/2) of them)."""
    ids = np.sort(np.asarray(ids, dtype=np.int64))
    order = _stream(BOOTSTRAP_ROOT_SEED, int(replicate), word).permutation(
        len(ids)
    )
    chosen = set(ids[order[: len(ids) // 2]].tolist())
    return {int(value): int(value in chosen) for value in ids}


def refit_multiplicities(clusters: pd.DataFrame, replicate: int) -> dict:
    """Arm R's person multiplicities under ``REFIT_SCHEME``.

    ``copies``: arm F's multinomial for full-anchor households (the same
    stream, so the frames pair) and an independent multinomial for every
    other cluster. ``half``: a without-replacement half of each stratum's
    clusters.
    """
    if REFIT_SCHEME == "copies":
        by_cluster = {
            **stratum_multiplicities(clusters, "anchor", replicate, 0),
            **stratum_multiplicities(clusters, "other", replicate, 1),
        }
    elif REFIT_SCHEME == "half":
        by_cluster = {}
        for stratum, word in (("anchor", 2), ("other", 3)):
            ids = clusters.loc[clusters["stratum"] == stratum, "cluster"]
            by_cluster.update(half_sample(ids.unique(), replicate, word))
    else:
        raise ValueError(f"unknown refit scheme {REFIT_SCHEME!r}")
    return person_multiplicities(clusters, by_cluster)


def design_multiplicities(design: pd.DataFrame, replicate: int) -> dict:
    """Rao-Wu multiplicities over PSID sampling-error clusters in strata.

    In a stratum with n >= 2 clusters, n - 1 clusters are drawn with
    replacement and each draw counts n / (n - 1); with PSID's two clusters
    per stratum that is one cluster copied twice. A stratum with one
    cluster keeps it once. Fractional counts cannot be copied, so a
    stratum with three or more clusters draws n clusters with replacement
    instead; ``design_summary`` counts such strata.
    """
    rng = _stream(BOOTSTRAP_ROOT_SEED, int(replicate), 4)
    by_secu: dict[tuple[int, int], int] = {}
    for stratum, group in design.groupby("stratum", sort=True):
        clusters = np.sort(group["cluster"].unique())
        n = len(clusters)
        if n == 1:
            counts = np.array([1])
        elif n == 2:
            counts = np.zeros(2, dtype=int)
            counts[rng.integers(0, 2)] = 2
        else:
            counts = rng.multinomial(n, np.full(n, 1.0 / n))
        for cluster, count in zip(clusters, counts, strict=False):
            by_secu[(int(stratum), int(cluster))] = int(count)
    return {
        int(person): by_secu[(int(stratum), int(cluster))]
        for person, stratum, cluster in zip(
            design["person_id"],
            design["stratum"],
            design["cluster"],
            strict=False,
        )
    }


def design_summary(design: pd.DataFrame) -> dict[str, int]:
    sizes = design.groupby("stratum")["cluster"].nunique()
    return {
        "strata": int(len(sizes)),
        "strata_with_one_cluster": int((sizes == 1).sum()),
        "strata_with_two_clusters": int((sizes == 2).sum()),
        "strata_with_three_or_more_clusters": int((sizes >= 3).sum()),
        "persons": int(len(design)),
    }


def arm_f_replicate(
    replicate: int,
    clusters: pd.DataFrame,
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
    truth_reference: Mapping[str, float | None],
) -> dict[str, Any]:
    """Fixed law, fixed per-person paths, households copied (bootstrap)."""
    mult = anchor_multiplicities(clusters, replicate)
    truth_cells, draw_cells = draw_cell_values(
        copy_persons(truth, mult),
        [copy_persons(frame, mult) for frame in draws],
    )
    return {
        "replicate": replicate,
        "gaps": gaps_from(truth_cells, draw_cells),
        "tdev": {
            name: truth_deviation(
                CELL_METRICS[name], truth_cells[name], truth_reference[name]
            )
            for name in CELLS
        },
    }


def arm_d_replicate(
    replicate: int,
    design: pd.DataFrame,
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
) -> dict[str, Any]:
    """Arm F's computation with design clusters resampled within strata."""
    mult = design_multiplicities(design, replicate)
    truth_cells, draw_cells = draw_cell_values(
        copy_persons(truth, mult),
        [copy_persons(frame, mult) for frame in draws],
    )
    return {"replicate": replicate, "gaps": gaps_from(truth_cells, draw_cells)}


def refit_effect(
    metric: str,
    refit_draws: Sequence[float | None],
    fixed_draws: Sequence[float | None],
) -> dict[str, float] | None:
    """The refit's effect on one cell's projected statistic, from the K
    paired draw values on one frame.

    ``delta`` is the refit-law projected statistic minus the fixed-law one
    (a log ratio for log-ratio cells). ``w`` estimates the simulation
    variance of ``delta`` and ``wcov`` the simulation covariance of
    ``delta`` with the fixed-law statistic, both from the draw-to-draw
    spread divided by K (delta method for log-ratio cells).
    """
    if any(value is None for value in (*refit_draws, *fixed_draws)):
        return None
    refit = np.asarray(refit_draws, dtype=np.float64)
    fixed = np.asarray(fixed_draws, dtype=np.float64)
    k = len(refit)
    if k < 2 or k != len(fixed):
        return None
    mean_refit, mean_fixed = float(refit.mean()), float(fixed.mean())
    if metric == "log_ratio":
        if mean_refit <= 0 or mean_fixed <= 0:
            return None
        delta = math.log(mean_refit / mean_fixed)
        refit, fixed = refit / mean_refit, fixed / mean_fixed
    else:
        delta = mean_refit - mean_fixed
    difference = refit - fixed
    return {
        "delta": float(delta),
        "w": float(np.var(difference, ddof=1) / k),
        "wcov": float(np.cov(fixed, difference, ddof=1)[0, 1] / k),
    }


def arm_r_replicate(
    replicate: int,
    clusters: pd.DataFrame,
    fit_input: pd.DataFrame,
    earnings: pd.DataFrame,
    full_anchor: pd.DataFrame,
    nawi: Mapping[int, float],
    truth: pd.DataFrame,
    draws: Sequence[pd.DataFrame],
    *,
    qrf_factory: Any = None,
) -> dict[str, Any]:
    """Refit the law on one resampled household set and project it.

    On the same frame the worker also forms the fixed-law statistic from the
    full-sample projection's per-person paths, so each cell's refit effect
    is a paired difference. It returns no truth or projected value.
    """
    mult = refit_multiplicities(clusters, replicate)
    fitted_b = fit_law(
        copy_persons(fit_input, mult),
        nawi,
        qrf_factory=qrf_factory,
        skip_forests=qrf_factory is None,
    )
    context_b = build_context(
        fitted_b,
        copy_persons(
            earnings.loc[earnings["period"].isin(SCORED_PERIODS)], mult
        ),
        copy_persons(full_anchor, mult),
    )
    truth_r, draws_r = draw_cell_values(
        context_b.truth_support, project_draws(fitted_b.generator, context_b)
    )
    truth_f, draws_f = draw_cell_values(
        copy_persons(truth, mult),
        [copy_persons(frame, mult) for frame in draws],
    )
    return {
        "replicate": replicate,
        "gap_refit": gaps_from(truth_r, draws_r),
        "gap_fixed": gaps_from(truth_f, draws_f),
        "effect": {
            name: refit_effect(
                CELL_METRICS[name],
                [cells[name] for cells in draws_r],
                [cells[name] for cells in draws_f],
            )
            for name in CELLS
        },
        "truth_agreement": truth_agreement(truth_r, truth_f),
    }


def truth_agreement(
    left: Mapping[str, float | None], right: Mapping[str, float | None]
) -> dict[str, Any]:
    """Whether two arms' truth statistics agree; no value is returned."""
    worst = 0.0
    same_definedness = True
    for name in CELLS:
        a, b = left[name], right[name]
        if a is None or b is None:
            same_definedness &= (a is None) == (b is None)
            continue
        worst = max(worst, abs(a - b) / max(abs(a), abs(b), 1e-300))
    return {
        "same_definedness": bool(same_definedness),
        "within_rtol": bool(worst <= TRUTH_AGREEMENT_RTOL),
    }


# --------------------------------------------------------------------------
# Support counts and transport
# --------------------------------------------------------------------------
#: The scored support each cell's sampling variance scales with: its key in
#: ``support_counts`` and in the frozen record's ``counts`` block.
CELL_SUPPORT = {
    **{
        f"earn_{tag}.{cohort}": ("level_cells", cohort)
        for tag in ("p10", "p50", "p90", "zero_rate")
        for cohort in ("prime", "older")
    },
    **{
        f"earn_{tag}.{cohort}": ("change_pairs", cohort)
        for tag in ("dlog_sd", "dlog_mean")
        for cohort in ("prime", "older")
    },
    "earn_mob_h1_diag": ("change_pairs", "pooled_one_step"),
    "earn_autocorr_lag1": ("change_pairs", "pooled_one_step"),
    "earn_mob_h2_diag": ("change_pairs", "pooled_two_step"),
    "earn_autocorr_lag2": ("change_pairs", "pooled_two_step"),
}


def support_counts(truth: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Row and pair counts of a truth support, as the frozen count script
    defines them (``track_b_b0_1_counts.structural_counts``). Every valid
    row counts; nothing is split by earnings sign."""
    origin, first, last = CHANGE_YEARS
    level = truth[truth["period"].isin(LEVEL_YEARS)]

    def pairs(a: int, b: int, cohort: str | None) -> int:
        left = truth.loc[truth["period"] == a, ["person_id", "cohort"]]
        right = truth.loc[truth["period"] == b, ["person_id", "cohort"]]
        joined = left.merge(right, on="person_id", suffixes=("", "_later"))
        if cohort is not None:
            joined = joined[
                (joined["cohort"] == cohort)
                & (joined["cohort_later"] == cohort)
            ]
        return int(len(joined))

    steps = ((origin, first), (first, last))
    return {
        "level_cells": {
            cohort: int((level["cohort"] == cohort).sum())
            for cohort in ("prime", "older")
        },
        "change_pairs": {
            **{
                cohort: sum(pairs(a, b, cohort) for a, b in steps)
                for cohort in ("prime", "older")
            },
            "pooled_one_step": sum(pairs(a, b, None) for a, b in steps),
            "pooled_two_step": pairs(origin, last, None),
        },
    }


def b2_support_counts() -> dict[str, dict[str, int]]:
    """B2's own support counts, from the frozen protocol-v1 record."""
    counts = json.loads(COUNTS.read_text(encoding="utf-8"))["counts"]
    return {
        group: {
            key: int(value["rows"]) for key, value in counts[group].items()
        }
        for group in ("level_cells", "change_pairs")
    }


def transport_factor(
    n_b2: int, n_origin: int, pairs_origin: int, pairs_b2: int
) -> float:
    """How much larger e may be at B2's origin than at the pseudo-origin.

    e is estimation variance over the truth statistic's sampling variance.
    The first falls with the anchor forward-pair count the law is fitted
    on, the second with the cell's scored support, so the ratio scales
    with (n_B2 / n_2006) * (P_2006 / P_2010). The factor never scales
    down.
    """
    scaled = (n_b2 / n_origin) * (pairs_origin / pairs_b2)
    return max(1.0, float(scaled))


def e_for_b2(e_ucl: float, factor: float) -> float:
    """B2's registered estimation-variance ratio: max(0, e_ucl) * factor."""
    return max(0.0, float(e_ucl)) * float(factor)


# --------------------------------------------------------------------------
# Summaries (scale-free ratios only)
# --------------------------------------------------------------------------
def _sd(values: np.ndarray, axis: int | None = None) -> Any:
    return np.std(values, axis=axis, ddof=1)


def summarize_cell(
    arm_f: Sequence[tuple[float | None, float | None]],
    arm_r: Sequence[Mapping[str, float] | None],
    arm_d: Sequence[float | None],
    factor: float,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """One cell's planning values, as ratios to se_up.

    ``arm_f`` holds (gap, truth deviation) per bootstrap replicate;
    ``arm_r`` holds each refit replicate's ``delta``, ``w``, ``wcov``,
    ``gap_fixed`` and ``gap_refit``; ``arm_d`` holds the design arm's gaps.

    - se_up = SD(truth deviation) * sqrt(1 + 1/K): the audit's upper bound,
      with the truth statistic's standard error taken from the same
      replicates instead of from the 100-seed floor;
    - r = SD(gap) / se_up over arm F;
    - e = (Var(delta) - mean(w)) / se_up**2 over arm R: the variance of the
      refit's effect, net of simulation variance;
    - s2 = r**2 + factor * max(0, e), the gap variance B2's bound rule sees.

    Limits resample replicate indices jointly (numerators and denominators
    together). Upper limits are 97.5th percentiles: percentile limits
    from this many refits under-cover, so the wider limit stands for a
    one-sided 95% bound.
    """
    f = np.asarray(
        [
            pair
            for pair in arm_f
            if pair[0] is not None and pair[1] is not None
        ],
        dtype=np.float64,
    ).reshape(-1, 2)
    r_rows = [row for row in arm_r if row is not None]
    d = np.asarray([g for g in arm_d if g is not None], dtype=np.float64)
    out: dict[str, Any] = {
        "n_defined": {
            "arm_f": int(len(f)),
            "arm_r": int(len(r_rows)),
            "arm_d": int(len(d)),
        },
        "n_undefined": {
            "arm_f": int(len(arm_f) - len(f)),
            "arm_r": int(len(arm_r) - len(r_rows)),
            "arm_d": int(len(arm_d) - len(d)),
        },
    }
    enough = (
        len(f) >= MIN_DEFINED_SHARE_F * len(arm_f)
        and len(f) >= 2
        and len(r_rows) == len(arm_r)
        and len(r_rows) >= 2
    )
    if not enough:
        out["defined"] = False
        return out
    gap_f, tdev = f[:, 0], f[:, 1]
    inflate = 1.0 + 1.0 / K
    var_up = float(np.var(tdev, ddof=1) * inflate)
    if not var_up > 0:
        out["defined"] = False
        return out
    delta = np.asarray([row["delta"] for row in r_rows])
    w = np.asarray([row["w"] for row in r_rows])
    wcov = np.asarray([row["wcov"] for row in r_rows])
    gap_fixed = np.asarray([row["gap_fixed"] for row in r_rows])
    gap_refit = np.asarray([row["gap_refit"] for row in r_rows])

    r2 = float(np.var(gap_f, ddof=1) / var_up)
    e = float((np.var(delta, ddof=1) - w.mean()) / var_up)
    cross = float(
        2.0 * (np.cov(gap_fixed, delta, ddof=1)[0, 1] - wcov.mean()) / var_up
    )

    r2_star = np.empty(N_CI_RESAMPLES)
    up_star = np.empty(N_CI_RESAMPLES)
    for start in range(0, N_CI_RESAMPLES, CI_BATCH):
        stop = min(N_CI_RESAMPLES, start + CI_BATCH)
        idx = rng.integers(0, len(f), size=(stop - start, len(f)))
        up_star[start:stop] = np.var(tdev[idx], axis=1, ddof=1) * inflate
        r2_star[start:stop] = (
            np.var(gap_f[idx], axis=1, ddof=1) / up_star[start:stop]
        )
    idx = rng.integers(0, len(delta), size=(N_CI_RESAMPLES, len(delta)))
    e_star = (
        np.var(delta[idx], axis=1, ddof=1) - w[idx].mean(axis=1)
    ) / up_star
    centered_fixed = gap_fixed[idx] - gap_fixed[idx].mean(
        axis=1, keepdims=True
    )
    centered_delta = delta[idx] - delta[idx].mean(axis=1, keepdims=True)
    cov_star = (centered_fixed * centered_delta).sum(axis=1) / (len(delta) - 1)
    cross_star = 2.0 * (cov_star - wcov[idx].mean(axis=1)) / up_star
    s2_star = r2_star + factor * np.maximum(0.0, e_star)

    def limits(samples: np.ndarray) -> list[float]:
        return [float(np.quantile(samples, level)) for level in CI_LEVELS]

    e_ucl = float(np.quantile(e_star, UCL_LEVEL))
    cross_ci = limits(cross_star)
    cross_positive = bool(cross_ci[0] > 0)
    s2_ucl = float(np.quantile(s2_star, UCL_LEVEL))
    out.update(
        {
            "defined": True,
            "shared_anchor_ratio": {
                "r": math.sqrt(r2),
                "ci": [math.sqrt(max(0.0, v)) for v in limits(r2_star)],
            },
            "estimation_variance": {
                "e": e,
                "ci": limits(e_star),
                "e_ucl": e_ucl,
                "e_ucl_negative": bool(e_ucl < 0),
                "transport_factor": float(factor),
                "e_b2": e_for_b2(e_ucl, factor),
            },
            "gap_variance": {
                "s2": r2 + factor * max(0.0, e),
                "s2_ucl": s2_ucl,
                "cross_term_resolved_positive": cross_positive,
                "s2_gate": s2_ucl
                + (factor * cross if cross_positive else 0.0),
            },
            "diagnostics": {
                "cross_term": cross,
                "cross_term_ci": cross_ci,
                "simulation_share_of_refit_variance": float(
                    w.mean() / np.var(delta, ddof=1)
                ),
                "increment": float(
                    (np.var(gap_refit, ddof=1) - np.var(gap_fixed, ddof=1))
                    / var_up
                ),
                "var_ratio_fixed_on_refit_frames": float(
                    np.var(gap_fixed, ddof=1) / var_up
                ),
            },
        }
    )
    if len(d) >= 2:
        d_star = np.empty(N_CI_RESAMPLES)
        for start in range(0, N_CI_RESAMPLES, CI_BATCH):
            stop = min(N_CI_RESAMPLES, start + CI_BATCH)
            idx_d = rng.integers(0, len(d), size=(stop - start, len(d)))
            idx_f = rng.integers(0, len(f), size=(stop - start, len(f)))
            d_star[start:stop] = _sd(d[idx_d], axis=1) / _sd(
                gap_f[idx_f], axis=1
            )
        ratio_ci = limits(d_star)
        out["design_ratio"] = {
            "d": float(_sd(d) / _sd(gap_f)),
            "ci": ratio_ci,
            "within_limit": bool(ratio_ci[1] <= DESIGN_RATIO_LIMIT),
        }
    return out


def cell_record(
    name: str,
    floor_entry: Mapping[str, Any],
    arm_f: Sequence[tuple[float | None, float | None]],
    arm_r: Sequence[Mapping[str, float] | None],
    arm_d: Sequence[float | None],
    factor: float,
    void: bool,
    rng: np.random.Generator,
    mc_error: float | None = None,
) -> dict[str, Any]:
    """One cell's recorded entry: eligibility and scale-free ratios only.

    A cell has planning values only if its pseudo-origin household floor is
    eligible, no arm is void, at least 99% of arm F's replicates and every
    arm R replicate are defined. A cell without them cannot gate B2.
    """
    eligible = floor_eligible(floor_entry)
    cell: dict[str, Any] = {
        "metric": CELL_METRICS[name],
        "floor_household_eligible": eligible,
    }
    if not eligible or void:
        cell["defined"] = False
        cell["undefined_reason"] = (
            "arm_void" if void else "pseudo_origin_floor_ineligible"
        )
        return cell
    cell.update(summarize_cell(arm_f, arm_r, arm_d, factor, rng))
    if cell.get("defined"):
        tdev = np.asarray(
            [pair[1] for pair in arm_f if None not in pair], dtype=np.float64
        )
        cell["diagnostics"]["floor_sigma_over_twice_truth_sd"] = float(
            float(floor_entry["realized_sigma"]) / (2.0 * _sd(tdev))
        )
        if mc_error is not None:
            cell["diagnostics"]["mc_error_over_se_up"] = float(
                mc_error / (_sd(tdev) * math.sqrt(1.0 + 1.0 / K))
            )
    else:
        cell["undefined_reason"] = "too_few_defined_replicates"
    return cell


#: Every key path a recorded cell may hold (protocol v2, "Recorded").
CELL_RECORD_PATHS = frozenset(
    {
        "metric",
        "floor_household_eligible",
        "defined",
        "undefined_reason",
        "n_defined",
        "n_defined/arm_f",
        "n_defined/arm_r",
        "n_defined/arm_d",
        "n_undefined",
        "n_undefined/arm_f",
        "n_undefined/arm_r",
        "n_undefined/arm_d",
        "shared_anchor_ratio",
        "shared_anchor_ratio/r",
        "shared_anchor_ratio/ci",
        "estimation_variance",
        "estimation_variance/e",
        "estimation_variance/ci",
        "estimation_variance/e_ucl",
        "estimation_variance/e_ucl_negative",
        "estimation_variance/transport_factor",
        "estimation_variance/e_b2",
        "gap_variance",
        "gap_variance/s2",
        "gap_variance/s2_ucl",
        "gap_variance/cross_term_resolved_positive",
        "gap_variance/s2_gate",
        "design_ratio",
        "design_ratio/d",
        "design_ratio/ci",
        "design_ratio/within_limit",
        "diagnostics",
        "diagnostics/cross_term",
        "diagnostics/cross_term_ci",
        "diagnostics/simulation_share_of_refit_variance",
        "diagnostics/increment",
        "diagnostics/var_ratio_fixed_on_refit_frames",
        "diagnostics/floor_sigma_over_twice_truth_sd",
        "diagnostics/mc_error_over_se_up",
    }
)


def monte_carlo_error(
    metric: str, draw_values: Sequence[float | None]
) -> float | None:
    """The projected statistic's simulation standard error in the gap's
    scale: the draw-to-draw SD over sqrt(K) (of ln P_k for log-ratio
    cells). Element 8's Monte Carlo rule compares it with the tolerance."""
    if any(value is None for value in draw_values) or len(draw_values) < 2:
        return None
    values = np.asarray(draw_values, dtype=np.float64)
    if metric == "log_ratio":
        if (values <= 0).any():
            return None
        values = np.log(values)
    return float(_sd(values) / math.sqrt(len(values)))


def gap_correlation(
    results: Sequence[Mapping[str, Any] | None],
) -> dict[str, Any]:
    """Arm F's correlation matrix of the cells' gaps (a covariance-type
    quantity), over replicates in which every listed cell is defined."""
    rows = [r["gaps"] for r in results if r is not None]
    names = [
        name
        for name in CELLS
        if sum(row[name] is not None for row in rows)
        >= MIN_DEFINED_SHARE_F * len(rows)
    ]
    matrix = np.asarray(
        [
            [row[name] for name in names]
            for row in rows
            if all(row[name] is not None for name in names)
        ],
        dtype=np.float64,
    )
    if len(names) < 2 or len(matrix) < 3:
        return {"cells": names, "matrix": None, "replicates": int(len(matrix))}
    return {
        "cells": names,
        "matrix": np.corrcoef(matrix, rowvar=False).round(4).tolist(),
        "replicates": int(len(matrix)),
    }


#: The record's top-level keys (protocol v2, "Recorded").
RECORD_KEYS = frozenset(
    {
        "schema",
        "protocol",
        "protocol_v2_sha256",
        "repository_head",
        "worktree_clean",
        "script_sha256",
        "runtime",
        "psid_dir",
        "psid_files_opened_sha256",
        "nawi",
        "source_reproduction",
        "forest_skip_check",
        "geometry",
        "law",
        "counts",
        "bootstrap",
        "transport",
        "design_rule",
        "arm_f_gap_correlation",
        "cells",
        "outcome_blind",
        "wall_seconds",
        "freeze_push",
        "checkpoint_events",
    }
)


def assert_record_shape(record: Mapping[str, Any]) -> None:
    """Refuse a record with an unlisted key, a level or gap key, or a
    value that is not finite."""
    if set(record) - RECORD_KEYS:
        raise AssertionError("the record holds an unlisted top-level key")
    assert_record_is_variance_only(record)
    for cell in record["cells"].values():
        if not key_paths(cell) <= CELL_RECORD_PATHS:
            raise AssertionError("a cell record holds an unlisted key")
    json.dumps(record, allow_nan=False)


def key_paths(record: Mapping[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, item in record.items():
        path = f"{prefix}{key}"
        paths.add(path)
        if isinstance(item, Mapping):
            paths |= key_paths(item, f"{path}/")
    return paths


def assert_record_is_variance_only(record: Any, path: str = "") -> None:
    """Refuse a record that carries a forbidden (level or gap) key."""
    if isinstance(record, Mapping):
        for key, item in record.items():
            if str(key) in FORBIDDEN_RECORD_KEYS:
                raise AssertionError(f"forbidden record key at {path}/{key}")
            assert_record_is_variance_only(item, f"{path}/{key}")
    elif isinstance(record, list | tuple):
        for index, item in enumerate(record):
            assert_record_is_variance_only(item, f"{path}[{index}]")


# --------------------------------------------------------------------------
# Provenance guards
# --------------------------------------------------------------------------
def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def protocol_block_sha256(text: str) -> str:
    """SHA-256 of the protocol-v2 block, markers included."""
    start = text.index(PROTOCOL_BEGIN)
    stop = text.index(PROTOCOL_END) + len(PROTOCOL_END)
    if text.count(PROTOCOL_BEGIN) != 1 or text.count(PROTOCOL_END) != 1:
        raise AssertionError("the protocol-v2 markers are not unique")
    return hashlib.sha256(text[start:stop].encode()).hexdigest()


def runtime_record() -> dict[str, Any]:
    observed = {
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "pandas": importlib.metadata.version("pandas"),
        "scikit_learn": importlib.metadata.version("scikit-learn"),
        "scipy": importlib.metadata.version("scipy"),
        "quantile_forest": importlib.metadata.version("quantile-forest"),
        "populace_fit": importlib.metadata.version("populace-fit"),
        "populace_frame": importlib.metadata.version("populace-frame"),
    }
    if observed != RUNTIME:
        raise RuntimeError(f"runtime {observed} differs from {RUNTIME}")
    qrf_path = Path(
        inspect.getfile(importlib.import_module("populace.fit.qrf"))
    ).resolve()
    populace_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=qrf_path.parent,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )

    def populace_git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=populace_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    head = populace_git("rev-parse", "HEAD")
    fit_tree = populace_git(
        "rev-parse", "HEAD:packages/populace-fit/src/populace/fit"
    )
    frame_tree = populace_git(
        "rev-parse", "HEAD:packages/populace-frame/src/populace/frame"
    )
    dirty = populace_git(
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        "packages/populace-fit/src",
        "packages/populace-frame/src",
    )
    if (
        head != selector.EXPECTED_POPULACE_HEAD
        or fit_tree != selector.EXPECTED_POPULACE_FIT_TREE
        or frame_tree != selector.EXPECTED_POPULACE_FRAME_TREE
        or dirty
    ):
        raise RuntimeError("the populace fitting stack is not the pinned one")
    return {
        "versions": observed,
        "populace_head": head,
        "populace_fit_tree": fit_tree,
        "populace_frame_tree": frame_tree,
        "threads": {name: os.environ.get(name) for name in THREAD_ENV},
        "platform": platform.platform(),
    }


def nawi_2006(pe_us_dir: Path) -> tuple[dict[int, float], dict[str, Any]]:
    """NAWI through 2006 by the selectors' prefix reader, hash-pinned."""
    dist = list(pe_us_dir.glob("policyengine_us-*.dist-info"))
    if len(dist) != 1:
        raise RuntimeError("expected exactly one policyengine-us dist-info")
    metadata = (dist[0] / "METADATA").read_text(encoding="utf-8")
    version = next(
        line.split(":", 1)[1].strip()
        for line in metadata.splitlines()
        if line.startswith("Version:")
    )
    if version != POLICYENGINE_US_VERSION:
        raise RuntimeError(f"policyengine-us {version} is not 1.752.2")
    path = pe_us_dir / NAWI_RELATIVE
    values, audit = selector._read_historical_nawi(
        path, maximum_year=PSEUDO_ORIGIN
    )
    expected = selector.EXPECTED_BOUNDARY_NAWI[PSEUDO_ORIGIN]
    if (
        audit["bytes_consumed_through_maximum_key"] != expected["prefix_bytes"]
        or audit["admitted_prefix_sha256"] != expected["prefix_sha256"]
        or _canonical_sha256(values) != expected["mapping_sha256"]
    ):
        raise RuntimeError("the 2006 NAWI prefix differs from the pin")
    if missing := sorted(
        set(range(PSEUDO_ORIGIN - 9, PSEUDO_ORIGIN + 1)) - set(values)
    ):
        raise ValueError(f"NAWI misses fit-decade years {missing}")
    return values, {
        "policyengine_us_version": version,
        "maximum_key_year": audit["maximum_admitted_key_year"],
        "prefix_bytes": audit["bytes_consumed_through_maximum_key"],
        "prefix_sha256": audit["admitted_prefix_sha256"],
        "mapping_sha256": _canonical_sha256(values),
    }


# --------------------------------------------------------------------------
# Parallel replicate driver with a private, gap-only checkpoint
# --------------------------------------------------------------------------
class InfrastructureInterruption(RuntimeError):
    """A failure outside any replicate (worker killed, pool broken)."""


_WORKER: dict[str, Any] = {}


def _worker_init(payload: dict[str, Any]) -> None:
    _WORKER.clear()
    _WORKER.update(payload)


def _guarded(function: Callable[[int], dict[str, Any]], replicate: int):
    """Turn an exception inside a replicate into a counted failure."""
    try:
        return function(replicate)
    except (MemoryError, OSError):
        raise  # infrastructure, not a property of the replicate
    except Exception as error:  # noqa: BLE001 (recorded and counted)
        return {
            "replicate": replicate,
            "failed": True,
            "exception_class": type(error).__name__,
        }


def _worker_f(replicate: int) -> dict[str, Any]:
    return _guarded(
        lambda b: arm_f_replicate(
            b,
            _WORKER["clusters"],
            _WORKER["truth"],
            _WORKER["draws"],
            _WORKER["truth_reference"],
        ),
        replicate,
    )


def _worker_d(replicate: int) -> dict[str, Any]:
    return _guarded(
        lambda b: arm_d_replicate(
            b, _WORKER["design"], _WORKER["truth"], _WORKER["draws"]
        ),
        replicate,
    )


def _worker_r(replicate: int) -> dict[str, Any]:
    return _guarded(
        lambda b: arm_r_replicate(
            b,
            _WORKER["clusters"],
            _WORKER["fit_input"],
            _WORKER["earnings"],
            _WORKER["full_anchor"],
            _WORKER["nawi"],
            _WORKER["truth"],
            _WORKER["draws"],
        ),
        replicate,
    )


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def open_checkpoint(directory: Path, identity: Mapping[str, str]) -> dict:
    """Bind a checkpoint to one commit and protocol, refuse any other, and
    log this process's start. Returns the manifest."""
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["identity"] != dict(identity):
            raise RuntimeError("the checkpoint belongs to another run")
        if manifest["events"][-1]["event"] == "process_start":
            manifest["events"].append(
                {"event": "unlogged_termination", "utc": _utc()}
            )
    else:
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {
            "identity": dict(identity),
            "events": [],
            "arm_r_started_epoch": None,
        }
    manifest["events"].append({"event": "process_start", "utc": _utc()})
    write_manifest(directory, manifest)
    return manifest


def write_manifest(directory: Path, manifest: Mapping[str, Any]) -> None:
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def arm_r_deadline(directory: Path, manifest: dict) -> float:
    """The arm-R budget runs from arm R's first start, across resumes."""
    if manifest["arm_r_started_epoch"] is None:
        manifest["arm_r_started_epoch"] = time.time()
        write_manifest(directory, manifest)
    return float(manifest["arm_r_started_epoch"]) + ARM_R_BUDGET_SECONDS


def run_replicates(
    arm: str,
    count: int,
    function: Callable[[int], dict[str, Any]],
    payload: dict[str, Any],
    workers: int,
    checkpoint: Path,
    *,
    minimum: int | None = None,
    deadline: float | None = None,
) -> tuple[list[dict[str, Any] | None], dict[str, Any]]:
    """Run replicates 0..count-1 in index order, resuming this run's own
    checkpoint.

    With ``deadline`` (a wall-clock time), replicates still pending when it
    passes are cancelled and the arm keeps the longest completed prefix
    0..B-1, which must hold at least ``minimum`` replicates. The rule
    depends on time only, never on a value.
    """
    directory = checkpoint / arm
    directory.mkdir(parents=True, exist_ok=True)
    results: dict[int, dict[str, Any]] = {}
    for path in sorted(directory.glob("replicate-*.json")):
        stored = json.loads(path.read_text(encoding="utf-8"))
        results[int(stored["replicate"])] = stored
    resumed = len(results)
    pending = [index for index in range(count) if index not in results]
    _progress(f"{arm}: {resumed} checkpointed, {len(pending)} to run")
    stopped_at_deadline = False
    if pending:
        try:
            with futures.ProcessPoolExecutor(
                max_workers=workers,
                initializer=_worker_init,
                initargs=(payload,),
            ) as pool:
                submitted = {
                    pool.submit(function, index): index for index in pending
                }
                done = 0
                while submitted:
                    timeout = (
                        None
                        if deadline is None
                        else max(0.0, deadline - time.time())
                    )
                    finished, _ = futures.wait(
                        submitted,
                        timeout=timeout,
                        return_when=futures.FIRST_COMPLETED,
                    )
                    if not finished:
                        stopped_at_deadline = True
                        for future in submitted:
                            future.cancel()
                        break
                    for future in finished:
                        index = submitted.pop(future)
                        try:
                            stored = future.result()
                        except Exception as error:  # noqa: BLE001
                            raise InfrastructureInterruption(
                                f"{arm}: {type(error).__name__}"
                            ) from error
                        (directory / f"replicate-{index:05d}.json").write_text(
                            json.dumps(stored), encoding="utf-8"
                        )
                        results[index] = stored
                        done += 1
                        if done % max(1, len(pending) // 20) == 0:
                            _progress(
                                f"{arm}: {done}/{len(pending)} replicates done"
                            )
                if stopped_at_deadline:
                    pool.shutdown(wait=False, cancel_futures=True)
        except futures.process.BrokenProcessPool as error:
            raise InfrastructureInterruption(f"{arm}: {error!r}") from error
    prefix = 0
    while prefix in results:
        prefix += 1
    used = count if not stopped_at_deadline else prefix
    if minimum is not None and used < minimum:
        raise AssertionError(f"{arm}: only {used} replicates before deadline")
    ordered = []
    failures: list[str] = []
    for index in range(used):
        stored = results[index]
        if stored.get("failed"):
            failures.append(stored["exception_class"])
            ordered.append(None)
        else:
            ordered.append(stored)
    status = {
        "requested": count,
        "used": used,
        "stopped_at_deadline": stopped_at_deadline,
        "resumed_from_checkpoint": resumed,
        "failed": len(failures),
        "failure_classes": sorted(set(failures)),
    }
    status["void"] = status["failed"] > MAX_FAILED_SHARE * used
    return ordered, status


def thread_settings() -> dict[str, str]:
    """The run's explicit thread settings (both must be set)."""
    settings = {name: os.environ.get(name) for name in THREAD_ENV}
    unset = sorted(name for name, value in settings.items() if not value)
    if unset:
        raise RuntimeError(f"set {unset} explicitly for the run")
    return {name: str(value) for name, value in settings.items()}


def pushed_head(branch: str) -> str:
    """The remote branch head, read before any PSID file is opened."""
    out = _git("ls-remote", "origin", f"refs/heads/{branch}")
    if not out:
        raise RuntimeError(f"branch {branch} is not on origin")
    return out.split()[0]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--workers-f", type=int, default=8)
    parser.add_argument("--workers-r", type=int, default=4)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    started = time.time()
    checkpoint = args.checkpoint_dir.resolve()
    if checkpoint.is_relative_to(ROOT):
        raise RuntimeError("the checkpoint directory must be outside the repo")
    if OUTPUT.exists():
        raise FileExistsError(f"{OUTPUT} exists; the run is one-shot")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("the worktree is not clean")
    head = _git("rev-parse", "HEAD")
    if head != args.freeze_commit:
        raise RuntimeError("HEAD is not the protocol-freeze commit")
    remote = pushed_head(args.branch)
    if remote != head:
        raise RuntimeError("the freeze commit is not the pushed branch head")
    block = protocol_block_sha256(ADDENDUM.read_text(encoding="utf-8"))
    if block != PROTOCOL_V2_SHA256:
        raise RuntimeError("the protocol-v2 block differs from the frozen one")
    identity = {
        "head": head,
        "protocol_v2_sha256": block,
        **thread_settings(),
    }
    manifest = open_checkpoint(checkpoint, identity)
    push_record = {"branch": args.branch, "remote_head": remote, "utc": _utc()}
    try:
        record = _run(args, checkpoint, manifest, head, block, started)
    except (
        InfrastructureInterruption,
        MemoryError,
        KeyboardInterrupt,
    ) as error:
        manifest["events"].append(
            {
                "event": "interrupted",
                "utc": _utc(),
                "exception_class": type(error).__name__,
            }
        )
        write_manifest(checkpoint, manifest)
        _progress("interrupted; the checkpoint is kept for a logged resume")
        raise
    except BaseException as error:
        shutil.rmtree(checkpoint, ignore_errors=True)
        _progress(
            "failed: publish the stage and exception class "
            f"({type(error).__name__}); the checkpoint was deleted"
        )
        raise
    record["freeze_push"] = push_record
    record["checkpoint_events"] = manifest["events"] + [
        {"event": "completed", "utc": _utc()}
    ]
    assert_record_shape(record)
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True)
        stream.write("\n")
    shutil.rmtree(checkpoint)
    _progress(f"wrote {OUTPUT.relative_to(ROOT)}; checkpoint deleted")
    return 0


def _run(
    args: argparse.Namespace,
    checkpoint: Path,
    manifest: dict,
    head: str,
    block: str,
    started: float,
) -> dict[str, Any]:
    runtime = runtime_record()
    psid_dir = Path(os.environ["POPULACE_DYNAMICS_PSID_DIR"]).resolve()
    pe_us_dir = Path(os.environ["POPULACE_DYNAMICS_PE_US_DIR"]).resolve()

    _progress("reading field-capped sources (collection waves <= 2011)")
    with psid_read_guard(psid_dir), record_files_read(psid_dir) as opened:
        sources = load_sources(psid_dir)
    if not all(psid_path_allowed(Path(name)) for name in opened):
        raise AssertionError("a PSID file outside the read set was opened")
    late = [
        name
        for name in opened
        if name.startswith("family/")
        and int(name.split("/")[1]) > MAX_COLLECTION_WAVE
    ]
    if late:
        raise AssertionError(f"post-2011 family files were opened: {late}")
    checks = source_checks(sources)
    nawi, nawi_record = nawi_2006(pe_us_dir)

    earnings = sources.earnings
    fit_input = truncate_estimation_frame(
        earnings,
        boundary_year=PSEUDO_ORIGIN,
        year_column="period",
        flow=False,
        label="pseudo-origin fit input",
    )
    full_anchor = anchor_frame(sources.person_wave, ANCHOR_WAVE)
    _progress("fitting candidate 3's law at the pseudo-origin")
    fitted = fit_law(fit_input, nawi)
    context = build_context(fitted, earnings, full_anchor)
    truth = context.truth_support
    _progress("projecting the full sample (K draws)")
    draws = project_draws(fitted.generator, context)
    _progress("checking that a forest-free refit is the same law")
    skip_check = forest_skip_check(fitted, fit_input, nawi, context, draws)
    fitted_pairs = fitted.forward_pairs[["person_id"]]
    del fitted
    _progress("household-split floor, seeds 0-99")
    floor = household_floor(full_anchor, truth)
    clusters = cluster_table(
        sources.person_wave, fit_input["person_id"].unique(), full_anchor
    )

    truth_reference, full_draw_cells = draw_cell_values(truth, draws)
    mc_errors = {
        name: monte_carlo_error(
            CELL_METRICS[name], [cells[name] for cells in full_draw_cells]
        )
        for name in CELLS
    }
    del full_draw_cells
    domain_persons = set(int(value) for value in truth["person_id"].unique())
    with psid_read_guard(psid_dir), record_files_read(psid_dir) as opened_d:
        design = read_design_variables(data_dir=psid_dir)
    opened.update(opened_d)
    design = design[design["person_id"].isin(domain_persons)].reset_index(
        drop=True
    )
    if set(design["person_id"].astype(int)) != domain_persons:
        raise AssertionError("a domain person has no design variables")

    payload = {
        "clusters": clusters,
        "truth": truth,
        "draws": draws,
        "truth_reference": truth_reference,
        "design": design,
    }
    results_f, status_f = run_replicates(
        "arm_f", B_F, _worker_f, payload, args.workers_f, checkpoint
    )
    results_d, status_d = run_replicates(
        "arm_d", B_D, _worker_d, payload, args.workers_f, checkpoint
    )
    payload_r = {
        "clusters": clusters,
        "fit_input": fit_input,
        "earnings": earnings.loc[earnings["period"].isin(SCORED_PERIODS)],
        "full_anchor": full_anchor,
        "nawi": nawi,
        "truth": truth,
        "draws": draws,
    }
    results_r, status_r = run_replicates(
        "arm_r",
        B_R_MAX,
        _worker_r,
        payload_r,
        args.workers_r,
        checkpoint,
        minimum=B_R_MIN,
        deadline=arm_r_deadline(checkpoint, manifest),
    )
    agreement = [r["truth_agreement"] for r in results_r if r is not None]
    if not all(a["same_definedness"] and a["within_rtol"] for a in agreement):
        raise AssertionError("the paired arms disagree on the truth statistic")

    rng = _stream(BOOTSTRAP_ROOT_SEED, 2**20)
    n_dom = len(context.domain_ids)
    origin_counts = support_counts(truth)
    b2_counts = b2_support_counts()
    pairs_origin = anchor_forward_pairs(earnings, PSEUDO_ORIGIN)
    if pairs_origin != int(len(fitted_pairs)):
        raise AssertionError("the pair count differs from the fit's own")
    pairs_b2 = int(checks["anchor_forward_pairs_2010"])
    void = status_f["void"] or status_r["void"] or status_d["void"]
    per_cell = {}
    for name in CELLS:
        group, key = CELL_SUPPORT[name]
        factor = transport_factor(
            b2_counts[group][key],
            origin_counts[group][key],
            pairs_origin,
            pairs_b2,
        )
        per_cell[name] = cell_record(
            name,
            floor[name],
            [
                (
                    (None, None)
                    if r is None
                    else (r["gaps"][name], r["tdev"][name])
                )
                for r in results_f
            ],
            [
                (
                    None
                    if r["effect"][name] is None
                    or r["gap_fixed"][name] is None
                    or r["gap_refit"][name] is None
                    else {
                        **r["effect"][name],
                        "gap_fixed": r["gap_fixed"][name],
                        "gap_refit": r["gap_refit"][name],
                    }
                )
                for r in results_r
                if r is not None
            ],
            [None if r is None else r["gaps"][name] for r in results_d],
            factor,
            void,
            rng,
            mc_errors[name],
        )

    return {
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "protocol_v2_sha256": block,
        "repository_head": head,
        "worktree_clean": True,
        "script_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "runtime": runtime,
        "psid_dir": str(psid_dir),
        "psid_files_opened_sha256": dict(sorted(opened.items())),
        "nawi": nawi_record,
        "source_reproduction": checks,
        "forest_skip_check": skip_check,
        "geometry": {
            "pseudo_origin": PSEUDO_ORIGIN,
            "anchor_wave": ANCHOR_WAVE,
            "level_years": list(LEVEL_YEARS),
            "change_years": list(CHANGE_YEARS),
            "collection_waves": list(COLLECTION_WAVES),
        },
        "law": {
            "candidate_id": CANDIDATE_3.candidate_id,
            "candidate_spec_sha256": CANDIDATE_3.sha256,
            "fit_seed": FIT_SEED,
            "draw_seeds": list(DRAW_SEEDS),
        },
        "counts": {
            "fit_input_rows": int(len(fit_input)),
            "n_full_anchor": int(len(full_anchor)),
            "n_domain": n_dom,
            "anchor_forward_pairs": pairs_origin,
            "support": origin_counts,
            "design": design_summary(design),
            "n_anchor_clusters": int(
                clusters.loc[clusters.stratum == "anchor", "cluster"].nunique()
            ),
            "n_other_clusters": int(
                clusters.loc[clusters.stratum == "other", "cluster"].nunique()
            ),
        },
        "bootstrap": {
            "root_seed": BOOTSTRAP_ROOT_SEED,
            "b_f": B_F,
            "b_d": B_D,
            "refit_scheme": REFIT_SCHEME,
            "ucl_level": UCL_LEVEL,
            "arm_d": status_d,
            "b_r_max": B_R_MAX,
            "b_r_min": B_R_MIN,
            "arm_r_budget_seconds": ARM_R_BUDGET_SECONDS,
            "n_ci_resamples": N_CI_RESAMPLES,
            "ci_levels": list(CI_LEVELS),
            "arm_f": status_f,
            "arm_r": status_r,
            "e_is_lower_bound": bool(status_r["failed"] > 0),
            "paired_truth_agreement_rtol": TRUTH_AGREEMENT_RTOL,
            "paired_truth_agreement": True,
            "workers": {"arm_f": args.workers_f, "arm_r": args.workers_r},
        },
        "transport": {
            "support_2010": b2_counts,
            "anchor_forward_pairs_2010": pairs_b2,
            "rule": "max(1, (n_B2 / n_2006) * (P_2006 / P_2010)) per cell",
        },
        "design_rule": {
            "limit": DESIGN_RATIO_LIMIT,
            "household_resampling_stands": bool(
                all(
                    cell.get("design_ratio", {}).get("within_limit", False)
                    for cell in per_cell.values()
                    if cell.get("defined")
                )
            ),
        },
        "arm_f_gap_correlation": gap_correlation(results_f),
        "cells": per_cell,
        "outcome_blind": {
            "reference_years_after_2010_read": False,
            "b2_cell_or_floor_computed": False,
            "levels_or_gaps_recorded": False,
            "raw_scale_variances_recorded": False,
        },
        "wall_seconds": round(time.time() - started, 1),
    }


if __name__ == "__main__":
    raise SystemExit(main())
