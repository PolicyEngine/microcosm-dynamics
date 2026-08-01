"""Fail-closed validators for the standing benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE / "registry.json"
HISTORY_PATH = HERE / "history.jsonl"

TIERS = (
    "admin_truth",
    "model_triangulation",
    "statutory_parameter",
)
GAP_CLASSES = (
    "label_mismatch",
    "frame_no_alignment",
    "concept_mismatch",
    "module_missing",
    "small_cell",
    "preliminary_source",
    "unexplained",
)
COMPARISON_SCOPES = ("ratio", "share", "trajectory", "ordering")

REGISTRY_KEYS = {
    "allowed_comparison_scopes",
    "canonicalization",
    "deferred_comparisons",
    "entries",
    "external_capture_review",
    "gap_class_counts",
    "gap_classes",
    "honesty_frame",
    "inputs",
    "purpose",
    "registry_change_law",
    "row_count",
    "schema_version",
    "seed_evaluation",
    "tier_counts",
    "tiers",
    "validation_only_law",
}
ENTRY_KEYS = {
    "comparison_scope",
    "concept_mismatch",
    "evidential_status",
    "external_reference",
    "gap_class",
    "gap_closure_condition",
    "gap_note",
    "our_side_artifact",
    "published_formula",
    "published_unit",
    "quantity",
    "row_id",
    "source_pin",
    "spec_revisions",
    "tier",
    "verification_class",
}
HISTORY_KEYS = {
    "deviation",
    "evaluated_at_run",
    "gap_class",
    "gap_note",
    "label_state",
    "our",
    "published",
    "registry_sha",
    "row_id",
}


def sha256_bytes(raw: bytes) -> str:
    """Return the lowercase SHA-256 digest of bytes."""

    return hashlib.sha256(raw).hexdigest()


def is_sha256(value: Any) -> bool:
    """Return whether value is exactly one lowercase SHA-256 digest."""

    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def canonical_json_bytes(value: Any) -> bytes:
    """Render canonical pretty JSON used by registry.json."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_jsonl_line(value: Any) -> bytes:
    """Render one compact, sorted, canonical JSONL object."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def load_registry(path: Path = REGISTRY_PATH) -> tuple[dict[str, Any], bytes]:
    """Load registry bytes while retaining their hash identity."""

    raw = path.read_bytes()
    registry = json.loads(raw)
    if raw != canonical_json_bytes(registry):
        raise AssertionError("registry.json is not canonical sorted JSON")
    validate_registry(registry)
    return registry, raw


def load_history(
    path: Path = HISTORY_PATH,
) -> tuple[list[dict[str, Any]], bytes]:
    """Load and validate canonical history records in append order."""

    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise AssertionError(
            "history.jsonl must be nonempty and LF-terminated"
        )
    records = []
    offset = 0
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        if line in {b"\n", b"\r\n"}:
            raise AssertionError(f"blank history line {line_number}")
        record = json.loads(line)
        if line != canonical_jsonl_line(record):
            raise AssertionError(
                f"history line {line_number} is not canonical sorted JSON"
            )
        record["_byte_start"] = offset
        offset += len(line)
        record["_byte_end"] = offset
        records.append(record)
    validate_history(records)
    for record in records:
        del record["_byte_start"]
        del record["_byte_end"]
    return records, raw


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate exact registry shape, enums, pins, and synchronized counts."""

    assert set(registry) == REGISTRY_KEYS
    assert registry["schema_version"] == "standing_benchmark_registry.v1"
    assert registry["allowed_comparison_scopes"] == list(COMPARISON_SCOPES)
    assert set(registry["tiers"]) == set(TIERS)
    assert set(registry["gap_classes"]) == set(GAP_CLASSES)
    assert all(
        definition["closure_condition"].strip()
        for definition in registry["gap_classes"].values()
    )
    assert (
        "never normative"
        in registry["tiers"]["model_triangulation"]["gap_law"]
    )

    entries = registry["entries"]
    assert isinstance(entries, list) and entries
    assert registry["row_count"] == len(entries)
    row_ids = [entry["row_id"] for entry in entries]
    assert len(row_ids) == len(set(row_ids))

    tier_counts = Counter()
    gap_counts = Counter()
    for entry in entries:
        validate_registry_entry(entry)
        tier_counts[entry["tier"]] += 1
        gap_counts[entry["gap_class"]] += 1

    assert registry["tier_counts"] == {
        tier: tier_counts[tier] for tier in TIERS
    }
    assert registry["gap_class_counts"] == {
        gap_class: gap_counts[gap_class] for gap_class in GAP_CLASSES
    }


def validate_registry_entry(entry: dict[str, Any]) -> None:
    """Validate one append-mostly benchmark specification."""

    assert set(entry) == ENTRY_KEYS
    assert isinstance(entry["row_id"], str) and entry["row_id"].strip()
    assert isinstance(entry["quantity"], str) and entry["quantity"].strip()
    assert entry["tier"] in TIERS
    assert entry["gap_class"] in GAP_CLASSES
    assert entry["gap_class"] != "unexplained"
    assert isinstance(entry["gap_note"], str) and entry["gap_note"].strip()
    assert entry["gap_note"].rstrip().endswith(".")
    assert (
        isinstance(entry["gap_closure_condition"], str)
        and entry["gap_closure_condition"].strip()
    )
    assert entry["verification_class"] in {
        "verified",
        "reported_not_verified",
    }
    assert isinstance(entry["comparison_scope"], list)
    assert entry["comparison_scope"]
    assert len(entry["comparison_scope"]) == len(
        set(entry["comparison_scope"])
    )
    assert set(entry["comparison_scope"]) <= set(COMPARISON_SCOPES)

    our_pointer = entry["our_side_artifact"]["artifact_pointer"]
    assert set(our_pointer) == {"json_pointer", "path", "sha256"}
    assert is_sha256(our_pointer["sha256"])
    assert our_pointer["path"].endswith(".json")
    assert our_pointer["json_pointer"].startswith("/")

    source_pin = entry["source_pin"]
    assert set(source_pin) == {
        "artifacts",
        "exact_locators",
        "reported_value_provenance",
    }
    assert source_pin["artifacts"]
    assert source_pin["exact_locators"]
    for artifact in source_pin["artifacts"]:
        assert artifact["pin_type"] in {
            "committed_extraction",
            "sha_manifested_capture",
        }
        assert is_sha256(artifact["sha256"])
        if artifact["pin_type"] == "committed_extraction":
            assert artifact["path"]
            assert artifact["json_pointer"].startswith("/")
        else:
            assert artifact["filename"]
            assert artifact["size_bytes"] > 0
    for locator in source_pin["exact_locators"]:
        assert locator["document"]
        assert "page" in locator
        assert locator["table"]

    if entry["verification_class"] == "verified":
        for locator in source_pin["exact_locators"]:
            accepted = {
                "committed_extraction",
                "reviewed_external_capture",
            } & set(locator)
            assert len(accepted) == 1
    else:
        assert ".mermin." in entry["row_id"]
        assert source_pin["reported_value_provenance"]["classification"] == (
            "reported_not_verified"
        )
        for locator in source_pin["exact_locators"]:
            assert "missing after REFRESH" in locator["capture_status"]
            corroboration = locator["unmanifested_corroborating_copy"]
            assert corroboration["manifested"] is False
            assert corroboration["accepted_as_verified_source"] is False

    revisions = entry["spec_revisions"]
    assert isinstance(revisions, list)
    for expected_revision, revision in enumerate(revisions, 1):
        assert revision["revision"] == expected_revision
        assert revision["note"].strip()
        assert isinstance(revision["changed_fields"], list)
        assert revision["changed_fields"]


def validate_history(records: list[dict[str, Any]]) -> None:
    """Validate record sets and enforce the unexplained-gap alarm."""

    assert records
    sets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    run_registry_shas: dict[str, set[str]] = defaultdict(set)
    seen_row_runs = set()
    for record in records:
        public_record = {
            key: value
            for key, value in record.items()
            if not key.startswith("_")
        }
        assert set(public_record) == HISTORY_KEYS
        assert is_sha256(record["evaluated_at_run"])
        assert is_sha256(record["registry_sha"])
        assert isinstance(record["row_id"], str) and record["row_id"]
        assert record["gap_class"] in GAP_CLASSES
        assert (
            record["gap_class"] != "unexplained"
        ), f"unexplained benchmark gap: {record['row_id']}"
        assert (
            isinstance(record["gap_note"], str) and record["gap_note"].strip()
        ), f"missing gap note: {record['row_id']}"
        assert record["gap_note"].rstrip().endswith(".")
        assert set(record["our"]) == {"unit", "value"}
        assert set(record["published"]) == {"unit", "value"}
        assert isinstance(record["deviation"], dict) and record["deviation"]
        assert (
            isinstance(record["label_state"], dict) and record["label_state"]
        )

        row_run = (record["row_id"], record["evaluated_at_run"])
        assert row_run not in seen_row_runs, (
            "row/run SHA reused; any deviation movement without a new run SHA "
            "is a drift finding"
        )
        seen_row_runs.add(row_run)
        sets[(record["evaluated_at_run"], record["registry_sha"])].append(
            record
        )
        run_registry_shas[record["evaluated_at_run"]].add(
            record["registry_sha"]
        )

    assert all(
        len(shas) == 1 for shas in run_registry_shas.values()
    ), "one run SHA cannot be reused against multiple registries"

    for record_set in sets.values():
        byte_starts = [record["_byte_start"] for record in record_set]
        byte_ends = [record["_byte_end"] for record in record_set]
        assert max(byte_ends) - min(byte_starts) == sum(
            end - start
            for start, end in zip(byte_starts, byte_ends, strict=True)
        ), "each evaluation record set must be contiguous"


def latest_records(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return the last appended record for each row."""

    latest = {}
    for record in records:
        latest[record["row_id"]] = record
    return latest
