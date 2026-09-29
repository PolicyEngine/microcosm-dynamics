"""INVENTED DATA - NOT A COMPARISON: dry-run artifact retention seams."""

import copy
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import track_a_v2_dry_run as dry


def _attempt(status, *, step=6):
    return {
        "header": dry.INVENTED_HEADER,
        "attempt": {
            "status": status,
            "step": step,
            "counters": {"invented_marker": 7},
            "uncomputed_rows": (
                [] if status == "completed" else list(range(68))
            ),
        },
        "rows": (
            {str(index): {"invented": True} for index in range(68)}
            if status == "completed"
            else {}
        ),
    }


@pytest.fixture
def seam(tmp_path, monkeypatch):
    """Mock every model path; exercise only the invented script protocol."""
    root = tmp_path / "repository"
    package = root / "src/populace_dynamics/track_a_v2"
    package.mkdir(parents=True)
    source = package / "calculator.py"
    source.write_text("invented_version = 1\n")
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "track_a_v2_driver.py").write_text("invented_driver = 1\n")
    persons = pd.DataFrame([{"person_id": 1, "weight": 1.0}])
    inputs = SimpleNamespace(
        cohort=SimpleNamespace(
            seal="invented-seal",
            persons=persons,
            initial_slice=persons.copy(),
            careers={1: {}},
            opening={},
        )
    )
    projected = {
        0: SimpleNamespace(
            slices=tuple(
                pd.DataFrame([{"person_id": 1, "di_event": "none"}])
                for _ in range(3)
            )
        )
    }
    state = SimpleNamespace(
        root=root,
        source=source,
        output=root / ".cache" / "new-attempt",
        results=[_attempt("completed"), _attempt("refused", step=2)],
        runs=0,
        manifests=0,
    )

    def run(*args, **kwargs):
        dry.legacy._project_population()
        result = copy.deepcopy(state.results[state.runs])
        state.runs += 1
        return result

    def manifest(**kwargs):
        state.manifests += 1
        return {
            "header": dry.INVENTED_HEADER,
            "implementation": [
                dry.file_record(path, root=root)
                for path in kwargs["implementation"]
            ],
        }

    monkeypatch.setattr(dry, "ROOT", root)
    monkeypatch.setattr(dry, "invented_inputs", lambda: inputs)
    monkeypatch.setattr(dry, "runtime_parameter_bundle", lambda _: {})
    monkeypatch.setattr(
        dry.legacy, "_project_population", lambda: (projected, {})
    )
    monkeypatch.setattr(
        dry,
        "HistoryValidator",
        lambda *args: SimpleNamespace(requested_di_levels=lambda: [1]),
    )
    monkeypatch.setattr(dry, "run_joint", run)
    monkeypatch.setattr(dry, "build_manifest", manifest)
    return state


def _json(path):
    return json.loads(path.read_text())


def _assert_invented_headers(output):
    for path in output.glob("*.json"):
        assert _json(path)["header"] == dry.INVENTED_HEADER


def test_unchanged_sources_bind_start_snapshot_and_complete_artifacts(seam):
    """Successful manifests match start bytes and retain returned attempts."""
    result = dry.dry_run(seam.output)
    assert result == seam.results[0]
    assert seam.runs == 2
    assert seam.manifests == 1
    start = _json(seam.output / "implementation-start.json")
    manifest = _json(seam.output / "hash-manifest.json")
    assert manifest["implementation"] == start["implementation"]
    assert _json(seam.output / "result.json") == seam.results[0]
    assert _json(seam.output / "forced-refusal.json") == seam.results[1]
    assert (
        (seam.output / "RESULTS.md")
        .read_text()
        .startswith(dry.INVENTED_HEADER + "\n")
    )
    assert not (seam.output / "dry-run-failure.json").exists()
    _assert_invented_headers(seam.output)


@pytest.mark.parametrize("populated", (False, True))
def test_existing_output_directory_refuses_before_inputs(
    seam, monkeypatch, populated
):
    """An existing attempt directory, even empty, is never overwritten."""
    seam.output.mkdir(parents=True)
    if populated:
        (seam.output / "prior.json").write_text("prior bytes\n")
    monkeypatch.setattr(
        dry, "invented_inputs", lambda: pytest.fail("inputs must not be built")
    )
    before = {path.name: path.read_bytes() for path in seam.output.iterdir()}
    with pytest.raises(FileExistsError):
        dry.dry_run(seam.output)
    assert {
        path.name: path.read_bytes() for path in seam.output.iterdir()
    } == before
    assert seam.runs == seam.manifests == 0


@pytest.mark.parametrize("mutation", ("content", "addition", "removal"))
def test_changed_implementation_refuses_manifest_and_keeps_attempts(
    seam, monkeypatch, mutation
):
    """Any intended source-content or file-list change blocks the manifest."""
    run = dry.run_joint

    def mutate(*args, **kwargs):
        result = run(*args, **kwargs)
        if seam.runs == 1:
            if mutation == "content":
                seam.source.write_text("invented_version = 2\n")
            elif mutation == "addition":
                (seam.source.parent / "added.py").write_text("invented = 1\n")
            else:
                seam.source.unlink()
        return result

    monkeypatch.setattr(dry, "run_joint", mutate)
    with pytest.raises(ValueError, match="implementation changed"):
        dry.dry_run(seam.output)
    assert seam.manifests == 0
    assert _json(seam.output / "result.json") == seam.results[0]
    assert _json(seam.output / "forced-refusal.json") == seam.results[1]
    assert _json(seam.output / "dry-run-failure.json")["type"] == "ValueError"
    assert not (seam.output / "hash-manifest.json").exists()
    assert not (seam.output / "RESULTS.md").exists()
    _assert_invented_headers(seam.output)


def test_source_change_during_manifest_construction_refuses_emission(
    seam, monkeypatch
):
    """A source change inside manifest construction cannot escape the seal."""
    build = dry.build_manifest

    def mutate(**kwargs):
        manifest = build(**kwargs)
        seam.source.write_text("invented_version = 2\n")
        return manifest

    monkeypatch.setattr(dry, "build_manifest", mutate)
    with pytest.raises(ValueError, match="while building"):
        dry.dry_run(seam.output)
    assert seam.manifests == 1
    assert not (seam.output / "hash-manifest.json").exists()
    assert _json(seam.output / "result.json") == seam.results[0]
    assert _json(seam.output / "forced-refusal.json") == seam.results[1]
    _assert_invented_headers(seam.output)


def test_unexpected_initial_refusal_is_written_before_assertion(seam):
    """An unexpected returned refusal retains its step and computed counters."""
    seam.results[0] = _attempt("refused", step=3)
    with pytest.raises(AssertionError, match="complete run refused"):
        dry.dry_run(seam.output)
    assert _json(seam.output / "result.json") == seam.results[0]
    assert seam.runs == 1
    assert seam.manifests == 0
    assert not (seam.output / "forced-refusal.json").exists()
    assert (
        _json(seam.output / "dry-run-failure.json")["type"] == "AssertionError"
    )
    _assert_invented_headers(seam.output)


@pytest.mark.parametrize("status,step", (("completed", 6), ("refused", 3)))
def test_unexpected_forced_attempt_is_written_before_assertion(
    seam, status, step
):
    """An incorrect forced-refusal result is preserved without a manifest."""
    seam.results[1] = _attempt(status, step=step)
    with pytest.raises(AssertionError):
        dry.dry_run(seam.output)
    assert _json(seam.output / "result.json") == seam.results[0]
    assert _json(seam.output / "forced-refusal.json") == seam.results[1]
    assert seam.manifests == 0
    assert not (seam.output / "hash-manifest.json").exists()
    _assert_invented_headers(seam.output)


@pytest.mark.parametrize("failing_run", (1, 2))
def test_unexpected_exception_keeps_prior_outputs(
    seam, monkeypatch, failing_run
):
    """Unexpected exceptions retain prior attempts without invented results."""
    run = dry.run_joint

    def fail(*args, **kwargs):
        if seam.runs + 1 == failing_run:
            raise RuntimeError("intended invented failure")
        return run(*args, **kwargs)

    monkeypatch.setattr(dry, "run_joint", fail)
    with pytest.raises(RuntimeError, match="intended invented failure"):
        dry.dry_run(seam.output)
    assert (seam.output / "result.json").exists() == (failing_run == 2)
    assert not (seam.output / "forced-refusal.json").exists()
    failure = _json(seam.output / "dry-run-failure.json")
    assert failure["type"] == "RuntimeError"
    assert failure["reason"] == "intended invented failure"
    assert seam.manifests == 0
    _assert_invented_headers(seam.output)
