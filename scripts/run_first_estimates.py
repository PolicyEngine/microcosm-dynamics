"""One-shot CLI for the registered first-estimates coordinator.

After self-re-execution seals the interpreter, this launcher uses only the
standard library to bind Git to the launcher's repository, require ordinary
tracked-index flags and empty full-porcelain status, and refuse ignored
``__pycache__/``, ``*.pyc``, ``*.pyo``, or ``*.so`` executable artifacts under
``src/`` or ``scripts/`` before adding ``src`` to ``sys.path``.  A failure at
that pre-import boundary is procedural: the coordinator is not yet available
to write an incident, so the launcher prints the documented structured
refusal to stderr and exits nonzero.  The fresh registration must restate all
pre-import checks and their procedural-refusal handling.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_PYCACHE_SENTINEL_ENV = "POPULACE_DYNAMICS_FIRST_ESTIMATES_PYCACHE_SENTINEL"
_PYCACHE_SENTINEL_PREFIX = "populace-first-estimates-pycache-"
_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_PRE_IMPORT_REFUSAL_REASON = "preparation_pre_import_repository_guard_refused"


def _sealed_pycache_sentinel() -> Path | None:
    """Return the launcher's empty cache sentinel only under all three flags."""
    sentinel = os.environ.get(_PYCACHE_SENTINEL_ENV)
    prefix = sys.pycache_prefix
    if (
        not sys.flags.isolated
        or not sys.flags.dont_write_bytecode
        or not sentinel
        or prefix != sentinel
    ):
        return None
    path = Path(sentinel)
    try:
        if (
            not path.is_absolute()
            or path.is_symlink()
            or not path.is_dir()
            or any(path.iterdir())
        ):
            return None
    except OSError:
        return None
    return path


def _seal_interpreter() -> Path:
    """Replace an unsealed launcher with an isolated cache-miss interpreter."""
    sealed = _sealed_pycache_sentinel()
    if sealed is not None:
        return sealed

    sentinel = Path(
        tempfile.mkdtemp(prefix=_PYCACHE_SENTINEL_PREFIX)
    ).resolve()
    os.environ[_PYCACHE_SENTINEL_ENV] = str(sentinel)
    arguments = [
        sys.executable,
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={sentinel}",
        str(Path(__file__).resolve()),
        *sys.argv[1:],
    ]
    try:
        os.execv(sys.executable, arguments)
    except BaseException:
        try:
            sentinel.rmdir()
        except OSError:
            pass
        raise
    raise RuntimeError("sealed interpreter exec unexpectedly returned")


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    """Run one pre-import Git query without importing repository code."""
    import subprocess

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
        raise RuntimeError(
            "registered first estimates could not complete the pre-import "
            "repository guard"
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
            "Git returned an invalid checkout root for the pre-import guard"
        ) from error
    if git_root != root:
        raise RuntimeError(
            "launcher repository root differs from the Git checkout root"
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


def _assert_pre_import_repository_guard(repository: Path) -> None:
    """Refuse tracked drift, untracked files, and ignored executables."""
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


def _print_pre_import_refusal(error: RuntimeError) -> None:
    """Emit the procedural refusal that substitutes for an incident."""
    print(
        json.dumps(
            {
                "path": None,
                "phase": "preparation",
                "reason": _PRE_IMPORT_REFUSAL_REASON,
                "reason_detail": str(error),
                "status": "procedural_refusal",
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )


def _run_coordinator(**arguments):
    """Import reviewed repository code only after the interpreter is sealed."""
    source = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(source))
    from populace_dynamics.estimates.coordinator import (
        run_registered_first_estimates,
    )

    return run_registered_first_estimates(**arguments)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the registered first-estimates ceremony at its canonical "
            "repository output path."
        )
    )
    parser.add_argument(
        "--registration-reference",
        required=True,
        help="Fresh issue/comment registration identifier.",
    )
    parser.add_argument(
        "--registered-configuration",
        type=Path,
        required=True,
        help="File containing the exact canonical registered JSON bytes.",
    )
    parser.add_argument(
        "--retry-after-incident",
        type=int,
        help="Explicit sole retry-eligible incident index.",
    )
    return parser.parse_args()


def main() -> int:
    _seal_interpreter()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    repository = Path(__file__).resolve().parents[1]
    try:
        _assert_pre_import_repository_guard(repository)
    except RuntimeError as error:
        _print_pre_import_refusal(error)
        return 1
    args = _arguments()
    result = _run_coordinator(
        registration_reference=args.registration_reference,
        registered_configuration_path=args.registered_configuration,
        retry_after_incident=args.retry_after_incident,
    )
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
