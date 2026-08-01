#!/usr/bin/env python3
"""Validate and append one complete benchmark evaluation record set."""

from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path

from schema import (
    HISTORY_PATH,
    RUN_MANIFEST_PATH,
    canonical_jsonl_line,
    load_history,
    load_registry,
    load_run_manifest,
    repo_relative_artifact_path,
    sha256_bytes,
    validate_history,
    validate_history_against_registry,
    validate_history_run_artifacts,
    validate_index_manifest_artifact,
)


def validate_candidate(path: Path, run_artifact: Path) -> tuple[bytes, bytes]:
    """Return canonical history and manifest bytes after protocol checks."""

    registry, registry_raw = load_registry()
    existing, _ = load_history()
    manifest, _ = load_run_manifest()
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
    artifact_entry = {
        "artifact_path": repo_relative_artifact_path(run_artifact),
        "evaluated_at_run": run_sha,
    }
    validate_history_run_artifacts(
        existing + candidate,
        [*manifest, artifact_entry],
        require_git=False,
    )
    validate_index_manifest_artifact(artifact_entry)
    return candidate_raw, canonical_jsonl_line(artifact_entry)


def append(path: Path, run_artifact: Path) -> None:
    """Append validated manifest and history bytes as one locked operation."""

    manifest_descriptor = os.open(RUN_MANIFEST_PATH, os.O_RDWR | os.O_APPEND)
    history_descriptor = os.open(HISTORY_PATH, os.O_RDWR | os.O_APPEND)
    descriptors = (manifest_descriptor, history_descriptor)
    original_sizes = tuple(
        os.fstat(descriptor).st_size for descriptor in descriptors
    )
    mutated = False
    try:
        for descriptor in descriptors:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        candidate_raw, manifest_raw = validate_candidate(path, run_artifact)
        mutated = True
        manifest_written = os.write(manifest_descriptor, manifest_raw)
        if manifest_written != len(manifest_raw):
            raise OSError("short append to benchmark run manifest")
        history_written = os.write(history_descriptor, candidate_raw)
        if history_written != len(candidate_raw):
            raise OSError("short append to benchmark history")
        os.fsync(manifest_descriptor)
        os.fsync(history_descriptor)
        load_history(require_git=False)
    except BaseException:
        if mutated:
            for descriptor, size in zip(
                descriptors, original_sizes, strict=True
            ):
                os.ftruncate(descriptor, size)
                os.fsync(descriptor)
        raise
    finally:
        for descriptor in reversed(descriptors):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--run-artifact",
        type=Path,
        required=True,
        help="immutable evaluation artifact whose SHA identifies the record set",
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
        help="append a validated record set and its run-manifest entry",
    )
    args = parser.parse_args()
    if args.check:
        validate_candidate(args.candidate, args.run_artifact)
    else:
        append(args.candidate, args.run_artifact)


if __name__ == "__main__":
    main()
