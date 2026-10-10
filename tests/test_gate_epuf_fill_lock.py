"""Bind gate_epuf_fill's locked gates.yaml block to its ratified draft.

The lock flip (decision d927, ratified by Max on 2026-10-10) adds the block
in ``docs/design/gate_epuf_fill_block_draft.yaml`` to ``gates.yaml`` with
exactly the lock-time deltas its history lists. These tests check that the
block is that draft, that every pinned file still hashes to its pin, that
the registered constants agree with the block, and that the lock is what
``epuf_fill_gate.test_part`` reads. Nothing here reads TEST.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness import epuf_fill_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / "gates.yaml"
DRAFT = ROOT / "docs" / "design" / "gate_epuf_fill_block_draft.yaml"


def _block() -> dict:
    return yaml.safe_load(GATES.read_text())["gates"]["gate_epuf_fill"]


def _sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_the_block_is_the_draft_with_only_the_lock_time_deltas():
    block = _block()
    draft = yaml.safe_load(DRAFT.read_text())["gate_epuf_fill"]
    expected = copy.deepcopy(draft)
    expected["status"] = "locked"
    expected["locked"] = True
    expected["thresholds"]["locked"] = True
    expected["test_scoring_sha256"] = block["test_scoring_sha256"]
    expected["ceremony_record"]["ratification"] = block["ceremony_record"][
        "ratification"
    ]
    expected["history"] = block["history"]
    assert block == expected
    assert block["ceremony_record"]["ratification"].startswith(
        "decision d927, ruled by Max 2026-10-10"
    )
    (entry,) = block["history"]
    assert entry["id"] == "2026-10-10-epuf-fill-gate-lock"
    assert entry["ratified"] == "2026-10-10"


def test_the_lock_is_what_test_part_reads():
    status = g._gate_lock_status(GATES)
    assert status == {"locked": True, "registration_id": g.REGISTRATION_ID}
    assert _block()["registration_id"] == g.REGISTRATION_ID


def test_every_pinned_file_hashes_to_its_pin():
    block = _block()
    assert _sha256(block["floor_run"]) == block["floor_run_sha256"]
    assert _sha256(block["psid_scale"]) == block["psid_scale_sha256"]
    assert _sha256(block["test_scoring"]) == block["test_scoring_sha256"]
    # The TEST entry point loads the same floor build the block pins.
    assert block["floor_run_sha256"] == scoring.REGISTERED_FLOORS_SHA256
    assert ROOT / block["floor_run"] == scoring.REGISTERED_FLOORS
    assert block["rules"] == "src/populace_dynamics/harness/epuf_fill_gate.py"


def test_the_block_states_the_registered_constants():
    block = _block()
    thresholds = block["thresholds"]
    assert thresholds["k_tolerance"] == g.K_TOLERANCE == 1.0
    floors = json.loads((ROOT / block["floor_run"]).read_text())
    reasons = list(floors["partition"].values())
    assert thresholds["gating_cells"] == reasons.count("gates") == 319
    assert (
        thresholds["report_only_cells"]
        == len(reasons) - reasons.count("gates")
        == 7
    )
    assert "3 tau" in thresholds["adoption"] and g.IMPROVES_CAP == 3.0
    assert block["floor_build_commit"] == floors["code_commit"][:8]
