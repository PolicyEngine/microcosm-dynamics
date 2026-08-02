#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 52.

The helper encodes the completed whole-document review as reviewer-approved
source windows, explicit corrections, and exact UTF-8 spans.  It never opens
the stage-1 candidate artifact.  Direct lexical detection is used only inside
the source regions that survived semantic review; the annotation builder joins
the resulting sealed review to candidates afterward.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_052_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]


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

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        page_bytes = page_texts[page - 1].encode("utf-8")
        while start < end and page_bytes[start : start + 1] in b" \t\r\n":
            start += 1
        while end > start and page_bytes[end - 1 : end] in b" \t\r\n":
            end -= 1
        if start >= end:
            raise ValueError(f"empty span after trimming: page={page}")
        return start, end

    def full_pages(
        *ranges: tuple[int, int]
    ) -> dict[int, tuple[tuple[int, int], ...]]:
        return {
            page: ((0, page_size(page)),)
            for first, last in ranges
            for page in range(first, last + 1)
        }

    # Every omitted byte on every one of the 289 pages was reviewed.  These
    # are the only semantic regions in which any R_Q occurrence survived.
    source_windows: dict[int, tuple[tuple[int, int], ...]] = {
        **full_pages((22, 30), (32, 77)),
        79: ((152, 676),),
        84: ((313, 3539),),
        85: ((29, 2126),),
        86: ((308, 3527),),
        87: ((99, 1474),),
        88: ((3, 3736),),
        89: ((112, 3873),),
        90: ((3, 3698),),
        91: ((100, 708),),
        92: ((120, 2626),),
        93: ((105, 3364),),
        94: ((3, 442),),
        95: ((100, 242),),
        106: ((202, 2197),),
        107: ((101, 992),),
        114: ((56, 2607),),
        115: ((108, 1719),),
        116: ((1, 2919),),
        117: ((101, 996),),
        118: ((894, 945), (1992, 2108), (2483, 2840)),
        119: ((1974, 2132), (2892, 3051)),
        120: ((993, 1044), (1866, 1982), (2370, 2745)),
        121: ((829, 926),),
        122: ((1326, 5310),),
        123: ((649, 1729),),
        125: ((98, 225),),
        126: ((2559, 2836),),
        127: ((257, 304),),
        128: ((208, 324), (877, 2843)),
        129: ((101, 881),),
        130: ((2301, 2565),),
        131: ((100, 238),),
        232: ((212, 1549),),
        233: ((98, 888),),
        266: ((426, 520), (951, 1070), (1115, 1186)),
        278: ((1047, 1368),),
        279: ((550, 930),),
        280: ((445, 477), (566, 619), (1419, 2249)),
        281: ((1282, 1960),),
        282: ((746, 1015),),
        283: ((341, 817), (1042, 1306)),
    }
    out_of_scope_pages = frozenset(range(118, 132))
    for page in out_of_scope_pages:
        source_windows.pop(page, None)

    def inside(page: int, start: int, end: int) -> bool:
        return any(
            window_start <= start < end <= window_end
            for window_start, window_end in source_windows.get(page, ())
        )

    specs: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    def add(
        page: int,
        start: int,
        end: int,
        kind: str,
        routes: Sequence[Sequence[tuple[int, int, int]]] = ((),),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        start, end = trim_span(page, start, end)
        key = (page, start, end, kind)
        route_set = {tuple(route) for route in routes}
        current = specs.get(key)
        if current is None:
            specs[key] = {
                "page": page,
                "start": start,
                "end": end,
                "kind": kind,
                "routes": route_set,
                "note": note,
            }
        else:
            current["routes"].update(route_set)

    # Replacements remove detector fragments of the same kind that overlap an
    # independently reviewed complete source atom.
    replacements: list[tuple[int, int, int, str, str]] = [
        (
            22,
            74,
            293,
            "field_purpose_prompt",
            "Complete B1 objective and response/skip block.",
        ),
        (
            22,
            245,
            293,
            "flow_branch_label",
            "Complete B1 skip condition, including its physical-line continuation.",
        ),
        (
            22,
            798,
            899,
            "field_purpose_prompt",
            "Complete B2 retirement-year prompt.",
        ),
        (
            22,
            903,
            1161,
            "field_purpose_prompt",
            "Complete B3 current-activity prompt.",
        ),
        (
            24,
            1278,
            1410,
            "context_anchor",
            "Complete B4c employment-context question across its line break.",
        ),
        (
            24,
            1278,
            1410,
            "field_purpose_prompt",
            "Complete B4c employment-status objective across its line break.",
        ),
        (
            24,
            1302,
            1318,
            "repeat_or_alias_instruction",
            "Atomic B4b title-fill cross-reference.",
        ),
        (
            27,
            1162,
            1187,
            "repeat_or_alias_instruction",
            "Atomic repeat-B10-if-necessary instruction.",
        ),
        (
            23,
            270,
            438,
            "repeat_or_alias_instruction",
            "Explicit Sections B/C to D/E parallel-instruction cross-reference.",
        ),
        (
            79,
            152,
            247,
            "field_purpose_prompt",
            "Complete rented-room work-boundary objective.",
        ),
        (
            79,
            160,
            203,
            "flow_branch_label",
            "Roomer-or-boarder condition.",
        ),
        (
            79,
            321,
            350,
            "context_anchor",
            "Income-producing-work boundary.",
        ),
        (
            79,
            346,
            454,
            "repeat_or_alias_instruction",
            "Complete work-income Section B/C or D/E cross-reference block.",
        ),
        (
            79,
            456,
            491,
            "flow_branch_label",
            "Unable-to-separate nested condition.",
        ),
        (
            79,
            598,
            676,
            "context_anchor",
            "Housework exclusion boundary for family-unit members.",
        ),
        (
            278,
            1047,
            1135,
            "context_anchor",
            "Complete K44 work-years question.",
        ),
        (
            278,
            1047,
            1135,
            "field_purpose_prompt",
            "Complete K44 work-years question.",
        ),
        (
            278,
            1143,
            1159,
            "flow_branch_label",
            "Reported-years continuation branch.",
        ),
        (
            278,
            1184,
            1228,
            "flow_branch_label",
            "No-work-years terminal branch.",
        ),
        (
            278,
            1239,
            1333,
            "context_anchor",
            "Complete K45 full-time-work question.",
        ),
        (
            278,
            1239,
            1333,
            "field_purpose_prompt",
            "Complete K45 full-time-work question.",
        ),
        (
            279,
            550,
            643,
            "context_anchor",
            "Complete K44 work-for-money clarification.",
        ),
        (
            279,
            550,
            643,
            "field_purpose_prompt",
            "Complete K44 work-for-money clarification.",
        ),
        (
            279,
            654,
            737,
            "context_anchor",
            "Complete Wife work-history clarification.",
        ),
        (
            279,
            748,
            834,
            "context_anchor",
            "Complete year-count interpretation.",
        ),
        (279, 845, 868, "context_anchor", "Explicit school-year exclusion."),
        (
            279,
            871,
            929,
            "context_anchor",
            "Complete K45 full-time interpretation.",
        ),
        (
            279,
            871,
            929,
            "field_purpose_prompt",
            "Complete K45 full-time interpretation.",
        ),
        (
            280,
            1419,
            1519,
            "context_anchor",
            "Complete L4 father-occupation question.",
        ),
        (
            280,
            1419,
            1519,
            "field_purpose_prompt",
            "Complete L4 father-occupation question.",
        ),
        (280, 1523, 1598, "context_anchor", "Complete L5 first-job question."),
        (
            280,
            1523,
            1598,
            "field_purpose_prompt",
            "Complete L5 first-job question.",
        ),
        (
            282,
            746,
            862,
            "context_anchor",
            "Complete L11 move-for-job question.",
        ),
        (
            282,
            746,
            862,
            "field_purpose_prompt",
            "Complete L11 move-for-job question.",
        ),
        (
            282,
            937,
            1014,
            "context_anchor",
            "Complete L12 job-refusal question.",
        ),
        (
            282,
            937,
            1014,
            "field_purpose_prompt",
            "Complete L12 job-refusal question.",
        ),
        (
            84,
            2362,
            2407,
            "repeat_or_alias_instruction",
            "G9b earlier-work cross-reference.",
        ),
        (
            84,
            3138,
            3218,
            "repeat_or_alias_instruction",
            "G9d earlier-work cross-reference.",
        ),
        (
            85,
            505,
            590,
            "context_anchor",
            "Complete G1a occupation-to-farm classification context.",
        ),
        (
            85,
            505,
            590,
            "field_purpose_prompt",
            "Complete G1a occupation-to-farm classification purpose.",
        ),
        (
            85,
            608,
            800,
            "repeat_or_alias_instruction",
            "Exact Section D/E to G4 cross-reference.",
        ),
        (
            86,
            2359,
            2404,
            "repeat_or_alias_instruction",
            "G9b earlier-work cross-reference.",
        ),
        (
            86,
            3167,
            3212,
            "repeat_or_alias_instruction",
            "G9d earlier-work cross-reference.",
        ),
        (
            87,
            588,
            628,
            "flow_branch_label",
            "Multiple-business repeat condition.",
        ),
        (
            87,
            644,
            705,
            "repeat_or_alias_instruction",
            "Repeat G7a-G11b for each business.",
        ),
        (87, 1062, 1090, "flow_branch_label", "Head-work-time condition."),
        (
            87,
            1232,
            1275,
            "flow_branch_label",
            "Unreported-business-hours condition.",
        ),
        (
            94,
            193,
            300,
            "field_purpose_prompt",
            "Complete G23 extra-job earnings inclusion question.",
        ),
        (
            94,
            330,
            388,
            "field_purpose_prompt",
            "Complete G24 extra-job earnings amount question.",
        ),
        (
            95,
            179,
            241,
            "context_anchor",
            "Complete extra-job hours-to-income purpose context.",
        ),
        (
            95,
            100,
            241,
            "field_purpose_prompt",
            "Complete extra-job hours-to-income purpose.",
        ),
        (107, 201, 245, "role_total_anchor", "Wife all-work-sources total."),
        (
            107,
            317,
            432,
            "flow_branch_label",
            "Wife business-income inclusion condition.",
        ),
        (
            107,
            434,
            559,
            "repeat_or_alias_instruction",
            "Business-income inclusion cross-reference.",
        ),
        (
            119,
            2892,
            3008,
            "flow_branch_label",
            "Multiple-OFUM booklet condition.",
        ),
        (
            119,
            3009,
            3050,
            "repeat_or_alias_instruction",
            "One booklet for each additional OFUM.",
        ),
        (
            121,
            866,
            924,
            "flow_branch_label",
            "Each-eligible-OFUM booklet condition.",
        ),
        (
            121,
            829,
            926,
            "repeat_or_alias_instruction",
            "Repeat a booklet for each eligible OFUM.",
        ),
        (
            123,
            1282,
            1380,
            "context_anchor",
            "Complete per-job income context.",
        ),
        (
            123,
            1282,
            1380,
            "field_purpose_prompt",
            "Complete per-job income purpose.",
        ),
        (
            123,
            1553,
            1612,
            "flow_branch_label",
            "Irregular-employment hours condition.",
        ),
        (
            126,
            2559,
            2793,
            "flow_branch_label",
            "Additional-OFUM booklet condition.",
        ),
        (
            126,
            2559,
            2793,
            "repeat_or_alias_instruction",
            "Another booklet for each additional OFUM.",
        ),
        (126, 2806, 2883, "flow_branch_label", "All-other-OFUM route."),
        (
            127,
            257,
            304,
            "repeat_or_alias_instruction",
            "One booklet for each eligible OFUM.",
        ),
        (
            129,
            101,
            469,
            "field_purpose_prompt",
            "Complete younger-OFUM work-income purpose.",
        ),
        (130, 2371, 2403, "flow_branch_label", "More-persons-listed branch."),
        (130, 2446, 2456, "flow_branch_label", "All-others branch."),
        (
            130,
            2461,
            2517,
            "repeat_or_alias_instruction",
            "Younger-OFUM work-supplement cross-reference.",
        ),
        (
            131,
            100,
            238,
            "context_anchor",
            "Complete labor-income total-hours context.",
        ),
        (
            131,
            100,
            238,
            "field_purpose_prompt",
            "Complete labor-income total-hours purpose.",
        ),
        (232, 212, 276, "flow_branch_label", "No-help-items terminal branch."),
        (232, 334, 348, "flow_branch_label", "P9-P10 all-other-cases branch."),
        (
            232,
            357,
            378,
            "context_anchor",
            "Physical-line continuation of the no-help-items condition.",
        ),
        (232, 395, 404, "flow_branch_label", "No-help-items route to P11."),
        (
            232,
            480,
            802,
            "field_purpose_prompt",
            "Complete Head help-to-work-hours purpose.",
        ),
        (
            232,
            661,
            802,
            "context_anchor",
            "Head paid-job work-hours source block.",
        ),
        (
            232,
            894,
            951,
            "context_anchor",
            "Head work-hours response alternatives.",
        ),
        (232, 1091, 1112, "flow_branch_label", "Wife-in-family branch."),
        (232, 1120, 1146, "flow_branch_label", "No-wife terminal branch."),
        (
            232,
            1229,
            1392,
            "field_purpose_prompt",
            "Complete Wife help-to-work-hours purpose.",
        ),
        (
            232,
            1324,
            1392,
            "context_anchor",
            "Wife paid-job work-hours source block.",
        ),
        (
            232,
            1495,
            1549,
            "context_anchor",
            "Wife work-hours response alternatives.",
        ),
        (233, 487, 573, "context_anchor", "P8 work-hours routing context."),
        (
            233,
            613,
            820,
            "context_anchor",
            "Complete P9 work-hours purpose context.",
        ),
        (
            233,
            613,
            820,
            "field_purpose_prompt",
            "Complete P9 work-hours purpose.",
        ),
        (
            233,
            823,
            887,
            "repeat_or_alias_instruction",
            "P10 is explicitly equivalent to P9 for Wife.",
        ),
        (266, 426, 440, "flow_branch_label", "New-Wife Section K branch."),
        (266, 453, 468, "flow_branch_label", "Same-Wife terminal branch."),
        (266, 485, 502, "flow_branch_label", "Wife Section K branch."),
        (266, 506, 519, "flow_branch_label", "No-Wife terminal branch."),
        (280, 445, 456, "flow_branch_label", "New-Head Section L branch."),
        (280, 464, 476, "flow_branch_label", "Same-Head terminal branch."),
        (
            280,
            1684,
            1880,
            "flow_branch_label",
            "Never-worked terminal route to L7.",
        ),
        (
            280,
            1882,
            2015,
            "context_anchor",
            "Complete L6 job-history question.",
        ),
        (
            280,
            1882,
            2015,
            "field_purpose_prompt",
            "Complete L6 job-history question.",
        ),
        (
            280,
            2187,
            2248,
            "context_anchor",
            "L6 job-history response alternatives.",
        ),
        (
            281,
            1282,
            1445,
            "context_anchor",
            "Complete L4-L5 occupation and job-purpose explanation.",
        ),
        (
            281,
            1282,
            1445,
            "field_purpose_prompt",
            "Complete L4-L5 occupation and job-purpose explanation.",
        ),
        (
            281,
            1556,
            1642,
            "context_anchor",
            "New-Head career-similarity context.",
        ),
        (
            281,
            1654,
            1740,
            "field_purpose_prompt",
            "Occupational-similarity collection purpose.",
        ),
        (
            281,
            1752,
            1835,
            "context_anchor",
            "Full-time versus school-job boundary.",
        ),
        (
            281,
            1847,
            1959,
            "context_anchor",
            "Labor-force continuity boundary.",
        ),
        (
            283,
            341,
            816,
            "context_anchor",
            "Complete L11-L12 job-mobility interpretation.",
        ),
        (
            283,
            341,
            816,
            "field_purpose_prompt",
            "Complete L11-L12 job-mobility purpose.",
        ),
        (
            283,
            1042,
            1305,
            "field_purpose_prompt",
            "Section L duplicates Section K for New Head.",
        ),
        (
            283,
            1042,
            1305,
            "repeat_or_alias_instruction",
            "Explicit Section L duplication of Section K.",
        ),
        (282, 898, 926, "flow_branch_label", "L11 yes-to-L13 terminal route."),
        (
            25,
            102,
            509,
            "repeat_or_alias_instruction",
            "B4-B59 main-job scope and B82 cross-reference.",
        ),
        (
            35,
            104,
            462,
            "repeat_or_alias_instruction",
            "B12-B19 regular-versus-overtime scope.",
        ),
        (
            39,
            1013,
            1098,
            "repeat_or_alias_instruction",
            "Same-employer spells total-altogether instruction.",
        ),
        (
            41,
            1351,
            1759,
            "repeat_or_alias_instruction",
            "B23-B24 present-employer scope.",
        ),
        (
            43,
            100,
            172,
            "repeat_or_alias_instruction",
            "B35-B36 cross-reference to B9-B9a.",
        ),
        (
            43,
            1893,
            2049,
            "repeat_or_alias_instruction",
            "B41-B41c cross-reference to B9-B11.",
        ),
        (
            43,
            2050,
            2198,
            "repeat_or_alias_instruction",
            "B42 cross-reference to B39.",
        ),
        (
            47,
            199,
            231,
            "repeat_or_alias_instruction",
            "B45b cross-reference to B38.",
        ),
        (
            47,
            232,
            402,
            "repeat_or_alias_instruction",
            "B46-B47 cross-reference to B25-B29.",
        ),
        (
            47,
            677,
            711,
            "repeat_or_alias_instruction",
            "B49-B49a cross-reference to B9-B9a.",
        ),
        (
            49,
            94,
            125,
            "repeat_or_alias_instruction",
            "B52 cross-reference to B38.",
        ),
        (
            49,
            835,
            866,
            "repeat_or_alias_instruction",
            "B57a cross-reference to B38.",
        ),
        (
            51,
            132,
            482,
            "repeat_or_alias_instruction",
            "One Work History Supplement per additional employer.",
        ),
        (
            51,
            484,
            871,
            "repeat_or_alias_instruction",
            "WHS section invocation and questionnaire-return mapping.",
        ),
        (
            51,
            1629,
            1787,
            "repeat_or_alias_instruction",
            "S41-S41c cross-reference to B9-B11.",
        ),
        (
            51,
            1788,
            1818,
            "repeat_or_alias_instruction",
            "S42 cross-reference to B39.",
        ),
        (
            52,
            31,
            280,
            "repeat_or_alias_instruction",
            "S42a checkpoint cross-references B/C/D/E and supplements.",
        ),
        (
            52,
            821,
            1400,
            "repeat_or_alias_instruction",
            "Explicit current-job to extra-job local reference.",
        ),
        (
            53,
            45,
            83,
            "repeat_or_alias_instruction",
            "S42a-S42d cross-reference to B42a-B42d.",
        ),
        (
            53,
            85,
            120,
            "repeat_or_alias_instruction",
            "S43-S44 cross-reference to B4-B5.",
        ),
        (
            55,
            87,
            119,
            "repeat_or_alias_instruction",
            "S45b cross-reference to B38.",
        ),
        (
            55,
            120,
            309,
            "repeat_or_alias_instruction",
            "S46-S47 cross-reference to B25-B29.",
        ),
        (
            55,
            310,
            345,
            "repeat_or_alias_instruction",
            "S49-S49a cross-reference to B9-B9a.",
        ),
        (
            57,
            90,
            118,
            "repeat_or_alias_instruction",
            "S52 cross-reference to B38.",
        ),
        (
            57,
            119,
            152,
            "repeat_or_alias_instruction",
            "S53-S55 cross-reference to B53-B55.",
        ),
        (
            57,
            153,
            182,
            "repeat_or_alias_instruction",
            "S57a cross-reference to B38.",
        ),
        (
            57,
            183,
            347,
            "repeat_or_alias_instruction",
            "One WHS per employer and return instruction.",
        ),
        (
            67,
            100,
            121,
            "repeat_or_alias_instruction",
            "B86 cross-reference to B11 QxQ.",
        ),
        (
            67,
            852,
            965,
            "repeat_or_alias_instruction",
            "B94-B105 repeats B82-B93.",
        ),
        (
            69,
            167,
            298,
            "repeat_or_alias_instruction",
            "Section C parallels Section B.",
        ),
        (
            69,
            338,
            372,
            "repeat_or_alias_instruction",
            "C2 cross-reference to B21.",
        ),
        (
            71,
            626,
            735,
            "repeat_or_alias_instruction",
            "Section C to Section B comparable-instruction mapping.",
        ),
        (
            71,
            736,
            950,
            "repeat_or_alias_instruction",
            "C9-C11 cross-reference to B9-B11.",
        ),
        (
            73,
            43,
            79,
            "repeat_or_alias_instruction",
            "C12-C14 cross-reference to B4-B5.",
        ),
        (
            73,
            80,
            110,
            "repeat_or_alias_instruction",
            "C14a cross-reference to B11.",
        ),
        (
            73,
            111,
            141,
            "repeat_or_alias_instruction",
            "C15 cross-reference to B55.",
        ),
        (
            75,
            102,
            439,
            "repeat_or_alias_instruction",
            "C16-C51 follows B24-B59.",
        ),
        (
            75,
            441,
            561,
            "repeat_or_alias_instruction",
            "C52-C98 parallels B60-B106.",
        ),
        (
            77,
            257,
            455,
            "repeat_or_alias_instruction",
            "Wife treatment equivalence in Sections D/E.",
        ),
        (
            77,
            589,
            862,
            "repeat_or_alias_instruction",
            "Sections D/E parallel B/C.",
        ),
        (77, 1030, 1154, "repeat_or_alias_instruction", "D1a parallels B1."),
        (
            77,
            1155,
            1400,
            "repeat_or_alias_instruction",
            "Section D parallels Section B.",
        ),
        (
            27,
            1635,
            1672,
            "flow_branch_label",
            "Road-construction-worker classification condition.",
        ),
        (
            27,
            1730,
            1777,
            "flow_branch_label",
            "Road-foreman supervision condition.",
        ),
        (
            27,
            1799,
            1847,
            "flow_branch_label",
            "Road-operative equipment condition.",
        ),
        (
            27,
            1852,
            1918,
            "flow_branch_label",
            "Road-laborer labor-only condition.",
        ),
        (
            39,
            586,
            706,
            "flow_branch_label",
            "Looked-at-advertisements probe condition.",
        ),
        (
            39,
            707,
            775,
            "flow_branch_label",
            "No-ad-placement recording condition.",
        ),
        (
            43,
            1415,
            1494,
            "flow_branch_label",
            "Present-employer start and B40-yes condition.",
        ),
        (
            43,
            1552,
            1588,
            "flow_branch_label",
            "Months-worked-for-both nested condition.",
        ),
        (
            63,
            1259,
            1394,
            "flow_branch_label",
            "Unemployed-looking-and-vacation condition.",
        ),
        (
            63,
            1400,
            1465,
            "flow_branch_label",
            "Earned-vacation-then-layoff condition.",
        ),
        (
            63,
            1466,
            1546,
            "flow_branch_label",
            "Earned-vacation allocation consequence.",
        ),
        (
            63,
            1547,
            1679,
            "flow_branch_label",
            "Permanent-layoff-first alternative.",
        ),
        (
            125,
            98,
            225,
            "context_anchor",
            "Explicit nonlabor-versus-work-income boundary.",
        ),
        (
            125,
            160,
            225,
            "repeat_or_alias_instruction",
            "Work income is explicitly cross-referenced to G78.",
        ),
        (84, 431, 466, "flow_branch_label", "Farmer-or-rancher branch."),
        (84, 489, 508, "flow_branch_label", "All-others route to G5."),
        (84, 583, 591, "flow_branch_label", "Farmer branch continuation."),
        (
            84,
            1077,
            1223,
            "field_purpose_prompt",
            "Complete G5 business-ownership question.",
        ),
        (84, 1261, 1269, "flow_branch_label", "G5 yes branch."),
        (84, 1304, 1334, "flow_branch_label", "G5 no branch."),
        (
            84,
            2108,
            2175,
            "field_purpose_prompt",
            "Complete G9a Head work-time question.",
        ),
        (
            84,
            2206,
            2262,
            "flow_branch_label",
            "G9a inconsistency-probe condition.",
        ),
        (84, 2277, 2287, "flow_branch_label", "G9a yes branch."),
        (84, 2301, 2328, "flow_branch_label", "G9a no branch."),
        (84, 2624, 2634, "flow_branch_label", "G9b reported-hours branch."),
        (84, 2658, 2687, "flow_branch_label", "G9b unreported-hours branch."),
        (84, 2795, 2814, "flow_branch_label", "Wife-in-family branch."),
        (84, 2822, 2837, "flow_branch_label", "All-others branch."),
        (84, 3054, 3062, "flow_branch_label", "G9c yes branch."),
        (84, 3080, 3110, "flow_branch_label", "G9c no branch."),
        (84, 3471, 3485, "flow_branch_label", "G9d reported-hours branch."),
        (84, 3509, 3538, "flow_branch_label", "G9d unreported-hours branch."),
        (
            85,
            36,
            91,
            "flow_branch_label",
            "Work-income requires employment-section hours.",
        ),
        (
            85,
            162,
            254,
            "context_anchor",
            "Employment hours require Section G income.",
        ),
        (
            85,
            169,
            246,
            "flow_branch_label",
            "Employment-hours-to-income condition.",
        ),
        (85, 608, 664, "flow_branch_label", "Wife farm-owner work condition."),
        (86, 418, 452, "flow_branch_label", "Farmer-or-rancher branch."),
        (86, 472, 491, "flow_branch_label", "All-others route to G5."),
        (86, 562, 570, "flow_branch_label", "Farmer branch continuation."),
        (
            86,
            1055,
            1199,
            "field_purpose_prompt",
            "Complete G5 business-ownership question.",
        ),
        (86, 1231, 1239, "flow_branch_label", "G5 yes branch."),
        (86, 1278, 1308, "flow_branch_label", "G5 no branch."),
        (
            86,
            2056,
            2123,
            "field_purpose_prompt",
            "Complete G9a Head work-time question.",
        ),
        (
            86,
            2152,
            2208,
            "flow_branch_label",
            "G9a inconsistency-probe condition.",
        ),
        (86, 2222, 2232, "flow_branch_label", "G9a yes branch."),
        (86, 2243, 2272, "flow_branch_label", "G9a no branch."),
        (86, 2609, 2619, "flow_branch_label", "G9b reported-hours branch."),
        (86, 2643, 2672, "flow_branch_label", "G9b unreported-hours branch."),
        (86, 2777, 2796, "flow_branch_label", "Wife-in-family branch."),
        (86, 2804, 2853, "flow_branch_label", "All-others branch."),
        (86, 3060, 3068, "flow_branch_label", "G9c yes branch."),
        (86, 3086, 3116, "flow_branch_label", "G9c no branch."),
        (86, 3455, 3469, "flow_branch_label", "G9d reported-hours branch."),
        (86, 3497, 3526, "flow_branch_label", "G9d unreported-hours branch."),
        (
            87,
            223,
            271,
            "flow_branch_label",
            "Missing-income-or-hours callback condition.",
        ),
        (87, 343, 435, "field_purpose_prompt", "G5-G7a owned-business scope."),
        (
            87,
            820,
            825,
            "flow_branch_label",
            "Self-employed no-business condition.",
        ),
        (
            87,
            1019,
            1113,
            "field_purpose_prompt",
            "Head work-time reporting purpose.",
        ),
        (88, 621, 630, "flow_branch_label", "G11 profit branch."),
        (
            88,
            633,
            691,
            "field_purpose_prompt",
            "Complete G11a income-share question.",
        ),
        (88, 712, 737, "field_purpose_prompt", "Complete G11b loss question."),
        (
            88,
            955,
            963,
            "field_purpose_prompt",
            "Complete G11a left-in amount question.",
        ),
        (
            88,
            1034,
            1042,
            "field_purpose_prompt",
            "Complete G11b year question.",
        ),
        (88, 1272, 1289, "flow_branch_label", "Only-one-business branch."),
        (
            88,
            1311,
            1410,
            "flow_branch_label",
            "Two-or-more-businesses branch.",
        ),
        (
            88,
            1586,
            1735,
            "field_purpose_prompt",
            "Complete G12 wage-and-salary question.",
        ),
        (
            88,
            1737,
            1866,
            "flow_branch_label",
            "G12 unincorporated-business exclusion condition.",
        ),
        (
            88,
            2021,
            2058,
            "field_purpose_prompt",
            "Complete G13 total-wages question.",
        ),
        (
            88,
            2074,
            2113,
            "field_purpose_prompt",
            "Complete G16 supplementary-income question.",
        ),
        (
            88,
            2133,
            2157,
            "role_total_anchor",
            "Head total wages and salaries.",
        ),
        (
            88,
            2235,
            2261,
            "field_purpose_prompt",
            "Complete G13 1993-salary purpose.",
        ),
        (
            88,
            2290,
            2303,
            "field_purpose_prompt",
            "Complete G16 commissions purpose.",
        ),
        (88, 2639, 2649, "flow_branch_label", "G16a branch."),
        (88, 2654, 2668, "flow_branch_label", "G16 no-income route."),
        (88, 2881, 2891, "flow_branch_label", "G14 yes branch."),
        (88, 2899, 2909, "flow_branch_label", "G14 no branch."),
        (
            89,
            131,
            167,
            "flow_branch_label",
            "G10 don't-know response condition.",
        ),
        (
            89,
            187,
            306,
            "flow_branch_label",
            "Unknown-incorporation recording condition.",
        ),
        (89, 475, 484, "flow_branch_label", "Corrected G11 Code 3 skip."),
        (
            89,
            550,
            655,
            "field_purpose_prompt",
            "G11a net-profit interpretation.",
        ),
        (
            89,
            685,
            762,
            "flow_branch_label",
            "Draw-and-profit split condition.",
        ),
        (
            89,
            972,
            1107,
            "flow_branch_label",
            "Nonowner Wife wage exclusion condition.",
        ),
        (
            89,
            1237,
            1303,
            "flow_branch_label",
            "Part-owner separate-share condition.",
        ),
        (89, 1457, 1509, "flow_branch_label", "Only-total-known condition."),
        (
            89,
            1940,
            1988,
            "flow_branch_label",
            "Missing-income-or-hours callback condition.",
        ),
        (
            89,
            2069,
            2096,
            "flow_branch_label",
            "Head-worked-in-1993 condition.",
        ),
        (
            89,
            2633,
            2662,
            "flow_branch_label",
            "Extra-jobs inclusion condition.",
        ),
        (89, 3068, 3100, "flow_branch_label", "Fixed-salary condition."),
        (
            89,
            3428,
            3511,
            "flow_branch_label",
            "Complicated-work-history condition.",
        ),
        (90, 531, 540, "flow_branch_label", "G11 profit branch."),
        (
            90,
            543,
            601,
            "field_purpose_prompt",
            "Complete G11a income-share question.",
        ),
        (90, 626, 651, "field_purpose_prompt", "Complete G11b loss question."),
        (
            90,
            877,
            885,
            "field_purpose_prompt",
            "Complete G11a left-in amount question.",
        ),
        (90, 960, 968, "field_purpose_prompt", "Complete G11b year question."),
        (90, 1215, 1232, "flow_branch_label", "Only-one-business branch."),
        (
            90,
            1254,
            1357,
            "flow_branch_label",
            "Two-or-more-businesses branch.",
        ),
        (
            90,
            1450,
            1599,
            "field_purpose_prompt",
            "Complete G12 wage-and-salary question.",
        ),
        (
            90,
            1601,
            1730,
            "flow_branch_label",
            "G12 unincorporated-business exclusion condition.",
        ),
        (
            90,
            1885,
            1922,
            "field_purpose_prompt",
            "Complete G13 total-wages question.",
        ),
        (
            90,
            1939,
            1981,
            "field_purpose_prompt",
            "Complete G16 supplementary-income question.",
        ),
        (
            90,
            2001,
            2025,
            "role_total_anchor",
            "Head total wages and salaries.",
        ),
        (
            90,
            2107,
            2133,
            "field_purpose_prompt",
            "Complete G13 1993-salary purpose.",
        ),
        (
            90,
            2166,
            2178,
            "field_purpose_prompt",
            "Complete G16 commissions purpose.",
        ),
        (90, 2527, 2537, "flow_branch_label", "G16a branch."),
        (90, 2543, 2557, "flow_branch_label", "G16 no-income route."),
        (90, 2814, 2824, "flow_branch_label", "G14 yes branch."),
        (90, 2833, 2843, "flow_branch_label", "G14 no branch."),
        (
            91,
            274,
            362,
            "flow_branch_label",
            "Already-included-income condition.",
        ),
        (
            91,
            396,
            462,
            "flow_branch_label",
            "Earnings-only-from-supplements condition.",
        ),
        (
            91,
            481,
            573,
            "field_purpose_prompt",
            "Job-Supplement hours-reporting purpose.",
        ),
        (91, 489, 586, "flow_branch_label", "Missing-work-hours condition."),
        (
            92,
            120,
            290,
            "field_purpose_prompt",
            "Complete G18 professional-practice question.",
        ),
        (
            92,
            987,
            1135,
            "field_purpose_prompt",
            "Complete G18b farming-income question.",
        ),
        (
            92,
            1484,
            1568,
            "context_anchor",
            "Farm-income work-hours reporting context.",
        ),
        (
            92,
            1771,
            1944,
            "field_purpose_prompt",
            "Complete G18c roomer-or-boarder question.",
        ),
        (92, 1862, 1942, "context_anchor", "Roomer work-for-income boundary."),
        (
            93,
            683,
            771,
            "field_purpose_prompt",
            "G18b farm-income interpretation purpose.",
        ),
        (93, 722, 770, "flow_branch_label", "Current-farming-job condition."),
        (
            93,
            857,
            918,
            "flow_branch_label",
            "Nonfarming-current-job condition.",
        ),
        (
            93,
            1122,
            1169,
            "flow_branch_label",
            "Missing-income-or-hours callback condition.",
        ),
        (
            93,
            1235,
            1314,
            "context_anchor",
            "Roomer-or-boarder income context.",
        ),
        (
            93,
            1235,
            1314,
            "field_purpose_prompt",
            "Roomer-or-boarder income purpose.",
        ),
        (
            93,
            1566,
            1616,
            "flow_branch_label",
            "Work-required roomer-income condition.",
        ),
        (
            93,
            1675,
            1694,
            "flow_branch_label",
            "No-work rent-income condition.",
        ),
        (
            93,
            1873,
            1918,
            "flow_branch_label",
            "Inseparable-food-cost condition.",
        ),
        (
            93,
            2350,
            2391,
            "flow_branch_label",
            "Parent room-and-board payment condition.",
        ),
        (93, 2446, 2466, "flow_branch_label", "Rent-only alternative."),
        (
            93,
            2488,
            2587,
            "field_purpose_prompt",
            "G19 amount-and-unit purpose.",
        ),
        (
            93,
            2746,
            2837,
            "field_purpose_prompt",
            "G20 months-received purpose.",
        ),
        (
            93,
            2987,
            3363,
            "field_purpose_prompt",
            "G21 work-hours cross-check purpose.",
        ),
        (
            93,
            2987,
            3363,
            "repeat_or_alias_instruction",
            "Complete G21 Section B/C work-hours cross-reference.",
        ),
        (
            93,
            3099,
            3160,
            "flow_branch_label",
            "Missing-reported-hours condition.",
        ),
        (
            93,
            3206,
            3284,
            "flow_branch_label",
            "Late-discovered-missing-hours condition.",
        ),
        (94, 114, 137, "flow_branch_label", "Extra-job branch."),
        (94, 153, 184, "flow_branch_label", "All-others route."),
        (95, 167, 211, "flow_branch_label", "Head extra-job-hours condition."),
        (106, 204, 228, "flow_branch_label", "Wife-in-family branch."),
        (106, 254, 269, "flow_branch_label", "All-others branch."),
        (106, 280, 302, "flow_branch_label", "All-others route."),
        (106, 640, 666, "flow_branch_label", "Wife-worked-in-1993 branch."),
        (106, 685, 698, "flow_branch_label", "All-others route to G52c."),
        (106, 790, 800, "flow_branch_label", "G51b continuation branch."),
        (
            106,
            841,
            1094,
            "field_purpose_prompt",
            "Complete G51b Wife work-earnings question.",
        ),
        (
            106,
            1757,
            1794,
            "context_anchor",
            "Reported work-hours branch context.",
        ),
        (
            106,
            1809,
            1852,
            "context_anchor",
            "Unreported work-hours branch context.",
        ),
        (
            106,
            2061,
            2073,
            "flow_branch_label",
            "Wife-income-last-year branch.",
        ),
        (106, 2107, 2119, "flow_branch_label", "No-wife-income branch."),
        (106, 2134, 2148, "flow_branch_label", "Continue-to-G53 branch."),
        (106, 2178, 2196, "flow_branch_label", "All-others route to G64."),
        (
            107,
            434,
            492,
            "flow_branch_label",
            "Wife business-owner income condition.",
        ),
        (
            107,
            589,
            597,
            "flow_branch_label",
            "Known-business-income amount condition.",
        ),
        (
            107,
            859,
            991,
            "field_purpose_prompt",
            "Complete Job Supplement hours-reporting purpose.",
        ),
        (
            107,
            875,
            945,
            "flow_branch_label",
            "Unreported-work-hours condition.",
        ),
        (
            114,
            845,
            862,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            893,
            922,
            "field_purpose_prompt",
            "Complete GJ0b supplement-type prompt.",
        ),
        (
            114,
            935,
            950,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            963,
            982,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            1044,
            1061,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            1127,
            1142,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            1155,
            1161,
            "field_purpose_prompt",
            "GJ1 business-work prompt part.",
        ),
        (
            114,
            2087,
            2153,
            "field_purpose_prompt",
            "Complete GJ2 employer-name question.",
        ),
        (
            114,
            2154,
            2339,
            "flow_branch_label",
            "Employer-name assurance condition.",
        ),
        (
            114,
            2341,
            2454,
            "flow_branch_label",
            "No-employer-name recording condition.",
        ),
        (
            115,
            434,
            470,
            "flow_branch_label",
            "Unreported-work-hours supplement condition.",
        ),
        (
            115,
            801,
            883,
            "field_purpose_prompt",
            "GJ0a-GJ0b supplement-origin purpose.",
        ),
        (
            115,
            1213,
            1233,
            "repeat_or_alias_instruction",
            "GJ2 repeats B11 employer-name handling.",
        ),
        (
            115,
            1296,
            1339,
            "flow_branch_label",
            "Employer-name concern or refusal condition.",
        ),
        (
            115,
            1341,
            1415,
            "field_purpose_prompt",
            "GJ3-GJ3a occupation-probe purpose.",
        ),
        (
            115,
            1341,
            1415,
            "repeat_or_alias_instruction",
            "GJ3-GJ3a repeats B9-B11 probing.",
        ),
        (
            115,
            1677,
            1689,
            "flow_branch_label",
            "Service-station probe condition.",
        ),
        (
            116,
            89,
            153,
            "flow_branch_label",
            "Business-origin supplement branch.",
        ),
        (
            116,
            181,
            193,
            "flow_branch_label",
            "All-other supplement origins branch.",
        ),
        (116, 239, 248, "flow_branch_label", "Business-origin route to GJ4."),
        (116, 1206, 1278, "context_anchor", "Stopped-work question context."),
        (116, 1291, 1298, "flow_branch_label", "Stopped-work yes branch."),
        (116, 1306, 1315, "flow_branch_label", "Stopped-work no branch."),
        (116, 1327, 1337, "flow_branch_label", "No-stop route to GJ11."),
        (
            116,
            1432,
            1448,
            "flow_branch_label",
            "Volunteered-day recording condition.",
        ),
        (116, 2232, 2246, "flow_branch_label", "Return-to-G9b branch."),
        (116, 2258, 2272, "flow_branch_label", "Return-to-G9d branch."),
        (116, 2281, 2295, "flow_branch_label", "Return-to-G17e branch."),
        (116, 2342, 2356, "flow_branch_label", "Return-to-G52b branch."),
        (116, 2659, 2666, "flow_branch_label", "Return-to-G21a branch."),
        (116, 2673, 2680, "flow_branch_label", "Return-to-G21b branch."),
        (116, 2692, 2699, "flow_branch_label", "Return-to-G21c branch."),
        (
            117,
            101,
            221,
            "flow_branch_label",
            "Business-income supplement skip condition.",
        ),
        (
            117,
            101,
            199,
            "field_purpose_prompt",
            "GJ3ab supplement-routing purpose.",
        ),
        (
            117,
            222,
            256,
            "flow_branch_label",
            "All-other supplement-origin branch.",
        ),
        (117, 258, 349, "context_anchor", "GJ4 weeks-worked interpretation."),
        (
            117,
            817,
            917,
            "field_purpose_prompt",
            "GJ10 separation-reason purpose.",
        ),
        (118, 2778, 2808, "flow_branch_label", "OFUM-remains booklet branch."),
        (118, 2825, 2840, "flow_branch_label", "No-OFUM route."),
        (
            119,
            1997,
            2025,
            "flow_branch_label",
            "Moved-out-or-deceased OFUM retention condition.",
        ),
        (120, 2673, 2703, "flow_branch_label", "OFUM-remains booklet branch."),
        (120, 2729, 2744, "flow_branch_label", "No-OFUM route."),
        (
            122,
            1556,
            1864,
            "field_purpose_prompt",
            "Complete G75 employment-status question.",
        ),
        (
            122,
            3550,
            3665,
            "field_purpose_prompt",
            "Complete G76 job-count question.",
        ),
        (122, 3680, 3695, "flow_branch_label", "Only-one-job branch."),
        (122, 3731, 3742, "flow_branch_label", "Two-jobs branch."),
        (122, 3749, 3762, "flow_branch_label", "Three-jobs branch."),
        (122, 3773, 3789, "flow_branch_label", "Four-jobs branch."),
        (122, 3799, 3821, "flow_branch_label", "No-job terminal branch."),
        (122, 3959, 3973, "flow_branch_label", "No-job route to G83."),
        (
            122,
            4788,
            4999,
            "field_purpose_prompt",
            "Complete G81 weekly-hours question.",
        ),
        (122, 5094, 5116, "flow_branch_label", "Only-one-job G82 branch."),
        (122, 5180, 5190, "flow_branch_label", "All-other job counts branch."),
        (
            122,
            5216,
            5230,
            "flow_branch_label",
            "Only-one-job next-page route.",
        ),
        (
            122,
            5272,
            5309,
            "flow_branch_label",
            "Additional-job repeat branch.",
        ),
        (
            122,
            5272,
            5309,
            "repeat_or_alias_instruction",
            "Repeat G77-G81 for each additional job.",
        ),
        (
            123,
            880,
            921,
            "flow_branch_label",
            "Irregular-employment condition.",
        ),
        (
            123,
            1329,
            1372,
            "flow_branch_label",
            "Rate-versus-total-income condition.",
        ),
        (128, 180, 199, "flow_branch_label", "Young-OFUM branch."),
        (128, 208, 285, "flow_branch_label", "Age-15-or-younger branch."),
        (128, 286, 324, "flow_branch_label", "All-other OFUM branch."),
        (128, 410, 428, "flow_branch_label", "No-OFUM route."),
        (
            128,
            877,
            1031,
            "field_purpose_prompt",
            "Complete younger-member income question.",
        ),
        (128, 1124, 1155, "flow_branch_label", "No-income terminal branch."),
        (
            128,
            1386,
            1430,
            "field_purpose_prompt",
            "Complete work-income amount question.",
        ),
        (
            128,
            2244,
            2387,
            "field_purpose_prompt",
            "Complete occupation-and-work question.",
        ),
        (
            128,
            2586,
            2732,
            "context_anchor",
            "Complete weeks-and-hours work context.",
        ),
        (
            128,
            2586,
            2732,
            "field_purpose_prompt",
            "Complete weeks-and-hours work purpose.",
        ),
        (
            129,
            223,
            469,
            "context_anchor",
            "Younger-child work-income context.",
        ),
        (129, 366, 374, "job_anchor", "Odd-jobs source anchor."),
        (129, 602, 635, "flow_branch_label", "No-OFUM branch."),
        (129, 636, 739, "flow_branch_label", "Young-OFUM inclusion branch."),
        (
            130,
            2461,
            2517,
            "flow_branch_label",
            "More-persons supplement branch.",
        ),
        (130, 2550, 2564, "flow_branch_label", "All-others next-page route."),
        (88, 70, 84, "flow_branch_label", "Corporation branch."),
        (88, 95, 112, "flow_branch_label", "Unincorporated-business branch."),
        (88, 125, 144, "flow_branch_label", "Other-business-form branch."),
        (88, 343, 353, "flow_branch_label", "Profit branch."),
        (88, 407, 414, "flow_branch_label", "Loss branch."),
        (88, 510, 523, "flow_branch_label", "Broke-even branch."),
        (90, 70, 84, "flow_branch_label", "Corporation branch."),
        (90, 95, 112, "flow_branch_label", "Unincorporated-business branch."),
        (90, 126, 145, "flow_branch_label", "Other-business-form branch."),
        (90, 348, 359, "flow_branch_label", "Profit branch."),
        (90, 414, 432, "flow_branch_label", "Broke-even branch."),
        (
            122,
            1396,
            1432,
            "flow_branch_label",
            "Deceased-OFUM terminal branch.",
        ),
        (122, 1476, 1509, "flow_branch_label", "Not-deceased OFUM branch."),
        (128, 1362, 1378, "flow_branch_label", "Work-income source branch."),
    ]
    purpose_merges = [
        (24, 103, 201, "Complete B4 employment-status question."),
        (24, 594, 725, "Complete B4a two-job/self-employment alternative."),
        (24, 1569, 1592, "Pure B5 left-column physical-line prompt slice."),
        (24, 1664, 1683, "Pure B5 left-column physical-line prompt slice."),
        (24, 1609, 1658, "Pure B6 right-column physical-line prompt slice."),
        (24, 1704, 1749, "Pure B6 right-column physical-line prompt slice."),
        (27, 2298, 2978, "Complete occupation-probe example block."),
        (29, 1076, 1190, "Complete utilities-industry probe."),
        (29, 2377, 2494, "Complete engines-and-motors probe."),
        (29, 2502, 2625, "Complete textiles-and-clothing probe."),
        (30, 161, 371, "Complete oil-industry probe."),
        (33, 99, 617, "Complete B11 employer-name purpose block."),
        (34, 104, 202, "Complete B12 remuneration-type question."),
        (34, 1516, 1651, "Complete B19 extra-hour earnings question."),
        (38, 1001, 1104, "Complete B23 present-employer tenure question."),
        (40, 96, 289, "Complete repeated-employment start qualifier."),
        (71, 101, 625, "Complete C4-C8 work-history purpose block."),
        (40, 680, 701, "Pure B25 column prompt slice."),
        (40, 788, 806, "Pure B25 column prompt slice."),
        (40, 892, 904, "Pure B25 column prompt slice."),
        (40, 993, 1007, "Pure B25 column prompt slice."),
        (40, 1097, 1108, "Pure B25 column prompt slice."),
        (40, 715, 742, "Pure B30 column prompt slice."),
        (40, 823, 847, "Pure B30 column prompt slice."),
        (40, 927, 950, "Pure B30 column prompt slice."),
        (40, 1028, 1044, "Pure B30 column prompt slice."),
        (40, 753, 780, "Pure B31 column prompt slice."),
        (40, 866, 884, "Pure B31 column prompt slice."),
        (40, 970, 985, "Pure B31 column prompt slice."),
        (40, 1071, 1089, "Pure B31 column prompt slice."),
        (40, 1175, 1191, "Pure B31 column prompt slice."),
        (42, 111, 236, "Complete B35 occupation question."),
        (42, 572, 678, "Complete B39 months-worked question."),
        (42, 1100, 1209, "Complete B41 occupation question."),
        (42, 1213, 1417, "Complete B41a duties clarification."),
        (42, 1477, 1804, "Complete B41c employer/confidentiality block."),
        (42, 1808, 1938, "Complete B42 months-worked question."),
        (43, 173, 291, "Complete B38 present-employer hours objective."),
        (43, 292, 988, "Complete B39 months-worked objective block."),
        (43, 2050, 2198, "Complete B42 objective block."),
        (44, 1662, 1814, "Complete B43 employment-status question."),
        (44, 702, 1251, "Complete B58 source-record instruction."),
        (44, 1359, 1455, "Complete B42b overlap question."),
        (44, 1998, 2018, "Pure B44 left-column physical-line prompt slice."),
        (44, 2104, 2118, "Pure B44 left-column physical-line prompt slice."),
        (44, 2200, 2213, "Pure B44 left-column physical-line prompt slice."),
        (44, 2229, 2241, "Pure B44 left-column physical-line prompt slice."),
        (44, 2033, 2088, "Pure B45 right-column physical-line prompt slice."),
        (44, 2139, 2184, "Pure B45 right-column physical-line prompt slice."),
        (46, 462, 566, "Complete B46 position-change question."),
        (46, 685, 799, "Complete B47 position-change-type question."),
        (46, 1398, 1534, "Complete B49 occupation question."),
        (48, 941, 1092, "Complete B55 separation-reason question."),
        (50, 508, 633, "Complete S41 occupation question."),
        (50, 910, 1246, "Complete S41c employer/confidentiality block."),
        (50, 1250, 1367, "Complete S42 months-worked question."),
        (52, 1806, 1978, "Complete S43 employment-status question."),
        (52, 2130, 2150, "Pure S44 left-column physical-line prompt slice."),
        (52, 2232, 2246, "Pure S44 left-column physical-line prompt slice."),
        (52, 2325, 2338, "Pure S44 left-column physical-line prompt slice."),
        (52, 2355, 2367, "Pure S44 left-column physical-line prompt slice."),
        (52, 2162, 2215, "Pure S45 right-column physical-line prompt slice."),
        (52, 2263, 2308, "Pure S45 right-column physical-line prompt slice."),
        (54, 881, 1001, "Complete S47 position-change-type question."),
        (54, 593, 713, "Complete S46 position-change question."),
        (54, 1138, 1350, "Complete S48 start-year question."),
        (56, 741, 918, "Complete S55 separation-reason question."),
        (56, 1084, 1130, "Pure S56a left-column physical-line prompt slice."),
        (56, 1197, 1210, "Pure S56a left-column physical-line prompt slice."),
        (56, 1145, 1183, "Pure S57 right-column physical-line prompt slice."),
        (56, 1254, 1283, "Pure S57 right-column physical-line prompt slice."),
        (61, 622, 1226, "Complete B66-B68 time-off objective block."),
        (62, 584, 703, "Complete B72 missed-work question."),
        (62, 2147, 2234, "Complete B78 main-job weeks question."),
        (63, 218, 1847, "Complete B72-B74 compatibility objective block."),
        (63, 2188, 2866, "Complete B78 objective and instruction block."),
        (64, 4, 99, "Complete B79 main-job hours question."),
        (64, 1346, 1479, "Complete B82 extra-job question."),
        (64, 1560, 1667, "Complete B83 employer-type question."),
        (66, 904, 997, "Complete B90 extra-job start question."),
        (66, 1054, 1147, "Complete B91 extra-job months question."),
        (67, 410, 732, "Complete B89 average-hours objective."),
        (70, 215, 371, "Complete C5 last-work date question."),
        (72, 3, 105, "Complete C12 employment-status question."),
        (72, 409, 544, "Complete C12a two-job/self-employment alternative."),
        (72, 1516, 1541, "Pure C13 left-column physical-line prompt slice."),
        (72, 1614, 1633, "Pure C13 left-column physical-line prompt slice."),
        (72, 1555, 1606, "Pure C14 right-column physical-line prompt slice."),
        (72, 1653, 1698, "Pure C14 right-column physical-line prompt slice."),
        (72, 2131, 2458, "Complete C14a employer/confidentiality block."),
        (74, 196, 382, "Complete repeated-employment start qualifier."),
        (74, 769, 790, "Pure C17 column prompt slice."),
        (74, 874, 892, "Pure C17 column prompt slice."),
        (74, 975, 984, "Pure C17 column prompt slice."),
        (74, 1073, 1087, "Pure C17 column prompt slice."),
        (74, 1171, 1182, "Pure C17 column prompt slice."),
        (74, 802, 829, "Pure C22 column prompt slice."),
        (74, 907, 931, "Pure C22 column prompt slice."),
        (74, 1008, 1028, "Pure C22 column prompt slice."),
        (74, 1106, 1122, "Pure C22 column prompt slice."),
        (74, 840, 866, "Pure C23 column prompt slice."),
        (74, 949, 967, "Pure C23 column prompt slice."),
        (74, 1050, 1065, "Pure C23 column prompt slice."),
        (74, 1148, 1163, "Pure C23 column prompt slice."),
        (74, 1246, 1262, "Pure C23 column prompt slice."),
        (
            88,
            2679,
            2817,
            "Complete G14 bonus/overtime/tips/commission question.",
        ),
        (
            90,
            2568,
            2705,
            "Complete G14 bonus/overtime/tips/commission question.",
        ),
        (106, 1299, 1427, "Complete G52 gross-earnings question."),
        (114, 1440, 1689, "Complete GJ1 work and employer-type question."),
        (22, 824, 848, "Pure B2 question-header physical-line slice."),
        (22, 885, 899, "Pure B2 question-completion physical-line slice."),
        (36, 743, 775, "Pure B17b prompt header."),
        (36, 798, 835, "Pure B17c prompt header."),
        (36, 842, 850, "Pure B17b amount prompt slice."),
        (36, 897, 905, "Pure B17c amount prompt slice."),
        (40, 2232, 2271, "Pure B26 column prompt slice."),
        (40, 2286, 2325, "Pure B32 column prompt slice."),
        (40, 2337, 2366, "Pure B26 column prompt slice."),
        (40, 2392, 2421, "Pure B32 column prompt slice."),
        (40, 2433, 2459, "Pure B27 column prompt slice."),
        (40, 2488, 2512, "Pure B33 column prompt slice."),
        (40, 2693, 2730, "Pure B27 column prompt slice."),
        (40, 2747, 2787, "Pure B33 column prompt slice."),
        (40, 2798, 2830, "Pure B27 column prompt slice."),
        (40, 2841, 2862, "Pure B27 column prompt slice."),
        (40, 3011, 3058, "Pure B34 first prompt slice."),
        (40, 3125, 3158, "Pure B34 middle prompt slice."),
        (40, 3225, 3252, "Pure B34 final prompt slice."),
        (40, 3506, 3543, "Pure B29 first prompt slice."),
        (40, 3551, 3585, "Pure B29 middle prompt slice."),
        (40, 3593, 3624, "Pure B29 final prompt slice."),
        (48, 1260, 1309, "Pure B56 left-column prompt slice."),
        (48, 1318, 1359, "Pure B57 right-column prompt slice."),
        (48, 1428, 1456, "Pure B57 right-column prompt slice."),
        (48, 1525, 1534, "Pure B57 right-column prompt slice."),
        (60, 807, 878, "Complete B60 weeks-worked prompt slice."),
        (60, 918, 982, "Pure B60 continuation prompt slice."),
        (60, 1025, 1082, "Pure B60 continuation prompt slice."),
        (60, 1124, 1185, "Pure B60 continuation prompt slice."),
        (64, 1001, 1027, "Pure B81c prompt slice."),
        (64, 1034, 1054, "Pure B81c prompt slice."),
        (64, 1061, 1082, "Pure B81c prompt slice."),
        (64, 1089, 1102, "Pure B81c amount slice."),
        (64, 1176, 1201, "Pure B81d prompt slice."),
        (64, 1209, 1228, "Pure B81d prompt slice."),
        (64, 1236, 1252, "Pure B81d prompt slice."),
        (64, 1260, 1268, "Pure B81d amount slice."),
        (74, 1754, 1793, "Pure C18 column prompt slice."),
        (74, 1806, 1845, "Pure C24 column prompt slice."),
        (74, 1857, 1883, "Pure C18 column prompt slice."),
        (74, 1910, 1939, "Pure C24 column prompt slice."),
        (74, 1951, 1977, "Pure C18 column prompt slice."),
        (74, 2004, 2028, "Pure C24 column prompt slice."),
        (74, 2200, 2237, "Pure C19 column prompt slice."),
        (74, 2252, 2292, "Pure C25 column prompt slice."),
        (74, 2303, 2335, "Pure C19 column prompt slice."),
        (74, 3146, 3180, "Pure C21 middle prompt slice."),
        (74, 3188, 3219, "Pure C21 final prompt slice."),
        (76, 1393, 1418, "Pure D2 question-header prompt slice."),
        (76, 1455, 1476, "Pure D2 question-completion prompt slice."),
        (84, 968, 1020, "Complete G4 farm-income amount prompt."),
        (86, 947, 998, "Complete G4 farm-income amount prompt."),
        (88, 3226, 3241, "Pure G17b overtime prompt slice."),
        (88, 3312, 3323, "Pure G17c tips prompt slice."),
        (88, 3402, 3421, "Pure G17d commissions prompt slice."),
        (90, 3164, 3182, "Pure G17b overtime prompt slice."),
        (90, 3256, 3270, "Pure G17c tips prompt slice."),
        (90, 3347, 3368, "Pure G17d commissions prompt slice."),
        (122, 4130, 4199, "Complete G79 occupation prompt."),
        (122, 4788, 4842, "Pure G81 employer-name prompt slice."),
        (122, 4859, 4905, "Pure G81 confidentiality prompt slice."),
        (279, 550, 868, "Complete K44 work-years purpose explanation."),
        (
            281,
            1448,
            1959,
            "Complete L6 occupation-history purpose explanation.",
        ),
        (58, 83, 435, "Complete B60-B78 work-history purpose statement."),
        (58, 1286, 1507, "Complete work-status objective statement."),
        (107, 101, 306, "Complete G50-G52 purpose explanation."),
        (107, 308, 857, "Complete business-income duplication purpose block."),
        (115, 129, 609, "Complete Job Supplement purpose statement."),
        (75, 102, 439, "Complete C16-C51 duplicate-purpose explanation."),
        (75, 441, 561, "Complete C52-C98 duplicate-purpose explanation."),
        (24, 498, 725, "Complete B4a job-count purpose block."),
        (24, 836, 1255, "Complete B4b job-choice purpose block."),
        (25, 102, 509, "Complete main-versus-extra-job assignment rule."),
        (25, 511, 1591, "Complete B4 main-job choice purpose block."),
        (25, 1592, 1884, "Complete B5 unresolved-job purpose block."),
        (25, 1886, 2006, "Complete B8 additional-job purpose block."),
        (27, 115, 3291, "Complete B9-B9a occupation-probing purpose block."),
        (
            26,
            196,
            520,
            "Complete employer-name and confidentiality purpose block.",
        ),
        (
            28,
            196,
            523,
            "Complete employer-name and confidentiality purpose block.",
        ),
        (29, 103, 831, "Complete B10 employer-kind purpose block."),
        (29, 1198, 1438, "Complete government-level purpose item."),
        (29, 1597, 1672, "Complete machine-kind purpose item."),
        (29, 1673, 1857, "Complete machinist distinction purpose item."),
        (29, 1865, 2029, "Complete school-kind purpose item."),
        (29, 2246, 2368, "Complete employer-division purpose item."),
        (29, 2693, 3038, "Complete pay-method purpose item."),
        (30, 17, 154, "Complete managerial-duties purpose item."),
        (30, 623, 779, "Complete supervisory-duties purpose item."),
        (
            32,
            196,
            522,
            "Complete employer-name and confidentiality purpose block.",
        ),
        (34, 1922, 2049, "Complete B14 fixed-amount purpose block."),
        (35, 104, 462, "Complete B12-B19 earnings-purpose overview."),
        (35, 463, 687, "Complete B12 pay-basis purpose block."),
        (35, 688, 977, "Complete B14 fixed-pay purpose block."),
        (35, 979, 1543, "Complete B15 overtime-pay purpose block."),
        (35, 1545, 1684, "Complete B18 other-payment purpose block."),
        (35, 1685, 1803, "Complete B19 earnings-total purpose block."),
        (37, 95, 645, "Complete B17 remuneration-components purpose block."),
        (39, 101, 321, "Complete B20 union purpose block."),
        (39, 322, 775, "Complete B21 job-search purpose block."),
        (39, 836, 1098, "Complete B23 business-change purpose block."),
        (41, 139, 797, "Complete B24-B34 sequence-purpose overview."),
        (41, 1351, 1759, "Complete B24 start-date purpose block."),
        (41, 1760, 2262, "Complete B25-B29 1993-start purpose block."),
        (41, 2263, 2498, "Complete B30 1994-start purpose block."),
        (41, 2500, 2753, "Complete B31-B34 earlier-start purpose block."),
        (42, 794, 1027, "Complete B40 main-job purpose question."),
        (43, 989, 1130, "Complete B40 no-work route purpose block."),
        (43, 1131, 1405, "Complete B40 pre-1993 interpretation block."),
        (43, 1406, 1648, "Complete B40 1993 interpretation block."),
        (43, 1649, 1892, "Complete B40 1994 interpretation block."),
        (45, 93, 770, "Complete B42a-B42d overlap interpretation block."),
        (46, 935, 1164, "Complete B48 start-year purpose block."),
        (47, 90, 198, "Complete B45a amount-and-unit purpose instruction."),
        (47, 232, 676, "Complete B46-B47 purpose block."),
        (48, 2123, 2291, "Complete B59 supplemental-job purpose block."),
        (49, 126, 834, "Complete B53-B55 purpose block."),
        (49, 867, 1069, "Complete B59 supplemental-job purpose block."),
        (50, 637, 849, "Complete S41a supervisory-purpose block."),
        (51, 1629, 1787, "Complete S41-S41c job-detail purpose instruction."),
        (54, 1585, 1723, "Complete S49 purpose block."),
        (55, 120, 309, "Complete S46-S47 purpose block."),
        (56, 186, 329, "Complete S53 purpose block."),
        (56, 2006, 2200, "Complete S59 purpose block."),
        (61, 102, 378, "Complete B60-B62 purpose block."),
        (61, 379, 621, "Complete B63-B65 purpose block."),
        (62, 1353, 1454, "Complete B75 no-job purpose question."),
        (62, 1907, 2018, "Complete B77a no-job-months purpose question."),
        (63, 101, 217, "Complete B69-B71 purpose block."),
        (63, 1848, 2187, "Complete B75-B77 purpose block."),
        (64, 759, 908, "Complete B81b main-job purpose block."),
        (65, 178, 380, "Complete B80-B81 purpose block."),
        (65, 381, 515, "Complete B81a-B81d multiple-job purpose block."),
        (65, 516, 2197, "Complete B82 main-job-hours purpose block."),
        (65, 2200, 2565, "Complete B83-B85 purpose block."),
        (66, 102, 439, "Complete B86 employer-name purpose block."),
        (67, 122, 296, "Complete B87 employer-location purpose block."),
        (67, 297, 409, "Complete B88 distance purpose block."),
        (67, 733, 850, "Complete B90-B93 purpose block."),
        (70, 1227, 1335, "Complete C8 job-search-months purpose question."),
        (71, 736, 950, "Complete C9-C11 job-detail purpose instruction."),
        (72, 307, 544, "Complete C12a job-count purpose block."),
        (72, 678, 1132, "Complete C12b main-job choice purpose block."),
        (72, 1156, 1284, "Complete C12c unresolved-job purpose block."),
        (72, 2462, 2590, "Complete C15 incorporated-status purpose block."),
        (74, 2764, 2797, "Pure C26 middle purpose slice."),
        (76, 678, 908, "Complete D1a activity-status purpose block."),
        (76, 1638, 1653, "Complete D3 work-for-money purpose fragment."),
        (84, 600, 774, "Complete G2 farm-expense purpose question."),
        (84, 783, 959, "Complete G3 farm-expense purpose question."),
        (84, 1692, 1855, "Complete G7 business-income purpose question."),
        (84, 2108, 2262, "Complete G9a work-hours purpose question."),
        (84, 2883, 3027, "Complete G9c Wife-work purpose question."),
        (84, 3138, 3218, "Complete G9d prior-report purpose question."),
        (85, 505, 800, "Complete G1a QxQ purpose block."),
        (85, 801, 1308, "Complete G2 QxQ purpose block."),
        (85, 1309, 1936, "Complete G3 QxQ purpose block."),
        (85, 1938, 2125, "Complete G4 QxQ purpose block."),
        (86, 579, 753, "Complete G2 farm-expense purpose question."),
        (86, 762, 938, "Complete G3 farm-expense purpose question."),
        (86, 1630, 1800, "Complete G7 business-income purpose question."),
        (86, 2056, 2208, "Complete G9a work-hours purpose question."),
        (86, 2894, 3037, "Complete G9c Wife-work purpose question."),
        (87, 343, 705, "Complete G5-G7a QxQ purpose block."),
        (87, 721, 922, "Complete self-employment QxQ purpose paragraph."),
        (87, 1019, 1473, "Complete G9a-G9d QxQ purpose block."),
        (88, 745, 791, "Pure G11a purpose slice."),
        (88, 824, 843, "Pure G11b purpose slice."),
        (88, 851, 900, "Pure G11a purpose slice."),
        (88, 930, 947, "Pure G11b purpose slice."),
        (88, 1586, 1866, "Complete G12 purpose question."),
        (88, 2133, 2157, "Pure G13 purpose slice."),
        (88, 2188, 2215, "Pure G16 purpose slice."),
        (88, 2323, 2351, "Pure G13-G16 purpose slice."),
        (89, 112, 403, "Complete G10 QxQ purpose block."),
        (89, 550, 1570, "Complete G11a QxQ purpose block."),
        (89, 2055, 2437, "Complete G12 QxQ purpose block."),
        (89, 2439, 3873, "Complete G13 QxQ purpose block."),
        (90, 659, 705, "Pure G11a purpose slice."),
        (90, 742, 761, "Pure G11b purpose slice."),
        (90, 769, 818, "Pure G11a purpose slice."),
        (90, 852, 869, "Pure G11b purpose slice."),
        (90, 1450, 1730, "Complete G12 purpose question."),
        (90, 2001, 2025, "Pure G13 purpose slice."),
        (90, 2060, 2087, "Pure G16 purpose slice."),
        (90, 2198, 2226, "Pure G13-G16 purpose slice."),
        (91, 227, 387, "Complete G14 QxQ purpose block."),
        (
            91,
            100,
            226,
            "Complete G11a-G13 anti-double-counting purpose block.",
        ),
        (91, 481, 707, "Complete G17e QxQ purpose block."),
        (93, 105, 681, "Complete G18 QxQ purpose block."),
        (93, 683, 999, "Complete G18b QxQ purpose block."),
        (93, 1235, 2486, "Complete G18c QxQ purpose block."),
        (93, 2488, 2744, "Complete G19a-G19c QxQ purpose block."),
        (93, 2746, 2985, "Complete G20a-G20c QxQ purpose block."),
        (115, 1213, 1339, "Complete GJ2 purpose block."),
        (115, 1341, 1718, "Complete GJ3-GJ3a purpose block."),
        (117, 258, 376, "Complete GJ4 QxQ purpose block."),
        (117, 378, 694, "Complete GJ5 QxQ purpose block."),
        (117, 696, 815, "Complete GJ6-GJ9 QxQ purpose block."),
        (117, 817, 995, "Complete GJ10 QxQ purpose block."),
    ]
    replacements = [
        replacement
        for replacement in replacements
        if replacement[3] != "field_purpose_prompt"
        or not any(
            replacement[0] == page
            and replacement[1] < end
            and start < replacement[2]
            for page, start, end, _note in purpose_merges
        )
    ]
    replacements.extend(
        (page, start, end, "field_purpose_prompt", note)
        for page, start, end, note in purpose_merges
    )
    context_reslices = [
        (22, 303, 320, "Pure working-now response context."),
        (22, 331, 365, "Pure temporarily-off response context."),
        (22, 798, 821, "Pure retired response context."),
        (22, 824, 848, "Pure B2 question-header context."),
        (64, 2075, 2094, "Pure B83a answer context."),
        (76, 919, 936, "Pure D1 working-now response context."),
        (76, 938, 972, "Pure D1 temporarily-off response context."),
        (76, 1368, 1389, "Pure D1 retired response context."),
        (76, 1393, 1418, "Pure D2 question-header context."),
        (76, 1746, 1797, "Pure D1 disabled response context."),
        (76, 1811, 1818, "Pure D3 yes response context."),
        (40, 96, 289, "Complete B24 start-date qualifier context."),
        (71, 101, 625, "Complete C4-C8 work-history context block."),
        (74, 196, 382, "Complete C16 start-date qualifier context."),
        (74, 1754, 1793, "Pure C18 column context slice."),
        (74, 1806, 1845, "Pure C24 column context slice."),
        (74, 1857, 1883, "Pure C18 column context slice."),
        (74, 1910, 1939, "Pure C24 column context slice."),
        (74, 1951, 1977, "Pure C18 column context slice."),
        (74, 2004, 2028, "Pure C24 column context slice."),
        (74, 2200, 2237, "Pure C19 column context slice."),
        (74, 2252, 2292, "Pure C25 column context slice."),
        (74, 2303, 2335, "Pure C19 column context slice."),
        (74, 2346, 2367, "Pure C19 column context slice."),
        (52, 1806, 1978, "Complete S43 employment-status context."),
        (84, 2434, 2458, "Pure G9b yes response context."),
        (84, 2478, 2501, "Pure G9b no response context."),
        (84, 3258, 3282, "Pure G9d yes response context."),
        (84, 3302, 3325, "Pure G9d no response context."),
        (86, 2427, 2451, "Pure G9b yes response context."),
        (86, 2471, 2494, "Pure G9b no response context."),
        (86, 3246, 3270, "Pure G9d yes response context."),
        (86, 3294, 3317, "Pure G9d no response context."),
        (88, 3549, 3588, "Pure G17e reported-hours response context."),
        (88, 3589, 3631, "Pure G17e unreported-hours response context."),
        (90, 3494, 3533, "Pure G17e reported-hours response context."),
        (90, 3547, 3589, "Pure G17e unreported-hours response context."),
        (92, 795, 834, "Pure G21a reported-hours response context."),
        (92, 835, 877, "Pure G21a missing-hours response context."),
        (92, 1578, 1616, "Pure G21b reported-hours response context."),
        (92, 1617, 1661, "Pure G21b missing-hours response context."),
        (92, 2436, 2475, "Pure G21c reported-hours response context."),
        (92, 2476, 2518, "Pure G21c missing-hours response context."),
        (122, 1930, 1940, "Pure G76 first-year response context."),
        (122, 1951, 1958, "Pure G76 first-year response context."),
        (122, 1982, 1992, "Pure G76 second-year response context."),
        (122, 2011, 2021, "Pure G76 second-year response context."),
        (122, 2241, 2249, "Pure G77 first-job response context."),
        (122, 2272, 2282, "Pure G77 other-job response context."),
        (122, 4859, 4905, "Pure G81 confidentiality context."),
        (232, 894, 906, "Pure P9 hours response context."),
        (232, 917, 929, "Pure P9 hours response context."),
        (232, 939, 951, "Pure P9 hours response context."),
        (232, 1495, 1507, "Pure P10 hours response context."),
        (232, 1516, 1528, "Pure P10 hours response context."),
        (232, 1537, 1549, "Pure P10 hours response context."),
        (280, 2187, 2200, "Pure L6 first-response context."),
        (280, 2210, 2225, "Pure L6 second-response context."),
        (280, 2238, 2248, "Pure L6 third-response context."),
        (232, 640, 802, "Complete P9 work-hours context."),
        (232, 1235, 1392, "Complete P10 work-hours context."),
        (233, 487, 611, "Complete P8 assistance context explanation."),
        (279, 550, 868, "Complete K44 work-years context explanation."),
        (
            281,
            1448,
            1959,
            "Complete L6 occupation-history context explanation.",
        ),
        (107, 101, 306, "Complete G50-G52 context explanation."),
        (107, 599, 857, "Complete business-income amount context."),
        (115, 129, 609, "Complete Job Supplement context statement."),
        (44, 1359, 1455, "Complete B42b overlap context."),
        (54, 1138, 1350, "Complete S48 start-year context."),
    ]
    replacements = [
        replacement
        for replacement in replacements
        if replacement[3] != "context_anchor"
        or not any(
            replacement[0] == page
            and replacement[1] < end
            and start < replacement[2]
            for page, start, end, _note in context_reslices
        )
    ]
    replacements.extend(
        (page, start, end, "context_anchor", note)
        for page, start, end, note in context_reslices
    )
    flow_reslices = [
        (22, 239, 293, "Complete B1 working-now/temporarily-off route."),
        (22, 506, 520, "B1 looking-for-work response branch."),
        (22, 798, 811, "B1 retired response branch."),
        (22, 1170, 1182, "B1 disabled response branch."),
        (22, 1292, 1300, "B3 yes response branch."),
        (22, 1749, 1767, "B1 keeping-house response branch."),
        (22, 1839, 1853, "B1 student response branch."),
        (22, 1903, 1921, "B1 other-activity response branch."),
        (23, 637, 758, "B1 working-now Section B branch."),
        (23, 759, 847, "B3 yes Section B branch."),
        (23, 848, 877, "B3 no Section C branch."),
        (
            25,
            302,
            448,
            "Complete equal-hours higher-earnings main-job branch.",
        ),
        (25, 1306, 1409, "Unresolved main/extra role B5 branch."),
        (25, 1783, 1884, "Other business-category note branch."),
        (26, 420, 520, "B11 missing-employer-name action."),
        (27, 2979, 3291, "Complete mixed self/other-employment directive."),
        (28, 423, 523, "B11 missing-employer-name action."),
        (29, 1198, 1438, "Government-department probe branch."),
        (29, 1597, 1672, "Machine-type probe branch."),
        (29, 2814, 2952, "Complete commission-status fallback probe branch."),
        (30, 623, 779, "Manager/supervisor duties probe branch."),
        (32, 422, 522, "B11 missing-employer-name action."),
        (33, 443, 617, "Missing-employer-name short-title action."),
        (35, 688, 863, "Complete fixed-amount B14 no branch."),
        (35, 864, 977, "Complete salary-plus-overtime B14 yes branch."),
        (39, 586, 706, "Advertisement-used branch."),
        (39, 707, 775, "No-advertisement child branch."),
        (39, 917, 993, "Ownership-change note branch."),
        (39, 994, 1098, "Multiple-spells total-altogether branch."),
        (40, 91, 289, "Complete B24 most-recent-start directive."),
        (41, 1760, 2262, "B25-B29 1993-start route block."),
        (41, 2263, 2498, "B30 1994-or-unknown-start route block."),
        (41, 2500, 2753, "B31-B34 pre-1993-start route block."),
        (42, 887, 963, "Self-employed B40 counting branch."),
        (42, 1271, 1417, "B41a conditional clarification branch."),
        (42, 1700, 1804, "B41c missing-employer-name action."),
        (43, 715, 988, "B39 main-versus-extra-months branch."),
        (43, 989, 1130, "B40 no-to-B60 branch."),
        (43, 1131, 1405, "Pre-1993 start branch."),
        (43, 1406, 1648, "1993 start/overlap branch."),
        (43, 1649, 1892, "1994 start branch."),
        (45, 237, 569, "Partial position-overlap branch."),
        (45, 570, 769, "Complete position-overlap branch."),
        (24, 207, 223, "B4 self-employed response branch."),
        (24, 237, 257, "B4 both response branch."),
        (24, 286, 300, "B4 someone-else response branch."),
        (24, 760, 773, "B4a one-job response branch."),
        (24, 807, 815, "B4a route to B5."),
        (24, 1443, 1464, "B4c self-employed-only response branch."),
        (24, 1467, 1487, "B4c someone-else-only response branch."),
        (24, 1529, 1537, "Pure B5 left-column route."),
        (24, 1557, 1565, "Pure B6 right-column route."),
        (24, 2230, 2231, "B7 yes response branch."),
        (24, 2247, 2261, "B7 no route to B9."),
        (24, 2404, 2414, "B8 yes terminal response branch."),
        (34, 203, 216, "B12 salaried response branch."),
        (34, 231, 241, "B12 salary-plus-commission response branch."),
        (34, 249, 259, "B12 paid-by-hour response branch."),
        (34, 264, 274, "B12 hourly-plus-tips response branch."),
        (34, 279, 289, "B12 hourly-plus-commission response branch."),
        (34, 295, 303, "B12 other-payment response branch."),
        (34, 2080, 2111, "B14 no route to B17a."),
        (34, 2123, 2124, "B14 yes response branch."),
        (36, 445, 471, "B17a tips branch."),
        (36, 488, 592, "B17a commission branch."),
        (36, 700, 714, "B17a all-others route to B20."),
        (38, 234, 240, "B20 no route to B22."),
        (38, 833, 886, "B22 someone-else-only branch."),
        (38, 941, 958, "B22 all-others branch."),
        (38, 961, 975, "B22 all-others route."),
        (40, 367, 373, "B24 1993 response branch."),
        (40, 383, 389, "B24 1994 response branch."),
        (40, 390, 411, "B24 1993-or-1994 unknown response branch."),
        (40, 418, 429, "B24 other-year response branch."),
        (40, 435, 451, "B24 before-1993 response branch."),
        (40, 458, 469, "B24 unknown-year response branch."),
        (40, 1203, 1212, "B25 yes response branch."),
        (40, 1357, 1363, "B30 1993 response branch."),
        (40, 1480, 1486, "B30 1994 response branch."),
        (40, 1645, 1651, "B31 1993 response branch."),
        (40, 2104, 2121, "B31 other-year response branch."),
        (
            40,
            2581,
            2582,
            "B32 yes response recovered from degraded source glyph.",
        ),
        (
            40,
            2583,
            2592,
            "B32 no route recovered from degraded source glyph and skip text.",
        ),
        (40, 2647, 2656, "B26 1993 route to B29."),
        (40, 2683, 2689, "B26 1994 response branch."),
        (40, 2966, 2973, "B27 yes response branch."),
        (40, 2974, 2986, "B27 no response branch."),
        (42, 1067, 1099, "B40 no response branch."),
        (44, 99, 112, "B42 no-overlap branch."),
        (44, 115, 159, "Complete B42 one-month-overlap branch."),
        (44, 209, 280, "Complete B42 partial-overlap branch."),
        (44, 354, 375, "B42 complete-overlap branch."),
        (44, 619, 628, "B42 route to B43."),
        (44, 1335, 1352, "Source-visible truncated B58 route."),
        (44, 1498, 1525, "B42b no route to B43."),
        (44, 1821, 1837, "B43 self-employed response branch."),
        (44, 1847, 1867, "B43 both response branch."),
        (44, 1882, 1897, "B43 someone-else response branch."),
        (46, 593, 601, "B46 no route to B48."),
        (46, 1218, 1224, "B48 1993 response branch."),
        (46, 1234, 1245, "B48 other-year response branch."),
        (46, 1255, 1266, "B48 before-1993 response branch."),
        (46, 1274, 1285, "B48 unknown-year response branch."),
        (48, 509, 510, "B53 yes response branch."),
        (48, 578, 584, "B53 no route to B59."),
        (48, 1186, 1206, "Self-employed-only B56 route."),
        (48, 1240, 1254, "All-others B57 route."),
        (48, 2300, 2310, "B59 yes response branch."),
        (48, 2334, 2339, "B59 no response branch."),
        (48, 2349, 2369, "B59 no route to B60."),
        (48, 2374, 2386, "B59 yes route to pink supplement."),
        (48, 1942, 1952, "Self-employed B56 route to B57a."),
        (49, 403, 532, "Complete B58 overlap-resolution branch."),
        (49, 877, 1069, "Complete B59 supplement-route branch."),
        (50, 702, 849, "S41a main-versus-extra-job clarification branch."),
        (50, 1147, 1246, "S41c missing-employer-name action."),
        (51, 239, 482, "More-than-two-employers WHS branch."),
        (55, 157, 309, "Complete S46-S47 conditional directive."),
        (52, 287, 302, "S42 no-overlap branch."),
        (52, 305, 351, "Complete S42 one-month-overlap branch."),
        (52, 398, 466, "Complete S42 partial-overlap branch."),
        (52, 533, 557, "S42 complete-overlap branch."),
        (52, 809, 818, "S42 route to S43."),
        (52, 1633, 1655, "S42b no route to S43."),
        (52, 1985, 2001, "S43 self-employed response branch."),
        (52, 2008, 2028, "S43 both response branch."),
        (52, 2037, 2052, "S43 someone-else response branch."),
        (54, 741, 749, "S46 no route to S48."),
        (54, 1408, 1414, "S48 1993 response branch."),
        (54, 1424, 1435, "S48 other-year response branch."),
        (54, 1444, 1455, "S48 before-1993 response branch."),
        (54, 1461, 1472, "S48 unknown-year response branch."),
        (56, 343, 344, "S53 yes response branch."),
        (56, 364, 370, "S53 no route to S59."),
        (56, 1015, 1035, "Self-employed-only S56 route."),
        (56, 1068, 1082, "All-others S57 route."),
        (56, 2213, 2223, "S59 yes response branch."),
        (56, 2224, 2247, "S59 yes route to additional supplement."),
        (56, 2561, 2578, "S20 Section B return route."),
        (56, 2579, 2596, "S20 Section C return route."),
        (56, 2597, 2614, "S20 Section D return route."),
        (56, 2615, 2632, "S20 Section E return route."),
        (59, 1426, 1591, "Complete no-job illness-recording condition."),
        (61, 438, 621, "Complete B63-B65 recording condition."),
        (60, 1240, 1241, "B60 yes response branch."),
        (60, 1311, 1384, "Complete B60 no route to B63."),
        (60, 1622, 1623, "B63 yes response branch."),
        (60, 1684, 1743, "Complete B63 no route to B66."),
        (60, 2015, 2048, "B66 no route to B69."),
        (62, 728, 729, "B72 yes response branch."),
        (62, 1478, 1479, "B75 yes response branch."),
        (62, 2287, 2415, "B78 did-not-work response branch."),
        (62, 2495, 2509, "B78 did-not-work route to B82."),
        (62, 2630, 2647, "B78 all-other totals response branch."),
        (63, 2869, 3133, "Complete B78 discrepancy-resolution condition."),
        (64, 635, 665, "B81a multiple-main-job response branch."),
        (64, 681, 693, "B81a all-others response branch."),
        (64, 747, 757, "B81a all-others route to B82."),
        (64, 1481, 1555, "B82 no terminal branch."),
        (65, 381, 515, "Complete multiple-main-job explanation branch."),
        (65, 1175, 1305, "Complete main-job selection branch."),
        (65, 1314, 1453, "Complete ambiguous-main-job branch."),
        (65, 1815, 1938, "Complete acceptable-job-description branch."),
        (66, 1529, 1587, "B92 no terminal branch."),
        (66, 323, 439, "Complete B86 missing-employer-name action."),
        (67, 208, 296, "Complete B87 location-recording condition."),
        (68, 179, 180, "C1 yes response branch."),
        (68, 212, 226, "C1 no route to C4."),
        (70, 198, 203, "C4 yes route to C6."),
        (70, 451, 457, "C5 1993 response branch."),
        (70, 464, 470, "C5 1994 response branch."),
        (70, 473, 490, "C5 1993-or-1994 response branch."),
        (70, 498, 509, "C5 other-year response branch."),
        (70, 522, 538, "C5 before-1993 response branch."),
        (70, 551, 562, "C5 unknown-year response branch."),
        (70, 835, 838, "C6 yes response branch."),
        (70, 931, 939, "C6 no response branch."),
        (70, 1071, 1109, "C6 no terminal route to Section D."),
        (70, 1187, 1196, "C7 all-52-weeks response branch."),
        (70, 1584, 1609, "C8 terminal route to Section D."),
        (72, 112, 128, "C12 self-employed response branch."),
        (72, 143, 163, "C12 both response branch."),
        (72, 193, 208, "C12 someone-else response branch."),
        (72, 581, 593, "C12a one-job response branch."),
        (72, 599, 610, "C12a two-jobs response branch."),
        (72, 647, 656, "C12a one-job route to C13."),
        (72, 1318, 1341, "C12c self-employed response branch."),
        (72, 1414, 1432, "C12c someone-else response branch."),
        (72, 1472, 1481, "Pure C13 left-column route."),
        (72, 1502, 1511, "Pure C14 right-column route."),
        (72, 1727, 1746, "C13 unincorporated response branch."),
        (72, 1765, 1775, "C14 federal response branch."),
        (72, 1781, 1789, "C14 state response branch."),
        (72, 1796, 1804, "C14 local response branch."),
        (72, 1808, 1818, "C14 private response branch."),
        (72, 1924, 1939, "C13 corporation response branch."),
        (72, 1986, 2005, "C14 other response branch."),
        (72, 2014, 2026, "Common C13 route to C14a."),
        (72, 2349, 2458, "Complete C14a missing-employer-name action."),
        (74, 456, 462, "C16 1993 response branch."),
        (74, 473, 478, "C16 1994 response branch."),
        (74, 481, 498, "C16 1993-or-1994 unknown response branch."),
        (74, 506, 517, "C16 other-year response branch."),
        (74, 523, 539, "C16 before-1993 response branch."),
        (74, 547, 558, "C16 unknown-year response branch."),
        (74, 1273, 1281, "C17 yes response branch."),
        (74, 1288, 1295, "C17 no response branch."),
        (74, 1409, 1415, "C22 1993 response branch."),
        (74, 1423, 1429, "C22 1994 response branch."),
        (74, 1441, 1447, "C23 1993 response branch."),
        (74, 1451, 1457, "C23 1994 response branch."),
        (74, 1462, 1473, "C23 other-year response branch."),
        (74, 1607, 1621, "C22 route to C32."),
        (74, 1736, 1750, "C23 other-year route to C31."),
        (
            74,
            2095,
            2102,
            "C24 no route to C31 recovered from degraded source glyph.",
        ),
        (74, 2192, 2197, "C18 1994 response branch."),
        (74, 2478, 2479, "C19 yes response branch."),
        (74, 3258, 3288, "C21 promotion response branch."),
        (
            74,
            3294,
            3311,
            "C21 major-change response branch recovered from visible source bytes.",
        ),
        (74, 3320, 3339, "C21 other response branch."),
        (74, 3391, 3405, "C21 route to C27."),
        (74, 2945, 2975, "C26 promotion response branch."),
        (74, 3054, 3098, "C26 major-change response branch."),
        (74, 3235, 3254, "C26 other response branch."),
        (74, 3443, 3457, "C26 route to C31."),
        (76, 265, 281, "D1 Head-male response branch."),
        (76, 300, 318, "D1 Head-female response branch."),
        (76, 919, 936, "D1 working-now response branch."),
        (76, 938, 1027, "Complete D1 temporarily-off response branch."),
        (76, 1110, 1124, "D1 looking-for-work response branch."),
        (76, 1233, 1246, "D1 working-or-temporarily-off route to D4."),
        (76, 1368, 1389, "D1 retired response branch."),
        (76, 1746, 1797, "D1 disabled response branch."),
        (76, 1811, 1818, "D3 yes response branch."),
        (76, 1892, 1902, "D3 yes route to D4."),
        (76, 2084, 2091, "D3 source-visible no route to Section E."),
        (76, 2285, 2378, "D1 keeping-house response branch."),
        (76, 2381, 2443, "D1 student response branch."),
        (76, 2444, 2508, "D1 other-activity response branch."),
        (74, 2158, 2168, "C18 1993 route to C21."),
        (74, 2492, 2499, "C19 no response branch."),
        (76, 506, 532, "Wife present branch."),
        (76, 539, 567, "No-wife branch."),
        (57, 275, 347, "WHS return-or-repeat terminal branch."),
        (71, 243, 735, "Complete continue-C9-C51 work-history condition."),
        (84, 2434, 2458, "G9b reported-hours response branch."),
        (84, 2478, 2501, "G9b unreported-hours response branch."),
        (84, 3258, 3282, "G9d reported-hours response branch."),
        (84, 3302, 3325, "G9d unreported-hours response branch."),
        (86, 2427, 2451, "G9b reported-hours response branch."),
        (86, 2471, 2494, "G9b unreported-hours response branch."),
        (86, 3246, 3270, "G9d reported-hours response branch."),
        (86, 3294, 3317, "G9d unreported-hours response branch."),
        (88, 161, 170, "Corporation route to G12."),
        (88, 621, 630, "Broke-even route to G12."),
        (88, 1930, 1942, "G12 no response branch."),
        (88, 2837, 2844, "G14 yes response branch."),
        (88, 2857, 2863, "G14 no response branch."),
        (88, 2881, 2891, "G14 yes route to G16a."),
        (88, 2899, 2909, "G14 no route to G17e."),
        (88, 3549, 3588, "G17e reported-hours response branch."),
        (88, 3589, 3631, "G17e unreported-hours response branch."),
        (88, 3706, 3735, "G17e unreported-hours supplement route."),
        (90, 162, 171, "Corporation route to G12."),
        (90, 531, 540, "Broke-even route to G12."),
        (90, 1795, 1802, "G12 no response branch."),
        (90, 2725, 2735, "G14 yes response branch."),
        (90, 2787, 2796, "G14 no response branch."),
        (90, 2814, 2824, "G14 yes route to G16a."),
        (90, 2833, 2843, "G14 no route to G17e."),
        (90, 3494, 3533, "G17e reported-hours response branch."),
        (90, 3547, 3589, "G17e unreported-hours response branch."),
        (90, 3668, 3697, "G17e unreported-hours supplement route."),
        (91, 100, 226, "Complete G11a-G13 anti-double-counting condition."),
        (92, 795, 834, "G21a reported-hours response branch."),
        (92, 835, 877, "G21a unreported-hours response branch."),
        (92, 957, 986, "G21a supplement route."),
        (92, 1142, 1143, "G18b yes response branch."),
        (92, 1168, 1199, "G18b no route to G18c."),
        (92, 1578, 1616, "G21b reported-hours response branch."),
        (92, 1617, 1661, "G21b unreported-hours response branch."),
        (92, 1740, 1769, "G21b supplement route."),
        (92, 1984, 1985, "G18c yes response branch."),
        (92, 2021, 2057, "G18c no route to G22."),
        (92, 2436, 2475, "G21c reported-hours response branch."),
        (92, 2476, 2518, "G21c unreported-hours response branch."),
        (92, 2596, 2625, "G21c supplement route."),
        (94, 330, 334, "G23 no route to G24."),
        (94, 407, 408, "G23 yes route to G25a."),
        (107, 434, 492, "Included-business-income conditional branch."),
        (107, 589, 597, "Known-amount child condition."),
        (107, 875, 991, "Complete missing-hours supplement action."),
        (114, 575, 587, "GJ0a G9b-business selector."),
        (114, 594, 609, "GJ0a G9d-business selector."),
        (114, 615, 626, "GJ0a G17e Head-wages selector."),
        (114, 638, 654, "GJ0a G21 Head-other-work selector."),
        (114, 681, 697, "GJ0a G52b Wife-work selector."),
        (114, 1013, 1031, "GJ0b G21a professional-practice selector."),
        (114, 1224, 1237, "GJ0b G21b farming selector."),
        (114, 1388, 1414, "GJ0b G21c roomer-or-boarder selector."),
        (114, 1719, 1728, "GJ1 federal-government response branch."),
        (114, 1731, 1738, "GJ1 state-government response branch."),
        (114, 1742, 1752, "GJ1 local-government response branch."),
        (114, 1753, 1762, "GJ1 private-company response branch."),
        (114, 1763, 1769, "GJ1 self-employed response branch."),
        (114, 1774, 1792, "GJ1 other-employer-type response branch."),
        (115, 434, 609, "Complete missing-hours supplement action."),
        (115, 1213, 1339, "Complete employer-name assurance action."),
        (106, 1757, 1794, "G52a reported-hours response branch."),
        (106, 1809, 1852, "G52a unreported-hours response branch."),
        (116, 2548, 2554, "G21a terminal option branch."),
        (116, 2562, 2568, "G21b terminal option branch."),
        (116, 2581, 2587, "G21c terminal option branch."),
        (119, 1974, 2131, "Complete moved-or-died roster instruction."),
        (232, 1202, 1211, "No-wife P10 route to P11."),
        (266, 471, 476, "Ivory no-wife response branch."),
        (266, 951, 1070, "No-wife terminal route to Section L."),
        (266, 1115, 1186, "Same-wife/no-wife terminal route."),
        (280, 566, 619, "Same-Head terminal route to Section M."),
    ]
    replacements = [
        replacement
        for replacement in replacements
        if replacement[3] != "flow_branch_label"
        or not any(
            replacement[0] == page
            and replacement[1] < end
            and start < replacement[2]
            for page, start, end, _note in flow_reslices
        )
    ]
    replacements.extend(
        (page, start, end, "flow_branch_label", note)
        for page, start, end, note in flow_reslices
    )

    # These exact reviewed atoms are detector or earlier hand-specification
    # false positives.  Normalize the hand-authored coordinates before the
    # filter because some replacement windows include leading whitespace.
    reviewed_false_occurrences = {
        (23, 156, 216, "flow_branch_label"),
        (24, 207, 301, "context_anchor"),
        (24, 1442, 1491, "context_anchor"),
        (40, 96, 289, "flow_branch_label"),
        (40, 2232, 2325, "context_anchor"),
        (40, 2337, 2421, "context_anchor"),
        (40, 2693, 2787, "context_anchor"),
        (44, 1821, 1897, "context_anchor"),
        (48, 2215, 2291, "flow_branch_label"),
        (52, 1985, 2052, "context_anchor"),
        (56, 2103, 2189, "flow_branch_label"),
        (58, 1193, 1285, "flow_branch_label"),
        (61, 297, 378, "flow_branch_label"),
        (63, 403, 481, "flow_branch_label"),
        (63, 939, 1022, "flow_branch_label"),
        (63, 2040, 2129, "flow_branch_label"),
        (63, 2480, 2559, "flow_branch_label"),
        (67, 865, 931, "flow_branch_label"),
        (74, 196, 278, "flow_branch_label"),
        (75, 102, 179, "flow_branch_label"),
        (77, 782, 862, "flow_branch_label"),
        (77, 863, 948, "flow_branch_label"),
        (84, 334, 361, "flow_branch_label"),
        (84, 2692, 2726, "flow_branch_label"),
        (86, 329, 356, "flow_branch_label"),
        (86, 2677, 2710, "flow_branch_label"),
        (88, 1182, 1213, "flow_branch_label"),
        (88, 3458, 3538, "flow_branch_label"),
        (90, 1125, 1156, "flow_branch_label"),
        (90, 3403, 3483, "flow_branch_label"),
        (92, 700, 784, "flow_branch_label"),
        (92, 1484, 1568, "flow_branch_label"),
        (92, 2341, 2426, "flow_branch_label"),
        (94, 3, 30, "flow_branch_label"),
        (115, 1677, 1689, "flow_branch_label"),
        (116, 1432, 1448, "flow_branch_label"),
        (123, 1009, 1077, "role_total_anchor"),
        (123, 1282, 1380, "role_total_anchor"),
        (131, 100, 238, "role_total_anchor"),
        (38, 733, 760, "field_purpose_prompt"),
        (56, 1678, 1697, "field_purpose_prompt"),
        (56, 2298, 2325, "field_purpose_prompt"),
        (58, 1193, 1285, "field_purpose_prompt"),
        (76, 78, 104, "field_purpose_prompt"),
        (131, 100, 238, "context_anchor"),
        (131, 100, 238, "field_purpose_prompt"),
        (131, 225, 237, "remuneration_component_anchor"),
        (232, 357, 378, "context_anchor"),
        (232, 579, 590, "role_anchor"),
        (232, 894, 951, "context_anchor"),
        (232, 1495, 1549, "context_anchor"),
        (280, 1419, 1519, "context_anchor"),
        (280, 1419, 1519, "field_purpose_prompt"),
        (280, 2187, 2248, "context_anchor"),
        (281, 1282, 1445, "context_anchor"),
        (282, 746, 1015, "flow_branch_label"),
        (282, 746, 1015, "role_anchor"),
        (282, 746, 1015, "job_anchor"),
        (282, 746, 1015, "context_anchor"),
        (282, 746, 1015, "field_purpose_prompt"),
        (283, 341, 817, "role_anchor"),
        (283, 341, 817, "job_anchor"),
        (283, 341, 817, "context_anchor"),
        (283, 341, 817, "field_purpose_prompt"),
        (283, 1042, 1306, "field_purpose_prompt"),
        (283, 1156, 1166, "role_anchor"),
        (117, 101, 199, "field_purpose_prompt"),
        (116, 313, 321, "business_aggregate_anchor"),
        (51, 1233, 1318, "context_anchor"),
        (51, 1233, 1318, "field_purpose_prompt"),
        (59, 262, 348, "field_purpose_prompt"),
        (68, 605, 644, "field_purpose_prompt"),
        (77, 552, 588, "field_purpose_prompt"),
        (281, 1282, 1445, "field_purpose_prompt"),
        (23, 1468, 1544, "field_purpose_prompt"),
        (23, 1731, 1805, "field_purpose_prompt"),
        (23, 1921, 1987, "field_purpose_prompt"),
        (23, 1995, 2071, "field_purpose_prompt"),
        (76, 919, 936, "context_anchor"),
        (76, 938, 972, "context_anchor"),
        (76, 1368, 1389, "context_anchor"),
        (76, 1746, 1797, "context_anchor"),
        (76, 1811, 1818, "context_anchor"),
        (84, 2434, 2458, "context_anchor"),
        (84, 2478, 2501, "context_anchor"),
        (84, 3258, 3282, "context_anchor"),
        (84, 3302, 3325, "context_anchor"),
        (86, 2427, 2451, "context_anchor"),
        (86, 2471, 2494, "context_anchor"),
        (86, 3246, 3270, "context_anchor"),
        (86, 3294, 3317, "context_anchor"),
        (88, 3549, 3588, "context_anchor"),
        (88, 3589, 3631, "context_anchor"),
        (90, 3494, 3533, "context_anchor"),
        (90, 3547, 3589, "context_anchor"),
        (92, 795, 834, "context_anchor"),
        (92, 835, 877, "context_anchor"),
        (92, 1578, 1616, "context_anchor"),
        (92, 1617, 1661, "context_anchor"),
        (92, 2436, 2475, "context_anchor"),
        (92, 2476, 2518, "context_anchor"),
        (58, 83, 114, "flow_branch_label"),
        (58, 129, 181, "flow_branch_label"),
        (29, 1865, 2029, "flow_branch_label"),
        (65, 1975, 2038, "flow_branch_label"),
        (74, 1377, 1387, "flow_branch_label"),
        (74, 1483, 1486, "flow_branch_label"),
        (74, 1560, 1565, "flow_branch_label"),
        (74, 1640, 1643, "flow_branch_label"),
        (74, 2503, 2514, "flow_branch_label"),
        (74, 2552, 2555, "flow_branch_label"),
        (74, 3345, 3360, "flow_branch_label"),
        (74, 3366, 3374, "flow_branch_label"),
        (76, 227, 242, "flow_branch_label"),
        (76, 407, 416, "flow_branch_label"),
        (76, 574, 589, "flow_branch_label"),
        (76, 1210, 1215, "flow_branch_label"),
        (76, 1346, 1356, "flow_branch_label"),
        (76, 2167, 2187, "flow_branch_label"),
        (95, 167, 211, "flow_branch_label"),
        (79, 152, 247, "field_purpose_prompt"),
    }
    replacements = [
        replacement
        for replacement in replacements
        if replacement[0] not in out_of_scope_pages
        and not any(
            replacement[0] == other_page
            and replacement[3] == other_kind
            and replacement[1] < other_end
            and other_start < replacement[2]
            for other_page, other_start, other_end, other_kind in (
                reviewed_false_occurrences
            )
        )
    ]

    replacement_regions = [
        (page, start, end, kind)
        for page, start, end, kind, _note in replacements
    ]

    def overlaps_replacement(
        page: int, start: int, end: int, kind: str
    ) -> bool:
        return any(
            page == other_page
            and kind == other_kind
            and start < other_end
            and other_start < end
            for other_page, other_start, other_end, other_kind in replacement_regions
        )

    early_false_components = {
        (27, 3241, 3251),
        (29, 2064, 2070),
        (61, 883, 895),
    }
    false_detected = {
        (84, 313, 321, "remuneration_component_anchor"),
        (85, 1614, 1619, "remuneration_component_anchor"),
        (86, 308, 316, "remuneration_component_anchor"),
        (89, 2380, 2425, "remuneration_component_anchor"),
        (93, 243, 251, "business_aggregate_anchor"),
        (115, 1033, 1054, "business_aggregate_anchor"),
        (128, 989, 993, "role_anchor"),
        (84, 2531, 2591, "field_purpose_prompt"),
        (84, 3368, 3428, "field_purpose_prompt"),
        (86, 2520, 2580, "field_purpose_prompt"),
        (86, 3354, 3418, "field_purpose_prompt"),
        (87, 239, 295, "field_purpose_prompt"),
        (87, 644, 705, "flow_branch_label"),
        (89, 1956, 2008, "field_purpose_prompt"),
        (93, 1137, 1189, "field_purpose_prompt"),
        (79, 152, 247, "field_purpose_prompt"),
        (89, 405, 504, "field_purpose_prompt"),
        (94, 3, 30, "field_purpose_prompt"),
        (107, 859, 955, "repeat_or_alias_instruction"),
        (87, 816, 922, "repeat_or_alias_instruction"),
        (89, 3807, 3873, "repeat_or_alias_instruction"),
        (92, 994, 1043, "repeat_or_alias_instruction"),
        (92, 987, 1073, "repeat_or_alias_instruction"),
        (93, 782, 851, "repeat_or_alias_instruction"),
        (114, 193, 259, "field_purpose_prompt"),
        (114, 1719, 1792, "field_purpose_prompt"),
        (50, 182, 243, "field_purpose_prompt"),
        (24, 1664, 1749, "context_anchor"),
        (40, 788, 884, "context_anchor"),
        (44, 2104, 2184, "context_anchor"),
        (52, 2232, 2308, "context_anchor"),
        (72, 1614, 1698, "context_anchor"),
        (74, 874, 967, "context_anchor"),
        (23, 546, 581, "flow_branch_label"),
        (34, 1516, 1556, "flow_branch_label"),
        (34, 1922, 2002, "flow_branch_label"),
        (51, 672, 762, "flow_branch_label"),
        (51, 1233, 1318, "flow_branch_label"),
        (77, 782, 862, "flow_branch_label"),
        (77, 863, 948, "flow_branch_label"),
        (115, 321, 418, "flow_branch_label"),
        (115, 705, 799, "flow_branch_label"),
        (118, 894, 945, "flow_branch_label"),
        (118, 894, 945, "repeat_or_alias_instruction"),
        (118, 1992, 2079, "flow_branch_label"),
        (118, 1992, 2079, "repeat_or_alias_instruction"),
        (120, 993, 1044, "flow_branch_label"),
        (120, 993, 1044, "repeat_or_alias_instruction"),
        (120, 1866, 1953, "flow_branch_label"),
        (120, 1866, 1953, "repeat_or_alias_instruction"),
        (122, 1326, 1363, "field_purpose_prompt"),
        (122, 5001, 5036, "field_purpose_prompt"),
        (129, 850, 880, "field_purpose_prompt"),
    }
    false_detected.update(reviewed_false_occurrences)

    route_repeat_only_pages = {118, 119, 120, 121, 126, 127, 130}
    manual_only_pages = {125, 232, 233, 266, 278, 279, 280, 281, 282, 283}

    def overlaps_reviewed_false(
        page: int, start: int, end: int, kind: str
    ) -> bool:
        return any(
            page == other_page
            and kind == other_kind
            and start < other_end
            and other_start < end
            for other_page, other_start, other_end, other_kind in (
                reviewed_false_occurrences
            )
        )

    def keep_detected(row: dict[str, Any]) -> bool:
        page = row["page_number"]
        start = row["utf8_byte_start"]
        end = row["utf8_byte_end"]
        kind = row["occurrence_kind_candidate"]
        if not inside(page, start, end):
            return False
        if page in manual_only_pages:
            return False
        if page in route_repeat_only_pages and kind not in {
            "flow_branch_label",
            "repeat_or_alias_instruction",
        }:
            return False
        if overlaps_replacement(page, start, end, kind):
            return False
        if page <= 83 and kind in {
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
            "role_total_anchor",
        }:
            return False
        if page <= 83 and kind == "repeat_or_alias_instruction":
            return False
        if page <= 83 and kind == "flow_branch_label":
            upper = row["matched_text"].upper()
            compact = " ".join(upper.split())
            if "IF VOLUNTEERED" in upper or "GET DAY IF VOLUNTEERED" in upper:
                return False
            if "IF NECESSARY" in upper and "IF NO EMPLOYER" not in upper:
                return False
            if "INTERVIEWER CHECKPOINT" in upper:
                return False
            if compact in {"GO TO", "TURN TO"}:
                return False
            if (page, start) in {(27, 798), (27, 1141)}:
                return False
        if (
            kind == "flow_branch_label"
            and "INTERVIEWER CHECKPOINT" in row["matched_text"].upper()
        ):
            return False
        if (
            kind == "remuneration_component_anchor"
            and (page, start, end) in early_false_components
        ):
            return False
        if (
            page,
            start,
            end,
            kind,
        ) in false_detected or overlaps_reviewed_false(page, start, end, kind):
            return False
        if (
            page == 123
            and kind == "repeat_or_alias_instruction"
            and start == 1188
        ):
            return False
        if (
            page == 87
            and kind == "repeat_or_alias_instruction"
            and start == 343
        ):
            return False
        if page == 85 and kind == "role_total_anchor":
            return False
        if page == 92 and kind == "business_aggregate_anchor" and start == 259:
            return False
        if (
            page == 93
            and kind == "business_aggregate_anchor"
            and start in {115, 147, 359}
        ):
            return False
        return True

    detected_rows: list[dict[str, Any]] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        detected, _line_count = (
            annotation.stage1_candidates.detect_page_candidates(
                page_text,
                source_document_id=source_document_id,
                interview_wave=interview_wave,
                page_number=page_number,
            )
        )
        detected_rows.extend(row for row in detected if keep_detected(row))

    for row in detected_rows:
        add(
            row["page_number"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            row["occurrence_kind_candidate"],
            note="Reviewer-approved atom independently re-derived from source bytes.",
        )

    for page, start, end, kind, note in replacements:
        add(page, start, end, kind, note=note)

    # Source-visible role forms missed by the stage-1 singular-role detector.
    manual_roles = [
        (23, 1230, 1235),
        (41, 1226, 1231),
        (41, 1772, 1777),
        (41, 2180, 2185),
        (41, 2276, 2281),
        (41, 2512, 2517),
        (49, 605, 610),
        (51, 587, 592),
        (51, 604, 609),
        (51, 611, 616),
        (58, 108, 113),
        (59, 991, 996),
        (59, 1040, 1045),
        (59, 1085, 1090),
        (65, 818, 823),
        (65, 985, 990),
        (71, 185, 190),
        (77, 908, 913),
        (77, 923, 928),
    ]
    for page, start, end in manual_roles:
        add(
            page,
            start,
            end,
            "role_anchor",
            note="Plural role lexeme manually recovered from exact source bytes.",
        )

    manual_anchors = [
        (84, 2389, 2398, "job_anchor"),
        (84, 3200, 3209, "job_anchor"),
        (86, 2386, 2395, "job_anchor"),
        (86, 3194, 3203, "job_anchor"),
        (84, 630, 638, "remuneration_component_anchor"),
        (84, 644, 651, "farm_aggregate_anchor"),
        (84, 813, 831, "remuneration_component_anchor"),
        (84, 993, 1003, "remuneration_component_anchor"),
        (84, 1009, 1016, "farm_aggregate_anchor"),
        (88, 2290, 2302, "remuneration_component_anchor"),
        (88, 2804, 2816, "remuneration_component_anchor"),
        (88, 3408, 3420, "remuneration_component_anchor"),
        (90, 352, 358, "remuneration_component_anchor"),
        (92, 259, 280, "remuneration_component_anchor"),
        (92, 284, 289, "remuneration_component_anchor"),
        (92, 1107, 1114, "remuneration_component_anchor"),
        (92, 1118, 1134, "remuneration_component_anchor"),
        (92, 1832, 1851, "remuneration_component_anchor"),
        (93, 115, 136, "remuneration_component_anchor"),
        (93, 343, 348, "remuneration_component_anchor"),
        (93, 693, 700, "remuneration_component_anchor"),
        (93, 704, 720, "remuneration_component_anchor"),
        (93, 1245, 1264, "remuneration_component_anchor"),
        (128, 1373, 1377, "remuneration_component_anchor"),
        (128, 1420, 1429, "remuneration_component_anchor"),
        (128, 2273, 2284, "job_anchor"),
        (131, 225, 237, "remuneration_component_anchor"),
        (115, 1033, 1054, "remuneration_component_anchor"),
        (232, 579, 583, "role_anchor"),
        (232, 584, 590, "role_anchor"),
        (232, 686, 690, "role_anchor"),
        (232, 754, 767, "job_anchor"),
        (232, 1258, 1262, "role_anchor"),
        (232, 1263, 1269, "role_anchor"),
        (232, 1344, 1357, "job_anchor"),
        (233, 519, 523, "role_anchor"),
        (233, 524, 528, "role_anchor"),
        (233, 529, 535, "role_anchor"),
        (233, 666, 670, "role_anchor"),
        (233, 875, 879, "role_anchor"),
        (233, 880, 886, "role_anchor"),
        (266, 433, 437, "role_anchor"),
        (266, 488, 492, "role_anchor"),
        (266, 496, 502, "role_anchor"),
        (278, 1088, 1092, "role_anchor"),
        (278, 1093, 1099, "role_anchor"),
        (279, 671, 675, "role_anchor"),
        (279, 676, 682, "role_anchor"),
        (280, 1545, 1551, "role_anchor"),
        (280, 1553, 1580, "job_anchor"),
        (280, 452, 456, "role_anchor"),
        (281, 1518, 1522, "role_anchor"),
        (281, 1560, 1564, "role_anchor"),
        (281, 1769, 1773, "role_anchor"),
        (281, 1907, 1911, "role_anchor"),
        (282, 761, 765, "role_anchor"),
        (282, 841, 861, "job_anchor"),
        (282, 952, 956, "role_anchor"),
        (282, 975, 980, "job_anchor"),
        (283, 694, 698, "role_anchor"),
        (283, 1090, 1094, "role_anchor"),
        (283, 1156, 1160, "role_anchor"),
        (283, 1162, 1166, "role_anchor"),
        (283, 1300, 1304, "role_anchor"),
    ]
    for page, start, end, kind in manual_anchors:
        if page in out_of_scope_pages or overlaps_reviewed_false(
            page, start, end, kind
        ):
            continue
        add(
            page,
            start,
            end,
            kind,
            note="Anchor span manually corrected or added from exact source bytes.",
        )

    # Exact atoms in the narrow p79 boundary that must survive even when a
    # generic lexical detector does not emit the source form.
    for page, start, end in [
        (79, 219, 223),
        (79, 227, 231),
        (79, 232, 238),
        (79, 401, 405),
        (79, 442, 446),
        (79, 447, 453),
    ]:
        add(
            page,
            start,
            end,
            "role_anchor",
            note="Exact source-local role anchor.",
        )

    p22_b1_categories = (
        (22, 506, 520),
        (22, 798, 811),
        (22, 1170, 1182),
        (22, 1749, 1767),
        (22, 1839, 1853),
        (22, 1903, 1921),
    )
    p22_b3_yes = (22, 1292, 1300)
    p22_b4_entry_paths = ((),)
    p24_b4_self = (24, 207, 223)
    p24_b4_both = (24, 237, 257)
    p24_b4_someone = (24, 286, 300)
    p24_b4a_one = (24, 760, 773)
    p24_b4a_go_b5 = (24, 807, 815)
    p24_b4c_self = (24, 1443, 1464)
    p24_b4c_someone = (24, 1467, 1487)
    p24_b4c_go_b5 = (24, 1529, 1537)
    p24_b4c_go_b6 = (24, 1557, 1565)
    p24_b7_yes = (24, 2230, 2231)
    p24_b7_no = (24, 2247, 2261)
    p24_b8_yes = (24, 2404, 2414)
    p24_b5_paths = ((),)
    p24_b6_paths = ((),)

    p34_b12_salaried = (34, 203, 216)
    p34_b12_salary_commission = (34, 231, 241)
    p34_b12_hour_tips = (34, 264, 274)
    p34_b12_hour_commission = (34, 279, 289)
    p34_b12_other = (34, 295, 303)
    p34_b14_no = (34, 2080, 2111)
    p34_b14_yes = (34, 2123, 2124)
    p36_b17a_tips = (36, 445, 471)
    p36_b17a_commission = (36, 488, 592)
    p36_b17a_all_others = (36, 700, 714)
    p36_b17a_tips_paths = ((p36_b17a_tips,),)
    p36_b17a_commission_paths = ((p36_b17a_commission,),)
    p38_b22_someone = (38, 833, 886)
    p38_b22_others = (38, 941, 958)
    p38_b22_route = (38, 961, 975)
    p38_b22_someone_paths = ((p38_b22_someone,),)
    p38_b22_other_paths = ((p38_b22_others,),)

    p40_1993 = (40, 367, 373)
    p40_b25_yes = (40, 1203, 1212)
    p40_b30_1993 = (40, 1357, 1363)
    p40_b30_1994 = (40, 1480, 1486)
    p40_b31_1993 = (40, 1645, 1651)
    p40_b31_other = (40, 2104, 2121)
    p40_b32_yes = (40, 2581, 2582)
    p40_b32_no = (40, 2583, 2592)
    p40_b26_1993 = (40, 2647, 2656)
    p40_b26_1994 = (40, 2683, 2689)
    p40_b27_yes = (40, 2966, 2973)
    p40_b27_no = (40, 2974, 2986)
    p40_b30_paths = ((),)
    p40_b31_paths = ((),)
    p40_b32_paths = ((),)
    p40_b34_paths = ((),)

    p44_no_overlap = (44, 99, 112)
    p44_one_month = (44, 115, 159)
    p44_partial = (44, 209, 280)
    p44_all_months = (44, 354, 375)
    p44_go_b43 = (44, 619, 628)
    p44_partial_no = (44, 1498, 1525)
    p44_b43_self = (44, 1821, 1837)
    p44_b43_both = (44, 1847, 1867)
    p44_b43_someone = (44, 1882, 1897)
    p44_b43_entry_paths = ((),)
    p44_non_d_paths = tuple(
        (selector,)
        for selector in (p44_b43_self, p44_b43_both, p44_b43_someone)
    )
    p46_b46_no = (46, 593, 601)
    p46_b48_1993 = (46, 1218, 1224)
    p46_b48_other = (46, 1234, 1245)
    p46_b48_before = (46, 1255, 1266)
    p46_b48_unknown = (46, 1274, 1285)
    p46_b48_entry_paths = ((),)
    p48_b53_yes = (48, 509, 510)
    p48_b53_no = (48, 578, 584)
    p48_self = (48, 1186, 1206)
    p48_all_others = (48, 1240, 1254)
    p48_go_b57a = (48, 1942, 1952)
    p48_b59_yes = (48, 2300, 2310)
    p48_b59_no = (48, 2334, 2339)
    p48_b59_entry_paths = ((),)

    p52_no_overlap = (52, 287, 302)
    p52_one_month = (52, 305, 351)
    p52_partial = (52, 398, 466)
    p52_all_months = (52, 533, 557)
    p52_go_s43 = (52, 809, 818)
    p52_partial_no = (52, 1633, 1655)
    p52_s43_self = (52, 1985, 2001)
    p52_s43_both = (52, 2008, 2028)
    p52_s43_someone = (52, 2037, 2052)
    p52_s43_entry_paths = ((),)
    p52_non_d_paths = tuple(
        (selector,)
        for selector in (p52_s43_self, p52_s43_both, p52_s43_someone)
    )
    p54_s46_no = (54, 741, 749)
    p54_s48_1993 = (54, 1408, 1414)
    p54_s48_other = (54, 1424, 1435)
    p54_s48_before = (54, 1444, 1455)
    p54_s48_unknown = (54, 1461, 1472)
    p54_s48_entry_paths = ((),)
    p56_s53_yes = (56, 343, 344)
    p56_s53_no = (56, 364, 370)
    p56_self = (56, 1015, 1035)
    p56_all_others = (56, 1068, 1082)
    p56_go_s57a = (56, 1802, 1812)
    p56_s59_yes = (56, 2213, 2223)
    p56_s59_entry_paths = ((),)

    p60_b60_yes = (60, 1240, 1241)
    p60_b63_yes = (60, 1622, 1623)
    p60_b63_no = (60, 1684, 1743)
    p60_b66_no = (60, 2015, 2048)
    p60_b63_entry_paths = ((),)
    p60_b66_entry_paths = ((),)
    p62_b72_yes = (62, 728, 729)
    p62_b75_yes = (62, 1478, 1479)
    p62_b78_none = (62, 2287, 2415)
    p62_b78_none_go = (62, 2495, 2509)
    p62_b78_all = (62, 2630, 2647)
    p62_b78_reconcile = (62, 2653, 2734)
    p62_b69_entry_paths = ((),)
    p62_b72_entry_paths = ((),)
    p62_b75_entry_paths = ((),)
    p62_b78_entry_paths = ((),)
    p68_c1_yes = (68, 179, 180)
    p68_c4_entry_paths = ((),)
    p70_c4_go = (70, 198, 203)
    p70_c5_1993 = (70, 451, 457)
    p70_c5_1994 = (70, 464, 470)
    p70_c5_1993_or_1994 = (70, 473, 490)
    p70_c5_other = (70, 498, 509)
    p70_c5_before = (70, 522, 538)
    p70_c5_unknown = (70, 551, 562)
    p70_c6_yes = (70, 835, 838)
    p70_c6_no = (70, 932, 939)
    p70_c6_terminal = (70, 1071, 1109)
    p70_c7_all = (70, 1187, 1196)
    p70_c8_terminal = (70, 1584, 1609)
    p70_c6_entry_paths = ((),)
    p70_c9_paths = ((),)

    p64_multiple_jobs = (64, 635, 665)
    p64_all_others = (64, 681, 693)
    p64_go_b82 = (64, 747, 757)
    p64_b80_no = (64, 287, 319)
    p62_b78_all_paths = ((p62_b78_all,),)
    p64_b79_entry_paths = ((p62_b78_all,),)
    p64_b81a_entry_paths = ((p62_b78_all,),)
    p64_b82_entry_paths = ((),)
    p64_b82_no = (64, 1513, 1554)
    p66_missing_employer = (66, 323, 439)
    p66_b92_no = (66, 1556, 1586)

    p71_work_history = (71, 243, 735)
    p72_self = (72, 112, 128)
    p72_both = (72, 143, 163)
    p72_someone = (72, 193, 208)
    p72_one_job = (72, 581, 593)
    p72_two_jobs = (72, 599, 610)
    p72_one_go_c13 = (72, 647, 656)
    p72_c12c_self = (72, 1318, 1341)
    p72_c12c_someone = (72, 1414, 1432)
    p72_c12c_go_c13 = (72, 1472, 1481)
    p72_c12c_go_c14 = (72, 1502, 1511)
    p72_missing_employer = (72, 2349, 2458)
    p72_c12_entry_paths = ((),)
    p72_c13_paths = (
        tuple(path + (p72_self,) for path in p72_c12_entry_paths)
        + tuple(
            path + (p72_both, p72_one_job, p72_one_go_c13)
            for path in p72_c12_entry_paths
        )
        + tuple(
            path
            + (
                p72_both,
                p72_two_jobs,
                p72_c12c_self,
                p72_c12c_go_c13,
            )
            for path in p72_c12_entry_paths
        )
    )
    p72_c14_paths = tuple(
        path + (p72_someone,) for path in p72_c12_entry_paths
    ) + tuple(
        path
        + (
            p72_both,
            p72_two_jobs,
            p72_c12c_someone,
            p72_c12c_go_c14,
        )
        for path in p72_c12_entry_paths
    )
    p72_c13_unincorporated = (72, 1727, 1746)
    p72_c13_corporation = (72, 1924, 1939)
    p72_c13_go_c14a = (72, 2014, 2026)
    p72_c14_categories = (
        (72, 1765, 1775),
        (72, 1781, 1789),
        (72, 1796, 1804),
        (72, 1808, 1818),
        (72, 1986, 2005),
    )
    p72_c14a_paths = ((),)

    p74_1993 = (74, 456, 462)
    p74_1994 = (74, 473, 478)
    p74_1993_or_1994 = (74, 481, 498)
    p74_other_year = (74, 506, 517)
    p74_before_1993 = (74, 523, 539)
    p74_unknown_year = (74, 547, 558)
    p74_c17_yes = (74, 1273, 1281)
    p74_c17_no = (74, 1288, 1295)
    p74_c22_1993 = (74, 1409, 1415)
    p74_c22_1994 = (74, 1423, 1429)
    p74_c23_1993 = (74, 1441, 1447)
    p74_c23_1994 = (74, 1451, 1457)
    p74_c23_other = (74, 1462, 1473)
    p74_c22_go_c32 = (74, 1607, 1621)
    p74_c23_go_c31 = (74, 1736, 1750)
    p74_c24_no = (74, 2095, 2102)
    p74_c16_entry_paths = ((),)
    p74_c22_paths = ((),)
    p74_c23_paths = ((),)
    p74_c18_1993_route = (74, 2158, 2168)
    p74_c18_1994 = (74, 2192, 2197)
    p74_c19_yes = (74, 2478, 2479)
    p74_c19_no = (74, 2492, 2499)
    p74_c26_promotion = (74, 2945, 2975)
    p74_c26_major_change = (74, 3054, 3098)
    p74_c26_other = (74, 3235, 3254)
    p74_c21_promotion = (74, 3258, 3288)
    p74_c21_major_change = (74, 3294, 3311)
    p74_c21_other = (74, 3320, 3339)
    p74_c21_terminal = (74, 3391, 3405)
    p74_c26_terminal = (74, 3443, 3457)
    p74_c18_paths = tuple(
        path + (p74_1993, p74_c17_no) for path in p74_c16_entry_paths
    )
    p74_c24_paths = tuple(path + (p74_c23_1994,) for path in p74_c23_paths)
    p74_c21_paths = ((),)
    p74_c26_paths = ((),)

    p76_head_male = (76, 265, 281)
    p76_wife = (76, 506, 532)
    p76_no_wife = (76, 539, 567)
    p76_working = (76, 919, 936)
    p76_temporary = (76, 938, 1027)
    p76_unemployed = (76, 1110, 1124)
    p76_go_d4 = (76, 1233, 1246)
    p76_retired = (76, 1368, 1389)
    p76_disabled = (76, 1746, 1797)
    p76_d3_yes = (76, 1811, 1818)
    p76_d3_yes_go = (76, 1892, 1902)
    p76_d3_no_go = (76, 2084, 2091)
    p76_keeping_house = (76, 2296, 2377)
    p76_student = (76, 2392, 2442)
    p76_other = (76, 2455, 2507)
    p76_d3_entry_paths = ((),)

    p79_roomers = (79, 160, 203)
    p232_no_help = (232, 212, 276)
    p232_all_others = (232, 334, 348)
    p232_wife_in_fu = (232, 1091, 1112)
    p266_new_wife = (266, 426, 440)
    p266_wife = (266, 485, 502)
    p280_new_head = (280, 445, 456)
    p278_years = (278, 1143, 1159)
    p27_road = (27, 1635, 1672)
    p27_foreman = (27, 1730, 1777)
    p27_operative = (27, 1799, 1847)
    p27_laborer = (27, 1852, 1918)
    p39_ads = (39, 586, 706)
    p39_no_ad = (39, 707, 775)
    p43_present_1993 = (43, 1415, 1648)
    p63_unemployed_vacation = (63, 1259, 1394)
    p63_earned_then_laid_off = (63, 1400, 1465)
    p63_if_so = (63, 1466, 1546)
    p63_layoff_first = (63, 1547, 1679)
    p84_farmer = (84, 431, 466)
    p84_all_others = (84, 489, 508)
    p84_go_g5 = (84, 583, 591)
    p84_g5_yes = (84, 1261, 1269)
    p84_g5_no = (84, 1304, 1334)
    p84_g9a_yes = (84, 2277, 2287)
    p84_g9a_no = (84, 2301, 2328)
    p84_g9b_reported = (84, 2434, 2458)
    p84_g9b_unreported = (84, 2478, 2501)
    p84_go_g9bb = (84, 2624, 2634)
    p84_g9b_supplement = (84, 2658, 2687)
    p84_wife = (84, 2795, 2814)
    p84_g9bb_other_route = (84, 2822, 2837)
    p84_g9c_yes = (84, 3054, 3062)
    p84_g9c_no = (84, 3080, 3110)
    p84_g9d_reported = (84, 3258, 3282)
    p84_g9d_unreported = (84, 3302, 3325)
    p84_g9d_next = (84, 3471, 3485)
    p84_g9d_supplement = (84, 3509, 3538)
    p84_g5_parent_paths = ((),)
    p84_g5_yes_paths = ((p84_g5_yes,),)
    p84_g9bb_entry_paths = ((p84_g5_yes,),)
    p84_g10_entry_paths = ((p84_g5_yes,),)
    p86_farmer = (86, 418, 452)
    p86_all_others = (86, 472, 491)
    p86_go_g5 = (86, 562, 570)
    p86_g5_yes = (86, 1231, 1239)
    p86_g5_no = (86, 1278, 1308)
    p86_g9a_yes = (86, 2222, 2232)
    p86_g9a_no = (86, 2243, 2272)
    p86_g9b_reported = (86, 2427, 2451)
    p86_g9b_unreported = (86, 2471, 2494)
    p86_go_g9bb = (86, 2609, 2619)
    p86_g9b_supplement = (86, 2643, 2672)
    p86_wife = (86, 2777, 2796)
    p86_g9bb_other_route = (86, 2804, 2853)
    p86_g9c_yes = (86, 3060, 3068)
    p86_g9c_no = (86, 3086, 3116)
    p86_g9d_reported = (86, 3246, 3270)
    p86_g9d_unreported = (86, 3294, 3317)
    p86_g9d_next = (86, 3455, 3469)
    p86_g9d_supplement = (86, 3497, 3526)
    p86_g5_parent_paths = ((),)
    p86_g5_yes_paths = ((p86_g5_yes,),)
    p86_g9bb_entry_paths = ((p86_g5_yes,),)
    p86_g10_entry_paths = ((p86_g5_yes,),)
    p88_business_form_entry_paths = p84_g10_entry_paths
    p90_business_form_entry_paths = p86_g10_entry_paths
    p88_unincorporated = (88, 95, 112)
    p88_other = (88, 125, 144)
    p88_corporation = (88, 70, 84)
    p88_corporation_go = (88, 161, 170)
    p88_profit = (88, 343, 353)
    p88_loss = (88, 407, 414)
    p88_broke_even = (88, 510, 523)
    p88_broke_go = (88, 621, 630)
    p88_one_business = (88, 1272, 1289)
    p88_multiple_businesses = (88, 1311, 1409)
    p88_repeat_business = (88, 1540, 1584)
    p88_g12_no = (88, 1930, 1942)
    p88_g12_instruction = (88, 1737, 1866)
    p88_g16_to_g16a = (88, 2639, 2649)
    p88_g16_to_g18 = (88, 2654, 2668)
    p88_g14_yes = (88, 2837, 2844)
    p88_g14_no = (88, 2857, 2863)
    p88_g14_yes_route = (88, 2881, 2891)
    p88_g14_no_route = (88, 2899, 2909)
    p88_g17_reported = (88, 3549, 3588)
    p88_g17_unreported = (88, 3589, 3631)
    p88_g17_supplement = (88, 3706, 3735)
    p90_unincorporated = (90, 95, 112)
    p90_other = (90, 126, 145)
    p90_corporation = (90, 70, 84)
    p90_corporation_go = (90, 162, 171)
    p90_profit = (90, 348, 359)
    p90_broke_even = (90, 416, 432)
    p90_broke_go = (90, 531, 540)
    p90_one_business = (90, 1215, 1232)
    p90_multiple_businesses = (90, 1254, 1357)
    p90_repeat_business = (90, 1404, 1448)
    p90_g12_no = (90, 1795, 1802)
    p90_g12_instruction = (90, 1601, 1730)
    p90_g16_to_g16a = (90, 2527, 2537)
    p90_g16_to_g18 = (90, 2543, 2557)
    p90_g14_yes = (90, 2725, 2735)
    p90_g14_no = (90, 2787, 2796)
    p90_g14_yes_route = (90, 2814, 2824)
    p90_g14_no_route = (90, 2833, 2843)
    p90_g17_reported = (90, 3494, 3533)
    p90_g17_unreported = (90, 3547, 3589)
    p90_g17_supplement = (90, 3668, 3697)
    p88_owner_paths = tuple(
        path + (owner,)
        for path in p88_business_form_entry_paths
        for owner in (p88_unincorporated, p88_other)
    )
    p88_profit_paths = tuple(path + (p88_profit,) for path in p88_owner_paths)
    p88_loss_paths = tuple(path + (p88_loss,) for path in p88_owner_paths)
    p88_g11_result_paths = p88_profit_paths + p88_loss_paths
    p88_g12_entry_paths = ((),)
    p90_owner_paths = tuple(
        path + (owner,)
        for path in p90_business_form_entry_paths
        for owner in (p90_unincorporated, p90_other)
    )
    p90_profit_paths = tuple(path + (p90_profit,) for path in p90_owner_paths)
    # The loss response glyph is absent from the replay bytes on this form;
    # the owner-only arm is its source-order-preserving representation.
    p90_loss_paths = p90_owner_paths
    p90_g11_result_paths = p90_profit_paths + p90_loss_paths
    p90_g12_entry_paths = ((),)
    p88_g12_no_paths = ((p88_g12_no,),)
    p90_g12_no_paths = ((p90_g12_no,),)
    p88_g16a_entry_paths = (
        (p88_g12_no, p88_g16_to_g16a),
        (p88_g14_yes, p88_g14_yes_route),
    )
    p90_g16a_entry_paths = (
        (p90_g12_no, p90_g16_to_g16a),
        (p90_g14_yes, p90_g14_yes_route),
    )
    p88_g17e_entry_paths = p88_g16a_entry_paths + (
        (p88_g14_no, p88_g14_no_route),
    )
    p90_g17e_entry_paths = p90_g16a_entry_paths + (
        (p90_g14_no, p90_g14_no_route),
    )
    p92_g18a_no = (92, 323, 358)
    p92_g21a_reported = (92, 795, 834)
    p92_g21a_unreported = (92, 835, 877)
    p92_g21a_supplement = (92, 957, 986)
    p92_g18b_yes = (92, 1142, 1143)
    p92_g18b_no = (92, 1168, 1199)
    p92_g21b_reported = (92, 1578, 1616)
    p92_g21b_unreported = (92, 1617, 1661)
    p92_g21b_supplement = (92, 1740, 1769)
    p92_g18c_yes = (92, 1984, 1985)
    p92_g18c_no = (92, 2021, 2057)
    p92_g21c_reported = (92, 2436, 2475)
    p92_g21c_unreported = (92, 2476, 2518)
    p92_g21c_supplement = (92, 2596, 2625)
    p92_g18a_entry_paths = ((),)
    p92_g18b_entry_paths = ((),)
    p92_g18c_entry_paths = ((),)
    p92_g22_entry_paths = ((),)
    p94_extra_job = (94, 114, 137)
    p94_all_others = (94, 153, 184)
    p94_g23_no = (94, 330, 334)
    p94_g23_yes = (94, 407, 408)
    p106_wife = (106, 204, 228)
    p106_worked = (106, 640, 666)
    p106_all_others = (106, 685, 698)
    p106_all_others_go = (106, 790, 800)
    p106_worked_go = (106, 1283, 1293)
    p106_hours_reported = (106, 1757, 1794)
    p106_hours_unreported = (106, 1809, 1852)
    p106_hours_supplement = (106, 1930, 1959)
    p106_income_yes = (106, 2061, 2073)
    p106_income_other = (106, 2107, 2119)
    p106_g52_entry_paths = (
        (p106_wife,),
        (p106_wife, p106_worked),
    )
    p106_g52c_entry_paths = (
        (p106_wife, p106_all_others, p106_all_others_go),
        (p106_wife, p106_worked, p106_worked_go),
        (p106_wife, p106_hours_reported),
        (p106_wife, p106_hours_unreported, p106_hours_supplement),
        (p106_wife, p106_worked, p106_hours_reported),
        (
            p106_wife,
            p106_worked,
            p106_hours_unreported,
            p106_hours_supplement,
        ),
    )
    p107_business = (107, 317, 432)
    p107_included_business = (107, 434, 492)
    p107_if_known = (107, 589, 597)
    p107_missing_hours = (107, 875, 991)
    p114_g9b_business = (114, 575, 587)
    p114_g9d_business = (114, 594, 609)
    p114_g17e_wages = (114, 615, 626)
    p114_g21_other_work = (114, 638, 654)
    p114_g52b_wife_work = (114, 681, 697)
    p114_g21a = (114, 1013, 1031)
    p114_g21b = (114, 1224, 1237)
    p114_g21c = (114, 1388, 1414)
    p114_employer_categories = (
        (114, 1719, 1728),
        (114, 1731, 1738),
        (114, 1742, 1752),
        (114, 1753, 1762),
        (114, 1763, 1769),
        (114, 1774, 1792),
    )
    p114_left_gj1_paths = (
        (p114_g9b_business,),
        (p114_g9d_business,),
    )
    p114_right_gj1_paths = (
        (p114_g17e_wages,),
        (p114_g21_other_work, p114_g21a),
        (p114_g21_other_work, p114_g21b),
        (p114_g21_other_work, p114_g21c),
        (p114_g52b_wife_work,),
    )
    p114_gj2_entry_paths = ((),)
    p114_missing_employer = (114, 2341, 2454)
    p115_missing_hours = (115, 434, 609)
    p116_business_origin = (116, 89, 153)
    p116_all_origins = (116, 181, 193)
    p116_go_gj4 = (116, 239, 248)
    p116_stopped_yes = (116, 1291, 1298)
    p116_stopped_no = (116, 1306, 1315)
    p116_go_gj11 = (116, 1327, 1337)
    p116_return_g9b = (116, 2232, 2246)
    p116_return_g9d = (116, 2258, 2272)
    p116_return_g17e = (116, 2281, 2295)
    p116_return_g52b = (116, 2342, 2356)
    p116_terminal_g21a = (116, 2548, 2554)
    p116_terminal_g21b = (116, 2562, 2568)
    p116_terminal_g21c = (116, 2581, 2587)
    p116_return_g21a = (116, 2659, 2666)
    p116_return_g21b = (116, 2673, 2680)
    p116_return_g21c = (116, 2692, 2699)
    p116_gj4_entry_paths = ((),)
    p116_gj11_entry_paths = ((),)
    p117_business_supplement = (117, 101, 221)
    p119_multiple_ofums = (119, 2892, 3008)
    p122_not_deceased = (122, 1476, 1509)
    p122_job_one = (122, 3680, 3695)
    p122_job_two = (122, 3731, 3742)
    p122_job_three = (122, 3749, 3762)
    p122_job_four = (122, 3773, 3789)
    p122_job_none = (122, 3799, 3821)
    p122_g82_one = (122, 5094, 5116)
    p122_g82_other = (122, 5180, 5190)
    p128_young = (128, 208, 285)
    p128_work = (128, 1367, 1378)
    p130_more_people = (130, 2371, 2403)
    p130_supplement = (130, 2461, 2517)

    # Later-starting atoms that state the result, action, or interpretation of
    # a source-explicit local condition inherit that condition.  Exact-span
    # purpose rows are included here as dual classifications; flow rows with
    # the same coordinates remain independently rooted unless listed in the
    # nested-flow table below.
    direct_result_routes: dict[
        tuple[int, int, int],
        tuple[tuple[tuple[int, int, int], ...], ...],
    ] = {
        (22, 303, 320): (((22, 239, 293),),),
        (22, 331, 365): (((22, 239, 293),),),
        (22, 689, 699): (((22, 506, 520),),),
        (22, 798, 821): (((22, 798, 811),),),
        (22, 824, 848): (((22, 798, 811),),),
        (22, 885, 899): (((22, 798, 811),),),
        (22, 886, 890): (((22, 798, 811),),),
        (22, 1170, 1220): (((22, 1170, 1182),),),
        (22, 1749, 1831): (((22, 1749, 1767),),),
        (22, 1839, 1895): (((22, 1839, 1853),),),
        (23, 670, 734): (((23, 637, 758),),),
        (25, 305, 309): (((25, 302, 448),),),
        (25, 356, 364): (((25, 302, 448),),),
        (25, 397, 401): (((25, 302, 448),),),
        (25, 402, 407): (((25, 302, 448),),),
        (25, 439, 447): (((25, 302, 448),),),
        (27, 1638, 1642): (((27, 1635, 1672),),),
        (27, 2982, 2986): (((27, 2979, 3291),),),
        (27, 3117, 3121): (((27, 2979, 3291),),),
        (27, 3207, 3211): (((27, 2979, 3291),),),
        (29, 1198, 1438): (((29, 1198, 1438),),),
        (29, 1213, 1217): (((29, 1198, 1438),),),
        (29, 1597, 1672): (((29, 1597, 1672),),),
        (29, 1612, 1616): (((29, 1597, 1672),),),
        (30, 623, 779): (((30, 623, 779),),),
        (30, 632, 642): (((30, 623, 779),),),
        (30, 682, 685): (((30, 623, 779),),),
        (30, 719, 723): (((30, 623, 779),),),
        (30, 719, 779): (((30, 623, 779),),),
        (35, 718, 724): (((35, 688, 863),),),
        (35, 876, 880): (((35, 864, 977),),),
        (35, 897, 903): (((35, 864, 977),),),
        (35, 928, 936): (((35, 864, 977),),),
        (39, 1001, 1005): (((39, 994, 1098),),),
        (39, 1020, 1098): (((39, 994, 1098),),),
        (39, 1048, 1066): (((39, 994, 1098),),),
        (41, 1760, 2262): (((41, 1760, 2262),),),
        (41, 1772, 1777): (((41, 1760, 2262),),),
        (41, 1871, 1879): (((41, 1760, 2262),),),
        (41, 2006, 2020): (((41, 1760, 2262),),),
        (41, 2107, 2115): (((41, 1760, 2262),),),
        (41, 2149, 2233): (((41, 1760, 2262),),),
        (41, 2180, 2185): (((41, 1760, 2262),),),
        (41, 2263, 2498): (((41, 2263, 2498),),),
        (41, 2276, 2281): (((41, 2263, 2498),),),
        (41, 2387, 2403): (((41, 2263, 2498),),),
        (41, 2461, 2465): (((41, 2263, 2498),),),
        (41, 2474, 2487): (((41, 2263, 2498),),),
        (41, 2488, 2497): (((41, 2263, 2498),),),
        (41, 2500, 2753): (((41, 2500, 2753),),),
        (41, 2512, 2517): (((41, 2500, 2753),),),
        (41, 2607, 2623): (((41, 2500, 2753),),),
        (41, 2640, 2660): (((41, 2500, 2753),),),
        (42, 904, 917): (((42, 887, 963),),),
        (42, 904, 963): (((42, 887, 963),),),
        (42, 923, 931): (((42, 887, 963),),),
        (42, 954, 962): (((42, 887, 963),),),
        (42, 1315, 1324): (((42, 1271, 1417),),),
        (42, 1402, 1410): (((42, 1271, 1417),),),
        (43, 727, 731): (((43, 724, 988),),),
        (43, 760, 773): (((43, 724, 988),),),
        (43, 779, 787): (((43, 724, 988),),),
        (43, 803, 812): (((43, 724, 988),),),
        (43, 823, 907): (((43, 724, 988),),),
        (43, 837, 845): (((43, 724, 988),),),
        (43, 868, 877): (((43, 724, 988),),),
        (43, 946, 955): (((43, 724, 988),),),
        (43, 989, 1130): (((43, 989, 1130),),),
        (43, 1014, 1018): (((43, 989, 1130),),),
        (43, 1034, 1042): (((43, 989, 1130),),),
        (43, 1043, 1051): (((43, 989, 1130),),),
        (43, 1140, 1405): (((43, 1140, 1405),),),
        (43, 1143, 1147): (((43, 1140, 1405),),),
        (43, 1169, 1185): (((43, 1140, 1405),),),
        (43, 1265, 1281): (((43, 1140, 1405),),),
        (43, 1282, 1286): (((43, 1140, 1405),),),
        (43, 1395, 1404): (((43, 1140, 1405),),),
        (43, 1415, 1648): (((43, 1415, 1648),),),
        (43, 1658, 1892): (((43, 1658, 1892),),),
        (43, 1661, 1667): (((43, 1658, 1892),),),
        (43, 1691, 1707): (((43, 1658, 1892),),),
        (43, 1775, 1778): (((43, 1658, 1892),),),
        (43, 1779, 1788): (((43, 1658, 1892),),),
        (43, 1794, 1798): (((43, 1658, 1892),),),
        (43, 1875, 1891): (((43, 1658, 1892),),),
        (45, 333, 337): (((45, 248, 569),),),
        (45, 359, 363): (((45, 248, 569),),),
        (45, 386, 395): (((45, 248, 569),),),
        (45, 396, 400): (((45, 248, 569),),),
        (45, 431, 439): (((45, 248, 569),),),
        (45, 462, 471): (((45, 248, 569),),),
        (45, 478, 487): (((45, 248, 569),),),
        (45, 522, 531): (((45, 248, 569),),),
        (45, 634, 637): (((45, 581, 769),),),
        (45, 686, 695): (((45, 581, 769),),),
        (45, 728, 737): (((45, 581, 769),),),
        (49, 411, 415): (((49, 403, 532),),),
        (49, 428, 441): (((49, 403, 532),),),
        (49, 511, 520): (((49, 403, 532),),),
        (49, 880, 884): (((49, 877, 1069),),),
        (49, 904, 907): (((49, 877, 1069),),),
        (49, 908, 917): (((49, 877, 1069),),),
        (49, 1004, 1023): (((49, 877, 1069),),),
        (49, 1024, 1032): (((49, 877, 1069),),),
        (50, 738, 825): (((50, 702, 849),),),
        (50, 747, 756): (((50, 702, 849),),),
        (50, 834, 842): (((50, 702, 849),),),
        (50, 1160, 1168): (((50, 1147, 1246),),),
        (50, 1210, 1213): (((50, 1147, 1246),),),
        (51, 274, 286): (((51, 239, 482),),),
        (51, 287, 296): (((51, 239, 482),),),
        (51, 379, 398): (((51, 239, 482),),),
        (51, 441, 449): (((51, 239, 482),),),
        (51, 450, 459): (((51, 239, 482),),),
        (55, 160, 164): (((55, 157, 309),),),
        (55, 165, 169): (((55, 157, 309),),),
        (55, 170, 176): (((55, 157, 309),),),
        (55, 191, 203): (((55, 157, 309),),),
        (55, 227, 240): (((55, 157, 309),),),
        (59, 1429, 1433): (((59, 1426, 1591),),),
        (59, 1449, 1452): (((59, 1426, 1591),),),
        (65, 381, 515): (((65, 381, 515),),),
        (76, 919, 936): ((p76_head_male, p76_wife, p76_working),),
        (76, 938, 972): ((p76_head_male, p76_wife),),
        (76, 1368, 1389): ((p76_head_male, p76_wife, p76_retired),),
        (76, 1746, 1797): ((p76_head_male, p76_wife, p76_disabled),),
        (76, 1811, 1818): ((p76_d3_yes,),),
        p84_g9b_reported: tuple(
            path + (p84_g9a_yes, p84_g9b_reported) for path in p84_g5_yes_paths
        ),
        p84_g9b_unreported: tuple(
            path + (p84_g9a_yes, p84_g9b_unreported)
            for path in p84_g5_yes_paths
        ),
        p84_g9d_reported: tuple(
            path + (p84_wife, p84_g9c_yes, p84_g9d_reported)
            for path in p84_g9bb_entry_paths
        ),
        p84_g9d_unreported: tuple(
            path + (p84_wife, p84_g9c_yes, p84_g9d_unreported)
            for path in p84_g9bb_entry_paths
        ),
        p86_g9b_reported: tuple(
            path + (p86_g9a_yes, p86_g9b_reported) for path in p86_g5_yes_paths
        ),
        p86_g9b_unreported: tuple(
            path + (p86_g9a_yes, p86_g9b_unreported)
            for path in p86_g5_yes_paths
        ),
        p86_g9d_reported: tuple(
            path + (p86_wife, p86_g9c_yes, p86_g9d_reported)
            for path in p86_g9bb_entry_paths
        ),
        p86_g9d_unreported: tuple(
            path + (p86_wife, p86_g9c_yes, p86_g9d_unreported)
            for path in p86_g9bb_entry_paths
        ),
        p88_g17_reported: tuple(
            path + (p88_g17_reported,) for path in p88_g17e_entry_paths
        ),
        p88_g17_unreported: tuple(
            path + (p88_g17_unreported,) for path in p88_g17e_entry_paths
        ),
        p90_g17_reported: tuple(
            path + (p90_g17_reported,) for path in p90_g17e_entry_paths
        ),
        p90_g17_unreported: tuple(
            path + (p90_g17_unreported,) for path in p90_g17e_entry_paths
        ),
        (91, 108, 226): (((91, 108, 226),),),
        p92_g21a_reported: ((p92_g21a_reported,),),
        p92_g21a_unreported: ((p92_g21a_unreported,),),
        p92_g21b_reported: ((p92_g18b_yes, p92_g21b_reported),),
        p92_g21b_unreported: ((p92_g18b_yes, p92_g21b_unreported),),
        p92_g21c_reported: ((p92_g18c_yes, p92_g21c_reported),),
        p92_g21c_unreported: ((p92_g18c_yes, p92_g21c_unreported),),
        (115, 1213, 1339): (((115, 1213, 1339),),),
    }
    for row in specs.values():
        page = row["page"]
        start = row["start"]
        key = (page, start, row["end"])
        if row["kind"] != "flow_branch_label" and key in direct_result_routes:
            row["routes"] = set(direct_result_routes[key])
        elif page == 24:
            b4_parent_paths = p22_b4_entry_paths
            if key == (24, 764, 771):
                row["routes"] = {
                    path + (p24_b4_both, p24_b4a_one)
                    for path in b4_parent_paths
                }
            elif 103 <= start < 207:
                row["routes"] = set(b4_parent_paths)
            elif key == (24, 510, 725):
                row["routes"] = {
                    path + (p24_b4_both,) for path in b4_parent_paths
                }
            elif key == (24, 546, 553):
                row["routes"] = {
                    path + (p24_b4_both,) for path in b4_parent_paths
                }
            elif 594 <= start < 817:
                row["routes"] = {
                    path + (p24_b4_both,) for path in b4_parent_paths
                }
            elif 817 <= start < 1411:
                row["routes"] = {
                    path + (p24_b4_both,) for path in b4_parent_paths
                }
            elif key in {
                (24, 1569, 1592),
                (24, 1664, 1683),
                (24, 1755, 1769),
            }:
                row["routes"] = set(p24_b5_paths)
            elif 2312 <= start < 2404:
                row["routes"] = {path + (p24_b7_yes,) for path in p24_b6_paths}
            elif (
                key
                in {
                    (24, 1609, 1658),
                    (24, 1704, 1749),
                }
                or start >= 2125
            ):
                row["routes"] = set(p24_b6_paths)
        elif page == 26 and key in {(26, 433, 441), (26, 482, 485)}:
            row["routes"] = {((26, 420, 520),)}
        elif page == 28 and key in {(28, 436, 444), (28, 485, 488)}:
            row["routes"] = {((28, 423, 523),)}
        elif page == 32 and key in {(32, 435, 443), (32, 484, 487)}:
            row["routes"] = {((32, 422, 522),)}
        elif page == 33 and key in {(33, 487, 495), (33, 552, 555)}:
            row["routes"] = {((33, 443, 617),)}
        elif page == 34:
            if key in {(34, 234, 240), (34, 335, 345)}:
                row["routes"] = {(p34_b12_salary_commission,)}
            elif key == (34, 369, 373):
                row["routes"] = {(p34_b12_hour_tips,)}
            elif key == (34, 383, 393):
                row["routes"] = {(p34_b12_hour_commission,)}
            elif 684 <= start < 1844:
                row["routes"] = {(p34_b12_other,)}
            elif key in {p34_b14_no, p34_b14_yes}:
                row["routes"] = {
                    (p34_b12_salaried,),
                    (p34_b12_salary_commission,),
                }
            elif 2136 <= start:
                row["routes"] = {
                    (p34_b12_salaried, p34_b14_yes),
                    (p34_b12_salary_commission, p34_b14_yes),
                }
            elif 1844 <= start:
                row["routes"] = {
                    (p34_b12_salaried,),
                    (p34_b12_salary_commission,),
                }
        elif page == 36:
            b16_paths = {()}
            if key == (36, 455, 459):
                row["routes"] = set(p36_b17a_tips_paths)
            elif key in {
                (36, 489, 495),
                (36, 498, 508),
                (36, 570, 580),
            }:
                row["routes"] = set(p36_b17a_commission_paths)
            elif start < 354:
                row["routes"] = b16_paths
            elif (
                key
                in {
                    (36, 743, 775),
                    (36, 842, 850),
                }
                or 714 < start < 798
            ):
                row["routes"] = set(p36_b17a_tips_paths)
            elif (
                key
                in {
                    (36, 798, 835),
                    (36, 897, 905),
                }
                or 850 <= start
            ):
                row["routes"] = set(p36_b17a_commission_paths)
        elif page == 38:
            if key == (38, 836, 840) or 992 <= start < 1190:
                row["routes"] = set(p38_b22_someone_paths)
        elif page == 40:
            b25_starts = {680, 788, 892, 993, 1097}
            b30_starts = {715, 823, 927, 1028}
            b31_starts = {753, 866, 970, 1071, 1175}
            if start in b25_starts or 1192 <= start < 1357:
                row["routes"] = {(p40_1993,)}
            elif start in b30_starts:
                row["routes"] = set(p40_b30_paths)
            elif start in b31_starts:
                row["routes"] = set(p40_b31_paths)
            elif 2232 <= start < 2693:
                if start in {2286, 2392, 2488}:
                    row["routes"] = set(p40_b32_paths)
                else:
                    row["routes"] = {(p40_1993,)}
            elif 2693 <= start < 2990:
                if start in {2747}:
                    row["routes"] = {
                        path + (p40_b32_yes,) for path in p40_b32_paths
                    }
                else:
                    row["routes"] = {(p40_1993, p40_b26_1994)}
            elif 2990 <= start < 3255:
                row["routes"] = set(p40_b34_paths)
            elif 3255 <= start < 3506:
                row["routes"] = {(p40_1993, p40_b26_1994, p40_b27_yes)}
            elif 3506 <= start < 3625:
                row["routes"] = {
                    (p40_1993, p40_b26_1993),
                    (p40_1993, p40_b26_1994, p40_b27_yes),
                }
        elif page == 42 and key in {(42, 1713, 1721), (42, 1763, 1766)}:
            row["routes"] = {((42, 1700, 1804),)}
        elif page == 44:
            if 631 <= start < 1353:
                row["routes"] = {(p44_all_months,)}
            elif 1353 <= start < 1662:
                row["routes"] = {(p44_partial,)}
            elif 1662 <= start < 1821:
                row["routes"] = set(p44_b43_entry_paths)
            elif key in {
                (44, 1998, 2018),
                (44, 2104, 2118),
                (44, 2200, 2213),
                (44, 2229, 2241),
            }:
                row["routes"] = {
                    path + (p44_b43_self,) for path in p44_b43_entry_paths
                }
            elif key in {
                (44, 2033, 2088),
                (44, 2139, 2184),
                (44, 2051, 2055),
            }:
                row["routes"] = {
                    path + (selector,)
                    for path in p44_b43_entry_paths
                    for selector in (p44_b43_both, p44_b43_someone)
                }
        elif page == 46:
            if start < 462:
                row["routes"] = set(p44_non_d_paths)
            elif start < 935:
                row["routes"] = {()}
            elif start < 1218:
                row["routes"] = set(p46_b48_entry_paths)
            elif 1286 <= start < 1611:
                row["routes"] = {
                    path + (selector,)
                    for path in p46_b48_entry_paths
                    for selector in (
                        p46_b48_other,
                        p46_b48_before,
                        p46_b48_unknown,
                    )
                }
        elif page == 48:
            if start < 394:
                row["routes"] = {
                    path + (selector,)
                    for path in p46_b48_entry_paths
                    for selector in (
                        p46_b48_other,
                        p46_b48_before,
                        p46_b48_unknown,
                    )
                }
            elif start < p48_b53_yes[1]:
                row["routes"] = {()}
            elif key in {p48_b53_yes, p48_b53_no} or start < 594:
                row["routes"] = {()}
            elif start < 1186:
                row["routes"] = {(p48_b53_yes,)}
            elif 1260 <= start < 1942:
                if start in {1260, 1482}:
                    row["routes"] = {(p48_b53_yes, p48_self)}
                else:
                    row["routes"] = {(p48_b53_yes, p48_all_others)}
            elif 1955 <= start < 2022:
                row["routes"] = {(p48_b53_yes,)}
            elif 2123 <= start < 2292:
                row["routes"] = set(p48_b59_entry_paths)
            elif key == (48, 2349, 2369):
                row["routes"] = {
                    path + (p48_b59_no,) for path in p48_b59_entry_paths
                }
            elif key == (48, 2374, 2386):
                row["routes"] = {
                    path + (p48_b59_yes,) for path in p48_b59_entry_paths
                }
        elif page == 52:
            if 821 <= start < 1498:
                row["routes"] = {(p52_all_months,)}
            elif 1498 <= start < 1806:
                row["routes"] = {(p52_partial,)}
            elif 1806 <= start < 1985:
                row["routes"] = set(p52_s43_entry_paths)
            elif key in {
                (52, 2130, 2150),
                (52, 2232, 2246),
                (52, 2325, 2338),
                (52, 2355, 2367),
            }:
                row["routes"] = {
                    path + (p52_s43_self,) for path in p52_s43_entry_paths
                }
            elif key in {
                (52, 2162, 2215),
                (52, 2263, 2308),
            }:
                row["routes"] = {
                    path + (selector,)
                    for path in p52_s43_entry_paths
                    for selector in (p52_s43_both, p52_s43_someone)
                }
        elif page == 54:
            if start < 593:
                row["routes"] = set(p52_non_d_paths)
            elif start < 1138:
                row["routes"] = {()}
            elif start < 1408:
                row["routes"] = set(p54_s48_entry_paths)
            elif 1473 <= start:
                row["routes"] = {
                    path + (selector,)
                    for path in p54_s48_entry_paths
                    for selector in (
                        p54_s48_other,
                        p54_s48_before,
                        p54_s48_unknown,
                    )
                }
        elif page == 56:
            if start < 186:
                row["routes"] = {
                    path + (selector,)
                    for path in p54_s48_entry_paths
                    for selector in (
                        p54_s48_other,
                        p54_s48_before,
                        p54_s48_unknown,
                    )
                }
            elif start < p56_s53_yes[1]:
                row["routes"] = {()}
            elif key in {p56_s53_yes, p56_s53_no} or start < 383:
                row["routes"] = {()}
            elif start < 1015:
                row["routes"] = {(p56_s53_yes,)}
            elif 1084 <= start < 1802:
                if start in {1084, 1197}:
                    row["routes"] = {(p56_s53_yes, p56_self)}
                else:
                    row["routes"] = {(p56_s53_yes, p56_all_others)}
            elif 1814 <= start < 1893:
                row["routes"] = {(p56_s53_yes,)}
            elif 2006 <= start < 2201:
                row["routes"] = set(p56_s59_entry_paths)
            elif key == (56, 2224, 2247):
                row["routes"] = {
                    path + (p56_s59_yes,) for path in p56_s59_entry_paths
                }
            elif 2561 <= start < 2633:
                row["routes"] = {(p56_s59_yes, (56, 2224, 2247))}
        elif page == 60:
            if 1396 <= start < 1538:
                row["routes"] = {(p60_b60_yes,)}
            elif 1538 <= start < 1752:
                row["routes"] = set(p60_b63_entry_paths)
            elif 1752 <= start < 1915:
                row["routes"] = {
                    path + (p60_b63_yes,) for path in p60_b63_entry_paths
                }
            elif 1915 <= start < 2056:
                row["routes"] = set(p60_b66_entry_paths)
            elif start >= 2056:
                row["routes"] = set(p60_b66_entry_paths)
        elif page == 62:
            if key in {p62_b78_none, p62_b78_all}:
                row["routes"] = set(p62_b78_entry_paths)
            elif key == p62_b78_none_go:
                row["routes"] = {
                    path + (p62_b78_none,) for path in p62_b78_entry_paths
                }
            elif key == p62_b78_reconcile:
                row["routes"] = set(p62_b78_all_paths)
            elif start < 584:
                row["routes"] = set(p62_b69_entry_paths)
            elif start < 873:
                row["routes"] = set(p62_b72_entry_paths)
            elif start < 1353:
                row["routes"] = {
                    path + (p62_b72_yes,) for path in p62_b72_entry_paths
                }
            elif start < 1576:
                row["routes"] = set(p62_b75_entry_paths)
            elif start < 2147:
                row["routes"] = {
                    path + (p62_b75_yes,) for path in p62_b75_entry_paths
                }
            else:
                row["routes"] = set(p62_b78_entry_paths)
        elif page == 64:
            if start < 455:
                row["routes"] = set(p64_b79_entry_paths)
            elif start < 635:
                row["routes"] = set(p64_b81a_entry_paths)
            elif key in {p64_multiple_jobs, p64_all_others}:
                row["routes"] = set(p64_b81a_entry_paths)
            elif key == p64_go_b82:
                row["routes"] = {
                    path + (p64_all_others,) for path in p64_b81a_entry_paths
                }
            elif 635 < start < 665:
                row["routes"] = {
                    path + (p64_multiple_jobs,)
                    for path in p64_b81a_entry_paths
                }
            elif 759 <= start < 1346:
                row["routes"] = {
                    path + (p64_multiple_jobs,)
                    for path in p64_b81a_entry_paths
                }
            elif 1346 <= start < 1481:
                row["routes"] = set(p64_b82_entry_paths)
            elif 1555 <= start:
                row["routes"] = set(p64_b82_entry_paths)
        elif page == 66:
            if key in {(66, 341, 349), (66, 385, 388)}:
                row["routes"] = {
                    path + (p66_missing_employer,)
                    for path in p64_b82_entry_paths
                }
            elif start < 1529 or start >= 1588:
                row["routes"] = set(p64_b82_entry_paths)
        elif page == 68 and start >= 234:
            row["routes"] = {(p68_c1_yes,)}
        elif page == 70:
            if 112 <= start < 735:
                row["routes"] = set(p68_c4_entry_paths)
            elif 735 <= start < 1584:
                if start >= 978:
                    row["routes"] = {
                        path + (p70_c6_yes,) for path in p70_c6_entry_paths
                    }
                else:
                    row["routes"] = set(p70_c6_entry_paths)
            elif start >= 1613:
                row["routes"] = set(p70_c9_paths)
        elif (
            page == 71 and start >= 246 and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p71_work_history,)}
        elif page == 72:
            if start < 307 and row["kind"] != "flow_branch_label":
                row["routes"] = set(p72_c12_entry_paths)
            elif 307 <= start < 581:
                row["routes"] = {
                    path + (p72_both,) for path in p72_c12_entry_paths
                }
            elif key == (72, 585, 592):
                row["routes"] = {
                    path + (p72_both, p72_one_job)
                    for path in p72_c12_entry_paths
                }
            elif key == (72, 604, 608):
                row["routes"] = {
                    path + (p72_both, p72_two_jobs)
                    for path in p72_c12_entry_paths
                }
            elif 658 <= start < 1318:
                row["routes"] = {
                    path + (p72_both, p72_two_jobs)
                    for path in p72_c12_entry_paths
                }
            elif key == (72, 1318, 1348):
                row["routes"] = {
                    path + (p72_both, p72_two_jobs, p72_c12c_self)
                    for path in p72_c12_entry_paths
                }
            elif key in {
                (72, 1516, 1541),
                (72, 1614, 1633),
                (72, 1706, 1720),
            }:
                row["routes"] = set(p72_c13_paths)
            elif key in {
                (72, 1555, 1606),
                (72, 1653, 1698),
                (72, 1569, 1573),
            }:
                row["routes"] = set(p72_c14_paths)
            elif key in {(72, 2363, 2371), (72, 2413, 2416)}:
                row["routes"] = {
                    path + (p72_missing_employer,) for path in p72_c14a_paths
                }
            elif 2131 <= start < 2592:
                row["routes"] = set(p72_c14a_paths)
        elif page == 74:
            c17_starts = {769, 874, 975, 1073, 1171}
            c22_starts = {802, 907, 1008, 1106}
            c23_starts = {840, 949, 1050, 1148, 1246}
            if start < 456 and row["kind"] != "flow_branch_label":
                row["routes"] = set(p74_c16_entry_paths)
            elif start in c17_starts or key == (74, 1074, 1082):
                row["routes"] = {
                    path + (p74_1993,) for path in p74_c16_entry_paths
                }
            elif start in c22_starts or key == (74, 1019, 1027):
                row["routes"] = set(p74_c22_paths)
            elif start in c23_starts or key == (74, 1154, 1162):
                row["routes"] = set(p74_c23_paths)
            elif 1754 <= start < 2030:
                if start in {1754, 1857, 1951, 1952}:
                    row["routes"] = set(p74_c18_paths)
                else:
                    row["routes"] = set(p74_c24_paths)
            elif 2200 <= start < 2450:
                if start == 2252:
                    row["routes"] = set(p74_c24_paths)
                else:
                    row["routes"] = {
                        path + (p74_c18_1994,) for path in p74_c18_paths
                    }
            elif 2567 <= start < 2598:
                row["routes"] = {
                    path + (p74_c18_1994, p74_c19_yes)
                    for path in p74_c18_paths
                }
            elif 2652 <= start < 2890:
                row["routes"] = set(p74_c26_paths)
            elif start in {3101, 3146, 3188}:
                row["routes"] = set(p74_c21_paths)
        elif page == 76:
            if key in {(76, 267, 271), (76, 510, 514), (76, 515, 521)}:
                if start == 267:
                    row["routes"] = {(p76_head_male,)}
                else:
                    row["routes"] = {(p76_head_male, p76_wife)}
            elif key == (76, 304, 308):
                row["routes"] = {((76, 300, 318),)}
            elif key in {(76, 546, 550), (76, 551, 557)}:
                row["routes"] = {(p76_head_male, p76_no_wife)}
            elif 678 <= start < 919:
                row["routes"] = {(p76_head_male, p76_wife)}
            elif key == p76_unemployed:
                row["routes"] = {(p76_head_male, p76_wife)}
            elif key == p76_go_d4:
                row["routes"] = {
                    (p76_head_male, p76_wife, p76_working),
                    (p76_head_male, p76_wife, p76_temporary),
                }
            elif key == (76, 1346, 1356):
                row["routes"] = {(p76_head_male, p76_wife, p76_unemployed)}
            elif 1393 <= start < 1546:
                row["routes"] = {(p76_head_male, p76_wife, p76_retired)}
            elif 1546 <= start < 1746:
                row["routes"] = set(p76_d3_entry_paths[:3])
            elif 1798 <= start < 1811:
                row["routes"] = set(p76_d3_entry_paths)
            elif key == p76_d3_yes:
                row["routes"] = set(p76_d3_entry_paths)
            elif key == p76_d3_yes_go:
                row["routes"] = {
                    path + (p76_d3_yes,) for path in p76_d3_entry_paths
                }
            elif key == p76_d3_no_go:
                row["routes"] = set(p76_d3_entry_paths)
            elif 2189 <= start:
                row["routes"] = {(p76_head_male, p76_wife)}
        elif page == 84:
            if key == (84, 2673, 2676):
                row["routes"] = {
                    path
                    + (
                        p84_g9a_yes,
                        p84_g9b_unreported,
                        p84_g9b_supplement,
                    )
                    for path in p84_g5_yes_paths
                }
            elif key == (84, 2801, 2807):
                row["routes"] = {
                    path + (p84_wife,) for path in p84_g9bb_entry_paths
                }
            elif key == (84, 3524, 3527):
                row["routes"] = {
                    path
                    + (
                        p84_wife,
                        p84_g9c_yes,
                        p84_g9d_unreported,
                        p84_g9d_supplement,
                    )
                    for path in p84_g9bb_entry_paths
                }
            elif key == p84_go_g5:
                row["routes"] = {(p84_all_others,)}
            elif 431 < start < 466:
                row["routes"] = {(p84_farmer,)}
            elif 593 <= start < 1077:
                row["routes"] = {(p84_farmer,)}
            elif 1077 <= start < 1377:
                row["routes"] = set(p84_g5_parent_paths)
            elif 1377 <= start < 2348:
                row["routes"] = set(p84_g5_yes_paths)
            elif 2348 <= start < 2692:
                row["routes"] = {
                    path + (p84_g9a_yes,) for path in p84_g5_yes_paths
                }
            elif 2692 <= start < 2867:
                row["routes"] = set(p84_g9bb_entry_paths)
            elif 2867 <= start < 3112:
                row["routes"] = {
                    path + (p84_wife,) for path in p84_g9bb_entry_paths
                }
            elif 3112 <= start:
                row["routes"] = {
                    path + (p84_wife, p84_g9c_yes)
                    for path in p84_g9bb_entry_paths
                }
        elif page == 86:
            if key == (86, 2658, 2661):
                row["routes"] = {
                    path
                    + (
                        p86_g9a_yes,
                        p86_g9b_unreported,
                        p86_g9b_supplement,
                    )
                    for path in p86_g5_yes_paths
                }
            elif key == (86, 2783, 2789):
                row["routes"] = {
                    path + (p86_wife,) for path in p86_g9bb_entry_paths
                }
            elif key == (86, 3512, 3515):
                row["routes"] = {
                    path
                    + (
                        p86_wife,
                        p86_g9c_yes,
                        p86_g9d_unreported,
                        p86_g9d_supplement,
                    )
                    for path in p86_g9bb_entry_paths
                }
            elif key == p86_go_g5:
                row["routes"] = {(p86_all_others,)}
            elif 418 < start < 452:
                row["routes"] = {(p86_farmer,)}
            elif 572 <= start < 1055:
                row["routes"] = {(p86_farmer,)}
            elif 1055 <= start < 1345:
                row["routes"] = set(p86_g5_parent_paths)
            elif 1345 <= start < 2324:
                row["routes"] = set(p86_g5_yes_paths)
            elif 2324 <= start < 2677:
                row["routes"] = {
                    path + (p86_g9a_yes,) for path in p86_g5_yes_paths
                }
            elif 2677 <= start < 2879:
                row["routes"] = set(p86_g9bb_entry_paths)
            elif 2879 <= start < 3145:
                row["routes"] = {
                    path + (p86_wife,) for path in p86_g9bb_entry_paths
                }
            elif 3145 <= start:
                row["routes"] = {
                    path + (p86_wife, p86_g9c_yes)
                    for path in p86_g9bb_entry_paths
                }
        elif page == 88:
            if key == (88, 73, 84):
                row["routes"] = {
                    path + (p88_corporation,)
                    for path in p88_business_form_entry_paths
                }
            elif key == (88, 98, 112):
                row["routes"] = {
                    path + (p88_unincorporated,)
                    for path in p88_business_form_entry_paths
                }
            elif key == (88, 347, 353):
                row["routes"] = set(p88_profit_paths)
            elif key in {
                (88, 70, 84),
                (88, 95, 112),
                (88, 125, 144),
            }:
                row["routes"] = set(p88_business_form_entry_paths)
            elif key in {
                (88, 343, 353),
                (88, 407, 414),
                (88, 510, 523),
            }:
                row["routes"] = {
                    path + (owner,)
                    for path in p88_business_form_entry_paths
                    for owner in (p88_unincorporated, p88_other)
                }
            elif key in {p88_one_business, p88_multiple_businesses}:
                row["routes"] = set(p88_g11_result_paths)
            elif key == (88, 1281, 1289):
                row["routes"] = {
                    path + (p88_one_business,) for path in p88_g11_result_paths
                }
            elif key == (88, 1576, 1584):
                row["routes"] = {
                    path + (p88_multiple_businesses, p88_repeat_business)
                    for path in p88_g11_result_paths
                }
            elif key == p88_repeat_business:
                row["routes"] = {
                    path + (p88_multiple_businesses, p88_repeat_business)
                    for path in p88_g11_result_paths
                }
            elif start < 631:
                if start in {251, 264, 280, 290}:
                    row["routes"] = set(p88_owner_paths)
                else:
                    row["routes"] = set(p88_business_form_entry_paths)
            elif start in {633, 745, 761, 851, 894, 955}:
                row["routes"] = set(p88_profit_paths)
            elif start in {712, 824, 839, 930, 939, 1034}:
                row["routes"] = set(p88_loss_paths)
            elif start < 1272:
                row["routes"] = set(p88_g11_result_paths)
            elif 1585 <= start < 2074:
                if start in {1802, 1811, 1829}:
                    row["routes"] = {
                        path + (p88_g12_instruction,)
                        for path in p88_g12_entry_paths
                    }
                else:
                    row["routes"] = set(p88_g12_entry_paths)
            elif 2074 <= start < 2304:
                if start in {2074, 2188, 2197, 2207, 2290}:
                    row["routes"] = set(p88_g12_no_paths)
                else:
                    row["routes"] = set(p88_g12_entry_paths)
            elif 2304 <= start < 2837:
                row["routes"] = set(p88_g12_entry_paths)
            elif 2911 <= start < 3458:
                row["routes"] = set(p88_g16a_entry_paths)
            elif start >= 3458:
                if key == (88, 3721, 3724):
                    row["routes"] = {
                        path + (p88_g17_unreported, p88_g17_supplement)
                        for path in p88_g17e_entry_paths
                    }
                else:
                    row["routes"] = set(p88_g17e_entry_paths)
        elif page == 90:
            if key == (90, 73, 84):
                row["routes"] = {
                    path + (p90_corporation,)
                    for path in p90_business_form_entry_paths
                }
            elif key == (90, 98, 112):
                row["routes"] = {
                    path + (p90_unincorporated,)
                    for path in p90_business_form_entry_paths
                }
            elif key == (90, 352, 358):
                row["routes"] = set(p90_profit_paths)
            elif key in {
                (90, 70, 84),
                (90, 95, 112),
                (90, 126, 145),
            }:
                row["routes"] = set(p90_business_form_entry_paths)
            elif key in {(90, 348, 359), (90, 414, 432)}:
                row["routes"] = {
                    path + (owner,)
                    for path in p90_business_form_entry_paths
                    for owner in (p90_unincorporated, p90_other)
                }
            elif key in {p90_one_business, p90_multiple_businesses}:
                row["routes"] = set(p90_g11_result_paths)
            elif key == (90, 1224, 1232):
                row["routes"] = {
                    path + (p90_one_business,) for path in p90_g11_result_paths
                }
            elif key == (90, 1440, 1448):
                row["routes"] = {
                    path + (p90_multiple_businesses, p90_repeat_business)
                    for path in p90_g11_result_paths
                }
            elif key == p90_repeat_business:
                row["routes"] = {
                    path + (p90_multiple_businesses, p90_repeat_business)
                    for path in p90_g11_result_paths
                }
            elif start < 531:
                if start in {256, 269, 285, 295}:
                    row["routes"] = set(p90_owner_paths)
                else:
                    row["routes"] = set(p90_business_form_entry_paths)
            elif start in {543, 659, 675, 769, 812, 877}:
                row["routes"] = set(p90_profit_paths)
            elif start in {626, 742, 757, 852, 861, 960}:
                row["routes"] = set(p90_loss_paths)
            elif start < 1215:
                row["routes"] = set(p90_g11_result_paths)
            elif 1449 <= start < 1939:
                if start in {1666, 1675, 1693}:
                    row["routes"] = {
                        path + (p90_g12_instruction,)
                        for path in p90_g12_entry_paths
                    }
                else:
                    row["routes"] = set(p90_g12_entry_paths)
            elif 1939 <= start < 2179:
                if start in {1939, 2060, 2069, 2079, 2166}:
                    row["routes"] = set(p90_g12_no_paths)
                else:
                    row["routes"] = set(p90_g12_entry_paths)
            elif 2179 <= start < 2725:
                row["routes"] = set(p90_g12_entry_paths)
            elif 2844 <= start < 3403:
                row["routes"] = set(p90_g16a_entry_paths)
            elif start >= 3403:
                if key == (90, 3683, 3686):
                    row["routes"] = {
                        path + (p90_g17_unreported, p90_g17_supplement)
                        for path in p90_g17e_entry_paths
                    }
                else:
                    row["routes"] = set(p90_g17e_entry_paths)
        elif page == 92:
            if key == (92, 972, 975):
                row["routes"] = {
                    path + (p92_g21a_unreported, p92_g21a_supplement)
                    for path in p92_g18a_entry_paths
                }
            elif start < 987:
                row["routes"] = set(p92_g18a_entry_paths)
            elif start < 1201:
                row["routes"] = set(p92_g18b_entry_paths)
            elif start < 1771:
                if key == (92, 1755, 1758):
                    row["routes"] = {
                        path
                        + (
                            p92_g18b_yes,
                            p92_g21b_unreported,
                            p92_g21b_supplement,
                        )
                        for path in p92_g18b_entry_paths
                    }
                else:
                    row["routes"] = {
                        path + (p92_g18b_yes,) for path in p92_g18b_entry_paths
                    }
            elif start < 2060:
                row["routes"] = set(p92_g18c_entry_paths)
            else:
                if key == (92, 2611, 2614):
                    row["routes"] = {
                        path
                        + (
                            p92_g18c_yes,
                            p92_g21c_unreported,
                            p92_g21c_supplement,
                        )
                        for path in p92_g18c_entry_paths
                    }
                else:
                    row["routes"] = {
                        path + (p92_g18c_yes,) for path in p92_g18c_entry_paths
                    }
        elif page == 94 and row["kind"] != "flow_branch_label":
            if key == (94, 120, 129):
                row["routes"] = {
                    path + (p94_extra_job,) for path in p92_g22_entry_paths
                }
            elif start >= 330:
                row["routes"] = {
                    path + (p94_extra_job, p94_g23_no)
                    for path in p92_g22_entry_paths
                }
            elif start >= 193:
                row["routes"] = {
                    path + (p94_extra_job,) for path in p92_g22_entry_paths
                }
            else:
                row["routes"] = set(p92_g22_entry_paths)
        elif page == 106:
            if 204 <= start < 229 and row["kind"] != "flow_branch_label":
                row["routes"] = {(p106_wife,)}
            elif key == (106, 1945, 1948):
                row["routes"] = {
                    path + (p106_hours_unreported, p106_hours_supplement)
                    for path in p106_g52_entry_paths
                }
            elif key == (106, 640, 644):
                row["routes"] = {(p106_wife,)}
            elif key == (106, 645, 651):
                row["routes"] = {(p106_wife, p106_worked)}
            elif (
                key == p106_hours_reported
                and row["kind"] != "flow_branch_label"
            ):
                row["routes"] = {
                    path + (p106_hours_reported,)
                    for path in p106_g52_entry_paths
                }
            elif (
                key == p106_hours_unreported
                and row["kind"] != "flow_branch_label"
            ):
                row["routes"] = {
                    path + (p106_hours_unreported,)
                    for path in p106_g52_entry_paths
                }
            elif 306 <= start < 802:
                row["routes"] = {(p106_wife,)}
            elif 802 <= start < 1295:
                row["routes"] = {(p106_wife, p106_worked)}
            elif 1295 <= start < 1960:
                row["routes"] = set(p106_g52_entry_paths)
            elif 1960 <= start < 2121:
                row["routes"] = set(p106_g52c_entry_paths)
            elif 2121 <= start < 2160:
                row["routes"] = {(p106_wife, p106_income_yes)}
            elif 2160 <= start:
                row["routes"] = {(p106_wife, p106_income_other)}
        elif page == 107:
            if key in {
                (107, 434, 559),
                (107, 528, 536),
                p107_if_known,
            }:
                row["routes"] = {(p107_business, p107_included_business)}
            elif 317 < start < 599:
                row["routes"] = {(p107_business,)}
            elif 875 < start <= 991:
                row["routes"] = {(p107_missing_hours,)}
        elif page == 114:
            if key in {
                (114, 579, 587),
                (114, 707, 711),
            }:
                row["routes"] = {(p114_g9b_business,)}
            elif key in {
                (114, 598, 606),
                (114, 723, 727),
                (114, 728, 734),
            }:
                row["routes"] = {(p114_g9d_business,)}
            elif key in {
                (114, 620, 626),
                (114, 745, 750),
            }:
                row["routes"] = {(p114_g17e_wages,)}
            elif key == (114, 642, 648):
                row["routes"] = {(p114_g21_other_work,)}
            elif key in {
                (114, 686, 692),
                (114, 693, 697),
            }:
                row["routes"] = {(p114_g52b_wife_work,)}
            elif key == (114, 893, 922):
                row["routes"] = {(p114_g21_other_work,)}
            elif key in {p114_g21a, p114_g21b, p114_g21c}:
                row["routes"] = {(p114_g21_other_work,)}
            elif key == (114, 1230, 1237):
                row["routes"] = {(p114_g21_other_work, p114_g21b)}
            elif 833 <= start < 1162:
                row["routes"] = set(p114_left_gj1_paths)
            elif 1440 <= start < 2087:
                row["routes"] = set(p114_right_gj1_paths)
            elif key in {
                (114, 2355, 2363),
                (114, 2404, 2407),
            }:
                row["routes"] = {
                    path + (p114_missing_employer,)
                    for path in p114_gj2_entry_paths
                }
            elif start >= 2087:
                row["routes"] = set(p114_gj2_entry_paths)
        elif page == 115 and key == (115, 528, 536):
            row["routes"] = {(p115_missing_hours,)}
        elif page == 116:
            if key == (116, 71, 79):
                row["routes"] = {()}
            elif key in {
                p116_return_g9b,
                p116_return_g9d,
                p116_return_g17e,
                p116_return_g52b,
                p116_terminal_g21a,
                p116_terminal_g21b,
                p116_terminal_g21c,
            }:
                row["routes"] = set(p116_gj11_entry_paths)
            elif key == p116_return_g21a:
                row["routes"] = {(p116_terminal_g21a,)}
            elif key == p116_return_g21b:
                row["routes"] = {(p116_terminal_g21b,)}
            elif key == p116_return_g21c:
                row["routes"] = {(p116_terminal_g21c,)}
            elif key == p116_business_origin:
                row["routes"] = {()}
            elif key == p116_all_origins:
                row["routes"] = {()}
            elif key in {
                (116, 94, 102),
                (116, 106, 110),
                (116, 118, 126),
                (116, 130, 134),
                (116, 135, 141),
            }:
                row["routes"] = {(p116_business_origin,)}
            elif key == p116_go_gj4:
                row["routes"] = {(p116_business_origin,)}
            elif 251 <= start < 351:
                row["routes"] = {(p116_all_origins,)}
            elif 351 <= start < 1339:
                row["routes"] = set(p116_gj4_entry_paths)
            elif 1339 <= start < 1768:
                row["routes"] = {
                    path + (p116_stopped_yes,) for path in p116_gj4_entry_paths
                }
            elif start >= 1768:
                row["routes"] = set(p116_gj11_entry_paths)
        elif page == 117 and key == (117, 135, 143):
            row["routes"] = {(p117_business_supplement,)}
        elif (
            page == 119
            and row["kind"] == "repeat_or_alias_instruction"
            and start == 3009
        ):
            row["routes"] = {(p119_multiple_ofums,)}
        elif page == 122:
            positive_jobs = (
                p122_job_one,
                p122_job_two,
                p122_job_three,
                p122_job_four,
            )
            if 1512 <= start < 3680:
                row["routes"] = {(p122_not_deceased,)}
            elif key in {
                p122_job_one,
                p122_job_two,
                p122_job_three,
                p122_job_four,
                p122_job_none,
            }:
                row["routes"] = {(p122_not_deceased,)}
            elif key == (122, 3959, 3973):
                row["routes"] = {
                    (
                        p122_not_deceased,
                        p122_job_none,
                    )
                }
            elif 3974 <= start < 5094:
                row["routes"] = {
                    (p122_not_deceased, job_branch)
                    for job_branch in positive_jobs
                }
            elif key == p122_g82_one:
                row["routes"] = {
                    (
                        p122_not_deceased,
                        p122_job_one,
                    )
                }
            elif key == p122_g82_other:
                row["routes"] = {
                    (p122_not_deceased, job_branch)
                    for job_branch in (
                        p122_job_two,
                        p122_job_three,
                        p122_job_four,
                    )
                }
            elif key == (122, 5216, 5230):
                row["routes"] = {
                    (
                        p122_not_deceased,
                        p122_job_one,
                        p122_g82_one,
                    )
                }
            elif 5191 <= start:
                row["routes"] = {
                    (p122_not_deceased, job_branch, p122_g82_other)
                    for job_branch in (
                        p122_job_two,
                        p122_job_three,
                        p122_job_four,
                    )
                }
        elif page == 126 and row["kind"] == "repeat_or_alias_instruction":
            row["routes"] = {((126, 2559, 2793),)}
        elif page == 128:
            if 431 <= start < 1362:
                row["routes"] = {(p128_young,)}
            elif key == p128_work:
                row["routes"] = {(p128_young,)}
            elif 1362 <= start < 2843:
                row["routes"] = {(p128_young, p128_work)}
        elif page == 130 and start >= 2461:
            if row["kind"] == "repeat_or_alias_instruction":
                row["routes"] = {
                    (
                        p130_more_people,
                        p130_supplement,
                    )
                }
            elif key == p130_supplement:
                row["routes"] = {(p130_more_people,)}
        elif page == 79 and 219 <= start < 456:
            row["routes"] = {(p79_roomers,)}
        elif (
            page == 27
            and 1730 <= start < 1777
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p27_road, p27_foreman)}
        elif (
            page == 27
            and 1799 <= start < 1847
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p27_road, p27_operative)}
        elif (
            page == 27
            and 1852 <= start < 1918
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p27_road, p27_laborer)}
        elif (
            page == 39
            and 586 <= start < 706
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p39_ads,)}
        elif (
            page == 39
            and 707 <= start < 775
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p39_ads, p39_no_ad)}
        elif (
            page == 43
            and 1415 < start < 1648
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p43_present_1993,)}
        elif page == 61 and key == (61, 441, 445):
            row["routes"] = {((61, 438, 621),)}
        elif page == 63 and key == (63, 3094, 3098):
            row["routes"] = {((63, 2869, 3133),)}
        elif page == 67 and key == (67, 285, 295):
            row["routes"] = {((67, 208, 296),)}
        elif (
            page == 63
            and 1259 <= start < 1394
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {(p63_unemployed_vacation,)}
        elif (
            page == 63
            and 1400 <= start < 1465
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {
                (
                    p63_unemployed_vacation,
                    p63_earned_then_laid_off,
                )
            }
        elif (
            page == 63
            and 1466 <= start < 1546
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {
                (
                    p63_unemployed_vacation,
                    p63_earned_then_laid_off,
                    p63_if_so,
                )
            }
        elif (
            page == 63
            and 1547 <= start < 1679
            and row["kind"] != "flow_branch_label"
        ):
            row["routes"] = {
                (
                    p63_unemployed_vacation,
                    p63_layoff_first,
                )
            }
        elif page == 65 and row["kind"] != "flow_branch_label":
            if start in {392, 414, 483, 487, 511}:
                row["routes"] = {((65, 381, 515),)}
            elif start in {1182, 1272, 1296}:
                row["routes"] = {((65, 1175, 1305),)}
            elif start in {1317, 1354, 1407, 1426}:
                row["routes"] = {((65, 1314, 1453),)}
        elif page == 85 and row["kind"] != "flow_branch_label":
            if start in {39, 52}:
                row["routes"] = {((85, 36, 91),)}
            elif start in {172, 185}:
                row["routes"] = {((85, 169, 246),)}
            elif start in {608, 616, 655, 693}:
                row["routes"] = {((85, 608, 664),)}
        elif page == 87 and row["kind"] != "flow_branch_label":
            if start == 239:
                row["routes"] = {((87, 223, 271),)}
            elif start in {620, 644, 688}:
                row["routes"] = {((87, 588, 628),)}
            elif start in {1069, 1157, 1165}:
                row["routes"] = {((87, 1062, 1090),)}
            elif start in {1251, 1323, 1365}:
                row["routes"] = {((87, 1232, 1275),)}
        elif page == 89 and row["kind"] != "flow_branch_label":
            if start in {224, 232, 281, 294}:
                row["routes"] = {((89, 187, 306),)}
            elif start in {722, 756, 791}:
                row["routes"] = {((89, 685, 762),)}
            elif start in {
                979,
                984,
                1042,
                1051,
                1084,
                1099,
                1189,
                1197,
                1215,
            }:
                row["routes"] = {((89, 972, 1107),)}
            elif start in {1240, 1245, 1356, 1436}:
                row["routes"] = {((89, 1237, 1303),)}
            elif start == 1956:
                row["routes"] = {((89, 1940, 1988),)}
            elif start == 2072:
                row["routes"] = {((89, 2069, 2096),)}
            elif start == 2636:
                row["routes"] = {((89, 2633, 2662),)}
            elif start in {3071, 3182, 3254, 3324, 3330, 3370}:
                row["routes"] = {((89, 3068, 3100),)}
            elif start in {3431, 3448, 3503, 3543, 3582}:
                row["routes"] = {((89, 3428, 3511),)}
        elif page == 91 and row["kind"] != "flow_branch_label":
            if start == 277:
                row["routes"] = {((91, 274, 362),)}
            elif start in {399, 424, 433, 443, 451}:
                row["routes"] = {((91, 396, 462),)}
            elif start in {617, 667}:
                row["routes"] = {((91, 489, 586),)}
        elif page == 93 and row["kind"] != "flow_branch_label":
            if start in {725, 736, 743, 760, 786}:
                row["routes"] = {((93, 722, 770),)}
            elif start in {860, 877, 911, 940, 952, 987}:
                row["routes"] = {((93, 857, 918),)}
            elif start == 1137:
                row["routes"] = {((93, 1122, 1169),)}
            elif start == 1628:
                row["routes"] = {((93, 1566, 1616),)}
            elif start in {3181, 3190}:
                row["routes"] = {((93, 3099, 3160),)}
        elif page == 232 and 357 <= start < 405:
            row["routes"] = {(p232_no_help,)}
        elif page == 232 and 480 <= start < 955:
            row["routes"] = {(p232_all_others,)}
        elif page == 232 and 1229 <= start < 1550:
            row["routes"] = {
                (
                    p232_all_others,
                    p232_wife_in_fu,
                )
            }
        elif page == 278 and start < 1239:
            row["routes"] = {(p266_new_wife,), (p266_wife,)}
        elif page == 278:
            row["routes"] = {
                (p266_new_wife, p278_years),
                (p266_wife, p278_years),
            }
        elif page == 280 and row["kind"] != "flow_branch_label":
            row["routes"] = {(p280_new_head,)}
        elif page == 266 and row["kind"] != "flow_branch_label":
            row["routes"] = {(p266_new_wife,) if start < 485 else (p266_wife,)}
        elif page == 282 and row["kind"] != "flow_branch_label":
            row["routes"] = {(p280_new_head,)}

    for row in specs.values():
        row["routes"] = {
            tuple(
                (
                    parent_page,
                    *trim_span(parent_page, parent_start, parent_end),
                )
                for parent_page, parent_start, parent_end in route
            )
            for route in row["routes"]
        }

    ordered_specs = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
        ),
    )

    # Branch rows are first stated as exact occurrence atoms.  Parent routes
    # are resolved below; most reviewed clauses are independent roots.
    flow_rows = [
        row for row in ordered_specs if row["kind"] == "flow_branch_label"
    ]
    flow_by_key = {
        (row["page"], row["start"], row["end"]): row for row in flow_rows
    }
    if len(flow_by_key) != len(flow_rows):
        raise ValueError("duplicate flow source key")

    # Only source-explicit nested ancestry is listed.  Keys name exact flow
    # occurrences; all unlisted labels have the root as their sole parent.
    nested_flow_routes: dict[
        tuple[int, int, int],
        tuple[tuple[tuple[int, int, int], ...], ...],
    ] = {
        (79, 456, 491): (((79, 160, 203),),),
        (232, 1091, 1112): (((232, 334, 348),),),
        (232, 1120, 1146): (((232, 334, 348),),),
        (280, 1684, 1880): (((280, 445, 456),),),
        (27, 1730, 1777): (((27, 1635, 1672),),),
        (27, 1799, 1847): (((27, 1635, 1672),),),
        (27, 1852, 1918): (((27, 1635, 1672),),),
        (39, 707, 775): (((39, 586, 706),),),
        (89, 1457, 1509): (((89, 1237, 1303),),),
        (63, 1400, 1465): (((63, 1259, 1394),),),
        (63, 1466, 1546): (((63, 1259, 1394), (63, 1400, 1465)),),
        (63, 1547, 1679): (((63, 1259, 1394),),),
        (106, 280, 302): (((106, 254, 269),),),
        (106, 790, 800): (((106, 204, 228), (106, 685, 698)),),
        (106, 1757, 1794): (((106, 204, 228), (106, 640, 666)),),
        (106, 1809, 1852): (((106, 204, 228), (106, 640, 666)),),
        (106, 1930, 1959): (
            ((106, 204, 228), (106, 640, 666), (106, 1809, 1852)),
        ),
        (232, 1202, 1211): (((232, 334, 348), (232, 1120, 1146)),),
        (266, 951, 1070): (((266, 506, 519),),),
        (266, 1115, 1186): (
            ((266, 453, 468),),
            ((266, 471, 476),),
        ),
        (280, 566, 619): (((280, 464, 476),),),
    }

    nested_flow_routes[p22_b3_yes] = tuple(
        (category,) for category in p22_b1_categories[:3]
    )
    for selector in (p24_b4_self, p24_b4_both, p24_b4_someone):
        nested_flow_routes[selector] = p22_b4_entry_paths
    nested_flow_routes[p24_b4a_one] = tuple(
        path + (p24_b4_both,) for path in p22_b4_entry_paths
    )
    nested_flow_routes[p24_b4a_go_b5] = tuple(
        path + (p24_b4_both, p24_b4a_one) for path in p22_b4_entry_paths
    )
    for selector in (p24_b4c_self, p24_b4c_someone):
        nested_flow_routes[selector] = tuple(
            path + (p24_b4_both,) for path in p22_b4_entry_paths
        )
    nested_flow_routes[p24_b4c_go_b5] = tuple(
        path + (p24_b4_both, p24_b4c_self) for path in p22_b4_entry_paths
    )
    nested_flow_routes[p24_b4c_go_b6] = tuple(
        path + (p24_b4_both, p24_b4c_someone) for path in p22_b4_entry_paths
    )
    for selector in (p24_b7_yes, p24_b7_no):
        nested_flow_routes[selector] = p24_b6_paths
    nested_flow_routes[p24_b8_yes] = tuple(
        path + (p24_b7_yes,) for path in p24_b6_paths
    )

    for selector in (p34_b14_no, p34_b14_yes):
        nested_flow_routes[selector] = (
            (p34_b12_salaried,),
            (p34_b12_salary_commission,),
        )
    for selector in (
        p36_b17a_tips,
        p36_b17a_commission,
        p36_b17a_all_others,
    ):
        nested_flow_routes[selector] = ((),)
    for selector in (p38_b22_someone, p38_b22_others):
        nested_flow_routes[selector] = ((),)
    nested_flow_routes[p38_b22_route] = p38_b22_other_paths

    nested_flow_routes[p40_b25_yes] = ((p40_1993,),)
    for selector in (p40_b30_1993, p40_b30_1994):
        nested_flow_routes[selector] = p40_b30_paths
    for selector in (p40_b31_1993, p40_b31_other):
        nested_flow_routes[selector] = p40_b31_paths
    for selector in (p40_b26_1993, p40_b26_1994):
        nested_flow_routes[selector] = ((p40_1993,),)
    for selector in (p40_b32_yes, p40_b32_no):
        nested_flow_routes[selector] = p40_b32_paths
    for selector in (p40_b27_yes, p40_b27_no):
        nested_flow_routes[selector] = ((p40_1993, p40_b26_1994),)

    nested_flow_routes[p44_go_b43] = (
        (p44_no_overlap,),
        (p44_one_month,),
    )
    nested_flow_routes[p44_partial_no] = ((p44_partial,),)
    nested_flow_routes[(44, 1335, 1352)] = ((p44_all_months,),)
    for selector in (p44_b43_self, p44_b43_both, p44_b43_someone):
        nested_flow_routes[selector] = p44_b43_entry_paths
    nested_flow_routes[p46_b46_no] = ((),)
    for selector in (
        p46_b48_1993,
        p46_b48_other,
        p46_b48_before,
        p46_b48_unknown,
    ):
        nested_flow_routes[selector] = p46_b48_entry_paths
    for selector in (p48_b53_yes, p48_b53_no):
        nested_flow_routes[selector] = ((),)
    for selector in (p48_self, p48_all_others):
        nested_flow_routes[selector] = ((p48_b53_yes,),)
    nested_flow_routes[p48_go_b57a] = ((p48_b53_yes, p48_self),)
    for selector in (p48_b59_yes, p48_b59_no):
        nested_flow_routes[selector] = p48_b59_entry_paths
    nested_flow_routes[(48, 2349, 2369)] = tuple(
        path + (p48_b59_no,) for path in p48_b59_entry_paths
    )
    nested_flow_routes[(48, 2374, 2386)] = tuple(
        path + (p48_b59_yes,) for path in p48_b59_entry_paths
    )

    nested_flow_routes[p52_go_s43] = (
        (p52_no_overlap,),
        (p52_one_month,),
    )
    nested_flow_routes[p52_partial_no] = ((p52_partial,),)
    for selector in (p52_s43_self, p52_s43_both, p52_s43_someone):
        nested_flow_routes[selector] = p52_s43_entry_paths
    nested_flow_routes[p54_s46_no] = ((),)
    for selector in (
        p54_s48_1993,
        p54_s48_other,
        p54_s48_before,
        p54_s48_unknown,
    ):
        nested_flow_routes[selector] = p54_s48_entry_paths
    for selector in (p56_s53_yes, p56_s53_no):
        nested_flow_routes[selector] = ((),)
    for selector in (p56_self, p56_all_others):
        nested_flow_routes[selector] = ((p56_s53_yes,),)
    nested_flow_routes[p56_go_s57a] = ((p56_s53_yes, p56_self),)
    nested_flow_routes[p56_s59_yes] = p56_s59_entry_paths
    nested_flow_routes[(56, 2224, 2247)] = tuple(
        path + (p56_s59_yes,) for path in p56_s59_entry_paths
    )
    for selector in (
        (56, 2561, 2578),
        (56, 2579, 2596),
        (56, 2597, 2614),
        (56, 2615, 2632),
    ):
        nested_flow_routes[selector] = ((p56_s59_yes, (56, 2224, 2247)),)

    for selector in (p60_b63_yes, p60_b63_no):
        nested_flow_routes[selector] = p60_b63_entry_paths
    nested_flow_routes[p60_b66_no] = p60_b66_entry_paths
    for selector in (p62_b78_none, p62_b78_all):
        nested_flow_routes[selector] = p62_b78_entry_paths
    nested_flow_routes[p62_b78_none_go] = tuple(
        path + (p62_b78_none,) for path in p62_b78_entry_paths
    )
    nested_flow_routes[p62_b78_reconcile] = p62_b78_all_paths
    nested_flow_routes[p64_b80_no] = p64_b79_entry_paths
    for selector in (p64_multiple_jobs, p64_all_others):
        nested_flow_routes[selector] = p64_b81a_entry_paths
    nested_flow_routes[p64_go_b82] = tuple(
        path + (p64_all_others,) for path in p64_b81a_entry_paths
    )
    nested_flow_routes[p64_b82_no] = p64_b82_entry_paths
    nested_flow_routes[p66_b92_no] = p64_b82_entry_paths

    nested_flow_routes[p70_c4_go] = p68_c4_entry_paths
    for selector in (
        p70_c5_1993,
        p70_c5_1994,
        p70_c5_1993_or_1994,
        p70_c5_other,
        p70_c5_before,
        p70_c5_unknown,
    ):
        nested_flow_routes[selector] = ((),)
    for selector in (p70_c6_yes, p70_c6_no):
        nested_flow_routes[selector] = p70_c6_entry_paths
    nested_flow_routes[p70_c6_terminal] = tuple(
        path + (p70_c6_no,) for path in p70_c6_entry_paths
    )
    nested_flow_routes[p70_c7_all] = tuple(
        path + (p70_c6_yes,) for path in p70_c6_entry_paths
    )
    nested_flow_routes[p70_c8_terminal] = tuple(
        path + (p70_c6_yes,) for path in p70_c6_entry_paths
    )

    for selector in (p72_self, p72_both, p72_someone):
        nested_flow_routes[selector] = p72_c12_entry_paths
    for selector in (p72_one_job, p72_two_jobs):
        nested_flow_routes[selector] = tuple(
            path + (p72_both,) for path in p72_c12_entry_paths
        )
    nested_flow_routes[p72_one_go_c13] = tuple(
        path + (p72_both, p72_one_job) for path in p72_c12_entry_paths
    )
    for selector in (p72_c12c_self, p72_c12c_someone):
        nested_flow_routes[selector] = tuple(
            path + (p72_both, p72_two_jobs) for path in p72_c12_entry_paths
        )
    nested_flow_routes[p72_c12c_go_c13] = tuple(
        path + (p72_both, p72_two_jobs, p72_c12c_self)
        for path in p72_c12_entry_paths
    )
    nested_flow_routes[p72_c12c_go_c14] = tuple(
        path + (p72_both, p72_two_jobs, p72_c12c_someone)
        for path in p72_c12_entry_paths
    )
    for selector in (p72_c13_unincorporated, p72_c13_corporation):
        nested_flow_routes[selector] = p72_c13_paths
    for selector in p72_c14_categories:
        nested_flow_routes[selector] = p72_c14_paths
    nested_flow_routes[p72_c13_go_c14a] = tuple(
        path + (answer,)
        for path in p72_c13_paths
        for answer in (p72_c13_unincorporated, p72_c13_corporation)
    )

    for selector in (
        p74_1993,
        p74_1994,
        p74_1993_or_1994,
        p74_other_year,
        p74_before_1993,
        p74_unknown_year,
    ):
        nested_flow_routes[selector] = p74_c16_entry_paths
    for selector in (p74_c17_yes, p74_c17_no):
        nested_flow_routes[selector] = tuple(
            path + (p74_1993,) for path in p74_c16_entry_paths
        )
    for selector in (p74_c22_1993, p74_c22_1994):
        nested_flow_routes[selector] = p74_c22_paths
    for selector in (p74_c23_1993, p74_c23_1994, p74_c23_other):
        nested_flow_routes[selector] = p74_c23_paths
    nested_flow_routes[p74_c22_go_c32] = tuple(
        path + (selector,)
        for path in p74_c22_paths
        for selector in (p74_c22_1993, p74_c22_1994)
    )
    nested_flow_routes[p74_c23_go_c31] = tuple(
        path + (p74_c23_other,) for path in p74_c23_paths
    )
    nested_flow_routes[p74_c24_no] = p74_c24_paths
    for selector in (p74_c18_1993_route, p74_c18_1994):
        nested_flow_routes[selector] = p74_c18_paths
    p74_c19_paths = tuple(path + (p74_c18_1994,) for path in p74_c18_paths)
    for selector in (p74_c19_yes, p74_c19_no):
        nested_flow_routes[selector] = p74_c19_paths
    for selector in (
        p74_c21_promotion,
        p74_c21_major_change,
        p74_c21_other,
    ):
        nested_flow_routes[selector] = p74_c21_paths
    nested_flow_routes[p74_c21_terminal] = tuple(
        path + (selector,)
        for path in p74_c21_paths
        for selector in (
            p74_c21_promotion,
            p74_c21_major_change,
            p74_c21_other,
        )
    )
    for selector in (
        p74_c26_promotion,
        p74_c26_major_change,
        p74_c26_other,
    ):
        nested_flow_routes[selector] = p74_c26_paths
    nested_flow_routes[p74_c26_terminal] = tuple(
        path + (selector,)
        for path in p74_c26_paths
        for selector in (
            p74_c26_promotion,
            p74_c26_major_change,
            p74_c26_other,
        )
    )
    for selector in (p76_wife, p76_no_wife):
        nested_flow_routes[selector] = ((p76_head_male,),)
    for selector in (
        p76_working,
        p76_temporary,
        p76_unemployed,
        p76_retired,
        p76_disabled,
        p76_keeping_house,
        p76_student,
        p76_other,
    ):
        nested_flow_routes[selector] = ((p76_head_male, p76_wife),)
    nested_flow_routes[p76_go_d4] = (
        (p76_head_male, p76_wife, p76_working),
        (p76_head_male, p76_wife, p76_temporary),
    )
    nested_flow_routes[p76_d3_yes] = p76_d3_entry_paths
    nested_flow_routes[p76_d3_yes_go] = tuple(
        path + (p76_d3_yes,) for path in p76_d3_entry_paths
    )
    nested_flow_routes[p76_d3_no_go] = p76_d3_entry_paths

    nested_flow_routes[p84_go_g5] = ((p84_all_others,),)
    for selector in (p84_g5_yes, p84_g5_no):
        nested_flow_routes[selector] = p84_g5_parent_paths
    for selector in (p84_g9a_yes, p84_g9a_no):
        nested_flow_routes[selector] = p84_g5_yes_paths
    for selector in (p84_g9b_reported, p84_g9b_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p84_g9a_yes,) for path in p84_g5_yes_paths
        )
    nested_flow_routes[p84_go_g9bb] = tuple(
        path + (p84_g9a_yes, p84_g9b_reported) for path in p84_g5_yes_paths
    )
    nested_flow_routes[p84_g9b_supplement] = tuple(
        path + (p84_g9a_yes, p84_g9b_unreported) for path in p84_g5_yes_paths
    )
    for selector in (p84_wife, p84_g9bb_other_route):
        nested_flow_routes[selector] = p84_g9bb_entry_paths
    for selector in (p84_g9c_yes, p84_g9c_no):
        nested_flow_routes[selector] = tuple(
            path + (p84_wife,) for path in p84_g9bb_entry_paths
        )
    for selector in (p84_g9d_reported, p84_g9d_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p84_wife, p84_g9c_yes) for path in p84_g9bb_entry_paths
        )
    nested_flow_routes[p84_g9d_next] = tuple(
        path + (p84_wife, p84_g9c_yes, p84_g9d_reported)
        for path in p84_g9bb_entry_paths
    )
    nested_flow_routes[p84_g9d_supplement] = tuple(
        path + (p84_wife, p84_g9c_yes, p84_g9d_unreported)
        for path in p84_g9bb_entry_paths
    )

    nested_flow_routes[p86_go_g5] = ((p86_all_others,),)
    for selector in (p86_g5_yes, p86_g5_no):
        nested_flow_routes[selector] = p86_g5_parent_paths
    for selector in (p86_g9a_yes, p86_g9a_no):
        nested_flow_routes[selector] = p86_g5_yes_paths
    for selector in (p86_g9b_reported, p86_g9b_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p86_g9a_yes,) for path in p86_g5_yes_paths
        )
    nested_flow_routes[p86_go_g9bb] = tuple(
        path + (p86_g9a_yes, p86_g9b_reported) for path in p86_g5_yes_paths
    )
    nested_flow_routes[p86_g9b_supplement] = tuple(
        path + (p86_g9a_yes, p86_g9b_unreported) for path in p86_g5_yes_paths
    )
    for selector in (p86_wife, p86_g9bb_other_route):
        nested_flow_routes[selector] = p86_g9bb_entry_paths
    for selector in (p86_g9c_yes, p86_g9c_no):
        nested_flow_routes[selector] = tuple(
            path + (p86_wife,) for path in p86_g9bb_entry_paths
        )
    for selector in (p86_g9d_reported, p86_g9d_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p86_wife, p86_g9c_yes) for path in p86_g9bb_entry_paths
        )
    nested_flow_routes[p86_g9d_next] = tuple(
        path + (p86_wife, p86_g9c_yes, p86_g9d_reported)
        for path in p86_g9bb_entry_paths
    )
    nested_flow_routes[p86_g9d_supplement] = tuple(
        path + (p86_wife, p86_g9c_yes, p86_g9d_unreported)
        for path in p86_g9bb_entry_paths
    )

    for selector in (p88_corporation, p88_unincorporated, p88_other):
        nested_flow_routes[selector] = p88_business_form_entry_paths
    nested_flow_routes[p88_corporation_go] = tuple(
        path + (p88_corporation,) for path in p88_business_form_entry_paths
    )
    for selector in (p88_profit, p88_loss, p88_broke_even):
        nested_flow_routes[selector] = tuple(
            path + (owner,)
            for path in p88_business_form_entry_paths
            for owner in (p88_unincorporated, p88_other)
        )
    nested_flow_routes[p88_broke_go] = tuple(
        path + (owner, p88_broke_even)
        for path in p88_business_form_entry_paths
        for owner in (p88_unincorporated, p88_other)
    )
    for selector in (p88_one_business, p88_multiple_businesses):
        nested_flow_routes[selector] = p88_g11_result_paths
    nested_flow_routes[p88_repeat_business] = tuple(
        path + (p88_multiple_businesses,) for path in p88_g11_result_paths
    )
    nested_flow_routes[p88_g12_no] = p88_g12_entry_paths
    for selector in (p88_g16_to_g16a, p88_g16_to_g18):
        nested_flow_routes[selector] = tuple(
            path + (p88_g12_no,) for path in p88_g12_entry_paths
        )
    for selector in (p88_g14_yes, p88_g14_no):
        nested_flow_routes[selector] = p88_g12_entry_paths
    nested_flow_routes[p88_g14_yes_route] = tuple(
        path + (p88_g14_yes,) for path in p88_g12_entry_paths
    )
    nested_flow_routes[p88_g14_no_route] = tuple(
        path + (p88_g14_no,) for path in p88_g12_entry_paths
    )
    for selector in (p88_g17_reported, p88_g17_unreported):
        nested_flow_routes[selector] = p88_g17e_entry_paths
    nested_flow_routes[p88_g17_supplement] = tuple(
        path + (p88_g17_unreported,) for path in p88_g17e_entry_paths
    )

    for selector in (p90_corporation, p90_unincorporated, p90_other):
        nested_flow_routes[selector] = p90_business_form_entry_paths
    nested_flow_routes[p90_corporation_go] = tuple(
        path + (p90_corporation,) for path in p90_business_form_entry_paths
    )
    for selector in (p90_profit, p90_broke_even):
        nested_flow_routes[selector] = tuple(
            path + (owner,)
            for path in p90_business_form_entry_paths
            for owner in (p90_unincorporated, p90_other)
        )
    nested_flow_routes[p90_broke_go] = tuple(
        path + (owner, p90_broke_even)
        for path in p90_business_form_entry_paths
        for owner in (p90_unincorporated, p90_other)
    )
    for selector in (p90_one_business, p90_multiple_businesses):
        nested_flow_routes[selector] = p90_g11_result_paths
    nested_flow_routes[p90_repeat_business] = tuple(
        path + (p90_multiple_businesses,) for path in p90_g11_result_paths
    )
    nested_flow_routes[p90_g12_no] = p90_g12_entry_paths
    for selector in (p90_g16_to_g16a, p90_g16_to_g18):
        nested_flow_routes[selector] = tuple(
            path + (p90_g12_no,) for path in p90_g12_entry_paths
        )
    for selector in (p90_g14_yes, p90_g14_no):
        nested_flow_routes[selector] = p90_g12_entry_paths
    nested_flow_routes[p90_g14_yes_route] = tuple(
        path + (p90_g14_yes,) for path in p90_g12_entry_paths
    )
    nested_flow_routes[p90_g14_no_route] = tuple(
        path + (p90_g14_no,) for path in p90_g12_entry_paths
    )
    for selector in (p90_g17_reported, p90_g17_unreported):
        nested_flow_routes[selector] = p90_g17e_entry_paths
    nested_flow_routes[p90_g17_supplement] = tuple(
        path + (p90_g17_unreported,) for path in p90_g17e_entry_paths
    )
    nested_flow_routes[p106_all_others_go] = ((p106_wife, p106_all_others),)
    nested_flow_routes[p106_worked_go] = ((p106_wife, p106_worked),)
    nested_flow_routes[p106_hours_reported] = p106_g52_entry_paths
    nested_flow_routes[p106_hours_unreported] = p106_g52_entry_paths
    nested_flow_routes[p106_hours_supplement] = tuple(
        path + (p106_hours_unreported,) for path in p106_g52_entry_paths
    )
    nested_flow_routes[p106_income_yes] = ((p106_wife,),)
    nested_flow_routes[p106_income_other] = ((p106_wife,),)
    for selector in (p114_g21a, p114_g21b, p114_g21c):
        nested_flow_routes[selector] = ((p114_g21_other_work,),)
    for selector in p114_employer_categories:
        nested_flow_routes[selector] = p114_right_gj1_paths
    nested_flow_routes[p114_missing_employer] = p114_gj2_entry_paths
    nested_flow_routes[p92_g18a_no] = p92_g18a_entry_paths
    for selector in (p92_g21a_reported, p92_g21a_unreported):
        nested_flow_routes[selector] = p92_g18a_entry_paths
    nested_flow_routes[p92_g21a_supplement] = tuple(
        path + (p92_g21a_unreported,) for path in p92_g18a_entry_paths
    )
    for selector in (p92_g18b_yes, p92_g18b_no):
        nested_flow_routes[selector] = p92_g18b_entry_paths
    for selector in (p92_g21b_reported, p92_g21b_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p92_g18b_yes,) for path in p92_g18b_entry_paths
        )
    nested_flow_routes[p92_g21b_supplement] = tuple(
        path + (p92_g18b_yes, p92_g21b_unreported)
        for path in p92_g18b_entry_paths
    )
    for selector in (p92_g18c_yes, p92_g18c_no):
        nested_flow_routes[selector] = p92_g18c_entry_paths
    for selector in (p92_g21c_reported, p92_g21c_unreported):
        nested_flow_routes[selector] = tuple(
            path + (p92_g18c_yes,) for path in p92_g18c_entry_paths
        )
    nested_flow_routes[p92_g21c_supplement] = tuple(
        path + (p92_g18c_yes, p92_g21c_unreported)
        for path in p92_g18c_entry_paths
    )
    for selector in (p94_extra_job, p94_all_others):
        nested_flow_routes[selector] = p92_g22_entry_paths
    for selector in (p94_g23_no, p94_g23_yes):
        nested_flow_routes[selector] = tuple(
            path + (p94_extra_job,) for path in p92_g22_entry_paths
        )
    nested_flow_routes[p116_business_origin] = ((),)
    nested_flow_routes[p116_all_origins] = ((),)
    nested_flow_routes[p116_go_gj4] = ((p116_business_origin,),)
    for selector in (p116_stopped_yes, p116_stopped_no):
        nested_flow_routes[selector] = p116_gj4_entry_paths
    nested_flow_routes[p116_go_gj11] = ((p116_stopped_no,),)
    for selector in (
        p116_return_g9b,
        p116_return_g9d,
        p116_return_g17e,
        p116_return_g52b,
        p116_terminal_g21a,
        p116_terminal_g21b,
        p116_terminal_g21c,
    ):
        nested_flow_routes[selector] = p116_gj11_entry_paths
    for terminal, return_route in (
        (p116_terminal_g21a, p116_return_g21a),
        (p116_terminal_g21b, p116_return_g21b),
        (p116_terminal_g21c, p116_return_g21c),
    ):
        nested_flow_routes[return_route] = ((terminal,),)
    for key, routes in nested_flow_routes.items():
        flow_by_key[key]["routes"] = set(routes)

    for row in flow_rows:
        row["review_id"] = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )

    resolved_flow_paths: dict[tuple[int, int, int], list[list[str]]] = {}
    resolved_flow_path_sets: dict[
        tuple[int, int, int], set[tuple[str, ...]]
    ] = {}
    resolved_branch_ref_cache: dict[
        tuple[tuple[int, int, int], tuple[str, ...]], str
    ] = {}
    resolved_route_cache: dict[tuple[tuple[int, int, int], ...], list[str]] = (
        {}
    )

    def resolve_route(
        route: Sequence[tuple[int, int, int]],
    ) -> list[str]:
        route_key = tuple(route)
        cached = resolved_route_cache.get(route_key)
        if cached is not None:
            return cached
        prefix: list[str] = []
        for parent_key in route_key:
            parent = flow_by_key[parent_key]
            parent_paths = resolved_flow_paths[parent_key]
            prefix_key = tuple(prefix)
            if prefix_key not in resolved_flow_path_sets[parent_key]:
                raise ValueError(
                    f"flow ancestry cannot resolve {route_key} via {parent_key}"
                )
            cache_key = (parent_key, prefix_key)
            branch_ref = resolved_branch_ref_cache.get(cache_key)
            if branch_ref is None:
                branch_ref = annotation._review_branch_ref(
                    parent["review_id"], prefix, len(parent_paths)
                )
                resolved_branch_ref_cache[cache_key] = branch_ref
            prefix.append(branch_ref)
        resolved_route_cache[route_key] = prefix
        return prefix

    for row in flow_rows:
        key = (row["page"], row["start"], row["end"])
        resolved = [resolve_route(route) for route in sorted(row["routes"])]
        resolved_flow_paths[key] = resolved
        resolved_flow_path_sets[key] = {
            tuple(parent_path) for parent_path in resolved
        }

    def resolve_routes(
        routes: Sequence[Sequence[tuple[int, int, int]]],
    ) -> list[list[str]]:
        return [resolve_route(route) for route in routes]

    occurrence_specs: list[dict[str, Any]] = []
    id_by_key: dict[tuple[int, int, int, str], str] = {}
    for row in ordered_specs:
        review_occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
        id_by_key[(row["page"], row["start"], row["end"], row["kind"])] = (
            review_occurrence_id
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

    occurrence_by_id = {
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
        raw = page_texts[page - 1].encode("utf-8")[
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ]
        label = raw.decode("utf-8", errors="strict")
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
            nested = [
                parent
                for parent in parent_anchor_specs
                if parent["page_number"] == page
                and branch_compatible(spec, parent)
                and (
                    spec["utf8_byte_start"]
                    <= parent["utf8_byte_start"]
                    < parent["utf8_byte_end"]
                    <= spec["utf8_byte_end"]
                    or parent["utf8_byte_start"]
                    <= spec["utf8_byte_start"]
                    < spec["utf8_byte_end"]
                    <= parent["utf8_byte_end"]
                )
            ]
            parent_ids = [parent["review_occurrence_id"] for parent in nested]
            parent_ids.sort(
                key=lambda review_id: occurrence_specs.index(
                    occurrence_by_id[review_id]
                )
            )
        if kind not in {"context_anchor", "remuneration_component_anchor"}:
            parent_note = "Parent resolution is not applicable to this non-component anchor."
        elif parent_ids:
            parent_note = "Explicit source-local parent anchors were verified in the same source block."
        else:
            parent_note = (
                "Whole-page review found no explicit source-local parent anchor; "
                "parent resolution is preserved for later global assembly."
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

    repeat_instruction_coordinates = {
        (27, 1162, 1187),
        (51, 139, 482),
        (51, 491, 871),
        (57, 183, 347),
        (67, 865, 965),
        (69, 175, 298),
        (87, 644, 705),
        (88, 1540, 1584),
        (89, 1572, 1670),
        (90, 1404, 1448),
        (119, 3009, 3050),
        (121, 829, 925),
        (122, 5272, 5309),
        (126, 2559, 2793),
        (127, 257, 304),
    }
    cross_reference_coordinates = {
        (23, 270, 438),
        (24, 1302, 1318),
        (25, 108, 509),
        (35, 104, 462),
        (39, 1020, 1098),
        (41, 1351, 1759),
        (43, 100, 172),
        (43, 1893, 2049),
        (43, 2050, 2198),
        (47, 199, 231),
        (47, 232, 402),
        (47, 677, 711),
        (49, 94, 125),
        (49, 835, 866),
        (51, 1629, 1787),
        (51, 1788, 1818),
        (52, 35, 280),
        (52, 885, 1399),
        (53, 45, 83),
        (53, 85, 120),
        (55, 87, 119),
        (55, 120, 309),
        (55, 310, 345),
        (57, 90, 118),
        (57, 119, 152),
        (57, 153, 182),
        (67, 100, 121),
        (69, 338, 372),
        (71, 626, 735),
        (71, 736, 950),
        (73, 43, 79),
        (73, 80, 110),
        (73, 111, 141),
        (75, 102, 439),
        (75, 441, 561),
        (77, 257, 455),
        (77, 597, 862),
        (77, 1039, 1154),
        (77, 1164, 1400),
        (79, 346, 454),
        (85, 608, 800),
        (93, 2987, 3363),
        (107, 434, 559),
        (115, 1213, 1233),
        (115, 1341, 1415),
        (125, 160, 225),
        (130, 2461, 2517),
        (233, 823, 887),
        (283, 1042, 1305),
    }
    same_label_coordinates = {
        (84, 2362, 2407),
        (84, 3138, 3218),
        (86, 2359, 2404),
        (86, 3167, 3212),
    }
    repeat_instruction_coordinates = {
        coordinate
        for coordinate in repeat_instruction_coordinates
        if coordinate[0] not in out_of_scope_pages
    }
    cross_reference_coordinates = {
        coordinate
        for coordinate in cross_reference_coordinates
        if coordinate[0] not in out_of_scope_pages
    }
    relation_by_coordinate = {
        **{
            coordinate: "explicit_repeat_instruction"
            for coordinate in repeat_instruction_coordinates
        },
        **{
            coordinate: "explicit_cross_reference"
            for coordinate in cross_reference_coordinates
        },
        **{
            coordinate: "same_printed_identifier_and_exact_label"
            for coordinate in same_label_coordinates
        },
    }
    actual_repeat_coordinates = {
        (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        for spec in occurrence_specs
        if spec["occurrence_kind"] == "repeat_or_alias_instruction"
    }
    if (
        repeat_instruction_coordinates & cross_reference_coordinates
        or repeat_instruction_coordinates & same_label_coordinates
        or cross_reference_coordinates & same_label_coordinates
        or set(relation_by_coordinate) != actual_repeat_coordinates
    ):
        raise ValueError("reviewed repeat relation coordinate cover drift")

    local_repeat_bindings = {
        (39, 1020, 1098): {
            "canonical": [(39, 846, 854, "job_anchor")],
            "alias": [(39, 1048, 1066, "job_anchor")],
        },
        (41, 1351, 1759): {
            "canonical": [(39, 846, 854, "job_anchor")],
            "alias": [
                (40, 63, 79, "job_anchor"),
                (41, 1390, 1406, "job_anchor"),
                (41, 1477, 1490, "job_anchor"),
                (41, 1546, 1554, "job_anchor"),
            ],
        },
        (49, 94, 125): {
            "canonical": [(42, 461, 522, "context_anchor")],
            "alias": [(48, 219, 286, "context_anchor")],
        },
        (52, 885, 1399): {
            "canonical": [(52, 993, 1001, "job_anchor")],
            "alias": [
                (52, 1085, 1093, "job_anchor"),
                (52, 1185, 1194, "job_anchor"),
            ],
        },
        (57, 90, 118): {
            "canonical": [(42, 461, 522, "context_anchor")],
            "alias": [(56, 8, 87, "context_anchor")],
        },
        (77, 257, 455): {
            "canonical": [(77, 430, 434, "role_anchor")],
            "alias": [(77, 257, 263, "role_anchor")],
        },
        (84, 2362, 2407): {
            "canonical": [(84, 2389, 2398, "job_anchor")],
            "alias": [(86, 2386, 2395, "job_anchor")],
            "repeat_coordinates": [(84, 2362, 2407), (86, 2359, 2404)],
        },
        (86, 2359, 2404): {
            "canonical": [(84, 2389, 2398, "job_anchor")],
            "alias": [(86, 2386, 2395, "job_anchor")],
            "repeat_coordinates": [(84, 2362, 2407), (86, 2359, 2404)],
        },
        (84, 3138, 3218): {
            "canonical": [(84, 3200, 3209, "job_anchor")],
            "alias": [(86, 3194, 3203, "job_anchor")],
            "repeat_coordinates": [(84, 3138, 3218), (86, 3167, 3212)],
        },
        (86, 3167, 3212): {
            "canonical": [(84, 3200, 3209, "job_anchor")],
            "alias": [(86, 3194, 3203, "job_anchor")],
            "repeat_coordinates": [(84, 3138, 3218), (86, 3167, 3212)],
        },
        (87, 644, 705): {
            "canonical": [
                (88, 280, 286, "remuneration_component_anchor"),
                (88, 290, 294, "remuneration_component_anchor"),
            ],
            "alias": [
                (90, 285, 291, "remuneration_component_anchor"),
                (90, 295, 299, "remuneration_component_anchor"),
            ],
            "repeat_coordinates": [
                (87, 644, 705),
                (88, 1540, 1584),
                (89, 1572, 1670),
                (90, 1404, 1448),
            ],
        },
        (88, 1540, 1584): {
            "canonical": [
                (88, 280, 286, "remuneration_component_anchor"),
                (88, 290, 294, "remuneration_component_anchor"),
            ],
            "alias": [
                (90, 285, 291, "remuneration_component_anchor"),
                (90, 295, 299, "remuneration_component_anchor"),
            ],
            "repeat_coordinates": [
                (87, 644, 705),
                (88, 1540, 1584),
                (89, 1572, 1670),
                (90, 1404, 1448),
            ],
        },
        (89, 1572, 1670): {
            "canonical": [
                (88, 280, 286, "remuneration_component_anchor"),
                (88, 290, 294, "remuneration_component_anchor"),
            ],
            "alias": [
                (90, 285, 291, "remuneration_component_anchor"),
                (90, 295, 299, "remuneration_component_anchor"),
            ],
            "repeat_coordinates": [
                (87, 644, 705),
                (88, 1540, 1584),
                (89, 1572, 1670),
                (90, 1404, 1448),
            ],
        },
        (90, 1404, 1448): {
            "canonical": [
                (88, 280, 286, "remuneration_component_anchor"),
                (88, 290, 294, "remuneration_component_anchor"),
            ],
            "alias": [
                (90, 285, 291, "remuneration_component_anchor"),
                (90, 295, 299, "remuneration_component_anchor"),
            ],
            "repeat_coordinates": [
                (87, 644, 705),
                (88, 1540, 1584),
                (89, 1572, 1670),
                (90, 1404, 1448),
            ],
        },
        (233, 823, 887): {
            "canonical": [
                (232, 640, 802, "context_anchor"),
                (232, 754, 767, "job_anchor"),
            ],
            "alias": [
                (232, 1235, 1392, "context_anchor"),
                (232, 1344, 1357, "job_anchor"),
            ],
        },
    }
    business_repeat_coordinates = [
        (87, 644, 705),
        (88, 1540, 1584),
        (89, 1572, 1670),
        (90, 1404, 1448),
    ]
    business_repeat_binding = {
        "canonical": [
            (84, 1795, 1855, "context_anchor"),
            (84, 1835, 1843, "business_aggregate_anchor"),
            (84, 1879, 1887, "business_aggregate_anchor"),
            (84, 1935, 1943, "business_aggregate_anchor"),
            (84, 2011, 2015, "role_anchor"),
            (84, 2027, 2031, "role_anchor"),
            (84, 2032, 2038, "role_anchor"),
            (84, 2122, 2126, "role_anchor"),
            (84, 2158, 2166, "business_aggregate_anchor"),
            (84, 2389, 2398, "job_anchor"),
            (84, 2673, 2676, "job_anchor"),
            (84, 2801, 2807, "role_anchor"),
            (84, 2898, 2902, "role_anchor"),
            (84, 2903, 2909, "role_anchor"),
            (84, 2941, 2949, "business_aggregate_anchor"),
            (84, 3200, 3209, "job_anchor"),
            (84, 3524, 3527, "job_anchor"),
            (88, 17, 28, "business_aggregate_anchor"),
            (88, 35, 49, "business_aggregate_anchor"),
            (88, 50, 58, "business_aggregate_anchor"),
            (88, 73, 84, "business_aggregate_anchor"),
            (88, 98, 112, "business_aggregate_anchor"),
            (88, 264, 272, "business_aggregate_anchor"),
            (88, 280, 286, "remuneration_component_anchor"),
            (88, 290, 294, "remuneration_component_anchor"),
            (88, 347, 353, "remuneration_component_anchor"),
            (88, 761, 769, "business_aggregate_anchor"),
            (88, 839, 843, "remuneration_component_anchor"),
            (88, 894, 900, "remuneration_component_anchor"),
            (88, 939, 947, "business_aggregate_anchor"),
            (88, 1251, 1261, "business_aggregate_anchor"),
            (88, 1281, 1289, "business_aggregate_anchor"),
            (88, 1576, 1584, "business_aggregate_anchor"),
            (88, 1600, 1604, "role_anchor"),
            (88, 1606, 1610, "remuneration_component_anchor"),
            (88, 1611, 1616, "remuneration_component_anchor"),
            (88, 1620, 1628, "remuneration_component_anchor"),
            (88, 1657, 1661, "job_anchor"),
            (88, 1684, 1698, "business_aggregate_anchor"),
            (88, 1699, 1707, "business_aggregate_anchor"),
            (88, 1802, 1807, "remuneration_component_anchor"),
            (88, 1811, 1819, "remuneration_component_anchor"),
            (88, 1829, 1832, "job_anchor"),
            (88, 2048, 2052, "role_anchor"),
            (88, 2054, 2058, "remuneration_component_anchor"),
            (88, 2149, 2154, "remuneration_component_anchor"),
            (88, 2188, 2195, "remuneration_component_anchor"),
            (88, 2197, 2205, "remuneration_component_anchor"),
            (88, 2207, 2211, "remuneration_component_anchor"),
            (88, 2235, 2243, "remuneration_component_anchor"),
            (88, 2290, 2302, "remuneration_component_anchor"),
            (88, 2757, 2764, "remuneration_component_anchor"),
            (88, 2785, 2793, "remuneration_component_anchor"),
            (88, 2795, 2799, "remuneration_component_anchor"),
            (88, 2804, 2816, "remuneration_component_anchor"),
            (88, 3182, 3189, "remuneration_component_anchor"),
            (88, 3232, 3240, "remuneration_component_anchor"),
            (88, 3318, 3322, "remuneration_component_anchor"),
            (88, 3408, 3420, "remuneration_component_anchor"),
            (88, 3721, 3724, "job_anchor"),
        ],
        "alias": [
            (86, 1730, 1800, "context_anchor"),
            (86, 1780, 1788, "business_aggregate_anchor"),
            (86, 1825, 1833, "business_aggregate_anchor"),
            (86, 1881, 1889, "business_aggregate_anchor"),
            (86, 1952, 1956, "role_anchor"),
            (86, 1966, 1970, "role_anchor"),
            (86, 1972, 1978, "role_anchor"),
            (86, 2070, 2074, "role_anchor"),
            (86, 2106, 2114, "business_aggregate_anchor"),
            (86, 2386, 2395, "job_anchor"),
            (86, 2658, 2661, "job_anchor"),
            (86, 2783, 2789, "role_anchor"),
            (86, 2909, 2913, "role_anchor"),
            (86, 2914, 2920, "role_anchor"),
            (86, 2952, 2960, "business_aggregate_anchor"),
            (86, 3194, 3203, "job_anchor"),
            (86, 3512, 3515, "job_anchor"),
            (90, 17, 28, "business_aggregate_anchor"),
            (90, 35, 49, "business_aggregate_anchor"),
            (90, 50, 58, "business_aggregate_anchor"),
            (90, 73, 84, "business_aggregate_anchor"),
            (90, 98, 112, "business_aggregate_anchor"),
            (90, 269, 277, "business_aggregate_anchor"),
            (90, 285, 291, "remuneration_component_anchor"),
            (90, 295, 299, "remuneration_component_anchor"),
            (90, 675, 683, "business_aggregate_anchor"),
            (90, 757, 761, "remuneration_component_anchor"),
            (90, 812, 818, "remuneration_component_anchor"),
            (90, 861, 869, "business_aggregate_anchor"),
            (90, 1194, 1204, "business_aggregate_anchor"),
            (90, 1224, 1232, "business_aggregate_anchor"),
            (90, 1440, 1448, "business_aggregate_anchor"),
            (90, 1464, 1468, "role_anchor"),
            (90, 1470, 1474, "remuneration_component_anchor"),
            (90, 1475, 1480, "remuneration_component_anchor"),
            (90, 1484, 1492, "remuneration_component_anchor"),
            (90, 1521, 1525, "job_anchor"),
            (90, 1548, 1562, "business_aggregate_anchor"),
            (90, 1563, 1571, "business_aggregate_anchor"),
            (90, 1666, 1671, "remuneration_component_anchor"),
            (90, 1675, 1683, "remuneration_component_anchor"),
            (90, 1693, 1696, "job_anchor"),
            (90, 1912, 1916, "role_anchor"),
            (90, 1918, 1922, "remuneration_component_anchor"),
            (90, 2017, 2022, "remuneration_component_anchor"),
            (90, 2060, 2067, "remuneration_component_anchor"),
            (90, 2069, 2077, "remuneration_component_anchor"),
            (90, 2079, 2083, "remuneration_component_anchor"),
            (90, 2107, 2115, "remuneration_component_anchor"),
            (90, 2166, 2177, "remuneration_component_anchor"),
            (90, 2646, 2653, "remuneration_component_anchor"),
            (90, 2674, 2682, "remuneration_component_anchor"),
            (90, 2684, 2688, "remuneration_component_anchor"),
            (90, 2693, 2704, "remuneration_component_anchor"),
            (90, 3119, 3126, "remuneration_component_anchor"),
            (90, 3173, 3181, "remuneration_component_anchor"),
            (90, 3265, 3269, "remuneration_component_anchor"),
            (90, 3356, 3367, "remuneration_component_anchor"),
            (90, 3683, 3686, "job_anchor"),
        ],
        "repeat_coordinates": business_repeat_coordinates,
    }
    for coordinate in business_repeat_coordinates:
        local_repeat_bindings[coordinate] = business_repeat_binding
    target_scope_by_coordinate = {
        (23, 270, 438): "cross_document",
        (67, 865, 965): "cross_document",
        (75, 441, 561): "cross_document",
        (77, 597, 862): "cross_document",
        (77, 1039, 1154): "cross_document",
        (77, 1164, 1400): "cross_document",
        (51, 491, 871): "unresolved",
        (52, 35, 280): "unresolved",
        (79, 346, 454): "unresolved",
        (85, 608, 800): "unresolved",
    }
    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }

    repeat_alias_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != "repeat_or_alias_instruction":
            continue
        coordinate = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        binding = local_repeat_bindings.get(coordinate)
        canonical_ids = (
            []
            if binding is None
            else sorted(
                [id_by_key[key] for key in binding["canonical"]],
                key=occurrence_order.__getitem__,
            )
        )
        alias_ids = (
            []
            if binding is None
            else sorted(
                [id_by_key[key] for key in binding["alias"]],
                key=occurrence_order.__getitem__,
            )
        )
        related_repeat_ids = (
            [spec["review_occurrence_id"]]
            if binding is None
            else [
                id_by_key[(*repeat_coordinate, "repeat_or_alias_instruction")]
                for repeat_coordinate in binding.get(
                    "repeat_coordinates", [coordinate]
                )
            ]
        )
        evidence_ids = sorted(
            {
                *related_repeat_ids,
                *canonical_ids,
                *alias_ids,
            },
            key=occurrence_order.__getitem__,
        )
        repeat_alias_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "relation": relation_by_coordinate[coordinate],
                "alias_anchor_review_occurrence_ids": alias_ids,
                "canonical_anchor_review_occurrence_ids": canonical_ids,
                "evidence_review_occurrence_ids": evidence_ids,
                "target_scope": target_scope_by_coordinate.get(
                    coordinate, "document_local"
                ),
                "resolution_status": (
                    "preserved_for_global_resolution"
                    if binding is None
                    else "document_local_source_evidence_complete"
                ),
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
            "whole_page_review": "all_289_pages_including_empty_occurrence_pages",
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
