"""Fast tests for the nonpersistent first-estimates coordinator."""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from populace_dynamics.contract import ContractRef
from populace_dynamics.estimates import coordinator, publication, runner
from populace_dynamics.estimates.parameters import (
    ParameterDependencyUnavailable,
)
from populace_dynamics.harness.m6_candidate3_runner import (
    M6Candidate3InputPlan,
)

REGISTRATION = "issue-42-comment-1234567"
PARAMETER_PROVENANCE = {"bundle_sha256": "c" * 64}
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


@pytest.fixture(autouse=True)
def _fixed_sidecar_identity(monkeypatch):
    monkeypatch.setattr(publication, "environment_block", lambda: ENVIRONMENT)
    monkeypatch.setattr(
        publication.ContractRef,
        "current",
        staticmethod(lambda _root=None: CONTRACT),
    )


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "runs").mkdir(parents=True)
    return root


def _configuration_bytes(
    *,
    registration: str = REGISTRATION,
    provenance: dict | None = None,
) -> bytes:
    configuration = runner.registered_configuration_echo(
        registration_reference=registration,
        parameter_bundle=provenance or PARAMETER_PROVENANCE,
    )
    return publication.canonical_json_bytes(configuration)


def _operations(
    calls: list[str],
    captured: dict,
    *,
    failure_phase: str | None = None,
    failure: Exception | None = None,
    provenance: dict | None = None,
    sidecar_payload: bytes | None = None,
) -> coordinator._CoordinatorOperations:
    error = failure or RuntimeError("estimate sentinel [1, 2, 3]")

    def maybe_fail(phase: str, value):
        calls.append(phase)
        if failure_phase == phase:
            raise error
        return value

    def load_parameters():
        return maybe_fail(
            "load_parameters",
            SimpleNamespace(provenance=provenance or PARAMETER_PROVENANCE),
        )

    def prepare_sidecar(_root: Path):
        calls.append("prepare_sidecar")
        payload = sidecar_payload
        if payload is None:
            payload = publication.canonical_json_bytes(
                {
                    "environment": ENVIRONMENT,
                    "contract": asdict(CONTRACT),
                }
            )
        return payload, publication.hashlib.sha256(payload).hexdigest()

    def execute_projection(*args, **kwargs):
        captured["execute_args"] = args
        captured["execute_kwargs"] = kwargs
        return maybe_fail("compute", "projection-batch")

    def prepare_batch(batch, *, parameters):
        captured["prepared_parameters"] = parameters
        assert batch == "projection-batch"
        return maybe_fail("invariant", "prepared-batch")

    def build_artifact(prepared, **kwargs):
        assert prepared == "prepared-batch"
        captured["artifact_kwargs"] = kwargs
        return {"fixture": True, "prior_incidents": kwargs["prior_incidents"]}

    def publish_artifact(token, artifact):
        calls.append("publication")
        if failure_phase == "publication":
            raise error
        captured["published_token"] = token
        captured["published_artifact"] = artifact
        path = token._registration._repository_root / (
            publication.DEFAULT_ARTIFACT_PATH
        )
        path.write_text(json.dumps(artifact) + "\n")
        return path

    return coordinator._CoordinatorOperations(
        load_parameters=load_parameters,
        load_input_plan=lambda root: maybe_fail(
            "load_input_plan",
            ("input-plan", root),
        ),
        resolve_contract=lambda root: maybe_fail(
            "resolve_contract",
            ("resolved-contract", root),
        ),
        prepare_sidecar=prepare_sidecar,
        execute_projection=execute_projection,
        prepare_batch=prepare_batch,
        build_artifact=build_artifact,
        publish_artifact=publish_artifact,
        publish_incident=publication.write_first_estimates_incident,
    )


def _run(
    root: Path,
    operations: coordinator._CoordinatorOperations,
    *,
    registration: str = REGISTRATION,
    configuration_bytes: bytes | None = None,
    retry_after_incident: int | None = None,
) -> coordinator.CoordinatorResult:
    return coordinator._run_registered_first_estimates_for_test(
        repository_root=root,
        registration_reference=registration,
        registered_configuration_bytes=(
            configuration_bytes
            if configuration_bytes is not None
            else _configuration_bytes(registration=registration)
        ),
        retry_after_incident=retry_after_incident,
        operations=operations,
    )


def test__coordinator__binds_every_phase_and_publishes_canonical_path(
    tmp_path,
):
    root = _repository(tmp_path)
    calls: list[str] = []
    captured: dict = {}
    result = _run(root, _operations(calls, captured))

    assert result == coordinator.CoordinatorResult(
        status="published",
        path=root / publication.DEFAULT_ARTIFACT_PATH,
        phase="publication",
        reason=None,
    )
    assert calls == [
        "resolve_contract",
        "load_parameters",
        "prepare_sidecar",
        "load_input_plan",
        "compute",
        "invariant",
        "publication",
    ]
    assert captured["execute_kwargs"]["registered_configuration_bytes"] == (
        _configuration_bytes()
    )
    assert captured["artifact_kwargs"]["prior_incidents"] == ()
    assert captured["artifact_kwargs"][
        "configuration_echo"
    ] == runner.registered_configuration_echo(
        registration_reference=REGISTRATION,
        parameter_bundle=PARAMETER_PROVENANCE,
    )


@pytest.mark.parametrize(
    ("phase", "failure_phase"),
    [
        ("preparation", "resolve_contract"),
        ("compute", "compute"),
        ("invariant", "invariant"),
        ("publication", "publication"),
    ],
)
def test__coordinator__publishes_every_abort_without_exception_values(
    tmp_path,
    phase,
    failure_phase,
):
    root = _repository(tmp_path)
    result = _run(
        root,
        _operations([], {}, failure_phase=failure_phase),
    )

    assert result.status == "incident"
    assert result.phase == phase
    record = json.loads(result.path.read_text())
    assert record["phase"] == phase
    assert record["configuration_echo"] == json.loads(_configuration_bytes())
    assert "estimate sentinel" not in record["reason_detail"]
    assert "[1, 2, 3]" not in result.path.read_text()


def test__coordinator__permits_exactly_one_explicit_external_retry(tmp_path):
    root = _repository(tmp_path)
    first = _run(
        root,
        _operations(
            [],
            {},
            failure_phase="compute",
            failure=coordinator.ExternalPreOutputFailure(
                "external_projection_host_unavailable",
                "Projection host unavailable before output.",
            ),
        ),
    )
    assert first.status == "incident"
    assert first.reason == "external_projection_host_unavailable"

    captured: dict = {}
    second = _run(
        root,
        _operations([], captured),
        retry_after_incident=1,
    )
    assert second.status == "published"
    assert captured["artifact_kwargs"]["prior_incidents"] == (
        "runs/first_estimates_incident_1.json",
    )
    assert captured["published_artifact"]["prior_incidents"] == (
        "runs/first_estimates_incident_1.json",
    )


def test__coordinator__second_failure_requires_fresh_registration(tmp_path):
    root = _repository(tmp_path)
    external = coordinator.ExternalPreOutputFailure(
        "external_projection_host_unavailable",
        "Projection host unavailable before output.",
    )
    assert (
        _run(
            root,
            _operations([], {}, failure_phase="compute", failure=external),
        ).status
        == "incident"
    )
    assert (
        _run(
            root,
            _operations([], {}, failure_phase="compute", failure=external),
            retry_after_incident=1,
        ).status
        == "incident"
    )

    calls: list[str] = []
    third = _run(root, _operations(calls, {}), retry_after_incident=2)
    assert third.reason == (
        "preparation_fresh_registration_required_second_failure"
    )
    assert calls == []
    assert third.path.name == "first_estimates_incident_3.json"


def test__coordinator__rejects_noneligible_retry_and_config_drift(tmp_path):
    root = _repository(tmp_path)
    first = _run(
        root,
        _operations([], {}, failure_phase="invariant"),
    )
    assert first.status == "incident"

    blocked = _run(
        root,
        _operations([], {}),
        retry_after_incident=1,
    )
    assert blocked.reason == (
        "preparation_fresh_registration_required_nonretryable_incident"
    )

    drifted = {"bundle_sha256": "d" * 64}
    drift = _run(
        root,
        _operations([], {}, provenance=drifted),
        configuration_bytes=_configuration_bytes(provenance=drifted),
    )
    assert drift.reason == (
        "preparation_fresh_registration_required_configuration_drift"
    )


def test__coordinator__published_v1_and_bad_sidecar_abort(tmp_path):
    published_root = _repository(tmp_path / "published")
    assert (
        _run(
            published_root,
            _operations([], {}),
        ).status
        == "published"
    )
    blocked = _run(published_root, _operations([], {}))
    assert blocked.reason == (
        "preparation_fresh_registration_required_published_v1"
    )

    sidecar_root = _repository(tmp_path / "sidecar")
    empty = publication.canonical_json_bytes({})
    invalid = _run(
        sidecar_root,
        _operations([], {}, sidecar_payload=empty),
    )
    assert invalid.status == "incident"
    assert invalid.phase == "preparation"


def test__coordinator__fresh_registration_cross_references_prior_incident(
    tmp_path,
):
    root = _repository(tmp_path)
    assert (
        _run(
            root,
            _operations([], {}, failure_phase="invariant"),
        ).status
        == "incident"
    )

    captured: dict = {}
    fresh_registration = "issue-42-comment-7654321"
    result = _run(
        root,
        _operations([], captured),
        registration=fresh_registration,
    )
    assert result.status == "published"
    assert captured["artifact_kwargs"]["prior_incidents"] == (
        "runs/first_estimates_incident_1.json",
    )


def test__coordinator__production_surface_has_no_injected_bundle_or_output():
    assert set(
        inspect.signature(
            coordinator.run_registered_first_estimates
        ).parameters
    ) == {
        "repository_root",
        "registration_reference",
        "registered_configuration_bytes",
        "retry_after_incident",
    }
    with pytest.raises(TypeError, match="precompute token"):
        publication.write_first_estimates_artifact({}, {})


def test__coordinator__rejects_invalid_registration_before_ceremony(tmp_path):
    root = _repository(tmp_path)
    calls: list[str] = []
    invalid = publication.canonical_json_bytes(
        {"registration_reference": REGISTRATION}
    )

    with pytest.raises(ValueError, match="projection block"):
        _run(
            root,
            _operations(calls, {}),
            configuration_bytes=invalid,
        )

    assert calls == []
    assert list((root / "runs").iterdir()) == []


def test__registered_input_factory__binds_committed_file_and_exact_type(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    path = root / "scripts" / "registered_m6_candidate3_inputs.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"registered factory\n")
    full_inputs = object()
    plan = M6Candidate3InputPlan(
        fit_inputs=object(),
        load_full_inputs=lambda: full_inputs,
    )
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: b"registered factory\n",
    )
    monkeypatch.setattr(
        coordinator,
        "_load_module",
        lambda *_args: SimpleNamespace(build_input_plan=lambda: plan),
    )

    observed = coordinator._load_registered_input_plan(root)
    assert observed.fit_inputs is plan.fit_inputs
    assert observed.load_full_inputs() is full_inputs
    path.write_bytes(b"drifted factory\n")
    with pytest.raises(RuntimeError, match="committed HEAD blob"):
        coordinator._load_registered_input_plan(root)


def test__default_operations__classify_external_parameter_dependency(
    monkeypatch,
):
    def unavailable():
        raise ParameterDependencyUnavailable("private dependency path")

    monkeypatch.setattr(coordinator, "load_report_parameters", unavailable)

    with pytest.raises(coordinator.ExternalPreOutputFailure) as caught:
        coordinator._default_operations().load_parameters()

    assert caught.value.reason == "external_parameter_bundle_unavailable"
    assert caught.value.safe_detail == (
        "Registered parameter dependency unavailable before output."
    )
    assert "private dependency path" not in caught.value.safe_detail


def test__default_operations__do_not_retry_internal_parameter_failure(
    monkeypatch,
):
    def invalid_internal_file():
        raise FileNotFoundError("tracked COLA path")

    monkeypatch.setattr(
        coordinator,
        "load_report_parameters",
        invalid_internal_file,
    )

    with pytest.raises(FileNotFoundError, match="tracked COLA path"):
        coordinator._default_operations().load_parameters()


def test__registered_input_factory__classifies_lazy_external_dependency(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    path = root / "scripts" / "registered_m6_candidate3_inputs.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"registered factory\n")

    def unavailable():
        raise FileNotFoundError("private input path")

    plan = M6Candidate3InputPlan(
        fit_inputs=object(),
        load_full_inputs=unavailable,
    )
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: b"registered factory\n",
    )
    monkeypatch.setattr(
        coordinator,
        "_load_module",
        lambda *_args: SimpleNamespace(build_input_plan=lambda: plan),
    )

    observed = coordinator._load_registered_input_plan(root)
    with pytest.raises(coordinator.ExternalPreOutputFailure) as caught:
        observed.load_full_inputs()

    assert caught.value.reason == "external_registered_input_unavailable"
    assert caught.value.safe_detail == (
        "Registered input dependency unavailable before output."
    )
    assert "private input path" not in caught.value.safe_detail
