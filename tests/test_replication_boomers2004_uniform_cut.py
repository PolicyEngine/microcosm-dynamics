"""Pin the exercise-2 registered one-shot artifact (Registration 16).

``runs/replication_boomers2004_uniform_cut_v1.json`` is the output of the
single registered run of DynaSim scorecard exercise 2 (a uniform 13
percent Social Security cut; the change in the adjusted poverty rate at
67 for the 1936-45 cohort; Track U).  The run cannot be reproduced in CI
(real PSID data), so these tests pin what was registered and what the run
recorded: the file hash its sidecar binds, the registration pointer and
commit, the ratified specification, Max's rulings, the registered rows,
the input provenance, and the code's structural guarantee that nobody
leaves poverty under the cut.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "replication_boomers2004_uniform_cut_v1.json"
SIDECAR = ROOT / "runs" / "replication_boomers2004_uniform_cut_v1.env.json"
REGISTRATION = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5852808026"
)
REGISTERED_COMMIT = "6a81c7940b14253072af1609232025008e71020f"
ARTIFACT_SHA256 = (
    "48fb6cb108b09e19ed10c32586bd1b0d9521ec7746f693ba0241963ac24a4de3"
)
SPECIFICATION_SHA256 = (
    "830b0ab4c18273563add529fecf21f843eb418996da741d087d785c4f882781f"
)
ROWS = [
    "U0",
    "U1",
    "U2",
    "U3",
    "U4",
    "U5",
    "U0-F",
    "U7",
    "U8",
    "U9",
    "U10",
    "U2-F",
    "U3-F",
    "U4-F",
    "U5-F",
    "U7-F",
    "U8-F",
    "U9-F",
    "U10-F",
]
LABELS = [
    "PSID-realized outcomes (not a projection)",
    "Python income concept (not Axiom)",
    "mechanical incidence",
]


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_the_sidecar_binds_the_committed_bytes():
    digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    assert digest == ARTIFACT_SHA256
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    assert sidecar["artifact_sha256"] == ARTIFACT_SHA256
    assert sidecar["artifact"] == ARTIFACT.name


def test_the_run_is_the_registered_one_shot(artifact):
    assert artifact["publishes_regardless"] is True
    assert artifact["comparator_seal_opened_before_commit"] is False
    assert artifact["data_provenance"] == "registered_real"
    assert artifact["registration_pointer"] == REGISTRATION
    assert artifact["labels"] == LABELS
    run = artifact["run"]
    assert run["registration_pointer"] == REGISTRATION
    assert run["registered_commit"] == REGISTERED_COMMIT
    assert run["git_head"] == REGISTERED_COMMIT
    assert run["git_clean"] is True
    assert "--headline-row U0" in run["command"]


def test_the_specification_is_the_ratified_text(artifact):
    specification = artifact["specification"]
    assert specification["version"] == "u1-ratified-1"
    assert specification["status"] == "ratified_frozen"
    assert specification["sha256"] == SPECIFICATION_SHA256
    checks = artifact["checks"]
    assert checks["specification_rows"]["rows_equal_the_block"] is True
    assert checks["max_rulings"]["rulings_equal"] is True


def test_the_headline_and_rows_are_the_registered_ones(artifact):
    assert artifact["headline"]["row"] == "U0"
    assert artifact["headline"]["wealth_refused_waves"] == []
    assert list(artifact["rows"]) == ROWS
    assert artifact["comparator_column"] == "1936-45"


def test_inputs_were_pinned_and_recorded(artifact):
    provenance = artifact["cohort_provenance"]
    assert provenance["psid_files_bundle_sha256"]
    assert artifact["psid_files_sha256"]
    assert set(artifact["parameters"]) == {"thresholds", "ssi", "life_tables"}


def _cells(tabulation):
    """Yield every (name, cell) pair of a row's tabulation that has a Δ."""

    stack = [("", tabulation)]
    while stack:
        path, node = stack.pop()
        if isinstance(node, dict):
            if "delta" in node and isinstance(node["delta"], (int, float)):
                yield path, node
            for key, value in node.items():
                stack.append((f"{path}/{key}", value))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                stack.append((f"{path}[{index}]", value))


@pytest.mark.parametrize("row", ROWS)
def test_nobody_leaves_poverty_under_the_cut(artifact, row):
    """The cut and the SSI responses never raise a unit's income above
    its baseline, so every recorded change in the poverty rate is at least
    zero (up to floating point)."""

    entry = artifact["rows"][row]
    if entry.get("status") != "computed":
        pytest.skip(f"{row} is {entry.get('status')}")
    cells = list(_cells(entry["tabulation"]))
    assert cells, f"{row} records no cell with a change"
    for path, cell in cells:
        assert cell["delta"] >= -1e-9, (row, path)


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
