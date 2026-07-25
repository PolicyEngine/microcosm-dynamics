"""One-shot CLI for the registered first-estimates coordinator."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Set both the inherited process environment and this interpreter before any
# repository module is imported.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

from populace_dynamics.estimates.coordinator import (  # noqa: E402
    run_registered_first_estimates,
)


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
    args = _arguments()
    result = run_registered_first_estimates(
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
