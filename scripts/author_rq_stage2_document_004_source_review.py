#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 4.

The authenticated 35-page 1969 family questionnaire was read page by page
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
import build_rq_stage2_document_004_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 35


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
    2: "Children, siblings, and family-background screen reviewed; incidental HEAD labels are outside R_Q.",
    3: "Transportation access screen reviewed; get-to-work wording is not employment hierarchy evidence.",
    4: "Vehicle screen reviewed; the car-repeat instruction and self-repair prose are outside R_Q.",
    5: "Housing tenure, utilities, and mortgage screen reviewed; no R_Q occurrence retained.",
    6: "Rent and work-for-housing screen reviewed; housing barter wording is outside R_Q.",
    7: "Housing repair and mobility screen reviewed; worklike repair prose is outside R_Q.",
    8: "Head cross-reference, employment assignment, occupation, employee/self status, tenure, prior-job context, and relative-pay context retained; job-quality prose excluded.",
    9: "Actual vacation, sick-family missed-work, unemployment, weeks, hours, overtime, extra-job, and extra-pay fields retained.",
    10: "Counterfactual labor supply and commuting-cost screen reviewed and excluded.",
    11: "Attendance, mobility, and job-attitude prose excluded; contemplated-job occupation and expected pay retained.",
    12: "Unemployed target job, previous-job history, actual weeks and hours, sick-week, and unemployment exposure retained; search prose excluded.",
    13: "Former-worker commuting-cost screen reviewed; no R_Q occurrence retained.",
    14: "Attendance, mobility, available-job, and job-attitude prose reviewed and excluded.",
    15: "Inactive-head actual work, occupation, weeks, and hours retained; prospective search fields excluded.",
    16: "Prospective future-work screen reviewed and excluded.",
    17: "Marital flow, the explicit G2-G7 wife-occupation cross-reference, and wife's actual work, occupation, weeks, and hours retained; commute and fertility prose excluded.",
    18: "Housework, child-care help, and paid household-help screen reviewed and excluded.",
    19: "Food, smoking, work-meal, and consumption screen reviewed; work wording is outside R_Q.",
    20: "Food-production and food-assistance screen reviewed; no R_Q occurrence retained.",
    21: "Income section farm assignment, farm, business, head wage-total, and bonus fields retained.",
    22: "Head professional/farm income and wife's role-total/source/amount fields retained; nonwork income excluded.",
    23: "Byte-empty extracted page reviewed; no occurrence exists.",
    24: "Other-family-member income grid reviewed; outside the two-role R_Q domain.",
    25: "Other-family-member continuation grid reviewed; outside the two-role R_Q domain.",
    26: "Settlement, family-total comparison, expenses, and outlook fields reviewed and excluded.",
    27: "Support and savings screen reviewed; no R_Q occurrence retained.",
    28: "Insurance and health-limitation screen reviewed; worklike health prose is outside R_Q.",
    29: "Other-family-member health and care screen reviewed; work wording is outside R_Q.",
    30: "Time-use, courses, union dues, and future-planning screen reviewed and excluded.",
    31: "Attitudes and hypothetical job-preference screen reviewed; no R_Q occurrence retained.",
    32: "Attitudes and money-planning screen reviewed; no R_Q occurrence retained.",
    33: "Background, education, and training screen reviewed; no R_Q occurrence retained.",
    34: "Mobility and interviewer-observation screen reviewed; job/disfigurement prose is outside R_Q.",
    35: "Dwelling and neighborhood observation screen reviewed; no R_Q occurrence retained.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_D = ("p8_sec_d",)
D_SCOPE = SEC_D + ("p8_ask_everyone",)
D_WORKING = D_SCOPE + ("p8_d1_working",)
D_LOOKING = D_SCOPE + ("p8_d1_looking",)
D_INACTIVE = D_SCOPE + ("p8_d1_inactive",)
D_OTHER = D_SCOPE + ("p8_d1_other",)
D_OTHER_JOB = D_OTHER + ("p8_other_has_job",)
D_OTHER_NO_JOB = D_OTHER + ("p8_other_no_job",)
D_ACTIVE = (D_WORKING, D_OTHER_JOB)
D_SOMEONE_ELSE = extend_routes(D_ACTIVE, "p8_d4_someone_else")
D_BOTH = extend_routes(D_ACTIVE, "p8_d4_both")
D_SELF = extend_routes(D_ACTIVE, "p8_d4_self")
D_TENURE = (*D_SOMEONE_ELSE, *D_BOTH, *D_SELF)
D_SHORT = extend_routes(D_TENURE, "p8_d5_short")
D_LONG = extend_routes(D_TENURE, "p8_d5_long")
D_POST = (*D_SHORT, *D_LONG)
D10_YES = extend_routes(D_POST, "p9_d10_yes")
D12_YES = extend_routes(D_POST, "p9_d12_yes")
D14_YES = extend_routes(D_POST, "p9_d14_yes")
D18_NO = extend_routes(D_POST, "p9_d18_no")
D20_YES = extend_routes(D_POST, "p9_d20_yes")
D43_NEW = extend_routes(D_POST, "p11_d43_new_job")

SEC_E = D_LOOKING + ("p12_sec_e",)
F_ENTRY = (D_INACTIVE, D_OTHER_NO_JOB)
SEC_F = extend_routes(F_ENTRY, "p15_sec_f")
F1_YES = extend_routes(SEC_F, "p15_f1_yes")

SEC_G = ("p17_sec_g",)
G_MARRIED = SEC_G + ("p17_g1_married",)
G2_YES = G_MARRIED + ("p17_g2_yes",)

SEC_H = ("p21_sec_h",)
H_FARM = SEC_H + ("p21_h1_farmer",)
H_NOT_FARM = SEC_H + ("p21_h1_not_farmer",)
H5_ROUTES = (H_FARM, H_NOT_FARM)
H_BUSINESS = extend_routes(H5_ROUTES, "p21_h5_yes")
H_UNINCORPORATED = extend_routes(H_BUSINESS, "p21_h6_unincorporated")
H_BOTH = extend_routes(H_BUSINESS, "p21_h6_both")
H_UNKNOWN = extend_routes(H_BUSINESS, "p21_h6_unknown")
H9_YES = SEC_H + ("p21_h9_yes",)
H_WIFE = SEC_H + ("p22_h13_wife_in_du",)
H14_YES = H_WIFE + ("p22_h14_yes",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Pages 1-7 were reviewed in full and contain no retained R_Q atom.

    add(spec(8, sel_line(4), F, "p8_sec_d"))
    add(
        spec(
            8,
            sel_word(6, "ASK EVERYONE"),
            F,
            "p8_ask_everyone",
            routes=(SEC_D,),
        )
    )
    add(
        spec(
            8,
            sel_word(6, "THESE QUESTIONS REFER TO THE HEAD OF THE FU"),
            X,
            "p8_questions_refer_to_head_cross_reference",
            routes=(D_SCOPE,),
            note=(
                "Exact printed cross-reference binding the D questions to "
                "the head of the family unit retained for global alias "
                "resolution."
            ),
        )
    )
    add(
        spec(
            8,
            sel_word(6, "HEAD"),
            R,
            "p8_role_head",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            8,
            sel_word(8, "HEAD'S"),
            R,
            "p8_role_head_possessive",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            8,
            sel_word(8, "HEAD", 1),
            R,
            "p8_role_head_assignment",
            routes=(D_SCOPE,),
        )
    )
    add(
        spec(
            8,
            sel_word(8, "present               job"),
            J,
            "p8_present_job",
            routes=(D_SCOPE,),
        )
    )
    add(
        *question(
            8,
            sel_block(8, 9),
            "p8_d1_assignment",
            parents=("p8_present_job",),
            routes=(D_SCOPE,),
        )
    )
    for line_number, needle, key in (
        (10, "WORKING NOW", "p8_d1_working"),
        (10, "LOOKING FOR WORK", "p8_d1_looking"),
        (10, "RETIRED, PERMANENTLY", "p8_d1_inactive"),
        (18, "OTHER", "p8_d1_other"),
    ):
        add(spec(8, sel_word(line_number, needle), F, key, routes=(D_SCOPE,)))
    add(
        spec(
            8,
            sel_word(18, "GO TO D2 IF HAS JOB"),
            F,
            "p8_other_has_job",
            routes=(D_OTHER,),
        )
    )
    add(
        spec(
            8,
            sel_word(19, "TURN TO Fl"),
            F,
            "p8_other_no_job",
            routes=(D_OTHER,),
        )
    )
    add(
        spec(
            8,
            sel_word(21, "main occupation"),
            J,
            "p8_main_occupation",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            8,
            sel_line(21),
            "p8_d2_occupation",
            parents=("p8_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            8,
            sel_line(26),
            "p8_d3_clarification",
            anchor_kind=None,
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            8,
            sel_line(30),
            "p8_d4_employee_self",
            parents=("p8_main_occupation",),
            routes=D_ACTIVE,
        )
    )
    for needle, key in (
        ("SOMEONEELSE", "p8_d4_someone_else"),
        ("BOTH SOMEONEELSE AND SELF", "p8_d4_both"),
        ("SELF ONLY", "p8_d4_self"),
    ):
        add(spec(8, sel_word(31, needle), F, key, routes=D_ACTIVE))
    add(
        spec(
            8,
            sel_word(33, "this                job"),
            J,
            "p8_tenure_job",
            routes=D_TENURE,
        )
    )
    add(
        *question(
            8,
            sel_line(33),
            "p8_d5_tenure",
            parents=("p8_tenure_job",),
            routes=D_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_line(35),
            F,
            "p8_d5_long",
            routes=D_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_line(38),
            F,
            "p8_d5_short",
            routes=D_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(40, "job you had before"),
            J,
            "p8_previous_job",
            routes=D_SHORT,
        )
    )
    add(
        spec(
            8,
            sel_block(40, 41),
            C,
            "p8_d6_previous_job_end",
            parents=("p8_previous_job",),
            routes=D_SHORT,
            note=(
                "Exact prior-job separation context retained without an "
                "unclassifiable field-purpose prompt."
            ),
        )
    )
    add(
        spec(
            8,
            sel_word(46, "present      job"),
            J,
            "p8_present_job_comparison",
            routes=D_SHORT,
        )
    )
    add(
        spec(
            8,
            sel_line(46),
            C,
            "p8_d7_pay_comparison",
            parents=("p8_present_job_comparison", "p8_previous_job"),
            routes=D_SHORT,
            note=(
                "Exact relative-pay context retained without treating its "
                "binary comparison as an amount-purpose prompt."
            ),
        )
    )

    # D8-D9 job-quality and free-form reason prose cannot be consumed by the
    # closed field-purpose registry and is outside the retained context set.

    add(*question(9, sel_line(3), "p9_d10_vacation", routes=D_POST))
    add(spec(9, sel_word(4, "YES"), F, "p9_d10_yes", routes=D_POST))
    add(
        *question(
            9,
            sel_range(4, "Dll.", 5, "MONTHS"),
            "p9_d11_vacation_amount",
            routes=D10_YES,
        )
    )
    add(
        *question(
            9,
            sel_block(8, 9),
            "p9_d12_sick_family_missed_work",
            routes=D_POST,
        )
    )
    add(spec(9, sel_word(10, "YES"), F, "p9_d12_yes", routes=D_POST))
    add(
        *question(
            9,
            sel_range(10, "D13.", 11, "MONTHS"),
            "p9_d13_missed_work_amount",
            routes=D12_YES,
        )
    )
    add(
        *question(
            9,
            sel_line(14),
            "p9_d14_unemployment_strike",
            routes=D_POST,
        )
    )
    add(spec(9, sel_word(16, "YES"), F, "p9_d14_yes", routes=D_POST))
    add(
        *question(
            9,
            sel_range(16, "D15.", 17, "MONTHS"),
            "p9_d15_unemployment_amount",
            routes=D14_YES,
        )
    )
    add(
        spec(
            9,
            sel_word(20, "main job"),
            J,
            "p9_main_job",
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(20),
            "p9_d16_weeks",
            parents=("p9_main_job",),
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(22),
            "p9_d17_hours",
            parents=("p9_main_job",),
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(25),
            "p9_annual_hours_worked",
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_line(26),
            "p9_d18_overtime_screen",
            parents=("p9_main_job",),
            routes=D_POST,
        )
    )
    add(spec(9, sel_word(27, "YES"), F, "p9_d18_yes", routes=D_POST))
    add(spec(9, sel_word(29, "NO"), F, "p9_d18_no", routes=D_POST))
    add(
        *question(
            9,
            sel_tail(29, "D19."),
            "p9_d19_overtime_hours",
            parents=("p9_main_job",),
            routes=D18_NO,
        )
    )
    add(
        spec(
            9,
            sel_word(32, "extra            jobs"),
            J,
            "p9_extra_jobs",
            routes=D_POST,
        )
    )
    add(
        *question(
            9,
            sel_block(32, 33),
            "p9_d20_extra_job_screen",
            anchor_kind=None,
            routes=D_POST,
        )
    )
    add(spec(9, sel_word(35, "YES"), F, "p9_d20_yes", routes=D_POST))
    add(
        *question(
            9,
            sel_line(40),
            "p9_d21_extra_work",
            parents=("p9_extra_jobs",),
            routes=D20_YES,
        )
    )
    add(
        *question(
            9,
            sel_line(44),
            "p9_d22_anything_else",
            anchor_kind=None,
            routes=D20_YES,
        )
    )
    add(
        *question(
            9,
            sel_line(46),
            "p9_d23_extra_pay",
            anchor_kind=M,
            parents=("p9_extra_jobs",),
            routes=D20_YES,
        )
    )
    add(
        *question(
            9,
            sel_line(48),
            "p9_d24_extra_weeks",
            parents=("p9_extra_jobs",),
            routes=D20_YES,
        )
    )
    add(
        *question(
            9,
            sel_line(50),
            "p9_d25_extra_hours",
            parents=("p9_extra_jobs",),
            routes=D20_YES,
        )
    )

    # Page 10 was reviewed completely; counterfactual hours and commuting
    # fields do not establish a source job/component relationship.

    add(
        spec(
            11,
            sel_word(16, "new job"),
            J,
            "p11_new_job",
            routes=D_POST,
        )
    )
    add(
        *question(
            11,
            sel_line(16),
            "p11_d43_new_job_screen",
            anchor_kind=None,
            routes=D_POST,
        )
    )
    add(
        spec(
            11,
            sel_word(18, "THINKING ABOUT GETTING"),
            F,
            "p11_d43_new_job",
            routes=D_POST,
        )
    )
    add(
        *question(
            11,
            sel_line(22),
            "p11_d44_target_occupation",
            parents=("p11_new_job",),
            routes=D43_NEW,
        )
    )
    add(
        *question(
            11,
            sel_line(25),
            "p11_d45_expected_pay",
            anchor_kind=M,
            parents=("p11_new_job",),
            routes=D43_NEW,
        )
    )

    add(
        spec(
            12,
            sel_tail(4, "SECTION E:"),
            F,
            "p12_sec_e",
            routes=(D_LOOKING,),
        )
    )
    add(
        spec(
            12,
            sel_word(7, "job"),
            J,
            "p12_target_job",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(7),
            "p12_e1_target_occupation",
            parents=("p12_target_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(12),
            "p12_e2_expected_pay",
            anchor_kind=M,
            parents=("p12_target_job",),
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_word(30, "job you had before"),
            J,
            "p12_previous_job",
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_block(30, 31),
            C,
            "p12_e6_previous_job_end",
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
            sel_line(36),
            "p12_e7_weeks",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(39),
            "p12_e8_hours",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(42),
            "p12_e9_sick_weeks",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(45),
            "p12_e10_unemployment",
            routes=(SEC_E,),
        )
    )

    # Pages 13-14 were reviewed in full; commute, attendance, mobility,
    # available-job, and job-attitude prose is excluded.

    add(
        spec(
            15,
            sel_tail(5, "SECTION F:"),
            F,
            "p15_sec_f",
            routes=F_ENTRY,
        )
    )
    add(
        *question(
            15,
            sel_line(8),
            "p15_f1_worked_for_money",
            routes=SEC_F,
        )
    )
    add(spec(15, sel_word(10, "YES"), F, "p15_f1_yes", routes=SEC_F))
    add(
        spec(
            15,
            sel_word(14, "occupation"),
            J,
            "p15_occupation",
            routes=F1_YES,
        )
    )
    add(
        *question(
            15,
            sel_line(14),
            "p15_f2_occupation",
            parents=("p15_occupation",),
            routes=F1_YES,
        )
    )
    add(
        *question(
            15,
            sel_range(19, "How many weeks", 22, "year?"),
            "p15_f3_weeks",
            parents=("p15_occupation",),
            routes=F1_YES,
        )
    )
    add(
        *question(
            15,
            sel_range(21, "About", 24, "worked)?"),
            "p15_f4_hours",
            parents=("p15_occupation",),
            routes=F1_YES,
        )
    )

    # Page 16 was reviewed completely; future-work intentions are excluded.

    add(spec(17, sel_line(5), F, "p17_sec_g"))
    add(
        *question(
            17,
            sel_line(10),
            "p17_g1_marital_status",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            17,
            sel_word(12, "MARRIED"),
            F,
            "p17_g1_married",
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            17,
            sel_line(15),
            X,
            "p17_g2_g7_wife_occupation_cross_reference",
            routes=(G_MARRIED,),
            note=(
                "Exact printed cross-reference binding G2-G7 to the wife's "
                "occupation retained for later global alias resolution."
            ),
        )
    )
    add(
        spec(
            17,
            sel_word(15, "WIFE's"),
            R,
            "p17_role_wife_cross_reference",
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            17,
            sel_word(15, "OCCUPATION"),
            J,
            "p17_wife_occupation_label",
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            17,
            sel_word(16, "wife"),
            R,
            "p17_role_wife",
            routes=(G_MARRIED,),
        )
    )
    add(
        *question(
            17,
            sel_line(16),
            "p17_g2_wife_worked",
            anchor_kind=None,
            routes=(G_MARRIED,),
        )
    )
    add(spec(17, sel_word(17, "YES"), F, "p17_g2_yes", routes=(G_MARRIED,)))
    add(
        spec(
            17,
            sel_word(21, "she"),
            R,
            "p17_role_she",
            routes=(G2_YES,),
        )
    )
    add(
        *question(
            17,
            sel_line(21),
            "p17_g3_wife_occupation",
            parents=("p17_wife_occupation_label",),
            routes=(G2_YES,),
        )
    )
    add(
        *question(
            17,
            sel_line(23),
            "p17_g4_wife_weeks",
            parents=("p17_wife_occupation_label",),
            routes=(G2_YES,),
        )
    )
    add(
        *question(
            17,
            sel_line(25),
            "p17_g5_wife_hours",
            parents=("p17_wife_occupation_label",),
            routes=(G2_YES,),
        )
    )

    # Pages 18-20 were reviewed in full; housework, paid help, food,
    # work meals, and food-production prose are outside R_Q.

    add(spec(21, sel_line(3), F, "p21_sec_h"))
    add(
        *question(
            21,
            sel_block(8, 9),
            "p21_h1_farm_assignment",
            anchor_kind=FA,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(9, "FARMER, OR RANCHER"),
            F,
            "p21_h1_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(9, "NOT A FARMER OR RANCHER"),
            F,
            "p21_h1_not_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            21,
            sel_block(14, 16),
            "p21_h2_farm_receipts",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_block(18, 19),
            "p21_h3_farm_expenses",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_line(21),
            "p21_h4_farm_net",
            anchor_kind=FA,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_block(25, 26),
            "p21_h5_business_screen",
            anchor_kind=BA,
            routes=H5_ROUTES,
        )
    )
    add(spec(21, sel_word(27, "YEs"), F, "p21_h5_yes", routes=H5_ROUTES))
    add(
        *question(
            21,
            sel_block(32, 33),
            "p21_h6_business_type",
            parents=("p21_h5_business_screen",),
            routes=H_BUSINESS,
        )
    )
    for line_number, needle, key in (
        (35, "LJNINCORPORATED", "p21_h6_unincorporated"),
        (36, "BOTH", "p21_h6_both"),
        (37, "DON'T KNOW", "p21_h6_unknown"),
    ):
        add(
            spec(
                21,
                sel_word(line_number, needle),
                F,
                key,
                routes=H_BUSINESS,
            )
        )
    add(
        *question(
            21,
            sel_block(39, 40),
            "p21_h7_business_income",
            anchor_kind=BA,
            routes=(*H_UNINCORPORATED, *H_BOTH, *H_UNKNOWN),
        )
    )
    add(
        spec(
            21,
            sel_word(45, "HEAD"),
            R,
            "p21_role_head",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            21,
            sel_block(45, 46),
            "p21_h8_head_wages",
            anchor_kind=T,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            21,
            sel_block(48, 49),
            "p21_h9_bonus_overtime_commission",
            anchor_kind=M,
            parents=("p21_h8_head_wages",),
            routes=(SEC_H,),
        )
    )
    add(spec(21, sel_word(50, "YES"), F, "p21_h9_yes", routes=(SEC_H,)))
    add(
        *question(
            21,
            sel_line(54),
            "p21_h10_bonus_amount",
            anchor_kind=None,
            routes=(H9_YES,),
        )
    )

    add(
        spec(
            22,
            sel_word(4, "HEAD"),
            R,
            "p22_role_head",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_line(4),
            "p22_h11_other_income_screen",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(6, "professional           practice   or trade"),
            J,
            "p22_professional_trade",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_line(6),
            "p22_h11a_professional_trade",
            anchor_kind=M,
            parents=("p22_professional_trade",),
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_word(8, "farming or market gardening"),
            "p22_h11b_farming",
            anchor_kind=FA,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_block(6, 12),
            P,
            "p22_h11_shared_amount_prompt",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_line(40),
            "p22_h13_head_wife_check",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(40, "HEAD"),
            R,
            "p22_role_head_check",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(40, "WIFE"),
            R,
            "p22_role_wife_check",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(41, "YES, WIFE IN DU"),
            F,
            "p22_h13_wife_in_du",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(41, "NO WIFE IN DU"),
            F,
            "p22_h13_no_wife_in_du",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_word(46, "wife"),
            R,
            "p22_role_wife_income",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            22,
            sel_line(46),
            "p22_h14_wife_total",
            anchor_kind=T,
            routes=(H_WIFE,),
        )
    )
    add(spec(22, sel_word(48, "YES"), F, "p22_h14_yes", routes=(H_WIFE,)))
    add(
        *question(
            22,
            sel_line(51),
            "p22_h15_wife_sources",
            parents=("p22_h14_wife_total",),
            routes=(H14_YES,),
        )
    )
    add(
        *question(
            22,
            sel_block(55, 56),
            "p22_h15a_wife_amount",
            anchor_kind=None,
            routes=(H14_YES,),
        )
    )

    # Pages 23-35 were reviewed completely. The byte-empty page, other-family
    # income grids, family totals, health, time use, attitudes, background,
    # mobility, and interviewer-observation prose are outside this sealed
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
            "p8_questions_refer_to_head_cross_reference",
            ("p8_role_head_possessive", "p8_role_head_assignment"),
            "p8_role_head",
        ),
        (
            "p17_g2_g7_wife_occupation_cross_reference",
            ("p17_role_wife", "p17_role_she"),
            "p17_role_wife_cross_reference",
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
            "whole_page_review": "all_35_pages_including_empty_occurrence_pages",
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
        f"document 4 source review: {len(review['occurrence_specs'])} "
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
