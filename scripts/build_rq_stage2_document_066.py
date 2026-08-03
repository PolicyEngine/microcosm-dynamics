#!/usr/bin/env python3
"""Build and validate the sealed stage-2 annotation for fam2005_QxQs.pdf.

The stage-1 detector output is provenance only.  The review specification
below names source text selected during a complete 97-page review; spans,
hashes, paths, and IDs are re-derived from the authenticated PDF bytes before
the candidate artifact is opened for adjudication.

fam2005_QxQs.pdf is the 2005 question-by-question objectives manual: printed
interviewer instructions keyed to questionnaire item identifiers rather than a
printed questionnaire.  In this wave the former Sections B and C are
consolidated into BC and the former Sections D and E into DE, so employment
items carry one printed identifier (``BC/DE20``) covering both the Head and
the Wife/"Wife" series; section 19 gives R_Q no role coordinate, so the shard
records the printed compound verbatim and leaves role resolution to global
assembly.

The retention test applied throughout is whether the printed text
*establishes* a document-local R_Q fact for a named item or item series -- a
role attachment, a job slot, a remuneration component, an aggregate, a
retained contextual field, a field purpose, a controlling condition, or an
explicit repeat/cross-reference.  Three consequences are worth stating,
because this document is dominated by text that fails the test:

* Non-labour income is rejected.  Transfer and asset receipts (Social
  Security, SSI, TANF/ADC, veterans and employer pensions *as income*,
  unemployment and workers compensation, child support, alimony, help from
  relatives, rent, dividends, interest, trust funds) are printed at length in
  Sections G and R but establish no remuneration component of any job.
* Wealth stocks are rejected.  Section W's farm and business questions ask
  for asset *values*, not for work income, so they are not farm or business
  aggregates.
* Work-like lexemes outside the employment subject matter are rejected:
  Section A's rent-free-quarters occupations, Section F's business vehicle
  use, Section H's work-limiting health conditions and Railroad Retirement
  Board claim number, Section J and KL third-party (father's) occupations,
  Section M's explicitly unpaid volunteering, and the Respondent Payment
  section's "Home, work, or Cell?" phone type.

A field-purpose prompt is retained only where the printed purpose maps into
the section 19 field-purpose vocabulary below; printed job attributes with no
such purpose (employer headcount at BC/DE25a, union coverage at BC/DE26-27,
required computer use at BC/DE28) are recorded as rejections rather than
forced into an ill-fitting purpose.

Much of this manual reprints 1997 text verbatim.  Every retained span was
compared against the sealed fam1997_QxQs shard, and where the printed text is
shared its disposition follows that shard, so the two shards concatenate
without spurious asymmetry: the younger-OFUM odd-jobs objective is rejected as
a probing example inside a general any-income series; the three BC/DE22
continuation sentences (farm and ranch workers, incorporated family farms,
separate private practices) are folded into the BC/DE22 context item as
self-employment coding examples rather than emitted as aggregates or job
slots; BC/DE31 is a context anchor because it states a property of the pay
arrangement rather than a payment; and the BC/DE41 "altogether" continuation
is folded into its own item rather than emitted as a separate repeat
instruction.
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
DOCUMENT_POSITION = 66
DOCUMENT_ID = (
    "psid-source-document:"
    "df4a9be59d38749dbf5d663616e6e6bff86ff340d4d53e21a5b9a6b16f687b9d"
)
INTERVIEW_WAVE = 2005
CANONICAL_SOURCE_PATH = "documentation/capture1/fam2005_QxQs.pdf"
PDF_FILENAME = "fam2005_QxQs.pdf"
PDF_SIZE = 391_820
PDF_SHA256 = "6359949ba113373570292372b656e9be577ee1cc1fa25f402e86e00e059f16be"
PAGE_COUNT = 97
EMPTY_TEXT_PAGES: tuple[int, ...] = ()

REPLAY_PATH = ROOT / "docs/analysis/rq_stage1_evidence/source_replay_v1.json"
INDEX_PATH = ROOT / "docs/analysis/rq_stage1_candidates/index_v1.json"
CANDIDATE_PATH = (
    ROOT
    / "docs/analysis/rq_stage1_candidates/batch_07_documents_061_070"
    / "document_066_fam2005_QxQs_candidates_v1.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs/analysis/rq_stage2_annotations"
    / "document_066_fam2005_QxQs_annotation_v1.json"
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
    "79735e707e001282e49e71afa07fb11f2c2afce8b4fde5dd7e9951faf508eabe"
)
CANDIDATE_CONTENT_SHA256 = (
    "8b9aa8e3cab6523f8342c1e75d48cf302d1da6532d94044114ac7eb493218abf"
)
CANDIDATE_PAYLOAD_SHA256 = (
    "2fed17870c5e055b176bdd4df6e104d468e8eb58be7deb97cd9f2a5fc4998178"
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
        raise ValueError("document-66 candidate index selection drift")

    candidate_raw = CANDIDATE_PATH.read_bytes()
    if _sha256(candidate_raw) != CANDIDATE_RAW_SHA256:
        raise ValueError("document-66 candidate raw identity drift")
    candidate = _strict_load(CANDIDATE_PATH, "document-66 candidates")
    candidates.validate_document_candidates(candidate, replay)
    if (
        candidate["integrity"]["content_sha256"] != CANDIDATE_CONTENT_SHA256
        or candidate["candidate_manifest"]["candidate_payload_sha256"]
        != CANDIDATE_PAYLOAD_SHA256
    ):
        raise ValueError("document-66 candidate content identity drift")
    return candidate


def _derive_pages(capture_root: Path) -> list[str]:
    pdf_path = capture_root / PDF_FILENAME
    raw = pdf_path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam2005_QxQs.pdf whole-file identity drift")
    pages = questionnaire_inventory._pdftotext_pages(pdf_path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("fam2005_QxQs.pdf page-count drift")
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
        raise ValueError("document-66 replay page cover drift")
    for row, page_text in zip(rows, page_texts, strict=True):
        page_bytes = page_text.encode("utf-8")
        if row["page_text_utf8_size_bytes"] != len(page_bytes) or row[
            "page_text_utf8_sha256"
        ] != _sha256(page_bytes):
            raise ValueError("document-66 replay page text drift")
    if (
        tuple(index + 1 for index, text in enumerate(page_texts) if not text)
        != EMPTY_TEXT_PAGES
    ):
        raise ValueError("document-66 empty-text page domain drift")
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
# read during the complete 97-page pass and is re-resolved against the
# authenticated fam2005_QxQs.pdf bytes.
# ---------------------------------------------------------------------------

# Controlling flow.  A branch is retained only where printed text states a
# condition that determines whether a retained R_Q item series is asked.
# Advisory conditionals inside a single item ("if R cannot separate the
# amounts, estimate") are rejected as noncontrolling flow text.
FLOW_SPECS: tuple[dict[str, Any], ...] = (
    _line(
        "f_bcde",
        15,
        "Regardless of whom your Respondent is, Section BC is asked about the",
    ),
    _line(
        "f_bcde13",
        15,
        "It is crucial that you get an accurate reply to BC/DE1-3",
        parent="f_bcde",
    ),
    _line(
        "f_g_workincome",
        29,
        "reports work income in Section G, hours for that work must",
    ),
    _line(
        "f_g_workhours",
        29,
        "reports working during 2004 in the employment sections,",
    ),
    _line(
        "f_g17_supp",
        31,
        "If there are no work hours reported in Section BC for income",
    ),
    _line(
        "f_g52_supp",
        37,
        "Again, if income is reported but no work hours were recorded",
    ),
    _line(
        "f_g75_ofum",
        40,
        "questions G75–G90 are asked of OFUMS age 16",
    ),
    _line(
        "f_p_head",
        51,
        "Only Heads who are currently employed at a job (Section BC)",
    ),
    _line(
        "f_p_head_former",
        51,
        "Heads who are not currently working, but have worked in the past",
    ),
    _line(
        "f_p_head_never",
        51,
        "If the Head has never worked, the application skips",
    ),
    _line(
        "f_p_wife_scope",
        56,
        "The application checks for a Wife/“Wife” in the FU and her",
    ),
    _line(
        "f_p_wife",
        56,
        "Only Wifes/”Wifes” who are currently employed at a job",
        parent="f_p_wife_scope",
    ),
    _line(
        "f_p_wife_former",
        56,
        "Wifes/”Wife’s” who are not currently working, but have worked",
        parent="f_p_wife_scope",
    ),
    _line(
        "f_kl_new",
        73,
        "If the FU has a new Head or new Wife /“Wife”, the application",
    ),
    _line(
        "f_r2_wife",
        81,
        "If she was employed in 2003 the series will start with R2-R3",
    ),
    _line(
        "f_r9_ofum",
        81,
        "This series is for any OFUM age 16 or older in the 2003 FU",
    ),
    _line(
        "f_io18",
        95,
        "Did you find out about someone’s job too late in the interview",
    ),
    _line(
        "f_io19",
        96,
        "Was a job reported for any FU member for which you later learned",
    ),
)

ROOT_PATH = ("root",)
P_ROOT = (("root",),)
P_BCDE = (("root", "f_bcde"),)
P_BCJOB = (("root", "f_bcde", "f_bcde13"),)
P_G75 = (("root", "f_g75_ofum"),)
P_PHEAD = (("root", "f_p_head"),)
P_PHEADFMR = (("root", "f_p_head_former"),)
P_PWIFE = (("root", "f_p_wife_scope", "f_p_wife"),)
P_PWIFEFMR = (("root", "f_p_wife_scope", "f_p_wife_former"),)
P_KL = (("root", "f_kl_new"),)
P_IO18 = (("root", "f_io18"),)
P_IO19 = (("root", "f_io19"),)


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
    # --- Sections BC and DE -------------------------------------------------
    _anchor(
        "r_bc_head",
        15,
        "role_anchor",
        _in("Regardless of whom your Respondent is", "Head"),
        classification=HEAD,
        paths=P_BCDE,
    ),
    _anchor(
        "r_de_wife",
        15,
        "role_anchor",
        _in("FU, while Section DE is asked about the", "Wife /“Wife”"),
        classification=SPOUSE,
        paths=P_BCDE,
    ),
    _anchor(
        "j_bc_employer",
        15,
        "job_anchor",
        _in("1 WORKING NOW H/W has an employer", "an employer"),
        identifier="1 WORKING NOW",
        paths=P_BCDE,
    ),
    _anchor(
        "j_bc_returnjob",
        15,
        "job_anchor",
        _in("and expects to return to her/his job", "her/his job"),
        identifier="2 ONLY TEMPORARILY LAID OFF",
        paths=P_BCDE,
    ),
    _anchor(
        "j_bcde4_job",
        16,
        "job_anchor",
        _in("BC/DE4-7. You will be asking employer’s names", "every job"),
        identifier="BC/DE4-7.",
        paths=P_BCJOB,
    ),
    _anchor(
        "j_bc_jobdef",
        16,
        "job_anchor",
        _in("in order for an activity to be considered", "“a job”"),
        paths=P_BCJOB,
    ),
    _anchor(
        "j_bcde20_job",
        17,
        "job_anchor",
        _in("H/W’s job and job duties/activities.", "H/W’s job"),
        identifier="BC/DE20.",
        paths=P_BCJOB,
    ),
    _anchor(
        "a_bcde23_business",
        20,
        "business_aggregate_anchor",
        _in("“business” and don’t believe BC/DE23", "“business”"),
        identifier="BC/DE23.",
        paths=P_BCJOB,
    ),
    _anchor(
        "j_bcde41_employer",
        21,
        "job_anchor",
        _in("By employer, we mean company, firm", "employer"),
        identifier="BC/DE41.",
        paths=P_BCJOB,
    ),
    _anchor(
        "j_bcde51_thatjob",
        21,
        "job_anchor",
        _in("We are simply looking for the reason", "that job"),
        identifier="BC/DE51.",
        paths=P_BCJOB,
    ),
    _anchor(
        "j_bcde64_another",
        21,
        "job_anchor",
        _in("“Another job” can mean a different position", "“Another job”"),
        identifier="BC/DE64.",
        paths=P_BCJOB,
    ),
    # --- Section G ----------------------------------------------------------
    _anchor(
        "r_g_head",
        29,
        "role_anchor",
        _in("reports work income in Section G", "Head"),
        classification=HEAD,
    ),
    _anchor(
        "r_g_wife",
        29,
        "role_anchor",
        _in("reports work income in Section G", "Wife /“Wife”"),
        classification=SPOUSE,
    ),
    _anchor(
        "a_g2_farm",
        29,
        "farm_aggregate_anchor",
        _in("Receipts from normal farm operations", "normal farm operations"),
        identifier="G2.",
    ),
    _anchor(
        "a_g3_farm",
        29,
        "farm_aggregate_anchor",
        _in("Farm operating expenses can include", "Farm operating expenses"),
        identifier="G3.",
    ),
    _anchor(
        "a_g4_farm",
        30,
        "farm_aggregate_anchor",
        _in("Farm income equals total receipts", "Farm income"),
        identifier="G4.",
    ),
    _anchor(
        "a_g5_business",
        30,
        "business_aggregate_anchor",
        _in("business is and specify who in the family owned it", "business"),
        identifier="G5–7a.",
    ),
    _anchor(
        "a_g10_business",
        30,
        "business_aggregate_anchor",
        _in("owned a business in 2004, but R doesn’t know", "a business"),
        identifier="G10.",
    ),
    _anchor(
        "r_g13_head",
        31,
        "role_anchor",
        _in("This question applies only to current Head", "Head"),
        classification=HEAD,
    ),
    _anchor(
        "rt_g13_alljobs",
        31,
        "role_total_anchor",
        _in("from all 2004 wages.", "all 2004 wages"),
        identifier="G13.",
    ),
    _anchor(
        "rt_g13_total",
        31,
        "role_total_anchor",
        _in("remind her/him of the several jobs", "total income"),
    ),
    _anchor(
        "a_g18a_prof",
        31,
        "business_aggregate_anchor",
        _in("PROFESSIONAL PRACTICE: Includes", "PROFESSIONAL PRACTICE"),
        identifier="G18a.",
    ),
    _anchor(
        "a_g18a_trade",
        32,
        "business_aggregate_anchor",
        _in("TRADE: Includes self-employed tradesmen", "TRADE"),
    ),
    _anchor(
        "a_g18b_farm",
        32,
        "farm_aggregate_anchor",
        _in(
            "FARMING OR MARKET GARDENING",
            "FARMING OR MARKET GARDENING",
        ),
        identifier="G18b.",
    ),
    _anchor(
        "a_g18c_boarders",
        32,
        "business_aggregate_anchor",
        _in("ROOMERS OR BOARDERS (Extremely Rare)", "ROOMERS OR BOARDERS"),
        identifier="G18c.",
    ),
    _anchor(
        "j_g22_mainjob",
        32,
        "job_anchor",
        _in(
            "hours on jobs other than the current main job",
            "the current main job",
        ),
        identifier="G22–24.",
    ),
    _anchor(
        "r_g51_wife",
        37,
        "role_anchor",
        _in("income from all work sources is recorded", "Wife/“Wife’s”"),
        classification=SPOUSE,
    ),
    _anchor(
        "rt_g51_allwork",
        37,
        "role_total_anchor",
        _in(
            "income from all work sources is recorded",
            "income from all work sources",
        ),
        identifier="G51a-G52a.",
    ),
    _anchor(
        "a_g51_business",
        37,
        "business_aggregate_anchor",
        _in("income is from work in a business of which", "a business"),
    ),
    _anchor(
        "j_g_ofumjobs",
        40,
        "job_anchor",
        _in(
            "The questions cover jobs held by the Ofum",
            "jobs held by the Ofum",
        ),
        paths=P_G75,
    ),
    _anchor(
        "j_g76_eachjob",
        40,
        "job_anchor",
        _in("can about each job in 2004", "each job"),
        identifier="G76–82.",
        paths=P_G75,
    ),
    _anchor(
        "j_g81_thatjob",
        40,
        "job_anchor",
        _in("the total number of hours worked in 2004", "that job"),
        identifier="G81.",
        paths=P_G75,
    ),
    # --- Section P ----------------------------------------------------------
    _anchor(
        "j_p1_current",
        51,
        "job_anchor",
        _in(
            "Head’s Pension from a Current Employer (P1–44)",
            "Current Employer",
        ),
        identifier="P1–44",
    ),
    _anchor(
        "j_p45_former",
        51,
        "job_anchor",
        _in(
            "Head’s Pension from a Former Employer (P45-69)", "Former Employer"
        ),
        identifier="P45-69",
    ),
    _anchor(
        "j_p71_current",
        51,
        "job_anchor",
        _in(
            "Wife/“Wife’s” Pension from a Current Employer (P71–114)",
            "Current Employer",
        ),
        identifier="P71–114",
    ),
    _anchor(
        "j_p115_former",
        51,
        "job_anchor",
        _in(
            "Wife/“Wife’s” Pension from a Former Employer (P115–139)",
            "Former Employer",
        ),
        identifier="P115–139",
    ),
    _anchor(
        "r_p1_head",
        51,
        "role_anchor",
        _in("Only Heads who are currently employed at a job", "Heads"),
        classification=HEAD,
        identifier="P1.",
        paths=P_PHEAD,
    ),
    _anchor(
        "j_p1_jobemployer",
        51,
        "job_anchor",
        _in(
            "pension plan at his/her current job employer.",
            "current job employer",
        ),
        paths=P_PHEAD,
    ),
    _anchor(
        "j_p45_fmremp",
        54,
        "job_anchor",
        _in(
            "Here we ask about pensions from a former employer",
            "a former employer",
        ),
        identifier="P45–P69.",
        paths=P_PHEADFMR,
    ),
    _anchor(
        "r_p71_wife",
        56,
        "role_anchor",
        _in("Only Wifes/”Wifes” who are currently employed", "Wifes/”Wifes”"),
        classification=SPOUSE,
        identifier="P71.",
        paths=P_PWIFE,
    ),
    _anchor(
        "j_p71_jobemployer",
        56,
        "job_anchor",
        _in(
            "a pension plan at her current job employer.",
            "current job employer",
        ),
        paths=P_PWIFE,
    ),
    _anchor(
        "j_p115_fmremp",
        58,
        "job_anchor",
        _in(
            "Here we ask about pensions from a former employer",
            "a former employer",
        ),
        identifier="P115–P139.",
        paths=P_PWIFEFMR,
    ),
    # --- Section KL ---------------------------------------------------------
    _anchor(
        "r_k63_hw",
        75,
        "role_anchor",
        _in(
            "For instance, if the Head/Wife /“Wife” worked two months", "Head"
        ),
        classification=HEAD,
        paths=P_KL,
    ),
    _anchor(
        "r_k63_wife",
        75,
        "role_anchor",
        _in(
            "For instance, if the Head/Wife /“Wife” worked two months",
            "Wife /“Wife”",
        ),
        classification=SPOUSE,
        paths=P_KL,
    ),
    _anchor(
        "r_l74_head",
        75,
        "role_anchor",
        _in("We are interested in the similarity of occupations", "Head"),
        classification=HEAD,
        identifier="L74.",
        paths=P_KL,
    ),
    _anchor(
        "j_l74_diversejobs",
        75,
        "job_anchor",
        _in("etc.) or held a number of diverse jobs", "diverse jobs"),
        paths=P_KL,
    ),
    # --- Section R ----------------------------------------------------------
    _anchor(
        "r_r2_head",
        81,
        "role_anchor",
        _in(
            "We mean the total earnings from all jobs Head had in 2003", "Head"
        ),
        classification=HEAD,
        identifier="R2.",
    ),
    _anchor(
        "rt_r2_total",
        81,
        "role_total_anchor",
        _in(
            "We mean the total earnings from all jobs Head had in 2003",
            "the total earnings from all jobs Head had in 2003",
        ),
        identifier="R2.",
    ),
    _anchor(
        "j_r2_alljobs",
        81,
        "job_anchor",
        _in(
            "We mean the total earnings from all jobs Head had in 2003",
            "all jobs",
        ),
    ),
    _anchor(
        "a_r2_business",
        81,
        "business_aggregate_anchor",
        _in("bonus, commissions, profit from business", "business"),
    ),
    _anchor(
        "r_r2_wife",
        81,
        "role_anchor",
        _in(
            "If there is a Wife or “Wife” in the FU this set", "Wife or “Wife”"
        ),
        classification=SPOUSE,
        identifier="R2-R6.",
    ),
    # --- Interviewer Observations ------------------------------------------
    _anchor(
        "j_io18a_job",
        96,
        "job_anchor",
        _in("each FU member’s unreported job.", "unreported job"),
        identifier="IO18a.",
        paths=P_IO18,
    ),
    _anchor(
        "j_io19a_thatjob",
        96,
        "job_anchor",
        _in("Please specify who and which job", "that job"),
        identifier="IO19a.",
        paths=P_IO19,
    ),
    _anchor(
        "a_io19_business",
        96,
        "business_aggregate_anchor",
        _in(
            "report that they work in a spouse’s business",
            "a spouse’s business",
        ),
        paths=P_IO19,
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
    # --- Sections BC and DE: entry and employment status --------------------
    _item(
        "bcde1_3",
        15,
        "It is crucial that you get an accurate reply to BC/DE1-3",
        CTX,
        ("interview_and_role_attachment",),
        "BC/DE1–3.",
        (),
        P_BCDE,
    ),
    _item(
        "bc_code1",
        15,
        "1 WORKING NOW H/W has an employer",
        CTX,
        ("interview_and_role_attachment", "employee_self_or_mixed"),
        "1 WORKING NOW",
        ("j_bc_employer",),
        P_BCDE,
    ),
    _item(
        "bc_code2",
        15,
        "2 ONLY TEMPORARILY LAID OFF H/W is employed",
        CTX,
        ("interview_and_role_attachment",),
        "2 ONLY TEMPORARILY LAID OFF",
        ("j_bc_returnjob",),
        P_BCDE,
    ),
    _item(
        "bc_code3",
        15,
        "3 LOOKING FOR WORK, UNEMPLOYED H/W is not working now",
        CTX,
        ("interview_and_role_attachment",),
        "3 LOOKING FOR WORK, UNEMPLOYED",
        (),
        P_BCDE,
    ),
    _item(
        "bc_code4",
        15,
        "4 NOT WORKING/NOT LOOKING",
        CTX,
        ("interview_and_role_attachment",),
        "4 NOT WORKING/NOT LOOKING",
        (),
        P_BCDE,
    ),
    _item(
        "bc_code5",
        15,
        "5 DISABLED, PERMANENTLY OR TEMPORARILY",
        CTX,
        ("interview_and_role_attachment",),
        "5 DISABLED, PERMANENTLY OR TEMPORARILY",
        (),
        P_BCDE,
    ),
    _item(
        "bc_code6",
        15,
        "6 KEEPING HOUSE",
        CTX,
        ("interview_and_role_attachment",),
        "6 KEEPING HOUSE",
        (),
        P_BCDE,
    ),
    _item(
        "bc_code7",
        15,
        "7 STUDENT R may mention these codes",
        CTX,
        ("interview_and_role_attachment",),
        "7 STUDENT",
        (),
        P_BCDE,
    ),
    # --- Current main job, occupation, industry, self-employment ------------
    _item(
        "bcde4_7",
        16,
        "BC/DE4-7. You will be asking employer’s names",
        CTX,
        ("job_identifier",),
        "BC/DE4-7.",
        ("j_bcde4_job",),
        P_BCJOB,
    ),
    _item(
        "bc_jobdef",
        16,
        "in order for an activity to be considered",
        CTX,
        ("job_identifier",),
        None,
        ("j_bc_jobdef",),
        P_BCJOB,
    ),
    _item(
        "bcde20",
        17,
        "OCCUPATION: Follow the guidelines below",
        CTX,
        ("occupation",),
        "BC/DE20.",
        ("j_bcde20_job",),
        P_BCJOB,
    ),
    _item(
        "bcde21",
        18,
        "INDUSTRY: The type of business or industry",
        CTX,
        ("industry",),
        "BC/DE21.",
        (),
        P_BCJOB,
    ),
    _item(
        "bc_govlevel",
        18,
        "3. If employed by the government, specify the department",
        CTX,
        ("government_level", "industry"),
        None,
        (),
        P_BCJOB,
    ),
    _item(
        "bc_military",
        18,
        "6) When H/W works for a branch of the military",
        CTX,
        ("industry", "federal_service"),
        None,
        (),
        P_BCJOB,
    ),
    _item(
        "bcde22",
        19,
        "Be careful with the following situations and record",
        CTX,
        ("employee_self_or_mixed",),
        "BC/DE22.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde23",
        20,
        "Many self-employed people and professionals do not consider",
        CTX,
        ("incorporation",),
        "BC/DE23.",
        ("a_bcde23_business",),
        P_BCJOB,
    ),
    # --- Current pay and overtime -------------------------------------------
    _item(
        "bcde29_39",
        20,
        "Questions BC/DE29, 30, 33, 36, 37, 38 refer to H/W’s regular pay",
        REM,
        ("amount", "reporting_unit"),
        "BC/DE29–39.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde29",
        20,
        "The OTHER category is for everything that is not salary",
        REM,
        ("amount",),
        "BC/DE29.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde31",
        20,
        "This should be NO if H/W’s income is a fixed",
        CTX,
        ("amount", "reporting_unit"),
        "BC/DE31.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde32_34",
        20,
        "Select all that R mentions. Use code 5 – EXACT AMOUNT",
        REM,
        ("amount",),
        "BC/DE32, 34.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde38",
        21,
        "OTHER ways H/W is paid for regular work time",
        REM,
        ("amount",),
        "BC/DE38.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde39",
        21,
        "We know that this question may be difficult",
        REM,
        ("amount",),
        "BC/DE39.",
        (),
        P_BCJOB,
    ),
    _item(
        "bcde41",
        21,
        "By employer, we mean company, firm",
        CTX,
        ("job_identifier", "month_or_exposure"),
        "BC/DE41.",
        ("j_bcde41_employer",),
        P_BCJOB,
    ),
    _item(
        "bcde51",
        21,
        "We are simply looking for the reason",
        CTX,
        ("job_identifier",),
        "BC/DE51.",
        ("j_bcde51_thatjob",),
        P_BCJOB,
    ),
    _item(
        "bcde64",
        21,
        "“Another job” can mean a different position",
        CTX,
        ("job_identifier",),
        "BC/DE64.",
        ("j_bcde64_another",),
        P_BCJOB,
    ),
    # --- Section F: income-producing housework routed to BC/DE --------------
    _item(
        "f2_3",
        23,
        "If roomers or boarders are living in the HU, time spent",
        CTX,
        ("assignment", "month_or_exposure"),
        "F2–3.",
        (),
        P_ROOT,
    ),
    # --- Section G: work-linked income --------------------------------------
    _item(
        "g_wages_gross",
        29,
        "All wages and salaries listed in Section G should be before taxes",
        REM,
        ("amount",),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "g1a",
        29,
        "You will know from Sections BC or DE whether H/W’s current",
        CTX,
        ("occupation",),
        "G1a.",
        (),
        P_ROOT,
    ),
    _item(
        "g2",
        29,
        "Receipts from normal farm operations",
        REM,
        ("amount",),
        "G2.",
        ("a_g2_farm",),
        P_ROOT,
    ),
    _item(
        "g3",
        29,
        "Farm operating expenses can include",
        REM,
        ("amount",),
        "G3.",
        ("a_g3_farm",),
        P_ROOT,
    ),
    _item(
        "g4",
        30,
        "Farm income equals total receipts",
        REM,
        ("amount",),
        "G4.",
        ("a_g4_farm",),
        P_ROOT,
    ),
    _item(
        "g_matchhours",
        30,
        "We must have work hours for all income reported in Section G",
        CTX,
        ("amount", "month_or_exposure"),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "g5_7a",
        30,
        "Do NOT include investment stock ownership in G5",
        CTX,
        ("assignment",),
        "G5–7a.",
        ("a_g5_business",),
        P_ROOT,
    ),
    _item(
        "g8",
        30,
        "Remember that “family” refers to members of this FU only",
        CTX,
        ("assignment",),
        "G8.",
        ("a_g5_business",),
        P_ROOT,
    ),
    _item(
        "g9a_g9b",
        30,
        "These questions are crucial. If the Head put in work time",
        CTX,
        ("assignment", "month_or_exposure"),
        "G9a/G9b.",
        ("a_g5_business",),
        P_ROOT,
    ),
    _item(
        "g10",
        30,
        "If R doesn’t understand the question, select DON’T KNOW",
        CTX,
        ("incorporation",),
        "G10.",
        ("a_g10_business",),
        P_ROOT,
    ),
    _item(
        "g11b",
        30,
        "The amount given here is net profit",
        REM,
        ("amount",),
        "G11b.",
        ("a_g5_business",),
        P_ROOT,
    ),
    _item(
        "g11b_wages",
        30,
        "If the Wife/“Wife” or other FU member is not a part owner",
        REM,
        ("amount", "assignment"),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "g12",
        31,
        "If Head was working in 2004, this question almost certainly",
        CTX,
        ("month_or_exposure",),
        "G12.",
        (),
        P_ROOT,
    ),
    _item(
        "g13",
        31,
        "This question applies only to current Head",
        REM,
        ("amount",),
        "G13.",
        ("rt_g13_alljobs",),
        P_ROOT,
    ),
    _item(
        "g14",
        31,
        "Note the phrase “in addition to this.”",
        REM,
        ("amount",),
        "G14.",
        (),
        P_ROOT,
    ),
    _item(
        "g16",
        31,
        "If earnings are solely from bonuses, overtime, tips",
        REM,
        ("amount",),
        "G16.",
        (),
        P_ROOT,
    ),
    _item(
        "g17f_g23",
        31,
        "If there are no work hours reported in Section BC for income",
        CTX,
        ("month_or_exposure",),
        "G17f–G23.",
        (),
        P_ROOT,
    ),
    _item(
        "g18a",
        31,
        "PROFESSIONAL PRACTICE: Includes",
        REM,
        ("amount", "occupation"),
        "G18a.",
        ("a_g18a_prof",),
        P_ROOT,
    ),
    _item(
        "g18a_trade",
        32,
        "TRADE: Includes self-employed tradesmen",
        REM,
        ("amount", "occupation"),
        None,
        ("a_g18a_trade",),
        P_ROOT,
    ),
    _item(
        "g18b",
        32,
        "FARMING OR MARKET GARDENING",
        REM,
        ("amount", "occupation"),
        "G18b.",
        ("a_g18b_farm",),
        P_ROOT,
    ),
    _item(
        "g18c",
        32,
        "ROOMERS OR BOARDERS (Extremely Rare)",
        REM,
        ("amount",),
        "G18c.",
        ("a_g18c_boarders",),
        P_ROOT,
    ),
    _item(
        "g19",
        32,
        "It is very important to select the appropriate time unit",
        CTX,
        ("reporting_unit",),
        "G19a,b,c.",
        (),
        P_ROOT,
    ),
    _item(
        "g20",
        32,
        "We want to know during which months of 2004 this income",
        CTX,
        ("month_or_exposure",),
        "G20a,b,c.",
        (),
        P_ROOT,
    ),
    _item(
        "g21",
        32,
        "Again, make sure you have work hours in Section BC",
        CTX,
        ("month_or_exposure",),
        "G21a,b,c.",
        (),
        P_ROOT,
    ),
    _item(
        "g22_24",
        32,
        "The purpose of this sequence is to help you make sure",
        CTX,
        ("amount", "month_or_exposure"),
        "G22–24.",
        ("j_g22_mainjob",),
        P_ROOT,
    ),
    _item(
        "g51a_g52a",
        37,
        "Remember that work hours in Section DE imply income here",
        CTX,
        ("amount", "month_or_exposure"),
        "G51a-G52a.",
        ("rt_g51_allwork",),
        P_ROOT,
    ),
    _item(
        "g52b",
        37,
        "Again, if income is reported but no work hours were recorded",
        CTX,
        ("month_or_exposure",),
        "G52b.",
        (),
        P_ROOT,
    ),
    # --- Section G: other-FU-member jobs ------------------------------------
    _item(
        "g75",
        40,
        "You may select as many codes as apply to the OFUM’s current",
        CTX,
        ("interview_and_role_attachment",),
        "G75.",
        (),
        P_G75,
    ),
    _item(
        "g_ofumjobs",
        40,
        "The questions cover jobs held by the Ofum",
        CTX,
        ("job_identifier",),
        None,
        ("j_g_ofumjobs",),
        P_G75,
    ),
    _item(
        "g76_82",
        40,
        "If this person’s employment was irregular, try to get",
        CTX,
        ("amount", "month_or_exposure"),
        "G76–82.",
        ("j_g76_eachjob",),
        P_G75,
    ),
    _item(
        "g78",
        40,
        "List total annual income from each job here",
        REM,
        ("amount", "reporting_unit"),
        "G78.",
        ("j_g76_eachjob",),
        P_G75,
    ),
    _item(
        "g79",
        40,
        "This figure should be the number of weeks in which any work",
        CTX,
        ("month_or_exposure",),
        "G79.",
        (),
        P_G75,
    ),
    _item(
        "g81",
        40,
        "If employment was irregular and R can’t give hours per week",
        CTX,
        ("month_or_exposure",),
        "G81.",
        ("j_g81_thatjob",),
        P_G75,
    ),
    _item(
        "g83",
        40,
        "“Income” in this sequence refers to non-labor income",
        CTX,
        ("amount",),
        "G83.",
        (),
        P_G75,
    ),
    # --- Section P: pension coverage and contributions at a named job -------
    _item(
        "p1",
        51,
        "Only Heads who are currently employed at a job (Section BC)",
        CTX,
        ("interview_and_role_attachment",),
        "P1.",
        ("j_p1_current",),
        P_PHEAD,
    ),
    _item(
        "p1_covered",
        51,
        "Note that P1 asks not only whether Head is eligible",
        CTX,
        ("public_retirement_system_participation",),
        None,
        ("j_p1_jobemployer",),
        P_PHEAD,
    ),
    _item(
        "p6",
        51,
        "Although we ask how many years Head has been covered",
        CTX,
        ("month_or_exposure", "public_retirement_system_participation"),
        "P6.",
        (),
        P_PHEAD,
    ),
    _item(
        "p7_p8",
        51,
        "Heads not currently covered by a plan may be after a certain",
        CTX,
        ("month_or_exposure", "public_retirement_system_participation"),
        "P7–P8.",
        (),
        P_PHEAD,
    ),
    _item(
        "p11_p15",
        52,
        "Head may be required to contribute a certain amount",
        REM,
        ("amount", "reporting_unit"),
        "P11–P15.",
        (),
        P_PHEAD,
    ),
    _item(
        "p17_p19",
        52,
        "What amount does the employer contribute",
        REM,
        ("amount", "reporting_unit"),
        "P17–P19.",
        (),
        P_PHEAD,
    ),
    _item(
        "p45_p69",
        54,
        "Here we ask about pensions from a former employer",
        CTX,
        ("public_retirement_system_participation",),
        "P45–P69.",
        ("j_p45_fmremp",),
        P_PHEADFMR,
    ),
    _item(
        "p_wifescope",
        56,
        "The application checks for a Wife/“Wife” in the FU and her",
        CTX,
        ("interview_and_role_attachment",),
        None,
        (),
        P_ROOT,
    ),
    _item(
        "p71",
        56,
        "Only Wifes/”Wifes” who are currently employed at a job",
        CTX,
        ("interview_and_role_attachment",),
        "P71.",
        ("j_p71_current",),
        P_PWIFE,
    ),
    _item(
        "p71_covered",
        56,
        "Note that P71 asks not only whether Wife/”Wife is eligible",
        CTX,
        ("public_retirement_system_participation",),
        None,
        ("j_p71_jobemployer",),
        P_PWIFE,
    ),
    _item(
        "p76",
        56,
        "Although we ask how many years Wife/”Wife” has been covered",
        CTX,
        ("month_or_exposure", "public_retirement_system_participation"),
        "P76.",
        (),
        P_PWIFE,
    ),
    _item(
        "p81_p85",
        56,
        "Wife/”Wife” may be required to contribute a certain amount",
        REM,
        ("amount", "reporting_unit"),
        "P81–P85.",
        (),
        P_PWIFE,
    ),
    _item(
        "p87_p89",
        56,
        "What amount does the employer contribute",
        REM,
        ("amount", "reporting_unit"),
        "P87–P89.",
        (),
        P_PWIFE,
    ),
    _item(
        "p115_p139",
        58,
        "Here we ask about pensions from a former employer",
        CTX,
        ("public_retirement_system_participation",),
        "P115–P139.",
        ("j_p115_fmremp",),
        P_PWIFEFMR,
    ),
    # --- Section KL: lifetime work exposure and occupation ------------------
    _item(
        "k63l70",
        75,
        "This means the number of years in which any work was done",
        CTX,
        ("month_or_exposure",),
        "K63L70.",
        (),
        P_KL,
    ),
    _item(
        "k64l71",
        75,
        "Thirty-five hours or more per week is full-time",
        CTX,
        ("month_or_exposure",),
        "K64L71.",
        (),
        P_KL,
    ),
    _item(
        "k66l73",
        75,
        "Again, use the same probing technique you use in Section BC",
        CTX,
        ("occupation", "industry"),
        "K66L73.",
        (),
        P_KL,
    ),
    _item(
        "l74",
        75,
        "We are interested in the similarity of occupations",
        CTX,
        ("occupation",),
        "L74.",
        ("j_l74_diversejobs",),
        P_KL,
    ),
    # --- Section R: off-year earnings ---------------------------------------
    _item(
        "r2",
        81,
        "We mean the total earnings from all jobs Head had in 2003",
        REM,
        ("amount",),
        "R2.",
        ("rt_r2_total", "j_r2_alljobs", "a_r2_business"),
        P_ROOT,
    ),
    _item(
        "r2_r6",
        81,
        "If there is a Wife or “Wife” in the FU this set",
        CTX,
        ("interview_and_role_attachment",),
        "R2-R6.",
        (),
        P_ROOT,
    ),
    _item(
        "r9_r15",
        81,
        "This series is for any OFUM age 16 or older in the 2003 FU",
        CTX,
        ("interview_and_role_attachment",),
        "R9–R15.",
        (),
        P_ROOT,
    ),
    # --- Interviewer Observations: unreported and unpaid jobs ---------------
    _item(
        "io18a",
        96,
        "Tell us for which FU member or members you discovered a job",
        CTX,
        ("job_identifier",),
        "IO18a.",
        ("j_io18a_job",),
        P_IO18,
    ),
    _item(
        "io18a_details",
        96,
        "Please provide as much information as possible about occupation",
        CTX,
        ("amount", "month_or_exposure", "industry", "occupation"),
        None,
        ("j_io18a_job",),
        P_IO18,
    ),
    _item(
        "io19a",
        96,
        "Please specify who and which job",
        CTX,
        ("job_identifier",),
        "IO19a.",
        ("j_io19a_thatjob",),
        P_IO19,
    ),
    _item(
        "io19_unpaid",
        96,
        "We often have people who report that they work in a spouse’s",
        CTX,
        ("assignment", "employee_self_or_mixed"),
        None,
        ("a_io19_business",),
        P_IO19,
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


# Printed repeat and cross-reference instructions.  Each is dispositioned
# exactly once below, either against two retained local anchors or as an
# unresolved printed target preserved verbatim for global assembly.
REPEAT_SPECS: tuple[dict[str, Any], ...] = (
    _ri(
        "ri_bcde4_every",
        16,
        _mark("BC/DE4-7. You will be asking employer’s names"),
        P_BCJOB,
    ),
    _ri(
        "ri_f2_3",
        23,
        _mark("income-producing work and should be included in Section BC"),
    ),
    _ri("ri_g1a", 29, _mark("You will know from Sections BC or DE whether")),
    _ri("ri_g4", 30, _mark("Farm income equals total receipts")),
    _ri(
        "ri_g_matchhours",
        30,
        _mark("We must have work hours for all income reported in Section G"),
    ),
    _ri(
        "ri_g5_repeat",
        30,
        _mark("one business, repeat questions G7a-G11b"),
    ),
    _ri(
        "ri_g9",
        30,
        _mark("reported in Section BC, and Wife’s/“wife’s” work time"),
    ),
    _ri(
        "ri_g11b_wages",
        30,
        _mark("belongs with the Wife’s/“Wife’s” or OFUM’s job income"),
    ),
    _ri("ri_g12", 31, _mark("In section BC we ask about current pay rates")),
    _ri(
        "ri_g13_g11b", 31, _mark("If an amount is given for both G11b and G13")
    ),
    _ri(
        "ri_g17",
        31,
        _mark("If there are no work hours reported in Section BC for income"),
    ),
    _ri("ri_g18b", 32, _mark("farming income should be listed at G2-G4")),
    _ri(
        "ri_g18c",
        32,
        _mark("work hours should be mentioned in Section BC. If no job"),
    ),
    _ri(
        "ri_g21",
        32,
        _mark("Again, make sure you have work hours in Section BC"),
    ),
    _ri(
        "ri_g51a",
        37,
        _mark("Remember that work hours in Section DE imply income here"),
    ),
    _ri(
        "ri_g51_business",
        37,
        _mark(
            "she is full or part owner, it may already be included at G5-G11b"
        ),
    ),
    _ri(
        "ri_g52b",
        37,
        _mark("Again, if income is reported but no work hours were recorded"),
    ),
    _ri(
        "ri_g53_63",
        37,
        _mark("These questions are the same as those asked for the Head"),
    ),
    _ri(
        "ri_g75",
        40,
        _mark("BC1-BC3/DE1-DE3 QxQs for definitions of employment status"),
        P_G75,
    ),
    _ri(
        "ri_g83",
        40,
        _mark("should be included at G78, not here"),
        P_G75,
    ),
    _ri(
        "ri_p1",
        51,
        _mark("Only Heads who are currently employed at a job (Section BC)"),
        P_PHEAD,
    ),
    _ri(
        "ri_p45",
        54,
        _mark("procedures described in the P1–P44 QxQs apply here as well"),
        P_PHEADFMR,
    ),
    _ri(
        "ri_p_wifeparallel",
        56,
        _mark("P115–P139, Pension from a Former Employer, are parallel"),
    ),
    _ri(
        "ri_p71",
        56,
        _mark("Only Wifes/”Wifes” who are currently employed at a job"),
        P_PWIFE,
    ),
    _ri(
        "ri_p115",
        58,
        _mark("procedures described in the P71–P114 QxQs apply here as well"),
        P_PWIFEFMR,
    ),
    _ri(
        "ri_k66l73",
        75,
        _mark("Again, use the same probing technique you use in Section BC"),
        P_KL,
    ),
    _ri(
        "ri_io18a",
        96,
        _mark("Tell us for which FU member or members you discovered a job"),
        P_IO18,
    ),
)

XREF = "explicit_cross_reference"
REPEATED = "explicit_repeat_instruction"
RESOLVED_HANDOFF = "local_resolved_cross_reference_for_global_assembly"

# Resolved alias evidence: both endpoints carry a retained local anchor.
RESOLVED_ALIAS_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (XREF, "ri_g1a", "g1a#a", "bcde20#a"),
    (XREF, "ri_g4", "g4#a", "g2#a"),
    (XREF, "ri_g4", "g4#a", "g3#a"),
    (XREF, "ri_g13_g11b", "g13#a", "g11b#a"),
    (XREF, "ri_g17", "g17f_g23#a", "g13#a"),
    (XREF, "ri_g18b", "g18b#a", "g2#a"),
    (XREF, "ri_g18b", "g18b#a", "g4#a"),
    (XREF, "ri_g51_business", "g51a_g52a#a", "g5_7a#a"),
    (XREF, "ri_g75", "g75#a", "bcde1_3#a"),
    (XREF, "ri_g83", "g83#a", "g78#a"),
    (XREF, "ri_p45", "p45_p69#a", "p1#a"),
    (XREF, "ri_p115", "p115_p139#a", "p71#a"),
)

OUTSIDE = "local_target_outside_rq_annotation_domain"
SERIES = "local_series_target_unresolved_for_global_assembly"
CROSSDOC = "cross_document_target_unresolved_for_global_assembly"

# Unresolved alias evidence: the printed target is a section reference, a
# question range, or a repeated employment spell.  It is preserved verbatim
# for global assembly and is never silently bound inside the shard.
UNRESOLVED_ALIAS_SPECS: tuple[dict[str, Any], ...] = (
    {
        "relation": REPEATED,
        "instruction": "ri_bcde4_every",
        "page": 16,
        "target": "every job that H/W",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_f2_3",
        "page": 23,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g_matchhours",
        "page": 30,
        "target": "Sections BC/DE",
        "handoff": SERIES,
    },
    {
        "relation": REPEATED,
        "instruction": "ri_g5_repeat",
        "page": 30,
        "target": "G7a-G11b",
        "handoff": OUTSIDE,
    },
    {
        "relation": XREF,
        "instruction": "ri_g9",
        "page": 30,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g11b_wages",
        "page": 30,
        "target": "OFUM’s job income questions",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g12",
        "page": 31,
        "target": "section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g18c",
        "page": 32,
        "target": "Section BC",
        "target_occurrence": 1,
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g21",
        "page": 32,
        "target": "Section BC",
        "target_occurrence": 2,
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g51a",
        "page": 37,
        "target": "Section DE",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g52b",
        "page": 37,
        "target": "Section DE",
        "target_occurrence": 1,
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_g53_63",
        "page": 37,
        "target": "those asked for the Head",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_p1",
        "page": 51,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_p_wifeparallel",
        "page": 56,
        "target": "the Head’s series",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_p71",
        "page": 56,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_k66l73",
        "page": 75,
        "target": "Section BC",
        "handoff": SERIES,
    },
    {
        "relation": XREF,
        "instruction": "ri_io18a",
        "page": 96,
        "target": "employment section",
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
        key=lambda row: (
            min(
                (
                    occurrence_by_id[occurrence_id]["page_number"],
                    occurrence_by_id[occurrence_id][
                        "occurrence_index_on_page"
                    ],
                )
                for occurrence_id in row["evidence_occurrence_ids"]
            )
            + (row["local_repeat_evidence_id"],)
        )
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
    # 37 exact-span reviewer re-classifications: the candidate found the
    # printed line that whole-page review retained, but read it as the wrong
    # kind -- most often a conditional clause inside an objective statement
    # read as controlling flow, or a cross reference read as a field prompt.
    (18, 2011, 2078, "flow_branch_label"): "context_anchor",
    (
        20,
        1350,
        1440,
        "repeat_or_alias_instruction",
    ): "remuneration_component_anchor",
    (20, 1993, 2082, "flow_branch_label"): "context_anchor",
    (21, 379, 466, "flow_branch_label"): "context_anchor",
    (21, 735, 829, "repeat_or_alias_instruction"): "context_anchor",
    (23, 173, 271, "flow_branch_label"): "context_anchor",
    (29, 136, 222, "context_anchor"): "flow_branch_label",
    (30, 106, 193, "role_total_anchor"): "remuneration_component_anchor",
    (30, 781, 856, "flow_branch_label"): "repeat_or_alias_instruction",
    (30, 1153, 1244, "flow_branch_label"): "context_anchor",
    (30, 1455, 1544, "flow_branch_label"): "context_anchor",
    (30, 2131, 2213, "flow_branch_label"): "remuneration_component_anchor",
    (30, 2319, 2396, "flow_branch_label"): "repeat_or_alias_instruction",
    (31, 248, 336, "flow_branch_label"): "context_anchor",
    (31, 1795, 1875, "flow_branch_label"): "repeat_or_alias_instruction",
    (31, 1916, 2015, "flow_branch_label"): "remuneration_component_anchor",
    (31, 2087, 2178, "flow_branch_label"): "remuneration_component_anchor",
    (31, 2447, 2522, "context_anchor"): "remuneration_component_anchor",
    (32, 17, 86, "context_anchor"): "remuneration_component_anchor",
    (32, 363, 442, "context_anchor"): "remuneration_component_anchor",
    (32, 363, 442, "flow_branch_label"): "remuneration_component_anchor",
    (32, 455, 537, "flow_branch_label"): "repeat_or_alias_instruction",
    (32, 1252, 1328, "context_anchor"): "repeat_or_alias_instruction",
    (32, 1252, 1328, "flow_branch_label"): "repeat_or_alias_instruction",
    (32, 2982, 3071, "flow_branch_label"): "context_anchor",
    (37, 705, 785, "flow_branch_label"): "repeat_or_alias_instruction",
    (37, 1131, 1227, "field_purpose_prompt"): "repeat_or_alias_instruction",
    (40, 1334, 1434, "flow_branch_label"): "context_anchor",
    (40, 1715, 1809, "context_anchor"): "remuneration_component_anchor",
    (40, 1715, 1809, "flow_branch_label"): "remuneration_component_anchor",
    (40, 1715, 1809, "role_total_anchor"): "remuneration_component_anchor",
    (40, 1970, 2067, "flow_branch_label"): "context_anchor",
    (54, 45, 134, "flow_branch_label"): "context_anchor",
    (58, 680, 771, "flow_branch_label"): "context_anchor",
    (81, 697, 796, "flow_branch_label"): "context_anchor",
    (95, 2509, 2595, "field_purpose_prompt"): "flow_branch_label",
    (96, 409, 497, "field_purpose_prompt"): "flow_branch_label",
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
    """Build document 66 from pinned source bytes and explicit decisions."""

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
        raise ValueError("document-66 independently replayed identity drift")

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


CANDIDATE_DENOMINATOR = 3948


def validate_annotation(
    value: Mapping[str, Any], capture_root: Path | None = None
) -> None:
    """Validate every stage-2 document-66 source and sealing invariant."""

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
        raise ValueError("document-66 candidate denominator drift")
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
        committed = _strict_load(OUTPUT_PATH, "stage-2 document-66 annotation")
        validate_annotation(committed, capture_root=args.capture_root)
    else:
        _write(value)
    print(
        "document 66: "
        f"{len(value['questionnaire_page_rows'])} pages, "
        f"{len(value['questionnaire_occurrence_rows'])} occurrences, "
        f"{len(value['flow_branch_rows'])} branches, sealed"
    )


if __name__ == "__main__":
    main()
