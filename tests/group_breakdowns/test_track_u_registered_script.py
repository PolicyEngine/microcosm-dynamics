"""Track U's actual entry point publishes only to its checked repository.

INVENTED DATA - NOT A COMPARISON. Parent bytes, guards, environment,
parameters, inputs and computed cells are temporary invented stand-ins.
The real registration preflight and exclusive pair writer are exercised.
No PSID file or committed run artifact is read.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from populace_dynamics.group_breakdowns import common

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-9"
)
COMMIT = "c" * 40
ENVIRONMENT = {
    "python": "3.0.0-INVENTED",
    "packages": {"numpy": "0-INVENTED"},
    "project": {"kind": "INVENTED"},
}


def _script():
    path = ROOT / "scripts" / "run_track_u_groups_registered.py"
    spec = importlib.util.spec_from_file_location("_track_u_groups_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = _script()


def test_main_writes_relative_output_under_root_from_another_cwd(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    (root / "scripts").mkdir()
    caller = tmp_path / "caller"
    caller.mkdir()
    sentinel = caller / "runs"
    sentinel.write_text("INVENTED caller file\n")
    monkeypatch.chdir(caller)
    monkeypatch.setattr(SCRIPT, "ROOT", root)

    def git(checked_root, *args):
        assert checked_root == root
        if args == ("rev-parse", "HEAD"):
            return COMMIT
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(common, "_git", git)
    specification = root / "INVENTED-specification.md"
    specification.write_text("INVENTED specification\n")
    block = {"kind": "INVENTED"}
    rows = {"INVENTED": True}
    rulings = {"INVENTED": True}
    committed = {
        "registration_pointer": POINTER.removesuffix("9") + "8",
        "checks": {"specification_rows": rows, "max_rulings": rulings},
        "specification": {"sha256": common.file_sha256(specification)},
        "headline": {"row": "INVENTED"},
    }
    parent_path = root / "runs" / "invented_parent_v1.json"
    parent_path.write_text(json.dumps(committed))
    sidecar_path = parent_path.with_suffix(".env.json")
    sidecar_path.write_text(json.dumps({"environment": ENVIRONMENT}))
    monkeypatch.setattr(SCRIPT.groups, "BASE_ARTIFACT", parent_path)
    monkeypatch.setattr(
        SCRIPT.groups, "BASE_ARTIFACT_SHA256", common.file_sha256(parent_path)
    )
    monkeypatch.setattr(
        SCRIPT, "SIDECAR_SHA256", common.file_sha256(sidecar_path)
    )
    monkeypatch.setattr(
        SCRIPT.groups,
        "load_committed_artifact",
        lambda: copy.deepcopy(committed),
    )
    monkeypatch.setattr(SCRIPT.rows, "specification_block", lambda: block)
    monkeypatch.setattr(
        SCRIPT.rows, "check_rows_against_block", lambda _: rows
    )
    monkeypatch.setattr(
        SCRIPT.rows, "check_rulings_against_block", lambda _: rulings
    )
    monkeypatch.setattr(SCRIPT.rows, "SPECIFICATION_PATH", specification)
    (root / "scripts" / "run_track_u_registered.py").write_text(
        '"""INVENTED parent guards: no data or computation."""\n'
        "def check_specification_ratified(block):\n"
        "    assert block == {'kind': 'INVENTED'}\n"
        "def check_headline(row, inputs):\n"
        "    assert row == 'INVENTED'\n"
        "    assert inputs == {'kind': 'INVENTED'}\n"
    )
    parameters = SimpleNamespace(kind="INVENTED")
    ssa = SimpleNamespace(kind="INVENTED")
    inputs = {"kind": "INVENTED"}
    monkeypatch.setattr(SCRIPT, "check_parameter_checkout", lambda: "a" * 40)
    monkeypatch.setattr(SCRIPT.ss_params, "load_ssa_parameters", lambda: ssa)
    monkeypatch.setattr(
        common, "environment", lambda **_: copy.deepcopy(ENVIRONMENT)
    )
    monkeypatch.setattr(SCRIPT.ap, "load_poverty_thresholds", lambda: {})
    monkeypatch.setattr(
        SCRIPT.runner, "committed_parameters", lambda _: parameters
    )
    monkeypatch.setattr(SCRIPT.age67, "load_age67_inputs", lambda: inputs)
    compute_calls = []

    def compute(actual_inputs, actual_parameters, actual_parent, **kwargs):
        assert actual_inputs is inputs
        assert actual_parameters is parameters
        assert actual_parent == committed
        assert kwargs["lifetime_inputs"].params is ssa
        compute_calls.append(kwargs)
        return {"header": common.INVENTED_DATA_HEADER}

    monkeypatch.setattr(SCRIPT.groups, "build_uniform_cut_groups", compute)
    relative = Path("runs") / "invented_groups_posthoc_v1.json"
    argv = [
        "--registration-pointer",
        POINTER,
        "--registered-commit",
        COMMIT,
        "--output",
        str(relative),
    ]
    assert SCRIPT.main(argv) == 0
    assert len(compute_calls) == 1
    output = root / relative
    written = json.loads(output.read_text())
    assert written["header"] == common.INVENTED_DATA_HEADER
    assert written["run"]["output_path"] == str(relative)
    assert written["run"]["sidecar_path"] == str(
        relative.with_suffix(".env.json")
    )
    output_sidecar = output.with_suffix(".env.json")
    sidecar = json.loads(output_sidecar.read_text())
    assert sidecar["artifact"] == output.name
    assert sidecar["artifact_sha256"] == common.file_sha256(output)
    assert sidecar["environment"] == ENVIRONMENT
    assert capsys.readouterr().out.strip() == str(output)
    assert set(caller.iterdir()) == {sentinel}
    assert sentinel.read_text() == "INVENTED caller file\n"

    before = output.read_bytes(), output_sidecar.read_bytes()
    with pytest.raises(common.GroupBreakdownRefusal, match="one-shot"):
        SCRIPT.main(argv)
    assert len(compute_calls) == 1
    assert (output.read_bytes(), output_sidecar.read_bytes()) == before
    assert set(caller.iterdir()) == {sentinel}
    assert sentinel.read_text() == "INVENTED caller file\n"
