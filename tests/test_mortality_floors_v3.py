"""Tests for the mortality floors v3 artifact (runs/mortality_floors_v3.json).

The artifact is a REPORTED ANCHOR (reads no gate, changes no gate): the
pre-registration packet's three data-side blockers answered from bytes
-- the weight universe (R1), a pinned death-ascertainment convention
with its sensitivity band (R6) and the censoring convention with the
evidence against its assumption (R7) -- with the 100-seed
person-disjoint half-split floor rebuilt on both universes under every
convention. It is pinned like the other ``runs/`` floors.

Two tiers, mirroring ``tests/test_mortality_floors_v2.py``:

* Always-runnable tests touching only committed files. Every headline
  number recomputes from the artifact's own committed bytes: the pooled
  floors from the per-seed cells, the tolerances from the floors, the
  bootstrap probabilities from the committed sigmas and the stated rng,
  the per-cell weight-series shares as a partition that aggregates to
  the v2 figures, the withdrawal's three measurements from the frame
  statistics they cite, the death-record classification as a partition
  of the file, the ascertainment rates and the band's upper ends from
  ``r``, the convention movement from the hazards and the per-convention
  floors, the censoring quote from the v1 builder's own lines, the
  PSID/NCHS ratio summaries from the anchor windows and the attrition
  table from its counts. The survival convention's floors are asserted
  equal to the committed v2 bytes, so v3 is tied to v2 without touching
  PSID; the v1 and v2 artifacts are asserted byte-identical to their
  committed digests; the six committed inputs are sha256-pinned; and
  ``gates.yaml`` is checked to be innocent of this artifact.
* PSID-gated reproduction pins (skipped when the PSID individual file
  is absent) that rebuild the four convention frames and reproduce the
  classification, the rates, seed 0 under the pinned convention on both
  universes, seed 0 of v2 on the survival frame, the declared anchor,
  the resolution table, the per-cell shares, the attrition table and
  the within-rule sensitivity -- with ``populace.fit`` never imported.
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
ARTIFACT = ROOT / "runs" / "mortality_floors_v3.json"
V1_ARTIFACT = ROOT / "runs" / "mortality_floors_v1.json"
V2_ARTIFACT = ROOT / "runs" / "mortality_floors_v2.json"
M6_FLOORS = ROOT / "runs" / "m6_holdout_floors_v4.json"
NCHS = ROOT / "data" / "external" / "nchs_life_tables_2023.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"
BUILDER_V1 = SCRIPTS / "build_mortality_floors.py"
BUILDER_V2 = SCRIPTS / "build_mortality_floors_v2.py"

#: The committed bytes of the two predecessor artifacts at the commit
#: this artifact was built on (9b28ca6). Neither may move.
V1_COMMITTED = (
    49_624,
    "24075adc58feb8360bade74ad33cbdce1a3ed004536dc3bb59471a7b3d9d28b7",
)
V2_COMMITTED = (
    1_810_852,
    "2d8dc422470b379460b2b76ae8597b578ee8f40f2f6a9be948bcc633f5196d9b",
)

T_MAX = math.log(1.5)
UNIVERSES = ("declared_1997_plus", "all_v1_comparable")
CONVENTIONS = (
    "survival_v1_v2",
    "pinned_narrow_midpoint",
    "band_upper_informed",
    "band_upper_packet_literal",
)
PINNED = "pinned_narrow_midpoint"
SURVIVAL = "survival_v1_v2"

REAL_DATA = Path("~/PolicyEngine/psid-data").expanduser()
needs_real_ind = pytest.mark.skipif(
    not (REAL_DATA / "ind2023er").is_dir(),
    reason="PSID ind2023er not staged",
)


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _v1() -> dict:
    return json.loads(V1_ARTIFACT.read_text())


def _v2() -> dict:
    return json.loads(V2_ARTIFACT.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_mortality_floors_v3 as builder

    return builder


def _block(art: dict, convention: str, universe: str) -> dict:
    return art["internal_noise_floor"]["conventions"][convention]["universes"][
        universe
    ]


def _every_block(art: dict):
    for convention in CONVENTIONS:
        for universe in UNIVERSES:
            yield convention, universe, _block(art, convention, universe)


def _assert_close(got, ref, path: str = "$") -> None:
    """Recursive equality with float tolerance; exact for everything else."""
    if isinstance(ref, dict):
        assert isinstance(got, dict), path
        assert set(got) == set(ref), (path, set(got) ^ set(ref))
        for key in ref:
            _assert_close(got[key], ref[key], f"{path}.{key}")
    elif isinstance(ref, list):
        assert isinstance(got, list), path
        assert len(got) == len(ref), path
        for index, (a, b) in enumerate(zip(got, ref, strict=True)):
            _assert_close(a, b, f"{path}[{index}]")
    elif isinstance(ref, bool) or ref is None or isinstance(ref, str):
        assert got == ref, (path, got, ref)
    elif isinstance(ref, float):
        assert got == pytest.approx(ref, rel=1e-9, abs=1e-9), (
            path,
            got,
            ref,
        )
    else:
        assert got == ref, (path, got, ref)


# --------------------------------------------------------------------------
# Framing: reported anchor, nothing ratified, gates.yaml innocent
# --------------------------------------------------------------------------
def test_schema_and_reported_anchor():
    art = _artifact()
    assert art["schema_version"] == "mortality_floors.v3"
    assert art["run"] == "mortality_floors_v3"
    assert art["reported_anchor_not_gated"] is True
    assert "changes no gate" in art["purpose"]
    assert "gates.yaml is untouched" in art["purpose"]
    assert "differential mortality" in art["component"]
    note = art["proposed_thresholds_note"]
    assert "NOT RATIFIED" in note
    assert "referee round" in note
    assert "ratifies nothing" in note
    assert art["revision_pins"]["artifact_schema_version"] == (
        "mortality_floors.v3"
    )


def test_no_reform_scored_and_nothing_adopted():
    art = _artifact()
    assert "reform" not in art
    assert "gate_result" not in art
    assert "thresholds" not in art
    joined = " ".join(art["does_not_do"]).lower()
    assert "edit gates.yaml" in joined
    assert "score a candidate" in joined
    assert "rule on 85+" in joined
    assert "delete, edit or supersede" in joined
    for _, _, block in _every_block(art):
        for cell in block["cell_stability"].values():
            assert "gate_eligible" not in cell
            assert "v1_rule_gate_eligible" in cell


def test_gates_yaml_does_not_read_this_artifact():
    """The rebuild is evidence, not a wired-in derivation basis."""
    gates_text = GATES.read_text()
    assert "mortality_floors_v3" not in gates_text
    assert "gate_mortality" not in gates_text


def test_supersession_declares_v2_and_retains_both_predecessors():
    art = _artifact()
    sup = art["supersedes"]
    assert sup["artifact"] == "runs/mortality_floors_v2.json"
    assert sup["sha256"] == _sha(V2_ARTIFACT)
    assert sup["v1_artifact_sha256"] == _sha(V1_ARTIFACT)
    assert "NOT deleted" in sup["v2_retained_as"]
    assert "v1 likewise" in sup["v2_retained_as"]
    assert V1_ARTIFACT.is_file()
    assert V2_ARTIFACT.is_file()


def test_v1_and_v2_artifacts_are_byte_identical_to_their_committed_bytes():
    """Neither predecessor moved: size and sha256 against the record."""
    for path, (size, sha) in (
        (V1_ARTIFACT, V1_COMMITTED),
        (V2_ARTIFACT, V2_COMMITTED),
    ):
        assert path.stat().st_size == size, path
        assert _sha(path) == sha, path
    art = _artifact()
    assert art["revision_pins"]["v1_artifact_sha256"] == V1_COMMITTED[1]
    assert art["revision_pins"]["v2_artifact_sha256"] == V2_COMMITTED[1]
    assert art["v2_reproduction_check"]["v2_artifact_sha256"] == (
        V2_COMMITTED[1]
    )


def test_committed_inputs_are_pinned_by_sha256():
    art = _artifact()
    pins = art["revision_pins"]
    assert pins["nchs_reference_sha256"] == _sha(NCHS)
    assert pins["v1_artifact_sha256"] == _sha(V1_ARTIFACT)
    assert pins["v2_artifact_sha256"] == _sha(V2_ARTIFACT)
    assert pins["gates_yaml_sha256"] == _sha(GATES)
    assert pins["builder_v1_sha256"] == _sha(BUILDER_V1)
    assert pins["builder_v2_sha256"] == _sha(BUILDER_V2)
    assert art["t_max_scope"]["m6_reference"]["sha256"] == _sha(M6_FLOORS)
    assert re.fullmatch(r"[0-9a-f]{40}", pins["populace_dynamics_sha"])
    for key in (
        "psid_ind2023er_txt_sha256",
        "psid_ind2023er_sps_sha256",
        "psid_ind2023er_codebook_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", pins[key]), key
    release = art["data"]["psid_release"]
    assert release["data_sha256"] == pins["psid_ind2023er_txt_sha256"]
    assert release["sps_sha256"] == pins["psid_ind2023er_sps_sha256"]
    assert release["codebook_sha256"] == (
        pins["psid_ind2023er_codebook_sha256"]
    )


def test_what_changed_names_the_three_blockers():
    art = _artifact()
    joined = " ".join(art["what_changed_from_v2"])
    for tag in ("R1.1", "R1.2", "R1.4", "R6.1", "R6.2", "R6.3", "R7"):
        assert tag in joined, tag
    assert "R4" in joined


# --------------------------------------------------------------------------
# Seed count: 100, stated, and honoured under every convention
# --------------------------------------------------------------------------
def test_seed_count_is_100_and_stated_everywhere():
    art = _artifact()
    inf = art["internal_noise_floor"]
    assert inf["floor_seeds"] == list(range(100))
    assert inf["seed_count"] == 100
    assert "0-99" in inf["method"]
    assert "gate_m4" in inf["seed_count_precedent"]
    assert "identical partition under every convention" in (
        inf["split_frame_pin"]
    )
    assert inf["headline"] == {
        "convention": PINNED,
        "universe": "declared_1997_plus",
        "role": "the declared estimand; the derivation basis",
    }
    for convention, universe, block in _every_block(art):
        assert block["start_year_min"] == (
            1997 if universe == "declared_1997_plus" else None
        )
        assert set(block["noise_floor_seeds_0_99"]) == set(art["cell_order"])
        for floor in block["noise_floor_seeds_0_99"].values():
            assert floor["n_seeds"] == 100
            assert len(floor["values"]) == 100
        for cell in block["cell_stability"].values():
            assert cell["n_seeds"] == 100
        if convention == PINNED:
            assert [s["seed"] for s in block["per_seed"]] == list(range(100))
            assert block["per_seed_reference"] is None
        elif convention == SURVIVAL:
            assert block["per_seed"] is None
            assert block["per_seed_reference"].startswith(
                "runs/mortality_floors_v2.json"
            )
            assert universe in block["per_seed_reference"]
        else:
            assert block["per_seed"] is None
            assert block["per_seed_reference"].startswith("not committed")


def test_survival_convention_equals_the_committed_v2_floors():
    """The code-path tie: v3's lower band end IS v2, value for value."""
    art = _artifact()
    v2 = _v2()
    check = art["v2_reproduction_check"]
    assert check["v2_artifact"] == "runs/mortality_floors_v2.json"
    assert check["reproduces_exactly"] is True
    assert check["max_abs_diff_in_floor_values"] == 0.0
    for universe in UNIVERSES:
        assert check["universes"][universe] == {
            "cells_compared": 14,
            "max_abs_diff_in_floor_values": 0.0,
            "floor_values_reproduce_exactly": True,
            "stability_blocks_identical": True,
        }
        got = _block(art, SURVIVAL, universe)
        ref = v2["internal_noise_floor"]["universes"][universe]
        assert got["noise_floor_seeds_0_99"] == ref["noise_floor_seeds_0_99"]
        assert got["cell_stability"] == ref["cell_stability"]
        assert got["k_sensitivity"] == ref["k_sensitivity"]


def test_pinned_pooled_floor_recomputes_from_per_seed():
    art = _artifact()
    for universe in UNIVERSES:
        block = _block(art, PINNED, universe)
        per_seed = block["per_seed"]
        for key, floor in block["noise_floor_seeds_0_99"].items():
            ratios = [s["cells"][key]["log_ratio_abs"] for s in per_seed]
            assert all(v is not None for v in ratios), (universe, key)
            assert floor["values"] == pytest.approx(ratios)
            assert floor["mean"] == pytest.approx(np.mean(ratios))
            assert floor["sd"] == pytest.approx(np.std(ratios, ddof=1))
            assert floor["min"] == pytest.approx(min(ratios))
            assert floor["max"] == pytest.approx(max(ratios))
            if universe == "declared_1997_plus":
                pct = [s["cells"][key]["pct_diff_abs"] for s in per_seed]
                assert floor["pct_diff_abs"]["values"] == pytest.approx(pct)
                assert floor["pct_diff_abs"]["mean"] == pytest.approx(
                    np.mean(pct)
                )
            else:
                assert "pct_diff_abs" not in floor


def test_pinned_per_seed_cells_are_internally_consistent():
    art = _artifact()
    for universe in UNIVERSES:
        block = _block(art, PINNED, universe)
        full = universe == "declared_1997_plus"
        for seed in block["per_seed"]:
            if full:
                assert set(seed) >= {"hazards_side_a", "hazards_side_b"}
            else:
                assert "hazards_side_a" not in seed
            for key, cell in seed["cells"].items():
                if full:
                    assert "pct_diff_abs" in cell
                    assert "deaths_expected_a" not in cell
                else:
                    assert "pct_diff_abs" not in cell
                    # an integer-death frame: expected == counted
                    assert cell["deaths_expected_a"] == pytest.approx(
                        cell["n_death_a"]
                    ), (universe, key)
                    assert cell["deaths_expected_b"] == pytest.approx(
                        cell["n_death_b"]
                    ), (universe, key)
                if cell["log_ratio_abs"] is None:
                    assert cell["m_a"] == 0 or cell["m_b"] == 0, key
                    continue
                assert cell["log_ratio_abs"] == pytest.approx(
                    abs(math.log(cell["m_a"] / cell["m_b"]))
                ), (universe, key)
                if full:
                    assert cell["pct_diff_abs"] == pytest.approx(
                        abs(cell["m_a"] - cell["m_b"]) / cell["m_b"] * 100.0
                    ), (universe, key)
                    assert seed["hazards_side_a"][key] == cell["m_a"]
                    assert seed["hazards_side_b"][key] == cell["m_b"]


def test_realized_sigma_is_the_rms_of_the_floor_values():
    art = _artifact()
    for convention, universe, block in _every_block(art):
        for key, floor in block["noise_floor_seeds_0_99"].items():
            values = np.asarray(floor["values"], dtype=np.float64)
            assert floor["realized_sigma"] == pytest.approx(
                float(np.sqrt((values**2).mean()))
            ), (convention, universe, key)
            assert block["cell_stability"][key]["realized_sigma"] == (
                floor["realized_sigma"]
            )


def test_tolerances_follow_the_derivation_convention():
    """tolerance_k = round(mean + k*sd, 3) under every convention."""
    art = _artifact()
    assert art["internal_noise_floor"]["t_max"] == pytest.approx(T_MAX)
    for convention, universe, block in _every_block(art):
        floors = block["noise_floor_seeds_0_99"]
        for key, cell in block["cell_stability"].items():
            assert key in floors, (convention, universe, key)
            floor = floors[key]
            for k in (2, 3, 4):
                assert cell[f"tolerance_k{k}"] == round(
                    floor["mean"] + k * floor["sd"], 3
                ), (convention, universe, key, k)
            assert cell["clears_t_max_at_k3"] is bool(
                cell["tolerance_k3"] <= T_MAX
            ), (convention, universe, key)
            assert cell["tolerance_sigma_units_k3"] == round(
                cell["tolerance_k3"] / floor["realized_sigma"], 3
            ), (convention, universe, key)
            assert cell["defined_seeds"] == 100


def test_report_reason_matches_the_recorded_fields():
    art = _artifact()
    for convention, universe, block in _every_block(art):
        for key, cell in block["cell_stability"].items():
            if cell["defined_seeds"] < cell["n_seeds"]:
                expected = "undefined_on_some_seed"
            elif not cell["clears_t_max_at_k3"]:
                expected = "tolerance_above_t_max"
            elif cell["min_deaths_either_half"] < 20:
                expected = "below_20_deaths_weaker_half"
            else:
                expected = "clears_t_max_at_k3"
            assert cell["report_reason"] == expected, (
                convention,
                universe,
                key,
            )
            assert cell["v1_rule_gate_eligible"] is bool(
                cell["defined_seeds"] == cell["n_seeds"]
                and cell["min_deaths_either_half"] >= 20
            )


def test_k_sensitivity_matches_the_tolerances():
    art = _artifact()
    for convention, universe, block in _every_block(art):
        stability = block["cell_stability"]
        assert set(block["k_sensitivity"]) == {"2", "3", "4"}
        for k, entry in block["k_sensitivity"].items():
            expected = sorted(
                key
                for key, cell in stability.items()
                if cell.get(f"tolerance_k{k}") is not None
                and cell[f"tolerance_k{k}"] <= T_MAX
            )
            assert entry["cells"] == expected, (convention, universe, k)
            assert entry["n_clearing_t_max"] == len(expected)


def test_kish_effective_counts_recompute_for_the_pinned_convention():
    art = _artifact()
    for universe in UNIVERSES:
        block = _block(art, PINNED, universe)
        per_seed = block["per_seed"]
        for key, cell in block["cell_stability"].items():
            expected = min(
                min(
                    s["cells"][key]["kish_death_a"],
                    s["cells"][key]["kish_death_b"],
                )
                for s in per_seed
            )
            assert cell["min_effective_deaths_kish"] == pytest.approx(
                round(expected, 3)
            ), (universe, key)
            expected_deaths = min(
                min(s["cells"][key]["n_death_a"], s["cells"][key]["n_death_b"])
                for s in per_seed
            )
            assert cell["min_deaths_either_half"] == expected_deaths
    questions = " ".join(
        q["question"] for q in art["open_questions_for_the_ceremony"]
    )
    assert "weighted vs unweighted event-count eligibility" in questions


def test_universe_partition_agreement_recomputes():
    art = _artifact()
    agreement = art["internal_noise_floor"][
        "universe_partition_agreement_pinned"
    ]
    for universe, field in (
        ("declared_1997_plus", "declared_clearing_t_max_at_k3"),
        ("all_v1_comparable", "all_clearing_t_max_at_k3"),
    ):
        assert agreement[field] == sorted(
            key
            for key, c in _block(art, PINNED, universe)[
                "cell_stability"
            ].items()
            if c["clears_t_max_at_k3"]
        )
    assert agreement["agree"] is bool(
        agreement["declared_clearing_t_max_at_k3"]
        == agreement["all_clearing_t_max_at_k3"]
    )
    assert agreement["agree"] is True


def test_partition_movement_v2_to_v3_recomputes_from_the_two_floors():
    art = _artifact()
    v2_stab = _v2()["internal_noise_floor"]["universes"]["declared_1997_plus"][
        "cell_stability"
    ]
    v3_stab = _block(art, PINNED, "declared_1997_plus")["cell_stability"]
    movement = art["partition_movement"]["v2_survival_to_v3_pinned_declared"]
    v2_clearing = sorted(
        k for k, c in v2_stab.items() if c["clears_t_max_at_k3"]
    )
    v3_clearing = sorted(
        k for k, c in v3_stab.items() if c["clears_t_max_at_k3"]
    )
    assert movement["v2_clearing"] == v2_clearing
    assert movement["v3_clearing"] == v3_clearing
    assert movement["demoted"] == sorted(set(v2_clearing) - set(v3_clearing))
    assert movement["promoted"] == sorted(set(v3_clearing) - set(v2_clearing))
    assert movement["unchanged"] == sorted(set(v2_clearing) & set(v3_clearing))
    # The measured claim: the pinned convention moves no cell across the
    # cap on the declared universe.
    assert movement["demoted"] == []
    assert movement["promoted"] == []
    assert movement["unchanged"] == [
        "75-84|female",
        "75-84|male",
        "85+|female",
        "85+|male",
    ]
    for key in art["cell_order"]:
        pair = movement["tolerance_k3_v2_vs_v3"][key]
        assert pair["v2"] == v2_stab[key]["tolerance_k3"]
        assert pair["v3"] == v3_stab[key]["tolerance_k3"]
        assert pair["delta"] == round(pair["v3"] - pair["v2"], 3)


# --------------------------------------------------------------------------
# Seed-count stability: the bootstrap recomputes from committed bytes
# --------------------------------------------------------------------------
def test_seed_count_bootstrap_recomputes_from_committed_sigmas():
    """Every published probability re-draws from the stated rng (stream 3)."""
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert "populace.fit" not in sys.modules

    art = _artifact()
    stability = art["seed_count_stability"]
    assert stability["t_max"] == pytest.approx(T_MAX)
    assert stability["cell_order"] == art["cell_order"]
    floors = _block(art, PINNED, "declared_1997_plus")[
        "noise_floor_seeds_0_99"
    ]
    for index, key in enumerate(art["cell_order"]):
        entry = stability["per_cell"][key]
        assert entry["sigma_v3_100_seed"] == pytest.approx(
            floors[key]["realized_sigma"]
        ), key
        block = entry["at_100_seeds_sigma_v3"]
        assert block["n_draws"] == 100
        assert block["sigma"] == pytest.approx(entry["sigma_v3_100_seed"])
        got = builder.v2b._bootstrap_block(
            block["sigma"], block["n_draws"], block["n_bootstrap"], index, 3
        )
        assert got == block, key


def test_bootstrap_probabilities_separate_the_clearing_set():
    """The clearing cells are near-certain; the 65-74 cells are coin flips."""
    art = _artifact()
    per_cell = art["seed_count_stability"]["per_cell"]
    stability = _block(art, PINNED, "declared_1997_plus")["cell_stability"]
    for key, cell in stability.items():
        p = per_cell[key]["at_100_seeds_sigma_v3"][
            "p_tolerance_at_or_below_t_max"
        ]
        if cell["clears_t_max_at_k3"]:
            assert p > 0.9, (key, p)
        elif key.startswith("65-74"):
            assert 0.3 < p < 0.7, (key, p)
        else:
            assert p < 0.01, (key, p)


# --------------------------------------------------------------------------
# R1 -- the weight universe
# --------------------------------------------------------------------------
def test_resolution_table_is_committed_per_wave():
    art = _artifact()
    wu = art["weight_universe"]
    table = wu["resolution_table"]
    assert len(table) == 43
    waves = [row["wave"] for row in table]
    assert waves == sorted(set(waves))
    assert waves == list(range(1968, 1998)) + list(range(1999, 2024, 2))
    for row in table:
        assert re.fullmatch(r"ER\d+[A-Z]?", row["variable"]), row
        assert row["fallback_pattern"] in wu["fallback_patterns"]
        assert row["fallback_rank"] == wu["fallback_patterns"].index(
            row["fallback_pattern"]
        )
        start, end = row["sps_columns"]
        assert end >= start > 0
        assert re.fullmatch(r"F\d+\.\d+", row["sps_format"]), row
        assert row["series"] in wu["series"]
        if row["wave"] >= 1997:
            assert row["series"] == "CORE/IMM INDIVIDUAL CROSS-SECTION WT"
            assert row["sps_format"] in ("F5.0", "F6.0")
            assert row["sps_format_source"].startswith("implicit integer")
        else:
            assert row["sps_format"] in ("F4.1", "F7.3")
            assert row["sps_format_source"] == "FORMATS block"
    series_by_wave = {row["wave"]: row["series"] for row in table}
    assert {
        int(k): v for k, v in wu["measurement"]["series_by_wave"].items()
    } == series_by_wave
    assert wu["n_series_across_window"] == 4
    assert wu["measurement"]["n_series_across_window"] == 4
    for name, summary in wu["series"].items():
        rows = [row for row in table if row["series"] == name]
        assert summary["waves_resolved"] == [
            rows[0]["wave"],
            rows[-1]["wave"],
        ]
        assert summary["n_waves_resolved"] == len(rows)
        assert summary["variables"] == [
            rows[0]["variable"],
            rows[-1]["variable"],
        ]
        assert summary["sps_formats"] == sorted(
            {row["sps_format"] for row in rows}
        )


def test_series_documentation_names_target_population_and_scale():
    art = _artifact()
    series = art["weight_universe"]["series"]
    declared = series["CORE/IMM INDIVIDUAL CROSS-SECTION WT"]
    assert declared["codebook"]["longitudinal"] is False
    assert "Cross-sectional" in declared["codebook"]["target_population"]
    assert "population-scaled" in declared["codebook"]["scale"]
    assert "NOT population-scaled" not in declared["codebook"]["scale"]
    longitudinal = series["CORE INDIVIDUAL LONGITUDINAL WEIGHT"]
    assert longitudinal["codebook"]["longitudinal"] is True
    assert "LONGITUDINAL" in longitudinal["codebook"]["target_population"]
    pre_max = 0.0
    for name, summary in series.items():
        assert summary["codebook"]["target_population"]
        assert summary["codebook"]["codebook_entry"].startswith("ER")
        if name != "CORE/IMM INDIVIDUAL CROSS-SECTION WT":
            assert "NOT population-scaled" in summary["codebook"]["scale"]
            assert summary["codebook"]["longitudinal"] is True
            pre_max = max(
                pre_max, summary["measured_in_frame"]["max_slice_weight"]
            )
    assert pre_max < 200
    assert declared["measured_in_frame"]["max_slice_weight"] > 100 * pre_max
    assert declared["measured_in_frame"]["start_waves_present"] == [1997, 2021]


def test_weight_series_shares_are_a_partition():
    art = _artifact()
    weights = art["weight_universe"]["measurement"]
    by_series = weights["by_series"]
    assert sum(
        s["share_of_weighted_exposure"] for s in by_series.values()
    ) == pytest.approx(1.0)
    assert sum(
        s["share_of_unweighted_deaths"] for s in by_series.values()
    ) == pytest.approx(1.0)
    assert sum(s["n_slices"] for s in by_series.values()) == (
        art["data"]["n_slices"]
    )
    pre, post = weights["pre_1997"], weights["from_1997"]
    assert pre["share_of_weighted_exposure"] + post[
        "share_of_weighted_exposure"
    ] == pytest.approx(1.0)
    assert pre["share_of_unweighted_deaths"] + post[
        "share_of_unweighted_deaths"
    ] == pytest.approx(1.0)
    assert pre["n_slices"] + post["n_slices"] == art["data"]["n_slices"]
    assert pre["share_of_unweighted_deaths"] > 0.35
    assert pre["share_of_weighted_exposure"] < 0.002
    # The v2 figures, carried by value.
    v2_weights = _v2()["estimand"]["weight_universe_measurement"]
    assert pre == v2_weights["pre_1997"]
    assert post == v2_weights["from_1997"]


def test_per_cell_series_shares_partition_and_aggregate_to_the_v2_figures():
    art = _artifact()
    wu = art["weight_universe"]
    shares = wu["per_cell_shares"]
    assert list(shares) == art["cell_order"]
    series_names = list(wu["series"])
    pre_deaths = pre_exposure = total_deaths = total_exposure = 0.0
    n_slices = 0
    for key, cell in shares.items():
        assert list(cell["by_series"]) == series_names, key
        assert sum(
            s["share_of_weighted_exposure"] for s in cell["by_series"].values()
        ) == pytest.approx(1.0), key
        assert sum(
            s["share_of_unweighted_deaths"] for s in cell["by_series"].values()
        ) == pytest.approx(1.0), key
        assert sum(
            s["weighted_exposure_py"] for s in cell["by_series"].values()
        ) == pytest.approx(cell["weighted_exposure_py"]), key
        assert (
            sum(s["deaths_unwt"] for s in cell["by_series"].values())
            == cell["deaths_unwt"]
        ), key
        pre_series = [n for n in series_names if n != series_names[-1]]
        assert cell["pre_1997_share_of_weighted_exposure"] == pytest.approx(
            sum(
                cell["by_series"][n]["share_of_weighted_exposure"]
                for n in pre_series
            )
        ), key
        assert cell["pre_1997_share_of_unweighted_deaths"] == pytest.approx(
            sum(
                cell["by_series"][n]["share_of_unweighted_deaths"]
                for n in pre_series
            )
        ), key
        assert cell["pre_1997_share_of_weighted_exposure"] < 0.0014, key
        assert cell["pre_1997_share_of_unweighted_deaths"] > 0.2, key
        pre_deaths += (
            cell["pre_1997_share_of_unweighted_deaths"] * cell["deaths_unwt"]
        )
        pre_exposure += (
            cell["pre_1997_share_of_weighted_exposure"]
            * cell["weighted_exposure_py"]
        )
        total_deaths += cell["deaths_unwt"]
        total_exposure += cell["weighted_exposure_py"]
        n_slices += sum(s["n_slices"] for s in cell["by_series"].values())
    measurement = wu["measurement"]["pre_1997"]
    assert pre_deaths / total_deaths == pytest.approx(
        measurement["share_of_unweighted_deaths"]
    )
    assert pre_exposure / total_exposure == pytest.approx(
        measurement["share_of_weighted_exposure"]
    )
    assert round(pre_deaths) == measurement["deaths_unwt"]
    assert n_slices == art["data"]["n_slices"]
    survival_all = art["external_anchor"]["windows_survival_v1_v2_convention"][
        "all"
    ]
    assert total_exposure == pytest.approx(
        survival_all["total_exposure_py_weighted"]
    )
    assert total_deaths == survival_all["total_death_events_unwt"]


def test_sample_strata_partition_each_era():
    art = _artifact()
    strata = art["weight_universe"]["sample_strata"]
    names = [s["name"] for s in strata["strata"]]
    assert names == [
        "core_SRC",
        "core_SEO",
        "immigrant_1997_1999",
        "immigrant_2017_2019",
        "latino_1990_1995",
    ]
    for stratum in strata["strata"]:
        lo, hi = stratum["er30001_range"]
        assert 0 < lo < hi
    eras = strata["by_era"]
    assert list(eras) == ["pre_1997", "1997_2015", "2017_plus"]
    for era, block in eras.items():
        by_stratum = block["by_stratum"]
        assert "other" not in by_stratum
        assert "latino_1990_1995" not in by_stratum
        assert sum(
            s["share_of_weighted_exposure"] for s in by_stratum.values()
        ) == pytest.approx(1.0), era
        assert sum(
            s["share_of_unweighted_deaths"] for s in by_stratum.values()
        ) == pytest.approx(1.0), era
        assert sum(s["n_slices"] for s in by_stratum.values()) == (
            block["n_slices"]
        ), era
    assert "immigrant_2017_2019" not in eras["pre_1997"]["by_stratum"]
    assert "immigrant_2017_2019" not in eras["1997_2015"]["by_stratum"]
    assert "immigrant_1997_1999" not in eras["pre_1997"]["by_stratum"]
    refresher = eras["2017_plus"]["by_stratum"]["immigrant_2017_2019"]
    assert 0.05 < refresher["share_of_weighted_exposure"] < 0.12
    assert refresher["share_of_unweighted_deaths"] < 0.02
    assert sum(b["n_slices"] for b in eras.values()) == art["data"]["n_slices"]


def test_declaration_quotes_its_own_measurements():
    art = _artifact()
    wu = art["weight_universe"]
    declaration = wu["declaration"]
    assert declaration["declared_universe_start_wave"] == 1997
    assert "CROSS-SECTION WT" in declaration["declared_weight_universe"]
    assert len(declaration["why"]) == 4
    post_share = wu["measurement"]["from_1997"]["share_of_weighted_exposure"]
    equivalence = wu["universe_equivalence"]["max_abs_log_ratio"]
    assert f"{100 * post_share:.4f}%" in declaration["why"][2]
    assert f"{equivalence:.6f} log units" in declaration["why"][2]
    assert "4001-4851" in declaration["within_universe_composition_change"]
    estimand = art["estimand"]
    assert estimand["declared_universe_start_wave"] == 1997
    assert estimand["declared_weight_universe"] == (
        declaration["declared_weight_universe"]
    )
    assert estimand["death_ascertainment_convention"] == PINNED
    assert estimand["censoring_convention"] == "governance.censoring.rule"
    governance = art["governance"]["weight_universe"]
    assert governance["declared"] == "weight_universe.declaration"
    assert "binds both sides of every score" in governance["binds"]
    assert "report-only" in governance["binds"]


def test_all_window_is_numerically_the_declared_window():
    art = _artifact()
    equivalence = art["weight_universe"]["universe_equivalence"]
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
    assert equivalence == _v2()["estimand"]["universe_equivalence"]


def test_the_v1_caveat_is_withdrawn_with_three_measurements():
    art = _artifact()
    v1 = _v1()
    v2 = _v2()
    wu = art["weight_universe"]
    withdrawal = wu["withdrawal_of_v1_caveat"]
    v1_caveat = v1["exposure_construction"]["biennial_caveats"][1]
    assert withdrawal["withdrawn_text"] == v1_caveat
    assert "bias PSID UPWARD" in v1_caveat
    assert withdrawal["withdrawn_from"].endswith("biennial_caveats[1]")
    assert withdrawal["v2_withdrawal_carried"] == (
        v2["exposure_construction"]["withdrawn_v1_caveat"]["why_withdrawn"]
    )
    assert art["exposure_construction"]["withdrawn_v1_caveat"]["text"] == (
        v1_caveat
    )
    for caveat in art["exposure_construction"]["biennial_caveats"]:
        assert "bias PSID UPWARD" not in caveat
    # 1. premise
    premise = withdrawal["premise_measured"]
    higher = lower = 0
    for key, cell in premise["per_cell"].items():
        expected = math.log(
            cell["m_pre_1997_within_window"]
            / cell["m_1997_plus_within_window"]
        )
        assert cell["ln_pre_over_post"] == pytest.approx(expected), key
        assert cell["older_decades_run_higher"] is bool(expected > 0)
        higher += expected > 0
        lower += expected < 0
    assert premise["n_cells_older_decades_higher"] == higher
    assert premise["n_cells_older_decades_lower"] == lower
    assert higher + lower == 14
    assert lower >= 7
    for key in ("85+|male", "85+|female"):
        assert premise["per_cell"][key]["ln_pre_over_post"] < -0.3, key
    assert f"holds in only {higher} of 14 cells and fails in {lower}" in (
        premise["reading"]
    )
    # 2. mechanism
    mechanism = withdrawal["mechanism_measured"]
    measurement = wu["measurement"]
    assert mechanism["pre_1997_share_of_weighted_exposure"] == (
        measurement["pre_1997"]["share_of_weighted_exposure"]
    )
    assert mechanism["pre_1997_share_of_unweighted_deaths"] == (
        measurement["pre_1997"]["share_of_unweighted_deaths"]
    )
    assert mechanism["mean_slice_weight_pre_1997"] == (
        measurement["pre_1997"]["mean_slice_weight"]
    )
    assert mechanism["mean_slice_weight_1997_plus"] == (
        measurement["from_1997"]["mean_slice_weight"]
    )
    assert mechanism["storage_formats"] == {
        name: summary["sps_formats"] for name, summary in wu["series"].items()
    }
    pre_share = mechanism["pre_1997_share_of_weighted_exposure"]
    assert f"carry {100 * pre_share:.4f}% of the weighted" in (
        mechanism["reading"]
    )
    # 3. consequence
    consequence = withdrawal["consequence_measured"]
    max_equiv = wu["universe_equivalence"]["max_abs_log_ratio"]
    assert consequence["max_abs_ln_m_all_over_m_1997_plus"] == max_equiv
    anchor = art["external_anchor"]["windows_survival_v1_v2_convention"][
        "all"
    ]["by_band_sex"]
    undercount = consequence["undercount_abs_ln_ratio_per_cell_all_window"]
    assert set(undercount) == set(art["cell_order"])
    for key, value in undercount.items():
        assert value == pytest.approx(abs(math.log(anchor[key]["ratio"]))), key
    min_undercount = min(undercount.values())
    assert consequence["min_undercount_abs_ln_ratio"] == pytest.approx(
        min_undercount
    )
    assert consequence["claimed_offset_as_share_of_min_undercount"] == (
        pytest.approx(max_equiv / min_undercount)
    )
    assert consequence["claimed_offset_as_share_of_min_undercount"] < 0.01
    reading = consequence["reading"]
    assert f"most {max_equiv:.6f} log units" in reading
    assert f"at least {min_undercount:.3f} log units" in reading
    assert f"at most {100 * max_equiv / min_undercount:.2f}% of the" in (
        reading
    )
    assert withdrawal["verdict"].startswith("WITHDRAWN")
    assert f"fails in {lower} of 14 cells" in withdrawal["verdict"]
    assert "Nothing in v3 restates it" in withdrawal["verdict"]


# --------------------------------------------------------------------------
# R6 -- death ascertainment
# --------------------------------------------------------------------------
def test_death_record_classification_partitions_the_file():
    art = _artifact()
    classification = art["death_ascertainment"]["classification"]
    counts = classification["status_counts"]
    assert sum(counts.values()) == 85_536
    assert "85,536" in art["data"]["death_record_counts"]["note"]
    narrow, wide = classification["narrow"], classification["wide"]
    assert narrow["n"] + wide["n"] == counts["range"]
    spans = {
        int(k): v for k, v in classification["range_span_distribution"].items()
    }
    assert sum(spans.values()) == counts["range"]
    assert sum(v for k, v in spans.items() if k <= 2) == narrow["n"]
    assert sum(v for k, v in spans.items() if k >= 3) == wide["n"]
    assert min(spans) == 1
    assert max(spans) == 26
    by_span = classification["narrow_by_span"]
    assert set(by_span) == {"1", "2"}
    for field in (
        "n",
        "in_frame",
        "observed_at_lo",
        "in_frame_last_wave_before_lo",
        "lo_is_grid_wave",
        "hi_is_next_grid_wave_of_lo",
        "range_overlaps_last_observed_interval",
    ):
        assert narrow[field] == sum(b[field] for b in by_span.values()), field
    for block in (narrow, wide, *by_span.values()):
        assert sum(block["by_sex"].values()) == block["n"]
        assert block["in_frame"] <= block["n"]
        assert block["observed_at_lo"] <= block["in_frame"]
        assert block["in_frame_last_wave_before_lo"] <= block["in_frame"]
        assert (
            block["observed_at_lo"] + block["in_frame_last_wave_before_lo"]
            <= block["in_frame"]
        )
        assert block["hi_is_next_grid_wave_of_lo"] <= block["lo_is_grid_wave"]
    assert wide["hi_is_next_grid_wave_of_lo"] == 0
    na = classification["na_year"]
    assert na["n"] == counts["na_dk"]
    assert na["in_frame_with_last_interval"] <= na["in_frame"] <= na["n"]
    assert (
        sum(classification["narrow_lo_distribution"].values()) == narrow["n"]
    )
    record = art["data"]["death_record_counts"]
    for key in counts:
        assert record[key] == counts[key]
    assert record["range_narrow_span_le_2"] == narrow["n"]
    assert record["range_wide_span_ge_3"] == wide["n"]
    reading = classification["reading"]
    assert f"{narrow['lo_is_grid_wave']} of {narrow['n']} narrow codes" in (
        reading
    )
    assert f"next grid wave in {narrow['hi_is_next_grid_wave_of_lo']}" in (
        reading
    )
    assert f"Only {narrow['observed_at_lo']} narrow-coded" in reading
    assert f"{narrow['in_frame_last_wave_before_lo']} in-frame decedents" in (
        reading
    )
    assert f"{narrow['n'] - narrow['in_frame']} are not in the frame" in (
        reading
    )


def test_ascertainment_rates_recompute():
    art = _artifact()
    da = art["death_ascertainment"]
    rates = da["ascertainment_rates"]
    packet = rates["packet_rate"]
    assert packet["numerator"] == (
        da["pinned_rule_effect"]["death_events_survival_convention"]
    )
    assert (
        packet["denominator"] == da["classification"]["status_counts"]["exact"]
    )
    assert packet["value"] == pytest.approx(
        packet["numerator"] / packet["denominator"]
    )
    assert "not a conditional probability" in packet["what_it_divides"]
    in_frame = rates["in_frame_rate"]
    assert in_frame["value"] == pytest.approx(
        in_frame["numerator"] / in_frame["denominator"]
    )
    assert (
        in_frame["numerator"]
        + in_frame["death_after_last_interval"]
        + in_frame["death_before_last_observed_wave"]
        == in_frame["denominator"]
    )
    assert in_frame["denominator"] < packet["denominator"]
    assert in_frame["value"] > packet["value"]
    recent = rates["in_frame_rate_last_wave_1997_plus"]
    assert recent["value"] == pytest.approx(
        recent["numerator"] / recent["denominator"]
    )
    assert recent["denominator"] < in_frame["denominator"]
    by_band = rates["by_age_band_at_last_wave"]
    assert list(by_band) == art["age_bands"]
    assert sum(b["n"] for b in by_band.values()) <= in_frame["denominator"]
    for band, block in by_band.items():
        assert block["rate"] == pytest.approx(
            block["ascertained"] / block["n"]
        ), band
    assert by_band["85+"]["rate"] > by_band["25-34"]["rate"]
    split = rates["within_two_year_interval_split"]
    assert (
        split["n_in_first_year"] + split["n_in_second_year"]
        == split["n_ascertained_in_two_year_intervals"]
    )
    assert split["p_second_year"] == pytest.approx(
        split["n_in_second_year"]
        / split["n_ascertained_in_two_year_intervals"]
    )
    assert split["p_second_year"] > 0.5
    assert rates["rule_rate_used_by_the_band"] == in_frame["value"]


def test_pinned_rule_effect_recomputes():
    art = _artifact()
    da = art["death_ascertainment"]
    convention = da["convention"]
    assert convention["name"] == PINNED
    assert convention["narrow_max_span"] == 2
    assert "floor((lo + hi) / 2)" in convention["rule"]
    assert "sensitivity band" in convention["rule"]
    p2 = da["ascertainment_rates"]["within_two_year_interval_split"][
        "p_second_year"
    ]
    assert "166 of the 200 narrow codes" in convention["why_the_midpoint"]
    assert f"{100 * p2:.1f}% of the time" in convention["why_the_midpoint"]
    assert da["classification"]["narrow"]["hi_is_next_grid_wave_of_lo"] == 166
    assert convention["implementation"].endswith("assign_narrow_death_years")
    effect = da["pinned_rule_effect"]
    assert (
        effect["death_events_pinned_convention"]
        - effect["death_events_survival_convention"]
        == effect["death_events_added"]
    )
    assert (
        sum(effect["added_by_cell"].values()) == effect["death_events_added"]
    )
    assert set(effect["added_by_cell"]) == set(art["cell_order"])
    assert sum(effect["added_by_start_wave_era"].values()) == (
        effect["death_events_added"]
    )
    assert effect["n_slices_survival"] == effect["n_slices_pinned"]
    assert effect["n_slices_pinned"] == art["data"]["n_slices"]
    band = da["sensitivity_band"]
    events = band["expected_death_events_by_convention"]
    assert events[SURVIVAL] == effect["death_events_survival_convention"]
    assert events[PINNED] == effect["death_events_pinned_convention"]
    declared = band["expected_death_events_by_convention_declared_universe"]
    assert declared[PINNED] - declared[SURVIVAL] == (
        effect["added_by_start_wave_era"]["1997_plus"]
    )
    assert (
        declared[SURVIVAL]
        == _v2()["external_anchor"]["windows"]["declared_1997_plus"][
            "total_death_events_unwt"
        ]
    )


def test_sensitivity_band_upper_ends_recompute_from_r():
    art = _artifact()
    da = art["death_ascertainment"]
    band = da["sensitivity_band"]
    rates = da["ascertainment_rates"]
    r = band["r_used"]
    assert r == rates["rule_rate_used_by_the_band"]
    assert band["p_second_year_used"] == (
        rates["within_two_year_interval_split"]["p_second_year"]
    )
    assert band["lower_end"]["convention"] == SURVIVAL
    events = band["expected_death_events_by_convention"]
    declared = band["expected_death_events_by_convention_declared_universe"]
    informed = band["upper_end_informed"]
    literal = band["upper_end_packet_literal"]
    assert informed["convention"] == "band_upper_informed"
    assert literal["convention"] == "band_upper_packet_literal"
    for end in (informed, literal):
        targets = end["targets"]
        assert sum(targets["by_status"].values()) == targets["n_persons"]
        assert sum(targets["by_start_wave_era"].values()) == (
            targets["n_persons"]
        )
        assert targets["n_with_banded_start_age"] <= targets["n_persons"]
        assert targets["expected_added_death_events_all_ages"] == (
            pytest.approx(r * targets["n_persons"])
        )
    # The frame holds banded slices only, so the added expected events
    # are r per target with a banded start age.
    assert events["band_upper_informed"] - events[PINNED] == pytest.approx(
        r * informed["targets"]["n_with_banded_start_age"]
    )
    assert events["band_upper_packet_literal"] - events[PINNED] == (
        pytest.approx(r * literal["targets"]["n_with_banded_start_age"])
    )
    persons = informed["targets"]["persons"]
    assert len(persons) == informed["targets"]["n_persons"]
    assert literal["targets"]["persons"] is None
    banded_recent = [
        p
        for p in persons
        if p["start_wave"] >= 1997 and p["age_at_start"] >= 25
    ]
    assert declared["band_upper_informed"] - declared[PINNED] == (
        pytest.approx(r * len(banded_recent))
    )
    # On the declared universe the literal extreme adds nothing beyond
    # the informed end: every extra person was last seen before 1997.
    assert declared["band_upper_packet_literal"] == (
        declared["band_upper_informed"]
    )
    assert literal["targets"]["by_start_wave_era"]["1997_plus"] == (
        informed["targets"]["by_start_wave_era"]["1997_plus"]
    )
    for person in persons:
        assert person["death_status"] in ("range", "na_dk")
        assert person["next_wave"] > person["start_wave"]
        assert person["feasible_years"]
        for year in person["feasible_years"]:
            assert person["start_wave"] <= year < person["next_wave"]
    wide_in_frame_overlapping = da["classification"]["wide"][
        "range_overlaps_last_observed_interval"
    ]
    assert informed["targets"]["by_status"]["range"] <= (
        wide_in_frame_overlapping
    )
    assert informed["targets"]["by_status"]["na_dk"] == (
        da["classification"]["na_year"]["in_frame_with_last_interval"]
    )


def test_measured_movement_recomputes_cell_by_cell():
    art = _artifact()
    movement = art["death_ascertainment"]["measured_movement"]
    band = art["death_ascertainment"]["sensitivity_band"]
    for universe in UNIVERSES:
        block = movement[universe]
        events = block["death_events_by_convention"]
        expected_events = (
            band["expected_death_events_by_convention_declared_universe"]
            if universe == "declared_1997_plus"
            else band["expected_death_events_by_convention"]
        )
        for name in CONVENTIONS:
            assert events[name] == pytest.approx(expected_events[name]), (
                universe,
                name,
            )
        for name in CONVENTIONS[1:]:
            assert block["numerator_change_vs_survival_pct"][name] == (
                pytest.approx(
                    100.0
                    * (events[name] - events[SURVIVAL])
                    / events[SURVIVAL]
                )
            )
        max_abs = {name: 0.0 for name in CONVENTIONS[1:]}
        max_dt = {name: 0.0 for name in CONVENTIONS[1:]}
        for key, cell in block["per_cell"].items():
            base = cell["hazard"][SURVIVAL]
            base_t = cell["tolerance_k3"][SURVIVAL]
            for name in CONVENTIONS:
                stability = _block(art, name, universe)["cell_stability"][key]
                assert cell["tolerance_k3"][name] == stability["tolerance_k3"]
                assert cell["clears_t_max_at_k3"][name] is (
                    stability["clears_t_max_at_k3"]
                )
                if name == SURVIVAL:
                    continue
                m = cell["hazard"][name]
                expected = math.log(m / base)
                assert cell["ln_over_survival"][name] == pytest.approx(
                    expected, abs=1e-12
                ), (universe, key, name)
                max_abs[name] = max(max_abs[name], abs(expected))
                t = cell["tolerance_k3"][name]
                assert cell["delta_tolerance_k3"][name] == round(t - base_t, 3)
                max_dt[name] = max(max_dt[name], abs(t - base_t))
        for name in CONVENTIONS[1:]:
            assert block["max_abs_ln_over_survival"][name] == pytest.approx(
                max_abs[name], abs=1e-12
            )
            assert block["max_abs_delta_tolerance_k3"][name] == (
                pytest.approx(max_dt[name], abs=1e-12)
            )
        for name in CONVENTIONS:
            assert block["clearing_sets_k3"][name] == sorted(
                key
                for key, cell in block["per_cell"].items()
                if cell["clears_t_max_at_k3"][name]
            )


def test_packet_estimate_is_replaced_by_the_measurement():
    art = _artifact()
    movement = art["death_ascertainment"]["measured_movement"]
    replaced = movement["packet_estimate_replaced"]
    assert "+3.9%" in replaced["packet"]["estimate"]
    assert "0.483" in replaced["packet"]["assumption"]
    declared = replaced["measured_declared_universe"]
    assert declared["numerator_change_pct"] == (
        movement["declared_1997_plus"]["numerator_change_vs_survival_pct"]
    )
    assert declared["max_abs_ln_over_survival"] == (
        movement["declared_1997_plus"]["max_abs_ln_over_survival"]
    )
    assert replaced["measured_all_window"]["numerator_change_pct"] == (
        movement["all_v1_comparable"]["numerator_change_vs_survival_pct"]
    )
    for name in CONVENTIONS[1:]:
        assert declared["numerator_change_pct"][name] < 0.3
        assert declared["max_abs_ln_over_survival"][name] < 0.03
        assert declared["max_abs_delta_tolerance_k3"][name] < 0.01
    # The clearing set is identical under all four conventions on both
    # universes: the estimate's "15% of the 85+|female tolerance" is 0.
    for universe in UNIVERSES:
        sets = movement[universe]["clearing_sets_k3"]
        assert len({tuple(s) for s in sets.values()}) == 1
        assert sets[PINNED] == [
            "75-84|female",
            "75-84|male",
            "85+|female",
            "85+|male",
        ]
        assert movement[universe]["per_cell"]["85+|female"][
            "delta_tolerance_k3"
        ] == {name: 0.0 for name in CONVENTIONS[1:]}
    why = replaced["why_the_estimate_was_high"]
    assert "119 of the 305" in why
    assert "0.483" in why


def test_within_rule_sensitivity_brackets_the_pinned_rule():
    art = _artifact()
    da = art["death_ascertainment"]
    sensitivity = da["within_rule_sensitivity"]
    effect = da["pinned_rule_effect"]
    at_lo, at_hi = sensitivity["assign_at_lo"], sensitivity["assign_at_hi"]
    assert at_lo["death_events"] == effect["death_events_pinned_convention"]
    assert at_hi["death_events"] == effect["death_events_survival_convention"]
    for universe in UNIVERSES:
        diffs = at_lo[universe]["ln_m_variant_over_m_pinned_per_cell"]
        assert set(diffs) == set(art["cell_order"])
        assert at_lo[universe]["max_abs"] == pytest.approx(
            max(abs(v) for v in diffs.values())
        )
        assert at_lo[universe]["max_abs"] < 5e-4
        diffs = at_hi[universe]["ln_m_variant_over_m_pinned_per_cell"]
        assert at_hi[universe]["max_abs"] == pytest.approx(
            max(abs(v) for v in diffs.values())
        )
        # assigning at hi removes every added death: the mirror image
        assert at_hi[universe]["max_abs"] == pytest.approx(
            da["measured_movement"][universe]["max_abs_ln_over_survival"][
                PINNED
            ],
            abs=1e-9,
        )


def test_governance_pins_the_ascertainment_convention_on_both_sides():
    art = _artifact()
    governance = art["governance"]["death_ascertainment"]
    assert governance["convention"] == PINNED
    assert governance["convention"] == (
        art["death_ascertainment"]["convention"]["name"]
    )
    assert governance["declared"] == "death_ascertainment.convention"
    assert governance["sensitivity_band"] == (
        "death_ascertainment.sensitivity_band"
    )
    assert "binds both sides of every score" in governance["binds_both_sides"]
    assert "never a second scoring rule" in governance["binds_both_sides"]
    assert art["external_anchor"]["convention"] == PINNED
    assert art["anchor_invariants"]["convention"] == PINNED
    assert "PINNED in governance.death_ascertainment" in (
        art["exposure_construction"]["biennial_caveats"][1]
    )
    assert any(
        "pinned in governance.death_ascertainment" in d
        for d in art["external_anchor"]["concept_deltas_named"]
    )


def test_post_death_observations_are_disclosed_and_small():
    art = _artifact()
    note = art["data"]["post_death_observations"]
    assert note["n_exact_decedents_total"] == (
        art["death_ascertainment"]["classification"]["status_counts"]["exact"]
    )
    assert note["their_deaths_counted_in_frame"] <= (
        note["n_exact_decedents_with_post_death_slices"]
    )
    assert note["n_post_death_slices"] >= (
        note["n_exact_decedents_with_post_death_slices"]
    )
    # Every such decedent carries a death year before their last
    # observed wave, so they are a subset of that in-frame count.
    assert note["n_exact_decedents_with_post_death_slices"] <= (
        art["death_ascertainment"]["ascertainment_rates"]["in_frame_rate"][
            "death_before_last_observed_wave"
        ]
    )
    for universe in UNIVERSES:
        assert note["max_abs_ln_movement_if_dropped"][universe] < 5e-4
    assert note["convention"].startswith("INHERITED")
    questions = " ".join(
        q["question"] for q in art["open_questions_for_the_ceremony"]
    )
    assert "post-death observed waves" in questions


# --------------------------------------------------------------------------
# R7 -- censoring
# --------------------------------------------------------------------------
def test_censoring_rule_is_quoted_from_the_v1_builder_byte_for_byte():
    art = _artifact()
    rule = art["governance"]["censoring"]["rule"]
    assert rule["source_sha256"] == _sha(BUILDER_V1)
    assert rule["source_sha256"] == art["revision_pins"]["builder_v1_sha256"]
    lines = BUILDER_V1.read_text().splitlines()
    assert rule["packet_cites_lines"] == "56-61"
    assert rule["cited_lines_text"] == [lines[i - 1] for i in range(56, 62)]
    assert rule["item_lines"] == "57-62"
    assert rule["rule_quoted"] == " ".join(
        lines[i - 1].strip() for i in range(57, 63)
    )
    cited_stripped = " ".join(
        lines[i - 1].strip() for i in range(56, 62)
    ).strip()
    assert rule["rule_quoted"].startswith(cited_stripped)
    assert rule["rule_quoted"].startswith(
        "1. **Deaths only in the immediately-following interval.**"
    )
    assert rule["rule_quoted"].endswith("not corrected here.")
    assert "build_exposure_slices" in rule["code_location"]
    assert "Biennial-panel caveats" in rule["source"]


def test_censoring_assumption_and_binding_are_stated():
    art = _artifact()
    censoring = art["governance"]["censoring"]
    assert set(censoring) == {
        "rule",
        "assumption",
        "evidence_against",
        "binds",
    }
    assert censoring["assumption"].startswith("NON-INFORMATIVE NONRESPONSE")
    assert "same death hazard" in censoring["assumption"]
    assert "binds both sides of every score" in censoring["binds"]
    assert "no PASS may describe the censoring as innocuous" in (
        censoring["binds"]
    )
    assert set(censoring["evidence_against"]) == {
        "psid_over_nchs_ratios",
        "attrition_versus_death_by_age_and_sex",
    }
    assert "DECLARED in governance.censoring" in (
        art["exposure_construction"]["biennial_caveats"][0]
    )
    assert any(
        "declared in governance.censoring" in d
        for d in art["external_anchor"]["concept_deltas_named"]
    )


def test_psid_over_nchs_ratio_summaries_recompute_from_the_anchor_windows():
    art = _artifact()
    evidence = art["governance"]["censoring"]["evidence_against"][
        "psid_over_nchs_ratios"
    ]
    anchor = art["external_anchor"]
    sources = {
        "all_pinned": anchor["windows"]["all"],
        "declared_1997_plus_pinned": anchor["windows"]["declared_1997_plus"],
        "all_survival_v1_v2": anchor["windows_survival_v1_v2_convention"][
            "all"
        ],
        "declared_1997_plus_survival_v1_v2": anchor[
            "windows_survival_v1_v2_convention"
        ]["declared_1997_plus"],
    }
    assert set(evidence["by_window"]) == set(sources)
    for name, window in sources.items():
        ratios = [
            c["ratio"]
            for c in window["by_band_sex"].values()
            if c["ratio"] is not None
        ]
        summary = evidence["by_window"][name]
        assert summary["n_estimable_cells"] == len(ratios) == 14
        assert summary["min_ratio"] == pytest.approx(min(ratios)), name
        assert summary["max_ratio"] == pytest.approx(max(ratios)), name
        assert summary["median_ratio"] == pytest.approx(
            float(np.median(ratios))
        ), name
        assert summary == window["ratio_summary"]
        assert summary["max_ratio"] < 1.0
    v2_all = _v2()["external_anchor"]["windows"]["all"]["ratio_summary"]
    assert sources["all_survival_v1_v2"]["ratio_summary"] == v2_all
    quoted = (
        f"{v2_all['min_ratio']:.3f}-{v2_all['max_ratio']:.3f}, "
        f"median {v2_all['median_ratio']:.3f}"
    )
    assert quoted in evidence["statistic"]
    assert "three quarters" in evidence["reading"]


def test_attrition_evidence_recomputes_from_its_counts():
    art = _artifact()
    evidence = art["governance"]["censoring"]["evidence_against"][
        "attrition_versus_death_by_age_and_sex"
    ]
    table = evidence["table"]
    windows = table["windows"]
    assert set(windows) == {"all", "declared_1997_plus", "pre_1997"}
    counts = ("n_person_intervals", "n_deaths", "n_attrit", "n_continue")
    for field, total in (
        ("n_continue", table["totals"]["continues"]),
        ("n_deaths", table["totals"]["death"]),
        ("n_attrit", table["totals"]["attrit"]),
        ("n_person_intervals", table["n_person_intervals_banded"]),
    ):
        assert sum(c[field] for c in windows["all"].values()) == total, field
    overlap_all = 0
    for name, window in windows.items():
        assert list(window) == art["cell_order"], name
        for key, cell in window.items():
            n = cell["n_person_intervals"]
            # continues / death are not exclusive: a person recorded
            # dead in the interval AND observed at the next wave is the
            # post-death record inconsistency (data.post_death_observations).
            # attrit = neither, so the three sum to n plus that overlap.
            overlap = (
                cell["n_continue"] + cell["n_deaths"] + cell["n_attrit"] - n
            )
            assert 0 <= overlap <= 3, (name, key, overlap)
            if name == "all":
                overlap_all += overlap
            assert cell["death_hazard_per_interval_unwt"] == pytest.approx(
                cell["n_deaths"] / n
            ), (name, key)
            assert cell["attrition_hazard_per_interval_unwt"] == (
                pytest.approx(cell["n_attrit"] / n)
            ), (name, key)
            assert cell["attrition_over_death_wt"] == pytest.approx(
                cell["attrition_hazard_per_interval_wt"]
                / cell["death_hazard_per_interval_wt"]
            ), (name, key)
            assert (
                0
                <= cell["share_of_attriters_with_later_known_death_unwt"]
                <= 1
            )
            assert 0 <= cell["share_of_attriters_observed_again_unwt"] <= 1
            if name == "declared_1997_plus":
                assert cell["mean_interval_length_years"] == 2.0
            elif name == "pre_1997":
                assert cell["mean_interval_length_years"] == 1.0
            else:
                assert 1.0 < cell["mean_interval_length_years"] < 2.0
    assert (
        0
        < overlap_all
        <= (art["data"]["post_death_observations"]["n_post_death_slices"])
    )
    for key in art["cell_order"]:
        for field in counts:
            assert (
                windows["declared_1997_plus"][key][field]
                + windows["pre_1997"][key][field]
                == windows["all"][key][field]
            ), (key, field)
    declared = windows["declared_1997_plus"]
    young = declared["25-34|female"][
        "share_of_attriters_with_later_known_death_unwt"
    ]
    reading = evidence["reading"]
    assert f"{100 * young:.1f}% at 25-34|female" in reading
    for sex in ("male", "female"):
        share = declared[f"85+|{sex}"][
            "share_of_attriters_with_later_known_death_unwt"
        ]
        assert f"{100 * share:.1f}% ({sex})" in reading
    assert "the R4 evidence" in reading


def test_attrition_gradient_is_the_r4_evidence():
    """Attrition and death are least separable at 85+, in both sexes."""
    art = _artifact()
    declared = art["governance"]["censoring"]["evidence_against"][
        "attrition_versus_death_by_age_and_sex"
    ]["table"]["windows"]["declared_1997_plus"]
    for sex in ("male", "female"):
        later = [
            declared[f"{band}|{sex}"][
                "share_of_attriters_with_later_known_death_unwt"
            ]
            for band in art["age_bands"]
        ]
        assert later == sorted(later), (sex, later)
        ratio = [
            declared[f"{band}|{sex}"]["attrition_over_death_wt"]
            for band in art["age_bands"]
        ]
        assert ratio == sorted(ratio, reverse=True), (sex, ratio)
        assert ratio[0] > 10
        assert ratio[-1] < 1
        assert later[0] < 0.05
        assert later[-1] > 0.6


# --------------------------------------------------------------------------
# External anchor: carried forward under the pinned convention
# --------------------------------------------------------------------------
def test_nchs_reference_pinned_by_sha256():
    art = _artifact()
    committed_sha = _sha(NCHS)
    assert art["external_anchor"]["nchs_reference_sha256"] == committed_sha
    assert art["revision_pins"]["nchs_reference_sha256"] == committed_sha
    assert art["external_anchor"]["nchs_vintage_year"] == 2023
    ref = json.loads(NCHS.read_text())
    carried = art["external_anchor"]["nchs_source_file_sha256"]
    for pop, meta in ref["fetch"]["source_files"].items():
        assert carried[pop] == meta["sha256"]


def test_undercount_reported_not_calibrated_in_every_window():
    art = _artifact()
    v1 = _v1()
    anchor = art["external_anchor"]
    for field in ("undercount_note", "band_central_rate_formula"):
        assert anchor[field] == v1["external_anchor"][field], field
    assert "must NOT gate a level match" in anchor["gating_ruling_inherited"]
    assert len(anchor["concept_deltas_named"]) >= 4
    assert set(anchor["windows"]) == {"all", "recent", "declared_1997_plus"}
    assert set(anchor["windows_survival_v1_v2_convention"]) == {
        "all",
        "declared_1997_plus",
    }
    for group in ("windows", "windows_survival_v1_v2_convention"):
        for name, window in anchor[group].items():
            ratios = [
                c["ratio"]
                for c in window["by_band_sex"].values()
                if c["ratio"] is not None
            ]
            assert len(ratios) == 14, (group, name)
            assert all(r < 1.0 for r in ratios), (group, name)
            assert window["ratio_summary"]["median_ratio"] < 1.0


def test_external_ratios_recompute_from_parts():
    art = _artifact()
    anchor = art["external_anchor"]
    for group in ("windows", "windows_survival_v1_v2_convention"):
        for name, window in anchor[group].items():
            for key, cell in window["by_band_sex"].items():
                if cell["ratio"] is None:
                    continue
                assert cell["psid_m"] == pytest.approx(
                    cell["psid_deaths_wt"] / cell["psid_exposure_py"]
                ), (group, name, key)
                assert cell["ratio"] == pytest.approx(
                    cell["psid_m"] / cell["nchs_M"]
                ), (group, name, key)


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


def test_external_anchor_windows_carry_the_declared_events():
    art = _artifact()
    anchor = art["external_anchor"]
    effect = art["death_ascertainment"]["pinned_rule_effect"]
    band = art["death_ascertainment"]["sensitivity_band"]
    assert anchor["windows"]["all"]["total_death_events_unwt"] == (
        effect["death_events_pinned_convention"]
    )
    assert anchor["windows"]["declared_1997_plus"][
        "total_death_events_unwt"
    ] == (
        band["expected_death_events_by_convention_declared_universe"][PINNED]
    )
    survival = anchor["windows_survival_v1_v2_convention"]
    assert survival["all"]["total_death_events_unwt"] == (
        effect["death_events_survival_convention"]
    )
    v2_windows = _v2()["external_anchor"]["windows"]
    for name in ("all", "declared_1997_plus"):
        assert survival[name] == v2_windows[name], name
    for name in ("all", "declared_1997_plus"):
        assert anchor["windows"][name]["n_slices"] == (
            survival[name]["n_slices"]
        )
    scope = art["t_max_scope"]
    claim = scope["which_surface_this_artifact_is_about"]
    assert str(effect["death_events_pinned_convention"]) in claim
    assert (
        str(anchor["windows"]["declared_1997_plus"]["total_death_events_unwt"])
        in claim
    )
    assert "pinned convention" in claim


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


def test_t_max_scope_quotes_the_m6_artifact_accurately():
    art = _artifact()
    ref = art["t_max_scope"]["m6_reference"]
    assert ref["sha256"] == _sha(M6_FLOORS)
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
    assert (
        art["external_anchor"]["windows"]["all"]["total_death_events_unwt"]
        > 10 * ref["fully_pooled_n_events_full"]
    )


def test_gates_yaml_citations_still_point_at_what_they_claim():
    """A stale line citation is the defect the v2 rebuild answered."""
    art = _artifact()
    block = art["gates_yaml_citations"]
    assert block["file"] == "gates.yaml"
    assert block["sha256"] == _sha(GATES)
    assert art["revision_pins"]["gates_yaml_sha256"] == block["sha256"]
    lines = GATES.read_text().splitlines()
    assert block["n_lines"] == len(lines)
    assert block["citations"]
    for entry in block["citations"]:
        assert lines[entry["line"] - 1].strip() == entry["text"], entry


def test_every_gates_yaml_line_the_artifact_cites_is_pinned():
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


# --------------------------------------------------------------------------
# Anchor invariants: reported, never gated, recomputable from per-seed
# --------------------------------------------------------------------------
def _half_hazards(art: dict, sides: tuple[str, ...]) -> list[dict]:
    per_seed = _block(art, PINNED, "declared_1997_plus")["per_seed"]
    return [
        entry[f"hazards_side_{side}"] for entry in per_seed for side in sides
    ]


def test_sex_dominance_is_reported_not_gated():
    art = _artifact()
    invariants = art["anchor_invariants"]
    assert invariants["reported_not_gated"] is True
    assert invariants["universe"] == "declared_1997_plus"
    assert invariants["convention"] == PINNED
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


def test_the_dominance_margin_narrowed_from_v2_and_still_clears_margin_k():
    """The pinned convention's side effect on the anchor, measured."""
    art = _artifact()
    v2 = _v2()
    headline = art["anchor_invariants"]["sex_dominance"]["headline"]
    v2_headline = v2["anchor_invariants"]["sex_dominance"]["headline"]
    assert headline["band_set"] == v2_headline["band_set"]
    for field in (
        "margin_sigma_units_side_a",
        "margin_sigma_units_both_sides",
    ):
        assert headline[field] < v2_headline[field], field
        assert headline[field] >= 3.0, field
    assert headline["clears_margin_k_side_a"] is True
    assert headline["clears_margin_k_both_sides"] is True
    note = art["proposed_thresholds_note"]
    assert f"{headline['margin_sigma_units_side_a']} half-split sd units" in (
        note
    )


def test_the_dominance_cell_is_the_only_surface_seeing_the_differential():
    """The reason the anchor is load-bearing, checked from the numbers.

    Every internal cell that clears the cap has a full-panel male/female
    log gap inside its own k=3 tolerance, so a sex-flat candidate
    reproduces every clearing cell. v2's stronger reading -- that the
    clearing bands are the bands with the SMALLEST gaps -- is measured
    under both conventions and recorded either way; under the pinned
    convention the 75-84 gap rises above the 65-74 gap and the artifact
    says so.
    """
    art = _artifact()
    dominance = art["anchor_invariants"]["sex_dominance"]
    stability = _block(art, PINNED, "declared_1997_plus")["cell_stability"]
    clearing = sorted(
        k for k, c in stability.items() if c["clears_t_max_at_k3"]
    )
    assert clearing
    panels = {
        PINNED: art["external_anchor"]["windows"]["declared_1997_plus"][
            "by_band_sex"
        ],
        SURVIVAL: art["external_anchor"]["windows_survival_v1_v2_convention"][
            "declared_1997_plus"
        ]["by_band_sex"],
    }

    def gap(panel: dict, band: str) -> float:
        return abs(
            math.log(
                panel[f"{band}|male"]["psid_m"]
                / panel[f"{band}|female"]["psid_m"]
            )
        )

    per_cell = dominance["clearing_cells_gap_vs_tolerance"]
    assert sorted(per_cell) == clearing
    for key, entry in per_cell.items():
        band = key.split("|")[0]
        assert entry["full_panel_abs_log_gap"] == pytest.approx(
            gap(panels[PINNED], band)
        ), key
        assert entry["tolerance_k3"] == stability[key]["tolerance_k3"]
        assert entry["gap_within_tolerance"] is bool(
            entry["full_panel_abs_log_gap"] <= entry["tolerance_k3"]
        )
        assert entry["gap_within_tolerance"] is True, key
    assert dominance["every_clearing_cell_gap_within_its_tolerance"] is True

    ranking = dominance["band_gap_ranking"]
    clearing_bands = [
        b for b in art["age_bands"] if any(k.startswith(b) for k in clearing)
    ]
    assert ranking["clearing_bands"] == clearing_bands
    for name, panel in panels.items():
        block = ranking[name]
        gaps = {band: gap(panel, band) for band in art["age_bands"]}
        assert set(block["gaps"]) == set(gaps)
        for band, value in gaps.items():
            assert block["gaps"][band] == pytest.approx(value), (name, band)
        assert block["ascending"] == sorted(gaps, key=gaps.get)
        smallest = block["ascending"][: len(clearing_bands)]
        assert ranking["smallest_gap_bands_are_the_clearing_bands"][
            name
        ] is bool(sorted(smallest) == sorted(clearing_bands))
    flags = ranking["smallest_gap_bands_are_the_clearing_bands"]
    # v2's reading was true of the survival convention; the artifact
    # records what the pinned convention did to it.
    assert flags[SURVIVAL] is True
    why = dominance["why_this_matters"]
    if flags[PINNED]:
        assert "still holds" in why
    else:
        assert "WITHDRAWN" in why
    for band in clearing_bands:
        assert f"{band} {ranking[PINNED]['gaps'][band]:.3f}" in why
    assert "the ceremony's ruling" in why
    for band in dominance["headline"]["band_set"]:
        assert band not in clearing_bands


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


def test_the_cited_gate_m4_anchor_margins_bracket_the_quoted_range():
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
    headline = art["anchor_invariants"]["sex_dominance"]["headline"]
    assert "4.797-12.806" in headline["thinness_note"]
    assert headline["margin_sigma_units_side_a"] < min(margins)


def test_person_identity_check_shows_no_pad_rows():
    art = _artifact()
    check = art["data"]["person_identity_check"]
    assert check == _v2()["data"]["person_identity_check"]
    assert check["no_pad_rows_present"] is True
    assert check["n_nonpositive_person_ids"] == 0
    assert check["min_person_id"] > 0
    adapter = (ROOT / "scripts" / "registered_m6_inputs.py").read_text()
    assert "PAD_IDENTITY_DISCLOSURE" not in adapter
    assert "c9cc6f1e71fab96ef830d7e7b434ee216f1a96c8" in check["rule"]
    assert "12d782f84e18cda0293edba19389e7672ab80477" in check["rule"]


def test_open_questions_are_recorded_and_unanswered():
    art = _artifact()
    questions = art["open_questions_for_the_ceremony"]
    assert len(questions) >= 5
    topics = " ".join(q["question"] for q in questions)
    for topic in (
        "85+",
        "MARGIN_K",
        "eligibility",
        "tie-break",
        "post-death",
    ):
        assert topic in topics, topic
    details = " ".join(q["detail"] for q in questions)
    assert "rules nothing" in details
    assert "within_rule_sensitivity" in details


def test_proposed_thresholds_note_quotes_the_measurements():
    art = _artifact()
    note = art["proposed_thresholds_note"]
    pre_share = art["weight_universe"]["measurement"]["pre_1997"][
        "share_of_weighted_exposure"
    ]
    assert f"{100 * pre_share:.4f}%" in note
    declared = art["death_ascertainment"]["measured_movement"][
        "declared_1997_plus"
    ]
    assert f"{declared['numerator_change_vs_survival_pct'][PINNED]:.2f}%" in (
        note
    )
    assert f"than {declared['max_abs_delta_tolerance_k3'][PINNED]:.3f};" in (
        note
    )
    assert "DEMOTES []" in note
    assert "PROMOTES []" in note
    stability = _block(art, PINNED, "declared_1997_plus")["cell_stability"]
    clearing = sorted(
        k for k, c in stability.items() if c["clears_t_max_at_k3"]
    )
    assert f"ln(1.5): {clearing}" in note
    assert "PINNED death-ascertainment convention" in note
    assert "DECLARED censoring convention" in note
    assert "binds both sides of every score" in note
    assert "WITHDRAWN" in note


# --------------------------------------------------------------------------
# Reproduction from PSID (skipped off-machine; NO populace-fit)
# --------------------------------------------------------------------------
_REAL: dict = {}


def _real(builder) -> dict:
    """The four convention frames, built once per session."""
    if not _REAL:
        from populace_dynamics.data import deaths, panels

        demo = panels.demographic_panel()
        death_records = deaths.read_death_records()
        frames, detail = builder.build_convention_frames(demo, death_records)
        _REAL.update(demo=demo, dr=death_records, frames=frames, detail=detail)
    return _REAL


@needs_real_ind
def test_convention_frames_and_seed0_reproduce_without_populace_fit():
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert (
        "populace.fit" not in sys.modules
    ), "importing the v3 mortality builder pulled populace.fit"
    real = _real(builder)
    frames, detail = real["frames"], real["detail"]
    art = _artifact()
    da = art["death_ascertainment"]

    # The frames carry the committed expected event totals.
    band = da["sensitivity_band"]
    for name, frame in frames.items():
        assert float(frame.death.sum()) == pytest.approx(
            band["expected_death_events_by_convention"][name]
        ), name
        assert len(frame) == art["data"]["n_slices"]
        assert frame.person_id.nunique() == (
            art["data"]["n_persons_with_exposure"]
        )
    # The classification, the rates, the pinned effect and the targets.
    _assert_close(detail["classification"], da["classification"])
    _assert_close(detail["ascertainment_rates"], da["ascertainment_rates"])
    _assert_close(detail["pinned_rule_effect"], da["pinned_rule_effect"])
    _assert_close(
        detail["upper_band_targets"]["band_upper_informed"],
        band["upper_end_informed"]["targets"],
    )
    _assert_close(
        detail["upper_band_targets"]["band_upper_packet_literal"],
        band["upper_end_packet_literal"]["targets"],
    )
    _assert_close(detail["grid"], da["grid"])

    # Seed 0 of the pinned convention reproduces on both universes.
    pinned = frames[PINNED]
    for universe, start, full in (
        ("declared_1997_plus", 1997, True),
        ("all_v1_comparable", None, False),
    ):
        got = builder.measure_seed(0, pinned, start_year_min=start, full=full)
        ref = _block(art, PINNED, universe)["per_seed"][0]
        assert ref["seed"] == 0
        assert got["n_persons_side_a"] == ref["n_persons_side_a"]
        assert got["n_persons_side_b"] == ref["n_persons_side_b"]
        _assert_close(got["cells"], ref["cells"], universe)
        if full:
            _assert_close(got["hazards_side_a"], ref["hazards_side_a"])
            _assert_close(got["hazards_side_b"], ref["hazards_side_b"])
    # Seed 0 of v2 still comes off the survival frame.
    got = builder.v2b.measure_seed(0, frames[SURVIVAL], start_year_min=1997)
    ref = _v2()["internal_noise_floor"]["universes"]["declared_1997_plus"][
        "per_seed"
    ][0]
    _assert_close(got["cells"], ref["cells"])

    # The declared anchor under the pinned convention reproduces.
    nchs_rates = builder.v1b.nchs_band_rates(json.loads(NCHS.read_text()))
    got_anchor = builder.v1b.external_anchor(
        pinned, nchs_rates, start_year_min=1997
    )
    _assert_close(
        got_anchor, art["external_anchor"]["windows"]["declared_1997_plus"]
    )
    assert "populace.fit" not in sys.modules


@needs_real_ind
def test_weight_universe_and_psid_pins_reproduce():
    builder = _import_builder()
    real = _real(builder)
    survival = real["frames"][SURVIVAL]
    art = _artifact()
    wu = art["weight_universe"]

    table = builder.weight_resolution_table()
    assert table == wu["resolution_table"]
    series_by_wave = {row["wave"]: row["series"] for row in table}
    assert series_by_wave == builder.v2b.weight_series_by_wave()
    _assert_close(builder.weight_series_summary(table, survival), wu["series"])
    _assert_close(
        builder.per_cell_series_shares(survival, series_by_wave),
        wu["per_cell_shares"],
    )
    _assert_close(builder.sample_stratum_shares(survival), wu["sample_strata"])
    _assert_close(
        builder.v2b.weight_universe_report(survival, series_by_wave),
        wu["measurement"],
    )
    _assert_close(
        builder.v2b.universe_equivalence(survival), wu["universe_equivalence"]
    )

    ind_dir = builder._psid_ind_dir()
    pins = art["revision_pins"]
    assert pins["psid_ind2023er_sps_sha256"] == _sha(ind_dir / "IND2023ER.sps")
    assert pins["psid_ind2023er_codebook_sha256"] == _sha(
        ind_dir / "IND2023ER_codebook.pdf"
    )
    assert pins["psid_ind2023er_txt_sha256"] == _sha(ind_dir / "IND2023ER.txt")
    assert "populace.fit" not in sys.modules


@needs_real_ind
def test_attrition_and_within_rule_sensitivity_reproduce():
    builder = _import_builder()
    real = _real(builder)
    demo, dr, frames = real["demo"], real["dr"], real["frames"]
    art = _artifact()

    _, next_wave = builder._grid(demo)
    obs = builder._observed_frame(demo, dr)
    dr_pinned = builder.assign_narrow_death_years(dr)
    pi = builder.person_interval_table(obs, dr_pinned, dr, next_wave)
    _assert_close(
        builder.attrition_evidence(pi),
        art["governance"]["censoring"]["evidence_against"][
            "attrition_versus_death_by_age_and_sex"
        ]["table"],
    )
    _assert_close(
        builder.within_rule_sensitivity(demo, dr, frames[PINNED]),
        art["death_ascertainment"]["within_rule_sensitivity"],
    )
    _assert_close(
        builder.post_death_observation_note(frames[SURVIVAL], dr),
        art["data"]["post_death_observations"],
    )
    _assert_close(
        builder.censoring_rule_quote(), art["governance"]["censoring"]["rule"]
    )
    assert "populace.fit" not in sys.modules
