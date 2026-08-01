#!/usr/bin/env python3
"""Initialize once or reproduce-check the immutable benchmark-history seed."""

from __future__ import annotations

import argparse
from pathlib import Path

import build_registry
from schema import (
    HISTORY_PATH,
    canonical_jsonl_line,
    load_history,
    sha256_bytes,
)

SEED_ROW_COUNT = 42
SEED_REGISTRY_SHA256 = (
    "05da7dbd3e8c247eb4cec2c321ebbf9b934f08576d96548b924a30e68d062977"
)
SEED_HISTORY_PREFIX_SHA256 = (
    "40ed82ee5ad01b6b36364de2310d45757a8a7dbb5c8f3274e83c46b7f8d514e4"
)


def seed_bytes() -> bytes:
    """Return the frozen canonical 42-record seed set."""

    records = build_registry.seed_history_records(SEED_REGISTRY_SHA256)
    assert len(records) == SEED_ROW_COUNT
    return b"".join(canonical_jsonl_line(record) for record in records)


def seed_prefix(raw: bytes) -> bytes:
    """Return exactly the immutable seed prefix from a growing history."""

    lines = raw.splitlines(keepends=True)
    if len(lines) < SEED_ROW_COUNT:
        raise AssertionError(
            f"history has {len(lines)} lines; seed needs {SEED_ROW_COUNT}"
        )
    return b"".join(lines[:SEED_ROW_COUNT])


def initialize(path: Path = HISTORY_PATH) -> None:
    """Create the seed only when no history path exists."""

    if path.exists():
        raise SystemExit(
            "history is append-only; refusing to initialize an existing file"
        )
    registry_raw = build_registry.OUT.read_bytes()
    if sha256_bytes(registry_raw) != SEED_REGISTRY_SHA256:
        raise SystemExit(
            "registry bytes do not match the frozen seed registry"
        )
    path.write_bytes(seed_bytes())


def check(path: Path = HISTORY_PATH) -> None:
    """Reproduce-check the seed prefix while allowing later appends."""

    _, raw = load_history(path)
    prefix = seed_prefix(raw)
    if prefix != seed_bytes():
        raise SystemExit("the immutable history seed prefix has drifted")
    if sha256_bytes(prefix) != SEED_HISTORY_PREFIX_SHA256:
        raise SystemExit("the immutable history seed SHA-256 has drifted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--initialize",
        action="store_true",
        help="create history.jsonl once; fail if it already exists",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="check the frozen seed prefix; never write",
    )
    args = parser.parse_args()
    if args.initialize:
        initialize()
    else:
        check()


if __name__ == "__main__":
    main()
