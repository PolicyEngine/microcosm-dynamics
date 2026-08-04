#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 20.

``q77.pdf`` is the 34-page 1977 family questionnaire. Every complete page of
authenticated Poppler text was reviewed before these selectors were written.
This module never opens the stage-1 candidate
artifact; candidate rows are joined only by the sealed annotation builder
after this source-byte ledger validates.

The retained domain is the questionnaire's role, employment assignment,
occupation, industry, employee/self-employment, incorporation, job identity,
work exposure, actual remuneration, role-total, farm, business, and lifetime
work-history fields.  Worklike prose in transportation, housing, child care,
attitudes, health, commuting, training, job-search effort, job-finding
chance, residential mobility, and counterfactual labour-supply questions is
outside the ratified section-19 purpose vocabulary.  A retained screen keeps
its legible printed routing atoms; OCR-destroyed or unextractable labels are
not reconstructed.  No repeated wording is promoted to alias evidence:
``same job`` is a response field, ``Anything else?`` is a prompt, and the
F14 interviewer check does not assert an anchor identity.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_candidates as stage1  # noqa: E402
import build_rq_stage2_document_020_annotation as annotation  # noqa: E402

F = "flow_branch_label"
R = "role_anchor"
J = "job_anchor"
M = "remuneration_component_anchor"
T = "role_total_anchor"
FA = "farm_aggregate_anchor"
BA = "business_aggregate_anchor"
C = "context_anchor"
P = "field_purpose_prompt"

REVIEW_PATH = annotation.REVIEW_PATH
PAGE_COUNT = 34


class SpecError(ValueError):
    """Raised when a reviewer selector no longer resolves in source bytes."""


def _line_rows(page_text: str) -> list[dict[str, Any]]:
    return stage1._physical_lines(page_text)


def _utf8(page_text: str, char_start: int, char_end: int) -> tuple[int, int]:
    return (
        len(page_text[:char_start].encode("utf-8")),
        len(page_text[:char_end].encode("utf-8")),
    )


def resolve_line(page_text: str, line_number: int) -> tuple[int, int]:
    for row in _line_rows(page_text):
        if row["line_number"] == line_number:
            return _utf8(page_text, row["start"], row["end"])
    raise SpecError(f"line {line_number} is blank or absent")


def resolve_block(
    page_text: str, first_line: int, last_line: int
) -> tuple[int, int]:
    start = resolve_line(page_text, first_line)[0]
    end = resolve_line(page_text, last_line)[1]
    if start >= end:
        raise SpecError(f"block {first_line}-{last_line} is inverted")
    return start, end


def resolve_needle(
    page_text: str, line_number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    line_start, line_end = resolve_line(page_text, line_number)
    raw = page_text.encode("utf-8")
    target = needle.encode("utf-8")
    found: list[int] = []
    cursor = line_start
    while True:
        position = raw.find(target, cursor, line_end)
        if position < 0:
            break
        found.append(position)
        cursor = position + 1
    if occurrence >= len(found):
        raise SpecError(
            f"needle {needle!r} occurrence {occurrence} missing on line "
            f"{line_number}"
        )
    return found[occurrence], found[occurrence] + len(target)


def resolve_tail(
    page_text: str, line_number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    start, _ = resolve_needle(page_text, line_number, needle, occurrence)
    return start, resolve_line(page_text, line_number)[1]


def resolve(page_text: str, selector: Sequence[Any]) -> tuple[int, int]:
    mode = selector[0]
    if mode == "line":
        return resolve_line(page_text, selector[1])
    if mode == "block":
        return resolve_block(page_text, selector[1], selector[2])
    if mode == "needle":
        return resolve_needle(page_text, selector[1], selector[2], selector[3])
    if mode == "tail":
        return resolve_tail(page_text, selector[1], selector[2], selector[3])
    raise SpecError(f"unknown selector mode {mode!r}")


def sel_line(number: int) -> tuple[Any, ...]:
    return ("line", number)


def sel_block(first: int, last: int) -> tuple[Any, ...]:
    return ("block", first, last)


def sel_word(number: int, needle: str, occurrence: int = 0) -> tuple[Any, ...]:
    return ("needle", number, needle, occurrence)


def sel_tail(number: int, needle: str, occurrence: int = 0) -> tuple[Any, ...]:
    return ("tail", number, needle, occurrence)


def spec(
    page: int,
    selector: tuple[Any, ...],
    kind: str,
    key: str,
    *,
    parents: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
    note: str = "",
) -> dict[str, Any]:
    return {
        "page": page,
        "selector": selector,
        "kind": kind,
        "key": key,
        "parents": tuple(parents),
        "routes": tuple(tuple(route) for route in routes),
        "note": note,
    }


def question(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    anchor_kind: str | None = C,
    parents: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
    note: str = "",
) -> tuple[dict[str, Any], ...]:
    prompt = spec(
        page,
        selector,
        P,
        f"{key}_prompt",
        routes=routes,
        note="Exact printed field-purpose prompt retained.",
    )
    if anchor_kind is None:
        return (prompt,)
    anchor = spec(
        page,
        selector,
        anchor_kind,
        key,
        parents=parents,
        routes=routes,
        note=note or "Exact printed document-local anchor retained.",
    )
    return anchor, prompt


_DEFAULT_NOTES = {
    F: "Exact printed flow or routing atom retained on a retained screen.",
    R: "Exact printed questionnaire-role anchor retained.",
    J: "Exact printed job-establishing noun retained.",
    M: "Exact printed actual-remuneration component retained.",
    T: "Exact printed role-total anchor retained.",
    FA: "Exact printed farm-aggregate anchor retained.",
    BA: "Exact printed business-aggregate anchor retained.",
    C: "Exact printed contextual field for a ratified purpose retained.",
    P: "Exact printed field-purpose prompt retained.",
}


PAGE_NOTES: dict[int, str] = {
    1: "Cover and child-schooling section reviewed; no R_Q occurrence retained.",
    2: "Transportation section reviewed; work-travel prose is outside the R_Q employment hierarchy.",
    3: "Housing ownership section reviewed; housing farm wording is not employment evidence.",
    4: "Housing rent and utilities section reviewed; no R_Q occurrence retained.",
    5: "Residential mobility section reviewed; hypothetical moving prose is outside R_Q.",
    6: "Head section D assignment, occupation, industry, and routing reviewed.",
    7: "Head D5-D25 employee/self, government, supervision, union, and tenure screen reviewed.",
    8: "Head D26-D39 job tenure, history, absence, vacation, and routing reviewed.",
    9: "Head D40-D49 strike, unemployment, work exposure, and overtime screen reviewed.",
    10: "Head D50-D63 pay basis, remuneration, extra-job, and work exposure screen reviewed.",
    11: "Head D64-D71 counterfactual labor supply and commuting screen reviewed and excluded.",
    12: "Head section E sought-job/pay screen reviewed; training/search/mobility prose excluded.",
    13: "Head E13-E26 last-job and actual work-absence screen reviewed.",
    14: "Head E27-E37 actual work exposure retained; commuting prose excluded.",
    15: "Head section F actual past-work screen reviewed; future-job plans excluded.",
    16: "Head F14-F25 sought-job/pay and job-search screen reviewed; only ratified job/pay atoms retained.",
    17: "Section G spouse work screen reviewed; spouse assignment, occupation, and industry retained.",
    18: "Spouse G8-G20 work absence, vacation, strike, unemployment, and routing reviewed.",
    19: "Spouse G21-G30 main-job exposure retained; child-care and household-work prose excluded.",
    20: "Housework and household-member screen reviewed; no R_Q occurrence retained.",
    21: "Food expenditure and food-stamp section reviewed; incidental work wording excluded.",
    22: "Food-stamp continuation reviewed; no R_Q occurrence retained.",
    23: "Section H farm, business, wages, and head aggregate earnings reviewed.",
    24: "Head remuneration and nonlabor-income screen reviewed; only work earnings retained.",
    25: "Spouse income source and amount screen reviewed; transfers and health coverage excluded.",
    26: "Other-family-member income/work grid reviewed; outside the two-role R_Q domain.",
    27: "Continuation grid for other family members reviewed; outside the two-role R_Q domain.",
    28: "Other-member cross-reference, welfare, and windfall screen reviewed; no two-role R_Q atom retained.",
    29: "Support, union, health-limitation, and care screen reviewed; no R_Q atom retained.",
    30: "New-wife background and lifetime work-history screen reviewed.",
    31: "New-head background and first-job screen reviewed.",
    32: "New-head mobility/background screen reviewed; historical job-mobility hypotheticals excluded.",
    33: "New-head lifetime work-history screen reviewed; education/training prose excluded.",
    34: "By-observation section reviewed; no R_Q occurrence retained.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_D = ("p6_sec_d",)
D1_WORKING = SEC_D + ("p6_d1_working",)
D1_ONLY = SEC_D + ("p6_d1_only",)
D1_LOOKING = SEC_D + ("p6_d1_looking",)
D1_RETIRED = SEC_D + ("p6_d1_retired",)
D1_PERMANENTLY = SEC_D + ("p6_d1_permanently",)
D1_HOUSEWIFE = SEC_D + ("p6_d1_housewife",)
D1_STUDENT = SEC_D + ("p6_d1_student",)
D1_OTHER = SEC_D + ("p6_d1_other",)
D1_OTHER_HAS_JOB = D1_OTHER + ("p6_d1_if_has",)
D1_OTHERWISE = D1_OTHER + ("p6_d1_otherwise",)
D_ACTIVE = (D1_WORKING, D1_ONLY, D1_OTHER_HAS_JOB)
D_BOTH = extend_routes(D_ACTIVE, "p7_d5_both")
D_SHORT = extend_routes(D_ACTIVE, "p8_short_tenure")
D32_YES = extend_routes(D_ACTIVE, "p8_d32_yes")
D35_YES = extend_routes(D_ACTIVE, "p8_d35_yes")
D38_YES = extend_routes(D_ACTIVE, "p8_d38_yes")
D40_YES = extend_routes(D_ACTIVE, "p9_d40_yes")
D42_YES = extend_routes(D_ACTIVE, "p9_d42_yes")
D44_MORE = extend_routes(D42_YES, "p9_d44_more")
D48_YES = extend_routes(D_ACTIVE, "p9_d48_yes")
D50_SALARIED = extend_routes(D_ACTIVE, "p10_d50_salaried")
D50_HOURLY = extend_routes(D_ACTIVE, "p10_d50_hourly")
D50_OTHER = extend_routes(D_ACTIVE, "p10_d50_other")
D52_YES = extend_routes(D50_SALARIED, "p10_d52_yes")
D58_YES = extend_routes(D_ACTIVE, "p10_d58_yes")
SEC_E = D1_LOOKING + ("p12_sec_e",)
E14_YES = SEC_E + ("p13_e14_yes",)
E_RECENT = E14_YES + ("p13_recent_work",)
E20_YES = E_RECENT + ("p13_e20_yes",)
E22_YES = E_RECENT + ("p13_e22_yes",)
E25_YES = E_RECENT + ("p13_e25_yes",)
E27_YES = E_RECENT + ("p14_e27_yes",)
E29_YES = E_RECENT + ("p14_e29_yes",)
E31_MORE = E29_YES + ("p14_e31_more",)
F_ENTRY = (
    D1_RETIRED,
    D1_PERMANENTLY,
    D1_HOUSEWIFE,
    D1_STUDENT,
    D1_OTHERWISE,
)
SEC_F = extend_routes(F_ENTRY, "p15_sec_f")
F_WORKED = extend_routes(SEC_F, "p15_worked_yes")
F10_NO = extend_routes(F_WORKED, "p15_f10_no")
F_THINKING = extend_routes(SEC_F, "p16_thinking_yes")
SEC_G = ("p17_sec_g",)
G_ELIGIBLE = SEC_G + ("p17_spouse_in_fu",)
G_WORKED = G_ELIGIBLE + ("p17_g5_yes",)
G8_YES = G_WORKED + ("p18_g8_yes",)
G11_YES = G_WORKED + ("p18_g11_yes",)
G13_YES = G_WORKED + ("p18_g13_yes",)
G15_YES = G_WORKED + ("p18_g15_yes",)
G17_YES = G_WORKED + ("p18_g17_yes",)
G19_MORE = G17_YES + ("p18_g19_more",)
G23_CHILDREN = G_ELIGIBLE + ("p19_g23_children",)
SEC_H = ("p23_sec_h",)
H_FARMER = SEC_H + ("p23_farmer",)
H_BUSINESS = SEC_H + ("p23_h5_yes",)
H_BUSINESS_UNINCORPORATED = H_BUSINESS + ("p23_h6_unincorporated",)
H_BUSINESS_BOTH = H_BUSINESS + ("p23_h6_both",)
H9_YES = SEC_H + ("p24_h9_yes",)
H_WIFE = SEC_H + ("p25_h18_yes_wife",)
H19_YES = H_WIFE + ("p25_h19_yes",)
SEC_J = ("p30_sec_j",)
J_NEW = SEC_J + ("p30_new_wife",)
SEC_K = ("p31_sec_k",)
K_NEW = SEC_K + ("p31_new_head",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Pages 1-5 were reviewed in full. Their child-schooling,
    # transportation, housing, utilities, and residential-mobility prose
    # supports no atom in the section-19 employment hierarchy.

    # Head employment: assignment, source job contexts, work exposure, and
    # actual remuneration. The printed section heading is the local branch
    # that separates these atoms from the mutually exclusive E/F schedules.
    add(spec(6, sel_tail(11, "SECTION D:"), F, "p6_sec_d"))
    add(spec(6, sel_word(14, "HEAD"), R, "p6_role_head", routes=(SEC_D,)))
    add(*question(6, sel_block(14, 15), "p6_d1_assignment", routes=(SEC_D,)))
    for line_number, needle, key in (
        (17, "1. WORKING", "p6_d1_working"),
        (17, "2. ONLY", "p6_d1_only"),
        (17, "3. LOOKING FOR", "p6_d1_looking"),
        (17, "4.       RETIRED", "p6_d1_retired"),
        (18, "5. PERMANENTLY", "p6_d1_permanently"),
        (24, "6.       HOUSEWIFE", "p6_d1_housewife"),
        (25, "7.   STUDENT", "p6_d1_student"),
        (26, "8.   OTHER", "p6_d1_other"),
    ):
        add(spec(6, sel_word(line_number, needle), F, key, routes=(SEC_D,)))
    add(spec(6, sel_word(26, "IF HAS"), F, "p6_d1_if_has", routes=(D1_OTHER,)))
    add(
        spec(
            6,
            sel_word(27, "OTHERWISE"),
            F,
            "p6_d1_otherwise",
            routes=(D1_OTHER,),
        )
    )
    add(*question(6, sel_block(33, 34), "p6_d2_occupation", routes=D_ACTIVE))
    add(
        *question(
            6,
            sel_line(41),
            "p6_d3_detail",
            anchor_kind=None,
            routes=D_ACTIVE,
        )
    )
    add(*question(6, sel_line(46), "p6_d4_industry", routes=D_ACTIVE))

    add(*question(7, sel_line(5), "p7_d5_employee_self", routes=D_ACTIVE))
    add(
        spec(
            7,
            sel_word(8, "2. BOTH          SOMEONE ELSE AND SELF"),
            F,
            "p7_d5_both",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_word(10, "D6.    Do you work for the federal,"),
            "p7_d6_government",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_word(10, "D14.     When you work for others,"),
            "p7_d14_government",
            routes=D_BOTH,
        )
    )
    add(
        *question(
            7,
            sel_block(64, 65),
            "p7_d21_tenure",
            routes=D_BOTH,
        )
    )
    add(*question(7, sel_block(67, 68), "p7_d13_tenure", routes=D_ACTIVE))

    add(*question(8, sel_block(6, 7), "p8_d26_tenure", routes=D_ACTIVE))
    add(
        spec(
            8,
            sel_word(6, "present            position"),
            J,
            "p8_present_position",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            8,
            sel_word(8, "IF LESS THAN           ONE YEAR"),
            F,
            "p8_short_tenure",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            8,
            sel_line(11),
            "p8_d27_start",
            parents=("p8_present_position",),
            routes=D_SHORT,
        )
    )
    for first, last, key in (
        (12, 13, "p8_d28_previous"),
        (18, 20, "p8_d29_compare"),
        (23, 23, "p8_d30_reason"),
        (28, 28, "p8_d31_pay_compare"),
    ):
        add(
            *question(
                8,
                sel_block(first, last),
                key,
                anchor_kind=None,
                routes=D_SHORT,
            )
        )
    for first, last, key, anchor in (
        (36, 36, "p8_d32_family_sick", C),
        (41, 42, "p8_d33_relation", None),
        (48, 49, "p8_d34_family_sick_time", C),
        (52, 52, "p8_d35_own_sick", C),
        (57, 58, "p8_d36_own_sick_time", C),
        (60, 60, "p8_d37_paid_vacation", C),
        (62, 62, "p8_d38_vacation", C),
        (67, 68, "p8_d39_vacation_time", C),
    ):
        add(
            *question(
                8,
                sel_block(first, last),
                key,
                anchor_kind=anchor,
                routes=(
                    D32_YES
                    if key in {"p8_d33_relation", "p8_d34_family_sick_time"}
                    else (
                        D35_YES
                        if key == "p8_d36_own_sick_time"
                        else (
                            D38_YES
                            if key == "p8_d39_vacation_time"
                            else D_ACTIVE
                        )
                    )
                ),
            )
        )
    add(spec(8, sel_word(38, "1. YES"), F, "p8_d32_yes", routes=D_ACTIVE))
    add(spec(8, sel_word(54, "1. YES"), F, "p8_d35_yes", routes=D_ACTIVE))
    add(spec(8, sel_word(64, "1. YES"), F, "p8_d38_yes", routes=D_ACTIVE))

    for first, last, key, anchor in (
        (11, 11, "p9_d40_strike", C),
        (16, 17, "p9_d41_strike_time", C),
        (19, 19, "p9_d42_unemployed", C),
        (26, 27, "p9_d43_unemployed_time", C),
        (29, 33, "p9_d44_periods", C),
        (38, 39, "p9_d45_period_count", C),
    ):
        add(
            *question(
                9,
                sel_block(first, last),
                key,
                anchor_kind=anchor,
                routes=(
                    D40_YES
                    if key == "p9_d41_strike_time"
                    else (
                        D42_YES
                        if key in {"p9_d43_unemployed_time", "p9_d44_periods"}
                        else (
                            D44_MORE
                            if key == "p9_d45_period_count"
                            else D_ACTIVE
                        )
                    )
                ),
            )
        )
    add(spec(9, sel_word(13, "1. YES"), F, "p9_d40_yes", routes=D_ACTIVE))
    add(spec(9, sel_word(21, "1. YES"), F, "p9_d42_yes", routes=D_ACTIVE))
    add(
        spec(
            9,
            sel_word(33, "5. MORE THAN TWO"),
            F,
            "p9_d44_more",
            routes=D42_YES,
        )
    )
    add(
        spec(
            9, sel_word(43, "main     job"), J, "p9_main_job", routes=D_ACTIVE
        )
    )
    add(
        *question(
            9,
            sel_line(43),
            "p9_d46_weeks",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            9,
            sel_block(46, 47),
            "p9_d47_hours",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            9,
            sel_line(52),
            "p9_d48_overtime",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            9,
            sel_line(57),
            "p9_d49_overtime_hours",
            parents=("p9_main_job",),
            routes=D48_YES,
        )
    )
    add(spec(9, sel_word(54, "1. YES"), F, "p9_d48_yes", routes=D_ACTIVE))

    add(
        *question(
            10,
            sel_line(9),
            "p10_d50_pay_type",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            10,
            sel_word(11, "1. SALARIED"),
            F,
            "p10_d50_salaried",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            10,
            sel_word(11, "3. PAID         BY HOUR"),
            F,
            "p10_d50_hourly",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(10, sel_word(11, "7. OTHER"), F, "p10_d50_other", routes=D_ACTIVE)
    )
    for line_number, needle, key, kind in (
        (
            14,
            "D51.    How much is              your        salary?",
            "p10_d51_salary",
            M,
        ),
        (18, "D52.    If you were to work more", "p10_d52_extra_pay", None),
        (27, "D53. About how much", "p10_d53_overtime_amount", None),
        (14, "D54.      What is your hourly", "p10_d54_hourly", M),
        (21, "D55.      What is your hourly", "p10_d55_overtime_rate", M),
        (14, "D56.      How is     that?", "p10_d56_unit", None),
        (24, "D57.      If you worked    an", "p10_d57_extra_hour", None),
    ):
        add(
            *question(
                10,
                sel_word(line_number, needle),
                key,
                anchor_kind=kind,
                parents=("p9_main_job",),
                routes=(
                    D50_SALARIED
                    if key in {"p10_d51_salary", "p10_d52_extra_pay"}
                    else (
                        D52_YES
                        if key == "p10_d53_overtime_amount"
                        else (
                            D50_HOURLY
                            if key
                            in {"p10_d54_hourly", "p10_d55_overtime_rate"}
                            else D50_OTHER
                        )
                    )
                ),
            )
        )
    add(
        spec(10, sel_word(24, "1. YES"), F, "p10_d52_yes", routes=D50_SALARIED)
    )
    add(
        *question(
            10,
            sel_block(39, 40),
            "p10_d58_extra_jobs",
            anchor_kind=None,
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            10,
            sel_word(39, "extra                          jobs"),
            J,
            "p10_extra_jobs",
            routes=D_ACTIVE,
        )
    )
    add(spec(10, sel_word(42, "1. YES"), F, "p10_d58_yes", routes=D_ACTIVE))
    add(
        *question(
            10,
            sel_block(46, 47),
            "p10_d59_occupation",
            parents=("p10_extra_jobs",),
            routes=D58_YES,
        )
    )
    add(
        *question(
            10,
            sel_line(51),
            "p10_d60_other",
            anchor_kind=None,
            routes=D58_YES,
        )
    )
    add(
        *question(
            10,
            sel_block(55, 56),
            "p10_d61_hourly",
            anchor_kind=M,
            parents=("p10_extra_jobs",),
            routes=D58_YES,
        )
    )
    add(
        *question(
            10,
            sel_line(58),
            "p10_d62_weeks",
            parents=("p10_extra_jobs",),
            routes=D58_YES,
        )
    )
    add(
        *question(
            10,
            sel_line(61),
            "p10_d63_hours",
            parents=("p10_extra_jobs",),
            routes=D58_YES,
        )
    )

    # Page 11 asks only counterfactual labor-supply and commuting questions.
    add(
        spec(
            12, sel_tail(9, "SECTION E:"), F, "p12_sec_e", routes=(D1_LOOKING,)
        )
    )
    add(spec(12, sel_word(12, "job"), J, "p12_sought_job", routes=(SEC_E,)))
    add(
        *question(
            12,
            sel_line(12),
            "p12_e1_sought_occupation",
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(16),
            "p12_e2_expected_pay",
            anchor_kind=M,
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )

    add(
        *question(
            13,
            sel_line(10),
            "p13_e14_ever_job",
            anchor_kind=None,
            routes=(SEC_E,),
        )
    )
    add(spec(13, sel_word(12, "1. YES"), F, "p13_e14_yes", routes=(SEC_E,)))
    add(
        spec(
            13,
            sel_word(16, "last        job"),
            J,
            "p13_last_job",
            routes=(E14_YES,),
        )
    )
    add(
        *question(
            13,
            sel_line(16),
            "p13_e15_last_occupation",
            parents=("p13_last_job",),
            routes=(E14_YES,),
        )
    )
    add(
        *question(
            13,
            sel_line(20),
            "p13_e16_industry",
            parents=("p13_last_job",),
            routes=(E14_YES,),
        )
    )
    add(
        *question(
            13,
            sel_block(28, 29),
            "p13_e18_separation",
            anchor_kind=None,
            routes=(E14_YES,),
        )
    )
    add(*question(13, sel_line(34), "p13_e19_last_work", routes=(E14_YES,)))
    add(
        spec(
            13,
            sel_word(36, "IF 1976 OR          1977"),
            F,
            "p13_recent_work",
            routes=(E14_YES,),
        )
    )
    for first, last, key, anchor in (
        (40, 40, "p13_e20_vacation", C),
        (44, 45, "p13_e21_vacation_time", C),
        (46, 46, "p13_e22_family_sick", C),
        (52, 54, "p13_e23_relation", None),
        (56, 57, "p13_e24_family_sick_time", C),
        (60, 60, "p13_e25_own_sick", C),
        (64, 65, "p13_e26_own_sick_time", C),
    ):
        add(
            *question(
                13,
                sel_block(first, last),
                key,
                anchor_kind=anchor,
                routes=(
                    (
                        E20_YES
                        if key == "p13_e21_vacation_time"
                        else (
                            E22_YES
                            if key
                            in {"p13_e23_relation", "p13_e24_family_sick_time"}
                            else (
                                E25_YES
                                if key == "p13_e26_own_sick_time"
                                else E_RECENT
                            )
                        )
                    ),
                ),
            )
        )
    add(spec(13, sel_word(42, "1. YES"), F, "p13_e20_yes", routes=(E_RECENT,)))
    add(spec(13, sel_word(48, "1. YES"), F, "p13_e22_yes", routes=(E_RECENT,)))
    add(spec(13, sel_word(62, "1. YES"), F, "p13_e25_yes", routes=(E_RECENT,)))

    for first, last, key, anchor in (
        (15, 15, "p14_e27_strike", C),
        (19, 20, "p14_e28_strike_time", C),
        (22, 22, "p14_e29_unemployed", C),
        (28, 29, "p14_e30_unemployed_time", C),
        (31, 32, "p14_e31_periods", C),
        (37, 38, "p14_e32_period_count", C),
        (43, 45, "p14_e33_weeks", C),
        (47, 50, "p14_e34_hours", C),
    ):
        parents = (
            ("p13_last_job",)
            if key in {"p14_e33_weeks", "p14_e34_hours"}
            else ()
        )
        add(
            *question(
                14,
                sel_block(first, last),
                key,
                anchor_kind=anchor,
                parents=parents,
                routes=(
                    (
                        E27_YES
                        if key == "p14_e28_strike_time"
                        else (
                            E29_YES
                            if key
                            in {"p14_e30_unemployed_time", "p14_e31_periods"}
                            else (
                                E31_MORE
                                if key == "p14_e32_period_count"
                                else E_RECENT
                            )
                        )
                    ),
                ),
            )
        )
    add(
        spec(
            14,
            sel_word(17, "1.     YES"),
            F,
            "p14_e27_yes",
            routes=(E_RECENT,),
        )
    )
    add(spec(14, sel_word(24, "1. YES"), F, "p14_e29_yes", routes=(E_RECENT,)))
    add(
        spec(
            14,
            sel_word(34, "5. MORE THAN TWO"),
            F,
            "p14_e31_more",
            routes=(E29_YES,),
        )
    )

    add(spec(15, sel_tail(7, "SECTION F:"), F, "p15_sec_f", routes=F_ENTRY))
    add(
        *question(
            15,
            sel_block(23, 24),
            "p15_f3_work_for_money",
            anchor_kind=None,
            routes=SEC_F,
        )
    )
    add(spec(15, sel_word(25, "1. YES"), F, "p15_worked_yes", routes=SEC_F))
    for first, last, key in (
        (39, 40, "p15_f6_occupation"),
        (43, 44, "p15_f7_industry"),
        (45, 48, "p15_f8_weeks"),
        (49, 50, "p15_f9_hours"),
        (52, 54, "p15_f10_still_working"),
    ):
        add(
            *question(
                15,
                sel_block(first, last),
                key,
                routes=F_WORKED,
            )
        )
    add(spec(15, sel_word(54, "5. NO"), F, "p15_f10_no", routes=F_WORKED))
    add(
        *question(
            15,
            sel_block(56, 58),
            "p15_f11_separation",
            anchor_kind=None,
            routes=F10_NO,
        )
    )

    add(
        spec(
            16,
            sel_word(11, '1. "YES" TO THINKING'),
            F,
            "p16_thinking_yes",
            routes=SEC_F,
        )
    )
    add(spec(16, sel_word(17, "job"), J, "p16_sought_job", routes=F_THINKING))
    add(
        *question(
            16,
            sel_line(17),
            "p16_f15_sought_job",
            parents=("p16_sought_job",),
            routes=F_THINKING,
        )
    )
    add(
        *question(
            16,
            sel_line(21),
            "p16_f16_expected_pay",
            anchor_kind=M,
            parents=("p16_sought_job",),
            routes=F_THINKING,
        )
    )

    # Spouse work schedule. Child care and household work on pages 19-20 do
    # not become employment hierarchy atoms.
    add(spec(17, sel_tail(10, "SECTION G:"), F, "p17_sec_g"))
    add(
        spec(
            17,
            sel_word(10, "WIFE'S"),
            R,
            "p17_role_wife_header",
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            17,
            sel_line(16),
            "p17_g1_marital",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            17,
            sel_line(36),
            "p17_g4_checkpoint",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(spec(17, sel_block(39, 42), F, "p17_spouse_in_fu", routes=(SEC_G,)))
    add(
        *question(
            17,
            sel_line(46),
            "p17_g5_work",
            anchor_kind=None,
            routes=(G_ELIGIBLE,),
        )
    )
    add(
        spec(
            17,
            sel_word(46, "wife/friend"),
            R,
            "p17_role_wife_g5",
            routes=(G_ELIGIBLE,),
        )
    )
    add(
        spec(17, sel_word(48, "1. YES"), F, "p17_g5_yes", routes=(G_ELIGIBLE,))
    )
    add(*question(17, sel_line(53), "p17_g6_occupation", routes=(G_WORKED,)))
    add(*question(17, sel_line(57), "p17_g7_industry", routes=(G_WORKED,)))

    for first, last, key, anchor in (
        (10, 11, "p18_g8_family_sick", C),
        (15, 17, "p18_g9_relation", None),
        (19, 20, "p18_g10_family_sick_time", C),
        (23, 23, "p18_g11_own_sick", C),
        (28, 29, "p18_g12_own_sick_time", C),
        (31, 31, "p18_g13_vacation", C),
        (36, 37, "p18_g14_vacation_time", C),
        (40, 40, "p18_g15_strike", C),
        (44, 45, "p18_g16_strike_time", C),
        (48, 49, "p18_g17_unemployed", C),
        (56, 57, "p18_g18_unemployed_time", C),
        (59, 60, "p18_g19_periods", C),
        (65, 68, "p18_g20_period_count", C),
    ):
        add(
            *question(
                18,
                sel_block(first, last),
                key,
                anchor_kind=anchor,
                routes=(
                    (
                        G8_YES
                        if key
                        in {"p18_g9_relation", "p18_g10_family_sick_time"}
                        else (
                            G11_YES
                            if key == "p18_g12_own_sick_time"
                            else (
                                G13_YES
                                if key == "p18_g14_vacation_time"
                                else (
                                    G15_YES
                                    if key == "p18_g16_strike_time"
                                    else (
                                        G17_YES
                                        if key
                                        in {
                                            "p18_g18_unemployed_time",
                                            "p18_g19_periods",
                                        }
                                        else (
                                            G19_MORE
                                            if key == "p18_g20_period_count"
                                            else G_WORKED
                                        )
                                    )
                                )
                            )
                        )
                    ),
                ),
            )
        )
    for line_number, needle, key, route in (
        (12, "1. YES", "p18_g8_yes", G_WORKED),
        (25, "1. YES", "p18_g11_yes", G_WORKED),
        (33, "1. YES", "p18_g13_yes", G_WORKED),
        (42, "1.   YES", "p18_g15_yes", G_WORKED),
        (51, "1. YES", "p18_g17_yes", G_WORKED),
        (60, "more than two?", "p18_g19_more", G17_YES),
    ):
        add(spec(18, sel_word(line_number, needle), F, key, routes=(route,)))
    for line_number, key in (
        (10, "p18_role_spouse_g8"),
        (23, "p18_role_spouse_g11"),
        (31, "p18_role_spouse_g13"),
        (40, "p18_role_spouse_g15"),
        (48, "p18_role_spouse_g17"),
    ):
        add(
            spec(
                18,
                sel_word(line_number, "(wife/friend)"),
                R,
                key,
                routes=(G_WORKED,),
            )
        )

    add(
        spec(
            19,
            sel_word(11, "main     job"),
            J,
            "p19_main_job_g21",
            routes=(G_WORKED,),
        )
    )
    add(
        *question(
            19,
            sel_block(11, 12),
            "p19_g21_weeks",
            parents=("p19_main_job_g21",),
            routes=(G_WORKED,),
        )
    )
    add(
        spec(
            19,
            sel_word(13, "main    job"),
            J,
            "p19_main_job_g22",
            routes=(G_WORKED,),
        )
    )
    add(
        *question(
            19,
            sel_block(13, 16),
            "p19_g22_hours",
            parents=("p19_main_job_g22",),
            routes=(G_WORKED,),
        )
    )
    add(
        spec(
            19,
            sel_word(20, "1.    CHILD/CHILDREN"),
            F,
            "p19_g23_children",
            routes=(G_ELIGIBLE,),
        )
    )
    add(
        *question(
            19,
            sel_line(27),
            "p19_g24_working_now",
            anchor_kind=None,
            routes=(G23_CHILDREN,),
        )
    )
    add(
        spec(
            19,
            sel_word(27, "(wife/friend)"),
            R,
            "p19_role_spouse_g24",
            routes=(G23_CHILDREN,),
        )
    )

    # Pages 20-22 concern housework, food spending, and food stamps only.
    add(spec(23, sel_line(7), F, "p23_sec_h"))
    add(
        spec(
            23,
            sel_word(20, "1.    FARMER, OR RANCHER"),
            F,
            "p23_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            23,
            sel_block(23, 24),
            "p23_h2_receipts",
            anchor_kind=M,
            parents=("p23_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_block(26, 27),
            "p23_h3_expenses",
            anchor_kind=M,
            parents=("p23_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_line(29),
            "p23_h4_net_farm",
            anchor_kind=None,
            routes=(H_FARMER,),
        )
    )
    add(
        spec(
            23,
            sel_word(29, "net     income          from          farming"),
            FA,
            "p23_farm_aggregate",
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_block(33, 34),
            "p23_h5_business",
            anchor_kind=C,
            routes=(SEC_H,),
        )
    )
    add(spec(23, sel_word(36, "1. YES"), F, "p23_h5_yes", routes=(SEC_H,)))
    add(
        spec(
            23,
            sel_word(40, "unincorporated                          business"),
            BA,
            "p23_business_aggregate",
            routes=(H_BUSINESS,),
        )
    )
    add(
        *question(
            23,
            sel_block(39, 41),
            "p23_h6_incorporation",
            parents=("p23_business_aggregate",),
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            23,
            sel_word(45, "2. UNINCORPORATED"),
            F,
            "p23_h6_unincorporated",
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            23, sel_word(46, "3. BOTH"), F, "p23_h6_both", routes=(H_BUSINESS,)
        )
    )
    add(
        *question(
            23,
            sel_block(49, 51),
            "p23_h7_business_share",
            anchor_kind=M,
            parents=("p23_business_aggregate",),
            routes=(H_BUSINESS_UNINCORPORATED, H_BUSINESS_BOTH),
        )
    )
    add(
        spec(
            23, sel_word(60, "(HEAD)"), R, "p23_role_head_h8", routes=(SEC_H,)
        )
    )
    add(
        *question(
            23,
            sel_block(60, 61),
            "p23_h8_wages",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            24,
            sel_block(11, 12),
            "p24_h9_bonus",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(spec(24, sel_word(14, "YES"), F, "p24_h9_yes", routes=(SEC_H,)))
    add(
        *question(
            24,
            sel_line(16),
            "p24_h10_bonus_amount",
            anchor_kind=None,
            routes=(H9_YES,),
        )
    )
    add(
        *question(
            24,
            sel_line(18),
            "p24_h11_other_income",
            anchor_kind=C,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            24, sel_word(18, "(HEAD)"), R, "p24_role_head_h11", routes=(SEC_H,)
        )
    )
    add(
        *question(
            24,
            sel_word(
                21,
                "a)      professional                  practice             or    trade?",
            ),
            "p24_h11a_professional",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            24,
            sel_word(
                23, "b)      farming              or market     gardening,"
            ),
            "p24_h11b_farming",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            24,
            sel_word(25, "roomers              or boarders?"),
            "p24_h11b_roomers",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            24,
            sel_block(21, 28),
            P,
            "p24_h11_shared_amount_prompt",
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            25,
            sel_line(33),
            "p25_h18_checkpoint",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(25, sel_word(33, "HEAD"), R, "p25_role_head_h18", routes=(SEC_H,))
    )
    add(
        spec(25, sel_word(33, "WIFE"), R, "p25_role_wife_h18", routes=(SEC_H,))
    )
    add(
        spec(
            25,
            sel_word(35, "YES, WIFE/FRIEND                IN FU"),
            F,
            "p25_h18_yes_wife",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            25,
            sel_word(37, "(wife/friend)"),
            R,
            "p25_role_wife_h19",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            25,
            sel_line(37),
            "p25_h19_role_total",
            anchor_kind=T,
            routes=(H_WIFE,),
        )
    )
    add(spec(25, sel_word(38, "YES"), F, "p25_h19_yes", routes=(H_WIFE,)))
    add(
        *question(
            25,
            sel_line(40),
            "p25_h20_source",
            anchor_kind=C,
            parents=("p25_h19_role_total",),
            routes=(H19_YES,),
        )
    )
    add(
        *question(
            25,
            sel_line(43),
            "p25_h21_amount",
            anchor_kind=M,
            parents=("p25_h19_role_total",),
            routes=(H19_YES,),
        )
    )

    # Pages 26-29 concern persons outside the two-role universe, welfare,
    # support, union membership, health limitation, and care needs.
    add(spec(30, sel_line(10), F, "p30_sec_j"))
    add(
        spec(
            30,
            sel_word(10, "WIFE"),
            R,
            "p30_role_wife_header",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            30,
            sel_word(15, "1. FU HAS NEW (WIFE/PERMANENT"),
            F,
            "p30_new_wife",
            routes=(SEC_J,),
        )
    )
    add(*question(30, sel_line(49), "p30_j10_years", routes=(J_NEW,)))
    add(*question(30, sel_line(53), "p30_j11_full_time", routes=(J_NEW,)))
    add(*question(30, sel_block(57, 58), "p30_j12_part_time", routes=(J_NEW,)))

    add(spec(31, sel_line(7), F, "p31_sec_k"))
    add(
        spec(
            31, sel_word(7, "HEAD"), R, "p31_role_head_header", routes=(SEC_K,)
        )
    )
    add(
        spec(
            31,
            sel_word(12, "1. FU HAS A NEW HEAD THIS YEAR"),
            F,
            "p31_new_head",
            routes=(SEC_K,),
        )
    )
    add(
        spec(
            31,
            sel_word(34, "(HEAD'S)"),
            R,
            "p31_role_head_k4",
            routes=(K_NEW,),
        )
    )
    add(
        spec(
            31,
            sel_word(
                34, "first       full      time         regular        job"
            ),
            J,
            "p31_first_job",
            routes=(K_NEW,),
        )
    )
    add(
        *question(
            31,
            sel_line(34),
            "p31_k4_first_job",
            parents=("p31_first_job",),
            routes=(K_NEW,),
        )
    )
    add(*question(31, sel_block(39, 40), "p31_k5_job_kinds", routes=(K_NEW,)))

    add(spec(33, sel_word(7, "(HEAD)"), R, "p33_role_head", routes=(K_NEW,)))
    add(*question(33, sel_line(7), "p33_k25_years", routes=(K_NEW,)))
    add(*question(33, sel_line(11), "p33_k26_full_time", routes=(K_NEW,)))
    add(*question(33, sel_block(16, 17), "p33_k27_part_time", routes=(K_NEW,)))

    return tuple(rows)


REVIEW_ROWS = _review_rows()


def _validate_scope() -> None:
    if set(PAGE_NOTES) != set(range(1, PAGE_COUNT + 1)):
        raise SpecError("page review notes do not cover every page")
    keys = [row["key"] for row in REVIEW_ROWS]
    if len(keys) != len(set(keys)):
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        raise SpecError(f"duplicate reviewer keys: {duplicates}")


def author_review() -> dict[str, Any]:
    _validate_scope()
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]

    resolved: dict[str, dict[str, Any]] = {}
    for row in REVIEW_ROWS:
        page_text = page_texts[row["page"] - 1]
        start, end = resolve(page_text, row["selector"])
        matched = page_text.encode("utf-8")[start:end]
        matched.decode("utf-8", errors="strict")
        if not matched:
            raise SpecError(f"empty reviewer span for {row['key']}")
        resolved[row["key"]] = {
            **row,
            "utf8_byte_start": start,
            "utf8_byte_end": end,
        }

    ordered = sorted(
        resolved.values(),
        key=lambda row: (
            row["page"],
            row["utf8_byte_start"],
            row["utf8_byte_end"],
            annotation.KIND_ORDER[row["kind"]],
            row["key"],
        ),
    )

    review_id_by_key: dict[str, str] = {}
    occurrence_specs: list[dict[str, Any]] = []
    for row in ordered:
        review_id = "rq-review-occurrence:" + annotation._canonical_digest(
            [
                source_document_id,
                row["page"],
                row["utf8_byte_start"],
                row["utf8_byte_end"],
                row["kind"],
                annotation._sha256(
                    page_texts[row["page"] - 1].encode("utf-8")[
                        row["utf8_byte_start"] : row["utf8_byte_end"]
                    ]
                ),
            ]
        )
        review_id_by_key[row["key"]] = review_id
        occurrence_specs.append({**row, "review_occurrence_id": review_id})

    branch_refs_by_key: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    final_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        paths: list[list[str]] = []
        for route in row["routes"]:
            path: list[str] = []
            for parent_key in route:
                if parent_key not in branch_refs_by_key:
                    raise SpecError(
                        f"{row['key']} routes through unresolved {parent_key}"
                    )
                matching_refs = [
                    branch_ref
                    for branch_ref, parent_path in branch_refs_by_key[
                        parent_key
                    ]
                    if parent_path == tuple(path)
                ]
                if len(matching_refs) != 1:
                    raise SpecError(
                        f"{row['key']} cannot resolve {parent_key} after "
                        f"{tuple(path)}"
                    )
                path.append(matching_refs[0])
            paths.append(path)
        final_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "page_number": row["page"],
                "utf8_byte_start": row["utf8_byte_start"],
                "utf8_byte_end": row["utf8_byte_end"],
                "occurrence_kind": row["kind"],
                "parent_review_branch_paths": paths,
                "review_note": row["note"] or _DEFAULT_NOTES[row["kind"]],
            }
        )
        if row["kind"] == F:
            branch_refs_by_key[row["key"]] = [
                (
                    annotation._review_branch_ref(
                        row["review_occurrence_id"], path, len(paths)
                    ),
                    tuple(path),
                )
                for path in paths
            ]

    anchor_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        if row["kind"] not in annotation.ANCHOR_KINDS:
            continue
        page_text = page_texts[row["page"] - 1]
        matched = page_text.encode("utf-8")[
            row["utf8_byte_start"] : row["utf8_byte_end"]
        ].decode("utf-8")
        if row["kind"] == R:
            node_domain = "role"
            classification = stage1._role_classification(matched)
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                row["kind"]
            ]
        parents = [review_id_by_key[key] for key in row["parents"]]
        anchor_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": annotation._source_printed_identifier(
                    page_text, row["utf8_byte_start"], matched
                ),
                "parent_review_occurrence_ids": parents,
                "parent_resolution_note": (
                    "Printed parent job or aggregate is named on this screen."
                    if parents
                    else "No printed parent job or aggregate is assigned locally."
                ),
                "classification_status": "provisional_document_local",
            }
        )

    review = {
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
            "whole_page_review": "all_34_pages_including_empty_occurrence_pages",
            "span_granularity": (
                "exact_utf8_lexeme_physical_line_or_source_block"
            ),
            "candidate_nonselection": (
                "candidates_joined_only_after_source_rows_complete"
            ),
            "global_ids_assigned": False,
        },
        "page_review_rows": [
            {
                "page_number": page_number,
                "page_text_utf8_sha256": annotation._sha256(
                    page_texts[page_number - 1].encode("utf-8")
                ),
                "whole_page_review_complete": True,
                "review_status": "complete",
                "review_note": PAGE_NOTES[page_number],
            }
            for page_number in range(1, PAGE_COUNT + 1)
        ],
        "occurrence_specs": final_specs,
        "local_anchor_specs": anchor_specs,
        "repeat_alias_specs": [],
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
    parser.add_argument("--census", action="store_true")
    args = parser.parse_args()
    review = author_review()
    raw = annotation._canonical_bytes(review)
    if args.check:
        if not REVIEW_PATH.exists() or REVIEW_PATH.read_bytes() != raw:
            raise SystemExit(f"stale or missing {REVIEW_PATH.name}")
    else:
        REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        REVIEW_PATH.write_bytes(raw)
    counts: Counter[str] = Counter(
        row["occurrence_kind"] for row in review["occurrence_specs"]
    )
    print(
        f"document 20 source review: {len(review['occurrence_specs'])} "
        f"occurrence specs, {len(review['local_anchor_specs'])} anchors, "
        f"{len(review['repeat_alias_specs'])} repeat rows"
    )
    if args.census:
        for kind in annotation.OCCURRENCE_KINDS:
            print(f"  {kind}: {counts.get(kind, 0)}")
        pages = Counter(
            row["page_number"] for row in review["occurrence_specs"]
        )
        print(
            "  pages with occurrences:",
            len(pages),
            "| empty-occurrence pages:",
            PAGE_COUNT - len(pages),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
