#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for q87.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 53-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

Two review rules govern this document, an early two-column scan whose pinned
Poppler derivation interleaves the left and right printed pages on one
physical line:

1. Every emitted span is one contiguous exact byte slice of the page.  Printed
   text the layout derivation interleaves with unrelated column text is not
   lawfully locatable as a single label and is rejected rather than stitched.
2. An anchor is retained only when it establishes, for the head or spouse
   role, a job, a remuneration component, a job context, or a farm/business
   aggregate.  Other-family-member, parent, and non-employment prose cannot
   resolve either catalog role and is rejected.
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

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402
import build_rq_stage1_candidates as candidates  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

SCHEMA_VERSION = "rq_stage2_document_annotation.v1"
STATUS = "pass_sealed_complete_nonauthority_annotation"
DOCUMENT_POSITION = 40
DOCUMENT_ID = (
    "psid-source-document:"
    "7953106faa93bf55aef2cf58fc482bee3582e6873b9f4441c8447c8494b08473"
)
INTERVIEW_WAVE = 1987
CANONICAL_SOURCE_PATH = "documentation/capture1/q87.pdf"
PDF_SIZE = 2_794_108
PDF_SHA256 = "93ec286ea29c978b5e2571be20bd8690429b9ee7468029aade90b8d46d278d70"
PAGE_COUNT = 53
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_04_documents_031_040"
    / "document_040_q87_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_040_q87_annotation_v1.json"
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
    "6ca2f0602345bde2f836e50a9d1a6ba62e9fbaba0cf8f1bf3ed9291593182fad"
)
CANDIDATE_CONTENT_SHA256 = (
    "7f46226048820db9a9273d6f4fd439f5067ca1efcc2521360c65175b834d8a1e"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "b8a21757fa4234bb1f0169baf816061dd36a5a8c0480093a22356179e14fba86"
)
CANDIDATE_DENOMINATOR = 3346

FLOW_ROOT = "questionnaire-flow:root"
OCCURRENCE_KINDS = candidates.OCCURRENCE_KINDS
KIND_ORDER = {kind: index for index, kind in enumerate(OCCURRENCE_KINDS)}
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


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return source_tools.canonical_json_bytes(value)


def _digest(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _content_digest(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _digest(preimage)


def _expect_keys(
    value: Mapping[str, Any], expected: Sequence[str], label: str
) -> None:
    if set(value) != set(expected):
        raise ValueError(f"{label} key domain drift")


def _strict_load(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_bytes())
    except Exception as error:  # pragma: no cover - defensive
        raise ValueError(f"unreadable {label}") from error


def _identity(
    path: Path,
    schema_version: str,
    artifact_id: str,
    raw_sha256: str,
    content_sha256: str,
) -> dict[str, Any]:
    raw = path.read_bytes()
    if _sha256(raw) != raw_sha256:
        raise ValueError(f"{path.name} raw digest drift")
    return {
        "path": str(path.relative_to(ROOT)),
        "schema_version": schema_version,
        "artifact_id": artifact_id,
        "byte_size": len(raw),
        "raw_sha256": raw_sha256,
        "content_sha256": content_sha256,
    }


def _default_capture_root() -> Path:
    override = os.environ.get("PSID_DATA_ROOT")
    if override:
        return Path(override) / "documentation/capture1"
    return Path.home() / "PolicyEngine/psid-data/documentation/capture1"


def _load_replay_and_index() -> tuple[dict[str, Any], dict[str, Any]]:
    replay = _strict_load(REPLAY_PATH, "stage-1 source replay")
    index = _strict_load(INDEX_PATH, "stage-1 candidate index")
    if (
        _content_digest(replay) != REPLAY_CONTENT_SHA256
        or _content_digest(index) != INDEX_CONTENT_SHA256
    ):
        raise ValueError("stage-1 replay or index content digest drift")
    return replay, index


def _load_candidate(
    replay: Mapping[str, Any], index: Mapping[str, Any]
) -> dict[str, Any]:
    manifest = [
        row
        for row in index["document_candidate_manifest_rows"]
        if row["document_source_position"] == DOCUMENT_POSITION
    ]
    if len(manifest) != 1:
        raise ValueError("document-40 candidate manifest is not singular")
    row = manifest[0]
    if (
        row["source_document_id"] != DOCUMENT_ID
        or row["canonical_source_path"] != CANONICAL_SOURCE_PATH
        or row["interview_wave"] != INTERVIEW_WAVE
        or row["page_count"] != PAGE_COUNT
        or row["raw_sha256"] != CANDIDATE_RAW_SHA256
        or row["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or row["candidate_payload_sha256"] != CANDIDATE_PAYLOAD_SHA256
        or str(CANDIDATE_PATH.relative_to(ROOT)) != row["path"]
    ):
        raise ValueError("document-40 candidate manifest identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-40 candidates")
    if (
        _sha256(CANDIDATE_PATH.read_bytes()) != CANDIDATE_RAW_SHA256
        or _content_digest(candidate) != CANDIDATE_CONTENT_SHA256
        or candidate["document_source_position"] != DOCUMENT_POSITION
        or candidate["source_replay_identity"]["content_sha256"]
        != _content_digest(replay)
    ):
        raise ValueError("document-40 candidate artifact identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / "q87.pdf"
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("q87.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("q87.pdf page-count drift")
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
        raise ValueError("document-40 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-40 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-40 empty-text page domain drift")
    return rows


def _needle_span(
    page_text: str, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    starts: list[int] = []
    cursor = 0
    while True:
        found = page_text.find(needle, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    if occurrence < 0 or occurrence >= len(starts):
        raise ValueError(
            f"missing exact needle {needle!r} occurrence {occurrence}"
        )
    start_chars = starts[occurrence]
    end_chars = start_chars + len(needle)
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _resolve_span(page_text: str, spec: Mapping[str, Any]) -> tuple[int, int]:
    if "utf8_byte_start" in spec:
        return spec["utf8_byte_start"], spec["utf8_byte_end"]
    return _needle_span(
        page_text, spec["needle"], spec.get("needle_occurrence", 0)
    )


# ---------------------------------------------------------------------------
# Reviewer decisions.  Each row was selected during the complete 53-page pass
# and is re-resolved against the authenticated q87 page bytes below.
# ---------------------------------------------------------------------------

# (key, page, needle, needle_occurrence, parent_branch_key)
FLOW_SPECS: tuple[tuple[Any, ...], ...] = (
    ("b_section", 5, "SECTION B:   EMPLOYMENTOF HEAD", 0, None),
    (
        "b1_codes13",
        5,
        "[IF R MENTIONS CODES 1-3,     CHECK ONE AND ONLY ONE BOX, AND NONE"
        " FROM 4-8)",
        0,
        "b_section",
    ),
    ("b1_working_now", 5, "1. WORKINGNOW", 0, "b1_codes13"),
    (
        "b1_codes48",
        5,
        "[IF R MENTIONS ONLY CODES 4-8, CHECK AS MANY AS APPLY]",
        0,
        "b_section",
    ),
    ("b22_a_self", 7, "A. HEAD WORKSFOR SELF ONLY OR", 0, "b1_working_now"),
    ("b22_b_others", 7, "B. ALL OTHERS", 0, "b1_working_now"),
    ("b34_a_same", 8, "A.     SAME EMPLOYER", 0, "b1_working_now"),
    ("b34_b_self", 8, "B.     SELF-EMPLOYED", 0, "b1_working_now"),
    ("b34_c_diff", 8, "C.     DIFFERENT EMPLOYER", 0, "b1_working_now"),
    ("b67_first_extra", 10, "FIRST EXTRA JOB", 0, "b1_working_now"),
    ("b67_second_extra", 10, "SECONDEXTRA JOB", 0, "b1_working_now"),
    ("b84_first_extra", 10, "FIRST EXTRA JOB", 1, "b1_working_now"),
    ("b84_second_extra", 10, "SECONDEXTRA JOB", 1, "b1_working_now"),
    (
        "c_section",
        11,
        'SECTION C:    HEAD IS NOT WORKINGNOW ["NO" TO B3, (P. 6)]',
        0,
        None,
    ),
    ("c20_someone_else", 12, "1. SOMEONEELSE ONLY", 0, "c_section"),
    ("c20_both", 12, "2. BOTH SOMEONEELSE AND SELF", 0, "c_section"),
    ("c20_self", 12, "3. SELF ONLY", 0, "c_section"),
    ("c34_a_same", 14, "A.   SAME EMPLOYER", 0, "c_section"),
    ("c34_b_self", 14, "B.     SELF-EMPLOYED", 0, "c_section"),
    ("c34_c_diff", 14, "C.     DIFFERENT EMPLOYER", 0, "c_section"),
    ("c65_second_extra", 16, "SECONDEXTRA JOB", 0, "c_section"),
    ("c82_first_extra", 16, "FIRST EXTRA JOB", 0, "c_section"),
    ("c82_second_extra", 16, "SECONDEXTRA JOB", 1, "c_section"),
    ("d_section", 17, "SECTION D:      EMPLOYMENTOF WIFE/-WIFE”", 0, None),
    (
        "d1b_codes13",
        17,
        "[IF R MENTIONS CODES 1-3, CHECK,ONE AND ONLY ONE BOX, AND NONE"
        " FROM 4-8]",
        0,
        "d_section",
    ),
    ("d1b_working_now", 17, "1. WORKINGNOW", 0, "d1b_codes13"),
    (
        "d1b_codes48",
        17,
        "(IF R MENTIONS ONLY CODES 4-8, CHECK AS MANY AS APPLY]",
        0,
        "d_section",
    ),
    (
        "d20_a_self",
        19,
        'A. WIPE/"WIFE" WORKSFOR SELF ONLY l7R',
        0,
        "d1b_working_now",
    ),
    ("d20_b_others", 19, "B. ALL OTHERS", 0, "d1b_working_now"),
    ("d32_a_same", 20, "A.   SAME EMPLOYER", 0, "d1b_working_now"),
    ("d32_b_self", 20, "SELF-EMPLOYED", 0, "d1b_working_now"),
    ("d32_c_diff", 20, "DIFFERENT EMPLOYER", 0, "d1b_working_now"),
    ("d65_first_extra", 22, "FIRST EXTRA JOB", 0, "d1b_working_now"),
    ("d65_second_extra", 22, "SECONDEXTRA JOB", 0, "d1b_working_now"),
    (
        "e_section",
        23,
        'SECTION E:   WIFE/"WIFE"   IS NOT WORKINGNOW ["NO" TO D3, (P. 31)]',
        0,
        None,
    ),
    ("e18_both", 24, "2. BOTH SOMEONEELSE AND SELF", 0, "e_section"),
    ("e18_self", 24, "3. SELF ONLY", 0, "e_section"),
    ("e32_a_same", 26, "A.    SAME EMPLOYER", 0, "e_section"),
    ("e32_b_self", 26, "SELF-EMPLOYED", 0, "e_section"),
    ("e32_c_diff", 26, "DIFFERENT EMPLOYER", 0, "e_section"),
    ("e63_first_extra", 28, "FIRST EXTRA JOB", 0, "e_section"),
    ("e63_second_extra", 28, "SECONDEXTRA JOB", 0, "e_section"),
    ("e80_first_extra", 28, "FIRST EXTRA JOB", 1, "e_section"),
    ("e80_second_extra", 28, "SECONDEXTRA JOB", 1, "e_section"),
    ("g_section", 31, "SECTION G:     INCOME", 0, None),
    ("g1_farmer", 31, "HEAD IS A FARMER OR RANCHER", 0, "g_section"),
    ("g22_a_extra", 32, "A.    EXTRA JOB IN 1986", 0, "g_section"),
    (
        "g22_b_others",
        32,
        "B.    ALL OTHERS---W0         TO G25",
        0,
        "g_section",
    ),
    ("g49_a_wife", 33, 'A.     WIFE/"WIFE" IN FU NOW', 0, "g_section"),
    ("k_section", 48, "SECTION K:     BACKGROUND", 0, None),
    ("l_section", 51, "SECTION L:   BACKGROUND", 0, None),
)


NODE_DOMAIN_BY_CLASSIFICATION = {
    "head_or_reference_person": "role",
    "spouse_or_partner": "role",
    "source_job": "job_slot",
    "source_context": "component_slot",
    "source_remuneration_component": "component_slot",
    "farm_aggregate": "aggregate",
    "business_aggregate": "aggregate",
    "role_total": "aggregate",
}
KIND_BY_CLASSIFICATION = {
    "head_or_reference_person": "role_anchor",
    "spouse_or_partner": "role_anchor",
    "source_job": "job_anchor",
    "source_context": "context_anchor",
    "source_remuneration_component": "remuneration_component_anchor",
    "farm_aggregate": "farm_aggregate_anchor",
    "business_aggregate": "business_aggregate_anchor",
    "role_total": "role_total_anchor",
}

HEAD = "head_or_reference_person"
SPOUSE = "spouse_or_partner"
JOB = "source_job"
CTX = "source_context"
REM = "source_remuneration_component"
FARM = "farm_aggregate"
BUS = "business_aggregate"
TOTAL = "role_total"

# (key, page, needle, occurrence, classification, identifier, parents, paths)
ANCHOR_SPECS: tuple[tuple[Any, ...], ...] = (
    # ---------------- Section B: employment of head ----------------
    ("b1_head", 5, "HEAD", 2, HEAD, "B1.", (), ("b_section",)),
    (
        "b1_status_context",
        5,
        (328, 498),
        None,
        CTX,
        "B1.",
        ("b1_head",),
        ("b_section",),
    ),
    (
        "b4_main_job",
        5,
        "main job",
        0,
        JOB,
        "984.",
        ("b1_head",),
        ("b1_working_now",),
    ),
    (
        "b4_employee_context",
        5,
        "are you (HEAD) self-employed",
        0,
        CTX,
        "984.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b5_incorporation_context",
        5,
        "a corporation?",
        0,
        CTX,
        "B5.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b6_government_context",
        5,
        "local government, a private company, or what?",
        0,
        CTX,
        "B6.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b9_occupation_context",
        5,
        "What is your (HEAD'S) main occupation?",
        0,
        CTX,
        "B9.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b10_duties_context",
        5,
        "What are your most important   activities        or duties?",
        0,
        CTX,
        "B10.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b11_industry_context",
        5,
        "What kind of business   or industry     iS that     in?",
        0,
        CTX,
        "B11.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b12_pay_basis_context",
        6,
        "are you (HEAD) salaried,              paid by the hour,      or what?",
        0,
        CTX,
        "B12.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b13_salary_component",
        6,
        "salary?",
        0,
        REM,
        "B13.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b16_hourly_regular_component",
        6,
        "hourly wage rate",
        0,
        REM,
        "B16.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b17_hourly_overtime_component",
        6,
        "hourly wage rate",
        1,
        REM,
        "B17.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b15_extra_hours_component",
        6,
        "would you make",
        0,
        REM,
        "115.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b19_extra_hour_component",
        6,
        "earn for that hour?",
        0,
        REM,
        "B19.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b23_tenure_context",
        7,
        "How many years altogether      have you (HEAD) worked for your",
        0,
        CTX,
        "B23.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b24_start_context",
        7,
        "did you start working in your present (position/",
        0,
        CTX,
        "B24.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b26_starting_wage_component",
        7,
        "What was your starting      salary   or wage at that         time?",
        0,
        REM,
        "B26.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b27_hours_context",
        7,
        "And how many hours a week did you work?",
        0,
        CTX,
        "B27.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b29_previous_position_job",
        7,
        "another position    with the same employer",
        0,
        JOB,
        "8029.",
        ("b1_head",),
        ("b1_working_now",),
    ),
    (
        "b33_end_context",
        7,
        "In what month and year did that     (position/work  situation)    end?",
        0,
        CTX,
        "B33.",
        ("b29_previous_position_job",),
        ("b1_working_now",),
    ),
    (
        "b35_government_context",
        8,
        "government, a private  company, or what?",
        0,
        CTX,
        "B35.",
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b36_industry_context",
        8,
        "What kind of business        or industry     was that   in?",
        0,
        CTX,
        None,
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b37_occupation_context",
        8,
        "What was your (HEAD'S) occupation?",
        0,
        CTX,
        "B37.",
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b38_duties_context",
        8,
        "Whet were your most important               activities     or duties?",
        0,
        CTX,
        "B38.",
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b39_final_wage_component",
        8,
        "final               wage or salary",
        0,
        REM,
        "B39.",
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b40_hours_context",
        8,
        "And how many hours a week did you work?",
        0,
        CTX,
        "0840.",
        ("b29_previous_position_job",),
        ("b34_c_diff",),
    ),
    (
        "b41_start_context",
        8,
        "did you (HEAD) start working in that (position/work",
        0,
        CTX,
        "B41.",
        ("b29_previous_position_job",),
        ("b1_working_now",),
    ),
    (
        "b43_starting_wage_component",
        8,
        "Whet was your starting       salary       or wage at that       time?",
        0,
        REM,
        "B43.",
        ("b29_previous_position_job",),
        ("b1_working_now",),
    ),
    (
        "b44_hours_context",
        8,
        "And how many hours       a week did you work?",
        0,
        CTX,
        "El44.",
        ("b29_previous_position_job",),
        ("b1_working_now",),
    ),
    (
        "b63_weeks_context",
        9,
        "how many weeks did you actually   work on your main job(s) in",
        0,
        CTX,
        "B63.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b64_hours_context",
        9,
        "how many hours a week did you work on your main job(s)       in 1986?",
        0,
        CTX,
        "164.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b66_overtime_hours_context",
        9,
        "How many hours did that overtime amount to in 1986?",
        0,
        CTX,
        "B66.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b67_extra_job",
        10,
        "extra          job or other     way of making money",
        0,
        JOB,
        "B67.",
        ("b1_head",),
        ("b1_working_now",),
    ),
    (
        "b68_occupation_context",
        10,
        "whet sort of work",
        0,
        CTX,
        "B60.",
        ("b67_extra_job",),
        ("b67_first_extra", "b67_second_extra"),
    ),
    (
        "b70_extra_earnings_component",
        10,
        "About how much did you",
        0,
        REM,
        "B70.",
        ("b67_extra_job",),
        ("b67_first_extra", "b67_second_extra"),
    ),
    (
        "b71_weeks_context",
        10,
        "And, how many weeks did",
        0,
        CTX,
        "B71.",
        ("b67_extra_job",),
        ("b67_first_extra", "b67_second_extra"),
    ),
    (
        "b73_hours_context",
        10,
        "On the average, how",
        0,
        CTX,
        "B73.",
        ("b67_extra_job",),
        ("b67_first_extra", "b67_second_extra"),
    ),
    (
        "b81_weeks_1987_context",
        10,
        "How many weeks this   year have you (HEAD) actually              worked"
        " on your main job(s)?",
        0,
        CTX,
        "B81.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b83_hours_1987_context",
        10,
        "how many hours a reek have you worked on your main job(s)",
        0,
        CTX,
        "B83.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
    (
        "b84_extra_job_1987",
        10,
        "had an extra            job or other       way of making money",
        0,
        JOB,
        "B84.",
        ("b1_head",),
        ("b1_working_now",),
    ),
    (
        "b85_occupation_context",
        10,
        "What sort of work",
        0,
        CTX,
        "B65.",
        ("b84_extra_job_1987",),
        ("b84_first_extra", "b84_second_extra"),
    ),
    (
        "b87_weeks_context",
        10,
        "how many weeks",
        1,
        CTX,
        "B87.",
        ("b84_extra_job_1987",),
        ("b84_first_extra", "b84_second_extra"),
    ),
    (
        "b92_would_earn_component",
        11,
        "How much would you have earned",
        0,
        REM,
        "B92.",
        ("b4_main_job",),
        ("b1_working_now",),
    ),
)


ANCHOR_SPECS += (
    (
        "c9_head",
        12,
        "HEAD",
        0,
        HEAD,
        "c9.",
        (),
        ("c_section",),
    ),
    (
        "c9_ever_worked_context",
        12,
        "Have you (HEAD) ever done any work for money?",
        0,
        CTX,
        "c9.",
        ("c9_head",),
        ("c_section",),
    ),
    (
        "c17_last_job",
        12,
        "your occupation        on your last      job?",
        0,
        JOB,
        "C17.",
        ("c9_head",),
        ("c_section",),
    ),
    (
        "c18_duties_context",
        12,
        "What were your most important        activities       or duties?",
        0,
        CTX,
        "C18.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c19_industry_context",
        12,
        "what kind of business     or industry      was that       in?",
        0,
        CTX,
        "C19.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c20_employee_context",
        12,
        "Were you self-employed,        were you employed by someone else,                  or what?",
        0,
        CTX,
        "C20.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c21_government_context",
        12,
        "Did you work for    the federal,     state,    or local     government,          a private       company,",
        0,
        CTX,
        "C21.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c23_end_context",
        12,
        "In what month and year did that (position/work situation)",
        0,
        CTX,
        "C23.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c24_final_wage_component",
        13,
        "final              wage or salary",
        0,
        REM,
        "C24.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c25_hours_context",
        13,
        "And how many hours a week did you work?",
        0,
        CTX,
        "C25.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c26_start_context",
        13,
        "did you (HEAD) start working in that (position/work",
        0,
        CTX,
        "C26.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c28_starting_wage_component",
        13,
        "What was your starting           salary       or wage at that           time?",
        0,
        REM,
        "C28.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c29_hours_context",
        13,
        "And how many hours a week did you work?",
        1,
        CTX,
        "C29.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c30_previous_position_job",
        13,
        "another position          with the same employer",
        0,
        JOB,
        "C30.",
        ("c9_head",),
        ("c_section",),
    ),
    (
        "c33_end_context",
        13,
        "In what month and year did that       (position/work  situation)     end?",
        0,
        CTX,
        "C33.",
        ("c30_previous_position_job",),
        ("c_section",),
    ),
    (
        "c35_government_context",
        14,
        "government, a private  company, or what?",
        0,
        CTX,
        "C35.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c36_industry_context",
        14,
        "What kind of business           or industry    was that     in?",
        0,
        CTX,
        "C36.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c37_occupation_context",
        14,
        "What was your (HEAD'S) occupation?",
        0,
        CTX,
        "C37.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c38_duties_context",
        14,
        "What were your most important                    activities     or duties?",
        0,
        CTX,
        "C36.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c39_final_wage_component",
        14,
        "final                    wage or salary",
        0,
        REM,
        "C39.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c40_hours_context",
        14,
        "And how many hours a week did you work?",
        0,
        CTX,
        "C40.",
        ("c30_previous_position_job",),
        ("c34_c_diff",),
    ),
    (
        "c41_start_context",
        14,
        "did you (HEAD) start working in that (position/work",
        0,
        CTX,
        "C41.",
        ("c30_previous_position_job",),
        ("c_section",),
    ),
    (
        "c43_starting_wage_component",
        14,
        "What was your starting   salary   or wage at that       time?",
        0,
        REM,
        "C43.",
        ("c30_previous_position_job",),
        ("c_section",),
    ),
    (
        "c44_hours_context",
        14,
        "And how many hours a week did you work?",
        1,
        CTX,
        "C44.",
        ("c30_previous_position_job",),
        ("c_section",),
    ),
    (
        "c63_weeks_context",
        15,
        "how many weeks did you actually   work on your main job(s) in",
        0,
        CTX,
        "C63.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c64_hours_context",
        15,
        "how many hours a week   did you work on your main job(s)    in 1986?",
        0,
        CTX,
        "C64.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c65_extra_job",
        16,
        "have an extra job or other way of making money in addition to your main",
        0,
        JOB,
        "C65.",
        ("c9_head",),
        ("c_section",),
    ),
    (
        "c66_occupation_context",
        16,
        "What sort of work",
        0,
        CTX,
        "C66.",
        ("c65_extra_job",),
        ("c65_second_extra",),
    ),
    (
        "c68_extra_earnings_component",
        16,
        "About how much did you",
        0,
        REM,
        "C68.",
        ("c65_extra_job",),
        ("c65_second_extra",),
    ),
    (
        "c69_weeks_context",
        16,
        "And, how many weeks did",
        0,
        CTX,
        "C69.",
        ("c65_extra_job",),
        ("c65_second_extra",),
    ),
    (
        "c71_hours_context",
        16,
        "On the average, how",
        0,
        CTX,
        "C71.",
        ("c65_extra_job",),
        ("c65_second_extra",),
    ),
    (
        "c79_weeks_1987_context",
        16,
        "How many weeks this     year did you (HEAD) actually            work on your main job(s)?",
        0,
        CTX,
        "C79.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c81_hours_1987_context",
        16,
        "how many hours a week did you work on your main job(s)",
        0,
        CTX,
        "wxl.",
        ("c17_last_job",),
        ("c_section",),
    ),
    (
        "c82_extra_job_1987",
        16,
        "have an extra job or other way Of making money in addition to your main",
        0,
        JOB,
        "CBZ.",
        ("c9_head",),
        ("c_section",),
    ),
    (
        "c83_occupation_context",
        16,
        "What sort of work",
        1,
        CTX,
        "C83.",
        ("c82_extra_job_1987",),
        ("c82_first_extra", "c82_second_extra"),
    ),
    (
        "c85_weeks_context",
        16,
        "him many weeks",
        0,
        CTX,
        "C85.",
        ("c82_extra_job_1987",),
        ("c82_first_extra", "c82_second_extra"),
    ),
)


ANCHOR_SPECS += (
    (
        "d1b_spouse",
        17,
        'wife/"WIFE"',
        0,
        SPOUSE,
        "D1b.",
        (),
        ("d_section",),
    ),
    (
        "d1b_status_context",
        17,
        "does -- is she working          now,",
        0,
        CTX,
        "D1b.",
        ("d1b_spouse",),
        ("d_section",),
    ),
    (
        "d4_main_job",
        18,
        "her man job",
        0,
        JOB,
        "004.",
        ("d1b_spouse",),
        ("d1b_working_now",),
    ),
    (
        "d4_employee_context",
        18,
        'is your (wife/"WIFE")           self-employed,      is she employed by someone',
        0,
        CTX,
        "004.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d6_government_context",
        18,
        "state, or local government, a private   company,",
        0,
        CTX,
        "D&.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d9_occupation_context",
        18,
        "What is your (wife's/\"WIFE's\")         main occupation?",
        0,
        CTX,
        "D9.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d10_duties_context",
        18,
        "What are her most important      activities        or duties?",
        0,
        CTX,
        "D10.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d11_industry_context",
        18,
        "What kind of business    or industry      is that     in?",
        0,
        CTX,
        "D11.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d12_pay_basis_context",
        18,
        'is your (wife/"WIFE")          salaried,   paid by the hour,         or what?',
        0,
        CTX,
        "D12.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d13_salary_component",
        18,
        "How much is her",
        0,
        REM,
        "D13.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d16_hourly_regular_component",
        18,
        "hourly wage rate",
        0,
        REM,
        "D16.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d17_hourly_overtime_component",
        18,
        "hourly wage rate",
        1,
        REM,
        "D17.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d15_extra_hours_component",
        18,
        "would she make",
        0,
        REM,
        "D15.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d19_extra_hour_component",
        18,
        "earn for that hour?",
        0,
        REM,
        "D19.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d21_tenure_context",
        19,
        'How many years altogether         has your (wife/"WIFE")           worked for her',
        0,
        CTX,
        "D21.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d22_start_context",
        19,
        "did she start working in her present (position/",
        0,
        CTX,
        "D22.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d24_starting_wage_component",
        19,
        "What was her starting    salary     or wage at that          time?",
        0,
        REM,
        "D24.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d25_hours_context",
        19,
        "And how many hours a week did she work?",
        0,
        CTX,
        "D25.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d27_previous_position_job",
        19,
        "another position     with the same",
        0,
        JOB,
        "D27.",
        ("d1b_spouse",),
        ("d1b_working_now",),
    ),
    (
        "d31_end_context",
        19,
        "In what month and year did that        (position/work  situation)   end?",
        0,
        CTX,
        "D31.",
        ("d27_previous_position_job",),
        ("d1b_working_now",),
    ),
    (
        "d33_government_context",
        20,
        "local government, a private  company, or what?",
        0,
        CTX,
        None,
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d34_industry_context",
        20,
        "What kind of business          or industry   was that    in?",
        0,
        CTX,
        "D34.",
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d35_occupation_context",
        20,
        "What was your (wife's/\"WIFE's\")        occupation?",
        0,
        CTX,
        "D35.",
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d36_duties_context",
        20,
        "What were her most important      activities       or duties?",
        0,
        CTX,
        "D36.",
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d37_final_wage_component",
        20,
        "What was her final     wage or salary",
        0,
        REM,
        "D37.",
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d38_hours_context",
        20,
        "And how many hours a week did she work?",
        0,
        CTX,
        "D38.",
        ("d27_previous_position_job",),
        ("d32_c_diff",),
    ),
    (
        "d39_start_context",
        20,
        "start working in that (position/work",
        0,
        CTX,
        "D39.",
        ("d27_previous_position_job",),
        ("d1b_working_now",),
    ),
    (
        "d41_starting_wage_component",
        20,
        "What was her starting   salary   or wage at that     time?",
        0,
        REM,
        "D41.",
        ("d27_previous_position_job",),
        ("d1b_working_now",),
    ),
    (
        "d42_hours_context",
        20,
        "And how many hours a reek did she work?",
        0,
        CTX,
        "D42.",
        ("d27_previous_position_job",),
        ("d1b_working_now",),
    ),
    (
        "d61_weeks_context",
        21,
        "how many weeks did she actually     work on her main job(s)     in",
        0,
        CTX,
        "D61.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d62_hours_context",
        21,
        "how many hours a week did she work on her main job(s)         in 1986?",
        0,
        CTX,
        "0062.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d64_overtime_hours_context",
        21,
        "How many hours did that overtime    amount to in 1986?",
        0,
        CTX,
        "D64.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d65_extra_job",
        22,
        "have an extra     job or other           way of making money in addition        to",
        0,
        JOB,
        None,
        ("d1b_spouse",),
        ("d1b_working_now",),
    ),
    (
        "d66_occupation_context",
        22,
        "What sort of work",
        0,
        CTX,
        "D66.",
        ("d65_extra_job",),
        ("d65_first_extra", "d65_second_extra"),
    ),
    (
        "d68_extra_earnings_component",
        22,
        "About how much did she",
        0,
        REM,
        "D68.",
        ("d65_extra_job",),
        ("d65_first_extra", "d65_second_extra"),
    ),
    (
        "d69_weeks_context",
        22,
        "And, how many weeks did",
        0,
        CTX,
        "D69.",
        ("d65_extra_job",),
        ("d65_first_extra", "d65_second_extra"),
    ),
    (
        "d71_hours_context",
        22,
        "many hours a week did",
        0,
        CTX,
        "D71.",
        ("d65_extra_job",),
        ("d65_first_extra", "d65_second_extra"),
    ),
    (
        "d79_weeks_1987_context",
        22,
        "How many weeks this         year has she actually           worked on her main job(s)?",
        0,
        CTX,
        "D79.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d81_hours_1987_context",
        22,
        "how many hours a week has she worked on her main job(s)",
        0,
        CTX,
        "D81.",
        ("d4_main_job",),
        ("d1b_working_now",),
    ),
    (
        "d82_extra_job_1987",
        22,
        "had an extra                 job or other       way of making money in addition",
        0,
        JOB,
        "D82.",
        ("d1b_spouse",),
        ("d1b_working_now",),
    ),
    (
        "d83_occupation_context",
        22,
        "What sort of work",
        1,
        CTX,
        None,
        ("d82_extra_job_1987",),
        ("d1b_working_now",),
    ),
    (
        "d85_weeks_context",
        22,
        "how many weeks",
        1,
        CTX,
        "D85.",
        ("d82_extra_job_1987",),
        ("d1b_working_now",),
    ),
)


ANCHOR_SPECS += (
    (
        "e1_spouse",
        23,
        'wife/"WIFE"',
        0,
        SPOUSE,
        "E1.",
        (),
        ("e_section",),
    ),
    (
        "e7_ever_worked_context",
        24,
        'Has your (wife/"WIFE")               ever done any work for money?',
        0,
        CTX,
        "E7.",
        ("e1_spouse",),
        ("e_section",),
    ),
    (
        "e15_last_job",
        24,
        "her occupation             on her last         job?",
        0,
        JOB,
        "E15.",
        ("e1_spouse",),
        ("e_section",),
    ),
    (
        "e16_duties_context",
        24,
        "What were her most important               activities          or duties?",
        0,
        CTX,
        "E16.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e17_industry_context",
        24,
        "What kind of business             or industry     “as that        in?",
        0,
        CTX,
        "E17.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e18_employee_context",
        24,
        "Was she self-employed,    was she employed by someone else,         or what?",
        0,
        CTX,
        "E18.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e19_government_context",
        24,
        "Did she work far the federal,       state,   or local   government,       a private        company,",
        0,
        CTX,
        "E19.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e21_end_context",
        24,
        "In what month and year did that (position/work situation)             end?",
        0,
        CTX,
        "E21.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e22_final_wage_component",
        25,
        "final   wage or salary",
        0,
        REM,
        "E22.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e23_hours_context",
        25,
        "And how many hours a week did she work?",
        0,
        CTX,
        "E23.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e24_start_context",
        25,
        "In what month and year did she start working in that (position/work situation)?",
        0,
        CTX,
        "E24.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e26_starting_wage_component",
        25,
        "What was her starting     salary    or wage at that     time?",
        0,
        REM,
        "E26.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e27_hours_context",
        25,
        "And how many hours a week did she work?",
        1,
        CTX,
        "E27.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e28_previous_position_job",
        25,
        "another position   with the same employer",
        0,
        JOB,
        "E26.",
        ("e1_spouse",),
        ("e_section",),
    ),
    (
        "e31_end_context",
        25,
        "In what month and year did that       (position/work  situation)      end?",
        0,
        CTX,
        "E31.",
        ("e28_previous_position_job",),
        ("e_section",),
    ),
    (
        "e33_government_context",
        26,
        "local government, a private  company, or what?",
        0,
        CTX,
        "E33.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e34_industry_context",
        26,
        "What kind of business         or industry     was that     in?",
        0,
        CTX,
        "E34.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e35_occupation_context",
        26,
        'What was your (wife/"WIFE\'s")             occupation?',
        0,
        CTX,
        "E35.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e36_duties_context",
        26,
        "What were her most important             activities     or duties?",
        0,
        CTX,
        "E36.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e37_final_wage_component",
        26,
        "What was her final          wage or salary",
        0,
        REM,
        "E37.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e38_hours_context",
        26,
        "And how many hours a week did             she work?",
        0,
        CTX,
        "E38.",
        ("e28_previous_position_job",),
        ("e32_c_diff",),
    ),
    (
        "e39_start_context",
        26,
        'did your (wife/"WIFE") start working in that (position/work',
        0,
        CTX,
        "E39.",
        ("e28_previous_position_job",),
        ("e_section",),
    ),
    (
        "e41_starting_wage_component",
        26,
        "What was her starting   salary   or wage at that     time?",
        0,
        REM,
        "E41.",
        ("e28_previous_position_job",),
        ("e_section",),
    ),
    (
        "e42_hours_context",
        26,
        "And how many hours a week did she work?",
        0,
        CTX,
        "E42.",
        ("e28_previous_position_job",),
        ("e_section",),
    ),
    (
        "e61_weeks_context",
        27,
        "how many weeks did she actually  work on her main job(s) in",
        0,
        CTX,
        "E61.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e62_hours_context",
        27,
        "how many hours a week did she work on her main job(s)    in 1986?",
        0,
        CTX,
        "OF&?.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e63_extra_job",
        28,
        "have an extra job or other way of making money in addition",
        0,
        JOB,
        "E63.",
        ("e1_spouse",),
        ("e_section",),
    ),
    (
        "e64_occupation_context",
        28,
        "What sort of work",
        0,
        CTX,
        "E64.",
        ("e63_extra_job",),
        ("e63_first_extra", "e63_second_extra"),
    ),
    (
        "e66_extra_earnings_component",
        28,
        "Abut how much did she",
        0,
        REM,
        "E66.",
        ("e63_extra_job",),
        ("e63_first_extra", "e63_second_extra"),
    ),
    (
        "e67_weeks_context",
        28,
        "And, how many weeks",
        0,
        CTX,
        "E67.",
        ("e63_extra_job",),
        ("e63_first_extra", "e63_second_extra"),
    ),
    (
        "e69_hours_context",
        28,
        "many hours a week did",
        0,
        CTX,
        "E69.",
        ("e63_extra_job",),
        ("e63_first_extra", "e63_second_extra"),
    ),
    (
        "e77_weeks_1987_context",
        28,
        'How many weeks this      year did your (wife/"WIFE")            actually    work on her main job(s)?',
        0,
        CTX,
        "E77.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e79_hours_1987_context",
        28,
        "how many hours a week did she work on her main job(s)                     in 1987?",
        0,
        CTX,
        "E79.",
        ("e15_last_job",),
        ("e_section",),
    ),
    (
        "e80_extra_job_1987",
        28,
        "have an extra job or other way of making money in addition",
        1,
        JOB,
        "E80.",
        ("e1_spouse",),
        ("e_section",),
    ),
    (
        "e81_occupation_context",
        28,
        "What sort of work did",
        0,
        CTX,
        "E81.",
        ("e80_extra_job_1987",),
        ("e80_first_extra", "e80_second_extra"),
    ),
    (
        "e83_weeks_context",
        28,
        "how many weeks did",
        0,
        CTX,
        "BEB3.",
        ("e80_extra_job_1987",),
        ("e80_first_extra", "e80_second_extra"),
    ),
    (
        "g3_farm_aggregate",
        31,
        "farming",
        0,
        FARM,
        "G3.",
        (),
        ("g1_farmer",),
    ),
    (
        "g3_farm_receipts_component",
        31,
        "total receipts from farming in 1986",
        0,
        REM,
        "G3.",
        ("g3_farm_aggregate",),
        ("g1_farmer",),
    ),
    (
        "g4_operating_expenses_component",
        31,
        "total       operating   expenses",
        0,
        REM,
        "G4.",
        ("g3_farm_aggregate",),
        ("g1_farmer",),
    ),
    (
        "g5_net_farm_component",
        31,
        "net income from farming",
        0,
        REM,
        "G5.",
        ("g3_farm_aggregate",),
        ("g1_farmer",),
    ),
    (
        "g6_business_aggregate",
        31,
        "own a business",
        0,
        BUS,
        "G6.",
        (),
        ("g_section",),
    ),
    (
        "g7_business_kind_context",
        31,
        "What kind of business       was that?",
        0,
        CTX,
        "G7.",
        ("g6_business_aggregate",),
        ("g_section",),
    ),
    (
        "g9_work_time_context",
        31,
        "put in any work time for this business",
        0,
        CTX,
        "G9",
        ("g6_business_aggregate",),
        ("g_section",),
    ),
    (
        "g10_incorporation_context",
        31,
        "Was it a corporation    or an unincorporated",
        0,
        CTX,
        "G10.",
        ("g6_business_aggregate",),
        ("g_section",),
    ),
    (
        "g11_business_share_component",
        31,
        "income from the business",
        0,
        REM,
        "G11.",
        ("g6_business_aggregate",),
        ("g_section",),
    ),
    (
        "g12_head",
        31,
        "HEAD",
        0,
        HEAD,
        "GLZ.",
        (),
        ("g_section",),
    ),
    (
        "g12_role_total",
        31,
        'Did you (HEAD) ear" wages or salaries           in 1986 from any jobs?',
        0,
        TOTAL,
        "GLZ.",
        ("g12_head",),
        ("g_section",),
    ),
    (
        "g12_wages_component",
        31,
        "wages or salaries",
        0,
        REM,
        "GLZ.",
        ("g12_head",),
        ("g_section",),
    ),
    (
        "g14_bonus_component",
        31,
        "income from bonuses,",
        0,
        REM,
        "G14.",
        ("g12_head",),
        ("g_section",),
    ),
    (
        "g16_bonus_component",
        31,
        "bonuses, overtime,  tips, or",
        0,
        REM,
        "G16.",
        ("g12_head",),
        ("g_section",),
    ),
    (
        "g18a_professional_business",
        31,
        "professional practice or trade",
        0,
        BUS,
        "G18.",
        (),
        ("g_section",),
    ),
    (
        "g18b_farming_market",
        31,
        "farming or",
        0,
        FARM,
        "b.",
        (),
        ("g_section",),
    ),
    (
        "g18c_roomers_business",
        31,
        "roomers or",
        0,
        BUS,
        "c.",
        (),
        ("g_section",),
    ),
    (
        "g23_extra_earnings_context",
        32,
        "Have you included        your earnings       from the extra      job(s)",
        0,
        CTX,
        "G23.",
        ("g12_head",),
        ("g22_a_extra",),
    ),
    (
        "g24_extra_earnings_component",
        32,
        "How much did you earn from your extra jobs in 1986?",
        0,
        REM,
        "G24.",
        ("g12_head",),
        ("g22_a_extra",),
    ),
    (
        "g50_spouse",
        33,
        'wife/"WIFE"',
        0,
        SPOUSE,
        "G50.",
        (),
        ("g49_a_wife",),
    ),
    (
        "g51_wife_earnings_context",
        33,
        "Was any of it        earnings      from her work?",
        0,
        CTX,
        "G51.",
        ("g50_spouse",),
        ("g49_a_wife",),
    ),
    (
        "g52_wife_earnings_component",
        33,
        'How much did she ear" altogether              from work in 1986',
        0,
        REM,
        "G52.",
        ("g50_spouse",),
        ("g49_a_wife",),
    ),
    (
        "k44_spouse",
        50,
        'wife/"WIFE"',
        0,
        SPOUSE,
        "K44.",
        (),
        ("k_section",),
    ),
    (
        "k44_lifetime_work_context",
        50,
        'How many years altogether            has your (wife/"WIFE")       worked for money since she was 18?',
        0,
        CTX,
        "K44.",
        ("k44_spouse",),
        ("k_section",),
    ),
    (
        "k45_fulltime_years_context",
        50,
        "How many of these years did she work full-time",
        0,
        CTX,
        "~45.",
        ("k44_spouse",),
        ("k_section",),
    ),
    (
        "l5_first_job",
        51,
        "first      full-time     regular    job",
        0,
        JOB,
        "L5.",
        (),
        ("l_section",),
    ),
    (
        "l6_occupation_context",
        51,
        "same occupation you started in, or what?",
        0,
        CTX,
        "L6.",
        ("l5_first_job",),
        ("l_section",),
    ),
    (
        "l57_head",
        53,
        "READ",
        2,
        HEAD,
        "L57.",
        (),
        ("l_section",),
    ),
    (
        "l57_lifetime_work_context",
        53,
        "years altogether     have you (READ) worked for money since you were 18?",
        0,
        CTX,
        "L57.",
        ("l57_head",),
        ("l_section",),
    ),
    (
        "l58_fulltime_years_context",
        53,
        "How many of these years did you work full-time",
        0,
        CTX,
        None,
        ("l57_head",),
        ("l_section",),
    ),
)


# (anchor_key, field_purposes, applicable_anchor_keys); the prompt occurrence
# is the same exact printed span, emitted under the prompt kind.
PROMPT_SPECS: tuple[tuple[Any, ...], ...] = (
    (
        "b1_status_context",
        ("interview_and_role_attachment",),
        ("b1_status_context", "b1_head"),
    ),
    ("b4_main_job", ("job_identifier",), ("b4_main_job", "b1_head")),
    (
        "b4_employee_context",
        ("employee_self_or_mixed",),
        ("b4_employee_context", "b4_main_job"),
    ),
    (
        "b5_incorporation_context",
        ("incorporation",),
        ("b5_incorporation_context", "b4_main_job"),
    ),
    (
        "b6_government_context",
        ("government_level",),
        ("b6_government_context", "b4_main_job"),
    ),
    (
        "b9_occupation_context",
        ("occupation",),
        ("b9_occupation_context", "b4_main_job"),
    ),
    (
        "b10_duties_context",
        ("occupation",),
        ("b10_duties_context", "b4_main_job"),
    ),
    (
        "b11_industry_context",
        ("industry",),
        ("b11_industry_context", "b4_main_job"),
    ),
    (
        "b12_pay_basis_context",
        ("reporting_unit",),
        ("b12_pay_basis_context", "b4_main_job"),
    ),
    (
        "b13_salary_component",
        ("amount", "reporting_unit"),
        ("b13_salary_component", "b4_main_job"),
    ),
    (
        "b16_hourly_regular_component",
        ("amount", "reporting_unit"),
        ("b16_hourly_regular_component", "b4_main_job"),
    ),
    (
        "b17_hourly_overtime_component",
        ("amount", "reporting_unit"),
        ("b17_hourly_overtime_component", "b4_main_job"),
    ),
    (
        "b15_extra_hours_component",
        ("amount", "reporting_unit"),
        ("b15_extra_hours_component", "b4_main_job"),
    ),
    (
        "b19_extra_hour_component",
        ("amount", "reporting_unit"),
        ("b19_extra_hour_component", "b4_main_job"),
    ),
    (
        "b23_tenure_context",
        ("month_or_exposure",),
        ("b23_tenure_context", "b4_main_job"),
    ),
    (
        "b24_start_context",
        ("month_or_exposure",),
        ("b24_start_context", "b4_main_job"),
    ),
    (
        "b26_starting_wage_component",
        ("amount", "reporting_unit"),
        ("b26_starting_wage_component", "b4_main_job"),
    ),
    (
        "b27_hours_context",
        ("month_or_exposure",),
        ("b27_hours_context", "b4_main_job"),
    ),
    (
        "b29_previous_position_job",
        ("job_identifier",),
        ("b29_previous_position_job", "b1_head"),
    ),
    (
        "b33_end_context",
        ("month_or_exposure",),
        ("b33_end_context", "b29_previous_position_job"),
    ),
    (
        "b35_government_context",
        ("government_level",),
        ("b35_government_context", "b29_previous_position_job"),
    ),
    (
        "b36_industry_context",
        ("industry",),
        ("b36_industry_context", "b29_previous_position_job"),
    ),
    (
        "b37_occupation_context",
        ("occupation",),
        ("b37_occupation_context", "b29_previous_position_job"),
    ),
    (
        "b38_duties_context",
        ("occupation",),
        ("b38_duties_context", "b29_previous_position_job"),
    ),
    (
        "b39_final_wage_component",
        ("amount", "reporting_unit"),
        ("b39_final_wage_component", "b29_previous_position_job"),
    ),
    (
        "b40_hours_context",
        ("month_or_exposure",),
        ("b40_hours_context", "b29_previous_position_job"),
    ),
    (
        "b41_start_context",
        ("month_or_exposure",),
        ("b41_start_context", "b29_previous_position_job"),
    ),
    (
        "b43_starting_wage_component",
        ("amount", "reporting_unit"),
        ("b43_starting_wage_component", "b29_previous_position_job"),
    ),
    (
        "b44_hours_context",
        ("month_or_exposure",),
        ("b44_hours_context", "b29_previous_position_job"),
    ),
    (
        "b63_weeks_context",
        ("month_or_exposure",),
        ("b63_weeks_context", "b4_main_job"),
    ),
    (
        "b64_hours_context",
        ("month_or_exposure",),
        ("b64_hours_context", "b4_main_job"),
    ),
    (
        "b66_overtime_hours_context",
        ("month_or_exposure",),
        ("b66_overtime_hours_context", "b4_main_job"),
    ),
    ("b67_extra_job", ("job_identifier",), ("b67_extra_job", "b1_head")),
    (
        "b68_occupation_context",
        ("occupation",),
        ("b68_occupation_context", "b67_extra_job"),
    ),
    (
        "b70_extra_earnings_component",
        ("amount", "reporting_unit"),
        ("b70_extra_earnings_component", "b67_extra_job"),
    ),
    (
        "b71_weeks_context",
        ("month_or_exposure",),
        ("b71_weeks_context", "b67_extra_job"),
    ),
    (
        "b73_hours_context",
        ("month_or_exposure",),
        ("b73_hours_context", "b67_extra_job"),
    ),
    (
        "b81_weeks_1987_context",
        ("month_or_exposure",),
        ("b81_weeks_1987_context", "b4_main_job"),
    ),
    (
        "b83_hours_1987_context",
        ("month_or_exposure",),
        ("b83_hours_1987_context", "b4_main_job"),
    ),
    (
        "b84_extra_job_1987",
        ("job_identifier",),
        ("b84_extra_job_1987", "b1_head"),
    ),
    (
        "b85_occupation_context",
        ("occupation",),
        ("b85_occupation_context", "b84_extra_job_1987"),
    ),
    (
        "b87_weeks_context",
        ("month_or_exposure",),
        ("b87_weeks_context", "b84_extra_job_1987"),
    ),
    (
        "b92_would_earn_component",
        ("amount", "reporting_unit"),
        ("b92_would_earn_component", "b4_main_job"),
    ),
    (
        "c9_ever_worked_context",
        ("interview_and_role_attachment",),
        ("c9_ever_worked_context", "c9_head"),
    ),
    ("c17_last_job", ("job_identifier",), ("c17_last_job", "c9_head")),
    (
        "c18_duties_context",
        ("occupation",),
        ("c18_duties_context", "c17_last_job"),
    ),
    (
        "c19_industry_context",
        ("industry",),
        ("c19_industry_context", "c17_last_job"),
    ),
    (
        "c20_employee_context",
        ("employee_self_or_mixed",),
        ("c20_employee_context", "c17_last_job"),
    ),
    (
        "c21_government_context",
        ("government_level",),
        ("c21_government_context", "c17_last_job"),
    ),
    (
        "c23_end_context",
        ("month_or_exposure",),
        ("c23_end_context", "c17_last_job"),
    ),
    (
        "c24_final_wage_component",
        ("amount", "reporting_unit"),
        ("c24_final_wage_component", "c17_last_job"),
    ),
    (
        "c25_hours_context",
        ("month_or_exposure",),
        ("c25_hours_context", "c17_last_job"),
    ),
    (
        "c26_start_context",
        ("month_or_exposure",),
        ("c26_start_context", "c17_last_job"),
    ),
    (
        "c28_starting_wage_component",
        ("amount", "reporting_unit"),
        ("c28_starting_wage_component", "c17_last_job"),
    ),
    (
        "c29_hours_context",
        ("month_or_exposure",),
        ("c29_hours_context", "c17_last_job"),
    ),
    (
        "c30_previous_position_job",
        ("job_identifier",),
        ("c30_previous_position_job", "c9_head"),
    ),
    (
        "c33_end_context",
        ("month_or_exposure",),
        ("c33_end_context", "c30_previous_position_job"),
    ),
    (
        "c35_government_context",
        ("government_level",),
        ("c35_government_context", "c30_previous_position_job"),
    ),
    (
        "c36_industry_context",
        ("industry",),
        ("c36_industry_context", "c30_previous_position_job"),
    ),
    (
        "c37_occupation_context",
        ("occupation",),
        ("c37_occupation_context", "c30_previous_position_job"),
    ),
    (
        "c38_duties_context",
        ("occupation",),
        ("c38_duties_context", "c30_previous_position_job"),
    ),
    (
        "c39_final_wage_component",
        ("amount", "reporting_unit"),
        ("c39_final_wage_component", "c30_previous_position_job"),
    ),
    (
        "c40_hours_context",
        ("month_or_exposure",),
        ("c40_hours_context", "c30_previous_position_job"),
    ),
    (
        "c41_start_context",
        ("month_or_exposure",),
        ("c41_start_context", "c30_previous_position_job"),
    ),
    (
        "c43_starting_wage_component",
        ("amount", "reporting_unit"),
        ("c43_starting_wage_component", "c30_previous_position_job"),
    ),
    (
        "c44_hours_context",
        ("month_or_exposure",),
        ("c44_hours_context", "c30_previous_position_job"),
    ),
    (
        "c63_weeks_context",
        ("month_or_exposure",),
        ("c63_weeks_context", "c17_last_job"),
    ),
    (
        "c64_hours_context",
        ("month_or_exposure",),
        ("c64_hours_context", "c17_last_job"),
    ),
    ("c65_extra_job", ("job_identifier",), ("c65_extra_job", "c9_head")),
    (
        "c66_occupation_context",
        ("occupation",),
        ("c66_occupation_context", "c65_extra_job"),
    ),
    (
        "c68_extra_earnings_component",
        ("amount", "reporting_unit"),
        ("c68_extra_earnings_component", "c65_extra_job"),
    ),
    (
        "c69_weeks_context",
        ("month_or_exposure",),
        ("c69_weeks_context", "c65_extra_job"),
    ),
    (
        "c71_hours_context",
        ("month_or_exposure",),
        ("c71_hours_context", "c65_extra_job"),
    ),
    (
        "c79_weeks_1987_context",
        ("month_or_exposure",),
        ("c79_weeks_1987_context", "c17_last_job"),
    ),
    (
        "c81_hours_1987_context",
        ("month_or_exposure",),
        ("c81_hours_1987_context", "c17_last_job"),
    ),
    (
        "c82_extra_job_1987",
        ("job_identifier",),
        ("c82_extra_job_1987", "c9_head"),
    ),
    (
        "c83_occupation_context",
        ("occupation",),
        ("c83_occupation_context", "c82_extra_job_1987"),
    ),
    (
        "c85_weeks_context",
        ("month_or_exposure",),
        ("c85_weeks_context", "c82_extra_job_1987"),
    ),
    (
        "d1b_status_context",
        ("interview_and_role_attachment",),
        ("d1b_status_context", "d1b_spouse"),
    ),
    ("d4_main_job", ("job_identifier",), ("d4_main_job", "d1b_spouse")),
    (
        "d4_employee_context",
        ("employee_self_or_mixed",),
        ("d4_employee_context", "d4_main_job"),
    ),
    (
        "d6_government_context",
        ("government_level",),
        ("d6_government_context", "d4_main_job"),
    ),
    (
        "d9_occupation_context",
        ("occupation",),
        ("d9_occupation_context", "d4_main_job"),
    ),
    (
        "d10_duties_context",
        ("occupation",),
        ("d10_duties_context", "d4_main_job"),
    ),
    (
        "d11_industry_context",
        ("industry",),
        ("d11_industry_context", "d4_main_job"),
    ),
    (
        "d12_pay_basis_context",
        ("reporting_unit",),
        ("d12_pay_basis_context", "d4_main_job"),
    ),
    (
        "d13_salary_component",
        ("amount", "reporting_unit"),
        ("d13_salary_component", "d4_main_job"),
    ),
    (
        "d16_hourly_regular_component",
        ("amount", "reporting_unit"),
        ("d16_hourly_regular_component", "d4_main_job"),
    ),
    (
        "d17_hourly_overtime_component",
        ("amount", "reporting_unit"),
        ("d17_hourly_overtime_component", "d4_main_job"),
    ),
    (
        "d15_extra_hours_component",
        ("amount", "reporting_unit"),
        ("d15_extra_hours_component", "d4_main_job"),
    ),
    (
        "d19_extra_hour_component",
        ("amount", "reporting_unit"),
        ("d19_extra_hour_component", "d4_main_job"),
    ),
    (
        "d21_tenure_context",
        ("month_or_exposure",),
        ("d21_tenure_context", "d4_main_job"),
    ),
    (
        "d22_start_context",
        ("month_or_exposure",),
        ("d22_start_context", "d4_main_job"),
    ),
    (
        "d24_starting_wage_component",
        ("amount", "reporting_unit"),
        ("d24_starting_wage_component", "d4_main_job"),
    ),
    (
        "d25_hours_context",
        ("month_or_exposure",),
        ("d25_hours_context", "d4_main_job"),
    ),
    (
        "d27_previous_position_job",
        ("job_identifier",),
        ("d27_previous_position_job", "d1b_spouse"),
    ),
    (
        "d31_end_context",
        ("month_or_exposure",),
        ("d31_end_context", "d27_previous_position_job"),
    ),
    (
        "d33_government_context",
        ("government_level",),
        ("d33_government_context", "d27_previous_position_job"),
    ),
    (
        "d34_industry_context",
        ("industry",),
        ("d34_industry_context", "d27_previous_position_job"),
    ),
    (
        "d35_occupation_context",
        ("occupation",),
        ("d35_occupation_context", "d27_previous_position_job"),
    ),
    (
        "d36_duties_context",
        ("occupation",),
        ("d36_duties_context", "d27_previous_position_job"),
    ),
    (
        "d37_final_wage_component",
        ("amount", "reporting_unit"),
        ("d37_final_wage_component", "d27_previous_position_job"),
    ),
    (
        "d38_hours_context",
        ("month_or_exposure",),
        ("d38_hours_context", "d27_previous_position_job"),
    ),
    (
        "d39_start_context",
        ("month_or_exposure",),
        ("d39_start_context", "d27_previous_position_job"),
    ),
    (
        "d41_starting_wage_component",
        ("amount", "reporting_unit"),
        ("d41_starting_wage_component", "d27_previous_position_job"),
    ),
    (
        "d42_hours_context",
        ("month_or_exposure",),
        ("d42_hours_context", "d27_previous_position_job"),
    ),
    (
        "d61_weeks_context",
        ("month_or_exposure",),
        ("d61_weeks_context", "d4_main_job"),
    ),
    (
        "d62_hours_context",
        ("month_or_exposure",),
        ("d62_hours_context", "d4_main_job"),
    ),
    (
        "d64_overtime_hours_context",
        ("month_or_exposure",),
        ("d64_overtime_hours_context", "d4_main_job"),
    ),
    ("d65_extra_job", ("job_identifier",), ("d65_extra_job", "d1b_spouse")),
    (
        "d66_occupation_context",
        ("occupation",),
        ("d66_occupation_context", "d65_extra_job"),
    ),
    (
        "d68_extra_earnings_component",
        ("amount", "reporting_unit"),
        ("d68_extra_earnings_component", "d65_extra_job"),
    ),
    (
        "d69_weeks_context",
        ("month_or_exposure",),
        ("d69_weeks_context", "d65_extra_job"),
    ),
    (
        "d71_hours_context",
        ("month_or_exposure",),
        ("d71_hours_context", "d65_extra_job"),
    ),
    (
        "d79_weeks_1987_context",
        ("month_or_exposure",),
        ("d79_weeks_1987_context", "d4_main_job"),
    ),
    (
        "d81_hours_1987_context",
        ("month_or_exposure",),
        ("d81_hours_1987_context", "d4_main_job"),
    ),
    (
        "d82_extra_job_1987",
        ("job_identifier",),
        ("d82_extra_job_1987", "d1b_spouse"),
    ),
    (
        "d83_occupation_context",
        ("occupation",),
        ("d83_occupation_context", "d82_extra_job_1987"),
    ),
    (
        "d85_weeks_context",
        ("month_or_exposure",),
        ("d85_weeks_context", "d82_extra_job_1987"),
    ),
    (
        "e7_ever_worked_context",
        ("interview_and_role_attachment",),
        ("e7_ever_worked_context", "e1_spouse"),
    ),
    ("e15_last_job", ("job_identifier",), ("e15_last_job", "e1_spouse")),
    (
        "e16_duties_context",
        ("occupation",),
        ("e16_duties_context", "e15_last_job"),
    ),
    (
        "e17_industry_context",
        ("industry",),
        ("e17_industry_context", "e15_last_job"),
    ),
    (
        "e18_employee_context",
        ("employee_self_or_mixed",),
        ("e18_employee_context", "e15_last_job"),
    ),
    (
        "e19_government_context",
        ("government_level",),
        ("e19_government_context", "e15_last_job"),
    ),
    (
        "e21_end_context",
        ("month_or_exposure",),
        ("e21_end_context", "e15_last_job"),
    ),
    (
        "e22_final_wage_component",
        ("amount", "reporting_unit"),
        ("e22_final_wage_component", "e15_last_job"),
    ),
    (
        "e23_hours_context",
        ("month_or_exposure",),
        ("e23_hours_context", "e15_last_job"),
    ),
    (
        "e24_start_context",
        ("month_or_exposure",),
        ("e24_start_context", "e15_last_job"),
    ),
    (
        "e26_starting_wage_component",
        ("amount", "reporting_unit"),
        ("e26_starting_wage_component", "e15_last_job"),
    ),
    (
        "e27_hours_context",
        ("month_or_exposure",),
        ("e27_hours_context", "e15_last_job"),
    ),
    (
        "e28_previous_position_job",
        ("job_identifier",),
        ("e28_previous_position_job", "e1_spouse"),
    ),
    (
        "e31_end_context",
        ("month_or_exposure",),
        ("e31_end_context", "e28_previous_position_job"),
    ),
    (
        "e33_government_context",
        ("government_level",),
        ("e33_government_context", "e28_previous_position_job"),
    ),
    (
        "e34_industry_context",
        ("industry",),
        ("e34_industry_context", "e28_previous_position_job"),
    ),
    (
        "e35_occupation_context",
        ("occupation",),
        ("e35_occupation_context", "e28_previous_position_job"),
    ),
    (
        "e36_duties_context",
        ("occupation",),
        ("e36_duties_context", "e28_previous_position_job"),
    ),
    (
        "e37_final_wage_component",
        ("amount", "reporting_unit"),
        ("e37_final_wage_component", "e28_previous_position_job"),
    ),
    (
        "e38_hours_context",
        ("month_or_exposure",),
        ("e38_hours_context", "e28_previous_position_job"),
    ),
    (
        "e39_start_context",
        ("month_or_exposure",),
        ("e39_start_context", "e28_previous_position_job"),
    ),
    (
        "e41_starting_wage_component",
        ("amount", "reporting_unit"),
        ("e41_starting_wage_component", "e28_previous_position_job"),
    ),
    (
        "e42_hours_context",
        ("month_or_exposure",),
        ("e42_hours_context", "e28_previous_position_job"),
    ),
    (
        "e61_weeks_context",
        ("month_or_exposure",),
        ("e61_weeks_context", "e15_last_job"),
    ),
    (
        "e62_hours_context",
        ("month_or_exposure",),
        ("e62_hours_context", "e15_last_job"),
    ),
    ("e63_extra_job", ("job_identifier",), ("e63_extra_job", "e1_spouse")),
    (
        "e64_occupation_context",
        ("occupation",),
        ("e64_occupation_context", "e63_extra_job"),
    ),
    (
        "e66_extra_earnings_component",
        ("amount", "reporting_unit"),
        ("e66_extra_earnings_component", "e63_extra_job"),
    ),
    (
        "e67_weeks_context",
        ("month_or_exposure",),
        ("e67_weeks_context", "e63_extra_job"),
    ),
    (
        "e69_hours_context",
        ("month_or_exposure",),
        ("e69_hours_context", "e63_extra_job"),
    ),
    (
        "e77_weeks_1987_context",
        ("month_or_exposure",),
        ("e77_weeks_1987_context", "e15_last_job"),
    ),
    (
        "e79_hours_1987_context",
        ("month_or_exposure",),
        ("e79_hours_1987_context", "e15_last_job"),
    ),
    (
        "e80_extra_job_1987",
        ("job_identifier",),
        ("e80_extra_job_1987", "e1_spouse"),
    ),
    (
        "e81_occupation_context",
        ("occupation",),
        ("e81_occupation_context", "e80_extra_job_1987"),
    ),
    (
        "e83_weeks_context",
        ("month_or_exposure",),
        ("e83_weeks_context", "e80_extra_job_1987"),
    ),
    (
        "g3_farm_receipts_component",
        ("amount", "reporting_unit"),
        ("g3_farm_receipts_component", "g3_farm_aggregate"),
    ),
    (
        "g4_operating_expenses_component",
        ("amount", "reporting_unit"),
        ("g4_operating_expenses_component", "g3_farm_aggregate"),
    ),
    (
        "g5_net_farm_component",
        ("amount", "reporting_unit"),
        ("g5_net_farm_component", "g3_farm_aggregate"),
    ),
    (
        "g7_business_kind_context",
        ("industry",),
        ("g7_business_kind_context", "g6_business_aggregate"),
    ),
    (
        "g9_work_time_context",
        ("month_or_exposure",),
        ("g9_work_time_context", "g6_business_aggregate"),
    ),
    (
        "g10_incorporation_context",
        ("incorporation",),
        ("g10_incorporation_context", "g6_business_aggregate"),
    ),
    (
        "g11_business_share_component",
        ("amount", "reporting_unit"),
        ("g11_business_share_component", "g6_business_aggregate"),
    ),
    ("g12_role_total", ("amount",), ("g12_role_total", "g12_head")),
    (
        "g14_bonus_component",
        ("amount", "reporting_unit"),
        ("g14_bonus_component", "g12_head"),
    ),
    (
        "g16_bonus_component",
        ("amount", "reporting_unit"),
        ("g16_bonus_component", "g12_head"),
    ),
    (
        "g23_extra_earnings_context",
        ("amount",),
        ("g23_extra_earnings_context", "g12_head"),
    ),
    (
        "g24_extra_earnings_component",
        ("amount", "reporting_unit"),
        ("g24_extra_earnings_component", "g12_head"),
    ),
    (
        "g51_wife_earnings_context",
        ("month_or_exposure",),
        ("g51_wife_earnings_context", "g50_spouse"),
    ),
    (
        "g52_wife_earnings_component",
        ("amount", "reporting_unit"),
        ("g52_wife_earnings_component", "g50_spouse"),
    ),
    (
        "k44_lifetime_work_context",
        ("month_or_exposure",),
        ("k44_lifetime_work_context", "k44_spouse"),
    ),
    (
        "k45_fulltime_years_context",
        ("month_or_exposure",),
        ("k45_fulltime_years_context", "k44_spouse"),
    ),
    ("l5_first_job", ("job_identifier",), ("l5_first_job",)),
    (
        "l6_occupation_context",
        ("occupation",),
        ("l6_occupation_context", "l5_first_job"),
    ),
    (
        "l57_lifetime_work_context",
        ("month_or_exposure",),
        ("l57_lifetime_work_context", "l57_head"),
    ),
    (
        "l58_fulltime_years_context",
        ("month_or_exposure",),
        ("l58_fulltime_years_context", "l57_head"),
    ),
)


# (key, page, needle, occurrence, relation, target_needle, target_occurrence,
#  handoff_status, paths)
REPEAT_SPECS: tuple[tuple[Any, ...], ...] = (
    (
        "b22_checkpoint_xref",
        7,
        "SEE B4, (P. 7)--WHETHER SELF-EMPLOYED",
        0,
        "explicit_cross_reference",
        "B4, (P. 7)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("b1_working_now",),
    ),
    (
        "b34_checkpoint_xref",
        8,
        "SEE B29 @j B31, (P.11l)--PREVIOUS",
        0,
        "explicit_cross_reference",
        "B29 @j B31, (P.11l)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("b1_working_now",),
    ),
    (
        "b74_repeat_first",
        10,
        "ASK B68-",
        0,
        "explicit_repeat_instruction",
        "B68-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("b67_first_extra",),
    ),
    (
        "b74_repeat_second",
        10,
        "ASK B68-",
        1,
        "explicit_repeat_instruction",
        "B68-",
        1,
        "local_target_outside_rq_annotation_domain",
        ("b67_second_extra",),
    ),
    (
        "c34_checkpoint_xref",
        14,
        "SEE C30 or C32, (P. 23)--PREVIOUS POSITION",
        0,
        "explicit_cross_reference",
        "C30 or C32, (P. 23)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("c_section",),
    ),
    (
        "c72_repeat_first",
        16,
        "ASK C66-",
        0,
        "explicit_repeat_instruction",
        "C66-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("c65_second_extra",),
    ),
    (
        "c72_repeat_second",
        16,
        "ASK C66-",
        1,
        "explicit_repeat_instruction",
        "C66-",
        1,
        "local_target_outside_rq_annotation_domain",
        ("c65_second_extra",),
    ),
    (
        "c88_repeat",
        16,
        "ASK C83",
        0,
        "explicit_repeat_instruction",
        "C83",
        0,
        "local_target_outside_rq_annotation_domain",
        ("c82_first_extra",),
    ),
    (
        "d20_checkpoint_xref",
        19,
        "SEE D4, (P. 32)--WHETHER SELF-EMPLOYED",
        0,
        "explicit_cross_reference",
        "D4, (P. 32)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("d1b_working_now",),
    ),
    (
        "d32_checkpoint_xref",
        20,
        "SEE D27 m D29, (P. 35)--PREVIOUS POSITION",
        0,
        "explicit_cross_reference",
        "D27 m D29, (P. 35)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("d1b_working_now",),
    ),
    (
        "d72_repeat_first",
        22,
        "ASK D66-",
        0,
        "explicit_repeat_instruction",
        "D66-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("d65_first_extra",),
    ),
    (
        "d72_repeat_second",
        22,
        "ASK D66-",
        1,
        "explicit_repeat_instruction",
        "D66-",
        1,
        "local_target_outside_rq_annotation_domain",
        ("d65_second_extra",),
    ),
    (
        "d88_repeat",
        22,
        "ASK DB3-",
        0,
        "explicit_repeat_instruction",
        "DB3-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("d1b_working_now",),
    ),
    (
        "e32_checkpoint_xref",
        26,
        "SEE E28 OR E30, (P. 47)--PREVIOUS",
        0,
        "explicit_cross_reference",
        "E28 OR E30, (P. 47)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("e_section",),
    ),
    (
        "e70_repeat_first",
        28,
        "ASK E64-",
        0,
        "explicit_repeat_instruction",
        "E64-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("e63_first_extra",),
    ),
    (
        "e70_repeat_second",
        28,
        "ASK E64-",
        1,
        "explicit_repeat_instruction",
        "E64-",
        1,
        "local_target_outside_rq_annotation_domain",
        ("e63_second_extra",),
    ),
    (
        "e86_repeat_first",
        28,
        "ASK E81-",
        0,
        "explicit_repeat_instruction",
        "E81-",
        0,
        "local_target_outside_rq_annotation_domain",
        ("e80_first_extra",),
    ),
    (
        "e86_repeat_second",
        28,
        "ASK E81-",
        1,
        "explicit_repeat_instruction",
        "E81-",
        1,
        "local_target_outside_rq_annotation_domain",
        ("e80_second_extra",),
    ),
    (
        "g9_workhours_xref",
        31,
        "MUST BE REPORTED!",
        0,
        "explicit_cross_reference",
        "MUST BE REPORTED!",
        0,
        "local_target_outside_rq_annotation_domain",
        ("g_section",),
    ),
    (
        "g18c_workhours_xref",
        31,
        "SECTION B OR C.",
        0,
        "explicit_cross_reference",
        "SECTION B OR C.",
        0,
        "local_target_outside_rq_annotation_domain",
        ("g_section",),
    ),
    (
        "g22_checkpoint_xref",
        32,
        "SEE B67, (P.16)      OR C65, (P.28)--EXTRA",
        0,
        "explicit_cross_reference",
        "B67, (P.16)      OR C65, (P.28)",
        0,
        "local_target_outside_rq_annotation_domain",
        ("g_section",),
    ),
    (
        "g52_workhours_xref",
        33,
        "REPORTED IN SECTION",
        0,
        "explicit_cross_reference",
        "D OR E FOR THIS INCOME",
        0,
        "local_target_outside_rq_annotation_domain",
        ("g49_a_wife",),
    ),
)

# No two retained anchors share an exact printed identifier and exact label;
# the same_printed_identifier_and_exact_label relation is therefore empty here.
SAME_LABEL_ALIAS_SPECS: tuple[dict[str, Any], ...] = ()


def _selector(page: int, needle: Any, occurrence: Any) -> dict[str, Any]:
    if isinstance(needle, tuple):
        return {
            "page": page,
            "utf8_byte_start": needle[0],
            "utf8_byte_end": needle[1],
        }
    return {"page": page, "needle": needle, "needle_occurrence": occurrence}


def _normalized_specs() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    flow = [
        {
            **_selector(page, needle, occurrence),
            "key": key,
            "kind": "flow_branch_label",
            "parent": parent,
        }
        for key, page, needle, occurrence, parent in FLOW_SPECS
    ]
    anchors = [
        {
            **_selector(page, needle, occurrence),
            "key": key,
            "kind": KIND_BY_CLASSIFICATION[classification],
            "node_domain": NODE_DOMAIN_BY_CLASSIFICATION[classification],
            "classification": classification,
            "identifier": identifier,
            "parents": tuple(parents),
            "paths": tuple(paths),
        }
        for (
            key,
            page,
            needle,
            occurrence,
            classification,
            identifier,
            parents,
            paths,
        ) in ANCHOR_SPECS
    ]
    anchor_by_key = {spec["key"]: spec for spec in anchors}
    prompts = []
    for anchor_key, purposes, applicable in PROMPT_SPECS:
        anchor = anchor_by_key[anchor_key]
        prompts.append(
            {
                **{
                    field: anchor[field]
                    for field in (
                        "page",
                        "needle",
                        "needle_occurrence",
                        "utf8_byte_start",
                        "utf8_byte_end",
                    )
                    if field in anchor
                },
                "key": f"{anchor_key}__prompt",
                "kind": "field_purpose_prompt",
                "anchor_key": anchor_key,
                "purposes": tuple(purposes),
                "anchors": tuple(applicable),
                "paths": anchor["paths"],
            }
        )
    repeats = [
        {
            **_selector(page, needle, occurrence),
            "key": key,
            "kind": "repeat_or_alias_instruction",
            "relation": relation,
            "target": target,
            "target_occurrence": target_occurrence,
            "handoff": handoff,
            "paths": tuple(paths),
        }
        for (
            key,
            page,
            needle,
            occurrence,
            relation,
            target,
            target_occurrence,
            handoff,
            paths,
        ) in REPEAT_SPECS
    ]
    return flow, anchors, prompts, repeats


def _path_sort_key(path: Sequence[str]) -> tuple[bytes, ...]:
    return tuple(part.encode("utf-8") for part in path)


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


def _locator() -> dict[str, Any]:
    locator_id = "psid-whole-document:" + _digest(
        [DOCUMENT_ID, INTERVIEW_WAVE, PDF_SHA256, PDF_SIZE]
    )
    return {
        "locator_id": locator_id,
        "source_document_id": DOCUMENT_ID,
        "interview_wave": INTERVIEW_WAVE,
        "filename": "q87.pdf",
        "location_type": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": PDF_SIZE,
        "size_bytes": PDF_SIZE,
        "full_file_sha256": PDF_SHA256,
        "range_sha256": PDF_SHA256,
        "pdf_page_domain": "all_pages_and_flow_branches",
    }


def _preliminary_occurrences(
    page_texts: Sequence[str],
) -> list[dict[str, Any]]:
    flow, anchors, prompts, repeats = _normalized_specs()
    specs = [*flow, *anchors, *prompts, *repeats]
    keys = [spec["key"] for spec in specs]
    if len(keys) != len(set(keys)):
        raise ValueError("review specification key collision")
    branch_keys = {spec["key"] for spec in flow}
    anchor_keys = {spec["key"] for spec in anchors}
    for spec in flow:
        if spec["parent"] is not None and spec["parent"] not in branch_keys:
            raise ValueError(f"unresolved flow parent {spec['parent']}")
    for spec in (*anchors, *prompts, *repeats):
        missing = set(spec["paths"]) - branch_keys
        if missing:
            raise ValueError(f"unresolved occurrence flow path {missing}")
    for spec in anchors:
        missing = set(spec["parents"]) - anchor_keys
        if missing:
            raise ValueError(f"unresolved local anchor parents: {missing}")
    for spec in prompts:
        missing = set(spec["anchors"]) - anchor_keys
        if missing:
            raise ValueError(f"unresolved prompt anchors: {missing}")
        for purpose in spec["purposes"]:
            if purpose not in PURPOSE_ORDER:
                raise ValueError(f"unratified field purpose {purpose}")

    rows: list[dict[str, Any]] = []
    for spec in specs:
        page_text = page_texts[spec["page"] - 1]
        start, end = _resolve_span(page_text, spec)
        matched, matched_sha256 = _strict_slice(
            page_text, start, end, spec["key"]
        )
        rows.append(
            {
                **spec,
                "utf8_byte_start": start,
                "utf8_byte_end": end,
                "matched_text": matched,
                "matched_utf8_sha256": matched_sha256,
            }
        )
    return rows


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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Order every occurrence once, then resolve branches before paths.

    The layout derivation places a printed routing label after questions it
    governs on the same physical page, so occurrence ordering (a pure span
    function) is fixed first and flow ancestry is resolved second.  Branch
    parents must still resolve earlier in complete source order.
    """

    items = _preliminary_occurrences(page_texts)
    items_by_group: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(
        list
    )
    for item in items:
        group = (
            item["page"],
            item["utf8_byte_start"],
            item["utf8_byte_end"],
            KIND_ORDER[item["kind"]],
        )
        items_by_group[group].append(item)

    slots: list[dict[str, Any]] = []
    page_indices: Counter[int] = Counter()
    for group in sorted(items_by_group):
        group_items = items_by_group[group]
        kind = group_items[0]["kind"]
        if kind != "flow_branch_label" and len(group_items) != 1:
            raise ValueError("duplicate non-flow atomic occurrence")
        if kind == "flow_branch_label" and len(group_items) > 1:
            raise ValueError("multi-parent branch label needs declared order")
        for ordinal, item in enumerate(group_items):
            index_on_page = page_indices[item["page"]]
            page_indices[item["page"]] += 1
            slots.append(
                {
                    "item": item,
                    "index_on_page": index_on_page,
                    "semantic_ordinal": (
                        ordinal if len(group_items) > 1 else 0
                    ),
                }
            )

    branches: list[dict[str, Any]] = []
    branch_by_key: dict[str, dict[str, Any]] = {}
    rows_by_slot: dict[int, dict[str, Any]] = {}
    occurrence_id_by_key: dict[str, str] = {}
    atom_coordinates: set[tuple[Any, ...]] = set()

    def _emit(position: int, slot: Mapping[str, Any], paths: list[list[str]]):
        item = slot["item"]
        row = _occurrence_row(
            item,
            locator_id,
            slot["index_on_page"],
            slot["semantic_ordinal"],
            paths,
        )
        coordinate = (
            item["page"],
            item["utf8_byte_start"],
            item["utf8_byte_end"],
            item["kind"],
            slot["semantic_ordinal"],
        )
        if coordinate in atom_coordinates:
            raise ValueError("duplicate occurrence coordinate")
        atom_coordinates.add(coordinate)
        rows_by_slot[position] = row
        occurrence_id_by_key[item["key"]] = row["questionnaire_occurrence_id"]
        return row

    for position, slot in enumerate(slots):
        item = slot["item"]
        if item["kind"] != "flow_branch_label":
            continue
        parent_key = item["parent"]
        if parent_key is None:
            parent_path = [FLOW_ROOT]
        else:
            if parent_key not in branch_by_key:
                raise ValueError(
                    f"later or unresolved flow parent {parent_key}"
                )
            parent_path = branch_by_key[parent_key]["branch_path"]
        row = _emit(position, slot, [list(parent_path)])
        parent_id = parent_path[-1]
        branch_id = "questionnaire-flow:" + _digest(
            [parent_id, INTERVIEW_WAVE, row["questionnaire_occurrence_id"]]
        )
        branch_path = [*parent_path, branch_id]
        if branch_id in branch_path[:-1]:
            raise ValueError("flow cycle")
        branch = {
            "flow_branch_id": branch_id,
            "parent_flow_branch_id": parent_id,
            "source_occurrence_id": row["questionnaire_occurrence_id"],
            "branch_path": branch_path,
            "interview_wave": INTERVIEW_WAVE,
            "source_locator_id": locator_id,
            "page_number": item["page"],
            "occurrence_index_on_page": slot["index_on_page"],
            "branch_label": item["matched_text"],
            "branch_label_sha256": item["matched_utf8_sha256"],
        }
        branches.append(branch)
        branch_by_key[item["key"]] = branch

    for position, slot in enumerate(slots):
        item = slot["item"]
        if item["kind"] == "flow_branch_label":
            continue
        paths = []
        for path_key in item["paths"]:
            if path_key not in branch_by_key:
                raise ValueError(f"unresolved occurrence flow path {path_key}")
            paths.append(branch_by_key[path_key]["branch_path"])
        if not paths:
            paths.append([FLOW_ROOT])
        if len({tuple(path) for path in paths}) != len(paths):
            raise ValueError("duplicate occurrence flow path")
        _emit(position, slot, sorted(paths, key=_path_sort_key))

    occurrences = [rows_by_slot[position] for position in range(len(slots))]
    branches.sort(
        key=lambda row: (row["page_number"], row["occurrence_index_on_page"])
    )
    return occurrences, branches, occurrence_id_by_key


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
    return [
        {
            "questionnaire_page_id": replay_page["questionnaire_page_id"],
            "source_document_id": DOCUMENT_ID,
            "source_locator_id": locator_id,
            "interview_wave": INTERVIEW_WAVE,
            "page_number": replay_page["page_number"],
            "page_text_utf8_sha256": replay_page["page_text_utf8_sha256"],
            "questionnaire_occurrence_ids": ids_by_page[
                replay_page["page_number"]
            ],
            "annotation_status": "complete",
        }
        for replay_page in replay_pages
    ]


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
    occurrence_id_by_key: Mapping[str, str],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _, anchors, _, _ = _normalized_specs()
    rows: list[dict[str, Any]] = []
    for spec in anchors:
        occurrence_id = occurrence_id_by_key[spec["key"]]
        occurrence = occurrence_by_id[occurrence_id]
        identifier, identifier_span = _identifier_slice(
            spec, page_texts[spec["page"] - 1]
        )
        parent_ids = [occurrence_id_by_key[key] for key in spec["parents"]]
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
    occurrence_id_by_key: Mapping[str, str],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _, _, prompts, _ = _normalized_specs()
    rows: list[dict[str, Any]] = []
    for spec in prompts:
        occurrence_id = occurrence_id_by_key[spec["key"]]
        occurrence = occurrence_by_id[occurrence_id]
        purposes = sorted(spec["purposes"], key=PURPOSE_ORDER.__getitem__)
        anchor_ids = [occurrence_id_by_key[key] for key in spec["anchors"]]
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
    occurrence_id_by_key: Mapping[str, str],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _, _, _, repeats = _normalized_specs()
    rows: list[dict[str, Any]] = []
    for spec in repeats:
        instruction_id = occurrence_id_by_key[spec["key"]]
        start, end = _needle_span(
            page_texts[spec["page"] - 1],
            spec["target"],
            spec["target_occurrence"],
        )
        matched, matched_sha256 = _strict_slice(
            page_texts[spec["page"] - 1], start, end, spec["key"]
        )
        unresolved = {
            "page_number": spec["page"],
            "utf8_byte_start": start,
            "utf8_byte_end": end,
            "matched_text": matched,
            "matched_utf8_sha256": matched_sha256,
        }
        preimage = [spec["relation"], instruction_id, unresolved]
        rows.append(
            {
                "local_repeat_evidence_id": (
                    "rq-local-repeat-evidence:" + _digest(preimage)
                ),
                "alias_relation": spec["relation"],
                "alias_anchor_occurrence_id": None,
                "referenced_anchor_occurrence_id": None,
                "source_instruction_occurrence_ids": [instruction_id],
                "unresolved_target_reference": unresolved,
                "evidence_occurrence_ids": [instruction_id],
                "handoff_status": spec["handoff"],
                "annotation_status": "complete",
            }
        )
    if SAME_LABEL_ALIAS_SPECS:  # pragma: no cover - empty for document 40
        raise ValueError("document-40 declares no same-label alias rows")
    rows.sort(
        key=lambda row: min(
            (
                occurrence_by_id[occurrence_id]["page_number"],
                occurrence_by_id[occurrence_id]["occurrence_index_on_page"],
            )
            for occurrence_id in row["evidence_occurrence_ids"]
        )
    )
    return rows


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
    by_page: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in output_rows:
        by_page[row["page_number"]].append(row)
    result: dict[str, list[str]] = {}
    for candidate in candidate_rows:
        kind = candidate["occurrence_kind_candidate"]
        same_page = by_page[candidate["page_number"]]
        targets = [
            row
            for row in same_page
            if row["occurrence_kind"] == kind
            and _overlaps(
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                candidate["utf8_byte_start"],
                candidate["utf8_byte_end"],
            )
        ]
        if not targets and kind in ANCHOR_RECLASS_TARGETS:
            # Whole-page review reclassified these detector lexemes; the
            # candidate is dispositioned against the retained row it names.
            targets = [
                row
                for row in same_page
                if row["occurrence_kind"] in ANCHOR_RECLASS_TARGETS[kind]
                and _overlaps(
                    row["utf8_byte_start"],
                    row["utf8_byte_end"],
                    candidate["utf8_byte_start"],
                    candidate["utf8_byte_end"],
                )
            ]
        ids = sorted(
            {row["questionnaire_occurrence_id"] for row in targets},
            key=output_order.__getitem__,
        )
        result[candidate["candidate_occurrence_id"]] = ids
    return result


# A detector lexeme whose retained semantics is a different §19 kind is
# dispositioned as a correction against that retained row rather than as a
# bare rejection.
ANCHOR_RECLASS_TARGETS = {
    "business_aggregate_anchor": ("context_anchor", "job_anchor"),
    "farm_aggregate_anchor": ("context_anchor",),
    "job_anchor": ("context_anchor",),
    "role_total_anchor": ("remuneration_component_anchor",),
    "field_purpose_prompt": ("context_anchor",),
}


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
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    output_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrence_rows
    }
    occurrence_projection = _candidate_occurrence_projection(
        candidate["candidate_occurrence_rows"], occurrence_rows
    )
    disposition_by_id: dict[str, str] = {}
    stage2_ids_by_candidate: dict[str, list[str]] = {}
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
        stage2_ids_by_candidate[candidate_id] = list(ids)

    locator_candidate = candidate["whole_document_locator_candidate"]
    append(
        "whole_document_locator",
        locator_candidate["candidate_locator_id"],
        "accepted",
        [locator["locator_id"]],
    )
    for candidate_page, output_page in zip(
        candidate["candidate_page_rows"], page_rows, strict=True
    ):
        append(
            "page",
            candidate_page["candidate_page_id"],
            "accepted",
            [output_page["questionnaire_page_id"]],
        )
    for candidate_occurrence in candidate["candidate_occurrence_rows"]:
        candidate_id = candidate_occurrence["candidate_occurrence_id"]
        ids = occurrence_projection[candidate_id]
        disposition = _candidate_occurrence_disposition(
            candidate_occurrence, ids, output_by_id
        )
        append("occurrence", candidate_id, disposition, ids)

    branch_id_by_source = {
        row["source_occurrence_id"]: row["flow_branch_id"]
        for row in branch_rows
    }
    branch_by_id = {row["flow_branch_id"]: row for row in branch_rows}
    candidate_ids_by_occurrence: dict[str, list[str]] = defaultdict(list)
    for candidate_occurrence_id, output_ids in occurrence_projection.items():
        for output_id in output_ids:
            candidate_ids_by_occurrence[output_id].append(
                candidate_occurrence_id
            )
    candidate_branch_source: dict[str, str] = {}
    for candidate_path in candidate["candidate_flow_path_rows"]:
        branch_id = candidate_path["candidate_branch_id"]
        source_id = candidate_path["source_candidate_occurrence_id"]
        existing = candidate_branch_source.setdefault(branch_id, source_id)
        if existing != source_id:
            raise ValueError("candidate branch has multiple source labels")

    for candidate_path in candidate["candidate_flow_path_rows"]:
        ids: list[str] = []
        source_candidate_id = candidate_path["source_candidate_occurrence_id"]
        candidate_parent_sources = [
            candidate_branch_source[branch_id]
            for branch_id in candidate_path["candidate_parent_path"]
            if branch_id != candidates.FLOW_ROOT_ID
        ]
        for occurrence_id in occurrence_projection[source_candidate_id]:
            if occurrence_id not in branch_id_by_source:
                continue
            branch_id = branch_id_by_source[occurrence_id]
            final_parent_sources = [
                branch_by_id[parent_branch_id]["source_occurrence_id"]
                for parent_branch_id in branch_by_id[branch_id]["branch_path"][
                    1:-1
                ]
            ]
            parent_path_matches = len(candidate_parent_sources) == len(
                final_parent_sources
            ) and all(
                candidate_parent_id
                in candidate_ids_by_occurrence[final_occurrence_id]
                for candidate_parent_id, final_occurrence_id in zip(
                    candidate_parent_sources,
                    final_parent_sources,
                    strict=True,
                )
            )
            if parent_path_matches:
                ids.append(branch_id)
        if not ids:
            disposition = "rejected"
        elif len(ids) > 1:
            disposition = "split"
        else:
            source_disposition = disposition_by_id[
                candidate_path["source_candidate_occurrence_id"]
            ]
            disposition = (
                "accepted" if source_disposition == "accepted" else "modified"
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
            for occurrence_id in occurrence_projection[source_candidate_id]
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
                projected_parents.extend(
                    occurrence_projection[parent_candidate_id]
                )
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
    return rows, stage2_ids_by_candidate


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
            row_id = row[id_field]
            if row_id in result:
                raise ValueError("stage-2 output IDs are not globally unique")
            result[row_id] = row
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
        elif dispositions == {"split"} and len(source_ids) == 1:
            action = "candidate_split"
        elif dispositions <= {"accepted", "modified", "split"}:
            # Several detector rows name one reviewer-verified span; the
            # retained row is the corrected consolidation of all of them.
            action = "candidate_modified"
        else:
            raise ValueError(
                f"unknown candidate dispositions for output {output_id}"
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
            row_id = row[id_field]
            if row_id in result:
                raise ValueError("candidate IDs are not globally unique")
            result[row_id] = row
    return result


def _occurrence_location(row: Mapping[str, Any], *, candidate: bool) -> str:
    kind_field = (
        "occurrence_kind_candidate" if candidate else "occurrence_kind"
    )
    return (
        f"{row[kind_field]} on page {row['page_number']} at UTF-8 bytes "
        f"[{row['utf8_byte_start']}, {row['utf8_byte_end']})"
    )


def _candidate_correction(
    disposition: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    output_rows: Sequence[Mapping[str, Any]],
    candidate_rows_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    kind = disposition["candidate_row_kind"]
    action = disposition["disposition"]
    if kind == "occurrence":
        source = _occurrence_location(candidate_row, candidate=True)
        if action == "rejected":
            occurrence_kind = candidate_row["occurrence_kind_candidate"]
            conclusions = {
                "flow_branch_label": (
                    "noncontrolling_flow_text_rejected",
                    "does not control a retained R_Q path",
                ),
                "field_purpose_prompt": (
                    "non_rq_field_prompt_rejected",
                    "does not express a retained R_Q field purpose",
                ),
                "role_anchor": (
                    "referential_role_mention_rejected",
                    "refers to a role without establishing a new local role anchor",
                ),
                "job_anchor": (
                    "nonestablishing_job_mention_rejected",
                    "does not establish a distinct local job slot",
                ),
                "remuneration_component_anchor": (
                    "nonestablishing_remuneration_mention_rejected",
                    "does not establish a distinct remuneration component",
                ),
                "role_total_anchor": (
                    "non_role_total_text_rejected",
                    "does not state a role-total remuneration anchor",
                ),
                "farm_aggregate_anchor": (
                    "nonestablishing_farm_mention_rejected",
                    "does not establish a distinct farm aggregate",
                ),
                "business_aggregate_anchor": (
                    "nonestablishing_business_mention_rejected",
                    "does not establish a distinct business aggregate",
                ),
                "context_anchor": (
                    "nonestablishing_context_text_rejected",
                    "does not establish a retained contextual field",
                ),
                "repeat_or_alias_instruction": (
                    "non_rq_repeat_instruction_rejected",
                    "does not instruct a repeat or cross-reference inside the"
                    " retained R_Q domain",
                ),
            }
            reason, conclusion = conclusions[occurrence_kind]
            return (
                reason,
                f"Whole-page review determined that candidate {source} "
                f"{conclusion}; no output row was emitted.",
            )

        targets = [
            _occurrence_location(target, candidate=False)
            for target in output_rows
        ]
        if action == "split":
            return (
                "compound_occurrence_split",
                f"Candidate {source} contains {len(targets)} independently "
                f"verified atoms: {'; '.join(targets)}.",
            )
        target = output_rows[0]
        kind_changed = (
            candidate_row["occurrence_kind_candidate"]
            != target["occurrence_kind"]
        )
        span_changed = (
            candidate_row["page_number"],
            candidate_row["utf8_byte_start"],
            candidate_row["utf8_byte_end"],
        ) != (
            target["page_number"],
            target["utf8_byte_start"],
            target["utf8_byte_end"],
        )
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
            f"Candidate {source} was corrected to the independently re-sliced "
            f"{_occurrence_location(target, candidate=False)}.",
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
            return (
                "unselected_flow_ancestry_rejected",
                f"Candidate path for {source} has parent path {candidate_path}; "
                "the independently reconstructed control-flow graph has no "
                "matching path for that label.",
            )
        final_paths = json.dumps(
            [row["branch_path"] for row in output_rows],
            separators=(",", ":"),
        )
        if action == "split":
            return (
                "flow_path_split",
                f"Candidate path for {source} was split into {len(output_rows)} "
                f"complete retained branch paths {final_paths}.",
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
            return (
                "nonestablishing_anchor_classification_rejected",
                f"Candidate anchor classification for {source} has no retained "
                "local establishing anchor after whole-page review.",
            )
        targets = [
            (
                f"{row['node_domain']}/{row['classification']} with printed "
                f"identifier {row['printed_identifier']!r} and parents "
                f"{json.dumps(row['parent_anchor_occurrence_ids'], separators=(',', ':'))}"
            )
            for row in output_rows
        ]
        if action == "split":
            return (
                "anchor_classification_split",
                f"Candidate anchor classification for {source} was split into "
                f"{len(targets)} local anchors: {'; '.join(targets)}.",
            )
        return (
            "anchor_definition_corrected",
            f"Candidate anchor classification for {source} was corrected from "
            f"{candidate_row['node_domain_candidate']}/"
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
            f"paths {json.dumps(output_row['flow_branch_paths'], separators=(',', ':'))}.",
        )
    if kind == "flow_branch":
        return (
            "manual_flow_branch_after_complete_page_review",
            f"Complete page review added branch label {output_row['branch_label']!r} "
            f"with complete path {json.dumps(output_row['branch_path'], separators=(',', ':'))}.",
        )
    if kind == "local_anchor_classification":
        return (
            "manual_anchor_after_complete_page_review",
            f"Complete page review classified source occurrence "
            f"{output_row['source_occurrence_id']} as "
            f"{output_row['node_domain']}/{output_row['classification']} with "
            f"parents {json.dumps(output_row['parent_anchor_occurrence_ids'], separators=(',', ':'))}.",
        )
    if kind == "local_field_purpose_classification":
        return (
            "manual_field_purpose_after_complete_page_review",
            f"Complete page review classified prompt occurrence "
            f"{output_row['source_prompt_occurrence_id']} with exact purposes "
            f"{json.dumps(output_row['field_purposes'], separators=(',', ':'))}.",
        )
    if kind == "local_repeat_or_alias_evidence":
        if output_row["unresolved_target_reference"] is not None:
            target = output_row["unresolved_target_reference"]
            detail = (
                f"target text {target['matched_text']!r} on page "
                f"{target['page_number']} at UTF-8 bytes "
                f"[{target['utf8_byte_start']}, {target['utf8_byte_end']})"
            )
        else:
            detail = (
                f"alias occurrence {output_row['alias_anchor_occurrence_id']} "
                "and referenced occurrence "
                f"{output_row['referenced_anchor_occurrence_id']}"
            )
        return (
            "manual_repeat_evidence_after_complete_page_review",
            f"Complete page review added {output_row['alias_relation']} evidence "
            f"for {detail}.",
        )
    if kind == "whole_document_locator":
        return (
            "manual_locator_after_complete_document_review",
            f"Complete document review added exact whole-file locator "
            f"{output_row['locator_id']}.",
        )
    if kind == "page":
        return (
            "manual_page_after_complete_page_review",
            f"Complete review added page {output_row['page_number']} with text "
            f"hash {output_row['page_text_utf8_sha256']}.",
        )
    raise ValueError(f"unknown manual-add row kind {kind}")


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
        candidate_row = candidate_rows_by_id[row["candidate_id"]]
        output_rows = [
            output_rows_by_id[output_id] for output_id in row["stage2_row_ids"]
        ]
        reason, note = _candidate_correction(
            row, candidate_row, output_rows, candidate_rows_by_id
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
        output_row = output_rows_by_id[row["stage2_row_id"]]
        reason, note = _manual_add_note(row["stage2_row_kind"], output_row)
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
    (
        "local_anchor_classification_rows",
        ("local_anchor_classification_id",),
    ),
    (
        "local_field_purpose_classification_rows",
        ("local_field_purpose_classification_id",),
    ),
    ("local_repeat_or_alias_evidence_rows", ("local_repeat_evidence_id",)),
    (
        "candidate_disposition_rows",
        ("candidate_row_kind", "candidate_id"),
    ),
    (
        "output_adjudication_rows",
        ("stage2_row_kind", "stage2_row_id"),
    ),
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


OUTER_KEYS = (
    "schema_version",
    "artifact_id",
    "authority_disposition",
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


def build_annotation(capture_root: Path | None = None) -> dict[str, Any]:
    """Build document 40 from pinned source bytes and explicit decisions."""

    capture_root = (
        _default_capture_root() if capture_root is None else capture_root
    )
    replay, index = _load_replay_and_index()
    page_texts = _derive_pages(capture_root)
    replay_pages = _review_page_rows(replay, page_texts)
    document = replay["source_document_replay"]["questionnaire_documents"][
        DOCUMENT_POSITION - 1
    ]
    if (
        document["source_document_id"] != DOCUMENT_ID
        or document["interview_waves"] != [INTERVIEW_WAVE]
        or document["canonical_source_path"] != CANONICAL_SOURCE_PATH
        or document["byte_size"] != PDF_SIZE
        or document["sha256"] != PDF_SHA256
    ):
        raise ValueError("document-40 independently replayed identity drift")

    locator = _locator()
    occurrences, branches, occurrence_id_by_key = (
        _build_occurrences_and_branches(page_texts, locator["locator_id"])
    )
    pages = _page_rows(replay_pages, occurrences, locator["locator_id"])
    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    anchors = _local_anchor_rows(
        page_texts, occurrence_id_by_key, occurrence_by_id
    )
    purposes = _purpose_rows(occurrence_id_by_key, occurrence_by_id)
    repeats = _repeat_rows(page_texts, occurrence_id_by_key, occurrence_by_id)
    candidate = _load_candidate(replay, index)
    if document != candidate["document_source_row"]:
        raise ValueError("candidate document differs from source replay")
    dispositions, _ = _candidate_dispositions(
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

    replay_identity = _identity(
        REPLAY_PATH,
        replay["schema_version"],
        replay["artifact_id"],
        REPLAY_RAW_SHA256,
        REPLAY_CONTENT_SHA256,
    )
    index_identity = _identity(
        INDEX_PATH,
        index["schema_version"],
        index["artifact_id"],
        INDEX_RAW_SHA256,
        INDEX_CONTENT_SHA256,
    )
    candidate_identity = {
        **_identity(
            CANDIDATE_PATH,
            candidate["schema_version"],
            candidate["artifact_id"],
            CANDIDATE_RAW_SHA256,
            CANDIDATE_CONTENT_SHA256,
        ),
        "candidate_payload_sha256": CANDIDATE_PAYLOAD_SHA256,
    }
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": (
            "rq-stage2-document-annotation:"
            + _digest([DOCUMENT_ID, INTERVIEW_WAVE])
        ),
        "authority_disposition": {
            "authority_kind": "sealed_document_annotation_nonauthority",
            "sealed_document_count": 1,
            "whole_document_page_review_complete": True,
            "candidate_auto_promotion_permitted": False,
            "downstream_authority_inputs_read": False,
            "global_resolution_performed": False,
            "canonical_q5_artifact_emitted": False,
            "canonical_era_seal_emitted": False,
            "status": "pass",
        },
        "source_replay_identity": replay_identity,
        "candidate_index_identity": index_identity,
        "candidate_artifact_identity": candidate_identity,
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
    validate_annotation(value, capture_root=capture_root)
    return value


def _validate_exact_rows(
    rows: Sequence[Mapping[str, Any]], keys: Sequence[str], label: str
) -> None:
    for index, row in enumerate(rows):
        _expect_keys(row, keys, f"{label}[{index}]")


def _candidate_domain(
    candidate: Mapping[str, Any],
) -> list[tuple[str, str]]:
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
    """Validate every stage-2 document-40 source and sealing invariant."""

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
        or value["document_source_row"]
        != replay["source_document_replay"]["questionnaire_documents"][
            DOCUMENT_POSITION - 1
        ]
        or value["questionnaire_page_text_derivation"]
        != replay["questionnaire_page_replay"][
            "questionnaire_page_text_derivation"
        ]
        or value["status"] != STATUS
    ):
        raise ValueError("stage-2 outer identity drift")
    expected_authority = {
        "authority_kind": "sealed_document_annotation_nonauthority",
        "sealed_document_count": 1,
        "whole_document_page_review_complete": True,
        "candidate_auto_promotion_permitted": False,
        "downstream_authority_inputs_read": False,
        "global_resolution_performed": False,
        "canonical_q5_artifact_emitted": False,
        "canonical_era_seal_emitted": False,
        "status": "pass",
    }
    if value["authority_disposition"] != expected_authority:
        raise ValueError("stage-2 nonauthority disposition drift")

    expected_replay_identity = _identity(
        REPLAY_PATH,
        replay["schema_version"],
        replay["artifact_id"],
        REPLAY_RAW_SHA256,
        REPLAY_CONTENT_SHA256,
    )
    expected_index_identity = _identity(
        INDEX_PATH,
        index["schema_version"],
        index["artifact_id"],
        INDEX_RAW_SHA256,
        INDEX_CONTENT_SHA256,
    )
    if (
        value["source_replay_identity"] != expected_replay_identity
        or value["candidate_index_identity"] != expected_index_identity
    ):
        raise ValueError("stage-2 replay or index identity drift")

    locator_rows = value["whole_document_locator_rows"]
    _validate_exact_rows(locator_rows, LOCATOR_KEYS, "locator")
    if locator_rows != [_locator()]:
        raise ValueError("whole-document locator drift")
    locator = locator_rows[0]
    locator_id = locator["locator_id"]

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

    expected_occurrences, expected_branches, occurrence_id_by_key = (
        _build_occurrences_and_branches(page_texts, locator_id)
    )
    expected_pages = _page_rows(replay_pages, expected_occurrences, locator_id)
    if pages != expected_pages:
        raise ValueError("missing, reordered, or changed questionnaire page")
    if occurrences != expected_occurrences:
        raise ValueError("occurrence span, path, order, hash, or ID drift")
    if branches != expected_branches:
        raise ValueError("flow branch ancestry, label, path, or ID drift")

    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrences
    }
    if len(occurrence_by_id) != len(occurrences):
        raise ValueError("duplicate occurrence ID")
    expected_anchors = _local_anchor_rows(
        page_texts, occurrence_id_by_key, occurrence_by_id
    )
    expected_purposes = _purpose_rows(occurrence_id_by_key, occurrence_by_id)
    expected_repeats = _repeat_rows(
        page_texts, occurrence_id_by_key, occurrence_by_id
    )
    if anchors != expected_anchors:
        raise ValueError("local anchor classification or parent drift")
    if purposes != expected_purposes:
        raise ValueError("field-purpose classification or evidence drift")
    if repeats != expected_repeats:
        raise ValueError("repeat/alias evidence is incomplete or inferred")

    # Candidate evidence is opened only after source bytes have independently
    # reproduced the full page, occurrence, branch, anchor, purpose, and
    # repeat/alias output domains above.
    candidate = _load_candidate(replay, index)
    if value["document_source_row"] != candidate["document_source_row"]:
        raise ValueError("candidate document differs from source replay")
    expected_candidate_identity = {
        **_identity(
            CANDIDATE_PATH,
            candidate["schema_version"],
            candidate["artifact_id"],
            CANDIDATE_RAW_SHA256,
            CANDIDATE_CONTENT_SHA256,
        ),
        "candidate_payload_sha256": CANDIDATE_PAYLOAD_SHA256,
    }
    if value["candidate_artifact_identity"] != expected_candidate_identity:
        raise ValueError("stage-2 candidate identity drift")

    expected_dispositions, _ = _candidate_dispositions(
        candidate, locator, pages, occurrences, branches, anchors
    )
    if dispositions != expected_dispositions:
        raise ValueError("candidate disposition exact cover drift")
    if len(dispositions) != CANDIDATE_DENOMINATOR:
        raise ValueError("document-40 candidate denominator drift")
    candidate_domain = _candidate_domain(candidate)
    if [
        (row["candidate_row_kind"], row["candidate_id"])
        for row in dispositions
    ] != candidate_domain:
        raise ValueError("candidate disposition domain order drift")

    output_relations = _output_relations(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    output_rows_by_id = _output_row_lookup(
        locator, pages, occurrences, branches, anchors, purposes, repeats
    )
    expected_adjudications = _output_adjudications(
        output_relations, dispositions
    )
    if adjudications != expected_adjudications:
        raise ValueError(
            "output adjudication exact cover or reverse-map drift"
        )
    if len(output_rows_by_id) != len(output_relations):
        raise ValueError("stage-2 output IDs are not globally unique")

    disposition_by_id = {row["candidate_id"]: row for row in dispositions}
    adjudication_by_id = {row["stage2_row_id"]: row for row in adjudications}
    for candidate_id, disposition in disposition_by_id.items():
        for _, output_id in output_relations:
            forward = output_id in disposition["stage2_row_ids"]
            reverse = (
                candidate_id
                in adjudication_by_id[output_id]["source_candidate_ids"]
            )
            if forward != reverse:
                raise ValueError("candidate/output adjudication is one-sided")

    expected_notes = _correction_notes(
        candidate, dispositions, adjudications, output_rows_by_id
    )
    if notes != expected_notes:
        raise ValueError("correction-note exact cover drift")
    expected_seal = _seal(value)
    if value["seal"] != expected_seal:
        raise ValueError("row-domain seal drift")
    expected_integrity = {
        "canonicalization": candidates.CANONICALIZATION,
        "content_sha256": _content_digest(value),
    }
    if value["integrity"] != expected_integrity:
        raise ValueError("stage-2 whole-artifact integrity drift")

    serialized = json.dumps(value, ensure_ascii=True)
    forbidden = (
        "psid-job-slot:",
        "psid-component-slot:",
        "psid-node-alias:",
        "psid-questionnaire-relationship:",
        '"canonical_node_id"',
        '"source_inventory_key"',
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-40 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 40: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
