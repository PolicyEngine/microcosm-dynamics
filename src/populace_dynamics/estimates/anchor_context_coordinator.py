"""Sealed coordinator for the registered anchor-context ceremony."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import populace_dynamics.estimates as estimates_package
from populace_dynamics.estimates import (
    anchor_context_publication,
    anchor_context_report,
)
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import coordinator as first_coordinator
from populace_dynamics.estimates import publication as first_publication

CoordinatorResult = first_coordinator.CoordinatorResult
ExternalPreOutputFailure = first_coordinator.ExternalPreOutputFailure

CANONICAL_EXECUTION_RULE = {
    "registered_runs": 1,
    "publishes_regardless": True,
    "no_self_rescue": True,
    "retry": (
        "At most one coordinator-adjudicated, report-first retry solely for "
        "an external preparation or compute incident that yielded no "
        "estimate-bearing information."
    ),
    "fresh_registration_required_if": (
        "A published v1, any changed configuration byte, or a second failure "
        "of any kind."
    ),
}
PRELAUNCH_CHECK_NAMES = (
    "ratified_design_and_implementation",
    "fresh_registration_and_canonical_configuration",
    "registered_input_identities_without_open",
    "outputs_absent_and_incident_index_contiguous",
    "isolated_invocation_byte_match",
    "publishes_regardless_and_retry_law_acknowledged",
)

_SCRIPT_PATH = "scripts/run_anchor_context_report.py"
_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_SAFE_REASON = first_coordinator._SAFE_EXTERNAL_REASON


class _CeremonyAbort(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class _IncidentHistory:
    records: tuple[Mapping[str, Any], ...]


def _continue_after_preparation() -> None:
    """Production no-op at the test-private preparation boundary."""


@dataclass(frozen=True)
class _CoordinatorOperations:
    """Injectable seams; the public production function accepts none."""

    assert_interpreter: Callable[[Mapping[str, Any], Sequence[str]], None]
    validate_repository: Callable[[Path, Mapping[str, Any]], None]
    prepare_sidecar: Callable[[Path], tuple[bytes, str]]
    load_inputs: Callable[
        [Path, Mapping[str, Any]],
        tuple[Mapping[str, Any], Mapping[str, Any]],
    ]
    build_results: Callable[..., Mapping[str, Any]]
    validate_results: Callable[..., None]
    build_runtime_provenance: Callable[[str], Mapping[str, Any]]
    build_artifact: Callable[..., Mapping[str, Any]]
    publish_artifact: Callable[..., Path]
    publish_incident: Callable[..., Path]
    after_preparation: Callable[[], None] = _continue_after_preparation


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    """Run Git without inheriting caller-supplied GIT_* overrides."""
    root = repository.resolve()
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }
    try:
        return subprocess.run(
            [
                "git",
                "-C",
                str(root),
                f"--git-dir={root / '.git'}",
                *arguments,
            ],
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise _CeremonyAbort(
            "preparation_git_guard_failed",
            "Git could not verify the registered report checkout.",
        ) from error


def _assert_sealed_interpreter(
    configuration: Mapping[str, Any],
    actual_invocation: Sequence[str],
) -> None:
    """Require the exact already-registered isolated invocation."""
    if not isinstance(actual_invocation, (list, tuple)):
        raise _CeremonyAbort(
            "preparation_invocation_unavailable",
            "The interpreter did not expose its exact invocation array.",
        )
    actual = list(actual_invocation)
    registered = configuration["invocation"]
    if actual != registered:
        raise _CeremonyAbort(
            "preparation_invocation_drift",
            "The isolated invocation differs from registered bytes.",
        )
    if (
        len(actual) != 8
        or actual[1:4] != ["-I", "-B", "-X"]
        or not actual[4].startswith("pycache_prefix=")
        or actual[5] != _SCRIPT_PATH
        or actual[6] != "--registration"
    ):
        raise _CeremonyAbort(
            "preparation_invocation_shape_refused",
            "The invocation is not the canonical isolated command.",
        )
    sentinel_literal = actual[4].removeprefix("pycache_prefix=")
    if (
        not sys.flags.isolated
        or not sys.flags.dont_write_bytecode
        or sys.pycache_prefix != sentinel_literal
    ):
        raise _CeremonyAbort(
            "preparation_unsealed_interpreter_refused",
            "The coordinator requires python -I -B -X pycache_prefix=...",
        )
    sentinel = Path(sentinel_literal)
    try:
        valid = bool(
            sentinel.is_absolute()
            and not sentinel.is_symlink()
            and sentinel.is_dir()
            and not any(sentinel.iterdir())
        )
    except OSError:
        valid = False
    if not valid:
        raise _CeremonyAbort(
            "preparation_pycache_sentinel_refused",
            "The registered pycache sentinel is not a fresh empty directory.",
        )


def _validate_repository(
    repository_root: Path,
    configuration: Mapping[str, Any],
) -> None:
    """Bind the clean ordinary checkout to the implementation commit."""
    root = repository_root.resolve()
    reported = Path(
        os.fsdecode(_git_bytes(root, "rev-parse", "--show-toplevel")).strip()
    ).resolve()
    if reported != root:
        raise _CeremonyAbort(
            "preparation_repository_root_drift",
            "Git reports a different repository root.",
        )
    hidden = tuple(
        entry
        for entry in _git_bytes(root, "ls-files", "-v", "-z", "--").split(
            b"\0"
        )
        if entry and (entry[:1].islower() or entry.startswith(b"S "))
    )
    if hidden:
        raise _CeremonyAbort(
            "preparation_nonordinary_index_refused",
            "Tracked files use assume-unchanged or skip-worktree flags.",
        )
    status = _git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status:
        raise _CeremonyAbort(
            "preparation_repository_drift",
            "The registered report requires an entirely clean checkout.",
        )
    head = os.fsdecode(_git_bytes(root, "rev-parse", "HEAD")).strip()
    if head != configuration["implementation_commit"]:
        raise _CeremonyAbort(
            "preparation_implementation_commit_drift",
            "Checkout HEAD differs from the registered implementation commit.",
        )
    ignored = _git_bytes(
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
    ignored_executables = tuple(
        path
        for path in ignored.split(b"\0")
        if path
        and (
            b"__pycache__" in path.split(b"/")
            or path.endswith(_IGNORED_EXECUTABLE_SUFFIXES)
        )
    )
    if ignored_executables:
        raise _CeremonyAbort(
            "preparation_ignored_executable_refused",
            "The code roots contain ignored executable artifacts.",
        )


def _load_inputs(
    repository_root: Path,
    configuration: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    first = anchor_context_publication._load_verified_json(
        repository_root,
        configuration["first_estimates_input"],
        role="first_estimates",
    )
    anchors = anchor_context_publication._load_verified_json(
        repository_root,
        configuration["anchor_input"],
        role="anchor",
    )
    return first, anchors


def _publish_artifact(
    token: anchor_context_publication._AnchorContextPrecomputeToken,
    artifact: Mapping[str, Any],
    *,
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
) -> Path:
    return anchor_context_publication.write_anchor_context_artifact(
        token,
        artifact,
        first_estimates=first_estimates,
        anchors=anchors,
    )


def _default_operations() -> _CoordinatorOperations:
    return _CoordinatorOperations(
        assert_interpreter=_assert_sealed_interpreter,
        validate_repository=_validate_repository,
        prepare_sidecar=(
            anchor_context_publication.prepare_environment_sidecar
        ),
        load_inputs=_load_inputs,
        build_results=anchor_context_report.build_results,
        validate_results=anchor_context_report.validate_results,
        build_runtime_provenance=(
            anchor_context_publication.build_runtime_provenance
        ),
        build_artifact=(
            anchor_context_publication.build_anchor_context_artifact
        ),
        publish_artifact=_publish_artifact,
        publish_incident=(
            anchor_context_publication.write_anchor_context_incident
        ),
    )


def _parse_configuration(
    *,
    repository_root: Path,
    registered_configuration_bytes: bytes,
    production_only: bool,
) -> first_publication._RegisteredConfigurationToken:
    try:
        decoded = json.loads(registered_configuration_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "registered configuration is not valid JSON"
        ) from error
    configuration = decoded if isinstance(decoded, Mapping) else {}
    reference = configuration.get("registration_reference")
    if not isinstance(reference, str) or not reference:
        raise ValueError("registered configuration has no reference")
    token = first_publication._parse_registered_configuration(
        repository_root=repository_root,
        registration_reference=reference,
        registered_configuration_bytes=registered_configuration_bytes,
    )
    if production_only:
        anchor_context_publication.validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=registered_configuration_bytes,
        )
    else:
        anchor_context_publication._validate_configuration_echo_for_execution(
            configuration
        )
    return token


def _read_incident_history(
    repository_root: Path,
) -> _IncidentHistory:
    """Read and exact-validate the complete contiguous incident history."""
    runs = repository_root / "runs"
    anchor_context_publication._next_incident_path(repository_root)
    indexed = []
    for path in runs.iterdir():
        match = anchor_context_publication._INCIDENT_FILENAME.fullmatch(
            path.name
        )
        if match is not None:
            indexed.append((int(match.group(1)), path))
    indexed.sort()
    records = []
    for index, path in indexed:
        raw = path.read_bytes()
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} is not valid JSON.",
            ) from error
        if anchor_context_publication.canonical_json_bytes(record) != raw:
            raise _CeremonyAbort(
                "preparation_incident_history_noncanonical",
                f"Incident {index} bytes are not canonical.",
            )
        configuration = (
            record.get("configuration_echo")
            if isinstance(record, Mapping)
            else None
        )
        if not isinstance(configuration, Mapping):
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} has no configuration echo.",
            )
        try:
            anchor_context_publication.validate_anchor_context_incident(
                record,
                path=path,
                expected_configuration_echo=configuration,
                repository_root=repository_root,
                validate_artifact_existence=False,
            )
        except (TypeError, ValueError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} violates the typed schema.",
            ) from error
        records.append(record)
    return _IncidentHistory(records=tuple(records))


def _assert_outputs_absent(repository_root: Path) -> None:
    for relative_path in (
        registry.PRIMARY_OUTPUT_PATH,
        registry.SIDECAR_OUTPUT_PATH,
    ):
        if os.path.lexists(repository_root / relative_path):
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_published_v1",
                "The primary report path or sidecar is already occupied.",
            )


def _authorize_invocation(
    configuration: Mapping[str, Any],
    history: _IncidentHistory,
) -> None:
    """Allow a fresh run or the sole unchanged eligible retry."""
    current = []
    expected_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )
    for record in history.records:
        if (
            record["registration_reference"]
            != configuration["registration_reference"]
        ):
            continue
        record_bytes = anchor_context_publication.canonical_json_bytes(
            record["configuration_echo"]
        )
        if record_bytes != expected_bytes:
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_configuration_drift",
                "This registration reference already has different bytes.",
            )
        current.append(record)
    if not current:
        return
    if len(current) != 1:
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_second_failure",
            "This registration already has a second failure.",
        )
    if not anchor_context_publication.incident_is_retry_eligible(current[0]):
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_nonretryable_incident",
            "The prior incident is not retry-eligible.",
        )


def _complete_prelaunch_checks(
    *,
    repository_root: Path,
    configuration: Mapping[str, Any],
    actual_invocation: Sequence[str],
    operations: _CoordinatorOperations,
) -> _IncidentHistory:
    """Perform the six §5.3 checks without opening either input."""
    if configuration["design"] != registry.design_binding():
        raise _CeremonyAbort(
            "preparation_design_binding_drift",
            "The registered design binding differs from the ratified design.",
        )
    operations.validate_repository(repository_root, configuration)
    anchor_context_publication._validate_configuration_echo_for_execution(
        configuration
    )
    if configuration["first_estimates_input"] != (
        registry.first_estimates_input_identity()
    ) and configuration["first_estimates_input"].get("path") in {
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    }:
        raise _CeremonyAbort(
            "preparation_mixed_input_identity_refused",
            "A fixture identity aliases a production path.",
        )
    _assert_outputs_absent(repository_root)
    history = _read_incident_history(repository_root)
    operations.assert_interpreter(configuration, actual_invocation)
    if (
        CANONICAL_EXECUTION_RULE["publishes_regardless"] is not True
        or CANONICAL_EXECUTION_RULE["no_self_rescue"] is not True
    ):
        raise AssertionError("canonical execution acknowledgement changed")
    _authorize_invocation(configuration, history)
    return history


def _safe_incident_fields(
    phase: str,
    error: BaseException,
    *,
    estimate_bearing_information_yielded: bool,
) -> tuple[str, str]:
    if (
        isinstance(error, ExternalPreOutputFailure)
        and phase in {"preparation", "compute"}
        and not estimate_bearing_information_yielded
    ):
        if _SAFE_REASON.fullmatch(error.reason) is None:
            raise AssertionError(
                "external reason was not constructor-validated"
            )
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
        first_publication._RegisteredConfigurationToken
        | anchor_context_publication._AnchorContextPrecomputeToken
    ),
    *,
    phase: str,
    error: BaseException,
    estimate_bearing_information_yielded: bool,
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    reason, detail = _safe_incident_fields(
        phase,
        error,
        estimate_bearing_information_yielded=(
            estimate_bearing_information_yielded
        ),
    )
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


def _run_registered_anchor_context_for_test(
    *,
    repository_root: str | Path,
    registered_configuration_bytes: bytes,
    actual_invocation: Sequence[str],
    operations: _CoordinatorOperations,
    production_only: bool = False,
) -> CoordinatorResult:
    """Test-private ceremony implementation with injectable operations."""
    root = Path(repository_root).resolve()
    registration = _parse_configuration(
        repository_root=root,
        registered_configuration_bytes=registered_configuration_bytes,
        production_only=production_only,
    )
    configuration = first_publication._configuration_echo(registration)
    precompute: (
        anchor_context_publication._AnchorContextPrecomputeToken | None
    ) = None
    try:
        _complete_prelaunch_checks(
            repository_root=root,
            configuration=configuration,
            actual_invocation=actual_invocation,
            operations=operations,
        )
        sidecar_payload, reported_sidecar_hash = operations.prepare_sidecar(
            root
        )
        runtime_provenance = operations.build_runtime_provenance(
            configuration["implementation_commit"]
        )
        precompute = anchor_context_publication._freeze_precompute(
            registration,
            runtime_provenance=runtime_provenance,
            sidecar_payload=sidecar_payload,
        )
        if reported_sidecar_hash != precompute.sidecar_sha256:
            raise ValueError(
                "prepared sidecar digest differs from frozen bytes"
            )
        first_estimates, anchors = operations.load_inputs(root, configuration)
    except BaseException as error:
        return _publish_abort(
            precompute or registration,
            phase="preparation",
            error=error,
            estimate_bearing_information_yielded=False,
            operations=operations,
        )

    operations.after_preparation()
    try:
        results = operations.build_results(first_estimates, anchors)
    except BaseException as error:
        return _publish_abort(
            precompute,
            phase="compute",
            error=error,
            estimate_bearing_information_yielded=False,
            operations=operations,
        )

    estimate_bearing_information_yielded = True
    try:
        operations.validate_results(
            results,
            first_estimates=first_estimates,
            anchors=anchors,
        )
        artifact = operations.build_artifact(
            configuration_echo=configuration,
            runtime_provenance=runtime_provenance,
            results=results,
            first_estimates=first_estimates,
            anchors=anchors,
            environment_sidecar_sha256=precompute.sidecar_sha256,
        )
    except BaseException as error:
        return _publish_abort(
            precompute,
            phase="invariant",
            error=error,
            estimate_bearing_information_yielded=(
                estimate_bearing_information_yielded
            ),
            operations=operations,
        )

    try:
        operations.validate_repository(root, configuration)
        path = operations.publish_artifact(
            precompute,
            artifact,
            first_estimates=first_estimates,
            anchors=anchors,
        )
    except BaseException as error:
        return _publish_abort(
            precompute,
            phase="publication",
            error=error,
            estimate_bearing_information_yielded=True,
            operations=operations,
        )
    return CoordinatorResult(
        status="published",
        path=path,
        phase="publication",
        reason=None,
    )


def _sealed_repository_root() -> Path:
    package_file = Path(estimates_package.__file__).resolve()
    if len(package_file.parents) < 4:
        raise RuntimeError("estimates package has no repository root")
    root = package_file.parents[3]
    expected = root / "src/populace_dynamics/estimates/__init__.py"
    if expected.resolve() != package_file:
        raise RuntimeError("estimates package is outside the source tree")
    return root.resolve()


def run_registered_anchor_context(
    registration_path: str | Path,
) -> CoordinatorResult:
    """Run the production ceremony with no input or output injection."""
    root = _sealed_repository_root()
    path = Path(registration_path)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("registration path escapes the repository") from error
    registered_configuration_bytes = resolved.read_bytes()
    actual_invocation = list(getattr(sys, "orig_argv", ()))
    with first_coordinator._exclusive_ceremony_lock(root):
        return _run_registered_anchor_context_for_test(
            repository_root=root,
            registered_configuration_bytes=registered_configuration_bytes,
            actual_invocation=actual_invocation,
            operations=_default_operations(),
            production_only=True,
        )


__all__ = [
    "CANONICAL_EXECUTION_RULE",
    "CoordinatorResult",
    "ExternalPreOutputFailure",
    "PRELAUNCH_CHECK_NAMES",
    "run_registered_anchor_context",
]
