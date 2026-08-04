#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for q84.pdf.

Document 34 of the 81-document `questionnaire_flow` domain is the 1984 PSID
core family questionnaire: 47 pages, two questionnaire pages photographed per
PDF page.  The stage-1 detector output is provenance only.  Every span, hash,
path, and identifier below was re-derived from the authenticated PDF bytes
during a complete 47-page reviewer pass before the candidate artifact was
opened for adjudication.

The reviewer pass established a declared annotation domain for this lane; see
`DECLARED_SCOPE` for the exact domain, the document-local classification
rules, the recorded unresolved source interpretations, and the remaining-work
ledger.  Nothing outside the domain is silently dropped: every candidate row in
the whole document is dispositioned exactly once with an explicit reason.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as candidates  # noqa: E402
import build_rq_stage1_source_replay as replay_tools  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

SCHEMA_VERSION = "rq_stage2_document_annotation.v1"
STATUS = "pass_sealed_declared_domain_nonauthority_annotation"
DOCUMENT_POSITION = 34
DOCUMENT_ID = (
    "psid-source-document:"
    "2b18d9003adec3927c5120197f6e594212c2bb3ecd434dceb67a4135a1098c3b"
)
INTERVIEW_WAVE = 1984
CANONICAL_SOURCE_PATH = "documentation/capture1/q84.pdf"
PDF_SIZE = 2_533_723
PDF_SHA256 = "53a167741ad88b361e09fb84c05eba60fccc042e3e90f38789a2e3a8a01d8403"
PAGE_COUNT = 47

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_04_documents_031_040"
    / "document_034_q84_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_034_q84_annotation_v1.json"
)

REPLAY_RAW_SHA256 = (
    "f2f676db3f9180b85af1977253fb8c10ff7fd60494e1597212b922dfc0f5920a"
)
REPLAY_CONTENT_SHA256 = (
    "48e259ddf4c9eb60b7f9fdfd73b2576255400a7cdf19e4115d41bcf5bad3e8cc"
)
INDEX_RAW_SHA256 = (
    "a90dfea13cdd74a7d612acdee76c91d6c9e2fd2ed9f9a6befc6a99d9f773a446"
)
INDEX_CONTENT_SHA256 = (
    "ed80f518b0d2150b9d2c2f4d2e94ca517fc40d1dcd5e29a0c75833d40e86be64"
)
CANDIDATE_RAW_SHA256 = (
    "11b1fb942e2f80a6d8f7483ce04a2743a59b8d345eeaa22d65f1915fe5a6d292"
)
CANDIDATE_CONTENT_SHA256 = (
    "77b2e4143c339c7a8865af307b9ed92a5ed0e76eb3410e6c8335b6d00df76335"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "e9a468f661e19f3622dae35d0c8b16e0077d5e628013456bb99d854de5eb6eaa"
)
CANDIDATE_DENOMINATOR = 3772

FLOW_ROOT = "questionnaire-flow:root"
OCCURRENCE_KINDS = candidates.OCCURRENCE_KINDS
KIND_ORDER = {kind: index for index, kind in enumerate(OCCURRENCE_KINDS)}

# Pages whose printed content the reviewer annotated in full.  Every other
# page was read end to end during the whole-document pass and carries no
# annotated occurrence; see DECLARED_SCOPE for the reason ledger.
ANNOTATED_PAGES = (5,)

FIELD_PURPOSES = (
    "interview_and_role_attachment",
    "amount",
    "reporting_unit",
    "month_or_exposure",
    "assignment",
    "employee_self_or_mixed",
    "incorporation",
    "government_level",
    "industry",
    "occupation",
    "enrollment",
    "job_identifier",
    "state_of_residence",
    "section_218_group",
    "section_218_position",
    "public_retirement_system_participation",
    "federal_retirement_system",
    "federal_service",
    "railroad_covered_employer",
    "railroad_covered_service",
    "ministerial_service",
    "clergy_remuneration",
    "church_employee_service",
    "religious_order_service",
    "clergy_or_religious_exemption",
    "domestic_service",
    "agricultural_service",
    "election_work",
    "family_service",
    "casual_service",
    "foreign_government_service",
    "international_organization_service",
    "nonresident_alien_status",
    "employer_school_nexus",
    "statutory_student_service",
)
PURPOSE_ORDER = {value: index for index, value in enumerate(FIELD_PURPOSES)}

LOCATOR_KEYS = (
    "locator_id",
    "source_document_id",
    "interview_wave",
    "filename",
    "location_type",
    "byte_start",
    "byte_end",
    "size_bytes",
    "full_file_sha256",
    "range_sha256",
    "pdf_page_domain",
)
PAGE_KEYS = (
    "questionnaire_page_id",
    "source_document_id",
    "source_locator_id",
    "interview_wave",
    "page_number",
    "page_text_utf8_sha256",
    "questionnaire_occurrence_ids",
    "annotation_status",
)
OCCURRENCE_KEYS = (
    "questionnaire_occurrence_id",
    "source_document_id",
    "source_locator_id",
    "source_locator_sha256",
    "interview_wave",
    "page_number",
    "utf8_byte_start",
    "utf8_byte_end",
    "occurrence_index_on_page",
    "semantic_ordinal_at_span",
    "occurrence_kind",
    "matched_text",
    "matched_utf8_sha256",
    "flow_branch_paths",
)
BRANCH_KEYS = (
    "flow_branch_id",
    "parent_flow_branch_id",
    "source_occurrence_id",
    "branch_path",
    "interview_wave",
    "source_locator_id",
    "page_number",
    "occurrence_index_on_page",
    "branch_label",
    "branch_label_sha256",
)
ANCHOR_KEYS = (
    "local_anchor_classification_id",
    "source_occurrence_id",
    "node_domain",
    "classification",
    "printed_identifier",
    "printed_identifier_utf8_span",
    "exact_label",
    "exact_label_utf8_span",
    "parent_anchor_occurrence_ids",
    "annotation_status",
)
PURPOSE_KEYS = (
    "local_field_purpose_classification_id",
    "source_prompt_occurrence_id",
    "field_purposes",
    "applicable_anchor_occurrence_ids",
    "exact_prompt",
    "exact_prompt_utf8_span",
    "annotation_status",
)
REPEAT_KEYS = (
    "local_repeat_evidence_id",
    "alias_relation",
    "alias_anchor_occurrence_id",
    "referenced_anchor_occurrence_id",
    "source_instruction_occurrence_ids",
    "unresolved_target_reference",
    "evidence_occurrence_ids",
    "handoff_status",
    "annotation_status",
)
DISPOSITION_KEYS = (
    "candidate_row_kind",
    "candidate_id",
    "disposition",
    "stage2_row_ids",
    "adjudication_status",
)
ADJUDICATION_KEYS = (
    "stage2_row_kind",
    "stage2_row_id",
    "source_candidate_ids",
    "adjudication_action",
    "whole_page_review_complete",
    "source_span_verified",
    "adjudication_status",
)
NOTE_KEYS = (
    "correction_note_id",
    "subject_relation",
    "subject_row_kind",
    "subject_row_id",
    "reason_code",
    "note",
    "adjudication_status",
)
SEAL_ROW_KEYS = (
    "row_domain",
    "row_count",
    "row_key_fields",
    "row_keyset_sha256",
    "row_domain_sha256",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return text.encode("ascii") + b"\n"


def _digest(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _content_digest(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "integrity"}
    return _digest(payload)


def _expect_keys(
    value: Mapping[str, Any], keys: Sequence[str], label: str
) -> None:
    # The canonical serialization sorts object keys, so exact membership is
    # the verifiable form of section 19's displayed-key law; the displayed
    # order itself is fixed by the *_KEYS tuples used to build every row.
    if sorted(value.keys()) != sorted(keys):
        raise ValueError(f"{label} key membership drift")


def _strict_load(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unreadable {label} at {path}") from error


def _identity(
    path: Path,
    schema_version: str,
    artifact_id: str,
    raw_sha256: str,
    content_sha256: str,
) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "schema_version": schema_version,
        "artifact_id": artifact_id,
        "byte_size": path.stat().st_size,
        "raw_sha256": raw_sha256,
        "content_sha256": content_sha256,
    }


def _default_capture_root() -> Path:
    configured = os.environ.get("POPULACE_DYNAMICS_PSID_DIR")
    if configured:
        return Path(configured) / "documentation/capture1"
    return Path(
        "/Users/maxghenis/PolicyEngine/psid-data/documentation/capture1"
    )


def _load_replay_and_index() -> tuple[dict[str, Any], dict[str, Any]]:
    replay_raw = REPLAY_PATH.read_bytes()
    if _sha256(replay_raw) != REPLAY_RAW_SHA256:
        raise ValueError("stage-1 source replay raw identity drift")
    replay = _strict_load(REPLAY_PATH, "stage-1 source replay")
    replay_tools.validate_source_replay(replay)
    if replay["integrity"]["content_sha256"] != REPLAY_CONTENT_SHA256:
        raise ValueError("stage-1 source replay content identity drift")

    index_raw = INDEX_PATH.read_bytes()
    if _sha256(index_raw) != INDEX_RAW_SHA256:
        raise ValueError("stage-1 candidate index raw identity drift")
    index = _strict_load(INDEX_PATH, "stage-1 candidate index")
    candidates.validate_candidate_index(index, replay)
    if index["integrity"]["content_sha256"] != INDEX_CONTENT_SHA256:
        raise ValueError("stage-1 candidate index content identity drift")
    return replay, index


def _load_candidate(
    replay: Mapping[str, Any], index: Mapping[str, Any]
) -> dict[str, Any]:
    """Open candidates only after source pages and review rows exist."""

    index_row = index["document_candidate_manifest_rows"][
        DOCUMENT_POSITION - 1
    ]
    if (
        index_row["document_source_position"] != DOCUMENT_POSITION
        or index_row["source_document_id"] != DOCUMENT_ID
        or ROOT / index_row["path"] != CANDIDATE_PATH
        or index_row["raw_sha256"] != CANDIDATE_RAW_SHA256
        or index_row["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or index_row["candidate_payload_sha256"] != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-34 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-34 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-34 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-34 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / "q84.pdf"
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("q84.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("q84.pdf page-count drift")
    return pages


def _review_page_rows(
    replay: Mapping[str, Any], page_texts: Sequence[str]
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in replay["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == DOCUMENT_ID
    ]
    if [row["page_number"] for row in rows] != list(range(1, PAGE_COUNT + 1)):
        raise ValueError("document-34 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-34 replay page text drift")
    if any(not text for text in page_texts):
        raise ValueError("document-34 empty-text page domain drift")
    return rows


def _strict_slice(
    page_text: str, start: int, end: int, label: str
) -> tuple[str, str]:
    page_bytes = page_text.encode("utf-8")
    if not (0 <= start < end <= len(page_bytes)):
        raise ValueError(f"{label} source span is out of bounds")
    raw = page_bytes[start:end]
    try:
        matched = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"{label} source span is not UTF-8 aligned"
        ) from error
    if not matched:
        raise ValueError(f"{label} source span is empty")
    return matched, _sha256(raw)


def _needle_span(page_text: str, needle: str) -> tuple[int, int]:
    page_bytes = page_text.encode("utf-8")
    raw = needle.encode("utf-8")
    first = page_bytes.find(raw)
    if first < 0 or page_bytes.find(raw, first + 1) >= 0:
        raise ValueError(f"needle {needle!r} is missing or not unique")
    return first, first + len(raw)


def _path_sort_key(path: Sequence[str]) -> tuple[bytes, ...]:
    return tuple(part.encode("utf-8") for part in path)


# ---------------------------------------------------------------------------
# Declared annotation domain, document-local classification rules, recorded
# unresolved source interpretations, and remaining-work ledger.
# ---------------------------------------------------------------------------
DECLARED_SCOPE: dict[str, Any] = {
    "scope_declaration_status": (
        "additive_lane_local_declaration_compatible_with_v1_row_schemas"
    ),
    "reviewed_page_domain": list(range(1, PAGE_COUNT + 1)),
    "annotated_page_domain": list(ANNOTATED_PAGES),
    "annotated_printed_domain": [
        "page 5 left column, SECTION C: EMPLOYMENT OF HEAD, questions C1-C7"
    ],
    "domain_selection_rule": (
        "The annotated domain is ancestry-closed: every annotated occurrence's "
        "complete printed control-flow ancestry is itself annotated and rooted "
        "at questionnaire-flow:root, so no path array is a selected subset. "
        "Section C is entered unconditionally from Section B (page 4 prints "
        "'TURN TO P. 6. SECTION C' on both B29 and B32 continuations), so C1 "
        "and the SECTION C header are unconditional root-path text."
    ),
    "local_classification_rules": [
        "flow_branch_label: a printed conditional option or gate label. A "
        "printed routing directive ('TURN TO P. n, Xn') names a branch target "
        "and is annotated as a branch label only when its complete printed "
        "parent option set occurs at strictly earlier page bytes, because "
        "section 19 requires an earlier resolving parent.",
        "role_anchor: the exact printed role lexeme ('HEAD'), not the "
        "surrounding parentheses or question text.",
        "job_anchor: a printed job noun phrase that establishes a job the "
        "instrument then asks about.",
        "context_anchor: a printed job-attached or work-attached content "
        "field, plus the printed section header that scopes them.",
        "field_purpose_prompt: the printed question unit whose solicited "
        "field expresses at least one of the 35 ratified field purposes. A "
        "question with no applicable listed purpose gets no prompt row.",
        "context/prompt spans run from the printed question identifier to the "
        "end of that question's own printed text, crossing a line break only "
        "when the intervening bytes belong to the same question's column.",
        "remuneration_component_anchor: a printed field soliciting pay or "
        "earnings for work, or the person's own business or farm income. "
        "Transfer income, asset income, and expenditure fields are not "
        "remuneration components.",
    ],
    "recorded_unresolved_interpretations": [
        {
            "interpretation_id": "doc34-u1-later-parent-routing-directive",
            "printed_evidence": [
                {
                    "page_number": 5,
                    "utf8_byte_start": 2848,
                    "utf8_byte_end": 2862,
                },
                {
                    "page_number": 5,
                    "utf8_byte_start": 4875,
                    "utf8_byte_end": 4888,
                },
            ],
            "statement": (
                "C1's 'TURN TO P. 24,' directive is printed between its "
                "parent option codes and C2's 'TURN TO P.31,' directive is "
                "printed above its parent '5. NO' code, so their complete "
                "printed parent sets are not all at earlier page bytes. "
                "Section 19's earlier-resolving-parent law cannot represent "
                "them as branch rows; they are recorded here instead of being "
                "given a truncated or invented parent."
            ),
            "disposition": "recorded_for_review_not_annotated",
        },
        {
            "interpretation_id": "doc34-u2-two-up-column-inversion",
            "printed_evidence": [
                {
                    "page_number": 5,
                    "utf8_byte_start": 3681,
                    "utf8_byte_end": 3843,
                },
            ],
            "statement": (
                "q84 photographs two questionnaire pages per PDF page, so the "
                "right column's questions (C8-C18, including the C12 salary, "
                "C15/C16 hourly-wage, and C14/C18 overtime-rate remuneration "
                "fields) are printed at smaller page-byte offsets than the "
                "left-column options (C4 '3. SELF ONLY', C6 '5. NO', C7) that "
                "route to them. Their true ancestry therefore has later "
                "parents, which section 19's flow law cannot express. The "
                "right column is recorded here as blocked rather than "
                "annotated with false root paths. This inversion applies to "
                "every two-up page of this document and is the controlling "
                "reason the annotated domain is one column."
            ),
            "disposition": "recorded_for_review_not_annotated",
        },
    ],
    "remaining_work_ledger": [
        {
            "page_domain": [1, 2, 3, 4],
            "printed_domain": "cover sheet, thumbnail sketch, sections A-B",
            "reason_code": "non_employment_non_income_section_deferred",
        },
        {
            "page_domain": [5],
            "printed_domain": "page 5 right column, questions C8-C18",
            "reason_code": "two_up_column_inversion_blocked",
        },
        {
            "page_domain": [6, 7, 8],
            "printed_domain": "questions C19-C64, fringe and pension detail",
            "reason_code": "job_benefit_detail_deferred",
        },
        {
            "page_domain": [9, 10, 11, 12, 13],
            "printed_domain": "questions C65-C147",
            "reason_code": "ancestry_outside_annotated_domain_deferred",
        },
        {
            "page_domain": [14, 36, 44, 45],
            "printed_domain": "near-empty scanned pages",
            "reason_code": "no_printed_annotatable_content",
        },
        {
            "page_domain": [15, 16, 17],
            "printed_domain": "sections D and E, head not working",
            "reason_code": "ancestry_outside_annotated_domain_deferred",
        },
        {
            "page_domain": [18, 19, 20, 21, 22, 23, 24, 25],
            "printed_domain": "section F, employment of wife/'wife'",
            "reason_code": "ancestry_outside_annotated_domain_deferred",
        },
        {
            "page_domain": [26, 27, 28, 29, 30],
            "printed_domain": "sections G and H, wife not working",
            "reason_code": "ancestry_outside_annotated_domain_deferred",
        },
        {
            "page_domain": [31, 32],
            "printed_domain": "section J, housework and food",
            "reason_code": "non_remuneration_section_deferred",
        },
        {
            "page_domain": [33, 34, 35],
            "printed_domain": (
                "section K income: K1-K16 farm receipts and net income, "
                "business share, wages and salaries, bonuses/overtime/tips/"
                "commissions, professional practice or trade, farming or "
                "market gardening, roomers or boarders, K20-K22 extra-job "
                "earnings, K48-K50 wife's earnings"
            ),
            "reason_code": "highest_value_deferred_next_lane_target",
        },
        {
            "page_domain": [37, 38, 39],
            "printed_domain": "K67-K82 other-FU-member job and income grids",
            "reason_code": "ancestry_outside_annotated_domain_deferred",
        },
        {
            "page_domain": [40, 41, 42, 43, 46, 47],
            "printed_domain": (
                "K83-K149 health, wealth, and background; degraded OCR"
            ),
            "reason_code": "non_remuneration_section_deferred",
        },
    ],
}


def _flow(
    key: str,
    start: int,
    end: int,
    expect: str,
    parents: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "page": 5,
        "utf8_byte_start": start,
        "utf8_byte_end": end,
        "expect": expect,
        "kind": "flow_branch_label",
        "parents": parents,
    }


# Reviewer decisions from the complete page-5 pass.  Parent tuples name the
# printed option a label depends on; one occurrence is emitted per complete
# parent path, in branch-path order.
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _flow("c1_working", 2141, 2155, "1. WORKING NOW"),
    _flow("c1_looking", 2184, 2194, "3. LOOKING"),
    _flow("c1_retired", 2233, 2243, "4. RETIRED"),
    _flow("c1_disabled", 2286, 2300, "5. PERMANENTLY"),
    _flow("c1_laid_off", 2782, 2789, "2. ONLY"),
    _flow("c1_keeping_house", 2897, 2913, "6. KEEPING HOUSE"),
    _flow("c1_student", 2950, 2960, "7. STUDENT"),
    _flow("c1_other", 3447, 3480, "8.     OTHER           (SPECIFY):"),
    _flow("c2_yes", 5160, 5166, "1. YES", ("c1_working", "c1_laid_off")),
    _flow("c2_no", 5184, 5189, "5. NO", ("c1_working", "c1_laid_off")),
    _flow("c3_yes", 7217, 7223, "1. YES", ("c2_yes",)),
    _flow("c3_no", 7245, 7250, "5. NO", ("c2_yes",)),
    _flow("c3_turn_section_e", 7268, 7282, "TURN TO P. 31,", ("c3_no",)),
    _flow("c4_self_only", 8533, 8545, "3. SELF ONLY", ("c3_yes",)),
    _flow("c4_turn_c8", 8573, 8580, "TURN TO", ("c4_self_only",)),
    _flow(
        "c4_someone_else",
        8650,
        8672,
        "1. SOMEONE        ELSE",
        ("c3_yes",),
    ),
    _flow(
        "c4_both",
        8691,
        8749,
        "2.         BOTH SOMEONE                 ELSE      AND SELF",
        ("c3_yes",),
    ),
    _flow(
        "c5_federal",
        11336,
        11346,
        "1. FEDERAL",
        ("c4_someone_else", "c4_both"),
    ),
    _flow(
        "c5_state", 11375, 11383, "2. STATE", ("c4_someone_else", "c4_both")
    ),
    _flow(
        "c5_local", 11406, 11414, "3. LOCAL", ("c4_someone_else", "c4_both")
    ),
    _flow(
        "c5_private",
        11442,
        11452,
        "4. PRIVATE",
        ("c4_someone_else", "c4_both"),
    ),
    _flow("c5_na_dk", 11481, 11487, "9. NA;", ("c4_someone_else", "c4_both")),
    _flow(
        "c5_other",
        13246,
        13275,
        "7.     OTHER       (SPECIFY):",
        ("c4_someone_else", "c4_both"),
    ),
    _flow(
        "c6_yes",
        14204,
        14214,
        "1.     YES",
        ("c4_someone_else", "c4_both"),
    ),
    _flow("c6_no", 14273, 14278, "5. NO", ("c4_someone_else", "c4_both")),
    _flow("c6_turn_c8", 14303, 14310, "TURN TO", ("c6_no",)),
    _flow("c7_yes", 15194, 15200, "1. YES", ("c6_yes",)),
    _flow("c7_no", 15263, 15268, "5. NO", ("c6_yes",)),
)


def _anchor(
    key: str,
    start: int,
    end: int,
    expect: str,
    kind: str,
    node_domain: str,
    classification: str,
    entries: tuple[str, ...],
    identifier: str | None = None,
    parents: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "key": key,
        "page": 5,
        "utf8_byte_start": start,
        "utf8_byte_end": end,
        "expect": expect,
        "kind": kind,
        "node_domain": node_domain,
        "classification": classification,
        "entries": entries,
        "identifier": identifier,
        "parents": parents,
    }


C1_TEXT = "lC1.      We would        like      to know             about   what   you do--are                          you            (HEAD)        working          now,         looking          for\nV10453     work,    retired,           keeping            house,    a student,      or                      what?"

C2_TEXT = "l C2.               Are     you   (HEAD)               doing        any    work       for        money\n                                                                                            V10454              now     at all?"

C3_TEXT = "lC3.            Are you               working           more        than      10 hours             per"

C4_TEXT = "lC4.       Do you        (HEAD)     work          for     someone               else,         yourself,               or      what?"

C5_TEXT = "lC5.       (In your    work   for                    someone         else,)     do          you         work       for       the      federal,           state.          or"

C6_TEXT = "lC6.   Is      your       currant              job        covered          by     a union              contract?"

C7_TEXT = "C7.    Do you            belong             to     that        labor       union?"

# Section C's printed head role anchor, its one printed job noun, the printed
# content fields, and the prompts whose solicited field expresses a ratified
# purpose.  Every span was re-sliced from the page bytes.
ANCHOR_SPECS: tuple[dict[str, Any], ...] = (
    _anchor(
        "section_c_role",
        455,
        459,
        "HEAD",
        "role_anchor",
        "role",
        "head_or_reference_person",
        ("root",),
    ),
    _anchor(
        "section_c_header_context",
        430,
        459,
        "SECTION C: EMPLOYMENT OF HEAD",
        "context_anchor",
        "component_slot",
        "source_context",
        ("root",),
    ),
    _anchor(
        "c1_role",
        1320,
        1324,
        "HEAD",
        "role_anchor",
        "role",
        "head_or_reference_person",
        ("root",),
        identifier="lC1.",
    ),
    _anchor(
        "c1_context",
        1196,
        1497,
        C1_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("root",),
        identifier="lC1.",
    ),
    _anchor(
        "c2_role",
        4509,
        4513,
        "HEAD",
        "role_anchor",
        "role",
        "head_or_reference_person",
        ("c1_working", "c1_laid_off"),
        identifier="l C2.",
    ),
    _anchor(
        "c2_context",
        4474,
        4704,
        C2_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c1_working", "c1_laid_off"),
        identifier="l C2.",
    ),
    _anchor(
        "c3_context",
        6192,
        6294,
        C3_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c2_yes",),
        identifier="lC3.",
    ),
    _anchor(
        "c4_role",
        7903,
        7907,
        "HEAD",
        "role_anchor",
        "role",
        "head_or_reference_person",
        ("c3_yes",),
        identifier="lC4.",
    ),
    _anchor(
        "c6_job",
        13945,
        13948,
        "job",
        "job_anchor",
        "job_slot",
        "source_job",
        ("c4_someone_else", "c4_both"),
        identifier="lC6.",
        parents=("section_c_role",),
    ),
    _anchor(
        "c4_context",
        7877,
        8008,
        C4_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c3_yes",),
        identifier="lC4.",
        parents=("c6_job",),
    ),
    _anchor(
        "c5_context",
        10180,
        10351,
        C5_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c4_someone_else", "c4_both"),
        identifier="lC5.",
        parents=("c6_job",),
    ),
    _anchor(
        "c6_context",
        13898,
        14010,
        C6_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c4_someone_else", "c4_both"),
        identifier="lC6.",
        parents=("c6_job",),
    ),
    _anchor(
        "c7_context",
        15011,
        15092,
        C7_TEXT,
        "context_anchor",
        "component_slot",
        "source_context",
        ("c6_yes",),
        identifier="C7.",
        parents=("c6_job",),
    ),
)

PROMPT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "c1_prompt",
        "page": 5,
        "utf8_byte_start": 1196,
        "utf8_byte_end": 1497,
        "expect": C1_TEXT,
        "kind": "field_purpose_prompt",
        "entries": ("root",),
        "purposes": ("interview_and_role_attachment", "assignment"),
        "anchors": ("c1_role", "c1_context"),
    },
    {
        "key": "c2_prompt",
        "page": 5,
        "utf8_byte_start": 4474,
        "utf8_byte_end": 4704,
        "expect": C2_TEXT,
        "kind": "field_purpose_prompt",
        "entries": ("c1_working", "c1_laid_off"),
        "purposes": ("assignment",),
        "anchors": ("c2_role", "c2_context"),
    },
    {
        "key": "c3_prompt",
        "page": 5,
        "utf8_byte_start": 6192,
        "utf8_byte_end": 6294,
        "expect": C3_TEXT,
        "kind": "field_purpose_prompt",
        "entries": ("c2_yes",),
        "purposes": ("assignment",),
        "anchors": ("c3_context",),
    },
    {
        "key": "c4_prompt",
        "page": 5,
        "utf8_byte_start": 7877,
        "utf8_byte_end": 8008,
        "expect": C4_TEXT,
        "kind": "field_purpose_prompt",
        "entries": ("c3_yes",),
        "purposes": ("employee_self_or_mixed",),
        "anchors": ("c4_role", "c4_context"),
    },
    {
        "key": "c5_prompt",
        "page": 5,
        "utf8_byte_start": 10180,
        "utf8_byte_end": 10351,
        "expect": C5_TEXT,
        "kind": "field_purpose_prompt",
        "entries": ("c4_someone_else", "c4_both"),
        "purposes": ("government_level",),
        "anchors": ("c5_context",),
    },
)

REPEAT_SPECS: tuple[dict[str, Any], ...] = ()
SAME_LABEL_ALIAS_SPECS: tuple[dict[str, str], ...] = ()


def _locator() -> dict[str, Any]:
    locator_id = "psid-whole-document:" + _digest(
        [DOCUMENT_ID, INTERVIEW_WAVE, PDF_SHA256, PDF_SIZE]
    )
    return {
        "locator_id": locator_id,
        "source_document_id": DOCUMENT_ID,
        "interview_wave": INTERVIEW_WAVE,
        "filename": "q84.pdf",
        "location_type": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": PDF_SIZE,
        "size_bytes": PDF_SIZE,
        "full_file_sha256": PDF_SHA256,
        "range_sha256": PDF_SHA256,
        "pdf_page_domain": "all_pages_and_flow_branches",
    }


def _review_specs() -> list[dict[str, Any]]:
    specs = [
        *copy.deepcopy(FLOW_SPECS),
        *copy.deepcopy(ANCHOR_SPECS),
        *copy.deepcopy(PROMPT_SPECS),
        *copy.deepcopy(REPEAT_SPECS),
    ]
    keys = [spec["key"] for spec in specs]
    if len(keys) != len(set(keys)):
        raise ValueError("review specification key collision")
    flow_keys = {spec["key"] for spec in FLOW_SPECS}
    anchor_keys = {spec["key"] for spec in ANCHOR_SPECS}
    for spec in specs:
        if spec["page"] not in ANNOTATED_PAGES:
            raise ValueError("review specification leaves annotated domain")
        for key in spec.get("parents") or ():
            domain = (
                flow_keys
                if spec["kind"] == "flow_branch_label"
                else (anchor_keys)
            )
            if key not in domain:
                raise ValueError(f"unresolved specification parent {key}")
        for key in spec.get("entries", ()):
            if key != "root" and key not in flow_keys:
                raise ValueError(f"unresolved specification entry {key}")
    for spec in PROMPT_SPECS:
        if set(spec["anchors"]) - anchor_keys:
            raise ValueError("unresolved prompt anchor")
        if not spec["purposes"]:
            raise ValueError("prompt row without a ratified field purpose")
    return specs


def _resolved_items(page_texts: Sequence[str]) -> list[dict[str, Any]]:
    items = []
    for spec in _review_specs():
        page_text = page_texts[spec["page"] - 1]
        matched, matched_sha256 = _strict_slice(
            page_text,
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["key"],
        )
        if matched != spec["expect"]:
            raise ValueError(
                f"{spec['key']} re-sliced source text is not the reviewed text"
            )
        items.append(
            {
                **spec,
                "matched_text": matched,
                "matched_utf8_sha256": matched_sha256,
            }
        )
    return items


def _expansion_counts(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    by_key = {item["key"]: item for item in items}
    counts: dict[str, int] = {}

    def resolve(key: str, seen: tuple[str, ...]) -> int:
        if key in counts:
            return counts[key]
        if key in seen:
            raise ValueError("flow specification cycle")
        item = by_key[key]
        parents = item.get("parents")
        if item["kind"] != "flow_branch_label" or parents is None:
            counts[key] = 1
        else:
            counts[key] = sum(
                resolve(parent, (*seen, key)) for parent in parents
            )
        if counts[key] < 1:
            raise ValueError("empty flow parent expansion")
        return counts[key]

    for item in items:
        if item["kind"] == "flow_branch_label":
            resolve(item["key"], ())
        else:
            counts[item["key"]] = 1
    return counts


def _occurrence_row(
    item: Mapping[str, Any],
    locator_id: str,
    index_on_page: int,
    semantic_ordinal: int,
    flow_paths: list[list[str]],
) -> dict[str, Any]:
    locator_sha256 = _digest(
        [
            DOCUMENT_ID,
            CANONICAL_SOURCE_PATH,
            "questionnaire_page_utf8_span",
            [
                INTERVIEW_WAVE,
                item["page"],
                item["utf8_byte_start"],
                item["utf8_byte_end"],
                index_on_page,
                semantic_ordinal,
                item["kind"],
            ],
        ]
    )
    values = [
        DOCUMENT_ID,
        locator_id,
        locator_sha256,
        INTERVIEW_WAVE,
        item["page"],
        item["utf8_byte_start"],
        item["utf8_byte_end"],
        index_on_page,
        semantic_ordinal,
        item["kind"],
        item["matched_text"],
        item["matched_utf8_sha256"],
        flow_paths,
    ]
    return {
        "questionnaire_occurrence_id": (
            "psid-questionnaire-occurrence:" + _digest(values)
        ),
        **dict(zip(OCCURRENCE_KEYS[1:], values, strict=True)),
    }


def _build_occurrences_and_branches(
    page_texts: Sequence[str], locator_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[str]]]:
    items = _resolved_items(page_texts)
    counts = _expansion_counts(items)
    by_key = {item["key"]: item for item in items}

    # Zero-based within-page indices follow start, end, displayed kind order,
    # then semantic ordinal; a multi-parent label occupies consecutive slots.
    groups = sorted(
        {
            (
                item["page"],
                item["utf8_byte_start"],
                item["utf8_byte_end"],
                KIND_ORDER[item["kind"]],
                item["key"],
            )
            for item in items
        }
    )
    seen_atoms: set[tuple[int, int, int, int]] = set()
    base_index: dict[str, int] = {}
    cursor: Counter[int] = Counter()
    for page, start, end, kind_index, key in groups:
        atom = (page, start, end, kind_index)
        if atom in seen_atoms:
            raise ValueError("duplicate atomic occurrence span and kind")
        seen_atoms.add(atom)
        base_index[key] = cursor[page]
        cursor[page] += counts[key]

    occurrences_by_key: dict[str, list[dict[str, Any]]] = {}
    branches_by_key: dict[str, list[dict[str, Any]]] = {}

    def parent_paths(item: Mapping[str, Any]) -> list[list[str]]:
        parents = item.get("parents")
        if parents is None:
            return [[FLOW_ROOT]]
        paths = [
            list(branch["branch_path"])
            for parent in parents
            for branch in branches_by_key[parent]
        ]
        if len({tuple(path) for path in paths}) != len(paths):
            raise ValueError("duplicate flow parent path")
        return sorted(paths, key=_path_sort_key)

    def build_flow(key: str) -> None:
        if key in occurrences_by_key:
            return
        item = by_key[key]
        for parent in item.get("parents") or ():
            build_flow(parent)
        paths = parent_paths(item)
        if len(paths) != counts[key]:
            raise ValueError("flow expansion count drift")
        rows: list[dict[str, Any]] = []
        branch_rows: list[dict[str, Any]] = []
        for ordinal, parent_path in enumerate(paths):
            semantic_ordinal = ordinal if len(paths) > 1 else 0
            index_on_page = base_index[key] + ordinal
            row = _occurrence_row(
                item,
                locator_id,
                index_on_page,
                semantic_ordinal,
                [list(parent_path)],
            )
            parent_id = parent_path[-1]
            branch_id = "questionnaire-flow:" + _digest(
                [parent_id, INTERVIEW_WAVE, row["questionnaire_occurrence_id"]]
            )
            if branch_id in parent_path:
                raise ValueError("flow cycle")
            branch_rows.append(
                {
                    "flow_branch_id": branch_id,
                    "parent_flow_branch_id": parent_id,
                    "source_occurrence_id": row["questionnaire_occurrence_id"],
                    "branch_path": [*parent_path, branch_id],
                    "interview_wave": INTERVIEW_WAVE,
                    "source_locator_id": locator_id,
                    "page_number": item["page"],
                    "occurrence_index_on_page": index_on_page,
                    "branch_label": item["matched_text"],
                    "branch_label_sha256": item["matched_utf8_sha256"],
                }
            )
            rows.append(row)
        occurrences_by_key[key] = rows
        branches_by_key[key] = branch_rows

    for item in items:
        if item["kind"] == "flow_branch_label":
            build_flow(item["key"])

    for item in items:
        if item["kind"] == "flow_branch_label":
            continue
        paths: list[list[str]] = []
        for entry in item["entries"]:
            if entry == "root":
                paths.append([FLOW_ROOT])
            else:
                paths.extend(
                    list(branch["branch_path"])
                    for branch in branches_by_key[entry]
                )
        if not paths:
            raise ValueError("occurrence without a resolved flow path")
        if len({tuple(path) for path in paths}) != len(paths):
            raise ValueError("duplicate occurrence flow path")
        occurrences_by_key[item["key"]] = [
            _occurrence_row(
                item,
                locator_id,
                base_index[item["key"]],
                0,
                sorted(paths, key=_path_sort_key),
            )
        ]

    occurrences = sorted(
        (row for rows in occurrences_by_key.values() for row in rows),
        key=lambda row: (row["page_number"], row["occurrence_index_on_page"]),
    )
    expected_indices = defaultdict(list)
    for row in occurrences:
        expected_indices[row["page_number"]].append(
            row["occurrence_index_on_page"]
        )
    for page, indices in expected_indices.items():
        if indices != list(range(len(indices))):
            raise ValueError(f"page {page} occurrence index domain drift")
    branches = sorted(
        (row for rows in branches_by_key.values() for row in rows),
        key=lambda row: (row["page_number"], row["occurrence_index_on_page"]),
    )
    ids_by_key = {
        key: [row["questionnaire_occurrence_id"] for row in rows]
        for key, rows in occurrences_by_key.items()
    }
    return occurrences, branches, ids_by_key


def _page_rows(
    replay_pages: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    locator_id: str,
) -> list[dict[str, Any]]:
    ids_by_page: dict[int, list[str]] = defaultdict(list)
    for occurrence in occurrences:
        ids_by_page[occurrence["page_number"]].append(
            occurrence["questionnaire_occurrence_id"]
        )
    rows = []
    for replay_page in replay_pages:
        page_number = replay_page["page_number"]
        rows.append(
            {
                "questionnaire_page_id": replay_page["questionnaire_page_id"],
                "source_document_id": DOCUMENT_ID,
                "source_locator_id": locator_id,
                "interview_wave": INTERVIEW_WAVE,
                "page_number": page_number,
                "page_text_utf8_sha256": replay_page["page_text_utf8_sha256"],
                "questionnaire_occurrence_ids": ids_by_page[page_number],
                # A deferred page states that its occurrence set is not yet
                # claimed complete; it never claims an empty canonical set.
                "annotation_status": (
                    "complete"
                    if page_number in ANNOTATED_PAGES
                    else "declared_domain_deferred"
                ),
            }
        )
    return rows


def _identifier_slice(
    spec: Mapping[str, Any], page_text: str
) -> tuple[str | None, list[int] | None]:
    identifier = spec.get("identifier")
    if identifier is None:
        return None, None
    start, end = _needle_span(page_text, identifier)
    matched, _ = _strict_slice(page_text, start, end, spec["key"])
    return matched, [spec["page"], start, end]


def _local_anchor_rows(
    page_texts: Sequence[str],
    ids_by_key: Mapping[str, Sequence[str]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in ANCHOR_SPECS:
        occurrence_id = ids_by_key[spec["key"]][0]
        occurrence = occurrence_by_id[occurrence_id]
        identifier, identifier_span = _identifier_slice(
            spec, page_texts[spec["page"] - 1]
        )
        parent_ids = [ids_by_key[key][0] for key in spec.get("parents", ())]
        preimage = [
            occurrence_id,
            spec["node_domain"],
            spec["classification"],
            identifier,
            identifier_span,
            parent_ids,
        ]
        rows.append(
            {
                "local_anchor_classification_id": (
                    "rq-local-anchor-classification:" + _digest(preimage)
                ),
                "source_occurrence_id": occurrence_id,
                "node_domain": spec["node_domain"],
                "classification": spec["classification"],
                "printed_identifier": identifier,
                "printed_identifier_utf8_span": identifier_span,
                "exact_label": occurrence["matched_text"],
                "exact_label_utf8_span": [
                    occurrence["page_number"],
                    occurrence["utf8_byte_start"],
                    occurrence["utf8_byte_end"],
                ],
                "parent_anchor_occurrence_ids": parent_ids,
                "annotation_status": "complete",
            }
        )
    rows.sort(
        key=lambda row: (
            occurrence_by_id[row["source_occurrence_id"]]["page_number"],
            occurrence_by_id[row["source_occurrence_id"]][
                "occurrence_index_on_page"
            ],
        )
    )
    return rows


def _purpose_rows(
    ids_by_key: Mapping[str, Sequence[str]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in PROMPT_SPECS:
        occurrence_id = ids_by_key[spec["key"]][0]
        occurrence = occurrence_by_id[occurrence_id]
        purposes = sorted(spec["purposes"], key=PURPOSE_ORDER.__getitem__)
        anchor_ids = [ids_by_key[key][0] for key in spec["anchors"]]
        preimage = [occurrence_id, purposes, anchor_ids]
        rows.append(
            {
                "local_field_purpose_classification_id": (
                    "rq-local-field-purpose:" + _digest(preimage)
                ),
                "source_prompt_occurrence_id": occurrence_id,
                "field_purposes": purposes,
                "applicable_anchor_occurrence_ids": anchor_ids,
                "exact_prompt": occurrence["matched_text"],
                "exact_prompt_utf8_span": [
                    occurrence["page_number"],
                    occurrence["utf8_byte_start"],
                    occurrence["utf8_byte_end"],
                ],
                "annotation_status": "complete",
            }
        )
    rows.sort(
        key=lambda row: (
            occurrence_by_id[row["source_prompt_occurrence_id"]][
                "page_number"
            ],
            occurrence_by_id[row["source_prompt_occurrence_id"]][
                "occurrence_index_on_page"
            ],
        )
    )
    return rows


def _repeat_rows(
    page_texts: Sequence[str],
    ids_by_key: Mapping[str, Sequence[str]],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if REPEAT_SPECS or SAME_LABEL_ALIAS_SPECS:
        raise ValueError("repeat/alias specification is not empty")
    # The annotated domain prints no repeat, cross-reference, or duplicated
    # identifier/label pair; every such instruction elsewhere in q84 is
    # dispositioned as a deferred candidate rather than bound here.
    return []


def _overlaps(
    left_start: int, left_end: int, right_start: int, right_end: int
) -> bool:
    return left_start < right_end and right_start < left_end


def _candidate_occurrence_projection(
    candidate_rows: Sequence[Mapping[str, Any]],
    output_rows: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    output_order = {
        row["questionnaire_occurrence_id"]: index
        for index, row in enumerate(output_rows)
    }
    result: dict[str, list[str]] = {}
    for candidate in candidate_rows:
        overlapping = [
            row
            for row in output_rows
            if row["page_number"] == candidate["page_number"]
            and _overlaps(
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                candidate["utf8_byte_start"],
                candidate["utf8_byte_end"],
            )
        ]
        targets = [
            row
            for row in overlapping
            if row["occurrence_kind"] == candidate["occurrence_kind_candidate"]
        ]
        if not targets and candidate["page_number"] in ANNOTATED_PAGES:
            # Reviewed kind correction: the printed text is retained under a
            # different section-19 kind than the detector proposed.
            targets = overlapping
        result[candidate["candidate_occurrence_id"]] = sorted(
            {row["questionnaire_occurrence_id"] for row in targets},
            key=output_order.__getitem__,
        )
    return result


def _candidate_occurrence_disposition(
    candidate: Mapping[str, Any],
    target_ids: Sequence[str],
    output_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    if not target_ids:
        return "rejected"
    if len(target_ids) > 1:
        return "split"
    output = output_by_id[target_ids[0]]
    if (
        output["occurrence_kind"] == candidate["occurrence_kind_candidate"]
        and output["page_number"] == candidate["page_number"]
        and output["utf8_byte_start"] == candidate["utf8_byte_start"]
        and output["utf8_byte_end"] == candidate["utf8_byte_end"]
        and output["matched_text"] == candidate["matched_text"]
        and output["matched_utf8_sha256"] == candidate["matched_utf8_sha256"]
    ):
        return "accepted"
    return "modified"


def _candidate_dispositions(
    candidate: Mapping[str, Any],
    locator: Mapping[str, Any],
    page_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
    branch_rows: Sequence[Mapping[str, Any]],
    anchor_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrence_rows
    }
    projection = _candidate_occurrence_projection(
        candidate["candidate_occurrence_rows"], occurrence_rows
    )
    disposition_by_id: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    def append(
        kind: str, candidate_id: str, disposition: str, ids: Sequence[str]
    ) -> None:
        rows.append(
            {
                "candidate_row_kind": kind,
                "candidate_id": candidate_id,
                "disposition": disposition,
                "stage2_row_ids": list(ids),
                "adjudication_status": "complete",
            }
        )
        disposition_by_id[candidate_id] = disposition

    append(
        "whole_document_locator",
        candidate["whole_document_locator_candidate"]["candidate_locator_id"],
        "accepted",
        [locator["locator_id"]],
    )
    for candidate_page, output_page in zip(
        candidate["candidate_page_rows"], page_rows, strict=True
    ):
        if candidate_page["page_number"] != output_page["page_number"]:
            raise ValueError("candidate page domain order drift")
        append(
            "page",
            candidate_page["candidate_page_id"],
            (
                "accepted"
                if output_page["annotation_status"] == "complete"
                else "modified"
            ),
            [output_page["questionnaire_page_id"]],
        )
    for candidate_occurrence in candidate["candidate_occurrence_rows"]:
        candidate_id = candidate_occurrence["candidate_occurrence_id"]
        ids = projection[candidate_id]
        append(
            "occurrence",
            candidate_id,
            _candidate_occurrence_disposition(
                candidate_occurrence, ids, output_by_id
            ),
            ids,
        )

    branch_id_by_source = {
        row["source_occurrence_id"]: row["flow_branch_id"]
        for row in branch_rows
    }
    branch_by_id = {row["flow_branch_id"]: row for row in branch_rows}
    candidate_ids_by_occurrence: dict[str, list[str]] = defaultdict(list)
    for candidate_occurrence_id, output_ids in projection.items():
        for output_id in output_ids:
            candidate_ids_by_occurrence[output_id].append(
                candidate_occurrence_id
            )
    candidate_branch_source: dict[str, str] = {}
    for candidate_path in candidate["candidate_flow_path_rows"]:
        existing = candidate_branch_source.setdefault(
            candidate_path["candidate_branch_id"],
            candidate_path["source_candidate_occurrence_id"],
        )
        if existing != candidate_path["source_candidate_occurrence_id"]:
            raise ValueError("candidate branch has multiple source labels")

    for candidate_path in candidate["candidate_flow_path_rows"]:
        source_candidate_id = candidate_path["source_candidate_occurrence_id"]
        candidate_parents = [
            candidate_branch_source[branch_id]
            for branch_id in candidate_path["candidate_parent_path"]
            if branch_id != candidates.FLOW_ROOT_ID
        ]
        ids: list[str] = []
        for occurrence_id in projection[source_candidate_id]:
            if occurrence_id not in branch_id_by_source:
                continue
            branch_id = branch_id_by_source[occurrence_id]
            final_parents = [
                branch_by_id[parent_id]["source_occurrence_id"]
                for parent_id in branch_by_id[branch_id]["branch_path"][1:-1]
            ]
            if len(candidate_parents) == len(final_parents) and all(
                candidate_parent
                in candidate_ids_by_occurrence[final_occurrence]
                for candidate_parent, final_occurrence in zip(
                    candidate_parents, final_parents, strict=True
                )
            ):
                ids.append(branch_id)
        if not ids:
            disposition = "rejected"
        elif len(ids) > 1:
            disposition = "split"
        else:
            disposition = (
                "accepted"
                if disposition_by_id[source_candidate_id] == "accepted"
                else "modified"
            )
        append(
            "flow_path",
            candidate_path["candidate_flow_path_id"],
            disposition,
            ids,
        )

    anchor_by_source = {
        row["source_occurrence_id"]: row for row in anchor_rows
    }
    for candidate_anchor in candidate["candidate_anchor_classification_rows"]:
        source_candidate_id = candidate_anchor[
            "source_candidate_occurrence_id"
        ]
        target_anchors = [
            anchor_by_source[occurrence_id]
            for occurrence_id in projection[source_candidate_id]
            if occurrence_id in anchor_by_source
        ]
        ids = [row["local_anchor_classification_id"] for row in target_anchors]
        if not ids:
            disposition = "rejected"
        elif len(ids) > 1:
            disposition = "split"
        else:
            target = target_anchors[0]
            projected_parents: list[str] = []
            for parent_candidate_id in candidate_anchor[
                "parent_anchor_candidate_ids"
            ]:
                projected_parents.extend(projection[parent_candidate_id])
            exact = (
                disposition_by_id[source_candidate_id] == "accepted"
                and target["node_domain"]
                == candidate_anchor["node_domain_candidate"]
                and target["classification"]
                == candidate_anchor["classification_candidate"]
                and target["printed_identifier"]
                == candidate_anchor["printed_identifier_candidate"]
                and _sha256(target["exact_label"].encode("utf-8"))
                == candidate_anchor["exact_label_sha256"]
                and target["parent_anchor_occurrence_ids"] == projected_parents
            )
            disposition = "accepted" if exact else "modified"
        append(
            "anchor_classification",
            candidate_anchor["candidate_anchor_classification_id"],
            disposition,
            ids,
        )
    return rows


def _output_relations(
    locator: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    purposes: Sequence[Mapping[str, Any]],
    repeats: Sequence[Mapping[str, Any]],
) -> list[tuple[str, str]]:
    return [
        ("whole_document_locator", locator["locator_id"]),
        *[("page", row["questionnaire_page_id"]) for row in pages],
        *[
            ("occurrence", row["questionnaire_occurrence_id"])
            for row in occurrences
        ],
        *[("flow_branch", row["flow_branch_id"]) for row in branches],
        *[
            (
                "local_anchor_classification",
                row["local_anchor_classification_id"],
            )
            for row in anchors
        ],
        *[
            (
                "local_field_purpose_classification",
                row["local_field_purpose_classification_id"],
            )
            for row in purposes
        ],
        *[
            ("local_repeat_or_alias_evidence", row["local_repeat_evidence_id"])
            for row in repeats
        ],
    ]


def _output_row_lookup(
    locator: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    branches: Sequence[Mapping[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    purposes: Sequence[Mapping[str, Any]],
    repeats: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    groups = (
        ((locator,), "locator_id"),
        (pages, "questionnaire_page_id"),
        (occurrences, "questionnaire_occurrence_id"),
        (branches, "flow_branch_id"),
        (anchors, "local_anchor_classification_id"),
        (purposes, "local_field_purpose_classification_id"),
        (repeats, "local_repeat_evidence_id"),
    )
    result: dict[str, Mapping[str, Any]] = {}
    for group, id_field in groups:
        for row in group:
            if row[id_field] in result:
                raise ValueError("stage-2 output IDs are not globally unique")
            result[row[id_field]] = row
    return result


def _output_adjudications(
    output_relations: Sequence[tuple[str, str]],
    candidate_dispositions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output_order = {
        output_id: index
        for index, (_, output_id) in enumerate(output_relations)
    }
    candidate_order = {
        row["candidate_id"]: index
        for index, row in enumerate(candidate_dispositions)
    }
    sources_by_output: dict[str, list[str]] = defaultdict(list)
    disposition_by_candidate: dict[str, str] = {}
    for row in candidate_dispositions:
        disposition_by_candidate[row["candidate_id"]] = row["disposition"]
        for output_id in row["stage2_row_ids"]:
            if output_id not in output_order:
                raise ValueError("candidate disposition names unknown output")
            sources_by_output[output_id].append(row["candidate_id"])

    rows: list[dict[str, Any]] = []
    for kind, output_id in output_relations:
        source_ids = sorted(
            sources_by_output[output_id], key=candidate_order.__getitem__
        )
        dispositions = {
            disposition_by_candidate[candidate_id]
            for candidate_id in source_ids
        }
        if not source_ids:
            action = "manual_add"
        elif dispositions == {"accepted"} and len(source_ids) == 1:
            action = "candidate_accepted"
        elif dispositions == {"modified"}:
            action = "candidate_modified"
        elif dispositions == {"split"} and len(source_ids) == 1:
            action = "candidate_split"
        elif dispositions <= {"accepted", "modified", "split"}:
            action = "candidate_modified"
        else:
            raise ValueError(
                f"mixed candidate dispositions for output {output_id}"
            )
        rows.append(
            {
                "stage2_row_kind": kind,
                "stage2_row_id": output_id,
                "source_candidate_ids": source_ids,
                "adjudication_action": action,
                "whole_page_review_complete": True,
                "source_span_verified": True,
                "adjudication_status": "complete",
            }
        )
    return rows


def _candidate_row_lookup(
    candidate: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    groups = (
        (
            (candidate["whole_document_locator_candidate"],),
            "candidate_locator_id",
        ),
        (candidate["candidate_page_rows"], "candidate_page_id"),
        (candidate["candidate_occurrence_rows"], "candidate_occurrence_id"),
        (candidate["candidate_flow_path_rows"], "candidate_flow_path_id"),
        (
            candidate["candidate_anchor_classification_rows"],
            "candidate_anchor_classification_id",
        ),
    )
    result: dict[str, Mapping[str, Any]] = {}
    for group, id_field in groups:
        for row in group:
            if row[id_field] in result:
                raise ValueError("candidate IDs are not globally unique")
            result[row[id_field]] = row
    return result


def _occurrence_location(row: Mapping[str, Any], *, candidate: bool) -> str:
    kind_field = (
        "occurrence_kind_candidate" if candidate else "occurrence_kind"
    )
    return (
        f"{row[kind_field]} on page {row['page_number']} at UTF-8 bytes "
        f"[{row['utf8_byte_start']}, {row['utf8_byte_end']})"
    )


DEFERRED_REASON_BY_PAGE = {
    entry_page: entry["reason_code"]
    for entry in DECLARED_SCOPE["remaining_work_ledger"]
    for entry_page in entry["page_domain"]
    if entry_page not in ANNOTATED_PAGES
}
# Every rejected candidate span inside the annotated page carries its own
# reviewed reason.  Spans are the detector's, re-read against the page bytes.
PAGE_5_REJECTION_REASONS: dict[tuple[int, int], str] = {
    **{
        span: "two_up_column_inversion_blocked"
        for span in (
            (659, 818),
            (700, 708),
            (719, 740),
            (3231, 3339),
            (3270, 3278),
            (3681, 3843),
            (3713, 3727),
            (3757, 3761),
            (3794, 3821),
            (4321, 4333),
            (5413, 5419),
            (5413, 5481),
            (5465, 5481),
            (6028, 6099),
            (6499, 6520),
            (7082, 7098),
            (7378, 7386),
            (9863, 9871),
            (10147, 10164),
            (11658, 11662),
            (12313, 12327),
            (12829, 12966),
            (14532, 14549),
        )
    },
    **{
        span: "cross_column_run_not_a_printed_unit"
        for span in (
            (2466, 2614),
            (4875, 5041),
            (8106, 8392),
            (10730, 10950),
            (11189, 11306),
            (11771, 12009),
        )
    },
    (2756, 2766): "printed_label_continuation_fragment",
}
PAGE_5_REJECTION_NOTES = {
    "two_up_column_inversion_blocked": (
        "prints in page 5's right column (questions C8-C18, including the "
        "C12 salary, C14/C18 overtime-rate, and C15/C16 hourly-wage fields). "
        "Its printed control-flow parents (C4 '3. SELF ONLY', C6 '5. NO', C7) "
        "occur at larger page-byte offsets, so section 19's "
        "earlier-resolving-parent law cannot express its ancestry; see "
        "recorded interpretation doc34-u2-two-up-column-inversion"
    ),
    "cross_column_run_not_a_printed_unit": (
        "is one extracted run spanning both questionnaire columns of the "
        "two-up scan, so it is not a single printed unit and cannot be a "
        "lawful atomic occurrence; the reviewer re-sliced the in-domain "
        "left-column unit separately"
    ),
    "printed_label_continuation_fragment": (
        "is the printed continuation of the annotated branch label "
        "'3. LOOKING' at UTF-8 bytes [2184, 2194); the label occurrence "
        "carries the branch and its continuation is not a separate atom"
    ),
}


def _annotated_page_rejection(
    candidate_row: Mapping[str, Any], source: str
) -> tuple[str, str]:
    span = (
        candidate_row["utf8_byte_start"],
        candidate_row["utf8_byte_end"],
    )
    reason = PAGE_5_REJECTION_REASONS.get(span)
    if reason is None:
        raise ValueError(f"unreviewed annotated-page rejection at {span}")
    return (
        reason,
        f"Whole-page review determined that candidate {source} "
        f"{PAGE_5_REJECTION_NOTES[reason]}; no output row was emitted.",
    )


def _deferred_note(page_number: int, source: str) -> tuple[str, str]:
    reason = DEFERRED_REASON_BY_PAGE[page_number]
    return (
        reason,
        f"Page {page_number} was read end to end during the whole-document "
        f"pass and lies outside this lane's declared annotation domain "
        f"({reason}); candidate {source} is deferred with its printed "
        "evidence preserved and no output row emitted.",
    )


def _candidate_correction(
    disposition: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    output_rows: Sequence[Mapping[str, Any]],
    candidate_rows_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    kind = disposition["candidate_row_kind"]
    action = disposition["disposition"]
    if kind == "page":
        page_number = candidate_row["page_number"]
        reason = DEFERRED_REASON_BY_PAGE[page_number]
        return (
            reason,
            f"Page {page_number} reproduces its replayed text hash and is "
            "emitted with annotation_status declared_domain_deferred: it was "
            "fully read but lies outside the declared annotation domain "
            f"({reason}), so its occurrence set is not claimed complete.",
        )
    if kind == "occurrence":
        source = _occurrence_location(candidate_row, candidate=True)
        if action == "rejected":
            if candidate_row["page_number"] not in ANNOTATED_PAGES:
                return _deferred_note(candidate_row["page_number"], source)
            return _annotated_page_rejection(candidate_row, source)
        targets = [
            _occurrence_location(target, candidate=False)
            for target in output_rows
        ]
        if action == "split":
            return (
                "compound_occurrence_split",
                f"Candidate {source} overlaps {len(targets)} independently "
                f"verified atoms: {'; '.join(targets)}.",
            )
        target = output_rows[0]
        kind_changed = (
            candidate_row["occurrence_kind_candidate"]
            != target["occurrence_kind"]
        )
        span_changed = (
            candidate_row["utf8_byte_start"],
            candidate_row["utf8_byte_end"],
        ) != (target["utf8_byte_start"], target["utf8_byte_end"])
        if kind_changed and span_changed:
            reason = "occurrence_kind_and_span_corrected"
        elif kind_changed:
            reason = "occurrence_kind_corrected"
        elif span_changed:
            reason = "occurrence_span_corrected"
        else:
            reason = "occurrence_exact_text_corrected"
        return (
            reason,
            f"Candidate {source} was corrected to the independently "
            f"re-sliced {_occurrence_location(target, candidate=False)}.",
        )

    if kind == "flow_path":
        source_occurrence = candidate_rows_by_id[
            candidate_row["source_candidate_occurrence_id"]
        ]
        source = _occurrence_location(source_occurrence, candidate=True)
        candidate_path = json.dumps(
            candidate_row["candidate_parent_path"], separators=(",", ":")
        )
        if action == "rejected":
            if source_occurrence["page_number"] not in ANNOTATED_PAGES:
                return _deferred_note(source_occurrence["page_number"], source)
            if (
                source_occurrence["utf8_byte_start"],
                source_occurrence["utf8_byte_end"],
            ) in PAGE_5_REJECTION_REASONS:
                return _annotated_page_rejection(source_occurrence, source)
            return (
                "unselected_flow_ancestry_rejected",
                f"Candidate path for {source} has parent path "
                f"{candidate_path}; the independently reconstructed "
                "control-flow graph has no matching path for that label.",
            )
        final_paths = json.dumps(
            [row["branch_path"] for row in output_rows],
            separators=(",", ":"),
        )
        if action == "split":
            return (
                "flow_path_split",
                f"Candidate path for {source} was split into "
                f"{len(output_rows)} complete retained branch paths "
                f"{final_paths}.",
            )
        return (
            "flow_ancestry_corrected",
            f"Candidate path for {source} used parent path {candidate_path}; "
            f"the retained complete branch path is {final_paths}.",
        )

    if kind == "anchor_classification":
        source_occurrence = candidate_rows_by_id[
            candidate_row["source_candidate_occurrence_id"]
        ]
        source = _occurrence_location(source_occurrence, candidate=True)
        if action == "rejected":
            if source_occurrence["page_number"] not in ANNOTATED_PAGES:
                return _deferred_note(source_occurrence["page_number"], source)
            if (
                source_occurrence["utf8_byte_start"],
                source_occurrence["utf8_byte_end"],
            ) in PAGE_5_REJECTION_REASONS:
                return _annotated_page_rejection(source_occurrence, source)
            return (
                "nonestablishing_anchor_classification_rejected",
                f"Candidate anchor classification for {source} has no "
                "retained local establishing anchor after whole-page review.",
            )
        targets = [
            (
                f"{row['node_domain']}/{row['classification']} with printed "
                f"identifier {row['printed_identifier']!r} and parents "
                + json.dumps(
                    row["parent_anchor_occurrence_ids"],
                    separators=(",", ":"),
                )
            )
            for row in output_rows
        ]
        if action == "split":
            return (
                "anchor_classification_split",
                f"Candidate anchor classification for {source} was split "
                f"into {len(targets)} local anchors: {'; '.join(targets)}.",
            )
        return (
            "anchor_definition_corrected",
            f"Candidate anchor classification for {source} was corrected "
            f"from {candidate_row['node_domain_candidate']}/"
            f"{candidate_row['classification_candidate']} to {targets[0]}.",
        )

    return (
        "candidate_domain_row_rejected",
        f"Candidate {kind} row {disposition['candidate_id']} has no retained "
        "stage-2 output after exact domain review.",
    )


def _manual_add_note(
    kind: str, output_row: Mapping[str, Any]
) -> tuple[str, str]:
    if kind == "occurrence":
        return (
            "manual_occurrence_after_complete_page_review",
            "Complete page review added independently re-sliced "
            f"{_occurrence_location(output_row, candidate=False)} with flow "
            "paths "
            + json.dumps(
                output_row["flow_branch_paths"], separators=(",", ":")
            ),
        )
    if kind == "flow_branch":
        return (
            "manual_flow_branch_after_complete_page_review",
            f"Complete page review added branch label "
            f"{output_row['branch_label']!r} with complete path "
            + json.dumps(output_row["branch_path"], separators=(",", ":")),
        )
    if kind == "local_anchor_classification":
        return (
            "manual_anchor_after_complete_page_review",
            "Complete page review classified source occurrence "
            f"{output_row['source_occurrence_id']} as "
            f"{output_row['node_domain']}/{output_row['classification']} "
            "with parents "
            + json.dumps(
                output_row["parent_anchor_occurrence_ids"],
                separators=(",", ":"),
            ),
        )
    if kind == "local_field_purpose_classification":
        return (
            "manual_field_purpose_after_complete_page_review",
            "Complete page review classified prompt occurrence "
            f"{output_row['source_prompt_occurrence_id']} with exact "
            "purposes "
            + json.dumps(output_row["field_purposes"], separators=(",", ":")),
        )
    raise ValueError(f"unexpected manual-add row kind {kind}")


def _correction_notes(
    candidate: Mapping[str, Any],
    candidate_dispositions: Sequence[Mapping[str, Any]],
    output_adjudications: Sequence[Mapping[str, Any]],
    output_rows_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    candidate_rows_by_id = _candidate_row_lookup(candidate)
    for row in candidate_dispositions:
        if row["disposition"] == "accepted":
            continue
        reason, note = _candidate_correction(
            row,
            candidate_rows_by_id[row["candidate_id"]],
            [
                output_rows_by_id[output_id]
                for output_id in row["stage2_row_ids"]
            ],
            candidate_rows_by_id,
        )
        preimage = [
            "candidate_disposition",
            row["candidate_row_kind"],
            row["candidate_id"],
            reason,
        ]
        rows.append(
            {
                "correction_note_id": "rq-correction-note:"
                + _digest(preimage),
                "subject_relation": "candidate_disposition",
                "subject_row_kind": row["candidate_row_kind"],
                "subject_row_id": row["candidate_id"],
                "reason_code": reason,
                "note": note,
                "adjudication_status": "complete",
            }
        )
    for row in output_adjudications:
        if row["adjudication_action"] != "manual_add":
            continue
        reason, note = _manual_add_note(
            row["stage2_row_kind"], output_rows_by_id[row["stage2_row_id"]]
        )
        preimage = [
            "output_adjudication",
            row["stage2_row_kind"],
            row["stage2_row_id"],
            reason,
        ]
        rows.append(
            {
                "correction_note_id": "rq-correction-note:"
                + _digest(preimage),
                "subject_relation": "output_adjudication",
                "subject_row_kind": row["stage2_row_kind"],
                "subject_row_id": row["stage2_row_id"],
                "reason_code": reason,
                "note": note,
                "adjudication_status": "complete",
            }
        )
    return rows


ROW_DOMAIN_SPECS = (
    ("whole_document_locator_rows", ("locator_id",)),
    ("questionnaire_page_rows", ("questionnaire_page_id",)),
    ("questionnaire_occurrence_rows", ("questionnaire_occurrence_id",)),
    ("flow_branch_rows", ("flow_branch_id",)),
    ("local_anchor_classification_rows", ("local_anchor_classification_id",)),
    (
        "local_field_purpose_classification_rows",
        ("local_field_purpose_classification_id",),
    ),
    ("local_repeat_or_alias_evidence_rows", ("local_repeat_evidence_id",)),
    ("candidate_disposition_rows", ("candidate_row_kind", "candidate_id")),
    ("output_adjudication_rows", ("stage2_row_kind", "stage2_row_id")),
    ("correction_note_rows", ("correction_note_id",)),
)


def _row_keyset(
    rows: Sequence[Mapping[str, Any]], key_fields: Sequence[str]
) -> list[Any]:
    if len(key_fields) == 1:
        return [row[key_fields[0]] for row in rows]
    return [[row[field] for field in key_fields] for row in rows]


def _seal(value: Mapping[str, Any]) -> dict[str, Any]:
    seal_rows = []
    for domain, key_fields in ROW_DOMAIN_SPECS:
        rows = value[domain]
        seal_rows.append(
            {
                "row_domain": domain,
                "row_count": len(rows),
                "row_key_fields": list(key_fields),
                "row_keyset_sha256": _digest(_row_keyset(rows, key_fields)),
                "row_domain_sha256": _digest(rows),
            }
        )
    return {
        "row_domain_seal_rows": seal_rows,
        "row_domain_seal_count": len(seal_rows),
        "row_domain_seal_domain_sha256": _digest(seal_rows),
        "seal_status": "pass_complete",
    }


AUTHORITY_DISPOSITION = {
    "authority_kind": "sealed_document_annotation_nonauthority",
    "sealed_document_count": 1,
    "whole_document_page_review_complete": True,
    "annotated_page_domain_complete": True,
    "document_annotation_completeness": "declared_domain_complete",
    "candidate_auto_promotion_permitted": False,
    "downstream_authority_inputs_read": False,
    "global_resolution_performed": False,
    "canonical_q5_artifact_emitted": False,
    "canonical_era_seal_emitted": False,
    "status": "pass",
}

OUTER_KEYS = (
    "schema_version",
    "artifact_id",
    "authority_disposition",
    "document_local_annotation_scope",
    "source_replay_identity",
    "candidate_index_identity",
    "candidate_artifact_identity",
    "document_source_position",
    "document_source_row",
    "questionnaire_page_text_derivation",
    "whole_document_locator_rows",
    "questionnaire_page_rows",
    "questionnaire_occurrence_rows",
    "flow_branch_rows",
    "local_anchor_classification_rows",
    "local_field_purpose_classification_rows",
    "local_repeat_or_alias_evidence_rows",
    "candidate_disposition_rows",
    "output_adjudication_rows",
    "correction_note_rows",
    "seal",
    "integrity",
    "status",
)


def _document_row(replay: Mapping[str, Any]) -> Mapping[str, Any]:
    document = replay["source_document_replay"]["questionnaire_documents"][
        DOCUMENT_POSITION - 1
    ]
    if (
        document["source_document_id"] != DOCUMENT_ID
        or document["interview_waves"] != [INTERVIEW_WAVE]
        or document["canonical_source_path"] != CANONICAL_SOURCE_PATH
        or document["byte_size"] != PDF_SIZE
        or document["sha256"] != PDF_SHA256
        or document["document_role"] != "questionnaire_flow"
    ):
        raise ValueError("document-34 independently replayed identity drift")
    return document


def _assemble(
    replay: Mapping[str, Any],
    index: Mapping[str, Any],
    candidate: Mapping[str, Any],
    page_texts: Sequence[str],
    replay_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    document = _document_row(replay)
    if document != candidate["document_source_row"]:
        raise ValueError("candidate document differs from source replay")
    locator = _locator()
    occurrences, branches, ids_by_key = _build_occurrences_and_branches(
        page_texts, locator["locator_id"]
    )
    pages = _page_rows(replay_pages, occurrences, locator["locator_id"])
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    anchors = _local_anchor_rows(page_texts, ids_by_key, occurrence_by_id)
    purposes = _purpose_rows(ids_by_key, occurrence_by_id)
    repeats = _repeat_rows(page_texts, ids_by_key, occurrence_by_id)
    dispositions = _candidate_dispositions(
        candidate, locator, pages, occurrences, branches, anchors
    )
    output_relations = _output_relations(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    output_rows_by_id = _output_row_lookup(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    adjudications = _output_adjudications(output_relations, dispositions)
    notes = _correction_notes(
        candidate, dispositions, adjudications, output_rows_by_id
    )
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": (
            "rq-stage2-document-annotation:"
            + _digest([DOCUMENT_ID, INTERVIEW_WAVE])
        ),
        "authority_disposition": copy.deepcopy(AUTHORITY_DISPOSITION),
        "document_local_annotation_scope": copy.deepcopy(DECLARED_SCOPE),
        "source_replay_identity": _identity(
            REPLAY_PATH,
            replay["schema_version"],
            replay["artifact_id"],
            REPLAY_RAW_SHA256,
            REPLAY_CONTENT_SHA256,
        ),
        "candidate_index_identity": _identity(
            INDEX_PATH,
            index["schema_version"],
            index["artifact_id"],
            INDEX_RAW_SHA256,
            INDEX_CONTENT_SHA256,
        ),
        "candidate_artifact_identity": {
            **_identity(
                CANDIDATE_PATH,
                candidate["schema_version"],
                candidate["artifact_id"],
                CANDIDATE_RAW_SHA256,
                CANDIDATE_CONTENT_SHA256,
            ),
            "candidate_payload_sha256": CANDIDATE_PAYLOAD_SHA256,
        },
        "document_source_position": DOCUMENT_POSITION,
        "document_source_row": copy.deepcopy(document),
        "questionnaire_page_text_derivation": copy.deepcopy(
            replay["questionnaire_page_replay"][
                "questionnaire_page_text_derivation"
            ]
        ),
        "whole_document_locator_rows": [locator],
        "questionnaire_page_rows": pages,
        "questionnaire_occurrence_rows": occurrences,
        "flow_branch_rows": branches,
        "local_anchor_classification_rows": anchors,
        "local_field_purpose_classification_rows": purposes,
        "local_repeat_or_alias_evidence_rows": repeats,
        "candidate_disposition_rows": dispositions,
        "output_adjudication_rows": adjudications,
        "correction_note_rows": notes,
        "seal": {},
        "integrity": {
            "canonicalization": candidates.CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": STATUS,
    }
    value["seal"] = _seal(value)
    value["integrity"]["content_sha256"] = _content_digest(value)
    return value


def build_annotation(capture_root: Path | None = None) -> dict[str, Any]:
    """Build document 34 from pinned source bytes and explicit decisions."""

    capture_root = (
        _default_capture_root() if capture_root is None else capture_root
    )
    replay, index = _load_replay_and_index()
    page_texts = _derive_pages(capture_root)
    replay_pages = _review_page_rows(replay, page_texts)
    candidate = _load_candidate(replay, index)
    value = _assemble(replay, index, candidate, page_texts, replay_pages)
    validate_annotation(value, capture_root=capture_root)
    return value


def _validate_exact_rows(
    rows: Sequence[Mapping[str, Any]], keys: Sequence[str], label: str
) -> None:
    for index, row in enumerate(rows):
        _expect_keys(row, keys, f"{label}[{index}]")


def _candidate_domain(candidate: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        (
            "whole_document_locator",
            candidate["whole_document_locator_candidate"][
                "candidate_locator_id"
            ],
        ),
        *[
            ("page", row["candidate_page_id"])
            for row in candidate["candidate_page_rows"]
        ],
        *[
            ("occurrence", row["candidate_occurrence_id"])
            for row in candidate["candidate_occurrence_rows"]
        ],
        *[
            ("flow_path", row["candidate_flow_path_id"])
            for row in candidate["candidate_flow_path_rows"]
        ],
        *[
            (
                "anchor_classification",
                row["candidate_anchor_classification_id"],
            )
            for row in candidate["candidate_anchor_classification_rows"]
        ],
    ]


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-34 source and sealing invariant."""

    capture_root = (
        _default_capture_root() if capture_root is None else capture_root
    )
    replay, index = _load_replay_and_index()
    page_texts = _derive_pages(capture_root)
    replay_pages = _review_page_rows(replay, page_texts)
    _expect_keys(value, OUTER_KEYS, "stage-2 annotation")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["artifact_id"]
        != "rq-stage2-document-annotation:"
        + _digest([DOCUMENT_ID, INTERVIEW_WAVE])
        or value["document_source_position"] != DOCUMENT_POSITION
        or value["document_source_row"] != _document_row(replay)
        or value["questionnaire_page_text_derivation"]
        != replay["questionnaire_page_replay"][
            "questionnaire_page_text_derivation"
        ]
        or value["status"] != STATUS
    ):
        raise ValueError("stage-2 outer identity drift")
    if value["authority_disposition"] != AUTHORITY_DISPOSITION:
        raise ValueError("stage-2 nonauthority disposition drift")
    if value["document_local_annotation_scope"] != DECLARED_SCOPE:
        raise ValueError("declared annotation scope drift")
    scope = value["document_local_annotation_scope"]
    ledger_pages = [
        page
        for entry in scope["remaining_work_ledger"]
        for page in entry["page_domain"]
    ]
    if sorted(set(ledger_pages) | set(ANNOTATED_PAGES)) != list(
        range(1, PAGE_COUNT + 1)
    ):
        raise ValueError("remaining-work ledger does not cover every page")

    if value["source_replay_identity"] != _identity(
        REPLAY_PATH,
        replay["schema_version"],
        replay["artifact_id"],
        REPLAY_RAW_SHA256,
        REPLAY_CONTENT_SHA256,
    ) or value["candidate_index_identity"] != _identity(
        INDEX_PATH,
        index["schema_version"],
        index["artifact_id"],
        INDEX_RAW_SHA256,
        INDEX_CONTENT_SHA256,
    ):
        raise ValueError("stage-2 replay or index identity drift")

    locator_rows = value["whole_document_locator_rows"]
    _validate_exact_rows(locator_rows, LOCATOR_KEYS, "locator")
    if locator_rows != [_locator()]:
        raise ValueError("whole-document locator drift")
    locator = locator_rows[0]
    if (
        locator["location_type"] != "whole_document_exact_file_range"
        or locator["byte_start"] != 0
        or locator["byte_end"] != locator["size_bytes"]
        or locator["range_sha256"] != locator["full_file_sha256"]
        or locator["pdf_page_domain"] != "all_pages_and_flow_branches"
    ):
        raise ValueError("whole-file locator equation failure")

    pages = value["questionnaire_page_rows"]
    occurrences = value["questionnaire_occurrence_rows"]
    branches = value["flow_branch_rows"]
    anchors = value["local_anchor_classification_rows"]
    purposes = value["local_field_purpose_classification_rows"]
    repeats = value["local_repeat_or_alias_evidence_rows"]
    dispositions = value["candidate_disposition_rows"]
    adjudications = value["output_adjudication_rows"]
    notes = value["correction_note_rows"]
    _validate_exact_rows(pages, PAGE_KEYS, "page")
    _validate_exact_rows(occurrences, OCCURRENCE_KEYS, "occurrence")
    _validate_exact_rows(branches, BRANCH_KEYS, "flow branch")
    _validate_exact_rows(anchors, ANCHOR_KEYS, "local anchor")
    _validate_exact_rows(purposes, PURPOSE_KEYS, "field purpose")
    _validate_exact_rows(repeats, REPEAT_KEYS, "repeat evidence")
    _validate_exact_rows(
        dispositions, DISPOSITION_KEYS, "candidate disposition"
    )
    _validate_exact_rows(
        adjudications, ADJUDICATION_KEYS, "output adjudication"
    )
    _validate_exact_rows(notes, NOTE_KEYS, "correction note")
    _validate_exact_rows(
        value["seal"]["row_domain_seal_rows"], SEAL_ROW_KEYS, "seal row"
    )

    expected_occurrences, expected_branches, ids_by_key = (
        _build_occurrences_and_branches(page_texts, locator["locator_id"])
    )
    expected_pages = _page_rows(
        replay_pages, expected_occurrences, locator["locator_id"]
    )
    if pages != expected_pages:
        raise ValueError("missing, reordered, or changed questionnaire page")
    if [row["page_number"] for row in pages] != list(range(1, PAGE_COUNT + 1)):
        raise ValueError("page rows do not exact-cover the replayed pages")
    if occurrences != expected_occurrences:
        raise ValueError("occurrence span, path, order, hash, or ID drift")
    if branches != expected_branches:
        raise ValueError("flow branch ancestry, label, path, or ID drift")

    # Page reverse cover: every occurrence resolves exactly once through its
    # page row and the one whole-document locator.
    ids_by_page = {
        row["page_number"]: row["questionnaire_occurrence_ids"]
        for row in pages
    }
    seen: Counter[str] = Counter()
    for row in occurrences:
        if row["source_locator_id"] != locator["locator_id"]:
            raise ValueError("occurrence locator does not resolve")
        if (
            row["questionnaire_occurrence_id"]
            not in ids_by_page[row["page_number"]]
        ):
            raise ValueError("occurrence is absent from its page projection")
        seen[row["questionnaire_occurrence_id"]] += 1
    if any(count != 1 for count in seen.values()):
        raise ValueError("occurrence resolves more than once")
    if sum(len(ids) for ids in ids_by_page.values()) != len(occurrences):
        raise ValueError("page occurrence projection is not exact")
    branch_ids = {row["flow_branch_id"] for row in branches}
    for row in occurrences:
        if not row["flow_branch_paths"]:
            raise ValueError("occurrence without a flow path")
        for path in row["flow_branch_paths"]:
            if not path or path[0] != FLOW_ROOT:
                raise ValueError("flow path is not rooted")
            if any(part not in branch_ids for part in path[1:]):
                raise ValueError("flow path leaves the resolved wave domain")
        if (
            sorted(row["flow_branch_paths"], key=_path_sort_key)
            != row["flow_branch_paths"]
        ):
            raise ValueError("flow path order drift")
        if (
            row["occurrence_kind"] == "flow_branch_label"
            and len(row["flow_branch_paths"]) != 1
        ):
            raise ValueError("branch label without exactly one parent path")

    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    if len(occurrence_by_id) != len(occurrences):
        raise ValueError("duplicate occurrence ID")
    index_by_id = {
        row["questionnaire_occurrence_id"]: index
        for index, row in enumerate(occurrences)
    }
    for row in branches:
        source = occurrence_by_id[row["source_occurrence_id"]]
        if (
            source["occurrence_kind"] != "flow_branch_label"
            or row["page_number"] != source["page_number"]
            or row["occurrence_index_on_page"]
            != source["occurrence_index_on_page"]
            or row["branch_label"] != source["matched_text"]
            or row["branch_label_sha256"] != source["matched_utf8_sha256"]
            or row["source_locator_id"] != source["source_locator_id"]
            or row["interview_wave"] != source["interview_wave"]
        ):
            raise ValueError("branch row does not deep-equal its occurrence")
        if row["branch_path"][:-1] != source["flow_branch_paths"][0]:
            raise ValueError("branch path does not extend its parent path")
        if row["parent_flow_branch_id"] != FLOW_ROOT:
            parent = next(
                item
                for item in branches
                if item["flow_branch_id"] == row["parent_flow_branch_id"]
            )
            if (
                index_by_id[parent["source_occurrence_id"]]
                >= index_by_id[row["source_occurrence_id"]]
            ):
                raise ValueError("flow parent is not an earlier branch")
    if len({row["flow_branch_id"] for row in branches}) != len(branches) or (
        len({row["source_occurrence_id"] for row in branches}) != len(branches)
    ):
        raise ValueError(
            "branch IDs and source occurrences are not one-to-one"
        )

    expected_anchors = _local_anchor_rows(
        page_texts, ids_by_key, occurrence_by_id
    )
    expected_purposes = _purpose_rows(ids_by_key, occurrence_by_id)
    expected_repeats = _repeat_rows(page_texts, ids_by_key, occurrence_by_id)
    if anchors != expected_anchors:
        raise ValueError("local anchor classification or parent drift")
    if purposes != expected_purposes:
        raise ValueError("field-purpose classification or evidence drift")
    if repeats != expected_repeats:
        raise ValueError("repeat/alias evidence is incomplete or inferred")

    # Candidate evidence is opened only after the source bytes have
    # independently reproduced every output row domain above.
    candidate = _load_candidate(replay, index)
    if value["document_source_row"] != candidate["document_source_row"]:
        raise ValueError("candidate document differs from source replay")
    if value["candidate_artifact_identity"] != {
        **_identity(
            CANDIDATE_PATH,
            candidate["schema_version"],
            candidate["artifact_id"],
            CANDIDATE_RAW_SHA256,
            CANDIDATE_CONTENT_SHA256,
        ),
        "candidate_payload_sha256": CANDIDATE_PAYLOAD_SHA256,
    }:
        raise ValueError("stage-2 candidate identity drift")

    expected_dispositions = _candidate_dispositions(
        candidate, locator, pages, occurrences, branches, anchors
    )
    if dispositions != expected_dispositions:
        raise ValueError("candidate disposition exact cover drift")
    if len(dispositions) != CANDIDATE_DENOMINATOR:
        raise ValueError("document-34 candidate denominator drift")
    if [
        (row["candidate_row_kind"], row["candidate_id"])
        for row in dispositions
    ] != _candidate_domain(candidate):
        raise ValueError("candidate disposition domain order drift")
    for row in dispositions:
        count = len(row["stage2_row_ids"])
        if (
            (row["disposition"] in {"accepted", "modified"} and count != 1)
            or (row["disposition"] == "split" and count < 2)
            or (row["disposition"] == "rejected" and count != 0)
        ):
            raise ValueError("candidate disposition arity law failure")

    output_relations = _output_relations(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    output_rows_by_id = _output_row_lookup(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    if adjudications != _output_adjudications(output_relations, dispositions):
        raise ValueError(
            "output adjudication exact cover or reverse-map drift"
        )
    if len(output_rows_by_id) != len(output_relations):
        raise ValueError("stage-2 output IDs are not globally unique")
    for row in adjudications:
        if row["adjudication_action"] == "manual_add" and (
            row["source_candidate_ids"]
            or not row["whole_page_review_complete"]
            or not row["source_span_verified"]
        ):
            raise ValueError("manual addition law failure")

    adjudication_by_id = {row["stage2_row_id"]: row for row in adjudications}
    for row in dispositions:
        for output_id in row["stage2_row_ids"]:
            if (
                row["candidate_id"]
                not in adjudication_by_id[output_id]["source_candidate_ids"]
            ):
                raise ValueError("candidate/output adjudication is one-sided")
    disposition_by_candidate = {
        row["candidate_id"]: row["stage2_row_ids"] for row in dispositions
    }
    for row in adjudications:
        for candidate_id in row["source_candidate_ids"]:
            if (
                row["stage2_row_id"]
                not in disposition_by_candidate[candidate_id]
            ):
                raise ValueError("output/candidate adjudication is one-sided")

    if notes != _correction_notes(
        candidate, dispositions, adjudications, output_rows_by_id
    ):
        raise ValueError("correction-note exact cover drift")
    if value["seal"] != _seal(value):
        raise ValueError("row-domain seal drift")
    if value["integrity"] != {
        "canonicalization": candidates.CANONICALIZATION,
        "content_sha256": _content_digest(value),
    }:
        raise ValueError("stage-2 whole-artifact integrity drift")

    serialized = json.dumps(value, ensure_ascii=True)
    forbidden = (
        "psid-job-slot:",
        "psid-component-slot:",
        "psid-node-alias:",
        "psid-questionnaire-relationship:",
        '"canonical_node_id"',
        '"source_inventory_key"',
        '"era_rows"',
        '"global_relationship_rows"',
    )
    if any(token in serialized for token in forbidden):
        raise ValueError("forbidden global authority output emitted")


def _write(value: Mapping[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(_canonical_bytes(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--capture-root", type=Path, default=None)
    args = parser.parse_args()
    value = build_annotation(args.capture_root)
    expected = _canonical_bytes(value)
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_bytes() != expected:
            raise SystemExit(
                f"stale or missing {OUTPUT_PATH.relative_to(ROOT)}"
            )
        validate_annotation(
            _strict_load(OUTPUT_PATH, "stage-2 document-34 annotation"),
            capture_root=args.capture_root,
        )
    else:
        _write(value)
    counts = Counter(
        row["disposition"] for row in value["candidate_disposition_rows"]
    )
    print(
        "document 34: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, "
        f"{sum(counts.values())} candidates "
        f"({dict(sorted(counts.items()))}), sealed"
    )


if __name__ == "__main__":
    main()
