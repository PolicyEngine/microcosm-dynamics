"""Fixture-only tests for the registered anchor-context coordinator."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import textwrap
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any

import pytest

from populace_dynamics.contract import ContractRef
from populace_dynamics.estimates import (
    anchor_context_coordinator as coordinator,
)
from populace_dynamics.estimates import (
    anchor_context_publication as publication,
)
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import anchor_context_report as report
from populace_dynamics.estimates import coordinator as first_coordinator

FIXTURE_SOURCE_ROOT = Path(__file__).parents[1] / "fixtures" / "anchor_context"
FIRST_ESTIMATES_FIXTURE = (
    FIXTURE_SOURCE_ROOT / "first_estimates_fixture_v1.json"
)
ANCHOR_FIXTURE = FIXTURE_SOURCE_ROOT / "ssa_level_anchors_fixture_v1.json"
REGISTRATION_REFERENCE = "issue-42-comment-fixture-anchor-context"
IMPLEMENTATION_COMMIT = "c" * 40
FIXTURE_FIRST_PATH = (
    "tests/fixtures/anchor_context/first_estimates_fixture_v1.json"
)
FIXTURE_ANCHOR_PATH = (
    "tests/fixtures/anchor_context/ssa_level_anchors_fixture_v1.json"
)
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
    blob_sha="a" * 40,
    head_sha="b" * 40,
    path="gates.yaml",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "anchor-context-fixture-rehearsal-test"
    (root / "runs").mkdir(parents=True)
    for source, relative in (
        (FIRST_ESTIMATES_FIXTURE, FIXTURE_FIRST_PATH),
        (ANCHOR_FIXTURE, FIXTURE_ANCHOR_PATH),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    return root


def _invocation(root: Path) -> list[str]:
    sentinel = root / "fresh-empty-pycache"
    sentinel.mkdir(exist_ok=True)
    registration = root / "registrations" / "anchor-context.json"
    registration.parent.mkdir(exist_ok=True)
    return [
        "python",
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={sentinel}",
        "scripts/run_anchor_context_report.py",
        "--registration",
        str(registration),
    ]


def _configuration(root: Path) -> dict[str, Any]:
    return publication._registered_configuration_echo_for_test(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=_invocation(root),
        first_estimates_input={
            "path": FIXTURE_FIRST_PATH,
            "sha256": _sha256(FIRST_ESTIMATES_FIXTURE),
        },
        anchor_input={
            "path": FIXTURE_ANCHOR_PATH,
            "artifact_vintage_id": "ssa_level_anchors.fixture_only.v1",
            "sha256": _sha256(ANCHOR_FIXTURE),
        },
    )


def _configuration_bytes(root: Path) -> bytes:
    return publication.canonical_json_bytes(_configuration(root))


@pytest.fixture(autouse=True)
def _fixed_sidecar_identity(monkeypatch):
    monkeypatch.setattr(
        publication.first_publication,
        "environment_block",
        lambda: ENVIRONMENT,
    )
    monkeypatch.setattr(
        publication.first_publication.ContractRef,
        "current",
        staticmethod(lambda _root=None: CONTRACT),
    )


def _operations(
    calls: list[str],
    captured: dict[str, Any],
    *,
    failure_phase: str | None = None,
    failure: BaseException | None = None,
) -> coordinator._CoordinatorOperations:
    error = failure or RuntimeError("fixture estimate sentinel [1, 2, 3]")

    def maybe_fail(phase: str, value: Any) -> Any:
        calls.append(phase)
        if failure_phase == phase:
            raise error
        return value

    def load_inputs(registration):
        assert isinstance(
            registration,
            publication.first_publication._RegisteredConfigurationToken,
        )
        root = registration._repository_root
        configuration_echo = publication.first_publication._configuration_echo(
            registration
        )
        publication._assert_fixture_identities(
            configuration_echo["first_estimates_input"],
            configuration_echo["anchor_input"],
        )
        loaded = publication.load_fixture_documents(root)
        return maybe_fail("preparation", loaded)

    def build_results(
        _registration,
        loaded_inputs,
    ) -> dict[str, Any]:
        return maybe_fail(
            "compute",
            report.build_results(loaded_inputs),
        )

    def validate_results(
        _registration,
        results: dict[str, Any],
        loaded_inputs,
    ) -> None:
        report.validate_results(
            results,
            fixture_inputs=loaded_inputs,
        )
        maybe_fail("invariant_results", None)

    def prepare_sidecar(_root: Path) -> tuple[bytes, str]:
        payload = publication.canonical_json_bytes(
            {
                "environment": ENVIRONMENT,
                "contract": asdict(CONTRACT),
            }
        )
        return payload, hashlib.sha256(payload).hexdigest()

    def build_artifact(**kwargs):
        captured["artifact_kwargs"] = kwargs
        artifact = publication.build_anchor_context_artifact(**kwargs)
        return maybe_fail("invariant_artifact", artifact)

    def publish_artifact(*args, **kwargs):
        calls.append("publication")
        if failure_phase == "publication":
            raise error
        captured["publication_args"] = args
        captured["publication_kwargs"] = dict(kwargs)
        token, artifact = args
        assert kwargs.pop("ceremony_capability") is None
        return publication._write_anchor_context_artifact_for_test(
            repository_root=token.registration._repository_root,
            artifact=artifact,
            expected_configuration_echo=(
                publication.first_publication._configuration_echo(
                    token.registration
                )
            ),
            expected_runtime_provenance=publication._runtime_provenance(token),
            expected_prior_incidents=token.prior_incidents,
            sidecar_payload=token.sidecar_payload,
            **kwargs,
        )

    def publish_incident(token, **kwargs):
        registration = (
            token.registration
            if isinstance(token, publication._AnchorContextPrecomputeToken)
            else token
        )
        configuration_echo = publication.first_publication._configuration_echo(
            registration
        )
        production_only = (
            configuration_echo["first_estimates_input"]
            == registry.first_estimates_input_identity()
            and configuration_echo["anchor_input"]
            == registry.anchor_input_identity()
        )
        return publication._write_anchor_context_incident_for_test(
            repository_root=registration._repository_root,
            configuration_echo=configuration_echo,
            production_only=production_only,
            **kwargs,
        )

    return coordinator._CoordinatorOperations(
        assert_interpreter=lambda _configuration, _actual_invocation: None,
        validate_repository=lambda _root, _configuration: None,
        prepare_sidecar=prepare_sidecar,
        load_inputs=load_inputs,
        build_results=build_results,
        validate_results=validate_results,
        build_runtime_provenance=(
            lambda _implementation_commit: copy.deepcopy(RUNTIME_PROVENANCE)
        ),
        build_artifact=build_artifact,
        publish_artifact=publish_artifact,
        publish_incident=publish_incident,
        after_preparation=lambda: None,
    )


def _run(
    root: Path,
    operations: coordinator._CoordinatorOperations,
    *,
    configuration_bytes: bytes | None = None,
    actual_invocation: list[str] | None = None,
) -> coordinator.CoordinatorResult:
    payload = (
        configuration_bytes
        if configuration_bytes is not None
        else _configuration_bytes(root)
    )
    configuration = json.loads(payload)
    return coordinator._run_registered_anchor_context_for_test(
        repository_root=root,
        registered_configuration_bytes=payload,
        actual_invocation=(
            configuration["invocation"]
            if actual_invocation is None
            else actual_invocation
        ),
        operations=operations,
    )


def _run_attempt(
    root: Path,
    operations: coordinator._CoordinatorOperations,
    *,
    retry_receipt: coordinator._RetryReceipt | None = None,
    configuration_bytes: bytes | None = None,
) -> coordinator._CoordinatorAttemptOutcome:
    """Exercise one internal fixture attempt while preserving receipt handoff."""
    payload = (
        configuration_bytes
        if configuration_bytes is not None
        else _configuration_bytes(root)
    )
    configuration = json.loads(payload)
    return coordinator._run_registered_anchor_context_core(
        repository_root=root,
        registered_configuration_bytes=payload,
        actual_invocation=configuration["invocation"],
        operations=operations,
        production_only=False,
        coordinator_invocation=None,
        retry_receipt=retry_receipt,
        mint_capability=None,
        revoke_capability=None,
        issue_initial_attempt=coordinator._issue_initial_attempt,
        require_initial_attempt=coordinator._require_initial_attempt,
        seal_retry_authority=coordinator._seal_retry_authority,
        revoke_initial_attempt=coordinator._revoke_initial_attempt,
        authorize_invocation=coordinator._authorize_invocation,
        create_retry_claim=coordinator._create_retry_claim,
        require_retry_authorization=(coordinator._require_retry_authorization),
        revoke_retry_authorization=(coordinator._revoke_retry_authorization),
    )


def _publish_external_incident(root: Path) -> Path:
    return publication._write_anchor_context_incident_for_test(
        repository_root=root,
        phase="compute",
        reason="external_fixture_storage_unavailable",
        reason_detail="Fixture storage unavailable before output.",
        configuration_echo=_configuration(root),
        production_only=False,
    )


def test_fixture_rehearsal_runs_engine_validators_and_ceremony_end_to_end(
    tmp_path,
):
    root = _repository(tmp_path)
    calls: list[str] = []
    captured: dict[str, Any] = {}
    registered_bytes = _configuration_bytes(root)

    result = _run(root, _operations(calls, captured))

    assert result == coordinator.CoordinatorResult(
        status="published",
        path=root / registry.PRIMARY_OUTPUT_PATH,
        phase="publication",
        reason=None,
    )
    assert calls == [
        "preparation",
        "compute",
        "invariant_results",
        "invariant_artifact",
        "publication",
    ]
    artifact = json.loads(result.path.read_bytes())
    configuration = json.loads(registered_bytes)
    assert artifact["configuration_echo"] == configuration
    assert (
        publication.canonical_json_bytes(artifact["configuration_echo"])
        == registered_bytes
    )
    assert len(artifact["results"]["comparison_results"]) == 9
    assert artifact["prior_incidents"] == []
    assert Path(f"{result.path}.env.json").is_file()
    assert captured["artifact_kwargs"]["configuration_echo"] == configuration
    attempt_claim = root / "runs/anchor_context_report_attempt.claim"
    claim = json.loads(attempt_claim.read_bytes())
    assert set(claim) == {
        "schema_version",
        "registration_reference",
        "configuration_sha256",
        "next_incident_index",
        "authority_path",
        "authority_device",
        "authority_inode",
        "authority_nonce_sha256",
        "prelaunch_record",
    }
    assert claim["schema_version"] == "anchor_context_report_attempt.v3"
    assert claim["registration_reference"] == REGISTRATION_REFERENCE
    assert (
        claim["configuration_sha256"]
        == hashlib.sha256(registered_bytes).hexdigest()
    )
    assert claim["next_incident_index"] == 1
    assert claim["authority_path"] == (
        "runs/anchor_context_report_retry_authority.claim"
    )
    authority = root / claim["authority_path"]
    metadata = authority.stat()
    assert (claim["authority_device"], claim["authority_inode"]) == (
        metadata.st_dev,
        metadata.st_ino,
    )
    assert len(claim["authority_nonce_sha256"]) == 64
    assert (
        claim["prelaunch_record"]["checks"][0]["evidence"][
            "production_input_io_before_launch"
        ]
        is False
    )
    assert authority.read_bytes() == b""


@pytest.mark.parametrize(
    ("failure_phase", "expected_phase"),
    [
        ("preparation", "preparation"),
        ("compute", "compute"),
        ("invariant_results", "invariant"),
        ("invariant_artifact", "invariant"),
        ("publication", "publication"),
    ],
)
def test_every_failure_phase_publishes_typed_incident_without_values(
    tmp_path,
    failure_phase,
    expected_phase,
):
    root = _repository(tmp_path)
    calls: list[str] = []
    result = _run(
        root,
        _operations(calls, {}, failure_phase=failure_phase),
    )

    assert result.status == "incident"
    assert result.phase == expected_phase
    record = json.loads(result.path.read_bytes())
    assert record["phase"] == expected_phase
    assert record["configuration_echo"] == _configuration(root)
    serialized = result.path.read_text(encoding="utf-8")
    assert "fixture estimate sentinel" not in serialized
    assert "[1, 2, 3]" not in serialized
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()
    assert not (root / registry.SIDECAR_OUTPUT_PATH).exists()
    assert (
        root / "runs/anchor_context_report_retry_authority.claim"
    ).read_bytes() == b""


def test_input_hash_failure_aborts_before_engine(tmp_path):
    root = _repository(tmp_path)
    configuration = _configuration(root)
    configuration["first_estimates_input"]["sha256"] = "0" * 64
    calls: list[str] = []

    with pytest.raises(ValueError, match="identity is not fixed"):
        _run(
            root,
            _operations(calls, {}),
            configuration_bytes=publication.canonical_json_bytes(
                configuration
            ),
        )

    assert calls == []
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()


def test_fixture_rehearsal_rejects_production_identities_before_read(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    production_configuration = publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=_invocation(root),
    )
    calls: list[str] = []
    attempted_read = False

    def forbidden_read(*_args, **_kwargs):
        nonlocal attempted_read
        attempted_read = True
        raise AssertionError("fixture rehearsal attempted an input read")

    monkeypatch.setattr(publication, "_load_verified_json", forbidden_read)

    result = _run(
        root,
        _operations(calls, {}),
        configuration_bytes=publication.canonical_json_bytes(
            production_configuration
        ),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert attempted_read is False
    assert calls == []
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()


@pytest.mark.parametrize(
    "relative_output",
    [registry.PRIMARY_OUTPUT_PATH, registry.SIDECAR_OUTPUT_PATH],
)
def test_output_must_be_absent_before_input_load(tmp_path, relative_output):
    root = _repository(tmp_path)
    output = root / relative_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("occupied fixture path\n", encoding="utf-8")
    calls: list[str] = []

    result = _run(root, _operations(calls, {}))

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert calls == []
    assert output.read_text(encoding="utf-8") == "occupied fixture path\n"


def test_configuration_keeps_exact_canonical_invocation_and_bytes(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration = _configuration(root)
    invocation = _invocation(root)
    registered_bytes = publication.canonical_json_bytes(configuration)
    captured: dict[str, Any] = {}
    sentinel = Path(invocation[4].removeprefix("pycache_prefix="))
    monkeypatch.setattr(
        coordinator,
        "sys",
        SimpleNamespace(
            flags=SimpleNamespace(
                isolated=True,
                dont_write_bytecode=True,
            ),
            pycache_prefix=str(sentinel),
        ),
    )
    operations = replace(
        _operations([], captured),
        assert_interpreter=coordinator._assert_sealed_interpreter,
    )

    result = _run(
        root,
        operations,
        configuration_bytes=registered_bytes,
    )

    assert result.status == "published"
    assert configuration["invocation"] == invocation
    assert captured["artifact_kwargs"]["configuration_echo"]["invocation"] == (
        invocation
    )
    assert (
        publication.canonical_json_bytes(
            captured["artifact_kwargs"]["configuration_echo"]
        )
        == registered_bytes
    )


def test_all_six_prelaunch_checks_are_recorded_before_input_loading(
    tmp_path,
):
    root = _repository(tmp_path)
    records: list[coordinator._PrelaunchRecord] = []
    events: list[str] = []
    operations = _operations([], {})
    original_load = operations.load_inputs

    def record_prelaunch(record):
        claim = json.loads(
            (root / "runs/anchor_context_report_attempt.claim").read_bytes()
        )
        assert claim["prelaunch_record"] == json.loads(record.evidence_bytes)
        events.append("prelaunch_record")
        records.append(record)

    def load_after_record(registration):
        events.append("input_load")
        assert len(records) == 1
        assert registration._repository_root == root
        claim = json.loads(
            (root / "runs/anchor_context_report_attempt.claim").read_bytes()
        )
        assert claim["prelaunch_record"] == json.loads(
            records[0].evidence_bytes
        )
        return original_load(registration)

    result = _run(
        root,
        replace(
            operations,
            record_prelaunch=record_prelaunch,
            load_inputs=load_after_record,
        ),
    )

    assert result.status == "published"
    assert events == ["prelaunch_record", "input_load"]
    assert len(records) == 1
    record = records[0]
    assert record.check_names == coordinator.PRELAUNCH_CHECK_NAMES
    assert (
        record.configuration_sha256
        == hashlib.sha256(_configuration_bytes(root)).hexdigest()
    )
    assert record.next_incident_index == 1
    evidence = json.loads(record.evidence_bytes)
    assert evidence["schema_version"] == "anchor_context_report_prelaunch.v1"
    assert evidence["registration_reference"] == REGISTRATION_REFERENCE
    assert [check["name"] for check in evidence["checks"]] == list(
        coordinator.PRELAUNCH_CHECK_NAMES
    )
    assert all(check["passed"] is True for check in evidence["checks"])
    assert evidence["checks"][0]["evidence"] == {
        "design": _configuration(root)["design"],
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "production_input_io_before_launch": False,
    }
    assert evidence["checks"][1]["evidence"] == {
        "registration_reference": REGISTRATION_REFERENCE,
        "registered_configuration": _configuration(root),
        "registered_configuration_sha256": record.configuration_sha256,
        "registered_configuration_byte_length": len(
            _configuration_bytes(root)
        ),
    }
    assert evidence["checks"][2]["evidence"] == {
        "first_estimates_input": _configuration(root)["first_estimates_input"],
        "anchor_input": _configuration(root)["anchor_input"],
        "production_inputs_opened": False,
    }
    assert evidence["checks"][3]["evidence"] == {
        "output_absence": [
            {"path": registry.PRIMARY_OUTPUT_PATH, "absent": True},
            {"path": registry.SIDECAR_OUTPUT_PATH, "absent": True},
        ],
        "incident_history": [],
        "next_incident_index": 1,
    }
    assert evidence["checks"][4]["evidence"] == {
        "registered_invocation": _invocation(root),
        "actual_invocation": _invocation(root),
        "byte_match": True,
        "isolated_interpreter_verified": True,
    }
    assert evidence["checks"][5]["evidence"] == {
        "execution_rule": coordinator.CANONICAL_EXECUTION_RULE,
        "acknowledged": True,
    }


def test_prelaunch_observer_failure_leaves_durable_evidence_before_input(
    tmp_path,
):
    root = _repository(tmp_path)
    calls: list[str] = []
    captured_record: list[coordinator._PrelaunchRecord] = []

    def fail_after_durable_record(record):
        claim_path = root / "runs/anchor_context_report_attempt.claim"
        assert claim_path.is_file()
        claim = json.loads(claim_path.read_bytes())
        assert claim["prelaunch_record"] == json.loads(record.evidence_bytes)
        captured_record.append(record)
        raise RuntimeError("crash immediately after durable prelaunch record")

    result = _run(
        root,
        replace(
            _operations(calls, {}),
            record_prelaunch=fail_after_durable_record,
        ),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert calls == []
    assert len(captured_record) == 1
    claim = json.loads(
        (root / "runs/anchor_context_report_attempt.claim").read_bytes()
    )
    assert claim["prelaunch_record"] == json.loads(
        captured_record[0].evidence_bytes
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "delete",
        "reorder_checks",
        "check_evidence",
        "configuration_echo",
        "actual_invocation",
        "next_incident_index",
    ],
)
def test_prelaunch_claim_mutation_refuses_input_loading(tmp_path, mutation):
    root = _repository(tmp_path)
    calls: list[str] = []

    def mutate_durable_record(_record):
        claim_path = root / "runs/anchor_context_report_attempt.claim"
        if mutation == "delete":
            claim_path.unlink()
            return
        claim = json.loads(claim_path.read_bytes())
        prelaunch = claim["prelaunch_record"]
        if mutation == "reorder_checks":
            prelaunch["checks"].reverse()
        elif mutation == "check_evidence":
            prelaunch["checks"][0]["evidence"][
                "production_input_io_before_launch"
            ] = True
        elif mutation == "configuration_echo":
            prelaunch["checks"][1]["evidence"]["registered_configuration"][
                "invocation"
            ][-1] += ".changed"
        elif mutation == "actual_invocation":
            prelaunch["checks"][4]["evidence"]["actual_invocation"][
                -1
            ] += ".changed"
        else:
            prelaunch["next_incident_index"] = 2
        claim_path.chmod(0o644)
        claim_path.write_bytes(publication.canonical_json_bytes(claim))
        claim_path.chmod(0o444)

    result = _run(
        root,
        replace(
            _operations(calls, {}),
            record_prelaunch=mutate_durable_record,
        ),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert calls == []


@pytest.mark.parametrize(
    "mutation",
    ["nested_incident_index_bool", "registered_runs_bool"],
)
def test_prelaunch_evidence_rejects_bool_for_frozen_integer(
    tmp_path,
    mutation,
):
    root = _repository(tmp_path)
    configuration = _configuration(root)
    record = coordinator._complete_prelaunch_checks(
        repository_root=root,
        configuration=configuration,
        actual_invocation=configuration["invocation"],
        history=coordinator._read_incident_history(
            root,
            production_only=False,
        ),
        operations=_operations([], {}),
    )
    evidence = json.loads(record.evidence_bytes)
    if mutation == "nested_incident_index_bool":
        evidence["checks"][3]["evidence"]["next_incident_index"] = True
    else:
        evidence["checks"][5]["evidence"]["execution_rule"][
            "registered_runs"
        ] = True

    with pytest.raises(ValueError):
        coordinator._validate_prelaunch_record_value(evidence)


def test_canonical_invocation_is_exact_checked_before_input_load(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration = _configuration(root)
    sentinel = Path(
        configuration["invocation"][4].removeprefix("pycache_prefix=")
    )
    monkeypatch.setattr(
        coordinator,
        "sys",
        SimpleNamespace(
            flags=SimpleNamespace(
                isolated=True,
                dont_write_bytecode=True,
            ),
            pycache_prefix=str(sentinel),
        ),
    )
    calls: list[str] = []
    operations = replace(
        _operations(calls, {}),
        assert_interpreter=coordinator._assert_sealed_interpreter,
    )
    drifted_invocation = list(configuration["invocation"])
    drifted_invocation[-1] += ".changed"

    result = _run(
        root,
        operations,
        configuration_bytes=publication.canonical_json_bytes(configuration),
        actual_invocation=drifted_invocation,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_invocation_drift"
    assert calls == []


def test_incident_echo_comes_from_unchanged_registered_bytes(tmp_path):
    root = _repository(tmp_path)
    registered_bytes = _configuration_bytes(root)
    operations = _operations([], {})

    def mutate_then_abort(**kwargs):
        kwargs["configuration_echo"]["registration_reference"] = "mutated"
        raise RuntimeError("mutated fixture echo")

    operations = replace(operations, build_artifact=mutate_then_abort)
    result = _run(
        root,
        operations,
        configuration_bytes=registered_bytes,
    )

    assert result.status == "incident"
    assert result.phase == "invariant"
    record = json.loads(result.path.read_bytes())
    assert (
        publication.canonical_json_bytes(record["configuration_echo"])
        == registered_bytes
    )


@pytest.mark.parametrize(
    ("failure_phase", "expected_calls"),
    [
        ("preparation", ["preparation"]),
        ("compute", ["preparation", "compute"]),
    ],
)
def test_external_failure_is_eligible_but_coordinator_does_not_self_rescue(
    tmp_path,
    failure_phase,
    expected_calls,
):
    root = _repository(tmp_path)
    calls: list[str] = []
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    operations = _operations(
        calls,
        {},
        failure_phase=failure_phase,
        failure=external,
    )
    original_publish = operations.publish_incident

    def publish_before_authority(*args, **kwargs):
        authority_path = (
            root / "runs/anchor_context_report_retry_authority.claim"
        )
        assert authority_path.is_file()
        assert authority_path.read_bytes() == b""
        return original_publish(*args, **kwargs)

    result = _run(
        root,
        replace(
            operations,
            publish_incident=publish_before_authority,
        ),
    )

    assert result.status == "incident"
    record = json.loads(result.path.read_bytes())
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
    assert publication.incident_is_retry_eligible(record)
    attempt_path = root / "runs/anchor_context_report_attempt.claim"
    authority_path = root / "runs/anchor_context_report_retry_authority.claim"
    attempt_bytes = attempt_path.read_bytes()
    authority_bytes = authority_path.read_bytes()
    authority = json.loads(authority_bytes)
    assert set(authority) == {
        "schema_version",
        "registration_reference",
        "configuration_sha256",
        "attempt_claim_sha256",
        "authority_nonce",
        "incident_index",
        "incident_path",
        "incident_sha256",
        "estimate_bearing_information_yielded",
    }
    assert authority == {
        "schema_version": "anchor_context_report_retry_authority.v1",
        "registration_reference": REGISTRATION_REFERENCE,
        "configuration_sha256": hashlib.sha256(
            _configuration_bytes(root)
        ).hexdigest(),
        "attempt_claim_sha256": hashlib.sha256(attempt_bytes).hexdigest(),
        "authority_nonce": authority["authority_nonce"],
        "incident_index": 1,
        "incident_path": ("runs/anchor_context_report_incident_1.json"),
        "incident_sha256": hashlib.sha256(
            result.path.read_bytes()
        ).hexdigest(),
        "estimate_bearing_information_yielded": False,
    }
    assert len(authority["authority_nonce"]) == 64
    attempt = json.loads(attempt_bytes)
    assert (
        hashlib.sha256(
            authority["authority_nonce"].encode("ascii")
        ).hexdigest()
        == attempt["authority_nonce_sha256"]
    )
    authority_metadata = authority_path.stat()
    assert (
        attempt["authority_device"],
        attempt["authority_inode"],
    ) == (authority_metadata.st_dev, authority_metadata.st_ino)
    assert calls == expected_calls
    assert (
        len(
            list((root / "runs").glob("anchor_context_report_incident_*.json"))
        )
        == 1
    )
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()


def test_forged_external_incident_cannot_retroactively_create_attempt_claim(
    tmp_path,
):
    root = _repository(tmp_path)
    forged = _publish_external_incident(root)
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert forged.is_file()
    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == "preparation_retry_authority_missing_or_invalid"
    assert calls == []
    assert not (root / "runs/anchor_context_report_attempt.claim").exists()
    assert not (root / "runs/anchor_context_report_retry.claim").exists()
    assert not (
        root / "runs/anchor_context_report_retry_authority.claim"
    ).exists()


def test_hard_failure_then_forged_incident_cannot_claim_retry(tmp_path):
    root = _repository(tmp_path)
    operations = _operations([], {})

    def hard_crash():
        raise RuntimeError("simulated unrecorded hard failure")

    with pytest.raises(RuntimeError, match="unrecorded hard failure"):
        _run(root, replace(operations, after_preparation=hard_crash))

    attempt_path = root / "runs/anchor_context_report_attempt.claim"
    authority_path = root / "runs/anchor_context_report_retry_authority.claim"
    attempt_bytes = attempt_path.read_bytes()
    assert authority_path.read_bytes() == b""
    _publish_external_incident(root)
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.reason == "preparation_retry_authority_missing_or_invalid"
    assert calls == []
    assert attempt_path.read_bytes() == attempt_bytes
    assert authority_path.read_bytes() == b""
    assert not (root / "runs/anchor_context_report_retry.claim").exists()


def test_self_consistent_forged_provenance_cannot_claim_retry(tmp_path):
    root = _repository(tmp_path)
    configuration_bytes = _configuration_bytes(root)
    configuration = json.loads(configuration_bytes)
    history = coordinator._read_incident_history(
        root,
        production_only=False,
    )
    prelaunch = coordinator._complete_prelaunch_checks(
        repository_root=root,
        configuration=configuration,
        actual_invocation=configuration["invocation"],
        history=history,
        operations=_operations([], {}),
    )
    authority_path = root / coordinator._RETRY_AUTHORITY_PATH
    descriptor = os.open(
        authority_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o400,
    )
    authority_metadata = os.fstat(descriptor)
    os.close(descriptor)
    nonce = "a" * 64
    attempt_payload = coordinator._attempt_claim_payload(
        registration_reference=REGISTRATION_REFERENCE,
        configuration_sha256=hashlib.sha256(configuration_bytes).hexdigest(),
        next_incident_index=1,
        authority_file_id=(
            authority_metadata.st_dev,
            authority_metadata.st_ino,
        ),
        authority_nonce_sha256=hashlib.sha256(
            nonce.encode("ascii")
        ).hexdigest(),
        prelaunch_record=prelaunch,
    )
    attempt_path = root / coordinator._ATTEMPT_CLAIM_PATH
    coordinator._write_claim(attempt_path, attempt_payload)
    incident_path = _publish_external_incident(root)
    authority_payload = coordinator._retry_authority_payload(
        registration_reference=REGISTRATION_REFERENCE,
        configuration_sha256=hashlib.sha256(configuration_bytes).hexdigest(),
        attempt_claim_sha256=hashlib.sha256(attempt_payload).hexdigest(),
        authority_nonce=nonce,
        incident_index=1,
        incident_path=incident_path.relative_to(root).as_posix(),
        incident_sha256=hashlib.sha256(incident_path.read_bytes()).hexdigest(),
    )
    authority_path.chmod(0o600)
    authority_path.write_bytes(authority_payload)
    authority_path.chmod(0o400)
    forged_history = coordinator._read_incident_history(
        root,
        production_only=False,
    )
    with pytest.raises(TypeError, match="sealed coordinator stack"):
        coordinator._authorize_invocation(
            root,
            configuration,
            forged_history,
            None,
            False,
        )
    assert not any(
        isinstance(cell.cell_contents, dict)
        for cell in coordinator._authorize_invocation.__closure__
    )
    forged_receipt = object.__new__(coordinator._RetryReceipt)
    incident_metadata = incident_path.stat()
    attempt_metadata = attempt_path.stat()
    authority_metadata = authority_path.stat()
    forged_state = SimpleNamespace(
        receipt=forged_receipt,
        repository_root=root,
        registration_reference=REGISTRATION_REFERENCE,
        configuration_sha256=hashlib.sha256(configuration_bytes).hexdigest(),
        incident_index=1,
        incident_path=incident_path,
        incident_payload=incident_path.read_bytes(),
        incident_file_id=(
            incident_metadata.st_dev,
            incident_metadata.st_ino,
        ),
        incident_phase="compute",
        incident_reason="external_fixture_storage_unavailable",
        estimate_bearing_information_yielded=False,
        attempt_claim=attempt_path,
        attempt_payload=attempt_payload,
        attempt_file_id=(
            attempt_metadata.st_dev,
            attempt_metadata.st_ino,
        ),
        authority_path=authority_path,
        authority_payload=authority_payload,
        authority_file_id=(
            authority_metadata.st_dev,
            authority_metadata.st_ino,
        ),
        production_only=False,
        consumed=False,
    )
    object.__setattr__(forged_receipt, "_state", forged_state)
    calls: list[str] = []

    blocked = _run_attempt(
        root,
        _operations(calls, {}),
        retry_receipt=forged_receipt,
        configuration_bytes=configuration_bytes,
    ).result

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_retry_provenance_not_coordinator_published"
    )
    assert calls == []
    assert not (root / coordinator._RETRY_CLAIM_PATH).exists()


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "registration_reference",
        "configuration_sha256",
        "attempt_claim_sha256",
        "authority_nonce",
        "incident_index",
        "incident_path",
        "incident_sha256",
        "estimate_bearing_information_yielded",
    ],
)
def test_retry_authority_rejects_every_field_mutation(tmp_path, field):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    first = _run(
        root,
        _operations(
            [],
            {},
            failure_phase="compute",
            failure=external,
        ),
    )
    assert first.status == "incident"
    authority_path = root / "runs/anchor_context_report_retry_authority.claim"
    authority = json.loads(authority_path.read_bytes())
    if field == "incident_index":
        authority[field] = 2
    elif field == "estimate_bearing_information_yielded":
        authority[field] = True
    elif field == "incident_path":
        authority[field] = "runs/anchor_context_report_incident_2.json"
    elif field.endswith("sha256") or field == "authority_nonce":
        authority[field] = (
            "f" * 64 if authority[field] != "f" * 64 else "e" * 64
        )
    else:
        authority[field] = f"{authority[field]}-mutated"
    authority_path.chmod(0o644)
    authority_path.write_bytes(publication.canonical_json_bytes(authority))
    authority_path.chmod(0o444)
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert calls == []
    assert not (root / "runs/anchor_context_report_retry.claim").exists()


@pytest.mark.parametrize(
    "mutation",
    ["missing", "empty", "partial", "noncanonical", "inode_replacement"],
)
def test_retry_authority_requires_exact_reserved_canonical_file(
    tmp_path,
    mutation,
):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    assert (
        _run(
            root,
            _operations(
                [],
                {},
                failure_phase="compute",
                failure=external,
            ),
        ).status
        == "incident"
    )
    authority_path = root / "runs/anchor_context_report_retry_authority.claim"
    original = authority_path.read_bytes()
    authority_path.chmod(0o644)
    if mutation == "missing":
        authority_path.unlink()
    elif mutation == "empty":
        authority_path.write_bytes(b"")
    elif mutation == "partial":
        authority_path.write_bytes(original[: max(1, len(original) // 2)])
    elif mutation == "noncanonical":
        authority_path.write_bytes(b" " + original)
    else:
        displaced = authority_path.with_suffix(".displaced")
        authority_path.rename(displaced)
        authority_path.write_bytes(original)
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert calls == []
    assert not (root / "runs/anchor_context_report_retry.claim").exists()


@pytest.mark.parametrize(
    "target",
    ["attempt", "attempt_prelaunch", "incident"],
)
def test_retry_authority_rejects_bound_record_mutation(tmp_path, target):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    first = _run(
        root,
        _operations(
            [],
            {},
            failure_phase="compute",
            failure=external,
        ),
    )
    assert first.status == "incident"
    if target in {"attempt", "attempt_prelaunch"}:
        path = root / "runs/anchor_context_report_attempt.claim"
        value = json.loads(path.read_bytes())
        if target == "attempt":
            value["authority_nonce_sha256"] = "0" * 64
        else:
            value["prelaunch_record"]["checks"][5]["evidence"][
                "acknowledged"
            ] = False
    else:
        path = first.path
        value = json.loads(path.read_bytes())
        value["reason_detail"] += " Changed after authority publication."
    path.chmod(0o644)
    path.write_bytes(publication.canonical_json_bytes(value))
    path.chmod(0o444)
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert calls == []
    assert not (root / "runs/anchor_context_report_retry.claim").exists()


def test_retry_claim_requires_live_opaque_authorization(tmp_path):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    assert (
        _run(
            root,
            _operations(
                [],
                {},
                failure_phase="compute",
                failure=external,
            ),
        ).status
        == "incident"
    )
    with pytest.raises(TypeError, match="minted only by the coordinator"):
        coordinator._RetryAuthorization()
    forged = object.__new__(coordinator._RetryAuthorization)
    for candidate in (1, Path("runs/incident.json"), forged):
        with pytest.raises(
            TypeError,
            match="live authenticated authorization",
        ):
            coordinator._create_retry_claim(root, candidate, object())
    assert not (root / "runs/anchor_context_report_retry.claim").exists()


def test_retry_claim_verifier_cannot_be_injected(tmp_path):
    root = _repository(tmp_path)
    _publish_external_incident(root)
    configuration = _configuration(root)
    record = coordinator._complete_prelaunch_checks(
        repository_root=root,
        configuration=configuration,
        actual_invocation=configuration["invocation"],
        history=coordinator._read_incident_history(
            root,
            production_only=False,
        ),
        operations=_operations([], {}),
    )
    forged_state = SimpleNamespace(
        registration_reference=REGISTRATION_REFERENCE,
        incident_index=1,
        authority_payload=b"caller-selected authority",
    )

    with pytest.raises(TypeError):
        coordinator._create_retry_claim(
            root,
            object(),
            record,
            _require_authorization=lambda *_args: forged_state,
        )

    assert not (root / coordinator._RETRY_CLAIM_PATH).exists()


@pytest.mark.parametrize(
    ("reader_name", "claim_name"),
    [
        ("canonical", "anchor_context_report_attempt.claim"),
        ("attempt", "anchor_context_report_attempt.claim"),
        ("authority", "anchor_context_report_retry_authority.claim"),
        ("retry", "anchor_context_report_retry.claim"),
    ],
)
@pytest.mark.parametrize(
    "protected_path",
    [
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    ],
)
def test_claim_readers_reject_every_production_alias_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reader_name: str,
    claim_name: str,
    protected_path: str,
):
    read_attempts = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("production bytes reached os.read")

    monkeypatch.setattr(coordinator.os, "read", forbidden_read)
    for alias_kind in ("direct", "hardlink", "symlink", "reverse_symlink"):
        root = tmp_path / alias_kind
        (root / "runs").mkdir(parents=True)
        protected = root / protected_path
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_bytes(b'{"estimate_bearing":true}\n')
        claim = root / "runs" / claim_name
        if alias_kind == "direct":
            candidate = protected
        elif alias_kind == "hardlink":
            os.link(protected, claim)
            candidate = claim
        elif alias_kind == "symlink":
            claim.symlink_to(protected)
            candidate = claim
        else:
            payload = protected.read_bytes()
            protected.unlink()
            claim.write_bytes(payload)
            protected.symlink_to(claim)
            candidate = claim

        if reader_name == "canonical":
            result = coordinator._read_canonical_mapping(
                candidate,
                maximum_bytes=coordinator._CLAIM_MAX_BYTES,
                expected_name=claim_name,
            )
        elif reader_name == "attempt":
            result = coordinator._read_attempt_claim(candidate)
        elif reader_name == "authority":
            result = coordinator._read_retry_authority(candidate)
        else:
            result = coordinator._read_retry_claim(candidate)
        assert result is None

    assert read_attempts == 0


@pytest.mark.parametrize(
    "mutation", ["same_inode_rewrite", "name_replacement"]
)
def test_canonical_mapping_rejects_equal_size_mutation_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
):
    runs = tmp_path / "runs"
    runs.mkdir()
    candidate = runs / "anchor_context_report_retry.claim"
    candidate.write_bytes(b'{"value":"AAAA"}\n')
    replacement = b'{"value":"BBBB"}\n'
    original_read = coordinator.os.read
    mutated = False

    def mutate_after_read(descriptor, byte_count):
        nonlocal mutated
        chunk = original_read(descriptor, byte_count)
        if chunk and not mutated:
            mutated = True
            if mutation == "same_inode_rewrite":
                candidate.write_bytes(replacement)
                metadata = candidate.stat()
                os.utime(
                    candidate,
                    ns=(
                        metadata.st_atime_ns,
                        metadata.st_mtime_ns + 1_000_000,
                    ),
                )
            else:
                candidate.rename(candidate.with_suffix(".displaced"))
                candidate.write_bytes(replacement)
        return chunk

    monkeypatch.setattr(coordinator.os, "read", mutate_after_read)

    loaded = coordinator._read_canonical_mapping(
        candidate,
        maximum_bytes=coordinator._CLAIM_MAX_BYTES,
        expected_name=candidate.name,
    )

    assert mutated is True
    assert loaded is None


def test_retry_receipt_never_escapes_to_a_later_fixture_invocation(tmp_path):
    root = _repository(tmp_path)
    registered_bytes = _configuration_bytes(root)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    first = _run(
        root,
        _operations(
            [],
            {},
            failure_phase="compute",
            failure=external,
        ),
        configuration_bytes=registered_bytes,
    )
    attempt_path = root / "runs/anchor_context_report_attempt.claim"
    authority_path = root / "runs/anchor_context_report_retry_authority.claim"
    attempt_bytes = attempt_path.read_bytes()
    authority_bytes = authority_path.read_bytes()

    calls: list[str] = []
    blocked = _run(
        root,
        _operations(calls, {}),
        configuration_bytes=registered_bytes,
    )

    assert first.status == "incident"
    assert blocked.status == "incident"
    assert blocked.reason == (
        "preparation_retry_provenance_not_coordinator_published"
    )
    assert calls == []
    assert not (root / "runs/anchor_context_report_retry.claim").exists()
    assert attempt_path.read_bytes() == attempt_bytes
    assert authority_path.read_bytes() == authority_bytes


def test_coordinator_owned_receipt_allows_exactly_one_report_first_retry(
    tmp_path,
):
    root = _repository(tmp_path)
    registered_bytes = _configuration_bytes(root)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    calls: list[str] = []
    captured: dict[str, Any] = {}
    successful = _operations(calls, captured)
    original_build = successful.build_results
    attempts = 0

    def fail_once(authority, loaded_inputs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            calls.append("compute")
            raise external
        return original_build(authority, loaded_inputs)

    operations = replace(successful, build_results=fail_once)
    first = _run_attempt(
        root,
        operations,
        configuration_bytes=registered_bytes,
    )

    assert first.result.status == "incident"
    assert isinstance(first.retry_receipt, coordinator._RetryReceipt)
    assert first.retry_receipt._state.production_only is False
    with pytest.raises(FrozenInstanceError):
        first.retry_receipt._state.production_only = True
    second = _run_attempt(
        root,
        operations,
        retry_receipt=first.retry_receipt,
        configuration_bytes=registered_bytes,
    )

    assert second.result.status == "published"
    assert second.retry_receipt is None
    assert attempts == 2
    retry_claim = json.loads(
        (root / "runs/anchor_context_report_retry.claim").read_bytes()
    )
    assert retry_claim["retry_after_incident"] == 1
    assert retry_claim["prelaunch_record"]["checks"][3]["evidence"][
        "incident_history"
    ] == ["runs/anchor_context_report_incident_1.json"]
    with pytest.raises(TypeError, match="live authenticated authorization"):
        coordinator._create_retry_claim(
            root,
            object.__new__(coordinator._RetryAuthorization),
            second.result.path,
        )


def test_durable_attempt_claim_blocks_reentry_after_process_death(tmp_path):
    root = _repository(tmp_path)
    operations = _operations([], {})

    def hard_crash():
        raise RuntimeError("simulated hard process death")

    with pytest.raises(RuntimeError, match="hard process death"):
        _run(root, replace(operations, after_preparation=hard_crash))

    assert (root / "runs/anchor_context_report_attempt.claim").is_file()
    assert (
        root / "runs/anchor_context_report_retry_authority.claim"
    ).read_bytes() == b""
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert calls == []


def test_lost_retry_receipt_blocks_retry_after_process_death(
    tmp_path,
):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_fixture_storage_unavailable",
        "Fixture storage unavailable before output.",
    )
    assert (
        _run(
            root,
            _operations(
                [],
                {},
                failure_phase="compute",
                failure=external,
            ),
        ).status
        == "incident"
    )
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_retry_provenance_not_coordinator_published"
    )
    assert calls == []
    assert not (root / "runs/anchor_context_report_retry.claim").exists()
    incidents = sorted(
        (root / "runs").glob("anchor_context_report_incident_*.json")
    )
    assert [path.name for path in incidents] == [
        "anchor_context_report_incident_1.json",
        "anchor_context_report_incident_2.json",
    ]


def test_public_entry_point_exposes_only_registration_path():
    assert coordinator.CoordinatorResult is first_coordinator.CoordinatorResult
    assert set(
        inspect.signature(coordinator.run_registered_anchor_context).parameters
    ) == {"registration_path"}


def test_public_execution_law_cannot_mutate_private_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    with pytest.raises(TypeError):
        coordinator.CANONICAL_EXECUTION_RULE["no_self_rescue"] = False

    root = _repository(tmp_path)
    attacker_rule = {
        "registered_runs": 99,
        "publishes_regardless": False,
        "no_self_rescue": False,
        "retry": "attacker selected",
        "fresh_registration_required_if": "never",
    }
    monkeypatch.setattr(
        coordinator,
        "CANONICAL_EXECUTION_RULE",
        attacker_rule,
    )
    configuration = _configuration(root)
    record = coordinator._complete_prelaunch_checks(
        repository_root=root,
        configuration=configuration,
        actual_invocation=configuration["invocation"],
        history=coordinator._read_incident_history(
            root,
            production_only=False,
        ),
        operations=_operations([], {}),
    )
    evidence = json.loads(record.evidence_bytes)
    execution_rule = evidence["checks"][5]["evidence"]["execution_rule"]

    assert execution_rule["registered_runs"] == 1
    assert execution_rule["publishes_regardless"] is True
    assert execution_rule["no_self_rescue"] is True
    coordinator._prelaunch_record_value(record)


def test_public_runner_owns_fail_once_report_first_retry(
    tmp_path: Path,
):
    """The exported one-argument runner retains and consumes the receipt."""
    isolated = tmp_path / "isolated-public-runner"
    shutil.copytree(Path(__file__).parents[2] / "src", isolated / "src")
    publication_source = (
        isolated
        / "src/populace_dynamics/estimates/anchor_context_publication.py"
    )
    publication_source.write_text(
        publication_source.read_text().replace(
            "\n_seal_coordinator_authority_import()\n",
            "\n# Delayed only in this isolated import-order fixture.\n",
        )
    )
    script = isolated / "exercise_public_retry.py"
    script.write_text(textwrap.dedent("""
            import hashlib
            import inspect
            import json
            from pathlib import Path
            from types import SimpleNamespace

            from populace_dynamics.estimates import (
                anchor_context_publication as publication,
            )
            from populace_dynamics.estimates import (
                anchor_context_registry as registry,
            )
            from populace_dynamics.estimates import (
                anchor_context_report as report,
            )
            from populace_dynamics.estimates import coordinator as first

            root = Path.cwd()
            (root / "runs").mkdir()
            registration = root / "docs/registrations/context.json"
            registration.parent.mkdir(parents=True)
            sentinel = root / "fresh-empty-pycache"
            sentinel.mkdir()
            invocation = [
                "python",
                "-I",
                "-B",
                "-X",
                f"pycache_prefix={sentinel}",
                "scripts/run_anchor_context_report.py",
                "--registration",
                str(registration),
            ]
            configuration = publication.registered_configuration_echo(
                registration_reference="public-retry-ownership",
                implementation_commit="c" * 40,
                invocation=invocation,
            )
            registration.write_bytes(
                publication.canonical_json_bytes(configuration)
            )

            publication.prepare_environment_sidecar = (
                lambda _root: (b"{}\\n", hashlib.sha256(b"{}\\n").hexdigest())
            )
            publication.validate_environment_sidecar_payload = (
                lambda _payload: {}
            )
            publication._validate_runtime_provenance = (
                lambda _value, **_kwargs: None
            )
            publication._load_production_documents = lambda _authority: object()
            publication._require_verified_production_inputs = (
                lambda _bundle, **_kwargs: ({}, {})
            )
            publication.build_runtime_provenance = lambda commit: {
                "schema_version": publication.RUNTIME_PROVENANCE_SCHEMA_VERSION,
                "implementation_commit": commit,
                "python": "fixture",
                "platform": "fixture",
            }
            publication.build_anchor_context_artifact = (
                lambda **kwargs: {
                    "configuration_echo": kwargs["configuration_echo"],
                    "prior_incidents": list(kwargs["prior_incidents"]),
                }
            )

            attempts = 0

            def fail_once(_authority, _inputs):
                global attempts
                attempts += 1
                if attempts == 1:
                    raise first.ExternalPreOutputFailure(
                        "external_fixture_storage_unavailable",
                        "Fixture storage unavailable before output.",
                    )
                return {"attempt": attempts}

            report._build_production_results = fail_once
            report._validate_production_results = (
                lambda _authority, _results, _inputs: None
            )

            def publish(_token, artifact, **_kwargs):
                path = root / registry.PRIMARY_OUTPUT_PATH
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(publication.canonical_json_bytes(artifact))
                return path

            publication.write_anchor_context_artifact = publish

            from populace_dynamics.estimates import (
                anchor_context_coordinator as coordinator,
            )

            coordinator.sys = SimpleNamespace(
                orig_argv=invocation,
                flags=SimpleNamespace(
                    isolated=True,
                    dont_write_bytecode=True,
                ),
                pycache_prefix=str(sentinel),
            )

            def git_bytes(_repository, *arguments):
                if arguments == ("rev-parse", "--show-toplevel"):
                    return f"{root}\\n".encode()
                if arguments == ("rev-parse", "HEAD"):
                    return b"cccccccccccccccccccccccccccccccccccccccc\\n"
                return b""

            coordinator._git_bytes = git_bytes
            result = coordinator.run_registered_anchor_context(registration)

            assert result.status == "published"
            assert attempts == 2
            assert not hasattr(result, "retry_receipt")
            assert set(
                inspect.signature(
                    coordinator.run_registered_anchor_context
                ).parameters
            ) == {"registration_path"}
            assert [
                path.name
                for path in (root / "runs").glob(
                    "anchor_context_report_incident_*.json"
                )
            ] == ["anchor_context_report_incident_1.json"]
            retry_claim = json.loads(
                (
                    root / "runs/anchor_context_report_retry.claim"
                ).read_bytes()
            )
            assert retry_claim["retry_after_incident"] == 1
            artifact = json.loads(result.path.read_bytes())
            assert artifact["prior_incidents"] == [
                "runs/anchor_context_report_incident_1.json"
            ]
            """))
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=isolated,
        env={
            **os.environ,
            "PYTHONPATH": str(isolated / "src"),
        },
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_ceremony_capability_is_not_caller_constructible():
    with pytest.raises(TypeError, match="minted only by the coordinator"):
        coordinator._CeremonyCapability()
    with pytest.raises(TypeError, match="issued only by the coordinator"):
        coordinator._CoordinatorInvocation()
    with pytest.raises(TypeError, match="minted only by the coordinator"):
        coordinator._RetryReceipt()
    with pytest.raises(TypeError, match="created only by the coordinator"):
        coordinator._CoordinatorAttemptOutcome()
    assert not hasattr(coordinator, "_mint_ceremony_capability")
    assert not hasattr(coordinator, "_issue_coordinator_invocation")
    for protocol_factory in (
        "_retry_authority_protocol",
        "_retry_claim_protocol",
        "_ceremony_capability_protocol",
        "_build_registered_anchor_context_core",
        "_execution_rule_protocol",
    ):
        assert not hasattr(coordinator, protocol_factory)


def test_direct_production_core_cannot_forge_ceremony_or_retry_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "direct-production-core"
    (root / "runs").mkdir(parents=True)
    invocation = _invocation(root)
    configuration = publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=invocation,
    )
    calls: list[str] = []
    fake_mint_calls: list[object] = []

    def fail_after_claim(_authority):
        calls.append("production_input")
        raise coordinator.ExternalPreOutputFailure(
            "external_fixture_storage_unavailable",
            "Fixture storage unavailable before output.",
        )

    def fake_mint(*_args):
        fake_mint_calls.append(object())
        return object()

    operations = replace(
        _operations(calls, {}),
        assert_interpreter=lambda _configuration, _invocation: None,
        validate_repository=lambda _root, _configuration: None,
        load_inputs=fail_after_claim,
    )
    monkeypatch.setattr(
        coordinator,
        "_require_coordinator_invocation",
        lambda *_args: None,
    )
    arguments = {
        "repository_root": root,
        "registered_configuration_bytes": (
            publication.canonical_json_bytes(configuration)
        ),
        "actual_invocation": invocation,
        "operations": operations,
        "production_only": True,
        "coordinator_invocation": object(),
        "retry_receipt": None,
        "mint_capability": fake_mint,
        "revoke_capability": lambda _capability: None,
        "issue_initial_attempt": coordinator._issue_initial_attempt,
        "require_initial_attempt": coordinator._require_initial_attempt,
        "seal_retry_authority": coordinator._seal_retry_authority,
        "revoke_initial_attempt": coordinator._revoke_initial_attempt,
        "authorize_invocation": coordinator._authorize_invocation,
        "create_retry_claim": coordinator._create_retry_claim,
        "require_retry_authorization": (
            coordinator._require_retry_authorization
        ),
        "revoke_retry_authorization": (
            coordinator._revoke_retry_authorization
        ),
    }
    with pytest.raises(TypeError, match="sealed production invocation"):
        coordinator._run_registered_anchor_context_core(**arguments)

    assert calls == []
    assert fake_mint_calls == []
    assert list((root / "runs").iterdir()) == []


def test_rebound_production_verifiers_cannot_reach_io_or_compute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _repository(tmp_path)
    invocation = _invocation(root)
    configuration = publication.registered_configuration_echo(
        registration_reference=REGISTRATION_REFERENCE,
        implementation_commit=IMPLEMENTATION_COMMIT,
        invocation=invocation,
    )
    registration = publication.first_publication._RegisteredConfigurationToken(
        _repository_root=root,
        _registration_reference=REGISTRATION_REFERENCE,
        _configuration_bytes=publication.canonical_json_bytes(configuration),
    )
    fixture_bundle = publication.load_fixture_documents(root)
    fixture_documents = publication._require_verified_fixture_inputs(
        fixture_bundle
    )
    opened_paths: list[str] = []

    def reached_production_open(_authority, _root, relative_path):
        opened_paths.append(relative_path)
        raise AssertionError("production path reached descriptor open")

    monkeypatch.setattr(
        coordinator,
        "_require_ceremony_capability",
        lambda _candidate: registration,
    )
    monkeypatch.setattr(
        publication,
        "_require_verified_production_inputs",
        lambda *_args, **_kwargs: fixture_documents,
    )
    monkeypatch.setattr(
        publication,
        "_open_regular_relative",
        reached_production_open,
    )

    with pytest.raises(TypeError, match="live ceremony capability"):
        publication._load_production_documents(object())
    with pytest.raises(TypeError, match="live ceremony capability"):
        report._build_production_results(object(), object())

    assert opened_paths == []


def test_extracted_closure_issuers_reject_caller_created_prerequisites(
    tmp_path: Path,
):
    root = _repository(tmp_path)
    registration = coordinator._parse_configuration(
        repository_root=root,
        registered_configuration_bytes=_configuration_bytes(root),
        production_only=False,
    )
    claim = root / "runs/anchor_context_report_attempt.claim"
    record = coordinator._PrelaunchRecord(
        check_names=coordinator.PRELAUNCH_CHECK_NAMES,
        configuration_sha256=hashlib.sha256(
            _configuration_bytes(root)
        ).hexdigest(),
        next_incident_index=1,
        evidence_bytes=b"{}\n",
    )
    closure = dict(
        zip(
            coordinator.run_registered_anchor_context.__code__.co_freevars,
            coordinator.run_registered_anchor_context.__closure__,
            strict=True,
        )
    )
    extracted_mint = closure["mint"].cell_contents
    extracted_issue = closure["issue_invocation"].cell_contents

    with pytest.raises(TypeError, match="sealed runner stack"):
        extracted_mint(
            registration,
            record,
            claim,
            None,
            None,
            None,
        )
    with pytest.raises(TypeError, match="sealed runner stack"):
        extracted_issue(
            root,
            _configuration_bytes(root),
            _invocation(root),
            _operations([], {}),
            None,
        )


def test_fixture_runner_authority_is_rejected_by_every_production_gate(
    tmp_path: Path,
):
    root = _repository(tmp_path)
    operations = _operations([], {})
    original_load = operations.load_inputs

    def probe_production_gates(registration):
        assert isinstance(
            registration,
            publication.first_publication._RegisteredConfigurationToken,
        )
        with pytest.raises(TypeError, match="live ceremony capability"):
            publication._load_production_documents(registration)
        with pytest.raises(TypeError, match="live ceremony capability"):
            report._build_production_results(registration, object())
        with pytest.raises(TypeError, match="live ceremony capability"):
            report._validate_production_results(
                registration,
                {},
                object(),
            )
        with pytest.raises(TypeError, match="live ceremony capability"):
            publication.build_anchor_context_artifact(
                configuration_echo=publication.registered_configuration_echo(
                    registration_reference=REGISTRATION_REFERENCE,
                    implementation_commit=IMPLEMENTATION_COMMIT,
                    invocation=_invocation(root),
                ),
                runtime_provenance=RUNTIME_PROVENANCE,
                results={},
                input_bundle=object(),
                environment_sidecar_sha256="0" * 64,
                ceremony_capability=registration,
            )
        return original_load(registration)

    result = _run(
        root,
        replace(operations, load_inputs=probe_production_gates),
    )

    assert result.status == "published"


def test_public_runner_dependencies_cannot_be_rebound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    attacker_calls: list[str] = []
    root = tmp_path / "attacker-repository"
    registration_path = root / "docs/registrations/context.json"
    registration_path.parent.mkdir(parents=True)
    registration_path.write_bytes(b"attacker-selected bytes")

    def reached(label):
        def fail(*_args, **_kwargs):
            attacker_calls.append(label)
            raise AssertionError(f"rebound {label} was reached")

        return fail

    monkeypatch.setattr(
        coordinator,
        "_sealed_repository_root",
        reached("repository root"),
    )
    monkeypatch.setattr(
        coordinator,
        "_read_registered_configuration_bytes",
        reached("registration reader"),
    )
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        reached("operation factory"),
    )
    monkeypatch.setattr(
        coordinator,
        "_run_registered_anchor_context_core",
        reached("coordinator core"),
    )

    with pytest.raises(ValueError, match="escapes the repository"):
        coordinator.run_registered_anchor_context(registration_path)

    assert attacker_calls == []


def test_functiontype_clone_with_replacement_ceremony_dependencies_fails_closed(
    tmp_path: Path,
):
    original = coordinator.run_registered_anchor_context
    closure = dict(
        zip(
            original.__code__.co_freevars,
            original.__closure__,
            strict=True,
        )
    )
    attacker_calls: list[str] = []

    def reached(label):
        def fail(*_args, **_kwargs):
            attacker_calls.append(label)
            raise AssertionError(f"replacement {label} was reached")

        return fail

    original_operations = closure["production_operations"].cell_contents
    replacements = {
        "sealed_repository_root": tmp_path / "replacement-root",
        "read_registered_configuration_bytes": reached("reader"),
        "exclusive_ceremony_lock": reached("lock"),
        "production_operations": replace(
            original_operations,
            load_inputs=reached("production input"),
            build_results=reached("production compute"),
        ),
    }

    def cell(value):
        def capture():
            return value

        return capture.__closure__[0]

    cloned_closure = tuple(
        cell(replacements[name]) if name in replacements else closure[name]
        for name in original.__code__.co_freevars
    )
    clone = FunctionType(
        original.__code__,
        original.__globals__,
        "cloned_run_registered_anchor_context",
        original.__defaults__,
        cloned_closure,
    )
    clone.__kwdefaults__ = original.__kwdefaults__

    with pytest.raises(TypeError, match="runner provenance changed"):
        clone(tmp_path / "docs/registrations/attacker.json")

    assert attacker_calls == []
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize(
    "protected_path",
    [
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    ],
)
def test_public_entry_rejects_production_input_as_registration_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protected_path: str,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    attempted_reads: list[Path] = []

    def forbidden_read(path: Path):
        attempted_reads.append(path)
        raise AssertionError("protected production input was read")

    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(Path, "read_bytes", forbidden_read)

    with pytest.raises(ValueError, match="protected ceremony data"):
        coordinator.run_registered_anchor_context(protected_path)

    assert attempted_reads == []


@pytest.mark.parametrize(
    "protected_path",
    [
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    ],
)
def test_public_entry_rejects_hardlinked_production_registration_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protected_path: str,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    protected = root / protected_path
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_bytes(b"protected production bytes")
    registration = root / "docs/registrations/alias.json"
    registration.parent.mkdir(parents=True)
    os.link(protected, registration)
    read_attempts = 0
    successful_leaf_opens = 0
    original_open = coordinator.os.open

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("hardlinked production bytes were read")

    def count_leaf_open(path, flags, *args, **kwargs):
        nonlocal successful_leaf_opens
        descriptor = original_open(path, flags, *args, **kwargs)
        if path == registration.name:
            successful_leaf_opens += 1
        return descriptor

    monkeypatch.setattr(coordinator.os, "open", count_leaf_open)
    monkeypatch.setattr(coordinator.os, "read", forbidden_read)

    with pytest.raises(ValueError, match="singly linked|aliases protected"):
        coordinator._read_registered_configuration_bytes(root, registration)

    assert read_attempts == 0
    assert successful_leaf_opens == 0


@pytest.mark.parametrize(
    "symlink_component", ["docs", "registrations", "leaf"]
)
def test_registration_descriptor_gate_rejects_symlink_components_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    symlink_component: str,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "registrations").mkdir(parents=True)
    (outside / "registrations/registration.json").write_bytes(b"{}\n")
    if symlink_component == "docs":
        (root / "docs").symlink_to(outside, target_is_directory=True)
    else:
        (root / "docs").mkdir()
        if symlink_component == "registrations":
            (root / "docs/registrations").symlink_to(
                outside / "registrations",
                target_is_directory=True,
            )
        else:
            (root / "docs/registrations").mkdir()
            (root / "docs/registrations/registration.json").symlink_to(
                outside / "registrations/registration.json"
            )
    read_attempts = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("symlinked registration bytes were read")

    monkeypatch.setattr(coordinator.os, "read", forbidden_read)

    with pytest.raises(OSError):
        coordinator._read_registered_configuration_bytes(
            root, "docs/registrations/registration.json"
        )

    assert read_attempts == 0


def test_registration_gate_rejects_reverse_production_symlink_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    registration = root / "docs/registrations/registration.json"
    registration.parent.mkdir(parents=True)
    registration.write_bytes(b"{}\n")
    protected = root / registry.FIRST_ESTIMATES_INPUT_PATH
    protected.symlink_to(registration)
    read_attempts = 0

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("reverse-aliased registration bytes were read")

    monkeypatch.setattr(coordinator.os, "read", forbidden_read)

    with pytest.raises(
        ValueError, match="production input path is not regular"
    ):
        coordinator._read_registered_configuration_bytes(root, registration)

    assert read_attempts == 0


def test_registration_gate_rejects_preopen_inode_exchange_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    registration = root / "docs/registrations/registration.json"
    registration.parent.mkdir(parents=True)
    registration.write_bytes(b'{"safe":"registration"}\n')
    protected = root / registry.FIRST_ESTIMATES_INPUT_PATH
    protected.write_bytes(b"protected production bytes")
    original_open = coordinator.os.open
    exchanged = False
    read_attempts = 0

    def exchange_before_leaf_open(path, flags, *args, **kwargs):
        nonlocal exchanged
        if path == registration.name and not exchanged:
            exchanged = True
            temporary = root / "exchange.tmp"
            registration.rename(temporary)
            protected.rename(registration)
            temporary.rename(protected)
        return original_open(path, flags, *args, **kwargs)

    def forbidden_read(*_args, **_kwargs):
        nonlocal read_attempts
        read_attempts += 1
        raise AssertionError("exchanged production bytes were read")

    monkeypatch.setattr(coordinator.os, "open", exchange_before_leaf_open)
    monkeypatch.setattr(coordinator.os, "read", forbidden_read)

    with pytest.raises(ValueError, match="aliases protected ceremony data"):
        coordinator._read_registered_configuration_bytes(root, registration)

    assert exchanged is True
    assert read_attempts == 0
