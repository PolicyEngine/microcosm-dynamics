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

from populace_dynamics.min_benefit_track_m import rules
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


def test_every_component_exists_and_the_gate_is_what_refuses():
    """M3-M5 are built, so no component is missing; the preflight's
    specification gate refuses the committed draft (above)."""

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


def test_the_computation_refuses_psid_records_under_the_draft(monkeypatch):
    """``run_pipeline`` reads the PSID through M4 and M5 and hands records
    carrying the files' hashes to the pipeline, which refuses them under
    the committed draft before evaluating any record.  The PSID read is
    replaced by INVENTED frames marked as read from files; the refusal is
    the pipeline's."""

    from populace_dynamics.min_benefit_track_m import (
        cohort,
        invented,
        invented_psid,
        pipeline,
    )

    script = _script()
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
    with pytest.raises(Exception, match="does not authorize a real-data"):
        script.run_pipeline(parameters, registration_pointer=POINTER)
    assert evaluated == []


class _Cola(dict):
    provenance = {"kind": "INVENTED"}


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
