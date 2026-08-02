#!/usr/bin/env python3
"""Generate deterministic, nonauthority R_Q annotation candidates.

The fixed source replay selects the 81-document/page denominator before this
tool reads any candidate output.  Machine detections are review aids only:
they never become section-19 annotation rows without explicit stage-2
adjudication.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402
import build_rq_stage1_source_replay as source_replay  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

SCHEMA_VERSION = "rq_stage1_document_annotation_candidates.v1"
BATCH_SCHEMA_VERSION = "rq_stage1_candidate_batch_manifest.v1"
INDEX_SCHEMA_VERSION = "rq_stage1_candidate_index.v1"
STATUS = "unadjudicated_nonauthority_candidates"
BATCH_STATUS = "pass_complete_candidate_batch"
INDEX_STATUS = "pass_complete_candidate_index"
CANONICALIZATION = source_tools.CANONICALIZATION
SOURCE_REPLAY_PATH = source_replay.OUTPUT_PATH
SOURCE_REPLAY_RAW_SHA256 = (
    "f2f676db3f9180b85af1977253fb8c10ff7fd60494e1597212b922dfc0f5920a"
)
SOURCE_REPLAY_CONTENT_SHA256 = (
    "48e259ddf4c9eb60b7f9fdfd73b2576255400a7cdf19e4115d41bcf5bad3e8cc"
)
CANDIDATE_ROOT = ROOT / "docs" / "analysis" / "rq_stage1_candidates"
INDEX_PATH = CANDIDATE_ROOT / "index_v1.json"
BATCH_SIZE = 10
FLOW_ROOT_ID = "rq-candidate-flow:root"
FLOW_ROOT_PATH_ID = "rq-candidate-flow-path:root"
ADJUDICATION_STATUS = "unadjudicated_candidate"

OCCURRENCE_KINDS = (
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
KIND_ORDER = {kind: position for position, kind in enumerate(OCCURRENCE_KINDS)}

CANDIDATE_NONSELECTION_LAW = {
    "authority_kind": "candidate_only_nonauthority",
    "candidate_selected_source_denominator": False,
    "auto_promotion_permitted": False,
    "stage2_rows_emitted": False,
    "adjudication_required_for_every_stage2_row": True,
    "zero_candidate_page_proves_zero_canonical_occurrences": False,
    "final_global_node_ids_assigned": False,
    "status": "pass",
}

FLOW_LINE = r"""
    \bIF\b
    |\b(?:GO|TURN|SKIP)\s+(?:BACK\s+)?TO\b
    |\bASK\b.{0,80}\b(?:IF|EVERYONE|ALL)\b
    |\b(?:ALL\s+OTHERS|OTHERWISE|ASK\s+EVERYONE)\b
    |\b(?:LOOP|REPEAT)\s*(?:\d|[A-Z])
    |\b(?:LOGIC|CAI\s+CHECKPOINT|CHECKPOINT)\b
    |[→↓]
    |(?:^|\s)>{1,2}(?=\s|[A-Z])
    |\[[A-Z][A-Z0-9_]{0,24}\s*(?:>=|<=|=|>|<|GE\b|LE\b)[^]\r\n]{0,120}:
"""
ROLE_TOKEN = r"""
    \b(?:HEAD|WIFE|HUSBAND|REFERENCE[ -]PERSON|SPOUSE[ -]PARTNER)(?:['’]S)?\b
    |\[(?:RP|SP)\]
    |["“]WIFE["”]
"""
JOB_TOKEN = r"""
    \b(?:(?:current|present|main|extra|other|another|additional|first|second|
    third|fourth|fifth|last|former|previous|most\s+recent|new|regular|this|
    that|same|which|one|two|\d+(?:st|nd|rd|th)?)\s+){0,3}
    (?:job|jobs|occupation|occupations|employer|employers|position|positions)\b
    |\b(?:BC)?JOB(?:TYPE|NUM|COUNT)\b
"""
REMUNERATION_TOKEN = r"""
    \b(?:wages?|salar(?:y|ies)|bonus(?:es)?|overtime|tips?|commissions?|
    earn(?:s|ed|ing|ings)?|compensation|receipts|profits?|loss(?:es)?|fees?|
    honoraria|piecework|paychecks?)\b
    |\b(?:hourly\s+wage\s+rate|pay\s+rate|rate\s+of\s+pay|
    income\s+from\s+work|labor\s+income|job[- ]related\s+income|
    operating\s+expenses|net\s+income)\b
    |\bhow\s+much\b.{0,80}\b(?:pay|paid)\b
    |\b(?:pay|paid)\b.{0,80}\b(?:job|work|hour|week|month|year)\b
"""
ROLE_TOTAL_LINE = r"""
    (?:\b(?:total|altogether|combined|in\s+all)\b|
    \ball\b.{0,30}\bjobs?\b).{0,140}
    \b(?:wages?|salar(?:y|ies)|earn(?:s|ed|ing|ings)?|income|pay)\b
    |\b(?:wages?|salar(?:y|ies)|earn(?:s|ed|ing|ings)?|income|pay)\b
    .{0,140}(?:\b(?:total|altogether|combined|in\s+all)\b|
    \ball\b.{0,30}\bjobs?\b)
"""
FARM_TOKEN = r"""
    \b(?:farm(?:er|ers|ing|s)?|ranch(?:er|ers|ing)?|agricultur(?:e|al)|
    market\s+gardening)\b
"""
BUSINESS_TOKEN = r"""
    \b(?:business(?:es)?|self[- ]?employ(?:ed|ment)?|unincorporated|
    incorporated|corporation|partnership|proprietorship|
    professional\s+practice)\b
"""
CONTEXT_LINE = r"""
    \b(?:hours?|weeks?|days?|months?|years?)\b.{0,100}
    \b(?:work(?:ed|ing)?|jobs?|employ(?:ed|ment)?)\b
    |\b(?:work(?:ed|ing)?|jobs?|employ(?:ed|ment)?)\b.{0,100}
    \b(?:hours?|weeks?|days?|months?|years?)\b
    |\b(?:working\s+now|looking\s+for\s+(?:a\s+)?(?:work|job)|retired|
    keeping\s+house|housewife|student|disabled|temporarily\s+laid\s+off|
    unemployed|on\s+strike|full[- ]time|part[- ]time)\b
    |\b(?:start(?:ed|ing)?|begin|began|end(?:ed|ing)?|leave|left|quit|lost)
    \b.{0,80}\b(?:work|job|business|employ)\w*\b
    |\b(?:employee|self[- ]employed|incorporat(?:ed|ion)|government\s+level|
    (?:federal|state|local)\s+government|industry|occupation|union|
    railroad\s+(?:employer|service)|ministerial\s+service|clergy|
    church\s+employee|religious\s+order|domestic\s+service|
    agricultural\s+service|election\s+work|family\s+service|
    casual\s+service|foreign\s+government|international\s+organization|
    nonresident\s+alien|student\s+service)\b
"""
ALIAS_LINE = r"""
    \b(?:again|repeat|same\s+(?:as|job|employer|business|CMJ)|
    another\s+(?:job|business)|other\s+job|next\s+(?:job|business)|
    additional\s+(?:job|business|member)|copy|preload|refer\s+(?:back\s+)?to|
    cross[- ]reference|go\s+back\s+to|turn\s+back\s+and\s+ask)\b
    |\b(?:already|earlier|previously)\b.{0,80}
    \b(?:told|reported|mentioned|asked|covered)\b
    |\b(?:TITLE|ANSWER|DATA)\s+FROM\s+[A-Z]{1,12}\d[A-Z0-9_.-]*\b
"""
INTERROGATIVE_LINE = r"""
    ^\s*(?:\([^)]{0,30}\)\s*)?
    (?:how|what|when|where|why|who|whose|which|did|do|does|is|are|was|were|
    have|has|would|could|can|will)\b
"""
QUESTION_IDENTIFIER_LINE = r"""
    ^\s*(?:\([^\r\n)]{0,24}\)\s*)?
    (?:(?:[A-Z]{1,10}\d[A-Z0-9_.-]{0,22})|(?:[A-Z][A-Z0-9_]{2,32}))\.
    (?:\s|\()
"""

DETECTOR_RULE_ROWS = (
    {
        "detector_rule_id": "flow_control_line_v1",
        "occurrence_kind_candidate": "flow_branch_label",
        "span_mode": "trimmed_physical_line",
        "pattern": FLOW_LINE,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "role_lexeme_v1",
        "occurrence_kind_candidate": "role_anchor",
        "span_mode": "exact_regex_match",
        "pattern": ROLE_TOKEN,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "job_lexeme_v1",
        "occurrence_kind_candidate": "job_anchor",
        "span_mode": "exact_regex_match",
        "pattern": JOB_TOKEN,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "remuneration_lexeme_v1",
        "occurrence_kind_candidate": "remuneration_component_anchor",
        "span_mode": "exact_regex_match",
        "pattern": REMUNERATION_TOKEN,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "role_total_line_v1",
        "occurrence_kind_candidate": "role_total_anchor",
        "span_mode": "trimmed_physical_line",
        "pattern": ROLE_TOTAL_LINE,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "farm_lexeme_v1",
        "occurrence_kind_candidate": "farm_aggregate_anchor",
        "span_mode": "exact_regex_match",
        "pattern": FARM_TOKEN,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "business_lexeme_v1",
        "occurrence_kind_candidate": "business_aggregate_anchor",
        "span_mode": "exact_regex_match",
        "pattern": BUSINESS_TOKEN,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "context_line_v1",
        "occurrence_kind_candidate": "context_anchor",
        "span_mode": "trimmed_physical_line",
        "pattern": CONTEXT_LINE,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "purpose_question_mark_line_v1",
        "occurrence_kind_candidate": "field_purpose_prompt",
        "span_mode": "trimmed_physical_line",
        "pattern": r"\?",
        "ignore_case": False,
    },
    {
        "detector_rule_id": "purpose_interrogative_line_v1",
        "occurrence_kind_candidate": "field_purpose_prompt",
        "span_mode": "trimmed_physical_line",
        "pattern": INTERROGATIVE_LINE,
        "ignore_case": True,
    },
    {
        "detector_rule_id": "purpose_identifier_line_v1",
        "occurrence_kind_candidate": "field_purpose_prompt",
        "span_mode": "trimmed_physical_line",
        "pattern": QUESTION_IDENTIFIER_LINE,
        "ignore_case": False,
    },
    {
        "detector_rule_id": "repeat_alias_line_v1",
        "occurrence_kind_candidate": "repeat_or_alias_instruction",
        "span_mode": "trimmed_physical_line",
        "pattern": ALIAS_LINE,
        "ignore_case": True,
    },
)
RULE_ORDER = {
    row["detector_rule_id"]: position
    for position, row in enumerate(DETECTOR_RULE_ROWS)
}
PRINTED_IDENTIFIER_RE = re.compile(
    r"^\s*(?:\([^\r\n)]{0,24}\)\s*)?"
    r"((?:[A-Z]{1,10}\d[A-Z0-9_.-]{0,22})|"
    r"(?:[A-Z][A-Z0-9_]{2,32}))\.",
    re.ASCII,
)
ROUTE_TARGET_RE = re.compile(
    r"\b(?:GO|TURN|SKIP)\s+(?:BACK\s+)?TO\s+"
    r"([A-Z]{1,10}\d[A-Z0-9_.-]{0,22})",
    re.ASCII | re.IGNORECASE,
)

ANCHOR_CLASSIFICATIONS = {
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
COMPONENT_KINDS = {
    "remuneration_component_anchor",
    "context_anchor",
}
PARENT_ANCHOR_KINDS = {
    "job_anchor",
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return source_tools._canonical_digest(value)


def _content_sha256(value: Mapping[str, Any]) -> str:
    return source_tools._content_sha256(value)


def _expect_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keyset drift")


def _compiled_detector_rules() -> tuple[
    tuple[Mapping[str, Any], re.Pattern], ...
]:
    result: list[tuple[Mapping[str, Any], re.Pattern]] = []
    for row in DETECTOR_RULE_ROWS:
        flags = re.ASCII | re.VERBOSE
        if row["ignore_case"]:
            flags |= re.IGNORECASE
        result.append((row, re.compile(row["pattern"], flags)))
    return tuple(result)


COMPILED_DETECTOR_RULES = _compiled_detector_rules()
GENERATOR_SPEC_IDENTITY = {
    "generator_spec_version": "rq_stage1_candidate_detectors.v1",
    "occurrence_kind_order": list(OCCURRENCE_KINDS),
    "occurrence_kind_order_sha256": _canonical_digest(list(OCCURRENCE_KINDS)),
    "detector_rule_count": len(DETECTOR_RULE_ROWS),
    "detector_rule_domain_sha256": _canonical_digest(list(DETECTOR_RULE_ROWS)),
    "span_law": "exact_utf8_bytes_lf_physical_lines_ascii_space_tab_trim_v1",
    "candidate_order": "page_start_end_kind_rule_then_candidate_id_v1",
}


def source_replay_identity() -> dict[str, Any]:
    return {
        "path": str(SOURCE_REPLAY_PATH.relative_to(ROOT)),
        "schema_version": source_replay.SCHEMA_VERSION,
        "byte_size": SOURCE_REPLAY_PATH.stat().st_size,
        "raw_sha256": SOURCE_REPLAY_RAW_SHA256,
        "content_sha256": SOURCE_REPLAY_CONTENT_SHA256,
    }


def load_source_replay() -> dict[str, Any]:
    raw = SOURCE_REPLAY_PATH.read_bytes()
    if _sha256(raw) != SOURCE_REPLAY_RAW_SHA256:
        raise ValueError("R_Q source replay raw identity drift")
    value = source_tools.strict_parse_document(raw, "R_Q source replay")
    if not isinstance(value, dict):
        raise ValueError("R_Q source replay is not an object")
    source_replay.validate_source_replay(value)
    if value["integrity"]["content_sha256"] != SOURCE_REPLAY_CONTENT_SHA256:
        raise ValueError("R_Q source replay content identity drift")
    return value


def _physical_lines(page_text: str) -> list[dict[str, Any]]:
    """Split only on LF and trim only exact CR/ASCII space/tab edges."""

    rows: list[dict[str, Any]] = []
    start = 0
    line_number = 1
    nonblank_ordinal = 0
    while start <= len(page_text):
        lf = page_text.find("\n", start)
        raw_end = len(page_text) if lf < 0 else lf
        end = (
            raw_end - 1
            if raw_end > start and page_text[raw_end - 1] == "\r"
            else raw_end
        )
        trimmed_start = start
        while trimmed_start < end and page_text[trimmed_start] in " \t":
            trimmed_start += 1
        trimmed_end = end
        while (
            trimmed_end > trimmed_start and page_text[trimmed_end - 1] in " \t"
        ):
            trimmed_end -= 1
        if trimmed_start < trimmed_end:
            nonblank_ordinal += 1
            indent = 0
            for character in page_text[start:trimmed_start]:
                indent = (
                    indent + 1 if character == " " else ((indent // 8) + 1) * 8
                )
            rows.append(
                {
                    "line_number": line_number,
                    "start": trimmed_start,
                    "end": trimmed_end,
                    "indent_columns": indent,
                    "nonblank_ordinal": nonblank_ordinal,
                    "text": page_text[trimmed_start:trimmed_end],
                }
            )
        if lf < 0:
            break
        start = lf + 1
        line_number += 1
    return rows


def _utf8_offsets(text: str) -> list[int]:
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + len(character.encode("utf-8")))
    return offsets


def detect_page_candidates(
    page_text: str,
    *,
    source_document_id: str,
    interview_wave: int,
    page_number: int,
    document_nonblank_line_base: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Return ordered occurrence candidates for one exact page string."""

    page_bytes = page_text.encode("utf-8")
    offsets = _utf8_offsets(page_text)
    hits: dict[tuple[int, int, str], dict[str, Any]] = {}
    lines = _physical_lines(page_text)
    for line in lines:
        for rule, pattern in COMPILED_DETECTOR_RULES:
            matches: Sequence[re.Match]
            if rule["span_mode"] == "trimmed_physical_line":
                match = pattern.search(line["text"])
                matches = () if match is None else (match,)
            else:
                matches = tuple(pattern.finditer(line["text"]))
            for match in matches:
                if rule["span_mode"] == "trimmed_physical_line":
                    char_start = line["start"]
                    char_end = line["end"]
                else:
                    char_start = line["start"] + match.start()
                    char_end = line["start"] + match.end()
                byte_start = offsets[char_start]
                byte_end = offsets[char_end]
                if byte_start >= byte_end:
                    continue
                key = (
                    byte_start,
                    byte_end,
                    rule["occurrence_kind_candidate"],
                )
                hit = hits.setdefault(
                    key,
                    {
                        "byte_start": byte_start,
                        "byte_end": byte_end,
                        "kind": rule["occurrence_kind_candidate"],
                        "line_number": line["line_number"],
                        "line_indent_columns": line["indent_columns"],
                        "document_nonblank_line_ordinal": (
                            document_nonblank_line_base
                            + line["nonblank_ordinal"]
                        ),
                        "rule_ids": [],
                    },
                )
                hit["rule_ids"].append(rule["detector_rule_id"])

    ordered_hits = sorted(
        hits.values(),
        key=lambda row: (
            row["byte_start"],
            row["byte_end"],
            KIND_ORDER[row["kind"]],
            tuple(RULE_ORDER[rule_id] for rule_id in row["rule_ids"]),
        ),
    )
    rows: list[dict[str, Any]] = []
    for candidate_index, hit in enumerate(ordered_hits):
        matched_bytes = page_bytes[hit["byte_start"] : hit["byte_end"]]
        matched_text = matched_bytes.decode("utf-8", errors="strict")
        rule_ids = sorted(set(hit["rule_ids"]), key=RULE_ORDER.__getitem__)
        matched_sha256 = _sha256(matched_bytes)
        candidate_id = "rq-candidate-occurrence:" + _canonical_digest(
            [
                source_document_id,
                interview_wave,
                page_number,
                hit["byte_start"],
                hit["byte_end"],
                candidate_index,
                hit["kind"],
                matched_sha256,
                rule_ids,
            ]
        )
        rows.append(
            {
                "candidate_occurrence_id": candidate_id,
                "source_document_id": source_document_id,
                "interview_wave": interview_wave,
                "page_number": page_number,
                "utf8_byte_start": hit["byte_start"],
                "utf8_byte_end": hit["byte_end"],
                "candidate_index_on_page": candidate_index,
                "occurrence_kind_candidate": hit["kind"],
                "matched_text": matched_text,
                "matched_utf8_sha256": matched_sha256,
                "line_number": hit["line_number"],
                "line_indent_columns": hit["line_indent_columns"],
                "document_nonblank_line_ordinal": hit[
                    "document_nonblank_line_ordinal"
                ],
                "detector_rule_ids": rule_ids,
                "candidate_flow_context_path_ids": [],
                "adjudication_status": ADJUDICATION_STATUS,
            }
        )
    return rows, len(lines)


def _flow_candidate_rows(
    occurrence_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flow_occurrences = [
        row
        for row in occurrence_rows
        if row["occurrence_kind_candidate"] == "flow_branch_label"
    ]
    branch_id_by_occurrence = {
        row["candidate_occurrence_id"]: (
            "rq-candidate-flow-branch:"
            + _canonical_digest(
                [
                    row["source_document_id"],
                    row["interview_wave"],
                    row["candidate_occurrence_id"],
                ]
            )
        )
        for row in flow_occurrences
    }
    result: list[dict[str, Any]] = []
    path_ids_by_occurrence: dict[str, list[str]] = {}
    for index, occurrence in enumerate(flow_occurrences):
        branch_id = branch_id_by_occurrence[
            occurrence["candidate_occurrence_id"]
        ]
        options: list[tuple[str | None, str]] = [(None, "root_fallback_v1")]
        earlier = [
            row
            for row in flow_occurrences[:index]
            if occurrence["document_nonblank_line_ordinal"]
            - row["document_nonblank_line_ordinal"]
            <= 64
        ]
        indentation_parent = next(
            (
                row
                for row in reversed(earlier)
                if row["line_indent_columns"]
                < occurrence["line_indent_columns"]
            ),
            None,
        )
        if indentation_parent is not None:
            options.append(
                (
                    branch_id_by_occurrence[
                        indentation_parent["candidate_occurrence_id"]
                    ],
                    "nearest_lower_indentation_v1",
                )
            )
        logic_parent = next(
            (
                row
                for row in reversed(earlier)
                if re.search(
                    r"\b(?:IF|LOGIC|CHECKPOINT)\b|\[",
                    row["matched_text"],
                    re.ASCII | re.IGNORECASE,
                )
            ),
            None,
        )
        if logic_parent is not None:
            options.append(
                (
                    branch_id_by_occurrence[
                        logic_parent["candidate_occurrence_id"]
                    ],
                    "nearest_logic_candidate_v1",
                )
            )
        route_targets = list(
            dict.fromkeys(
                match.group(1)
                for match in ROUTE_TARGET_RE.finditer(
                    occurrence["matched_text"]
                )
            )
        )
        seen_parent_ids: set[str | None] = set()
        for parent_id, basis_rule_id in options:
            if parent_id in seen_parent_ids:
                continue
            seen_parent_ids.add(parent_id)
            parent_path = (
                [FLOW_ROOT_ID]
                if parent_id is None
                else [FLOW_ROOT_ID, parent_id]
            )
            branch_path = [*parent_path, branch_id]
            candidate_flow_path_id = (
                "rq-candidate-flow-path:"
                + _canonical_digest(
                    [
                        occurrence["candidate_occurrence_id"],
                        branch_id,
                        parent_path,
                        branch_path,
                        basis_rule_id,
                        route_targets,
                    ]
                )
            )
            result.append(
                {
                    "candidate_flow_path_id": candidate_flow_path_id,
                    "source_candidate_occurrence_id": occurrence[
                        "candidate_occurrence_id"
                    ],
                    "candidate_branch_id": branch_id,
                    "candidate_parent_path": parent_path,
                    "candidate_branch_path": branch_path,
                    "basis_rule_id": basis_rule_id,
                    "route_target_tokens": route_targets,
                    "adjudication_status": ADJUDICATION_STATUS,
                }
            )
            path_ids_by_occurrence.setdefault(
                occurrence["candidate_occurrence_id"], []
            ).append(candidate_flow_path_id)

    preceding_flow: list[dict[str, Any]] = []
    for occurrence in occurrence_rows:
        context_ids = [FLOW_ROOT_PATH_ID]
        prior = next(
            (
                row
                for row in reversed(preceding_flow)
                if occurrence["document_nonblank_line_ordinal"]
                - row["document_nonblank_line_ordinal"]
                <= 64
            ),
            None,
        )
        if prior is not None:
            context_ids.extend(
                path_ids_by_occurrence[prior["candidate_occurrence_id"]]
            )
        occurrence["candidate_flow_context_path_ids"] = context_ids
        if occurrence["occurrence_kind_candidate"] == "flow_branch_label":
            preceding_flow.append(occurrence)
    return result


def _role_classification(matched_text: str) -> str:
    lowered = matched_text.casefold()
    if (
        "head" in lowered
        or "reference" in lowered
        or lowered.strip("[]").casefold() == "rp"
    ):
        return "head_or_reference_person"
    return "spouse_or_partner"


def _printed_identifier(line_text: str) -> str | None:
    match = PRINTED_IDENTIFIER_RE.search(line_text)
    return None if match is None else match.group(1)


def _anchor_classification_rows(
    occurrence_rows: Sequence[Mapping[str, Any]],
    page_texts: Sequence[str],
) -> list[dict[str, Any]]:
    page_lines = [
        {row["line_number"]: row for row in _physical_lines(page_text)}
        for page_text in page_texts
    ]
    anchors = [
        row
        for row in occurrence_rows
        if row["occurrence_kind_candidate"] == "role_anchor"
        or row["occurrence_kind_candidate"] in ANCHOR_CLASSIFICATIONS
    ]
    result: list[dict[str, Any]] = []
    for index, occurrence in enumerate(anchors):
        kind = occurrence["occurrence_kind_candidate"]
        if kind == "role_anchor":
            node_domain = "role"
            classification = _role_classification(occurrence["matched_text"])
        else:
            node_domain, classification = ANCHOR_CLASSIFICATIONS[kind]
        parents: list[str] = []
        if kind in COMPONENT_KINDS:
            for earlier in reversed(anchors[:index]):
                if (
                    occurrence["document_nonblank_line_ordinal"]
                    - earlier["document_nonblank_line_ordinal"]
                    > 64
                ):
                    break
                if (
                    earlier["occurrence_kind_candidate"] in PARENT_ANCHOR_KINDS
                    and earlier["candidate_occurrence_id"] not in parents
                ):
                    parents.append(earlier["candidate_occurrence_id"])
                if len(parents) == 4:
                    break
            parents.reverse()
        line_text = page_lines[occurrence["page_number"] - 1][
            occurrence["line_number"]
        ]["text"]
        printed_identifier = _printed_identifier(line_text)
        candidate_id = (
            "rq-candidate-anchor-classification:"
            + _canonical_digest(
                [
                    occurrence["candidate_occurrence_id"],
                    node_domain,
                    classification,
                    parents,
                    printed_identifier,
                    occurrence["matched_utf8_sha256"],
                    occurrence["detector_rule_ids"],
                ]
            )
        )
        result.append(
            {
                "candidate_anchor_classification_id": candidate_id,
                "source_candidate_occurrence_id": occurrence[
                    "candidate_occurrence_id"
                ],
                "node_domain_candidate": node_domain,
                "classification_candidate": classification,
                "parent_anchor_candidate_ids": parents,
                "printed_identifier_candidate": printed_identifier,
                "exact_label_sha256": occurrence["matched_utf8_sha256"],
                "basis_rule_ids": occurrence["detector_rule_ids"],
                "canonical_node_id": None,
                "adjudication_status": ADJUDICATION_STATUS,
            }
        )
    return result


def _whole_document_locator_candidate(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    wave = document["interview_waves"][0]
    candidate_locator_id = "rq-candidate-whole-document:" + _canonical_digest(
        [
            document["source_document_id"],
            wave,
            document["sha256"],
            document["byte_size"],
        ]
    )
    return {
        "candidate_locator_id": candidate_locator_id,
        "source_document_id": document["source_document_id"],
        "interview_wave": wave,
        "filename": Path(document["canonical_source_path"]).name,
        "location_type_candidate": "whole_document_exact_file_range",
        "byte_start": 0,
        "byte_end": document["byte_size"],
        "size_bytes": document["byte_size"],
        "full_file_sha256": document["sha256"],
        "range_sha256": document["sha256"],
        "pdf_page_domain_candidate": "all_pages_and_flow_branches",
        "adjudication_status": ADJUDICATION_STATUS,
    }


def _candidate_page_rows(
    document: Mapping[str, Any],
    expected_pages: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    occurrences_by_page: dict[int, list[str]] = {}
    for row in occurrence_rows:
        occurrences_by_page.setdefault(row["page_number"], []).append(
            row["candidate_occurrence_id"]
        )
    wave = document["interview_waves"][0]
    result: list[dict[str, Any]] = []
    for page in expected_pages:
        page_number = page["page_number"]
        result.append(
            {
                "candidate_page_id": (
                    "rq-candidate-page:"
                    + _canonical_digest(
                        [
                            document["source_document_id"],
                            wave,
                            page_number,
                            page["page_text_utf8_sha256"],
                        ]
                    )
                ),
                "replay_questionnaire_page_id": page["questionnaire_page_id"],
                "source_document_id": document["source_document_id"],
                "interview_wave": wave,
                "page_number": page_number,
                "page_text_utf8_sha256": page["page_text_utf8_sha256"],
                "candidate_occurrence_ids": occurrences_by_page.get(
                    page_number, []
                ),
                "candidate_status": ADJUDICATION_STATUS,
            }
        )
    return result


def _candidate_manifest(
    document: Mapping[str, Any],
    page_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
    flow_rows: Sequence[Mapping[str, Any]],
    anchor_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = Counter(
        row["occurrence_kind_candidate"] for row in occurrence_rows
    )
    payload = [
        list(page_rows),
        list(occurrence_rows),
        list(flow_rows),
        list(anchor_rows),
    ]
    return {
        "source_document_id": document["source_document_id"],
        "interview_wave": document["interview_waves"][0],
        "canonical_source_path": document["canonical_source_path"],
        "page_count": len(page_rows),
        "empty_candidate_page_count": sum(
            not row["candidate_occurrence_ids"] for row in page_rows
        ),
        "candidate_occurrence_count": len(occurrence_rows),
        "candidate_occurrence_counts_by_kind": {
            kind: counts[kind] for kind in OCCURRENCE_KINDS
        },
        "candidate_occurrence_keyset_sha256": _canonical_digest(
            [row["candidate_occurrence_id"] for row in occurrence_rows]
        ),
        "candidate_occurrence_domain_sha256": _canonical_digest(
            list(occurrence_rows)
        ),
        "candidate_flow_path_count": len(flow_rows),
        "candidate_flow_path_domain_sha256": _canonical_digest(
            list(flow_rows)
        ),
        "candidate_anchor_classification_count": len(anchor_rows),
        "candidate_anchor_classification_domain_sha256": _canonical_digest(
            list(anchor_rows)
        ),
        "candidate_payload_sha256": _canonical_digest(payload),
        "authority_kind": "candidate_only_nonauthority",
        "auto_promotion_permitted": False,
        "adjudication_required_for_every_stage2_row": True,
    }


def build_document_candidates(
    replay_artifact: Mapping[str, Any],
    document_source_position: int,
    capture_root: Path = source_tools.DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    """Build one fixed-position document candidate artifact."""

    documents = replay_artifact["source_document_replay"][
        "questionnaire_documents"
    ]
    if not 1 <= document_source_position <= len(documents):
        raise ValueError(
            "document source position outside fixed 81-row domain"
        )
    document = documents[document_source_position - 1]
    filename = Path(document["canonical_source_path"]).name
    source_tools._verified_file(
        capture_root / filename,
        document["byte_size"],
        document["sha256"],
        document["source_document_id"],
    )
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("candidate generation Poppler version drift")
    page_texts = questionnaire_inventory._pdftotext_pages(
        capture_root / filename
    )
    expected_pages = [
        row
        for row in replay_artifact["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == document["source_document_id"]
    ]
    if len(page_texts) != len(expected_pages):
        raise ValueError("candidate document page count differs from replay")
    for page_text, expected in zip(page_texts, expected_pages, strict=True):
        page_bytes = page_text.encode("utf-8")
        if (
            len(page_bytes) != expected["page_text_utf8_size_bytes"]
            or _sha256(page_bytes) != expected["page_text_utf8_sha256"]
        ):
            raise ValueError("candidate page bytes differ from replay")

    occurrence_rows: list[dict[str, Any]] = []
    nonblank_line_base = 0
    for page_number, page_text in enumerate(page_texts, start=1):
        page_occurrences, nonblank_count = detect_page_candidates(
            page_text,
            source_document_id=document["source_document_id"],
            interview_wave=document["interview_waves"][0],
            page_number=page_number,
            document_nonblank_line_base=nonblank_line_base,
        )
        occurrence_rows.extend(page_occurrences)
        nonblank_line_base += nonblank_count
    flow_rows = _flow_candidate_rows(occurrence_rows)
    anchor_rows = _anchor_classification_rows(occurrence_rows, page_texts)
    page_rows = _candidate_page_rows(document, expected_pages, occurrence_rows)
    manifest = _candidate_manifest(
        document, page_rows, occurrence_rows, flow_rows, anchor_rows
    )
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": (
            "rq-stage1-document-candidates:"
            + _canonical_digest([document["source_document_id"]])
        ),
        "generator_spec_identity": copy.deepcopy(GENERATOR_SPEC_IDENTITY),
        "source_replay_identity": source_replay_identity(),
        "document_source_position": document_source_position,
        "document_source_row": copy.deepcopy(document),
        "whole_document_locator_candidate": _whole_document_locator_candidate(
            document
        ),
        "candidate_page_rows": page_rows,
        "candidate_occurrence_rows": occurrence_rows,
        "candidate_flow_path_rows": flow_rows,
        "candidate_anchor_classification_rows": anchor_rows,
        "candidate_manifest": manifest,
        "candidate_nonselection_law": copy.deepcopy(
            CANDIDATE_NONSELECTION_LAW
        ),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_document_candidates(value, replay_artifact, page_texts)
    return value


def validate_document_candidates(
    value: Mapping[str, Any],
    replay_artifact: Mapping[str, Any],
    page_texts: Sequence[str] | None = None,
) -> None:
    """Mirror document candidate schemas, IDs, spans, covers, and laws."""

    _expect_keys(
        value,
        {
            "schema_version",
            "artifact_id",
            "generator_spec_identity",
            "source_replay_identity",
            "document_source_position",
            "document_source_row",
            "whole_document_locator_candidate",
            "candidate_page_rows",
            "candidate_occurrence_rows",
            "candidate_flow_path_rows",
            "candidate_anchor_classification_rows",
            "candidate_manifest",
            "candidate_nonselection_law",
            "integrity",
            "status",
        },
        "document candidates",
    )
    documents = replay_artifact["source_document_replay"][
        "questionnaire_documents"
    ]
    position = value["document_source_position"]
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["generator_spec_identity"] != GENERATOR_SPEC_IDENTITY
        or value["source_replay_identity"] != source_replay_identity()
        or not isinstance(position, int)
        or isinstance(position, bool)
        or not 1 <= position <= len(documents)
        or value["document_source_row"] != documents[position - 1]
        or value["candidate_nonselection_law"] != CANDIDATE_NONSELECTION_LAW
        or value["status"] != STATUS
        or value["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": _content_sha256(value),
        }
    ):
        raise ValueError("document candidate identity or law drift")
    document = value["document_source_row"]
    expected_artifact_id = (
        "rq-stage1-document-candidates:"
        + _canonical_digest([document["source_document_id"]])
    )
    if value["artifact_id"] != expected_artifact_id:
        raise ValueError("document candidate artifact ID drift")

    locator = value["whole_document_locator_candidate"]
    expected_locator = _whole_document_locator_candidate(document)
    if locator != expected_locator:
        raise ValueError("whole-document locator candidate drift")

    expected_pages = [
        row
        for row in replay_artifact["questionnaire_page_replay"][
            "questionnaire_page_rows"
        ]
        if row["source_document_id"] == document["source_document_id"]
    ]
    page_rows = value["candidate_page_rows"]
    occurrence_rows = value["candidate_occurrence_rows"]
    occurrence_ids: set[str] = set()
    occurrences_by_page: dict[int, list[str]] = {}
    last_order: tuple[Any, ...] | None = None
    for row in occurrence_rows:
        _expect_keys(
            row,
            {
                "candidate_occurrence_id",
                "source_document_id",
                "interview_wave",
                "page_number",
                "utf8_byte_start",
                "utf8_byte_end",
                "candidate_index_on_page",
                "occurrence_kind_candidate",
                "matched_text",
                "matched_utf8_sha256",
                "line_number",
                "line_indent_columns",
                "document_nonblank_line_ordinal",
                "detector_rule_ids",
                "candidate_flow_context_path_ids",
                "adjudication_status",
            },
            "occurrence candidate row",
        )
        kind = row["occurrence_kind_candidate"]
        matched_bytes = row["matched_text"].encode("utf-8")
        order = (
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            KIND_ORDER.get(kind, len(KIND_ORDER)),
            row["candidate_occurrence_id"],
        )
        expected_id = "rq-candidate-occurrence:" + _canonical_digest(
            [
                document["source_document_id"],
                document["interview_waves"][0],
                row["page_number"],
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["candidate_index_on_page"],
                kind,
                row["matched_utf8_sha256"],
                row["detector_rule_ids"],
            ]
        )
        if (
            kind not in KIND_ORDER
            or row["source_document_id"] != document["source_document_id"]
            or row["interview_wave"] != document["interview_waves"][0]
            or not 1 <= row["page_number"] <= len(expected_pages)
            or row["utf8_byte_start"] < 0
            or row["utf8_byte_end"] <= row["utf8_byte_start"]
            or row["utf8_byte_end"] - row["utf8_byte_start"]
            != len(matched_bytes)
            or _sha256(matched_bytes) != row["matched_utf8_sha256"]
            or row["candidate_occurrence_id"] != expected_id
            or row["candidate_occurrence_id"] in occurrence_ids
            or row["adjudication_status"] != ADJUDICATION_STATUS
            or not row["detector_rule_ids"]
            or row["detector_rule_ids"]
            != sorted(
                set(row["detector_rule_ids"]), key=RULE_ORDER.__getitem__
            )
            or last_order is not None
            and order < last_order
        ):
            raise ValueError("occurrence candidate row drift")
        if page_texts is not None:
            page_bytes = page_texts[row["page_number"] - 1].encode("utf-8")
            if (
                page_bytes[row["utf8_byte_start"] : row["utf8_byte_end"]]
                != matched_bytes
            ):
                raise ValueError("occurrence candidate span differs from page")
        occurrence_ids.add(row["candidate_occurrence_id"])
        occurrences_by_page.setdefault(row["page_number"], []).append(
            row["candidate_occurrence_id"]
        )
        last_order = order
    for _page_number, rows in _group_by_page(occurrence_rows).items():
        if [row["candidate_index_on_page"] for row in rows] != list(
            range(len(rows))
        ):
            raise ValueError("candidate same-page index drift")

    if len(page_rows) != len(expected_pages):
        raise ValueError("candidate page cover drift")
    for candidate_page, replay_page in zip(
        page_rows, expected_pages, strict=True
    ):
        expected_page = {
            "candidate_page_id": (
                "rq-candidate-page:"
                + _canonical_digest(
                    [
                        document["source_document_id"],
                        document["interview_waves"][0],
                        replay_page["page_number"],
                        replay_page["page_text_utf8_sha256"],
                    ]
                )
            ),
            "replay_questionnaire_page_id": replay_page[
                "questionnaire_page_id"
            ],
            "source_document_id": document["source_document_id"],
            "interview_wave": document["interview_waves"][0],
            "page_number": replay_page["page_number"],
            "page_text_utf8_sha256": replay_page["page_text_utf8_sha256"],
            "candidate_occurrence_ids": occurrences_by_page.get(
                replay_page["page_number"], []
            ),
            "candidate_status": ADJUDICATION_STATUS,
        }
        if candidate_page != expected_page:
            raise ValueError("candidate page row drift")

    flow_rows = value["candidate_flow_path_rows"]
    _validate_flow_rows(flow_rows, occurrence_rows)
    anchor_rows = value["candidate_anchor_classification_rows"]
    _validate_anchor_rows(anchor_rows, occurrence_rows, page_texts)
    expected_manifest = _candidate_manifest(
        document, page_rows, occurrence_rows, flow_rows, anchor_rows
    )
    if value["candidate_manifest"] != expected_manifest:
        raise ValueError("candidate manifest drift")


def _group_by_page(
    occurrence_rows: Sequence[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    result: dict[int, list[Mapping[str, Any]]] = {}
    for row in occurrence_rows:
        result.setdefault(row["page_number"], []).append(row)
    return result


def _validate_flow_rows(
    flow_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
) -> None:
    occurrences = {
        row["candidate_occurrence_id"]: row for row in occurrence_rows
    }
    occurrence_order = {
        row["candidate_occurrence_id"]: position
        for position, row in enumerate(occurrence_rows)
    }
    branch_occurrence_by_id: dict[str, str] = {}
    path_ids: set[str] = set()
    path_source_occurrence: dict[str, str] = {}
    flow_occurrence_ids = {
        row["candidate_occurrence_id"]
        for row in occurrence_rows
        if row["occurrence_kind_candidate"] == "flow_branch_label"
    }
    covered_flow_occurrences: set[str] = set()
    for row in flow_rows:
        _expect_keys(
            row,
            {
                "candidate_flow_path_id",
                "source_candidate_occurrence_id",
                "candidate_branch_id",
                "candidate_parent_path",
                "candidate_branch_path",
                "basis_rule_id",
                "route_target_tokens",
                "adjudication_status",
            },
            "flow-path candidate row",
        )
        occurrence = occurrences.get(row["source_candidate_occurrence_id"])
        expected_branch_id = (
            None
            if occurrence is None
            else "rq-candidate-flow-branch:"
            + _canonical_digest(
                [
                    occurrence["source_document_id"],
                    occurrence["interview_wave"],
                    occurrence["candidate_occurrence_id"],
                ]
            )
        )
        expected_id = "rq-candidate-flow-path:" + _canonical_digest(
            [
                row["source_candidate_occurrence_id"],
                row["candidate_branch_id"],
                row["candidate_parent_path"],
                row["candidate_branch_path"],
                row["basis_rule_id"],
                row["route_target_tokens"],
            ]
        )
        if (
            occurrence is None
            or occurrence["occurrence_kind_candidate"] != "flow_branch_label"
            or row["candidate_branch_id"] != expected_branch_id
            or row["candidate_flow_path_id"] != expected_id
            or row["candidate_flow_path_id"] in path_ids
            or not row["candidate_parent_path"]
            or row["candidate_parent_path"][0] != FLOW_ROOT_ID
            or row["candidate_branch_path"]
            != [*row["candidate_parent_path"], row["candidate_branch_id"]]
            or row["candidate_branch_id"] in row["candidate_parent_path"]
            or len(row["candidate_parent_path"]) not in {1, 2}
            or row["basis_rule_id"]
            not in {
                "root_fallback_v1",
                "nearest_lower_indentation_v1",
                "nearest_logic_candidate_v1",
            }
            or (len(row["candidate_parent_path"]) == 1)
            != (row["basis_rule_id"] == "root_fallback_v1")
            or row["route_target_tokens"]
            != list(
                dict.fromkeys(
                    match.group(1)
                    for match in ROUTE_TARGET_RE.finditer(
                        occurrence["matched_text"]
                    )
                )
            )
            or row["adjudication_status"] != ADJUDICATION_STATUS
        ):
            raise ValueError("flow-path candidate row drift")
        if len(row["candidate_parent_path"]) == 2:
            parent_occurrence_id = branch_occurrence_by_id.get(
                row["candidate_parent_path"][1]
            )
            if (
                parent_occurrence_id is None
                or occurrence_order[parent_occurrence_id]
                >= occurrence_order[row["source_candidate_occurrence_id"]]
            ):
                raise ValueError("flow-path candidate parent order drift")
        path_ids.add(row["candidate_flow_path_id"])
        branch_occurrence_by_id[row["candidate_branch_id"]] = row[
            "source_candidate_occurrence_id"
        ]
        path_source_occurrence[row["candidate_flow_path_id"]] = row[
            "source_candidate_occurrence_id"
        ]
        covered_flow_occurrences.add(row["source_candidate_occurrence_id"])
    if covered_flow_occurrences != flow_occurrence_ids:
        raise ValueError("flow candidate occurrence cover drift")
    valid_context_ids = path_ids | {FLOW_ROOT_PATH_ID}
    for occurrence in occurrence_rows:
        context_ids = occurrence["candidate_flow_context_path_ids"]
        if (
            not context_ids
            or context_ids[0] != FLOW_ROOT_PATH_ID
            or len(context_ids) != len(set(context_ids))
            or not set(context_ids) <= valid_context_ids
        ):
            raise ValueError("occurrence flow-context candidates drift")
        for path_id in context_ids[1:]:
            if (
                occurrence_order[path_source_occurrence[path_id]]
                >= (occurrence_order[occurrence["candidate_occurrence_id"]])
            ):
                raise ValueError("flow-context candidate is not earlier")


def _validate_anchor_rows(
    anchor_rows: Sequence[Mapping[str, Any]],
    occurrence_rows: Sequence[Mapping[str, Any]],
    page_texts: Sequence[str] | None = None,
) -> None:
    occurrences = {
        row["candidate_occurrence_id"]: row for row in occurrence_rows
    }
    anchor_occurrences = {
        row["candidate_occurrence_id"]
        for row in occurrence_rows
        if row["occurrence_kind_candidate"] == "role_anchor"
        or row["occurrence_kind_candidate"] in ANCHOR_CLASSIFICATIONS
    }
    row_ids: set[str] = set()
    covered: set[str] = set()
    occurrence_order = {
        row["candidate_occurrence_id"]: position
        for position, row in enumerate(occurrence_rows)
    }
    page_lines = (
        None
        if page_texts is None
        else [
            {row["line_number"]: row for row in _physical_lines(page_text)}
            for page_text in page_texts
        ]
    )
    for row in anchor_rows:
        _expect_keys(
            row,
            {
                "candidate_anchor_classification_id",
                "source_candidate_occurrence_id",
                "node_domain_candidate",
                "classification_candidate",
                "parent_anchor_candidate_ids",
                "printed_identifier_candidate",
                "exact_label_sha256",
                "basis_rule_ids",
                "canonical_node_id",
                "adjudication_status",
            },
            "anchor-classification candidate row",
        )
        occurrence = occurrences.get(row["source_candidate_occurrence_id"])
        if occurrence is None:
            raise ValueError("anchor candidate occurrence is unresolved")
        kind = occurrence["occurrence_kind_candidate"]
        if kind == "role_anchor":
            expected_domain = "role"
            expected_classification = _role_classification(
                occurrence["matched_text"]
            )
        else:
            expected_domain, expected_classification = (
                ANCHOR_CLASSIFICATIONS.get(kind, (None, None))
            )
        expected_id = (
            "rq-candidate-anchor-classification:"
            + _canonical_digest(
                [
                    row["source_candidate_occurrence_id"],
                    row["node_domain_candidate"],
                    row["classification_candidate"],
                    row["parent_anchor_candidate_ids"],
                    row["printed_identifier_candidate"],
                    row["exact_label_sha256"],
                    row["basis_rule_ids"],
                ]
            )
        )
        if (
            occurrence is None
            or row["source_candidate_occurrence_id"] not in anchor_occurrences
            or row["node_domain_candidate"] != expected_domain
            or row["classification_candidate"] != expected_classification
            or row["candidate_anchor_classification_id"] != expected_id
            or row["candidate_anchor_classification_id"] in row_ids
            or row["exact_label_sha256"] != occurrence["matched_utf8_sha256"]
            or row["basis_rule_ids"] != occurrence["detector_rule_ids"]
            or row["canonical_node_id"] is not None
            or row["adjudication_status"] != ADJUDICATION_STATUS
            or any(
                parent not in anchor_occurrences
                for parent in row["parent_anchor_candidate_ids"]
            )
            or any(
                occurrence_order[parent]
                >= occurrence_order[row["source_candidate_occurrence_id"]]
                for parent in row["parent_anchor_candidate_ids"]
            )
        ):
            raise ValueError("anchor-classification candidate row drift")
        if page_lines is not None:
            line_text = page_lines[occurrence["page_number"] - 1][
                occurrence["line_number"]
            ]["text"]
            if row["printed_identifier_candidate"] != _printed_identifier(
                line_text
            ):
                raise ValueError("printed identifier candidate drift")
        row_ids.add(row["candidate_anchor_classification_id"])
        covered.add(row["source_candidate_occurrence_id"])
    if covered != anchor_occurrences:
        raise ValueError("anchor-classification occurrence cover drift")


def batch_bounds(
    batch_index: int, document_count: int = 81
) -> tuple[int, int]:
    batch_count = (document_count + BATCH_SIZE - 1) // BATCH_SIZE
    if not 1 <= batch_index <= batch_count:
        raise ValueError("candidate batch index outside fixed batch domain")
    first = (batch_index - 1) * BATCH_SIZE + 1
    return first, min(first + BATCH_SIZE - 1, document_count)


def batch_directory(batch_index: int) -> Path:
    first, last = batch_bounds(batch_index)
    return CANDIDATE_ROOT / (
        f"batch_{batch_index:02d}_documents_{first:03d}_{last:03d}"
    )


def document_output_path(position: int, document: Mapping[str, Any]) -> Path:
    batch_index = (position - 1) // BATCH_SIZE + 1
    stem = Path(document["canonical_source_path"]).stem
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", stem)
    return batch_directory(batch_index) / (
        f"document_{position:03d}_{safe_stem}_candidates_v1.json"
    )


def batch_manifest_path(batch_index: int) -> Path:
    return batch_directory(batch_index) / "batch_manifest_v1.json"


def render_document_candidates(value: Mapping[str, Any]) -> bytes:
    return source_tools.canonical_json_bytes(value)


def build_batch(
    replay_artifact: Mapping[str, Any],
    batch_index: int,
    capture_root: Path = source_tools.DEFAULT_CAPTURE_ROOT,
) -> tuple[list[tuple[Path, bytes]], dict[str, Any]]:
    first, last = batch_bounds(batch_index)
    documents = replay_artifact["source_document_replay"][
        "questionnaire_documents"
    ]
    outputs: list[tuple[Path, bytes]] = []
    identity_rows: list[dict[str, Any]] = []
    counts = Counter()
    page_count = 0
    for position in range(first, last + 1):
        artifact = build_document_candidates(
            replay_artifact, position, capture_root
        )
        path = document_output_path(position, documents[position - 1])
        raw = render_document_candidates(artifact)
        outputs.append((path, raw))
        manifest = artifact["candidate_manifest"]
        page_count += manifest["page_count"]
        counts.update(manifest["candidate_occurrence_counts_by_kind"])
        identity_rows.append(
            {
                "document_source_position": position,
                "source_document_id": manifest["source_document_id"],
                "path": str(path.relative_to(ROOT)),
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
                "content_sha256": artifact["integrity"]["content_sha256"],
                "candidate_payload_sha256": manifest[
                    "candidate_payload_sha256"
                ],
            }
        )
    manifest_value: dict[str, Any] = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "artifact_id": f"rq-stage1-candidate-batch:{batch_index:02d}",
        "source_replay_identity": source_replay_identity(),
        "batch_index": batch_index,
        "document_source_position_start": first,
        "document_source_position_end": last,
        "document_count": len(identity_rows),
        "questionnaire_page_count": page_count,
        "candidate_occurrence_counts_by_kind": {
            kind: counts[kind] for kind in OCCURRENCE_KINDS
        },
        "document_artifact_rows": identity_rows,
        "document_artifact_domain_sha256": _canonical_digest(identity_rows),
        "candidate_nonselection_law": copy.deepcopy(
            CANDIDATE_NONSELECTION_LAW
        ),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": BATCH_STATUS,
    }
    manifest_value["integrity"]["content_sha256"] = _content_sha256(
        manifest_value
    )
    validate_batch_manifest(manifest_value, replay_artifact)
    return outputs, manifest_value


def validate_batch_manifest(
    value: Mapping[str, Any], replay_artifact: Mapping[str, Any]
) -> None:
    _expect_keys(
        value,
        {
            "schema_version",
            "artifact_id",
            "source_replay_identity",
            "batch_index",
            "document_source_position_start",
            "document_source_position_end",
            "document_count",
            "questionnaire_page_count",
            "candidate_occurrence_counts_by_kind",
            "document_artifact_rows",
            "document_artifact_domain_sha256",
            "candidate_nonselection_law",
            "integrity",
            "status",
        },
        "candidate batch manifest",
    )
    first, last = batch_bounds(value["batch_index"])
    rows = value["document_artifact_rows"]
    documents = replay_artifact["source_document_replay"][
        "questionnaire_documents"
    ]
    expected_paths = [
        str(
            document_output_path(
                position, documents[position - 1]
            ).relative_to(ROOT)
        )
        for position in range(first, last + 1)
    ]
    row_keys = {
        "document_source_position",
        "source_document_id",
        "path",
        "byte_size",
        "raw_sha256",
        "content_sha256",
        "candidate_payload_sha256",
    }
    batch_document_ids = {
        documents[position - 1]["source_document_id"]
        for position in range(first, last + 1)
    }
    expected_page_count = sum(
        row["page_count"]
        for row in replay_artifact["questionnaire_page_replay"][
            "document_page_rows"
        ]
        if row["source_document_id"] in batch_document_ids
    )
    if (
        value["schema_version"] != BATCH_SCHEMA_VERSION
        or value["artifact_id"]
        != f"rq-stage1-candidate-batch:{value['batch_index']:02d}"
        or value["source_replay_identity"] != source_replay_identity()
        or value["document_source_position_start"] != first
        or value["document_source_position_end"] != last
        or value["document_count"] != len(rows)
        or value["document_count"] != last - first + 1
        or [row["document_source_position"] for row in rows]
        != list(range(first, last + 1))
        or [row["source_document_id"] for row in rows]
        != [
            documents[position - 1]["source_document_id"]
            for position in range(first, last + 1)
        ]
        or any(set(row) != row_keys for row in rows)
        or [row["path"] for row in rows] != expected_paths
        or any(
            row["byte_size"] <= 0
            or len(row["raw_sha256"]) != 64
            or len(row["content_sha256"]) != 64
            or len(row["candidate_payload_sha256"]) != 64
            for row in rows
        )
        or value["questionnaire_page_count"] != expected_page_count
        or set(value["candidate_occurrence_counts_by_kind"])
        != set(OCCURRENCE_KINDS)
        or any(
            not isinstance(count, int) or isinstance(count, bool) or count < 0
            for count in value["candidate_occurrence_counts_by_kind"].values()
        )
        or value["document_artifact_domain_sha256"] != _canonical_digest(rows)
        or value["candidate_nonselection_law"] != CANDIDATE_NONSELECTION_LAW
        or value["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": _content_sha256(value),
        }
        or value["status"] != BATCH_STATUS
    ):
        raise ValueError("candidate batch manifest drift")


def _era_id_for_wave(wave: int) -> str:
    matches = [
        spec["era_id"]
        for spec in source_tools.ERA_SPECS
        if wave in spec["interview_waves"]
    ]
    if len(matches) != 1:
        raise ValueError(f"wave {wave} does not resolve to one fixed era")
    return matches[0]


def _read_candidate_artifact(
    identity: Mapping[str, Any], replay_artifact: Mapping[str, Any]
) -> dict[str, Any]:
    path = ROOT / identity["path"]
    raw = path.read_bytes()
    if (
        len(raw) != identity["byte_size"]
        or _sha256(raw) != identity["raw_sha256"]
    ):
        raise ValueError(f"candidate artifact identity drift: {path}")
    value = source_tools.strict_parse_document(raw, str(path))
    if not isinstance(value, dict):
        raise ValueError(f"candidate artifact is not an object: {path}")
    if raw != source_tools.canonical_json_bytes(value):
        raise ValueError(f"candidate artifact is not canonical: {path}")
    validate_document_candidates(value, replay_artifact)
    if value["integrity"]["content_sha256"] != identity["content_sha256"]:
        raise ValueError(f"candidate artifact content drift: {path}")
    return value


def _read_batch_manifest(
    batch_index: int, replay_artifact: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    path = batch_manifest_path(batch_index)
    raw = path.read_bytes()
    value = source_tools.strict_parse_document(raw, str(path))
    if not isinstance(value, dict):
        raise ValueError(f"candidate batch manifest is not an object: {path}")
    if raw != source_tools.canonical_json_bytes(value):
        raise ValueError(f"candidate batch manifest is not canonical: {path}")
    validate_batch_manifest(value, replay_artifact)
    return raw, value


def build_candidate_index(
    replay_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble the exact nine-batch/81-document candidate census."""

    batch_rows: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    global_counts: Counter[str] = Counter()
    global_page_count = 0
    global_flow_count = 0
    global_anchor_count = 0
    for batch_index in range(1, 10):
        raw, batch = _read_batch_manifest(batch_index, replay_artifact)
        batch_path = batch_manifest_path(batch_index)
        batch_rows.append(
            {
                "batch_index": batch_index,
                "path": str(batch_path.relative_to(ROOT)),
                "byte_size": len(raw),
                "raw_sha256": _sha256(raw),
                "content_sha256": batch["integrity"]["content_sha256"],
                "document_count": batch["document_count"],
                "questionnaire_page_count": batch["questionnaire_page_count"],
                "candidate_occurrence_counts_by_kind": batch[
                    "candidate_occurrence_counts_by_kind"
                ],
            }
        )
        observed_batch_counts: Counter[str] = Counter()
        observed_batch_pages = 0
        for identity in batch["document_artifact_rows"]:
            artifact = _read_candidate_artifact(identity, replay_artifact)
            manifest = artifact["candidate_manifest"]
            if (
                identity["candidate_payload_sha256"]
                != manifest["candidate_payload_sha256"]
            ):
                raise ValueError("batch and document candidate payload drift")
            observed_batch_counts.update(
                manifest["candidate_occurrence_counts_by_kind"]
            )
            observed_batch_pages += manifest["page_count"]
            global_counts.update(
                manifest["candidate_occurrence_counts_by_kind"]
            )
            global_page_count += manifest["page_count"]
            global_flow_count += manifest["candidate_flow_path_count"]
            global_anchor_count += manifest[
                "candidate_anchor_classification_count"
            ]
            document_rows.append(
                {
                    **copy.deepcopy(identity),
                    "era_id": _era_id_for_wave(manifest["interview_wave"]),
                    "interview_wave": manifest["interview_wave"],
                    "canonical_source_path": manifest["canonical_source_path"],
                    "page_count": manifest["page_count"],
                    "empty_candidate_page_count": manifest[
                        "empty_candidate_page_count"
                    ],
                    "candidate_occurrence_count": manifest[
                        "candidate_occurrence_count"
                    ],
                    "candidate_occurrence_counts_by_kind": manifest[
                        "candidate_occurrence_counts_by_kind"
                    ],
                    "candidate_flow_path_count": manifest[
                        "candidate_flow_path_count"
                    ],
                    "candidate_anchor_classification_count": manifest[
                        "candidate_anchor_classification_count"
                    ],
                }
            )
        if (
            observed_batch_pages != batch["questionnaire_page_count"]
            or {kind: observed_batch_counts[kind] for kind in OCCURRENCE_KINDS}
            != batch["candidate_occurrence_counts_by_kind"]
        ):
            raise ValueError("candidate batch census differs from documents")

    if [row["document_source_position"] for row in document_rows] != list(
        range(1, 82)
    ) or global_page_count != 10_190:
        raise ValueError("global candidate document/page cover drift")
    era_rows: list[dict[str, Any]] = []
    for spec in source_tools.ERA_SPECS:
        rows = [
            row for row in document_rows if row["era_id"] == spec["era_id"]
        ]
        counts: Counter[str] = Counter()
        for row in rows:
            counts.update(row["candidate_occurrence_counts_by_kind"])
        if (
            len(rows) != spec["questionnaire_document_count"]
            or sum(row["page_count"] for row in rows)
            != spec["questionnaire_page_count"]
        ):
            raise ValueError(f"{spec['era_id']} candidate cover drift")
        era_rows.append(
            {
                "era_id": spec["era_id"],
                "interview_waves": list(spec["interview_waves"]),
                "questionnaire_document_count": len(rows),
                "questionnaire_page_count": sum(
                    row["page_count"] for row in rows
                ),
                "candidate_occurrence_count": sum(counts.values()),
                "candidate_occurrence_counts_by_kind": {
                    kind: counts[kind] for kind in OCCURRENCE_KINDS
                },
                "candidate_flow_path_count": sum(
                    row["candidate_flow_path_count"] for row in rows
                ),
                "candidate_anchor_classification_count": sum(
                    row["candidate_anchor_classification_count"]
                    for row in rows
                ),
                "document_candidate_payload_domain_sha256": (
                    _canonical_digest(
                        [row["candidate_payload_sha256"] for row in rows]
                    )
                ),
            }
        )

    value: dict[str, Any] = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "artifact_id": INDEX_SCHEMA_VERSION,
        "generator_spec_identity": copy.deepcopy(GENERATOR_SPEC_IDENTITY),
        "source_replay_identity": source_replay_identity(),
        "batch_manifest_rows": batch_rows,
        "batch_manifest_count": len(batch_rows),
        "batch_manifest_domain_sha256": _canonical_digest(batch_rows),
        "document_candidate_manifest_rows": document_rows,
        "document_candidate_manifest_count": len(document_rows),
        "document_candidate_manifest_domain_sha256": _canonical_digest(
            document_rows
        ),
        "questionnaire_page_count": global_page_count,
        "candidate_occurrence_count": sum(global_counts.values()),
        "candidate_occurrence_counts_by_kind": {
            kind: global_counts[kind] for kind in OCCURRENCE_KINDS
        },
        "candidate_flow_path_count": global_flow_count,
        "candidate_anchor_classification_count": global_anchor_count,
        "era_candidate_census_rows": era_rows,
        "era_candidate_census_domain_sha256": _canonical_digest(era_rows),
        "candidate_payload_domain_sha256": _canonical_digest(
            [row["candidate_payload_sha256"] for row in document_rows]
        ),
        "candidate_nonselection_law": copy.deepcopy(
            CANDIDATE_NONSELECTION_LAW
        ),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": INDEX_STATUS,
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_candidate_index(value, replay_artifact)
    return value


def validate_candidate_index(
    value: Mapping[str, Any], replay_artifact: Mapping[str, Any]
) -> None:
    document_rows = value["document_candidate_manifest_rows"]
    batch_rows = value["batch_manifest_rows"]
    era_rows = value["era_candidate_census_rows"]
    counts: Counter[str] = Counter()
    for row in document_rows:
        counts.update(row["candidate_occurrence_counts_by_kind"])
    if (
        value["schema_version"] != INDEX_SCHEMA_VERSION
        or value["artifact_id"] != INDEX_SCHEMA_VERSION
        or value["generator_spec_identity"] != GENERATOR_SPEC_IDENTITY
        or value["source_replay_identity"] != source_replay_identity()
        or value["batch_manifest_count"] != len(batch_rows)
        or value["batch_manifest_count"] != 9
        or [row["batch_index"] for row in batch_rows] != list(range(1, 10))
        or value["batch_manifest_domain_sha256"]
        != _canonical_digest(batch_rows)
        or value["document_candidate_manifest_count"] != len(document_rows)
        or value["document_candidate_manifest_count"] != 81
        or [row["document_source_position"] for row in document_rows]
        != list(range(1, 82))
        or [row["source_document_id"] for row in document_rows]
        != [
            row["source_document_id"]
            for row in replay_artifact["source_document_replay"][
                "questionnaire_documents"
            ]
        ]
        or value["document_candidate_manifest_domain_sha256"]
        != _canonical_digest(document_rows)
        or value["questionnaire_page_count"]
        != sum(row["page_count"] for row in document_rows)
        or value["questionnaire_page_count"] != 10_190
        or value["candidate_occurrence_counts_by_kind"]
        != {kind: counts[kind] for kind in OCCURRENCE_KINDS}
        or value["candidate_occurrence_count"] != sum(counts.values())
        or value["candidate_flow_path_count"]
        != sum(row["candidate_flow_path_count"] for row in document_rows)
        or value["candidate_anchor_classification_count"]
        != sum(
            row["candidate_anchor_classification_count"]
            for row in document_rows
        )
        or len(era_rows) != 6
        or [row["era_id"] for row in era_rows]
        != [spec["era_id"] for spec in source_tools.ERA_SPECS]
        or value["era_candidate_census_domain_sha256"]
        != _canonical_digest(era_rows)
        or value["candidate_payload_domain_sha256"]
        != _canonical_digest(
            [row["candidate_payload_sha256"] for row in document_rows]
        )
        or value["candidate_nonselection_law"] != CANDIDATE_NONSELECTION_LAW
        or value["integrity"]
        != {
            "canonicalization": CANONICALIZATION,
            "content_sha256": _content_sha256(value),
        }
        or value["status"] != INDEX_STATUS
    ):
        raise ValueError("global candidate index drift")


def _write_or_check(path: Path, raw: bytes, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_bytes() != raw:
            raise ValueError(f"candidate output does not reproduce: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def write_batch(
    replay_artifact: Mapping[str, Any],
    batch_index: int,
    capture_root: Path,
    check: bool,
) -> None:
    outputs, manifest = build_batch(replay_artifact, batch_index, capture_root)
    for path, raw in outputs:
        _write_or_check(path, raw, check)
    _write_or_check(
        batch_manifest_path(batch_index),
        source_tools.canonical_json_bytes(manifest),
        check,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--batch", type=int)
    mode.add_argument("--all-batches", action="store_true")
    mode.add_argument("--index", action="store_true")
    parser.add_argument(
        "--capture-root", type=Path, default=source_tools.DEFAULT_CAPTURE_ROOT
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    # The complete replay is validated before a fixed output shard is chosen.
    replay_artifact = load_source_replay()
    if args.index:
        _write_or_check(
            INDEX_PATH,
            source_tools.canonical_json_bytes(
                build_candidate_index(replay_artifact)
            ),
            args.check,
        )
        return 0
    batch_indices = range(1, 10) if args.all_batches else (args.batch,)
    for batch_index in batch_indices:
        write_batch(
            replay_artifact,
            batch_index,
            args.capture_root,
            args.check,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
