"""Validation and mutation coverage for the sealed document-5 stage-2 shard.

The shard is `documentation/capture1/fam1970_QxQs.pdf` (wave 1970, 91 pages).
Every test here re-derives the annotation from the registered PDF and the
committed reviewer source review, so a drifted page digest, span, hash, ID,
ordering, branch ancestry, or adjudication relation fails loudly.
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_005_annotation as builder  # noqa: E402


def _require_source() -> None:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            str(Path.home() / "PolicyEngine" / "psid-data"),
        )
    )
    if not (psid_root / builder.CANONICAL_SOURCE_PATH).exists():
        pytest.skip("staged PSID fam1970_QxQs.pdf is unavailable")


@pytest.fixture(scope="module")
def built() -> tuple[dict, list[str]]:
    _require_source()
    value = builder.build_annotation()
    pages = builder._page_texts_for_validation()
    return value, pages


def test_reproduces_committed_sealed_annotation(built):
    value, pages = built
    assert builder.OUTPUT_PATH.read_bytes() == builder._canonical_bytes(value)
    builder.validate_annotation(value, pages)


def test_shard_is_nonauthority_and_single_document(built):
    value, _pages = built
    assert value["document_source_position"] == 5
    assert value["authority_kind"] == builder.AUTHORITY_KIND
    statement = value["nonauthority_statement"]
    assert statement["one_document_only"] is True
    assert statement["status"] == "nonauthority"
    for key in (
        "era_seal_emitted",
        "global_alias_resolution_emitted",
        "global_catalog_emitted",
        "hierarchy_emitted",
        "legal_registry_read",
        "q5_emitted",
        "r_q_emitted",
        "slot_or_inventory_emitted",
    ):
        assert statement[key] is False
    assert value["seal"]["global_ids_assigned"] is False
    assert not builder._contains_global_id(value)


def test_whole_file_locator_equations(built):
    value, _pages = built
    locator = value["whole_document_locator"]
    assert tuple(locator) == builder.LOCATOR_KEYS
    assert locator["location_type"] == "whole_document_exact_file_range"
    assert locator["byte_start"] == 0
    assert locator["byte_end"] == locator["size_bytes"]
    assert locator["range_sha256"] == locator["full_file_sha256"]
    assert locator["pdf_page_domain"] == "all_pages_and_flow_branches"
    assert locator["interview_wave"] == builder.INTERVIEW_WAVE


def test_page_cover_includes_every_empty_occurrence_page(built):
    value, _pages = built
    page_rows = value["questionnaire_page_rows"]
    assert [row["page_number"] for row in page_rows] == list(
        range(1, builder.PAGE_COUNT + 1)
    )
    assert all(row["annotation_status"] == "complete" for row in page_rows)
    empty = [
        row for row in page_rows if not row["questionnaire_occurrence_ids"]
    ]
    # A reviewed page with no occurrence is still a covered page.
    assert empty
    assert value["seal"]["empty_occurrence_page_count"] == len(empty)


def test_occurrence_kinds_are_the_ten_ordered_section_19_kinds(built):
    value, _pages = built
    kinds = {
        row["occurrence_kind"]
        for row in value["questionnaire_occurrence_rows"]
    }
    assert kinds <= set(builder.OCCURRENCE_KINDS)
    census = value["seal"]["questionnaire_occurrence_counts_by_kind"]
    assert set(census) == set(builder.OCCURRENCE_KINDS)
    assert sum(census.values()) == len(value["questionnaire_occurrence_rows"])


def test_every_occurrence_resolves_through_its_page_exactly_once(built):
    value, _pages = built
    projections = {
        row["page_number"]: row["questionnaire_occurrence_ids"]
        for row in value["questionnaire_page_rows"]
    }
    seen: set[str] = set()
    for row in value["questionnaire_occurrence_rows"]:
        identifier = row["questionnaire_occurrence_id"]
        assert projections[row["page_number"]].count(identifier) == 1
        assert identifier not in seen
        seen.add(identifier)


def test_branch_rows_are_one_to_one_with_labels_and_acyclic(built):
    value, _pages = built
    labels = [
        row
        for row in value["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    branches = value["flow_branch_rows"]
    assert len(branches) == len(labels)
    assert len({row["source_occurrence_id"] for row in branches}) == len(
        branches
    )
    by_id = {row["flow_branch_id"]: row for row in branches}
    for row in branches:
        assert row["branch_path"][-1] == row["flow_branch_id"]
        assert row["branch_path"][-2] == row["parent_flow_branch_id"]
        seen: set[str] = set()
        cursor = row["flow_branch_id"]
        while cursor != builder.FLOW_ROOT:
            assert cursor not in seen
            seen.add(cursor)
            cursor = by_id[cursor]["parent_flow_branch_id"]


def test_branch_compatibility_is_existential_and_serializes_no_witness(built):
    value, _pages = built
    occurrences = value["questionnaire_occurrence_rows"]
    resolved = [row["branch_path"] for row in value["flow_branch_rows"]]
    unconditional = [
        row
        for row in occurrences
        if row["flow_branch_paths"] == [[builder.FLOW_ROOT]]
    ][:3]
    assert unconditional
    # Unconditional rows are compatible with every resolved path.
    assert builder.branch_compatible(unconditional, resolved) is True
    # The predicate returns only a boolean; no witness path escapes.
    assert builder.branch_compatible(unconditional, resolved) is not resolved
    assert isinstance(builder.branch_compatible(unconditional, resolved), bool)
    with pytest.raises(ValueError):
        builder.branch_compatible([], resolved)


def test_local_anchors_carry_exact_source_evidence(built):
    value, _pages = built
    occurrences = {
        row["questionnaire_occurrence_id"]: row
        for row in value["questionnaire_occurrence_rows"]
    }
    anchors = value["local_anchor_classification_rows"]
    anchor_atoms = {
        identifier
        for identifier, row in occurrences.items()
        if row["occurrence_kind"] in builder.ANCHOR_KINDS
    }
    assert {row["source_occurrence_id"] for row in anchors} == anchor_atoms
    for row in anchors:
        source = occurrences[row["source_occurrence_id"]]
        assert row["exact_label"] == source["matched_text"]
        assert row["classification_status"] == "provisional_document_local"
        # no global node or relationship ID is assigned locally
        assert not row["local_anchor_classification_id"].startswith(
            ("psid-job-slot:", "psid-component-slot:", "psid-node-alias:")
        )


def test_every_repeat_instruction_is_dispositioned(built):
    value, _pages = built
    instructions = {
        row["questionnaire_occurrence_id"]
        for row in value["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    repeats = value["local_repeat_alias_evidence_rows"]
    assert {row["source_occurrence_id"] for row in repeats} == instructions
    for row in repeats:
        assert row["relation"] in builder.ALIAS_RELATIONS
        assert row["source_occurrence_id"] in row["evidence_occurrence_ids"]
        # cross-document targets stay unresolved in the shard
        assert row["resolution_status"] == "deferred_to_global_assembly"


def test_candidate_domain_is_exact_covered_once(built):
    value, _pages = built
    replay, index = builder._pinned_inputs()
    _document, manifest, _pages_rows = builder._document_identity(
        replay, index
    )
    candidates = builder._load_candidates(manifest)
    expected = (
        {
            candidates["whole_document_locator_candidate"][
                "candidate_locator_id"
            ]
        }
        | {
            row["candidate_page_id"]
            for row in candidates["candidate_page_rows"]
        }
        | {
            row["candidate_occurrence_id"]
            for row in candidates["candidate_occurrence_rows"]
        }
        | {
            row["candidate_flow_path_id"]
            for row in candidates["candidate_flow_path_rows"]
        }
        | {
            row["candidate_anchor_classification_id"]
            for row in candidates["candidate_anchor_classification_rows"]
        }
    )
    dispositions = value["candidate_disposition_rows"]
    observed = [row["candidate_id"] for row in dispositions]
    assert len(observed) == len(set(observed))
    assert set(observed) == expected
    assert all(
        row["adjudication_status"] == "complete" for row in dispositions
    )


def test_output_domain_is_exact_adjudicated_once(built):
    value, _pages = built
    adjudications = value["output_adjudication_rows"]
    observed = [row["stage2_row_id"] for row in adjudications]
    assert len(observed) == len(set(observed))
    expected = (
        [value["whole_document_locator"]["locator_id"]]
        + [
            row["questionnaire_page_id"]
            for row in value["questionnaire_page_rows"]
        ]
        + [
            row["questionnaire_occurrence_id"]
            for row in value["questionnaire_occurrence_rows"]
        ]
        + [row["flow_branch_id"] for row in value["flow_branch_rows"]]
        + [
            row["local_anchor_classification_id"]
            for row in value["local_anchor_classification_rows"]
        ]
        + [
            row["local_repeat_alias_evidence_id"]
            for row in value["local_repeat_alias_evidence_rows"]
        ]
    )
    assert set(observed) == set(expected)
    for row in adjudications:
        assert row["whole_page_review_complete"] is True
        assert row["source_span_verified"] is True
        if row["adjudication_action"] == "manual_add":
            assert row["source_candidate_ids"] == []
        else:
            assert row["source_candidate_ids"]


def test_no_candidate_auto_promoted(built):
    value, _pages = built
    # Every emitted row is an explicit decision, including one that happens to
    # equal a candidate: the accepted action is still recorded per row.
    actions = {
        row["adjudication_action"] for row in value["output_adjudication_rows"]
    }
    assert actions <= set(builder.ADJUDICATION_ACTIONS)
    assert "manual_add" in actions, "reviewer additions must be recorded"


def test_mutations_are_rejected(built):
    value, pages = built
    mutations = builder._mutations(value)
    assert len(mutations) >= 17
    survived = []
    for label, broken in mutations:
        try:
            builder.validate_annotation(broken, pages)
        except Exception:  # noqa: BLE001 - a rejection is the pass condition
            continue
        survived.append(label)
    assert not survived, f"mutations not rejected: {survived}"


def test_source_review_is_reviewer_authored_and_complete(built):
    _value, pages = built
    review = builder._load_review()
    assert review["authority_kind"] == (
        "reviewer_authored_source_bytes_only_nonauthority"
    )
    assert review["review_method"]["global_ids_assigned"] is False
    assert len(review["page_review_rows"]) == builder.PAGE_COUNT
    assert all(
        row["whole_page_review_complete"] is True
        for row in review["page_review_rows"]
    )
    builder.validate_review(review, pages)


def test_review_span_drift_is_rejected(built):
    _value, pages = built
    review = copy.deepcopy(builder._load_review())
    review["occurrence_specs"][0]["utf8_byte_start"] = review[
        "occurrence_specs"
    ][0]["utf8_byte_end"]
    with pytest.raises(ValueError):
        builder.validate_review(review, pages)
