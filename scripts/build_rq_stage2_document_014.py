#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for q74.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 25-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.
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
import build_rq_stage1_source_replay as replay_tools  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

SCHEMA_VERSION = "rq_stage2_document_annotation.v1"
STATUS = "pass_sealed_complete_nonauthority_annotation"
DOCUMENT_POSITION = 14
DOCUMENT_ID = (
    "psid-source-document:"
    "f9140158fc372056d7ba85654ec3cb3bace413c36f468124159dd55621fb548a"
)
INTERVIEW_WAVE = 1974
CANONICAL_SOURCE_PATH = "documentation/capture1/q74.pdf"
PDF_SIZE = 934_225
PDF_SHA256 = "c379581d8bf5fd3e587016578d9aed365dea45f035838de96f78c8d2a12d7941"
PAGE_COUNT = 25
EMPTY_TEXT_PAGES = (1, 3, 5, 7, 9, 11, 13, 21, 22, 23, 25)

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_02_documents_011_020"
    / "document_014_q74_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_014_q74_annotation_v1.json"
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
    "6205a483da7bbeca21b5ce615d3c5af2bf23f47cf48282b2ff413680802b379f"
)
CANDIDATE_CONTENT_SHA256 = (
    "429588f79764ab6f99cf821f2230e02abcb509ba405144d343f55a48c7b85d3d"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "582e50bdca6002ff62d4e332e0b6e98d546d0f45bf02fba56a5a06ff330af527"
)

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
    value = source_tools.strict_parse_document(path.read_bytes(), label)
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


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
        raise ValueError("document-14 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-14 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-14 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-14 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / "q74.pdf"
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("q74.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("q74.pdf page-count drift")
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
        raise ValueError("document-14 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-14 replay page text drift")
    if tuple(
        index + 1 for index, text in enumerate(page_texts) if not text
    ) != (EMPTY_TEXT_PAGES):
        raise ValueError("document-14 empty-text page domain drift")
    return rows


def _trimmed_line_span(page_text: str, marker: str) -> tuple[int, int]:
    matches: list[tuple[int, int]] = []
    offset = 0
    for raw_line in page_text.splitlines(keepends=True):
        line = raw_line[:-1] if raw_line.endswith("\n") else raw_line
        if line.endswith("\r"):
            line = line[:-1]
        if marker in line:
            left = len(line) - len(line.lstrip(" \t"))
            right = len(line.rstrip(" \t"))
            matches.append((offset + left, offset + right))
        offset += len(raw_line)
    if len(matches) != 1:
        raise ValueError(f"expected one physical line containing {marker!r}")
    start_chars, end_chars = matches[0]
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _block_span(
    page_text: str, start_marker: str, end_marker: str | None = None
) -> tuple[int, int]:
    lines = page_text.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)
    start_rows = [
        index for index, line in enumerate(lines) if start_marker in line
    ]
    end_marker = start_marker if end_marker is None else end_marker
    end_rows = [
        index for index, line in enumerate(lines) if end_marker in line
    ]
    if (
        len(start_rows) != 1
        or len(end_rows) != 1
        or end_rows[0] < start_rows[0]
    ):
        raise ValueError(
            f"invalid unique block markers {start_marker!r}, {end_marker!r}"
        )
    first = lines[start_rows[0]].rstrip("\n\r")
    last = lines[end_rows[0]].rstrip("\n\r")
    left = len(first) - len(first.lstrip(" \t"))
    right = len(last.rstrip(" \t"))
    start_chars = offsets[start_rows[0]] + left
    end_chars = offsets[end_rows[0]] + right
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


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
    if "needle" in spec:
        return _needle_span(
            page_text, spec["needle"], spec.get("needle_occurrence", 0)
        )
    if "start_marker" in spec:
        return _block_span(
            page_text, spec["start_marker"], spec.get("end_marker")
        )
    return _trimmed_line_span(page_text, spec["line_marker"])


def _line(key: str, page: int, marker: str, **values: Any) -> dict[str, Any]:
    return {"key": key, "page": page, "line_marker": marker, **values}


def _block(
    key: str,
    page: int,
    start_marker: str,
    end_marker: str,
    **values: Any,
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "start_marker": start_marker,
        "end_marker": end_marker,
        **values,
    }


def _needle(key: str, page: int, needle: str, **values: Any) -> dict[str, Any]:
    return {"key": key, "page": page, "needle": needle, **values}


def _byte(
    key: str, page: int, start: int, end: int, **values: Any
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "utf8_byte_start": start,
        "utf8_byte_end": end,
        **values,
    }


# These are reviewer decisions, not detector rules.  Each selector identifies
# text observed during the page-by-page pass and is re-resolved against q74.
ANCHOR_SPECS: tuple[dict[str, Any], ...] = (
    _needle(
        "d1_head_possessive",
        4,
        "HEAD's",
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="Dl.",
    ),
    _needle(
        "d1_head",
        4,
        "HEAD",
        needle_occurrence=1,
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="Dl.",
    ),
    _needle(
        "d1_present_job",
        4,
        "present job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="Dl.",
        parents=("d1_head",),
    ),
    _needle(
        "d2_main_occupation",
        4,
        "main occupation",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="Dz.",
        parents=("d1_head",),
    ),
    _line(
        "d2_occupation_context",
        4,
        "What is your main occupation?",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Dz.",
        parents=("d2_main_occupation",),
    ),
    _line(
        "d3_occupation_context",
        4,
        "D3. Tell",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D3.",
        parents=("d2_main_occupation",),
    ),
    _line(
        "d4_industry_context",
        4,
        "D4.   What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D4.",
        parents=("d1_present_job",),
    ),
    _line(
        "d5_employee_context",
        4,
        "D5.    Do you work",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D5.",
        parents=("d1_present_job",),
    ),
    _needle(
        "d6_this_job",
        4,
        "this        job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="D6.",
        parents=("d1_head",),
    ),
    _line(
        "d6_exposure_context",
        4,
        "D6.    How long",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D6.",
        parents=("d6_this_job",),
    ),
    _needle(
        "d25_extra_jobs",
        6,
        "extra jobs",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="D25.",
    ),
    _needle(
        "d25_main_job",
        6,
        "main job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="D25.",
    ),
    _line(
        "d25_assignment_context",
        6,
        "D25.       Did you have any extra jobs",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D25.",
        parents=("d25_extra_jobs",),
    ),
    _line(
        "d26_occupation_context",
        6,
        "D2fj. Vhat did you do?",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D2fj.",
        parents=("d25_extra_jobs",),
    ),
    _line(
        "d27_occupation_context",
        6,
        "D27. Anything",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D27.",
        parents=("d25_extra_jobs",),
    ),
    _line(
        "d28_hourly_component",
        6,
        "D28. About h ow much",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="D28.",
        parents=("d25_extra_jobs",),
    ),
    _needle(
        "d29_extra_job",
        6,
        "extra                    job(s)",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="D29.",
    ),
    _line(
        "d29_exposure_context",
        6,
        "D29. And how many weeks",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D29.",
        parents=("d29_extra_job",),
    ),
    _needle(
        "d30_extra_job",
        6,
        "extra           job(s)",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="D30.",
    ),
    _line(
        "d30_exposure_context",
        6,
        "D30. On the average.",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="D30.",
        parents=("d30_extra_job",),
    ),
    _needle(
        "e1_prospective_job",
        8,
        "job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="El.",
    ),
    _line(
        "e1_occupation_context",
        8,
        "El.     What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="El.",
        parents=("e1_prospective_job",),
    ),
    _line(
        "e2_expected_component",
        8,
        "E2.     How much might",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="E2.",
        parents=("e1_prospective_job",),
    ),
    _line(
        "e3_enrollment_context",
        8,
        "E3.   Will",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="E3.",
        parents=("e1_prospective_job",),
    ),
    _needle(
        "e6_last_job",
        8,
        "last       job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
    ),
    _needle(
        "e6_occupation",
        8,
        "occupation",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        parents=(),
    ),
    _line(
        "e6_occupation_context",
        8,
        "What sort   of work did you do",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        parents=("e6_last_job",),
    ),
    _line(
        "e7_industry_context",
        8,
        "E7. What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="E7.",
        parents=("e6_last_job",),
    ),
    _line(
        "e9_exposure_context",
        8,
        "E9.     How many weeks",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="E9.",
        parents=("e6_last_job",),
    ),
    _line(
        "e10_exposure_context",
        8,
        "ElO. About how many hours",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="ElO.",
        parents=("e6_last_job",),
    ),
    _line(
        "e11_exposure_context",
        8,
        "Ell.     How many weeks were you sick",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Ell.",
        parents=("e6_last_job",),
    ),
    _block(
        "e12_exposure_context",
        8,
        "E12. Then, how many weeks",
        "or laid     off",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="E12.",
        parents=("e6_last_job",),
    ),
    _needle(
        "f1_head",
        10,
        "HEAD",
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="Fl.",
    ),
    _line(
        "f1_assignment_context",
        10,
        "Fl.   During",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Fl.",
        parents=("f1_head",),
    ),
    _needle(
        "f3_occupation_job",
        10,
        "occupation",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="F3.",
        parents=("f1_head",),
    ),
    _line(
        "f3_occupation_context",
        10,
        "F3.     What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="F3.",
        parents=("f3_occupation_job",),
    ),
    _line(
        "f4_industry_context",
        10,
        "F4.    What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="F4.",
        parents=("f3_occupation_job",),
    ),
    _line(
        "f5_exposure_context",
        10,
        "F5.     How many weeks",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="F5.",
        parents=("f3_occupation_job",),
    ),
    _line(
        "f6_exposure_context",
        10,
        "F6.     About how many hours",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="F6.",
        parents=("f3_occupation_job",),
    ),
    _needle(
        "f7_new_job",
        10,
        "new job",
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="F7.",
        parents=("f1_head",),
    ),
    _needle(
        "f8_prospective_job",
        10,
        "job",
        needle_occurrence=3,
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="FF8.",
        parents=("f1_head",),
    ),
    _line(
        "f8_occupation_context",
        10,
        "FF8. What kind",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="FF8.",
        parents=("f8_prospective_job",),
    ),
    _line(
        "f9_expected_component",
        10,
        "F9.     How much might",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="F9.",
        parents=("f8_prospective_job",),
    ),
    _line(
        "f10_enrollment_context",
        10,
        "FlO. Would you have to get",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="FlO.",
        parents=("f8_prospective_job",),
    ),
    _line(
        "f14_pay_component",
        10,
        "F14. How much do they pay?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="F14.",
        parents=("f8_prospective_job",),
    ),
    _needle(
        "g13_wife",
        12,
        "wife",
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="Gl3.",
    ),
    _line(
        "g13_exposure_context",
        12,
        "Gl3.     How many years",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Gl3.",
        parents=("g13_wife",),
    ),
    _needle(
        "g14_wife",
        12,
        "she",
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="G14.",
    ),
    _line(
        "g14_exposure_context",
        12,
        "G14.     How many of these years",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="G14.",
        parents=("g14_wife",),
    ),
    _needle(
        "g15_wife",
        12,
        "she",
        needle_occurrence=1,
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="G15.",
    ),
    _line(
        "g15_exposure_context",
        12,
        "G15.     During",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="G15.",
        parents=("g15_wife",),
    ),
    _line(
        "h1_farm_aggregate",
        15,
        "Hl.   ,'FI;J;R",
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="Hl.",
    ),
    _block(
        "h2_farm_component",
        15,
        "H2. What were your total receipts",
        "soi1 bank payments",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H2.",
        parents=("h1_farm_aggregate",),
    ),
    _needle(
        "h2_farming_aggregate",
        15,
        "farming",
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="H2.",
    ),
    _block(
        "h3_farm_expense_component",
        15,
        "H3. Chat were your",
        "expenses?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H3.",
        parents=("h1_farm_aggregate",),
    ),
    _line(
        "h4_farm_net_component",
        15,
        "H4. That left",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H4.",
        parents=("h1_farm_aggregate",),
    ),
    _needle(
        "h4_farming_aggregate",
        15,
        "farming",
        needle_occurrence=1,
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="H4.",
    ),
    _block(
        "h5_business_aggregate",
        15,
        "H5.     Did you",
        "interest in any business enterprise?",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H5.",
    ),
    _block(
        "h6_incorporation_context",
        15,
        "H6. 1s it a corporation",
        "interest in both kinds?",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="H6.",
        parents=("h5_business_aggregate",),
    ),
    _block(
        "h7_business_aggregate",
        15,
        "H7. How much was your",
        "any profit left in?",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H7.",
    ),
    _needle(
        "h7_business_component",
        15,
        "total                         income from the business",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H7.",
        parents=("h7_business_aggregate",),
    ),
    _block(
        "h8_head_role_total",
        15,
        "H8.   How much did you",
        "anything was deducted",
        kind="role_total_anchor",
        node_domain="aggregate",
        classification="role_total",
        identifier="H8.",
    ),
    _needle(
        "h8_head",
        15,
        "HEAD",
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="H8.",
    ),
    _needle(
        "h8_wage_component",
        15,
        "wages and salaries",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H8.",
        parents=("h8_head_role_total",),
    ),
    _block(
        "h9_supplemental_component",
        16,
        "H9.    In addition",
        "commissions?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H9.",
        parents=("h8_head_role_total",),
    ),
    _needle(
        "h11_head",
        16,
        "HEAD",
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="Hll.",
    ),
    _needle(
        "h11a_business_aggregate",
        16,
        "professional practice  or trade",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="a>",
    ),
    _line(
        "h11a_business_component",
        16,
        "professional practice  or trade?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="a>",
        parents=("h11a_business_aggregate",),
    ),
    _needle(
        "h11b_farm_aggregate",
        16,
        "farming or market gardening",
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="b)",
    ),
    _needle(
        "h11b_business_aggregate",
        16,
        "roomers or boarders",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="b)",
    ),
    _needle(
        "h11b_farm_component",
        16,
        "farming or market gardening",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="b)",
        parents=("h11b_farm_aggregate",),
    ),
    _needle(
        "h17_head",
        17,
        "HEAD",
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="H17.",
    ),
    _needle(
        "h17_wife",
        17,
        "WIFE",
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="H17.",
    ),
    _needle(
        "h18_wife",
        17,
        "wife",
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="H18.",
    ),
    _block(
        "h19_wife_role_total",
        17,
        "H19.   Was it",
        "a business,     or what?",
        kind="role_total_anchor",
        node_domain="aggregate",
        classification="role_total",
        identifier="H19.",
        parents=("h18_wife",),
    ),
    _needle(
        "h19_wage_component",
        17,
        "wages, salary",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H19.",
        parents=("h19_wife_role_total",),
    ),
    _needle(
        "h19_business_aggregate",
        17,
        "a business",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H19.",
        parents=("h18_wife",),
    ),
)


PROMPT_SPECS: tuple[dict[str, Any], ...] = (
    _block(
        "d1_prompt",
        4,
        "Dl.    We would like",
        "now, looking for work",
        purposes=("interview_and_role_attachment", "assignment"),
        anchors=("d1_head_possessive", "d1_head", "d1_present_job"),
    ),
    _line(
        "d2_prompt",
        4,
        "What is your main occupation?",
        purposes=("occupation", "job_identifier"),
        anchors=("d1_head", "d2_main_occupation", "d2_occupation_context"),
    ),
    _line(
        "d3_prompt",
        4,
        "D3. Tell",
        purposes=("occupation",),
        anchors=("d1_head", "d2_main_occupation", "d3_occupation_context"),
    ),
    _line(
        "d4_prompt",
        4,
        "D4.   What kind",
        purposes=("industry",),
        anchors=("d1_head", "d1_present_job", "d4_industry_context"),
    ),
    _line(
        "d5_prompt",
        4,
        "D5.    Do you work",
        purposes=("employee_self_or_mixed",),
        anchors=("d1_head", "d1_present_job", "d5_employee_context"),
    ),
    _line(
        "d6_prompt",
        4,
        "D6.    How long",
        purposes=("month_or_exposure",),
        anchors=("d1_head", "d6_this_job", "d6_exposure_context"),
    ),
    _block(
        "d25_prompt",
        6,
        "D25.       Did you have any extra jobs",
        "your main job in 1973?",
        purposes=("assignment", "job_identifier"),
        anchors=("d25_extra_jobs", "d25_main_job", "d25_assignment_context"),
    ),
    _line(
        "d26_prompt",
        6,
        "D2fj. Vhat did you do?",
        purposes=("occupation",),
        anchors=("d25_extra_jobs", "d26_occupation_context"),
    ),
    _line(
        "d27_prompt",
        6,
        "D27. Anything",
        purposes=("occupation",),
        anchors=("d25_extra_jobs", "d27_occupation_context"),
    ),
    _line(
        "d28_prompt",
        6,
        "D28. About h ow much",
        purposes=("amount", "reporting_unit"),
        anchors=("d25_extra_jobs", "d28_hourly_component"),
    ),
    _line(
        "d29_prompt",
        6,
        "D29. And how many weeks",
        purposes=("month_or_exposure",),
        anchors=("d29_extra_job", "d29_exposure_context"),
    ),
    _line(
        "d30_prompt",
        6,
        "D30. On the average.",
        purposes=("month_or_exposure",),
        anchors=("d30_extra_job", "d30_exposure_context"),
    ),
    _line(
        "e1_prompt",
        8,
        "El.     What kind",
        purposes=("occupation", "job_identifier"),
        anchors=("e1_prospective_job", "e1_occupation_context"),
    ),
    _line(
        "e2_prompt",
        8,
        "E2.     How much might",
        purposes=("amount", "reporting_unit"),
        anchors=("e1_prospective_job", "e2_expected_component"),
    ),
    _line(
        "e3_prompt",
        8,
        "E3.   Will",
        purposes=("enrollment",),
        anchors=("e1_prospective_job", "e3_enrollment_context"),
    ),
    _line(
        "e6_prompt",
        8,
        "What sort   of work did you do",
        purposes=("occupation", "job_identifier"),
        anchors=("e6_last_job", "e6_occupation", "e6_occupation_context"),
    ),
    _line(
        "e7_prompt",
        8,
        "E7. What kind",
        purposes=("industry",),
        anchors=("e6_last_job", "e7_industry_context"),
    ),
    _line(
        "e9_prompt",
        8,
        "E9.     How many weeks",
        purposes=("month_or_exposure",),
        anchors=("e6_last_job", "e9_exposure_context"),
    ),
    _line(
        "e10_prompt",
        8,
        "ElO. About how many hours",
        purposes=("month_or_exposure",),
        anchors=("e6_last_job", "e10_exposure_context"),
    ),
    _line(
        "e11_prompt",
        8,
        "Ell.     How many weeks were you sick",
        purposes=("month_or_exposure",),
        anchors=("e6_last_job", "e11_exposure_context"),
    ),
    _block(
        "e12_prompt",
        8,
        "E12. Then, how many weeks",
        "or laid     off",
        purposes=("month_or_exposure",),
        anchors=("e6_last_job", "e12_exposure_context"),
    ),
    _line(
        "f1_prompt",
        10,
        "Fl.   During",
        purposes=("interview_and_role_attachment", "assignment"),
        anchors=("f1_head", "f1_assignment_context"),
    ),
    _line(
        "f3_prompt",
        10,
        "F3.     What kind",
        purposes=("occupation", "job_identifier"),
        anchors=("f1_head", "f3_occupation_job", "f3_occupation_context"),
    ),
    _line(
        "f4_prompt",
        10,
        "F4.    What kind",
        purposes=("industry",),
        anchors=("f3_occupation_job", "f4_industry_context"),
    ),
    _line(
        "f5_prompt",
        10,
        "F5.     How many weeks",
        purposes=("month_or_exposure",),
        anchors=("f3_occupation_job", "f5_exposure_context"),
    ),
    _line(
        "f6_prompt",
        10,
        "F6.     About how many hours",
        purposes=("month_or_exposure",),
        anchors=("f3_occupation_job", "f6_exposure_context"),
    ),
    _line(
        "f7_prompt",
        10,
        "F7.     Are you thinking",
        purposes=("job_identifier",),
        anchors=("f1_head", "f7_new_job"),
    ),
    _line(
        "f8_prompt",
        10,
        "FF8. What kind",
        purposes=("occupation", "job_identifier"),
        anchors=("f1_head", "f8_prospective_job", "f8_occupation_context"),
    ),
    _line(
        "f9_prompt",
        10,
        "F9.     How much might",
        purposes=("amount", "reporting_unit"),
        anchors=("f8_prospective_job", "f9_expected_component"),
    ),
    _line(
        "f10_prompt",
        10,
        "FlO. Would you have to get",
        purposes=("enrollment",),
        anchors=("f8_prospective_job", "f10_enrollment_context"),
    ),
    _line(
        "f14_prompt",
        10,
        "F14. How much do they pay?",
        purposes=("amount", "reporting_unit"),
        anchors=("f8_prospective_job", "f14_pay_component"),
    ),
    _line(
        "g13_prompt",
        12,
        "Gl3.     How many years",
        purposes=("interview_and_role_attachment", "month_or_exposure"),
        anchors=("g13_wife", "g13_exposure_context"),
    ),
    _line(
        "g14_prompt",
        12,
        "G14.     How many of these years",
        purposes=("month_or_exposure",),
        anchors=("g14_wife", "g14_exposure_context"),
    ),
    _line(
        "g15_prompt",
        12,
        "G15.     During",
        purposes=("month_or_exposure",),
        anchors=("g15_wife", "g15_exposure_context"),
    ),
    _line(
        "h1_prompt",
        15,
        "Hl.   ,'FI;J;R",
        purposes=("assignment",),
        anchors=("h1_farm_aggregate",),
    ),
    _block(
        "h2_prompt",
        15,
        "H2. What were your total receipts",
        "soi1 bank payments",
        purposes=("amount", "reporting_unit"),
        anchors=(
            "h1_farm_aggregate",
            "h2_farming_aggregate",
            "h2_farm_component",
        ),
    ),
    _block(
        "h3_prompt",
        15,
        "H3. Chat were your",
        "expenses?",
        purposes=("amount", "reporting_unit"),
        anchors=("h1_farm_aggregate", "h3_farm_expense_component"),
    ),
    _line(
        "h4_prompt",
        15,
        "H4. That left",
        purposes=("amount", "reporting_unit"),
        anchors=(
            "h1_farm_aggregate",
            "h4_farming_aggregate",
            "h4_farm_net_component",
        ),
    ),
    _block(
        "h5_prompt",
        15,
        "H5.     Did you",
        "interest in any business enterprise?",
        purposes=("assignment",),
        anchors=("h5_business_aggregate",),
    ),
    _block(
        "h6_prompt",
        15,
        "H6. 1s it a corporation",
        "interest in both kinds?",
        purposes=("incorporation",),
        anchors=("h5_business_aggregate", "h6_incorporation_context"),
    ),
    _block(
        "h7_prompt",
        15,
        "H7. How much was your",
        "any profit left in?",
        purposes=("amount", "reporting_unit"),
        anchors=("h7_business_aggregate", "h7_business_component"),
    ),
    _block(
        "h8_prompt",
        15,
        "H8.   How much did you",
        "anything was deducted",
        purposes=("interview_and_role_attachment", "amount", "reporting_unit"),
        anchors=("h8_head", "h8_head_role_total", "h8_wage_component"),
    ),
    _block(
        "h9_prompt",
        16,
        "H9.    In addition",
        "commissions?",
        purposes=("assignment",),
        anchors=("h8_head", "h8_head_role_total", "h9_supplemental_component"),
    ),
    _line(
        "h10_prompt",
        16,
        "HlO. How much was that?",
        purposes=("amount", "reporting_unit"),
        anchors=("h8_head", "h8_head_role_total", "h9_supplemental_component"),
    ),
    _line(
        "h11_header_prompt",
        16,
        "Hll.   Did you",
        purposes=("interview_and_role_attachment", "assignment"),
        anchors=("h11_head", "h11a_business_aggregate", "h11b_farm_aggregate"),
    ),
    _line(
        "h11a_prompt",
        16,
        "professional practice  or trade?",
        purposes=("assignment", "amount", "reporting_unit"),
        anchors=(
            "h11_head",
            "h11a_business_aggregate",
            "h11a_business_component",
        ),
    ),
    _block(
        "h11b_prompt",
        16,
        "farming or market gardening",
        "roomers or boarders?",
        purposes=("assignment", "amount", "reporting_unit"),
        anchors=("h11_head", "h11b_farm_aggregate", "h11b_farm_component"),
    ),
    _line(
        "h17_prompt",
        17,
        "H17.   INTERVIEWER",
        purposes=("interview_and_role_attachment",),
        anchors=("h17_head", "h17_wife"),
    ),
    _line(
        "h18_prompt",
        17,
        "H18.   Did your wife",
        purposes=("interview_and_role_attachment", "assignment"),
        anchors=("h18_wife", "h19_wife_role_total"),
    ),
    _line(
        "h19_prompt",
        17,
        "H19.   Was it",
        purposes=("assignment",),
        anchors=(
            "h18_wife",
            "h19_wife_role_total",
            "h19_wage_component",
            "h19_business_aggregate",
        ),
    ),
    _line(
        "h20_prompt",
        17,
        "H20.   How much was it",
        purposes=("amount", "reporting_unit"),
        anchors=(
            "h18_wife",
            "h19_wife_role_total",
            "h19_wage_component",
            "h19_business_aggregate",
        ),
    ),
)


REPEAT_SPECS: tuple[dict[str, Any], ...] = (
    _line(
        "h14_cross_reference",
        17,
        "H14.   INTERVIEWER: REFER TO",
        relation="explicit_cross_reference",
        target="Hlld      AND Hlle",
        handoff="local_target_outside_rq_annotation_domain",
    ),
    _byte(
        "h21_cross_reference",
        18,
        79,
        305,
        relation="explicit_cross_reference",
        target="COVER SHEET",
        handoff="cross_document_target_unresolved_for_global_assembly",
    ),
    _line(
        "h33_repeat",
        20,
        "TURN BACK AND ASK H22-H31",
        relation="explicit_repeat_instruction",
        target="H22-H31",
        handoff="local_target_outside_rq_annotation_domain",
    ),
)

SAME_LABEL_ALIAS_SPECS: tuple[dict[str, str], ...] = (
    {
        "key": "h17_exact_head_alias",
        "canonical_anchor": "h17_head",
        "alias_anchor": "h17_female_head",
    },
    {
        "key": "h17_exact_wife_alias",
        "canonical_anchor": "h17_wife",
        "alias_anchor": "h17_yes_wife",
    },
)


_DECLARED_ANCHORS = {row["key"]: row for row in ANCHOR_SPECS}


def _reviewed_anchor(key: str, **changes: Any) -> dict[str, Any]:
    return {**_DECLARED_ANCHORS[key], **changes}


# Freeze the conservative establishing-anchor inventory from the independent
# semantic review.  Later mentions are not inferred aliases or new jobs.
ANCHOR_SPECS = (
    _reviewed_anchor("d1_head"),
    _reviewed_anchor("d1_present_job", parents=("d1_head",)),
    _block(
        "d1_assignment_context",
        4,
        "Dl.    We would like",
        "now, looking for work",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Dl.",
        parents=("d1_present_job",),
    ),
    _reviewed_anchor("d2_occupation_context", parents=("d1_present_job",)),
    _reviewed_anchor("d4_industry_context"),
    _reviewed_anchor("d5_employee_context"),
    _reviewed_anchor("d6_exposure_context", parents=("d1_present_job",)),
    _reviewed_anchor("d25_extra_jobs"),
    _reviewed_anchor("d26_occupation_context"),
    _needle(
        "d28_hourly_component",
        6,
        "About h ow much did you make per hour at this?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="D28.",
        parents=("d25_extra_jobs",),
    ),
    _reviewed_anchor("d29_exposure_context", parents=("d25_extra_jobs",)),
    _reviewed_anchor("d30_exposure_context", parents=("d25_extra_jobs",)),
    _line(
        "e_section_context",
        8,
        "SECTION E:",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
    ),
    _reviewed_anchor("e1_prospective_job"),
    _needle(
        "e2_expected_component",
        8,
        "earn",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="E2.",
        parents=("e1_prospective_job",),
    ),
    _reviewed_anchor("e6_last_job"),
    _reviewed_anchor("e6_occupation_context"),
    _reviewed_anchor("e7_industry_context"),
    _byte(
        "e9_exposure_context",
        8,
        1157,
        1209,
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="E9.",
        parents=("e6_last_job",),
    ),
    _reviewed_anchor("e10_exposure_context"),
    _line(
        "e11_exposure_context",
        8,
        "Ell.     How many weeks were you sick",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="Ell.",
        parents=("e6_last_job",),
    ),
    _reviewed_anchor("e12_exposure_context"),
    _line(
        "f_section_context",
        10,
        "SECTION F:",
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
    ),
    _reviewed_anchor("f1_head"),
    _reviewed_anchor("f1_assignment_context"),
    _reviewed_anchor("f3_occupation_job"),
    _reviewed_anchor("f3_occupation_context"),
    _reviewed_anchor("f4_industry_context"),
    _reviewed_anchor("f5_exposure_context"),
    _reviewed_anchor("f6_exposure_context"),
    _byte(
        "f8_prospective_job",
        10,
        1578,
        1581,
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="FF8.",
        parents=("f1_head",),
    ),
    _needle(
        "f9_expected_component",
        10,
        "earn",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="F9.",
        parents=("f8_prospective_job",),
    ),
    _byte(
        "f13_available_jobs",
        10,
        2377,
        2381,
        kind="job_anchor",
        node_domain="job_slot",
        classification="source_job",
        identifier="F13.",
        parents=("f1_head",),
    ),
    _needle(
        "f14_pay_component",
        10,
        "How much do they pay",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="F14.",
        parents=("f13_available_jobs",),
    ),
    _reviewed_anchor("g13_wife"),
    _reviewed_anchor("g13_exposure_context"),
    _reviewed_anchor("g14_exposure_context", parents=("g13_wife",)),
    _reviewed_anchor("g15_exposure_context", parents=("g13_wife",)),
    _byte(
        "h1_farm_aggregate",
        15,
        517,
        553,
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="Hl.",
    ),
    _needle(
        "h2_farming_aggregate",
        15,
        "farming",
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="H2.",
    ),
    _needle(
        "h2_farm_component",
        15,
        "receipts",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H2.",
        parents=("h1_farm_aggregate",),
    ),
    _needle(
        "h3_farm_expense_component",
        15,
        "operating   expenses",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H3.",
        parents=("h1_farm_aggregate",),
    ),
    _needle(
        "h4_farm_net_component",
        15,
        "net income",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H4.",
        parents=("h1_farm_aggregate",),
    ),
    _needle(
        "h4_farming_aggregate",
        15,
        "farming",
        needle_occurrence=1,
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="H4.",
    ),
    _needle(
        "h5_business_primary",
        15,
        "business",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H5.",
    ),
    _needle(
        "h5_business_enterprise",
        15,
        "business",
        needle_occurrence=1,
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H5.",
    ),
    _byte(
        "h6_incorporation_context",
        15,
        1995,
        2152,
        kind="context_anchor",
        node_domain="component_slot",
        classification="source_context",
        identifier="H6.",
        parents=("h5_business_primary",),
    ),
    _needle(
        "h7_business_aggregate",
        15,
        "business",
        needle_occurrence=3,
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H7.",
    ),
    _needle(
        "h7_business_component",
        15,
        "share of the total                         income from the business",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H7.",
        parents=("h5_business_primary",),
    ),
    _reviewed_anchor("h8_head"),
    _reviewed_anchor("h8_head_role_total"),
    _needle(
        "h8_wage_component",
        15,
        "wages and salaries",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H8.",
        parents=("h8_head_role_total",),
    ),
    _block(
        "h9_supplemental_component",
        16,
        "bonuses,",
        "commissions?",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H9.",
        parents=("h8_head_role_total",),
    ),
    _reviewed_anchor("h11_head"),
    _needle(
        "h11a_business_aggregate",
        16,
        "professional practice  or trade",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="a>",
    ),
    _needle(
        "h11b_farm_aggregate",
        16,
        "farming or market gardening",
        kind="farm_aggregate_anchor",
        node_domain="aggregate",
        classification="farm_aggregate",
        identifier="b)",
    ),
    _reviewed_anchor("h11b_business_aggregate"),
    _reviewed_anchor("h17_head"),
    _reviewed_anchor("h17_wife"),
    _byte(
        "h17_yes_wife",
        17,
        650,
        654,
        kind="role_anchor",
        node_domain="role",
        classification="spouse_or_partner",
        identifier="H17.",
    ),
    _needle(
        "h17_female_head",
        17,
        "HEAD",
        needle_occurrence=1,
        kind="role_anchor",
        node_domain="role",
        classification="head_or_reference_person",
        identifier="H17.",
    ),
    _reviewed_anchor("h18_wife"),
    _reviewed_anchor("h19_wife_role_total"),
    _needle(
        "h19_wage_component",
        17,
        "wages, salary",
        kind="remuneration_component_anchor",
        node_domain="component_slot",
        classification="source_remuneration_component",
        identifier="H19.",
        parents=("h19_wife_role_total",),
    ),
    _needle(
        "h19_business_aggregate",
        17,
        "business",
        kind="business_aggregate_anchor",
        node_domain="aggregate",
        classification="business_aggregate",
        identifier="H19.",
        parents=("h18_wife",),
    ),
)

_DECLARED_PROMPTS = {row["key"]: row for row in PROMPT_SPECS}


def _reviewed_prompt(key: str, **changes: Any) -> dict[str, Any]:
    return {**_DECLARED_PROMPTS[key], **changes}


PROMPT_SPECS = (
    _reviewed_prompt(
        "d1_prompt",
        anchors=("d1_head", "d1_present_job", "d1_assignment_context"),
    ),
    _reviewed_prompt(
        "d2_prompt",
        purposes=("occupation",),
        anchors=("d1_head", "d1_present_job", "d2_occupation_context"),
    ),
    _reviewed_prompt("d4_prompt"),
    _reviewed_prompt("d5_prompt"),
    _reviewed_prompt(
        "d6_prompt",
        anchors=("d1_head", "d1_present_job", "d6_exposure_context"),
    ),
    _reviewed_prompt("d25_prompt", anchors=("d25_extra_jobs",)),
    _reviewed_prompt("d26_prompt"),
    _reviewed_prompt(
        "d27_prompt", anchors=("d25_extra_jobs", "d26_occupation_context")
    ),
    _reviewed_prompt("d28_prompt"),
    _reviewed_prompt(
        "d29_prompt", anchors=("d25_extra_jobs", "d29_exposure_context")
    ),
    _reviewed_prompt(
        "d30_prompt", anchors=("d25_extra_jobs", "d30_exposure_context")
    ),
    _reviewed_prompt(
        "e1_prompt",
        purposes=("job_identifier",),
        anchors=("e_section_context", "e1_prospective_job"),
    ),
    _reviewed_prompt("e2_prompt"),
    _reviewed_prompt(
        "e6_prompt",
        purposes=("occupation",),
        anchors=("e6_last_job", "e6_occupation_context"),
    ),
    _reviewed_prompt("e7_prompt"),
    _byte(
        "e9_prompt",
        8,
        1157,
        1209,
        purposes=("month_or_exposure",),
        anchors=("e6_last_job", "e9_exposure_context"),
    ),
    _reviewed_prompt("e10_prompt"),
    _reviewed_prompt("e11_prompt"),
    _reviewed_prompt("e12_prompt"),
    _reviewed_prompt(
        "f1_prompt", anchors=("f1_head", "f1_assignment_context")
    ),
    _reviewed_prompt(
        "f3_prompt",
        purposes=("occupation",),
        anchors=("f1_head", "f3_occupation_job", "f3_occupation_context"),
    ),
    _reviewed_prompt("f4_prompt"),
    _reviewed_prompt("f5_prompt"),
    _reviewed_prompt("f6_prompt"),
    _reviewed_prompt(
        "f8_prompt",
        purposes=("job_identifier",),
        anchors=("f1_head", "f8_prospective_job"),
    ),
    _reviewed_prompt("f9_prompt"),
    _reviewed_prompt(
        "f14_prompt", anchors=("f13_available_jobs", "f14_pay_component")
    ),
    _reviewed_prompt("g13_prompt"),
    _reviewed_prompt(
        "g14_prompt", anchors=("g13_wife", "g14_exposure_context")
    ),
    _reviewed_prompt(
        "g15_prompt", anchors=("g13_wife", "g15_exposure_context")
    ),
    _byte(
        "h1_prompt",
        15,
        517,
        553,
        purposes=("assignment",),
        anchors=("h1_farm_aggregate",),
    ),
    _reviewed_prompt("h2_prompt"),
    _reviewed_prompt("h3_prompt"),
    _reviewed_prompt("h4_prompt"),
    _reviewed_prompt(
        "h5_prompt",
        anchors=("h5_business_primary", "h5_business_enterprise"),
    ),
    _byte(
        "h6_prompt",
        15,
        1995,
        2152,
        purposes=("incorporation",),
        anchors=(
            "h5_business_primary",
            "h6_incorporation_context",
        ),
    ),
    _reviewed_prompt(
        "h7_prompt",
        anchors=(
            "h5_business_primary",
            "h7_business_aggregate",
            "h7_business_component",
        ),
    ),
    _reviewed_prompt("h8_prompt"),
    _reviewed_prompt("h9_prompt"),
    _reviewed_prompt("h10_prompt"),
    _reviewed_prompt(
        "h11_header_prompt",
        anchors=(
            "h11_head",
            "h11a_business_aggregate",
            "h11b_farm_aggregate",
            "h11b_business_aggregate",
        ),
    ),
    _needle(
        "h11a_prompt",
        16,
        "professional practice  or trade?",
        purposes=("assignment",),
        anchors=("h11_head", "h11a_business_aggregate"),
    ),
    _byte(
        "h11a_amount_prompt",
        16,
        488,
        507,
        purposes=("amount", "reporting_unit"),
        anchors=("h11_head", "h11a_business_aggregate"),
    ),
    _byte(
        "h11b_farm_prompt",
        16,
        577,
        605,
        purposes=("assignment",),
        anchors=("h11_head", "h11b_farm_aggregate"),
    ),
    _byte(
        "h11b_business_prompt",
        16,
        646,
        666,
        purposes=("assignment",),
        anchors=("h11_head", "h11b_business_aggregate"),
    ),
    _byte(
        "h11b_amount_prompt",
        16,
        692,
        711,
        purposes=("amount", "reporting_unit"),
        anchors=(
            "h11_head",
            "h11b_farm_aggregate",
            "h11b_business_aggregate",
        ),
    ),
    _reviewed_prompt("h17_prompt", anchors=("h17_head", "h17_wife")),
    _reviewed_prompt("h18_prompt"),
    _reviewed_prompt("h19_prompt"),
    _reviewed_prompt("h20_prompt"),
)


def _flow(
    key: str,
    page: int,
    start: int,
    end: int,
    parent: str | None = None,
) -> dict[str, Any]:
    return _byte(
        key,
        page,
        start,
        end,
        kind="flow_branch_label",
        parent=parent,
    )


# Complete pinned-text control flow.  Same-span rows are intentional when one
# printed label has multiple complete parent paths.
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _flow("p2_ask_everyone", 2, 282, 296),
    _flow("p2_b1_yes", 2, 520, 521),
    _flow("p2_b1_no_b3", 2, 546, 571),
    _flow("p2_b3_yes_b6", 2, 1058, 1102),
    _flow("p2_b4_no_c1", 2, 1523, 1567),
    _flow("p2_b5_turn_c1", 2, 2304, 2367),
    _flow("p2_b6_turn_c1", 2, 2999, 3045, "p2_b3_yes_b6"),
    _flow("p4_working_entry", 4, 348, 364),
    _flow("p4_turn_e", 4, 625, 649),
    _flow("p4_other_has_job", 4, 975, 1101),
    _flow("p4_turn_f", 4, 1341, 1352),
    _flow("p4_if_not_clear_work", 4, 1745, 1759, "p4_working_entry"),
    _flow("p4_if_not_clear_other", 4, 1745, 1759, "p4_other_has_job"),
    _flow("p4_ge_year_work", 4, 2254, 2306, "p4_working_entry"),
    _flow("p4_ge_year_other", 4, 2254, 2306, "p4_other_has_job"),
    _flow("p4_lt_year_work", 4, 2329, 2350, "p4_working_entry"),
    _flow("p4_lt_year_other", 4, 2329, 2350, "p4_other_has_job"),
    _flow("p4_d9_turn_work", 4, 2934, 2975, "p4_lt_year_work"),
    _flow("p4_d9_turn_other", 4, 2934, 2975, "p4_lt_year_other"),
    _flow("p6_d25_yes_work", 6, 272, 275, "p4_working_entry"),
    _flow("p6_d25_yes_other", 6, 272, 275, "p4_other_has_job"),
    _flow("p6_d25_no_work", 6, 304, 324, "p4_working_entry"),
    _flow("p6_d25_no_other", 6, 304, 324, "p4_other_has_job"),
    _flow("p6_d31_yes_work", 6, 1547, 1572, "p4_working_entry"),
    _flow("p6_d31_yes_other", 6, 1547, 1572, "p4_other_has_job"),
    _flow("p6_d31_no_work", 6, 1593, 1619, "p4_working_entry"),
    _flow("p6_d31_no_other", 6, 1593, 1619, "p4_other_has_job"),
    _flow("p6_d32_yes_work", 6, 2061, 2090, "p6_d31_no_work"),
    _flow("p6_d32_yes_other", 6, 2061, 2090, "p6_d31_no_other"),
    _flow("p6_d32_no_work", 6, 2173, 2189, "p6_d31_no_work"),
    _flow("p6_d32_no_other", 6, 2173, 2189, "p6_d31_no_other"),
    _flow("p6_d33_yes_direct_work", 6, 2386, 2417, "p6_d31_yes_work"),
    _flow("p6_d33_yes_direct_other", 6, 2386, 2417, "p6_d31_yes_other"),
    _flow("p6_d33_yes_via_d32_work", 6, 2386, 2417, "p6_d32_no_work"),
    _flow("p6_d33_yes_via_d32_other", 6, 2386, 2417, "p6_d32_no_other"),
    _flow("p6_d33_no_direct_work", 6, 2427, 2436, "p6_d31_yes_work"),
    _flow("p6_d33_no_direct_other", 6, 2427, 2436, "p6_d31_yes_other"),
    _flow("p6_d33_no_via_d32_work", 6, 2427, 2436, "p6_d32_no_work"),
    _flow("p6_d33_no_via_d32_other", 6, 2427, 2436, "p6_d32_no_other"),
    _flow("p8_section_e", 8, 97, 153, "p4_turn_e"),
    _flow("p8_nothing_e6", 8, 519, 544, "p8_section_e"),
    _flow("p8_zero_e11", 8, 1248, 1274, "p8_section_e"),
    _flow("p10_section_f", 10, 267, 333),
    _flow("p10_f2_yes", 10, 615, 643, "p10_section_f"),
    _flow("p10_f2_no", 10, 657, 692, "p10_section_f"),
    _flow("p10_f7_yes", 10, 1400, 1426, "p10_section_f"),
    _flow("p10_f7_no", 10, 1445, 1486, "p10_section_f"),
    _flow("p10_if_yes_f2", 10, 1514, 1537, "p10_f2_yes"),
    _flow("p10_if_yes_f7", 10, 1514, 1537, "p10_f7_yes"),
    _flow("p10_nothing_f2", 10, 2002, 2027, "p10_if_yes_f2"),
    _flow("p10_nothing_f7", 10, 2002, 2027, "p10_if_yes_f7"),
    _flow("p10_f13_yes_f2", 10, 2485, 2491, "p10_if_yes_f2"),
    _flow("p10_f13_yes_f7", 10, 2485, 2491, "p10_if_yes_f7"),
    _flow("p10_f13_no_f2", 10, 2522, 2558, "p10_if_yes_f2"),
    _flow("p10_f13_no_f7", 10, 2522, 2558, "p10_if_yes_f7"),
    _flow("p10_turn_g_f2", 10, 2816, 2837, "p10_f13_yes_f2"),
    _flow("p10_turn_g_f7", 10, 2816, 2837, "p10_f13_yes_f7"),
    _flow("p12_g13_none", 12, 291, 323),
    _flow("p12_g14_all", 12, 536, 558),
    _flow("p12_children_yes", 12, 799, 800),
    _flow("p12_children_no", 12, 839, 889),
    _flow("p12_all_others", 12, 1252, 1274),
    _flow("p12_turn_g22", 12, 2558, 2580),
    _flow("p14_ask_everyone", 14, 71, 97),
    _flow("p14_two_plus", 14, 1062, 1088),
    _flow("p14_one_person", 14, 1100, 1165),
    _flow("p14_g38_yes", 14, 1315, 1319, "p14_two_plus"),
    _flow("p14_g38_no", 14, 1342, 1379, "p14_two_plus"),
    _flow("p14_g41_yes", 14, 2056, 2083, "p14_g38_yes"),
    _flow("p14_g41_no", 14, 2097, 2136, "p14_g38_yes"),
    _flow("p15_ask_everyone_1", 15, 286, 300),
    _flow("p15_farmer", 15, 517, 553),
    _flow("p15_not_farmer", 15, 621, 661),
    _flow("p15_h5_yes", 15, 1913, 1919),
    _flow("p15_h5_no", 15, 1946, 1970),
    _flow("p15_h6_corporation", 15, 2182, 2210, "p15_h5_yes"),
    _flow("p15_h6_unincorporated", 15, 2239, 2259, "p15_h5_yes"),
    _flow("p15_h6_both", 15, 2337, 2344, "p15_h5_yes"),
    _flow("p15_h6_dont_know", 15, 2361, 2390, "p15_h5_yes"),
    _flow("p15_ask_everyone_2", 15, 2938, 2952),
    _flow("p16_h9_yes", 16, 214, 219),
    _flow("p16_h9_no", 16, 243, 260),
    _flow("p16_if_yes_any", 16, 415, 431),
    _flow("p16_if_no", 16, 933, 941),
    _flow("p16_h12_yes", 16, 2246, 2252),
    _flow("p16_h12_no", 16, 2270, 2298),
    _flow("p17_welfare_yes", 17, 227, 261),
    _flow("p17_no_welfare", 17, 278, 308),
    _flow("p17_h15_yes", 17, 464, 472, "p17_welfare_yes"),
    _flow("p17_h15_no", 17, 480, 498, "p17_welfare_yes"),
    _flow("p17_h17_yes", 17, 641, 660),
    _flow("p17_h17_no", 17, 667, 729),
    _flow("p17_h18_yes", 17, 818, 825, "p17_h17_yes"),
    _flow("p17_h18_no", 17, 837, 866, "p17_h17_yes"),
    _flow("p18_no_people", 18, 306, 357),
    _flow("p18_h22_yes", 18, 613, 619),
    _flow("p18_h22_no", 18, 625, 641),
    _flow("p18_if_wages_business", 18, 1285, 1304, "p18_h22_yes"),
    _flow("p18_if_dont_know", 18, 1806, 1821, "p18_if_wages_business"),
    _flow("p18_h29_yes", 18, 2021, 2027, "p18_h22_yes"),
    _flow("p18_h29_no", 18, 2033, 2049, "p18_h22_yes"),
    _flow("p19_top1_yes", 19, 249, 255),
    _flow("p19_top1_no", 19, 260, 276),
    _flow("p19_top2_yes", 19, 280, 286),
    _flow("p19_top2_no", 19, 296, 312),
    _flow("p19_top3_yes", 19, 321, 326),
    _flow("p19_top3_no", 19, 332, 348),
    _flow("p19_bottom1_yes", 19, 1181, 1187),
    _flow("p19_bottom1_no", 19, 1195, 1207),
    _flow("p19_bottom2_yes", 19, 1212, 1218),
    _flow("p19_bottom2_no", 19, 1230, 1242),
    _flow("p19_bottom3_yes", 19, 1253, 1259),
    _flow("p19_bottom3_no", 19, 1266, 1278),
    _flow("p19_turn_h32", 19, 1679, 1701),
    _flow("p20_ask_everyone", 20, 101, 115),
    _flow("p20_h32_yes", 20, 304, 314),
    _flow("p20_h32_no", 20, 344, 364),
    _flow("p20_h34_yes", 20, 842, 844),
    _flow("p20_h34_no", 20, 872, 901),
    _flow("p20_h36_yes", 20, 1242, 1248),
    _flow("p20_h36_no", 20, 1268, 1295),
    _flow("p20_h39_yes", 20, 1695, 1696, "p20_h36_yes"),
    _flow("p20_h39_no", 20, 1722, 1749, "p20_h36_yes"),
    _flow("p24_turn_cover_1", 24, 369, 400),
    _flow("p24_turn_cover_2", 24, 741, 772),
)


OCCURRENCE_PATH_OVERRIDES: dict[str, tuple[str, ...]] = {
    **{
        key: ("p4_working_entry", "p4_other_has_job")
        for key in (
            "d2_occupation_context",
            "d4_industry_context",
            "d5_employee_context",
            "d6_exposure_context",
            "d2_prompt",
            "d4_prompt",
            "d5_prompt",
            "d6_prompt",
            "d25_extra_jobs",
            "d25_prompt",
        )
    },
    **{
        key: ("p6_d25_yes_work", "p6_d25_yes_other")
        for key in (
            "d26_occupation_context",
            "d28_hourly_component",
            "d29_exposure_context",
            "d30_exposure_context",
            "d26_prompt",
            "d27_prompt",
            "d28_prompt",
            "d29_prompt",
            "d30_prompt",
        )
    },
    **{
        key: ("p8_section_e",)
        for key in (
            "e_section_context",
            "e1_prospective_job",
            "e2_expected_component",
            "e6_last_job",
            "e6_occupation_context",
            "e7_industry_context",
            "e9_exposure_context",
            "e10_exposure_context",
            "e11_exposure_context",
            "e12_exposure_context",
            "e1_prompt",
            "e2_prompt",
            "e6_prompt",
            "e7_prompt",
            "e9_prompt",
            "e10_prompt",
            "e11_prompt",
            "e12_prompt",
        )
    },
    **{
        key: ("p10_section_f",)
        for key in (
            "f_section_context",
            "f1_head",
            "f1_assignment_context",
            "f3_occupation_job",
            "f3_occupation_context",
            "f4_industry_context",
            "f5_exposure_context",
            "f6_exposure_context",
            "f1_prompt",
            "f3_prompt",
            "f4_prompt",
            "f5_prompt",
            "f6_prompt",
        )
    },
    **{
        key: ("p10_if_yes_f2", "p10_if_yes_f7")
        for key in (
            "f8_prospective_job",
            "f9_expected_component",
            "f13_available_jobs",
            "f8_prompt",
            "f9_prompt",
        )
    },
    **{
        key: ("p10_f13_yes_f2", "p10_f13_yes_f7")
        for key in ("f14_pay_component", "f14_prompt")
    },
    **{
        key: ("p15_farmer",)
        for key in (
            "h1_farm_aggregate",
            "h2_farming_aggregate",
            "h2_farm_component",
            "h3_farm_expense_component",
            "h4_farm_net_component",
            "h4_farming_aggregate",
            "h1_prompt",
            "h2_prompt",
            "h3_prompt",
            "h4_prompt",
        )
    },
    **{
        key: ("p15_h5_yes",)
        for key in (
            "h6_incorporation_context",
            "h6_prompt",
        )
    },
    **{
        key: (
            "p15_h6_unincorporated",
            "p15_h6_both",
            "p15_h6_dont_know",
        )
        for key in (
            "h7_business_aggregate",
            "h7_business_component",
            "h7_prompt",
        )
    },
    "h10_prompt": ("p16_h9_yes",),
    **{
        key: ("p16_if_yes_any",)
        for key in ("h11a_amount_prompt", "h11b_amount_prompt")
    },
    "h17_female_head": ("p17_h17_no",),
    "h17_yes_wife": ("p17_h17_yes",),
    **{key: ("p17_h17_yes",) for key in ("h18_wife", "h18_prompt")},
    **{
        key: ("p17_h18_yes",)
        for key in (
            "h19_wife_role_total",
            "h19_wage_component",
            "h19_business_aggregate",
            "h19_prompt",
            "h20_prompt",
        )
    },
    "h33_repeat": ("p20_h32_yes",),
}


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
        "filename": "q74.pdf",
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
    specs: list[dict[str, Any]] = []
    specs.extend(copy.deepcopy(FLOW_SPECS))
    specs.extend(copy.deepcopy(ANCHOR_SPECS))
    specs.extend(
        {**copy.deepcopy(spec), "kind": "field_purpose_prompt"}
        for spec in PROMPT_SPECS
    )
    specs.extend(
        {**copy.deepcopy(spec), "kind": "repeat_or_alias_instruction"}
        for spec in REPEAT_SPECS
    )
    keys = [spec["key"] for spec in specs]
    if len(keys) != len(set(keys)):
        raise ValueError("review specification key collision")
    anchor_keys = {spec["key"] for spec in ANCHOR_SPECS}
    for spec in ANCHOR_SPECS:
        missing = set(spec.get("parents", ())) - anchor_keys
        if missing:
            raise ValueError(f"unresolved local anchor parents: {missing}")
    for spec in PROMPT_SPECS:
        missing = set(spec["anchors"]) - anchor_keys
        if missing:
            raise ValueError(f"unresolved prompt anchors: {missing}")

    rows: list[dict[str, Any]] = []
    for spec in specs:
        page = spec["page"]
        start, end = _resolve_span(page_texts[page - 1], spec)
        matched, matched_sha256 = _strict_slice(
            page_texts[page - 1], start, end, spec["key"]
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

    occurrences: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    occurrence_id_by_key: dict[str, str] = {}
    branch_by_key: dict[str, dict[str, Any]] = {}
    page_indices: Counter[int] = Counter()
    atom_coordinates: set[tuple[Any, ...]] = set()

    for group in sorted(items_by_group):
        group_items = items_by_group[group]
        kind = group_items[0]["kind"]
        if kind != "flow_branch_label" and len(group_items) != 1:
            raise ValueError("duplicate non-flow atomic occurrence")

        prepared: list[tuple[list[str], dict[str, Any]]] = []
        for item in group_items:
            if kind == "flow_branch_label":
                parent_key = item["parent"]
                if parent_key is None:
                    parent_path = [FLOW_ROOT]
                else:
                    if parent_key not in branch_by_key:
                        raise ValueError(
                            f"later or unresolved flow parent {parent_key}"
                        )
                    parent_path = branch_by_key[parent_key]["branch_path"]
                prepared.append((parent_path, item))
            else:
                path_keys = OCCURRENCE_PATH_OVERRIDES.get(
                    item["key"], ("root",)
                )
                paths = []
                for path_key in path_keys:
                    if path_key == "root":
                        paths.append([FLOW_ROOT])
                    elif path_key in branch_by_key:
                        paths.append(branch_by_key[path_key]["branch_path"])
                    else:
                        raise ValueError(
                            f"unresolved occurrence flow path {path_key}"
                        )
                unique_paths = {tuple(path) for path in paths}
                if len(unique_paths) != len(paths):
                    raise ValueError("duplicate occurrence flow path")
                prepared.append(
                    (
                        [],
                        {
                            **item,
                            "resolved_paths": sorted(
                                paths, key=_path_sort_key
                            ),
                        },
                    )
                )
        if kind == "flow_branch_label":
            prepared.sort(key=lambda pair: _path_sort_key(pair[0]))

        for ordinal, (parent_path, item) in enumerate(prepared):
            semantic_ordinal = ordinal if len(prepared) > 1 else 0
            flow_paths = (
                [list(parent_path)]
                if kind == "flow_branch_label"
                else item["resolved_paths"]
            )
            index_on_page = page_indices[item["page"]]
            page_indices[item["page"]] += 1
            row = _occurrence_row(
                item,
                locator_id,
                index_on_page,
                semantic_ordinal,
                flow_paths,
            )
            coordinate = (
                item["page"],
                item["utf8_byte_start"],
                item["utf8_byte_end"],
                kind,
                semantic_ordinal,
            )
            if coordinate in atom_coordinates:
                raise ValueError("duplicate occurrence coordinate")
            atom_coordinates.add(coordinate)
            occurrences.append(row)
            occurrence_id_by_key[item["key"]] = row[
                "questionnaire_occurrence_id"
            ]

            if kind == "flow_branch_label":
                parent_id = parent_path[-1]
                branch_id = "questionnaire-flow:" + _digest(
                    [
                        parent_id,
                        INTERVIEW_WAVE,
                        row["questionnaire_occurrence_id"],
                    ]
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
                    "occurrence_index_on_page": index_on_page,
                    "branch_label": item["matched_text"],
                    "branch_label_sha256": item["matched_utf8_sha256"],
                }
                branches.append(branch)
                branch_by_key[item["key"]] = branch

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
    rows: list[dict[str, Any]] = []
    for spec in ANCHOR_SPECS:
        occurrence_id = occurrence_id_by_key[spec["key"]]
        occurrence = occurrence_by_id[occurrence_id]
        identifier, identifier_span = _identifier_slice(
            spec, page_texts[spec["page"] - 1]
        )
        parent_ids = [
            occurrence_id_by_key[key] for key in spec.get("parents", ())
        ]
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
    return rows


def _purpose_rows(
    occurrence_id_by_key: Mapping[str, str],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in PROMPT_SPECS:
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
    return rows


def _repeat_rows(
    page_texts: Sequence[str],
    occurrence_id_by_key: Mapping[str, str],
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in REPEAT_SPECS:
        instruction_id = occurrence_id_by_key[spec["key"]]
        start, end = _needle_span(page_texts[spec["page"] - 1], spec["target"])
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
        evidence_ids = [instruction_id]
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
                "evidence_occurrence_ids": evidence_ids,
                "handoff_status": spec["handoff"],
                "annotation_status": "complete",
            }
        )
    for spec in SAME_LABEL_ALIAS_SPECS:
        canonical_id = occurrence_id_by_key[spec["canonical_anchor"]]
        alias_id = occurrence_id_by_key[spec["alias_anchor"]]
        canonical = occurrence_by_id[canonical_id]
        alias = occurrence_by_id[alias_id]
        anchor_specs = {row["key"]: row for row in ANCHOR_SPECS}
        canonical_spec = anchor_specs[spec["canonical_anchor"]]
        alias_spec = anchor_specs[spec["alias_anchor"]]
        if (
            canonical["matched_text"] != alias["matched_text"]
            or canonical_spec.get("identifier") is None
            or canonical_spec.get("identifier") != alias_spec.get("identifier")
            or canonical_spec["classification"] != alias_spec["classification"]
        ):
            raise ValueError(
                "same-label alias identifier, label, or class is not exact"
            )
        evidence_ids = sorted(
            (canonical_id, alias_id),
            key=lambda occurrence_id: (
                occurrence_by_id[occurrence_id]["page_number"],
                occurrence_by_id[occurrence_id]["occurrence_index_on_page"],
            ),
        )
        preimage = [
            "same_printed_identifier_and_exact_label",
            alias_id,
            canonical_id,
            evidence_ids,
        ]
        rows.append(
            {
                "local_repeat_evidence_id": (
                    "rq-local-repeat-evidence:" + _digest(preimage)
                ),
                "alias_relation": "same_printed_identifier_and_exact_label",
                "alias_anchor_occurrence_id": alias_id,
                "referenced_anchor_occurrence_id": canonical_id,
                "source_instruction_occurrence_ids": [],
                "unresolved_target_reference": None,
                "evidence_occurrence_ids": evidence_ids,
                "handoff_status": (
                    "local_exact_identifier_and_label_for_global_assembly"
                ),
                "annotation_status": "complete",
            }
        )
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
    result: dict[str, list[str]] = {}
    for candidate in candidate_rows:
        same_kind = [
            row
            for row in output_rows
            if row["page_number"] == candidate["page_number"]
            and row["occurrence_kind"]
            == candidate["occurrence_kind_candidate"]
            and _overlaps(
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                candidate["utf8_byte_start"],
                candidate["utf8_byte_end"],
            )
        ]
        targets = same_kind
        if not targets and candidate["occurrence_kind_candidate"] in {
            "business_aggregate_anchor",
        }:
            # Manual semantic corrections: industry wording is context, and
            # corporation status is incorporation context rather than a
            # separate business aggregate.
            targets = [
                row
                for row in output_rows
                if row["page_number"] == candidate["page_number"]
                and row["occurrence_kind"] == "context_anchor"
                and _overlaps(
                    row["utf8_byte_start"],
                    row["utf8_byte_end"],
                    candidate["utf8_byte_start"],
                    candidate["utf8_byte_end"],
                )
            ]
        if (
            not targets
            and candidate["occurrence_kind_candidate"]
            == "business_aggregate_anchor"
            and candidate["page_number"] == 15
            and candidate["utf8_byte_start"] == 2245
            and candidate["utf8_byte_end"] == 2259
        ):
            # H6's uppercase UNINCORPORATED answer was detected as an
            # aggregate.  Its actual semantics are the containing flow label.
            targets = [
                row
                for row in output_rows
                if row["page_number"] == candidate["page_number"]
                and row["occurrence_kind"] == "flow_branch_label"
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
        elif dispositions == {"modified"}:
            action = "candidate_modified"
        elif dispositions == {"split"} and len(source_ids) == 1:
            action = "candidate_split"
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
    """Build document 14 from pinned source bytes and explicit decisions."""

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
        raise ValueError("document-14 independently replayed identity drift")

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
    """Validate every stage-2 document-14 source and sealing invariant."""

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
    if len(dispositions) != 648:
        raise ValueError("document-14 candidate denominator drift")
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-14 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 14: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
