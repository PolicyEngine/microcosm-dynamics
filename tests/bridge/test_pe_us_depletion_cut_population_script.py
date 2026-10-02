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
def test_preflight_refuses_existing_output(tmp_path, frozen, sidecar):
    output = tmp_path / "population.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    existing.write_text("preserved")
    with pytest.raises(runner.Refusal, match="already exists"):
        _preflight(tmp_path, frozen)
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
        lambda *_: {"status": "skipped", "reason": "unit test"},
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
    "variable,check", [("social_security", "4"), ("ssi_if_takes_up", 6)]
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
