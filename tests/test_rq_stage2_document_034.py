"""Validation and mutation coverage for the sealed q84 stage-2 shard."""

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

import build_rq_stage2_document_034 as builder  # noqa: E402


def _capture_root() -> Path:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            "/Users/maxghenis/PolicyEngine/psid-data",
        )
    )
    capture_root = psid_root / "documentation/capture1"
    if not (capture_root / "q84.pdf").exists():
        pytest.skip("staged PSID q84.pdf is unavailable")
    return capture_root


def _reseal(value: dict) -> dict:
    value["seal"] = builder._seal(value)
    value["integrity"]["content_sha256"] = builder._content_digest(value)
    return value


def test_document_034_reproduces_committed_sealed_annotation():
    capture_root = _capture_root()
    observed = builder.build_annotation(capture_root)
    assert builder.OUTPUT_PATH.read_bytes() == builder._canonical_bytes(
        observed
    )
    builder.validate_annotation(observed, capture_root)

    # Declared-domain facts the later era seal and global assembly depend on.
    assert observed["document_source_position"] == 34
    assert len(observed["questionnaire_page_rows"]) == builder.PAGE_COUNT
    assert [
        row["page_number"] for row in observed["questionnaire_page_rows"]
    ] == list(range(1, builder.PAGE_COUNT + 1))
    deferred = [
        row["page_number"]
        for row in observed["questionnaire_page_rows"]
        if row["annotation_status"] != "complete"
    ]
    assert deferred == [
        page
        for page in range(1, builder.PAGE_COUNT + 1)
        if page not in builder.ANNOTATED_PAGES
    ]
    assert (
        len(observed["candidate_disposition_rows"])
        == builder.CANDIDATE_DENOMINATOR
    )
    assert {
        row["adjudication_status"]
        for row in observed["candidate_disposition_rows"]
    } == {"complete"}
    assert {
        row["disposition"] for row in observed["candidate_disposition_rows"]
    } <= {"accepted", "modified", "split", "rejected"}
    # Every candidate and every emitted row is adjudicated exactly once.
    assert len(
        {row["candidate_id"] for row in observed["candidate_disposition_rows"]}
    ) == len(observed["candidate_disposition_rows"])
    assert len(
        {row["stage2_row_id"] for row in observed["output_adjudication_rows"]}
    ) == len(observed["output_adjudication_rows"])
    # No global catalog, alias, or relationship identifier is minted here.
    assert observed["authority_disposition"][
        "global_resolution_performed"
    ] is (False)


def test_document_034_mutations_fail_closed():
    capture_root = _capture_root()
    valid = builder.build_annotation(capture_root)
    mutations: list[dict] = []

    missing_page = copy.deepcopy(valid)
    missing_page["questionnaire_page_rows"].pop(0)
    mutations.append(missing_page)

    reordered_pages = copy.deepcopy(valid)
    reordered_pages["questionnaire_page_rows"][0:2] = reversed(
        reordered_pages["questionnaire_page_rows"][0:2]
    )
    mutations.append(reordered_pages)

    forced_complete = copy.deepcopy(valid)
    forced_complete["questionnaire_page_rows"][0][
        "annotation_status"
    ] = "complete"
    mutations.append(forced_complete)

    bad_span = copy.deepcopy(valid)
    bad_span["questionnaire_occurrence_rows"][0]["utf8_byte_end"] += 1
    mutations.append(bad_span)

    bad_hash = copy.deepcopy(valid)
    bad_hash["questionnaire_occurrence_rows"][0]["matched_utf8_sha256"] = (
        "0" * 64
    )
    mutations.append(bad_hash)

    bad_id = copy.deepcopy(valid)
    bad_id["questionnaire_occurrence_rows"][0][
        "questionnaire_occurrence_id"
    ] = ("psid-questionnaire-occurrence:" + "0" * 64)
    mutations.append(bad_id)

    reordered_occurrences = copy.deepcopy(valid)
    reordered_occurrences["questionnaire_occurrence_rows"][0:2] = reversed(
        reordered_occurrences["questionnaire_occurrence_rows"][0:2]
    )
    mutations.append(reordered_occurrences)

    illegal_ordinal = copy.deepcopy(valid)
    for row in illegal_ordinal["questionnaire_occurrence_rows"]:
        if row["semantic_ordinal_at_span"] != 0:
            row["semantic_ordinal_at_span"] = 0
            break
    else:  # pragma: no cover - the shard always has a multi-parent label
        raise AssertionError("no multi-parent label to mutate")
    mutations.append(illegal_ordinal)

    duplicate_atom = copy.deepcopy(valid)
    duplicate_atom["questionnaire_occurrence_rows"].append(
        copy.deepcopy(duplicate_atom["questionnaire_occurrence_rows"][0])
    )
    mutations.append(duplicate_atom)

    selected_path_subset = copy.deepcopy(valid)
    for row in selected_path_subset["questionnaire_occurrence_rows"]:
        if len(row["flow_branch_paths"]) > 1:
            row["flow_branch_paths"] = row["flow_branch_paths"][:1]
            break
    else:  # pragma: no cover - the shard always has a multi-path occurrence
        raise AssertionError("no multi-path occurrence to mutate")
    mutations.append(selected_path_subset)

    unrooted_path = copy.deepcopy(valid)
    unrooted_path["questionnaire_occurrence_rows"][0]["flow_branch_paths"] = [
        ["questionnaire-flow:" + "0" * 64]
    ]
    mutations.append(unrooted_path)

    later_parent = copy.deepcopy(valid)
    branches = later_parent["flow_branch_rows"]
    branches[0]["parent_flow_branch_id"] = branches[-1]["flow_branch_id"]
    mutations.append(later_parent)

    omitted_label = copy.deepcopy(valid)
    omitted_label["flow_branch_rows"].pop()
    mutations.append(omitted_label)

    duplicate_label_row = copy.deepcopy(valid)
    duplicate_label_row["flow_branch_rows"].append(
        copy.deepcopy(duplicate_label_row["flow_branch_rows"][0])
    )
    mutations.append(duplicate_label_row)

    cyclic_branch = copy.deepcopy(valid)
    first = cyclic_branch["flow_branch_rows"][0]
    first["branch_path"] = [*first["branch_path"], first["flow_branch_id"]]
    mutations.append(cyclic_branch)

    inferred_alias = copy.deepcopy(valid)
    inferred_alias["local_repeat_or_alias_evidence_rows"].append(
        {
            "local_repeat_evidence_id": "rq-local-repeat-evidence:" + "0" * 64,
            "alias_relation": "same_printed_identifier_and_exact_label",
            "alias_anchor_occurrence_id": valid[
                "local_anchor_classification_rows"
            ][0]["source_occurrence_id"],
            "referenced_anchor_occurrence_id": valid[
                "local_anchor_classification_rows"
            ][1]["source_occurrence_id"],
            "source_instruction_occurrence_ids": [],
            "unresolved_target_reference": None,
            "evidence_occurrence_ids": [],
            "handoff_status": "local_exact_identifier_and_label_for_global"
            "_assembly",
            "annotation_status": "complete",
        }
    )
    mutations.append(inferred_alias)

    changed_anchor_class = copy.deepcopy(valid)
    changed_anchor_class["local_anchor_classification_rows"][0][
        "classification"
    ] = "spouse_or_partner"
    mutations.append(changed_anchor_class)

    omitted_disposition = copy.deepcopy(valid)
    omitted_disposition["candidate_disposition_rows"].pop()
    mutations.append(omitted_disposition)

    unadjudicated_output = copy.deepcopy(valid)
    unadjudicated_output["output_adjudication_rows"].pop()
    mutations.append(unadjudicated_output)

    one_sided_adjudication = copy.deepcopy(valid)
    one_sided_adjudication["output_adjudication_rows"][0][
        "source_candidate_ids"
    ] = []
    mutations.append(one_sided_adjudication)

    dropped_note = copy.deepcopy(valid)
    dropped_note["correction_note_rows"].pop()
    mutations.append(dropped_note)

    changed_scope = copy.deepcopy(valid)
    changed_scope["document_local_annotation_scope"][
        "annotated_page_domain"
    ] = list(range(1, builder.PAGE_COUNT + 1))
    mutations.append(changed_scope)

    forbidden_global_output = copy.deepcopy(valid)
    forbidden_global_output["local_anchor_classification_rows"][0][
        "classification"
    ] = "psid-component-slot:0"
    mutations.append(forbidden_global_output)

    for index, mutated in enumerate(mutations):
        with pytest.raises(ValueError):
            builder.validate_annotation(_reseal(mutated), capture_root)
        assert index >= 0

    # A stale seal or integrity digest also fails closed.
    stale_seal = copy.deepcopy(valid)
    stale_seal["seal"]["row_domain_seal_rows"][0]["row_count"] += 1
    with pytest.raises(ValueError):
        builder.validate_annotation(stale_seal, capture_root)

    stale_integrity = copy.deepcopy(valid)
    stale_integrity["integrity"]["content_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        builder.validate_annotation(stale_integrity, capture_root)
