#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 10.

``q72.pdf`` is the 42-page 1972 family questionnaire. Every page was
reviewed from authenticated Poppler text and a full-page rendering before
these selectors were written. This module never opens the stage-1 candidate
artifact; candidate rows are joined only by the sealed annotation builder
after this source-byte ledger validates.

The retained domain is the questionnaire's role, employment assignment,
occupation, industry, employee/self-employment, job identity, work exposure,
actual remuneration, role-total, farm, business, and lifetime work-history
fields. Worklike prose in transportation, housing, home repair, housework,
food, attitudes, health, commuting, training, job-search effort,
job-availability, residential mobility, and counterfactual labour-supply
questions is outside the ratified section-19 purpose vocabulary. Other-family
member income is outside the two-role R_Q domain. A retained screen keeps only
legible printed routing atoms; OCR-destroyed labels are not reconstructed.
The G2-G9 wife-occupation cross-reference is preserved for later global
resolution, but this document-local shard assigns no global component IDs.
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
import build_rq_stage2_document_010_annotation as annotation  # noqa: E402

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

REVIEW_PATH = annotation.REVIEW_PATH
PAGE_COUNT = 42


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


def cross_reference(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    routes: Sequence[Sequence[str]],
    alias_keys: Sequence[str] = (),
    canonical_keys: Sequence[str] = (),
    evidence_keys: Sequence[str] = (),
    target_scope: str = "document_local",
    resolution_status: str = "preserved_for_global_resolution",
) -> dict[str, Any]:
    row = spec(
        page,
        selector,
        A,
        key,
        routes=routes,
        note="Exact printed cross-reference retained for global resolution.",
    )
    row["repeat"] = {
        "relation": "explicit_cross_reference",
        "alias_keys": tuple(alias_keys),
        "canonical_keys": tuple(canonical_keys),
        "evidence_keys": tuple(evidence_keys) or (key,),
        "target_scope": target_scope,
        "resolution_status": resolution_status,
    }
    return row


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
    A: "Exact printed repeat or cross-reference instruction retained.",
}


PAGE_NOTES: dict[int, str] = {
    1: "Children and family-change screen reviewed; no retained R_Q field.",
    2: "Transportation and vehicle screen reviewed; no retained R_Q field.",
    3: "Vehicle repeat panel reviewed; transportation is outside R_Q.",
    4: "Housing screen reviewed; no retained R_Q field.",
    5: "Housing and work-for-housing prose reviewed and excluded.",
    6: "Housing and self-performed home-repair prose reviewed and excluded.",
    7: "Head assignment, occupation, industry, tenure, and prior-job screen retained.",
    8: "Head exposure/pay retained; raster-only or garbled answer labels were not minted.",
    9: "Head extra-job actual fields retained; hypothetical supply excluded.",
    10: "Commuting screen reviewed; no ratified R_Q field retained.",
    11: "Lateness, future-job, mobility, and satisfaction screen excluded.",
    12: "Sought-job, expected-pay, last-job, and actual exposure fields retained.",
    13: "Commuting screen reviewed; no ratified R_Q field retained.",
    14: "Lateness, job availability, and hypothetical mobility screen excluded.",
    15: "Head actual-work and sought-job/pay fields retained; search prose excluded.",
    16: "Wife actual-work, occupation, industry, and exposure fields retained.",
    17: "Counterfactual wife work, children, and education screen excluded.",
    18: "Housework, child-care, and food-preparation screen reviewed and excluded.",
    19: "Food, cigarettes, and food-stamp screen reviewed and excluded.",
    20: "Meals and food-production screen reviewed and excluded.",
    21: (
        "Farm/business/head pay retained; garbled positive H1 bytes were "
        "raster-verified, and unextractable H6 options remain an exact "
        "non-corporation fallthrough."
    ),
    22: "Head bonus and covered self-employment income fields retained; transfers excluded.",
    23: "Wife role-total and actual-income amount fields retained; welfare excluded.",
    24: "Other-family-member income and repeat panel excluded from two-role R_Q.",
    25: "Other-family-member continuation reviewed and excluded.",
    26: "Other-member, windfall, and all-source family-income screen excluded.",
    27: "Support and savings screen reviewed; no retained R_Q field.",
    28: "Insurance and health-related work limitation screen reviewed and excluded.",
    29: "Family health, school, and extra-care screen reviewed and excluded.",
    30: "Word-test screen reviewed; no retained R_Q field.",
    31: "Word-test continuation reviewed; no retained R_Q field.",
    32: "Feelings screen reviewed; no retained R_Q field.",
    33: "Attitude and hypothetical job-choice screen reviewed and excluded.",
    34: "Attitude and hypothetical job-choice screen reviewed and excluded.",
    35: "Social-description and test-anxiety screen reviewed and excluded.",
    36: "Test-anxiety and spare-time screen reviewed and excluded.",
    37: "Time use, union, and retrospective impressions screen excluded.",
    38: "New-head first-job and lifetime occupation-history fields retained.",
    39: "Sibling, education, finance, and religion screen reviewed and excluded.",
    40: "Background, mobility, training, education, and veteran screen excluded.",
    41: "Interviewer-observation screen reviewed; no retained R_Q field.",
    42: "Dwelling-observation screen reviewed; no retained R_Q field.",
}


SEC_D = ("p7_sec_d",)
D_HAS_JOB = SEC_D + ("p7_d_has_job",)
D_SHORT = D_HAS_JOB + ("p7_less_than_year",)
D_LONG = D_HAS_JOB + ("p7_one_year_or_more",)
D_POST_TENURE = (D_LONG, D_SHORT)
D_OVERTIME_YES = (
    D_LONG + ("p8_d18_yes",),
    D_SHORT + ("p8_d18_yes",),
)
D_OVERTIME_NO = (
    D_LONG + ("p8_d18_no",),
    D_SHORT + ("p8_d18_no",),
)
D_AFTER_OVERTIME = D_OVERTIME_YES + D_OVERTIME_NO
D_EXTRA = tuple(path + ("p9_d24_yes",) for path in D_AFTER_OVERTIME)
SEC_E = ("p12_sec_e",)
SEC_F = ("p15_sec_f",)
F_WORK = SEC_F + ("p15_f1_yes",)
F_SOUGHT = SEC_F + ("p15_f2_f6_yes",)
SEC_G = ("p16_sec_g",)
G_WORK = SEC_G + ("p16_g2_yes",)
SEC_H = ("p21_sec_h",)
H_FARMER = SEC_H + ("p21_farmer",)
H_NOT_FARMER = SEC_H + ("p21_not_farmer",)
H_AFTER_FARM = (H_FARMER, H_NOT_FARMER)
H_BUSINESS = tuple(path + ("p21_h5_yes",) for path in H_AFTER_FARM)
H_NO_BUSINESS = tuple(path + ("p21_h5_no",) for path in H_AFTER_FARM)
H6_CORPORATION = tuple(path + ("p21_h6_corporation",) for path in H_BUSINESS)
H6_DONT_KNOW = tuple(path + ("p21_h6_dont_know",) for path in H_BUSINESS)
H7_FALLTHROUGH = H_BUSINESS + H6_DONT_KNOW
H_AFTER_BUSINESS = H_NO_BUSINESS + H6_CORPORATION + H7_FALLTHROUGH
H9_YES = tuple(path + ("p22_h9_yes",) for path in H_AFTER_BUSINESS)
H9_NO = tuple(path + ("p22_h9_no",) for path in H_AFTER_BUSINESS)
H_AFTER_BONUS = H9_YES + H9_NO
H_WIFE = tuple(path + ("p23_h22_yes_wife",) for path in H_AFTER_BONUS)
H_WIFE_INCOME = tuple(path + ("p23_h23_yes",) for path in H_WIFE)
H11_ANY_YES = tuple(path + ("p22_h11_any_yes",) for path in H_AFTER_BONUS)
SEC_M = ("p38_sec_m",)
M_NEW_HEAD = SEC_M + ("p38_new_head",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Section D: head current and extra employment.
    add(spec(7, sel_tail(4, "SECTION D:"), F, "p7_sec_d"))
    add(
        *question(
            7,
            sel_block(7, 8),
            "p7_d1_assignment",
            parents=("p7_present_job",),
            routes=(SEC_D,),
        )
    )
    add(
        spec(
            7,
            sel_word(7, "HEAD's"),
            R,
            "p7_role_head_possessive",
            routes=(SEC_D,),
        )
    )
    add(
        spec(
            7, sel_word(7, "present job"), J, "p7_present_job", routes=(SEC_D,)
        )
    )
    add(spec(7, sel_word(7, "HEAD", 1), R, "p7_role_head", routes=(SEC_D,)))
    add(spec(7, sel_block(13, 16), F, "p7_d_has_job", routes=(SEC_D,)))
    add(
        *question(
            7,
            sel_line(17),
            "p7_d2_occupation",
            parents=("p7_present_job",),
            routes=(D_HAS_JOB,),
        )
    )
    add(
        spec(
            7,
            sel_word(22, "(IF NOT CLEAR)"),
            F,
            "p7_not_clear",
            routes=(D_HAS_JOB,),
        )
    )
    add(
        *question(
            7,
            sel_tail(22, "D3."),
            "p7_d3_detail",
            anchor_kind=None,
            routes=(D_HAS_JOB + ("p7_not_clear",),),
        )
    )
    add(
        *question(
            7,
            sel_line(27),
            "p7_d3a_industry",
            parents=("p7_present_job",),
            routes=(D_HAS_JOB,),
        )
    )
    add(
        *question(
            7,
            sel_line(30),
            "p7_d4_employee_self",
            parents=("p7_present_job",),
            routes=(D_HAS_JOB,),
        )
    )
    add(
        *question(
            7,
            sel_line(33),
            "p7_d5_tenure",
            parents=("p7_present_job",),
            routes=(D_HAS_JOB,),
        )
    )
    add(spec(7, sel_line(34), F, "p7_one_year_or_more", routes=(D_HAS_JOB,)))
    add(spec(7, sel_line(36), F, "p7_less_than_year", routes=(D_HAS_JOB,)))
    add(
        *question(
            7,
            sel_block(38, 39),
            "p7_d6_previous_job_exit",
            anchor_kind=None,
            routes=(D_SHORT,),
        )
    )
    add(
        spec(
            7,
            sel_word(38, "job you had before"),
            J,
            "p7_previous_job",
            routes=(D_SHORT,),
        )
    )
    add(
        *question(
            7,
            sel_line(43),
            "p7_d7_pay_compare",
            anchor_kind=None,
            routes=(D_SHORT,),
        )
    )
    add(
        *question(
            7,
            sel_block(46, 47),
            "p7_d8_job_compare",
            anchor_kind=None,
            routes=(D_SHORT,),
        )
    )
    add(
        *question(
            7,
            sel_line(50),
            "p7_d9_reason",
            anchor_kind=None,
            routes=(D_SHORT,),
        )
    )

    for first, last, key in (
        (4, 4, "d10_vacation"),
        (6, 6, "d11_vacation_time"),
        (10, 11, "d12_sick"),
        (13, 13, "d13_sick_time"),
        (18, 18, "d14_unemployed_strike"),
        (19, 20, "d15_unemployed_strike_time"),
    ):
        add(
            *question(
                8,
                sel_block(first, last),
                f"p8_{key}",
                parents=("p7_present_job",),
                routes=D_POST_TENURE,
            )
        )
    add(
        *question(
            8,
            sel_block(23, 24),
            "p8_d16_weeks",
            parents=("p8_main_job",),
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8, sel_word(23, "main job"), J, "p8_main_job", routes=D_POST_TENURE
        )
    )
    add(
        *question(
            8,
            sel_block(25, 26),
            "p8_d17_hours",
            parents=("p8_main_job",),
            routes=D_POST_TENURE,
        )
    )
    add(
        *question(
            8,
            sel_line(29),
            "p8_d18_overtime",
            parents=("p8_main_job",),
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(29, "overtime"),
            M,
            "p8_d18_overtime_component",
            parents=("p8_main_job",),
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(31, "[ 1 YES"),
            F,
            "p8_d18_yes",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(31, "[ ] NO (GO TO D20)"),
            F,
            "p8_d18_no",
            routes=D_POST_TENURE,
        )
    )
    add(
        *question(
            8,
            sel_line(34),
            "p8_d19_overtime_hours",
            parents=("p8_main_job",),
            routes=D_OVERTIME_YES,
        )
    )
    add(
        *question(
            8,
            sel_block(37, 38),
            "p8_d20_extra_pay",
            parents=("p8_main_job",),
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            8,
            sel_word(43, "D21. What would be your hourly              rate"),
            "p8_d21_overtime_rate",
            anchor_kind=None,
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            8,
            sel_word(44, "for that overtime?"),
            "p8_d21_overtime_rate_continuation",
            anchor_kind=None,
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            8,
            sel_word(43, "D22. Do you have an hourly wage rate"),
            "p8_d22_hourly_status",
            parents=("p8_main_job",),
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            8,
            sel_word(44, "for your regular work?"),
            "p8_d22_hourly_status_continuation",
            anchor_kind=None,
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            8,
            sel_line(50),
            "p8_d23_hourly_rate",
            anchor_kind=M,
            parents=("p8_main_job",),
            routes=D_AFTER_OVERTIME,
        )
    )

    add(
        *question(
            9,
            sel_block(4, 5),
            "p9_d24_extra_jobs",
            parents=("p9_extra_jobs",),
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        spec(
            9,
            sel_word(4, "extra jobs"),
            J,
            "p9_extra_jobs",
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        spec(
            9, sel_word(6, "1. YES"), F, "p9_d24_yes", routes=D_AFTER_OVERTIME
        )
    )
    add(
        spec(
            9,
            sel_word(6, "15.1       (GO TO D30)"),
            F,
            "p9_d24_no",
            routes=D_AFTER_OVERTIME,
        )
    )
    add(
        *question(
            9,
            sel_line(10),
            "p9_d25_occupation",
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )
    add(
        *question(
            9, sel_line(15), "p9_d26_other", anchor_kind=None, routes=D_EXTRA
        )
    )
    add(
        *question(
            9,
            sel_line(16),
            "p9_d27_hourly",
            anchor_kind=M,
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )
    add(
        *question(
            9,
            sel_line(17),
            "p9_d28_weeks",
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )
    add(
        *question(
            9,
            sel_line(19),
            "p9_d29_hours",
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )

    # Section E: looking for work and last actual job.
    add(spec(12, sel_block(3, 4), F, "p12_sec_e"))
    add(
        *question(
            12,
            sel_line(7),
            "p12_e1_sought_occupation",
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )
    add(spec(12, sel_word(7, "job"), J, "p12_sought_job", routes=(SEC_E,)))
    add(
        *question(
            12,
            sel_line(11),
            "p12_e2_expected_pay",
            anchor_kind=M,
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(26),
            "p12_e6_last_occupation",
            parents=("p12_last_job",),
            routes=(SEC_E,),
        )
    )
    add(spec(12, sel_word(26, "last job"), J, "p12_last_job", routes=(SEC_E,)))
    add(
        *question(
            12,
            sel_line(31),
            "p12_e6a_industry",
            parents=("p12_last_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_block(35, 36),
            "p12_e6b_separation",
            anchor_kind=None,
            routes=(SEC_E,),
        )
    )
    for line_number, key in (
        (41, "e7_weeks"),
        (44, "e8_hours"),
        (46, "e9_sick"),
        (49, "e10_unemployed"),
    ):
        add(
            *question(
                12,
                sel_line(line_number),
                f"p12_{key}",
                parents=("p12_last_job",),
                routes=(SEC_E,),
            )
        )

    # Section F: head actual work and contemplated job identity/pay.
    add(spec(15, sel_block(3, 4), F, "p15_sec_f"))
    add(
        *question(
            15,
            sel_line(6),
            "p15_f1_work_for_money",
            parents=("p15_actual_job",),
            routes=(SEC_F,),
        )
    )
    add(spec(15, sel_word(6, "HEAD"), R, "p15_role_head", routes=(SEC_F,)))
    add(spec(15, sel_word(7, "1. YES"), F, "p15_f1_yes", routes=(SEC_F,)))
    add(spec(15, sel_word(7, "5. NO"), F, "p15_f1_no", routes=(SEC_F,)))
    add(
        *question(
            15,
            sel_line(13),
            "p15_f3_occupation",
            parents=("p15_actual_job",),
            routes=(F_WORK,),
        )
    )
    add(
        spec(
            15,
            sel_word(13, "occupation"),
            J,
            "p15_actual_job",
            routes=(F_WORK,),
        )
    )
    add(
        *question(
            15,
            sel_line(16),
            "p15_f3a_industry",
            parents=("p15_actual_job",),
            routes=(F_WORK,),
        )
    )
    add(
        *question(
            15,
            sel_line(19),
            "p15_f4_weeks",
            parents=("p15_actual_job",),
            routes=(F_WORK,),
        )
    )
    add(
        *question(
            15,
            sel_line(21),
            "p15_f5_hours",
            parents=("p15_actual_job",),
            routes=(F_WORK,),
        )
    )
    add(spec(15, sel_line(27), F, "p15_f2_f6_yes", routes=(SEC_F,)))
    add(
        *question(
            15,
            sel_line(29),
            "p15_f7_sought_occupation",
            parents=("p15_sought_job",),
            routes=(F_SOUGHT,),
        )
    )
    add(spec(15, sel_word(29, "job"), J, "p15_sought_job", routes=(F_SOUGHT,)))
    add(
        *question(
            15,
            sel_line(33),
            "p15_f8_expected_pay",
            anchor_kind=M,
            parents=("p15_sought_job",),
            routes=(F_SOUGHT,),
        )
    )

    # Section G: wife actual employment. Counterfactual and commute fields stop at G5.
    add(spec(16, sel_block(18, 19), F, "p16_sec_g"))
    add(
        *question(
            16,
            sel_line(21),
            "p16_g1_marital",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(spec(16, sel_line(23), F, "p16_nonmarried_exit", routes=(SEC_G,)))
    add(
        cross_reference(
            16,
            sel_line(24),
            "p16_g2_g9_crossref",
            routes=(SEC_G,),
            alias_keys=("p16_role_wife_g2",),
            canonical_keys=("p16_role_wife_header",),
            evidence_keys=(
                "p16_g2_g9_crossref",
                "p16_role_wife_header",
                "p16_role_wife_g2",
            ),
            resolution_status="document_local_source_evidence_complete",
        )
    )
    add(
        spec(
            16,
            sel_word(24, "WIFE's"),
            R,
            "p16_role_wife_header",
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            16,
            sel_line(26),
            "p16_g2_work_for_money",
            parents=("p16_wife_actual_job",),
            routes=(SEC_G,),
        )
    )
    add(spec(16, sel_word(26, "wife"), R, "p16_role_wife_g2", routes=(SEC_G,)))
    add(
        spec(
            16,
            sel_word(26, "work for money"),
            J,
            "p16_wife_actual_job",
            routes=(SEC_G,),
        )
    )
    add(spec(16, sel_word(27, "1. YES"), F, "p16_g2_yes", routes=(SEC_G,)))
    add(
        spec(
            16,
            sel_word(27, "5. NO j (GO TO GlO, PAGE 17)"),
            F,
            "p16_g2_no",
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            16,
            sel_line(30),
            "p16_g3_occupation",
            parents=("p16_wife_actual_job",),
            routes=(G_WORK,),
        )
    )
    add(
        *question(
            16,
            sel_line(34),
            "p16_g3a_industry",
            parents=("p16_wife_actual_job",),
            routes=(G_WORK,),
        )
    )
    add(
        *question(
            16,
            sel_line(37),
            "p16_g4_weeks",
            parents=("p16_wife_actual_job",),
            routes=(G_WORK,),
        )
    )
    add(
        *question(
            16,
            sel_line(38),
            "p16_g5_hours",
            parents=("p16_wife_actual_job",),
            routes=(G_WORK,),
        )
    )

    # Section H: farm, business, head remuneration, and wife total.
    add(spec(21, sel_line(3), F, "p21_sec_h"))
    add(
        spec(
            21,
            sel_line(12),
            F,
            "p21_farmer",
            routes=(SEC_H,),
            note=(
                "Exact pinned Poppler span for the raster-verified positive "
                "FARMER OR RANCHER branch; no replacement text was minted."
            ),
        )
    )
    add(spec(21, sel_line(13), F, "p21_not_farmer", routes=(SEC_H,)))
    add(
        *question(
            21,
            sel_block(17, 18),
            "p21_h2_receipts",
            anchor_kind=M,
            parents=("p21_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            21,
            sel_block(19, 20),
            "p21_h3_expenses",
            anchor_kind=M,
            parents=("p21_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            21,
            sel_line(21),
            "p21_h4_net_farm",
            anchor_kind=None,
            routes=(H_FARMER,),
        )
    )
    add(
        spec(
            21,
            sel_word(21, "net income from farming"),
            FA,
            "p21_farm_aggregate",
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            21,
            sel_block(23, 24),
            "p21_h5_business",
            parents=("p21_business_aggregate",),
            routes=H_AFTER_FARM,
        )
    )
    add(
        spec(
            21,
            sel_word(23, "a business"),
            BA,
            "p21_business_aggregate",
            routes=H_AFTER_FARM,
        )
    )
    add(
        spec(
            21,
            sel_word(27, "1. YES"),
            F,
            "p21_h5_yes",
            routes=H_AFTER_FARM,
        )
    )
    add(
        spec(
            21,
            sel_word(27, "mNO        (GO TO H8)"),
            F,
            "p21_h5_no",
            routes=H_AFTER_FARM,
        )
    )
    add(
        *question(
            21,
            sel_block(29, 30),
            "p21_h6_incorporation",
            parents=("p21_business_aggregate",),
            routes=H_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(29, "unincorporated              business"),
            BA,
            "p21_unincorporated_business",
            routes=H_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_block(31, 32),
            F,
            "p21_h6_corporation",
            routes=H_BUSINESS,
            note=(
                "Exact Poppler lines and the raster identify the CORPORATION "
                "response as the branch that goes directly to H8."
            ),
        )
    )
    add(
        spec(
            21,
            sel_word(39, "[ 8. DON'T KNOW\\"),
            F,
            "p21_h6_dont_know",
            routes=H_BUSINESS,
            note="Exact printed H6 don't-know fallthrough branch retained.",
        )
    )
    add(
        *question(
            21,
            sel_block(40, 42),
            "p21_h7_business_share",
            anchor_kind=M,
            parents=("p21_business_aggregate",),
            routes=H7_FALLTHROUGH,
        )
    )
    add(
        *question(
            21,
            sel_block(48, 49),
            "p21_h8_head_total",
            anchor_kind=T,
            routes=H_AFTER_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(48, "HEAD"),
            R,
            "p21_role_head_h8",
            routes=H_AFTER_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(48, "wages and salaries"),
            M,
            "p21_h8_wages",
            parents=("p21_h8_head_total",),
            routes=H_AFTER_BUSINESS,
        )
    )

    add(
        *question(
            22,
            sel_block(4, 5),
            "p22_h9_bonus",
            anchor_kind=M,
            parents=("p21_h8_head_total",),
            routes=H_AFTER_BUSINESS,
        )
    )
    add(
        spec(
            22,
            sel_word(7, "[ IYES"),
            F,
            "p22_h9_yes",
            routes=H_AFTER_BUSINESS,
        )
    )
    add(
        spec(
            22,
            sel_word(7, "[ ]NO (GO TO Hll)"),
            F,
            "p22_h9_no",
            routes=H_AFTER_BUSINESS,
        )
    )
    add(
        *question(
            22,
            sel_line(12),
            "p22_h10_bonus_amount",
            anchor_kind=None,
            routes=H9_YES,
        )
    )
    add(
        *question(
            22,
            sel_line(15),
            "p22_h11_other_income",
            anchor_kind=None,
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            22,
            sel_word(15, "HEAD"),
            R,
            "p22_role_head_h11",
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            22,
            sel_word(16, '(IF "YES" To ANY'),
            F,
            "p22_h11_any_yes",
            routes=H_AFTER_BONUS,
            note="Exact printed conditional amount-followup branch retained.",
        )
    )
    add(
        spec(
            22,
            sel_tail(16, "a)"),
            M,
            "p22_h11a_professional",
            routes=H11_ANY_YES,
        )
    )
    add(
        spec(
            22,
            sel_block(17, 18),
            M,
            "p22_h11b_farming_roomers",
            routes=H11_ANY_YES,
            note=(
                "One printed remuneration item spans farming or market "
                "gardening and roomers or boarders; the two-column exact "
                "source span is retained without multiplying the item."
            ),
        )
    )
    add(
        spec(
            22,
            sel_word(17, "farming or market gardening"),
            FA,
            "p22_h11b_farm_source",
            routes=H11_ANY_YES,
        )
    )
    add(
        spec(
            22,
            sel_block(17, 19),
            P,
            "p22_h11_amount_prompt",
            routes=H11_ANY_YES,
            note=(
                "Exact two-column Poppler span carrying the printed ASK "
                "'How much was it?' and ENTER AMOUNT purpose."
            ),
        )
    )

    add(
        *question(
            23,
            sel_line(36),
            "p23_h22_checkpoint",
            anchor_kind=None,
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            23,
            sel_word(36, "HEAD"),
            R,
            "p23_role_head_h22",
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            23,
            sel_word(36, "WIFE"),
            R,
            "p23_role_wife_h22",
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            23,
            sel_word(37, "YES, WIFE IN FU"),
            F,
            "p23_h22_yes_wife",
            routes=H_AFTER_BONUS,
        )
    )
    add(
        spec(
            23,
            sel_word(
                37, "NO WIFE IN FU OR FU HAS FEMALEHEAD (TURN TO H26, PAGE 24)"
            ),
            F,
            "p23_h22_no_wife",
            routes=H_AFTER_BONUS,
        )
    )
    add(
        *question(
            23,
            sel_line(40),
            "p23_h23_wife_income",
            anchor_kind=C,
            routes=H_WIFE,
        )
    )
    add(spec(23, sel_word(40, "wife"), R, "p23_role_wife_h23", routes=H_WIFE))
    add(spec(23, sel_word(41, "[ IYES"), F, "p23_h23_yes", routes=H_WIFE))
    add(
        spec(
            23,
            sel_word(41, "[ ]NO (TURN TO H26, PAGE 24)"),
            F,
            "p23_h23_no",
            routes=H_WIFE,
        )
    )
    add(
        *question(
            23,
            sel_line(43),
            "p23_h24_source",
            parents=("p23_h24_business",),
            routes=H_WIFE_INCOME,
        )
    )
    add(
        spec(
            23,
            sel_word(43, "wages, salary"),
            M,
            "p23_h24_wages",
            parents=("p23_h25_role_total",),
            routes=H_WIFE_INCOME,
        )
    )
    add(
        spec(
            23,
            sel_word(43, "a business"),
            BA,
            "p23_h24_business",
            routes=H_WIFE_INCOME,
        )
    )
    add(
        *question(
            23,
            sel_line(48),
            "p23_h25_role_total",
            anchor_kind=T,
            routes=H_WIFE_INCOME,
        )
    )

    # Section M: new-head first job and lifetime job-kind history.
    add(spec(38, sel_line(2), F, "p38_sec_m"))
    add(
        spec(
            38,
            sel_word(7, "FU HAS ANEWHEADTHIS YEAR"),
            F,
            "p38_new_head",
            routes=(SEC_M,),
        )
    )
    add(
        spec(
            38,
            sel_word(7, "THIS FIJ HAS THE SAMEHEADAS IN 1971"),
            F,
            "p38_same_head",
            routes=(SEC_M,),
        )
    )
    add(
        spec(
            38, sel_word(7, "HEAD", 0), R, "p38_role_new_head", routes=(SEC_M,)
        )
    )
    add(
        spec(
            38,
            sel_word(7, "HEAD", 1),
            R,
            "p38_role_same_head",
            routes=(SEC_M,),
        )
    )
    add(
        cross_reference(
            38,
            sel_word(7, "THIS FIJ HAS THE SAMEHEADAS IN 1971"),
            "p38_same_head_crossref",
            routes=(SEC_M,),
            alias_keys=("p38_role_same_head",),
            evidence_keys=("p38_same_head_crossref", "p38_role_same_head"),
            target_scope="cross_document",
        )
    )
    add(
        spec(
            38,
            sel_line(8),
            F,
            "p38_same_head_exit",
            routes=(SEC_M + ("p38_same_head",),),
        )
    )
    add(
        *question(
            38,
            sel_line(26),
            "p38_m4_first_job",
            parents=("p38_first_job",),
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        spec(
            38,
            sel_word(26, "HEAD's"),
            R,
            "p38_role_head_m4",
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        spec(
            38,
            sel_word(26, "first        full     time regular    job"),
            J,
            "p38_first_job",
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        spec(
            38,
            sel_block(27, 28),
            F,
            "p38_never_worked_exit",
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        *question(
            38,
            sel_block(29, 30),
            "p38_m5_job_kinds",
            anchor_kind=None,
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        spec(
            38,
            sel_word(30, "same occupation"),
            C,
            "p38_same_occupation_context",
            parents=("p38_first_job",),
            routes=(M_NEW_HEAD,),
        )
    )
    add(
        cross_reference(
            38,
            sel_word(30, "same occupation you started             in"),
            "p38_m5_occupation_crossref",
            routes=(M_NEW_HEAD,),
            alias_keys=("p38_same_occupation_context",),
            canonical_keys=("p38_m4_first_job",),
            evidence_keys=(
                "p38_m4_first_job",
                "p38_m5_occupation_crossref",
                "p38_same_occupation_context",
            ),
            resolution_status="document_local_source_evidence_complete",
        )
    )

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

    branch_refs_by_key: dict[str, dict[tuple[str, ...], str]] = {}
    final_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        paths: list[list[str]] = []
        for route in row["routes"]:
            path: list[str] = []
            for parent_key in route:
                variants = branch_refs_by_key.get(parent_key)
                if variants is None or tuple(path) not in variants:
                    raise SpecError(
                        f"{row['key']} routes through unresolved {parent_key} "
                        f"after {path}"
                    )
                path.append(variants[tuple(path)])
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
            branch_refs_by_key[row["key"]] = {
                tuple(path): annotation._review_branch_ref(
                    row["review_occurrence_id"], path, len(paths)
                )
                for path in paths
            }

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

    source_order_by_key = {
        row["key"]: position for position, row in enumerate(occurrence_specs)
    }
    repeat_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        repeat = row.get("repeat")
        if repeat is None:
            continue
        alias_keys = sorted(
            repeat["alias_keys"], key=source_order_by_key.__getitem__
        )
        canonical_keys = sorted(
            repeat["canonical_keys"], key=source_order_by_key.__getitem__
        )
        evidence_keys = sorted(
            repeat["evidence_keys"], key=source_order_by_key.__getitem__
        )
        repeat_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "relation": repeat["relation"],
                "alias_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in alias_keys
                ],
                "canonical_anchor_review_occurrence_ids": [
                    review_id_by_key[key] for key in canonical_keys
                ],
                "evidence_review_occurrence_ids": [
                    review_id_by_key[key] for key in evidence_keys
                ],
                "target_scope": repeat["target_scope"],
                "resolution_status": repeat["resolution_status"],
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
            "whole_page_review": "all_42_pages_including_empty_occurrence_pages",
            "span_granularity": "exact_utf8_lexeme_physical_line_or_source_block",
            "candidate_nonselection": "candidates_joined_only_after_source_rows_complete",
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
        "repeat_alias_specs": repeat_specs,
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
        f"document 10 source review: {len(review['occurrence_specs'])} "
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
