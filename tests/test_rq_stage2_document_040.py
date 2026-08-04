"""Validation and mutation coverage for the sealed q87 stage-2 shard."""

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

import build_rq_stage2_document_040 as builder  # noqa: E402


def _capture_root() -> Path:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            "/Users/maxghenis/PolicyEngine/psid-data",
        )
    )
    capture_root = psid_root / "documentation/capture1"
    if not (capture_root / "q87.pdf").exists():
        pytest.skip("staged PSID q87.pdf is unavailable")
    return capture_root


def _reseal(value: dict) -> dict:
    value["seal"] = builder._seal(value)
    value["integrity"]["content_sha256"] = builder._content_digest(value)
    return value


def test_document_040_reproduces_committed_sealed_annotation():
    capture_root = _capture_root()
    observed = builder.build_annotation(capture_root)
    assert builder.OUTPUT_PATH.read_bytes() == builder._canonical_bytes(
        observed
    )
    builder.validate_annotation(observed, capture_root)


def test_document_040_mutations_fail_closed():
    capture_root = _capture_root()
    valid = builder.build_annotation(capture_root)

    mutations = []

    missing_page = copy.deepcopy(valid)
    missing_page["questionnaire_page_rows"].pop(0)
    mutations.append(missing_page)

    reordered_page = copy.deepcopy(valid)
    reordered_page["questionnaire_page_rows"][0:2] = reversed(
        reordered_page["questionnaire_page_rows"][0:2]
    )
    mutations.append(reordered_page)

    bad_span = copy.deepcopy(valid)
    bad_span["questionnaire_occurrence_rows"][0]["utf8_byte_end"] += 1
    mutations.append(bad_span)

    bad_hash = copy.deepcopy(valid)
    bad_hash["questionnaire_occurrence_rows"][0]["matched_utf8_sha256"] = (
        "0" * 64
    )
    mutations.append(bad_hash)

    bad_locator_hash = copy.deepcopy(valid)
    bad_locator_hash["questionnaire_occurrence_rows"][0][
        "source_locator_sha256"
    ] = ("0" * 64)
    mutations.append(bad_locator_hash)

    bad_id = copy.deepcopy(valid)
    bad_id["questionnaire_occurrence_rows"][0][
        "questionnaire_occurrence_id"
    ] = ("psid-questionnaire-occurrence:" + "0" * 64)
    mutations.append(bad_id)

    illegal_ordinal = copy.deepcopy(valid)
    nonflow = next(
        row
        for row in illegal_ordinal["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] != "flow_branch_label"
    )
    nonflow["semantic_ordinal_at_span"] = 1
    mutations.append(illegal_ordinal)

    duplicate_atom = copy.deepcopy(valid)
    duplicate_atom["questionnaire_occurrence_rows"].append(
        copy.deepcopy(duplicate_atom["questionnaire_occurrence_rows"][-1])
    )
    mutations.append(duplicate_atom)

    unresolved_parent = copy.deepcopy(valid)
    unresolved_parent["flow_branch_rows"][0]["parent_flow_branch_id"] = (
        "questionnaire-flow:" + "0" * 64
    )
    mutations.append(unresolved_parent)

    later_parent = copy.deepcopy(valid)
    later_parent["flow_branch_rows"][0]["parent_flow_branch_id"] = (
        later_parent["flow_branch_rows"][-1]["flow_branch_id"]
    )
    mutations.append(later_parent)

    cyclic_parent = copy.deepcopy(valid)
    cyclic_parent["flow_branch_rows"][0]["parent_flow_branch_id"] = (
        cyclic_parent["flow_branch_rows"][0]["flow_branch_id"]
    )
    mutations.append(cyclic_parent)

    omitted_label = copy.deepcopy(valid)
    omitted_label["flow_branch_rows"].pop(0)
    mutations.append(omitted_label)

    duplicate_label = copy.deepcopy(valid)
    duplicate_label["flow_branch_rows"].append(
        copy.deepcopy(duplicate_label["flow_branch_rows"][-1])
    )
    mutations.append(duplicate_label)

    selected_path_subset = copy.deepcopy(valid)
    multipath = next(
        row
        for row in selected_path_subset["questionnaire_occurrence_rows"]
        if len(row["flow_branch_paths"]) > 1
    )
    multipath["flow_branch_paths"] = multipath["flow_branch_paths"][:1]
    mutations.append(selected_path_subset)

    duplicate_path = copy.deepcopy(valid)
    path_row = next(
        row
        for row in duplicate_path["questionnaire_occurrence_rows"]
        if len(row["flow_branch_paths"]) > 1
    )
    path_row["flow_branch_paths"].append(
        copy.deepcopy(path_row["flow_branch_paths"][0])
    )
    mutations.append(duplicate_path)

    inferred_alias = copy.deepcopy(valid)
    explicit_repeat = next(
        row
        for row in inferred_alias["local_repeat_or_alias_evidence_rows"]
        if row["alias_relation"] != "same_printed_identifier_and_exact_label"
    )
    explicit_repeat["alias_relation"] = (
        "same_printed_identifier_and_exact_label"
    )
    mutations.append(inferred_alias)

    omitted_candidate = copy.deepcopy(valid)
    omitted_candidate["candidate_disposition_rows"].pop()
    mutations.append(omitted_candidate)

    unadjudicated_output = copy.deepcopy(valid)
    unadjudicated_output["output_adjudication_rows"].pop()
    mutations.append(unadjudicated_output)

    one_sided_mapping = copy.deepcopy(valid)
    backed_output = next(
        row
        for row in one_sided_mapping["output_adjudication_rows"]
        if row["source_candidate_ids"]
    )
    backed_output["source_candidate_ids"] = []
    backed_output["adjudication_action"] = "manual_add"
    mutations.append(one_sided_mapping)

    one_sided_forward = copy.deepcopy(valid)
    forward_row = next(
        row
        for row in one_sided_forward["candidate_disposition_rows"]
        if row["stage2_row_ids"]
    )
    forward_row["stage2_row_ids"] = []
    forward_row["disposition"] = "rejected"
    mutations.append(one_sided_forward)

    missing_note = copy.deepcopy(valid)
    missing_note["correction_note_rows"].pop()
    mutations.append(missing_note)

    forbidden_global_id = copy.deepcopy(valid)
    forbidden_global_id["local_anchor_classification_rows"][0][
        "exact_label"
    ] = ("psid-job-slot:" + "0" * 64)
    mutations.append(forbidden_global_id)

    for mutation in mutations:
        with pytest.raises(ValueError):
            builder.validate_annotation(_reseal(mutation), capture_root)


def test_document_040_candidate_domain_is_exact_covered_once():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    replay, index = builder._load_replay_and_index()
    candidate = builder._load_candidate(replay, index)
    expected = builder._candidate_domain(candidate)
    observed = [
        (row["candidate_row_kind"], row["candidate_id"])
        for row in value["candidate_disposition_rows"]
    ]
    assert observed == expected
    assert len(observed) == builder.CANDIDATE_DENOMINATOR
    assert len(set(observed)) == len(observed)
    assert {
        row["disposition"] for row in value["candidate_disposition_rows"]
    } <= {
        "accepted",
        "modified",
        "split",
        "rejected",
    }
    assert all(
        row["adjudication_status"] == "complete"
        for row in value["candidate_disposition_rows"]
    )


def test_document_040_pages_exact_cover_every_replayed_page():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    pages = value["questionnaire_page_rows"]
    assert [row["page_number"] for row in pages] == list(
        range(1, builder.PAGE_COUNT + 1)
    )
    assert all(row["annotation_status"] == "complete" for row in pages)
    empty = [row for row in pages if not row["questionnaire_occurrence_ids"]]
    assert empty, "pages with an empty occurrence array must still be covered"
    projected = [
        occurrence_id
        for row in pages
        for occurrence_id in row["questionnaire_occurrence_ids"]
    ]
    assert projected == [
        row["questionnaire_occurrence_id"]
        for row in value["questionnaire_occurrence_rows"]
    ]


def test_document_040_manual_additions_are_reviewed_and_verified():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    manual = [
        row
        for row in value["output_adjudication_rows"]
        if row["adjudication_action"] == "manual_add"
    ]
    assert manual
    for row in manual:
        assert row["source_candidate_ids"] == []
        assert row["whole_page_review_complete"] is True
        assert row["source_span_verified"] is True


def test_document_040_emits_no_global_authority_artifact():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    assert (
        value["authority_disposition"]["global_resolution_performed"] is False
    )
    assert (
        value["authority_disposition"]["canonical_q5_artifact_emitted"]
        is False
    )
    assert (
        value["authority_disposition"]["canonical_era_seal_emitted"] is False
    )
    assert value["local_repeat_or_alias_evidence_rows"]
    for row in value["local_repeat_or_alias_evidence_rows"]:
        assert row["alias_relation"] in {
            "explicit_repeat_instruction",
            "explicit_cross_reference",
            "same_printed_identifier_and_exact_label",
        }
        assert row["evidence_occurrence_ids"]
        assert row["annotation_status"] == "complete"
