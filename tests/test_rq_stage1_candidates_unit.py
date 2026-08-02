"""Synthetic unit tests for nonauthority R_Q candidate generation."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as builder  # noqa: E402

DOCUMENT_ID = "psid-source-document:" + "a" * 64
WAVE = 2023


def _detect_pages(page_texts: list[str]) -> list[dict]:
    rows: list[dict] = []
    line_base = 0
    for page_number, page_text in enumerate(page_texts, start=1):
        page_rows, line_count = builder.detect_page_candidates(
            page_text,
            source_document_id=DOCUMENT_ID,
            interview_wave=WAVE,
            page_number=page_number,
            document_nonblank_line_base=line_base,
        )
        rows.extend(page_rows)
        line_base += line_count
    return rows


def test_detector_spec_exact_covers_ten_ordered_candidate_kinds():
    assert builder.OCCURRENCE_KINDS == (
        "flow_branch_label",
        "role_anchor",
        "job_anchor",
        "remuneration_component_anchor",
        "role_total_anchor",
        "farm_aggregate_anchor",
        "business_aggregate_anchor",
        "context_anchor",
        "field_purpose_prompt",
        "repeat_or_alias_instruction",
    )
    assert set(
        row["occurrence_kind_candidate"] for row in builder.DETECTOR_RULE_ROWS
    ) == set(builder.OCCURRENCE_KINDS)
    assert builder.GENERATOR_SPEC_IDENTITY["detector_rule_count"] == len(
        builder.DETECTOR_RULE_ROWS
    )


def test_broad_detector_fixture_emits_every_candidate_kind():
    text = "\n".join(
        (
            "IF A1=1, GO TO A2",
            "REFERENCE PERSON and SPOUSE-PARTNER",
            "B4. At your main job, how much wages and overtime did you earn?",
            "What were total earnings from all jobs combined?",
            "H2. What were total receipts from farming?",
            "Did that business or professional practice earn profits?",
            "How many hours per week did you work?",
            "A1. What was the amount?",
            "GO BACK TO B4 AND REPEAT FOR THE SAME JOB",
        )
    )
    rows, _ = builder.detect_page_candidates(
        text,
        source_document_id=DOCUMENT_ID,
        interview_wave=WAVE,
        page_number=1,
    )
    assert set(row["occurrence_kind_candidate"] for row in rows) == set(
        builder.OCCURRENCE_KINDS
    )


def test_unicode_spans_are_exact_half_open_utf8_bytes():
    text = "é → REFERENCE PERSON earned wages?\n"
    rows, _ = builder.detect_page_candidates(
        text,
        source_document_id=DOCUMENT_ID,
        interview_wave=WAVE,
        page_number=1,
    )
    page_bytes = text.encode("utf-8")
    for row in rows:
        matched = page_bytes[row["utf8_byte_start"] : row["utf8_byte_end"]]
        assert matched.decode("utf-8") == row["matched_text"]
        assert (
            hashlib.sha256(matched).hexdigest() == (row["matched_utf8_sha256"])
        )
    role = next(
        row
        for row in rows
        if row["occurrence_kind_candidate"] == "role_anchor"
    )
    assert role["utf8_byte_start"] == len("é → ".encode())


def test_candidate_order_ids_and_dedup_are_deterministic():
    text = "A1. What wages did the REFERENCE PERSON earn at the main job?\n"
    first, _ = builder.detect_page_candidates(
        text,
        source_document_id=DOCUMENT_ID,
        interview_wave=WAVE,
        page_number=1,
    )
    second, _ = builder.detect_page_candidates(
        text,
        source_document_id=DOCUMENT_ID,
        interview_wave=WAVE,
        page_number=1,
    )
    assert first == second
    assert [row["candidate_index_on_page"] for row in first] == list(
        range(len(first))
    )
    assert len(
        {
            (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["occurrence_kind_candidate"],
            )
            for row in first
        }
    ) == len(first)
    assert all(
        row["candidate_occurrence_id"].startswith("rq-candidate-occurrence:")
        for row in first
    )


def test_empty_page_is_retained_without_invented_occurrences():
    rows, line_count = builder.detect_page_candidates(
        "   \n\t\n",
        source_document_id=DOCUMENT_ID,
        interview_wave=WAVE,
        page_number=1,
    )
    assert rows == []
    assert line_count == 0


def test_flow_path_candidates_are_acyclic_options_not_annotations():
    text = "IF A1=1, GO TO A2\n    IF A2=1, SKIP TO A3\nALL OTHERS GO TO A4\n"
    occurrences = _detect_pages([text])
    flow_rows = builder._flow_candidate_rows(occurrences)
    flow_occurrences = [
        row
        for row in occurrences
        if row["occurrence_kind_candidate"] == "flow_branch_label"
    ]
    assert {row["source_candidate_occurrence_id"] for row in flow_rows} == {
        row["candidate_occurrence_id"] for row in flow_occurrences
    }
    assert all(
        row["candidate_parent_path"][0] == builder.FLOW_ROOT_ID
        and row["candidate_branch_path"]
        == [*row["candidate_parent_path"], row["candidate_branch_id"]]
        and row["candidate_branch_id"] not in row["candidate_parent_path"]
        and row["adjudication_status"] == builder.ADJUDICATION_STATUS
        for row in flow_rows
    )
    assert not any("questionnaire-flow:" in str(row) for row in flow_rows)


def test_anchor_classifications_offer_parents_without_global_ids():
    text = (
        "B4. At the main job, how much wages did the REFERENCE PERSON earn?\n"
        "B5. What overtime pay came from that job?\n"
    )
    occurrences = _detect_pages([text])
    builder._flow_candidate_rows(occurrences)
    rows = builder._anchor_classification_rows(occurrences, [text])
    remuneration = [
        row
        for row in rows
        if row["classification_candidate"] == "source_remuneration_component"
    ]
    assert remuneration
    assert any(row["parent_anchor_candidate_ids"] for row in remuneration)
    assert all(
        row["canonical_node_id"] is None
        and row["adjudication_status"] == builder.ADJUDICATION_STATUS
        for row in rows
    )


def test_per_document_manifest_recomputes_counts_digest_and_nonpromotion():
    page_text = "A1. What wages did the HEAD earn at the main job?\n"
    occurrences = _detect_pages([page_text])
    flow_rows = builder._flow_candidate_rows(occurrences)
    anchor_rows = builder._anchor_classification_rows(occurrences, [page_text])
    page_bytes = page_text.encode()
    document = {
        "source_document_id": DOCUMENT_ID,
        "interview_waves": [WAVE],
        "canonical_source_path": "documentation/capture1/fixture.pdf",
    }
    replay_pages = [
        {
            "questionnaire_page_id": "psid-questionnaire-page:" + "b" * 64,
            "page_number": 1,
            "page_text_utf8_sha256": hashlib.sha256(page_bytes).hexdigest(),
        },
        {
            "questionnaire_page_id": "psid-questionnaire-page:" + "c" * 64,
            "page_number": 2,
            "page_text_utf8_sha256": hashlib.sha256(b"").hexdigest(),
        },
    ]
    page_rows = builder._candidate_page_rows(
        document, replay_pages, occurrences
    )
    manifest = builder._candidate_manifest(
        document, page_rows, occurrences, flow_rows, anchor_rows
    )
    assert manifest["source_document_id"] == DOCUMENT_ID
    assert manifest["page_count"] == 2
    assert manifest["empty_candidate_page_count"] == 1
    assert manifest["candidate_occurrence_count"] == len(occurrences)
    assert set(manifest["candidate_occurrence_counts_by_kind"]) == set(
        builder.OCCURRENCE_KINDS
    )
    assert len(manifest["candidate_payload_sha256"]) == 64
    assert manifest["authority_kind"] == "candidate_only_nonauthority"
    assert manifest["auto_promotion_permitted"] is False
    assert manifest["adjudication_required_for_every_stage2_row"] is True
