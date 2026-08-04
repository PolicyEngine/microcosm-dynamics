#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 2.

The authenticated 32-page 1968 family questionnaire was read page by page
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
import build_rq_stage2_document_002_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 32


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
    1: "Head interview attachment retained; housing tenure and property prose is outside R_Q.",
    2: "Rent and housing-value screen reviewed; work-for-housing wording is outside R_Q.",
    3: "Housing repairs reviewed; self-performed repair prose is not employment evidence.",
    4: "Family listing reviewed; incidental working and schooling descriptors are outside R_Q.",
    5: "Family, schooling, and vehicle screen reviewed; no R_Q occurrence retained.",
    6: "Vehicle ownership and repair screen reviewed; no R_Q occurrence retained.",
    7: "Vehicle repair and insurance screen reviewed; self-repair prose is outside R_Q.",
    8: "Savings, food, and clothing screen reviewed; no R_Q occurrence retained.",
    9: "Food and clothing savings screen reviewed; no R_Q occurrence retained.",
    10: "Head section F assignment, occupation, employee/self status, tenure, and job-history fields retained.",
    11: "Mobility, training, search, and attitude prose excluded; contemplated-job occupation and amount retained.",
    12: "Health and attendance prose reviewed and excluded; long unemployment and actual missed-work fields retained.",
    13: "Actual vacation, weeks, hours, overtime, extra-job, and extra-pay fields retained.",
    14: "Counterfactual labor-supply prose excluded; unemployed section G occupation and exposure fields retained.",
    15: "Unemployed employer-history fields retained; mobility, search, and attitude prose excluded.",
    16: "Health and attendance prose excluded; long-unemployment history retained.",
    17: "Inactive-head section H actual work, occupation, weeks, and hours retained; prospective and health prose excluded.",
    18: "Marital flow and wife's actual work, occupation, weeks, and hours retained; child-care prose excluded.",
    19: "Wife education, marriage, and fertility screen reviewed; no R_Q occurrence retained.",
    20: "Income section farm, business, head wage-total, and bonus fields retained.",
    21: "Head professional/farm work income and wife's role-total/source/amount fields retained; roomer and nonwork income excluded.",
    22: "Other-family-member income and repeat instruction reviewed; outside the two-role R_Q domain.",
    23: "Other-family-member continuation grid reviewed; outside the two-role R_Q domain.",
    24: "Settlement, in-kind pay, family totals, and comparison fields reviewed and excluded.",
    25: "Family financial outlook and support screen reviewed; no R_Q occurrence retained.",
    26: "Time-use and leisure screen reviewed; no R_Q occurrence retained.",
    27: "Help, support, and union-dues screen reviewed; no R_Q occurrence retained.",
    28: "Attitudes and hypothetical job-preference screen reviewed and excluded.",
    29: "Attitudes continuation reviewed; no R_Q occurrence retained.",
    30: "Background, education, training, and veteran screen reviewed and excluded.",
    31: "Interviewer observation screen reviewed; employability prose is not questionnaire employment evidence.",
    32: "Dwelling and questionnaire-structure page reviewed; no R_Q occurrence retained.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_F = ("p10_sec_f",)
F_WORKING = SEC_F + ("p10_f1_working",)
F_UNEMPLOYED = SEC_F + ("p10_f1_unemployed",)
F_INACTIVE = SEC_F + ("p10_f1_inactive",)
F_OTHER = SEC_F + ("p10_f1_other",)
F_OTHER_JOB = F_OTHER + ("p10_other_has_job",)
F_OTHER_NO_JOB = F_OTHER + ("p10_other_no_job",)
F_ACTIVE = (F_WORKING, F_OTHER_JOB)
F_SOMEONE_ELSE = extend_routes(F_ACTIVE, "p10_f4_someone_else")
F_BOTH = extend_routes(F_ACTIVE, "p10_f4_both")
F_SELF = extend_routes(F_ACTIVE, "p10_f4_self")
F_EMPLOYER = (*F_SOMEONE_ELSE, *F_BOTH)
F_SHORT = extend_routes(F_EMPLOYER, "p10_f6_short")
F_LONG = extend_routes(F_EMPLOYER, "p10_f6_long")
F_POST = (*F_SHORT, *F_LONG, *F_SELF)
F14_TRY = extend_routes(F_POST, "p11_f14_try_new_job")
F31_YES = extend_routes(F_POST, "p12_f31_yes")
F37_YES = extend_routes(F_POST, "p13_f37_yes")
F37_NO = extend_routes(F_POST, "p13_f37_no")
F39_YES = extend_routes(F37_YES, "p13_f39_yes")
F42_YES = extend_routes(F_POST, "p13_f42_yes")

SEC_G = F_UNEMPLOYED + ("p14_sec_g",)
G2_YES = SEC_G + ("p14_g2_yes",)
G2_NO = SEC_G + ("p14_g2_no",)
G_ALL = (G2_YES, G2_NO)
G25_YES = extend_routes(G_ALL, "p16_g25_yes")

H_ENTRY = (F_INACTIVE, F_OTHER_NO_JOB)
SEC_H = extend_routes(H_ENTRY, "p17_sec_h")
H1_YES = extend_routes(SEC_H, "p17_h1_yes")

SEC_I = ("p18_sec_i",)
I_MARRIED = SEC_I + ("p18_i1_married",)
I9_YES = I_MARRIED + ("p18_i9_yes",)

SEC_J = ("p20_sec_j",)
J_FARM = SEC_J + ("p20_j1_farmer",)
J_NOT_FARM = SEC_J + ("p20_j1_not_farmer",)
J5_ROUTES = (J_FARM, J_NOT_FARM)
J_BUSINESS = extend_routes(J5_ROUTES, "p20_j5_yes")
J_BUSINESS_UNINCORPORATED = extend_routes(J_BUSINESS, "p20_j6_unincorporated")
J_BUSINESS_BOTH = extend_routes(J_BUSINESS, "p20_j6_both")
J_BUSINESS_UNKNOWN = extend_routes(J_BUSINESS, "p20_j6_unknown")
J9_YES = SEC_J + ("p20_j9_yes",)
J_HEAD_WIFE = SEC_J + ("p21_j12_head_wife",)
J13_YES = J_HEAD_WIFE + ("p21_j13_yes",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    add(spec(1, sel_word(16, "head"), R, "p1_role_head"))
    add(
        *question(
            1,
            sel_line(16),
            "p1_a1_head_attachment",
            anchor_kind=None,
        )
    )

    # Pages 2-9 were reviewed in full and contain no retained R_Q atom.

    add(spec(10, sel_line(3), F, "p10_sec_f"))
    add(
        spec(
            10,
            sel_word(7, "present job"),
            J,
            "p10_present_job",
            routes=(SEC_F,),
        )
    )
    add(
        *question(
            10,
            sel_block(7, 8),
            "p10_f1_assignment",
            parents=("p10_present_job",),
            routes=(SEC_F,),
        )
    )
    for needle, key in (
        ("WORKING NOW", "p10_f1_working"),
        ("UNEMPLOYED", "p10_f1_unemployed"),
        ("RETIRED, HOUSEWIFE,", "p10_f1_inactive"),
        ("OTHER", "p10_f1_other"),
    ):
        add(spec(10, sel_word(9, needle), F, key, routes=(SEC_F,)))
    add(
        spec(
            10,
            sel_tail(12, "(GO TO F2 IF HAS JOB,"),
            F,
            "p10_other_has_job",
            routes=(F_OTHER,),
        )
    )
    add(
        spec(
            10,
            sel_word(13, "TURN TO H1 OTHERWISE"),
            F,
            "p10_other_no_job",
            routes=(F_OTHER,),
        )
    )
    add(
        spec(
            10,
            sel_word(17, "main occupation"),
            J,
            "p10_main_occupation",
            routes=F_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_line(17),
            "p10_f2_occupation",
            parents=("p10_present_job",),
            routes=F_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_block(21, 22),
            "p10_f3_clarification",
            anchor_kind=None,
            routes=F_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_line(25),
            "p10_f4_employee_self",
            parents=("p10_main_occupation",),
            routes=F_ACTIVE,
        )
    )
    for needle, key in (
        ("SOMEONEELSE", "p10_f4_someone_else"),
        ("BOTH SOMEONEELSE AND SELF", "p10_f4_both"),
        ("SELF ONLY", "p10_f4_self"),
    ):
        add(spec(10, sel_word(26, needle), F, key, routes=F_ACTIVE))
    add(
        spec(
            10,
            sel_word(33, "present       employer"),
            J,
            "p10_present_employer",
            routes=F_EMPLOYER,
        )
    )
    add(
        *question(
            10,
            sel_line(33),
            "p10_f6_tenure",
            parents=("p10_present_employer",),
            routes=F_EMPLOYER,
        )
    )
    add(
        spec(
            10,
            sel_word(34, "(IF 10 YEARS OR MORE"),
            F,
            "p10_f6_long",
            routes=F_EMPLOYER,
        )
    )
    add(
        spec(
            10,
            sel_word(36, "(IF LESS THAN 10 YEARS)"),
            F,
            "p10_f6_short",
            routes=F_EMPLOYER,
        )
    )
    add(
        spec(
            10,
            sel_word(38, "job you had before"),
            J,
            "p10_previous_job",
            routes=F_SHORT,
        )
    )
    add(
        *question(
            10,
            sel_block(38, 40),
            "p10_f7_previous_job_end",
            parents=("p10_previous_job",),
            routes=F_SHORT,
        )
    )
    add(
        spec(
            10,
            sel_word(43, "present           job"),
            J,
            "p10_present_job_comparison",
            routes=F_SHORT,
        )
    )
    add(
        *question(
            10,
            sel_line(43),
            "p10_f8_job_comparison",
            parents=("p10_present_job_comparison", "p10_previous_job"),
            routes=F_SHORT,
        )
    )
    add(
        *question(
            10,
            sel_block(47, 48),
            "p10_f9_pay_comparison",
            parents=("p10_present_job_comparison", "p10_previous_job"),
            routes=F_SHORT,
        )
    )
    add(
        *question(
            10,
            sel_block(50, 51),
            "p10_f10_employer_count",
            routes=F_SHORT,
        )
    )

    # The mobility, training, search-effort, and attitude fields on page 11
    # are excluded. The explicit contemplated-job occupation/amount pair is
    # a source job and remuneration field and is retained.
    add(
        spec(
            11,
            sel_word(21, "new job"),
            J,
            "p11_new_job",
            routes=F_POST,
        )
    )
    add(
        *question(
            11,
            sel_block(21, 22),
            "p11_f14_new_job_screen",
            anchor_kind=None,
            routes=F_POST,
        )
    )
    add(
        spec(
            11,
            sel_word(23, "TRY FOR NEWJOB,"),
            F,
            "p11_f14_try_new_job",
            routes=F_POST,
        )
    )
    add(
        *question(
            11,
            sel_line(27),
            "p11_f15_target_occupation",
            parents=("p11_new_job",),
            routes=F14_TRY,
        )
    )
    add(
        *question(
            11,
            sel_line(29),
            "p11_f16_expected_pay",
            anchor_kind=M,
            parents=("p11_new_job",),
            routes=F14_TRY,
        )
    )

    add(
        *question(
            12,
            sel_block(38, 39),
            "p12_f31_unemployment_strike",
            routes=F_POST,
        )
    )
    add(spec(12, sel_word(40, "YES"), F, "p12_f31_yes", routes=F_POST))
    add(
        *question(
            12,
            sel_line(42),
            "p12_f32_last_time",
            routes=F31_YES,
        )
    )
    add(
        *question(
            12,
            sel_block(45, 47),
            "p12_f33_unemployed_days",
            routes=F_POST,
        )
    )
    add(
        spec(
            12,
            sel_word(50, "main job"),
            J,
            "p12_main_job",
            routes=F_POST,
        )
    )
    add(
        *question(
            12,
            sel_block(50, 53),
            "p12_f34_missed_main_job",
            parents=("p12_main_job",),
            routes=F_POST,
        )
    )

    add(*question(13, sel_line(5), "p13_f35_vacation", routes=F_POST))
    add(
        spec(
            13,
            sel_word(7, "main job"),
            J,
            "p13_main_job",
            routes=F_POST,
        )
    )
    add(
        *question(
            13,
            sel_line(7),
            "p13_f36_weeks",
            parents=("p13_main_job",),
            routes=F_POST,
        )
    )
    add(
        *question(
            13,
            sel_line(10),
            "p13_f37_standard_week",
            parents=("p13_main_job",),
            routes=F_POST,
        )
    )
    add(spec(13, sel_word(12, "YES"), F, "p13_f37_yes", routes=F_POST))
    add(spec(13, sel_word(12, "No"), F, "p13_f37_no", routes=F_POST))
    add(
        *question(
            13,
            sel_segment(14, "F38.", "F41."),
            "p13_f38_standard_hours",
            parents=("p13_main_job",),
            routes=F37_YES,
        )
    )
    add(
        *question(
            13,
            sel_range(18, "F39.", 19, "main job?"),
            "p13_f39_overtime",
            parents=("p13_main_job",),
            routes=F37_YES,
        )
    )
    add(spec(13, sel_word(21, "YES"), F, "p13_f39_yes", routes=F37_YES))
    add(
        *question(
            13,
            sel_block(23, 25),
            "p13_f40_overtime_hours",
            parents=("p13_main_job",),
            routes=F39_YES,
        )
    )
    add(
        *question(
            13,
            sel_range(14, "F41.", 16, "last year?"),
            "p13_f41_average_hours",
            parents=("p13_main_job",),
            routes=F37_NO,
        )
    )
    add(
        spec(
            13,
            sel_word(30, "other        jobs"),
            J,
            "p13_other_jobs",
            routes=F_POST,
        )
    )
    add(
        *question(
            13,
            sel_block(30, 31),
            "p13_f42_extra_job_screen",
            anchor_kind=None,
            routes=F_POST,
        )
    )
    add(spec(13, sel_word(32, "YES"), F, "p13_f42_yes", routes=F_POST))
    add(
        *question(
            13,
            sel_line(37),
            "p13_f43_extra_work",
            parents=("p13_other_jobs",),
            routes=F42_YES,
        )
    )
    add(
        *question(
            13,
            sel_line(42),
            "p13_f44_anything_else",
            anchor_kind=None,
            routes=F42_YES,
        )
    )
    add(
        *question(
            13,
            sel_line(45),
            "p13_f45_extra_hours",
            parents=("p13_other_jobs",),
            routes=F42_YES,
        )
    )
    add(
        *question(
            13,
            sel_block(50, 51),
            "p13_f46_extra_pay",
            anchor_kind=M,
            parents=("p13_other_jobs",),
            routes=F42_YES,
        )
    )

    add(
        spec(
            14,
            sel_tail(28, "SECTION G:"),
            F,
            "p14_sec_g",
            routes=(F_UNEMPLOYED,),
        )
    )
    add(
        spec(
            14,
            sel_word(32, "occupation"),
            J,
            "p14_occupation",
            routes=(SEC_G,),
        )
    )
    add(
        *question(
            14,
            sel_line(32),
            "p14_g1_occupation",
            parents=("p14_occupation",),
            routes=(SEC_G,),
        )
    )
    add(*question(14, sel_line(37), "p14_g2_worked", routes=(SEC_G,)))
    add(spec(14, sel_word(39, "YES"), F, "p14_g2_yes", routes=(SEC_G,)))
    add(
        spec(
            14,
            sel_word(39, "NO (TURN TO G5)"),
            F,
            "p14_g2_no",
            routes=(SEC_G,),
        )
    )
    add(*question(14, sel_line(44), "p14_g3_weeks", routes=(G2_YES,)))
    add(*question(14, sel_line(46), "p14_g4_hours", routes=(G2_YES,)))

    add(
        *question(
            15,
            sel_line(5),
            "p15_g5_previous_job_end",
            parents=("p14_occupation",),
            routes=G_ALL,
        )
    )
    add(
        *question(
            15,
            sel_line(10),
            "p15_g6_employer_count",
            routes=G_ALL,
        )
    )

    # G7-G24 were reviewed; mobility, search, health, and attendance prose is
    # outside the retained domain.
    add(
        *question(
            16,
            sel_line(35),
            "p16_g25_unemployment_strike",
            routes=G_ALL,
        )
    )
    add(spec(16, sel_word(37, "YES"), F, "p16_g25_yes", routes=G_ALL))
    add(
        *question(
            16,
            sel_block(40, 41),
            "p16_g26_last_time",
            routes=G25_YES,
        )
    )

    add(
        spec(
            17,
            sel_tail(5, "SECTION H:"),
            F,
            "p17_sec_h",
            routes=H_ENTRY,
        )
    )
    add(
        *question(
            17,
            sel_line(9),
            "p17_h1_worked_for_money",
            routes=SEC_H,
        )
    )
    add(spec(17, sel_word(11, "YES"), F, "p17_h1_yes", routes=SEC_H))
    add(
        spec(
            17,
            sel_word(16, "occupation"),
            J,
            "p17_occupation",
            routes=H1_YES,
        )
    )
    add(
        *question(
            17,
            sel_block(16, 18),
            "p17_h2_occupation",
            parents=("p17_occupation",),
            routes=H1_YES,
        )
    )
    add(
        *question(
            17,
            sel_line(19),
            "p17_h3_weeks",
            parents=("p17_occupation",),
            routes=H1_YES,
        )
    )
    add(
        *question(
            17,
            sel_line(21),
            "p17_h4_hours",
            parents=("p17_occupation",),
            routes=H1_YES,
        )
    )

    add(spec(18, sel_line(4), F, "p18_sec_i"))
    add(
        *question(
            18,
            sel_line(8),
            "p18_i1_marital_status",
            anchor_kind=None,
            routes=(SEC_I,),
        )
    )
    add(
        spec(18, sel_word(10, "MARRIED"), F, "p18_i1_married", routes=(SEC_I,))
    )
    add(
        spec(
            18,
            sel_word(41, "wife"),
            R,
            "p18_role_wife",
            routes=(I_MARRIED,),
        )
    )
    add(
        *question(
            18,
            sel_line(41),
            "p18_i9_wife_worked",
            anchor_kind=None,
            routes=(I_MARRIED,),
        )
    )
    add(spec(18, sel_word(42, "YES"), F, "p18_i9_yes", routes=(I_MARRIED,)))
    add(
        spec(
            18,
            sel_word(45, "she"),
            R,
            "p18_role_she",
            routes=(I9_YES,),
        )
    )
    add(
        *question(
            18,
            sel_line(45),
            "p18_i10_wife_occupation",
            routes=(I9_YES,),
        )
    )
    add(
        *question(
            18,
            sel_line(47),
            "p18_i11_wife_weeks",
            routes=(I9_YES,),
        )
    )
    add(
        *question(
            18,
            sel_line(48),
            "p18_i12_wife_hours",
            routes=(I9_YES,),
        )
    )

    # Page 19 was reviewed completely and contains no retained R_Q atom.

    add(spec(20, sel_line(4), F, "p20_sec_j"))
    add(spec(20, sel_word(12, "FARMER"), F, "p20_j1_farmer", routes=(SEC_J,)))
    add(
        spec(
            20,
            sel_word(12, "NOT A FARMER"),
            F,
            "p20_j1_not_farmer",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            20,
            sel_block(15, 16),
            "p20_j2_farm_receipts",
            anchor_kind=FA,
            routes=(J_FARM,),
        )
    )
    add(
        *question(
            20,
            sel_block(17, 18),
            "p20_j3_farm_expenses",
            anchor_kind=FA,
            routes=(J_FARM,),
        )
    )
    add(
        *question(
            20,
            sel_line(20),
            "p20_j4_farm_net",
            anchor_kind=FA,
            routes=(J_FARM,),
        )
    )
    add(
        *question(
            20,
            sel_block(24, 25),
            "p20_j5_business_screen",
            anchor_kind=BA,
            routes=J5_ROUTES,
        )
    )
    add(spec(20, sel_word(26, "YES"), F, "p20_j5_yes", routes=J5_ROUTES))
    add(
        *question(
            20,
            sel_block(29, 30),
            "p20_j6_business_type",
            parents=("p20_j5_business_screen",),
            routes=J_BUSINESS,
        )
    )
    for line_number, needle, key in (
        (34, "UNINCORPORATED", "p20_j6_unincorporated"),
        (35, "BOTH", "p20_j6_both"),
        (36, "DON'T KNOW", "p20_j6_unknown"),
    ):
        add(
            spec(
                20,
                sel_word(line_number, needle),
                F,
                key,
                routes=J_BUSINESS,
            )
        )
    add(
        *question(
            20,
            sel_block(38, 40),
            "p20_j7_business_income",
            anchor_kind=BA,
            routes=(
                *J_BUSINESS_UNINCORPORATED,
                *J_BUSINESS_BOTH,
                *J_BUSINESS_UNKNOWN,
            ),
        )
    )
    add(
        spec(
            20,
            sel_word(45, "HEAD"),
            R,
            "p20_role_head",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            20,
            sel_block(45, 46),
            "p20_j8_head_wages",
            anchor_kind=T,
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            20,
            sel_line(49),
            "p20_j9_bonus_overtime_commission",
            anchor_kind=M,
            parents=("p20_j8_head_wages",),
            routes=(SEC_J,),
        )
    )
    add(spec(20, sel_word(51, "YES"), F, "p20_j9_yes", routes=(SEC_J,)))
    add(
        *question(
            20,
            sel_line(55),
            "p20_j10_bonus_amount",
            anchor_kind=None,
            routes=(J9_YES,),
        )
    )

    add(
        spec(
            21,
            sel_word(5, "HEAD"),
            R,
            "p21_role_head",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            21,
            sel_line(5),
            "p21_j11_other_income_screen",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(7, "professional            practice      or trade"),
            J,
            "p21_professional_trade",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            21,
            sel_line(7),
            "p21_j11a_professional_trade",
            anchor_kind=M,
            parents=("p21_professional_trade",),
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            21,
            sel_word(9, "farming or market gardening"),
            "p21_j11b_farming",
            anchor_kind=FA,
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_block(11, 15),
            P,
            "p21_j11_shared_amount_prompt",
            routes=(SEC_J,),
        )
    )
    add(
        *question(
            21,
            sel_block(35, 36),
            "p21_j12_head_wife_check",
            anchor_kind=None,
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(38, "HEAD"),
            R,
            "p21_role_head_check",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(38, "WIFE"),
            R,
            "p21_role_wife_check",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(38, "HEAD AND WIFE"),
            F,
            "p21_j12_head_wife",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(38, "SINGLE MAN OR WOMAN"),
            F,
            "p21_j12_single",
            routes=(SEC_J,),
        )
    )
    add(
        spec(
            21,
            sel_word(41, "wife"),
            R,
            "p21_role_wife_income",
            routes=(J_HEAD_WIFE,),
        )
    )
    add(
        *question(
            21,
            sel_line(41),
            "p21_j13_wife_total",
            anchor_kind=T,
            routes=(J_HEAD_WIFE,),
        )
    )
    add(
        spec(
            21,
            sel_word(46, "(IF YES)"),
            F,
            "p21_j13_yes",
            routes=(J_HEAD_WIFE,),
        )
    )
    add(
        *question(
            21,
            sel_range(46, "Was it", 49, "(SOURCE)"),
            "p21_j14_wife_sources",
            parents=("p21_j13_wife_total",),
            routes=(J13_YES,),
        )
    )
    add(
        *question(
            21,
            sel_block(52, 53),
            "p21_j15_wife_amount",
            anchor_kind=None,
            routes=(J13_YES,),
        )
    )

    # Pages 22-32 were reviewed completely. Other-family-member grids,
    # settlements, in-kind family pay, family totals, time use, attitudes,
    # background, and interviewer-observation prose are outside this sealed
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
            "whole_page_review": "all_32_pages_including_empty_occurrence_pages",
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
        f"document 2 source review: {len(review['occurrence_specs'])} "
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
