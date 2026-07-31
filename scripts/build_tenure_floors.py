"""Build pre-IC3 CPS tenure noise-floor references for gate E3 (#192).

REPORTED ANCHOR, NOT A GATE RUN: IC3 has not locked and no thresholds
are proposed; v1 pinning does not ratify anything. E3's moment is the
tenure distribution (P25/P50/P75) by age band against the CPS
January supplement; this commits the person-disjoint half-vs-half
sampling-noise floor those thresholds would later be derived from,
completing the tenure side of Workstream A's floor battery
(companion to the E4/E5 SIPP floors).

Method mirrors the spell floors: for seeds 0-4, persons split into
two disjoint sha256 halves; each cell's weighted P25/P50/P75 of
``tenure_years`` is computed on both halves and the across-seed
mean and sd of the absolute quantile gap **in years** is the floor
(quantiles are in interpretable units, so the gap is reported in
years rather than a log ratio). Reported tenure heaps hard on
integers, so half-vs-half quantile gaps are frequently EXACTLY zero
(both halves' quantiles land on the same heap) — a degenerate basis
for a "quantile error vs floor" criterion. Each cell therefore also
carries a weighted-ECDF max-gap (Kolmogorov-style) floor, which is
smooth under heaping; the IC3 round can choose between the quantile
and distributional formulations with both on the record. All three
staged supplements
(2020/2022/2024) are floored independently — the across-year spread
of the floors is itself informative about supplement-to-supplement
stability. Cells with fewer than 200 unweighted persons per half
are flagged thin.

Thin-flag units: the thin flag counts **rows** per half, which
equal persons because the CPS tenure frame has one record per
person, against ``THIN_CELL_PERSONS = 200`` (the same constant the
SIPP spell floors use, where E4 and E9 count distinct persons —
units are recorded per artifact).

Usage::

    python scripts/build_tenure_floors.py

writes ``runs/tenure_floors_v1.json``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from populace_dynamics.contract import environment_block  # noqa: E402
from populace_dynamics.data import cps_tenure  # noqa: E402

YEARS = (2020, 2022, 2024)
SEEDS = (0, 1, 2, 3, 4)
QUANTILES = (0.25, 0.50, 0.75)
THIN_CELL_PERSONS = 200

ARTIFACT = REPO / "runs/tenure_floors_v1.json"
ENV_SIDECAR = ARTIFACT.with_suffix(".env.json")
INPUT_SIDECAR = ARTIFACT.with_suffix(".inputs.json")
OFFICIAL_SOURCE_URL = (
    "https://www2.census.gov/programs-surveys/cps/datasets/"
    "{year}/supp/jan{yy:02d}pub.csv"
)


def _source_pins() -> list[dict[str, str]]:
    data_dir = cps_tenure._resolve_data_dir(None)  # noqa: SLF001
    pins = []
    for year in YEARS:
        path = cps_tenure._resolve_person_path(year, data_dir)  # noqa: SLF001
        pins.append(
            {
                "year": str(year),
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return pins


def _reader_commit() -> str:
    """Last commit touching the CPS tenure reader for this run."""
    import subprocess

    try:
        return subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%H",
                "--",
                "src/populace_dynamics/data/cps_tenure.py",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _half(person_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{person_id}".encode()).digest()
    return digest[0] & 1


def _weighted_quantile(values, weights, q: float) -> float:
    order = np.argsort(values, kind="stable")
    values = np.asarray(values)[order]
    weights = np.asarray(weights)[order]
    cum = np.cumsum(weights) - 0.5 * weights
    cum /= weights.sum()
    return float(np.interp(q, cum, values))


def _weighted_ecdf_max_gap(a_values, a_weights, b_values, b_weights):
    """Max |F_a(x) - F_b(x)| over the union grid of observed values."""
    grid = np.union1d(a_values, b_values)

    def ecdf(values, weights):
        order = np.argsort(values, kind="stable")
        v = np.asarray(values)[order]
        w = np.asarray(weights)[order]
        cum = np.cumsum(w) / w.sum()
        idx = np.searchsorted(v, grid, side="right") - 1
        return np.where(idx >= 0, cum[idx], 0.0)

    return float(
        np.max(np.abs(ecdf(a_values, a_weights) - ecdf(b_values, b_weights)))
    )


def floors_for_year(year: int) -> dict:
    records = cps_tenure.read_cps_tenure(year)
    usable = records[
        records["tenure_years"].notna() & (records["weight"] > 0)
    ].copy()
    labels = [f"{lo}_{hi}" for lo, hi in cps_tenure.DEFAULT_AGE_BANDS]
    import pandas as pd

    usable["age_band"] = pd.cut(
        usable["age"],
        bins=[cps_tenure.DEFAULT_AGE_BANDS[0][0] - 1]
        + [hi for _, hi in cps_tenure.DEFAULT_AGE_BANDS],
        labels=labels,
    )
    usable = usable[usable["age_band"].notna()]

    cells = {}
    for band, cell in usable.groupby("age_band", observed=True):
        values = cell["tenure_years"].to_numpy(dtype=float)
        weights = cell["weight"].to_numpy(dtype=float)
        point = {
            f"p{int(q * 100)}": round(
                _weighted_quantile(values, weights, q), 2
            )
            for q in QUANTILES
        }
        halves = cell["person_id"].map(
            lambda pid: [_half(pid, seed) for seed in SEEDS]
        )
        gaps: dict[str, list[float]] = {
            f"p{int(q * 100)}": [] for q in QUANTILES
        }
        ks_gaps: list[float] = []
        thin = False
        for i, _seed in enumerate(SEEDS):
            mask_a = halves.map(lambda h, i=i: h[i] == 0)
            a, b = cell[mask_a], cell[~mask_a]
            if min(len(a), len(b)) < THIN_CELL_PERSONS:
                thin = True
            for q in QUANTILES:
                qa = _weighted_quantile(
                    a["tenure_years"].to_numpy(dtype=float),
                    a["weight"].to_numpy(dtype=float),
                    q,
                )
                qb = _weighted_quantile(
                    b["tenure_years"].to_numpy(dtype=float),
                    b["weight"].to_numpy(dtype=float),
                    q,
                )
                gaps[f"p{int(q * 100)}"].append(abs(qa - qb))
            ks_gaps.append(
                _weighted_ecdf_max_gap(
                    a["tenure_years"].to_numpy(dtype=float),
                    a["weight"].to_numpy(dtype=float),
                    b["tenure_years"].to_numpy(dtype=float),
                    b["weight"].to_numpy(dtype=float),
                )
            )
        cells[str(band)] = {
            **point,
            "persons_unweighted": int(len(cell)),
            "floor_abs_gap_years": {
                name: {
                    "mean": round(float(np.mean(values)), 3),
                    "sd": round(float(np.std(values)), 3),
                }
                for name, values in gaps.items()
            },
            "floor_ecdf_max_gap": {
                "mean": round(float(np.mean(ks_gaps)), 4),
                "sd": round(float(np.std(ks_gaps)), 4),
            },
            "thin": thin,
        }
    return cells


def build() -> dict:
    return {
        "artifact": "tenure_floors",
        "version": "v1",
        "status": (
            "PRE-LOCK REFERENCE - NOT RATIFIED; IC3 not locked; no "
            "thresholds. v1 is a pinning event, not a ratification"
        ),
        "issue": "192",
        "deployment_scale_note": (
            "RECORDED GAP (review of #212): these floors are "
            "half-vs-half, i.e. the sampling noise of ~50%-of-source "
            "estimates, while IC3 proposes scoring on a 0.20 person "
            "holdout - there is no candidate-context floor (gate-1 "
            "ctx20 analog). Under root-n scaling, a 20% scoring "
            "frame has ~sqrt(0.5/0.2)=1.58x the sampling noise of "
            "the half-split basis, so these floors are mildly "
            "ANTI-conservative (too tight), not conservative. "
            "RECORDED_NOT_SATISFIED: IC3 must accept a registered "
            "analytic scale adjustment or require matching-context "
            "floors before candidate runs."
        ),
        "source": "CPS January supplements 2020/2022/2024 (PTST1TN, "
        "PWTENWGT); reader per #205",
        "method": (
            "person-disjoint sha256 half-splits, seeds 0-4; per-cell "
            "absolute weighted-quantile gap in years AND weighted-ECDF "
            "max gap (heaping-robust), mean/sd across seeds; BLS age "
            "bands"
        ),
        "heaping_caveat": (
            "reported tenure heaps on integers, so half-vs-half "
            "quantile gaps are frequently exactly zero (36/63 cells "
            "in the first build) - a degenerate threshold basis; the "
            "ECDF max-gap floor is the heaping-robust alternative "
            "for the IC3 round to choose between"
        ),
        "thin_flag_units": (
            "rows per half, equal to persons (one CPS record per "
            "person) vs THIN_CELL_PERSONS=200"
        ),
        "cps_tenure_reader_commit": _reader_commit(),
        "source_inputs": _source_pins(),
        "by_year": {str(year): floors_for_year(year) for year in YEARS},
    }


def main() -> None:
    artifact = build()
    ARTIFACT.write_text(json.dumps(artifact, indent=2) + "\n")
    data_dir = cps_tenure._resolve_data_dir(None)  # noqa: SLF001
    INPUT_SIDECAR.write_text(
        json.dumps(
            {
                "artifact": ARTIFACT.name,
                "status": "SOURCE_INPUT_DIGESTS",
                "source_inputs": [
                    {
                        **source,
                        "bytes": cps_tenure._resolve_person_path(  # noqa: SLF001
                            int(source["year"]), data_dir
                        )
                        .stat()
                        .st_size,
                        "official_url": OFFICIAL_SOURCE_URL.format(
                            year=int(source["year"]),
                            yy=int(source["year"]) % 100,
                        ),
                    }
                    for source in artifact["source_inputs"]
                ],
            },
            indent=2,
        )
        + "\n"
    )
    ENV_SIDECAR.write_text(
        json.dumps(
            {
                "artifact": ARTIFACT.name,
                "status": "MEASUREMENT_ENVIRONMENT",
                "environment": environment_block(),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {ARTIFACT}")
    y24 = artifact["by_year"]["2024"]
    example = y24["35_44"]
    print(
        "example 35_44 (2024): p50 =",
        example["p50"],
        "floor(p50) =",
        example["floor_abs_gap_years"]["p50"],
    )


if __name__ == "__main__":
    main()
