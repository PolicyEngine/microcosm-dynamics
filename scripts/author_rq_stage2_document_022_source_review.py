#!/usr/bin/env python3
"""Author the candidate-free stage-2 source review for q78.pdf.

All 42 pages were reviewed from authenticated Poppler 26.04.0 text and page
renders before these selectors were written. The stage-1 candidate artifact is
not opened here; candidate adjudication happens only after this source ledger
validates in the sealed builder. OCR-destroyed printing is never reconstructed.
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
import build_rq_stage2_document_022_annotation as annotation  # noqa: E402

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
    """Raised when a source selector no longer resolves."""


def _line_rows(page_text: str) -> list[dict[str, Any]]:
    return stage1._physical_lines(page_text)


def _utf8(page_text: str, start: int, end: int) -> tuple[int, int]:
    return (
        len(page_text[:start].encode("utf-8")),
        len(page_text[:end].encode("utf-8")),
    )


def resolve_line(page_text: str, number: int) -> tuple[int, int]:
    for row in _line_rows(page_text):
        if row["line_number"] == number:
            return _utf8(page_text, row["start"], row["end"])
    raise SpecError(f"line {number} is blank or absent")


def resolve_block(page_text: str, first: int, last: int) -> tuple[int, int]:
    start = resolve_line(page_text, first)[0]
    end = resolve_line(page_text, last)[1]
    if start >= end:
        raise SpecError(f"block {first}-{last} is inverted")
    return start, end


def resolve_needle(
    page_text: str, number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    line_start, line_end = resolve_line(page_text, number)
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
            f"{number}"
        )
    return found[occurrence], found[occurrence] + len(target)


def resolve_tail(
    page_text: str, number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    start, _ = resolve_needle(page_text, number, needle, occurrence)
    return start, resolve_line(page_text, number)[1]


def resolve_run(
    page_text: str, number: int, first: int, last: int
) -> tuple[int, int]:
    line_start, line_end = resolve_line(page_text, number)
    segment = page_text.encode("utf-8")[line_start:line_end]
    offsets: list[tuple[int, int]] = []
    position = 0
    while position < len(segment):
        while position < len(segment) and segment[position] in b" \t":
            position += 1
        if position >= len(segment):
            break
        token_start = position
        while position < len(segment) and segment[position] not in b" \t":
            position += 1
        offsets.append((token_start, position))
    if not 0 <= first <= last < len(offsets):
        raise SpecError(
            f"token run {first}-{last} is outside line {number}: "
            f"{len(offsets)} tokens"
        )
    return (
        line_start + offsets[first][0],
        line_start + offsets[last][1],
    )


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
    if mode == "run":
        return resolve_run(page_text, selector[1], selector[2], selector[3])
    raise SpecError(f"unknown selector mode {mode!r}")


def spec(
    page: int,
    kind: str,
    selector: tuple[Any, ...],
    key: str,
    *,
    parents: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
    note: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "page": page,
        "kind": kind,
        "selector": selector,
        "key": key,
        "parents": tuple(parents),
        "routes": tuple(tuple(route) for route in routes),
        "note": note,
        **extra,
    }


def line(page: int, number: int, kind: str, key: str, **rest: Any):
    return spec(page, kind, ("line", number), key, **rest)


def block(page: int, first: int, last: int, kind: str, key: str, **rest: Any):
    return spec(page, kind, ("block", first, last), key, **rest)


def word(
    page: int,
    number: int,
    needle: str,
    kind: str,
    key: str,
    occurrence: int = 0,
    **rest: Any,
):
    return spec(
        page,
        kind,
        ("needle", number, needle, occurrence),
        key,
        **rest,
    )


def tail(
    page: int,
    number: int,
    needle: str,
    kind: str,
    key: str,
    occurrence: int = 0,
    **rest: Any,
):
    return spec(
        page,
        kind,
        ("tail", number, needle, occurrence),
        key,
        **rest,
    )


def run(
    page: int,
    number: int,
    first: int,
    last: int,
    kind: str,
    key: str,
    **rest: Any,
):
    return spec(page, kind, ("run", number, first, last), key, **rest)


def question(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    anchor_kind: str | None = C,
    parents: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
) -> tuple[dict[str, Any], ...]:
    prompt = spec(page, P, selector, f"{key}_prompt", routes=routes)
    if anchor_kind is None:
        return (prompt,)
    return (
        spec(
            page,
            anchor_kind,
            selector,
            key,
            parents=parents,
            routes=routes,
        ),
        prompt,
    )


_DEFAULT_NOTES = {
    F: "Exact printed flow or routing atom on a retained screen.",
    R: "Exact printed questionnaire-role anchor.",
    J: "Exact printed job-establishing anchor.",
    M: "Exact printed actual-remuneration component anchor.",
    T: "Exact printed role-total anchor.",
    FA: "Exact printed farm-aggregate anchor.",
    BA: "Exact printed business-aggregate anchor.",
    C: "Exact printed contextual field for a ratified purpose.",
    P: "Exact printed field-purpose prompt.",
    A: "Exact printed repeat instruction preserved for global resolution.",
}


PAGE_NOTES = {
    page: (
        "Whole page reviewed from authenticated text and render; retained "
        "occurrences, if any, are exhaustively listed in this source ledger."
    )
    for page in range(1, PAGE_COUNT + 1)
}
PAGE_NOTES.update(
    {
        1: "Face sheet and section A children/schooling fields reviewed; "
        "administrative and education content maps to no retained employment "
        "or work-income occurrence.",
        2: "Section B transportation fields reviewed; hypothetical commuting "
        "access and vehicle ownership map to no retained employment or "
        "work-income occurrence.",
        3: "Section C housing, utility, mortgage, and property-value fields "
        "reviewed; housing finance maps to no retained occurrence.",
        4: "Section C rent and utility fields reviewed; housing costs map to no "
        "retained employment or work-income occurrence.",
        5: "Section C residential-mobility fields reviewed; actual or possible "
        "moves and their reasons map to no retained occurrence.",
        6: "Section D assignment, occupation, industry, and routing reviewed.",
        7: "D5-D17 reviewed; union, training, and competition fields excluded.",
        8: "D18-D29 tenure and actual work-absence fields reviewed.",
        9: "D30-D37 actual absence and work exposure reviewed.",
        10: "D38-D51 pay, extra-job, and work-exposure fields reviewed.",
        11: "D52-D59 reviewed; counterfactual labor supply, desired work, and "
        "commuting fields map to no retained occurrence.",
        12: "D60-D71 first-regular-job screen and exact visible routes reviewed.",
        13: "D72-D82 employer tenure reviewed; networking fields excluded.",
        14: "D83-D89 retirement plans, future benefit eligibility, and expected "
        "income reviewed; prospective and counterfactual fields map to no "
        "retained occurrence.",
        15: "Section E sought-job and expected-pay fields reviewed.",
        16: "E14-E26 first-job screen reviewed; networking fields excluded.",
        17: "E27-E38 last-job and source-visible absence fields reviewed; job-"
        "separation reasons and related prose were excluded.",
        18: "E39-E45 work exposure reviewed; commuting fields excluded.",
        19: "Section F retirement and actual post-retirement work reviewed.",
        20: "F10-F21 actual past work reviewed; counterfactual prose excluded.",
        21: "F22-F31 future job intentions, search activity, training, location, "
        "hours, and hypothetical pay reviewed; none establishes actual paid "
        "work or remuneration.",
        22: "Section G reviewed; OCR-destroyed G1-G7 were not reconstructed.",
        23: "G10-G17 source-visible spouse work-absence fields reviewed.",
        24: "G20-G27 spouse work and employer tenure reviewed; commuting and "
        "job-network fields were excluded.",
        25: "G28-G39 job-search help, workplace contacts, and prospective "
        "retirement eligibility reviewed; none maps to a retained field "
        "purpose.",
        26: "G40-G45 unpaid household-work fields reviewed; housework is outside "
        "the retained paid-work and work-income occurrence domain.",
        27: "G46-G58 food-stamp receipt and household food-spending fields "
        "reviewed; transfer and consumption content maps to no retained "
        "occurrence.",
        28: "G59-G62 food-stamp receipt and purchase-value fields reviewed; "
        "transfer content maps to no retained occurrence.",
        29: "Section H farm, business, and head earnings reviewed.",
        30: "Head remuneration reviewed; welfare, Medicaid, Social Security, "
        "and other nonlabor H11c-H19 fields were excluded.",
        31: "Spouse income source and role total reviewed; H20-H22 and H27-H31 "
        "transfer and nonwork fields were excluded.",
        32: "Other-person income/work grid and visible repeats reviewed; "
        "OCCUPATION is contextual rather than a distinct printed job, and "
        "residual H43-H45 income fields were excluded.",
        33: "Continuation income/work grid reviewed column by column; residual "
        "H43-H45 source and amount columns were excluded.",
        34: "H46-H56 residual-income, medical-program, and family job-search "
        "fields reviewed; they map to no retained purpose, and the turn-back "
        "directive duplicates repeat evidence already printed on retained "
        "pages 32-33.",
        35: "H57-H71 lump-sum receipts, outside support, union membership, and "
        "health-limitation fields reviewed; none maps to a retained actual-"
        "work or remuneration purpose.",
        36: "H72-H80 other-adult disability, care, and extra-cost fields "
        "reviewed; health limitations map to no retained occurrence.",
        37: "H81-H89 child disability, care, schooling, and extra-cost fields "
        "reviewed; they map to no retained occurrence.",
        38: "Section J new-wife lifetime work history reviewed.",
        39: "Section K new-head first-job screen reviewed.",
        40: "New-head mobility/background reviewed; no occurrence retained.",
        41: "New-head lifetime work history reviewed; schooling excluded.",
        42: "Section L interviewer-observation and geographic-location fields "
        "reviewed; administrative geography maps to no retained occurrence.",
    }
)


D = ("p6_section_d",)
E = ("p15_section_e",)
F_ROUTE = ("p19_section_f",)
G = ("p22_section_g",)
H = ("p29_section_h",)
J_ROUTE = ("p38_section_j",)
K = ("p39_section_k",)

ROWS: list[dict[str, Any]] = []


def add(*items: dict[str, Any]) -> None:
    ROWS.extend(items)


def repeat(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    routes: Sequence[Sequence[str]],
    note: str = "",
) -> dict[str, Any]:
    return spec(
        page,
        A,
        selector,
        key,
        routes=routes,
        note=note,
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    )


# Section D: head employment.
add(line(6, 3, F, "p6_section_d"))
add(*question(6, ("block", 6, 7), "p6_d1_assignment", routes=(D,)))
add(word(6, 6, "HEAD", R, "p6_role_head", routes=(D,)))
add(word(6, 10, "TURNTO PAGE19, F1", F, "p6_turn_f1", routes=(D,)))
add(line(6, 11, F, "p6_turn_e1", routes=(D,)))
add(word(6, 14, "(GO TO D2 IF", F, "p6_other_has_job", routes=(D,)))
add(block(6, 16, 17, F, "p6_otherwise_turn_f1", routes=(D,)))
add(*question(6, ("line", 20), "p6_d2_occupation", routes=(D,)))
add(line(6, 28, F, "p6_d3_if_not_clear", routes=(D,)))
add(
    *question(
        6,
        ("line", 29),
        "p6_d3_detail",
        routes=(D + ("p6_d3_if_not_clear",),),
    )
)
add(*question(6, ("line", 34), "p6_d4_industry", routes=(D,)))

add(*question(7, ("line", 2), "p7_d5_employee_self", routes=(D,)))
add(word(7, 6, "(GO TO D12)", F, "p7_d5_go_d12", routes=(D,)))
add(*question(7, ("run", 8, 0, 5), "p7_d6_government", routes=(D,)))
add(*question(7, ("run", 8, 6, 14), "p7_d9_government", routes=(D,)))
add(run(7, 17, 0, 2, F, "p7_d7_go_d12", routes=(D,)))
add(run(7, 17, 3, 5, F, "p7_d10_go_d12", routes=(D,)))
add(run(7, 23, 3, 5, F, "p7_d11_go_d12", routes=(D,)))
add(line(7, 24, F, "p7_d8_go_d12", routes=(D,)))
add(run(7, 31, 2, 4, F, "p7_d13_go_d15", routes=(D,)))

add(
    word(
        8,
        3,
        "present position",
        J,
        "p8_job_present_position",
        routes=(D,),
    )
)
add(
    *question(
        8,
        ("line", 3),
        "p8_d18_tenure",
        parents=("p8_job_present_position",),
        routes=(D,),
    )
)
add(run(8, 6, 0, 2, F, "p8_d18_less_year", routes=(D,)))
add(run(8, 6, 3, 9, F, "p8_d18_year_more", routes=(D,)))
add(
    *question(
        8,
        ("line", 9),
        "p8_d19_start",
        parents=("p8_job_present_position",),
        routes=(D + ("p8_d18_less_year",),),
    )
)
add(line(8, 15, F, "p8_d20_go_d24", routes=(D,)))
add(run(8, 19, 1, 3, F, "p8_d21_go_d23", routes=(D,)))
add(line(8, 29, F, "p8_d23_go_d24", routes=(D,)))
for number, key in (
    (31, "p8_d24_family_sick"),
    (35, "p8_d25_amount"),
    (37, "p8_d26_own_sick"),
    (40, "p8_d27_amount"),
    (42, "p8_d28_vacation"),
    (45, "p8_d29_amount"),
):
    add(
        *question(
            8,
            ("line", number),
            key,
            parents=("p9_job_main",),
            routes=(D,),
        )
    )
add(run(8, 33, 1, 3, F, "p8_d24_go_d26", routes=(D,)))
add(run(8, 39, 1, 3, F, "p8_d26_go_d28", routes=(D,)))
add(run(8, 44, 1, 3, F, "p8_d28_turn_d30", routes=(D,)))

for number, key in (
    (7, "p9_d30_strike"),
    (11, "p9_d31_amount"),
    (14, "p9_d32_unemployed"),
    (18, "p9_d33_amount"),
    (21, "p9_d34_weeks"),
    (25, "p9_d35_hours"),
    (29, "p9_d36_overtime"),
    (33, "p9_d37_overtime_hours"),
):
    add(
        *question(
            9,
            ("line", number),
            key,
            parents=("p9_job_main",),
            routes=(D,),
        )
    )
add(word(9, 21, "main job", J, "p9_job_main", routes=(D,)))
add(line(9, 9, F, "p9_d30_go_d32", routes=(D,)))
add(line(9, 16, F, "p9_d32_go_d34", routes=(D,)))
add(line(9, 31, F, "p9_d36_turn_d38", routes=(D,)))

add(
    *question(
        10,
        ("line", 3),
        "p10_d38_pay_form",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(
    run(
        10,
        8,
        0,
        5,
        M,
        "p10_d39_salary",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(
    run(
        10,
        8,
        6,
        11,
        M,
        "p10_d42_regular_wage",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(
    run(
        10,
        15,
        5,
        10,
        M,
        "p10_d43_overtime_wage",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(run(10, 19, 3, 5, F, "p10_d40_go_d46", routes=(D,)))
add(line(10, 20, F, "p10_d41_go_d46", routes=(D,)))
add(
    run(
        10,
        24,
        3,
        7,
        M,
        "p10_d41_extra_hour_pay",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(line(10, 28, F, "p10_d43_go_d46", routes=(D,)))
add(
    run(
        10,
        24,
        8,
        10,
        M,
        "p10_d45_extra_hour_pay",
        parents=("p9_job_main",),
        routes=(D,),
    )
)
add(line(10, 29, F, "p10_d45_go_d46", routes=(D,)))
add(word(10, 33, "extra jobs", J, "p10_job_extra", routes=(D,)))
add(
    *question(
        10,
        ("block", 33, 34),
        "p10_d46_extra_jobs",
        parents=("p10_job_extra",),
        routes=(D,),
    )
)
add(run(10, 36, 1, 3, F, "p10_d46_turn_d52", routes=(D,)))
add(
    *question(
        10,
        ("line", 40),
        "p10_d47_occupation",
        parents=("p10_job_extra",),
        routes=(D,),
    )
)
add(
    *question(
        10,
        ("line", 46),
        "p10_d49_hourly_pay",
        anchor_kind=M,
        parents=("p10_job_extra",),
        routes=(D,),
    )
)
for number, key in ((48, "p10_d50_weeks"), (51, "p10_d51_hours")):
    add(
        *question(
            10,
            ("line", number),
            key,
            parents=("p10_job_extra",),
            routes=(D,),
        )
    )

add(word(12, 9, "HEAD", R, "p12_role_head", routes=(D,)))
add(run(12, 9, 3, 4, F, "p12_never_regular_turn", routes=(D,)))
add(
    word(
        12,
        8,
        "a regular or possibly permanent job",
        J,
        "p12_job_first_regular",
        routes=(D,),
    )
)
add(
    *question(
        12,
        ("line", 14),
        "p12_d62_first_occupation",
        parents=("p12_job_first_regular",),
        routes=(D,),
    )
)
for number, first, last, key in (
    (27, 2, 4, "p12_d65_go_d71"),
    (38, 1, 3, "p12_d68_go_d71"),
    (41, 2, 4, "p12_d69_go_d71"),
):
    add(run(12, number, first, last, F, key, routes=(D,)))
add(line(12, 46, F, "p12_d70_go_d71", routes=(D,)))

add(word(13, 4, "(TURNTO PAGE22, G1)", F, "p13_d72_turn_g1", routes=(D,)))
add(
    *question(
        13,
        ("line", 7),
        "p13_d73_employer_tenure",
        parents=("p8_job_present_position",),
        routes=(D,),
    )
)
for number, key in (
    (23, "p13_d76_go_d82"),
    (34, "p13_d79_go_d82"),
    (37, "p13_d80_go_d82"),
):
    add(word(13, number, "(GO TO D82)", F, key, routes=(D,)))
add(line(13, 49, F, "p13_d82_turn_g1", routes=(D,)))

# Section E: looking for work and last job.
add(block(15, 3, 4, F, "p15_section_e"))
add(word(15, 8, "job", J, "p15_job_sought", routes=(E,)))
add(
    *question(
        15,
        ("line", 8),
        "p15_e1_sought_occupation",
        parents=("p15_job_sought",),
        routes=(E,),
    )
)
add(
    *question(
        15,
        ("line", 12),
        "p15_e2_expected_pay",
        anchor_kind=M,
        parents=("p15_job_sought",),
        routes=(E,),
    )
)
add(word(15, 17, "(GO TO Eh)", F, "p15_e4_go_e6", routes=(E,)))
add(word(15, 31, "(GO TO E10)", F, "p15_e9_go_e10", routes=(E,)))

add(word(16, 3, "job", J, "p16_job_ever", routes=(E,)))
add(
    *question(
        16,
        ("line", 3),
        "p16_e14_ever_job",
        parents=("p16_job_ever",),
        routes=(E,),
    )
)
add(word(16, 4, "(TURNTO PAGE22, G1)", F, "p16_e14_turn_g1", routes=(E,)))
add(run(16, 8, 2, 3, F, "p16_e15_under45", routes=(E,)))
add(word(16, 8, "HEAD", R, "p16_role_head", routes=(E,)))
add(run(16, 8, 6, 9, F, "p16_e15_45_older", routes=(E,)))
add(run(16, 8, 10, 12, F, "p16_e15_turn_e27", routes=(E,)))
add(
    word(
        16,
        12,
        "a regular or possibly permanent job",
        J,
        "p16_job_first_regular",
        routes=(E + ("p16_e15_under45",),),
    )
)
add(
    run(
        16,
        13,
        4,
        6,
        F,
        "p16_never_regular_turn_e27",
        routes=(E + ("p16_e15_under45",),),
    )
)
add(
    *question(
        16,
        ("line", 17),
        "p16_e17_first_occupation",
        parents=("p16_job_first_regular",),
        routes=(E + ("p16_e15_under45",),),
    )
)
for number, key in (
    (30, "p16_e20_go_e26"),
    (42, "p16_e23_go_e26"),
    (46, "p16_e24_go_e26"),
):
    add(
        run(
            16,
            number,
            1,
            3,
            F,
            key,
            routes=(E + ("p16_e15_under45",),),
        )
    )

add(word(17, 4, "last job", J, "p17_job_last", routes=(E,)))
for number, key in (
    (4, "p17_e27_last_occupation"),
    (10, "p17_e28_industry"),
    (19, "p17_e30_last_worked"),
):
    add(
        *question(
            17,
            ("line", number),
            key,
            parents=("p17_job_last",),
            routes=(E,),
        )
    )
add(run(17, 21, 1, 5, F, "p17_e30_recent", routes=(E,)))
add(run(17, 21, 7, 8, F, "p17_e30_before", routes=(E,)))
add(
    run(
        17,
        22,
        2,
        4,
        F,
        "p17_e30_turn_g1",
        routes=(E + ("p17_e30_before",),),
    )
)
for number, key in (
    (24, "p17_e31_vacation"),
    (28, "p17_e32_amount"),
    (34, "p17_e35_own_sick"),
    (39, "p17_e36_amount"),
):
    add(
        *question(
            17,
            ("line", number),
            key,
            parents=("p17_job_last",),
            routes=(E + ("p17_e30_recent",),),
        )
    )
add(
    run(
        17,
        26,
        4,
        6,
        F,
        "p17_e31_go_e33",
        routes=(E + ("p17_e30_recent",),),
    )
)
add(
    run(
        17,
        36,
        6,
        8,
        F,
        "p17_e35_go_e37",
        routes=(E + ("p17_e30_recent",),),
    )
)

E_RECENT = E + ("p17_e30_recent",)
for number, key in (
    (5, "p18_e39_unemployed"),
    (9, "p18_e40_amount"),
    (12, "p18_e41_weeks"),
    (16, "p18_e42_hours"),
):
    add(
        *question(
            18,
            ("line", number),
            key,
            parents=("p17_job_last",),
            routes=(E_RECENT,),
        )
    )
add(run(18, 7, 1, 3, F, "p18_e39_go_e41", routes=(E_RECENT,)))
add(run(18, 22, 4, 6, F, "p18_e43_turn_g1", routes=(E_RECENT,)))
add(line(18, 35, F, "p18_e45_turn_g1", routes=(E_RECENT,)))

# Section F: retirement and actual post-retirement work.
add(block(19, 4, 5, F, "p19_section_f"))
add(run(19, 11, 0, 1, F, "p19_f1_retired", routes=(F_ROUTE,)))
add(line(19, 12, F, "p19_f1_other", routes=(F_ROUTE,)))
add(
    line(
        19,
        13,
        F,
        "p19_f1_turn_f15",
        routes=(F_ROUTE + ("p19_f1_other",),),
    )
)
F_RETIRED = F_ROUTE + ("p19_f1_retired",)
add(
    word(
        19,
        17,
        "(IF LESS THAN20 YEARSAGO)",
        F,
        "p19_f2_less20",
        routes=(F_RETIRED,),
    )
)
add(
    word(
        19,
        17,
        "(IF 20 OR MOREYEARSAGO)",
        F,
        "p19_f2_20_more",
        routes=(F_RETIRED,),
    )
)
add(
    tail(
        19,
        17,
        "(TURN",
        F,
        "p19_f2_turn_f15",
        routes=(F_RETIRED + ("p19_f2_20_more",),),
    )
)
F_RETIRED_RECENT = F_RETIRED + ("p19_f2_less20",)
add(line(19, 26, F, "p19_f4_go_f6", routes=(F_RETIRED_RECENT,)))
add(*question(19, ("line", 37), "p19_f7_worked", routes=(F_RETIRED_RECENT,)))
add(
    word(
        19,
        42,
        "(TURN TO PAGE20, ~10)",
        F,
        "p19_f8_turn_f10",
        routes=(F_RETIRED_RECENT,),
    )
)

add(
    word(
        20,
        3,
        "(GO TO F12)",
        F,
        "p20_f10_go_f12",
        routes=(F_RETIRED_RECENT,),
    )
)
F_F15_ROUTES = (
    F_ROUTE + ("p19_f1_other", "p19_f1_turn_f15"),
    F_RETIRED + ("p19_f2_20_more", "p19_f2_turn_f15"),
    F_RETIRED_RECENT,
)
add(*question(20, ("line", 26), "p20_f15_money_work", routes=F_F15_ROUTES))
add(
    word(
        20,
        27,
        "(.TURNTO PAGE21, F22)",
        F,
        "p20_f15_turn_f22",
        routes=F_F15_ROUTES,
    )
)
add(*question(20, ("line", 30), "p20_f16_occupation", routes=F_F15_ROUTES))
add(*question(20, ("line", 34), "p20_f17_industry", routes=F_F15_ROUTES))
add(*question(20, ("line", 36), "p20_f18_weeks", routes=F_F15_ROUTES))
add(*question(20, ("line", 38), "p20_f19_hours", routes=F_F15_ROUTES))
add(
    *question(
        20,
        ("line", 40),
        "p20_f20_still_working",
        routes=F_F15_ROUTES,
    )
)
add(line(20, 43, F, "p20_f20_turn_f22", routes=F_F15_ROUTES))

# Section H: farm, business, role earnings, and other-person work grids.
add(line(29, 4, F, "p29_section_h"))
add(run(29, 14, 2, 6, F, "p29_h1_not_farmer", routes=(H,)))
add(
    run(
        29,
        15,
        1,
        3,
        F,
        "p29_h1_go_h5",
        routes=(H + ("p29_h1_not_farmer",),),
    )
)
add(
    *question(
        29,
        ("block", 18, 19),
        "p29_h2_farm_receipts",
        anchor_kind=M,
        parents=("p29_farm_aggregate",),
        routes=(H,),
    )
)
add(
    *question(
        29,
        ("block", 20, 21),
        "p29_h3_farm_expenses",
        anchor_kind=M,
        parents=("p29_farm_aggregate",),
        routes=(H,),
    )
)
add(
    *question(
        29, ("line", 22), "p29_h4_net_farm", anchor_kind=None, routes=(H,)
    )
)
add(
    run(
        29,
        22,
        5,
        8,
        FA,
        "p29_farm_aggregate",
        routes=(H,),
    )
)
add(
    *question(
        29,
        ("block", 25, 26),
        "p29_h5_business_interest",
        parents=("p29_business_aggregate",),
        routes=(H,),
    )
)
add(run(29, 27, 0, 3, F, "p29_h5_no_go_h8", routes=(H,)))
add(
    *question(
        29,
        ("block", 30, 31),
        "p29_h6_incorporation",
        parents=("p29_business_aggregate",),
        routes=(H,),
    )
)
add(
    run(
        29,
        30,
        7,
        8,
        BA,
        "p29_business_aggregate",
        routes=(H,),
    )
)
add(run(29, 33, 1, 2, F, "p29_h6_corporation", routes=(H,)))
add(
    run(
        29,
        35,
        0,
        2,
        F,
        "p29_h6_go_h8_ocr_h3",
        routes=(H + ("p29_h6_corporation",),),
        note=(
            "Exact OCR bytes read GO TO H3; the rendered directive is H8, "
            "and no correction is invented in the source span."
        ),
    )
)
add(
    *question(
        29,
        ("block", 37, 38),
        "p29_h7_business_income",
        anchor_kind=M,
        parents=("p29_business_aggregate",),
        routes=(H,),
    )
)
add(
    *question(
        29, ("block", 45, 46), "p29_h8_head_total", anchor_kind=T, routes=(H,)
    )
)
add(run(29, 45, 5, 5, R, "p29_role_head", routes=(H,)))

add(
    *question(
        30, ("line", 2), "p30_h9_bonus_income", anchor_kind=M, routes=(H,)
    )
)
add(run(30, 4, 1, 3, F, "p30_h9_go_h11", routes=(H,)))
add(run(30, 8, 3, 3, R, "p30_role_head", routes=(H,)))
add(run(30, 9, 0, 4, F, "p30_h11_if_yes", routes=(H,)))
for number, first, last, key in (
    (9, 6, 9, "p30_h11_professional_trade"),
    (11, 3, 6, "p30_h11_farming_market"),
    (12, 0, 2, "p30_h11_roomers_boarders"),
):
    add(run(30, number, first, last, M, key, routes=(H,)))
add(run(30, 13, 0, 2, F, "p30_h11_if_no", routes=(H,)))
for number, first, last, key in (
    (22, 2, 7, "p30_h12_go_h16"),
    (27, 2, 4, "p30_h13_go_h15"),
    (42, 2, 4, "p30_h16_go_h18"),
    (47, 2, 3, "p30_h18_turn_h20"),
):
    add(run(30, number, first, last, F, key, routes=(H,)))

add(run(31, 13, 2, 4, F, "p31_h21_go_h23", routes=(H,)))
add(run(31, 19, 1, 5, F, "p31_h23_wife_in_fu", routes=(H,)))
add(run(31, 19, 8, 15, F, "p31_h23_no_wife", routes=(H,)))
add(
    run(
        31,
        20,
        0,
        2,
        F,
        "p31_h23_no_wife_turn_h32",
        routes=(H + ("p31_h23_no_wife",),),
    )
)
add(
    run(
        31,
        19,
        3,
        3,
        R,
        "p31_role_wife",
        routes=(H + ("p31_h23_wife_in_fu",),),
    )
)
H_WIFE = H + ("p31_h23_wife_in_fu",)
add(*question(31, ("line", 22), "p31_h24_wife_income", routes=(H_WIFE,)))
add(run(31, 24, 2, 4, F, "p31_h24_no_turn_h32", routes=(H_WIFE,)))
add(*question(31, ("line", 26), "p31_h25_income_source", routes=(H_WIFE,)))
add(
    *question(
        31, ("line", 28), "p31_h26_wife_total", anchor_kind=T, routes=(H_WIFE,)
    )
)
add(run(31, 32, 2, 4, F, "p31_h27_go_h29", routes=(H_WIFE,)))

add(run(32, 4, 0, 3, F, "p32_h32_someone", routes=(H,)))
add(run(32, 4, 6, 8, F, "p32_h32_none_turn_h46", routes=(H,)))
H_SOMEONE = H + ("p32_h32_someone",)
add(run(32, 7, 1, 4, F, "p32_h33_over13", routes=(H_SOMEONE,)))
add(run(32, 7, 5, 7, F, "p32_h33_none_turn_h46", routes=(H_SOMEONE,)))
H_GRID = H_SOMEONE + ("p32_h33_over13",)
add(repeat(32, ("block", 9, 10), "p32_repeat_list_people", routes=(H_GRID,)))
add(*question(32, ("run", 13, 0, 6), "p32_h34_income", routes=(H_GRID,)))
add(repeat(32, ("run", 14, 0, 4), "p32_repeat_next_person", routes=(H_GRID,)))
add(
    *question(
        32, ("line", 17), "p32_h35_amount", anchor_kind=M, routes=(H_GRID,)
    )
)
add(*question(32, ("block", 19, 20), "p32_h36_source", routes=(H_GRID,)))
add(run(32, 23, 0, 2, F, "p32_h36_wages_business", routes=(H_GRID,)))
H_WORK = H_GRID + ("p32_h36_wages_business",)
for number, key in (
    (24, "p32_h37_occupation"),
    (27, "p32_h38_weeks"),
    (30, "p32_h39_hours"),
):
    add(*question(32, ("line", number), key, routes=(H_WORK,)))
add(run(32, 33, 1, 3, F, "p32_h40_if_unknown", routes=(H_WORK,)))
add(
    *question(
        32,
        ("run", 33, 4, 8),
        "p32_h40_half_time",
        routes=(H_WORK + ("p32_h40_if_unknown",),),
    )
)
add(*question(32, ("block", 34, 35), "p32_h41_missed_work", routes=(H_WORK,)))
add(run(32, 36, 2, 4, F, "p32_h41_go_h43", routes=(H_WORK,)))
add(*question(32, ("line", 38), "p32_h42_amount", routes=(H_WORK,)))

for first, last, key in (
    (0, 4, "p33_repeat_top_h34"),
    (5, 8, "p33_repeat_top_h43_second"),
    (9, 12, "p33_repeat_top_h43_third"),
):
    add(repeat(33, ("run", 11, first, last), key, routes=(H_GRID,)))
for first, last, key in (
    (0, 2, "p33_h35_amount_first"),
    (3, 5, "p33_h35_amount_second"),
    (6, 8, "p33_h35_amount_third"),
):
    add(run(33, 14, first, last, M, key, routes=(H_GRID,)))
for number, prefix in (
    (16, "h36_source"),
    (21, "h37_occupation"),
    (23, "h38_weeks"),
    (25, "h39_hours"),
):
    route = H_GRID if number == 16 else H_WORK
    for token, ordinal in enumerate(("first", "second", "third")):
        add(
            run(
                33,
                number,
                token,
                token,
                C,
                f"p33_{prefix}_{ordinal}",
                routes=(route,),
            )
        )
for first, last, ordinal in (
    (0, 1, "first"),
    (2, 3, "second"),
    (4, 5, "third"),
):
    add(
        run(
            33,
            33,
            first,
            last,
            C,
            f"p33_h42_units_{ordinal}",
            routes=(H_WORK,),
        )
    )
add(repeat(33, ("run", 36, 1, 4), "p33_repeat_bottom_h34", routes=(H_GRID,)))
add(repeat(33, ("run", 36, 5, 8), "p33_repeat_bottom_h43", routes=(H_GRID,)))

# Section G: spouse work. G1-G7 and G18-G19 are not sliceable in q78.
add(block(22, 3, 4, F, "p22_section_g"))
add(run(22, 3, 1, 1, R, "p22_role_wife", routes=(G,)))
add(run(22, 15, 1, 8, F, "p22_g5_no_turn_g20", routes=(G,)))

for selector, key in (
    (("line", 11), "p23_g10_own_sick"),
    (("line", 15), "p23_g11_amount"),
    (("line", 18), "p23_g12_vacation"),
    (("line", 22), "p23_g13_amount"),
    (("line", 25), "p23_g14_strike"),
    (("line", 29), "p23_g15_amount"),
    (("block", 32, 33), "p23_g16_unemployed"),
    (("line", 36), "p23_g17_amount"),
):
    add(*question(23, selector, key, routes=(G,)))
add(run(23, 11, 3, 3, R, "p23_role_wife", routes=(G,)))
for number, first, last, key in (
    (13, 1, 4, "p23_g10_go_g12"),
    (20, 2, 4, "p23_g12_go_g14"),
    (27, 2, 5, "p23_g14_go_g16"),
    (34, 0, 3, "p23_g16_go_g18"),
):
    add(run(23, number, first, last, F, key, routes=(G,)))

add(*question(24, ("line", 3), "p24_g20_working_now", routes=(G,)))
add(run(24, 3, 3, 3, R, "p24_role_wife", routes=(G,)))
add(run(24, 5, 0, 3, F, "p24_g20_turn_g39", routes=(G,)))
add(run(24, 9, 2, 6, F, "p24_g21_none_go_g24", routes=(G,)))
add(run(24, 23, 0, 4, F, "p24_g24_under45", routes=(G,)))
add(run(24, 23, 7, 11, F, "p24_g24_45_older", routes=(G,)))
add(
    run(
        24,
        24,
        0,
        2,
        F,
        "p24_g24_turn_g34",
        routes=(G + ("p24_g24_45_older",),),
    )
)
add(
    *question(
        24,
        ("line", 26),
        "p24_g25_employer_tenure",
        routes=(G + ("p24_g24_under45",),),
    )
)
add(
    run(
        24,
        47,
        1,
        3,
        F,
        "p24_g27_turn_g33",
        routes=(G + ("p24_g24_under45",),),
    )
)

# Sections J and K: lifetime work history and first job.
add(line(38, 6, F, "p38_section_j"))
for number, first, last, key in (
    (22, 0, 3, "p38_j3_go_j8"),
    (26, 0, 2, "p38_j6_go_j8"),
    (30, 0, 2, "p38_j4_go_j8"),
    (30, 3, 5, "p38_j7_go_j8"),
):
    add(run(38, number, first, last, F, key, routes=(J_ROUTE,)))
add(*question(38, ("line", 36), "p38_j10_lifetime_years", routes=(J_ROUTE,)))
add(run(38, 36, 7, 7, R, "p38_role_wife", routes=(J_ROUTE,)))
add(run(38, 37, 2, 7, F, "p38_j10_none_turn_k1", routes=(J_ROUTE,)))
add(*question(38, ("line", 39), "p38_j11_full_time", routes=(J_ROUTE,)))
add(run(38, 40, 2, 5, F, "p38_j11_all_turn_k1", routes=(J_ROUTE,)))
add(*question(38, ("block", 42, 43), "p38_j12_part_time", routes=(J_ROUTE,)))
add(run(38, 46, 0, 2, F, "p38_j12_turn_k1", routes=(J_ROUTE,)))

add(line(39, 3, F, "p39_section_k"))
add(run(39, 8, 0, 6, F, "p39_k1_same_head", routes=(K,)))
add(
    run(
        39,
        25,
        4,
        7,
        J,
        "p39_job_first_full_time",
        routes=(K,),
    )
)
add(run(39, 25, 3, 3, R, "p39_role_head", routes=(K,)))
add(
    *question(
        39,
        ("line", 25),
        "p39_k4_first_occupation",
        parents=("p39_job_first_full_time",),
        routes=(K,),
    )
)
add(block(39, 27, 28, F, "p39_k4_never_go_k6", routes=(K,)))
add(run(39, 36, 1, 4, F, "p39_k6_go_k9", routes=(K,)))
add(run(39, 47, 1, 4, F, "p39_k9_turn_k11", routes=(K,)))

add(
    *question(
        41,
        ("run", 2, 0, 11),
        "p41_k25_lifetime_years",
        routes=(K,),
    )
)
add(run(41, 2, 6, 6, R, "p41_role_head", routes=(K,)))
add(run(41, 4, 2, 6, F, "p41_k25_none_go_k28", routes=(K,)))
add(*question(41, ("line", 6), "p41_k26_full_time", routes=(K,)))
add(run(41, 8, 2, 5, F, "p41_k26_all_go_k28", routes=(K,)))
add(*question(41, ("block", 10, 11), "p41_k27_part_time", routes=(K,)))
add(run(41, 27, 0, 2, F, "p41_k29_go_k31", routes=(K,)))


def _validate_scope() -> None:
    if set(PAGE_NOTES) != set(range(1, PAGE_COUNT + 1)):
        raise SpecError("page review notes do not cover every page")
    keys = [row["key"] for row in ROWS]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise SpecError(f"duplicate reviewer keys: {duplicates}")


def author_review() -> dict[str, Any]:
    _validate_scope()
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]

    resolved: dict[str, dict[str, Any]] = {}
    for row in ROWS:
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
        if not paths:
            raise SpecError(f"{row['key']} has no applicable path")
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
            # A multi-parent printed label emits one semantic occurrence and
            # branch per applicable parent path.  This document's multi-parent
            # labels are terminal routing atoms, so only singular labels need
            # a shorthand key for use as a later parent.
            if len(paths) == 1:
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
                    page_text, row["utf8_byte_start"]
                ),
                "parent_review_occurrence_ids": parents,
                "parent_resolution_note": (
                    "Printed parent job or aggregate is named in the local "
                    "questionnaire context."
                    if parents
                    else "No printed parent is assigned locally; parenting "
                    "is deferred to global assembly."
                ),
                "classification_status": "provisional_document_local",
            }
        )

    repeat_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        if row["kind"] != A:
            continue
        repeat_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "relation": row["relation"],
                "alias_anchor_review_occurrence_ids": [],
                "canonical_anchor_review_occurrence_ids": [],
                "evidence_review_occurrence_ids": [
                    row["review_occurrence_id"]
                ],
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
            "whole_page_review": (
                "all_42_pages_including_empty_occurrence_pages"
            ),
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
        f"document 22 source review: {len(review['occurrence_specs'])} "
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
