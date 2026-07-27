"""No-argument sealed launcher for the fixture-only context rehearsal."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _metadata(status: str, reason: str | None = None, checks=()):
    result = {"status": status}
    if reason is not None:
        result["reason"] = reason
    if checks:
        result["checks"] = list(checks)
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def _assert_pre_import_seal() -> None:
    actual = list(getattr(sys, "orig_argv", ()))
    if (
        len(sys.argv) != 1
        or len(actual) != 6
        or actual[1:4] != ["-I", "-B", "-X"]
        or not actual[4].startswith("pycache_prefix=")
        or Path(actual[5]).resolve() != Path(__file__).resolve()
    ):
        raise RuntimeError("noncanonical invocation")
    sentinel_literal = actual[4].removeprefix("pycache_prefix=")
    if (
        not sys.flags.isolated
        or not sys.flags.dont_write_bytecode
        or sys.pycache_prefix != sentinel_literal
    ):
        raise RuntimeError("unsealed interpreter")
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
        raise RuntimeError("nonempty pycache sentinel")


def main() -> int:
    try:
        _assert_pre_import_seal()
    except RuntimeError:
        print(
            _metadata(
                "refused",
                reason="unsealed_or_noncanonical_invocation",
            ),
            file=sys.stderr,
        )
        return 1

    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository / "src"))
    try:
        from populace_dynamics.estimates.anchor_context_rehearsal import (
            run_fixture_rehearsal,
        )

        result = run_fixture_rehearsal()
    except BaseException:
        print(
            _metadata("failed", reason="fixture_rehearsal_failed"),
            file=sys.stderr,
        )
        return 1
    print(_metadata(result.status, checks=result.checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
