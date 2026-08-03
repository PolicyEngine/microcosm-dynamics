"""Validation and mutation coverage for the sealed q85 stage-2 shard."""

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

import build_rq_stage2_document_036 as builder  # noqa: E402


def _capture_root() -> Path:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            "/Users/maxghenis/PolicyEngine/psid-data",
        )
    )
    capture_root = psid_root / "documentation/capture1"
    if not (capture_root / "q85.pdf").exists():
        pytest.skip("staged PSID q85.pdf is unavailable")
    return capture_root


def _reseal(value: dict) -> dict:
    value["seal"] = builder._seal(value)
    value["integrity"]["content_sha256"] = builder._content_digest(value)
    return value


def test_document_036_reproduces_committed_sealed_annotation():
    capture_root = _capture_root()
    observed = builder.build_annotation(capture_root)
    assert builder.OUTPUT_PATH.read_bytes() == builder._canonical_bytes(
        observed
    )
    builder.validate_annotation(observed, capture_root)


def test_document_036_covers_every_replayed_page():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    page_rows = value["questionnaire_page_rows"]
    assert [row["page_number"] for row in page_rows] == list(
        range(1, builder.PAGE_COUNT + 1)
    )
    # Pages the reviewer read and deliberately left with no occurrence must
    # still be present; a zero-occurrence page is never an omitted page.
    assert any(not row["questionnaire_occurrence_ids"] for row in page_rows)
    assert all(row["annotation_status"] == "complete" for row in page_rows)


def test_document_036_dispositions_exact_cover_every_candidate():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    _, index = builder._load_replay_and_index()
    candidate = builder._load_candidate(index)
    expected = (
        1
        + len(candidate["candidate_page_rows"])
        + len(candidate["candidate_occurrence_rows"])
        + len(candidate["candidate_flow_path_rows"])
        + len(candidate["candidate_anchor_classification_rows"])
    )
    assert len(value["candidate_disposition_rows"]) == expected
    assert all(
        row["adjudication_status"] == "complete"
        for row in value["candidate_disposition_rows"]
    )


def test_document_036_emits_no_global_or_authority_artifact():
    capture_root = _capture_root()
    value = builder.build_annotation(capture_root)
    disposition = value["authority_disposition"]
    assert disposition["authority_kind"] == "nonauthority_document_shard"
    assert disposition["sealed_document_count"] == 1
    for flag in (
        "closes_class_a_residual",
        "closes_class_b_residual",
        "emits_era_seal",
        "emits_global_alias_catalog",
        "emits_global_node_ids",
        "emits_q5_artifact",
        "emits_r_q",
        "read_inventory_crosswalk_reader_or_legal_registry",
    ):
        assert disposition[flag] is False
    blob = builder._canonical_bytes(value).decode("ascii")
    for prefix in builder.FORBIDDEN_GLOBAL_PREFIXES:
        assert prefix not in blob


def test_document_036_mutations_fail_closed():
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

    emptied_projection = copy.deepcopy(valid)
    populated = next(
        row
        for row in emptied_projection["questionnaire_page_rows"]
        if row["questionnaire_occurrence_ids"]
    )
    populated["questionnaire_occurrence_ids"] = []
    mutations.append(emptied_projection)

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

    bad_occurrence_id = copy.deepcopy(valid)
    bad_occurrence_id["questionnaire_occurrence_rows"][0][
        "questionnaire_occurrence_id"
    ] = ("psid-questionnaire-occurrence:" + "0" * 64)
    mutations.append(bad_occurrence_id)

    bad_locator_id = copy.deepcopy(valid)
    bad_locator_id["whole_document_locator_rows"][0]["locator_id"] = (
        "psid-whole-document:" + "0" * 64
    )
    mutations.append(bad_locator_id)

    broken_locator_equation = copy.deepcopy(valid)
    broken_locator_equation["whole_document_locator_rows"][0]["byte_start"] = 1
    mutations.append(broken_locator_equation)

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

    reordered_paths = copy.deepcopy(valid)
    order_row = next(
        row
        for row in reordered_paths["questionnaire_occurrence_rows"]
        if len(row["flow_branch_paths"]) > 1
    )
    order_row["flow_branch_paths"] = list(
        reversed(order_row["flow_branch_paths"])
    )
    mutations.append(reordered_paths)

    inferred_alias = copy.deepcopy(valid)
    explicit_repeat = next(
        row
        for row in inferred_alias["local_repeat_or_alias_evidence_rows"]
        if row["alias_relation"] != "same_printed_identifier_and_exact_label"
    )
    explicit_repeat["alias_relation"] = "inferred_job_number_equivalence"
    mutations.append(inferred_alias)

    dropped_repeat = copy.deepcopy(valid)
    dropped_repeat["local_repeat_or_alias_evidence_rows"].pop()
    mutations.append(dropped_repeat)

    normalized_label = copy.deepcopy(valid)
    foldable = next(
        row
        for row in normalized_label["local_anchor_classification_rows"]
        if row["exact_label"] != row["exact_label"].upper()
    )
    foldable["exact_label"] = foldable["exact_label"].upper()
    mutations.append(normalized_label)

    normalized_whitespace = copy.deepcopy(valid)
    spaced = next(
        row
        for row in normalized_whitespace["local_anchor_classification_rows"]
        if "\n" in row["exact_label"] or "  " in row["exact_label"]
    )
    spaced["exact_label"] = " ".join(spaced["exact_label"].split())
    mutations.append(normalized_whitespace)

    forbidden_global_id = copy.deepcopy(valid)
    forbidden_global_id["local_anchor_classification_rows"][0][
        "local_classification"
    ] = ("psid-job-slot:" + "0" * 64)
    mutations.append(forbidden_global_id)

    omitted_candidate = copy.deepcopy(valid)
    omitted_candidate["candidate_disposition_rows"].pop()
    mutations.append(omitted_candidate)

    rejected_names_row = copy.deepcopy(valid)
    rejected = next(
        row
        for row in rejected_names_row["candidate_disposition_rows"]
        if row["disposition"] == "rejected"
    )
    rejected["stage2_row_ids"] = [
        rejected_names_row["questionnaire_occurrence_rows"][0][
            "questionnaire_occurrence_id"
        ]
    ]
    mutations.append(rejected_names_row)

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

    unreviewed_output = copy.deepcopy(valid)
    unreviewed_output["output_adjudication_rows"][0][
        "whole_page_review_complete"
    ] = False
    mutations.append(unreviewed_output)

    missing_note = copy.deepcopy(valid)
    missing_note["correction_note_rows"].pop()
    mutations.append(missing_note)

    claimed_authority = copy.deepcopy(valid)
    claimed_authority["authority_disposition"]["emits_r_q"] = True
    mutations.append(claimed_authority)

    for mutation in mutations:
        with pytest.raises(ValueError):
            builder.validate_annotation(_reseal(mutation), capture_root)
