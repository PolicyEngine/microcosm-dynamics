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
  of the file (with the 49 -> 44 link asserted record by record), the
  ascertainment rates and the band's three upper ends from ``r``, the
  convention movement from the hazards and the per-convention floors
  (against survival AND against the pinned convention), the censoring
  quote from the v1 builder's own lines, the PSID/NCHS ratio summaries
  from the anchor windows and the attrition table from its counts with
  the exact continue-and-die overlap identity. The survival
  convention's floors are asserted equal to the committed v2 bytes, so
  v3 is tied to v2 without touching PSID; the v1 and v2 artifacts AND
  THIS ARTIFACT are asserted byte-identical to their committed digests
  (``V3_COMMITTED``, the gate-3 digest-pin precedent); the committed
  inputs and this artifact's own builder are sha256-pinned; the
  inherited reference constants are pinned to literals; and
  ``gates.yaml`` is checked under a PRE-LOCK MARKER
  (``GATE_MORTALITY_BLOCK_LANDED``) rather than frozen.
* SYNTHETIC tests of the ascertainment convention on hand-made
  death-code frames (no PSID): the midpoint rule, its tie-break, the
  band-end target sets and the fractional-death expected-value
  identities -- so the convention cannot move in CI where the
  PSID-gated tests skip (referee B, D-4).
* PSID-gated reproduction pins (skipped when the PSID individual file
  is absent) that rebuild the five convention frames and reproduce the
  classification, the rates, ALL 100 seeds of the headline block and
  seeds 0, 37 and 99 of every other block (including the upper ends'
  floor values), seed 0 of v2 on the survival frame, the declared
  anchor, the resolution table, the per-cell shares on both frames, the
  attrition table and the within-rule sensitivity -- with
  ``populace.fit`` never imported.

``gates.yaml`` is READ, never frozen (referee B, D-1): cited-line text
is compared against the contract at the recorded git blob
(``gates_yaml_citations.git_blob``, resolved with ``git cat-file``),
never against the live file's whole-file sha256 or line count -- the
gate_m4 / gate_m6 precedent under which a floor is pinned by path and
governance. The live contract may move (the gate block itself will move
it) without this suite turning red.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
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
BUILDER_V3 = SCRIPTS / "build_mortality_floors_v3.py"

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
#: THIS artifact's committed bytes (size, sha256), re-stated by the
#: 2026-09-07 record sitting after the rebuild (referee A D1 / B D-4:
#: the digest-pin precedent of the gate-3 suites). A rebuilt artifact
#: under a moved convention cannot replace this one silently; any
#: rebuild must re-state this constant in the same commit.
V3_COMMITTED = (
    2_711_564,
    "8998bca2d7026926cc44a199087810bc654863c12b2d14466ce0ff73f95e0776",
)
#: The commit the committed artifact records it was built on
#: (``revision_pins.populace_dynamics_sha``): the v3 commit the record
#: sitting fixed over.
BUILT_ON = "2fbde39e2ca5be17552e601c9c9b4a96bf40ee33"

#: PRE-LOCK MARKER (referee B, D-5). False until the commit that inserts
#: the ``gate_mortality`` block into ``gates.yaml`` flips it to True.
#: While False, ``test_gates_yaml_pre_lock_guard`` asserts gates.yaml is
#: innocent of this artifact; flipped, the same test asserts the block
#: exists and cites THIS artifact by path (the gate2c / gate_m4
#: post-lock guard shape). The gate commit flips ONE constant instead of
#: deleting a test.
GATE_MORTALITY_BLOCK_LANDED = False

T_MAX = math.log(1.5)
UNIVERSES = ("declared_1997_plus", "all_v1_comparable")
CONVENTIONS = (
    "survival_v1_v2",
    "pinned_narrow_midpoint",
    "band_upper_informed",
    "band_upper_packet_literal",
    "band_upper_truly_literal",
)
PINNED = "pinned_narrow_midpoint"
SURVIVAL = "survival_v1_v2"
INFORMED = "band_upper_informed"
RESIDUE_LITERAL = "band_upper_packet_literal"
TRULY_LITERAL = "band_upper_truly_literal"
UPPER_ENDS = (INFORMED, RESIDUE_LITERAL, TRULY_LITERAL)
#: Seeds the PSID-gated tier reproduces for every block that is not the
#: headline (the headline block is reproduced on all 100 seeds).
SPOT_SEEDS = (0, 37, 99)

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


def _git_blob(blob_id: str) -> bytes | None:
    """The bytes of a git blob from this checkout, or None off-git."""
    try:
        return subprocess.check_output(
            ["git", "cat-file", "blob", blob_id],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None


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


def test_gates_yaml_pre_lock_guard():
    """The rebuild is evidence, not a wired-in derivation basis.

    PRE-LOCK GUARD under ``GATE_MORTALITY_BLOCK_LANDED`` (referee B,
    D-5). While the marker is False, gates.yaml must mention neither
    this artifact nor ``gate_mortality``. The commit that inserts the
    gate block flips the marker to True instead of deleting this test;
    flipped, the same test asserts the block exists as a top-level
    gate and cites THIS artifact by path -- the gate2c / gate_m4
    post-lock guard shape. The artifact itself stays a reported anchor
    either way (``reported_anchor_not_gated``); the gate reads it by
    path, it does not become a gate.
    """
    gates_text = GATES.read_text()
    art = _artifact()
    assert art["reported_anchor_not_gated"] is True
    if not GATE_MORTALITY_BLOCK_LANDED:
        assert "mortality_floors_v3" not in gates_text
        assert "gate_mortality" not in gates_text
        return
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(gates_text)
    assert "gate_mortality" in spec["gates"]
    assert "runs/mortality_floors_v3.json" in gates_text


def test_artifact_bytes_are_pinned_to_the_committed_digest():
    """THIS artifact's size and sha256 equal the constant in this file.

    The digest-pin precedent of the gate-3 suites (referee A D1 / B
    D-4): nothing machine-readable stopped a rebuilt artifact under a
    moved convention from replacing the committed one under the same
    file name. Now the constant must be re-stated in the same commit as
    any rebuild, which is the review surface.
    """
    assert ARTIFACT.stat().st_size == V3_COMMITTED[0]
    assert _sha(ARTIFACT) == V3_COMMITTED[1]


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
    """Every committed input, AND this artifact's own builder, by sha256.

    ``gates_yaml_sha256`` is PROVENANCE (the digest of the contract the
    citations were made against, cross-checked against the recorded
    blob in ``test_gates_yaml_citations_match_the_recorded_blob``); it
    is deliberately NOT compared with the live file (referee B, D-1).
    """
    art = _artifact()
    pins = art["revision_pins"]
    assert pins["nchs_reference_sha256"] == _sha(NCHS)
    assert pins["v1_artifact_sha256"] == _sha(V1_ARTIFACT)
    assert pins["v2_artifact_sha256"] == _sha(V2_ARTIFACT)
    assert re.fullmatch(r"[0-9a-f]{64}", pins["gates_yaml_sha256"])
    assert pins["gates_yaml_sha256"] == art["gates_yaml_citations"]["sha256"]
    assert re.fullmatch(r"[0-9a-f]{40}", pins["gates_yaml_git_blob"])
    assert (
        pins["gates_yaml_git_blob"] == art["gates_yaml_citations"]["git_blob"]
    )
    assert "NOT a freeze of the live file" in pins["gates_yaml_pin_semantics"]
    assert pins["builder_v1_sha256"] == _sha(BUILDER_V1)
    assert pins["builder_v2_sha256"] == _sha(BUILDER_V2)
    # The builder that produced these bytes is the committed one
    # (referee B D-4): an edited builder must rebuild and re-pin.
    assert pins["builder_v3_sha256"] == _sha(BUILDER_V3)
    assert art["t_max_scope"]["m6_reference"]["sha256"] == _sha(M6_FLOORS)
    assert re.fullmatch(r"[0-9a-f]{40}", pins["populace_dynamics_sha"])
    assert pins["populace_dynamics_sha"] == BUILT_ON
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
    # The upper ends' half-death counts are ROUNDED EXPECTATIONS over
    # fractional deaths and say so (referee A, D7); the integer frames
    # say their counts are exact.
    for convention, meta in inf["conventions"].items():
        semantics = meta["count_semantics"]
        if convention in (SURVIVAL, PINNED):
            assert semantics.startswith("exact integer death counts")
        else:
            assert semantics.startswith("ROUNDED EXPECTED counts")
            assert "nothing gates on these counts" in semantics
    assert "RESIDUE-LITERAL" in inf["conventions"][RESIDUE_LITERAL]["role"]
    assert "NOT the packet's literal" in (
        inf["conventions"][RESIDUE_LITERAL]["role"]
    )
    assert "TRULY LITERAL" in inf["conventions"][TRULY_LITERAL]["role"]


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
    # The start-wave range is 1997-2021: the 2023 wave is the terminal
    # grid wave and starts no interval (referee A D3, referee B D-9).
    # Recomputed from the committed series block, not asserted by hand.
    first, last = wu["series"]["CORE/IMM INDIVIDUAL CROSS-SECTION WT"][
        "measured_in_frame"
    ]["start_waves_present"]
    assert (first, last) == (1997, 2021)
    assert f"interval start waves {first}-{last}" in (
        declaration["declared_weight_universe"]
    )
    assert "1997-2023" not in declaration["declared_weight_universe"]
    assert "terminal grid wave" in declaration["declared_weight_universe"]
    estimand = art["estimand"]
    assert estimand["declared_universe_start_wave"] == 1997
    assert estimand["declared_universe_last_start_wave"] == last
    assert estimand["declared_weight_universe"] == (
        declaration["declared_weight_universe"]
    )
    assert estimand["death_ascertainment_convention"] == PINNED
    assert estimand["censoring_convention"] == "governance.censoring.rule"
    assert "INTERVIEW-CONDITIONAL" in (
        estimand["hazard_is_interview_conditional"]
    )
    governance = art["governance"]["weight_universe"]
    assert governance["declared"] == "weight_universe.declaration"
    assert "binds both sides of every score" in governance["binds"]
    assert "report-only" in governance["binds"]
    assert f"{first}-{last}" in governance["binds"]
    # The old phrase survives only inside the record of its correction.
    # (The series' codebook.waves is legitimately "1997-2023": the series
    # is RESOLVED for the 2023 wave; no interval STARTS there.) Counted,
    # not diffed: a failed `not in` on a 2.7 MB dump would make pytest
    # render a difflib diff of the whole artifact.
    live = dict(art)
    live.pop("record_corrections")
    assert json.dumps(live).count("start waves 1997-2023") == 0
    assert (
        json.dumps(art["record_corrections"]).count(
            "interval start waves 1997-2023"
        )
        == 1
    )


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
    # The frame each figure is on is stated (referee A D4, B D-7).
    assert withdrawal["measured_on_frame"].startswith(SURVIVAL)
    assert "premise_on_pinned_frame" in withdrawal["measured_on_frame"]

    # 1. premise -- on the survival frame (v2's figures) and, recorded
    # beside it, on the pinned frame; both recompute from their cells.
    def _recompute(block: dict) -> tuple[int, int]:
        higher = lower = 0
        for key, cell in block["per_cell"].items():
            expected = math.log(
                cell["m_pre_1997_within_window"]
                / cell["m_1997_plus_within_window"]
            )
            assert cell["ln_pre_over_post"] == pytest.approx(expected), key
            assert cell["older_decades_run_higher"] is bool(expected > 0)
            higher += expected > 0
            lower += expected < 0
        assert block["n_cells_older_decades_higher"] == higher
        assert block["n_cells_older_decades_lower"] == lower
        assert higher + lower == 14
        for key in ("85+|male", "85+|female"):
            assert block["per_cell"][key]["ln_pre_over_post"] < -0.3, key
        return higher, lower

    premise = withdrawal["premise_measured"]
    assert premise["frame"] == SURVIVAL
    higher, lower = _recompute(premise)
    assert lower >= 7
    assert f"holds in only {higher} of 14 cells and fails in {lower}" in (
        premise["reading"]
    )
    pinned_premise = withdrawal["premise_on_pinned_frame"]
    assert pinned_premise["frame"] == PINNED
    higher_p, lower_p = _recompute(pinned_premise)
    assert lower_p >= 7
    assert f"holds in {higher_p} of 14 cells and fails in {lower_p}" in (
        pinned_premise["reading"]
    )
    assert f"on the pinned frame the premise fails in {lower_p} of 14" in (
        withdrawal["verdict"]
    )
    # Each frame's 1997+ within-window hazard IS that frame's declared
    # anchor hazard, so the two premise blocks are tied to the two anchor
    # window sets by value (survival -> v2's carried windows, pinned ->
    # the headline windows).
    anchor = art["external_anchor"]
    survival_declared = anchor["windows_survival_v1_v2_convention"][
        "declared_1997_plus"
    ]["by_band_sex"]
    pinned_declared = anchor["windows"]["declared_1997_plus"]["by_band_sex"]
    for key in art["cell_order"]:
        assert premise["per_cell"][key]["m_1997_plus_within_window"] == (
            pytest.approx(survival_declared[key]["psid_m"])
        ), key
        assert pinned_premise["per_cell"][key][
            "m_1997_plus_within_window"
        ] == pytest.approx(pinned_declared[key]["psid_m"]), key
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
    # The 49 -> 44 link (referee A D5, B D-8): counted == observed at
    # the grid wave containing the midpoint AND banded at the midpoint
    # age; every count in the decomposition ties to the classification
    # and to the pinned rule's added events.
    d = classification["narrow_counted_decomposition"]
    added = art["death_ascertainment"]["pinned_rule_effect"][
        "death_events_added"
    ]
    assert d["n_narrow"] == narrow["n"]
    assert d["counted_in_pinned_frame"] == added
    assert d["counted_in_pinned_frame"] == d["of_which_banded_at_midpoint_age"]
    assert (
        d["of_which_banded_at_midpoint_age"]
        <= d["observed_at_grid_wave_containing_midpoint"]
        <= narrow["in_frame"]
    )
    assert d["observed_at_lo"] == narrow["observed_at_lo"]
    assert (
        d["observed_at_lo_and_counted"] + d["observed_at_lo_not_counted"]
        == d["observed_at_lo"]
    )
    assert (
        d["observed_at_lo_and_counted"] + d["counted_not_observed_at_lo"]
        == d["counted_in_pinned_frame"]
    )
    ages = d["observed_at_lo_not_counted_ages_at_midpoint"]
    assert len(ages) == d["observed_at_lo_not_counted"]
    assert all(age < 25 for age in ages)
    persons = d["counted_not_observed_at_lo_persons"]
    assert len(persons) == d["counted_not_observed_at_lo"]
    for p in persons:
        assert p["lo_is_grid_wave"] is False
        assert p["lo"] <= p["midpoint"] <= p["hi"]
        assert p["wave_of_midpoint"] <= p["midpoint"]
        assert p["age_at_midpoint"] >= 25
    assert d["last_wave_before_lo"] == narrow["in_frame_last_wave_before_lo"]
    assert (
        d["last_wave_before_lo_and_counted"]
        + d["last_wave_before_lo_never_scored"]
        == d["last_wave_before_lo"]
    )
    assert d["last_wave_before_lo_and_counted"] == len(persons)
    assert "observed_at_lo is a record count" in d["rule"]
    assert (
        f"the link from {d['observed_at_lo']} to {d['counted_in_pinned_frame']}"
        in reading
    )
    assert (
        f"{d['observed_at_lo_and_counted']} of the {d['observed_at_lo']}"
        in (reading)
    )
    assert f"{d['last_wave_before_lo_never_scored']} of them died after" in (
        reading
    )
    assert "asserted record by record" in reading


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
    truly = band["upper_end_truly_literal"]
    assert informed["convention"] == INFORMED
    assert literal["convention"] == RESIDUE_LITERAL
    assert truly["convention"] == TRULY_LITERAL
    classification = da["classification"]
    for end in (informed, literal, truly):
        targets = end["targets"]
        assert sum(targets["by_status"].values()) == targets["n_persons"]
        assert sum(targets["by_range_span_class"].values()) == (
            targets["n_persons"]
        )
        assert targets["by_range_span_class"]["na_year"] == (
            targets["by_status"].get("na_dk", 0)
        )
        assert sum(targets["by_start_wave_era"].values()) == (
            targets["n_persons"]
        )
        assert targets["n_with_banded_start_age"] <= targets["n_persons"]
        assert (
            targets["n_with_banded_start_age_and_last_wave_1997_plus"]
            <= targets["n_with_banded_start_age"]
        )
        assert targets["expected_added_death_events_all_ages"] == (
            pytest.approx(r * targets["n_persons"])
        )
        # The committed frame deltas ARE the added expected events.
        assert events[end["convention"]] - events[PINNED] == pytest.approx(
            targets["expected_added_death_events_in_banded_frame"]
        )
        assert declared[end["convention"]] - declared[PINNED] == (
            pytest.approx(
                targets[
                    "expected_added_death_events_in_banded_frame_declared_universe"
                ]
            )
        )
    # The two RESIDUE ends: r per target with a banded start age, exactly
    # (every residue target's slices are banded or absent as a whole).
    for end in (informed, literal):
        targets = end["targets"]
        assert targets["by_range_span_class"]["narrow_span_le_2"] == 0
        assert events[end["convention"]] - events[PINNED] == pytest.approx(
            r * targets["n_with_banded_start_age"]
        )
        assert declared[end["convention"]] - declared[PINNED] == (
            pytest.approx(
                r * targets["n_with_banded_start_age_and_last_wave_1997_plus"]
            )
        )
    # The TRULY LITERAL end (referee B, D-2) targets every in-frame
    # non-exact decedent the pinned rule does not count: the residue
    # plus the narrow-coded decedents whose midpoint produced no event.
    accounting = truly["in_frame_non_exact_accounting"]
    counts = classification["status_counts"]
    assert accounting["non_exact_records"] == counts["range"] + counts["na_dk"]
    assert accounting["in_frame"] == (
        classification["narrow"]["in_frame"]
        + classification["wide"]["in_frame"]
        + classification["na_year"]["in_frame"]
    )
    assert accounting["counted_by_the_pinned_rule"] == (
        da["pinned_rule_effect"]["death_events_added"]
    )
    assert accounting["not_counted_by_the_pinned_rule"] == (
        accounting["in_frame"] - accounting["counted_by_the_pinned_rule"]
    )
    tt = truly["targets"]
    assert tt["n_persons"] <= accounting["not_counted_by_the_pinned_rule"]
    assert tt["by_range_span_class"]["narrow_span_le_2"] == (
        classification["narrow"]["in_frame"]
        - accounting["counted_by_the_pinned_rule"]
    )
    assert tt["by_range_span_class"]["wide_span_ge_3"] == (
        literal["targets"]["by_range_span_class"]["wide_span_ge_3"]
    )
    assert tt["by_range_span_class"]["na_year"] == (
        literal["targets"]["by_range_span_class"]["na_year"]
    )
    assert tt["n_persons"] > literal["targets"]["n_persons"]
    # Added events are r per banded target up to one partial (a target
    # whose start age is 24 contributes only its banded second slice).
    added_all = tt["expected_added_death_events_in_banded_frame"]
    assert r * (tt["n_with_banded_start_age"] - 1) < added_all
    assert added_all < r * (tt["n_with_banded_start_age"] + 1)
    added_declared = tt[
        "expected_added_death_events_in_banded_frame_declared_universe"
    ]
    n_recent = tt["n_with_banded_start_age_and_last_wave_1997_plus"]
    assert r * (n_recent - 1) < added_declared < r * (n_recent + 1)
    assert added_declared > declared[INFORMED] - declared[PINNED]
    # The labels say what the bytes do.
    assert literal["label"] == "the RESIDUE-LITERAL upper end"
    assert "NOT the packet's assumption taken literally" in (
        literal["name_note"]
    )
    assert "upper_end_truly_literal" in literal["name_note"]
    assert f"{literal['targets']['n_persons']} persons" in literal["rule"]
    assert "EXCLUDED from it" in literal["rule"]
    assert "TRULY LITERAL" in truly["label"]
    assert "does not COUNT" in truly["rule"]
    assert "147" in literal["what_it_is_not"]
    # Its movement against the pinned convention equals the measured
    # movement block, universe by universe.
    movement = da["measured_movement"]
    for universe in UNIVERSES:
        got = truly["movement_vs_pinned"][universe]
        block = movement[universe]
        ev = block["death_events_by_convention"]
        assert got["expected_death_events"] == ev[TRULY_LITERAL]
        assert got["added_over_pinned"] == pytest.approx(
            ev[TRULY_LITERAL] - ev[PINNED]
        )
        assert got["numerator_change_vs_pinned_pct"] == (
            block["numerator_change_vs_pinned_pct"][TRULY_LITERAL]
        )
        for key in art["cell_order"]:
            assert got["ln_over_pinned_per_cell"][key] == (
                block["per_cell"][key]["ln_over_pinned"][TRULY_LITERAL]
            )
            assert got["delta_tolerance_k3_vs_pinned_per_cell"][key] == (
                block["per_cell"][key]["delta_tolerance_k3_vs_pinned"][
                    TRULY_LITERAL
                ]
            )
        assert got["max_abs_ln_over_pinned"] == (
            block["max_abs_ln_over_pinned"][TRULY_LITERAL]
        )
        assert got["max_abs_delta_tolerance_k3_vs_pinned"] == (
            block["max_abs_delta_tolerance_k3_vs_pinned"][TRULY_LITERAL]
        )
        assert (
            got["clearing_set_k3"] == block["clearing_sets_k3"][TRULY_LITERAL]
        )
        assert got["clearing_set_unchanged_from_pinned"] is (
            got["clearing_set_k3"] == block["clearing_sets_k3"][PINNED]
        )
        assert got["clearing_set_unchanged_from_pinned"] is True
    persons = informed["targets"]["persons"]
    assert len(persons) == informed["targets"]["n_persons"]
    assert literal["targets"]["persons"] is None
    assert truly["targets"]["persons"] is None
    banded_recent = [
        p
        for p in persons
        if p["start_wave"] >= 1997 and p["age_at_start"] >= 25
    ]
    assert len(banded_recent) == (
        informed["targets"]["n_with_banded_start_age_and_last_wave_1997_plus"]
    )
    assert declared["band_upper_informed"] - declared[PINNED] == (
        pytest.approx(r * len(banded_recent))
    )
    # On the declared universe the residue-literal end adds nothing
    # beyond the informed end: every extra person was last seen before
    # 1997. The truly literal end does add there.
    assert declared["band_upper_packet_literal"] == (
        declared["band_upper_informed"]
    )
    assert declared[TRULY_LITERAL] > declared["band_upper_informed"]
    assert literal["targets"]["by_start_wave_era"]["1997_plus"] == (
        informed["targets"]["by_start_wave_era"]["1997_plus"]
    )
    for person in persons:
        assert person["death_status"] in ("range", "na_dk")
        assert person["next_wave"] > person["start_wave"]
        assert person["feasible_years"]
        for year in person["feasible_years"]:
            assert person["start_wave"] <= year < person["next_wave"]
        if person["death_status"] == "range":
            assert person["range_span"] > 2
        else:
            assert person["range_span"] is None
    wide_in_frame_overlapping = classification["wide"][
        "range_overlaps_last_observed_interval"
    ]
    assert informed["targets"]["by_status"]["range"] <= (
        wide_in_frame_overlapping
    )
    assert informed["targets"]["by_status"]["na_dk"] == (
        classification["na_year"]["in_frame_with_last_interval"]
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
        vs_pinned = [n for n in CONVENTIONS if n != PINNED]
        for name in vs_pinned:
            assert block["numerator_change_vs_pinned_pct"][name] == (
                pytest.approx(
                    100.0 * (events[name] - events[PINNED]) / events[PINNED]
                )
            )
        max_abs = {name: 0.0 for name in CONVENTIONS[1:]}
        max_dt = {name: 0.0 for name in CONVENTIONS[1:]}
        max_abs_p = {name: 0.0 for name in vs_pinned}
        max_dt_p = {name: 0.0 for name in vs_pinned}
        for key, cell in block["per_cell"].items():
            base = cell["hazard"][SURVIVAL]
            base_t = cell["tolerance_k3"][SURVIVAL]
            base_p = cell["hazard"][PINNED]
            base_pt = cell["tolerance_k3"][PINNED]
            for name in CONVENTIONS:
                stability = _block(art, name, universe)["cell_stability"][key]
                assert cell["tolerance_k3"][name] == stability["tolerance_k3"]
                assert cell["clears_t_max_at_k3"][name] is (
                    stability["clears_t_max_at_k3"]
                )
                m = cell["hazard"][name]
                t = cell["tolerance_k3"][name]
                if name != PINNED:
                    expected_p = math.log(m / base_p)
                    assert cell["ln_over_pinned"][name] == pytest.approx(
                        expected_p, abs=1e-12
                    ), (universe, key, name)
                    max_abs_p[name] = max(max_abs_p[name], abs(expected_p))
                    assert cell["delta_tolerance_k3_vs_pinned"][name] == (
                        round(t - base_pt, 3)
                    )
                    max_dt_p[name] = max(max_dt_p[name], abs(t - base_pt))
                if name == SURVIVAL:
                    continue
                expected = math.log(m / base)
                assert cell["ln_over_survival"][name] == pytest.approx(
                    expected, abs=1e-12
                ), (universe, key, name)
                max_abs[name] = max(max_abs[name], abs(expected))
                assert cell["delta_tolerance_k3"][name] == round(t - base_t, 3)
                max_dt[name] = max(max_dt[name], abs(t - base_t))
        for name in CONVENTIONS[1:]:
            assert block["max_abs_ln_over_survival"][name] == pytest.approx(
                max_abs[name], abs=1e-12
            )
            assert block["max_abs_delta_tolerance_k3"][name] == (
                pytest.approx(max_dt[name], abs=1e-12)
            )
        for name in vs_pinned:
            assert block["max_abs_ln_over_pinned"][name] == pytest.approx(
                max_abs_p[name], abs=1e-12
            )
            assert block["max_abs_delta_tolerance_k3_vs_pinned"][name] == (
                pytest.approx(max_dt_p[name], abs=1e-12)
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
    for universe, key in (
        ("declared_1997_plus", "measured_declared_universe"),
        ("all_v1_comparable", "measured_all_window"),
    ):
        vs = replaced[key]["vs_pinned"]
        assert vs["numerator_change_pct"] == (
            movement[universe]["numerator_change_vs_pinned_pct"]
        )
        assert vs["max_abs_ln_over_pinned"] == (
            movement[universe]["max_abs_ln_over_pinned"]
        )
        assert vs["max_abs_delta_tolerance_k3_vs_pinned"] == (
            movement[universe]["max_abs_delta_tolerance_k3_vs_pinned"]
        )
    # The pinned convention and the two residue ends: the packet's
    # +3.9% / 0.038 log is replaced by < 0.3% / < 0.03 log / < 0.01 in
    # tolerance. The truly literal end is larger (it targets 142
    # persons) and is bounded separately: < 1% on the numerator, < 0.01
    # log against the pinned convention, < 0.007 in any tolerance.
    for name in (PINNED, INFORMED, RESIDUE_LITERAL):
        assert declared["numerator_change_pct"][name] < 0.3
        assert declared["max_abs_ln_over_survival"][name] < 0.03
        assert declared["max_abs_delta_tolerance_k3"][name] < 0.01
    assert 0.3 < declared["numerator_change_pct"][TRULY_LITERAL] < 1.0
    assert declared["max_abs_ln_over_survival"][TRULY_LITERAL] < 0.04
    assert declared["max_abs_delta_tolerance_k3"][TRULY_LITERAL] < 0.01
    vs = declared["vs_pinned"]
    assert vs["numerator_change_pct"][TRULY_LITERAL] < 0.5
    assert vs["max_abs_ln_over_pinned"][TRULY_LITERAL] < 0.01
    assert vs["max_abs_delta_tolerance_k3_vs_pinned"][TRULY_LITERAL] < 0.007
    note = replaced["truly_literal_end_added_at_the_record_sitting"]
    assert "the clearing set is unchanged" in note
    assert "147" in note
    added = (
        movement["declared_1997_plus"]["death_events_by_convention"][
            TRULY_LITERAL
        ]
        - movement["declared_1997_plus"]["death_events_by_convention"][PINNED]
    )
    assert f"adds {added:.3f} expected events" in note
    # The clearing set is identical under all five conventions on both
    # universes: the estimate's "15% of the 85+|female tolerance" is 0.
    for universe in UNIVERSES:
        sets = movement[universe]["clearing_sets_k3"]
        assert set(sets) == set(CONVENTIONS)
        assert len({tuple(s) for s in sets.values()}) == 1
        assert sets[PINNED] == [
            "75-84|female",
            "75-84|male",
            "85+|female",
            "85+|male",
        ]
        delta_85f = movement[universe]["per_cell"]["85+|female"][
            "delta_tolerance_k3"
        ]
        for name in (PINNED, INFORMED, RESIDUE_LITERAL):
            assert delta_85f[name] == 0.0, (universe, name)
        # The truly literal end (142 targets) does reach 85+|female: it
        # TIGHTENS the tolerance by at most 0.002 (0.246 -> 0.244 on the
        # declared universe), never loosens it.
        assert -0.002 <= delta_85f[TRULY_LITERAL] <= 0.0, universe
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
    # The unit string says the three outcome flags are NOT a partition
    # and states the identity (referee B D-3, A D6).
    assert "NOT a partition" in table["unit"]
    assert "n_continue + n_deaths + n_attrit = n_person_intervals + " in (
        table["unit"]
    )
    assert f"the {table['totals']['continue_and_death']} person-intervals" in (
        table["unit"]
    )
    assert table["identity"].startswith("n_continue + n_deaths + n_attrit ==")
    counts = (
        "n_person_intervals",
        "n_deaths",
        "n_attrit",
        "n_continue",
        "n_continue_and_death",
    )
    for field, total in (
        ("n_continue", table["totals"]["continues"]),
        ("n_deaths", table["totals"]["death"]),
        ("n_attrit", table["totals"]["attrit"]),
        ("n_continue_and_death", table["totals"]["continue_and_death"]),
        ("n_person_intervals", table["n_person_intervals_banded"]),
    ):
        assert sum(c[field] for c in windows["all"].values()) == total, field
    assert (
        table["totals"]["continues"]
        + table["totals"]["death"]
        + table["totals"]["attrit"]
        == table["n_person_intervals_banded"]
        + table["totals"]["continue_and_death"]
    )
    overlap_all = 0
    for name, window in windows.items():
        assert list(window) == art["cell_order"], name
        for key, cell in window.items():
            n = cell["n_person_intervals"]
            # continues / death are not exclusive: a person recorded
            # dead in the interval AND observed at the next wave is the
            # post-death record inconsistency (data.post_death_observations).
            # attrit = neither, so the three sum to n plus that overlap,
            # which is now committed per cell and asserted EXACTLY.
            overlap = (
                cell["n_continue"] + cell["n_deaths"] + cell["n_attrit"] - n
            )
            assert overlap == cell["n_continue_and_death"], (name, key)
            assert 0 <= overlap <= 3, (name, key, overlap)
            if name == "all":
                overlap_all += overlap
    assert overlap_all == table["totals"]["continue_and_death"]
    for name, window in windows.items():
        for key, cell in window.items():
            n = cell["n_person_intervals"]
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


def test_gates_yaml_citations_match_the_recorded_blob():
    """A stale line citation is the defect the v2 rebuild answered.

    Cited-line text is compared against gates.yaml AT THE RECORDED GIT
    BLOB (``gates_yaml_citations.git_blob``, content-addressed, so it
    stays reachable through master's history after a squash merge),
    NEVER against the live file's whole-file sha256 or line count
    (referee B, D-1: no ratified floor test freezes the live contract;
    the gate block itself will move it). ``gates_yaml_sha256`` is
    provenance and must equal the digest of that blob. A citation that
    was stale when made still fails loudly. Off a git checkout the blob
    cannot be resolved; the live file then stands in only while it
    still carries the recorded digest, otherwise the check is skipped
    with its reason. The live-file phrase checks in
    ``test_t_max_scope_quotes_gates_yaml_accurately`` read by content,
    not by line, and are unaffected.
    """
    art = _artifact()
    block = art["gates_yaml_citations"]
    assert block["file"] == "gates.yaml"
    assert re.fullmatch(r"[0-9a-f]{64}", block["sha256"])
    assert re.fullmatch(r"[0-9a-f]{40}", block["git_blob"])
    assert art["revision_pins"]["gates_yaml_sha256"] == block["sha256"]
    assert "AT THE RECORDED BLOB" in block["rule"]
    assert "never against the live file" in block["rule"]
    recorded = _git_blob(block["git_blob"])
    if recorded is None:
        live = GATES.read_bytes()
        if hashlib.sha256(live).hexdigest() != block["sha256"]:
            pytest.skip(
                "gates.yaml at the recorded blob is not resolvable from "
                "this checkout and the live file has moved on; the "
                "citation text is checked against the recorded blob only"
            )
        recorded = live
    # The blob id is sha1("blob <n>\0" + bytes): recomputed, not trusted.
    assert (
        hashlib.sha1(b"blob %d\0" % len(recorded) + recorded).hexdigest()
        == block["git_blob"]
    )
    assert hashlib.sha256(recorded).hexdigest() == block["sha256"]
    lines = recorded.decode().splitlines()
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
    assert len(questions) >= 9
    topics = " ".join(q["question"] for q in questions)
    for topic in (
        "85+",
        "MARGIN_K",
        "eligibility",
        "tie-break",
        "post-death",
        "survivorship STOCK",
        "operating characteristic",
        "censoring convention",
        "stability clause",
    ):
        assert topic in topics, topic
    details = " ".join(q["detail"] for q in questions)
    assert "rules nothing" in details
    assert "within_rule_sensitivity" in details
    # R8 at headline prominence: the FIRST open question is the deferral.
    r8 = questions[0]
    assert r8["question"].startswith("R8 survivorship STOCK cell")
    assert r8["question"].endswith("DEFERRED")
    assert "STOCK_K" in r8["detail"]
    assert "certification_scope.does_not_support[0]" in r8["status"]


def test_referee_a_findings_are_carried_verbatim_and_unresolved():
    """Referee A's three statistical findings on the v3 bytes are carried
    with the referee's own numbers, attributed to the referee's report by
    path and digest, and marked NOT resolved -- this sitting resolves
    none of them and recomputes none of the referee's figures."""
    art = _artifact()
    carried = [
        q
        for q in art["open_questions_for_the_ceremony"]
        if q["question"].startswith("referee A finding")
    ]
    assert len(carried) == 3
    expected_numbers = {
        "(i)": (
            "3.139 sigma",
            "3.066 sigma",
            "0.60 / 0.37",
            "0.26 / 0.22",
            ">= 0.985",
        ),
        "(ii)": (
            "+0.27 to +0.74 log",
            "+0.281 / +0.359",
            "1.03x / 1.46x",
            "0.95-0.98x",
            "0.760 to 1.036",
            "<= 0.030",
        ),
        "(iii)": ("0.44 / 0.61", "P ~ 0.6", "[0.1, 0.9]", "1,000 seeds"),
    }
    for q in carried:
        tag = next(
            t for t in expected_numbers if f"finding {t}" in q["question"]
        )
        for number in expected_numbers[tag]:
            assert number in q["detail"], (tag, number)
        assert "carried VERBATIM" in q["detail"]
        assert "mortality-v3-referee-A/REPORT.md" in q["source"]
        assert "3daae3fe3ba767c5" in q["source"]
        assert "NOT resolved" in q["status"]
    # The one thing adopted from them is wording, and it says so.
    finding_ii = next(q for q in carried if "(ii)" in q["question"])
    assert "certification-scope wording is adopted" in finding_ii["detail"]
    assert "NOT recomputed" in finding_ii["detail"]
    assert "resolve referee A's three statistical findings" in " ".join(
        art["does_not_do"]
    )


def test_certification_scope_defers_r8_at_headline_prominence():
    """The R8 survivorship deferral and the interview-conditional scope
    (both referees; referee A section 3.4 wording) are in the artifact at
    headline prominence, with the deferral's reason."""
    art = _artifact()
    scope = art["certification_scope"]
    assert set(scope) == {
        "note",
        "headline",
        "would_support_if_ratified",
        "does_not_support",
    }
    assert "R8 -- DEFERRED" in scope["headline"]
    assert "INTERVIEW-CONDITIONAL" in scope["headline"]
    deferral = scope["does_not_support"][0]
    assert deferral["claim"].startswith("survival to claiming ages")
    assert "STOCK cell (packet R8)" in deferral["claim"]
    assert deferral["status"].startswith("DEFERRED")
    assert "STOCK_K" in deferral["reason"]
    assert "not a bounded addition" in deferral["reason"]
    assert "carries the deferral" in deferral["reason"]
    assert "not_certified" in deferral["consequence_for_the_gate_block"]
    joined = " ".join(
        d if isinstance(d, str) else json.dumps(d)
        for d in scope["does_not_support"]
    )
    for phrase in (
        "mortality DRIFT",
        "mortality LEVELS against NCHS",
        "the 25-74 cells",
        "differential (male > female) claim",
        "censoring is innocuous",
    ):
        assert phrase in joined, phrase
    stability = _block(art, PINNED, "declared_1997_plus")["cell_stability"]
    clearing = sorted(
        k for k, c in stability.items() if c["clears_t_max_at_k3"]
    )
    supports = " ".join(scope["would_support_if_ratified"])
    assert f"on this basis: {clearing}" in supports
    assert "interval start waves 1997-2021" in supports
    assert "INTERVIEW-CONDITIONAL PSID hazard" in supports
    per_cell = art["seed_count_stability"]["per_cell"]
    for key, sex in (("65-74|male", "male"), ("65-74|female", "female")):
        p = per_cell[key]["at_100_seeds_sigma_v3"][
            "p_tolerance_at_or_below_t_max"
        ]
        assert f"{p:.3f} {sex}" in joined
    assert "add a survivorship stock statistic" in " ".join(art["does_not_do"])
    assert "CERTIFICATION SCOPE" in art["proposed_thresholds_note"]
    assert "R8" in art["proposed_thresholds_note"]


def _resolve_artifact_path(art: dict, path: str) -> bool:
    """Does a dotted ``a.b[0].c`` path (``*`` = any key) exist in ``art``?"""
    nodes = [art]
    for token in re.findall(r"\[\d+\]|[^.\[\]]+", path):
        next_nodes = []
        for node in nodes:
            if token.startswith("["):
                index = int(token[1:-1])
                if isinstance(node, list) and index < len(node):
                    next_nodes.append(node[index])
            elif token == "*":
                if isinstance(node, dict):
                    next_nodes.extend(node.values())
            elif isinstance(node, dict) and token in node:
                next_nodes.append(node[token])
        nodes = next_nodes
        if not nodes:
            return False
    return True


def test_record_corrections_name_every_defect_and_point_at_live_paths():
    """The record of the 2026-09-07 sitting: every referee defect the
    brief listed, its fix, and where the fix lives -- and every named
    artifact path exists in these bytes (a path that does not resolve
    would be a fix claimed and not made)."""
    art = _artifact()
    record = art["record_corrections"]
    assert "2fbde39" in record["sitting"]
    assert "3daae3fe3ba767c5" in record["referees"]["A_statistical"]
    assert "0c8baddc9cddbbf5" in record["referees"]["B_contract_and_record"]
    assert "no floor value" in record["invariant"]
    assert "elapsed_seconds" in record["invariant"]
    defects = " ".join(item["defect"] for item in record["items"])
    for tag in (
        "B D-1",
        "B D-2",
        "B D-3",
        "B D-4",
        "B D-5",
        "B D-7",
        "B D-8",
        "B D-9",
        "A D1",
        "A D2",
        "A D3",
        "A D4",
        "A D5",
        "A D6",
        "A D7",
        "R8",
        "A findings (i), (ii), (iii)",
    ):
        assert tag in defects, tag
    assert len(record["items"]) == 13
    for item in record["items"]:
        assert set(item) == {"defect", "what", "fix", "where"}
        assert item["where"]
        for where in item["where"]:
            if where.startswith("tests/"):
                assert (ROOT / where.split(" ")[0]).is_file(), where
                continue
            assert _resolve_artifact_path(art, where), where


def test_reference_constants_are_pinned_to_literals():
    """The constants inherited from the v2 builder are pinned to literals
    in the v3 builder and in the artifact (referee A, D2), and the
    resolution guard's reach is stated."""
    builder = _import_builder()
    expected = {
        "DECLARED_UNIVERSE_START": 1997,
        "T_MAX": math.log(1.5),
        "MARGIN_K": 3,
        "FLOOR_SEEDS": "0-99",
        "N_SEEDS": 100,
        "NARROW_MAX_SPAN": 2,
    }
    assert builder.REFERENCE_CONSTANTS == expected
    builder.check_reference_constants()
    assert builder.DECLARED_UNIVERSE_START == 1997
    assert builder.T_MAX == pytest.approx(T_MAX)
    assert builder.MARGIN_K == 3
    assert tuple(builder.FLOOR_SEEDS) == tuple(range(100))
    assert builder.NARROW_MAX_SPAN == 2
    assert builder.CONVENTIONS == CONVENTIONS
    assert builder.UPPER_ENDS == UPPER_ENDS
    art = _artifact()
    pins = art["revision_pins"]["reference_constants"]
    assert set(pins) == set(expected)
    for key, value in expected.items():
        if isinstance(value, float):
            assert pins[key] == pytest.approx(value)
        else:
            assert pins[key] == value
    note = art["weight_universe"]["resolution_guard_note"]
    assert "NOT a change to panels.py" in note
    assert "committed table itself" in note


# --------------------------------------------------------------------------
# SYNTHETIC tier: the ascertainment convention on hand-made frames
# (no PSID; runs wherever the PSID-gated tests skip -- referee B, D-4)
# --------------------------------------------------------------------------
def _synthetic_death_records() -> pd.DataFrame:
    """Twelve persons covering every death-code class the rule meets."""
    rows = [
        # person, sex, status, lo, hi
        (1, "male", "range", 1999, 2001),  # span 2; seen 1997, 1999
        (2, "male", "range", 1999, 2001),  # span 2; last seen 1997
        (3, "female", "range", 1999, 2002),  # span 3 (wide)
        (4, "female", "range", 1998, 1999),  # span 1, lo off-grid
        (5, "male", "range", 1999, 2000),  # span 1; aged 20 (unbanded)
        (6, "female", "range", 2001, 2002),  # span 1; seen 2001
        (7, "male", "na_dk", None, None),  # NA-year; seen 2001
        (8, "female", "range", 2005, 2010),  # wide, not overlapping
        (9, "male", "na_dk", None, None),  # seen only at the terminal wave
        (10, "female", "range", 2000, 2004),  # wide, second year only
        (11, "male", "exact", 2002, 2002),  # exact death
        (12, "female", "not_deceased", None, None),
    ]
    return pd.DataFrame(
        {
            "person_id": pd.array([r[0] for r in rows], dtype="int64"),
            "sex": pd.array([r[1] for r in rows], dtype="string"),
            "death_status": pd.array([r[2] for r in rows], dtype="string"),
            "death_year": pd.array(
                [r[3] if r[2] == "exact" else None for r in rows],
                dtype="Int64",
            ),
            "death_year_lo": pd.array([r[3] for r in rows], dtype="Int64"),
            "death_year_hi": pd.array([r[4] for r in rows], dtype="Int64"),
        }
    )


def _synthetic_demo() -> pd.DataFrame:
    """Person-waves on a biennial grid 1997-2003 (2003 terminal)."""
    rows = [
        (1, 1997, 60),
        (1, 1999, 62),
        (2, 1997, 70),
        (3, 1997, 75),
        (3, 1999, 77),
        (4, 1997, 78),
        (5, 1999, 20),
        (6, 2001, 50),
        (6, 2003, 52),
        (7, 2001, 40),
        (8, 1999, 66),
        (9, 2003, 30),
        (10, 1999, 55),
        (11, 2001, 80),
        (12, 1997, 45),
        (12, 1999, 47),
        (12, 2001, 49),
        (12, 2003, 51),
    ]
    return pd.DataFrame(
        {
            "person_id": np.asarray([r[0] for r in rows], dtype=np.int64),
            "period": np.asarray([r[1] for r in rows], dtype=np.int64),
            "age": np.asarray([r[2] for r in rows], dtype=np.int64),
            "weight": np.ones(len(rows), dtype=np.float64),
        }
    )


def _deaths_by_person(slices: pd.DataFrame) -> dict[int, float]:
    return {
        int(p): float(d)
        for p, d in slices.groupby("person_id").death.sum().items()
        if d > 0
    }


def test_synthetic_assign_narrow_death_years_is_the_midpoint_rule():
    """span 1 -> lo; span 2 -> lo + 1; span >= 3, NA-year, exact and
    not-deceased records untouched; the flag marks exactly the narrow
    codes; the input frame is not mutated."""
    builder = _import_builder()
    dr = _synthetic_death_records()
    before = dr.copy()
    out = builder.assign_narrow_death_years(dr)
    pd.testing.assert_frame_equal(dr, before)
    assert builder.NARROW_MAX_SPAN == 2
    year = dict(zip(out.person_id, out.death_year, strict=True))
    flag = dict(zip(out.person_id, out.assigned_by_pinned_rule, strict=True))
    assert year[1] == 2000 and flag[1]  # (1999 + 2001) // 2
    assert year[2] == 2000 and flag[2]
    assert pd.isna(year[3]) and not flag[3]  # wide
    assert year[4] == 1998 and flag[4]  # (1998 + 1999) // 2 = lo
    assert year[5] == 1999 and flag[5]
    assert year[6] == 2001 and flag[6]
    assert pd.isna(year[7]) and not flag[7]  # NA-year
    assert pd.isna(year[8]) and not flag[8]  # wide
    assert pd.isna(year[10]) and not flag[10]  # wide
    assert year[11] == 2002 and not flag[11]  # exact untouched
    assert pd.isna(year[12]) and not flag[12]
    assert int(out.assigned_by_pinned_rule.sum()) == 5


def test_synthetic_pinned_rule_end_to_end_and_its_tie_break():
    """Through the v1 exposure machinery unchanged: a narrow code is
    counted iff the person was observed at the start of the grid
    interval containing the midpoint AND the slice age there is banded;
    assigning at lo / hi instead is the within-rule sensitivity."""
    builder = _import_builder()
    demo, dr = _synthetic_demo(), _synthetic_death_records()
    survival = builder.v1b.build_exposure_slices(demo, dr)
    assert _deaths_by_person(survival) == {11: 1.0}  # exact only
    pinned = builder.v1b.build_exposure_slices(
        demo, builder.assign_narrow_death_years(dr)
    )
    # 1: midpoint 2000 in [1999, 2001), observed at 1999, aged 63 there.
    # 4: midpoint 1998 in [1997, 1999), observed at 1997, aged 79 there.
    # 6: midpoint 2001 in [2001, 2003), observed at 2001, aged 50.
    # 2: midpoint 2000, last observed 1997 -> never scored.
    # 5: midpoint 1999, observed at 1999 but aged 20 -> unbanded.
    assert _deaths_by_person(pinned) == {1: 1.0, 4: 1.0, 6: 1.0, 11: 1.0}
    # Person 6 dies in the FIRST year of a biennial interval, so the v1
    # machinery emits no second slice for them: one slice fewer than the
    # survival frame. (In the real data every added death lands in a
    # one-year interval or a second year, which is why n_slices is equal
    # there -- pinned_rule_effect.n_slices_survival == n_slices_pinned.)
    assert len(pinned) == len(survival) - 1
    assert survival[survival.person_id == 6].age.tolist() == [
        50,
        51,
    ] and pinned[pinned.person_id == 6].age.tolist() == [50]
    death_rows = pinned[pinned.death > 0].set_index("person_id")
    assert (
        death_rows.loc[1, "age"] == 63 and death_rows.loc[1, "exposure"] == 0.5
    )
    assert (
        death_rows.loc[4, "age"] == 79 and death_rows.loc[4, "exposure"] == 0.5
    )
    assert (
        death_rows.loc[6, "age"] == 50 and death_rows.loc[6, "exposure"] == 0.5
    )
    # Person 1's second interval: the year-1999 slice keeps full exposure.
    p1 = pinned[(pinned.person_id == 1) & (pinned.start_wave == 1999)]
    assert sorted(p1.age.tolist()) == [62, 63]
    assert p1[p1.age == 62].exposure.item() == 1.0
    # Tie-break: at hi, 1 and 4 fall outside their interval and drop out;
    # at lo, the same three are counted (1 moves to its year-1999 slice).
    for column, expected in (
        ("death_year_hi", {6: 1.0, 11: 1.0}),
        ("death_year_lo", {1: 1.0, 4: 1.0, 6: 1.0, 11: 1.0}),
    ):
        alt = dr.copy()
        span = (alt.death_year_hi - alt.death_year_lo).astype("float")
        narrow = (alt.death_status == "range") & (span <= 2)
        alt.loc[narrow, "death_year"] = alt.loc[narrow, column].astype("Int64")
        got = builder.v1b.build_exposure_slices(demo, alt)
        assert _deaths_by_person(got) == expected, column
    # The 49 -> 44 decomposition machinery on the synthetic frame.
    grid, next_wave = builder._grid(demo)
    obs = builder._observed_frame(demo, dr)
    last = builder.last_observed(obs, next_wave)
    classification = builder.death_record_classification(
        dr, obs, last, grid, next_wave, counted_person_ids={1, 4, 6, 11}
    )
    assert classification["narrow"]["n"] == 5
    assert classification["wide"]["n"] == 3
    assert classification["narrow"]["observed_at_lo"] == 3  # 1, 5, 6
    d = classification["narrow_counted_decomposition"]
    assert d["observed_at_grid_wave_containing_midpoint"] == 4  # 1, 4, 5, 6
    assert d["of_which_banded_at_midpoint_age"] == 3
    assert d["counted_in_pinned_frame"] == 3
    assert d["observed_at_lo_and_counted"] == 2  # 1, 6
    assert d["observed_at_lo_not_counted"] == 1  # 5
    assert d["observed_at_lo_not_counted_ages_at_midpoint"] == [20]
    assert d["counted_not_observed_at_lo"] == 1  # 4, lo 1998 off-grid
    assert d["counted_not_observed_at_lo_persons"][0]["person_id"] == 4
    assert d["counted_not_observed_at_lo_persons"][0]["lo_is_grid_wave"] is (
        False
    )
    assert d["last_wave_before_lo"] == 2  # 2 and 4
    assert d["last_wave_before_lo_and_counted"] == 1  # 4
    assert d["last_wave_before_lo_never_scored"] == 1  # 2
    # A counted set that violates the rule is refused, not recorded.
    with pytest.raises(RuntimeError):
        builder.death_record_classification(
            dr, obs, last, grid, next_wave, counted_person_ids={1, 2, 6, 11}
        )


def test_synthetic_band_end_target_sets():
    """Which decedents each upper end scores: the informed end respects
    ranges, the residue-literal end ignores them but excludes every
    narrow-assigned decedent, the truly literal end excludes only the
    narrow decedents the pinned rule COUNTS. A person with no following
    grid wave is never a target."""
    builder = _import_builder()
    demo, dr = _synthetic_demo(), _synthetic_death_records()
    grid, next_wave = builder._grid(demo)
    obs = builder._observed_frame(demo, dr)
    last = builder.last_observed(obs, next_wave)
    dr_pinned = builder.assign_narrow_death_years(dr)
    assigned = dr_pinned.set_index("person_id")["assigned_by_pinned_rule"]
    counted = {1, 4, 6}
    assigned_and_counted = pd.Series(
        assigned.to_numpy() & assigned.index.isin(counted),
        index=assigned.index,
    )
    informed = builder.fractional_death_targets(
        dr, last, next_wave, respect_ranges=True, exclude_assigned=assigned
    )
    residue = builder.fractional_death_targets(
        dr, last, next_wave, respect_ranges=False, exclude_assigned=assigned
    )
    truly = builder.fractional_death_targets(
        dr,
        last,
        next_wave,
        respect_ranges=False,
        exclude_assigned=assigned_and_counted,
    )
    assert sorted(informed.person_id) == [3, 7, 10]
    assert sorted(residue.person_id) == [3, 7, 8, 10]
    assert sorted(truly.person_id) == [2, 3, 5, 7, 8, 10]
    # 9 (terminal wave only) and 11 (exact), 12 (alive) never appear.
    by_person = informed.set_index("person_id")
    assert by_person.loc[
        3, ["feasible_first_year", "feasible_second_year"]
    ].tolist() == [True, True]
    assert by_person.loc[
        7, ["feasible_first_year", "feasible_second_year"]
    ].tolist() == [True, True]
    # 10's range 2000-2004 meets [1999, 2001) in 2000 only.
    assert by_person.loc[
        10, ["feasible_first_year", "feasible_second_year"]
    ].tolist() == [False, True]
    assert by_person.loc[3, "range_span"] == 3
    assert pd.isna(by_person.loc[7, "range_span"])
    assert residue.set_index("person_id").loc[
        8, ["feasible_first_year", "feasible_second_year"]
    ].tolist() == [True, True]
    truly_by = truly.set_index("person_id")
    assert (
        truly_by.loc[2, "start_wave"] == 1997
        and truly_by.loc[2, "next_wave"] == 1999
    )
    assert truly_by.loc[5, "age_at_start"] == 20
    assert truly_by.loc[2, "range_span"] == 2


def test_synthetic_apply_fractional_deaths_expected_value_identities():
    """E[exposure_1] = 1 - r*p0/2; E[exposure_2] = 1 - r*p0 - r*p1/2;
    E[death_j] = r*p_j; a fully feasible target adds exactly r expected
    deaths; a target feasible in the second year only adds r there and
    leaves the first slice whole; on a one-year interval p0 = 1."""
    builder = _import_builder()
    demo, dr = _synthetic_demo(), _synthetic_death_records()
    grid, next_wave = builder._grid(demo)
    obs = builder._observed_frame(demo, dr)
    last = builder.last_observed(obs, next_wave)
    dr_pinned = builder.assign_narrow_death_years(dr)
    pinned = builder.v1b.build_exposure_slices(demo, dr_pinned)
    assigned = dr_pinned.set_index("person_id")["assigned_by_pinned_rule"]
    targets = builder.fractional_death_targets(
        dr, last, next_wave, respect_ranges=True, exclude_assigned=assigned
    )
    r, p2 = 0.6, 0.65
    out = builder.apply_fractional_deaths(pinned, targets, r, p2)
    assert len(out) == len(pinned)
    untouched = ~out.person_id.isin(targets.person_id)
    pd.testing.assert_frame_equal(out[untouched], pinned[untouched])
    assert float(out.death.sum() - pinned.death.sum()) == pytest.approx(
        r * len(targets)
    )
    p0, p1 = 1.0 - p2, p2
    for person, first_age in ((3, 77), (7, 40)):
        rows = out[out.person_id == person].set_index("age")
        assert rows.loc[first_age, "exposure"] == pytest.approx(
            1 - 0.5 * r * p0
        )
        assert rows.loc[first_age, "death"] == pytest.approx(r * p0)
        assert rows.loc[first_age + 1, "exposure"] == pytest.approx(
            1 - r * p0 - 0.5 * r * p1
        )
        assert rows.loc[first_age + 1, "death"] == pytest.approx(r * p1)
    rows = out[out.person_id == 10].set_index("age")  # second year only
    assert rows.loc[55, "exposure"] == 1.0 and rows.loc[55, "death"] == 0.0
    assert rows.loc[56, "exposure"] == pytest.approx(1 - 0.5 * r)
    assert rows.loc[56, "death"] == pytest.approx(r)
    # One-year interval: a single feasible slice, p0 = 1.
    # Person 21 is last seen at 1990 (person 22 carries the 1991 wave, so
    # 1990 has a successor): interval [1990, 1991), one feasible year.
    demo1 = pd.DataFrame(
        {
            "person_id": np.asarray([21, 22, 22], dtype=np.int64),
            "period": np.asarray([1990, 1990, 1991], dtype=np.int64),
            "age": np.asarray([60, 40, 41], dtype=np.int64),
            "weight": np.ones(3),
        }
    )
    dr1 = pd.DataFrame(
        {
            "person_id": pd.array([21, 22], dtype="int64"),
            "sex": pd.array(["female", "male"], dtype="string"),
            "death_status": pd.array(
                ["na_dk", "not_deceased"], dtype="string"
            ),
            "death_year": pd.array([None, None], dtype="Int64"),
            "death_year_lo": pd.array([None, None], dtype="Int64"),
            "death_year_hi": pd.array([None, None], dtype="Int64"),
        }
    )
    grid1, next1 = builder._grid(demo1)
    obs1 = builder._observed_frame(demo1, dr1)
    last1 = builder.last_observed(obs1, next1)
    base1 = builder.v1b.build_exposure_slices(demo1, dr1)
    targets1 = builder.fractional_death_targets(
        dr1,
        last1,
        next1,
        respect_ranges=True,
        exclude_assigned=pd.Series(False, index=dr1.person_id),
    )
    assert sorted(targets1.person_id) == [21]  # last wave 1990 -> [1990, 1991)
    out1 = builder.apply_fractional_deaths(base1, targets1, r, p2)
    row = out1[out1.person_id == 21].set_index("age")
    assert row.loc[60, "exposure"] == pytest.approx(1 - 0.5 * r)
    assert row.loc[60, "death"] == pytest.approx(r)


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
    truly_dt = declared["max_abs_delta_tolerance_k3_vs_pinned"][TRULY_LITERAL]
    assert f"more than {truly_dt:.3f} over the pinned convention" in note
    assert "three upper ends" in note
    assert "interval start waves 1997-2021" in note
    assert "1997-2023" not in note
    assert "measured on the survival frame" in note
    assert "CARRIED FINDINGS" in note
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
def test_convention_frames_and_seeds_reproduce_without_populace_fit():
    """The five frames, the classification (with the 49 -> 44 link), the
    rates, the three band ends' targets, ALL 100 seeds of the headline
    block and seeds 0, 37, 99 of every other block reproduce from PSID
    (referee A D1: 97 of 100 seeds were pinned by internal consistency
    only). ``populace.fit`` is never imported."""
    assert "populace.fit" not in sys.modules
    builder = _import_builder()
    assert (
        "populace.fit" not in sys.modules
    ), "importing the v3 mortality builder pulled populace.fit"
    real = _real(builder)
    frames, detail = real["frames"], real["detail"]
    art = _artifact()
    da = art["death_ascertainment"]
    assert set(frames) == set(CONVENTIONS)

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
    for name, key in (
        (INFORMED, "upper_end_informed"),
        (RESIDUE_LITERAL, "upper_end_packet_literal"),
        (TRULY_LITERAL, "upper_end_truly_literal"),
    ):
        _assert_close(
            detail["upper_band_targets"][name], band[key]["targets"], key
        )
    _assert_close(
        detail["in_frame_non_exact_accounting"],
        band["upper_end_truly_literal"]["in_frame_non_exact_accounting"],
    )
    _assert_close(detail["grid"], da["grid"])

    # The headline block (pinned, declared): ALL 100 seeds, cell by
    # cell and both per-half hazard vectors.
    pinned = frames[PINNED]
    head = _block(art, PINNED, "declared_1997_plus")["per_seed"]
    assert [s["seed"] for s in head] == list(range(100))
    for ref in head:
        got = builder.measure_seed(
            ref["seed"], pinned, start_year_min=1997, full=True
        )
        assert got["n_persons_side_a"] == ref["n_persons_side_a"]
        assert got["n_persons_side_b"] == ref["n_persons_side_b"]
        _assert_close(got["cells"], ref["cells"], f"seed{ref['seed']}")
        _assert_close(got["hazards_side_a"], ref["hazards_side_a"])
        _assert_close(got["hazards_side_b"], ref["hazards_side_b"])
    # The pinned all-window block: spot seeds, compact shape.
    for seed in SPOT_SEEDS:
        got = builder.measure_seed(
            seed, pinned, start_year_min=None, full=False
        )
        ref = _block(art, PINNED, "all_v1_comparable")["per_seed"][seed]
        assert ref["seed"] == seed
        assert got["n_persons_side_a"] == ref["n_persons_side_a"]
        assert got["n_persons_side_b"] == ref["n_persons_side_b"]
        _assert_close(got["cells"], ref["cells"], f"all seed{seed}")
    # The survival blocks: spot seeds through v2's own measure_seed
    # against v2's committed per-seed records (the code-path tie).
    v2_universes = _v2()["internal_noise_floor"]["universes"]
    for universe, start in (
        ("declared_1997_plus", 1997),
        ("all_v1_comparable", None),
    ):
        for seed in SPOT_SEEDS:
            got = builder.v2b.measure_seed(
                seed, frames[SURVIVAL], start_year_min=start
            )
            ref = v2_universes[universe]["per_seed"][seed]
            assert ref["seed"] == seed
            _assert_close(got["cells"], ref["cells"], f"{universe} seed{seed}")
    # The three upper ends carry no per-seed records; their committed
    # floor VALUES are reproduced at the spot seeds on both universes.
    for name in UPPER_ENDS:
        for universe, start in (
            ("declared_1997_plus", 1997),
            ("all_v1_comparable", None),
        ):
            floors = _block(art, name, universe)["noise_floor_seeds_0_99"]
            for seed in SPOT_SEEDS:
                got = builder.measure_seed(
                    seed, frames[name], start_year_min=start, full=False
                )
                for key, floor in floors.items():
                    assert got["cells"][key]["log_ratio_abs"] == pytest.approx(
                        floor["values"][seed], rel=1e-9, abs=1e-12
                    ), (name, universe, seed, key)

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
    # The same shares on the pinned frame (referee A D4): the frame each
    # R1 figure is on is stated and both are committed.
    assert wu["measured_on_frame"]["frame"] == SURVIVAL
    _assert_close(
        builder.per_cell_series_shares(real["frames"][PINNED], series_by_wave),
        wu["per_cell_shares_pinned_convention"],
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
