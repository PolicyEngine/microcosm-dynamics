"""Sealed fixture-only rehearsal for the anchor-context ceremony.

The public entry point accepts no paths or identities.  It verifies one
committed fixture manifest, copies only those two hash-pinned fixtures into
fresh private repositories, and runs the real ceremony machinery there.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from populace_dynamics.estimates import (
    anchor_context_coordinator as coordinator,
)
from populace_dynamics.estimates import (
    anchor_context_publication as publication,
)
from populace_dynamics.estimates import anchor_context_registry as registry
from populace_dynamics.estimates import anchor_context_report as report

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = (
    _REPOSITORY_ROOT / "scripts/rehearse_anchor_context_report.py"
).resolve()
_MANIFEST_PATH = Path("tests/fixtures/anchor_context/manifest_v1.json")
_MANIFEST_SHA256 = (
    "6da0708b3ae070c2524dd1522a4771bec1cbd982b03cd58a45a3ae72e3bdcc27"
)
_FIRST_FIXTURE_PATH = (
    "tests/fixtures/anchor_context/first_estimates_fixture_v1.json"
)
_FIRST_FIXTURE_SHA256 = (
    "be95a6eef919d2cf46197467fd75463d2c94d607983674da9f2723b0391d1c61"
)
_ANCHOR_FIXTURE_PATH = (
    "tests/fixtures/anchor_context/ssa_level_anchors_fixture_v1.json"
)
_ANCHOR_FIXTURE_SHA256 = (
    "0a473202440878e66201f60fbd76a686d22b77a2b0fd64fefb3b88bcc55f2ac4"
)
_ANCHOR_FIXTURE_VINTAGE = "ssa_level_anchors.fixture_only.v1"
_MANIFEST_SCHEMA = "anchor_context_fixture_manifest.fixture_only.v1"
_PRIVATE_CONTRACT_BYTES = b"fixture_only: true\n"
_PRIVATE_GITIGNORE_BYTES = (
    b"runs/anchor_context_report_attempt.claim\n"
    b"runs/anchor_context_report_retry.claim\n"
    b"runs/anchor_context_report_incident_*.json\n"
)
_SUCCESS_REFERENCE = "anchor-context-fixture-rehearsal-success"
_INCIDENT_REFERENCE = "anchor-context-fixture-rehearsal-incident"
_PASSED_CHECKS = (
    "fixed_fixture_identity_gate",
    "success_ceremony_and_validators",
    "canonical_sidecar_publication",
    "typed_incident_publication",
    "private_root_cleanup",
)


class FixtureRehearsalError(RuntimeError):
    """A non-estimate-bearing fixture rehearsal failure."""


class _ExpectedIncidentProbe(RuntimeError):
    """Intentional compute failure used to exercise typed incidents."""


@dataclass(frozen=True)
class RehearsalResult:
    """Pass/fail metadata containing no fixture statistic."""

    status: Literal["passed"]
    checks: tuple[str, ...]


def _expected_manifest() -> dict[str, Any]:
    return {
        "fixture_only": True,
        "inputs": [
            {
                "path": _FIRST_FIXTURE_PATH,
                "role": "first_estimates",
                "sha256": _FIRST_FIXTURE_SHA256,
            },
            {
                "path": _ANCHOR_FIXTURE_PATH,
                "role": "anchor",
                "sha256": _ANCHOR_FIXTURE_SHA256,
            },
        ],
        "schema_version": _MANIFEST_SCHEMA,
    }


def _fixed_fixture_identities() -> tuple[dict[str, str], dict[str, str]]:
    """Return fresh copies of the only identities admitted by rehearsal."""
    return (
        {
            "path": _FIRST_FIXTURE_PATH,
            "sha256": _FIRST_FIXTURE_SHA256,
        },
        {
            "path": _ANCHOR_FIXTURE_PATH,
            "artifact_vintage_id": _ANCHOR_FIXTURE_VINTAGE,
            "sha256": _ANCHOR_FIXTURE_SHA256,
        },
    )


def _assert_rehearsal_identities(
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    """Reject production and any non-fixed identity before an input read."""
    publication._assert_fixture_identities(
        first_estimates_input,
        anchor_input,
    )
    expected_first, expected_anchor = _fixed_fixture_identities()
    if dict(first_estimates_input) != expected_first:
        raise ValueError("rehearsal first-estimates identity is not fixed")
    if dict(anchor_input) != expected_anchor:
        raise ValueError("rehearsal anchor identity is not fixed")


def _load_committed_manifest(
    repository_root: Path = _REPOSITORY_ROOT,
) -> tuple[Mapping[str, Any], bytes]:
    """Read and exact-check the nonproduction manifest, never an input."""
    root = Path(repository_root)
    path = _sealed_fixture_source(root, _MANIFEST_PATH.as_posix())
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _MANIFEST_SHA256:
        raise FixtureRehearsalError("fixture manifest hash changed")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FixtureRehearsalError("fixture manifest is invalid") from error
    if not isinstance(document, Mapping):
        raise FixtureRehearsalError("fixture manifest is not an object")
    if publication.canonical_json_bytes(document) != raw:
        raise FixtureRehearsalError("fixture manifest is not canonical")
    if document != _expected_manifest():
        raise FixtureRehearsalError("fixture manifest content changed")
    return document, raw


def _identities_from_manifest(
    manifest: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    by_role = {
        row["role"]: row
        for row in manifest["inputs"]
        if isinstance(row, Mapping)
    }
    first = {
        "path": by_role["first_estimates"]["path"],
        "sha256": by_role["first_estimates"]["sha256"],
    }
    anchor = {
        "path": by_role["anchor"]["path"],
        "artifact_vintage_id": _ANCHOR_FIXTURE_VINTAGE,
        "sha256": by_role["anchor"]["sha256"],
    }
    _assert_rehearsal_identities(first, anchor)
    return first, anchor


def _git(repository_root: Path, *arguments: str) -> bytes:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }
    try:
        return subprocess.run(
            ["git", "-C", str(repository_root), *arguments],
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise FixtureRehearsalError(
            "private fixture repository setup failed"
        ) from error


def _sealed_fixture_source(source_root: Path, relative_path: str) -> Path:
    """Resolve one fixed fixture without following a source-tree symlink."""
    root = Path(source_root)
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise FixtureRehearsalError(
            "fixture source root is unavailable"
        ) from error
    if root.is_symlink() or resolved_root != root:
        raise FixtureRehearsalError("fixture source root resolution drifted")

    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise FixtureRehearsalError("fixture source path is not relative")
    source = root
    for component in relative.parts:
        source /= component
        if source.is_symlink():
            raise FixtureRehearsalError(
                "fixture source path contains a symlink"
            )
    try:
        resolved_source = source.resolve(strict=True)
    except OSError as error:
        raise FixtureRehearsalError("fixture source is unavailable") from error
    expected_source = resolved_root / relative
    if resolved_source != expected_source or not source.is_file():
        raise FixtureRehearsalError("fixture source resolution drifted")
    return source


def _populate_private_root(
    *,
    source_root: Path,
    private_root: Path,
    manifest_bytes: bytes,
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> str:
    """Create one clean private Git root after the identity-only gate."""
    _assert_rehearsal_identities(first_estimates_input, anchor_input)
    private_root.mkdir(parents=True, exist_ok=True)

    manifest_target = private_root / _MANIFEST_PATH
    manifest_target.parent.mkdir(parents=True)
    manifest_target.write_bytes(manifest_bytes)
    for identity in (first_estimates_input, anchor_input):
        relative = Path(identity["path"])
        source = _sealed_fixture_source(source_root, identity["path"])
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != identity["sha256"]:
            raise FixtureRehearsalError("fixed fixture hash changed")
        target = private_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    (private_root / "gates.yaml").write_bytes(_PRIVATE_CONTRACT_BYTES)
    (private_root / ".gitignore").write_bytes(_PRIVATE_GITIGNORE_BYTES)
    (private_root / "runs").mkdir()
    _git(private_root, "init", "-q")
    _git(
        private_root,
        "add",
        "--",
        ".gitignore",
        "gates.yaml",
        _MANIFEST_PATH.as_posix(),
        first_estimates_input["path"],
        anchor_input["path"],
    )
    _git(
        private_root,
        "-c",
        "user.name=Anchor Context Rehearsal",
        "-c",
        "user.email=fixture-rehearsal@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-verify",
        "-qm",
        "fixture-only rehearsal root",
    )
    return os.fsdecode(_git(private_root, "rev-parse", "HEAD")).strip()


@contextmanager
def _private_repository(
    *,
    manifest_bytes: bytes,
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
):
    with tempfile.TemporaryDirectory(
        prefix="anchor-context-fixture-rehearsal-"
    ) as directory:
        root = Path(directory).resolve()
        implementation_commit = _populate_private_root(
            source_root=_REPOSITORY_ROOT,
            private_root=root,
            manifest_bytes=manifest_bytes,
            first_estimates_input=first_estimates_input,
            anchor_input=anchor_input,
        )
        yield root, implementation_commit


def _assert_rehearsal_interpreter(
    configuration: Mapping[str, Any],
    actual_invocation: Sequence[str],
) -> None:
    """Require this no-argument script under the exact isolated flags."""
    actual = list(actual_invocation)
    if configuration["invocation"] != actual:
        raise FixtureRehearsalError("rehearsal invocation bytes changed")
    if (
        len(actual) != 6
        or actual[1:4] != ["-I", "-B", "-X"]
        or not actual[4].startswith("pycache_prefix=")
        or Path(actual[5]).resolve() != _SCRIPT_PATH
    ):
        raise FixtureRehearsalError("rehearsal invocation is not canonical")
    sentinel_literal = actual[4].removeprefix("pycache_prefix=")
    if (
        not sys.flags.isolated
        or not sys.flags.dont_write_bytecode
        or sys.pycache_prefix != sentinel_literal
    ):
        raise FixtureRehearsalError("rehearsal interpreter is not sealed")
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
        raise FixtureRehearsalError("rehearsal pycache sentinel is not empty")


def _load_fixture_inputs(registration_token):
    if not isinstance(
        registration_token,
        publication.first_publication._RegisteredConfigurationToken,
    ):
        raise TypeError("fixture rehearsal requires its registration token")
    configuration = publication.first_publication._configuration_echo(
        registration_token
    )
    _assert_rehearsal_identities(
        configuration["first_estimates_input"],
        configuration["anchor_input"],
    )
    return publication.load_fixture_documents(
        registration_token._repository_root
    )


def _fixture_operations(*, incident_probe: bool):
    operations = coordinator._default_operations()

    def build_fixture_results(_registration, loaded_inputs):
        return report.build_results(loaded_inputs)

    def validate_fixture_results(
        _registration,
        results,
        loaded_inputs,
    ):
        report.validate_results(
            results,
            fixture_inputs=loaded_inputs,
        )

    def fail_compute(_registration, _loaded_inputs):
        raise _ExpectedIncidentProbe("typed incident rehearsal probe")

    def publish_fixture_artifact(
        token,
        artifact,
        *,
        input_bundle,
        ceremony_capability,
    ):
        if ceremony_capability is not None:
            raise TypeError("fixture publication rejects production authority")
        configuration = publication.first_publication._configuration_echo(
            token.registration
        )
        return publication._write_anchor_context_artifact_for_test(
            repository_root=token.registration._repository_root,
            artifact=artifact,
            expected_configuration_echo=configuration,
            expected_runtime_provenance=publication._runtime_provenance(token),
            expected_prior_incidents=token.prior_incidents,
            input_bundle=input_bundle,
            sidecar_payload=token.sidecar_payload,
        )

    def publish_fixture_incident(
        token,
        *,
        phase: str,
        reason: str,
        reason_detail: str,
    ):
        registration = (
            token.registration
            if isinstance(token, publication._AnchorContextPrecomputeToken)
            else token
        )
        configuration = publication.first_publication._configuration_echo(
            registration
        )
        return publication._write_anchor_context_incident_for_test(
            repository_root=registration._repository_root,
            phase=phase,
            reason=reason,
            reason_detail=reason_detail,
            configuration_echo=configuration,
            production_only=False,
        )

    return replace(
        operations,
        assert_interpreter=_assert_rehearsal_interpreter,
        load_inputs=_load_fixture_inputs,
        build_results=(
            fail_compute if incident_probe else build_fixture_results
        ),
        validate_results=validate_fixture_results,
        publish_artifact=publish_fixture_artifact,
        publish_incident=publish_fixture_incident,
    )


def _configuration(
    *,
    registration_reference: str,
    implementation_commit: str,
    invocation: Sequence[str],
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> dict[str, Any]:
    return publication._registered_configuration_echo_for_test(
        registration_reference=registration_reference,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )


def _run_success_ceremony(
    *,
    root: Path,
    implementation_commit: str,
    invocation: Sequence[str],
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    configuration = _configuration(
        registration_reference=_SUCCESS_REFERENCE,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )
    registered_bytes = publication.canonical_json_bytes(configuration)
    publication._validate_fixture_configuration_echo(
        configuration,
        registered_configuration_bytes=registered_bytes,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )
    result = coordinator._run_registered_anchor_context_for_test(
        repository_root=root,
        registered_configuration_bytes=registered_bytes,
        actual_invocation=invocation,
        operations=_fixture_operations(incident_probe=False),
    )
    expected_primary = root / registry.PRIMARY_OUTPUT_PATH
    expected_sidecar = root / registry.SIDECAR_OUTPUT_PATH
    if (
        result.status != "published"
        or result.path != expected_primary
        or not expected_primary.is_file()
        or not expected_sidecar.is_file()
    ):
        raise FixtureRehearsalError("fixture success ceremony did not publish")

    fixture_inputs = publication.load_fixture_documents(root)
    artifact_raw = expected_primary.read_bytes()
    sidecar_raw = expected_sidecar.read_bytes()
    artifact = json.loads(artifact_raw)
    if publication.canonical_json_bytes(artifact) != artifact_raw:
        raise FixtureRehearsalError("fixture primary is not canonical")
    publication.validate_environment_sidecar_payload(sidecar_raw)
    runtime_provenance = publication.build_runtime_provenance(
        implementation_commit
    )
    publication.validate_anchor_context_artifact(
        artifact,
        expected_configuration_echo=configuration,
        expected_runtime_provenance=runtime_provenance,
        input_bundle=fixture_inputs,
    )


def _run_incident_ceremony(
    *,
    root: Path,
    implementation_commit: str,
    invocation: Sequence[str],
    first_estimates_input: Mapping[str, Any],
    anchor_input: Mapping[str, Any],
) -> None:
    configuration = _configuration(
        registration_reference=_INCIDENT_REFERENCE,
        implementation_commit=implementation_commit,
        invocation=invocation,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    )
    registered_bytes = publication.canonical_json_bytes(configuration)
    result = coordinator._run_registered_anchor_context_for_test(
        repository_root=root,
        registered_configuration_bytes=registered_bytes,
        actual_invocation=invocation,
        operations=_fixture_operations(incident_probe=True),
    )
    if result.status != "incident" or result.phase != "compute":
        raise FixtureRehearsalError("fixture incident ceremony did not abort")
    if (root / registry.PRIMARY_OUTPUT_PATH).exists() or (
        root / registry.SIDECAR_OUTPUT_PATH
    ).exists():
        raise FixtureRehearsalError("fixture incident emitted a report pair")
    raw = result.path.read_bytes()
    record = json.loads(raw)
    if publication.canonical_json_bytes(record) != raw:
        raise FixtureRehearsalError("fixture incident is not canonical")
    publication._validate_anchor_context_incident(
        record,
        path=result.path,
        expected_configuration_echo=configuration,
        repository_root=root,
        production_only=False,
    )


def run_fixture_rehearsal() -> RehearsalResult:
    """Run success and typed-incident ceremonies using fixed fixtures only."""
    invocation = list(getattr(sys, "orig_argv", ()))
    _assert_rehearsal_interpreter({"invocation": invocation}, invocation)
    manifest, manifest_bytes = _load_committed_manifest()
    first_estimates_input, anchor_input = _identities_from_manifest(manifest)

    success_root: Path | None = None
    with _private_repository(
        manifest_bytes=manifest_bytes,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    ) as (root, implementation_commit):
        success_root = root
        _run_success_ceremony(
            root=root,
            implementation_commit=implementation_commit,
            invocation=invocation,
            first_estimates_input=first_estimates_input,
            anchor_input=anchor_input,
        )
    if success_root is None or success_root.exists():
        raise FixtureRehearsalError("fixture success root was not removed")

    incident_root: Path | None = None
    with _private_repository(
        manifest_bytes=manifest_bytes,
        first_estimates_input=first_estimates_input,
        anchor_input=anchor_input,
    ) as (root, implementation_commit):
        incident_root = root
        _run_incident_ceremony(
            root=root,
            implementation_commit=implementation_commit,
            invocation=invocation,
            first_estimates_input=first_estimates_input,
            anchor_input=anchor_input,
        )
    if incident_root is None or incident_root.exists():
        raise FixtureRehearsalError("fixture incident root was not removed")

    return RehearsalResult(status="passed", checks=_PASSED_CHECKS)


__all__ = ["RehearsalResult", "run_fixture_rehearsal"]
