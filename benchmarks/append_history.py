#!/usr/bin/env python3
"""Validate and append one complete certified-run benchmark record set."""

from __future__ import annotations

import argparse
from pathlib import Path

from schema import (
    HISTORY_PATH,
    load_history,
    load_registry,
    sha256_bytes,
)


def validate_candidate(path: Path) -> bytes:
    """Return candidate bytes after all append-only protocol checks pass."""

    registry, registry_raw = load_registry()
    existing, _ = load_history()
    candidate, candidate_raw = load_history(path)

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
    if any(record["evaluated_at_run"] == run_sha for record in existing):
        raise SystemExit(
            "evaluation run SHA already exists; reuse is a drift finding"
        )
    if any(record["registry_sha"] != registry_sha for record in candidate):
        raise SystemExit("candidate registry_sha does not match registry.json")
    return candidate_raw


def append(path: Path) -> None:
    """Append validated bytes without rewriting existing history."""

    candidate_raw = validate_candidate(path)
    with HISTORY_PATH.open("ab") as history_file:
        history_file.write(candidate_raw)
        history_file.flush()
    load_history()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
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
        validate_candidate(args.candidate)
    else:
        append(args.candidate)


if __name__ == "__main__":
    main()
