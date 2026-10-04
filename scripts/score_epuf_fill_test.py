"""gate_epuf_fill's one TEST scoring of the registered candidates.

Runs only after ``gates.yaml`` locks the gate: it reads TEST through
``epuf_fill_gate.test_part`` (via ``epuf_fill_scoring.score_registered``),
which refuses otherwise. It loads the registered candidates named in the
manifest (``runs/epuf_fill_candidates_v1.json``) by their SHA-256 from the
staged fills folder, scores each family's current rule, primary and
alternative over the registered draw seeds against the registered v3
floors, and writes the result whether the candidates pass or fail. It
refuses to overwrite an existing result. Usage::

    python scripts/score_epuf_fill_test.py \
        --manifest runs/epuf_fill_candidates_v1.json \
        --output runs/epuf_fill_gate_test_v1.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from populace_dynamics.artifacts import write_new
from populace_dynamics.harness import epuf_fill_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = Path("~/PolicyEngine/epuf-data/fills").expanduser()


def candidates_from(manifest: dict, fills_dir: Path) -> dict:
    """``{family: {role: (path, sha256)}}`` from a candidate manifest."""

    spec: dict[str, dict[str, tuple[Path, str]]] = {}
    for record in manifest["fills"].values():
        spec.setdefault(record["family"], {})[record["role"]] = (
            fills_dir / record["file"],
            record["sha256"],
        )
    return spec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fills-dir",
        type=Path,
        default=Path(
            os.environ.get("POPULACE_DYNAMICS_EPUF_FILLS_DIR", DEFAULT_DIR)
        ),
    )
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"{args.output} exists; TEST is scored once")
    started = time.time()
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    record = scoring.score_registered(
        candidates_from(manifest, args.fills_dir)
    )
    document = {
        "schema": "populace_dynamics.epuf_fill_gate_test.v1",
        "code_commit": subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "scored_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "manifest": str(args.manifest),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        **record,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(args.output, document, sidecar=True)


if __name__ == "__main__":
    main()
