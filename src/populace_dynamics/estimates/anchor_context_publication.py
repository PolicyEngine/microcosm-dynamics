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
from collections.abc import Mapping, Sequence
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


@dataclass(frozen=True)
class _AnchorContextPrecomputeToken:
    """Opaque publication authority frozen before report computation."""

    registration: first_publication._RegisteredConfigurationToken
    runtime_provenance_bytes: bytes
    sidecar_payload: bytes
    sidecar_sha256: str
    prior_incidents: tuple[str, ...]


_VERIFIED_INPUT_AUTHORITY = object()


@dataclass(frozen=True, init=False)
class _VerifiedProductionInputs:
    """Opaque result of both registered production hash gates."""

    registration: first_publication._RegisteredConfigurationToken
    first_estimates: Mapping[str, Any]
    anchors: Mapping[str, Any]
    first_estimates_snapshot: bytes
    anchors_snapshot: bytes

    def __init__(
        self,
        authority: object,
        *,
        registration: first_publication._RegisteredConfigurationToken,
        first_estimates: Mapping[str, Any],
        anchors: Mapping[str, Any],
    ):
        if authority is not _VERIFIED_INPUT_AUTHORITY:
            raise TypeError(
                "verified production inputs are created only by the hash gate"
            )
        object.__setattr__(self, "registration", registration)
        object.__setattr__(self, "first_estimates", first_estimates)
        object.__setattr__(self, "anchors", anchors)
        object.__setattr__(
            self,
            "first_estimates_snapshot",
            canonical_json_bytes(first_estimates),
        )
        object.__setattr__(
            self,
            "anchors_snapshot",
            canonical_json_bytes(anchors),
        )


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


def _load_verified_json(
    repository_root: str | Path,
    identity: Mapping[str, Any],
    *,
    role: str,
) -> Mapping[str, Any]:
    """Hash exact bytes before deserializing one registered JSON input."""
    root = Path(repository_root).resolve()
    validated = _validate_input_identity(identity, role=role)
    path = root / validated["path"]
    if path.is_symlink():
        raise ValueError(f"{role} input must not be a symlink")
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{role} input escapes the repository") from error
    raw = resolved.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != validated["sha256"]:
        raise ValueError(f"{role} input sha256 differs from registration")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{role} input is not valid JSON") from error
    value = _require_mapping(document, f"{role} input")
    if role == "anchor" and value.get("artifact_vintage_id") != (
        validated["artifact_vintage_id"]
    ):
        raise ValueError("anchor input vintage differs from registration")
    return value


def _assert_fixture_identities(
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    first = _validate_input_identity(
        first_estimates_input,
        role="first_estimates",
    )
    anchor = _validate_input_identity(anchor_input, role="anchor")
    production_paths = {
        registry.FIRST_ESTIMATES_INPUT_PATH,
        registry.ANCHOR_INPUT_PATH,
    }
    production_hashes = {
        registry.FIRST_ESTIMATES_INPUT_SHA256,
        registry.ANCHOR_INPUT_SHA256,
    }
    if first["path"] in production_paths or anchor["path"] in production_paths:
        raise ValueError("fixture rehearsal rejects production input paths")
    if (
        first["sha256"] in production_hashes
        or anchor["sha256"] in production_hashes
    ):
        raise ValueError("fixture rehearsal rejects production input hashes")
    if anchor["artifact_vintage_id"] == registry.ANCHOR_ARTIFACT_VINTAGE_ID:
        raise ValueError("fixture rehearsal rejects the production vintage")


def load_fixture_documents(
    repository_root: str | Path,
    *,
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Load only identities structurally disjoint from both production inputs."""
    _assert_fixture_identities(first_estimates_input, anchor_input)
    first = _load_verified_json(
        repository_root,
        first_estimates_input,
        role="first_estimates",
    )
    anchor = _load_verified_json(
        repository_root,
        anchor_input,
        role="anchor",
    )
    if first.get("fixture_only") is not True:
        raise ValueError("first-estimates rehearsal input is not fixture-only")
    if anchor.get("fixture_only") is not True:
        raise ValueError("anchor rehearsal input is not fixture-only")
    return first, anchor


def _load_production_documents(
    token: first_publication._RegisteredConfigurationToken,
) -> _VerifiedProductionInputs:
    if not isinstance(token, first_publication._RegisteredConfigurationToken):
        raise TypeError(
            "production input loading requires a registration token"
        )
    configuration = first_publication._configuration_echo(token)
    validate_registered_configuration_echo(
        configuration,
        registered_configuration_bytes=token._configuration_bytes,
    )
    first = _load_verified_json(
        token._repository_root,
        configuration["first_estimates_input"],
        role="first_estimates",
    )
    anchor = _load_verified_json(
        token._repository_root,
        configuration["anchor_input"],
        role="anchor",
    )
    return _VerifiedProductionInputs(
        _VERIFIED_INPUT_AUTHORITY,
        registration=token,
        first_estimates=first,
        anchors=anchor,
    )


def _validate_environment_sidecar_hash(value: Any) -> str:
    return _sha256(value, "environment sidecar sha256")


def _validate_artifact_input_binding(
    configuration: Mapping[str, Any],
    *,
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
    verified_production_inputs: _VerifiedProductionInputs | None,
) -> None:
    production = (
        configuration["first_estimates_input"]
        == registry.first_estimates_input_identity()
        and configuration["anchor_input"] == registry.anchor_input_identity()
    )
    if production:
        if not isinstance(
            verified_production_inputs,
            _VerifiedProductionInputs,
        ):
            raise TypeError(
                "production artifact validation requires hash-gated inputs"
            )
        registered_configuration = first_publication._configuration_echo(
            verified_production_inputs.registration
        )
        _assert_exact_json(
            registered_configuration,
            configuration,
            "verified_inputs.configuration_echo",
        )
        if (
            first_estimates is not verified_production_inputs.first_estimates
            or anchors is not verified_production_inputs.anchors
        ):
            raise ValueError(
                "production artifact inputs differ from hash-gated documents"
            )
        if canonical_json_bytes(first_estimates) != (
            verified_production_inputs.first_estimates_snapshot
        ):
            raise ValueError(
                "first-estimates input mutated after its production hash gate"
            )
        if canonical_json_bytes(anchors) != (
            verified_production_inputs.anchors_snapshot
        ):
            raise ValueError(
                "anchor input mutated after its production hash gate"
            )
        return
    if verified_production_inputs is not None:
        raise TypeError("fixture artifacts cannot carry production authority")
    first_input = _require_mapping(
        configuration["first_estimates_input"],
        "fixture artifact first_estimates_input",
    )
    anchor_input = _require_mapping(
        configuration["anchor_input"],
        "fixture artifact anchor_input",
    )
    _assert_fixture_identities(first_input, anchor_input)
    if first_estimates.get("fixture_only") is not True:
        raise ValueError(
            "fixture artifact first-estimates input is not fixture"
        )
    if anchors.get("fixture_only") is not True:
        raise ValueError("fixture artifact anchor input is not fixture")


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
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
    environment_sidecar_sha256: str,
    prior_incidents: Sequence[str] = (),
    verified_production_inputs: _VerifiedProductionInputs | None = None,
) -> dict[str, Any]:
    """Assemble the complete integrity-bound primary report."""
    configuration = copy.deepcopy(dict(configuration_echo))
    _validate_configuration_echo_for_execution(configuration)
    _validate_artifact_input_binding(
        configuration,
        first_estimates=first_estimates,
        anchors=anchors,
        verified_production_inputs=verified_production_inputs,
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
        verified_production_inputs=verified_production_inputs,
        first_estimates=first_estimates,
        anchors=anchors,
    )
    return artifact


def validate_anchor_context_artifact(
    artifact: Mapping[str, Any],
    *,
    expected_configuration_echo: Mapping[str, Any],
    expected_runtime_provenance: Mapping[str, Any],
    expected_prior_incidents: Sequence[str] = (),
    verified_production_inputs: _VerifiedProductionInputs | None = None,
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
) -> None:
    """Validate every report field and independently recompute all results."""
    value = _require_mapping(artifact, "artifact")
    _require_exact_keys(value, _ARTIFACT_KEYS, "artifact")
    if value["schema_version"] != registry.REPORT_SCHEMA_VERSION:
        raise ValueError("anchor-context artifact schema changed")
    if value["configuration_echo"] != expected_configuration_echo:
        raise ValueError("artifact configuration echo changed")
    _validate_configuration_echo_for_execution(value["configuration_echo"])
    _validate_artifact_input_binding(
        value["configuration_echo"],
        first_estimates=first_estimates,
        anchors=anchors,
        verified_production_inputs=verified_production_inputs,
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
    anchor_context_report.validate_results(
        value["results"],
        first_estimates=first_estimates,
        anchors=anchors,
    )
    canonical_json_bytes(value)


def _write_anchor_context_artifact_for_test(
    *,
    repository_root: str | Path,
    artifact: Mapping[str, Any],
    expected_configuration_echo: Mapping[str, Any],
    expected_runtime_provenance: Mapping[str, Any],
    expected_prior_incidents: Sequence[str] = (),
    verified_production_inputs: _VerifiedProductionInputs | None = None,
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
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
        verified_production_inputs=verified_production_inputs,
        first_estimates=first_estimates,
        anchors=anchors,
    )
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
    first_estimates: Mapping[str, Any],
    anchors: Mapping[str, Any],
    verified_production_inputs: _VerifiedProductionInputs | None = None,
) -> Path:
    """Publish only through the opaque precompute token."""
    if not isinstance(token, _AnchorContextPrecomputeToken):
        raise TypeError("publication requires an anchor precompute token")
    configuration = first_publication._configuration_echo(token.registration)
    return _write_anchor_context_artifact_for_test(
        repository_root=token.registration._repository_root,
        artifact=artifact,
        expected_configuration_echo=configuration,
        expected_runtime_provenance=_runtime_provenance(token),
        expected_prior_incidents=token.prior_incidents,
        verified_production_inputs=verified_production_inputs,
        first_estimates=first_estimates,
        anchors=anchors,
        sidecar_payload=token.sidecar_payload,
    )


def _validate_anchor_context_incident(
    record: Mapping[str, Any],
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
    validate_artifact_existence: bool = True,
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
    if validate_artifact_existence:
        expected_path = (
            registry.PRIMARY_OUTPUT_PATH
            if value["phase"] == "publication" and partial_exists
            else None
        )
        if artifact_path != expected_path:
            raise ValueError(
                "artifact_path must be non-null iff publication partial exists"
            )
    elif artifact_path is not None and (
        value["phase"] != "publication"
        or artifact_path != registry.PRIMARY_OUTPUT_PATH
    ):
        raise ValueError("artifact_path violates the publication iff rule")
    _, next_index = _next_incident_path(root)
    if incident_path.exists():
        if index >= next_index:
            raise ValueError("incident path is outside contiguous history")
    elif index != next_index:
        raise ValueError("incident index is not the next contiguous suffix")
    canonical_json_bytes(value)


def validate_anchor_context_incident(
    record: Mapping[str, Any],
    *,
    path: str | Path,
    expected_configuration_echo: Mapping[str, Any],
    repository_root: str | Path,
    validate_artifact_existence: bool = True,
) -> None:
    """Validate one production incident and its exact registered echo."""
    _validate_anchor_context_incident(
        record,
        path=path,
        expected_configuration_echo=expected_configuration_echo,
        repository_root=repository_root,
        validate_artifact_existence=validate_artifact_existence,
        production_only=True,
    )


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
