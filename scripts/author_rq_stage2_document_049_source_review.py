#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 49.

The 153-page 1992 QxQ was reviewed page by page from the authenticated
Poppler text. This helper encodes the retained employment, work-income, and
limited work-history source regions. It reruns the stage-1 lexical detectors
over authenticated bytes but never opens the committed candidate artifact;
candidate rows are joined only by the sealed document annotation builder.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_049_annotation as annotation

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

# Whole-document review retained the Head employment sequences, the visible
# Wife employment-entry handoff, the work-only portion of Section G, and the
# narrowly bounded lifetime-work/New-Head history prompts.  Health,
# housework, OFUM income, education/training, transfer income, marriage, and
# Latino-background prose deliberately emit no source occurrence rows even
# when they contain generic words such as ``work``, ``job``, or ``income``.
EMPLOYMENT_PAGES = frozenset(range(20, 60))
WORK_INCOME_PAGES = frozenset({*range(66, 77), 82, 83})
WORK_HISTORY_PAGES = frozenset({138, *range(146, 153)})
SEMANTIC_PAGES = frozenset().union(
    EMPLOYMENT_PAGES,
    WORK_INCOME_PAGES,
    WORK_HISTORY_PAGES,
)

# One-based physical-page byte windows independently selected from the pinned
# Poppler strings. Full-page employment review is intentional. Section G
# windows end before transfers and other nonwork income. Background windows
# exclude education/training prose that merely mentions employability.
REVIEWED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    66: ((109, 2282),),
    67: ((126, 2168),),
    68: ((118, 2446),),
    69: ((98, 2825),),
    70: ((122, 3876),),
    71: ((92, 3284),),
    72: ((123, 4034),),
    73: ((91, 2525),),
    74: ((63, 638),),
    75: ((89, 231),),
    76: ((57, 641),),
    82: ((353, 1141),),
    83: ((1011, 1684),),
    138: ((412, 1117),),
    146: ((222, 278), (2165, 2551)),
    147: ((938, 1321),),
    148: ((293, 811), (2082, 2940)),
    149: ((1343, 2051),),
    150: ((1172, 1606),),
    151: ((518, 995), (1220, 1494)),
    152: ((2250, 3115),),
}

EMPLOYMENT_KINDS = frozenset({F, R, J, M, C, P, A})
INCOME_KINDS = frozenset(annotation.OCCURRENCE_KINDS)
HISTORY_KINDS = frozenset({F, R, J, C, P, A})

# Narrative Q-by-Q pages contain many interrogative examples and generic
# mentions of a job.  On these pages, only identifier-bearing prompt lines
# auto-survive; complete source blocks are added explicitly below.
QBYQ_PAGES = frozenset(
    {
        21,
        23,
        24,
        25,
        27,
        29,
        31,
        33,
        35,
        37,
        39,
        41,
        42,
        43,
        45,
        47,
        49,
        51,
        53,
        55,
        57,
        59,
        67,
        69,
        71,
        73,
        75,
        83,
        147,
        149,
        151,
    }
)

FLOW_EXCLUSION_MARKERS = (
    "IF NECESSARY",
    "IF VOLUNTEERED",
    "IF ZERO",
    "IF NOT CLEAR",
    "IF R DOESN'T UNDERSTAND",
    "IF R DOES NOT UNDERSTAND",
    "IF DOESN'T SPECIFY",
    "IF DOES NOT SPECIFY",
    "RETURN TO THE SAME",
)
FLOW_ACTION_MARKERS = (
    "GO TO",
    "TURN TO",
    "NEXT PAGE",
    "SKIP TO",
    "ASK SECTION",
    "ASK B",
    "ASK C",
    "ASK D",
    "ASK E",
    "ALL OTHERS",
    "OTHERWISE",
)

# These stage-1 purpose hits are answer text, handwritten responses, or bare
# checkpoint headings. None states a source field's purpose.
FALSE_PURPOSE_SPANS: frozenset[tuple[int, int, int]] = frozenset(
    {(56, 2732, 2752)}
)
FALSE_REPEAT_SPANS: frozenset[tuple[int, int, int]] = frozenset()
FALSE_FLOW_SPANS: frozenset[tuple[int, int, int]] = frozenset()

PAGE_REVIEW_QUALIFIERS = {
    20: " Poppler interleaves B1/B3 columns; only independently visible answer and destination atoms were retained.",
    38: " The Work History Supplement names future D/E entry sites, which are repeat evidence rather than illegal later-parent paths.",
    40: " Missing positive complements at supplement exits were not reconstructed from layout.",
    58: " Poppler interleaves the D1 checkpoint columns; no missing D3 text was invented.",
    66: " After the farmer-only G3-5 block, both G2 paths continue to G6; absent positive complements were not invented.",
    68: " The filled duplicate preserves its own farmer/all-other alternatives and exact source bytes.",
    82: " Wife work-income routing is bounded to G49-G52 and excludes adjacent transfer-income fields.",
    138: " Section-L checkpoint columns are interleaved; only source-visible entry and exit atoms were retained.",
    146: " The L44 NONE route exits the section; L45 retains the complete source-visible entry alternatives.",
    148: " The same-Head exit and M5 NEVER WORKED route are visible; no worked complement was invented.",
    152: " Training branches converge before M57; lifetime-work fields retain only the outer New-Head entry alternatives.",
}
LOCAL_COMPLEMENT_LIMITATION_PAGES = frozenset(
    {30, 32, 34, 36, 40, 44, 46, 48, 52, 54, 56, 66, 68, 70, 72, 74, 76, 82}
)

COMPOSITE_WIFE_RE = re.compile(
    r"\(?(?:WIFE(?:S|['\u2019]S)?\s*/\s*[\"\u201c]\s*"
    r"WIFE(?:S|['\u2019]S)?[,\.]?\s*[\"\u201d])\)?",
    re.IGNORECASE,
)
SEE_REFERENCE_RE = re.compile(
    r"\bSEE\b[^\n]{0,100}\b(?:SECTION\s+)?[BCDEGLM]\s*\d",
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
        return REVIEWED_BYTE_WINDOWS.get(page, ((0, page_size(page)),))

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

    # Source-visible outer routing. OCR dropped several answer labels, so the
    # graph uses only text that exists in the authenticated Poppler bytes.
    # Missing labels are never reconstructed from layout or candidate paths.
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

    flow("head_code_1", 20, *byte_find(20, "I 1. WORKING Now]"))
    flow(
        "head_code_2",
        20,
        *byte_find(20, "2. ONLY TEMPORARILY LAID OFF, SICK"),
    )
    flow("head_code_3", 20, *byte_find(20, "3. LOOKING FOR"))
    flow("head_codes_4_8", 20, 717, 771)
    flow(
        "head_paid_work_yes",
        20,
        1288,
        1297,
        (("head_code_3",), ("head_codes_4_8",)),
    )
    flow(
        "head_not_working_route",
        20,
        1550,
        1828,
        (("head_code_3",), ("head_codes_4_8",)),
        "OCR-interleaved but source-visible TURN TO SECTION C route; absent NO text was not invented.",
    )
    flow(
        "b_supplement_entry",
        36,
        1664,
        1711,
        (
            ("head_code_1",),
            ("head_code_2",),
            ("head_code_3", "head_paid_work_yes"),
            ("head_codes_4_8", "head_paid_work_yes"),
        ),
    )
    flow("wife_female_head_exit", 58, 302, 439)
    flow("wife_present", 58, 549, 577)
    flow("no_wife_exit", 58, 589, 736)
    flow(
        "wife_code_1",
        58,
        *byte_find(58, "I 1. WORKING NOW'"),
        (("wife_present",),),
    )
    flow(
        "wife_code_2",
        58,
        *byte_find(58, "2. ONLY TEMPORARILY LAID OFF, SICK"),
        (("wife_present",),),
    )
    flow(
        "wife_code_3",
        58,
        *byte_find(58, "3. LOOKING FOR"),
        (("wife_present",),),
    )
    flow(
        "wife_codes_4_8",
        58,
        1390,
        1445,
        (("wife_present",),),
    )
    flow(
        "wife_paid_work_yes",
        58,
        2028,
        2036,
        (
            ("wife_present", "wife_code_3"),
            ("wife_present", "wife_codes_4_8"),
        ),
    )
    flow(
        "wife_not_working_route",
        58,
        2228,
        2635,
        (
            ("wife_present", "wife_code_3"),
            ("wife_present", "wife_codes_4_8"),
        ),
        "OCR-interleaved but source-visible TURN TO SECTION E route; absent NO text was not invented.",
    )

    # Both clean/fill copies are source pages and therefore retain their own
    # exact farmer/all-other and extra-job alternatives.
    flow(
        "g2_p66_farmer", 66, *byte_find(66, "1.   HEAD IS A FARMER OR RANCHER")
    )
    flow("g2_p66_all_others", 66, 415, 438)
    flow(
        "g6_p66_no_to_g12",
        66,
        1271,
        1302,
        (("g2_p66_farmer",), ("g2_p66_all_others",)),
        "Source-visible G6 NO exit after the farmer/all-other convergence.",
    )
    flow(
        "g2_p68_farmer", 68, *byte_find(68, "1.   HEAD IS A FARMER OR RANCHER")
    )
    flow("g2_p68_all_others", 68, 439, 463)
    flow(
        "g6_p68_no_to_g12",
        68,
        1318,
        1348,
        (("g2_p68_farmer",), ("g2_p68_all_others",)),
        "Source-visible G6 NO exit after the farmer/all-other convergence.",
    )
    flow("g13_p70_to_g18", 70, 852, 861)
    flow("g15_p70_to_g18", 70, 1329, 1338)
    flow("g13_p72_to_g18", 72, 852, 861)
    flow("g15_p72_to_g18", 72, 1330, 1339)
    flow("g22_p74_extra_job", 74, *byte_find(74, "A.     EXTRA JOB IN 1991"))
    flow("g22_p74_all_others", 74, 212, 243)
    flow("g22_p76_extra_job", 76, *byte_find(76, "A.   EXTRA JOB IN 1991"))
    flow("g22_p76_all_others", 76, 203, 236)
    flow(
        "g49_wife_present",
        82,
        *byte_find(82, 'A.   WIFE/"WIFE" IN FU NOW'),
    )
    flow(
        "g49_all_others_exit",
        82,
        482,
        523,
    )
    flow(
        "g50_no_exit",
        82,
        648,
        666,
        (("g49_wife_present",),),
    )

    # L and M contribute only narrow work-history fields. Their entry/exit
    # atoms remain in the graph so those fields do not lose section ancestry.
    flow("l_new_wife_entry", 138, *byte_find(138, "1. NEW WIFE OR"))
    flow(
        "l_splitoff_wife_entry",
        138,
        *byte_find(138, '1. WIFE OR "WIFE"'),
    )
    flow("l_same_wife_exit", 138, *byte_find(138, "TURN TO P . 115,"))
    flow("l_no_wife_exit", 138, *byte_find(138, "TURN TO P. 115,"))
    l_work_routes = (("l_new_wife_entry",), ("l_splitoff_wife_entry",))
    flow("l36_no_to_l42", 146, *byte_find(146, "Go To L42"), l_work_routes)
    flow("l44_none_exit", 146, 2315, 2401, l_work_routes)

    flow(
        "m_splitoff_entry",
        148,
        *byte_find(148, "1. GREEN, LIIIE, GOLDENROD OR"),
    )
    flow("m_new_head_entry", 148, *byte_find(148, "1. NEW HEAD"))
    flow("m_same_head_exit", 148, *byte_find(148, "5. SAME HEAD"))
    m_work_routes = (("m_splitoff_entry",), ("m_new_head_entry",))
    flow(
        "m5_never_worked_to_m7",
        148,
        2278,
        2683,
        m_work_routes,
        "Source-visible M5 NEVER WORKED route to M7; absent worked complement was not invented.",
    )
    flow("m57_cover_sheet_exit", 152, 2393, 2740, m_work_routes)
    flow("m58_final_exit", 152, 2921, 3115, m_work_routes)

    flow_defs.sort(
        key=lambda row: (row["page"], row["start"], row["end"], row["symbol"])
    )
    flow_by_symbol = {row["symbol"]: row for row in flow_defs}
    if len(flow_by_symbol) != len(flow_defs):
        raise ValueError("duplicate flow symbol")

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

    head_b_route = (
        ("head_code_1",),
        ("head_code_2",),
        ("head_code_3", "head_paid_work_yes"),
        ("head_codes_4_8", "head_paid_work_yes"),
    )
    head_c_route = (
        ("head_code_3", "head_not_working_route"),
        ("head_codes_4_8", "head_not_working_route"),
    )
    supplement_entry_routes = (
        ("head_code_1", "b_supplement_entry"),
        ("head_code_2", "b_supplement_entry"),
        ("head_code_3", "head_paid_work_yes", "b_supplement_entry"),
        (
            "head_codes_4_8",
            "head_paid_work_yes",
            "b_supplement_entry",
        ),
        *head_c_route,
    )
    l_work_route = l_work_routes
    m_work_route = m_work_routes

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if page in {20, 21}:
            return ((),)
        if 22 <= page <= 37:
            return head_b_route
        if 38 <= page <= 41:
            return supplement_entry_routes
        if 42 <= page <= 49:
            return head_b_route
        if 50 <= page <= 57:
            return head_c_route
        if page == 58:
            if 739 <= start < 1580:
                return (("wife_present",),)
            if 1580 <= start < 2228:
                return (
                    ("wife_present", "wife_code_3"),
                    ("wife_present", "wife_codes_4_8"),
                )
            return ((),)
        if page == 59:
            return ((),)
        if page == 66:
            if 463 <= start < 1057:
                return (("g2_p66_farmer",),)
            if start >= 1057:
                return (("g2_p66_farmer",), ("g2_p66_all_others",))
        if page == 68:
            if 464 <= start < 1100:
                return (("g2_p68_farmer",),)
            if start >= 1100:
                return (("g2_p68_farmer",), ("g2_p68_all_others",))
        if page == 74 and start >= 247:
            return (("g22_p74_extra_job",),)
        if page == 76 and start >= 240:
            return (("g22_p76_extra_job",),)
        if page == 82:
            if start >= 528:
                return (("g49_wife_present",),)
        if page in {146, 147}:
            return l_work_route
        if page in {148, 149, 150, 151, 152}:
            return m_work_route
        return ((),)

    def allowed_kinds(page: int) -> frozenset[str]:
        if page in EMPLOYMENT_PAGES:
            return EMPLOYMENT_KINDS
        if page in WORK_INCOME_PAGES:
            return INCOME_KINDS
        return HISTORY_KINDS

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
        if (
            "INTERVIEWER CHECKPOINT" in folded
            or not re.search(r"[A-Za-z]", text)
            or folded.strip(" .,:;[](){}'\"") in {"IS", "NO", "YES"}
            or (
                any(
                    marker in folded
                    for marker in ("GO TO", "TURN TO", "NEXT PAGE")
                )
                and "?" not in text
            )
        ):
            return False
        if row["page_number"] in QBYQ_PAGES:
            return "purpose_identifier_line_v1" in rules
        # Questionnaire pages retain identifier-bearing and actual question
        # lines.  Narrative Q-by-Q prose is handled by exact manual blocks.
        return (
            "purpose_identifier_line_v1" in rules
            or "purpose_interrogative_line_v1" in rules
            or ("?" in text and not folded.startswith("IF "))
        )

    def in_relevant_window(
        page: int,
        start: int,
        end: int,
        kind: str,
        text: str,
        row: dict[str, Any] | None = None,
    ) -> bool:
        if (
            page not in SEMANTIC_PAGES
            or not inside_reviewed_window(page, start, end)
            or kind not in allowed_kinds(page)
        ):
            return False
        folded = " ".join(text.upper().split())
        if kind == P and (page, start, end) in FALSE_PURPOSE_SPANS:
            return False
        if page in WORK_HISTORY_PAGES and kind not in {F, R}:
            return False
        if page == 138 and kind != F:
            return False
        if page == 148 and kind == R and start < 2082:
            return False
        if page == 67 and kind not in {R, M, FA, C, P, A}:
            return False
        if page == 69 and kind not in {R, C, P, A}:
            return False
        if page == 71 and kind not in {R, M, C, A}:
            return False
        if page == 73 and kind not in {R, C, A}:
            return False
        if page == 75 and kind not in {R, C, P, A}:
            return False
        if page == 83 and kind not in {R, T, C, A}:
            return False
        if page in {74, 76} and kind in {T, FA, BA}:
            return False
        if page == 82 and kind in {J, FA, BA}:
            return False
        if kind in {T, FA, BA}:
            if kind == T:
                # The four lawful work totals are manually re-sliced below;
                # detector lines on two-column grids cross unrelated columns.
                return False
            if kind == FA:
                if page == 67:
                    return start in {695, 716, 962, 1330, 1504}
                return page in {66, 68, 70, 72}
            if kind == BA:
                return page in {66, 68, 70, 72} and not (
                    page in {70, 72} and folded == "UNINCORPORATED"
                )
        if kind == F:
            if page in QBYQ_PAGES or (page, start, end) in FALSE_FLOW_SPANS:
                return False
            if any(marker in folded for marker in FLOW_EXCLUSION_MARKERS):
                return False
            return any(marker in folded for marker in FLOW_ACTION_MARKERS)
        if kind == P:
            if row is None:
                return True
            return retain_purpose(row)
        if kind == A:
            if (page, start, end) in FALSE_REPEAT_SPANS:
                return False
            return any(
                marker in folded
                for marker in (
                    "REPEAT",
                    "SAME JOB",
                    "PREVIOUSLY",
                    "ALREADY TOLD",
                    "WORK HISTORY SUPPLEMENT",
                    "SEE B",
                    "SEE C",
                    "SEE D",
                    "SEE E",
                    "SEE G",
                    "SEE K",
                )
            )
        if kind == J:
            if page in WORK_HISTORY_PAGES:
                # Only the corrected M5 full-time regular-job label survives.
                return False
            if page in WORK_INCOME_PAGES:
                return page in {66, 68, 74, 76}
            if page in QBYQ_PAGES:
                printed_identifier = annotation._source_printed_identifier(
                    page_texts[page - 1], start
                )
                if printed_identifier is None:
                    return False
        if kind == M and page in QBYQ_PAGES:
            return False
        if kind == C and page in {21, 24, 25, 27, 29, 31, 33, 35}:
            # These early Q-by-Q pages mostly contain worked examples and
            # generic prose. Complete objective blocks are added manually.
            return False
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

    # Q-by-Q repeat and cross-reference prose is semantically atomic at the
    # printed instruction-block level.  These exact blocks were independently
    # re-sliced after the lexical pass; no candidate boundary is authoritative.
    repeat_blocks: tuple[tuple[int, int, int, str], ...] = (
        (21, 235, 546, "B/C instructions explicitly recur in D/E."),
        (
            23,
            101,
            504,
            "Main-job instructions explicitly reference the B82 extra-job sequence.",
        ),
        (
            23,
            3372,
            3449,
            "Printed B10 repeat instruction at the physical page boundary.",
        ),
        (
            29,
            91,
            279,
            "B20 explicitly defines the local meaning of another job.",
        ),
        (
            31,
            1290,
            1363,
            "Overlapping employment periods explicitly route to extra-job questions.",
        ),
        (33, 86, 158, "B35-36 explicitly cross-reference B9-10."),
        (35, 84, 115, "B43-45 explicitly cross-reference B4-6."),
        (35, 117, 266, "B46-48 explicitly cross-reference B9-11."),
        (35, 268, 301, "B49-50 explicitly cross-reference B37-38."),
        (37, 87, 245, "B51-53 explicitly cross-reference B25-29."),
        (37, 1200, 1234, "B57-58 explicitly cross-reference B37-38."),
        (
            37,
            1236,
            1443,
            "Additional changes explicitly invoke the Work History Supplement.",
        ),
        (39, 491, 823, "The supplement is explicitly reused in B/C/D/E."),
        (39, 1609, 1640, "S1 explicitly cross-references B24."),
        (39, 1642, 1674, "S2 explicitly cross-references B39."),
        (39, 1676, 1712, "S3-5 explicitly cross-reference B4-6."),
        (39, 1714, 1870, "S6-8 explicitly cross-reference B9-11."),
        (39, 1872, 1904, "S9 explicitly cross-references B37."),
        (41, 87, 116, "S10 explicitly cross-references B38."),
        (41, 118, 313, "S11-13 explicitly cross-reference B25-29."),
        (41, 315, 350, "S14-18 explicitly cross-reference B54-58."),
        (41, 352, 516, "S19 explicitly repeats the Work History Supplement."),
        (
            47,
            216,
            385,
            "B72-74 explicitly cross-reference work-history and extra-job dates.",
        ),
        (
            47,
            1905,
            2236,
            "B75-77 explicitly cross-reference the work history.",
        ),
        (
            49,
            3132,
            3241,
            "Page 19 explicitly repeats the Page 18 extra-job sequence.",
        ),
        (51, 154, 284, "Section C explicitly parallels Section B."),
        (51, 328, 363, "C2 explicitly cross-references B21."),
        (
            53,
            87,
            739,
            "C4-8 explicitly reuse comparable Section-B instructions.",
        ),
        (53, 741, 949, "C9-11 explicitly cross-reference B9-11."),
        (55, 47, 86, "C12-14 explicitly cross-reference B4-6."),
        (55, 88, 117, "C15 explicitly cross-references B56."),
        (57, 85, 430, "C16-51 explicitly repeat B24-59."),
        (57, 434, 696, "Unreproduced C52-73 explicitly parallel B60-81."),
        (
            59,
            606,
            887,
            "D/E explicitly parallel B/C and reuse their objectives.",
        ),
        (59, 1074, 1199, "D1a explicitly parallels B1."),
        (59, 1201, 1462, "Unreproduced D remainder explicitly parallels B."),
        (66, 299, 345, "G2 explicitly cross-references B9-10."),
        (67, 126, 427, "Section G explicitly maps work hours to B/C/D/E."),
        (
            67,
            620,
            929,
            "G2-5 explicitly cross-reference employment and income fields.",
        ),
        (68, 316, 367, "Duplicate G2 explicitly cross-references B9-10."),
        (
            69,
            98,
            395,
            "Section-G consistency rule explicitly links work and income.",
        ),
        (69, 396, 617, "G3-4 are an explicit repeated farm-income block."),
        (69, 618, 964, "G7-11 explicitly repeat for every business."),
        (
            69,
            965,
            1187,
            "G12-20 provide an explicit fallback work-income sequence.",
        ),
        (69, 1188, 1475, "Section G explicitly maps back to B/C/D/E."),
        (
            70,
            3393,
            3876,
            "Roomer/boarder work hours explicitly return to B/C.",
        ),
        (
            71,
            92,
            363,
            "Section-G consistency rule explicitly links work and income.",
        ),
        (71, 364, 492, "B/C are explicit catch points for wage work."),
        (71, 493, 822, "G12-18 explicitly reuse B12-19 concepts."),
        (
            71,
            1651,
            1944,
            "G11/G13 explicitly prevent duplicate business income.",
        ),
        (71, 1945, 2077, "G14-15 explicitly prevent duplicate income."),
        (
            71,
            2078,
            2252,
            "G16-17 explicitly distinguish commissions-only income.",
        ),
        (
            71,
            2358,
            2965,
            "G18 explicitly cross-references earlier business/farm amounts.",
        ),
        (71, 2966, 3284, "G18 explicitly redirects farming income."),
        (
            72,
            3472,
            4034,
            "Duplicate roomer work hours explicitly return to B/C.",
        ),
        (
            73,
            91,
            365,
            "Section-G consistency rule explicitly links work and income.",
        ),
        (
            73,
            366,
            942,
            "B/C and G25a are explicit alternate reporting locations.",
        ),
        (73, 1162, 1610, "G19c explicitly cross-references G25a."),
        (73, 1611, 2525, "G21 explicitly returns missing work hours to B/C."),
        (74, 102, 158, "G22 explicitly cross-references B82/C74 extra jobs."),
        (
            74,
            247,
            364,
            "G23 explicitly repeats the extra-job inclusion check.",
        ),
        (76, 96, 148, "Duplicate G22 explicitly cross-references B82/C74."),
        (
            76,
            240,
            357,
            "Duplicate G23 explicitly repeats the inclusion check.",
        ),
        (
            83,
            1011,
            1684,
            "G51-52 explicitly link D/E work and G income both ways.",
        ),
        (
            149,
            1343,
            1508,
            "M4-5 explicitly cross-reference B9-11 occupation objectives.",
        ),
        (151, 1220, 1494, "M14-58 explicitly duplicate Section L."),
    )
    for page, start, end, note in repeat_blocks:
        manual(page, start, end, (A,), note)

    # Candidate-free recovery of source-visible local skip atoms. These are
    # retained with their outer ancestry, but no absent YES/NO complement is
    # reconstructed and no exiting branch is fed back into a later merge.
    for page, start, end, note in (
        (22, 1258, 1263, "B7 source-visible route to B9."),
        (28, 230, 237, "B20 source-visible route to B22."),
        (30, 1241, 1278, "B24 source-visible route to B37."),
        (30, 1344, 1405, "B24 source-visible route to B40."),
        (30, 1488, 1650, "B24 source-visible route to B34."),
        (30, 1686, 1800, "B24 source-visible route to B39."),
        (30, 2092, 2278, "B32 source-visible route to B39."),
        (30, 2325, 2377, "B26 source-visible route to B29."),
        (30, 2710, 2805, "B27 NO route to B35."),
        (32, 1426, 1495, "B40 NO route to B60."),
        (36, 182, 213, "B51 source-visible route to B54."),
        (36, 492, 525, "B54 source-visible route to B59."),
        (36, 1601, 1659, "B59 NO route to B60."),
        (40, 249, 288, "S11 source-visible route to S14."),
        (44, 2019, 2101, "B66 NO route to B69."),
        (
            46,
            802,
            880,
            "OCR-interleaved but source-visible B72 NO route to B75.",
        ),
        (46, 1954, 2044, "B78 source-visible route to B82."),
        (46, 2523, 2583, "B80 NO route to B82."),
        (48, 182, 261, "B82 NO route to Section D."),
        (48, 2589, 2652, "B92 NO route to B94."),
        (50, 252, 319, "C1 source-visible route to C4."),
        (52, 116, 160, "C4 source-visible route to C6."),
        (52, 827, 926, "C6 NO exit to Section D."),
        (52, 1159, 1234, "C8 exit to Section D."),
        (56, 1333, 1462, "C17 source-visible route to C29."),
        (56, 1631, 1746, "C23 source-visible route to C31."),
        (56, 2706, 2752, "C19 NO route to C27."),
    ):
        manual(page, start, end, (F,), note)
    for page, phrase, start, note in (
        (30, "NEXT PAGE, 835", 3300, "B29 route to B35."),
        (30, "NEXT PAGE, 839", 3300, "B34 route to B39."),
        (56, "NEXT PAGE, C32", 1500, "C22 route to C32."),
        (56, "NEXT PAGE,", 2200, "C24 source-visible next-page route."),
        (56, "NEXT PAGE,", 2750, "C25 source-visible next-page route."),
        (56, "NEXT PAGE, C27", 3200, "C21 route to C27."),
        (56, "NEXT PAGE, C31", 3200, "C26 route to C31."),
    ):
        manual(page, *byte_find(page, phrase, start), (F,), note)

    # Complete contextual blocks replace detector fragments on explanatory
    # pages. They remain source-local and do not infer any global component.
    for page, start, end, kinds, note in (
        (67, 126, 427, (C,), "Complete work-hours/income linkage context."),
        (67, 620, 929, (C,), "Complete farm-work handoff context."),
        (
            69,
            98,
            395,
            (C,),
            "Complete Section-G work/income consistency context.",
        ),
        (69, 1188, 1475, (C,), "Complete employment-section handoff context."),
        (70, 3393, 3876, (C,), "Complete roomer-work linkage context."),
        (
            71,
            92,
            363,
            (C,),
            "Complete Section-G work/income consistency context.",
        ),
        (71, 364, 492, (C,), "Complete B/C wage-work catch context."),
        (71, 493, 822, (C,), "Complete wage-work objective context."),
        (71, 1651, 1944, (C,), "Complete anti-double-counting context."),
        (71, 1945, 2077, (C,), "Complete income-exclusion context."),
        (71, 2078, 2252, (C,), "Complete commissions-only context."),
        (71, 2358, 2965, (C,), "Complete professional-practice context."),
        (71, 2966, 3284, (C,), "Complete farming-income redirect context."),
        (72, 3472, 4034, (C,), "Complete duplicate roomer-work context."),
        (
            73,
            91,
            365,
            (C,),
            "Complete Section-G work/income consistency context.",
        ),
        (73, 366, 942, (C,), "Complete B/C versus G25a context."),
        (73, 1162, 1610, (C,), "Complete G19c work-hours context."),
        (73, 1611, 2525, (C,), "Complete G21 return-to-B/C context."),
        (83, 1011, 1684, (C,), "Complete Wife work-income linkage context."),
        (146, 2218, 2314, (C, P), "Complete L44 lifetime-work question."),
        (146, 2403, 2513, (C, P), "Complete L45 full-time-work question."),
        (147, 938, 1260, (C, P), "Complete L44 lifetime-work objective."),
        (147, 1261, 1321, (C, P), "Complete L45 full-time definition."),
        (148, 2082, 2158, (C, P), "Complete M5 first-regular-job question."),
        (
            148,
            2802,
            2940,
            (C, P),
            "Complete M6 occupation-continuity question.",
        ),
        (
            149,
            1509,
            2051,
            (C, P),
            "Complete M6 occupation-continuity objective.",
        ),
        (150, 1172, 1295, (C, P), "Complete M11 move-for-job question."),
        (150, 1415, 1503, (C, P), "Complete M12 declined-job question."),
        (
            151,
            518,
            995,
            (C,),
            "Complete M11-12 job-mobility objective context.",
        ),
        (152, 2305, 2392, (C, P), "Complete M57 lifetime-work question."),
        (152, 2741, 2835, (C, P), "Complete M58 full-time-work question."),
    ):
        manual(page, start, end, kinds, note)

    # The first-regular-job lexeme is the only job-slot anchor in the narrow
    # background/history scope; father occupations and training-for-jobs prose
    # are outside the canonical Head/Wife job hierarchy.
    manual(
        148,
        *byte_find(148, "first full-time regular job"),
        (J,),
        "Exact M5 first-regular-job anchor.",
    )

    # Work-linked Section-G totals are re-sliced because the detector often
    # crosses adjacent two-column prompts or retains only a fragment.
    manual(66, 1920, 2158, (T,), "Exact G11 business-income role total.")
    manual(
        68, 2072, 2314, (T,), "Exact duplicate G11 business-income role total."
    )
    for page in (70, 72):
        manual(
            page,
            *byte_find(page, "altogether from wages or"),
            (T,),
            "Exact Head all-wages total anchor.",
        )
    manual(82, 716, 855, (T,), "Exact Wife all-work total question.")
    manual(82, 980, 1016, (T,), "Exact Wife total-earnings printed label.")
    manual(
        83,
        *byte_find(83, "all work sources"),
        (T,),
        "Exact Wife all-work-sources total anchor.",
    )

    # G23/G24 and G52 purpose/component blocks are complete semantic units.
    manual(74, 247, 364, (P,), "Complete G23 extra-job inclusion prompt.")
    manual(74, 413, 638, (M,), "Complete G24 extra-job earnings field.")
    manual(76, 240, 357, (P,), "Complete duplicate G23 inclusion prompt.")
    manual(76, 416, 641, (M,), "Complete duplicate G24 earnings field.")
    manual(82, 669, 712, (P,), "Complete G51 Wife-work purpose prompt.")
    manual(82, 716, 855, (P,), "Complete G52 total-work purpose prompt.")

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
        parent_basis = "nearest"
        if kind in {C, M}:
            compatible = [
                parent
                for parent in parent_anchors
                if parent["page_number"] == page
                and branch_compatible(spec, parent)
            ]
            if kind == M and (
                (page == 66 and spec["utf8_byte_start"] >= 1920)
                or (page == 68 and spec["utf8_byte_start"] >= 2072)
            ):
                selected = [
                    parent
                    for parent in compatible
                    if parent["occurrence_kind"] == T
                ]
                if len(selected) != 1:
                    raise ValueError(
                        "G11 business components need one role-total parent"
                    )
                parent_basis = "g11_role_total"
            elif (
                kind == M
                and page in {70, 72}
                and spec["utf8_byte_start"] < 500
            ):
                selected = [
                    parent
                    for parent in compatible
                    if parent["occurrence_kind"] == T
                ]
                if len(selected) != 1:
                    raise ValueError(
                        "G12 wage components need one role-total parent"
                    )
                parent_basis = "g12_role_total"
            else:
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
        elif parent_ids and parent_basis in {
            "g11_role_total",
            "g12_role_total",
        }:
            parent_note = (
                "The G11/G12 component was verified against its exact "
                "role-total label, not a nearby aggregate lexeme."
            )
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
                    "crop up again",
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
                "target_scope": "document_local",
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
                f"{PAGE_REVIEW_QUALIFIERS.get(page, '')}"
                + (
                    " The positive complement to a local skip is not independently locatable; downstream atoms retain every locatable outer path."
                    if page in LOCAL_COMPLEMENT_LIMITATION_PAGES
                    else ""
                )
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
            "whole_page_review": "all_153_pages_including_empty_occurrence_pages",
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
