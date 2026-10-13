"""Registration checks and publication on invented arrays, without HDF."""

from __future__ import annotations

import importlib.util
import json
import plistlib
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "population_registered_script",
    ROOT / "scripts/run_pe_us_depletion_cut_population_registered.py",
)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)

COMMIT = "a" * 40
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-12345"
)


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(runner.pop, "SPECIFICATION_STATUS", "ratified_frozen")
    monkeypatch.setattr(runner.pop, "SPECIFICATION_VERSION", "sa1-ratified-1")
    monkeypatch.setattr(runner.pop, "SPECIFICATION_SHA256", "b" * 64)
    return {"status": "ratified_frozen", "version": "sa1-ratified-1"}


def _preflight(tmp_path, specification, **changes):
    options = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "population.json",
        "git": lambda *args: COMMIT if args[0] == "rev-parse" else "",
        "specification": specification,
        "specification_sha256": "b" * 64,
    }
    options.update(changes)
    return runner.preflight(**options)


@pytest.mark.parametrize(
    "pointer",
    ["", "https://example.com", POINTER.replace("42#", "41#"), POINTER + "/"],
)
def test_preflight_refuses_bad_pointer(tmp_path, frozen, pointer):
    with pytest.raises(runner.Refusal, match="issue #42"):
        _preflight(tmp_path, frozen, registration_pointer=pointer)


@pytest.mark.parametrize("commit", ["abc1234", "g" * 40, "a" * 41])
def test_preflight_refuses_non_full_hex_commit(tmp_path, frozen, commit):
    with pytest.raises(runner.Refusal, match="40-hex"):
        _preflight(tmp_path, frozen, registered_commit=commit)


def test_preflight_refuses_head_mismatch(tmp_path, frozen):
    with pytest.raises(runner.Refusal, match="HEAD differs"):
        _preflight(tmp_path, frozen, registered_commit="c" * 40)


def test_preflight_refuses_dirty_tree(tmp_path, frozen):
    def git(*args):
        return COMMIT if args[0] == "rev-parse" else " M source.py"

    with pytest.raises(runner.Refusal, match="dirty"):
        _preflight(tmp_path, frozen, git=git)


@pytest.mark.parametrize(
    "field,value", [("status", "draft"), ("version", "sa1-draft-3")]
)
def test_preflight_refuses_draft_specification(tmp_path, frozen, field, value):
    with pytest.raises(runner.Refusal, match="ratified_frozen"):
        _preflight(tmp_path, {**frozen, field: value})


def test_preflight_refuses_wrong_specification_hash(tmp_path, frozen):
    with pytest.raises(runner.Refusal, match="SHA-256"):
        _preflight(tmp_path, frozen, specification_sha256="c" * 64)


@pytest.mark.parametrize("sidecar", [False, True])
@pytest.mark.parametrize("symlink", [False, True])
def test_preflight_refuses_existing_output(tmp_path, frozen, sidecar, symlink):
    output = tmp_path / "population.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    if symlink:
        existing.symlink_to(tmp_path / "missing")
    else:
        existing.write_text("preserved")
    with pytest.raises(runner.Refusal, match="already exists"):
        _preflight(tmp_path, frozen)
    if symlink:
        assert existing.is_symlink()
    else:
        assert existing.read_text() == "preserved"


def test_preflight_accepts_exact_frozen_registration(tmp_path, frozen):
    assert _preflight(tmp_path, frozen) == {
        "head": COMMIT,
        "git_clean": True,
        "skipped": [],
    }


@pytest.mark.parametrize("destination", ["output", "docs_dir"])
def test_dry_run_refuses_repository_outputs(tmp_path, destination):
    kwargs = {"output": None, "docs_dir": None}
    kwargs[destination] = (
        runner.DEFAULT_OUTPUT
        if destination == "output"
        else runner.DEFAULT_DOCS_DIR
    )
    with pytest.raises(runner.Refusal, match="dry run outputs"):
        runner.output_destinations(tmp_path, invented=True, **kwargs)


def test_dry_run_refuses_external_destination_outside_raw(tmp_path):
    with pytest.raises(runner.Refusal, match="raw-dir"):
        runner.output_destinations(
            tmp_path / "raw", tmp_path / "other.json", None, invented=True
        )


def test_dry_run_defaults_all_outputs_to_raw(tmp_path):
    artifact, docs = runner.output_destinations(
        tmp_path, None, None, invented=True
    )
    assert artifact.parent == tmp_path
    assert docs.parent == tmp_path


def _invented_probe():
    n = 6
    household = np.array([0, 1, 1, 2, 2, 2])
    unit = np.array([0, 1, 1, 2, 2, 3])
    age = np.array([68, 70, 64, 70, 70, 88])
    components = {name: np.zeros(n, dtype=float) for name in runner.COMPONENTS}
    components[runner.COMPONENTS[0]][:] = 8916
    return {
        **components,
        "person_id": np.arange(n) + 1,
        "household_id": np.array([11, 12, 13]),
        "marital_unit_id": np.arange(4) + 21,
        "household_index": household,
        "marital_unit_index": unit,
        "age": age,
        "frame_age": age.copy(),
        "A_MARITL": np.array([7, 1, 1, 1, 1, 4]),
        "cps_race": np.array([1, 2, 4, 1, 3, 1]),
        "is_hispanic": np.array([False, False, False, True, False, False]),
        "is_female": np.array([False, False, True, False, True, True]),
        **{
            f"frame_{name}": values.copy()
            for name, values in components.items()
        },
    }


def _scenario(probe, components, variant):
    resources = np.array([1500, 2500, 0, 5000, 0, 0], dtype=float)
    joint = np.zeros(6, dtype=bool)
    passed = (
        resources <= 2000
        if variant == "asset_test_as_encoded"
        else np.ones(6, dtype=bool)
    )
    total = sum(components.values())
    potential = 12168 - total
    ssi = potential * passed
    household = probe["household_index"]
    return {
        **{
            name: probe[name].copy()
            for name in (
                "person_id",
                "household_id",
                "marital_unit_id",
                "household_index",
                "marital_unit_index",
            )
        },
        **components,
        **{
            f"baseline_{name}": probe[name].copy()
            for name in runner.COMPONENTS
        },
        "social_security": total,
        "ssi_if_takes_up": ssi,
        "ssi": ssi.copy(),
        "ssi_countable_resources": resources,
        "ssi_claim_is_joint": joint,
        "meets_ssi_resource_test": passed,
        "is_ssi_aged_blind_disabled": np.array(
            [True, True, False, True, True, True]
        ),
        "is_ssi_qualified_noncitizen": np.zeros(6, dtype=bool),
        "immigration_status": np.array(["CITIZEN"] * 6),
        "takes_up_ssi_if_eligible": np.ones(6, dtype=bool),
        "individual_limit": np.asarray(2000.0),
        "couple_limit": np.asarray(3000.0),
        "household_weight": np.array([1.0, 2.0, 3.0]),
        "household_market_income": np.array([0.0, 200.0, 300.0]),
        "household_benefits": np.array([12000.0, 25000.0, 35000.0]),
        "household_health_benefits": np.zeros(3),
        "household_count_people": np.array([1.0, 2.0, 3.0]),
        "household_income_decile": np.array([1, 5, 9]),
        "household_state_benefits": np.zeros(3),
        "household_net_income": np.bincount(
            household, weights=total + ssi, minlength=3
        ),
    }


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    probe = _invented_probe()
    calls = []
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib_cache"))
    check_output = runner.subprocess.check_output

    def font_discovery(command, *args, **kwargs):
        # The restricted macOS host's system_profiler does not expose its
        # fonts. Matplotlib's bundled fonts suffice for a chart metadata
        # test, and this avoids a blocked host discovery subprocess.
        if command and command[0] == "system_profiler":
            return plistlib.dumps([{"_items": []}])
        return check_output(command, *args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "check_output", font_discovery)

    def child(_python, job, _timeout):
        calls.append(job["mode"])
        if job["mode"] == "write-invented":
            Path(job["frame_path"]).write_bytes(b"invented bytes")
            return {
                "frame_path": job["frame_path"],
                "timings": {"total_seconds": 0.1},
                "peak_rss_bytes": 100,
            }
        if job["mode"] == "probe":
            arrays = probe
        else:
            with np.load(job["components_path"]) as saved:
                components = {
                    name: saved[name].copy() for name in runner.COMPONENTS
                }
            arrays = _scenario(probe, components, job["variant"])
        with Path(job["output_path"]).open("xb") as stream:
            np.savez(stream, **arrays)
        return {
            "array_path": job["output_path"],
            "timings": {"total_seconds": 0.2},
            "peak_rss_bytes": 200,
        }

    installation = {
        "record_check": {
            "package_record_digest": runner.pop.PE_US_PIN[
                "package_record_digest"
            ]
        }
    }
    monkeypatch.setattr(runner, "_run_child", child)
    monkeypatch.setattr(
        runner.bridge, "_interpreter", lambda _: Path("invented-python")
    )
    monkeypatch.setattr(
        runner.minimum, "pinned_release", lambda _: (None, installation)
    )
    monkeypatch.setattr(runner, "_git", lambda *_: COMMIT)
    monkeypatch.setattr(
        runner.sample,
        "trustees_citation",
        lambda *_: {
            "quotes": {
                "OASI": {"payable_share": "0.78"},
                "OASDI": {"payable_share": "0.83"},
            }
        },
    )
    args = runner.argument_parser().parse_args(
        [
            "--invented-dry-run",
            "--raw-dir",
            str(tmp_path),
            "--phase-marker",
            str(tmp_path / "phase-statistics"),
        ]
    )
    return args, calls


def test_invented_pipeline_writers_keep_all_labels_no_absolute_paths(pipeline):
    args, calls = pipeline
    document = runner.run(args)
    assert calls == ["write-invented", "probe", *(["scenario"] * 6)]
    assert all(
        value["passed"] for value in document["checks"]["refusals"].values()
    )
    assert document["preflight"]["skipped"] == [
        "registration_pointer",
        "registered_commit",
        "clean_tree",
        "specification_status_version_and_hash",
    ]
    assert document["header"][0] == runner.DRY_RUN_LABEL
    artifact = args.raw_dir / "invented_population.json"
    saved = json.loads(artifact.read_text())
    assert list(saved)[0] == "header"
    sidecar = json.loads(artifact.with_suffix(".env.json").read_text())
    assert sidecar["artifact_sha256"] == runner._sha256(artifact)
    assert sidecar["header"] == document["header"]
    assert sidecar["named_differences"] == runner.pop.NAMED_DIFFERENCES
    report = (args.raw_dir / "invented_report/report.md").read_text()
    for label in document["header"]:
        assert label in report
        if document["chart"]["status"] == "written":
            assert (
                label
                in (
                    args.raw_dir / "invented_report/replacement.svg"
                ).read_text()
            )
            assert (
                label.encode()
                in (
                    args.raw_dir / "invented_report/replacement.png"
                ).read_bytes()
            )
    runner.minimum._no_absolute_paths(saved)
    runner.minimum._no_absolute_paths(sidecar)
    assert len(document["results"]) == 5
    assert all(len(document["results"][row]) == 2 for row in runner.pop.ROWS)
    assert (args.raw_dir / "phase-statistics").exists()
    assert document["diagnostics"]["context"]["status"] == "not_provided"


def test_row_identity_failure_invalidates_only_r3_r4(pipeline, monkeypatch):
    args, _ = pipeline
    actual = runner._run_child

    def altered(python, job, timeout):
        result = actual(python, job, timeout)
        if (
            job["mode"] == "scenario"
            and job["variant"] == "asset_test_as_encoded"
        ):
            path = Path(job["output_path"])
            arrays = runner._load_arrays(path)
            arrays["ssi_if_takes_up"][0] += 10
            with path.open("wb") as stream:
                np.savez(stream, **arrays)
        return result

    monkeypatch.setattr(runner, "_run_child", altered)
    monkeypatch.setattr(
        runner,
        "write_chart",
        lambda *_, **_kwargs: {"status": "skipped", "reason": "unit test"},
    )
    document = runner.run(args)
    for row in runner.pop.ROWS:
        entry = document["results"][row]["oasi22"]["all"]["all"]
        assert entry["status"] == (
            "invalid" if row in ("R3", "R4") else "valid"
        )
        if row in ("R3", "R4"):
            assert entry["F_test"] is None
            assert (
                entry["undefined_reasons"]["F_test"] == "row machinery invalid"
            )
            assert entry["intervals"]["F_test"]["interval"] is None


def test_refusal_record_contains_no_statistics_or_person_arrays(tmp_path):
    path = runner.write_refusal(
        tmp_path / "invented.json",
        runner.Refusal(4, "cut check", 3),
        "refusal_checks",
        invented=True,
        outcomes_computed=True,
    )
    record = json.loads(path.read_text())
    assert record["header"][0] == runner.DRY_RUN_LABEL
    assert "results" not in record
    assert "person_id" not in record
    assert record["refusal"]["failing_persons"] == 3
    assert record["refusal"]["ssi_outcomes_computed_and_discarded"]
    assert record["named_differences"] == runner.pop.NAMED_DIFFERENCES


def test_no_absolute_paths_rejects_run_metadata(pipeline):
    args, calls = pipeline
    args.run_metadata = args.raw_dir / "metadata.json"
    args.run_metadata.write_text(json.dumps({"source": "/private/local"}))
    with pytest.raises(ValueError, match="local path"):
        runner.run(args)
    assert not calls


def test_exclusive_writer_preserves_existing_file(tmp_path):
    path = tmp_path / "preserved.md"
    path.write_text("original")
    with pytest.raises(FileExistsError):
        runner._write_new(path, "replacement")
    assert path.read_text() == "original"


def test_context_requires_pinned_source_and_records_values(tmp_path):
    probe = _invented_probe()
    components = {name: probe[name] for name in runner.COMPONENTS}
    baseline = _scenario(probe, components, "asset_test_as_encoded")
    record = {
        "sha256": runner.CONTEXT_SHA256,
        "url": "https://example.com/pinned",
        "table": "Table 1",
        "values_thousands": {"social_security_only": 65522, "both": 2533},
    }
    path = tmp_path / "context.json"
    path.write_text(json.dumps(record))
    context = runner.context_block(path, probe, baseline)
    assert context["status"] == "provided"
    assert context["values_thousands"] == record["values_thousands"]
    record["sha256"] = "0" * 64
    path.write_text(json.dumps(record))
    with pytest.raises(runner.Refusal, match="snapshot"):
        runner.context_block(path, probe, baseline)


def test_structural_check_refuses_negative_resources_and_cross_household_units():
    probe = _invented_probe()
    baseline = _scenario(
        probe,
        {name: probe[name] for name in runner.COMPONENTS},
        "asset_test_as_encoded",
    )
    baseline["ssi_countable_resources"][0] = -1
    probe["household_index"][2] = 2
    result = runner._structural_check(probe, baseline, invented=True)
    assert result["failures"] >= 2


def test_failed_phase_hook_refuses_before_statistics_and_discards_arrays(
    pipeline, monkeypatch
):
    args, _ = pipeline
    args.phase_hook = "invented-hook"
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 1})(),
    )
    monkeypatch.setattr(
        runner.pop,
        "bootstrap_intervals",
        lambda *_args: pytest.fail("statistics started after failed hook"),
    )
    with pytest.raises(runner.Refusal, match="hook exited nonzero"):
        runner.run(args)
    assert args.phase_marker.exists()
    assert not list(args.raw_dir.glob("*.npz"))
    refusal = json.loads(
        (args.raw_dir / "invented_population.refusal.json").read_text()
    )
    assert refusal["refusal"]["phase_reached"] == "phase-statistics"
    assert refusal["refusal"]["ssi_outcomes_computed_and_discarded"]


def test_baseline_component_refusal_precedes_marker_and_discards_arrays(
    pipeline, monkeypatch
):
    args, _ = pipeline
    actual = runner._run_child

    def altered(python, job, timeout):
        result = actual(python, job, timeout)
        if job["mode"] == "scenario":
            path = Path(job["output_path"])
            arrays = runner._load_arrays(path)
            arrays["baseline_social_security_retirement"][0] += 1
            with path.open("wb") as stream:
                np.savez(stream, **arrays)
        return result

    monkeypatch.setattr(runner, "_run_child", altered)
    with pytest.raises(runner.Refusal, match="baseline component"):
        runner.run(args)
    assert not args.phase_marker.exists()
    assert not list(args.raw_dir.glob("*.npz"))


def test_existing_raw_transport_is_preserved_before_children(pipeline):
    args, calls = pipeline
    path = args.raw_dir / "probe.npz"
    path.write_bytes(b"preserve existing transport")
    with pytest.raises(
        runner.Refusal, match="raw transport output already exists"
    ):
        runner.run(args)
    assert path.read_bytes() == b"preserve existing transport"
    assert not calls


@pytest.mark.parametrize(
    "variable,check",
    [("social_security_retirement", "4"), ("ssi_if_takes_up", 6)],
)
def test_nonfinite_child_amounts_cannot_pass_tolerances(
    pipeline, monkeypatch, variable, check
):
    args, _ = pipeline
    actual = runner._run_child

    def altered(python, job, timeout):
        result = actual(python, job, timeout)
        if job["mode"] == "scenario":
            path = Path(job["output_path"])
            arrays = runner._load_arrays(path)
            arrays[variable][0] = np.nan
            with path.open("wb") as stream:
                np.savez(stream, **arrays)
        return result

    monkeypatch.setattr(runner, "_run_child", altered)
    with pytest.raises(runner.Refusal) as caught:
        runner.run(args)
    assert caught.value.check == check
    assert not args.phase_marker.exists()
    assert not list(args.raw_dir.glob("*.npz"))


@pytest.mark.parametrize(
    "malformation",
    ["record_list", "values_list", "values_none", "source_not_string"],
)
def test_malformed_context_is_recorded_as_a_refusal_before_children(
    pipeline, malformation
):
    args, calls = pipeline
    record = {
        "sha256": runner.CONTEXT_SHA256,
        "url": "https://example.com/source",
        "table": "Table 1",
        "values_thousands": {"social_security_only": 65522, "both": 2533},
    }
    if malformation == "record_list":
        record = []
    elif malformation == "values_list":
        record["values_thousands"] = []
    elif malformation == "values_none":
        record["values_thousands"] = None
    else:
        record["table"] = None
    args.context_snapshot = args.raw_dir / "context.json"
    args.context_snapshot.write_text(json.dumps(record))
    with pytest.raises(runner.Refusal) as caught:
        runner.run(args)
    assert caught.value.check == "context"
    assert not calls
    record = json.loads(
        (args.raw_dir / "invented_population.refusal.json").read_text()
    )
    assert record["refusal"]["check"] == "context"


def test_raced_canonical_array_is_preserved(pipeline, monkeypatch):
    args, _ = pipeline
    actual = runner._run_child
    external = args.raw_dir / "probe.npz"

    def raced(python, job, timeout):
        if job["mode"] == "probe":
            external.write_bytes(b"externally created after preflight")
        return actual(python, job, timeout)

    monkeypatch.setattr(runner, "_run_child", raced)
    with pytest.raises(runner.Refusal):
        runner.run(args)
    assert external.read_bytes() == b"externally created after preflight"
    assert not list(args.raw_dir.glob(".population-child-*"))
    assert not args.phase_marker.exists()


def test_private_child_partial_arrays_are_removed_after_timeout(
    pipeline, monkeypatch
):
    args, _ = pipeline
    actual = runner._run_child

    def timed_out(python, job, timeout):
        if job["mode"] == "scenario":
            Path(job["output_path"]).write_bytes(
                b"invented partial SSI transport"
            )
            raise runner.Refusal(
                "child", "child process exceeded explicit timeout"
            )
        return actual(python, job, timeout)

    monkeypatch.setattr(runner, "_run_child", timed_out)
    with pytest.raises(runner.Refusal, match="timeout"):
        runner.run(args)
    assert not list(args.raw_dir.glob(".population-child-*"))
    assert not list(args.raw_dir.glob("*.npz"))
    assert not args.phase_marker.exists()


def _invented_chart(document, directory, *, created_paths=None):
    for name in ("replacement.png", "replacement.svg"):
        runner._write_new(
            directory / name,
            "invented chart statistics",
            created_paths=created_paths,
        )
    return {
        "status": "written",
        "files": ["replacement.png", "replacement.svg"],
    }


def test_raced_publication_sidecar_preserved_while_owned_statistics_removed(
    pipeline, monkeypatch
):
    args, _ = pipeline
    output = args.raw_dir / "invented_population.json"
    external = output.with_suffix(".env.json")

    def raced_chart(document, directory, *, created_paths=None):
        result = _invented_chart(
            document, directory, created_paths=created_paths
        )
        external.write_text("externally created sidecar")
        return result

    monkeypatch.setattr(runner, "write_chart", raced_chart)
    with pytest.raises(runner.Refusal):
        runner.run(args)
    assert external.read_text() == "externally created sidecar"
    assert not output.exists()
    assert not list((args.raw_dir / "invented_report").glob("replacement.*"))
    assert not list(args.raw_dir.glob("*.npz"))
    assert not (args.raw_dir / "manifest.json").exists()


def test_publication_report_failure_removes_all_owned_statistics(
    pipeline, monkeypatch
):
    args, _ = pipeline
    actual = runner._write_new

    def failing_report(path, text, **kwargs):
        actual(path, text, **kwargs)
        if path.name == "report.md":
            raise OSError("invented report failure")

    monkeypatch.setattr(runner, "write_chart", _invented_chart)
    monkeypatch.setattr(runner, "_write_new", failing_report)
    with pytest.raises(runner.Refusal):
        runner.run(args)
    assert not (args.raw_dir / "invented_population.json").exists()
    assert not (args.raw_dir / "invented_population.env.json").exists()
    assert not list((args.raw_dir / "invented_report").iterdir())
    assert not list(args.raw_dir.glob("*.npz"))
    assert not (args.raw_dir / "manifest.json").exists()
    refusal = json.loads(
        (args.raw_dir / "invented_population.refusal.json").read_text()
    )
    assert refusal["refusal"]["ssi_outcomes_computed_and_discarded"]


def test_sidecar_environment_validated_before_publication(
    pipeline, monkeypatch
):
    args, _ = pipeline
    monkeypatch.setattr(
        runner, "_environment", lambda: {"python": "/private/local-path"}
    )
    monkeypatch.setattr(
        runner,
        "write_chart",
        lambda *_args, **_kwargs: pytest.fail(
            "chart published before environment validation"
        ),
    )
    with pytest.raises(runner.Refusal) as caught:
        runner.run(args)
    assert caught.value.check == 7
    assert not (args.raw_dir / "invented_population.json").exists()
    assert not (args.raw_dir / "invented_report").exists()
    assert not list(args.raw_dir.glob("*.npz"))


@pytest.mark.parametrize(
    "name", ["artifact", "sidecar", "report", "png", "svg"]
)
def test_dangling_output_symlinks_refused_before_computation(tmp_path, name):
    output = tmp_path / "invented.json"
    docs = tmp_path / "report"
    docs.mkdir()
    path = {
        "artifact": output,
        "sidecar": output.with_suffix(".env.json"),
        "report": docs / "report.md",
        "png": docs / "replacement.png",
        "svg": docs / "replacement.svg",
    }[name]
    path.symlink_to(tmp_path / "missing")
    with pytest.raises(runner.Refusal, match="already exists"):
        runner.output_destinations(tmp_path, output, docs, invented=True)
    assert path.is_symlink()


@pytest.mark.parametrize(
    "metadata", [{}, {"release_held_for": ""}, {"release_held_for": "soon"}]
)
def test_registered_run_refuses_without_a_release_decision(metadata):
    with pytest.raises(runner.Refusal, match="release decision"):
        runner.release_decision(metadata, invented=False)


def test_release_decision_is_recorded_and_dry_runs_need_none():
    assert (
        runner.release_decision({"release_held_for": "d900"}, invented=False)
        == "d900"
    )
    assert runner.release_decision({}, invented=True) == "not_applicable"


_fixture_scenario = _scenario


def _worked_scenario(probe, components, variant):
    """The fixture's scenario with one joint claim and one non-taker.

    Persons 3 and 4 claim jointly, so the encoded test pools their $5,000
    against the couple limit; person 5 is eligible but does not take SSI
    up, so ``ssi`` and ``ssi_if_takes_up`` differ for that unit.
    """
    arrays = _fixture_scenario(probe, components, variant)
    joint = np.array([False, False, False, True, True, False])
    resources = arrays["ssi_countable_resources"]
    pooled = np.bincount(probe["marital_unit_index"], weights=resources)[
        probe["marital_unit_index"]
    ]
    passed = (
        np.where(joint, pooled <= 3000, resources <= 2000)
        if variant == "asset_test_as_encoded"
        else np.ones(6, dtype=bool)
    )
    takes_up = np.array([True, True, True, True, True, False])
    eligible = (12168 - arrays["social_security"]) * passed
    arrays.update(
        ssi_claim_is_joint=joint,
        meets_ssi_resource_test=passed,
        ssi_if_takes_up=eligible,
        ssi=eligible * takes_up,
        takes_up_ssi_if_eligible=takes_up,
        household_net_income=np.bincount(
            probe["household_index"],
            weights=arrays["social_security"] + eligible * takes_up,
            minlength=3,
        ),
    )
    return arrays


def test_registered_statistics_end_to_end_on_a_worked_population(
    pipeline, monkeypatch
):
    """Expected values for every row, worked by hand from the specification.

    Six people each lose $1,968 a year (743 -> 579 a month). Person weights
    are 1, 2, 2, 3, 3, 3 (W = 14). Marital units: {0}, {1, 2}, {3, 4}, {5}.
    Resources: 1,500; 2,500 and 0; 5,000 and 0 (a joint claim); 0.
    """
    monkeypatch.setattr(sys.modules[__name__], "_scenario", _worked_scenario)
    args, _ = pipeline
    document = runner.run(args)
    assert all(
        record["passed"]
        for record in document["checks"]["row_validity"].values()
    )

    def cell(row):
        return document["results"][row]["oasi22"]["all"]["all"]

    r0 = cell("R0")
    assert (r0["n"], r0["n_cond"]) == (6, 6)
    assert r0["W"] == pytest.approx(14)
    # Encoded test: units {0} and {5} full; {1, 2} part (the holder fails
    # alone, the spouse passes); {3, 4} none (joint: 5,000 > 3,000).
    assert r0["F_test"] == pytest.approx(4 / 14)
    assert r0["P_test"] == pytest.approx(4 / 14)
    assert r0["N_test"] == pytest.approx(6 / 14)
    assert r0["F_no"] == pytest.approx(1)
    assert r0["B"] == pytest.approx(6 / 14)
    assert r0["B_part"] == pytest.approx(4 / 14)
    assert r0["B_cond"] == pytest.approx(6 / 14)

    r3 = cell("R3")
    # Spousal deeming: {1, 2} pooled 2,500 <= 3,000 passes; {3, 4} fails.
    assert r3["F_test"] == pytest.approx(8 / 14)
    assert r3["P_test"] == pytest.approx(0)
    assert r3["B"] == pytest.approx(6 / 14)
    assert r3["B_part"] == pytest.approx(0)

    r4 = cell("R4")
    # Household pooling: person 5 shares the 5,000 household and fails.
    assert r4["F_test"] == pytest.approx(5 / 14)
    assert r4["B"] == pytest.approx(9 / 14)
    assert r4["B"] >= r3["B"]

    r2 = cell("R2")
    # Frame take-up: person 5 never takes SSI up, so that unit is none with
    # and without the asset test and is not counted as blocked.
    assert r2["F_no"] == pytest.approx(11 / 14)
    assert r2["N_no"] == pytest.approx(3 / 14)
    assert r2["n_cond"] == 5
    assert r2["W_cond"] == pytest.approx(11)
    assert r2["F_test"] == pytest.approx(1 / 14)
    assert r2["P_test"] == pytest.approx(4 / 14)
    assert r2["N_test"] == pytest.approx(9 / 14)
    assert r2["B"] == pytest.approx(6 / 14)
    assert r2["B_cond"] == pytest.approx(6 / 11)
    assert r2["B_part"] == pytest.approx(4 / 14)


def _mismatched_test_scenario(probe, components, variant):
    """PE-US's test fails person 0, whose resources pass the encoded rule."""
    arrays = _fixture_scenario(probe, components, variant)
    if variant == "asset_test_as_encoded":
        passed = arrays["meets_ssi_resource_test"].copy()
        passed[0] = False
        eligible = (12168 - arrays["social_security"]) * passed
        arrays.update(
            meets_ssi_resource_test=passed,
            ssi_if_takes_up=eligible,
            ssi=eligible.copy(),
        )
    return arrays


def test_resource_test_mismatch_invalidates_only_r3_r4(pipeline, monkeypatch):
    """Row validity (b) is not a refusal: R3 and R4 fall, the rest stand."""
    monkeypatch.setattr(
        sys.modules[__name__], "_scenario", _mismatched_test_scenario
    )
    args, _ = pipeline
    document = runner.run(args)
    validity = document["checks"]["row_validity"]
    assert validity["a"]["passed"]
    assert not validity["b"]["passed"]
    assert validity["b"]["failing_persons"] == 1
    for row in ("R3", "R4"):
        entry = document["results"][row]["oasi22"]["all"]["all"]
        assert entry["status"] == "invalid"
        assert entry["B"] is None
    for row in ("R0", "R2", "R5"):
        entry = document["results"][row]["oasi22"]["all"]["all"]
        assert entry["status"] == "valid"
        assert entry["B"] is not None


def test_frame_storing_a_calculated_variable_is_refused(pipeline, monkeypatch):
    load = runner._load_arrays

    def with_stored_ssi(path):
        arrays = load(path)
        if path.name == "probe.npz":
            arrays["frame_column_names"] = np.asarray(["age", "ssi"])
        return arrays

    monkeypatch.setattr(runner, "_load_arrays", with_stored_ssi)
    args, calls = pipeline
    with pytest.raises(runner.Refusal) as caught:
        runner.run(args)
    assert caught.value.check == "frame"
    assert "ssi" in caught.value.name
    assert "scenario" not in calls


@pytest.mark.parametrize(
    "value",
    [
        {"note": "saved at /tmp/private"},
        {"/private/path": "value"},
        ["nested", {"where": "~/evidence/run.log"}],
        "file:///Users/someone/frame.h5",
        "/Users/someone/frame.h5",
    ],
)
def test_no_local_paths_refuses_embedded_paths_and_keys(value):
    with pytest.raises(ValueError, match="local path"):
        runner.no_local_paths(value)


@pytest.mark.parametrize(
    "value",
    [
        {"url": "https://www.ssa.gov/oact/TR/2026/II_A_highlights.html"},
        "https://example.com/tmp/file",
        "docs/analysis/pe_us_depletion_cut_20261001/sources/page.html",
        "PEUS/variables/gov/ssa/ssi/ssi_if_takes_up.py:25-38",
        {"labels": list(runner.pop.LABELS), "n": 3, "share": 0.5},
        list(runner.pop.NAMED_DIFFERENCES),
    ],
)
def test_no_local_paths_accepts_urls_and_relative_paths(value):
    runner.no_local_paths(value)


def test_child_helpers_refuse_the_real_frame_without_registration(
    tmp_path, monkeypatch
):
    from populace_dynamics.bridge import (
        depletion_cut_population_child as child,
    )

    frame = tmp_path / "frame.h5"
    frame.write_bytes(b"not the frame")
    monkeypatch.setattr(child, "_cached_sha256", lambda _: child.FRAME_SHA256)
    monkeypatch.setattr(child, "_REGISTRATION", None)
    with pytest.raises(ValueError, match="registered entry point"):
        child._microsimulation(frame)
    with pytest.raises(ValueError, match="registered entry point"):
        child._probe(frame)
    with pytest.raises(ValueError, match="explicit dataset"):
        child._microsimulation(None)


def test_child_registration_record_is_validated():
    from populace_dynamics.bridge import (
        depletion_cut_population_child as child,
    )

    assert child._registration({"registered": False}) is None
    with pytest.raises(ValueError, match="registration record"):
        child._registration({"registered": True})
    with pytest.raises(ValueError, match="registration record"):
        child._registration(
            {"registered": True, "registration": {"pointer": "x"}}
        )
    record = {
        "pointer": "https://github.com/PolicyEngine/microcosm-dynamics/"
        "issues/42#issuecomment-1",
        "commit": "a" * 40,
        "specification_sha256": "b" * 64,
    }
    assert (
        child._registration({"registered": True, "registration": record})
        == record
    )
