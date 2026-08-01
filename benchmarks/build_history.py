#!/usr/bin/env python3
"""Reproduce-check the immutable seed prefix of growing benchmark history."""

from __future__ import annotations

import argparse

from schema import HISTORY_PATH, load_history, sha256_bytes

SEED_ROW_COUNT = 42
SEED_RUN_SHA256 = (
    "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977"
)
SEED_REGISTRY_SHA256 = (
    "d915af609c95fc2616c7ed61760df6efd437e28047ee8800f6b5e19de5bdd48b"
)
SEED_HISTORY_PREFIX_SHA256 = (
    "8bf5ee2d519efa225702b30dc38ddefc4a100845d8196d2cf1eb055a058ff1ae"
)


def seed_prefix(raw: bytes) -> bytes:
    """Return exactly the immutable seed prefix from a growing history."""

    lines = raw.splitlines(keepends=True)
    if len(lines) < SEED_ROW_COUNT:
        raise AssertionError(
            f"history has {len(lines)} lines; seed needs {SEED_ROW_COUNT}"
        )
    return b"".join(lines[:SEED_ROW_COUNT])


def check() -> None:
    """Check only frozen seed identities, independently of registry growth."""

    records, raw = load_history(HISTORY_PATH)
    seed_records = records[:SEED_ROW_COUNT]
    prefix = seed_prefix(raw)
    if sha256_bytes(prefix) != SEED_HISTORY_PREFIX_SHA256:
        raise SystemExit("the immutable history seed SHA-256 has drifted")
    if {record["evaluated_at_run"] for record in seed_records} != {
        SEED_RUN_SHA256
    }:
        raise SystemExit("the immutable history seed run SHA has drifted")
    if {record["registry_sha"] for record in seed_records} != {
        SEED_REGISTRY_SHA256
    }:
        raise SystemExit("the immutable history seed registry SHA has drifted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        required=True,
        help="check the frozen seed prefix; never write",
    )
    parser.parse_args()
    check()


if __name__ == "__main__":
    main()
