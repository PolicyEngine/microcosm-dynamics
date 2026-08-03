#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for fam1971_QxQs.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 92-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

fam1971_QxQs.pdf interleaves the printed 1971 family questionnaire with the
matching question-by-question objectives manual.  The retention test applied
throughout is whether the printed text *establishes* a document-local R_Q
fact for a named printed item or item series -- a role attachment, a job
slot, a remuneration component, an aggregate, a retained contextual field, a
field purpose, a controlling condition, or an explicit repeat/cross-reference.

Four document-wide retention rules were applied during the complete pass:

  1. Only the Head and the Wife are role-bearing.  The H20-H32 "anyone else
     living here" income grid, its ``GO BACK TO H20`` repeat instruction, and
     the p.25 repetition note establish no anchor inside the two-role domain
     and are rejected in full.
  2. Non-employment subject matter is rejected even where it carries
     work-like lexemes: children and schooling, transportation and commuting
     (D34-D41, E12-E19, G8-G9), housing tenure/mortgage/utilities, do-it-
     yourself repair savings, housework and child care, food and expenditure,
     transfer/property/pension/benefit receipt (H11c-H11k, H33-H52),
     health, union dues, time use, feelings, family background, and
     by-observation items.
  3. Hypothetical, prospective, and labor-supply-preference items state no
     realized remuneration: D30-D33, D46-D54, E1-E5, E24-E28, F2, F6-F13,
     F15-F16, G6-G7, G10-G14.  Probe follow-ups that add no distinct printed
     field (D3, D26) are rejected against the printed item they probe.
  4. An exclusion cross-reference that only forbids double counting states no
     alias between retained anchors and is rejected; a cross-reference that
     names where a component *does* belong is retained.

Two printed in-kind fields survive rule 2 on their own printed evidence
rather than on lexeme matching: C14 ("Do you do some work in return for your
housing?") and C15, because the p.5 objective states that such housing "may
be part of the benefits on one's regular job".  G38-G41 (meals at work or at
school) does not survive: it is printed as a family food-expenditure measure,
covers school as well as work, and attaches to no role.

Flow discipline: a branch is emitted only where the printed conditional label
survives in the extracted page bytes *and* gates a retained R_Q item series.
Several 1971 answer boxes are lost to OCR (the D20 and H5 affirmative boxes,
the F1 and G2 affirmative boxes); no branch is fabricated for them, so the
items they gate resolve at their nearest lawful printed ancestor path.
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
DOCUMENT_POSITION = 7
DOCUMENT_ID = (
    "psid-source-document:"
    "0b593711db0765737c383e7f0d4a963d0771fe34256db6a1b1b7956d6d5e0448"
)
INTERVIEW_WAVE = 1971
CANONICAL_SOURCE_PATH = "documentation/capture1/fam1971_QxQs.pdf"
PDF_FILENAME = "fam1971_QxQs.pdf"
PDF_SIZE = 24_196_248
PDF_SHA256 = "bf11433773143970a0d63311359bea435e66e4354c2bd2d61d28225411b9ef54"
PAGE_COUNT = 92
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_01_documents_001_010"
    / "document_007_fam1971_QxQs_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_007_fam1971_QxQs_annotation_v1.json"
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
    "2888e142ea23ee762f61c84969a3555adcfd383c72c3e0cf1fe7e6f115f75167"
)
CANDIDATE_CONTENT_SHA256 = (
    "fd32d29ea417bcd7dad688e4bae7f68100709ae8863db399c8a6f624aecb737a"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "15265147f7c89fb145d78cc5ba2c9839afdb746553baafe0af422bb0738e35de"
)

FLOW_ROOT = "questionnaire-flow:root"
OCCURRENCE_KINDS = candidates.OCCURRENCE_KINDS
KIND_ORDER = {kind: index for index, kind in enumerate(OCCURRENCE_KINDS)}
FIELD_PURPOSES = (
    "interview_and_role_attachment",
    "employment_status",
    "job_identifier",
    "occupation",
    "industry",
    "employee_self_or_mixed",
    "incorporation",
    "job_tenure",
    "weeks_worked",
    "hours_worked",
    "time_not_worked",
    "receipt_indicator",
    "income_source",
    "amount",
    "rate",
    "reporting_unit",
    "in_kind_receipt",
    "farm_receipts",
    "farm_operating_expenses",
    "net_farm_income",
    "business_share",
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
        raise ValueError("document-7 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-7 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-7 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-7 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / PDF_FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1971_QxQs.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("fam1971_QxQs.pdf page-count drift")
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
        raise ValueError("document-7 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-7 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-7 empty-text page domain drift")
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


SELECTOR_KEYS = frozenset(
    {
        "line_marker",
        "start_marker",
        "end_marker",
        "needle",
        "needle_occurrence",
        "inline_marker",
    }
)


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


# ---------------------------------------------------------------------------
# Reviewer decisions.  These are not detector rules: each selector names text
# read during the complete 92-page pass and is re-resolved against the
# authenticated fam1971_QxQs.pdf bytes.
# ---------------------------------------------------------------------------

# Controlling flow.  The p.7 objectives page states the three sequence
# conditions in printed words; the remaining branches are printed answer-box
# labels whose text survives OCR and which gate a retained item series.
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _in(
        "!1. OWNS OR IS BUYING",
        "8. NEITHER",
    )
    | {"key": "f_c_neither", "page": 7},
    _mark("Working Now, or Only Temporarily Laid Off")
    | {
        "key": "f_d_seq",
        "page": 16,
    },
    _mark("Looking For Work (Unemployed)") | {"key": "f_e_seq", "page": 16},
    _mark("Retired, Permanently Disabled, Housewife or Student--Ask F")
    | {
        "key": "f_f_seq",
        "page": 16,
    },
    _in("5. NO   (GO TO D30)", "l. YES")
    | {"key": "f_d24_yes", "page": 22, "parent": "f_d_seq"},
    _in("NOT A FAR.t'1ER OR RANCHER", "1. rARMER, OR RANCHER")
    | {"key": "f_h1_farmer", "page": 48},
    _in("o=UNINCORPORATED", "UNINCORPORATED")
    | {"key": "f_h6_uninc", "page": 48},
    _in("I 3. BOTH I", "3. BOTH") | {"key": "f_h6_both", "page": 48},
    _in("]NO WIFE IN DU", "IN DU") | {"key": "f_h17_wife", "page": 57},
    _in("5. THIS FU HAS TH", "FU HAS A NEW HEAD THIS YEAR")
    | {"key": "f_l_new_head", "page": 78},
)

ROOT_PATH = ("root",)
P_ROOT = (("root",),)
P_C = (("root", "f_c_neither"),)
P_D = (("root", "f_d_seq"),)
P_D24 = (("root", "f_d_seq", "f_d24_yes"),)
P_E = (("root", "f_e_seq"),)
P_F = (("root", "f_f_seq"),)
P_FARM = (("root", "f_h1_farmer"),)
P_H7 = (("root", "f_h6_uninc"), ("root", "f_h6_both"))
P_WIFE_DU = (("root", "f_h17_wife"),)
P_L = (("root", "f_l_new_head"),)


def _anchor(
    key: str,
    page: int,
    kind: str,
    selector: Mapping[str, Any],
    *,
    classification: str | None = None,
    identifier: str | None = None,
    identifier_occurrence: int = 0,
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
        "identifier_occurrence": identifier_occurrence,
        "parents": parents,
        "paths": paths,
        **{k: v for k, v in selector.items() if k in SELECTOR_KEYS},
    }


HEAD = "head_or_reference_person"
SPOUSE = "spouse_or_partner"

# Standalone role and job anchors: the printed lexeme that names the node.
STANDALONE_ANCHORS: tuple[dict[str, Any], ...] = (
    _anchor(
        "r_head_d1",
        15,
        "role_anchor",
        _in("We would like to know", "(HEAD's)"),
        classification=HEAD,
    ),
    _anchor(
        "j_main",
        15,
        "job_anchor",
        _in("Dl.   We would like to know", "present job"),
    ),
    _anchor(
        "j_prior",
        15,
        "job_anchor",
        _in(
            "What happened to the job you had before", "the job you had before"
        ),
        paths=P_D,
    ),
    _anchor(
        "j_extra",
        22,
        "job_anchor",
        _in("D24. · Did you have any extra jobs", "extra jobs"),
        paths=P_D,
    ),
    _anchor(
        "j_last_e",
        29,
        "job_anchor",
        _in("E6.   What sort of work did you do", "your last job"),
        paths=P_E,
    ),
    _anchor(
        "r_head_f",
        35,
        "role_anchor",
        _in("Fl.   During the last year (1970)", "(HEAD)"),
        classification=HEAD,
        paths=P_F,
    ),
    _anchor(
        "j_f_work",
        35,
        "job_anchor",
        _in("Fl.   During the last year (1970)", "work for money"),
        paths=P_F,
    ),
    _anchor(
        "r_wife_g2",
        38,
        "role_anchor",
        _in("G2.    Did your wife do any work for money", "wife"),
        classification=SPOUSE,
    ),
    _anchor(
        "j_wife",
        38,
        "job_anchor",
        _in("G2.    Did your wife do any work for money", "work for money"),
    ),
    _anchor(
        "r_head_h8",
        48,
        "role_anchor",
        _in("receive from v.;ages and salaries", "(HEAD)"),
        classification=HEAD,
    ),
    _anchor(
        "r_head_h11",
        52,
        "role_anchor",
        _in("Hll. Did you (HEAD) receive any other income", "(HEAD)"),
        classification=HEAD,
    ),
    _anchor(
        "r_wife_h18",
        57,
        "role_anchor",
        _in("Hl8.   Did your wife have any income", "wife"),
        classification=SPOUSE,
    ),
    _anchor(
        "j_first",
        78,
        "job_anchor",
        _in(
            "Thinking of your first full time regular job",
            "first full time regular job",
        ),
        paths=P_L,
    ),
    _anchor(
        "r_head_l",
        79,
        "role_anchor",
        _in(
            "This section's questions apply to the Head of the FU.",
            "Head of the FU",
        ),
        classification=HEAD,
        paths=P_L,
    ),
)

CTX = "context_anchor"
REM = "remuneration_component_anchor"
TOT = "role_total_anchor"
FARM = "farm_aggregate_anchor"
BUS = "business_aggregate_anchor"


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
        **{k: v for k, v in selector.items() if k in SELECTOR_KEYS},
    }


# Retained printed instrument items.  The retained span is the trimmed
# printed line (or printed block) that carries the item's identifier; the
# same span carries the item's anchor and its field-purpose prompt.
ITEM_SPECS: tuple[dict[str, Any], ...] = (
    # Section C -- housing received in return for work (in-kind pay).
    _item(
        "c14",
        10,
        _mark("Cl4.    Do you do some work in return for your housing?"),
        REM,
        ("in_kind_receipt",),
        "Cl4.",
        (),
        P_C,
    ),
    _item(
        "c15",
        10,
        _mark("Cl5.    How much would it rent for if it were rented?"),
        REM,
        ("in_kind_receipt", "amount", "reporting_unit"),
        "Cl5.",
        ("c14#a",),
        P_C,
    ),
    # Section D -- employment of the Head.
    _item(
        "d1",
        15,
        _span(
            "Dl.   We would like to know about your (HEAD's) present job",
            "now, looking for work, retired, a housewife, or 'ivhat?",
        ),
        CTX,
        ("interview_and_role_attachment", "employment_status"),
        "Dl.",
        ("r_head_d1", "j_main"),
    ),
    _item(
        "d2",
        15,
        _mark("D2.    What is your main occupation?"),
        CTX,
        ("occupation",),
        "D2.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d3a",
        15,
        _mark("D3a. What kind of business is that in?"),
        CTX,
        ("industry",),
        "D3a.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d4",
        15,
        _mark("D4.    Do you work f or someone else, yourself, cr what?"),
        CTX,
        ("employee_self_or_mixed",),
        "D4.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d5",
        15,
        _mark("DS.    How long have you had this job?"),
        CTX,
        ("job_tenure",),
        "DS.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d6",
        15,
        _span(
            "D6.    What happened to the job you had before",
            "laid off, or what?",
        ),
        CTX,
        ("employment_status",),
        "D6.",
        ("j_prior",),
        P_D,
    ),
    _item(
        "d7",
        15,
        _mark(
            "D7 .   Does your present job pay more than the one you had before?"
        ),
        CTX,
        ("rate",),
        "D7 .",
        ("j_main", "j_prior"),
        P_D,
    ),
    _item(
        "d10_11",
        19,
        _mark("DlO.   Did you take any vacation during 1970?"),
        CTX,
        ("time_not_worked",),
        "DlO.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d12_13",
        19,
        _span(
            "Dl2.   Did you miss any work in 1970 because you were sick",
            "in the family was sick?",
        ),
        CTX,
        ("time_not_worked",),
        "Dl2.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d14_15",
        19,
        _mark(
            "Dl4.   Did you miss any ~.;ork in 1970 because you were unemployed"
        ),
        CTX,
        ("time_not_worked",),
        "Dl4.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d16",
        19,
        _mark(
            "Dl6.   Then, how many weeks did you actually work on your main job"
        ),
        CTX,
        ("weeks_worked",),
        "Dl6.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d17",
        19,
        _span(
            "Dl7.   And, on the average,how many hours a week did you work",
            "year?",
        ),
        CTX,
        ("hours_worked",),
        "Dl7.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d18",
        19,
        _mark(
            "Dl8.   Did you have any overtime which isn't included in that?"
        ),
        CTX,
        ("hours_worked",),
        "Dl8.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d19",
        19,
        _mark("Dl9. How many hours did that overtime amount to in 1970?"),
        CTX,
        ("hours_worked",),
        "Dl9.",
        ("d18#a",),
        P_D,
    ),
    _item(
        "d20",
        19,
        _span(
            "D20.   If you were to work more hours than usual during some week",
            "for those extra hours of work?",
        ),
        CTX,
        ("rate",),
        "D20.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d21",
        19,
        _in(
            "D21 . What would be your hourly rate",
            "D21 . What would be your hourly rate",
        ),
        REM,
        ("rate",),
        "D21 .",
        ("j_main",),
        P_D,
    ),
    _item(
        "d22",
        19,
        _in(
            "D22. Do you have an hourly wage rate",
            "D22. Do you have an hourly wage rate",
        ),
        CTX,
        ("rate",),
        "D22.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d23",
        19,
        _mark("D23.   What is your hourly wage rate for your regular"),
        REM,
        ("rate",),
        "D23.",
        ("j_main",),
        P_D,
    ),
    _item(
        "d24",
        22,
        _span(
            "D24. · Did you have any extra jobs or other ways of making money",
            "your main job in 1970?",
        ),
        CTX,
        ("receipt_indicator",),
        "D24.",
        ("j_extra", "j_main"),
        P_D,
    ),
    _item(
        "d25",
        22,
        _mark("D25. What did you do?"),
        CTX,
        ("occupation",),
        "D25.",
        ("j_extra",),
        P_D24,
    ),
    _item(
        "d27",
        22,
        _mark("D27. About how much did you make per hour at this?"),
        REM,
        ("rate",),
        "D27.",
        ("j_extra",),
        P_D24,
    ),
    _item(
        "d28",
        22,
        _mark(
            "D28. And how many weeks did you work on your extra job(s) in 1970?"
        ),
        CTX,
        ("weeks_worked",),
        "D28.",
        ("j_extra",),
        P_D24,
    ),
    _item(
        "d29",
        22,
        _mark(
            "D29.   On   the average, how many hours a week did you work on your extra"
        ),
        CTX,
        ("hours_worked",),
        "D29.",
        ("j_extra",),
        P_D24,
    ),
    # Section E -- Head looking for work; last job.
    _item(
        "e6",
        29,
        _mark("E6.   What sort of work did you do on your last job?"),
        CTX,
        ("occupation",),
        "E6.",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e6a",
        29,
        _mark("E6a . What kind of business was that in?"),
        CTX,
        ("industry",),
        "E6a .",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e6b",
        29,
        _span(
            "E6b. What happened to that job- did the company ,fold",
            "what?",
        ),
        CTX,
        ("employment_status",),
        "E6b.",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e7",
        29,
        _mark("E7.   How many weeks did you work in 1970?"),
        CTX,
        ("weeks_worked",),
        "E7.",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e8",
        29,
        _mark(
            "E8.   About how many hours a week did you work when you worked?"
        ),
        CTX,
        ("hours_worked",),
        "E8.",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e9",
        29,
        _mark("E9.   How many weeks were you sick in 1970?"),
        CTX,
        ("time_not_worked",),
        "E9.",
        ("j_last_e",),
        P_E,
    ),
    _item(
        "e10",
        29,
        _mark(
            "ElO.   Then, how many weeks were you unemployed or laid off in 1970?"
        ),
        CTX,
        ("time_not_worked",),
        "ElO.",
        ("j_last_e",),
        P_E,
    ),
    # Section F -- Head out of the labour force who nonetheless worked.
    _item(
        "f1",
        35,
        _mark(
            "Fl.   During the last year (1970), did you (HEAD) do any work for money?"
        ),
        CTX,
        ("employment_status", "receipt_indicator"),
        "Fl.",
        ("r_head_f", "j_f_work"),
        P_F,
    ),
    _item(
        "f3",
        35,
        _mark("F3.   What kind of work did you do when you worked?"),
        CTX,
        ("occupation",),
        "F3.",
        ("j_f_work",),
        P_F,
    ),
    _item(
        "f3a",
        35,
        _mark("F3a. What kind of business is that in?"),
        CTX,
        ("industry",),
        "F3a.",
        ("j_f_work",),
        P_F,
    ),
    _item(
        "f4",
        35,
        _mark("F4.   How many weeks did you work last year?"),
        CTX,
        ("weeks_worked",),
        "F4.",
        ("j_f_work",),
        P_F,
    ),
    _item(
        "f5",
        35,
        _mark(
            "F5.   About how many hours a week did you work (when you \\vorked)?"
        ),
        CTX,
        ("hours_worked",),
        "F5.",
        ("j_f_work",),
        P_F,
    ),
    # Section G -- the Wife's work.
    _item(
        "g_scope",
        38,
        _mark("(Q' s G2-G9 REFER TO WIFE's OCCUPATION)"),
        CTX,
        ("interview_and_role_attachment",),
        None,
        ("r_wife_g2", "j_wife"),
    ),
    _item(
        "g2",
        38,
        _mark("G2.    Did your wife do any work for money in"),
        CTX,
        ("receipt_indicator",),
        "G2.",
        ("j_wife",),
    ),
    _item(
        "g3",
        38,
        _mark("G3.    What kind of work did she do?"),
        CTX,
        ("occupation",),
        "G3.",
        ("j_wife",),
    ),
    _item(
        "g3a",
        38,
        _mark("G3a . What kind of business is that in?"),
        CTX,
        ("industry",),
        "G3a .",
        ("j_wife",),
    ),
    _item(
        "g4",
        38,
        _mark("G4.    About how many weeks did she .-10rk last year?"),
        CTX,
        ("weeks_worked",),
        "G4.",
        ("j_wife",),
    ),
    _item(
        "g5",
        38,
        _mark("GS.     And about how many hours"),
        CTX,
        ("hours_worked",),
        "GS.",
        ("j_wife",),
    ),
    # Section H -- income.
    _item(
        "h2",
        48,
        _span(
            "H2. What were your total receipts from farming in 1970",
            "soil bank payments and commodity credit loans?",
        ),
        FARM,
        ("farm_receipts", "amount"),
        "H2.",
        ("r_head_d1",),
        P_FARM,
    ),
    _item(
        "h3",
        48,
        _span(
            "H3. What were your total operating expenses?",
            "expenses?                                        ",
        ),
        FARM,
        ("farm_operating_expenses", "amount"),
        "H3.",
        ("h2#a",),
        P_FARM,
    ),
    _item(
        "h4",
        48,
        _mark("H4. That left you a net income from farming of?"),
        FARM,
        ("net_farm_income", "amount"),
        "H4.",
        ("h2#a", "h3#a"),
        P_FARM,
    ),
    _item(
        "h5",
        48,
        _span(
            "H5.   Did you (R AND FA}IILY) own a business at any time in 1970",
            "i nterest in any business enterprise?",
        ),
        BUS,
        ("receipt_indicator",),
        "H5.",
        ("r_head_d1",),
    ),
    _item(
        "h6",
        48,
        _span(
            "Is it a corporation or an unincorporated business",
            "interest in both kinds?",
        ),
        CTX,
        ("incorporation",),
        None,
        ("h5#a",),
    ),
    _item(
        "h7",
        48,
        _span(
            "H7. How much was your (FAMILY's) share of the total income from the business",
            "in 1970 - that is~ the amount you took out plus any profit left in ?",
        ),
        BUS,
        ("business_share", "amount"),
        "H7.",
        ("h5#a",),
        P_H7,
    ),
    _item(
        "h8",
        48,
        _span(
            "H8 .   How much did you (HEAD) receive from v.;ages and salaries in 1970",
            "anything was deducted for taxes or other things?",
        ),
        TOT,
        ("amount",),
        "H8 .",
        ("r_head_h8",),
    ),
    _item(
        "h9",
        52,
        _span(
            "H9.   In addition to this1 did you have any income from bonuses, overtime",
            "commissions?",
        ),
        REM,
        ("receipt_indicator",),
        "H9.",
        ("r_head_h8",),
    ),
    _item(
        "h10",
        52,
        _mark("HlO. How much was that?"),
        REM,
        ("amount",),
        "HlO.",
        ("h9#a",),
    ),
    _item(
        "h11",
        52,
        _mark("Hll. Did you (HEAD) receive any other income in 1970 from:"),
        CTX,
        ("interview_and_role_attachment", "income_source"),
        "Hll.",
        ("r_head_h11",),
    ),
    _item(
        "h11a",
        52,
        _in(
            "a) professional practice or trade?",
            "a) professional practice or trade?",
        ),
        REM,
        ("income_source", "amount", "reporting_unit"),
        "a)",
        ("r_head_h11",),
    ),
    _item(
        "h11b",
        52,
        _in(
            "b) farming or market gardening,",
            "b) farming or market gardening,",
        ),
        FARM,
        ("income_source", "amount", "reporting_unit"),
        "b)",
        ("r_head_h11",),
    ),
    _item(
        "h17",
        57,
        _mark("Hl7.   INTERVIEWER:    DOES HEAD HAVE IHFE IN DU?"),
        CTX,
        ("interview_and_role_attachment",),
        "Hl7.",
        ("r_wife_h18",),
    ),
    _item(
        "h18",
        57,
        _mark("Hl8.   Did your wife have any income during 1970?"),
        CTX,
        ("receipt_indicator",),
        "Hl8.",
        ("r_wife_h18",),
        P_WIFE_DU,
    ),
    _item(
        "h19",
        57,
        _mark("Hl9 . Was it income from wages, salary, a business, or"),
        CTX,
        ("income_source",),
        "Hl9 .",
        ("r_wife_h18", "j_wife"),
        P_WIFE_DU,
    ),
    _item(
        "h19a",
        57,
        _mark("Hl9a . How much was it before deductions?"),
        TOT,
        ("amount",),
        "Hl9a .",
        ("r_wife_h18",),
        P_WIFE_DU,
    ),
    # Section L -- the Head's first job and job history.
    _item(
        "l4",
        78,
        _mark(
            "14. Thinking of your first full time regular job, what did you do?"
        ),
        CTX,
        ("occupation",),
        "14.",
        ("j_first",),
        P_L,
    ),
    _item(
        "l5",
        78,
        _span(
            "15. Have you had a number of different kinds of jobs",
            "in the same occupation you started in, or what?",
        ),
        CTX,
        ("job_identifier", "occupation"),
        "15.",
        ("j_first",),
        P_L,
    ),
)


def _purpose(
    key: str,
    page: int,
    selector: Mapping[str, Any],
    purposes: tuple[str, ...],
    anchors: tuple[str, ...],
    paths: tuple[tuple[str, ...], ...] = P_ROOT,
) -> dict[str, Any]:
    return {
        "key": key,
        "page": page,
        "kind": "field_purpose_prompt",
        "purposes": purposes,
        "anchors": anchors,
        "paths": paths,
        **{k: v for k, v in selector.items() if k in SELECTOR_KEYS},
    }


# Objectives-manual prose that states the purpose of a retained printed
# instrument field.  These rows carry no new anchor: the printed objective
# explains an instrument item that already carries its own anchor.
PURPOSE_SPECS: tuple[dict[str, Any], ...] = (
    _purpose(
        "p_c13_14",
        11,
        _span(
            "Cl3, 14   Such housing may be part of the benefits on one's regular job",
            "those who get free living quarters and those who work for their",
        ),
        ("in_kind_receipt",),
        ("c14#a",),
        P_C,
    ),
    _purpose(
        "p_c15",
        11,
        _span(
            "Cl5       Rent for a comparable house or apartment including whatever",
            "furnishings and utilities the landlord provides is what is",
        ),
        ("in_kind_receipt", "amount"),
        ("c15#a",),
        P_C,
    ),
    _purpose(
        "p_d1_role",
        16,
        _span(
            "The D, E, and F sequences apply to the head of the household even if",
            "section should be asked.",
        ),
        ("interview_and_role_attachment", "employment_status"),
        ("d1#a", "r_head_d1"),
    ),
    _purpose(
        "p_d2_3",
        17,
        _span(
            "02, 3.   Again, remember questions in the D-F sequence refer to the Head",
            "of ·the family.",
        ),
        ("interview_and_role_attachment", "occupation"),
        ("d2#a", "r_head_d1"),
        P_D,
    ),
    _purpose(
        "p_d3a",
        17,
        _span(
            "03a      The answers to this question are fitted into an industrial",
            "code and are sometimes vital in determining which code a",
        ),
        ("industry",),
        ("d3a#a",),
        P_D,
    ),
    _purpose(
        "p_d4",
        18,
        _mark(
            "D4         Be sure to ask this question; do not assume what the reply"
        ),
        ("employee_self_or_mixed",),
        ("d4#a",),
        P_D,
    ),
    _purpose(
        "p_d5",
        18,
        _span(
            "DS         The length of time with the present employer, not the time at his",
            "present position within the company, if they differ, is what is",
        ),
        ("job_tenure",),
        ("d5#a",),
        P_D,
    ),
    _purpose(
        "p_d7_8_9",
        18,
        _span(
            "D7, 8, 9   These three questions taken together are designed to get a",
            "on an overall basis. Appropriate sets of responses are:",
        ),
        ("rate",),
        ("d7#a",),
        P_D,
    ),
    _purpose(
        "p_d10_16",
        20,
        _span(
            "Quest ions 010-016 should give a complete accounting of the Head's",
            "52 weeks. If they don't, probe to find out why.",
        ),
        ("weeks_worked", "time_not_worked"),
        ("d10_11#a", "d12_13#a", "d14_15#a", "d16#a"),
        P_D,
    ),
    _purpose(
        "p_d17_19",
        20,
        _span(
            "017, 18,   Note that this question applies to the main job only. Overtime in",
            "that the figure in 019 is an annual amount.",
        ),
        ("hours_worked",),
        ("d17#a", "d18#a", "d19#a"),
        P_D,
    ),
    _purpose(
        "p_d20",
        20,
        _span(
            '020.       The reply to 020 should be "NO," if the Head\'s income is a fixed',
            "how many hours he works in a week. If he gets paid a fixed salary",
        ),
        ("rate",),
        ("d20#a",),
        P_D,
    ),
    _purpose(
        "p_d21_23",
        21,
        _span(
            "D21, 23.   Hourly rates for overtime work are usually higher (often 1 1/2 times)",
            "between the two rates appears to be out of line.",
        ),
        ("rate",),
        ("d21#a", "d23#a"),
        P_D,
    ),
    _purpose(
        "p_d22",
        21,
        _span(
            'D22.       In general, the reply to this question should be "YES" if the Head',
            'is paid on an hourly basis, but "NO" if he is paid on salary.',
        ),
        ("rate",),
        ("d22#a",),
        P_D,
    ),
    _purpose(
        "p_d24",
        23,
        _span(
            "D24.       This question refers to second jobs held simultaneously with the main",
            "job, not to main jobs held previous to the Head's current employment.",
        ),
        ("job_identifier",),
        ("d24#a", "j_extra", "j_main"),
        P_D,
    ),
    _purpose(
        "p_d27",
        23,
        _span(
            "D27.       If the ext ra work is such that it is difficult to estimate an hourly",
            "rate, for instance, real estate management, you need not probe--",
        ),
        ("rate",),
        ("d27#a",),
        P_D24,
    ),
    _purpose(
        "p_d28_29",
        23,
        _span(
            'D28, 29.   Responses may fit the question framework, e.g. "3 months, for 20 hours',
            "spent in 1970 on extra jobs .",
        ),
        ("weeks_worked", "hours_worked"),
        ("d28#a", "d29#a"),
        P_D24,
    ),
    _purpose(
        "p_e7",
        30,
        _mark(
            "E7.     Enter he r e the total number of weeks actually worked in 1970."
        ),
        ("weeks_worked",),
        ("e7#a",),
        P_E,
    ),
    _purpose(
        "p_e8",
        30,
        _span(
            "E8 .    If the Head's work schedule was irregular, be sure the total",
            "E7 and E8.",
        ),
        ("hours_worked",),
        ("e8#a", "e7#a"),
        P_E,
    ),
    _purpose(
        "p_e9",
        30,
        _span(
            "E9.     Include paid as well as unpaid sick leave. If the Head distinguishes",
            "his own sick time from time lost because others were sick, please note.",
        ),
        ("time_not_worked",),
        ("e9#a",),
        P_E,
    ),
    _purpose(
        "p_e10",
        30,
        _span(
            "ElO.    Check a t this point to see that the time does indeed add up to",
            "the full year. Probe for the reason why, if it doesn t.",
        ),
        ("time_not_worked",),
        ("e10#a",),
        P_E,
    ),
    _purpose(
        "p_f1",
        36,
        _span(
            "Fl.        For such Heads , work may have been irregular part-time work or",
            "We are interested in any money earning activity during 1970.",
        ),
        ("employment_status",),
        ("f1#a", "j_f_work"),
        P_F,
    ),
    _purpose(
        "p_f4_5",
        36,
        _span(
            "F4, 5.     We want to be able to calculate the total hours of work in 1970.",
            "these Heads it is not necessary to be able to account for all",
        ),
        ("weeks_worked", "hours_worked"),
        ("f4#a", "f5#a"),
        P_F,
    ),
    _purpose(
        "p_g_section",
        39,
        _span(
            "Since many of the questions in this section apply to things that",
            "in this section.",
        ),
        ("interview_and_role_attachment",),
        ("g_scope#a", "r_wife_g2"),
    ),
    _purpose(
        "p_h_intro",
        49,
        _span(
            "Family income is, of coun:e, this study's single most important",
            "get complete and accurate responses. If the respondent is reluctant",
        ),
        ("interview_and_role_attachment",),
        ("h8#a",),
    ),
    _purpose(
        "p_h1",
        49,
        _span(
            "Hl.   A farmer for our purposes is anyone whose main source of income is",
            'consider "rancher" and "farmer" synonymous terms.',
        ),
        ("farm_receipts",),
        ("h2#a",),
        P_FARM,
    ),
    _purpose(
        "p_h2",
        50,
        _span(
            "HZ .   The following are included here as receipt s f r om normal farming",
            "4) receipts from commodity credit loan s",
        ),
        ("farm_receipts",),
        ("h2#a",),
        P_FARM,
    ),
    _purpose(
        "p_h3",
        50,
        _span(
            "H3 .   Fa rm operating expenses may include:",
            "7) property taxes (but not Federal Income Taxes)",
        ),
        ("farm_operating_expenses",),
        ("h3#a",),
        P_FARM,
    ),
    _purpose(
        "p_h4",
        50,
        _span(
            "H4.    Simply defined, farm income equals total r ece i pts less operating",
            "e xpenses . Doing t he subtraction and then askin g H4 will enable",
        ),
        ("net_farm_income",),
        ("h4#a",),
        P_FARM,
    ),
    _purpose(
        "p_h5",
        50,
        _span(
            "HS.    The respondent need not be a businessman for this question to be",
            "enterprise.",
        ),
        ("receipt_indicator",),
        ("h5#a",),
    ),
    _purpose(
        "p_h6",
        50,
        _span(
            "H6.    If t he respondent does not seem to under s t and the question, check",
            'check "corporation" but note in the margin t ha t he just owns stock.',
        ),
        ("incorporation",),
        ("h6#a",),
    ),
    _purpose(
        "p_h7",
        51,
        _span(
            "H7.   The figure should include the total profits from the business in",
            "profits, write them both down, with identification. If the wife or",
        ),
        ("business_share",),
        ("h7#a",),
        P_H7,
    ),
    _purpose(
        "p_h8",
        51,
        _span(
            "H8.   This question applies only to the 1971 Head of the FU. For most",
            "wage earners this is the income reported on one's W2 form(s).",
        ),
        ("amount", "interview_and_role_attachment"),
        ("h8#a", "r_head_h8"),
    ),
    _purpose(
        "p_h9_10",
        53,
        _span(
            'H9, 10.   Note the phrase "In addition to this." If Head has already included',
            "there is no need to separate it.",
        ),
        ("receipt_indicator", "amount"),
        ("h9#a", "h10#a"),
    ),
    _purpose(
        "p_h11",
        53,
        _span(
            "Hll.       In answering Questions Hlla-llk it is very important to state",
            'their duration in 1970. So if R says "$400," ask if this is per',
        ),
        ("reporting_unit",),
        ("h11#a", "h11a#a", "h11b#a"),
    ),
    _purpose(
        "p_h11a",
        53,
        _span(
            "Hlla.       1) Income BEFORE TAXES but AFTER EXPENSES is what is wanted here.",
            "independent work in the evenings--and the latter is included",
        ),
        ("income_source", "amount"),
        ("h11a#a",),
    ),
    _purpose(
        "p_h17_20",
        58,
        _mark(
            "1. Make sure the wife ' s income from all sources is recorded."
        ),
        ("amount", "income_source"),
        ("h19a#a", "h19#a"),
        P_WIFE_DU,
    ),
    _purpose(
        "p_l_role",
        79,
        _mark("This section's questions apply to the Head of the FU."),
        ("interview_and_role_attachment",),
        ("r_head_l",),
        P_L,
    ),
    _purpose(
        "p_l5",
        79,
        _span(
            "15.       We are only interested in the number of occupations the Head of the",
            "currently .",
        ),
        ("job_identifier", "occupation"),
        ("l5#a", "j_first"),
        P_L,
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
        **{k: v for k, v in selector.items() if k in SELECTOR_KEYS},
    }


# Explicit printed repeat and cross-reference instructions.  Every retained
# instruction is dispositioned below by a resolved or unresolved alias row.
REPEAT_SPECS: tuple[dict[str, Any], ...] = (
    _ri(
        "ri_d25_26",
        23,
        _mark("D25, 26.   See D2, 3 ; the same instructions apply ."),
        P_D24,
    ),
    _ri(
        "ri_e1",
        30,
        _in(
            "is what is wanted here. See the objectives for D2-D3; they apply",
            "See the objectives for D2-D3; they apply",
        ),
        P_E,
    ),
    _ri(
        "ri_e6",
        30,
        _mark("E6.     See D2-3; the same objectives apply."),
        P_E,
    ),
    _ri(
        "ri_e6a",
        30,
        _mark("E6a .   See D3a ; the same obj ectives apply."),
        P_E,
    ),
    _ri(
        "ri_f3",
        36,
        _mark("F3.        See D2-3; the same objectives apply."),
        P_F,
    ),
    _ri(
        "ri_f3a",
        36,
        _mark("F3a.        See D3d; the same objectives apply."),
        P_F,
    ),
    _ri(
        "ri_g2_3_3a",
        39,
        _mark("G2, 3, 3a. See Section D, Questions D2-3,3a for objectives."),
    ),
    _ri(
        "ri_g4_5",
        39,
        _span(
            "G4,5.      See the objectives for E7, 8; they are the same as those for",
            "these two questions. If the wife has an irregular work schedule,",
        ),
    ),
    _ri(
        "ri_h1_nonfarm",
        49,
        _mark("Farm income for nonfarmers should be picked up in Hllb."),
    ),
    _ri(
        "ri_h7_wife",
        51,
        _span(
            "other member of the family is paid wages or a salary by the business,",
            "that should also be labeled and included here.",
        ),
    ),
    _ri(
        "ri_h8_second_job",
        51,
        _mark("should include income from a second job if the Head had one."),
    ),
    _ri(
        "ri_h8_businessmen",
        51,
        _span(
            "3) Businessmen: The wages and salaries that unincorporated",
            "should be recorded in Hl7. However, wages they get from",
        ),
    ),
    _ri(
        "ri_h11b_primary",
        53,
        _span(
            "Hllb.       1. FARMING OR MARKET GARDENING: If farming is R's primary",
            "duplicated her~ but if he receives most of his income",
        ),
    ),
    _ri(
        "ri_h11c_salary",
        53,
        _span(
            "corporated business, the salary he paid himself should be",
            "entered under H8. He may also have taken profits out of",
        ),
    ),
    _ri(
        "ri_h17_business",
        58,
        _span(
            "3. If some or all of the wife ' s income is from work in the family",
            'in business income" in the margin.',
        ),
        P_WIFE_DU,
    ),
    _ri(
        "ri_l4",
        79,
        _mark("14.       See D2-3; the same instructions apply."),
        P_L,
    ),
)

XREF = "explicit_cross_reference"
REPEATED = "explicit_repeat_instruction"
RESOLVED_HANDOFF = "local_resolved_cross_reference_for_global_assembly"

# Resolved alias evidence: both endpoints carry a retained local anchor.
RESOLVED_ALIAS_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (XREF, "ri_d25_26", "d25#a", "d2#a"),
    (XREF, "ri_e6", "e6#a", "d2#a"),
    (XREF, "ri_e6a", "e6a#a", "d3a#a"),
    (XREF, "ri_f3", "f3#a", "d2#a"),
    (XREF, "ri_g2_3_3a", "g3#a", "d2#a"),
    (XREF, "ri_g2_3_3a", "g3a#a", "d3a#a"),
    (XREF, "ri_g4_5", "g4#a", "e7#a"),
    (XREF, "ri_g4_5", "g5#a", "e8#a"),
    (XREF, "ri_h1_nonfarm", "h11b#a", "h2#a"),
    (XREF, "ri_h11b_primary", "h11b#a", "h2#a"),
    (XREF, "ri_h7_wife", "h19a#a", "h7#a"),
    (XREF, "ri_h17_business", "h19a#a", "h7#a"),
    (XREF, "ri_h8_second_job", "h8#a", "d27#a"),
    (XREF, "ri_h11c_salary", "h6#a", "h8#a"),
    (XREF, "ri_l4", "l4#a", "d2#a"),
)

SERIES = "local_series_target_unresolved_for_global_assembly"
MISPRINT = "printed_target_identifier_unresolved_for_global_assembly"

# Unresolved alias evidence: the printed target is a whole question series or
# a printed identifier this shard will not silently repair.  It is preserved
# verbatim for global assembly and never silently bound inside the shard.
UNRESOLVED_ALIAS_SPECS: tuple[dict[str, Any], ...] = (
    {
        "relation": XREF,
        "instruction": "ri_e1",
        "page": 30,
        "target": "D2-D3",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_f3a",
        "page": 36,
        "target": "D3d",
        "handoff": MISPRINT,
    },
    {
        "relation": XREF,
        "instruction": "ri_h8_businessmen",
        "page": 51,
        "target": "Hl7",
        "handoff": MISPRINT,
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
            key: value for key, value in spec.items() if key in SELECTOR_KEYS
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


ITEM_ANCHOR_SPECS, ITEM_PROMPT_SPECS = _expand_items()
PROMPT_SPECS: tuple[dict[str, Any], ...] = (
    *ITEM_PROMPT_SPECS,
    *PURPOSE_SPECS,
)
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
    """Order every occurrence, then resolve branches, then resolve paths.

    fam1971_QxQs prints each instrument page immediately before the
    objectives page that states its controlling condition, so a lawful
    branch label can follow the items it gates in source order.  Indices
    therefore come from one complete same-page ordering pass; branch rows
    are built next in source-occurrence order (a parent must still be an
    earlier branch); path-bearing occurrences resolve last.
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

    plan: list[tuple[dict[str, Any], int, int]] = []
    page_indices: Counter[int] = Counter()
    for group in sorted(items_by_group):
        group_items = items_by_group[group]
        kind = group_items[0]["kind"]
        if len(group_items) != 1:
            if kind != "flow_branch_label":
                raise ValueError("duplicate non-flow atomic occurrence")
            raise ValueError(
                "multi-parent flow label ordering is unresolved in this shard"
            )
        for ordinal, item in enumerate(group_items):
            semantic_ordinal = ordinal if len(group_items) > 1 else 0
            index_on_page = page_indices[item["page"]]
            page_indices[item["page"]] += 1
            plan.append((item, index_on_page, semantic_ordinal))

    branches: list[dict[str, Any]] = []
    branch_by_key: dict[str, dict[str, Any]] = {}
    row_by_key: dict[str, dict[str, Any]] = {}
    atom_coordinates: set[tuple[Any, ...]] = set()

    def _record(
        item: Mapping[str, Any],
        index_on_page: int,
        semantic_ordinal: int,
        flow_paths: list[list[str]],
    ) -> dict[str, Any]:
        row = _occurrence_row(
            item, locator_id, index_on_page, semantic_ordinal, flow_paths
        )
        coordinate = (
            item["page"],
            item["utf8_byte_start"],
            item["utf8_byte_end"],
            item["kind"],
            semantic_ordinal,
        )
        if coordinate in atom_coordinates:
            raise ValueError("duplicate occurrence coordinate")
        atom_coordinates.add(coordinate)
        row_by_key[item["key"]] = row
        return row

    for item, index_on_page, semantic_ordinal in plan:
        if item["kind"] != "flow_branch_label":
            continue
        parent_key = item.get("parent")
        if parent_key is None:
            parent_path = [FLOW_ROOT]
        else:
            if parent_key not in branch_by_key:
                raise ValueError(
                    f"later or unresolved flow parent {parent_key}"
                )
            parent_path = branch_by_key[parent_key]["branch_path"]
        row = _record(
            item, index_on_page, semantic_ordinal, [list(parent_path)]
        )
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
            "occurrence_index_on_page": index_on_page,
            "branch_label": item["matched_text"],
            "branch_label_sha256": item["matched_utf8_sha256"],
        }
        branches.append(branch)
        branch_by_key[item["key"]] = branch

    for item, index_on_page, semantic_ordinal in plan:
        if item["kind"] == "flow_branch_label":
            continue
        paths: list[list[str]] = []
        for path_keys in item["paths"]:
            if path_keys[0] != "root":
                raise ValueError("flow path must start at the root")
            resolved = [FLOW_ROOT]
            for path_key in path_keys[1:]:
                if path_key not in branch_by_key:
                    raise ValueError(
                        f"unresolved occurrence flow path {path_key}"
                    )
                resolved = branch_by_key[path_key]["branch_path"]
            paths.append(resolved)
        if len({tuple(path) for path in paths}) != len(paths):
            raise ValueError("duplicate occurrence flow path")
        _record(
            item,
            index_on_page,
            semantic_ordinal,
            sorted(paths, key=_path_sort_key),
        )

    occurrences = [row_by_key[item["key"]] for item, _, _ in plan]
    occurrence_id_by_key = {
        key: row["questionnaire_occurrence_id"]
        for key, row in row_by_key.items()
    }
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


CANDIDATE_DENOMINATOR = 3030


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-7 source and sealing invariant."""

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
        raise ValueError("document-7 candidate denominator drift")
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-7 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 7: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
