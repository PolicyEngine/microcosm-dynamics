"""Fast tests for the nonpersistent first-estimates coordinator."""

from __future__ import annotations

import copy
import fcntl
import importlib.machinery
import importlib.util
import inspect
import json
import os
import py_compile
import stat
import subprocess
import sys
from dataclasses import asdict, replace
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
RUNTIME_PROVENANCE = {
    "schema_version": "first_estimates.runtime_provenance.v1",
    "parameters": {},
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
    failure: BaseException | None = None,
    provenance: dict | None = None,
    runtime_provenance: dict | None = None,
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
            SimpleNamespace(
                provenance=(
                    provenance
                    if provenance is not None
                    else PARAMETER_PROVENANCE
                ),
                runtime_provenance=(
                    runtime_provenance
                    if runtime_provenance is not None
                    else RUNTIME_PROVENANCE
                ),
            ),
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
        return {
            "fixture": True,
            "configuration_echo": kwargs["configuration_echo"],
            "runtime_provenance": kwargs["runtime_provenance"],
            "prior_incidents": kwargs["prior_incidents"],
        }

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
        assert_interpreter=lambda: None,
        load_parameters=load_parameters,
        load_input_plan=lambda root: maybe_fail(
            "load_input_plan",
            ("input-plan", root),
        ),
        validate_input_sources=lambda _root: None,
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
    assert (
        captured["artifact_kwargs"]["runtime_provenance"] == RUNTIME_PROVENANCE
    )


def test__coordinator__compares_only_stable_registered_parameters(tmp_path):
    relative_file = "policyengine_us/parameters/gov/ssa/nawi.yaml"
    stable_parameters = {
        "schema_version": "first_estimates.parameters.v1",
        "bundle_sha256": "c" * 64,
        "policyengine_us": {
            "version": "1.752.2",
            "parameter_directory": "policyengine_us/parameters",
            "ssa_parameter_directory": ("policyengine_us/parameters/gov/ssa"),
            "ssa_parameter_files": {
                relative_file: {
                    "relative_path": relative_file,
                    "sha256": "a" * 64,
                }
            },
            "actuals_asserted": {
                "nawi_2020": 55_628.60,
                "wage_base_2022": 147_000.0,
            },
        },
        "cola": {
            "relative_path": "data/external/ssa_cola_history.json",
            "sha256": "b" * 64,
        },
    }

    def runtime(checkout: str, revision: str) -> dict:
        site_packages = f"/{checkout}/site-packages"
        return {
            "schema_version": "first_estimates.runtime_provenance.v1",
            "parameters": {
                "policyengine_us": {
                    "root": site_packages,
                    "ssa_parameter_directory": (
                        f"{site_packages}/policyengine_us/parameters/gov/ssa"
                    ),
                    "git_revision": revision,
                    "ssa_parameter_files": {
                        relative_file: {
                            "path": f"{site_packages}/{relative_file}",
                        }
                    },
                },
                "oasdi_rate_legs": {
                    "employee": {
                        "path": (
                            f"{site_packages}/policyengine_us/parameters/gov/"
                            "irs/payroll/social_security/rate/employee.yaml"
                        )
                    },
                    "employer": {
                        "path": (
                            f"{site_packages}/policyengine_us/parameters/gov/"
                            "irs/payroll/social_security/rate/employer.yaml"
                        )
                    },
                },
                "cola": {
                    "path": (
                        f"/{checkout}/data/external/ssa_cola_history.json"
                    )
                },
            },
        }

    before_runtime = runtime("checkout-before", "070cbb7")
    later_runtime = runtime("checkout-later", "a65e9ba")
    registered_configuration = runner.registered_configuration_echo(
        registration_reference=REGISTRATION,
        parameter_bundle=stable_parameters,
    )
    registered_bytes = publication.canonical_json_bytes(
        registered_configuration
    )
    registered_text = registered_bytes.decode()

    assert before_runtime != later_runtime
    assert "git_revision" not in registered_text
    assert "/checkout-" not in registered_text

    calls: list[str] = []
    captured: dict = {}
    result = _run(
        _repository(tmp_path / "later"),
        _operations(
            calls,
            captured,
            provenance=stable_parameters,
            runtime_provenance=later_runtime,
        ),
        configuration_bytes=registered_bytes,
    )

    assert result.status == "published"
    assert captured["published_artifact"]["configuration_echo"] == (
        registered_configuration
    )
    assert captured["published_artifact"]["runtime_provenance"] == (
        later_runtime
    )

    mutated_parameters = copy.deepcopy(stable_parameters)
    mutated_parameters["policyengine_us"]["ssa_parameter_files"][
        relative_file
    ]["sha256"] = ("d" * 64)
    mutation_calls: list[str] = []
    mutation = _run(
        _repository(tmp_path / "mutation"),
        _operations(
            mutation_calls,
            {},
            provenance=mutated_parameters,
            runtime_provenance=later_runtime,
        ),
        configuration_bytes=registered_bytes,
    )

    assert mutation.status == "incident"
    assert mutation.phase == "preparation"
    assert "compute" not in mutation_calls


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

    stale_root = _repository(tmp_path / "stale-sidecar")
    stale_contract = ContractRef(
        blob_sha="d" * 40,
        head_sha="e" * 40,
        path="gates.yaml",
    )
    stale_payload = publication.canonical_json_bytes(
        {
            "environment": ENVIRONMENT,
            "contract": asdict(stale_contract),
        }
    )
    stale = _run(
        stale_root,
        _operations([], {}, sidecar_payload=stale_payload),
    )
    assert stale.status == "incident"
    assert stale.phase == "preparation"


def test__coordinator__rejects_contract_drift_during_resolution(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    state = {"contract": CONTRACT}
    drifted = ContractRef(
        blob_sha="d" * 40,
        head_sha="e" * 40,
        path="gates.yaml",
    )
    monkeypatch.setattr(
        publication.ContractRef,
        "current",
        staticmethod(lambda _root=None: state["contract"]),
    )
    operations = _operations([], {})

    def resolve(root):
        state["contract"] = drifted
        return ("resolved-contract", root)

    result = _run(
        root,
        replace(operations, resolve_contract=resolve),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"


def test__coordinator__revalidates_frozen_identity_before_publication(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    state = {"contract": CONTRACT}
    drifted = ContractRef(
        blob_sha="d" * 40,
        head_sha="e" * 40,
        path="gates.yaml",
    )
    monkeypatch.setattr(
        publication.ContractRef,
        "current",
        staticmethod(lambda _root=None: state["contract"]),
    )
    operations = _operations([], {})
    execute_projection = operations.execute_projection

    def execute(*args, **kwargs):
        batch = execute_projection(*args, **kwargs)
        state["contract"] = drifted
        return batch

    result = _run(
        root,
        replace(operations, execute_projection=execute),
    )

    assert result.status == "incident"
    assert result.phase == "publication"
    assert result.reason == "publication_abort"
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__coordinator__revalidates_input_sources_before_publication(tmp_path):
    root = _repository(tmp_path)
    operations = _operations([], {})
    checks = 0

    def drifted(_root):
        nonlocal checks
        checks += 1
        if checks == 2:
            raise RuntimeError("registered input source drift")

    result = _run(
        root,
        replace(operations, validate_input_sources=drifted),
    )

    assert result.status == "incident"
    assert result.phase == "publication"
    assert result.reason == "publication_abort"
    assert checks == 2
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


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
        "registration_reference",
        "registered_configuration_path",
        "retry_after_incident",
    }
    with pytest.raises(TypeError, match="precompute token"):
        publication.write_first_estimates_artifact({}, {})


def test__coordinator__invalid_registration_publishes_incident(tmp_path):
    root = _repository(tmp_path)
    calls: list[str] = []
    invalid = publication.canonical_json_bytes(
        {"registration_reference": REGISTRATION}
    )

    result = _run(
        root,
        _operations(calls, {}),
        configuration_bytes=invalid,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    record = json.loads(result.path.read_text())
    assert record["configuration_echo"] == json.loads(invalid)
    assert calls == []
    assert list((root / "runs").iterdir()) == [result.path]


def test__coordinator__malformed_json_publishes_bootstrap_incident(tmp_path):
    root = _repository(tmp_path)
    result = _run(
        root,
        _operations([], {}),
        configuration_bytes=b"{not-json",
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    record = json.loads(result.path.read_text())
    assert record["registration_reference"] == REGISTRATION
    assert record["configuration_echo"] == {
        "registration_reference": REGISTRATION
    }


def test__production_path__malformed_bytes_incident_keeps_claim(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(b"{not-json")
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    claim = root / "runs" / "first_estimates_attempt.claim"
    assert claim.is_file()
    assert json.loads(claim.read_text())["registration_reference"] == (
        REGISTRATION
    )


def test__production_path__empty_registration_reference_is_incident_accounted(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)

    result = coordinator.run_registered_first_estimates(
        registration_reference="",
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    record = json.loads(result.path.read_text())
    assert record["registration_reference"] == ""
    assert record["configuration_echo"] == {"registration_reference": ""}
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()


def test__production_path__registration_reference_length_boundary(
    tmp_path,
    monkeypatch,
):
    maximum = "😀" * 85 + "r"
    overlong = maximum + "r"
    assert (
        len(publication.canonical_json_bytes(maximum))
        == publication._REGISTRATION_REFERENCE_MAX_BYTES
        == 1024
    )
    assert len(publication.canonical_json_bytes(overlong)) == 1025
    assert len(maximum) == 86
    assert len(maximum.encode("utf-8")) == 341
    with pytest.raises(ValueError, match="1,024 canonical JSON bytes"):
        coordinator._attempt_claim_payload(overlong)

    overlong_root = _repository(tmp_path / "overlong")
    overlong_configuration = overlong_root / "registration.json"
    overlong_configuration.write_bytes(
        _configuration_bytes(registration=overlong)
    )
    calls: list[str] = []
    operations = _operations(calls, {})
    monkeypatch.setattr(
        coordinator,
        "_sealed_repository_root",
        lambda: overlong_root,
    )
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)

    refused = coordinator.run_registered_first_estimates(
        registration_reference=overlong,
        registered_configuration_path=overlong_configuration,
    )

    assert refused.status == "incident"
    assert refused.phase == "preparation"
    assert refused.reason == "preparation_abort"
    assert calls == []
    assert not (
        overlong_root / "runs" / "first_estimates_attempt.claim"
    ).exists()
    assert not (overlong_root / publication.DEFAULT_ARTIFACT_PATH).exists()

    maximum_root = _repository(tmp_path / "maximum")
    maximum_configuration = maximum_root / "registration.json"
    maximum_configuration.write_bytes(
        _configuration_bytes(registration=maximum)
    )
    monkeypatch.setattr(
        coordinator,
        "_sealed_repository_root",
        lambda: maximum_root,
    )

    published = coordinator.run_registered_first_estimates(
        registration_reference=maximum,
        registered_configuration_path=maximum_configuration,
    )

    claim = maximum_root / "runs" / "first_estimates_attempt.claim"
    claim_bytes = claim.read_bytes()
    assert published.status == "published"
    assert json.loads(claim_bytes)["registration_reference"] == maximum
    assert (
        len(claim_bytes) == 1097 < coordinator._ATTEMPT_CLAIM_MAX_BYTES == 4096
    )


def test__coordinator__changed_registered_byte_publishes_incident(tmp_path):
    root = _repository(tmp_path)
    configuration = json.loads(_configuration_bytes())
    configuration["projection"]["root_seeds"][0] += 1
    changed = publication.canonical_json_bytes(configuration)

    result = _run(
        root,
        _operations([], {}),
        configuration_bytes=changed,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    assert json.loads(result.path.read_text())["configuration_echo"] == (
        configuration
    )
    corrected = _run(root, _operations([], {}))
    assert corrected.reason == (
        "preparation_fresh_registration_required_configuration_drift"
    )


def test__coordinator__noncanonical_same_json_bytes_publish_incident(tmp_path):
    root = _repository(tmp_path)
    noncanonical = _configuration_bytes().removesuffix(b"\n")

    result = _run(
        root,
        _operations([], {}),
        configuration_bytes=noncanonical,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    record = json.loads(result.path.read_text())
    assert record["configuration_echo"] == json.loads(_configuration_bytes())


def test__coordinator__cross_root_configuration_path_is_refused(tmp_path):
    root = _repository(tmp_path)
    outside = tmp_path / "outside" / "registration.json"
    outside.parent.mkdir()
    outside.write_bytes(_configuration_bytes())

    result = coordinator._run_registered_first_estimates_from_path_for_test(
        repository_root=root,
        registration_reference=REGISTRATION,
        registered_configuration_path=outside,
        retry_after_incident=None,
        operations=_operations([], {}),
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == (
        "preparation_cross_root_registered_configuration_refused"
    )
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__production_path__in_root_symlink_to_external_config_is_refused(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    outside = tmp_path / "outside-registration.json"
    outside.write_bytes(_configuration_bytes())
    linked = root / "registration.json"
    linked.symlink_to(outside)
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations([], {}),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=linked,
    )

    assert result.status == "incident"
    assert result.reason == (
        "preparation_cross_root_registered_configuration_refused"
    )
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert not list(outside.parent.glob("first_estimates_incident_*.json"))


def test__sealed_runs__symlink_refuses_lock_claim_and_outside_writes(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    root.mkdir()
    outside_runs = tmp_path / "outside-runs"
    outside_runs.mkdir()
    (root / "runs").symlink_to(outside_runs, target_is_directory=True)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)

    with pytest.raises(coordinator._CeremonyAbort) as caught:
        coordinator.run_registered_first_estimates(
            registration_reference=REGISTRATION,
            registered_configuration_path=configuration_path,
        )

    assert caught.value.reason == "preparation_cross_root_runs_refused"
    assert list(outside_runs.iterdir()) == []


def test__registered_input_factory__binds_committed_file_and_exact_type(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    path = root / "scripts" / "registered_m6_candidate3_inputs.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"registered factory\n")
    monkeypatch.setattr(
        coordinator,
        "_INPUT_FACTORY_SOURCES",
        (coordinator._INPUT_FACTORY_PATH,),
    )
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


def test__registered_input_factory__keeps_scripts_path_through_lazy_import(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    factory_source = (
        b"from populace_dynamics.harness.m6_candidate3_runner import "
        b"M6Candidate3InputPlan\n"
        b"\n"
        b"def build_input_plan():\n"
        b"    import incident3_lazy_helper\n"
        b"    return M6Candidate3InputPlan(\n"
        b"        fit_inputs=incident3_lazy_helper.FIT_INPUTS,\n"
        b"        load_full_inputs=lambda: None,\n"
        b"    )\n"
    )
    helper_source = b'FIT_INPUTS = "incident3-lazy-sentinel"\n'
    factory_path = root / coordinator._INPUT_FACTORY_PATH
    helper_path = scripts / "incident3_lazy_helper.py"
    factory_path.write_bytes(factory_source)
    helper_path.write_bytes(helper_source)
    sources = (
        coordinator._INPUT_FACTORY_PATH,
        Path("scripts/incident3_lazy_helper.py"),
    )
    committed = {
        sources[0].as_posix(): factory_source,
        sources[1].as_posix(): helper_source,
    }
    monkeypatch.setattr(coordinator, "_INPUT_FACTORY_SOURCES", sources)
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda _root, *arguments: committed[
            arguments[-1].removeprefix("HEAD:")
        ],
    )
    monkeypatch.delitem(
        sys.modules,
        "incident3_lazy_helper",
        raising=False,
    )
    original_path = sys.path.copy()

    observed = coordinator._load_registered_input_plan(root)

    assert observed.fit_inputs == "incident3-lazy-sentinel"
    assert "incident3_lazy_helper" not in sys.modules
    assert sys.path == original_path


def test__registered_input_factory__restores_scripts_path_after_failure(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    path = root / coordinator._INPUT_FACTORY_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(b"registered factory\n")
    monkeypatch.setattr(
        coordinator,
        "_INPUT_FACTORY_SOURCES",
        (coordinator._INPUT_FACTORY_PATH,),
    )
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: b"registered factory\n",
    )
    original_path = sys.path.copy()

    def fail_after_mutating_path():
        assert sys.path[0] == str(path.parent)
        sys.path.append("factory-path-mutation")
        raise RuntimeError("factory sentinel")

    monkeypatch.setattr(
        coordinator,
        "_load_module",
        lambda *_args: SimpleNamespace(
            build_input_plan=fail_after_mutating_path
        ),
    )

    with pytest.raises(RuntimeError, match="factory sentinel"):
        coordinator._load_registered_input_plan(root)

    assert sys.path == original_path


def test__registered_input_factory__binds_imported_dependency_chain(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    sources = (
        Path("scripts/registered_m6_candidate3_inputs.py"),
        Path("scripts/registered_m6_candidate2_inputs.py"),
    )
    committed = {
        sources[0]: b"candidate 3\n",
        sources[1]: b"candidate 2\n",
    }
    for relative, payload in committed.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    monkeypatch.setattr(coordinator, "_INPUT_FACTORY_SOURCES", sources)

    def git_bytes(_root, *arguments):
        relative = Path(arguments[-1].removeprefix("HEAD:"))
        return committed[relative]

    monkeypatch.setattr(coordinator, "_git_bytes", git_bytes)
    coordinator._assert_registered_input_sources(root)

    (root / sources[1]).write_bytes(b"drifted candidate 2\n")
    with pytest.raises(RuntimeError, match="candidate2.*committed HEAD"):
        coordinator._assert_registered_input_sources(root)


def test__estimator_surface__binds_every_module_to_committed_head(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    relative = Path("src/populace_dynamics/estimates/coordinator.py")
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"committed coordinator\n")
    monkeypatch.setattr(
        coordinator,
        "_ESTIMATOR_SURFACE_SOURCES",
        (relative,),
    )
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: b"committed coordinator\n",
    )

    coordinator._assert_estimator_surface_sources(root)
    path.write_bytes(b"changed coordinator\n")
    with pytest.raises(RuntimeError, match="estimator.*committed HEAD"):
        coordinator._assert_estimator_surface_sources(root)


def test__git_helpers__scrub_environment_and_route_to_explicit_root(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "sealed"
    root.mkdir()
    script = Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    spec = importlib.util.spec_from_file_location(
        "_test_run_first_estimates_git_helper",
        script,
    )
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    observed: list[tuple[list[str], dict]] = []

    def run(command, **kwargs):
        observed.append((command, kwargs))
        return SimpleNamespace(stdout=b"fixture\n")

    for name, value in {
        "GIT_DIR": str(tmp_path / "redirect.git"),
        "GIT_WORK_TREE": str(tmp_path / "redirect-worktree"),
        "GIT_INDEX_FILE": str(tmp_path / "redirect.index"),
        "GIT_COMMON_DIR": str(tmp_path / "redirect-common"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "status.showUntrackedFiles",
        "GIT_CONFIG_VALUE_0": "no",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ROUND8_NON_GIT_SENTINEL", "preserved")
    monkeypatch.setattr(subprocess, "run", run)

    assert coordinator._git_bytes(root, "status") == b"fixture\n"
    assert launcher._git_bytes(root, "status") == b"fixture\n"

    expected_command = [
        "git",
        "-C",
        str(root),
        f"--git-dir={root / '.git'}",
        "status",
    ]
    assert len(observed) == 2
    for command, kwargs in observed:
        assert command == expected_command
        assert kwargs["check"] is True
        assert kwargs["capture_output"] is True
        assert "cwd" not in kwargs
        assert kwargs["env"]["ROUND8_NON_GIT_SENTINEL"] == "preserved"
        assert not any(name.startswith("GIT_") for name in kwargs["env"])
    assert os.environ["GIT_DIR"] == str(tmp_path / "redirect.git")


def test__repository_guards__refuse_mismatched_git_toplevel_before_status(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "sealed"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    script = Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    spec = importlib.util.spec_from_file_location(
        "_test_run_first_estimates_git_root",
        script,
    )
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)

    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: f"{other}\n".encode(),
    )
    monkeypatch.setattr(
        launcher,
        "_git_bytes",
        lambda *_args: f"{other}\n".encode(),
    )

    with pytest.raises(RuntimeError, match="differs from the Git checkout"):
        coordinator._assert_no_repository_drift(root)
    with pytest.raises(RuntimeError, match="differs from the Git checkout"):
        launcher._assert_pre_import_repository_guard(root)


@pytest.mark.parametrize("staged", [False, True], ids=["worktree", "index"])
def test__production_path__tracked_drift_anywhere_is_preparation_incident(
    tmp_path,
    monkeypatch,
    staged,
):
    root = _repository(tmp_path)
    ignore = root / ".gitignore"
    ignore.write_text("runs/first_estimates_attempt.claim\n")
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    tracked = root / "src" / "populace_dynamics" / "artifacts.py"
    tracked.parent.mkdir(parents=True)
    tracked.write_bytes(b'"""committed writer"""\n')
    coordinator._git_bytes(root, "init", "--quiet")
    coordinator._git_bytes(
        root,
        "add",
        ignore.relative_to(root).as_posix(),
        configuration_path.relative_to(root).as_posix(),
        tracked.relative_to(root).as_posix(),
    )
    coordinator._git_bytes(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "fixture",
    )
    tracked.write_bytes(b'"""drifted writer"""\n')
    if staged:
        coordinator._git_bytes(
            root, "add", tracked.relative_to(root).as_posix()
        )
    expected_status = (
        b"M  src/populace_dynamics/artifacts.py\n"
        if staged
        else b" M src/populace_dynamics/artifacts.py\n"
    )
    assert (
        coordinator._git_bytes(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        == expected_status
    )
    calls: list[str] = []
    operations = replace(
        _operations(calls, {}),
        validate_input_sources=coordinator._assert_registered_sources,
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    assert calls == []
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__production_path__untracked_import_package_is_preparation_incident(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    ignore = root / ".gitignore"
    ignore.write_text("runs/first_estimates_attempt.claim\n")
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    tracked_sibling = root / "scripts" / "registered_m6_candidate2_inputs.py"
    tracked_sibling.parent.mkdir(parents=True)
    tracked_sibling.write_text('"""Tracked input adapter."""\n')
    coordinator._git_bytes(root, "init", "--quiet")
    coordinator._git_bytes(
        root,
        "add",
        ignore.relative_to(root).as_posix(),
        configuration_path.relative_to(root).as_posix(),
        tracked_sibling.relative_to(root).as_posix(),
    )
    coordinator._git_bytes(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "fixture",
    )
    shadow = (
        root / "scripts" / "registered_m6_candidate2_inputs" / "__init__.py"
    )
    shadow.parent.mkdir(parents=True)
    shadow.write_text('"""Untracked import shadow."""\n')
    coordinator._git_bytes(
        root,
        "config",
        "status.showUntrackedFiles",
        "no",
    )
    assert coordinator._git_bytes(root, "status", "--porcelain=v1") == b""
    assert coordinator._git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ) == (b"?? scripts/registered_m6_candidate2_inputs/__init__.py\n")
    calls: list[str] = []
    operations = replace(
        _operations(calls, {}),
        validate_input_sources=coordinator._assert_registered_sources,
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    assert calls == []
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__production_path__ignored_import_cache_is_preparation_incident(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    ignore = root / ".gitignore"
    ignore.write_text(
        "__pycache__/\n*.py[cod]\n*.so\nruns/first_estimates_attempt.claim\n"
    )
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    tracked_sibling = root / "scripts" / "registered_m6_candidate2_inputs.py"
    tracked_sibling.parent.mkdir(parents=True)
    tracked_sibling.write_text('"""Tracked input adapter."""\n')
    coordinator._git_bytes(root, "init", "--quiet")
    coordinator._git_bytes(
        root,
        "add",
        ignore.relative_to(root).as_posix(),
        configuration_path.relative_to(root).as_posix(),
        tracked_sibling.relative_to(root).as_posix(),
    )
    coordinator._git_bytes(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "fixture",
    )
    source = tmp_path / "crafted_input.py"
    source.write_text("raise RuntimeError('crafted cache executed')\n")
    staged_cache = tmp_path / "crafted_input.pyc"
    py_compile.compile(
        str(source),
        cfile=str(staged_cache),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    cache = Path(importlib.util.cache_from_source(str(tracked_sibling)))
    cache.parent.mkdir()
    staged_cache.replace(cache)
    ignored = coordinator._git_bytes(
        root,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "-z",
        "--",
        "src",
        "scripts",
    )
    assert (
        coordinator._git_bytes(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        == b""
    )
    assert ignored == os.fsencode(cache.relative_to(root)) + b"\0"
    calls: list[str] = []
    operations = replace(
        _operations(calls, {}),
        validate_input_sources=coordinator._assert_registered_sources,
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_abort"
    assert calls == []
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__estimator_surface__pins_complete_module_tuple():
    expected = (
        Path("src/populace_dynamics/estimates/__init__.py"),
        Path("src/populace_dynamics/estimates/career.py"),
        Path("src/populace_dynamics/estimates/coordinator.py"),
        Path("src/populace_dynamics/estimates/first_report.py"),
        Path("src/populace_dynamics/estimates/ledgers.py"),
        Path("src/populace_dynamics/estimates/parameters.py"),
        Path("src/populace_dynamics/estimates/preparation.py"),
        Path("src/populace_dynamics/estimates/publication.py"),
        Path("src/populace_dynamics/estimates/runner.py"),
    )
    root = Path(__file__).parents[2]
    observed = tuple(
        sorted(
            path.relative_to(root)
            for path in (
                root / "src" / "populace_dynamics" / "estimates"
            ).glob("*.py")
        )
    )

    assert coordinator._ESTIMATOR_SURFACE_SOURCES == expected
    assert observed == expected


def test__registered_input_factory__pins_complete_production_source_chain():
    expected = (
        Path("scripts/registered_m6_candidate3_inputs.py"),
        Path("scripts/registered_m6_candidate2_inputs.py"),
        Path("scripts/registered_m6_inputs.py"),
        Path("scripts/build_mortality_floors.py"),
    )

    assert coordinator._INPUT_FACTORY_SOURCES == expected
    coordinator._assert_registered_input_sources(Path(__file__).parents[2])


def test__sealed_root__comes_from_imported_estimates_package():
    assert coordinator._sealed_repository_root() == Path(__file__).parents[2]


def test__sealed_root__refuses_nested_source_copy(
    tmp_path,
    monkeypatch,
):
    checkout = tmp_path / "checkout"
    nested_root = checkout / "nested"
    package_file = nested_root / (
        "src/populace_dynamics/estimates/__init__.py"
    )
    package_file.parent.mkdir(parents=True)
    package_file.write_bytes(b'"""nested copy"""\n')
    monkeypatch.setattr(
        coordinator.estimates_package,
        "__file__",
        str(package_file),
    )
    monkeypatch.setattr(
        coordinator,
        "_git_bytes",
        lambda *_args: f"{checkout}\n".encode(),
    )

    with pytest.raises(RuntimeError, match="differs from the Git checkout"):
        coordinator._sealed_repository_root()


def test__ceremony_lock__is_exclusive_and_creates_no_state_file(tmp_path):
    root = _repository(tmp_path)
    before = set((root / "runs").iterdir())

    with coordinator._exclusive_ceremony_lock(root):
        descriptor = os.open(root / "runs", os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(
                    descriptor,
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        finally:
            os.close(descriptor)

    assert set((root / "runs").iterdir()) == before


def test__production_entry__holds_lock_for_complete_coordinator_call(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    events: list[str] = []
    expected = coordinator.CoordinatorResult(
        status="incident",
        path=root / "runs" / "first_estimates_incident_1.json",
        phase="preparation",
        reason="fixture",
    )

    class Lock:
        def __enter__(self):
            events.append("lock")

        def __exit__(self, *_args):
            events.append("unlock")

    monkeypatch.setattr(
        coordinator,
        "_exclusive_ceremony_lock",
        lambda observed_root: events.append(f"root:{observed_root}") or Lock(),
    )

    def run(**_kwargs):
        events.append("run")
        return expected

    monkeypatch.setattr(
        coordinator,
        "_sealed_repository_root",
        lambda: root,
    )
    monkeypatch.setattr(
        coordinator,
        "_run_registered_first_estimates_from_path_for_test",
        run,
    )

    observed = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=root / "registration.json",
    )

    assert observed == expected
    assert events == [
        f"root:{root.resolve()}",
        "lock",
        "run",
        "unlock",
    ]


def test__production_entry__unsealed_interpreter_is_preparation_incident(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    calls: list[str] = []
    operations = replace(
        _operations(calls, {}),
        assert_interpreter=coordinator._assert_sealed_interpreter,
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)
    monkeypatch.delenv(coordinator._PYCACHE_SENTINEL_ENV, raising=False)

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == "preparation_unsealed_interpreter_refused"
    assert calls == []
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__cli__unsealed_launcher_reexecs_with_exact_seal(
    tmp_path,
    monkeypatch,
):
    script = Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    spec = importlib.util.spec_from_file_location(
        "_test_run_first_estimates_reexec",
        script,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sentinel = tmp_path / "fresh-empty-pycache"
    sentinel.mkdir()
    captured: dict = {}

    class Replaced(RuntimeError):
        pass

    def execv(executable, arguments):
        captured["executable"] = executable
        captured["arguments"] = arguments
        raise Replaced

    monkeypatch.delenv(module._PYCACHE_SENTINEL_ENV, raising=False)
    monkeypatch.setattr(
        module.tempfile,
        "mkdtemp",
        lambda **_kwargs: str(sentinel),
    )
    monkeypatch.setattr(module.os, "execv", execv)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            script.name,
            "--registration-reference",
            REGISTRATION,
        ],
    )

    with pytest.raises(Replaced):
        module._seal_interpreter()

    assert captured["executable"] == sys.executable
    assert captured["arguments"] == [
        sys.executable,
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={sentinel}",
        str(script.resolve()),
        "--registration-reference",
        REGISTRATION,
    ]
    assert os.environ[module._PYCACHE_SENTINEL_ENV] == str(sentinel)
    assert not sentinel.exists()


def test__sealed_interpreter__misses_crafted_scripts_cache(tmp_path):
    repository = Path(__file__).parents[2]
    script = repository / "scripts" / "run_first_estimates.py"
    scripts = tmp_path / "repo" / "scripts"
    scripts.mkdir(parents=True)
    source = scripts / "seal_probe.py"
    source.write_text("raise RuntimeError('crafted cache executed')\n")
    cache = Path(importlib.util.cache_from_source(str(source)))
    cache.parent.mkdir()
    py_compile.compile(
        str(source),
        cfile=str(cache),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    source.write_text("VALUE = 'source-loaded'\n")
    control = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            f"import sys; sys.path.insert(0, {str(scripts)!r}); "
            "import seal_probe",
        ],
        capture_output=True,
        text=True,
    )
    assert control.returncode != 0
    assert "crafted cache executed" in control.stderr

    sentinel = tmp_path / "populace-first-estimates-pycache-probe"
    sentinel.mkdir()
    environment = os.environ.copy()
    environment[coordinator._PYCACHE_SENTINEL_ENV] = str(sentinel)
    environment["PYTHONPYCACHEPREFIX"] = str(tmp_path / "hostile-prefix")
    probe = "\n".join(
        (
            "import importlib.util",
            "import json",
            "import sys",
            f"launcher_path = {str(script)!r}",
            "spec = importlib.util.spec_from_file_location("
            "'_sealed_launcher_probe', launcher_path)",
            "launcher = importlib.util.module_from_spec(spec)",
            "spec.loader.exec_module(launcher)",
            "sealed = launcher._sealed_pycache_sentinel()",
            f"sys.path.insert(0, {str(repository / 'src')!r})",
            "from populace_dynamics.estimates import "
            "coordinator as sealed_coordinator",
            "sealed_coordinator._assert_sealed_interpreter()",
            f"sys.path.insert(0, {str(scripts)!r})",
            "import seal_probe",
            "print(json.dumps({",
            "    'cached': seal_probe.__spec__.cached,",
            "    'coordinator_cached': sealed_coordinator.__spec__.cached,",
            "    'coordinator_origin': sealed_coordinator.__spec__.origin,",
            "    'isolated': sys.flags.isolated,",
            "    'no_bytecode': sys.flags.dont_write_bytecode,",
            "    'origin': seal_probe.__spec__.origin,",
            "    'prefix': sys.pycache_prefix,",
            "    'sealed': str(sealed) if sealed else None,",
            "    'value': seal_probe.VALUE,",
            "}, sort_keys=True))",
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={sentinel}",
            "-c",
            probe,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    observed = json.loads(completed.stdout)
    assert observed["isolated"] == 1
    assert observed["no_bytecode"] == 1
    assert observed["prefix"] == str(sentinel)
    assert observed["sealed"] == str(sentinel)
    assert observed["coordinator_origin"] == str(
        repository / "src/populace_dynamics/estimates/coordinator.py"
    )
    assert Path(observed["coordinator_cached"]).is_relative_to(sentinel)
    assert observed["origin"] == str(source)
    assert Path(observed["cached"]).is_relative_to(sentinel)
    assert observed["value"] == "source-loaded"
    assert cache.is_file()
    assert not any(sentinel.iterdir())


def _pre_import_guard_repository(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repo"
    scripts = repository / "scripts"
    estimates = repository / "src" / "populace_dynamics" / "estimates"
    scripts.mkdir(parents=True)
    estimates.mkdir(parents=True)
    launcher = Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    (scripts / launcher.name).write_bytes(launcher.read_bytes())
    (repository / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\n*.so\n"
        "runs/first_estimates_attempt.claim\n"
        "runs/first_estimates_incident_*.json\n"
    )
    import_marker = tmp_path / "populace-imported"
    (estimates.parent / "__init__.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(import_marker)!r}).write_text('imported\\n')\n"
    )
    (estimates / "__init__.py").write_text("")
    (estimates / "coordinator.py").write_text(
        "raise RuntimeError('coordinator imported before repository guard')\n"
    )
    subprocess.run(
        ["git", "init", "-q"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "status.showUntrackedFiles", "no"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=First Estimates Test",
            "-c",
            "user.email=first-estimates@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "pre-import guard fixture",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return repository, import_marker


def _run_pre_import_shadow_probe(
    repository: Path,
    sentinel: Path,
    *,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    sentinel.mkdir()
    environment = os.environ.copy()
    environment[coordinator._PYCACHE_SENTINEL_ENV] = str(sentinel)
    if environment_overrides:
        environment.update(environment_overrides)
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={sentinel}",
            str(repository / "scripts" / "run_first_estimates.py"),
            "--registration-reference",
            REGISTRATION,
            "--registered-configuration",
            str(repository / "registered.json"),
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        env=environment,
    )


def _assert_pre_import_procedural_refusal(
    repository: Path,
    import_marker: Path,
    completed: subprocess.CompletedProcess[str],
    sentinel: Path,
    *,
    reason_detail: str,
) -> None:
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert json.loads(completed.stderr) == {
        "path": None,
        "phase": "preparation",
        "reason": "preparation_pre_import_repository_guard_refused",
        "reason_detail": reason_detail,
        "status": "procedural_refusal",
    }
    assert completed.stderr.count("\n") == 1
    assert not import_marker.exists()
    assert not (repository / "runs").exists()
    assert not any(sentinel.iterdir())


def _assert_pre_import_shadow_refusal(
    repository: Path,
    shadow: Path,
    import_marker: Path,
    completed: subprocess.CompletedProcess[str],
    sentinel: Path,
) -> None:
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    ignored = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "-z",
            "--",
            "src",
            "scripts",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )

    assert status.stdout == b""
    assert ignored.stdout.split(b"\0") == [
        shadow.relative_to(repository).as_posix().encode(),
        b"",
    ]
    _assert_pre_import_procedural_refusal(
        repository,
        import_marker,
        completed,
        sentinel,
        reason_detail=(
            "registered first estimates requires sealed code roots without "
            "ignored executable artifacts"
        ),
    )


def test__sealed_launcher__refuses_abi_shadow_despite_git_dir_redirection(
    tmp_path,
):
    repository, import_marker = _pre_import_guard_repository(tmp_path)
    redirect, _ = _pre_import_guard_repository(tmp_path / "redirect")
    suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    shadow = (
        repository
        / "src"
        / "populace_dynamics"
        / "estimates"
        / f"coordinator{suffix}"
    )
    shadow.write_bytes(b"ignored extension shadow must never be loaded\n")
    sentinel = tmp_path / "extension-shadow-sentinel"
    redirected_environment = {
        "GIT_DIR": str(redirect / ".git"),
        "GIT_WORK_TREE": str(redirect),
        "GIT_INDEX_FILE": str(redirect / ".git" / "index"),
    }
    redirected_status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        env={**os.environ, **redirected_environment},
    )
    assert redirected_status.stdout == b""

    completed = _run_pre_import_shadow_probe(
        repository,
        sentinel,
        environment_overrides=redirected_environment,
    )

    _assert_pre_import_shadow_refusal(
        repository,
        shadow,
        import_marker,
        completed,
        sentinel,
    )


def test__sealed_launcher__refuses_direct_sourceless_stdlib_shadow_pre_import(
    tmp_path,
):
    repository, import_marker = _pre_import_guard_repository(tmp_path)
    shadow_marker = tmp_path / "subprocess-shadow-imported"
    shadow_source = tmp_path / "subprocess.py"
    shadow_source.write_text(
        "from pathlib import Path\n"
        f"Path({str(shadow_marker)!r}).write_text('imported\\n')\n"
        "raise RuntimeError('sourceless subprocess shadow executed')\n"
    )
    shadow = repository / "src" / "subprocess.pyc"
    py_compile.compile(
        str(shadow_source),
        cfile=str(shadow),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    sentinel = tmp_path / "sourceless-shadow-sentinel"

    completed = _run_pre_import_shadow_probe(repository, sentinel)

    _assert_pre_import_shadow_refusal(
        repository,
        shadow,
        import_marker,
        completed,
        sentinel,
    )
    assert not (repository / "src" / "subprocess.py").exists()
    assert not shadow_marker.exists()


def test__sealed_launcher__refuses_assume_unchanged_tracked_edit_pre_import(
    tmp_path,
):
    repository, import_marker = _pre_import_guard_repository(tmp_path)
    relative = Path("src/populace_dynamics/estimates/coordinator.py")
    tracked = repository / relative
    subprocess.run(
        [
            "git",
            "update-index",
            "--assume-unchanged",
            "--",
            relative.as_posix(),
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    tracked.write_text(
        "raise RuntimeError('assume-unchanged coordinator executed')\n"
    )
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    flags = subprocess.run(
        ["git", "ls-files", "-v", "-z", "--", relative.as_posix()],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    assert status.stdout == b""
    assert flags.stdout == b"h " + os.fsencode(relative) + b"\0"
    sentinel = tmp_path / "assume-unchanged-sentinel"

    completed = _run_pre_import_shadow_probe(repository, sentinel)

    _assert_pre_import_procedural_refusal(
        repository,
        import_marker,
        completed,
        sentinel,
        reason_detail=(
            "registered first estimates requires tracked files without "
            "assume-unchanged or skip-worktree flags"
        ),
    )


def test__coordinator_recheck__refuses_dirty_root_despite_git_dir_redirection(
    tmp_path,
    monkeypatch,
):
    repository, _ = _pre_import_guard_repository(tmp_path)
    redirect, _ = _pre_import_guard_repository(tmp_path / "redirect")
    tracked = repository / "src/populace_dynamics/estimates/coordinator.py"
    tracked.write_text("drift hidden by redirected Git state\n")
    monkeypatch.setenv("GIT_DIR", str(redirect / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(redirect))
    redirected_status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    assert redirected_status.stdout == b""

    with pytest.raises(RuntimeError, match="entirely clean"):
        coordinator._assert_no_repository_drift(repository)


@pytest.mark.parametrize(
    ("index_option", "expected_tag"),
    [
        ("--assume-unchanged", b"h "),
        ("--skip-worktree", b"S "),
    ],
    ids=["assume-unchanged", "skip-worktree"],
)
def test__coordinator_recheck__refuses_hidden_tracked_edit(
    tmp_path,
    index_option,
    expected_tag,
):
    repository, _ = _pre_import_guard_repository(tmp_path)
    relative = Path("src/populace_dynamics/estimates/coordinator.py")
    tracked = repository / relative
    subprocess.run(
        ["git", "update-index", index_option, "--", relative.as_posix()],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    tracked.write_text("tracked drift hidden by index flag\n")
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    flags = subprocess.run(
        ["git", "ls-files", "-v", "-z", "--", relative.as_posix()],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    assert status.stdout == b""
    assert flags.stdout == expected_tag + os.fsencode(relative) + b"\0"

    with pytest.raises(
        RuntimeError, match="assume-unchanged or skip-worktree"
    ):
        coordinator._assert_no_repository_drift(repository)


def test__cli__passes_raw_path_and_has_no_root_override(
    tmp_path,
    monkeypatch,
    capsys,
):
    repository, _ = _pre_import_guard_repository(tmp_path)
    live_script = (
        Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    )
    script = repository / "scripts" / "run_first_estimates.py"
    spec = importlib.util.spec_from_file_location(
        "_test_run_first_estimates_cli",
        live_script,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "__file__", str(script))
    raw_path = tmp_path / "not-read-by-cli.json"
    captured: dict = {}
    parse_arguments = module._arguments
    monkeypatch.setattr(
        module,
        "_arguments",
        lambda: SimpleNamespace(
            registration_reference=REGISTRATION,
            registered_configuration=raw_path,
            retry_after_incident=None,
        ),
    )

    def run(**kwargs):
        captured.update(kwargs)
        return coordinator.CoordinatorResult(
            status="published",
            path=tmp_path / "runs" / "first_estimates_v1.json",
            phase="publication",
            reason=None,
        )

    monkeypatch.setattr(module, "_seal_interpreter", lambda: tmp_path)
    monkeypatch.setattr(module, "_run_coordinator", run)
    assert module.main() == 0
    assert captured == {
        "registration_reference": REGISTRATION,
        "registered_configuration_path": raw_path,
        "retry_after_incident": None,
    }
    assert not raw_path.exists()
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            script.name,
            "--registration-reference",
            REGISTRATION,
            "--registered-configuration",
            str(raw_path),
            "--repository-root",
            str(tmp_path),
        ],
    )
    with pytest.raises(SystemExit):
        parse_arguments()
    assert (
        "unrecognized arguments: --repository-root" in capsys.readouterr().err
    )


def test__attempt_claim__is_durable_and_blocks_same_registration(tmp_path):
    root = _repository(tmp_path)
    path = coordinator._create_attempt_claim(root, REGISTRATION)
    original = path.read_bytes()

    assert path == root / "runs" / "first_estimates_attempt.claim"
    assert json.loads(original) == {
        "schema_version": "first_estimates_attempt.v1",
        "registration_reference": REGISTRATION,
    }
    with pytest.raises(
        coordinator._CeremonyAbort,
        match="fresh-registration adjudication",
    ) as same:
        coordinator._create_attempt_claim(root, REGISTRATION)
    assert same.value.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    with pytest.raises(
        coordinator._CeremonyAbort,
        match="fresh-registration adjudication",
    ) as fresh:
        coordinator._create_attempt_claim(
            root,
            "issue-42-comment-7654321",
        )
    assert fresh.value.reason == same.value.reason
    assert path.read_bytes() == original
    oversized = root / "runs" / "oversized.claim"
    oversized.write_bytes(b"x" * (coordinator._ATTEMPT_CLAIM_MAX_BYTES + 1))
    assert coordinator._read_attempt_claim(oversized) is None


@pytest.mark.parametrize(
    "failure",
    [
        OSError("claim storage unavailable"),
        KeyboardInterrupt(),
    ],
    ids=["io-error", "keyboard-interrupt"],
)
def test__production_path__partial_claim_failure_is_incident_accounted(
    tmp_path,
    monkeypatch,
    failure,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    payload = coordinator._attempt_claim_payload(REGISTRATION)

    def write_partial(descriptor, observed_payload):
        assert observed_payload == payload
        assert os.write(descriptor, observed_payload[:7]) == 7
        raise failure

    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_write_attempt_claim_payload",
        write_partial,
    )
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations([], {}),
    )

    first = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )
    claim = root / "runs" / "first_estimates_attempt.claim"
    partial = claim.read_bytes()
    second = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert first.status == "incident"
    assert first.phase == "preparation"
    assert first.reason == "preparation_abort"
    assert (
        type(failure).__name__
        in json.loads(first.path.read_text())["reason_detail"]
    )
    assert partial == payload[:7]
    assert claim.read_bytes() == partial
    assert second.status == "incident"
    assert second.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert second.path.name == "first_estimates_incident_2.json"


@pytest.mark.parametrize(
    "claim_payload",
    [
        (
            b'{"registration_reference":NaN,'
            b'"schema_version":"first_estimates_attempt.v1"}\n'
        ),
        (
            b'{"registration_reference":1e1000000,'
            b'"schema_version":"first_estimates_attempt.v1"}\n'
        ),
    ],
    ids=["nan", "overflow"],
)
def test__production_path__nonfinite_claim_requires_fresh_adjudication(
    tmp_path,
    monkeypatch,
    claim_payload,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    claim = root / "runs" / "first_estimates_attempt.claim"
    claim.write_bytes(claim_payload)
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations([], {}),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert claim.read_bytes() == claim_payload


def test__production_path__symlinked_matching_claim_requires_fresh_adjudication(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    outside = tmp_path / "outside.claim"
    outside.write_bytes(coordinator._attempt_claim_payload(REGISTRATION))
    claim = root / "runs" / "first_estimates_attempt.claim"
    claim.symlink_to(outside)
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations([], {}),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )

    assert result.status == "incident"
    assert result.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert claim.is_symlink()
    assert outside.read_bytes() == coordinator._attempt_claim_payload(
        REGISTRATION
    )


@pytest.mark.skipif(
    not all(
        hasattr(os, name) for name in ("mkfifo", "O_NOFOLLOW", "O_NONBLOCK")
    ),
    reason="platform has no nonblocking no-follow FIFO support",
)
def test__production_path__fifo_claim_requires_fresh_adjudication(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    claim = root / "runs" / "first_estimates_attempt.claim"
    os.mkfifo(claim)
    real_open = os.open
    claim_open_flags: list[int] = []

    def guarded_open(path, flags, *args, **kwargs):
        if Path(path) == claim:
            claim_open_flags.append(flags)
            if not flags & os.O_WRONLY:
                required = os.O_NOFOLLOW | os.O_NONBLOCK
                if flags & required != required:
                    raise OSError("claim reader omitted safe FIFO flags")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(coordinator.os, "open", guarded_open)
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    calls: list[str] = []
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations(calls, {}),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )

    reader_flags = [
        flags for flags in claim_open_flags if not flags & os.O_WRONLY
    ]
    assert result.status == "incident"
    assert result.phase == "preparation"
    assert result.reason == (
        "preparation_fresh_registration_adjudication_required_attempt_claim"
    )
    assert result.path.name == "first_estimates_incident_1.json"
    assert calls == []
    assert len(reader_flags) == 1
    assert reader_flags[0] & os.O_NOFOLLOW
    assert reader_flags[0] & os.O_NONBLOCK
    assert stat.S_ISFIFO(os.lstat(claim).st_mode)


def test__production_path__successful_publication_keeps_claim(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations([], {}),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "published"
    assert (root / "runs" / "first_estimates_attempt.claim").is_file()
    assert result.path.is_file()


def test__production_path__external_incident_retry_succeeds_with_same_claim(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    external = coordinator.ExternalPreOutputFailure(
        "external_projection_host_unavailable",
        "Projection host unavailable before output.",
    )
    captured: dict = {}
    attempts = iter(
        (
            _operations(
                [],
                {},
                failure_phase="compute",
                failure=external,
            ),
            _operations([], captured),
        )
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator, "_default_operations", lambda: next(attempts)
    )

    first = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )
    claim = root / "runs" / "first_estimates_attempt.claim"
    claim_bytes = claim.read_bytes()
    retry_claim = root / "runs" / "first_estimates_retry.claim"
    assert not retry_claim.exists()
    second = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )

    assert first.status == "incident"
    assert first.reason == "external_projection_host_unavailable"
    assert second.status == "published"
    assert claim.read_bytes() == claim_bytes
    assert retry_claim.read_bytes() == coordinator._retry_claim_payload(
        REGISTRATION,
        1,
    )
    assert captured["artifact_kwargs"]["prior_incidents"] == (
        "runs/first_estimates_incident_1.json",
    )


def test__production_path__hard_crash_after_retry_claim_refuses_later_retry(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    external = coordinator.ExternalPreOutputFailure(
        "external_projection_host_unavailable",
        "Projection host unavailable before output.",
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations(
            [],
            {},
            failure_phase="compute",
            failure=external,
        ),
    )
    first = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    retry_claim = coordinator._create_retry_claim(root, REGISTRATION, 1)
    retry_claim_bytes = retry_claim.read_bytes()
    assert first.status == "incident"
    assert first.reason == "external_projection_host_unavailable"
    assert sorted((root / "runs").glob("first_estimates_incident_*.json")) == [
        first.path
    ]
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()
    sidecar = Path(f"{root / publication.DEFAULT_ARTIFACT_PATH}.env.json")
    assert not sidecar.exists()

    calls: list[str] = []
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations(calls, {}),
    )
    blocked = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )

    assert blocked.status == "incident"
    assert blocked.phase == "preparation"
    assert blocked.reason == (
        "preparation_fresh_registration_required_retry_claim"
    )
    assert calls == []
    assert retry_claim.read_bytes() == retry_claim_bytes
    assert sorted((root / "runs").glob("first_estimates_incident_*.json")) == [
        first.path,
        blocked.path,
    ]
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()


def test__production_path__second_external_failure_requires_fresh_registration(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    external = coordinator.ExternalPreOutputFailure(
        "external_projection_host_unavailable",
        "Projection host unavailable before output.",
    )
    calls: list[str] = []
    operations = _operations(
        calls,
        {},
        failure_phase="compute",
        failure=external,
    )
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(coordinator, "_default_operations", lambda: operations)

    first = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )
    claim = root / "runs" / "first_estimates_attempt.claim"
    claim_bytes = claim.read_bytes()
    second = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )
    third = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=2,
    )

    assert first.reason == "external_projection_host_unavailable"
    assert second.reason == "external_projection_host_unavailable"
    assert third.reason == (
        "preparation_fresh_registration_required_second_failure"
    )
    assert third.path.name == "first_estimates_incident_3.json"
    assert calls.count("compute") == 2
    assert claim.read_bytes() == claim_bytes


def test__production_path__keyboard_interrupt_incident_keeps_claim(
    tmp_path,
    monkeypatch,
):
    root = _repository(tmp_path)
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
    monkeypatch.setattr(coordinator, "_sealed_repository_root", lambda: root)
    monkeypatch.setattr(
        coordinator,
        "_default_operations",
        lambda: _operations(
            [],
            {},
            failure_phase="compute",
            failure=KeyboardInterrupt(),
        ),
    )

    result = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
    )

    assert result.status == "incident"
    assert result.phase == "compute"
    assert result.reason == "compute_abort"
    record = json.loads(result.path.read_text())
    assert "KeyboardInterrupt" in record["reason_detail"]
    claim = root / "runs" / "first_estimates_attempt.claim"
    assert claim.is_file()
    assert not (root / publication.DEFAULT_ARTIFACT_PATH).exists()

    blocked = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )
    assert blocked.reason == (
        "preparation_fresh_registration_required_nonretryable_incident"
    )
    assert sorted((root / "runs").glob("first_estimates_incident_*.json")) == [
        result.path,
        blocked.path,
    ]
    assert claim.is_file()


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
    monkeypatch.setattr(
        coordinator,
        "_INPUT_FACTORY_SOURCES",
        (coordinator._INPUT_FACTORY_PATH,),
    )

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
