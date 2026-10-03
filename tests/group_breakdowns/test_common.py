"""INVENTED DATA tests of parent identity and one-shot registration guards.

All JSON documents and checkout states below are invented.  No committed
outcome artifact or microdata is opened.  The static tier classifier assigns
artifact because the registration tests name temporary runs JSON paths.
"""

import hashlib
import json
import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from populace_dynamics.group_breakdowns.common import (
    POSTHOC_LABELS,
    GroupBreakdownRefusal,
    assert_exact_cells,
    assert_sha256,
    environment,
    preflight,
    write_artifact_pair,
)

INVENTED_POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-123456789"
)
INVENTED_COMMIT = "a" * 40
_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)
_JSON = st.recursive(
    _SCALARS,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(), children, max_size=4),
    ),
    max_leaves=12,
)


def _invented_git(*args):
    return INVENTED_COMMIT if args == ("rev-parse", "HEAD") else ""


def _preflight(tmp_path, **overrides):
    arguments = {
        "registration_pointer": INVENTED_POINTER,
        "registered_commit": INVENTED_COMMIT,
        "output": tmp_path / "runs" / "invented_groups_posthoc_v1.json",
        "root": tmp_path,
        "git": _invented_git,
    }
    arguments.update(overrides)
    return preflight(**arguments)


@given(_JSON)
def test_exact_identity_after_json_round_trip(invented):
    """Every finite invented JSON tree reproduces all of its leaves."""

    restored = json.loads(json.dumps(invented, allow_nan=False))
    checked = assert_exact_cells(invented, restored)
    assert checked.compared_leaf_cells >= 0
    assert checked.absolute_tolerance == checked.relative_tolerance == 0.0


@given(_JSON, _JSON)
def test_identity_differential_against_canonical_json(left, right):
    """The independent JSON representation has the same exact semantics."""

    same = json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False
    )
    if same:
        assert_exact_cells(left, right)
    else:
        with pytest.raises(GroupBreakdownRefusal):
            assert_exact_cells(left, right)


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_one_binary64_step_never_gets_a_summation_tolerance(value):
    changed = math.nextafter(value, math.inf)
    with pytest.raises(GroupBreakdownRefusal):
        assert_exact_cells(
            {"invented_rate": value}, {"invented_rate": changed}
        )


@pytest.mark.parametrize(
    ("committed", "recomputed"),
    [
        (0.0, -0.0),
        (True, 1),
        (1, 1.0),
        ({"x": None}, {}),
        ({}, {"x": None}),
        ([1], [1, 2]),
        (float("nan"), float("nan")),
        (float("inf"), float("inf")),
        ({1: "x"}, {1: "x"}),
        (object(), object()),
    ],
)
def test_structural_and_nonfinite_mismatches_refuse(committed, recomputed):
    with pytest.raises(GroupBreakdownRefusal):
        assert_exact_cells(committed, recomputed)


def test_mapping_order_and_json_array_semantics():
    check = assert_exact_cells(
        {"a": (1, 2), "b": "x"}, {"b": "x", "a": [1, 2]}
    )
    assert check.compared_leaf_cells == 3


def test_mismatch_reports_path_without_cell_values():
    with pytest.raises(GroupBreakdownRefusal) as caught:
        assert_exact_cells({"invented": [123]}, {"invented": [456]})
    assert "cells.invented[0]" in str(caught.value)
    assert "123" not in str(caught.value)
    assert "456" not in str(caught.value)


def test_labels_state_the_post_hoc_report_only_status():
    assert POSTHOC_LABELS == (
        "registered, one-shot, post hoc, not blind",
        "report-only",
    )


def test_preflight_returns_bound_new_pair(tmp_path):
    result = _preflight(tmp_path)
    assert result.git_head == result.registered_commit == INVENTED_COMMIT
    assert result.git_clean
    assert result.output_path.name == "invented_groups_posthoc_v1.json"
    assert result.sidecar_path.name == "invented_groups_posthoc_v1.env.json"
    assert not result.output_path.exists()
    assert not result.sidecar_path.exists()


@pytest.mark.parametrize(
    "pointer",
    [
        "",
        INVENTED_POINTER.replace("/42#", "/41#"),
        INVENTED_POINTER.replace("https://", "http://"),
        INVENTED_POINTER.replace("microcosm-dynamics", "other-project"),
        INVENTED_POINTER + "?other=1",
        INVENTED_POINTER + "\n",
        INVENTED_POINTER.replace("#issuecomment-", "#discussioncomment-"),
    ],
)
def test_registration_pointer_refuses_before_git(tmp_path, pointer):
    def must_not_call_git(*args):
        pytest.fail("invalid pointer must refuse before reading git state")

    with pytest.raises(GroupBreakdownRefusal, match="issue #42"):
        _preflight(
            tmp_path, registration_pointer=pointer, git=must_not_call_git
        )


@pytest.mark.parametrize("commit", ["", "a" * 39, "A" * 40, "g" * 40])
def test_registered_commit_must_be_full_lowercase_sha(tmp_path, commit):
    with pytest.raises(GroupBreakdownRefusal, match="40-hex"):
        _preflight(tmp_path, registered_commit=commit)


def test_registered_commit_must_equal_head(tmp_path):
    with pytest.raises(GroupBreakdownRefusal, match="HEAD"):
        _preflight(tmp_path, registered_commit="b" * 40)


@given(st.text(min_size=1).filter(lambda value: bool(value.strip())))
def test_any_dirty_status_refuses_before_writing(status):
    """A tracked or untracked status has no permitted silent exception."""

    def dirty_git(*args):
        return INVENTED_COMMIT if args == ("rev-parse", "HEAD") else status

    with pytest.raises(GroupBreakdownRefusal, match="clean"):
        preflight(
            registration_pointer=INVENTED_POINTER,
            registered_commit=INVENTED_COMMIT,
            output=Path("invented_groups_posthoc_v1.json"),
            root=Path("INVENTED-NONEXISTENT-CHECKOUT"),
            git=dirty_git,
        )


@pytest.mark.parametrize(
    "relative",
    [
        "invented_groups_posthoc_v1.json",
        "runs/invented.json",
        "runs/subdirectory/invented_groups_posthoc_v1.json",
        "runs/../invented_groups_posthoc_v1.json",
        "runs/.invented_groups_posthoc_v1.json",
    ],
)
def test_output_must_be_a_named_artifact_in_checkout_runs(tmp_path, relative):
    with pytest.raises(GroupBreakdownRefusal, match="output must be"):
        _preflight(tmp_path, output=Path(relative))


@pytest.mark.parametrize("sidecar", [False, True])
def test_either_existing_member_blocks_registration(tmp_path, sidecar):
    path = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    path.parent.mkdir()
    if sidecar:
        path = path.with_suffix(".env.json")
    path.write_text("INVENTED existing bytes", encoding="utf-8")
    with pytest.raises(GroupBreakdownRefusal, match="one-shot"):
        _preflight(tmp_path)
    assert path.read_text(encoding="utf-8") == "INVENTED existing bytes"


def test_symlinked_runs_cannot_escape_checkout(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (tmp_path / "runs").symlink_to(target, target_is_directory=True)
    with pytest.raises(GroupBreakdownRefusal, match="symlink"):
        _preflight(tmp_path)


def test_dangling_sidecar_symlink_blocks_registration(tmp_path):
    output = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    output.parent.mkdir()
    output.with_suffix(".env.json").symlink_to(tmp_path / "absent")
    with pytest.raises(GroupBreakdownRefusal, match="one-shot"):
        _preflight(tmp_path)


def test_write_pair_binds_the_exact_artifact_bytes(tmp_path):
    output = tmp_path / "invented.json"
    written = write_artifact_pair(
        output=output,
        artifact={"header": "INVENTED DATA - NOT A COMPARISON", "x": 0.0},
        environment={"python": "INVENTED VERSION"},
    )
    assert written == (output, output.with_suffix(".env.json"))
    sidecar = json.loads(written[1].read_text(encoding="utf-8"))
    assert sidecar["artifact"] == output.name
    assert (
        sidecar["artifact_sha256"]
        == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert sidecar["environment"] == {"python": "INVENTED VERSION"}


@pytest.mark.parametrize("sidecar", [False, True])
def test_write_collision_preserves_existing_member_and_removes_new(
    tmp_path, sidecar
):
    output = tmp_path / "invented.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    existing.write_text("INVENTED original bytes", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_artifact_pair(output=output, artifact={"x": 1}, environment={})
    assert existing.read_text(encoding="utf-8") == "INVENTED original bytes"
    absent = output if sidecar else output.with_suffix(".env.json")
    assert not absent.exists()


@pytest.mark.parametrize("in_environment", [False, True])
def test_nonfinite_json_refuses_before_either_file_is_created(
    tmp_path, in_environment
):
    output = tmp_path / "invented.json"
    artifact = {} if in_environment else {"x": float("nan")}
    env = {"x": float("inf")} if in_environment else {}
    with pytest.raises(ValueError):
        write_artifact_pair(output=output, artifact=artifact, environment=env)
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_failed_sidecar_open_rolls_back_new_artifact(tmp_path, monkeypatch):
    output = tmp_path / "invented.json"
    original_open = Path.open

    def failing_open(path, *args, **kwargs):
        if path == output.with_suffix(".env.json"):
            raise OSError("INVENTED storage failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="INVENTED storage failure"):
        write_artifact_pair(output=output, artifact={"x": 1}, environment={})
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()


def test_environment_delegates_to_track_a_resolver(tmp_path):
    script = tmp_path / "scripts" / "run_track_a_registered.py"
    script.parent.mkdir()
    script.write_text(
        "def _environment(*, ssa_parameters_revision):\n"
        "    return {'delegated_revision': ssa_parameters_revision}\n"
        "def main():\n"
        "    raise AssertionError('registered main must not run')\n",
        encoding="utf-8",
    )
    assert environment(ssa_parameters_revision="INVENTED", root=tmp_path) == {
        "delegated_revision": "INVENTED"
    }


def test_sha_pin_refuses_changed_invented_artifact(tmp_path):
    path = tmp_path / "invented.json"
    path.write_bytes(b"INVENTED file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert assert_sha256(path, digest) == digest
    path.write_bytes(b"INVENTED changed file")
    with pytest.raises(GroupBreakdownRefusal, match="SHA-256 mismatch"):
        assert_sha256(path, digest)


@pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "g" * 64])
def test_sha_pin_requires_full_lowercase_sha_before_file_read(
    tmp_path, digest
):
    with pytest.raises(GroupBreakdownRefusal, match="64-hex"):
        assert_sha256(tmp_path / "absent", digest)
