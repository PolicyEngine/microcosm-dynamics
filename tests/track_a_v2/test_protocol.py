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
    return {
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
