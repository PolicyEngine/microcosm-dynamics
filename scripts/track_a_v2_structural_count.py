"""Separately frozen structural entry: projection and permitted counts only."""

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
    load_registered_inputs,
    preflight,
)
from populace_dynamics.track_a_v2.structural import (  # noqa: E402
    run_structural,
    validate_count_outputs,
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
        mode="structural",
    )
    with args.output.open("x", encoding="utf-8") as handle:
        try:
            artifact = run_structural(
                load_registered_inputs(checked), registration=checked
            )
            validate_count_outputs(artifact["counts"])
        except (Exception, KeyboardInterrupt) as error:
            artifact = {
                "header": REGISTERED_HEADER,
                "attempt": {
                    "status": "refused",
                    "refusal": str(error) or type(error).__name__,
                    "first_failing_person_draw": None,
                    "step": "structural_input_loading_or_infrastructure",
                    "uncomputed_draws": list(range(20)),
                },
            }
        artifact["preflight"] = asdict(checked)
        json.dump(artifact, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(args.output)
    return 2 if artifact["attempt"]["status"] == "refused" else 0


if __name__ == "__main__":
    raise SystemExit(main())
