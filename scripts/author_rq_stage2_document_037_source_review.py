#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 37.

The 181-page 1986 QxQ was reviewed page by page from the authenticated
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

import build_rq_stage2_document_037_annotation as annotation

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
EMPLOYMENT_PAGES = frozenset(range(18, 90)) - {39}
WORK_INCOME_PAGES = frozenset({*range(98, 109), 114, 115})
WORK_HISTORY_PAGES = frozenset({167, 168, 172, 174, 175, 176, 177, 181})
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
    106: ((59, 650),),
    107: ((39, 170),),
    108: ((58, 729),),
    114: ((396, 1636),),
    115: ((606, 1013),),
    167: ((1660, 1988),),
    168: ((254, 1012),),
    172: ((2193, 2505),),
    174: ((828, 1481),),
    175: ((475, 970), (1201, 1487)),
    176: ((230, 597), (2161, 2533)),
    177: ((1472, 1762),),
    181: ((315, 361), (2294, 2750)),
}

EMPLOYMENT_KINDS = frozenset({F, R, J, M, C, P, A})
INCOME_KINDS = frozenset(annotation.OCCURRENCE_KINDS)
HISTORY_KINDS = frozenset({F, R, J, C, P, A})

# Narrative Q-by-Q pages contain many interrogative examples and generic
# mentions of a job.  On these pages, only identifier-bearing prompt lines
# auto-survive; complete source blocks are added explicitly below.
QBYQ_PAGES = frozenset(
    {
        19,
        21,
        22,
        23,
        25,
        27,
        29,
        31,
        33,
        37,
        41,
        43,
        45,
        47,
        49,
        51,
        53,
        55,
        57,
        67,
        99,
        101,
        103,
        105,
        107,
        115,
        167,
        174,
        175,
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
    "DO NOT ASK",
    "DON'T ASK",
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

    flow("head_codes_1_3", 18, 289, 360)
    flow("head_codes_4_8", 18, 903, 957)
    flow(
        "head_paid_work_yes",
        18,
        *byte_find(18, "11. YESI"),
        (("head_codes_4_8",),),
    )
    flow(
        "head_not_working_route",
        18,
        *line_span(18, 36, 39),
        (("head_codes_4_8",),),
    )

    flow("female_head_exit", 66, 287, 321)
    flow("no_wife_exit", 66, 470, 525)
    flow("wife_codes_1_3", 66, 710, 781)
    flow("wife_paid_work_yes", 66, 1339, 1348)
    flow("wife_not_working_route", 66, 1351, 1359)

    # Both clean/fill copies are source pages and therefore retain their own
    # exact farmer/all-other and extra-job alternatives.
    flow("g2_p98_farmer", 98, 403, 435)
    flow("g2_p98_all_others", 98, 459, 472)
    flow("g2_p100_farmer", 100, 410, 442)
    flow("g2_p100_all_others", 100, 467, 489)
    flow("g22_p106_extra_job", 106, 178, 200)
    flow("g22_p106_all_others", 106, 214, 259)
    flow("g22_p108_all_others", 108, 224, 242)
    flow("g22_p108_extra_job", 108, 260, 282)
    flow("g49_wife_present", 114, 502, 534)
    flow("g49_all_others_exit", 114, 556, 609)

    # K and L contribute only narrow work-history fields.  Their entry/exit
    # atoms remain in the graph so those fields do not lose section ancestry.
    flow("k_new_wife_entry", 168, 449, 461)
    flow("k_splitoff_wife_entry", 168, 502, 516)
    flow("k_reinterview_exit", 168, 848, 866)
    flow("k_splitoff_exit", 168, 895, 913)
    k_work_routes = (("k_new_wife_entry",), ("k_splitoff_wife_entry",))
    flow("k44_to_section_l", 172, 2288, 2355, k_work_routes)

    flow("l_splitoff_entry", 176, 293, 304)
    flow("l_new_head_entry", 176, 403, 414)
    flow("l_same_head_exit", 176, 422, 433)
    flow(
        "l_cover_sheet_exit",
        176,
        503,
        597,
        (("l_same_head_exit",),),
    )
    l_work_routes = (("l_splitoff_entry",), ("l_new_head_entry",))
    flow("l11_no_to_l13", 177, 1631, 1639, l_work_routes)
    flow("l49_no_to_l55", 181, 349, 360, l_work_routes)
    flow("l57_cover_sheet_exit", 181, 2424, 2454, l_work_routes)
    flow("l58_final_exit", 181, 2597, 2750, l_work_routes)

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
    wife_d_route = (("wife_codes_1_3",), ("wife_paid_work_yes",))
    wife_e_route = (("wife_not_working_route",),)
    k_work_route = k_work_routes
    l_work_route = l_work_routes

    def source_routes(
        page: int, start: int, _end: int, _kind: str
    ) -> tuple[tuple[str, ...], ...]:
        if 20 <= page <= 51:
            return head_b_route
        if 52 <= page <= 65:
            return head_c_route
        if 68 <= page <= 78:
            return wife_d_route
        if 79 <= page <= 89:
            return wife_e_route
        if page == 98:
            if 686 <= start < 1174:
                return (("g2_p98_farmer",),)
            if start >= 1174:
                return (("g2_p98_farmer",), ("g2_p98_all_others",))
        if page == 100:
            if 737 <= start < 1221:
                return (("g2_p100_farmer",),)
            if start >= 1221:
                return (("g2_p100_farmer",), ("g2_p100_all_others",))
        if page == 106 and start >= 263:
            return (("g22_p106_extra_job",),)
        if page == 108 and start >= 349:
            return (("g22_p108_extra_job",),)
        if page == 114:
            if start >= 613:
                return (("g49_wife_present",),)
        if page == 115:
            return (("g49_wife_present",),)
        if page == 172:
            return k_work_route
        if page in {176, 177, 181}:
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
        if page == 105:
            return False
        if page == 107 and kind != R:
            return False
        if page == 115 and kind in {F, J, M, T, FA, BA}:
            return False
        if page == 168 and kind != F:
            return False
        if page == 99 and kind not in {R, FA, P}:
            return False
        if page in {101, 103, 167} and kind != R:
            return False
        if page in {172, 176, 177, 181} and kind not in {F, R}:
            return False
        if page == 114 and kind == C:
            return False
        if page == 114 and kind == P and 991 <= start < 1141:
            return False
        if page == 174 and start < 928 and kind in {C, P}:
            return False
        if page == 175 and kind == P:
            return False
        if kind in {T, FA, BA}:
            if kind == T:
                # The four lawful work totals are manually re-sliced below;
                # detector lines on two-column grids cross unrelated columns.
                return False
            if kind == FA:
                return page in {98, 100, 102, 104} or (
                    page == 99 and start < 728
                )
            if kind == BA:
                return page in {98, 100, 102, 104}
        if kind == F:
            if any(marker in folded for marker in FLOW_EXCLUSION_MARKERS):
                return False
            return any(marker in folded for marker in FLOW_ACTION_MARKERS)
        if kind == P:
            if row is None:
                return True
            return retain_purpose(row)
        if kind == A:
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
                return page in {98, 100, 106, 108}
            if page == 19:
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
        if kind == C and page == 19:
            return False
        if kind == M and page in {99, 101, 103, 105, 107, 115}:
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
        (19, 196, 384, "B/C instructions explicitly recur in D/E."),
        (33, 1950, 1968, "B39 explicitly cross-references B11."),
        (33, 1969, 2022, "B40-41 explicitly cross-reference B9-10."),
        (
            33,
            2077,
            2288,
            "Additional changes use the Work History Supplement.",
        ),
        (
            37,
            39,
            349,
            "Supplement repeats across four employment sections and jobs.",
        ),
        (37, 350, 372, "S1-S3 explicitly cross-reference B32-34."),
        (37, 373, 393, "S4-S9 explicitly cross-reference B36."),
        (37, 394, 416, "S10-S15 explicitly cross-reference B39-44."),
        (57, 39, 81, "C20-21 explicitly cross-reference B4 and B6."),
        (57, 82, 103, "C22-24 explicitly cross-reference B20-22."),
        (57, 104, 475, "C25-47 repeat the B work-history instructions."),
        (57, 476, 646, "C48-66 explicitly repeat B48-66."),
        (57, 737, 859, "C68-75 explicitly repeat B70-77."),
        (57, 860, 1068, "C76-84 explicitly repeat B78-86."),
        (57, 1069, 1129, "C85-91 explicitly repeat B70-77."),
        (
            67,
            166,
            517,
            "D/E role definitions explicitly hand off to the Glossary.",
        ),
        (
            67,
            518,
            777,
            "D/E explicitly parallel B/C and reuse their objectives.",
        ),
        (99, 84, 355, "G3-24 and G52 income require B/C and D/E work hours."),
        (
            99,
            356,
            523,
            "Employment-section work explicitly requires G income.",
        ),
        (101, 36, 241, "G5 explicitly reuses G3 and G4 amounts."),
        (
            101,
            242,
            462,
            "G6-8 are a repeated business-income instruction block.",
        ),
        (101, 463, 660, "G9 explicitly hands work hours back to B/C and D/E."),
        (105, 40, 868, "Roomer income explicitly requires B/C work hours."),
        (
            105,
            1709,
            2023,
            "G21 explicitly sends missing work hours back to B/C.",
        ),
        (
            106,
            92,
            159,
            "G22 explicitly cross-references B70 and C68 extra jobs.",
        ),
        (106, 273, 389, "G23 repeats the extra-job earnings inclusion check."),
        (
            108,
            91,
            156,
            "G22 explicitly cross-references B70 and C68 extra jobs.",
        ),
        (108, 359, 475, "G23 repeats the extra-job earnings inclusion check."),
        (
            115,
            606,
            1013,
            "G51-52 explicitly link D/E work and G income both ways.",
        ),
        (174, 828, 928, "L4-5 explicitly cross-reference B9-11."),
        (
            175,
            1201,
            1487,
            "L14-58 explicitly duplicate and cross-reference Section K.",
        ),
    )
    for page, start, end, note in repeat_blocks:
        manual(page, start, end, (A,), note)

    # Printed AGAIN labels occur twice on each two-column continuation row.
    # Preserve each visible atom independently rather than one cross-column
    # detector span.
    again_atoms: tuple[tuple[int, int, int], ...] = (
        (46, 2718, 2727),
        (46, 2763, 2772),
        (48, 3849, 3858),
        (48, 3876, 3885),
        (64, 2558, 2567),
        (64, 2591, 2600),
        (65, 3471, 3480),
        (65, 3504, 3513),
        (77, 2166, 2175),
        (77, 2204, 2213),
        (78, 3517, 3526),
        (78, 3551, 3560),
        (88, 2565, 2574),
        (88, 2593, 2603),
        (89, 3275, 3284),
        (89, 3314, 3323),
    )
    for page, start, end in again_atoms:
        manual(
            page,
            start,
            end,
            (A,),
            "Atomic printed AGAIN continuation instruction.",
        )

    # Section G source blocks: retain only work-linked income constructs and
    # replace line/token fragments with the complete printed semantic unit.
    manual(99, 590, 844, (C, A), "Complete G2 farm-work handoff context.")
    manual(99, 590, 653, (P,), "G2 identifies the employment lookup purpose.")
    manual(101, 242, 305, (P,), "G6-8 business-income field purpose line.")
    manual(101, 463, 660, (C,), "Complete G9 work-hours handoff context.")
    manual(101, 463, 520, (P,), "G9 work-hours handoff purpose line.")

    manual(103, 41, 172, (C,), "Complete G12 wage-work context block.")
    manual(103, 173, 430, (C,), "Complete G13 current-Head wage context.")
    manual(103, 304, 430, (A,), "G13 explicitly includes extra-job income.")
    manual(
        103, 1063, 1496, (A,), "G13 avoids duplicate business and wage income."
    )
    manual(103, 1497, 1685, (C, A), "G14-15 avoid duplicate income reporting.")
    manual(
        103, 1686, 1878, (C, M), "G16-17 commissions-only earnings component."
    )
    manual(
        103, 1879, 2484, (C,), "Complete G18a professional-practice context."
    )
    manual(
        103,
        2300,
        2484,
        (A,),
        "G18a excludes income already reported at G11/G13.",
    )
    manual(
        103,
        2485,
        2752,
        (C, A),
        "G18b redirects farming income by job context.",
    )

    manual(105, 40, 868, (C,), "Complete roomer-income work linkage context.")
    manual(105, 1226, 2023, (C,), "Complete G19-21 work-hours context.")
    manual(
        105, 1878, 2023, (F,), "Missing work hours route back to Section B/C."
    )

    manual(106, 273, 389, (P,), "Complete G23 extra-job inclusion prompt.")
    manual(106, 477, 648, (M, P), "Complete G24 extra-job earnings field.")
    manual(107, 39, 169, (C,), "Complete G22-24 work-income objective.")
    manual(107, 39, 104, (P,), "G22-24 work-income purpose statement.")
    manual(108, 359, 475, (P,), "Complete G23 extra-job inclusion prompt.")
    manual(108, 563, 727, (M, P), "Complete G24 extra-job earnings field.")

    manual(102, 551, 578, (T,), "Exact Head all-wages total label.")
    manual(104, 541, 567, (T,), "Exact Head all-wages total label.")
    manual(114, 1063, 1140, (T,), "Exact Wife all-work total question label.")
    manual(114, 1333, 1359, (T,), "Exact Wife total-earnings printed label.")
    manual(
        115, 606, 1013, (C,), "Complete G51-52 work-income linkage context."
    )
    manual(115, 743, 764, (T,), "Exact Wife all-work-sources total label.")

    # Narrow K/L lifetime-work and work-history scope.  Objective prose that
    # merely mentions jobs or occupations is context/purpose, not a job slot.
    manual(167, 1660, 1725, (C, P), "K44 lifetime-work objective line.")
    manual(167, 1778, 1782, (R,), "Exact New-Wife role atom.")
    manual(167, 1783, 1789, (R,), "Exact quoted-Wife role atom.")
    manual(167, 1938, 1988, (C, P), "Complete K45 full-time-work objective.")

    manual(172, 2193, 2287, (C, P), "Complete K44 lifetime-work question.")
    manual(172, 2237, 2241, (R,), "Exact Wife role atom in K44.")
    manual(172, 2243, 2249, (R,), "Exact quoted-Wife role atom in K44.")
    manual(172, 2356, 2424, (C,), "K45 full-time-work question context.")
    manual(172, 2356, 2466, (P,), "Complete K45 full-time-work prompt.")

    manual(
        174, 928, 1481, (C, P), "Complete L6 occupation-continuity objective."
    )
    manual(
        175, 475, 970, (C,), "Complete L11-12 job-mobility objective context."
    )

    manual(176, 2161, 2243, (C, P), "Complete L5 first-regular-job question.")
    manual(176, 2215, 2224, (J,), "Exact L5 first regular-job anchor.")
    manual(176, 2247, 2477, (P,), "L6 occupation-continuity question body.")
    manual(176, 2477, 2533, (C, P), "L6 final occupation-continuity clause.")

    manual(177, 1472, 1601, (P,), "Complete L11 move-for-job question.")
    manual(177, 1677, 1762, (P,), "Complete L12 declined-job question.")

    manual(181, 2294, 2385, (C, P), "Complete L57 lifetime-work question.")
    manual(181, 2456, 2562, (C, P), "Complete L58 full-time-work question.")

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
            "whole_page_review": "all_181_pages_including_empty_occurrence_pages",
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
