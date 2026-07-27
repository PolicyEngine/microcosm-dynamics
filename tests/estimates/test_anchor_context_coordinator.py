"""Fixture-only tests for the registered anchor-context coordinator."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
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
    root = tmp_path / "repo"
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
        root = registration._repository_root
        configuration_echo = publication.first_publication._configuration_echo(
            registration
        )
        loaded = publication.load_fixture_documents(
            root,
            first_estimates_input=configuration_echo["first_estimates_input"],
            anchor_input=configuration_echo["anchor_input"],
        )
        return maybe_fail("preparation", loaded)

    def build_results(
        first_estimates: dict[str, Any],
        anchors: dict[str, Any],
    ) -> dict[str, Any]:
        return maybe_fail(
            "compute",
            report.build_results(first_estimates, anchors),
        )

    def validate_results(
        results: dict[str, Any],
        *,
        first_estimates: dict[str, Any],
        anchors: dict[str, Any],
    ) -> None:
        report.validate_results(
            results,
            first_estimates=first_estimates,
            anchors=anchors,
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
        captured["publication_kwargs"] = kwargs
        return publication.write_anchor_context_artifact(*args, **kwargs)

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
    assert json.loads(attempt_claim.read_bytes()) == {
        "schema_version": "anchor_context_report_attempt.v1",
        "registration_reference": REGISTRATION_REFERENCE,
    }


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


def test_input_hash_failure_aborts_before_engine(tmp_path):
    root = _repository(tmp_path)
    configuration = _configuration(root)
    configuration["first_estimates_input"]["sha256"] = "0" * 64
    calls: list[str] = []

    result = _run(
        root,
        _operations(calls, {}),
        configuration_bytes=publication.canonical_json_bytes(configuration),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
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

    result = _run(
        root,
        _operations(
            calls,
            {},
            failure_phase=failure_phase,
            failure=external,
        ),
    )

    assert result.status == "incident"
    record = json.loads(result.path.read_bytes())
    assert publication.incident_is_retry_eligible(record)
    assert calls == expected_calls
    assert (
        len(
            list((root / "runs").glob("anchor_context_report_incident_*.json"))
        )
        == 1
    )
    assert not (root / registry.PRIMARY_OUTPUT_PATH).exists()


def test_one_later_invocation_may_retry_only_with_unchanged_bytes(tmp_path):
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

    captured: dict[str, Any] = {}
    retry = _run(
        root,
        _operations([], captured),
        configuration_bytes=registered_bytes,
    )

    assert first.status == "incident"
    assert retry.status == "published"
    assert json.loads(retry.path.read_bytes())["prior_incidents"] == [
        "runs/anchor_context_report_incident_1.json"
    ]
    assert (root / "runs/anchor_context_report_retry.claim").is_file()
    assert (
        publication.canonical_json_bytes(
            captured["artifact_kwargs"]["configuration_echo"]
        )
        == registered_bytes
    )

    drift_root = _repository(tmp_path / "drift")
    drift_bytes = _configuration_bytes(drift_root)
    assert (
        _run(
            drift_root,
            _operations(
                [],
                {},
                failure_phase="compute",
                failure=external,
            ),
            configuration_bytes=drift_bytes,
        ).status
        == "incident"
    )
    changed = json.loads(drift_bytes)
    changed["invocation"][-1] += ".changed"
    calls: list[str] = []
    blocked = _run(
        drift_root,
        _operations(calls, {}),
        configuration_bytes=publication.canonical_json_bytes(changed),
    )

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert calls == []


def test_durable_attempt_claim_blocks_reentry_after_process_death(tmp_path):
    root = _repository(tmp_path)
    coordinator._create_attempt_claim(
        root,
        REGISTRATION_REFERENCE,
        allow_matching_retry_claim=False,
    )
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert calls == []


def test_durable_retry_claim_blocks_a_second_retry_after_process_death(
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
    coordinator._create_retry_claim(
        root,
        REGISTRATION_REFERENCE,
        1,
    )
    calls: list[str] = []

    blocked = _run(root, _operations(calls, {}))

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_fresh_registration_required_retry_claim"
    )
    assert calls == []
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
