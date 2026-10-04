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
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness import epuf_fill_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = Path("~/PolicyEngine/epuf-data/fills").expanduser()
#: The registered manifest; any other manifest is refused.
REGISTERED_MANIFEST = "runs/epuf_fill_candidates_v1.json"
REGISTERED_MANIFEST_SHA256 = (
    "a304311343f3c78f7702ec6918b991b6bea30dad2a23529df6f0f975ce7f62d0"
)
#: Files whose state the record reports.
CODE_FILES = (
    "src/populace_dynamics/harness/epuf_fill_gate.py",
    "src/populace_dynamics/harness/epuf_fill_scoring.py",
    "src/populace_dynamics/estimates/epuf_fill.py",
    "scripts/score_epuf_fill_test.py",
)


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
    manifest_bytes = args.manifest.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_sha256 != REGISTERED_MANIFEST_SHA256:
        raise ValueError(
            f"{args.manifest} has SHA-256 {manifest_sha256}, not the "
            f"registered {REGISTERED_MANIFEST_SHA256}"
        )
    started = time.time()
    clean = (
        subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--"]
            + list(CODE_FILES),
            check=False,
        ).returncode
        == 0
    )
    # Refuse before any marker unless the gate is locked (test_part checks
    # again before it reads TEST).
    status = g._gate_lock_status(ROOT / "gates.yaml")
    if not status["locked"] or status["registration_id"] != g.REGISTRATION_ID:
        raise g.TestPartLocked(
            "gate_epuf_fill is not locked; TEST stays unread"
        )
    # A started marker, so a run that fails after reading TEST leaves a
    # trace of the read.
    marker = Path(f"{args.output}.started.json")
    with marker.open("x") as handle:
        json.dump(
            {
                "started_at_utc": dt.datetime.now(dt.UTC).isoformat(
                    timespec="seconds"
                ),
                "manifest_sha256": manifest_sha256,
            },
            handle,
        )
    manifest = json.loads(manifest_bytes)
    record = scoring.score_registered(
        candidates_from(manifest, args.fills_dir)
    )
    # Published paths are the registered file names, not local folders.
    for family in record["candidates"].values():
        for role in family.values():
            role["path"] = Path(role["path"]).name
    document = {
        "schema": "populace_dynamics.epuf_fill_gate_test.v1",
        "code_commit": subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "scored_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "code_files_clean": clean,
        "manifest": REGISTERED_MANIFEST,
        "manifest_sha256": manifest_sha256,
        **record,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_new(args.output, document, sidecar=True)


if __name__ == "__main__":
    main()
