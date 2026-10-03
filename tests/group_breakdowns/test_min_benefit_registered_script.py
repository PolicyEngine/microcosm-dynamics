"""The exercise-4 group-breakdown entry point refuses every other state.

INVENTED DATA - NOT A COMPARISON.  Unit tier: no PSID file, committed
artifact or policyengine-us checkout is read.  The "committed parent" is
written to a temporary directory: the registered computation run once on
``min_benefit_track_m.invented_psid``'s frames, marked as read from files
(an INVENTED file name and hash, as ``tests/min_benefit_track_m/
test_registered_run_script.py`` marks them), under Registration 17's
pointer, with the bindings the preflight checks.  ``git``, the Track M
parameter loader, the environment resolver and the COLA history are
stand-ins; every PSID loader is INVENTED.

Stated and tested:

* the preflight refuses a pointer that is not an issue #42 comment,
  Registration 17's own pointer, a short commit, another ``HEAD``, a
  dirty tree, an existing output or sidecar, other parent bytes, and a
  parent that is not Registration 17's run on the M1 specification of
  this commit;
* before any PSID read: other parameter pins and another environment
  (Python, numpy, pandas, scipy, the policyengine-us revision) refuse;
* a parent with one committed cell moved by one unit in the last place
  refuses after the re-execution, before the group-attribute loader is
  called, and nothing is written;
* the registered state writes the artifact and its sidecar exclusively,
  with Track M's labels, the post hoc labels and the reproduction record.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.group_breakdowns import common
from populace_dynamics.group_breakdowns import min_benefit as mb
from populace_dynamics.min_benefit_track_m import (
    COVERED_EARNINGS_DISCLOSURE,
    OUTPUT_LABELS,
    invented,
    invented_psid,
)
from populace_dynamics.min_benefit_track_m.evaluation import PSID_FILES
from populace_dynamics.min_benefit_track_m.tabulation import REGISTERED_REAL

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-9"
)
COMMIT = "c" * 40
PINS = {"pinned": "INVENTED"}
#: An INVENTED environment, as Track A's resolver records one.
ENVIRONMENT = {
    "python": "3.0.0-INVENTED",
    "platform": "INVENTED",
    "packages": {"numpy": "0-INVENTED", "pandas": "0", "scipy": "0"},
    "policyengine_us_parameters": {"revision": "INVENTED"},
}


def _script():
    path = ROOT / "scripts" / "run_min_benefit_groups_registered.py"
    spec = importlib.util.spec_from_file_location("_g4c_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT = _script()


def _git(head: str = COMMIT, porcelain: str = ""):
    def fake(*args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return head
        if args == ("status", "--porcelain"):
            return porcelain
        raise AssertionError(args)

    return fake


class _Cola(dict):
    provenance = {"kind": "INVENTED"}


@pytest.fixture(scope="module")
def stand_ins():
    params, cola = invented.invented_parameters()
    frames = invented_psid.invented_cohort_inputs(seed=5, n_family_units=30)
    marked = dataclasses.replace(
        frames,
        provenance={
            **frames.provenance,
            "psid_files_sha256": {"INVENTED.txt": "0" * 64},
        },
    )
    cola = _Cola(cola)
    run = mb.reexecute_track_m(
        marked,
        params,
        cola_rates=cola,
        data_provenance=REGISTERED_REAL,
        registration_pointer=mb.PARENT_REGISTRATION_POINTER,
        provenance_kind=PSID_FILES,
        source={"cola_history": dict(cola.provenance)},
    )
    document = common.json_normalized(dict(run.result))
    document.update(
        specification={
            "sha256": mb.PARENT_SPECIFICATION_SHA256,
            "version": "m1-ratified-1",
        },
        checks={"parameter_pins": dict(PINS)},
        run={"registered_commit": mb.PARENT_REGISTERED_COMMIT},
    )
    return SimpleNamespace(
        params=params, cola=cola, frames=marked, document=document
    )


def _write_parent(directory: Path, document: dict, environment=None):
    path = directory / "parent_v1.json"
    path.write_text(json.dumps(document, indent=2) + "\n")
    digest = common.file_sha256(path)
    path.with_suffix(".env.json").write_text(
        json.dumps(
            {
                "artifact": path.name,
                "artifact_sha256": digest,
                "environment": environment or ENVIRONMENT,
            }
        )
    )
    return path, digest


def _minimal_parent(**changes) -> dict:
    document = {
        "registration_pointer": mb.PARENT_REGISTRATION_POINTER,
        "specification": {"sha256": mb.PARENT_SPECIFICATION_SHA256},
        "run": {"registered_commit": mb.PARENT_REGISTERED_COMMIT},
    }
    document.update(changes)
    return document


def _preflight(tmp_path, document=None, **kwargs):
    path, digest = _write_parent(tmp_path, document or _minimal_parent())
    arguments = dict(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "out" / "groups_posthoc_v1.json",
        git=_git(),
        parent_path=path,
        parent_sha256=digest,
    )
    arguments.update(kwargs)
    return SCRIPT.preflight(**arguments)


# =========================================================================
# Preflight
# =========================================================================
def test_the_registered_state_passes_preflight(tmp_path):
    state = _preflight(tmp_path)
    assert state["head"] == COMMIT
    assert state["binding"]["registered_commit"] == mb.PARENT_REGISTERED_COMMIT
    assert not (tmp_path / "out").exists()


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
        ({"registration_pointer": None}, "issue #42"),
        (
            {"registration_pointer": mb.PARENT_REGISTRATION_POINTER},
            "not Registration 17's",
        ),
        ({"registered_commit": "abc123"}, "full 40-hex"),
        ({"git": _git(head="d" * 40)}, "is not the registered commit"),
        ({"git": _git(porcelain=" M src/x.py")}, "clean"),
        ({"parent_sha256": "0" * 64}, "not the committed"),
    ],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        _preflight(tmp_path, **kwargs)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("suffix", [".json", ".env.json"])
def test_an_existing_output_or_sidecar_is_refused(tmp_path, suffix):
    output = tmp_path / "out" / "groups_posthoc_v1.json"
    output.parent.mkdir()
    existing = output.with_suffix(suffix)
    existing.write_text("{}")
    with pytest.raises(ValueError, match="one-shot"):
        _preflight(tmp_path, output=output)
    assert existing.read_text() == "{}"


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        (
            {"registration_pointer": POINTER},
            "not Registration 17's artifact",
        ),
        ({"run": {"registered_commit": "e" * 40}}, "not 2e4e08be"),
        (
            {"specification": {"sha256": "f" * 64}},
            "another M1 specification",
        ),
    ],
)
def test_a_parent_other_than_registration_17s_is_refused(
    tmp_path, changes, match
):
    with pytest.raises(ValueError, match=match):
        _preflight(tmp_path, _minimal_parent(**changes))


def test_a_changed_m1_specification_is_refused(tmp_path):
    other = tmp_path / "other_specification.md"
    other.write_text("not the M1 specification\n")
    with pytest.raises(ValueError, match="changed since Registration 17"):
        _preflight(tmp_path, specification_path=other)


@settings(max_examples=60, deadline=None)
@given(st.text(max_size=120))
def test_property_any_other_pointer_is_refused(pointer):
    if re.fullmatch(
        r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
        r"#issuecomment-\d+",
        pointer,
    ):
        return
    with pytest.raises(ValueError, match="issue #42"):
        SCRIPT.preflight(
            registration_pointer=pointer,
            registered_commit=COMMIT,
            output=Path("never-written-by-the-preflight.json"),
            git=_git(),
        )


@settings(max_examples=60, deadline=None)
@given(st.text(alphabet="0123456789abcdef", min_size=40, max_size=40))
def test_property_any_other_head_is_refused(head):
    if head == COMMIT:
        return
    with pytest.raises(ValueError, match="not the registered commit"):
        SCRIPT.preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=Path("never-written-by-the-preflight.json"),
            git=_git(head=head),
        )


@settings(max_examples=40, deadline=None)
@given(st.text(min_size=1, max_size=40).filter(lambda t: t != ""))
def test_property_any_dirty_tree_is_refused(porcelain):
    with pytest.raises(ValueError, match="clean"):
        SCRIPT.preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=Path("never-written-by-the-preflight.json"),
            git=_git(porcelain=porcelain),
        )


# =========================================================================
# Pre-PSID checks
# =========================================================================
def test_the_environment_fields_are_the_reproductions():
    assert SCRIPT.ENVIRONMENT_FIELDS == (
        "python",
        "packages.numpy",
        "packages.pandas",
        "packages.scipy",
        "policyengine_us_parameters.revision",
    )


def test_the_parent_environment_passes():
    record = SCRIPT.check_environment(
        copy.deepcopy(ENVIRONMENT), {"environment": ENVIRONMENT}
    )
    assert record["matches_parent"] is True
    assert set(record["fields"]) == set(SCRIPT.ENVIRONMENT_FIELDS)
    assert isinstance(record["gil_disabled_this_run"], bool)


def _with(environment: dict, dotted: str, value) -> dict:
    out = copy.deepcopy(environment)
    node = out
    keys = dotted.split(".")
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    return out


@pytest.mark.parametrize("field", SCRIPT.ENVIRONMENT_FIELDS)
def test_any_other_environment_field_is_refused(field):
    with pytest.raises(ValueError, match=re.escape(field)):
        SCRIPT.check_environment(
            _with(ENVIRONMENT, field, "other"), {"environment": ENVIRONMENT}
        )
    with pytest.raises(ValueError, match=re.escape(field)):
        SCRIPT.check_environment(
            ENVIRONMENT, {"environment": _with(ENVIRONMENT, field, None)}
        )


def test_the_platform_is_recorded_not_compared():
    record = SCRIPT.check_environment(
        {**ENVIRONMENT, "platform": "elsewhere"}, {"environment": ENVIRONMENT}
    )
    assert record["platform_this_run"] == "elsewhere"


def test_other_parameter_pins_are_refused():
    parent = common.CommittedArtifact(
        document={"checks": {"parameter_pins": dict(PINS)}}
    )
    assert SCRIPT.check_parameter_pins(dict(PINS), parent) == PINS
    with pytest.raises(ValueError, match="parameter_pins"):
        SCRIPT.check_parameter_pins({"pinned": "other"}, parent)


def test_every_composed_file_exists_and_is_hashed():
    paths = SCRIPT.composed_paths()
    assert "scripts/run_min_benefit_groups_registered.py" in paths
    assert "src/populace_dynamics/group_breakdowns/min_benefit.py" in paths
    assert "src/populace_dynamics/group_breakdowns/common.py" in paths
    assert "src/populace_dynamics/min_benefit_track_m/cohort.py" in paths
    assert "src/populace_dynamics/ss/statutory_aime.py" in paths
    digests = SCRIPT.source_sha256()
    assert set(digests) == set(paths)
    assert all(re.fullmatch(r"[0-9a-f]{64}", d) for d in digests.values())


def test_the_header_carries_every_label_and_the_disclosure():
    for label in (*OUTPUT_LABELS, *common.POST_HOC_LABELS):
        assert label in SCRIPT.REGISTERED_HEADER
    assert COVERED_EARNINGS_DISCLOSURE in SCRIPT.REGISTERED_HEADER
    assert "Publishes regardless of outcome" in SCRIPT.REGISTERED_HEADER


def test_the_default_output_is_a_new_artifact_beside_the_parent():
    assert SCRIPT.DEFAULT_OUTPUT == mb.OUTPUT_ARTIFACT_PATH
    assert mb.OUTPUT_ARTIFACT_PATH.parent == mb.PARENT_ARTIFACT_PATH.parent
    assert mb.OUTPUT_ARTIFACT_PATH.name == (
        mb.PARENT_ARTIFACT_PATH.stem.removesuffix("_v1")
        + "_groups_posthoc_v1.json"
    )


def test_main_refuses_without_a_pointer(capsys):
    with pytest.raises(SystemExit):
        SCRIPT.main(["--registered-commit", COMMIT])
    assert "--registration-pointer" in capsys.readouterr().err


# =========================================================================
# execute(): the order and the writes
# =========================================================================
class _Spy:
    def __init__(self, inner=None):
        self.calls: list = []
        self.inner = inner

    def __call__(self, *args):
        self.calls.append(args)
        if self.inner is None:
            raise AssertionError("called")
        return self.inner(*args)


def _execute(tmp_path, stand_ins, document, **overrides):
    path, digest = _write_parent(tmp_path, document)
    output = tmp_path / "out" / "groups_posthoc_v1.json"
    arguments = dict(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=output,
        argv=["--registration-pointer", POINTER],
        git=_git(),
        track_m_script=SimpleNamespace(
            check_runnable=lambda: None,
            committed_parameters=lambda block: (stand_ins.params, dict(PINS)),
        ),
        environment=lambda **_: copy.deepcopy(ENVIRONMENT),
        load_cola=lambda: stand_ins.cola,
        load_cohort_inputs=lambda: stand_ins.frames,
        load_side_frame=mb.invented_group_attribute_loader(
            stand_ins.frames, seed=1
        ),
        parent_path=path,
        parent_sha256=digest,
    )
    arguments.update(overrides)
    return output, SCRIPT.execute(**arguments)


def test_a_moved_cell_refuses_before_any_group_attribute(tmp_path, stand_ins):
    """The orchestrator's order test: a parent whose MS0 share moved by
    one unit in the last place is refused after a real re-execution of
    the registered computation, before the group-attribute loader is
    called, and neither the artifact nor its sidecar is written."""

    document = copy.deepcopy(stand_ins.document)
    cells = document["rows"]["MS0"]["tabulation"]["cells"]
    index = next(i for i, cell in enumerate(cells) if cell["defined"])
    cells[index]["share_percent"] = math.nextafter(
        cells[index]["share_percent"], math.inf
    )
    side_frames = _Spy()
    reads = _Spy(lambda: stand_ins.frames)
    with pytest.raises(common.ReproductionMismatchError) as error:
        _execute(
            tmp_path,
            stand_ins,
            document,
            load_side_frame=side_frames,
            load_cohort_inputs=reads,
        )
    assert len(reads.calls) == 1
    assert side_frames.calls == []
    assert f"tabulation.cells[{index}].share_percent" in str(error.value)
    assert not (tmp_path / "out").exists()


def test_another_environment_refuses_before_the_cohort_is_read(
    tmp_path, stand_ins
):
    reads = _Spy()
    with pytest.raises(ValueError, match="packages.numpy"):
        _execute(
            tmp_path,
            stand_ins,
            stand_ins.document,
            environment=lambda **_: _with(
                ENVIRONMENT, "packages.numpy", "9.9.9"
            ),
            load_cohort_inputs=reads,
        )
    assert reads.calls == []
    assert not (tmp_path / "out").exists()


def test_other_parameter_pins_refuse_before_the_cohort_is_read(
    tmp_path, stand_ins
):
    reads = _Spy()
    with pytest.raises(ValueError, match="parameter_pins"):
        _execute(
            tmp_path,
            stand_ins,
            stand_ins.document,
            track_m_script=SimpleNamespace(
                check_runnable=lambda: None,
                committed_parameters=lambda block: (
                    stand_ins.params,
                    {"pinned": "other"},
                ),
            ),
            load_cohort_inputs=reads,
        )
    assert reads.calls == []


def test_a_missing_component_refuses_before_the_parameters(
    tmp_path, stand_ins
):
    def missing():
        raise RuntimeError("the Track M pipeline is not built")

    def never(block):
        raise AssertionError("parameters read")

    with pytest.raises(RuntimeError, match="not built"):
        _execute(
            tmp_path,
            stand_ins,
            stand_ins.document,
            track_m_script=SimpleNamespace(
                check_runnable=missing, committed_parameters=never
            ),
        )


def test_the_registered_state_writes_the_artifact_and_sidecar(
    tmp_path, stand_ins
):
    """INVENTED stand-ins through the whole registered path: the artifact
    and its sidecar are created exclusively and carry every label."""

    output, artifact = _execute(tmp_path, stand_ins, stand_ins.document)
    written = json.loads(output.read_text())
    assert written == common.json_normalized(artifact)
    sidecar = json.loads(output.with_suffix(".env.json").read_text())
    assert sidecar["artifact"] == output.name
    assert sidecar["artifact_sha256"] == common.file_sha256(output)
    assert sidecar["environment"] == ENVIRONMENT
    assert next(iter(written)) == "header"
    assert written["header"] == SCRIPT.REGISTERED_HEADER
    assert written["data_provenance"] == REGISTERED_REAL
    assert written["registration_pointer"] == POINTER
    assert written["registration"]["pointer"] == POINTER
    assert written["labels"] == [*OUTPUT_LABELS, *common.POST_HOC_LABELS]
    assert written["breakdown"]["registration_pointer"] == POINTER
    assert written["reads_comparator_values"] is False
    assert written["publishes_regardless"] is True
    assert written["blind"] is False and written["scored"] is False
    assert written["reproduction"]["identical"] is True
    assert written["reproduction"][
        "reexecuted_under_registration_pointer"
    ] == (mb.PARENT_REGISTRATION_POINTER)
    assert written["consistency_with_registered_cells"]["identical"] is True
    assert written["checks"]["parameter_pins"] == PINS
    assert written["checks"]["environment"]["matches_parent"] is True
    assert written["run"]["registered_commit"] == COMMIT
    assert written["run"]["git_clean"] is True
    assert set(written["code_sha256"]) == set(SCRIPT.composed_paths())
    assert written["parent"]["registered_commit"] == (
        mb.PARENT_REGISTERED_COMMIT
    )
    # One shot: a second run on the same output is refused by the
    # preflight, and the first artifact is unchanged.
    before = output.read_bytes()
    with pytest.raises(ValueError, match="one-shot"):
        _execute(tmp_path, stand_ins, stand_ins.document)
    assert output.read_bytes() == before
