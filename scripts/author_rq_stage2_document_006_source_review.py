#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 6.

The authenticated 30-page 1970 family questionnaire was read page by page
before candidate rows were inspected. This module records only exact source
bytes and never opens the stage-1 candidate artifact; the sealed annotation
builder performs the later candidate join.

The retained domain is role and employment assignment, occupation, employee
or self-employment status, job identity and tenure, actual work exposure,
questionnaire remuneration fields, role totals, farm and business aggregates,
and the wife's observed work attachment. Housing, transportation, family listing,
child care, health, job search, mobility, attitudes, training, and other
worklike prose outside those purposes was reviewed but excluded. No global
component IDs or unsupported repeat relationships are assigned.
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
import build_rq_stage2_document_006_annotation as annotation  # noqa: E402

F = "flow_branch_label"
R = "role_anchor"
J = "job_anchor"
M = "remuneration_component_anchor"
T = "role_total_anchor"
FA = "farm_aggregate_anchor"
BA = "business_aggregate_anchor"
C = "context_anchor"
P = "field_purpose_prompt"
X = "repeat_or_alias_instruction"

REVIEW_PATH = annotation.REVIEW_PATH
PAGE_COUNT = 30


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


# The questionnaire's side-by-side layout occasionally places two questions on one
# Poppler physical line. This selector retains one exact column segment.
_base_resolve = resolve


def resolve_segment(
    page_text: str,
    line_number: int,
    start_needle: str,
    end_needle: str,
) -> tuple[int, int]:
    line_start, line_end = resolve_line(page_text, line_number)
    raw = page_text.encode("utf-8")
    start = raw.find(start_needle.encode("utf-8"), line_start, line_end)
    if start < 0:
        raise SpecError(
            f"segment start {start_needle!r} missing on line {line_number}"
        )
    end = raw.find(
        end_needle.encode("utf-8"),
        start + len(start_needle.encode("utf-8")),
        line_end,
    )
    if end < 0:
        raise SpecError(
            f"segment end {end_needle!r} missing on line {line_number}"
        )
    return start, end


def resolve_range(
    page_text: str,
    start_line: int,
    start_needle: str,
    end_line: int,
    end_needle: str,
) -> tuple[int, int]:
    start, _ = resolve_needle(page_text, start_line, start_needle)
    _, end = resolve_needle(page_text, end_line, end_needle)
    if start >= end:
        raise SpecError(
            f"range {start_line}:{start_needle!r} through "
            f"{end_line}:{end_needle!r} is inverted"
        )
    return start, end


def resolve(page_text: str, selector: Sequence[Any]) -> tuple[int, int]:
    if selector[0] == "segment":
        return resolve_segment(
            page_text, selector[1], selector[2], selector[3]
        )
    if selector[0] == "range":
        return resolve_range(
            page_text,
            selector[1],
            selector[2],
            selector[3],
            selector[4],
        )
    return _base_resolve(page_text, selector)


def sel_segment(
    number: int, start_needle: str, end_needle: str
) -> tuple[Any, ...]:
    return ("segment", number, start_needle, end_needle)


def sel_range(
    start_line: int,
    start_needle: str,
    end_line: int,
    end_needle: str,
) -> tuple[Any, ...]:
    return ("range", start_line, start_needle, end_line, end_needle)


PAGE_NOTES: dict[int, str] = {
    1: "Cover and children section reviewed; schooling and family-composition fields are outside R_Q.",
    2: "Children and transportation screens reviewed; get-to-work wording is not employment hierarchy evidence.",
    3: "Vehicle screen reviewed; the car-repeat instruction and self-repair prose are outside R_Q.",
    4: "Housing tenure, utilities, mortgage, and farm-home value screens reviewed; no R_Q occurrence retained.",
    5: "Rent and work-for-housing screen reviewed; housing barter wording is outside R_Q.",
    6: "Housing repair, neighborhood, and mobility screens reviewed; worklike repair prose is outside R_Q.",
    7: "Head employment assignment, occupation, employee/self status, tenure, prior-job context, and relative-pay context retained; the four raster-only inactive D1 labels are not replaced by prompt text or the distinct OTHER route, and job-quality prose is excluded.",
    8: "Actual vacation, sick-family missed work, unemployment, weeks, hours, overtime, and wage fields retained; response labels absent from the pinned page text are not replaced with downstream question prose.",
    9: "Actual extra-job work, pay, weeks, and hours retained; the visually present D24 YES label is absent from the pinned page text, and counterfactual labor-supply prose is excluded.",
    10: "Commuting time, mode, and cost screen reviewed and excluded.",
    11: "Attendance, contemplated-job, expected-pay, mobility, and job-attitude prose reviewed and excluded as prospective or nonrealized work context.",
    12: "Prospective target-job and expected-pay prose excluded; previous-job history, actual weeks and hours, sick-week, and unemployment exposure retained.",
    13: "Former-worker commuting-cost screen reviewed; no R_Q occurrence retained.",
    14: "Attendance, mobility, available-job, reservation-wage, and job-attitude prose reviewed and excluded as prospective or nonrealized work context.",
    15: "Inactive-head actual work, occupation, weeks, and hours retained; prospective target-job, available-job, search, and training fields excluded.",
    16: "Future-work intentions excluded; the G2-G7 wife-occupation cross-reference and wife's actual work, occupation, weeks, and hours retained; unlocatable G1/G2 response labels are not replaced with question prose, and commute fields are excluded.",
    17: "Fertility and housework screens reviewed; work-around-the-house prose is outside R_Q.",
    18: "Housework, child-care help, paid household help, and food screens reviewed and excluded.",
    19: "Food, smoking, work-meal, and consumption screens reviewed; work wording is outside R_Q.",
    20: "Food-production and food-assistance screens reviewed; no R_Q occurrence retained.",
    21: "Income section farm assignment, farm, business, and head wage-total fields retained.",
    22: "Head bonus/overtime/commission, professional/trade, farming/market-gardening, and roomer/boarder income fields retained; the mixed H11b line is split by printed source phrase and nonwork income is excluded.",
    23: "Welfare fields excluded; wife's role-total, source, and amount fields retained.",
    24: "Other-family-member income grid reviewed; outside the two-role R_Q domain.",
    25: "Other-family-member continuation grid reviewed; outside the two-role R_Q domain.",
    26: "Settlement, family-total comparison, expenses, and outlook fields reviewed and excluded.",
    27: "Support and savings screen reviewed; no R_Q occurrence retained.",
    28: "Insurance and health-limitation screen reviewed; worklike health prose is outside R_Q.",
    29: "Other-family-member health and care screen reviewed; work wording is outside R_Q.",
    30: "Time use, courses, union dues, and future-planning screen reviewed and excluded.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_D = ("p7_sec_d",)
D_SCOPE = SEC_D
D_WORKING = D_SCOPE + ("p7_d1_working",)
D_LOOKING = D_SCOPE + ("p7_d1_looking",)
D_OTHER = D_SCOPE + ("p7_d1_other",)
D_OTHER_JOB = D_OTHER + ("p7_other_has_job",)
D_ACTIVE = (D_WORKING, D_OTHER_JOB)
D_SOMEONE_ELSE = extend_routes(D_ACTIVE, "p7_d4_someone_else")
D_BOTH = extend_routes(D_ACTIVE, "p7_d4_both")
D_SELF = extend_routes(D_ACTIVE, "p7_d4_self")
D_TENURE = (*D_SOMEONE_ELSE, *D_BOTH, *D_SELF)
D_SHORT = extend_routes(D_TENURE, "p7_d5_short")
D_LONG = extend_routes(D_TENURE, "p7_d5_long")
D_POST = (*D_SHORT, *D_LONG)
D10_YES = extend_routes(D_POST, "p8_d10_yes")
D12_YES = extend_routes(D_POST, "p8_d12_yes")
D14_YES = extend_routes(D_POST, "p8_d14_yes")
D18_YES = extend_routes(D_POST, "p8_d18_yes")
D20_NO = extend_routes(D_POST, "p8_d20_no")

SEC_E = D_LOOKING + ("p12_sec_e",)
E7_NONE = SEC_E + ("p12_e7_none",)

SEC_F = D_OTHER + ("p7_to_f1", "p15_sec_f")

SEC_G = ("p16_sec_g",)

SEC_H = ("p21_sec_h",)
H_FARM = SEC_H + ("p21_h1_farmer",)
H_NOT_FARM = SEC_H + ("p21_h1_not_farmer",)
H5_ROUTES = (H_FARM, H_NOT_FARM)
H_BUSINESS = extend_routes(H5_ROUTES, "p21_h5_yes")
H_UNINCORPORATED = extend_routes(H_BUSINESS, "p21_h6_unincorporated")
H_BOTH = extend_routes(H_BUSINESS, "p21_h6_both")
H_UNKNOWN = extend_routes(H_BUSINESS, "p21_h6_unknown")
H9_YES = SEC_H + ("p22_h9_yes",)
H_WIFE = SEC_H + ("p23_h17_wife_in_du",)
H18_YES = H_WIFE + ("p23_h18_yes",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Pages 1-6 were reviewed in full and contain no retained R_Q atom.

    add(spec(7, sel_line(4), F, "p7_sec_d"))
    add(
        spec(
            7,
            sel_word(6, "HEAD'S"),
            R,
            "p7_role_head_possessive",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            7,
            sel_word(6, "HEAD", 1),
            R,
            "p7_role_head_assignment",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            7,
            sel_word(6, "present job"),
            J,
            "p7_present_job",
            routes=(D_SCOPE,),
        )
    )
    add(
        *question(
            7,
            sel_block(6, 7),
            "p7_d1_assignment",
            parents=("p7_present_job",),
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            7,
            sel_range(9, "1.", 11, "LAID OFF"),
            F,
            "p7_d1_working",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            7,
            sel_word(11, "TO El, PAGE 12"),
            F,
            "p7_d1_looking",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            7,
            sel_word(13, "6.q"),
            F,
            "p7_d1_other",
            routes=(D_SCOPE,),
            note=(
                "Exact pinned Poppler bytes for the rendered D1 OTHER "
                "response label retained."
            ),
        )
    )
    add(
        spec(
            7,
            sel_word(13, "GO TO D2"),
            F,
            "p7_other_has_job",
            routes=(D_OTHER,),
        )
    )
    add(
        spec(
            7,
            sel_word(16, "TO F1, PAGE 15)"),
            F,
            "p7_to_f1",
            routes=(D_OTHER,),
            note=(
                "Exact printed OTHER-without-job Section F route retained "
                "only for its uniquely attributable printed occurrence; it "
                "is not reused for the distinct inactive-label route."
            ),
        )
    )
    add(
        spec(
            7,
            sel_word(18, "main occupation"),
            J,
            "p7_main_occupation",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_line(18),
            "p7_d2_occupation",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_line(21),
            "p7_d3_clarification",
            anchor_kind=None,
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_line(26),
            "p7_d4_employee_self",
            parents=("p7_main_occupation",),
            routes=D_ACTIVE,
        )
    )
    for needle, key, occurrence in (
        ("SOMEONELSE", "p7_d4_someone_else", 0),
        ("BOTH SOMEONELSE AND SELF", "p7_d4_both", 0),
        ("SELF ONLY", "p7_d4_self", 0),
    ):
        add(spec(7, sel_word(27, needle, occurrence), F, key, routes=D_ACTIVE))
    add(spec(7, sel_word(29, "job"), J, "p7_tenure_job", routes=D_TENURE))
    add(
        *question(
            7,
            sel_line(29),
            "p7_d5_tenure",
            parents=("p7_tenure_job",),
            routes=D_TENURE,
        )
    )
    add(spec(7, sel_line(31), F, "p7_d5_long", routes=D_TENURE))
    add(spec(7, sel_line(33), F, "p7_d5_short", routes=D_TENURE))
    add(
        spec(
            7,
            sel_word(35, "job you had"),
            J,
            "p7_previous_job",
            routes=D_SHORT,
        )
    )
    add(
        spec(
            7,
            sel_block(35, 36),
            C,
            "p7_d6_previous_job_end",
            parents=("p7_previous_job",),
            routes=D_SHORT,
            note=(
                "Exact prior-job separation context retained without an "
                "unclassifiable field-purpose prompt."
            ),
        )
    )
    add(
        spec(
            7,
            sel_range(40, "present", 40, "job"),
            J,
            "p7_present_job_comparison",
            routes=D_SHORT,
        )
    )
    add(
        spec(
            7,
            sel_line(40),
            C,
            "p7_d7_pay_comparison",
            parents=("p7_present_job_comparison", "p7_previous_job"),
            routes=D_SHORT,
            note=(
                "Exact relative-pay context retained without treating its "
                "binary comparison as an amount-purpose prompt."
            ),
        )
    )

    # D8-D9 job-quality and free-form reason prose cannot be consumed by the
    # closed field-purpose registry and is outside the retained context set.

    add(*question(8, sel_line(5), "p8_d10_vacation", routes=D_POST))
    add(
        spec(
            8,
            sel_word(6, "l.Yq"),
            F,
            "p8_d10_yes",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D10 "
                "YES response retained after visual verification."
            ),
        )
    )
    add(
        spec(
            8,
            sel_word(7, "15.d"),
            F,
            "p8_d10_no",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D10 NO "
                "response retained after visual verification."
            ),
        )
    )
    add(
        *question(
            8, sel_tail(6, "D11."), "p8_d11_vacation_amount", routes=D10_YES
        )
    )
    add(
        *question(
            8,
            sel_block(10, 11),
            "p8_d12_sick_family_missed_work",
            routes=D_POST,
        )
    )
    add(
        spec(
            8,
            sel_word(12, "~-iYzq"),
            F,
            "p8_d12_yes",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D12 "
                "YES response retained after visual verification."
            ),
        )
    )
    add(
        spec(
            8,
            sel_word(13, "Is.d"),
            F,
            "p8_d12_no",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D12 NO "
                "response retained after visual verification."
            ),
        )
    )
    add(
        *question(
            8,
            sel_range(12, "D13.", 13, "MONTHS"),
            "p8_d13_missed_work_amount",
            routes=D12_YES,
        )
    )
    add(
        *question(8, sel_line(16), "p8_d14_unemployment_strike", routes=D_POST)
    )
    add(
        spec(
            8,
            sel_word(17, "(1.4"),
            F,
            "p8_d14_yes",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D14 "
                "YES response retained after visual verification."
            ),
        )
    )
    add(
        spec(
            8,
            sel_word(19, "15.d"),
            F,
            "p8_d14_no",
            routes=D_POST,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered D14 NO "
                "response retained after visual verification."
            ),
        )
    )
    add(
        *question(
            8,
            sel_range(17, "D15.", 18, "MONTHS"),
            "p8_d15_unemployment_amount",
            routes=D14_YES,
        )
    )
    add(spec(8, sel_word(21, "main job"), J, "p8_main_job", routes=D_POST))
    add(
        *question(
            8,
            sel_line(21),
            "p8_d16_weeks",
            parents=("p8_main_job",),
            routes=D_POST,
        )
    )
    add(
        *question(
            8,
            sel_block(23, 24),
            "p8_d17_hours",
            parents=("p8_main_job",),
            routes=D_POST,
        )
    )
    add(
        *question(
            8,
            sel_line(27),
            "p8_d18_overtime_screen",
            parents=("p8_main_job",),
            routes=D_POST,
        )
    )
    add(spec(8, sel_word(28, "YES"), F, "p8_d18_yes", routes=D_POST))
    add(
        spec(
            8,
            sel_word(28, "NO (GO TO D20)"),
            F,
            "p8_d18_no",
            routes=D_POST,
        )
    )
    add(
        *question(
            8,
            sel_line(30),
            "p8_d19_overtime_hours",
            parents=("p8_main_job",),
            routes=D18_YES,
        )
    )
    add(
        spec(
            8,
            sel_word(35, "15.1"),
            F,
            "p8_d20_no",
            routes=D_POST,
            note=(
                "Exact bbox-verified OCR slice for the rendered D20 NO response "
                "retained; the D20 YES box has no pinned Poppler text."
            ),
        )
    )
    add(
        *question(
            8,
            sel_block(33, 34),
            "p8_d20_overtime_pay_screen",
            parents=("p8_main_job",),
            routes=D_POST,
        )
    )
    add(
        spec(
            8,
            sel_range(39, "D21.", 39, "rate"),
            M,
            "p8_d21_overtime_rate",
            parents=("p8_main_job",),
            routes=D_POST,
            note=(
                "Exact first-line overtime-rate component retained; its "
                "separate purpose atom carries the printed overtime qualifier."
            ),
        )
    )
    add(
        spec(
            8,
            sel_range(40, "(V195)for", 40, "overtime?"),
            P,
            "p8_d21_overtime_rate_prompt",
            routes=D_POST,
            note=(
                "Exact second-line qualifier completes the D21 overtime-rate "
                "purpose without absorbing the side-by-side D22 column."
            ),
        )
    )
    add(
        spec(
            8,
            sel_tail(39, "D22."),
            C,
            "p8_d22_regular_wage_screen",
            parents=("p8_main_job",),
            routes=D20_NO,
            note=(
                "Exact first-line regular-wage screen retained; its separate "
                "purpose atom carries the printed regular-work qualifier."
            ),
        )
    )
    add(
        spec(
            8,
            sel_range(40, "(V196)for", 40, "work?"),
            P,
            "p8_d22_regular_wage_screen_prompt",
            routes=D20_NO,
            note=(
                "Exact second-line qualifier completes the D22 regular-work "
                "purpose without absorbing the side-by-side D21 column."
            ),
        )
    )
    add(
        *question(
            8,
            sel_line(45),
            "p8_d23_regular_wage",
            anchor_kind=M,
            parents=("p8_main_job",),
            routes=D_POST,
        )
    )

    add(
        spec(
            9, sel_word(4, "extra     jobs"), J, "p9_extra_jobs", routes=D_POST
        )
    )
    add(
        *question(
            9,
            sel_block(4, 5),
            "p9_d24_extra_job_screen",
            anchor_kind=None,
            routes=D_POST,
        )
    )
    add(
        spec(
            9,
            sel_word(6, "5. NO(G0 TO D30)"),
            F,
            "p9_d24_no",
            routes=D_POST,
            note=(
                "Exact D24 NO route retained; the rendered D24 YES box has no "
                "pinned Poppler text, so no child identifier is substituted."
            ),
        )
    )
    add(
        *question(
            9,
            sel_line(10),
            "p9_d25_extra_work",
            parents=("p9_extra_jobs",),
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(13),
            "p9_d26_anything_else",
            anchor_kind=None,
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(15),
            "p9_d27_extra_pay",
            anchor_kind=M,
            parents=("p9_extra_jobs",),
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(17),
            "p9_d28_extra_weeks",
            parents=("p9_extra_jobs",),
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(20),
            "p9_d29_extra_hours",
            parents=("p9_extra_jobs",),
            routes=D_POST,
        )
    )

    # Page 10 was reviewed completely; counterfactual hours and commuting
    # fields do not establish a source job/component relationship.

    add(spec(12, sel_block(7, 8), F, "p12_sec_e", routes=(D_LOOKING,)))
    add(
        spec(
            12,
            sel_range(31, "last", 31, "job"),
            J,
            "p12_previous_job",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(31),
            "p12_e6_previous_occupation",
            parents=("p12_previous_job",),
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_block(36, 37),
            C,
            "p12_e6a_previous_job_end",
            parents=("p12_previous_job",),
            routes=(SEC_E,),
            note=(
                "Exact prior-job separation context retained without an "
                "unclassifiable field-purpose prompt."
            ),
        )
    )
    add(
        *question(
            12,
            sel_line(42),
            "p12_e7_weeks",
            parents=("p12_previous_job",),
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_word(42, "0. NONE (GO TO E9)"),
            F,
            "p12_e7_none",
            routes=(SEC_E,),
            note=(
                "Exact zero-weeks routing label retained; the positive numeric "
                "entry has no separate printed branch label in the pinned text."
            ),
        )
    )
    add(
        *question(
            12,
            sel_line(44),
            "p12_e8_hours",
            parents=("p12_previous_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(46),
            "p12_e9_sick_weeks",
            parents=("p12_previous_job",),
            routes=(SEC_E, E7_NONE),
        )
    )
    add(
        *question(
            12,
            sel_line(49),
            "p12_e10_unemployment",
            parents=("p12_previous_job",),
            routes=(SEC_E,),
        )
    )

    # Pages 13-14 were reviewed in full; commute, attendance, mobility,
    # available-job, and job-attitude prose is excluded.

    add(
        spec(
            15,
            sel_block(4, 5),
            F,
            "p15_sec_f",
            routes=(D_OTHER + ("p7_to_f1",),),
            note=(
                "Exact Section F heading retained on the independently "
                "resolving D1 OTHER-without-job path; raster-only inactive "
                "D1 paths are handled by the sealed fail-closed consequence."
            ),
        )
    )
    add(
        spec(
            15,
            sel_word(8, "HEAD"),
            R,
            "p15_role_head",
            routes=(SEC_F,),
        )
    )
    add(
        *question(
            15,
            sel_line(8),
            "p15_f1_worked_for_money",
            routes=(SEC_F,),
        )
    )
    add(
        spec(
            15,
            sel_word(16, "occupation"),
            J,
            "p15_occupation",
            routes=(SEC_F,),
        )
    )
    add(
        *question(
            15,
            sel_line(16),
            "p15_f3_occupation",
            parents=("p15_occupation",),
            routes=(SEC_F,),
        )
    )
    add(
        *question(
            15,
            sel_line(19),
            "p15_f4_weeks",
            parents=("p15_occupation",),
            routes=(SEC_F,),
        )
    )
    add(
        *question(
            15,
            sel_line(21),
            "p15_f5_hours",
            parents=("p15_occupation",),
            routes=(SEC_F,),
        )
    )

    add(spec(16, sel_block(22, 23), F, "p16_sec_g"))
    add(
        spec(
            16,
            sel_word(32, "(TURN TO G14, PAGE 17)"),
            F,
            "p16_g1_nonmarried_exit",
            routes=(SEC_G,),
            note=(
                "Exact collective nonmarried exit retained; its four individual "
                "response boxes and the MARRIED box have no pinned Poppler text."
            ),
        )
    )
    add(
        spec(
            16,
            sel_line(33),
            X,
            "p16_g2_g7_wife_occupation_cross_reference",
            routes=(SEC_G,),
            note=(
                "Exact printed cross-reference binding G2-G7 to the wife's "
                "occupation retained for later global alias resolution; the "
                "visible G1 MARRIED box is absent from pinned page text."
            ),
        )
    )
    add(
        spec(
            16,
            sel_word(33, "WIFE"),
            R,
            "p16_role_wife_cross_reference",
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            16,
            sel_word(33, "OCCUPATION"),
            J,
            "p16_wife_occupation_label",
            routes=(SEC_G,),
        )
    )
    add(spec(16, sel_word(35, "wife"), R, "p16_role_wife", routes=(SEC_G,)))
    add(
        *question(
            16,
            sel_line(35),
            "p16_g2_wife_worked",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            16,
            sel_range(36, "15.", 36, "17)"),
            F,
            "p16_g2_no",
            routes=(SEC_G,),
            note=(
                "Exact bbox-verified OCR slice and route for the rendered G2 NO "
                "response retained; the G2 YES box has no pinned Poppler text."
            ),
        )
    )
    add(spec(16, sel_word(40, "she"), R, "p16_role_she", routes=(SEC_G,)))
    add(
        *question(
            16,
            sel_line(40),
            "p16_g3_wife_occupation",
            parents=("p16_wife_occupation_label",),
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            16,
            sel_line(42),
            "p16_g4_wife_weeks",
            parents=("p16_wife_occupation_label",),
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            16,
            sel_line(44),
            "p16_g5_wife_hours",
            parents=("p16_wife_occupation_label",),
            routes=(SEC_G,),
        )
    )

    # Pages 17-20 were reviewed in full; fertility, housework, paid help,
    # food, work meals, and food-production prose are outside R_Q.

    add(spec(21, sel_line(7), F, "p21_sec_h"))
    add(
        *question(
            21,
            sel_block(15, 17),
            "p21_h1_farm_assignment",
            anchor_kind=FA,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(17, "FARMER,OR RANCHER"),
            F,
            "p21_h1_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(17, "NOT A FARMEROR RANCHER"),
            F,
            "p21_h1_not_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            21,
            sel_block(21, 22),
            "p21_h2_farm_receipts",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_block(23, 24),
            "p21_h3_farm_expenses",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_line(25),
            "p21_h4_farm_net",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_block(28, 29),
            "p21_h5_business_screen",
            anchor_kind=BA,
            routes=H5_ROUTES,
        )
    )
    add(
        spec(
            21,
            sel_word(30, "tT--Ed"),
            F,
            "p21_h5_yes",
            routes=H5_ROUTES,
            note=(
                "Exact bbox-verified OCR slice for the rendered H5 YES response "
                "retained; downstream H6 prose is not used as a branch label."
            ),
        )
    )
    add(
        spec(
            21,
            sel_range(30, "1", 30, "H8)"),
            F,
            "p21_h5_no",
            routes=H5_ROUTES,
            note=(
                "Exact OCR response remnant and printed H5 NO route retained "
                "after bbox verification."
            ),
        )
    )
    add(
        *question(
            21,
            sel_block(34, 35),
            "p21_h6_business_type",
            parents=("p21_h5_business_screen",),
            routes=H_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(36, "CORPORATION(GO TO H8)"),
            F,
            "p21_h6_corporation",
            routes=H_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(37, "UNINCORPORATED"),
            F,
            "p21_h6_unincorporated",
            routes=H_BUSINESS,
        )
    )
    add(
        spec(
            21,
            sel_word(38, "pzEq"),
            F,
            "p21_h6_both",
            routes=H_BUSINESS,
            note=(
                "Exact OCR-corrupted page-text slice for the rendered H6 "
                "BOTH response retained after visual verification."
            ),
        )
    )
    add(
        spec(
            21,
            sel_word(40, "DON'T KNOW"),
            F,
            "p21_h6_unknown",
            routes=H_BUSINESS,
        )
    )
    add(
        *question(
            21,
            sel_block(42, 43),
            "p21_h7_business_income",
            anchor_kind=BA,
            routes=(*H_UNINCORPORATED, *H_BOTH, *H_UNKNOWN),
        )
    )
    add(
        *question(
            21,
            sel_block(49, 51),
            "p21_h8_head_wages",
            anchor_kind=T,
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            22,
            sel_block(6, 7),
            "p22_h9_bonus_overtime_commission",
            anchor_kind=M,
            parents=("p21_h8_head_wages",),
            routes=(SEC_H,),
        )
    )
    add(spec(22, sel_word(8, "YES"), F, "p22_h9_yes", routes=(SEC_H,)))
    add(
        *question(
            22,
            sel_line(12),
            "p22_h10_bonus_amount",
            anchor_kind=None,
            routes=(H9_YES,),
        )
    )
    add(spec(22, sel_word(15, "HEAD"), R, "p22_role_head", routes=(SEC_H,)))
    add(
        *question(
            22, sel_line(15), "p22_h11_other_income_screen", routes=(SEC_H,)
        )
    )
    add(
        spec(
            22,
            sel_range(17, "professional", 17, "trade"),
            J,
            "p22_professional_trade",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_line(17),
            "p22_h11a_professional_trade",
            anchor_kind=M,
            parents=("p22_professional_trade",),
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_block(19, 20),
            "p22_h11b_farming",
            anchor_kind=FA,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_block(17, 20),
            P,
            "p22_h11_shared_amount_prompt",
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            23,
            sel_line(24),
            "p23_h17_head_wife_check",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23, sel_word(24, "HEAD"), R, "p23_role_head_check", routes=(SEC_H,)
        )
    )
    add(
        spec(
            23, sel_word(24, "WIFE"), R, "p23_role_wife_check", routes=(SEC_H,)
        )
    )
    add(
        spec(
            23,
            sel_word(26, "YES, WIFE IN DU"),
            F,
            "p23_h17_wife_in_du",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(30, "wife"),
            R,
            "p23_role_wife_income",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            23,
            sel_line(30),
            "p23_h18_wife_total",
            anchor_kind=T,
            routes=(H_WIFE,),
        )
    )
    add(spec(23, sel_word(31, "YES"), F, "p23_h18_yes", routes=(H_WIFE,)))
    add(
        *question(
            23,
            sel_line(33),
            "p23_h19_wife_sources",
            parents=("p23_h18_wife_total",),
            routes=(H18_YES,),
        )
    )
    add(
        *question(
            23,
            sel_block(37, 38),
            "p23_h19a_wife_amount",
            anchor_kind=None,
            routes=(H18_YES,),
        )
    )

    # Pages 24-30 were reviewed completely. Other-family income, family
    # totals, health, time use, and union-dues prose are outside this sealed
    # two-role source projection.

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

    occurrence_order = {
        row["review_occurrence_id"]: position
        for position, row in enumerate(final_specs)
    }
    repeat_declarations = [
        (
            "p16_g2_g7_wife_occupation_cross_reference",
            ("p16_role_wife", "p16_role_she"),
            "p16_role_wife_cross_reference",
        ),
    ]
    repeat_specs: list[dict[str, Any]] = []
    for repeat_key, alias_keys, canonical_key in repeat_declarations:
        repeat_review_id = review_id_by_key[repeat_key]
        alias_review_ids = [
            review_id_by_key[alias_key] for alias_key in alias_keys
        ]
        canonical_review_id = review_id_by_key[canonical_key]
        repeat_specs.append(
            {
                "review_occurrence_id": repeat_review_id,
                "relation": "explicit_cross_reference",
                "alias_anchor_review_occurrence_ids": alias_review_ids,
                "canonical_anchor_review_occurrence_ids": [
                    canonical_review_id
                ],
                "evidence_review_occurrence_ids": sorted(
                    [
                        repeat_review_id,
                        canonical_review_id,
                        *alias_review_ids,
                    ],
                    key=lambda item: occurrence_order[item],
                ),
                "target_scope": "document_local",
                "resolution_status": (
                    "document_local_source_evidence_complete"
                ),
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
            "whole_page_review": "all_30_pages_including_empty_occurrence_pages",
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
        f"document 6 source review: {len(review['occurrence_specs'])} "
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
