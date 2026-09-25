"""The Track M one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed: only the preflight,
the parameter pins and the pipeline guard of
``scripts/run_track_m_registered.py`` run, with a fake ``git`` and a
ratified, unblocked copy of the committed block built in memory.
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
    """The committed block ratified and unblocked, as the registered
    commit's block must be: status and version ratified, ``blocked_by``
    empty."""

    ratified = json.loads(json.dumps(spec.m1_parameter_block()))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    ratified["blocked_by"] = []
    return ratified


def _without(block: dict, key: str) -> dict:
    return {name: value for name, value in block.items() if name != key}


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
        # The committed draft (m1-draft-2), read from the document.
        ({"specification": None}, "authorizes no real-data run"),
        (
            {"specification": {**_ratified(), "version": "m1-draft-3"}},
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
        # A ratified block that still names a blocker authorizes nothing,
        # nor does one without the list.
        (
            {
                "specification": {
                    **_ratified(),
                    "blocked_by": ["beneficiary_cohort_m4"],
                }
            },
            "still blocked by",
        ),
        (
            {"specification": _without(_ratified(), "blocked_by")},
            "no blocked_by",
        ),
        # The statistic and the uncertainty are held to the tabulation.
        (
            {
                "specification": {
                    **_ratified(),
                    "uncertainty": {
                        **_ratified()["uncertainty"],
                        "draws": 20,
                    },
                }
            },
            "uncertainty",
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
        "still-blocked",
        "no-blocked-by-list",
        "uncertainty-differs",
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
    ]
    with pytest.raises(RuntimeError, match="not built"):
        script.check_runnable()
    with pytest.raises(NotImplementedError, match="M3-M5"):
        script.run_pipeline(None, registration_pointer=POINTER)
    # one registration-pointer pattern, shared with the tabulation guard
    from populace_dynamics.min_benefit_track_m import tabulation

    assert script.REGISTRATION_POINTER is tabulation.REGISTRATION_POINTER


def test_the_parameters_must_be_the_files_the_block_records():
    script = _script()
    block = spec.m1_parameter_block()
    qc = {"sha256": block["sources"]["quarter_of_coverage_amounts"]["sha256"]}
    census = {"sha256": block["sources"]["census_thresholds"]["sha256"]}
    assert script.check_parameter_pins(
        block, quarter_of_coverage=qc, thresholds=census
    ) == {
        "quarter_of_coverage": qc["sha256"],
        "census_thresholds": census["sha256"],
    }
    with pytest.raises(ValueError, match="quarter_of_coverage"):
        script.check_parameter_pins(
            block, quarter_of_coverage={"sha256": "0" * 64}, thresholds=census
        )
    with pytest.raises(ValueError, match="census_thresholds"):
        script.check_parameter_pins(
            block, quarter_of_coverage=qc, thresholds={"sha256": "0" * 64}
        )
    unrecorded = json.loads(json.dumps(block))
    del unrecorded["sources"]["census_thresholds"]["sha256"]
    with pytest.raises(ValueError, match="records no SHA-256"):
        script.check_parameter_pins(
            unrecorded, quarter_of_coverage=qc, thresholds=census
        )


def test_main_refuses_before_any_parameter_or_psid_read(tmp_path, monkeypatch):
    """Past the preflight, a missing component stops the run before the
    parameters load, and nothing is written."""

    script = _script()
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})

    def never(*args, **kwargs):
        raise AssertionError("loaded parameters before check_runnable")

    monkeypatch.setattr(script, "committed_parameters", never)
    monkeypatch.setattr(script, "run_pipeline", never)
    output = tmp_path / "run.json"
    with pytest.raises(RuntimeError, match="not built"):
        script.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--output",
                str(output),
            ]
        )
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_main_pins_parameters_before_the_computation(tmp_path, monkeypatch):
    """With every component present (as if M3-M5 existed), the parameter
    pins and the environment come before the computation, which refuses
    today; nothing is written."""

    script = _script()
    calls = []
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})
    monkeypatch.setattr(script, "missing_components", lambda: [])

    def parameters(block):
        calls.append(("parameters", block["version"]))
        return _Parameters(), {"pinned": "yes"}

    def environment(**kwargs):
        calls.append(("environment", kwargs["ssa_parameters_revision"]))
        return {}

    monkeypatch.setattr(script, "committed_parameters", parameters)
    monkeypatch.setattr(script, "_environment", environment)
    output = tmp_path / "run.json"
    with pytest.raises(NotImplementedError, match="M3-M5"):
        script.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--output",
                str(output),
            ]
        )
    assert calls == [
        ("parameters", spec.m1_parameter_block()["version"]),
        ("environment", "INVENTED"),
    ]
    assert not output.exists()


class _Parameters:
    class params:
        pe_us_revision = "INVENTED"


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


def test_the_header_carries_every_label_and_the_disclosure():
    script = _script()
    for label in script.OUTPUT_LABELS:
        assert label in script.REGISTERED_HEADER
    assert script.COVERED_EARNINGS_DISCLOSURE in script.REGISTERED_HEADER
