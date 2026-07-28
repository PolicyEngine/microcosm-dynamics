"""Canonical isolated launcher for the registered anchor-context report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_PRE_IMPORT_REFUSAL_REASON = "preparation_pre_import_guard_refused"
_COORDINATOR_ENTRY_FAILURE_REASON = "preparation_coordinator_entry_failed"
_COORDINATOR_ENTRY_FAILURE_DETAIL = (
    "Coordinator import or entry failed before returning a terminal result."
)
_CONFIGURATION_SCHEMA = "anchor_context_report_configuration.v1"
_INCIDENT_SCHEMA = "anchor_context_report_incident.v1"
_INCIDENT_PREFIX = "anchor_context_report_incident_"
_INCIDENT_FILENAME = re.compile(
    r"anchor_context_report_incident_([1-9]\d*)\.json"
)
_INCIDENT_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z"
)
_INCIDENT_KEYS = {
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
_REGISTRATION_DIRECTORY = Path("docs/registrations")
_REGISTRATION_MAX_BYTES = 1024 * 1024
_INCIDENT_MAX_BYTES = 2 * 1024 * 1024
_PROTECTED_PATHS = (
    Path("runs/first_estimates_v1.json"),
    Path(
        "data/external/"
        "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
    ),
)
_CONFIGURATION_KEYS = {
    "schema_version",
    "registration_reference",
    "design",
    "implementation_commit",
    "invocation",
    "first_estimates_input",
    "anchor_input",
    "required_series_ids",
    "model_metric_specs",
    "pairings",
    "comparison_specs",
}
_DESIGN_BINDING = {
    "path": "docs/design/anchor_context_extraction.md",
    "ratification_commit": "1ad337d3a3eaeba3369a3405469b1e74335e156a",
    "revision": 4,
}
_FIRST_ESTIMATES_INPUT = {
    "path": "runs/first_estimates_v1.json",
    "sha256": "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977",
}
_ANCHOR_INPUT = {
    "path": (
        "data/external/"
        "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
    ),
    "artifact_vintage_id": (
        "ssa_level_anchors.supplement2025_trustees2026.vintage1"
    ),
    "sha256": "adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1",
}
_FROZEN_REGISTRY_SHA256 = {
    "required_series_ids": (
        "52665dd90fc2db4149a641fdd1335758b25133b82311a5b43cfa2a2faae11e2e"
    ),
    "model_metric_specs": (
        "9a584f2109d10c1ce908d6661cb9c1da904521b45ec3a1d5bcf3e62b129eeff0"
    ),
    "pairings": (
        "9773833b9cfe740f1e6e71bb3aae7bc31b040faa8458e942c5b104381b6de412"
    ),
    "comparison_specs": (
        "6a4485fcaf4e741eb0ac05e77ac22ab94cefb0469e1edeba55db4653f71ab1ad"
    ),
}


class _GitVerificationUnavailable(RuntimeError):
    """The pinned checkout could not be authenticated with Git."""


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the registered anchor-context ceremony at its canonical "
            "append-only output paths."
        )
    )
    parser.add_argument(
        "--registration",
        required=True,
        help="Path to the exact canonical registered configuration bytes.",
    )
    return parser.parse_args()


def _git_bytes(repository: Path, *arguments: str) -> bytes:
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
                str(repository),
                f"--git-dir={repository / '.git'}",
                *arguments,
            ],
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise _GitVerificationUnavailable(
            "Git could not verify the pre-import report checkout"
        ) from error


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _validate_bootstrap_configuration(
    configuration: Mapping[str, Any],
) -> None:
    """Exact-check the production echo without importing checkout code."""
    if set(configuration) != _CONFIGURATION_KEYS:
        raise ValueError("registration configuration keys changed")
    if configuration["schema_version"] != _CONFIGURATION_SCHEMA:
        raise ValueError("registration configuration schema changed")
    reference = configuration["registration_reference"]
    if (
        not isinstance(reference, str)
        or not reference
        or len(_canonical_json_bytes(reference)) > 4096
    ):
        raise ValueError("registration reference is invalid")
    if configuration["design"] != _DESIGN_BINDING:
        raise ValueError("registration design binding changed")
    implementation = configuration["implementation_commit"]
    if (
        not isinstance(implementation, str)
        or re.fullmatch(r"[0-9a-f]{40}", implementation) is None
    ):
        raise ValueError("registration implementation commit is invalid")
    invocation = configuration["invocation"]
    if (
        not isinstance(invocation, list)
        or not invocation
        or any(
            not isinstance(argument, str) or not argument
            for argument in invocation
        )
    ):
        raise ValueError("registration invocation is invalid")
    if configuration["first_estimates_input"] != _FIRST_ESTIMATES_INPUT:
        raise ValueError("registration first-estimates identity changed")
    if configuration["anchor_input"] != _ANCHOR_INPUT:
        raise ValueError("registration anchor identity changed")
    for key, expected_digest in _FROZEN_REGISTRY_SHA256.items():
        observed = hashlib.sha256(
            _canonical_json_bytes(configuration[key])
        ).hexdigest()
        if observed != expected_digest:
            raise ValueError(f"registration {key} changed")


def _registration_relative_path(
    repository: Path,
    registration: str | Path,
) -> Path:
    candidate = Path(registration)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(repository)
        except ValueError as error:
            raise ValueError(
                "registration path is outside the checkout"
            ) from error
    else:
        relative = candidate
    if (
        relative in _PROTECTED_PATHS
        or relative.is_absolute()
        or len(relative.parts) != 3
        or relative.parts[:2] != _REGISTRATION_DIRECTORY.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(
            "registration must be one file directly under docs/registrations"
        )
    return relative


def _protected_file_ids(repository: Path) -> set[tuple[int, int]]:
    identities: set[tuple[int, int]] = set()
    for relative in _PROTECTED_PATHS:
        path = repository / relative
        try:
            metadata = os.stat(path, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("protected production input path is not regular")
        identities.add((metadata.st_dev, metadata.st_ino))
    return identities


def _stable_metadata(metadata: os.stat_result) -> tuple[int, ...]:
    """Return fields that must remain fixed across a descriptor read."""
    return (
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_dev,
        metadata.st_ino,
    )


def _read_registered_configuration(
    repository: Path,
    registration: str | Path,
    *,
    permit_unavailable_git: bool = False,
) -> tuple[Mapping[str, Any], bytes]:
    """Gate, pin, bound, authenticate, and then read registration bytes."""
    root = repository.resolve()
    relative = _registration_relative_path(root, registration)
    protected_ids = _protected_file_ids(root)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    root_descriptor = os.open(root, directory_flags)
    docs_descriptor = -1
    registrations_descriptor = -1
    descriptor = -1
    try:
        docs_descriptor = os.open(
            "docs",
            directory_flags,
            dir_fd=root_descriptor,
        )
        registrations_descriptor = os.open(
            "registrations",
            directory_flags,
            dir_fd=docs_descriptor,
        )
        named_before = os.stat(
            relative.name,
            dir_fd=registrations_descriptor,
            follow_symlinks=False,
        )
        named_file_id = (named_before.st_dev, named_before.st_ino)
        if (
            not stat.S_ISREG(named_before.st_mode)
            or named_before.st_nlink != 1
            or named_before.st_size < 1
            or named_before.st_size > _REGISTRATION_MAX_BYTES
            or named_file_id in protected_ids
        ):
            raise ValueError(
                "registration is not a bounded singly-linked regular file"
            )
        descriptor = os.open(
            relative.name,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
            dir_fd=registrations_descriptor,
        )
        metadata = os.fstat(descriptor)
        file_id = (metadata.st_dev, metadata.st_ino)
        if (
            file_id != named_file_id
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > _REGISTRATION_MAX_BYTES
            or file_id in protected_ids
        ):
            raise ValueError(
                "registration is not a bounded singly-linked regular file"
            )
        chunks = bytearray()
        while len(chunks) <= _REGISTRATION_MAX_BYTES:
            chunk = os.read(
                descriptor,
                _REGISTRATION_MAX_BYTES + 1 - len(chunks),
            )
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > _REGISTRATION_MAX_BYTES:
            raise ValueError("registration exceeds its read bound")
        after = os.fstat(descriptor)
        named = os.stat(
            relative.name,
            dir_fd=registrations_descriptor,
            follow_symlinks=False,
        )
        if _stable_metadata(after) != _stable_metadata(
            metadata
        ) or _stable_metadata(named) != _stable_metadata(metadata):
            raise ValueError("registration identity changed during its read")
        payload = bytes(chunks)
    finally:
        for opened in (
            descriptor,
            registrations_descriptor,
            docs_descriptor,
            root_descriptor,
        ):
            if opened >= 0:
                os.close(opened)
    try:
        tracked = _git_bytes(
            root,
            "show",
            f"HEAD:{relative.as_posix()}",
        )
    except _GitVerificationUnavailable:
        if not permit_unavailable_git:
            raise
    else:
        if payload != tracked:
            raise ValueError(
                "registration bytes differ from the committed record"
            )
    try:
        configuration = json.loads(payload)
        canonical = _canonical_json_bytes(configuration)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError("registration is not canonical JSON") from error
    if not isinstance(configuration, Mapping) or canonical != payload:
        raise ValueError("registration is not a canonical JSON object")
    _validate_bootstrap_configuration(configuration)
    return configuration, payload


def _next_incident_index(runs_descriptor: int) -> int:
    indices = []
    for name in os.listdir(runs_descriptor):
        match = _INCIDENT_FILENAME.fullmatch(name)
        if match is None:
            if name.startswith(_INCIDENT_PREFIX):
                raise ValueError("existing incident filename is malformed")
            continue
        metadata = os.stat(
            name,
            dir_fd=runs_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("existing incident is not a singly-linked file")
        indices.append(int(match.group(1)))
    indices.sort()
    if indices != list(range(1, len(indices) + 1)):
        raise ValueError("existing incident suffixes are not contiguous")
    return len(indices) + 1


def _incident_names(repository: Path) -> frozenset[str]:
    runs_descriptor = os.open(
        repository.resolve() / "runs",
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        return frozenset(
            name
            for name in os.listdir(runs_descriptor)
            if _INCIDENT_FILENAME.fullmatch(name) is not None
        )
    finally:
        os.close(runs_descriptor)


def _read_existing_incident(
    repository: Path,
    runs_descriptor: int,
    filename: str,
    configuration: Mapping[str, Any],
    registered_bytes: bytes,
) -> Mapping[str, Any]:
    before = os.stat(
        filename,
        dir_fd=runs_descriptor,
        follow_symlinks=False,
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size < 1
        or before.st_size > _INCIDENT_MAX_BYTES
    ):
        raise ValueError("new incident is not a bounded singly-linked file")
    descriptor = os.open(
        filename,
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0),
        dir_fd=runs_descriptor,
    )
    try:
        opened = os.fstat(descriptor)
        if _stable_metadata(opened) != _stable_metadata(before):
            raise ValueError("new incident identity changed before its read")
        chunks = bytearray()
        while len(chunks) <= _INCIDENT_MAX_BYTES:
            chunk = os.read(
                descriptor,
                _INCIDENT_MAX_BYTES + 1 - len(chunks),
            )
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) > _INCIDENT_MAX_BYTES:
            raise ValueError("new incident exceeds its read bound")
        after = os.fstat(descriptor)
        named = os.stat(
            filename,
            dir_fd=runs_descriptor,
            follow_symlinks=False,
        )
        if _stable_metadata(after) != _stable_metadata(
            opened
        ) or _stable_metadata(named) != _stable_metadata(opened):
            raise ValueError("new incident identity changed during its read")
    finally:
        os.close(descriptor)
    payload = bytes(chunks)
    try:
        record = json.loads(payload)
        canonical = _canonical_json_bytes(record)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError("new incident is not canonical JSON") from error
    match = _INCIDENT_FILENAME.fullmatch(filename)
    if (
        match is None
        or not isinstance(record, Mapping)
        or canonical != payload
        or set(record) != _INCIDENT_KEYS
        or record["schema_version"] != _INCIDENT_SCHEMA
        or isinstance(record["incident_index"], bool)
        or not isinstance(record["incident_index"], int)
        or record["incident_index"] != int(match.group(1))
        or record["phase"]
        not in {"preparation", "invariant", "compute", "publication"}
        or not isinstance(record["reason"], str)
        or not record["reason"]
        or not isinstance(record["reason_detail"], str)
        or record["configuration_echo"] != configuration
        or _canonical_json_bytes(record["configuration_echo"])
        != registered_bytes
        or record["registration_reference"]
        != configuration["registration_reference"]
    ):
        raise ValueError("new incident record is invalid")
    timestamp = record["timestamp_utc"]
    if (
        not isinstance(timestamp, str)
        or _INCIDENT_TIMESTAMP.fullmatch(timestamp) is None
    ):
        raise ValueError("new incident timestamp is invalid")
    try:
        parsed_timestamp = datetime.fromisoformat(
            timestamp.removesuffix("Z") + "+00:00"
        )
    except ValueError as error:
        raise ValueError("new incident timestamp is invalid") from error
    if parsed_timestamp.tzinfo != timezone.utc:
        raise ValueError("new incident timestamp is not UTC")
    primary_relative = "runs/anchor_context_report_v1.json"
    primary_exists = (repository.resolve() / primary_relative).is_file()
    expected_artifact = (
        primary_relative
        if record["phase"] == "publication" and primary_exists
        else None
    )
    if record["artifact_path"] != expected_artifact:
        raise ValueError("new incident artifact path is invalid")
    return record


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written == 0:
            raise OSError("incident write made no progress")
        view = view[written:]


def _publish_pre_import_incident(
    repository: Path,
    registration: str | Path,
    error: BaseException,
    *,
    reason: str = _PRE_IMPORT_REFUSAL_REASON,
    permit_unavailable_git: bool = False,
    incident_names_before: frozenset[str] | None = None,
) -> tuple[Path, Mapping[str, Any]]:
    """Publish the mandatory preparation incident without importing repo code."""
    configuration, registered_bytes = _read_registered_configuration(
        repository,
        registration,
        permit_unavailable_git=permit_unavailable_git,
    )
    root = repository.resolve()
    runs = root / "runs"
    runs_descriptor = os.open(
        runs,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        index = _next_incident_index(runs_descriptor)
        current_names = frozenset(
            name
            for name in os.listdir(runs_descriptor)
            if _INCIDENT_FILENAME.fullmatch(name) is not None
        )
        if incident_names_before is not None:
            if not incident_names_before.issubset(current_names):
                raise ValueError("incident history changed during coordinator")
            new_names = current_names - incident_names_before
            if new_names:
                if len(new_names) != 1:
                    raise ValueError(
                        "coordinator published multiple new incidents"
                    )
                filename = next(iter(new_names))
                record = _read_existing_incident(
                    root,
                    runs_descriptor,
                    filename,
                    configuration,
                    registered_bytes,
                )
                return runs / filename, record
        filename = f"{_INCIDENT_PREFIX}{index}.json"
        record = {
            "schema_version": _INCIDENT_SCHEMA,
            "incident_index": index,
            "timestamp_utc": (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            ),
            "phase": "preparation",
            "reason": reason,
            "reason_detail": (
                _COORDINATOR_ENTRY_FAILURE_DETAIL
                if reason == _COORDINATOR_ENTRY_FAILURE_REASON
                else str(error)
            ),
            "registration_reference": configuration["registration_reference"],
            "configuration_echo": configuration,
            "artifact_path": None,
        }
        payload = _canonical_json_bytes(record)
        descriptor = os.open(
            filename,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o444,
            dir_fd=runs_descriptor,
        )
        try:
            _write_all(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(runs_descriptor)
    finally:
        os.close(runs_descriptor)
    return runs / filename, record


def _assert_pre_import_guard(repository: Path) -> None:
    """Refuse anything except the already-registered sealed invocation."""
    prefix = sys.pycache_prefix
    if (
        not sys.flags.isolated
        or not sys.flags.dont_write_bytecode
        or not isinstance(prefix, str)
    ):
        raise RuntimeError(
            "runner requires python -I -B -X pycache_prefix=<fresh empty dir>"
        )
    sentinel = Path(prefix)
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
        raise RuntimeError("pycache prefix is not a fresh empty directory")

    root = repository.resolve()
    reported = Path(
        os.fsdecode(_git_bytes(root, "rev-parse", "--show-toplevel")).strip()
    ).resolve()
    if reported != root:
        raise RuntimeError("launcher path differs from Git checkout root")
    hidden = tuple(
        entry
        for entry in _git_bytes(root, "ls-files", "-v", "-z", "--").split(
            b"\0"
        )
        if entry and (entry[:1].islower() or entry.startswith(b"S "))
    )
    if hidden:
        raise RuntimeError(
            "tracked files use assume-unchanged or skip-worktree flags"
        )
    if _git_bytes(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ):
        raise RuntimeError("launcher requires an entirely clean checkout")
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
        raise RuntimeError("code roots contain ignored executable artifacts")


def _print_pre_import_refusal(
    error: BaseException,
    *,
    reason: str = _PRE_IMPORT_REFUSAL_REASON,
) -> None:
    print(
        json.dumps(
            {
                "status": "procedural_refusal",
                "path": None,
                "phase": "preparation",
                "reason": reason,
                "reason_detail": (
                    _COORDINATOR_ENTRY_FAILURE_DETAIL
                    if reason == _COORDINATOR_ENTRY_FAILURE_REASON
                    else str(error)
                ),
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )


def _print_incident(path: Path, record: Mapping[str, Any]) -> None:
    print(
        json.dumps(
            {
                "status": "incident",
                "path": path.as_posix(),
                "phase": record["phase"],
                "reason": record["reason"],
            },
            sort_keys=True,
        )
    )


def _run_coordinator(registration: str):
    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository / "src"))
    from populace_dynamics.estimates.anchor_context_coordinator import (
        run_registered_anchor_context,
    )

    return run_registered_anchor_context(registration)


def main() -> int:
    args = _arguments()
    repository = Path(__file__).resolve().parents[1]
    try:
        _assert_pre_import_guard(repository)
    except RuntimeError as error:
        try:
            path, record = _publish_pre_import_incident(
                repository,
                args.registration,
                error,
                permit_unavailable_git=isinstance(
                    error,
                    _GitVerificationUnavailable,
                ),
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            _print_pre_import_refusal(error)
            return 1
        _print_incident(path, record)
        return 1
    incident_names_before = None
    try:
        incident_names_before = _incident_names(repository)
        result = _run_coordinator(args.registration)
    except BaseException as error:
        try:
            path, record = _publish_pre_import_incident(
                repository,
                args.registration,
                error,
                reason=_COORDINATOR_ENTRY_FAILURE_REASON,
                incident_names_before=incident_names_before,
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            _print_pre_import_refusal(
                error,
                reason=_COORDINATOR_ENTRY_FAILURE_REASON,
            )
            return 1
        _print_incident(path, record)
        return 1
    print(
        json.dumps(
            {
                "status": result.status,
                "path": result.path.as_posix(),
                "phase": result.phase,
                "reason": result.reason,
            },
            sort_keys=True,
        )
    )
    return 0 if result.status == "published" else 1


if __name__ == "__main__":
    raise SystemExit(main())
