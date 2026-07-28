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
_ATTEMPT_CLAIM_SCHEMA = "anchor_context_report_attempt.v2"
_RETRY_CLAIM_PATH = Path("runs/anchor_context_report_retry.claim")
_RETRY_CLAIM_SCHEMA = "anchor_context_report_retry.v2"
_RETRY_AUTHORITY_PATH = Path(
    "runs/anchor_context_report_retry_authority.claim"
)
_RETRY_AUTHORITY_SCHEMA = "anchor_context_report_retry_authority.v1"
_CLAIM_MAX_BYTES = first_coordinator._ATTEMPT_CLAIM_MAX_BYTES
_INCIDENT_MAX_BYTES = 4 * 1024 * 1024
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
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    """Read one singly-linked canonical mapping through a pinned descriptor."""
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
                or metadata.st_nlink != 1
                or metadata.st_size > maximum_bytes
            ):
                return None
            chunks = bytearray()
            while len(chunks) <= maximum_bytes:
                chunk = os.read(
                    descriptor,
                    maximum_bytes + 1 - len(chunks),
                )
                if not chunk:
                    break
                chunks.extend(chunk)
            if len(chunks) > maximum_bytes:
                return None
            payload = bytes(chunks)
            after = os.fstat(descriptor)
            if (after.st_dev, after.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ) or after.st_size != metadata.st_size:
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
        }
    )


def _read_attempt_claim(
    path: Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    loaded = _read_canonical_mapping(path, maximum_bytes=_CLAIM_MAX_BYTES)
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
    }
    next_index = value.get("next_incident_index")
    authority_device = value.get("authority_device")
    authority_inode = value.get("authority_inode")
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
    loaded = _read_canonical_mapping(path, maximum_bytes=_CLAIM_MAX_BYTES)
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
    return anchor_context_publication.canonical_json_bytes(
        {
            "schema_version": _RETRY_CLAIM_SCHEMA,
            "registration_reference": registration_reference,
            "retry_after_incident": retry_after_incident,
            "retry_authority_sha256": retry_authority_sha256,
        }
    )


def _read_retry_claim(
    path: Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]] | None:
    loaded = _read_canonical_mapping(path, maximum_bytes=_CLAIM_MAX_BYTES)
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
        }
        or value.get("schema_version") != _RETRY_CLAIM_SCHEMA
        or not isinstance(value.get("registration_reference"), str)
        or isinstance(retry_index, bool)
        or not isinstance(retry_index, int)
        or retry_index < 1
        or not _is_sha256(value.get("retry_authority_sha256"))
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


def _retain_prelaunch_record(_record: _PrelaunchRecord) -> None:
    """Production keeps the frozen record in the active call frame."""


@dataclass(frozen=True)
class _PrelaunchRecord:
    """In-memory proof that all six registered checks preceded input load."""

    check_names: tuple[str, ...]
    configuration_sha256: str
    next_incident_index: int


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


@dataclass(frozen=True)
class _RetryAuthorizationState:
    token: _RetryAuthorization
    repository_root: Path
    registration_reference: str
    configuration_sha256: str
    incident_index: int
    incident_path: Path
    incident_payload: bytes
    incident_file_id: tuple[int, int]
    attempt_claim: Path
    attempt_payload: bytes
    attempt_file_id: tuple[int, int]
    authority_path: Path
    authority_payload: bytes
    authority_file_id: tuple[int, int]


def _retry_authority_protocol():
    """Issue only live initial/retry tokens backed by durable exact evidence."""
    getframe = sys._getframe
    initial_issued: dict[int, _InitialAttemptState] = {}
    retry_issued: dict[int, _RetryAuthorizationState] = {}

    def issue_initial(
        registration: first_publication._RegisteredConfigurationToken,
        prelaunch_record: _PrelaunchRecord,
        production_only: bool,
    ) -> _InitialAttemptAuthority:
        caller = getframe(1)
        if (
            caller.f_code is not _run_registered_anchor_context_core.__code__
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
    ) -> Path:
        caller = getframe(1)
        state = initial_issued.get(id(token))
        if (
            state is None
            or state.token is not token
            or not isinstance(token, _InitialAttemptAuthority)
            or caller.f_code is not _publish_abort.__code__
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
        incident_loaded = _read_canonical_mapping(
            expected_path,
            maximum_bytes=_INCIDENT_MAX_BYTES,
        )
        if incident_loaded is None:
            raise RuntimeError("published incident is not canonical on disk")
        incident, incident_payload, _incident_file_id = incident_loaded
        configuration = first_publication._configuration_echo(
            state.registration
        )
        anchor_context_publication._validate_anchor_context_incident(
            incident,
            path=expected_path,
            expected_configuration_echo=configuration,
            repository_root=state.registration._repository_root,
            production_only=state.production_only,
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
        return state.authority_path

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
    ) -> _RetryAuthorization | None:
        """Allow fresh execution or mint the sole authenticated retry."""
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
        token = object.__new__(_RetryAuthorization)
        object.__setattr__(token, "incident_index", incident_index)
        retry_issued[id(token)] = _RetryAuthorizationState(
            token=token,
            repository_root=repository_root,
            registration_reference=configuration["registration_reference"],
            configuration_sha256=configuration_sha256,
            incident_index=incident_index,
            incident_path=repository_root / incident_relative,
            incident_payload=incident_payload,
            incident_file_id=incident_file_id,
            attempt_claim=attempt_claim,
            attempt_payload=attempt_payload,
            attempt_file_id=attempt_file_id,
            authority_path=authority_path,
            authority_payload=authority_payload,
            authority_file_id=authority_file_id,
        )
        return token

    def require_retry(
        token: object,
        repository_root: Path,
    ) -> _RetryAuthorizationState:
        state = retry_issued.get(id(token))
        if (
            state is None
            or state.token is not token
            or not isinstance(token, _RetryAuthorization)
            or state.repository_root != repository_root
        ):
            raise TypeError("retry requires live authenticated authorization")
        attempt = _read_attempt_claim(state.attempt_claim)
        authority = _read_retry_authority(state.authority_path)
        incident = _read_canonical_mapping(
            state.incident_path,
            maximum_bytes=_INCIDENT_MAX_BYTES,
        )
        if (
            attempt is None
            or attempt[1] != state.attempt_payload
            or attempt[2] != state.attempt_file_id
            or authority is None
            or authority[1] != state.authority_payload
            or authority[2] != state.authority_file_id
            or incident is None
            or incident[1] != state.incident_payload
            or incident[2] != state.incident_file_id
        ):
            raise TypeError("authenticated retry evidence changed")
        return state

    def revoke_retry(token: object) -> None:
        state = retry_issued.get(id(token))
        if state is not None and state.token is token:
            retry_issued.pop(id(token), None)

    return (
        issue_initial,
        require_initial,
        seal,
        revoke_initial,
        authorize,
        require_retry,
        revoke_retry,
    )


(
    _issue_initial_attempt,
    _require_initial_attempt,
    _seal_retry_authority,
    _revoke_initial_attempt,
    _authorize_invocation,
    _require_retry_authorization,
    _revoke_retry_authorization,
) = _retry_authority_protocol()


def _create_retry_claim(
    repository_root: Path,
    authorization: object,
    *,
    _require_authorization: Callable[
        [object, Path], _RetryAuthorizationState
    ] = _require_retry_authorization,
) -> Path:
    """Durably consume the one retry only from live authenticated evidence."""
    state = _require_authorization(authorization, repository_root)
    path = repository_root / _RETRY_CLAIM_PATH
    payload = _retry_claim_payload(
        registration_reference=state.registration_reference,
        retry_after_incident=state.incident_index,
        retry_authority_sha256=hashlib.sha256(
            state.authority_payload
        ).hexdigest(),
    )
    try:
        _write_claim(path, payload)
    except FileExistsError:
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_retry_claim",
            (
                "The durable anchor-context retry claim is already occupied; "
                "the sole retry is consumed."
            ),
        ) from None
    return path


def _ceremony_capability_protocol():
    """Expose only the sealed runner and live-capability verifier."""
    getframe = sys._getframe
    issue_initial_attempt = _issue_initial_attempt
    require_initial_attempt = _require_initial_attempt
    seal_retry_authority = _seal_retry_authority
    revoke_initial_attempt = _revoke_initial_attempt
    authorize_invocation = _authorize_invocation
    create_retry_claim = _create_retry_claim
    require_retry_authorization = _require_retry_authorization
    revoke_retry_authorization = _revoke_retry_authorization
    issued: dict[int, tuple[Any, ...]] = {}

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
        if (
            caller.f_code is not _run_registered_anchor_context_core.__code__
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
                retry_state.attempt_claim != attempt_claim
                or retry_claim
                != registration._repository_root / _RETRY_CLAIM_PATH
            ):
                raise TypeError("retry ceremony claim identity changed")
            retry_loaded = _read_retry_claim(retry_claim)
            expected_retry_payload = _retry_claim_payload(
                registration_reference=retry_state.registration_reference,
                retry_after_incident=retry_state.incident_index,
                retry_authority_sha256=hashlib.sha256(
                    retry_state.authority_payload
                ).hexdigest(),
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
            initial_attempt_authority,
            retry_authorization,
            retry_claim,
            retry_payload,
            retry_file_id,
        ) = state
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
                issue_initial_attempt=issue_initial_attempt,
                seal_retry_authority=seal_retry_authority,
                revoke_initial_attempt=revoke_initial_attempt,
                authorize_invocation=authorize_invocation,
                create_retry_claim=create_retry_claim,
                revoke_retry_authorization=revoke_retry_authorization,
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
    payloads = []
    file_ids = []
    for index, path in indexed:
        loaded = _read_canonical_mapping(
            path,
            maximum_bytes=_INCIDENT_MAX_BYTES,
        )
        if loaded is None:
            raise _CeremonyAbort(
                "preparation_incident_history_invalid",
                (
                    f"Incident {index} is not a canonical, singly-linked "
                    "bounded JSON object."
                ),
            )
        record, raw, file_id = loaded
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
    attempt_authority: _InitialAttemptAuthority | None,
    seal_retry_authority: Callable[..., Path],
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
    if (
        attempt_authority is not None
        and isinstance(error, ExternalPreOutputFailure)
        and phase in {"preparation", "compute"}
        and estimate_bearing_information_yielded is False
    ):
        seal_retry_authority(
            attempt_authority,
            path,
            phase=phase,
            reason=reason,
            estimate_bearing_information_yielded=False,
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
    seal_retry_authority: Callable[..., Path],
    revoke_initial_attempt: Callable[[object], None],
    authorize_invocation: Callable[
        [Path, Mapping[str, Any], _IncidentHistory],
        _RetryAuthorization | None,
    ],
    create_retry_claim: Callable[[Path, object], Path],
    revoke_retry_authorization: Callable[[object], None],
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
    initial_attempt_authority: _InitialAttemptAuthority | None = None
    retry_authorization: _RetryAuthorization | None = None
    retry_claim: Path | None = None
    try:
        try:
            history = _read_incident_history(
                root,
                production_only=production_only,
            )
            retry_authorization = authorize_invocation(
                root,
                configuration,
                history,
            )
            if not production_only:
                anchor_context_publication._assert_fixture_identities(
                    configuration["first_estimates_input"],
                    configuration["anchor_input"],
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
            if retry_authorization is None:
                initial_attempt_authority = issue_initial_attempt(
                    registration,
                    prelaunch_record,
                    production_only,
                )
                attempt_claim = initial_attempt_authority.attempt_claim
            else:
                attempt_claim = root / _ATTEMPT_CLAIM_PATH
                retry_claim = create_retry_claim(root, retry_authorization)
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
            return _publish_abort(
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
            return _publish_abort(
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
            return _publish_abort(
                precompute,
                phase="publication",
                error=error,
                estimate_bearing_information_yielded=True,
                operations=operations,
                attempt_authority=initial_attempt_authority,
                seal_retry_authority=seal_retry_authority,
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
        if initial_attempt_authority is not None:
            revoke_initial_attempt(initial_attempt_authority)
        if retry_authorization is not None:
            revoke_retry_authorization(retry_authorization)


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
        issue_initial_attempt=_issue_initial_attempt,
        seal_retry_authority=_seal_retry_authority,
        revoke_initial_attempt=_revoke_initial_attempt,
        authorize_invocation=_authorize_invocation,
        create_retry_claim=_create_retry_claim,
        revoke_retry_authorization=_revoke_retry_authorization,
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
