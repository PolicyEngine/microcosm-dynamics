#!/usr/bin/env python3
"""Reproduce-check the immutable seed prefix of growing benchmark history."""

from __future__ import annotations

import argparse

from schema import (
    HISTORY_PATH,
    RUN_MANIFEST_PATH,
    load_history,
    load_run_manifest,
    sha256_bytes,
)

SEED_ROW_COUNT = 42
SEED_RUN_SHA256 = (
    "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977"
)
SEED_REGISTRY_SHA256 = (
    "3355f6686d67eb39793fb790327010c21ee852704968c627f0d851c6dd7d1726"
)
SEED_HISTORY_PREFIX_SHA256 = (
    "61b8233b430c80c68a26cd5c1cbda8cb71ed8ef2631d96d0d4b7424f2f430d31"
)
SEED_RUN_MANIFEST_PREFIX_SHA256 = (
    "b8cacb139ce67ed1bf5ba1509d4ca9f995d6d5e032ddfa4cb4ec565ba220f82c"
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
    manifest, manifest_raw = load_run_manifest(RUN_MANIFEST_PATH)
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
    manifest_prefix = manifest_raw.splitlines(keepends=True)[0]
    if sha256_bytes(manifest_prefix) != SEED_RUN_MANIFEST_PREFIX_SHA256:
        raise SystemExit("the immutable run-manifest seed SHA-256 has drifted")
    if manifest[0]["evaluated_at_run"] != SEED_RUN_SHA256:
        raise SystemExit(
            "the immutable run-manifest seed identity has drifted"
        )


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
