"""Invented-input B1 orchestration, evidence, and exclusive-write checks."""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from populace_dynamics.engine.support import StartWaveWeightSnapshot
from populace_dynamics.harness import m6_projection
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
    lineage = {
        "q_invariant_fit_signature_sha256": "a" * 64,
        "rank_refresh_fit_audit": {"invented_refresh_rows": [1, 2]},
        "resolved_spec_sha256s": {"forward_earnings_adapter": "c" * 64},
        "refit_provenance": {"earnings": {"invented_seed": 0}},
        "boundary_year": 2014,
    }
    baseline = {"family_a": {"per_seed": []}, "lineage": lineage}
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
        # The replay side's refit, built from its own copy of the lineage.
        "fit_signature": runner._fit_lineage_signature(copy.deepcopy(lineage)),
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


def test_original_rng_is_sized_by_the_harness_not_the_replay(
    tmp_path, monkeypatch
):
    # The registry size does not change any stream, so only the recorded
    # n_periods differs; before the fix both sides used RNG_N_PERIODS.
    monkeypatch.setattr(m6_projection, "PROJECTION_END_YEAR", 2023)
    supplied = _invented_differential_inputs()
    result = runner.run_differential(**supplied, output=tmp_path)

    differences = result["differential"]["differences"]
    assert len(differences) == 4
    for difference in differences:
        assert difference["kind"] == "signature_value"
        assert difference["path"] == ["rng_signature", "n_periods"]
        assert difference["expected"]["repr"] == "9"
        assert difference["actual"]["repr"] == "8"
    assert result["registered_per_draw_cells"]["equal"] is True


def test_original_fit_side_comes_from_the_committed_lineage(tmp_path):
    supplied = _invented_differential_inputs()
    supplied["baseline"]["lineage"]["q_invariant_fit_signature_sha256"] = (
        "d" * 64
    )
    supplied["baseline"]["lineage"]["boundary_year"] = 2015
    result = runner.run_differential(**supplied, output=tmp_path)

    differences = result["differential"]["differences"]
    # boundary_year is outside FIT_SIGNATURE_KEYS and stays immaterial.
    assert [item["path"] for item in differences] == [
        ["fit_signature", "q_invariant_fit_signature_sha256"]
    ] * 4
    assert result["differential"]["equal"] is False
    payload = json.loads((tmp_path / "seed_0_draw_0.json").read_bytes())
    assert payload["original_fit_signature"][
        "q_invariant_fit_signature_sha256"
    ] == ("d" * 64)
    assert payload["replay_fit_signature"] == supplied["fit_signature"]


def test_fit_signature_uses_the_artifact_json_types():
    lineage = {
        key: {"values": (1, 2.5), "flag": True}
        for key in runner.FIT_SIGNATURE_KEYS
    }
    signature = runner._fit_lineage_signature(lineage)
    assert signature == {
        key: {"values": [1, 2.5], "flag": True}
        for key in runner.FIT_SIGNATURE_KEYS
    }
    assert lineage[runner.FIT_SIGNATURE_KEYS[0]]["values"] == (1, 2.5)


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
                    "fit_signature": copy.deepcopy(supplied["fit_signature"]),
                    "rng_signature": runner.earnings_rng_signature(
                        all_person_ids=population.holdout_ids,
                        draw_index=draw,
                        n_periods=m6_projection.PROJECTION_END_YEAR - 2014,
                    ),
                }
            )
    return {
        "schema_version": "track_b_b1_historical_reference.v1",
        "baseline_sha256": runner.BASELINE_SHA256,
        "origin": "historical_candidate3_run",
        "records": records,
    }


def _write_reference(path: Path, manifest: dict) -> str:
    path.write_bytes(runner.json_bytes(manifest))
    return runner.sha256(path.read_bytes())


def test_committed_build_admits_no_historical_reference():
    assert runner.HISTORICAL_REFERENCE_SHA256 is None


def test_regenerated_reference_is_refused_while_no_hash_is_committed(
    tmp_path,
):
    # Before the fix, this regenerated file returned REPRODUCED because the
    # caller supplied its hash; custody now comes only from the constant.
    supplied = _invented_differential_inputs()
    reference = tmp_path / "invented_original_reference.json"
    digest = _write_reference(
        reference, _invented_historical_manifest(supplied)
    )

    with pytest.raises(ValueError, match="refuses every historical"):
        runner.read_historical_reference(reference)
    unread = runner.HistoricalReference(reference.read_bytes())
    assert unread.digest == digest
    with pytest.raises(ValueError, match="refuses every historical"):
        runner.run_differential(
            **supplied, output=tmp_path, historical_reference=unread
        )
    assert not list(tmp_path.glob("seed_*_draw_*.json"))


def test_reference_cannot_be_relabelled_or_edited_after_reading(
    tmp_path, monkeypatch
):
    supplied = _invented_differential_inputs()
    honest = _invented_historical_manifest(supplied)
    perturbed = copy.deepcopy(honest)
    earnings = next(
        column
        for column in perturbed["records"][3]["scored"]["columns"]
        if column["name"] == "earnings"
    )
    value = np.frombuffer(
        bytes.fromhex(earnings["values"][0]["float64_hex"]),
        dtype=np.float64,
    )[0]
    earnings["values"][0] = runner._scalar(np.nextafter(value, np.inf))
    committed = tmp_path / "invented_committed.json"
    regenerated = tmp_path / "invented_regenerated.json"
    digest = _write_reference(committed, perturbed)
    regenerated_digest = _write_reference(regenerated, honest)
    assert regenerated_digest != digest
    output = tmp_path / "evidence"
    output.mkdir()
    monkeypatch.setattr(
        runner, "HISTORICAL_REFERENCE_SHA256", regenerated_digest
    )
    honest_records = runner.authenticated_records(
        runner.HistoricalReference(regenerated.read_bytes())
    )
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", digest)

    # Other bytes cannot borrow the committed hash: it is recomputed.
    substituted = runner.HistoricalReference(regenerated.read_bytes())
    with pytest.raises(ValueError, match="differs from the committed"):
        runner.run_differential(
            **supplied, output=output, historical_reference=substituted
        )
    reference = runner.read_historical_reference(committed)
    with pytest.raises(dataclasses.FrozenInstanceError):
        reference.payload = regenerated.read_bytes()
    # Splicing the honest record into parsed records cannot reach the
    # comparison, which re-parses the committed bytes.
    edited = runner.authenticated_records(reference)
    edited[1, 1] = honest_records[1, 1]
    result = runner.run_differential(
        **supplied, output=output, historical_reference=reference
    )
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    failures = result["historical_equality"]["differences"]
    assert [(item["seed"], item["draw"]) for item in failures] == [(1, 1)]


@pytest.mark.parametrize("committed", [None, "0" * 64])
def test_execute_refuses_uncommitted_reference_and_publishes_abort(
    repository, monkeypatch, committed
):
    _baseline_protocol(repository)
    monkeypatch.setattr(
        runner, "source_guard", lambda *args: {"commit": "b" * 40}
    )
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", committed)
    reference = repository / "invented_regenerated_reference.json"
    reference.write_bytes(b'{"origin":"historical_candidate3_run"}\n')

    result = runner.execute(
        root=repository,
        registration_id="9999999999",
        expected_commit="b" * 40,
        operation=lambda *args: pytest.fail("data operation invoked"),
        historical_reference=reference,
    )

    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert "HISTORICAL_REFERENCE_SHA256" in result["abort"]["message"]
    # The refusal is recorded; the refused file's hash appears in the abort
    # message whenever it was read (a None constant refuses before reading).
    assert result["historical_reference"] == {
        "path": str(reference),
        "committed_sha256": committed,
    }
    if committed is not None:
        assert runner.sha256(reference.read_bytes()) in (
            result["abort"]["message"]
        )
    assert (
        json.loads(
            (repository / runner.DEFAULT_OUTPUT / "result.json").read_text()
        )
        == result
    )


def test_cli_has_no_hash_that_could_override_the_committed_constant(
    monkeypatch, capsys
):
    script = Path(__file__).resolve().parents[1] / "scripts/run_track_b_b1.py"
    spec = importlib.util.spec_from_file_location("run_track_b_b1", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    def execute(**kwargs):
        calls.append(kwargs)
        return {"status": "BASELINE_REPLAY_MISMATCH"}

    monkeypatch.setattr(module, "execute", execute)
    arguments = [
        "--registration-id",
        "9999999999",
        "--expected-commit",
        "b" * 40,
        "--historical-reference",
        "invented.json",
    ]
    with pytest.raises(SystemExit) as exit_info:
        module.main([*arguments, "--historical-reference-sha256", "0" * 64])
    assert exit_info.value.code == 2
    assert "--historical-reference-sha256" in capsys.readouterr().err
    assert calls == []

    assert module.main(arguments) == 2
    assert set(calls[0]) == {
        "root",
        "registration_id",
        "expected_commit",
        "output",
        "historical_reference",
    }


def test_reference_matching_monkeypatched_constant_is_accepted(
    tmp_path, monkeypatch
):
    supplied = _invented_differential_inputs()
    reference = tmp_path / "invented_original_reference.json"
    digest = _write_reference(
        reference, _invented_historical_manifest(supplied)
    )
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", digest)
    historical = runner.read_historical_reference(reference)
    assert historical.digest == digest
    result = runner.run_differential(
        **supplied, output=tmp_path, historical_reference=historical
    )

    assert result["status"] == "REPRODUCED"
    assert result["equal"] is True
    assert result["historical_equality"]["equal"] is True
    assert result["differential"]["equal"] is True
    assert result["registered_per_draw_cells"]["equal"] is True
    assert len(result["historical_equality"]["comparisons"]) == 4


def test_one_person_historical_perturbation_blocks_reproduction(
    tmp_path, monkeypatch
):
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
    digest = _write_reference(reference, manifest)
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", digest)
    historical = runner.read_historical_reference(reference)
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


def test_historical_file_hash_and_duplicate_record_are_fail_closed(
    tmp_path, monkeypatch
):
    supplied = _invented_differential_inputs()
    manifest = _invented_historical_manifest(supplied)
    reference = tmp_path / "invented_reference.json"
    _write_reference(reference, manifest)
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="differs from the committed"):
        runner.read_historical_reference(reference)

    manifest["records"].append(manifest["records"][0])
    digest = _write_reference(reference, manifest)
    monkeypatch.setattr(runner, "HISTORICAL_REFERENCE_SHA256", digest)
    with pytest.raises(ValueError, match="duplicate historical reference"):
        runner.read_historical_reference(reference)


@pytest.mark.parametrize(
    "unserializable", [object(), float("nan")], ids=["object", "nan"]
)
def test_unserializable_result_still_publishes_a_mismatch_record(
    repository, monkeypatch, unserializable
):
    _baseline_protocol(repository)
    monkeypatch.setattr(
        runner, "source_guard", lambda *args: {"commit": "b" * 40}
    )
    result = _execute(
        repository,
        lambda *args: {
            "status": "BASELINE_REPLAY_MISMATCH",
            "equal": False,
            "admitted_scope": "none",
            "diagnostic": unserializable,
        },
    )

    published = json.loads(
        (repository / runner.DEFAULT_OUTPUT / "result.json").read_text()
    )
    assert published == result
    assert result["status"] == "BASELINE_REPLAY_MISMATCH"
    assert result["equal"] is False
    assert result["admitted_scope"] == "none"
    assert result["publishes_regardless"] is True
    assert result["registration_id"] == "9999999999"
    assert result["publication_error"]["type"] in {"TypeError", "ValueError"}
    assert result["serializable_result_fields"]["source"] == {
        "commit": "b" * 40
    }
    assert result["unserializable_result_fields"] == ["diagnostic"]
    assert "'diagnostic'" in result["unserializable_result_repr"]
    assert result["partial_files"] == []


def test_operation_cannot_publish_reproduced_without_admitted_reference(
    repository, monkeypatch
):
    _baseline_protocol(repository)
    monkeypatch.setattr(
        runner, "source_guard", lambda *args: {"commit": "b" * 40}
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
    assert "REPRODUCED requires" in result["abort"]["message"]
    assert (
        json.loads(
            (repository / runner.DEFAULT_OUTPUT / "result.json").read_text()
        )
        == result
    )


def test_replay_fit_signature_is_compared_in_json_types(tmp_path):
    supplied = _invented_differential_inputs()
    audit = supplied["fit_signature"]["rank_refresh_fit_audit"]
    audit["invented_refresh_rows"] = tuple(audit["invented_refresh_rows"])
    result = runner.run_differential(**supplied, output=tmp_path)
    assert result["differential"]["equal"] is True
