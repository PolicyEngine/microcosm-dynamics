"""Canonical isolated launcher for the registered anchor-context report."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_IGNORED_EXECUTABLE_SUFFIXES = (b".pyc", b".pyo", b".so")
_PRE_IMPORT_REFUSAL_REASON = "preparation_pre_import_guard_refused"


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
        raise RuntimeError(
            "Git could not verify the pre-import report checkout"
        ) from error


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


def _print_pre_import_refusal(error: RuntimeError) -> None:
    print(
        json.dumps(
            {
                "status": "procedural_refusal",
                "path": None,
                "phase": "preparation",
                "reason": _PRE_IMPORT_REFUSAL_REASON,
                "reason_detail": str(error),
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
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
        _print_pre_import_refusal(error)
        return 1
    result = _run_coordinator(args.registration)
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
