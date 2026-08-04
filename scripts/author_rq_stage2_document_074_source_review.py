#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 74.

This one-document authoring helper encodes the completed whole-page review as
explicit source windows and exact UTF-8 spans.  It deliberately never opens the
stage-1 candidate artifact.  Direct lexical detection is used only to enumerate
anchor lexemes inside reviewer-approved semantic windows; flow, purpose,
context, and repeat evidence are all stated explicitly below.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_074_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]
FLOW_ROOT = "questionnaire-flow:root"


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


def _inside(
    page_number: int,
    start: int,
    end: int,
    windows: dict[int, tuple[tuple[int, int], ...]],
) -> bool:
    return any(
        window_start <= start < end <= window_end
        for window_start, window_end in windows.get(page_number, ())
    )


def _pension_type_routes(
    plan_types: Iterable[str], *, loops: bool = False
) -> list[tuple[str, ...]]:
    prefix = ("former_summary", "former_detail")
    if not loops:
        return [(*prefix, plan_type) for plan_type in plan_types]
    return [
        (*prefix, plan_type, loop)
        for plan_type in plan_types
        for loop in ("former_loop_1", "former_loop_2")
    ]


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]
    interview_wave = document["interview_waves"][0]

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        page_bytes = page_texts[page - 1].encode("utf-8")
        while start < end and page_bytes[start : start + 1] in b" \t\r\n":
            start += 1
        while end > start and page_bytes[end - 1 : end] in b" \t\r\n":
            end -= 1
        if start >= end:
            raise ValueError(f"empty span after trimming: page={page}")
        return start, end

    # These are the only source windows in which lexical anchors survived the
    # page-by-page semantic review.  All omitted portions of all 142 pages were
    # explicitly reviewed and adjudicated as empty for R_Q.
    anchor_windows: dict[int, tuple[tuple[int, int], ...]] = {
        **{
            page: ((0, len(page_texts[page - 1].encode("utf-8"))),)
            for page in range(21, 31)
        },
        31: ((162, 711),),
        **{
            page: ((0, len(page_texts[page - 1].encode("utf-8"))),)
            for page in range(42, 48)
        },
        54: ((170, 2004),),
        60: ((0, len(page_texts[59].encode("utf-8"))),),
        61: ((0, len(page_texts[60].encode("utf-8"))),),
        69: ((119, 398),),
        **{
            page: ((0, len(page_texts[page - 1].encode("utf-8"))),)
            for page in range(86, 97)
        },
        118: ((5, 473),),
        120: ((5, 465),),
        122: ((1246, 1346),),
        123: ((97, 1061),),
        140: ((1825, 2535),),
        141: ((95, 806),),
    }

    flow_defs: list[dict[str, Any]] = []

    def flow(
        symbol: str,
        page: int,
        start: int,
        end: int,
        parents: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source routing clause retained after whole-page review.",
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

    # Employment QxQ routing and occupation/industry probe branches.
    flow("employer_name_missing", 22, 2065, 2129)
    flow("paid_activity", 22, 2698, 2739)
    flow("paid_but_not_considered", 22, 2765, 2822, (("paid_activity",),))
    flow("bank_example", 23, 1562, 1632)
    flow("engineer_example", 23, 1970, 2001)
    flow("road_worker", 23, 2519, 2572)
    flow("road_foreman", 23, 2671, 2706, (("road_worker",),))
    flow("road_operative", 23, 2750, 2783, (("road_worker",),))
    flow("road_laborer", 23, 2828, 2861, (("road_worker",),))
    flow("college_teacher", 23, 3223, 3243)
    flow("both_self_and_other", 24, 388, 473)
    flow("government_employer", 24, 2552, 2581)
    flow("machine_operator", 24, 2923, 2952)
    flow("college_level", 24, 3287, 3310)
    flow("manager_or_supervisor", 25, 1700, 1738)
    flow("works_at_home", 25, 1884, 1928)
    flow("cannot_separate_employment", 25, 2805, 2820)
    flow("other_business_category", 26, 229, 313)
    flow("llc_or_llp", 26, 355, 458)
    flow("large_employer_example", 26, 1017, 1041)
    flow("self_employed_none", 26, 1170, 1226)
    flow("fixed_income", 27, 546, 737)
    flow("fixed_salary_plus_overtime", 27, 738, 835)
    flow("no_overtime", 28, 687, 732)
    flow("company_changed_owners", 29, 910, 951)
    flow("same_employer_multiple_times", 29, 993, 1082)
    flow("unpaid_overtime", 29, 1370, 1438)
    flow("ads_example", 30, 357, 401)
    flow("probe_ads", 30, 507, 525, (("ads_example",),))
    flow("internet_answer", 30, 629, 743)
    flow("roomers_or_boarders", 31, 172, 215)
    flow(
        "cannot_separate_housework", 31, 474, 509, (("roomers_or_boarders",),)
    )

    # Section G and off-year labor-income routing.
    flow("section_g_hours", 42, 36, 95)
    flow("employment_hours_to_income", 42, 192, 277)
    flow("missing_income_or_hours", 43, 990, 1042)
    flow("repeat_business_g5", 43, 1261, 1314)
    flow("repeat_business_g6", 43, 1745, 1798)
    flow("repeat_business_g7", 43, 2323, 2376)
    flow("head_work_time", 44, 154, 182)
    flow("head_hours_missing", 44, 242, 248)
    flow("wife_work_time", 44, 376, 415)
    flow("wife_hours_missing", 44, 475, 481)
    flow("llc_classification", 44, 580, 680)
    flow("ownership_unknown", 44, 718, 778)
    flow("incorporation_unknown", 44, 779, 905)
    flow("g11_values_present", 45, 298, 331)
    flow("draw_in_total", 45, 458, 597)
    flow("nonowner_wages", 45, 781, 912)
    flow("owner_separate_share", 45, 1056, 1107)
    flow("only_total_known", 45, 1260, 1293, (("owner_separate_share",),))
    flow("head_worked_2012", 45, 1922, 1949)
    flow("multiple_head_jobs", 46, 215, 240)
    flow("current_salary_rate", 46, 415, 447)
    flow("complicated_work_history", 46, 658, 740)
    flow("g11b_and_g13", 46, 1147, 1190)
    flow("already_included_income", 46, 1430, 1522)
    flow("earnings_only_supplements", 46, 1564, 1630)
    flow("missing_work_hours", 46, 1818, 1930)
    flow("head_farming_occupation", 47, 783, 816)
    flow("head_current_job_not_farming", 47, 911, 977)
    flow("jobs_hours_missing", 47, 1989, 2070)
    flow("late_missing_hours", 47, 2149, 2232)
    flow("other_jobs_g23", 47, 2402, 2478)
    flow("other_jobs_g24", 47, 2583, 2659)
    flow("wife_business_income", 54, 718, 845)
    flow("wife_business_income_g52", 54, 1348, 1475)
    flow("wife_hours_missing_g52b", 54, 1851, 1923)
    flow("ofum_irregular_g76", 60, 1449, 1492)
    flow("ofum_irregular_g77", 60, 1788, 1831)
    flow("g78_rate", 61, 150, 201)
    flow("ofum_irregular_g78", 61, 257, 300)
    flow("ofum_irregular_g79", 61, 642, 685)
    flow("ofum_irregular_g80", 61, 854, 897)
    flow("g81_irregular_hours", 61, 1066, 1127)
    flow("ofum_irregular_g81", 61, 1219, 1262)
    flow("offyear_head_or_wife", 69, 119, 225)

    # Pension routing: repeated current/former summaries, plan-type alternatives,
    # and former-plan loops are explicit source branches rather than selected paths.
    flow("current_summary", 86, 344, 520)
    flow("former_summary", 86, 546, 726)
    flow("head_never_worked", 86, 739, 813)
    flow("wife_present", 86, 814, 866, (("head_never_worked",),))
    flow("wife_never_worked", 86, 867, 951)
    flow("current_detail", 86, 1983, 2149, (("current_summary",),))
    flow("former_detail", 86, 2170, 2347, (("former_summary",),))
    flow(
        "head_never_detail",
        86,
        2368,
        2458,
        (("head_never_worked", "wife_present"),),
    )
    flow(
        "wife_present_detail",
        86,
        2478,
        2518,
        (("head_never_worked", "wife_present", "head_never_detail"),),
    )
    flow(
        "current_multiple_plans",
        86,
        2733,
        2904,
        (("current_summary", "current_detail"),),
    )
    current = ("current_summary", "current_detail")
    flow("plan_both", 88, 294, 384, (current,))
    # Include the physical-line-final "If" in the exact DB condition.
    db_start, _ = _byte_find(page_texts[87], "If\n", 481)
    flow("plan_db", 88, db_start, 718, (current,))
    flow("plan_dc", 88, 1002, 1076, (current,))
    dc_and_both = (
        (*current, "plan_dc"),
        (*current, "plan_both"),
    )
    all_current_types = (
        (*current, "plan_db"),
        (*current, "plan_dc"),
        (*current, "plan_both"),
    )
    flow("p18_amount_condition", 89, 1140, 1250, dc_and_both)
    flow("p18_percent_condition", 89, 1351, 1461, dc_and_both)
    flow("employer_matches", 89, 1476, 1644, dc_and_both)
    flow("p18_percent_b_condition", 89, 1646, 1755, dc_and_both)
    flow("p32_years_instead_of_age", 90, 1619, 1668, all_current_types)
    flow("p44_employer_matches", 92, 751, 925, all_current_types)
    former = ("former_summary", "former_detail")
    flow("former_type_a", 93, 712, 727, (former,))
    flow("former_type_b", 93, 732, 752, (former,))
    flow("former_type_both", 93, 924, 938, (former,))
    former_types = (
        (*former, "former_type_a"),
        (*former, "former_type_b"),
        (*former, "former_type_both"),
    )
    flow("former_loop_1", 93, 1127, 1248, former_types)
    flow("former_loop_2", 93, 1267, 1368, former_types)
    former_b_and_both = _pension_type_routes(
        ("former_type_b", "former_type_both"), loops=True
    )
    flow("p48_multiple_response", 93, 2528, 2657, former_b_and_both)
    former_b = _pension_type_routes(("former_type_b",), loops=True)
    flow("p66_account_converted", 96, 1552, 1623, former_b)
    flow(
        "p66_year_answer",
        96,
        1796,
        1820,
        tuple((*route, "p66_account_converted") for route in former_b),
    )
    all_former_types = _pension_type_routes(
        ("former_type_a", "former_type_b", "former_type_both"), loops=True
    )
    flow("p69_another_plan", 96, 2386, 2516, all_former_types)
    flow(
        "p69_open_loop",
        96,
        2517,
        2590,
        tuple((*route, "p69_another_plan") for route in all_former_types),
    )

    # Remaining lawful KL/IO routing clauses.
    father_flow_start, father_flow_end = _byte_find(
        page_texts[117],
        "If he wasn’t doing any work for money or\n              you get a “DON’T KNOW” or “REFUSED” here, do not ask KL11.",
    )
    mother_flow_start, mother_flow_end = _byte_find(
        page_texts[119],
        "If he wasn’t doing any work for\n              money or you get a “DON’T KNOW” or “REFUSED” here, do not ask KL21.",
    )
    flow("father_no_paid_work", 118, father_flow_start, father_flow_end)
    flow("mother_no_paid_work", 120, mother_flow_start, mother_flow_end)
    flow("kl70_response_rule", 123, 520, 739)
    flow("kl73_missing_detail", 123, 976, 1061)

    flow_defs.sort(
        key=lambda row: (row["page"], row["start"], row["end"], row["symbol"])
    )
    flow_by_symbol = {row["symbol"]: row for row in flow_defs}
    if len(flow_by_symbol) != len(flow_defs):
        raise ValueError("duplicate flow symbol")
    resolved_flow_paths: dict[str, list[list[str]]] = {}
    for row in flow_defs:
        occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            "flow_branch_label",
        )
        row["review_id"] = occurrence_id
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
        if len(resolved) != len({tuple(path) for path in resolved}):
            raise ValueError(f"duplicate flow route for {row['symbol']}")
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

    specs: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    def add(
        page: int,
        start: int,
        end: int,
        kind: str,
        routes: Sequence[Sequence[str]] = ((),),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        start, end = trim_span(page, start, end)
        key = (page, start, end, kind)
        current_row = specs.get(key)
        route_set = {tuple(route) for route in routes}
        if current_row is None:
            specs[key] = {
                "page": page,
                "start": start,
                "end": end,
                "kind": kind,
                "routes": route_set,
                "note": note,
            }
        else:
            current_row["routes"].update(route_set)

    for row in flow_defs:
        add(
            row["page"],
            row["start"],
            row["end"],
            "flow_branch_label",
            row["routes"],
            row["note"],
        )

    def pension_routes(page: int, start: int) -> list[tuple[str, ...]]:
        if page == 86:
            if 1232 <= start < 1983:
                return [("current_summary",)]
            if 1983 <= start < 2170:
                return [current]
            if 2170 <= start < 2368:
                return [former]
            if 2368 <= start < 2520:
                return [
                    (
                        "head_never_worked",
                        "wife_present",
                        "head_never_detail",
                    )
                ]
            if start >= 2520:
                return [current]
            return [()]
        if page == 87:
            return [current]
        if page == 88:
            if start < 294:
                return [current]
            if 294 <= start < 393:
                return [(*current, "plan_both")]
            if 393 <= start < 727:
                return [(*current, "plan_db")]
            if 727 <= start < 1296:
                return [(*current, "plan_dc")]
            return list(dc_and_both)
        if page == 89:
            return list(dc_and_both if start < 2064 else all_current_types)
        if page in {90, 91} or page == 92 and start < 1656:
            return list(all_current_types)
        if page == 92:
            return [former]
        if page == 93:
            if start < 712:
                return [former]
            if start < 771:
                return [former]
            if start < 1127:
                return [former]
            if start < 1373:
                return list(former_types)
            if start < 1539:
                return _pension_type_routes(("former_type_both",), loops=True)
            return list(former_b_and_both)
        if page == 94:
            return list(
                former_b_and_both
                if start < 612
                else _pension_type_routes(
                    ("former_type_a", "former_type_both"), loops=True
                )
            )
        if page == 95 or page == 96 and start < 371:
            return _pension_type_routes(
                ("former_type_a", "former_type_both"), loops=True
            )
        if page == 96 and start < 2266:
            return list(former_b)
        if page == 96:
            return list(all_former_types)
        return [()]

    def source_routes(
        page: int, start: int, end: int, kind: str
    ) -> list[tuple[str, ...]]:
        if 86 <= page <= 96:
            return pension_routes(page, start)

        # The income QxQs interleave unconditional explanatory prose with
        # conditional questions.  Only the exact source atoms below inherit
        # the corresponding condition; broader purpose/repeat text stays at
        # root unless its own start is listed.
        income_route_starts: dict[int, dict[str, set[int]]] = {
            42: {
                "section_g_hours": {36, 39, 47, 52},
                "employment_hours_to_income": {192, 199, 207, 212},
            },
            43: {
                "repeat_business_g5": {1302, 1306, 1364},
                "repeat_business_g6": {1786, 1790, 1848},
                "repeat_business_g7": {2364, 2368, 2426},
            },
            44: {
                "head_work_time": {161},
                "wife_work_time": {383, 388},
                "llc_classification": {583, 668, 691},
                "incorporation_unknown": {817, 868, 893},
            },
            45: {
                "draw_in_total": {495, 507, 519, 573, 589},
                "nonowner_wages": {788, 793, 855, 875, 889, 904},
                "owner_separate_share": {1059, 1064, 1170, 1228},
                "head_worked_2012": {1925, 2083, 2162, 2177, 2237, 2252},
            },
            46: {
                "multiple_head_jobs": {218, 300},
                "current_salary_rate": {418},
                "complicated_work_history": {661, 678, 724, 772, 822},
                "earnings_only_supplements": {1567, 1592, 1601, 1611, 1619},
            },
            47: {
                "head_farming_occupation": {786, 797, 806},
                "head_current_job_not_farming": {
                    914,
                    937,
                    970,
                    999,
                    1025,
                    1069,
                },
                "jobs_hours_missing": {1992},
                "other_jobs_g23": {2405, 2433, 2442, 2462},
                "other_jobs_g24": {2586, 2614, 2623, 2643},
            },
            54: {
                "wife_business_income": {740, 748, 785},
                "wife_business_income_g52": {1370, 1378, 1415},
                "wife_hours_missing_g52b": {1880},
            },
            60: {
                "ofum_irregular_g76": {1540, 1555, 1644},
                "ofum_irregular_g77": {1879, 1894, 1983},
            },
            61: {
                "ofum_irregular_g78": {348, 363, 452},
                "ofum_irregular_g79": {733, 748, 837},
                "ofum_irregular_g80": {945, 960, 1049},
                "g81_irregular_hours": {1200},
                "ofum_irregular_g81": {1310, 1325, 1414},
            },
        }
        for symbol, routed_starts in income_route_starts.get(page, {}).items():
            if start in routed_starts:
                return [(symbol,)]
        if page == 22:
            if kind == "remuneration_component_anchor" and start == 2724:
                return [("paid_activity",)]
            if start in {2116, 2149}:
                return [("employer_name_missing",)]
            if start >= 2765 and end <= 2933:
                return [("paid_activity", "paid_but_not_considered")]
        if page == 23:
            if 2519 <= start < 2630:
                return [("road_worker",)]
            if 3245 <= start < 3272:
                return [("college_teacher",)]
        if page == 27 and 738 <= start <= 835:
            return [("fixed_salary_plus_overtime",)]
        if page == 29 and 993 <= start <= 1091:
            return [("same_employer_multiple_times",)]
        if page == 30 and 766 <= start <= 861:
            return [("internet_answer",)]
        if page == 31 and 162 <= start < 627:
            return [("roomers_or_boarders",)]
        return [()]

    def keep_detected_anchor(row: dict[str, Any]) -> bool:
        page = row["page_number"]
        start = row["utf8_byte_start"]
        end = row["utf8_byte_end"]
        kind = row["occurrence_kind_candidate"]
        if kind not in {
            "role_anchor",
            "job_anchor",
            "remuneration_component_anchor",
            "role_total_anchor",
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
        } or not _inside(page, start, end, anchor_windows):
            return False
        if 21 <= page <= 31:
            if kind in {
                "farm_aggregate_anchor",
                "business_aggregate_anchor",
                "role_total_anchor",
            }:
                return False
            if page == 22 and start == 2537:
                return False
            if page == 22 and kind == "remuneration_component_anchor":
                return False
            if page == 24 and kind == "remuneration_component_anchor":
                return False
            if page == 25 and kind == "remuneration_component_anchor":
                return False
            if page == 27 and start == 1685:
                return False
            if page == 28 and start == 326:
                return False
            if page == 30 and kind == "job_anchor":
                return False
        if page == 42:
            if kind == "remuneration_component_anchor" and start == 2049:
                return False
            if kind == "farm_aggregate_anchor" and start == 1422:
                return False
        if page == 43:
            if kind == "role_total_anchor":
                return False
            if kind == "remuneration_component_anchor" and start == 725:
                return False
        if (
            page == 45
            and kind == "remuneration_component_anchor"
            and start == 1660
        ):
            return False
        if page == 46 and kind == "role_total_anchor" and start == 491:
            return False
        if page == 47 and kind == "business_aggregate_anchor":
            return False
        if page == 54 and start >= 2004:
            return False
        if page == 60:
            if kind in {"business_aggregate_anchor", "role_total_anchor"}:
                return False
            if kind == "job_anchor" and start == 1268:
                return False
        if page == 61:
            if kind == "role_total_anchor":
                return False
            if kind == "remuneration_component_anchor" and start == 1475:
                return False
        if 86 <= page <= 96:
            if kind == "business_aggregate_anchor":
                return False
            if kind == "role_anchor" and (page, start) in {
                (86, 2858),
                (91, 176),
            }:
                return False
            if kind == "remuneration_component_anchor":
                return row["matched_text"].casefold() in {
                    "salary",
                    "wage",
                    "compensation",
                }
        if page in {118, 120, 122} and kind == "job_anchor":
            return False
        if page == 123 and kind == "job_anchor":
            return False
        if page == 140 and kind == "job_anchor" and start == 2210:
            return False
        if page == 141:
            if kind == "job_anchor" and start not in {127, 163}:
                return False
            if kind == "remuneration_component_anchor" and start == 702:
                return False
        return True

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
            if keep_detected_anchor(row):
                add(
                    page_number,
                    row["utf8_byte_start"],
                    row["utf8_byte_end"],
                    row["occurrence_kind_candidate"],
                    source_routes(
                        page_number,
                        row["utf8_byte_start"],
                        row["utf8_byte_end"],
                        row["occurrence_kind_candidate"],
                    ),
                    "Reviewer-approved anchor lexeme independently re-derived from source bytes.",
                )

    # The stage-1 role detector misses plural and malformed-quote pension roles.
    pension_role_pattern = re.compile(
        r"Heads|Wives|[“”]Wives[”\"]|[“”]Wife[”\"]"
    )
    for page in range(86, 97):
        text = page_texts[page - 1]
        offsets = annotation.stage1_candidates._utf8_offsets(text)
        for match in pension_role_pattern.finditer(text):
            add(
                page,
                offsets[match.start()],
                offsets[match.end()],
                "role_anchor",
                pension_routes(page, offsets[match.start()]),
                "Plural or malformed-quote role lexeme manually recovered from source bytes.",
            )

    # Manual remuneration and aggregate corrections/additions.
    manual_anchors = [
        (22, 2360, 2371, "remuneration_component_anchor"),
        (22, 2397, 2403, "remuneration_component_anchor"),
        (22, 2603, 2628, "remuneration_component_anchor"),
        (22, 2724, 2732, "remuneration_component_anchor"),
        (22, 2996, 3005, "remuneration_component_anchor"),
        (22, 3187, 3201, "remuneration_component_anchor"),
        (26, 1876, 1882, "remuneration_component_anchor"),
        (26, 1926, 1932, "remuneration_component_anchor"),
        (26, 2186, 2197, "remuneration_component_anchor"),
        (26, 2259, 2271, "remuneration_component_anchor"),
        (26, 2688, 2699, "remuneration_component_anchor"),
        (27, 122, 134, "remuneration_component_anchor"),
        (27, 999, 1010, "remuneration_component_anchor"),
        (27, 1071, 1083, "remuneration_component_anchor"),
        (27, 1666, 1675, "remuneration_component_anchor"),
        (27, 1685, 1702, "remuneration_component_anchor"),
        (27, 1979, 1990, "remuneration_component_anchor"),
        (27, 2051, 2063, "remuneration_component_anchor"),
        (28, 307, 316, "remuneration_component_anchor"),
        (28, 326, 343, "remuneration_component_anchor"),
        (28, 867, 878, "remuneration_component_anchor"),
        (28, 939, 951, "remuneration_component_anchor"),
        (28, 1845, 1856, "remuneration_component_anchor"),
        (28, 1917, 1929, "remuneration_component_anchor"),
        (29, 362, 373, "remuneration_component_anchor"),
        (29, 434, 446, "remuneration_component_anchor"),
        (47, 117, 138, "remuneration_component_anchor"),
        (47, 374, 379, "remuneration_component_anchor"),
        (47, 754, 761, "remuneration_component_anchor"),
        (47, 765, 781, "remuneration_component_anchor"),
        (54, 601, 629, "role_total_anchor"),
        (54, 1231, 1259, "role_total_anchor"),
        (61, 110, 129, "remuneration_component_anchor"),
        (123, 823, 864, "job_anchor"),
        (140, 2300, 2306, "remuneration_component_anchor"),
        (140, 2437, 2445, "remuneration_component_anchor"),
        (140, 2454, 2486, "context_anchor"),
        (140, 2467, 2477, "role_anchor"),
        (141, 627, 656, "context_anchor"),
        (141, 637, 647, "role_anchor"),
        (141, 698, 720, "remuneration_component_anchor"),
    ]
    for page, start, end, kind in manual_anchors:
        add(
            page,
            start,
            end,
            kind,
            source_routes(page, start, end, kind),
            "Anchor span manually corrected or added from exact source bytes.",
        )

    # Exact context atoms.  Candidate-like physical lines are listed explicitly
    # because their semantic acceptance was decided during source review.
    context_spans: dict[int, list[tuple[int, int]]] = {
        21: [
            (1168, 1244),
            (1264, 1346),
            (1625, 1703),
            (1920, 1987),
            (2007, 2086),
            (2139, 2210),
            (2230, 2310),
            (2428, 2509),
            (2574, 2595),
            (2616, 2666),
            (2687, 2714),
            (2735, 2756),
        ],
        22: [
            (193, 271),
            (286, 372),
            (387, 460),
            (990, 1070),
            (1085, 1167),
            (1182, 1256),
            (1837, 1914),
            (2223, 2322),
            (2323, 2418),
            (2419, 2508),
            (2509, 2607),
            (2608, 2669),
            (2670, 2771),
            (2774, 2868),
            (2869, 2933),
            (2934, 3024),
            (3025, 3114),
            (3115, 3205),
            (3206, 3234),
        ],
        23: [
            (103, 149),
            (162, 248),
            (275, 358),
            (371, 458),
            (528, 612),
            (759, 848),
            (1518, 1597),
        ],
        24: [
            (992, 1031),
            (1033, 1125),
            (1137, 1212),
            (1317, 1397),
            (2287, 2337),
            (3001, 3080),
        ],
        25: [
            (254, 319),
            (1696, 1777),
            (1872, 1962),
            (2053, 2178),
            (2396, 2458),
            (2472, 2540),
            (2553, 2584),
            (2598, 2675),
        ],
        26: [
            (6, 93),
            (484, 564),
            (580, 656),
            (672, 706),
            (869, 944),
            (1170, 1253),
            (1506, 1599),
            (1613, 1689),
            (1717, 1800),
        ],
        27: [(600, 737)],
        29: [(1135, 1226), (1553, 1644), (1776, 1860), (1862, 2120)],
        30: [(766, 861)],
        31: [(349, 370), (639, 711)],
        42: [(36, 124), (192, 278), (549, 644)],
        43: [
            (857, 933),
            (936, 1023),
            (1024, 1098),
            (1099, 1109),
            (1396, 1481),
            (1880, 1965),
            (2458, 2543),
        ],
        44: [(113, 205), (335, 428), (893, 967)],
        46: [
            (209, 284),
            (632, 708),
            (724, 806),
            (853, 928),
            (1034, 1109),
            (1803, 1894),
        ],
        47: [
            (103, 192),
            (374, 443),
            (740, 829),
            (937, 1100),
            (1856, 1946),
            (1960, 2035),
            (2126, 2207),
            (2433, 2508),
            (2614, 2689),
        ],
        54: [(481, 553), (1097, 1183), (1830, 1924)],
        60: [
            (93, 164),
            (176, 256),
            (439, 480),
            (490, 565),
            (746, 824),
            (836, 908),
            (918, 990),
            (1002, 1078),
            (1175, 1256),
            (1290, 1311),
            (1321, 1371),
            (1381, 1408),
            (1418, 1439),
            (1540, 1618),
            (1879, 1957),
        ],
        61: [
            (97, 183),
            (348, 426),
            (555, 632),
            (733, 811),
            (945, 1023),
            (1058, 1147),
            (1156, 1209),
            (1310, 1388),
        ],
        86: [
            (189, 239),
            (268, 317),
            (450, 500),
            (663, 712),
            (1232, 1282),
            (1401, 1479),
            (2106, 2135),
            (2302, 2332),
        ],
        88: [(481, 544), (1149, 1223), (1231, 1280), (1768, 1834)],
        89: [(538, 603), (632, 690), (1476, 1558), (1572, 1644), (1757, 1848)],
        90: [(643, 719), (1192, 1268)],
        91: [(1361, 1443), (2045, 2127)],
        92: [
            (327, 409),
            (751, 833),
            (853, 925),
            (1250, 1332),
            (1656, 1705),
            (1718, 2239),
        ],
        93: [
            (595, 663),
            (1539, 1684),
            (1860, 1949),
            (1968, 2039),
            (2163, 2240),
            (2259, 2338),
        ],
        96: [(394, 615), (911, 990)],
        123: [
            (97, 184),
            (199, 280),
            (295, 368),
            (383, 440),
            (442, 504),
            (741, 975),
        ],
        140: [(2157, 2237), (2247, 2323)],
        141: [(328, 417)],
    }
    for page, spans in context_spans.items():
        for start, end in spans:
            add(
                page,
                start,
                end,
                "context_anchor",
                source_routes(page, start, end, "context_anchor"),
                "Source-explicit earnings or work interpretation context.",
            )

    father_purpose = (5, 220)
    mother_purpose = (5, 220)
    add(118, *father_purpose, "context_anchor")
    add(118, *father_purpose, "field_purpose_prompt")
    add(120, *mother_purpose, "context_anchor")
    add(120, *mother_purpose, "field_purpose_prompt")

    # Exact source-explicit field purpose prompts.
    purpose_spans: dict[int, list[tuple[int, int]]] = {
        21: [(822, 920)],
        22: [(527, 620), (1364, 1448)],
        23: [
            (759, 848),
            (2543, 2630),
            (2978, 3074),
            (3245, 3272),
            (3443, 3461),
            (3486, 3514),
            (3539, 3616),
        ],
        24: [
            (18, 84),
            (99, 142),
            (157, 214),
            (229, 257),
            (272, 293),
            (1033, 1125),
            (1409, 1486),
            (1498, 1576),
            (2053, 2117),
            (2129, 2185),
            (2349, 2424),
            (2436, 2511),
            (2527, 2537),
            (2549, 2616),
            (2777, 2840),
            (2852, 2908),
            (2920, 2989),
            (3270, 3343),
            (3359, 3367),
        ],
        25: [
            (110, 146),
            (159, 237),
            (254, 319),
            (444, 514),
            (634, 656),
            (669, 743),
            (760, 772),
            (785, 856),
            (873, 897),
            (910, 954),
            (967, 1039),
            (1056, 1131),
            (1210, 1293),
            (1310, 1390),
            (1407, 1426),
            (1439, 1498),
            (1511, 1593),
            (1606, 1683),
            (1794, 1870),
            (2180, 2274),
        ],
        26: [
            (6, 93),
            (484, 564),
            (580, 656),
            (672, 706),
            (821, 867),
            (1802, 1886),
            (2554, 2641),
        ],
        27: [(512, 599), (1363, 1443), (1640, 1720), (1829, 1845)],
        28: [(4, 92), (198, 281), (479, 486), (1525, 1620)],
        29: [
            (101, 195),
            (824, 916),
            (1135, 1226),
            (1358, 1453),
            (1553, 1644),
            (1776, 1860),
            (1862, 1950),
        ],
        30: [(766, 861)],
        31: [(162, 254)],
        42: [(549, 644), (1660, 1715)],
        43: [(104, 194), (1112, 1195), (1596, 1679), (2174, 2257)],
        44: [(4, 92), (113, 205), (335, 428), (568, 655)],
        45: [(100, 191), (1911, 2003)],
        46: [(6, 97), (1373, 1474), (1550, 1641), (1803, 1894)],
        47: [
            (103, 192),
            (740, 829),
            (1307, 1477),
            (1579, 1668),
            (1856, 1946),
            (2329, 2418),
            (2510, 2599),
        ],
        54: [(170, 257), (1097, 1183), (1830, 2004)],
        60: [(4, 83), (1441, 1651)],
        61: [(97, 247), (555, 632), (846, 1056), (1058, 1209)],
        69: [(119, 225)],
        86: [(1283, 1479), (2520, 2712)],
        87: [
            (103, 198),
            (350, 443),
            (749, 842),
            (1246, 1339),
            (1645, 1738),
            (2044, 2137),
            (2541, 2634),
        ],
        88: [(4, 84)],
        89: [(783, 885), (1757, 1848), (2064, 2315)],
        90: [
            (4, 258),
            (528, 786),
            (1077, 1335),
            (1605, 1865),
            (1867, 2089),
            (2191, 2413),
        ],
        91: [(103, 318), (320, 687), (689, 1056), (1058, 1154), (1742, 1838)],
        92: [(4, 105), (927, 1028), (1718, 2239)],
        93: [
            (107, 202),
            (1395, 1535),
            (1539, 1684),
            (1860, 1949),
            (2659, 2758),
        ],
        94: [(69, 289), (291, 511), (677, 1092), (1094, 1334), (1755, 1991)],
        95: [
            (102, 218),
            (803, 1010),
            (1431, 1633),
            (1799, 2040),
            (2042, 2230),
            (2232, 2504),
        ],
        96: [
            (4, 294),
            (394, 615),
            (795, 891),
            (1161, 1355),
            (1533, 1988),
            (1990, 2089),
            (2266, 2360),
        ],
        122: [(1246, 1346)],
        123: [(97, 184), (442, 504), (741, 975)],
        140: [(1825, 1933), (1935, 2146), (2157, 2337), (2339, 2535)],
        141: [(95, 172)],
    }
    for page, spans in purpose_spans.items():
        for start, end in spans:
            add(
                page,
                start,
                end,
                "field_purpose_prompt",
                source_routes(page, start, end, "field_purpose_prompt"),
                "Source-explicit interviewer objective or field-information purpose.",
            )

    # Cross-references and repeat instructions; no equivalence is inferred.
    father_repeat = _byte_find(
        page_texts[117],
        "Use the same probing techniques you used in Sections\n              BC/DE to get all the details of this work.",
    )
    mother_repeat = _byte_find(
        page_texts[119],
        "Use the same probing techniques you used in\n              Sections BC/DE to get all the details of this work.",
    )
    kl_repeat = _byte_find(
        page_texts[122],
        "Use the same probing techniques you used in Sections BC/DE to get\n              all the details of this work.",
    )
    repeat_spans: dict[int, list[tuple[int, int]]] = {
        26: [(2065, 2139), (2250, 2323), (2554, 2641)],
        27: [(113, 186), (879, 953), (1062, 1135), (1859, 1933), (2042, 2115)],
        28: [(747, 821), (930, 1003), (1725, 1799), (1908, 1981)],
        29: [(242, 316), (425, 498), (1008, 1091), (1862, 1950)],
        31: [(397, 422), (436, 473)],
        43: [(1302, 1381), (1786, 1865), (2364, 2443)],
        45: [(966, 1043)],
        46: [(1034, 1109)],
        47: [(844, 905), (1856, 1946)],
        54: [(847, 979), (1477, 1609)],
        60: [(439, 480)],
        61: [(1489, 1554)],
        86: [(2044, 2063)],
        88: [(160, 285)],
        92: [(1918, 2001)],
        93: [(683, 831), (1127, 1368)],
        94: [(792, 1092), (1452, 1753), (2109, 2410)],
        95: [(336, 637), (1128, 1429)],
        96: [(795, 891), (1045, 1086), (2414, 2516)],
        118: [father_repeat],
        120: [mother_repeat],
        123: [kl_repeat],
        141: [(95, 172)],
    }
    for page, spans in repeat_spans.items():
        for start, end in spans:
            add(
                page,
                start,
                end,
                "repeat_or_alias_instruction",
                source_routes(page, start, end, "repeat_or_alias_instruction"),
                "Explicit repeat or cross-reference preserved without global resolution.",
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

    def branch_compatible(
        source: dict[str, Any], parent: dict[str, Any]
    ) -> bool:
        return any(
            source_path[: min(len(source_path), len(parent_path))]
            == parent_path[: min(len(source_path), len(parent_path))]
            for source_path in source["parent_review_branch_paths"]
            for parent_path in parent["parent_review_branch_paths"]
        )

    current_main_job_id = id_by_key[(22, 1316, 1332, "job_anchor")]
    parent_overrides: dict[
        tuple[int, int, str],
        list[tuple[int, int, int, str]],
    ] = {
        (45, 140, "remuneration_component_anchor"): [
            (45, 589, 597, "business_aggregate_anchor")
        ],
        (45, 573, "remuneration_component_anchor"): [
            (45, 589, 597, "business_aggregate_anchor")
        ],
        (45, 700, "remuneration_component_anchor"): [
            (45, 589, 597, "business_aggregate_anchor")
        ],
        (45, 855, "remuneration_component_anchor"): [
            (45, 889, 903, "business_aggregate_anchor"),
            (45, 904, 912, "business_aggregate_anchor"),
        ],
        (45, 875, "remuneration_component_anchor"): [
            (45, 889, 903, "business_aggregate_anchor"),
            (45, 904, 912, "business_aggregate_anchor"),
        ],
        (45, 1170, "remuneration_component_anchor"): [],
        (45, 1228, "remuneration_component_anchor"): [],
        (45, 2083, "remuneration_component_anchor"): [
            (45, 2162, 2176, "business_aggregate_anchor"),
            (45, 2177, 2185, "business_aggregate_anchor"),
        ],
        **{
            (47, start, "remuneration_component_anchor"): []
            for start in (117, 244, 256, 343, 374, 501, 698)
        },
        (47, 999, "remuneration_component_anchor"): [
            (47, 937, 948, "job_anchor"),
            (47, 970, 977, "farm_aggregate_anchor"),
            (47, 1025, 1032, "farm_aggregate_anchor"),
        ],
        **{
            (54, start, "remuneration_component_anchor"): [
                (54, 601, 629, "role_total_anchor")
            ]
            for start in (231, 670, 676, 691, 1027, 1036)
        },
        **{
            (54, start, "remuneration_component_anchor"): [
                (54, 1231, 1259, "role_total_anchor")
            ]
            for start in (1300, 1306, 1321, 1657, 1666)
        },
        **{
            (69, start, "remuneration_component_anchor"): [
                (69, 234, 314, "role_total_anchor")
            ]
            for start in (252, 309, 326, 334, 341)
        },
        (69, 354, "remuneration_component_anchor"): [
            (69, 234, 314, "role_total_anchor"),
            (69, 366, 374, "business_aggregate_anchor"),
            (69, 382, 397, "business_aggregate_anchor"),
        ],
        (88, 481, "context_anchor"): [(88, 45, 53, "job_anchor")],
        (88, 520, "remuneration_component_anchor"): [
            (88, 45, 53, "job_anchor")
        ],
        (88, 1149, "context_anchor"): [(88, 1156, 1164, "job_anchor")],
        (88, 1231, "context_anchor"): [(88, 1156, 1164, "job_anchor")],
        (88, 1768, "context_anchor"): [(88, 2036, 2044, "job_anchor")],
        (89, 632, "context_anchor"): [(89, 575, 583, "job_anchor")],
        (89, 1572, "context_anchor"): [(89, 1490, 1498, "job_anchor")],
        (91, 1237, "remuneration_component_anchor"): [
            (91, 1698, 1706, "job_anchor")
        ],
        (91, 1361, "context_anchor"): [(91, 1698, 1706, "job_anchor")],
        (91, 1921, "remuneration_component_anchor"): [
            (91, 2382, 2390, "job_anchor")
        ],
        (91, 2045, "context_anchor"): [(91, 2382, 2390, "job_anchor")],
        (92, 193, "remuneration_component_anchor"): [
            (92, 684, 692, "job_anchor")
        ],
        (92, 327, "context_anchor"): [(92, 684, 692, "job_anchor")],
        (92, 853, "context_anchor"): [(92, 765, 773, "job_anchor")],
        (92, 1116, "remuneration_component_anchor"): [
            (92, 1607, 1615, "job_anchor")
        ],
        (92, 1250, "context_anchor"): [(92, 1607, 1615, "job_anchor")],
        **{
            (93, start, "context_anchor"): [(93, 2006, 2014, "job_anchor")]
            for start in (1860, 1968, 2163, 2259)
        },
        (123, 741, "context_anchor"): [(123, 823, 864, "job_anchor")],
        (140, 2157, "context_anchor"): [(140, 2142, 2145, "job_anchor")],
        (140, 2247, "context_anchor"): [(140, 2333, 2336, "job_anchor")],
        (141, 328, "context_anchor"): [(140, 2354, 2357, "job_anchor")],
        (141, 627, "context_anchor"): [
            (140, 2354, 2357, "job_anchor"),
            (141, 648, 656, "business_aggregate_anchor"),
        ],
        (141, 698, "remuneration_component_anchor"): [
            (140, 2354, 2357, "job_anchor"),
            (141, 761, 769, "business_aggregate_anchor"),
        ],
        (140, 2437, "remuneration_component_anchor"): [
            (140, 2354, 2357, "job_anchor"),
            (140, 2478, 2486, "business_aggregate_anchor"),
        ],
        (140, 2454, "context_anchor"): [
            (140, 2354, 2357, "job_anchor"),
            (140, 2478, 2486, "business_aggregate_anchor"),
        ],
    }
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
        try:
            printed_identifier = annotation._source_printed_identifier(
                page_texts[page - 1], spec["utf8_byte_start"]
            )
        except ValueError as error:
            raise ValueError(
                f"anchor does not start in a physical line: page={page} "
                f"span={spec['utf8_byte_start']}:{spec['utf8_byte_end']} "
                f"kind={kind} label={label!r}"
            ) from error
        parent_ids: list[str] = []
        if kind in {"context_anchor", "remuneration_component_anchor"}:
            nested_parents = [
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
            if nested_parents:
                parent_ids = [
                    parent["review_occurrence_id"] for parent in nested_parents
                ]
            elif kind == "remuneration_component_anchor" and 26 <= page <= 29:
                parent_ids = [current_main_job_id]
            elif kind == "remuneration_component_anchor":
                nearby = [
                    parent
                    for parent in parent_anchor_specs
                    if parent["page_number"] == page
                    and branch_compatible(spec, parent)
                    and min(
                        abs(spec["utf8_byte_start"] - parent["utf8_byte_end"]),
                        abs(parent["utf8_byte_start"] - spec["utf8_byte_end"]),
                    )
                    <= 300
                ]
                if nearby:
                    distance = min(
                        min(
                            abs(
                                spec["utf8_byte_start"]
                                - parent["utf8_byte_end"]
                            ),
                            abs(
                                parent["utf8_byte_start"]
                                - spec["utf8_byte_end"]
                            ),
                        )
                        for parent in nearby
                    )
                    parent_ids = [
                        parent["review_occurrence_id"]
                        for parent in nearby
                        if min(
                            abs(
                                spec["utf8_byte_start"]
                                - parent["utf8_byte_end"]
                            ),
                            abs(
                                parent["utf8_byte_start"]
                                - spec["utf8_byte_end"]
                            ),
                        )
                        == distance
                    ]
            override_key = (page, spec["utf8_byte_start"], kind)
            if override_key in parent_overrides:
                parent_ids = [
                    id_by_key[parent_key]
                    for parent_key in parent_overrides[override_key]
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
                "Explicit source-local parent anchors were verified from the "
                "same question, heading, source block, or direct work-pay context."
            )
        else:
            parent_note = (
                "Whole-page review found general or no-job context and asserted "
                "no local parent anchor."
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

    repeat_alias_specs: list[dict[str, Any]] = []
    p140_job = id_by_key[(140, 2354, 2357, "job_anchor")]
    p141_which = id_by_key[(141, 127, 136, "job_anchor")]
    p141_that = id_by_key[(141, 163, 171, "job_anchor")]
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != "repeat_or_alias_instruction":
            continue
        page = spec["page_number"]
        raw = page_texts[page - 1].encode("utf-8")[
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ]
        text = raw.decode("utf-8", errors="strict").casefold()
        review_id = spec["review_occurrence_id"]
        if page == 141 and spec["utf8_byte_start"] == 95:
            aliases = [p141_which, p141_that]
            canonicals = [p140_job]
            evidence = [p140_job, review_id, p141_which, p141_that]
            target_scope = "document_local"
            resolution_status = "document_local_source_evidence_complete"
            relation = "explicit_cross_reference"
        else:
            aliases = []
            canonicals = []
            evidence = [review_id]
            target_scope = "unresolved"
            resolution_status = "preserved_for_global_resolution"
            relation = (
                "explicit_repeat_instruction"
                if any(
                    token in text
                    for token in (
                        "repeat",
                        "again",
                        "another",
                        "same employer",
                        "loop",
                    )
                )
                else "explicit_cross_reference"
            )
        repeat_alias_specs.append(
            {
                "review_occurrence_id": review_id,
                "relation": relation,
                "alias_anchor_review_occurrence_ids": aliases,
                "canonical_anchor_review_occurrence_ids": canonicals,
                "evidence_review_occurrence_ids": evidence,
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
            "whole_page_review": "all_142_pages_including_empty_occurrence_pages",
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
