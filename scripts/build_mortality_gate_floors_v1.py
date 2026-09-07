"""Mortality gate floors v1: the GATE-SCHEMA derivation from floors v3.

THRESHOLD BINDING (the pre-registration packet's ceremony step 3), NOT A
GATE RUN, NOT A RATIFICATION. This script reads the verified floor basis
``runs/mortality_floors_v3.json`` BY PATH with its size and sha256 pinned,
and derives from its committed per-seed values -- never from typed
numbers -- everything the ``gate_mortality`` block needs in the shape
``runs/m4_gate_floors_v1.json`` established: the ``noise_floor_seeds_0_99``
floor block, ``cell_stability``, the ``gate_partition`` under BOTH
eligibility rules (R3), ``k_sensitivity`` at k = 1 / 2 / 3 / 4 with the
faithful-candidate operating characteristic at each (R2), the anchor
checks and the anchor cell's operating characteristic under the inherited
candidate-side rule with its remedies priced (R5), the 85+ evidence (R4),
the draw-stream base and its distinctness proof (R9), the restricted-
before-split perturbation tolerance beside the pinned full-frame one
(R10), the teeth table C1-C6 (R11), the wording audit (R12), referee A's
three additions, and the DRAFT ``gate_mortality`` block as a string
(``draft_gates_yaml_fragment.text``) with every open ruling named as a
placeholder the ratifying round must fill.

It writes NO ``gates.yaml`` byte. It does not open v1, v2 or v3 for
writing. It scores no candidate. Every ruling it touches is FILED and
PRICED both ways; none is MADE here.

Two of its blocks need the staged PSID individual file (the restricted-
split perturbation and the censoring bracket); the rest derive from the
v3 bytes alone. Run from the repository root::

    .venv/bin/python scripts/build_mortality_gate_floors_v1.py

It needs no populace-fit.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_mortality_floors as v1b  # noqa: E402
import build_mortality_floors_v3 as v3b  # noqa: E402

from populace_dynamics.data import deaths, panels  # noqa: E402
from populace_dynamics.harness import panel as hpanel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FLOOR_PATH = ROOT / "runs" / "mortality_floors_v3.json"
ARTIFACT_PATH = ROOT / "runs" / "mortality_gate_floors_v1.json"
GATES_PATH = ROOT / "gates.yaml"
NCHS_PATH = ROOT / "data" / "external" / "nchs_life_tables_2023.json"
V3_BUILDER_PATH = ROOT / "scripts" / "build_mortality_floors_v3.py"

ARTIFACT_SCHEMA_VERSION = "mortality_gate_floors.v1"
RUN_NAME = "mortality_gate_floors_v1"

#: The VERIFIED floor basis this derivation reads (floors v4 at 62d01d6;
#: independent verification VERIFIED -- READY FOR THRESHOLD BINDING).
#: Size and sha256 are pinned here AND in tests/test_gates_derivations.py;
#: a rebuilt v3 under a moved convention cannot feed this derivation
#: silently (referee A D1 remedy at binding).
SOURCE_FLOOR_COMMITTED = (
    2_711_564,
    "8998bca2d7026926cc44a199087810bc654863c12b2d14466ce0ff73f95e0776",
)
#: The gates.yaml blob the R4 "~27%" quotation is located in (byte-
#: identical to origin/master at this sitting; resolved by git cat-file).
GATES_YAML_BLOB_AT_BINDING = "b0c39af1e13a705f90b85d3e6b9a91e1d3c5485c"
GATES_YAML_27PCT_LINES = (5399, 5402)

T_MAX = math.log(1.5)
K_CHOSEN = 3
K_GRID = (1, 2, 3, 4)
ROUNDING = 3
MARGIN_K = 3
MIN_EVENTS = 20
GATE_SEEDS = (0, 1, 2, 3, 4)
FLOOR_SEEDS = tuple(range(100))
CANDIDATE_DRAWS = 20
#: R9 -- the PROPOSED draw-stream base. Issue #74 Phase B -> 7400 + k.
#: DISTINCT from every stream gates.yaml names (5200 tranche 2a/2b/2c/
#: m4; 4200 the superseded single draw; 4100 the drifted stream finding
#: 2 of gate_m4 restored from; 9100 / 9200 gate_w1 families A / B; 91000
#: the W1 bootstrap; 20260710 the 2c bootstrap), from the split seeds
#: 0-99, the gate seeds 0-4 and the floors' bootstrap key 20260906. It
#: enters gates.yaml ONLY at the flip.
DRAW_STREAM_BASE = 7400
PRECEDENT_OC_BAND = {"gate_2a": 0.9685, "gate_2b": 0.9678, "gate_2c": 0.9641}
HEADLINE_CONVENTION = "pinned_narrow_midpoint"
HEADLINE_UNIVERSE = "declared_1997_plus"
DECLARED_START = 1997
DOMINANCE_BAND_SET = ("45-54", "55-64", "65-74")
FIVE_BAND_SET = ("25-34", "35-44", "45-54", "55-64", "65-74")
GRADIENT_BAND_SET = ("55-64", "65-74", "75-84", "85+")
BANDS_25_84 = tuple(b for b in v1b.BAND_LABELS if b != "85+")
CELL_PREFIX = "death."
#: Referee A's stability clause (finding (iii)): a cell whose bootstrap
#: P(T <= cap) at its own sigma lies in this band is report-only whatever
#: its point tolerance -- PROPOSED, not adopted.
STABILITY_BAND = (0.1, 0.9)
#: The words the R12 audit forbids in the block and the PR body.
FORBIDDEN_WORDS = ("anchored", "aligned", "calibrated to")

REFEREE_A_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "mortality-v3-referee-A/REPORT.md (49,071 bytes, sha256 "
    "3daae3fe3ba767c5e8af3db8c98ee158ee9e53308c444505fb55bc8c03113f1d)"
)
REFEREE_B_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "mortality-v3-referee-B/REPORT.md (44,213 bytes, sha256 "
    "0c8baddc9cddbbf5aaa6bfc1941488944db4050d27ed9951edbd3a8177d75791)"
)
VERIFICATION_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "mortality-v4-verify/REPORT.md (39,760 bytes, sha256 "
    "f90769dad2c980d95a3dd5b23a73403c46db0143aa5e502fc280dbae72df4671)"
)
PACKET_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "cap-mortality-gate-prep/REPORT.md (80,940 bytes, sha256 "
    "c5d38caf643c5c7690933512a200e3a43da871d1d7eb5efbf1d121e992966ad2)"
)

#: Referee A's censoring bracket (A section 3.4) as A reported it, carried
#: for comparison against this builder's own recomputation below.
REFEREE_A_BRACKET_UNLIMITED = {
    "25-34|male": 0.269,
    "25-34|female": 0.739,
    "35-44|male": 0.270,
    "35-44|female": 0.271,
    "45-54|male": 0.320,
    "45-54|female": 0.499,
    "55-64|male": 0.324,
    "55-64|female": 0.466,
    "65-74|male": 0.271,
    "65-74|female": 0.307,
    "75-84|male": 0.321,
    "75-84|female": 0.365,
    "85+|male": 0.281,
    "85+|female": 0.359,
}
REFEREE_A_BRACKET_LE_ONE_INTERVAL = {
    "25-34|male": 0.189,
    "25-34|female": 0.690,
    "35-44|male": 0.242,
    "35-44|female": 0.239,
    "45-54|male": 0.298,
    "45-54|female": 0.449,
    "55-64|male": 0.273,
    "55-64|female": 0.423,
    "65-74|male": 0.252,
    "65-74|female": 0.292,
    "75-84|male": 0.292,
    "75-84|female": 0.342,
    "85+|male": 0.262,
    "85+|female": 0.336,
}
REFEREE_A_BRACKET_TOTALS = {
    "unlimited": {"added_deaths_declared": 982, "median_ratio": 1.036},
    "le_one_more_grid_interval": {
        "added_deaths_declared": 850,
        "median_ratio": 1.015,
    },
    "missed_exact_decedents": 2796,
    "missed_exact_decedents_last_wave_1997_plus": 1025,
}
#: Referee A's anchor OC (A section 4.5) as reported, for comparison.
REFEREE_A_ANCHOR_OC = {
    "side_a_draw_noise_only": {"p_seed": 0.733, "p_gate": 0.597},
    "side_a_fitted_excluding_holdout": {"p_seed": 0.554, "p_gate": 0.262},
    "both_sides_draw_noise_only": {"p_seed": 0.616, "p_gate": 0.365},
    "both_sides_fitted_excluding_holdout": {
        "p_seed": 0.526,
        "p_gate": 0.221,
    },
}
#: Referee A's finding (iii), the sentence from A section 4.3 quoted
#: EXACTLY (record hygiene, verification item 10 / V-1): the v3 artifact's
#: open_questions_for_the_ceremony[8] carries a condensed splice labelled
#: "VERBATIM"; this artifact carries the sentence as A wrote it.
REFEREE_A_FINDING_III_VERBATIM = (
    "Statistical reading: at 100 seeds the partition status of both "
    "65-74 cells is decided by the seed set, not by the data; the "
    "pre-registered seeds 0-99 make the point estimate the convention, "
    "and a candidate cannot move it, but a future rebuild under any "
    "changed convention (as R6 just demonstrated, 0.413 → 0.408) can "
    "flip `65-74|female` at P ≈ 0.6. Recommendation for threshold "
    "binding (§6): pre-register a stability clause — a cell whose "
    "bootstrap `P(T ≤ cap)` at its own σ lies in [0.1, 0.9] is "
    "report-only whatever its point tolerance — which changes nothing "
    "today and removes the flip risk; or decide the partition at 1,000 "
    "seeds (my loop: 4.6 s per 100 seeds per block)."
)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _sha_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _tolerance(mean: float, sd: float, k: float) -> float:
    """``round(mean + k*sd, 3)`` -- the shared derivation convention."""
    return round(mean + k * sd, ROUNDING)


def _gate_4_of_5(p_seed: float) -> float:
    return p_seed**5 + 5.0 * p_seed**4 * (1.0 - p_seed)


def _git_sha(cwd: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=cwd, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_blob(blob_id: str) -> bytes | None:
    try:
        return subprocess.check_output(
            ["git", "cat-file", "blob", blob_id],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def load_source_floor() -> dict[str, Any]:
    """The verified v3 floor, read by path, its bytes checked first."""
    size = SOURCE_FLOOR_PATH.stat().st_size
    digest = _sha_of_file(SOURCE_FLOOR_PATH)
    if (size, digest) != SOURCE_FLOOR_COMMITTED:
        raise RuntimeError(
            "runs/mortality_floors_v3.json is not the verified artifact: "
            f"({size}, {digest}) != {SOURCE_FLOOR_COMMITTED}"
        )
    return json.loads(SOURCE_FLOOR_PATH.read_text())


def headline_block(v3: dict[str, Any]) -> dict[str, Any]:
    return v3["internal_noise_floor"]["conventions"][HEADLINE_CONVENTION][
        "universes"
    ][HEADLINE_UNIVERSE]


def gate_cell(cell: str) -> str:
    """``75-84|male`` -> ``death.75-84|male`` (the gates.yaml cell name)."""
    return f"{CELL_PREFIX}{cell}"


# --------------------------------------------------------------------------
# R2 -- the floor block, cell stability, tolerances, OC, k-sensitivity
# --------------------------------------------------------------------------
def derive_floor(per_seed: list[dict[str, Any]], cells: list[str]) -> dict:
    """``noise_floor_seeds_0_99`` re-derived from the per-seed |ln| values.

    Nothing is copied from v3's own pooled block; the test asserts the two
    agree, so the derivation basis is the per-seed record itself.
    """
    out: dict[str, Any] = {}
    for cell in cells:
        values = np.array(
            [s["cells"][cell]["log_ratio_abs"] for s in per_seed],
            dtype=np.float64,
        )
        if values.size != len(FLOOR_SEEDS) or np.isnan(values).any():
            raise RuntimeError(f"{cell}: undefined on some seed")
        out[cell] = {
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=1)),
            "min": float(values.min()),
            "max": float(values.max()),
            "n_seeds": int(values.size),
            "realized_sigma": float(np.sqrt((values**2).mean())),
            "values": [float(v) for v in values],
        }
    return out


def cell_stability(
    per_seed: list[dict[str, Any]],
    floor: dict[str, Any],
    bootstrap: dict[str, Any],
    cells: list[str],
) -> dict[str, Any]:
    """Per cell: counts under both eligibility rules, tolerances at every
    k, sigma units, the cap test and the bootstrap P(T <= cap)."""
    out: dict[str, Any] = {}
    for cell in cells:
        min_deaths = min(
            min(s["cells"][cell]["n_death_a"], s["cells"][cell]["n_death_b"])
            for s in per_seed
        )
        min_kish = min(
            min(
                s["cells"][cell]["kish_death_a"],
                s["cells"][cell]["kish_death_b"],
            )
            for s in per_seed
        )
        f = floor[cell]
        tol = {
            f"tolerance_k{k}": _tolerance(f["mean"], f["sd"], k)
            for k in K_GRID
        }
        p_boot = bootstrap["per_cell"][cell]["at_100_seeds_sigma_v3"][
            "p_tolerance_at_or_below_t_max"
        ]
        entry: dict[str, Any] = {
            "defined_seeds": int(f["n_seeds"]),
            "n_seeds": int(f["n_seeds"]),
            "min_deaths_either_half_unweighted": int(min_deaths),
            "min_effective_deaths_kish": round(float(min_kish), 3),
            "realized_sigma": f["realized_sigma"],
            **tol,
            "tolerance_sigma_units_k3": round(
                tol["tolerance_k3"] / f["realized_sigma"], 3
            ),
            "clears_t_max_at_k3": bool(tol["tolerance_k3"] <= T_MAX),
            "clears_t_max_by_k": {
                str(k): bool(tol[f"tolerance_k{k}"] <= T_MAX) for k in K_GRID
            },
            "bootstrap_p_tolerance_at_or_below_t_max_100_seeds": p_boot,
            "bootstrap_in_stability_band": bool(
                STABILITY_BAND[0] <= p_boot <= STABILITY_BAND[1]
            ),
            "events_ge_20_unweighted_worst_seed": bool(
                min_deaths >= MIN_EVENTS
            ),
            "events_ge_20_kish_effective_worst_seed": bool(
                min_kish >= MIN_EVENTS
            ),
        }
        out[cell] = entry
    return out


def report_reason(entry: dict[str, Any], rule: str) -> str:
    """The machine reason for a cell under one eligibility rule, in the
    v1/v2/v3 pool_floor precedence: undefined -> power -> events -> clears."""
    if entry["defined_seeds"] < entry["n_seeds"]:
        return "undefined_on_some_seed"
    if not entry["clears_t_max_at_k3"]:
        return "tolerance_above_t_max"
    if rule == "unweighted_worst_seed_ge_20":
        if not entry["events_ge_20_unweighted_worst_seed"]:
            return "below_20_deaths_weaker_half"
    elif rule == "kish_effective_ge_20":
        if not entry["events_ge_20_kish_effective_worst_seed"]:
            return "below_20_effective_deaths_weaker_half"
    else:
        raise ValueError(rule)
    return "clears_t_max_at_k3"


ELIGIBILITY_RULES = {
    "unweighted_worst_seed_ge_20": (
        "v1's rule: at least 20 UNWEIGHTED deaths on the weaker half of the "
        "worst seed (NCHS's reliability floor), AND defined on every seed, "
        "AND tolerance_k3 <= T_max"
    ),
    "kish_effective_ge_20": (
        "the packet's section-1 correction: at least 20 EFFECTIVE (Kish, "
        "(sum w d)^2 / sum (w d)^2) weighted deaths on the weaker half of "
        "the worst seed, AND defined on every seed, AND tolerance_k3 <= "
        "T_max -- the count matched to the WEIGHTED statistic that is gated"
    ),
}


def partitions_by_rule(
    stability: dict[str, Any], cells: list[str]
) -> dict[str, Any]:
    """R3: the partition under BOTH rules, and the priced difference."""
    out: dict[str, Any] = {}
    for rule, text in ELIGIBILITY_RULES.items():
        eligible, report_only, reasons = [], [], {}
        for cell in cells:
            reason = report_reason(stability[cell], rule)
            reasons[cell] = reason
            (
                eligible if reason == "clears_t_max_at_k3" else report_only
            ).append(cell)
        events_pass = [
            c
            for c in cells
            if stability[c][
                (
                    "events_ge_20_unweighted_worst_seed"
                    if rule == "unweighted_worst_seed_ge_20"
                    else "events_ge_20_kish_effective_worst_seed"
                )
            ]
        ]
        out[rule] = {
            "rule": text,
            "gate_eligible_internal": sorted(eligible),
            "report_only": sorted(report_only),
            "report_reason": reasons,
            "cells_passing_the_event_criterion_alone": sorted(events_pass),
            "n_gate_eligible_internal": len(eligible),
            "n_report_only": len(report_only),
        }
    a = out["unweighted_worst_seed_ge_20"]
    b = out["kish_effective_ge_20"]
    ev_a = set(a["cells_passing_the_event_criterion_alone"])
    ev_b = set(b["cells_passing_the_event_criterion_alone"])
    out["difference"] = {
        "gated_sets_identical": a["gate_eligible_internal"]
        == b["gate_eligible_internal"],
        "gated_set": a["gate_eligible_internal"],
        "event_criterion_pass_unweighted_only": sorted(ev_a - ev_b),
        "event_criterion_pass_kish_only": sorted(ev_b - ev_a),
        "report_reason_differs_on": sorted(
            c for c in cells if a["report_reason"][c] != b["report_reason"][c]
        ),
        "min_counts_on_the_gated_set": {
            c: {
                "unweighted": stability[c][
                    "min_deaths_either_half_unweighted"
                ],
                "kish": stability[c]["min_effective_deaths_kish"],
            }
            for c in a["gate_eligible_internal"]
        },
        "price": (
            "ZERO movement of the gated set today under either rule: every "
            "clearing cell carries unweighted min 86-155 and Kish 67.6-120.9 "
            "against the 20 floor (both referees). The rules differ only in "
            "which event criterion a cell ABOVE the cap would also fail "
            "(cells listed in event_criterion_pass_unweighted_only clear the "
            "unweighted count and fail the Kish count; both are demoted on "
            "power first, so no report_reason moves). The ruling matters "
            "only for a future rebuild that brings a sparse cell under the "
            "cap: the Kish rule is the stricter one and the one matched to "
            "the weighted statistic; the unweighted rule is the v1 record "
            "and the NCHS reliability convention as literally stated."
        ),
    }
    return out


def faithful_oc(
    cells: list[str], stability: dict[str, Any], k: int
) -> dict[str, Any]:
    """gate_m4's independence-approx normal OC for a faithful candidate."""
    per_cell: dict[str, Any] = {}
    p_seed = 1.0
    for cell in cells:
        tol = stability[cell][f"tolerance_k{k}"]
        sigma = stability[cell]["realized_sigma"]
        p = 2.0 * _normal_cdf(tol / sigma) - 1.0
        per_cell[cell] = {
            "tolerance": tol,
            "realized_sigma": sigma,
            "cell_pass_prob": round(p, 6),
        }
        p_seed *= p
    if not cells:
        return {
            "n_gated_internal_cells": 0,
            "p_seed_pass": None,
            "p_gate_pass_4_of_5": None,
            "per_cell": {},
        }
    return {
        "n_gated_internal_cells": len(cells),
        "p_seed_pass": round(p_seed, 4),
        "p_gate_pass_4_of_5": round(_gate_4_of_5(p_seed), 4),
        "per_cell": per_cell,
    }


OC_METHOD = (
    "Independence-approx normal OC. Per gated internal cell a faithful "
    "candidate's score ~ half-normal(realized_sigma); cell pass = "
    "2*Phi(tolerance/sigma)-1. Seed pass = product over gated cells; gate "
    "= P(>=4 of 5) = p^5 + 5 p^4 (1-p). The K=20 estimator shares this "
    "draw-noise-free basis (runs/m4_gate_floors_v1.json "
    "faithful_candidate_oc.method, re-used verbatim)."
)


def k_selection(stability: dict[str, Any], cells: list[str]) -> dict[str, Any]:
    """Which cells clear the cap at each k and the OC on both surfaces."""
    by_k: dict[str, Any] = {}
    for k in K_GRID:
        clearing = sorted(
            c for c in cells if stability[c][f"tolerance_k{k}"] <= T_MAX
        )
        clearing_25_84 = [c for c in clearing if not c.startswith("85+")]
        oc_all = faithful_oc(clearing, stability, k)
        oc_25_84 = faithful_oc(clearing_25_84, stability, k)
        by_k[str(k)] = {
            "n_cells_incl_85plus": len(clearing),
            "cells_incl_85plus": clearing,
            "p_seed_incl_85plus": oc_all["p_seed_pass"],
            "p_gate_incl_85plus": oc_all["p_gate_pass_4_of_5"],
            "n_cells_25_84": len(clearing_25_84),
            "cells_25_84": clearing_25_84,
            "p_seed_25_84": oc_25_84["p_seed_pass"],
            "p_gate_25_84": oc_25_84["p_gate_pass_4_of_5"],
            "clears_precedent_band_incl_85plus": (
                oc_all["p_gate_pass_4_of_5"] is not None
                and oc_all["p_gate_pass_4_of_5"]
                >= min(PRECEDENT_OC_BAND.values())
            ),
            "clears_precedent_band_25_84": (
                oc_25_84["p_gate_pass_4_of_5"] is not None
                and oc_25_84["p_gate_pass_4_of_5"]
                >= min(PRECEDENT_OC_BAND.values())
            ),
        }
    return {
        "rule": (
            "UNIFORM k (mortality declares no stock cell, so gate_m4's MIXED "
            "flow/stock k does not arise); k is pinned by the faithful-"
            "candidate OC against the 2a/2b/2c precedent band, the gate_m4 "
            "k_selection method"
        ),
        "chosen_k": K_CHOSEN,
        "k_grid": list(K_GRID),
        "by_k": by_k,
        "precedent_oc_band": dict(PRECEDENT_OC_BAND),
        "reading": (
            "k=1 and k=2 collapse the OC below the precedent floor on both "
            "surfaces; k=4 keeps only three cells and drops 75-84|female; "
            "k=3 is the only k that both keeps the 75-84 pair and clears "
            "precedent on both surfaces -- the same finding as gate_m4's, "
            "reached on a different module (packet section 2.3, confirmed "
            "by referee A section 4.2 and here from the v3 bytes)"
        ),
    }


# --------------------------------------------------------------------------
# R5 -- anchor checks and the anchor operating characteristic
# --------------------------------------------------------------------------
def _dominance(h: dict[str, float], band: str) -> float | None:
    m, f = h.get(f"{band}|male", 0.0), h.get(f"{band}|female", 0.0)
    return math.log(m / f) if m > 0 and f > 0 else None


def _min_gradient(h: dict[str, float], sex: str, bands: tuple[str, ...]):
    gaps = []
    for lo, hi in zip(bands[:-1], bands[1:], strict=True):
        a, b = h.get(f"{lo}|{sex}", 0.0), h.get(f"{hi}|{sex}", 0.0)
        if a <= 0 or b <= 0:
            return None
        gaps.append(math.log(b / a))
    return min(gaps)


def _margin_block(
    full_value: float, half_values: list[float | None]
) -> dict[str, Any]:
    vals = np.array(
        [v for v in half_values if v is not None], dtype=np.float64
    )
    sd = float(vals.std(ddof=1))
    return {
        "n_halves_scored": int(vals.size),
        "n_halves_offered": len(half_values),
        "real_full_panel_min": float(full_value),
        "half_split_mean": float(vals.mean()),
        "half_split_sd": sd,
        "min_over_halves": float(vals.min()),
        "holds_on_every_half": bool(vals.min() > 0),
        "margin_sigma_units": round(full_value / sd, 3),
        "clears_margin_k": bool(full_value / sd >= MARGIN_K),
    }


def anchor_checks(
    per_seed: list[dict[str, Any]], full_h: dict[str, float]
) -> dict[str, Any]:
    """The dominance and age-gradient invariants under both half
    conventions, recomputed from the per-seed hazard vectors."""
    side_a = [s["hazards_side_a"] for s in per_seed]
    both = [
        h for s in per_seed for h in (s["hazards_side_a"], s["hazards_side_b"])
    ]
    out: dict[str, Any] = {}
    for label, band_set in (
        ("sex_dominance.male_exceeds_female", DOMINANCE_BAND_SET),
        ("sex_dominance.five_band_alternative", FIVE_BAND_SET),
    ):

        def stat(h: dict[str, float], band_set=band_set) -> float | None:
            vals = [_dominance(h, b) for b in band_set]
            return None if any(v is None for v in vals) else min(vals)

        full = stat(full_h)
        out[label] = {
            "statistic": (
                "min over the contiguous band set of ln(m_male / m_female); "
                "level-free, so the PSID undercount does not touch it"
            ),
            "band_set": list(band_set),
            "side_a": _margin_block(full, [stat(h) for h in side_a]),
            "both_sides": _margin_block(full, [stat(h) for h in both]),
        }
    for sex in v1b.SEXES:

        def gstat(h: dict[str, float], sex=sex) -> float | None:
            return _min_gradient(h, sex, GRADIENT_BAND_SET)

        full = gstat(full_h)
        out[f"age_gradient.comonotone|{sex}"] = {
            "statistic": (
                "the weighted hazard rises strictly across "
                f"{' < '.join(GRADIENT_BAND_SET)}, scored as the MIN ADJACENT "
                "LOG GAP over those bands"
            ),
            "band_set": list(GRADIENT_BAND_SET),
            "side_a": _margin_block(full, [gstat(h) for h in side_a]),
            "both_sides": _margin_block(full, [gstat(h) for h in both]),
            "v3_labels_this": (
                "companion evidence, NOT commissioned (anchor_invariants."
                "age_gradient_companion.commissioned = false); the packet's "
                "section-1 draft lists it as an anchor cell. Its "
                "commissioning is a ratifying-round confirmation, filed in "
                "open_questions_for_the_ceremony[R5]"
            ),
        }
    return out


def anchor_oc_row(margin_sigma: float, noise_ratio: float, candidate_k: float):
    """One row of the anchor OC: the candidate's statistic ~ N(model, (noise
    ratio x sigma)^2) must exceed candidate_k x sigma; a degenerate
    sex-flat candidate (statistic 0) is scored on the same rule."""
    p_seed = _normal_cdf((margin_sigma - candidate_k) / noise_ratio)
    p_c6 = _normal_cdf((0.0 - candidate_k) / noise_ratio)
    return {
        "faithful_p_seed": round(p_seed, 4),
        "faithful_p_gate_4_of_5": round(_gate_4_of_5(p_seed), 4),
        "sex_flat_c6_p_seed": round(p_c6, 4),
        "sex_flat_c6_p_gate_4_of_5": round(_gate_4_of_5(p_c6), 4),
    }


NOISE_SCENARIOS = {
    "draw_noise_only": {
        "noise_ratio": 1.0 / math.sqrt(CANDIDATE_DRAWS),
        "assumption": (
            "the candidate's model value equals the full-panel PSID value "
            "(exact for the accepted adapter's class, whose fitted level is "
            "the PSID level by the refit.py identity) and its per-seed "
            "side-A statistic carries only the Monte-Carlo noise of the "
            "K=20 draws: sigma / sqrt(20)"
        ),
    },
    "fitted_excluding_holdout": {
        "noise_ratio": math.sqrt(1.0 + 1.0 / CANDIDATE_DRAWS),
        "assumption": (
            "the candidate is fitted on the seed's complement half (the "
            "registration rule: fitting exclusions = the seed-s holdout "
            "persons), so its model value inherits side B's sampling noise "
            "sigma on top of the draw noise: sigma * sqrt(1 + 1/20)"
        ),
    },
}


def anchor_operating_characteristic(checks: dict[str, Any]) -> dict[str, Any]:
    """R5: referee A's OC recomputed, the remedies priced, a convention
    proposed. Nothing here is a ruling."""
    dom = checks["sex_dominance.male_exceeds_female"]
    five = checks["sex_dominance.five_band_alternative"]
    margins = {
        "headline_3_band_side_a": dom["side_a"]["margin_sigma_units"],
        "headline_3_band_both_sides": dom["both_sides"]["margin_sigma_units"],
        "five_band_side_a": five["side_a"]["margin_sigma_units"],
        "five_band_both_sides": five["both_sides"]["margin_sigma_units"],
        "gate_m4_weakest_anchor": 4.797,
    }
    inherited: dict[str, Any] = {}
    for mlabel, m in margins.items():
        inherited[mlabel] = {
            scen: anchor_oc_row(m, spec["noise_ratio"], MARGIN_K)
            for scen, spec in NOISE_SCENARIOS.items()
        }
    remedies: dict[str, Any] = {}
    for candidate_k, label in (
        (0, "a_bare_positivity_k0"),
        (1, "b_k1"),
        (2, "b_k2"),
    ):
        remedies[label] = {
            "candidate_side_k": candidate_k,
            "rule": (
                "the candidate's per-gate-seed statistic must exceed "
                f"{candidate_k} x the committed real half-split sd; the "
                f"MARGIN_K = {MARGIN_K} evidence-time condition (the REAL "
                "floor's margin) gates the CELL's eligibility, not the "
                "candidate (gate_m4 flip-note 3 separation, extended to the "
                "margin itself)"
                if candidate_k < MARGIN_K
                else "inherited"
            ),
            "by_margin": {
                mlabel: {
                    scen: anchor_oc_row(m, spec["noise_ratio"], candidate_k)
                    for scen, spec in NOISE_SCENARIOS.items()
                }
                for mlabel, m in margins.items()
                if mlabel.startswith("headline")
            },
        }
    remedies["c_demote_and_rename"] = {
        "rule": (
            "the sex-dominance anchor is REPORTED, not gated; the gate is "
            "renamed away from 'differential' (id mortality_reproduction) "
            "and every PASS statement says the sex differential is not "
            "certified, at covers prominence (the packet's "
            "differential_claim_requires_the_anchor clause fires)"
        ),
        "price": (
            "the internal surface's OC is unchanged (0.9868 on 4 cells / "
            "0.9975 on 2) and no rule with a thin margin remains; but C6 "
            "(sex-flat) becomes an UNCAUGHT degenerate of the whole gate, "
            "since every clearing cell's full-panel sex gap sits inside its "
            "own tolerance, and the module the gate certifies is no longer "
            "differential mortality"
        ),
    }
    return {
        "method": (
            "referee A section 4.5, recomputed here from the v3 per-seed "
            "hazard vectors: the candidate's per-gate-seed side-A statistic "
            "min_b ln(m_male,b / m_female,b) over the band set ~ N(model "
            "value, (noise_ratio x sigma)^2), sigma = the committed real "
            "half-split sd under the named half convention; the seed passes "
            "iff the statistic exceeds candidate_k x sigma; the gate passes "
            "iff >= 4 of 5 gate seeds. The faithful candidate's model value "
            "is the full-panel PSID value; the sex-flat degenerate's is 0."
        ),
        "margins_sigma_units": margins,
        "inherited_rule_margin_k_3_candidate_side": inherited,
        "referee_a_reported": REFEREE_A_ANCHOR_OC,
        "reading": (
            "under gate_m4's inherited rule (candidate margin >= 3 sigma) a "
            "faithful candidate passes the anchor cell with probability "
            f"{inherited['headline_3_band_side_a']['draw_noise_only']['faithful_p_gate_4_of_5']:.3f} / "
            f"{inherited['headline_3_band_both_sides']['draw_noise_only']['faithful_p_gate_4_of_5']:.3f} "
            "(side A / 200 halves) with draw noise only and "
            f"{inherited['headline_3_band_side_a']['fitted_excluding_holdout']['faithful_p_gate_4_of_5']:.3f} / "
            f"{inherited['headline_3_band_both_sides']['fitted_excluding_holdout']['faithful_p_gate_4_of_5']:.3f} "
            "when fitted excluding the holdout half; gate_m4's weakest anchor "
            "at 4.797 sigma gives >= 0.985 on the same computation. More "
            "draws do not cure it: the fitted-model noise sigma does not "
            "shrink with K"
        ),
        "remedies_priced": remedies,
        "half_convention_proposed": {
            "proposal": "both_sides",
            "why": (
                "(1) it is the STRICTER convention (sd 0.10111 > 0.09877; "
                "margin 3.066 < 3.139); (2) it is the convention under which "
                "the headline band set was SELECTED -- the 5-band set holds "
                "on all 100 side-A halves and fails on the 200 (one inversion "
                "at 35-44 on a B half), so selecting the band set on 200 "
                "halves and then pricing its margin on 100 would mix "
                "conventions; (3) 200 halves estimate the sd of a HALF's "
                "statistic from twice the draws, and both halves of a seed "
                "are equally valid halves of the panel. Its price is 0.073 "
                "sigma of margin. gate_m4's precedent is the side-A "
                "convention ('holds on all 100 real half-splits'); the "
                "evidence-time 'holds on every half' condition is kept under "
                "BOTH conventions here, so the precedent's non-parametric "
                "test is not weakened by the proposal"
            ),
            "the_alternative": (
                "side_a: gate_m4's literal precedent; margin 3.139; the "
                "5-band set would then be admissible at 3.047 sigma, which "
                "the both-sides scan rejects"
            ),
        },
        "status": "FILED and PRICED; the ruling is the referee round's",
    }


# --------------------------------------------------------------------------
# R11 -- the teeth table
# --------------------------------------------------------------------------
def teeth_table(
    full_window: dict[str, Any],
    stability: dict[str, Any],
    gated_4: list[str],
    anchor_oc: dict[str, Any],
) -> dict[str, Any]:
    """Degenerate candidates C1-C6 scored full-panel against the k=3
    tolerances on the 4-cell and the 2-cell surfaces."""
    by = full_window["by_band_sex"]
    full_h = {k: v["psid_m"] for k, v in by.items()}
    nchs = {k: v["nchs_M"] for k, v in by.items()}
    gated_2 = [c for c in gated_4 if not c.startswith("85+")]

    def pooled(sex: str | None) -> float:
        wd = sum(
            v["psid_deaths_wt"]
            for k, v in by.items()
            if sex is None or k.endswith(f"|{sex}")
        )
        we = sum(
            v["psid_exposure_py"]
            for k, v in by.items()
            if sex is None or k.endswith(f"|{sex}")
        )
        return wd / we

    def scores(cand: dict[str, float]) -> dict[str, float]:
        return {
            c: round(abs(math.log(cand[c] / full_h[c])), 3) for c in gated_4
        }

    candidates = {
        "c1_external_levels": {
            "candidate": (
                "the NCHS 2023 life-table band rates used directly as the "
                "hazard, no undercount adjustment"
            ),
            "hazard": {c: nchs[c] for c in gated_4},
        },
        "c2_age_flat_within_sex": {
            "candidate": (
                "one hazard per sex: the declared-window exposure-weighted "
                "pooled rate over all seven bands, per sex"
            ),
            "hazard": {c: pooled(c.split("|")[1]) for c in gated_4},
        },
        "c3_fully_flat": {
            "candidate": (
                "one hazard for everyone: the declared-window exposure-"
                "weighted pooled rate over all bands and both sexes"
            ),
            "hazard": {c: pooled(None) for c in gated_4},
        },
        "c4_uniform_level_plus_25pct": {
            "candidate": "every cell's PSID hazard x 1.25",
            "hazard": {c: full_h[c] * 1.25 for c in gated_4},
        },
        "c5_uniform_level_minus_25pct": {
            "candidate": "every cell's PSID hazard x 0.75",
            "hazard": {c: full_h[c] * 0.75 for c in gated_4},
        },
        "c6_sex_flat": {
            "candidate": "both sexes assigned the female PSID hazard of the band",
            "hazard": {
                c: full_h[f"{c.split('|')[0]}|female"] for c in gated_4
            },
        },
    }
    tol = {c: stability[c]["tolerance_k3"] for c in gated_4}
    rows: dict[str, Any] = {}
    for name, spec in candidates.items():
        sc = scores(spec["hazard"])
        fail_4 = sorted(c for c in gated_4 if sc[c] > tol[c])
        fail_2 = sorted(c for c in gated_2 if sc[c] > tol[c])
        rows[name] = {
            "candidate": spec["candidate"],
            "scores": sc,
            "tolerances": tol,
            "verdict_4_cell_surface": "FAIL" if fail_4 else "PASS",
            "failing_cells_4_cell": fail_4,
            "verdict_2_cell_surface_25_84": "FAIL" if fail_2 else "PASS",
            "failing_cells_2_cell": fail_2,
            "min_margin_to_failure_4_cell": round(
                min(tol[c] - sc[c] for c in gated_4), 3
            ),
        }
    rows["c4_uniform_level_plus_25pct"]["known_non_catch"] = True
    rows["c4_uniform_level_plus_25pct"]["reading"] = (
        "PASSES every gated internal cell on both surfaces: ln(1.25) = 0.223 "
        "is inside every clearing tolerance. The internal surface does NOT "
        "catch a uniform +25% level error. No anchor cell sees a level "
        "either (the invariants are level-free), so this is a non-catch of "
        "the WHOLE gate, stated as such."
    )
    rows["c5_uniform_level_minus_25pct"]["reading"] = (
        "|ln(0.75)| = 0.288 fails only 85+|female (0.246) and 85+|male "
        "(0.274) -- caught on the 4-cell surface by the 85+ cells alone, "
        "uncaught on the 2-cell surface. The R4 ruling decides whether a "
        "-25% level error is caught."
    )
    rows["c6_sex_flat"]["known_non_catch_of_the_internal_surface"] = True
    rows["c6_sex_flat"]["caught_by"] = "sex_dominance.male_exceeds_female"
    rows["c6_sex_flat"]["catch_attribution"] = (
        "PASSES every internal cell on both surfaces: each clearing cell's "
        "full-panel sex gap (75-84 0.321; 85+ 0.203) sits inside its own "
        "tolerance. The ONLY surface that sees it is the sex-dominance anchor, "
        "where its statistic is 0 against a required margin; under the "
        "inherited candidate-side rule (>= 3 sigma) it is caught with "
        "probability ~1, and under the bare-positivity remedy (a) only with "
        "probability 1 - 0.1875 = 0.8125 per gate run -- the anchor's OC "
        "beside the catch (anchor_operating_characteristic.remedies_priced)."
    )
    rows["c6_sex_flat"]["anchor_oc_beside_the_catch"] = {
        "inherited_rule": anchor_oc[
            "inherited_rule_margin_k_3_candidate_side"
        ]["headline_3_band_both_sides"],
        "remedy_a_bare_positivity": anchor_oc["remedies_priced"][
            "a_bare_positivity_k0"
        ]["by_margin"]["headline_3_band_both_sides"],
        "remedy_b_k1": anchor_oc["remedies_priced"]["b_k1"]["by_margin"][
            "headline_3_band_both_sides"
        ],
    }
    rows["c1_external_levels"]["reading"] = (
        "an external-levels candidate that ignores the PSID undercount "
        "entirely passes the 2-cell surface outright and fails the 4-cell "
        "surface only through 85+|female (0.250 vs 0.246, a 0.004 margin): "
        "the reproduction surface is nearly blind to the undercount, which "
        "is why LEVELS stay report-only and why the certification scope is "
        "interview-conditional."
    )
    return {
        "basis": (
            "full-panel scoring on the declared universe under the pinned "
            "convention (external_anchor.windows.declared_1997_plus of v3) "
            "against the k=3 tolerances -- an UPPER BOUND on teeth: per-seed "
            "side-A scoring adds floor noise and makes each verdict LESS "
            "likely to fail"
        ),
        "gated_4_cell_surface": gated_4,
        "gated_2_cell_surface_25_84": gated_2,
        "candidates": rows,
        "catch_structure": (
            "age-flat and fully-flat hazards FAIL internally by a wide margin "
            "(scores 1.2-2.7 against tolerances 0.25-0.38) -- the age "
            "gradient is decisively gated; a uniform +25% LEVEL error PASSES "
            "every internal cell and is caught by NOTHING (known non-catch); "
            "a uniform -25% level error is caught only by the 85+ cells (R4); "
            "external NCHS levels with no undercount adjustment pass the "
            "2-cell surface and fail the 4-cell surface by 0.004 at 85+|"
            "female; a SEX-FLAT candidate PASSES every internal cell (known "
            "non-catch of the internal surface) and is caught ONLY by the "
            "sex-dominance anchor, whose own operating characteristic is the "
            "R5 ruling. The k=3 internal surface alone must NEVER be "
            "described as certifying differential mortality."
        ),
        "known_non_catches": {
            "internal_surface": ["c4_uniform_level_plus_25pct", "c6_sex_flat"],
            "whole_gate": ["c4_uniform_level_plus_25pct"],
        },
    }


# --------------------------------------------------------------------------
# R4 -- 85+
# --------------------------------------------------------------------------
def r4_block(
    v3: dict[str, Any],
    stability: dict[str, Any],
    k_sel: dict[str, Any],
    bracket: dict[str, Any] | None,
) -> dict[str, Any]:
    blob = _git_blob(GATES_YAML_BLOB_AT_BINDING)
    live = GATES_PATH.read_text()
    lo, hi = GATES_YAML_27PCT_LINES
    live_lines = live.splitlines()
    quote_live = live_lines[lo - 1 : hi]
    quote_blob = (
        blob.decode("utf-8").splitlines()[lo - 1 : hi] if blob else None
    )
    by = v3["external_anchor"]["windows"][HEADLINE_UNIVERSE]["by_band_sex"]
    deaths_by_band = {
        b: sum(
            v["psid_deaths_unwt"]
            for k, v in by.items()
            if k.startswith(f"{b}|")
        )
        for b in v1b.BAND_LABELS
    }
    bands = list(v1b.BAND_LABELS)
    shares = {}
    for i, start in enumerate(bands[:-1]):
        pool = bands[i:]
        total = sum(deaths_by_band[b] for b in pool)
        shares[f"{start.split('-')[0]}+"] = {
            "pool_bands": pool,
            "events_unwt": total,
            "events_85plus": deaths_by_band["85+"],
            "share_from_85plus": round(deaths_by_band["85+"] / total, 4),
        }
    oc4 = k_sel["by_k"]["3"]["p_gate_incl_85plus"]
    oc2 = k_sel["by_k"]["3"]["p_gate_25_84"]
    return {
        "question": (
            "is 85+ gate-eligible for a REPRODUCTION gate, given gate_m6 "
            "partitions death.85+|{male,female} report-only under "
            "attrition_confounded_truth?"
        ),
        "item_1_the_27_percent": {
            "located": True,
            "where": f"gates.yaml:{lo}-{hi} (gate_m6.not_certified[0], margin mortality_drift)",
            "git_blob_at_binding": GATES_YAML_BLOB_AT_BINDING,
            "quoted_text_at_the_blob": quote_blob,
            "live_file_identical_to_blob_on_these_lines": quote_blob
            == quote_live,
            "which_quantity_it_is": (
                "gate_m6's statement is about 85+-INCLUSIVE POOLED RUNGS on "
                "gate_m6's TEMPORAL-HOLDOUT death surface (fit <= 2014, "
                "score 2015-2022; closed panel; HOUSEHOLD-disjoint mortality "
                "family): the share of such a pool's events that come from "
                "the 85+ stratum. Its computation is in NO committed artifact "
                "(packet limit 2; referee B: 0 hits in runs/m6_holdout_floors_v4.json, "
                "whose death ladder enumerates 25-84 rungs only)."
            ),
            "is_it_the_same_quantity_as_anything_here": False,
            "why_not": (
                "this artifact's surface is the person-disjoint half-split "
                "REPRODUCTION surface on the declared 1997-2021 start-wave "
                "universe (2,277 events), not gate_m6's 2015-2022 temporal "
                "holdout (308 events fully pooled). The nearest analogue on "
                "THIS frame is the 85+ share of every 85+-inclusive pool "
                "(shares_of_85plus_events_by_pool below): 25.1% for the "
                "fully pooled 25+ surface, 37.4% for 65+, 52.8% for 75+. "
                "Numerically near ~27% for the 25+ pool, but a different "
                "object; it neither confirms nor refutes gate_m6's figure."
            ),
            "shares_of_85plus_events_by_pool": shares,
            "disposition": (
                "the ~27% stays UNLOCATED in any committed artifact. Its "
                "production or withdrawal is a gate_m6 METADATA-ONLY "
                "amendment (the gate_m4 verification-round precedent, "
                "gates.yaml:3006-3016), owed by whoever next amends gate_m6; "
                "it is NOT this gate's block to edit and this sitting edits "
                "no gates.yaml byte. Filed in open_questions_for_the_ceremony[R4]."
            ),
        },
        "item_2_sensitivity_of_85plus_to_the_censoring_convention": (
            bracket
            if bracket is not None
            else {"status": "not computed (PSID not staged)"}
        ),
        "item_3_the_ruling_priced_both_ways": {
            "admit_85plus": {
                "surface": "4 internal cells {75-84, 85+} x {male, female}",
                "faithful_oc_p_gate": oc4,
                "tolerances": {
                    c: stability[c]["tolerance_k3"]
                    for c in ("85+|male", "85+|female")
                },
                "for": (
                    "gate_m4 finding 1's principle: a concept delta (here, "
                    "attrition confounding of the 85+ TRUTH) is a PSID-vs-"
                    "external property and never enters a candidate-vs-PSID "
                    "REPRODUCTION cell; both halves inherit the same confounded "
                    "truth and the half-split null is valid on the frame; the "
                    "85+ cells are the two tightest (0.274 / 0.246) and catch "
                    "the -25% level error and the external-levels candidate "
                    "that the 2-cell surface lets through (R11)"
                ),
                "against": (
                    "the censoring bracket at 85+ (+0.281 / +0.359 log) is "
                    "1.03x / 1.46x the cells' own tolerances: what a PASS "
                    "certifies is reproduction of a hazard whose LEVEL is set "
                    "by the censoring convention to within more than the "
                    "tolerance; gate_m6's standing machine reason for the same "
                    "stratum is attrition_confounded_truth; a gate whose "
                    "tightest cells sit on the least separable truth must say "
                    "so at covers prominence (certification_scope: "
                    "interview-conditional)"
                ),
            },
            "exclude_85plus": {
                "surface": "2 internal cells {75-84} x {male, female}",
                "faithful_oc_p_gate": oc2,
                "for": (
                    "consistency with gate_m6's partition reason for the same "
                    "stratum; the certification narrows to cells whose "
                    "censoring bracket (0.95-0.98x tolerance) is inside the "
                    "tolerance"
                ),
                "against": (
                    "the 2-cell surface is nearly blind to LEVELS: C1 "
                    "(external levels, no undercount adjustment) and C5 "
                    "(-25%) both PASS it (R11); the two 85+ cells carry the "
                    "largest event counts (215 / 357 declared deaths) and the "
                    "tightest floors on the whole surface"
                ),
            },
            "certification_scope_either_way": (
                "the gated hazard is the INTERVIEW-CONDITIONAL PSID hazard -- "
                "exposure ends at the last observed wave and deaths are "
                "counted only in the one interval after it -- not a "
                "population hazard; the undercount is part of the truth both "
                "sides inherit (v3 certification_scope, adopted from referee "
                "A section 3.4; carried into the draft block's "
                "certification_scope and not_certified)"
            ),
        },
        "status": "FILED and PRICED; the ruling is the referee round's",
    }


# --------------------------------------------------------------------------
# R9 -- the draw stream
# --------------------------------------------------------------------------
_RNG_PATTERNS = (
    re.compile(r"default_rng\(\s*(\d{3,})"),
    re.compile(r"default_rng\(\s*\[\s*(\d{3,})"),
    re.compile(r"_base:\s*(\d{3,})"),
    re.compile(r"\bseed:\s*(\d{3,})"),
    re.compile(r"\b(\d{4,})\s*\+\s*(?:k|seed)\b"),
)


def enumerate_gates_yaml_seed_bases(text: str) -> dict[str, list[int]]:
    """Every numeric rng base / seed gates.yaml names, with the lines."""
    found: dict[int, set[int]] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pat in _RNG_PATTERNS:
            for m in pat.finditer(line):
                found.setdefault(int(m.group(1)), set()).add(lineno)
    return {str(k): sorted(v) for k, v in sorted(found.items())}


def draw_stream_block(gates_text: str) -> dict[str, Any]:
    bases = enumerate_gates_yaml_seed_bases(gates_text)
    stream = list(range(DRAW_STREAM_BASE, DRAW_STREAM_BASE + CANDIDATE_DRAWS))
    occupied: set[int] = set()
    for b in bases:
        base = int(b)
        occupied.update(range(base, base + 100))
    occupied.update(FLOOR_SEEDS)
    occupied.update(GATE_SEEDS)
    occupied.update(range(20260906, 20260906 + 100))
    collisions = sorted(set(stream) & occupied)
    if collisions:
        raise RuntimeError(f"draw stream collides: {collisions}")
    return {
        "proposed_base": DRAW_STREAM_BASE,
        "candidate_draw_stream": (
            f"numpy.random.default_rng({DRAW_STREAM_BASE} + k), k=0..{CANDIDATE_DRAWS - 1}"
        ),
        "mnemonic": "issue #74 (Phase B, differential mortality) -> 7400 + k",
        "enters_gates_yaml": "ONLY at the flip; pinned here and bound by tests/test_gates_derivations.py",
        "every_seed_base_named_in_gates_yaml": bases,
        "also_distinct_from": {
            "split_seeds": "0-99 (floor_seeds; the person-disjoint split)",
            "gate_seeds": list(GATE_SEEDS),
            "floors_bootstrap_key": "numpy.random.default_rng([20260906, stream, cell_index]) (v2/v3 seed_count_stability)",
            "packet_bootstrap": "numpy.default_rng(20260906) (packet section 2.4, DRAFT-COMPUTED, not committed)",
        },
        "range_checked": f"{DRAW_STREAM_BASE}..{DRAW_STREAM_BASE + CANDIDATE_DRAWS - 1} against every base above extended by +0..99",
        "collisions": collisions,
        "distinct": not collisions,
        "gates_yaml_mentions_the_base_today": str(DRAW_STREAM_BASE) in bases,
    }


# --------------------------------------------------------------------------
# Referee A's additions (i) scoring frame, (ii) stability clause, (iii) flip
# --------------------------------------------------------------------------
def scoring_frame_definition() -> dict[str, Any]:
    return {
        "operational_definition": (
            "For gate seed s, the candidate's scoring frame IS the side-A "
            "person-interval exposure table: the slices of the pinned-"
            "convention frame (scripts/build_mortality_floors_v3.py "
            "build_convention_frames, pinned_narrow_midpoint) whose person "
            "is drawn to side A by populace_dynamics.harness.panel."
            "split_panel_by_person(full frame, 'person_id', fraction=0.5, "
            "seed=s), restricted AFTER the split to start waves >= 1997. "
            "That table -- person_id, sex, start-wave weight, age, band, "
            "start_wave, and the interval each slice belongs to -- is HANDED "
            "to the candidate. The candidate simulates, for each person-"
            "interval in it, whether the person dies in that interval and in "
            "which single-year slice; it may not add persons, intervals or "
            "exposure, and it may not carry a person's simulated survival "
            "past the person's last observed wave. Its hazard for a cell is "
            "m_candidate,s = sum(w * d_sim) / sum(w * exposure_sim) over the "
            "same slices, with exposure_sim formed by the SAME rule as the "
            "truth (the simulated death-year slice carries exposure 0.5 and "
            "one death; later slices in that interval carry nothing), and "
            "mbar_candidate,s is its mean over the K=20 registered draws."
        ),
        "deaths_counted_inside_those_intervals_only": True,
        "why_this_makes_binds_both_sides_operational": (
            "the censoring convention (exposure ends at the last observed "
            "wave; a death more than one grid interval later is never "
            "counted) and the ascertainment convention (narrow codes at the "
            "midpoint; the residue as survival) are properties of the FRAME, "
            "and the candidate is scored on the truth's frame, not on a frame "
            "of its own. A candidate that models deaths of attriters after "
            "their last wave earns nothing for them and loses nothing for "
            "them: those person-years are not in the table. This is what "
            "'the convention binds both sides' means, in operations "
            "(referee A section 6, addition (i))."
        ),
        "pad_row_exclusion": (
            "the registered mortality-exposure adapter emits two INVENTED "
            "age-coverage pad rows carrying person_id -1 (female) and -2 "
            "(male) (scripts/registered_m6_inputs.py PAD_IDENTITY_DISCLOSURE "
            "in the accepted adapter increment). They correspond to no PSID "
            "person, are absent from the floor frame (v3 data."
            "person_identity_check: min person_id 1001, no non-positive ids) "
            "and are EXCLUDED from the scoring frame; a run whose artifact "
            "does not evidence their exclusion is INVALID."
        ),
        "per_gate_seed_frame_sizes": "computed from PSID below (per_gate_seed)",
    }


def gate_seed_frames(
    pinned: pd.DataFrame, gated_4: list[str]
) -> dict[str, Any]:
    """The side-A scoring frame's size per gate seed, with a digest of the
    side-A person ids so a registration can be checked against it."""
    out: dict[str, Any] = {}
    for seed in GATE_SEEDS:
        side_a, _ = hpanel.split_panel_by_person(
            pinned, "person_id", fraction=0.5, seed=seed
        )
        ids = np.sort(side_a.person_id.unique())
        window = side_a[side_a.start_wave >= DECLARED_START]
        haz = v1b.weighted_hazards(window)
        out[str(seed)] = {
            "n_persons_side_a_full_frame": int(ids.size),
            "side_a_person_ids_sha256": hashlib.sha256(
                ",".join(str(int(i)) for i in ids).encode()
            ).hexdigest(),
            "n_persons_side_a_declared_window": int(
                window.person_id.nunique()
            ),
            "n_slices_declared_window": int(len(window)),
            "weighted_exposure_py_declared_window": float(
                (window.weight * window.exposure).sum()
            ),
            "deaths_unwt_declared_window": int(
                round(float(window.death.sum()))
            ),
            "gated_cells": {
                c: {
                    "psid_m_side_a": haz[c]["psid_m"],
                    "exposure_py_side_a": haz[c]["psid_exposure_py"],
                    "deaths_unwt_side_a": haz[c]["psid_deaths_unwt"],
                }
                for c in gated_4
            },
        }
    return out


def stability_clause(
    stability: dict[str, Any], cells: list[str]
) -> dict[str, Any]:
    in_band = sorted(
        c for c in cells if stability[c]["bootstrap_in_stability_band"]
    )
    clearing = sorted(c for c in cells if stability[c]["clears_t_max_at_k3"])
    would_demote = sorted(set(in_band) & set(clearing))
    nearest = min(
        (c for c in clearing),
        key=lambda c: stability[c][
            "bootstrap_p_tolerance_at_or_below_t_max_100_seeds"
        ],
    )
    return {
        "clause_proposed": (
            "a cell whose bootstrap P(T(k=3) <= T_max) at its own realized "
            f"sigma, at 100 seeds, lies in [{STABILITY_BAND[0]}, {STABILITY_BAND[1]}] "
            "is REPORT-ONLY whatever its point tolerance (referee A section "
            "4.3 / finding (iii)); the probability is the v3 seed_count_"
            "stability block's, rng numpy.random.default_rng([20260906, 3, "
            "cell_index]), 20,000 draws"
        ),
        "source": REFEREE_A_REPORT
        + ", section 4.3 and verdict lower-severity list",
        "cells_in_band_today": {
            c: stability[c][
                "bootstrap_p_tolerance_at_or_below_t_max_100_seeds"
            ]
            for c in in_band
        },
        "clearing_cells_the_clause_would_demote_today": would_demote,
        "changes_nothing_today": not would_demote,
        "nearest_clearing_cell_to_the_band": {
            "cell": nearest,
            "p": stability[nearest][
                "bootstrap_p_tolerance_at_or_below_t_max_100_seeds"
            ],
            "distance_to_upper_edge": round(
                stability[nearest][
                    "bootstrap_p_tolerance_at_or_below_t_max_100_seeds"
                ]
                - STABILITY_BAND[1],
                4,
            ),
        },
        "priced": {
            "adopt_the_clause": (
                "removes the flip risk on the two 65-74 cells (P 0.443 / "
                "0.605) for any future rebuild under a changed convention at "
                "no cost today; its cost is that a clearing cell drifting "
                "into the band on a rebuild (75-84|female sits at 0.9456, "
                "0.046 above the band's edge) would be demoted on the "
                "clause, not on its point tolerance -- a pre-registered "
                "rule, so no self-rescue question arises"
            ),
            "decide_at_1000_seeds": (
                "a 1,000-seed rebuild of the headline block (~46 s at "
                "referee A's 4.6 s per 100 seeds) narrows the 65-74 cells' "
                "tolerance distribution by sqrt(10) and would settle their "
                "status by measurement; its cost is a NEW floor artifact "
                "(the derivation basis moves from v3), a fresh verification "
                "round, and a floor_seeds departure from the gate_m4 / "
                "gate_m6 precedent (0-99) that must itself be pre-registered. "
                "This sitting's contract is that no floor number moves, so it "
                "is priced, not done"
            ),
        },
        "status": "FILED and PRICED; not adopted here",
    }


def flip_plan() -> dict[str, Any]:
    return {
        "rule": (
            "the commit that inserts the gate_mortality block into gates.yaml "
            "(under `gates:`, after gate_m6) flips GATE_MORTALITY_BLOCK_LANDED "
            "from False to True in EVERY file that carries it, IN THE SAME "
            "COMMIT, and changes nothing else in those files (the gate_m6 "
            "flip precedent 4b75147: named guard-test inversions in one "
            "commit; the v3 pre-lock-guard precedent: one constant, no test "
            "deleted)"
        ),
        "marker": "GATE_MORTALITY_BLOCK_LANDED",
        "files_carrying_the_marker": [
            "tests/test_mortality_floors_v2.py",
            "tests/test_mortality_floors_v3.py",
            "tests/test_gates_derivations.py",
            "tests/test_mortality_gate_floors_v1.py",
        ],
        "what_flips_with_it": [
            "tests/test_gates_derivations.py: _gate_mortality_block() reads "
            "the LIVE gates.yaml block instead of the artifact's draft "
            "fragment, so every derivation binding runs against the live "
            "contract (LOCKED-HOT, the 2a lesson); the pre-lock guard inverts "
            "to assert the block exists and cites runs/mortality_gate_floors_v1.json",
            "tests/test_gates_derivations.py "
            "test_gate_m4_flip_leaves_locked_siblings_byte_identical and "
            "tests/test_gate_w1_derivations.py (:1223) must admit "
            "{'gate_mortality'} as a sole added key while the flip PR is open "
            "(the gate_w1 / gate_m6 tolerance form)",
            "gates.yaml: floor_run_sha256 replaces the <FILLED AT "
            "RATIFICATION> placeholder with the sha256 of "
            "runs/mortality_gate_floors_v1.json AS RATIFIED; every <RULING ...> "
            "placeholder is replaced by the ratifying round's text; status "
            "-> locked; locked -> true; a history entry is added",
            "tests/tier_counts.json and tests/README-tiers.md re-refreshed by "
            "LIVE collection (gate_m4 flip-note 1)",
        ],
        "verified_shape": (
            "the v4 verification simulated the v2/v3 marker flip in a clone: "
            "one failure per file pre-flip (the guard), 74 / 44 green "
            "post-flip with the block under `gates:` (verification report "
            "section 1, simulations 1-2)"
        ),
    }


# --------------------------------------------------------------------------
# PSID-dependent blocks: R10 and the censoring bracket
# --------------------------------------------------------------------------
def restricted_split_perturbation(
    pinned: pd.DataFrame, committed_stability: dict[str, Any], verbose: bool
) -> dict[str, Any]:
    """R10: the same 100 seeds with the frame restricted to 25-84 BEFORE
    the split, beside the pinned full-frame-before-split convention."""
    started = time.time()
    restricted = pinned[pinned.band.isin(BANDS_25_84)].reset_index(drop=True)
    per_seed_restricted = [
        v3b.measure_seed(
            s, restricted, start_year_min=DECLARED_START, full=False
        )
        for s in FLOOR_SEEDS
    ]
    floor_r, stab_r = v3b.pool_floor(per_seed_restricted)
    per_seed_full = [
        v3b.measure_seed(s, pinned, start_year_min=DECLARED_START, full=False)
        for s in FLOOR_SEEDS
    ]
    floor_f, stab_f = v3b.pool_floor(per_seed_full)
    cells = list(BANDS_25_84)
    per_cell: dict[str, Any] = {}
    for band in cells:
        for sex in v1b.SEXES:
            key = f"{band}|{sex}"
            per_cell[key] = {
                "full_frame_before_split": {
                    "tolerance_k3": stab_f[key]["tolerance_k3"],
                    "mean": floor_f[key]["mean"],
                    "sd": floor_f[key]["sd"],
                    "clears_t_max_at_k3": stab_f[key]["clears_t_max_at_k3"],
                    "equals_committed_v3": bool(
                        stab_f[key]["tolerance_k3"]
                        == committed_stability[key]["tolerance_k3"]
                    ),
                },
                "restricted_25_84_before_split": {
                    "tolerance_k3": stab_r[key]["tolerance_k3"],
                    "mean": floor_r[key]["mean"],
                    "sd": floor_r[key]["sd"],
                    "realized_sigma": floor_r[key]["realized_sigma"],
                    "clears_t_max_at_k3": stab_r[key]["clears_t_max_at_k3"],
                    "min_deaths_either_half": stab_r[key][
                        "min_deaths_either_half"
                    ],
                    "values": floor_r[key]["values"],
                },
                "delta_tolerance_k3_restricted_minus_full": round(
                    stab_r[key]["tolerance_k3"] - stab_f[key]["tolerance_k3"],
                    3,
                ),
            }
    if not all(
        v["full_frame_before_split"]["equals_committed_v3"]
        for v in per_cell.values()
    ):
        raise RuntimeError(
            "the full-frame recompute does not equal the committed v3 floor"
        )
    knife = per_cell["75-84|male"]
    clearing_r = sorted(
        k
        for k, v in per_cell.items()
        if v["restricted_25_84_before_split"]["clears_t_max_at_k3"]
    )
    clearing_f = sorted(
        k
        for k, v in per_cell.items()
        if v["full_frame_before_split"]["clears_t_max_at_k3"]
    )
    n_persons_r = int(restricted.person_id.nunique())
    if verbose:
        print(
            f"  R10 restricted split: {time.time() - started:.1f}s; 75-84|male "
            f"full {knife['full_frame_before_split']['tolerance_k3']} vs restricted "
            f"{knife['restricted_25_84_before_split']['tolerance_k3']}; clearing "
            f"full {clearing_f} restricted {clearing_r}"
        )
    return {
        "question": (
            "does restricting the frame to ages 25-84 BEFORE "
            "split_panel_by_person move the tolerances, and does the "
            "knife-edge cell survive the pinned convention?"
        ),
        "pinned_convention": (
            "FULL frame before the split (every age, every start wave), the "
            "window filter applied to each side afterwards -- v1/v2/v3's "
            "convention, v3 internal_noise_floor.split_frame_pin, the "
            "derivation basis of every threshold here"
        ),
        "perturbation": (
            "the pinned-convention frame restricted to band in 25-34..75-84 "
            "(the 85+ slices and no others removed) BEFORE the split, seeds "
            "0-99, declared universe; split_panel_by_person draws on the "
            "sorted unique person ids, so removing persons who carry only "
            "85+ slices re-deals every person's side"
        ),
        "n_persons_full_frame": int(pinned.person_id.nunique()),
        "n_persons_restricted_frame": n_persons_r,
        "per_cell": per_cell,
        "clearing_set_k3_full_frame": clearing_f,
        "clearing_set_k3_restricted": clearing_r,
        "knife_edge_cell": {
            "cell": "75-84|male",
            "tolerance_k3_full_frame_before_split": knife[
                "full_frame_before_split"
            ]["tolerance_k3"],
            "tolerance_k3_restricted_25_84_before_split": knife[
                "restricted_25_84_before_split"
            ]["tolerance_k3"],
            "t_max": T_MAX,
            "packet_figures_at_v1_survival_convention": {
                "restricted": 0.405,
                "full": 0.335,
            },
            "reading": (
                "the packet's knife edge (0.405 vs a cap of 0.4055 at v1's "
                "survival convention) is recomputed here under the pinned "
                "convention on the declared universe; both figures are "
                "published so the sensitivity is visible. The bound threshold "
                "is the full-frame one; a test in tests/test_gates_derivations.py "
                "fails if the builder's split convention changes"
            ),
        },
        "seconds": round(time.time() - started, 1),
    }


def censoring_extension_bracket(
    demo: pd.DataFrame,
    dr: pd.DataFrame,
    pinned: pd.DataFrame,
    nchs_rates: dict[str, float],
    stability: dict[str, Any],
    cells: list[str],
    verbose: bool,
) -> dict[str, Any]:
    """Referee A section 3.4, recomputed: credit the exact decedents the
    inherited rule right-censors with exposure from the missed wave to the
    death year, and count the death; the two conventions bracket the truth
    because attriting SURVIVORS' exposure is unknown (this variant
    overstates the hazard)."""
    started = time.time()
    _, next_wave = v3b._grid(demo)
    obs = v3b._observed_frame(demo, dr)
    last = v3b.last_observed(obs, next_wave)
    exact = (
        dr[dr.death_status == "exact"]
        .set_index("person_id")[["death_year"]]
        .join(last, how="inner")
    )
    exact = exact[exact.next_wave.notna()].copy()
    exact["death_year"] = exact.death_year.astype(int)
    exact["next_wave"] = exact.next_wave.astype(int)
    missed = exact[exact.death_year >= exact.next_wave]
    rows = []
    for pid, r in missed.iterrows():
        for year in range(int(r.next_wave), int(r.death_year) + 1):
            is_death = year == int(r.death_year)
            rows.append(
                (
                    int(pid),
                    r.sex,
                    float(r.weight),
                    int(r.age) + (year - int(r.last_wave)),
                    int(r.last_wave),
                    0.5 if is_death else 1.0,
                    1.0 if is_death else 0.0,
                    int(r.next_wave),
                    int(r.death_year),
                )
            )
    ext = pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "sex",
            "weight",
            "age",
            "start_wave",
            "exposure",
            "death",
            "next_wave",
            "death_year",
        ],
    )
    ext["band"] = ext.age.map(v1b._band_of)
    ext = ext[ext.band.notna()].reset_index(drop=True)
    pinned_window = pinned[pinned.start_wave >= DECLARED_START]
    h_pin = v1b.weighted_hazards(pinned_window)
    variants = {
        "unlimited": ext,
        "le_one_more_grid_interval": ext[ext.death_year < ext.next_wave + 2],
    }
    out_variants: dict[str, Any] = {}
    for name, e in variants.items():
        e_window = e[e.start_wave >= DECLARED_START]
        both = pd.concat(
            [
                pinned_window[
                    [
                        "person_id",
                        "sex",
                        "weight",
                        "age",
                        "band",
                        "start_wave",
                        "exposure",
                        "death",
                    ]
                ],
                e_window[
                    [
                        "person_id",
                        "sex",
                        "weight",
                        "age",
                        "band",
                        "start_wave",
                        "exposure",
                        "death",
                    ]
                ],
            ],
            ignore_index=True,
        )
        h_ext = v1b.weighted_hazards(both)
        per_cell: dict[str, Any] = {}
        ratios = []
        for c in cells:
            lr = math.log(h_ext[c]["psid_m"] / h_pin[c]["psid_m"])
            tol = stability[c]["tolerance_k3"]
            ratios.append(h_ext[c]["psid_m"] / nchs_rates[c])
            per_cell[c] = {
                "ln_m_extended_over_m_pinned": round(lr, 6),
                "tolerance_k3_pinned": tol,
                "bracket_over_tolerance_k3": round(lr / tol, 4),
                "psid_over_nchs_pinned": round(
                    h_pin[c]["psid_m"] / nchs_rates[c], 6
                ),
                "psid_over_nchs_extended": round(
                    h_ext[c]["psid_m"] / nchs_rates[c], 6
                ),
                "exceeds_own_tolerance": bool(lr > tol),
            }
        out_variants[name] = {
            "added_death_events_declared_window": int(
                round(float(e_window.death.sum()))
            ),
            "added_slices_declared_window": int(len(e_window)),
            "pinned_death_events_declared_window": int(
                round(float(pinned_window.death.sum()))
            ),
            "psid_over_nchs_extended_summary": {
                "min": round(min(ratios), 6),
                "max": round(max(ratios), 6),
                "median": round(float(np.median(ratios)), 6),
            },
            "per_cell": per_cell,
            "range_of_ln_movement": {
                "min": round(
                    min(
                        v["ln_m_extended_over_m_pinned"]
                        for v in per_cell.values()
                    ),
                    3,
                ),
                "max": round(
                    max(
                        v["ln_m_extended_over_m_pinned"]
                        for v in per_cell.values()
                    ),
                    3,
                ),
            },
            "cells_where_the_bracket_exceeds_the_tolerance": sorted(
                c for c, v in per_cell.items() if v["exceeds_own_tolerance"]
            ),
        }
    ref_diff = {
        "unlimited": max(
            abs(
                out_variants["unlimited"]["per_cell"][c][
                    "ln_m_extended_over_m_pinned"
                ]
                - REFEREE_A_BRACKET_UNLIMITED[c]
            )
            for c in cells
        ),
        "le_one_more_grid_interval": max(
            abs(
                out_variants["le_one_more_grid_interval"]["per_cell"][c][
                    "ln_m_extended_over_m_pinned"
                ]
                - REFEREE_A_BRACKET_LE_ONE_INTERVAL[c]
            )
            for c in cells
        ),
    }
    gap = missed.death_year - missed.next_wave
    if verbose:
        print(
            f"  censoring bracket: {time.time() - started:.1f}s; missed {len(missed)}; "
            f"unlimited +{out_variants['unlimited']['added_death_events_declared_window']} "
            f"median ratio {out_variants['unlimited']['psid_over_nchs_extended_summary']['median']:.3f}; "
            f"max |diff vs A| {ref_diff}"
        )
    return {
        "report_only": True,
        "gates_nothing": True,
        "method": (
            "referee A section 3.4, recomputed by this builder: exact "
            "decedents whose death year is at or after the grid wave "
            "following their last observed wave (right-censored by the "
            "inherited rule) are credited single-year exposure from the "
            "missed wave to the death year, ages advancing from the last-wave "
            "age, the last-wave weight, start_wave = the last observed wave "
            "(so the declared window keeps those whose last wave is 1997+); "
            "the death-year slice carries exposure 0.5 and one death. "
            "Because attriting SURVIVORS' exposure is unknown, the extended "
            "convention OVERSTATES the hazard; the pinned and the extended "
            "conventions bracket the truth"
        ),
        "missed_exact_decedents": int(len(missed)),
        "missed_exact_decedents_last_wave_1997_plus": int(
            (missed.last_wave >= DECLARED_START).sum()
        ),
        "years_after_the_missed_wave": {
            "mean": round(float(gap.mean()), 3),
            "median": float(gap.median()),
            "p90": float(gap.quantile(0.9)),
        },
        "variants": out_variants,
        "referee_a_reported": {
            "unlimited": REFEREE_A_BRACKET_UNLIMITED,
            "le_one_more_grid_interval": REFEREE_A_BRACKET_LE_ONE_INTERVAL,
            "totals": REFEREE_A_BRACKET_TOTALS,
            "max_abs_difference_ln_vs_this_builder": {
                k: round(v, 6) for k, v in ref_diff.items()
            },
        },
        "reading": (
            "the censoring convention, not the ascertainment convention, "
            "sets the LEVEL: crediting known deaths after attrition moves "
            "every declared-universe hazard by roughly +0.27 to +0.74 log "
            "(the R6 convention moves them by <= 0.030) and takes the "
            "PSID/NCHS median from 0.760 to ~1.04. For the two 85+ cells the "
            "bracket EXCEEDS the cell's own k=3 tolerance; for 75-84 it is "
            "0.95-0.98 of it. Not a bar to a REPRODUCTION gate (both sides "
            "inherit the same rule; the half-split null is valid on the "
            "frame), but the number the R4 ruling was asked to have"
        ),
        "seconds": round(time.time() - started, 1),
    }


# --------------------------------------------------------------------------
# R12 -- wording audit
# --------------------------------------------------------------------------
COVERS_PROMINENCE_CHECKLIST = [
    {
        "item": "no drift",
        "required_phrases": ["certifies NOTHING about mortality DRIFT"],
        "source": "referee B section 6; gate_m6.not_certified[0] stands",
    },
    {
        "item": "no NCHS levels",
        "required_phrases": [
            "NOTHING about mortality LEVELS against NCHS",
            "no external mortality LEVEL is gated",
        ],
        "source": "referee B section 6; gates.yaml:5737-5740",
    },
    {
        "item": "no survival to claiming ages (R8 deferred)",
        "required_phrases": ["SURVIVAL TO CLAIMING AGES", "R8", "DEFERRED"],
        "source": "referee B section 6; v3 certification_scope.headline",
    },
    {
        "item": "nothing on 25-74",
        "required_phrases": ["NOTHING about the 25-74 cells"],
        "source": "referee B section 6; the 65-74 cells are coin flips",
    },
    {
        "item": "conventions bind both sides; the undercount is part of the truth",
        "required_phrases": [
            "bind BOTH SIDES",
            "undercount is part of the truth",
        ],
        "source": "referee B section 6; v3 governance.*.binds",
    },
    {
        "item": "person-disjoint split, differing from gate_m6's household-disjoint mortality family",
        "required_phrases": [
            "PERSON-DISJOINT",
            "HOUSEHOLD-DISJOINT",
            "gate_m6",
        ],
        "source": "referee B section 6; gates.yaml:5534 split_units",
    },
    {
        "item": "the band is the truth's disclosed uncertainty, never a second scoring rule",
        "required_phrases": [
            "disclosed uncertainty of the truth, never a second scoring rule"
        ],
        "source": "referee B section 6; v3 governance.death_ascertainment.binds_both_sides",
    },
    {
        "item": "start waves 1997-2021, never 1997-2023",
        "required_phrases": ["1997-2021"],
        "forbidden_phrases": ["1997-2023", "1997–2023", "1997—2023"],
        "source": "referee B D-9 / referee A D3",
    },
    {
        "item": "the upper end never called the packet's literal extreme",
        "required_phrases": ["RESIDUE-LITERAL", "TRULY LITERAL"],
        "forbidden_phrases": ["packet's literal extreme", "packet-literal"],
        "source": "referee B D-2; verification section 2",
    },
]


def normalized(text: str) -> str:
    """Whitespace-collapsed text: the phrase checks must not depend on
    where a folded YAML scalar breaks its lines."""
    return " ".join(text.split())


def wording_audit(
    fragment: str, artifact_json_without_audit: str
) -> dict[str, Any]:
    flat = normalized(fragment)
    low_f = flat.lower()
    low_a = normalized(artifact_json_without_audit).lower()
    forbidden = {
        w: {
            "fragment": low_f.count(w),
            "artifact_excluding_this_block": low_a.count(w),
        }
        for w in FORBIDDEN_WORDS
    }
    checklist = []
    for item in COVERS_PROMINENCE_CHECKLIST:
        present = {p: (p in flat) for p in item["required_phrases"]}
        absent = {
            p: (p not in flat) for p in item.get("forbidden_phrases", [])
        }
        checklist.append(
            {
                **item,
                "required_present": present,
                "forbidden_absent": absent,
                "holds": all(present.values()) and all(absent.values()),
            }
        )
    audit = {
        "scope": (
            "the draft gate_mortality block (draft_gates_yaml_fragment.text) "
            "and this artifact's JSON with this audit block removed. The PR "
            "body does not exist yet (no PR is opened by this sitting); its "
            "audit is owed by the verification round at PR time, with the "
            "same word list"
        ),
        "forbidden_word_counts": forbidden,
        "forbidden_words_absent_from_fragment": all(
            v["fragment"] == 0 for v in forbidden.values()
        ),
        "forbidden_words_absent_from_artifact": all(
            v["artifact_excluding_this_block"] == 0 for v in forbidden.values()
        ),
        "circularity_disclosure_present": "circularity_disclosure" in fragment,
        "covers_prominence": checklist,
        "all_covers_prominence_items_hold": all(c["holds"] for c in checklist),
    }
    return audit


# --------------------------------------------------------------------------
# The DRAFT block
# --------------------------------------------------------------------------
def _fmt(x: float, nd: int = 5) -> str:
    return f"{x:.{nd}f}"


def draft_fragment(
    stability: dict[str, Any],
    floor: dict[str, Any],
    partition: dict[str, Any],
    k_sel: dict[str, Any],
    oc4: dict[str, Any],
    oc2: dict[str, Any],
    checks: dict[str, Any],
    anchor_oc: dict[str, Any],
    teeth: dict[str, Any],
    r10: dict[str, Any] | None,
    bracket: dict[str, Any] | None,
    v3: dict[str, Any],
) -> str:
    """The gate_mortality block as YAML text (2-space indent under
    ``gates:``), the packet's section-1 draft updated to these bytes."""
    g = gate_cell
    t = {c: stability[c]["tolerance_k3"] for c in stability}
    dom = checks["sex_dominance.male_exceeds_female"]
    five = checks["sex_dominance.five_band_alternative"]
    gm = checks["age_gradient.comonotone|male"]
    gf = checks["age_gradient.comonotone|female"]
    inh = anchor_oc["inherited_rule_margin_k_3_candidate_side"]
    rem = anchor_oc["remedies_priced"]
    knife_r = (
        r10["knife_edge_cell"]["tolerance_k3_restricted_25_84_before_split"]
        if r10
        else "<PSID>"
    )
    knife_f = t["75-84|male"]
    br = bracket["variants"]["unlimited"]["per_cell"] if bracket else None
    br_txt = (
        f"+{br['85+|male']['ln_m_extended_over_m_pinned']:.3f} / "
        f"+{br['85+|female']['ln_m_extended_over_m_pinned']:.3f} log "
        f"({br['85+|male']['bracket_over_tolerance_k3']:.2f}x / "
        f"{br['85+|female']['bracket_over_tolerance_k3']:.2f}x the k=3 tolerances)"
        if br
        else "+0.281 / +0.359 log (1.03x / 1.46x the k=3 tolerances; referee A section 3.4)"
    )
    report_only = partition["report_only"]
    ro_lines = "\n".join(
        f'        - "{g(c)}"   # {t[c]:.3f} ; {stability[c]["report_reason_kish"]}; '
        f'unweighted min {stability[c]["min_deaths_either_half_unweighted"]}, '
        f'Kish {stability[c]["min_effective_deaths_kish"]}'
        for c in report_only
    )
    n_gated_internal = len(partition["internal_gate_eligible"])
    k_by = k_sel["by_k"]

    def _by_k_line(k: str) -> str:
        b = k_by[k]
        return (
            f'          "{k}": {{ n_cells_25_84: {b["n_cells_25_84"]}, '
            f'p_gate_25_84: {b["p_gate_25_84"] if b["p_gate_25_84"] is not None else "null"}, '
            f'n_cells_incl_85plus: {b["n_cells_incl_85plus"]}, '
            f'p_gate_incl_85plus: {b["p_gate_incl_85plus"] if b["p_gate_incl_85plus"] is not None else "null"} }}'
        )

    def _cell_rule(c: str) -> str:
        return f'                "{g(c)}": {{ key: "{c}", k: 3, rounding: 3, quantity_type: flow }}'

    def _cell_tol(c: str) -> str:
        f = floor[c]
        return (
            f'              "{g(c)}": {t[c]:.3f}   # floor mean {_fmt(f["mean"])}, '
            f'sd {_fmt(f["sd"])}, sigma {_fmt(f["realized_sigma"])}, '
            f'T/sigma {stability[c]["tolerance_sigma_units_k3"]}'
        )

    text = f"""  gate_mortality:
    # DRAFT -- NOT APPLIED TO gates.yaml. Emitted by
    # scripts/build_mortality_gate_floors_v1.py into
    # runs/mortality_gate_floors_v1.json (draft_gates_yaml_fragment.text) at
    # the threshold-binding sitting of 2026-09-07 (the packet's ceremony
    # step 3). Every number below is machine-derived from the VERIFIED floor
    # basis runs/mortality_floors_v3.json (2,711,564 B, sha256
    # {SOURCE_FLOOR_COMMITTED[1][:16]}...) and bound by
    # tests/test_gates_derivations.py; nothing is typed. Ceremony order:
    # floors -> THIS BINDING -> adversarial referee round -> verification ->
    # ratifying merge (issue #74 Phase B, comment 4907496891). Every
    # "<RULING ...>" placeholder is an open question the ratifying round
    # must fill; the options and their prices are in the artifact's
    # open_questions_for_the_ceremony. Until then every number is DRAFT.
    id: mortality_differential   # <RULING R5: 'differential' only while sex_dominance.male_exceeds_female is GATED; else mortality_reproduction>
    status: draft_pending_referee_round
    locked: false
    kind: anchor_based
    covers: >-
      the DIFFERENTIAL-MORTALITY module (issue #74 Phase B): the person-
      disjoint 50/50 half-split REPRODUCTION of the weighted PSID central
      death rate m(age band x sex) = sum(w * death) / sum(w * exposure) on
      the person-interval exposure of the demographic panel, on the
      declared weight universe (CORE/IMM INDIVIDUAL CROSS-SECTION WT,
      interval start waves 1997-2021; intervals ending by 2023), under the
      pinned narrow-midpoint ascertainment convention and the declared
      censoring rule, in <RULING R4: {n_gated_internal} | 2> internal cells
      ({{75-84<RULING R4: , 85+>}} x {{male, female}}), plus <RULING R5: the
      sex-DOMINANCE anchor over 45-54..65-74 and> the age-gradient SHAPE
      anchors over 55+ per sex. The gate is ANCHOR-BASED (gate_m4 style):
      the PSID mortality UNDERCOUNT (median PSID/NCHS ratio 0.760 on the
      declared universe) forbids gating a PSID LEVEL against an NCHS
      LEVEL, so the external-facing surface is concept-bridged SHAPE and
      DOMINANCE only; the undercount does NOT touch a candidate-vs-PSID
      REPRODUCTION cell, so the half-split floor gates the reproduction
      cells directly (the gate_m4 finding-1 principle). The scored surface
      is EXACTLY the cells enumerated in internal_surface + anchor_surface;
      no external mortality LEVEL is gated anywhere. A PASS certifies
      NOTHING about mortality DRIFT, NOTHING about mortality LEVELS against
      NCHS, NOTHING about SURVIVAL TO CLAIMING AGES (R8 -- DEFERRED) and
      NOTHING about the 25-74 cells, at this same prominence (see
      not_certified). The gated hazard is the INTERVIEW-CONDITIONAL PSID
      hazard, not a population hazard.
    # ---- the negative surface, at covers prominence (gate_m6 amendment-1
    # candor standard). Any PASS statement must carry each margin below at
    # the same prominence as its headline claim.
    not_certified:
      - margin: mortality_drift
        detail: >-
          A PASS certifies NOTHING about mortality DRIFT. gate_m6.not_certified[0]
          (gates.yaml:5396-5405) stands: that is gate_m6's TEMPORAL-HOLDOUT
          drift surface; this is the person-disjoint REPRODUCTION surface on
          a different event base. Nothing here weakens it.
      - margin: mortality_levels_against_nchs
        detail: >-
          A PASS certifies NOTHING about mortality LEVELS against NCHS. Every
          PSID/NCHS ratio is below 1 in every window (0.360-0.865, median
          0.760); it is the truth's undercount, REPORTED never gated
          (gates.yaml:5737-5740, '|ln|-gating external mortality LEVELS stays
          REJECTED'). A candidate that reproduces PSID inherits the undercount.
      - margin: survival_to_claiming_ages
        detail: >-
          SURVIVAL TO CLAIMING AGES (62 / FRA / 67), life expectancy at 65
          and every survivorship STOCK are NOT CERTIFIED (packet R8 --
          DEFERRED; v3 certification_scope.headline). No stock cell exists on
          this floor basis; these are the quantities Social Security benefit
          levels ride on, and a hazard gate at 75-84 / 85+ certifies almost
          nothing about them.
      - margin: cells_25_74
        detail: >-
          A PASS certifies NOTHING about the 25-74 cells: their k=3
          tolerances exceed ln(1.5) ({t["25-34|female"]:.3f} down to
          {t["65-74|female"]:.3f}); the two 65-74 cells are seed-decided
          (bootstrap P(clear) 0.443 male / 0.605 female at 100 seeds) and are
          report-only whatever the R3/R4 rulings.
      - margin: conventions_and_the_undercount
        detail: >-
          The weight universe, the ascertainment convention and the censoring
          rule bind BOTH SIDES of every score, and the undercount is part of
          the truth both sides inherit; no PASS may describe the censoring as
          innocuous. The ascertainment sensitivity band (lower end survival;
          upper ends RESIDUE-LITERAL, informed and TRULY LITERAL) is the
          disclosed uncertainty of the truth, never a second scoring rule.
          Crediting known deaths after attrition would move the 85+ hazards by
          {br_txt}; the gated hazard is
          interview-conditional.
      - margin: split_unit
        detail: >-
          The split is PERSON-DISJOINT (split_panel_by_person, gate_m4's
          disability convention). It DIFFERS from gate_m6's HOUSEHOLD-DISJOINT
          mortality family (gates.yaml:5534 split_units); no gate_m6 mortality
          statement transfers here and none from here transfers to gate_m6.
      - margin: sex_differential_rides_on_the_anchor
        detail: >-
          <RULING R5> Only sex_dominance.male_exceeds_female sees the sex
          differential: every clearing cell's full-panel sex gap (75-84 0.321,
          85+ 0.203) sits inside its own tolerance, so a sex-flat candidate
          passes every internal cell (degenerate_candidates.c6_sex_flat). If
          the anchor is demoted, the certification narrows to hazard
          reproduction and the id is renamed mortality_reproduction.
    holdout_basis: [ind2023er_demographic_panel, ind2023er_death_file, nchs_life_tables_2023]
    data_staged: >-
      ind2023er is staged on disk (the demographic panel + ER32000 sex +
      ER32050 year of death). The NCHS 2023 US period life tables are bundled
      IN-REPO at data/external/nchs_life_tables_2023.json, sha-pinned
      (af58c19ea205ad10ca7e4d0add0f6274d2165d23d402283b22ac0ff8e6398a68).
      There is no staged holdout FILE; the holdout is the person-disjoint
      side-A half of each split seed.
    floor_run: runs/mortality_gate_floors_v1.json
    floor_run_sha256: "<FILLED AT RATIFICATION>"
    derived_from_floor: runs/mortality_floors_v3.json
    derived_from_floor_sha256: {SOURCE_FLOOR_COMMITTED[1]}
    lock_ceremony:
      exists: false
      completed_so_far:
        - floors v2 (100 seeds; R2, R3 counts, R5 tables)
        - floors v3 (R1, R6, R7 answered from bytes; the pinned convention)
        - adversarial referees A (statistical) and B (contract and record)
        - floors v4 (the record and binding defects fixed; no floor number moved)
        - independent verification (VERIFIED -- READY FOR THRESHOLD BINDING)
        - threshold binding (this draft; every ruling filed and priced)
      required_before_lock:
        - adversarial_referee_round_on_the_bound_thresholds
        - the_rulings_R3_R4_R5_R9_R10_and_the_stability_clause_made_and_written_in
        - verification_round
        - ratifying_merge_with_the_GATE_MORTALITY_BLOCK_LANDED_flip
    thresholds:
      locked: false
      status: draft_pending_referee_round
      tranche_id: mortality_differential
      kind: anchor_based
      floor_run: runs/mortality_gate_floors_v1.json
      floor_key: noise_floor_seeds_0_99
      derived_from:
        floor: runs/mortality_floors_v3.json
        size_bytes: {SOURCE_FLOOR_COMMITTED[0]}
        sha256: {SOURCE_FLOOR_COMMITTED[1]}
        block: internal_noise_floor.conventions.pinned_narrow_midpoint.universes.declared_1997_plus
        rule: >-
          every tolerance below == round(mean + 3 * sd, 3) over the 100
          per-seed |ln(m_A / m_B)| values of that block (sd at ddof=1),
          recomputed by tests/test_gates_derivations.py from the per-seed
          record, never from a typed number; capped at T_max = ln(1.5).
      external_anchor: data/external/nchs_life_tables_2023.json
      estimand: >-
        the weighted PSID central death rate m(band, sex) = sum(w * death) /
        sum(w * exposure) over single-year person-interval exposure slices
        (scripts/build_mortality_floors.build_exposure_slices on the pinned
        death-record frame of scripts/build_mortality_floors_v3.py), on the
        DECLARED weight universe (start waves 1997-2021). Per the standing
        description_claims_exactly_the_scored_surface rule
        (gate_2.governance.amendment_rules), the scored surface is EXACTLY
        the enumerated cells -- NOT US mortality, NOT the NCHS life table, NOT
        survival to any claiming age. The hazard is INTERVIEW-CONDITIONAL:
        exposure ends at the last observed wave and deaths are counted only
        in the one grid interval after it.
      weight_universe:
        declaration: >-
          CORE/IMM INDIVIDUAL CROSS-SECTION WT, interval start waves
          1997-2021 (the 2023 wave is the terminal grid wave and starts no
          interval; every interval ends by 2023). The four PSID weight series
          across the window are not one estimand (the 1993-1996 rung is
          LONGITUDINAL; the 1997+ rung adds the IMMIGRANT sample); the 1997+
          series carries 99.9037% of the weighted exposure and the pooled
          all-window rate is the 1997+ rate to 0.000356 log units. The
          all-window universe is report-only under every convention.
        binds: >-
          both sides of every score: truth and candidate are scored on start
          waves 1997+ under the cross-section weight (v3
          governance.weight_universe.binds).
        v1_caveat_withdrawn: >-
          runs/mortality_floors_v1.json exposure_construction.biennial_caveats
          'older decades bias PSID UPWARD, against the undercount' is
          WITHDRAWN with three measurements (v3
          weight_universe.withdrawal_of_v1_caveat); it is not restated here.
      death_ascertainment:
        convention: pinned_narrow_midpoint
        rule: >-
          a range code lo-hi with span <= 2 years is assigned the death year
          floor((lo + hi) / 2) and scored by the exact-year machinery
          unchanged (200 of 293 range codes); the 93 wide codes and 12
          NA-year deaths carry full exposure and zero deaths in the headline
          floor and are published as a sensitivity band whose upper ends are
          the informed end, the RESIDUE-LITERAL end (the 67-person residue
          scored ignoring their ranges) and the TRULY LITERAL end (every one
          of the 142 in-frame non-exact decedents the pinned rule does not
          count). Measured: the pinned convention moves no k=3 tolerance by
          more than 0.008 over the survival convention, the truly literal end
          by no more than 0.006 over the pinned one (v3
          death_ascertainment.measured_movement).
        binds_both_sides: >-
          the convention binds both sides of every score; a candidate that
          ascertains deaths differently is scored on this frame's convention,
          not its own, and the band is the disclosed uncertainty of the
          truth, never a second scoring rule.
      censoring:
        rule: >-
          exposure ends at a person's last observed wave; a death more than
          one grid interval after that wave is never counted (v1 builder
          docstring, item 1, quoted byte-for-byte in v3 governance.censoring).
        assumption: >-
          NON-INFORMATIVE NONRESPONSE conditional on band and sex.
        evidence_against: >-
          the PSID/NCHS ratios (0.360-0.865, median 0.760 on the declared
          universe) and the attrition-by-age table (v3 governance.censoring
          .evidence_against): death removes people from the panel between
          waves, so nonresponse is informative for mortality by construction.
        bracket_report_only: >-
          crediting known deaths after attrition (referee A section 3.4,
          recomputed in runs/mortality_gate_floors_v1.json
          r4_85plus.item_2_sensitivity_of_85plus_to_the_censoring_convention)
          moves every declared-universe hazard by +0.27 to +0.74 log and the
          85+ hazards by {br_txt}. REPORT-ONLY;
          gates nothing; it is the size of the level's dependence on the rule.
      statistic: >-
        Two families. INTERNAL (candidate-vs-PSID reproduction): per gated
        cell |ln(mbar_candidate,s / m_A,s)| between the candidate's
        mean-over-K=20-draws hazard for seed s's holdout half A and that
        half's own empirical PSID hazard; tolerance = round(floor mean + 3 *
        floor sd, 3) capped at T_max = ln(1.5), with a UNIFORM k = 3
        (mortality declares no stock cell, so the gate_m4 MIXED-k split does
        not arise; see k_selection). ANCHOR (concept-bridged SHAPE /
        DOMINANCE): the candidate's own per-seed simulated invariant against
        the committed real half-split sd of that invariant -- the candidate-
        side condition is <RULING R5>; the evidence-time condition is that
        the REAL floor holds the invariant on every half with margin >=
        MARGIN_K = 3 sigma.
      protocol:
        option: >-
          anchor-based, gate_m4 style. Internal cells use the person-disjoint
          half-split, for which the half-vs-half floor is exactly the null.
          Anchor cells use the candidate's own per-seed simulated invariant
          against a margin fixed from the real half-split sd.
        estimator: >-
          mean-over-K=20-draws (tranche 2a amendment 1, ratified 2026-07-08,
          PR 96), re-used VERBATIM. mbar_candidate,s is the MEAN over 20
          pre-registered simulation draws of the cell HAZARD, scored ONCE per
          cell as |ln(mbar / m_A)| -- NOT the mean of per-draw |ln| scores.
        candidate_draws: {CANDIDATE_DRAWS}
        candidate_draw_stream: numpy.random.default_rng({DRAW_STREAM_BASE} + k), k=0..K-1
        draw_stream_base: {DRAW_STREAM_BASE}   # R9: DISTINCT from 5200 (2a/2b/2c/m4), 4200, 4100, 9100 / 9200 (W1), 91000, 20260710, the split seeds 0-99 and the gate seeds; proven in runs/mortality_gate_floors_v1.json draw_stream and bound by tests/test_gates_derivations.py
        gate_seeds: [0, 1, 2, 3, 4]
        floor_seeds: 0-99
        split: >-
          PERSON-DISJOINT 50/50 half-split
          (populace_dynamics.harness.panel.split_panel_by_person,
          fraction=0.5, seed=s) taken on the FULL exposure-slice frame,
          before any band or window restriction. Side A is seed s's HOLDOUT;
          side B is the fitting complement. NO person straddles the halves.
        split_frame_pin:
          # LOAD-BEARING (R10). Restricting the frame to 25-84 BEFORE the
          # split re-deals every person's side and moves tolerances: under a
          # 25-84-restricted split frame the 75-84|male k=3 tolerance is
          # {knife_r} (pinned convention, declared universe) where the pinned
          # full-frame split gives {knife_f:.3f}; the packet's v1-survival figures
          # were 0.405 vs 0.335 against a cap of 0.4055. The full-frame
          # convention is the committed builder's and is pinned here; a
          # perturbation test in tests/test_gates_derivations.py fails if
          # the builder's split convention changes.
          frame: the full slice frame, all ages, all start waves, before band assignment and before the window
          restricted_25_84_before_split_tolerance_75_84_male: {knife_r}
          full_frame_before_split_tolerance_75_84_male: {knife_f:.3f}
        candidate_scoring_frame: >-
          (referee A, addition (i)) for gate seed s the candidate is HANDED the
          side-A person-interval exposure table -- the pinned-convention
          frame's slices whose person is drawn to side A, restricted AFTER the
          split to start waves >= 1997: person_id, sex, start-wave weight,
          age, band, start_wave and interval. It simulates, for each person-
          interval in it, whether and in which slice the person dies; it may
          add no person, interval or exposure and may carry no one past their
          last observed wave. Deaths are counted INSIDE THOSE INTERVALS ONLY.
          m_candidate,s = sum(w * d_sim) / sum(w * exposure_sim) over the same
          slices, exposure_sim formed by the truth's rule (the simulated
          death-year slice carries 0.5 and one death; later slices in that
          interval carry nothing). The side-A person-id digests per gate seed
          are in runs/mortality_gate_floors_v1.json
          candidate_scoring_frame.per_gate_seed.
        pad_row_exclusion: >-
          the registered mortality-exposure adapter emits two INVENTED
          age-coverage pad rows carrying person_id -1 (female) and -2 (male)
          (PAD_IDENTITY_DISCLOSURE). They correspond to no PSID person, are
          absent from the floor frame (min person_id 1001) and are EXCLUDED
          from the scoring frame, from every exposure denominator and from
          every scored cell. A run whose artifact does not evidence their
          exclusion is INVALID.
        conjunction: >-
          seed passes iff EVERY gated cell holds (internal |ln| tolerance AND
          anchor condition); the gate passes iff >= 4 of 5 gate seeds pass.
          Report-only cells and all external LEVELS publish, never gate.
        fresh_run_artifact_schema:
          per_draw_per_cell_rates:
            required: true
            shape: [20, "<RULING R4: {n_gated_internal} | 2>", 5]
            rule: >-
              commit every draw's per-cell hazard r[k, cell, s] so mbar
              recomputes cell-by-cell and |ln(mbar / m_A)| is independently
              auditable.
          undefined_draw_rule:
            required: true
            pre_specified: true
            rule: >-
              if any gated cell's hazard is UNDEFINED on any draw (empty
              simulated exposure denominator), the RUN IS INVALIDATED and must
              be re-registered. No draw may be dropped, substituted or
              re-rolled.
          per_draw_dispersion_disclosure: {{ required: true, gated: false, report_only: true }}
          weight_universe_evidence:
            required: true
            rule: >-
              the run must publish, per gated cell, the share of weighted
              exposure and of unweighted deaths falling under each PSID weight
              series, so a referee can see the declared universe was honoured.
          scoring_frame_evidence:
            required: true
            rule: >-
              the run must publish, per gate seed, the sha256 of the sorted
              side-A person ids it scored on and its slice count, equal to
              runs/mortality_gate_floors_v1.json candidate_scoring_frame
              .per_gate_seed; a mismatch INVALIDATES the run.
      power_cap:
        t_max: ln(1.5)
        rule: >-
          an internal cell is gate-eligible iff its floor statistic is DEFINED
          on every one of the 100 seeds AND <RULING R3: its EFFECTIVE (Kish)
          weighted death count | its UNWEIGHTED death count> on the weaker
          half of the worst seed is >= 20 AND its k=3 tolerance is <= T_max.
          Both rules admit the same four cells today (unweighted min 86-155,
          Kish 67.6-120.9); the partition under each is committed in
          runs/mortality_gate_floors_v1.json eligibility_rules.
        stability_clause: >-
          <RULING A(ii): adopt | decide at 1,000 seeds> a cell whose bootstrap
          P(T(k=3) <= T_max) at its own sigma at 100 seeds lies in [0.1, 0.9]
          is REPORT-ONLY whatever its point tolerance. Today: 65-74|male 0.443
          and 65-74|female 0.605 are in the band and already report-only; no
          clearing cell is in it (nearest 75-84|female at 0.9456). Adopting
          it changes nothing today and removes the flip risk on a rebuild.
        aggregations: {{}}
      k_selection:
        rule: UNIFORM k = 3 (no stock family is declared); k pinned by the faithful-candidate OC against the 2a/2b/2c precedent band (the gate_m4 method)
        chosen_k: 3
        by_k:
{_by_k_line("1")}
{_by_k_line("2")}
{_by_k_line("3")}
{_by_k_line("4")}
        precedent_oc_band: {{ gate_2a: 0.9685, gate_2b: 0.9678, gate_2c: 0.9641 }}
        rationale: >-
          k=1 and k=2 collapse the faithful-candidate OC below the precedent
          floor 0.9641 on both surfaces; k=4 drops 75-84|female and keeps only
          three cells. k=3 is the only k that keeps the 75-84 pair and clears
          precedent on both surfaces ({oc2["p_gate_pass_4_of_5"]} on 25-84 /
          {oc4["p_gate_pass_4_of_5"]} with 85+). The same finding as gate_m4's,
          reached on a different module.
      faithful_candidate_oc:
        method: independence-approx normal OC on the draw-noise-free half-normal basis (runs/m4_gate_floors_v1.json faithful_candidate_oc.method)
        surface_4_cell_incl_85plus: {{ n_gated_internal_cells: {oc4["n_gated_internal_cells"]}, p_seed_pass: {oc4["p_seed_pass"]}, p_gate_pass_4_of_5: {oc4["p_gate_pass_4_of_5"]} }}
        surface_2_cell_25_84: {{ n_gated_internal_cells: {oc2["n_gated_internal_cells"]}, p_seed_pass: {oc2["p_seed_pass"]}, p_gate_pass_4_of_5: {oc2["p_gate_pass_4_of_5"]} }}
        binding_surface: "<RULING R4>"
        oc_vs_precedent: >-
          both surfaces sit AT OR ABOVE the precedent band top 0.9685 (gate_m4
          flip-note 2 wording: the band is a floor). The anchor cells add the
          R5 term (anchor_surface.operating_characteristic), which under the
          inherited candidate-side rule is NOT at or above precedent.
      internal_surface:
        # Tolerances == round(mean + 3*sd, 3) on the 100 per-seed |ln| values
        # of runs/mortality_floors_v3.json's headline block; machine-bound in
        # tests/test_gates_derivations.py; the floor is READ, never rewritten.
        floor_run: runs/mortality_gate_floors_v1.json
        floor_key: noise_floor_seeds_0_99
        views:
          hazard_reproduction:
            quantity_type: flow
            gated: true
            statistic: >-
              per age band x sex weighted central death rate,
              |ln(candidate / PSID)|.
            tolerances:
{_cell_tol("75-84|male")}
{_cell_tol("75-84|female")}
            derivations:
              floor_run: runs/mortality_gate_floors_v1.json
              floor_key: noise_floor_seeds_0_99
              rules:
{_cell_rule("75-84|male")}
{_cell_rule("75-84|female")}
          hazard_reproduction_85plus:
            # <RULING R4>: gate_m6 partitions death.85+|{{male,female}} report-only
            # under attrition_confounded_truth; the censoring bracket at 85+ is
            # {br_txt}. Both cells clear the cap with room; admitting them
            # takes the surface from 2 to 4 cells at OC {oc4["p_gate_pass_4_of_5"]}
            # (from {oc2["p_gate_pass_4_of_5"]}) and is what catches the -25% level
            # error and the external-levels candidate (degenerate_candidates).
            quantity_type: flow
            gated: "<RULING R4: true | false>"
            status: derived_pending_ruling_R4
            statistic: same statistic, the 85+ band
            tolerances:
{_cell_tol("85+|male")}
{_cell_tol("85+|female")}
            derivations:
              floor_run: runs/mortality_gate_floors_v1.json
              floor_key: noise_floor_seeds_0_99
              rules:
{_cell_rule("85+|male")}
{_cell_rule("85+|female")}
      anchor_surface:
        # Concept-bridged SHAPE / DOMINANCE. Unit-honest bounded/ordinal
        # invariants, NEVER |ln ratio| gates against an external LEVEL. The
        # evidence-time condition (the REAL floor holds the invariant on every
        # half with margin >= MARGIN_K x the real half-split sd) is a property
        # of the floor; the CANDIDATE-side condition is the R5 ruling.
        anchor_run: runs/mortality_gate_floors_v1.json
        margin_k: 3
        half_convention: "<RULING R5: both_sides (PROPOSED: the stricter convention, the one the headline band set was selected under) | side_a (gate_m4's literal precedent)>"
        cells:
          "sex_dominance.male_exceeds_female":
            gated: "<RULING R5: gated under remedy (a) or (b) | demoted under (c)>"
            statistic: >-
              min over the contiguous bands {{45-54, 55-64, 65-74}} of
              ln(m_male / m_female) exceeds 0; level-free.
            real_full_panel_min: {dom["side_a"]["real_full_panel_min"]:.5f}
            real_half_split_sd: {{ side_a: {dom["side_a"]["half_split_sd"]:.5f}, both_sides: {dom["both_sides"]["half_split_sd"]:.5f} }}
            margin_sigma_units: {{ side_a: {dom["side_a"]["margin_sigma_units"]}, both_sides: {dom["both_sides"]["margin_sigma_units"]} }}
            holds_on_every_real_half: {{ side_a: {str(dom["side_a"]["holds_on_every_half"]).lower()}, both_sides: {str(dom["both_sides"]["holds_on_every_half"]).lower()} }}
            band_restriction_reason: >-
              dominance inverts on 1 of 200 real halves at 35-44 (a B half) and
              1 of 200 at 75-84; {{45-54, 55-64, 65-74}} is the widest contiguous
              set with zero inversions under BOTH half conventions. The 5-band
              set 25-34..65-74 holds on all 100 side-A halves ({five["side_a"]["margin_sigma_units"]} sigma) and
              FAILS on the 200 ({five["both_sides"]["margin_sigma_units"]} sigma, one inversion) -- the two
              conventions select different sets, which is why the convention is
              itself a ruling.
            operating_characteristic:
              # R5 (referee A section 4.5, recomputed): under gate_m4's inherited
              # candidate-side rule (candidate margin >= 3 sigma) a FAITHFUL
              # candidate passes this cell with the probabilities below.
              inherited_rule_faithful_p_gate:
                side_a_draw_noise_only: {inh["headline_3_band_side_a"]["draw_noise_only"]["faithful_p_gate_4_of_5"]}
                side_a_fitted_excluding_holdout: {inh["headline_3_band_side_a"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}
                both_sides_draw_noise_only: {inh["headline_3_band_both_sides"]["draw_noise_only"]["faithful_p_gate_4_of_5"]}
                both_sides_fitted_excluding_holdout: {inh["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}
              gate_m4_weakest_anchor_4_797_same_computation: {inh["gate_m4_weakest_anchor"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}
              remedies_priced:
                a_bare_positivity_k0: {{ faithful_p_gate: {rem["a_bare_positivity_k0"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}, sex_flat_c6_p_gate: {rem["a_bare_positivity_k0"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["sex_flat_c6_p_gate_4_of_5"]} }}
                b_k1: {{ faithful_p_gate: {rem["b_k1"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}, sex_flat_c6_p_gate: {rem["b_k1"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["sex_flat_c6_p_gate_4_of_5"]} }}
                b_k2: {{ faithful_p_gate: {rem["b_k2"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}, sex_flat_c6_p_gate: {rem["b_k2"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["sex_flat_c6_p_gate_4_of_5"]} }}
                c_demote_and_rename: the anchor is REPORTED; id -> mortality_reproduction; C6 becomes an uncaught degenerate of the whole gate
              note: >-
                (both_sides margin, fitted-excluding-holdout noise). More draws
                do not cure the inherited rule: the fitted-model noise does not
                shrink with K.
            gate_rule:
              candidate_condition: "<RULING R5: (a) the candidate's per-gate-seed statistic > 0 | (b) > K x real_half_split_sd with K in {{1, 2}} stated here | (c) none -- demoted>; gate passes iff >= 4 of 5 gate seeds. This is the ONLY thing a candidate must satisfy."
              evidence_time_conditions: >-
                flip-note 3 (gate_m4): 'holds on every real half' and 'margin
                >= MARGIN_K = 3 x the real half-split sd' are properties of the
                REAL floor established at floor-build time under the ruled half
                convention; they set the cell's gate-eligibility and are NOT
                re-checked on the candidate.
            anchor_corroboration: >-
              the NCHS 2023 table's male rate exceeds the female rate in every
              band -- a CONSTANT of the sha-pinned reference; it corroborates
              the choice of invariant and constrains no candidate.
            unique_catch: >-
              this is the ONLY gated cell that sees the sex differential
              (degenerate_candidates.c6_sex_flat). Removing it removes
              differential mortality from a differential-mortality gate.
          "age_gradient.comonotone|male":
            gated: "<RULING R5-companion: commission (the packet's section-1 draft) | report-only (v3 labels it companion evidence)>"
            statistic: >-
              the weighted hazard rises strictly across 55-64 < 65-74 < 75-84 <
              85+, scored as the MIN ADJACENT LOG GAP over those bands.
            real_full_panel_min_gap: {gm["side_a"]["real_full_panel_min"]:.5f}
            real_half_split_sd: {{ side_a: {gm["side_a"]["half_split_sd"]:.5f}, both_sides: {gm["both_sides"]["half_split_sd"]:.5f} }}
            margin_sigma_units: {{ side_a: {gm["side_a"]["margin_sigma_units"]}, both_sides: {gm["both_sides"]["margin_sigma_units"]} }}
            holds_on_every_real_half: {{ side_a: {str(gm["side_a"]["holds_on_every_half"]).lower()}, both_sides: {str(gm["both_sides"]["holds_on_every_half"]).lower()} }}
            band_restriction_reason: >-
              the 25-34 -> 35-44 male gap INVERTS on 26 of 200 real halves, so
              no band set reaching below 55-64 satisfies the evidence-time
              condition for both sexes; 55+ is the widest set that does.
            operating_characteristic_note: at ~10 sigma the inherited rule gives a faithful pass >= 0.999 under both noise models; the R5 question does not bite here.
          "age_gradient.comonotone|female":
            gated: "<RULING R5-companion: commission | report-only>"
            statistic: same invariant, female
            real_full_panel_min_gap: {gf["side_a"]["real_full_panel_min"]:.5f}
            real_half_split_sd: {{ side_a: {gf["side_a"]["half_split_sd"]:.5f}, both_sides: {gf["both_sides"]["half_split_sd"]:.5f} }}
            margin_sigma_units: {{ side_a: {gf["side_a"]["margin_sigma_units"]}, both_sides: {gf["both_sides"]["margin_sigma_units"]} }}
            holds_on_every_real_half: {{ side_a: {str(gf["side_a"]["holds_on_every_half"]).lower()}, both_sides: {str(gf["both_sides"]["holds_on_every_half"]).lower()} }}
      report_only:
        # The {len(report_only)} remaining band x sex cells, all by the machine reason
        # tolerance_above_t_max at k=3 (the first reason in the v1/v2/v3
        # precedence); the event criterion each would ALSO fail is noted.
        # Set-bound to runs/mortality_gate_floors_v1.json gate_partition.report_only.
{ro_lines}
      external_anchor_report:
        reported_anchor_not_gated: true
        anchor_pins:
          "data/external/nchs_life_tables_2023.json":
            sha256: af58c19ea205ad10ca7e4d0add0f6274d2165d23d402283b22ac0ff8e6398a68
        concept_delta: >-
          the PSID observes fewer deaths per person-year than the NCHS period
          population in EVERY band x sex (declared universe, pinned
          convention: ratios 0.360 to 0.865, median 0.760). Named deltas: (1)
          censoring -- deaths are counted only in the one grid interval after
          an observed wave, so an attriter who dies later is right-censored
          and uncounted (the bracket above is its size); (2) death dating --
          narrow range codes at the midpoint, the 105-person residue as
          survival, the band disclosed; (3) weight universe -- start waves
          1997-2021; (4) period -- interval deaths against a 2023 period
          table. LEVELS are therefore NOT level-comparable and are report-only
          with the delta named. The gate bridges only the level-invariant
          SHAPE and DOMINANCE.
        calibration: none -- the bridge names deltas and moves no floor value
        circularity_disclosure: >-
          engine.refit.fit_mortality_model (refit.py:1113-1115) computes
          ratio = psid_rate / central_rate and then multiplies the external
          central rate by that ratio, so the external rate CANCELS EXACTLY and
          the fitted level is the PSID level (the function's own docstring,
          :1066-1068; its result variable is named with the word this audit
          forbids, and is not repeated here). The NCHS input contributes no
          information to the fitted model. Any statement that the engine's
          mortality is externally pinned to NCHS is false and must not appear
          in a PASS statement. Compare gate_m6:5745-5749, which already
          discloses the same path circularity for the report-only
          triangulation.
      degenerate_candidates:
        # R11 (runs/mortality_gate_floors_v1.json degenerate_candidates):
        # full-panel scoring on the declared universe against the k=3
        # tolerances -- an UPPER BOUND on teeth.
        c1_external_levels:
          candidate: NCHS 2023 band rates used directly, no undercount adjustment
          scores: {{ {", ".join(f'"{c}": {teeth["candidates"]["c1_external_levels"]["scores"][c]:.3f}' for c in teeth["gated_4_cell_surface"])} }}
          verdict_2_cell: {teeth["candidates"]["c1_external_levels"]["verdict_2_cell_surface_25_84"]}   # the 25-84 surface is nearly blind to the undercount
          verdict_4_cell: {teeth["candidates"]["c1_external_levels"]["verdict_4_cell_surface"]}   # only via 85+|female, {teeth["candidates"]["c1_external_levels"]["scores"]["85+|female"]:.3f} vs {t["85+|female"]:.3f}
        c2_age_flat_within_sex:
          scores: {{ {", ".join(f'"{c}": {teeth["candidates"]["c2_age_flat_within_sex"]["scores"][c]:.3f}' for c in teeth["gated_4_cell_surface"])} }}
          verdict: FAIL on every surface -- the age gradient is decisively gated
        c3_fully_flat:
          scores: {{ {", ".join(f'"{c}": {teeth["candidates"]["c3_fully_flat"]["scores"][c]:.3f}' for c in teeth["gated_4_cell_surface"])} }}
          verdict: FAIL on every surface
        c4_uniform_level_plus_25pct:
          score_every_cell: 0.223
          verdict: KNOWN NON-CATCH of the WHOLE gate -- PASSES every gated internal cell on both surfaces, and no anchor invariant sees a level.
        c5_uniform_level_minus_25pct:
          score_every_cell: 0.288
          verdict: {teeth["candidates"]["c5_uniform_level_minus_25pct"]["verdict_4_cell_surface"]} on the 4-cell surface (85+ cells only), {teeth["candidates"]["c5_uniform_level_minus_25pct"]["verdict_2_cell_surface_25_84"]} on the 2-cell surface -- the R4 ruling decides whether -25% is caught
        c6_sex_flat:
          candidate: both sexes assigned the female hazard
          scores: {{ {", ".join(f'"{c}": {teeth["candidates"]["c6_sex_flat"]["scores"][c]:.3f}' for c in teeth["gated_4_cell_surface"])} }}
          verdict_internal: KNOWN NON-CATCH of the internal surface -- PASSES every internal cell
          caught_by: sex_dominance.male_exceeds_female
          anchor_oc_beside_the_catch: >-
            under the inherited 3-sigma candidate rule C6 is caught with
            probability ~1 but the faithful candidate passes with only
            {inh["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]}; under bare positivity (a) the faithful candidate passes with
            {rem["a_bare_positivity_k0"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]} and C6 passes with {rem["a_bare_positivity_k0"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["sex_flat_c6_p_gate_4_of_5"]}; under K=1 (b) the faithful
            candidate passes with {rem["b_k1"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["faithful_p_gate_4_of_5"]} and C6 with {rem["b_k1"]["by_margin"]["headline_3_band_both_sides"]["fitted_excluding_holdout"]["sex_flat_c6_p_gate_4_of_5"]} (both_sides margin,
            fitted-excluding-holdout noise). This is the anchor's unique catch
            and the reason the k=3 internal surface alone must NEVER be
            described as certifying differential mortality.
        catch_structure: >-
          {teeth["catch_structure"]}
      governance:
        registration: >-
          pre-registered on issue #42 like every gate-1 / gate-2 candidate. A
          candidate registers its spec, its fitting exclusions (the seed-s
          holdout persons), its draw seeds ({DRAW_STREAM_BASE} + k) and its declared
          weight universe BEFORE scoring. Outer runs are one-shot.
        candidate_scale: >-
          PINNED to the seed-s holdout half (side A). The candidate simulates
          exactly the persons and intervals of the scoring frame, fixing the
          output scale the floor and the tolerances are measured at.
        weight_definition: >-
          every gated internal statistic is weighted by the START-WAVE
          cross-sectional PSID weight of each exposure slice, from the
          DECLARED universe only. The unweighted rate is reported alongside
          and is never gated.
        amendment_rules:
          inherits: gate_1
          no_self_rescue: >-
            inherited verbatim from gate_1.amendment_rules: no candidate's
            committed run verdict changes under a rule proposed after that run.
          amendments_only_via: >-
            public proposal + adversarial referee round + verification +
            maintainer ratification by merge.
          description_claims_exactly_the_scored_surface: >-
            bound by the standing rule promoted into
            gate_2.governance.amendment_rules (amendment 2): covers /
            holdout_basis / estimand claim EXACTLY the scored cells. No
            national mortality level, no life expectancy, and no survival-to-
            claiming statement may be headlined.
          floor_seed_count:
            rule: >-
              a mortality floor supporting a lock carries >= 100 split seeds
              (gate_m4 floor_seeds 0-99; gate_m6 [0, 99]); the 5-seed v1 floor
              is retained as the pre-lock record and is never a derivation
              basis. <RULING A(ii)> may raise the partition decision to 1,000
              seeds.
          differential_claim_requires_the_anchor:
            rule: >-
              a PASS may be described as certifying DIFFERENTIAL mortality only
              while sex_dominance.male_exceeds_female is a GATED cell. If that
              cell is demoted (R5 remedy (c)), the certification narrows to
              hazard reproduction in the gated bands plus the age-gradient
              shape, the id becomes mortality_reproduction, and every PASS
              statement says so at the same prominence as the headline claim.
      certification_scope:
        tranche: mortality_differential
        headline: >-
          SURVIVAL TO CLAIMING AGES IS NOT CERTIFIED BY THIS BASIS (packet R8
          -- DEFERRED); THE GATED HAZARD IS THE INTERVIEW-CONDITIONAL PSID
          HAZARD, NOT A POPULATION HAZARD (v3 certification_scope, carried).
        certifies: >-
          person-disjoint half-split REPRODUCTION of the weighted PSID central
          death rate in the gated cells on the declared universe under the
          pinned ascertainment and declared censoring conventions, <RULING R5:
          plus the sex DOMINANCE over 45-74 and> the age-gradient SHAPE over
          55+, on generated panels scored on the side-A frame.
        does_not_support:
          - survival to age 62 / FRA / 67, life expectancy at 65, or any survivorship STOCK (R8 -- DEFERRED at headline prominence)
          - national or population mortality LEVELS (the gated statistic reproduces a surface measured at a median 0.760 of the NCHS period rate)
          - mortality DRIFT or projection (gate_m6.not_certified[0] stands)
          - the 25-74 cells, mortality below 25, and the pre-1997 PSID weight universes
          - that the censoring is innocuous or the hazard free of the undercount
          - the differential (male > female) claim unless the sex-dominance anchor is GATED (R5)
      ceremony_notes:
        placeholders_the_ratifying_round_must_fill:
          - "<RULING R3>: the eligibility count (Kish effective PROPOSED | unweighted)"
          - "<RULING R4>: 85+ in the reproduction gate (4-cell surface, OC {oc4["p_gate_pass_4_of_5"]}) | out (2-cell, OC {oc2["p_gate_pass_4_of_5"]})"
          - "<RULING R5>: the anchor's candidate-side rule ((a) bare positivity | (b) K in {{1, 2}}) | demotion (c) with the rename; the half convention (both_sides PROPOSED | side_a); the age-gradient companions' commissioning"
          - "<RULING A(ii)>: the stability clause | a 1,000-seed partition decision"
          - "<FILLED AT RATIFICATION>: floor_run_sha256 = sha256 of runs/mortality_gate_floors_v1.json as ratified"
          - "draw_stream_base {DRAW_STREAM_BASE}: PROPOSED here; enters gates.yaml only at the flip"
        flip_plan: >-
          (referee A, addition (iii)) the commit that inserts this block under
          `gates:` flips GATE_MORTALITY_BLOCK_LANDED False -> True in
          tests/test_mortality_floors_v2.py, tests/test_mortality_floors_v3.py,
          tests/test_gates_derivations.py and
          tests/test_mortality_gate_floors_v1.py IN THE SAME COMMIT (one
          constant per file; no test deleted); the derivation bindings then read
          the LIVE block (LOCKED-HOT); the added-key tolerance sets in
          tests/test_gates_derivations.py and tests/test_gate_w1_derivations.py
          admit {{'gate_mortality'}} while the flip PR is open; tier_counts.json
          and README-tiers.md are re-refreshed by live collection.
        wording_audit: >-
          zero occurrences in this block of each of the three words the R12
          audit forbids (runs/mortality_gate_floors_v1.json
          wording_audit.forbidden_word_counts); the PR body is audited by the
          verification round at PR time with the same list.
"""
    return text


# --------------------------------------------------------------------------
# Open questions and scope
# --------------------------------------------------------------------------
def open_questions(
    partition_rules: dict[str, Any],
    r4: dict[str, Any],
    anchor_oc: dict[str, Any],
    draw: dict[str, Any],
    r10: dict[str, Any] | None,
    clause: dict[str, Any],
) -> list[dict[str, Any]]:
    knife = r10["knife_edge_cell"] if r10 else None
    return [
        {
            "id": "R3",
            "question": "is gate-eligibility decided on weighted (Kish effective) or unweighted event counts?",
            "options": {
                "kish_effective_ge_20": partition_rules[
                    "kish_effective_ge_20"
                ]["gate_eligible_internal"],
                "unweighted_worst_seed_ge_20": partition_rules[
                    "unweighted_worst_seed_ge_20"
                ]["gate_eligible_internal"],
            },
            "priced": partition_rules["difference"]["price"],
            "proposed": "kish_effective_ge_20 (the count matched to the weighted statistic; the stricter rule; the packet's section-1 correction)",
            "changes_the_gated_set_today": not partition_rules["difference"][
                "gated_sets_identical"
            ],
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "R4",
            "question": r4["question"],
            "item_1": r4["item_1_the_27_percent"]["disposition"],
            "options": {
                "admit_85plus": r4["item_3_the_ruling_priced_both_ways"][
                    "admit_85plus"
                ],
                "exclude_85plus": r4["item_3_the_ruling_priced_both_ways"][
                    "exclude_85plus"
                ],
            },
            "certification_scope_either_way": r4[
                "item_3_the_ruling_priced_both_ways"
            ]["certification_scope_either_way"],
            "status": "FILED and PRICED; not ruled (the referee's, per the packet)",
        },
        {
            "id": "R5",
            "question": "is the sex-dominance anchor gate-eligible, under which candidate-side rule and which half convention?",
            "operating_characteristic": anchor_oc["reading"],
            "options": {k: v for k, v in anchor_oc["remedies_priced"].items()},
            "half_convention": anchor_oc["half_convention_proposed"],
            "age_gradient_companions": (
                "the packet's section-1 draft gates age_gradient.comonotone|"
                "{male,female} over 55+ (margins ~9.7-10.0 sigma, hold on every "
                "half under both conventions); v3 labels them companion "
                "evidence, not commissioned. Their commissioning is filed here "
                "for the ratifying round; the R5 OC question does not bite at "
                "10 sigma"
            ),
            "consequence_if_demoted": "differential_claim_requires_the_anchor fires; id -> mortality_reproduction",
            "status": "FILED and PRICED; not ruled (the referee's, per the packet)",
        },
        {
            "id": "R9",
            "question": "which draw-stream base, and is it distinct?",
            "proposed": draw["proposed_base"],
            "proof": draw["every_seed_base_named_in_gates_yaml"],
            "distinct": draw["distinct"],
            "status": "PROPOSED and pinned here; enters gates.yaml only at the flip",
        },
        {
            "id": "R10",
            "question": "is the split frame pinned, and does the knife-edge cell survive it?",
            "pinned": "full frame before the split (v1/v2/v3; v3 split_frame_pin)",
            "knife_edge": knife,
            "status": "ANSWERED as evidence (both tolerances published; perturbation test bound); the pin is inherited, not a new ruling",
        },
        {
            "id": "A(ii)",
            "question": "a pre-registered stability clause for seed-decided cells, or a 1,000-seed partition decision?",
            "clause": clause["clause_proposed"],
            "priced": clause["priced"],
            "changes_nothing_today": clause["changes_nothing_today"],
            "status": "FILED and PRICED; not adopted",
        },
        {
            "id": "R8",
            "question": "survivorship STOCK cell",
            "status": "DEFERRED (v3 certification_scope.does_not_support[0]); carried into the draft block's not_certified at covers prominence; not reopened here",
        },
    ]


DOES_NOT_DO = [
    "edit gates.yaml or any threshold (the draft block is a STRING inside this artifact)",
    "score a candidate or run a gate",
    "make any ruling: R3, R4, R5, A(ii) are FILED and PRICED; R9 is PROPOSED",
    "open runs/mortality_floors_v1.json, _v2.json or _v3.json for writing (v3 is READ by path with its bytes pinned)",
    "move any floor value, tolerance, mean, sd, sigma, Kish count, death count or partition of v3 (every number here is DERIVED from v3's per-seed record or ADDED as new evidence)",
    "add a survivorship stock statistic (R8 stays DEFERRED)",
    "resolve referee A's finding (i); it is recomputed and priced, not resolved",
]


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------
def run(verbose: bool = True, with_psid: bool = True) -> dict[str, Any]:
    started = time.time()
    v3 = load_source_floor()
    cells = list(v3["cell_order"])
    head = headline_block(v3)
    per_seed = head["per_seed"]
    if [s["seed"] for s in per_seed] != list(FLOOR_SEEDS):
        raise RuntimeError(
            "the headline block's per-seed record is not seeds 0-99"
        )

    floor = derive_floor(per_seed, cells)
    # The derivation must agree with v3's own pooled block cell for cell.
    for c in cells:
        ref = head["noise_floor_seeds_0_99"][c]
        for key in ("mean", "sd", "min", "max", "realized_sigma"):
            if not math.isclose(
                floor[c][key], ref[key], rel_tol=1e-12, abs_tol=1e-12
            ):
                raise RuntimeError(
                    f"{c}.{key}: derived {floor[c][key]} != v3 {ref[key]}"
                )
        if (
            _tolerance(floor[c]["mean"], floor[c]["sd"], 3)
            != head["cell_stability"][c]["tolerance_k3"]
        ):
            raise RuntimeError(f"{c}: k=3 tolerance differs from v3")
    stability = cell_stability(
        per_seed, floor, v3["seed_count_stability"], cells
    )
    rules = partitions_by_rule(stability, cells)
    for c in cells:
        stability[c]["report_reason_kish"] = rules["kish_effective_ge_20"][
            "report_reason"
        ][c]
        stability[c]["report_reason_unweighted"] = rules[
            "unweighted_worst_seed_ge_20"
        ]["report_reason"][c]
    gated_4 = rules["kish_effective_ge_20"]["gate_eligible_internal"]
    gated_2 = [c for c in gated_4 if not c.startswith("85+")]
    report_only = rules["kish_effective_ge_20"]["report_only"]
    k_sel = k_selection(stability, cells)
    oc4 = faithful_oc(gated_4, stability, K_CHOSEN)
    oc2 = faithful_oc(gated_2, stability, K_CHOSEN)

    full_window = v3["external_anchor"]["windows"][HEADLINE_UNIVERSE]
    full_h = {k: v["psid_m"] for k, v in full_window["by_band_sex"].items()}
    checks = anchor_checks(per_seed, full_h)
    # Agreement with v3's committed anchor tables.
    v3_dom = v3["anchor_invariants"]["sex_dominance"]["margins_by_band_set"][
        "45-54+55-64+65-74"
    ]
    for conv in ("side_a", "both_sides"):
        got = checks["sex_dominance.male_exceeds_female"][conv]
        if got["margin_sigma_units"] != v3_dom[conv]["margin_sigma_units"]:
            raise RuntimeError(f"dominance margin {conv} differs from v3")
        if not math.isclose(
            got["half_split_sd"], v3_dom[conv]["half_split_sd"], rel_tol=1e-12
        ):
            raise RuntimeError(f"dominance sd {conv} differs from v3")
    anchor_oc = anchor_operating_characteristic(checks)
    teeth = teeth_table(full_window, stability, gated_4, anchor_oc)
    gates_text = GATES_PATH.read_text()
    draw = draw_stream_block(gates_text)
    clause = stability_clause(stability, cells)

    anchor_eligible = [
        name
        for name, chk in checks.items()
        if not name.endswith("five_band_alternative")
        and chk["side_a"]["holds_on_every_half"]
        and chk["both_sides"]["holds_on_every_half"]
        and chk["side_a"]["clears_margin_k"]
        and chk["both_sides"]["clears_margin_k"]
    ]
    gate_partition = {
        "gate_eligible": [gate_cell(c) for c in gated_4] + anchor_eligible,
        "report_only": [gate_cell(c) for c in report_only],
        "n_gate_eligible": len(gated_4) + len(anchor_eligible),
        "n_report_only": len(report_only),
        "internal_gate_eligible": [gate_cell(c) for c in gated_4],
        "anchor_gate_eligible": anchor_eligible,
        "eligibility_rule_applied": "kish_effective_ge_20 (PROPOSED; identical gated set under unweighted_worst_seed_ge_20 -- see eligibility_rules)",
        "anchor_eligibility_basis": (
            "evidence-time: holds on every real half AND margin >= MARGIN_K "
            "under BOTH half conventions; the candidate-side rule is the R5 "
            "ruling and does not enter eligibility"
        ),
        "rulings_that_can_move_it": {
            "R3": "no (both rules admit the same four internal cells)",
            "R4": f"yes: exclude 85+ -> internal {len(gated_2)} cells {[gate_cell(c) for c in gated_2]}, OC {oc2['p_gate_pass_4_of_5']}",
            "R5": "yes: demote sex_dominance.male_exceeds_female -> anchor cells drop to the two age-gradient companions if commissioned, else none",
        },
        "r4_alternative_partition": {
            "internal_gate_eligible": [gate_cell(c) for c in gated_2],
            "report_only": [gate_cell(c) for c in report_only]
            + [gate_cell(c) for c in gated_4 if c.startswith("85+")],
            "report_reason_for_85plus": "attrition_confounded_truth (gate_m6's machine reason for the same stratum)",
        },
        "status": "DERIVED under the proposed rules; pending the rulings named",
    }
    reference_moments = [gate_cell(c) for c in cells]

    r10 = None
    bracket = None
    scoring_seeds: dict[str, Any] | None = None
    psid_block: dict[str, Any] = {"staged": False}
    if with_psid:
        ind_dir = v3b._psid_ind_dir()
        if ind_dir.is_dir():
            t0 = time.time()
            demo = panels.demographic_panel()
            dr = deaths.read_death_records()
            frames, _detail = v3b.build_convention_frames(demo, dr)
            pinned = frames[v3b.CONVENTION_PINNED]
            if verbose:
                print(
                    f"  frames built in {time.time() - t0:.1f}s; pinned {len(pinned)} slices"
                )
            nchs_rates = v1b.nchs_band_rates(json.loads(NCHS_PATH.read_text()))
            r10 = restricted_split_perturbation(
                pinned, head["cell_stability"], verbose
            )
            bracket = censoring_extension_bracket(
                demo, dr, pinned, nchs_rates, stability, cells, verbose
            )
            scoring_seeds = gate_seed_frames(pinned, gated_4)
            psid_block = {
                "staged": True,
                "ind2023er_txt_sha256": _sha_of_file(
                    ind_dir / "IND2023ER.txt"
                ),
                "frame_pinned_n_slices": int(len(pinned)),
                "frame_pinned_n_persons": int(pinned.person_id.nunique()),
                "frame_pinned_death_events": float(pinned.death.sum()),
            }
    r4 = r4_block(v3, stability, k_sel, bracket)
    scoring = scoring_frame_definition()
    scoring["per_gate_seed"] = scoring_seeds
    fragment = draft_fragment(
        stability,
        floor,
        gate_partition_internal_names(
            gate_partition, report_only, gated_4, anchor_eligible
        ),
        k_sel,
        oc4,
        oc2,
        checks,
        anchor_oc,
        teeth,
        r10,
        bracket,
        v3,
    )
    fragment_meta = {
        "text": fragment,
        "text_sha256": _sha_of_text(fragment),
        "n_lines": len(fragment.splitlines()),
        "n_bytes": len(fragment.encode("utf-8")),
        "indent": "2 spaces under `gates:`; parse with yaml.safe_load('gates:\\n' + text)['gates']['gate_mortality']",
        "status_in_text": "draft_pending_referee_round",
        "written_nowhere_else": "asserted by tests/test_mortality_gate_floors_v1.py and tests/test_gates_derivations.py: gates.yaml mentions neither gate_mortality nor this artifact nor runs/mortality_floors_v3.json while GATE_MORTALITY_BLOCK_LANDED is False, and the text occurs in no other tracked file",
    }

    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run": RUN_NAME,
        "reported_anchor_not_gated": True,
        "component": "differential mortality (issue #74 Phase B); THRESHOLD BINDING, the packet's ceremony step 3",
        "purpose": (
            "the gate-schema derivation from the VERIFIED floor basis "
            "runs/mortality_floors_v3.json: the noise floor, cell stability, "
            "the gate partition under both eligibility rules, k-sensitivity "
            "with the faithful-candidate OC, the anchor checks and the anchor "
            "cell's operating characteristic with its remedies priced, the "
            "85+ evidence, the draw stream, the restricted-split perturbation, "
            "the teeth table, the wording audit, referee A's three additions "
            "and the DRAFT gate_mortality block as a string. It edits no "
            "gates.yaml byte, scores no candidate and makes no ruling."
        ),
        "does_not_do": DOES_NOT_DO,
        "source_floor": {
            "path": "runs/mortality_floors_v3.json",
            "size_bytes": SOURCE_FLOOR_COMMITTED[0],
            "sha256": SOURCE_FLOOR_COMMITTED[1],
            "schema_version": v3["schema_version"],
            "built_on_commit": v3["revision_pins"]["populace_dynamics_sha"],
            "verified_by": VERIFICATION_REPORT,
            "headline_block": f"internal_noise_floor.conventions.{HEADLINE_CONVENTION}.universes.{HEADLINE_UNIVERSE}",
            "convention": HEADLINE_CONVENTION,
            "universe": HEADLINE_UNIVERSE,
            "read_by": "path, with size and sha256 checked before any value is read",
        },
        "ceremony": {
            "step": "3 of the packet's suggested sequence: derive thresholds and bind them; pin the draw stream; compute the teeth table; the stock question stays deferred",
            "packet": PACKET_REPORT,
            "referees": {
                "A_statistical": REFEREE_A_REPORT,
                "B_contract_and_record": REFEREE_B_REPORT,
            },
            "verification": VERIFICATION_REPORT,
            "gates_yaml_untouched": True,
            "gates_yaml_stub": "gate_mortality (DRAFT as a string in draft_gates_yaml_fragment; not in gates.yaml)",
            "next": "adversarial referee round on these bound thresholds -> the rulings -> verification -> ratifying merge with the GATE_MORTALITY_BLOCK_LANDED flip",
        },
        "derivation_convention": {
            "tolerance": "round(mean + k * sd, 3), sd over the 100 per-seed |ln(m_A / m_B)| values at ddof=1 (tests/test_gates_derivations.py convention)",
            "realized_sigma": "RMS of the 100 floor values (runs/m4_gate_floors_v1.json convention)",
            "t_max": T_MAX,
            "t_max_source": "ln(1.5)",
            "chosen_k": K_CHOSEN,
            "k_grid": list(K_GRID),
            "margin_k": MARGIN_K,
            "min_events": MIN_EVENTS,
            "gate_seeds": list(GATE_SEEDS),
            "floor_seeds": "0-99",
            "candidate_draws": CANDIDATE_DRAWS,
            "cell_name_rule": "gates.yaml cell = 'death.' + v3 cell ('death.75-84|male')",
        },
        "cell_order": cells,
        "reference_moments": reference_moments,
        "noise_floor_seeds_0_99": floor,
        "cell_stability": stability,
        "eligibility_rules": rules,
        "gate_partition": gate_partition,
        "k_selection": k_sel,
        "faithful_candidate_oc": {
            "method": OC_METHOD,
            "surface_4_cell_incl_85plus": oc4,
            "surface_2_cell_25_84": oc2,
            "binding_surface": "<RULING R4>",
        },
        "anchor_checks": checks,
        "anchor_operating_characteristic": anchor_oc,
        "degenerate_candidates": teeth,
        "r4_85plus": r4,
        "draw_stream": draw,
        "restricted_split_perturbation": (
            r10
            if r10 is not None
            else {"status": "not computed (PSID not staged)"}
        ),
        "stability_clause": clause,
        "candidate_scoring_frame": scoring,
        "flip_plan": flip_plan(),
        "record_hygiene": {
            "verification_item_10_V1": (
                "the v3 artifact's open_questions_for_the_ceremony[8].detail "
                "labels a condensed splice of referee A section 4.3 "
                "'VERBATIM'; v3 is not re-emitted (its digest must not move), "
                "so the sentence is carried here EXACTLY as A wrote it"
            ),
            "referee_a_finding_iii_verbatim": REFEREE_A_FINDING_III_VERBATIM,
            "source": REFEREE_A_REPORT + ", section 4.3",
            "v3_label_status": "condensed from (not verbatim); every number in it is A's and intact (verification section 5)",
        },
        "certification_scope": v3["certification_scope"],
        "open_questions_for_the_ceremony": open_questions(
            rules, r4, anchor_oc, draw, r10, clause
        ),
        "draft_gates_yaml_fragment": fragment_meta,
        "psid": psid_block,
        "revision_pins": {
            "populace_dynamics_sha": _git_sha(ROOT),
            "source_floor_sha256": SOURCE_FLOOR_COMMITTED[1],
            "source_floor_size_bytes": SOURCE_FLOOR_COMMITTED[0],
            "builder_v3_sha256": _sha_of_file(V3_BUILDER_PATH),
            "builder_gate_v1_sha256": _sha_of_file(Path(__file__).resolve()),
            "nchs_reference_sha256": _sha_of_file(NCHS_PATH),
            "gates_yaml_git_blob_for_the_r4_quotation": GATES_YAML_BLOB_AT_BINDING,
            "gates_yaml_pin_semantics": "PROVENANCE of the R4 quotation only; NOT a freeze of the live file (referee B D-1)",
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        },
    }
    # R12 on the fragment and on the artifact minus the audit block itself.
    audit = wording_audit(fragment, json.dumps(artifact))
    if not audit["forbidden_words_absent_from_fragment"]:
        raise RuntimeError(
            f"forbidden word in the draft block: {audit['forbidden_word_counts']}"
        )
    if not audit["forbidden_words_absent_from_artifact"]:
        raise RuntimeError(
            f"forbidden word in the artifact: {audit['forbidden_word_counts']}"
        )
    if not audit["all_covers_prominence_items_hold"]:
        raise RuntimeError(
            "covers-prominence item missing: "
            + str(
                [
                    c["item"]
                    for c in audit["covers_prominence"]
                    if not c["holds"]
                ]
            )
        )
    artifact["wording_audit"] = audit
    artifact["elapsed_seconds"] = round(time.time() - started, 1)
    return artifact


def gate_partition_internal_names(
    gate_partition: dict[str, Any],
    report_only: list[str],
    gated_4: list[str],
    anchor_eligible: list[str],
) -> dict[str, Any]:
    """The partition in v3 cell names, for the fragment writer."""
    return {
        "internal_gate_eligible": gated_4,
        "anchor_gate_eligible": anchor_eligible,
        "report_only": report_only,
    }


def main() -> None:
    artifact = run(verbose=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {ARTIFACT_PATH} ({ARTIFACT_PATH.stat().st_size} bytes)")
    frag = artifact["draft_gates_yaml_fragment"]
    print(
        f"draft block: {frag['n_lines']} lines, {frag['n_bytes']} bytes, sha256 {frag['text_sha256']}"
    )


if __name__ == "__main__":
    main()
