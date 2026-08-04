#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for fam2009_QxQs.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 121-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

fam2009_QxQs.pdf is the 2009 question-by-question objectives manual: printed
interviewer instructions keyed to questionnaire item identifiers rather than a
printed questionnaire.  The retention test applied throughout is therefore
whether the printed text *establishes* a document-local R_Q fact for a named
item or item series -- a role attachment, a job slot, a remuneration
component, an aggregate, a retained contextual field, a field purpose, a
controlling condition, or an explicit repeat/cross-reference.  Narrative
procedure, probing examples, data-entry validation instructions, and
non-employment subject matter (housing, housework and expenditure, transfer
income, wealth, pensions, health, marriage and fertility, philanthropy,
respondent payment, and family-composition observations) are rejected even
where they carry work-like lexemes.
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
DOCUMENT_POSITION = 70
DOCUMENT_ID = (
    "psid-source-document:"
    "a7b37ac33b57943a66743b958e223d710bab3c661bab8000d284806c2a2952e6"
)
INTERVIEW_WAVE = 2009
CANONICAL_SOURCE_PATH = "documentation/capture1/fam2009_QxQs.pdf"
PDF_FILENAME = "fam2009_QxQs.pdf"
PDF_SIZE = 419_377
PDF_SHA256 = "84e60ed3b53cca857a12502bf241985d8fafc83dcd6ae2d18be00f93236b10f7"
PAGE_COUNT = 121
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_07_documents_061_070"
    / "document_070_fam2009_QxQs_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_070_fam2009_QxQs_annotation_v1.json"
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
    "32277f77b6a641d8fbfd206acc4abd979f105fa856f749f1faad9f8a64753912"
)
CANDIDATE_CONTENT_SHA256 = (
    "ba280a08cca777cb37135b9a7258fdab2ced9208e944ae5ddedfaae9b62a9648"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "e2f74cb75dd013dd893b7b16d406673f052d35c0d5144079426927008f7eca4f"
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
        raise ValueError("document-70 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-70 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-70 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-70 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / PDF_FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam2009_QxQs.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("fam2009_QxQs.pdf page-count drift")
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
        raise ValueError("document-70 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-70 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-70 empty-text page domain drift")
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
# read during the complete 121-page pass and is re-resolved against the
# authenticated fam2009_QxQs.pdf bytes.
# ---------------------------------------------------------------------------

# Controlling flow.  A branch is retained only where printed text states a
# condition that determines whether a retained R_Q item series is asked.
# Advisory conditionals inside an objective paragraph ("if R cannot give an
# exact number, probe") are rejected as noncontrolling flow text, as is every
# routing statement whose whole target series is outside the retained R_Q
# domain (pensions, wealth, health, transfers, respondent payment).
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _block(
        "f_bcde",
        19,
        "Regardless of whom your Respondent is",
        "This is extremely important.",
    ),
    # The 2009 layout breaks this sentence across a gutter "Objective" label,
    # so the retained span is the printed line that carries the condition.
    _line("f_g_workincome", 36, "reports work income in Section G"),
    _block(
        "f_g_workhours",
        36,
        "reports working during 2008 in the employment sections",
        "income from those hours must be reported in Section G.",
    ),
    _block(
        "f_f2_route",
        28,
        "If roomers or boarders are living in the HU",
        "Section DE (for the Wife/“Wife”)",
    ),
    _block(
        "f_r_wife",
        56,
        "If there is a Wife or “Wife” in the FU this set of questions",
        "in 2007, then application skips to R4.",
    ),
    _block(
        "f_kl_scope",
        101,
        "If the FU has a new Head or new Wife",
        "background information about that new FU member.",
    ),
)

ROOT_PATH = ("root",)
P_ROOT = (("root",),)
P_BCDE = (("root", "f_bcde"),)
P_RWIFE = (("root", "f_r_wife"),)
P_KL = (("root", "f_kl_scope"),)


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

# Standalone role, job, aggregate, and role-total anchors: the printed lexeme
# that names the node, following the doc-14/doc-58 convention of short
# establishing spans.
STANDALONE_ANCHORS: tuple[dict[str, Any], ...] = (
    _anchor(
        "r_bcde_head",
        19,
        "role_anchor",
        _in("of Head and Wife/“Wife” (H/W)", "Head"),
        classification=HEAD,
    ),
    _anchor(
        "r_bcde_spouse",
        19,
        "role_anchor",
        _in("of Head and Wife/“Wife” (H/W)", "Wife/“Wife”"),
        classification=SPOUSE,
    ),
    _anchor(
        "j_bcde_main_job",
        20,
        "job_anchor",
        _at("Current Main Job"),
        paths=P_BCDE,
    ),
    _anchor(
        "a_bcde23_business",
        24,
        "business_aggregate_anchor",
        _in(
            "“business” and don’t believe BC/DE23 applies",
            "business",
        ),
        identifier="BC/DE23.",
        paths=P_BCDE,
    ),
    _anchor(
        "j_bcde64_another_job",
        26,
        "job_anchor",
        _in("“Another job” can mean a different position", "Another job"),
        identifier="BC/DE64.",
        paths=P_BCDE,
    ),
    _anchor(
        "a_g2_farm",
        36,
        "farm_aggregate_anchor",
        _in("Receipts from normal farm operations include:", "farm"),
        identifier="G2.",
    ),
    _anchor(
        "a_g3_farm",
        37,
        "farm_aggregate_anchor",
        _in("Farm operating expenses can include:", "Farm"),
        identifier="G3.",
    ),
    _anchor(
        "a_g4_farm",
        37,
        "farm_aggregate_anchor",
        _in("Farm income equals total receipts", "Farm"),
        identifier="G4.",
    ),
    _anchor(
        "a_g5_business",
        37,
        "business_aggregate_anchor",
        _in("business is and specify who in the family owned it", "business"),
        identifier="G5–7a.",
    ),
    _anchor(
        "a_g10_business",
        38,
        "business_aggregate_anchor",
        _in(
            "owned a business in 2008, but R doesn’t know whether the "
            "business was",
            "business",
        ),
        identifier="G10.",
    ),
    _anchor(
        "t_g13_total_wages",
        39,
        "role_total_anchor",
        _at("total 2008\n               wages/salary"),
        identifier="G13.",
    ),
    _anchor(
        "t_g13_total_income",
        39,
        "role_total_anchor",
        _at("total income\n               from all 2008 wages"),
        identifier="G13.",
    ),
    _anchor(
        "a_g18a_practice",
        40,
        "business_aggregate_anchor",
        _in(
            "PROFESSIONAL PRACTICE: Includes self-employed doctors",
            "PROFESSIONAL PRACTICE",
        ),
        identifier="G18a.",
    ),
    _anchor(
        "a_g18a_trade",
        40,
        "business_aggregate_anchor",
        _in("TRADE: Includes self-employed tradesmen", "TRADE"),
    ),
    _anchor(
        "a_g18b_farming",
        40,
        "farm_aggregate_anchor",
        _in(
            "FARMING OR MARKET GARDENING: If farming is Head’s occupation",
            "FARMING OR MARKET GARDENING",
        ),
        identifier="G18b.",
    ),
    _anchor(
        "a_g18c_boarders",
        40,
        "business_aggregate_anchor",
        _in("ROOMERS OR BOARDERS (Extremely Rare)", "ROOMERS OR BOARDERS"),
        identifier="G18c.",
    ),
    _anchor(
        "j_g22_other_jobs",
        41,
        "job_anchor",
        _in(
            "hours on jobs other than the current main job",
            "jobs other than the current main job",
        ),
        identifier="G22–24.",
    ),
    _anchor(
        "t_g51_wife_total",
        46,
        "role_total_anchor",
        _mark("income from all work sources is recorded"),
        identifier="G51a-G52a.",
    ),
    _anchor(
        "j_g76_each_job",
        51,
        "job_anchor",
        _in("can about each job in 2008", "each job"),
        identifier="G76–82.",
    ),
    _anchor(
        "r_r2_head",
        56,
        "role_anchor",
        _in(
            "We mean the total earnings from all jobs Head had in 2007",
            "Head",
        ),
        classification=HEAD,
        identifier="R2.",
    ),
    _anchor(
        "t_r2_total",
        56,
        "role_total_anchor",
        _in(
            "We mean the total earnings from all jobs Head had in 2007",
            "the total earnings from all jobs Head had in 2007",
        ),
        identifier="R2.",
    ),
    _anchor(
        "a_r2_business",
        56,
        "business_aggregate_anchor",
        _in(
            "bonus, commissions, profit from business and/or self-employment",
            "business",
        ),
    ),
    _anchor(
        "r_r2_wife",
        56,
        "role_anchor",
        _in(
            "If there is a Wife or “Wife” in the FU this set of " "questions",
            "Wife or “Wife”",
        ),
        classification=SPOUSE,
        paths=P_RWIFE,
    ),
    _anchor(
        "r_kl_head",
        101,
        "role_anchor",
        _in("If the FU has a new Head or new Wife", "Head"),
        classification=HEAD,
        paths=P_KL,
    ),
    _anchor(
        "r_kl_spouse",
        101,
        "role_anchor",
        _in("If the FU has a new Head or new Wife", "Wife /“Wife”"),
        classification=SPOUSE,
        paths=P_KL,
    ),
    _anchor(
        "j_io18_unreported_job",
        119,
        "job_anchor",
        _in("each FU member’s unreported job.", "unreported job"),
        identifier="IO18a.",
    ),
)

CTX = "context_anchor"
REM = "remuneration_component_anchor"
TOT = "role_total_anchor"


def _item(
    key: str,
    page: int,
    selector: Mapping[str, Any],
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
        "kind": kind,
        "purposes": purposes,
        "identifier": identifier,
        "identifier_occurrence": identifier_occurrence,
        "parents": parents,
        "paths": paths,
        **{k: v for k, v in selector.items() if k not in {"key", "page"}},
    }


# Retained items.  The prompt span is the trimmed printed line (or the printed
# block) that carries the item's identifier -- the printed locator of the field
# inside this manual -- and the same span carries the item's
# component/context/total anchor.
#
# Three document-wide retention rules were applied during the complete pass:
#   1. A bare "ENTER “1.0” and F2 NOTE for responses that do not fit"
#      line is a data-entry validation instruction.  It establishes no distinct
#      component beyond the series header that names the field, and is
#      rejected wherever it stands alone.
#   2. Transfer, asset, pension, health, philanthropy, respondent-payment, and
#      family-composition items carry no R_Q remuneration component or coverage
#      context and are rejected in full, including their work-like lexemes.
#   3. An exclusion cross-reference ("should not be repeated here", "do not
#      double-count") states no alias between retained anchors and is rejected;
#      only positive repeat and cross-reference instructions are retained.
ITEM_SPECS: tuple[dict[str, Any], ...] = (
    # Sections BC and DE -- employment of Head and Wife/"Wife".
    _item(
        "bcde1_3",
        19,
        _mark("It is crucial that you get an accurate reply to BC/DE1-3"),
        CTX,
        ("interview_and_role_attachment",),
        "BC/DE1–3.",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code1",
        19,
        _mark("1) WORKING NOW: H/W has an employer"),
        CTX,
        ("interview_and_role_attachment",),
        "1)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code2",
        19,
        _mark("2) ONLY TEMPORARILY LAID OFF"),
        CTX,
        ("interview_and_role_attachment",),
        "2)",
        (),
        P_BCDE,
        1,
    ),
    _item(
        "bcde_code3",
        19,
        _mark("3) LOOKING FOR WORK, UNEMPLOYED"),
        CTX,
        ("interview_and_role_attachment",),
        "3)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code4",
        19,
        _mark("4) RETIRED"),
        CTX,
        ("interview_and_role_attachment",),
        "4)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code5",
        19,
        _mark("5) DISABLED, PERMANENTLY OR TEMPORARILY"),
        CTX,
        ("interview_and_role_attachment",),
        "5)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code6",
        19,
        _mark("6) KEEPING HOUSE"),
        CTX,
        ("interview_and_role_attachment",),
        "6)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde_code7",
        19,
        _mark("7) STUDENT"),
        CTX,
        ("interview_and_role_attachment",),
        "7)",
        (),
        P_BCDE,
    ),
    _item(
        "bcde3",
        19,
        _span(
            "R may mention these codes even though follow-up questions reveal",
            "working for money now or have been working recently (BC/DE3)",
        ),
        CTX,
        ("interview_and_role_attachment",),
        "BC/DE3",
        (),
        P_BCDE,
    ),
    _item(
        "bcde4_7",
        20,
        _mark("You will be asking employer’s names for every job that H/W"),
        CTX,
        ("job_identifier",),
        "BC/DE4-7.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde20",
        21,
        _mark("OCCUPATION: Follow the guidelines below"),
        CTX,
        ("occupation",),
        "BC/DE20.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde21",
        22,
        _mark("INDUSTRY: The type of business or industry has to fit"),
        CTX,
        ("industry",),
        "BC/DE21.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde21_govt",
        22,
        _span(
            "3. If employed by the government, specify the department",
            "Labor, etc., and the level: federal, state, or local.",
        ),
        CTX,
        ("government_level", "industry"),
        None,
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde22",
        24,
        _mark(
            "Be careful with the following situations and record as many details"
        ),
        CTX,
        ("employee_self_or_mixed",),
        "BC/DE22.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde23",
        24,
        _mark(
            "Many self-employed people and professionals do not consider what "
            "they do a"
        ),
        CTX,
        ("incorporation",),
        "BC/DE23.",
        ("a_bcde23_business",),
        P_BCDE,
    ),
    _item(
        "bcde29_39",
        25,
        _mark(
            "Questions BC/DE29, 30, 33, 36, 37, 38 refer to H/W’s regular pay"
        ),
        REM,
        ("amount", "reporting_unit"),
        "BC/DE29–39.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde29",
        25,
        _mark(
            "The OTHER category is for everything that is not salary, hourly"
        ),
        REM,
        ("amount", "reporting_unit"),
        "BC/DE29.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde31",
        25,
        _mark(
            "This should be NO if H/W’s income is a fixed "
            "weekly/monthly/annual amount"
        ),
        CTX,
        ("amount",),
        "BC/DE31.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde32_34",
        25,
        _mark("Select all that R mentions. Use code 5 – EXACT AMOUNT"),
        REM,
        ("amount", "reporting_unit"),
        "BC/DE32, 34.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde38",
        25,
        _mark("OTHER ways H/W is paid for regular work time"),
        REM,
        ("amount",),
        "BC/DE38.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde39",
        26,
        _mark(
            "We know that this question may be difficult for some situations"
        ),
        REM,
        ("amount",),
        "BC/DE39.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde41",
        26,
        _mark("By employer, we mean company, firm, or organization"),
        CTX,
        ("job_identifier", "month_or_exposure"),
        "BC/DE41.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde42a",
        26,
        _mark(
            "We’re trying to get actual number of weeks worked during the year"
        ),
        CTX,
        ("month_or_exposure",),
        "BC/DE42a.",
        ("j_bcde_main_job",),
        P_BCDE,
    ),
    _item(
        "bcde64",
        26,
        _mark(
            "“Another job” can mean a different position with the same employer"
        ),
        CTX,
        ("job_identifier",),
        "BC/DE64.",
        ("j_bcde64_another_job",),
        P_BCDE,
    ),
    # Section G -- income.
    _item(
        "g_wagebasis",
        36,
        _mark(
            "All wages and salaries listed in Section G should be before taxes"
        ),
        REM,
        ("amount",),
    ),
    _item(
        "g1a",
        36,
        _mark(
            "You will know from Sections BC or DE whether H/W’s current "
            "occupation is"
        ),
        CTX,
        ("occupation",),
        "G1a.",
    ),
    _item(
        "g2",
        36,
        _mark("Receipts from normal farm operations include:"),
        REM,
        ("amount",),
        "G2.",
        ("a_g2_farm",),
    ),
    _item(
        "g3",
        37,
        _mark("Farm operating expenses can include:"),
        REM,
        ("amount",),
        "G3.",
        ("a_g3_farm",),
    ),
    _item(
        "g4",
        37,
        _mark(
            "Farm income equals total receipts (G2) minus operating expenses (G3)"
        ),
        REM,
        ("amount",),
        "G4.",
        ("a_g4_farm",),
    ),
    _item(
        "g5_7a",
        37,
        _mark("Do NOT include investment stock ownership in G5"),
        CTX,
        ("incorporation",),
        "G5–7a.",
        ("a_g5_business",),
    ),
    _item(
        "g8",
        38,
        _mark("Remember that “family” refers to members of this FU only!"),
        CTX,
        ("interview_and_role_attachment",),
        "G8.",
    ),
    _item(
        "g9a_9b",
        38,
        _mark("These questions are crucial. If the Head put in work time"),
        CTX,
        ("month_or_exposure",),
        "G9a/G9b.",
    ),
    _item(
        "g10",
        38,
        _mark("If R doesn’t understand the question, select DON’T KNOW"),
        CTX,
        ("incorporation",),
        "G10.",
        ("a_g10_business",),
    ),
    _item(
        "g11b",
        38,
        _mark("The amount given here is net profit (i.e., after expenses)"),
        REM,
        ("amount",),
        "G11b.",
        ("a_g5_business",),
    ),
    _item(
        "g12",
        39,
        _mark(
            "If Head was working in 2008, this question almost certainly should "
            "be marked"
        ),
        CTX,
        ("interview_and_role_attachment",),
        "G12.",
    ),
    _item(
        "g13",
        39,
        _mark(
            "This question applies only to current Head. For most wage-earners"
        ),
        REM,
        ("amount",),
        "G13.",
    ),
    _item(
        "g14",
        39,
        _mark("Note the phrase “in addition to this.”"),
        REM,
        ("amount",),
        "G14.",
    ),
    _item(
        "g16",
        39,
        _mark(
            "If earnings are solely from bonuses, overtime, tips or commissions"
        ),
        REM,
        ("amount",),
        "G16.",
    ),
    _item(
        "g17f_23",
        39,
        _mark(
            "If there are no work hours reported in Section BC for income "
            "recorded at G13"
        ),
        CTX,
        ("month_or_exposure",),
        "G17f–G23.",
    ),
    _item(
        "g18a",
        40,
        _mark("PROFESSIONAL PRACTICE: Includes self-employed doctors"),
        REM,
        ("amount",),
        "G18a.",
        ("a_g18a_practice",),
    ),
    _item(
        "g18a_trade",
        40,
        _mark(
            "TRADE: Includes self-employed tradesmen such as plumbers, carpenters,"
        ),
        REM,
        ("amount",),
        None,
        ("a_g18a_trade",),
    ),
    _item(
        "g18b",
        40,
        _mark("FARMING OR MARKET GARDENING: If farming is Head’s occupation"),
        REM,
        ("amount",),
        "G18b.",
        ("a_g18b_farming",),
    ),
    _item(
        "g18c",
        40,
        _mark("ROOMERS OR BOARDERS (Extremely Rare)"),
        REM,
        ("amount",),
        "G18c.",
        ("a_g18c_boarders",),
    ),
    _item(
        "g19a_c",
        40,
        _mark("It is very important to select the appropriate time unit"),
        CTX,
        ("reporting_unit",),
        "G19a,b,c.",
    ),
    _item(
        "g20a_c",
        40,
        _mark(
            "We want to know during which months of 2008 this income was received"
        ),
        CTX,
        ("month_or_exposure",),
        "G20a,b,c.",
    ),
    _item(
        "g21a_c",
        41,
        _mark(
            "Again, make sure you have work hours in Section BC for any income "
            "reported"
        ),
        CTX,
        ("month_or_exposure",),
        "G21a,b,c.",
    ),
    _item(
        "g22_24",
        41,
        _mark(
            "The purpose of this sequence is to help you make sure that if Head "
            "had work"
        ),
        CTX,
        ("month_or_exposure", "job_identifier"),
        "G22–24.",
        ("j_g22_other_jobs",),
    ),
    _item(
        "g50",
        46,
        _mark("The key word here is ANY income."),
        CTX,
        ("interview_and_role_attachment",),
        "G50.",
    ),
    _item(
        "g51a_52a",
        46,
        _mark(
            "Remember that work hours in Section DE imply income here and vice versa."
        ),
        REM,
        ("amount",),
        "G51a-G52a.",
        ("t_g51_wife_total",),
    ),
    _item(
        "g52b",
        46,
        _mark(
            "Again, if income is reported but no work hours were recorded in Section DE"
        ),
        CTX,
        ("month_or_exposure",),
        "G52b.",
    ),
    _item(
        "g75",
        50,
        _mark(
            "You may select as many codes as apply to the OFUM’s current situation."
        ),
        CTX,
        ("interview_and_role_attachment",),
        "G75.",
    ),
    _item(
        "g76_82",
        51,
        _mark("If this person’s employment was irregular"),
        CTX,
        ("month_or_exposure", "job_identifier"),
        "G76–82.",
        ("j_g76_each_job",),
    ),
    _item(
        "g77",
        51,
        _mark("For Spanish interviews, record answers verbatim in Spanish"),
        CTX,
        ("occupation",),
        "G77.",
    ),
    _item(
        "g78",
        51,
        _mark("List total annual income from each job here."),
        REM,
        ("amount",),
        "G78.",
        ("j_g76_each_job",),
    ),
    _item(
        "g79",
        51,
        _mark(
            "This figure should be the number of weeks in which any work was done."
        ),
        CTX,
        ("month_or_exposure",),
        "G79.",
    ),
    _item(
        "g81",
        51,
        _mark("If employment was irregular and R can’t give hours per week"),
        CTX,
        ("month_or_exposure",),
        "G81.",
    ),
    # Section R -- off-year income.
    _item(
        "r2_head",
        56,
        _mark("We mean the total earnings from all jobs Head had in 2007"),
        REM,
        ("amount",),
        "R2.",
        ("t_r2_total",),
    ),
    # Section KL -- background and work history of a new Head or Wife/"Wife".
    _item(
        "kl70",
        103,
        _mark("This means the number of years in which any work was done"),
        CTX,
        ("month_or_exposure",),
        "KL70.",
        (),
        P_KL,
    ),
    _item(
        "kl71",
        103,
        _mark("Thirty-five hours or more per week is full-time."),
        CTX,
        ("month_or_exposure",),
        "KL71.",
        (),
        P_KL,
    ),
    _item(
        "kl72_73",
        103,
        _mark("Again, use the same probing technique you use in Section BC"),
        CTX,
        ("industry", "occupation"),
        "KL72-KL73",
        (),
        P_KL,
    ),
    # Interviewer observations -- jobs discovered after the employment section.
    _item(
        "io18",
        119,
        _mark(
            "Did you find out about someone’s job too late in the interview"
        ),
        CTX,
        ("job_identifier",),
        "IO18.",
        ("j_io18_unreported_job",),
    ),
    _item(
        "io18a",
        119,
        _mark(
            "Tell us for which FU member or members you discovered a job for after the"
        ),
        CTX,
        ("job_identifier",),
        "IO18a.",
        ("j_io18_unreported_job",),
    ),
    _item(
        "io18a_detail",
        119,
        _span(
            "Please provide as much information as possible about occupation",
            "income and who had this",
        ),
        CTX,
        ("amount", "month_or_exposure", "industry", "occupation"),
        None,
        ("j_io18_unreported_job",),
    ),
    _item(
        "io19",
        119,
        _span(
            "Was a job reported for any FU member for which you later learned",
            "services",
        ),
        CTX,
        ("amount",),
        "IO19.",
    ),
    _item(
        "io19a",
        120,
        _mark(
            "Please specify who and which job, and the circumstances of that job."
        ),
        CTX,
        ("job_identifier",),
        "IO19a.",
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
    _ri(
        "ri_g1a",
        36,
        _mark(
            "You will know from Sections BC or DE whether H/W’s current "
            "occupation is"
        ),
    ),
    _ri(
        "ri_g9a_9b",
        38,
        _mark("These questions are crucial. If the Head put in work time"),
    ),
    _ri(
        "ri_g17f_23",
        39,
        _mark(
            "If there are no work hours reported in Section BC for income "
            "recorded at G13"
        ),
    ),
    _ri(
        "ri_g21a_c",
        41,
        _mark(
            "Again, make sure you have work hours in Section BC for any income "
            "reported"
        ),
    ),
    _ri(
        "ri_g52b",
        46,
        _mark(
            "Again, if income is reported but no work hours were recorded in "
            "Section DE"
        ),
    ),
    _ri(
        "ri_g53_63",
        46,
        _mark("These questions are the same as those asked for the Head"),
    ),
    _ri(
        "ri_g75",
        50,
        _mark("BC1-BC3/DE1-DE3 QxQs for definitions of employment status."),
    ),
    _ri(
        "ri_kl71",
        103,
        _mark(
            "If an actual # of years are entered for the previous question (KL70)"
        ),
        P_KL,
    ),
    _ri(
        "ri_kl72_73",
        103,
        _mark("Again, use the same probing technique you use in Section BC"),
        P_KL,
    ),
)

XREF = "explicit_cross_reference"
REPEATED = "explicit_repeat_instruction"
RESOLVED_HANDOFF = "local_resolved_cross_reference_for_global_assembly"

# Resolved alias evidence: both endpoints carry a retained local anchor.
RESOLVED_ALIAS_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (XREF, "ri_g1a", "g1a#a", "bcde20#a"),
    (XREF, "ri_g17f_23", "g17f_23#a", "g13#a"),
    (XREF, "ri_g75", "g75#a", "bcde1_3#a"),
    (XREF, "ri_kl71", "kl71#a", "kl70#a"),
    (XREF, "ri_kl72_73", "kl72_73#a", "bcde20#a"),
    (XREF, "ri_kl72_73", "kl72_73#a", "bcde21#a"),
)

OUTSIDE = "local_target_outside_rq_annotation_domain"
SERIES = "local_series_target_unresolved_for_global_assembly"
CROSSDOC = "cross_document_target_unresolved_for_global_assembly"

# Unresolved alias evidence: the printed target is a whole question series or
# an unannotated item.  It is preserved verbatim for global assembly and is
# never silently bound inside the shard.
UNRESOLVED_ALIAS_SPECS: tuple[dict[str, Any], ...] = (
    {
        "relation": XREF,
        "instruction": "ri_g9a_9b",
        "page": 38,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g21a_c",
        "page": 41,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g52b",
        "page": 46,
        "target": "Section DE",
        "target_occurrence": 1,
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g53_63",
        "page": 46,
        "target": "asked for the Head",
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
    # No exact-span kind correction was adjudicated for this document.
    # Where a candidate names a retained printed line under a kind this
    # review did not retain, the candidate's kind claim is itself the
    # defect, so the row is rejected with its kind-specific reason rather
    # than silently re-pointed at an output of another kind.
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
    """Build document 70 from pinned source bytes and explicit decisions."""

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
        raise ValueError("document-70 independently replayed identity drift")

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


CANDIDATE_DENOMINATOR = 3985


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-70 source and sealing invariant."""

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
        raise ValueError("document-70 candidate denominator drift")
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-70 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 70: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
