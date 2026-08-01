#!/usr/bin/env python3
"""Validate and append one complete certified-run benchmark record set."""

from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path

from schema import (
    HISTORY_PATH,
    load_history,
    load_registry,
    sha256_bytes,
    validate_history,
    validate_history_against_registry,
)


def validate_candidate(path: Path, run_artifact: Path) -> bytes:
    """Return candidate bytes after all append-only protocol checks pass."""

    registry, registry_raw = load_registry()
    existing, _ = load_history()
    candidate, candidate_raw = load_history(path)

    if not run_artifact.is_file():
        raise SystemExit(f"missing certified run artifact: {run_artifact}")
    artifact_sha = sha256_bytes(run_artifact.read_bytes())

    registry_sha = sha256_bytes(registry_raw)
    expected_row_ids = [entry["row_id"] for entry in registry["entries"]]
    candidate_row_ids = [record["row_id"] for record in candidate]
    if candidate_row_ids != expected_row_ids:
        raise SystemExit(
            "candidate must contain every active registry row in registry order"
        )

    run_shas = {record["evaluated_at_run"] for record in candidate}
    if len(run_shas) != 1:
        raise SystemExit(
            "candidate must contain exactly one evaluation run SHA"
        )
    run_sha = next(iter(run_shas))
    if run_sha != artifact_sha:
        raise SystemExit(
            "candidate evaluated_at_run does not match the run artifact SHA"
        )
    if any(record["evaluated_at_run"] == run_sha for record in existing):
        raise SystemExit(
            "evaluation run SHA already exists; reuse is a drift finding"
        )
    if any(record["registry_sha"] != registry_sha for record in candidate):
        raise SystemExit("candidate registry_sha does not match registry.json")

    entries_by_id = {entry["row_id"]: entry for entry in registry["entries"]}
    prior_by_id = {record["row_id"]: record for record in existing}
    for record in candidate:
        entry = entries_by_id[record["row_id"]]
        if record["our"]["unit"] != entry["our_side_artifact"]["unit"]:
            raise SystemExit(
                f"candidate our unit does not match registry: {record['row_id']}"
            )
        if record["published"]["unit"] != entry["published_unit"]:
            raise SystemExit(
                "candidate published unit does not match registry: "
                f"{record['row_id']}"
            )
        if record["gap_class"] != entry["gap_class"]:
            raise SystemExit(
                "candidate gap class does not match registry: "
                f"{record['row_id']}"
            )
        if record["gap_note"] != entry["gap_note"]:
            raise SystemExit(
                "candidate gap note does not match registry: "
                f"{record['row_id']}"
            )
        prior = prior_by_id.get(record["row_id"])
        if (
            prior is not None
            and prior["registry_sha"] == registry_sha
            and record["published"] != prior["published"]
        ):
            raise SystemExit(
                "published value moved under an unchanged registry: "
                f"{record['row_id']}"
            )

    validate_history(existing + candidate)
    validate_history_against_registry(
        existing + candidate, registry, registry_sha
    )
    return candidate_raw


def append(path: Path, run_artifact: Path) -> None:
    """Append validated bytes without rewriting existing history."""

    descriptor = os.open(HISTORY_PATH, os.O_WRONLY | os.O_APPEND)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        candidate_raw = validate_candidate(path, run_artifact)
        written = os.write(descriptor, candidate_raw)
        if written != len(candidate_raw):
            raise OSError("short append to benchmark history")
        os.fsync(descriptor)
        load_history()
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--run-artifact",
        type=Path,
        required=True,
        help="immutable certified artifact whose SHA identifies the record set",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="validate a candidate record set; never write",
    )
    mode.add_argument(
        "--append",
        action="store_true",
        help="append a validated record set to history.jsonl",
    )
    args = parser.parse_args()
    if args.check:
        validate_candidate(args.candidate, args.run_artifact)
    else:
        append(args.candidate, args.run_artifact)


if __name__ == "__main__":
    main()
