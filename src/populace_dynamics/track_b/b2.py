"""Track B B2: the rules its floor builder, comparator and scorer share.

``docs/design/track_b_b0_1_addendum.md`` is the frozen record B2 registers
on. This module holds the parts of it that decide something, so that the
three scripts apply one copy of each rule:

- B2's geometry, seeds, streams and replicate counts (sections 4 and 7);
- the root-parameterised household and design multiplicities (section 13,
  "To B2"); the design copy implements section 7's merged-stratum rule,
  and neither copy reads protocol v2's root;
- the stratum census, simultaneous merges, integer-copy scale and design
  degrees of freedom (section 7);
- ``t_star``, the registered standard error and the bound rule (section 7);
- the Monte Carlo and undefined-replicate rules (section 7);
- validity and the pass conjunction, INVALID, then FAIL, then PASS, then
  INCONCLUSIVE (section 8);
- eligibility and the decompounding ladder inside B2's gate surface: the
  six level cells of d781 (a), rescoped by d1606 (option C1) to p90 and
  the zero rate by cohort (section 5);
- tolerances, their plain-unit statements and the exposure labels
  (sections 5 and 6);
- the unadjusted 95% interval of every report-only cell (section 5).

It reads no file. Every function is deterministic for fixed inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.stats import t as student_t

from populace_dynamics.harness import m6_cells
from populace_dynamics.harness.m6_cells import earnings_cells

# --------------------------------------------------------------------------
# Geometry (addendum section 4; audit sections 4.3 and 7)
# --------------------------------------------------------------------------
ORIGIN = 2010
ANCHOR_WAVE = ORIGIN + 1
LEVEL_YEARS = (ORIGIN + 2, ORIGIN + 4)
CHANGE_YEARS = (ORIGIN, ORIGIN + 2, ORIGIN + 4)
SCORED_PERIODS = CHANGE_YEARS
#: Income-reference years are collected at the next odd wave (audit 4.3).
COLLECTION_WAVE_OF = {year: year + 1 for year in SCORED_PERIODS}
AGE_CONVENTION = (
    "cohort and support use age at the collection wave (2011, 2013, 2015), "
    "not age in the income-reference year; prime is 25-44 and older 45-64"
)
REFERENCE_YEAR_MAPPING = (
    "income-reference years 2010, 2012 and 2014 are collected at the 2011, "
    "2013 and 2015 interviews; PSID has no 2012 or 2014 interview"
)

# --------------------------------------------------------------------------
# Law, seeds, streams and replicate counts (addendum section 7)
# --------------------------------------------------------------------------
FIT_SEED = 5200
DRAW_SEEDS = tuple(range(6200, 6220))
K = len(DRAW_SEEDS)
FLOOR_SEEDS = tuple(range(100))
GATE_SEEDS = (0, 1, 2, 3, 4)
SEEDS_REQUIRED = 4
#: B2's scoring-bootstrap root (section 7). Protocol v2's root, 20260930,
#: is never read here.
ROOT_SEED = 20261002
#: Stream words: [root, b, 0] household replicate b; [root, b, 4] design
#: replicate b.
HOUSEHOLD_WORD = 0
DESIGN_WORD = 4
B_HOUSEHOLD = 4000
B_DESIGN = 4000
#: Copies of one person are numbered 0..ID_SCALE-1 (``copy_persons``).
ID_SCALE = 1000
#: Household clusters carry ``anchor wave * CLUSTER_SCALE + interview``,
#: the planning script's ``cluster_table`` encoding.
CLUSTER_SCALE = 100_000
WAGE_VINTAGE = (
    "policyengine-us 1.752.2 NAWI realized through 2010, with the fitter's "
    "log-linear projection over 2001-2010 after it (element 1)"
)
#: Kept distinct from M6's ``ols_log_nawi_2005_2014`` (section 13).
WAGE_VINTAGE_LABEL = "pe_us_1_752_2_nawi_realized_2010_loglinear_2001_2010"

# --------------------------------------------------------------------------
# Rules (addendum sections 5-8)
# --------------------------------------------------------------------------
ALPHA = 0.05
POWER_TARGET = 0.90
MIN_GATED_CELLS = 4
TOLERANCE_K = 3
METRIC_CAP = dict(m6_cells.METRIC_CAP)
MIN_EVENTS = m6_cells.MIN_EVENTS_FOR_GATE
#: A gated cell with more than this share of its design or household
#: replicates undefined cannot pass.
MAX_UNDEFINED_SHARE = 0.01
#: The Monte Carlo error must be below tol / MONTE_CARLO_DIVISOR.
MONTE_CARLO_DIVISOR = 10

INVALID = "INVALID"
FAIL = "FAIL"
PASS = "PASS"
INCONCLUSIVE = "INCONCLUSIVE"
OUTCOMES = (INVALID, FAIL, PASS, INCONCLUSIVE)

LADDER_CLEARED = "LADDER_CLEARED"
WEAK_POWER_OR_VACUITY = "WEAK_POWER_OR_VACUITY"
FLOOR_OUTCOMES = (
    LADDER_CLEARED,
    WEAK_POWER_OR_VACUITY,
)

# --------------------------------------------------------------------------
# Cells (audit section 9.1; addendum section 5)
# --------------------------------------------------------------------------
#: M6's concept families (``scripts/build_m6_holdout_floors_v2.py:118``).
CONCEPT_FAMILY = {
    "earn_p10": "log_quantiles",
    "earn_p50": "log_quantiles",
    "earn_p90": "log_quantiles",
    "earn_dlog_sd": "dispersion",
    "earn_mob_h1_diag": "mobility",
    "earn_mob_h2_diag": "mobility",
    "earn_zero_rate": "zero_rate",
    "earn_autocorr_lag1": "autocorrelation",
    "earn_autocorr_lag2": "autocorrelation",
    "earn_dlog_mean": "change_mean",
}
#: The 16 gateable cells and their metrics (``m6_cells.earnings_cells``).
CELL_METRICS = dict(
    sorted(
        {
            **{
                f"earn_{tag}.{cohort}": "log_ratio"
                for tag in ("p10", "p50", "p90", "zero_rate", "dlog_sd")
                for cohort in ("prime", "older")
            },
            **{
                f"earn_dlog_mean.{cohort}": "abs_gap_log"
                for cohort in ("prime", "older")
            },
            "earn_mob_h1_diag": "log_ratio",
            "earn_mob_h2_diag": "log_ratio",
            "earn_autocorr_lag1": "abs_gap_corr",
            "earn_autocorr_lag2": "abs_gap_corr",
        }.items()
    )
)
CELLS = tuple(CELL_METRICS)
#: d781 (a): the six level cells, B2's ruled surface.
LEVEL_CELLS = (
    "earn_p50.older",
    "earn_p50.prime",
    "earn_p90.older",
    "earn_p90.prime",
    "earn_zero_rate.older",
    "earn_zero_rate.prime",
)
#: d1606, option C1 (2026-10-16): B2's gate surface. Its first floor
#: stopped the ladder inside the six (#42 comment 6200099988); priced on
#: that floor (#42 comment 6201696504), only the six less both medians
#: cleared at k = 3. The medians and the other ten cells are report-only.
GATE_SURFACE = (
    "earn_p90.older",
    "earn_p90.prime",
    "earn_zero_rate.older",
    "earn_zero_rate.prime",
)
#: M6 v3's retained six (``gates.yaml:5600-5606``), the selectors' cells.
M6_RETAINED = (
    "earn_autocorr_lag2",
    "earn_dlog_mean.prime",
    "earn_dlog_sd.older",
    "earn_mob_h1_diag",
    "earn_p10.prime",
    "earn_zero_rate.older",
)
EXPOSURE_PUBLISHED_OUTCOMES = (
    "published candidate-3-law outcomes at boundaries 2008 and 2010"
)
EXPOSURE_FLOOR_DETAIL = (
    "published five-seed floor detail, no published candidate outcome"
)

# --------------------------------------------------------------------------
# Statements B2's records carry (sections 4, 5, 6 and 13)
# --------------------------------------------------------------------------
HEADLINE_SCOPE = (
    "B2's gate covers p90 earnings and the zero-earnings rate, by cohort, "
    "only: not median earnings, changes, dispersion, mobility or "
    "persistence. H and B3L rely on B2 for those two level statistics only "
    "(d781 (a), d1606 option C1)."
)
FALLBACK_SCOPE = (
    "EXPOSURE_UNRESOLVED fires (Q8(b)): B2's registration is the registered "
    "fallback at design section 3.2's scope, '2010→2014 continuity on "
    "the stated surface, ages 25–64. Not a 2010-vintage forecast' "
    "(design line 150). H and B3L may rely on B2 only within that scope. "
    "Removing this statement after any candidate run requires a dated "
    "amendment."
)
SECTION_5_3_SENTENCE = (
    "No Track B gate holds ages 25-61 earnings to a fixed limit (Q4)."
)
PLANNING_CAVEAT = (
    "The planning values come from a window whose truth years, 2008 and "
    "2010, fall in a recession; neither their transport to 2012 and 2014 "
    "nor r's is tested."
)
B1_LABEL = "reconstructed reproduction (weaker than bit-for-bit)"
B1_EVIDENCE = (
    "B1 v2 returned RECONSTRUCTED_REPRODUCTION: issue #42 comments "
    "6110674288 (registration) and 6113379406 (result) (d622)"
)
CANDIDATE_3_DISCLOSURE = (
    "**Candidate 3 records a valid M6 pass; it certifies nothing about "
    "mortality drift.** The artifact records four passing seeds, q=0.55 "
    "and rho=−0.6. Fits use data through 2014; gated demographic flows "
    "cover 2015–2019 and earnings cover 2016/2018. The 2020–2022 window "
    "is diagnostic only. Certification is conditional on prior structural "
    "and same-holdout surface selection. The v4 point estimate "
    "`p_gate=0.9018301` clears 0.90 by 0.0018301, but its clearance is not "
    "statistically resolved: the reported jackknife SE is approximately "
    "0.013–0.019. Synthesized support, redrawn initial states and endogenous "
    "widowhood require the decision-5 successor gate."
)
CODEBOOK_CONCEPT_CHECK = (
    "audit section 4.2: definitions only; all six labor-income variables "
    "exclude farm and unincorporated business income, and market "
    "gardening is absent from the 2015 component lists"
)


def concept(cell: str) -> str:
    """A cell's M6 concept family."""
    return CONCEPT_FAMILY[cell.split(".")[0]]


def exposure_label(cell: str) -> str:
    """Section 5's exposure label for a cell."""
    if cell not in CELL_METRICS:
        raise KeyError(f"{cell!r} is not one of the 16 gateable cells")
    if cell in M6_RETAINED:
        return EXPOSURE_PUBLISHED_OUTCOMES
    return EXPOSURE_FLOOR_DETAIL


# --------------------------------------------------------------------------
# Canonical hashing (the selectors' ``_plain`` and ``_canonical_sha256``)
# --------------------------------------------------------------------------
def plain(value: Any) -> Any:
    """JSON-ready copy: numpy scalars to Python, non-finite floats to None.

    A copy of ``select_m6_qstar_train_only._plain``, so the floor builder
    and the comparator hash exactly what the selectors' ledgers hold.
    """
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return [plain(item) for item in value.tolist()]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is pd.NA:
        return None
    return value


def canonical_sha256(value: Any) -> str:
    """The selectors' canonical SHA-256: sorted keys, no spaces, no NaN."""
    encoded = json.dumps(
        plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def id_sha256(values: Any) -> str:
    """The selectors' ``_id_checksum``: sorted unique integers, one a line."""
    ordered = sorted(int(value) for value in set(values))
    raw = "".join(f"{value}\n" for value in ordered).encode()
    return hashlib.sha256(raw).hexdigest()


def six_cell_floor_block(floor: Mapping[str, Any]) -> dict[str, Any]:
    """The person-split floor block for the six M6-retained cells, as the
    selectors' ``_boundary_context`` keeps it."""
    return {name: floor[name] for name in M6_RETAINED}


def six_cell_seed_detail(
    detail: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The seed 0-4 floor detail restricted to the six M6-retained cells."""
    return [
        {
            "seed": record["seed"],
            "cells": {name: record["cells"][name] for name in M6_RETAINED},
        }
        for record in detail
    ]


# --------------------------------------------------------------------------
# Cells on B2's geometry
# --------------------------------------------------------------------------
def cell_value(record: Mapping[str, Any]) -> float | None:
    """A cell's value when its metric defines it, else None.

    A copy of ``select_m6_qstar_train_only._selection_cell_value``: a
    non-finite value is undefined, and so is a non-positive value of a
    log-ratio cell.
    """
    raw = record.get("rate", record.get("value"))
    if raw is None:
        return None
    value = float(raw)
    if not math.isfinite(value):
        return None
    metric = str(record.get("metric", "log_ratio"))
    if (metric == "log_ratio" or "rate" in record) and value <= 0:
        return None
    return value


def cell_values(
    frame: pd.DataFrame,
    *,
    level_years: tuple[int, ...] = LEVEL_YEARS,
    change_years: tuple[int, ...] = CHANGE_YEARS,
) -> dict[str, float | None]:
    """Each gateable cell's value on one frame (None when undefined), by
    the unchanged M6 reducer."""
    reduced = earnings_cells(
        frame, level_years=level_years, change_years=change_years
    )
    out: dict[str, float | None] = {}
    for name, metric in CELL_METRICS.items():
        record = reduced[name]
        if str(record["metric"]) != metric:
            raise AssertionError(f"{name}'s metric is not {metric}")
        out[name] = cell_value(record)
    return out


# --------------------------------------------------------------------------
# The 2011 anchor, the domain and the truth support (audit section 7)
# --------------------------------------------------------------------------
def cohort(age: object) -> str | None:
    """The M6 earnings cohort of a collection-wave age, or None."""
    if pd.isna(age):
        return None
    value = int(age)
    for name, lower, upper in m6_cells.EARN_COHORTS:
        if lower <= value <= upper:
            return name
    return None


def full_anchor_frame(
    anchor_demo: pd.DataFrame, anchor_wave: int = ANCHOR_WAVE
) -> pd.DataFrame:
    """The full anchor: the positive-weight roster at the anchor wave.

    ``anchor_demo`` is the selectors' anchor roster (present persons,
    positive weight). The household is the anchor wave's interview number
    and the fixed weight that wave's weight, as in the selectors'
    ``_boundary_context`` (``select_m6_qstar_train_only.py:1416-1428``).
    """
    full = anchor_demo.loc[
        anchor_demo["period"] == anchor_wave,
        ["person_id", "interview", "weight"],
    ].copy()
    full = full.rename(columns={"interview": "household_id"})
    full = full.sort_values("person_id", kind="stable").reset_index(drop=True)
    if full.empty or full["person_id"].duplicated().any():
        raise ValueError(f"the {anchor_wave} full anchor is empty or repeated")
    if (pd.to_numeric(full["weight"], errors="coerce") <= 0).any():
        raise ValueError(f"the {anchor_wave} full anchor has a weight <= 0")
    return full


def domain_person_ids(
    earnings: pd.DataFrame,
    full_anchor: pd.DataFrame,
    origin: int = ORIGIN,
) -> frozenset[int]:
    """The domain from data alone: full-anchor persons with a valid origin
    row (section 9, step 2)."""
    with_row = set(
        earnings.loc[earnings["period"] == origin, "person_id"].astype(int)
    )
    return frozenset(
        int(person)
        for person in set(full_anchor["person_id"].astype(int)) & with_row
    )


def truth_support(
    earnings: pd.DataFrame,
    full_anchor: pd.DataFrame,
    domain_ids: frozenset[int],
    periods: tuple[int, ...] = SCORED_PERIODS,
) -> pd.DataFrame:
    """The domain's earnings rows at the scored periods with a cohort.

    Each row carries the person's fixed anchor weight (its own weight kept
    as ``raw_row_weight``) and the cohort of its collection-wave age, as in
    the selectors' ``_boundary_context`` and the planning script's
    ``build_context``.
    """
    fixed_weight = full_anchor.set_index("person_id")["weight"]
    truth = earnings.loc[
        earnings["period"].isin(periods)
        & earnings["person_id"].isin(domain_ids)
    ].copy()
    truth["raw_row_weight"] = truth["weight"].astype("float64")
    truth["weight"] = truth["person_id"].map(fixed_weight).astype("float64")
    truth["cohort"] = truth["age"].map(cohort)
    truth = truth[truth["cohort"].notna()].copy()
    truth = truth.sort_values(["person_id", "period"], kind="stable")
    truth = truth.reset_index(drop=True)
    if truth.duplicated(["person_id", "period"]).any():
        raise ValueError("truth support has duplicate person-period rows")
    return truth


def split_floor(
    full_anchor: pd.DataFrame,
    truth: pd.DataFrame,
    split_column: str,
    *,
    level_years: tuple[int, ...] = LEVEL_YEARS,
    change_years: tuple[int, ...] = CHANGE_YEARS,
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
    """``run_floor`` on the full anchor split by ``split_column``, truth only.

    Each seed splits the full anchor first and then intersects each half
    with the truth support (section 4). Returns every cell's floor and the
    gate seeds' (0-4) detail.
    """

    def compute(person_ids: set[object]) -> dict[str, Any]:
        selected = set(int(value) for value in person_ids)
        return earnings_cells(
            truth[truth["person_id"].isin(selected)],
            level_years=level_years,
            change_years=change_years,
        )

    return m6_cells.run_floor(full_anchor, compute, split_column)


# --------------------------------------------------------------------------
# Root-parameterised multiplicities (section 13, "To B2")
# --------------------------------------------------------------------------
def stream(root: int, *words: int) -> np.random.Generator:
    """The generator for SeedSequence words [root, *words]."""
    return np.random.default_rng(
        np.random.SeedSequence([int(root), *(int(word) for word in words)])
    )


def household_clusters(
    full_anchor: pd.DataFrame, anchor_wave: int = ANCHOR_WAVE
) -> pd.DataFrame:
    """Every full-anchor person's household cluster, in one stratum.

    The cluster is ``anchor_wave * CLUSTER_SCALE + household_id``, the
    planning script's ``cluster_table`` encoding for anchor households.
    Households without a domain person are included (section 7).
    """
    household = full_anchor["household_id"].astype("int64")
    clusters = pd.DataFrame(
        {
            "person_id": full_anchor["person_id"].astype("int64"),
            "cluster": int(anchor_wave) * CLUSTER_SCALE + household,
            "stratum": "anchor",
        }
    )
    if clusters["person_id"].duplicated().any():
        raise ValueError("the full anchor repeats a person")
    return clusters.sort_values("person_id", kind="stable").reset_index(
        drop=True
    )


def stratum_multiplicities(
    clusters: pd.DataFrame,
    stratum: str,
    replicate: int,
    word: int,
    *,
    root: int,
) -> dict[int, int]:
    """Multinomial cluster multiplicities for one stratum and replicate:
    equal probabilities, as many draws as clusters."""
    ids = np.sort(
        clusters.loc[clusters["stratum"] == stratum, "cluster"]
        .astype("int64")
        .unique()
    )
    if not len(ids):
        return {}
    counts = stream(root, int(replicate), word).multinomial(
        len(ids), np.full(len(ids), 1.0 / len(ids))
    )
    return {
        int(cluster): int(count)
        for cluster, count in zip(ids, counts, strict=True)
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
            strict=True,
        )
    }


def anchor_multiplicities(
    clusters: pd.DataFrame, replicate: int, *, root: int
) -> dict[int, int]:
    """Household replicate b's person multiplicities, stream [root, b, 0].

    The planning script's ``anchor_multiplicities`` with the root passed
    explicitly.
    """
    return person_multiplicities(
        clusters,
        stratum_multiplicities(
            clusters, "anchor", replicate, HOUSEHOLD_WORD, root=root
        ),
    )


def copy_scale(max_count: int) -> int:
    """The identifier scale for copies: ``ID_SCALE`` while every count is
    below it, else the smallest power of ten above the largest count."""
    if max_count < ID_SCALE:
        return ID_SCALE
    return 10 ** len(str(int(max_count)))


def copy_persons(
    frame: pd.DataFrame,
    multiplicity: Mapping[int, int],
    pinned: Callable[[pd.DataFrame, Mapping[int, int]], pd.DataFrame],
) -> pd.DataFrame:
    """Copy each person's rows c times, as the addendum's ``copy_persons``.

    ``pinned`` is the planning script's ``copy_persons`` (section 13, "To
    B2"), which numbers copies ``person * ID_SCALE + k`` and refuses a
    count of ``ID_SCALE`` or more. Below that it is called unchanged, so
    frames equal arm F's. Section 7's stratum rule can need more copies at
    scale L, so above it the same construction runs with a wider scale
    (``copy_scale``). Only the identifiers' encoding differs; rows, order
    and every other column are the same.
    """
    counts = (
        frame["person_id"]
        .astype("int64")
        .map(lambda person: multiplicity.get(int(person), 0))
        .to_numpy(dtype=np.int64)
    )
    largest = int(counts.max()) if counts.size else 0
    if largest < ID_SCALE:
        return pinned(frame, multiplicity)
    scale = copy_scale(largest)
    top = int(frame["person_id"].astype("int64").max())
    if (top + 1) * scale >= np.iinfo(np.int64).max:
        raise OverflowError("copied identifiers would overflow int64")
    repeated = frame.loc[frame.index.repeat(counts)].copy()
    copy = repeated.groupby(level=0).cumcount().to_numpy(dtype=np.int64)
    repeated["person_id"] = (
        repeated["person_id"].astype("int64") * scale + copy
    )
    return repeated.sort_values(
        ["person_id", "period"] if "period" in repeated else ["person_id"],
        kind="stable",
    ).reset_index(drop=True)


def design_multiplicities(
    design: pd.DataFrame, replicate: int, *, root: int
) -> dict[int, int]:
    """Design replicate b's Rao-Wu multiplicities, stream [root, b, 4].

    Singleton strata merge simultaneously before drawing. At scale L,
    two-cluster strata preserve arm D's random call and copy the selected
    cluster 2L times. Larger strata draw n - 1 clusters with replacement
    by multinomial and copy each draw L*n/(n - 1) times. Strata and their
    original (stratum, cluster) identities are visited in sorted order.
    """
    design, _ = merge_design_strata(design)
    sizes = design.groupby("stratum")["cluster"].nunique()
    if int((sizes - 1).sum()) == 0:
        raise ValueError("the merged design has no degree of freedom")
    scale = math.lcm(*(int(n) - 1 for n in sizes))
    rng = stream(root, int(replicate), DESIGN_WORD)
    by_secu: dict[tuple[int, int], int] = {}
    for stratum, group in design.groupby("stratum", sort=True):
        clusters = np.sort(group["cluster"].unique())
        n = len(clusters)
        if n == 2:
            counts = np.zeros(2, dtype=int)
            counts[rng.integers(0, 2)] = 2 * scale
        else:
            counts = rng.multinomial(n - 1, np.full(n, 1.0 / n))
            counts *= scale * n // (n - 1)
        for cluster, count in zip(clusters, counts, strict=True):
            by_secu[(int(stratum), int(cluster))] = int(count)
    return {
        int(person): by_secu[(int(stratum), int(cluster))]
        for person, stratum, cluster in zip(
            design["person_id"],
            design["stratum"],
            design["cluster"],
            strict=True,
        )
    }


# --------------------------------------------------------------------------
# Stratum census, simultaneous merges and degrees of freedom (section 7)
# --------------------------------------------------------------------------
def _validated_design(design: pd.DataFrame) -> pd.DataFrame:
    """A nonempty design with unique persons and integer design codes."""
    if design.empty:
        raise ValueError("the design table is empty")
    required = ("person_id", "stratum", "cluster")
    missing = [name for name in required if name not in design]
    if missing:
        raise ValueError(f"the design table lacks {', '.join(missing)}")
    validated = design.copy()
    for name in required:
        try:
            values = pd.to_numeric(design[name], errors="raise")
            if (
                values.isna().any()
                or not np.isfinite(values).all()
                or not (values == np.floor(values)).all()
            ):
                raise ValueError
            validated[name] = values.astype("int64")
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"the design table's {name} must contain finite integers"
            ) from error
    if validated["person_id"].duplicated().any():
        raise ValueError("the design table repeats a person")
    return validated


def stratum_census(design: pd.DataFrame) -> dict[str, Any]:
    """The design strata among the truth-support persons, by cluster count.

    The first five keys are the planning script's ``design_summary``. The
    record adds the histogram of strata by cluster count, the cluster
    count, and the design degrees of freedom nu = sum over strata of
    (clusters - 1), so a stratum with one cluster adds nothing.
    """
    design = _validated_design(design)
    sizes = design.groupby("stratum")["cluster"].nunique()
    histogram = sizes.value_counts().sort_index()
    return {
        "strata": int(len(sizes)),
        "strata_with_one_cluster": int((sizes == 1).sum()),
        "strata_with_two_clusters": int((sizes == 2).sum()),
        "strata_with_three_or_more_clusters": int((sizes >= 3).sum()),
        "persons": int(len(design)),
        "clusters": int(sizes.sum()),
        "strata_by_cluster_count": {
            str(int(n)): int(count) for n, count in histogram.items()
        },
        "design_degrees_of_freedom": int((sizes - 1).sum()),
    }


def merge_design_strata(
    design: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, int]]]:
    """Apply section 7's simultaneous singleton-stratum merges.

    Targets are chosen only among strata with at least two clusters in
    the original design. Distance is by stratum code, lower code on a
    tie. If every original stratum is a singleton, the lowest code is
    the sole merged stratum. Cluster codes may repeat between original
    strata: their original pairs remain distinct after a merge, by a
    deterministic integer recoding within each affected target stratum.
    """
    merged = _validated_design(design)
    sizes = merged.groupby("stratum")["cluster"].nunique()
    targets = sorted(int(code) for code in sizes.index[sizes >= 2])
    if not targets:
        targets = [int(sizes.index.min())]
    destinations = {
        int(code): min(
            targets, key=lambda target: (abs(target - code), target)
        )
        for code in sizes.index[sizes == 1]
    }
    destinations = {
        source: target
        for source, target in destinations.items()
        if source != target
    }
    merges = [
        {"from_stratum": source, "to_stratum": target}
        for source, target in sorted(destinations.items())
    ]
    if not merges:
        return merged, merges
    original = merged[["stratum", "cluster"]].copy()
    merged["stratum"] = merged["stratum"].map(
        lambda code: destinations.get(int(code), int(code))
    )
    for target in sorted(set(destinations.values())):
        selected = merged["stratum"] == target
        identities = sorted(
            set(
                zip(
                    original.loc[selected, "stratum"],
                    original.loc[selected, "cluster"],
                    strict=True,
                )
            )
        )
        by_identity = {
            identity: index for index, identity in enumerate(identities)
        }
        merged.loc[selected, "cluster"] = [
            by_identity[(stratum, cluster)]
            for stratum, cluster in zip(
                original.loc[selected, "stratum"],
                original.loc[selected, "cluster"],
                strict=True,
            )
        ]
    return merged, merges


def design_summary(design: pd.DataFrame) -> dict[str, Any]:
    """The frozen floor record: original census, merges, merged census, L, ν."""
    before = stratum_census(design)
    merged, merges = merge_design_strata(design)
    after = stratum_census(merged)
    sizes = merged.groupby("stratum")["cluster"].nunique()
    return {
        "before_merges": before,
        "merges": merges,
        "after_merges": after,
        "scale_l": math.lcm(*(int(n) - 1 for n in sizes)),
        "design_degrees_of_freedom": after["design_degrees_of_freedom"],
    }


def t_star(m: int, nu: float | None) -> float:
    """t*_{m,nu}: the two-sided simultaneous 95% value over m cells.

    Student t with ``nu`` degrees of freedom at 1 - 0.05 / (2 m); ``None``
    or infinity gives the normal z*_m.
    """
    if int(m) != m or m < 1:
        raise ValueError("a gate needs at least one cell")
    level = 1.0 - ALPHA / (2.0 * m)
    if nu is None or math.isinf(nu):
        return float(norm.ppf(level))
    if not nu > 0:
        raise ValueError("degrees of freedom must be positive")
    return float(student_t.ppf(level, nu))


# --------------------------------------------------------------------------
# Standard errors, the bound rule and the Monte Carlo rule (section 7)
# --------------------------------------------------------------------------
def registered_estimation_ratio(planning_cell: Mapping[str, Any]) -> float:
    """a_c: the cell's registered estimation-variance ratio.

    e_B2 from the planning record, plus the transported cross term f x c
    where protocol v2's rule adds it (its 5th percentile above zero).
    """
    if not planning_cell.get("defined"):
        raise ValueError("the cell has no planning values")
    estimation = planning_cell["estimation_variance"]
    value = float(estimation["e_b2"])
    if planning_cell["gap_variance"]["cross_term_resolved_positive"]:
        value += float(estimation["transport_factor"]) * float(
            planning_cell["diagnostics"]["cross_term"]
        )
    if not (math.isfinite(value) and value >= 0):
        raise ValueError("a registered estimation ratio must be >= 0")
    return value


def defined_sd(values: Sequence[float | None]) -> tuple[float | None, int]:
    """The sample SD (ddof 1) of the defined values, and how many are
    undefined. The SD is None with fewer than two defined values."""
    defined = np.asarray(
        [v for v in values if v is not None and math.isfinite(v)],
        dtype=np.float64,
    )
    undefined = len(values) - len(defined)
    if len(defined) < 2:
        return None, undefined
    return float(np.std(defined, ddof=1)), undefined


def se_upper(truth_deviations: Sequence[float | None]) -> dict[str, Any]:
    """se_up: SD of the truth deviation over the household replicates
    times sqrt(1 + 1/K) (section 7). None when fewer than two are defined
    or the SD is zero."""
    sd, undefined = defined_sd(truth_deviations)
    value = None if sd is None or sd <= 0 else sd * math.sqrt(1.0 + 1.0 / K)
    return {
        "se_up": value,
        "replicates": len(truth_deviations),
        "undefined": undefined,
        "undefined_share_ok": undefined_share_ok(
            undefined, len(truth_deviations)
        ),
    }


def registered_se(
    se_boot: float | None, a_c: float, se_up: float | None
) -> float | None:
    """se_c = sqrt(se_boot**2 + a_c * se_up**2); None if either SE is."""
    if a_c < 0 or not math.isfinite(a_c):
        raise ValueError("a_c must be a finite non-negative constant")
    if se_boot is None or se_up is None:
        return None
    if not (math.isfinite(se_boot) and math.isfinite(se_up)):
        return None
    # hypot neither underflows nor overflows, so se_c >= se_boot exactly.
    return math.hypot(se_boot, math.sqrt(a_c) * se_up)


def bound_value(
    gap: float | None, se: float | None, critical: float
) -> float | None:
    """|g| + t* x se, the simultaneous bound; None if g or se is."""
    if gap is None or se is None:
        return None
    if not (math.isfinite(gap) and math.isfinite(se)):
        return None
    return abs(gap) + critical * se


def bound_passes(
    gap: float | None, se: float | None, tolerance: float, critical: float
) -> bool:
    """The bound rule: |g| + t* se <= tol."""
    value = bound_value(gap, se, critical)
    return value is not None and value <= tolerance


def monte_carlo_passes(mc_error: float | None, tolerance: float) -> bool:
    """The Monte Carlo rule: the error must be below tol / 10."""
    return (
        mc_error is not None
        and math.isfinite(mc_error)
        and mc_error < tolerance / MONTE_CARLO_DIVISOR
    )


def undefined_share_ok(undefined: int, total: int) -> bool:
    """At most 1% of the replicates undefined."""
    return total > 0 and undefined <= MAX_UNDEFINED_SHARE * total


def report_interval(
    gap: float | None, se: float | None, nu: float | None
) -> list[float] | None:
    """A report-only cell's unadjusted 95% interval, g -/+ t*_{1,nu} se."""
    if gap is None or se is None:
        return None
    critical = t_star(1, nu)
    return [gap - critical * se, gap + critical * se]


# --------------------------------------------------------------------------
# Validity and the pass conjunction (section 8)
# --------------------------------------------------------------------------
def frame_valid(truth: float | None, draws: Sequence[float | None]) -> bool:
    """M6's validity on one frame (``m6_scoring.py:713-733``).

    Valid when the truth is defined, none of the K draws is undefined, and
    the draws are not all identical. M6 refuses an undefined truth and
    marks every draw undefined when a log-ratio truth is not positive;
    here both make the cell invalid.
    """
    if truth is None or not math.isfinite(truth):
        return False
    if not draws or any(value is None for value in draws):
        return False
    if any(not math.isfinite(value) for value in draws):
        return False
    return any(value != draws[0] for value in draws)


def within(gap: float | None, tolerance: float) -> bool:
    """|g| <= tol, false when g is undefined."""
    return gap is not None and math.isfinite(gap) and abs(gap) <= tolerance


@dataclass(frozen=True)
class GatedCell:
    """Everything section 8 needs about one gated cell."""

    name: str
    tolerance: float
    full_valid: bool
    full_gap: float | None
    side_a_valid: tuple[bool, ...]
    side_a_gap: tuple[float | None, ...]
    se: float | None
    mc_error: float | None
    design_undefined: int
    design_replicates: int
    household_undefined: int
    household_replicates: int


def cell_bound_record(cell: GatedCell, critical: float) -> dict[str, Any]:
    """One gated cell's conditions for PASS (section 8, item 3)."""
    bound = bound_value(cell.full_gap, cell.se, critical)
    record = {
        "bound": bound,
        "bound_within_tolerance": bound is not None
        and bound <= cell.tolerance,
        "se_defined": cell.se is not None,
        "mc_error_defined": cell.mc_error is not None,
        "monte_carlo_rule": monte_carlo_passes(cell.mc_error, cell.tolerance),
        "design_undefined_share_ok": undefined_share_ok(
            cell.design_undefined, cell.design_replicates
        ),
        "household_undefined_share_ok": undefined_share_ok(
            cell.household_undefined, cell.household_replicates
        ),
    }
    record["passes"] = all(
        bool(record[key])
        for key in (
            "bound_within_tolerance",
            "se_defined",
            "mc_error_defined",
            "monte_carlo_rule",
            "design_undefined_share_ok",
            "household_undefined_share_ok",
        )
    )
    return record


def gate_outcome(
    cells: Sequence[GatedCell], critical: float
) -> dict[str, Any]:
    """Section 8's outcome: the first of INVALID, FAIL, PASS, INCONCLUSIVE.

    1. INVALID if any gated cell is not valid on full support or on any of
       the five gate seeds' side A.
    2. FAIL if fewer than four of the five seeds pass (a seed passes when
       every gated cell's side-A gap is within tolerance), or some gated
       cell's full-support gap is outside tolerance.
    3. PASS if every gated cell's bound lies within tolerance, its se and
       Monte Carlo error are defined, the Monte Carlo rule holds, and at
       most 1% of its design and household replicates are undefined.
    4. INCONCLUSIVE otherwise.
    """
    if not cells:
        raise ValueError("a gate needs at least one cell")
    names = [cell.name for cell in cells]
    if len(set(names)) != len(names):
        raise ValueError("a gated cell is repeated")
    for cell in cells:
        if not (
            len(cell.side_a_valid) == len(GATE_SEEDS)
            and len(cell.side_a_gap) == len(GATE_SEEDS)
        ):
            raise ValueError(f"{cell.name} needs one side A per gate seed")
        if not (math.isfinite(cell.tolerance) and cell.tolerance > 0):
            raise ValueError(f"{cell.name} has no positive tolerance")
        # A frame valid by M6's rule always has a defined gap.
        if cell.full_valid and cell.full_gap is None:
            raise ValueError(f"{cell.name} is valid but has no gap")
        if any(
            valid and gap is None
            for valid, gap in zip(
                cell.side_a_valid, cell.side_a_gap, strict=True
            )
        ):
            raise ValueError(f"{cell.name} has a valid side A with no gap")
    invalid = sorted(
        cell.name
        for cell in cells
        if not cell.full_valid or not all(cell.side_a_valid)
    )
    seeds = [
        all(within(cell.side_a_gap[index], cell.tolerance) for cell in cells)
        for index in range(len(GATE_SEEDS))
    ]
    outside = sorted(
        cell.name
        for cell in cells
        if cell.full_valid and not within(cell.full_gap, cell.tolerance)
    )
    per_cell = {cell.name: cell_bound_record(cell, critical) for cell in cells}
    if invalid:
        outcome = INVALID
    elif sum(seeds) < SEEDS_REQUIRED or outside:
        outcome = FAIL
    elif all(record["passes"] for record in per_cell.values()):
        outcome = PASS
    else:
        outcome = INCONCLUSIVE
    return {
        "outcome": outcome,
        "critical_value": critical,
        "invalid_cells": invalid,
        "seed_passes": dict(
            zip((str(seed) for seed in GATE_SEEDS), seeds, strict=True)
        ),
        "n_seeds_passed": int(sum(seeds)),
        "cells_outside_tolerance": outside,
        "per_cell": per_cell,
    }


# --------------------------------------------------------------------------
# Tolerances, eligibility and the ladder (sections 5 and 6)
# --------------------------------------------------------------------------
def tolerance(mean: float, sd: float, metric: str) -> dict[str, Any]:
    """tol = min(round(mean + 3 SD, 3), cap) (``m6_cells._tol``)."""
    cap = METRIC_CAP[metric]
    uncapped = m6_cells._tol(mean, sd, TOLERANCE_K)
    value = min(uncapped, cap)
    return {
        "tolerance": value,
        "uncapped": uncapped,
        "cap": cap,
        "at_cap": bool(abs(value - cap) <= 1e-9),
        "metric": metric,
        "plain_units": plain_units(metric, value),
    }


def _number(value: float) -> str:
    return format(float(value), ".6g")


def plain_units(metric: str, value: float) -> str:
    """A tolerance in plain units (section 6)."""
    if metric == "log_ratio":
        factor = math.exp(value)
        return (
            f"within a factor of e^{_number(value)} = {factor:.4f}, that is "
            f"within {100.0 * (factor - 1.0):.1f}% above or "
            f"{100.0 * (1.0 - 1.0 / factor):.1f}% below"
        )
    if metric == "abs_gap_log":
        return f"mean two-year log change within ±{_number(value)}"
    if metric == "abs_gap_corr":
        return f"correlation within ±{_number(value)}"
    raise ValueError(f"unknown metric {metric!r}")


def floor_eligible(
    record: Mapping[str, Any], n_seeds: int = len(FLOOR_SEEDS)
) -> bool:
    """Section 5's floor condition, exactly: every seed defined and at least
    20 events in the weaker half on every seed (``m6_cells.py:56``).

    Unlike the planning script's ``floor_eligible``, it does not require a
    positive sigma. A zero or undefined sigma on an eligible cell is an
    uninformative tolerance, which stops B2 at floor build (the design's
    trigger for ``WEAK_POWER_OR_VACUITY``); it does not drop the cell.
    """
    return (
        int(record["n_defined_seeds"]) == n_seeds
        and int(record["min_events_weaker_half"]) >= MIN_EVENTS
    )


@dataclass(frozen=True)
class LadderCell:
    """A cell eligible to gate, with what the ladder orders and guards."""

    name: str
    tolerance: float
    sigma: float
    at_cap: bool = False

    @property
    def ratio(self) -> float:
        return self.tolerance / self.sigma


def ladder(
    cells: Sequence[LadderCell],
    power: Callable[[tuple[str, ...]], float],
    *,
    target: float = POWER_TARGET,
    min_cells: int = MIN_GATED_CELLS,
) -> dict[str, Any]:
    """Section 5's decompounding ladder, run inside B2's gate surface.

    1. Order the eligible cells by descending tolerance/sigma, ties by
       name.
    2. Compute the gate-level power of the cells still gated, with
       Bonferroni m equal to their number (``power`` is called with the
       sorted names of the cells still gated).
    3. Stop if the power is at least ``target``.
    4. Otherwise take the next cell in the order: keep it if it is the last
       of its concept family, else prune it and return to step 2.

    The guards: at least ``min_cells`` gated cells, and not every gated
    tolerance at its cap. The ladder clears only if it ends at or above
    ``target`` with both guards holding; otherwise B2 is
    WEAK_POWER_OR_VACUITY at floor build.
    """
    names = [cell.name for cell in cells]
    if len(set(names)) != len(names):
        raise ValueError("a ladder cell is repeated")
    for cell in cells:
        if not (cell.sigma > 0 and cell.tolerance > 0):
            raise ValueError(f"{cell.name} needs a positive tolerance/sigma")
    order = sorted(cells, key=lambda cell: (-cell.ratio, cell.name))
    retained = sorted(names)
    log: list[dict[str, Any]] = []
    value = float(power(tuple(retained))) if retained else 0.0
    initial = value
    for cell in order:
        if value >= target:
            break
        family = concept(cell.name)
        if sum(concept(name) == family for name in retained) <= 1:
            log.append(
                {
                    "cell": cell.name,
                    "tol_over_sigma": cell.ratio,
                    "action": "kept_last_in_concept",
                    "concept": family,
                }
            )
            continue
        retained.remove(cell.name)
        value = float(power(tuple(retained)))
        log.append(
            {
                "cell": cell.name,
                "tol_over_sigma": cell.ratio,
                "action": "pruned",
                "concept": family,
                "p_gate_after": value,
            }
        )
    by_name = {cell.name: cell for cell in cells}
    four_cells = len(retained) >= min_cells
    not_all_capped = not retained or not all(
        by_name[name].at_cap for name in retained
    )
    clears = bool(value >= target and four_cells and not_all_capped)
    return {
        "order": [cell.name for cell in order],
        "tol_over_sigma": {cell.name: cell.ratio for cell in order},
        "p_gate_before_pruning": initial,
        "log": log,
        "retained": list(retained),
        "pruned": sorted(set(names) - set(retained)),
        "p_gate": value,
        "power_target": target,
        "guards": {
            "at_least_four_cells": bool(four_cells),
            "not_every_tolerance_at_cap": bool(not_all_capped),
        },
        "clears": clears,
        "outcome": LADDER_CLEARED if clears else WEAK_POWER_OR_VACUITY,
    }


# --------------------------------------------------------------------------
# Replicate driver, PSID read guard and repository checks (shared plumbing)
# --------------------------------------------------------------------------
_WORKER: dict[str, Any] = {}


def _worker_init(payload: dict[str, Any]) -> None:
    _WORKER.clear()
    _WORKER.update(payload)


def worker_payload() -> dict[str, Any]:
    """The payload a replicate function reads inside a worker process."""
    return _WORKER


def _guarded_call(
    function: Callable[[int], dict[str, Any]], replicate: int
) -> dict[str, Any]:
    try:
        return function(replicate)
    except (MemoryError, OSError):
        raise
    except Exception as error:  # noqa: BLE001 (recorded as undefined)
        return {
            "replicate": int(replicate),
            "failed": True,
            "exception_class": type(error).__name__,
        }


def run_replicates(
    function: Callable[[int], dict[str, Any]],
    count: int,
    payload: dict[str, Any],
    workers: int,
) -> list[dict[str, Any]]:
    """Run replicates 0..count-1 and return them in index order.

    ``function`` reads its inputs from ``worker_payload()``. A replicate
    that raises is returned as ``{"failed": True, "exception_class": ...}``
    and its cells count as undefined; a memory or operating-system error
    stops the run. With one worker the replicates run in this process.
    """
    import concurrent.futures as futures

    if workers <= 1:
        _worker_init(payload)
        try:
            return [_guarded_call(function, index) for index in range(count)]
        finally:
            _WORKER.clear()
    results: dict[int, dict[str, Any]] = {}
    with futures.ProcessPoolExecutor(
        max_workers=workers, initializer=_worker_init, initargs=(payload,)
    ) as pool:
        submitted = {
            pool.submit(_guarded_call, function, index): index
            for index in range(count)
        }
        done = 0
        for future in futures.as_completed(submitted):
            results[submitted[future]] = future.result()
            done += 1
            if done % max(1, count // 20) == 0:
                progress(f"{done}/{count} replicates done")
    return [results[index] for index in range(count)]


#: The open attempt log, if any (``open_attempt``).
_ATTEMPT: dict[str, Path | None] = {"path": None}


def open_attempt(path: Path, header: Mapping[str, Any]) -> None:
    """Create the one-shot attempt log; refuse if it exists.

    The scorer opens it after every check that needs no PSID data (the
    floor, the planning record, the scoring inputs and NAWI) and before it
    reads any. The
    header records the run's identity; every later ``progress`` stage is
    appended with its UTC time and synced to disk. So a run that ends
    without its output leaves a durable record of the last stage it
    reached, and whether any candidate gap had been computed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {"utc": _utc_now(), "attempt": plain(dict(header))}, sort_keys=True
    )
    with path.open("x", encoding="utf-8") as stream_:
        stream_.write(line + "\n")
        stream_.flush()
        os.fsync(stream_.fileno())
    # The new entry in its directory is synced too, so the log survives a
    # power loss, not only a killed process.
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    _ATTEMPT["path"] = path


def close_attempt() -> None:
    """Stop appending stages (the log itself stays on disk)."""
    _ATTEMPT["path"] = None


def _utc_now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds"
    )


def progress(message: str) -> None:
    """Stage names and counts only, on stderr, and appended to the open
    attempt log, if there is one."""
    print(message, file=sys.stderr, flush=True)
    path = _ATTEMPT["path"]
    if path is not None:
        line = json.dumps({"utc": _utc_now(), "stage": message})
        with path.open("a", encoding="utf-8") as stream_:
            stream_.write(line + "\n")
            stream_.flush()
            os.fsync(stream_.fileno())


_GUARD: dict[str, Any] = {"roots": None, "allowed": None, "installed": False}


def _guard_hook(event: str, args: tuple) -> None:
    if event != "open":
        return
    roots, allowed = _GUARD["roots"], _GUARD["allowed"]
    if roots is None or not args or isinstance(args[0], int):
        return
    literal = Path(os.path.abspath(os.fsdecode(os.fspath(args[0]))))
    for candidate in (literal, literal.resolve()):
        for root in roots:
            if candidate.is_relative_to(root):
                relative = candidate.relative_to(root).as_posix()
                if relative not in allowed:
                    raise PermissionError(
                        f"B2's read set does not hold {relative}"
                    )
                return


@contextmanager
def psid_read_guard(psid_dir: Path, allowed: frozenset[str]) -> Iterator[None]:
    """Refuse, before it happens, any open under ``psid_dir`` outside
    ``allowed`` (paths relative to it, in POSIX form)."""
    if not _GUARD["installed"]:
        sys.addaudithook(_guard_hook)
        _GUARD["installed"] = True
    literal = Path(os.path.abspath(psid_dir))
    _GUARD["roots"] = (literal, literal.resolve())
    _GUARD["allowed"] = frozenset(allowed)
    try:
        yield
    finally:
        _GUARD["roots"] = None
        _GUARD["allowed"] = None


def check_opened(
    opened: Mapping[str, str], pinned: Mapping[str, str]
) -> dict[str, str]:
    """Every opened PSID file must be in the pinned read set with the
    pinned SHA-256. Returns the opened files' hashes, sorted."""
    outside = sorted(set(opened) - set(pinned))
    if outside:
        raise AssertionError(
            f"files outside B2's read set were opened: {outside}"
        )
    differing = sorted(
        name for name, digest in opened.items() if pinned[name] != digest
    )
    if differing:
        raise AssertionError(
            f"files differ from their pinned hashes: {differing}"
        )
    return dict(sorted(opened.items()))


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def require_clean_head(root: Path, expected_commit: str) -> str:
    """The worktree must be clean and HEAD must be ``expected_commit``."""
    if not expected_commit:
        raise RuntimeError("an expected commit is required")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("the worktree is not clean")
    head = git(root, "rev-parse", "HEAD")
    if head != expected_commit:
        raise RuntimeError(
            f"HEAD {head} is not the expected commit {expected_commit}"
        )
    return head


def require_registration(registration_id: str | None) -> str:
    """A registration identifier is required and must be one word."""
    value = (registration_id or "").strip()
    if not value or any(character.isspace() for character in value):
        raise RuntimeError("a one-word registration identifier is required")
    return value


def committed_sha256(root: Path, path: Path) -> dict[str, str]:
    """A file's SHA-256, required to be committed at HEAD unchanged."""
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    try:
        blob = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"{relative} is not committed at HEAD") from error
    data = path.read_bytes()
    if data != blob:
        raise RuntimeError(f"{relative} differs from its committed bytes")
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "commit": git(root, "log", "-n", "1", "--format=%H", "--", relative),
    }


def write_exclusive(path: Path, record: Mapping[str, Any]) -> str:
    """Write ``record`` as JSON to a new file; refuse to overwrite. Returns
    the written bytes' SHA-256."""
    text = (
        json.dumps(plain(record), indent=1, sort_keys=True, allow_nan=False)
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream_:
        stream_.write(text)
    return hashlib.sha256(text.encode()).hexdigest()


#: The most worker processes a B2 run may use: with one thread each, the
#: shared-host cap of four (Max, 2026-10-11).
MAX_WORKERS = 4


def require_workers(workers: int) -> int:
    """The run's worker count, refused outside 1 to ``MAX_WORKERS``."""
    if isinstance(workers, bool) or not isinstance(workers, int):
        raise RuntimeError(
            f"workers must be an integer from 1 to {MAX_WORKERS}"
        )
    if not 1 <= workers <= MAX_WORKERS:
        raise RuntimeError(f"workers must be from 1 to {MAX_WORKERS}")
    return workers


#: The thread variables every B2 process must set to 1.
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


#: populace-fit's forest job count. Unset, it is -1, every core, which the
#: shared host's cap forbids; protocol v2 pinned it to 4. Forests are
#: built with fixed per-tree seeds, so the count is not expected to change
#: a fit; B2 fixes it and does not rely on that expectation.
FIT_JOBS_VARIABLE = "POPULACE_FIT_N_JOBS"


def thread_settings() -> dict[str, str]:
    """The run's thread settings: one BLAS, OpenMP and numexpr thread per
    process, a passive OpenMP wait policy, and ``POPULACE_FIT_N_JOBS``
    from 1 to 4 (registered at 4, as protocol v2 ran).

    Max ruled on 2026-10-11 that runs on the shared host use at most four
    BLAS and OpenMP threads and ``OMP_WAIT_POLICY=PASSIVE``. B2 uses one
    thread per process, and up to four worker processes. On 2026-10-13 a
    probe of candidate 3's fit and projection on invented data stalled
    once at 0% CPU with more than one OpenMP thread. On 2026-10-15 the
    same probe completed at 1, 2 and 4 threads, so the stall was not
    reproduced; its cause is unknown. B2 uses one thread because it
    completed in every run (B2's registration on #42, "Why one thread").
    """
    settings = {name: os.environ.get(name, "") for name in THREAD_VARIABLES}
    for name, value in settings.items():
        if value != "1":
            raise RuntimeError(f"set {name}=1")
    jobs = os.environ.get(FIT_JOBS_VARIABLE, "")
    if jobs not in {str(n) for n in range(1, MAX_WORKERS + 1)}:
        raise RuntimeError(
            f"set {FIT_JOBS_VARIABLE} to an integer from 1 to {MAX_WORKERS}"
        )
    policy = os.environ.get("OMP_WAIT_POLICY", "")
    if policy.upper() != "PASSIVE":
        raise RuntimeError("set OMP_WAIT_POLICY=PASSIVE")
    return {**settings, FIT_JOBS_VARIABLE: jobs, "OMP_WAIT_POLICY": policy}
