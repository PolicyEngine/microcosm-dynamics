#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 31.

The 118-page 1983 QxQ was reviewed page by page from the authenticated
Poppler text. This helper encodes the retained employment, work-history, and
annual-earnings source regions. It reruns the stage-1 lexical detectors over
authenticated bytes but never opens the committed candidate artifact;
candidate rows are joined only by the sealed document annotation builder.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_031_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]

F = "flow_branch_label"
R = "role_anchor"
J = "job_anchor"
M = "remuneration_component_anchor"
T = "role_total_anchor"
FA = "farm_aggregate_anchor"
BA = "business_aggregate_anchor"
C = "context_anchor"
P = "field_purpose_prompt"
A = "repeat_or_alias_instruction"

# The 118 physical pages were partitioned during the independent visual and
# exact-text review.  FORM_PAGES are printed questionnaire screens;
# QBYQ_PAGES are the paired question-by-question objectives (including their
# numbered blank leaves).  Pages 1-3 and 114-118 are front matter, education,
# thumbnail, and interview-administration material and therefore contribute
# no R_Q occurrence atoms despite containing generic role/work vocabulary.
FORM_PAGES = frozenset(
    {
        4,
        6,
        8,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        32,
        34,
        36,
        38,
        40,
        42,
        44,
        46,
        48,
        50,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        66,
        68,
        70,
        72,
        *range(74, 87),
        *range(89, 95),
        96,
        98,
        *range(101, 111),
        113,
    }
)
QBYQ_PAGES = frozenset(
    {
        5,
        7,
        *range(9, 12),
        13,
        15,
        17,
        19,
        21,
        23,
        25,
        27,
        29,
        31,
        33,
        35,
        37,
        39,
        41,
        43,
        45,
        47,
        49,
        51,
        53,
        55,
        57,
        59,
        61,
        63,
        65,
        67,
        69,
        71,
        73,
        87,
        88,
        95,
        97,
        99,
        100,
        111,
        112,
    }
)
EXCLUDED_PAGES = frozenset({1, 2, 3, *range(114, 119)})
SEMANTIC_PAGES = FORM_PAGES | QBYQ_PAGES
if (
    FORM_PAGES & QBYQ_PAGES
    or SEMANTIC_PAGES & EXCLUDED_PAGES
    or SEMANTIC_PAGES | EXCLUDED_PAGES != frozenset(range(1, 119))
):
    raise RuntimeError("document 31 physical-page partition drift")

ALL_KINDS = frozenset(annotation.OCCURRENCE_KINDS)

FLOW_EXCLUSION_MARKERS = (
    "IF NECESSARY",
    "IF VOLUNTEERED",
    "IF ZERO",
    "IF NOT CLEAR",
    "IF R DOESN'T UNDERSTAND",
    "IF R DOES NOT UNDERSTAND",
    "IF DOESN'T SPECIFY",
    "IF DOES NOT SPECIFY",
    "IF IN DOUBT",
    "IF EITHER",
)
FLOW_ACTION_MARKERS = (
    "GO TO",
    "G0 TO",
    "G0 T0",
    "TURN TO",
    "TURN TOP",
    "NEXT PAGE",
    "SKIP TO",
    "ASK SECTION",
    "ASK B",
    "ASK C",
    "ASK D",
    "ASK E",
    "ALL OTHERS",
    "OTHERWISE",
    "DO NOT ASK",
    "DON'T ASK",
)

# These screens discuss fringe-benefit availability or pension-plan design,
# not a covered-earnings job, amount, total, context, or purpose construct.
# Their worklike vocabulary is therefore dispositioned as out of R_Q scope
# after whole-page review.  Routes into and out of these screens are still
# represented by the adjacent in-scope employment-section labels.
NONEMPLOYMENT_PAGES = frozenset(
    {
        14,
        15,
        *range(28, 38),
        75,
        *range(81, 86),
    }
)

COMPOSITE_WIFE_RE = re.compile(
    r"(?:WIFE(?:['\u2019]S)?|W!FE\s*1\s*S)\s*/\s*"
    r"(?:FEMALE\s+)?FRIEND(?:['\u2019]S)?",
    re.IGNORECASE,
)
SEE_REFERENCE_RE = re.compile(
    r"\bSEE\b[^\n]{0,100}(?:[A-HJ]\s*\d|SECTION\s+[A-HJ])",
    re.IGNORECASE,
)


def _review_id(
    source_document_id: str,
    page_texts: Sequence[str],
    page_number: int,
    start: int,
    end: int,
    kind: str,
) -> str:
    matched = page_texts[page_number - 1].encode("utf-8")[start:end]
    if not matched:
        raise ValueError("empty reviewer span")
    matched.decode("utf-8", errors="strict")
    return "rq-review-occurrence:" + annotation._canonical_digest(
        [
            source_document_id,
            page_number,
            start,
            end,
            kind,
            annotation._sha256(matched),
        ]
    )


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]
    interview_wave = document["interview_waves"][0]

    def page_size(page: int) -> int:
        return len(page_texts[page - 1].encode("utf-8"))

    def reviewed_windows(page: int) -> tuple[tuple[int, int], ...]:
        return ((0, page_size(page)),)

    def inside_reviewed_window(page: int, start: int, end: int) -> bool:
        return any(
            window_start <= start < end <= window_end
            for window_start, window_end in reviewed_windows(page)
        )

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        while start < end and raw[start : start + 1] in b" \t\r\n":
            start += 1
        while start < end and raw[end - 1 : end] in b" \t\r\n":
            end -= 1
        if not 0 <= start < end <= len(raw):
            raise ValueError(f"invalid reviewed span on page {page}")
        raw[start:end].decode("utf-8", errors="strict")
        return start, end

    def line_span(page: int, first: int, last: int) -> tuple[int, int]:
        lines = page_texts[page - 1].splitlines(keepends=True)
        if not 1 <= first <= last <= len(lines):
            raise ValueError(f"line range drift on page {page}")
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line.encode("utf-8")))
        return trim_span(page, offsets[first - 1], offsets[last])

    def byte_find(page: int, needle: str, start: int = 0) -> tuple[int, int]:
        raw = page_texts[page - 1].encode("utf-8")
        needle_raw = needle.encode("utf-8")
        position = raw.find(needle_raw, start)
        if position < 0:
            raise ValueError(
                f"source phrase not found on page {page}: {needle!r}"
            )
        return position, position + len(needle_raw)

    specs: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    def add(
        page: int,
        start: int,
        end: int,
        kind: str,
        routes: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source atom retained after whole-page review.",
        *,
        replace_overlap: bool = False,
    ) -> bool:
        start, end = trim_span(page, start, end)
        key = (page, start, end, kind)
        current = specs.get(key)
        if current is not None:
            current["routes"].update(tuple(route) for route in routes)
            return True
        overlaps = [
            existing
            for existing in specs
            if existing[0] == page
            and existing[3] == kind
            and existing[1] < end
            and start < existing[2]
        ]
        if overlaps and not replace_overlap:
            return False
        for existing in overlaps:
            del specs[existing]
        specs[key] = {
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "routes": {tuple(route) for route in routes},
            "note": note,
        }
        return True

    # Source-visible outer routing.  These exact labels establish the three
    # Head and three Wife employment-section alternatives plus the Section-J
    # wife-earnings screen.  The work-history sections are reachable by each
    # applicable alternative; no OCR-missing answer label is reconstructed.
    flow_defs: list[dict[str, Any]] = []

    def flow(
        symbol: str,
        page: int,
        start: int,
        end: int,
        parents: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source routing atom retained with reviewed ancestry.",
    ) -> None:
        start, end = trim_span(page, start, end)
        flow_defs.append(
            {
                "symbol": symbol,
                "page": page,
                "start": start,
                "end": end,
                "routes": [tuple(route) for route in parents],
                "note": note,
            }
        )

    flow(
        "head_looking_route_p4",
        4,
        *byte_find(4, "TURN TO P. 14,"),
    )
    flow(
        "head_other_direct_route_p4",
        4,
        *byte_find(4, "TURN TO P. 20,"),
    )
    flow(
        "head_working_route_p4",
        4,
        *byte_find(4, "GO TO A2 IF HEAD HAS JOB,"),
    )
    flow(
        "head_other_fallback_route_p4",
        4,
        *byte_find(4, "OTHERWISE TURN TO P. 20, SECTION C"),
    )

    flow(
        "head_looking_route_p6",
        6,
        *byte_find(6, "TURN TO P. 14."),
    )
    flow(
        "head_other_direct_route_p6",
        6,
        *byte_find(6, "TURN TO P. 20,"),
    )
    flow(
        "head_working_route_p6",
        6,
        *byte_find(6, "GO TO A2 IF HEAD HAS JOB,"),
    )
    flow(
        "head_other_fallback_route_p6",
        6,
        *byte_find(6, "OTHERWISE TURN TO P. 20, SECTION C"),
    )

    flow("wife_absent_route", 72, *line_span(72, 8, 8))
    flow("wife_looking_route", 72, *byte_find(72, "TURN TO P. 45,"))
    flow(
        "wife_other_direct_route",
        72,
        *byte_find(72, "TURN TO P. 51."),
    )
    flow("wife_working_route", 72, *byte_find(72, "GO TO E3 IF HAS JOB,"))
    flow(
        "wife_other_fallback_route",
        72,
        *byte_find(72, "OTHERWISE TURN TO P. 51, SECTION G"),
    )

    flow("wife_earnings_route", 110, *line_span(110, 10, 11))
    flow("head_earnings_direct_route", 110, *line_span(110, 13, 13))

    wife_earnings_base = (("wife_earnings_route",),)
    flow(
        "j2_skip_to_j5",
        110,
        *byte_find(110, "GOTO J5"),
        wife_earnings_base,
    )
    flow(
        "j3_no_to_j5",
        110,
        *line_span(110, 28, 28),
        wife_earnings_base,
    )
    j5_entry_routes = (
        ("wife_earnings_route",),
        ("wife_earnings_route", "j2_skip_to_j5"),
        ("wife_earnings_route", "j3_no_to_j5"),
    )
    flow(
        "j5_none_to_j8",
        110,
        *line_span(110, 37, 37),
        j5_entry_routes,
    )
    flow(
        "j6_no_to_j8",
        110,
        *line_span(110, 46, 46),
        j5_entry_routes,
    )
    j8_entry_routes = (
        ("head_earnings_direct_route",),
        *j5_entry_routes,
        *(route + ("j5_none_to_j8",) for route in j5_entry_routes),
        *(route + ("j6_no_to_j8",) for route in j5_entry_routes),
    )
    flow(
        "j8_none_to_j11",
        113,
        *line_span(113, 7, 7),
        j8_entry_routes,
    )
    flow(
        "j9_no_to_j11",
        113,
        *line_span(113, 13, 13),
        j8_entry_routes,
    )
    j11_entry_routes = (
        *j8_entry_routes,
        *(route + ("j8_none_to_j11",) for route in j8_entry_routes),
        *(route + ("j9_no_to_j11",) for route in j8_entry_routes),
    )

    flow_defs.sort(
        key=lambda row: (row["page"], row["start"], row["end"], row["symbol"])
    )
    for row in flow_defs:
        add(
            row["page"],
            row["start"],
            row["end"],
            F,
            row["routes"],
            row["note"],
            replace_overlap=True,
        )

    head_working_routes = (
        ("head_working_route_p4",),
        ("head_working_route_p6",),
    )
    head_looking_routes = (
        ("head_looking_route_p4",),
        ("head_looking_route_p6",),
    )
    head_other_routes = (
        ("head_other_direct_route_p4",),
        ("head_other_fallback_route_p4",),
        ("head_other_direct_route_p6",),
        ("head_other_fallback_route_p6",),
    )
    head_history_routes = (
        *head_working_routes,
        *head_looking_routes,
        *head_other_routes,
    )
    wife_working_route = (("wife_working_route",),)
    wife_looking_route = (("wife_looking_route",),)
    wife_other_routes = (
        ("wife_other_direct_route",),
        ("wife_other_fallback_route",),
    )
    wife_history_routes = (
        ("wife_working_route",),
        ("wife_looking_route",),
        *wife_other_routes,
    )
    head_a2_starts = {
        4: byte_find(4, "• A2.")[0],
        6: byte_find(6, "• A2.")[0],
        7: byte_find(7, "A2.")[0],
    }
    wife_e3_start = byte_find(72, "• E3.")[0]
    j5_start = line_span(110, 33, 33)[0]
    j11_start = line_span(113, 19, 19)[0]

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if page == 4 and start >= head_a2_starts[4]:
            return (("head_working_route_p4",),)
        if page == 6 and start >= head_a2_starts[6]:
            return (("head_working_route_p6",),)
        if page == 7 and start >= head_a2_starts[7]:
            return head_working_routes
        if 8 <= page <= 37:
            return head_working_routes
        if 38 <= page <= 47:
            return head_looking_routes
        if 48 <= page <= 51:
            return head_other_routes
        if 52 <= page <= 71:
            return head_history_routes
        if page == 72 and start >= wife_e3_start:
            return wife_working_route
        if 74 <= page <= 85:
            return wife_working_route
        if 86 <= page <= 93:
            return wife_looking_route
        if 94 <= page <= 97:
            return wife_other_routes
        if 98 <= page <= 109:
            return wife_history_routes
        if page == 110 and start >= j5_start:
            return j5_entry_routes
        if (page == 110 and start >= 387) or (page == 111 and start >= 583):
            return (("wife_earnings_route",),)
        if page == 113:
            return j11_entry_routes if start >= j11_start else j8_entry_routes
        return ((),)

    def allowed_kinds(page: int) -> frozenset[str]:
        del page
        return ALL_KINDS

    def retain_purpose(row: dict[str, Any]) -> bool:
        text = " ".join(row["matched_text"].split())
        folded = text.upper()
        rules = set(row["detector_rule_ids"])
        if any(
            marker in folded
            for marker in (
                "THIS IS A BLANK PAGE",
                "CONVERSION TABLE",
                "FOR OFFICE USE ONLY",
                "EXACT TIME NOW",
                "IF NECESSARY",
                "IF VOLUNTEERED",
            )
        ):
            return False
        # Question marks and interrogative words alone massively overgenerate
        # on the Q-by-Q examples and on continuation/answer lines.  Retain the
        # exact printed-identifier line here; important multiline earning and
        # alias prompts are independently re-sliced below.
        return "purpose_identifier_line_v1" in rules

    pension_or_fringe_form_pages = frozenset(
        {14, 28, 30, 32, 34, 36, 75, *range(81, 86)}
    )
    pension_or_fringe_qbyq_pages = frozenset({15, 29, 31, 33, 35, 37})
    noncomponent_pages = (
        pension_or_fringe_form_pages | pension_or_fringe_qbyq_pages
    )

    def printed_identifier(page: int, start: int) -> str | None:
        return annotation._source_printed_identifier(
            page_texts[page - 1], start
        )

    def line_text(page: int, start: int) -> str:
        for line in annotation.stage1_candidates._physical_lines(
            page_texts[page - 1]
        ):
            line_start = len(
                page_texts[page - 1][: line["start"]].encode("utf-8")
            )
            line_end = len(page_texts[page - 1][: line["end"]].encode("utf-8"))
            if line_start <= start < line_end:
                return " ".join(line["text"].split())
        raise ValueError(f"source atom does not resolve to page {page} line")

    def in_relevant_window(
        page: int,
        start: int,
        end: int,
        kind: str,
        text: str,
        row: dict[str, Any] | None = None,
    ) -> bool:
        if page not in SEMANTIC_PAGES or not inside_reviewed_window(
            page, start, end
        ):
            return False
        if page in NONEMPLOYMENT_PAGES:
            return False
        if kind not in allowed_kinds(page):
            return False
        folded = " ".join(text.upper().split())
        source_line = line_text(page, start).upper()
        identifier = printed_identifier(page, start)

        if kind in {T, FA, BA}:
            if kind == T:
                # The one source-visible role-total objective is independently
                # re-sliced below to include its complete printed clause.
                return False
            if kind == FA:
                # Farm/ranch tokens in this document are occupation examples,
                # not a farm-income aggregate amount construct.
                return False
            # Business/industry and self-employment status tokens are not
            # amount aggregates.  The J2 objective is the sole explicit
            # annual unincorporated-business earnings linkage.
            return kind == BA and page == 111 and start >= 1500

        if kind == F:
            if any(marker in folded for marker in FLOW_EXCLUSION_MARKERS):
                return False
            action_count = len(
                re.findall(
                    r"\b(?:GO|G0|TURN)\s+T(?:O|0|OP)\b",
                    folded,
                )
            )
            if action_count > 1 or re.search(
                r"\bTURN\s+T(?:O|OP)\s*(?:P\.)?[.\s]*$",
                folded,
            ):
                # Multi-column lines must be split into one exact route per
                # label below; targetless OCR fragments cannot be labels.
                return False
            return any(marker in folded for marker in FLOW_ACTION_MARKERS)

        if kind == P:
            if row is None:
                return True
            if page in noncomponent_pages:
                return False
            return retain_purpose(row)

        if kind == A:
            if any(
                marker in folded
                for marker in (
                    "SAME AS LAST JOB",
                    "SAME AS PRESENT JOB",
                    "SAME EMPLOYER",
                    "SAME JOB",
                    "ANOTHER JOB",
                    "OTHER JOB",
                    "EXTRA JOB",
                    "AGAIN",
                    "COMPARABLE TO SECTION",
                    "SEE THE OBJECTIVES",
                    "SEE OBJECTIVES",
                )
            ):
                return True
            return "SEE " in folded and any(
                token in folded
                for token in (
                    "A2",
                    "A3",
                    "A7",
                    "A8",
                    "A22",
                    "A27",
                    "A28",
                    "A38",
                    "A39",
                    "A40",
                    "C2",
                    "D15",
                )
            )

        if kind == J:
            if page in QBYQ_PAGES:
                bare = folded.strip(" .,;:?!()[]{}\"'") in {
                    "JOB",
                    "JOBS",
                    "EMPLOYER",
                    "EMPLOYERS",
                    "POSITION",
                    "POSITIONS",
                    "OCCUPATION",
                    "OCCUPATIONS",
                }
                strong = any(
                    marker in source_line
                    for marker in (
                        "MAIN JOB",
                        "LAST JOB",
                        "PRESENT JOB",
                        "PREVIOUS JOB",
                        "EXTRA JOB",
                        "SAME JOB",
                    )
                )
                if identifier is None and (bare or not strong):
                    return False

        if kind in {M, C}:
            if page in noncomponent_pages:
                return False
            if page in QBYQ_PAGES and identifier is None:
                return False

        if kind == R and page in QBYQ_PAGES:
            return identifier is not None or any(
                marker in source_line
                for marker in (
                    "SECTION ",
                    "APPLY TO THE HEAD",
                    "HEAD IS ",
                    "WIFE/FRIEND",
                    "WIFE'S/FRIEND'S",
                )
            )

        return True

    composite_role_ranges: dict[int, list[tuple[int, int]]] = {}
    for page in sorted(SEMANTIC_PAGES):
        page_text = page_texts[page - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        for match in COMPOSITE_WIFE_RE.finditer(page_text):
            start = offsets[match.start()]
            end = offsets[match.end()]
            if not in_relevant_window(page, start, end, R, match.group()):
                continue
            composite_role_ranges.setdefault(page, []).append((start, end))
            add(
                page,
                start,
                end,
                R,
                source_routes(page, start, end, R),
                "Composite Wife/quoted-Wife role independently re-sliced as one source atom.",
            )

    # Candidate-free lexical enumeration: only the detector implementation is
    # reused; no stage-1 candidate file is opened by this helper.
    for page, page_text in enumerate(page_texts, start=1):
        detected, _line_count = (
            annotation.stage1_candidates.detect_page_candidates(
                page_text,
                source_document_id=source_document_id,
                interview_wave=interview_wave,
                page_number=page,
            )
        )
        for row in detected:
            kind = row["occurrence_kind_candidate"]
            start = row["utf8_byte_start"]
            end = row["utf8_byte_end"]
            if kind == R and any(
                composite_start < end and start < composite_end
                for composite_start, composite_end in composite_role_ranges.get(
                    page, ()
                )
            ):
                continue
            if not in_relevant_window(
                page,
                start,
                end,
                kind,
                row["matched_text"],
                row,
            ):
                continue
            if kind == F and any(
                existing_page == page
                and existing_kind == F
                and existing_start < end
                and start < existing_end
                for existing_page, existing_start, existing_end, existing_kind in specs
            ):
                continue
            add(
                page,
                start,
                end,
                kind,
                source_routes(page, start, end, kind),
                "Reviewer-approved atom independently re-derived from exact page bytes.",
            )

    # Recover source-visible routing lines whose OCR spells the action as
    # TURN TOP., G0 T0, or another form outside the stage-1 flow grammar.
    # Limit this recovery to actual form pages so Q-by-Q prose containing
    # descriptive "go to" language does not become a branch label.
    for page in sorted(FORM_PAGES - NONEMPLOYMENT_PAGES):
        offset = 0
        for physical_line in page_texts[page - 1].splitlines(keepends=True):
            end = offset + len(physical_line.encode("utf-8"))
            folded = " ".join(physical_line.upper().split())
            action_count = len(
                re.findall(
                    r"\b(?:GO|G0|TURN)\s+T(?:O|0|OP)\b",
                    folded,
                )
            )
            if (
                folded
                and not any(
                    marker in folded for marker in FLOW_EXCLUSION_MARKERS
                )
                and any(marker in folded for marker in FLOW_ACTION_MARKERS)
                and action_count <= 1
                and not re.search(
                    r"\bTURN\s+T(?:O|OP)\s*(?:P\.)?[.\s]*$",
                    folded,
                )
            ):
                add(
                    page,
                    offset,
                    end,
                    F,
                    source_routes(page, offset, end, F),
                    "OCR-tolerant form-route recovery from exact physical-line bytes.",
                )
            offset = end

    # Explicit SEE cross-references are source repeat/alias evidence even when
    # the stage-1 repeat grammar misses them. Trimmed physical lines preserve
    # the exact printed context and are re-derived from authenticated bytes.
    for page in sorted(SEMANTIC_PAGES):
        raw = page_texts[page - 1].encode("utf-8")
        offset = 0
        for line in page_texts[page - 1].splitlines(keepends=True):
            end = offset + len(line.encode("utf-8"))
            text = line.strip()
            if (
                text
                and SEE_REFERENCE_RE.search(text)
                and inside_reviewed_window(page, offset, end)
                and page not in NONEMPLOYMENT_PAGES
            ):
                add(
                    page,
                    offset,
                    end,
                    A,
                    source_routes(page, offset, end, A),
                    "Explicit printed SEE cross-reference recovered from exact source bytes.",
                    replace_overlap=True,
                )
            offset = end
        if offset != len(raw):
            raise ValueError(f"physical-line denominator drift on page {page}")

    def manual(
        page: int,
        start: int,
        end: int,
        kinds: Sequence[str],
        note: str,
    ) -> None:
        """Replace detector fragments with a complete source-visible atom."""

        if page in NONEMPLOYMENT_PAGES:
            return

        for kind in kinds:
            add(
                page,
                start,
                end,
                kind,
                source_routes(page, start, end, kind),
                note,
                replace_overlap=True,
            )

    def manual_lines(
        page: int,
        first_line: int,
        last_line: int,
        kinds: Sequence[str],
        note: str,
    ) -> None:
        manual(page, *line_span(page, first_line, last_line), kinds, note)

    def manual_between(
        page: int,
        start_needle: str,
        end_needle: str,
        note: str,
        search_start: int = 0,
    ) -> None:
        start = byte_find(page, start_needle, search_start)[0]
        end = byte_find(page, end_needle, start)[1]
        manual(page, start, end, (F,), note)

    # Multi-column and line-wrapped routes need one source atom per printed
    # alternative.  These blocks replace combined detector lines and recover
    # targets that are complete in the source bytes only after a line wrap.
    manual_between(
        4,
        "TURN TO",
        "• 2, A7",
        "Complete wrapped A2 self-only route to A7.",
        1980,
    )
    manual_lines(8, 49, 50, (F,), "Complete wrapped A12 route to A18a.")
    manual(28, *byte_find(28, "GO TO A59"), (F,), "Atomic A56 YES route.")
    manual(
        28,
        *byte_find(28, "TURN TO P. 13. , A82"),
        (F,),
        "Atomic A56 DON'T KNOW route.",
    )
    manual_between(
        40,
        "o4. HAS HAD A J08~TURN TO",
        "p. 16' 829",
        "Complete B13 prior-job route to B29.",
    )
    manual(
        40,
        *byte_find(40, "TURN TO P. 16, 819"),
        (F,),
        "Atomic B13 last-worked route to B19.",
    )
    manual_between(
        40,
        "05· NEVER WORKED~TURN TO P. 32 ,",
        "SECTION E",
        "Complete B13 never-worked exit to Section E.",
    )
    manual(
        48,
        260,
        332,
        (F,),
        "OCR-tolerant complete C1 other-status route to C3.",
    )
    manual(
        56,
        903,
        938,
        (F,),
        "OCR-tolerant complete D15 route to D17.",
    )
    manual_lines(
        56,
        38,
        39,
        (F,),
        "Complete D19 pre-1981 route to D58.",
    )
    manual_lines(
        66,
        31,
        32,
        (F,),
        "Complete D55 no-other-main-jobs route to D58.",
    )
    manual_lines(
        89,
        14,
        15,
        (F,),
        "Complete F10a never-worked exit to Section J.",
    )
    manual(
        89,
        720,
        750,
        (F,),
        "Trimmed F10a last-worked route without adjacent answer-column text.",
    )
    manual_lines(
        102,
        36,
        37,
        (F,),
        "Complete H19 pre-1981 route to H58.",
    )
    manual_lines(
        104,
        10,
        10,
        (F,),
        "OCR-tolerant complete H35a no route to H35d.",
    )
    manual_lines(
        107,
        29,
        30,
        (F,),
        "Complete H55 no-other-main-jobs route to H58.",
    )
    manual_lines(
        108,
        39,
        39,
        (F,),
        "OCR-tolerant complete H64 no route to H66.",
    )

    # The rendered questionnaire also shows routes on pages 6, 12, 30, 40,
    # 89, 98, 102, and 105 whose target bytes are absent or interleaved in
    # Poppler replay.  No contiguous UTF-8 interval can encode those labels
    # without either omitting the target or absorbing a different branch, so
    # they are deliberately not minted as occurrences.

    # Source-proved objective reuse and cross-section recurrence.  Each block
    # is an exact physical-line slice; targets remain unresolved for the later
    # global alias stage.
    repeat_line_blocks: tuple[tuple[int, int, int, str], ...] = (
        (17, 10, 12, "A22-A23 explicitly reuse A7/A7a/A8 objectives."),
        (17, 13, 14, "A24-A27a explicitly reuse A10-A17 objectives."),
        (39, 6, 8, "B1 explicitly reuses the A7/A7a objectives."),
        (39, 16, 16, "B8-B10 explicitly reuse A7-A8 objectives."),
        (41, 4, 4, "B13b-B18a explicitly reuse A22-A27a objectives."),
        (43, 4, 4, "B19-B29 explicitly reuse A28-A38 objectives."),
        (45, 4, 4, "B30 explicitly cross-references A38."),
        (45, 6, 7, "B31a-B32 explicitly reuse A40b/A41 objectives."),
        (47, 4, 4, "B44 explicitly cross-references A39."),
        (47, 5, 5, "B45-B46 explicitly cross-reference A40b-A41."),
        (51, 4, 5, "C11a-C13a explicitly reuse C2-C8 for 1981."),
        (55, 4, 4, "D8-D9 explicitly cross-reference A2-A8."),
        (57, 8, 8, "D21-D22 explicitly cross-reference A8/A3."),
        (59, 4, 4, "D23-D24 explicitly cross-reference A7/A7a."),
        (61, 4, 4, "D35b-c explicitly cross-reference A8/A3."),
        (61, 6, 6, "D35d-e explicitly cross-reference A7/A7a."),
        (65, 6, 6, "D47b-c explicitly cross-reference A8/A3."),
        (65, 8, 8, "D47d-e explicitly cross-reference A7/A7a."),
        (73, 11, 15, "Sections E-H explicitly parallel Sections A-D."),
        (73, 16, 17, "E2 explicitly reuses the A1 employment definitions."),
        (87, 7, 7, "Section F explicitly states comparability to Section B."),
        (95, 6, 6, "Section G explicitly states comparability to Section C."),
        (99, 7, 7, "Section H explicitly states comparability to Section D."),
    )
    for page, first_line, last_line, note in repeat_line_blocks:
        manual_lines(page, first_line, last_line, (A,), note)

    # Printed same-job/same-employer labels and questions are the strongest
    # document-local alias evidence.  They are preserved as exact blocks but
    # are not bound to a canonical job in this nonauthority shard.
    alias_line_blocks: tuple[tuple[int, int, int, str], ...] = (
        (40, 25, 25, "Printed SAME AS LAST JOB instruction."),
        (56, 31, 32, "D18 explicit same-employer comparison."),
        (56, 44, 44, "D20 explicit previous-job same-employer branch."),
        (64, 7, 7, "D46 explicit later-main-job same-employer comparison."),
        (76, 29, 29, "Printed SAME AS PRESENT JOB instruction."),
        (89, 24, 24, "Printed SAME AS LAST JOB instruction."),
        (102, 4, 6, "H15 explicit prior-job/same-employer branch."),
        (102, 28, 29, "H18 explicit same-employer comparison."),
        (102, 41, 41, "H20 explicit previous-job same-employer branch."),
        (106, 10, 10, "H46 explicit later-main-job same-employer comparison."),
    )
    for page, first_line, last_line, note in alias_line_blocks:
        manual_lines(page, first_line, last_line, (A,), note)

    # Annual-earnings purpose prompts are multiline semantic units.  Re-slice
    # them from exact bytes rather than promoting the detector's individual
    # question-mark and identifier lines.
    annual_prompt_blocks: tuple[tuple[int, int, int, str], ...] = (
        (110, 17, 18, "Complete J2 1982 Wife main-job wage/salary prompt."),
        (110, 22, 23, "Complete J3 1982 Wife additional-component prompt."),
        (110, 30, 30, "Complete J4 1982 Wife component-amount prompt."),
        (110, 33, 35, "Complete J5 1981 Wife main-job wage/salary prompt."),
        (110, 40, 41, "Complete J6 1981 Wife additional-component prompt."),
        (110, 48, 48, "Complete J7 1981 Wife component-amount prompt."),
        (113, 3, 5, "Complete J8 1982 Head main-job wage/salary prompt."),
        (113, 10, 11, "Complete J9 1982 Head additional-component prompt."),
        (113, 16, 16, "Complete J10 1982 Head component-amount prompt."),
        (113, 19, 21, "Complete J11 1981 Head main-job wage/salary prompt."),
        (113, 26, 27, "Complete J12 1981 Head additional-component prompt."),
        (113, 32, 34, "Complete J13 1981 Head component-amount prompt."),
    )
    for page, first_line, last_line, note in annual_prompt_blocks:
        manual_lines(page, first_line, last_line, (P,), note)

    manual_lines(
        111,
        8,
        14,
        (C,),
        "Complete work-hours/annual-income reconciliation context.",
    )
    manual_lines(
        111,
        17,
        28,
        (P,),
        "Complete J2 annual wage/salary objective block.",
    )
    manual_lines(
        111,
        27,
        28,
        (T,),
        "Exact total-1982-wages/salary role-total objective clause.",
    )
    manual_lines(
        111,
        32,
        34,
        (BA, C),
        "Annual unincorporated-business earnings linkage block.",
    )
    manual_lines(
        111,
        35,
        37,
        (P, A),
        "J3-J4 additional-income purpose and explicit no-double-count instruction.",
    )

    # Complete local control-flow ancestry.  The stage-1 detector identifies
    # labels, not their questionnaire targets, so retaining its parent-path
    # guesses would silently select a subset.  Resolve each in-scope shortcut
    # from the exact printed target and propagate every alternative through
    # the remainder of its destination scope.  A generic printed section exit
    # is a leaf in the ending tree and the destination section's source-visible
    # entry alternatives are its roots.  An explicit named midsection target
    # (for example, B13 -> D58) instead carries its ancestry into that target's
    # bounded scope.  This preserves printed routes without inventing
    # respondent-history products across independent Head, Wife, and
    # annual-earnings screens.
    section_page_ranges = {
        "A": range(4, 38),
        "B": range(38, 48),
        "C": range(48, 52),
        "D": range(52, 72),
        "E": range(72, 86),
        "F": range(86, 94),
        "G": range(94, 98),
        "H": range(98, 110),
        "J": range(110, 114),
    }

    def section_for_page(page: int) -> str | None:
        return next(
            (
                section
                for section, page_range in section_page_ranges.items()
                if page in page_range
            ),
            None,
        )

    target_aliases: dict[str, tuple[str, ...]] = {
        "A2": ("A2",),
        "A6": ("A6",),
        "A7": ("A7",),
        "A18a": ("A18A", "AL8A", "A1BA", "ALBA"),
        "A24": ("A24",),
        "A28": ("A28",),
        "A30": ("A30", "A3O"),
        "A32": ("A32", "A3Z"),
        "A34": ("A34",),
        "A36": ("A36",),
        "A38": ("A38", "A3B"),
        "A42": ("A42",),
        "A44": ("A44",),
        "A46": ("A46",),
        "A48": ("A48",),
        "A50": ("A50", "ASO"),
        "A52": ("A52",),
        "A56": ("A56",),
        "B5": ("B5", "85"),
        "B13": ("B13", "813"),
        "B15": ("B15", "815"),
        "B19": ("B19", "819"),
        "B21": ("B21", "821"),
        "B23": ("B23", "S23"),
        "B25": ("B25", "825"),
        "B27": ("B27", "827"),
        "B29": ("B29", "829"),
        "B33": ("B33", "833"),
        "C3": ("C3",),
        "C11": ("C11", "CII", "CLL"),
        "D4": ("D4", "04"),
        "D12": ("D12", "012"),
        "D17": ("D17", "017"),
        "D19": ("D19", "019"),
        "D23": ("D23", "023"),
        "D35d": ("D35D", "035D"),
        "D47d": ("D47D", "047D"),
        "D58": ("D58", "058"),
        "D62": ("D62", "062"),
        "D66": ("D66", "066"),
        "E7": ("E7",),
        "E15a": ("E15A", "EL5A"),
        "E20": ("E20", "E2O"),
        "E23": ("E23",),
        "E25": ("E25",),
        "E27": ("E27",),
        "E29": ("E29",),
        "E31": ("E31",),
        "E33": ("E33",),
        "E37": ("E37",),
        "E39": ("E39",),
        "E41": ("E41",),
        "E43": ("E43",),
        "E45": ("E45",),
        "E47": ("E47",),
        "E51": ("E51",),
        "F4": ("F4",),
        "F10a": ("F10A", "J10A", "J1OA"),
        "F13": ("F13", "FL3"),
        "F16": ("F16", "FL6"),
        "F18": ("F18",),
        "F20": ("F20",),
        "F22": ("F22",),
        "F24": ("F24",),
        "F26": ("F26",),
        "F30": ("F30",),
        "F32": ("F32",),
        "F34": ("F34",),
        "F36": ("F36",),
        "F38": ("F38",),
        "F40": ("F40",),
        "G3": ("G3",),
        "G11": ("G11", "GII", "GLL"),
        "H4": ("H4",),
        "H17": ("H17", "HT7"),
        "H19": ("H19",),
        "H23": ("H23",),
        "H35d": ("H35D",),
        "H47d": ("H47D",),
        "H58": ("H58", "H5TS"),
        "H62": ("H62",),
        "H66": ("H66",),
    }

    target_line_specs: dict[str, tuple[tuple[int, int], ...]] = {
        "A2": ((4, 26), (6, 30)),
        "A6": ((4, 56), (6, 55)),
        "A7": ((8, 3), (12, 3)),
        "A18a": ((14, 3),),
        "A24": ((16, 31),),
        "A28": ((18, 5), (20, 4)),
        "A30": ((18, 16), (20, 15)),
        "A32": ((18, 25), (20, 25)),
        "A34": ((18, 34), (20, 33)),
        "A36": ((18, 42), (20, 42)),
        "A38": ((18, 52), (20, 52)),
        "A42": ((24, 3),),
        "A44": ((24, 20),),
        "A46": ((24, 27),),
        "A48": ((24, 40),),
        "A50": ((24, 47),),
        "A52": ((24, 61),),
        "A56": ((28, 5),),
        "B5": ((38, 22),),
        "B13": ((40, 3),),
        "B15": ((40, 30),),
        "B19": ((42, 4),),
        "B21": ((42, 12),),
        "B23": ((42, 23),),
        "B25": ((42, 33),),
        "B27": ((42, 43),),
        "B29": ((42, 54),),
        "B33": ((46, 4),),
        "C3": ((48, 10),),
        "C11": ((50, 5),),
        "D4": ((52, 35),),
        "D12": ((54, 45),),
        "D17": ((56, 26),),
        "D19": ((56, 35),),
        "D23": ((58, 3),),
        "D35d": ((60, 23),),
        "D47d": ((64, 38),),
        "D58": ((68, 4),),
        "D62": ((68, 26),),
        "D66": ((70, 3),),
        "E7": ((72, 53),),
        "E15a": ((75, 3),),
        "E20": ((76, 39),),
        "E23": ((77, 4),),
        "E25": ((77, 14),),
        "E27": ((77, 23),),
        "E29": ((77, 32),),
        "E31": ((77, 40),),
        "E33": ((77, 49),),
        "E37": ((79, 3),),
        "E39": ((79, 16),),
        "E41": ((79, 27),),
        "E43": ((79, 35),),
        "E45": ((79, 45),),
        "E47": ((79, 56),),
        "E51": ((81, 3),),
        "F4": ((86, 20),),
        "F10a": ((89, 3),),
        "F13": ((89, 32),),
        "F16": ((90, 4),),
        "F18": ((90, 13),),
        "F20": ((90, 19),),
        "F22": ((90, 28),),
        "F24": ((90, 36),),
        "F26": ((90, 46),),
        "F30": ((92, 3),),
        "F32": ((92, 14),),
        "F34": ((92, 22),),
        "F36": ((92, 31),),
        "F38": ((92, 38),),
        "F40": ((92, 48),),
        "G3": ((94, 16),),
        "G11": ((96, 5),),
        "H4": ((98, 30),),
        "H17": ((102, 24),),
        "H19": ((102, 33),),
        "H23": ((103, 4),),
        "H35d": ((104, 28),),
        "H47d": ((106, 38),),
        "H58": ((108, 5),),
        "H62": ((108, 27),),
        "H66": ((109, 3),),
    }
    target_locations = {
        target: tuple(
            (page, line_span(page, line, line)[0]) for page, line in line_specs
        )
        for target, line_specs in target_line_specs.items()
    }
    target_scope_end_lines: dict[str, tuple[int, int] | None] = {
        "A6": (8, 3),
        "A7": (8, 18),
        "A18a": (16, 3),
        **{
            target: (22, 4)
            for target in {
                "A24",
                "A28",
                "A30",
                "A32",
                "A34",
                "A36",
                "A38",
            }
        },
        **{
            target: (26, 5)
            for target in {"A42", "A44", "A46", "A48", "A50", "A52"}
        },
        "A56": None,
        "B5": (38, 27),
        "B13": (42, 4),
        "B15": (42, 4),
        **{
            target: (44, 7)
            for target in {"B19", "B21", "B23", "B25", "B27", "B29"}
        },
        "B33": (46, 4),
        "C3": (50, 5),
        "C11": None,
        "D4": (54, 4),
        "D12": (56, 3),
        "D17": (58, 44),
        "D19": (58, 44),
        "D23": (58, 44),
        "D35d": (62, 20),
        "D47d": (66, 25),
        "D58": (68, 26),
        "D62": (70, 3),
        "D66": None,
        "E7": (74, 3),
        "E15a": (76, 3),
        **{
            target: (78, 3)
            for target in {
                "E20",
                "E23",
                "E25",
                "E27",
                "E29",
                "E31",
                "E33",
            }
        },
        **{
            target: (80, 3)
            for target in {"E37", "E39", "E41", "E43", "E45", "E47"}
        },
        "E51": None,
        "F4": (86, 22),
        **{
            target: (91, 4)
            for target in {
                "F10a",
                "F13",
                "F16",
                "F18",
                "F20",
                "F22",
                "F24",
                "F26",
            }
        },
        **{
            target: (93, 3)
            for target in {"F30", "F32", "F34", "F36", "F38", "F40"}
        },
        "G3": (96, 5),
        "G11": None,
        "H4": (101, 3),
        "H17": (103, 41),
        "H19": (103, 41),
        "H23": (103, 41),
        "H35d": (105, 16),
        "H47d": (107, 23),
        "H58": (108, 27),
        "H62": (109, 3),
        "H66": None,
    }
    target_scope_ends = {
        target: (
            None
            if line_spec is None
            else (
                line_spec[0],
                line_span(line_spec[0], line_spec[1], line_spec[1])[0],
            )
        )
        for target, line_spec in target_scope_end_lines.items()
    }

    known_flow_symbol_by_key = {
        (row["page"], row["start"], row["end"]): row["symbol"]
        for row in flow_defs
    }

    def compact_flow_text(row: dict[str, Any]) -> str:
        raw = page_texts[row["page"] - 1].encode("utf-8")
        text = raw[row["start"] : row["end"]].decode("utf-8", errors="strict")
        return re.sub(r"[^A-Z0-9?]", "", text.upper())

    def flow_target(row: dict[str, Any]) -> str | None:
        compact = compact_flow_text(row)
        for section in section_page_ranges:
            if f"SECTION{section}" in compact:
                return f"SECTION_{section}"
        if row["page"] == 76 and row["start"] == 878:
            # The rendered answer arrow visibly resolves to E23; Poppler
            # truncates its printed page/question destination to "P. 3,".
            return "E23"
        if row["page"] == 16 and row["start"] == 1382:
            # The rendered A22 loop arrow returns to the A24 pay-status
            # screen; OCR drops the printed 4 from its target.
            return "A24"
        if row["page"] == 62 and compact.endswith("P3005"):
            return "D58"
        if row["page"] == 66 and row["start"] == 1630:
            return "D58"
        if row["page"] == 92 and compact.endswith("GOTOF3"):
            return "F34"
        matches: list[tuple[int, int, str]] = []
        for target, aliases in target_aliases.items():
            for alias in aliases:
                position = compact.rfind(alias)
                if position >= 0:
                    matches.append((position, len(alias), target))
        if not matches:
            return None
        _position, _length, target = max(matches)
        return target

    # A flow occurrence with no recoverable destination cannot support a
    # complete path.  The sole such form fragment is the OCR-truncated E17b
    # "TURN TO P. 3," line; its complete E23 alternatives remain elsewhere.
    for key, row in list(specs.items()):
        if (
            row["kind"] == F
            and (row["page"], row["start"], row["end"])
            not in known_flow_symbol_by_key
            and row["page"] < 110
            and flow_target(row) is None
        ):
            del specs[key]

    def local_flow_symbol(row: dict[str, Any]) -> str:
        return (
            f"local_flow_p{row['page']:03d}_"
            f"b{row['start']:05d}_{row['end']:05d}"
        )

    def selected_target_locations(
        source_page: int, target: str
    ) -> tuple[tuple[int, int], ...]:
        locations = target_locations[target]
        if target == "A6" and source_page in {4, 6}:
            return tuple(row for row in locations if row[0] == source_page)
        if target == "A7" and source_page in {4, 6}:
            target_page = 8 if source_page == 4 else 12
            return tuple(row for row in locations if row[0] == target_page)
        if target in {"A28", "A30", "A32", "A34", "A36", "A38"}:
            if source_page in {8, 18}:
                return tuple(row for row in locations if row[0] == 18)
            if source_page in {12, 20}:
                return tuple(row for row in locations if row[0] == 20)
        return locations

    def schedule_applies(
        schedule: dict[str, Any], page: int, start: int
    ) -> bool:
        if section_for_page(page) != schedule["section"]:
            return False
        if (
            schedule["scope_end"] is not None
            and (page, start) >= schedule["scope_end"]
        ):
            return False
        target = schedule["target"]
        source_page = schedule["source_page"]
        for target_page, target_start in schedule["locations"]:
            if target == "A6" and source_page in {4, 6}:
                if (
                    page == source_page
                    and start >= target_start
                    or 7 <= page <= 37
                ):
                    return True
                continue
            if target_page in {18, 20} and target.startswith("A"):
                if target_page == 18 and (
                    page == 18
                    and start >= target_start
                    or page == 19
                    or 22 <= page <= 37
                ):
                    return True
                if target_page == 20 and (
                    page == 20
                    and start >= target_start
                    or page == 21
                    or 22 <= page <= 37
                ):
                    return True
                continue
            if (page, start) >= (target_page, target_start):
                return True
        return False

    schedules: list[dict[str, Any]] = []

    def planned_routes(row: dict[str, Any]) -> set[tuple[str, ...]]:
        routes = {
            tuple(route)
            for route in source_routes(
                row["page"], row["start"], row["end"], row["kind"]
            )
        }
        for schedule in schedules:
            if schedule_applies(schedule, row["page"], row["start"]):
                routes.update(schedule["routes"])
        return routes

    flow_specs = sorted(
        (row for row in specs.values() if row["kind"] == F),
        key=lambda row: (row["page"], row["start"], row["end"]),
    )
    for row in flow_specs:
        key = (row["page"], row["start"], row["end"])
        if key in known_flow_symbol_by_key:
            continue
        row["routes"] = planned_routes(row)
        target = flow_target(row)
        source_section = section_for_page(row["page"])
        if (
            target is None
            or target.startswith("SECTION_")
            or source_section is None
        ):
            continue
        destination_section = target[0]
        if destination_section not in section_page_ranges:
            raise ValueError(f"unknown destination section for {target}")
        locations = selected_target_locations(row["page"], target)
        forward_locations = tuple(
            location
            for location in locations
            if location > (row["page"], row["start"])
        )
        if not forward_locations:
            # Printed backward loops are retained as terminal branch evidence;
            # propagating them would create a prohibited cyclic path product.
            continue
        symbol = local_flow_symbol(row)
        schedules.append(
            {
                "section": destination_section,
                "target": target,
                "source_page": row["page"],
                "locations": forward_locations,
                "scope_end": target_scope_ends[target],
                "routes": {
                    parent_route + (symbol,) for parent_route in row["routes"]
                },
            }
        )

    for row in specs.values():
        if row["page"] < 110 and row["kind"] != F:
            row["routes"] = planned_routes(row)

    for row in flow_specs:
        key = (row["page"], row["start"], row["end"])
        if key in known_flow_symbol_by_key:
            continue
        flow_defs.append(
            {
                "symbol": local_flow_symbol(row),
                "page": row["page"],
                "start": row["start"],
                "end": row["end"],
                "routes": sorted(row["routes"]),
                "note": row["note"],
            }
        )

    flow_defs.sort(
        key=lambda row: (row["page"], row["start"], row["end"], row["symbol"])
    )
    flow_by_symbol = {row["symbol"]: row for row in flow_defs}
    if len(flow_by_symbol) != len(flow_defs):
        raise ValueError("duplicate flow symbol")
    if len(flow_defs) != len(flow_specs):
        raise ValueError(
            "retained flow labels do not map one-to-one to definitions"
        )
    resolved_flow_paths: dict[str, list[list[str]]] = {}
    for row in flow_defs:
        review_occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            F,
        )
        row["review_id"] = review_occurrence_id
        resolved: list[list[str]] = []
        for symbolic_route in row["routes"]:
            prefix: list[str] = []
            for symbol in symbolic_route:
                parent = flow_by_symbol[symbol]
                parent_paths = resolved_flow_paths[symbol]
                if prefix not in parent_paths:
                    raise ValueError(
                        f"flow ancestry for {row['symbol']} cannot resolve {symbol}"
                    )
                prefix.append(
                    annotation._review_branch_ref(
                        parent["review_id"], prefix, len(parent_paths)
                    )
                )
            resolved.append(prefix)
        resolved_flow_paths[row["symbol"]] = resolved

    def resolve_routes(routes: Sequence[Sequence[str]]) -> list[list[str]]:
        resolved: list[list[str]] = []
        for route in routes:
            prefix: list[str] = []
            for symbol in route:
                parent = flow_by_symbol[symbol]
                parent_paths = resolved_flow_paths[symbol]
                if prefix not in parent_paths:
                    raise ValueError(f"nonflow route cannot resolve {symbol}")
                prefix.append(
                    annotation._review_branch_ref(
                        parent["review_id"], prefix, len(parent_paths)
                    )
                )
            resolved.append(prefix)
        return resolved

    ordered_specs = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
        ),
    )
    occurrence_specs: list[dict[str, Any]] = []
    for row in ordered_specs:
        occurrence_specs.append(
            {
                "review_occurrence_id": _review_id(
                    source_document_id,
                    page_texts,
                    row["page"],
                    row["start"],
                    row["end"],
                    row["kind"],
                ),
                "page_number": row["page"],
                "utf8_byte_start": row["start"],
                "utf8_byte_end": row["end"],
                "occurrence_kind": row["kind"],
                "parent_review_branch_paths": resolve_routes(
                    sorted(row["routes"])
                ),
                "review_note": row["note"],
            }
        )

    occurrence_by_id = {
        spec["review_occurrence_id"]: spec for spec in occurrence_specs
    }
    parent_anchors = [
        spec
        for spec in occurrence_specs
        if spec["occurrence_kind"] in {J, T, FA, BA}
    ]

    def branch_compatible(
        source: dict[str, Any], parent: dict[str, Any]
    ) -> bool:
        return any(
            source_path[: min(len(source_path), len(parent_path))]
            == parent_path[: min(len(source_path), len(parent_path))]
            for source_path in source["parent_review_branch_paths"]
            for parent_path in parent["parent_review_branch_paths"]
        )

    local_anchor_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        kind = spec["occurrence_kind"]
        if kind not in annotation.ANCHOR_KINDS:
            continue
        page = spec["page_number"]
        raw = page_texts[page - 1].encode("utf-8")
        label = raw[spec["utf8_byte_start"] : spec["utf8_byte_end"]].decode(
            "utf-8", errors="strict"
        )
        if kind == R:
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                label
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                kind
            ]
        parent_ids: list[str] = []
        if kind in {C, M}:
            compatible = [
                parent
                for parent in parent_anchors
                if parent["page_number"] == page
                and branch_compatible(spec, parent)
            ]
            nested = [
                parent
                for parent in compatible
                if spec["utf8_byte_start"]
                <= parent["utf8_byte_start"]
                < parent["utf8_byte_end"]
                <= spec["utf8_byte_end"]
            ]
            if nested:
                selected = nested
            else:
                distances = [
                    (
                        min(
                            abs(
                                spec["utf8_byte_start"]
                                - parent["utf8_byte_end"]
                            ),
                            abs(
                                parent["utf8_byte_start"]
                                - spec["utf8_byte_end"]
                            ),
                        ),
                        parent,
                    )
                    for parent in compatible
                ]
                nearest = min(
                    (distance for distance, _ in distances), default=10**9
                )
                selected = [
                    parent
                    for distance, parent in distances
                    if distance == nearest and distance <= 192
                ]
            parent_ids = [row["review_occurrence_id"] for row in selected]
            parent_ids.sort(
                key=lambda review_id: occurrence_specs.index(
                    occurrence_by_id[review_id]
                )
            )
        if kind not in {C, M}:
            parent_note = "Parent resolution is not applicable to this non-component anchor."
        elif parent_ids:
            parent_note = (
                "Nearest compatible source-local job or aggregate anchor was "
                "verified within the same printed block."
            )
        else:
            parent_note = (
                "Whole-page review found general context or no unambiguous "
                "document-local parent anchor."
            )
        local_anchor_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_texts[page - 1], spec["utf8_byte_start"]
                ),
                "parent_review_occurrence_ids": parent_ids,
                "parent_resolution_note": parent_note,
                "classification_status": "provisional_document_local",
            }
        )

    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    repeat_alias_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != A:
            continue
        raw = page_texts[spec["page_number"] - 1].encode("utf-8")
        text = raw[spec["utf8_byte_start"] : spec["utf8_byte_end"]].decode(
            "utf-8", errors="strict"
        )
        folded = text.casefold()
        relation = (
            "explicit_repeat_instruction"
            if any(
                marker in folded
                for marker in (
                    "repeat",
                    "again",
                    "another job",
                    "other job",
                )
            )
            else "explicit_cross_reference"
        )
        evidence_ids = [spec["review_occurrence_id"]]
        evidence_ids.sort(key=occurrence_order.__getitem__)
        repeat_alias_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "relation": relation,
                "alias_anchor_review_occurrence_ids": [],
                "canonical_anchor_review_occurrence_ids": [],
                "evidence_review_occurrence_ids": evidence_ids,
                "target_scope": "unresolved",
                "resolution_status": "preserved_for_global_resolution",
            }
        )

    counts_by_page = Counter(spec["page_number"] for spec in occurrence_specs)
    page_review_rows = [
        {
            "page_number": page,
            "page_text_utf8_sha256": annotation._sha256(text.encode("utf-8")),
            "whole_page_review_complete": True,
            "review_status": "complete",
            "review_note": (
                "Whole page reviewed against exact source bytes; "
                f"{counts_by_page[page]} source occurrence atoms retained."
            ),
        }
        for page, text in enumerate(page_texts, start=1)
    ]
    review: dict[str, Any] = {
        "schema_version": annotation.REVIEW_SCHEMA_VERSION,
        "review_id": "rq-stage2-source-review:"
        + annotation._canonical_digest(
            [source_document_id, annotation.DOCUMENT_SOURCE_POSITION]
        ),
        "authority_kind": "reviewer_authored_source_bytes_only_nonauthority",
        "document_source_position": annotation.DOCUMENT_SOURCE_POSITION,
        "source_document_id": source_document_id,
        "review_method": {
            "source_rows_derived_from_page_bytes": True,
            "whole_page_review": "all_118_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": local_anchor_specs,
        "repeat_alias_specs": repeat_alias_specs,
        "integrity": {
            "canonicalization": annotation.CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": "complete",
    }
    review["integrity"]["content_sha256"] = annotation._content_sha256(review)
    annotation.validate_review(review, document, page_texts)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    review = author_review()
    annotation._write_or_check(
        annotation.REVIEW_PATH,
        annotation._canonical_bytes(review),
        args.check,
    )
    counts = Counter(
        row["occurrence_kind"] for row in review["occurrence_specs"]
    )
    print(
        f"{'checked' if args.check else 'wrote'} "
        f"{annotation.REVIEW_PATH.relative_to(ROOT)}: "
        f"{len(review['occurrence_specs'])} occurrences {dict(counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
