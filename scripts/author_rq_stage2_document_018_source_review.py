#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 18.

``q76.pdf`` is the 62-page 1976 heads-and-wives questionnaire.  Every page
was reviewed from authenticated Poppler text and a full-page rendering before
these selectors were written.  This module never opens the stage-1 candidate
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
F15 interviewer check does not assert an anchor identity.
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
import build_rq_stage2_document_018_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 62


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
    1: "Heads cover and section A reviewed; no retained field occurrence.",
    2: "Transportation screen reviewed; no ratified R_Q field retained.",
    3: "Housing screen reviewed; no ratified R_Q field retained.",
    4: "Housing and residential-mobility screen reviewed; no retained field.",
    5: "Heads section D assignment, occupation, and industry screen retained.",
    6: "Heads D5-D24 employee/self, government, incorporation, and tenure screen retained.",
    7: "Heads D25-D37 reviewed; tenure/job-history fields retained, training prose excluded.",
    8: "Heads D38-D50 work-absence and exposure screen retained.",
    9: "Heads D51-D63 work exposure, pay, and pension-coverage screen retained.",
    10: "Heads D64-D75 reviewed; extra-job actual fields retained, counterfactuals excluded.",
    11: "Commuting, job-finding chance, and retirement-intention screen reviewed and excluded.",
    12: "Mobility, limitation, and counterfactual work-preference screen reviewed and excluded.",
    13: "Heads section E sought-job and last-job fields retained; search/training prose excluded.",
    14: "Heads E16-E28 work-absence and exposure screen retained.",
    15: "Heads E29-E34 reviewed; actual exposure retained, commuting/counterfactuals excluded.",
    16: "Heads section F actual-work fields retained; future-work and commuting prose excluded.",
    17: "Heads F15-F27 reviewed; sought-job/pay fields retained, limitations/training excluded.",
    18: "Heads search-effort and residential-mobility screen reviewed and excluded.",
    19: "Heads section G wife work attachment, occupation, industry, and exposure retained.",
    20: "Housework screen reviewed; no ratified R_Q field retained.",
    21: "Food and food-stamp screen reviewed; no ratified R_Q field retained.",
    22: "Printed blank page reviewed; no occurrence retained.",
    23: "Section H farm, business, wages, and aggregate fields retained.",
    24: "Section H actual head remuneration rows retained; transfers/assets excluded.",
    25: "Section H wife role-total and actual-income amount fields retained.",
    26: "Other-family-member income screen reviewed; outside the two-role R_Q domain.",
    27: "Other-family-member continuation reviewed; outside the two-role R_Q domain.",
    28: "Other income, support, union, and health screen reviewed and excluded.",
    29: "Heads section J lifetime work-history fields retained.",
    30: "Heads section J return-to-work identity and actual earnings fields retained.",
    31: "Heads section K new-head first-job fields retained; background items excluded.",
    32: "Background, children, and family-history screen reviewed and excluded.",
    33: "Background and schooling screen reviewed and excluded.",
    34: "Education, religion, and by-observation screen reviewed and excluded.",
    35: "By-observation screen reviewed; no ratified R_Q field retained.",
    36: "Wives cover/background screen reviewed; no retained field occurrence.",
    37: "Wives background screen reviewed; no ratified R_Q field retained.",
    38: "Wives schooling, religion, and health screen reviewed and excluded.",
    39: "Wives housework and child-care screen reviewed and excluded.",
    40: "Wives B9 present-job attachment retained; child-care fields excluded.",
    41: "Counterfactual child-care and labour-supply screen reviewed and excluded.",
    42: "Wives C5/C11-C14 pre-marriage work-history fields retained.",
    43: "Fertility and future-job-plan screen reviewed and excluded.",
    44: "Attitudes and children screen reviewed; no ratified R_Q field retained.",
    45: "Wives section D assignment, occupation, and industry screen retained.",
    46: "Wives D5-D24 employee/self, government, incorporation, and tenure screen retained.",
    47: "Wives D25-D37 reviewed; tenure/job-history fields retained, training prose excluded.",
    48: "Wives D38-D50 work-absence and exposure screen retained.",
    49: "Wives D51-D63 work exposure, pay, and pension-coverage screen retained.",
    50: "Wives D64-D75 reviewed; extra-job actual fields retained, counterfactuals excluded.",
    51: "Wives commuting, job-finding chance, and retirement-intention screen excluded.",
    52: "Wives mobility, limitations, and counterfactual work-preference screen excluded.",
    53: "Wives section E sought-job and last-job fields retained; search/training excluded.",
    54: "Wives E17-E26 work-absence and exposure screen retained.",
    55: "Wives E27-E35 reviewed; actual exposure retained, commuting/counterfactuals excluded.",
    56: "Wives section F actual-work fields retained; future-work and commuting excluded.",
    57: "Wives F13-F27 reviewed; sought-job/pay fields retained, limitations/training excluded.",
    58: "Wives search-effort, housework, and mobility screen reviewed and excluded.",
    59: "Wives section G lifetime work-history fields retained.",
    60: "Wives section G return-to-work identity and actual earnings fields retained.",
    61: "Feelings screen reviewed; no ratified R_Q field retained.",
    62: "By-observation screen reviewed; no ratified R_Q field retained.",
}


SEC_DH = ("p5_sec_d",)
D_BOTH_H = SEC_DH + ("p6_d5_both",)
D_SHORT_H = SEC_DH + ("p7_less_than_year",)
SEC_EH = ("p13_sec_e",)
SEC_FH = ("p16_sec_f",)
SEC_GH = ("p19_sec_g",)
SEC_H = ("p23_sec_h",)
H_FARMER = SEC_H + ("p23_farmer",)
H_WIFE = SEC_H + ("p25_yes_wife",)
H23_YES = H_WIFE + ("p25_h23_yes",)
SEC_J = ("p29_sec_j",)
SEC_K = ("p31_sec_k",)
K_NEW = SEC_K + ("p31_new_head",)
K_SAME = SEC_K + ("p31_same_head",)
SEC_CW = ("p42_sec_c",)
SEC_DW = ("p45_sec_d",)
D_SHORT_W = SEC_DW + ("p47_less_than_year",)
D_NO_PREVIOUS_W = D_SHORT_W + ("p47_no_previous_job",)
SEC_EW = ("p53_sec_e",)
SEC_FW = ("p56_sec_f",)
SEC_GW = ("p59_sec_g",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    add(spec(5, sel_tail(7, "SECTION D:"), F, "p5_sec_d"))
    add(spec(5, sel_word(10, "HEAD"), R, "p5_role_head", routes=(SEC_DH,)))
    add(*question(5, sel_block(10, 11), "p5_d1_assignment", routes=(SEC_DH,)))
    add(
        *question(
            5, sel_line(16), "p5_d3_detail", anchor_kind=None, routes=(SEC_DH,)
        )
    )
    add(*question(5, sel_block(21, 22), "p5_d4_industry", routes=(SEC_DH,)))

    add(*question(6, sel_line(4), "p6_d5_employee_self", routes=(SEC_DH,)))
    add(spec(6, sel_line(6), F, "p6_d5_both", routes=(SEC_DH,)))
    add(
        *question(
            6,
            sel_word(9, "D6. Do you work for the"),
            "p6_d6_government",
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            6,
            sel_word(9, "D11. When you work for"),
            "p6_d11_government",
            routes=(D_BOTH_H,),
        )
    )
    add(
        *question(
            6,
            sel_word(9, "Dl9.    Is your business"),
            "p6_d19_incorporation",
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            6,
            sel_word(21, "5. NO (GO TO D15)"),
            F,
            "p6_d12_no",
            routes=(D_BOTH_H,),
        )
    )
    add(
        *question(
            6, sel_block(43, 44), "p6_d16_incorporation", routes=(D_BOTH_H,)
        )
    )
    add(
        spec(
            6,
            sel_word(51, "5. NO (GO TO D22)"),
            F,
            "p6_d17_no",
            routes=(D_BOTH_H,),
        )
    )
    add(
        spec(
            6,
            sel_word(57, "(GO TO D22)", 0),
            F,
            "p6_go_d22_1",
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            6,
            sel_word(57, "(GO TO D22)", 1),
            F,
            "p6_go_d22_2",
            routes=(D_BOTH_H,),
        )
    )
    add(
        spec(
            6,
            sel_word(57, "(TURN TO PAGE 7, D25)"),
            F,
            "p6_turn_d25",
            routes=(SEC_DH,),
        )
    )
    add(*question(6, sel_block(65, 66), "p6_d24_tenure", routes=(SEC_DH,)))

    add(*question(7, sel_line(32), "p7_d32_tenure", routes=(SEC_DH,)))
    add(
        spec(
            7,
            sel_word(32, "present                  position"),
            J,
            "p7_present_position",
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            7,
            sel_word(34, "IF LESS THAN ONE YEAR"),
            F,
            "p7_less_than_year",
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            7,
            sel_word(34, "IF ONE YEAR OR MORE"),
            F,
            "p7_one_year_or_more",
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            7,
            sel_word(
                34, "(TURN                               TO PAGE 8, D38)"
            ),
            F,
            "p7_long_tenure_exit",
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            7,
            sel_line(37),
            "p7_d33_start",
            parents=("p7_present_position",),
            routes=(D_SHORT_H,),
        )
    )
    add(
        *question(
            7,
            sel_block(38, 39),
            "p7_d34_previous",
            anchor_kind=None,
            routes=(D_SHORT_H,),
        )
    )
    add(
        *question(
            7,
            sel_block(44, 45),
            "p7_d35_compare",
            anchor_kind=None,
            routes=(D_SHORT_H,),
        )
    )
    add(
        *question(
            7,
            sel_block(49, 50),
            "p7_d36_reason",
            anchor_kind=None,
            routes=(D_SHORT_H,),
        )
    )
    add(
        *question(
            7,
            sel_line(53),
            "p7_d37_pay_compare",
            anchor_kind=None,
            routes=(D_SHORT_H,),
        )
    )
    add(spec(7, sel_line(58), F, "p7_turn_d38", routes=(D_SHORT_H,)))

    add(*question(8, sel_line(5), "p8_d38_family_sick", routes=(SEC_DH,)))
    add(
        *question(
            8, sel_block(10, 11), "p8_d40_family_sick_time", routes=(SEC_DH,)
        )
    )
    add(*question(8, sel_block(14, 15), "p8_d41_own_sick", routes=(SEC_DH,)))
    add(spec(8, sel_line(16), F, "p8_go_d43", routes=(SEC_DH,)))
    add(
        *question(
            8, sel_block(19, 20), "p8_d42_own_sick_time", routes=(SEC_DH,)
        )
    )
    add(*question(8, sel_line(22), "p8_d43_paid_vacation", routes=(SEC_DH,)))
    add(*question(8, sel_line(24), "p8_d44_vacation", routes=(SEC_DH,)))
    add(
        *question(
            8, sel_block(29, 30), "p8_d45_vacation_time", routes=(SEC_DH,)
        )
    )
    add(*question(8, sel_line(31), "p8_d46_strike", routes=(SEC_DH,)))
    add(
        *question(8, sel_block(36, 37), "p8_d47_strike_time", routes=(SEC_DH,))
    )
    add(*question(8, sel_line(39), "p8_d48_unemployed", routes=(SEC_DH,)))
    add(
        *question(
            8, sel_block(44, 45), "p8_d49_unemployed_time", routes=(SEC_DH,)
        )
    )
    add(*question(8, sel_block(47, 48), "p8_d50_periods", routes=(SEC_DH,)))

    add(
        *question(
            9,
            sel_block(6, 7),
            "p9_d51_weeks",
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(spec(9, sel_word(6, "main job"), J, "p9_main_job", routes=(SEC_DH,)))
    add(
        *question(
            9,
            sel_block(9, 10),
            "p9_d52_hours",
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_line(12),
            "p9_d53_overtime",
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_block(17, 18),
            "p9_d54_overtime_hours",
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_block(19, 20),
            "p9_d55_pay_type",
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(23, "D56. How much is your salary?"),
            "p9_d56_salary",
            anchor_kind=M,
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(23, "D59. What is your hourly"),
            "p9_d59_hourly",
            anchor_kind=M,
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(23, "D61. How is that?"),
            "p9_d61_unit",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(26, "D57.    If you were to work more"),
            "p9_d57_extra_pay",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(29, "D60. What is your hourly"),
            "p9_d60_overtime_rate",
            anchor_kind=M,
            parents=("p9_main_job",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(32, "D62. If     you worked an"),
            "p9_d62_extra_hour",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            9,
            sel_word(35, "D58. About how much"),
            "p9_d58_overtime_amount",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    for ordinal in range(3):
        add(
            spec(
                9,
                sel_word(43, "(GO TO D63)", ordinal),
                F,
                f"p9_go_d63_{ordinal + 1}",
                routes=(SEC_DH,),
            )
        )
    add(
        *question(
            9, sel_block(46, 47), "p9_d63_pension_coverage", routes=(SEC_DH,)
        )
    )

    add(
        *question(
            10,
            sel_block(4, 5),
            "p10_d64_extra_jobs",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    add(
        spec(
            10,
            sel_word(4, "extra jobs"),
            J,
            "p10_extra_jobs",
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            10,
            sel_block(10, 11),
            "p10_d65_occupation",
            parents=("p10_extra_jobs",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            10,
            sel_block(13, 14),
            "p10_d66_other",
            anchor_kind=None,
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            10,
            sel_block(16, 17),
            "p10_d67_hourly",
            anchor_kind=M,
            parents=("p10_extra_jobs",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            10,
            sel_block(18, 19),
            "p10_d68_weeks",
            parents=("p10_extra_jobs",),
            routes=(SEC_DH,),
        )
    )
    add(
        *question(
            10,
            sel_block(21, 22),
            "p10_d69_hours",
            parents=("p10_extra_jobs",),
            routes=(SEC_DH,),
        )
    )
    add(spec(10, sel_line(54), F, "p10_turn_d76", routes=(SEC_DH,)))

    add(
        spec(
            13,
            sel_word(
                3,
                "SECTION E:        IF LOOKING FOR WORK, UNEMPLOYEDIN D1",
            ),
            F,
            "p13_sec_e",
        )
    )
    add(
        *question(
            13,
            sel_line(4),
            "p13_e1_sought_occupation",
            parents=("p13_sought_job",),
            routes=(SEC_EH,),
        )
    )
    add(spec(13, sel_word(4, "job"), J, "p13_sought_job", routes=(SEC_EH,)))
    add(
        *question(
            13,
            sel_block(13, 14),
            "p13_e3_expected_pay",
            anchor_kind=M,
            parents=("p13_sought_job",),
            routes=(SEC_EH,),
        )
    )
    add(
        *question(
            13,
            sel_line(40),
            "p13_e11_ever_job",
            anchor_kind=None,
            routes=(SEC_EH,),
        )
    )
    add(
        *question(
            13,
            sel_block(45, 46),
            "p13_e12_last_occupation",
            parents=("p13_last_job",),
            routes=(SEC_EH,),
        )
    )
    add(
        spec(
            13, sel_word(45, "last   job"), J, "p13_last_job", routes=(SEC_EH,)
        )
    )
    add(
        *question(
            13,
            sel_block(48, 49),
            "p13_e13_industry",
            parents=("p13_last_job",),
            routes=(SEC_EH,),
        )
    )
    add(
        *question(
            13,
            sel_block(55, 56),
            "p13_e15_separation",
            anchor_kind=None,
            routes=(SEC_EH,),
        )
    )

    for first, last, key, anchor in (
        (3, 4, "e16_last_work", C),
        (8, 9, "e17_vacation", C),
        (13, 14, "e18_vacation_time", C),
        (15, 16, "e19_family_sick", C),
        (21, 22, "e20_relation", None),
        (25, 26, "e21_family_sick_time", C),
        (28, 29, "e22_own_sick", C),
        (33, 34, "e23_own_sick_time", C),
        (35, 36, "e24_strike", C),
        (40, 41, "e25_strike_time", C),
        (42, 43, "e26_unemployed", C),
        (47, 48, "e27_unemployed_time", C),
        (49, 50, "e28_periods", C),
    ):
        add(
            *question(
                14,
                sel_block(first, last),
                f"p14_{key}",
                anchor_kind=anchor,
                routes=(SEC_EH,),
            )
        )
    add(*question(15, sel_block(5, 7), "p15_e29_weeks", routes=(SEC_EH,)))
    add(*question(15, sel_block(9, 11), "p15_e30_hours", routes=(SEC_EH,)))
    add(spec(15, sel_line(34), F, "p15_turn_g1", routes=(SEC_EH,)))

    add(spec(16, sel_tail(4, "SECTION F:"), F, "p16_sec_f"))
    add(
        *question(
            16,
            sel_line(6),
            "p16_f1_work_for_money",
            anchor_kind=None,
            routes=(SEC_FH,),
        )
    )
    add(
        spec(
            16,
            sel_word(16, "(TURN TO PAGE 17, F15)"),
            F,
            "p16_turn_f15",
            routes=(SEC_FH,),
        )
    )
    add(
        *question(
            16,
            sel_block(34, 35),
            "p16_f11_separation",
            anchor_kind=None,
            routes=(SEC_FH,),
        )
    )
    add(
        *question(
            16,
            sel_line(39),
            "p16_f12_reason",
            anchor_kind=None,
            routes=(SEC_FH,),
        )
    )
    add(
        *question(
            17,
            sel_word(30, "of job do you have in mind               ?"),
            "p17_f18_sought_job",
            parents=("p17_sought_job",),
            routes=(SEC_FH,),
        )
    )
    add(spec(17, sel_word(30, "job"), J, "p17_sought_job", routes=(SEC_FH,)))
    add(
        *question(
            17,
            sel_block(36, 37),
            "p17_f19_expected_pay",
            anchor_kind=M,
            parents=("p17_sought_job",),
            routes=(SEC_FH,),
        )
    )
    add(spec(17, sel_line(45), F, "p17_turn_g1", routes=(SEC_FH,)))

    add(spec(19, sel_line(5), F, "p19_sec_g"))
    add(
        spec(
            19,
            sel_word(5, "WIFE'S"),
            R,
            "p19_role_wife_header",
            routes=(SEC_GH,),
        )
    )
    add(
        *question(
            19,
            sel_line(11),
            "p19_g1_marital",
            anchor_kind=None,
            routes=(SEC_GH,),
        )
    )
    add(spec(19, sel_line(16), F, "p19_turn_g7", routes=(SEC_GH,)))
    add(
        spec(
            19,
            sel_word(19, "WIFE'S"),
            R,
            "p19_role_wife_schedule",
            routes=(SEC_GH,),
        )
    )
    add(
        *question(
            19,
            sel_block(22, 23),
            "p19_g2_work",
            anchor_kind=None,
            routes=(SEC_GH,),
        )
    )
    add(
        spec(19, sel_word(22, "wife"), R, "p19_role_wife_g2", routes=(SEC_GH,))
    )
    add(*question(19, sel_line(31), "p19_g3_occupation", routes=(SEC_GH,)))
    add(*question(19, sel_block(35, 36), "p19_g4_industry", routes=(SEC_GH,)))
    add(*question(19, sel_line(39), "p19_g5_weeks", routes=(SEC_GH,)))
    add(*question(19, sel_line(41), "p19_g6_hours", routes=(SEC_GH,)))

    add(spec(23, sel_word(5, "SECTION H:     INCOME"), F, "p23_sec_h"))
    add(
        spec(
            23,
            sel_word(14, "1. FARMER, OR RANCHER"),
            F,
            "p23_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(14, "5. NOT A FARMEROR RANCHER"),
            F,
            "p23_not_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            23,
            sel_block(17, 19),
            "p23_h2_receipts",
            anchor_kind=M,
            parents=("p23_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_block(21, 22),
            "p23_h3_expenses",
            anchor_kind=M,
            parents=("p23_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_line(24),
            "p23_h4_net_farm",
            anchor_kind=None,
            routes=(H_FARMER,),
        )
    )
    add(
        spec(
            23,
            sel_word(24, "net income from farming"),
            FA,
            "p23_farm_aggregate",
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            23,
            sel_block(28, 29),
            "p23_h5_business",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            23,
            sel_block(34, 36),
            "p23_h6_incorporation",
            parents=("p23_business_aggregate",),
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(34, "unincorporated         business"),
            BA,
            "p23_business_aggregate",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            23,
            sel_block(41, 43),
            "p23_h7_business_share",
            anchor_kind=M,
            parents=("p23_business_aggregate",),
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            23,
            sel_block(49, 50),
            "p23_h8_wages",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(spec(23, sel_word(49, "HEAD"), R, "p23_role_head_h8", routes=(SEC_H,)))

    add(
        *question(
            24, sel_block(5, 6), "p24_h9_bonus", anchor_kind=M, routes=(SEC_H,)
        )
    )
    add(
        *question(
            24,
            sel_line(11),
            "p24_h11_other_income",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(24, sel_word(11, "HEAD"), R, "p24_role_head_h11", routes=(SEC_H,))
    )
    add(
        spec(
            24,
            sel_word(
                13, "a)   professional           practice      or trade?"
            ),
            M,
            "p24_h11a_professional",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            24,
            sel_word(15, "b) farming or market gardening,"),
            M,
            "p24_h11b_farming",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            24,
            sel_word(16, "roomers or boarders?"),
            M,
            "p24_h11b_roomers",
            routes=(SEC_H,),
        )
    )

    for line_number, needle, key in (
        (8, "GO TO H17)", "p25_go_h17_1"),
        (12, "(GO                  TO H17)", "p25_go_h17_2"),
        (21, "(GO TO Hl7)", "p25_go_h17_3"),
        (38, "(GO TO H22)", "p25_go_h22"),
    ):
        add(spec(25, sel_word(line_number, needle), F, key, routes=(SEC_H,)))
    add(
        *question(
            25,
            sel_line(39),
            "p25_h22_checkpoint",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(25, sel_word(39, "HEAD"), R, "p25_role_head_h22", routes=(SEC_H,))
    )
    add(
        spec(25, sel_word(39, "WIFE"), R, "p25_role_wife_h22", routes=(SEC_H,))
    )
    add(
        spec(
            25,
            sel_word(41, "YES, WIFE IN FU"),
            F,
            "p25_yes_wife",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            25,
            sel_word(41, "NO WIFE IN FU OR FU HAS FEMALE"),
            F,
            "p25_no_wife",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            25, sel_line(43), "p25_wife_total", anchor_kind=T, routes=(H_WIFE,)
        )
    )
    add(
        spec(
            25, sel_word(43, "wife"), R, "p25_role_wife_h23", routes=(H_WIFE,)
        )
    )
    add(spec(25, sel_line(45), F, "p25_h23_yes", routes=(H_WIFE,)))
    add(
        *question(
            25,
            sel_line(48),
            "p25_h24_source",
            anchor_kind=None,
            routes=(H23_YES,),
        )
    )
    add(
        *question(
            25,
            sel_line(53),
            "p25_h25_amount",
            anchor_kind=M,
            parents=("p25_wife_total",),
            routes=(H23_YES,),
        )
    )

    add(spec(29, sel_line(8), F, "p29_sec_j"))
    add(*question(29, sel_block(10, 11), "p29_j1_years", routes=(SEC_J,)))
    add(spec(29, sel_word(10, "HEAD"), R, "p29_role_head", routes=(SEC_J,)))
    add(
        spec(
            29,
            sel_word(11, "(TURN               TO PAGE 31, K1)"),
            F,
            "p29_turn_k1",
            routes=(SEC_J,),
        )
    )
    add(*question(29, sel_block(13, 14), "p29_j2_full_time", routes=(SEC_J,)))
    add(
        spec(
            29,
            sel_word(15, "(GO        TO J4)"),
            F,
            "p29_go_j4",
            routes=(SEC_J,),
        )
    )
    add(*question(29, sel_block(18, 20), "p29_j3_time", routes=(SEC_J,)))
    add(
        *question(
            29,
            sel_block(23, 25),
            "p29_j4_break",
            anchor_kind=None,
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            29,
            sel_block(30, 31),
            "p29_j5_periods",
            anchor_kind=None,
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            29,
            sel_word(36, "J6. When was the period you"),
            "p29_j6_period",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            29,
            sel_word(36, "J7. What was the most recent period"),
            "p29_j7_period",
            routes=(SEC_J,),
        )
    )
    add(spec(29, sel_line(42), F, "p29_before_1955", routes=(SEC_J,)))
    add(
        *question(
            29,
            sel_block(45, 46),
            "p29_j8_reason",
            anchor_kind=None,
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            30,
            sel_block(7, 8),
            "p30_j10_return_reason",
            anchor_kind=None,
            routes=(SEC_J,),
        )
    )
    add(*question(30, sel_block(12, 13), "p30_j11_same_work", routes=(SEC_J,)))
    add(
        *question(
            30,
            sel_word(17, "J12.   Was it   the same job?"),
            "p30_j12_same_job",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            30,
            sel_line(35),
            "p30_j15_return_earnings",
            anchor_kind=M,
            routes=(SEC_J,),
        )
    )

    add(spec(31, sel_line(5), F, "p31_sec_k"))
    add(
        spec(
            31,
            sel_word(9, "1. FU HAS A NEW HEAD THIS YEAR"),
            F,
            "p31_new_head",
            routes=(SEC_K,),
        )
    )
    add(
        spec(
            31,
            sel_word(9, "5. THIS FU HAS THE SAME HEAD AS IN 1975"),
            F,
            "p31_same_head",
            routes=(SEC_K,),
        )
    )
    add(spec(31, sel_line(10), F, "p31_turn_l1", routes=(K_SAME,)))
    add(
        *question(
            31,
            sel_line(29),
            "p31_k4_first_job",
            parents=("p31_first_job",),
            routes=(K_NEW,),
        )
    )
    add(
        spec(
            31, sel_word(29, "HEAD'S"), R, "p31_role_head_k4", routes=(K_NEW,)
        )
    )
    add(
        spec(
            31,
            sel_word(29, "first         full        time regular        job"),
            J,
            "p31_first_job",
            routes=(K_NEW,),
        )
    )
    add(spec(31, sel_line(32), F, "p31_go_k6", routes=(K_NEW,)))
    add(
        *question(
            31,
            sel_block(34, 35),
            "p31_k5_job_kinds",
            routes=(K_NEW,),
        )
    )

    add(
        *question(
            40, sel_line(6), "p40_b9_present_job", parents=("p40_present_job",)
        )
    )
    add(spec(40, sel_word(6, "job"), J, "p40_present_job"))
    for ordinal in range(3):
        add(
            spec(
                40,
                sel_word(
                    34 if ordinal == 0 else 35 if ordinal == 1 else 40,
                    "(GO TO B18)",
                ),
                F,
                f"p40_go_b18_{ordinal + 1}",
            )
        )
    add(spec(40, sel_line(54), F, "p40_turn_c1"))

    add(spec(42, sel_line(6), F, "p42_sec_c"))
    add(
        *question(
            42,
            sel_word(14, "C11. Before you were first   married, did"),
            "p42_c11_work",
            parents=("p42_c11_job",),
            routes=(SEC_CW,),
        )
    )
    add(
        spec(
            42,
            sel_word(15, "youhave a job working for money?"),
            J,
            "p42_c11_job",
            routes=(SEC_CW,),
        )
    )
    add(
        *question(42, sel_block(19, 20), "p42_c12_full_time", routes=(SEC_CW,))
    )
    add(
        *question(
            42,
            sel_word(27, "C13. Did you work for money during"),
            "p42_c13_work",
            routes=(SEC_CW,),
        )
    )
    add(
        *question(
            42,
            sel_word(
                28,
                "C5. Before you were first  married,            did you",
            ),
            "p42_c5_work",
            parents=("p42_c5_job",),
            routes=(SEC_CW,),
        )
    )
    add(
        spec(
            42,
            sel_word(30, "have a job working for money?"),
            J,
            "p42_c5_job",
            routes=(SEC_CW,),
        )
    )
    add(
        *question(42, sel_block(33, 34), "p42_c14_full_time", routes=(SEC_CW,))
    )
    add(
        spec(
            42,
            sel_word(41, "(TURN TO PAGE 8, C15)"),
            F,
            "p42_turn_c15_1",
            routes=(SEC_CW,),
        )
    )
    add(spec(42, sel_line(46), F, "p42_turn_c15_2", routes=(SEC_CW,)))

    add(spec(45, sel_line(8), F, "p45_sec_d"))
    add(spec(45, sel_word(12, "WIFE"), R, "p45_role_wife", routes=(SEC_DW,)))
    add(
        *question(45, sel_block(12, 13), "p45_d1_assignment", routes=(SEC_DW,))
    )
    add(
        *question(45, sel_block(18, 19), "p45_d2_occupation", routes=(SEC_DW,))
    )
    add(
        *question(
            45,
            sel_line(23),
            "p45_d3_detail",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(*question(45, sel_block(28, 29), "p45_d4_industry", routes=(SEC_DW,)))

    add(
        *question(
            46, sel_block(6, 8), "p46_d5_employee_self", routes=(SEC_DW,)
        )
    )
    add(
        *question(
            46,
            sel_word(12, ". Do you work for the"),
            "p46_d6_government",
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            46,
            sel_word(12, "D11. When you work for others,   do"),
            "p46_d11_government",
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            46,
            sel_word(12, "D19. Is your business"),
            "p46_d19_incorporation",
            routes=(SEC_DW,),
        )
    )
    add(spec(46, sel_line(24), F, "p46_go_d10", routes=(SEC_DW,)))
    add(
        *question(
            46, sel_block(42, 43), "p46_d16_incorporation", routes=(SEC_DW,)
        )
    )
    for ordinal in range(2):
        add(
            spec(
                46,
                sel_word(53, "(GO TO D22)", ordinal),
                F,
                f"p46_go_d22_{ordinal + 1}",
                routes=(SEC_DW,),
            )
        )
    add(
        spec(
            46,
            sel_word(53, "(TURN TO PAGE 12, D25)"),
            F,
            "p46_turn_d25",
            routes=(SEC_DW,),
        )
    )
    add(*question(46, sel_block(61, 63), "p46_d24_tenure", routes=(SEC_DW,)))

    add(*question(47, sel_block(32, 33), "p47_d32_tenure", routes=(SEC_DW,)))
    add(
        spec(
            47,
            sel_word(32, "present               position"),
            J,
            "p47_present_position",
            routes=(SEC_DW,),
        )
    )
    add(
        spec(
            47,
            sel_word(33, "(IF LESS THAN ONE YEAR)"),
            F,
            "p47_less_than_year",
            routes=(SEC_DW,),
        )
    )
    add(
        spec(
            47,
            sel_word(33, "IF ONE YEAR OR MORE"),
            F,
            "p47_one_year_or_more",
            routes=(SEC_DW,),
        )
    )
    add(
        spec(
            47,
            sel_word(33, "TURN TO PAGE 13, D38)"),
            F,
            "p47_long_tenure_exit",
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            47,
            sel_block(37, 38),
            "p47_d33_start",
            parents=("p47_present_position",),
            routes=(D_SHORT_W,),
        )
    )
    add(
        *question(
            47,
            sel_block(39, 40),
            "p47_d34_previous",
            anchor_kind=None,
            routes=(D_SHORT_W,),
        )
    )
    add(spec(47, sel_line(42), F, "p47_no_previous_job", routes=(D_SHORT_W,)))
    add(
        spec(
            47,
            sel_line(43),
            F,
            "p47_turn_d38_1",
            routes=(D_NO_PREVIOUS_W,),
        )
    )
    add(
        *question(
            47,
            sel_block(48, 49),
            "p47_d35_compare",
            anchor_kind=None,
            routes=(D_SHORT_W,),
        )
    )
    add(spec(47, sel_line(58), F, "p47_turn_d38_2", routes=(D_SHORT_W,)))

    for first, last, key, anchor in (
        (6, 7, "d38_family_sick", C),
        (11, 13, "d39_relation", None),
        (15, 16, "d40_family_sick_time", C),
        (19, 20, "d41_own_sick", C),
        (23, 24, "d42_own_sick_time", C),
        (26, 27, "d43_paid_vacation", C),
        (28, 29, "d44_vacation", C),
        (32, 33, "d45_vacation_time", C),
        (35, 36, "d46_strike", C),
        (39, 40, "d47_strike_time", C),
        (42, 44, "d48_unemployed", C),
        (49, 50, "d49_unemployed_time", C),
        (52, 52, "d50_periods", C),
    ):
        add(
            *question(
                48,
                sel_block(first, last),
                f"p48_{key}",
                anchor_kind=anchor,
                routes=(SEC_DW,),
            )
        )

    add(
        *question(
            49,
            sel_block(6, 7),
            "p49_d51_weeks",
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(spec(49, sel_word(6, "main job"), J, "p49_main_job", routes=(SEC_DW,)))
    add(
        *question(
            49,
            sel_block(9, 11),
            "p49_d52_hours",
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_line(13),
            "p49_d53_overtime",
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_line(18),
            "p49_d54_overtime_hours",
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_block(21, 22),
            "p49_d55_pay_type",
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(27, "D56. How much is your salary?"),
            "p49_d56_salary",
            anchor_kind=M,
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(27, "D59. What is your hourly"),
            "p49_d59_hourly",
            anchor_kind=M,
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(27, "D61. How is that?"),
            "p49_d61_unit",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(31, "D57. If you were to work more"),
            "p49_d57_extra_pay",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(34, "D60. What is your hourly"),
            "p49_d60_overtime_rate",
            anchor_kind=M,
            parents=("p49_main_job",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(39, "D62. If you worked an"),
            "p49_d62_extra_hour",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            49,
            sel_word(43, "D58. About how much"),
            "p49_d58_overtime_amount",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    for ordinal in range(3):
        add(
            spec(
                49,
                sel_word(49, "(GO TO D63)", ordinal),
                F,
                f"p49_go_d63_{ordinal + 1}",
                routes=(SEC_DW,),
            )
        )
    add(
        *question(
            49, sel_block(51, 53), "p49_d63_pension_coverage", routes=(SEC_DW,)
        )
    )

    add(
        *question(
            50,
            sel_block(6, 7),
            "p50_d64_extra_jobs",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(
        spec(
            50,
            sel_word(6, "extra      jobs"),
            J,
            "p50_extra_jobs",
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            50,
            sel_block(12, 13),
            "p50_d65_occupation",
            parents=("p50_extra_jobs",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            50,
            sel_block(15, 16),
            "p50_d66_other",
            anchor_kind=None,
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            50,
            sel_block(18, 19),
            "p50_d67_hourly",
            anchor_kind=M,
            parents=("p50_extra_jobs",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            50,
            sel_block(20, 22),
            "p50_d68_weeks",
            parents=("p50_extra_jobs",),
            routes=(SEC_DW,),
        )
    )
    add(
        *question(
            50,
            sel_block(23, 25),
            "p50_d69_hours",
            parents=("p50_extra_jobs",),
            routes=(SEC_DW,),
        )
    )

    add(
        spec(
            53,
            sel_word(
                5,
                "SECTION E:      IF LOOKING FOR WORK, UNEMPLOYEDIN D1",
            ),
            F,
            "p53_sec_e",
        )
    )
    add(
        *question(
            53,
            sel_block(7, 8),
            "p53_e1_sought_occupation",
            parents=("p53_sought_job",),
            routes=(SEC_EW,),
        )
    )
    add(spec(53, sel_word(7, "job"), J, "p53_sought_job", routes=(SEC_EW,)))
    add(
        *question(
            53,
            sel_block(15, 16),
            "p53_e3_expected_pay",
            anchor_kind=M,
            parents=("p53_sought_job",),
            routes=(SEC_EW,),
        )
    )
    add(
        *question(
            53,
            sel_block(43, 44),
            "p53_e12_ever_job",
            anchor_kind=None,
            routes=(SEC_EW,),
        )
    )
    add(
        *question(
            53,
            sel_block(45, 46),
            "p53_e13_last_occupation",
            parents=("p53_last_job",),
            routes=(SEC_EW,),
        )
    )
    add(
        spec(
            53,
            sel_word(45, "last      job"),
            J,
            "p53_last_job",
            routes=(SEC_EW,),
        )
    )
    add(
        *question(
            53,
            sel_block(48, 49),
            "p53_e14_industry",
            parents=("p53_last_job",),
            routes=(SEC_EW,),
        )
    )
    add(
        *question(
            53,
            sel_block(54, 56),
            "p53_e16_separation",
            anchor_kind=None,
            routes=(SEC_EW,),
        )
    )

    for first, last, key, anchor in (
        (6, 7, "e17_last_work", C),
        (11, 12, "e18_vacation", C),
        (15, 16, "e19_vacation_time", C),
        (21, 21, "e21_relation", None),
        (26, 27, "e22_family_sick_time", C),
        (31, 32, "e23_own_sick", C),
        (35, 36, "e24_own_sick_time", C),
        (38, 39, "e25_strike", C),
        (42, 44, "e26_strike_time", C),
    ):
        add(
            *question(
                54,
                sel_block(first, last),
                f"p54_{key}",
                anchor_kind=anchor,
                routes=(SEC_EW,),
            )
        )
    for first, last, key in (
        (6, 7, "e27_unemployed"),
        (12, 13, "e28_unemployed_time"),
        (15, 16, "e29_periods"),
        (20, 22, "e30_weeks"),
        (24, 25, "e31_hours"),
    ):
        add(
            *question(
                55, sel_block(first, last), f"p55_{key}", routes=(SEC_EW,)
            )
        )
    add(spec(55, sel_line(47), F, "p55_turn_g1", routes=(SEC_EW,)))

    add(
        spec(
            56,
            sel_word(
                5,
                "SECTION F:      RETIRED, HOUSEWIFE, STUDENT, "
                "PERMANENTLYDISABLED",
            ),
            F,
            "p56_sec_f",
        )
    )
    add(
        *question(
            56,
            sel_line(6),
            "p56_f1_work_for_money",
            anchor_kind=None,
            routes=(SEC_FW,),
        )
    )
    add(
        spec(
            56,
            sel_word(15, "(TURN TO PAGE 22, F15)"),
            F,
            "p56_turn_f15",
            routes=(SEC_FW,),
        )
    )
    add(
        *question(56, sel_block(19, 20), "p56_f4_occupation", routes=(SEC_FW,))
    )
    add(*question(56, sel_block(22, 23), "p56_f5_industry", routes=(SEC_FW,)))
    add(*question(56, sel_block(24, 25), "p56_f6_weeks", routes=(SEC_FW,)))
    add(*question(56, sel_block(26, 27), "p56_f7_hours", routes=(SEC_FW,)))
    add(
        *question(
            56,
            sel_block(40, 42),
            "p56_f11_separation",
            anchor_kind=None,
            routes=(SEC_FW,),
        )
    )
    add(
        *question(
            56,
            sel_line(47),
            "p56_f12_reason",
            anchor_kind=None,
            routes=(SEC_FW,),
        )
    )
    add(
        *question(
            57,
            sel_word(30, "F18. What kind        of job do you have in"),
            "p57_f18_sought_job",
            parents=("p57_sought_job",),
            routes=(SEC_FW,),
        )
    )
    add(spec(57, sel_word(30, "job"), J, "p57_sought_job", routes=(SEC_FW,)))
    add(
        *question(
            57,
            sel_word(
                35, "F19. How much would you expect                to earn?"
            ),
            "p57_f19_expected_pay",
            anchor_kind=M,
            parents=("p57_sought_job",),
            routes=(SEC_FW,),
        )
    )
    add(spec(57, sel_line(44), F, "p57_turn_g1", routes=(SEC_FW,)))

    add(spec(59, sel_line(5), F, "p59_sec_g"))
    add(*question(59, sel_block(7, 9), "p59_g1_years", routes=(SEC_GW,)))
    add(*question(59, sel_line(11), "p59_g2_full_time", routes=(SEC_GW,)))
    add(*question(59, sel_block(15, 17), "p59_g3_time", routes=(SEC_GW,)))
    add(
        *question(
            59,
            sel_block(19, 20),
            "p59_g4_first_job",
            parents=("p59_first_job",),
            routes=(SEC_GW,),
        )
    )
    add(
        spec(
            59,
            sel_word(19, "first         full     time,    regular    job"),
            J,
            "p59_first_job",
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_block(23, 24),
            "p59_g5_job_kinds",
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_block(29, 32),
            "p59_g6_break",
            anchor_kind=None,
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_block(37, 38),
            "p59_g7_periods",
            anchor_kind=None,
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_word(41, "G8. When was the period you were"),
            "p59_g8_period",
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_word(41, "G9. When was the most recent"),
            "p59_g9_period",
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            59,
            sel_block(50, 53),
            "p59_g10_reason",
            anchor_kind=None,
            routes=(SEC_GW,),
        )
    )
    add(
        *question(
            60,
            sel_block(6, 7),
            "p60_g12_return_reason",
            anchor_kind=None,
            routes=(SEC_GW,),
        )
    )
    add(*question(60, sel_line(11), "p60_g13_same_work", routes=(SEC_GW,)))
    add(
        *question(
            60,
            sel_block(31, 34),
            "p60_g17_return_earnings",
            anchor_kind=M,
            routes=(SEC_GW,),
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

    branch_ref_by_key: dict[str, str] = {}
    final_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        paths: list[list[str]] = []
        for route in row["routes"]:
            path: list[str] = []
            for parent_key in route:
                if parent_key not in branch_ref_by_key:
                    raise SpecError(
                        f"{row['key']} routes through unresolved {parent_key}"
                    )
                path.append(branch_ref_by_key[parent_key])
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
            if len(paths) != 1:
                raise SpecError(f"{row['key']} has multiple parent paths")
            branch_ref_by_key[row["key"]] = annotation._review_branch_ref(
                row["review_occurrence_id"], paths[0], len(paths)
            )

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
            "whole_page_review": "all_62_pages_including_empty_occurrence_pages",
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
        f"document 18 source review: {len(review['occurrence_specs'])} "
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
