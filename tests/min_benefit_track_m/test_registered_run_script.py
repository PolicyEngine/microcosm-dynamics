"""The Track M one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed: only the preflight and
the pipeline guard of ``scripts/run_track_m_registered.py`` run, with a
fake ``git`` and a ratified copy of the committed block built in memory.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import specification as spec

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40


def _script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    module_spec = importlib.util.spec_from_file_location("_track_m_run", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


def _ratified() -> dict:
    block = spec.m1_parameter_block()
    ratified = json.loads(json.dumps(block))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    ratified["decisions_awaiting_max"] = {}
    ratified["decisions"] = {
        name: {"ruling": entry["proposed_default"]}
        for name, entry in block["decisions_awaiting_max"].items()
    }
    return ratified


def test_the_registered_state_passes_preflight(tmp_path):
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
        specification=_ratified(),
    )
    assert state == {"head": COMMIT}


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
        # The committed draft (m1-draft-1), read from the document.
        ({"specification": None}, "authorizes no real-data run"),
        (
            {"specification": {**_ratified(), "version": "m1-draft-2"}},
            "authorizes no real-data run",
        ),
        (
            {
                "specification": {
                    **_ratified(),
                    "decisions_awaiting_max": {"policy_year": {}},
                }
            },
            "awaiting Max",
        ),
    ],
    ids=[
        "pointer",
        "other-issue",
        "issue-not-comment",
        "short-sha",
        "wrong-head",
        "dirty-tree",
        "committed-draft",
        "draft-version",
        "decision-pending",
    ],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        "specification": _ratified(),
        **kwargs,
    }
    with pytest.raises(ValueError, match=match):
        _script().preflight(**arguments)


def test_an_existing_artifact_is_refused(tmp_path):
    output = tmp_path / "run.json"
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="one-shot"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=output,
            git=_git(),
            specification=_ratified(),
        )


def test_the_artifact_is_created_exclusively(tmp_path):
    script = _script()
    path = tmp_path / "run.json"
    script._write_new(path, "first\n")
    with pytest.raises(FileExistsError):
        script._write_new(path, "second\n")
    assert path.read_text(encoding="utf-8") == "first\n"


def test_the_pipeline_refuses_before_any_psid_read():
    script = _script()
    missing = script.missing_components()
    assert missing == [
        "M3/M4 beneficiary cohort",
        "M5 realized careers",
        "M8 tabulation",
    ]
    with pytest.raises(RuntimeError, match="not built"):
        script.check_runnable()
    with pytest.raises(NotImplementedError, match="M10"):
        script.run_pipeline(None)


def test_main_refuses_outside_the_registered_state(tmp_path):
    with pytest.raises(ValueError):
        _script().main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--output",
                str(tmp_path / "run.json"),
            ]
        )
    assert not (tmp_path / "run.json").exists()


def test_the_header_carries_every_label():
    script = _script()
    for label in script.OUTPUT_LABELS:
        assert label in script.REGISTERED_HEADER
