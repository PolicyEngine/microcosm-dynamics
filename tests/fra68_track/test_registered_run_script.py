"""The exercise-3 one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed here: only the preflight
guards of ``scripts/run_fra68_registered.py`` run, with a fake ``git``, the
committed E1 section 21 block (ratified, ``e1-ratified-1``) and edited
copies of it.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from populace_dynamics.estimates import cola_age_profile
from populace_dynamics.fra68_track import (
    E1_RULINGS,
    MAX_RULINGS,
    FRA68Config,
)
from populace_dynamics.fra68_track import runner as fra68_runner
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
    """The committed block: ratified, with Max's ruling on every field."""
    return copy.deepcopy(e1_parameter_block())


def test_the_committed_block_is_ratified_and_ruled():
    block = _ruled()
    assert block["version"] == "e1-ratified-1"
    assert block["status"] == "ratified_frozen"
    assert "decisions_awaiting_max" not in block
    for name, ruling in MAX_RULINGS.items():
        assert block["decisions"][name]["ruling"] == ruling["ruling"], name


def test_the_registered_state_passes(tmp_path):
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
        specification=_ruled(),
    )
    assert state == {"head": COMMIT}


def test_the_committed_e1_passes_the_preflight(tmp_path):
    # No specification passed: the preflight reads the committed E1.
    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
    )
    assert state == {"head": COMMIT}


def _draft() -> dict:
    # INVENTED: the committed block under the last draft's header.
    block = _ruled()
    block["version"] = "e1-draft-7"
    block["status"] = "draft_refereed_not_ratified"
    return block


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


def _unruled() -> dict:
    block = _ruled()
    del block["decisions"]["claim_class"]
    return block


def _as_filed() -> dict:
    # A ruling on what d188 as filed names alone: d196's fields and the
    # benefit computation years (covered by d188 item (a), not named in
    # it) have no recorded ruling.
    block = _ruled()
    for name, ruling in MAX_RULINGS.items():
        if ruling.get("named_in_d188_as_filed") is False:
            del block["decisions"][name]
    return block


def _ruled_otherwise_in_block_and_config() -> dict:
    # The block edited to another primary, with a configuration that
    # follows it: the code's record of Max's ruling refuses it.
    block = _ruled()
    block["decisions"]["primary_schedule_id"]["ruling"] = "P1"
    return block


def _ruled_otherwise() -> dict:
    block = _ruled()
    block["decisions"]["acceptance_rule"]["ruling"] = "within 1 point"
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
        ({"specification": _draft()}, "authorizes no real-data run"),
        ({"specification": _pending()}, "awaiting Max"),
        ({"specification": _referee()}, "authorizes no real-data run"),
        ({"specification": _mismatch()}, "differ"),
        ({"specification": _unruled()}, "records no ruling"),
        ({"specification": _as_filed()}, "records no ruling"),
        ({"specification": _ruled_otherwise()}, "departs from Max's"),
        (
            {"config": FRA68Config(primary_schedule_id="P1")},
            "departs from Max's",
        ),
        (
            {
                "specification": _ruled_otherwise_in_block_and_config(),
                "config": FRA68Config(primary_schedule_id="P1"),
            },
            "differ from the code's record of Max's rulings",
        ),
    ],
    ids=[
        "pointer",
        "other-issue",
        "issue-not-comment",
        "short-sha",
        "wrong-head",
        "dirty-tree",
        "draft-header",
        "pending-decision",
        "referee-status",
        "block-differs",
        "no-ruling",
        "ruled-as-filed-only",
        "ruled-otherwise",
        "config-departs",
        "block-departs-from-code",
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


#: Header values that never state ratification.  The preflight's former
#: marker-only test (candidate, draft, not_merged, not_ratified, referee
#: as substrings) passed every one of these except the last.
_NOT_RATIFIED = [
    ("status", "pending_ratification"),
    ("status", "unratified"),
    ("status", "not yet ratified"),
    ("status", "proposed"),
    ("status", "Not Ratified"),
    ("status", None),
    ("version", "e1-3"),
    ("status", "ratified_after_referee"),
]


@pytest.mark.parametrize(("field", "value"), _NOT_RATIFIED)
def test_a_header_that_does_not_state_ratification_is_refused(
    tmp_path, field, value
):
    # Regression: the E1 preflight kept its own marker list, weaker than
    # A7's fail-closed test (#454), and let these through.
    block = _ruled()
    block[field] = value
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "run.json",
            git=_git(),
            specification=block,
        )


def test_the_preflight_and_a7_share_one_ratification_test(tmp_path):
    # No marker list of the exercise-3 code's own: the preflight refuses
    # exactly the headers whose tabulation records them as not ratified.
    assert not hasattr(fra68_runner, "UNRATIFIED_MARKERS")
    assert set(E1_RULINGS.extra_unratified_markers) == {"referee"}
    cases = [*_NOT_RATIFIED, ("status", "ratified_frozen")]
    for field, value in cases:
        block = {**_ruled(), field: value}
        record = cola_age_profile.specification_record(
            block, extra_markers=E1_RULINGS.extra_unratified_markers
        )
        try:
            _script().preflight(
                registration_pointer=POINTER,
                registered_commit=COMMIT,
                output=tmp_path / "run.json",
                git=_git(),
                specification=block,
            )
        except ValueError as error:
            assert "authorizes no real-data run" in str(error)
            refused = True
        else:
            refused = False
        assert refused is (not record["ratified"]), (field, value)
        assert refused is bool(E1_RULINGS.unratified_fields(block))
    assert not refused  # the last case, a ratified header, passes


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


def test_the_sidecar_records_every_import_by_its_distribution():
    # Regression: the sidecar looked up fixed distribution names, so the
    # repository ("populace-dynamics") and policyengine-us were recorded as
    # None.  It now uses exercise 1's resolver, which records the
    # distribution that provides each import, the project at the commit
    # and the policyengine-us checkout revision the oracle reads.
    environment = _script()._environment(
        ssa_parameters_revision="INVENTED-REVISION"
    )
    assert None not in environment["packages"].values()
    assert environment["distributions_by_import"]["populace_dynamics"]
    for name in environment["distributions_by_import"]["populace_dynamics"]:
        assert name in environment["packages"]
    assert environment["project"]["name"]
    assert environment["policyengine_us_parameters"]["revision"] == (
        "INVENTED-REVISION"
    )
