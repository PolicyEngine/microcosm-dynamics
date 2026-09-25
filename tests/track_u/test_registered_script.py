"""The Track U registered one-shot entry point refuses every other state.

No PSID file is read and no statistic is computed: only the preflight
guards of ``scripts/run_track_u_registered.py`` run, with a fake ``git``
and hand-built specification headers, plus one run of ``main`` whose
preflight is replaced to show the threshold refusal comes before any PSID
read.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u import rows

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40
#: A hand-built header of a ratified, complete block (not the committed
#: specification, which is a draft).
RATIFIED = {
    "status": "ratified_frozen",
    "version": "u1-ratified-1",
    "threshold": {"capture_status": "captured"},
    "blocked_by": [],
    "claim_class": {"accepted": "track_u", "decision": "d189"},
}


def _script():
    path = ROOT / "scripts" / "run_track_u_registered.py"
    spec = importlib.util.spec_from_file_location("_track_u_registered", path)
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


def _arguments(tmp_path, **overrides):
    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        "specification": RATIFIED,
    }
    arguments.update(overrides)
    return arguments


def test_the_registered_state_passes(tmp_path):
    assert _script().preflight(**_arguments(tmp_path)) == {"head": COMMIT}


@pytest.mark.parametrize(
    ("overrides", "match"),
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
        (
            {"specification": {**RATIFIED, "status": "draft_for_referee"}},
            "authorizes no run",
        ),
        (
            {"specification": {**RATIFIED, "version": "u1-draft-3"}},
            "authorizes no run",
        ),
        (
            {"specification": {**RATIFIED, "status": "not yet ratified"}},
            "authorizes no run",
        ),
        (
            {
                "specification": {
                    **RATIFIED,
                    "rows": {"U2-F": {"awaiting": "the fallback rule"}},
                }
            },
            "awaited",
        ),
        (
            {
                "specification": {
                    **RATIFIED,
                    "claim_class": {"awaiting": "d189"},
                }
            },
            "awaited",
        ),
        (
            {
                "specification": {
                    **RATIFIED,
                    "blocked_by": ["census_thresholds_not_captured"],
                }
            },
            "blocked",
        ),
        (
            {
                "specification": {
                    **RATIFIED,
                    "threshold": {"capture_status": "not_captured"},
                }
            },
            "captured",
        ),
    ],
    ids=[
        "pointer",
        "other-issue",
        "issue-not-comment",
        "short-sha",
        "wrong-head",
        "dirty-tree",
        "draft-status",
        "draft-version",
        "negated-status",
        "row-awaiting",
        "claim-awaiting",
        "blocked-by",
        "thresholds-not-captured",
    ],
)
def test_non_registered_states_are_refused(tmp_path, overrides, match):
    with pytest.raises(ValueError, match=match):
        _script().preflight(**_arguments(tmp_path, **overrides))


def test_the_committed_specification_authorizes_no_run(tmp_path):
    block = rows.specification_block()
    with pytest.raises(ValueError, match="authorizes no run"):
        _script().check_specification_ratified(block)
    # even with a ratified header, the committed draft still awaits
    # decisions and is blocked
    header = copy.deepcopy(block)
    header.update(status="ratified_frozen", version="u1-ratified-1")
    with pytest.raises(ValueError, match="awaited"):
        _script().check_specification_ratified(header)


@pytest.mark.parametrize("existing", ["run.json", "run.env.json"])
def test_an_existing_artifact_refuses_a_second_shot(tmp_path, existing):
    (tmp_path / existing).write_text("{}")
    with pytest.raises(ValueError, match="one-shot"):
        _script().preflight(**_arguments(tmp_path))


def test_the_artifact_is_created_exclusively(tmp_path):
    target = tmp_path / "run.json"
    _script()._write_new(target, "first\n")
    with pytest.raises(FileExistsError):
        _script()._write_new(target, "second\n")
    assert target.read_text() == "first\n"


def test_the_registration_pointer_and_commit_are_required():
    with pytest.raises(SystemExit):
        _script().main([])
    # the headline row is required too, and only U0 or U0-F
    with pytest.raises(SystemExit):
        _script().main(
            ["--registration-pointer", POINTER, "--registered-commit", COMMIT]
        )
    with pytest.raises(SystemExit):
        _script().main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--headline-row",
                "U1",
            ]
        )


class _Staging:
    """INVENTED stand-in for loaded inputs: only the refused waves."""

    def __init__(self, refused):
        self.wealth_refusals = {wave: "not staged" for wave in refused}


def test_the_headline_row_must_match_the_staging():
    """The fallback rule (specification section 11): the registration
    names the headline row, and the run refuses a staging that gives
    another."""

    script = _script()
    assert script.check_headline("U0", _Staging(())) == "U0"
    assert script.check_headline("U0-F", _Staging((2005, 2007))) == "U0-F"
    with pytest.raises(ValueError, match="staging changed"):
        script.check_headline("U0", _Staging((2005, 2007)))
    with pytest.raises(ValueError, match="staging changed"):
        script.check_headline("U0-F", _Staging(()))


def test_the_registered_headline_must_be_the_one_the_block_records():
    """``u1-draft-6`` records the staged PSID's headline (U0) in the
    section 15 block: the supplements were staged, adjudicated and read
    before the #42 registration, so the fallback rule fixed the headline.
    A registration naming another row is refused whatever the run-time
    staging gives (review of ``dynamics-track-u-wealth-20260925``)."""

    script = _script()
    block = rows.specification_block()
    assert block["population"]["headline"]["staged_psid_headline"] == "U0"
    assert script.check_registered_headline("U0", block) == "U0"
    with pytest.raises(ValueError, match="staged_psid_headline"):
        script.check_registered_headline("U0-F", block)
    # a block without the record (an earlier draft) constrains nothing
    # here; check_headline still holds the registration to the staging
    earlier = copy.deepcopy(block)
    del earlier["population"]["headline"]["staged_psid_headline"]
    assert script.check_registered_headline("U0-F", earlier) == "U0-F"
    assert script.check_registered_headline("U0-F", RATIFIED) == "U0-F"


def test_the_block_headline_is_checked_before_any_psid_read(
    tmp_path, monkeypatch
):
    """With the committed capture and parameters, a registered headline
    the block does not record stops the run before any PSID file is read
    and before anything is written."""

    script = _script()
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})

    def no_psid(**_):
        raise AssertionError("PSID read before the headline check")

    monkeypatch.setattr(script.age67, "load_age67_inputs", no_psid)
    output = tmp_path / "run.json"
    with pytest.raises(ValueError, match="contradicts the specification"):
        script.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--headline-row",
                "U0-F",
                "--output",
                str(output),
            ]
        )
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


@pytest.mark.parametrize(
    "capture, error",
    [
        ("missing", ap.ThresholdsNotCapturedError),
        ("tampered", ap.AdjustedPovertyError),
    ],
)
def test_a_bad_threshold_capture_stops_the_run_before_any_psid_read(
    tmp_path, monkeypatch, capture, error
):
    """The committed capture is pinned; a missing or tampered one is
    refused before any PSID file is read (the loader is pointed at a
    copy, with the committed pin)."""

    script = _script()
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})

    def no_psid(**_):
        raise AssertionError("PSID read before the threshold check")

    monkeypatch.setattr(script.age67, "load_age67_inputs", no_psid)
    path = tmp_path / "census_poverty_thresholds_2004_2012.json"
    if capture == "tampered":
        data = json.loads(ap.THRESHOLDS_PATH.read_text())
        data["weighted_average"]["2012"]["two_65_plus"] += 1
        path.write_text(json.dumps(data, indent=2) + "\n")
    load = ap.load_poverty_thresholds
    monkeypatch.setattr(
        script.ap, "load_poverty_thresholds", lambda: load(path)
    )
    output = tmp_path / "run.json"
    with pytest.raises(error):
        script.main(
            [
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--headline-row",
                "U0-F",
                "--output",
                str(output),
            ]
        )
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_the_script_shares_the_exercise_1_ratification_test():
    from populace_dynamics.estimates import cola_age_profile
    from populace_dynamics.uniform_cut_track_u import runner

    script = _script()
    assert script.UNRATIFIED_MARKERS is cola_age_profile.UNRATIFIED_MARKERS
    assert script.REGISTRATION_POINTER is runner.REGISTRATION_POINTER
    assert script.DEFAULT_OUTPUT == (
        ROOT / "runs" / "replication_boomers2004_uniform_cut_v1.json"
    )
    assert not script.DEFAULT_OUTPUT.exists()
