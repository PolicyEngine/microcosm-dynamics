"""Nonpersistent coordinator for the registered first-estimates ceremony.

The public entry point has no parameter-bundle, input-factory, sidecar, or
output-path injection.  It binds those production objects itself, freezes the
registered bytes before compute, and writes only the artifact pair or an
append-only incident record prescribed by the design.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from populace_dynamics.estimates import publication
from populace_dynamics.estimates.parameters import load_report_parameters
from populace_dynamics.estimates.preparation import (
    _build_prepared_first_estimates_artifact,
    _prepare_first_report_batch,
)
from populace_dynamics.estimates.runner import (
    execute_first_report_projection,
    registered_configuration_echo,
    resolve_report_contract,
    validate_registered_configuration_echo,
)
from populace_dynamics.harness.m6_candidate3_runner import (
    M6Candidate3InputPlan,
)

__all__ = [
    "CoordinatorResult",
    "ExternalPreOutputFailure",
    "run_registered_first_estimates",
]

_INPUT_FACTORY_PATH = Path("scripts/registered_m6_candidate3_inputs.py")
_INPUT_FACTORY_CALLABLE = "build_input_plan"
_SAFE_EXTERNAL_REASON = re.compile(r"external_[a-z0-9_]+")
_SAFE_EXTERNAL_DETAIL = re.compile(r"[A-Za-z0-9 .,:;()_/\-]+")


@dataclass(frozen=True)
class CoordinatorResult:
    """Terminal publication or incident produced by one invocation."""

    status: Literal["published", "incident"]
    path: Path
    phase: str
    reason: str | None


class ExternalPreOutputFailure(RuntimeError):
    """Explicit coordinator-adjudicated retry-eligible external failure."""

    def __init__(self, reason: str, safe_detail: str):
        if _SAFE_EXTERNAL_REASON.fullmatch(reason) is None:
            raise ValueError(
                "external failure reason must match external_[a-z0-9_]+"
            )
        if (
            not safe_detail
            or len(safe_detail) > 240
            or _SAFE_EXTERNAL_DETAIL.fullmatch(safe_detail) is None
        ):
            raise ValueError("external failure detail is not incident-safe")
        super().__init__(safe_detail)
        self.reason = reason
        self.safe_detail = safe_detail


class _CeremonyAbort(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class _IncidentHistory:
    paths: tuple[str, ...]
    records: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class _CoordinatorOperations:
    """Test-private seams; the public production entry point never accepts it."""

    load_parameters: Callable[[], Any]
    load_input_plan: Callable[[Path], M6Candidate3InputPlan]
    resolve_contract: Callable[[Path], Any]
    prepare_sidecar: Callable[[Path], tuple[bytes, str]]
    execute_projection: Callable[..., Any]
    prepare_batch: Callable[..., Any]
    build_artifact: Callable[..., Mapping[str, Any]]
    publish_artifact: Callable[..., Path]
    publish_incident: Callable[..., Path]


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        command = " ".join(("git", *arguments))
        raise RuntimeError(
            f"unable to bind registered input factory with `{command}`"
        ) from error


def _load_module(path: Path, scripts: Path) -> ModuleType:
    module_name = "_first_estimates_registered_input_factory"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("registered input factory cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(scripts))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(scripts))
        sys.modules.pop(module_name, None)
    return module


def _load_registered_input_plan(repository: Path) -> M6Candidate3InputPlan:
    """Load only the tracked, byte-clean registered candidate-3 factory."""
    relative = _INPUT_FACTORY_PATH.as_posix()
    path = repository / _INPUT_FACTORY_PATH
    committed = _git_bytes(repository, "show", f"HEAD:{relative}")
    try:
        working = path.read_bytes()
    except FileNotFoundError as error:
        raise RuntimeError("registered input factory is absent") from error
    if working != committed:
        raise RuntimeError(
            "registered input factory differs from its committed HEAD blob"
        )
    module = _load_module(path, path.parent)
    factory = getattr(module, _INPUT_FACTORY_CALLABLE, None)
    if not callable(factory):
        raise RuntimeError("registered input factory callable is absent")
    plan = factory()
    if not isinstance(plan, M6Candidate3InputPlan):
        raise TypeError(
            "registered input factory did not return M6Candidate3InputPlan"
        )
    return plan


def _default_operations() -> _CoordinatorOperations:
    return _CoordinatorOperations(
        load_parameters=lambda: load_report_parameters(),
        load_input_plan=_load_registered_input_plan,
        resolve_contract=resolve_report_contract,
        prepare_sidecar=publication.prepare_environment_sidecar,
        execute_projection=execute_first_report_projection,
        prepare_batch=_prepare_first_report_batch,
        build_artifact=_build_prepared_first_estimates_artifact,
        publish_artifact=publication.write_first_estimates_artifact,
        publish_incident=publication.write_first_estimates_incident,
    )


def _read_incident_history(
    token: publication._RegisteredConfigurationToken,
) -> _IncidentHistory:
    root = token._repository_root
    runs = root / "runs"
    if not runs.is_dir():
        raise _CeremonyAbort(
            "preparation_runs_directory_absent",
            "The registered repository has no runs directory.",
        )
    indexed: list[tuple[int, Path]] = []
    for path in runs.glob("first_estimates_incident_*.json"):
        match = publication._INCIDENT_FILENAME.fullmatch(path.name)
        if match is not None:
            indexed.append((int(match.group(1)), path))
    indexed.sort()
    if [index for index, _path in indexed] != list(range(1, len(indexed) + 1)):
        raise _CeremonyAbort(
            "preparation_incident_history_noncontiguous",
            "Existing first-estimates incident indices are not contiguous.",
        )

    records: list[Mapping[str, Any]] = []
    paths: list[str] = []
    for index, path in indexed:
        try:
            record = json.loads(path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} is not readable canonical JSON.",
            ) from error
        if not isinstance(record, Mapping):
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} is not a JSON object.",
            )
        record_configuration = record.get("configuration_echo")
        if not isinstance(record_configuration, Mapping):
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} has no configuration object.",
            )
        try:
            publication.validate_first_estimates_incident(
                record,
                path=path,
                expected_configuration_echo=record_configuration,
                repository_root=root,
                validate_artifact_existence=False,
            )
        except (TypeError, ValueError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} fails the frozen schema.",
            ) from error
        records.append(record)
        paths.append(path.relative_to(root).as_posix())
    return _IncidentHistory(paths=tuple(paths), records=tuple(records))


def _authorize_invocation(
    token: publication._RegisteredConfigurationToken,
    history: _IncidentHistory,
    *,
    retry_after_incident: int | None,
) -> None:
    root = token._repository_root
    artifact = root / publication.DEFAULT_ARTIFACT_PATH
    sidecar = Path(f"{artifact}.env.json")
    if artifact.exists() or sidecar.exists():
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_published_v1",
            "The canonical artifact path or its sidecar already exists.",
        )

    current: list[Mapping[str, Any]] = []
    for record in history.records:
        if (
            record.get("registration_reference")
            != token._registration_reference
        ):
            continue
        current.append(record)
        record_bytes = publication.canonical_json_bytes(
            record["configuration_echo"]
        )
        if record_bytes != token._configuration_bytes:
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_configuration_drift",
                "This registration reference already has different bytes.",
            )

    if not current:
        if retry_after_incident is not None:
            raise _CeremonyAbort(
                "preparation_retry_without_prior_incident",
                "No prior incident exists for the requested retry.",
            )
        return
    if len(current) != 1:
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_second_failure",
            "This registration already has more than one incident.",
        )
    prior = current[0]
    if not publication.incident_is_retry_eligible(prior):
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_nonretryable_incident",
            "The prior incident is not external and pre-output.",
        )
    if retry_after_incident != prior["incident_index"]:
        raise _CeremonyAbort(
            "preparation_retry_requires_exact_incident",
            "The sole eligible incident must be selected explicitly.",
        )


def _safe_incident_fields(
    phase: str,
    error: Exception,
) -> tuple[str, str]:
    if isinstance(error, ExternalPreOutputFailure) and phase in {
        "preparation",
        "compute",
    }:
        return error.reason, error.safe_detail
    if isinstance(error, _CeremonyAbort):
        return error.reason, error.detail
    return (
        f"{phase}_abort",
        (
            f"{type(error).__name__} raised during {phase}; "
            "exception detail withheld by incident policy."
        ),
    )


def _publish_abort(
    token: (
        publication._RegisteredConfigurationToken
        | publication._PrecomputeToken
    ),
    *,
    phase: str,
    error: Exception,
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    reason, detail = _safe_incident_fields(phase, error)
    path = operations.publish_incident(
        token,
        phase=phase,
        reason=reason,
        reason_detail=detail,
    )
    return CoordinatorResult(
        status="incident",
        path=path,
        phase=phase,
        reason=reason,
    )


def _run_registered_first_estimates_for_test(
    *,
    repository_root: str | Path,
    registration_reference: str,
    registered_configuration_bytes: bytes,
    retry_after_incident: int | None,
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    """Test-private implementation behind the sealed production entry point."""
    registration = publication._parse_registered_configuration(
        repository_root=repository_root,
        registration_reference=registration_reference,
        registered_configuration_bytes=registered_configuration_bytes,
    )
    # This is the boundary of the ceremony.  Before the full frozen structure
    # is proved, caller bytes cannot safely populate an incident's
    # numeric-array-exempt configuration_echo.
    validate_registered_configuration_echo(
        publication._configuration_echo(registration),
        registered_configuration_bytes=registered_configuration_bytes,
    )

    precompute: publication._PrecomputeToken | None = None
    try:
        history = _read_incident_history(registration)
        _authorize_invocation(
            registration,
            history,
            retry_after_incident=retry_after_incident,
        )
        resolved = operations.resolve_contract(registration._repository_root)
        parameters = operations.load_parameters()
        expected_configuration = registered_configuration_echo(
            registration_reference=registration_reference,
            parameter_bundle=parameters.provenance,
        )
        validate_registered_configuration_echo(
            expected_configuration,
            registered_configuration_bytes=registered_configuration_bytes,
        )
        sidecar_payload, sidecar_sha256 = operations.prepare_sidecar(
            registration._repository_root
        )
        precompute = publication._freeze_precompute(
            registration,
            expected_configuration_echo=expected_configuration,
            sidecar_payload=sidecar_payload,
            prior_incidents=history.paths,
        )
        if sidecar_sha256 != precompute._sidecar_sha256:
            raise ValueError(
                "prepared sidecar digest differs from its frozen bytes"
            )
        input_plan = operations.load_input_plan(registration._repository_root)
    except Exception as error:
        return _publish_abort(
            precompute or registration,
            phase="preparation",
            error=error,
            operations=operations,
        )

    try:
        batch = operations.execute_projection(
            input_plan,
            resolved=resolved,
            configuration_echo=expected_configuration,
            registered_configuration_bytes=registered_configuration_bytes,
        )
    except Exception as error:
        return _publish_abort(
            precompute,
            phase="compute",
            error=error,
            operations=operations,
        )

    try:
        prepared = operations.prepare_batch(
            batch,
            parameters=parameters,
        )
        artifact = operations.build_artifact(
            prepared,
            configuration_echo=expected_configuration,
            environment_sidecar_sha256=precompute._sidecar_sha256,
            prior_incidents=precompute._prior_incidents,
        )
    except Exception as error:
        return _publish_abort(
            precompute,
            phase="invariant",
            error=error,
            operations=operations,
        )

    try:
        path = operations.publish_artifact(precompute, artifact)
    except Exception as error:
        return _publish_abort(
            precompute,
            phase="publication",
            error=error,
            operations=operations,
        )
    return CoordinatorResult(
        status="published",
        path=path,
        phase="publication",
        reason=None,
    )


def run_registered_first_estimates(
    *,
    repository_root: str | Path,
    registration_reference: str,
    registered_configuration_bytes: bytes,
    retry_after_incident: int | None = None,
) -> CoordinatorResult:
    """Run the one-shot production ceremony with no persistent coordinator."""
    return _run_registered_first_estimates_for_test(
        repository_root=repository_root,
        registration_reference=registration_reference,
        registered_configuration_bytes=registered_configuration_bytes,
        retry_after_incident=retry_after_incident,
        operations=_default_operations(),
    )
