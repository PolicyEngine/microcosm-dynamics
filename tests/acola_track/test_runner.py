"""Registration 18's whole runner, using invented populations only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics.acola_track import runner
from populace_dynamics.acola_track.config import (
    REGISTRATION_POINTER,
    RUNNABLE_ROWS,
    ACOLAConfig,
)
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.opening import track_a_cohort_sha256
from tests.cola_track_a.test_assembly import (
    invented_cola,
    invented_di_rates,
    invented_mortality,
    invented_params,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ACOLAConfig(draw_indices=(0, 1))


@lru_cache(maxsize=1)
def _cohort():
    return prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7)
        ),
        data_provenance="invented",
        config=CONFIG.track_a_config(),
    )


def _inputs(**changes):
    values = {
        "cohort": _cohort(),
        "params": invented_params(),
        "baseline": invented_cola(),
        "di_rates": invented_di_rates(),
        "population_mortality": invented_mortality(),
        "claiming_pmf": invented.invented_claiming_pmf(),
        "provenance": {"invented_inputs": True},
    }
    values.update(changes)
    return TrackAInputs(**values)


@pytest.fixture(scope="module")
def whole_result():
    return runner.run_acola(_inputs())


def test_whole_invented_run_has_every_row_memo_null_and_label(whole_result):
    assert set(whole_result["rows"]) == set(RUNNABLE_ROWS)
    assert whole_result["deferred_rows"]["C0-D"]["status"] == "deferred"
    assert whole_result["deferred_rows"]["C0-D"]["row"]["mechanism"] == "D"
    assert whole_result["labels"][-1] == "report-only"
    assert whole_result["publishes_regardless"] is True
    assert whole_result["comparator_seal_opened_before_commit"] is False
    assert set(whole_result["nulls"]) >= {"N", "N_model", "N_MINT", "N_M1"}
    assert whole_result["nulls"]["december_null_registered"] is False
    assert (
        whole_result["projection_weights"][
            "n_persons_weight_varies_across_draws"
        ]
        == 0
    )
    for row_id, row in whole_result["rows"].items():
        assert row["status"] == "computed"
        assert row["labels"] == whole_result["labels"]
        assert "equal by construction" in row["membership_note"]
        if row_id.startswith("C"):
            assert row["statistics"]["P"]["mean"] <= 0
            assert len(row["per_draw"]) == 20
            assert set(row["null_gaps"]) == {"P_minus_N", "P_minus_N_model"}
            for cell in row["per_draw"]:
                assert cell["n_base"] == cell["n_reform"]
                assert cell["weight_base"] == cell["weight_reform"]
                assert set(cell["spouse_worker_classes"]) == {
                    "entitled_unconverted_di_worker",
                    "another_worker",
                    "unclassified",
                }
        else:
            assert set(row["bands"]) == {
                "Total",
                "62-69",
                "70-79",
                "80-89",
                "90+",
            }
            assert row["registered_null"] == (
                "N_M1" if row_id == "M1" else "N_MINT"
            )
            for band in row["bands"].values():
                assert len(band["per_draw"]) == 20
                assert len(band["floor_per_seed"]) == 5
                assert len(band["null_gaps"]) == 3
    context = whole_result["context_beneficiary_count"]
    assert context["context_only"] is True
    assert context["scaling_applied"] is False
    assert context["model_mean"] == pytest.approx(
        sum(
            cell["weight_base"]
            for cell in whole_result["rows"]["C0"]["per_draw"]
        )
        / 20
    )
    assert context["trustees"]["beneficiary_count"] > 0


def test_invented_whole_artifact_and_sidecar_only_in_temporary_directory(
    tmp_path, whole_result
):
    spec = importlib.util.spec_from_file_location(
        "_acola_entry_dry", ROOT / "scripts" / "run_acola_registered.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    artifact = {
        "header": "INVENTED DATA - NOT A COMPARISON",
        **whole_result,
        "checks": {"invented_dry_run": True},
        "run": {
            "started": "INVENTED",
            "finished": "INVENTED",
            "registration_pointer": REGISTRATION_POINTER,
            "registered_commit": "a" * 40,
            "git_head": "a" * 40,
            "git_clean": True,
            "command": "INVENTED DATA - pytest temporary-directory dry run",
        },
    }
    output = tmp_path / "invented.json"
    script.write_artifact(output, artifact, {"python": "INVENTED"})
    assert json.loads(output.read_text()) == artifact
    sidecar = json.loads(output.with_suffix(".env.json").read_text())
    assert sidecar["artifact"] == output.name
    assert (
        sidecar["artifact_sha256"]
        == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert sidecar["environment"] == {"python": "INVENTED"}
    for row in artifact["rows"].values():
        if "bands" in row:
            for band in row["bands"].values():
                for summary in band["statistics"].values():
                    if summary["mean"] is None:
                        assert summary["undefined_reason"]
                    if not summary["floor"]["defined"]:
                        assert summary["floor"]["undefined_reason"]


def test_projection_once_per_draw_with_shared_lookups_and_cache(monkeypatch):
    project = runner.legacy._project_population
    emitter = runner.reference_benefit_rows
    calls = []
    projects = []

    def project_spy(*args, **kwargs):
        projects.append(kwargs)
        return project(*args, **kwargs)

    def emit_spy(*args, **kwargs):
        calls.append(
            (kwargs["draw"], id(kwargs["lookups"]), id(kwargs["pia_cache"]))
        )
        return emitter(*args, **kwargs)

    monkeypatch.setattr(runner.legacy, "_project_population", project_spy)
    monkeypatch.setattr(runner, "reference_benefit_rows", emit_spy)
    runner.run_acola(_inputs(), config=CONFIG)
    assert len(projects) == 1
    assert len(calls) == 2 * len(RUNNABLE_ROWS)
    assert len({call[2] for call in calls}) == 1
    for draw in CONFIG.draw_indices:
        assert len({call[1] for call in calls if call[0] == draw}) == 1


def test_same_draw_seed_is_deterministic(whole_result):
    # Recompute seed 5200 independently of the other nineteen draws.
    repeated = runner.run_acola(
        _inputs(), config=ACOLAConfig(draw_indices=(0,))
    )
    for row_id, row in repeated["rows"].items():
        if "bands" in row:
            for band, cell in row["bands"].items():
                assert (
                    cell["per_draw"][0]
                    == whole_result["rows"][row_id]["bands"][band]["per_draw"][
                        0
                    ]
                )
        else:
            assert (
                row["per_draw"][0]
                == whole_result["rows"][row_id]["per_draw"][0]
            )


@pytest.mark.parametrize(
    ("spouse", "linked", "expected"),
    [
        (pd.NA, None, "unclassified"),
        (2, None, "unclassified"),
        (
            2,
            {"di_entitled": True, "di_conversion_year": pd.NA},
            "entitled_unconverted_di_worker",
        ),
        (
            2,
            {"di_entitled": True, "di_conversion_year": 2029},
            "another_worker",
        ),
        (
            2,
            {"di_entitled": False, "di_conversion_year": pd.NA},
            "another_worker",
        ),
    ],
)
def test_spouse_classification_uses_living_link_2030_di_state(
    spouse, linked, expected
):
    states = [{"person_id": 1, "spouse_person_id": spouse}]
    if linked is not None:
        states.append({"person_id": 2, **linked})
    final = pd.DataFrame(states).set_index("person_id", drop=False)
    lookups = SimpleNamespace(
        final=final, alive=lambda pid: pid in final.index
    )
    assert runner.spouse_worker_class(1, lookups) == expected


def test_refused_row_is_published_with_every_null_statistic(monkeypatch):
    emitter = runner.reference_benefit_rows

    def refused(*args, **kwargs):
        if kwargs["row"].row_id == "C0" and kwargs["draw"] == 1:
            raise ValueError("INVENTED refusal")
        return emitter(*args, **kwargs)

    monkeypatch.setattr(runner, "reference_benefit_rows", refused)
    result = runner.run_acola(_inputs(), config=CONFIG)
    row = result["rows"]["C0"]
    assert row["status"] == "refused"
    assert len(row["refusals"]) == 1
    successful, failed = row["per_draw"]
    assert successful["draw"] == 0
    assert successful["P"] < 0
    assert successful["T_base"] > 0
    assert failed["draw"] == 1
    assert failed["T_base"] is None
    assert failed["weight_base"] is None
    for totals in failed["component_totals"].values():
        assert totals == {"base": None, "reform": None}
    for memo in failed["spouse_worker_classes"].values():
        assert all(value is None for value in memo.values())
    assert failed["undefined_reasons"]["T_base"]
    for summary in row["statistics"].values():
        assert summary["mean"] is None
        assert summary["undefined_reason"]
        assert summary["floor"]["mean"] is None
        assert summary["floor"]["undefined_reason"]
    assert result["rows"]["M0"]["status"] == "computed"
    assert result["context_beneficiary_count"]["model_mean"] is None
    json.dumps(result, allow_nan=False)


def test_completed_draw_with_no_recipients_is_explicitly_undefined(
    monkeypatch,
):
    emitter = runner.reference_benefit_rows

    def empty(*args, **kwargs):
        if kwargs["row"].row_id == "C0" and kwargs["draw"] == 0:
            return [], {}
        return emitter(*args, **kwargs)

    monkeypatch.setattr(runner, "reference_benefit_rows", empty)
    result = runner.run_acola(_inputs(), config=CONFIG)
    row = result["rows"]["C0"]
    assert row["status"] == "computed"
    first, second = row["per_draw"]
    assert first["T_base"] == 0
    assert first["n_base"] == 0
    assert first["P"] is None
    assert first["undefined_reasons"]["P"]
    assert second["P"] < 0
    assert row["statistics"]["P"]["mean"] is None
    assert row["statistics"]["P"]["undefined_reason"]
    json.dumps(result, allow_nan=False)


def test_projection_cannot_silently_omit_a_draw(monkeypatch):
    monkeypatch.setattr(
        runner.legacy,
        "_project_population",
        lambda *args, **kwargs: ({0: None}, {}),
    )
    with pytest.raises(ValueError, match="omitted a configured draw"):
        runner.run_acola(_inputs(), config=CONFIG)


def test_reduced_rate_floor_refuses_before_projection(monkeypatch):
    baseline = replace(
        invented_cola(),
        by_determination_year={year: 0.005 for year in range(1979, 2032)},
    )
    monkeypatch.setattr(
        runner.legacy,
        "_project_population",
        lambda *args, **kwargs: pytest.fail("projection ran"),
    )
    with pytest.raises(ValueError, match="REFUSE"):
        runner.run_acola(_inputs(baseline=baseline), config=CONFIG)


def test_registered_pointer_is_required_before_any_real_statistic():
    cohort = replace(_cohort(), data_provenance="registered_real")
    with pytest.raises(ValueError, match="Registration 18's pointer"):
        runner.run_acola(_inputs(cohort=cohort))


def test_registered_real_rejects_partial_run_before_projection():
    cohort = replace(_cohort(), data_provenance="registered_real")
    with pytest.raises(ValueError, match="Registration 18"):
        runner.run_acola(
            _inputs(cohort=cohort),
            config=CONFIG,
            registration_pointer=REGISTRATION_POINTER,
        )


def test_registered_real_requires_committed_parameter_values(monkeypatch):
    cohort = replace(_cohort(), data_provenance="registered_real")
    monkeypatch.setattr(
        runner.legacy,
        "_project_population",
        lambda *args, **kwargs: pytest.fail("projection ran"),
    )
    with pytest.raises(ValueError, match="committed inputs"):
        runner.run_acola(
            _inputs(cohort=cohort), registration_pointer=REGISTRATION_POINTER
        )


@pytest.mark.parametrize("change", ["source", "seal", "labels"])
def test_source_seal_and_labels_are_checked_before_projection(
    monkeypatch, change
):
    cohort = _cohort()
    if change == "source":
        cohort = replace(cohort, source_provenance={"kind": "caller_frames"})
        match = "source provenance"
    elif change == "seal":
        cohort = replace(cohort, diagnostics={"changed": True})
        match = "does not match the seal"
    else:
        cohort = replace(cohort, labels=("WRONG",))
        object.__setattr__(cohort, "seal", track_a_cohort_sha256(cohort))
        match = "must carry the labels"
    monkeypatch.setattr(
        runner.legacy,
        "_project_population",
        lambda *args, **kwargs: pytest.fail("projection ran"),
    )
    with pytest.raises(ValueError, match=match):
        runner.run_acola(_inputs(cohort=cohort), config=CONFIG)


def test_shifted_summary_preserves_undefined_sd_reason():
    summary = {
        "mean": 0.0,
        "sd": None,
        "sample_sd": None,
        "per_draw": [0.0],
        "undefined_reason": None,
        "undefined_reasons": {"sd": "fewer_than_two_draws"},
        "floor": {
            "defined": False,
            "mean": None,
            "undefined_reason": "no usable seed",
        },
    }
    shifted = runner._shifted_summary(summary, {"value": -3.0})
    assert shifted["mean"] == 3.0
    assert shifted["per_draw"] == [3.0]
    assert shifted["sd"] is None
    assert shifted["undefined_reasons"]["sd"] == "fewer_than_two_draws"
    assert shifted["floor"] == summary["floor"]
    assert summary["mean"] == 0.0
    json.dumps(shifted, allow_nan=False)
