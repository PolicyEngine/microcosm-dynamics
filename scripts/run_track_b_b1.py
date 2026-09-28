#!/usr/bin/env python3
"""Run the registered Track B B1 reproduction attempt on staged inputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from populace_dynamics.track_b.runner import DEFAULT_OUTPUT, execute

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registration-id",
        required=True,
        help="Fresh issue #42 reproduction comment ID or URL",
    )
    parser.add_argument(
        "--expected-commit",
        required=True,
        help="Full frozen B1 build commit SHA",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--historical-reference",
        type=Path,
        help=(
            "Historical person-level archive; admitted only if its SHA256 "
            "equals the committed runner.HISTORICAL_REFERENCE_SHA256 "
            "(None refuses every archive)"
        ),
    )
    args = parser.parse_args(argv)
    result = execute(
        root=ROOT,
        registration_id=args.registration_id,
        expected_commit=args.expected_commit,
        output=args.out,
        historical_reference=args.historical_reference,
    )
    print(f"{result['status']}: {args.out / 'result.json'}; reproduction only")
    return 0 if result["status"] == "REPRODUCED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
