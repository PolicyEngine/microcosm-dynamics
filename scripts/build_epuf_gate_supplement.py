"""Supplement to the EPUF gate's floor artifact, for the referee round.

Round 1 of the referee review (``reviews/gate_epuf_round1_referee_20261002.md``)
asked for three things the floor artifact does not store:

1. **Bite shifts.** Each bite demonstration's per-seed estimates on the 20
   gate holdouts and its mean shift from the unperturbed real holdouts, for
   every cell the registered rules selected, and the bite's power under the
   gate's own noise model: the probability that a candidate centred at the
   PSID's position moved by that shift falls outside the cell's interval,
   with the cell's realised sigma. The fail shares in the floor artifact
   perturb the realised sample and score it on fixed holdouts, so they omit
   the noise the 20 seeds share.
2. **Birth years.** The support's birth-year distribution within each sex and
   cohort band beside EPUF's, because the PSID birth year (derived from age
   at interview) sits about half a year below EPUF's year of birth.
3. **A build timestamp** (UTC).

The bite perturbations, splits, support and cells are imported unchanged
from ``scripts/build_epuf_gate_floors.py``; the script asserts that it
reproduces the floor artifact's fail shares exactly, so the shifts belong to
the same computation. It reads the real PSID only through the existing
loaders the floor builder uses, and generates no candidate.

Usage::

    uv run python scripts/build_epuf_gate_supplement.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

from populace_dynamics.artifacts import write_new
from populace_dynamics.data import epuf
from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import (
    COHORT_BANDS,
    SEXES,
    WindowArrays,
)

ROOT = Path(__file__).resolve().parents[1]
FLOORS = ROOT / "runs" / "epuf_gate_floors_v1.json"
ARTIFACT = ROOT / "runs" / "epuf_gate_supplement_v1.json"
SCHEMA_VERSION = "epuf_gate_supplement.v1"


def _builder():
    name = "build_epuf_gate_floors"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def power_against_shift(
    shift: float, bridge: float, sigma: float, lower: float, upper: float
) -> float:
    """Probability that a candidate at the PSID's position plus ``shift``
    falls outside ``[lower, upper]``, under the cell's normal noise."""
    centre = bridge + shift
    return float(
        norm.cdf((lower - centre) / sigma) + norm.sf((upper - centre) / sigma)
    )


def bite_shifts(builder, frame, universe, floors) -> dict[str, object]:
    """Per-seed estimates and shifts of every bite, on the selected cells."""
    registered = floors["registered"]
    cells = floors["cells"]
    position = np.searchsorted(universe, frame["person_id"].to_numpy())
    masks = {
        seed: builder.holdout_mask(
            universe, seed=seed, fraction=gate.HOLDOUT_FRACTION
        )[position]
        for seed in gate.GATE_SEEDS
    }
    wage_bases = builder.wage_bases()
    real = WindowArrays(frame, wage_bases=wage_bases)
    real_values = {
        seed: builder._values(real.cells(mask)) for seed, mask in masks.items()
    }
    real_estimate = {
        cell_id: gate.pooled_estimate(
            cell_id, [real_values[s][cell_id] for s in gate.GATE_SEEDS]
        )
        for cell_id in registered
    }
    perturbations = {
        f"bd1_persistence_loss_{share:.2f}": (
            lambda f, r, share=share: builder.perturb_persistence(f, r, share)
        )
        for share in builder.BD1_SHARES
    }
    perturbations["bd2_sex_blind_donors"] = (
        lambda f, r: builder.perturb_sex_blind(f, r, same_sex=False)
    )
    perturbations["bd2c_same_sex_donors_control"] = (
        lambda f, r: builder.perturb_sex_blind(f, r, same_sex=True)
    )
    perturbations["bd3_top_tail_compression"] = builder.perturb_top_tail
    perturbations["bd4_participation_loss"] = builder.perturb_participation

    out: dict[str, object] = {}
    for index, (name, perturb) in enumerate(perturbations.items()):
        per_cell = {cell_id: [] for cell_id in registered}
        fails = 0
        for seed in builder.BITE_SEEDS:
            rng = np.random.default_rng([builder.BITE_SEED_BASE, index, seed])
            arrays = WindowArrays(perturb(frame, rng), wage_bases=wage_bases)
            per_seed = {
                s: builder._values(arrays.cells(mask))
                for s, mask in masks.items()
            }
            scored = gate.score_run(per_seed, registered)
            fails += not scored["pass"]
            for cell_id in registered:
                per_cell[cell_id].append(scored["cells"][cell_id]["estimate"])
        fail_share = fails / len(builder.BITE_SEEDS)
        recorded = floors["bite_demonstrations"][name]["fail_share"]
        if fail_share != recorded:
            raise AssertionError(
                f"{name}: fail share {fail_share} is not the floor "
                f"artifact's {recorded}; not the same computation"
            )
        rows = {}
        for cell_id, estimates in per_cell.items():
            cell = cells[cell_id]
            shift = float(np.mean(estimates) - real_estimate[cell_id])
            rows[cell_id] = {
                "estimates_over_perturbation_seeds": estimates,
                "real_gate_holdout_estimate": real_estimate[cell_id],
                "mean_shift": shift,
                "power_under_gate_noise_model": power_against_shift(
                    shift,
                    cell["bridge_psid_minus_epuf"],
                    cell["floor"]["realized_sigma"],
                    cell["lower"],
                    cell["upper"],
                ),
            }
        out[name] = {"fail_share_reproduced": fail_share, "cells": rows}
    detection = {}
    for cell_id in registered:
        cell = cells[cell_id]
        sigma = cell["floor"]["realized_sigma"]
        distance = cell["bridge_psid_minus_epuf"] - cell["lower"]
        detection[cell_id] = {
            "distance_from_psid_to_lower_edge": distance,
            "realized_sigma": sigma,
            "shortfall_failing_80_percent": distance + 0.8416 * sigma,
            "shortfall_failing_90_percent": distance + 1.2816 * sigma,
        }
    out["detection_points"] = detection
    return out


def birth_years(frame, demographic) -> dict[str, object]:
    """Within-band birth-year shares: PSID support (weighted) and EPUF."""
    out = {}
    labels = {1: "men", 2: "women"}
    for sex in SEXES:
        code = next(k for k, v in labels.items() if v == sex)
        for band, (low, high) in COHORT_BANDS.items():
            years = list(range(low, high + 1))
            psid = frame[
                (frame["sex"] == sex) & frame["birth_year"].between(low, high)
            ]
            psid_share = (
                psid.groupby("birth_year")["weight"].sum().reindex(years)
            ).fillna(0.0)
            psid_share = psid_share / psid_share.sum()
            epuf_band = demographic[
                (demographic["sex"] == code)
                & demographic["birth_year"].between(low, high)
            ]
            epuf_share = (
                epuf_band.groupby("birth_year").size().reindex(years)
            ).fillna(0)
            epuf_share = epuf_share / epuf_share.sum()
            out[f"{sex}.{band}"] = {
                "birth_years": years,
                "psid_support_weighted_share": [float(v) for v in psid_share],
                "epuf_share": [float(v) for v in epuf_share],
                "psid_mean_birth_year": float(
                    np.average(years, weights=psid_share)
                ),
                "epuf_mean_birth_year": float(
                    np.average(years, weights=epuf_share)
                ),
            }
    return out


def main() -> None:
    started = dt.datetime.now(dt.timezone.utc)
    builder = _builder()
    floors = json.loads(FLOORS.read_text(encoding="utf-8"))
    frame, universe, _ = builder.psid_support()
    demographic = epuf.read_demographic()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run": "epuf_gate_supplement_v1",
        "status": "REFEREE_ROUND_1_SUPPLEMENT",
        "built_utc": started.isoformat(timespec="seconds"),
        "floor_run": "runs/epuf_gate_floors_v1.json",
        "floor_run_sha256": hashlib.sha256(FLOORS.read_bytes()).hexdigest(),
        "candidate_blind": {"generated_candidates": 0},
        "bites": bite_shifts(builder, frame, universe, floors),
        "birth_year_mix": birth_years(frame, demographic),
    }
    write_new(ARTIFACT, payload, sidecar=True)
    print(f"wrote {ARTIFACT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
