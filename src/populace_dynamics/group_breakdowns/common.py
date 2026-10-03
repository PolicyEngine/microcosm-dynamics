"""Refusal and publication guards for registered post hoc breakdowns.

The registration and environment conventions compose the frozen Track A
entry point, ``scripts/run_track_a_registered.py`` (preflight and
``_environment``), without changing it.  A reproduced parent artifact must
match before its adapter loads attributes or computes subgroup cells.

Invariants: comparisons have zero tolerance, including binary64 signed
zero; preflight permits only a new paired artifact under this checkout's
``runs`` directory; publication never overwrites either member of a pair,
and removes only files it created if publication fails.  No helper reads
microdata or computes a measure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POSTHOC_LABELS = (
    "registered, one-shot, post hoc, not blind",
    "report-only",
)
REGISTRATION_POINTER = re.compile(
    r"https://github\.com/PolicyEngine/microcosm-dynamics/issues/42"
    r"#issuecomment-[0-9]+"
)
_ARTIFACT_NAME = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.-]*_groups_posthoc_v1\.json"
)
_ROOT = Path(__file__).resolve().parents[3]


class GroupBreakdownRefusal(ValueError):
    """A required reproduction or registration invariant was not met."""


@dataclass(frozen=True)
class ReproductionCheck:
    """Recorded evidence of complete, exact parent-cell reproduction."""

    compared_leaf_cells: int
    comparison: str = "bit-exact binary64 floats and exact JSON scalars"
    absolute_tolerance: float = 0.0
    relative_tolerance: float = 0.0


@dataclass(frozen=True)
class RegisteredRun:
    """The checked checkout and new output pair bound by a registration."""

    registration_pointer: str
    registered_commit: str
    git_head: str
    git_clean: bool
    output_path: Path
    sidecar_path: Path


def assert_exact_cells(
    committed: Any,
    recomputed: Any,
    *,
    path: str = "cells",
) -> ReproductionCheck:
    """Refuse any changed, missing, extra, or nonfinite JSON cell.

    Dictionary order is immaterial, and tuples have their JSON-array
    semantics.  Scalar types remain exact: ``True``, ``1`` and ``1.0`` are
    distinct.  Finite Python floats are compared by their binary64 bits,
    so even a change from ``0.0`` to ``-0.0`` refuses.  No summation
    tolerance is introduced, and refusal messages expose paths only.
    """

    def refuse(location: str, reason: str = "mismatch") -> None:
        raise GroupBreakdownRefusal(
            f"committed cell {reason} at {location}; no group cells allowed"
        )

    def compare(expected: Any, actual: Any, location: str) -> int:
        if isinstance(expected, Mapping) or isinstance(actual, Mapping):
            if not isinstance(expected, Mapping) or not isinstance(
                actual, Mapping
            ):
                refuse(location)
            if any(not isinstance(key, str) for key in expected):
                refuse(location, "has a non-JSON key")
            if any(not isinstance(key, str) for key in actual):
                refuse(location, "has a non-JSON key")
            if expected.keys() != actual.keys():
                refuse(location, "keys mismatch")
            return sum(
                compare(expected[key], actual[key], f"{location}.{key}")
                for key in expected
            )
        arrays = (list, tuple)
        if isinstance(expected, arrays) or isinstance(actual, arrays):
            if not isinstance(expected, arrays) or not isinstance(
                actual, arrays
            ):
                refuse(location)
            if len(expected) != len(actual):
                refuse(location, "array length mismatch")
            return sum(
                compare(left, right, f"{location}[{index}]")
                for index, (left, right) in enumerate(
                    zip(expected, actual, strict=True)
                )
            )
        if type(expected) is not type(actual):
            refuse(location, "scalar type mismatch")
        if isinstance(expected, float):
            if not math.isfinite(expected) or not math.isfinite(actual):
                refuse(location, "is nonfinite")
            if struct.pack("!d", expected) != struct.pack("!d", actual):
                refuse(location)
        elif expected is None or isinstance(expected, str | bool | int):
            if expected != actual:
                refuse(location)
        else:
            refuse(location, "has a non-JSON value")
        return 1

    return ReproductionCheck(compare(committed, recomputed, path))


def assert_sha256(path: Path, expected_sha256: str) -> str:
    """Refuse to admit pinned non-microdata bytes with a different SHA-256."""

    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise GroupBreakdownRefusal("expected SHA-256 must be full 64-hex")
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise GroupBreakdownRefusal(f"SHA-256 mismatch for {path}")
    return actual


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _exists(path: Path) -> bool:
    """Include dangling symlinks among paths that must not be replaced."""

    return path.exists() or path.is_symlink()


def preflight(
    *,
    registration_pointer: str,
    registered_commit: str,
    output: Path,
    root: Path,
    git: Callable[..., str] | None = None,
) -> RegisteredRun:
    """Check registration, clean HEAD, and new paired paths before reads.

    This verifies the pointer's form locally; it does not retrieve the
    comment or imply that a new real-data run has been authorized.  The
    orchestrator must obtain the issue #42 registration before execution.
    ``git`` is injectable solely to exercise guards on invented data.
    """

    if not REGISTRATION_POINTER.fullmatch(registration_pointer):
        raise GroupBreakdownRefusal(
            "registration pointer must be an issue #42 comment URL"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", registered_commit):
        raise GroupBreakdownRefusal(
            "--registered-commit must be a full 40-hex SHA"
        )
    root = Path(root).resolve()
    if git is None:

        def git(*args: str) -> str:
            return _git(root, *args)

    head = git("rev-parse", "HEAD")
    if head != registered_commit:
        raise GroupBreakdownRefusal(
            "HEAD is not the registered commit; no run allowed"
        )
    if git("status", "--porcelain", "--untracked-files=all") != "":
        raise GroupBreakdownRefusal(
            "working tree must be clean for a registered run"
        )
    runs = root / "runs"
    if runs.is_symlink():
        raise GroupBreakdownRefusal("runs directory must not be a symlink")
    candidate = Path(output)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise GroupBreakdownRefusal("output must not be a symlink")
    candidate = candidate.resolve()
    if candidate.parent != runs.resolve() or not _ARTIFACT_NAME.fullmatch(
        candidate.name
    ):
        raise GroupBreakdownRefusal(
            "output must be runs/<name>_groups_posthoc_v1.json"
        )
    sidecar = candidate.with_suffix(".env.json")
    if _exists(candidate) or _exists(sidecar):
        raise GroupBreakdownRefusal(
            "artifact or environment sidecar already exists: one-shot"
        )
    return RegisteredRun(
        registration_pointer,
        registered_commit,
        head,
        True,
        candidate,
        sidecar,
    )


def environment(
    *,
    ssa_parameters_revision: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Reuse Track A's installed-distribution resolver unchanged.

    Loading the entry-point module through ``importlib`` composes its
    resolver exactly as the frozen FRA-68 and Track M runners do.  The
    registered ``main`` function is never invoked.
    """

    script = (Path(root) if root is not None else _ROOT) / "scripts"
    script = script / "run_track_a_registered.py"
    spec = importlib.util.spec_from_file_location(
        "_group_breakdowns_track_a_registered", script
    )
    if spec is None or spec.loader is None:
        raise GroupBreakdownRefusal("cannot load Track A environment resolver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._environment(ssa_parameters_revision=ssa_parameters_revision)


def write_artifact_pair(
    *,
    output: Path,
    artifact: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> tuple[Path, Path]:
    """Exclusively create artifact and SHA-bound sidecar, or roll back.

    Serialization happens before either file is opened.  On any failure,
    rollback removes only files this invocation created, and only while
    their inode still matches.  An existing artifact or sidecar is never
    changed.  A host interruption can leave an incomplete pair, which
    preflight refuses; publication is not a transactional filesystem.
    """

    output = Path(output)
    sidecar = output.with_suffix(".env.json")
    artifact_text = json.dumps(artifact, indent=2, allow_nan=False) + "\n"
    artifact_sha256 = hashlib.sha256(artifact_text.encode("utf-8")).hexdigest()
    sidecar_text = (
        json.dumps(
            {
                "artifact": output.name,
                "artifact_sha256": artifact_sha256,
                "environment": dict(environment),
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    created: list[tuple[Path, os.stat_result]] = []
    try:
        for path, content in (
            (output, artifact_text),
            (sidecar, sidecar_text),
        ):
            with path.open("x", encoding="utf-8") as handle:
                created.append((path, os.fstat(handle.fileno())))
                handle.write(content)
    except BaseException:
        for path, stat in reversed(created):
            try:
                current = path.lstat()
                if (current.st_dev, current.st_ino) == (
                    stat.st_dev,
                    stat.st_ino,
                ):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise
    return output, sidecar
