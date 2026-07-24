"""One-shot CLI for the registered first-estimates coordinator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from populace_dynamics.estimates.coordinator import (
    run_registered_first_estimates,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


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
        "--repository-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--retry-after-incident",
        type=int,
        help="Explicit sole retry-eligible incident index.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    result = run_registered_first_estimates(
        repository_root=args.repository_root,
        registration_reference=args.registration_reference,
        registered_configuration_bytes=(
            args.registered_configuration.read_bytes()
        ),
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
