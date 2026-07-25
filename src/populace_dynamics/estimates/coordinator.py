"""Sealed coordinator for the registered first-estimates ceremony.

The public entry point has no parameter-bundle, input-factory, sidecar, or
output-path injection.  It derives its repository from the imported estimates
package, durably claims the registration before work begins, freezes the
registered bytes before compute, and writes only that durable claim plus the
artifact pair or an append-only incident record prescribed by the design.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import populace_dynamics.estimates as estimates_package
from populace_dynamics.estimates import publication
from populace_dynamics.estimates.parameters import (
    ParameterDependencyUnavailable,
    load_report_parameters,
)
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
_INPUT_FACTORY_SOURCES = (
    _INPUT_FACTORY_PATH,
    Path("scripts/registered_m6_candidate2_inputs.py"),
    Path("scripts/registered_m6_inputs.py"),
    Path("scripts/build_mortality_floors.py"),
)
_ESTIMATOR_SURFACE_SOURCES = (
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
_INPUT_FACTORY_MODULES = (
    "registered_m6_candidate2_inputs",
    "registered_m6_inputs",
    "build_mortality_floors",
)
_INPUT_FACTORY_CALLABLE = "build_input_plan"
_ATTEMPT_CLAIM_PATH = Path("runs/first_estimates_attempt.claim")
_ATTEMPT_CLAIM_SCHEMA = "first_estimates_attempt.v1"
_ATTEMPT_CLAIM_MAX_BYTES = 4096
_RETRY_CLAIM_PATH = Path("runs/first_estimates_retry.claim")
_RETRY_CLAIM_SCHEMA = "first_estimates_retry.v1"
_PYCACHE_SENTINEL_ENV = "POPULACE_DYNAMICS_FIRST_ESTIMATES_PYCACHE_SENTINEL"
_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_ESTIMATES_PACKAGE_PATH = Path("src/populace_dynamics/estimates/__init__.py")
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

    assert_interpreter: Callable[[], None]
    load_parameters: Callable[[], Any]
    load_input_plan: Callable[[Path], M6Candidate3InputPlan]
    validate_input_sources: Callable[[Path], None]
    resolve_contract: Callable[[Path], Any]
    prepare_sidecar: Callable[[Path], tuple[bytes, str]]
    execute_projection: Callable[..., Any]
    prepare_batch: Callable[..., Any]
    build_artifact: Callable[..., Mapping[str, Any]]
    publish_artifact: Callable[..., Path]
    publish_incident: Callable[..., Path]


def _exception_chain_contains(
    error: BaseException,
    classes: tuple[type[BaseException], ...],
) -> bool:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, classes):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _load_production_parameters() -> Any:
    """Translate only unavailable external parameter dependencies."""
    try:
        return load_report_parameters()
    except ParameterDependencyUnavailable as error:
        raise ExternalPreOutputFailure(
            "external_parameter_bundle_unavailable",
            "Registered parameter dependency unavailable before output.",
        ) from error


def _assert_sealed_interpreter() -> None:
    """Require the isolated, no-write interpreter and its empty cache sentinel."""
    sentinel = os.environ.get(_PYCACHE_SENTINEL_ENV)
    prefix = sys.pycache_prefix
    valid = bool(
        sys.flags.isolated
        and sys.flags.dont_write_bytecode
        and sentinel
        and prefix == sentinel
    )
    if valid:
        path = Path(sentinel)
        try:
            valid = bool(
                path.is_absolute()
                and not path.is_symlink()
                and path.is_dir()
                and not any(path.iterdir())
            )
        except OSError:
            valid = False
    if not valid:
        raise _CeremonyAbort(
            "preparation_unsealed_interpreter_refused",
            (
                "The coordinator requires python -I -B -X "
                "pycache_prefix=<fresh empty sentinel directory>."
            ),
        )


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    root = repository.resolve()
    command = [
        "git",
        "-C",
        str(root),
        f"--git-dir={root / '.git'}",
        *arguments,
    ]
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        command_text = " ".join(command)
        raise RuntimeError(
            f"unable to bind registered input factory with `{command_text}`"
        ) from error


def _assert_git_toplevel(repository: Path) -> Path:
    """Return the canonical root only when Git reports that exact checkout."""
    root = repository.resolve()
    encoded = _git_bytes(root, "rev-parse", "--show-toplevel")
    try:
        reported = os.fsdecode(encoded).strip()
        if not reported:
            raise ValueError("empty Git checkout root")
        git_root = Path(reported).resolve()
    except (OSError, TypeError, ValueError) as error:
        raise RuntimeError(
            "Git returned an invalid checkout root for the estimates package"
        ) from error
    if git_root != root:
        raise RuntimeError(
            "imported estimates package root differs from the Git checkout root"
        )
    return root


def _assert_ordinary_index_flags(repository: Path) -> None:
    """Refuse index entries hidden from ordinary worktree inspection."""
    entries = _git_bytes(repository, "ls-files", "-v", "-z", "--")
    hidden = tuple(
        entry
        for entry in entries.split(b"\0")
        if entry and (entry[:1].islower() or entry.startswith(b"S "))
    )
    if hidden:
        raise RuntimeError(
            "registered first estimates requires tracked files without "
            "assume-unchanged or skip-worktree flags"
        )


def _assert_registered_input_sources(repository: Path) -> None:
    """Bind the wrapper and every sibling module it imports to HEAD bytes."""
    for relative_path in _INPUT_FACTORY_SOURCES:
        relative = relative_path.as_posix()
        path = repository / relative_path
        committed = _git_bytes(repository, "show", f"HEAD:{relative}")
        try:
            working = path.read_bytes()
        except FileNotFoundError as error:
            raise RuntimeError(
                f"registered input source {relative} is absent"
            ) from error
        if working != committed:
            raise RuntimeError(
                f"registered input source {relative} differs from its "
                "committed HEAD blob"
            )


def _assert_no_repository_drift(repository: Path) -> None:
    """Refuse any index or worktree entry in the sealed checkout."""
    repository = _assert_git_toplevel(repository)
    _assert_ordinary_index_flags(repository)
    status = _git_bytes(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status:
        raise RuntimeError(
            "registered first estimates requires an entirely clean "
            "index/worktree"
        )
    ignored = _git_bytes(
        repository,
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
        raise RuntimeError(
            "registered first estimates requires sealed code roots without "
            "ignored executable artifacts"
        )


def _assert_estimator_surface_sources(repository: Path) -> None:
    """Bind every estimator module executed by the ceremony to HEAD bytes."""
    for relative_path in _ESTIMATOR_SURFACE_SOURCES:
        relative = relative_path.as_posix()
        path = repository / relative_path
        committed = _git_bytes(repository, "show", f"HEAD:{relative}")
        try:
            working = path.read_bytes()
        except FileNotFoundError as error:
            raise RuntimeError(
                f"estimator source {relative} is absent"
            ) from error
        if working != committed:
            raise RuntimeError(
                f"estimator source {relative} differs from its committed "
                "HEAD blob"
            )


def _assert_registered_sources(repository: Path) -> None:
    """Seal all tracked files while retaining the recorded HEAD source tuple."""
    _assert_no_repository_drift(repository)
    _assert_estimator_surface_sources(repository)
    _assert_registered_input_sources(repository)


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
    _assert_registered_input_sources(repository)
    path = repository / _INPUT_FACTORY_PATH
    for module_name in _INPUT_FACTORY_MODULES:
        sys.modules.pop(module_name, None)
    module = _load_module(path, path.parent)
    factory = getattr(module, _INPUT_FACTORY_CALLABLE, None)
    if not callable(factory):
        raise RuntimeError("registered input factory callable is absent")
    try:
        plan = factory()
    except BaseException as error:
        if _exception_chain_contains(error, (OSError,)):
            raise ExternalPreOutputFailure(
                "external_registered_input_unavailable",
                "Registered input dependency unavailable before output.",
            ) from error
        raise
    if not isinstance(plan, M6Candidate3InputPlan):
        raise TypeError(
            "registered input factory did not return M6Candidate3InputPlan"
        )

    def load_full_inputs() -> Any:
        try:
            return plan.load_full_inputs()
        except BaseException as error:
            if _exception_chain_contains(error, (OSError,)):
                raise ExternalPreOutputFailure(
                    "external_registered_input_unavailable",
                    "Registered input dependency unavailable before output.",
                ) from error
            raise

    return M6Candidate3InputPlan(
        fit_inputs=plan.fit_inputs,
        load_full_inputs=load_full_inputs,
    )


def _default_operations() -> _CoordinatorOperations:
    return _CoordinatorOperations(
        assert_interpreter=_assert_sealed_interpreter,
        load_parameters=_load_production_parameters,
        load_input_plan=_load_registered_input_plan,
        validate_input_sources=_assert_registered_sources,
        resolve_contract=resolve_report_contract,
        prepare_sidecar=publication.prepare_environment_sidecar,
        execute_projection=execute_first_report_projection,
        prepare_batch=_prepare_first_report_batch,
        build_artifact=_build_prepared_first_estimates_artifact,
        publish_artifact=publication.write_first_estimates_artifact,
        publish_incident=publication.write_first_estimates_incident,
    )


@contextmanager
def _exclusive_ceremony_lock(repository_root: Path) -> Iterator[None]:
    """Serialize all claim, validation, compute, and publication activity."""
    runs = _sealed_runs_directory(repository_root)
    descriptor = os.open(
        runs,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _sealed_runs_directory(repository_root: Path) -> Path:
    """Reject a missing, symlinked, or cross-root canonical runs directory."""
    root = repository_root.resolve()
    runs = root / "runs"
    if runs.is_symlink() or (runs.exists() and runs.resolve() != runs):
        raise _CeremonyAbort(
            "preparation_cross_root_runs_refused",
            "The canonical runs directory escapes the sealed root.",
        )
    if not runs.is_dir():
        raise _CeremonyAbort(
            "preparation_runs_directory_absent",
            "The sealed repository has no canonical runs directory.",
        )
    return runs


def _sealed_repository_root() -> Path:
    """Derive the sole production root from the imported estimates package."""
    package_file = Path(estimates_package.__file__).resolve()
    if len(package_file.parents) < 4:
        raise RuntimeError(
            "imported estimates package has no canonical repository root"
        )
    root = package_file.parents[3]
    if (root / _ESTIMATES_PACKAGE_PATH).resolve() != package_file:
        raise RuntimeError(
            "imported estimates package is outside the canonical src layout"
        )
    return _assert_git_toplevel(root)


def _path_within_root(
    repository_root: Path,
    path: str | Path,
    *,
    label: str,
) -> Path:
    """Resolve a caller path only when it remains inside the sealed root."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as error:
        raise _CeremonyAbort(
            f"preparation_cross_root_{label}_refused",
            f"The {label.replace('_', ' ')} path is outside the sealed root.",
        ) from error
    return resolved


def _attempt_claim_payload(registration_reference: str) -> bytes:
    publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    return publication.canonical_json_bytes(
        {
            "schema_version": _ATTEMPT_CLAIM_SCHEMA,
            "registration_reference": registration_reference,
        }
    )


def _write_attempt_claim_payload(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written == 0:
            raise OSError("attempt claim write made no progress")
        view = view[written:]


def _read_attempt_claim(path: Path) -> Mapping[str, Any] | None:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    nonblocking = getattr(os, "O_NONBLOCK", None)
    if no_follow is None or nonblocking is None:
        return None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | no_follow | nonblocking,
        )
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size > _ATTEMPT_CLAIM_MAX_BYTES
            ):
                return None
            chunks = bytearray()
            while len(chunks) <= _ATTEMPT_CLAIM_MAX_BYTES:
                chunk = os.read(
                    descriptor,
                    _ATTEMPT_CLAIM_MAX_BYTES + 1 - len(chunks),
                )
                if not chunk:
                    break
                chunks.extend(chunk)
            if len(chunks) > _ATTEMPT_CLAIM_MAX_BYTES:
                return None
            payload = bytes(chunks)
        finally:
            os.close(descriptor)
        value = json.loads(payload)
        canonical_payload = publication.canonical_json_bytes(value)
    except (
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
    ):
        return None
    if not isinstance(value, Mapping):
        return None
    if canonical_payload != payload:
        return None
    if set(value) != {"schema_version", "registration_reference"}:
        return None
    if value.get("schema_version") != _ATTEMPT_CLAIM_SCHEMA:
        return None
    if not isinstance(value.get("registration_reference"), str):
        return None
    return value


def _create_attempt_claim(
    repository_root: Path,
    registration_reference: str,
    *,
    allow_matching_retry_claim: bool = False,
) -> Path:
    """Durably claim an attempt or retain its matching retry claim."""
    if not isinstance(registration_reference, str):
        raise TypeError("registration_reference must be a string")
    runs = _sealed_runs_directory(repository_root)
    path = runs / _ATTEMPT_CLAIM_PATH.name
    payload = _attempt_claim_payload(registration_reference)
    if len(payload) > _ATTEMPT_CLAIM_MAX_BYTES:
        raise ValueError("attempt claim payload exceeds its read bound")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o444,
        )
    except FileExistsError:
        existing = _read_attempt_claim(path)
        if (
            existing is not None
            and existing.get("registration_reference")
            == registration_reference
        ):
            if allow_matching_retry_claim:
                return path
            detail = (
                "This registration already has a durable attempt claim; "
                "fresh-registration adjudication is required."
            )
        else:
            detail = (
                "A durable attempt claim already occupies the canonical "
                "path; fresh-registration adjudication must resolve it."
            )
        raise _CeremonyAbort(
            "preparation_fresh_registration_adjudication_required_attempt_claim",
            detail,
        ) from None

    try:
        _write_attempt_claim_payload(descriptor, payload)
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
    return path


def _retry_claim_payload(
    registration_reference: str,
    retry_after_incident: int,
) -> bytes:
    publication._validate_registration_reference_byte_bound(
        registration_reference
    )
    return publication.canonical_json_bytes(
        {
            "schema_version": _RETRY_CLAIM_SCHEMA,
            "registration_reference": registration_reference,
            "retry_after_incident": retry_after_incident,
        }
    )


def _create_retry_claim(
    repository_root: Path,
    registration_reference: str,
    retry_after_incident: int,
) -> Path:
    """Durably and exclusively consume the sole authorized retry."""
    if not isinstance(registration_reference, str):
        raise TypeError("registration_reference must be a string")
    if (
        isinstance(retry_after_incident, bool)
        or not isinstance(retry_after_incident, int)
        or retry_after_incident < 1
    ):
        raise TypeError("retry_after_incident must be a positive integer")
    runs = _sealed_runs_directory(repository_root)
    path = runs / _RETRY_CLAIM_PATH.name
    payload = _retry_claim_payload(
        registration_reference,
        retry_after_incident,
    )
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o444,
        )
    except FileExistsError:
        raise _CeremonyAbort(
            "preparation_fresh_registration_required_retry_claim",
            (
                "The canonical retry-claim path is already occupied; "
                "the sole retry is consumed and fresh registration is "
                "required."
            ),
        ) from None

    try:
        _write_attempt_claim_payload(descriptor, payload)
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
    return path


def _assert_precompute_identity(
    token: publication._PrecomputeToken,
    *,
    expected_contract: Any,
) -> None:
    """Recheck that the frozen environment/contract still names this checkout."""
    root = token._registration._repository_root
    current_contract = publication.ContractRef.current(root)
    if current_contract != expected_contract:
        raise RuntimeError(
            "repository contract identity changed during the ceremony"
        )
    publication.validate_environment_sidecar_payload(
        token._sidecar_payload,
        expected_record={
            "environment": publication.environment_block(),
            "contract": asdict(current_contract),
        },
    )


def _read_incident_history(
    token: publication._RegisteredConfigurationToken,
) -> _IncidentHistory:
    root = token._repository_root
    runs = _sealed_runs_directory(root)
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
    error: BaseException,
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
    error: BaseException,
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    registration = (
        token._registration
        if isinstance(token, publication._PrecomputeToken)
        else token
    )
    _sealed_runs_directory(registration._repository_root)
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


def _bootstrap_registration_token(
    *,
    repository_root: Path,
    registration_reference: str,
) -> publication._RegisteredConfigurationToken:
    """Create a minimal incident token without parsing caller bytes."""
    configuration = {
        "registration_reference": registration_reference,
    }
    return publication._RegisteredConfigurationToken(
        _repository_root=repository_root.resolve(),
        _registration_reference=registration_reference,
        _configuration_bytes=publication.canonical_json_bytes(configuration),
    )


def _upgrade_bootstrap_registration_token(
    token: publication._RegisteredConfigurationToken,
    *,
    registered_configuration_bytes: bytes,
) -> publication._RegisteredConfigurationToken:
    """Preserve a decoded matching-ref echo before exact-byte validation."""
    candidate = json.loads(registered_configuration_bytes)
    if (
        not isinstance(candidate, Mapping)
        or candidate.get("registration_reference")
        != token._registration_reference
    ):
        return token
    return publication._RegisteredConfigurationToken(
        _repository_root=token._repository_root,
        _registration_reference=token._registration_reference,
        _configuration_bytes=publication.canonical_json_bytes(candidate),
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
    root = Path(repository_root).resolve()
    registration = _bootstrap_registration_token(
        repository_root=root,
        registration_reference=registration_reference,
    )
    precompute: publication._PrecomputeToken | None = None
    try:
        registration = _upgrade_bootstrap_registration_token(
            registration,
            registered_configuration_bytes=registered_configuration_bytes,
        )
        registration = publication._parse_registered_configuration(
            repository_root=root,
            registration_reference=registration_reference,
            registered_configuration_bytes=registered_configuration_bytes,
        )
        validate_registered_configuration_echo(
            publication._configuration_echo(registration),
            registered_configuration_bytes=registered_configuration_bytes,
        )
        history = _read_incident_history(registration)
        _authorize_invocation(
            registration,
            history,
            retry_after_incident=retry_after_incident,
        )
        if retry_after_incident is not None:
            _create_retry_claim(
                registration._repository_root,
                registration_reference,
                retry_after_incident,
            )
        operations.validate_input_sources(registration._repository_root)
        contract_ref = publication.ContractRef.current(
            registration._repository_root
        )
        resolved = operations.resolve_contract(registration._repository_root)
        if (
            publication.ContractRef.current(registration._repository_root)
            != contract_ref
        ):
            raise RuntimeError(
                "repository contract identity changed while resolving it"
            )
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
            runtime_provenance=parameters.runtime_provenance,
            sidecar_payload=sidecar_payload,
            prior_incidents=history.paths,
        )
        if sidecar_sha256 != precompute._sidecar_sha256:
            raise ValueError(
                "prepared sidecar digest differs from its frozen bytes"
            )
        _assert_precompute_identity(
            precompute,
            expected_contract=contract_ref,
        )
        input_plan = operations.load_input_plan(registration._repository_root)
    except BaseException as error:
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
    except BaseException as error:
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
            runtime_provenance=publication._runtime_provenance(precompute),
            environment_sidecar_sha256=precompute._sidecar_sha256,
            prior_incidents=precompute._prior_incidents,
        )
    except BaseException as error:
        return _publish_abort(
            precompute,
            phase="invariant",
            error=error,
            operations=operations,
        )

    try:
        _assert_precompute_identity(
            precompute,
            expected_contract=contract_ref,
        )
        _sealed_runs_directory(registration._repository_root)
        operations.validate_input_sources(
            registration._repository_root,
        )
        path = operations.publish_artifact(precompute, artifact)
    except BaseException as error:
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


def _run_registered_first_estimates_from_path_for_test(
    *,
    repository_root: str | Path,
    registration_reference: str,
    registered_configuration_path: str | Path,
    retry_after_incident: int | None,
    operations: _CoordinatorOperations,
) -> CoordinatorResult:
    """Read raw configuration paths only inside incident accounting."""
    root = Path(repository_root).resolve()
    fallback = _bootstrap_registration_token(
        repository_root=root,
        registration_reference=registration_reference,
    )
    try:
        _create_attempt_claim(
            root,
            registration_reference,
            allow_matching_retry_claim=retry_after_incident is not None,
        )
        operations.assert_interpreter()
        path = _path_within_root(
            root,
            registered_configuration_path,
            label="registered_configuration",
        )
        registered_configuration_bytes = path.read_bytes()
    except BaseException as error:
        return _publish_abort(
            fallback,
            phase="preparation",
            error=error,
            operations=operations,
        )
    return _run_registered_first_estimates_for_test(
        repository_root=root,
        registration_reference=registration_reference,
        registered_configuration_bytes=registered_configuration_bytes,
        retry_after_incident=retry_after_incident,
        operations=operations,
    )


def run_registered_first_estimates(
    *,
    registration_reference: str,
    registered_configuration_path: str | Path,
    retry_after_incident: int | None = None,
) -> CoordinatorResult:
    """Run the one-shot ceremony from the imported package's sealed root."""
    root = _sealed_repository_root()
    with _exclusive_ceremony_lock(root):
        return _run_registered_first_estimates_from_path_for_test(
            repository_root=root,
            registration_reference=registration_reference,
            registered_configuration_path=registered_configuration_path,
            retry_after_incident=retry_after_incident,
            operations=_default_operations(),
        )
