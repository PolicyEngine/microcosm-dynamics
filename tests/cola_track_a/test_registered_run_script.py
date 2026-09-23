"""The registered one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed here: only the preflight
guards of ``scripts/run_track_a_registered.py`` run, with a fake ``git``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40


def _script():
    path = ROOT / "scripts" / "run_track_a_registered.py"
    spec = importlib.util.spec_from_file_location("_registered_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def test_the_registered_state_passes(tmp_path):
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
    )
    assert state == {"head": COMMIT}


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"registration_pointer": "https://example.org/x"}, "issue #42"),
        ({"registered_commit": "abc123"}, "full 40-hex"),
        ({"git": _git(head="b" * 40)}, "is not the registered commit"),
        ({"git": _git(porcelain=" M src/x.py")}, "clean"),
    ],
    ids=["pointer", "short-sha", "wrong-head", "dirty-tree"],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        **kwargs,
    }
    with pytest.raises(ValueError, match=match):
        _script().preflight(**arguments)


@pytest.mark.parametrize("existing", ["run.json", "run.env.json"])
def test_an_existing_artifact_refuses_a_second_shot(tmp_path, existing):
    (tmp_path / existing).write_text("{}")
    with pytest.raises(ValueError, match="one-shot"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "run.json",
            git=_git(),
        )


def test_the_registration_pointer_and_commit_are_required():
    with pytest.raises(SystemExit):
        _script().main([])
