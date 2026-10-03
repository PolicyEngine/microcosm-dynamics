"""INVENTED registration and exclusive-writer checks; no real-data run."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "_projection_group_registration",
    ROOT / "scripts" / "run_projection_groups_registered.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-123456789"
)
COMMIT = "a" * 40


def invented_git(*args):
    """INVENTED clean registered HEAD, without consulting any repository."""
    return COMMIT if args == ("rev-parse", "HEAD") else ""


@pytest.fixture
def specification_spy(monkeypatch):
    calls = []
    monkeypatch.setattr(
        runner,
        "_check_specification",
        lambda *args: calls.append(args),
    )
    return calls


@pytest.mark.parametrize("exercise", ["cola", "fra68"])
def test_valid_preflight_creates_nothing(
    tmp_path, specification_spy, exercise
):
    output = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    state = runner.preflight(
        exercise=exercise,
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=output,
        root=tmp_path,
        git=invented_git,
    )
    assert state == {"head": COMMIT}
    assert len(specification_spy) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "pointer",
    [
        "",
        POINTER.replace("issues/42", "issues/41"),
        POINTER.replace("#issuecomment-", "/comments/"),
        POINTER + "/",
        POINTER + "\n",
        POINTER.replace("https://", "http://"),
    ],
)
def test_bad_pointer_refuses_before_git_or_loaders(tmp_path, pointer):
    def forbidden(*args):
        pytest.fail(
            "git or specification loader called before pointer refusal"
        )

    with pytest.raises(ValueError, match="issue #42"):
        runner.preflight(
            exercise="cola",
            registration_pointer=pointer,
            registered_commit=COMMIT,
            output=tmp_path / "runs" / "invented_groups_posthoc_v1.json",
            root=tmp_path,
            git=forbidden,
        )
    assert list(tmp_path.iterdir()) == []


@given(
    comment_id=st.integers(min_value=0, max_value=10**30),
    corruption=st.sampled_from(["prefix", "suffix", "wrong_issue"]),
)
def test_pointer_near_matches_never_authorize(comment_id, corruption):
    pointer = POINTER.rsplit("-", 1)[0] + f"-{comment_id}"
    if corruption == "prefix":
        pointer = " " + pointer
    elif corruption == "suffix":
        pointer += " "
    else:
        pointer = pointer.replace("issues/42", "issues/420")

    def forbidden(*args):
        pytest.fail("registration near-match reached repository access")

    with pytest.raises(ValueError, match="issue #42"):
        runner.preflight(
            exercise="cola",
            registration_pointer=pointer,
            registered_commit=COMMIT,
            output=Path("INVENTED_UNWRITTEN_OUTPUT.json"),
            git=forbidden,
        )


@pytest.mark.parametrize("commit", ["a" * 39, "a" * 41, "A" * 40, "g" * 40])
def test_full_lowercase_sha_required(tmp_path, specification_spy, commit):
    with pytest.raises(ValueError, match="40-hex"):
        runner.preflight(
            exercise="cola",
            registration_pointer=POINTER,
            registered_commit=commit,
            output=tmp_path / "runs" / "invented_groups_posthoc_v1.json",
            root=tmp_path,
            git=invented_git,
        )
    assert specification_spy == []


@pytest.mark.parametrize(
    "git_result,message",
    [("b" * 40, "HEAD"), (" M invented.txt", "clean")],
)
def test_head_and_clean_tree_are_required(
    tmp_path, specification_spy, git_result, message
):
    def git(*args):
        if args == ("rev-parse", "HEAD"):
            return git_result if message == "HEAD" else COMMIT
        return git_result

    with pytest.raises(ValueError, match=message):
        runner.preflight(
            exercise="cola",
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "runs" / "invented_groups_posthoc_v1.json",
            root=tmp_path,
            git=git,
        )
    assert specification_spy == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("sidecar", [False, True])
def test_preflight_preserves_existing_pair(
    tmp_path, specification_spy, sidecar
):
    output = tmp_path / "runs" / "invented_groups_posthoc_v1.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("INVENTED EXISTING BYTES", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        runner.preflight(
            exercise="cola",
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=output,
            root=tmp_path,
            git=invented_git,
        )
    assert existing.read_text() == "INVENTED EXISTING BYTES"
    assert specification_spy == []


def test_specification_refusal_creates_nothing(tmp_path, monkeypatch):
    def unratified(*args):
        raise ValueError("INVENTED unratified specification")

    monkeypatch.setattr(runner, "_check_specification", unratified)
    with pytest.raises(ValueError, match="unratified"):
        runner.preflight(
            exercise="cola",
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "runs" / "invented_groups_posthoc_v1.json",
            root=tmp_path,
            git=invented_git,
        )
    assert list(tmp_path.iterdir()) == []


def test_new_pair_has_binding_sha256(tmp_path):
    output = tmp_path / "invented.json"
    runner.write_new_pair(
        output,
        {"header": "INVENTED DATA - NOT A COMPARISON", "value": 1.0},
        {"python": "INVENTED"},
    )
    sidecar = json.loads(output.with_suffix(".env.json").read_text())
    assert sidecar["artifact"] == output.name
    assert (
        sidecar["artifact_sha256"]
        == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert output.read_bytes().endswith(b"\n")


@pytest.mark.parametrize("sidecar", [False, True])
def test_exclusive_writer_preserves_racing_existing_file(tmp_path, sidecar):
    output = tmp_path / "invented.json"
    existing = output.with_suffix(".env.json") if sidecar else output
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("INVENTED RACING BYTES", encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner.write_new_pair(output, {"value": 1.0}, {})
    assert existing.read_text() == "INVENTED RACING BYTES"
    assert set(tmp_path.iterdir()) == {existing}


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf")])
@pytest.mark.parametrize("environment", [False, True])
def test_nonfinite_pair_refuses_before_any_write(
    tmp_path, nonfinite, environment
):
    output = tmp_path / "invented.json"
    bad = {"value": nonfinite}
    with pytest.raises(ValueError, match="JSON compliant"):
        runner.write_new_pair(
            output,
            {} if environment else bad,
            bad if environment else {},
        )
    assert list(tmp_path.iterdir()) == []


def test_environment_requires_exact_core_versions():
    invented = {
        "python": "INVENTED 1.0",
        "packages": {"numpy": "1", "pandas": "2", "scipy": "3"},
    }
    runner.check_reproduction_environment(invented, invented, "a03e82e503")
    for package in ("numpy", "pandas", "scipy"):
        changed = {
            **invented,
            "packages": {**invented["packages"], package: "INVENTED CHANGE"},
        }
        with pytest.raises(ValueError, match=package):
            runner.check_reproduction_environment(
                changed, invented, "a03e82e503"
            )
    with pytest.raises(ValueError, match="Python"):
        runner.check_reproduction_environment(
            {**invented, "python": "INVENTED CHANGE"}, invented, "a03e82e503"
        )
    with pytest.raises(ValueError, match="a03e82e503"):
        runner.check_reproduction_environment(invented, invented, "INVENTED")


def test_environment_mismatch_refuses_before_cohort_reader(monkeypatch):
    expected = {
        "python": "INVENTED 1.0",
        "packages": {"numpy": "1", "pandas": "2", "scipy": "3"},
    }

    def forbidden_reader(*args, **kwargs):
        pytest.fail("cohort reader called before environment refusal")

    legacy = SimpleNamespace(
        load_ssa_parameters=lambda: SimpleNamespace(
            pe_us_revision="a03e82e503"
        ),
        _environment=lambda **kwargs: {
            **expected,
            "python": "INVENTED CHANGE",
        },
        psid2010=SimpleNamespace(load_psid2010_inputs=forbidden_reader),
    )
    monkeypatch.setattr(runner, "_script_module", lambda name: legacy)
    with pytest.raises(ValueError, match="Python"):
        runner.build_registered_inputs(
            "cola", object(), parent={}, expected_environment=expected
        )


def test_missing_registration_cli_never_reaches_builder(monkeypatch):
    monkeypatch.setattr(
        runner,
        "build_registered_inputs",
        lambda *args, **kwargs: pytest.fail("real-data builder called"),
    )
    with pytest.raises(SystemExit) as error:
        runner.main(["--exercise", "cola"])
    assert error.value.code == 2


def test_methodology_pin_mismatch_refuses_before_parent_or_builder(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(runner, "preflight", lambda **kwargs: {"head": COMMIT})
    monkeypatch.setattr(runner, "_sha256", lambda path: "INVENTED MISMATCH")

    def forbidden(*args, **kwargs):
        pytest.fail("parent or builder reached before methodology pin refusal")

    monkeypatch.setattr(runner, "_parent", forbidden)
    monkeypatch.setattr(runner, "build_registered_inputs", forbidden)
    with pytest.raises(ValueError, match="methodology specification SHA-256"):
        runner.main(
            [
                "--exercise",
                "cola",
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--output",
                str(tmp_path / "invented.json"),
            ]
        )
    assert list(tmp_path.iterdir()) == []


def test_parent_pointer_cannot_authorize_new_groups(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "preflight", lambda **kwargs: {"head": COMMIT})
    monkeypatch.setattr(
        runner, "_sha256", lambda path: runner.POSTHOC_SPECIFICATION_SHA256
    )
    monkeypatch.setattr(
        runner,
        "_parent",
        lambda exercise: ({"registration_pointer": POINTER}, {}, "SHA"),
    )
    monkeypatch.setattr(
        runner,
        "build_registered_inputs",
        lambda *args, **kwargs: pytest.fail(
            "old pointer reached cohort builder"
        ),
    )
    with pytest.raises(ValueError, match="new issue #42"):
        runner.main(
            [
                "--exercise",
                "cola",
                "--registration-pointer",
                POINTER,
                "--registered-commit",
                COMMIT,
                "--output",
                str(tmp_path / "invented.json"),
            ]
        )
    assert list(tmp_path.iterdir()) == []


def test_mismatched_committed_cell_main_loads_no_attributes_or_writes(
    tmp_path, monkeypatch
):
    """INVENTED parent mismatch exercises the actual common refusal gate."""
    from populace_dynamics.group_breakdowns import cola, common

    result = {
        "rows": {
            "R0": {
                "tabulation": {"groups": [{"cell": {"percent_change": 1.0}}]}
            }
        },
        "draws": {"2011": {"0": {"count": 1}}},
        "registration_pointer": POINTER,
    }
    parent = copy.deepcopy(result)
    parent["rows"]["R0"]["tabulation"]["groups"][0]["cell"][
        "percent_change"
    ] = 2.0
    replay = common.ProjectionReplay(
        exercise="cola",
        result=result,
        benefit_rows={"R0": pd.DataFrame({"person_id": [1]})},
        states={},
    )
    loader_calls = []

    def forbidden_attributes(*args, **kwargs):
        loader_calls.append((args, kwargs))
        pytest.fail("group attributes loaded before committed-cell refusal")

    monkeypatch.setattr(
        common.g1, "load_group_attributes", forbidden_attributes
    )
    monkeypatch.setattr(runner, "preflight", lambda **kwargs: {"head": COMMIT})
    monkeypatch.setattr(
        runner,
        "_sha256",
        lambda path: runner.POSTHOC_SPECIFICATION_SHA256,
    )
    monkeypatch.setattr(
        runner, "_parent", lambda exercise: (parent, {}, "SHA")
    )
    monkeypatch.setattr(
        runner,
        "build_registered_inputs",
        lambda *args, **kwargs: (object(), {}, {}, None),
    )
    monkeypatch.setattr(cola, "reproduce_cola", lambda *args, **kwargs: replay)
    output = tmp_path / "invented_groups.json"
    with pytest.raises(common.ReproductionMismatch, match="percent_change"):
        runner.main(
            [
                "--exercise",
                "cola",
                "--registration-pointer",
                POINTER + "0",
                "--registered-commit",
                COMMIT,
                "--output",
                str(output),
            ]
        )
    assert loader_calls == []
    assert not output.exists()
    assert not output.with_suffix(".env.json").exists()
    assert list(tmp_path.iterdir()) == []
