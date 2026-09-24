"""The exercise-3 one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed here: only the preflight
guards of ``scripts/run_fra68_registered.py`` run, with a fake ``git`` and
edited copies of the E1 section 21 block.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from populace_dynamics.fra68_track import FRA68Config
from populace_dynamics.fra68_track.runner import e1_parameter_block

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40


def _script():
    path = ROOT / "scripts" / "run_fra68_registered.py"
    spec = importlib.util.spec_from_file_location("_fra68_registered", path)
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


def _ruled() -> dict:
    """The committed block as a ratified, fully ruled version would read."""
    block = copy.deepcopy(e1_parameter_block())
    block["status"] = "ratified_frozen"
    block["version"] = "e1-ratified-1"
    block["decisions_awaiting_max"] = {}
    return block


def test_the_registered_state_passes(tmp_path):
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
        specification=_ruled(),
    )
    assert state == {"head": COMMIT}


def test_the_committed_draft_authorizes_no_run(tmp_path):
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "run.json",
            git=_git(),
        )


def _pending() -> dict:
    block = _ruled()
    block["decisions_awaiting_max"] = {"primary_schedule_id": {}}
    return block


def _referee() -> dict:
    block = _ruled()
    block["status"] = "referee_pass_1"
    return block


def _mismatch() -> dict:
    block = _ruled()
    block["primary_schedule"] = "P1"
    return block


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"registration_pointer": "https://example.org/x"}, "issue #42"),
        (
            {
                "registration_pointer": (
                    "https://github.com/PolicyEngine/microcosm-dynamics/"
                    "issues/420#issuecomment-1"
                )
            },
            "issue #42",
        ),
        (
            {
                "registration_pointer": (
                    "https://github.com/PolicyEngine/microcosm-dynamics/"
                    "issues/42"
                )
            },
            "issue #42",
        ),
        ({"registered_commit": "abc123"}, "full 40-hex"),
        ({"git": _git(head="b" * 40)}, "is not the registered commit"),
        ({"git": _git(porcelain=" M src/x.py")}, "clean"),
        ({"specification": _pending()}, "awaiting Max"),
        ({"specification": _referee()}, "authorizes no real-data run"),
        ({"specification": _mismatch()}, "differ"),
        (
            {"config": FRA68Config(primary_schedule_id="P1")},
            "differ",
        ),
    ],
    ids=[
        "pointer",
        "other-issue",
        "issue-not-comment",
        "short-sha",
        "wrong-head",
        "dirty-tree",
        "pending-decision",
        "referee-status",
        "block-differs",
        "config-differs",
    ],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        "specification": _ruled(),
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
            specification=_ruled(),
        )


def test_the_artifact_is_created_exclusively(tmp_path):
    target = tmp_path / "run.json"
    _script()._write_new(target, "first\n")
    with pytest.raises(FileExistsError):
        _script()._write_new(target, "second\n")
    assert target.read_text() == "first\n"


def test_the_registration_pointer_and_commit_are_required():
    with pytest.raises(SystemExit):
        _script().main([])


def test_the_default_output_is_the_exercise_3_runs_artifact():
    output = _script().DEFAULT_OUTPUT
    assert output == ROOT / "runs" / "replication_urban2010_fra68_v1.json"
