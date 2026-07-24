"""Schema and one-shot tests for first-estimates publication records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from populace_dynamics.estimates import publication


def _configuration() -> dict:
    return {
        "registration_reference": "issue-42-comment-1234567",
        "projection": {
            "draw_indices": list(range(20)),
            "root_seeds": list(range(5200, 5220)),
        },
        "parameters": {"bundle_sha256": "c" * 64},
    }


def _sidecar() -> bytes:
    return publication.canonical_json_bytes(
        {
            "contract": {
                "blob_sha": "a" * 40,
                "head_sha": "b" * 40,
                "path": "gates.yaml",
            },
            "environment": {"python": "fixture"},
        }
    )


def _artifact(sidecar: bytes | None = None) -> dict:
    payload = sidecar if sidecar is not None else _sidecar()
    annual = publication.table_record(
        per_draw=[
            {"draw_index": draw_index, "year": 2015, "value": 0.0}
            for draw_index in range(20)
        ],
        aggregate=[
            {
                "year": 2015,
                "mean": 0.0,
                "sample_sd": 0.0,
            }
        ],
        unit_label=(
            "annualized statutory benefit, eligibility-PIA with COLA, "
            "no recomputation"
        ),
        annual=True,
        biennial_companion=[
            {
                "year": 2016,
                "mean": 0.0,
                "sample_sd": 0.0,
            }
        ],
    )
    return {
        "schema_version": publication.ARTIFACT_SCHEMA_VERSION,
        "identity": {
            "registration_reference": "issue-42-comment-1234567",
        },
        "configuration_echo": _configuration(),
        "integrity": {
            "environment_sidecar": {
                "path": "first_estimates_v1.json.env.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        },
        "parameters": {"bundle_sha256": "c" * 64},
        "execution": {
            "canonical_rule": publication.CANONICAL_EXECUTION_RULE,
        },
        "tables": {"modeled_award_flow": annual},
        "counts": {},
        "diagnostics": {},
        "gap_block": list(publication.GAP_BLOCK),
        "certifies_nothing": list(publication.CERTIFIES_NOTHING),
    }


def test__artifact_writer__binds_and_writes_exact_sidecar_once(tmp_path):
    sidecar = _sidecar()
    artifact = _artifact(sidecar)
    destination = tmp_path / "first_estimates_v1.json"

    publication.write_first_estimates_artifact(
        destination,
        artifact,
        expected_configuration_echo=_configuration(),
        sidecar_payload=sidecar,
    )

    assert json.loads(destination.read_text()) == artifact
    assert Path(f"{destination}.env.json").read_bytes() == sidecar
    with pytest.raises(FileExistsError, match="one-shot rule"):
        publication.write_first_estimates_artifact(
            destination,
            artifact,
            expected_configuration_echo=_configuration(),
            sidecar_payload=sidecar,
        )


def test__artifact_validator__rejects_gap_or_label_drift():
    artifact = _artifact()
    artifact["gap_block"] = artifact["gap_block"][:-1]
    with pytest.raises(ValueError, match="gap block"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )

    artifact = _artifact()
    artifact["tables"]["modeled_award_flow"]["labels"] = ["frame-relative"]
    with pytest.raises(ValueError, match="evidence labels"):
        publication.validate_first_estimates_artifact(
            artifact,
            expected_configuration_echo=_configuration(),
        )


def test__incident_writer__uses_exact_schema_and_retry_class(tmp_path):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    configuration = _configuration()

    path = publication.write_first_estimates_incident(
        repository_root=root,
        phase="preparation",
        reason="external_parameter_checkout_unavailable",
        reason_detail="pinned checkout was not mounted",
        registration_reference="issue-42-comment-1234567",
        configuration_echo=configuration,
        timestamp_utc="2026-07-24T12:34:56Z",
    )
    record = json.loads(path.read_text())

    assert set(record) == {
        "schema_version",
        "incident_index",
        "timestamp_utc",
        "phase",
        "reason",
        "reason_detail",
        "registration_reference",
        "configuration_echo",
        "artifact_path",
    }
    assert record["incident_index"] == 1
    assert record["artifact_path"] is None
    assert publication.incident_is_retry_eligible(record)
    publication.validate_first_estimates_incident(
        record,
        path=path,
        expected_configuration_echo=configuration,
        repository_root=root,
    )


def test__incident_validator__enforces_publication_partial_iff_rule(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    partial = runs / "first_estimates_v1.json"
    partial.write_text('{"partial": true}\n')
    configuration = _configuration()

    path = publication.write_first_estimates_incident(
        repository_root=root,
        phase="publication",
        reason="sidecar_hash_mismatch",
        reason_detail="the exact sidecar did not match its primary binding",
        registration_reference="issue-42-comment-1234567",
        configuration_echo=configuration,
        partial_artifact_path=partial,
        timestamp_utc="2026-07-24T12:34:56.123456Z",
    )
    record = json.loads(path.read_text())
    assert record["artifact_path"] == "runs/first_estimates_v1.json"
    assert not publication.incident_is_retry_eligible(record)

    record["phase"] = "compute"
    with pytest.raises(ValueError, match="artifact_path"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test__incident_validator__requires_timestamp_and_registration_identity(
    tmp_path,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    configuration = _configuration()
    path = root / "runs" / "first_estimates_incident_1.json"
    record = {
        "schema_version": publication.INCIDENT_SCHEMA_VERSION,
        "incident_index": 1,
        "timestamp_utc": "2026-07-24Z",
        "phase": "invariant",
        "reason": "schema_drift",
        "reason_detail": "fixture",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "artifact_path": None,
    }

    with pytest.raises(ValueError, match="ISO-8601"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )

    record["timestamp_utc"] = "2026-07-24T12:34:56Z"
    record["registration_reference"] = "different-registration"
    with pytest.raises(ValueError, match="registration reference"):
        publication.validate_first_estimates_incident(
            record,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test__incident_validator__requires_partial_path_when_v1_exists(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (runs / "first_estimates_v1.json").write_text('{"partial": true}\n')
    configuration = _configuration()
    record = {
        "schema_version": publication.INCIDENT_SCHEMA_VERSION,
        "incident_index": 1,
        "timestamp_utc": "2026-07-24T12:34:56Z",
        "phase": "publication",
        "reason": "write_interrupted",
        "reason_detail": "fixture",
        "registration_reference": configuration["registration_reference"],
        "configuration_echo": configuration,
        "artifact_path": None,
    }

    with pytest.raises(ValueError, match="artifact_path"):
        publication.validate_first_estimates_incident(
            record,
            path=runs / "first_estimates_incident_1.json",
            expected_configuration_echo=configuration,
            repository_root=root,
        )
