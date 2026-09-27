"""The Track M one-shot entry point refuses every non-registered state.

No PSID file is read and no statistic is computed: only the preflight,
the parameter pins and the pipeline guard of
``scripts/run_track_m_registered.py`` run, with a fake ``git``.  The
committed block is ratified and, since the registered-commit edit of
2026-09-27, unblocked, so the preflight passes it at the registered
commit on a clean tree; the refusals of a blocked block are shown on
copies built in memory.  ``test_registered_commit.py`` runs the checks
before the PSID read on the committed block (it needs the oracle's
parameters).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.min_benefit_track_m import rules
from populace_dynamics.min_benefit_track_m import specification as spec

ROOT = Path(__file__).resolve().parents[2]
POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
COMMIT = "a" * 40
#: A path the preflight must never find (and nothing here writes).  It
#: names no evidence directory, so the tier classifier (tests/conftest.py)
#: keeps this module in the unit tier: it reads no committed artifact.
NEVER_WRITTEN = Path(__file__).with_name("never-written-by-the-preflight.out")
#: The blockers ``m1-ratified-1``'s block listed when it was ratified; the
#: registered-commit edit (2026-09-27) dropped both.
BLOCKERS_AT_RATIFICATION = (
    "registration_package_m10_needs_the_comparator_seal_hash",
    "issue_42_registration_absent",
)


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
    empty.  Since the registered-commit edit it equals the committed
    block (tested below)."""

    ratified = json.loads(json.dumps(spec.m1_parameter_block()))
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "m1-ratified-1"
    ratified["blocked_by"] = []
    return ratified


def _blocked(blockers=BLOCKERS_AT_RATIFICATION) -> dict:
    """The committed block listing ``blockers``: by default the block as
    ratified, before the registered-commit edit."""

    return {**_ratified(), "blocked_by": list(blockers)}


def _without(block: dict, key: str) -> dict:
    return {name: value for name, value in block.items() if name != key}


def test_the_committed_block_is_the_ratified_unblocked_block():
    assert spec.m1_parameter_block() == _ratified()
    assert spec.m1_parameter_block()["blocked_by"] == []


@pytest.mark.parametrize(
    "specification", [None, _ratified()], ids=["committed", "copy"]
)
def test_the_registered_state_passes_preflight(tmp_path, specification):
    """The committed block (read from the document when ``specification``
    is None, as the entry script reads it) at the registered commit on a
    clean tree, with an issue #42 comment pointer and no output yet."""

    state = _script().preflight(
        registration_pointer=POINTER,
        registered_commit=COMMIT,
        output=tmp_path / "run.json",
        git=_git(),
        specification=specification,
    )
    assert state == {"head": COMMIT}
    assert not (tmp_path / "run.json").exists()


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
        # The block as ratified, before the registered-commit edit: it
        # still named the registration package and the registration.
        ({"specification": _blocked()}, "still blocked by"),
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
        "blocked-as-ratified",
        "draft-version",
        "decision-pending",
        "still-blocked",
        "no-blocked-by-list",
        "uncertainty-differs",
    ],
)
def test_non_registered_states_are_refused(tmp_path, kwargs, match):
    """Each departure from the registered state is refused, against the
    committed block (``specification=None``: read from the document)
    unless the case supplies another."""

    arguments = {
        "registration_pointer": POINTER,
        "registered_commit": COMMIT,
        "output": tmp_path / "run.json",
        "git": _git(),
        "specification": None,
        **kwargs,
    }
    with pytest.raises(ValueError, match=match):
        _script().preflight(**arguments)


@pytest.mark.parametrize("existing", ["run.json", "run.env.json"])
def test_an_existing_artifact_is_refused(tmp_path, existing):
    """The artifact or its sidecar: either refuses a second shot, under
    the committed block."""

    (tmp_path / existing).write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="one-shot"):
        _script().preflight(
            registration_pointer=POINTER,
            registered_commit=COMMIT,
            output=tmp_path / "run.json",
            git=_git(),
        )
    assert (tmp_path / existing).read_text(encoding="utf-8") == "{}\n"


def _preflight(**changes):
    """The preflight in the registered state, under the committed block,
    with ``changes``; the output is a path that never exists."""

    return _script().preflight(
        **{
            "registration_pointer": POINTER,
            "registered_commit": COMMIT,
            "output": NEVER_WRITTEN,
            "git": _git(),
            **changes,
        }
    )


def _is_42_comment(pointer: str) -> bool:
    from populace_dynamics.min_benefit_track_m import tabulation

    return tabulation.REGISTRATION_POINTER.fullmatch(pointer) is not None


_NOT_A_42_COMMENT = st.one_of(
    st.text(max_size=120),
    st.builds(
        "https://github.com/PolicyEngine/microcosm-dynamics/issues/{}"
        "#issuecomment-{}".format,
        st.integers(min_value=0).filter(lambda issue: issue != 42),
        st.integers(min_value=0),
    ),
    st.builds(
        (POINTER + "{}").format,
        st.text(min_size=1, max_size=20).filter(
            lambda tail: not tail.isdecimal() or not tail.isascii()
        ),
    ),
).filter(lambda pointer: not _is_42_comment(pointer))


@settings(max_examples=150, deadline=None)
@given(_NOT_A_42_COMMENT)
def test_property_any_other_pointer_is_refused(pointer):
    """Invariant: the preflight refuses every pointer that is not an issue
    #42 comment URL, whatever the rest of the state."""

    with pytest.raises(ValueError, match="issue #42"):
        _preflight(registration_pointer=pointer)
    assert not NEVER_WRITTEN.exists()


@settings(max_examples=100, deadline=None)
@given(
    st.text(alphabet="0123456789abcdef", min_size=40, max_size=40).filter(
        lambda head: head != COMMIT
    )
)
def test_property_any_other_head_is_refused(head):
    """Invariant: a ``HEAD`` other than the registered commit is refused."""

    with pytest.raises(ValueError, match="is not the registered commit"):
        _preflight(git=_git(head=head))


@settings(max_examples=100, deadline=None)
@given(st.text(min_size=1, max_size=80))
def test_property_any_dirty_tree_is_refused(porcelain):
    """Invariant: any ``git status --porcelain`` output but the empty
    string (a clean tree) is refused."""

    with pytest.raises(ValueError, match="clean"):
        _preflight(git=_git(porcelain=porcelain))


def test_the_artifact_is_created_exclusively(tmp_path):
    script = _script()
    path = tmp_path / "run.json"
    script._write_new(path, "first\n")
    with pytest.raises(FileExistsError):
        script._write_new(path, "second\n")
    assert path.read_text(encoding="utf-8") == "first\n"


def test_every_component_exists():
    """M3-M5 are built, so no component is missing (the preflight passes
    the committed block at the registered commit, above)."""

    script = _script()
    assert script.missing_components() == []
    script.check_runnable()
    # one registration-pointer pattern, shared with the tabulation guard
    from populace_dynamics.min_benefit_track_m import tabulation

    assert script.REGISTRATION_POINTER is tabulation.REGISTRATION_POINTER


def test_a_missing_component_is_named(monkeypatch):
    script = _script()
    monkeypatch.setattr(
        script,
        "PIPELINE_MODULES",
        {
            **script.PIPELINE_MODULES,
            "M99 absent": "populace_dynamics.min_benefit_track_m.absent",
        },
    )
    assert script.missing_components() == ["M99 absent"]
    with pytest.raises(RuntimeError, match="not built: missing M99 absent"):
        script.check_runnable()


def _marked_psid_read(monkeypatch):
    """Replace the PSID read with INVENTED frames marked as read from
    files, and the COLA history with the invented one; return the
    invented parameters and a list that records any evaluation."""

    from populace_dynamics.min_benefit_track_m import (
        cohort,
        invented,
        invented_psid,
        pipeline,
    )

    frames = invented_psid.invented_cohort_inputs(seed=4, n_family_units=40)
    marked = type(frames)(
        structure_inputs=frames.structure_inputs,
        individual_receipt=frames.individual_receipt,
        family_1993_receipt=frames.family_1993_receipt,
        family_level_receipt=frames.family_level_receipt,
        prior_year_labor=frames.prior_year_labor,
        provenance={"psid_files_sha256": {"INVENTED.txt": "0" * 64}},
    )
    monkeypatch.setattr(cohort, "load_cohort_inputs", lambda **_: marked)
    parameters, cola = invented.invented_parameters()
    monkeypatch.setattr(
        "populace_dynamics.estimates.parameters.load_cola_history",
        lambda: _Cola(cola),
    )
    evaluated = []
    monkeypatch.setattr(
        pipeline, "evaluate", lambda *a, **k: evaluated.append(1)
    )
    return parameters, evaluated


@pytest.mark.parametrize(
    "pointer",
    [
        "https://example.org/x",
        POINTER.replace("/42#", "/420#"),
        "https://github.com/PolicyEngine/microcosm-dynamics/issues/42",
    ],
    ids=["pointer", "other-issue", "issue-not-comment"],
)
def test_the_computation_refuses_psid_records_without_the_42_pointer(
    monkeypatch, pointer
):
    """``run_pipeline`` reads the PSID through M4 and M5 and hands records
    carrying the files' hashes to the pipeline, which refuses them without
    an issue #42 comment pointer before evaluating any record, although
    the committed block now authorizes the run.  The PSID read is
    replaced by INVENTED frames marked as read from files; the refusal is
    the pipeline's."""

    parameters, evaluated = _marked_psid_read(monkeypatch)
    with pytest.raises(Exception, match="registration pointer"):
        _script().run_pipeline(parameters, registration_pointer=pointer)
    assert evaluated == []


def test_the_computation_refuses_psid_records_under_a_blocked_block(
    monkeypatch,
):
    """Were the committed block still blocked (as ratified), the pipeline
    would refuse the records it is handed even with an issue #42 comment
    pointer, before evaluating any record: it reads the committed block
    itself.  The committed block is replaced in memory; the PSID read is
    INVENTED frames marked as read from files."""

    parameters, evaluated = _marked_psid_read(monkeypatch)
    blocked = _blocked()
    monkeypatch.setattr(spec, "m1_parameter_block", lambda *a: blocked)
    with pytest.raises(Exception, match="does not authorize a real-data"):
        _script().run_pipeline(parameters, registration_pointer=POINTER)
    assert evaluated == []


def test_the_computation_passes_d430s_sensitivity(monkeypatch):
    """``run_pipeline`` reads the PSID once and builds that one read
    twice, under the scored reading and under cos d430's sensitivity
    reading, and passes the second as ``own_receipt_sensitivity`` (the
    pipeline refuses a registered run without it).  The PSID read is
    INVENTED frames marked as read from files; the pipeline call is
    captured, not run."""

    from populace_dynamics.min_benefit_track_m import (
        cohort,
        invented,
        invented_psid,
        pipeline,
    )
    from populace_dynamics.min_benefit_track_m import policy as pol

    script = _script()
    frames = invented_psid.invented_cohort_inputs(
        seed=4, n_family_units=40, unknown_or_other_before_62=0.5
    )
    marked = type(frames)(
        structure_inputs=frames.structure_inputs,
        individual_receipt=frames.individual_receipt,
        family_1993_receipt=frames.family_1993_receipt,
        family_level_receipt=frames.family_level_receipt,
        prior_year_labor=frames.prior_year_labor,
        provenance={"psid_files_sha256": {"INVENTED.txt": "0" * 64}},
    )
    reads = []

    def load(**kwargs):
        reads.append(kwargs)
        return marked

    monkeypatch.setattr(cohort, "load_cohort_inputs", load)
    built = []
    build_cohort = cohort.build_cohort

    def build(inputs, **kwargs):
        reading = kwargs.get(
            "own_receipt_reading", pol.OWN_RECEIPT_UNKNOWN_OR_OTHER_IS_OWN
        )
        built.append((inputs, reading))
        return build_cohort(inputs, **kwargs)

    monkeypatch.setattr(cohort, "build_cohort", build)
    parameters, cola = invented.invented_parameters()
    monkeypatch.setattr(
        "populace_dynamics.estimates.parameters.load_cola_history",
        lambda: _Cola(cola),
    )
    seen = {}

    def capture(records, parameters, **kwargs):
        seen.update(kwargs, records=records)
        return {"sensitivities": {pol.OWN_RECEIPT_SENSITIVITY_ID: {}}}

    monkeypatch.setattr(pipeline, "run_track_m", capture)
    out = script.run_pipeline(parameters, registration_pointer=POINTER)
    scored, other = seen["records"], seen["own_receipt_sensitivity"]
    # one PSID read, built under both readings (independent review of
    # 2026-09-26, D2: a second read went undetected)
    assert len(reads) == 1
    assert len(built) == 2
    assert all(inputs is marked for inputs, _ in built)
    assert {reading for _, reading in built} == set(pol.OWN_RECEIPT_READINGS)
    assert seen["data_provenance"] == "registered_real"
    assert (
        scored.own_receipt_reading == pol.OWN_RECEIPT_UNKNOWN_OR_OTHER_IS_OWN
    )
    assert other.own_receipt_reading == (
        pol.OWN_RECEIPT_PRE62_UNKNOWN_OR_OTHER_UNOBSERVED
    )
    assert other.provenance_kind == scored.provenance_kind == "psid_files"
    assert other.source["psid_files_sha256"] == (
        scored.source["psid_files_sha256"]
    )
    assert other.workers != scored.workers
    assert "cohort_structure" in out
    assert (
        "cohort_structure"
        in out["sensitivities"][pol.OWN_RECEIPT_SENSITIVITY_ID]
    )


class _Cola(dict):
    provenance = {"kind": "INVENTED"}


def test_main_publishes_the_sensitivity_in_the_artifact(tmp_path, monkeypatch):
    """The artifact carries ``run_pipeline``'s result whole: d430's
    sensitivity is published under ``sensitivities`` beside the rows
    (independent review of 2026-09-26, D2: dropping it went undetected).
    The preflight, the parameters and the computation are stand-ins; the
    result is INVENTED."""

    from populace_dynamics.min_benefit_track_m import policy as pol

    script = _script()
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})
    monkeypatch.setattr(script, "missing_components", lambda: [])
    monkeypatch.setattr(
        script,
        "committed_parameters",
        lambda block: (_Parameters(), {"pinned": "INVENTED"}),
    )
    monkeypatch.setattr(script, "_environment", lambda **_: {})
    result = {
        "rows": {"MS0": {"INVENTED": True}},
        "sensitivities": {
            pol.OWN_RECEIPT_SENSITIVITY_ID: {
                "scored": False,
                "INVENTED": True,
            }
        },
    }
    monkeypatch.setattr(
        script,
        "run_pipeline",
        lambda parameters, **_: json.loads(json.dumps(result)),
    )
    output = tmp_path / "run.json"
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
    artifact = json.loads(output.read_text())
    assert artifact["sensitivities"] == result["sensitivities"]
    assert artifact["rows"] == result["rows"]
    assert output.with_suffix(".env.json").exists()


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


def test_the_committed_files_pass_the_parameter_pins():
    """The loaders' records of the committed quarter-of-coverage capture
    and Census capture pass the pins against the committed block (the
    test above holds the pins to the block's own values)."""

    from populace_dynamics.min_benefit_track_m import coverage

    script = _script()
    thresholds = rules.load_aged_thresholds().source
    assert script.check_parameter_pins(
        spec.m1_parameter_block(),
        quarter_of_coverage=coverage.load_qc_amounts().source,
        thresholds=thresholds,
    ) == {
        "quarter_of_coverage": coverage.QC_CAPTURE_SHA256,
        "census_thresholds": thresholds["sha256"],
    }


def test_main_refuses_before_any_parameter_or_psid_read(tmp_path, monkeypatch):
    """Past the preflight, a missing component stops the run before the
    parameters load, and nothing is written."""

    script = _script()
    monkeypatch.setattr(script, "preflight", lambda **_: {"head": COMMIT})
    monkeypatch.setattr(script, "missing_components", lambda: ["M99"])

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
    """The parameter pins and the environment come before the
    computation; a refused computation writes nothing."""

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

    def computation(parameters, **kwargs):
        calls.append(("computation", kwargs["registration_pointer"]))
        raise RuntimeError("the computation refuses (stand-in)")

    monkeypatch.setattr(script, "committed_parameters", parameters)
    monkeypatch.setattr(script, "_environment", environment)
    monkeypatch.setattr(script, "run_pipeline", computation)
    output = tmp_path / "run.json"
    with pytest.raises(RuntimeError, match="stand-in"):
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
        ("computation", POINTER),
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
