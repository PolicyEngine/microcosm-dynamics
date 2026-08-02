"""Reproduce the legal audit from the registered external staging corpus."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "historical_coverage_legal_registration_required_v1.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_historical_coverage_rule_specs as builder  # noqa: E402

STAGED_CAPTURE = builder.DEFAULT_CAPTURE_ROOT


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact() -> dict[str, Any]:
    value = builder.strict_json_loads(
        ARTIFACT.read_bytes(), "committed legal-registration audit"
    )
    assert isinstance(value, dict)
    return value


def _require_staged_capture() -> Path:
    manifest = STAGED_CAPTURE / builder.CAPTURE_MANIFEST_FILENAME
    if not manifest.is_file() or manifest.is_symlink():
        pytest.skip("coordinator legal-capture staging area is unavailable")
    return manifest


def _reseal_sources(value: dict[str, Any]) -> None:
    documents = value["source_document_candidates"]
    ordered_ids = [row["source_document_id"] for row in documents]
    value["ordered_source_document_ids"] = ordered_ids
    value["source_document_candidate_count"] = len(documents)
    value["source_document_keyset_sha256"] = builder._sha256(
        builder.canonical_json_bytes(ordered_ids)
    )
    value["source_document_rows_sha256"] = builder._sha256(
        builder.canonical_json_bytes(documents)
    )
    census = builder._source_authority_class_census(documents)
    value["source_authority_class_census"] = census
    value["source_authority_class_census_count"] = len(census)
    value["source_authority_class_census_sha256"] = builder._sha256(
        builder.canonical_json_bytes(census)
    )
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def test_staged_112_document_capture_reproduces_committed_audit():
    staged_manifest = _require_staged_capture()
    raw = staged_manifest.read_bytes()
    assert len(raw) == builder.EXPECTED_CAPTURE_MANIFEST_SIZE == 18_835
    assert hashlib.sha256(raw).hexdigest() == (
        "58951b038ac6bc5122952e5db8d76e3e78572b8c1bac403d2c0b561af16b68ac"
    )
    rows = raw.decode("utf-8").splitlines()
    assert len(rows) == builder.EXPECTED_CAPTURE_ROW_COUNT == 112
    total_bytes = 0
    for manifest_position, row in enumerate(rows, start=1):
        _, expected_sha256, size_token, filename, _ = row.split("\t")
        expected_size = int(size_token)
        staged_path = STAGED_CAPTURE / filename
        assert staged_path.is_file(), manifest_position
        assert not staged_path.is_symlink(), manifest_position
        assert staged_path.stat().st_size == expected_size, manifest_position
        assert _sha256(staged_path) == expected_sha256, manifest_position
        total_bytes += expected_size
    assert total_bytes == builder.EXPECTED_DECLARED_SOURCE_BYTE_SIZE
    assert total_bytes == 1_750_563_108

    committed = ARTIFACT.read_bytes()
    assert builder.render_audit(STAGED_CAPTURE) == committed
    builder.validate_registration_required_audit(
        _artifact(), capture_root=STAGED_CAPTURE
    )


def test_resealed_source_identity_cannot_substitute_for_staged_bytes():
    _require_staged_capture()
    value = copy.deepcopy(_artifact())
    row = value["source_document_candidates"][0]
    row["sha256"] = "f" * 64
    row["source_document_id"] = f"legal-source:{'f' * 64}"
    row["locator"]["full_file_sha256"] = "f" * 64
    row["locator"]["range_sha256"] = "f" * 64
    value["source_document_candidates"].sort(
        key=lambda item: item["source_document_id"].encode("utf-8")
    )
    _reseal_sources(value)
    builder.validate_registration_required_audit_structure(value)
    with pytest.raises(ValueError, match="does not reproduce"):
        builder.validate_registration_required_audit(
            value, capture_root=STAGED_CAPTURE
        )
