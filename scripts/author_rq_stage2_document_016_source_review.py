#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 16.

Every one of the 29 pages in ``q75.pdf`` was reviewed from authenticated
Poppler text and the rendered PDF before these selectors were written. This
module never opens the stage-1 candidate artifact; candidates are joined only
by the sealed annotation builder after this source-byte ledger validates.

The retained domain is limited to the two-role employment, job-history,
work-exposure, remuneration, farm, and business source semantics needed by
section 19. Transportation, housing, food assistance, other-family income,
feelings, education, residential mobility, health, and merely hypothetical
worklike prose were reviewed and excluded. Only explicit printed cross-
references are retained as unresolved repeat evidence; no repeated wording
is promoted to alias evidence, and no global node or relationship ID is
assigned.
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
import build_rq_stage2_document_016_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 29


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


def resolve_range(
    page_text: str,
    first_line: int,
    first_needle: str,
    last_line: int,
    last_needle: str,
) -> tuple[int, int]:
    """Resolve an exact cross-line range without neighboring print columns."""

    start, _ = resolve_needle(page_text, first_line, first_needle)
    _, end = resolve_needle(page_text, last_line, last_needle)
    if start >= end:
        raise SpecError(
            f"range {first_line}:{first_needle!r}-"
            f"{last_line}:{last_needle!r} is inverted"
        )
    return start, end


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
    if mode == "range":
        return resolve_range(
            page_text,
            selector[1],
            selector[2],
            selector[3],
            selector[4],
        )
    raise SpecError(f"unknown selector mode {mode!r}")


def sel_line(number: int) -> tuple[Any, ...]:
    return ("line", number)


def sel_block(first: int, last: int) -> tuple[Any, ...]:
    return ("block", first, last)


def sel_word(number: int, needle: str, occurrence: int = 0) -> tuple[Any, ...]:
    return ("needle", number, needle, occurrence)


def sel_tail(number: int, needle: str, occurrence: int = 0) -> tuple[Any, ...]:
    return ("tail", number, needle, occurrence)


def sel_range(
    first_line: int,
    first_needle: str,
    last_line: int,
    last_needle: str,
) -> tuple[Any, ...]:
    return ("range", first_line, first_needle, last_line, last_needle)


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


def unresolved_repeat(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    routes: Sequence[Sequence[str]] = ((),),
    relation: str = "explicit_cross_reference",
    note: str,
) -> dict[str, Any]:
    row = spec(page, selector, A, key, routes=routes, note=note)
    row.update(
        relation=relation,
        alias=(),
        canonical=(),
        evidence=(),
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    )
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
    1: "Cover and children section reviewed; no retained R_Q occurrence.",
    2: "Transportation screen reviewed; worklike travel prose excluded.",
    3: "Housing satisfaction screen reviewed and excluded.",
    4: "Housing cost and mobility screen reviewed; farm home-value mention excluded.",
    5: "Housing condition screen reviewed and excluded.",
    6: "Neighborhood condition screen reviewed and excluded.",
    7: "Head employment assignment, occupation, industry, employee/self, government, and incorporation fields retained; visually implied housewife/student answer routes are absent from pinned page text and were not reconstructed.",
    8: "Head tenure and prior-job fields retained; supervisory prose excluded.",
    9: "Head vacation, absence, work-exposure, and overtime-hour fields retained; the D25 yes label is absent from pinned page text and D26 remains on the closest common source-visible ancestor.",
    10: "Head overtime-pay eligibility/rates, regular wage, retirement-plan, and extra-job fields retained; byte-missing D38/D41 yes labels not reconstructed.",
    11: "Counterfactual hours, commuting, and future-job preference screen reviewed and excluded.",
    12: "Head sought-job and last-job identity, exposure, and absence fields retained; search and training prose excluded.",
    13: "E15 routing serves excluded commuting fields; commuting, job-worth, and mobility prose reviewed and excluded.",
    14: "Head nonworker actual-work and sought-job/pay fields retained; training/search prose excluded; F1 answer boxes and the F2 yes box are absent from pinned page text and were not reconstructed.",
    15: "Wife role/job attachment, occupation cross-reference, industry, and exposure fields retained; counterfactual and commuting prose excluded.",
    16: "Food and food-stamp spending screen reviewed and excluded.",
    17: "Farm, business, wages, and aggregate income fields retained.",
    18: "Head actual remuneration components retained; transfer and asset-income prose excluded while the source-visible H12 bridge route is retained.",
    19: "H19 public-retirement context/cross-reference and wife income-presence, source, and amount fields retained; welfare and SSI prose is excluded while its source-visible bridge routes are retained.",
    20: "Other-family-member income screen reviewed; outside the two-role R_Q domain.",
    21: "Other-family-member continuation reviewed; outside the two-role R_Q domain.",
    22: "Other-person income and support screen reviewed and excluded.",
    23: "Savings, expectations, and union screen reviewed and excluded.",
    24: "Feelings screen reviewed and excluded.",
    25: "Education screen reviewed; no retained R_Q occurrence.",
    26: "New-wife checkpoint and lifetime work-history fields retained; parental education excluded.",
    27: "New-head first regular job and occupation-history fields retained; family-background prose is excluded while its source-visible bridge routes are retained.",
    28: "Background, mobility, and rejected-job prose reviewed and excluded.",
    29: "Head lifetime work-history fields retained; health-limitation prose is excluded while its printed terminal routes are retained.",
}


def extend_routes(
    routes: Sequence[Sequence[str]], branch_key: str
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(route) + (branch_key,) for route in routes)


SEC_D = ("p7_sec_d",)
D1_WORKING = SEC_D + ("p7_d1_working",)
D1_LOOKING = SEC_D + ("p7_d1_looking",)
D1_RETIRED = SEC_D + ("p7_d1_retired",)
D1_PERMANENTLY = SEC_D + ("p7_d1_permanently",)
D1_OTHER = SEC_D + ("p7_d1_other",)
D1_OTHER_HAS_JOB = D1_OTHER + ("p7_d1_if_has_job",)
D1_OTHERWISE = D1_OTHER + ("p7_d1_otherwise",)
D_ACTIVE = (D1_WORKING, D1_OTHER_HAS_JOB)
D3_NOT_CLEAR = extend_routes(D_ACTIVE, "p7_d3_if_not_clear")
D_SOMEONE = extend_routes(D_ACTIVE, "p7_d5_someone")
D_BOTH = extend_routes(D_ACTIVE, "p7_d5_both")
D_SELF = extend_routes(D_ACTIVE, "p7_d5_self")
D_SHORT = extend_routes(D_ACTIVE, "p8_less_than_year")
D22_BETTER = extend_routes(D_SHORT, "p8_d22_better")
D22_WORSE = extend_routes(D_SHORT, "p8_d22_worse")
D27_YES = extend_routes(D_ACTIVE, "p9_d27_yes")
D29_YES = extend_routes(D_ACTIVE, "p9_d29_yes")
D34_YES = extend_routes(D_ACTIVE, "p9_d34_yes")
D36_YES = extend_routes(D_ACTIVE, "p10_d36_yes")
D36_NO = extend_routes(D_ACTIVE, "p10_d36_no")
D41_NO = extend_routes(D_ACTIVE, "p10_d41_no")
SEC_E = D1_LOOKING + ("p12_sec_e",)
E13_NONE = SEC_E + ("p12_e13_none",)
F_ENTRY = (D1_RETIRED, D1_PERMANENTLY, D1_OTHERWISE)
SEC_F = extend_routes(F_ENTRY, "p14_sec_f")
F2_YES = extend_routes(SEC_F, "p14_f2_yes")
F7_YES = extend_routes(SEC_F, "p14_f7_yes")
SEC_G = ("p15_sec_g",)
G_MARRIED = SEC_G + ("p15_married",)
G_SINGLE = SEC_G + ("p15_single",)
G_WIDOWED = SEC_G + ("p15_widowed",)
G_DIVORCED = SEC_G + ("p15_divorced",)
G_SEPARATED = SEC_G + ("p15_separated",)
G_WORKED = G_MARRIED + ("p15_g2_yes",)
G7_YES = G_WORKED + ("p15_g7_yes",)
SEC_H = ("p17_sec_h",)
H_FARMER = SEC_H + ("p17_farmer",)
H_NOT_FARMER = SEC_H + ("p17_not_farmer",)
H_BUSINESS = SEC_H + ("p17_business_yes",)
H_BUSINESS_UNINCORPORATED = H_BUSINESS + ("p17_h6_unincorporated",)
H_BUSINESS_BOTH = H_BUSINESS + ("p17_h6_both",)
H_BUSINESS_DK = H_BUSINESS + ("p17_h6_dont_know",)
H9_YES = SEC_H + ("p18_h9_yes",)
H_SOCIAL_SECURITY = SEC_H + ("p19_h19_social_security",)
H_WIFE = SEC_H + ("p19_wife_present",)
H_WIFE_INCOME = H_WIFE + ("p19_wife_income_yes",)
SEC_L = ("p26_sec_l",)
L_NEW = SEC_L + ("p26_new_wife",)
L_SAME = SEC_L + ("p26_same_wife",)
L_NO_WIFE = SEC_L + ("p26_no_wife",)
L_FEMALE_HEAD = SEC_L + ("p26_female_head",)
L4_NONE = L_NEW + ("p26_l4_none",)
L5_ALL = L_NEW + ("p26_l5_all",)
SEC_M = ("p27_sec_m",)
M_NEW = SEC_M + ("p27_new_head",)
M_SAME = SEC_M + ("p27_same_head",)
M26_NONE = M_NEW + ("p29_m26_none",)
M27_ALL = M_NEW + ("p29_m27_all",)


def _review_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []

    def add(*items: dict[str, Any]) -> None:
        rows.extend(items)

    # Section D: current head employment. The plain section heading is the
    # source-visible navigational root for this schedule, not a response.
    # Exact D1 labels establish the mutually exclusive downstream schedules.
    add(spec(7, sel_tail(2, "SECTION D:"), F, "p7_sec_d"))
    add(spec(7, sel_word(5, "HEAD"), R, "p7_role_head", routes=(SEC_D,)))
    add(
        spec(
            7,
            sel_word(5, "present  job"),
            J,
            "p7_present_job",
            routes=(SEC_D,),
        )
    )
    add(
        *question(
            7,
            sel_block(5, 6),
            "p7_d1_assignment",
            parents=("p7_present_job",),
            routes=(SEC_D,),
        )
    )
    for line_number, needle, key in (
        (9, "1. WORKING", "p7_d1_working"),
        (9, "2.  LOOKING FOR", "p7_d1_looking"),
        (9, "3. RETIRED", "p7_d1_retired"),
        (11, "3. PERMANENTLY", "p7_d1_permanently"),
        (18, "6. OTHER", "p7_d1_other"),
    ):
        add(spec(7, sel_word(line_number, needle), F, key, routes=(SEC_D,)))
    add(
        spec(
            7,
            sel_word(18, "GO TO D2 IF HAS JOB"),
            F,
            "p7_d1_if_has_job",
            routes=(D1_OTHER,),
        )
    )
    add(
        spec(
            7,
            sel_word(19, "OTHERWISE TURN TO"),
            F,
            "p7_d1_otherwise",
            routes=(D1_OTHER,),
        )
    )
    add(
        *question(
            7,
            sel_line(22),
            "p7_d2_occupation",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            7,
            sel_word(28, "(IF    NOT CLEAR)"),
            F,
            "p7_d3_if_not_clear",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_tail(28, "D3."),
            "p7_d3_occupation_detail",
            anchor_kind=None,
            routes=D3_NOT_CLEAR,
        )
    )
    add(
        *question(
            7,
            sel_line(33),
            "p7_d4_industry",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            7,
            sel_line(37),
            "p7_d5_employee_self",
            parents=("p7_present_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            7,
            sel_word(40, "1.    SOMEONE ELSE"),
            F,
            "p7_d5_someone",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            7,
            sel_word(40, "2.     BOTH SOMEONE ELSE AND SELF"),
            F,
            "p7_d5_both",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            7,
            sel_word(40, "3. SELF ONLY"),
            F,
            "p7_d5_self",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            7,
            sel_word(44, "Federal, State or"),
            C,
            "p7_d6_government",
            parents=("p7_present_job",),
            routes=D_SOMEONE,
            note="Exact federal/state fragment of the column-split D6 government field.",
        )
    )
    add(
        spec(
            7,
            sel_word(43, "Do you work for the"),
            P,
            "p7_d6_government_prompt",
            routes=D_SOMEONE,
            note="Exact locatable purpose fragment of the column-split D6 field.",
        )
    )
    add(
        *question(
            7,
            sel_word(44, "incorporated?", 0),
            "p7_d7_incorporation",
            parents=("p7_present_job",),
            routes=D_BOTH,
        )
    )
    add(
        *question(
            7,
            sel_word(44, "incorporated?", 1),
            "p7_d11_incorporation",
            parents=("p7_present_job",),
            routes=D_SELF,
        )
    )
    add(
        *question(
            7,
            sel_word(56, "State or local  Government?"),
            "p7_d10_government",
            parents=("p7_present_job",),
            routes=D_BOTH,
        )
    )

    add(
        spec(
            8,
            sel_word(22, "this                job"),
            J,
            "p8_current_job",
            routes=D_ACTIVE,
            note="D18 establishes the separately printed current-job node.",
        )
    )
    add(
        *question(
            8,
            sel_line(22),
            "p8_d18_tenure",
            parents=("p8_current_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            8,
            sel_word(24, "(IF   ONE YEAR OR MORE, TURN TO PAGE 9, D24)"),
            F,
            "p8_one_year_or_more",
            routes=D_ACTIVE,
        )
    )
    add(
        spec(
            8,
            sel_word(25, "(IF         LESS THAN ONE YEAR)"),
            F,
            "p8_less_than_year",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            8,
            sel_line(28),
            "p8_d19_start",
            parents=("p8_current_job",),
            routes=D_SHORT,
        )
    )
    add(
        spec(
            8,
            sel_word(30, "job you had before"),
            J,
            "p8_previous_job",
            routes=D_SHORT,
        )
    )
    add(
        *question(
            8,
            sel_block(30, 31),
            "p8_d20_separation",
            parents=("p8_previous_job",),
            routes=D_SHORT,
        )
    )
    add(
        *question(
            8,
            sel_line(33),
            "p8_d21_pay_compare",
            parents=("p8_current_job", "p8_previous_job"),
            routes=D_SHORT,
        )
    )
    add(
        *question(
            8,
            sel_block(37, 38),
            "p8_d22_job_compare",
            parents=("p8_current_job", "p8_previous_job"),
            routes=D_SHORT,
        )
    )
    for needle, key in (
        ("1.    BETTER", "p8_d22_better"),
        ("5. WORSE", "p8_d22_worse"),
        (
            "3.    SAME (TURN                  TO PAGE 9,           D24)",
            "p8_d22_same",
        ),
    ):
        add(spec(8, sel_word(40, needle), F, key, routes=D_SHORT))
    add(
        *question(
            8,
            sel_line(43),
            "p8_d23_compare_reason",
            anchor_kind=None,
            routes=(*D22_BETTER, *D22_WORSE),
        )
    )
    add(*question(9, sel_line(3), "p9_d24_paid_vacation", routes=D_ACTIVE))
    add(*question(9, sel_line(5), "p9_d25_vacation", routes=D_ACTIVE))
    add(
        spec(
            9,
            sel_block(7, 8),
            F,
            "p9_d25_no",
            routes=D_ACTIVE,
            note="Exact locatable D25 no/skip atom; the printed yes label is absent from pinned page text.",
        )
    )
    add(
        *question(
            9,
            sel_line(11),
            "p9_d26_vacation_time",
            routes=D_ACTIVE,
            note="D26 is reached through D25 yes, whose printed label is absent from pinned page text; the closest common source-visible ancestry is retained.",
        )
    )
    add(
        *question(9, sel_block(14, 15), "p9_d27_sick_absence", routes=D_ACTIVE)
    )
    add(spec(9, sel_word(17, "1. YES"), F, "p9_d27_yes", routes=D_ACTIVE))
    add(
        spec(
            9,
            sel_word(17, "5. NO              (GO TO D29)"),
            F,
            "p9_d27_no",
            routes=D_ACTIVE,
        )
    )
    add(*question(9, sel_line(20), "p9_d28_sick_time", routes=D27_YES))
    add(
        *question(
            9,
            sel_line(23),
            "p9_d29_unemployment_strike",
            routes=D_ACTIVE,
        )
    )
    add(spec(9, sel_word(25, "1. YES"), F, "p9_d29_yes", routes=D_ACTIVE))
    add(
        spec(
            9,
            sel_word(25, "5.         NO             (GO TO D32)"),
            F,
            "p9_d29_no",
            routes=D_ACTIVE,
        )
    )
    add(*question(9, sel_line(28), "p9_d30_unemployment_time", routes=D29_YES))
    add(
        *question(
            9,
            sel_block(31, 32),
            "p9_d31_unemployment_periods",
            routes=D29_YES,
        )
    )
    add(
        spec(
            9,
            sel_word(37, "main     job"),
            J,
            "p9_main_job",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            9,
            sel_line(37),
            "p9_d32_weeks",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            9,
            sel_block(40, 41),
            "p9_d33_hours",
            parents=("p9_main_job",),
            routes=D_ACTIVE,
        )
    )
    add(*question(9, sel_line(43), "p9_d34_overtime", routes=D_ACTIVE))
    add(spec(9, sel_word(45, "YES"), F, "p9_d34_yes", routes=D_ACTIVE))
    add(
        spec(
            9,
            sel_tail(45, "[ ] NO"),
            F,
            "p9_d34_no",
            routes=D_ACTIVE,
        )
    )
    add(*question(9, sel_line(47), "p9_d35_overtime_hours", routes=D34_YES))

    add(
        *question(
            10,
            sel_block(3, 4),
            "p10_d36_overtime_pay_eligibility",
            routes=D_ACTIVE,
        )
    )
    add(spec(10, sel_word(6, "1. YES"), F, "p10_d36_yes", routes=D_ACTIVE))
    add(spec(10, sel_word(6, "5. NO"), F, "p10_d36_no", routes=D_ACTIVE))
    add(
        *question(
            10,
            sel_word(10, "rate for that overtime?"),
            "p10_d37_overtime_hourly_rate",
            anchor_kind=M,
            routes=D36_YES,
            note="Exact locatable D37 rate fragment; the parallel columns do not form one atomic multiline slice.",
        )
    )
    add(
        *question(
            10,
            sel_word(9, "Do you have an hourly wage"),
            "p10_d38_hourly_basis",
            routes=D36_NO,
            note="Exact locatable D38 prompt fragment; its printed answer boxes are absent from pinned page text.",
        )
    )
    add(
        *question(
            10,
            sel_line(15),
            "p10_d39_regular_hourly_rate",
            anchor_kind=M,
            routes=(*D36_YES, *D36_NO),
            note="D39 is reached from D36 yes or D38 yes; D38 answer labels are not locatable in pinned page text.",
        )
    )
    add(
        *question(10, sel_line(17), "p10_d40_retirement_plan", routes=D_ACTIVE)
    )
    add(
        spec(
            10,
            sel_word(19, "extra    jobs"),
            J,
            "p10_extra_jobs",
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_block(19, 20),
            "p10_d41_extra_job",
            parents=("p10_extra_jobs",),
            routes=D_ACTIVE,
        )
    )
    add(spec(10, sel_word(22, "5. NO"), F, "p10_d41_no", routes=D_ACTIVE))
    add(
        spec(
            10,
            sel_line(23),
            F,
            "p10_d41_no_exit",
            routes=D41_NO,
            note="Exact multiline D41 no/turn exit retained; the printed yes box is absent from pinned page text.",
        )
    )
    add(
        *question(
            10,
            sel_line(26),
            "p10_d42_extra_occupation",
            parents=("p10_extra_jobs",),
            routes=D_ACTIVE,
            note="D42-D46 follow D41 yes, whose printed label is absent from pinned page text; the closest common source-visible ancestry is retained.",
        )
    )
    add(
        spec(
            10,
            sel_line(31),
            P,
            "p10_d43_additional_extra_job_prompt",
            routes=D_ACTIVE,
            note="D43 prints the prompt for an additional extra-job report.",
        )
    )
    add(
        *question(
            10,
            sel_line(33),
            "p10_d44_extra_hourly",
            anchor_kind=M,
            parents=("p10_extra_jobs",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_line(35),
            "p10_d45_extra_weeks",
            parents=("p10_extra_jobs",),
            routes=D_ACTIVE,
        )
    )
    add(
        *question(
            10,
            sel_block(37, 38),
            "p10_d46_extra_hours",
            parents=("p10_extra_jobs",),
            routes=D_ACTIVE,
        )
    )

    # Sections E and F: sought, last, and actual work.
    add(
        spec(
            12,
            sel_tail(2, "SECTION E:"),
            F,
            "p12_sec_e",
            routes=(D1_LOOKING,),
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
            sel_word(23, "last         job"),
            J,
            "p12_last_job",
            routes=(SEC_E,),
        )
    )
    for selector, key in (
        (sel_line(23), "p12_e6_last_occupation"),
        (sel_line(29), "p12_e7_last_industry"),
        (sel_line(39), "p12_e9_separation"),
        (sel_line(44), "p12_e10_weeks"),
        (sel_line(46), "p12_e11_hours"),
        (sel_line(48), "p12_e12_sick"),
        (sel_line(50), "p12_e13_unemployed"),
        (sel_block(53, 54), "p12_e14_periods"),
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
    add(
        spec(
            12,
            sel_word(44, "00. NONE                   (GO TO E12)"),
            F,
            "p12_e10_none",
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_word(50, "00. NONE"),
            F,
            "p12_e13_none",
            routes=(SEC_E,),
        )
    )
    add(
        spec(
            12,
            sel_tail(52, "PAGE 13"),
            F,
            "p12_e13_none_exit",
            routes=(E13_NONE,),
        )
    )

    add(spec(14, sel_tail(4, "SECTION F:"), F, "p14_sec_f", routes=F_ENTRY))
    add(spec(14, sel_word(8, "HEAD"), R, "p14_role_head", routes=SEC_F))
    add(*question(14, sel_line(8), "p14_f1_actual_work", routes=SEC_F))
    add(
        spec(
            14,
            sel_word(15, "(GO TO F8)"),
            F,
            "p14_f2_yes",
            routes=SEC_F,
            note="Exact locatable F2 yes-route atom; its printed yes box is absent from pinned page text.",
        )
    )
    add(
        spec(
            14,
            sel_range(
                15, "5. NO (TURN", 16, "TO PAGE 15,                  G1)"
            ),
            F,
            "p14_f2_no",
            routes=SEC_F,
        )
    )
    for selector, key in (
        (sel_line(23), "p14_f3_occupation"),
        (sel_line(27), "p14_f4_industry"),
        (sel_block(31, 32), "p14_f5_weeks"),
        (sel_line(34), "p14_f6_hours"),
    ):
        add(*question(14, selector, key, routes=SEC_F))
    add(
        spec(
            14,
            sel_word(38, "1. YES             (GO TO F8)"),
            F,
            "p14_f7_yes",
            routes=SEC_F,
        )
    )
    add(
        spec(
            14,
            sel_word(
                38,
                "5. NO                (TURN TO PAGE 15,                 G1)",
            ),
            F,
            "p14_f7_no",
            routes=SEC_F,
        )
    )
    add(
        spec(
            14,
            sel_word(44, "job"),
            J,
            "p14_sought_job",
            routes=(*F2_YES, *F7_YES),
        )
    )
    add(
        *question(
            14,
            sel_line(44),
            "p14_f8_sought_job",
            parents=("p14_sought_job",),
            routes=(*F2_YES, *F7_YES),
        )
    )
    add(
        *question(
            14,
            sel_line(48),
            "p14_f9_expected_pay",
            anchor_kind=M,
            parents=("p14_sought_job",),
            routes=(*F2_YES, *F7_YES),
        )
    )
    add(
        spec(
            14,
            sel_word(54, "5. NOTHING                 (GO TO F13)"),
            F,
            "p14_f11_nothing",
            routes=(*F2_YES, *F7_YES),
        )
    )
    add(
        spec(
            14,
            sel_range(
                64, "5. NO (TURN TO", 65, "PAGE 15,                     G1)"
            ),
            F,
            "p14_f13_no",
            routes=(*F2_YES, *F7_YES),
        )
    )

    # Section G: wife actual work. The section header is unconditional; the
    # marital-status and actual-work answers supply the source flow.
    add(spec(15, sel_word(2, "SECTION G:"), F, "p15_sec_g"))
    add(spec(15, sel_line(5), P, "p15_g1_marital_prompt", routes=(SEC_G,)))
    for needle, key in (
        ("1. MARRIED", "p15_married"),
        ("2.    SINGLE", "p15_single"),
        ("3. WIDOWED", "p15_widowed"),
        ("4. DIVORCED", "p15_divorced"),
        ("5.    SEPARATED", "p15_separated"),
    ):
        add(spec(15, sel_word(7, needle), F, key, routes=(SEC_G,)))
    add(
        spec(
            15,
            sel_tail(9, "(TURN TO PAGE 16"),
            F,
            "p15_nonmarried_exit",
            routes=(G_SINGLE, G_WIDOWED, G_DIVORCED, G_SEPARATED),
        )
    )
    add(
        unresolved_repeat(
            15,
            sel_line(11),
            "p15_g2_g13_wife_occupation_cross_reference",
            routes=(G_MARRIED,),
            note="The printed G2-G13 instruction explicitly cross-refers to wife's occupation; global equivalence is deferred.",
        )
    )
    add(
        spec(
            15, sel_word(11, "WIFE'S"), R, "p15_role_wife", routes=(G_MARRIED,)
        )
    )
    add(
        spec(
            15,
            sel_word(11, "OCCUPATION"),
            J,
            "p15_wife_occupation_job",
            routes=(G_MARRIED,),
        )
    )
    add(
        spec(
            15,
            sel_word(13, "wife"),
            R,
            "p15_role_wife_g2",
            routes=(G_MARRIED,),
        )
    )
    add(
        *question(
            15,
            sel_line(13),
            "p15_g2_work",
            parents=("p15_wife_occupation_job",),
            routes=(G_MARRIED,),
        )
    )
    add(spec(15, sel_word(15, "1. YES"), F, "p15_g2_yes", routes=(G_MARRIED,)))
    add(
        spec(
            15,
            sel_range(
                15,
                "5. NO (TURN",
                16,
                "TO PAGE 16,                          G14)",
            ),
            F,
            "p15_g2_no",
            routes=(G_MARRIED,),
        )
    )
    for selector, key in (
        (sel_line(21), "p15_g3_occupation"),
        (sel_line(25), "p15_g4_industry"),
        (sel_line(28), "p15_g5_weeks"),
        (sel_line(30), "p15_g6_hours"),
        (sel_line(32), "p15_g7_unemployment"),
    ):
        add(
            *question(
                15,
                selector,
                key,
                parents=("p15_wife_occupation_job",),
                routes=(G_WORKED,),
            )
        )
    add(spec(15, sel_word(34, "1. YES"), F, "p15_g7_yes", routes=(G_WORKED,)))
    add(
        spec(
            15,
            sel_range(34, "5. NOTO", 35, "(GOG9)"),
            F,
            "p15_g7_no",
            routes=(G_WORKED,),
            note="Exact OCR-interleaved G7 no/skip atom retained.",
        )
    )
    add(
        *question(
            15,
            sel_line(38),
            "p15_g8_unemployment_time",
            parents=("p15_wife_occupation_job",),
            routes=(G7_YES,),
        )
    )

    # Section H: earned-income aggregates and two-role income. H5 is reached
    # from both H1 outcomes, and H8 explicitly resets with ASK EVERYONE.
    add(spec(17, sel_word(3, "SECTION H:"), F, "p17_sec_h"))
    add(
        spec(
            17,
            sel_word(15, "1. FARMER, OR RANCHER"),
            F,
            "p17_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            17,
            sel_word(
                15,
                "5.    NOT A FARMER OR RANCHER                       (GO TO H5)",
            ),
            F,
            "p17_not_farmer",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            17,
            sel_word(24, "net      income       from    farming"),
            FA,
            "p17_farm_aggregate",
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            17,
            sel_block(18, 19),
            "p17_h2_receipts",
            anchor_kind=M,
            parents=("p17_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            17,
            sel_block(21, 22),
            "p17_h3_expenses",
            anchor_kind=M,
            parents=("p17_farm_aggregate",),
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            17,
            sel_line(24),
            "p17_h4_net_farm",
            anchor_kind=None,
            routes=(H_FARMER,),
        )
    )
    add(
        *question(
            17,
            sel_block(28, 29),
            "p17_h5_business",
            anchor_kind=C,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            17, sel_word(31, "1. YES"), F, "p17_business_yes", routes=(SEC_H,)
        )
    )
    add(
        spec(
            17,
            sel_word(31, "5. NO        (GO TO H8)"),
            F,
            "p17_business_no",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            17,
            sel_word(34, "unincorporated              business"),
            BA,
            "p17_business_aggregate",
            routes=(H_BUSINESS,),
        )
    )
    add(
        *question(
            17,
            sel_block(34, 35),
            "p17_h6_incorporation",
            parents=("p17_business_aggregate",),
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            17,
            sel_word(37, "1.     CORPORATION         (GO TO H8)"),
            F,
            "p17_h6_corporation",
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            17,
            sel_word(38, "2. UNINCORPORATED"),
            F,
            "p17_h6_unincorporated",
            routes=(H_BUSINESS,),
        )
    )
    add(
        spec(
            17, sel_word(39, "3. BOTH"), F, "p17_h6_both", routes=(H_BUSINESS,)
        )
    )
    add(
        spec(
            17,
            sel_word(40, "8. DON'T KNOW"),
            F,
            "p17_h6_dont_know",
            routes=(H_BUSINESS,),
        )
    )
    add(
        *question(
            17,
            sel_block(42, 44),
            "p17_h7_business_share",
            anchor_kind=M,
            parents=("p17_business_aggregate",),
            routes=(
                H_BUSINESS_UNINCORPORATED,
                H_BUSINESS_BOTH,
                H_BUSINESS_DK,
            ),
        )
    )
    add(spec(17, sel_word(50, "HEAD"), R, "p17_role_head", routes=(SEC_H,)))
    add(
        *question(
            17,
            sel_block(50, 51),
            "p17_h8_wages",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )

    add(
        *question(
            18,
            sel_block(3, 4),
            "p18_h9_bonus",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(spec(18, sel_word(6, "YES"), F, "p18_h9_yes", routes=(SEC_H,)))
    add(spec(18, sel_tail(6, "[ ] NO"), F, "p18_h9_no", routes=(SEC_H,)))
    add(
        *question(
            18,
            sel_line(10),
            "p18_h10_bonus_amount",
            anchor_kind=None,
            routes=(H9_YES,),
        )
    )
    add(spec(18, sel_word(13, "HEAD"), R, "p18_role_head", routes=(SEC_H,)))
    add(*question(18, sel_line(13), "p18_h11_other_income", routes=(SEC_H,)))
    add(
        *question(
            18,
            sel_word(
                15,
                "professional                        practice        or     trade?",
            ),
            "p18_h11a_professional",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            18,
            sel_word(17, "farming   or market   gardening,"),
            "p18_h11b_farming",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        *question(
            18,
            sel_word(20, "roomers  or boarders?"),
            "p18_h11b_roomers",
            anchor_kind=M,
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            18,
            sel_range(18, '"How much was', 19, 'it?"'),
            P,
            "p18_h11_shared_amount_prompt",
            routes=(SEC_H,),
            note="Exact shared amount-purpose prompt for affirmative H11 items.",
        )
    )
    add(
        spec(
            18,
            sel_tail(44, "[ ] NO"),
            F,
            "p18_h12_no_route",
            routes=(SEC_H,),
            note="Exact source-visible H12 bridge route retained without classifying the transfer-income prose.",
        )
    )

    for line_number, needle, key in (
        (5, "(GO TO H19)", "p19_h14_no_route"),
        (11, "(GO TO H17)", "p19_h15_no_route"),
        (18, "(GO TO H19)", "p19_h17_no_route"),
        (21, "(GO TO H19)", "p19_h18_exit"),
    ):
        add(
            spec(
                19,
                sel_word(line_number, needle),
                F,
                key,
                routes=(SEC_H,),
                note="Exact source-visible bridge route retained without classifying the intervening welfare or SSI prose.",
            )
        )
    add(
        unresolved_repeat(
            19,
            sel_line(24),
            "p19_h19_refer_h11f",
            routes=(SEC_H,),
            note="H19 explicitly cross-refers to excluded H11f; the endpoint is preserved unresolved without promoting Social Security detail into R_Q.",
        )
    )
    add(
        *question(
            19,
            sel_block(24, 25),
            "p19_h19_social_security_checkpoint",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            19,
            sel_word(25, "1.     INCOME FROM SOCIAL SECURITY"),
            F,
            "p19_h19_social_security",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            19,
            sel_word(
                25,
                "5. NO                       SUCH INCOME            (GO TO H23)",
            ),
            F,
            "p19_h19_no_social_security",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            19,
            sel_tail(30, "5.      NO"),
            F,
            "p19_h20_no_route",
            routes=(H_SOCIAL_SECURITY,),
            note="Exact source-visible H20 no/route atom retained under the H19 Social Security branch.",
        )
    )
    add(
        spec(
            19,
            sel_word(36, "(GO TO H23)"),
            F,
            "p19_h22_exit",
            routes=(H_SOCIAL_SECURITY,),
            note="Exact source-visible H22 convergence route retained under the H19 Social Security branch.",
        )
    )
    add(
        spec(
            19,
            sel_line(39),
            P,
            "p19_h23_wife_checkpoint_prompt",
            routes=(SEC_H,),
        )
    )
    add(
        spec(19, sel_word(39, "HEAD"), R, "p19_role_head_h23", routes=(SEC_H,))
    )
    add(
        spec(19, sel_word(39, "WIFE"), R, "p19_role_wife_h23", routes=(SEC_H,))
    )
    add(
        spec(
            19,
            sel_word(40, "YES, WIFE IN FU"),
            F,
            "p19_wife_present",
            routes=(SEC_H,),
        )
    )
    add(
        spec(
            19,
            sel_word(40, "NO WIFE IN FU OR FU HAS FEMALE HEAD"),
            F,
            "p19_no_wife",
            routes=(SEC_H,),
            note="Exact no-wife label retained; the dangling printed '(TURN TO' fragment has no destination in pinned page text and is excluded.",
        )
    )
    add(spec(19, sel_word(44, "wife"), R, "p19_role_wife", routes=(H_WIFE,)))
    add(
        *question(
            19,
            sel_line(44),
            "p19_h24_wife_income_presence",
            anchor_kind=C,
            routes=(H_WIFE,),
        )
    )
    add(
        spec(
            19, sel_word(45, "YES"), F, "p19_wife_income_yes", routes=(H_WIFE,)
        )
    )
    add(
        spec(
            19,
            sel_tail(45, "[ ] NO"),
            F,
            "p19_wife_income_no",
            routes=(H_WIFE,),
        )
    )
    add(
        *question(
            19,
            sel_line(47),
            "p19_h25_wife_source",
            anchor_kind=C,
            routes=(H_WIFE_INCOME,),
        )
    )
    add(
        *question(
            19,
            sel_line(52),
            "p19_h26_wife_amount",
            anchor_kind=M,
            routes=(H_WIFE_INCOME,),
        )
    )

    # Lifetime work-history sections. Each heading is the source-visible
    # navigational root; the L1/M1 labels create response branches below it.
    add(spec(26, sel_word(8, "SECTION L:"), F, "p26_sec_l"))
    add(
        spec(
            26, sel_word(8, "WIFE"), R, "p26_role_wife_header", routes=(SEC_L,)
        )
    )
    add(spec(26, sel_line(11), P, "p26_l1_checkpoint_prompt", routes=(SEC_L,)))
    add(
        spec(
            26,
            sel_word(14, "1. FU HAS NEW WIFE"),
            F,
            "p26_new_wife",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            26,
            sel_word(14, "5. FU HAS SAME WIFE AS IN 1974"),
            F,
            "p26_same_wife",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            26,
            sel_word(15, "OR FU HAS NO WIFE"),
            F,
            "p26_no_wife",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            26,
            sel_word(16, "OR FU HAS FEMALE HEAD"),
            F,
            "p26_female_head",
            routes=(SEC_L,),
        )
    )
    add(
        spec(
            26,
            sel_line(17),
            F,
            "p26_l1_exit",
            routes=(L_SAME, L_NO_WIFE, L_FEMALE_HEAD),
        )
    )
    add(spec(26, sel_word(29, "wife"), R, "p26_role_wife", routes=(L_NEW,)))
    add(*question(26, sel_line(29), "p26_l4_years_worked", routes=(L_NEW,)))
    add(spec(26, sel_word(33, "00. NONE"), F, "p26_l4_none", routes=(L_NEW,)))
    add(
        spec(
            26,
            sel_range(33, "(TURN TO", 34, "PAGE 27,   Ml)"),
            F,
            "p26_l4_none_exit",
            routes=(L4_NONE,),
        )
    )
    add(*question(26, sel_line(35), "p26_l5_full_time", routes=(L_NEW,)))
    add(spec(26, sel_word(40, "ALL"), F, "p26_l5_all", routes=(L_NEW,)))
    add(
        spec(
            26,
            sel_range(40, "(TURN TO", 41, "PAGE 27, Ml)"),
            F,
            "p26_l5_all_exit",
            routes=(L5_ALL,),
        )
    )
    add(*question(26, sel_block(42, 43), "p26_l6_part_time", routes=(L_NEW,)))

    add(spec(27, sel_word(3, "SECTION M:"), F, "p27_sec_m"))
    add(
        spec(
            27, sel_word(3, "HEAD"), R, "p27_role_head_header", routes=(SEC_M,)
        )
    )
    add(spec(27, sel_line(4), P, "p27_m1_checkpoint_prompt", routes=(SEC_M,)))
    add(
        spec(
            27,
            sel_word(6, "1. FU HAS A NEW HEAD THIS YEAR"),
            F,
            "p27_new_head",
            routes=(SEC_M,),
        )
    )
    add(
        spec(
            27,
            sel_word(6, "5. THIS FU HAS THE SAME HEAD AS IN 1974"),
            F,
            "p27_same_head",
            routes=(SEC_M,),
        )
    )
    add(
        spec(
            27,
            sel_line(7),
            F,
            "p27_same_head_exit",
            routes=(M_SAME,),
        )
    )
    add(spec(27, sel_word(28, "HEAD"), R, "p27_role_head", routes=(M_NEW,)))
    add(
        spec(
            27,
            sel_word(
                28, "first         full      time        regular      job"
            ),
            J,
            "p27_first_job",
            routes=(M_NEW,),
        )
    )
    add(
        *question(
            27,
            sel_line(28),
            "p27_m4_first_job",
            parents=("p27_first_job",),
            routes=(M_NEW,),
        )
    )
    add(
        spec(
            27,
            sel_word(30, "0. NEVER WORKED"),
            F,
            "p27_m4_never_worked",
            routes=(M_NEW,),
        )
    )
    add(
        *question(
            27,
            sel_block(33, 34),
            "p27_m5_occupation_history",
            routes=(M_NEW,),
        )
    )
    add(
        spec(
            27,
            sel_word(41, "[ ] NO (GO TO M9)"),
            F,
            "p27_m6_no_route",
            routes=(M_NEW,),
            note="Exact source-visible M6 bridge route retained without classifying the children prose.",
        )
    )
    add(
        spec(
            27,
            sel_word(55, "[ ] NO        (TURN TO PAGE 28, M11)"),
            F,
            "p27_m9_no_route",
            routes=(M_NEW,),
            note="Exact source-visible M9 bridge route retained without classifying the children prose.",
        )
    )

    add(spec(29, sel_word(3, "HEAD"), R, "p29_role_head_m26", routes=(M_NEW,)))
    add(*question(29, sel_line(3), "p29_m26_years_worked", routes=(M_NEW,)))
    add(
        spec(
            29, sel_word(5, "00.    NONE"), F, "p29_m26_none", routes=(M_NEW,)
        )
    )
    add(
        spec(
            29,
            sel_word(5, "(GO TO M29)"),
            F,
            "p29_m26_none_exit",
            routes=(M26_NONE,),
        )
    )
    add(spec(29, sel_word(7, "HEAD"), R, "p29_role_head_m27", routes=(M_NEW,)))
    add(*question(29, sel_line(7), "p29_m27_full_time", routes=(M_NEW,)))
    add(spec(29, sel_word(9, "ALL"), F, "p29_m27_all", routes=(M_NEW,)))
    add(
        spec(
            29,
            sel_word(9, "(GO TO M29)"),
            F,
            "p29_m27_all_exit",
            routes=(M27_ALL,),
        )
    )
    add(
        spec(29, sel_word(11, "HEAD"), R, "p29_role_head_m28", routes=(M_NEW,))
    )
    add(*question(29, sel_block(11, 12), "p29_m28_part_time", routes=(M_NEW,)))
    add(
        spec(
            29,
            sel_word(
                23,
                "5. NO              (TURN TO PAGE 3 OF COVER SHEET)",
            ),
            F,
            "p29_m29_no_route",
            routes=(M_NEW,),
            note="Exact terminal M29 no/cover-sheet route retained without classifying the health-limitation prose.",
        )
    )
    add(
        spec(
            29,
            sel_word(40, "(TURN TO PAGE 3 OF COVER SHEET)"),
            F,
            "p29_m32_exit",
            routes=(M_NEW,),
            note="Exact terminal M32 cover-sheet route retained without classifying the health-limitation prose.",
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
        for position, row in enumerate(occurrence_specs)
    }
    repeat_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        if row["kind"] != A:
            continue
        alias_ids = [review_id_by_key[key] for key in row.get("alias", ())]
        canonical_ids = [
            review_id_by_key[key] for key in row.get("canonical", ())
        ]
        evidence = [
            review_id_by_key[key] for key in row.get("evidence", ())
        ] + [row["review_occurrence_id"]]
        repeat_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "relation": row["relation"],
                "alias_anchor_review_occurrence_ids": sorted(
                    set(alias_ids), key=occurrence_order.__getitem__
                ),
                "canonical_anchor_review_occurrence_ids": sorted(
                    set(canonical_ids), key=occurrence_order.__getitem__
                ),
                "evidence_review_occurrence_ids": sorted(
                    set(evidence), key=occurrence_order.__getitem__
                ),
                "target_scope": row["target_scope"],
                "resolution_status": row["resolution_status"],
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
            "whole_page_review": "all_29_pages_including_empty_occurrence_pages",
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
        f"document 16 source review: {len(review['occurrence_specs'])} "
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
