"""Invented protocol fixtures: no real cohort is read or projected."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from populace_dynamics.track_a_v2 import protocol
from populace_dynamics.track_a_v2.manifest import (
    REGISTERED_HEADER,
    SPECIFICATION_SHA256,
    file_record,
    object_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-123"
)
COMMIT = "1" * 40


def fake_git(*args):
    return COMMIT if args == ("rev-parse", "HEAD") else ""


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    # Manifest bytes have independent tests. These fake package records
    # isolate the protocol interlocks without reading any statutory/data file.
    monkeypatch.setattr(protocol, "verify_manifest", lambda *a, **kw: None)
    record_path = tmp_path / "invented-freeze.txt"
    record_path.write_text("INVENTED DATA - NOT A COMPARISON\n")
    package_record = file_record(record_path, root=ROOT)
    package = {
        "version": "a2-ratified-1",
        "mode": "registered",
        "implementation_commit": COMMIT,
        "specification_sha256": SPECIFICATION_SHA256,
        "registration_pointer": POINTER,
        "draw_indices": list(range(20)),
        "root_seeds": list(range(5200, 5220)),
        "anchor_wave": 2011,
        "reference_year": 2030,
        "output": str(tmp_path / "artifact.json"),
        "executor": "invented-test-executor",
        "environment": {"python": "invented"},
        "procedure": "invented test procedure",
        "attempt_policy": "infrastructure failures only",
        "input_roots": {
            "psid": "/invented/psid",
            "policyengine_us": "/invented/oracle",
        },
        "hash_manifest": {
            "header": REGISTERED_HEADER,
            "implementation": [
                {"path": str(path.relative_to(ROOT))}
                for path in (
                    *(ROOT / "src/populace_dynamics/track_a_v2").glob("*.py"),
                    *(ROOT / "scripts").glob("track_a_v2_*.py"),
                )
            ],
            "source_files": {"statute": package_record},
            "inputs": {
                name: package_record
                for name in (
                    "claiming_reference",
                    "cola_history",
                    "di_rates",
                    "di_nchs",
                )
            },
            "parameter_bundles": {"runtime": {"sha256": "invented"}},
        },
        "rows": list(protocol.FROZEN_ROWS),
        "headlines": ["D×R0", "D×F0"],
        "floor_seeds": list(range(5)),
        "floor_fraction": 0.5,
        "reporting_template": package_record,
        "exposure_record": package_record,
        "forecasts": package_record,
    }
    bind_invented_structural_attempt(package, tmp_path)
    return package


def check(frozen, **changes):
    kwargs = {
        "root": ROOT,
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": Path(frozen["output"]),
        "protocol": frozen,
        "protocol_sha256": object_sha256(frozen),
        "git": fake_git,
        **changes,
    }
    return protocol.preflight(**kwargs)


def test_frozen_protocol_passes(frozen):
    """Exact specification, commit, clean state and complete package pass."""
    result = check(frozen)
    assert result.head == COMMIT
    assert result.mode == "registered"
    assert result.specification_sha256 == SPECIFICATION_SHA256


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"registration_pointer": "not-an-issue"}, "issue #42"),
        ({"registered_commit": "111"}, "full 40-hex"),
        ({"registered_commit": "2" * 40}, "exact registered commit"),
        ({"protocol_sha256": "0" * 64}, "protocol hash"),
        (
            {
                "git": lambda *args: (
                    COMMIT if args[0] == "rev-parse" else " M x"
                )
            },
            "clean",
        ),
    ],
)
def test_preflight_refuses_nonfrozen_state(frozen, change, message):
    """Every interlock fails before a population loader could run."""
    with pytest.raises(ValueError, match=message):
        check(frozen, **change)


@pytest.mark.parametrize(
    "field",
    [
        "version",
        "specification_sha256",
        "anchor_wave",
        "root_seeds",
        "draw_indices",
        "executor",
        "environment",
        "procedure",
        "attempt_policy",
        "rows",
        "headlines",
        "floor_fraction",
        "reporting_template",
        "forecasts",
        "exposure_record",
    ],
)
def test_frozen_package_requires_every_registered_field(frozen, field):
    """A package omission never silently inherits an execution default."""
    del frozen[field]
    with pytest.raises(ValueError):
        check(frozen)


def test_ratified_specification_bytes_are_pinned(frozen, tmp_path):
    """Even a document claiming ratification fails when its bytes differ."""
    spec = tmp_path / protocol.SPECIFICATION_PATH
    spec.parent.mkdir(parents=True)
    spec.write_text("Status: ratified; a2-ratified-1; altered\n")
    with pytest.raises(ValueError, match="ratified a2-ratified-1 bytes"):
        check(frozen, root=tmp_path)


def test_artifact_is_exclusive_even_after_preflight(frozen):
    """An existing artifact or creation race never overwrites an attempt."""
    check(frozen)
    path = Path(frozen["output"])
    protocol.write_new(path, {"invented": 1})
    with pytest.raises(ValueError, match="one-shot"):
        check(frozen)
    with pytest.raises(FileExistsError):
        protocol.write_new(path, {"invented": 2})
    assert json.loads(path.read_text()) == {"invented": 1}


def structural_protocol(frozen):
    frozen = copy.deepcopy(frozen)
    frozen.pop("structural_check", None)
    for key in ("rows", "headlines", "floor_seeds", "floor_fraction"):
        del frozen[key]
    frozen.update(
        mode="structural",
        authorization="Max d513, 2026-09-28, item 7",
        permitted_outputs=list(protocol.STRUCTURAL_OUTPUTS),
    )
    return frozen


def test_structural_protocol_is_separate_and_count_only(frozen):
    """The authorized structural exception cannot authorize outcomes."""
    frozen = structural_protocol(frozen)
    assert check(frozen, mode="structural").mode == "structural"
    frozen["permitted_outputs"].append("benefits")
    with pytest.raises(ValueError, match="only frozen count"):
        check(frozen, mode="structural")


def test_structural_check_requires_its_authorization(frozen):
    """No generic protocol can stand in for the §16.7 authorization."""
    frozen = structural_protocol(frozen)
    del frozen["authorization"]
    with pytest.raises(ValueError, match="explicit authorization"):
        check(frozen, mode="structural")


def test_registered_package_requires_structural_check_binding(frozen):
    """§11 cannot omit the attempt and counts of the authorized check."""
    binding = frozen.pop("structural_check")
    with pytest.raises(ValueError, match="structural-check authorization"):
        check(frozen)
    frozen["structural_check"] = {
        "status": "not_performed",
        "authorization": binding["authorization"],
        "reason": "An explicit omission still lacks the required attempt.",
    }
    with pytest.raises(ValueError, match="authorized structural attempt"):
        check(frozen)


def bind_invented_structural_attempt(frozen, tmp_path):
    """Bind invented records without executing a real structural check."""
    from populace_dynamics.track_a_v2.structural import (
        COUNT_UNITS,
        ORDERING_CLASSES,
    )

    prior = structural_protocol(frozen)
    digest = object_sha256(prior)
    protocol_path = tmp_path / "invented-prior-protocol.json"
    protocol_path.write_text(json.dumps(prior))
    rows = [
        *(f"R{i}" for i in range(6)),
        *(f"F{i}" for i in range(8)),
        *(f"U{i}" for i in range(3)),
    ]
    counts = {
        "d_unsupported_histories": 0,
        "s_refused_earlier_spells": 0,
        "opening_proxy_applications": 0,
        "s_ordering_classes": {
            f"{row}/{scenario}": dict.fromkeys(ORDERING_CLASSES, 0)
            for row in rows
            for scenario in ("baseline", "reform")
        },
    }
    artifact = {
        "header": REGISTERED_HEADER,
        "protocol_sha256": digest,
        "attempt": {
            "status": "completed",
            "refusal": None,
            "completed_draws": list(range(20)),
            "uncomputed_draws": [],
        },
        "count_units": COUNT_UNITS,
        "counts": counts,
    }
    artifact_path = tmp_path / "invented-prior-attempt.json"
    artifact_path.write_text(json.dumps(artifact))
    frozen["structural_check"] = {
        "status": "performed",
        "authorization": prior["authorization"],
        "protocol": file_record(protocol_path, root=ROOT),
        "artifact": file_record(artifact_path, root=ROOT),
        "protocol_sha256": digest,
    }
    return artifact, artifact_path


def test_registered_package_binds_structural_attempt_and_exact_counts(
    frozen, tmp_path
):
    """A prior structural attempt must match its own frozen protocol and counts."""
    artifact, artifact_path = bind_invented_structural_attempt(
        frozen, tmp_path
    )
    check(frozen)
    artifact["counts"]["weight_sum"] = 1
    artifact_path.write_text(json.dumps(artifact))
    frozen["structural_check"]["artifact"] = file_record(
        artifact_path, root=ROOT
    )
    with pytest.raises(ValueError, match="only the four frozen"):
        check(frozen)
    artifact["counts"].pop("weight_sum")
    artifact["protocol_sha256"] = "0" * 64
    artifact_path.write_text(json.dumps(artifact))
    frozen["structural_check"]["artifact"] = file_record(
        artifact_path, root=ROOT
    )
    with pytest.raises(ValueError, match="frozen protocol"):
        check(frozen)
    artifact["protocol_sha256"] = frozen["structural_check"]["protocol_sha256"]
    artifact["benefits"] = {"invented": 1}
    artifact_path.write_text(json.dumps(artifact))
    frozen["structural_check"]["artifact"] = file_record(
        artifact_path, root=ROOT
    )
    with pytest.raises(ValueError, match="only frozen structural artifact"):
        check(frozen)


def test_runtime_input_and_parameter_binding_refuses_substitution(
    frozen, tmp_path
):
    """An unrelated frozen file or changed runtime bundle cannot authorize data."""
    from types import SimpleNamespace

    from populace_dynamics.track_a_v2.manifest import runtime_parameter_bundle

    source = tmp_path / "invented-source.txt"
    source.write_text("INVENTED DATA - NOT A COMPARISON\n")
    source_record = file_record(source, root=ROOT)
    inputs = SimpleNamespace(
        cohort=SimpleNamespace(
            source_provenance={
                "psid_data_dir": str(tmp_path),
                "psid_files_sha256": {source.name: source_record["sha256"]},
            }
        ),
        params={"rate": 0.5},
        baseline={"rate": 0},
        di_rates={"rate": 0},
        population_mortality={"rate": 0},
        claiming_pmf={("female", 2008): {67: 1}},
    )
    actual = runtime_parameter_bundle(inputs)
    frozen["hash_manifest"]["parameter_bundles"]["runtime"] = {
        "bundle": actual,
        "sha256": object_sha256(actual),
    }
    with pytest.raises(ValueError, match="runtime input absent"):
        check(frozen).validate_inputs(inputs)
    frozen["hash_manifest"]["inputs"][
        "invented-population-source"
    ] = source_record
    check(frozen).validate_inputs(inputs)
    inputs.params["rate"] = 0.6
    with pytest.raises(ValueError, match="effective runtime parameter"):
        check(frozen).validate_inputs(inputs)


@pytest.mark.parametrize("entry", ["registered", "structural_count"])
def test_script_refusal_does_not_load_inputs(
    entry, frozen, monkeypatch, tmp_path
):
    """Entry preflight failure is ordered before all real input loading."""
    import importlib

    script = importlib.import_module(f"scripts.track_a_v2_{entry}")
    request = tmp_path / "protocol.json"
    request.write_text(json.dumps(frozen))
    loaded = []
    monkeypatch.setattr(
        script, "load_registered_inputs", lambda *args: loaded.append(1)
    )
    with pytest.raises(ValueError, match="issue #42"):
        script.main(
            [
                "--registration-pointer",
                "invalid",
                "--registered-commit",
                COMMIT,
                "--protocol",
                str(request),
                "--protocol-sha256",
                object_sha256(frozen),
                "--output",
                frozen["output"],
            ]
        )
    assert loaded == []
    assert not Path(frozen["output"]).exists()


@pytest.mark.parametrize("entry", ["registered", "structural_count"])
def test_interrupted_loader_writes_refusal_artifact(
    entry, frozen, monkeypatch, tmp_path
):
    """An interruption after exclusive creation leaves a recorded refusal."""
    import importlib

    script = importlib.import_module(f"scripts.track_a_v2_{entry}")
    checked = check(frozen)
    monkeypatch.setattr(script, "preflight", lambda **kwargs: checked)

    def interrupted(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(script, "load_registered_inputs", interrupted)
    request = tmp_path / "invented-protocol.json"
    request.write_text(json.dumps(frozen))
    status = script.main(
        [
            "--registration-pointer",
            POINTER,
            "--registered-commit",
            COMMIT,
            "--protocol",
            str(request),
            "--protocol-sha256",
            object_sha256(frozen),
            "--output",
            frozen["output"],
        ]
    )
    artifact = json.loads(Path(frozen["output"]).read_text())
    assert status == 2
    assert artifact["attempt"]["status"] == "refused"
    assert artifact["attempt"]["refusal"] == "KeyboardInterrupt"
    assert set(artifact) == {"header", "attempt", "preflight"}
    if entry == "registered":
        assert artifact["attempt"]["uncomputed_rows"] == list(
            protocol.FROZEN_ROWS
        )
        assert artifact["attempt"]["counters"] == {}
    else:
        assert artifact["attempt"]["uncomputed_draws"] == list(range(20))


@pytest.mark.parametrize(
    "extra", ["benefits", "weight_sums", "weighted_totals", "tabulations"]
)
def test_structural_script_refuses_extra_artifact_outputs(
    extra, frozen, tmp_path, monkeypatch
):
    """Intended injected outcome fields never escape the structural artifact."""
    from scripts import track_a_v2_structural_count as script

    artifact, _ = bind_invented_structural_attempt(frozen, tmp_path)
    artifact[extra] = {"invented": 1}
    frozen = structural_protocol(frozen)
    checked = check(frozen, mode="structural")
    monkeypatch.setattr(script, "preflight", lambda **kwargs: checked)
    monkeypatch.setattr(
        script, "load_registered_inputs", lambda *args: object()
    )
    monkeypatch.setattr(
        script, "run_structural", lambda *args, **kwargs: artifact
    )
    request = tmp_path / "invented-structural.json"
    request.write_text(json.dumps(frozen))
    status = script.main(
        [
            "--registration-pointer",
            POINTER,
            "--registered-commit",
            COMMIT,
            "--protocol",
            str(request),
            "--protocol-sha256",
            object_sha256(frozen),
            "--output",
            frozen["output"],
        ]
    )
    written = json.loads(Path(frozen["output"]).read_text())
    assert status == 2
    assert extra not in written
    assert "only frozen structural artifact" in written["attempt"]["refusal"]
    assert set(written) == {"header", "attempt", "preflight"}


def test_structural_script_runs_invented_weighted_projection_end_to_end(
    frozen, tmp_path, monkeypatch
):
    """d603 permits weighted transitions; only frozen counts reach the file."""
    from dataclasses import replace

    from populace_dynamics.cola_track_a import benefits, invented
    from populace_dynamics.engine import di_entitlement
    from populace_dynamics.track_a_v2 import structural
    from populace_dynamics.track_a_v2.invented import invented_inputs
    from populace_dynamics.track_a_v2.manifest import INVENTED_HEADER
    from populace_dynamics.track_a_v2.structural_inputs import (
        prepare_structural_cohort,
    )
    from scripts import track_a_v2_structural_count as script

    frozen = structural_protocol(frozen)
    monkeypatch.setattr(protocol, "git_output", lambda root, *a: fake_git(*a))
    inputs = invented_inputs(seed=7)
    inputs = replace(
        inputs,
        cohort=prepare_structural_cohort(
            invented.invented_psid2010_inputs(seed=7),
            data_provenance="invented",
        ),
    )
    loaded = []

    def load_invented(checked):
        assert checked.mode == "structural"
        assert checked.protocol_sha256 == object_sha256(frozen)
        assert Path(frozen["output"]).exists()
        loaded.append(True)
        return inputs

    weighted_calls = []
    unchanged_weighted_transition = di_entitlement._net_of_di_origin

    def weighted_transition(*args, **kwargs):
        weighted_calls.append(True)
        return unchanged_weighted_transition(*args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("structural projection requested benefits")

    monkeypatch.setattr(benefits._Calculator, "_level", forbidden)
    monkeypatch.setattr(script, "load_registered_inputs", load_invented)
    monkeypatch.setattr(
        di_entitlement, "_net_of_di_origin", weighted_transition
    )
    request = tmp_path / "invented-structural.json"
    request.write_text(json.dumps(frozen))
    status = script.main(
        [
            "--registration-pointer",
            POINTER,
            "--registered-commit",
            COMMIT,
            "--protocol",
            str(request),
            "--protocol-sha256",
            object_sha256(frozen),
            "--output",
            frozen["output"],
        ]
    )
    written = json.loads(Path(frozen["output"]).read_text())
    assert loaded == [True]
    assert len(weighted_calls) == 20 * 20
    assert status == 0
    assert written["header"] == INVENTED_HEADER
    assert written["attempt"]["status"] == "completed"
    assert written["attempt"]["completed_draws"] == list(range(20))
    structural.validate_structural_artifact(written)
    assert set(written["counts"]) == set(protocol.STRUCTURAL_OUTPUTS)
    assert set(written) == {
        "header",
        "protocol_sha256",
        "attempt",
        "count_units",
        "counts",
        "preflight",
    }


def test_structural_loader_requires_frozen_protocol_before_loading(
    monkeypatch,
):
    """d603 removes no §11 input-binding or pre-execution prerequisite."""
    from populace_dynamics.cohorts import psid2010

    def forbidden(*args, **kwargs):
        raise AssertionError("population load occurred before freeze")

    monkeypatch.setattr(psid2010, "load_psid2010_inputs", forbidden)
    checked = protocol.PreflightRecord(
        COMMIT, SPECIFICATION_SHA256, POINTER, "0" * 64, "structural"
    )
    with pytest.raises(ValueError, match="fully frozen protocol"):
        protocol.load_registered_inputs(checked)


@pytest.mark.parametrize(
    "field",
    [
        "implementation_commit",
        "specification_sha256",
        "registration_pointer",
        "procedure",
        "attempt_policy",
        "authorization",
        "permitted_outputs",
    ],
)
def test_structural_protocol_requires_pre_execution_record(frozen, field):
    """The structural exception still requires its own complete frozen record."""
    frozen = structural_protocol(frozen)
    del frozen[field]
    with pytest.raises(ValueError):
        check(frozen, mode="structural")
