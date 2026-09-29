#!/usr/bin/env python3
"""Run the registered Track B B1 reproduction attempt on staged inputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from populace_dynamics.track_b.reconstructed import (
    DEFAULT_OUTPUT as RECONSTRUCTED_OUTPUT,
)
from populace_dynamics.track_b.reconstructed import (
    RECONSTRUCTED_REPRODUCTION,
)
from populace_dynamics.track_b.runner import (
    BASELINE_VERSIONS,
    BIT_FOR_BIT,
    DEFAULT_OUTPUT,
    RECONSTRUCTED,
    execute,
)

ROOT = Path(__file__).resolve().parents[1]
# The passing status of each registered version.
PASSING_STATUS = {
    BIT_FOR_BIT: "REPRODUCED",
    RECONSTRUCTED: RECONSTRUCTED_REPRODUCTION,
}
SCOPE_NOTE = {
    BIT_FOR_BIT: "reproduction only",
    RECONSTRUCTED: "reconstructed reproduction only (weaker than bit-for-bit)",
}


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
    parser.add_argument(
        "--baseline-version",
        choices=BASELINE_VERSIONS,
        default=BIT_FOR_BIT,
        help=(
            "Registered B1 baseline: bit-for-bit (v1, the default; the only "
            "version that can yield REPRODUCED) or reconstructed (v2, "
            "decision d571; can yield only RECONSTRUCTED_REPRODUCTION)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            f"Output directory; must be {DEFAULT_OUTPUT} for bit-for-bit and "
            f"{RECONSTRUCTED_OUTPUT} for reconstructed (the defaults)"
        ),
    )
    parser.add_argument(
        "--historical-reference",
        type=Path,
        help=(
            "Historical person-level archive; admitted only if its SHA256 "
            "equals the committed runner.HISTORICAL_REFERENCE_SHA256 "
            "(None refuses every archive). Bit-for-bit only"
        ),
    )
    args = parser.parse_args(argv)
    version = args.baseline_version
    if args.out is not None:
        output = args.out
    elif version == RECONSTRUCTED:
        output = RECONSTRUCTED_OUTPUT
    else:
        output = DEFAULT_OUTPUT
    result = execute(
        root=ROOT,
        registration_id=args.registration_id,
        expected_commit=args.expected_commit,
        output=output,
        historical_reference=args.historical_reference,
        baseline_version=version,
    )
    print(
        f"{result['status']}: {output / 'result.json'}; {SCOPE_NOTE[version]}"
    )
    return 0 if result["status"] == PASSING_STATUS[version] else 2


if __name__ == "__main__":
    raise SystemExit(main())
