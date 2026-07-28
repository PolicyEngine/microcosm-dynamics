"""Sealed coordinator for the registered anchor-context ceremony."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import populace_dynamics.estimates as estimates_package
from populace_dynamics.estimates import (
    anchor_context_publication,
    anchor_context_report,
)
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import coordinator as first_coordinator
from populace_dynamics.estimates import publication as first_publication

_bind_coordinator_capability_verifier = (
    anchor_context_publication._take_coordinator_capability_verifier_binding()
)

CoordinatorResult = first_coordinator.CoordinatorResult
ExternalPreOutputFailure = first_coordinator.ExternalPreOutputFailure


def _execution_rule_protocol():
    """Retain the execution law as private immutable canonical bytes."""
    frozen = anchor_context_publication.canonical_json_bytes(
        {
            "registered_runs": 1,
            "publishes_regardless": True,
            "no_self_rescue": True,
            "retry": (
                "At most one coordinator-adjudicated, report-first retry "
                "solely for an external preparation or compute incident that "
                "yielded no estimate-bearing information."
            ),
            "fresh_registration_required_if": (
                "A published v1, any changed configuration byte, or a second "
                "failure of any kind."
            ),
        }
    )

    def value() -> Mapping[str, Any]:
        decoded = json.loads(frozen)
        if not isinstance(decoded, Mapping):
            raise AssertionError("private execution law is not a mapping")
        return decoded

    return (
        MappingProxyType(dict(value())),
        bytes(bytearray(frozen)),
        bytes(bytearray(frozen)),
    )


(
    CANONICAL_EXECUTION_RULE,
    _VALIDATION_EXECUTION_RULE_BYTES,
    _COMPLETION_EXECUTION_RULE_BYTES,
) = _execution_rule_protocol()
del _execution_rule_protocol
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
_ATTEMPT_CLAIM_SCHEMA = "anchor_context_report_attempt.v3"
_RETRY_CLAIM_PATH = Path("runs/anchor_context_report_retry.claim")
_RETRY_CLAIM_SCHEMA = "anchor_context_report_retry.v3"
_RETRY_AUTHORITY_PATH = Path(
    "runs/anchor_context_report_retry_authority.claim"
)
_RETRY_AUTHORITY_SCHEMA = "anchor_context_report_retry_authority.v1"
_PRELAUNCH_RECORD_SCHEMA = "anchor_context_report_prelaunch.v1"
_CLAIM_MAX_BYTES = 1024 * 1024
_INCIDENT_MAX_BYTES = 4 * 1024 * 1024
_REGISTRATION_MAX_BYTES = 1024 * 1024


class _CeremonyAbort(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, init=False)
class _CoordinatorInvocation:
    """Opaque authority to enter the production ceremony state machine."""

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "coordinator invocations are issued only by the coordinator"
        )


@dataclass(frozen=True, init=False)
class _CeremonyCapability:
    """Unforgeable, live authority for production input I/O and compute."""

    registration: first_publication._RegisteredConfigurationToken
    prelaunch_record: _PrelaunchRecord
    attempt_claim: Path
    retry_claim: Path | None

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "ceremony capabilities are minted only by the coordinator"
        )


@dataclass(frozen=True, init=False)
class _InitialAttemptAuthority:
    """Live authority retaining the pre-incident nonce and reserved inode."""

    attempt_claim: Path

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "initial-attempt authority is minted only by the coordinator"
        )


@dataclass(frozen=True, init=False)
class _RetryAuthorization:
    """Opaque authorization minted only from authenticated durable evidence."""

    incident_index: int

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "retry authorization is minted only by the coordinator"
        )


@dataclass(frozen=True, init=False)
class _RetryReceipt:
    """One-shot handoff retained only inside one coordinator invocation."""

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError("retry receipts are minted only by the coordinator")


@dataclass(frozen=True, init=False)
class _CoordinatorAttemptOutcome:
    """Internal result plus the optional report-first retry handoff."""

    result: CoordinatorResult
    retry_receipt: _RetryReceipt | None

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError("attempt outcomes are created only by the coordinator")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _read_canonical_mapping(
    path: Path,
    *,
    maximum_bytes: int,
    expected_name: str,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    """Read a canonical claim through a pinned root-to-leaf descriptor chain."""
    stable_fields = (
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_dev",
        "st_ino",
    )

    def signature(metadata: os.stat_result) -> tuple[int, ...]:
        return tuple(getattr(metadata, field) for field in stable_fields)

    candidate = Path(path)
    permitted_names = {
        _ATTEMPT_CLAIM_PATH.name,
        _RETRY_AUTHORITY_PATH.name,
        _RETRY_CLAIM_PATH.name,
    }
    if (
        expected_name != candidate.name
        or candidate.parent.name != "runs"
        or (
            expected_name not in permitted_names
            and anchor_context_publication._INCIDENT_FILENAME.fullmatch(
                expected_name
            )
            is None
        )
    ):
        return None
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
        return None
    repository_root = candidate.parent.parent
    descriptors: list[int] = []
    claim_descriptor: int | None = None
    try:
        root_before = os.stat(repository_root, follow_symlinks=False)
        if not stat.S_ISDIR(root_before.st_mode):
            return None
        root_descriptor = os.open(
            repository_root,
            os.O_RDONLY | directory_flag | no_follow | close_on_exec,
        )
        descriptors.append(root_descriptor)
        root_opened = os.fstat(root_descriptor)
        if signature(root_opened) != signature(root_before):
            return None

        runs_before = os.stat(
            "runs",
            dir_fd=root_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(runs_before.st_mode):
            return None
        runs_descriptor = os.open(
            "runs",
            os.O_RDONLY | directory_flag | no_follow | close_on_exec,
            dir_fd=root_descriptor,
        )
        descriptors.append(runs_descriptor)
        runs_opened = os.fstat(runs_descriptor)
        if signature(runs_opened) != signature(runs_before):
            return None

        protected_file_ids: set[tuple[int, int]] = set()
        for protected_relative in (
            registry.FIRST_ESTIMATES_INPUT_PATH,
            registry.ANCHOR_INPUT_PATH,
        ):
            try:
                protected = os.stat(
                    protected_relative,
                    dir_fd=root_descriptor,
                )
            except OSError:
                continue
            protected_file_ids.add((protected.st_dev, protected.st_ino))

        candidate_before = os.stat(
            expected_name,
            dir_fd=runs_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(candidate_before.st_mode)
            or candidate_before.st_nlink != 1
            or candidate_before.st_size > maximum_bytes
            or (candidate_before.st_dev, candidate_before.st_ino)
            in protected_file_ids
        ):
            return None
        claim_descriptor = os.open(
            expected_name,
            os.O_RDONLY | no_follow | nonblocking | close_on_exec,
            dir_fd=runs_descriptor,
        )
        metadata = os.fstat(claim_descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > maximum_bytes
            or signature(metadata) != signature(candidate_before)
            or (metadata.st_dev, metadata.st_ino) in protected_file_ids
        ):
            return None
        chunks = bytearray()
        while len(chunks) <= maximum_bytes:
            chunk = os.read(
                claim_descriptor,
                maximum_bytes + 1 - len(chunks),
            )
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > maximum_bytes:
            return None
        payload = bytes(chunks)
        after = os.fstat(claim_descriptor)
        named_after = os.stat(
            expected_name,
            dir_fd=runs_descriptor,
            follow_symlinks=False,
        )
        if (
            len(payload) != metadata.st_size
            or signature(after) != signature(metadata)
            or signature(named_after) != signature(metadata)
        ):
            return None
        root_after = os.fstat(root_descriptor)
        root_named_after = os.stat(repository_root, follow_symlinks=False)
        runs_after = os.fstat(runs_descriptor)
        runs_named_after = os.stat(
            "runs",
            dir_fd=root_descriptor,
            follow_symlinks=False,
        )
        if (
            signature(root_after) != signature(root_opened)
            or signature(root_named_after) != signature(root_opened)
            or signature(runs_after) != signature(runs_opened)
            or signature(runs_named_after) != signature(runs_opened)
        ):
            return None
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
    finally:
        if claim_descriptor is not None:
            os.close(claim_descriptor)
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if (
        not isinstance(value, Mapping)
        or canonical != payload
        or len(payload) > maximum_bytes
    ):
        return None
    return value, payload, (metadata.st_dev, metadata.st_ino)


def _attempt_claim_payload(
    *,
    registration_reference: str,
    configuration_sha256: str,
    next_incident_index: int,
    authority_file_id: tuple[int, int],
    authority_nonce_sha256: str,
    prelaunch_record: _PrelaunchRecord,
) -> bytes:
    first_publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    if not _is_sha256(configuration_sha256):
        raise TypeError("configuration_sha256 must be lowercase SHA-256")
    if (
        isinstance(next_incident_index, bool)
        or not isinstance(next_incident_index, int)
        or next_incident_index < 1
    ):
        raise TypeError("next_incident_index must be a positive integer")
    if not _is_sha256(authority_nonce_sha256):
        raise TypeError("authority nonce commitment must be lowercase SHA-256")
    prelaunch = _prelaunch_record_value(prelaunch_record)
    if (
        prelaunch["registration_reference"] != registration_reference
        or prelaunch["configuration_sha256"] != configuration_sha256
        or prelaunch["next_incident_index"] != next_incident_index
    ):
        raise ValueError("attempt claim differs from its prelaunch evidence")
    authority_device, authority_inode = authority_file_id
    if (
        isinstance(authority_device, bool)
        or not isinstance(authority_device, int)
        or authority_device < 0
        or isinstance(authority_inode, bool)
        or not isinstance(authority_inode, int)
        or authority_inode < 1
    ):
        raise TypeError(
            "authority file identity must contain positive integers"
        )
    return anchor_context_publication.canonical_json_bytes(
        {
            "schema_version": _ATTEMPT_CLAIM_SCHEMA,
            "registration_reference": registration_reference,
            "configuration_sha256": configuration_sha256,
            "next_incident_index": next_incident_index,
            "authority_path": _RETRY_AUTHORITY_PATH.as_posix(),
            "authority_device": authority_device,
            "authority_inode": authority_inode,
            "authority_nonce_sha256": authority_nonce_sha256,
            "prelaunch_record": prelaunch,
        }
    )


def _read_attempt_claim(
    path: Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    loaded = _read_canonical_mapping(
        path,
        maximum_bytes=_CLAIM_MAX_BYTES,
        expected_name=_ATTEMPT_CLAIM_PATH.name,
    )
    if loaded is None:
        return None
    value, payload, file_id = loaded
    expected_keys = {
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
    next_index = value.get("next_incident_index")
    authority_device = value.get("authority_device")
    authority_inode = value.get("authority_inode")
    try:
        prelaunch = _validate_prelaunch_record_value(
            value.get("prelaunch_record")
        )
    except (TypeError, ValueError):
        return None
    if (
        set(value) != expected_keys
        or value.get("schema_version") != _ATTEMPT_CLAIM_SCHEMA
        or not isinstance(value.get("registration_reference"), str)
        or not _is_sha256(value.get("configuration_sha256"))
        or isinstance(next_index, bool)
        or not isinstance(next_index, int)
        or next_index < 1
        or value.get("authority_path") != _RETRY_AUTHORITY_PATH.as_posix()
        or isinstance(authority_device, bool)
        or not isinstance(authority_device, int)
        or authority_device < 0
        or isinstance(authority_inode, bool)
        or not isinstance(authority_inode, int)
        or authority_inode < 1
        or not _is_sha256(value.get("authority_nonce_sha256"))
        or prelaunch["registration_reference"]
        != value.get("registration_reference")
        or prelaunch["configuration_sha256"]
        != value.get("configuration_sha256")
        or prelaunch["next_incident_index"] != next_index
    ):
        return None
    return value, payload, file_id


def _retry_authority_payload(
    *,
    registration_reference: str,
    configuration_sha256: str,
    attempt_claim_sha256: str,
    authority_nonce: str,
    incident_index: int,
    incident_path: str,
    incident_sha256: str,
) -> bytes:
    return anchor_context_publication.canonical_json_bytes(
        {
            "schema_version": _RETRY_AUTHORITY_SCHEMA,
            "registration_reference": registration_reference,
            "configuration_sha256": configuration_sha256,
            "attempt_claim_sha256": attempt_claim_sha256,
            "authority_nonce": authority_nonce,
            "incident_index": incident_index,
            "incident_path": incident_path,
            "incident_sha256": incident_sha256,
            "estimate_bearing_information_yielded": False,
        }
    )


def _read_retry_authority(
    path: Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    loaded = _read_canonical_mapping(
        path,
        maximum_bytes=_CLAIM_MAX_BYTES,
        expected_name=_RETRY_AUTHORITY_PATH.name,
    )
    if loaded is None:
        return None
    value, payload, file_id = loaded
    expected_keys = {
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
    incident_index = value.get("incident_index")
    if (
        set(value) != expected_keys
        or value.get("schema_version") != _RETRY_AUTHORITY_SCHEMA
        or not isinstance(value.get("registration_reference"), str)
        or not _is_sha256(value.get("configuration_sha256"))
        or not _is_sha256(value.get("attempt_claim_sha256"))
        or not _is_sha256(value.get("authority_nonce"))
        or isinstance(incident_index, bool)
        or not isinstance(incident_index, int)
        or incident_index < 1
        or value.get("incident_path")
        != f"runs/anchor_context_report_incident_{incident_index}.json"
        or not _is_sha256(value.get("incident_sha256"))
        or value.get("estimate_bearing_information_yielded") is not False
    ):
        return None
    return value, payload, file_id


def _retry_claim_payload(
    *,
    registration_reference: str,
    retry_after_incident: int,
    retry_authority_sha256: str,
    prelaunch_record: _PrelaunchRecord,
) -> bytes:
    first_publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    if (
        isinstance(retry_after_incident, bool)
        or not isinstance(retry_after_incident, int)
        or retry_after_incident < 1
    ):
        raise TypeError("retry_after_incident must be a positive integer")
    if not _is_sha256(retry_authority_sha256):
        raise TypeError("retry authority digest must be lowercase SHA-256")
    prelaunch = _prelaunch_record_value(prelaunch_record)
    if (
        prelaunch["registration_reference"] != registration_reference
        or prelaunch["next_incident_index"] != retry_after_incident + 1
    ):
        raise ValueError("retry claim differs from its prelaunch evidence")
    return anchor_context_publication.canonical_json_bytes(
        {
            "schema_version": _RETRY_CLAIM_SCHEMA,
            "registration_reference": registration_reference,
            "retry_after_incident": retry_after_incident,
            "retry_authority_sha256": retry_authority_sha256,
            "prelaunch_record": prelaunch,
        }
    )


def _read_retry_claim(
    path: Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    loaded = _read_canonical_mapping(
        path,
        maximum_bytes=_CLAIM_MAX_BYTES,
        expected_name=_RETRY_CLAIM_PATH.name,
    )
    if loaded is None:
        return None
    value, payload, file_id = loaded
    retry_index = value.get("retry_after_incident")
    if (
        set(value)
        != {
            "schema_version",
            "registration_reference",
            "retry_after_incident",
            "retry_authority_sha256",
            "prelaunch_record",
        }
        or value.get("schema_version") != _RETRY_CLAIM_SCHEMA
        or not isinstance(value.get("registration_reference"), str)
        or isinstance(retry_index, bool)
        or not isinstance(retry_index, int)
        or retry_index < 1
        or not _is_sha256(value.get("retry_authority_sha256"))
    ):
        return None
    try:
        prelaunch = _validate_prelaunch_record_value(
            value.get("prelaunch_record")
        )
    except (TypeError, ValueError):
        return None
    if (
        prelaunch["registration_reference"]
        != value.get("registration_reference")
        or prelaunch["next_incident_index"] != retry_index + 1
    ):
        return None
    return value, payload, file_id


def _write_claim(path: Path, payload: bytes) -> None:
    if len(payload) > _CLAIM_MAX_BYTES:
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


@dataclass(frozen=True)
class _IncidentHistory:
    paths: tuple[str, ...]
    records: tuple[Mapping[str, Any], ...]
    payloads: tuple[bytes, ...]
    file_ids: tuple[tuple[int, int], ...]


def _continue_after_preparation() -> None:
    """Production no-op at the test-private preparation boundary."""


def _retain_prelaunch_record(record: _PrelaunchRecord) -> None:
    """Exact-check the frozen record before its durable claim is observed."""
    _prelaunch_record_value(record)


@dataclass(frozen=True)
class _PrelaunchRecord:
    """Immutable canonical evidence that all six checks preceded input load."""

    check_names: tuple[str, ...]
    configuration_sha256: str
    next_incident_index: int
    evidence_bytes: bytes


def _validate_prelaunch_record_value_impl(
    candidate: object,
    *,
    execution_rule: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(candidate, Mapping):
        raise TypeError("prelaunch record must be a JSON object")
    value = candidate
    if set(value) != {
        "schema_version",
        "registration_reference",
        "configuration_sha256",
        "next_incident_index",
        "checks",
    }:
        raise ValueError("prelaunch record keys changed")
    if value["schema_version"] != _PRELAUNCH_RECORD_SCHEMA:
        raise ValueError("prelaunch record schema changed")
    reference = value["registration_reference"]
    if not isinstance(reference, str) or not reference:
        raise TypeError("prelaunch registration reference is invalid")
    configuration_sha256 = value["configuration_sha256"]
    if not _is_sha256(configuration_sha256):
        raise TypeError("prelaunch configuration digest is invalid")
    next_index = value["next_incident_index"]
    if (
        isinstance(next_index, bool)
        or not isinstance(next_index, int)
        or next_index < 1
    ):
        raise TypeError("prelaunch next incident index is invalid")
    checks = value["checks"]
    if not isinstance(checks, list) or len(checks) != len(
        PRELAUNCH_CHECK_NAMES
    ):
        raise TypeError("prelaunch checks must be the exact ordered six")
    evidence_by_name: dict[str, Mapping[str, Any]] = {}
    for position, expected_name in enumerate(PRELAUNCH_CHECK_NAMES):
        check = checks[position]
        if (
            not isinstance(check, Mapping)
            or set(check) != {"name", "passed", "evidence"}
            or check["name"] != expected_name
            or check["passed"] is not True
            or not isinstance(check["evidence"], Mapping)
        ):
            raise ValueError("prelaunch check order or pass state changed")
        evidence_by_name[expected_name] = check["evidence"]

    design = evidence_by_name[PRELAUNCH_CHECK_NAMES[0]]
    if (
        set(design)
        != {
            "design",
            "implementation_commit",
            "production_input_io_before_launch",
        }
        or design["design"] != registry.design_binding()
        or not isinstance(design["implementation_commit"], str)
        or len(design["implementation_commit"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in design["implementation_commit"]
        )
        or design["production_input_io_before_launch"] is not False
    ):
        raise ValueError("ratification and no-input evidence changed")
    anchor_context_publication._assert_exact_json(
        design["design"],
        registry.design_binding(),
        "prelaunch ratified design",
    )

    registration = evidence_by_name[PRELAUNCH_CHECK_NAMES[1]]
    if set(registration) != {
        "registration_reference",
        "registered_configuration",
        "registered_configuration_sha256",
        "registered_configuration_byte_length",
    }:
        raise ValueError("registration evidence keys changed")
    configuration = registration["registered_configuration"]
    if not isinstance(configuration, Mapping):
        raise TypeError("registered configuration evidence is not an object")
    configuration_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )
    anchor_context_publication._validate_configuration_echo_for_execution(
        configuration
    )
    if (
        registration["registration_reference"] != reference
        or configuration.get("registration_reference") != reference
        or configuration.get("implementation_commit")
        != design["implementation_commit"]
        or registration["registered_configuration_sha256"]
        != configuration_sha256
        or hashlib.sha256(configuration_bytes).hexdigest()
        != configuration_sha256
        or registration["registered_configuration_byte_length"]
        != len(configuration_bytes)
    ):
        raise ValueError("registered configuration evidence changed")

    inputs = evidence_by_name[PRELAUNCH_CHECK_NAMES[2]]
    if (
        set(inputs)
        != {
            "first_estimates_input",
            "anchor_input",
            "production_inputs_opened",
        }
        or inputs["first_estimates_input"]
        != configuration.get("first_estimates_input")
        or inputs["anchor_input"] != configuration.get("anchor_input")
        or inputs["production_inputs_opened"] is not False
    ):
        raise ValueError("registered input identity evidence changed")
    anchor_context_publication._assert_exact_json(
        inputs["first_estimates_input"],
        configuration["first_estimates_input"],
        "prelaunch first-estimates identity",
    )
    anchor_context_publication._assert_exact_json(
        inputs["anchor_input"],
        configuration["anchor_input"],
        "prelaunch anchor identity",
    )

    outputs = evidence_by_name[PRELAUNCH_CHECK_NAMES[3]]
    expected_absence = [
        {"path": registry.PRIMARY_OUTPUT_PATH, "absent": True},
        {"path": registry.SIDECAR_OUTPUT_PATH, "absent": True},
    ]
    history = outputs.get("incident_history")
    if (
        set(outputs)
        != {"output_absence", "incident_history", "next_incident_index"}
        or outputs["output_absence"] != expected_absence
        or not isinstance(history, list)
        or any(not isinstance(path, str) for path in history)
        or outputs["next_incident_index"] != next_index
        or next_index != len(history) + 1
    ):
        raise ValueError("output and incident-contiguity evidence changed")
    anchor_context_publication._assert_exact_json(
        outputs["output_absence"],
        expected_absence,
        "prelaunch output absence",
    )
    anchor_context_publication._assert_exact_json(
        outputs["next_incident_index"],
        next_index,
        "prelaunch next incident index",
    )
    for position, path in enumerate(history, start=1):
        if path != f"runs/anchor_context_report_incident_{position}.json":
            raise ValueError("prelaunch incident history is not contiguous")

    invocation = evidence_by_name[PRELAUNCH_CHECK_NAMES[4]]
    registered_invocation = invocation.get("registered_invocation")
    actual_invocation = invocation.get("actual_invocation")
    if (
        set(invocation)
        != {
            "registered_invocation",
            "actual_invocation",
            "byte_match",
            "isolated_interpreter_verified",
        }
        or not isinstance(registered_invocation, list)
        or not registered_invocation
        or any(
            not isinstance(argument, str) or not argument
            for argument in registered_invocation
        )
        or actual_invocation != registered_invocation
        or registered_invocation != configuration.get("invocation")
        or invocation["byte_match"] is not True
        or invocation["isolated_interpreter_verified"] is not True
    ):
        raise ValueError("isolated invocation evidence changed")
    anchor_context_publication._assert_exact_json(
        actual_invocation,
        registered_invocation,
        "prelaunch actual invocation",
    )
    anchor_context_publication._assert_exact_json(
        registered_invocation,
        configuration["invocation"],
        "prelaunch registered invocation",
    )

    execution = evidence_by_name[PRELAUNCH_CHECK_NAMES[5]]
    if (
        set(execution) != {"execution_rule", "acknowledged"}
        or execution["execution_rule"] != execution_rule
        or execution["acknowledged"] is not True
    ):
        raise ValueError("execution-law evidence changed")
    anchor_context_publication._assert_exact_json(
        execution["execution_rule"],
        execution_rule,
        "prelaunch execution rule",
    )
    return value


def _prelaunch_record_validator_protocol(
    implementation: Callable[..., Mapping[str, Any]],
    canonical_execution_rule_bytes: bytes,
) -> Callable[[object], Mapping[str, Any]]:
    frozen = bytes(canonical_execution_rule_bytes)
    json_loads = json.loads
    mapping_type = Mapping

    def validate(candidate: object) -> Mapping[str, Any]:
        execution_rule = json_loads(frozen)
        if not isinstance(execution_rule, mapping_type):
            raise AssertionError("private execution law is not a mapping")
        return implementation(
            candidate,
            execution_rule=execution_rule,
        )

    return validate


_validate_prelaunch_record_value = _prelaunch_record_validator_protocol(
    _validate_prelaunch_record_value_impl,
    _VALIDATION_EXECUTION_RULE_BYTES,
)
del _VALIDATION_EXECUTION_RULE_BYTES
del _validate_prelaunch_record_value_impl
del _prelaunch_record_validator_protocol


def _prelaunch_record_value(
    record: _PrelaunchRecord,
) -> Mapping[str, Any]:
    if not isinstance(record, _PrelaunchRecord):
        raise TypeError("prelaunch record has the wrong type")
    if not isinstance(record.evidence_bytes, bytes):
        raise TypeError("prelaunch evidence must be immutable bytes")
    try:
        value = json.loads(record.evidence_bytes)
        canonical = anchor_context_publication.canonical_json_bytes(value)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError("prelaunch evidence is not canonical JSON") from error
    validated = _validate_prelaunch_record_value(value)
    if (
        canonical != record.evidence_bytes
        or record.check_names != PRELAUNCH_CHECK_NAMES
        or validated["configuration_sha256"] != record.configuration_sha256
        or validated["next_incident_index"] != record.next_incident_index
    ):
        raise ValueError("prelaunch in-memory and canonical evidence differ")
    return validated


@dataclass
class _InitialAttemptState:
    token: _InitialAttemptAuthority
    registration: first_publication._RegisteredConfigurationToken
    prelaunch_record: _PrelaunchRecord
    production_only: bool
    attempt_claim: Path
    attempt_payload: bytes
    attempt_file_id: tuple[int, int]
    authority_path: Path
    authority_file_id: tuple[int, int]
    authority_nonce: str
    authority_descriptor: int


def _retry_authority_protocol():
    """Issue only live initial/retry tokens backed by durable exact evidence."""
    getframe = sys._getframe
    initial_issued: dict[int, _InitialAttemptState] = {}
    sealed_core_code: Any = None
    sealed_abort_code: Any = None

    class RetryAuthorityVault:
        """Hide receipt and retry-token identity registries behind bound methods."""

        __slots__ = (
            "_abort",
            "_authorizations",
            "_authorize",
            "_consume_receipt_bound",
            "_core",
            "_getframe",
            "_incident_max_bytes",
            "_issue_authorization_bound",
            "_issue_receipt_bound",
            "_mapping_proxy_type",
            "_protocol_bound",
            "_read_attempt_claim",
            "_read_canonical_mapping",
            "_read_retry_authority",
            "_receipts",
            "_receipt_type",
            "_retry_type",
            "_seal",
            "_stack_bound",
        )

        def __getattribute__(self, _name: str) -> Any:
            raise AttributeError("retry authority state is sealed")

        def __setattr__(self, _name: str, _value: Any) -> None:
            raise TypeError("retry authority state is sealed")

        def bind_protocol(
            self,
            seal: Callable[..., Any],
            authorize: Callable[..., Any],
            issue_receipt_bound: Callable[..., Any],
            consume_receipt_bound: Callable[..., Any],
            issue_authorization_bound: Callable[..., Any],
        ) -> None:
            if object.__getattribute__(self, "_protocol_bound"):
                raise RuntimeError("retry authority protocol is already bound")
            object.__setattr__(self, "_seal", seal)
            object.__setattr__(self, "_authorize", authorize)
            object.__setattr__(
                self,
                "_issue_receipt_bound",
                issue_receipt_bound,
            )
            object.__setattr__(
                self,
                "_consume_receipt_bound",
                consume_receipt_bound,
            )
            object.__setattr__(
                self,
                "_issue_authorization_bound",
                issue_authorization_bound,
            )
            object.__setattr__(self, "_protocol_bound", True)

        def bind_stack(
            self,
            core: Callable[..., Any],
            abort: Callable[..., Any],
        ) -> None:
            if object.__getattribute__(self, "_stack_bound"):
                raise RuntimeError("retry authority stack is already sealed")
            object.__setattr__(self, "_core", core)
            object.__setattr__(self, "_abort", abort)
            object.__setattr__(self, "_stack_bound", True)

        def issue_receipt(
            self,
            receipt: object,
            initial_token: object,
            repository_root: Path,
            registration_reference: str,
            configuration_sha256: str,
            incident_index: int,
            incident_path: Path,
            incident_payload: bytes,
            incident_file_id: tuple[int, int],
            incident_phase: str,
            incident_reason: str,
            estimate_bearing_information_yielded: bool,
            attempt_claim: Path,
            attempt_payload: bytes,
            attempt_file_id: tuple[int, int],
            authority_path: Path,
            authority_payload: bytes,
            authority_file_id: tuple[int, int],
            production_only: bool,
        ) -> None:
            caller = object.__getattribute__(self, "_getframe")(1)
            abort_frame = caller.f_back
            core_frame = (
                abort_frame.f_back if abort_frame is not None else None
            )
            seal = object.__getattribute__(self, "_seal")
            abort = object.__getattribute__(self, "_abort")
            core = object.__getattribute__(self, "_core")
            if (
                not object.__getattribute__(self, "_protocol_bound")
                or not object.__getattribute__(self, "_stack_bound")
                or caller.f_code is not seal.__code__
                or caller.f_locals.get("issue_receipt")
                is not object.__getattribute__(self, "_issue_receipt_bound")
                or caller.f_locals.get("receipt") is not receipt
                or abort_frame is None
                or abort_frame.f_code is not abort.__code__
                or abort_frame.f_locals.get("seal_retry_authority") is not seal
                or abort_frame.f_locals.get("attempt_authority")
                is not initial_token
                or core_frame is None
                or core_frame.f_code is not core.__code__
                or core_frame.f_locals.get("publish_abort") is not abort
                or core_frame.f_locals.get("seal_retry_authority") is not seal
                or core_frame.f_locals.get("initial_attempt_authority")
                is not initial_token
                or not isinstance(
                    receipt,
                    object.__getattribute__(self, "_receipt_type"),
                )
            ):
                raise TypeError(
                    "retry receipt issuance requires the exact published "
                    "coordinator incident stack"
                )
            object.__getattribute__(self, "_receipts")[id(receipt)] = (
                receipt,
                repository_root,
                registration_reference,
                configuration_sha256,
                incident_index,
                incident_path,
                incident_payload,
                incident_file_id,
                incident_phase,
                incident_reason,
                estimate_bearing_information_yielded,
                attempt_claim,
                attempt_payload,
                attempt_file_id,
                authority_path,
                authority_payload,
                authority_file_id,
                production_only,
            )

        def consume_receipt(self, receipt: object) -> tuple[Any, ...] | None:
            caller = object.__getattribute__(self, "_getframe")(1)
            core_frame = caller.f_back
            authorize = object.__getattribute__(self, "_authorize")
            core = object.__getattribute__(self, "_core")
            if (
                not object.__getattribute__(self, "_protocol_bound")
                or not object.__getattribute__(self, "_stack_bound")
                or caller.f_code is not authorize.__code__
                or caller.f_locals.get("consume_receipt")
                is not object.__getattribute__(self, "_consume_receipt_bound")
                or caller.f_locals.get("retry_receipt") is not receipt
                or core_frame is None
                or core_frame.f_code is not core.__code__
                or core_frame.f_locals.get("authorize_invocation")
                is not authorize
                or core_frame.f_locals.get("retry_receipt") is not receipt
            ):
                raise TypeError(
                    "retry receipt consumption requires the exact "
                    "coordinator adjudication stack"
                )
            state = object.__getattribute__(self, "_receipts").pop(
                id(receipt),
                None,
            )
            if (
                state is None
                or state[0] is not receipt
                or not isinstance(
                    receipt,
                    object.__getattribute__(self, "_receipt_type"),
                )
            ):
                return None
            return state

        def issue_authorization(
            self,
            token: object,
            repository_root: Path,
            registration_reference: str,
            configuration_sha256: str,
            incident_index: int,
            incident_path: Path,
            incident_payload: bytes,
            incident_file_id: tuple[int, int],
            attempt_claim: Path,
            attempt_payload: bytes,
            attempt_file_id: tuple[int, int],
            authority_path: Path,
            authority_payload: bytes,
            authority_file_id: tuple[int, int],
        ) -> None:
            caller = object.__getattribute__(self, "_getframe")(1)
            core_frame = caller.f_back
            authorize = object.__getattribute__(self, "_authorize")
            core = object.__getattribute__(self, "_core")
            if (
                not object.__getattribute__(self, "_protocol_bound")
                or not object.__getattribute__(self, "_stack_bound")
                or caller.f_code is not authorize.__code__
                or caller.f_locals.get("issue_authorization")
                is not object.__getattribute__(
                    self,
                    "_issue_authorization_bound",
                )
                or caller.f_locals.get("token") is not token
                or core_frame is None
                or core_frame.f_code is not core.__code__
                or core_frame.f_locals.get("authorize_invocation")
                is not authorize
                or not isinstance(
                    token,
                    object.__getattribute__(self, "_retry_type"),
                )
            ):
                raise TypeError(
                    "retry authorization issuance requires exact "
                    "coordinator adjudication"
                )
            object.__getattribute__(self, "_authorizations")[id(token)] = (
                token,
                repository_root,
                registration_reference,
                configuration_sha256,
                incident_index,
                incident_path,
                incident_payload,
                incident_file_id,
                attempt_claim,
                attempt_payload,
                attempt_file_id,
                authority_path,
                authority_payload,
                authority_file_id,
            )

        def require_authorization(
            self,
            token: object,
            repository_root: Path,
        ) -> Mapping[str, Any]:
            state = object.__getattribute__(self, "_authorizations").get(
                id(token)
            )
            if (
                state is None
                or state[0] is not token
                or not isinstance(
                    token,
                    object.__getattribute__(self, "_retry_type"),
                )
                or state[1] != repository_root
            ):
                raise TypeError(
                    "retry requires live authenticated authorization"
                )
            attempt = object.__getattribute__(
                self,
                "_read_attempt_claim",
            )(state[8])
            authority = object.__getattribute__(
                self,
                "_read_retry_authority",
            )(state[11])
            incident = object.__getattribute__(
                self,
                "_read_canonical_mapping",
            )(
                state[5],
                maximum_bytes=object.__getattribute__(
                    self,
                    "_incident_max_bytes",
                ),
                expected_name=state[5].name,
            )
            if (
                attempt is None
                or attempt[1] != state[9]
                or attempt[2] != state[10]
                or authority is None
                or authority[1] != state[12]
                or authority[2] != state[13]
                or incident is None
                or incident[1] != state[6]
                or incident[2] != state[7]
            ):
                raise TypeError("authenticated retry evidence changed")
            return object.__getattribute__(self, "_mapping_proxy_type")(
                {
                    "repository_root": state[1],
                    "registration_reference": state[2],
                    "configuration_sha256": state[3],
                    "incident_index": state[4],
                    "incident_path": state[5],
                    "incident_payload": state[6],
                    "incident_file_id": state[7],
                    "attempt_claim": state[8],
                    "attempt_payload": state[9],
                    "attempt_file_id": state[10],
                    "authority_path": state[11],
                    "authority_payload": state[12],
                    "authority_file_id": state[13],
                }
            )

        def revoke_authorization(self, token: object) -> None:
            state = object.__getattribute__(self, "_authorizations").get(
                id(token)
            )
            if state is not None and state[0] is token:
                object.__getattribute__(self, "_authorizations").pop(
                    id(token),
                    None,
                )

    vault = object.__new__(RetryAuthorityVault)
    object.__setattr__(vault, "_abort", None)
    object.__setattr__(vault, "_authorizations", {})
    object.__setattr__(vault, "_authorize", None)
    object.__setattr__(vault, "_core", None)
    object.__setattr__(vault, "_getframe", getframe)
    object.__setattr__(vault, "_incident_max_bytes", _INCIDENT_MAX_BYTES)
    object.__setattr__(vault, "_mapping_proxy_type", MappingProxyType)
    object.__setattr__(vault, "_protocol_bound", False)
    object.__setattr__(vault, "_read_attempt_claim", _read_attempt_claim)
    object.__setattr__(
        vault,
        "_read_canonical_mapping",
        _read_canonical_mapping,
    )
    object.__setattr__(vault, "_read_retry_authority", _read_retry_authority)
    object.__setattr__(vault, "_receipts", {})
    object.__setattr__(vault, "_receipt_type", _RetryReceipt)
    object.__setattr__(vault, "_retry_type", _RetryAuthorization)
    object.__setattr__(vault, "_seal", None)
    object.__setattr__(vault, "_stack_bound", False)
    bind_vault_stack = object.__getattribute__(vault, "bind_stack")
    bind_vault_protocol = object.__getattribute__(vault, "bind_protocol")
    issue_receipt = object.__getattribute__(vault, "issue_receipt")
    consume_receipt = object.__getattribute__(vault, "consume_receipt")
    issue_authorization = object.__getattribute__(
        vault,
        "issue_authorization",
    )
    require_retry = object.__getattribute__(vault, "require_authorization")
    revoke_retry = object.__getattribute__(vault, "revoke_authorization")

    def bind_stack(
        core: Callable[..., Any], abort: Callable[..., Any]
    ) -> None:
        nonlocal sealed_core_code, sealed_abort_code
        if sealed_core_code is not None or sealed_abort_code is not None:
            raise RuntimeError("retry authority stack is already sealed")
        sealed_core_code = core.__code__
        sealed_abort_code = abort.__code__
        bind_vault_stack(core, abort)

    def issue_initial(
        registration: first_publication._RegisteredConfigurationToken,
        prelaunch_record: _PrelaunchRecord,
        production_only: bool,
    ) -> _InitialAttemptAuthority:
        caller = getframe(1)
        if (
            caller.f_code is not sealed_core_code
            or caller.f_locals.get("registration") is not registration
            or caller.f_locals.get("prelaunch_record") is not prelaunch_record
            or caller.f_locals.get("production_only") is not production_only
            or caller.f_locals.get("issue_initial_attempt")
            is not issue_initial
        ):
            raise TypeError(
                "initial-attempt authority can be issued only on the sealed "
                "coordinator stack"
            )
        if not isinstance(
            registration,
            first_publication._RegisteredConfigurationToken,
        ) or not isinstance(prelaunch_record, _PrelaunchRecord):
            raise TypeError("initial attempt requires registration and checks")
        root = registration._repository_root
        runs = first_coordinator._sealed_runs_directory(root)
        attempt_claim = runs / _ATTEMPT_CLAIM_PATH.name
        retry_claim = runs / _RETRY_CLAIM_PATH.name
        authority_path = runs / _RETRY_AUTHORITY_PATH.name
        if os.path.lexists(attempt_claim):
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
            )
        if os.path.lexists(retry_claim):
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_retry_claim",
                (
                    "The durable anchor-context retry claim is already "
                    "occupied; the sole retry is consumed."
                ),
            )
        if os.path.lexists(authority_path):
            raise _CeremonyAbort(
                "preparation_retry_authority_path_occupied",
                (
                    "The durable anchor-context retry-authority path is "
                    "already occupied without authenticated history."
                ),
            )
        try:
            authority_descriptor = os.open(
                authority_path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o400,
            )
        except FileExistsError:
            raise _CeremonyAbort(
                "preparation_retry_authority_path_occupied",
                "The durable retry-authority reservation is occupied.",
            ) from None
        authority_metadata = os.fstat(authority_descriptor)
        authority_file_id = (
            authority_metadata.st_dev,
            authority_metadata.st_ino,
        )
        authority_nonce = secrets.token_hex(32)
        attempt_payload = _attempt_claim_payload(
            registration_reference=registration._registration_reference,
            configuration_sha256=prelaunch_record.configuration_sha256,
            next_incident_index=prelaunch_record.next_incident_index,
            authority_file_id=authority_file_id,
            authority_nonce_sha256=hashlib.sha256(
                authority_nonce.encode("ascii")
            ).hexdigest(),
            prelaunch_record=prelaunch_record,
        )
        try:
            _write_claim(attempt_claim, attempt_payload)
        except FileExistsError:
            os.close(authority_descriptor)
            raise _CeremonyAbort(
                (
                    "preparation_fresh_registration_adjudication_required_"
                    "attempt_claim"
                ),
                "The durable anchor-context attempt claim became occupied.",
            ) from None
        attempt_metadata = os.stat(attempt_claim, follow_symlinks=False)
        token = object.__new__(_InitialAttemptAuthority)
        object.__setattr__(token, "attempt_claim", attempt_claim)
        state = _InitialAttemptState(
            token=token,
            registration=registration,
            prelaunch_record=prelaunch_record,
            production_only=production_only,
            attempt_claim=attempt_claim,
            attempt_payload=attempt_payload,
            attempt_file_id=(
                attempt_metadata.st_dev,
                attempt_metadata.st_ino,
            ),
            authority_path=authority_path,
            authority_file_id=authority_file_id,
            authority_nonce=authority_nonce,
            authority_descriptor=authority_descriptor,
        )
        initial_issued[id(token)] = state
        return token

    def require_initial(
        token: object,
        registration: first_publication._RegisteredConfigurationToken,
        prelaunch_record: _PrelaunchRecord,
    ) -> Path:
        state = initial_issued.get(id(token))
        if (
            state is None
            or state.token is not token
            or not isinstance(token, _InitialAttemptAuthority)
            or state.registration is not registration
            or state.prelaunch_record is not prelaunch_record
        ):
            raise TypeError("initial-attempt authority is not live")
        current_claim = _read_attempt_claim(state.attempt_claim)
        try:
            authority_metadata = os.fstat(state.authority_descriptor)
        except OSError as error:
            raise TypeError(
                "retry-authority reservation is not live"
            ) from error
        current_prelaunch = _prelaunch_record_value(prelaunch_record)
        if (
            current_claim is None
            or current_claim[1] != state.attempt_payload
            or current_claim[2] != state.attempt_file_id
            or current_claim[0]["prelaunch_record"] != current_prelaunch
            or (
                authority_metadata.st_dev,
                authority_metadata.st_ino,
            )
            != state.authority_file_id
            or authority_metadata.st_size != 0
            or not stat.S_ISREG(authority_metadata.st_mode)
            or authority_metadata.st_nlink != 1
        ):
            raise TypeError("initial-attempt durable state changed")
        return state.attempt_claim

    def seal(
        token: object,
        incident_path: Path,
        *,
        phase: str,
        reason: str,
        estimate_bearing_information_yielded: bool,
    ) -> _RetryReceipt:
        caller = getframe(1)
        state = initial_issued.get(id(token))
        if (
            state is None
            or state.token is not token
            or not isinstance(token, _InitialAttemptAuthority)
            or caller.f_code is not sealed_abort_code
            or caller.f_locals.get("attempt_authority") is not token
        ):
            raise TypeError(
                "retry authority can be sealed only by the live coordinator"
            )
        if (
            phase not in {"preparation", "compute"}
            or not reason.startswith("external_")
            or estimate_bearing_information_yielded is not False
        ):
            raise TypeError("failure is not eligible for retry authority")
        expected_relative = (
            "runs/anchor_context_report_incident_"
            f"{state.prelaunch_record.next_incident_index}.json"
        )
        expected_path = state.registration._repository_root / expected_relative
        if Path(incident_path) != expected_path:
            raise RuntimeError("incident writer returned a noncanonical path")
        configuration = first_publication._configuration_echo(
            state.registration
        )
        incident, incident_payload, incident_file_id = (
            anchor_context_publication._validate_anchor_context_incident_file(
                path=expected_path,
                expected_configuration_echo=configuration,
                repository_root=state.registration._repository_root,
                production_only=state.production_only,
            )
        )
        if (
            incident.get("incident_index")
            != state.prelaunch_record.next_incident_index
            or incident.get("phase") != phase
            or incident.get("reason") != reason
            or incident.get("configuration_echo") != configuration
            or not anchor_context_publication.incident_is_retry_eligible(
                incident
            )
        ):
            raise RuntimeError(
                "published incident does not authenticate the caught failure"
            )
        current_claim = _read_attempt_claim(state.attempt_claim)
        authority_metadata = os.fstat(state.authority_descriptor)
        if (
            current_claim is None
            or current_claim[1] != state.attempt_payload
            or current_claim[2] != state.attempt_file_id
            or (
                authority_metadata.st_dev,
                authority_metadata.st_ino,
            )
            != state.authority_file_id
            or authority_metadata.st_size != 0
        ):
            raise RuntimeError("attempt or retry-authority state changed")
        authority_payload = _retry_authority_payload(
            registration_reference=state.registration._registration_reference,
            configuration_sha256=state.prelaunch_record.configuration_sha256,
            attempt_claim_sha256=hashlib.sha256(
                state.attempt_payload
            ).hexdigest(),
            authority_nonce=state.authority_nonce,
            incident_index=state.prelaunch_record.next_incident_index,
            incident_path=expected_relative,
            incident_sha256=hashlib.sha256(incident_payload).hexdigest(),
        )
        first_coordinator._write_attempt_claim_payload(
            state.authority_descriptor,
            authority_payload,
        )
        os.fsync(state.authority_descriptor)
        os.fchmod(state.authority_descriptor, 0o444)
        os.close(state.authority_descriptor)
        state.authority_descriptor = -1
        directory = os.open(
            state.authority_path.parent,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        sealed = _read_retry_authority(state.authority_path)
        if (
            sealed is None
            or sealed[1] != authority_payload
            or sealed[2] != state.authority_file_id
        ):
            raise RuntimeError("retry authority did not seal durably")
        receipt = object.__new__(_RetryReceipt)
        issue_receipt(
            receipt,
            token,
            state.registration._repository_root,
            state.registration._registration_reference,
            state.prelaunch_record.configuration_sha256,
            state.prelaunch_record.next_incident_index,
            expected_path,
            incident_payload,
            incident_file_id,
            phase,
            reason,
            False,
            state.attempt_claim,
            state.attempt_payload,
            state.attempt_file_id,
            state.authority_path,
            authority_payload,
            state.authority_file_id,
            state.production_only,
        )
        return receipt

    def revoke_initial(token: object) -> None:
        state = initial_issued.get(id(token))
        if state is None or state.token is not token:
            return
        initial_issued.pop(id(token), None)
        if state.authority_descriptor >= 0:
            os.close(state.authority_descriptor)
            state.authority_descriptor = -1

    def authorize(
        repository_root: Path,
        configuration: Mapping[str, Any],
        history: _IncidentHistory,
        retry_receipt: _RetryReceipt | None,
        production_only: bool,
    ) -> _RetryAuthorization | None:
        """Allow fresh execution or mint the sole authenticated retry."""
        caller = getframe(1)
        if (
            caller.f_code is not sealed_core_code
            or caller.f_locals.get("authorize_invocation") is not authorize
            or caller.f_locals.get("retry_receipt") is not retry_receipt
            or caller.f_locals.get("production_only") is not production_only
        ):
            raise TypeError(
                "retry adjudication requires the sealed coordinator stack"
            )
        current = []
        expected_bytes = anchor_context_publication.canonical_json_bytes(
            configuration
        )
        configuration_sha256 = hashlib.sha256(expected_bytes).hexdigest()
        for position, record in enumerate(history.records):
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
                    (
                        "preparation_fresh_registration_required_"
                        "configuration_drift"
                    ),
                    "This registration reference already has different bytes.",
                )
            current.append(
                (
                    record,
                    history.paths[position],
                    history.payloads[position],
                    history.file_ids[position],
                )
            )
        if not current:
            if retry_receipt is not None:
                raise _CeremonyAbort(
                    "preparation_retry_receipt_without_prior_incident",
                    "A retry receipt cannot authorize an initial attempt.",
                )
            return None
        if len(current) != 1:
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_second_failure",
                "This registration already has a second failure.",
            )
        incident, incident_relative, incident_payload, incident_file_id = (
            current[0]
        )
        if not anchor_context_publication.incident_is_retry_eligible(incident):
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_nonretryable_incident",
                "The prior incident is not retry-eligible.",
            )
        retry_claim = repository_root / _RETRY_CLAIM_PATH
        if os.path.lexists(retry_claim):
            raise _CeremonyAbort(
                "preparation_fresh_registration_required_retry_claim",
                (
                    "The durable anchor-context retry claim is already "
                    "occupied; the sole retry is consumed."
                ),
            )
        attempt_claim = repository_root / _ATTEMPT_CLAIM_PATH
        authority_path = repository_root / _RETRY_AUTHORITY_PATH
        attempt_loaded = _read_attempt_claim(attempt_claim)
        authority_loaded = _read_retry_authority(authority_path)
        if attempt_loaded is None or authority_loaded is None:
            raise _CeremonyAbort(
                "preparation_retry_authority_missing_or_invalid",
                (
                    "The prior incident has no authenticated initial-attempt "
                    "and no-yield provenance."
                ),
            )
        attempt, attempt_payload, attempt_file_id = attempt_loaded
        authority, authority_payload, authority_file_id = authority_loaded
        incident_index = incident["incident_index"]
        commitment = hashlib.sha256(
            authority["authority_nonce"].encode("ascii")
        ).hexdigest()
        if (
            attempt["registration_reference"]
            != configuration["registration_reference"]
            or attempt["configuration_sha256"] != configuration_sha256
            or attempt["next_incident_index"] != incident_index
            or attempt["authority_device"] != authority_file_id[0]
            or attempt["authority_inode"] != authority_file_id[1]
            or not hmac.compare_digest(
                attempt["authority_nonce_sha256"],
                commitment,
            )
            or authority["registration_reference"]
            != configuration["registration_reference"]
            or authority["configuration_sha256"] != configuration_sha256
            or authority["attempt_claim_sha256"]
            != hashlib.sha256(attempt_payload).hexdigest()
            or authority["incident_index"] != incident_index
            or authority["incident_path"] != incident_relative
            or authority["incident_sha256"]
            != hashlib.sha256(incident_payload).hexdigest()
            or authority["estimate_bearing_information_yielded"] is not False
        ):
            raise _CeremonyAbort(
                "preparation_retry_authority_mismatch",
                (
                    "The retry authority does not authenticate the exact "
                    "attempt, incident, configuration, and no-yield state."
                ),
            )
        receipt_state = consume_receipt(retry_receipt)
        if (
            receipt_state is None
            or receipt_state[0] is not retry_receipt
            or receipt_state[1] != repository_root
            or receipt_state[2] != configuration["registration_reference"]
            or receipt_state[3] != configuration_sha256
            or receipt_state[4] != incident_index
            or receipt_state[5] != repository_root / incident_relative
            or receipt_state[6] != incident_payload
            or receipt_state[7] != incident_file_id
            or receipt_state[8] != incident["phase"]
            or receipt_state[9] != incident["reason"]
            or receipt_state[10] is not False
            or receipt_state[11] != attempt_claim
            or receipt_state[12] != attempt_payload
            or receipt_state[13] != attempt_file_id
            or receipt_state[14] != authority_path
            or receipt_state[15] != authority_payload
            or receipt_state[16] != authority_file_id
            or receipt_state[17] is not production_only
        ):
            raise _CeremonyAbort(
                "preparation_retry_provenance_not_coordinator_published",
                (
                    "The retry evidence was not retained from this "
                    "coordinator's own incident publication."
                ),
            )
        token = object.__new__(_RetryAuthorization)
        object.__setattr__(token, "incident_index", incident_index)
        issue_authorization(
            token,
            repository_root,
            configuration["registration_reference"],
            configuration_sha256,
            incident_index,
            repository_root / incident_relative,
            incident_payload,
            incident_file_id,
            attempt_claim,
            attempt_payload,
            attempt_file_id,
            authority_path,
            authority_payload,
            authority_file_id,
        )
        return token

    bind_vault_protocol(
        seal,
        authorize,
        issue_receipt,
        consume_receipt,
        issue_authorization,
    )

    return (
        bind_stack,
        issue_initial,
        require_initial,
        seal,
        revoke_initial,
        authorize,
        require_retry,
        revoke_retry,
    )


(
    _bind_retry_authority_stack,
    _issue_initial_attempt,
    _require_initial_attempt,
    _seal_retry_authority,
    _revoke_initial_attempt,
    _authorize_invocation,
    _require_retry_authorization,
    _revoke_retry_authorization,
) = _retry_authority_protocol()
del _retry_authority_protocol


def _retry_claim_protocol(
    require_authorization: Callable[[object, Path], Any],
) -> Callable[[Path, object, _PrelaunchRecord], Path]:
    def create(
        repository_root: Path,
        authorization: object,
        prelaunch_record: _PrelaunchRecord,
    ) -> Path:
        """Consume the one retry only from live authenticated evidence."""
        state = require_authorization(authorization, repository_root)
        path = repository_root / _RETRY_CLAIM_PATH
        payload = _retry_claim_payload(
            registration_reference=state["registration_reference"],
            retry_after_incident=state["incident_index"],
            retry_authority_sha256=hashlib.sha256(
                state["authority_payload"]
            ).hexdigest(),
            prelaunch_record=prelaunch_record,
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

    return create


_create_retry_claim = _retry_claim_protocol(_require_retry_authorization)
del _retry_claim_protocol


def _ceremony_capability_protocol(
    core_factory: Callable[
        [Callable[..., None]],
        Callable[..., _CoordinatorAttemptOutcome],
    ],
    bind_capability_verifier: Callable[[Callable[..., Any]], None],
):
    """Expose only the sealed runner and live-capability verifier."""
    getframe = sys._getframe
    sealed_repository_root = _sealed_repository_root()
    exclusive_ceremony_lock = first_coordinator._exclusive_ceremony_lock
    read_registered_configuration_bytes = _read_registered_configuration_bytes
    bind_retry_authority_stack = _bind_retry_authority_stack
    issue_initial_attempt = _issue_initial_attempt
    require_initial_attempt = _require_initial_attempt
    seal_retry_authority = _seal_retry_authority
    revoke_initial_attempt = _revoke_initial_attempt
    authorize_invocation = _authorize_invocation
    create_retry_claim = _create_retry_claim
    require_retry_authorization = _require_retry_authorization
    revoke_retry_authorization = _revoke_retry_authorization
    write_artifact = anchor_context_publication.write_anchor_context_artifact

    def publish_artifact(
        token: anchor_context_publication._AnchorContextPrecomputeToken,
        artifact: Mapping[str, Any],
        *,
        input_bundle: object,
        ceremony_capability: _CeremonyCapability,
    ) -> Path:
        return write_artifact(
            token,
            artifact,
            input_bundle=input_bundle,
            ceremony_capability=ceremony_capability,
        )

    production_operations = _CoordinatorOperations(
        assert_interpreter=_assert_sealed_interpreter,
        validate_repository=_validate_repository,
        prepare_sidecar=(
            anchor_context_publication.prepare_environment_sidecar
        ),
        load_inputs=(anchor_context_publication._load_production_documents),
        build_results=anchor_context_report._build_production_results,
        validate_results=(anchor_context_report._validate_production_results),
        build_runtime_provenance=(
            anchor_context_publication.build_runtime_provenance
        ),
        build_artifact=(
            anchor_context_publication.build_anchor_context_artifact
        ),
        publish_artifact=publish_artifact,
        publish_incident=(
            anchor_context_publication.write_anchor_context_incident
        ),
        record_prelaunch=_retain_prelaunch_record,
    )
    operation_fields = tuple(_CoordinatorOperations.__dataclass_fields__)
    sealed_operation_identities = tuple(
        (
            getattr(production_operations, field),
            getattr(
                getattr(production_operations, field),
                "__code__",
                None,
            ),
        )
        for field in operation_fields
    )
    production_input_verifier = (
        anchor_context_publication._require_verified_production_inputs
    )
    production_input_verifier_code = production_input_verifier.__code__
    invocations: dict[int, tuple[Any, ...]] = {}
    issued: dict[int, tuple[Any, ...]] = {}

    def operations_are_exact(candidate: object) -> bool:
        return candidate is production_operations and all(
            getattr(candidate, field, None) is expected
            and getattr(expected, "__code__", None) is expected_code
            for field, (expected, expected_code) in zip(
                operation_fields,
                sealed_operation_identities,
                strict=True,
            )
        )

    def runner_frame_dependencies_are_exact(frame: Any) -> bool:
        """Pin every closure dependency that can enter the production core."""
        local = frame.f_locals
        return bool(
            frame.f_code is run.__code__
            and local.get("run_function") is run
            and local.get("run") is run
            and local.get("require_runner_provenance")
            is require_runner_provenance
            and local.get("sealed_repository_root") is sealed_repository_root
            and local.get("exclusive_ceremony_lock") is exclusive_ceremony_lock
            and local.get("read_registered_configuration_bytes")
            is read_registered_configuration_bytes
            and local.get("production_operations") is production_operations
            and local.get("core") is core
            and local.get("issue_invocation") is issue_invocation
            and local.get("revoke_invocation") is revoke_invocation
            and local.get("mint") is mint
            and local.get("revoke") is revoke
            and local.get("issue_initial_attempt") is issue_initial_attempt
            and local.get("require_initial_attempt") is require_initial_attempt
            and local.get("seal_retry_authority") is seal_retry_authority
            and local.get("revoke_initial_attempt") is revoke_initial_attempt
            and local.get("authorize_invocation") is authorize_invocation
            and local.get("create_retry_claim") is create_retry_claim
            and local.get("require_retry_authorization")
            is require_retry_authorization
            and local.get("revoke_retry_authorization")
            is revoke_retry_authorization
            and operations_are_exact(production_operations)
        )

    def require_runner_provenance(run_function: object) -> None:
        """Reject cloned runner code before it can acquire the ceremony lock."""
        caller = getframe(1)
        if (
            not runner_frame_dependencies_are_exact(caller)
            or run_function is not run
        ):
            raise TypeError("production runner provenance changed")

    def issue_invocation(
        repository_root: Path,
        registered_configuration_bytes: bytes,
        actual_invocation: Sequence[str],
        operations: _CoordinatorOperations,
        retry_receipt: _RetryReceipt | None,
    ) -> _CoordinatorInvocation:
        caller = getframe(1)
        if (
            not runner_frame_dependencies_are_exact(caller)
            or caller.f_locals.get("root") is not repository_root
            or caller.f_locals.get("registered_configuration_bytes")
            is not registered_configuration_bytes
            or caller.f_locals.get("actual_invocation")
            is not actual_invocation
            or caller.f_locals.get("operations") is not operations
            or caller.f_locals.get("retry_receipt") is not retry_receipt
        ):
            raise TypeError(
                "production invocation authority requires the sealed "
                "runner stack"
            )
        if (
            not isinstance(repository_root, Path)
            or not isinstance(registered_configuration_bytes, bytes)
            or repository_root is not sealed_repository_root
            or not operations_are_exact(operations)
        ):
            raise TypeError("production invocation prerequisites changed")
        invocation = object.__new__(_CoordinatorInvocation)
        invocations[id(invocation)] = (
            invocation,
            repository_root,
            registered_configuration_bytes,
            actual_invocation,
            tuple(actual_invocation),
            operations,
            retry_receipt,
            caller,
            run,
        )
        return invocation

    def require_invocation(
        invocation: object,
        repository_root: str | Path,
        registered_configuration_bytes: bytes,
        actual_invocation: Sequence[str],
        operations: _CoordinatorOperations,
        retry_receipt: _RetryReceipt | None,
    ) -> None:
        caller = getframe(1)
        parent = caller.f_back
        state = invocations.get(id(invocation))
        if (
            state is None
            or state[0] is not invocation
            or not isinstance(invocation, _CoordinatorInvocation)
            or caller.f_code is not core.__code__
            or parent is None
            or not runner_frame_dependencies_are_exact(parent)
            or caller.f_locals.get("coordinator_invocation") is not invocation
            or caller.f_locals.get("production_only") is not True
        ):
            raise TypeError(
                "production execution requires a sealed production invocation"
            )
        (
            _,
            issued_root,
            issued_configuration,
            issued_actual_invocation,
            frozen_actual_invocation,
            issued_operations,
            issued_retry_receipt,
            issued_run_frame,
            issued_run_function,
        ) = state
        if (
            repository_root is not issued_root
            or registered_configuration_bytes is not issued_configuration
            or actual_invocation is not issued_actual_invocation
            or tuple(actual_invocation) != frozen_actual_invocation
            or operations is not issued_operations
            or retry_receipt is not issued_retry_receipt
            or parent is not issued_run_frame
            or issued_run_function is not run
            or issued_root is not sealed_repository_root
            or not operations_are_exact(issued_operations)
        ):
            raise TypeError("sealed production invocation state changed")

    def revoke_invocation(invocation: object) -> None:
        state = invocations.get(id(invocation))
        if state is not None and state[0] is invocation:
            invocations.pop(id(invocation), None)

    def mint(
        registration: first_publication._RegisteredConfigurationToken,
        prelaunch_record: _PrelaunchRecord,
        attempt_claim: Path,
        initial_attempt_authority: _InitialAttemptAuthority | None,
        retry_authorization: _RetryAuthorization | None,
        retry_claim: Path | None,
    ) -> _CeremonyCapability:
        caller = getframe(1)
        parent = caller.f_back
        invocation = caller.f_locals.get("coordinator_invocation")
        invocation_state = invocations.get(id(invocation))
        if (
            caller.f_code is not core.__code__
            or parent is None
            or parent.f_code is not run.__code__
            or caller.f_locals.get("mint_capability") is not mint
            or caller.f_locals.get("production_only") is not True
            or caller.f_locals.get("registration") is not registration
            or caller.f_locals.get("prelaunch_record") is not prelaunch_record
            or caller.f_locals.get("attempt_claim") != attempt_claim
            or caller.f_locals.get("initial_attempt_authority")
            is not initial_attempt_authority
            or caller.f_locals.get("retry_authorization")
            is not retry_authorization
            or caller.f_locals.get("retry_claim") != retry_claim
            or caller.f_locals.get("operations") is not production_operations
            or caller.f_locals.get("root") is not sealed_repository_root
            or invocation_state is None
            or invocation_state[0] is not invocation
            or invocation_state[-2] is not parent
            or invocation_state[-1] is not run
            or not runner_frame_dependencies_are_exact(parent)
            or not operations_are_exact(production_operations)
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
        claim_loaded = _read_attempt_claim(attempt_claim)
        if (
            claim_loaded is None
            or claim_loaded[0].get("registration_reference")
            != registration._registration_reference
            or claim_loaded[0].get("configuration_sha256")
            != prelaunch_record.configuration_sha256
        ):
            raise RuntimeError(
                "ceremony capability requires its canonical attempt claim"
            )
        claim_payload = claim_loaded[1]
        claim_file_id = claim_loaded[2]
        if (initial_attempt_authority is None) == (
            retry_authorization is None
        ):
            raise TypeError(
                "ceremony capability requires exactly one attempt authority"
            )
        retry_payload: bytes | None = None
        retry_file_id: tuple[int, int] | None = None
        if initial_attempt_authority is not None:
            if retry_claim is not None:
                raise TypeError("initial execution cannot have a retry claim")
            if (
                require_initial_attempt(
                    initial_attempt_authority,
                    registration,
                    prelaunch_record,
                )
                != attempt_claim
            ):
                raise TypeError("initial attempt authority changed")
        else:
            retry_state = require_retry_authorization(
                retry_authorization,
                registration._repository_root,
            )
            if (
                retry_state["attempt_claim"] != attempt_claim
                or retry_claim
                != registration._repository_root / _RETRY_CLAIM_PATH
            ):
                raise TypeError("retry ceremony claim identity changed")
            retry_loaded = _read_retry_claim(retry_claim)
            expected_retry_payload = _retry_claim_payload(
                registration_reference=retry_state["registration_reference"],
                retry_after_incident=retry_state["incident_index"],
                retry_authority_sha256=hashlib.sha256(
                    retry_state["authority_payload"]
                ).hexdigest(),
                prelaunch_record=prelaunch_record,
            )
            if (
                retry_loaded is None
                or retry_loaded[1] != expected_retry_payload
            ):
                raise TypeError("retry claim is not authority-bound")
            retry_payload = retry_loaded[1]
            retry_file_id = retry_loaded[2]
        capability = object.__new__(_CeremonyCapability)
        object.__setattr__(capability, "registration", registration)
        object.__setattr__(
            capability,
            "prelaunch_record",
            prelaunch_record,
        )
        object.__setattr__(capability, "attempt_claim", attempt_claim)
        object.__setattr__(capability, "retry_claim", retry_claim)
        issued[id(capability)] = (
            capability,
            registration,
            prelaunch_record,
            attempt_claim,
            claim_payload,
            claim_file_id,
            initial_attempt_authority,
            retry_authorization,
            retry_claim,
            retry_payload,
            retry_file_id,
            caller,
            parent,
            invocation,
        )
        return capability

    def has_live_execution_stack(
        capability: _CeremonyCapability,
        *,
        registration: first_publication._RegisteredConfigurationToken,
        record: _PrelaunchRecord,
        attempt_claim: Path,
        initial_attempt_authority: _InitialAttemptAuthority | None,
        retry_authorization: _RetryAuthorization | None,
        retry_claim: Path | None,
        core_frame: Any,
        run_frame: Any,
        invocation: object,
    ) -> bool:
        """Require the exact active run, core, and current operation frames."""
        core_local = core_frame.f_locals
        invocation_state = invocations.get(id(invocation))
        if (
            core_frame.f_code is not core.__code__
            or core_frame.f_back is not run_frame
            or not runner_frame_dependencies_are_exact(run_frame)
            or invocation_state is None
            or invocation_state[0] is not invocation
            or invocation_state[-2] is not run_frame
            or invocation_state[-1] is not run
            or core_local.get("require_coordinator_invocation")
            is not require_invocation
            or core_local.get("coordinator_invocation") is not invocation
            or core_local.get("production_only") is not True
            or core_local.get("root") is not sealed_repository_root
            or core_local.get("operations") is not production_operations
            or core_local.get("registration") is not registration
            or core_local.get("prelaunch_record") is not record
            or core_local.get("attempt_claim") != attempt_claim
            or core_local.get("initial_attempt_authority")
            is not initial_attempt_authority
            or core_local.get("retry_authorization") is not retry_authorization
            or core_local.get("retry_claim") != retry_claim
            or core_local.get("ceremony_capability") is not capability
            or core_local.get("execution_authority") is not capability
            or core_local.get("mint_capability") is not mint
            or core_local.get("revoke_capability") is not revoke
            or core_local.get("issue_initial_attempt")
            is not issue_initial_attempt
            or core_local.get("require_initial_attempt")
            is not require_initial_attempt
            or core_local.get("seal_retry_authority")
            is not seal_retry_authority
            or core_local.get("revoke_initial_attempt")
            is not revoke_initial_attempt
            or core_local.get("authorize_invocation")
            is not authorize_invocation
            or core_local.get("create_retry_claim") is not create_retry_claim
            or core_local.get("require_retry_authorization")
            is not require_retry_authorization
            or core_local.get("revoke_retry_authorization")
            is not revoke_retry_authorization
            or not operations_are_exact(production_operations)
            or run_frame.f_locals.get("coordinator_invocation")
            is not invocation
            or run_frame.f_locals.get("root") is not sealed_repository_root
            or run_frame.f_locals.get("operations")
            is not production_operations
            or run_frame.f_locals.get("registered_configuration_bytes")
            is not invocation_state[2]
            or run_frame.f_locals.get("actual_invocation")
            is not invocation_state[3]
            or run_frame.f_locals.get("retry_receipt")
            is not invocation_state[6]
        ):
            return False

        operation_frame = None
        frame = getframe(2)
        while frame is not None and frame is not core_frame:
            if frame.f_back is core_frame:
                operation_frame = frame
                break
            frame = frame.f_back
        if operation_frame is None:
            return False
        allowed_codes = (
            production_operations.load_inputs.__code__,
            production_input_verifier_code,
            production_operations.build_results.__code__,
            production_operations.validate_results.__code__,
            production_operations.build_artifact.__code__,
            production_operations.publish_artifact.__code__,
        )
        operation_locals = operation_frame.f_locals
        keyword_arguments = operation_locals.get("kwargs")
        return bool(
            operation_frame.f_code in allowed_codes
            and (
                any(value is capability for value in operation_locals.values())
                or (
                    isinstance(keyword_arguments, Mapping)
                    and keyword_arguments.get("ceremony_capability")
                    is capability
                )
            )
        )

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
            initial_attempt_authority,
            retry_authorization,
            retry_claim,
            retry_payload,
            retry_file_id,
            core_frame,
            run_frame,
            invocation,
        ) = state
        if not has_live_execution_stack(
            capability,
            registration=registration,
            record=record,
            attempt_claim=attempt_claim,
            initial_attempt_authority=initial_attempt_authority,
            retry_authorization=retry_authorization,
            retry_claim=retry_claim,
            core_frame=core_frame,
            run_frame=run_frame,
            invocation=invocation,
        ):
            raise TypeError(
                "production operation requires the active sealed ceremony stack"
            )
        current_claim = _read_attempt_claim(attempt_claim)
        if (
            capability.registration is not registration
            or capability.prelaunch_record is not record
            or capability.attempt_claim != attempt_claim
            or capability.retry_claim != retry_claim
            or current_claim is None
            or current_claim[1] != claim_payload
            or current_claim[2] != claim_file_id
        ):
            raise TypeError("ceremony capability state changed")
        if initial_attempt_authority is not None:
            require_initial_attempt(
                initial_attempt_authority,
                registration,
                record,
            )
        else:
            require_retry_authorization(
                retry_authorization,
                registration._repository_root,
            )
            current_retry = (
                _read_retry_claim(retry_claim)
                if retry_claim is not None
                else None
            )
            if (
                current_retry is None
                or current_retry[1] != retry_payload
                or current_retry[2] != retry_file_id
            ):
                raise TypeError("ceremony retry claim changed")
        return registration

    def revoke(capability: object) -> None:
        state = issued.get(id(capability))
        if state is not None and state[0] is capability:
            issued.pop(id(capability), None)

    def run(registration_path: str | Path) -> CoordinatorResult:
        run_function = run
        require_runner_provenance(run_function)
        root = sealed_repository_root
        actual_invocation = list(getattr(sys, "orig_argv", ()))
        with exclusive_ceremony_lock(root):
            registered_configuration_bytes = (
                read_registered_configuration_bytes(
                    root,
                    registration_path,
                )
            )
            operations = production_operations
            retry_receipt: _RetryReceipt | None = None
            for attempt_index in range(2):
                coordinator_invocation = issue_invocation(
                    root,
                    registered_configuration_bytes,
                    actual_invocation,
                    operations,
                    retry_receipt,
                )
                try:
                    outcome = core(
                        repository_root=root,
                        registered_configuration_bytes=(
                            registered_configuration_bytes
                        ),
                        actual_invocation=actual_invocation,
                        operations=operations,
                        production_only=True,
                        coordinator_invocation=coordinator_invocation,
                        retry_receipt=retry_receipt,
                        mint_capability=mint,
                        revoke_capability=revoke,
                        issue_initial_attempt=issue_initial_attempt,
                        require_initial_attempt=require_initial_attempt,
                        seal_retry_authority=seal_retry_authority,
                        revoke_initial_attempt=revoke_initial_attempt,
                        authorize_invocation=authorize_invocation,
                        create_retry_claim=create_retry_claim,
                        require_retry_authorization=(
                            require_retry_authorization
                        ),
                        revoke_retry_authorization=(
                            revoke_retry_authorization
                        ),
                    )
                finally:
                    revoke_invocation(coordinator_invocation)
                if attempt_index == 0 and outcome.retry_receipt is not None:
                    retry_receipt = outcome.retry_receipt
                    continue
                return outcome.result
            raise AssertionError("coordinator retry loop did not terminate")

    run.__name__ = "run_registered_anchor_context"
    run.__qualname__ = "run_registered_anchor_context"
    run.__doc__ = (
        "Run the production ceremony through the sealed registration gate."
    )
    core = core_factory(require_invocation)
    bind_retry_authority_stack(core, _publish_abort)
    bind_capability_verifier(require)
    return run, require_invocation, core


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
    implementation_commit = configuration["implementation_commit"]
    try:
        _git_bytes(
            root,
            "rev-parse",
            "--verify",
            f"{implementation_commit}^{{commit}}",
        )
        _git_bytes(
            root,
            "merge-base",
            "--is-ancestor",
            implementation_commit,
            "HEAD",
        )
        implementation_trees = tuple(
            _git_bytes(
                root,
                "rev-parse",
                f"{implementation_commit}:{code_root}",
            )
            for code_root in ("src", "scripts")
        )
        head_trees = tuple(
            _git_bytes(root, "rev-parse", f"HEAD:{code_root}")
            for code_root in ("src", "scripts")
        )
    except _CeremonyAbort as error:
        raise _CeremonyAbort(
            "preparation_implementation_commit_drift",
            (
                "The registered implementation commit must exist, be an "
                "ancestor of HEAD, and identify both code roots."
            ),
        ) from error
    if implementation_trees != head_trees:
        raise _CeremonyAbort(
            "preparation_implementation_commit_drift",
            (
                "Checkout code trees differ from the registered "
                "implementation commit."
            ),
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
    payloads = []
    file_ids = []
    for index, path in indexed:
        try:
            record, raw, file_id = (
                anchor_context_publication._validate_anchor_context_incident_file(
                    path=path,
                    expected_configuration_echo=None,
                    repository_root=repository_root,
                    production_only=production_only,
                )
            )
        except (OSError, TypeError, ValueError) as error:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                (
                    f"Incident {index} is not a canonical, singly-linked "
                    "bounded JSON object."
                ),
            ) from error
        paths.append(path.relative_to(repository_root).as_posix())
        records.append(record)
        payloads.append(raw)
        file_ids.append(file_id)
    return _IncidentHistory(
        paths=tuple(paths),
        records=tuple(records),
        payloads=tuple(payloads),
        file_ids=tuple(file_ids),
    )


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


def _complete_prelaunch_checks_impl(
    *,
    repository_root: Path,
    configuration: Mapping[str, Any],
    actual_invocation: Sequence[str],
    history: _IncidentHistory,
    operations: _CoordinatorOperations,
    execution_rule: Mapping[str, Any],
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
        execution_rule["publishes_regardless"] is not True
        or execution_rule["no_self_rescue"] is not True
    ):
        raise AssertionError("canonical execution acknowledgement changed")
    configuration_bytes = anchor_context_publication.canonical_json_bytes(
        configuration
    )
    configuration_sha256 = hashlib.sha256(configuration_bytes).hexdigest()
    next_incident_index = len(history.paths) + 1
    evidence = {
        "schema_version": _PRELAUNCH_RECORD_SCHEMA,
        "registration_reference": configuration["registration_reference"],
        "configuration_sha256": configuration_sha256,
        "next_incident_index": next_incident_index,
        "checks": [
            {
                "name": PRELAUNCH_CHECK_NAMES[0],
                "passed": True,
                "evidence": {
                    "design": configuration["design"],
                    "implementation_commit": configuration[
                        "implementation_commit"
                    ],
                    "production_input_io_before_launch": False,
                },
            },
            {
                "name": PRELAUNCH_CHECK_NAMES[1],
                "passed": True,
                "evidence": {
                    "registration_reference": configuration[
                        "registration_reference"
                    ],
                    "registered_configuration": json.loads(
                        configuration_bytes
                    ),
                    "registered_configuration_sha256": configuration_sha256,
                    "registered_configuration_byte_length": len(
                        configuration_bytes
                    ),
                },
            },
            {
                "name": PRELAUNCH_CHECK_NAMES[2],
                "passed": True,
                "evidence": {
                    "first_estimates_input": configuration[
                        "first_estimates_input"
                    ],
                    "anchor_input": configuration["anchor_input"],
                    "production_inputs_opened": False,
                },
            },
            {
                "name": PRELAUNCH_CHECK_NAMES[3],
                "passed": True,
                "evidence": {
                    "output_absence": [
                        {
                            "path": registry.PRIMARY_OUTPUT_PATH,
                            "absent": True,
                        },
                        {
                            "path": registry.SIDECAR_OUTPUT_PATH,
                            "absent": True,
                        },
                    ],
                    "incident_history": list(history.paths),
                    "next_incident_index": next_incident_index,
                },
            },
            {
                "name": PRELAUNCH_CHECK_NAMES[4],
                "passed": True,
                "evidence": {
                    "registered_invocation": list(configuration["invocation"]),
                    "actual_invocation": list(actual_invocation),
                    "byte_match": True,
                    "isolated_interpreter_verified": True,
                },
            },
            {
                "name": PRELAUNCH_CHECK_NAMES[5],
                "passed": True,
                "evidence": {
                    "execution_rule": execution_rule,
                    "acknowledged": True,
                },
            },
        ],
    }
    evidence_bytes = anchor_context_publication.canonical_json_bytes(evidence)
    record = _PrelaunchRecord(
        check_names=PRELAUNCH_CHECK_NAMES,
        configuration_sha256=configuration_sha256,
        next_incident_index=next_incident_index,
        evidence_bytes=evidence_bytes,
    )
    _prelaunch_record_value(record)
    return record


def _prelaunch_completion_protocol(
    implementation: Callable[..., _PrelaunchRecord],
    canonical_execution_rule_bytes: bytes,
) -> Callable[..., _PrelaunchRecord]:
    frozen = bytes(canonical_execution_rule_bytes)
    json_loads = json.loads
    mapping_type = Mapping

    def complete(
        *,
        repository_root: Path,
        configuration: Mapping[str, Any],
        actual_invocation: Sequence[str],
        history: _IncidentHistory,
        operations: _CoordinatorOperations,
    ) -> _PrelaunchRecord:
        execution_rule = json_loads(frozen)
        if not isinstance(execution_rule, mapping_type):
            raise AssertionError("private execution law is not a mapping")
        return implementation(
            repository_root=repository_root,
            configuration=configuration,
            actual_invocation=actual_invocation,
            history=history,
            operations=operations,
            execution_rule=execution_rule,
        )

    return complete


_complete_prelaunch_checks = _prelaunch_completion_protocol(
    _complete_prelaunch_checks_impl,
    _COMPLETION_EXECUTION_RULE_BYTES,
)
del _COMPLETION_EXECUTION_RULE_BYTES
del _complete_prelaunch_checks_impl
del _prelaunch_completion_protocol


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
    attempt_authority: _InitialAttemptAuthority | None,
    seal_retry_authority: Callable[..., _RetryReceipt],
) -> _CoordinatorAttemptOutcome:
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
    retry_receipt: _RetryReceipt | None = None
    if (
        attempt_authority is not None
        and isinstance(error, ExternalPreOutputFailure)
        and phase in {"preparation", "compute"}
        and estimate_bearing_information_yielded is False
    ):
        retry_receipt = seal_retry_authority(
            attempt_authority,
            path,
            phase=phase,
            reason=reason,
            estimate_bearing_information_yielded=False,
        )
    result = CoordinatorResult(
        status="incident",
        path=path,
        phase=phase,
        reason=reason,
    )
    outcome = object.__new__(_CoordinatorAttemptOutcome)
    object.__setattr__(outcome, "result", result)
    object.__setattr__(outcome, "retry_receipt", retry_receipt)
    return outcome


def _build_registered_anchor_context_core(
    require_coordinator_invocation: Callable[..., None],
) -> Callable[..., _CoordinatorAttemptOutcome]:
    parse_configuration = _parse_configuration
    configuration_echo = first_publication._configuration_echo
    read_incident_history = _read_incident_history
    assert_fixture_identities = (
        anchor_context_publication._assert_fixture_identities
    )
    complete_prelaunch_checks = _complete_prelaunch_checks
    prelaunch_check_names = PRELAUNCH_CHECK_NAMES
    read_retry_claim = _read_retry_claim
    retry_claim_payload = _retry_claim_payload
    freeze_precompute = anchor_context_publication._freeze_precompute
    require_production_inputs = (
        anchor_context_publication._require_verified_production_inputs
    )
    require_fixture_inputs = (
        anchor_context_publication._require_verified_fixture_inputs
    )
    publish_abort = _publish_abort
    result_type = CoordinatorResult

    def core(
        *,
        repository_root: str | Path,
        registered_configuration_bytes: bytes,
        actual_invocation: Sequence[str],
        operations: _CoordinatorOperations,
        production_only: bool,
        coordinator_invocation: _CoordinatorInvocation | None,
        retry_receipt: _RetryReceipt | None,
        mint_capability: (
            Callable[
                [
                    first_publication._RegisteredConfigurationToken,
                    _PrelaunchRecord,
                    Path,
                    _InitialAttemptAuthority | None,
                    _RetryAuthorization | None,
                    Path | None,
                ],
                _CeremonyCapability,
            ]
            | None
        ),
        revoke_capability: Callable[[object], None] | None,
        issue_initial_attempt: Callable[
            [
                first_publication._RegisteredConfigurationToken,
                _PrelaunchRecord,
                bool,
            ],
            _InitialAttemptAuthority,
        ],
        require_initial_attempt: Callable[
            [
                object,
                first_publication._RegisteredConfigurationToken,
                _PrelaunchRecord,
            ],
            Path,
        ],
        seal_retry_authority: Callable[..., _RetryReceipt],
        revoke_initial_attempt: Callable[[object], None],
        authorize_invocation: Callable[
            [
                Path,
                Mapping[str, Any],
                _IncidentHistory,
                _RetryReceipt | None,
                bool,
            ],
            _RetryAuthorization | None,
        ],
        create_retry_claim: Callable[
            [Path, object, _PrelaunchRecord],
            Path,
        ],
        require_retry_authorization: Callable[
            [object, Path],
            Any,
        ],
        revoke_retry_authorization: Callable[[object], None],
    ) -> _CoordinatorAttemptOutcome:
        """Shared ceremony state machine; only the sealed closure can mint."""
        if production_only:
            require_coordinator_invocation(
                coordinator_invocation,
                repository_root,
                registered_configuration_bytes,
                actual_invocation,
                operations,
                retry_receipt,
            )
        elif coordinator_invocation is not None:
            raise TypeError(
                "fixture execution cannot use production invocation"
            )
        if production_only != (mint_capability is not None):
            raise TypeError("production execution requires the sealed issuer")
        if (mint_capability is None) != (revoke_capability is None):
            raise TypeError("ceremony capability lifecycle is incomplete")
        root = (
            repository_root
            if production_only and isinstance(repository_root, Path)
            else Path(repository_root).resolve()
        )
        registration = parse_configuration(
            repository_root=root,
            registered_configuration_bytes=registered_configuration_bytes,
            production_only=production_only,
        )
        configuration = configuration_echo(registration)
        precompute: (
            anchor_context_publication._AnchorContextPrecomputeToken | None
        ) = None
        ceremony_capability: _CeremonyCapability | None = None
        initial_attempt_authority: _InitialAttemptAuthority | None = None
        retry_authorization: _RetryAuthorization | None = None
        retry_claim: Path | None = None
        try:
            try:
                history = read_incident_history(
                    root,
                    production_only=production_only,
                )
                retry_authorization = authorize_invocation(
                    root,
                    configuration,
                    history,
                    retry_receipt,
                    production_only,
                )
                if not production_only:
                    assert_fixture_identities(
                        configuration["first_estimates_input"],
                        configuration["anchor_input"],
                    )
                prelaunch_record = complete_prelaunch_checks(
                    repository_root=root,
                    configuration=configuration,
                    actual_invocation=actual_invocation,
                    history=history,
                    operations=operations,
                )
                if prelaunch_record.check_names != prelaunch_check_names:
                    raise AssertionError("prelaunch check record changed")
                if retry_authorization is None:
                    initial_attempt_authority = issue_initial_attempt(
                        registration,
                        prelaunch_record,
                        production_only,
                    )
                    attempt_claim = initial_attempt_authority.attempt_claim
                else:
                    attempt_claim = root / _ATTEMPT_CLAIM_PATH
                    retry_claim = create_retry_claim(
                        root,
                        retry_authorization,
                        prelaunch_record,
                    )
                operations.record_prelaunch(prelaunch_record)
                if initial_attempt_authority is not None:
                    if (
                        require_initial_attempt(
                            initial_attempt_authority,
                            registration,
                            prelaunch_record,
                        )
                        != attempt_claim
                    ):
                        raise TypeError(
                            "initial prelaunch claim identity changed"
                        )
                else:
                    retry_state = require_retry_authorization(
                        retry_authorization,
                        root,
                    )
                    retry_loaded = (
                        read_retry_claim(retry_claim)
                        if retry_claim is not None
                        else None
                    )
                    expected_retry_payload = retry_claim_payload(
                        registration_reference=retry_state[
                            "registration_reference"
                        ],
                        retry_after_incident=retry_state["incident_index"],
                        retry_authority_sha256=hashlib.sha256(
                            retry_state["authority_payload"]
                        ).hexdigest(),
                        prelaunch_record=prelaunch_record,
                    )
                    if (
                        retry_loaded is None
                        or retry_loaded[1] != expected_retry_payload
                    ):
                        raise TypeError("retry prelaunch claim changed")
                execution_authority: object = registration
                if mint_capability is not None:
                    ceremony_capability = mint_capability(
                        registration,
                        prelaunch_record,
                        attempt_claim,
                        initial_attempt_authority,
                        retry_authorization,
                        retry_claim,
                    )
                    execution_authority = ceremony_capability
                sidecar_payload, reported_sidecar_hash = (
                    operations.prepare_sidecar(root)
                )
                runtime_provenance = operations.build_runtime_provenance(
                    configuration["implementation_commit"]
                )
                precompute = freeze_precompute(
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
                    require_production_inputs(
                        loaded_inputs,
                        ceremony_capability=ceremony_capability,
                    )
                else:
                    require_fixture_inputs(loaded_inputs)
            except BaseException as error:
                return publish_abort(
                    precompute or registration,
                    phase="preparation",
                    error=error,
                    estimate_bearing_information_yielded=False,
                    operations=operations,
                    attempt_authority=initial_attempt_authority,
                    seal_retry_authority=seal_retry_authority,
                )

            operations.after_preparation()
            try:
                results = operations.build_results(
                    execution_authority,
                    loaded_inputs,
                )
            except BaseException as error:
                return publish_abort(
                    precompute,
                    phase="compute",
                    error=error,
                    estimate_bearing_information_yielded=False,
                    operations=operations,
                    attempt_authority=initial_attempt_authority,
                    seal_retry_authority=seal_retry_authority,
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
                return publish_abort(
                    precompute,
                    phase="invariant",
                    error=error,
                    estimate_bearing_information_yielded=(
                        estimate_bearing_information_yielded
                    ),
                    operations=operations,
                    attempt_authority=initial_attempt_authority,
                    seal_retry_authority=seal_retry_authority,
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
                return publish_abort(
                    precompute,
                    phase="publication",
                    error=error,
                    estimate_bearing_information_yielded=True,
                    operations=operations,
                    attempt_authority=initial_attempt_authority,
                    seal_retry_authority=seal_retry_authority,
                )
            result = result_type(
                status="published",
                path=path,
                phase="publication",
                reason=None,
            )
            outcome = object.__new__(_CoordinatorAttemptOutcome)
            object.__setattr__(outcome, "result", result)
            object.__setattr__(outcome, "retry_receipt", None)
            return outcome
        finally:
            if (
                ceremony_capability is not None
                and revoke_capability is not None
            ):
                revoke_capability(ceremony_capability)
            if initial_attempt_authority is not None:
                revoke_initial_attempt(initial_attempt_authority)
            if retry_authorization is not None:
                revoke_retry_authorization(retry_authorization)

    core.__name__ = "_run_registered_anchor_context_core"
    core.__qualname__ = "_run_registered_anchor_context_core"
    return core


def _run_registered_anchor_context_for_test(
    *,
    repository_root: str | Path,
    registered_configuration_bytes: bytes,
    actual_invocation: Sequence[str],
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    """Run only the fixed-fixture ceremony with injectable test operations."""
    outcome = _run_registered_anchor_context_core(
        repository_root=repository_root,
        registered_configuration_bytes=registered_configuration_bytes,
        actual_invocation=actual_invocation,
        operations=operations,
        production_only=False,
        coordinator_invocation=None,
        retry_receipt=None,
        mint_capability=None,
        revoke_capability=None,
        issue_initial_attempt=_issue_initial_attempt,
        require_initial_attempt=_require_initial_attempt,
        seal_retry_authority=_seal_retry_authority,
        revoke_initial_attempt=_revoke_initial_attempt,
        authorize_invocation=_authorize_invocation,
        create_retry_claim=_create_retry_claim,
        require_retry_authorization=_require_retry_authorization,
        revoke_retry_authorization=_revoke_retry_authorization,
    )
    return outcome.result


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
    directory_chain: list[
        tuple[int, os.stat_result, int | None, str | Path]
    ] = []
    registration_descriptor: int | None = None
    stable_fields = (
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_dev",
        "st_ino",
    )

    def signature(metadata: os.stat_result) -> tuple[int, ...]:
        return tuple(getattr(metadata, field) for field in stable_fields)

    try:
        root_before = os.stat(root, follow_symlinks=False)
        if not stat.S_ISDIR(root_before.st_mode):
            raise ValueError("repository root is not a regular directory")
        root_descriptor = os.open(
            root,
            os.O_RDONLY | directory_flag | no_follow | close_on_exec,
        )
        descriptors.append(root_descriptor)
        root_opened = os.fstat(root_descriptor)
        if signature(root_opened) != signature(root_before):
            raise ValueError("repository root changed before its sealed open")
        directory_chain.append((root_descriptor, root_opened, None, root))
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
            parent_descriptor = current
            component_before = os.stat(
                component,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISLNK(component_before.st_mode):
                raise OSError(
                    "registration path component must not be a symbolic link"
                )
            if not stat.S_ISDIR(component_before.st_mode):
                raise ValueError(
                    "registration path component is not a directory"
                )
            current = os.open(
                component,
                os.O_RDONLY | directory_flag | no_follow | close_on_exec,
                dir_fd=parent_descriptor,
            )
            descriptors.append(current)
            component_opened = os.fstat(current)
            if signature(component_opened) != signature(component_before):
                raise ValueError(
                    "registration directory changed before its sealed open"
                )
            directory_chain.append(
                (
                    current,
                    component_opened,
                    parent_descriptor,
                    component,
                )
            )
        leaf_before = os.stat(
            parts[2],
            dir_fd=current,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(leaf_before.st_mode):
            raise OSError("registration leaf must not be a symbolic link")
        if (
            not stat.S_ISREG(leaf_before.st_mode)
            or leaf_before.st_nlink != 1
            or leaf_before.st_size > _REGISTRATION_MAX_BYTES
        ):
            raise ValueError(
                "registration must be one singly linked bounded regular file"
            )
        if (leaf_before.st_dev, leaf_before.st_ino) in protected_file_ids:
            raise ValueError(
                "registration path aliases protected ceremony data"
            )
        registration_descriptor = os.open(
            parts[2],
            os.O_RDONLY | no_follow | nonblocking | close_on_exec,
            dir_fd=current,
        )
        before = os.fstat(registration_descriptor)
        if (before.st_dev, before.st_ino) in protected_file_ids:
            raise ValueError(
                "registration path aliases protected ceremony data"
            )
        if (
            signature(before) != signature(leaf_before)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > _REGISTRATION_MAX_BYTES
        ):
            raise ValueError(
                "registration must be one singly linked bounded regular file"
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
        named_after = os.stat(
            parts[2],
            dir_fd=current,
            follow_symlinks=False,
        )
        if (
            len(payload) != before.st_size
            or signature(after) != signature(before)
            or signature(named_after) != signature(before)
        ):
            raise ValueError("registration changed during its sealed read")
        for descriptor, opened, parent, name in directory_chain:
            descriptor_after = os.fstat(descriptor)
            if parent is None:
                name_after = os.stat(name, follow_symlinks=False)
            else:
                name_after = os.stat(
                    name,
                    dir_fd=parent,
                    follow_symlinks=False,
                )
            if signature(descriptor_after) != signature(opened) or signature(
                name_after
            ) != signature(opened):
                raise ValueError(
                    "registration path chain changed during its sealed read"
                )
        return payload
    finally:
        if registration_descriptor is not None:
            os.close(registration_descriptor)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


(
    run_registered_anchor_context,
    _require_coordinator_invocation,
    _run_registered_anchor_context_core,
) = _ceremony_capability_protocol(
    _build_registered_anchor_context_core,
    _bind_coordinator_capability_verifier,
)
del _bind_coordinator_capability_verifier
del _build_registered_anchor_context_core
del _ceremony_capability_protocol


__all__ = [
    "CANONICAL_EXECUTION_RULE",
    "CoordinatorResult",
    "ExternalPreOutputFailure",
    "PRELAUNCH_CHECK_NAMES",
    "run_registered_anchor_context",
]
