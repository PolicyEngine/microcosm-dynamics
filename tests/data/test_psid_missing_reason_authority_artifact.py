"""Committed fail-closed artifact and mutation gates for Amendment 11."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from populace_dynamics.data.psid_missing_reason_authority import (
    AUTHORITY_FAILURE_DISPOSITION_ROWS,
    CONFLICTING_AUTHORITY_FAILURE_STATES,
    CONFLICTING_MISSING_REASON_AUTHORITY,
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
    EXPECTED_SOURCE_AUTHORIZED_AUDIT_BYTE_SIZE,
    EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256,
    EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT,
    EXPECTED_SOURCE_AUTHORIZED_OCCURRENCE_SHA256,
    EXPECTED_SOURCE_DOCUMENT_ROWS_SHA256,
    EXPECTED_UNADJUDICATED_LITERAL_COUNT,
    INCOMPLETE_AUTHORITY_FAILURE_STATES,
    INCOMPLETE_MISSING_REASON_AUTHORITY,
    REASON_CODE_PREFIX,
    SOURCE_AUTHORIZED_DISPOSITION,
    SOURCE_AUTHORIZED_MEANING,
    SOURCE_AUTHORIZED_VALUE_LEXEME,
    MissingReasonAuthorityError,
    canonical_json_bytes,
    settle_missing_reason_codes,
    sha256_bytes,
    utf8_compact_json_bytes,
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


_REPRESENTATIVE_OBJECT_PATHS = (
    (),
    ("authority_boundary",),
    ("authority_boundary", "directly_disproven_candidates", 0),
    ("authority_boundary", "numeric_range_rejection_witnesses"),
    (
        "authority_boundary",
        "numeric_range_rejection_witnesses",
        "rows",
        0,
    ),
    ("authority_boundary", "rejection_class_witnesses", 0),
    ("authority_boundary", "source_authorized_missing_audit", "rows", 0),
    ("conditional_reason_code_law",),
    ("derivation_identity",),
    ("derivation_identity", "implementation_files", 0),
    ("entry_kind_vector",),
    ("integrity",),
    ("registered_source_identity",),
    ("source_document_rows", 0),
    ("source_member_census",),
    ("source_member_census", "overlapping_candidate_phrase_counts"),
    ("source_member_census", "selected_exact_candidate_meaning_counts"),
)


def _value_at_path(value: Any, path: tuple[str | int, ...]) -> Any:
    for part in path:
        value = value[part]
    return value


def _iter_objects(
    value: Any, path: tuple[str | int, ...] = ()
) -> Iterator[tuple[tuple[str | int, ...], Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        yield path, value
        for key, nested in value.items():
            yield from _iter_objects(nested, (*path, key))
    elif isinstance(value, list):
        for position, nested in enumerate(value):
            yield from _iter_objects(nested, (*path, position))


def _iter_suffix_sha256_paths(
    value: Any, path: tuple[str | int, ...]
) -> Iterator[tuple[str | int, ...]]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            nested_path = (*path, key)
            if key.endswith("_sha256"):
                yield nested_path
            yield from _iter_suffix_sha256_paths(nested, nested_path)
    elif isinstance(value, list):
        for position, nested in enumerate(value):
            yield from _iter_suffix_sha256_paths(nested, (*path, position))


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


def test_candidate_counts_are_distinct_from_exact_source_authority(artifact):
    census = artifact["source_member_census"]
    boundary = artifact["authority_boundary"]
    assert census["pdf_source_row_count"] == 89_599
    assert census["pdf_source_member_count"] == 479_345
    assert census["pdf_lexical_missing_candidate_count"] == 203_283
    assert census["value_label_lexical_missing_candidate_count"] == 27_980
    assert boundary["lexical_candidate_is_source_authority"] is False
    assert boundary["authorized_current_literal_disposition_count"] == (
        EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
    )
    assert boundary["unadjudicated_literal_count"] == (
        EXPECTED_UNADJUDICATED_LITERAL_COUNT
    )
    assert (
        boundary["authorized_current_literal_disposition_count"]
        + boundary["unadjudicated_literal_count"]
        == EXPECTED_LITERAL_COUNT
    )
    assert boundary["source_defines_missing_disposition_vocabulary"] is True
    assert boundary["source_defines_reason_vocabulary"] is True
    assert boundary["source_defines_missing_disposition_column"] is False
    assert boundary["source_defines_reason_code_column"] is False
    assert boundary["inherited_dictionary_missing_declaration_count"] == 0
    assert boundary["dictionary_missing_declaration_scope"].startswith(
        "inherited_86_document"
    )


def test_all_52_authorized_occurrences_preserve_exact_source_bytes(artifact):
    census = artifact["source_member_census"]
    boundary = artifact["authority_boundary"]
    occurrences = boundary["source_authorized_missing_occurrences"]
    audit = boundary["source_authorized_missing_audit"]
    assert occurrences["row_count"] == EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
    assert occurrences["domain_sha256"] == (
        EXPECTED_SOURCE_AUTHORIZED_OCCURRENCE_SHA256
    )
    assert audit["row_count"] == EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
    assert audit["domain_sha256"] == EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256
    assert len(utf8_compact_json_bytes(audit["rows"])) == (
        EXPECTED_SOURCE_AUTHORIZED_AUDIT_BYTE_SIZE
    )
    assert census["source_authorized_missing_literal_count"] == (
        EXPECTED_SOURCE_AUTHORIZED_MISSING_COUNT
    )
    assert census["source_authorized_missing_audit_sha256"] == (
        EXPECTED_SOURCE_AUTHORIZED_AUDIT_SHA256
    )
    assert census["source_authorized_missing_occurrence_sha256"] == (
        EXPECTED_SOURCE_AUTHORIZED_OCCURRENCE_SHA256
    )
    assert {
        (row[0][10], row[0][11], row[4]) for row in occurrences["rows"]
    } == {
        (
            SOURCE_AUTHORIZED_VALUE_LEXEME,
            SOURCE_AUTHORIZED_MEANING,
            SOURCE_AUTHORIZED_DISPOSITION,
        )
    }
    assert all(
        row[5].startswith(REASON_CODE_PREFIX)
        and len(row[5]) == len(REASON_CODE_PREFIX) + 64
        for row in occurrences["rows"]
    )
    assert len({row[5] for row in occurrences["rows"]}) == 52
    assert {
        (
            row["source_value_lexeme"],
            row["source_meaning"],
            row["typed_disposition"],
        )
        for row in audit["rows"]
    } == {
        (
            SOURCE_AUTHORIZED_VALUE_LEXEME,
            SOURCE_AUTHORIZED_MEANING,
            SOURCE_AUTHORIZED_DISPOSITION,
        )
    }


def test_artifact_pins_total_failure_disposition_partition(artifact):
    law = artifact["conditional_reason_code_law"]
    assert law["authority_failure_disposition_rows"] == [
        list(row) for row in AUTHORITY_FAILURE_DISPOSITION_ROWS
    ]
    assert law["authority_failure_precedence"] == [
        CONFLICTING_MISSING_REASON_AUTHORITY,
        INCOMPLETE_MISSING_REASON_AUTHORITY,
    ]
    assert law["conflicting_failure_states"] == list(
        CONFLICTING_AUTHORITY_FAILURE_STATES
    )
    assert law["incomplete_failure_states"] == list(
        INCOMPLETE_AUTHORITY_FAILURE_STATES
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


def _object_path_id(path: tuple[str | int, ...]) -> str:
    return "top_level" if not path else ".".join(map(str, path))


def test_omitted_key_object_shape_matrix_is_complete(artifact):
    discovered_keysets = {
        frozenset(value) for _, value in _iter_objects(artifact)
    }
    represented_keysets = []
    for path in _REPRESENTATIVE_OBJECT_PATHS:
        representative = _value_at_path(artifact, path)
        assert isinstance(representative, Mapping)
        represented_keysets.append(frozenset(representative))
    assert len(discovered_keysets) == 17
    assert len(set(represented_keysets)) == len(represented_keysets)
    assert discovered_keysets == set(represented_keysets)
    assert sum(map(len, represented_keysets)) == 181


@pytest.mark.parametrize(
    "path",
    _REPRESENTATIVE_OBJECT_PATHS,
    ids=_object_path_id,
)
def test_every_key_in_representative_object_shape_is_required(artifact, path):
    keys = sorted(_value_at_path(artifact, path))
    for key in keys:
        candidate = deepcopy(artifact)
        del _value_at_path(candidate, path)[key]
        if (
            "integrity" in candidate
            and "content_sha256" in candidate["integrity"]
        ):
            _repin_content(candidate)
        with pytest.raises(MissingReasonAuthorityError):
            validate_authority_artifact(candidate)


def test_every_census_and_boundary_sha256_field_is_directly_mutated(artifact):
    paths = tuple(
        _iter_suffix_sha256_paths(
            artifact["source_member_census"], ("source_member_census",)
        )
    ) + tuple(
        _iter_suffix_sha256_paths(
            artifact["authority_boundary"], ("authority_boundary",)
        )
    )
    assert len(paths) == 18
    assert len(set(paths)) == len(paths)
    for path in paths:
        candidate = deepcopy(artifact)
        parent = _value_at_path(candidate, path[:-1])
        replacement = "0" * 64
        if parent[path[-1]] == replacement:
            replacement = "1" * 64
        parent[path[-1]] = replacement
        _repin_content(candidate)
        with pytest.raises(MissingReasonAuthorityError):
            validate_authority_artifact(candidate)


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
