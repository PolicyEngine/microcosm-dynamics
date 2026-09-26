"""Pin the exercise-3 registered one-shot artifact (Registration 15).

``runs/replication_urban2010_fra68_v1.json`` is the output of the single
registered run of DynaSim scorecard exercise 3 (the full retirement age
raised to 68; 2030 age profile). Registration 14 was refused before any
artifact was written; Registration 15 reran the reviewed fix. The run
cannot be reproduced in CI (real PSID data, about 30 minutes), so these
tests pin what was registered and what the run recorded: the file hash
its sidecar binds, the registration pointer and commit, the ratified
specification, Max's rulings, the input provenance and the C0 membership
record.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "replication_urban2010_fra68_v1.json"
SIDECAR = ROOT / "runs" / "replication_urban2010_fra68_v1.env.json"
REGISTRATION = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5840600730"
)
REGISTERED_COMMIT = "08a695a43078a7d6415c746c08371c5a6ee8e0ac"
ARTIFACT_SHA256 = (
    "9c768fff17bfd828d16bdca738f92d8487f082ec99cd94ee0c73959bb050746e"
)
ROWS = ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
C0_ROWS = ["F0", "F1", "F2", "F5", "F6", "F7", "F8"]
NAMED_MECHANISM = "spouse_excess_withheld_until_reform_conversion"


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
    run = artifact["run"]
    assert run["registration_pointer"] == REGISTRATION
    assert run["registered_commit"] == REGISTERED_COMMIT
    assert run["git_head"] == REGISTERED_COMMIT
    assert run["git_clean"] is True


def test_the_configuration_is_the_ruled_default(artifact):
    config = artifact["config"]
    assert config["reference_year"] == 2030
    assert config["draw_indices"] == list(range(20))
    assert config["rows"] == ROWS
    assert set(artifact["rows"]) == set(ROWS)
    assert config["primary_schedule_id"] == "P3"
    assert config["acceptance_rule"] is None
    assert config["oracle_fra_schedule_override"] is True


def test_the_specification_is_the_ratified_amendment(artifact):
    assert artifact["specification"] == "urban2010_fra68_exercise3"
    check = artifact["specification_check"]
    assert check["specification_version"] == "e1-ratified-2"
    assert check["specification_status"] == "ratified_frozen"
    assert check["consistent"] is True
    assert check["mismatches"] == []


def test_inputs_were_value_checked_and_labelled(artifact):
    assert artifact["parameter_consistency"]["consistent"] is True
    assert any("not Axiom" in label for label in artifact["labels"])
    assert set(artifact["cohorts"]) == {"2009", "2011"}
    for cohort in artifact["cohorts"].values():
        assert cohort["source_provenance_kind"] == "psid_files"
        provenance = cohort["source_provenance"]
        assert provenance["kind"] == "psid_files"
        assert provenance["psid_files_sha256"]
        assert provenance["content_sha256"]


#: The counts Registration 15 registered in advance from the membership
#: diagnostic: 8 baseline-only rows in each 2011-wave C0 row that carries
#: survivors and spouses, none in F6 (workers only), 1 in F8 (2009 wave).
REGISTERED_DIFFERENCES = {
    "F0": 8,
    "F1": 8,
    "F2": 8,
    "F5": 8,
    "F6": 0,
    "F7": 8,
    "F8": 1,
}


@pytest.mark.parametrize("row", C0_ROWS)
def test_c0_membership_differs_only_through_the_named_mechanism(artifact, row):
    record = artifact["rows"][row]["membership_differences"]
    assert record["classified"] is True
    assert record["not_explained_allowed"] is False
    assert record["n_rows_not_explained"] == 0
    assert record["n_rows_reform_only"] == 0
    assert record["n_rows_differ"] == REGISTERED_DIFFERENCES[row]
    assert record["n_rows_baseline_only"] == REGISTERED_DIFFERENCES[row]
    if REGISTERED_DIFFERENCES[row]:
        assert NAMED_MECHANISM in json.dumps(record["named_mechanisms"])


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
