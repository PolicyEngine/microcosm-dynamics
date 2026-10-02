"""Bind the EPUF gate's draft block to its committed floor artifact.

Every tolerance, interval, partition and pass probability in
``docs/design/gate_epuf_block_draft.yaml`` is recomputed here from the
floor replicates stored in ``runs/epuf_gate_floors_v1.json`` with the
registered algebra (``populace_dynamics.harness.epuf_gate``), and the
block must equal a fresh render of the artifact. The derivation files
must still hash to the values the artifact recorded when it was built.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest
import yaml
from scipy.stats import norm

from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import cell_ids, transform

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "epuf_gate_floors_v1.json"
FIRST_BUILD = ROOT / "runs" / "epuf_gate_floors_v1_first_build.json"
SUPPLEMENT = ROOT / "runs" / "epuf_gate_supplement_v1.json"
BLOCK = ROOT / "docs" / "design" / "gate_epuf_block_draft.yaml"
GATES = ROOT / "gates.yaml"


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _block() -> dict:
    return yaml.safe_load(BLOCK.read_text(encoding="utf-8"))["gates"][
        "gate_epuf"
    ]


def _render():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "render_gate_epuf_block_draft",
        ROOT / "scripts" / "render_gate_epuf_block_draft.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render()


def test_block_is_the_render_of_the_committed_artifact():
    assert BLOCK.read_text(encoding="utf-8") == _render()
    block = _block()
    assert (
        block["floor_run_sha256"]
        == hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    )


def test_block_is_unlocked_gates_nothing_and_gates_yaml_is_untouched():
    block = _block()
    artifact = _artifact()
    assert block["locked"] is False
    assert block["status"] == "unlocked_report_only"
    assert block["gated_cells"] == {}
    assert block["lock_ceremony"]["exists"] is False
    assert block["ceremony_pause"] == artifact["ceremony_pause"] is True
    assert block["referee_round_1"]["verdict"].startswith("AMEND")
    assert (ROOT / block["referee_round_1"]["report"]).is_file()
    gates = yaml.safe_load(GATES.read_text(encoding="utf-8"))["gates"]
    assert "gate_epuf" not in gates
    assert "gate_epuf" not in GATES.read_text(encoding="utf-8")
    assert artifact["ceremony"]["gates_yaml_untouched"] is True


def test_block_names_the_rules_commit_and_the_build_commit_separately():
    block = _block()
    artifact = _artifact()
    assert block["floor_build_commit"] == (
        artifact["revision_pins"]["head_sha"]
    )
    assert block["rules_commit"] == (
        "eec910d61a7e0afe21995957740e03d64acdffdc"
    )
    assert block["rules_commit"] != block["floor_build_commit"]
    first = json.loads(FIRST_BUILD.read_text(encoding="utf-8"))
    assert first["revision_pins"]["head_sha"] == block["rules_commit"]


def test_scoring_path_is_pinned():
    block = _block()
    module = block["scoring_path"]["module"]
    assert module == "src/populace_dynamics/harness/epuf_run.py"
    observed = hashlib.sha256((ROOT / module).read_bytes()).hexdigest()
    assert observed == block["scoring_path"]["sha256"]


def test_first_build_is_frozen_lineage_with_equal_window_results():
    first_bytes = FIRST_BUILD.read_bytes()
    assert hashlib.sha256(first_bytes).hexdigest() == (
        "369bf5ec4e62c0eaa2f70702a9173188c87e84a5544bb4470826781c1847e378"
    )
    assert _block()["first_floor_build"]["sha256"] == (
        hashlib.sha256(first_bytes).hexdigest()
    )
    first = json.loads(first_bytes)
    rebuilt = _artifact()
    for key in (
        "cells",
        "gate_partition",
        "registered",
        "faithful_candidate_oc",
        "training_copy",
        "real_gate_seed_values",
        "bite_demonstrations",
        "holdout_ids",
        "epuf_support",
        "ceremony_pause",
        "design",
    ):
        assert first[key] == rebuilt[key], key
    # Only the report-only career tranche differs (the AIME fix).
    assert (
        first["tranche_r_epuf_reference"]
        != rebuilt["tranche_r_epuf_reference"]
    )


def test_supplement_belongs_to_the_floor_run_and_matches_its_bites():
    supplement = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
    artifact = _artifact()
    assert supplement["floor_run_sha256"] == (
        hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    )
    assert _block()["supplement"]["sha256"] == (
        hashlib.sha256(SUPPLEMENT.read_bytes()).hexdigest()
    )
    assert supplement["candidate_blind"]["generated_candidates"] == 0
    bites = supplement["bites"]
    for name, row in artifact["bite_demonstrations"].items():
        if name in ("requirements", "pause"):
            continue
        assert bites[name]["fail_share_reproduced"] == row["fail_share"]
        for cell_id, cell in bites[name]["cells"].items():
            estimates = cell["estimates_over_perturbation_seeds"]
            assert len(estimates) == 50
            assert cell["mean_shift"] == pytest.approx(
                sum(estimates) / len(estimates)
                - cell["real_gate_holdout_estimate"]
            )
            floor = artifact["cells"][cell_id]
            centre = floor["bridge_psid_minus_epuf"] + cell["mean_shift"]
            sigma = floor["floor"]["realized_sigma"]
            expected = norm.cdf((floor["lower"] - centre) / sigma) + norm.sf(
                (floor["upper"] - centre) / sigma
            )
            assert cell["power_under_gate_noise_model"] == pytest.approx(
                expected
            )
    for cell_id, point in bites["detection_points"].items():
        floor = artifact["cells"][cell_id]
        sigma = floor["floor"]["realized_sigma"]
        distance = floor["bridge_psid_minus_epuf"] - floor["lower"]
        assert point["shortfall_failing_90_percent"] == pytest.approx(
            distance + 1.2816 * sigma
        )
        # The registered 10 percent persistence bite sits below the 90
        # percent detection point: the pause was foreseeable.
        shift = bites["bd1_persistence_loss_0.10"]["cells"][cell_id][
            "mean_shift"
        ]
        assert -shift < point["shortfall_failing_90_percent"]


def test_derivation_files_are_the_ones_the_floor_was_built_with():
    recorded = _artifact()["revision_pins"]["derivation_core_sha256"]
    assert set(recorded) == {
        "src/populace_dynamics/data/epuf.py",
        "src/populace_dynamics/harness/epuf_operator.py",
        "src/populace_dynamics/harness/epuf_cells.py",
        "src/populace_dynamics/harness/epuf_gate.py",
        "scripts/build_epuf_gate_floors.py",
    }
    for path, digest in recorded.items():
        observed = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert observed == digest, path


def test_every_cell_is_derived_by_the_registered_algebra():
    artifact = _artifact()
    assert sorted(artifact["cells"]) == sorted(cell_ids())
    reasons = {}
    for cell_id, cell in artifact["cells"].items():
        replicates = cell["floor"]["replicates"]
        assert len(replicates) == gate.N_FLOOR_REPLICATES
        defined = None not in replicates and cell["psid_value"] is not None
        if not defined:
            reasons[cell_id] = "undefined_on_some_split"
            assert cell["eligibility"] == "undefined_on_some_split"
            continue
        t = gate.tolerance(replicates)
        sigma = gate.realized_sigma(replicates)
        bridge = transform(cell_id, cell["psid_value"]) - transform(
            cell_id, cell["epuf_value"]
        )
        assert cell["floor"]["tolerance"] == t
        assert cell["floor"]["realized_sigma"] == pytest.approx(sigma)
        assert cell["bridge_psid_minus_epuf"] == pytest.approx(bridge)
        assert (cell["lower"], cell["upper"]) == gate.hull(bridge, t)
        assert cell["faithful_pass_probability"] == pytest.approx(
            gate.faithful_pass_probability(
                bridge, sigma, cell["lower"], cell["upper"]
            )
        )
        reason = gate.demotion_reason(
            gate.CellFloor(
                cell_id,
                True,
                cell["min_events"],
                bridge,
                t,
                sigma,
                cell["epuf_sampling_sd"],
            )
        )
        reasons[cell_id] = reason
        assert cell["eligibility"] == (reason or "eligible")
    gated, report = gate.adopt_ladder(reasons)
    partition = artifact["gate_partition"]
    assert partition["gated"] == gated
    assert partition["report_only"] == report


def test_block_carries_the_artifact_partition_and_numbers():
    artifact = _artifact()
    block = _block()
    partition = artifact["gate_partition"]
    selected = block["selected_by_registered_rules"]
    assert list(selected) == partition["gated"]
    expected_report = {
        cell_id: "not_locked_referee_round_1" for cell_id in partition["gated"]
    }
    expected_report.update(partition["report_only"])
    assert block["report_only"] == expected_report
    assert set(block["report_only"]) == set(cell_ids())
    for cell_id, row in selected.items():
        cell = artifact["cells"][cell_id]
        assert row["lower"] == cell["lower"]
        assert row["upper"] == cell["upper"]
        assert row["tolerance"] == cell["floor"]["tolerance"]
        assert max(abs(row["lower"]), abs(row["upper"])) <= cell["cap"]
        assert cell["minimum_detectable_gap_80"] <= cell["cap"]
    assert set(artifact["registered"]) == set(partition["gated"])


def test_operating_characteristic_and_pauses():
    artifact = _artifact()
    oc = artifact["faithful_candidate_oc"]
    gated = artifact["gate_partition"]["gated"]
    product = math.prod(
        artifact["cells"][cell_id]["faithful_pass_probability"]
        for cell_id in gated
    )
    assert oc["analytic_product"] == pytest.approx(product if gated else 1.0)
    assert oc["pause"] == (bool(gated) and product < gate.OC_PAUSE)
    bites = artifact["bite_demonstrations"]
    assert bites["pause"] == any(
        not row["met"] for row in bites["requirements"].values()
    )
    assert artifact["ceremony_pause"] == (oc["pause"] or bites["pause"])


def test_real_gate_holdouts_pass_as_their_own_training_copy():
    artifact = _artifact()
    if artifact["gate_partition"]["gated"]:
        assert artifact["training_copy"]["pass"] is True


def test_the_floor_generated_no_candidate():
    artifact = _artifact()
    assert artifact["candidate_blind"]["generated_candidates"] == 0
    source = (ROOT / "scripts" / "build_epuf_gate_floors.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("run_gate1_candidate", "populace.fit", "generate_"):
        assert forbidden not in source


def test_gate_holdouts_are_gate_ones():
    artifact = _artifact()
    gate1 = json.loads(
        (ROOT / "runs" / "gate1_rank_knn_v5.json").read_text(encoding="utf-8")
    )
    holdouts = artifact["holdout_ids"]
    assert sorted(holdouts, key=int) == [str(s) for s in gate.GATE_SEEDS]
    for row in gate1["per_seed"]:
        assert holdouts[str(row["seed"])]["n_persons"] == row["n_persons"]
