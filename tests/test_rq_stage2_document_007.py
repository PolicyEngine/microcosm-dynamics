"""Validation and mutation coverage for the sealed fam1971_QxQs shard."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage2_document_007 as builder  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

KIND_ORDER = {
    kind: index for index, kind in enumerate(builder.OCCURRENCE_KINDS)
}


def _capture_root() -> Path:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            "/Users/maxghenis/PolicyEngine/psid-data",
        )
    )
    capture_root = psid_root / "documentation/capture1"
    if not (capture_root / builder.PDF_FILENAME).exists():
        pytest.skip("staged PSID fam1971_QxQs.pdf is unavailable")
    return capture_root


def _reseal(value: dict) -> dict:
    value["seal"] = builder._seal(value)
    value["integrity"]["content_sha256"] = builder._content_digest(value)
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def test_document_007_reproduces_committed_sealed_annotation():
    capture_root = _capture_root()
    observed = builder.build_annotation(capture_root)
    assert builder.OUTPUT_PATH.read_bytes() == builder._canonical_bytes(
        observed
    )
    builder.validate_annotation(observed, capture_root)


def test_document_007_committed_shard_verifies_against_source_bytes():
    """Re-derive every sealed row straight from the PDF, not the builder."""

    capture_root = _capture_root()
    committed = json.loads(builder.OUTPUT_PATH.read_text(encoding="utf-8"))

    pdf_path = capture_root / builder.PDF_FILENAME
    raw = pdf_path.read_bytes()
    assert len(raw) == builder.PDF_SIZE
    assert _sha256(raw) == builder.PDF_SHA256
    page_texts = questionnaire_inventory._pdftotext_pages(pdf_path)
    assert len(page_texts) == builder.PAGE_COUNT

    locator_rows = committed["whole_document_locator_rows"]
    assert len(locator_rows) == 1
    locator = locator_rows[0]
    assert locator["location_type"] == "whole_document_exact_file_range"
    assert locator["byte_start"] == 0
    assert locator["byte_end"] == locator["size_bytes"] == builder.PDF_SIZE
    assert locator["range_sha256"] == locator["full_file_sha256"]
    assert locator["full_file_sha256"] == builder.PDF_SHA256
    assert locator["pdf_page_domain"] == "all_pages_and_flow_branches"
    assert locator["locator_id"] == "psid-whole-document:" + builder._digest(
        [
            builder.DOCUMENT_ID,
            builder.INTERVIEW_WAVE,
            builder.PDF_SHA256,
            builder.PDF_SIZE,
        ]
    )

    pages = committed["questionnaire_page_rows"]
    occurrences = committed["questionnaire_occurrence_rows"]
    assert [row["page_number"] for row in pages] == list(
        range(1, builder.PAGE_COUNT + 1)
    )
    for page_row, page_text in zip(pages, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        assert page_row["page_text_utf8_sha256"] == _sha256(page_bytes)
        assert page_row["source_locator_id"] == locator["locator_id"]
        assert page_row["interview_wave"] == builder.INTERVIEW_WAVE
        assert page_row["annotation_status"] == "complete"
        assert page_row[
            "questionnaire_page_id"
        ] == "psid-questionnaire-page:" + builder._digest(
            [
                builder.DOCUMENT_ID,
                builder.INTERVIEW_WAVE,
                page_row["page_number"],
                page_row["page_text_utf8_sha256"],
            ]
        )

    by_page: dict[int, list[dict]] = {
        page_row["page_number"]: [] for page_row in pages
    }
    for row in occurrences:
        by_page[row["page_number"]].append(row)

    for page_row in pages:
        page_number = page_row["page_number"]
        page_bytes = page_texts[page_number - 1].encode("utf-8")
        rows = by_page[page_number]
        keys = [
            (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                KIND_ORDER[row["occurrence_kind"]],
                row["semantic_ordinal_at_span"],
            )
            for row in rows
        ]
        assert keys == sorted(keys), page_number
        assert [row["occurrence_index_on_page"] for row in rows] == list(
            range(len(rows))
        )
        assert page_row["questionnaire_occurrence_ids"] == [
            row["questionnaire_occurrence_id"] for row in rows
        ]
        for row in rows:
            start = row["utf8_byte_start"]
            end = row["utf8_byte_end"]
            assert 0 <= start < end <= len(page_bytes)
            sliced = page_bytes[start:end]
            assert sliced.decode("utf-8") == row["matched_text"]
            assert _sha256(sliced) == row["matched_utf8_sha256"]
            assert row["source_document_id"] == builder.DOCUMENT_ID
            assert row["source_locator_id"] == locator["locator_id"]
            assert row["interview_wave"] == builder.INTERVIEW_WAVE
            assert row["occurrence_kind"] in builder.OCCURRENCE_KINDS
            assert row["source_locator_sha256"] == builder._digest(
                [
                    builder.DOCUMENT_ID,
                    builder.CANONICAL_SOURCE_PATH,
                    "questionnaire_page_utf8_span",
                    [
                        builder.INTERVIEW_WAVE,
                        page_number,
                        start,
                        end,
                        row["occurrence_index_on_page"],
                        row["semantic_ordinal_at_span"],
                        row["occurrence_kind"],
                    ],
                ]
            )
            values = [row[field] for field in builder.OCCURRENCE_KEYS[1:]]
            assert row[
                "questionnaire_occurrence_id"
            ] == "psid-questionnaire-occurrence:" + builder._digest(values)
            if row["occurrence_kind"] != "flow_branch_label":
                assert row["semantic_ordinal_at_span"] == 0

    coordinates = {
        (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind"],
            row["semantic_ordinal_at_span"],
        )
        for row in occurrences
    }
    assert len(coordinates) == len(occurrences)
    assert len(
        {row["questionnaire_occurrence_id"] for row in occurrences}
    ) == len(occurrences)
    assert len({row["source_locator_sha256"] for row in occurrences}) == len(
        occurrences
    )

    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    branches = committed["flow_branch_rows"]
    label_ids = [
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "flow_branch_label"
    ]
    assert [row["source_occurrence_id"] for row in branches] == label_ids
    assert len({row["flow_branch_id"] for row in branches}) == len(branches)
    branch_by_id = {row["flow_branch_id"]: row for row in branches}
    for position, branch in enumerate(branches):
        source = occurrence_by_id[branch["source_occurrence_id"]]
        assert branch["interview_wave"] == builder.INTERVIEW_WAVE
        assert branch["source_locator_id"] == locator["locator_id"]
        assert branch["page_number"] == source["page_number"]
        assert (
            branch["occurrence_index_on_page"]
            == source["occurrence_index_on_page"]
        )
        assert branch["branch_label"] == source["matched_text"]
        assert branch["branch_label_sha256"] == source["matched_utf8_sha256"]
        assert branch["branch_path"][-1] == branch["flow_branch_id"]
        assert branch["branch_path"][:-1] == source["flow_branch_paths"][0]
        assert len(source["flow_branch_paths"]) == 1
        assert branch["flow_branch_id"] == "questionnaire-flow:" + (
            builder._digest(
                [
                    branch["parent_flow_branch_id"],
                    builder.INTERVIEW_WAVE,
                    branch["source_occurrence_id"],
                ]
            )
        )
        assert branch["flow_branch_id"] not in branch["branch_path"][:-1]
        parent = branch["parent_flow_branch_id"]
        if parent == builder.FLOW_ROOT:
            assert branch["branch_path"] == [
                builder.FLOW_ROOT,
                branch["flow_branch_id"],
            ]
        else:
            assert parent in branch_by_id
            earlier = [row["flow_branch_id"] for row in branches[:position]]
            assert parent in earlier

    resolved_paths = {tuple(row["branch_path"]) for row in branches} | {
        (builder.FLOW_ROOT,)
    }
    for row in occurrences:
        paths = row["flow_branch_paths"]
        assert paths
        assert len({tuple(path) for path in paths}) == len(paths)
        encoded = [
            tuple(part.encode("utf-8") for part in path) for path in paths
        ]
        assert encoded == sorted(encoded)
        for path in paths:
            assert path
            assert path[0] == builder.FLOW_ROOT
            if row["occurrence_kind"] == "flow_branch_label":
                continue
            assert tuple(path) in resolved_paths

    anchors = committed["local_anchor_classification_rows"]
    purposes = committed["local_field_purpose_classification_rows"]
    repeats = committed["local_repeat_or_alias_evidence_rows"]
    anchor_kinds = set(builder.NODE_DOMAINS)
    anchor_sources = [row["source_occurrence_id"] for row in anchors]
    assert len(anchor_sources) == len(set(anchor_sources))
    assert {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] in anchor_kinds
    } == set(anchor_sources)
    for row in anchors:
        source = occurrence_by_id[row["source_occurrence_id"]]
        assert row["exact_label"] == source["matched_text"]
        assert row["exact_label_utf8_span"] == [
            source["page_number"],
            source["utf8_byte_start"],
            source["utf8_byte_end"],
        ]
        domain, _ = builder.NODE_DOMAINS[source["occurrence_kind"]]
        assert row["node_domain"] == domain
        assert row["annotation_status"] == "complete"
        for parent_id in row["parent_anchor_occurrence_ids"]:
            assert (
                occurrence_by_id[parent_id]["occurrence_kind"] in anchor_kinds
            )
        if row["printed_identifier"] is not None:
            page_number, start, end = row["printed_identifier_utf8_span"]
            page_bytes = page_texts[page_number - 1].encode("utf-8")
            assert (
                page_bytes[start:end].decode("utf-8")
                == row["printed_identifier"]
            )

    prompt_sources = [row["source_prompt_occurrence_id"] for row in purposes]
    assert len(prompt_sources) == len(set(prompt_sources))
    assert {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "field_purpose_prompt"
    } == set(prompt_sources)
    for row in purposes:
        source = occurrence_by_id[row["source_prompt_occurrence_id"]]
        assert row["exact_prompt"] == source["matched_text"]
        assert row["field_purposes"]
        assert all(
            purpose in builder.FIELD_PURPOSES
            for purpose in row["field_purposes"]
        )
        assert row["field_purposes"] == sorted(
            row["field_purposes"], key=builder.PURPOSE_ORDER.__getitem__
        )
        assert row["applicable_anchor_occurrence_ids"]

    instruction_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    consumed = {
        occurrence_id
        for row in repeats
        for occurrence_id in row["source_instruction_occurrence_ids"]
    }
    assert consumed == instruction_ids
    allowed_relations = {
        "explicit_repeat_instruction",
        "explicit_cross_reference",
        "same_printed_identifier_and_exact_label",
    }
    for row in repeats:
        assert row["alias_relation"] in allowed_relations
        assert row["evidence_occurrence_ids"]
        assert set(row["source_instruction_occurrence_ids"]) <= set(
            row["evidence_occurrence_ids"]
        )
        if row["unresolved_target_reference"] is None:
            assert row["alias_anchor_occurrence_id"] in occurrence_by_id
            assert row["referenced_anchor_occurrence_id"] in occurrence_by_id
            assert (
                row["alias_anchor_occurrence_id"]
                != row["referenced_anchor_occurrence_id"]
            )
        else:
            assert row["alias_anchor_occurrence_id"] is None
            assert row["referenced_anchor_occurrence_id"] is None
            target = row["unresolved_target_reference"]
            page_bytes = page_texts[target["page_number"] - 1].encode("utf-8")
            sliced = page_bytes[
                target["utf8_byte_start"] : target["utf8_byte_end"]
            ]
            assert sliced.decode("utf-8") == target["matched_text"]
            assert _sha256(sliced) == target["matched_utf8_sha256"]

    candidate = json.loads(builder.CANDIDATE_PATH.read_text(encoding="utf-8"))
    dispositions = committed["candidate_disposition_rows"]
    assert [
        (row["candidate_row_kind"], row["candidate_id"])
        for row in dispositions
    ] == builder._candidate_domain(candidate)
    assert len(dispositions) == builder.CANDIDATE_DENOMINATOR
    output_ids = {
        row["stage2_row_id"] for row in committed["output_adjudication_rows"]
    }
    for row in dispositions:
        assert row["adjudication_status"] == "complete"
        assert row["disposition"] in {
            "accepted",
            "modified",
            "split",
            "rejected",
        }
        count = len(row["stage2_row_ids"])
        if row["disposition"] == "rejected":
            assert count == 0
        elif row["disposition"] == "split":
            assert count >= 2
        else:
            assert count == 1
        assert set(row["stage2_row_ids"]) <= output_ids
    for row in committed["output_adjudication_rows"]:
        assert row["whole_page_review_complete"] is True
        assert row["source_span_verified"] is True
        assert row["adjudication_status"] == "complete"
        if row["adjudication_action"] == "manual_add":
            assert row["source_candidate_ids"] == []
        else:
            assert row["source_candidate_ids"]

    assert committed["status"] == builder.STATUS
    assert (
        committed["authority_disposition"]["authority_kind"]
        == "sealed_document_annotation_nonauthority"
    )
    assert (
        committed["authority_disposition"]["global_resolution_performed"]
        is False
    )


def test_document_007_mutations_fail_closed():
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

    # fam1971_QxQs H7 resolves under two complete printed paths (the
    # unincorporated and both-kinds boxes of H6), so the path-subset law is
    # exercised both by dropping one member of that path array and by
    # truncating a single-path conditional back to the bare root.
    dropped_path_member = copy.deepcopy(valid)
    multi_path = next(
        row
        for row in dropped_path_member["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] != "flow_branch_label"
        and len(row["flow_branch_paths"]) > 1
    )
    multi_path["flow_branch_paths"] = multi_path["flow_branch_paths"][:1]
    mutations.append(dropped_path_member)

    selected_path_subset = copy.deepcopy(valid)
    conditional = next(
        row
        for row in selected_path_subset["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] != "flow_branch_label"
        and len(row["flow_branch_paths"][0]) > 1
    )
    conditional["flow_branch_paths"] = [[builder.FLOW_ROOT]]
    mutations.append(selected_path_subset)

    duplicate_path = copy.deepcopy(valid)
    path_row = next(
        row
        for row in duplicate_path["questionnaire_occurrence_rows"]
        if row["occurrence_kind"] != "flow_branch_label"
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

    dropped_repeat_evidence = copy.deepcopy(valid)
    dropped_repeat_evidence["local_repeat_or_alias_evidence_rows"].pop()
    mutations.append(dropped_repeat_evidence)

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

    # fam1971_QxQs nests the D24 extra-job branch under the D-sequence
    # branch, so re-rooting it must be rejected as a broken ancestry.
    flattened_ancestry = copy.deepcopy(valid)
    nested = next(
        row
        for row in flattened_ancestry["flow_branch_rows"]
        if len(row["branch_path"]) > 2
    )
    nested["parent_flow_branch_id"] = builder.FLOW_ROOT
    nested["branch_path"] = [builder.FLOW_ROOT, nested["flow_branch_id"]]
    mutations.append(flattened_ancestry)

    forward_branch_label = copy.deepcopy(valid)
    forward_branch_label["flow_branch_rows"][1]["branch_label"] = (
        forward_branch_label["flow_branch_rows"][1]["branch_label"].upper()
    )
    mutations.append(forward_branch_label)

    unmapped_purpose = copy.deepcopy(valid)
    unmapped_purpose["local_field_purpose_classification_rows"][0][
        "applicable_anchor_occurrence_ids"
    ] = []
    mutations.append(unmapped_purpose)

    for mutation in mutations:
        with pytest.raises(ValueError):
            builder.validate_annotation(_reseal(mutation), capture_root)


def test_document_007_sealed_shape():
    """Pin the document-7 row census the final report and lane brief cite."""

    committed = json.loads(builder.OUTPUT_PATH.read_text(encoding="utf-8"))
    assert committed["document_source_position"] == 7
    assert committed["document_source_row"]["canonical_source_path"] == (
        builder.CANONICAL_SOURCE_PATH
    )
    assert committed["document_source_row"]["interview_waves"] == [1971]
    assert len(committed["questionnaire_page_rows"]) == 92
    assert len(committed["questionnaire_occurrence_rows"]) == 200
    assert len(committed["flow_branch_rows"]) == 10
    assert len(committed["local_anchor_classification_rows"]) == 75
    assert len(committed["local_field_purpose_classification_rows"]) == 99
    assert len(committed["local_repeat_or_alias_evidence_rows"]) == 18
    assert len(committed["candidate_disposition_rows"]) == 3030

    kinds = {
        row["occurrence_kind"]
        for row in committed["questionnaire_occurrence_rows"]
    }
    assert kinds == set(builder.OCCURRENCE_KINDS)

    empty_pages = [
        row["page_number"]
        for row in committed["questionnaire_page_rows"]
        if not row["questionnaire_occurrence_ids"]
    ]
    assert len(empty_pages) == 64

    unresolved = [
        row
        for row in committed["local_repeat_or_alias_evidence_rows"]
        if row["unresolved_target_reference"] is not None
    ]
    assert [
        row["unresolved_target_reference"]["matched_text"]
        for row in unresolved
    ] == ["D2-D3", "D3d", "Hl7"]

    serialized = json.dumps(committed, ensure_ascii=True)
    for token in (
        "psid-job-slot:",
        "psid-component-slot:",
        "psid-node-alias:",
        "psid-questionnaire-relationship:",
    ):
        assert token not in serialized
