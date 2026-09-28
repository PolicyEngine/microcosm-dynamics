"""Registered Track A v2 joint entry; preflight precedes every input read."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from populace_dynamics.track_a_v2.manifest import (  # noqa: E402
    REGISTERED_HEADER,
)
from populace_dynamics.track_a_v2.protocol import (  # noqa: E402
    FROZEN_ROWS,
    load_registered_inputs,
    preflight,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-pointer", required=True)
    parser.add_argument("--registered-commit", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    checked = preflight(
        root=ROOT,
        registration_pointer=args.registration_pointer,
        registered_commit=args.registered_commit,
        output=args.output,
        protocol=protocol,
        protocol_sha256=args.protocol_sha256,
    )
    # Exclusive creation closes the race between preflight and input load.
    # §10 requires even an infrastructure failure to preserve its attempt.
    with args.output.open("x", encoding="utf-8") as handle:
        try:
            from populace_dynamics.track_a_v2.runner import run_joint

            inputs = load_registered_inputs(checked)
            artifact = run_joint(
                inputs,
                registration_pointer=args.registration_pointer,
                registration=checked,
            )
        except (Exception, KeyboardInterrupt) as error:
            artifact = {
                "header": REGISTERED_HEADER,
                "attempt": {
                    "status": "refused",
                    "refusal": str(error) or type(error).__name__,
                    "first_failing_person_draw": None,
                    "step": "input_loading_or_infrastructure",
                    "uncomputed_rows": list(FROZEN_ROWS),
                    "counters": {},
                },
            }
        artifact["preflight"] = asdict(checked)
        json.dump(artifact, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(args.output)
    return 2 if artifact["attempt"]["status"] == "refused" else 0


if __name__ == "__main__":
    raise SystemExit(main())
