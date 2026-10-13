"""INVENTED data only. Does copying households distort the sign gate's fit?

Compares the HGB sign gate refit on (a) with-replacement household copies and
(b) without-replacement household half-samples of one invented panel:
boosting iterations and the across-refit variance of predicted
probabilities on a fixed feature grid. Under no distortion the two
variances agree (a half-sample estimate's deviation from the full-sample
estimate has the full-sample variance when f = 1/2).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
N_HOUSEHOLDS = int(sys.argv[2])
N_REFITS = int(sys.argv[3])
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import track_b_b0_1_planning_values as pv  # noqa: E402

from tests.test_track_b_b0_1_planning_values import (  # noqa: E402
    _codes,
    _invented_fields,
)

person_wave, labor = _invented_fields(n_households=N_HOUSEHOLDS, seed=101)
sources = pv.build_sources(person_wave, labor, _codes)
fit_input = pv.truncate_estimation_frame(
    sources.earnings,
    boundary_year=pv.PSEUDO_ORIGIN,
    year_column="period",
    flow=False,
    label="invented",
)
nawi = {year: 30_000.0 * 1.03 ** (year - 1990) for year in range(1960, 2007)}
full_anchor = pv.anchor_frame(sources.person_wave, pv.ANCHOR_WAVE)
clusters = pv.cluster_table(
    sources.person_wave, fit_input["person_id"].unique(), full_anchor
)
t0 = time.perf_counter()
full = pv.fit_law(fit_input, nawi, skip_forests=True)
print(
    f"households {N_HOUSEHOLDS} fit rows {len(fit_input)} pairs "
    f"{len(full.forward_pairs)} full fit {time.perf_counter() - t0:.1f}s",
    flush=True,
)


def gate_of(fitted):
    return fitted.generator.shared_gate._target_models["earnings_tp2"].gate


grid_level = np.exp(np.linspace(8.5, 11.8, 12))
grid_age = np.array([28.0, 38.0, 48.0, 58.0])
grid = np.array(
    [(level, age) for level in grid_level for age in grid_age]
    + [(0.0, age) for age in grid_age]
)


def p_positive(fitted):
    gate = gate_of(fitted)
    proba = gate.predict_proba(grid)
    column = list(gate.classes_).index(1)
    return proba[:, column]


base = p_positive(full)
print("full n_iter", gate_of(full).n_iter_, flush=True)
anchor_ids = np.sort(
    clusters.loc[clusters.stratum == "anchor", "cluster"].unique()
)
other_ids = np.sort(
    clusters.loc[clusters.stratum == "other", "cluster"].unique()
)
results = {}
for scheme in ("copies", "half"):
    iters, preds = [], []
    for b in range(N_REFITS):
        rng = np.random.default_rng([20260930, b, 7])
        by_cluster = {}
        for ids in (anchor_ids, other_ids):
            if not len(ids):
                continue
            if scheme == "copies":
                counts = rng.multinomial(
                    len(ids), np.full(len(ids), 1 / len(ids))
                )
            else:
                counts = np.zeros(len(ids), dtype=int)
                counts[rng.permutation(len(ids))[: len(ids) // 2]] = 1
            by_cluster.update(
                dict(zip(ids.tolist(), counts.tolist(), strict=False))
            )
        mult = pv.person_multiplicities(clusters, by_cluster)
        fitted = pv.fit_law(
            pv.copy_persons(fit_input, mult), nawi, skip_forests=True
        )
        iters.append(int(gate_of(fitted).n_iter_))
        preds.append(p_positive(fitted))
    preds = np.asarray(preds)
    results[scheme] = preds
    print(
        scheme,
        "n_iter mean",
        round(float(np.mean(iters)), 1),
        "min",
        min(iters),
        "max",
        max(iters),
        "| mean abs shift from full",
        round(float(np.mean(np.abs(preds.mean(axis=0) - base))), 4),
        "| mean variance over grid",
        f"{float(np.mean(preds.var(axis=0, ddof=1))):.3e}",
        flush=True,
    )
ratio = results["copies"].var(axis=0, ddof=1) / results["half"].var(
    axis=0, ddof=1
)
print(
    "variance ratio copies/half over grid: median",
    round(float(np.median(ratio)), 2),
    "geometric mean",
    round(float(np.exp(np.mean(np.log(ratio)))), 2),
    flush=True,
)
