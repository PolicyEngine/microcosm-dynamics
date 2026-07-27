"""Sealed coordinator for the registered anchor-context ceremony."""

from __future__ import annotations

import hashlib
import json
import os
import stat
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
_REGISTRATION_DIRECTORY = Path("docs/registrations")
_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_SAFE_REASON = first_coordinator._SAFE_EXTERNAL_REASON
_ATTEMPT_CLAIM_PATH = Path("runs/anchor_context_report_attempt.claim")
_ATTEMPT_CLAIM_SCHEMA = "anchor_context_report_attempt.v1"
_RETRY_CLAIM_PATH = Path("runs/anchor_context_report_retry.claim")
_RETRY_CLAIM_SCHEMA = "anchor_context_report_retry.v1"
_REGISTRATION_MAX_BYTES = 1024 * 1024


class _CeremonyAbort(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, init=False)
class _CeremonyCapability:
    """Unforgeable, live authority for production input I/O and compute."""

    registration: first_publication._RegisteredConfigurationToken
    prelaunch_record: _PrelaunchRecord
    attempt_claim: Path

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "ceremony capabilities are minted only by the coordinator"
        )


def _claim_payload(
    *,
    schema_version: str,
    registration_reference: str,
    retry_after_incident: int | None = None,
) -> bytes:
    first_publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    value: dict[str, Any] = {
        "schema_version": schema_version,
        "registration_reference": registration_reference,
    }
    if retry_after_incident is not None:
        if (
            isinstance(retry_after_incident, bool)
            or not isinstance(retry_after_incident, int)
            or retry_after_incident < 1
        ):
            raise TypeError("retry_after_incident must be a positive integer")
        value["retry_after_incident"] = retry_after_incident
    return anchor_context_publication.canonical_json_bytes(value)


def _read_claim(
    path: Path,
    *,
    schema_version: str,
    retry: bool,
) -> Mapping[str, Any] | None:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    if no_follow is None or nonblocking is None:
        return None
    try:
        descriptor = os.open(path, os.O_RDONLY | no_follow | nonblocking)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size
                > first_coordinator._ATTEMPT_CLAIM_MAX_BYTES
            ):
                return None
            payload = os.read(
                descriptor,
                first_coordinator._ATTEMPT_CLAIM_MAX_BYTES + 1,
            )
            if len(
                payload
            ) > first_coordinator._ATTEMPT_CLAIM_MAX_BYTES or os.read(
                descriptor, 1
            ):
                return None
        finally:
            os.close(descriptor)
        value = json.loads(payload)
        canonical = anchor_context_publication.canonical_json_bytes(value)
    except (
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ):
        return None
    expected_keys = {
        "schema_version",
        "registration_reference",
        *(("retry_after_incident",) if retry else ()),
    }
    if (
        not isinstance(value, Mapping)
        or canonical != payload
        or set(value) != expected_keys
        or value.get("schema_version") != schema_version
        or not isinstance(value.get("registration_reference"), str)
    ):
        return None
    retry_index = value.get("retry_after_incident")
    if retry and (
        isinstance(retry_index, bool)
        or not isinstance(retry_index, int)
        or retry_index < 1
    ):
        return None
    return value


def _write_claim(path: Path, payload: bytes) -> None:
    if len(payload) > first_coordinator._ATTEMPT_CLAIM_MAX_BYTES:
        raise ValueError("claim payload exceeds its read bound")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o444,
    )
    try:
        first_coordinator._write_attempt_claim_payload(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(
        path.parent,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _create_attempt_claim(
    repository_root: Path,
    registration_reference: str,
    *,
    allow_matching_retry_claim: bool,
) -> Path:
    runs = first_coordinator._sealed_runs_directory(repository_root)
    path = runs / _ATTEMPT_CLAIM_PATH.name
    payload = _claim_payload(
        schema_version=_ATTEMPT_CLAIM_SCHEMA,
        registration_reference=registration_reference,
    )
    try:
        _write_claim(path, payload)
    except FileExistsError:
        existing = _read_claim(
            path,
            schema_version=_ATTEMPT_CLAIM_SCHEMA,
            retry=False,
        )
        if (
            allow_matching_retry_claim
            and existing is not None
            and existing.get("registration_reference")
            == registration_reference
        ):
            return path
        raise _CeremonyAbort(
            (
                "preparation_fresh_registration_adjudication_required_"
                "attempt_claim"
            ),
            (
                "A durable anchor-context attempt claim already occupies "
                "the canonical path; fresh-registration adjudication is "
                "required."
            ),
        ) from None
    return path


def _create_retry_claim(
    repository_root: Path,
    registration_reference: str,
    retry_after_incident: int,
) -> Path:
    runs = first_coordinator._sealed_runs_directory(repository_root)
    path = runs / _RETRY_CLAIM_PATH.name
    payload = _claim_payload(
        schema_version=_RETRY_CLAIM_SCHEMA,
        registration_reference=registration_reference,
        retry_after_incident=retry_after_incident,
    )
    try:
        _write_claim(path, payload)
    except FileExistsError:
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_retry_claim",
            (
                "The durable anchor-context retry claim is already "
                "occupied; the sole retry is consumed."
            ),
        ) from None
    return path


@dataclass(frozen=True)
class _IncidentHistory:
    paths: tuple[str, ...]
    records: tuple[Mapping[str, Any], ...]


def _continue_after_preparation() -> None:
    """Production no-op at the test-private preparation boundary."""


def _retain_prelaunch_record(_record: _PrelaunchRecord) -> None:
    """Production keeps the frozen record in the active call frame."""


@dataclass(frozen=True)
class _PrelaunchRecord:
    """In-memory proof that all six registered checks preceded input load."""

    check_names: tuple[str, ...]
    configuration_sha256: str
    next_incident_index: int


def _ceremony_capability_protocol():
    """Expose only the sealed runner and live-capability verifier."""
    issued: dict[
        int,
        tuple[
            _CeremonyCapability,
            first_publication._RegisteredConfigurationToken,
            _PrelaunchRecord,
            Path,
            bytes,
            tuple[int, int],
        ],
    ] = {}

    def mint(
        registration: first_publication._RegisteredConfigurationToken,
        prelaunch_record: _PrelaunchRecord,
        attempt_claim: Path,
    ) -> _CeremonyCapability:
        caller = sys._getframe(1)
        parent = caller.f_back
        if (
            caller.f_code is not _run_registered_anchor_context_core.__code__
            or parent is None
            or parent.f_code is not run.__code__
            or caller.f_locals.get("mint_capability") is not mint
            or caller.f_locals.get("production_only") is not True
            or caller.f_locals.get("registration") is not registration
            or caller.f_locals.get("prelaunch_record") is not prelaunch_record
            or caller.f_locals.get("attempt_claim") != attempt_claim
        ):
            raise TypeError(
                "ceremony capabilities can be minted only on the sealed "
                "runner stack"
            )
        if not isinstance(
            registration,
            first_publication._RegisteredConfigurationToken,
        ):
            raise TypeError("ceremony capability requires registration")
        if not isinstance(prelaunch_record, _PrelaunchRecord):
            raise TypeError("ceremony capability requires all six checks")
        expected_claim = registration._repository_root / _ATTEMPT_CLAIM_PATH
        if attempt_claim != expected_claim:
            raise RuntimeError("ceremony capability claim path changed")
        claim = _read_claim(
            attempt_claim,
            schema_version=_ATTEMPT_CLAIM_SCHEMA,
            retry=False,
        )
        if (
            claim is None
            or claim.get("registration_reference")
            != registration._registration_reference
        ):
            raise RuntimeError(
                "ceremony capability requires its canonical attempt claim"
            )
        claim_payload = _claim_payload(
            schema_version=_ATTEMPT_CLAIM_SCHEMA,
            registration_reference=registration._registration_reference,
        )
        claim_metadata = os.stat(attempt_claim, follow_symlinks=False)
        claim_file_id = (claim_metadata.st_dev, claim_metadata.st_ino)
        capability = object.__new__(_CeremonyCapability)
        object.__setattr__(capability, "registration", registration)
        object.__setattr__(
            capability,
            "prelaunch_record",
            prelaunch_record,
        )
        object.__setattr__(capability, "attempt_claim", attempt_claim)
        issued[id(capability)] = (
            capability,
            registration,
            prelaunch_record,
            attempt_claim,
            claim_payload,
            claim_file_id,
        )
        return capability

    def require(
        capability: object,
    ) -> first_publication._RegisteredConfigurationToken:
        state = issued.get(id(capability))
        if (
            state is None
            or state[0] is not capability
            or not isinstance(capability, _CeremonyCapability)
        ):
            raise TypeError(
                "production operation requires a live ceremony capability"
            )
        (
            _,
            registration,
            record,
            attempt_claim,
            claim_payload,
            claim_file_id,
        ) = state
        current_claim = _read_claim(
            attempt_claim,
            schema_version=_ATTEMPT_CLAIM_SCHEMA,
            retry=False,
        )
        try:
            claim_metadata = os.stat(attempt_claim, follow_symlinks=False)
        except OSError as error:
            raise TypeError("ceremony attempt claim disappeared") from error
        if (
            capability.registration is not registration
            or capability.prelaunch_record is not record
            or capability.attempt_claim != attempt_claim
            or current_claim is None
            or anchor_context_publication.canonical_json_bytes(current_claim)
            != claim_payload
            or (claim_metadata.st_dev, claim_metadata.st_ino) != claim_file_id
        ):
            raise TypeError("ceremony capability state changed")
        return registration

    def revoke(capability: object) -> None:
        state = issued.get(id(capability))
        if state is not None and state[0] is capability:
            issued.pop(id(capability), None)

    def run(registration_path: str | Path) -> CoordinatorResult:
        root = _sealed_repository_root()
        actual_invocation = list(getattr(sys, "orig_argv", ()))
        with first_coordinator._exclusive_ceremony_lock(root):
            registered_configuration_bytes = (
                _read_registered_configuration_bytes(
                    root,
                    registration_path,
                )
            )
            return _run_registered_anchor_context_core(
                repository_root=root,
                registered_configuration_bytes=registered_configuration_bytes,
                actual_invocation=actual_invocation,
                operations=_default_operations(),
                production_only=True,
                mint_capability=mint,
                revoke_capability=revoke,
            )

    run.__name__ = "run_registered_anchor_context"
    run.__qualname__ = "run_registered_anchor_context"
    run.__doc__ = (
        "Run the production ceremony through the sealed registration gate."
    )
    return run, require


run_registered_anchor_context, _require_ceremony_capability = (
    _ceremony_capability_protocol()
)


@dataclass(frozen=True)
class _CoordinatorOperations:
    """Injectable seams; the public production function accepts none."""

    assert_interpreter: Callable[[Mapping[str, Any], Sequence[str]], None]
    validate_repository: Callable[[Path, Mapping[str, Any]], None]
    prepare_sidecar: Callable[[Path], tuple[bytes, str]]
    load_inputs: Callable[[object], Any]
    build_results: Callable[..., Mapping[str, Any]]
    validate_results: Callable[..., None]
    build_runtime_provenance: Callable[[str], Mapping[str, Any]]
    build_artifact: Callable[..., Mapping[str, Any]]
    publish_artifact: Callable[..., Path]
    publish_incident: Callable[..., Path]
    after_preparation: Callable[[], None] = _continue_after_preparation
    record_prelaunch: Callable[[_PrelaunchRecord], None] = (
        _retain_prelaunch_record
    )


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
    ceremony_capability: _CeremonyCapability,
) -> anchor_context_publication._VerifiedProductionInputs:
    return anchor_context_publication._load_production_documents(
        ceremony_capability
    )


def _build_results(
    ceremony_capability: _CeremonyCapability,
    loaded_inputs: anchor_context_publication._VerifiedProductionInputs,
) -> Mapping[str, Any]:
    return anchor_context_report._build_production_results(
        ceremony_capability,
        loaded_inputs,
    )


def _validate_results(
    ceremony_capability: _CeremonyCapability,
    results: Mapping[str, Any],
    loaded_inputs: anchor_context_publication._VerifiedProductionInputs,
) -> None:
    anchor_context_report._validate_production_results(
        ceremony_capability,
        results,
        loaded_inputs,
    )


def _publish_artifact(
    token: anchor_context_publication._AnchorContextPrecomputeToken,
    artifact: Mapping[str, Any],
    *,
    input_bundle: object,
    ceremony_capability: _CeremonyCapability,
) -> Path:
    return anchor_context_publication.write_anchor_context_artifact(
        token,
        artifact,
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
    )


def _default_operations() -> _CoordinatorOperations:
    return _CoordinatorOperations(
        assert_interpreter=_assert_sealed_interpreter,
        validate_repository=_validate_repository,
        prepare_sidecar=(
            anchor_context_publication.prepare_environment_sidecar
        ),
        load_inputs=_load_inputs,
        build_results=_build_results,
        validate_results=_validate_results,
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
    *,
    production_only: bool,
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
    paths = []
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
            anchor_context_publication._validate_anchor_context_incident(
                record,
                path=path,
                expected_configuration_echo=configuration,
                repository_root=repository_root,
                production_only=production_only,
            )
        except (TypeError, ValueError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                f"Incident {index} violates the typed schema.",
            ) from error
        paths.append(path.relative_to(repository_root).as_posix())
        records.append(record)
    return _IncidentHistory(paths=tuple(paths), records=tuple(records))


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
) -> int | None:
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
        return None
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
    return current[0]["incident_index"]


def _complete_prelaunch_checks(
    *,
    repository_root: Path,
    configuration: Mapping[str, Any],
    actual_invocation: Sequence[str],
    history: _IncidentHistory,
    operations: _CoordinatorOperations,
) -> _PrelaunchRecord:
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
    if len(history.paths) != len(history.records):
        raise AssertionError("incident history paths and records differ")
    operations.assert_interpreter(configuration, actual_invocation)
    if (
        CANONICAL_EXECUTION_RULE["publishes_regardless"] is not True
        or CANONICAL_EXECUTION_RULE["no_self_rescue"] is not True
    ):
        raise AssertionError("canonical execution acknowledgement changed")
    record = _PrelaunchRecord(
        check_names=PRELAUNCH_CHECK_NAMES,
        configuration_sha256=hashlib.sha256(
            anchor_context_publication.canonical_json_bytes(configuration)
        ).hexdigest(),
        next_incident_index=len(history.paths) + 1,
    )
    operations.record_prelaunch(record)
    return record


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
    if isinstance(error, (_CeremonyAbort, first_coordinator._CeremonyAbort)):
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


def _run_registered_anchor_context_core(
    *,
    repository_root: str | Path,
    registered_configuration_bytes: bytes,
    actual_invocation: Sequence[str],
    operations: _CoordinatorOperations,
    production_only: bool,
    mint_capability: (
        Callable[
            [
                first_publication._RegisteredConfigurationToken,
                _PrelaunchRecord,
                Path,
            ],
            _CeremonyCapability,
        ]
        | None
    ),
    revoke_capability: Callable[[object], None] | None,
) -> CoordinatorResult:
    """Shared ceremony state machine; only the sealed closure can mint."""
    if production_only != (mint_capability is not None):
        raise TypeError("production execution requires the sealed issuer")
    if (mint_capability is None) != (revoke_capability is None):
        raise TypeError("ceremony capability lifecycle is incomplete")
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
    ceremony_capability: _CeremonyCapability | None = None
    try:
        try:
            history = _read_incident_history(
                root,
                production_only=production_only,
            )
            retry_after_incident = _authorize_invocation(
                configuration,
                history,
            )
            prelaunch_record = _complete_prelaunch_checks(
                repository_root=root,
                configuration=configuration,
                actual_invocation=actual_invocation,
                history=history,
                operations=operations,
            )
            if prelaunch_record.check_names != PRELAUNCH_CHECK_NAMES:
                raise AssertionError("prelaunch check record changed")
            attempt_claim = _create_attempt_claim(
                root,
                configuration["registration_reference"],
                allow_matching_retry_claim=retry_after_incident is not None,
            )
            if retry_after_incident is not None:
                _create_retry_claim(
                    root,
                    configuration["registration_reference"],
                    retry_after_incident,
                )
            execution_authority: object = registration
            if mint_capability is not None:
                ceremony_capability = mint_capability(
                    registration,
                    prelaunch_record,
                    attempt_claim,
                )
                execution_authority = ceremony_capability
            sidecar_payload, reported_sidecar_hash = (
                operations.prepare_sidecar(root)
            )
            runtime_provenance = operations.build_runtime_provenance(
                configuration["implementation_commit"]
            )
            precompute = anchor_context_publication._freeze_precompute(
                registration,
                runtime_provenance=runtime_provenance,
                sidecar_payload=sidecar_payload,
                prior_incidents=history.paths,
            )
            if reported_sidecar_hash != precompute.sidecar_sha256:
                raise ValueError(
                    "prepared sidecar digest differs from frozen bytes"
                )
            loaded_inputs = operations.load_inputs(execution_authority)
            if production_only:
                anchor_context_publication._require_verified_production_inputs(
                    loaded_inputs,
                    ceremony_capability=ceremony_capability,
                )
            else:
                anchor_context_publication._require_verified_fixture_inputs(
                    loaded_inputs
                )
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
            results = operations.build_results(
                execution_authority,
                loaded_inputs,
            )
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
                execution_authority,
                results,
                loaded_inputs,
            )
            artifact = operations.build_artifact(
                configuration_echo=configuration,
                runtime_provenance=runtime_provenance,
                results=results,
                input_bundle=loaded_inputs,
                environment_sidecar_sha256=precompute.sidecar_sha256,
                prior_incidents=precompute.prior_incidents,
                ceremony_capability=ceremony_capability,
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
                input_bundle=loaded_inputs,
                ceremony_capability=ceremony_capability,
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
    finally:
        if ceremony_capability is not None and revoke_capability is not None:
            revoke_capability(ceremony_capability)


def _run_registered_anchor_context_for_test(
    *,
    repository_root: str | Path,
    registered_configuration_bytes: bytes,
    actual_invocation: Sequence[str],
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    """Run only the fixed-fixture ceremony with injectable test operations."""
    return _run_registered_anchor_context_core(
        repository_root=repository_root,
        registered_configuration_bytes=registered_configuration_bytes,
        actual_invocation=actual_invocation,
        operations=operations,
        production_only=False,
        mint_capability=None,
        revoke_capability=None,
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


def _read_registered_configuration_bytes(
    repository_root: Path,
    registration_path: str | Path,
) -> bytes:
    """Validate and read registration through one pinned descriptor chain."""
    root = repository_root.resolve()
    candidate = Path(registration_path)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(
                "registration path escapes the repository"
            ) from error
    else:
        relative = candidate
    parts = relative.parts
    if relative in {
        Path(registry.FIRST_ESTIMATES_INPUT_PATH),
        Path(registry.ANCHOR_INPUT_PATH),
    }:
        raise ValueError("registration path aliases protected ceremony data")
    if (
        len(parts) != 3
        or parts[:2] != _REGISTRATION_DIRECTORY.parts
        or parts[2] in {"", ".", ".."}
        or not parts[2].endswith(".json")
    ):
        raise ValueError(
            "registration must be a regular JSON file directly under "
            "docs/registrations"
        )
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    close_on_exec = getattr(os, "O_CLOEXEC", None)
    if (
        no_follow is None
        or directory_flag is None
        or nonblocking is None
        or close_on_exec is None
    ):
        raise RuntimeError("platform lacks sealed registration flags")

    descriptors: list[int] = []
    registration_descriptor: int | None = None
    try:
        root_descriptor = os.open(
            root,
            os.O_RDONLY | directory_flag | no_follow | close_on_exec,
        )
        descriptors.append(root_descriptor)
        protected_file_ids: set[tuple[int, int]] = set()
        for protected_path in (
            registry.FIRST_ESTIMATES_INPUT_PATH,
            registry.ANCHOR_INPUT_PATH,
        ):
            try:
                protected = os.stat(
                    protected_path,
                    dir_fd=root_descriptor,
                    follow_symlinks=False,
                )
            except OSError:
                continue
            if not stat.S_ISREG(protected.st_mode):
                raise ValueError(
                    "canonical production input path is not regular"
                )
            protected_file_ids.add((protected.st_dev, protected.st_ino))
        current = root_descriptor
        for component in _REGISTRATION_DIRECTORY.parts:
            current = os.open(
                component,
                os.O_RDONLY | directory_flag | no_follow | close_on_exec,
                dir_fd=current,
            )
            descriptors.append(current)
        registration_descriptor = os.open(
            parts[2],
            os.O_RDONLY | no_follow | nonblocking | close_on_exec,
            dir_fd=current,
        )
        before = os.fstat(registration_descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > _REGISTRATION_MAX_BYTES
        ):
            raise ValueError(
                "registration must be one singly linked bounded regular file"
            )
        if (before.st_dev, before.st_ino) in protected_file_ids:
            raise ValueError(
                "registration path aliases protected ceremony data"
            )
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(
                registration_descriptor,
                min(64 * 1024, _REGISTRATION_MAX_BYTES + 1 - observed),
            )
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > _REGISTRATION_MAX_BYTES:
                raise ValueError(
                    "registered configuration exceeds its byte bound"
                )
        payload = b"".join(chunks)
        after = os.fstat(registration_descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(before, field) != getattr(after, field)
            for field in stable_fields
        ):
            raise ValueError("registration changed during its sealed read")
        return payload
    finally:
        if registration_descriptor is not None:
            os.close(registration_descriptor)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


__all__ = [
    "CANONICAL_EXECUTION_RULE",
    "CoordinatorResult",
    "ExternalPreOutputFailure",
    "PRELAUNCH_CHECK_NAMES",
    "run_registered_anchor_context",
]
