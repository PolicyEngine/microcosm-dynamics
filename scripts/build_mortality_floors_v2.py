"""Mortality floors v2: the 100-seed rebuild and the corrected estimand.

REPORTED ANCHOR, NOT A GATE RUN. Like ``mortality_floors_v1``, this
reads no gate, changes no gate and ratifies nothing; it is committed
evidence pinned by a reproduction test. It SUPERSEDES
``runs/mortality_floors_v1.json`` as the floor basis a future
differential-mortality gate ceremony (issue #74 Phase B) would derive
pre-registered thresholds from, and RETAINS v1 as the pre-lock record.
``gates.yaml`` is untouched by this artifact and by this script.

Three things change from v1, each because v1 is measurably wrong or
measurably underpowered, and each measured here rather than asserted.

1. **Seed count: 5 -> 100.** v1's floor is
   ``noise_floor_seeds_0_4`` (five person-disjoint half-splits). Five
   seeds cannot identify which cells sit inside the ``ln(1.5)`` power
   cap: a parametric bootstrap of the same estimator puts
   ``P(round(mean + 3*sd, 3) <= ln 1.5)`` near a coin flip for several
   cells v1 shows clearing. This artifact rebuilds at 100 seeds --
   ``gate_m4``'s ``floor_seeds 0-99`` precedent -- and publishes the
   bootstrap probability per cell so every promotion and demotion
   against v1 is MEASURED, not narrated. The 5-seed v1 floor is
   reproduced first, byte-for-byte, as a check that the two artifacts
   share one code path (``v1_reproduction_check``).

2. **The estimand is restated as the 1997+ window.** The PSID
   individual file carries FOUR weight series across the exposure
   window (``panels.DEMOGRAPHIC_CONCEPTS['weight']`` fallback order),
   switching at 1990, 1993 and 1997. They are not one estimand: the
   1993-1996 rung is a LONGITUDINAL weight and the 1997+ rung adds the
   immigrant sample. Measured here: pre-1997 slices carry ~39.8% of the
   unweighted death events but ~0.096% of the WEIGHTED exposure, so
   v1's "all" window is numerically the 1997+ window
   (``|ln(m_all / m_1997+)|`` below 4e-4 in every cell). The declared
   universe is therefore CORE/IMM CROSS-SECTION 1997-2023, and v1's
   caveat that "older decades bias PSID UPWARD, against the undercount"
   is WITHDRAWN: the bias it claims rides on 0.096% of the weighted
   denominator and cannot offset anything. Both universes are built at
   100 seeds so the restatement is a measurement.

3. **The sex-differential dominance band is computed.** v1 proposed a
   shape anchor in prose and measured none of it. The gated internal
   cells that survive at 100 seeds (75-84 and 85+) are the bands with
   the SMALLEST male/female gaps, so a sex-flat candidate reproduces
   them; the differential is visible only through a dominance anchor.
   This artifact measures the per-band dominance invariant over every
   real half, finds the widest contiguous band set with zero
   inversions, and reports its margin in half-split sd units at
   ``MARGIN_K = 3``. REPORTED, NOT GATED -- whether a 3-sigma margin is
   acceptable is the ceremony's ruling, not this artifact's.

Scope of the ``ln(1.5)`` cap, stated because the record is easy to
misread. ``gates.yaml:5396-5405`` (``gate_m6.not_certified[0]``) says
"No admissible pooling of the 25-84 surface clears the ln(1.5) cap even
fully pooled (best tolerance ~0.472 vs cap 0.4055)". That is a true
statement about ``gate_m6``'s TEMPORAL-HOLDOUT drift surface, whose
fully pooled ``death.25-84`` rung carries 308 events
(``runs/m6_holdout_floors_v4.json`` ``coarsening_ladder.ladders.death``).
It is not a statement about THIS surface: the person-disjoint half-split
runs on 3,775 death events, a 12.3x event base, and answers
REPRODUCTION rather than DRIFT. Nothing here weakens
``gate_m6.not_certified[0]``; mortality drift stays uncertified.

Run from the repository root with the PSID individual file staged::

    .venv/bin/python scripts/build_mortality_floors_v2.py

It needs no populace-fit (real-vs-real / real-vs-external only).
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

from populace_dynamics.data import deaths, panels, psid  # noqa: E402
from populace_dynamics.harness import panel as hpanel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "runs" / "mortality_floors_v2.json"
V1_PATH = ROOT / "runs" / "mortality_floors_v1.json"
NCHS_PATH = ROOT / "data" / "external" / "nchs_life_tables_2023.json"
ARTIFACT_SCHEMA_VERSION = "mortality_floors.v2"

#: 100 person-disjoint half-split seeds -- the gate_m4 floor precedent
#: (gates.yaml:3128, floor_seeds 0-99). v1 used five.
FLOOR_SEEDS: tuple[int, ...] = tuple(range(100))
V1_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)

#: The declared weight universe: intervals whose START wave is at or
#: after the CORE/IMM INDIVIDUAL CROSS-SECTION WT switch.
DECLARED_UNIVERSE_START = 1997

#: Power cap. ln(1.5) is the cap every locked tranche in gates.yaml
#: uses; it is quoted here as the yardstick a cell is measured against,
#: and this artifact gates nothing with it.
T_MAX = math.log(1.5)

#: Anchor margin multiple, the gate_m4 convention (a candidate's own
#: simulated invariant must exceed MARGIN_K x the real half-split sd).
MARGIN_K = 3

#: Bands the age-gradient companion invariant is measured over.
AGE_GRADIENT_BANDS: tuple[str, ...] = ("55-64", "65-74", "75-84", "85+")

#: Parametric-bootstrap settings for the seed-count stability study.
BOOTSTRAP_SEED = 20260906
BOOTSTRAP_B_5 = 200_000
BOOTSTRAP_B_100 = 20_000

#: Fixed cell order; the bootstrap's per-cell rng stream is keyed on a
#: cell's index in it, so adding a cell never moves another's draws.
CELL_ORDER: tuple[str, ...] = tuple(
    v1b._key(band, sex) for band in v1b.BAND_LABELS for sex in v1b.SEXES
)


# --------------------------------------------------------------------------
# Weight-series universe
# --------------------------------------------------------------------------
def _canonical_series(label: str) -> str:
    """Strip a PSID label's trailing two-digit wave year."""
    return re.sub(r"\s*\d{2}\s*$", "", label).strip()


def weight_series_by_wave() -> dict[int, str]:
    """Wave year -> canonical weight-series name actually resolved.

    Replays ``panels._resolve_concepts``' fallback order for the
    ``weight`` concept against the real ``ind2023er`` label space, so
    the series a slice's start-wave weight came from is read from the
    file's own labels rather than assumed.
    """
    sps_path = (
        psid._resolve_data_dir(None)
        / psid.PRODUCTS["ind2023er"][0]
        / psid.PRODUCTS["ind2023er"][2]
    )
    labels = psid.parse_sps_labels(sps_path)
    merged: dict[int, str] = {}
    for pattern in panels.DEMOGRAPHIC_CONCEPTS["weight"]:
        for year, name in panels.wave_variables(labels, pattern).items():
            merged.setdefault(year, name)
    return {year: _canonical_series(labels[n]) for year, n in merged.items()}


def weight_universe_report(
    slices: pd.DataFrame, series_by_wave: dict[int, str]
) -> dict[str, Any]:
    """Per-series and pre/post-1997 exposure and death shares.

    The measurement behind the estimand restatement: which weight
    series each slice's start-wave weight came from, what share of the
    WEIGHTED exposure denominator it carries, and what share of the
    UNWEIGHTED death events.
    """
    df = slices.copy()
    df["series"] = df.start_wave.map(series_by_wave)
    df["we"] = df.weight * df.exposure
    total_we = float(df.we.sum())
    total_d = float(df.death.sum())

    by_series: dict[str, Any] = {}
    for name, grp in df.groupby("series", observed=True):
        waves = sorted(int(w) for w in grp.start_wave.unique())
        by_series[str(name)] = {
            "start_waves_present": [waves[0], waves[-1]],
            "n_slices": int(len(grp)),
            "weighted_exposure_py": float(grp.we.sum()),
            "share_of_weighted_exposure": float(grp.we.sum() / total_we),
            "deaths_unwt": int(round(float(grp.death.sum()))),
            "share_of_unweighted_deaths": float(grp.death.sum() / total_d),
            "mean_slice_weight": float(grp.weight.mean()),
            "max_slice_weight": float(grp.weight.max()),
        }

    def _side(mask: pd.Series) -> dict[str, Any]:
        grp = df[mask]
        return {
            "n_slices": int(len(grp)),
            "weighted_exposure_py": float(grp.we.sum()),
            "share_of_weighted_exposure": float(grp.we.sum() / total_we),
            "deaths_unwt": int(round(float(grp.death.sum()))),
            "share_of_unweighted_deaths": float(grp.death.sum() / total_d),
            "mean_slice_weight": float(grp.weight.mean()),
        }

    pre = df.start_wave < DECLARED_UNIVERSE_START
    return {
        "series_resolution_rule": (
            "populace_dynamics.data.panels.DEMOGRAPHIC_CONCEPTS['weight'] "
            "ordered fallback, replayed against the real ind2023er label "
            "space; a slice's series is the one resolved at its START wave"
        ),
        "series_by_wave": {
            str(y): s for y, s in sorted(series_by_wave.items())
        },
        "n_series_across_window": len(set(series_by_wave.values())),
        "by_series": by_series,
        "pre_1997": _side(pre),
        "from_1997": _side(~pre),
    }


def universe_equivalence(slices: pd.DataFrame) -> dict[str, Any]:
    """Per cell ``|ln(m_all / m_1997+)|`` -- the restatement, measured.

    If v1's "all" window is numerically the 1997+ window, these are all
    near zero and the pre-1997 slices supply no separate estimand.
    """
    haz_all = v1b.weighted_hazards(slices)
    haz_dec = v1b.weighted_hazards(
        slices[slices.start_wave >= DECLARED_UNIVERSE_START]
    )
    per_cell: dict[str, Any] = {}
    for key in CELL_ORDER:
        m_all = haz_all.get(key, {}).get("psid_m", 0.0)
        m_dec = haz_dec.get(key, {}).get("psid_m", 0.0)
        per_cell[key] = {
            "m_all": float(m_all),
            "m_1997_plus": float(m_dec),
            "abs_log_ratio": (
                float(abs(math.log(m_all / m_dec)))
                if m_all > 0 and m_dec > 0
                else None
            ),
        }
    defined = [
        c["abs_log_ratio"]
        for c in per_cell.values()
        if c["abs_log_ratio"] is not None
    ]
    return {
        "statistic": "|ln(m_all_window / m_1997_plus_window)| per band x sex",
        "per_cell": per_cell,
        "max_abs_log_ratio": float(max(defined)) if defined else None,
        "n_cells_compared": len(defined),
    }


# --------------------------------------------------------------------------
# One seed: person-disjoint half-split on the PINNED full frame
# --------------------------------------------------------------------------
def _kish(weights: np.ndarray) -> float:
    """Kish effective count ``(sum w)^2 / sum w^2`` (0 when empty)."""
    if weights.size == 0:
        return 0.0
    total = float(weights.sum())
    sq = float((weights**2).sum())
    return float(total * total / sq) if sq > 0 else 0.0


def _half_stats(half: pd.DataFrame) -> tuple[dict[str, Any], dict[str, float]]:
    """Band x sex hazards plus per-cell Kish effective death counts."""
    haz = v1b.weighted_hazards(half)
    dead = half[half.death > 0]
    kish: dict[str, float] = {}
    for (band, sex), grp in dead.groupby(["band", "sex"], observed=True):
        kish[v1b._key(band, sex)] = _kish(grp.weight.to_numpy(np.float64))
    return haz, kish


def measure_seed(
    seed: int, slices: pd.DataFrame, *, start_year_min: int | None
) -> dict[str, Any]:
    """One seed's half-split, in v1's cell shape plus v2's extras.

    SPLIT FRAME PIN. The split is always taken on the FULL slice frame
    -- every age, every start wave, before any universe restriction --
    and the window filter is applied to each side AFTERWARDS. This is
    v1's convention and it is load-bearing: restricting the frame
    before the split changes which persons are drawn and moves every
    tolerance, and it is what makes the two universes comparable
    seed-by-seed (both see the identical person partition).
    """
    side_a, side_b = hpanel.split_panel_by_person(
        slices, "person_id", fraction=0.5, seed=seed
    )
    n_a = int(side_a.person_id.nunique())
    n_b = int(side_b.person_id.nunique())
    if start_year_min is not None:
        side_a = side_a[side_a.start_wave >= start_year_min]
        side_b = side_b[side_b.start_wave >= start_year_min]

    haz_a, kish_a = _half_stats(side_a)
    haz_b, kish_b = _half_stats(side_b)

    cells: dict[str, Any] = {}
    for key in CELL_ORDER:
        a = haz_a.get(key)
        b = haz_b.get(key)
        m_a = a["psid_m"] if a else 0.0
        m_b = b["psid_m"] if b else 0.0
        defined = m_a > 0 and m_b > 0
        cells[key] = {
            "m_a": float(m_a),
            "m_b": float(m_b),
            "n_death_a": int(a["psid_deaths_unwt"]) if a else 0,
            "n_death_b": int(b["psid_deaths_unwt"]) if b else 0,
            "kish_death_a": float(kish_a.get(key, 0.0)),
            "kish_death_b": float(kish_b.get(key, 0.0)),
            "log_ratio_abs": (
                float(abs(np.log(m_a / m_b))) if defined else None
            ),
            "pct_diff_abs": (
                float(abs(m_a - m_b) / m_b * 100.0) if defined else None
            ),
        }
    return {
        "seed": seed,
        "n_persons_side_a": n_a,
        "n_persons_side_b": n_b,
        "cells": cells,
        "hazards_side_a": {k: v["psid_m"] for k, v in haz_a.items()},
        "hazards_side_b": {k: v["psid_m"] for k, v in haz_b.items()},
    }


# --------------------------------------------------------------------------
# Pooling: the 100-seed floor and the cell stability table
# --------------------------------------------------------------------------
def _tolerance(mean: float, sd: float, k: int) -> float:
    """``round(mean + k*sd, 3)`` -- the shared derivation convention."""
    return round(mean + k * sd, 3)


def pool_floor(
    per_seed: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Across-seed floor and cell stability for one universe.

    The floor block follows v1's convention (``mean``/``sd``/``values``
    of ``|ln(m_A/m_B)|``) plus ``realized_sigma`` -- the RMS of the
    floor values, the ``runs/m4_gate_floors_v1.json`` convention a
    half-normal operating characteristic is read against.

    The stability block reproduces v1's rule (defined on every seed AND
    >= 20 UNWEIGHTED deaths on the weaker half of the worst seed) and
    additionally REPORTS the Kish effective weighted death count and
    whether the k=3 tolerance clears the cap. Nothing here is a gate
    rule; the eligibility rule is a ceremony question, recorded in
    ``open_questions_for_the_ceremony``.
    """
    floors: dict[str, Any] = {}
    stability: dict[str, Any] = {}
    n_seeds = len(per_seed)
    for key in CELL_ORDER:
        ratios = [s["cells"][key]["log_ratio_abs"] for s in per_seed]
        pcts = [s["cells"][key]["pct_diff_abs"] for s in per_seed]
        min_deaths = min(
            min(s["cells"][key]["n_death_a"], s["cells"][key]["n_death_b"])
            for s in per_seed
        )
        min_kish = min(
            min(
                s["cells"][key]["kish_death_a"],
                s["cells"][key]["kish_death_b"],
            )
            for s in per_seed
        )
        defined_seeds = sum(v is not None for v in ratios)

        block = None
        if defined_seeds == n_seeds:
            block = v1b._summary([float(v) for v in ratios])
            values = np.asarray(block["values"], dtype=np.float64)
            block["realized_sigma"] = float(np.sqrt((values**2).mean()))
            block["pct_diff_abs"] = v1b._summary([float(v) for v in pcts])
            floors[key] = block

        entry: dict[str, Any] = {
            "defined_seeds": defined_seeds,
            "n_seeds": n_seeds,
            "min_deaths_either_half": int(min_deaths),
            "min_effective_deaths_kish": round(float(min_kish), 3),
            "v1_rule_gate_eligible": bool(
                defined_seeds == n_seeds
                and min_deaths >= v1b.MIN_DEATHS_FOR_GATE
            ),
        }
        if block is not None:
            entry["realized_sigma"] = block["realized_sigma"]
            for k in (2, 3, 4):
                entry[f"tolerance_k{k}"] = _tolerance(
                    block["mean"], block["sd"], k
                )
            entry["tolerance_sigma_units_k3"] = round(
                entry["tolerance_k3"] / block["realized_sigma"], 3
            )
            entry["clears_t_max_at_k3"] = bool(entry["tolerance_k3"] <= T_MAX)
        else:
            entry["clears_t_max_at_k3"] = False

        if defined_seeds < n_seeds:
            entry["report_reason"] = "undefined_on_some_seed"
        elif not entry["clears_t_max_at_k3"]:
            entry["report_reason"] = "tolerance_above_t_max"
        elif min_deaths < v1b.MIN_DEATHS_FOR_GATE:
            entry["report_reason"] = "below_20_deaths_weaker_half"
        else:
            entry["report_reason"] = "clears_t_max_at_k3"
        stability[key] = entry
    return floors, stability


def k_sensitivity(stability: dict[str, Any]) -> dict[str, Any]:
    """Which cells clear the cap at each k -- the gate_m4 shape."""
    out: dict[str, Any] = {}
    for k in (2, 3, 4):
        cells = sorted(
            key
            for key, v in stability.items()
            if v.get(f"tolerance_k{k}") is not None
            and v[f"tolerance_k{k}"] <= T_MAX
        )
        out[str(k)] = {"n_clearing_t_max": len(cells), "cells": cells}
    return out


# --------------------------------------------------------------------------
# Seed-count stability: the parametric bootstrap
# --------------------------------------------------------------------------
def _bootstrap_block(
    sigma: float, n_draws: int, n_boot: int, cell_index: int, stream: int
) -> dict[str, Any]:
    """``P(round(mean + 3*sd, 3) <= ln 1.5)`` for an n-seed floor.

    Draws ``n_draws`` half-normal(sigma) values ``n_boot`` times -- the
    faithful null a real-vs-real floor statistic follows if the two
    halves differ only by sampling noise -- and forms the same
    ``round(mean + 3*sd, 3)`` tolerance the derivation convention uses.
    The rng stream is keyed on (BOOTSTRAP_SEED, stream, cell_index), so
    every cell is independently reproducible and adding a cell never
    moves another's draws.
    """
    rng = np.random.default_rng([BOOTSTRAP_SEED, stream, cell_index])
    draws = np.abs(rng.normal(0.0, sigma, size=(n_boot, n_draws)))
    tol = np.round(draws.mean(axis=1) + 3.0 * draws.std(axis=1, ddof=1), 3)
    return {
        "sigma": float(sigma),
        "n_draws": int(n_draws),
        "n_bootstrap": int(n_boot),
        "rng": (
            f"numpy.random.default_rng([{BOOTSTRAP_SEED}, {stream}, "
            f"<cell_index in cell_order>])"
        ),
        "p_tolerance_at_or_below_t_max": float((tol <= T_MAX).mean()),
        "tolerance_pct05": float(np.percentile(tol, 5)),
        "tolerance_pct50": float(np.percentile(tol, 50)),
        "tolerance_pct95": float(np.percentile(tol, 95)),
    }


def seed_count_stability(
    v1_floor: dict[str, Any], v2_floor: dict[str, Any]
) -> dict[str, Any]:
    """Per cell: could a 5-seed floor have identified the partition?

    Three bootstraps per cell. ``at_5_seeds_sigma_v1`` uses the
    COMMITTED v1 5-seed RMS as sigma and asks whether a five-seed draw
    would place the cell inside the cap at all -- the measurement that
    demotes v1's partition. ``at_5_seeds_sigma_v2`` repeats it with the
    better 100-seed sigma. ``at_100_seeds_sigma_v2`` asks the same of
    the seed count this artifact actually uses.
    """
    per_cell: dict[str, Any] = {}
    for index, key in enumerate(CELL_ORDER):
        v1_block = v1_floor.get(key)
        v2_block = v2_floor.get(key)
        entry: dict[str, Any] = {}
        if v1_block is not None:
            v1_values = np.asarray(v1_block["values"], dtype=np.float64)
            entry["sigma_v1_5_seed"] = float(np.sqrt((v1_values**2).mean()))
            entry["at_5_seeds_sigma_v1"] = _bootstrap_block(
                entry["sigma_v1_5_seed"], 5, BOOTSTRAP_B_5, index, 1
            )
        if v2_block is not None:
            entry["sigma_v2_100_seed"] = v2_block["realized_sigma"]
            entry["at_5_seeds_sigma_v2"] = _bootstrap_block(
                entry["sigma_v2_100_seed"], 5, BOOTSTRAP_B_5, index, 2
            )
            entry["at_100_seeds_sigma_v2"] = _bootstrap_block(
                entry["sigma_v2_100_seed"], 100, BOOTSTRAP_B_100, index, 3
            )
        per_cell[key] = entry
    return {
        "question": (
            "For each band x sex cell, with what probability would a "
            "floor built at n seeds place the cell's k=3 tolerance at "
            "or below the ln(1.5) cap, if the floor statistic follows "
            "the faithful half-normal null at the cell's own sigma? A "
            "probability near 0.5 means the seed count, not the data, "
            "decides the cell's partition."
        ),
        "method": (
            "parametric bootstrap: draw n half-normal(sigma) values, "
            "form round(mean + 3*sd, 3) with the ddof=1 sd the "
            "derivation convention uses, repeat n_bootstrap times"
        ),
        "t_max": T_MAX,
        "cell_order": list(CELL_ORDER),
        "per_cell": per_cell,
    }


def partition_movement(
    v1_stability: dict[str, Any], v2_stability: dict[str, Any]
) -> dict[str, Any]:
    """v1's clearing set vs v2's, cell by cell, with the reason."""
    v1_clears = {
        key
        for key, v in v1_stability.items()
        if v.get("tolerance_k3") is not None and v["tolerance_k3"] <= T_MAX
    }
    v2_clears = {
        key for key, v in v2_stability.items() if v["clears_t_max_at_k3"]
    }
    return {
        "basis": (
            "the k=3 tolerance round(mean + 3*sd, 3) against T_max = "
            "ln(1.5), computed identically on the v1 5-seed floor and "
            "the v2 100-seed floor of the DECLARED universe"
        ),
        "v1_5_seed_clearing": sorted(v1_clears),
        "v2_100_seed_clearing": sorted(v2_clears),
        "demoted_by_the_rebuild": sorted(v1_clears - v2_clears),
        "promoted_by_the_rebuild": sorted(v2_clears - v1_clears),
        "unchanged": sorted(v1_clears & v2_clears),
    }


# --------------------------------------------------------------------------
# Anchor invariants (REPORTED, NOT GATED)
# --------------------------------------------------------------------------
def _half_hazard_vectors(
    per_seed: list[dict[str, Any]], *, sides: tuple[str, ...]
) -> list[dict[str, float]]:
    """Flatten the requested halves into hazard dicts, one per half."""
    out: list[dict[str, float]] = []
    for entry in per_seed:
        for side in sides:
            out.append(entry[f"hazards_side_{side}"])
    return out


def _dominance_by_band(
    hazards: dict[str, float],
) -> dict[str, float | None]:
    """``log(m_male / m_female)`` per band for one hazard vector."""
    out: dict[str, float | None] = {}
    for band in v1b.BAND_LABELS:
        m_m = hazards.get(v1b._key(band, "male"), 0.0)
        m_f = hazards.get(v1b._key(band, "female"), 0.0)
        out[band] = float(math.log(m_m / m_f)) if m_m > 0 and m_f > 0 else None
    return out


def _contiguous_runs(bands: list[str]) -> list[list[str]]:
    """Maximal contiguous runs of ``bands`` in BAND_LABELS order."""
    chosen = set(bands)
    runs: list[list[str]] = []
    current: list[str] = []
    for band in v1b.BAND_LABELS:
        if band in chosen:
            current.append(band)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def sex_dominance_anchor(
    full_panel: dict[str, float],
    halves_side_a: list[dict[str, float]],
    halves_both: list[dict[str, float]],
) -> dict[str, Any]:
    """The sex-differential dominance invariant. REPORTED, NOT GATED.

    Per band, ``log(m_male / m_female)`` on the full panel and on every
    real half. A band INVERTS on a half when the value is at or below
    zero there. A candidate band set is the widest CONTIGUOUS run of
    bands with zero inversions; the invariant scored over a set is the
    MIN over its bands, and its margin is the full-panel value divided
    by the sd of the per-half minima, quoted against ``MARGIN_K = 3``.

    The zero-inversion criterion and the margin are BOTH published
    under two half conventions, because they disagree here and the
    disagreement is the whole question. ``side_a`` is the 100 seed-s A
    halves -- gate_m4's "holds on all 100 real half-splits" convention.
    ``both_sides`` is all 200 halves, the stricter reading. Nothing is
    adopted: which convention governs is the ceremony's ruling.
    """

    def _table(halves: list[dict[str, float]]) -> dict[str, Any]:
        per_band: dict[str, Any] = {}
        for band in v1b.BAND_LABELS:
            vals = [
                v
                for v in (_dominance_by_band(h)[band] for h in halves)
                if v is not None
            ]
            arr = np.asarray(vals, dtype=np.float64)
            per_band[band] = {
                "n_halves_defined": int(arr.size),
                "n_halves_total": len(halves),
                "mean": float(arr.mean()) if arr.size else None,
                "sd": float(arr.std(ddof=1)) if arr.size > 1 else None,
                "min": float(arr.min()) if arr.size else None,
                "n_inversions": int((arr <= 0).sum()) if arr.size else None,
            }
        return per_band

    tables = {
        "side_a": _table(halves_side_a),
        "both_sides": _table(halves_both),
    }
    halves_by_convention = {
        "side_a": halves_side_a,
        "both_sides": halves_both,
    }

    zero_inversion: dict[str, list[str]] = {}
    runs: dict[str, list[list[str]]] = {}
    selected: dict[str, list[str]] = {}
    for name, table in tables.items():
        clean = [
            band
            for band in v1b.BAND_LABELS
            if table[band]["n_inversions"] == 0
            and table[band]["n_halves_defined"]
            == len(halves_by_convention[name])
        ]
        zero_inversion[name] = clean
        runs[name] = _contiguous_runs(clean)
        selected[name] = max(runs[name], key=len) if runs[name] else []

    def _margin(
        band_set: list[str], halves: list[dict[str, float]]
    ) -> dict[str, Any]:
        mins = []
        for half in halves:
            per_band = _dominance_by_band(half)
            vals = [per_band[b] for b in band_set]
            if any(v is None for v in vals):
                continue
            mins.append(min(vals))
        arr = np.asarray(mins, dtype=np.float64)
        full_vals = [_dominance_by_band(full_panel)[b] for b in band_set]
        full_min = (
            float(min(full_vals))
            if full_vals and all(v is not None for v in full_vals)
            else None
        )
        sd = float(arr.std(ddof=1)) if arr.size > 1 else None
        margin = (
            round(full_min / sd, 3) if sd and full_min is not None else None
        )
        return {
            "n_halves_scored": int(arr.size),
            "n_halves_offered": len(halves),
            "real_full_panel_min": full_min,
            "half_split_mean": float(arr.mean()) if arr.size else None,
            "half_split_sd": sd,
            "min_over_halves": float(arr.min()) if arr.size else None,
            "holds_on_every_half": bool(arr.size and arr.min() > 0),
            "margin_sigma_units": margin,
            "clears_margin_k": bool(margin is not None and margin >= MARGIN_K),
        }

    # Every contiguous run either criterion produces, plus the band set
    # the pre-registration packet named, each scored under both
    # conventions. Nothing is hidden behind a selection.
    candidates: list[list[str]] = []
    for name in tables:
        for run_bands in runs[name]:
            if run_bands not in candidates:
                candidates.append(run_bands)
    packet_band_set = ["45-54", "55-64", "65-74"]
    if packet_band_set not in candidates:
        candidates.append(packet_band_set)

    margins = {
        "+".join(band_set): {
            "band_set": band_set,
            "side_a": _margin(band_set, halves_side_a),
            "both_sides": _margin(band_set, halves_both),
        }
        for band_set in candidates
    }

    headline_set = selected["both_sides"]
    headline_key = "+".join(headline_set)
    return {
        "gated": False,
        "reported_not_gated": True,
        "statistic": (
            "min over a contiguous band set of log(m_male / m_female); "
            "the invariant is level-free, so the PSID mortality "
            "undercount does not touch it"
        ),
        "margin_k": MARGIN_K,
        "band_selection_rule": (
            "the widest CONTIGUOUS run of bands whose dominance is "
            "defined and strictly positive on every real half (the "
            "gate_m4 evidence-time condition 'holds on every real "
            "half-split'); bands that invert on any half are excluded. "
            "Applied under both half conventions because they select "
            "different sets here."
        ),
        "per_band": tables,
        "zero_inversion_bands": zero_inversion,
        "contiguous_runs": runs,
        "selected_band_set": selected,
        "conventions_disagree": bool(
            selected["side_a"] != selected["both_sides"]
        ),
        "packet_band_set": packet_band_set,
        "margins_by_band_set": margins,
        "headline": {
            "band_set": headline_set,
            "selection_convention": "both_sides",
            "why": (
                "the stricter criterion; it is the set the "
                "pre-registration packet named, and it is the only one "
                "of the two that survives an inversion scan over all "
                "200 halves"
            ),
            "margin_sigma_units_side_a": margins[headline_key]["side_a"][
                "margin_sigma_units"
            ],
            "margin_sigma_units_both_sides": margins[headline_key][
                "both_sides"
            ]["margin_sigma_units"],
            "clears_margin_k_side_a": margins[headline_key]["side_a"][
                "clears_margin_k"
            ],
            "clears_margin_k_both_sides": margins[headline_key]["both_sides"][
                "clears_margin_k"
            ],
            "thinness_note": (
                "this margin is thin against precedent: gate_m4's four "
                "anchor cells sit at 4.797-12.806 sd units "
                "(gates.yaml:3395, :3438, :3472, :3514). A margin "
                "barely above MARGIN_K is a referee question, not a "
                "measurement this artifact can settle."
            ),
        },
        "why_this_matters": (
            "the internal cells that clear the cap at 100 seeds are "
            "75-84 and 85+, the two bands with the SMALLEST male/female "
            "log gaps, so a candidate that assigns both sexes one "
            "hazard reproduces them. The dominance invariant is the "
            "only measured surface here that sees the sex differential "
            "at all. It is REPORTED, not gated: whether a margin this "
            "size is acceptable, and under which half convention, is "
            "the ceremony's ruling."
        ),
    }


def _adjacent_log_gaps(
    hazards: dict[str, float], sex: str, bands: tuple[str, ...]
) -> dict[str, float | None]:
    """``ln(m_next / m_band)`` for each adjacent pair of ``bands``."""
    gaps: dict[str, float | None] = {}
    for lo, hi in zip(bands[:-1], bands[1:], strict=True):
        m_lo = hazards.get(v1b._key(lo, sex), 0.0)
        m_hi = hazards.get(v1b._key(hi, sex), 0.0)
        gaps[f"{lo}->{hi}"] = (
            float(math.log(m_hi / m_lo)) if m_lo > 0 and m_hi > 0 else None
        )
    return gaps


def _min_adjacent_gap(
    hazards: dict[str, float], sex: str, bands: tuple[str, ...]
) -> float | None:
    """The min adjacent log gap over ``bands``, or None if any is undefined."""
    gaps = _adjacent_log_gaps(hazards, sex, bands)
    values = list(gaps.values())
    if any(v is None for v in values):
        return None
    return float(min(values))


def age_gradient_companion(
    full_panel: dict[str, float],
    halves_side_a: list[dict[str, float]],
    halves_both: list[dict[str, float]],
) -> dict[str, Any]:
    """Age-gradient min-adjacent-log-gap. REPORTED, NOT GATED.

    Not commissioned by this build; computed because it falls out of
    the same per-half hazard vectors the dominance invariant needs, and
    the ceremony's band-restriction question needs the same inversion
    evidence for the gradient as for dominance. Recorded as a companion
    so no one has to rerun the 100 seeds to get it.
    """
    all_bands = tuple(v1b.BAND_LABELS)
    halves_by_convention = {
        "side_a": halves_side_a,
        "both_sides": halves_both,
    }

    def _inversions(
        halves: list[dict[str, float]], sex: str
    ) -> dict[str, int]:
        gaps = [_adjacent_log_gaps(h, sex, all_bands) for h in halves]
        return {
            pair: sum(1 for g in gaps if g[pair] is not None and g[pair] <= 0)
            for pair in _adjacent_log_gaps(full_panel, sex, all_bands)
        }

    def _stats(halves: list[dict[str, float]], sex: str) -> dict[str, Any]:
        vals = [
            v
            for v in (
                _min_adjacent_gap(h, sex, AGE_GRADIENT_BANDS) for h in halves
            )
            if v is not None
        ]
        arr = np.asarray(vals, dtype=np.float64)
        full = _min_adjacent_gap(full_panel, sex, AGE_GRADIENT_BANDS)
        sd = float(arr.std(ddof=1)) if arr.size > 1 else None
        margin = round(full / sd, 3) if sd and full is not None else None
        return {
            "n_halves": int(arr.size),
            "real_full_panel_min_gap": full,
            "half_split_sd": sd,
            "min_over_halves": float(arr.min()) if arr.size else None,
            "holds_on_every_half": bool(arr.size and arr.min() > 0),
            "margin_sigma_units": margin,
            "clears_margin_k": bool(margin is not None and margin >= MARGIN_K),
        }

    by_sex: dict[str, Any] = {}
    for sex in v1b.SEXES:
        by_sex[sex] = {
            "full_panel_adjacent_gaps_all_bands": _adjacent_log_gaps(
                full_panel, sex, all_bands
            ),
            "adjacent_gap_inversions": {
                name: _inversions(halves, sex)
                for name, halves in halves_by_convention.items()
            },
            "n_halves_scanned": {
                name: len(halves)
                for name, halves in halves_by_convention.items()
            },
            "side_a_convention": _stats(halves_side_a, sex),
            "both_sides_convention": _stats(halves_both, sex),
        }

    return {
        "gated": False,
        "reported_not_gated": True,
        "commissioned": False,
        "statistic": (
            "min adjacent log gap ln(m_{next band} / m_{band}) over the "
            "measured band set, per sex"
        ),
        "margin_k": MARGIN_K,
        "measured_band_set": list(AGE_GRADIENT_BANDS),
        "note": (
            "companion evidence, produced from the same per-half "
            "hazard vectors as the dominance invariant; it is not part "
            "of what this build was asked for and gates nothing"
        ),
        "by_sex": by_sex,
    }


# --------------------------------------------------------------------------
# v1 reproduction check
# --------------------------------------------------------------------------
def v1_reproduction_check(
    slices: pd.DataFrame, v1_artifact: dict[str, Any]
) -> dict[str, Any]:
    """Rebuild v1's 5-seed floor and compare to the committed bytes.

    Run FIRST, before anything v2-specific, so a mismatch stops the
    build: if the committed 5-seed artifact does not come back out of
    this code path on this data, nothing downstream is comparable to it.
    """
    per_seed = [v1b.measure_seed_halfsplit(s, slices) for s in v1b.SEEDS]
    floor, stability = v1b.pool_internal_floor(per_seed)
    ref_inf = v1_artifact["internal_noise_floor"]
    ref_floor = ref_inf["noise_floor_seeds_0_4"]
    ref_stability = ref_inf["band_sex_stability"]

    max_diff = 0.0
    for key, block in floor.items():
        for got, ref in zip(
            block["values"], ref_floor[key]["values"], strict=True
        ):
            max_diff = max(max_diff, abs(float(got) - float(ref)))
    ref_anchor = v1_artifact["external_anchor"]["windows"]["all"]
    nchs_rates = v1b.nchs_band_rates(json.loads(NCHS_PATH.read_text()))
    anchor = v1b.external_anchor(slices, nchs_rates, start_year_min=None)
    return {
        "purpose": (
            "v2 supersedes v1 only if it comes off the same code path "
            "and the same data; this rebuilds the committed 5-seed "
            "floor and the committed all-window anchor first and "
            "compares them to the committed bytes"
        ),
        "v1_artifact": str(V1_PATH.relative_to(ROOT)),
        "v1_artifact_sha256": _sha_of_file(V1_PATH),
        "seeds": list(v1b.SEEDS),
        "cells_compared": len(floor),
        "max_abs_diff_in_floor_values": float(max_diff),
        "floor_values_reproduce_exactly": bool(max_diff == 0.0),
        "stability_blocks_identical": bool(stability == ref_stability),
        "n_slices_reproduced": int(len(slices)),
        "n_slices_committed": int(ref_anchor["n_slices"]),
        "total_death_events_unwt_reproduced": int(
            anchor["total_death_events_unwt"]
        ),
        "total_death_events_unwt_committed": int(
            ref_anchor["total_death_events_unwt"]
        ),
        "total_exposure_py_weighted_reproduced": float(
            anchor["total_exposure_py_weighted"]
        ),
        "total_exposure_py_weighted_committed": float(
            ref_anchor["total_exposure_py_weighted"]
        ),
        "v1_5_seed_floor": floor,
        "v1_5_seed_stability": stability,
    }


#: Every gates.yaml line this artifact cites, as (line number, what it
#: is). The builder reads the line's actual text into the artifact so a
#: reproduction test can re-read gates.yaml and catch a citation that
#: has gone stale -- a mis-cited line is exactly the defect the
#: pre-registration packet found in the record this rebuild answers.
GATES_CITATIONS: tuple[tuple[int, str], ...] = (
    (2906, "gate_m4 block start"),
    (3128, "gate_m4 floor_seeds (the 100-seed precedent)"),
    (3395, "gate_m4 anchor cell 1 margin"),
    (3438, "gate_m4 anchor cell 2 margin"),
    (3472, "gate_m4 anchor cell 3 margin"),
    (3514, "gate_m4 anchor cell 4 margin"),
    (5324, "gate_m6 block start"),
    (5395, "gate_m6.not_certified[0] margin name"),
    (5396, "the ln(1.5) cap claim, first cited line"),
    (5398, "the ln(1.5) cap claim, the pooling sentence"),
    (5399, "the ln(1.5) cap claim, the ~0.472 figure"),
    (5405, "the ln(1.5) cap claim, last cited line"),
    (5541, "gate_m6 floor_seeds"),
    (5737, "external mortality LEVELS stay ungated, first cited line"),
    (5738, "external mortality LEVELS stay ungated, the ruling"),
    (5740, "external mortality LEVELS stay ungated, last cited line"),
)


def gates_yaml_citations() -> dict[str, Any]:
    """The exact text at every gates.yaml line this artifact cites."""
    path = ROOT / "gates.yaml"
    lines = path.read_text().splitlines()
    return {
        "file": "gates.yaml",
        "sha256": _sha_of_file(path),
        "n_lines": len(lines),
        "rule": (
            "each entry records the line number this artifact cites and "
            "the exact stripped text at that line when the artifact was "
            "built. A reproduction test re-reads gates.yaml and compares, "
            "so a citation that goes stale fails loudly instead of "
            "quietly pointing at the wrong rule."
        ),
        "citations": [
            {
                "line": line,
                "what": what,
                "text": lines[line - 1].strip(),
            }
            for line, what in GATES_CITATIONS
        ],
    }


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------
def _sha_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(cwd: Path) -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd)
            .decode()
            .strip()
        )
    except Exception:
        return None


# --------------------------------------------------------------------------
# The NOT-RATIFIED note
# --------------------------------------------------------------------------
def proposed_thresholds_note(
    stability: dict[str, Any],
    movement: dict[str, Any],
    weights: dict[str, Any],
    dominance: dict[str, Any],
) -> str:
    clearing = sorted(
        k for k, v in stability.items() if v["clears_t_max_at_k3"]
    )
    not_clearing = sorted(
        k for k, v in stability.items() if not v["clears_t_max_at_k3"]
    )
    pre_exp = weights["pre_1997"]["share_of_weighted_exposure"]
    pre_d = weights["pre_1997"]["share_of_unweighted_deaths"]
    headline = dominance["headline"]
    margin = headline["margin_sigma_units_side_a"]
    return (
        "PROPOSED VALIDATION BASIS FOR THE DIFFERENTIAL-MORTALITY "
        "COMPONENT -- NOT RATIFIED.\n\n"
        "This artifact supersedes runs/mortality_floors_v1.json as the "
        "FLOOR BASIS and ratifies nothing. It reads no gate, changes no "
        "gate, edits no threshold and touches gates.yaml not at all. "
        "Ratification still requires the full ceremony (issue #74 "
        "comment 4907496891): floors -> thresholds with machine-bound "
        "derivations -> an adversarial referee round -> verification -> "
        "maintainer ratification by merge. No candidate has been scored "
        "against anything here.\n\n"
        "STATISTIC. Per age band x sex, the weighted PSID central death "
        "rate m(band, sex) = sum(w * death) / sum(w * exposure) over the "
        "person-interval exposure slices, on the DECLARED weight "
        "universe. A candidate-vs-PSID discrepancy would be scored as "
        "|ln(m_candidate / m_PSID)|.\n\n"
        "SEED COUNT. 100 person-disjoint half-split seeds (0-99), the "
        "gate_m4 floor precedent. v1's five seeds cannot identify the "
        "partition: the committed seed-count stability bootstrap puts "
        "P(a 5-seed floor places the cell at or below ln(1.5)) near a "
        "coin flip for several cells v1 shows clearing. Against v1's "
        "5-seed clearing set, the rebuild DEMOTES "
        f"{movement['demoted_by_the_rebuild']} and PROMOTES "
        f"{movement['promoted_by_the_rebuild']}. Cells whose k=3 "
        f"tolerance clears ln(1.5) at 100 seeds: {clearing}. Cells above "
        f"the cap at k=3: {not_clearing}. k itself is NOT fixed here -- "
        "tolerances at k=2, 3 and 4 are all published per cell and the "
        "choice is the ceremony's.\n\n"
        "WEIGHT UNIVERSE. The declared universe is CORE/IMM INDIVIDUAL "
        "CROSS-SECTION WT, start waves 1997-2023. Four weight series "
        "span the full exposure window and they are not one estimand. "
        f"Measured: pre-1997 slices carry {100 * pre_d:.2f}% of the "
        f"unweighted death events but {100 * pre_exp:.4f}% of the "
        "weighted exposure, so v1's 'all' window is numerically the "
        "1997+ window. v1's caveat that older decades bias PSID UPWARD "
        "against the undercount is WITHDRAWN, not restated: a bias "
        "riding on that share of the denominator offsets nothing. The "
        "pre-1997 slices are published as a report-only sensitivity "
        "(the 'all' universe floor is carried in full) and are never "
        "pooled into the declared statistic.\n\n"
        "EXTERNAL ANCHOR. The NCHS 2023 US period life tables "
        "(data/external/nchs_life_tables_2023.json, sha-pinned), "
        "aggregated to these bands. Because PSID undercounts mortality "
        "(every reported ratio below 1), the anchor must NOT gate a "
        "level match to NCHS -- that would reject reality. Carried "
        "forward from v1 verbatim, and reinforced by gates.yaml:5737-"
        "5740 (|ln|-gating external mortality LEVELS stays REJECTED).\n\n"
        "SEX DIFFERENTIAL. The internal cells that clear the cap at 100 "
        "seeds are the bands with the SMALLEST male/female gaps, so "
        "they cannot see the differential: a sex-flat candidate "
        "reproduces them. The dominance invariant over "
        f"{headline['band_set']} is measured here at {margin} "
        "half-split sd units (side-A convention; "
        f"{headline['margin_sigma_units_both_sides']} over all 200 "
        f"halves) against MARGIN_K = {MARGIN_K}. That is thin against "
        "the gate_m4 anchor precedent of 4.797-12.806 sd units, and it "
        "is REPORTED, NOT GATED. Any future gate that drops this cell "
        "must not be described as certifying DIFFERENTIAL "
        "mortality.\n\n"
        "SCOPE OF THE ln(1.5) CAP. gates.yaml:5396-5405 records that no "
        "admissible pooling of the 25-84 surface clears ln(1.5) even "
        "fully pooled (~0.472). That is gate_m6's TEMPORAL-HOLDOUT "
        "DRIFT surface (308 events fully pooled). This is the "
        "person-disjoint REPRODUCTION surface (3,775 events). The two "
        "answer different questions and nothing here weakens "
        "gate_m6.not_certified[0]: mortality DRIFT stays uncertified.\n\n"
        "BASELINE CONVENTION. Mortality feeds benefit levels through "
        "survival to and beyond claiming; any scored reform must state "
        "whether it runs against the scheduled or payable baseline "
        "(issue #74 protocol note 1). This artifact fixes none of that."
    )


def open_questions_for_the_ceremony() -> list[dict[str, str]]:
    """What this artifact deliberately does NOT settle."""
    return [
        {
            "question": "weighted vs unweighted event-count eligibility",
            "detail": (
                "v1's rule counts UNWEIGHTED deaths on the weaker half "
                "while the gated statistic is WEIGHTED. The Kish "
                "effective weighted count is published per cell "
                "(min_effective_deaths_kish) alongside the unweighted "
                "count so the ceremony can rule; this artifact applies "
                "NEITHER as a gate rule and reproduces v1's flag "
                "unchanged as v1_rule_gate_eligible."
            ),
        },
        {
            "question": "85+ eligibility for a reproduction gate",
            "detail": (
                "gate_m6 partitions death.85+|{male,female} report-only "
                "with the machine reason attrition_confounded_truth "
                "(runs/m6_holdout_floors_v4.json partition.report_only). "
                "Both 85+ cells clear the cap on this surface. Whether "
                "attrition confounding disqualifies them from a "
                "REPRODUCTION gate as it does from a DRIFT gate is a "
                "referee ruling, not a measurement; this artifact "
                "reports them and rules nothing."
            ),
        },
        {
            "question": "death-ascertainment convention",
            "detail": (
                "range-coded and unknown-year deaths are scored as "
                "SURVIVAL by the committed builder (full exposure, zero "
                "deaths, every interval). This artifact inherits that "
                "convention unchanged so it stays comparable to v1, and "
                "publishes the counts. Pinning a convention and "
                "measuring its bias is a ceremony deliverable."
            ),
        },
        {
            "question": "nonresponse censoring convention",
            "detail": (
                "exposure ends at a person's last observed wave, so a "
                "death more than one grid interval later is never "
                "counted. That is valid under non-informative "
                "nonresponse, and the undercount ratios published here "
                "are the direct measurement that the assumption fails. "
                "The convention must be declared with its violation "
                "named before any lock."
            ),
        },
        {
            "question": "k, and the MARGIN_K ruling for the anchor",
            "detail": (
                "tolerances at k=2, 3 and 4 are published per cell and "
                "no k is adopted here. The dominance anchor's margin is "
                "published in sd units under both the side-A and the "
                "both-sides half conventions; whether it is acceptable "
                "at MARGIN_K = 3, and under which convention, is the "
                "ceremony's ruling."
            ),
        },
    ]


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def run(verbose: bool = True) -> dict[str, Any]:
    started = time.time()

    nchs = json.loads(NCHS_PATH.read_text())
    nchs_rates = v1b.nchs_band_rates(nchs)
    v1_artifact = json.loads(V1_PATH.read_text())

    demo = panels.demographic_panel()
    death_records = deaths.read_death_records()
    slices = v1b.build_exposure_slices(demo, death_records)
    n_persons = int(slices.person_id.nunique())
    if verbose:
        print(
            f"exposure: {len(slices)} slices, {n_persons} persons, "
            f"{int(slices.death.sum())} death events"
        )

    # --- v1 first, as a check on the code path ---------------------------
    v1_check = v1_reproduction_check(slices, v1_artifact)
    if verbose:
        print(
            "v1 5-seed reproduction: max|diff| "
            f"{v1_check['max_abs_diff_in_floor_values']!r}, stability "
            f"identical {v1_check['stability_blocks_identical']}"
        )
    if not v1_check["floor_values_reproduce_exactly"]:
        raise RuntimeError(
            "the committed v1 5-seed floor did not reproduce; v2 is not "
            "comparable to it and the build stops"
        )
    if not v1_check["stability_blocks_identical"]:
        raise RuntimeError("v1 band_sex_stability did not reproduce")

    # --- the declared universe, measured ---------------------------------
    series_by_wave = weight_series_by_wave()
    weights = weight_universe_report(slices, series_by_wave)
    equivalence = universe_equivalence(slices)

    # --- 100-seed floors, both universes ---------------------------------
    per_seed_declared = [
        measure_seed(s, slices, start_year_min=DECLARED_UNIVERSE_START)
        for s in FLOOR_SEEDS
    ]
    per_seed_all = [
        measure_seed(s, slices, start_year_min=None) for s in FLOOR_SEEDS
    ]
    floor_declared, stability_declared = pool_floor(per_seed_declared)
    floor_all, stability_all = pool_floor(per_seed_all)

    # --- seed-count stability and the partition movement -----------------
    stability_bootstrap = seed_count_stability(
        v1_check["v1_5_seed_floor"], floor_declared
    )
    v1_stability_with_tol = {
        key: dict(
            v1_check["v1_5_seed_stability"][key],
            tolerance_k3=(
                _tolerance(
                    v1_check["v1_5_seed_floor"][key]["mean"],
                    v1_check["v1_5_seed_floor"][key]["sd"],
                    3,
                )
                if key in v1_check["v1_5_seed_floor"]
                else None
            ),
        )
        for key in CELL_ORDER
    }
    movement = partition_movement(v1_stability_with_tol, stability_declared)
    movement_all_universe = partition_movement(
        v1_stability_with_tol, stability_all
    )

    # --- anchor invariants on the declared universe ----------------------
    declared_slices = slices[slices.start_wave >= DECLARED_UNIVERSE_START]
    full_panel_haz = {
        k: v["psid_m"]
        for k, v in v1b.weighted_hazards(declared_slices).items()
    }
    halves_a = _half_hazard_vectors(per_seed_declared, sides=("a",))
    halves_both = _half_hazard_vectors(per_seed_declared, sides=("a", "b"))
    dominance = sex_dominance_anchor(full_panel_haz, halves_a, halves_both)
    gradient = age_gradient_companion(full_panel_haz, halves_a, halves_both)

    if verbose:
        for key in CELL_ORDER:
            st = stability_declared[key]
            print(
                f"  {key:>14}: T(k=3)={st.get('tolerance_k3')} "
                f"sigma={st.get('realized_sigma', 0):.5f} "
                f"minD={st['min_deaths_either_half']} "
                f"kish={st['min_effective_deaths_kish']} "
                f"{'CLEARS' if st['clears_t_max_at_k3'] else st['report_reason']}"
            )
        head = dominance["headline"]
        print(
            f"dominance band set {head['band_set']} margin "
            f"{head['margin_sigma_units_side_a']} sd (side A) / "
            f"{head['margin_sigma_units_both_sides']} sd (200 halves)"
        )

    anchor_all = v1b.external_anchor(slices, nchs_rates, start_year_min=None)
    anchor_recent = v1b.external_anchor(
        slices, nchs_rates, start_year_min=v1b.RECENT_START_YEAR
    )
    anchor_declared = v1b.external_anchor(
        slices, nchs_rates, start_year_min=DECLARED_UNIVERSE_START
    )

    artifact = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run": "mortality_floors_v2",
        "reported_anchor_not_gated": True,
        "component": "differential mortality (issue #74 Phase B; task B1)",
        "purpose": (
            "The mortality floor basis, rebuilt at 100 person-disjoint "
            "half-split seeds on a DECLARED weight universe, with the "
            "seed-count instability of the 5-seed predecessor measured "
            "rather than narrated and the sex-dominance invariant "
            "computed. This reads no gate and changes no gate on its "
            "own; gates.yaml is untouched. The pre-registered gate "
            "ceremony (issue #74 comment 4907496891) comes after. See "
            "proposed_thresholds_note (NOT RATIFIED)."
        ),
        "supersedes": {
            "artifact": str(V1_PATH.relative_to(ROOT)),
            "sha256": _sha_of_file(V1_PATH),
            "as": "the floor / derivation basis",
            "v1_retained_as": (
                "the pre-lock record and the first committed NCHS "
                "anchor. v1 is NOT deleted, NOT edited and its own "
                "reproduction test still pins it; it simply stops being "
                "a derivation basis, because five seeds cannot identify "
                "which cells sit inside the power cap (see "
                "seed_count_stability)."
            ),
        },
        "what_changed_from_v1": [
            "seed count 5 -> 100 (the gate_m4 floor_seeds 0-99 precedent)",
            "the weight universe is DECLARED (CORE/IMM cross-section, "
            "start waves 1997+) and the pre-1997 share is measured and "
            "quoted, not left implicit",
            "v1's biennial caveat that older decades bias PSID upward "
            "against the undercount is WITHDRAWN as numerically empty",
            "every cell carries the parametric-bootstrap probability "
            "that a 5-seed floor would have placed it inside the "
            "ln(1.5) cap, so the demotions are measured",
            "the sex-dominance invariant and its band set are computed "
            "over every real half and reported (NOT gated)",
            "cells carry realized_sigma, k=2/3/4 tolerances and the "
            "Kish effective weighted death count",
        ],
        "does_not_do": [
            "edit gates.yaml or any threshold",
            "score a candidate or run a gate",
            "adopt a k, a gate partition or an eligibility rule",
            "delete, edit or supersede any other runs/ artifact",
        ],
        "t_max_scope": {
            "t_max": T_MAX,
            "t_max_source": "ln(1.5)",
            "committed_claim": (
                "gates.yaml:5396-5405 (gate_m6.not_certified[0], "
                "margin mortality_drift): 'No admissible pooling of the "
                "25-84 surface clears the ln(1.5) cap even fully pooled "
                "(best tolerance ~0.472 vs cap 0.4055)'"
            ),
            "which_surface_that_claim_is_about": (
                "gate_m6's TEMPORAL-HOLDOUT drift surface. Its fully "
                "pooled death.25-84 rung carries 308 death events and a "
                "0.472 tolerance (runs/m6_holdout_floors_v4.json, "
                "coarsening_ladder.ladders.death, rung sex_pooled_age1, "
                "adopted_rung null, gated [])."
            ),
            "which_surface_this_artifact_is_about": (
                "the person-disjoint half-split REPRODUCTION surface, "
                "3775 unweighted death events on the full window and "
                "2273 on the declared 1997+ universe -- a different "
                "question (reproduction, not drift) on a much larger "
                "event base, the same split gate_m4 and gate_m6 already "
                "draw for disability."
            ),
            "what_this_artifact_does_not_claim": (
                "nothing here weakens gate_m6.not_certified[0]. "
                "Mortality DRIFT stays uncertified. A future "
                "reproduction gate built on this floor would certify "
                "reproduction and never drift."
            ),
            "m6_reference": {
                "artifact": "runs/m6_holdout_floors_v4.json",
                "sha256": _sha_of_file(
                    ROOT / "runs" / "m6_holdout_floors_v4.json"
                ),
                "fully_pooled_rung": "sex_pooled_age1",
                "fully_pooled_cell": "death.25-84",
                "fully_pooled_tolerance": 0.472,
                "fully_pooled_n_events_full": 308,
            },
        },
        "gates_yaml_citations": gates_yaml_citations(),
        "data": {
            "psid_population": v1_artifact["data"]["psid_population"],
            "n_persons_with_exposure": n_persons,
            "psid_wave_calendar": v1_artifact["data"]["psid_wave_calendar"],
            "death_record_counts": v1_artifact["data"]["death_record_counts"],
            "person_identity_check": {
                "rule": (
                    "this artifact is built on the FLOOR-BUILDER path "
                    "(build_mortality_floors.build_exposure_slices), "
                    "which emits real PSID person ids only, so the "
                    "person-disjoint split has a real key. Two "
                    "neighbouring facts, each read from its own bytes "
                    "and neither one true of the other file. (1) In "
                    "THIS repository at the build HEAD, "
                    "scripts/registered_m6_inputs.py emits SEVEN "
                    "columns and no person_id at all, so its inert "
                    "(0, 24) PAD_BAND rows carry no person identity to "
                    "collide with. (2) In the ACCEPTED ADAPTER "
                    "INCREMENT -- a different tree, git blob "
                    "c9cc6f1e71fab96ef830d7e7b434ee216f1a96c8, worktree "
                    "HEAD 12d782f84e18cda0293edba19389e7672ab80477, "
                    "recorded in dynamics-mortality-root-completion-"
                    "acceptance.json -- person_id leads the emitted "
                    "columns and the same two pad rows carry person_id "
                    "-1 (female) and -2 (male), disclosed there as "
                    "PAD_IDENTITY_DISCLOSURE: invented rows "
                    "corresponding to no PSID person. Neither file is "
                    "on this artifact's path; the check below is the "
                    "positive evidence that no such row reached any "
                    "number here, and a future gate run on the "
                    "registered path must exclude them explicitly."
                ),
                "min_person_id": int(slices.person_id.min()),
                "n_nonpositive_person_ids": int((slices.person_id <= 0).sum()),
                "no_pad_rows_present": bool(
                    int((slices.person_id <= 0).sum()) == 0
                ),
            },
        },
        "exposure_construction": {
            "unit": v1_artifact["exposure_construction"]["unit"],
            "rule": v1_artifact["exposure_construction"]["rule"],
            "weight": v1_artifact["exposure_construction"]["weight"],
            "biennial_caveats": [
                "deaths counted only in the one grid interval after an "
                "observed wave; later deaths of attriters are right-"
                "censored and NOT counted (part of the honest "
                "undercount). This is valid under non-informative "
                "nonresponse, and the undercount ratios in "
                "external_anchor are the direct measurement that the "
                "assumption fails",
                "range-coded and unknown-year deaths carry full "
                "exposure and zero deaths in every interval -- they are "
                "excluded from the NUMERATOR only, i.e. scored as "
                "survival. The convention is inherited from v1 "
                "unchanged so the two artifacts stay comparable; "
                "pinning one is a ceremony deliverable",
                "start-wave weight shared by a biennial interval's two "
                "slices; band assigned per slice-age",
                "the declared universe is a WEIGHT universe, not a "
                "period claim: it is 1997+ because that is where the "
                "CORE/IMM cross-section series begins, and the "
                "period-concept delta against a 2023 NCHS table is "
                "named separately in external_anchor",
            ],
            "withdrawn_v1_caveat": {
                "text": v1_artifact["exposure_construction"][
                    "biennial_caveats"
                ][1],
                "why_withdrawn": (
                    "it claims an offsetting upward bias from older "
                    "decades. Measured, pre-1997 slices carry "
                    f"{100 * weights['pre_1997']['share_of_weighted_exposure']:.4f}% "
                    "of the WEIGHTED exposure denominator, so no bias "
                    "riding on them can offset anything. Withdrawn, not "
                    "restated."
                ),
            },
        },
        "estimand": {
            "statistic": (
                "weighted PSID central death rate m(band, sex) = "
                "sum(w * death) / sum(w * exposure) over single-year "
                "person-interval exposure slices"
            ),
            "declared_weight_universe": (
                "CORE/IMM INDIVIDUAL CROSS-SECTION WT, interval start "
                "waves 1997-2023"
            ),
            "declared_universe_start_wave": DECLARED_UNIVERSE_START,
            "why_declared": (
                "four PSID weight series span the exposure window and "
                "they are not one estimand: the 1993-1996 rung is a "
                "LONGITUDINAL weight and the 1997+ rung adds the "
                "immigrant sample, a different target population"
            ),
            "weight_universe_measurement": weights,
            "universe_equivalence": equivalence,
            "consequence": (
                "v1's 'all' window is numerically the 1997+ window: "
                "pre-1997 slices supply "
                f"{100 * weights['pre_1997']['share_of_unweighted_deaths']:.2f}% "
                "of the unweighted death events but "
                f"{100 * weights['pre_1997']['share_of_weighted_exposure']:.4f}% "
                "of the weighted exposure, and "
                f"|ln(m_all / m_1997+)| <= {equivalence['max_abs_log_ratio']:.6f} "
                "in every band x sex cell. Both universes are built at "
                "100 seeds here so the restatement is measured; the "
                "'all' universe floor is retained as a report-only "
                "sensitivity and as the v1-comparable series."
            ),
        },
        "age_bands": list(v1b.BAND_LABELS),
        "sexes": list(v1b.SEXES),
        "cell_order": list(CELL_ORDER),
        "external_anchor": {
            "nchs_reference_file": str(NCHS_PATH.relative_to(ROOT)),
            "nchs_vintage_year": nchs["vintage_year"],
            "nchs_citation": nchs["report"]["nvsr_citation"],
            "nchs_reference_sha256": _sha_of_file(NCHS_PATH),
            "nchs_source_file_sha256": {
                pop: meta["sha256"]
                for pop, meta in nchs["fetch"]["source_files"].items()
            },
            "band_central_rate_formula": v1_artifact["external_anchor"][
                "band_central_rate_formula"
            ],
            "undercount_note": v1_artifact["external_anchor"][
                "undercount_note"
            ],
            "gating_ruling_inherited": (
                "the anchor must NOT gate a level match to NCHS -- that "
                "would reject reality (v1's own words, carried "
                "forward), reinforced by gates.yaml:5737-5740: "
                "'|ln|-gating external mortality LEVELS stays REJECTED'"
            ),
            "concept_deltas_named": [
                "ascertainment: a death is counted only in the one grid "
                "interval after an observed wave, so an attriter who "
                "dies later is right-censored and uncounted",
                "death dating: range-coded and unknown-year deaths are "
                "scored as survival",
                "weight universe: the declared window is 1997+ (see "
                "estimand)",
                "period: interval deaths against a 2023 period table",
            ],
            "windows": {
                "all": anchor_all,
                "recent": anchor_recent,
                "declared_1997_plus": anchor_declared,
            },
        },
        "internal_noise_floor": {
            "method": (
                "person-disjoint 50/50 half-split "
                "(populace_dynamics.harness.panel.split_panel_by_person, "
                "fraction=0.5, seeds 0-99) of the band x sex weighted "
                "hazards; the floor statistic is |ln(m_A / m_B)| "
                "between the two independent real halves"
            ),
            "split_unit": "person",
            "split_fraction": 0.5,
            "split_frame_pin": (
                "the split is taken on the FULL slice frame -- every "
                "age, every start wave, before any universe "
                "restriction -- and the window filter is applied to "
                "each side afterwards. This is v1's convention and it "
                "is load-bearing: restricting the frame before the "
                "split changes which persons are drawn and moves every "
                "tolerance. It also makes the two universes comparable "
                "seed by seed, because both see the identical person "
                "partition."
            ),
            "floor_seeds": list(FLOOR_SEEDS),
            "seed_count": len(FLOOR_SEEDS),
            "seed_count_precedent": (
                "gate_m4 floor_seeds 0-99 (gates.yaml:3128); gate_m6 "
                "floor_seeds [0, 99] (gates.yaml:5541)"
            ),
            "t_max": T_MAX,
            "t_max_source": "ln(1.5)",
            "tolerance_convention": (
                "round(mean + k * sd, 3) with the population-of-seeds "
                "sd at ddof=1 -- the tests/test_gates_derivations.py "
                "convention. realized_sigma is the RMS of the floor "
                "values (the runs/m4_gate_floors_v1.json convention)."
            ),
            "universes": {
                "declared_1997_plus": {
                    "start_year_min": DECLARED_UNIVERSE_START,
                    "role": "the declared estimand; the derivation basis",
                    "noise_floor_seeds_0_99": floor_declared,
                    "cell_stability": stability_declared,
                    "k_sensitivity": k_sensitivity(stability_declared),
                    "per_seed": per_seed_declared,
                },
                "all_v1_comparable": {
                    "start_year_min": None,
                    "role": (
                        "report-only sensitivity; the universe v1 used, "
                        "retained so the restatement is a measurement "
                        "and not an assertion"
                    ),
                    "noise_floor_seeds_0_99": floor_all,
                    "cell_stability": stability_all,
                    "k_sensitivity": k_sensitivity(stability_all),
                    "per_seed": per_seed_all,
                },
            },
            "universe_partition_agreement": {
                "declared_clearing_t_max_at_k3": sorted(
                    k
                    for k, v in stability_declared.items()
                    if v["clears_t_max_at_k3"]
                ),
                "all_clearing_t_max_at_k3": sorted(
                    k
                    for k, v in stability_all.items()
                    if v["clears_t_max_at_k3"]
                ),
                "agree": bool(
                    sorted(
                        k
                        for k, v in stability_declared.items()
                        if v["clears_t_max_at_k3"]
                    )
                    == sorted(
                        k
                        for k, v in stability_all.items()
                        if v["clears_t_max_at_k3"]
                    )
                ),
                "reading": (
                    "if the two universes agree at 100 seeds while v1's "
                    "5-seed partition differs from both, the seed "
                    "count, not the universe choice, is what identified "
                    "the partition"
                ),
            },
        },
        "v1_reproduction_check": v1_check,
        "seed_count_stability": stability_bootstrap,
        "partition_movement": {
            "declared_1997_plus": movement,
            "all_v1_comparable": movement_all_universe,
        },
        "anchor_invariants": {
            "reported_not_gated": True,
            "universe": "declared_1997_plus",
            "half_conventions": (
                "side_a = the 100 seed-s A halves (the gate_m4 'holds "
                "on all 100 real half-splits' convention); both_sides = "
                "all 200 halves. Both are published because they can "
                "disagree at the margin."
            ),
            "sex_dominance": dominance,
            "age_gradient_companion": gradient,
        },
        "open_questions_for_the_ceremony": open_questions_for_the_ceremony(),
        "proposed_thresholds_note": proposed_thresholds_note(
            stability_declared, movement, weights, dominance
        ),
        "revision_pins": {
            "populace_dynamics_sha": _git_sha(ROOT),
            "nchs_reference_sha256": _sha_of_file(NCHS_PATH),
            "v1_artifact_sha256": _sha_of_file(V1_PATH),
            "gates_yaml_sha256": _sha_of_file(ROOT / "gates.yaml"),
            "builder_v1_sha256": _sha_of_file(
                ROOT / "scripts" / "build_mortality_floors.py"
            ),
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        },
        "elapsed_seconds": round(time.time() - started, 1),
    }
    return artifact


def main() -> None:
    artifact = run(verbose=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
