#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 39.

The 166-page 1987 QxQ was reviewed page by page from the authenticated
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

import build_rq_stage2_document_039_annotation as annotation

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

# Whole-document review retained the employment sections for Head and Wife,
# the work-only portion of Section G, and narrowly bounded lifetime-work and
# New-Head work-history prompts. All remaining pages deliberately emit no
# source occurrence rows.
EMPLOYMENT_PAGES = frozenset(range(17, 89)) - {38, 65}
WORK_INCOME_PAGES = frozenset({*range(95, 106), 111, 112})
WORK_HISTORY_PAGES = frozenset({153, 154, 158, 159, 160, 161, 162, 166})
SEMANTIC_PAGES = frozenset().union(
    EMPLOYMENT_PAGES,
    WORK_INCOME_PAGES,
    WORK_HISTORY_PAGES,
)

# One-based physical-page byte windows independently selected from the pinned
# Poppler strings. Full-page employment review is intentional. The Section G
# windows end before transfers and other nonwork income, and the background
# windows exclude education/training prose that merely mentions jobs.
REVIEWED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    103: ((60, 663),),
    104: ((47, 178),),
    105: ((57, 628),),
    111: ((516, 1495),),
    112: ((615, 1053),),
    153: ((1648, 1971),),
    154: ((278, 1368),),
    158: ((2614, 2965),),
    159: ((824, 1453),),
    160: ((517, 1031), (1266, 1558)),
    161: ((177, 960), (2206, 3254)),
    162: ((1126, 1654),),
    166: ((374, 429), (2704, 3638)),
}

EMPLOYMENT_KINDS = frozenset({F, R, J, M, C, P, A})
INCOME_KINDS = frozenset(annotation.OCCURRENCE_KINDS)
HISTORY_KINDS = frozenset({F, R, J, C, P, A})

# Narrative Q-by-Q pages contain many interrogative examples and generic
# mentions of a job.  On these pages, only identifier-bearing prompt lines
# auto-survive; complete source blocks are added explicitly below.
QBYQ_PAGES = frozenset(
    {
        17,
        20,
        21,
        22,
        24,
        26,
        28,
        30,
        32,
        36,
        40,
        42,
        44,
        46,
        48,
        50,
        52,
        54,
        56,
        66,
        96,
        98,
        100,
        102,
        104,
        112,
        153,
        159,
        160,
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
FALSE_PURPOSE_SPANS = frozenset(
    {
        (19, 2054, 2138),
        (23, 2246, 2281),
        (31, 3261, 3317),
        (33, 82, 112),
        (33, 1953, 2032),
        (35, 250, 268),
        (43, 1480, 1587),
        (43, 2046, 2151),
        (53, 1539, 1598),
        (59, 66, 96),
        (78, 1070, 1112),
        (83, 70, 103),
        (103, 66, 97),
        (105, 61, 92),
        (111, 516, 547),
    }
)
FALSE_REPEAT_SPANS = frozenset({(30, 1762, 1826), (32, 311, 375)})
FALSE_FLOW_SPANS = frozenset(
    {
        (30, 748, 762),
        (32, 1462, 1525),
        (32, 1921, 1987),
        (32, 2003, 2038),
        (52, 366, 398),
        (58, 920, 927),
        (64, 2874, 2881),
        (64, 3260, 3267),
        (71, 1004, 1011),
        (76, 2072, 2077),
        (77, 2890, 2897),
        (77, 3274, 3281),
        (82, 960, 967),
        (87, 2316, 2324),
        (88, 993, 998),
        (88, 3040, 3047),
        (88, 3421, 3428),
    }
)

PAGE_REVIEW_QUALIFIERS = {
    18: " Poppler interleaves the B3 columns; OCR-damaged answer labels were visually verified at their exact spans without reconstructing missing text.",
    35: " The supplement also names later D/E invocation sites, which cannot be used as earlier branch parents.",
    36: " Later D/E invocation is preserved as repeat evidence rather than an illegal later-parent path.",
    37: " The supplement also names later D/E invocation sites, which cannot be used as earlier branch parents.",
    67: " Poppler interleaves the D3 columns; OCR-damaged answer labels were visually verified at their exact spans without reconstructing missing text.",
    95: " After the farmer-only G3-5 block, both G2 paths continue sequentially to G6; G6/G10 positive complements are not independently locatable.",
    97: " After the farmer-only G3-5 block, both G2 paths continue sequentially to G6; G6/G10 positive complements are not independently locatable.",
    154: " Checkpoint columns are interleaved; only independently locatable entry, exit, and role atoms were retained.",
    158: " The K44 NONE condition is not independently locatable, so K45 retains the complete locatable entry paths.",
    161: " The same-Head exit and L5 worked complement are unreadable; no branch label was invented.",
    162: " The L11 NO complement is absent from Poppler bytes; no branch label was invented for L12.",
    166: " Several answer columns interleave, so only source-visible route blocks were retained.",
}
LOCAL_COMPLEMENT_LIMITATION_PAGES = frozenset(
    {39, 41, 43, 45, 47, 61, 62, 63, 64, 74, 75, 76, 77, 86, 87, 88}
)

COMPOSITE_WIFE_RE = re.compile(
    r"\(?(?:WIFE(?:S|['\u2019]S)?\s*/\s*[\"\u201c]\s*"
    r"WIFE(?:S|['\u2019]S)?[,\.]?\s*[\"\u201d])\)?",
    re.IGNORECASE,
)
SEE_REFERENCE_RE = re.compile(
    r"\bSEE\b[^\n]{0,80}\b(?:SECTION\s+)?[BCDEGKL]\s*\d",
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

    # Source-visible outer routing.  OCR dropped several answer labels, so the
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

    flow("head_codes_1_3", 18, 321, 393)
    flow("head_codes_4_8", 18, 976, 1030)
    flow(
        "head_paid_work_yes",
        18,
        *byte_find(18, "j1. n:sj"),
        (("head_codes_4_8",),),
    )
    flow(
        "head_not_working_route",
        18,
        1725,
        2071,
        (("head_codes_4_8",),),
    )
    flow(
        "b_supplement_entry",
        34,
        1632,
        1675,
        (
            ("head_codes_1_3",),
            ("head_codes_4_8", "head_paid_work_yes"),
        ),
    )
    flow(
        "supplement_reverse_entry",
        35,
        3659,
        3684,
        (
            ("head_codes_1_3", "b_supplement_entry"),
            (
                "head_codes_4_8",
                "head_paid_work_yes",
                "b_supplement_entry",
            ),
            ("head_codes_4_8", "head_not_working_route"),
        ),
    )

    flow("no_wife_exit", 67, 371, 429)
    flow("wife_codes_1_3", 67, 602, 675)
    flow("wife_codes_4_8", 67, 1217, 1273)
    flow(
        "wife_paid_work_yes",
        67,
        *byte_find(67, "11.   YES'"),
        (("wife_codes_4_8",),),
    )
    flow(
        "wife_not_working_route",
        67,
        *byte_find(67, "I5Xol"),
        (("wife_codes_4_8",),),
    )

    # Both clean/fill copies are source pages and therefore retain their own
    # exact farmer/all-other and extra-job alternatives.
    flow(
        "g2_p95_farmer", 95, *byte_find(95, "1.   HEAD IS A FARMER OR RANCHER")
    )
    flow("g2_p95_all_others", 95, *byte_find(95, "[Z]s. ALLOTHE~"))
    flow(
        "g2_p97_farmer", 97, *byte_find(97, "l.   HEAD IS A FARMER OR RANCHER")
    )
    flow(
        "g2_p97_all_others",
        97,
        *byte_find(97, "~5.      ALL    ···-~GO ~ G6:==:>"),
    )
    flow(
        "g6_p95_no_to_g12",
        95,
        1673,
        1703,
        (("g2_p95_all_others",),),
        "OCR-damaged but source-visible G6 NO route to G12.",
    )
    flow(
        "g10_p95_corporation_to_g12",
        95,
        3168,
        3239,
        (("g2_p95_all_others",),),
        "OCR-damaged but source-visible G10 corporation route to G12.",
    )
    flow(
        "g6_p97_no_to_g12",
        97,
        1661,
        1696,
        (("g2_p97_all_others",),),
        "OCR-damaged but source-visible G6 NO route to G12.",
    )
    flow(
        "g10_p97_corporation_to_g12",
        97,
        3377,
        3568,
        (("g2_p97_all_others",),),
        "OCR-damaged but source-visible G10 corporation route to G12.",
    )
    flow("g13_p99_to_g18", 99, 1157, 1166)
    flow("g15_p99_to_g18", 99, 1522, 1533)
    flow("g13_p101_to_g18", 101, 1164, 1175)
    flow("g15_p101_to_g18", 101, 1538, 1549)
    flow(
        "g22_p103_extra_job", 103, *byte_find(103, "A.     EXTRA JOB·IN 1986")
    )
    flow(
        "g22_p103_all_others",
        103,
        *byte_find(103, "DB·      ALL   OTHERS-..GO TO G25"),
    )
    flow(
        "g22_p105_extra_job",
        105,
        *byte_find(105, "A.   EXTRA JOB·IN 1986"),
    )
    flow(
        "g22_p105_all_others",
        105,
        *byte_find(105, "DB.        ALL O'l'HERS-+GO TO G2   s"),
    )
    flow(
        "g49_wife_present",
        111,
        *byte_find(111, 'A.        WIFE/"WIFE" IN FU NOW'),
    )
    flow(
        "g49_all_others_exit",
        111,
        *byte_find(111, "DB.          ALL OTHERS - - . TURN TO P. 65, G64"),
    )
    flow(
        "g50_no_exit",
        111,
        817,
        880,
        (("g49_wife_present",),),
    )

    # K and L contribute only narrow work-history fields.  Their entry/exit
    # atoms remain in the graph so those fields do not lose section ancestry.
    flow("k_new_wife_entry", 154, *byte_find(154, "NEW WIFE/", 400))
    flow("k_splitoff_wife_entry", 154, *byte_find(154, 'l . WIFE/"WIFE"'))
    flow("k_reinterview_exit", 154, 1048, 1067)
    flow("k_splitoff_exit", 154, *byte_find(154, "TURN TO P. 98,", 1100))
    k_work_routes = (("k_new_wife_entry",), ("k_splitoff_wife_entry",))
    flow("k44_to_section_l", 158, 2713, 2799, k_work_routes)

    flow("l_splitoff_entry", 161, *byte_find(161, "l. SPLI'l'OFF"))
    flow("l_new_head_entry", 161, *byte_find(161, "l. NEW HEAD"))
    l_work_routes = (("l_splitoff_entry",), ("l_new_head_entry",))
    flow(
        "l5_never_worked_to_l7",
        161,
        2990,
        3111,
        l_work_routes,
        "OCR-damaged but source-visible L5 NEVER WORKED route to L7.",
    )
    flow("l11_yes_to_l13", 162, 1374, 1443, l_work_routes)
    flow("l49_no_to_l55", 166, 421, 429, l_work_routes)
    flow("l57_cover_sheet_exit", 166, 2798, 3245, l_work_routes)
    flow("l58_final_exit", 166, 3511, 3638, l_work_routes)

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
        ("head_codes_1_3",),
        ("head_codes_4_8", "head_paid_work_yes"),
    )
    head_c_route = (("head_codes_4_8", "head_not_working_route"),)
    wife_d_route = (
        ("wife_codes_1_3",),
        ("wife_codes_4_8", "wife_paid_work_yes"),
    )
    wife_e_route = (("wife_codes_4_8", "wife_not_working_route"),)
    supplement_entry_routes = (
        ("head_codes_1_3", "b_supplement_entry"),
        (
            "head_codes_4_8",
            "head_paid_work_yes",
            "b_supplement_entry",
        ),
        *head_c_route,
    )
    supplement_reverse_routes = tuple(
        (*route, "supplement_reverse_entry")
        for route in supplement_entry_routes
    )
    k_work_route = k_work_routes
    l_work_route = l_work_routes

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if page == 18:
            if 393 <= start < 976:
                return (("head_codes_1_3",),)
            if start >= 1030:
                return (("head_codes_4_8",),)
        if page in {35, 36}:
            return supplement_entry_routes
        if page == 37:
            return supplement_reverse_routes
        if 19 <= page <= 50:
            return head_b_route
        if 51 <= page <= 64:
            return head_c_route
        if page == 67:
            if 675 <= start < 1217:
                return (("wife_codes_1_3",),)
            if start >= 1273:
                return (("wife_codes_4_8",),)
        if 68 <= page <= 77:
            return wife_d_route
        if 78 <= page <= 88:
            return wife_e_route
        if page == 95:
            if 766 <= start < 1294:
                return (("g2_p95_farmer",),)
            if start >= 1294:
                return (("g2_p95_farmer",), ("g2_p95_all_others",))
        if page == 97:
            if 831 <= start < 1399:
                return (("g2_p97_farmer",),)
            if start >= 1399:
                return (("g2_p97_farmer",), ("g2_p97_all_others",))
        if page == 103 and start >= 272:
            return (("g22_p103_extra_job",),)
        if page == 105 and start >= 250:
            return (("g22_p105_extra_job",),)
        if page == 111:
            if start >= 717:
                return (("g49_wife_present",),)
        if page == 112:
            return (("g49_wife_present",),)
        if page == 158:
            return k_work_route
        if page in {161, 162, 166}:
            return l_work_route
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
        if page == 102:
            return False
        if page == 104 and kind != R:
            return False
        if page == 112 and kind in {F, J, FA}:
            return False
        if kind == P and (page, start, end) in FALSE_PURPOSE_SPANS:
            return False
        if page == 154 and kind != F:
            return False
        if page == 96 and kind not in {R, FA, P}:
            return False
        if page in {98, 100, 153} and kind != R:
            return False
        if page in {158, 161, 162, 166} and kind not in {F, R}:
            return False
        if page == 111 and kind == C:
            return False
        if page == 111 and kind == P and 1035 <= start < 1235:
            return False
        if page == 159 and start < 924 and kind in {C, P}:
            return False
        if page == 160 and kind == P:
            return False
        if kind in {T, FA, BA}:
            if kind == T:
                # The four lawful work totals are manually re-sliced below;
                # detector lines on two-column grids cross unrelated columns.
                return False
            if kind == FA:
                return page in {95, 97, 99, 101} or (
                    page == 96 and start < 857
                )
            if kind == BA:
                return page in {95, 97, 99, 101, 112}
        if kind == F:
            if page in {17, 20} or (page, start, end) in FALSE_FLOW_SPANS:
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
                    "AGAIN",
                    "SAME JOB",
                    "ANOTHER JOB",
                    "OTHER JOB",
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
                # Only the corrected L5 full-time regular-job label survives.
                return False
            if page in WORK_INCOME_PAGES:
                return page in {95, 97, 103, 105}
            if page == 17:
                return False
            if page in QBYQ_PAGES:
                printed_identifier = annotation._source_printed_identifier(
                    page_texts[page - 1], start
                )
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
                if printed_identifier is None and bare:
                    return False
        if kind == C and page == 17:
            return False
        if kind == M and page in {96, 98, 100, 102, 104}:
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
        (17, 211, 394, "B/C instructions explicitly recur in D/E."),
        (32, 2040, 2064, "B36 explicitly cross-references B11."),
        (32, 2065, 2123, "B37-38 explicitly cross-reference B9-10."),
        (
            32,
            2184,
            2450,
            "Additional changes use the Work History Supplement.",
        ),
        (
            36,
            46,
            333,
            "Supplement repeats across four employment sections and jobs.",
        ),
        (36, 333, 356, "S1-3 explicitly cross-reference B29-31."),
        (36, 357, 377, "S4-9 explicitly cross-reference B33."),
        (36, 378, 401, "S10-15 explicitly cross-reference B36-41."),
        (56, 47, 90, "C20-21 explicitly cross-reference B4 and B6."),
        (56, 91, 516, "C22-44 repeat the B work-history instructions."),
        (56, 581, 835, "C45-64 explicitly repeat B45-63."),
        (56, 836, 970, "C65-72 explicitly repeat B67-74."),
        (56, 970, 1171, "C73-81 explicitly repeat B75-83."),
        (56, 1172, 1233, "C82-88 explicitly repeat B67-74."),
        (
            66,
            177,
            504,
            "D/E role definitions explicitly hand off to the Glossary.",
        ),
        (
            66,
            505,
            746,
            "D/E explicitly parallel B/C and reuse their objectives.",
        ),
        (96, 100, 361, "G3-24 and G52 income require B/C and D/E work hours."),
        (
            96,
            362,
            531,
            "Employment-section work explicitly requires G income.",
        ),
        (98, 48, 256, "G5 explicitly reuses G3 and G4 amounts."),
        (
            98,
            257,
            595,
            "G6-8 are a repeated business-income instruction block.",
        ),
        (98, 596, 798, "G9 explicitly hands work hours back to B/C and D/E."),
        (102, 47, 842, "Roomer income explicitly requires B/C work hours."),
        (
            102,
            1627,
            1936,
            "G21 explicitly sends missing work hours back to B/C.",
        ),
        (
            103,
            110,
            175,
            "G22 explicitly cross-references B67 and C65 extra jobs.",
        ),
        (103, 272, 399, "G23 repeats the extra-job earnings inclusion check."),
        (
            105,
            105,
            156,
            "G22 explicitly cross-references B67 and C65 extra jobs.",
        ),
        (105, 250, 375, "G23 repeats the extra-job earnings inclusion check."),
        (
            112,
            615,
            1053,
            "G51-52 explicitly link D/E work and G income both ways.",
        ),
        (159, 824, 923, "L4-5 explicitly cross-reference B9-11."),
        (
            160,
            1266,
            1558,
            "L14-58 explicitly duplicate and cross-reference Section K.",
        ),
    )
    for page, start, end, note in repeat_blocks:
        manual(page, start, end, (A,), note)
    for page, start, end, note in (
        (21, 1004, 1087, "Complete explicit repeat-B10 instruction."),
        (37, 265, 376, "Complete same-employer question."),
        (40, 476, 532, "Complete B57-59 cross-reference sentence."),
        (40, 2086, 2150, "Complete printed AGAIN instruction sentence."),
        (46, 134, 292, "Complete repeated extra-job rule."),
    ):
        manual(page, start, end, (A,), note)
    manual(
        36,
        357,
        377,
        (P,),
        "S4-9 identifies the repeated B33 field purpose.",
    )
    manual(
        36,
        402,
        522,
        (P,),
        "S16 states the questionnaire-return purpose after the supplement.",
    )
    manual(36, 162, 167, (R,), "Exact plural Head role in supplement scope.")
    manual(
        36,
        190,
        204,
        (R,),
        "Exact plural Wife role in supplement scope.",
    )

    # Candidate-free corrections on the employment instruction pages.
    manual(18, 407, 504, (C,), "Complete codes 1-3 work-status context.")
    manual(18, 2084, 2097, (C,), "Exact code-7 student context.")
    manual(32, 686, 764, (P,), "Complete B30-31 identifier purpose line.")

    # Filled copies sometimes serialize handwritten answers into the same
    # physical line as a printed prompt. Keep only the exact printed prefix.
    for page, start, end in (
        (18, 1140, 1154),
        (19, 602, 621),
        (19, 632, 677),
        (23, 656, 677),
        (23, 693, 743),
        (25, 1091, 1101),
        (25, 1447, 1460),
        (25, 2123, 2131),
        (25, 2198, 2222),
        (29, 2681, 2733),
        (39, 2236, 2259),
        (41, 1204, 1257),
        (41, 2175, 2262),
        (43, 1357, 1416),
        (43, 1704, 1803),
        (43, 2161, 2196),
        (43, 2773, 2861),
        (45, 671, 740),
        (45, 835, 861),
        (45, 933, 953),
        (45, 1262, 1275),
        (45, 2118, 2142),
        (45, 2432, 2453),
        (49, 344, 353),
        (49, 390, 421),
        (49, 1157, 1175),
        (49, 1204, 1219),
        (49, 1764, 1777),
        (49, 1811, 1823),
        (68, 606, 620),
        (68, 635, 643),
        (69, 1515, 1528),
        (69, 2010, 2018),
        (69, 2077, 2101),
        (78, 515, 535),
        (82, 2283, 2304),
        (95, 2063, 2106),
        (95, 2316, 2358),
        (97, 2215, 2259),
        (97, 2534, 2563),
        (99, 712, 738),
        (99, 773, 788),
        (99, 1341, 1372),
        (99, 2380, 2396),
        (99, 2404, 2416),
        (99, 2430, 2443),
        (99, 4084, 4093),
        (101, 718, 745),
        (101, 777, 789),
        (101, 1354, 1385),
        (101, 2444, 2460),
        (101, 2468, 2480),
        (101, 2495, 2509),
        (101, 4226, 4235),
    ):
        manual(
            page,
            start,
            end,
            (P,),
            "Exact printed purpose prefix; filled-answer suffix excluded.",
        )

    # Printed AGAIN labels occur twice on each two-column continuation row.
    # Preserve each visible atom independently rather than one cross-column
    # detector span.
    for page in (45, 47, 63, 64, 76, 77, 87, 88):
        offsets = annotation.stage1_candidates._utf8_offsets(
            page_texts[page - 1]
        )
        for match in re.finditer(r"\bAGAIN\b", page_texts[page - 1]):
            manual(
                page,
                offsets[match.start()],
                offsets[match.end()],
                (A,),
                "Atomic printed AGAIN continuation instruction.",
            )
    for page, start, end in (
        (45, 3239, 3248),
        (45, 3283, 3292),
        (47, 3191, 3200),
        (47, 3217, 3226),
        (63, 2682, 2691),
        (63, 2721, 2730),
        (64, 3313, 3322),
        (64, 3348, 3357),
        (76, 2409, 2418),
        (76, 2444, 2453),
        (77, 3329, 3338),
        (77, 3361, 3370),
        (87, 2766, 2775),
        (87, 2803, 2812),
        (88, 3474, 3483),
        (88, 3508, 3517),
    ):
        manual(
            page,
            start,
            end,
            (A,),
            "Complete printed identifier-plus-AGAIN repeat atom.",
        )

    # Section G source blocks: retain only work-linked income constructs and
    # replace line/token fragments with the complete printed semantic unit.
    manual(96, 598, 857, (C, A), "Complete G2 farm-work handoff context.")
    manual(96, 598, 673, (P,), "G2 identifies the employment lookup purpose.")
    manual(98, 257, 332, (P,), "G6-8 business-income field purpose line.")
    manual(98, 596, 798, (C,), "Complete G9 work-hours handoff context.")
    manual(98, 596, 676, (P,), "G9 work-hours handoff purpose line.")

    manual(95, 766, 842, (P,), "Complete G3 identifier purpose line.")
    manual(97, 831, 912, (P,), "Complete G3 identifier purpose line.")
    manual(97, 1399, 1499, (P,), "Complete G6 identifier purpose line.")
    manual(95, 755, 765, (M,), "Exact G3 total-receipts field label.")
    manual(97, 820, 830, (M,), "Exact G3 total-receipts field label.")

    # Poppler serializes the G13/G16 and G14/G17 two-column prompts onto the
    # same lines. Preserve the two independently visible labels as disjoint
    # atoms instead of accepting each cross-column candidate span.
    for page, phrases in (
        (
            99,
            (
                "Gl3.   How much did you (HEAD) earn",
                "Gl6.       Did you have any income from",
                "Gl4.   In addition to this, did you",
                "Gl7.       How much was that?",
            ),
        ),
        (
            101,
            (
                "Gl3.     How much did you (HEAD) earn",
                "Gl6.       Did you have any income from",
                "Gl , .   In addition to this, did you",
                "Gl7.       How IIUch WU that?",
            ),
        ),
    ):
        for phrase in phrases:
            manual(
                page,
                *byte_find(page, phrase),
                (P,),
                "Exact purpose atom split from a two-column source line.",
            )
    manual(99, 1660, 1756, (P,), "Complete G18 identifier purpose line.")
    manual(101, 1706, 1805, (P,), "Complete G18 identifier purpose line.")
    manual(
        99, 2658, 2691, (BA,), "Exact professional-practice aggregate label."
    )
    manual(
        101, 2622, 2655, (BA,), "Exact professional-practice aggregate label."
    )
    manual(99, 2884, 2889, (BA,), "Exact trade aggregate-label continuation.")
    manual(101, 3246, 3251, (BA,), "Exact trade aggregate-label continuation.")
    manual(99, 3104, 3132, (FA,), "Exact market-gardening aggregate label.")
    manual(101, 3605, 3633, (FA,), "Exact market-gardening aggregate label.")

    manual(100, 47, 179, (C,), "Complete G12 wage-work context block.")
    manual(100, 180, 434, (C,), "Complete G13 current-Head wage context.")
    manual(
        100, 1020, 1432, (A,), "G13 avoids duplicate business and wage income."
    )
    manual(100, 1433, 1616, (C, A), "G14-15 avoid duplicate income reporting.")
    manual(
        100, 1617, 1728, (C, M), "G16-17 commissions-only earnings component."
    )
    manual(
        100, 1729, 2302, (C,), "Complete G18a professional-practice context."
    )
    manual(
        100,
        2095,
        2302,
        (A,),
        "G18a excludes income already reported at G11/G13.",
    )
    manual(
        100,
        2303,
        2593,
        (C, A),
        "G18b redirects farming income by job context.",
    )

    manual(102, 47, 842, (C,), "Complete roomer-income work linkage context.")
    manual(102, 1184, 1936, (C,), "Complete G19-21 work-hours context.")
    manual(103, 272, 399, (P,), "Complete G23 extra-job inclusion prompt.")
    manual(103, 448, 663, (M,), "Complete G24 extra-job earnings field.")
    manual(103, 493, 552, (P,), "Exact printed G24 purpose prompt.")
    manual(104, 47, 178, (C,), "Complete G22-24 work-income objective.")
    manual(104, 47, 127, (P,), "G22-24 work-income purpose statement.")
    manual(105, 250, 375, (P,), "Complete G23 extra-job inclusion prompt.")
    manual(105, 421, 628, (M,), "Complete G24 extra-job earnings field.")
    manual(105, 461, 526, (P,), "Exact printed G24 purpose prompt.")

    manual(
        99,
        *byte_find(99, "altogether from wages or"),
        (T,),
        "Exact Head all-wages total label.",
    )
    manual(
        101,
        *byte_find(101, "altogether from wages or"),
        (T,),
        "Exact Head all-wages total label.",
    )
    manual(111, 1102, 1179, (T,), "Exact Wife all-work total question label.")
    manual(111, 1195, 1235, (P,), "Complete G52 deduction purpose line.")
    manual(
        111,
        *byte_find(111, "TOTAL EARNINGS l'RCio! WORK IN 1986"),
        (T,),
        "Exact Wife total-earnings printed label.",
    )
    manual(
        112, 615, 1053, (C,), "Complete G51-52 work-income linkage context."
    )
    manual(
        112,
        *byte_find(112, "all work sources"),
        (T,),
        "Exact Wife all-work-sources total label.",
    )

    # Narrow K/L lifetime-work and work-history scope.  Objective prose that
    # merely mentions jobs or occupations is context/purpose, not a job slot.
    manual(153, 1648, 1729, (C, P), "K44 lifetime-work objective block.")
    manual(
        153,
        *byte_find(153, 'New Wife/"Wife"'),
        (R,),
        "Exact New-Wife role atom.",
    )
    manual(153, 1920, 1971, (C, P), "Complete K45 full-time-work objective.")

    manual(154, 505, 514, (R,), "Exact New-Wife checkpoint role atom.")
    manual(154, 568, 579, (R,), "Exact Wife checkpoint role atom.")
    for start, end in (
        (590, 594),
        (684, 690),
        (718, 722),
        (735, 739),
        (766, 772),
        (844, 850),
    ):
        manual(154, start, end, (R,), "Exact K1 checkpoint role atom.")

    manual(158, 2614, 2713, (C, P), "Complete K44 lifetime-work question.")
    manual(158, 2800, 2920, (C, P), "Complete K45 full-time-work prompt.")

    manual(
        159, 924, 1453, (C, P), "Complete L6 occupation-continuity objective."
    )
    manual(
        160, 517, 1031, (C,), "Complete L11-12 job-mobility objective context."
    )

    manual(161, 2564, 2648, (C, P), "Complete L5 first-regular-job question.")
    manual(
        161,
        *byte_find(161, "first full-time regular job"),
        (J,),
        "Exact L5 first regular-job anchor.",
    )
    manual(
        161, 3112, 3254, (C, P), "Complete L6 occupation-continuity prompt."
    )

    manual(162, 1126, 1261, (C, P), "Complete L11 move-for-job question.")
    manual(162, 1443, 1536, (C, P), "Complete L12 declined-job question.")

    manual(166, 2704, 2797, (C, P), "Complete L57 lifetime-work question.")
    manual(166, 3246, 3347, (C, P), "Complete L58 full-time-work question.")

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
            if (
                kind == M
                and page in {99, 101}
                and spec["utf8_byte_start"] < 300
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
        elif parent_ids and parent_basis == "g12_role_total":
            parent_note = (
                "The G12 wage component was verified against its G13 "
                "all-wages role-total label, not the expressly excluded "
                "unincorporated-business aggregate."
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
            "whole_page_review": "all_166_pages_including_empty_occurrence_pages",
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
