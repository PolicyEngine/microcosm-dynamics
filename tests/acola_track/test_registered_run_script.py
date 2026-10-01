"""A-COLA preflight and exclusive output tests; no population read."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.acola_track.config import (
    REGISTRATION_POINTER,
    SPECIFICATION_PATH,
    SPECIFICATION_SHA256,
    ACOLAConfig,
)

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "a" * 40


def _script(default_output=None):
    spec = importlib.util.spec_from_file_location(
        "_acola_registered_entry", ROOT / "scripts" / "run_acola_registered.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if default_output is not None:
        module.DEFAULT_OUTPUT = default_output
    return module


def _git(head=COMMIT, porcelain=""):
    def fake(*args):
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def test_committed_specification_and_registered_state_pass(
    tmp_path, monkeypatch
):
    script = _script(tmp_path / "artifact.json")

    def no_data(*args, **kwargs):
        pytest.fail("preflight read population data")

    monkeypatch.setattr(script.psid2010, "load_psid2010_inputs", no_data)
    monkeypatch.setattr(script, "run_acola", no_data)
    state = script.preflight(
        registration_pointer=REGISTRATION_POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "artifact.json",
        git=_git(),
    )
    assert state == {
        "head": COMMIT,
        "specification_sha256": SPECIFICATION_SHA256,
    }


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"registration_pointer": "https://example.org/x"}, "issue #42"),
        (
            {
                "registration_pointer": "https://github.com/PolicyEngine/microcosm-dynamics/issues/420#issuecomment-1"
            },
            "issue #42",
        ),
        (
            {
                "registration_pointer": "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
            },
            "issue #42",
        ),
        (
            {
                "registration_pointer": "https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-1"
            },
            "exact comment URL",
        ),
        ({"registered_commit": "a" * 7}, "40-hex"),
        ({"registered_commit": "z" * 40}, "40-hex"),
        ({"git": _git(head="b" * 40)}, "not the registered commit"),
        ({"git": _git(porcelain=" M src/file.py")}, "clean"),
        ({"git": _git(porcelain="?? untracked.log")}, "clean"),
        ({"config": ACOLAConfig(draw_indices=(0,))}, "Registration 18"),
        ({"config": ACOLAConfig(rows=("C0",))}, "Registration 18"),
        ({"config": ACOLAConfig(annual_reduction=0)}, "Registration 18"),
        ({"config": ACOLAConfig(floor_seeds=(1, 2))}, "Registration 18"),
    ],
)
def test_preflight_refusal_matrix(tmp_path, change, match):
    values = {
        "registration_pointer": REGISTRATION_POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "artifact.json",
        "git": _git(),
    }
    values.update(change)
    with pytest.raises(ValueError, match=match):
        _script(values["output"]).preflight(**values)


def test_changed_specification_is_refused(tmp_path):
    changed = tmp_path / "spec.md"
    changed.write_bytes(
        SPECIFICATION_PATH.read_bytes() + b"\nINVENTED CHANGE\n"
    )
    with pytest.raises(ValueError, match="SHA-256|sha256|binding"):
        _script(tmp_path / "artifact.json").preflight(
            registration_pointer=REGISTRATION_POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "artifact.json",
            git=_git(),
            specification_path=changed,
        )


@pytest.mark.parametrize("sidecar", [False, True])
def test_existing_artifact_or_sidecar_is_one_shot_refusal(tmp_path, sidecar):
    output = tmp_path / "artifact.json"
    occupied = output.with_suffix(".env.json") if sidecar else output
    occupied.write_text("INVENTED existing file")
    with pytest.raises(ValueError, match="one-shot"):
        _script(tmp_path / "artifact.json").preflight(
            registration_pointer=REGISTRATION_POINTER,
            registered_commit=COMMIT,
            output=output,
            git=_git(),
        )


def test_write_new_never_overwrites(tmp_path):
    output = tmp_path / "exclusive.json"
    script = _script()
    script._write_new(output, "first")
    with pytest.raises(FileExistsError):
        script._write_new(output, "second")
    assert output.read_text() == "first"


@pytest.mark.parametrize("field", ["artifact", "environment"])
def test_nonfinite_value_is_rejected_before_either_file_is_written(
    tmp_path, field
):
    output = tmp_path / "nonfinite.json"
    artifact = {"invented": 1}
    environment = {"python": "INVENTED"}
    (artifact if field == "artifact" else environment)["undefined"] = float(
        "nan"
    )
    with pytest.raises(ValueError, match="JSON compliant"):
        _script().write_artifact(output, artifact, environment)
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_undefined_values_and_reasons_serialize(tmp_path):
    output = tmp_path / "undefined.json"
    artifact = {"value": None, "undefined_reason": "INVENTED empty band"}
    _script().write_artifact(output, artifact, {"python": "INVENTED"})
    assert json.loads(output.read_text()) == artifact


def test_default_output_is_the_registered_artifact():
    assert (
        _script().DEFAULT_OUTPUT
        == ROOT / "runs" / "trust_fund_acola_2030_v1.json"
    )


def test_main_requires_registration_arguments():
    with pytest.raises(SystemExit):
        _script().main([])


def test_sidecar_uses_the_existing_environment_resolver():
    environment = (
        _script()
        ._script_module("run_track_a_registered")
        ._environment(ssa_parameters_revision="INVENTED", packages={})
    )
    assert environment["populace_dynamics_source"] == "src/populace_dynamics"
    assert environment["policyengine_us_parameters"]["revision"] == "INVENTED"


def test_preflight_refuses_an_alternate_artifact_path(tmp_path):
    script = _script(tmp_path / "registered.json")
    with pytest.raises(ValueError, match="fixed registered artifact"):
        script.preflight(
            registration_pointer=REGISTRATION_POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "alternate.json",
            git=_git(),
        )
