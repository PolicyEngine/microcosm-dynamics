"""Invented-input B1 orchestration, evidence, and exclusive-write checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from populace_dynamics.engine.support import StartWaveWeightSnapshot
from populace_dynamics.track_b import runner
from tests.test_track_b_replay import _inputs


@pytest.fixture
def repository(tmp_path):
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    return tmp_path


def _baseline_protocol(root: Path) -> dict:
    baseline = {
        "protocol": {
            "gate_seeds": list(runner.REGISTERED_SEEDS),
            "draw_index": list(runner.REGISTERED_DRAWS),
            "draw_seeds": list(range(5200, 5220)),
        }
    }
    destination = root / runner.BASELINE_PATH
    destination.parent.mkdir()
    destination.write_bytes(runner.json_bytes(baseline))
    return baseline


def _execute(root, operation):
    return runner.execute(
        root=root,
        registration_id="9999999999",
        expected_commit="b" * 40,
        operation=operation,
    )


def test_source_failure_records_complete_abort_without_loading_inputs(
    repository, monkeypatch
):
    calls = []

    def source_failure(*args):
        raise ValueError("invented source mismatch")

    monkeypatch.setattr(runner, "source_guard", source_failure)
    result = _execute(repository, lambda *args: calls.append(args))

    assert calls == []
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert result["abort"]["type"] == "ValueError"
    assert result["abort"]["message"] == "invented source mismatch"
    assert "source_failure" in result["abort"]["traceback"]
    assert (
        json.loads(
            (repository / runner.DEFAULT_OUTPUT / "result.json").read_text()
        )
        == result
    )


def test_computation_failure_preserves_partial_evidence_and_traceback(
    repository, monkeypatch
):
    baseline = _baseline_protocol(repository)
    monkeypatch.setattr(
        runner, "source_guard", lambda *args: {"commit": "b" * 40}
    )

    def operation(root, output, supplied_baseline):
        assert root == repository
        assert supplied_baseline == baseline
        runner._write_new(output / "partial.json", {"seed": 0, "draw": 0})
        raise RuntimeError("invented draw failure")

    result = _execute(repository, operation)

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["abort"]["message"] == "invented draw failure"
    assert "operation" in result["abort"]["traceback"]
    assert json.loads(
        (repository / runner.DEFAULT_OUTPUT / "partial.json").read_text()
    ) == {"seed": 0, "draw": 0}


def test_protocol_mismatch_aborts_before_operation(repository, monkeypatch):
    baseline = _baseline_protocol(repository)
    baseline["protocol"]["draw_index"].pop()
    (repository / runner.BASELINE_PATH).write_bytes(
        runner.json_bytes(baseline)
    )
    monkeypatch.setattr(runner, "source_guard", lambda *args: {})
    calls = []

    result = _execute(repository, lambda *args: calls.append(args))

    assert calls == []
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert "seed/draw protocol changed" in result["abort"]["message"]


def test_midrun_source_change_cannot_publish_success(repository, monkeypatch):
    _baseline_protocol(repository)
    observations = iter(({"source": "before"}, {"source": "after"}))
    monkeypatch.setattr(
        runner, "source_guard", lambda *args: next(observations)
    )
    result = _execute(
        repository,
        lambda *args: {
            "status": "REPRODUCED",
            "equal": True,
            "admitted_scope": "invented attempted admission",
        },
    )

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert "source changed during replay" in result["abort"]["message"]


@pytest.mark.parametrize(
    "output",
    [
        "runs/gate_m6_candidate3_v1.json",
        "runs/new_b1.json",
        "scratch/track_b/another_attempt",
        "../outside/b1_v1",
    ],
)
def test_output_cannot_collide_with_runs_or_escape(repository, output):
    protected = repository / "runs/gate_m6_candidate3_v1.json"
    protected.parent.mkdir()
    protected.write_bytes(b"invented existing evidence\n")
    with pytest.raises(ValueError, match="B1 output must be"):
        runner.reserve_output(repository, output)
    assert protected.read_bytes() == b"invented existing evidence\n"
    assert not (repository / runner.DEFAULT_OUTPUT).exists()


def test_output_directory_is_exclusive_and_never_overwrites(repository):
    destination = runner.reserve_output(repository, runner.DEFAULT_OUTPUT)
    existing = destination / "result.json"
    existing.write_bytes(b"invented existing result\n")

    with pytest.raises(FileExistsError):
        runner.reserve_output(repository, runner.DEFAULT_OUTPUT)
    with pytest.raises(FileExistsError):
        runner._write_new(existing, {"overwrite": True})
    assert existing.read_bytes() == b"invented existing result\n"


@pytest.mark.parametrize("component", ["scratch", "scratch/track_b"])
def test_symlinked_output_parent_is_refused(repository, tmp_path, component):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repository / component
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinks"):
        runner.reserve_output(repository, runner.DEFAULT_OUTPUT)
    assert list(outside.iterdir()) == []


def test_output_symlink_is_refused(repository):
    outside = repository / "outside"
    outside.mkdir()
    destination = repository / runner.DEFAULT_OUTPUT
    destination.parent.mkdir(parents=True)
    destination.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinks"):
        runner.reserve_output(repository, runner.DEFAULT_OUTPUT)
    assert list(outside.iterdir()) == []


def test_tracked_destination_refused_even_if_worktree_file_absent(repository):
    destination = repository / runner.DEFAULT_OUTPUT
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"invented tracked artifact\n")
    subprocess.run(
        ["git", "add", str(runner.DEFAULT_OUTPUT)],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    destination.unlink()

    with pytest.raises(ValueError, match="collides with tracked files"):
        runner.reserve_output(repository, runner.DEFAULT_OUTPUT)
    assert not destination.exists()


@pytest.mark.parametrize(
    "registration",
    [
        "5064153427",
        "https://github.com/PolicyEngine/populace-dynamics/issues/42"
        "#issuecomment-5064153427",
    ],
)
def test_candidate3_consumed_registration_is_not_reusable(
    repository, registration
):
    with pytest.raises(ValueError, match="fresh"):
        runner.execute(
            root=repository,
            registration_id=registration,
            expected_commit="b" * 40,
            operation=lambda *args: pytest.fail("data operation invoked"),
        )
    assert not (repository / runner.DEFAULT_OUTPUT).exists()


def _invented_differential_inputs():
    inputs = _inputs()
    truth = inputs["truth_support"].copy()
    truth["cohort"] = np.where(truth["person_id"] <= 4, "prime", "older")
    anchors = truth.loc[truth["period"] == 2014, ["person_id", "weight"]]
    population = SimpleNamespace(
        initial_slice=inputs["initial_slice"],
        earnings_support=truth.assign(weight=999.0),
        earnings_domain_ids=inputs["domain_person_ids"],
        holdout_ids=inputs["all_person_ids"],
        start_weights=StartWaveWeightSnapshot.from_frame(
            anchors, boundary_period=2014
        ),
    )
    seeds, draws = (0, 1), (0, 1)
    baseline = {"family_a": {"per_seed": []}}
    for seed in seeds:
        cells = {
            name: {"per_draw_rate": []} for name in runner.EARNINGS_CELL_NAMES
        }
        for draw in draws:
            original = runner.project_earnings_on_realized_support(
                **{**inputs, "truth_support": population.earnings_support},
                draw_index=draw,
            )
            scored = runner._scored_surface(original, population)
            observed = runner.earnings_cells(scored)
            for name in cells:
                cells[name]["per_draw_rate"].append(observed[name]["value"])
        baseline["family_a"]["per_seed"].append(
            {"seed": seed, "gated_cells": cells}
        )
    return {
        "populations": {seed: population for seed in seeds},
        "generator": inputs["generator"],
        "fit_signature": {"invented_fit_sha256": "a" * 64},
        "baseline": baseline,
        "seeds": seeds,
        "draws": draws,
    }


def test_full_invented_differential_is_deterministic_and_archive_fail_closed(
    tmp_path,
):
    supplied = _invented_differential_inputs()
    outputs = [tmp_path / "first", tmp_path / "second"]
    results = []
    for output in outputs:
        output.mkdir()
        results.append(runner.run_differential(**supplied, output=output))

    assert results[0] == results[1]
    result = results[0]
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert result["historical_person_level_reference_available"] is False
    assert result["differences"][0]["reason"] == (
        "historical_person_level_reference_unavailable"
    )
    assert result["differential"]["equal"] is True
    assert result["registered_per_draw_cells"]["equal"] is True
    assert len(result["differential"]["comparisons"]) == 4
    assert len(result["files"]) == 4
    for evidence in result["files"]:
        first = (outputs[0] / evidence["path"]).read_bytes()
        second = (outputs[1] / evidence["path"]).read_bytes()
        assert first == second
        assert runner.sha256(first) == evidence["sha256"]
        payload = json.loads(first)
        weights = next(
            column["values"]
            for column in payload["replay_scored"]["columns"]
            if column["name"] == "weight"
        )
        assert all(value != runner._scalar(999.0) for value in weights)


def test_changed_registered_cell_cannot_be_hidden_by_exact_loop_agreement(
    tmp_path,
):
    supplied = _invented_differential_inputs()
    name = runner.EARNINGS_CELL_NAMES[0]
    cell = supplied["baseline"]["family_a"]["per_seed"][1]["gated_cells"][name]
    cell["per_draw_rate"][1] += 1.0
    result = runner.run_differential(**supplied, output=tmp_path)

    assert result["differential"]["equal"] is True
    assert result["registered_per_draw_cells"]["equal"] is False
    differences = result["registered_per_draw_cells"]["differences"]
    assert len(differences) == 1
    assert differences[0]["seed"] == 1
    assert differences[0]["draw"] == 1
    assert differences[0]["cell"] == name


def test_frame_writer_retains_signed_zero_and_nan_payload_bits():
    import pandas as pd

    values = np.array(
        [0, 1 << 63, 0x7FF8000000000001, 0x7FF8000000000002],
        dtype=np.uint64,
    ).view(np.float64)
    payload = runner.frame_payload(pd.DataFrame({"earnings": values}))
    encoded = payload["columns"][0]["values"]
    assert len({value["float64_hex"] for value in encoded}) == 4
    assert [bytes.fromhex(value["float64_hex"]) for value in encoded] == [
        value.tobytes() for value in values
    ]


def _invented_historical_manifest(supplied):
    """Build invented references using only the unchanged original loop."""
    records = []
    for seed in supplied["seeds"]:
        population = supplied["populations"][seed]
        for draw in supplied["draws"]:
            original = runner.project_earnings_on_realized_support(
                initial_slice=population.initial_slice,
                truth_support=population.earnings_support,
                generator=supplied["generator"],
                domain_person_ids=population.earnings_domain_ids,
                all_person_ids=population.holdout_ids,
                draw_index=draw,
            )
            records.append(
                {
                    "seed": seed,
                    "draw": draw,
                    "scored": runner.frame_payload(
                        runner._scored_surface(original, population)
                    ),
                    "fit_signature": supplied["fit_signature"],
                    "rng_signature": runner.earnings_rng_signature(
                        all_person_ids=population.holdout_ids,
                        draw_index=draw,
                    ),
                }
            )
    return {
        "schema_version": "track_b_b1_historical_reference.v1",
        "baseline_sha256": runner.BASELINE_SHA256,
        "origin": "historical_candidate3_run",
        "records": records,
    }


def test_invented_original_reference_allows_exact_reproduction(tmp_path):
    supplied = _invented_differential_inputs()
    manifest = _invented_historical_manifest(supplied)
    reference = tmp_path / "invented_original_reference.json"
    reference.write_bytes(runner.json_bytes(manifest))
    historical = runner.read_historical_reference(
        reference, runner.sha256(reference.read_bytes())
    )
    result = runner.run_differential(
        **supplied, output=tmp_path, historical_reference=historical
    )

    assert result["status"] == "REPRODUCED"
    assert result["equal"] is True
    assert result["historical_equality"]["equal"] is True
    assert result["differential"]["equal"] is True
    assert result["registered_per_draw_cells"]["equal"] is True
    assert len(result["historical_equality"]["comparisons"]) == 4


def test_one_person_historical_perturbation_blocks_reproduction(tmp_path):
    supplied = _invented_differential_inputs()
    manifest = _invented_historical_manifest(supplied)
    earnings = next(
        column
        for column in manifest["records"][3]["scored"]["columns"]
        if column["name"] == "earnings"
    )
    value = np.frombuffer(
        bytes.fromhex(earnings["values"][0]["float64_hex"]),
        dtype=np.float64,
    )[0]
    earnings["values"][0] = runner._scalar(np.nextafter(value, np.inf))
    reference = tmp_path / "invented_perturbed_reference.json"
    reference.write_bytes(runner.json_bytes(manifest))
    historical = runner.read_historical_reference(
        reference, runner.sha256(reference.read_bytes())
    )
    result = runner.run_differential(
        **supplied, output=tmp_path, historical_reference=historical
    )

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert result["differential"]["equal"] is True
    assert result["registered_per_draw_cells"]["equal"] is True
    failures = result["historical_equality"]["differences"]
    assert len(failures) == 1
    assert failures[0]["seed"] == 1
    assert failures[0]["draw"] == 1
    assert failures[0]["column"] == "earnings"


def test_historical_file_hash_and_duplicate_record_are_fail_closed(tmp_path):
    supplied = _invented_differential_inputs()
    manifest = _invented_historical_manifest(supplied)
    reference = tmp_path / "invented_reference.json"
    reference.write_bytes(runner.json_bytes(manifest))
    with pytest.raises(ValueError, match="SHA256 differs"):
        runner.read_historical_reference(reference, "0" * 64)

    manifest["records"].append(manifest["records"][0])
    reference.write_bytes(runner.json_bytes(manifest))
    with pytest.raises(ValueError, match="duplicate historical reference"):
        runner.read_historical_reference(
            reference, runner.sha256(reference.read_bytes())
        )
