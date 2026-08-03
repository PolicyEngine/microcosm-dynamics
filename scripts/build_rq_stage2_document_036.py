#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for q85.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 67-page review; spans,
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
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as candidates  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

SCHEMA_VERSION = "rq_stage2_document_annotation.v1"
STATUS = "pass_sealed_complete_nonauthority_annotation"
DOCUMENT_POSITION = 36
DOCUMENT_ID = (
    "psid-source-document:"
    "1eb6a3a6b41fd8a8a5470fe150626088a0e395a56cb6f336119ee4cd55727fab"
)
INTERVIEW_WAVE = 1985
CANONICAL_SOURCE_PATH = "documentation/capture1/q85.pdf"
FILENAME = "q85.pdf"
PDF_SIZE = 3_327_221
PDF_SHA256 = "842e29ab71fca34a2e24768cabd03d3f194ea765e3f330e94a2deb5cc3f08f8d"
PAGE_COUNT = 67
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_04_documents_031_040"
    / "document_036_q85_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_036_q85_annotation_v1.json"
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
    "ed0c836838fded83baf45307a1070cbd2f06bd8e55aaf6e5f44d1176622c4cd3"
)
CANDIDATE_CONTENT_SHA256 = (
    "347fb7de40b5e6bf49c6c111996bc6beac1bb8bf128e682d1951c3376b2dee9e"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "c4521869ef23497f7e465cb3ed1432339c29e4add71a4d8096189ada7ebae1c6"
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
    "job_identifier",
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
    "local_classification",
    "printed_identifier",
    "exact_label",
    "exact_label_sha256",
    "parent_local_anchor_ids",
    "printed_subject",
    "classification_status",
)
PURPOSE_KEYS = (
    "local_field_purpose_classification_id",
    "source_occurrence_id",
    "field_purpose",
    "supported_local_anchor_ids",
    "exact_prompt",
    "exact_prompt_sha256",
    "classification_status",
)
REPEAT_KEYS = (
    "local_repeat_or_alias_evidence_id",
    "source_occurrence_id",
    "alias_relation",
    "alias_local_anchor_id",
    "canonical_local_anchor_id",
    "evidence_occurrence_ids",
    "printed_target",
    "resolution_status",
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
    "subject_kind",
    "subject_id",
    "note_kind",
    "note",
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        + "\n"
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _content_digest(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _digest(preimage)


def _expect_keys(
    row: Mapping[str, Any], keys: Sequence[str], label: str
) -> None:
    if tuple(row.keys()) != tuple(keys):
        raise ValueError(f"{label} keyset drift: {tuple(row.keys())!r}")


def _strict_load(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} missing at {path}")
    return json.loads(path.read_bytes())


def _default_capture_root() -> Path:
    psid_root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR",
            "/Users/maxghenis/PolicyEngine/psid-data",
        )
    )
    return psid_root / "documentation/capture1"


def _load_replay_and_index() -> tuple[dict[str, Any], dict[str, Any]]:
    replay_raw = REPLAY_PATH.read_bytes()
    if _sha256(replay_raw) != REPLAY_RAW_SHA256:
        raise ValueError("stage-1 source replay raw identity drift")
    replay = json.loads(replay_raw)
    if _content_digest(replay) != REPLAY_CONTENT_SHA256:
        raise ValueError("stage-1 source replay content identity drift")

    index_raw = INDEX_PATH.read_bytes()
    if _sha256(index_raw) != INDEX_RAW_SHA256:
        raise ValueError("stage-1 candidate index raw identity drift")
    index = json.loads(index_raw)
    if _content_digest(index) != INDEX_CONTENT_SHA256:
        raise ValueError("stage-1 candidate index content identity drift")
    return replay, index


def _load_candidate(index: Mapping[str, Any]) -> dict[str, Any]:
    manifest = [
        row
        for row in index["document_candidate_manifest_rows"]
        if row["document_source_position"] == DOCUMENT_POSITION
    ]
    if len(manifest) != 1:
        raise ValueError("document-36 candidate manifest is not a singleton")
    row = manifest[0]
    if (
        row["source_document_id"] != DOCUMENT_ID
        or row["canonical_source_path"] != CANONICAL_SOURCE_PATH
        or row["interview_wave"] != INTERVIEW_WAVE
        or row["page_count"] != PAGE_COUNT
        or row["raw_sha256"] != CANDIDATE_RAW_SHA256
        or row["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or row["candidate_payload_sha256"] != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-36 candidate manifest identity drift")

    raw = CANDIDATE_PATH.read_bytes()
    if _sha256(raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-36 candidate raw identity drift")
    candidate = json.loads(raw)
    if (
        _content_digest(candidate) != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-36 candidate content identity drift")
    if candidate["candidate_nonselection_law"]["auto_promotion_permitted"]:
        raise ValueError("candidate artifact claims auto promotion")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("q85.pdf whole-file identity drift")
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("pinned Poppler pdftotext version drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("q85.pdf page-count drift")
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
        raise ValueError("document-36 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-36 replay page text drift")
    observed_empty = tuple(
        index + 1 for index, text in enumerate(page_texts) if not text
    )
    if observed_empty != EMPTY_TEXT_PAGES:
        raise ValueError("document-36 empty-text page domain drift")
    return rows


def _trimmed_line_span(
    page_text: str, marker: str, ordinal: int | None = None
) -> tuple[int, int]:
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
    if not matches:
        raise ValueError(f"no physical line contains {marker!r}")
    if ordinal is None:
        if len(matches) > 1:
            raise ValueError(f"ambiguous physical line for {marker!r}")
        ordinal = 0
    if ordinal >= len(matches):
        raise ValueError(f"line ordinal {ordinal} out of range for {marker!r}")
    start_chars, end_chars = matches[ordinal]
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _needle_span(
    page_text: str, needle: str, ordinal: int | None = None
) -> tuple[int, int]:
    """Resolve a needle.

    ``ordinal`` of ``None`` requires the needle to be unique on the page.  An
    integer records that the reviewer inspected every hit and selected one.
    """
    hits: list[int] = []
    cursor = 0
    while True:
        found = page_text.find(needle, cursor)
        if found < 0:
            break
        hits.append(found)
        cursor = found + 1
    if not hits:
        raise ValueError(f"needle {needle!r} absent from page")
    if ordinal is None:
        if len(hits) > 1:
            raise ValueError(f"ambiguous needle {needle!r} ({len(hits)} hits)")
        ordinal = 0
    if ordinal >= len(hits):
        raise ValueError(f"needle ordinal {ordinal} out of range: {needle!r}")
    start_chars = hits[ordinal]
    end_chars = start_chars + len(needle)
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _block_span(
    page_text: str, start_marker: str, end_marker: str
) -> tuple[int, int]:
    start_chars = page_text.find(start_marker)
    if start_chars < 0:
        raise ValueError(f"block start {start_marker!r} absent")
    if page_text.find(start_marker, start_chars + 1) >= 0:
        raise ValueError(f"ambiguous block start {start_marker!r}")
    tail = page_text.find(end_marker, start_chars + len(start_marker))
    if tail < 0:
        raise ValueError(f"block end {end_marker!r} absent after start")
    end_chars = tail + len(end_marker)
    return (
        len(page_text[:start_chars].encode("utf-8")),
        len(page_text[:end_chars].encode("utf-8")),
    )


def _resolve_span(page_text: str, spec: Mapping[str, Any]) -> tuple[int, int]:
    if "utf8_byte_start" in spec:
        return spec["utf8_byte_start"], spec["utf8_byte_end"]
    if "needle" in spec:
        return _needle_span(page_text, spec["needle"], spec.get("ordinal"))
    if "start_marker" in spec:
        return _block_span(page_text, spec["start_marker"], spec["end_marker"])
    return _trimmed_line_span(
        page_text, spec["line_marker"], spec.get("ordinal")
    )


def _strict_slice(page_text: str, start: int, end: int) -> str:
    raw = page_text.encode("utf-8")
    if not 0 <= start < end <= len(raw):
        raise ValueError("span outside page byte domain")
    try:
        text = raw[start:end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("span is not character aligned") from error
    if not text:
        raise ValueError("empty matched text")
    return text


def _line(key: str, page: int, marker: str, **values: Any) -> dict[str, Any]:
    return {"key": key, "page": page, "line_marker": marker, **values}


def _needle(key: str, page: int, needle: str, **values: Any) -> dict[str, Any]:
    return {"key": key, "page": page, "needle": needle, **values}


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


# --------------------------------------------------------------------------
# Reviewer specification.
#
# Every row below is an explicit reviewer decision taken during the complete
# 67-page pass over q85.pdf.  Selectors name printed source text; the builder
# re-resolves each one against the authenticated page bytes.  Retention test:
# printed text is kept only where it establishes a document-local R_Q fact --
# a printed role designator, job referent, remuneration component, role total,
# farm/business aggregate, job or role context attribute, field-purpose
# prompt, conditional routing label, or repeat/cross-reference instruction.
# Non-employment subject matter, third-party occupations, and counterfactual
# job prose are rejected even where they carry work-like lexemes.
# --------------------------------------------------------------------------

HEAD = "head_or_reference_person"
SPOUSE = "spouse_or_partner"
JOB = ("job_slot", "source_job")
COMPONENT = ("component_slot", "source_remuneration_component")
CONTEXT = ("component_slot", "source_context")
ROLE_TOTAL = ("component_slot", "source_role_total")
FARM = ("component_slot", "source_farm_aggregate")
BUSINESS = ("component_slot", "source_business_aggregate")


def _role(key, page, sel, classification, identifier, subject, **kw):
    return {
        "key": key,
        "page": page,
        "kind": "role_anchor",
        "node_domain": "role",
        "classification": classification,
        "identifier": identifier,
        "subject": subject,
        **sel,
        **kw,
    }


def _anchor(key, page, sel, kind, domain_pair, identifier, subject, **kw):
    node_domain, classification = domain_pair
    return {
        "key": key,
        "page": page,
        "kind": kind,
        "node_domain": node_domain,
        "classification": classification,
        "identifier": identifier,
        "subject": subject,
        **sel,
        **kw,
    }


def _prompt(key, page, sel, purpose, supports, **kw):
    return {
        "key": key,
        "page": page,
        "kind": "field_purpose_prompt",
        "purpose": purpose,
        "supports": supports,
        **sel,
        **kw,
    }


def _branch(key, page, sel, parent=None, **kw):
    return {
        "key": key,
        "page": page,
        "kind": "flow_branch_label",
        "branch_parent": parent,
        **sel,
        **kw,
    }


def _repeat(key, page, sel, relation, alias, canonical, target, **kw):
    return {
        "key": key,
        "page": page,
        "kind": "repeat_or_alias_instruction",
        "alias_relation": relation,
        "alias_anchor": alias,
        "canonical_anchor": canonical,
        "printed_target": target,
        **sel,
        **kw,
    }


def N(needle, ordinal=None):
    return {"needle": needle, "ordinal": ordinal}


def L(marker, ordinal=None):
    return {"line_marker": marker, "ordinal": ordinal}


def B(start, end):
    return {"start_marker": start, "end_marker": end}


# Conditional routing labels retained from the review.  Only checkpoints that
# gate an employment or income item series are kept; marriage, children, and
# health checkpoints are rejected.
BRANCH_SPECS: tuple[dict[str, Any], ...] = (
    _branch("b_prev_same", 8, N("A. sit mmm")),
    _branch("b_prev_self", 8, N("n. sew-c7movw")),
    _branch("b_prev_diff", 8, N("c. DlP,encYI")),
    _branch("c_not_working", 11, L("C HEAD IS NOTWORKING")),
    _branch("c_prev_same", 14, N("A. SAME"), parent="c_not_working"),
    _branch("c_prev_self", 14, N("B. SELF-EMPLOYED"), parent="c_not_working"),
    _branch(
        "c_prev_diff", 14, N("DIFFERENT EMPLOYER"), parent="c_not_working"
    ),
    _branch("f_extra_job", 27, N("JOB1W1966")),
    _branch("f_all_others", 27, N("lb. ALLOTHERS")),
    _branch("j_prev_same", 43, N("k. s EMPLOYER")),
    _branch("j_prev_self", 43, N("8. SELF-EMPLOYED")),
    _branch("j_prev_diff", 43, N("C. DIFFEREWT")),
    _branch("k_not_working", 46, L("IS NOTWORKING NOW")),
    _branch("k_prev_same", 49, N("A. E UIPLOYCR"), parent="k_not_working"),
    _branch("k_prev_self", 49, N("*. SLLI-MPLOYLO"), parent="k_not_working"),
    _branch("k_prev_diff", 49, N("C. DIPILRLHI"), parent="k_not_working"),
)

C_PATH = ("c_not_working",)
K_PATH = ("k_not_working",)
B_PREV = ("b_prev_same", "b_prev_self", "b_prev_diff")
C_PREV = ("c_prev_same", "c_prev_self", "c_prev_diff")
J_PREV = ("j_prev_same", "j_prev_self", "j_prev_diff")
K_PREV = ("k_prev_same", "k_prev_self", "k_prev_diff")


# Establishing role designators.  Later lexical mentions of HEAD or
# WIFE/"WIFE" are not re-emitted as separate role anchors.
ROLE_SPECS: tuple[dict[str, Any], ...] = (
    _role("r_head_cover", 1, N("FOR HEADINTERVIEW:"), HEAD, "2.", "head"),
    _role(
        "r_wife_cover",
        1,
        N('FORWIFE/"WIFE" INTERVIEW:'),
        SPOUSE,
        "6.",
        "wife_or_wife_figure",
    ),
    _role("r_b1_head", 5, N("(HEAD)"), HEAD, "B1.", "head"),
    _role("r_b15_head", 5, N("(HEAD’S)"), HEAD, "B15.", "head"),
    _role("r_b18_head", 6, N("(HEAD)", 1), HEAD, "B18.", "head"),
    _role("r_b41_head", 7, N("(HEAD)", 2), HEAD, "B41.", "head"),
    _role("r_b79_head", 10, N("(HEAD)", 0), HEAD, "B79.", "head"),
    _role("r_c9_head", 12, N("(HEAD)"), HEAD, "C9.", "head", branches=C_PATH),
    _role(
        "r_c27_head",
        13,
        N("(HEAD'S)"),
        HEAD,
        "C27.",
        "head",
        branches=C_PATH,
    ),
    _role("r_f12_head", 26, N("(HEAD)", 0), HEAD, "F12.", "head"),
    _role("r_g5_head", 34, N("(NEW HEAD'S)"), HEAD, "G5.", "head"),
    _role(
        "r_j1f_wife",
        40,
        N("(WIFE/“WIFE”)", 0),
        SPOUSE,
        "J1f.",
        "wife_or_wife_figure",
    ),
    _role(
        "r_j15_wife",
        40,
        N('(WIFE’S/“WIFE’S")'),
        SPOUSE,
        "J15.",
        "wife_or_wife_figure",
    ),
    _role(
        "r_k9_wife",
        47,
        N("(WIFE/“WIFE”)"),
        SPOUSE,
        "K9.",
        "wife_or_wife_figure",
        branches=K_PATH,
    ),
    _role(
        "r_n5_wife",
        62,
        N("(WIFE’S/“WIFE'S\")"),
        SPOUSE,
        "N5.",
        "wife_or_wife_figure",
    ),
)


def _item(
    key,
    page,
    identifier,
    label,
    kind,
    domain_pair,
    purpose,
    *,
    parents=(),
    branches=(),
    subject="head",
    label_ordinal=None,
    prompt_end="?",
    prompt_start=None,
    role=None,
):
    """Emit one retained anchor plus the printed prompt that supports it."""
    anchor = _anchor(
        key,
        page,
        N(label, label_ordinal),
        kind,
        domain_pair,
        identifier,
        subject,
        parents=parents,
        branches=branches,
        role=role,
    )
    prompt = _prompt(
        key + "_prompt",
        page,
        B(prompt_start or identifier, prompt_end),
        purpose,
        (key,),
        branches=branches,
    )
    return (anchor, prompt)


def _flatten(*groups):
    rows: list[dict[str, Any]] = []
    for group in groups:
        for row in group:
            if isinstance(row, tuple):
                rows.extend(row)
            else:
                rows.append(row)
    return tuple(rows)


# Section B -- employment of head (pages 5-11).
SECTION_B = (
    _anchor(
        "b_section",
        5,
        N("SECTION B:EMPLOYMENTOFHEAD"),
        "context_anchor",
        CONTEXT,
        "SECTION B",
        "head",
        role="r_b1_head",
    ),
    _prompt(
        "b1_assignment_prompt",
        5,
        B("B1. B1We like", "a student,or what?"),
        "assignment",
        ("b_section",),
    ),
    _item(
        "b12_current_job",
        5,
        "B12.",
        "currentjob",
        "job_anchor",
        JOB,
        "job_identifier",
        role="r_b1_head",
    ),
    _item(
        "b15_occupation",
        5,
        "B15.",
        "mainoccupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("b12_current_job",),
        prompt_end="mainoccupation?",
    ),
    _item(
        "b17_industry",
        5,
        "B17.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("b12_current_job",),
    ),
    _item(
        "b18_main_job",
        6,
        "B18.",
        "mainjob",
        "job_anchor",
        JOB,
        "reporting_unit",
        role="r_b18_head",
    ),
    _item(
        "b19_salary",
        6,
        "B19.",
        "salary",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b18_main_job",),
        prompt_end="Howmuch is your",
    ),
    _item(
        "b22_hourly_wage",
        6,
        "B22.",
        "hourly wage rate",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b18_main_job",),
        prompt_end="What is your",
    ),
    _item(
        "b23_overtime_rate",
        6,
        "B23.",
        "hourlyrate",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b18_main_job",),
        prompt_end="for overtime?",
    ),
    _item(
        "b21_extra_hour_pay",
        6,
        "B21.",
        "perhourfor",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b18_main_job",),
        prompt_end="About how",
    ),
    _item(
        "b25_hour_earnings",
        6,
        "B25.",
        "earn forthat hour",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b18_main_job",),
    ),
    _item(
        "b35_employer_years",
        7,
        "B35.",
        "present employer",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b12_current_job",),
    ),
    _item(
        "b36_start_date",
        7,
        "B36.",
        "In whatmonth and\n                    yeardid you",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b12_current_job",),
        prompt_end="worksituation)?",
    ),
    _item(
        "b38_starting_wage",
        7,
        "B38.",
        "starting salary",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b12_current_job",),
        prompt_end="at that time?",
    ),
    _item(
        "b39_weekly_hours",
        7,
        "B39.",
        "hours a\n                            week did youwork?",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b12_current_job",),
    ),
    _item(
        "b41_prior_situation",
        7,
        "B41.",
        "another positionwiththesame employer",
        "job_anchor",
        JOB,
        "assignment",
        role="r_b41_head",
        prompt_start="B41. Wewant toknow",
        prompt_end="weredoingjust beforeyoustartedyourcurrent",
    ),
    _item(
        "b45_prior_end",
        7,
        "B45.",
        "andyeardid that (position/work",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b41_prior_situation",),
        prompt_end="situation) end?",
    ),
)


# Section C -- head is not working now (pages 11-17), gated by c_not_working.
SECTION_C = (
    _item(
        "c3_sought_job",
        11,
        "C3.",
        "kindof jobareyou",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=C_PATH,
        prompt_start="C3.What\n                                                                                          kindof jobareyou",
        prompt_end="lookingfor?",
    ),
    _item(
        "c5_lowest_wage",
        11,
        "C3.What",
        "lowestwaqe",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c3_sought_job",),
        branches=C_PATH,
        prompt_start="C3.What\n                                                                                          is thelowestwaqe",
        prompt_end="acceptonanyjob?",
    ),
    _item(
        "c6_search_duration",
        11,
        "C6.",
        "longhaveyoubeenlookingfor work",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c3_sought_job",),
        branches=C_PATH,
    ),
    _item(
        "c9_ever_worked",
        12,
        "C9",
        "everdoneanyworkfor money",
        "context_anchor",
        CONTEXT,
        "assignment",
        branches=C_PATH,
        prompt_end="everdoneanyworkfor money?",
    ),
    _item(
        "c10_last_worked",
        12,
        "C10.",
        "Whendid youlast work",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c9_ever_worked",),
        branches=C_PATH,
        prompt_end="did youlast work?",
    ),
    _item(
        "c17_last_job",
        12,
        "C17.",
        "last job",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=C_PATH,
        label_ordinal=1,
        prompt_end="onyourlast job?",
    ),
    _item(
        "c17_occupation",
        12,
        "C17.What",
        "wasyouroccupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("c17_last_job",),
        branches=C_PATH,
        prompt_end="wasyouroccupation",
    ),
    _item(
        "c19_industry",
        12,
        "C19.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("c17_last_job",),
        branches=C_PATH,
    ),
    _item(
        "c21_government_level",
        12,
        "C21.",
        "thefederal,state,or",
        "context_anchor",
        CONTEXT,
        "government_level",
        parents=("c17_last_job",),
        branches=C_PATH,
        prompt_end="localgovernment,a privatecompany,or what?",
    ),
    _item(
        "c27_final_wage",
        13,
        "C27.",
        "final wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c17_last_job",),
        branches=C_PATH,
        prompt_end="final wage",
    ),
    _item(
        "c28_weekly_hours",
        13,
        "C28.",
        "howmany hoursa week",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c17_last_job",),
        branches=C_PATH,
    ),
    _item(
        "c29_start_date",
        13,
        "C29.",
        "start working",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c17_last_job",),
        branches=C_PATH,
        prompt_end="start working",
    ),
    _item(
        "c31_starting_wage",
        13,
        "C31.",
        "startingsalaryor wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c17_last_job",),
        branches=C_PATH,
        prompt_end="at that time?",
    ),
    _item(
        "c33_prior_situation",
        13,
        "C33.",
        "anotherpositionwiththesame  emplover",
        "job_anchor",
        JOB,
        "assignment",
        branches=C_PATH,
        prompt_end="weredoingjust beforeyoustartedthat (position/",
    ),
    _item(
        "c38_government_level",
        14,
        "C38.",
        "federal,state,or localgovernment",
        "context_anchor",
        CONTEXT,
        "government_level",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="a privatecompany,\n                                  or what?",
    ),
    _item(
        "c39_industry",
        14,
        "C39.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("c33_prior_situation",),
        branches=C_PREV,
    ),
    _item(
        "c40_occupation",
        14,
        "C40.",
        "occupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="occupation",
    ),
    _item(
        "c42_final_wage",
        14,
        "C42.",
        "final wage or",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="final wage or",
    ),
    _item(
        "c44_start_date",
        14,
        "C44.",
        "start working in",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="start working in",
    ),
    _item(
        "c46_starting_wage",
        14,
        "C46.",
        "startingsalaryor wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="at that time?",
    ),
    _item(
        "c47_weekly_hours",
        14,
        "C47.",
        "howmany\n                                                                                             hoursa week",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("c33_prior_situation",),
        branches=C_PREV,
        prompt_end="did youwork?",
    ),
    _item(
        "c68_extra_job",
        16,
        "C68.",
        "extra job or other way of making money",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=C_PATH,
        prompt_end="in 1984?",
    ),
    _item(
        "c71_extra_earnings",
        16,
        "C71.",
        "makeat this",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("c68_extra_job",),
        branches=C_PATH,
        prompt_end="makeat this?",
    ),
    _item(
        "c92_lifetime_years",
        17,
        "C92.",
        "worked  for moneysinceyouwere18",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=C_PATH,
        prompt_end="sinceyouwere18?",
    ),
)


# Section F -- income (pages 26-33).  Farm and business aggregates, head and
# spouse remuneration, and the printed other-FU-member job grid.
SECTION_F = (
    _item(
        "f3_farm_receipts",
        26,
        "F1. What were your total receipts",
        "total receipts from farming",
        "farm_aggregate_anchor",
        FARM,
        "amount",
        prompt_end="commodity credit loans?",
    ),
    _item(
        "f4_farm_expenses",
        26,
        "F4.",
        "total operating expenses",
        "farm_aggregate_anchor",
        FARM,
        "amount",
        parents=("f3_farm_receipts",),
        prompt_end="living expenses?",
    ),
    _item(
        "f5_farm_net",
        26,
        "F5.",
        "net income from farming",
        "farm_aggregate_anchor",
        FARM,
        "amount",
        parents=("f3_farm_receipts",),
        prompt_end="(A - B =)",
    ),
    _item(
        "f6_business",
        26,
        "F6.",
        "own a business",
        "business_aggregate_anchor",
        BUSINESS,
        "amount",
        prompt_end="own a business at any time in 1984 or",
    ),
    _item(
        "f9_business_work_time",
        26,
        "F9.",
        "put in any work time for this business",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("f6_business",),
        prompt_end="in 1984?",
    ),
    _item(
        "f10_incorporation",
        26,
        "F10.",
        "corporationor anunincorporated",
        "context_anchor",
        CONTEXT,
        "incorporation",
        parents=("f6_business",),
        prompt_end="haveaninterestin bothkinds?",
    ),
    _item(
        "f11_business_share",
        26,
        "F11.",
        "shareof thetotal  income fromthebusiness",
        "business_aggregate_anchor",
        BUSINESS,
        "amount",
        parents=("f6_business",),
        prompt_end="shareof thetotal  income fromthebusiness",
    ),
    _item(
        "f12_wages_salaries",
        26,
        "F12.",
        "earnanymoney  fromwagesandsalariesin 1984",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        prompt_end="earnanymoney  fromwagesandsalariesin 1984?",
    ),
    _item(
        "f13_wages_total",
        26,
        "F13.",
        "altogether from wages and",
        "role_total_anchor",
        ROLE_TOTAL,
        "amount",
        parents=("f12_wages_salaries",),
        prompt_end="altogether from wages and",
    ),
    _item(
        "f14_bonus_overtime",
        26,
        "F14.",
        "income from bonuses,",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("f12_wages_salaries",),
        prompt_end="In addition to this, did you",
    ),
    _item(
        "f18_professional_practice",
        26,
        "F16. I’mgoingto readyoua list",
        "practiceor trade",
        "business_aggregate_anchor",
        BUSINESS,
        "amount",
        prompt_end="of othersourcesof income",
    ),
    _item(
        "f24_extra_job_earnings",
        27,
        "F24.",
        "earnfromyourextrajobs",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        branches=("f_extra_job",),
        prompt_end="In 1984?",
    ),
    _item(
        "f51_spouse_work_earnings",
        28,
        "F51.",
        "earnings from her work",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        subject="wife_or_wife_figure",
        prompt_end="from her work?",
    ),
    _item(
        "f52_spouse_total",
        28,
        "F52.",
        "earn altogether from work",
        "role_total_anchor",
        ROLE_TOTAL,
        "amount",
        parents=("f51_spouse_work_earnings",),
        subject="wife_or_wife_figure",
        prompt_end="was deducted fro taxes or other things?",
    ),
)


def _other_fu(page, tag, spec):
    """The printed other-FU-member employment grid on pages 30-32.

    Page-level OCR differs between the three printed member panels, so each
    panel names its own verified selectors rather than sharing a template.
    """
    return (
        _item(
            f"{tag}_job",
            page,
            spec["job_id"],
            spec["job"],
            "job_anchor",
            JOB,
            "job_identifier",
            subject="other_fu_member",
            prompt_end=spec["job_end"],
        ),
        _item(
            f"{tag}_occupation",
            page,
            spec["occ_id"],
            spec["occ"],
            "context_anchor",
            CONTEXT,
            "occupation",
            parents=(f"{tag}_job",),
            subject="other_fu_member",
            prompt_end=spec["occ_end"],
        ),
        _item(
            f"{tag}_earnings",
            page,
            spec["earn_id"],
            spec["earn"],
            "remuneration_component_anchor",
            COMPONENT,
            "amount",
            parents=(f"{tag}_job",),
            subject="other_fu_member",
            prompt_end=spec["earn_end"],
        ),
        _item(
            f"{tag}_weeks",
            page,
            spec["weeks_id"],
            spec["weeks"],
            "context_anchor",
            CONTEXT,
            "month_or_exposure",
            parents=(f"{tag}_job",),
            subject="other_fu_member",
            prompt_end=spec["weeks"],
        ),
        _item(
            f"{tag}_hours",
            page,
            spec["hours_id"],
            spec["hours"],
            "context_anchor",
            CONTEXT,
            "month_or_exposure",
            parents=(f"{tag}_job",),
            subject="other_fu_member",
            prompt_end=spec["hours_end"],
        ),
        _item(
            f"{tag}_other_jobs",
            page,
            spec["other_id"],
            spec["other"],
            "job_anchor",
            JOB,
            "job_identifier",
            subject="other_fu_member",
            prompt_end="other jobs in 1984?",
        ),
    )


OTHER_FU_PANELS = (
    (
        30,
        "fu_a",
        {
            "job_id": "F76.",
            "job": "a full-time of part-time nob",
            "job_end": "the house):",
            "occ_id": "F77.",
            "occ": "kindof workdid",
            "occ_end": "usuallydo?",
            "earn_id": "F78.",
            "earn": "earn from",
            "earn_end": "About how much",
            "weeks_id": "F79.",
            "weeks": "Abouthowmany  weeks",
            "hours_id": "F81.",
            "hours": "how many hours did",
            "hours_end": "per week?",
            "other_id": "F82.",
            "other": "F82. Did (he/she) have any",
        },
    ),
    (
        31,
        "fu_b",
        {
            "job_id": "F76.",
            "job": "a full-time or part-time job",
            "job_end": "thehouse)?",
            "occ_id": "F77.",
            "occ": "kindof workdid",
            "occ_end": "usuallydo?",
            "earn_id": "F78.",
            "earn": "earn from",
            "earn_end": "that job last year?",
            "weeks_id": "F79.",
            "weeks": "Abouthowmany  week,",
            "hours_id": "F81.",
            "hours": "howmany hoursdid",
            "hours_end": "perweek?",
            "other_id": "F82.",
            "other": "F82.Did (he/she) have any",
        },
    ),
    (
        32,
        "fu_c",
        {
            "job_id": "F76.",
            "job": "a full-time job",
            "job_end": "the house?",
            "occ_id": "F77.",
            "occ": "kindof workdid",
            "occ_end": "usuallydo?",
            "earn_id": "F78.",
            "earn": "earnfrom",
            "earn_end": "Abouthowmuch  money",
            "weeks_id": "F79.",
            "weeks": "Abouthowmany   weeks",
            "hours_id": "F81.",
            "hours": "howmany hoursdid",
            "hours_end": "perweek?",
            "other_id": "F92.",
            "other": "F92. Did(he/she)haveany",
        },
    ),
)

SECTION_F_OTHER_FU = _flatten(
    *[_other_fu(page, tag, spec) for page, tag, spec in OTHER_FU_PANELS]
)


# Section G -- background of head (page 34).
SECTION_G = (
    _item(
        "g5_first_job",
        34,
        "G5.",
        "first full-time regular job",
        "job_anchor",
        JOB,
        "job_identifier",
        role="r_g5_head",
        prompt_end="what did you do?",
    ),
    _item(
        "g6_occupation",
        34,
        "G6.",
        "same occupation you started in",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("g5_first_job",),
        prompt_end="Have you had a number of different kinds of jobs, or have you mostly worked in the",
    ),
)

# Section N -- background of wife/"wife" (page 62).
SECTION_N = (
    _item(
        "n5_first_job",
        62,
        "N5.",
        "first full-time regularjob",
        "job_anchor",
        JOB,
        "job_identifier",
        role="r_n5_wife",
        subject="wife_or_wife_figure",
        prompt_end="first full-time regularjob",
    ),
    _item(
        "n6_occupation",
        62,
        "N6.",
        "of differentkindsof jobs",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("n5_first_job",),
        subject="wife_or_wife_figure",
        prompt_end="of differentkindsof jobs,or hav",
    ),
)


WIFE = "wife_or_wife_figure"

# Section J -- employment of wife/"wife" (pages 39-46).
SECTION_J = (
    _anchor(
        "j_section",
        39,
        N("J: EMPLOYMENT"),
        "context_anchor",
        CONTEXT,
        "SECTION J",
        WIFE,
        role="r_j1f_wife",
    ),
    _prompt(
        "j1f_assignment_prompt",
        40,
        B("J1f.", "a student,or what?"),
        "assignment",
        ("j_section",),
    ),
    _item(
        "j12_government_level",
        40,
        "J12.",
        "thefederal,stateor localgovernment",
        "context_anchor",
        CONTEXT,
        "government_level",
        subject=WIFE,
        prompt_end="or what?",
    ),
    _item(
        "j13_current_job",
        40,
        "J13.",
        "currentjob",
        "job_anchor",
        JOB,
        "job_identifier",
        subject=WIFE,
        role="r_j1f_wife",
    ),
    _item(
        "j15_occupation",
        40,
        "J15.",
        "mainoccupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("j13_current_job",),
        subject=WIFE,
        prompt_end="mainoccupation?",
    ),
    _item(
        "j17_industry",
        40,
        "J17.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("j13_current_job",),
        subject=WIFE,
    ),
    _item(
        "j18_main_job",
        41,
        "J18.",
        "mainjob",
        "job_anchor",
        JOB,
        "reporting_unit",
        subject=WIFE,
        prompt_end="or what?",
    ),
    _item(
        "j19_salary",
        41,
        "J19.",
        "salary?",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j18_main_job",),
        subject=WIFE,
        prompt_end="is your",
    ),
    _item(
        "j22_hourly_wage",
        41,
        "J22.",
        "hourlywage rate",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j18_main_job",),
        subject=WIFE,
        label_ordinal=0,
        prompt_end="is your",
    ),
    _item(
        "j23_overtime_rate",
        41,
        "J23.",
        "hourlywage rate",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j18_main_job",),
        subject=WIFE,
        label_ordinal=1,
        prompt_end="Whatis your",
    ),
    _item(
        "j21_extra_hour_pay",
        41,
        "J21.",
        "perhourfor",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j18_main_job",),
        subject=WIFE,
        prompt_end="Abouthowmuch",
    ),
    _item(
        "j25_hour_earnings",
        41,
        "J25.",
        "earnfor that hour",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j18_main_job",),
        subject=WIFE,
        prompt_end="earnfor that hour?",
    ),
    _item(
        "j35_employer_years",
        42,
        "J35.",
        "worked for your present",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j13_current_job",),
        subject=WIFE,
        prompt_end="worked for your present",
    ),
    _item(
        "j36_start_date",
        42,
        "J36.",
        "start working\n                                          in yourpresent",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j13_current_job",),
        subject=WIFE,
        prompt_end="in yourpresent(position)",
    ),
    _item(
        "j38_starting_wage",
        42,
        "J38.",
        "starting salary or wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j13_current_job",),
        subject=WIFE,
        prompt_end="at that time?",
    ),
    _item(
        "j41_prior_situation",
        42,
        "J41.",
        "another position with the same",
        "job_anchor",
        JOB,
        "assignment",
        subject=WIFE,
        prompt_end="self-employed, or what?",
    ),
    _item(
        "j47_government_level",
        43,
        "J47.",
        "federal, state, or local",
        "context_anchor",
        CONTEXT,
        "government_level",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="a private company, or what?",
    ),
    _item(
        "j48_industry",
        43,
        "J48.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
    ),
    _item(
        "j49_occupation",
        43,
        "J49.",
        "occupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="occupation?",
    ),
    _item(
        "j51_final_wage",
        43,
        "J51.",
        "final wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="final wage",
    ),
    _item(
        "j52_weekly_hours",
        43,
        "J52.",
        "howmany\n               hoursa week",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="did youwork?",
    ),
    _item(
        "j53_start_date",
        43,
        "J53.",
        "start working",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="start working",
    ),
    _item(
        "j55_starting_wage",
        43,
        "J55.",
        "startingsalaryor wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j41_prior_situation",),
        branches=J_PREV,
        subject=WIFE,
        prompt_end="at that time?",
    ),
    _item(
        "j79_extra_job",
        45,
        "J79.",
        "an extra job or other way of making money",
        "job_anchor",
        JOB,
        "job_identifier",
        subject=WIFE,
        prompt_end="your main job in 1984?",
    ),
    _item(
        "j82_extra_earnings",
        45,
        "J82.",
        "makeat this",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("j79_extra_job",),
        subject=WIFE,
        prompt_end="makeat this?",
    ),
    _item(
        "j110_lifetime_years",
        46,
        "J110.",
        "workedfor money",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        subject=WIFE,
        prompt_end="sinceyouwere",
    ),
)

# Section K -- wife/"wife" is not working now (pages 46-52).
SECTION_K = (
    _item(
        "k3_sought_job",
        46,
        "K3.",
        "kindof job areyou",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="lookingfor?",
    ),
    _item(
        "k5_lowest_wage",
        46,
        "K5.",
        "lowestwage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k3_sought_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="acceptonmy job?",
    ),
    _item(
        "k9_ever_worked",
        47,
        "K9.",
        "everdoneanyworkfor money",
        "context_anchor",
        CONTEXT,
        "assignment",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="everdoneanyworkfor money?",
    ),
    _item(
        "k10_last_worked",
        47,
        "K10.",
        "did youlast work?",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("k9_ever_worked",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="did youlast work?",
    ),
    _item(
        "k17_last_job",
        47,
        "K17.",
        "last job",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=K_PATH,
        subject=WIFE,
        label_ordinal=1,
        prompt_end="onyourlast job?",
    ),
    _item(
        "k19_industry",
        47,
        "K19.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
    ),
    _item(
        "k21_government_level",
        47,
        "K21.",
        "thefedera1,state,or",
        "context_anchor",
        CONTEXT,
        "government_level",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="a privatecompany,or what?",
    ),
    _item(
        "k27_final_wage",
        48,
        "K27.",
        "final wage or salary",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="final wage or salary",
    ),
    _item(
        "k28_weekly_hours",
        48,
        "K28.",
        "howmany  hours a\n                         week",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="did youwork?",
    ),
    _item(
        "k29_start_date",
        48,
        "K29.",
        "start workingin that",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="start workingin that",
    ),
    _item(
        "k31_starting_wage",
        48,
        "K31.",
        "startingsalaryor wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k17_last_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="at that time?",
    ),
    _item(
        "k33_prior_situation",
        48,
        "K33.",
        "weredoingjust beforeyoustartedthat",
        "job_anchor",
        JOB,
        "assignment",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="weredoingjust beforeyoustartedthat",
    ),
    _item(
        "k38_government_level",
        49,
        "K38.",
        "federal, state, or local",
        "context_anchor",
        CONTEXT,
        "government_level",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
        prompt_end="a private company, or what?",
    ),
    _item(
        "k39_industry",
        49,
        "K39.",
        "kindof business",
        "context_anchor",
        CONTEXT,
        "industry",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
    ),
    _item(
        "k40_occupation",
        49,
        "K40.",
        "occupation",
        "context_anchor",
        CONTEXT,
        "occupation",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
        prompt_end="occupation?",
    ),
    _item(
        "k42_final_wage",
        49,
        "K42.",
        "final wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
        prompt_end="final wage",
    ),
    _item(
        "k44_start_date",
        49,
        "K44.",
        "start working",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
        prompt_end="start working",
    ),
    _item(
        "k46_starting_wage",
        49,
        "K46.",
        "startingsalaryor wage",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k33_prior_situation",),
        branches=K_PREV,
        subject=WIFE,
        prompt_end="at that time?",
    ),
    _item(
        "k68_extra_job",
        51,
        "K68.",
        "anextrajobor otherwayof making",
        "job_anchor",
        JOB,
        "job_identifier",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="mainjobin 1984?",
    ),
    _item(
        "k71_extra_earnings",
        51,
        "K71.",
        "make at this",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("k68_extra_job",),
        branches=K_PATH,
        subject=WIFE,
        prompt_end="make at this?",
    ),
    _item(
        "k92_lifetime_years",
        52,
        "k92.",
        "worked for money since",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="worked for money since",
    ),
)


# Main-job exposure totals and extra-job blocks completed on the second review
# pass over pages 9-11, 15, 44-45, 50-51.
EXPOSURE_AND_EXTRA = (
    _item(
        "b75_main_job_weeks",
        9,
        "B75.",
        "did youactuallyworkonyourmainjobin",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b18_main_job",),
        prompt_end="1984?",
    ),
    _item(
        "b76_main_job_hours",
        9,
        "B76.\n",
        "hoursa weekdid youworkonyourmainjobin 1984",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("b18_main_job",),
        prompt_end="in 1984?",
    ),
    _item(
        "b79_extra_job",
        10,
        "B79.",
        "anextrajobor otherway ofmaking",
        "job_anchor",
        JOB,
        "job_identifier",
        role="r_b79_head",
        prompt_end="mainjob in 1984?",
    ),
    _item(
        "b82_extra_earnings",
        10,
        "B82.",
        "make\n                at this",
        "remuneration_component_anchor",
        COMPONENT,
        "amount",
        parents=("b79_extra_job",),
        prompt_end="make\n                at this?",
    ),
    _item(
        "b110_lifetime_years",
        11,
        "B110.",
        "worked\n                                            for money",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        prompt_end="sinceyouwere18?",
    ),
    _item(
        "c66_main_job_weeks",
        15,
        "C66.",
        "weeksdid youactuallyworkonyourmainjobin",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=C_PATH,
        prompt_end="weeksdid youactuallyworkonyourmainjobin",
    ),
    _item(
        "c67_main_job_hours",
        15,
        "C67.",
        "did youworkonyourmainjobIn 1984",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=C_PATH,
        prompt_end="mainjobIn 1984?",
    ),
    _item(
        "j75_main_job_weeks",
        44,
        "J75.",
        "weeks did youactuallyworkonyourmainjobin",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j18_main_job",),
        subject=WIFE,
        prompt_end="weeks did youactuallyworkonyourmainjobin",
    ),
    _item(
        "j76_main_job_hours",
        44,
        "J76.",
        "howmanyhoursa week did youworkonyourmainjobin 1985",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        parents=("j18_main_job",),
        subject=WIFE,
        prompt_end="mainjobin 1985?",
    ),
    _item(
        "k66_main_job_weeks",
        50,
        "K66.",
        "howmanyweeksdid youactuallyworkon yourmainjobin",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="howmanyweeksdid youactuallyworkon yourmainjobin",
    ),
    _item(
        "k67_main_job_hours",
        50,
        "K67.",
        "did youworkonyourmain job",
        "context_anchor",
        CONTEXT,
        "month_or_exposure",
        branches=K_PATH,
        subject=WIFE,
        prompt_end="in 1984?",
    ),
)

# Printed repeat and cross-reference instructions.
REPEAT_SPECS = (
    _repeat(
        "f23_extra_job_crossref",
        27,
        B("F23. Have you included your earnings", "talked about?"),
        "explicit_cross_reference",
        "f24_extra_job_earnings",
        "f13_wages_total",
        "F13. wages and salaries amount",
    ),
    _repeat(
        "b86_repeat_extra_job",
        10,
        N("966AGAIN m97 996AG6I5l A67"),
        "explicit_repeat_instruction",
        None,
        "b79_extra_job",
        "B80-B86 extra-job block",
    ),
    _repeat(
        "c75_repeat_extra_job",
        16,
        N("Cl5AGAIN Cl6 Cl5AGk1* Cl6"),
        "explicit_repeat_instruction",
        None,
        "c68_extra_job",
        "C69-C75 extra-job block",
    ),
    _repeat(
        "k75_repeat_extra_job",
        51,
        N("K75AGAIN        K16     1175AGAIN       K16"),
        "explicit_repeat_instruction",
        None,
        "k68_extra_job",
        "K69-K75 extra-job block",
    ),
    _repeat(
        "k91_repeat_extra_job",
        51,
        N("K91AGAlK P.100,1(92     .91AGAIN P.lOO.K92"),
        "explicit_repeat_instruction",
        None,
        "k68_extra_job",
        "K86-K91 extra-job block",
    ),
    _repeat(
        "fu_b_repeat_grid",
        31,
        N("FezAGAIN P. 59,FBI ,a2LGAIWP. 59.PB"),
        "explicit_repeat_instruction",
        None,
        "fu_b_job",
        "F77-F82 other-FU-member job grid",
    ),
    _repeat(
        "c14_work_history_supplement",
        14,
        N("NlS1011Y"),
        "explicit_cross_reference",
        None,
        "c33_prior_situation",
        "printed work-history supplement (outside this document)",
        unresolved=True,
    ),
    _repeat(
        "k47_work_history_supplement",
        49,
        N("sJPPLD4wr"),
        "explicit_cross_reference",
        None,
        "k33_prior_situation",
        "printed pink work-history supplement (outside this document)",
        unresolved=True,
    ),
    _repeat(
        "a2_wife_interview_crossref",
        2,
        B("A2. IF YOU ARE", "BEGIN INTERVIEW."),
        "explicit_cross_reference",
        None,
        "r_wife_cover",
        'J1e, P. 76 wife/"wife" interview entry',
    ),
)


OCCURRENCE_SPECS: tuple[dict[str, Any], ...] = _flatten(
    ROLE_SPECS,
    BRANCH_SPECS,
    SECTION_B,
    SECTION_C,
    SECTION_F,
    SECTION_F_OTHER_FU,
    SECTION_G,
    SECTION_J,
    SECTION_K,
    SECTION_N,
    EXPOSURE_AND_EXTRA,
    REPEAT_SPECS,
)
SPEC_BY_KEY = {spec["key"]: spec for spec in OCCURRENCE_SPECS}
if len(SPEC_BY_KEY) != len(OCCURRENCE_SPECS):
    raise ValueError("duplicate reviewer spec key")


def _path_sort_key(path: Sequence[str]) -> tuple[bytes, ...]:
    return tuple(element.encode("utf-8") for element in path)


def _locator() -> dict[str, Any]:
    preimage = [DOCUMENT_ID, INTERVIEW_WAVE, PDF_SHA256, PDF_SIZE]
    row = {
        "locator_id": "psid-whole-document:" + _digest(preimage),
        "source_document_id": DOCUMENT_ID,
        "interview_wave": INTERVIEW_WAVE,
        "filename": FILENAME,
        "location_type": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": PDF_SIZE,
        "size_bytes": PDF_SIZE,
        "full_file_sha256": PDF_SHA256,
        "range_sha256": PDF_SHA256,
        "pdf_page_domain": "all_pages_and_flow_branches",
    }
    _expect_keys(row, LOCATOR_KEYS, "whole-document locator")
    return row


def _locator_digest(
    page_number: int,
    start: int,
    end: int,
    index: int,
    ordinal: int,
    kind: str,
) -> str:
    return _digest(
        [
            DOCUMENT_ID,
            CANONICAL_SOURCE_PATH,
            "questionnaire_page_utf8_span",
            [
                INTERVIEW_WAVE,
                page_number,
                start,
                end,
                index,
                ordinal,
                kind,
            ],
        ]
    )


def _build_occurrences_and_branches(
    page_texts: Sequence[str], locator_id: str
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, str],
    dict[str, str],
]:
    resolved: list[dict[str, Any]] = []
    for spec in OCCURRENCE_SPECS:
        page_text = page_texts[spec["page"] - 1]
        start, end = _resolve_span(page_text, spec)
        text = _strict_slice(page_text, start, end)
        resolved.append(
            {
                "key": spec["key"],
                "spec": spec,
                "page_number": spec["page"],
                "start": start,
                "end": end,
                "kind": spec["kind"],
                "text": text,
            }
        )

    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in resolved:
        by_page[row["page_number"]].append(row)
    for page_number, rows in by_page.items():
        rows.sort(
            key=lambda row: (row["start"], row["end"], KIND_ORDER[row["kind"]])
        )
        seen: set[tuple[int, int, str]] = set()
        for index, row in enumerate(rows):
            coordinate = (row["start"], row["end"], row["kind"])
            if coordinate in seen:
                raise ValueError(
                    f"duplicate atomic span on page {page_number}: {row['key']}"
                )
            seen.add(coordinate)
            row["index"] = index
            row["ordinal"] = 0

    branch_paths: dict[str, list[str]] = {}
    occurrence_ids: dict[str, str] = {}
    branch_rows: list[dict[str, Any]] = []

    def _parent_path(spec: Mapping[str, Any]) -> list[str]:
        parent = spec.get("branch_parent")
        if parent is None:
            return [FLOW_ROOT]
        if parent not in branch_paths:
            raise ValueError(f"branch parent {parent} unresolved")
        return list(branch_paths[parent])

    def _emit(
        row: Mapping[str, Any], paths: list[list[str]]
    ) -> dict[str, Any]:
        digest = _locator_digest(
            row["page_number"],
            row["start"],
            row["end"],
            row["index"],
            row["ordinal"],
            row["kind"],
        )
        tail = [
            DOCUMENT_ID,
            locator_id,
            digest,
            INTERVIEW_WAVE,
            row["page_number"],
            row["start"],
            row["end"],
            row["index"],
            row["ordinal"],
            row["kind"],
            row["text"],
            _sha256(row["text"].encode("utf-8")),
            paths,
        ]
        emitted = {
            "questionnaire_occurrence_id": (
                "psid-questionnaire-occurrence:" + _digest(tail)
            ),
            "source_document_id": DOCUMENT_ID,
            "source_locator_id": locator_id,
            "source_locator_sha256": digest,
            "interview_wave": INTERVIEW_WAVE,
            "page_number": row["page_number"],
            "utf8_byte_start": row["start"],
            "utf8_byte_end": row["end"],
            "occurrence_index_on_page": row["index"],
            "semantic_ordinal_at_span": row["ordinal"],
            "occurrence_kind": row["kind"],
            "matched_text": row["text"],
            "matched_utf8_sha256": _sha256(row["text"].encode("utf-8")),
            "flow_branch_paths": paths,
        }
        _expect_keys(emitted, OCCURRENCE_KEYS, "occurrence")
        return emitted

    emitted_by_key: dict[str, dict[str, Any]] = {}

    # Branch labels resolve first, parents before children.
    pending = [row for row in resolved if row["kind"] == "flow_branch_label"]
    guard = 0
    while pending:
        guard += 1
        if guard > len(BRANCH_SPECS) + 2:
            raise ValueError("branch resolution failed to converge")
        deferred = []
        for row in pending:
            parent_key = row["spec"].get("branch_parent")
            if parent_key is not None and parent_key not in branch_paths:
                deferred.append(row)
                continue
            parent_path = _parent_path(row["spec"])
            emitted = _emit(row, [parent_path])
            emitted_by_key[row["key"]] = emitted
            occurrence_id = emitted["questionnaire_occurrence_id"]
            occurrence_ids[row["key"]] = occurrence_id
            parent_id = parent_path[-1]
            branch_id = "questionnaire-flow:" + _digest(
                [parent_id, INTERVIEW_WAVE, occurrence_id]
            )
            if branch_id in branch_paths.values():
                raise ValueError("duplicate branch id")
            path = parent_path + [branch_id]
            branch_paths[row["key"]] = path
            branch_row = {
                "flow_branch_id": branch_id,
                "parent_flow_branch_id": parent_id,
                "source_occurrence_id": occurrence_id,
                "branch_path": path,
                "interview_wave": INTERVIEW_WAVE,
                "source_locator_id": locator_id,
                "page_number": row["page_number"],
                "occurrence_index_on_page": row["index"],
                "branch_label": row["text"],
                "branch_label_sha256": _sha256(row["text"].encode("utf-8")),
            }
            _expect_keys(branch_row, BRANCH_KEYS, "flow branch")
            branch_rows.append(branch_row)
        if len(deferred) == len(pending):
            raise ValueError("unresolvable branch parent chain")
        pending = deferred

    for row in resolved:
        if row["kind"] == "flow_branch_label":
            continue
        leaves = row["spec"].get("branches") or ()
        if leaves:
            paths = sorted(
                (list(branch_paths[leaf]) for leaf in leaves),
                key=_path_sort_key,
            )
            if len({tuple(path) for path in paths}) != len(paths):
                raise ValueError(f"duplicate flow path on {row['key']}")
        else:
            paths = [[FLOW_ROOT]]
        emitted = _emit(row, paths)
        emitted_by_key[row["key"]] = emitted
        occurrence_ids[row["key"]] = emitted["questionnaire_occurrence_id"]

    occurrence_rows = sorted(
        emitted_by_key.values(),
        key=lambda row: (
            row["page_number"],
            row["occurrence_index_on_page"],
        ),
    )
    branch_rows.sort(
        key=lambda row: (row["page_number"], row["occurrence_index_on_page"])
    )
    spec_text = {row["key"]: row["text"] for row in resolved}
    return occurrence_rows, branch_rows, occurrence_ids, spec_text


def _page_rows(
    replay_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
    locator_id: str,
) -> list[dict[str, Any]]:
    by_page: dict[int, list[str]] = defaultdict(list)
    for row in occurrence_rows:
        by_page[row["page_number"]].append(row["questionnaire_occurrence_id"])
    rows = []
    for replay_row in replay_rows:
        page_number = replay_row["page_number"]
        digest = replay_row["page_text_utf8_sha256"]
        page_id = "psid-questionnaire-page:" + _digest(
            [DOCUMENT_ID, INTERVIEW_WAVE, page_number, digest]
        )
        if page_id != replay_row["questionnaire_page_id"]:
            raise ValueError("page ID preimage drift")
        row = {
            "questionnaire_page_id": page_id,
            "source_document_id": DOCUMENT_ID,
            "source_locator_id": locator_id,
            "interview_wave": INTERVIEW_WAVE,
            "page_number": page_number,
            "page_text_utf8_sha256": digest,
            "questionnaire_occurrence_ids": list(by_page[page_number]),
            "annotation_status": "complete",
        }
        _expect_keys(row, PAGE_KEYS, "page")
        rows.append(row)
    return rows


def _local_anchor_rows(
    occurrence_ids: Mapping[str, str], spec_text: Mapping[str, str]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    anchor_ids: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    anchor_specs = [
        spec
        for spec in OCCURRENCE_SPECS
        if spec["kind"]
        in {
            "role_anchor",
            "job_anchor",
            "remuneration_component_anchor",
            "role_total_anchor",
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
            "context_anchor",
        }
    ]
    for spec in anchor_specs:
        anchor_ids[spec["key"]] = "rq-local-anchor:" + _digest(
            [DOCUMENT_ID, spec["key"], occurrence_ids[spec["key"]]]
        )
    for spec in anchor_specs:
        parents = [anchor_ids[key] for key in spec.get("parents", ())]
        for key in spec.get("parents", ()):
            if key not in anchor_ids:
                raise ValueError(f"unknown parent anchor {key}")
        label = spec_text[spec["key"]]
        row = {
            "local_anchor_classification_id": anchor_ids[spec["key"]],
            "source_occurrence_id": occurrence_ids[spec["key"]],
            "node_domain": spec["node_domain"],
            "local_classification": spec["classification"],
            "printed_identifier": spec.get("identifier"),
            "exact_label": label,
            "exact_label_sha256": _sha256(label.encode("utf-8")),
            "parent_local_anchor_ids": parents,
            "printed_subject": spec.get("subject"),
            "classification_status": "complete_document_local_provisional",
        }
        _expect_keys(row, ANCHOR_KEYS, "local anchor")
        rows.append(row)
    return rows, anchor_ids


def _purpose_rows(
    occurrence_ids: Mapping[str, str],
    anchor_ids: Mapping[str, str],
    spec_text: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows = []
    for spec in OCCURRENCE_SPECS:
        if spec["kind"] != "field_purpose_prompt":
            continue
        if spec["purpose"] not in PURPOSE_ORDER:
            raise ValueError(f"unknown field purpose {spec['purpose']}")
        supported = [
            anchor_ids[key] for key in spec["supports"] if key in anchor_ids
        ]
        prompt = spec_text[spec["key"]]
        row = {
            "local_field_purpose_classification_id": (
                "rq-local-field-purpose:"
                + _digest(
                    [DOCUMENT_ID, spec["key"], occurrence_ids[spec["key"]]]
                )
            ),
            "source_occurrence_id": occurrence_ids[spec["key"]],
            "field_purpose": spec["purpose"],
            "supported_local_anchor_ids": supported,
            "exact_prompt": prompt,
            "exact_prompt_sha256": _sha256(prompt.encode("utf-8")),
            "classification_status": "complete_document_local_provisional",
        }
        _expect_keys(row, PURPOSE_KEYS, "field purpose")
        rows.append(row)
    return rows


def _repeat_rows(
    occurrence_ids: Mapping[str, str], anchor_ids: Mapping[str, str]
) -> list[dict[str, Any]]:
    rows = []
    for spec in OCCURRENCE_SPECS:
        if spec["kind"] != "repeat_or_alias_instruction":
            continue
        alias_key = spec.get("alias_anchor")
        canonical_key = spec.get("canonical_anchor")
        unresolved = bool(spec.get("unresolved"))
        evidence = [occurrence_ids[spec["key"]]]
        for key in (alias_key, canonical_key):
            if key and key in occurrence_ids:
                evidence.append(occurrence_ids[key])
        row = {
            "local_repeat_or_alias_evidence_id": (
                "rq-local-repeat:"
                + _digest(
                    [DOCUMENT_ID, spec["key"], occurrence_ids[spec["key"]]]
                )
            ),
            "source_occurrence_id": occurrence_ids[spec["key"]],
            "alias_relation": spec["alias_relation"],
            "alias_local_anchor_id": (
                anchor_ids.get(alias_key) if alias_key else None
            ),
            "canonical_local_anchor_id": (
                anchor_ids.get(canonical_key) if canonical_key else None
            ),
            "evidence_occurrence_ids": evidence,
            "printed_target": spec["printed_target"],
            "resolution_status": (
                "unresolved_printed_target_for_global_assembly"
                if unresolved
                else "locally_resolved_document_evidence"
            ),
        }
        _expect_keys(row, REPEAT_KEYS, "repeat or alias")
        rows.append(row)
    return rows


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


REJECT_REASONS = {
    "non_employment_subject_matter": (
        "printed text lies in a non-employment section (marital status, "
        "housing, children, marriage history, health, education, ethnicity, "
        "military, religion, or food) and establishes no R_Q fact"
    ),
    "detector_span_not_a_printed_unit": (
        "detector line span crosses the scanned two-column layout and is not "
        "the printed unit that carries the R_Q fact"
    ),
    "worklike_lexeme_without_r_q_fact": (
        "printed text carries a work-like lexeme but names no role, job, "
        "remuneration component, aggregate, or job context"
    ),
    "flow_path_not_reviewer_derived": (
        "detector flow-path alternative is a root fallback or bounded guess "
        "that does not resolve a printed conditional gate"
    ),
    "anchor_classification_without_retained_anchor": (
        "detector anchor classification hangs off an occurrence the reviewer "
        "rejected, so no local anchor row exists to carry it"
    ),
}


def _classify_rejection(
    candidate: Mapping[str, Any], employment_pages: frozenset[int]
) -> str:
    if candidate["page_number"] not in employment_pages:
        return "non_employment_subject_matter"
    if "\n" in candidate["matched_text"]:
        return "detector_span_not_a_printed_unit"
    return "worklike_lexeme_without_r_q_fact"


def _candidate_dispositions(
    candidate_artifact: Mapping[str, Any],
    locator_row: Mapping[str, Any],
    page_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
    anchor_rows: Sequence[Mapping[str, Any]],
    branch_rows: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, list[tuple[str, str]]],
]:
    dispositions: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    employment_pages = frozenset(row["page_number"] for row in occurrence_rows)

    def _note(subject_kind, subject_id, note_kind, note):
        row = {
            "correction_note_id": "rq-correction-note:"
            + _digest([subject_kind, subject_id, note_kind, note]),
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "note_kind": note_kind,
            "note": note,
        }
        _expect_keys(row, NOTE_KEYS, "correction note")
        notes.append(row)

    # 1. Whole-document locator.
    locator_candidate = candidate_artifact["whole_document_locator_candidate"]
    for field in (
        "source_document_id",
        "interview_wave",
        "filename",
        "byte_start",
        "byte_end",
        "size_bytes",
        "full_file_sha256",
        "range_sha256",
    ):
        if locator_candidate[field] != locator_row[field]:
            raise ValueError(f"locator field {field} disagrees with review")
    dispositions.append(
        {
            "candidate_row_kind": "whole_document_locator",
            "candidate_id": locator_candidate["candidate_locator_id"],
            "disposition": "accepted",
            "stage2_row_ids": [locator_row["locator_id"]],
            "adjudication_status": "complete",
        }
    )

    # 2. Pages.
    page_by_number = {row["page_number"]: row for row in page_rows}
    for candidate in candidate_artifact["candidate_page_rows"]:
        page_row = page_by_number[candidate["page_number"]]
        if (
            candidate["page_text_utf8_sha256"]
            != page_row["page_text_utf8_sha256"]
        ):
            raise ValueError("candidate page digest disagrees with review")
        dispositions.append(
            {
                "candidate_row_kind": "page",
                "candidate_id": candidate["candidate_page_id"],
                "disposition": "accepted",
                "stage2_row_ids": [page_row["questionnaire_page_id"]],
                "adjudication_status": "complete",
            }
        )

    # 3. Occurrences.
    retained_by_page: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in occurrence_rows:
        retained_by_page[row["page_number"]].append(row)
    named_by: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for candidate in candidate_artifact["candidate_occurrence_rows"]:
        candidate_id = candidate["candidate_occurrence_id"]
        page_number = candidate["page_number"]
        start = candidate["utf8_byte_start"]
        end = candidate["utf8_byte_end"]
        matches = [
            row
            for row in retained_by_page.get(page_number, ())
            if _overlaps(
                start, end, row["utf8_byte_start"], row["utf8_byte_end"]
            )
        ]
        if not matches:
            reason = _classify_rejection(candidate, employment_pages)
            dispositions.append(
                {
                    "candidate_row_kind": "occurrence",
                    "candidate_id": candidate_id,
                    "disposition": "rejected",
                    "stage2_row_ids": [],
                    "adjudication_status": "complete",
                }
            )
            _note(
                "candidate_occurrence",
                candidate_id,
                reason,
                f"page {page_number} bytes {start}..{end} "
                f"({candidate['occurrence_kind_candidate']}): "
                + REJECT_REASONS[reason],
            )
            continue
        if len(matches) > 1:
            disposition = "split"
        else:
            row = matches[0]
            exact = (
                start == row["utf8_byte_start"]
                and end == row["utf8_byte_end"]
                and candidate["occurrence_kind_candidate"]
                == row["occurrence_kind"]
            )
            disposition = "accepted" if exact else "modified"
        row_ids = [row["questionnaire_occurrence_id"] for row in matches]
        dispositions.append(
            {
                "candidate_row_kind": "occurrence",
                "candidate_id": candidate_id,
                "disposition": disposition,
                "stage2_row_ids": row_ids,
                "adjudication_status": "complete",
            }
        )
        if disposition != "accepted":
            row = matches[0]
            _note(
                "candidate_occurrence",
                candidate_id,
                (
                    "span_and_kind_re_derived"
                    if disposition == "modified"
                    else "candidate_split_across_printed_units"
                ),
                f"page {page_number}: detector span {start}..{end} "
                f"kind {candidate['occurrence_kind_candidate']} replaced by "
                + "; ".join(
                    f"{item['utf8_byte_start']}..{item['utf8_byte_end']} "
                    f"kind {item['occurrence_kind']}"
                    for item in matches
                ),
            )

    # 4. Flow-path candidates.  The reviewer flow model is derived from the
    # printed conditional gates, not from detector alternatives.
    branch_occurrence_ids = {
        row["source_occurrence_id"] for row in branch_rows
    }
    candidate_to_rows = {
        row["candidate_id"]: row["stage2_row_ids"]
        for row in dispositions
        if row["candidate_row_kind"] == "occurrence"
    }
    for candidate in candidate_artifact["candidate_flow_path_rows"]:
        candidate_id = candidate["candidate_flow_path_id"]
        source = candidate["source_candidate_occurrence_id"]
        mapped = [
            row_id
            for row_id in candidate_to_rows.get(source, [])
            if row_id in branch_occurrence_ids
        ]
        if mapped:
            branch_ids = [
                row["flow_branch_id"]
                for row in branch_rows
                if row["source_occurrence_id"] in mapped
            ]
            dispositions.append(
                {
                    "candidate_row_kind": "flow_path",
                    "candidate_id": candidate_id,
                    "disposition": "modified",
                    "stage2_row_ids": branch_ids,
                    "adjudication_status": "complete",
                }
            )
            _note(
                "candidate_flow_path",
                candidate_id,
                "branch_path_re_derived",
                "detector branch-path alternative replaced by the "
                "reviewer-derived root-to-leaf path for "
                + ", ".join(branch_ids),
            )
            continue
        dispositions.append(
            {
                "candidate_row_kind": "flow_path",
                "candidate_id": candidate_id,
                "disposition": "rejected",
                "stage2_row_ids": [],
                "adjudication_status": "complete",
            }
        )
        _note(
            "candidate_flow_path",
            candidate_id,
            "flow_path_not_reviewer_derived",
            REJECT_REASONS["flow_path_not_reviewer_derived"],
        )

    # 5. Anchor-classification candidates.
    anchor_by_occurrence = {
        row["source_occurrence_id"]: row for row in anchor_rows
    }
    for candidate in candidate_artifact[
        "candidate_anchor_classification_rows"
    ]:
        candidate_id = candidate["candidate_anchor_classification_id"]
        source = candidate["source_candidate_occurrence_id"]
        mapped = [
            anchor_by_occurrence[row_id]
            for row_id in candidate_to_rows.get(source, [])
            if row_id in anchor_by_occurrence
        ]
        if not mapped:
            dispositions.append(
                {
                    "candidate_row_kind": "anchor_classification",
                    "candidate_id": candidate_id,
                    "disposition": "rejected",
                    "stage2_row_ids": [],
                    "adjudication_status": "complete",
                }
            )
            _note(
                "candidate_anchor_classification",
                candidate_id,
                "anchor_classification_without_retained_anchor",
                REJECT_REASONS[
                    "anchor_classification_without_retained_anchor"
                ],
            )
            continue
        row_ids = [row["local_anchor_classification_id"] for row in mapped]
        exact = (
            len(mapped) == 1
            and candidate["classification_candidate"]
            == mapped[0]["local_classification"]
        )
        disposition = (
            "accepted"
            if exact
            else ("split" if len(mapped) > 1 else "modified")
        )
        dispositions.append(
            {
                "candidate_row_kind": "anchor_classification",
                "candidate_id": candidate_id,
                "disposition": disposition,
                "stage2_row_ids": row_ids,
                "adjudication_status": "complete",
            }
        )
        if disposition != "accepted":
            _note(
                "candidate_anchor_classification",
                candidate_id,
                "local_classification_re_derived",
                f"detector classification "
                f"{candidate['classification_candidate']!r} replaced by "
                + ", ".join(row["local_classification"] for row in mapped),
            )

    for row in dispositions:
        _expect_keys(row, DISPOSITION_KEYS, "candidate disposition")
    named_by.clear()
    for row in dispositions:
        for row_id in row["stage2_row_ids"]:
            named_by[row_id].append((row["candidate_id"], row["disposition"]))
    return dispositions, notes, named_by


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
    (
        "local_repeat_or_alias_evidence_rows",
        ("local_repeat_or_alias_evidence_id",),
    ),
    ("candidate_disposition_rows", ("candidate_row_kind", "candidate_id")),
    ("output_adjudication_rows", ("stage2_row_kind", "stage2_row_id")),
    ("correction_note_rows", ("correction_note_id",)),
)

OUTPUT_ROW_DOMAINS = (
    ("whole_document_locator", "whole_document_locator_rows", "locator_id"),
    ("questionnaire_page", "questionnaire_page_rows", "questionnaire_page_id"),
    (
        "questionnaire_occurrence",
        "questionnaire_occurrence_rows",
        "questionnaire_occurrence_id",
    ),
    ("flow_branch", "flow_branch_rows", "flow_branch_id"),
    (
        "local_anchor_classification",
        "local_anchor_classification_rows",
        "local_anchor_classification_id",
    ),
    (
        "local_field_purpose_classification",
        "local_field_purpose_classification_rows",
        "local_field_purpose_classification_id",
    ),
    (
        "local_repeat_or_alias_evidence",
        "local_repeat_or_alias_evidence_rows",
        "local_repeat_or_alias_evidence_id",
    ),
)

ACTION_PRECEDENCE = ("accepted", "modified", "split")
ACTION_NAMES = {
    "accepted": "candidate_accepted",
    "modified": "candidate_modified",
    "split": "candidate_split",
}


def _output_adjudications(
    value: Mapping[str, Any],
    named_by: Mapping[str, list[tuple[str, str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    for kind, domain, id_field in OUTPUT_ROW_DOMAINS:
        for row in value[domain]:
            row_id = row[id_field]
            naming = sorted(set(named_by.get(row_id, ())))
            if naming:
                dispositions = {item[1] for item in naming}
                action = next(
                    ACTION_NAMES[name]
                    for name in ACTION_PRECEDENCE
                    if name in dispositions
                )
                candidate_ids = sorted({item[0] for item in naming})
            else:
                action = "manual_add"
                candidate_ids = []
            adjudication = {
                "stage2_row_kind": kind,
                "stage2_row_id": row_id,
                "source_candidate_ids": candidate_ids,
                "adjudication_action": action,
                "whole_page_review_complete": True,
                "source_span_verified": True,
                "adjudication_status": "complete",
            }
            _expect_keys(
                adjudication, ADJUDICATION_KEYS, "output adjudication"
            )
            rows.append(adjudication)
            if action == "manual_add":
                note = (
                    "reviewer addition emitted after the complete whole-page "
                    "review; the detector produced no candidate over this "
                    "printed unit and the span was re-sliced from the "
                    "authenticated page bytes"
                )
                notes.append(
                    {
                        "correction_note_id": "rq-correction-note:"
                        + _digest([kind, row_id, "manual_add", note]),
                        "subject_kind": kind,
                        "subject_id": row_id,
                        "note_kind": "manual_add",
                        "note": note,
                    }
                )
    return rows, notes


def _row_keyset(
    rows: Sequence[Mapping[str, Any]], key_fields: Sequence[str]
) -> list[list[Any]]:
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
    "status",
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
)


def build_annotation(capture_root: Path | None = None) -> dict[str, Any]:
    capture_root = capture_root or _default_capture_root()
    replay, index = _load_replay_and_index()
    page_texts = _derive_pages(capture_root)
    replay_page_rows = _review_page_rows(replay, page_texts)

    locator_row = _locator()
    occurrence_rows, branch_rows, occurrence_ids, spec_text = (
        _build_occurrences_and_branches(page_texts, locator_row["locator_id"])
    )
    page_rows = _page_rows(
        replay_page_rows, occurrence_rows, locator_row["locator_id"]
    )
    anchor_rows, anchor_ids = _local_anchor_rows(occurrence_ids, spec_text)
    purpose_rows = _purpose_rows(occurrence_ids, anchor_ids, spec_text)
    repeat_rows = _repeat_rows(occurrence_ids, anchor_ids)

    candidate_artifact = _load_candidate(index)
    dispositions, notes, named_by = _candidate_dispositions(
        candidate_artifact,
        locator_row,
        page_rows,
        occurrence_rows,
        anchor_rows,
        branch_rows,
    )

    document_row = candidate_artifact["document_source_row"]
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "",
        "status": STATUS,
        "authority_disposition": {
            "authority_kind": "nonauthority_document_shard",
            "closes_class_a_residual": False,
            "closes_class_b_residual": False,
            "emits_era_seal": False,
            "emits_global_alias_catalog": False,
            "emits_global_node_ids": False,
            "emits_q5_artifact": False,
            "emits_r_q": False,
            "read_inventory_crosswalk_reader_or_legal_registry": False,
            "sealed_document_count": 1,
        },
        "source_replay_identity": {
            "content_sha256": REPLAY_CONTENT_SHA256,
            "path": "docs/analysis/rq_stage1_evidence/source_replay_v1.json",
            "raw_sha256": REPLAY_RAW_SHA256,
        },
        "candidate_index_identity": {
            "content_sha256": INDEX_CONTENT_SHA256,
            "path": "docs/analysis/rq_stage1_candidates/index_v1.json",
            "raw_sha256": INDEX_RAW_SHA256,
        },
        "candidate_artifact_identity": {
            "candidate_payload_sha256": CANDIDATE_PAYLOAD_SHA256,
            "content_sha256": CANDIDATE_CONTENT_SHA256,
            "path": str(CANDIDATE_PATH.relative_to(ROOT)),
            "raw_sha256": CANDIDATE_RAW_SHA256,
        },
        "document_source_position": DOCUMENT_POSITION,
        "document_source_row": document_row,
        "questionnaire_page_text_derivation": replay[
            "questionnaire_page_replay"
        ]["questionnaire_page_text_derivation"],
        "whole_document_locator_rows": [locator_row],
        "questionnaire_page_rows": page_rows,
        "questionnaire_occurrence_rows": occurrence_rows,
        "flow_branch_rows": branch_rows,
        "local_anchor_classification_rows": anchor_rows,
        "local_field_purpose_classification_rows": purpose_rows,
        "local_repeat_or_alias_evidence_rows": repeat_rows,
        "candidate_disposition_rows": dispositions,
        "output_adjudication_rows": [],
        "correction_note_rows": [],
        "seal": {},
        "integrity": {
            "canonicalization": (
                "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
            ),
            "content_sha256": "0" * 64,
        },
    }

    adjudications, manual_notes = _output_adjudications(value, named_by)
    value["output_adjudication_rows"] = adjudications
    all_notes = notes + manual_notes
    seen_notes: set[str] = set()
    deduped = []
    for note in all_notes:
        if note["correction_note_id"] in seen_notes:
            continue
        seen_notes.add(note["correction_note_id"])
        deduped.append(note)
    deduped.sort(key=lambda row: row["correction_note_id"])
    value["correction_note_rows"] = deduped

    value["artifact_id"] = "rq-stage2-document-annotation:" + _digest(
        [
            DOCUMENT_ID,
            DOCUMENT_POSITION,
            PDF_SHA256,
            len(page_rows),
            len(occurrence_rows),
        ]
    )
    value["seal"] = _seal(value)
    value["integrity"]["content_sha256"] = _content_digest(value)
    _expect_keys(value, OUTER_KEYS, "annotation artifact")
    return value


FORBIDDEN_GLOBAL_PREFIXES = (
    "psid-job-slot:",
    "psid-component-slot:",
    "psid-node-alias:",
    "psid-questionnaire-relationship:",
    "psid-role-node:",
)
ALIAS_RELATIONS = frozenset(
    {
        "explicit_repeat_instruction",
        "explicit_cross_reference",
        "same_printed_identifier_and_exact_label",
    }
)


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    capture_root = capture_root or _default_capture_root()
    _expect_keys(value, OUTER_KEYS, "annotation artifact")
    if value["schema_version"] != SCHEMA_VERSION or value["status"] != STATUS:
        raise ValueError("annotation schema or status drift")

    disposition = value["authority_disposition"]
    if disposition["sealed_document_count"] != 1 or any(
        disposition[flag]
        for flag in (
            "closes_class_a_residual",
            "closes_class_b_residual",
            "emits_era_seal",
            "emits_global_alias_catalog",
            "emits_global_node_ids",
            "emits_q5_artifact",
            "emits_r_q",
            "read_inventory_crosswalk_reader_or_legal_registry",
        )
    ):
        raise ValueError("shard claims authority it must not claim")

    replay, index = _load_replay_and_index()
    page_texts = _derive_pages(capture_root)
    replay_page_rows = _review_page_rows(replay, page_texts)
    candidate_artifact = _load_candidate(index)

    # -- whole-document locator -------------------------------------------
    locator_rows = value["whole_document_locator_rows"]
    if len(locator_rows) != 1:
        raise ValueError("shard must have exactly one whole-file locator")
    locator = locator_rows[0]
    _expect_keys(locator, LOCATOR_KEYS, "whole-document locator")
    if (
        locator["location_type"] != "whole_document_exact_file_range"
        or locator["byte_start"] != 0
        or locator["byte_end"] != locator["size_bytes"]
        or locator["range_sha256"] != locator["full_file_sha256"]
        or locator["pdf_page_domain"] != "all_pages_and_flow_branches"
        or locator["size_bytes"] != PDF_SIZE
        or locator["full_file_sha256"] != PDF_SHA256
        or locator["filename"] != FILENAME
        or locator["interview_wave"] != INTERVIEW_WAVE
        or locator["source_document_id"] != DOCUMENT_ID
    ):
        raise ValueError("whole-file locator equations fail")
    expected_locator_id = "psid-whole-document:" + _digest(
        [DOCUMENT_ID, INTERVIEW_WAVE, PDF_SHA256, PDF_SIZE]
    )
    if locator["locator_id"] != expected_locator_id:
        raise ValueError("locator ID preimage drift")
    locator_id = locator["locator_id"]

    # -- pages -------------------------------------------------------------
    page_rows = value["questionnaire_page_rows"]
    if len(page_rows) != PAGE_COUNT:
        raise ValueError("page cover count drift")
    occurrence_rows = value["questionnaire_occurrence_rows"]
    by_page: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in occurrence_rows:
        by_page[row["page_number"]].append(row)

    for expected_number, (row, replay_row) in enumerate(
        zip(page_rows, replay_page_rows, strict=True), start=1
    ):
        _expect_keys(row, PAGE_KEYS, "page")
        number = row["page_number"]
        if (
            isinstance(number, bool)
            or not isinstance(number, int)
            or number != expected_number
        ):
            raise ValueError("page rows are not in page-number order")
        if (
            row["source_document_id"] != DOCUMENT_ID
            or row["source_locator_id"] != locator_id
            or row["interview_wave"] != INTERVIEW_WAVE
            or row["annotation_status"] != "complete"
        ):
            raise ValueError(f"page {number} binding drift")
        page_bytes = page_texts[number - 1].encode("utf-8")
        if row["page_text_utf8_sha256"] != _sha256(page_bytes):
            raise ValueError(f"page {number} text digest drift")
        if row["questionnaire_page_id"] != replay_row[
            "questionnaire_page_id"
        ] or row["questionnaire_page_id"] != (
            "psid-questionnaire-page:"
            + _digest(
                [
                    DOCUMENT_ID,
                    INTERVIEW_WAVE,
                    number,
                    row["page_text_utf8_sha256"],
                ]
            )
        ):
            raise ValueError(f"page {number} ID preimage drift")
        expected_ids = [
            item["questionnaire_occurrence_id"]
            for item in sorted(
                by_page.get(number, ()),
                key=lambda item: item["occurrence_index_on_page"],
            )
        ]
        if row["questionnaire_occurrence_ids"] != expected_ids:
            raise ValueError(
                f"page {number} occurrence projection is not the complete "
                "same-page source-order projection"
            )
    if len({row["questionnaire_page_id"] for row in page_rows}) != PAGE_COUNT:
        raise ValueError("page IDs are not unique")

    # -- branches (needed to resolve occurrence paths) ---------------------
    branch_rows = value["flow_branch_rows"]
    branch_by_id: dict[str, Mapping[str, Any]] = {}
    for row in branch_rows:
        _expect_keys(row, BRANCH_KEYS, "flow branch")
        if row["flow_branch_id"] in branch_by_id:
            raise ValueError("duplicate flow branch ID")
        branch_by_id[row["flow_branch_id"]] = row
    resolvable_paths = {(FLOW_ROOT,)}
    for row in branch_rows:
        resolvable_paths.add(tuple(row["branch_path"]))

    # -- occurrences -------------------------------------------------------
    seen_occurrence_ids: set[str] = set()
    seen_coordinates: set[tuple[Any, ...]] = set()
    seen_locator_digests: set[str] = set()
    for page_number, rows in by_page.items():
        ordered = sorted(
            rows,
            key=lambda row: (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                KIND_ORDER[row["occurrence_kind"]],
                row["semantic_ordinal_at_span"],
            ),
        )
        if [row["occurrence_index_on_page"] for row in ordered] != list(
            range(len(ordered))
        ):
            raise ValueError(
                f"page {page_number} occurrence ordering or index drift"
            )
        atoms: set[tuple[int, int, str]] = set()
        for row in ordered:
            key = (
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["occurrence_kind"],
            )
            if row["occurrence_kind"] != "flow_branch_label":
                if key in atoms:
                    raise ValueError(
                        f"page {page_number} duplicate atomic span and kind"
                    )
                if row["semantic_ordinal_at_span"] != 0:
                    raise ValueError(
                        f"page {page_number} illegal semantic ordinal"
                    )
            atoms.add(key)

    if [
        (row["page_number"], row["occurrence_index_on_page"])
        for row in occurrence_rows
    ] != sorted(
        (row["page_number"], row["occurrence_index_on_page"])
        for row in occurrence_rows
    ):
        raise ValueError("occurrence rows do not follow page-row order")

    for row in occurrence_rows:
        _expect_keys(row, OCCURRENCE_KEYS, "occurrence")
        if row["occurrence_kind"] not in KIND_ORDER:
            raise ValueError("unknown occurrence kind")
        page_number = row["page_number"]
        page_row = page_rows[page_number - 1]
        if (
            row["source_document_id"] != page_row["source_document_id"]
            or row["source_locator_id"] != page_row["source_locator_id"]
            or row["interview_wave"] != page_row["interview_wave"]
            or row["page_number"] != page_row["page_number"]
        ):
            raise ValueError("occurrence does not deep-equal its page row")
        start = row["utf8_byte_start"]
        end = row["utf8_byte_end"]
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or start >= end
        ):
            raise ValueError("occurrence offsets are not a half-open span")
        text = _strict_slice(page_texts[page_number - 1], start, end)
        if text != row["matched_text"]:
            raise ValueError("matched text is not the strict source slice")
        if row["matched_utf8_sha256"] != _sha256(text.encode("utf-8")):
            raise ValueError("matched text digest drift")
        expected_digest = _locator_digest(
            page_number,
            start,
            end,
            row["occurrence_index_on_page"],
            row["semantic_ordinal_at_span"],
            row["occurrence_kind"],
        )
        if row["source_locator_sha256"] != expected_digest:
            raise ValueError("occurrence locator digest drift")
        paths = row["flow_branch_paths"]
        if not isinstance(paths, list) or not paths:
            raise ValueError("flow_branch_paths must be a nonempty array")
        for path in paths:
            if not isinstance(path, list) or not path:
                raise ValueError("branch path must be a nonempty array")
            if tuple(path) not in resolvable_paths:
                raise ValueError("occurrence path does not resolve")
        if len({tuple(path) for path in paths}) != len(paths):
            raise ValueError("duplicate branch path on one occurrence")
        if [_path_sort_key(path) for path in paths] != sorted(
            _path_sort_key(path) for path in paths
        ):
            raise ValueError("branch paths are not in exact path order")
        if row["occurrence_kind"] == "flow_branch_label":
            if len(paths) != 1:
                raise ValueError("branch label must carry one parent path")
        expected_id = "psid-questionnaire-occurrence:" + _digest(
            [row[key] for key in OCCURRENCE_KEYS[1:]]
        )
        if row["questionnaire_occurrence_id"] != expected_id:
            raise ValueError("occurrence ID preimage drift")
        if expected_id in seen_occurrence_ids:
            raise ValueError("duplicate occurrence ID")
        seen_occurrence_ids.add(expected_id)
        coordinate = (
            page_number,
            start,
            end,
            row["occurrence_kind"],
            row["semantic_ordinal_at_span"],
        )
        if coordinate in seen_coordinates:
            raise ValueError("duplicate occurrence coordinate")
        seen_coordinates.add(coordinate)
        if expected_digest in seen_locator_digests:
            raise ValueError("duplicate occurrence locator digest")
        seen_locator_digests.add(expected_digest)

    occurrence_by_id = {
        row["questionnaire_occurrence_id"]: row for row in occurrence_rows
    }
    projected = [
        occurrence_id
        for row in page_rows
        for occurrence_id in row["questionnaire_occurrence_ids"]
    ]
    if len(projected) != len(occurrence_rows) or set(projected) != set(
        occurrence_by_id
    ):
        raise ValueError("page projection does not exact-cover occurrences")

    # -- branch ancestry ---------------------------------------------------
    branch_order = [
        (row["page_number"], row["occurrence_index_on_page"])
        for row in branch_rows
    ]
    if branch_order != sorted(branch_order):
        raise ValueError("flow branch rows do not follow occurrence order")
    label_occurrences = {
        row["questionnaire_occurrence_id"]
        for row in occurrence_rows
        if row["occurrence_kind"] == "flow_branch_label"
    }
    if {row["source_occurrence_id"] for row in branch_rows} != (
        label_occurrences
    ):
        raise ValueError("branch rows are not one-to-one with labels")
    if len({row["source_occurrence_id"] for row in branch_rows}) != len(
        branch_rows
    ):
        raise ValueError("duplicate branch label row")
    resolved_so_far: set[str] = {FLOW_ROOT}
    for row in branch_rows:
        source = occurrence_by_id[row["source_occurrence_id"]]
        if (
            source["occurrence_kind"] != "flow_branch_label"
            or row["interview_wave"] != source["interview_wave"]
            or row["source_locator_id"] != source["source_locator_id"]
            or row["page_number"] != source["page_number"]
            or row["occurrence_index_on_page"]
            != source["occurrence_index_on_page"]
            or row["branch_label"] != source["matched_text"]
            or row["branch_label_sha256"] != source["matched_utf8_sha256"]
        ):
            raise ValueError("branch row does not deep-equal its occurrence")
        parent = row["parent_flow_branch_id"]
        if parent not in resolved_so_far:
            raise ValueError("branch parent is unresolved or later")
        if parent == row["flow_branch_id"]:
            raise ValueError("branch cycle")
        expected_branch_id = "questionnaire-flow:" + _digest(
            [parent, INTERVIEW_WAVE, row["source_occurrence_id"]]
        )
        if row["flow_branch_id"] != expected_branch_id:
            raise ValueError("branch ID preimage drift")
        parent_path = source["flow_branch_paths"][0]
        if parent_path[-1] != parent:
            raise ValueError("branch parent path mismatch")
        if row["branch_path"] != list(parent_path) + [row["flow_branch_id"]]:
            raise ValueError("branch path is not the parent path extension")
        if len(set(row["branch_path"])) != len(row["branch_path"]):
            raise ValueError("branch path contains a cycle")
        resolved_so_far.add(row["flow_branch_id"])
    if len({tuple(row["branch_path"]) for row in branch_rows}) != len(
        branch_rows
    ):
        raise ValueError("duplicate branch path")

    # -- local anchors, purposes, repeat evidence -------------------------
    anchor_rows = value["local_anchor_classification_rows"]
    anchor_ids = {row["local_anchor_classification_id"] for row in anchor_rows}
    if len(anchor_ids) != len(anchor_rows):
        raise ValueError("duplicate local anchor ID")
    for row in anchor_rows:
        _expect_keys(row, ANCHOR_KEYS, "local anchor")
        source = occurrence_by_id.get(row["source_occurrence_id"])
        if source is None:
            raise ValueError("local anchor cites an unknown occurrence")
        if row["exact_label"] != source["matched_text"]:
            raise ValueError("local anchor label is not the exact source text")
        if row["exact_label_sha256"] != _sha256(
            row["exact_label"].encode("utf-8")
        ):
            raise ValueError("local anchor label digest drift")
        if row["classification_status"] != (
            "complete_document_local_provisional"
        ):
            raise ValueError("local anchor is not fully classified")
        for parent in row["parent_local_anchor_ids"]:
            if parent not in anchor_ids:
                raise ValueError("local anchor parent does not resolve")
        for field in ("exact_label", "local_classification", "node_domain"):
            if any(
                str(row[field]).startswith(prefix)
                for prefix in FORBIDDEN_GLOBAL_PREFIXES
            ):
                raise ValueError("local anchor assigns a global node ID")

    purpose_rows = value["local_field_purpose_classification_rows"]
    if len(
        {row["local_field_purpose_classification_id"] for row in purpose_rows}
    ) != len(purpose_rows):
        raise ValueError("duplicate field-purpose ID")
    for row in purpose_rows:
        _expect_keys(row, PURPOSE_KEYS, "field purpose")
        source = occurrence_by_id.get(row["source_occurrence_id"])
        if source is None or source["occurrence_kind"] != (
            "field_purpose_prompt"
        ):
            raise ValueError("field purpose does not cite a printed prompt")
        if row["field_purpose"] not in PURPOSE_ORDER:
            raise ValueError("unknown field purpose")
        if row["exact_prompt"] != source["matched_text"] or row[
            "exact_prompt_sha256"
        ] != _sha256(row["exact_prompt"].encode("utf-8")):
            raise ValueError("field purpose prompt drift")
        for anchor_id in row["supported_local_anchor_ids"]:
            if anchor_id not in anchor_ids:
                raise ValueError("field purpose cites an unknown anchor")
    if {row["source_occurrence_id"] for row in purpose_rows} != {
        row["questionnaire_occurrence_id"]
        for row in occurrence_rows
        if row["occurrence_kind"] == "field_purpose_prompt"
    }:
        raise ValueError("field purposes do not cover every printed prompt")

    repeat_rows = value["local_repeat_or_alias_evidence_rows"]
    for row in repeat_rows:
        _expect_keys(row, REPEAT_KEYS, "repeat or alias")
        source = occurrence_by_id.get(row["source_occurrence_id"])
        if source is None or source["occurrence_kind"] != (
            "repeat_or_alias_instruction"
        ):
            raise ValueError("alias evidence does not cite an instruction")
        if row["alias_relation"] not in ALIAS_RELATIONS:
            raise ValueError("unknown alias relation")
        if not row["evidence_occurrence_ids"]:
            raise ValueError("alias evidence is empty")
        for occurrence_id in row["evidence_occurrence_ids"]:
            if occurrence_id not in occurrence_by_id:
                raise ValueError("alias evidence cites unknown occurrence")
        if row["source_occurrence_id"] not in row["evidence_occurrence_ids"]:
            raise ValueError("alias evidence omits its own instruction")
        for field in ("alias_local_anchor_id", "canonical_local_anchor_id"):
            if row[field] is not None and row[field] not in anchor_ids:
                raise ValueError(f"{field} does not resolve")
        if row["resolution_status"] not in {
            "locally_resolved_document_evidence",
            "unresolved_printed_target_for_global_assembly",
        }:
            raise ValueError("unknown alias resolution status")
    if {row["source_occurrence_id"] for row in repeat_rows} != {
        row["questionnaire_occurrence_id"]
        for row in occurrence_rows
        if row["occurrence_kind"] == "repeat_or_alias_instruction"
    }:
        raise ValueError(
            "every repeat or alias instruction must be dispositioned"
        )

    # -- candidate disposition exact cover --------------------------------
    candidate_domains = {
        "whole_document_locator": {
            candidate_artifact["whole_document_locator_candidate"][
                "candidate_locator_id"
            ]
        },
        "page": {
            row["candidate_page_id"]
            for row in candidate_artifact["candidate_page_rows"]
        },
        "occurrence": {
            row["candidate_occurrence_id"]
            for row in candidate_artifact["candidate_occurrence_rows"]
        },
        "flow_path": {
            row["candidate_flow_path_id"]
            for row in candidate_artifact["candidate_flow_path_rows"]
        },
        "anchor_classification": {
            row["candidate_anchor_classification_id"]
            for row in candidate_artifact[
                "candidate_anchor_classification_rows"
            ]
        },
    }
    emitted_ids = {
        row_id
        for _, domain, id_field in OUTPUT_ROW_DOMAINS
        for row_id in (item[id_field] for item in value[domain])
    }
    observed: dict[str, set[str]] = defaultdict(set)
    forward: dict[str, list[str]] = {}
    for row in value["candidate_disposition_rows"]:
        _expect_keys(row, DISPOSITION_KEYS, "candidate disposition")
        kind = row["candidate_row_kind"]
        if kind not in candidate_domains:
            raise ValueError("unknown candidate row kind")
        if row["candidate_id"] in observed[kind]:
            raise ValueError("candidate dispositioned more than once")
        observed[kind].add(row["candidate_id"])
        if row["adjudication_status"] != "complete":
            raise ValueError("incomplete candidate adjudication")
        names = row["stage2_row_ids"]
        state = row["disposition"]
        if state in {"accepted", "modified"}:
            if len(names) != 1:
                raise ValueError(f"{state} candidate must name one row")
        elif state == "split":
            if len(names) < 2:
                raise ValueError("split candidate must name at least two rows")
        elif state == "rejected":
            if names:
                raise ValueError("rejected candidate must name no row")
        else:
            raise ValueError("unknown disposition")
        for row_id in names:
            if row_id not in emitted_ids:
                raise ValueError("disposition names an unemitted row")
        forward[row["candidate_id"]] = names
    for kind, domain in candidate_domains.items():
        if observed[kind] != domain:
            raise ValueError(
                f"candidate disposition does not exact-cover {kind}"
            )

    # -- output adjudication exact cover ----------------------------------
    adjudicated: set[tuple[str, str]] = set()
    backward: dict[str, list[str]] = {}
    for row in value["output_adjudication_rows"]:
        _expect_keys(row, ADJUDICATION_KEYS, "output adjudication")
        key = (row["stage2_row_kind"], row["stage2_row_id"])
        if key in adjudicated:
            raise ValueError("output row adjudicated more than once")
        adjudicated.add(key)
        if row["adjudication_status"] != "complete":
            raise ValueError("incomplete output adjudication")
        if (
            not row["whole_page_review_complete"]
            or not row["source_span_verified"]
        ):
            raise ValueError("output row lacks a completed review")
        action = row["adjudication_action"]
        if action not in set(ACTION_NAMES.values()) | {"manual_add"}:
            raise ValueError("unknown adjudication action")
        if action == "manual_add":
            if row["source_candidate_ids"]:
                raise ValueError("manual add carries a candidate projection")
        elif not row["source_candidate_ids"]:
            raise ValueError("candidate-backed row has no candidate")
        backward[row["stage2_row_id"]] = row["source_candidate_ids"]
    expected_keys = {
        (kind, item[id_field])
        for kind, domain, id_field in OUTPUT_ROW_DOMAINS
        for item in value[domain]
    }
    if adjudicated != expected_keys:
        raise ValueError("output adjudication does not exact-cover the rows")

    # -- the two relations must agree in both directions -------------------
    forward_pairs = {
        (candidate_id, row_id)
        for candidate_id, names in forward.items()
        for row_id in names
    }
    backward_pairs = {
        (candidate_id, row_id)
        for row_id, candidate_ids in backward.items()
        for candidate_id in candidate_ids
    }
    if forward_pairs != backward_pairs:
        raise ValueError(
            "candidate disposition and output adjudication disagree"
        )

    # -- correction notes --------------------------------------------------
    note_subjects = {
        (row["subject_kind"], row["subject_id"])
        for row in value["correction_note_rows"]
    }
    for row in value["correction_note_rows"]:
        _expect_keys(row, NOTE_KEYS, "correction note")
        if row["correction_note_id"] != "rq-correction-note:" + _digest(
            [
                row["subject_kind"],
                row["subject_id"],
                row["note_kind"],
                row["note"],
            ]
        ):
            raise ValueError("correction note ID preimage drift")
    for row in value["candidate_disposition_rows"]:
        if row["disposition"] == "accepted":
            continue
        subject_kind = "candidate_" + row["candidate_row_kind"]
        if (subject_kind, row["candidate_id"]) not in note_subjects:
            raise ValueError("non-accepted candidate lacks a correction note")
    for row in value["output_adjudication_rows"]:
        if row["adjudication_action"] != "manual_add":
            continue
        if (row["stage2_row_kind"], row["stage2_row_id"]) not in note_subjects:
            raise ValueError("manual add lacks a correction note")

    # -- seal and integrity ------------------------------------------------
    if value["seal"] != _seal(value):
        raise ValueError("row-domain seal drift")
    if value["integrity"]["content_sha256"] != _content_digest(value):
        raise ValueError("content digest drift")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    capture_root = args.capture_root or _default_capture_root()
    value = build_annotation(capture_root)
    validate_annotation(value, capture_root)
    raw = _canonical_bytes(value)
    if args.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != raw:
            print(
                "document-36 annotation is not reproducible", file=sys.stderr
            )
            return 1
        print("document-36 annotation reproduces its sealed bytes")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(raw)
    print(
        f"wrote {OUTPUT_PATH.relative_to(ROOT)} "
        f"({len(raw)} bytes, sha256 {_sha256(raw)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
