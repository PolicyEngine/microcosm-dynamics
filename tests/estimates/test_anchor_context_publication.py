"""Fixture-only tests for anchor-context publication contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics import artifacts
from populace_dynamics.contract import ContractRef
from populace_dynamics.estimates import (
    anchor_context_publication,
    anchor_context_report,
)
from populace_dynamics.estimates import anchor_context_registry as registry

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "anchor_context"
FIRST_ESTIMATES_FIXTURE = FIXTURE_ROOT / "first_estimates_fixture_v1.json"
ANCHOR_FIXTURE = FIXTURE_ROOT / "ssa_level_anchors_fixture_v1.json"
REPOSITORY_ROOT = Path(__file__).parents[2]

REGISTRATION_REFERENCE = "issue-314-comment-1234567"
IMPLEMENTATION_COMMIT = "b" * 40
INVOCATION = [
    "python",
    "-I",
    "-B",
    "-X",
    "pycache_prefix=/tmp/anchor-context-empty",
    "scripts/run_anchor_context_report.py",
    "--registration",
    "/tmp/anchor-context-registration.json",
]
RUNTIME_PROVENANCE = {
    "schema_version": "anchor_context_report.runtime_provenance.v1",
    "implementation_commit": IMPLEMENTATION_COMMIT,
    "python": "3.14.0",
    "platform": "fixture-platform",
}
ENVIRONMENT = {
    "python": "3.14.0",
    "numpy": "2.0.0",
    "pandas": "3.0.0",
    "sklearn": "1.9.0",
    "scipy": "1.18.0",
    "platform": "fixture-platform",
    "fitting_stack": {
        "populace_fit": "absent",
        "populace_frame": "absent",
    },
}
CONTRACT = ContractRef(
    blob_sha="c" * 40,
    head_sha="d" * 40,
    path="gates.yaml",
)

CONFIGURATION_KEYS = {
    "schema_version",
    "registration_reference",
    "design",
    "implementation_commit",
    "invocation",
    "first_estimates_input",
    "anchor_input",
    "required_series_ids",
    "model_metric_specs",
    "pairings",
    "comparison_specs",
}
INCIDENT_KEYS = {
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


def _configuration() -> dict[str, Any]:
    return anchor_context_publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=INVOCATION,
    )


def _fixture_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    first_estimates = json.loads(
        FIRST_ESTIMATES_FIXTURE.read_text(encoding="utf-8")
    )
    anchors = json.loads(ANCHOR_FIXTURE.read_text(encoding="utf-8"))
    assert first_estimates["fixture_only"] is True
    assert anchors["fixture_only"] is True
    return first_estimates, anchors


def _results() -> dict[str, Any]:
    first_estimates, anchors = _fixture_inputs()
    return anchor_context_report.build_results(first_estimates, anchors)


def _sidecar_payload() -> bytes:
    return anchor_context_publication.canonical_json_bytes(
        {
            "environment": ENVIRONMENT,
            "contract": asdict(CONTRACT),
        }
    )


def _fixture_identities() -> tuple[dict[str, str], dict[str, str]]:
    first_path = FIRST_ESTIMATES_FIXTURE.relative_to(REPOSITORY_ROOT)
    anchor_path = ANCHOR_FIXTURE.relative_to(REPOSITORY_ROOT)
    anchor = json.loads(ANCHOR_FIXTURE.read_text(encoding="utf-8"))
    return (
        {
            "path": first_path.as_posix(),
            "sha256": hashlib.sha256(
                FIRST_ESTIMATES_FIXTURE.read_bytes()
            ).hexdigest(),
        },
        {
            "path": anchor_path.as_posix(),
            "artifact_vintage_id": anchor["artifact_vintage_id"],
            "sha256": hashlib.sha256(ANCHOR_FIXTURE.read_bytes()).hexdigest(),
        },
    )


def _artifact() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    bytes,
]:
    configuration = _configuration()
    first_estimates, anchors = _fixture_inputs()
    results = anchor_context_report.build_results(first_estimates, anchors)
    sidecar_payload = _sidecar_payload()
    artifact = anchor_context_publication.build_anchor_context_artifact(
        configuration_echo=configuration,
        runtime_provenance=RUNTIME_PROVENANCE,
        results=results,
        first_estimates=first_estimates,
        anchors=anchors,
        environment_sidecar_sha256=hashlib.sha256(sidecar_payload).hexdigest(),
    )
    return (
        artifact,
        configuration,
        first_estimates,
        anchors,
        sidecar_payload,
    )


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    return root


def _incident(
    *,
    index: int = 1,
    phase: str = "preparation",
    reason: str = "external_fixture_unavailable",
) -> dict[str, Any]:
    configuration = _configuration()
    return {
        "schema_version": "anchor_context_report_incident.v1",
        "incident_index": index,
        "timestamp_utc": "2026-07-27T12:34:56.123456Z",
        "phase": phase,
        "reason": reason,
        "reason_detail": "synthetic fixture dependency was unavailable",
        "registration_reference": REGISTRATION_REFERENCE,
        "configuration_echo": configuration,
        "artifact_path": None,
    }


def _validate_incident(
    record: dict[str, Any],
    *,
    root: Path,
    filename: str = "anchor_context_report_incident_1.json",
    expected_configuration: dict[str, Any] | None = None,
) -> None:
    anchor_context_publication.validate_anchor_context_incident(
        record,
        path=root / "runs" / filename,
        expected_configuration_echo=(
            _configuration()
            if expected_configuration is None
            else expected_configuration
        ),
        repository_root=root,
    )


def test_registered_configuration_is_exact_deep_and_canonical():
    configuration = _configuration()
    registered_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )

    assert set(configuration) == CONFIGURATION_KEYS
    assert configuration["schema_version"] == (
        "anchor_context_report_configuration.v1"
    )
    assert configuration["registration_reference"] == REGISTRATION_REFERENCE
    assert configuration["design"] == registry.design_binding()
    assert configuration["implementation_commit"] == IMPLEMENTATION_COMMIT
    assert configuration["invocation"] == INVOCATION
    assert configuration["first_estimates_input"] == (
        registry.first_estimates_input_identity()
    )
    assert configuration["anchor_input"] == registry.anchor_input_identity()
    assert configuration["required_series_ids"] == (
        registry.required_series_ids()
    )
    assert configuration["model_metric_specs"] == (
        registry.model_metric_specs()
    )
    assert configuration["pairings"] == registry.pairings()
    assert configuration["comparison_specs"] == registry.comparison_specs()
    assert registered_bytes == (
        json.dumps(
            configuration,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    anchor_context_publication.validate_registered_configuration_echo(
        configuration,
        registered_configuration_bytes=registered_bytes,
    )


@pytest.mark.parametrize(
    ("field", "mutant"),
    [
        ("schema_version", "anchor_context_report_configuration.v2"),
        ("registration_reference", ""),
        ("implementation_commit", "B" * 40),
        ("implementation_commit", "b" * 39),
        ("invocation", []),
        ("invocation", ["python", 7]),
    ],
)
def test_registered_configuration_rejects_wrong_literals_and_types(
    field: str,
    mutant: Any,
):
    configuration = _configuration()
    configuration[field] = mutant

    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=(
                anchor_context_publication.canonical_json_bytes(configuration)
            ),
        )


def test_registered_configuration_rejects_bytes_keys_and_registry_drift():
    configuration = _configuration()
    registered_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )

    with pytest.raises(ValueError, match="registered bytes"):
        anchor_context_publication.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=registered_bytes.replace(
                b"issue-314", b"issue-315"
            ),
        )

    extra = copy.deepcopy(configuration)
    extra["unregistered"] = True
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            extra,
            registered_configuration_bytes=(
                anchor_context_publication.canonical_json_bytes(extra)
            ),
        )

    missing = copy.deepcopy(configuration)
    del missing["implementation_commit"]
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            missing,
            registered_configuration_bytes=(
                anchor_context_publication.canonical_json_bytes(missing)
            ),
        )

    wrong_mismatch = copy.deepcopy(configuration)
    wrong_mismatch["comparison_specs"][2]["mismatch_codes"].reverse()
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            wrong_mismatch,
            registered_configuration_bytes=(
                anchor_context_publication.canonical_json_bytes(wrong_mismatch)
            ),
        )


def test_fixture_hash_loader_and_echo_use_only_fixture_identities():
    first_identity, anchor_identity = _fixture_identities()

    loaded_first = anchor_context_publication._load_verified_json(
        REPOSITORY_ROOT,
        first_identity,
        role="first_estimates",
    )
    loaded_anchor = anchor_context_publication._load_verified_json(
        REPOSITORY_ROOT,
        anchor_identity,
        role="anchor",
    )
    fixture_first, fixture_anchor = (
        anchor_context_publication.load_fixture_documents(
            REPOSITORY_ROOT,
            first_estimates_input=first_identity,
            anchor_input=anchor_identity,
        )
    )
    assert loaded_first == fixture_first
    assert loaded_anchor == fixture_anchor
    assert fixture_first["fixture_only"] is True
    assert fixture_anchor["fixture_only"] is True

    fixture_configuration = (
        anchor_context_publication._registered_configuration_echo_for_test(
            registration_reference=REGISTRATION_REFERENCE,
            implementation_commit=IMPLEMENTATION_COMMIT,
            invocation=INVOCATION,
            first_estimates_input=first_identity,
            anchor_input=anchor_identity,
        )
    )
    fixture_bytes = anchor_context_publication.canonical_json_bytes(
        fixture_configuration
    )
    anchor_context_publication._validate_fixture_configuration_echo(
        fixture_configuration,
        registered_configuration_bytes=fixture_bytes,
        first_estimates_input=first_identity,
        anchor_input=anchor_identity,
    )
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            fixture_configuration,
            registered_configuration_bytes=fixture_bytes,
        )

    wrong_hash = copy.deepcopy(first_identity)
    wrong_hash["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sha256"):
        anchor_context_publication._load_verified_json(
            REPOSITORY_ROOT,
            wrong_hash,
            role="first_estimates",
        )


def test_artifact_is_exact_complete_and_bound_to_fixture_results():
    (
        artifact,
        configuration,
        first_estimates,
        anchors,
        sidecar_payload,
    ) = _artifact()

    assert set(artifact) == {
        "schema_version",
        "identity",
        "configuration_echo",
        "runtime_provenance",
        "inputs",
        "results",
        "labels",
        "evidential_statuses",
        "integrity",
        "certifies_nothing",
    }
    assert artifact["schema_version"] == "anchor_context_report.v1"
    assert artifact["identity"] == {
        "report_id": "anchor_context_report",
        "report_class": "registered estimates report",
        "registration_reference": REGISTRATION_REFERENCE,
    }
    assert artifact["configuration_echo"] == configuration
    assert artifact["runtime_provenance"] == RUNTIME_PROVENANCE
    assert artifact["inputs"] == {
        "first_estimates_input": configuration["first_estimates_input"],
        "anchor_input": configuration["anchor_input"],
    }
    assert artifact["results"] == _results()
    assert artifact["labels"] == list(
        anchor_context_publication.EVIDENCE_LABELS
    )
    assert artifact["evidential_statuses"] == (
        anchor_context_publication.EVIDENTIAL_STATUSES
    )
    assert artifact["integrity"] == {
        "environment_sidecar": {
            "path": "anchor_context_report_v1.json.env.json",
            "sha256": hashlib.sha256(sidecar_payload).hexdigest(),
        }
    }
    assert artifact["certifies_nothing"] == list(
        anchor_context_publication.CERTIFIES_NOTHING
    )

    anchor_context_publication.validate_anchor_context_artifact(
        artifact,
        expected_configuration_echo=configuration,
        expected_runtime_provenance=RUNTIME_PROVENANCE,
        first_estimates=first_estimates,
        anchors=anchors,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_top_level",
        "missing_top_level",
        "wrong_echo",
        "wrong_labels",
        "wrong_status",
        "wrong_result",
        "missing_certification",
    ],
)
def test_artifact_validator_rejects_schema_and_content_forgery(
    mutation: str,
):
    artifact, configuration, first_estimates, anchors, _ = _artifact()
    mutant = copy.deepcopy(artifact)

    if mutation == "extra_top_level":
        mutant["extra"] = True
    elif mutation == "missing_top_level":
        del mutant["labels"]
    elif mutation == "wrong_echo":
        mutant["configuration_echo"]["implementation_commit"] = "e" * 40
    elif mutation == "wrong_labels":
        mutant["labels"].reverse()
    elif mutation == "wrong_status":
        mutant["evidential_statuses"]["opening_stock_consumers"][
            "presentation"
        ] = "headline"
    elif mutation == "wrong_result":
        available = next(
            row
            for row in mutant["results"]["comparison_results"]
            if row["evaluated"]
        )
        available["annual_rows"][0]["comparison_mean"] += 1.0
    else:
        mutant["certifies_nothing"].pop()

    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_anchor_context_artifact(
            mutant,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=RUNTIME_PROVENANCE,
            first_estimates=first_estimates,
            anchors=anchors,
        )


def test_artifact_writer_binds_sidecar_and_retains_primary_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _repository(tmp_path)
    artifact, configuration, first_estimates, anchors, sidecar_payload = (
        _artifact()
    )
    wrong_binding = copy.deepcopy(artifact)
    wrong_binding["integrity"]["environment_sidecar"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="bind"):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            repository_root=root,
            artifact=wrong_binding,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=RUNTIME_PROVENANCE,
            first_estimates=first_estimates,
            anchors=anchors,
            sidecar_payload=sidecar_payload,
        )
    assert not (root / "runs" / "anchor_context_report_v1.json").exists()

    original_write = artifacts._write_exclusive

    def fail_sidecar(destination: Path, payload: str | bytes) -> None:
        if destination.name.endswith(".env.json"):
            raise OSError("synthetic sidecar failure")
        original_write(destination, payload)

    monkeypatch.setattr(artifacts, "_write_exclusive", fail_sidecar)
    with pytest.raises(OSError, match="synthetic sidecar failure"):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            repository_root=root,
            artifact=artifact,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=RUNTIME_PROVENANCE,
            first_estimates=first_estimates,
            anchors=anchors,
            sidecar_payload=sidecar_payload,
        )

    primary = root / "runs" / "anchor_context_report_v1.json"
    sidecar = root / "runs" / "anchor_context_report_v1.json.env.json"
    assert primary.read_bytes() == (
        anchor_context_publication.canonical_json_bytes(artifact)
    )
    assert not sidecar.exists()

    with pytest.raises(FileExistsError):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            repository_root=root,
            artifact=artifact,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=RUNTIME_PROVENANCE,
            first_estimates=first_estimates,
            anchors=anchors,
            sidecar_payload=sidecar_payload,
        )


def test_incident_schema_types_timestamp_and_canonical_bytes(tmp_path: Path):
    root = _repository(tmp_path)
    record = _incident()

    assert set(record) == INCIDENT_KEYS
    _validate_incident(record, root=root)

    path = anchor_context_publication._write_anchor_context_incident_for_test(
        repository_root=root,
        phase=record["phase"],
        reason=record["reason"],
        reason_detail=record["reason_detail"],
        configuration_echo=record["configuration_echo"],
        timestamp_utc=record["timestamp_utc"],
    )
    assert path.name == "anchor_context_report_incident_1.json"
    assert path.read_bytes() == (
        anchor_context_publication.canonical_json_bytes(record)
    )


@pytest.mark.parametrize("missing_key", sorted(INCIDENT_KEYS))
def test_incident_rejects_each_missing_schema_key(
    tmp_path: Path,
    missing_key: str,
):
    root = _repository(tmp_path)
    record = _incident()
    del record[missing_key]

    with pytest.raises((TypeError, ValueError)):
        _validate_incident(record, root=root)


@pytest.mark.parametrize(
    ("field", "mutant"),
    [
        ("schema_version", "anchor_context_report_incident.v2"),
        ("incident_index", True),
        ("incident_index", 0),
        ("phase", "prepare"),
        ("reason", ""),
        ("reason_detail", []),
        ("registration_reference", 7),
        ("configuration_echo", "not-an-object"),
        ("artifact_path", 7),
        ("timestamp_utc", "2026-07-27T12:34:56+00:00"),
        ("timestamp_utc", "2026-02-30T12:34:56Z"),
        ("timestamp_utc", "2026-07-27"),
    ],
)
def test_incident_rejects_wrong_literals_types_and_timestamps(
    tmp_path: Path,
    field: str,
    mutant: Any,
):
    root = _repository(tmp_path)
    record = _incident()
    record[field] = mutant

    with pytest.raises((TypeError, ValueError)):
        _validate_incident(record, root=root)


def test_incident_rejects_keys_echo_index_location_and_noncontiguity(
    tmp_path: Path,
):
    root = _repository(tmp_path)

    extra = _incident()
    extra["estimate"] = [1.0]
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(extra, root=root)

    expected = _configuration()
    drift = _incident()
    drift["configuration_echo"]["comparison_specs"].reverse()
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(
            drift,
            root=root,
            expected_configuration=expected,
        )

    with pytest.raises((TypeError, ValueError)):
        _validate_incident(
            _incident(),
            root=root,
            filename="anchor_context_report_incident_01.json",
        )
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(
            _incident(),
            root=root,
            filename="anchor_context_report_incident_2.json",
        )
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_anchor_context_incident(
            _incident(),
            path=root / "elsewhere" / "anchor_context_report_incident_1.json",
            expected_configuration_echo=_configuration(),
            repository_root=root,
        )

    (root / "runs" / "anchor_context_report_incident_2.json").touch()
    with pytest.raises(RuntimeError, match="contiguous"):
        anchor_context_publication._write_anchor_context_incident_for_test(
            repository_root=root,
            phase="preparation",
            reason="external_fixture_unavailable",
            reason_detail="synthetic",
            configuration_echo=_configuration(),
            timestamp_utc="2026-07-27T12:34:56Z",
        )


def test_incident_artifact_path_iff_publication_partial(tmp_path: Path):
    root = _repository(tmp_path)

    nonpublication = _incident(phase="compute")
    nonpublication["artifact_path"] = "runs/anchor_context_report_v1.json"
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(nonpublication, root=root)

    partial = root / "runs" / "anchor_context_report_v1.json"
    partial.write_text('{"fixture_partial":true}\n', encoding="utf-8")
    publication = _incident(phase="publication")
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(publication, root=root)

    publication["artifact_path"] = "runs/anchor_context_report_v1.json"
    _validate_incident(publication, root=root)

    publication["artifact_path"] = "../anchor_context_report_v1.json"
    with pytest.raises((TypeError, ValueError)):
        _validate_incident(publication, root=root)


def test_incident_retry_eligibility_is_exact_truth_table():
    for phase in ("preparation", "invariant", "compute", "publication"):
        for reason in (
            "external_dependency_unavailable",
            "dependency_unavailable",
        ):
            expected = phase in {
                "preparation",
                "compute",
            } and reason.startswith("external_")
            record = _incident(phase=phase, reason=reason)
            assert (
                anchor_context_publication.incident_is_retry_eligible(record)
                is expected
            )

    mutant = _incident()
    mutant["reason"] = ["external_dependency_unavailable"]
    assert not anchor_context_publication.incident_is_retry_eligible(mutant)
