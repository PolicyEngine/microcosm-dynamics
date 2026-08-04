#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 8.

``q71.pdf`` is the 37-page 1971 family questionnaire. Every complete page of
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
import build_rq_stage2_document_008_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 37


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


# q71's early side-by-side layout occasionally places two questions on one
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
    1: "Cover and child-schooling section reviewed; no R_Q occurrence retained.",
    2: "Transportation section reviewed; work-travel prose is outside the R_Q employment hierarchy.",
    3: "Vehicle ownership and repair section reviewed; self-repair prose is not employment evidence.",
    4: "Housing ownership section reviewed; the word farm denotes property rather than employment.",
    5: "Housing rent and work-for-housing section reviewed; imputed housing value is outside R_Q.",
    6: "Housing repair and residential-mobility section reviewed; no R_Q occurrence retained.",
    7: "Head section D assignment, occupation, industry, job identity, and tenure screen retained.",
    8: "Head D10-D23 actual absence, exposure, overtime, and wage fields retained.",
    9: "Head extra-job fields retained; counterfactual labor-supply prose excluded.",
    10: "Commuting and transportation-cost screen reviewed and excluded.",
    11: "Attendance reviewed and excluded; active-worker new-job occupation/pay retained; training, search, mobility, and attitudes excluded.",
    12: "Head section E sought-job, last-job, and actual 1970 exposure fields retained.",
    13: "Last-job commuting screen reviewed and excluded.",
    14: "Attendance, job-availability, mobility, and attitude screen reviewed and excluded.",
    15: "Head section F actual past-work and sought-job/pay fields retained; search and training prose excluded.",
    16: "Section G spouse work attachment, occupation, industry, and exposure fields retained.",
    17: "Spouse future-work, fertility, and housework screen reviewed and excluded.",
    18: "Household work, paid help, and food-expenditure screen reviewed and excluded.",
    19: "Food, smoking, and meals-at-work screen reviewed; work wording is incidental.",
    20: "Home food production and food-stamp screen reviewed; no R_Q occurrence retained.",
    21: "Section H farm, business, head wages, and aggregate earnings fields retained.",
    22: "Head remuneration screen reviewed; only work-derived income components retained.",
    23: "Spouse role-total, income source, and amount screen retained.",
    24: "Other-family-member income/work screen reviewed; outside the two-role R_Q domain.",
    25: "Other-family-member continuation grid reviewed; outside the two-role R_Q domain.",
    26: "Windfall and family-total comparison screen reviewed; no role-specific R_Q occurrence retained.",
    27: "Support and savings screen reviewed; no R_Q occurrence retained.",
    28: "Insurance and health-limitation screen reviewed; hypothetical capacity prose excluded.",
    29: "Other-member health and care screen reviewed; no R_Q occurrence retained.",
    30: "Time use, union dues, and future-plans screen reviewed and excluded.",
    31: "Attitudes screen reviewed; hypothetical job preference is outside R_Q.",
    32: "Attitudes continuation reviewed; no R_Q occurrence retained.",
    33: "New-head section L first-job and lifetime occupation-history fields retained.",
    34: "Sibling and religion background screen reviewed; no R_Q occurrence retained.",
    35: "Migration, education, training, and veteran background screen reviewed and excluded.",
    36: "By-observation screen reviewed; employability prose is not questionnaire employment evidence.",
    37: "Dwelling and neighborhood by-observation screen reviewed; no R_Q occurrence retained.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_D = ("p7_sec_d",)
D_WORKING = SEC_D + ("p7_d1_working",)
D_LOOKING = SEC_D + ("p7_d1_looking",)
D_RETIRED = SEC_D + ("p7_d1_retired",)
D_DISABLED = SEC_D + ("p7_d1_disabled",)
D_HOUSEWIFE = SEC_D + ("p7_d1_housewife",)
D_STUDENT = SEC_D + ("p7_d1_student",)
D_OTHER = SEC_D + ("p7_d1_other",)
D_OTHER_JOB = D_OTHER + ("p7_other_has_job",)
D_OTHER_NO_JOB = D_OTHER + ("p7_other_no_job",)
D_ACTIVE = (D_WORKING, D_OTHER_JOB)
D_SHORT = extend_routes(D_ACTIVE, "p7_d5_short")
D_LONG = extend_routes(D_ACTIVE, "p7_d5_long")
D8_BETTER = extend_routes(D_SHORT, "p7_d8_better")
D8_WORSE = extend_routes(D_SHORT, "p7_d8_worse")
D_POST_TENURE = (*D_SHORT, *D_LONG)
D12_YES = extend_routes(D_POST_TENURE, "p8_d12_yes")
D14_YES = extend_routes(D_POST_TENURE, "p8_d14_yes")
D18_YES = extend_routes(D_POST_TENURE, "p8_d18_yes")
D20_YES = extend_routes(D_POST_TENURE, "p8_d20_yes")
D20_NO = extend_routes(D_POST_TENURE, "p8_d20_no")
D22_YES = extend_routes(D20_NO, "p8_d22_yes")
D_EXTRA = extend_routes(D_POST_TENURE, "p9_d24_yes")
D_NEW_JOB = extend_routes(D_POST_TENURE, "p11_d46_new_job")

SEC_E = D_LOOKING + ("p12_sec_e",)

F_ENTRY = (
    D_RETIRED,
    D_DISABLED,
    D_HOUSEWIFE,
    D_STUDENT,
    D_OTHER_NO_JOB,
)
SEC_F = extend_routes(F_ENTRY, "p15_sec_f")
F_WORKED = extend_routes(SEC_F, "p15_f1_yes")
F_NOT_WORKED = extend_routes(SEC_F, "p15_f1_no")
F2_YES = extend_routes(F_NOT_WORKED, "p15_f2_yes")
F_SOUGHT = extend_routes((*F_WORKED, *F2_YES), "p15_f7_entry")

SEC_G = ("p16_sec_g",)
G_MARRIED = SEC_G + ("p16_g1_married",)
G_WORKED = G_MARRIED + ("p16_g2_yes",)

SEC_H = ("p21_sec_h",)
H_FARM = SEC_H + ("p21_h1_farmer",)
H_BUSINESS = SEC_H + ("p21_h5_yes",)
H_BUSINESS_UNINCORPORATED = H_BUSINESS + ("p21_h6_unincorporated",)
H_BUSINESS_BOTH = H_BUSINESS + ("p21_h6_both",)
H_BUSINESS_UNKNOWN = H_BUSINESS + ("p21_h6_unknown",)
H9_YES = SEC_H + ("p22_h9_yes",)
H_WIFE = SEC_H + ("p23_h17_wife",)
H_WIFE_INCOME = H_WIFE + ("p23_h18_yes",)

SEC_L = ("p33_sec_l",)
L_NEW_HEAD = SEC_L + ("p33_new_head",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Pages 1-6 were reviewed completely and contain no retained R_Q atom.

    add(spec(7, sel_tail(3, "SECTION D:"), F, "p7_sec_d"))
    add(spec(7, sel_word(6, "HEAD'S"), R, "p7_role_head", routes=(SEC_D,)))
    add(
        spec(
            7,
            sel_word(6, "present  job"),
            J,
            "p7_present_job",
            routes=(SEC_D,),
        )
    )
    add(
        *question(
            7,
            sel_block(6, 7),
            "p7_d1_assignment",
            parents=("p7_present_job",),
            routes=(SEC_D,),
        )
    )
    for line_number, needle, key in (
        (9, "1. WORKING NOW, OR", "p7_d1_working"),
        (9, "2. LOOKING FOR WORK", "p7_d1_looking"),
        (9, "3. RETIRED", "p7_d1_retired"),
        (10, "3. PERMANENTLY    DISABLED", "p7_d1_disabled"),
        (11, "4. HOUSEWIFE", "p7_d1_housewife"),
        (12, "5. STUDENT", "p7_d1_student"),
        (13, "6. OTHER", "p7_d1_other"),
    ):
        add(spec(7, sel_word(line_number, needle), F, key, routes=(SEC_D,)))
    add(
        spec(
            7,
            sel_range(13, "GO TO D2 IF HAS", 14, "JOB"),
            F,
            "p7_other_has_job",
            routes=(D_OTHER,),
        )
    )
    add(
        spec(
            7,
            sel_range(14, "OTHERWISE", 16, "PAGE 15)"),
            F,
            "p7_other_no_job",
            routes=(D_OTHER,),
        )
    )
    add(
        *question(
            7,
            sel_line(17),
            "p7_d2_occupation",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_line(23),
            "p7_d3_clarification",
            anchor_kind=None,
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_block(28, 29),
            "p7_d3a_industry",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_block(31, 33),
            "p7_d4_employee_self",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_block(35, 37),
            "p7_d5_tenure",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(spec(7, sel_line(39), F, "p7_d5_short", routes=D_ACTIVE))
    add(
        spec(
            7,
            sel_word(37, "IF   1 YEAR OR MORE"),
            F,
            "p7_d5_long",
            routes=D_ACTIVE,
        )
    )
    for selector, key in (
        (sel_block(41, 42), "p7_d6_previous_job_end"),
        (sel_block(47, 48), "p7_d7_pay_comparison"),
        (sel_block(50, 52), "p7_d8_job_comparison"),
    ):
        add(
            *question(
                7,
                selector,
                key,
                anchor_kind=None,
                routes=D_SHORT,
            )
        )
    add(
        spec(
            7,
            sel_word(52, "1. BETTER"),
            F,
            "p7_d8_better",
            routes=D_SHORT,
        )
    )
    add(
        spec(
            7,
            sel_word(52, "5. WORSE"),
            F,
            "p7_d8_worse",
            routes=D_SHORT,
        )
    )
    add(
        *question(
            7,
            sel_line(58),
            "p7_d9_reason",
            anchor_kind=None,
            routes=(*D8_BETTER, *D8_WORSE),
        )
    )

    for selector, key in (
        (sel_line(4), "p8_d10_vacation"),
        (sel_line(6), "p8_d11_vacation_amount"),
        (sel_block(10, 11), "p8_d12_family_sickness"),
        (sel_tail(13, "D13."), "p8_d13_missed_amount"),
        (sel_line(17), "p8_d14_unemployment_strike"),
        (sel_tail(19, "D15."), "p8_d15_missed_amount"),
    ):
        add(
            *question(
                8,
                selector,
                key,
                parents=("p7_present_job",),
                routes=(
                    D12_YES
                    if key == "p8_d13_missed_amount"
                    else (
                        D14_YES
                        if key == "p8_d15_missed_amount"
                        else D_POST_TENURE
                    )
                ),
            )
        )
    add(
        spec(
            8,
            sel_word(13, "1. YES"),
            F,
            "p8_d12_yes",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(19, "1. YES"),
            F,
            "p8_d14_yes",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(23, "main job"),
            J,
            "p8_main_job",
            routes=D_POST_TENURE,
        )
    )
    for selector, key in (
        (sel_block(23, 24), "p8_d16_weeks"),
        (sel_block(26, 27), "p8_d17_hours"),
        (sel_line(30), "p8_d18_overtime"),
        (sel_block(35, 36), "p8_d19_overtime_hours"),
        (sel_block(39, 40), "p8_d20_extra_hours_paid"),
    ):
        add(
            *question(
                8,
                selector,
                key,
                parents=("p8_main_job",),
                routes=(
                    D18_YES
                    if key == "p8_d19_overtime_hours"
                    else D_POST_TENURE
                ),
            )
        )
    add(
        spec(
            8,
            sel_word(32, "YES"),
            F,
            "p8_d18_yes",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(41, "1. YES"),
            F,
            "p8_d20_yes",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            8,
            sel_word(41, "5. NO"),
            F,
            "p8_d20_no",
            routes=D_POST_TENURE,
        )
    )
    add(
        *question(
            8,
            sel_segment(44, "D21.", "D22."),
            "p8_d21_overtime_rate",
            anchor_kind=M,
            parents=("p8_main_job",),
            routes=D20_YES,
        )
    )
    add(
        *question(
            8,
            sel_tail(44, "D22."),
            "p8_d22_hourly_basis",
            parents=("p8_main_job",),
            routes=D20_NO,
        )
    )
    add(
        spec(
            8,
            sel_word(46, "1. YES"),
            F,
            "p8_d22_yes",
            routes=D20_NO,
        )
    )
    add(
        *question(
            8,
            sel_line(51),
            "p8_d23_hourly_wage",
            anchor_kind=M,
            parents=("p8_main_job",),
            routes=(*D20_YES, *D22_YES),
        )
    )

    add(
        *question(
            9,
            sel_block(4, 5),
            "p9_d24_extra_job_screen",
            anchor_kind=None,
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            9,
            sel_word(4, "extra             jobs"),
            J,
            "p9_extra_jobs",
            routes=D_POST_TENURE,
        )
    )
    add(spec(9, sel_word(7, "1. YES"), F, "p9_d24_yes", routes=D_POST_TENURE))
    add(
        *question(
            9,
            sel_line(12),
            "p9_d25_extra_work",
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )
    add(
        *question(
            9,
            sel_line(17),
            "p9_d26_anything_else",
            anchor_kind=None,
            routes=D_EXTRA,
        )
    )
    add(
        *question(
            9,
            sel_line(19),
            "p9_d27_extra_pay",
            anchor_kind=M,
            parents=("p9_extra_jobs",),
            routes=D_EXTRA,
        )
    )
    for selector, key in (
        (sel_line(21), "p9_d28_extra_weeks"),
        (sel_line(23), "p9_d29_extra_hours"),
    ):
        add(
            *question(
                9,
                selector,
                key,
                parents=("p9_extra_jobs",),
                routes=D_EXTRA,
            )
        )

    # Page 10 commuting is outside the retained domain. Page 11's specific
    # contemplated new-job occupation/pay pair is retained; attendance,
    # training, search effort, mobility, and attitude prose is excluded.
    add(
        spec(
            11,
            sel_word(11, "new job"),
            J,
            "p11_new_job",
            routes=D_POST_TENURE,
        )
    )
    add(
        spec(
            11,
            sel_word(14, "GETTING A NEW JOB"),
            F,
            "p11_d46_new_job",
            routes=D_POST_TENURE,
        )
    )
    add(
        *question(
            11,
            sel_line(18),
            "p11_d47_new_job_occupation",
            parents=("p11_new_job",),
            routes=D_NEW_JOB,
        )
    )
    add(
        *question(
            11,
            sel_line(20),
            "p11_d48_expected_pay",
            anchor_kind=M,
            parents=("p11_new_job",),
            routes=D_NEW_JOB,
        )
    )

    add(
        spec(
            12, sel_tail(2, "SECTION E:"), F, "p12_sec_e", routes=(D_LOOKING,)
        )
    )
    add(spec(12, sel_word(5, "job"), J, "p12_sought_job", routes=(SEC_E,)))
    add(
        *question(
            12,
            sel_line(5),
            "p12_e1_sought_job",
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_line(9),
            "p12_e2_expected_pay",
            anchor_kind=M,
            parents=("p12_sought_job",),
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_word(27, "last        job"),
            J,
            "p12_last_job",
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_block(27, 28),
            "p12_e6_last_occupation",
            parents=("p12_last_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_block(33, 34),
            "p12_e6a_last_industry",
            parents=("p12_last_job",),
            routes=(SEC_E,),
        )
    )
    add(
        *question(
            12,
            sel_block(37, 38),
            "p12_e6b_job_end",
            anchor_kind=None,
            routes=(SEC_E,),
        )
    )
    for selector, key in (
        (sel_line(43), "p12_e7_weeks"),
        (sel_line(46), "p12_e8_hours"),
        (sel_line(49), "p12_e9_sick_weeks"),
        (sel_line(52), "p12_e10_unemployed_weeks"),
    ):
        add(
            *question(
                12,
                selector,
                key,
                parents=("p12_last_job",),
                routes=(SEC_E,),
            )
        )

    # Pages 13-14 were reviewed. Exact page-14 bytes replace two visible
    # mobility questions with literal Text placeholders, so no semantic span
    # is reconstructed from the rendering.

    add(
        spec(
            15,
            sel_tail(3, "SECTION F:"),
            F,
            "p15_sec_f",
            routes=F_ENTRY,
        )
    )
    add(spec(15, sel_word(6, "HEAD"), R, "p15_role_head", routes=SEC_F))
    add(
        *question(
            15,
            sel_block(6, 8),
            "p15_f1_worked_for_money",
            anchor_kind=None,
            routes=SEC_F,
        )
    )
    add(spec(15, sel_word(8, "1. YES"), F, "p15_f1_yes", routes=SEC_F))
    add(spec(15, sel_word(8, "5. NO"), F, "p15_f1_no", routes=SEC_F))
    add(
        spec(
            15,
            sel_word(12, "1. YES"),
            F,
            "p15_f2_yes",
            routes=F_NOT_WORKED,
        )
    )
    add(
        *question(
            15,
            sel_block(16, 17),
            "p15_f3_past_work",
            routes=F_WORKED,
        )
    )
    add(
        *question(
            15,
            sel_block(20, 21),
            "p15_f3a_past_industry",
            routes=F_WORKED,
        )
    )
    add(*question(15, sel_line(23), "p15_f4_weeks", routes=F_WORKED))
    add(*question(15, sel_line(25), "p15_f5_hours", routes=F_WORKED))
    add(
        spec(
            15,
            sel_line(31),
            F,
            "p15_f7_entry",
            routes=(*F_WORKED, *F2_YES),
        )
    )
    add(spec(15, sel_word(33, "job"), J, "p15_sought_job", routes=F_SOUGHT))
    add(
        *question(
            15,
            sel_block(33, 34),
            "p15_f7_sought_job",
            parents=("p15_sought_job",),
            routes=F_SOUGHT,
        )
    )
    add(
        *question(
            15,
            sel_line(36),
            "p15_f8_expected_pay",
            anchor_kind=M,
            parents=("p15_sought_job",),
            routes=F_SOUGHT,
        )
    )

    add(spec(16, sel_tail(16, "SECTION G:"), F, "p16_sec_g"))
    add(
        *question(
            16,
            sel_block(18, 20),
            "p16_g1_marital_status",
            anchor_kind=None,
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            16,
            sel_word(19, "1. MARRIED"),
            F,
            "p16_g1_married",
            routes=(SEC_G,),
        )
    )
    add(
        spec(
            16,
            sel_word(24, "WIFE's"),
            R,
            "p16_role_wifes",
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            16,
            sel_word(26, "wife"),
            R,
            "p16_role_wife",
            routes=(G_MARRIED,),
        )
    )
    add(
        *question(
            16,
            sel_block(26, 27),
            "p16_g2_wife_work",
            anchor_kind=None,
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            16,
            sel_word(27, "1. YES"),
            F,
            "p16_g2_yes",
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            16,
            sel_word(30, "she"),
            R,
            "p16_role_she",
            routes=(G_WORKED,),
        )
    )
    add(*question(16, sel_line(30), "p16_g3_work", routes=(G_WORKED,)))
    add(
        *question(
            16,
            sel_block(34, 35),
            "p16_g3a_industry",
            routes=(G_WORKED,),
        )
    )
    add(*question(16, sel_line(37), "p16_g4_weeks", routes=(G_WORKED,)))
    add(*question(16, sel_line(39), "p16_g5_hours", routes=(G_WORKED,)))

    # Pages 17-20 were reviewed; wife-future, household-work, food, and
    # meals-at-work prose is outside the role/job/remuneration denominator.

    add(spec(21, sel_tail(3, "SECTION H:"), F, "p21_sec_h"))
    add(
        spec(
            21,
            sel_word(13, "1. FARMER, OR RANCHER"),
            F,
            "p21_h1_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(13, "5. NOT A FARMER OR RANCHER"),
            F,
            "p21_h1_not_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            21,
            sel_word(24, "net     income         from    farming"),
            FA,
            "p21_farm_aggregate",
            routes=(H_FARM,),
        )
    )
    for selector, key in (
        (sel_block(18, 19), "p21_h2_farm_receipts"),
        (sel_block(21, 22), "p21_h3_farm_expenses"),
    ):
        add(
            *question(
                21,
                selector,
                key,
                anchor_kind=M,
                parents=("p21_farm_aggregate",),
                routes=(H_FARM,),
            )
        )
    add(
        *question(
            21,
            sel_line(24),
            "p21_h4_farm_net",
            anchor_kind=None,
            routes=(H_FARM,),
        )
    )
    add(
        *question(
            21,
            sel_block(28, 31),
            "p21_h5_business_screen",
            anchor_kind=C,
            routes=(SEC_H,),
        )
    )
    add(spec(21, sel_word(31, "1. YES"), F, "p21_h5_yes", routes=(SEC_H,)))
    add(
        spec(
            21,
            sel_segment(34, "unincorporated", ",        or"),
            BA,
            "p21_business_aggregate",
            routes=(H_BUSINESS,),
        )
    )
    add(
        *question(
            21,
            sel_block(34, 41),
            "p21_h6_business_type",
            parents=("p21_business_aggregate",),
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            21,
            sel_word(39, "2.          UNINCORPORATED"),
            F,
            "p21_h6_unincorporated",
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            21,
            sel_word(40, "3. BOTH"),
            F,
            "p21_h6_both",
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            21,
            sel_word(41, "8.          DON'T KNOW]"),
            F,
            "p21_h6_unknown",
            routes=(H_BUSINESS,),
        )
    )
    add(
        *question(
            21,
            sel_block(43, 47),
            "p21_h7_business_income",
            anchor_kind=M,
            parents=("p21_business_aggregate",),
            routes=(
                H_BUSINESS_UNINCORPORATED,
                H_BUSINESS_BOTH,
                H_BUSINESS_UNKNOWN,
            ),
        )
    )
    add(
        spec(
            21,
            sel_word(50, "HEAD"),
            R,
            "p21_role_head",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            21,
            sel_block(50, 52),
            "p21_h8_head_wages",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            22,
            sel_block(3, 6),
            "p22_h9_bonus_overtime_commission",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(spec(22, sel_word(6, "YES"), F, "p22_h9_yes", routes=(SEC_H,)))
    add(
        *question(
            22,
            sel_line(11),
            "p22_h10_bonus_amount",
            anchor_kind=None,
            routes=(H9_YES,),
        )
    )
    add(
        spec(
            22,
            sel_word(14, "HEAD"),
            R,
            "p22_role_head",
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_line(14),
            "p22_h11_other_income_screen",
            anchor_kind=C,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_word(
                16, "professional                practice       or trade?"
            ),
            "p22_h11a_professional_trade",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_word(18, "farming   or market gardening,"),
            "p22_h11b_farming",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            22,
            sel_word(20, "roomers or boarders?"),
            "p22_h11b_roomers",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            22,
            sel_block(16, 21),
            P,
            "p22_h11_shared_amount_prompt",
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            23,
            sel_block(22, 24),
            "p23_h17_wife_screen",
            anchor_kind=None,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(22, "HEAD"),
            R,
            "p23_role_head",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(22, "WIFE"),
            R,
            "p23_role_wife",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(24, "YES, WIFE IN DU"),
            F,
            "p23_h17_wife",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(24, "NO WIFE IN DU"),
            F,
            "p23_h17_no_wife",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            23,
            sel_word(29, "wife"),
            R,
            "p23_role_wife_income",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            23,
            sel_block(29, 31),
            "p23_h18_wife_total",
            anchor_kind=T,
            routes=(H_WIFE,),
        )
    )
    add(
        spec(
            23,
            sel_word(31, "YES"),
            F,
            "p23_h18_yes",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            23,
            sel_block(34, 37),
            "p23_h19_wife_source",
            anchor_kind=C,
            parents=("p23_h18_wife_total",),
            routes=(H_WIFE_INCOME,),
        )
    )
    add(
        *question(
            23,
            sel_block(40, 42),
            "p23_h19a_wife_amount",
            anchor_kind=M,
            parents=("p23_h18_wife_total",),
            routes=(H_WIFE_INCOME,),
        )
    )

    # Pages 24-32 were reviewed in full. Additional-member grids, family-total
    # comparisons, health, time use, union, and attitudes do not enter the
    # exact two-role employment hierarchy.

    add(spec(33, sel_tail(2, "SECTION L:"), F, "p33_sec_l"))
    add(
        spec(
            33,
            sel_tail(6, "5.     THIS FU HAS THE SAME"),
            F,
            "p33_same_head",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            33,
            sel_line(8),
            F,
            "p33_new_head",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            33,
            sel_word(8, "HEAD"),
            R,
            "p33_role_head",
            routes=(L_NEW_HEAD,),
        )
    )
    add(
        spec(
            33,
            sel_word(27, "first     full        time regular     job"),
            J,
            "p33_first_job",
            routes=(L_NEW_HEAD,),
        )
    )
    add(
        *question(
            33,
            sel_block(27, 29),
            "p33_l4_first_job",
            parents=("p33_first_job",),
            routes=(L_NEW_HEAD,),
        )
    )
    add(
        *question(
            33,
            sel_block(32, 33),
            "p33_l5_job_kinds",
            routes=(L_NEW_HEAD,),
        )
    )

    # Pages 34-37 were reviewed completely and contain no retained R_Q atom.
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
            "whole_page_review": "all_37_pages_including_empty_occurrence_pages",
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
        f"document 8 source review: {len(review['occurrence_specs'])} "
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
