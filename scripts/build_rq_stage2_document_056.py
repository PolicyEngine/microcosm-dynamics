#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for fam1996_QxQs.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 54-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

fam1996_QxQs.pdf is the 1996 question-by-question objectives manual: printed
interviewer instructions keyed to questionnaire item identifiers rather than a
printed questionnaire.  The retention test applied throughout is therefore
whether the printed text *establishes* a document-local R_Q fact for a named
item or item series -- a role attachment, a job slot, a remuneration
component, an aggregate, a retained contextual field, a field purpose, a
controlling condition, or an explicit repeat/cross-reference.  Narrative
procedure, probing examples, data-entry validation instructions, and
non-employment subject matter (marital status and housing, housework, child
care and food expenditure, transfer and asset income, pensions, health,
marriage and children, money management and bankruptcy, background education,
and risk aversion) are rejected even where they carry work-like lexemes.
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
DOCUMENT_POSITION = 56
DOCUMENT_ID = (
    "psid-source-document:"
    "1578032027e690b16afc920807dec8a5c2228aaf5440ec1594cd1e2a8dfb9c48"
)
INTERVIEW_WAVE = 1996
CANONICAL_SOURCE_PATH = "documentation/capture1/fam1996_QxQs.pdf"
PDF_FILENAME = "fam1996_QxQs.pdf"
PDF_SIZE = 26_967_987
PDF_SHA256 = "b0781bd03d8fbabcf3bc71d5742e42da51cc321007068eca3769b3aebd85c63e"
PAGE_COUNT = 54
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_06_documents_051_060"
    / "document_056_fam1996_QxQs_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_056_fam1996_QxQs_annotation_v1.json"
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
    "67088f4b9d6c252286640c21985e427385c9f73843cc382530f44c10100d7d43"
)
CANDIDATE_CONTENT_SHA256 = (
    "095866b13c4b81e373cbd83624d6c8970397946495683b286993b779f8419e46"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "97336ea573e034ec803aaf876bb02f3e246602d68b8937f3dfcc703f6e668237"
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
        raise ValueError("document-56 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-56 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-56 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-56 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / PDF_FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1996_QxQs.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("fam1996_QxQs.pdf page-count drift")
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
        raise ValueError("document-56 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-56 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-56 empty-text page domain drift")
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
# read during the complete 54-page review pass and is re-resolved against the
# authenticated fam1996_QxQs.pdf bytes.
# ---------------------------------------------------------------------------

# Controlling flow.  A branch is retained only where printed text states a
# condition or scope restriction that determines whether a retained R_Q item
# series is asked.  Advisory conditionals inside an objective paragraph ("if R
# gives an amount and frequency, probe for a total") are rejected as
# noncontrolling flow text, as is every routing statement whose whole target
# series is outside the retained R_Q domain (housing, food, transfers, assets,
# health, marriage and children, money management, risk aversion).
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _block(
        "f_bc_head",
        10,
        "SECTIONS B AND C APPLY TO THE CURRENT HEAD OF THE FU EVEN IF",
        "YOUR RESPONDENT IS NOT THE HEAD.",
    ),
    _block(
        "f_b_route",
        10,
        "WORKING NOW or 2. TEMPORARILY OFF from work, ask B4 and continue",
        "continue with Section B; if B3 is NO , GO TO Section C .",
        parent="f_bc_head",
    ),
    _line(
        "f_c_route",
        25,
        'Section C--Head Is Not Working Now at Bl ("No" to B3)',
        parent="f_bc_head",
    ),
    _inline(
        "f_de_wife",
        26,
        'Sections D and E apply to current Wife or "Wife" only.',
        'Sections D and E apply to current Wife or "Wife" only.',
    ),
    _block(
        "f_f2_route",
        27,
        "F2-3.     If roomers or boarders are living in the HU",
        "these rented rooms should not be counted here.",
    ),
    _line("f_g_workincome", 29, "reports work income in Section G"),
    _block(
        "f_g_workhours",
        29,
        "reports working during 1995 in the employment sections",
        "from those hours must be reported in Section G.",
    ),
    _block(
        "f_gj_supplement",
        37,
        "The yellow JOB SUPPLEMENT is for those rare occasions when R informs",
        "job that she/he did not report in the employment sections.",
    ),
    _block(
        "f_ofum_booklet",
        39,
        "If there is an eligible OFUM listed in G71 turn to the BLUE 1995",
        "Work Booklet. Use one booklet for each additional OFUM.",
    ),
    _block(
        "f_k_new_wife",
        51,
        "whether the FU has a new Wife/",
        "considered a new Wife/",
    ),
    _block(
        "f_l_new_head",
        53,
        "This section applies to anyone who is Head this year but is not",
        "asked this section, even if the (Splitoff) Head was Head of another",
    ),
)


ROOT_PATH = ("root",)

P_ROOT = (("root",),)
P_BC = (("root", "f_bc_head"),)
P_C = (("root", "f_bc_head", "f_c_route"),)
P_DE = (("root", "f_de_wife"),)
P_GJ = (("root", "f_gj_supplement"),)
P_OFUM = (("root", "f_ofum_booklet"),)
P_K = (("root", "f_k_new_wife"),)
P_L = (("root", "f_l_new_head"),)
P_F2 = (("root", "f_f2_route"),)


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
# that names the node.
STANDALONE_ANCHORS: tuple[dict[str, Any], ...] = (
    _anchor(
        "r_b_head",
        10,
        "role_anchor",
        _in("Section B--Employment of Head", "Head"),
        classification=HEAD,
    ),
    _anchor(
        "r_c_head",
        25,
        "role_anchor",
        _in('Section C--Head Is Not Working Now at Bl ("No" to B3)', "Head"),
        classification=HEAD,
        paths=P_C,
    ),
    _anchor(
        "r_de_spouse",
        26,
        "role_anchor",
        _in('Sections D and E--Employment of Wife/"Wife"', 'Wife/"Wife"'),
        classification=SPOUSE,
    ),
    _anchor(
        "r_whs_head",
        18,
        "role_anchor",
        _in("have allowed for up to four main jobs", "Head"),
        classification=HEAD,
        paths=P_BC,
    ),
    _anchor(
        "r_whs_spouse",
        18,
        "role_anchor",
        _in("have allowed for up to four main jobs", 'Wife/ "Wife ."'),
        classification=SPOUSE,
        paths=P_BC,
    ),
    _anchor(
        "r_g13_head",
        31,
        "role_anchor",
        _in("This question applies only to current Head.", "Head"),
        classification=HEAD,
        identifier="G 13.",
    ),
    _anchor(
        "r_g50_spouse",
        37,
        "role_anchor",
        _in("income from all work sources is recorded", "Wife's/\"Wife's\""),
        classification=SPOUSE,
        identifier="GS0-52.",
    ),
    _anchor(
        "r_gj4_head",
        38,
        "role_anchor",
        _in(
            "This is the number of calendar weeks in 1995 during which", "Head"
        ),
        classification=HEAD,
        identifier="GJ4.",
        paths=P_GJ,
    ),
    _anchor(
        "r_gj4_spouse",
        38,
        "role_anchor",
        _in(
            "This is the number of calendar weeks in 1995 during which",
            'Wife/ "WIFE"',
        ),
        classification=SPOUSE,
        identifier="GJ4.",
        paths=P_GJ,
    ),
    _anchor(
        "r_k_spouse",
        51,
        "role_anchor",
        _in(
            'Section K--Background and Education of New Wife/"Wife"',
            'Wife/"Wife"',
        ),
        classification=SPOUSE,
    ),
    _anchor(
        "r_l_head",
        53,
        "role_anchor",
        _in("Section L--Background and Education of New Head", "Head"),
        classification=HEAD,
    ),
    _anchor(
        "j_b_main_job",
        11,
        "job_anchor",
        _in("Note: B4-B59 refer to Head's main job", "main job"),
        identifier="B4-B59",
        paths=P_BC,
    ),
    _anchor(
        "j_b15_recent_main_job",
        15,
        "job_anchor",
        _in(
            "(Section B) or Most Recent Main Job (Section C), then other "
            "main jobs held in 1995, in",
            "Most Recent Main Job",
        ),
        paths=P_BC,
    ),
    _anchor(
        "j_b15_other_main_jobs",
        15,
        "job_anchor",
        _in(
            "(Section B) or Most Recent Main Job (Section C), then other "
            "main jobs held in 1995, in",
            "other main jobs held in 1995",
        ),
        paths=P_BC,
    ),
    _anchor(
        "j_b20_another_job",
        15,
        "job_anchor",
        _in(
            'B20.    "Another job" can mean a different position',
            "Another job",
        ),
        identifier="B20.",
        paths=P_BC,
    ),
    _anchor(
        "j_b40_other_employer",
        17,
        "job_anchor",
        _in(
            'B40.       If B40 is "NO", Head had no (other) main job employer',
            "main job employer",
        ),
        identifier="B40.",
        paths=P_BC,
    ),
    _anchor(
        "j_whs_additional",
        18,
        "job_anchor",
        _in(
            "If the person worked for more than two main job employers",
            "main job employers",
        ),
        paths=P_BC,
    ),
    _anchor(
        "j_b82_extra_job",
        23,
        "job_anchor",
        _in("B82.     Main vs. Extra Job distinctions", "Extra Job"),
        identifier="B82.",
        paths=P_BC,
    ),
    _anchor(
        "j_c_last_job",
        25,
        "job_anchor",
        _in("employment history for the last job held", "last job held"),
        identifier="C16-51.",
        paths=P_C,
    ),
    _anchor(
        "j_g22_extra",
        33,
        "job_anchor",
        _in("extra jobs, we get the income from them.", "extra jobs"),
        identifier="G22-24.",
    ),
    _anchor(
        "j_gj_unreported",
        37,
        "job_anchor",
        _in(
            "job that she/he did not report in the employment sections",
            "job that she/he did not report in the employment sections",
        ),
        paths=P_GJ,
    ),
    _anchor(
        "j_g76_each_job",
        40,
        "job_anchor",
        _in("about each job in 1995", "each job"),
        identifier="G76-82.",
        paths=P_OFUM,
    ),
    _anchor(
        "j_g92_child_jobs",
        41,
        "job_anchor",
        _in("Sometimes children make money from odd jobs", "odd jobs"),
        identifier="G92-98 .",
        paths=P_OFUM,
    ),
    _anchor(
        "a_b5_business",
        11,
        "business_aggregate_anchor",
        _in(
            "Many self-employed people and professionals do not consider",
            "business",
        ),
        identifier="BS.",
        paths=P_BC,
    ),
    _anchor(
        "a_b87_business",
        23,
        "business_aggregate_anchor",
        _in("For small business: if R asks", "small business"),
        identifier="B87 .",
        paths=P_BC,
    ),
    _anchor(
        "a_g2_farm",
        29,
        "farm_aggregate_anchor",
        _in("G2.       Receipts from normal farm operations include:", "farm"),
        identifier="G2.",
    ),
    _anchor(
        "a_g3_farm",
        29,
        "farm_aggregate_anchor",
        _in("G3 .      Farm operating expenses can include :", "Farm"),
        identifier="G3 .",
    ),
    _anchor(
        "a_g4_farm",
        30,
        "farm_aggregate_anchor",
        _in("G4.        Farm income equals total receipts", "Farm"),
        identifier="G4.",
    ),
    _anchor(
        "a_g5_business",
        30,
        "business_aggregate_anchor",
        _in("These questions refer to any business or financial", "business"),
        identifier="GS- 7a.",
    ),
    _anchor(
        "a_g10_business",
        30,
        "business_aggregate_anchor",
        _in("whether the business was incorporated or not", "business"),
        identifier="GlO .",
    ),
    _anchor(
        "a_g11c_business",
        30,
        "business_aggregate_anchor",
        _in(
            "record information for each additional business",
            "additional business",
        ),
        identifier="Gllc.",
    ),
    _anchor(
        "a_g18_practice",
        32,
        "business_aggregate_anchor",
        _in(
            "PROFESSIONAL PRACTICE: Includes self-employed doctors",
            "PROFESSIONAL PRACTICE",
        ),
        identifier="Gl8 .",
    ),
    _anchor(
        "a_g18_trade",
        32,
        "business_aggregate_anchor",
        _in("TRADE: Includes self-employed tradesmen", "TRADE"),
    ),
    _anchor(
        "a_g18b_farming",
        32,
        "farm_aggregate_anchor",
        _in(
            "G18b.     FARMING or MARKET GARDENING",
            "FARMING or MARKET GARDENING",
        ),
        identifier="G18b.",
    ),
    _anchor(
        "a_g18c_boarders",
        32,
        "business_aggregate_anchor",
        _in("G18c .    ROOMERS OR BOARDERS", "ROOMERS OR BOARDERS"),
        identifier="G18c .",
    ),
    _anchor(
        "t_g13_total_wages",
        31,
        "role_total_anchor",
        _at("total 1995\n               wages/salary"),
        identifier="G 13.",
    ),
    _anchor(
        "t_g13_total_income",
        31,
        "role_total_anchor",
        _in(
            "get total income from all 1995 wages",
            "total income from all 1995 wages",
        ),
        identifier="G 13.",
    ),
    _anchor(
        "t_g50_wife_total",
        37,
        "role_total_anchor",
        _in(
            "income from all work sources is recorded",
            "income from all work sources",
        ),
        identifier="GS0-52.",
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
#   1. A printed "See <item>" line is retained only where it names a retained
#      R_Q field; the same line carries both the field's anchor and the
#      cross-reference instruction.
#   2. Transfer, asset, pension, health, housing, food, philanthropy,
#      family-composition, and money-management items carry no R_Q
#      remuneration component or coverage context and are rejected in full,
#      including their work-like lexemes.
#   3. An exclusion cross-reference ("should not be repeated here", "do not
#      double-count", "not here") states no alias between retained anchors and
#      is rejected; only positive repeat and cross-reference instructions are
#      retained.
ITEM_SPECS: tuple[dict[str, Any], ...] = (
    _item(
        "b1_3",
        10,
        _mark("Bl-3   It is crucial that you get an accurate"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="Bl-3",
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b_code1",
        10,
        _mark("CODE l.       WORKING NOW: Head has an employer"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="CODE l.",
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b_code2",
        10,
        _mark("CODE 2 .      ONLY TEMPORARILY LAID OFF"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="CODE 2 .",
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b_code3",
        10,
        _mark("CODE 3.       LOOKING FOR WORK, UNEMPLOYED"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="CODE 3.",
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b_code4_8",
        10,
        _mark("CODES4-8 .    NOT WORKING/NOT LOOKING"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="CODES4-8 .",
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b4",
        11,
        _mark("B4.      Be careful with the following situations"),
        CTX,
        ("employee_self_or_mixed",),
        identifier="B4.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b5",
        11,
        _mark("BS.      Many self-employed people and professionals"),
        CTX,
        ("incorporation",),
        identifier="BS.",
        parents=("a_b5_business",),
        paths=P_BC,
    ),
    _item(
        "b9_9a",
        11,
        _mark("B9-9a.   Follow the guidelines below"),
        CTX,
        ("occupation",),
        identifier="B9-9a.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b10",
        12,
        _mark("B10.   The type of business or industry is fit"),
        CTX,
        ("industry",),
        identifier="B10.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b10_govt",
        13,
        _span(
            "3.         If Head is employed by the government",
            "etc., and the level: federal, state or local.",
        ),
        CTX,
        ("government_level", "industry"),
        identifier=None,
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b11",
        14,
        _mark("Bll.     You will be asking employer's name"),
        CTX,
        ("job_identifier",),
        identifier="Bll.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b12_19",
        14,
        _mark("Bl2-19. Questions B12, B13, B16 , and B18"),
        REM,
        ("amount", "reporting_unit"),
        identifier="Bl2-19.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b12",
        14,
        _mark("B12.     The OTHER category is for everything"),
        REM,
        ("amount", "reporting_unit"),
        identifier="B12.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b14",
        14,
        _mark("B14.     This should be NO if Head's income"),
        CTX,
        ("amount",),
        identifier="B14.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b15",
        14,
        _mark("B15.     Select all that R mentions . Use 5. EXACT AMOUNT"),
        REM,
        ("amount",),
        identifier="B15.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b18",
        15,
        _mark("B18     OTHER ways Head is paid for regular"),
        REM,
        ("amount",),
        identifier="B18",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b19",
        15,
        _mark("Bl9.    We know that B19 may be difficult"),
        REM,
        ("amount",),
        identifier="Bl9.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b17",
        15,
        _mark("B17.    Select all that R mentions. Use 5. EXACT AMOUNT"),
        REM,
        ("amount",),
        identifier="B17.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b23",
        15,
        _mark("B23.    By employer, we mean company, firm"),
        CTX,
        ("job_identifier",),
        identifier="B23.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_work_history",
        15,
        _mark("With questions B24-B59 and pink Work History Supplements"),
        CTX,
        ("month_or_exposure",),
        identifier="B24-B59",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_main_extra",
        16,
        _mark("A quick definition of main vs. extra jobs"),
        CTX,
        ("job_identifier",),
        identifier=None,
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b24",
        16,
        _mark("B24 .    Both B23 and B24 refer to the present"),
        CTX,
        ("month_or_exposure",),
        identifier="B24 .",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b25_29",
        16,
        _mark("B25-29. For Heads who began their present employment in 1995"),
        CTX,
        ("month_or_exposure",),
        identifier="B25-29.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b30",
        16,
        _mark("B30.     For Heads who began their present employment in 1996"),
        CTX,
        ("month_or_exposure",),
        identifier="B30.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b31_34",
        16,
        _mark("B31-34. For Heads who began their present employment prior"),
        CTX,
        ("month_or_exposure",),
        identifier="B31-34.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b38",
        16,
        _mark("B38 .    The amount at B38 should be an average"),
        REM,
        ("amount",),
        identifier="B38 .",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b39",
        16,
        _mark("B39.     Mark the months of 1995 that Head worked"),
        CTX,
        ("month_or_exposure",),
        identifier="B39.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b40",
        17,
        _mark('B40.       If B40 is "NO", Head had no (other)'),
        CTX,
        ("job_identifier",),
        identifier="B40.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b42a_42d",
        17,
        _mark("B42a-42d              There should be no overlap"),
        CTX,
        ("month_or_exposure",),
        identifier="B42a-42d",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b45a",
        17,
        _mark("B45a.                 Enter dollar amount and time period"),
        REM,
        ("amount", "reporting_unit"),
        identifier="B45a.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b46_47",
        17,
        _mark("B46-B47.              Again we' re looking for the most"),
        CTX,
        ("month_or_exposure",),
        identifier="B46-B47.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b53_55",
        18,
        _mark("B53-55.              Since Head is currently employed"),
        CTX,
        ("month_or_exposure",),
        identifier="B53-55.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b59",
        18,
        _mark("B59 .                If Head had any other main-job employers"),
        CTX,
        ("job_identifier",),
        identifier="B59 .",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "b_whs",
        18,
        _mark("The questionnaire employment sections are designed to cover"),
        CTX,
        ("job_identifier",),
        identifier=None,
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "b60_78",
        20,
        _mark("NOTE: ASK B60-78 FOR ALL HEADS!"),
        CTX,
        ("month_or_exposure",),
        identifier="B60-78",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_obj1",
        20,
        _mark("1. Separation of weeks into periods of work and non-work"),
        CTX,
        ("month_or_exposure",),
        identifier="1.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_obj2",
        20,
        _mark("2 . Average work hours per week for weeks worked"),
        CTX,
        ("month_or_exposure",),
        identifier="2 .",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_obj3",
        20,
        _mark("3. Annual overtime hours"),
        CTX,
        ("month_or_exposure",),
        identifier="3.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_work_def",
        20,
        _mark("Work in these questions means simply and only main job"),
        CTX,
        ("month_or_exposure",),
        identifier=None,
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b_unemployed_def",
        21,
        _mark("Weeks spent as unemployed weeks require two conditions."),
        CTX,
        ("month_or_exposure",),
        identifier=None,
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b_notlooking_def",
        21,
        _mark("Not Working and Not Looking is often confused"),
        CTX,
        ("month_or_exposure",),
        identifier=None,
        parents=(),
        paths=P_BC,
    ),
    _item(
        "b60_62",
        21,
        _mark('B60-62.   "Someone else" means anyone'),
        CTX,
        ("month_or_exposure",),
        identifier="B60-62.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b63_65",
        21,
        _mark("B63-65. Again, we don't need dates"),
        CTX,
        ("month_or_exposure",),
        identifier="B63-65.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b66_68",
        21,
        _mark("B66-68. Include paid and unpaid holidays"),
        CTX,
        ("month_or_exposure",),
        identifier="B66-68.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b69_71",
        21,
        _mark("B69-71. Beware of overlaps with unemployment"),
        CTX,
        ("month_or_exposure",),
        identifier="B69-71.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b72_74",
        22,
        _mark("B72-74. Check dates at B74 against work history"),
        CTX,
        ("month_or_exposure",),
        identifier="B72-74.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b75_77",
        22,
        _mark("B75-77. Again, check these dates against"),
        CTX,
        ("month_or_exposure",),
        identifier="B75-77.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b78",
        22,
        _mark("B78.     We want the total number of weeks"),
        CTX,
        ("month_or_exposure",),
        identifier="B78.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b79",
        23,
        _mark("B79.     This is the average hours per week"),
        CTX,
        ("month_or_exposure",),
        identifier="B79.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b80_81",
        23,
        _mark("B80-81. Be careful not to double count"),
        CTX,
        ("month_or_exposure",),
        identifier="B80-81.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b81a_d",
        23,
        _mark("B81a-d. If Head worked more than one main job"),
        CTX,
        ("month_or_exposure",),
        identifier="B81a-d.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b82",
        23,
        _mark("B82.     Main vs. Extra Job distinctions"),
        CTX,
        ("job_identifier",),
        identifier="B82.",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "b87",
        23,
        _mark("B87 .    Be sure to record the unit of time"),
        REM,
        ("amount", "reporting_unit"),
        identifier="B87 .",
        parents=("j_b82_extra_job", "a_b87_business"),
        paths=P_BC,
    ),
    _item(
        "b88",
        23,
        _mark("B88.     This is the number of calendar weeks in 1995"),
        CTX,
        ("month_or_exposure",),
        identifier="B88.",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "b89",
        24,
        _mark("B89.     This is average hours per week for the"),
        CTX,
        ("month_or_exposure",),
        identifier="B89.",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "b90_93",
        24,
        _mark("B90-93 . These dates will help us to check"),
        CTX,
        ("month_or_exposure",),
        identifier="B90-93 .",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "c4_8",
        25,
        _mark("C4-8 .   This sequence provides a short version"),
        CTX,
        ("month_or_exposure",),
        identifier="C4-8 .",
        parents=(),
        paths=P_C,
    ),
    _item(
        "c16_51",
        25,
        _mark("C16-51. This sequence, with WORK HISTORY"),
        CTX,
        ("job_identifier", "month_or_exposure"),
        identifier="C16-51.",
        parents=("j_c_last_job",),
        paths=P_C,
    ),
    _item(
        "de_definitions",
        26,
        _mark("Review the definitions of Head, Wife, and"),
        CTX,
        ("interview_and_role_attachment",),
        identifier=None,
        parents=(),
    ),
    _item(
        "d1_1a",
        26,
        _mark("Dl-la .   The Dl checkpoint routes all Female"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="Dl-la .",
        parents=(),
        paths=P_DE,
    ),
    _item(
        "g_intro_wages",
        29,
        _mark("All wages and salaries listed in Section G should be before"),
        REM,
        ("amount",),
        identifier=None,
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g_intro_profit",
        29,
        _mark("All profit or loss amounts should be net"),
        REM,
        ("amount",),
        identifier=None,
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g2",
        29,
        _mark("G2.       Receipts from normal farm operations"),
        REM,
        ("amount",),
        identifier="G2.",
        parents=("a_g2_farm",),
        paths=P_ROOT,
    ),
    _item(
        "g3",
        29,
        _mark("G3 .      Farm operating expenses can include"),
        CTX,
        ("amount",),
        identifier="G3 .",
        parents=("a_g3_farm",),
        paths=P_ROOT,
    ),
    _item(
        "g4",
        30,
        _mark("G4.        Farm income equals total receipts"),
        REM,
        ("amount",),
        identifier="G4.",
        parents=("a_g4_farm",),
        paths=P_ROOT,
    ),
    _item(
        "g5_7a",
        30,
        _mark("GS- 7a.    Do not include stock ownership"),
        CTX,
        ("assignment",),
        identifier="GS- 7a.",
        parents=("a_g5_business",),
        paths=P_ROOT,
    ),
    _item(
        "g8",
        30,
        _mark('G8.        Remember that "family" refers to members'),
        CTX,
        ("assignment",),
        identifier="G8.",
        parents=("a_g5_business",),
        paths=P_ROOT,
    ),
    _item(
        "g10",
        30,
        _mark("GlO .      If R doesn't understand the question"),
        CTX,
        ("incorporation",),
        identifier="GlO .",
        parents=("a_g10_business",),
        paths=P_ROOT,
    ),
    _item(
        "g11a",
        30,
        _mark("G 1 la.    The amount given here is net profit"),
        REM,
        ("amount",),
        identifier="G 1 la.",
        parents=("a_g5_business",),
        paths=P_ROOT,
    ),
    _item(
        "g12",
        31,
        _mark("Gl2.         If Head was working in 1995"),
        CTX,
        ("amount",),
        identifier="Gl2.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g13",
        31,
        _mark("G 13.        This question applies only to current"),
        REM,
        ("amount",),
        identifier="G 13.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g14",
        31,
        _mark('G 14 .       Note the phrase "in addition to this."'),
        REM,
        ("amount",),
        identifier="G 14 .",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g16",
        31,
        _mark("G16.         If earnings are solely from bonuses"),
        REM,
        ("amount",),
        identifier="G16.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g18",
        32,
        _mark("Gl8 .     PROFESSIONAL PRACTICE: Includes"),
        REM,
        ("amount",),
        identifier="Gl8 .",
        parents=("a_g18_practice",),
        paths=P_ROOT,
    ),
    _item(
        "g18_trade",
        32,
        _mark("TRADE: Includes self-employed tradesmen"),
        REM,
        ("amount",),
        identifier=None,
        parents=("a_g18_trade",),
        paths=P_ROOT,
    ),
    _item(
        "g18b",
        32,
        _mark("G18b.     FARMING or MARKET GARDENING"),
        REM,
        ("amount",),
        identifier="G18b.",
        parents=("a_g18b_farming",),
        paths=P_ROOT,
    ),
    _item(
        "g18c",
        32,
        _mark("G18c .    ROOMERS OR BOARDERS"),
        REM,
        ("amount",),
        identifier="G18c .",
        parents=("a_g18c_boarders",),
        paths=P_ROOT,
    ),
    _item(
        "g19a_c",
        32,
        _mark("G 19a-c. It is very important to select the"),
        CTX,
        ("reporting_unit",),
        identifier="G 19a-c.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g20a_c",
        32,
        _mark("G20a-c.   We want to know during which months"),
        CTX,
        ("month_or_exposure",),
        identifier="G20a-c.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g22_24",
        33,
        _mark("G22-24. The purpose of this sequence is to help"),
        REM,
        ("amount",),
        identifier="G22-24.",
        parents=("j_g22_extra",),
        paths=P_ROOT,
    ),
    _item(
        "g50_52",
        37,
        _mark("income from all work sources is recorded"),
        REM,
        ("amount",),
        identifier="GS0-52.",
        parents=("t_g50_wife_total",),
        paths=P_ROOT,
    ),
    _item(
        "gj0a_b",
        38,
        _mark("GJOa-b . Indicate which of seven places"),
        CTX,
        ("job_identifier",),
        identifier="GJOa-b .",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "gj3ab",
        38,
        _mark("GJ3ab .     If it was work hours for business"),
        CTX,
        ("assignment",),
        identifier="GJ3ab .",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "gj4",
        38,
        _mark("GJ4.        This is the number of calendar weeks"),
        CTX,
        ("month_or_exposure",),
        identifier="GJ4.",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "gj5",
        38,
        _mark("GJ5.        This is average hours per week"),
        CTX,
        ("month_or_exposure",),
        identifier="GJ5.",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "gj6_9",
        38,
        _mark("GJ6-9.      These dates will help us to check"),
        CTX,
        ("month_or_exposure",),
        identifier="GJ6-9.",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "gj10",
        38,
        _mark("GJlO .      We mention negative alternatives"),
        CTX,
        ("month_or_exposure",),
        identifier="GJlO .",
        parents=("j_gj_unreported",),
        paths=P_GJ,
    ),
    _item(
        "g75",
        40,
        _mark("G75.       Unlike the Head/Wife/"),
        CTX,
        ("interview_and_role_attachment",),
        identifier="G75.",
        parents=(),
        paths=P_OFUM,
    ),
    _item(
        "g76_82",
        40,
        _mark("G76-82. If this person's employment was irregular"),
        CTX,
        ("month_or_exposure",),
        identifier="G76-82.",
        parents=("j_g76_each_job",),
        paths=P_OFUM,
    ),
    _item(
        "g77",
        40,
        _mark("G77.       We use occupation to help us assign"),
        CTX,
        ("occupation",),
        identifier="G77.",
        parents=("j_g76_each_job",),
        paths=P_OFUM,
    ),
    _item(
        "g78",
        40,
        _mark("G78.       List total income from each job here."),
        REM,
        ("amount", "reporting_unit"),
        identifier="G78.",
        parents=("j_g76_each_job",),
        paths=P_OFUM,
    ),
    _item(
        "g79",
        40,
        _mark("G79 .      This figure should be the number of weeks"),
        CTX,
        ("month_or_exposure",),
        identifier="G79 .",
        parents=("j_g76_each_job",),
        paths=P_OFUM,
    ),
    _item(
        "g81",
        40,
        _mark("G8 l .    If employment was irregular"),
        CTX,
        ("month_or_exposure",),
        identifier="G8 l .",
        parents=("j_g76_each_job",),
        paths=P_OFUM,
    ),
    _item(
        "g92_98",
        41,
        _mark("G92-98 . Note these questions are only about"),
        CTX,
        ("assignment",),
        identifier="G92-98 .",
        parents=("j_g92_child_jobs",),
        paths=P_OFUM,
    ),
    _item(
        "g92_94ff",
        41,
        _mark("G92-94ff.     We need enough detail to calculate"),
        REM,
        ("amount",),
        identifier="G92-94ff.",
        parents=("j_g92_child_jobs",),
        paths=P_OFUM,
    ),
    _item(
        "k44",
        52,
        _mark("K44.       This means the number of years in which"),
        CTX,
        ("month_or_exposure",),
        identifier="K44.",
        parents=(),
        paths=P_K,
    ),
    _item(
        "k45",
        52,
        _mark("K45 .      Thirty-five hours or more per week"),
        CTX,
        ("month_or_exposure",),
        identifier="K45 .",
        parents=(),
        paths=P_K,
    ),
    _item(
        "l4_5",
        53,
        _mark("L4-5.        Probe to get as clear a picture"),
        CTX,
        ("occupation",),
        identifier="L4-5.",
        parents=(),
        paths=P_L,
    ),
    _item(
        "l6",
        53,
        _mark("L6.          We are interested in the similarity"),
        CTX,
        ("occupation",),
        identifier="L6.",
        parents=(),
        paths=P_L,
    ),
    _item(
        "b35_36",
        16,
        _mark("B35-36. See B9-B9a for probes and cautions"),
        CTX,
        ("occupation",),
        identifier="B35-36.",
        parents=("j_b_main_job",),
        paths=P_BC,
    ),
    _item(
        "b41_41c",
        17,
        _mark("B41-41c See B9-Bll instructions."),
        CTX,
        ("industry", "occupation", "job_identifier"),
        identifier="B41-41c",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b42",
        17,
        _mark("B42.       See B39."),
        CTX,
        ("month_or_exposure",),
        identifier="B42.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b43_44",
        17,
        _mark("B43-44.               See B4-B5"),
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        identifier="B43-44.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b45b",
        17,
        _mark("B45b.                 See B38"),
        REM,
        ("amount",),
        identifier="B45b.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b49_49a",
        18,
        _mark("B49-49a.             See B9-9a"),
        CTX,
        ("occupation",),
        identifier="B49-49a.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b52",
        18,
        _mark("B52.                 See B38"),
        REM,
        ("amount",),
        identifier="B52.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "b57a",
        18,
        _mark("B57a.                See B38"),
        REM,
        ("amount",),
        identifier="B57a.",
        parents=("j_b40_other_employer",),
        paths=P_BC,
    ),
    _item(
        "s41_41c",
        19,
        _mark("S41-41c.    See B9-Bll instructions"),
        CTX,
        ("industry", "occupation", "job_identifier"),
        identifier="S41-41c.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s42",
        19,
        _mark("S42.        See B39 instructions."),
        CTX,
        ("month_or_exposure",),
        identifier="S42.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s42a_42d",
        19,
        _mark("S42a-42d.   See B42a-42d"),
        CTX,
        ("month_or_exposure",),
        identifier="S42a-42d.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s43_44",
        19,
        _mark("S43-44.     See B4-B5"),
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        identifier="S43-44.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s45b",
        19,
        _mark("S45b .      See B38"),
        REM,
        ("amount",),
        identifier="S45b .",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s46_47",
        19,
        _mark("S46-47.     See B25-B29"),
        CTX,
        ("month_or_exposure",),
        identifier="S46-47.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s49_49a",
        19,
        _mark("S49-49a.    See B9-B9a"),
        CTX,
        ("occupation",),
        identifier="S49-49a.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s52",
        19,
        _mark("S52 .       See B38 instruction."),
        REM,
        ("amount",),
        identifier="S52 .",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s53_55",
        19,
        _mark("S53-55.     See B53-B55"),
        CTX,
        ("month_or_exposure",),
        identifier="S53-55.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s57a",
        19,
        _mark("S57a.       See B38 instructions."),
        REM,
        ("amount",),
        identifier="S57a.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "s59",
        19,
        _mark("S59.        Complete one WHS for each additional employer"),
        CTX,
        ("job_identifier",),
        identifier="S59.",
        parents=("j_whs_additional",),
        paths=P_BC,
    ),
    _item(
        "b83_85",
        23,
        _mark("B83-85. Follow the same general rules"),
        CTX,
        ("industry", "occupation"),
        identifier="B83-85.",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "b86",
        23,
        _mark("B86.     See Bll QxQ ."),
        CTX,
        ("job_identifier",),
        identifier="B86.",
        parents=("j_b82_extra_job",),
        paths=P_BC,
    ),
    _item(
        "c9_11",
        25,
        _mark("C9-11.   Probe for detail, as in the occupation/industry"),
        CTX,
        ("industry", "occupation"),
        identifier="C9-11.",
        parents=("j_c_last_job",),
        paths=P_C,
    ),
    _item(
        "c12_14",
        25,
        _mark("C12-14 . For instructions , see B4-B5."),
        CTX,
        ("employee_self_or_mixed", "incorporation"),
        identifier="C12-14 .",
        parents=("j_c_last_job",),
        paths=P_C,
    ),
    _item(
        "c14a",
        25,
        _mark("C14a.    See Bl 1 instructions."),
        CTX,
        ("job_identifier",),
        identifier="C14a.",
        parents=("j_c_last_job",),
        paths=P_C,
    ),
    _item(
        "c15",
        25,
        _mark("Cl5.     See B55 instructions."),
        CTX,
        ("month_or_exposure",),
        identifier="Cl5.",
        parents=("j_c_last_job",),
        paths=P_C,
    ),
    _item(
        "g1a",
        29,
        _mark("Gla.      You will know from B9b and BlO"),
        CTX,
        ("occupation",),
        identifier="Gla.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g17e",
        32,
        _mark("G17e.     If there are no work hours reported in Section B"),
        CTX,
        ("job_identifier",),
        identifier="G17e.",
        parents=(),
        paths=P_ROOT,
    ),
    _item(
        "g92_94cc",
        41,
        _mark("G92-G94cc See instructions for G92-G94ff"),
        CTX,
        ("assignment",),
        identifier="G92-G94cc",
        parents=("j_g92_child_jobs",),
        paths=P_OFUM,
    ),
    _item(
        "gj3_3a",
        38,
        _mark("GJ3-3a . Follow the same general rules"),
        CTX,
        ("industry", "occupation"),
        identifier="GJ3-3a .",
        parents=("j_gj_unreported",),
        paths=P_GJ,
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
        "ri_b4_note",
        11,
        _mark("For more information on main vs. extra jobs, see B82 Q-x-Qs."),
        P_BC,
    ),
    _ri(
        "ri_b35_36",
        16,
        _mark("B35-36. See B9-B9a for probes and cautions"),
        P_BC,
    ),
    _ri("ri_b41", 17, _mark("B41-41c See B9-Bll instructions."), P_BC),
    _ri("ri_b42", 17, _mark("B42.       See B39."), P_BC),
    _ri("ri_b43_44", 17, _mark("B43-44.               See B4-B5"), P_BC),
    _ri("ri_b45b", 17, _mark("B45b.                 See B38"), P_BC),
    _ri("ri_b46_47", 17, _mark("cautions and instructions at B25-B29"), P_BC),
    _ri("ri_b49", 18, _mark("B49-49a.             See B9-9a"), P_BC),
    _ri("ri_b52", 18, _mark("B52.                 See B38"), P_BC),
    _ri("ri_b57a", 18, _mark("B57a.                See B38"), P_BC),
    _ri("ri_s41", 19, _mark("S41-41c.    See B9-Bll instructions"), P_BC),
    _ri("ri_s42", 19, _mark("S42.        See B39 instructions."), P_BC),
    _ri("ri_s42a", 19, _mark("S42a-42d.   See B42a-42d"), P_BC),
    _ri("ri_s43", 19, _mark("S43-44.     See B4-B5"), P_BC),
    _ri("ri_s45b", 19, _mark("S45b .      See B38"), P_BC),
    _ri("ri_s46", 19, _mark("S46-47.     See B25-B29"), P_BC),
    _ri("ri_s49", 19, _mark("S49-49a.    See B9-B9a"), P_BC),
    _ri("ri_s52", 19, _mark("S52 .       See B38 instruction."), P_BC),
    _ri("ri_s53", 19, _mark("S53-55.     See B53-B55"), P_BC),
    _ri("ri_s57a", 19, _mark("S57a.       See B38 instructions."), P_BC),
    _ri(
        "ri_s59",
        19,
        _mark("S59.        Complete one WHS for each additional employer"),
        P_BC,
    ),
    _ri("ri_b83_85", 23, _mark("B83-85. Follow the same general rules"), P_BC),
    _ri("ri_b86", 23, _mark("B86.     See Bll QxQ ."), P_BC),
    _ri(
        "ri_b94_105",
        24,
        _span(
            "The sequence on pp. 24-25 (B94-Bl05) is a repeat of B82-B93",
            "not duplicated here.",
        ),
        P_BC,
    ),
    _ri("ri_c2", 25, _mark("C2.      See instructions for B21."), P_C),
    _ri(
        "ri_c9_11",
        25,
        _mark("C9-11.   Probe for detail, as in the occupation/industry"),
        P_C,
    ),
    _ri("ri_c12_14", 25, _mark("C12-14 . For instructions , see B4-B5."), P_C),
    _ri("ri_c14a", 25, _mark("C14a.    See Bl 1 instructions."), P_C),
    _ri("ri_c15", 25, _mark("Cl5.     See B55 instructions."), P_C),
    _ri("ri_c16_51", 25, _mark("instructions given for B24-B59"), P_C),
    _ri(
        "ri_c52_98",
        25,
        _span(
            "C52-98. We have not reproduced the remainder of Section C",
            "they parallel B60-B 106.",
        ),
        P_C,
    ),
    _ri(
        "ri_de_numbered",
        26,
        _mark("respectively, and the questions are numbered identically"),
        P_DE,
    ),
    _ri(
        "ri_de_parallel",
        26,
        _mark("Question objectives and concepts for B and C apply to D and E"),
        P_DE,
    ),
    _ri(
        "ri_de_remainder",
        26,
        _span(
            "We have not reproduced the remainder of Sections D and E",
            "questionnaire), as they parallel Sections B and C exactly.",
        ),
        P_DE,
    ),
    _ri(
        "ri_f2_3",
        27,
        _mark("work and should be included in Section B or C (for the Head)"),
        P_F2,
    ),
    _ri("ri_g1a", 29, _mark("Gla.      You will know from B9b and BlO")),
    _ri(
        "ri_g1a_g52",
        29,
        _mark("work hours in Section DIE; you may simply cross-reference"),
    ),
    _ri(
        "ri_g_box1",
        30,
        _span(
            "WE MUST HA VE WORK HOURS FOR ALL INCOME FROM A JOB AND",
            "SENDING THE COMPLETED INTERVIEW IN .",
        ),
    ),
    _ri(
        "ri_g9a_9d",
        30,
        _mark("G9a-G9d.               These questions are crucial."),
    ),
    _ri(
        "ri_g_box2",
        31,
        _span(
            "WE MUST HA VE WORK HOURS FOR ALL INCOME FROM A JOB AND",
            "SENDING THE COMPLETED INTERVIEW IN.",
        ),
    ),
    _ri(
        "ri_g17e",
        32,
        _mark("G17e.     If there are no work hours reported in Section B"),
    ),
    _ri(
        "ri_g18c_hours",
        32,
        _mark("this question, work hours should be mentioned in Section B/C"),
    ),
    _ri(
        "ri_g21a_c",
        32,
        _mark("G21a-c. Again, make sure you have work hours in Section B/C"),
    ),
    _ri(
        "ri_g50_52",
        37,
        _mark("GS0-52. Remember that work hours in Section DIE imply income"),
    ),
    _ri(
        "ri_g52b",
        37,
        _mark("G52b.      Again, if income is reported but no work hours"),
    ),
    _ri("ri_g53", 37, _mark("G53.       See G44a instructions.")),
    _ri("ri_g56", 37, _mark("G56.       See G44b instructions.")),
    _ri(
        "ri_g60",
        37,
        _mark("G60-60dd.     These questions are the same as those asked"),
    ),
    _ri("ri_g61", 37, _mark("G61.          See G40 instructions.")),
    _ri("ri_g62", 37, _mark("G62.          See G44e-f instructions.")),
    _ri(
        "ri_gj0",
        38,
        _span(
            "G9b      HEAD'S BUSINESS Income",
            "G52b Wife ' s/\"WIFE' S\" WAGE/SALARY Income",
        ),
        P_GJ,
    ),
    _ri("ri_gj3", 38, _mark("GJ3-3a . Follow the same general rules"), P_GJ),
    _ri(
        "ri_g75",
        40,
        _mark("as many as apply to the OFUM's current situation."),
        P_OFUM,
    ),
    _ri("ri_g79", 40, _mark("for B78 ."), P_OFUM),
    _ri(
        "ri_g81",
        40,
        _mark("the total number of hours worked in 1995 at that job."),
        P_OFUM,
    ),
    _ri(
        "ri_g92_94cc",
        41,
        _mark("G92-G94cc See instructions for G92-G94ff"),
        P_OFUM,
    ),
    _ri(
        "ri_l4_5",
        53,
        _mark("L4-5.        Probe to get as clear a picture as possible"),
        P_L,
    ),
    _ri(
        "ri_l14_58",
        54,
        _span(
            "L14-58.   From this point to the end of the New Head section",
            'for New Wife/"Wife." See Section K for instructions',
        ),
        P_L,
    ),
)


XREF = "explicit_cross_reference"
REPEATED = "explicit_repeat_instruction"
RESOLVED_HANDOFF = "local_resolved_cross_reference_for_global_assembly"

# Resolved alias evidence: both endpoints carry a retained local anchor.
RESOLVED_ALIAS_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (XREF, "ri_b4_note", "j_b_main_job", "j_b82_extra_job"),
    (XREF, "ri_b35_36", "b35_36#a", "b9_9a#a"),
    (XREF, "ri_b41", "b41_41c#a", "b9_9a#a"),
    (XREF, "ri_b41", "b41_41c#a", "b10#a"),
    (XREF, "ri_b41", "b41_41c#a", "b11#a"),
    (XREF, "ri_b42", "b42#a", "b39#a"),
    (XREF, "ri_b43_44", "b43_44#a", "b4#a"),
    (XREF, "ri_b43_44", "b43_44#a", "b5#a"),
    (XREF, "ri_b45b", "b45b#a", "b38#a"),
    (XREF, "ri_b46_47", "b46_47#a", "b25_29#a"),
    (XREF, "ri_b49", "b49_49a#a", "b9_9a#a"),
    (XREF, "ri_b52", "b52#a", "b38#a"),
    (XREF, "ri_b57a", "b57a#a", "b38#a"),
    (XREF, "ri_s41", "s41_41c#a", "b9_9a#a"),
    (XREF, "ri_s41", "s41_41c#a", "b10#a"),
    (XREF, "ri_s41", "s41_41c#a", "b11#a"),
    (XREF, "ri_s42", "s42#a", "b39#a"),
    (XREF, "ri_s42a", "s42a_42d#a", "b42a_42d#a"),
    (XREF, "ri_s43", "s43_44#a", "b4#a"),
    (XREF, "ri_s43", "s43_44#a", "b5#a"),
    (XREF, "ri_s45b", "s45b#a", "b38#a"),
    (XREF, "ri_s46", "s46_47#a", "b25_29#a"),
    (XREF, "ri_s49", "s49_49a#a", "b9_9a#a"),
    (XREF, "ri_s52", "s52#a", "b38#a"),
    (XREF, "ri_s53", "s53_55#a", "b53_55#a"),
    (XREF, "ri_s57a", "s57a#a", "b38#a"),
    (REPEATED, "ri_s59", "s59#a", "j_whs_additional"),
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
    (XREF, "ri_c16_51", "c16_51#a", "b_work_history#a"),
    (XREF, "ri_g1a", "g1a#a", "b9_9a#a"),
    (XREF, "ri_g1a", "g1a#a", "b10#a"),
    (XREF, "ri_g1a_g52", "g1a#a", "g50_52#a"),
    (XREF, "ri_g17e", "g17e#a", "g13#a"),
    (XREF, "ri_gj0", "gj0a_b#a", "g17e#a"),
    (XREF, "ri_gj0", "gj0a_b#a", "a_g5_business"),
    (XREF, "ri_gj0", "gj0a_b#a", "g18#a"),
    (XREF, "ri_gj0", "gj0a_b#a", "g18b#a"),
    (XREF, "ri_gj0", "gj0a_b#a", "g18c#a"),
    (XREF, "ri_gj0", "gj0a_b#a", "g50_52#a"),
    (XREF, "ri_gj3", "gj3_3a#a", "b9_9a#a"),
    (XREF, "ri_g75", "g75#a", "b1_3#a"),
    (XREF, "ri_g79", "g79#a", "b78#a"),
    (XREF, "ri_g81", "g81#a", "b79#a"),
    (XREF, "ri_g92_94cc", "g92_94cc#a", "g92_94ff#a"),
    (XREF, "ri_l4_5", "l4_5#a", "b9_9a#a"),
    (XREF, "ri_l4_5", "l4_5#a", "b10#a"),
)


OUTSIDE = "local_target_outside_rq_annotation_domain"
SERIES = "local_series_target_unresolved_for_global_assembly"
CROSSDOC = "cross_document_target_unresolved_for_global_assembly"

# Unresolved alias evidence: the printed target is a whole question series or
# an item this review did not retain.  It is preserved verbatim for global
# assembly and is never silently bound inside the shard.
UNRESOLVED_ALIAS_SPECS: tuple[dict[str, Any], ...] = (
    {
        "relation": REPEATED,
        "instruction": "ri_b94_105",
        "page": 24,
        "target": "B82-B93",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_c2",
        "page": 25,
        "target": "B21",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_c52_98",
        "page": 25,
        "target": "B60-B 106",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_de_numbered",
        "page": 26,
        "target": "B with D and C with E",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_de_parallel",
        "page": 26,
        "target": "B and C apply to D and E",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_de_remainder",
        "page": 26,
        "target": "Sections B and C exactly",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_f2_3",
        "page": 27,
        "target": "Section B or C",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g_box1",
        "page": 30,
        "target": "SECTIONS B-E",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g9a_9d",
        "page": 30,
        "target": "Section B/C",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g_box2",
        "page": 31,
        "target": "SECTIONS B-E",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g18c_hours",
        "page": 32,
        "target": "Section B/C",
        "handoff": SERIES,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g21a_c",
        "page": 32,
        "target": "Section B/C",
        "target_occurrence": 1,
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g50_52",
        "page": 37,
        "target": "Section DIE",
        "handoff": SERIES,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g52b",
        "page": 37,
        "target": "Section D or E",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g53",
        "page": 37,
        "target": "G44a",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_g56",
        "page": 37,
        "target": "G44b",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_g60",
        "page": 37,
        "target": "asked for the Head",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g61",
        "page": 37,
        "target": "G40",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_g62",
        "page": 37,
        "target": "G44e-f",
        "handoff": OUTSIDE,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_l14_58",
        "page": 54,
        "target": "Section K",
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
        raise ValueError("document-56 independently replayed identity drift")

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


CANDIDATE_DENOMINATOR = 3758


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-56 source and sealing invariant."""

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
        raise ValueError("document-56 candidate denominator drift")
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-56 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 56: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
