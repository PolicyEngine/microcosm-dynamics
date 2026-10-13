"""INVENTED registration-state tests; no checkout or microdata is opened.

Subprocess calls, parameter loaders, parent evidence and outcome writers
are replaced.  Only the entry-point source and invented temporary files
are read.  This module belongs to tier unit.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from populace_dynamics.group_breakdowns.common import (
    GroupBreakdownRefusal,
    RegisteredRun,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTED_COMMIT = "b" * 40
# Required production prefix with an explicitly invented full-SHA suffix.
INVENTED_PARAMETER_HEAD = "a03e82e503" + "0" * 30
INVENTED_OLD_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
INVENTED_NEW_POINTER = INVENTED_OLD_POINTER[:-1] + "2"
INVENTED_ENVIRONMENT = {
    "python": "INVENTED Python version",
    "packages": {
        "numpy": "INVENTED NumPy version",
        "pandas": "INVENTED pandas version",
        "policyengine-social-security-model": "INVENTED project version",
    },
    "project": {"name": "INVENTED project", "version": "INVENTED version"},
}


def _entry():
    source = ROOT / "scripts" / "run_track_u_groups_registered.py"
    spec = importlib.util.spec_from_file_location(
        "_invented_track_u_group_registration", source
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fake_checkout(entry, monkeypatch, *, head, status):
    calls = []
    checkout = Path("INVENTED-NONEXISTENT-PARAMETER-CHECKOUT")
    monkeypatch.setattr(entry.ss_params, "_resolve_pe_us", lambda _: checkout)

    def run(command, **kwargs):
        assert command[:4] == [
            "git",
            "--no-optional-locks",
            "-C",
            str(checkout),
        ]
        operation = tuple(command[4:])
        calls.append(operation)
        if operation == ("rev-parse", "HEAD"):
            return SimpleNamespace(stdout=head + "\n")
        if operation == ("status", "--porcelain", "--untracked-files=no"):
            return SimpleNamespace(stdout=status)
        raise AssertionError(f"unexpected git operation: {operation}")

    monkeypatch.setattr(entry.subprocess, "run", run)
    return calls


def test_clean_full_parameter_head_is_used_independent_of_abbreviation(
    monkeypatch,
):
    entry = _entry()
    calls = _fake_checkout(
        entry, monkeypatch, head=INVENTED_PARAMETER_HEAD, status=""
    )
    assert entry.check_parameter_checkout() == INVENTED_PARAMETER_HEAD
    assert calls == [
        ("rev-parse", "HEAD"),
        ("status", "--porcelain", "--untracked-files=no"),
    ]


@pytest.mark.parametrize(
    "head",
    [
        "a03e82e5",
        "a03e82e503",
        "a03e82e503" + "0" * 29,
        INVENTED_PARAMETER_HEAD + "0",
        "c" * 40,
    ],
)
def test_short_or_wrong_parameter_head_refuses_before_status(
    monkeypatch, head
):
    entry = _entry()
    calls = _fake_checkout(entry, monkeypatch, head=head, status="")
    with pytest.raises(GroupBreakdownRefusal, match="revision a03e82e503"):
        entry.check_parameter_checkout()
    assert calls == [("rev-parse", "HEAD")]


@pytest.mark.parametrize(
    "status",
    [
        " M parameters/INVENTED.yaml\n",
        "M  parameters/INVENTED.yaml\n",
        " D parameters/INVENTED.yaml\n",
    ],
)
def test_dirty_parameter_checkout_refuses_changed_tracked_parameters(
    monkeypatch, status
):
    entry = _entry()
    _fake_checkout(
        entry, monkeypatch, head=INVENTED_PARAMETER_HEAD, status=status
    )
    with pytest.raises(GroupBreakdownRefusal, match="clean tracked files"):
        entry.check_parameter_checkout()


def test_recorded_environment_matches_without_guessing_unrecorded_packages():
    entry = _entry()
    actual = copy.deepcopy(INVENTED_ENVIRONMENT)
    actual["packages"]["scipy"] = "INVENTED unrecorded supplemental version"
    entry.check_environment(actual, INVENTED_ENVIRONMENT)


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ("python", "Python version"),
        ("numpy", "package numpy"),
        ("pandas_absent", "package pandas"),
        ("project_version", "project.version"),
        ("project_name", "project.name"),
    ],
)
def test_environment_version_and_project_mismatch_refuse(change, match):
    entry = _entry()
    actual = copy.deepcopy(INVENTED_ENVIRONMENT)
    if change == "python":
        actual["python"] = "INVENTED changed Python"
    elif change == "numpy":
        actual["packages"]["numpy"] = "INVENTED changed NumPy"
    elif change == "pandas_absent":
        del actual["packages"]["pandas"]
    elif change == "project_version":
        actual["project"]["version"] = "INVENTED changed project version"
    else:
        actual["project"]["name"] = "INVENTED changed project name"
    with pytest.raises(GroupBreakdownRefusal, match=match):
        entry.check_environment(actual, INVENTED_ENVIRONMENT)


def test_spent_original_pointer_refuses_before_inputs_or_environment(
    monkeypatch,
):
    entry = _entry()
    calls = []
    monkeypatch.setattr(entry.common, "preflight", lambda **kwargs: object())
    monkeypatch.setattr(
        entry.groups,
        "load_committed_artifact",
        lambda: {"registration_pointer": INVENTED_OLD_POINTER},
    )

    def forbidden(*args, **kwargs):
        calls.append("read or write after spent pointer")
        raise AssertionError("spent registration must refuse first")

    monkeypatch.setattr(entry.age67, "load_age67_inputs", forbidden)
    monkeypatch.setattr(entry.common, "environment", forbidden)
    monkeypatch.setattr(entry.common, "assert_sha256", forbidden)
    monkeypatch.setattr(entry.common, "write_artifact_pair", forbidden)
    monkeypatch.setattr(entry, "check_parameter_checkout", forbidden)
    with pytest.raises(GroupBreakdownRefusal, match="new issue #42"):
        entry.main(
            [
                "--registration-pointer",
                INVENTED_OLD_POINTER,
                "--registered-commit",
                INVENTED_COMMIT,
            ]
        )
    assert calls == []


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--registration-pointer", INVENTED_NEW_POINTER],
        ["--registered-commit", INVENTED_COMMIT],
    ],
)
def test_missing_required_cli_refuses_before_preflight(
    monkeypatch, capsys, arguments
):
    entry = _entry()

    def forbidden(**kwargs):
        raise AssertionError("missing CLI must not reach preflight")

    monkeypatch.setattr(entry.common, "preflight", forbidden)
    with pytest.raises(SystemExit) as caught:
        entry.main(arguments)
    assert caught.value.code == 2
    assert "required" in capsys.readouterr().err


def _invented_main_state(entry, tmp_path, monkeypatch, actual_environment):
    """A fake parent and pipeline for testing entry-point guard ordering."""

    monkeypatch.setattr(entry, "ROOT", tmp_path)
    output = tmp_path / "invented_groups_posthoc_v1.json"
    state = RegisteredRun(
        registration_pointer=INVENTED_NEW_POINTER,
        registered_commit=INVENTED_COMMIT,
        git_head=INVENTED_COMMIT,
        git_clean=True,
        output_path=output,
        sidecar_path=output.with_suffix(".env.json"),
    )
    monkeypatch.setattr(entry.common, "preflight", lambda **kwargs: state)
    parent_path = tmp_path / "invented_parent.json"
    monkeypatch.setattr(entry.groups, "BASE_ARTIFACT", parent_path)
    parent_path.with_suffix(".env.json").write_text(
        json.dumps({"environment": INVENTED_ENVIRONMENT}), encoding="utf-8"
    )
    checks = {"specification_rows": {"INVENTED": True}, "max_rulings": {}}
    committed = {
        "registration_pointer": INVENTED_OLD_POINTER,
        "checks": checks,
        "specification": {"sha256": "f" * 64},
        "headline": {"row": "INVENTED"},
    }
    monkeypatch.setattr(
        entry.groups, "load_committed_artifact", lambda: committed
    )
    monkeypatch.setattr(
        entry.common, "assert_sha256", lambda path, expected: expected
    )
    monkeypatch.setattr(entry.rows, "specification_block", lambda: {})
    monkeypatch.setattr(
        entry.rows,
        "check_rows_against_block",
        lambda block: checks["specification_rows"],
    )
    monkeypatch.setattr(
        entry.rows,
        "check_rulings_against_block",
        lambda block: checks["max_rulings"],
    )
    parent_source = tmp_path / "scripts" / "run_track_u_registered.py"
    parent_source.parent.mkdir()
    parent_source.write_text(
        "def check_specification_ratified(block):\n"
        "    pass\n"
        "def check_headline(row, inputs):\n"
        "    pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        entry, "check_parameter_checkout", lambda: INVENTED_PARAMETER_HEAD
    )
    monkeypatch.setattr(
        entry.ss_params,
        "load_ssa_parameters",
        lambda: SimpleNamespace(pe_us_revision="a03e82e5"),
    )
    resolver_calls = []

    def resolver(*, ssa_parameters_revision):
        resolver_calls.append(ssa_parameters_revision)
        return actual_environment

    monkeypatch.setattr(entry.common, "environment", resolver)
    return state, resolver_calls


def test_environment_refusal_precedes_psid_loader(tmp_path, monkeypatch):
    entry = _entry()
    actual = copy.deepcopy(INVENTED_ENVIRONMENT)
    actual["packages"]["numpy"] = "INVENTED changed NumPy"
    _, resolver_calls = _invented_main_state(
        entry, tmp_path, monkeypatch, actual
    )
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("cohort or outcome computation")
        raise AssertionError("environment mismatch must refuse first")

    monkeypatch.setattr(entry.age67, "load_age67_inputs", forbidden)
    monkeypatch.setattr(entry.ap, "load_poverty_thresholds", forbidden)
    monkeypatch.setattr(entry.groups, "build_uniform_cut_groups", forbidden)
    monkeypatch.setattr(entry.common, "write_artifact_pair", forbidden)
    with pytest.raises(GroupBreakdownRefusal, match="package numpy"):
        entry.main(
            [
                "--registration-pointer",
                INVENTED_NEW_POINTER,
                "--registered-commit",
                INVENTED_COMMIT,
            ]
        )
    assert resolver_calls == [INVENTED_PARAMETER_HEAD]
    assert calls == []
    assert not (tmp_path / "invented_groups_posthoc_v1.json").exists()


def test_dirty_parameter_refusal_precedes_parameter_and_psid_loaders(
    tmp_path, monkeypatch
):
    entry = _entry()
    _invented_main_state(
        entry, tmp_path, monkeypatch, copy.deepcopy(INVENTED_ENVIRONMENT)
    )
    calls = []

    def dirty_checkout():
        raise GroupBreakdownRefusal(
            "SSA parameter checkout must have clean tracked files"
        )

    def forbidden(*args, **kwargs):
        calls.append("parameter or cohort loader")
        raise AssertionError("dirty parameter checkout must refuse first")

    monkeypatch.setattr(entry, "check_parameter_checkout", dirty_checkout)
    monkeypatch.setattr(entry.ss_params, "load_ssa_parameters", forbidden)
    monkeypatch.setattr(entry.age67, "load_age67_inputs", forbidden)
    monkeypatch.setattr(entry.common, "environment", forbidden)
    monkeypatch.setattr(entry.common, "write_artifact_pair", forbidden)
    with pytest.raises(GroupBreakdownRefusal, match="clean tracked files"):
        entry.main(
            [
                "--registration-pointer",
                INVENTED_NEW_POINTER,
                "--registered-commit",
                INVENTED_COMMIT,
            ]
        )
    assert calls == []
    assert not (tmp_path / "invented_groups_posthoc_v1.json").exists()


def test_full_parameter_head_reaches_environment_provenance(
    tmp_path, monkeypatch
):
    entry = _entry()
    state, resolver_calls = _invented_main_state(
        entry, tmp_path, monkeypatch, copy.deepcopy(INVENTED_ENVIRONMENT)
    )
    monkeypatch.setattr(entry.ap, "load_poverty_thresholds", lambda: object())
    monkeypatch.setattr(
        entry.runner, "committed_parameters", lambda _: object()
    )
    monkeypatch.setattr(entry.age67, "load_age67_inputs", lambda: object())
    monkeypatch.setattr(
        entry.groups,
        "build_uniform_cut_groups",
        lambda *args, **kwargs: {"header": "INVENTED DATA - NOT A COMPARISON"},
    )
    written = []
    monkeypatch.setattr(
        entry.common,
        "write_artifact_pair",
        lambda **kwargs: written.append(kwargs),
    )
    assert (
        entry.main(
            [
                "--registration-pointer",
                INVENTED_NEW_POINTER,
                "--registered-commit",
                INVENTED_COMMIT,
            ]
        )
        == 0
    )
    assert resolver_calls == [INVENTED_PARAMETER_HEAD]
    assert len(written) == 1
    assert written[0]["output"] == state.output_path
    assert written[0]["environment"] == INVENTED_ENVIRONMENT
    assert written[0]["artifact"]["run"]["registration_pointer"] == (
        INVENTED_NEW_POINTER
    )
    assert not state.output_path.exists()
    assert not state.sidecar_path.exists()
