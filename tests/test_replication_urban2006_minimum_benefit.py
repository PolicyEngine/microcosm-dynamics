"""Pin the exercise-4 registered one-shot artifact (Registration 17).

``runs/replication_urban2006_minimum_benefit_v1.json`` is the output of the
single registered run of DynaSim scorecard exercise 4 (a minimum Social
Security benefit; Table 6's 2025 share of OASDI beneficiaries aged 62 and
older who receive a minimum under options 2-5; Track M).  The run cannot
be reproduced in CI (real PSID data), so these tests pin what was
registered and what the run recorded: the file hash its sidecar binds,
the registration pointer and commit, the registered header and labels,
the ratified specification, Max's rulings, the registered rows and the
unscored d430 sensitivity, and the arithmetic every cell must satisfy
whatever its value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest

from populace_dynamics.min_benefit_track_m import policy

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.json"
SIDECAR = ROOT / "runs" / "replication_urban2006_minimum_benefit_v1.env.json"
REGISTRATION = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5855753783"
)
REGISTERED_COMMIT = "2e4e08beaad1614da089d76b2ad639d0a4884e2e"
ARTIFACT_SHA256 = (
    "b2c2806254618bc8c4cf6c20e652ec2a06ce8a7c05de01a82c151a5d7921cafc"
)
SPECIFICATION_SHA256 = (
    "2e55afc109bcd65d6cf7307b5f52ba91c4c9039891e80388b26214dcce29cc57"
)
ROWS = ["MS0", "MS1", "MS2", "MS3", "MS4", "MS5", "MS6"]
OPTIONS = [2, 3, 4, 5]
CELLS = ["all", "men", "women"]
SENSITIVITY = "own_receipt_reading_d430"


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entry_script():
    path = ROOT / "scripts" / "run_track_m_registered.py"
    spec = importlib.util.spec_from_file_location("_track_m_pin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _all_cells(artifact):
    """Yield (where, cell) for every row's cells and the sensitivity's."""

    for row in ROWS:
        for cell in artifact["rows"][row]["tabulation"]["cells"]:
            yield row, cell
    for cell in artifact["sensitivities"][SENSITIVITY]["tabulation"]["cells"]:
        yield SENSITIVITY, cell


def test_the_sidecar_binds_the_committed_bytes():
    digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    assert digest == ARTIFACT_SHA256
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    assert sidecar["artifact_sha256"] == ARTIFACT_SHA256
    assert sidecar["artifact"] == ARTIFACT.name


def test_the_run_is_the_registered_one_shot(artifact, entry_script):
    # PR #478: the registered header, not the pipeline's null one.
    assert artifact["header"] == entry_script.REGISTERED_HEADER
    assert list(artifact)[0] == "header"
    assert artifact["labels"] == list(entry_script.OUTPUT_LABELS)
    assert artifact["publishes_regardless"] is True
    assert artifact["comparator_seal_opened_before_commit"] is False
    assert artifact["data_provenance"] == "registered_real"
    assert artifact["registration_pointer"] == REGISTRATION
    run = artifact["run"]
    assert run["registration_pointer"] == REGISTRATION
    assert run["registered_commit"] == REGISTERED_COMMIT
    assert run["git_head"] == REGISTERED_COMMIT
    assert run["git_clean"] is True
    assert run["command"] == (
        "python scripts/run_track_m_registered.py --registration-pointer "
        f"{REGISTRATION} --registered-commit {REGISTERED_COMMIT}"
    )


def test_the_specification_is_the_ratified_text(artifact):
    assert artifact["specification"] == {
        "path": "docs/design/minimum_benefits_comparison.md",
        "sha256": SPECIFICATION_SHA256,
        "version": "m1-ratified-1",
        "status": "ratified_frozen",
    }


def test_the_rulings_are_maxs(artifact):
    rulings = artifact["max_rulings"]
    assert {ruling["field"] for ruling in rulings} == set(policy.MAX_RULINGS)
    assert {ruling["decision_record"] for ruling in rulings} == {
        "d219",
        "d279",
        "d280",
        "d430",
    }
    assert "d280" in artifact["disclosure"]


def test_the_headline_rows_and_cells_are_the_registered_ones(artifact):
    assert artifact["headline"]["row"] == "MS0"
    assert artifact["headline"]["option"] == 2
    assert artifact["headline"]["cell"] == "all"
    assert list(artifact["rows"]) == ROWS
    # M1 section 14: each row changes one field from MS0.
    assert {row: artifact["rows"][row]["change_from_ms0"] for row in ROWS} == {
        "MS0": {},
        "MS1": {"policy_year": 2007},
        "MS2": {"order": "cut_after_floor"},
        "MS3": {"counting_rule": "own_worker_pia_only"},
        "MS4": {"window_rule": "after_policy_year"},
        "MS5": {"pia_rule": "benefit_implied"},
        "MS6": {"di_pia_rule": "approximate_pia"},
    }
    for row in ROWS:
        tabulation = artifact["rows"][row]["tabulation"]
        cells = tabulation["cells"]
        # Each row's tabulation marks its own option-2 All cell; the
        # artifact's headline names MS0 as the scored row (M1 section 14).
        assert tabulation["headline"] == {"option": 2, "row": "all"}
        assert [(c["option"], c["row"]) for c in cells if c["headline"]] == [
            (2, "all")
        ]
        assert sorted((c["option"], c["row"]) for c in cells) == sorted(
            (option, name) for option in OPTIONS for name in CELLS
        )
    headline_cell = next(
        cell
        for cell in artifact["rows"]["MS0"]["tabulation"]["cells"]
        if cell["headline"]
    )
    assert (
        headline_cell["share_percent"] == artifact["headline"]["share_percent"]
    )


def test_the_d430_sensitivity_is_registered_and_unscored(artifact):
    sensitivity = artifact["sensitivities"][SENSITIVITY]
    assert sensitivity["scored"] is False
    assert sensitivity["registered"]["decision_record"] == "d430"
    assert sensitivity["registered"]["scored"] is False
    assert sensitivity["registered"]["row"] == "MS0"
    cells = sensitivity["tabulation"]["cells"]
    assert len(cells) == len(OPTIONS) * len(CELLS)
    assert all(cell["scored"] is False for cell in cells)
    assert not any(cell["headline"] for cell in cells)


def test_every_share_is_its_weighted_ratio(artifact):
    """S = 100 * (weighted receiving) / (weighted N), in [0, 100], with
    counts that cannot exceed their cell (M1 section 11)."""

    for where, cell in _all_cells(artifact):
        if not cell["defined"]:
            assert cell["undefined_reason"], (
                where,
                cell["option"],
                cell["row"],
            )
            continue
        share = cell["share_percent"]
        assert 0.0 <= share <= 100.0
        assert 0.0 <= cell["weighted_receiving"] <= cell["weighted_n"]
        assert 0 <= cell["unweighted_receiving"] <= cell["unweighted_n"]
        assert share == pytest.approx(
            100.0 * cell["weighted_receiving"] / cell["weighted_n"],
            rel=1e-12,
            abs=1e-12,
        )


def test_the_floor_uses_the_registered_seeds(artifact):
    for row in ROWS:
        uncertainty = artifact["rows"][row]["tabulation"]["uncertainty"]
        assert uncertainty["floor_seeds"] == [0, 1, 2, 3, 4]
        assert uncertainty["draws"] == 1
    for _, cell in _all_cells(artifact):
        floor = cell["floor"]
        if floor["defined"]:
            assert floor["n_seeds"] + len(floor["dropped_seeds"]) == 5
            assert floor["min"] <= floor["mean"] <= floor["max"]
            assert all(value >= 0.0 for value in floor["values"])


def test_the_sensitivity_changes_only_through_resting_records(artifact):
    """M1 section 11: a person outside the resting set reads the same
    inputs under both readings, so each cell's change equals the share
    moved in less the share moved out, and is at most the resting share."""

    readings = artifact["sensitivities"][SENSITIVITY][
        "receipt_under_both_readings"
    ]
    assert set(readings) == set(CELLS)
    for name, cell in readings.items():
        if not cell["defined"]:
            continue
        resting = cell["resting_weighted_share_percent"]
        assert resting == pytest.approx(
            100.0 * cell["resting_weighted"] / cell["weighted_n"], rel=1e-12
        )
        assert set(cell["options"]) == {str(option) for option in OPTIONS}
        for option, entry in cell["options"].items():
            change = entry["change_percent_points"]
            assert change == pytest.approx(
                entry["share_percent_sensitivity_reading"]
                - entry["share_percent_scored_reading"],
                abs=1e-9,
            )
            assert change == pytest.approx(
                entry["moved_in_percent"] - entry["moved_out_percent"],
                abs=1e-9,
            )
            assert abs(change) <= resting + 1e-9, (name, option)
            assert entry["moved_in_percent"] <= resting + 1e-9
            assert entry["moved_out_percent"] <= resting + 1e-9
    headline = readings["all"]["options"]["2"]
    ms0 = artifact["headline"]["share_percent"]
    assert headline["share_percent_scored_reading"] == pytest.approx(ms0)


def test_no_non_finite_number_was_written():
    def walk(value):
        if isinstance(value, float):
            assert math.isfinite(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(json.loads(ARTIFACT.read_text(encoding="utf-8")))
