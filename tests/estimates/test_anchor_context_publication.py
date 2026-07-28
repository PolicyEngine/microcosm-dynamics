"""Fixture-only tests for anchor-context publication contracts."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics import artifacts
from populace_dynamics.contract import ContractRef
from populace_dynamics.estimates import (
    anchor_context_coordinator,
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


def _production_configuration() -> dict[str, Any]:
    return anchor_context_publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=INVOCATION,
    )


def _configuration() -> dict[str, Any]:
    first_estimates_input, anchor_input = _fixture_identities()
    return anchor_context_publication._registered_configuration_echo_for_test(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=INVOCATION,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )


def _fixture_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    first_estimates = json.loads(
        FIRST_ESTIMATES_FIXTURE.read_text(encoding="utf-8")
    )
    anchors = json.loads(ANCHOR_FIXTURE.read_text(encoding="utf-8"))
    assert first_estimates["fixture_only"] is True
    assert anchors["fixture_only"] is True
    return first_estimates, anchors


def _fixture_bundle():
    return anchor_context_publication.load_fixture_documents(REPOSITORY_ROOT)


def _results() -> dict[str, Any]:
    return anchor_context_report.build_results(_fixture_bundle())


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
    fixture_inputs = _fixture_bundle()
    first_estimates, anchors = (
        anchor_context_publication._require_verified_fixture_inputs(
            fixture_inputs
        )
    )
    results = anchor_context_report.build_results(fixture_inputs)
    sidecar_payload = _sidecar_payload()
    artifact = anchor_context_publication.build_anchor_context_artifact(
        configuration_echo=configuration,
        runtime_provenance=RUNTIME_PROVENANCE,
        results=results,
        input_bundle=fixture_inputs,
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
    root = tmp_path / "anchor-context-fixture-rehearsal-test"
    (root / "runs").mkdir(parents=True)
    for source in (FIRST_ESTIMATES_FIXTURE, ANCHOR_FIXTURE):
        relative = source.relative_to(REPOSITORY_ROOT)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
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
    anchor_context_publication._validate_anchor_context_incident(
        record,
        path=root / "runs" / filename,
        expected_configuration_echo=(
            _configuration()
            if expected_configuration is None
            else expected_configuration
        ),
        repository_root=root,
        production_only=False,
    )


def test_registered_configuration_is_exact_deep_and_canonical():
    configuration = _production_configuration()
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
    configuration = _production_configuration()
    configuration[field] = mutant

    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=(
                anchor_context_publication.canonical_json_bytes(configuration)
            ),
        )


def test_registered_configuration_rejects_bytes_keys_and_registry_drift():
    configuration = _production_configuration()
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

    loaded_first, first_raw = anchor_context_publication._load_verified_json(
        REPOSITORY_ROOT,
        first_identity,
        role="first_estimates",
    )
    loaded_anchor, anchor_raw = anchor_context_publication._load_verified_json(
        REPOSITORY_ROOT,
        anchor_identity,
        role="anchor",
    )
    fixture_bundle = anchor_context_publication.load_fixture_documents(
        REPOSITORY_ROOT
    )
    fixture_first, fixture_anchor = (
        anchor_context_publication._require_verified_fixture_inputs(
            fixture_bundle
        )
    )
    assert loaded_first == fixture_first
    assert loaded_anchor == fixture_anchor
    assert first_raw == FIRST_ESTIMATES_FIXTURE.read_bytes()
    assert anchor_raw == ANCHOR_FIXTURE.read_bytes()
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
    with pytest.raises(ValueError, match="identity"):
        anchor_context_publication._load_verified_json(
            REPOSITORY_ROOT,
            wrong_hash,
            role="first_estimates",
        )


def test_constructible_registration_token_cannot_open_production_inputs(
    monkeypatch: pytest.MonkeyPatch,
):
    configuration = _production_configuration()
    registered_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )
    registration = anchor_context_publication.first_publication._parse_registered_configuration(
        repository_root=REPOSITORY_ROOT,
        registration_reference=REGISTRATION_REFERENCE,
        registered_configuration_bytes=registered_bytes,
    )
    attempted_reads: list[str] = []

    def forbidden_loader(*_args, **_kwargs):
        attempted_reads.append("production")
        raise AssertionError("production loader reached an input read")

    monkeypatch.setattr(
        anchor_context_publication,
        "_load_verified_json",
        forbidden_loader,
    )

    with pytest.raises(TypeError, match="live ceremony capability"):
        anchor_context_publication._load_production_documents(registration)

    assert attempted_reads == []


def test_public_engine_rejects_raw_nonfixture_documents_before_compute(
    monkeypatch: pytest.MonkeyPatch,
):
    first_estimates, anchors = _fixture_inputs()
    first_estimates["fixture_only"] = True
    anchors["fixture_only"] = True
    reached_core = False

    def forbidden_extraction(*_args, **_kwargs):
        nonlocal reached_core
        reached_core = True
        raise AssertionError("raw documents reached report computation")

    monkeypatch.setattr(
        anchor_context_report,
        "_extract_model_metrics",
        forbidden_extraction,
    )

    with pytest.raises(TypeError, match="loader-issued bundle"):
        anchor_context_report.build_results((first_estimates, anchors))

    assert reached_core is False


def test_raw_fixture_marker_cannot_authorize_any_report_operation():
    first_estimates, anchors = _fixture_inputs()
    raw_pair = (first_estimates, anchors)
    valid_results = anchor_context_report.build_results(_fixture_bundle())

    with pytest.raises(TypeError, match="loader-issued bundle"):
        anchor_context_report.extract_model_metrics(raw_pair)
    with pytest.raises(TypeError, match="loader-issued bundle"):
        anchor_context_report.extract_official_values(raw_pair)
    with pytest.raises(TypeError, match="loader-issued bundle"):
        anchor_context_report.validate_results(
            valid_results,
            fixture_inputs=raw_pair,
        )
    with pytest.raises(TypeError, match="loader-issued bundle"):
        anchor_context_publication.build_anchor_context_artifact(
            configuration_echo=_configuration(),
            runtime_provenance=RUNTIME_PROVENANCE,
            results=valid_results,
            input_bundle=raw_pair,
            environment_sidecar_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("role", "fixture_relative", "protected_relative"),
    [
        (
            "first_estimates",
            FIRST_ESTIMATES_FIXTURE.relative_to(REPOSITORY_ROOT).as_posix(),
            registry.FIRST_ESTIMATES_INPUT_PATH,
        ),
        (
            "anchor",
            ANCHOR_FIXTURE.relative_to(REPOSITORY_ROOT).as_posix(),
            registry.ANCHOR_INPUT_PATH,
        ),
    ],
)
def test_fixture_loader_rejects_hardlinked_production_inode_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    fixture_relative: str,
    protected_relative: str,
):
    root = tmp_path / "repo"
    protected = root / protected_relative
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"protected production bytes")
    fixture_path = root / fixture_relative
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    os.link(protected, fixture_path)
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("aliased production bytes were read")

    monkeypatch.setattr(anchor_context_publication.os, "read", forbidden_read)

    with pytest.raises(ValueError, match="singly linked|aliases a production"):
        anchor_context_publication._load_verified_json(
            root,
            anchor_context_publication._fixture_input_identity(role),
            role=role,
        )

    assert reads == 0


def test_fixture_loader_rejects_reverse_production_symlink_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "repo"
    fixture_path = root / anchor_context_publication._FIXTURE_FIRST_PATH
    fixture_path.parent.mkdir(parents=True)
    fixture_path.write_bytes(FIRST_ESTIMATES_FIXTURE.read_bytes())
    protected = root / registry.FIRST_ESTIMATES_INPUT_PATH
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.symlink_to(fixture_path)
    reads = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal reads
        reads += 1
        raise AssertionError("reverse-aliased production bytes were read")

    monkeypatch.setattr(anchor_context_publication.os, "read", forbidden_read)

    with pytest.raises(
        ValueError, match="production input path is not regular"
    ):
        anchor_context_publication._load_verified_json(
            root,
            anchor_context_publication._fixture_input_identity(
                "first_estimates"
            ),
            role="first_estimates",
        )

    assert reads == 0


def test_forged_ceremony_capability_cannot_reach_production_compute(
    monkeypatch: pytest.MonkeyPatch,
):
    reached_core = False

    def forbidden_core(*_args, **_kwargs):
        nonlocal reached_core
        reached_core = True
        raise AssertionError("forged authority reached report computation")

    monkeypatch.setattr(
        anchor_context_report,
        "_build_results",
        forbidden_core,
    )
    forged = object.__new__(anchor_context_coordinator._CeremonyCapability)

    with pytest.raises(TypeError, match="live ceremony capability"):
        anchor_context_report._build_production_results(forged, object())

    assert reached_core is False


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
        "prior_incidents",
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
    assert artifact["prior_incidents"] == []
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
        input_bundle=_fixture_bundle(),
    )


def test_artifact_builder_rejects_production_echo_with_unverified_documents():
    fixture_inputs = _fixture_bundle()
    with pytest.raises(TypeError, match="ceremony authority"):
        anchor_context_publication.build_anchor_context_artifact(
            configuration_echo=_production_configuration(),
            runtime_provenance=RUNTIME_PROVENANCE,
            results=anchor_context_report.build_results(fixture_inputs),
            input_bundle=fixture_inputs,
            environment_sidecar_sha256="0" * 64,
        )


def test_production_input_bundle_is_not_caller_constructible():
    configuration = _production_configuration()
    registered_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )
    registration = anchor_context_publication.first_publication._parse_registered_configuration(
        repository_root=REPOSITORY_ROOT,
        registration_reference=REGISTRATION_REFERENCE,
        registered_configuration_bytes=registered_bytes,
    )
    first_estimates, anchors = _fixture_inputs()
    with pytest.raises(TypeError, match="minted only inside"):
        anchor_context_publication._VerifiedProductionInputs(
            registration=registration,
            ceremony_capability=object(),
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
    artifact, configuration, _first, _anchors, _ = _artifact()
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
            input_bundle=_fixture_bundle(),
        )


def test_artifact_writer_binds_sidecar_and_retains_primary_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _repository(tmp_path)
    _source_artifact, configuration, _first, _anchors, sidecar_payload = (
        _artifact()
    )
    fixture_inputs = anchor_context_publication.load_fixture_documents(root)
    artifact = anchor_context_publication.build_anchor_context_artifact(
        configuration_echo=configuration,
        runtime_provenance=RUNTIME_PROVENANCE,
        results=anchor_context_report.build_results(fixture_inputs),
        input_bundle=fixture_inputs,
        environment_sidecar_sha256=hashlib.sha256(sidecar_payload).hexdigest(),
    )
    wrong_binding = copy.deepcopy(artifact)
    wrong_binding["integrity"]["environment_sidecar"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="bind"):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            repository_root=root,
            artifact=wrong_binding,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=RUNTIME_PROVENANCE,
            input_bundle=fixture_inputs,
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
            input_bundle=fixture_inputs,
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
            input_bundle=fixture_inputs,
            sidecar_payload=sidecar_payload,
        )


def test_fixture_writer_rejects_alternate_root_and_mutated_bundle_root(
    tmp_path: Path,
):
    root = tmp_path / "alternate-checkout"
    (root / "runs").mkdir(parents=True)
    artifact, configuration, _first, _anchors, sidecar_payload = _artifact()
    fixture_inputs = _fixture_bundle()
    kwargs = {
        "repository_root": root,
        "artifact": artifact,
        "expected_configuration_echo": configuration,
        "expected_runtime_provenance": RUNTIME_PROVENANCE,
        "input_bundle": fixture_inputs,
        "sidecar_payload": sidecar_payload,
    }

    with pytest.raises(TypeError, match="issued private rehearsal root"):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            **kwargs
        )
    object.__setattr__(fixture_inputs, "repository_root", root)
    with pytest.raises(ValueError, match="bundle bytes changed"):
        anchor_context_publication._write_anchor_context_artifact_for_test(
            **kwargs
        )
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()


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
    validated, payload, _file_id = (
        anchor_context_publication._validate_anchor_context_incident_file(
            path=path,
            expected_configuration_echo=record["configuration_echo"],
            repository_root=root,
            production_only=False,
        )
    )
    assert validated == record
    assert payload == path.read_bytes()


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
        outside = root / "elsewhere" / "anchor_context_report_incident_1.json"
        outside.parent.mkdir()
        outside.write_bytes(
            anchor_context_publication.canonical_json_bytes(
                {
                    **_incident(),
                    "configuration_echo": _production_configuration(),
                }
            )
        )
        anchor_context_publication.validate_anchor_context_incident(
            path=outside,
            expected_configuration_echo=_production_configuration(),
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


def test_production_incident_requires_the_exact_complete_configuration_echo(
    tmp_path: Path,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    record = _incident()
    record["configuration_echo"] = configuration
    path = root / "runs/anchor_context_report_incident_1.json"
    path.write_bytes(anchor_context_publication.canonical_json_bytes(record))
    assert (
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )
        == record
    )

    malformed_root = _repository(tmp_path / "malformed")
    malformed_echo = {"registration_reference": REGISTRATION_REFERENCE}
    malformed = copy.deepcopy(record)
    malformed["configuration_echo"] = malformed_echo
    malformed_path = (
        malformed_root / "runs/anchor_context_report_incident_1.json"
    )
    malformed_path.write_bytes(
        anchor_context_publication.canonical_json_bytes(malformed)
    )
    with pytest.raises((TypeError, ValueError)):
        anchor_context_publication.validate_anchor_context_incident(
            path=malformed_path,
            expected_configuration_echo=malformed_echo,
            repository_root=malformed_root,
        )


@pytest.mark.parametrize(
    "payload_transform",
    [
        lambda payload: b" " + payload,
        lambda payload: payload + b"\n",
        lambda payload: json.dumps(
            json.loads(payload),
            indent=2,
        ).encode("utf-8"),
    ],
)
def test_public_incident_validator_rejects_noncanonical_disk_bytes(
    tmp_path,
    payload_transform,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    record = _incident()
    record["configuration_echo"] = configuration
    path = root / "runs/anchor_context_report_incident_1.json"
    canonical = anchor_context_publication.canonical_json_bytes(record)
    path.write_bytes(payload_transform(canonical))

    with pytest.raises(ValueError, match="canonical"):
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test_public_incident_validator_owns_the_disk_mapping_and_has_no_bypass(
    tmp_path,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    supplied = _incident(reason="external_supplied_reason")
    supplied["configuration_echo"] = configuration
    on_disk = copy.deepcopy(supplied)
    on_disk["reason"] = "external_on_disk_reason"
    path = root / "runs/anchor_context_report_incident_1.json"
    path.write_bytes(anchor_context_publication.canonical_json_bytes(on_disk))

    assert (
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )
        == on_disk
    )
    parameters = inspect.signature(
        anchor_context_publication.validate_anchor_context_incident
    ).parameters
    assert "record" not in parameters
    assert "validate_artifact_existence" not in parameters
    with pytest.raises(TypeError):
        anchor_context_publication.validate_anchor_context_incident(
            supplied,
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )
    with pytest.raises(TypeError):
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
            validate_artifact_existence=False,
        )


@pytest.mark.parametrize(
    "path_kind",
    ["missing", "symlink", "fifo", "hardlink", "oversize"],
)
def test_public_incident_validator_rejects_unpinned_or_nonregular_path(
    tmp_path,
    path_kind,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    record = _incident()
    record["configuration_echo"] = configuration
    payload = anchor_context_publication.canonical_json_bytes(record)
    path = root / "runs/anchor_context_report_incident_1.json"
    source = root / "runs/source.json"
    if path_kind == "symlink":
        source.write_bytes(payload)
        path.symlink_to(source)
    elif path_kind == "fifo":
        os.mkfifo(path)
    elif path_kind == "hardlink":
        source.write_bytes(payload)
        os.link(source, path)
    elif path_kind == "oversize":
        path.write_bytes(
            b"{" + b"x" * anchor_context_publication._INCIDENT_MAX_BYTES + b"}"
        )

    with pytest.raises((OSError, TypeError, ValueError)):
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )


def test_public_incident_validator_rejects_inode_exchange_during_read(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    record = _incident()
    record["configuration_echo"] = configuration
    payload = anchor_context_publication.canonical_json_bytes(record)
    path = root / "runs/anchor_context_report_incident_1.json"
    path.write_bytes(payload)
    original_read = anchor_context_publication.os.read
    exchanged = False

    def exchange_after_read(descriptor, count):
        nonlocal exchanged
        chunk = original_read(descriptor, count)
        if chunk and not exchanged:
            exchanged = True
            path.rename(path.with_suffix(".original"))
            path.write_bytes(payload)
        return chunk

    monkeypatch.setattr(
        anchor_context_publication.os,
        "read",
        exchange_after_read,
    )

    with pytest.raises(ValueError, match="identity changed"):
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )

    assert exchanged is True


def test_public_incident_validator_rejects_equal_size_in_place_mutation(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration = _production_configuration()
    record = _incident()
    record["configuration_echo"] = configuration
    record["reason_detail"] = "AAAA"
    replacement = copy.deepcopy(record)
    replacement["reason_detail"] = "BBBB"
    payload = anchor_context_publication.canonical_json_bytes(record)
    replacement_payload = anchor_context_publication.canonical_json_bytes(
        replacement
    )
    assert len(replacement_payload) == len(payload)
    path = root / "runs/anchor_context_report_incident_1.json"
    path.write_bytes(payload)
    original_read = anchor_context_publication.os.read
    mutated = False

    def mutate_after_read(descriptor, count):
        nonlocal mutated
        chunk = original_read(descriptor, count)
        if chunk and not mutated:
            mutated = True
            path.write_bytes(replacement_payload)
        return chunk

    monkeypatch.setattr(
        anchor_context_publication.os,
        "read",
        mutate_after_read,
    )

    with pytest.raises(ValueError, match="identity changed"):
        anchor_context_publication.validate_anchor_context_incident(
            path=path,
            expected_configuration_echo=configuration,
            repository_root=root,
        )

    assert mutated is True
    assert path.read_bytes() == replacement_payload


def test_public_incident_validator_enforces_artifact_path_iff_on_disk(
    tmp_path,
):
    configuration = _production_configuration()

    compute_root = _repository(tmp_path / "compute")
    compute = _incident(phase="compute")
    compute["configuration_echo"] = configuration
    compute["artifact_path"] = registry.PRIMARY_OUTPUT_PATH
    compute_path = compute_root / "runs/anchor_context_report_incident_1.json"
    compute_path.write_bytes(
        anchor_context_publication.canonical_json_bytes(compute)
    )
    with pytest.raises(ValueError, match="iff"):
        anchor_context_publication.validate_anchor_context_incident(
            path=compute_path,
            expected_configuration_echo=configuration,
            repository_root=compute_root,
        )

    publication_root = _repository(tmp_path / "publication")
    (publication_root / registry.PRIMARY_OUTPUT_PATH).write_bytes(b"partial\n")
    publication_record = _incident(phase="publication")
    publication_record["configuration_echo"] = configuration
    publication_path = (
        publication_root / "runs/anchor_context_report_incident_1.json"
    )
    publication_path.write_bytes(
        anchor_context_publication.canonical_json_bytes(publication_record)
    )
    with pytest.raises(ValueError, match="iff"):
        anchor_context_publication.validate_anchor_context_incident(
            path=publication_path,
            expected_configuration_echo=configuration,
            repository_root=publication_root,
        )

    publication_record["artifact_path"] = registry.PRIMARY_OUTPUT_PATH
    publication_path.write_bytes(
        anchor_context_publication.canonical_json_bytes(publication_record)
    )
    assert (
        anchor_context_publication.validate_anchor_context_incident(
            path=publication_path,
            expected_configuration_echo=configuration,
            repository_root=publication_root,
        )
        == publication_record
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
