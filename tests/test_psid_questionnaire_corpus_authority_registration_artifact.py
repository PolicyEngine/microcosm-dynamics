"""Offline bindings for the committed PSID corpus-registration attempt."""

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
    / "psid_questionnaire_corpus_authority_registration_attempt_v1.json"
)
ARTIFACT_SIZE_BYTES = 499_221
ARTIFACT_SHA256 = (
    "a1216521410d5a73e0dfde4d094d703843016cf6e67c8ee11ac3c4be70baceb0"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_psid_questionnaire_corpus_authority_registration as builder  # noqa: E402


def _artifact() -> dict[str, Any]:
    value = builder._strictly_parsed_document(
        ARTIFACT.read_bytes(), "committed registration attempt"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict[str, Any], *, documents_changed: bool = False) -> None:
    if documents_changed:
        value["document_rows_sha256"] = builder._sha256(
            builder.canonical_json_bytes(value["document_candidates"])
        )
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def test_committed_attempt_is_canonical_size_and_sha_pinned():
    raw = ARTIFACT.read_bytes()
    assert len(raw) == ARTIFACT_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    value = _artifact()
    builder.validate_structure(value)
    assert raw == builder.canonical_json_bytes(value)
    assert b"/Users/" not in raw
    assert b"maxghenis" not in raw


def test_attempt_covers_the_exact_capture_domain_and_fails_closed():
    value = _artifact()
    documents = value["document_candidates"]
    assert value["document_candidate_count"] == len(documents) == 456
    assert value["unique_document_identity_count"] == 455
    assert value["ordered_document_ids"] == [
        f"psid-corpus-document-{position:04d}" for position in range(1, 457)
    ]
    assert value["verified_document_count"] == 440
    assert value["failed_document_count"] == 16
    assert value["failed_document_ids"] == builder.EXPECTED_FAILED_DOCUMENT_IDS
    assert {row["availability"] for row in documents} == {
        "verified",
        "identity_mismatch",
    }
    assert value["registration_status"] == "fail"
    assert value["failure_disposition"] == builder.FAILURE_DISPOSITION
    assert value["accepted_authority_registry"] is None
    assert value["name_disambiguation"] == builder.EXPECTED_DISAMBIGUATION_ROWS
    assert value["link_inventory_summary"] == {
        "link_count": 465,
        "unique_href_count": 456,
        "duplicate_link_count": 9,
        "deduplication_rule": "stable_first_occurrence_by_exact_href",
        "ordered_unique_hrefs_sha256": (
            "baa4c9fc45343701afea62349497f1e0fe5624ab12494f71fd10633254c0c323"
        ),
    }


def test_every_available_source_has_a_fail_closed_full_file_locator():
    value = _artifact()
    for capture_input in value["capture_input_identities"]:
        locator = capture_input["locator"]
        assert locator["location_type"] == "full_file_byte_range"
        assert locator["byte_start"] == 0
        assert locator["byte_end"] == locator["size_bytes"]
        assert locator["range_sha256"] == locator["full_file_sha256"]

    for row in value["document_candidates"]:
        if row["availability"] == "verified":
            locator = row["locator"]
            assert locator == {
                "location_type": "full_file_byte_range",
                "filename": row["on_disk_filename"],
                "full_file_sha256": row["expected_sha256"],
                "size_bytes": row["expected_size_bytes"],
                "byte_start": 0,
                "byte_end": row["expected_size_bytes"],
                "range_sha256": row["expected_sha256"],
            }
            assert row["observed_identity"] == {
                "filename": row["on_disk_filename"],
                "sha256": row["expected_sha256"],
                "size_bytes": row["expected_size_bytes"],
            }
        else:
            assert row["locator"] is None
            observed = row["observed_identity"]
            assert observed is not None
            assert (
                observed["sha256"],
                observed["size_bytes"],
            ) != (row["expected_sha256"], row["expected_size_bytes"])


def test_repo_authority_locators_resolve_frozen_lines_and_byte_ranges():
    value = _artifact()
    assert len(value["repo_authority_locators"]) == len(
        builder.REPO_AUTHORITY_LOCATOR_SPECS
    )
    for locator in value["repo_authority_locators"]:
        live = (ROOT / locator["committed_path"]).read_bytes()
        if locator["identity_scope"] == "append_only_prefix":
            frozen = live[: locator["size_bytes"]]
        else:
            assert len(live) == locator["size_bytes"]
            frozen = live
        assert len(frozen) == locator["size_bytes"]
        assert (
            hashlib.sha256(frozen).hexdigest() == locator["full_source_sha256"]
        )
        lines = frozen.splitlines(keepends=True)
        expected_start = sum(
            len(line) for line in lines[: locator["line_start"] - 1]
        )
        expected_end = sum(len(line) for line in lines[: locator["line_end"]])
        assert (locator["byte_start"], locator["byte_end"]) == (
            expected_start,
            expected_end,
        )
        cited = frozen[expected_start:expected_end]
        assert hashlib.sha256(cited).hexdigest() == locator["range_sha256"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("accept_authority", "accepted authority"),
        ("capture_input", "capture input identity"),
        ("repo_locator", "repo authority locator"),
        ("document_link", "document rows digest"),
        ("verified_locator", "verified locator"),
        ("promote_failed_document", "document rows digest"),
    ],
)
def test_coherently_resealed_mutations_are_rejected(
    mutation: str,
    message: str,
):
    value = copy.deepcopy(_artifact())
    documents_changed = False
    if mutation == "accept_authority":
        value["accepted_authority_registry"] = {"authority_id": "forged"}
    elif mutation == "capture_input":
        value["capture_input_identities"][0]["locator"][
            "filename"
        ] = "forged_browser_digests.txt"
    elif mutation == "repo_locator":
        value["repo_authority_locators"][0]["byte_start"] += 1
    elif mutation == "document_link":
        row = value["document_candidates"][0]
        row["source_url"] += "?forged=1"
        row["document_identity_sha256"] = builder._sha256(
            builder.canonical_json_bytes(
                [
                    row["digest_row_number"],
                    row["source_url"],
                    row["digest_row_filename"],
                    row["expected_sha256"],
                    row["expected_size_bytes"],
                ]
            )
        )
        documents_changed = True
    elif mutation == "verified_locator":
        row = value["document_candidates"][0]
        row["locator"]["byte_end"] -= 1
        documents_changed = True
    else:
        failed_id = value["failed_document_ids"][0]
        row = next(
            item
            for item in value["document_candidates"]
            if item["source_document_id"] == failed_id
        )
        row["availability"] = "verified"
        row["observed_identity"] = {
            "filename": row["on_disk_filename"],
            "sha256": row["expected_sha256"],
            "size_bytes": row["expected_size_bytes"],
        }
        row["locator"] = {
            "location_type": "full_file_byte_range",
            "filename": row["on_disk_filename"],
            "full_file_sha256": row["expected_sha256"],
            "size_bytes": row["expected_size_bytes"],
            "byte_start": 0,
            "byte_end": row["expected_size_bytes"],
            "range_sha256": row["expected_sha256"],
        }
        value["verified_document_ids"] = [
            item["source_document_id"]
            for item in value["document_candidates"]
            if item["availability"] == "verified"
        ]
        value["failed_document_ids"] = [
            item["source_document_id"]
            for item in value["document_candidates"]
            if item["availability"] != "verified"
        ]
        value["verified_document_count"] = len(value["verified_document_ids"])
        value["failed_document_count"] = len(value["failed_document_ids"])
        documents_changed = True
    _reseal(value, documents_changed=documents_changed)
    with pytest.raises(ValueError, match=message):
        builder.validate_structure(value)
