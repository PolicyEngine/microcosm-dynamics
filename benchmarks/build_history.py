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
    "5aa8ffb7f02527eb23e5948a32d6ffeeac03f941d733c47c55cf1aeabf1bfd89"
)
SEED_HISTORY_PREFIX_SHA256 = (
    "04bf81ffdbe73d8c47bcc8e7e9fb277f1e8fe126373d441f304f72c0f536f954"
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
