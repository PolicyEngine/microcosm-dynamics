"""Fast tests for the nonpersistent first-estimates coordinator."""

from __future__ import annotations

import fcntl
import importlib.util
import inspect
import json
import os
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


@pytest.mark.parametrize("staged", [False, True], ids=["worktree", "index"])
def test__production_path__tracked_drift_anywhere_is_preparation_incident(
    tmp_path,
    monkeypatch,
    staged,
):
    root = _repository(tmp_path)
    tracked = root / "src" / "populace_dynamics" / "artifacts.py"
    tracked.parent.mkdir(parents=True)
    tracked.write_bytes(b'"""committed writer"""\n')
    coordinator._git_bytes(root, "init", "--quiet")
    coordinator._git_bytes(root, "add", tracked.relative_to(root).as_posix())
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
    configuration_path = root / "registration.json"
    configuration_path.write_bytes(_configuration_bytes())
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
        lambda observed_root: (
            events.append(f"root:{observed_root}") or Lock()
        ),
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


def test__cli__passes_raw_path_and_has_no_root_override(
    tmp_path,
    monkeypatch,
    capsys,
):
    script = Path(__file__).parents[2] / "scripts" / "run_first_estimates.py"
    spec = importlib.util.spec_from_file_location(
        "_test_run_first_estimates_cli",
        script,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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

    monkeypatch.setattr(module, "run_registered_first_estimates", run)
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
    second = coordinator.run_registered_first_estimates(
        registration_reference=REGISTRATION,
        registered_configuration_path=configuration_path,
        retry_after_incident=1,
    )

    assert first.status == "incident"
    assert first.reason == "external_projection_host_unavailable"
    assert second.status == "published"
    assert claim.read_bytes() == claim_bytes
    assert captured["artifact_kwargs"]["prior_incidents"] == (
        "runs/first_estimates_incident_1.json",
    )


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
