"""One-shot CLI for the registered first-estimates coordinator."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_PYCACHE_SENTINEL_ENV = "POPULACE_DYNAMICS_FIRST_ESTIMATES_PYCACHE_SENTINEL"
_PYCACHE_SENTINEL_PREFIX = "populace-first-estimates-pycache-"


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
