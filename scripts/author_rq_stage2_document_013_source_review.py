#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 13.

The authenticated source is the 62-page 1974 family question-by-question
manual, ``fam1974_QxQs.pdf``.  Every exact Poppler 26.04.0 UTF-8 page was read
before this ledger was written.  The stage-1 candidate artifact is never
opened here; candidates enter only after the completed source ledger exists.

Printed instrument screens and interviewer-objective sheets alternate.  The
retained source domain is employment attachment, exact job and occupation or
industry identity, work exposure, pay components, farm and business
aggregates, role and family-member income sources, and lifetime work history.
Question-by-question prose is retained when it defines the purpose or boundary
of one of those fields.  Transportation, housing, commuting, child care, food,
housework, education, health, observation, and free-standing mobility prose
remain out of scope even when they contain worklike words.

Exact named reuse, cross-reference, repeat, and no-double-count instructions
involving retained fields are preserved as repeat/alias evidence.  A job noun
is retained only where it establishes a measured job or supplies exact local
attachment evidence; generic examples do not mint jobs.  OCR-destroyed or
physically split routing labels are never reconstructed.  No global job,
component, alias, relationship, hierarchy, inventory, or authority IDs are
assigned in this document-local shard.
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
import build_rq_stage2_document_013_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 62


def _line_rows(page_text: str) -> list[dict[str, Any]]:
    return stage1._physical_lines(page_text)


def _utf8(page_text: str, char_start: int, char_end: int) -> tuple[int, int]:
    return (
        len(page_text[:char_start].encode("utf-8")),
        len(page_text[:char_end].encode("utf-8")),
    )


class SpecError(ValueError):
    """Raised when a reviewer selector no longer resolves in source bytes."""


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


def resolve_from(
    page_text: str,
    line_number: int,
    needle: str,
    last_line: int,
    occurrence: int = 0,
) -> tuple[int, int]:
    start, _ = resolve_needle(page_text, line_number, needle, occurrence)
    return start, resolve_line(page_text, last_line)[1]


def resolve_span(
    page_text: str,
    first_line: int,
    first_needle: str,
    last_line: int,
    last_needle: str,
    first_occurrence: int = 0,
    last_occurrence: int = 0,
) -> tuple[int, int]:
    start, _ = resolve_needle(
        page_text, first_line, first_needle, first_occurrence
    )
    _, end = resolve_needle(page_text, last_line, last_needle, last_occurrence)
    if start >= end:
        raise SpecError(
            f"span {first_line}:{first_needle!r} through "
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
    if mode == "from":
        return resolve_from(
            page_text,
            selector[1],
            selector[2],
            selector[3],
            selector[4],
        )
    if mode == "span":
        return resolve_span(
            page_text,
            selector[1],
            selector[2],
            selector[3],
            selector[4],
            selector[5],
            selector[6],
        )
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
        page, kind, ("needle", number, needle, occurrence), key, **rest
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
    return spec(page, kind, ("tail", number, needle, occurrence), key, **rest)


def from_word(
    page: int,
    number: int,
    needle: str,
    last_line: int,
    kind: str,
    key: str,
    occurrence: int = 0,
    **rest: Any,
):
    return spec(
        page,
        kind,
        ("from", number, needle, last_line, occurrence),
        key,
        **rest,
    )


def span_words(
    page: int,
    first_line: int,
    first_needle: str,
    last_line: int,
    last_needle: str,
    kind: str,
    key: str,
    first_occurrence: int = 0,
    last_occurrence: int = 0,
    **rest: Any,
):
    return spec(
        page,
        kind,
        (
            "span",
            first_line,
            first_needle,
            last_line,
            last_needle,
            first_occurrence,
            last_occurrence,
        ),
        key,
        **rest,
    )


def paired(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    *,
    anchor_kind: str = C,
    parents: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
    note: str = "",
    parent_note: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Emit one exact source anchor and its one-to-one purpose prompt."""

    return (
        spec(
            page,
            anchor_kind,
            selector,
            key,
            parents=parents,
            routes=routes,
            note=note,
            parent_note=parent_note,
        ),
        spec(
            page,
            P,
            selector,
            f"{key}_prompt",
            routes=routes,
            note="Exact printed prompt for the retained source field.",
        ),
    )


_REJECTED = (
    "Every Poppler text line on page {page} was reviewed. The page prints "
    "{scope}, outside the retained employment, work-income, and work-history "
    "domain; worklike prose is not an occurrence."
)
_RETAINED = (
    "Every Poppler text line on page {page} was reviewed. The page prints "
    "{scope}; exact locatable source atoms are retained and all other prose "
    "is rejected."
)
_OBJECTIVES = (
    "Every Poppler text line on page {page} was reviewed. This is "
    "question-by-question interviewer commentary for {scope}; exact listed "
    "purpose, boundary, reuse, repeat, and cross-reference atoms are retained "
    "and unrelated prose is rejected."
)

_PAGE_SCOPE: dict[int, tuple[str, str]] = {
    1: ("out", "the question-by-question objectives title and child prose"),
    2: ("out", "the cover and section A child items"),
    3: ("out", "section B transportation items"),
    4: ("objectives", "section B transportation items"),
    5: ("out", "section C housing and moving items"),
    6: ("objectives", "section C housing items"),
    7: ("objectives", "section C moving items"),
    8: ("out", "an explicit blank-page marker"),
    9: ("in", "section D head employment items D1-D10"),
    10: ("objectives", "section D employment-status assignment items"),
    11: ("objectives", "occupation and industry items D2-D5"),
    12: ("objectives", "tenure and prior-job items D6-D10"),
    13: ("in", "head work-exposure and hourly-pay items D11-D24"),
    14: ("objectives", "head work-exposure and hourly-pay items"),
    15: ("in", "head extra-job items D25-D30 and rejected labor-supply items"),
    16: ("objectives", "head extra-job and labor-supply items"),
    17: (
        "in",
        "rejected commuting items and the retained D38 job-change item",
    ),
    18: ("objectives", "commuting and contemplated-job-change items"),
    19: ("in", "section E sought-job, last-job, and work-time items"),
    20: ("objectives", "section E sought-job and last-job items"),
    21: (
        "in",
        "rejected commuting plus retained unacceptable-job and pay items",
    ),
    22: ("objectives", "rejected commuting plus retained pay-threshold items"),
    23: ("in", "section F actual-work and sought-job items"),
    24: ("objectives", "section F actual-work and sought-job items"),
    25: ("in", "section G wife employment items G1-G12"),
    26: ("objectives", "section G wife employment items"),
    27: ("in", "wife lifetime-work and child-care entry items"),
    28: ("objectives", "wife work history and child-care items"),
    29: ("in", "head lifetime-work items and food items"),
    30: ("objectives", "head work history and food items"),
    31: ("out", "food, housework, and household-help items"),
    32: ("objectives", "food and housework items"),
    33: ("in", "section H farm, business, and head-wage items"),
    34: ("objectives", "section H farm and business items"),
    35: ("objectives", "business and head-wage items"),
    36: ("out", "an explicit blank-page marker"),
    37: ("in", "head work-income and other-income items H9-H13"),
    38: ("objectives", "head work-income and other-income items H9-H11"),
    39: (
        "objectives",
        "H11 trust, royalty, welfare, and Social Security sources",
    ),
    40: ("objectives", "H11 retirement and compensation sources"),
    41: ("objectives", "H11 remaining sources and H12-H13 family help"),
    42: ("out", "an explicit blank-page marker"),
    43: ("in", "wife income-source and amount items H17-H20"),
    44: ("objectives", "welfare and wife-income items"),
    45: ("in", "other-family-member income items H21-H31"),
    46: ("objectives", "other-family-member income items"),
    47: ("in", "three repeated other-family-member income columns"),
    48: ("objectives", "the repeated other-family-member grid"),
    49: (
        "in",
        "retained other-member income and H34-H35 money, then rejected support items",
    ),
    50: ("objectives", "transfers and support items"),
    51: ("in", "new-wife education and section K new-head routing"),
    52: ("objectives", "new-wife education and new-head routing"),
    53: ("in", "new-head first-job work-history and background items"),
    54: ("objectives", "new-head first-job and background items"),
    55: ("out", "mobility, education, and veteran items"),
    56: ("objectives", "mobility, education, and veteran items"),
    57: ("out", "work-limiting health items"),
    58: ("objectives", "work-limiting health items"),
    59: ("out", "interviewer-observation items"),
    60: ("objectives", "interviewer-observation items"),
    61: ("out", "the thumbnail-sketch title"),
    62: ("out", "thumbnail-sketch instructions"),
}

PAGE_NOTES = {
    page: {"out": _REJECTED, "in": _RETAINED, "objectives": _OBJECTIVES}[
        mode
    ].format(page=page, scope=scope)
    for page, (mode, scope) in _PAGE_SCOPE.items()
}

_DEFAULT_NOTES = {
    F: "Exact locatable printed routing atom retained with reviewed ancestry.",
    R: "Exact printed role lexeme retained as local role attachment evidence.",
    J: "Exact establishing printed job noun retained without global merging.",
    M: "Exact printed remuneration component retained from source bytes.",
    T: "Exact printed role-total remuneration anchor retained.",
    FA: "Exact printed farm aggregate anchor retained.",
    BA: "Exact printed business aggregate anchor retained.",
    C: "Exact printed contextual field retained for a defined purpose.",
    P: "Exact printed question prompt retained for its source field.",
    A: "Exact printed repeat or cross-reference instruction retained.",
}

XREF = "explicit_cross_reference"
REPEAT = "explicit_repeat_instruction"


def _xref(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    alias: Sequence[str],
    canonical: Sequence[str],
    note: str,
    *,
    target_scope: str = "document_local",
    resolution_status: str = "document_local_source_evidence_complete",
    routes: Sequence[Sequence[str]] = ((),),
) -> dict[str, Any]:
    return spec(
        page,
        A,
        selector,
        key,
        note=note,
        relation=XREF,
        alias=tuple(alias),
        canonical=tuple(canonical),
        evidence=tuple(alias) + tuple(canonical),
        target_scope=target_scope,
        resolution_status=resolution_status,
        routes=routes,
    )


def _unresolved_repeat(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    note: str,
    *,
    relation: str = REPEAT,
    alias: Sequence[str] = (),
    routes: Sequence[Sequence[str]] = ((),),
) -> dict[str, Any]:
    return spec(
        page,
        A,
        selector,
        key,
        note=note,
        relation=relation,
        alias=tuple(alias),
        evidence=tuple(alias),
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        routes=routes,
    )


def _repeat_relation(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    alias: Sequence[str],
    canonical: Sequence[str],
    note: str,
    *,
    routes: Sequence[Sequence[str]] = ((),),
) -> dict[str, Any]:
    return spec(
        page,
        A,
        selector,
        key,
        note=note,
        relation=REPEAT,
        alias=tuple(alias),
        canonical=tuple(canonical),
        evidence=tuple(alias) + tuple(canonical),
        target_scope="document_local",
        resolution_status="document_local_source_evidence_complete",
        routes=routes,
    )


SEC_D = ("p9_flow_section_d",)
D6_LONG = SEC_D + ("p9_flow_d6_long",)
D6_SHORT = SEC_D + ("p9_flow_d6_short",)
D9_WORSE = D6_SHORT + ("p9_flow_d9_worse",)
D11_YES = SEC_D + ("p13_flow_d11_yes",)
D13_YES = SEC_D + ("p13_flow_d13_yes",)
D15_YES = SEC_D + ("p13_flow_d15_yes",)
D19_YES = SEC_D + ("p13_flow_d19_yes",)
D23_HOURLY = SEC_D + ("p13_flow_d23_yes",)
D25_YES = SEC_D + ("p15_flow_d25_yes",)
SEC_E = ("p19_flow_section_e",)
E9_WORKED = SEC_E + ("p19_flow_e9_worked",)
SEC_F = ("p23_flow_section_f",)
F2_YES = SEC_F + ("p23_flow_f2_yes",)
F7_YES = SEC_F + ("p23_flow_f7_yes",)
F8_FROM_F2 = F2_YES + ("p23_flow_f2_or_f7",)
F8_FROM_F7 = F7_YES + ("p23_flow_f2_or_f7",)
SEC_G = ("p25_flow_section_g",)
G_MARRIED = SEC_G + ("p25_flow_g1_married",)
G_WIFE_OCCUPATION = G_MARRIED + ("p25_flow_wife_occupation_scope",)
G2_NO = G_MARRIED + ("p25_flow_g2_no",)
SEC_H = ("p33_flow_section_h",)
H_FARMER = SEC_H + ("p33_flow_h1_farmer",)
H_NOT_FARMER = SEC_H + ("p33_flow_h1_not_farmer",)
H_CORPORATION = SEC_H + ("p33_flow_h6_corporation",)
H_UNINCORPORATED = SEC_H + ("p33_flow_h6_unincorporated",)
H_BOTH = SEC_H + ("p33_flow_h6_both",)
H_DONT_KNOW = SEC_H + ("p33_flow_h6_dont_know",)
H11_ANY = SEC_H + ("p37_flow_h11_yes_to_any",)
H12_YES = SEC_H + ("p37_flow_h12_yes",)
H14_WELFARE = SEC_H + ("p43_flow_h14_welfare",)
H15_YES = H14_WELFARE + ("p43_flow_h15_yes",)
H_WIFE = SEC_H + ("p43_flow_h17_wife",)
H_NO_WIFE = SEC_H + ("p43_flow_h17_no_wife",)
H18_YES = H_WIFE + ("p43_flow_h18_yes",)
H22_YES = SEC_H + ("p45_flow_h22_yes",)
H24_WORK = H22_YES + ("p45_flow_h24_wages_business",)
H29_YES = H22_YES + ("p45_flow_h29_yes",)
H32_YES = SEC_H + ("p49_flow_h32_yes",)
H34_YES = SEC_H + ("p49_flow_h34_yes",)
SEC_K = ("p51_flow_section_k",)
K_NEW_HEAD = SEC_K + ("p51_flow_k1_new_head",)
K_SAME_HEAD = SEC_K + ("p51_flow_k1_same_head",)
K4_NEVER = K_NEW_HEAD + ("p53_flow_k4_never",)

_PRESENT_JOB_PARENT = "Parent job is D1's printed present-job noun."
_PREVIOUS_JOB_PARENT = "Parent job is D7's distinct previous-job noun."
_MAIN_JOB_PARENT = "Parent job is D17's printed main-job noun."
_EXTRA_JOB_PARENT = "Parent job is D25's printed extra-jobs noun."
_SOUGHT_JOB_PARENT = "Parent job is the printed sought-job noun."
_LAST_JOB_PARENT = "Parent job is E6's printed last-job noun."
_FIRST_JOB_PARENT = "Parent job is K4's printed first-full-time-job noun."
_FARM_PARENT = "Parent aggregate is the printed net-farm-income anchor."
_BUSINESS_PARENT = (
    "Parent aggregate is the printed unincorporated-business anchor."
)


PAGE_9 = (
    tail(9, 1, "SECTION D:", F, "p9_flow_section_d"),
    *paired(
        9,
        ("block", 3, 4),
        "p9_d1_employment_status",
        note="D1 prints the head's current employment-status assignment.",
    ),
    word(9, 3, "(HEAD)", R, "p9_role_head_d1"),
    word(9, 3, "present Job", J, "p9_job_present"),
    word(
        9,
        8,
        "(TURN TO El, PAGE 8)",
        F,
        "p9_flow_d1_looking_exit",
        routes=(SEC_D,),
    ),
    word(
        9,
        9,
        "[3 . PERMANENTLY DISABL]ill]",
        F,
        "p9_flow_d1_disabled",
        routes=(SEC_D,),
    ),
    word(
        9, 10, "14 . HOUSEi.JIFEj", F, "p9_flow_d1_housewife", routes=(SEC_D,)
    ),
    word(9, 12, "Is . STUDENT I", F, "p9_flow_d1_student", routes=(SEC_D,)),
    from_word(
        9,
        13,
        "j6 . OTHERj",
        17,
        F,
        "p9_flow_d1_other",
        routes=(SEC_D,),
    ),
    *paired(
        9,
        ("line", 18),
        "p9_d2_occupation",
        parents=("p9_job_present",),
        routes=(SEC_D,),
        note="D2 prints the main occupation of the present job.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(
        9, 18, "main occupation", J, "p9_job_main_occupation", routes=(SEC_D,)
    ),
    word(9, 23, "(IF NOT CLEAR)", F, "p9_flow_d3_probe", routes=(SEC_D,)),
    *paired(
        9,
        ("block", 23, 24),
        "p9_d3_occupation_detail",
        parents=("p9_job_present",),
        routes=(SEC_D,),
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 29),
        "p9_d4_industry",
        parents=("p9_job_present",),
        routes=(SEC_D,),
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 32),
        "p9_d5_employee_self",
        parents=("p9_job_present",),
        routes=(SEC_D,),
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 35),
        "p9_d6_job_tenure",
        parents=("p9_job_present",),
        routes=(SEC_D,),
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(9, 35, "this job", J, "p9_job_tenure_noun", routes=(SEC_D,)),
    line(9, 37, F, "p9_flow_d6_long", routes=(SEC_D,)),
    line(9, 39, F, "p9_flow_d6_short", routes=(SEC_D,)),
    *paired(
        9,
        ("block", 41, 42),
        "p9_d7_previous_job_outcome",
        parents=("p9_job_previous",),
        routes=(D6_SHORT,),
        parent_note=_PREVIOUS_JOB_PARENT,
    ),
    word(
        9,
        41,
        "the job you had before",
        J,
        "p9_job_previous",
        routes=(D6_SHORT,),
    ),
    *paired(
        9,
        ("line", 47),
        "p9_d8_relative_pay",
        parents=("p9_job_present", "p9_job_previous"),
        routes=(D6_SHORT,),
        note="D8 prints a qualitative present-versus-previous-job pay comparison.",
        parent_note="The exact question names both compared jobs.",
    ),
    *paired(
        9,
        ("block", 50, 51),
        "p9_d9_job_comparison",
        parents=("p9_job_present", "p9_job_previous"),
        routes=(D6_SHORT,),
        parent_note="The exact question names both compared jobs.",
    ),
    word(9, 52, "5. WORSE", F, "p9_flow_d9_worse", routes=(D6_SHORT,)),
    tail(9, 52, "3 . SAME", F, "p9_flow_d9_same_exit", routes=(D6_SHORT,)),
    *paired(9, ("line", 55), "p9_d10_comparison_reason", routes=(D9_WORSE,)),
)


PAGE_10 = (
    *paired(10, ("block", 14, 16), "p10_d_sequence_role_scope"),
    word(10, 14, "head of the household", R, "p10_role_head_scope"),
    line(10, 18, F, "p10_flow_working_definition"),
    *paired(10, ("block", 19, 24), "p10_working_definition"),
    line(10, 26, F, "p10_flow_looking_definition"),
    *paired(10, ("block", 27, 31), "p10_looking_definition"),
    line(10, 33, F, "p10_flow_out_of_labor_force_definition"),
    *paired(10, ("block", 34, 40), "p10_out_of_labor_force_definition"),
)


PAGE_11 = (
    *paired(11, ("line", 4), "p11_d2_d3_role_scope"),
    word(11, 4, "head of the family", R, "p11_role_head_scope"),
    *paired(11, ("block", 6, 9), "p11_occupation_skill_purpose"),
    word(
        11,
        9,
        "white-collar occupations",
        J,
        "p11_job_white_collar_occupations",
    ),
    *paired(11, ("block", 10, 12), "p11_occupation_place_purpose"),
    word(11, 10, "head", R, "p11_role_head_workplace"),
    *paired(11, ("block", 13, 18), "p11_job_title_precision_purpose"),
    word(11, 13, "job titles", J, "p11_job_titles"),
    *paired(11, ("block", 25, 26), "p11_d3_probe_purpose"),
    *paired(11, ("block", 29, 39), "p11_d4_industry_purpose"),
    word(11, 30, "particular occupation", J, "p11_job_particular_occupation"),
    *paired(11, ("line", 47), "p11_d5_required_classification"),
)


PAGE_12 = (
    *paired(12, ("block", 6, 7), "p12_d6_employer_tenure_purpose"),
    word(12, 6, "present employer", J, "p12_job_present_employer"),
    *paired(12, ("block", 10, 16), "p12_d7_previous_job_purpose"),
    word(12, 15, "head•s", R, "p12_role_head_first_job"),
    word(12, 15, "first job", J, "p12_job_first"),
    *paired(12, ("block", 19, 20), "p12_d8_d10_change_purpose"),
    word(12, 19, "change in jobs", J, "p12_job_change"),
)


PAGE_13 = (
    *paired(
        13,
        ("line", 17),
        "p13_d15_unemployment_strike",
        routes=(SEC_D,),
        note="D15 prints unemployment-or-strike work absence.",
    ),
    word(13, 19, "1. YES I", F, "p13_flow_d15_yes", routes=(SEC_D,)),
    tail(13, 21, "5 . NOt", F, "p13_flow_d15_no_exit", routes=(SEC_D,)),
    *paired(
        13,
        ("line", 19),
        "p13_d16_unemployment_duration",
        routes=(D15_YES,),
    ),
    *paired(
        13,
        ("line", 24),
        "p13_d17_weeks_main_job",
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 24, "main job", J, "p13_job_main", routes=(SEC_D,)),
    *paired(
        13,
        ("block", 27, 28),
        "p13_d18_hours_main_job",
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("line", 31),
        "p13_d19_overtime_presence",
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        13,
        31,
        "overtime",
        M,
        "p13_d19_overtime_component",
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 33, "[ ] YES", F, "p13_flow_d19_yes", routes=(SEC_D,)),
    tail(13, 33, "[ ] NO", F, "p13_flow_d19_no_exit", routes=(SEC_D,)),
    *paired(
        13,
        ("line", 36),
        "p13_d20_overtime_hours",
        parents=("p13_job_main",),
        routes=(D19_YES,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("block", 40, 41),
        "p13_d21_extra_hours_pay",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("needle", 46, "D22. What would be your hourly rate", 0),
        "p13_d22_overtime_rate",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("needle", 46, "D23. Do you have an hourly wage rate", 0),
        "p13_d23_hourly_status",
        parents=("p13_job_main",),
        routes=(SEC_D,),
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 49, "I 1 . YES J", F, "p13_flow_d23_yes", routes=(SEC_D,)),
    from_word(
        13,
        49,
        "5 . NO",
        50,
        F,
        "p13_flow_d23_no_exit",
        routes=(SEC_D,),
    ),
    *paired(
        13,
        ("line", 53),
        "p13_d24_regular_hourly_rate",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=(D23_HOURLY,),
        parent_note=_MAIN_JOB_PARENT,
    ),
)


PAGE_14 = (
    *paired(14, ("block", 4, 6), "p14_employment_year_accounting"),
    word(14, 4, "head's", R, "p14_role_head_accounting"),
    word(14, 6, "main job", J, "p14_job_main_accounting"),
    *paired(14, ("block", 22, 24), "p14_unemployment_definition"),
    word(14, 24, "main job", J, "p14_job_main_unemployment"),
    *paired(14, ("block", 27, 28), "p14_full_year_check"),
    *paired(14, ("block", 31, 35), "p14_main_job_overtime_definition"),
    word(14, 31, "main job", J, "p14_job_main_overtime"),
    *paired(
        14,
        ("block", 38, 43),
        "p14_fixed_and_overtime_pay",
        anchor_kind=M,
    ),
    word(14, 38, "head•s", R, "p14_role_head_income"),
    *paired(14, ("block", 46, 48), "p14_hourly_rate_check", anchor_kind=M),
    *paired(14, ("block", 51, 52), "p14_hourly_salary_basis", anchor_kind=M),
)


PAGE_15 = (
    *paired(
        15,
        ("block", 2, 3),
        "p15_d25_extra_jobs",
        parents=("p15_job_extra", "p13_job_main"),
        routes=(SEC_D,),
        parent_note="The question names both the extra-jobs source and main job.",
    ),
    word(15, 2, "extra jobs", J, "p15_job_extra", routes=(SEC_D,)),
    word(15, 3, "main job", J, "p15_job_main_reference", routes=(SEC_D,)),
    word(15, 5, "1. YES I", F, "p15_flow_d25_yes", routes=(SEC_D,)),
    tail(15, 5, "5. NO I", F, "p15_flow_d25_no_exit", routes=(SEC_D,)),
    *paired(
        15,
        ("line", 8),
        "p15_d26_occupation",
        parents=("p15_job_extra",),
        routes=(D25_YES,),
        parent_note=_EXTRA_JOB_PARENT,
    ),
    line(15, 13, P, "p15_d27_anything_else_prompt", routes=(D25_YES,)),
    _unresolved_repeat(
        15,
        ("line", 13),
        "p15_d27_anything_else_repeat",
        "D27 explicitly asks for another extra-work source; the repeated endpoint "
        "is preserved for global resolution.",
        routes=(D25_YES,),
    ),
    *paired(
        15,
        ("block", 15, 16),
        "p15_d28_extra_hourly_rate",
        anchor_kind=M,
        parents=("p15_job_extra",),
        routes=(D25_YES,),
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        15,
        ("line", 17),
        "p15_d29_extra_weeks",
        parents=("p15_job_extra",),
        routes=(D25_YES,),
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        15,
        ("line", 19),
        "p15_d30_extra_hours",
        parents=("p15_job_extra",),
        routes=(D25_YES,),
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        15,
        ("block", 24, 25),
        "p15_d31_work_availability",
        parents=("p9_job_present", "p15_job_extra"),
        routes=(SEC_D,),
        parent_note="D31 explicitly names the current job or jobs.",
    ),
    word(15, 27, "I 1. YES I", F, "p15_flow_d31_yes_exit", routes=(SEC_D,)),
    word(
        15,
        27,
        "I 5. NO OR DON'T KNOW I",
        F,
        "p15_flow_d31_no",
        routes=(SEC_D,),
    ),
)


PAGE_16 = (
    *paired(16, ("block", 5, 6), "p16_d25_job_boundary"),
    word(16, 5, "second jobs", J, "p16_job_second"),
    span_words(
        16,
        5,
        "main",
        6,
        "job",
        J,
        "p16_job_main_previous_phrase",
    ),
    word(16, 6, "head's", R, "p16_role_head_current_employment"),
    *paired(
        16,
        ("block", 7, 14),
        "p16_d25_extra_income_scope",
        anchor_kind=M,
    ),
    word(16, 7, "irregular jobs", J, "p16_job_irregular"),
    *paired(
        16,
        ("block", 20, 23),
        "p16_d28_hourly_pay_purpose",
        anchor_kind=M,
    ),
    word(16, 22, "extra job", J, "p16_job_extra_rate"),
    *paired(16, ("block", 26, 29), "p16_d29_d30_time_purpose"),
    *paired(16, ("block", 32, 35), "p16_d31_availability_purpose"),
    word(16, 32, "head", R, "p16_role_head_availability"),
    word(16, 33, "present job(s)", J, "p16_job_present_availability"),
)


PAGE_17 = (
    *paired(17, ("block", 17, 18), "p17_d38_job_intention", routes=(SEC_D,)),
    word(17, 17, "new job", J, "p17_job_new", routes=(SEC_D,)),
    span_words(
        17,
        17,
        "job you",
        18,
        "have now",
        J,
        "p17_job_current",
        routes=(SEC_D,),
    ),
)


PAGE_18 = (
    *paired(18, ("block", 25, 26), "p18_d38_new_job_definition"),
    word(18, 25, "new job", J, "p18_job_new"),
    word(18, 25, "same employer", J, "p18_job_same_employer"),
    word(18, 25, "different employer", J, "p18_job_different_employer"),
)


PAGE_19 = (
    tail(19, 1, "SECTION E:", F, "p19_flow_section_e"),
    *paired(19, ("line", 4), "p19_e1_sought_job", routes=(SEC_E,)),
    word(19, 4, "job", J, "p19_job_sought", routes=(SEC_E,)),
    *paired(
        19,
        ("line", 9),
        "p19_e2_expected_earnings",
        anchor_kind=M,
        parents=("p19_job_sought",),
        routes=(SEC_E,),
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    *paired(
        19,
        ("line", 12),
        "p19_e3_training",
        parents=("p19_job_sought",),
        routes=(SEC_E,),
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    *paired(19, ("line", 17), "p19_e4_search_action", routes=(SEC_E,)),
    tail(19, 18, "5. NOTHING", F, "p19_flow_e4_nothing", routes=(SEC_E,)),
    *paired(19, ("line", 21), "p19_e5_search_places", routes=(SEC_E,)),
    *paired(
        19,
        ("line", 26),
        "p19_e6_last_job_occupation",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    word(19, 26, "last job", J, "p19_job_last", routes=(SEC_E,)),
    *paired(
        19,
        ("line", 29),
        "p19_e7_last_job_industry",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        19,
        ("block", 32, 33),
        "p19_e8_last_job_outcome",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        19,
        ("line", 38),
        "p19_e9_weeks_worked",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    tail(19, 38, "~0. NONE I", F, "p19_flow_e9_none", routes=(SEC_E,)),
    *paired(
        19,
        ("line", 41),
        "p19_e10_hours_worked",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(19, ("line", 43), "p19_e11_sick_weeks", routes=(SEC_E,)),
    *paired(19, ("line", 46), "p19_e12_unemployed_weeks", routes=(SEC_E,)),
)


PAGE_20 = (
    *paired(20, ("block", 5, 6), "p20_e1_occupation_purpose", routes=(SEC_E,)),
    *paired(
        20,
        ("line", 9),
        "p20_e2_pay_period_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
    *paired(20, ("block", 12, 13), "p20_e3_training_purpose", routes=(SEC_E,)),
    *paired(20, ("block", 17, 18), "p20_e4_search_purpose", routes=(SEC_E,)),
    *paired(20, ("block", 23, 24), "p20_e5_places_purpose", routes=(SEC_E,)),
    *paired(20, ("line", 44), "p20_e9_weeks_purpose", routes=(SEC_E,)),
    *paired(20, ("block", 47, 48), "p20_e10_hours_purpose", routes=(SEC_E,)),
    word(20, 47, "head", R, "p20_role_head_schedule", routes=(SEC_E,)),
    *paired(20, ("block", 50, 53), "p20_e11_sick_purpose", routes=(SEC_E,)),
    *paired(20, ("block", 54, 55), "p20_e12_year_check", routes=(SEC_E,)),
)


E19_YES = SEC_E + ("p21_flow_e19_yes",)

PAGE_21 = (
    *paired(
        21, ("line", 24), "p21_e17_jobs_not_worth_taking", routes=(SEC_E,)
    ),
    word(21, 24, "jobs available", J, "p21_job_available", routes=(SEC_E,)),
    tail(21, 29, "I 5. NO I", F, "p21_flow_e17_no_exit", routes=(SEC_E,)),
    *paired(
        21,
        ("line", 31),
        "p21_e18_unacceptable_pay",
        anchor_kind=M,
        parents=("p21_job_available",),
        routes=(SEC_E,),
        parent_note="The amount applies to E17's jobs-available source.",
    ),
    *paired(
        21, ("block", 33, 34), "p21_e19_good_job_mobility", routes=(SEC_E,)
    ),
    word(21, 34, "job there", J, "p21_job_good_mobility", routes=(SEC_E,)),
    word(
        21,
        36,
        "[1. YES, MAYBE, OR DEPENDS",
        F,
        "p21_flow_e19_yes",
        routes=(SEC_E,),
    ),
    *paired(
        21,
        ("needle", 38, "E20. How much would a job have", 0),
        "p21_e20_required_pay",
        anchor_kind=M,
        parents=("p21_job_good_mobility",),
        routes=(E19_YES,),
        parent_note="The amount applies to the exact good-job mobility source.",
    ),
)


PAGE_22 = (
    *paired(
        22,
        ("block", 25, 28),
        "p22_e17_e18_unacceptable_pay_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
    span_words(
        22,
        26,
        "jobs in the",
        27,
        "area",
        J,
        "p22_job_jobs_in_area",
        routes=(SEC_E,),
    ),
    *paired(
        22,
        ("block", 35, 37),
        "p22_e20_pay_period_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
)


PAGE_23 = (
    tail(23, 1, "SECTION F:", F, "p23_flow_section_f"),
    *paired(
        23,
        ("line", 4),
        "p23_f1_work_for_money",
        anchor_kind=M,
        routes=(SEC_F,),
    ),
    word(23, 4, "(HEAD)", R, "p23_role_head_f1", routes=(SEC_F,)),
    word(
        23, 4, "work for money", J, "p23_job_work_for_money", routes=(SEC_F,)
    ),
    *paired(23, ("line", 8), "p23_f2_future_work", routes=(SEC_F,)),
    word(23, 10, "1 . YES", F, "p23_flow_f2_yes", routes=(SEC_F,)),
    tail(23, 10, "5. NO I", F, "p23_flow_f2_no_exit", routes=(SEC_F,)),
    *paired(23, ("line", 14), "p23_f3_occupation", routes=(SEC_F,)),
    word(
        23, 14, "occupation", J, "p23_job_actual_occupation", routes=(SEC_F,)
    ),
    *paired(
        23,
        ("line", 18),
        "p23_f4_industry",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(
        23,
        ("line", 22),
        "p23_f5_weeks_worked",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(
        23,
        ("line", 24),
        "p23_f6_hours_worked",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(23, ("line", 26), "p23_f7_new_job", routes=(SEC_F,)),
    word(23, 26, "new job", J, "p23_job_new", routes=(SEC_F,)),
    word(23, 27, "I l. YES I", F, "p23_flow_f7_yes", routes=(SEC_F,)),
    tail(23, 27, "I 5. NO I", F, "p23_flow_f7_no_exit", routes=(SEC_F,)),
    line(
        23,
        29,
        F,
        "p23_flow_f2_or_f7",
        routes=(F2_YES, F7_YES),
        note="Exact multiparent condition printed for affirmative F2 or F7.",
    ),
    *paired(
        23,
        ("line", 31),
        "p23_f8_job_in_mind",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    word(
        23,
        31,
        "job do you have in mind",
        J,
        "p23_job_in_mind",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        23,
        ("line", 35),
        "p23_f9_expected_earnings",
        anchor_kind=M,
        parents=("p23_job_in_mind",),
        routes=(F8_FROM_F2, F8_FROM_F7),
        parent_note="F8's job-in-mind noun is the local job parent.",
    ),
    *paired(
        23, ("line", 37), "p23_f10_training", routes=(F8_FROM_F2, F8_FROM_F7)
    ),
    *paired(
        23,
        ("line", 39),
        "p23_f11_search_action",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    tail(
        23,
        41,
        "5 . NOTHING",
        F,
        "p23_flow_f11_nothing",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        23,
        ("block", 43, 44),
        "p23_f12_search_places",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        23,
        ("line", 47),
        "p23_f13_jobs_not_worth_taking",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    word(
        23,
        47,
        "jobs around here",
        J,
        "p23_job_jobs_around_here",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    tail(
        23,
        48,
        "5. NO",
        F,
        "p23_flow_f13_no_exit",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        23,
        ("line", 51),
        "p23_f14_unacceptable_pay",
        anchor_kind=M,
        parents=("p23_job_jobs_around_here",),
        routes=(F8_FROM_F2, F8_FROM_F7),
        parent_note="F13's jobs-around-here noun is the local job parent.",
    ),
)


PAGE_24 = (
    *paired(24, ("block", 7, 9), "p24_f1_money_work_purpose", anchor_kind=M),
    word(24, 7, "heads", R, "p24_role_heads_f1"),
    word(24, 8, "full - time job", J, "p24_job_full_time_prior"),
    *paired(24, ("block", 12, 13), "p24_f2_work_timing_purpose"),
    *paired(24, ("block", 22, 25), "p24_f5_f6_hours_purpose"),
    word(24, 23, "heads", R, "p24_role_heads_hours"),
    *paired(24, ("block", 28, 30), "p24_f7_new_job_definition"),
    word(24, 28, '"New job"', J, "p24_job_new"),
    word(24, 28, "same employer", J, "p24_job_same_employer"),
    *paired(24, ("block", 33, 34), "p24_f8_job_in_mind_purpose"),
    word(24, 34, "job he has in mind", J, "p24_job_in_mind"),
    *paired(24, ("line", 37), "p24_f9_pay_period_purpose", anchor_kind=M),
    *paired(24, ("block", 40, 41), "p24_f10_training_purpose"),
    *paired(24, ("block", 44, 45), "p24_f11_search_purpose"),
    *paired(24, ("block", 48, 49), "p24_f12_places_purpose"),
    *paired(
        24,
        ("block", 52, 55),
        "p24_f13_f14_unacceptable_pay_purpose",
        anchor_kind=M,
    ),
    word(24, 53, "jobs around here", J, "p24_job_jobs_around_here"),
)


PAGE_25 = (
    tail(25, 2, "SECTION G:", F, "p25_flow_section_g"),
    *paired(25, ("line", 6), "p25_g1_marital_status", routes=(SEC_G,)),
    word(25, 8, "[i. MARRIED I", F, "p25_flow_g1_married", routes=(SEC_G,)),
    from_word(
        25,
        10,
        "2. SINGLE",
        12,
        F,
        "p25_flow_g1_nonwife_exit",
        routes=(SEC_G,),
    ),
    line(
        25,
        16,
        F,
        "p25_flow_wife_occupation_scope",
        routes=(G_MARRIED,),
    ),
    word(
        25,
        16,
        "WIFE ' s",
        R,
        "p25_role_wife_scope",
        routes=(G_WIFE_OCCUPATION,),
    ),
    *paired(
        25,
        ("block", 18, 21),
        "p25_g2_wife_work_for_money",
        anchor_kind=M,
        routes=(G_WIFE_OCCUPATION,),
    ),
    word(25, 21, "wife", R, "p25_role_wife_g2", routes=(G_WIFE_OCCUPATION,)),
    word(
        25,
        21,
        "work for money",
        J,
        "p25_job_wife_work",
        routes=(G_WIFE_OCCUPATION,),
    ),
    tail(25, 23, "5 . NO", F, "p25_flow_g2_no", routes=(G_WIFE_OCCUPATION,)),
    *paired(
        25,
        ("line", 25),
        "p25_g3_wife_occupation",
        parents=("p25_job_wife_work",),
        routes=(G_WIFE_OCCUPATION,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        25,
        ("line", 29),
        "p25_g4_wife_industry",
        parents=("p25_job_wife_work",),
        routes=(G_WIFE_OCCUPATION,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        25,
        ("line", 33),
        "p25_g5_wife_weeks",
        parents=("p25_job_wife_work",),
        routes=(G_WIFE_OCCUPATION,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        25,
        ("line", 35),
        "p25_g6_wife_hours",
        parents=("p25_job_wife_work",),
        routes=(G_WIFE_OCCUPATION,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        25,
        ("block", 37, 38),
        "p25_g7_wife_work_availability",
        parents=("p25_job_wife_work",),
        routes=(G_WIFE_OCCUPATION,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    tail(
        25,
        40,
        "I!. YES]",
        F,
        "p25_flow_g7_yes_exit",
        routes=(G_WIFE_OCCUPATION,),
    ),
)


PAGE_26 = (
    *paired(
        26, ("block", 12, 14), "p26_g1_female_head_context", routes=(SEC_G,)
    ),
    word(26, 12, "female head", R, "p26_role_female_head", routes=(SEC_G,)),
    *paired(
        26,
        ("block", 31, 32),
        "p26_g10_wife_new_job_context",
        routes=(G_MARRIED,),
    ),
    word(26, 31, "wife", R, "p26_role_wife_new_job", routes=(G_MARRIED,)),
    word(26, 31, "a job", J, "p26_job_wife_new", routes=(G_MARRIED,)),
)


PAGE_27 = (
    *paired(27, ("line", 2), "p27_g13_wife_career_years", routes=(G_MARRIED,)),
    word(27, 2, "wife", R, "p27_role_wife_career", routes=(G_MARRIED,)),
    *paired(
        27, ("line", 7), "p27_g14_wife_full_time_years", routes=(G_MARRIED,)
    ),
    tail(27, 12, "I ALL I", F, "p27_flow_g14_all_exit", routes=(G_MARRIED,)),
    *paired(
        27,
        ("line", 13),
        "p27_g15_wife_part_time_fraction",
        routes=(G_MARRIED,),
    ),
)


PAGE_29 = (
    *paired(29, ("line", 3), "p29_g22_head_career_years", routes=(SEC_G,)),
    word(29, 3, "(HEAD)", R, "p29_role_head_career", routes=(SEC_G,)),
    tail(29, 5, "00. NONE", F, "p29_flow_g22_none", routes=(SEC_G,)),
    *paired(29, ("line", 7), "p29_g23_head_full_time_years", routes=(SEC_G,)),
    word(29, 7, "(HEAD)", R, "p29_role_head_full_time", routes=(SEC_G,)),
    tail(29, 9, "[A-i.x:-1", F, "p29_flow_g23_all_exit", routes=(SEC_G,)),
    *paired(
        29,
        ("block", 10, 11),
        "p29_g24_head_part_time_fraction",
        routes=(SEC_G,),
    ),
    word(29, 10, "(HEAD)", R, "p29_role_head_part_time", routes=(SEC_G,)),
)


PAGE_30 = (
    *paired(30, ("block", 5, 8), "p30_g24_fraction_purpose", routes=(SEC_G,)),
)


PAGE_33 = (
    tail(33, 2, "SECTION H:", F, "p33_flow_section_h"),
    *paired(33, ("block", 6, 7), "p33_income_preamble", routes=(SEC_H,)),
    *paired(
        33, ("block", 10, 12), "p33_h1_farmer_classification", routes=(SEC_H,)
    ),
    word(
        33,
        12,
        "1. FARMER, OR RANCHER I",
        F,
        "p33_flow_h1_farmer",
        routes=(SEC_H,),
    ),
    word(
        33,
        12,
        "1. FARMER, OR RANCHER",
        FA,
        "p33_farm_classification_aggregate",
        routes=(SEC_H,),
    ),
    tail(
        33,
        12,
        "5. NOT A FARMER OR RANCHER I",
        F,
        "p33_flow_h1_not_farmer",
        routes=(SEC_H,),
    ),
    *paired(
        33,
        ("block", 15, 16),
        "p33_h2_farm_receipts",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    word(33, 15, "farming", FA, "p33_farming_aggregate", routes=(H_FARMER,)),
    *paired(
        33,
        ("block", 18, 20),
        "p33_h3_farm_expenses",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        33,
        ("line", 21),
        "p33_h4_net_farm_income",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    word(
        33,
        21,
        "net income from farming",
        FA,
        "p33_farm_aggregate",
        routes=(H_FARMER,),
    ),
    *paired(
        33, ("block", 25, 26), "p33_h5_business_interest", routes=(SEC_H,)
    ),
    word(
        33,
        25,
        "a business",
        BA,
        "p33_business_interest_aggregate",
        routes=(SEC_H,),
    ),
    tail(33, 28, "s. NO I", F, "p33_flow_h5_no_exit", routes=(SEC_H,)),
    *paired(
        33,
        ("block", 30, 31),
        "p33_h6_business_form",
        parents=("p33_business_aggregate",),
        routes=(SEC_H,),
        parent_note=_BUSINESS_PARENT,
    ),
    word(
        33,
        30,
        "unincorporated business",
        BA,
        "p33_business_aggregate",
        routes=(SEC_H,),
    ),
    tail(
        33,
        35,
        "I 1. CORPORATION I",
        F,
        "p33_flow_h6_corporation",
        routes=(SEC_H,),
    ),
    word(
        33,
        36,
        "I 2. UNINCORPORATED",
        F,
        "p33_flow_h6_unincorporated",
        routes=(SEC_H,),
    ),
    word(33, 37, "I 3. BOTH I", F, "p33_flow_h6_both", routes=(SEC_H,)),
    word(
        33,
        38,
        "I 8. DON'T KNOW I",
        F,
        "p33_flow_h6_dont_know",
        routes=(SEC_H,),
    ),
    *paired(
        33,
        ("block", 39, 42),
        "p33_h7_business_share",
        anchor_kind=M,
        parents=("p33_business_aggregate",),
        routes=(H_UNINCORPORATED, H_BOTH, H_DONT_KNOW),
        parent_note=_BUSINESS_PARENT,
    ),
    *paired(
        33,
        ("block", 47, 48),
        "p33_h8_head_wages_total",
        anchor_kind=T,
        routes=(SEC_H,),
    ),
    word(33, 47, "(HEAD)", R, "p33_role_head_h8", routes=(SEC_H,)),
    word(
        33,
        47,
        "wages and salaries",
        M,
        "p33_h8_wages_component",
        routes=(SEC_H,),
    ),
)


PAGE_34 = (
    *paired(34, ("block", 7, 9), "p34_h1_farmer_definition", routes=(SEC_H,)),
    word(34, 7, "A farmer", FA, "p34_farmer_aggregate", routes=(SEC_H,)),
    *paired(
        34,
        ("block", 13, 25),
        "p34_h2_receipts_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        34,
        ("block", 28, 38),
        "p34_h3_expenses_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        34,
        ("block", 41, 43),
        "p34_h4_net_income_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    word(
        34, 41, "Farm income", FA, "p34_farm_income_aggregate", routes=(SEC_H,)
    ),
    *paired(34, ("block", 46, 49), "p34_h5_business_purpose", routes=(SEC_H,)),
    word(
        34, 47, "The business", BA, "p34_business_aggregate", routes=(SEC_H,)
    ),
    *paired(
        34, ("block", 52, 55), "p34_h6_corporation_purpose", routes=(SEC_H,)
    ),
    word(
        34,
        53,
        '"corporation"',
        BA,
        "p34_corporation_aggregate",
        routes=(SEC_H,),
    ),
)


PAGE_35 = (
    *paired(
        35,
        ("block", 5, 9),
        "p35_h7_business_profit_purpose",
        anchor_kind=M,
        parents=("p33_business_aggregate",),
        routes=(SEC_H,),
        parent_note=_BUSINESS_PARENT,
    ),
    word(35, 5, "the business", BA, "p35_business_aggregate", routes=(SEC_H,)),
    word(35, 8, "wife", R, "p35_role_wife_business", routes=(SEC_H,)),
    *paired(
        35,
        ("block", 12, 14),
        "p35_h8_head_total_purpose",
        anchor_kind=T,
        routes=(SEC_H,),
    ),
    word(
        35,
        12,
        "1974 head of the FU",
        R,
        "p35_role_head_total",
        routes=(SEC_H,),
    ),
    word(35, 14, "second job", J, "p35_job_second", routes=(SEC_H,)),
    *paired(
        35,
        ("block", 16, 21),
        "p35_fixed_salary_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        35,
        ("block", 22, 24),
        "p35_complicated_history_purpose",
        routes=(SEC_H,),
    ),
    word(35, 22, "several jobs", J, "p35_job_several", routes=(SEC_H,)),
    *paired(
        35,
        ("block", 25, 28),
        "p35_businessman_wage_allocation",
        anchor_kind=M,
        parents=("p35_job_other",),
        routes=(SEC_H,),
        parent_note="The prose explicitly assigns the included wages to another job.",
    ),
    word(
        35,
        25,
        "unincorporated business",
        BA,
        "p35_unincorporated_business_aggregate",
        routes=(SEC_H,),
    ),
    word(35, 27, "some other job", J, "p35_job_other", routes=(SEC_H,)),
)


PAGE_37 = (
    *paired(
        37,
        ("block", 2, 3),
        "p37_h9_bonus_overtime_commission",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    tail(37, 5, "[ ]NO", F, "p37_flow_h9_no", routes=(SEC_H,)),
    *paired(
        37, ("line", 10), "p37_h10_amount", anchor_kind=M, routes=(SEC_H,)
    ),
    *paired(37, ("line", 13), "p37_h11_other_income_header", routes=(SEC_H,)),
    word(37, 13, "(HEAD)", R, "p37_role_head_h11", routes=(SEC_H,)),
    word(
        37,
        15,
        '(IF "YES" TO ANY',
        F,
        "p37_flow_h11_yes_to_any",
        routes=(SEC_H,),
    ),
    *paired(
        37,
        ("needle", 15, "a) professional practice or trade?", 0),
        "p37_h11a_professional_trade",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("block", 17, 19),
        "p37_h11b_farming_roomers",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    word(
        37,
        17,
        "farming or market gardening",
        FA,
        "p37_farming_market_aggregate",
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("block", 21, 22),
        "p37_h11c_dividend_interest_rent",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37, ("line", 24), "p37_h11d_adc_afdc", anchor_kind=M, routes=(H11_ANY,)
    ),
    *paired(
        37,
        ("line", 26),
        "p37_h11e_other_welfare",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("line", 28),
        "p37_h11f_social_security",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("block", 29, 30),
        "p37_h11g_retirement_pension_annuity",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("block", 31, 32),
        "p37_h11h_unemployment_workmens_comp",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("line", 34),
        "p37_h11i_alimony_child_support",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("line", 36),
        "p37_h11j_relatives",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(
        37,
        ("block", 38, 39),
        "p37_h11k_other",
        anchor_kind=M,
        routes=(H11_ANY,),
    ),
    *paired(37, ("block", 42, 43), "p37_h12_outside_help", routes=(SEC_H,)),
    word(37, 45, "[ ]YES", F, "p37_flow_h12_yes", routes=(SEC_H,)),
    tail(37, 45, "[ ]NO", F, "p37_flow_h12_no_exit", routes=(SEC_H,)),
    *paired(
        37,
        ("block", 47, 48),
        "p37_h13_outside_help_amount",
        anchor_kind=M,
        routes=(H12_YES,),
    ),
)


PAGE_38 = (
    *paired(
        38,
        ("block", 9, 14),
        "p38_h11_periodicity_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 17, 25),
        "p38_h11a_professional_trade_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        38,
        19,
        "self employed doctors",
        BA,
        "p38_self_employed_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 28, 34),
        "p38_h11b_farming_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        38,
        28,
        "FARMING OR MARKET GARDENING",
        FA,
        "p38_farming_market_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 36, 38),
        "p38_h11b_roomers_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 41, 47),
        "p38_h11c_dividends_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        38,
        42,
        "small incorporated business",
        BA,
        "p38_incorporated_business_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 49, 51),
        "p38_h11c_interest_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 53, 57),
        "p38_h11c_rent_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_39 = (
    *paired(
        39,
        ("block", 4, 6),
        "p39_h11c_trust_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        39,
        ("block", 8, 11),
        "p39_h11c_royalty_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        39,
        ("block", 14, 28),
        "p39_h11d_adc_afdc_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        39,
        ("block", 31, 48),
        "p39_h11e_other_welfare_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        39,
        ("block", 51, 53),
        "p39_h11f_social_security_start",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_40 = (
    *paired(
        40,
        ("block", 4, 15),
        "p40_h11f_social_security_continued",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        40,
        ("block", 18, 19),
        "p40_h11g_retirement_pay_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        40,
        ("block", 21, 38),
        "p40_h11g_pension_annuity_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        40,
        21,
        "previous employers",
        J,
        "p40_job_previous_employers",
        routes=(SEC_H,),
    ),
    *paired(
        40,
        ("block", 41, 48),
        "p40_h11h_unemployment_comp_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    span_words(
        40,
        47,
        "self-",
        48,
        "employed",
        BA,
        "p40_self_employed_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        40,
        ("block", 50, 55),
        "p40_h11h_workmens_comp_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(40, 53, "his job", J, "p40_job_injury_source", routes=(SEC_H,)),
)


PAGE_41 = (
    *paired(
        41,
        ("block", 5, 8),
        "p41_h11i_alimony_support_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 11, 13),
        "p41_h11j_relative_help_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 16, 19),
        "p41_h11k_training_allowance_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 21, 22),
        "p41_h11k_illegal_income_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 27, 29),
        "p41_h12_h13_family_help_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_43 = (
    word(
        43,
        7,
        "[ ] INCOME FROM WELFARE OR ADC, AFDC",
        F,
        "p43_flow_h14_welfare",
        routes=(SEC_H,),
    ),
    tail(
        43,
        7,
        "[ J NO SUCH INCOME",
        F,
        "p43_flow_h14_no_exit",
        routes=(SEC_H,),
    ),
    *paired(
        43,
        ("block", 10, 11),
        "p43_h15_non_cash_welfare",
        anchor_kind=M,
        routes=(H14_WELFARE,),
    ),
    word(43, 13, "[ ] YES", F, "p43_flow_h15_yes", routes=(H14_WELFARE,)),
    tail(43, 13, "[ ] NO", F, "p43_flow_h15_no_exit", routes=(H14_WELFARE,)),
    *paired(
        43,
        ("block", 15, 16),
        "p43_h16_welfare_amount",
        anchor_kind=M,
        routes=(H15_YES,),
    ),
    *paired(43, ("line", 19), "p43_h17_wife_checkpoint", routes=(SEC_H,)),
    word(43, 19, "HEAD", R, "p43_role_head_h17", routes=(SEC_H,)),
    word(43, 19, "WIFE", R, "p43_role_wife_h17", routes=(SEC_H,)),
    word(
        43,
        21,
        "[ ] YES, WIFE IN FU",
        F,
        "p43_flow_h17_wife",
        routes=(SEC_H,),
    ),
    tail(
        43,
        21,
        "[ ] NO WIFE IN FU",
        F,
        "p43_flow_h17_no_wife",
        routes=(SEC_H,),
    ),
    *paired(43, ("line", 23), "p43_h18_wife_income", routes=(H_WIFE,)),
    word(43, 23, "wife", R, "p43_role_wife_h18", routes=(H_WIFE,)),
    word(43, 24, "[t ] YES", F, "p43_flow_h18_yes", routes=(H_WIFE,)),
    tail(43, 24, "[ ] NO", F, "p43_flow_h18_no_exit", routes=(H_WIFE,)),
    *paired(43, ("line", 26), "p43_h19_wife_income_source", routes=(H18_YES,)),
    word(
        43,
        26,
        "wages, salary",
        M,
        "p43_h19_wage_salary_component",
        routes=(H18_YES,),
    ),
    word(
        43,
        26,
        "a business",
        BA,
        "p43_h19_business_aggregate",
        routes=(H18_YES,),
    ),
    *paired(
        43,
        ("block", 31, 32),
        "p43_h20_wife_income_total",
        anchor_kind=T,
        routes=(H18_YES,),
    ),
)


PAGE_44 = (
    *paired(
        44,
        ("block", 6, 16),
        "p44_h14_h16_welfare_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        44, 22, "wife's income", R, "p44_role_wife_all_income", routes=(SEC_H,)
    ),
    word(
        44,
        29,
        "wife's income",
        R,
        "p44_role_wife_business_income",
        routes=(SEC_H,),
    ),
    span_words(
        44,
        29,
        "family",
        30,
        "business",
        BA,
        "p44_family_business_aggregate",
        routes=(SEC_H,),
    ),
)


PAGE_45 = (
    *paired(45, ("block", 2, 6), "p45_h21_member_schedule", routes=(SEC_H,)),
    from_word(
        45,
        5,
        "IF NO SUCH PEOPLE",
        6,
        F,
        "p45_flow_h21_no_people_exit",
        routes=(SEC_H,),
    ),
    *paired(45, ("block", 8, 11), "p45_h22_member_income", routes=(SEC_H,)),
    word(45, 8, "[ ]YES", F, "p45_flow_h22_yes", routes=(SEC_H,)),
    word(
        45, 8, "[ ]NO (GO TO H22", F, "p45_flow_h22_no_loop", routes=(SEC_H,)
    ),
    *paired(
        45,
        ("line", 14),
        "p45_h23_member_income_amount",
        anchor_kind=M,
        routes=(H22_YES,),
    ),
    *paired(
        45,
        ("block", 16, 18),
        "p45_h24_member_income_source",
        routes=(H22_YES,),
    ),
    word(
        45,
        16,
        "wages , a pension",
        M,
        "p45_h24_wage_pension_component",
        routes=(H22_YES,),
    ),
    word(
        45,
        16,
        "a business",
        BA,
        "p45_h24_business_aggregate",
        routes=(H22_YES,),
    ),
    line(
        45,
        20,
        F,
        "p45_flow_h24_wages_business",
        routes=(H22_YES,),
    ),
    *paired(
        45, ("block", 23, 24), "p45_h25_member_occupation", routes=(H24_WORK,)
    ),
    word(
        45,
        24,
        "(OCCUPATION)",
        J,
        "p45_job_member_occupation",
        routes=(H24_WORK,),
    ),
    *paired(
        45,
        ("block", 25, 27),
        "p45_h26_member_weeks",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(
        45,
        ("block", 29, 30),
        "p45_h27_member_hours",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(
        45,
        ("line", 32),
        "p45_h28_member_half_time",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(45, ("block", 36, 40), "p45_h29_other_income", routes=(H22_YES,)),
    word(45, 37, "[ ]YES", F, "p45_flow_h29_yes", routes=(H22_YES,)),
    word(
        45,
        36,
        "[ ]NO (GO TO H22",
        F,
        "p45_flow_h29_no_loop",
        routes=(H22_YES,),
    ),
    *paired(
        45, ("block", 45, 47), "p45_h30_other_income_source", routes=(H29_YES,)
    ),
    *paired(
        45,
        ("block", 49, 50),
        "p45_h31_other_income_amount",
        anchor_kind=M,
        routes=(H29_YES,),
    ),
)


PAGE_46 = (
    *paired(
        46,
        ("line", 20),
        "p46_h23_amount_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        46,
        ("block", 23, 26),
        "p46_h24_source_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(46, 24, "odd jobs", J, "p46_job_odd_jobs", routes=(SEC_H,)),
    *paired(
        46, ("block", 29, 30), "p46_h25_occupation_purpose", routes=(SEC_H,)
    ),
    word(46, 29, "occupation", J, "p46_job_occupation", routes=(SEC_H,)),
    word(46, 30, "heads", R, "p46_role_heads", routes=(SEC_H,)),
    word(46, 30, "wives", R, "p46_role_wives", routes=(SEC_H,)),
    *paired(
        46,
        ("block", 33, 35),
        "p46_h26_h28_irregular_hours_purpose",
        parents=("p46_job_occupation",),
        routes=(SEC_H,),
        parent_note="The explanatory block explicitly applies to H25's occupation.",
    ),
    *paired(
        46,
        ("block", 38, 39),
        "p46_h29_h31_total_income_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_47_RELATION = tuple(
    row
    for column in range(3)
    for row in (
        *paired(
            47,
            ("needle", 6, "RELATION TO HEAD", column),
            f"p47_relation_{column + 1}",
            routes=(SEC_H,),
        ),
        word(
            47,
            6,
            "RELATION TO HEAD",
            R,
            f"p47_role_head_label_{column + 1}",
            occurrence=column,
            routes=(SEC_H,),
        ),
    )
)

PAGE_47_FIRST_SOURCE = tuple(
    row
    for column in range(3)
    for row in paired(
        47,
        ("needle", 17, "(SOURCE)", column),
        f"p47_source_1_{column + 1}",
        routes=(SEC_H,),
    )
)

PAGE_47_OCCUPATION = tuple(
    row
    for column in range(3)
    for row in (
        *paired(
            47,
            ("needle", 22, "(OCCUPATION)", column),
            f"p47_occupation_{column + 1}",
            routes=(SEC_H,),
        ),
        word(
            47,
            22,
            "(OCCUPATION)",
            J,
            f"p47_job_occupation_{column + 1}",
            occurrence=column,
            routes=(SEC_H,),
        ),
    )
)

PAGE_47_WEEKS = tuple(
    row
    for column in range(3)
    for row in paired(
        47,
        ("needle", 25, "(WEEKS)", column),
        f"p47_weeks_{column + 1}",
        parents=(f"p47_job_occupation_{column + 1}",),
        routes=(SEC_H,),
        parent_note="The same repeated column's occupation is the local job parent.",
    )
)

PAGE_47_HOURS = tuple(
    row
    for column in range(3)
    for row in paired(
        47,
        ("needle", 28, "(HOURS)", column),
        f"p47_hours_{column + 1}",
        parents=(f"p47_job_occupation_{column + 1}",),
        routes=(SEC_H,),
        parent_note="The same repeated column's occupation is the local job parent.",
    )
)

PAGE_47_SECOND_SOURCE = tuple(
    row
    for column in range(3)
    for row in paired(
        47,
        ("needle", 45, "(SOURCE)", column),
        f"p47_source_2_{column + 1}",
        routes=(SEC_H,),
    )
)

PAGE_47 = (
    *PAGE_47_RELATION,
    word(
        47, 8, "[ ]YES", F, "p47_flow_h22_yes_1", occurrence=0, routes=(SEC_H,)
    ),
    word(
        47,
        8,
        "[ ]NO (GO TO H22",
        F,
        "p47_flow_h22_no_1",
        occurrence=0,
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        47,
        ("needle", 8, "[ ]NO (GO TO H22", 0),
        "p47_repeat_next_person_1",
        "First repeated column explicitly loops to H22 for the next person.",
        routes=(SEC_H,),
    ),
    word(
        47, 8, "[ ]YES", F, "p47_flow_h22_yes_2", occurrence=1, routes=(SEC_H,)
    ),
    word(
        47,
        8,
        "[ ]NO (GO TO H22",
        F,
        "p47_flow_h22_no_2",
        occurrence=1,
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        47,
        ("needle", 8, "[ ]NO (GO TO H22", 1),
        "p47_repeat_next_person_2",
        "Second repeated column explicitly loops to H22 for the next person.",
        routes=(SEC_H,),
    ),
    word(
        47, 8, "[ ]YES", F, "p47_flow_h22_yes_3", occurrence=2, routes=(SEC_H,)
    ),
    word(47, 8, "[ ]NO (GO TO H:22", F, "p47_flow_h22_no_3", routes=(SEC_H,)),
    _unresolved_repeat(
        47,
        ("needle", 8, "[ ]NO (GO TO H:22", 0),
        "p47_repeat_next_person_3",
        "Third repeated column explicitly loops to H22 for the next person.",
        routes=(SEC_H,),
    ),
    *PAGE_47_FIRST_SOURCE,
    *PAGE_47_OCCUPATION,
    *PAGE_47_WEEKS,
    *PAGE_47_HOURS,
    word(47, 35, "_r YES", F, "p47_flow_h29_yes_1", routes=(SEC_H,)),
    word(47, 36, "[ ]NO (GO TO", F, "p47_flow_h29_no_1", routes=(SEC_H,)),
    _unresolved_repeat(
        47,
        ("needle", 36, "[ ]NO (GO TO", 0),
        "p47_repeat_h29_next_person_1",
        "First repeated H29 column explicitly loops to H22.",
        routes=(SEC_H,),
    ),
    word(47, 37, "[r ES", F, "p47_flow_h29_yes_2", routes=(SEC_H,)),
    word(47, 37, "[ ]NO (GO TO", F, "p47_flow_h29_no_2", routes=(SEC_H,)),
    _unresolved_repeat(
        47,
        ("needle", 37, "[ ]NO (GO TO", 0),
        "p47_repeat_h29_next_person_2",
        "Second repeated H29 column explicitly loops to H22.",
        routes=(SEC_H,),
    ),
    word(47, 39, "[ ]YES", F, "p47_flow_h29_yes_3", routes=(SEC_H,)),
    word(47, 39, "[ ]NO (GO TO", F, "p47_flow_h29_no_3", routes=(SEC_H,)),
    _unresolved_repeat(
        47,
        ("needle", 39, "[ ]NO (GO TO", 0),
        "p47_repeat_h29_next_person_3",
        "Third repeated H29 column explicitly loops to H22.",
        routes=(SEC_H,),
    ),
    *PAGE_47_SECOND_SOURCE,
    line(47, 54, F, "p47_flow_repeated_schedule_exit", routes=(SEC_H,)),
)


PAGE_48 = (
    _repeat_relation(
        48,
        ("block", 6, 8),
        "p48_repeat_previous_page",
        (
            "p47_relation_1",
            "p47_relation_2",
            "p47_relation_3",
            "p47_source_1_1",
            "p47_source_1_2",
            "p47_source_1_3",
            "p47_occupation_1",
            "p47_occupation_2",
            "p47_occupation_3",
            "p47_job_occupation_1",
            "p47_job_occupation_2",
            "p47_job_occupation_3",
            "p47_weeks_1",
            "p47_weeks_2",
            "p47_weeks_3",
            "p47_hours_1",
            "p47_hours_2",
            "p47_hours_3",
            "p47_source_2_1",
            "p47_source_2_2",
            "p47_source_2_3",
        ),
        (
            "p45_h21_member_schedule",
            "p45_h24_member_income_source",
            "p45_h25_member_occupation",
            "p45_job_member_occupation",
            "p45_h26_member_weeks",
            "p45_h27_member_hours",
            "p45_h30_other_income_source",
        ),
        "The page explicitly says it repeats the previous member schedule; "
        "every repeated relation, source, occupation, weeks, and hours anchor "
        "is tied to its establishing H21-H30 anchor without collapsing coordinates.",
        routes=(SEC_H,),
    ),
)


PAGE_49 = (
    *paired(49, ("block", 6, 7), "p49_h32_additional_income", routes=(SEC_H,)),
    word(49, 8, "(J YES", F, "p49_flow_h32_yes", routes=(SEC_H,)),
    tail(49, 8, "[] No", F, "p49_flow_h32_no_exit", routes=(SEC_H,)),
    *paired(
        49,
        ("line", 11),
        "p49_h33_additional_member_identity",
        routes=(H32_YES,),
    ),
    *paired(
        49,
        ("block", 20, 21),
        "p49_h34_other_money",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(49, 23, "11. YES I", F, "p49_flow_h34_yes", routes=(SEC_H,)),
    tail(49, 23, "~(GO TO H36)", F, "p49_flow_h34_no_exit", routes=(SEC_H,)),
    *paired(
        49,
        ("block", 25, 26),
        "p49_h35_other_money_amount",
        anchor_kind=M,
        routes=(H34_YES,),
    ),
)


PAGE_50 = (
    *paired(
        50,
        ("block", 6, 13),
        "p50_h34_h35_nonincome_money_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_51 = (
    tail(51, 33, "SECTION K:", F, "p51_flow_section_k"),
    word(
        51,
        38,
        "1 . FU HAS A NEW HEAD THIS YEAR",
        F,
        "p51_flow_k1_new_head",
        routes=(SEC_K,),
    ),
    from_word(
        51,
        38,
        "I 5 . THIS FU HAS THE SAME HEAD AS IN 19 73",
        39,
        F,
        "p51_flow_k1_same_head",
        routes=(SEC_K,),
    ),
)


PAGE_53 = (
    *paired(
        53,
        ("line", 3),
        "p53_k3_father_occupation",
        parents=("p53_job_father_occupation",),
        routes=(K_NEW_HEAD,),
        parent_note="The exact father's-usual-occupation noun is its local job parent.",
    ),
    word(
        53,
        3,
        "father's usual occupation",
        J,
        "p53_job_father_occupation",
        routes=(K_NEW_HEAD,),
    ),
    *paired(
        53,
        ("line", 6),
        "p53_k4_first_job_occupation",
        parents=("p53_job_first_full_time",),
        routes=(K_NEW_HEAD,),
        parent_note=_FIRST_JOB_PARENT,
    ),
    word(
        53, 6, "(HEAD's)", R, "p53_role_head_first_job", routes=(K_NEW_HEAD,)
    ),
    word(
        53,
        6,
        "first full time regular job",
        J,
        "p53_job_first_full_time",
        routes=(K_NEW_HEAD,),
    ),
    from_word(
        53,
        9,
        "I 0. NEVER HORKED I",
        11,
        F,
        "p53_flow_k4_never",
        routes=(K_NEW_HEAD,),
    ),
    *paired(
        53,
        ("block", 13, 14),
        "p53_k5_job_history",
        parents=("p53_job_different_kinds",),
        routes=(K_NEW_HEAD,),
        parent_note="K5's exact different-kinds-of-jobs noun is the local history parent.",
    ),
    word(
        53,
        13,
        "different kinds of jobs",
        J,
        "p53_job_different_kinds",
        routes=(K_NEW_HEAD,),
    ),
    word(
        53,
        14,
        "same occupation you started in",
        J,
        "p53_job_starting_occupation",
        routes=(K_NEW_HEAD,),
    ),
)


PAGE_54 = (
    *paired(
        54,
        ("block", 13, 17),
        "p54_k5_occupation_history_purpose",
        routes=(K_NEW_HEAD,),
    ),
    word(
        54,
        13,
        "occupations the head",
        J,
        "p54_job_head_occupations",
        routes=(K_NEW_HEAD,),
    ),
    word(54, 13, "head", R, "p54_role_head_history", routes=(K_NEW_HEAD,)),
    word(
        54, 15, "part-time jobs", J, "p54_job_part_time", routes=(K_NEW_HEAD,)
    ),
)


CROSS_REFERENCES = (
    _xref(
        16,
        ("line", 17),
        "p16_xref_d26_d27_to_d2_d3",
        ("p15_d26_occupation",),
        ("p9_d2_occupation",),
        "D26-D27 explicitly reuse the D2-D3 occupation instructions.",
        routes=(SEC_D,),
    ),
    _xref(
        20,
        ("block", 5, 6),
        "p20_xref_e1_to_d2_d3",
        ("p19_e1_sought_job",),
        ("p9_d2_occupation",),
        "E1 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        20,
        ("line", 29),
        "p20_xref_e6_to_d2_d3",
        ("p19_e6_last_job_occupation",),
        ("p9_d2_occupation",),
        "E6 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        20,
        ("line", 34),
        "p20_xref_e7_to_d4",
        ("p19_e7_last_job_industry",),
        ("p9_d4_industry",),
        "E7 explicitly applies the D4 industry objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        20,
        ("line", 39),
        "p20_xref_e8_to_d7",
        ("p19_e8_last_job_outcome",),
        ("p9_d7_previous_job_outcome",),
        "E8 explicitly applies the D7 prior-job outcome objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        24,
        ("line", 16),
        "p24_xref_f3_to_d2_d3",
        ("p23_f3_occupation",),
        ("p9_d2_occupation",),
        "F3 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_F,),
    ),
    _xref(
        24,
        ("line", 19),
        "p24_xref_f4_to_d4",
        ("p23_f4_industry",),
        ("p9_d4_industry",),
        "F4 explicitly applies the D4 industry objectives.",
        routes=(SEC_F,),
    ),
    _xref(
        26,
        ("block", 17, 18),
        "p26_xref_g3_g4_to_d2_d4",
        ("p25_g3_wife_occupation", "p25_g4_wife_industry"),
        ("p9_d2_occupation", "p9_d4_industry"),
        "The G3-G4 wife occupation/industry fields explicitly reuse D2-D4.",
        routes=(G_MARRIED,),
    ),
    _xref(
        26,
        ("block", 21, 23),
        "p26_xref_g5_g6_to_e9_e10",
        ("p25_g5_wife_weeks", "p25_g6_wife_hours"),
        ("p19_e9_weeks_worked", "p19_e10_hours_worked"),
        "G5-G6 explicitly reuse the E9-E10 work-time objectives.",
        routes=(G_MARRIED,),
    ),
    _xref(
        26,
        ("line", 26),
        "p26_xref_g7_g8_to_d31_d32",
        ("p25_g7_wife_work_availability",),
        ("p15_d31_work_availability",),
        "G7-G8 explicitly reuse D31-D32; the retained availability endpoints "
        "form the exact document-local portion of that instruction.",
        routes=(G_MARRIED,),
    ),
    _unresolved_repeat(
        34,
        ("line", 10),
        "p34_xref_nonfarmer_farm_to_h11b",
        "The instruction reallocates nonfarmer farm income to H11b; it is "
        "allocation evidence rather than a proved aggregate alias.",
        relation=XREF,
        alias=("p33_farm_aggregate",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        34,
        ("block", 54, 55),
        "p34_xref_corporation_to_h11c",
        "The H6 objective explicitly directs incorporated-business owners to H11c.",
        relation=XREF,
        alias=("p34_corporation_aggregate",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        35,
        ("block", 25, 28),
        "p35_xref_business_wages_h7_h8",
        "The prose allocates businessman wages between H7 and H8 without proving alias identity.",
        relation=XREF,
        alias=("p35_businessman_wage_allocation",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        35,
        ("block", 30, 31),
        "p35_no_double_count_h7_h8",
        "The exact instruction prevents the H7 and H8 figures from being recorded twice.",
        alias=("p33_h7_business_share", "p33_h8_head_wages_total"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        38,
        ("block", 4, 6),
        "p38_no_separate_h9_h10_from_h8",
        "The exact instruction preserves prior inclusion of H9-H10 sources in H8.",
        alias=("p37_h9_bonus_overtime_commission", "p33_h8_head_wages_total"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        38,
        ("block", 28, 34),
        "p38_no_duplicate_h11b_h2_h4",
        "The H11b objective explicitly prevents duplication with H2-H4 farm income.",
        alias=("p38_h11b_farming_purpose", "p33_h4_net_farm_income"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        38,
        ("line", 43),
        "p38_xref_salary_to_e8",
        "The printed objective sends a small-business salary to E8; the target "
        "is preserved unresolved because that printed identifier is anomalous here.",
        relation=XREF,
        alias=("p38_h11c_dividends_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        41,
        ("line", 24),
        "p41_no_double_count_h11k",
        "The exact H11k instruction forbids double counting without naming a unique endpoint.",
        alias=("p41_h11k_illegal_income_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        43,
        ("line", 5),
        "p43_xref_h14_to_h11d_h11e",
        "H14 explicitly refers to H11d and H11e; this is routing/allocation evidence.",
        relation=XREF,
        alias=("p37_h11d_adc_afdc", "p37_h11e_other_welfare"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        44,
        ("block", 17, 18),
        "p44_xref_welfare_food_stamps",
        "The welfare objective explicitly directs missed food stamps back to G23-G33.",
        relation=XREF,
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        44,
        ("block", 22, 27),
        "p44_wife_all_sources_instruction",
        "The exact instruction requires the wife's income from every source and "
        "preserves possible prior stock-income inclusion.",
        alias=("p43_h20_wife_income_total",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        44,
        ("block", 29, 31),
        "p44_no_duplicate_wife_business_h7",
        "The exact instruction prevents wife family-business income from duplicating H7.",
        alias=("p43_h20_wife_income_total", "p33_h7_business_share"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        45,
        ("block", 2, 6),
        "p45_repeat_member_schedule",
        "H21 explicitly creates the repeated member-income schedule for every listed person.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        45,
        ("needle", 8, "[ ]NO (GO TO H22", 0),
        "p45_repeat_h22_next_person",
        "The H22 no branch explicitly repeats H22 for the next listed person.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        45,
        ("needle", 36, "[ ]NO (GO TO H22", 0),
        "p45_repeat_h29_next_person",
        "The H29 no branch explicitly repeats H22 for the next listed person.",
        alias=("p45_h22_member_income",),
        routes=(H22_YES,),
    ),
    _unresolved_repeat(
        46,
        ("block", 5, 13),
        "p46_repeat_member_listing_instruction",
        "The objective explicitly defines complete repeated-person coverage, including movers.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        46,
        ("block", 38, 39),
        "p46_xref_additional_member_income",
        "The H29-H31 objective explicitly adds these amounts to prior member income.",
        relation=XREF,
        alias=("p46_h29_h31_total_income_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        49,
        ("line", 15),
        "p49_repeat_additional_members_h22_h31",
        "H33 explicitly sends each additional member through H22-H31.",
        alias=("p49_h33_additional_member_identity",),
        routes=(H32_YES,),
    ),
    _xref(
        54,
        ("line", 9),
        "p54_xref_k4_to_d2_d3",
        ("p53_k4_first_job_occupation",),
        ("p9_d2_occupation",),
        "K4 explicitly reuses D2-D3 occupation instructions; the exact local "
        "component link is to the D2 occupation field.",
        routes=(K_NEW_HEAD,),
    ),
)


REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_9,
    *PAGE_10,
    *PAGE_11,
    *PAGE_12,
    *PAGE_13,
    *PAGE_14,
    *PAGE_15,
    *PAGE_16,
    *PAGE_17,
    *PAGE_18,
    *PAGE_19,
    *PAGE_20,
    *PAGE_21,
    *PAGE_22,
    *PAGE_23,
    *PAGE_24,
    *PAGE_25,
    *PAGE_26,
    *PAGE_27,
    *PAGE_29,
    *PAGE_30,
    *PAGE_33,
    *PAGE_34,
    *PAGE_35,
    *PAGE_37,
    *PAGE_38,
    *PAGE_39,
    *PAGE_40,
    *PAGE_41,
    *PAGE_43,
    *PAGE_44,
    *PAGE_45,
    *PAGE_46,
    *PAGE_47,
    *PAGE_48,
    *PAGE_49,
    *PAGE_50,
    *PAGE_51,
    *PAGE_53,
    *PAGE_54,
    *CROSS_REFERENCES,
)


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
        try:
            start, end = resolve(page_text, row["selector"])
        except SpecError as error:
            raise SpecError(f"{row['key']}: {error}") from error
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

    branch_ref_by_key_and_parent: dict[tuple[str, tuple[str, ...]], str] = {}
    final_specs: list[dict[str, Any]] = []
    for row in occurrence_specs:
        paths: list[list[str]] = []
        for route in row["routes"]:
            path: list[str] = []
            for position, parent_key in enumerate(route):
                lookup = (parent_key, tuple(route[:position]))
                if lookup not in branch_ref_by_key_and_parent:
                    raise SpecError(
                        f"{row['key']} routes through unresolved {parent_key} "
                        f"with parent route {route[:position]}"
                    )
                path.append(branch_ref_by_key_and_parent[lookup])
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
            for route, path in zip(row["routes"], paths, strict=True):
                branch_ref_by_key_and_parent[(row["key"], tuple(route))] = (
                    annotation._review_branch_ref(
                        row["review_occurrence_id"], path, len(paths)
                    )
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
                "parent_resolution_note": row.get("parent_note")
                or (
                    "Parent job or aggregate is named in the same printed question block."
                    if parents
                    else "No printed parent job or aggregate on this screen; "
                    "parenting is deferred to global assembly."
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
            "whole_page_review": "all_62_pages_including_empty_occurrence_pages",
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
        f"document 13 source review: {len(review['occurrence_specs'])} "
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
