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
    "05da7dbd3e8c247eb4cec2c321ebbf9b934f08576d96548b924a30e68d062977"
)
SEED_HISTORY_PREFIX_SHA256 = (
    "40ed82ee5ad01b6b36364de2310d45757a8a7dbb5c8f3274e83c46b7f8d514e4"
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
