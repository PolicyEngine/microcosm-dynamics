"""B1 v2's record parsing, using invented artifact and sidecar contents.

No committed result cells, external parameter data or PSID are read, and
no real replay is run. The fixtures exercise the full 600-cell registration
shape, all lineage fields and provenance records. Source history checks
read code bytes only.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.track_b import reconstructed, runner
from tests.test_track_b_reconstructed import (
    FREEZE,
    LINEAGE_EXTRA,
    PROVENANCE,
    RUNTIME_IDENTITY,
    _invented_cell_values,
    _registered_baseline,
)

ROOT = Path(__file__).resolve().parents[1]
PASSING_ANCHOR = {
    "loader_revision": "f10cca5",
    "head": runner.BASELINE_COMMIT,
    "tracked_clean": True,
    "git_environment": {},
}


@pytest.fixture(scope="module")
def invented_records():
    artifact = {
        **_registered_baseline(_invented_cell_values()),
        "protocol": {
            "gate_seeds": list(runner.REGISTERED_SEEDS),
            "draw_index": list(runner.REGISTERED_DRAWS),
        },
        "lineage": {
            **{name: f"invented-{name}" for name in runner.FIT_SIGNATURE_KEYS},
            **LINEAGE_EXTRA,
        },
        "provenance": PROVENANCE,
        "runtime_identity": RUNTIME_IDENTITY,
    }
    sidecar = {
        "environment": {
            "candidate3_gate_freeze": {
                **FREEZE,
                "populace_frame": {"version": "invented"},
            }
        }
    }
    # Exercise the same JSON decode boundary as committed evidence.
    return tuple(
        json.loads(runner.json_bytes(record)) for record in (artifact, sidecar)
    )


def _has_commit(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


def test_artifact_parser_holds_exactly_600_float_cells(invented_records):
    artifact, _ = invented_records
    assert tuple(artifact["protocol"]["gate_seeds"]) == runner.REGISTERED_SEEDS
    assert tuple(artifact["protocol"]["draw_index"]) == runner.REGISTERED_DRAWS
    registered, problems = reconstructed.registered_cells(
        artifact, seeds=runner.REGISTERED_SEEDS, draws=runner.REGISTERED_DRAWS
    )
    assert problems == []
    assert len(registered) == 600
    assert all(type(value) is float for value in registered.values())
    result = reconstructed.compare_cells(
        registered,
        {side: dict(registered) for side in reconstructed.SIDES},
        seeds=runner.REGISTERED_SEEDS,
        draws=runner.REGISTERED_DRAWS,
    )
    assert result["equal"] is True
    assert result["compared_cells"] == 600


def test_all_provenance_records_satisfy_the_anchor_rule(invented_records):
    artifact, sidecar = invented_records
    registered = reconstructed.registered_provenance(artifact, sidecar)
    assert set(registered) == set(reconstructed.PROVENANCE_RECORDS)
    assert all(
        isinstance(record, dict) and record for record in registered.values()
    )
    assert (
        registered["provenance"]["external_details"]["ssa_revision"]
        == reconstructed.REGISTERED_SSA_REVISION
    )
    assert runner.BASELINE_COMMIT.startswith(
        reconstructed.REGISTERED_SSA_REVISION
    )
    assert set(registered["runtime_identity"]) == set(
        reconstructed.RUNTIME_IDENTITY_KEYS
    )
    freeze = registered["candidate3_gate_freeze"]
    assert set(freeze) == {
        "runtime",
        "thread_environment",
        "omp_wait_policy",
        "populace_fit",
        "populace_frame",
    }
    for key in reconstructed.RUNTIME_IDENTITY_KEYS:
        assert registered["runtime_identity"][key] == freeze["runtime"][key]
    assert reconstructed.anchor_problems(PASSING_ANCHOR, registered) == []
    result = reconstructed.compare_provenance(
        registered, copy.deepcopy(registered), PASSING_ANCHOR
    )
    assert result["equal"] is True


def test_lineage_preserves_refit_fields_and_floor_binding(
    invented_records,
):
    artifact, _ = invented_records
    lineage = artifact["lineage"]
    assert set(runner.FIT_SIGNATURE_KEYS) <= set(lineage)
    assert {"floor_run", "floor_sha256"} <= set(lineage)
    assert reconstructed.compare_lineage(lineage, copy.deepcopy(lineage))[
        "equal"
    ]
    for field in (*runner.FIT_SIGNATURE_KEYS, "floor_run", "floor_sha256"):
        changed = copy.deepcopy(lineage)
        changed[field] = f"changed-{field}"
        result = reconstructed.compare_lineage(lineage, changed)
        assert result["equal"] is False
        assert [item["path"] for item in result["differences"]] == [
            ["lineage", field]
        ]


def test_v2_extra_sources_are_unchanged_since_the_inherited_commit():
    assert not set(reconstructed.RECONSTRUCTED_SOURCES) & set(
        runner.BASELINE_SOURCES
    )
    if not _has_commit(runner.BASELINE_COMMIT):
        pytest.skip("this clone's history lacks the inherited commit")
    for name in reconstructed.RECONSTRUCTED_SOURCES:
        original = subprocess.run(
            ["git", "show", f"{runner.BASELINE_COMMIT}:{name}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert (ROOT / name).read_bytes() == original
