"""Pin the Track A registered one-shot artifact (Registration 13).

``runs/replication_urban2010_cola_v1.json`` is the output of the single
registered run of DynaSim scorecard exercise 1 (COLA -1pp, 2030 age
profile). It cannot be reproduced in CI (real PSID data, about 25 minutes),
so these tests pin what was registered and what the run recorded: the file
hash its sidecar binds, the registration pointer and commit, the frozen
configuration, Max's rulings and the input provenance.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "replication_urban2010_cola_v1.json"
SIDECAR = ROOT / "runs" / "replication_urban2010_cola_v1.env.json"
REGISTRATION = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-5804420283"
)
REGISTERED_COMMIT = "002264d92fb75f0ff22d7dc1fa9cdcef736a4cf6"
ARTIFACT_SHA256 = (
    "270acf292682b8111133f9047f366c93173e713bc422cb7e108bd064ac33d53e"
)


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


def test_the_configuration_is_the_frozen_default(artifact):
    config = artifact["config"]
    assert config["reference_year"] == 2030
    assert config["draw_indices"] == list(range(20))
    assert config["rows"] == ["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
    assert set(artifact["rows"]) == set(config["rows"])


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
