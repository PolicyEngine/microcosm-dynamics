"""Publication contracts for the registered anchor-context report.

This module reuses the first-estimates canonical registration and environment
sidecar machinery. It adds the anchor report's exact configuration, artifact,
hash-gate, and typed incident contracts without performing a production run.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from populace_dynamics import artifacts
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import anchor_context_report
from populace_dynamics.estimates import publication as first_publication

canonical_json_bytes = first_publication.canonical_json_bytes
prepare_environment_sidecar = first_publication.prepare_environment_sidecar
validate_environment_sidecar_payload = (
    first_publication.validate_environment_sidecar_payload
)

RUNTIME_PROVENANCE_SCHEMA_VERSION = (
    "anchor_context_report.runtime_provenance.v1"
)
EVIDENCE_LABELS = anchor_context_report.EVIDENCE_LABELS
EVIDENTIAL_STATUSES = {
    "comparison_results": {
        "status": "scale-invariant context only",
        "annual_scope": "baseline-only",
        "level_alignment_authority": False,
    },
    "official_anchor_level_panel": {
        "status": "descriptive only",
        "shared_level_gap_axis": False,
    },
    "model_level_panel": {
        "status": "descriptive only",
        "scope": "frame-relative, pre-alignment, labor-income proxy",
        "shared_level_gap_axis": False,
    },
    "opening_stock_consumers": {
        "status": "report-only imputed",
        "presentation": "secondary/non-headline",
        "model_metric_ids": [
            "combined_own_retirement.frame_annualized_benefit",
            "combined_own_retirement.weighted_beneficiary_count",
        ],
        "comparison_ids": [
            "cmp_retired_worker_monthly_benefit_per_beneficiary",
            "cmp_retired_worker_beneficiaries_per_worker",
            "cmp_retired_worker_benefits_per_reported_taxable_earnings",
        ],
    },
    "birth_timing": {
        "status": "unresolved",
        "reference": "Birth-timing sensitivity (amendment 2, frozen)",
        "annual_benefit_comparisons": "baseline-only",
        "cumulative_stress_applied_to_annual_values": False,
        "stress_interpretation": "stress scenarios, not bounds",
    },
}
CERTIFIES_NOTHING = (
    (
        "This report does not align, scale, calibrate, reweight, or "
        "nationalize the model frame."
    ),
    (
        "This report does not estimate what the Social Security "
        "Administration pays or collects."
    ),
    "This report does not certify forward production.",
    "This report creates no gate, floor, threshold, or verdict.",
    (
        "This report does not retire the frozen birth-timing sensitivity "
        "or authorize annual stress extrapolation."
    ),
)

_CONFIGURATION_KEYS = frozenset(
    {
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
)
_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "identity",
        "configuration_echo",
        "runtime_provenance",
        "inputs",
        "results",
        "labels",
        "evidential_statuses",
        "prior_incidents",
        "integrity",
        "certifies_nothing",
    }
)
_INCIDENT_KEYS = frozenset(
    {
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
)
_INCIDENT_PHASES = frozenset(
    {"preparation", "invariant", "compute", "publication"}
)
_INCIDENT_PREFIX = "anchor_context_report_incident_"
_INCIDENT_FILENAME = re.compile(
    r"anchor_context_report_incident_([1-9]\d*)\.json"
)
_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RUNTIME_KEYS = frozenset(
    {"schema_version", "implementation_commit", "python", "platform"}
)
_FIXTURE_FIRST_PATH = (
    "tests/fixtures/anchor_context/first_estimates_fixture_v1.json"
)
_FIXTURE_FIRST_SHA256 = (
    "be95a6eef919d2cf46197467fd75463d2c94d607983674da9f2723b0391d1c61"
)
_FIXTURE_ANCHOR_PATH = (
    "tests/fixtures/anchor_context/ssa_level_anchors_fixture_v1.json"
)
_FIXTURE_ANCHOR_SHA256 = (
    "0a473202440878e66201f60fbd76a686d22b77a2b0fd64fefb3b88bcc55f2ac4"
)
_FIXTURE_ANCHOR_VINTAGE = "ssa_level_anchors.fixture_only.v1"
_FILE_READ_CHUNK_SIZE = 1024 * 1024
_INPUT_MAX_BYTES = 64 * 1024 * 1024
_INCIDENT_MAX_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class _AnchorContextPrecomputeToken:
    """Opaque publication authority frozen before report computation."""

    registration: first_publication._RegisteredConfigurationToken
    runtime_provenance_bytes: bytes
    sidecar_payload: bytes
    sidecar_sha256: str
    prior_incidents: tuple[str, ...]


@dataclass(frozen=True, init=False)
class _VerifiedProductionInputs:
    """Opaque result of both registered production hash gates."""

    ceremony_capability: object
    registration: first_publication._RegisteredConfigurationToken
    first_estimates: Mapping[str, Any]
    anchors: Mapping[str, Any]
    first_estimates_snapshot: bytes
    anchors_snapshot: bytes

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "verified production inputs are minted only inside the ceremony"
        )


@dataclass(frozen=True, init=False)
class _VerifiedFixtureInputs:
    """Opaque result of the one fixed nonproduction fixture hash gate."""

    repository_root: Path
    first_estimates_input: Mapping[str, Any]
    anchor_input: Mapping[str, Any]
    first_estimates: Mapping[str, Any]
    anchors: Mapping[str, Any]
    first_estimates_snapshot: bytes
    anchors_snapshot: bytes

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError(
            "verified fixture inputs are minted only by the fixed loader"
        )


@dataclass(frozen=True, init=False)
class _InputReadAuthority:
    """One-call authority for one already-authorized input identity."""

    def __init__(self, *_args: Any, **_kwargs: Any):
        raise TypeError("input read authority is minted only by the loader")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} keys {sorted(observed)} != expected {sorted(expected)}"
        )


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a nonempty JSON string")
    return value


def _git_sha(value: Any, label: str) -> str:
    observed = _string(value, label)
    if _GIT_SHA.fullmatch(observed) is None:
        raise ValueError(f"{label} must be a 40-lowercase-hex Git SHA")
    return observed


def _sha256(value: Any, label: str) -> str:
    observed = _string(value, label)
    if _SHA256.fullmatch(observed) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return observed


def _assert_exact_json(actual: Any, expected: Any, path: str) -> None:
    """Compare JSON without bool/int coercion or sequence-order loss."""
    if type(actual) is not type(expected):
        raise ValueError(
            f"{path} has type {type(actual).__name__}; "
            f"expected {type(expected).__name__}"
        )
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(f"{path} has missing or extra object keys")
        for key, expected_value in expected.items():
            _assert_exact_json(actual[key], expected_value, f"{path}.{key}")
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f"{path} has the wrong array length")
        for index, (actual_value, expected_value) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _assert_exact_json(
                actual_value,
                expected_value,
                f"{path}[{index}]",
            )
        return
    if actual != expected:
        raise ValueError(f"{path} differs from the frozen value")


def _configuration_echo(
    *,
    registration_reference: str,
    implementation_commit: str,
    invocation: Sequence[str],
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> dict[str, Any]:
    _string(registration_reference, "registration_reference")
    first_publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    _git_sha(implementation_commit, "implementation_commit")
    if not isinstance(invocation, (list, tuple)) or not invocation:
        raise TypeError("invocation must be a nonempty string array")
    normalized_invocation = [
        _string(argument, f"invocation[{index}]")
        for index, argument in enumerate(invocation)
    ]
    return {
        "schema_version": registry.CONFIGURATION_SCHEMA_VERSION,
        "registration_reference": registration_reference,
        "design": registry.design_binding(),
        "implementation_commit": implementation_commit,
        "invocation": normalized_invocation,
        "first_estimates_input": copy.deepcopy(dict(first_estimates_input)),
        "anchor_input": copy.deepcopy(dict(anchor_input)),
        **registry.frozen_registries(),
    }


def registered_configuration_echo(
    *,
    registration_reference: str,
    implementation_commit: str,
    invocation: Sequence[str],
) -> dict[str, Any]:
    """Build the exact production configuration before report execution."""
    return _configuration_echo(
        registration_reference=registration_reference,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=registry.first_estimates_input_identity(),
        anchor_input=registry.anchor_input_identity(),
    )


def _registered_configuration_echo_for_test(
    *,
    registration_reference: str,
    implementation_commit: str,
    invocation: Sequence[str],
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a fixture-bound echo that production validation will reject."""
    return _configuration_echo(
        registration_reference=registration_reference,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )


def _validate_configuration_shape(
    configuration: Mapping[str, Any],
    *,
    expected_first_estimates_input: Mapping[str, Any],
    expected_anchor_input: Mapping[str, Any],
) -> None:
    _require_exact_keys(configuration, _CONFIGURATION_KEYS, "configuration")
    if configuration["schema_version"] != (
        registry.CONFIGURATION_SCHEMA_VERSION
    ):
        raise ValueError("configuration schema version changed")
    registration_reference = _string(
        configuration["registration_reference"],
        "configuration registration_reference",
    )
    first_publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    implementation_commit = _git_sha(
        configuration["implementation_commit"],
        "configuration implementation_commit",
    )
    invocation = _require_list(
        configuration["invocation"],
        "configuration invocation",
    )
    for index, argument in enumerate(invocation):
        _string(argument, f"configuration invocation[{index}]")
    expected = _configuration_echo(
        registration_reference=registration_reference,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=expected_first_estimates_input,
        anchor_input=expected_anchor_input,
    )
    _assert_exact_json(configuration, expected, "configuration")
    registry.validate_frozen_registries(
        required_series_ids=configuration["required_series_ids"],
        model_metric_specs=configuration["model_metric_specs"],
        pairings=configuration["pairings"],
        comparison_specs=configuration["comparison_specs"],
    )


def validate_registered_configuration_echo(
    configuration: Mapping[str, Any],
    *,
    registered_configuration_bytes: bytes,
) -> None:
    """Require canonical bytes and all eleven production configuration keys."""
    if not isinstance(registered_configuration_bytes, bytes):
        raise TypeError("registered configuration must be supplied as bytes")
    value = _require_mapping(configuration, "configuration")
    if canonical_json_bytes(value) != registered_configuration_bytes:
        raise ValueError(
            "configuration differs from the exact registered bytes"
        )
    _validate_configuration_shape(
        value,
        expected_first_estimates_input=(
            registry.first_estimates_input_identity()
        ),
        expected_anchor_input=registry.anchor_input_identity(),
    )


def _validate_fixture_configuration_echo(
    configuration: Mapping[str, Any],
    *,
    registered_configuration_bytes: bytes,
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    """Test-only exact validation for identities rejected by production."""
    if canonical_json_bytes(configuration) != registered_configuration_bytes:
        raise ValueError(
            "fixture configuration differs from its exact registered bytes"
        )
    _assert_fixture_identities(first_estimates_input, anchor_input)
    _validate_configuration_shape(
        configuration,
        expected_first_estimates_input=first_estimates_input,
        expected_anchor_input=anchor_input,
    )


def _validate_configuration_echo_for_execution(
    configuration: Mapping[str, Any],
) -> None:
    """Validate either the sole production identity or a rejected-by-prod fixture."""
    registered_bytes = canonical_json_bytes(configuration)
    first_estimates_input = _require_mapping(
        configuration.get("first_estimates_input"),
        "configuration first_estimates_input",
    )
    anchor_input = _require_mapping(
        configuration.get("anchor_input"),
        "configuration anchor_input",
    )
    if (
        first_estimates_input == registry.first_estimates_input_identity()
        and anchor_input == registry.anchor_input_identity()
    ):
        validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=registered_bytes,
        )
        return
    _validate_fixture_configuration_echo(
        configuration,
        registered_configuration_bytes=registered_bytes,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )


def build_runtime_provenance(
    implementation_commit: str,
) -> dict[str, str]:
    """Record separately labeled run-time identity."""
    return {
        "schema_version": RUNTIME_PROVENANCE_SCHEMA_VERSION,
        "implementation_commit": _git_sha(
            implementation_commit,
            "runtime implementation_commit",
        ),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def _validate_runtime_provenance(
    provenance: Any,
    *,
    implementation_commit: str,
) -> None:
    value = _require_mapping(provenance, "runtime_provenance")
    _require_exact_keys(value, _RUNTIME_KEYS, "runtime_provenance")
    if value["schema_version"] != RUNTIME_PROVENANCE_SCHEMA_VERSION:
        raise ValueError("runtime provenance schema changed")
    if value["implementation_commit"] != implementation_commit:
        raise ValueError(
            "runtime provenance implementation commit differs "
            "from configuration"
        )
    _git_sha(value["implementation_commit"], "runtime implementation_commit")
    _string(value["python"], "runtime python")
    _string(value["platform"], "runtime platform")


def _validate_input_identity(
    identity: Any,
    *,
    role: str,
) -> Mapping[str, Any]:
    value = _require_mapping(identity, f"{role} input identity")
    expected_keys = (
        frozenset({"path", "sha256"})
        if role == "first_estimates"
        else frozenset({"path", "artifact_vintage_id", "sha256"})
    )
    _require_exact_keys(value, expected_keys, f"{role} input identity")
    path = _string(value["path"], f"{role} input path")
    pure = PurePosixPath(path)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or "\\" in path
        or pure.as_posix() != path
    ):
        raise ValueError(f"{role} input path must be traversal-free relative")
    _sha256(value["sha256"], f"{role} input sha256")
    if role == "anchor":
        _string(
            value["artifact_vintage_id"],
            "anchor input artifact_vintage_id",
        )
    return value


def _production_input_identity(role: str) -> Mapping[str, Any]:
    if role == "first_estimates":
        return registry.first_estimates_input_identity()
    if role == "anchor":
        return registry.anchor_input_identity()
    raise ValueError("unknown input role")


def _fixture_input_identity(role: str) -> Mapping[str, Any]:
    if role == "first_estimates":
        return {
            "path": _FIXTURE_FIRST_PATH,
            "sha256": _FIXTURE_FIRST_SHA256,
        }
    if role == "anchor":
        return {
            "path": _FIXTURE_ANCHOR_PATH,
            "artifact_vintage_id": _FIXTURE_ANCHOR_VINTAGE,
            "sha256": _FIXTURE_ANCHOR_SHA256,
        }
    raise ValueError("unknown input role")


def _input_io_protocol():
    getframe = sys._getframe
    issued: dict[
        int,
        tuple[_InputReadAuthority, Path, str, int | None],
    ] = {}
    capability_verifier: (
        Callable[
            [object],
            first_publication._RegisteredConfigurationToken,
        ]
        | None
    ) = None

    def bind_capability_verifier(
        verifier: Callable[
            [object],
            first_publication._RegisteredConfigurationToken,
        ],
    ) -> None:
        nonlocal capability_verifier
        from populace_dynamics.estimates import anchor_context_coordinator

        caller = getframe(1)
        protocol = getattr(
            anchor_context_coordinator,
            "_ceremony_capability_protocol",
            None,
        )
        if (
            protocol is None
            or caller.f_code is not protocol.__code__
            or caller.f_locals.get("require") is not verifier
        ):
            raise TypeError(
                "input I/O verifier binding requires coordinator bootstrap"
            )
        if capability_verifier is not None:
            raise RuntimeError("input I/O capability verifier already bound")
        capability_verifier = verifier

    def require(
        candidate: object,
        *,
        repository_root: Path,
        relative_path: str,
        descriptor: int | None,
        expected_caller: Callable[..., Any],
    ) -> None:
        state = issued.get(id(candidate))
        caller = getframe(2)
        if (
            state is None
            or state[0] is not candidate
            or not isinstance(candidate, _InputReadAuthority)
            or state[1] is not repository_root
            or state[2] != relative_path
            or state[3] != descriptor
            or caller.f_code is not expected_caller.__code__
            or caller.f_locals.get("io_authority") is not candidate
        ):
            raise TypeError("input I/O is internal to a verified loader")

    def open_regular_relative(
        io_authority: object,
        repository_root: Path,
        relative_path: str,
    ) -> tuple[int, os.stat_result]:
        """Open one authorized file without following component symlinks."""
        require(
            io_authority,
            repository_root=repository_root,
            relative_path=relative_path,
            descriptor=None,
            expected_caller=load,
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
            raise RuntimeError("platform lacks sealed descriptor flags")
        parts = PurePosixPath(relative_path).parts
        if not parts:
            raise ValueError("input path is empty")
        opened_directories: list[int] = []
        try:
            current = os.open(
                repository_root,
                os.O_RDONLY | directory_flag | no_follow | close_on_exec,
            )
            opened_directories.append(current)
            for component in parts[:-1]:
                current = os.open(
                    component,
                    os.O_RDONLY | directory_flag | no_follow | close_on_exec,
                    dir_fd=current,
                )
                opened_directories.append(current)
            opened = os.open(
                parts[-1],
                os.O_RDONLY | no_follow | nonblocking | close_on_exec,
                dir_fd=current,
            )
            metadata = os.fstat(opened)
            if not stat.S_ISREG(metadata.st_mode):
                os.close(opened)
                raise ValueError("input path is not a regular file")
            return opened, metadata
        finally:
            for directory in reversed(opened_directories):
                os.close(directory)

    def protected_input_file_ids(
        io_authority: object,
        repository_root: Path,
        relative_path: str,
    ) -> frozenset[tuple[int, int]]:
        require(
            io_authority,
            repository_root=repository_root,
            relative_path=relative_path,
            descriptor=None,
            expected_caller=load,
        )
        protected: set[tuple[int, int]] = set()
        for relative in (
            registry.FIRST_ESTIMATES_INPUT_PATH,
            registry.ANCHOR_INPUT_PATH,
        ):
            try:
                metadata = os.stat(
                    repository_root / relative,
                    follow_symlinks=False,
                )
            except OSError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    "canonical production input path is not regular"
                )
            protected.add((metadata.st_dev, metadata.st_ino))
        return frozenset(protected)

    def read_open_descriptor(
        io_authority: object,
        repository_root: Path,
        relative_path: str,
        descriptor: int,
    ) -> bytes:
        require(
            io_authority,
            repository_root=repository_root,
            relative_path=relative_path,
            descriptor=descriptor,
            expected_caller=load,
        )
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(
                descriptor,
                min(
                    _FILE_READ_CHUNK_SIZE,
                    _INPUT_MAX_BYTES + 1 - observed,
                ),
            )
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            observed += len(chunk)
            if observed > _INPUT_MAX_BYTES:
                raise ValueError("input exceeds its sealed byte bound")

    def load(
        repository_root: str | Path,
        identity: Mapping[str, Any],
        *,
        role: str,
        ceremony_capability: object | None = None,
    ) -> tuple[Mapping[str, Any], bytes]:
        """Load one fixed fixture or live-capability production input."""
        root = Path(repository_root).resolve()
        validated = _validate_input_identity(identity, role=role)
        production_identity = _production_input_identity(role)
        fixture_identity = _fixture_input_identity(role)
        is_production = dict(validated) == dict(production_identity)
        is_fixture = dict(validated) == dict(fixture_identity)
        if not is_production and not is_fixture:
            raise ValueError(
                "input identity is neither fixed fixture nor production"
            )

        verified_registration = None
        if is_production:
            if ceremony_capability is None:
                raise TypeError(
                    "production input I/O requires a live ceremony capability"
                )
            if capability_verifier is None:
                raise RuntimeError("production input verifier is not bound")
            verified_registration = capability_verifier(ceremony_capability)
            configuration = first_publication._configuration_echo(
                verified_registration
            )
            configuration_key = (
                "first_estimates_input"
                if role == "first_estimates"
                else "anchor_input"
            )
            if (
                verified_registration._repository_root != root
                or configuration.get(configuration_key) != production_identity
            ):
                raise ValueError(
                    "ceremony capability is not bound to this production input"
                )
        elif ceremony_capability is not None:
            raise TypeError("fixture input I/O rejects production authority")

        relative_path = validated["path"]
        io_authority = object.__new__(_InputReadAuthority)
        issued[id(io_authority)] = (
            io_authority,
            root,
            relative_path,
            None,
        )
        descriptor: int | None = None
        try:
            descriptor, metadata = open_regular_relative(
                io_authority,
                root,
                relative_path,
            )
            file_id = (metadata.st_dev, metadata.st_ino)
            if metadata.st_nlink != 1 or metadata.st_size > _INPUT_MAX_BYTES:
                raise ValueError(
                    "input must be one singly linked bounded regular file"
                )
            if is_fixture and file_id in protected_input_file_ids(
                io_authority,
                root,
                relative_path,
            ):
                raise ValueError("fixture input aliases a production input")
            issued[id(io_authority)] = (
                io_authority,
                root,
                relative_path,
                descriptor,
            )
            raw = read_open_descriptor(
                io_authority,
                root,
                relative_path,
                descriptor,
            )
            after = os.fstat(descriptor)
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
                getattr(metadata, field) != getattr(after, field)
                for field in stable_fields
            ):
                raise ValueError("input changed during its sealed read")
        finally:
            issued.pop(id(io_authority), None)
            if descriptor is not None:
                os.close(descriptor)

        digest = hashlib.sha256(raw).hexdigest()
        if digest != validated["sha256"]:
            raise ValueError(f"{role} input sha256 differs from registration")
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{role} input is not valid JSON") from error
        value = _require_mapping(document, f"{role} input")
        if canonical_json_bytes(value) != raw:
            raise ValueError(f"{role} input is not canonical JSON")
        if role == "anchor" and value.get("artifact_vintage_id") != (
            validated["artifact_vintage_id"]
        ):
            raise ValueError("anchor input vintage differs from registration")
        return value, raw

    return (
        load,
        bind_capability_verifier,
        open_regular_relative,
        read_open_descriptor,
    )


(
    _load_verified_json,
    _bind_input_io_capability_verifier,
    _open_regular_relative,
    _read_open_descriptor,
) = _input_io_protocol()
del _input_io_protocol


def _assert_fixture_identities(
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    first = dict(
        _validate_input_identity(
            first_estimates_input,
            role="first_estimates",
        )
    )
    anchor = dict(_validate_input_identity(anchor_input, role="anchor"))
    if first != _fixture_input_identity("first_estimates"):
        raise ValueError("fixture first-estimates identity is not fixed")
    if anchor != _fixture_input_identity("anchor"):
        raise ValueError("fixture anchor identity is not fixed")


def _fixture_input_protocol():
    load_verified_json = _load_verified_json
    issued: dict[
        int,
        tuple[_VerifiedFixtureInputs, Path, bytes, bytes, bool],
    ] = {}

    def load(repository_root: str | Path) -> _VerifiedFixtureInputs:
        """Load only the two immutable manifest-bound fixture files."""
        root = Path(repository_root).resolve()
        first_identity = _fixture_input_identity("first_estimates")
        anchor_identity = _fixture_input_identity("anchor")
        first, first_raw = load_verified_json(
            root,
            first_identity,
            role="first_estimates",
        )
        anchor, anchor_raw = load_verified_json(
            root,
            anchor_identity,
            role="anchor",
        )
        if first.get("fixture_only") is not True:
            raise ValueError(
                "first-estimates rehearsal input is not fixture-only"
            )
        if anchor.get("fixture_only") is not True:
            raise ValueError("anchor rehearsal input is not fixture-only")
        bundle = object.__new__(_VerifiedFixtureInputs)
        object.__setattr__(bundle, "repository_root", root)
        object.__setattr__(
            bundle,
            "first_estimates_input",
            dict(first_identity),
        )
        object.__setattr__(bundle, "anchor_input", dict(anchor_identity))
        object.__setattr__(bundle, "first_estimates", first)
        object.__setattr__(bundle, "anchors", anchor)
        object.__setattr__(
            bundle,
            "first_estimates_snapshot",
            first_raw,
        )
        object.__setattr__(bundle, "anchors_snapshot", anchor_raw)
        temporary_root = Path(tempfile.gettempdir()).resolve()
        try:
            root.relative_to(temporary_root)
            under_temporary_root = True
        except ValueError:
            under_temporary_root = False
        publishable = under_temporary_root and root.name.startswith(
            "anchor-context-fixture-rehearsal-"
        )
        issued[id(bundle)] = (
            bundle,
            root,
            first_raw,
            anchor_raw,
            publishable,
        )
        return bundle

    def require(
        bundle: object,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        state = issued.get(id(bundle))
        if (
            state is None
            or state[0] is not bundle
            or not isinstance(bundle, _VerifiedFixtureInputs)
        ):
            raise TypeError(
                "fixture computation requires a fixed loader-issued bundle"
            )
        _, issued_root, first_raw, anchor_raw, _publishable = state
        if (
            bundle.repository_root != issued_root
            or bundle.first_estimates_snapshot != first_raw
            or bundle.anchors_snapshot != anchor_raw
            or hashlib.sha256(first_raw).hexdigest() != _FIXTURE_FIRST_SHA256
            or hashlib.sha256(anchor_raw).hexdigest() != _FIXTURE_ANCHOR_SHA256
        ):
            raise ValueError("fixed fixture bundle bytes changed")
        try:
            first = _require_mapping(
                json.loads(first_raw),
                "first-estimates fixture",
            )
            anchor = _require_mapping(
                json.loads(anchor_raw),
                "anchor fixture",
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("fixed fixture bundle is invalid JSON") from error
        if (
            canonical_json_bytes(first) != first_raw
            or canonical_json_bytes(anchor) != anchor_raw
            or first.get("fixture_only") is not True
            or anchor.get("fixture_only") is not True
            or anchor.get("artifact_vintage_id") != _FIXTURE_ANCHOR_VINTAGE
        ):
            raise ValueError("fixed fixture bundle content changed")
        return first, anchor

    def require_publishable(
        bundle: object,
        repository_root: Path,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        documents = require(bundle)
        state = issued[id(bundle)]
        _, issued_root, _first_raw, _anchor_raw, publishable = state
        if not publishable or repository_root.resolve() != issued_root:
            raise TypeError(
                "fixture publication requires its issued private rehearsal root"
            )
        return documents

    load.__name__ = "load_fixture_documents"
    load.__qualname__ = "load_fixture_documents"
    return load, require, require_publishable


(
    load_fixture_documents,
    _require_verified_fixture_inputs,
    _require_publishable_fixture_inputs,
) = _fixture_input_protocol()
del _fixture_input_protocol


def _production_input_protocol():
    load_verified_json = _load_verified_json
    configuration_echo = first_publication._configuration_echo
    validate_configuration = validate_registered_configuration_echo
    issued: dict[
        int,
        tuple[
            _VerifiedProductionInputs,
            object,
            first_publication._RegisteredConfigurationToken,
            bytes,
            bytes,
        ],
    ] = {}
    capability_verifier: (
        Callable[
            [object],
            first_publication._RegisteredConfigurationToken,
        ]
        | None
    ) = None

    def bind_capability_verifier(
        verifier: Callable[
            [object],
            first_publication._RegisteredConfigurationToken,
        ],
    ) -> None:
        nonlocal capability_verifier
        from populace_dynamics.estimates import anchor_context_coordinator

        caller = sys._getframe(1)
        protocol = getattr(
            anchor_context_coordinator,
            "_ceremony_capability_protocol",
            None,
        )
        if (
            protocol is None
            or caller.f_code is not protocol.__code__
            or caller.f_locals.get("require") is not verifier
        ):
            raise TypeError(
                "production verifier binding requires coordinator bootstrap"
            )
        if capability_verifier is not None:
            raise RuntimeError(
                "production input capability verifier already bound"
            )
        capability_verifier = verifier

    def verify_capability(
        ceremony_capability: object,
    ) -> first_publication._RegisteredConfigurationToken:
        if capability_verifier is None:
            raise RuntimeError("production input verifier is not bound")
        return capability_verifier(ceremony_capability)

    def load(ceremony_capability: object) -> _VerifiedProductionInputs:
        token = verify_capability(ceremony_capability)
        configuration = configuration_echo(token)
        validate_configuration(
            configuration,
            registered_configuration_bytes=token._configuration_bytes,
        )
        first, first_raw = load_verified_json(
            token._repository_root,
            configuration["first_estimates_input"],
            role="first_estimates",
            ceremony_capability=ceremony_capability,
        )
        anchor, anchor_raw = load_verified_json(
            token._repository_root,
            configuration["anchor_input"],
            role="anchor",
            ceremony_capability=ceremony_capability,
        )
        verified = object.__new__(_VerifiedProductionInputs)
        object.__setattr__(
            verified,
            "ceremony_capability",
            ceremony_capability,
        )
        object.__setattr__(verified, "registration", token)
        object.__setattr__(verified, "first_estimates", first)
        object.__setattr__(verified, "anchors", anchor)
        object.__setattr__(
            verified,
            "first_estimates_snapshot",
            first_raw,
        )
        object.__setattr__(verified, "anchors_snapshot", anchor_raw)
        issued[id(verified)] = (
            verified,
            ceremony_capability,
            token,
            first_raw,
            anchor_raw,
        )
        return verified

    def require(
        verified_inputs: object,
        *,
        ceremony_capability: object,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        registration = verify_capability(ceremony_capability)
        state = issued.get(id(verified_inputs))
        if (
            state is None
            or state[0] is not verified_inputs
            or not isinstance(
                verified_inputs,
                _VerifiedProductionInputs,
            )
        ):
            raise TypeError(
                "production computation requires hash-gated inputs"
            )
        (
            _,
            issued_capability,
            issued_registration,
            first_raw,
            anchor_raw,
        ) = state
        if (
            issued_capability is not ceremony_capability
            or issued_registration is not registration
            or verified_inputs.ceremony_capability is not ceremony_capability
            or verified_inputs.registration is not registration
            or verified_inputs.first_estimates_snapshot != first_raw
            or verified_inputs.anchors_snapshot != anchor_raw
        ):
            raise TypeError(
                "hash-gated inputs belong to a different ceremony capability"
            )
        try:
            first = _require_mapping(
                json.loads(first_raw),
                "first-estimates production input",
            )
            anchor = _require_mapping(
                json.loads(anchor_raw),
                "anchor production input",
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("production input snapshot is invalid") from error
        if (
            canonical_json_bytes(first) != first_raw
            or canonical_json_bytes(anchor) != anchor_raw
        ):
            raise ValueError("production input snapshot changed")
        return first, anchor

    load.__name__ = "_load_production_documents"
    load.__qualname__ = "_load_production_documents"
    return load, require, bind_capability_verifier


(
    _load_production_documents,
    _require_verified_production_inputs,
    _bind_production_input_capability_verifier,
) = _production_input_protocol()
del _production_input_protocol


def _validate_environment_sidecar_hash(value: Any) -> str:
    return _sha256(value, "environment sidecar sha256")


def _validate_artifact_input_binding(
    configuration: Mapping[str, Any],
    *,
    input_bundle: object,
    ceremony_capability: object | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any], bool]:
    production = (
        configuration["first_estimates_input"]
        == registry.first_estimates_input_identity()
        and configuration["anchor_input"] == registry.anchor_input_identity()
    )
    if production:
        if ceremony_capability is None:
            raise TypeError(
                "production artifact validation requires ceremony authority"
            )
        first_estimates, anchors = _require_verified_production_inputs(
            input_bundle,
            ceremony_capability=ceremony_capability,
        )
        registered_configuration = first_publication._configuration_echo(
            input_bundle.registration
        )
        _assert_exact_json(
            registered_configuration,
            configuration,
            "verified_inputs.configuration_echo",
        )
        return first_estimates, anchors, True
    if ceremony_capability is not None:
        raise TypeError("fixture artifacts cannot carry ceremony authority")
    first_input = _require_mapping(
        configuration["first_estimates_input"],
        "fixture artifact first_estimates_input",
    )
    anchor_input = _require_mapping(
        configuration["anchor_input"],
        "fixture artifact anchor_input",
    )
    _assert_fixture_identities(first_input, anchor_input)
    first_estimates, anchors = _require_verified_fixture_inputs(input_bundle)
    if (
        input_bundle.first_estimates_input != first_input
        or input_bundle.anchor_input != anchor_input
    ):
        raise ValueError(
            "fixture artifact identities differ from fixed bundle"
        )
    return first_estimates, anchors, False


def _validate_prior_incident_paths(
    prior_incidents: Sequence[str],
) -> tuple[str, ...]:
    if not isinstance(prior_incidents, (list, tuple)):
        raise TypeError("prior incidents must be a JSON string array")
    paths = tuple(prior_incidents)
    if not all(isinstance(path, str) for path in paths):
        raise TypeError("prior incident paths must be strings")
    expected = tuple(
        f"runs/anchor_context_report_incident_{index}.json"
        for index in range(1, len(paths) + 1)
    )
    if paths != expected:
        raise ValueError(
            "prior incidents must be the complete ordered context history"
        )
    return paths


def build_anchor_context_artifact(
    *,
    configuration_echo: Mapping[str, Any],
    runtime_provenance: Mapping[str, Any],
    results: Mapping[str, Any],
    input_bundle: object,
    environment_sidecar_sha256: str,
    prior_incidents: Sequence[str] = (),
    ceremony_capability: object | None = None,
) -> dict[str, Any]:
    """Assemble the complete integrity-bound primary report."""
    configuration = copy.deepcopy(dict(configuration_echo))
    _validate_configuration_echo_for_execution(configuration)
    _first_estimates, _anchors, _production = _validate_artifact_input_binding(
        configuration,
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
    )
    registration_reference = configuration["registration_reference"]
    artifact = {
        "schema_version": registry.REPORT_SCHEMA_VERSION,
        "identity": {
            "report_id": "anchor_context_report",
            "report_class": "registered estimates report",
            "registration_reference": registration_reference,
        },
        "configuration_echo": configuration,
        "runtime_provenance": copy.deepcopy(dict(runtime_provenance)),
        "inputs": {
            "first_estimates_input": copy.deepcopy(
                configuration["first_estimates_input"]
            ),
            "anchor_input": copy.deepcopy(configuration["anchor_input"]),
        },
        "results": copy.deepcopy(dict(results)),
        "labels": list(EVIDENCE_LABELS),
        "evidential_statuses": copy.deepcopy(EVIDENTIAL_STATUSES),
        "prior_incidents": list(
            _validate_prior_incident_paths(prior_incidents)
        ),
        "integrity": {
            "environment_sidecar": {
                "path": Path(registry.SIDECAR_OUTPUT_PATH).name,
                "sha256": _validate_environment_sidecar_hash(
                    environment_sidecar_sha256
                ),
            }
        },
        "certifies_nothing": list(CERTIFIES_NOTHING),
    }
    validate_anchor_context_artifact(
        artifact,
        expected_configuration_echo=configuration,
        expected_runtime_provenance=runtime_provenance,
        expected_prior_incidents=prior_incidents,
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
    )
    return artifact


def validate_anchor_context_artifact(
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
    expected_runtime_provenance: Mapping[str, Any],
    expected_prior_incidents: Sequence[str] = (),
    input_bundle: object,
    ceremony_capability: object | None = None,
) -> None:
    """Validate every report field and independently recompute all results."""
    value = _require_mapping(artifact, "artifact")
    _require_exact_keys(value, _ARTIFACT_KEYS, "artifact")
    if value["schema_version"] != registry.REPORT_SCHEMA_VERSION:
        raise ValueError("anchor-context artifact schema changed")
    if value["configuration_echo"] != expected_configuration_echo:
        raise ValueError("artifact configuration echo changed")
    _validate_configuration_echo_for_execution(value["configuration_echo"])
    _first_estimates, _anchors, production = _validate_artifact_input_binding(
        value["configuration_echo"],
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
    )
    identity = _require_mapping(value["identity"], "artifact identity")
    _require_exact_keys(
        identity,
        frozenset({"report_id", "report_class", "registration_reference"}),
        "artifact identity",
    )
    expected_identity = {
        "report_id": "anchor_context_report",
        "report_class": "registered estimates report",
        "registration_reference": expected_configuration_echo[
            "registration_reference"
        ],
    }
    _assert_exact_json(identity, expected_identity, "artifact.identity")
    if value["runtime_provenance"] != expected_runtime_provenance:
        raise ValueError("artifact runtime provenance changed")
    _validate_runtime_provenance(
        value["runtime_provenance"],
        implementation_commit=expected_configuration_echo[
            "implementation_commit"
        ],
    )
    expected_inputs = {
        "first_estimates_input": expected_configuration_echo[
            "first_estimates_input"
        ],
        "anchor_input": expected_configuration_echo["anchor_input"],
    }
    _assert_exact_json(value["inputs"], expected_inputs, "artifact.inputs")
    if value["labels"] != list(EVIDENCE_LABELS):
        raise ValueError("artifact changed the three evidence labels")
    _assert_exact_json(
        value["evidential_statuses"],
        EVIDENTIAL_STATUSES,
        "artifact.evidential_statuses",
    )
    expected_incidents = _validate_prior_incident_paths(
        expected_prior_incidents
    )
    _assert_exact_json(
        value["prior_incidents"],
        list(expected_incidents),
        "artifact.prior_incidents",
    )
    if value["certifies_nothing"] != list(CERTIFIES_NOTHING):
        raise ValueError("artifact certifies_nothing statements changed")
    integrity = _require_mapping(value["integrity"], "artifact integrity")
    _require_exact_keys(
        integrity,
        frozenset({"environment_sidecar"}),
        "artifact integrity",
    )
    sidecar = _require_mapping(
        integrity["environment_sidecar"],
        "artifact environment sidecar",
    )
    _require_exact_keys(
        sidecar,
        frozenset({"path", "sha256"}),
        "artifact environment sidecar",
    )
    if sidecar["path"] != Path(registry.SIDECAR_OUTPUT_PATH).name:
        raise ValueError("artifact environment sidecar path changed")
    _validate_environment_sidecar_hash(sidecar["sha256"])
    if not production:
        anchor_context_report.validate_results(
            value["results"],
            fixture_inputs=input_bundle,
        )
    else:
        anchor_context_report._validate_production_results(
            ceremony_capability,
            value["results"],
            input_bundle,
        )
    canonical_json_bytes(value)


def _write_anchor_context_artifact_for_test(
    *,
    repository_root: str | Path,
    artifact: Mapping[str, Any],
    expected_configuration_echo: Mapping[str, Any],
    expected_runtime_provenance: Mapping[str, Any],
    expected_prior_incidents: Sequence[str] = (),
    input_bundle: object,
    ceremony_capability: object | None = None,
    sidecar_payload: bytes,
) -> Path:
    """Validate and exclusively write primary then sidecar without rollback."""
    root = Path(repository_root).resolve()
    destination = root / registry.PRIMARY_OUTPUT_PATH
    validate_environment_sidecar_payload(sidecar_payload)
    expected_hash = hashlib.sha256(sidecar_payload).hexdigest()
    integrity = _require_mapping(
        artifact.get("integrity"),
        "artifact integrity",
    )
    sidecar = _require_mapping(
        integrity.get("environment_sidecar"),
        "artifact environment sidecar",
    )
    if sidecar.get("sha256") != expected_hash:
        raise ValueError("artifact does not bind the supplied sidecar bytes")
    validate_anchor_context_artifact(
        artifact,
        expected_configuration_echo=expected_configuration_echo,
        expected_runtime_provenance=expected_runtime_provenance,
        expected_prior_incidents=expected_prior_incidents,
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
    )
    production = ceremony_capability is not None
    if not production:
        _require_publishable_fixture_inputs(input_bundle, root)
    artifacts.write_new(
        destination,
        canonical_json_bytes(artifact),
        sidecar=True,
        sidecar_payload=sidecar_payload,
        preserve_primary_on_sidecar_failure=True,
    )
    return destination


def _parse_registered_configuration(
    *,
    repository_root: str | Path,
    registered_configuration_bytes: bytes,
) -> first_publication._RegisteredConfigurationToken:
    try:
        value = json.loads(registered_configuration_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "registered configuration is not valid JSON"
        ) from error
    configuration = _require_mapping(value, "registered configuration")
    registration_reference = _string(
        configuration.get("registration_reference"),
        "registered configuration registration_reference",
    )
    token = first_publication._parse_registered_configuration(
        repository_root=repository_root,
        registration_reference=registration_reference,
        registered_configuration_bytes=registered_configuration_bytes,
    )
    validate_registered_configuration_echo(
        first_publication._configuration_echo(token),
        registered_configuration_bytes=registered_configuration_bytes,
    )
    return token


def _freeze_precompute(
    registration: first_publication._RegisteredConfigurationToken,
    *,
    runtime_provenance: Mapping[str, Any],
    sidecar_payload: bytes,
    prior_incidents: Sequence[str] = (),
) -> _AnchorContextPrecomputeToken:
    if not isinstance(
        registration,
        first_publication._RegisteredConfigurationToken,
    ):
        raise TypeError("precompute requires a registration token")
    configuration = first_publication._configuration_echo(registration)
    _validate_runtime_provenance(
        runtime_provenance,
        implementation_commit=configuration["implementation_commit"],
    )
    validate_environment_sidecar_payload(sidecar_payload)
    payload = bytes(sidecar_payload)
    return _AnchorContextPrecomputeToken(
        registration=registration,
        runtime_provenance_bytes=canonical_json_bytes(runtime_provenance),
        sidecar_payload=payload,
        sidecar_sha256=hashlib.sha256(payload).hexdigest(),
        prior_incidents=_validate_prior_incident_paths(prior_incidents),
    )


def _runtime_provenance(
    token: _AnchorContextPrecomputeToken,
) -> Mapping[str, Any]:
    value = json.loads(token.runtime_provenance_bytes)
    return _require_mapping(value, "frozen runtime provenance")


def write_anchor_context_artifact(
    token: _AnchorContextPrecomputeToken,
    artifact: Mapping[str, Any],
    *,
    input_bundle: object,
    ceremony_capability: object,
) -> Path:
    """Publish production only through the live ceremony capability."""
    if not isinstance(token, _AnchorContextPrecomputeToken):
        raise TypeError("publication requires an anchor precompute token")
    _require_verified_production_inputs(
        input_bundle,
        ceremony_capability=ceremony_capability,
    )
    configuration = first_publication._configuration_echo(token.registration)
    return _write_anchor_context_artifact_for_test(
        repository_root=token.registration._repository_root,
        artifact=artifact,
        expected_configuration_echo=configuration,
        expected_runtime_provenance=_runtime_provenance(token),
        expected_prior_incidents=token.prior_incidents,
        input_bundle=input_bundle,
        ceremony_capability=ceremony_capability,
        sidecar_payload=token.sidecar_payload,
    )


def _validate_anchor_context_incident(
    record: Mapping[str, Any],
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
    production_only: bool,
) -> None:
    """Enforce the exact typed nine-key incident schema."""
    value = _require_mapping(record, "incident")
    _require_exact_keys(value, _INCIDENT_KEYS, "incident")
    if value["schema_version"] != registry.INCIDENT_SCHEMA_VERSION:
        raise ValueError("incident schema version changed")
    index = value["incident_index"]
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        raise TypeError("incident_index must be a positive JSON integer")
    root = Path(repository_root).resolve()
    incident_path = Path(path)
    if not incident_path.is_absolute():
        incident_path = root / incident_path
    incident_path = incident_path.resolve()
    if incident_path.parent != (root / "runs").resolve():
        raise ValueError("incident path must be directly under runs")
    match = _INCIDENT_FILENAME.fullmatch(incident_path.name)
    if match is None or int(match.group(1)) != index:
        raise ValueError("incident index does not match canonical filename")
    first_publication._parse_utc_timestamp(value["timestamp_utc"])
    if value["phase"] not in _INCIDENT_PHASES:
        raise ValueError("incident phase is outside the frozen enum")
    _string(value["reason"], "incident reason")
    if not isinstance(value["reason_detail"], str):
        raise TypeError("incident reason_detail must be a JSON string")
    _string(
        value["registration_reference"],
        "incident registration_reference",
    )
    configuration = _require_mapping(
        value["configuration_echo"],
        "incident configuration_echo",
    )
    configuration_bytes = canonical_json_bytes(configuration)
    if production_only:
        validate_registered_configuration_echo(
            configuration,
            registered_configuration_bytes=configuration_bytes,
        )
    else:
        first_estimates_input = _require_mapping(
            configuration.get("first_estimates_input"),
            "fixture incident first_estimates_input",
        )
        anchor_input = _require_mapping(
            configuration.get("anchor_input"),
            "fixture incident anchor_input",
        )
        _validate_fixture_configuration_echo(
            configuration,
            registered_configuration_bytes=configuration_bytes,
            first_estimates_input=first_estimates_input,
            anchor_input=anchor_input,
        )
    _assert_exact_json(
        configuration,
        expected_configuration_echo,
        "incident.configuration_echo",
    )
    if value["registration_reference"] != configuration.get(
        "registration_reference"
    ):
        raise ValueError(
            "incident registration reference differs from configuration"
        )
    artifact_path = value["artifact_path"]
    if artifact_path is not None and not isinstance(artifact_path, str):
        raise TypeError("incident artifact_path must be a string or null")
    primary = root / registry.PRIMARY_OUTPUT_PATH
    if os.path.lexists(primary) and (
        primary.is_symlink() or not primary.is_file()
    ):
        raise ValueError("partial primary path is not a regular file")
    partial_exists = primary.is_file()
    expected_path = (
        registry.PRIMARY_OUTPUT_PATH
        if value["phase"] == "publication" and partial_exists
        else None
    )
    if artifact_path != expected_path:
        raise ValueError(
            "artifact_path must be non-null iff publication partial exists"
        )
    _, next_index = _next_incident_path(root)
    if incident_path.exists():
        if index >= next_index:
            raise ValueError("incident path is outside contiguous history")
    elif index != next_index:
        raise ValueError("incident index is not the next contiguous suffix")
    canonical_json_bytes(value)


def _read_incident_file(
    path: str | Path,
    *,
    repository_root: str | Path,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]]:
    """Read canonical incident bytes through one pinned no-follow chain."""
    root = Path(repository_root).resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(
                "incident path is outside the repository"
            ) from error
    else:
        relative = candidate
    if (
        relative.is_absolute()
        or len(relative.parts) != 2
        or relative.parts[0] != "runs"
        or any(part in {"", ".", ".."} for part in relative.parts)
        or "\\" in relative.as_posix()
        or _INCIDENT_FILENAME.fullmatch(relative.name) is None
    ):
        raise ValueError("incident path must be canonical directly under runs")
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
        raise RuntimeError("platform lacks sealed incident descriptor flags")
    root_descriptor = os.open(
        root,
        os.O_RDONLY | directory_flag | no_follow | close_on_exec,
    )
    runs_descriptor = -1
    descriptor = -1
    try:
        runs_descriptor = os.open(
            "runs",
            os.O_RDONLY | directory_flag | no_follow | close_on_exec,
            dir_fd=root_descriptor,
        )
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | no_follow | nonblocking | close_on_exec,
            dir_fd=runs_descriptor,
        )
        metadata = os.fstat(descriptor)
        file_id = (metadata.st_dev, metadata.st_ino)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > _INCIDENT_MAX_BYTES
        ):
            raise ValueError(
                "incident must be a bounded singly-linked regular file"
            )
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
            raise ValueError("incident exceeds its read bound")
        after = os.fstat(descriptor)
        named = os.stat(
            relative.name,
            dir_fd=runs_descriptor,
            follow_symlinks=False,
        )
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
            getattr(metadata, field) != getattr(after, field)
            or getattr(metadata, field) != getattr(named, field)
            for field in stable_fields
        ):
            raise ValueError("incident identity changed during its read")
        payload = bytes(chunks)
    finally:
        for opened in (descriptor, runs_descriptor, root_descriptor):
            if opened >= 0:
                os.close(opened)
    try:
        record = json.loads(payload)
        canonical = canonical_json_bytes(record)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError("incident is not canonical JSON") from error
    if not isinstance(record, Mapping) or canonical != payload:
        raise ValueError("incident bytes are not one canonical JSON object")
    return record, payload, file_id


def _validate_anchor_context_incident_file(
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any] | None,
    repository_root: str | Path,
    production_only: bool,
) -> tuple[Mapping[str, Any], bytes, tuple[int, int]]:
    """Read and validate the exact current bytes at an incident path."""
    record, payload, file_id = _read_incident_file(
        path,
        repository_root=repository_root,
    )
    expected = (
        record.get("configuration_echo")
        if expected_configuration_echo is None
        else expected_configuration_echo
    )
    if not isinstance(expected, Mapping):
        raise ValueError("incident has no configuration echo")
    _validate_anchor_context_incident(
        record,
        path=path,
        expected_configuration_echo=expected,
        repository_root=repository_root,
        production_only=production_only,
    )
    return record, payload, file_id


def validate_anchor_context_incident(
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
) -> Mapping[str, Any]:
    """Read and validate one production incident's exact on-disk bytes."""
    record, _payload, _file_id = _validate_anchor_context_incident_file(
        path=path,
        expected_configuration_echo=expected_configuration_echo,
        repository_root=repository_root,
        production_only=True,
    )
    return record


def _next_incident_path(repository_root: Path) -> tuple[Path, int]:
    runs = repository_root / "runs"
    indices = []
    for path in runs.iterdir():
        if not path.name.startswith(_INCIDENT_PREFIX):
            continue
        match = _INCIDENT_FILENAME.fullmatch(path.name)
        if match is None or path.is_symlink() or not path.is_file():
            raise RuntimeError("existing incident filename is noncanonical")
        indices.append(int(match.group(1)))
    ordered = sorted(indices)
    if ordered != list(range(1, len(ordered) + 1)):
        raise RuntimeError("existing context incidents are not contiguous")
    index = len(ordered) + 1
    return runs / f"{_INCIDENT_PREFIX}{index}.json", index


def _write_anchor_context_incident_for_test(
    *,
    repository_root: str | Path,
    phase: str,
    reason: str,
    reason_detail: str,
    configuration_echo: Mapping[str, Any],
    timestamp_utc: str | None = None,
    production_only: bool = False,
) -> Path:
    """Append one canonical typed incident without a sidecar."""
    root = Path(repository_root).resolve()
    path, index = _next_incident_path(root)
    primary = root / registry.PRIMARY_OUTPUT_PATH
    artifact_path = (
        registry.PRIMARY_OUTPUT_PATH
        if phase == "publication" and primary.is_file()
        else None
    )
    timestamp = timestamp_utc or (
        first_publication.datetime.now(first_publication.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    record = {
        "schema_version": registry.INCIDENT_SCHEMA_VERSION,
        "incident_index": index,
        "timestamp_utc": timestamp,
        "phase": phase,
        "reason": reason,
        "reason_detail": reason_detail,
        "registration_reference": configuration_echo["registration_reference"],
        "configuration_echo": copy.deepcopy(dict(configuration_echo)),
        "artifact_path": artifact_path,
    }
    _validate_anchor_context_incident(
        record,
        path=path,
        expected_configuration_echo=configuration_echo,
        repository_root=root,
        production_only=production_only,
    )
    artifacts.write_new(path, canonical_json_bytes(record))
    return path


def write_anchor_context_incident(
    token: (
        first_publication._RegisteredConfigurationToken
        | _AnchorContextPrecomputeToken
    ),
    *,
    phase: str,
    reason: str,
    reason_detail: str,
) -> Path:
    """Publish an incident from frozen configuration only."""
    registration = (
        token.registration
        if isinstance(token, _AnchorContextPrecomputeToken)
        else token
    )
    if not isinstance(
        registration,
        first_publication._RegisteredConfigurationToken,
    ):
        raise TypeError("incident publication requires a registration token")
    configuration = first_publication._configuration_echo(registration)
    validate_registered_configuration_echo(
        configuration,
        registered_configuration_bytes=registration._configuration_bytes,
    )
    return _write_anchor_context_incident_for_test(
        repository_root=registration._repository_root,
        phase=phase,
        reason=reason,
        reason_detail=reason_detail,
        configuration_echo=configuration,
        production_only=True,
    )


def incident_is_retry_eligible(record: Mapping[str, Any]) -> bool:
    """Return the sole external, pre-output retry classification."""
    return (
        record.get("phase") in {"preparation", "compute"}
        and isinstance(record.get("reason"), str)
        and record["reason"].startswith("external_")
    )


__all__ = [
    "CERTIFIES_NOTHING",
    "EVIDENCE_LABELS",
    "EVIDENTIAL_STATUSES",
    "RUNTIME_PROVENANCE_SCHEMA_VERSION",
    "build_anchor_context_artifact",
    "build_runtime_provenance",
    "canonical_json_bytes",
    "incident_is_retry_eligible",
    "load_fixture_documents",
    "prepare_environment_sidecar",
    "registered_configuration_echo",
    "validate_anchor_context_artifact",
    "validate_anchor_context_incident",
    "validate_environment_sidecar_payload",
    "validate_registered_configuration_echo",
    "write_anchor_context_artifact",
    "write_anchor_context_incident",
]
