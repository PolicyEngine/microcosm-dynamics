#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for fam1997_QxQs.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 64-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

fam1997_QxQs.pdf is the 1997 question-by-question objectives manual: printed
interviewer instructions keyed to questionnaire item identifiers rather than a
printed questionnaire.  The retention test applied throughout is therefore
whether the printed text *establishes* a document-local R_Q fact for a named
item or item series -- a role attachment, a job slot, a remuneration
component, an aggregate, a retained contextual field, a field purpose, a
controlling condition, or an explicit repeat/cross-reference.  Narrative
procedure, probing examples, and non-employment subject matter are rejected
even where they carry work-like lexemes.
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
DOCUMENT_POSITION = 58
DOCUMENT_ID = (
    "psid-source-document:"
    "8116b39adb145810c342c96762405313e2d6df7d9bd77c9bf7c6558eefdf1871"
)
INTERVIEW_WAVE = 1997
CANONICAL_SOURCE_PATH = "documentation/capture1/fam1997_QxQs.pdf"
PDF_FILENAME = "fam1997_QxQs.pdf"
PDF_SIZE = 245_438
PDF_SHA256 = "ab811c94728f420f86d2a660599d3f2cb62d460b0da30e8f634642243a60bddc"
PAGE_COUNT = 64
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_06_documents_051_060"
    / "document_058_fam1997_QxQs_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_058_fam1997_QxQs_annotation_v1.json"
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
    "9fcb3566766f316f81fffcd68600c836f77df42450c768c1849d577e73bd7efe"
)
CANDIDATE_CONTENT_SHA256 = (
    "61bb7bcf5abe475b38b9a2c86698912e96ba2e7b68013124e30c093cd5cad16a"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "81213ca6059d12e208c9d54c6ae2f313e20cde433c5547ffef478ed411510bd7"
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

NODE_DOMAINS = {
    "role_anchor": ("role", None),
    "job_anchor": ("job_slot", "source_job"),
    "remuneration_component_anchor": (
        "component_slot",
        "source_remuneration_component",
    ),
    "role_total_anchor": ("aggregate", "role_total"),
    "farm_aggregate_anchor": ("aggregate", "farm_aggregate"),
    "business_aggregate_anchor": ("aggregate", "business_aggregate"),
    "context_anchor": ("component_slot", "source_context"),
}


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
        raise ValueError("document-58 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-58 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-58 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-58 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / PDF_FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1997_QxQs.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("fam1997_QxQs.pdf page-count drift")
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
        raise ValueError("document-58 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-58 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-58 empty-text page domain drift")
    return rows


def _line_char_spans(page_text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    offset = 0
    for raw_line in page_text.splitlines(keepends=True):
        line = raw_line[:-1] if raw_line.endswith("\n") else raw_line
        if line.endswith("\r"):
            line = line[:-1]
        spans.append((offset, offset + len(line), line))
        offset += len(raw_line)
    return spans


def _byte_span(page_text: str, start_chars: int, end_chars: int) -> tuple:
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _unique_line(page_text: str, marker: str) -> tuple[int, int, str]:
    matches = [
        (start, end, line)
        for start, end, line in _line_char_spans(page_text)
        if marker in line
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one physical line containing {marker!r}")
    return matches[0]


def _trimmed_line_span(page_text: str, marker: str) -> tuple[int, int]:
    start, _, line = _unique_line(page_text, marker)
    left = len(line) - len(line.lstrip(" \t"))
    right = len(line.rstrip(" \t"))
    return _byte_span(page_text, start + left, start + right)


def _block_span(
    page_text: str, start_marker: str, end_marker: str | None = None
) -> tuple[int, int]:
    spans = _line_char_spans(page_text)
    start_rows = [
        index
        for index, (_, _, line) in enumerate(spans)
        if start_marker in line
    ]
    end_marker = start_marker if end_marker is None else end_marker
    end_rows = [
        index for index, (_, _, line) in enumerate(spans) if end_marker in line
    ]
    if (
        len(start_rows) != 1
        or len(end_rows) != 1
        or end_rows[0] < start_rows[0]
    ):
        raise ValueError(
            f"invalid unique block markers {start_marker!r}, {end_marker!r}"
        )
    first_start, _, first = spans[start_rows[0]]
    last_start, _, last = spans[end_rows[0]]
    left = len(first) - len(first.lstrip(" \t"))
    right = len(last.rstrip(" \t"))
    return _byte_span(page_text, first_start + left, last_start + right)


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
    return _byte_span(page_text, start_chars, start_chars + len(needle))


def _inline_span(
    page_text: str, line_marker: str, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    line_start, line_end, line = _unique_line(page_text, line_marker)
    starts: list[int] = []
    cursor = 0
    while True:
        found = line.find(needle, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    if occurrence < 0 or occurrence >= len(starts):
        raise ValueError(
            f"missing inline needle {needle!r} in line {line_marker!r}"
        )
    start_chars = line_start + starts[occurrence]
    end_chars = start_chars + len(needle)
    if end_chars > line_end:
        raise ValueError(f"inline needle {needle!r} overruns its line")
    return _byte_span(page_text, start_chars, end_chars)


def _resolve_span(page_text: str, spec: Mapping[str, Any]) -> tuple[int, int]:
    if "utf8_byte_start" in spec:
        return spec["utf8_byte_start"], spec["utf8_byte_end"]
    if "inline_marker" in spec:
        return _inline_span(
            page_text,
            spec["inline_marker"],
            spec["needle"],
            spec.get("needle_occurrence", 0),
        )
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
    key: str, page: int, start_marker: str, end_marker: str, **values: Any
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


def _inline(
    key: str, page: int, line_marker: str, needle: str, **values: Any
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "inline_marker": line_marker,
        "needle": needle,
        **values,
    }


# ---------------------------------------------------------------------------
# Reviewer decisions.  These are not detector rules: each selector names text
# read during the complete 64-page pass and is re-resolved against the
# authenticated fam1997_QxQs.pdf bytes.
# ---------------------------------------------------------------------------

# Controlling flow.  A branch is retained only where printed text states a
# condition that determines whether a retained R_Q item series is asked.
# Advisory conditionals inside a single item ("if R does not know, estimate")
# are rejected as noncontrolling flow text.
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _line(
        "f_bscope", 12, "Sections B and C apply to the current Head of the FU"
    ),
    _line(
        "f_b1_working",
        12,
        "NOW or 2. TEMPORARILY OFF from work, ask B4",
        parent="f_bscope",
    ),
    _line(
        "f_b1_codes38",
        12,
        "If only CODES 3-8 are checked and B3 is YES",
        parent="f_bscope",
    ),
    _line("f_b1_no", 12, "if B3 is NO, GO TO Section C.", parent="f_bscope"),
    _line(
        "f_whs",
        20,
        "If Head had any other main-job employers during 1996",
        parent="f_bscope",
    ),
    _line("f_weeks", 22, "NOTE: ASK B60-78 FOR ALL HEADS!", parent="f_bscope"),
    _needle(
        "f_sectionc",
        27,
        'Section C--Head Is Not Working Now at B1 ("No" to B3)',
        parent="f_b1_no",
    ),
    _line("f_descope", 28, "Sections D and E apply to current Wife or"),
    _line(
        "f_d1route",
        28,
        "The D1 checkpoint routes all Female Heads",
        parent="f_descope",
    ),
    _block(
        "f_f2_route",
        29,
        "If roomers or boarders are living in the HU",
        'Wife/"Wife"). If R is unable to separate the time',
    ),
    _block(
        "f_g_workincome",
        31,
        'If Head or Wife/"Wife" reports work income in Section G',
        "reported in Section B/C or D/E.",
    ),
    _block(
        "f_g_workhours",
        31,
        'If Head or Wife/"Wife" reports working during 1996',
        "those hours must be reported in Section G.",
    ),
    _line("f_k_new", 56, '1. NEW WIFE OR "WIFE" IN FU THIS YEAR - ASK K2-K66'),
    _line("f_k_same", 56, '2. SAME WIFE OR "WIFE" IN FU THIS YEAR AND LAST'),
    _line("f_k_newsample", 56, '1. WIFE OR "WIFE" IN FU - ASK K2-K66'),
    _line("f_l_new", 59, "1. NEW HEAD IN FU THIS YEAR - ASK L2-L74"),
    _line(
        "f_l_same", 59, "5. SAME HEAD IN FU THIS YEAR AND LAST - ASK L75-L101"
    ),
    _line("f_l_newsample", 59, "and you MUST ASK L2-L74."),
    _line(
        "f_mscope", 61, "This section is asked in New Sample interviews only."
    ),
    _line("f_m_lastjob", 61, "you are skipped to M23.", parent="f_mscope"),
)

ROOT_PATH = ("root",)
P_BSCOPE = (("root", "f_bscope"),)
P_BMAIN = (
    ("root", "f_bscope", "f_b1_working"),
    ("root", "f_bscope", "f_b1_codes38"),
)
P_WHS = (("root", "f_bscope", "f_whs"),)
P_WEEKS = (("root", "f_bscope", "f_weeks"),)
P_SECTIONC = (("root", "f_bscope", "f_b1_no", "f_sectionc"),)
P_DE = (("root", "f_descope"),)
P_ROOT = (("root",),)
P_KNEW = (("root", "f_k_new"), ("root", "f_k_newsample"))
P_KSAME = (("root", "f_k_same"),)
P_LNEW = (("root", "f_l_new"), ("root", "f_l_newsample"))
P_LSAME = (("root", "f_l_same"),)
P_M = (("root", "f_mscope"),)
P_MLAST = (("root", "f_mscope", "f_m_lastjob"),)


def _anchor(
    key: str,
    page: int,
    kind: str,
    selector: Mapping[str, Any],
    *,
    classification: str | None = None,
    identifier: str | None = None,
    parents: tuple[str, ...] = (),
    paths: tuple[tuple[str, ...], ...] = P_ROOT,
) -> dict[str, Any]:
    domain, default_class = NODE_DOMAINS[kind]
    resolved = classification if classification is not None else default_class
    if resolved is None:
        raise ValueError(f"anchor {key} needs an explicit classification")
    return {
        "key": key,
        "page": page,
        "kind": kind,
        "node_domain": domain,
        "classification": resolved,
        "identifier": identifier,
        "parents": parents,
        "paths": paths,
        **{k: v for k, v in selector.items() if k not in {"key", "page"}},
    }


def _mark(marker: str) -> dict[str, Any]:
    return {"line_marker": marker}


def _at(needle: str, occurrence: int = 0) -> dict[str, Any]:
    return {"needle": needle, "needle_occurrence": occurrence}


def _in(marker: str, needle: str, occurrence: int = 0) -> dict[str, Any]:
    return {
        "inline_marker": marker,
        "needle": needle,
        "needle_occurrence": occurrence,
    }


def _span(start_marker: str, end_marker: str) -> dict[str, Any]:
    return {"start_marker": start_marker, "end_marker": end_marker}


HEAD = "head_or_reference_person"
SPOUSE = "spouse_or_partner"

# Standalone role, job, and aggregate anchors: the printed lexeme that names
# the node, following the doc-14 convention of short establishing spans.
STANDALONE_ANCHORS: tuple[dict[str, Any], ...] = (
    _anchor("r_b_head", 12, "role_anchor", _at("Head"), classification=HEAD),
    _anchor(
        "r_b13_head",
        13,
        "role_anchor",
        _in("Note: B4-B59 refer to", "Head's"),
        classification=HEAD,
        identifier="B4-B59",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b13_main_job",
        13,
        "job_anchor",
        _in("Note: B4-B59 refer to", "main job"),
        identifier="B4-B59",
        paths=P_BMAIN,
    ),
    _anchor(
        "a_b5_business",
        13,
        "business_aggregate_anchor",
        _in("Many self-employed people and professionals", "business"),
        identifier="B5.",
        paths=P_BMAIN,
    ),
    _anchor(
        "r_b9_head",
        14,
        "role_anchor",
        _in("Follow the guidelines below", "Head's"),
        classification=HEAD,
        identifier="B9-9a.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b9_main_job",
        14,
        "job_anchor",
        _in("Follow the guidelines below", "main job"),
        identifier="B9-9a.",
        paths=P_BMAIN,
    ),
    _anchor(
        "r_b1219_head",
        16,
        "role_anchor",
        _in("Questions B12, B13, B16, and B18", "Head's"),
        classification=HEAD,
        identifier="B12-19.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b20_another_job",
        17,
        "job_anchor",
        _in('"Another job" can mean a different position', "Another job"),
        identifier="B20.",
        paths=P_BMAIN,
    ),
    _anchor(
        "r_b23_head",
        17,
        "role_anchor",
        _in("Head's Work HistoryHead's Work History", "Head's"),
        classification=HEAD,
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b24_main_jobs",
        17,
        "job_anchor",
        _in("on main jobs about both changes in employer", "main jobs"),
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b82_extra_jobs",
        18,
        "job_anchor",
        _in("A quick definition of main vs. extra jobs", "extra jobs"),
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b24_employer",
        18,
        "job_anchor",
        _in(
            "Both B23 and B24 refer to the present employer",
            "present employer",
        ),
        identifier="B24.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b39_main_job",
        18,
        "job_anchor",
        _in("Mark the months of 1996 that Head worked", "main job"),
        identifier="B39.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b40_main_job_employer",
        18,
        "job_anchor",
        _in('If B40 is "NO", Head had no', "main job employer"),
        identifier="B40.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b42_main_job",
        19,
        "job_anchor",
        _in("There should be no overlap between B39 and B42", "main job"),
        identifier="B42a-42d",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b53_main_job",
        20,
        "job_anchor",
        _in("Since Head is currently employed on a different", "main job"),
        identifier="B53-55.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_whs_main_job_employers",
        20,
        "job_anchor",
        _in(
            "The questionnaire employment sections are designed",
            "main job employers",
        ),
        paths=P_WHS,
    ),
    _anchor(
        "r_s59_head",
        21,
        "role_anchor",
        _in("Complete one WHS for each additional employer", "Head"),
        classification=HEAD,
        identifier="S59.",
        paths=P_WHS,
    ),
    _anchor(
        "r_s59_wife",
        21,
        "role_anchor",
        _in("Complete one WHS for each additional employer", 'Wife/"Wife"'),
        classification=SPOUSE,
        identifier="S59.",
        paths=P_WHS,
    ),
    _anchor(
        "r_weeks_heads",
        22,
        "role_anchor",
        _in("NOTE: ASK B60-78 FOR ALL HEADS!", "HEADS"),
        classification=HEAD,
        paths=P_WEEKS,
    ),
    _anchor(
        "j_weeks_main_jobs",
        22,
        "job_anchor",
        _in("1. Separation of weeks into periods of work", "main job(s)"),
        paths=P_WEEKS,
    ),
    _anchor(
        "j_weeks_main_job_employment",
        22,
        "job_anchor",
        _in(
            "Work in these questions means simply and only",
            "main job employment",
        ),
        paths=P_WEEKS,
    ),
    _anchor(
        "j_b79_main_jobs",
        25,
        "job_anchor",
        _in(
            "This is the average hours per week on main job(s)", "main job(s)"
        ),
        identifier="B79.",
        paths=P_WEEKS,
    ),
    _anchor(
        "j_b82_extra_job",
        25,
        "job_anchor",
        _in("Main vs. Extra Job distinctions", "Extra Job"),
        identifier="B82.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b82_any_job",
        25,
        "job_anchor",
        _in("get more complete information on the kind(s) of work", "any job"),
        identifier="B82.",
        paths=P_BMAIN,
    ),
    _anchor(
        "a_b82_small_business",
        25,
        "business_aggregate_anchor",
        _in("that brought in income; examples include", "small business"),
        identifier="B82.",
        paths=P_BMAIN,
    ),
    _anchor(
        "a_b87_small_business",
        25,
        "business_aggregate_anchor",
        _in("Be sure to record the unit of time", "small business"),
        identifier="B87.",
        paths=P_BMAIN,
    ),
    _anchor(
        "j_b89_extra_job",
        25,
        "job_anchor",
        _in(
            "This is average hours per week for the weeks Head worked",
            "extra job",
        ),
        identifier="B89.",
        paths=P_BMAIN,
    ),
    _anchor(
        "r_c_head",
        27,
        "role_anchor",
        _in(
            'Section C--Head Is Not Working Now at B1 ("No" to B3)Section C',
            "Head",
        ),
        classification=HEAD,
        paths=P_SECTIONC,
    ),
    _anchor(
        "j_c16_last_job",
        27,
        "job_anchor",
        _in("employment history for the last job held", "the last job held"),
        identifier="C16-51.",
        paths=P_SECTIONC,
    ),
    _anchor(
        "r_de_wife",
        28,
        "role_anchor",
        _at('Wife/"Wife"'),
        classification=SPOUSE,
        paths=P_ROOT,
    ),
    _anchor(
        "r_g_head",
        31,
        "role_anchor",
        _in('If Head or Wife/"Wife" reports work income in Section G', "Head"),
        classification=HEAD,
    ),
    _anchor(
        "r_g_wife",
        31,
        "role_anchor",
        _in(
            'If Head or Wife/"Wife" reports work income in Section G',
            'Wife/"Wife"',
        ),
        classification=SPOUSE,
    ),
    _anchor(
        "a_g2_farm",
        31,
        "farm_aggregate_anchor",
        _in(
            "Receipts from normal farm operations include:", "farm operations"
        ),
        identifier="G2.",
    ),
    _anchor(
        "a_g3_farm",
        31,
        "farm_aggregate_anchor",
        _in("Farm operating expenses can include:", "Farm"),
        identifier="G3.",
    ),
    _anchor(
        "a_g4_farm",
        32,
        "farm_aggregate_anchor",
        _in("Farm income equals total receipts", "Farm"),
        identifier="G4.",
    ),
    _anchor(
        "a_g5_business",
        32,
        "business_aggregate_anchor",
        _in("Do not include stock ownership in G5", "any business"),
        identifier="G5-7a.",
    ),
    _anchor(
        "a_g10_business",
        32,
        "business_aggregate_anchor",
        _in("business in 1996, but R doesn't know whether", "business"),
        identifier="G10.",
    ),
    _anchor(
        "a_g11c_business",
        32,
        "business_aggregate_anchor",
        _in(
            "Attach an extra page or pages to record information for each additional business",
            "additional business",
        ),
        identifier="G11c.",
    ),
    _anchor(
        "r_g13_head",
        33,
        "role_anchor",
        _in("This question applies only to current Head", "Head"),
        classification=HEAD,
        identifier="G13.",
    ),
    _anchor(
        "t_g13_total_wages",
        33,
        "role_total_anchor",
        _in(
            "started work after graduating from college in June",
            "total 1996 wages/salary",
        ),
        identifier="G13.",
    ),
    _anchor(
        "t_g13_total_all_wages",
        33,
        "role_total_anchor",
        _in(
            "year, remind her/him of the several jobs",
            "total income from all 1996 wages",
        ),
        identifier="G13.",
    ),
    _anchor(
        "a_g18_practice",
        34,
        "business_aggregate_anchor",
        _in(
            "PROFESSIONAL PRACTICE: Includes self-employed doctors",
            "PROFESSIONAL PRACTICE",
        ),
        identifier="G18.",
    ),
    _anchor(
        "a_g18_trade",
        34,
        "business_aggregate_anchor",
        _in("TRADE: Includes self-employed tradesmen", "TRADE"),
    ),
    _anchor(
        "a_g18b_farming",
        34,
        "farm_aggregate_anchor",
        _in(
            "FARMING or MARKET GARDENING: If farming is Head",
            "FARMING or MARKET GARDENING",
        ),
        identifier="G18b.",
    ),
    _anchor(
        "a_g18c_boarders",
        34,
        "business_aggregate_anchor",
        _in(
            "ROOMERS OR BOARDERS: This is money paid to Head",
            "ROOMERS OR BOARDERS",
        ),
        identifier="G18c.",
    ),
    _anchor(
        "r_g50_wife",
        39,
        "role_anchor",
        _in("income from all work sources is recorded", "Wife's/\"Wife's\""),
        classification=SPOUSE,
    ),
    _anchor(
        "a_g52_business",
        39,
        "business_aggregate_anchor",
        _in(
            "income is from work in a business of which she is full",
            "business",
        ),
        identifier="G52b.",
    ),
    _anchor(
        "j_gj_job",
        40,
        "job_anchor",
        _in("The yellow JOB SUPPLEMENT is for those rare occasions", "a job"),
    ),
    _anchor(
        "r_gj_g9b_head",
        41,
        "role_anchor",
        _in("G9b HEAD'S BUSINESS Income", "HEAD'S"),
        classification=HEAD,
        identifier="G9b",
    ),
    _anchor(
        "a_gj_g9b_business",
        41,
        "business_aggregate_anchor",
        _in("G9b HEAD'S BUSINESS Income", "HEAD'S BUSINESS"),
        identifier="G9b",
    ),
    _anchor(
        "r_gj_g9d_wife",
        41,
        "role_anchor",
        _in("G9d WIFE'S/\"WIFE'S\" BUSINESS Income", "WIFE'S/\"WIFE'S\""),
        classification=SPOUSE,
        identifier="G9d",
    ),
    _anchor(
        "a_gj_g9d_business",
        41,
        "business_aggregate_anchor",
        _in(
            "G9d WIFE'S/\"WIFE'S\" BUSINESS Income",
            "WIFE'S/\"WIFE'S\" BUSINESS",
        ),
        identifier="G9d",
    ),
    _anchor(
        "r_gj_g17e_head",
        41,
        "role_anchor",
        _in("G17e Head's WAGE/SALARY Income", "Head's"),
        classification=HEAD,
        identifier="G17e",
    ),
    _anchor(
        "r_gj_g21a_head",
        41,
        "role_anchor",
        _in("G21-a Head's PROFESSIONAL PRACTICE/TRADE Income", "Head's"),
        classification=HEAD,
        identifier="G21-a",
    ),
    _anchor(
        "a_gj_g21a_practice",
        41,
        "business_aggregate_anchor",
        _in(
            "G21-a Head's PROFESSIONAL PRACTICE/TRADE Income",
            "PROFESSIONAL PRACTICE/TRADE",
        ),
        identifier="G21-a",
    ),
    _anchor(
        "r_gj_g21b_head",
        41,
        "role_anchor",
        _in("G21-b Head's FARMING/MARKET GARDENING Income", "Head's"),
        classification=HEAD,
        identifier="G21-b",
    ),
    _anchor(
        "a_gj_g21b_farming",
        41,
        "farm_aggregate_anchor",
        _in(
            "G21-b Head's FARMING/MARKET GARDENING Income",
            "FARMING/MARKET GARDENING",
        ),
        identifier="G21-b",
    ),
    _anchor(
        "r_gj_g21c_head",
        41,
        "role_anchor",
        _in("G21-c Head's ROOMER/BOARDER Income", "Head's"),
        classification=HEAD,
        identifier="G21-c",
    ),
    _anchor(
        "a_gj_g21c_boarder",
        41,
        "business_aggregate_anchor",
        _in("G21-c Head's ROOMER/BOARDER Income", "ROOMER/BOARDER"),
        identifier="G21-c",
    ),
    _anchor(
        "r_gj_g52b_wife",
        41,
        "role_anchor",
        _in("G52b Wife's/\"WIFE'S\" WAGE/SALARY Income", "Wife's/\"WIFE'S\""),
        classification=SPOUSE,
        identifier="G52b",
    ),
    _anchor(
        "r_gj4_head",
        41,
        "role_anchor",
        _in(
            "This is the number of calendar weeks in 1996 during which", "Head"
        ),
        classification=HEAD,
        identifier="GJ4.",
    ),
    _anchor(
        "r_gj4_wife",
        41,
        "role_anchor",
        _in(
            "This is the number of calendar weeks in 1996 during which",
            'Wife/"WIFE"',
        ),
        classification=SPOUSE,
        identifier="GJ4.",
    ),
    _anchor(
        "j_gj5_this_job",
        41,
        "job_anchor",
        _in(
            "This is average hours per week for the weeks worked on this job",
            "this job",
        ),
        identifier="GJ5.",
    ),
    _anchor(
        "j_g76_each_job",
        43,
        "job_anchor",
        _in("each job in 1996. We're after total hours", "each job"),
        identifier="G76-82.",
    ),
    _anchor(
        "r_k63_wife",
        58,
        "role_anchor",
        _in(
            'instance, if the Wife/"Wife" worked two months in 1982',
            'Wife/"Wife"',
        ),
        classification=SPOUSE,
        identifier="K63.",
        paths=P_KNEW,
    ),
    _anchor(
        "r_l72_head",
        60,
        "role_anchor",
        _in(
            "We are interested in the similarity of occupations Head has had",
            "Head",
        ),
        classification=HEAD,
        identifier="L72.",
        paths=P_LNEW,
    ),
    _anchor(
        "r_m_head",
        61,
        "role_anchor",
        _in("Each series is asked first about the Head", "Head"),
        classification=HEAD,
        paths=P_M,
    ),
    _anchor(
        "r_m_wife",
        61,
        "role_anchor",
        _in("then about the Wife", 'Wife/"Wife"'),
        classification=SPOUSE,
        paths=P_M,
    ),
    _anchor(
        "j_m1_last_employment",
        61,
        "job_anchor",
        _in(
            "For Heads born outside the U.S., we want to ask",
            "any last employment",
        ),
        identifier="M1.",
        paths=P_M,
    ),
    _anchor(
        "j_m_lastjob_heading",
        61,
        "job_anchor",
        _mark("Last Job Before Coming to the United States"),
        paths=P_M,
    ),
    _anchor(
        "j_m2_last_job",
        61,
        "job_anchor",
        _in(
            "Last Job Before Coming to U.S. For those Head",
            "Last Job Before Coming to U.S.",
        ),
        identifier="M2-M12.",
        paths=P_MLAST,
    ),
    _anchor(
        "j_m_firstjob_heading",
        61,
        "job_anchor",
        _mark("First Job in the United States"),
        paths=P_M,
    ),
    _anchor(
        "j_m12a_first_job",
        61,
        "job_anchor",
        _in("First Job in U.S. For Heads who immigrated", "the first job"),
        identifier="M12a-22.",
        paths=P_M,
    ),
    _anchor(
        "r_m23a_wife",
        62,
        "role_anchor",
        _in("The series M1-M23 repeats for any eligible", 'Wife/"Wife."'),
        classification=SPOUSE,
        identifier="M23a.",
        paths=P_M,
    ),
)


CTX = "context_anchor"
REM = "remuneration_component_anchor"
TOT = "role_total_anchor"


def _item(
    key: str,
    page: int,
    marker: str,
    kind: str,
    purposes: tuple[str, ...],
    identifier: str | None = None,
    parents: tuple[str, ...] = (),
    paths: tuple[tuple[str, ...], ...] = P_ROOT,
    identifier_occurrence: int = 0,
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "line_marker": marker,
        "kind": kind,
        "purposes": purposes,
        "identifier": identifier,
        "identifier_occurrence": identifier_occurrence,
        "parents": parents,
        "paths": paths,
    }


# Retained items.  The prompt span is the trimmed printed line that carries
# the item's identifier -- the printed locator of the field inside this
# manual -- and the same span carries the item's component/context anchor,
# following the doc-14 convention for a printed questionnaire line.
ITEM_SPECS: tuple[dict[str, Any], ...] = (
    # Section B entry and employment status.
    _item(
        "b1_3",
        12,
        "It is crucial that you get an accurate reply to B1-B3",
        CTX,
        ("interview_and_role_attachment",),
        "B1-3",
        (),
        P_BSCOPE,
    ),
    _item(
        "b_code1",
        12,
        "WORKING NOW: Head has an employer",
        CTX,
        ("interview_and_role_attachment",),
        "CODE 1.",
        (),
        P_BSCOPE,
    ),
    _item(
        "b_code2",
        12,
        "ONLY TEMPORARILY LAID OFF: Head is employed",
        CTX,
        ("interview_and_role_attachment",),
        "CODE 2.",
        (),
        P_BSCOPE,
    ),
    _item(
        "b_code3",
        12,
        "LOOKING FOR WORK, UNEMPLOYED: Head is not working now",
        CTX,
        ("interview_and_role_attachment",),
        "CODE 3.",
        (),
        P_BSCOPE,
    ),
    _item(
        "b_codes48",
        12,
        "CODES 4-8. NOT WORKING/NOT LOOKING",
        CTX,
        ("interview_and_role_attachment",),
        "CODES 4-8.",
        (),
        P_BSCOPE,
    ),
    # Main job definition and job-descriptor items.
    _item(
        "b_note459",
        13,
        "Note: B4-B59 refer to",
        CTX,
        ("job_identifier",),
        "B4-B59",
        ("j_b13_main_job",),
        P_BMAIN,
    ),
    _item(
        "b4",
        13,
        "Be careful with the following situations and record",
        CTX,
        ("employee_self_or_mixed",),
        "B4.",
        ("j_b13_main_job",),
        P_BMAIN,
    ),
    _item(
        "b5",
        13,
        "Many self-employed people and professionals",
        CTX,
        ("incorporation",),
        "B5.",
        ("a_b5_business",),
        P_BMAIN,
    ),
    _item(
        "b9_9a",
        14,
        "Follow the guidelines below",
        CTX,
        ("occupation",),
        "B9-9a.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b10",
        14,
        "The type of business or industry has to fit into an industrial code",
        CTX,
        ("industry",),
        "B10.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b_govt_level",
        15,
        "If Head is employed by the government, specify the department",
        CTX,
        ("government_level",),
        None,
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b11",
        16,
        "You will be asking employer's name for every employer",
        CTX,
        ("job_identifier",),
        "B11.",
        (),
        P_BMAIN,
    ),
    # Current pay rates.
    _item(
        "b12_19",
        16,
        "Questions B12, B13, B16, and B18",
        REM,
        ("amount", "reporting_unit"),
        "B12-19.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b12",
        16,
        "The OTHER category is for everything that is not salary",
        REM,
        ("amount", "reporting_unit"),
        "B12.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b14",
        16,
        "This should be NO if Head's income is a fixed",
        CTX,
        ("amount",),
        "B14.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b15",
        16,
        "Select all that R mentions. Use code 5. EXACT AMOUNT when R answers an amount",
        REM,
        ("amount", "reporting_unit"),
        "B15.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b18",
        17,
        "OTHER ways Head is paid for regular work time",
        REM,
        ("amount",),
        "B18",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b19",
        17,
        "We know that B19 may be difficult",
        REM,
        ("amount",),
        "B19.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b17",
        17,
        "Select all that R mentions. Use code 5. EXACT AMOUNT when R answers with an",
        REM,
        ("amount", "reporting_unit"),
        "B17.",
        ("j_b9_main_job",),
        P_BMAIN,
    ),
    _item(
        "b20",
        17,
        '"Another job" can mean a different position',
        CTX,
        ("job_identifier",),
        "B20.",
        ("j_b20_another_job",),
        P_BMAIN,
    ),
    _item(
        "b23",
        17,
        "By employer, we mean company, firm, or organization",
        CTX,
        ("job_identifier", "month_or_exposure"),
        "B23.",
        ("j_b24_main_jobs",),
        P_BMAIN,
    ),
    _item(
        "b_workhist",
        17,
        "With questions B24-B59 and pink Work History Supplements",
        CTX,
        ("job_identifier", "month_or_exposure"),
        None,
        ("j_b24_main_jobs",),
        P_BMAIN,
    ),
    # Work history.
    _item(
        "b24",
        18,
        "Both B23 and B24 refer to the present employer",
        CTX,
        ("month_or_exposure",),
        "B24.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b25_29",
        18,
        "For Heads who began their present employment in 1996",
        CTX,
        ("month_or_exposure",),
        "B25-29.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b30",
        18,
        "When Heads began their present employment in 1997",
        CTX,
        ("month_or_exposure",),
        "B30.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b31_34",
        18,
        "When Heads began their present employment prior to 1996",
        CTX,
        ("month_or_exposure",),
        "B31-34.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b35_36",
        18,
        "See B9-B9a for probes and cautions",
        CTX,
        ("occupation",),
        "B35-36.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b38",
        18,
        "The amount at B38 should be an average",
        REM,
        ("amount",),
        "B38.",
        ("j_b24_employer",),
        P_BMAIN,
    ),
    _item(
        "b39",
        18,
        "Mark the months of 1996 that Head worked",
        CTX,
        ("month_or_exposure",),
        "B39.",
        ("j_b39_main_job",),
        P_BMAIN,
        1,
    ),
    _item(
        "b40",
        18,
        'If B40 is "NO", Head had no',
        CTX,
        ("job_identifier",),
        "B40.",
        ("j_b40_main_job_employer",),
        P_BMAIN,
    ),
    _item(
        "b41_41c",
        19,
        "See B9-B11 instructions. Remember, occupation and industry",
        CTX,
        ("industry", "occupation"),
        "B41-41c",
        (),
        P_BMAIN,
    ),
    _item(
        "b42",
        19,
        "See B39. The same procedures as above apply",
        CTX,
        ("month_or_exposure",),
        "B42.",
        (),
        P_BMAIN,
    ),
    _item(
        "b42a_42d",
        19,
        "There should be no overlap between B39 and B42",
        CTX,
        ("month_or_exposure",),
        "B42a-42d",
        ("j_b42_main_job",),
        P_BMAIN,
    ),
    _item(
        "b43_44",
        19,
        "B43-44.",
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        "B43-44.",
        (),
        P_BMAIN,
    ),
    _item(
        "b45a",
        19,
        "Enter dollar amount and time period in which it was made",
        REM,
        ("amount", "reporting_unit"),
        "B45a.",
        (),
        P_BMAIN,
    ),
    _item("b45b", 19, "B45b.", REM, ("amount",), "B45b.", (), P_BMAIN),
    _item(
        "b46_47",
        19,
        "Again we're looking for the most recent position change in 1996",
        CTX,
        ("month_or_exposure",),
        "B46-B47.",
        (),
        P_BMAIN,
    ),
    _item(
        "b49_49a",
        19,
        "B49-49a.",
        CTX,
        ("occupation",),
        "B49-49a.",
        (),
        P_BMAIN,
    ),
    _item("b52", 19, "B52.", REM, ("amount",), "B52.", (), P_BMAIN),
    _item(
        "b53_55",
        20,
        "Since Head is currently employed on a different",
        CTX,
        ("month_or_exposure",),
        "B53-55.",
        ("j_b53_main_job",),
        P_BMAIN,
    ),
    _item("b57a", 20, "B57a.", REM, ("amount",), "B57a.", (), P_BMAIN),
    _item(
        "b59",
        20,
        "If Head had any other main-job employers during 1996",
        CTX,
        ("job_identifier",),
        "B59.",
        ("j_whs_main_job_employers",),
        P_BSCOPE,
    ),
    _item(
        "whs_intro",
        20,
        "The questionnaire employment sections are designed",
        CTX,
        ("job_identifier",),
        None,
        ("j_whs_main_job_employers",),
        P_WHS,
    ),
    # Work History Supplement items.
    _item(
        "s41_41c",
        21,
        "S41-41c.",
        CTX,
        ("industry", "occupation"),
        "S41-41c.",
        (),
        P_WHS,
    ),
    _item("s42", 21, "S42.  ", CTX, ("month_or_exposure",), "S42.", (), P_WHS),
    _item(
        "s42a_42d",
        21,
        "S42a-42d.",
        CTX,
        ("month_or_exposure",),
        "S42a-42d.",
        (),
        P_WHS,
    ),
    _item(
        "s43_44",
        21,
        "S43-44.",
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        "S43-44.",
        (),
        P_WHS,
    ),
    _item("s45b", 21, "S45b.", REM, ("amount",), "S45b.", (), P_WHS),
    _item(
        "s46_47",
        21,
        "S46-47.",
        CTX,
        ("month_or_exposure",),
        "S46-47.",
        (),
        P_WHS,
    ),
    _item(
        "s49_49a", 21, "S49-49a.", CTX, ("occupation",), "S49-49a.", (), P_WHS
    ),
    _item("s52", 21, "S52.", REM, ("amount",), "S52.", (), P_WHS),
    _item(
        "s53_55",
        21,
        "S53-55.",
        CTX,
        ("month_or_exposure",),
        "S53-55.",
        (),
        P_WHS,
    ),
    _item("s57a", 21, "S57a.", REM, ("amount",), "S57a.", (), P_WHS),
    _item(
        "s59",
        21,
        "S59.",
        CTX,
        ("job_identifier",),
        "S59.",
        ("j_whs_main_job_employers",),
        P_WHS,
    ),
    # 1996 work weeks.
    _item(
        "w_obj1",
        22,
        "1. Separation of weeks into periods of work",
        CTX,
        ("month_or_exposure",),
        None,
        ("j_weeks_main_jobs",),
        P_WEEKS,
    ),
    _item(
        "w_obj2",
        22,
        "2. Average work hours per week for weeks worked",
        CTX,
        ("month_or_exposure",),
        None,
        (),
        P_WEEKS,
    ),
    _item(
        "w_obj3",
        22,
        "3. Annual overtime hours",
        CTX,
        ("month_or_exposure",),
        None,
        (),
        P_WEEKS,
    ),
    _item(
        "w_workdef",
        22,
        "Work in these questions means simply and only",
        CTX,
        ("month_or_exposure",),
        None,
        ("j_weeks_main_job_employment",),
        P_WEEKS,
    ),
    _item(
        "w_unemp",
        23,
        "Unemployment vs. Temporary Layoff is a little more complicated",
        CTX,
        ("month_or_exposure",),
        None,
        (),
        P_WEEKS,
    ),
    _item(
        "w_unempcond",
        23,
        "Weeks spent as unemployed require two conditions",
        CTX,
        ("month_or_exposure",),
        None,
        (),
        P_WEEKS,
    ),
    _item(
        "w_nwnl",
        23,
        "Not Working and Not Looking is often confused",
        CTX,
        ("month_or_exposure",),
        None,
        (),
        P_WEEKS,
    ),
    _item(
        "b60_62",
        23,
        '"Someone else" means anyone, not just FU members',
        CTX,
        ("month_or_exposure",),
        "B60-62.",
        (),
        P_WEEKS,
    ),
    _item(
        "b63_65",
        23,
        "Again, we don't need dates for the occasional flu",
        CTX,
        ("month_or_exposure",),
        "B63-65.",
        (),
        P_WEEKS,
    ),
    _item(
        "b66_68",
        23,
        "Include paid and unpaid holidays, vacation time",
        CTX,
        ("month_or_exposure",),
        "B66-68.",
        (),
        P_WEEKS,
    ),
    _item(
        "b69_71",
        24,
        "Beware of overlaps with unemployment, temporary layoff",
        CTX,
        ("month_or_exposure",),
        "B69-71.",
        (),
        P_WEEKS,
    ),
    _item(
        "b72_74",
        24,
        "Check dates at B74 against work history",
        CTX,
        ("month_or_exposure",),
        "B72-74.",
        (),
        P_WEEKS,
    ),
    _item(
        "b75_77",
        24,
        "Again, check these dates against the work history",
        CTX,
        ("month_or_exposure",),
        "B75-77.",
        (),
        P_WEEKS,
    ),
    _item(
        "b78",
        24,
        "We want the total number of weeks during which Head did any work",
        CTX,
        ("month_or_exposure",),
        "B78.",
        (),
        P_WEEKS,
    ),
    _item(
        "b79",
        25,
        "This is the average hours per week on main job(s)",
        CTX,
        ("month_or_exposure",),
        "B79.",
        ("j_b79_main_jobs",),
        P_WEEKS,
    ),
    _item(
        "b80_81",
        25,
        "Be careful not to double count any overtime hours",
        CTX,
        ("month_or_exposure",),
        "B80-81.",
        (),
        P_WEEKS,
    ),
    _item(
        "b81a_d",
        25,
        "If Head worked more than one main job in 1996, we ask separate",
        CTX,
        ("month_or_exposure",),
        "B81a-d.",
        (),
        P_WEEKS,
    ),
    # Extra jobs.
    _item(
        "b82",
        25,
        "Main vs. Extra Job distinctions",
        CTX,
        ("job_identifier",),
        "B82.",
        ("j_b82_extra_job",),
        P_BMAIN,
    ),
    _item(
        "b83_85",
        25,
        "Follow the same general rules that you used for probing on B9-B11",
        CTX,
        ("industry", "occupation"),
        "B83-85.",
        (),
        P_BMAIN,
    ),
    _item(
        "b86",
        25,
        "See B11 QxQ.",
        CTX,
        ("job_identifier",),
        "B86.",
        (),
        P_BMAIN,
    ),
    _item(
        "b87",
        25,
        "Be sure to record the unit of time",
        REM,
        ("amount", "reporting_unit"),
        "B87.",
        ("a_b87_small_business",),
        P_BMAIN,
    ),
    _item(
        "b88",
        25,
        "This is the number of calendar weeks in 1996 during which Head did any work",
        CTX,
        ("month_or_exposure",),
        "B88.",
        (),
        P_BMAIN,
    ),
    _item(
        "b89",
        25,
        "This is average hours per week for the weeks Head worked",
        CTX,
        ("month_or_exposure",),
        "B89.",
        ("j_b89_extra_job",),
        P_BMAIN,
    ),
    _item(
        "b90_93",
        26,
        "These dates will help us to check for overlap with spells",
        CTX,
        ("month_or_exposure",),
        "B90-93.",
        (),
        P_BMAIN,
    ),
    # Section C.
    _item(
        "c4_8",
        27,
        "This sequence provides a short version of asking work week information",
        CTX,
        ("month_or_exposure",),
        "C4-8.",
        (),
        P_SECTIONC,
    ),
    _item(
        "c9_11",
        27,
        "Probe for detail, as in the occupation/industry instructions",
        CTX,
        ("industry", "occupation"),
        "C9-11.",
        (),
        P_SECTIONC,
    ),
    _item(
        "c12_14",
        27,
        "For instructions, see B4-B5.",
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        "C12-14.",
        (),
        P_SECTIONC,
    ),
    _item(
        "c14a", 27, "C14a.", CTX, ("job_identifier",), "C14a.", (), P_SECTIONC
    ),
    _item(
        "c15", 27, "C15.", CTX, ("month_or_exposure",), "C15.", (), P_SECTIONC
    ),
    _item(
        "c16_51",
        27,
        "This sequence, with WORK HISTORY SUPPLEMENTS if needed",
        CTX,
        ("month_or_exposure", "job_identifier"),
        "C16-51.",
        ("j_c16_last_job",),
        P_SECTIONC,
    ),
    # Sections D and E.
    _item(
        "d1_1a",
        28,
        "The D1 checkpoint routes all Female Heads",
        CTX,
        ("interview_and_role_attachment",),
        "D1-1a.",
        (),
        P_DE,
    ),
    _item(
        "d1a",
        28,
        "D1a is parallel to B1",
        CTX,
        ("interview_and_role_attachment",),
        "D1a",
        (),
        P_DE,
    ),
    # Section G reporting basis and farm income.
    _item(
        "g_wagebasis",
        31,
        "All wages and salaries listed in Section G should be before taxes",
        REM,
        ("amount",),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "g1a",
        31,
        "You will know from B9b and B10 whether Head's current occupation",
        CTX,
        ("occupation",),
        "G1a.",
        (),
        P_ROOT,
    ),
    _item(
        "g2",
        31,
        "Receipts from normal farm operations include:",
        REM,
        ("amount",),
        "G2.",
        ("a_g2_farm",),
        P_ROOT,
    ),
    _item(
        "g3",
        31,
        "Farm operating expenses can include:",
        REM,
        ("amount",),
        "G3.",
        ("a_g3_farm",),
        P_ROOT,
    ),
    _item(
        "g4",
        32,
        "Farm income equals total receipts",
        REM,
        ("amount",),
        "G4.",
        ("a_g4_farm",),
        P_ROOT,
    ),
    # Section G business income.
    _item(
        "g5_7a",
        32,
        "Do not include stock ownership in G5",
        CTX,
        ("incorporation",),
        "G5-7a.",
        ("a_g5_business",),
        P_ROOT,
    ),
    _item(
        "g9a_9d",
        32,
        "These questions are crucial. If the Head put in work time",
        CTX,
        ("month_or_exposure",),
        "G9a-G9d.",
        (),
        P_ROOT,
    ),
    _item(
        "g10",
        32,
        "If R doesn't understand the question, select DON'T KNOW",
        CTX,
        ("incorporation",),
        "G10.",
        ("a_g10_business",),
        P_ROOT,
    ),
    _item(
        "g11a",
        32,
        "The amount given here is net profit",
        REM,
        ("amount",),
        "G11a.",
        ("a_g5_business",),
        P_ROOT,
    ),
    # Section G labor income of Head.
    _item(
        "g12",
        33,
        "If Head was working in 1996, this question almost certainly",
        CTX,
        ("interview_and_role_attachment",),
        "G12.",
        (),
        P_ROOT,
    ),
    _item(
        "g13",
        33,
        "This question applies only to current Head",
        REM,
        ("amount",),
        "G13.",
        (),
        P_ROOT,
    ),
    _item(
        "g14",
        33,
        'Note the phrase "in addition to this."',
        REM,
        ("amount",),
        "G14.",
        (),
        P_ROOT,
    ),
    _item(
        "g16",
        33,
        "If earnings are solely from bonuses, overtime, tips or commissions",
        REM,
        ("amount",),
        "G16.",
        (),
        P_ROOT,
    ),
    _item(
        "g17f",
        33,
        "If there are no work hours reported in Section B or C for income",
        CTX,
        ("month_or_exposure",),
        "G17f.",
        (),
        P_ROOT,
    ),
    _item(
        "g18",
        34,
        "PROFESSIONAL PRACTICE: Includes self-employed doctors",
        REM,
        ("amount",),
        "G18.",
        ("a_g18_practice",),
        P_ROOT,
    ),
    _item(
        "g18_trade",
        34,
        "TRADE: Includes self-employed tradesmen",
        REM,
        ("amount",),
        None,
        ("a_g18_trade",),
        P_ROOT,
    ),
    _item(
        "g18b",
        34,
        "FARMING or MARKET GARDENING: If farming is Head",
        REM,
        ("amount",),
        "G18b.",
        ("a_g18b_farming",),
        P_ROOT,
    ),
    _item(
        "g18c",
        34,
        "ROOMERS OR BOARDERS: This is money paid to Head",
        REM,
        ("amount",),
        "G18c.",
        ("a_g18c_boarders",),
        P_ROOT,
    ),
    _item(
        "g19a_c",
        34,
        "It is very important to select the appropriate unit of time",
        CTX,
        ("reporting_unit",),
        "G19a-c.",
        (),
        P_ROOT,
    ),
    _item(
        "g20a_c",
        34,
        "We want to know during which months of 1996 this income was received",
        CTX,
        ("month_or_exposure",),
        "G20a-c.",
        (),
        P_ROOT,
    ),
    _item(
        "g21a_c",
        34,
        "Again, make sure you have work hours in Section B/C for any income",
        CTX,
        ("month_or_exposure",),
        "G21a-c.",
        (),
        P_ROOT,
    ),
    _item(
        "g22_24",
        35,
        "The purpose of this sequence is to help you make sure that IF Head",
        CTX,
        ("month_or_exposure",),
        "G22-24.",
        (),
        P_ROOT,
    ),
    # Section G labor income of Wife/"Wife".
    _item(
        "g50_52",
        38,
        "Remember that work hours in Section D/E imply income here",
        CTX,
        ("month_or_exposure",),
        "G50-52.",
        (),
        P_ROOT,
    ),
    _item(
        "g50_total",
        39,
        "income from all work sources is recorded, including tips",
        TOT,
        ("amount",),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "g52b",
        39,
        "Again, if income is reported but no work hours were recorded",
        CTX,
        ("month_or_exposure",),
        "G52b.",
        (),
        P_ROOT,
    ),
    # 1996 Job Supplement.
    _item(
        "gj_intro",
        40,
        "The yellow JOB SUPPLEMENT is for those rare occasions",
        CTX,
        ("job_identifier",),
        None,
        ("j_gj_job",),
        P_ROOT,
    ),
    _item(
        "gj0",
        41,
        "Indicate which of seven places you discovered the missing job information",
        CTX,
        ("job_identifier",),
        "GJ0a-b.",
        (),
        P_ROOT,
    ),
    _item(
        "gj_g9b",
        41,
        "G9b HEAD'S BUSINESS Income",
        REM,
        ("amount",),
        "G9b",
        ("a_gj_g9b_business",),
        P_ROOT,
    ),
    _item(
        "gj_g9d",
        41,
        "G9d WIFE'S/\"WIFE'S\" BUSINESS Income",
        REM,
        ("amount",),
        "G9d",
        ("a_gj_g9d_business",),
        P_ROOT,
    ),
    _item(
        "gj_g17e",
        41,
        "G17e Head's WAGE/SALARY Income",
        REM,
        ("amount",),
        "G17e",
        (),
        P_ROOT,
    ),
    _item(
        "gj_g21a",
        41,
        "G21-a Head's PROFESSIONAL PRACTICE/TRADE Income",
        REM,
        ("amount",),
        "G21-a",
        ("a_gj_g21a_practice",),
        P_ROOT,
    ),
    _item(
        "gj_g21b",
        41,
        "G21-b Head's FARMING/MARKET GARDENING Income",
        REM,
        ("amount",),
        "G21-b",
        ("a_gj_g21b_farming",),
        P_ROOT,
    ),
    _item(
        "gj_g21c",
        41,
        "G21-c Head's ROOMER/BOARDER Income",
        REM,
        ("amount",),
        "G21-c",
        ("a_gj_g21c_boarder",),
        P_ROOT,
    ),
    _item(
        "gj_g52b",
        41,
        "G52b Wife's/\"WIFE'S\" WAGE/SALARY Income",
        REM,
        ("amount",),
        "G52b",
        (),
        P_ROOT,
    ),
    _item(
        "gj3_3a",
        41,
        "Follow the same general rules that you used for probing on B9-B11",
        CTX,
        ("industry", "occupation"),
        "GJ3-3a.",
        (),
        P_ROOT,
    ),
    _item(
        "gj4",
        41,
        "This is the number of calendar weeks in 1996 during which",
        CTX,
        ("month_or_exposure",),
        "GJ4.",
        (),
        P_ROOT,
        2,
    ),
    _item(
        "gj5",
        41,
        "This is average hours per week for the weeks worked on this job",
        CTX,
        ("month_or_exposure",),
        "GJ5.",
        ("j_gj5_this_job",),
        P_ROOT,
    ),
    _item(
        "gj6_9",
        41,
        "These dates will help us to check for overlap with spells",
        CTX,
        ("month_or_exposure",),
        "GJ6-9.",
        (),
        P_ROOT,
    ),
    _item(
        "gj10",
        41,
        "We mention negative alternatives to make it easier for R to talk",
        CTX,
        ("month_or_exposure",),
        "GJ10.",
        (),
        P_ROOT,
    ),
    # Other FU member employment and income.
    _item(
        "g75",
        42,
        'Unlike the Head/Wife/"Wife" employment status questions',
        CTX,
        ("interview_and_role_attachment",),
        "G75.",
        (),
        P_ROOT,
    ),
    _item(
        "g76_82",
        43,
        "If this person's employment was irregular",
        CTX,
        ("month_or_exposure", "job_identifier"),
        "G76-82.",
        ("j_g76_each_job",),
        P_ROOT,
    ),
    _item(
        "g77",
        43,
        "We use occupation to help us assign missing income data",
        CTX,
        ("occupation",),
        "G77.",
        (),
        P_ROOT,
    ),
    _item(
        "g78",
        43,
        "List total annual income from each job here",
        REM,
        ("amount",),
        "G78.",
        ("j_g76_each_job",),
        P_ROOT,
    ),
    _item(
        "g79",
        43,
        "This figure should be the number of weeks in which any work was done",
        CTX,
        ("month_or_exposure",),
        "G79.",
        (),
        P_ROOT,
    ),
    _item(
        "g81",
        43,
        "If employment was irregular and R can't give hours per week",
        CTX,
        ("month_or_exposure",),
        "G81.",
        (),
        P_ROOT,
    ),
    # Section K work-history items for Wife/"Wife".
    _item(
        "k63",
        58,
        "This means the number of years in which any work was done",
        CTX,
        ("month_or_exposure",),
        "K63.",
        (),
        P_KNEW,
    ),
    _item(
        "k64",
        58,
        "Thirty-five hours or more per week is full-time.",
        CTX,
        ("month_or_exposure",),
        "K64.",
        (),
        P_KNEW,
    ),
    _item(
        "k65_66",
        58,
        "Again, use the same probing technique you use at B9-10",
        CTX,
        ("industry", "occupation"),
        "K65-66.",
        (),
        P_KNEW,
    ),
    _item(
        "k92_93",
        58,
        "K92-93.",
        CTX,
        ("month_or_exposure", "industry", "occupation"),
        "K92-93.",
        (),
        P_KSAME,
    ),
    # Section L work-history items for Head.
    _item(
        "l70_71",
        60,
        "See QxQs for comparable questions K63-64.",
        CTX,
        ("month_or_exposure",),
        "L70-71.",
        (),
        P_LNEW,
    ),
    _item(
        "l72",
        60,
        "We are interested in the similarity of occupations Head has had",
        CTX,
        ("occupation",),
        "L72.",
        (),
        P_LNEW,
    ),
    _item(
        "l73_74",
        60,
        "See QxQs for comparable questions K65-66.",
        CTX,
        ("industry", "occupation"),
        "L73-74.",
        (),
        P_LNEW,
    ),
    _item(
        "l100_101",
        60,
        "L100-101.",
        CTX,
        ("industry", "occupation"),
        "L100-101.",
        (),
        P_LSAME,
    ),
    # Section M immigrant employment history.
    _item(
        "m1",
        61,
        "For Heads born outside the U.S., we want to ask",
        CTX,
        ("job_identifier",),
        "M1.",
        ("j_m1_last_employment",),
        P_M,
        1,
    ),
    _item(
        "m2_m12",
        61,
        "Last Job Before Coming to U.S. For those Head",
        CTX,
        ("job_identifier",),
        "M2-M12.",
        ("j_m2_last_job",),
        P_MLAST,
    ),
    _item(
        "m4_5",
        61,
        "Use the same occupation/industry probing technique as at B9-B10",
        CTX,
        ("industry", "occupation"),
        "M4-5.",
        (),
        P_MLAST,
    ),
    _item(
        "m10",
        61,
        "This is the average hours worked per week for all jobs (combined)",
        CTX,
        ("month_or_exposure",),
        "M10.",
        (),
        P_MLAST,
    ),
    _item(
        "m11_11a",
        61,
        "Be sure to get both the amount and the period of payment",
        REM,
        ("amount", "reporting_unit"),
        "M11-11a.",
        (),
        P_MLAST,
    ),
    _item(
        "m12a_22",
        61,
        "First Job in U.S. For Heads who immigrated",
        CTX,
        ("job_identifier",),
        "M12a-22.",
        ("j_m12a_first_job",),
        P_M,
    ),
    _item(
        "m13_14",
        61,
        "These questions should prevent us from asking again about Head",
        CTX,
        ("job_identifier",),
        "M13-14.",
        (),
        P_M,
    ),
    _item(
        "m15_16",
        61,
        "See comparable QxQs at M4-5.",
        CTX,
        ("industry", "occupation"),
        "M15-16.",
        (),
        P_M,
    ),
    _item(
        "m17",
        61,
        "We mean where, in the United States, was Head living",
        CTX,
        ("state_of_residence",),
        "M17.",
        (),
        P_M,
    ),
    _item(
        "m21",
        62,
        "See comparable QxQ at M10",
        CTX,
        ("month_or_exposure",),
        "M21.",
        (),
        P_M,
    ),
)


def _ri(
    key: str,
    page: int,
    selector: Mapping[str, Any],
    paths: tuple[tuple[str, ...], ...] = P_ROOT,
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "paths": paths,
        **{k: v for k, v in selector.items()},
    }


# Explicit printed repeat and cross-reference instructions.  Every retained
# instruction is dispositioned below by a resolved or unresolved alias row.
REPEAT_SPECS: tuple[dict[str, Any], ...] = (
    _ri("ri_b82_xref", 13, _mark("see B82 Q-x-Qs"), P_BMAIN),
    _ri("ri_b35_36", 18, _mark("See B9-B9a for probes and cautions"), P_BMAIN),
    _ri(
        "ri_b18_extra",
        18,
        _mark("sure to ask the extra job sequences (B82-B106)"),
        P_BMAIN,
    ),
    _ri(
        "ri_b41_41c",
        19,
        _mark("See B9-B11 instructions. Remember, occupation and industry"),
        P_BMAIN,
    ),
    _ri(
        "ri_b42",
        19,
        _mark("See B39. The same procedures as above apply"),
        P_BMAIN,
    ),
    _ri("ri_b43_44", 19, _mark("B43-44."), P_BMAIN),
    _ri("ri_b45b", 19, _mark("B45b."), P_BMAIN),
    _ri(
        "ri_b46_47",
        19,
        _mark(
            "Again we're looking for the most recent position change in 1996"
        ),
        P_BMAIN,
    ),
    _ri("ri_b49_49a", 19, _mark("B49-49a."), P_BMAIN),
    _ri("ri_b52", 19, _mark("B52."), P_BMAIN),
    _ri("ri_b57a", 20, _mark("B57a."), P_BMAIN),
    _ri(
        "ri_whs_repeat",
        20,
        _mark("If the person worked for more than two main job employers"),
        P_WHS,
    ),
    _ri("ri_s41_41c", 21, _mark("S41-41c."), P_WHS),
    _ri("ri_s42", 21, _mark("S42.  "), P_WHS),
    _ri("ri_s42a_42d", 21, _mark("S42a-42d."), P_WHS),
    _ri("ri_s43_44", 21, _mark("S43-44."), P_WHS),
    _ri("ri_s45b", 21, _mark("S45b."), P_WHS),
    _ri("ri_s46_47", 21, _mark("S46-47."), P_WHS),
    _ri("ri_s49_49a", 21, _mark("S49-49a."), P_WHS),
    _ri("ri_s52", 21, _mark("S52."), P_WHS),
    _ri("ri_s53_55", 21, _mark("S53-55."), P_WHS),
    _ri("ri_s57a", 21, _mark("S57a."), P_WHS),
    _ri("ri_s59", 21, _mark("S59."), P_WHS),
    _ri(
        "ri_b83_85",
        25,
        _mark(
            "Follow the same general rules that you used for probing on B9-B11"
        ),
        P_BMAIN,
    ),
    _ri("ri_b86", 25, _mark("See B11 QxQ."), P_BMAIN),
    _ri("ri_b94_105", 26, _mark("is a repeat of B82-B93 and is not"), P_BMAIN),
    _ri(
        "ri_c_parallel",
        27,
        _mark("Section C parallels Section B quite closely"),
        P_SECTIONC,
    ),
    _ri("ri_c2", 27, _mark("See instructions for B21."), P_SECTIONC),
    _ri(
        "ri_c9_11",
        27,
        _mark("Probe for detail, as in the occupation/industry instructions"),
        P_SECTIONC,
    ),
    _ri("ri_c12_14", 27, _mark("For instructions, see B4-B5."), P_SECTIONC),
    _ri("ri_c14a", 27, _mark("C14a."), P_SECTIONC),
    _ri("ri_c15", 27, _mark("C15."), P_SECTIONC),
    _ri("ri_c16_51", 27, _mark("instructions given for B24-B59."), P_SECTIONC),
    _ri(
        "ri_c52_98",
        27,
        _mark("We have not reproduced the remainder of Section C questions"),
        P_SECTIONC,
    ),
    _ri(
        "ri_de_parallel",
        28,
        _span(
            "In the CAI application, they are actually the same exact questions",
            "concepts for B and C apply to D and E.",
        ),
        P_DE,
    ),
    _ri("ri_d1a", 28, _mark("D1a is parallel to B1"), P_DE),
    _ri(
        "ri_de_notreproduced",
        28,
        _mark("We have not reproduced the remainder of Sections D and E"),
        P_DE,
    ),
    _ri(
        "ri_g1a",
        31,
        _mark(
            "You will know from B9b and B10 whether Head's current occupation"
        ),
    ),
    _ri("ri_g5_repeat", 32, _mark("repeat questions G7a-G11b for")),
    _ri(
        "ri_g11c",
        32,
        _mark(
            "Attach an extra page or pages to record information for each additional business"
        ),
    ),
    _ri(
        "ri_g60_60dd",
        39,
        _mark("These questions are the same as those asked for the Head"),
    ),
    _ri(
        "ri_gj3_3a",
        41,
        _mark(
            "Follow the same general rules that you used for probing on B9-B11"
        ),
    ),
    _ri("ri_g75_see", 42, _mark("(See B1 Q-x-Qs, however, for")),
    _ri("ri_g79_see", 43, _mark("instructions for B78.")),
    _ri("ri_g81_see", 43, _mark("instructions for B79.")),
    _ri(
        "ri_k65_66",
        58,
        _mark("Again, use the same probing technique you use at B9-10"),
        P_KNEW,
    ),
    _ri(
        "ri_k67_k93",
        58,
        _mark("These are new questions asked when the Wife"),
        P_KSAME,
    ),
    _ri("ri_k92_93", 58, _mark("K92-93."), P_KSAME),
    _ri(
        "ri_l70_71",
        60,
        _mark("See QxQs for comparable questions K63-64."),
        P_LNEW,
    ),
    _ri(
        "ri_l73_74",
        60,
        _mark("See QxQs for comparable questions K65-66."),
        P_LNEW,
    ),
    _ri(
        "ri_l75_l101",
        60,
        _mark("These are new questions asked when the Head on a Reinterview"),
        P_LSAME,
    ),
    _ri("ri_l100_101", 60, _mark("L100-101."), P_LSAME),
    _ri(
        "ri_m4_5",
        61,
        _mark(
            "Use the same occupation/industry probing technique as at B9-B10"
        ),
        P_MLAST,
    ),
    _ri(
        "ri_m13_14",
        61,
        _mark(
            "These questions should prevent us from asking again about Head"
        ),
        P_M,
    ),
    _ri("ri_m15_16", 61, _mark("See comparable QxQs at M4-5."), P_M),
    _ri("ri_m21", 62, _mark("See comparable QxQ at M10"), P_M),
    _ri(
        "ri_m23a", 62, _mark("The series M1-M23 repeats for any eligible"), P_M
    ),
)

XREF = "explicit_cross_reference"
REPEATED = "explicit_repeat_instruction"
RESOLVED_HANDOFF = "local_resolved_cross_reference_for_global_assembly"

# Resolved alias evidence: both endpoints carry a retained local anchor.
RESOLVED_ALIAS_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (XREF, "ri_b82_xref", "b_note459#a", "b82#a"),
    (XREF, "ri_b35_36", "b35_36#a", "b9_9a#a"),
    (XREF, "ri_b18_extra", "b39#a", "b82#a"),
    (XREF, "ri_b41_41c", "b41_41c#a", "b9_9a#a"),
    (XREF, "ri_b41_41c", "b41_41c#a", "b10#a"),
    (XREF, "ri_b41_41c", "b41_41c#a", "b11#a"),
    (XREF, "ri_b42", "b42#a", "b39#a"),
    (XREF, "ri_b43_44", "b43_44#a", "b4#a"),
    (XREF, "ri_b43_44", "b43_44#a", "b5#a"),
    (XREF, "ri_b45b", "b45b#a", "b38#a"),
    (XREF, "ri_b46_47", "b46_47#a", "b25_29#a"),
    (XREF, "ri_b49_49a", "b49_49a#a", "b9_9a#a"),
    (XREF, "ri_b52", "b52#a", "b38#a"),
    (XREF, "ri_b57a", "b57a#a", "b38#a"),
    (XREF, "ri_s41_41c", "s41_41c#a", "b9_9a#a"),
    (XREF, "ri_s41_41c", "s41_41c#a", "b10#a"),
    (XREF, "ri_s41_41c", "s41_41c#a", "b11#a"),
    (XREF, "ri_s42", "s42#a", "b39#a"),
    (XREF, "ri_s42a_42d", "s42a_42d#a", "b42a_42d#a"),
    (XREF, "ri_s43_44", "s43_44#a", "b4#a"),
    (XREF, "ri_s43_44", "s43_44#a", "b5#a"),
    (XREF, "ri_s45b", "s45b#a", "b38#a"),
    (XREF, "ri_s46_47", "s46_47#a", "b25_29#a"),
    (XREF, "ri_s49_49a", "s49_49a#a", "b9_9a#a"),
    (XREF, "ri_s52", "s52#a", "b38#a"),
    (XREF, "ri_s53_55", "s53_55#a", "b53_55#a"),
    (XREF, "ri_s57a", "s57a#a", "b38#a"),
    (REPEATED, "ri_s59", "s59#a", "whs_intro#a"),
    (XREF, "ri_b83_85", "b83_85#a", "b9_9a#a"),
    (XREF, "ri_b83_85", "b83_85#a", "b10#a"),
    (XREF, "ri_b83_85", "b83_85#a", "b11#a"),
    (XREF, "ri_b86", "b86#a", "b11#a"),
    (XREF, "ri_c9_11", "c9_11#a", "b9_9a#a"),
    (XREF, "ri_c9_11", "c9_11#a", "b10#a"),
    (XREF, "ri_c9_11", "c9_11#a", "b11#a"),
    (XREF, "ri_c12_14", "c12_14#a", "b4#a"),
    (XREF, "ri_c12_14", "c12_14#a", "b5#a"),
    (XREF, "ri_c14a", "c14a#a", "b11#a"),
    (XREF, "ri_c15", "c15#a", "b53_55#a"),
    (XREF, "ri_c16_51", "c16_51#a", "b24#a"),
    (XREF, "ri_d1a", "d1a#a", "b1_3#a"),
    (XREF, "ri_g1a", "g1a#a", "b10#a"),
    (REPEATED, "ri_g11c", "a_g11c_business", "a_g5_business"),
    (XREF, "ri_gj3_3a", "gj3_3a#a", "b9_9a#a"),
    (XREF, "ri_gj3_3a", "gj3_3a#a", "b10#a"),
    (XREF, "ri_gj3_3a", "gj3_3a#a", "b11#a"),
    (XREF, "ri_g75_see", "g75#a", "b1_3#a"),
    (XREF, "ri_g79_see", "g79#a", "b78#a"),
    (XREF, "ri_g81_see", "g81#a", "b79#a"),
    (XREF, "ri_k65_66", "k65_66#a", "b9_9a#a"),
    (XREF, "ri_k65_66", "k65_66#a", "b10#a"),
    (XREF, "ri_k92_93", "k92_93#a", "k64#a"),
    (XREF, "ri_k92_93", "k92_93#a", "k65_66#a"),
    (XREF, "ri_l70_71", "l70_71#a", "k63#a"),
    (XREF, "ri_l70_71", "l70_71#a", "k64#a"),
    (XREF, "ri_l73_74", "l73_74#a", "k65_66#a"),
    (XREF, "ri_l100_101", "l100_101#a", "l73_74#a"),
    (XREF, "ri_m4_5", "m4_5#a", "b9_9a#a"),
    (XREF, "ri_m4_5", "m4_5#a", "b10#a"),
    (XREF, "ri_m15_16", "m15_16#a", "m4_5#a"),
    (XREF, "ri_m21", "m21#a", "m10#a"),
    (REPEATED, "ri_m23a", "r_m23a_wife", "r_m_wife"),
)

OUTSIDE = "local_target_outside_rq_annotation_domain"
SERIES = "local_series_target_unresolved_for_global_assembly"
CROSSDOC = "cross_document_target_unresolved_for_global_assembly"

# Unresolved alias evidence: the printed target is a question range, an
# unannotated item, or another document.  It is preserved verbatim for global
# assembly and is never silently bound inside the shard.
UNRESOLVED_ALIAS_SPECS: tuple[dict[str, Any], ...] = (
    {
        "relation": REPEATED,
        "instruction": "ri_whs_repeat",
        "page": 20,
        "target": "for each additional employer",
        "handoff": OUTSIDE,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_b94_105",
        "page": 26,
        "target": "B94-B105",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_c_parallel",
        "page": 27,
        "target": "Section B",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_c2",
        "page": 27,
        "target": "B21",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_c52_98",
        "page": 27,
        "target": "B60-B106",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_de_parallel",
        "page": 28,
        "target": "Sections B and C",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_de_notreproduced",
        "page": 28,
        "target": "pp. 40-71 of the questionnaire",
        "handoff": CROSSDOC,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g5_repeat",
        "page": 32,
        "target": "G7a-G11b",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_g60_60dd",
        "page": 39,
        "target": "asked for the Head",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_k67_k93",
        "page": 58,
        "target": "K2-K66",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_l75_l101",
        "page": 60,
        "target": "L2-L74",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_m13_14",
        "page": 61,
        "target": "current job",
        "handoff": SERIES,
    },
)


def _expand_items() -> (
    tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]
):
    anchors: list[dict[str, Any]] = []
    prompts: list[dict[str, Any]] = []
    for spec in ITEM_SPECS:
        domain, classification = NODE_DOMAINS[spec["kind"]]
        selector = {
            key: value
            for key, value in spec.items()
            if key
            in {
                "line_marker",
                "start_marker",
                "end_marker",
                "needle",
                "needle_occurrence",
                "inline_marker",
            }
        }
        anchors.append(
            {
                "key": spec["key"] + "#a",
                "page": spec["page"],
                "kind": spec["kind"],
                "node_domain": domain,
                "classification": classification,
                "identifier": spec["identifier"],
                "identifier_occurrence": spec["identifier_occurrence"],
                "parents": spec["parents"],
                "paths": spec["paths"],
                **selector,
            }
        )
        prompts.append(
            {
                "key": spec["key"],
                "page": spec["page"],
                "kind": "field_purpose_prompt",
                "purposes": spec["purposes"],
                "anchors": (spec["key"] + "#a", *spec["parents"]),
                "paths": spec["paths"],
                **selector,
            }
        )
    return tuple(anchors), tuple(prompts)


ITEM_ANCHOR_SPECS, PROMPT_SPECS = _expand_items()
ANCHOR_SPECS: tuple[dict[str, Any], ...] = (
    *STANDALONE_ANCHORS,
    *ITEM_ANCHOR_SPECS,
)


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
        "filename": PDF_FILENAME,
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
    specs: list[dict[str, Any]] = [
        {**copy.deepcopy(spec), "kind": "flow_branch_label"}
        for spec in FLOW_SPECS
    ]
    specs.extend(copy.deepcopy(ANCHOR_SPECS))
    specs.extend(copy.deepcopy(PROMPT_SPECS))
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
    instruction_keys = {spec["key"] for spec in REPEAT_SPECS}
    referenced = {row[1] for row in RESOLVED_ALIAS_SPECS} | {
        row["instruction"] for row in UNRESOLVED_ALIAS_SPECS
    }
    if referenced != instruction_keys:
        raise ValueError(
            "every repeat instruction needs exactly one alias disposition set"
        )
    for _, _, alias_key, referenced_key in RESOLVED_ALIAS_SPECS:
        missing = {alias_key, referenced_key} - anchor_keys
        if missing:
            raise ValueError(f"unresolved alias anchors: {missing}")

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
                parent_key = item.get("parent")
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
                paths = []
                for path_keys in item["paths"]:
                    resolved = [FLOW_ROOT]
                    for path_key in path_keys[1:]:
                        if path_key not in branch_by_key:
                            raise ValueError(
                                f"unresolved occurrence flow path {path_key}"
                            )
                        resolved = branch_by_key[path_key]["branch_path"]
                    if path_keys[0] != "root":
                        raise ValueError("flow path must start at the root")
                    paths.append(resolved)
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
                item, locator_id, index_on_page, semantic_ordinal, flow_paths
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
    start, end = _needle_span(
        page_text, identifier, spec.get("identifier_occurrence", 0)
    )
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
    rows: list[dict[str, Any]] = []
    for (
        relation,
        instruction_key,
        alias_key,
        referenced_key,
    ) in RESOLVED_ALIAS_SPECS:
        instruction_id = occurrence_id_by_key[instruction_key]
        alias_id = occurrence_id_by_key[alias_key]
        referenced_id = occurrence_id_by_key[referenced_key]
        evidence_ids = sorted(
            {alias_id, referenced_id, instruction_id},
            key=lambda occurrence_id: (
                occurrence_by_id[occurrence_id]["page_number"],
                occurrence_by_id[occurrence_id]["occurrence_index_on_page"],
            ),
        )
        preimage = [relation, alias_id, referenced_id, evidence_ids]
        rows.append(
            {
                "local_repeat_evidence_id": (
                    "rq-local-repeat-evidence:" + _digest(preimage)
                ),
                "alias_relation": relation,
                "alias_anchor_occurrence_id": alias_id,
                "referenced_anchor_occurrence_id": referenced_id,
                "source_instruction_occurrence_ids": [instruction_id],
                "unresolved_target_reference": None,
                "evidence_occurrence_ids": evidence_ids,
                "handoff_status": RESOLVED_HANDOFF,
                "annotation_status": "complete",
            }
        )
    for spec in UNRESOLVED_ALIAS_SPECS:
        instruction_id = occurrence_id_by_key[spec["instruction"]]
        page_text = page_texts[spec["page"] - 1]
        start, end = _needle_span(
            page_text, spec["target"], spec.get("target_occurrence", 0)
        )
        matched, matched_sha256 = _strict_slice(
            page_text, start, end, spec["instruction"]
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
    rows.sort(
        key=lambda row: min(
            (
                occurrence_by_id[occurrence_id]["page_number"],
                occurrence_by_id[occurrence_id]["occurrence_index_on_page"],
            )
            for occurrence_id in row["evidence_occurrence_ids"]
        )
        + (row["local_repeat_evidence_id"],)
    )
    return rows


def _overlaps(
    left_start: int, left_end: int, right_start: int, right_end: int
) -> bool:
    return left_start < right_end and right_start < left_end


# Explicit semantic re-classifications.  A candidate span keyed here names the
# same printed text that whole-page review retained under a different kind;
# without an entry a candidate that finds no same-kind output is rejected.
KIND_CORRECTIONS: dict[tuple[int, int, int, str], str] = {
    # 47 exact-span reviewer re-classifications: the candidate found the
    # printed line that whole-page review retained, but read it as the wrong
    # kind (a conditional clause inside an objective statement, a cross
    # reference inside a field definition, or a total inside a component).
    (13, 39, 116, "repeat_or_alias_instruction"): "context_anchor",
    (15, 432, 519, "flow_branch_label"): "context_anchor",
    (
        16,
        1735,
        1833,
        "repeat_or_alias_instruction",
    ): "remuneration_component_anchor",
    (16, 2336, 2430, "flow_branch_label"): "context_anchor",
    (17, 990, 1090, "repeat_or_alias_instruction"): "context_anchor",
    (17, 1689, 1780, "flow_branch_label"): "context_anchor",
    (18, 566, 666, "repeat_or_alias_instruction"): "context_anchor",
    (18, 2952, 3048, "flow_branch_label"): "context_anchor",
    (20, 1205, 1301, "flow_branch_label"): "repeat_or_alias_instruction",
    (21, 345, 442, "flow_branch_label"): "context_anchor",
    (23, 2600, 2693, "flow_branch_label"): "context_anchor",
    (23, 2600, 2693, "repeat_or_alias_instruction"): "context_anchor",
    (24, 1845, 1948, "repeat_or_alias_instruction"): "context_anchor",
    (25, 281, 377, "flow_branch_label"): "context_anchor",
    (25, 2549, 2652, "flow_branch_label"): "remuneration_component_anchor",
    (26, 268, 338, "flow_branch_label"): "repeat_or_alias_instruction",
    (27, 108, 205, "context_anchor"): "repeat_or_alias_instruction",
    (27, 275, 311, "field_purpose_prompt"): "repeat_or_alias_instruction",
    (27, 1297, 1377, "flow_branch_label"): "context_anchor",
    (27, 1481, 1567, "context_anchor"): "repeat_or_alias_instruction",
    (27, 1652, 1751, "field_purpose_prompt"): "repeat_or_alias_instruction",
    (32, 0, 95, "role_total_anchor"): "remuneration_component_anchor",
    (32, 439, 538, "repeat_or_alias_instruction"): "context_anchor",
    (32, 650, 742, "flow_branch_label"): "repeat_or_alias_instruction",
    (32, 1073, 1174, "flow_branch_label"): "context_anchor",
    (32, 1490, 1585, "flow_branch_label"): "context_anchor",
    (33, 425, 525, "flow_branch_label"): "context_anchor",
    (33, 2378, 2485, "flow_branch_label"): "remuneration_component_anchor",
    (33, 2552, 2653, "flow_branch_label"): "remuneration_component_anchor",
    (33, 2655, 2756, "flow_branch_label"): "context_anchor",
    (34, 81, 170, "context_anchor"): "remuneration_component_anchor",
    (34, 323, 411, "context_anchor"): "remuneration_component_anchor",
    (34, 663, 743, "flow_branch_label"): "remuneration_component_anchor",
    (34, 2755, 2850, "repeat_or_alias_instruction"): "context_anchor",
    (35, 0, 101, "flow_branch_label"): "context_anchor",
    (39, 653, 755, "flow_branch_label"): "context_anchor",
    (39, 653, 755, "repeat_or_alias_instruction"): "context_anchor",
    (43, 46, 146, "flow_branch_label"): "context_anchor",
    (43, 477, 574, "context_anchor"): "remuneration_component_anchor",
    (43, 477, 574, "flow_branch_label"): "remuneration_component_anchor",
    (43, 477, 574, "role_total_anchor"): "remuneration_component_anchor",
    (43, 758, 855, "flow_branch_label"): "context_anchor",
    (43, 866, 941, "context_anchor"): "repeat_or_alias_instruction",
    (58, 2180, 2276, "field_purpose_prompt"): "repeat_or_alias_instruction",
    (60, 1949, 2048, "field_purpose_prompt"): "repeat_or_alias_instruction",
    (61, 2086, 2192, "flow_branch_label"): "context_anchor",
    (62, 84, 153, "flow_branch_label"): "repeat_or_alias_instruction",
}


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
        coordinate = (
            candidate["page_number"],
            candidate["utf8_byte_start"],
            candidate["utf8_byte_end"],
            candidate["occurrence_kind_candidate"],
        )
        target_kind = KIND_CORRECTIONS.get(
            coordinate, candidate["occurrence_kind_candidate"]
        )
        targets = [
            row
            for row in output_rows
            if row["page_number"] == candidate["page_number"]
            and row["occurrence_kind"] == target_kind
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
                    candidate_parent_sources, final_parent_sources, strict=True
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
        elif dispositions <= {"modified", "accepted"} and "modified" in (
            dispositions
        ):
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


REJECTION_REASONS = {
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
        "nonestablishing_repeat_instruction_rejected",
        "states no repeat or cross-reference between retained R_Q anchors",
    ),
}


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
            reason, conclusion = REJECTION_REASONS[
                candidate_row["occurrence_kind_candidate"]
            ]
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
                    row["parent_anchor_occurrence_ids"], separators=(",", ":")
                )
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
            "paths "
            + json.dumps(
                output_row["flow_branch_paths"], separators=(",", ":")
            )
            + ".",
        )
    if kind == "flow_branch":
        return (
            "manual_flow_branch_after_complete_page_review",
            f"Complete page review added branch label "
            f"{output_row['branch_label']!r} with complete path "
            + json.dumps(output_row["branch_path"], separators=(",", ":"))
            + ".",
        )
    if kind == "local_anchor_classification":
        return (
            "manual_anchor_after_complete_page_review",
            "Complete page review classified source occurrence "
            f"{output_row['source_occurrence_id']} as "
            f"{output_row['node_domain']}/{output_row['classification']} with "
            "parents "
            + json.dumps(
                output_row["parent_anchor_occurrence_ids"],
                separators=(",", ":"),
            )
            + ".",
        )
    if kind == "local_field_purpose_classification":
        return (
            "manual_field_purpose_after_complete_page_review",
            "Complete page review classified prompt occurrence "
            f"{output_row['source_prompt_occurrence_id']} with exact purposes "
            + json.dumps(output_row["field_purposes"], separators=(",", ":"))
            + ".",
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
            f"Complete page review added {output_row['alias_relation']} "
            f"evidence for {detail}.",
        )
    if kind == "whole_document_locator":
        return (
            "manual_locator_after_complete_document_review",
            "Complete document review added exact whole-file locator "
            f"{output_row['locator_id']}.",
        )
    if kind == "page":
        return (
            "manual_page_after_complete_page_review",
            f"Complete review added page {output_row['page_number']} with "
            f"text hash {output_row['page_text_utf8_sha256']}.",
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
    """Build document 58 from pinned source bytes and explicit decisions."""

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
        raise ValueError("document-58 independently replayed identity drift")

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


CANDIDATE_DENOMINATOR = 4192


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-58 source and sealing invariant."""

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

    instruction_ids = {
        row["questionnaire_occurrence_id"]
        for row in occurrences
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    dispositioned = {
        occurrence_id
        for row in repeats
        for occurrence_id in row["source_instruction_occurrence_ids"]
    }
    if instruction_ids != dispositioned:
        raise ValueError(
            "every repeat/alias instruction must be explicitly dispositioned"
        )

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
        raise ValueError("document-58 candidate denominator drift")
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
        for output_id in disposition["stage2_row_ids"]:
            if (
                candidate_id
                not in adjudication_by_id[output_id]["source_candidate_ids"]
            ):
                raise ValueError("candidate/output adjudication is one-sided")
    for output_id, adjudication in adjudication_by_id.items():
        for candidate_id in adjudication["source_candidate_ids"]:
            if (
                output_id
                not in disposition_by_id[candidate_id]["stage2_row_ids"]
            ):
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-58 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 58: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
