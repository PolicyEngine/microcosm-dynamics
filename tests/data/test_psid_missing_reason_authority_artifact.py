"""Committed fail-closed artifact and mutation gates for Amendment 11."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from populace_dynamics.data.psid_missing_reason_authority import (
    EXPECTED_CENSUS_SHA256S,
    EXPECTED_COUNTEREXAMPLE_COUNT,
    EXPECTED_COUNTEREXAMPLE_SHA256,
    EXPECTED_DIRECTLY_DISPROVEN_COUNT,
    EXPECTED_DIRECTLY_DISPROVEN_SHA256,
    EXPECTED_ENTRY_KIND_PACKED_SHA256,
    EXPECTED_LEXICAL_MISSING_COUNT,
    EXPECTED_LEXICAL_OTHER_COUNT,
    EXPECTED_LEXICAL_PACKED_SHA256,
    EXPECTED_LITERAL_COUNT,
    EXPECTED_NUMERIC_RANGE_COUNT,
    EXPECTED_RANGE_REJECTION_SHA256,
    EXPECTED_REGISTERED_SOURCE_BYTE_SIZE,
    EXPECTED_SOURCE_DOCUMENT_ROWS_SHA256,
    MissingReasonAuthorityError,
    canonical_json_bytes,
    settle_missing_reason_codes,
    sha256_bytes,
    validate_authority_artifact,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "external"
    / "psid_missing_reason_code_authority_v1.json"
)


@pytest.fixture(scope="module")
def artifact():
    value = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    validate_authority_artifact(value)
    return value


def _repin_content(candidate):
    candidate["integrity"]["content_sha256"] = "0" * 64
    candidate["integrity"]["content_sha256"] = sha256_bytes(
        canonical_json_bytes(candidate)
    )


def test_artifact_is_exact_section_10_1_json(artifact):
    raw = ARTIFACT_PATH.read_bytes()
    assert raw == canonical_json_bytes(artifact)
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_registered_sources_and_two_nonauthority_partitions(artifact):
    registered = artifact["registered_source_identity"]
    census = artifact["source_member_census"]
    kinds = artifact["entry_kind_vector"]
    candidates = artifact["lexical_candidate_vector"]
    assert registered["registered_source_count"] == 47
    assert registered["registered_source_byte_size"] == (
        EXPECTED_REGISTERED_SOURCE_BYTE_SIZE
    )
    assert registered["source_file_mismatch_count"] == 0
    assert census["literal_member_count"] == EXPECTED_LITERAL_COUNT
    assert census["numeric_range_member_count"] == EXPECTED_NUMERIC_RANGE_COUNT
    assert kinds["one_count"] == EXPECTED_LITERAL_COUNT
    assert kinds["zero_count"] == EXPECTED_NUMERIC_RANGE_COUNT
    assert kinds["packed_sha256"] == EXPECTED_ENTRY_KIND_PACKED_SHA256
    assert candidates["one_count"] == EXPECTED_LEXICAL_MISSING_COUNT
    assert candidates["zero_count"] == EXPECTED_LEXICAL_OTHER_COUNT
    assert candidates["packed_sha256"] == EXPECTED_LEXICAL_PACKED_SHA256


def test_source_document_rows_exact_cover_43_pdfs_and_four_labels(artifact):
    rows = artifact["source_document_rows"]
    assert len(rows) == 47
    assert sum(row["source_byte_size"] for row in rows) == 114_875_090
    assert sum(row["canonical_row_count"] for row in rows) == 102_179
    assert sum(row["normalized_entry_count"] for row in rows) == 561_873
    assert (
        sum(row["lexical_missing_candidate_count"] for row in rows) == 231_263
    )
    assert (
        sum(row["canonical_source_path"].endswith(".pdf") for row in rows)
        == 43
    )
    assert artifact["source_document_rows_sha256"] == (
        EXPECTED_SOURCE_DOCUMENT_ROWS_SHA256
    )
    assert all(len(row["derivation_metadata_sha256"]) == 64 for row in rows)


def test_all_source_relation_digests_are_independently_pinned(artifact):
    census = artifact["source_member_census"]
    assert {key: census[key] for key in EXPECTED_CENSUS_SHA256S} == (
        EXPECTED_CENSUS_SHA256S
    )


def test_candidate_counts_are_evidence_not_source_authority(artifact):
    census = artifact["source_member_census"]
    boundary = artifact["authority_boundary"]
    assert census["pdf_source_row_count"] == 89_599
    assert census["pdf_source_member_count"] == 479_345
    assert census["pdf_lexical_missing_candidate_count"] == 203_283
    assert census["value_label_lexical_missing_candidate_count"] == 27_980
    assert boundary["lexical_candidate_is_source_authority"] is False
    assert boundary["authorized_current_literal_disposition_count"] == 0
    assert boundary["unadjudicated_literal_count"] == 524_590
    assert boundary["inherited_dictionary_missing_declaration_count"] == 0
    assert boundary["dictionary_missing_declaration_scope"].startswith(
        "inherited_86_document"
    )


def test_context_required_and_direct_disproof_relations_are_complete(artifact):
    boundary = artifact["authority_boundary"]
    assert boundary["minimum_counterexample_count"] == (
        EXPECTED_COUNTEREXAMPLE_COUNT
    )
    assert boundary["minimum_counterexample_sha256"] == (
        EXPECTED_COUNTEREXAMPLE_SHA256
    )
    assert boundary["directly_disproven_candidate_count"] == (
        EXPECTED_DIRECTLY_DISPROVEN_COUNT
    )
    assert boundary["directly_disproven_candidate_sha256"] == (
        EXPECTED_DIRECTLY_DISPROVEN_SHA256
    )
    meanings = {
        row["source_meaning"]
        for row in boundary["directly_disproven_candidates"]
    }
    assert "Never refused" in meanings
    assert "Refused at least once" in meanings
    assert any("missing finger" in meaning for meaning in meanings)
    assert any("DK how to apply" in meaning for meaning in meanings)


def test_all_21_numeric_range_wild_code_rows_remain_null(artifact):
    witness = artifact["authority_boundary"][
        "numeric_range_rejection_witnesses"
    ]
    assert witness["row_count"] == 21
    assert witness["domain_sha256"] == EXPECTED_RANGE_REJECTION_SHA256
    assert all(
        row["required_missing_reason_code"] is None for row in witness["rows"]
    )


def test_rejection_classes_cover_context_defaults_and_conflicts(artifact):
    rows = artifact["authority_boundary"]["rejection_class_witnesses"]
    classes = {row["class"] for row in rows}
    assert len(classes) == 15
    assert {
        "lexical_substring_negation",
        "lexical_substring_substantive_event",
        "lexical_substring_substantive_anatomy",
        "lexical_substring_accuracy_status",
        "lexical_substring_information_access_reason",
        "numeric_range_wild_code_defeat",
        "evidence_artifact_laundering",
        "future_disposition_conflict",
        "semantic_taxonomy_request",
    } <= classes


def test_malformed_relation_precedes_named_production_blocker(artifact):
    with pytest.raises(
        MissingReasonAuthorityError, match="malformed source document"
    ):
        settle_missing_reason_codes([{}] * 47, artifact)


def _mutate_registry(candidate):
    candidate["registered_source_identity"]["registry_sha256"] = "1" * 64


def _mutate_source_rows(candidate):
    candidate["source_document_rows"][0]["source_sha256"] = "1" * 64
    candidate["source_document_rows_sha256"] = sha256_bytes(
        canonical_json_bytes(candidate["source_document_rows"])
    )


def _mutate_derivation_metadata(candidate):
    candidate["source_document_rows"][0]["derivation_metadata_sha256"] = (
        "1" * 64
    )
    candidate["source_document_rows_sha256"] = sha256_bytes(
        canonical_json_bytes(candidate["source_document_rows"])
    )


def _mutate_source_row_order(candidate):
    rows = candidate["source_document_rows"]
    rows[0], rows[1] = rows[1], rows[0]
    rows[0]["position"] = 0
    rows[1]["position"] = 1
    candidate["source_document_rows_sha256"] = sha256_bytes(
        canonical_json_bytes(rows)
    )


def _mutate_lexical_vector(candidate):
    packed = bytearray.fromhex(
        candidate["lexical_candidate_vector"]["packed_hex"]
    )
    packed[0] ^= 0b11000000
    candidate["lexical_candidate_vector"]["packed_hex"] = packed.hex()
    candidate["lexical_candidate_vector"]["packed_sha256"] = sha256_bytes(
        packed
    )


def _mutate_entry_kind_vector(candidate):
    packed = bytearray.fromhex(candidate["entry_kind_vector"]["packed_hex"])
    packed[0] ^= 1 << 7
    candidate["entry_kind_vector"]["packed_hex"] = packed.hex()
    candidate["entry_kind_vector"]["packed_sha256"] = sha256_bytes(packed)


def _mutate_identity_digest(candidate):
    candidate["source_member_census"]["source_member_identity_sha256"] = (
        "1" * 64
    )


def _mutate_candidate_authority(candidate):
    candidate["authority_boundary"][
        "lexical_candidate_is_source_authority"
    ] = True


def _mutate_semantic_equivalence(candidate):
    candidate["conditional_reason_code_law"][
        "semantic_equivalence_claimed"
    ] = True


def _mutate_counterexample(candidate):
    candidate["authority_boundary"]["minimum_counterexamples"][0][
        "required_action"
    ] = "accept"


def _mutate_range_witness(candidate):
    candidate["authority_boundary"]["numeric_range_rejection_witnesses"][
        "rows"
    ][0]["required_missing_reason_code"] = "invented"


def _mutate_implementation(candidate):
    candidate["derivation_identity"]["implementation_files"][0]["sha256"] = (
        "1" * 64
    )


def _mutate_extra_nested_key(candidate):
    candidate["integrity"]["fallback"] = True


@pytest.mark.parametrize(
    "mutation",
    [
        _mutate_registry,
        _mutate_source_rows,
        _mutate_derivation_metadata,
        _mutate_source_row_order,
        _mutate_lexical_vector,
        _mutate_entry_kind_vector,
        _mutate_identity_digest,
        _mutate_candidate_authority,
        _mutate_semantic_equivalence,
        _mutate_counterexample,
        _mutate_range_witness,
        _mutate_implementation,
        _mutate_extra_nested_key,
    ],
)
def test_self_consistent_mutation_classes_fail_closed(artifact, mutation):
    candidate = deepcopy(artifact)
    mutation(candidate)
    _repin_content(candidate)
    with pytest.raises(MissingReasonAuthorityError):
        validate_authority_artifact(candidate)


def test_integrity_digest_cannot_be_mutated_without_detection(artifact):
    candidate = deepcopy(artifact)
    candidate["integrity"]["content_sha256"] = "1" * 64
    with pytest.raises(MissingReasonAuthorityError, match="content digest"):
        validate_authority_artifact(candidate)
