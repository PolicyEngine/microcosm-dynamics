"""Tests for the mortality floors rebuild (runs/mortality_floors_v2.json).

The artifact is a REPORTED ANCHOR (reads no gate, changes no gate): the
100-seed person-disjoint half-split floor on a declared weight universe,
the measured instability of the 5-seed predecessor, the PSID-vs-NCHS
external anchor carried forward from v1, and the sex-dominance invariant
reported without gating it. It is pinned like the other ``runs/`` floors.

Two tiers, mirroring ``tests/test_mortality_floors.py``:

* Always-runnable tests touching only committed files. Everything the
  artifact asserts about itself recomputes from its own committed
  bytes: the pooled floors from the per-seed cells, the tolerances from
  the floors, the bootstrap probabilities from the committed sigmas and
  the stated rng, the dominance and age-gradient invariants from the
  committed per-half hazard vectors, the partition movement from the
  two floors, and the ``ln(1.5)`` scope claims from ``gates.yaml`` and
  ``runs/m6_holdout_floors_v4.json``. The embedded v1 reproduction is
  checked against the committed ``runs/mortality_floors_v1.json``, so
  v2 is tied to v1 without touching PSID. No reform is scored here and
  ``gates.yaml`` is checked to be innocent of this artifact.
* A seed-0 + anchor + weight-series reproduction pin (skipped when the
  PSID individual file is absent) that rebuilds the exposure slices and
  reruns the declared-universe seed-0 half-split, the v1 seed-0
  half-split and the declared anchor, matching the committed numbers to
  float precision -- with populace.fit never imported.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "mortality_floors_v2.json"
V1_ARTIFACT = ROOT / "runs" / "mortality_floors_v1.json"
M6_FLOORS = ROOT / "runs" / "m6_holdout_floors_v4.json"
NCHS = ROOT / "data" / "external" / "nchs_life_tables_2023.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"

T_MAX = math.log(1.5)
UNIVERSES = ("declared_1997_plus", "all_v1_comparable")

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
needs_real_ind = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir(),
    reason="PSID ind2023er not staged",
)


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _v1() -> dict:
    return json.loads(V1_ARTIFACT.read_text())


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_mortality_floors_v2 as builder

    return builder


def _universe(art: dict, name: str) -> dict:
    return art["internal_noise_floor"]["universes"][name]


# --------------------------------------------------------------------------
# Framing: reported anchor, nothing ratified, gates.yaml innocent
# --------------------------------------------------------------------------
def test_schema_and_reported_anchor():
    art = _artifact()
    assert art["schema_version"] == "mortality_floors.v2"
    assert art["run"] == "mortality_floors_v2"
    assert art["reported_anchor_not_gated"] is True
    assert "changes no gate" in art["purpose"]
    assert "gates.yaml is untouched" in art["purpose"]
    assert "differential mortality" in art["component"]
    note = art["proposed_thresholds_note"]
    assert "NOT RATIFIED" in note
    assert "referee round" in note
    assert "ratifies nothing" in note


def test_no_reform_scored_and_nothing_adopted():
    art = _artifact()
    assert "reform" not in art
    assert "gate_result" not in art
    assert "thresholds" not in art
    joined = " ".join(art["does_not_do"]).lower()
    assert "edit gates.yaml" in joined
    assert "score a candidate" in joined
    # No cell carries a bare "gate_eligible" verdict: the only
    # eligibility flag is explicitly labelled as v1's rule, reproduced.
    for name in UNIVERSES:
        for cell in _universe(art, name)["cell_stability"].values():
            assert "gate_eligible" not in cell
            assert "v1_rule_gate_eligible" in cell


def test_gates_yaml_does_not_read_this_artifact():
    """The rebuild is evidence, not a wired-in derivation basis."""
    gates_text = GATES.read_text()
    assert "mortality_floors_v2" not in gates_text
    assert "gate_mortality" not in gates_text


def test_supersession_is_declared_and_v1_is_retained():
    art = _artifact()
    sup = art["supersedes"]
    assert sup["artifact"] == "runs/mortality_floors_v1.json"
    assert (
        sup["sha256"] == hashlib.sha256(V1_ARTIFACT.read_bytes()).hexdigest()
    )
    assert "NOT deleted" in sup["v1_retained_as"]
    assert V1_ARTIFACT.is_file()


# --------------------------------------------------------------------------
# Seed count: 100, stated, and honoured everywhere
# --------------------------------------------------------------------------
def test_seed_count_is_100_and_stated_everywhere():
    art = _artifact()
    inf = art["internal_noise_floor"]
    assert inf["floor_seeds"] == list(range(100))
    assert inf["seed_count"] == 100
    assert "0-99" in inf["method"]
    assert "gate_m4" in inf["seed_count_precedent"]
    for name in UNIVERSES:
        universe = _universe(art, name)
        per_seed = universe["per_seed"]
        assert [s["seed"] for s in per_seed] == list(range(100))
        assert universe["noise_floor_seeds_0_99"]
        for block in universe["noise_floor_seeds_0_99"].values():
            assert block["n_seeds"] == 100
            assert len(block["values"]) == 100
        for cell in universe["cell_stability"].values():
            assert cell["n_seeds"] == 100


def test_pooled_floor_recomputes_from_per_seed():
    art = _artifact()
    for name in UNIVERSES:
        universe = _universe(art, name)
        per_seed = universe["per_seed"]
        for key, block in universe["noise_floor_seeds_0_99"].items():
            ratios = [s["cells"][key]["log_ratio_abs"] for s in per_seed]
            assert all(v is not None for v in ratios), (name, key)
            assert block["values"] == pytest.approx(ratios)
            assert block["mean"] == pytest.approx(np.mean(ratios))
            assert block["sd"] == pytest.approx(np.std(ratios, ddof=1))
            assert block["min"] == pytest.approx(min(ratios))
            assert block["max"] == pytest.approx(max(ratios))
            pct = [s["cells"][key]["pct_diff_abs"] for s in per_seed]
            assert block["pct_diff_abs"]["values"] == pytest.approx(pct)
            assert block["pct_diff_abs"]["mean"] == pytest.approx(np.mean(pct))


def test_per_seed_cells_are_internally_consistent():
    art = _artifact()
    for name in UNIVERSES:
        for seed in _universe(art, name)["per_seed"]:
            for key, cell in seed["cells"].items():
                if cell["log_ratio_abs"] is None:
                    assert cell["m_a"] == 0 or cell["m_b"] == 0, key
                    continue
                assert cell["log_ratio_abs"] == pytest.approx(
                    abs(math.log(cell["m_a"] / cell["m_b"]))
                ), (name, key)
                assert cell["pct_diff_abs"] == pytest.approx(
                    abs(cell["m_a"] - cell["m_b"]) / cell["m_b"] * 100.0
                ), (name, key)


def test_realized_sigma_is_the_rms_of_the_floor_values():
    """The runs/m4_gate_floors_v1.json convention, reused verbatim."""
    art = _artifact()
    for name in UNIVERSES:
        for key, block in _universe(art, name)[
            "noise_floor_seeds_0_99"
        ].items():
            values = np.asarray(block["values"], dtype=np.float64)
            assert block["realized_sigma"] == pytest.approx(
                float(np.sqrt((values**2).mean()))
            ), (name, key)


def test_tolerances_follow_the_derivation_convention():
    """tolerance_k = round(mean + k*sd, 3), and the cap test matches."""
    art = _artifact()
    assert art["internal_noise_floor"]["t_max"] == pytest.approx(T_MAX)
    for name in UNIVERSES:
        universe = _universe(art, name)
        floors = universe["noise_floor_seeds_0_99"]
        for key, cell in universe["cell_stability"].items():
            if key not in floors:
                assert cell["clears_t_max_at_k3"] is False
                assert "tolerance_k3" not in cell
                continue
            block = floors[key]
            for k in (2, 3, 4):
                assert cell[f"tolerance_k{k}"] == round(
                    block["mean"] + k * block["sd"], 3
                ), (name, key, k)
            assert cell["clears_t_max_at_k3"] is bool(
                cell["tolerance_k3"] <= T_MAX
            ), (name, key)
            assert cell["tolerance_sigma_units_k3"] == round(
                cell["tolerance_k3"] / block["realized_sigma"], 3
            ), (name, key)


def test_report_reason_matches_the_recorded_fields():
    art = _artifact()
    for name in UNIVERSES:
        for key, cell in _universe(art, name)["cell_stability"].items():
            if cell["defined_seeds"] < cell["n_seeds"]:
                expected = "undefined_on_some_seed"
            elif not cell["clears_t_max_at_k3"]:
                expected = "tolerance_above_t_max"
            elif cell["min_deaths_either_half"] < 20:
                expected = "below_20_deaths_weaker_half"
            else:
                expected = "clears_t_max_at_k3"
            assert cell["report_reason"] == expected, (name, key)


def test_k_sensitivity_matches_the_tolerances():
    art = _artifact()
    for name in UNIVERSES:
        universe = _universe(art, name)
        stability = universe["cell_stability"]
        for k, block in universe["k_sensitivity"].items():
            expected = sorted(
                key
                for key, cell in stability.items()
                if cell.get(f"tolerance_k{k}") is not None
                and cell[f"tolerance_k{k}"] <= T_MAX
            )
            assert block["cells"] == expected, (name, k)
            assert block["n_clearing_t_max"] == len(expected)


def test_kish_effective_counts_recompute_and_gate_nothing():
    art = _artifact()
    for name in UNIVERSES:
        universe = _universe(art, name)
        per_seed = universe["per_seed"]
        for key, cell in universe["cell_stability"].items():
            expected = min(
                min(
                    s["cells"][key]["kish_death_a"],
                    s["cells"][key]["kish_death_b"],
                )
                for s in per_seed
            )
            assert cell["min_effective_deaths_kish"] == pytest.approx(
                round(expected, 3)
            ), (name, key)
            expected_deaths = min(
                min(s["cells"][key]["n_death_a"], s["cells"][key]["n_death_b"])
                for s in per_seed
            )
            assert cell["min_deaths_either_half"] == expected_deaths
            assert cell["v1_rule_gate_eligible"] is bool(
                cell["defined_seeds"] == cell["n_seeds"]
                and expected_deaths >= 20
            ), (name, key)
    questions = " ".join(
        q["question"] for q in art["open_questions_for_the_ceremony"]
    )
    assert "weighted vs unweighted event-count eligibility" in questions


# --------------------------------------------------------------------------
# The v1 reproduction check, against the committed v1 bytes
# --------------------------------------------------------------------------
def test_v1_reproduction_check_matches_the_committed_v1_artifact():
    art = _artifact()
    check = art["v1_reproduction_check"]
    v1 = _v1()
    assert check["v1_artifact"] == "runs/mortality_floors_v1.json"
    assert (
        check["v1_artifact_sha256"]
        == hashlib.sha256(V1_ARTIFACT.read_bytes()).hexdigest()
    )
    assert check["seeds"] == [0, 1, 2, 3, 4]
    assert check["floor_values_reproduce_exactly"] is True
    assert check["max_abs_diff_in_floor_values"] == 0.0
    assert check["stability_blocks_identical"] is True

    ref_floor = v1["internal_noise_floor"]["noise_floor_seeds_0_4"]
    assert set(check["v1_5_seed_floor"]) == set(ref_floor)
    for key, block in check["v1_5_seed_floor"].items():
        assert block["values"] == ref_floor[key]["values"], key
        assert block["mean"] == ref_floor[key]["mean"], key
        assert block["sd"] == ref_floor[key]["sd"], key
    assert (
        check["v1_5_seed_stability"]
        == v1["internal_noise_floor"]["band_sex_stability"]
    )

    ref_anchor = v1["external_anchor"]["windows"]["all"]
    assert check["n_slices_committed"] == ref_anchor["n_slices"]
    assert check["n_slices_reproduced"] == ref_anchor["n_slices"]
    assert (
        check["total_death_events_unwt_reproduced"]
        == ref_anchor["total_death_events_unwt"]
    )
    assert check["total_exposure_py_weighted_reproduced"] == pytest.approx(
        ref_anchor["total_exposure_py_weighted"], abs=1e-6
    )


def test_partition_movement_recomputes_from_the_two_floors():
    art = _artifact()
    check = art["v1_reproduction_check"]
    v1_clearing = sorted(
        key
        for key, block in check["v1_5_seed_floor"].items()
        if round(block["mean"] + 3 * block["sd"], 3) <= T_MAX
    )
    for name in UNIVERSES:
        movement = art["partition_movement"][name]
        stability = _universe(art, name)["cell_stability"]
        v2_clearing = sorted(
            key for key, c in stability.items() if c["clears_t_max_at_k3"]
        )
        assert movement["v1_5_seed_clearing"] == v1_clearing
        assert movement["v2_100_seed_clearing"] == v2_clearing
        assert movement["demoted_by_the_rebuild"] == sorted(
            set(v1_clearing) - set(v2_clearing)
        )
        assert movement["promoted_by_the_rebuild"] == sorted(
            set(v2_clearing) - set(v1_clearing)
        )
        assert movement["unchanged"] == sorted(
            set(v1_clearing) & set(v2_clearing)
        )
    # The rebuild really does move the partition -- otherwise the
    # artifact's reason for existing is unevidenced.
    declared = art["partition_movement"]["declared_1997_plus"]
    assert declared["demoted_by_the_rebuild"]
    assert declared["promoted_by_the_rebuild"]


def test_universe_partition_agreement_recomputes():
    art = _artifact()
    agreement = art["internal_noise_floor"]["universe_partition_agreement"]
    for name, field in (
        ("declared_1997_plus", "declared_clearing_t_max_at_k3"),
        ("all_v1_comparable", "all_clearing_t_max_at_k3"),
    ):
        assert agreement[field] == sorted(
            key
            for key, c in _universe(art, name)["cell_stability"].items()
            if c["clears_t_max_at_k3"]
        )
    assert agreement["agree"] is bool(
        agreement["declared_clearing_t_max_at_k3"]
        == agreement["all_clearing_t_max_at_k3"]
    )


# --------------------------------------------------------------------------
# Seed-count stability: the bootstrap recomputes from committed bytes
# --------------------------------------------------------------------------
def test_seed_count_bootstrap_recomputes_from_committed_sigmas():
    """Every published probability re-draws from the stated rng."""
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert "populace.fit" not in sys.modules

    art = _artifact()
    stability = art["seed_count_stability"]
    assert stability["t_max"] == pytest.approx(T_MAX)
    assert stability["cell_order"] == art["cell_order"]

    streams = {
        "at_5_seeds_sigma_v1": 1,
        "at_5_seeds_sigma_v2": 2,
        "at_100_seeds_sigma_v2": 3,
    }
    for index, key in enumerate(art["cell_order"]):
        entry = stability["per_cell"][key]
        for field, stream in streams.items():
            if field not in entry:
                continue
            block = entry[field]
            got = builder._bootstrap_block(
                block["sigma"],
                block["n_draws"],
                block["n_bootstrap"],
                index,
                stream,
            )
            assert got == block, (key, field)


def test_bootstrap_sigmas_come_from_the_committed_floors():
    art = _artifact()
    check = art["v1_reproduction_check"]["v1_5_seed_floor"]
    floors = _universe(art, "declared_1997_plus")["noise_floor_seeds_0_99"]
    for key, entry in art["seed_count_stability"]["per_cell"].items():
        if "sigma_v1_5_seed" in entry:
            values = np.asarray(check[key]["values"], dtype=np.float64)
            assert entry["sigma_v1_5_seed"] == pytest.approx(
                float(np.sqrt((values**2).mean()))
            ), key
            assert entry["at_5_seeds_sigma_v1"]["sigma"] == pytest.approx(
                entry["sigma_v1_5_seed"]
            )
            assert entry["at_5_seeds_sigma_v1"]["n_draws"] == 5
        if "sigma_v2_100_seed" in entry:
            assert entry["sigma_v2_100_seed"] == pytest.approx(
                floors[key]["realized_sigma"]
            ), key
            assert entry["at_100_seeds_sigma_v2"]["n_draws"] == 100


def test_the_demoted_cells_are_the_ones_the_bootstrap_calls_unstable():
    """The demotions are MEASURED, which is the artifact's whole claim.

    Every cell v1's five seeds placed inside the cap but 100 seeds do
    not is a cell whose 5-seed bootstrap probability is far from
    certain -- i.e. the seed draw, not the data, put it there.
    """
    art = _artifact()
    per_cell = art["seed_count_stability"]["per_cell"]
    demoted = art["partition_movement"]["declared_1997_plus"][
        "demoted_by_the_rebuild"
    ]
    assert demoted
    for key in demoted:
        p = per_cell[key]["at_5_seeds_sigma_v1"][
            "p_tolerance_at_or_below_t_max"
        ]
        assert 0.0 < p < 0.9, (key, p)
    for key in art["partition_movement"]["declared_1997_plus"]["unchanged"]:
        assert (
            per_cell[key]["at_100_seeds_sigma_v2"][
                "p_tolerance_at_or_below_t_max"
            ]
            > 0.9
        ), key


# --------------------------------------------------------------------------
# The corrected estimand
# --------------------------------------------------------------------------
def test_estimand_declares_the_1997_universe():
    art = _artifact()
    estimand = art["estimand"]
    assert estimand["declared_universe_start_wave"] == 1997
    assert "CROSS-SECTION" in estimand["declared_weight_universe"]
    weights = estimand["weight_universe_measurement"]
    assert weights["n_series_across_window"] == 4
    assert _universe(art, "declared_1997_plus")["start_year_min"] == 1997
    assert _universe(art, "all_v1_comparable")["start_year_min"] is None


def test_weight_series_shares_are_a_partition():
    art = _artifact()
    weights = art["estimand"]["weight_universe_measurement"]
    by_series = weights["by_series"]
    assert sum(
        s["share_of_weighted_exposure"] for s in by_series.values()
    ) == pytest.approx(1.0)
    assert sum(
        s["share_of_unweighted_deaths"] for s in by_series.values()
    ) == pytest.approx(1.0)
    assert (
        sum(s["n_slices"] for s in by_series.values())
        == art["external_anchor"]["windows"]["all"]["n_slices"]
    )
    pre, post = weights["pre_1997"], weights["from_1997"]
    assert pre["share_of_weighted_exposure"] + post[
        "share_of_weighted_exposure"
    ] == pytest.approx(1.0)
    assert pre["share_of_unweighted_deaths"] + post[
        "share_of_unweighted_deaths"
    ] == pytest.approx(1.0)
    assert (
        post["n_slices"]
        == art["external_anchor"]["windows"]["declared_1997_plus"]["n_slices"]
    )


def test_the_pre_1997_share_is_quoted_and_is_the_stated_asymmetry():
    """Many deaths, almost no weighted exposure -- the finding itself."""
    art = _artifact()
    weights = art["estimand"]["weight_universe_measurement"]
    pre = weights["pre_1997"]
    assert pre["share_of_unweighted_deaths"] > 0.35
    assert pre["share_of_weighted_exposure"] < 0.002
    assert pre["mean_slice_weight"] < weights["from_1997"]["mean_slice_weight"]
    # The numbers are quoted in prose, not only stored as fields.
    consequence = art["estimand"]["consequence"]
    assert f"{100 * pre['share_of_unweighted_deaths']:.2f}%" in consequence
    assert f"{100 * pre['share_of_weighted_exposure']:.4f}%" in consequence
    assert f"{100 * pre['share_of_unweighted_deaths']:.2f}%" in (
        art["proposed_thresholds_note"]
    )


def test_all_window_is_numerically_the_declared_window():
    art = _artifact()
    equivalence = art["estimand"]["universe_equivalence"]
    values = [
        c["abs_log_ratio"]
        for c in equivalence["per_cell"].values()
        if c["abs_log_ratio"] is not None
    ]
    assert len(values) == len(art["cell_order"])
    assert equivalence["max_abs_log_ratio"] == pytest.approx(max(values))
    assert equivalence["max_abs_log_ratio"] < 1e-3
    for key, cell in equivalence["per_cell"].items():
        assert cell["abs_log_ratio"] == pytest.approx(
            abs(math.log(cell["m_all"] / cell["m_1997_plus"]))
        ), key


def test_the_v1_caveat_is_withdrawn_verbatim_and_not_restated():
    art = _artifact()
    withdrawn = art["exposure_construction"]["withdrawn_v1_caveat"]
    v1_caveats = _v1()["exposure_construction"]["biennial_caveats"]
    assert withdrawn["text"] == v1_caveats[1]
    assert "bias PSID UPWARD" in withdrawn["text"]
    assert "Withdrawn, not" in withdrawn["why_withdrawn"]
    # The withdrawn claim does not survive anywhere in v2's own caveats.
    for caveat in art["exposure_construction"]["biennial_caveats"]:
        assert "bias PSID UPWARD" not in caveat


# --------------------------------------------------------------------------
# External anchor: carried forward with v1's undercount accounting
# --------------------------------------------------------------------------
def test_nchs_reference_pinned_by_sha256():
    art = _artifact()
    committed_sha = hashlib.sha256(NCHS.read_bytes()).hexdigest()
    assert art["external_anchor"]["nchs_reference_sha256"] == committed_sha
    assert art["revision_pins"]["nchs_reference_sha256"] == committed_sha
    assert art["external_anchor"]["nchs_vintage_year"] == 2023
    ref = json.loads(NCHS.read_text())
    carried = art["external_anchor"]["nchs_source_file_sha256"]
    for pop, meta in ref["fetch"]["source_files"].items():
        assert carried[pop] == meta["sha256"]


def test_v1_undercount_accounting_is_carried_forward_verbatim():
    art = _artifact()
    v1 = _v1()
    for field in (
        "undercount_note",
        "band_central_rate_formula",
    ):
        assert (
            art["external_anchor"][field] == v1["external_anchor"][field]
        ), field
    assert (
        "must NOT gate a level match"
        in art["external_anchor"]["gating_ruling_inherited"]
    )
    assert len(art["external_anchor"]["concept_deltas_named"]) >= 4


def test_undercount_reported_not_calibrated_in_every_window():
    art = _artifact()
    windows = art["external_anchor"]["windows"]
    assert set(windows) == {"all", "recent", "declared_1997_plus"}
    for name, window in windows.items():
        ratios = [
            c["ratio"]
            for c in window["by_band_sex"].values()
            if c["ratio"] is not None
        ]
        assert ratios, name
        assert all(r < 1.0 for r in ratios), name
        assert window["ratio_summary"]["median_ratio"] < 1.0, name


def test_external_ratios_recompute_from_parts():
    art = _artifact()
    for name, window in art["external_anchor"]["windows"].items():
        for key, cell in window["by_band_sex"].items():
            if cell["ratio"] is None:
                continue
            assert cell["psid_m"] == pytest.approx(
                cell["psid_deaths_wt"] / cell["psid_exposure_py"]
            ), (name, key)
            assert cell["ratio"] == pytest.approx(
                cell["psid_m"] / cell["nchs_M"]
            ), (name, key)


def test_nchs_band_rates_recompute_from_reference():
    art = _artifact()
    ref = json.loads(NCHS.read_text())

    def band_bounds(band: str) -> tuple[int, int]:
        if band.endswith("+"):
            return int(band[:-1]), 120
        lo, hi = band.split("-")
        return int(lo), int(hi)

    window = art["external_anchor"]["windows"]["declared_1997_plus"]
    for key, cell in window["by_band_sex"].items():
        band, sex = key.split("|")
        lo, hi = band_bounds(band)
        rows = {r["age"]: r for r in ref["tables"][sex]}
        lx = {a: rows[a]["lx"] for a in rows}
        tx = {a: rows[a]["Tx"] for a in rows}
        assert cell["nchs_M"] == pytest.approx(
            (lx[lo] - lx.get(hi + 1, 0.0)) / (tx[lo] - tx.get(hi + 1, 0.0))
        ), key


# --------------------------------------------------------------------------
# Anchor invariants: reported, never gated, and recomputable
# --------------------------------------------------------------------------
def _half_hazards(art: dict, sides: tuple[str, ...]) -> list[dict]:
    per_seed = _universe(art, "declared_1997_plus")["per_seed"]
    return [
        entry[f"hazards_side_{side}"] for entry in per_seed for side in sides
    ]


def test_sex_dominance_is_reported_not_gated():
    art = _artifact()
    invariants = art["anchor_invariants"]
    assert invariants["reported_not_gated"] is True
    assert invariants["universe"] == "declared_1997_plus"
    dominance = invariants["sex_dominance"]
    assert dominance["gated"] is False
    assert dominance["reported_not_gated"] is True
    assert dominance["margin_k"] == 3
    assert "the ceremony's ruling" in dominance["why_this_matters"]


def test_sex_dominance_per_band_table_recomputes_from_per_seed_hazards():
    art = _artifact()
    dominance = art["anchor_invariants"]["sex_dominance"]
    for name, sides in (("side_a", ("a",)), ("both_sides", ("a", "b"))):
        halves = _half_hazards(art, sides)
        for band, entry in dominance["per_band"][name].items():
            values = []
            for half in halves:
                m_m = half.get(f"{band}|male", 0.0)
                m_f = half.get(f"{band}|female", 0.0)
                if m_m > 0 and m_f > 0:
                    values.append(math.log(m_m / m_f))
            arr = np.asarray(values, dtype=np.float64)
            assert entry["n_halves_total"] == len(halves)
            assert entry["n_halves_defined"] == arr.size, (name, band)
            assert entry["mean"] == pytest.approx(arr.mean()), (name, band)
            assert entry["sd"] == pytest.approx(arr.std(ddof=1)), (name, band)
            assert entry["min"] == pytest.approx(arr.min()), (name, band)
            assert entry["n_inversions"] == int((arr <= 0).sum()), (name, band)


def test_sex_dominance_band_selection_follows_its_stated_rule():
    art = _artifact()
    dominance = art["anchor_invariants"]["sex_dominance"]
    bands = art["age_bands"]
    for name in ("side_a", "both_sides"):
        table = dominance["per_band"][name]
        clean = [b for b in bands if table[b]["n_inversions"] == 0]
        assert dominance["zero_inversion_bands"][name] == clean, name
        runs, current = [], []
        for band in bands:
            if band in set(clean):
                current.append(band)
            elif current:
                runs.append(current)
                current = []
        if current:
            runs.append(current)
        assert dominance["contiguous_runs"][name] == runs, name
        assert dominance["selected_band_set"][name] == max(runs, key=len), name
    assert dominance["conventions_disagree"] is bool(
        dominance["selected_band_set"]["side_a"]
        != dominance["selected_band_set"]["both_sides"]
    )
    headline = dominance["headline"]
    assert headline["selection_convention"] == "both_sides"
    assert headline["band_set"] == dominance["selected_band_set"]["both_sides"]
    # The band set the pre-registration packet named is scored too, so a
    # referee can compare like for like.
    assert dominance["packet_band_set"] == ["45-54", "55-64", "65-74"]
    assert "+".join(dominance["packet_band_set"]) in (
        dominance["margins_by_band_set"]
    )


def test_sex_dominance_margins_recompute_from_per_seed_hazards():
    art = _artifact()
    dominance = art["anchor_invariants"]["sex_dominance"]
    full_panel = art["external_anchor"]["windows"]["declared_1997_plus"][
        "by_band_sex"
    ]
    for entry in dominance["margins_by_band_set"].values():
        band_set = entry["band_set"]
        full_min = min(
            math.log(
                full_panel[f"{b}|male"]["psid_m"]
                / full_panel[f"{b}|female"]["psid_m"]
            )
            for b in band_set
        )
        for name, sides in (("side_a", ("a",)), ("both_sides", ("a", "b"))):
            block = entry[name]
            assert block["real_full_panel_min"] == pytest.approx(full_min)
            mins = []
            for half in _half_hazards(art, sides):
                vals = [
                    math.log(half[f"{b}|male"] / half[f"{b}|female"])
                    for b in band_set
                    if half.get(f"{b}|male", 0) > 0
                    and half.get(f"{b}|female", 0) > 0
                ]
                if len(vals) == len(band_set):
                    mins.append(min(vals))
            arr = np.asarray(mins, dtype=np.float64)
            assert block["n_halves_scored"] == arr.size
            assert block["half_split_sd"] == pytest.approx(arr.std(ddof=1))
            assert block["min_over_halves"] == pytest.approx(arr.min())
            assert block["holds_on_every_half"] is bool(arr.min() > 0)
            assert block["margin_sigma_units"] == round(
                full_min / arr.std(ddof=1), 3
            )
            assert block["clears_margin_k"] is bool(
                block["margin_sigma_units"] >= 3
            )


def test_the_dominance_cell_is_the_only_surface_seeing_the_differential():
    """The reason the anchor is load-bearing, checked from the numbers.

    Every internal cell that clears the cap sits in a band whose
    male/female log gap is smaller than the gap in every band the
    dominance invariant is scored over -- so a sex-flat candidate's
    error in the gated bands is smaller than the tolerance there.
    """
    art = _artifact()
    dominance = art["anchor_invariants"]["sex_dominance"]
    full_panel = art["external_anchor"]["windows"]["declared_1997_plus"][
        "by_band_sex"
    ]

    def gap(band: str) -> float:
        return abs(
            math.log(
                full_panel[f"{band}|male"]["psid_m"]
                / full_panel[f"{band}|female"]["psid_m"]
            )
        )

    stability = _universe(art, "declared_1997_plus")["cell_stability"]
    clearing = [k for k, c in stability.items() if c["clears_t_max_at_k3"]]
    assert clearing
    for key in clearing:
        band = key.split("|")[0]
        # a sex-flat candidate's error in this band is the band's own gap
        assert gap(band) <= stability[key]["tolerance_k3"], key
    for band in dominance["headline"]["band_set"]:
        assert gap(band) > max(gap(k.split("|")[0]) for k in clearing)


def test_age_gradient_companion_is_labelled_and_recomputes():
    art = _artifact()
    gradient = art["anchor_invariants"]["age_gradient_companion"]
    assert gradient["gated"] is False
    assert gradient["commissioned"] is False
    assert "gates nothing" in gradient["note"]
    band_set = gradient["measured_band_set"]
    for sex, block in gradient["by_sex"].items():
        for name, sides in (("side_a", ("a",)), ("both_sides", ("a", "b"))):
            halves = _half_hazards(art, sides)
            assert block["n_halves_scanned"][name] == len(halves)
            inversions = block["adjacent_gap_inversions"][name]
            for pair, count in inversions.items():
                lo, hi = pair.split("->")
                got = sum(
                    1
                    for h in halves
                    if h.get(f"{lo}|{sex}", 0) > 0
                    and h.get(f"{hi}|{sex}", 0) > 0
                    and math.log(h[f"{hi}|{sex}"] / h[f"{lo}|{sex}"]) <= 0
                )
                assert count == got, (sex, name, pair)
            mins = []
            for half in halves:
                gaps = []
                for lo, hi in zip(band_set[:-1], band_set[1:], strict=True):
                    if (
                        half.get(f"{lo}|{sex}", 0) > 0
                        and half.get(f"{hi}|{sex}", 0) > 0
                    ):
                        gaps.append(
                            math.log(half[f"{hi}|{sex}"] / half[f"{lo}|{sex}"])
                        )
                if len(gaps) == len(band_set) - 1:
                    mins.append(min(gaps))
            arr = np.asarray(mins, dtype=np.float64)
            conv = block[f"{name}_convention"]
            assert conv["n_halves"] == arr.size
            assert conv["half_split_sd"] == pytest.approx(arr.std(ddof=1))
            assert conv["min_over_halves"] == pytest.approx(arr.min())


# --------------------------------------------------------------------------
# The ln(1.5) scope claim, checked against the record it cites
# --------------------------------------------------------------------------
def test_t_max_scope_quotes_gates_yaml_accurately():
    art = _artifact()
    scope = art["t_max_scope"]
    assert scope["t_max"] == pytest.approx(T_MAX)
    assert scope["t_max_source"] == "ln(1.5)"
    gates_text = GATES.read_text()
    assert "mortality_drift" in gates_text
    for phrase in (
        "No admissible pooling of",
        "the 25-84 surface clears the ln(1.5) cap even fully pooled",
        "tolerance ~0.472 vs cap 0.4055",
    ):
        assert phrase in gates_text, phrase
    assert "gate_m6" in scope["which_surface_that_claim_is_about"]
    assert "drift" in scope["what_this_artifact_does_not_claim"].lower()


def test_gates_yaml_citations_still_point_at_what_they_claim():
    """A stale line citation is the defect this rebuild answers.

    The artifact records the exact text at every ``gates.yaml`` line it
    cites. If ``gates.yaml`` moves, this fails loudly rather than
    leaving the artifact quietly pointing at the wrong rule.
    """
    art = _artifact()
    block = art["gates_yaml_citations"]
    assert block["file"] == "gates.yaml"
    assert block["sha256"] == hashlib.sha256(GATES.read_bytes()).hexdigest()
    assert art["revision_pins"]["gates_yaml_sha256"] == block["sha256"]
    lines = GATES.read_text().splitlines()
    assert block["n_lines"] == len(lines)
    assert block["citations"]
    for entry in block["citations"]:
        assert lines[entry["line"] - 1].strip() == entry["text"], entry


def test_every_gates_yaml_line_the_artifact_cites_is_pinned():
    """No prose citation escapes the citation block."""
    art = _artifact()
    pinned = {e["line"] for e in art["gates_yaml_citations"]["citations"]}
    text = json.dumps(art)
    mentioned: set[int] = set()
    for match in re.finditer(r"gates\.yaml:(\d+)(?:-(\d+))?", text):
        mentioned.add(int(match.group(1)))
        if match.group(2):
            mentioned.add(int(match.group(2)))
    for match in re.finditer(r"[ ,]:(\d{4})\b", text):
        mentioned.add(int(match.group(1)))
    assert mentioned
    assert not mentioned - pinned, sorted(mentioned - pinned)


def test_the_cited_gate_m4_anchor_margins_bracket_the_quoted_range():
    """The 'thin against precedent' claim is checked, not asserted."""
    art = _artifact()
    citations = {
        e["line"]: e["text"] for e in art["gates_yaml_citations"]["citations"]
    }
    margins = [
        float(citations[line].split(":")[1])
        for line in (3395, 3438, 3472, 3514)
    ]
    assert min(margins) == 4.797
    assert max(margins) == 12.806
    note = art["anchor_invariants"]["sex_dominance"]["headline"][
        "thinness_note"
    ]
    assert "4.797-12.806" in note
    headline = art["anchor_invariants"]["sex_dominance"]["headline"]
    assert headline["margin_sigma_units_side_a"] < min(margins)


def test_t_max_scope_quotes_the_m6_artifact_accurately():
    art = _artifact()
    ref = art["t_max_scope"]["m6_reference"]
    assert ref["sha256"] == hashlib.sha256(M6_FLOORS.read_bytes()).hexdigest()
    m6 = json.loads(M6_FLOORS.read_text())
    ladder = m6["coarsening_ladder"]["ladders"]["death"]
    assert ladder["adopted_rung"] is None
    assert ladder["gated"] == []
    step = next(
        s for s in ladder["steps"] if s["rung"] == ref["fully_pooled_rung"]
    )
    cell = step["cells"][ref["fully_pooled_cell"]]
    assert cell["tolerance"] == ref["fully_pooled_tolerance"]
    assert cell["n_events_full"] == ref["fully_pooled_n_events_full"]
    assert cell["clears"] is False


def test_this_surface_has_the_event_base_it_claims():
    art = _artifact()
    scope = art["t_max_scope"]
    claim = scope["which_surface_this_artifact_is_about"]
    all_events = art["external_anchor"]["windows"]["all"][
        "total_death_events_unwt"
    ]
    declared_events = art["external_anchor"]["windows"]["declared_1997_plus"][
        "total_death_events_unwt"
    ]
    assert str(all_events) in claim
    assert str(declared_events) in claim
    assert (
        all_events > 10 * scope["m6_reference"]["fully_pooled_n_events_full"]
    )


def test_person_identity_check_shows_no_pad_rows():
    art = _artifact()
    check = art["data"]["person_identity_check"]
    assert check["no_pad_rows_present"] is True
    assert check["n_nonpositive_person_ids"] == 0
    assert check["min_person_id"] > 0
    rule = check["rule"]
    assert "PAD_IDENTITY_DISCLOSURE" in rule
    # The disclosure attributes the -1/-2 pad rows to the accepted
    # adapter increment by blob, NOT to this repository -- because this
    # repository's adapter emits no person_id at all. Both halves are
    # checked against the file each one is about.
    adapter = (ROOT / "scripts" / "registered_m6_inputs.py").read_text()
    assert "PAD_IDENTITY_DISCLOSURE" not in adapter
    assert (
        '"person_id"'
        not in adapter.split("def _pad_below_25")[0].split(
            "return frame.rename("
        )[-1]
    )
    assert "c9cc6f1e71fab96ef830d7e7b434ee216f1a96c8" in rule
    assert "12d782f84e18cda0293edba19389e7672ab80477" in rule
    assert "THIS repository" in rule


def test_open_questions_are_recorded_and_unanswered():
    art = _artifact()
    questions = art["open_questions_for_the_ceremony"]
    assert len(questions) >= 5
    topics = " ".join(q["question"] for q in questions)
    for topic in ("85+", "ascertainment", "censoring", "MARGIN_K"):
        assert topic in topics, topic


# --------------------------------------------------------------------------
# Reproduction from PSID (skipped off-machine; NO populace-fit)
# --------------------------------------------------------------------------
@needs_real_ind
def test_seed0_and_anchor_reproduce_without_populace_fit():
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert (
        "populace.fit" not in sys.modules
    ), "importing the v2 mortality builder pulled populace.fit"

    from populace_dynamics.data import deaths, panels

    demo = panels.demographic_panel()
    death_records = deaths.read_death_records()
    slices = builder.v1b.build_exposure_slices(demo, death_records)
    art = _artifact()

    # The committed v1 5-seed floor still comes off this code path.
    v1_check = builder.v1_reproduction_check(slices, _v1())
    assert v1_check["floor_values_reproduce_exactly"] is True
    assert v1_check["stability_blocks_identical"] is True

    # Seed 0 of the declared universe reproduces to float precision.
    got = builder.measure_seed(0, slices, start_year_min=1997)
    ref = next(
        s
        for s in _universe(art, "declared_1997_plus")["per_seed"]
        if s["seed"] == 0
    )
    assert got["n_persons_side_a"] == ref["n_persons_side_a"]
    assert got["n_persons_side_b"] == ref["n_persons_side_b"]
    for key, ref_cell in ref["cells"].items():
        got_cell = got["cells"][key]
        for field in ("m_a", "m_b", "kish_death_a", "kish_death_b"):
            assert got_cell[field] == pytest.approx(
                ref_cell[field], abs=1e-12
            ), (key, field)
        assert got_cell["n_death_a"] == ref_cell["n_death_a"], key
        assert got_cell["n_death_b"] == ref_cell["n_death_b"], key
        if ref_cell["log_ratio_abs"] is None:
            assert got_cell["log_ratio_abs"] is None, key
        else:
            assert got_cell["log_ratio_abs"] == pytest.approx(
                ref_cell["log_ratio_abs"], abs=1e-12
            ), key
    for side in ("a", "b"):
        for key, value in ref[f"hazards_side_{side}"].items():
            assert got[f"hazards_side_{side}"][key] == pytest.approx(
                value, abs=1e-12
            ), (side, key)

    # The declared-universe anchor reproduces.
    nchs_rates = builder.v1b.nchs_band_rates(json.loads(NCHS.read_text()))
    got_anchor = builder.v1b.external_anchor(
        slices, nchs_rates, start_year_min=1997
    )
    ref_anchor = art["external_anchor"]["windows"]["declared_1997_plus"]
    assert (
        got_anchor["total_death_events_unwt"]
        == ref_anchor["total_death_events_unwt"]
    )
    assert got_anchor["n_slices"] == ref_anchor["n_slices"]
    for key, ref_cell in ref_anchor["by_band_sex"].items():
        got_cell = got_anchor["by_band_sex"][key]
        assert got_cell["psid_m"] == pytest.approx(
            ref_cell["psid_m"], abs=1e-12
        ), key
        assert got_cell["ratio"] == pytest.approx(
            ref_cell["ratio"], abs=1e-12
        ), key

    assert "populace.fit" not in sys.modules


@needs_real_ind
def test_weight_universe_measurement_reproduces():
    builder = _import_builder()
    from populace_dynamics.data import deaths, panels

    demo = panels.demographic_panel()
    slices = builder.v1b.build_exposure_slices(
        demo, deaths.read_death_records()
    )
    series_by_wave = builder.weight_series_by_wave()
    art = _artifact()
    weights = art["estimand"]["weight_universe_measurement"]
    assert {int(k): v for k, v in weights["series_by_wave"].items()} == (
        series_by_wave
    )

    got = builder.weight_universe_report(slices, series_by_wave)
    for name, ref in weights["by_series"].items():
        for field in (
            "n_slices",
            "deaths_unwt",
            "start_waves_present",
        ):
            assert got["by_series"][name][field] == ref[field], (name, field)
        for field in (
            "share_of_weighted_exposure",
            "share_of_unweighted_deaths",
            "mean_slice_weight",
        ):
            assert got["by_series"][name][field] == pytest.approx(
                ref[field], rel=1e-12
            ), (name, field)
    for side in ("pre_1997", "from_1997"):
        for field, value in weights[side].items():
            assert got[side][field] == pytest.approx(value, rel=1e-12), (
                side,
                field,
            )

    equivalence = builder.universe_equivalence(slices)
    assert equivalence["max_abs_log_ratio"] == pytest.approx(
        art["estimand"]["universe_equivalence"]["max_abs_log_ratio"],
        abs=1e-12,
    )
