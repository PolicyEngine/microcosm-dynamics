#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 35.

The 199-page 1985 QxQ was reviewed page by page from the authenticated
Poppler text.  This helper encodes that review as explicit semantic page
windows, exact source-derived lexical atoms, and reviewer-selected routing
blocks.  It never opens the committed stage-1 candidate artifact; candidate
bytes are joined only later by the sealed annotation builder.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_035_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]

# The page review is deliberately narrower than the stage-1 lexical domain.
# In particular, children, transfers, other-FU-member work, generic education,
# health, and housework prose do not become R_Q evidence merely because they
# contain words such as ``work``, ``pay``, ``farm``, or ``Wife``.
ROLE_ONLY_PAGES = frozenset({*range(1, 7), *range(13, 16), *range(61, 67)})
HEAD_EMPLOYMENT_PAGES = frozenset({*range(16, 61)} - {36})
HEAD_INCOME_PAGES = frozenset({82, 83, 84, 85, 86, 87, 88, 89, 90, 92, 97, 98})
HEAD_BACKGROUND_WORK_PAGES = frozenset({115, 116, 117, 118, 122, 123, 127})
WIFE_EMPLOYMENT_PAGES = frozenset(range(136, 162))
EXPLICIT_PARALLEL_EVIDENCE_PAGES = frozenset({135, 187})
WIFE_BACKGROUND_WORK_PAGES = frozenset({188, 189, 191, 192})

SEMANTIC_PAGES = frozenset().union(
    ROLE_ONLY_PAGES,
    HEAD_EMPLOYMENT_PAGES,
    HEAD_INCOME_PAGES,
    HEAD_BACKGROUND_WORK_PAGES,
    WIFE_EMPLOYMENT_PAGES,
    EXPLICIT_PARALLEL_EVIDENCE_PAGES,
    WIFE_BACKGROUND_WORK_PAGES,
)

# These line windows are the surviving byte regions after whole-page review.
# Values are one-based inclusive physical-line ranges in the pinned Poppler
# strings.  Pages absent here use their complete text.
REVIEWED_LINE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    82: ((6, 46),),
    83: ((1, 54),),
    84: ((1, 33),),
    85: ((1, 47),),
    86: ((1, 84),),
    87: ((1, 29),),
    88: ((1, 97),),
    89: ((6, 7),),
    90: ((4, 16),),
    92: ((4, 17),),
    97: ((10, 16),),
    98: ((15, 50),),
    115: ((5, 15), (24, 34)),
    116: ((6, 15), (38, 54)),
    117: ((10, 17),),
    118: ((28, 36),),
    122: ((32, 40),),
    123: ((40, 44),),
    127: ((6, 13),),
    188: ((4, 15), (32, 49)),
    189: ((28, 38),),
    191: ((35, 43),),
    192: ((38, 40),),
}

# Audited byte windows supersede the convenient line notation above.  They
# deliberately trim page furniture and adjacent nonemployment questions.
REVIEWED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    82: ((89, 599), (601, 890), (891, 2145)),
    83: ((346, 1358), (1360, 3437)),
    84: ((38, 1672),),
    85: ((40, 2665),),
    86: ((66, 1485), (1486, 4640)),
    87: ((40, 1856),),
    88: ((62, 1374), (1376, 4841)),
    89: ((41, 171),),
    90: ((60, 605),),
    92: ((59, 651),),
    97: ((471, 881),),
    98: ((307, 1275),),
    115: ((91, 724), (1201, 1813)),
    116: ((128, 355), (1742, 2536)),
    117: ((490, 998),),
    118: ((1198, 1639),),
    122: ((1190, 1528),),
    123: ((1417, 1613),),
    127: ((108, 605),),
    135: ((1263, 1816),),
    136: ((51, 1380),),
    187: ((171, 486),),
    188: ((153, 366), (1470, 1558), (2090, 2233)),
    189: ((1206, 1331), (1401, 1460), (1470, 1578)),
    191: ((1171, 1226), (1290, 1354)),
    192: ((1707, 1744), (1817, 1877)),
}

# Kind-level decisions for pages whose worklike wording is especially prone
# to false promotion.  F/R/J/M/T/f/b/C/P/A abbreviations are expanded here to
# keep the reviewer decision table compact and inspectable.
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

PAGE_KIND_ALLOWLIST: dict[int, frozenset[str]] = {
    **{page: frozenset({R}) for page in ROLE_ONLY_PAGES},
    82: frozenset({R, J, M, FA, C, P, A}),
    83: frozenset({F, R, J, M, FA, BA, C, P, A}),
    84: frozenset({R, J, M, FA, BA, C, P, A}),
    85: frozenset({R, J, M, T, FA, BA, C, P, A}),
    86: frozenset({F, R, J, M, T, FA, BA, C, P, A}),
    87: frozenset({R, J, M, FA, BA, C, P, A}),
    88: frozenset({F, R, J, M, T, FA, BA, C, P, A}),
    89: frozenset({R, J, M, C, P, A}),
    90: frozenset({F, R, J, M, T, C, P, A}),
    92: frozenset({F, R, J, M, T, C, P, A}),
    97: frozenset({R, M, T, BA, C, P, A}),
    98: frozenset({F, R, J, M, T, BA, C, P, A}),
    115: frozenset({R, J, C, P, A}),
    116: frozenset({F, R, J, C, P, A}),
    117: frozenset({C}),
    118: frozenset({F, C}),
    122: frozenset({F, C, P}),
    123: frozenset({C, P}),
    127: frozenset({R, C, A}),
    135: frozenset({R, A}),
    136: frozenset({F, R, P}),
    137: frozenset({F, R, J, C, P}),
    138: frozenset({F, R, J, C, P}),
    139: frozenset({F, R, J, M, C, P}),
    140: frozenset({F, R, J, C}),
    141: frozenset({F, R, J, M, C, P, A}),
    142: frozenset({F, R, J, C, P}),
    143: frozenset({F, R, J, M, C, P, A}),
    144: frozenset({F, R, J, M, C, P}),
    145: frozenset({F, R, C, P, A}),
    146: frozenset({F, J, C, P}),
    147: frozenset({F, R, J, M, C, P, A}),
    148: frozenset({F, R, J, C, P, A}),
    149: frozenset({F, R, J, C, P}),
    150: frozenset({F, R, C, P}),
    151: frozenset({F, R, J, C, P}),
    152: frozenset({F, J, C, P}),
    153: frozenset({F, R, J, M, C, P}),
    154: frozenset({F, R, J, C, P}),
    155: frozenset({F, R, J, M, C, P, A}),
    156: frozenset({F, R, J, M, C, P}),
    157: frozenset({F, R, C, P, A}),
    158: frozenset({F, J, C, P}),
    159: frozenset({F, R, J, M, C, P, A}),
    160: frozenset({F, R, J, C, P, A}),
    161: frozenset({F, R, C, P}),
    187: frozenset({R, A}),
    188: frozenset({F, R, J, C, P}),
    189: frozenset({F, C}),
    191: frozenset({C, P}),
    192: frozenset({C, P}),
}

HEAD_PURPOSE_PAGES = frozenset(
    {18, 19, 24, 28, 30, 32, 34, 35, 38, 40, 42, 44, 46, 48, 49}
    | set(range(51, 61))
)

PURPOSE_ALLOWED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    18: ((0, 2392),),
    19: ((0, 423), (714, 1561)),
    28: ((0, 2602),),
    48: ((704, 803), (1087, 1136), (1408, 1488), (1623, 1702)),
    137: ((0, 2657),),
    141: ((271, 2599),),
    143: ((296, 2811),),
    149: ((1440, 2370),),
    150: ((865, 965), (1253, 1309), (1595, 1662), (1799, 1844)),
    155: ((290, 2045),),
}

PURPOSE_EXCLUDED_BYTE_WINDOWS: dict[int, tuple[tuple[int, int], ...]] = {
    18: ((1004, 1011), (1093, 1110), (2143, 2235)),
    24: (
        (167, 251),
        (266, 314),
        (383, 434),
        (716, 729),
        (1010, 1018),
        (1365, 1384),
        (1394, 1413),
        (1428, 1442),
        (1484, 1568),
    ),
    34: ((1659, 1700),),
    38: ((2069, 2094),),
    44: ((338, 419), (1209, 1213)),
    46: ((362, 442), (488, 523), (1017, 1062), (1551, 1611)),
    51: ((772, 1934),),
    90: ((60, 87),),
    92: ((59, 87),),
    137: (
        (1103, 1179),
        (2157, 2168),
        (2195, 2284),
        (2303, 2371),
        (2385, 2386),
    ),
    138: ((486, 542), (770, 791), (956, 985)),
    146: ((695, 744),),
    152: ((1119, 1980),),
}

REMUNERATION_EXCLUDED_SPANS = frozenset(
    {
        # ``wage`` is only the lexical prefix of ``wage-earners`` here.
        (85, 255, 259),
        # This is a carpenter example in explanatory prose, not a printed
        # remuneration component for the questionnaire field.
        (85, 2066, 2071),
        (20, 271, 277),
        (21, 280, 290),
        (22, 57, 63),
        # F3 lists wages/custom-work payments as farm operating expenses;
        # neither phrase names remuneration received by the respondent.
        (82, 1895, 1900),
        (82, 1949, 1962),
    }
)

ROLE_EXCLUDED_SPANS = frozenset(
    {
        # Historical spouse-name wording does not bind the named person to
        # the questionnaire Wife/"Wife" role.
        (62, 1390, 1399),
        (62, 1402, 1408),
        (63, 290, 299),
        (63, 301, 307),
        (64, 458, 465),
        (64, 515, 521),
        # These are lower-case family-history references to a respondent's
        # present wife, not questionnaire Wife-role labels.
        (66, 1586, 1590),
        (66, 1727, 1731),
        (140, 587, 594),
        (140, 990, 994),
    }
)

JOB_EXCLUDED_SPANS = frozenset(
    {
        # G6 objective prose mentions high-school jobs generically rather
        # than printing a source job-slot anchor.
        (115, 1561, 1572),
        (115, 1665, 1669),
        (140, 1116, 1119),
        (140, 1360, 1363),
        (140, 1436, 1439),
        (141, 2719, 2722),
        (141, 2804, 2807),
        (142, 1296, 1299),
        (146, 1203, 1206),
        (148, 120, 123),
        (154, 850, 853),
        (158, 1429, 1432),
        (160, 243, 246),
    }
)

FLOW_EXCLUDED_SPANS = frozenset(
    {
        (22, 1670, 1729),
        (25, 435, 487),
        (26, 488, 572),
        (28, 68, 99),
        (29, 118, 170),
        (30, 813, 820),
        (31, 63, 90),
        (34, 2964, 2994),
        (35, 64, 95),
        (35, 2830, 2861),
        (38, 1761, 1826),
        (39, 613, 663),
        (39, 1283, 1336),
        (41, 1973, 2024),
        (43, 418, 471),
        (42, 2749, 2754),
        (44, 3810, 3817),
        (44, 4229, 4236),
        (47, 872, 934),
        (54, 61, 88),
        (53, 892, 899),
        (58, 2549, 2554),
        (58, 2958, 2963),
        (59, 3628, 3635),
        (59, 4051, 4058),
        (138, 571, 634),
        (137, 3565, 3582),
        (139, 1215, 1222),
        (139, 1562, 1617),
        (141, 1661, 1679),
        (141, 1834, 1852),
        (142, 1397, 1404),
        (142, 3728, 3746),
        (142, 3917, 3935),
        (144, 892, 911),
        (144, 1813, 1851),
        (146, 1844, 1862),
        (147, 2134, 2139),
        (148, 2671, 2678),
        (149, 1594, 1686),
        (149, 1804, 1882),
        (149, 694, 704),
        (149, 1056, 1066),
        (150, 1034, 1051),
        (151, 1209, 1234),
        (152, 2557, 2575),
        (152, 2744, 2762),
        (153, 1260, 1278),
        (153, 1428, 1447),
        (154, 3349, 3367),
        (154, 3573, 3591),
        (154, 962, 1086),
        (154, 962, 969),
        (156, 873, 891),
        (156, 1070, 1088),
        (156, 1758, 1796),
        (158, 2197, 2255),
        (159, 302, 360),
        (159, 2226, 2231),
        (159, 2611, 2616),
        (159, 3102, 3171),
        (160, 463, 508),
        (160, 3091, 3098),
        (160, 3494, 3501),
        (160, 799, 875),
        (160, 1522, 1574),
        (161, 170, 247),
        (161, 466, 498),
    }
)

MANUAL_REPEAT_ONLY_PAGES = frozenset(
    {82, 84, 85, 87, 97, 115, 127, 135, 141, 143, 147, 148, 155, 159, 160, 187}
)

REPEAT_EXCLUDED_SPANS = frozenset(
    {
        # Generic job-history prose and routing arms are not repeat/alias
        # evidence.  They are either retained in their proper semantic kind
        # or rejected outright after whole-page review.
        (27, 1465, 1519),
        (29, 249, 303),
        (16, 437, 490),
        (20, 1207, 1254),
        (29, 1073, 1128),
        (30, 178, 258),
        (31, 183, 213),
        (31, 212, 232),
        (34, 915, 1005),
        (34, 1956, 1995),
        (35, 151, 179),
        (35, 162, 178),
        (35, 277, 362),
        (37, 2058, 2122),
        (41, 174, 231),
        (53, 269, 350),
        (54, 145, 182),
        (54, 161, 181),
        (42, 2804, 2873),
        (44, 4292, 4357),
        (58, 3015, 3076),
        (59, 4116, 4175),
    }
)

COMPOSITE_WIFE_RE = re.compile(
    r"\(?(?:WIFE(?:S|['\u2019]S)?\s*/\s*[\"\u201c]\s*WIFE(?:S|['\u2019]S)?[,\.]?\s*[\"\u201d])\)?",
    re.IGNORECASE,
)

FLOW_EXCLUSION_MARKERS = (
    "IF NECESSARY",
    "IF VOLUNTEERED",
    "IF R VOLUNTEERS",
    "IF R MENTIONS",
    "IF NOT CLEAR",
    "IF DOESN'T SPECIFY",
    "IF DOES NOT SPECIFY",
)
FLOW_ACTION_MARKERS = (
    "GO TO",
    "TURN TO",
    "CHECKPOINT",
    "DO NOT ASK",
    "DON'T ASK",
    "SKIP",
    "PROCEED",
    "ASK SECTION",
    "ASK C",
    "ASK B",
    "ASK J",
    "ASK K",
    "CHECK THAT BOX",
    "MARK ",
    "RECORD ",
    "PROBE ",
    "USE THE",
)

MANUAL_REMUNERATION_RE = re.compile(
    r"\b(?:labor\s+income|income\s+from\s+(?:work|wages?|salar(?:y|ies)|"
    r"jobs?|business|farm)|wages?\s+and\s+salar(?:y|ies)|retirement\s+pay|"
    r"pensions?|annuities|unemployment\s+compensation|"
    r"workers?\s+compensation)\b",
    re.IGNORECASE,
)


def _byte_find(page_text: str, needle: str, start: int = 0) -> tuple[int, int]:
    page_bytes = page_text.encode("utf-8")
    needle_bytes = needle.encode("utf-8")
    position = page_bytes.find(needle_bytes, start)
    if position < 0:
        raise ValueError(f"source phrase not found: {needle!r}")
    return position, position + len(needle_bytes)


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

    def reviewed_windows(page: int) -> tuple[tuple[int, int], ...]:
        explicit = REVIEWED_BYTE_WINDOWS.get(page)
        if explicit is not None:
            return explicit
        line_ranges = REVIEWED_LINE_WINDOWS.get(page)
        if line_ranges is None:
            return ((0, len(page_texts[page - 1].encode("utf-8"))),)
        physical_lines = page_texts[page - 1].splitlines(keepends=True)
        byte_starts: list[int] = []
        offset = 0
        for physical_line in physical_lines:
            byte_starts.append(offset)
            offset += len(physical_line.encode("utf-8"))
        windows: list[tuple[int, int]] = []
        for first_line, last_line in line_ranges:
            if not 1 <= first_line <= last_line <= len(physical_lines):
                raise ValueError(f"reviewed line window drift on page {page}")
            start = byte_starts[first_line - 1]
            end = (
                byte_starts[last_line]
                if last_line < len(physical_lines)
                else offset
            )
            windows.append((start, end))
        return tuple(windows)

    def inside_reviewed_window(page: int, start: int, end: int) -> bool:
        return any(
            window_start <= start < end <= window_end
            for window_start, window_end in reviewed_windows(page)
        )

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        page_bytes = page_texts[page - 1].encode("utf-8")
        while start < end and page_bytes[start : start + 1] in b" \t\r\n":
            start += 1
        while end > start and page_bytes[end - 1 : end] in b" \t\r\n":
            end -= 1
        if start >= end:
            raise ValueError(f"empty span after trimming: page={page}")
        page_bytes[start:end].decode("utf-8", errors="strict")
        return start, end

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
            existing_key
            for existing_key in specs
            if existing_key[0] == page
            and existing_key[3] == kind
            and existing_key[1] < end
            and start < existing_key[2]
        ]
        if overlaps and not replace_overlap:
            return False
        for existing_key in overlaps:
            del specs[existing_key]
        specs[key] = {
            "page": page,
            "start": start,
            "end": end,
            "kind": kind,
            "routes": {tuple(route) for route in routes},
            "note": note,
        }
        return True

    # The four source-explicit section routes are fixed before lexical source
    # detection.  The three B arms all resolve the same employment pages and
    # are deliberately retained as a complete alternative-path set.
    flow_defs: list[dict[str, Any]] = []

    def flow(
        symbol: str,
        page: int,
        start: int,
        end: int,
        parents: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source routing block retained after whole-page review.",
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

    flow("head_working_now", 16, 664, 1025)
    flow("head_temporarily_laid_off", 16, 1026, 1514)
    flow("head_other_paid_work_now", 16, 1515, 2028)
    flow("head_not_working_condition", 16, 2029, 2914)
    flow(
        "head_not_working_section",
        17,
        31,
        146,
        (("head_not_working_condition",),),
    )
    head_not_working_route = (
        "head_not_working_condition",
        "head_not_working_section",
    )
    flow("c1_yes_route", 47, 276, 358, (head_not_working_route,))
    flow("c1_no_route", 47, 359, 393, (head_not_working_route,))

    # Source-visible B-section routing families.  Each downstream merge keeps
    # every printed ancestry path; repeat-loop backs are evidence atoms but do
    # not become parents, which prevents artificial branch cycles.
    head_working_symbol_routes = (
        ("head_working_now",),
        ("head_temporarily_laid_off",),
        ("head_other_paid_work_now",),
    )
    flow("b34_employee", 28, 183, 213, head_working_symbol_routes)
    flow("b34_all_others", 28, 243, 277, head_working_symbol_routes)
    b34_employee_routes = tuple(
        (*route, "b34_employee") for route in head_working_symbol_routes
    )
    b34_all_others_routes = tuple(
        (*route, "b34_all_others") for route in head_working_symbol_routes
    )
    b34_merge_routes = (*b34_employee_routes, *b34_all_others_routes)

    for symbol, start, end in (
        ("b46_same_employer", 198, 233),
        ("b46_self_employed", 235, 277),
        ("b46_different_employer", 280, 332),
    ):
        flow(symbol, 31, start, end, b34_merge_routes)
    b46_same_routes = tuple(
        (*route, "b46_same_employer") for route in b34_merge_routes
    )
    b46_self_routes = tuple(
        (*route, "b46_self_employed") for route in b34_merge_routes
    )
    b46_different_routes = tuple(
        (*route, "b46_different_employer") for route in b34_merge_routes
    )
    b46_merge_routes = (
        *b46_same_routes,
        *b46_self_routes,
        *b46_different_routes,
    )

    for symbol, start, end in (
        ("s6_same_employer", 151, 179),
        ("s6_self_employed", 179, 215),
        ("s6_different_employer", 215, 261),
    ):
        flow(symbol, 35, start, end)
    s6_merge_routes = (
        ("s6_same_employer",),
        ("s6_self_employed",),
        ("s6_different_employer",),
    )

    flow("b75_zero", 40, 1928, 2041, b34_merge_routes)
    flow("b75_worked_weeks", 40, 2081, 2094, b34_merge_routes)
    b75_zero_routes = tuple((*route, "b75_zero") for route in b34_merge_routes)
    b75_worked_routes = tuple(
        (*route, "b75_worked_weeks") for route in b34_merge_routes
    )
    flow("b79_no_to_b87", 42, 262, 290, b75_worked_routes)
    flow("b79_yes_first_extra_job", 42, 340, 355, b75_worked_routes)
    b79_no_routes = tuple(
        (*route, "b79_no_to_b87") for route in b75_worked_routes
    )
    b79_yes_routes = tuple(
        (*route, "b79_yes_first_extra_job") for route in b75_worked_routes
    )
    flow("b86_first_again", 42, 2804, 2813, b79_yes_routes)
    b86_first_again_routes = tuple(
        (*route, "b86_first_again") for route in b79_yes_routes
    )
    flow(
        "b86_second_again",
        42,
        2850,
        2859,
        b86_first_again_routes,
    )
    flow(
        "b86_done_to_b87",
        42,
        2870,
        2873,
        (*b79_yes_routes, *b86_first_again_routes),
    )
    b86_done_direct_routes = tuple(
        (*route, "b86_done_to_b87") for route in b79_yes_routes
    )
    b86_done_repeat_routes = tuple(
        (*route, "b86_done_to_b87") for route in b86_first_again_routes
    )
    b87_merge_routes = (
        *b75_zero_routes,
        *b79_no_routes,
        *b86_done_direct_routes,
        *b86_done_repeat_routes,
    )

    flow("b93_some_weeks", 44, 1256, 1269, b87_merge_routes)
    flow("b93_none_to_b96", 44, 1305, 1337, b87_merge_routes)
    b93_some_routes = tuple(
        (*route, "b93_some_weeks") for route in b87_merge_routes
    )
    b93_none_routes = tuple(
        (*route, "b93_none_to_b96") for route in b87_merge_routes
    )
    b93_merge_routes = (*b93_some_routes, *b93_none_routes)
    flow("b96_yes", 44, 2006, 2010, b93_merge_routes)
    flow("b96_no_to_b103", 44, 2163, 2180, b93_merge_routes)
    b96_yes_routes = tuple((*route, "b96_yes") for route in b93_merge_routes)
    b96_no_routes = tuple(
        (*route, "b96_no_to_b103") for route in b93_merge_routes
    )
    flow("b102_first_again", 44, 4292, 4302, b96_yes_routes)
    b102_first_again_routes = tuple(
        (*route, "b102_first_again") for route in b96_yes_routes
    )
    flow("b102_first_done", 44, 4309, 4318, b96_yes_routes)
    flow("b102_second_again", 44, 4324, 4334, b102_first_again_routes)
    flow("b102_second_done", 44, 4348, 4357, b102_first_again_routes)
    b103_merge_routes = (
        *b96_no_routes,
        *(tuple((*route, "b102_first_done") for route in b96_yes_routes)),
        *(
            tuple(
                (*route, "b102_second_done")
                for route in b102_first_again_routes
            )
        ),
    )

    # C-section position-type and work-history routing families.
    c1_symbol_routes = (
        (*head_not_working_route, "c1_yes_route"),
        (*head_not_working_route, "c1_no_route"),
    )
    for symbol, start, end in (
        ("c37_same_employer", 145, 182),
        ("c37_self_employed", 283, 327),
        ("c37_different_employer", 329, 385),
    ):
        flow(symbol, 54, start, end, c1_symbol_routes)
    c37_same_routes = tuple(
        (*route, "c37_same_employer") for route in c1_symbol_routes
    )
    c37_self_routes = tuple(
        (*route, "c37_self_employed") for route in c1_symbol_routes
    )
    c37_different_routes = tuple(
        (*route, "c37_different_employer") for route in c1_symbol_routes
    )
    c37_merge_routes = (
        *c37_same_routes,
        *c37_self_routes,
        *c37_different_routes,
    )

    flow("c66_zero", 57, 1889, 1905, c1_symbol_routes)
    flow("c66_worked_weeks", 57, 2222, 2235, c1_symbol_routes)
    flow("c66_all_rest", 57, 2298, 2311, c1_symbol_routes)
    c66_zero_routes = tuple((*route, "c66_zero") for route in c1_symbol_routes)
    c66_worked_routes = tuple(
        (*route, "c66_worked_weeks") for route in c1_symbol_routes
    )
    c66_all_rest_routes = tuple(
        (*route, "c66_all_rest") for route in c1_symbol_routes
    )
    c66_merge_routes = (
        *c66_zero_routes,
        *c66_worked_routes,
        *c66_all_rest_routes,
    )
    flow("c68_yes", 58, 305, 311, c66_merge_routes)
    flow("c68_no_to_c76", 58, 457, 487, c66_merge_routes)
    c68_yes_routes = tuple((*route, "c68_yes") for route in c66_merge_routes)
    c68_no_routes = tuple(
        (*route, "c68_no_to_c76") for route in c66_merge_routes
    )
    flow("c75_first_again", 58, 3015, 3024, c68_yes_routes)
    c75_first_again_routes = tuple(
        (*route, "c75_first_again") for route in c68_yes_routes
    )
    flow("c75_first_done", 58, 3040, 3043, c68_yes_routes)
    flow("c75_second_again", 58, 3050, 3059, c75_first_again_routes)
    flow("c75_second_done", 58, 3073, 3076, c75_first_again_routes)
    c76_merge_routes = (
        *c68_no_routes,
        *(tuple((*route, "c75_first_done") for route in c68_yes_routes)),
        *(
            tuple(
                (*route, "c75_second_done") for route in c75_first_again_routes
            )
        ),
    )

    flow("c82_numeric_weeks", 59, 1121, 1134, c76_merge_routes)
    flow("c82_all_rest", 59, 1148, 1160, c76_merge_routes)
    flow("c82_none_to_c85", 59, 1173, 1196, c76_merge_routes)
    c82_numeric_routes = tuple(
        (*route, "c82_numeric_weeks") for route in c76_merge_routes
    )
    c82_all_rest_routes = tuple(
        (*route, "c82_all_rest") for route in c76_merge_routes
    )
    c82_none_routes = tuple(
        (*route, "c82_none_to_c85") for route in c76_merge_routes
    )
    c82_merge_routes = (
        *c82_numeric_routes,
        *c82_all_rest_routes,
        *c82_none_routes,
    )
    flow("c85_yes", 59, 1869, 1882, c82_merge_routes)
    flow("c85_no_to_c92", 59, 1901, 1938, c82_merge_routes)
    c85_yes_routes = tuple((*route, "c85_yes") for route in c82_merge_routes)
    c85_no_routes = tuple(
        (*route, "c85_no_to_c92") for route in c82_merge_routes
    )
    flow("c91_first_again", 59, 4116, 4125, c85_yes_routes)
    c91_first_again_routes = tuple(
        (*route, "c91_first_again") for route in c85_yes_routes
    )
    flow("c91_first_done", 59, 4134, 4142, c85_yes_routes)
    flow("c91_second_again", 59, 4146, 4155, c91_first_again_routes)
    flow("c91_second_done", 59, 4167, 4175, c91_first_again_routes)
    c92_merge_routes = (
        *c85_no_routes,
        *(tuple((*route, "c91_first_done") for route in c85_yes_routes)),
        *(
            tuple(
                (*route, "c91_second_done") for route in c91_first_again_routes
            )
        ),
    )
    flow("c92_positive_years", 60, 147, 159, c92_merge_routes)
    flow("c92_none_exit", 60, 176, 222, c92_merge_routes)
    c92_positive_routes = tuple(
        (*route, "c92_positive_years") for route in c92_merge_routes
    )
    flow("c93_partial_years", 60, 339, 354, c92_positive_routes)
    flow("c93_all_exit", 60, 367, 402, c92_positive_routes)
    c93_partial_routes = tuple(
        (*route, "c93_partial_years") for route in c92_positive_routes
    )

    # Section-J interview attachment and its K-section split are taken only
    # from the actual questionnaire routing bytes.  The editorial headings on
    # page 135 are repeat/parallel evidence, not branches.
    flow("j1a_checkpoint", 136, 226, 261)
    flow("female_head_exit", 136, 304, 401, (("j1a_checkpoint",),))
    flow("no_wife_exit", 136, 402, 500, (("j1a_checkpoint",),))
    flow("j1c_checkpoint", 136, 586, 618, (("j1a_checkpoint",),))
    flow(
        "wife_unavailable_exit",
        136,
        1019,
        1290,
        (("j1a_checkpoint", "j1c_checkpoint"),),
    )
    flow(
        "wife_interview_entry",
        136,
        1291,
        1380,
        (("j1a_checkpoint", "j1c_checkpoint"),),
    )
    wife_entry_route = (
        "j1a_checkpoint",
        "j1c_checkpoint",
        "wife_interview_entry",
    )
    flow(
        "wife_not_working_section",
        137,
        1470,
        1638,
        (wife_entry_route,),
    )
    wife_not_working_symbol_route = (
        *wife_entry_route,
        "wife_not_working_section",
    )
    flow("k34_yes", 154, 1483, 1486, (wife_not_working_symbol_route,))
    flow(
        "k34_no_to_k48",
        154,
        1499,
        1642,
        (wife_not_working_symbol_route,),
    )
    k34_yes_routes = ((*wife_not_working_symbol_route, "k34_yes"),)
    k34_no_routes = ((*wife_not_working_symbol_route, "k34_no_to_k48"),)
    flow(
        "j34_checkpoint",
        141,
        53,
        86,
        (wife_entry_route,),
    )
    flow(
        "j34_employee_arm",
        141,
        143,
        185,
        ((*wife_entry_route, "j34_checkpoint"),),
    )
    flow(
        "j34_all_others_arm",
        141,
        226,
        266,
        ((*wife_entry_route, "j34_checkpoint"),),
    )
    flow(
        "j46_checkpoint",
        143,
        65,
        97,
        (wife_entry_route,),
    )
    for symbol, start, end in (
        ("j46_same_employer", 166, 187),
        ("j46_self_employed", 213, 233),
        ("j46_different_employer", 266, 291),
    ):
        flow(
            symbol,
            143,
            start,
            end,
            ((*wife_entry_route, "j46_checkpoint"),),
        )
    flow(
        "k37_checkpoint",
        155,
        65,
        96,
        k34_yes_routes,
    )
    for symbol, start, end in (
        ("k37_same_employer", 164, 187),
        ("k37_self_employed", 210, 230),
        ("k37_different_employer", 260, 285),
    ):
        flow(
            symbol,
            155,
            start,
            end,
            (
                (
                    *k34_yes_routes[0],
                    "k37_checkpoint",
                ),
            ),
        )
    k37_same_routes = (
        (*k34_yes_routes[0], "k37_checkpoint", "k37_same_employer"),
    )
    k37_self_routes = (
        (*k34_yes_routes[0], "k37_checkpoint", "k37_self_employed"),
    )
    k37_different_routes = (
        (*k34_yes_routes[0], "k37_checkpoint", "k37_different_employer"),
    )
    k48_merge_routes = (
        *k34_no_routes,
        *k37_same_routes,
        *k37_self_routes,
        *k37_different_routes,
    )

    flow("k66_zero", 158, 2074, 2186, k48_merge_routes)
    flow("k66_worked_weeks", 158, 2223, 2236, k48_merge_routes)
    k66_zero_routes = tuple((*route, "k66_zero") for route in k48_merge_routes)
    k66_worked_routes = tuple(
        (*route, "k66_worked_weeks") for route in k48_merge_routes
    )
    flow("k66_zero_to_k68", 158, 2241, 2254, k66_zero_routes)
    k66_zero_exit_routes = tuple(
        (*route, "k66_zero_to_k68") for route in k66_zero_routes
    )
    k66_merge_routes = (*k66_zero_exit_routes, *k66_worked_routes)
    flow("k68_yes", 159, 302, 312, k66_merge_routes)
    flow("k68_no_to_k76", 159, 332, 360, k66_merge_routes)
    k68_yes_routes = tuple((*route, "k68_yes") for route in k66_merge_routes)
    k68_no_routes = tuple(
        (*route, "k68_no_to_k76") for route in k66_merge_routes
    )
    flow("k75_first_again", 159, 2665, 2674, k68_yes_routes)
    k75_first_again_routes = tuple(
        (*route, "k75_first_again") for route in k68_yes_routes
    )
    flow("k75_first_done", 159, 2687, 2690, k68_yes_routes)
    flow("k75_second_again", 159, 2698, 2707, k75_first_again_routes)
    flow("k75_second_done", 159, 2719, 2722, k75_first_again_routes)
    k76_merge_routes = (
        *k68_no_routes,
        *(tuple((*route, "k75_first_done") for route in k68_yes_routes)),
        *(
            tuple(
                (*route, "k75_second_done") for route in k75_first_again_routes
            )
        ),
    )
    flow("k82_numeric_weeks", 160, 799, 812, k76_merge_routes)
    flow("k82_all_rest", 160, 824, 836, k76_merge_routes)
    flow("k82_none_to_k85", 160, 850, 875, k76_merge_routes)
    k82_numeric_routes = tuple(
        (*route, "k82_numeric_weeks") for route in k76_merge_routes
    )
    k82_all_rest_routes = tuple(
        (*route, "k82_all_rest") for route in k76_merge_routes
    )
    k82_none_routes = tuple(
        (*route, "k82_none_to_k85") for route in k76_merge_routes
    )
    flow("k82_all_rest_to_k84", 160, 939, 948, k82_all_rest_routes)
    k82_all_rest_exit_routes = tuple(
        (*route, "k82_all_rest_to_k84") for route in k82_all_rest_routes
    )
    k82_merge_routes = (
        *k82_numeric_routes,
        *k82_all_rest_exit_routes,
        *k82_none_routes,
    )
    flow("k85_yes", 160, 1522, 1533, k82_merge_routes)
    flow("k85_no_to_k92", 160, 1556, 1574, k82_merge_routes)
    k85_yes_routes = tuple((*route, "k85_yes") for route in k82_merge_routes)
    k85_no_routes = tuple(
        (*route, "k85_no_to_k92") for route in k82_merge_routes
    )
    flow("k91_first_again", 160, 3552, 3561, k85_yes_routes)
    k91_first_again_routes = tuple(
        (*route, "k91_first_again") for route in k85_yes_routes
    )
    flow("k91_first_done", 160, 3575, 3584, k85_yes_routes)
    flow("k91_second_again", 160, 3587, 3596, k91_first_again_routes)
    flow("k91_second_done", 160, 3605, 3614, k91_first_again_routes)
    k92_merge_routes = (
        *k85_no_routes,
        *(tuple((*route, "k91_first_done") for route in k85_yes_routes)),
        *(
            tuple(
                (*route, "k91_second_done") for route in k91_first_again_routes
            )
        ),
    )
    flow("k92_positive_years", 161, 170, 182, k92_merge_routes)
    flow("k92_none_exit", 161, 199, 247, k92_merge_routes)
    k92_positive_routes = tuple(
        (*route, "k92_positive_years") for route in k92_merge_routes
    )
    flow("k93_partial_years", 161, 377, 382, k92_positive_routes)
    flow("k93_all_exit", 161, 397, 498, k92_positive_routes)
    k93_partial_routes = tuple(
        (*route, "k93_partial_years") for route in k92_positive_routes
    )

    flow("j110_positive_years", 149, 1616, 1621, (wife_entry_route,))
    flow("j110_none_exit", 149, 1640, 1686, (wife_entry_route,))
    j110_positive_routes = ((*wife_entry_route, "j110_positive_years"),)
    flow("j111_partial_years", 149, 1821, 1826, j110_positive_routes)
    flow("j111_all_exit", 149, 1841, 1882, j110_positive_routes)
    j111_partial_routes = ((*j110_positive_routes[0], "j111_partial_years"),)

    # New-Head background routing.  The same NEVER-WORKED label is printed
    # under both qualifying G1 arms, so it lawfully has two parent paths.
    flow("new_head_reinterview", 116, 179, 253)
    flow("new_head_splitoff", 116, 276, 308)
    flow("new_head_all_others", 116, 342, 355)
    flow(
        "new_head_never_worked",
        116,
        2005,
        2294,
        (("new_head_reinterview",), ("new_head_splitoff",)),
    )

    # Income-section checkpoints and their printed alternatives.  Later
    # screens carry every path that reaches the merge, rather than selecting
    # one candidate-generated alternative.
    flow("f2_checkpoint", 83, 346, 381)
    flow("f2_farmer_arm", 83, 437, 492, (("f2_checkpoint",),))
    flow("f2_all_others_arm", 83, 622, 681, (("f2_checkpoint",),))
    flow("f22_checkpoint", 90, 59, 88)
    flow("f22_extra_job_arm", 90, 167, 193, (("f22_checkpoint",),))
    flow("f22_all_others_arm", 90, 204, 233, (("f22_checkpoint",),))
    flow("f22_repeat_checkpoint", 92, 58, 88)
    flow(
        "f22_repeat_extra_job_arm",
        92,
        153,
        192,
        (("f22_repeat_checkpoint",),),
    )
    flow(
        "f22_repeat_all_others_arm",
        92,
        192,
        279,
        (("f22_repeat_checkpoint",),),
    )
    flow("f49_checkpoint", 98, 298, 330)
    flow("f49_wife_listed_arm", 98, 482, 530, (("f49_checkpoint",),))
    flow("f49_all_others_arm", 98, 532, 591, (("f49_checkpoint",),))

    flow("n1_checkpoint", 188, 153, 186)
    flow("wife_background_present", 188, 235, 277, (("n1_checkpoint",),))
    flow("female_head_background_exit", 188, 279, 340, (("n1_checkpoint",),))

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
            "flow_branch_label",
        )
        row["review_id"] = review_occurrence_id
        resolved: list[list[str]] = []
        for symbolic_route in row["routes"]:
            prefix: list[str] = []
            for symbol in symbolic_route:
                parent = flow_by_symbol[symbol]
                parent_paths = resolved_flow_paths[symbol]
                matches = [path for path in parent_paths if path == prefix]
                if len(matches) != 1:
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
                matches = [path for path in parent_paths if path == prefix]
                if len(matches) != 1:
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
            "flow_branch_label",
            row["routes"],
            row["note"],
            replace_overlap=True,
        )

    head_working_routes = (
        ("head_working_now",),
        ("head_temporarily_laid_off",),
        ("head_other_paid_work_now",),
    )
    wife_not_working_route = (*wife_entry_route, "wife_not_working_section")
    wife_background_route = ("n1_checkpoint", "wife_background_present")

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if page == 16:
            if 664 <= start < 1025:
                return (("head_working_now",),)
            if 1026 <= start < 1514:
                return (("head_temporarily_laid_off",),)
            if 1515 <= start < 2028:
                return (("head_other_paid_work_now",),)
            if 2029 <= start:
                return (("head_not_working_condition",),)
        if page == 17:
            if start < 146:
                return (("head_not_working_condition",),)
            return head_working_routes
        if page == 28:
            if 281 <= start < 672:
                return b34_employee_routes
            if start >= 672:
                return b34_merge_routes
            return head_working_routes
        if page in {29, 30}:
            return b34_merge_routes
        if page == 31:
            if 336 <= start < 907:
                return b46_different_routes
            if start >= 907:
                return b46_merge_routes
            return b34_merge_routes
        if page == 32:
            return b46_merge_routes
        if page in {33, 34}:
            # The shared work-history supplement is entered from multiple
            # sections whose selector text is printed only after its fields.
            return ((),)
        if page == 35:
            if start >= 262:
                return s6_merge_routes
            return ((),)
        if page in {37, 38, 39}:
            return b34_merge_routes
        if page == 40:
            if start >= 2340:
                return b75_worked_routes
            if 2112 <= start < 2130:
                return b75_zero_routes
            return b34_merge_routes
        if page == 41:
            return b75_worked_routes
        if page == 42:
            if 416 <= start < 2874:
                return (*b79_yes_routes, *b86_first_again_routes)
            if start >= 2875:
                return b87_merge_routes
            return b75_worked_routes
        if page == 43:
            return b87_merge_routes
        if page == 44:
            if 1338 <= start < 1758:
                return b93_some_routes
            if 1758 <= start < 2284:
                return b93_merge_routes
            if 2284 <= start < 4358:
                return (*b96_yes_routes, *b102_first_again_routes)
            return b87_merge_routes
        if page == 45:
            return b103_merge_routes
        if page == 46:
            return b103_merge_routes
        if 18 <= page <= 27:
            return head_working_routes
        if page == 47:
            return (head_not_working_route,)
        if page == 48:
            if 313 <= start < 890:
                return ((*head_not_working_route, "c1_no_route"),)
            if 892 <= start:
                return ((*head_not_working_route, "c1_yes_route"),)
            return (head_not_working_route,)
        if 49 <= page <= 53:
            return (
                (*head_not_working_route, "c1_yes_route"),
                (*head_not_working_route, "c1_no_route"),
            )
        if page == 54:
            if 389 <= start < 927:
                return c37_different_routes
            if start >= 927:
                return c37_merge_routes
            return c1_symbol_routes
        if page in {55, 56}:
            return c37_merge_routes
        if page == 57:
            if start >= 2482:
                return (*c66_worked_routes, *c66_all_rest_routes)
            return c1_symbol_routes
        if page == 58:
            if 608 <= start < 3078:
                return (*c68_yes_routes, *c75_first_again_routes)
            if start >= 3079:
                return c76_merge_routes
            return c66_merge_routes
        if page == 59:
            if 1275 <= start < 1446:
                return c82_numeric_routes
            if 1446 <= start < 1613:
                return (*c82_numeric_routes, *c82_all_rest_routes)
            if 1613 <= start < 1939:
                return c82_merge_routes
            if 1939 <= start < 4176:
                return (*c85_yes_routes, *c91_first_again_routes)
            if start >= 4176:
                return c92_merge_routes
            return c76_merge_routes
        if page == 60:
            if 225 <= start < 339:
                return c92_positive_routes
            if 339 <= start < 522:
                return c92_positive_routes
            if start >= 522:
                return c93_partial_routes
            return c92_merge_routes
        if page == 83:
            if 437 <= start < 681:
                return (("f2_checkpoint",),)
            if 681 <= start < 1360:
                return (("f2_checkpoint", "f2_farmer_arm"),)
            if 1360 <= start:
                return (
                    ("f2_checkpoint", "f2_farmer_arm"),
                    ("f2_checkpoint", "f2_all_others_arm"),
                )
        if page == 90:
            if 167 <= start < 233:
                return (("f22_checkpoint",),)
            if 234 <= start < 608:
                return (("f22_checkpoint", "f22_extra_job_arm"),)
            if 608 <= start:
                return (
                    ("f22_checkpoint", "f22_extra_job_arm"),
                    ("f22_checkpoint", "f22_all_others_arm"),
                )
        if page == 92:
            if 153 <= start < 279:
                return (("f22_repeat_checkpoint",),)
            if 279 <= start < 654:
                return (("f22_repeat_checkpoint", "f22_repeat_extra_job_arm"),)
            if 654 <= start:
                return (
                    ("f22_repeat_checkpoint", "f22_repeat_extra_job_arm"),
                    ("f22_repeat_checkpoint", "f22_repeat_all_others_arm"),
                )
        if page == 98:
            if 482 <= start < 591:
                return (("f49_checkpoint",),)
            if 594 <= start:
                return (("f49_checkpoint", "f49_wife_listed_arm"),)
        if page == 136:
            if 352 <= start < 500:
                return (("j1a_checkpoint",),)
            if 586 <= start < 619:
                return (("j1a_checkpoint",),)
            if 619 <= start < 1302:
                return (("j1a_checkpoint", "j1c_checkpoint"),)
            if 1302 <= start:
                return (("j1a_checkpoint", "j1c_checkpoint"),)
        if page == 141 and 143 <= start < 186:
            return ((*wife_entry_route, "j34_checkpoint"),)
        if page == 141 and 226 <= start < 271:
            return ((*wife_entry_route, "j34_checkpoint"),)
        if page == 141 and 271 <= start < 651:
            return ((*wife_entry_route, "j34_checkpoint", "j34_employee_arm"),)
        if page == 141 and 651 <= start:
            return (
                (*wife_entry_route, "j34_checkpoint", "j34_employee_arm"),
                (*wife_entry_route, "j34_checkpoint", "j34_all_others_arm"),
            )
        if page == 143 and 166 <= start < 292:
            return ((*wife_entry_route, "j46_checkpoint"),)
        if page == 143 and 296 <= start < 1255:
            return (
                (
                    *wife_entry_route,
                    "j46_checkpoint",
                    "j46_different_employer",
                ),
            )
        if page == 143 and 1255 <= start:
            return tuple(
                (*wife_entry_route, "j46_checkpoint", arm)
                for arm in (
                    "j46_same_employer",
                    "j46_self_employed",
                    "j46_different_employer",
                )
            )
        if page == 149:
            if 1689 <= start < 1821:
                return j110_positive_routes
            if start >= 1883:
                return j111_partial_routes
            return (wife_entry_route,)
        if 137 <= page <= 149:
            return (wife_entry_route,)
        if page == 154:
            if start >= 1644:
                return k34_yes_routes
            return (wife_not_working_route,)
        if page == 155 and 164 <= start < 286:
            return ((*k34_yes_routes[0], "k37_checkpoint"),)
        if page == 155 and 290 <= start < 919:
            return k37_different_routes
        if page == 155 and 919 <= start:
            return (
                *k37_same_routes,
                *k37_self_routes,
                *k37_different_routes,
            )
        if page == 156:
            return (*k37_same_routes, *k37_self_routes, *k37_different_routes)
        if page == 157:
            return k48_merge_routes
        if page == 158:
            if start >= 2256:
                return k66_worked_routes
            return k48_merge_routes
        if page == 159:
            if 361 <= start < 2723:
                return (*k68_yes_routes, *k75_first_again_routes)
            if start >= 2723:
                return k76_merge_routes
            return k66_merge_routes
        if page == 160:
            if 876 <= start < 939:
                return k82_numeric_routes
            if 949 <= start < 1271:
                return (*k82_numeric_routes, *k82_all_rest_exit_routes)
            if 1271 <= start < 1522:
                return k82_merge_routes
            if 1575 <= start < 3615:
                return (*k85_yes_routes, *k91_first_again_routes)
            if start >= 3615:
                return k92_merge_routes
            return k76_merge_routes
        if page == 161:
            if 250 <= start < 377:
                return k92_positive_routes
            if start >= 499:
                return k93_partial_routes
            return k92_merge_routes
        if 150 <= page <= 153:
            return (wife_not_working_route,)
        if page == 116 and 1529 <= start:
            return (("new_head_reinterview",), ("new_head_splitoff",))
        if page == 188 and 250 <= start < 340:
            return (("n1_checkpoint",),)
        if page == 188 and 366 <= start:
            return (wife_background_route,)
        if page in {189, 191, 192}:
            return (wife_background_route,)
        return ((),)

    def in_relevant_window(
        page: int, start: int, end: int, kind: str, text: str
    ) -> bool:
        if page not in SEMANTIC_PAGES:
            return False
        if not inside_reviewed_window(page, start, end):
            return False
        allowed_kinds = PAGE_KIND_ALLOWLIST.get(page)
        if allowed_kinds is not None and kind not in allowed_kinds:
            return False
        folded = " ".join(text.upper().split())
        if kind == "role_anchor" and (page, start, end) in ROLE_EXCLUDED_SPANS:
            return False
        if kind in {
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
            "role_total_anchor",
        }:
            if page not in HEAD_INCOME_PAGES:
                return False
            if kind == "farm_aggregate_anchor":
                return any(
                    marker in folded
                    for marker in (
                        "FARM",
                        "FARM INCOME",
                        "FARMER",
                        "FARMING",
                        "RANCHER",
                    )
                )
            if kind == "business_aggregate_anchor":
                return any(
                    marker in folded
                    for marker in (
                        "BUSINESS",
                        "SELF-EMPLOY",
                        "PROFESSIONAL PRACTICE",
                        "UNINCORPORATED",
                    )
                )
            return any(
                marker in folded
                for marker in ("TOTAL", "ALTOGETHER", "ALL JOB", "COMBINED")
            )
        if kind == "flow_branch_label":
            if (page, start, end) in FLOW_EXCLUDED_SPANS:
                return False
            if any(marker in folded for marker in FLOW_EXCLUSION_MARKERS):
                return False
            has_if = folded.startswith("IF ") or " IF " in f" {folded} "
            return any(marker in folded for marker in FLOW_ACTION_MARKERS) or (
                has_if
                and any(
                    marker in folded
                    for marker in (
                        "ASK",
                        "CHECK",
                        "MARK",
                        "RECORD",
                        "PROBE",
                        "PROCEED",
                    )
                )
            )
        if kind == "repeat_or_alias_instruction":
            if (
                page in MANUAL_REPEAT_ONLY_PAGES
                or (
                    page,
                    start,
                    end,
                )
                in REPEAT_EXCLUDED_SPANS
            ):
                return False
            return any(
                marker in folded
                for marker in (
                    "REPEAT",
                    "AGAIN",
                    "SAME EMPLOYER",
                    "SAME JOB",
                    "ANOTHER JOB",
                    "OTHER JOB",
                    "PREVIOUSLY",
                    "ALREADY TOLD",
                    "SEE B",
                    "SEE C",
                    "SEE J",
                    "SEE K",
                    "WORK HISTORY SUPPLEMENT",
                )
            )
        if (
            kind == "remuneration_component_anchor"
            and (
                page,
                start,
                end,
            )
            in REMUNERATION_EXCLUDED_SPANS
        ):
            return False
        if kind == "job_anchor":
            if (page, start, end) in JOB_EXCLUDED_SPANS:
                return False
            if page == 116:
                return 1780 <= start < end <= 1808
            if page == 188:
                return 1513 <= start < end <= 1540
            if page in {26, 140} and "NEW JOB" in folded:
                return False
        if kind == "context_anchor" and (page, start, end) in {
            (31, 256, 276),
            (35, 198, 214),
            (138, 770, 791),
            (143, 213, 233),
            (145, 246, 273),
            (155, 210, 230),
            (157, 219, 246),
        }:
            return False
        if kind == "field_purpose_prompt":
            if (
                page in HEAD_EMPLOYMENT_PAGES
                and page not in HEAD_PURPOSE_PAGES
            ):
                return False
            allowed_windows = PURPOSE_ALLOWED_BYTE_WINDOWS.get(page)
            if allowed_windows is not None and not any(
                window_start <= start < end <= window_end
                for window_start, window_end in allowed_windows
            ):
                return False
            if any(
                window_start <= start < end <= window_end
                for window_start, window_end in PURPOSE_EXCLUDED_BYTE_WINDOWS.get(
                    page, ()
                )
            ):
                return False
            return not any(
                marker in folded
                for marker in (
                    "THIS IS A BLANK PAGE",
                    "CONVERSION TABLE",
                    "FOR OFFICE USE ONLY",
                    "EXACT TIME NOW",
                )
            )
        return True

    # Composite spouse labels are single printed role atoms.  Enumerate them
    # from the authenticated page strings before the lexical pass, then reject
    # narrower detector hits that would split one composite into two roles.
    composite_role_ranges: dict[int, list[tuple[int, int]]] = {}
    for page_number in sorted(SEMANTIC_PAGES):
        page_text = page_texts[page_number - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        for match in COMPOSITE_WIFE_RE.finditer(page_text):
            start = offsets[match.start()]
            end = offsets[match.end()]
            if not in_relevant_window(
                page_number, start, end, R, match.group()
            ):
                continue
            composite_role_ranges.setdefault(page_number, []).append(
                (start, end)
            )
            add(
                page_number,
                start,
                end,
                R,
                source_routes(page_number, start, end, R),
                "Composite spouse-role label independently re-sliced as one exact source atom.",
            )

    # Re-run lexical enumeration directly over authenticated page bytes.  The
    # source-window and kind-specific decisions above, not the committed
    # candidate rows, select the retained atoms.
    for page_number, page_text in enumerate(page_texts, start=1):
        detected, _line_count = (
            annotation.stage1_candidates.detect_page_candidates(
                page_text,
                source_document_id=source_document_id,
                interview_wave=interview_wave,
                page_number=page_number,
            )
        )
        for row in detected:
            kind = row["occurrence_kind_candidate"]
            text = row["matched_text"]
            if kind == R and any(
                composite_start < row["utf8_byte_end"]
                and row["utf8_byte_start"] < composite_end
                for composite_start, composite_end in composite_role_ranges.get(
                    page_number, ()
                )
            ):
                continue
            if not in_relevant_window(
                page_number,
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                kind,
                text,
            ):
                continue
            if kind == F and any(
                existing_page == page_number
                and existing_kind == F
                and existing_start < row["utf8_byte_end"]
                and row["utf8_byte_start"] < existing_end
                for (
                    existing_page,
                    existing_start,
                    existing_end,
                    existing_kind,
                ) in specs
            ):
                # Explicit reviewer flow definitions already carry their
                # complete symbolic ancestry.  A detector rediscovery must
                # not merge a root/default route into the same source label.
                continue
            routes = source_routes(
                page_number,
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                kind,
            )
            add(
                page_number,
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                kind,
                routes,
                "Reviewer-approved source atom independently re-derived from exact page bytes.",
            )

    # Reviewer-authored corrections and detector misses.  These are exact
    # source spans, not candidate coordinates: complete parallel/cross-reference
    # blocks, OCR-split job labels, and remuneration questions whose damaged
    # wording falls outside the stage-1 grammar.
    manual_specs: tuple[tuple[int, int, int, str, str], ...] = (
        (16, 372, 511, A, "Complete B/C-to-J/K repeated-instruction block."),
        (18, 1445, 1568, F, "Complete B3 route to Section C."),
        (18, 2251, 2271, F, "Atomic B5 unincorporated branch label."),
        (18, 2305, 2330, F, "Atomic B8 NO skip branch label."),
        (18, 2647, 2687, F, "Complete route to B15."),
        (20, 1223, 1248, A, "Atomic B16 repeat instruction."),
        (24, 1072, 1113, F, "Complete route to B26."),
        (26, 543, 569, F, "Atomic B28 NONE route to B29."),
        (27, 446, 575, F, "Complete B36 work-history routing condition."),
        (29, 1170, 1295, F, "Complete B45 pre-1984 routing condition."),
        (29, 1105, 1169, A, "Complete B41 repeat directive."),
        (30, 1337, 1471, F, "Complete B42 NO skip branch."),
        (33, 420, 545, F, "Complete S16 supplement-exit rule."),
        (34, 3560, 3576, F, "Atomic B57 return target."),
        (34, 3583, 3599, F, "Atomic C48 return target."),
        (34, 3612, 3628, F, "Atomic J57 return target."),
        (34, 3639, 3655, F, "Atomic K48 return target."),
        (35, 3290, 3304, F, "Atomic OCR-surviving C48 return target."),
        (35, 3316, 3332, F, "Atomic J57 return target."),
        (35, 3337, 3348, F, "Atomic OCR-surviving K48 return target."),
        (38, 1798, 1826, F, "Atomic B60 NO route to B63."),
        (40, 2112, 2130, F, "Complete route to B87."),
        (42, 2804, 2813, A, "First atomic B86 repeat-loop instruction."),
        (42, 2850, 2859, A, "Second atomic B86 repeat-loop instruction."),
        (44, 4292, 4302, A, "First atomic B102 repeat-loop instruction."),
        (44, 4324, 4334, A, "Second atomic B102 repeat-loop instruction."),
        (51, 2648, 2666, F, "First C48 return target."),
        (51, 2680, 2698, F, "Second C48 return target."),
        (53, 1433, 1546, F, "Complete C34 NO skip branch."),
        (53, 3125, 3143, F, "First C48 return target."),
        (53, 3166, 3184, F, "Second C48 return target."),
        (55, 916, 934, F, "First C48 return target."),
        (55, 947, 966, F, "Second C48 return target."),
        (58, 3015, 3024, A, "First atomic C75 repeat-loop instruction."),
        (58, 3050, 3059, A, "Second atomic C75 repeat-loop instruction."),
        (59, 4116, 4125, A, "First atomic C91 repeat-loop instruction."),
        (59, 4146, 4155, A, "Second atomic C91 repeat-loop instruction."),
        (85, 2416, 2665, A, "Complete F3-F5 not-repeated-here condition."),
        (85, 943, 1053, T, "Head total 1984 wages across all jobs."),
        (86, 529, 551, T, "Head all-job wage-total anchor, left column only."),
        (
            86,
            3830,
            3840,
            BA,
            "Roomer/boarder aggregate, first clean source cell.",
        ),
        (
            86,
            4230,
            4239,
            BA,
            "Roomer/boarder aggregate, second clean source cell.",
        ),
        (87, 50, 69, BA, "Roomer/boarder income-source aggregate anchor."),
        (88, 443, 465, T, "Head all-job wage-total anchor, left column only."),
        (
            88,
            3959,
            3969,
            BA,
            "Roomer/boarder aggregate, first clean source cell.",
        ),
        (
            88,
            4296,
            4305,
            BA,
            "Roomer/boarder aggregate, second clean source cell.",
        ),
        (
            97,
            655,
            881,
            A,
            "Complete conditional F11 business-income cross-reference.",
        ),
        (97, 471, 645, T, "Wife total income from all work sources."),
        (98, 948, 1091, T, "Complete Wife work-income-total anchor."),
        (116, 1780, 1808, J, "OCR-exact first full-time regular job anchor."),
        (117, 490, 998, C, "G11-G12 no-job mobility context."),
        (118, 1198, 1333, C, "G11 no-job mobility context."),
        (118, 1466, 1564, C, "G12 no-job mobility context."),
        (127, 122, 436, C, "Roomer/boarder income-producing-work context."),
        (135, 1263, 1339, A, "Glossary role-definition cross-reference."),
        (135, 1295, 1299, R, "Head role in glossary-definition reminder."),
        (135, 1301, 1305, R, "Wife role in glossary-definition reminder."),
        (
            135,
            1311,
            1317,
            R,
            "Quoted Wife role in glossary-definition reminder.",
        ),
        (135, 1569, 1816, A, "J/K and B/C parallel-section instruction."),
        (135, 1604, 1620, R, 'OCR-exact Wife/"Wife" composite role label.'),
        (136, 953, 966, R, "Composite spouse/friend role label."),
        (138, 605, 634, F, "Atomic J13 NO route to J15."),
        (140, 288, 316, F, "Complete J29 NONE skip branch."),
        (141, 99, 125, A, "J34 employment-type cross-reference."),
        (141, 2627, 2641, R, "Complete spaced-close composite spouse role."),
        (142, 1870, 1994, F, "Complete J42 NO skip branch."),
        (143, 107, 149, A, "J46 previous-position cross-reference."),
        (143, 2076, 2095, R, "Complete possessive composite spouse role."),
        (144, 1212, 1226, R, "Complete spaced-close composite spouse role."),
        (145, 1096, 1110, R, "Complete spaced-close composite spouse role."),
        (
            147,
            691,
            832,
            M,
            "J82 extra-job amount and reporting-unit component.",
        ),
        (147, 2185, 2194, A, "First atomic J86 repeat-loop instruction."),
        (147, 2218, 2227, A, "Second atomic J86 repeat-loop instruction."),
        (148, 2723, 2733, A, "Atomic J102 repeat-loop instruction."),
        (149, 1488, 1504, R, "OCR-spaced composite spouse role label."),
        (152, 1301, 1411, F, "Complete K22 NONE skip branch."),
        (155, 105, 149, A, "K37 previous-position cross-reference."),
        (155, 1563, 1687, M, "OCR-damaged K42 final wage/salary component."),
        (153, 78, 97, R, "Complete possessive composite spouse role."),
        (153, 468, 483, R, "Complete spaced-close composite spouse role."),
        (153, 1559, 1574, R, "Complete spaced-close composite spouse role."),
        (154, 215, 230, R, "OCR-spaced composite spouse role label."),
        (154, 1076, 1086, F, "Atomic OCR-surviving K48 skip target."),
        (155, 330, 344, R, "Complete spaced-close composite spouse role."),
        (155, 1233, 1252, R, "Complete possessive composite spouse role."),
        (155, 1585, 1607, R, "OCR-damaged possessive composite spouse role."),
        (
            159,
            803,
            998,
            M,
            "K71 extra-job amount and reporting-unit component.",
        ),
        (159, 154, 169, R, "Complete spaced-close composite spouse role."),
        (159, 2665, 2674, A, "First atomic K75 repeat-loop instruction."),
        (159, 2698, 2707, A, "Second atomic K75 repeat-loop instruction."),
        (159, 2762, 2776, R, "Complete spaced-close composite spouse role."),
        (160, 710, 724, R, "Complete spaced-close composite spouse role."),
        (160, 3552, 3561, A, "First atomic K91 repeat-loop instruction."),
        (160, 3587, 3596, A, "Second atomic K91 repeat-loop instruction."),
        (161, 99, 114, R, "Complete spaced-close composite spouse role."),
        (187, 171, 486, A, "N/G parallel-section instruction."),
        (187, 312, 326, R, 'Plural Wife/"Wife" composite role label.'),
        (188, 1513, 1540, J, "Exact first full-time regular job anchor."),
        (189, 1206, 1331, C, "N11 no-job mobility context."),
        (189, 1470, 1578, C, "N12 no-job mobility context."),
    )
    for page, start, end, kind, note in manual_specs:
        if (
            page not in SEMANTIC_PAGES
            or not inside_reviewed_window(page, start, end)
            or kind
            not in PAGE_KIND_ALLOWLIST.get(
                page, frozenset(annotation.OCCURRENCE_KINDS)
            )
        ):
            raise ValueError(
                f"manual reviewed atom escaped page policy: {page}:{start}:{end}"
            )
        add(
            page,
            start,
            end,
            kind,
            source_routes(page, start, end, kind),
            note,
            replace_overlap=True,
        )

    manual_context_and_purpose: tuple[tuple[int, int, int], ...] = (
        (116, 1742, 1827),
        (116, 2393, 2536),
        (122, 1190, 1265),
        (122, 1354, 1450),
        (122, 1451, 1529),
        (123, 1417, 1455),
        (123, 1457, 1537),
        (188, 2090, 2233),
        (191, 1171, 1226),
        (191, 1290, 1354),
        (192, 1707, 1744),
        (192, 1817, 1877),
    )
    for page, start, end in manual_context_and_purpose:
        for kind in (C, P):
            add(
                page,
                start,
                end,
                kind,
                source_routes(page, start, end, kind),
                "Complete no-job context/purpose prompt manually sliced from exact source bytes.",
                replace_overlap=True,
            )

    manual_context_specs: tuple[tuple[int, int, int, str], ...] = (
        (137, 241, 404, "Complete J1f current-activity context."),
        (137, 444, 455, "Atomic LOOKING FOR response context."),
        (137, 484, 491, "Atomic RETIRED response context."),
        (137, 507, 527, "Atomic PERMANENTLY DISABLED response context."),
        (137, 925, 935, "Atomic SICK LEAVE response context."),
        (137, 1010, 1017, "Atomic STUDENT response context."),
        (137, 1961, 1974, "Atomic SELF-EMPLOYED response context."),
        (137, 1985, 2011, "Atomic mixed-employment response context."),
        (137, 1701, 1865, "Complete J4 employment-type context."),
        (138, 157, 276, "Complete J12 employer-type context."),
        (139, 441, 451, "Atomic work-time context cell."),
        (139, 853, 868, "Atomic more-hours context cell."),
        (140, 57, 207, "Complete J26 commute context."),
        (141, 271, 371, "Complete J35 employer-exposure context."),
        (141, 651, 829, "Complete J36 position-start context."),
        (141, 1981, 2036, "J37 reordered context fragment."),
        (141, 2090, 2173, "J37 temporary/permanent context fragment."),
        (141, 2514, 2565, "Complete J39 weekly-hours context."),
        (141, 2599, 2785, "Complete J40 job-opportunity context."),
        (142, 63, 142, "J41 previous-situation context, first fragment."),
        (142, 254, 492, "J41 previous-situation context, second fragment."),
        (142, 3021, 3171, "Complete J45 position-end context."),
        (143, 1270, 1329, "Complete J48 industry context."),
        (143, 1502, 1614, "Complete J49 occupation context."),
        (143, 2516, 2566, "Complete J52 weekly-hours context."),
        (144, 57, 267, "Complete J53 position-start context."),
        (144, 1153, 1337, "Complete J54 temporary/permanent context."),
        (144, 1683, 1739, "Complete J56 weekly-hours context."),
        (146, 551, 671, "Complete J69 unemployment context."),
        (146, 1142, 1244, "Complete J72 no-job context."),
        (146, 1535, 1620, "Complete J75 weeks-worked context."),
        (146, 2040, 2129, "Complete J76 weekly-hours context."),
        (147, 2244, 2488, "Complete J87 unemployment context."),
        (148, 52, 144, "J90 no-job context, first fragment."),
        (148, 265, 273, "J90 no-job context, second fragment."),
        (148, 754, 858, "Complete J95 weekly-hours context."),
        (149, 63, 243, "Complete J103 more-work context."),
        (149, 1440, 1551, "Complete J110 lifetime-work context."),
        (149, 1699, 1781, "Complete J111 full-time-work context."),
        (149, 1925, 2098, "Complete J112 fractional-work context."),
        (152, 1119, 1221, "Complete K22 commute context."),
        (152, 1983, 2135, "Complete K26 position-end context."),
        (153, 430, 625, "Complete K29 position-start context."),
        (153, 1542, 1677, "Complete K30 temporary/permanent context."),
        (153, 2029, 2076, "Complete K32 weekly-hours context."),
        (154, 190, 499, "Complete K33 previous-situation context."),
        (154, 572, 582, "Atomic UNEMPLOYED response context."),
        (154, 598, 609, "Atomic TEMPORARILY response context."),
        (154, 2279, 2492, "Complete K36 position-end context."),
        (155, 932, 991, "Complete K39 industry context."),
        (156, 162, 361, "Complete K44 position-start context."),
        (156, 1124, 1259, "Complete K45 temporary/permanent context."),
        (156, 1638, 1688, "Complete K47 weekly-hours context."),
        (158, 750, 863, "Complete K60 unemployment context."),
        (158, 1368, 1471, "Complete K63 no-job context."),
        (159, 57, 260, "Complete K68 extra-job context."),
        (159, 2724, 2971, "Complete K76 unemployment context."),
        (160, 176, 282, "Complete K79 no-job context."),
        (160, 1097, 1205, "Complete K84 weekly-hours context."),
        (160, 1271, 1475, "Complete K85 extra-job context."),
        (161, 53, 159, "Complete K92 lifetime-work context."),
        (161, 510, 624, "Complete K94 fractional-work context."),
    )
    for page, start, end, note in manual_context_specs:
        add(
            page,
            start,
            end,
            C,
            source_routes(page, start, end, C),
            note,
            replace_overlap=True,
        )

    manual_purpose_specs: tuple[tuple[int, int, int, str], ...] = (
        (18, 138, 288, "Complete B1 work-status prompt."),
        (18, 1280, 1382, "Complete B3 current-paid-work prompt."),
        (18, 1631, 1789, "Complete B4 employment-type prompt."),
        (19, 55, 179, "Complete B12 employer-type prompt."),
        (28, 672, 851, "Complete B36 position-start prompt."),
        (28, 1845, 1975, "Complete B37 temporary/permanent prompt."),
        (30, 53, 396, "Complete B41 previous-work-situation prompt."),
        (30, 2048, 2198, "Complete B45 position-end prompt."),
        (32, 56, 345, "Complete B53 position-start prompt."),
        (32, 993, 1113, "Complete B55 temporary/permanent prompt."),
        (34, 826, 1121, "Complete S1 previous-work-situation prompt."),
        (34, 1956, 2184, "Complete S3 employer-continuity prompt."),
        (34, 2404, 2553, "Complete S4 position-end prompt."),
        (35, 277, 396, "Complete S7 employer-type prompt."),
        (35, 451, 557, "Complete S8 occupation prompt."),
        (35, 602, 716, "Complete S9 industry prompt."),
        (35, 1624, 1678, "Complete S12 duties prompt."),
        (35, 2047, 2220, "Complete S15 position-start prompt."),
        (38, 969, 1422, "Complete B57 annual-work-history prompt."),
        (40, 574, 696, "Complete B69 unemployment-absence prompt."),
        (40, 1287, 1391, "Complete B72 no-job prompt."),
        (40, 1796, 1884, "Complete B75 weeks-worked prompt."),
        (42, 60, 176, "Complete B79 extra-job prompt."),
        (42, 426, 605, "Complete B80 occupation prompt."),
        (42, 617, 748, "Complete B81 duties prompt."),
        (42, 784, 850, "Complete B82 extra-job-amount prompt."),
        (42, 1307, 1413, "Complete B83 weeks-worked prompt."),
        (42, 1613, 1682, "Complete B84 timing prompt."),
        (42, 1827, 1971, "Complete B85 weekly-hours prompt."),
        (42, 2130, 2202, "Complete B86 repeat-job prompt."),
        (42, 2877, 3130, "Complete B87 unemployment-absence prompt."),
        (44, 64, 211, "Complete B90 no-job prompt."),
        (44, 1507, 1612, "Complete B95 weekly-hours prompt."),
        (44, 1758, 1874, "Complete B96 extra-job prompt."),
        (44, 2415, 2591, "Complete B97 occupation prompt."),
        (44, 2603, 2703, "Complete B98 duties prompt."),
        (44, 2713, 2822, "Complete B99 weeks-worked prompt."),
        (44, 2943, 3005, "Complete B100 timing prompt."),
        (44, 3242, 3349, "Complete B101 weekly-hours prompt."),
        (44, 3472, 3536, "Complete B102 repeat-job prompt."),
        (46, 60, 238, "Complete B103 more-work-available prompt."),
        (46, 2123, 2234, "Complete B112 fractional-work prompt."),
        (48, 704, 802, "Complete C8 timing prompt."),
        (49, 165, 320, "Complete C10 last-worked prompt."),
        (51, 233, 382, "Complete C21 employer-type prompt."),
        (51, 1830, 1942, "Complete C25 job-ending-reason prompt."),
        (51, 1947, 2101, "Complete C26 position-end prompt."),
        (52, 59, 166, "Complete C27 final-pay prompt."),
        (52, 615, 806, "Complete C29 position-start prompt."),
        (52, 1544, 1673, "Complete C30 temporary/permanent prompt."),
        (53, 170, 477, "Complete C33 previous-work-situation prompt."),
        (53, 1594, 1823, "Complete C35 employer-continuity prompt."),
        (54, 410, 553, "Complete C38 employer-type prompt."),
        (54, 1416, 1528, "Complete C42 position-start prompt."),
        (55, 155, 347, "Complete C44 temporary/permanent prompt."),
        (55, 1001, 1128, "Complete C45 starting-pay prompt."),
        (56, 1296, 1764, "Complete C48 annual-work-history prompt."),
        (56, 2104, 2194, "Complete C51 vacation prompt."),
        (57, 774, 884, "Complete C60 sickness-absence prompt."),
        (57, 1245, 1347, "Complete C63 unemployment-absence prompt."),
        (57, 1742, 1826, "Complete C66 no-job prompt."),
        (58, 57, 256, "Complete C68 weeks-worked prompt."),
        (58, 618, 791, "Complete C69 occupation prompt."),
        (58, 801, 903, "Complete C70 duties prompt."),
        (58, 913, 978, "Complete C71 extra-job-amount prompt."),
        (58, 1286, 1390, "Complete C72 weeks-worked prompt."),
        (58, 1508, 1626, "Complete C73 timing prompt."),
        (58, 1971, 2085, "Complete C74 weekly-hours prompt."),
        (58, 2208, 2281, "Complete C75 repeat-job prompt."),
        (58, 3079, 3321, "Complete C76 unemployment-absence prompt."),
        (59, 184, 287, "Complete C79 no-job prompt."),
        (59, 1446, 1551, "Complete C84 weeks-worked prompt."),
        (59, 1613, 1819, "Complete C85 weekly-hours prompt."),
        (59, 2187, 2245, "Complete C86 occupation prompt."),
        (59, 2257, 2354, "Complete C87 duties prompt."),
        (59, 2365, 2470, "Complete C88 weeks-worked prompt."),
        (59, 2595, 2618, "Complete C89 timing prompt."),
        (59, 3270, 3341, "Complete C91 weekly-hours prompt."),
        (60, 532, 646, "Complete C94 fractional-work prompt."),
        (82, 601, 696, "Complete F2 occupation-assignment block."),
        (82, 891, 1353, "Complete F3 included-receipts assignment block."),
        (82, 1365, 1530, "Complete F3 excluded-receipts assignment block."),
        (82, 1531, 2145, "Complete F4 operating-expense assignment block."),
        (83, 817, 960, "Complete F3 farm-receipts prompt."),
        (83, 1028, 1130, "Complete F4 operating-expenses prompt."),
        (83, 1238, 1291, "Complete F5 net-farm-income prompt."),
        (83, 1360, 1517, "Complete F6 business-interest prompt."),
        (83, 1792, 1834, "Complete F7 business-kind prompt."),
        (83, 1844, 1886, "Complete F8 family-owner prompt."),
        (83, 2182, 2269, "Complete F9 family-work-time prompt."),
        (83, 2479, 2618, "Complete F10 incorporation prompt."),
        (83, 2856, 3181, "Complete F11 business-income prompt."),
        (84, 38, 246, "Complete F5 farm-net assignment block."),
        (84, 247, 515, "Complete F6-F8 business-assignment block."),
        (84, 516, 736, "Complete F9 work-time assignment block."),
        (84, 737, 1022, "Complete F10 incorporation-assignment block."),
        (84, 1023, 1672, "Complete F11 business-income assignment block."),
        (86, 66, 156, "F12 all-job wages prompt, first source fragment."),
        (86, 214, 246, "F12 all-job wages prompt, second source fragment."),
        (86, 421, 449, "All-job wage-total prompt, first source fragment."),
        (86, 529, 554, "All-job wage-total prompt, second source fragment."),
        (86, 636, 662, "All-job wage-total prompt, third source fragment."),
        (86, 728, 756, "All-job wage-total prompt, fourth source fragment."),
        (86, 775, 801, "All-job wage-total prompt, fifth source fragment."),
        (86, 474, 510, "F16 bonus-income prompt, first source fragment."),
        (86, 590, 617, "F16 bonus-income prompt, second source fragment."),
        (86, 697, 709, "F16 bonus-income prompt, third source fragment."),
        (86, 1077, 1112, "F14 bonus-income prompt, first source fragment."),
        (86, 1182, 1211, "F14 bonus-income prompt, second source fragment."),
        (86, 1230, 1261, "F14 bonus-income prompt, third source fragment."),
        (86, 1137, 1163, "Complete F17 bonus-amount prompt."),
        (86, 1374, 1418, "Complete F15 amount prompt."),
        (86, 1486, 1575, "F18 other-income prompt, first source fragment."),
        (86, 1585, 1663, "F18 other-income prompt, second source fragment."),
        (86, 2137, 2176, "Income-grid amount prompt fragment."),
        (86, 1849, 1861, "Income-grid month prompt fragment."),
        (86, 1944, 1975, "Income-grid month prompt fragment."),
        (86, 2071, 2082, "Income-grid month prompt fragment."),
        (86, 2184, 2196, "Income-grid month prompt fragment."),
        (86, 1869, 1882, "Income-grid work-hours prompt fragment."),
        (86, 1981, 1992, "Income-grid work-hours prompt fragment."),
        (86, 2091, 2105, "Income-grid work-hours prompt fragment."),
        (86, 2204, 2217, "Income-grid work-hours prompt fragment."),
        (86, 3590, 3607, "Farming subitem purpose fragment."),
        (86, 3689, 3695, "Farming subitem purpose fragment."),
        (86, 3734, 3744, "Farming subitem purpose fragment."),
        (86, 3823, 3840, "Roomer-income subitem purpose fragment."),
        (86, 4230, 4239, "Roomer-income subitem purpose fragment."),
        (87, 40, 1227, "Complete F18c assignment block."),
        (87, 1228, 1694, "Complete F19-F21 assignment block."),
        (88, 62, 152, "F12 all-job wages prompt, first source fragment."),
        (88, 194, 241, "F12 all-job wages prompt, second source fragment."),
        (88, 338, 366, "All-job wage-total prompt, first source fragment."),
        (88, 443, 468, "All-job wage-total prompt, second source fragment."),
        (88, 547, 573, "All-job wage-total prompt, third source fragment."),
        (88, 636, 664, "All-job wage-total prompt, fourth source fragment."),
        (88, 683, 709, "All-job wage-total prompt, fifth source fragment."),
        (88, 387, 424, "F16 bonus-income prompt, first source fragment."),
        (88, 501, 528, "F16 bonus-income prompt, second source fragment."),
        (88, 605, 617, "F16 bonus-income prompt, third source fragment."),
        (88, 973, 1008, "F14 bonus-income prompt, first source fragment."),
        (88, 1075, 1104, "F14 bonus-income prompt, second source fragment."),
        (88, 1123, 1154, "F14 bonus-income prompt, third source fragment."),
        (88, 1029, 1056, "Complete F17 bonus-amount prompt."),
        (88, 1269, 1312, "Complete F15 amount prompt."),
        (88, 1376, 1465, "F18 other-income prompt, first source fragment."),
        (88, 1475, 1552, "F18 other-income prompt, second source fragment."),
        (88, 2022, 2056, "Income-grid amount prompt fragment."),
        (88, 1734, 1746, "Income-grid month prompt fragment."),
        (88, 1845, 1859, "Income-grid month prompt fragment."),
        (88, 1954, 1965, "Income-grid month prompt fragment."),
        (88, 2066, 2078, "Income-grid month prompt fragment."),
        (88, 1756, 1769, "Income-grid work-hours prompt fragment."),
        (88, 1867, 1878, "Income-grid work-hours prompt fragment."),
        (88, 1976, 1990, "Income-grid work-hours prompt fragment."),
        (88, 2088, 2101, "Income-grid work-hours prompt fragment."),
        (88, 3539, 3592, "Complete farming-subitem purpose block."),
        (88, 3952, 3969, "Roomer-income subitem purpose fragment."),
        (88, 4296, 4305, "Roomer-income subitem purpose fragment."),
        (89, 41, 171, "Complete F22-F24 objective block."),
        (90, 244, 356, "Complete F23 extra-job inclusion prompt."),
        (90, 448, 509, "Complete F24 extra-job amount prompt."),
        (92, 290, 404, "Complete F23 extra-job inclusion prompt."),
        (92, 490, 550, "Complete F24 extra-job amount prompt."),
        (97, 471, 644, "Complete F51-F52 assignment block."),
        (98, 594, 678, "Complete F50 Wife-income prompt."),
        (98, 774, 860, "Complete F51 work-earnings prompt."),
        (98, 948, 1091, "Complete F52 work-income-total prompt."),
        (115, 1201, 1289, "Complete G4-G5 objective block."),
        (115, 1290, 1813, "Complete G6 objective block."),
        (136, 856, 1017, "Complete J1d interview-availability prompt."),
        (137, 241, 404, "Complete J1f current-activity prompt."),
        (137, 810, 824, "J2 retirement-year prompt, first clean source cell."),
        (
            137,
            902,
            910,
            "J2 retirement-year prompt, second clean source cell.",
        ),
        (137, 987, 997, "J2 retirement-year prompt, third clean source cell."),
        (
            137,
            1095,
            1102,
            "J2 retirement-year prompt, fourth clean source cell.",
        ),
        (
            137,
            1179,
            1186,
            "J2 retirement-year prompt, fifth clean source cell.",
        ),
        (137, 1353, 1468, "Complete J3 current-paid-work prompt."),
        (137, 1701, 1865, "Complete J4 employment-type prompt."),
        (
            137,
            2168,
            2195,
            "J5 incorporation-status prompt, first clean source cell.",
        ),
        (
            137,
            2284,
            2303,
            "J5 incorporation-status prompt, second clean source cell.",
        ),
        (
            137,
            2371,
            2385,
            "J5 incorporation-status prompt, third clean source cell.",
        ),
        (138, 157, 276, "Complete J12 employer-type prompt."),
        (139, 173, 194, "J19 salary prompt, first clean source cell."),
        (139, 271, 278, "J19 salary prompt, second clean source cell."),
        (139, 205, 226, "J22 regular-rate prompt, first clean source cell."),
        (139, 307, 323, "J22 regular-rate prompt, second clean source cell."),
        (139, 374, 390, "J22 regular-rate prompt, third clean source cell."),
        (139, 441, 451, "J22 regular-rate prompt, fourth clean source cell."),
        (139, 233, 256, "Complete J24 rate-type prompt cell."),
        (139, 817, 840, "J20 overtime prompt, first clean source cell."),
        (139, 853, 868, "J20 overtime prompt, second clean source cell."),
        (139, 919, 936, "J20 overtime prompt, third clean source cell."),
        (139, 949, 965, "J20 overtime prompt, fourth clean source cell."),
        (139, 978, 994, "J20 overtime prompt, fifth clean source cell."),
        (139, 1007, 1024, "J20 overtime prompt, sixth clean source cell."),
        (139, 1103, 1111, "J20 overtime prompt, seventh clean source cell."),
        (139, 556, 750, "Complete J23 overtime-rate prompt."),
        (139, 1293, 1524, "Complete J25 marginal-hour-pay prompt."),
        (
            139,
            1531,
            1550,
            "J21 overtime-amount prompt, first clean source cell.",
        ),
        (
            139,
            1562,
            1576,
            "J21 overtime-amount prompt, second clean source cell.",
        ),
        (
            139,
            1629,
            1641,
            "J21 overtime-amount prompt, third clean source cell.",
        ),
        (
            139,
            1653,
            1671,
            "J21 overtime-amount prompt, fourth clean source cell.",
        ),
        (141, 271, 371, "Complete J35 present-employer exposure prompt."),
        (141, 651, 829, "Complete J36 present-position start prompt."),
        (
            141,
            1981,
            2036,
            "J37 reordered temporary/permanent prompt fragment.",
        ),
        (141, 2090, 2173, "Complete J37 temporary/permanent prompt."),
        (141, 2514, 2565, "Complete J39 hours prompt."),
        (
            142,
            63,
            142,
            "Previous-work-situation prompt, first source fragment.",
        ),
        (
            142,
            254,
            492,
            "Previous-work-situation prompt, second source fragment.",
        ),
        (142, 1598, 1702, "Complete J42 prior-work prompt."),
        (142, 2045, 2271, "Complete J43 employer-continuity prompt."),
        (142, 2734, 2951, "Complete J44 job-ending-reason prompt."),
        (142, 3021, 3171, "Complete J45 position-end prompt."),
        (143, 316, 468, "Complete J47 employer-type prompt."),
        (143, 1270, 1329, "Complete J48 industry prompt."),
        (143, 1502, 1614, "Complete J49 occupation prompt."),
        (143, 2053, 2172, "Complete J51 final-pay question block."),
        (143, 2516, 2566, "Complete J52 hours prompt."),
        (144, 57, 267, "Complete J53 position-start prompt."),
        (144, 1153, 1337, "Complete J54 temporary/permanent prompt."),
        (144, 1420, 1485, "Complete J55 starting-pay prompt."),
        (144, 1683, 1739, "Complete J56 hours prompt."),
        (145, 1055, 1531, "Complete J57 work-absence prompt."),
        (145, 1635, 1673, "Complete J58 duration prompt."),
        (145, 1795, 1817, "Complete J59 timing prompt."),
        (145, 1819, 1884, "Complete J60 sickness-absence prompt."),
        (145, 2032, 2068, "Complete J61 duration prompt."),
        (145, 2290, 2312, "Complete J62 timing prompt."),
        (145, 2438, 2494, "Complete J63 vacation prompt."),
        (145, 2667, 2718, "Complete J64 duration prompt."),
        (145, 2855, 2910, "Complete J65 timing prompt."),
        (146, 149, 215, "Complete J66 strike-absence prompt."),
        (146, 292, 328, "Complete J67 duration prompt."),
        (146, 430, 477, "Complete J68 timing prompt."),
        (146, 551, 671, "Complete J69 unemployment-absence prompt."),
        (146, 800, 837, "Complete J70 duration prompt."),
        (146, 1025, 1073, "Complete J71 timing prompt."),
        (146, 1142, 1244, "Complete J72 no-job prompt."),
        (146, 1276, 1308, "Complete J73 duration prompt."),
        (146, 1411, 1460, "Complete J74 timing prompt."),
        (146, 1535, 1620, "Complete J75 weeks-worked prompt."),
        (146, 2040, 2129, "Complete J76 weekly-hours prompt."),
        (146, 2208, 2268, "Complete J77 overtime prompt."),
        (146, 2448, 2508, "Complete J78 overtime-hours prompt."),
        (147, 51, 175, "Complete J79 extra-job prompt."),
        (147, 391, 448, "Complete J80 occupation prompt."),
        (147, 510, 539, "J81 duties prompt, first clean source cell."),
        (147, 605, 625, "J81 duties prompt, second clean source cell."),
        (147, 645, 655, "J81 duties prompt, third clean source cell."),
        (147, 700, 765, "Complete J82 extra-job-amount prompt."),
        (147, 1001, 1102, "Complete J83 weeks-worked prompt."),
        (147, 1240, 1308, "Complete J84 timing prompt."),
        (147, 1377, 1489, "Complete J85 weekly-hours prompt."),
        (147, 1601, 1672, "Complete J86 repeat-job prompt."),
        (147, 2244, 2488, "Complete J87 unemployment-absence prompt."),
        (147, 2499, 2538, "Complete J88 duration prompt."),
        (147, 2620, 2669, "Complete J89 timing prompt."),
        (148, 52, 144, "J90 no-job prompt, first source fragment."),
        (148, 265, 273, "J90 no-job prompt, second source fragment."),
        (148, 286, 320, "Complete OCR-surviving J91 prompt."),
        (148, 398, 446, "Complete J92 timing prompt."),
        (148, 531, 557, "Complete OCR-surviving J93 prompt."),
        (148, 754, 858, "Complete J95 weekly-hours prompt."),
        (148, 910, 1031, "Complete J96 extra-job prompt."),
        (148, 1257, 1313, "Complete J97 occupation prompt."),
        (148, 1429, 1456, "J98 duties prompt, first clean source cell."),
        (148, 1476, 1496, "J98 duties prompt, second clean source cell."),
        (148, 1586, 1596, "J98 duties prompt, third clean source cell."),
        (148, 1647, 1737, "Complete J99 weeks-worked prompt."),
        (148, 1883, 2002, "Complete J100 timing prompt."),
        (148, 2052, 2195, "Complete J101 weekly-hours prompt."),
        (148, 2308, 2373, "Complete J102 repeat-job prompt."),
        (149, 63, 243, "Complete J103 more-work-available prompt."),
        (149, 259, 307, "J104 amount prompt, left-column source fragment."),
        (
            149,
            370,
            381,
            "J104 reporting-unit prompt, left-column source fragment.",
        ),
        (149, 1440, 1552, "Complete J110 lifetime-work exposure prompt."),
        (149, 1689, 1782, "Complete J111 full-time-years prompt."),
        (149, 1914, 2099, "Complete J112 fractional-work exposure prompt."),
        (150, 865, 964, "Complete K8 timing prompt."),
        (151, 54, 113, "Complete K9 ever-worked prompt."),
        (151, 180, 330, "Complete K10 last-worked prompt."),
        (151, 598, 672, "Complete K11 1984-search prompt."),
        (151, 732, 764, "Complete K12 duration prompt."),
        (151, 793, 812, "Complete K13 timing prompt."),
        (151, 924, 984, "Complete K14 1985-search prompt."),
        (151, 1063, 1095, "Complete K15 duration prompt."),
        (151, 1122, 1141, "Complete K16 timing prompt."),
        (151, 1237, 1324, "Complete K17 occupation prompt."),
        (151, 1515, 1573, "Complete K18 duties prompt."),
        (151, 1577, 1630, "Complete K19 industry prompt."),
        (152, 356, 514, "Complete K21 employer-type prompt."),
        (152, 1869, 1979, "Complete K25 job-ending-reason prompt."),
        (152, 1983, 2135, "Complete K26 position-end prompt."),
        (153, 57, 175, "Complete K27 final-pay prompt."),
        (153, 316, 364, "Complete K28 hours prompt."),
        (153, 430, 625, "Complete K29 position-start prompt."),
        (153, 1542, 1677, "Complete K30 temporary/permanent prompt."),
        (153, 1743, 1802, "Complete K31 starting-pay prompt."),
        (153, 2029, 2076, "Complete K32 hours prompt."),
        (154, 190, 499, "Complete K33 previous-situation prompt."),
        (154, 1234, 1414, "Complete K34 prior-work prompt."),
        (154, 1698, 1941, "Complete K35 employer-continuity prompt."),
        (154, 2279, 2492, "Complete K36 position-end prompt."),
        (155, 308, 454, "Complete K38 employer-type prompt."),
        (155, 932, 991, "Complete K39 industry prompt."),
        (155, 1212, 1294, "Complete K40 occupation prompt."),
        (155, 1501, 1559, "Complete K41 duties prompt."),
        (155, 1563, 1687, "Complete K42 final-pay question block."),
        (155, 1922, 1971, "Complete K43 hours prompt."),
        (156, 162, 361, "Complete K44 position-start prompt."),
        (156, 1124, 1259, "Complete K45 temporary/permanent prompt."),
        (156, 1337, 1396, "Complete K46 starting-pay prompt."),
        (156, 1638, 1688, "Complete K47 hours prompt."),
        (157, 909, 971, "K48 preface, first clean source cell."),
        (157, 1017, 1080, "K48 preface, second clean source cell."),
        (157, 1129, 1194, "K48 preface, third clean source cell."),
        (157, 1233, 1295, "K48 preface, fourth clean source cell."),
        (157, 1306, 1370, "K48 vacation prompt, fifth clean source cell."),
        (157, 1456, 1511, "Complete K49 duration prompt."),
        (157, 1643, 1667, "Complete K50 timing prompt."),
        (157, 1752, 1839, "Complete K51 family-sickness prompt."),
        (157, 2008, 2045, "Complete K52 duration prompt."),
        (157, 2341, 2365, "Complete K53 timing prompt."),
        (157, 2368, 2432, "Complete K54 sickness-absence prompt."),
        (157, 2609, 2646, "Complete K55 duration prompt."),
        (157, 2793, 2816, "Complete K56 timing prompt."),
        (158, 157, 222, "Complete K57 strike-absence prompt."),
        (158, 381, 416, "Complete K58 duration prompt."),
        (158, 613, 661, "Complete K59 timing prompt."),
        (158, 750, 863, "Complete K60 unemployment-absence prompt."),
        (158, 1013, 1048, "Complete K61 duration prompt."),
        (158, 1245, 1293, "Complete K62 timing prompt."),
        (158, 1368, 1471, "Complete K63 no-job prompt."),
        (158, 1586, 1617, "Complete K64 duration prompt."),
        (158, 1813, 1862, "Complete K65 timing prompt."),
        (158, 1952, 2034, "Complete K66 weeks-worked prompt."),
        (158, 2448, 2541, "Complete K67 weekly-hours prompt."),
        (159, 57, 260, "Complete K68 extra-job prompt."),
        (159, 632, 691, "Complete K69 occupation prompt."),
        (159, 701, 802, "Complete K70 duties prompt."),
        (159, 811, 933, "Complete K71 extra-job-amount prompt."),
        (159, 1217, 1320, "Complete K72 weeks-worked prompt."),
        (159, 1429, 1498, "Complete K73 timing prompt."),
        (159, 1677, 1790, "Complete K74 weekly-hours prompt."),
        (159, 1904, 1976, "Complete K75 repeat-job prompt."),
        (159, 2724, 2971, "Complete K76 unemployment-absence prompt."),
        (159, 3060, 3095, "Complete K77 duration prompt."),
        (159, 3179, 3231, "Complete K78 timing prompt."),
        (160, 176, 282, "Complete K79 no-job prompt."),
        (160, 376, 413, "Complete OCR-surviving K80 prompt."),
        (160, 521, 571, "Complete K81 timing prompt."),
        (160, 668, 759, "Complete K82 weeks-worked prompt."),
        (160, 958, 1007, "Complete K83 timing prompt."),
        (160, 1097, 1205, "Complete K84 weekly-hours prompt."),
        (160, 1271, 1475, "Complete K85 extra-job prompt."),
        (160, 1814, 1872, "Complete K86 occupation prompt."),
        (160, 1884, 1984, "Complete K87 duties prompt."),
        (160, 1995, 2100, "Complete K88 weeks-worked prompt."),
        (160, 2220, 2289, "Complete K89 timing prompt."),
        (160, 2517, 2632, "Complete K90 weekly-hours prompt."),
        (160, 2754, 2825, "Complete K91 repeat-job prompt."),
        (161, 53, 159, "Complete K92 lifetime-work prompt."),
        (161, 260, 346, "Complete K93 full-time-years prompt."),
        (161, 510, 624, "Complete K94 fractional-work prompt."),
    )
    for page, start, end, note in manual_purpose_specs:
        add(
            page,
            start,
            end,
            P,
            source_routes(page, start, end, P),
            note,
            replace_overlap=True,
        )

    # Recover explicit remuneration phrases outside the stage-1 lexical
    # grammar.  Add only a nonoverlapping exact match; nearby benefits or
    # generic uses of "income" do not auto-promote.
    for page_number in sorted(SEMANTIC_PAGES):
        page_text = page_texts[page_number - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(page_text)
        for match in MANUAL_REMUNERATION_RE.finditer(page_text):
            start = offsets[match.start()]
            end = offsets[match.end()]
            if not in_relevant_window(
                page_number,
                start,
                end,
                M,
                match.group(),
            ):
                continue
            add(
                page_number,
                start,
                end,
                "remuneration_component_anchor",
                source_routes(
                    page_number, start, end, "remuneration_component_anchor"
                ),
                "Source-explicit remuneration phrase manually recovered from exact bytes.",
            )

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
        review_occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
        occurrence_specs.append(
            {
                "review_occurrence_id": review_occurrence_id,
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

    occurrence_by_review_id = {
        spec["review_occurrence_id"]: spec for spec in occurrence_specs
    }
    parent_anchor_specs = [
        spec
        for spec in occurrence_specs
        if spec["occurrence_kind"]
        in {
            "job_anchor",
            "role_total_anchor",
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
        }
    ]
    parent_anchor_by_key = {
        (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        ): spec
        for spec in parent_anchor_specs
    }

    # Ambiguous two-column income layouts need explicit source-local parent
    # decisions; nearest-neighbour distance alone would bind several wage
    # components to the adjacent unincorporated-business wording.
    explicit_parent_keys: dict[
        tuple[int, int, int, str], tuple[tuple[int, int, int, str], ...]
    ] = {
        **{
            (23, start, end, M): ((23, 365, 368, J),)
            for start, end in (
                (73, 79),
                (80, 84),
                (89, 97),
                (210, 216),
                (234, 242),
                (302, 308),
                (324, 334),
                (353, 368),
                (391, 395),
                (401, 405),
                (723, 729),
                (764, 772),
                (843, 851),
                (1130, 1136),
                (1142, 1152),
            )
        },
        **{
            (24, start, end, M): ((24, 82, 90, J),)
            for start, end in (
                (266, 272),
                (298, 314),
                (653, 669),
                (720, 728),
                (1365, 1369),
            )
        },
        (28, 2140, 2146, M): ((28, 1893, 1901, J),),
        (28, 2150, 2154, M): ((28, 1893, 1901, J),),
        (32, 1220, 1226, M): ((32, 1029, 1037, J),),
        (32, 1230, 1234, M): ((32, 1029, 1037, J),),
        **{
            (35, start, end, M): ((35, 133, 150, J),)
            for start, end in (
                (1804, 1808),
                (1812, 1818),
                (3590, 3596),
                (3600, 3604),
            )
        },
        (39, 2194, 2202, M): ((39, 2032, 2041, J),),
        (39, 2330, 2338, M): ((39, 2032, 2041, J),),
        (40, 2564, 2572, M): ((40, 2413, 2421, J),),
        (40, 2794, 2802, M): ((40, 2413, 2421, J),),
        (40, 2857, 2865, M): ((40, 2413, 2421, J),),
        (50, 355, 361, M): ((50, 227, 235, J),),
        (52, 1791, 1797, M): ((52, 1591, 1599, J),),
        (52, 1801, 1805, M): ((52, 1591, 1599, J),),
        (55, 1233, 1239, M): ((55, 1047, 1055, J),),
        (55, 1243, 1247, M): ((55, 1047, 1055, J),),
        (83, 1059, 1077, M): ((83, 863, 870, FA),),
        (84, 649, 705, C): ((84, 455, 463, BA),),
        (85, 447, 453, M): ((85, 959, 1052, T),),
        (85, 638, 684, C): ((85, 959, 1052, T),),
        (85, 770, 775, M): ((85, 959, 1052, T),),
        (85, 776, 782, M): ((85, 959, 1052, T),),
        (85, 800, 806, M): ((85, 959, 1052, T),),
        (85, 893, 942, C): ((85, 959, 1052, T),),
        (85, 1045, 1050, M): ((85, 959, 1052, T),),
        (85, 1757, 1765, M): ((85, 959, 1052, T),),
        (85, 2447, 2506, C): ((85, 2419, 2426, FA),),
        (86, 219, 224, M): ((86, 529, 550, T),),
        (86, 229, 237, M): ((86, 529, 550, T),),
        (86, 1203, 1210, M): ((86, 529, 550, T),),
        (86, 1230, 1238, M): ((86, 529, 550, T),),
        (86, 1240, 1244, M): ((86, 529, 550, T),),
        (86, 1249, 1260, M): ((86, 529, 550, T),),
        (86, 4423, 4527, C): (
            (86, 3830, 3840, BA),
            (86, 4230, 4239, BA),
        ),
        (86, 4535, 4640, C): (
            (86, 3830, 3840, BA),
            (86, 4230, 4239, BA),
        ),
        (87, 181, 191, M): ((87, 50, 69, BA),),
        (88, 194, 198, M): ((88, 443, 464, T),),
        (88, 214, 219, M): ((88, 443, 464, T),),
        (88, 224, 232, M): ((88, 443, 464, T),),
        (88, 1096, 1103, M): ((88, 443, 464, T),),
        (88, 1123, 1131, M): ((88, 443, 464, T),),
        (88, 1133, 1137, M): ((88, 443, 464, T),),
        (88, 1142, 1153, M): ((88, 443, 464, T),),
        (88, 4714, 4730, C): (
            (88, 3959, 3969, BA),
            (88, 4296, 4305, BA),
        ),
        (88, 4738, 4841, C): (
            (88, 3959, 3969, BA),
            (88, 4296, 4305, BA),
        ),
        **{
            (139, start, end, M): ((139, 95, 98, J),)
            for start, end in (
                (133, 149),
                (271, 277),
                (307, 323),
                (669, 685),
                (740, 748),
                (1505, 1509),
            )
        },
        (141, 2287, 2293, M): ((141, 2003, 2011, J),),
        (141, 2297, 2301, M): ((141, 2003, 2011, J),),
        (144, 1456, 1462, M): ((144, 1247, 1255, J),),
        (144, 1466, 1470, M): ((144, 1247, 1255, J),),
        (147, 700, 831, M): (),
        (153, 1774, 1780, M): ((153, 1595, 1603, J),),
        (153, 1784, 1788, M): ((153, 1595, 1603, J),),
        (154, 572, 582, C): (),
        (154, 598, 609, C): (),
        (156, 1368, 1374, M): ((156, 1179, 1187, J),),
        (156, 1378, 1382, M): ((156, 1179, 1187, J),),
        (159, 811, 997, M): (),
    }

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
        label = (
            page_texts[page - 1]
            .encode("utf-8")[spec["utf8_byte_start"] : spec["utf8_byte_end"]]
            .decode("utf-8", errors="strict")
        )
        if kind == "role_anchor":
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                label
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                kind
            ]
        printed_identifier = annotation._source_printed_identifier(
            page_texts[page - 1], spec["utf8_byte_start"]
        )
        parent_ids: list[str] = []
        if kind in {"context_anchor", "remuneration_component_anchor"}:
            component_key = (
                page,
                spec["utf8_byte_start"],
                spec["utf8_byte_end"],
                kind,
            )
            if component_key in explicit_parent_keys:
                selected = [
                    parent_anchor_by_key[parent_key]
                    for parent_key in explicit_parent_keys[component_key]
                ]
                if any(
                    not branch_compatible(spec, parent) for parent in selected
                ):
                    raise ValueError(
                        f"explicit parent branch mismatch: {component_key}"
                    )
            else:
                compatible = [
                    parent
                    for parent in parent_anchor_specs
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
                    nearest_distance = min(
                        (item[0] for item in distances), default=10**9
                    )
                    selected = [
                        parent
                        for distance, parent in distances
                        if distance == nearest_distance and distance <= 160
                    ]
            parent_ids = [
                parent["review_occurrence_id"] for parent in selected
            ]
            parent_ids.sort(
                key=lambda review_id: occurrence_specs.index(
                    occurrence_by_review_id[review_id]
                )
            )
        if kind not in {"context_anchor", "remuneration_component_anchor"}:
            parent_note = "Parent resolution is not applicable to this non-component anchor."
        elif parent_ids:
            parent_note = (
                "Explicit source-local parent anchors were verified from the same "
                "question, line, or adjacent source block."
            )
        else:
            parent_note = (
                "Whole-page review found general or no-job context and asserted no "
                "document-local parent anchor."
            )
        local_anchor_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": printed_identifier,
                "parent_review_occurrence_ids": parent_ids,
                "parent_resolution_note": parent_note,
                "classification_status": "provisional_document_local",
            }
        )

    occurrence_by_key = {
        (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
            spec["occurrence_kind"],
        ): spec
        for spec in occurrence_specs
    }
    occurrence_order = {
        spec["review_occurrence_id"]: index
        for index, spec in enumerate(occurrence_specs)
    }
    repeat_resolution_specs: dict[
        tuple[int, int, int],
        tuple[
            str,
            tuple[tuple[int, int, int, str], ...],
            tuple[tuple[int, int, int, str], ...],
            str,
            str,
        ],
    ] = {
        (20, 1223, 1248): (
            "explicit_repeat_instruction",
            ((20, 1219, 1222, J),),
            ((19, 747, 762, J),),
            "document_local",
            "document_local_source_evidence_complete",
        ),
        (85, 2416, 2665): (
            "explicit_repeat_instruction",
            (
                (85, 2386, 2393, FA),
                (85, 2419, 2426, FA),
                (85, 2580, 2587, FA),
                (85, 2624, 2631, FA),
            ),
            ((82, 940, 944, FA),),
            "document_local",
            "document_local_source_evidence_complete",
        ),
        (97, 655, 881): (
            "explicit_cross_reference",
            ((97, 737, 745, BA), (97, 849, 857, BA)),
            ((84, 1245, 1253, BA),),
            "document_local",
            "document_local_source_evidence_complete",
        ),
        (135, 1263, 1339): (
            "explicit_cross_reference",
            (
                (135, 1295, 1299, R),
                (135, 1301, 1305, R),
                (135, 1311, 1317, R),
            ),
            (),
            "cross_document",
            "preserved_for_global_resolution",
        ),
        (141, 99, 125): (
            "explicit_cross_reference",
            ((141, 99, 125, C),),
            ((137, 1961, 1974, C),),
            "document_local",
            "document_local_source_evidence_complete",
        ),
        (143, 107, 149): (
            "explicit_cross_reference",
            ((143, 132, 149, J),),
            ((142, 311, 327, J), (142, 2084, 2092, J)),
            "document_local",
            "document_local_source_evidence_complete",
        ),
        (155, 105, 149): (
            "explicit_cross_reference",
            ((155, 132, 149, J),),
            ((154, 319, 335, J), (154, 1743, 1751, J)),
            "document_local",
            "document_local_source_evidence_complete",
        ),
    }

    repeat_alias_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != "repeat_or_alias_instruction":
            continue
        raw = page_texts[spec["page_number"] - 1].encode("utf-8")[
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ]
        text = raw.decode("utf-8", errors="strict").casefold()
        repeat_key = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        override = repeat_resolution_specs.get(repeat_key)
        if override is None:
            relation = (
                "explicit_repeat_instruction"
                if any(
                    marker in text
                    for marker in (
                        "repeat",
                        "again",
                        "another job",
                        "other job",
                    )
                )
                else "explicit_cross_reference"
            )
            alias_keys: tuple[tuple[int, int, int, str], ...] = ()
            canonical_keys: tuple[tuple[int, int, int, str], ...] = ()
            target_scope = "unresolved"
            resolution_status = "preserved_for_global_resolution"
        else:
            (
                relation,
                alias_keys,
                canonical_keys,
                target_scope,
                resolution_status,
            ) = override
        alias_ids = [
            occurrence_by_key[key]["review_occurrence_id"]
            for key in alias_keys
        ]
        canonical_ids = [
            occurrence_by_key[key]["review_occurrence_id"]
            for key in canonical_keys
        ]
        evidence_ids = sorted(
            {
                spec["review_occurrence_id"],
                *alias_ids,
                *canonical_ids,
            },
            key=occurrence_order.__getitem__,
        )
        repeat_alias_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "relation": relation,
                "alias_anchor_review_occurrence_ids": alias_ids,
                "canonical_anchor_review_occurrence_ids": canonical_ids,
                "evidence_review_occurrence_ids": evidence_ids,
                "target_scope": target_scope,
                "resolution_status": resolution_status,
            }
        )

    counts_by_page = Counter(spec["page_number"] for spec in occurrence_specs)
    page_review_rows = [
        {
            "page_number": page_number,
            "page_text_utf8_sha256": annotation._sha256(
                page_text.encode("utf-8")
            ),
            "whole_page_review_complete": True,
            "review_status": "complete",
            "review_note": (
                "Whole page reviewed against exact source bytes; "
                f"{counts_by_page[page_number]} source occurrence atoms retained."
            ),
        }
        for page_number, page_text in enumerate(page_texts, start=1)
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
            "whole_page_review": "all_199_pages_including_empty_occurrence_pages",
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
        annotation.REVIEW_PATH, annotation._canonical_bytes(review), args.check
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
