#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 19.

The authenticated source is the 74-page 1977 family question-by-question
manual, fam1977_QxQs.pdf. Printed questionnaire screens alternate with
interviewer-objective pages. Every page was read from the independently
replayed Poppler 26.04.0 UTF-8 bytes before candidate adjudication.

The retained domain is deliberately narrow: head and spouse employment
attachment, job identity, occupation and industry, employee/self/government
context, work exposure, pay components, farm and unincorporated-business
aggregates, and lifetime work history. Housing, mobility, commuting,
job-search effort, supervision, union, child care, housework, food, transfers,
assets, other-family-member income, health, education, and observation prose
do not enter merely because they contain worklike vocabulary.

Ordinary interviewer-objective prose is commentary rather than a printed
field. Only exact named cross-references and repeat instructions are retained
from objective pages. A job noun is retained only when it establishes a job
that parents a retained local field; later same-screen back-references do not
mint another job. Section H4 and H6 supply the farm and business aggregates.
H11a and H11b supply work-income components; H11c onward are nonwork income.
H19 asks only whether the wife had income, so this document prints no
role-total amount anchor.

A retained screen contributes every legible routing atom needed by its flow.
OCR-destroyed or physically split labels are never repaired: the annotation
uses only exact nonempty UTF-8 slices. Global component and equivalence IDs are
left to the later authority-wide assembly stage.
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
import build_rq_stage2_document_019_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 74


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


def resolve_tail(
    page_text: str, line_number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    """Span from a printed needle to the end of its physical line.

    Some instruments print a section header on a line that also
    carries the printed screen number, so a whole-line span would swallow an
    unrelated token.  This selector keeps the exact printed header bytes.
    """

    start, _ = resolve_needle(page_text, line_number, needle, occurrence)
    return start, resolve_line(page_text, line_number)[1]


def resolve_from(
    page_text: str,
    line_number: int,
    needle: str,
    last_line: int,
    occurrence: int = 0,
) -> tuple[int, int]:
    """Span from an exact inline needle through a later physical line."""

    start, _ = resolve_needle(page_text, line_number, needle, occurrence)
    return start, resolve_line(page_text, last_line)[1]


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
    raise SpecError(f"unknown selector mode {mode!r}")


_REJECTED = (
    "Every Poppler text line on page {page} was reviewed.  The page prints "
    "{scope}, outside the retained R_Q employment, work-income, and "
    "work-history domain; worklike prose on this page is not an occurrence."
)
_RETAINED = (
    "Every Poppler text line on page {page} was reviewed.  The page prints "
    "{scope}; exact locatable R_Q atoms are retained and all other prose is "
    "rejected."
)
_OBJECTIVES = (
    "Every Poppler text line on page {page} was reviewed.  This is "
    "question-by-question interviewer commentary for {scope}, not a printed "
    "field screen; only an explicit named cross-reference or repeat "
    "instruction listed in the source ledger is retained."
)

_PAGE_SCOPE: dict[int, tuple[str, str]] = {
    1: ("out", "the cover sheet and family-listing material"),
    2: ("out", "cover and family-composition instructions"),
    3: ("out", "transportation and nonemployment household material"),
    4: ("out", "transportation objectives"),
    5: ("out", "housing, rent, and household-property material"),
    6: ("out", "housing objectives, including farm-labor housing examples"),
    7: ("out", "housing and residential-mobility material"),
    8: ("out", "housing and residential-mobility objectives"),
    9: ("out", "residential-mobility material"),
    10: ("out", "residential-mobility objectives with incidental job prose"),
    11: ("in", "section D entry and head employment items D1-D4"),
    12: ("objectives", "section D items D1-D4"),
    13: ("objectives", "section D items D2-D4"),
    14: ("in", "head employment-arrangement and employer items D5-D25"),
    15: ("objectives", "items D5-D25"),
    16: ("in", "head job-spell and work-time items D26-D39"),
    17: ("objectives", "items D26-D39"),
    18: ("in", "head work-time items D40-D49"),
    19: ("objectives", "items D40-D49"),
    20: ("in", "head pay and extra-job items D50-D63"),
    21: ("objectives", "items D52-D63"),
    22: ("out", "counterfactual labor-supply and commuting items D64-D71"),
    23: ("objectives", "items D64-D71"),
    24: ("in", "section E sought-job items E1-E12"),
    25: ("objectives", "section E items E1-E12"),
    26: ("in", "last-job and work-time items E13-E26"),
    27: ("objectives", "items E13-E26"),
    28: ("in", "last-job work-time and commuting items E27-E37"),
    29: ("objectives", "items E27-E37"),
    30: ("in", "section F actual-work and future-job items F1-F13"),
    31: ("objectives", "section F items F1-F13"),
    32: ("in", "section F sought-job and search items F14-F25"),
    33: ("objectives", "items F14-F25"),
    34: ("in", "section G wife-work entry items G1-G7"),
    35: ("objectives", "section G items G1-G7"),
    36: ("in", "wife work-time items G8-G20"),
    37: ("objectives", "wife work-time items G8-G20"),
    38: ("in", "wife main-job and child-care items G21-G30"),
    39: ("objectives", "items G21-G30"),
    40: ("out", "wife-work attitude and housework items G31-G38"),
    41: ("objectives", "items G31-G38"),
    42: ("out", "food and food-stamp items G39-G51"),
    43: ("objectives", "items G39-G51"),
    44: ("out", "food-stamp items G52-G58"),
    45: ("objectives", "items G52-G58"),
    46: ("in", "section H farm, business, and head wage items H1-H8"),
    47: ("objectives", "section H items H1-H8"),
    48: ("objectives", "item H8"),
    49: ("in", "head work-income and other-income items H9-H13"),
    50: ("objectives", "items H9-H11b"),
    51: ("objectives", "items H11c-H11g"),
    52: ("objectives", "items H11g-H13"),
    53: ("in", "welfare checkpoints and wife income items H14-H25"),
    54: ("objectives", "items H14-H25"),
    55: ("out", "the other-family-member income grid H26-H38"),
    56: ("objectives", "the other-family-member grid H26-H38"),
    57: ("out", "continued other-family-member income columns"),
    58: ("objectives", "the repeated other-family-member grid"),
    59: ("out", "other-member transfers and lump-sum receipts"),
    60: ("objectives", "other-member transfers and lump-sum receipts"),
    61: ("out", "support, union, disability, and care items"),
    62: ("objectives", "support, union, disability, and care items"),
    63: ("in", "section J new-wife work-history items J1-J12"),
    64: ("objectives", "section J items J1-J12"),
    65: ("in", "section K new-head and first-job items K1-K10"),
    66: ("objectives", "section K items K1-K10"),
    67: ("out", "new-head background and mobility items K11-K24"),
    68: ("objectives", "items K11-K24"),
    69: ("in", "new-head work-history, schooling, and religion items K25-K39"),
    70: ("objectives", "items K25-K39"),
    71: ("out", "section L interviewer-observation items"),
    72: ("objectives", "section L interviewer-observation items"),
    73: ("out", "the thumbnail-sketch title page"),
    74: ("out", "thumbnail-sketch narrative instructions"),
}

PAGE_NOTES: dict[int, str] = {}
for _page, (_mode, _scope) in _PAGE_SCOPE.items():
    _template = {
        "out": _REJECTED,
        "in": _RETAINED,
        "objectives": _OBJECTIVES,
    }[_mode]
    PAGE_NOTES[_page] = _template.format(page=_page, scope=_scope)

_DEFAULT_NOTES = {
    F: "Exact locatable printed routing atom retained with reviewed ancestry.",
    R: "Exact printed role lexeme retained as local role attachment evidence.",
    J: "Exact establishing printed job noun retained without global merging.",
    M: "Exact printed remuneration component retained from source bytes.",
    T: "Exact printed role-total remuneration anchor retained.",
    FA: "Exact printed farm aggregate anchor retained.",
    BA: "Exact printed business aggregate anchor retained.",
    C: "Exact printed contextual field retained for a ratified purpose.",
    P: "Exact printed question prompt retained for its source field.",
    A: "Exact printed repeat or cross-reference instruction retained.",
}

XREF = "explicit_cross_reference"
REPEAT = "explicit_repeat_instruction"


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
    """Emit one source anchor and its one-to-one purpose prompt."""

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


SEC_D = ("p11_flow_section_d",)
D_EMPLOYEE = SEC_D + ("p14_flow_d5_someone_else",)
D_BOTH = SEC_D + ("p14_flow_d5_both",)
D_SELF = SEC_D + ("p14_flow_d5_self",)
D26_LONG = SEC_D + ("p16_flow_d26_one_year_or_more",)
D29_BETTER = SEC_D + ("p16_flow_d29_better",)
D29_WORSE = SEC_D + ("p16_flow_d29_worse",)
D29_SAME = SEC_D + ("p16_flow_d29_same",)
D_SALARIED = SEC_D + ("p20_flow_d50_salaried",)
D_HOURLY = SEC_D + ("p20_flow_d50_hourly",)
SEC_E = ("p24_flow_section_e",)
E_RECENT = SEC_E + ("p26_flow_e19_recent",)
E_OLD = SEC_E + ("p26_flow_e19_before_1976",)
SEC_F = ("p30_flow_section_f",)
F_THINKING = SEC_F + ("p32_flow_f14_thinking_yes",)
SEC_G = ("p34_flow_section_g",)
G_ELIGIBLE = SEC_G + ("p34_flow_g4_eligible",)
G_ALL_OTHERS = SEC_G + ("p34_flow_g4_all_others",)
G_CHILDREN = G_ELIGIBLE + ("p38_flow_g23_children",)
G19_ONE = G_ELIGIBLE + ("p36_flow_g19_one",)
G19_TWO = G_ELIGIBLE + ("p36_flow_g19_two",)
G19_MORE = G_ELIGIBLE + ("p36_flow_g19_more_than_two",)
SEC_H = ("p46_flow_section_h",)
H_FARMER = SEC_H + ("p46_flow_h1_farmer",)
H_NOT_FARMER = SEC_H + ("p46_flow_h1_not_farmer",)
H_CORPORATION = SEC_H + ("p46_flow_h6_corporation",)
H_UNINCORPORATED = SEC_H + ("p46_flow_h6_unincorporated",)
H_BOTH = SEC_H + ("p46_flow_h6_both",)
H_DONT_KNOW = SEC_H + ("p46_flow_h6_dont_know",)
H_WIFE = SEC_H + ("p53_flow_h18_wife_present",)
H_NO_WIFE = SEC_H + ("p53_flow_h18_no_wife",)
H24_POSITIVE = SEC_H + ("p53_flow_h24_social_security",)
H24_NO = SEC_H + ("p53_flow_h24_no",)
SEC_J = ("p63_flow_section_j",)
J_NEW_WIFE = SEC_J + ("p63_flow_j1_new_wife",)
J10_NONE = J_NEW_WIFE + ("p63_flow_j10_none",)
J11_ALL = J_NEW_WIFE + ("p63_flow_j11_all",)
K_NEW_HEAD = ("p65_flow_k1_new_head",)
K_SAME_HEAD = ("p65_flow_k1_same_head",)
K25_NONE = K_NEW_HEAD + ("p69_flow_k25_none",)
K26_ALL = K_NEW_HEAD + ("p69_flow_k26_all",)

_MAIN_JOB_PARENT = (
    "Parent job is the establishing main-job noun on the retained screen."
)
_EXTRA_JOB_PARENT = (
    "Parent job is the establishing extra-jobs noun on the retained screen."
)
_LAST_JOB_PARENT = (
    "Parent job is the establishing last-job noun on the retained screen."
)
_FARM_PARENT = "Parent aggregate is the printed net-farm-income anchor."
_BUSINESS_PARENT = (
    "Parent aggregate is the printed unincorporated-business anchor."
)


PAGE_11 = (
    tail(
        11,
        1,
        "SECTION D:",
        F,
        "p11_flow_section_d",
        note="Printed section D header opening the head employment schedule.",
    ),
    word(11, 4, "(HEAD)", R, "p11_role_head_d1", routes=(SEC_D,)),
    *paired(
        11,
        ("block", 4, 5),
        "p11_d1_assignment",
        routes=(SEC_D,),
        note="D1 prints the head labor-force assignment field.",
    ),
    word(11, 8, "1. WORKING", F, "p11_flow_d1_working", routes=(SEC_D,)),
    word(11, 10, "2 . ONLY", F, "p11_flow_d1_laid_off", routes=(SEC_D,)),
    word(
        11,
        12,
        "3. LOOKING FOR",
        F,
        "p11_flow_d1_looking",
        routes=(SEC_D,),
    ),
    word(11, 14, "4. RETIRED", F, "p11_flow_d1_retired", routes=(SEC_D,)),
    word(
        11,
        15,
        "5 . PERMANENTLY",
        F,
        "p11_flow_d1_disabled",
        routes=(SEC_D,),
    ),
    word(
        11,
        19,
        "6 . HOUSEWIFE",
        F,
        "p11_flow_d1_housewife",
        routes=(SEC_D,),
    ),
    word(11, 20, "7. STUDENT", F, "p11_flow_d1_student", routes=(SEC_D,)),
    word(11, 21, "8.    OTHER I", F, "p11_flow_d1_other", routes=(SEC_D,)),
    *paired(
        11,
        ("line", 27),
        "p11_d2_occupation",
        routes=(SEC_D,),
        note="D2 prints the head main-occupation field.",
    ),
    line(11, 31, P, "p11_d3_prompt", routes=(SEC_D,)),
    *paired(
        11,
        ("line", 36),
        "p11_d4_industry",
        routes=(SEC_D,),
        note="D4 prints the kind-of-business industry field.",
    ),
)


PAGE_14 = (
    line(
        14,
        1,
        C,
        "p14_d5_employee_self",
        routes=(SEC_D,),
        note="The three D5 answer headings print the employee, mixed, and "
        "self-employed arrangement field; the question stem is absent from "
        "the exact page text.",
    ),
    word(
        14,
        1,
        "SOH.EONE ELSE",
        F,
        "p14_flow_d5_someone_else",
        routes=(SEC_D,),
    ),
    word(
        14,
        1,
        "LL BOTH SOMEONE ELSE AND SELF",
        F,
        "p14_flow_d5_both",
        routes=(SEC_D,),
    ),
    word(
        14,
        1,
        "ITJ SELF ONLY",
        F,
        "p14_flow_d5_self",
        routes=(SEC_D,),
    ),
    word(
        14,
        2,
        "federal,",
        C,
        "p14_d6_government_level",
        routes=(D_EMPLOYEE,),
        note="Exact D6 federal-government label supporting the government-"
        "level context; its continuation is column-interleaved.",
    ),
    word(
        14,
        2,
        "D6 . Do you work for the federal,",
        P,
        "p14_d6_prompt",
        routes=(D_EMPLOYEE,),
    ),
    word(
        14,
        10,
        "f ede r a l, state o r l ocal",
        C,
        "p14_d14_government_level",
        routes=(D_BOTH,),
        note="Exact government-level lexeme for D14.",
    ),
    word(
        14,
        4,
        "Dl4 . When you work fo r others ,",
        P,
        "p14_d14_prompt",
        routes=(D_BOTH,),
    ),
    word(14, 50, "(GO TO Dl9)", F, "p14_flow_d16_no", routes=(D_BOTH,)),
    word(14, 65, "( GO TO D21)", F, "p14_flow_d19_no", routes=(D_BOTH,)),
    word(
        14,
        30,
        "(TURN TO PAGE 8, D26 )",
        F,
        "p14_flow_d25_exit",
        routes=(D_SELF,),
    ),
    word(
        14,
        78,
        "( TURN TO PAGE 8 , D26)",
        F,
        "p14_flow_d22_exit",
        routes=(D_BOTH,),
    ),
    word(
        14,
        79,
        "(TURN     TO PAGE 8, D26)",
        F,
        "p14_flow_d13_exit",
        routes=(D_EMPLOYEE,),
    ),
    word(
        14,
        74,
        "for your present employer?",
        C,
        "p14_d13_employer_tenure",
        routes=(D_EMPLOYEE,),
        note="D13 prints tenure with the present employer.",
    ),
    word(
        14,
        73,
        "Dl 3. How l ong h ave you worked",
        P,
        "p14_d13_prompt",
        routes=(D_EMPLOYEE,),
    ),
    *paired(
        14,
        ("line", 71),
        "p14_d21_employer_tenure",
        routes=(D_BOTH,),
        note="D21 prints tenure with the present employer for the mixed "
        "employee/self-employed branch.",
    ),
)


PAGE_16 = (
    *paired(
        16,
        ("line", 1),
        "p16_d26_position_tenure",
        routes=(SEC_D,),
        note="D26 prints tenure in the head's present position.",
    ),
    word(
        16,
        1,
        "your present position",
        J,
        "p16_job_present_position",
        routes=(SEC_D,),
        note="D26 establishes the head's present-position job.",
    ),
    word(
        16,
        3,
        "IF ONE YEAR OR MORE",
        F,
        "p16_flow_d26_one_year_or_more",
        routes=(SEC_D,),
    ),
    word(
        16,
        3,
        "( GO TO D32)",
        F,
        "p16_flow_d26_long_exit",
        routes=(D26_LONG,),
    ),
    *paired(
        16,
        ("line", 6),
        "p16_d27_start_month",
        parents=("p16_job_present_position",),
        routes=(SEC_D,),
        note="D27 prints the start-month exposure of the present job.",
        parent_note="Parent job is D26's present-position anchor.",
    ),
    *paired(
        16,
        ("block", 7, 8),
        "p16_d28_previous_job_outcome",
        parents=("p16_job_previous",),
        routes=(SEC_D,),
        note="D28 prints the disposition of the previous job.",
        parent_note="Parent job is the distinct prior-job noun in D28.",
    ),
    word(
        16,
        7,
        "the job you had before",
        J,
        "p16_job_previous",
        routes=(SEC_D,),
        note="D28 establishes the head's previous job.",
    ),
    block(
        16,
        10,
        11,
        F,
        "p16_flow_d28_no_previous_job",
        routes=(SEC_D,),
    ),
    *paired(
        16,
        ("block", 17, 18),
        "p16_d29_job_comparison",
        parents=("p16_job_present_position", "p16_job_previous"),
        routes=(SEC_D,),
        note="D29 prints a present-versus-previous-job assignment comparison.",
        parent_note="The comparison names both jobs on the same screen.",
    ),
    word(16, 20, "BETTER", F, "p16_flow_d29_better", routes=(SEC_D,)),
    word(16, 20, "WORSE", F, "p16_flow_d29_worse", routes=(SEC_D,)),
    word(16, 20, "SAME", F, "p16_flow_d29_same", routes=(SEC_D,)),
    word(
        16,
        20,
        "(GO TO D31)",
        F,
        "p16_flow_d29_same_exit",
        routes=(D29_SAME,),
    ),
    line(
        16,
        21,
        P,
        "p16_d30_prompt",
        routes=(D29_BETTER, D29_WORSE),
    ),
    *paired(
        16,
        ("line", 26),
        "p16_d31_relative_pay",
        parents=("p16_job_present_position", "p16_job_previous"),
        routes=(SEC_D,),
        note="D31 prints a qualitative relative-pay assignment field, not "
        "a remuneration amount.",
        parent_note="The comparison names the present and previous jobs.",
    ),
    word(16, 31, "(GO TO .D32)", F, "p16_flow_d31_exit", routes=(SEC_D,)),
    *paired(
        16,
        ("line", 34),
        "p16_d32_other_sick",
        routes=(SEC_D,),
        note="D32 prints a 1976 missed-work exposure.",
    ),
    word(16, 37, "( GO TO fi35)", F, "p16_flow_d32_no", routes=(SEC_D,)),
    line(16, 40, P, "p16_d33_prompt", routes=(SEC_D,)),
    *paired(
        16,
        ("line", 47),
        "p16_d34_other_sick_amount",
        routes=(SEC_D,),
        note="D34 prints the duration of missed work.",
    ),
    *paired(
        16,
        ("line", 51),
        "p16_d35_own_sick",
        routes=(SEC_D,),
        note="D35 prints a 1976 own-sickness work exposure.",
    ),
    word(
        16,
        54,
        "B{GO           TO   D37)",
        F,
        "p16_flow_d35_no",
        routes=(SEC_D,),
    ),
    *paired(
        16,
        ("line", 57),
        "p16_d36_own_sick_amount",
        routes=(SEC_D,),
        note="D36 prints the duration of own-sickness missed work.",
    ),
    *paired(
        16,
        ("line", 60),
        "p16_d37_paid_vacation",
        routes=(SEC_D,),
        note="D37 prints annual paid-vacation weeks.",
    ),
    *paired(
        16,
        ("line", 62),
        "p16_d38_vacation",
        routes=(SEC_D,),
        note="D38 prints whether vacation or time off occurred in 1976.",
    ),
    word(
        16,
        65,
        "(TURN TO PAGE 9, D40)",
        F,
        "p16_flow_d38_exit",
        routes=(SEC_D,),
    ),
    *paired(
        16,
        ("line", 66),
        "p16_d39_vacation_amount",
        routes=(SEC_D,),
        note="D39 prints the vacation or time-off duration.",
    ),
)


D44_ONE = SEC_D + ("p18_flow_d44_one",)
D44_TWO = SEC_D + ("p18_flow_d44_two",)
D44_MORE = SEC_D + ("p18_flow_d44_more_than_two",)

PAGE_18 = (
    *paired(
        18,
        ("line", 1),
        "p18_d40_strike",
        routes=(SEC_D,),
        note="D40 prints a 1976 strike-related missed-work exposure.",
    ),
    word(18, 4, "(GO TO D42)", F, "p18_flow_d40_no", routes=(SEC_D,)),
    *paired(
        18,
        ("line", 6),
        "p18_d41_strike_amount",
        routes=(SEC_D,),
        note="D41 prints the strike-related missed-work duration.",
    ),
    *paired(
        18,
        ("line", 9),
        "p18_d42_unemployment",
        routes=(SEC_D,),
        note="D42 prints a 1976 unemployment or layoff exposure.",
    ),
    word(18, 11, "(GO TO D46)", F, "p18_flow_d42_no", routes=(SEC_D,)),
    *paired(
        18,
        ("line", 14),
        "p18_d43_unemployment_amount",
        routes=(SEC_D,),
        note="D43 prints unemployment or layoff duration.",
    ),
    *paired(
        18,
        ("block", 17, 18),
        "p18_d44_unemployment_spells",
        routes=(SEC_D,),
        note="D44 prints the unemployment-spell classification.",
    ),
    word(
        18,
        20,
        "l . ALL IN ONE STRETCH",
        F,
        "p18_flow_d44_one",
        routes=(SEC_D,),
    ),
    word(
        18,
        20,
        "3 . TWO PERIODS",
        F,
        "p18_flow_d44_two",
        routes=(SEC_D,),
    ),
    word(
        18,
        20,
        "5 . MORE THAN TWO",
        F,
        "p18_flow_d44_more_than_two",
        routes=(SEC_D,),
    ),
    word(
        18,
        23,
        "(GO TO D46)",
        F,
        "p18_flow_d44_exit",
        routes=(D44_ONE, D44_TWO),
    ),
    *paired(
        18,
        ("line", 26),
        "p18_d45_unemployment_count",
        routes=(D44_MORE,),
        note="D45 prints the number of unemployment periods.",
    ),
    *paired(
        18,
        ("line", 31),
        "p18_d46_weeks_worked",
        parents=("p18_job_main",),
        routes=(SEC_D,),
        note="D46 prints weeks worked on the main job in 1976.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        18,
        31,
        "main j ob",
        J,
        "p18_job_main",
        routes=(SEC_D,),
        note="D46 establishes the head's main job; the later same-screen "
        "spelling is a back-reference, not another source job.",
    ),
    *paired(
        18,
        ("line", 34),
        "p18_d47_hours_worked",
        parents=("p18_job_main",),
        routes=(SEC_D,),
        note="D47 prints average weekly hours on the main job.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        18,
        ("line", 40),
        "p18_d48_overtime",
        routes=(SEC_D,),
        note="D48 prints whether overtime is excluded from reported hours.",
    ),
    word(
        18,
        42,
        "(TURN TO PAGE 10, D50)",
        F,
        "p18_flow_d48_no",
        routes=(SEC_D,),
    ),
    *paired(
        18,
        ("line", 43),
        "p18_d49_overtime_hours",
        routes=(SEC_D,),
        note="D49 prints annual overtime hours.",
    ),
)


PAGE_20 = (
    *paired(
        20,
        ("line", 1),
        "p20_d50_reporting_unit",
        routes=(SEC_D,),
        note="D50 prints the salary/hourly/other pay reporting unit.",
    ),
    word(
        20,
        3,
        "~SALARIED I",
        F,
        "p20_flow_d50_salaried",
        routes=(SEC_D,),
    ),
    word(
        20,
        3,
        "PAID BY HOUR",
        F,
        "p20_flow_d50_hourly",
        routes=(SEC_D,),
    ),
    *paired(
        20,
        ("needle", 4, "D51. How much is your salary?", 0),
        "p20_d51_salary",
        anchor_kind=M,
        parents=("p18_job_main",),
        routes=(D_SALARIED,),
        note="D51 prints the main-job salary remuneration component.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        20,
        7,
        "D52 . If you were to work more",
        P,
        "p20_d52_prompt",
        routes=(D_SALARIED,),
    ),
    word(20, 14, "( GO TO D58)", F, "p20_flow_d52_no", routes=(D_SALARIED,)),
    word(
        20,
        18,
        "DS 3 . IAbout how much",
        P,
        "p20_d53_prompt",
        routes=(D_SALARIED,),
    ),
    *paired(
        20,
        ("needle", 4, "D54. What is your hourly", 0),
        "p20_d54_regular_hourly_rate",
        anchor_kind=M,
        parents=("p18_job_main",),
        routes=(D_HOURLY,),
        note="D54 prints the regular-time hourly wage component.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        20,
        ("needle", 10, "D55 . What is your hourly", 0),
        "p20_d55_overtime_hourly_rate",
        anchor_kind=M,
        parents=("p18_job_main",),
        routes=(D_HOURLY,),
        note="D55 prints the overtime hourly wage component.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        20,
        4,
        "D56 ~ · How   is that?",
        P,
        "p20_d56_prompt",
        routes=(SEC_D,),
    ),
    word(
        20,
        15,
        "D57 . If you worked an",
        P,
        "p20_d57_prompt",
        routes=(SEC_D,),
    ),
    word(20, 25, "(GO TO . D58", F, "p20_flow_d53_exit", routes=(D_SALARIED,)),
    word(20, 25, "(GO TO _D58)", F, "p20_flow_d55_exit", routes=(D_HOURLY,)),
    word(
        20,
        25,
        "( GO TO D58)",
        F,
        "p20_flow_d57_exit",
        routes=(SEC_D,),
    ),
    block(20, 30, 31, P, "p20_d58_prompt", routes=(SEC_D,)),
    word(
        20,
        30,
        "extra jobs",
        J,
        "p20_job_extra",
        routes=(SEC_D,),
        note="D58 establishes the head's extra-job schedule.",
    ),
    word(
        20,
        33,
        '(TUR.i\\l" TO PAGE 11, D64)',
        F,
        "p20_flow_d58_no",
        routes=(SEC_D,),
    ),
    *paired(
        20,
        ("line", 36),
        "p20_d59_occupation",
        parents=("p20_job_extra",),
        routes=(SEC_D,),
        note="D59 prints the extra-job occupation field.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    line(20, 38, P, "p20_d60_prompt", routes=(SEC_D,)),
    line(
        20,
        38,
        A,
        "p20_d60_repeat",
        routes=(SEC_D,),
        relation=REPEAT,
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="D60's printed 'Anything else?' reopens the extra-job listing "
        "without equating the separately reported jobs.",
    ),
    *paired(
        20,
        ("line", 41),
        "p20_d61_hourly_pay",
        anchor_kind=M,
        parents=("p20_job_extra",),
        routes=(SEC_D,),
        note="D61 prints hourly pay for the extra-job schedule.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        20,
        ("block", 43, 44),
        "p20_d62_weeks",
        parents=("p20_job_extra",),
        routes=(SEC_D,),
        note="D62 prints weeks worked in extra jobs.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        20,
        ("line", 46),
        "p20_d63_hours",
        parents=("p20_job_extra",),
        routes=(SEC_D,),
        note="D63 prints average weekly extra-job hours.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
)


PAGE_24 = (
    tail(
        24,
        2,
        "SECTION E:",
        F,
        "p24_flow_section_e",
        note="Printed section E header opening the looking-for-work schedule.",
    ),
    *paired(
        24,
        ("line", 4),
        "p24_e1_occupation",
        parents=("p24_job_sought",),
        routes=(SEC_E,),
        note="E1 prints the occupation of the job being sought.",
        parent_note="Parent job is E1's sought-job noun.",
    ),
    word(
        24,
        4,
        "job",
        J,
        "p24_job_sought",
        routes=(SEC_E,),
        note="E1 establishes the sought job.",
    ),
    *paired(
        24,
        ("line", 8),
        "p24_e2_expected_earnings",
        anchor_kind=M,
        parents=("p24_job_sought",),
        routes=(SEC_E,),
        note="E2 prints expected earnings and reporting unit for the sought "
        "job.",
        parent_note="Parent job is E1's sought-job noun.",
    ),
    word(24, 14, "(GO TO E6)", F, "p24_flow_e4_no", routes=(SEC_E,)),
    word(24, 31, "(GO TO ElO)", F, "p24_flow_e8_no", routes=(SEC_E,)),
    word(
        24,
        49,
        "(TURN TO PAGE 13. El3)",
        F,
        "p24_flow_e12_exit",
        routes=(SEC_E,),
    ),
    word(
        24,
        50,
        "(TURN TO PAGE 13, El3)",
        F,
        "p24_flow_e11_exit",
        routes=(SEC_E,),
    ),
)


PAGE_26 = (
    *paired(
        26,
        ("line", 3),
        "p26_e14_ever_job",
        routes=(SEC_E,),
        note="E14 prints whether the head ever held a job.",
    ),
    word(
        26,
        5,
        "(TURN TO PAGE 17, Gl)",
        F,
        "p26_flow_e14_no",
        routes=(SEC_E,),
    ),
    *paired(
        26,
        ("line", 7),
        "p26_e15_occupation",
        parents=("p26_job_last",),
        routes=(SEC_E,),
        note="E15 prints the occupation of the last job.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        26,
        7,
        "last job",
        J,
        "p26_job_last",
        routes=(SEC_E,),
        note="E15 establishes the head's last job.",
    ),
    *paired(
        26,
        ("line", 11),
        "p26_e16_industry",
        parents=("p26_job_last",),
        routes=(SEC_E,),
        note="E16 prints the last-job industry.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        26,
        ("block", 16, 17),
        "p26_e18_job_outcome",
        parents=("p26_job_last",),
        routes=(SEC_E,),
        note="E18 prints the last-job disposition.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        26,
        ("line", 22),
        "p26_e19_last_worked",
        parents=("p26_job_last",),
        routes=(SEC_E,),
        note="E19 prints the last-worked exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        26,
        24,
        "IF 1976 OR 1977",
        F,
        "p26_flow_e19_recent",
        routes=(SEC_E,),
    ),
    word(
        26,
        24,
        "IF BEFORE 1976",
        F,
        "p26_flow_e19_before_1976",
        routes=(SEC_E,),
    ),
    word(
        26,
        24,
        "(TURN TO PAGE 17, Gl)",
        F,
        "p26_flow_e19_old_exit",
        routes=(E_OLD,),
    ),
    *paired(
        26,
        ("line", 27),
        "p26_e20_vacation",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E20 prints a 1976 vacation exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(26, 29, "(GO TO E22)", F, "p26_flow_e20_no", routes=(E_RECENT,)),
    *paired(
        26,
        ("block", 30, 31),
        "p26_e21_vacation_amount",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E21 prints vacation or time-off duration.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        26,
        ("line", 35),
        "p26_e22_other_sick",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E22 prints a missed-work exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(26, 37, "(GO TO E25)", F, "p26_flow_e22_no", routes=(E_RECENT,)),
    line(26, 39, P, "p26_e23_prompt", routes=(E_RECENT,)),
    *paired(
        26,
        ("line", 42),
        "p26_e24_other_sick_amount",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E24 prints missed-work duration.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        26,
        ("line", 46),
        "p26_e25_own_sick",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E25 prints an own-sickness work exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        26,
        48,
        "(TURN TO PAGE 14, E27)",
        F,
        "p26_flow_e25_no",
        routes=(E_RECENT,),
    ),
    *paired(
        26,
        ("line", 50),
        "p26_e26_own_sick_amount",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E26 prints own-sickness missed-work duration.",
        parent_note=_LAST_JOB_PARENT,
    ),
)


E31_ONE = E_RECENT + ("p28_flow_e31_one",)
E31_TWO = E_RECENT + ("p28_flow_e31_two",)
E31_MORE = E_RECENT + ("p28_flow_e31_more_than_two",)

PAGE_28 = (
    *paired(
        28,
        ("line", 1),
        "p28_e27_strike",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E27 prints a strike-related work exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(28, 3, "(GO TO E29)", F, "p28_flow_e27_no", routes=(E_RECENT,)),
    *paired(
        28,
        ("line", 4),
        "p28_e28_strike_amount",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E28 prints strike-related missed-work duration.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 8),
        "p28_e29_unemployment",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E29 prints unemployment or layoff exposure.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(28, 10, "(GO TO E33)", F, "p28_flow_e29_no", routes=(E_RECENT,)),
    *paired(
        28,
        ("line", 12),
        "p28_e30_unemployment_amount",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E30 prints unemployment or layoff duration.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("block", 15, 16),
        "p28_e31_unemployment_spells",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E31 prints the unemployment-spell classification.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        28,
        18,
        "I 1. ALL IN ONE STRETCH I",
        F,
        "p28_flow_e31_one",
        routes=(E_RECENT,),
    ),
    word(
        28,
        20,
        "~ TWO PERIODS I",
        F,
        "p28_flow_e31_two",
        routes=(E_RECENT,),
    ),
    word(
        28,
        23,
        "MORE TH.A3",
        F,
        "p28_flow_e31_more_than_two",
        routes=(E_RECENT,),
    ),
    word(
        28,
        24,
        "(GO TO E33)",
        F,
        "p28_flow_e31_exit",
        routes=(E31_ONE, E31_TWO),
    ),
    *paired(
        28,
        ("block", 25, 26),
        "p28_e32_unemployment_count",
        parents=("p26_job_last",),
        routes=(E31_MORE,),
        note="E32 prints the number of unemployment periods.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 30),
        "p28_e33_weeks",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E33 prints weeks worked in 1976.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 34),
        "p28_e34_hours",
        parents=("p26_job_last",),
        routes=(E_RECENT,),
        note="E34 prints average weekly hours worked.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        28,
        41,
        "(TURN TO PAGE 17 , Gl)",
        F,
        "p28_flow_e35_none",
        routes=(E_RECENT,),
    ),
)


PAGE_30 = (
    tail(
        30,
        1,
        "SECTION F:",
        F,
        "p30_flow_section_f",
        note="Printed section F header opening the inactive-head schedule.",
    ),
    line(30, 4, P, "p30_f1_prompt", routes=(SEC_F,)),
    *paired(
        30,
        ("line", 15),
        "p30_f3_actual_work",
        routes=(SEC_F,),
        note="F3 prints whether the head did work for money in 1976.",
    ),
    word(
        30,
        22,
        "(TURN TO PAGE 16 , Fl 4)",
        F,
        "p30_flow_f4_no",
        routes=(SEC_F,),
    ),
    word(
        30,
        26,
        "(TURN TO PAGE 16, Fl4",
        F,
        "p30_flow_f5_exit",
        routes=(SEC_F,),
    ),
    *paired(
        30,
        ("line", 30),
        "p30_f6_occupation",
        routes=(SEC_F,),
        note="F6 prints the occupation of actual 1976 work.",
    ),
    *paired(
        30,
        ("line", 34),
        "p30_f7_industry",
        routes=(SEC_F,),
        note="F7 prints the industry of actual 1976 work.",
    ),
    *paired(
        30,
        ("line", 36),
        "p30_f8_weeks",
        routes=(SEC_F,),
        note="F8 prints weeks worked in 1976.",
    ),
    *paired(
        30,
        ("line", 38),
        "p30_f9_hours",
        routes=(SEC_F,),
        note="F9 prints average weekly hours worked.",
    ),
    *paired(
        30,
        ("line", 41),
        "p30_f10_still_working",
        routes=(SEC_F,),
        note="F10 prints current-work assignment.",
    ),
    word(30, 43, "(GO TO Fl2)", F, "p30_flow_f10_yes", routes=(SEC_F,)),
    *paired(
        30,
        ("block", 45, 46),
        "p30_f11_job_outcome",
        routes=(SEC_F,),
        note="F11 prints the disposition of that actual-work job.",
    ),
    word(
        30,
        53,
        "(TURN TO PAGE 16' Fl4)",
        F,
        "p30_flow_f12_no",
        routes=(SEC_F,),
    ),
)


PAGE_32 = (
    word(
        32,
        4,
        '1. " YE S" TO TH I NKING',
        F,
        "p32_flow_f14_thinking_yes",
        routes=(SEC_F,),
    ),
    word(
        32,
        4,
        '5. " NOu TO THINKI NG',
        F,
        "p32_flow_f14_thinking_no",
        routes=(SEC_F,),
    ),
    *paired(
        32,
        ("line", 11),
        "p32_f15_occupation",
        parents=("p32_job_sought",),
        routes=(F_THINKING,),
        note="F15, whose identifier extracts as FU5, prints the occupation "
        "of the job in mind.",
        parent_note="Parent job is F15's job-in-mind noun.",
    ),
    word(
        32,
        11,
        "j ob",
        J,
        "p32_job_sought",
        routes=(F_THINKING,),
        note="F15 establishes the job the head has in mind.",
    ),
    *paired(
        32,
        ("line", 13),
        "p32_f16_expected_earnings",
        anchor_kind=M,
        parents=("p32_job_sought",),
        routes=(F_THINKING,),
        note="F16 prints expected earnings and reporting unit.",
        parent_note="Parent job is F15's job-in-mind noun.",
    ),
    word(32, 17, "(GO TO F20)", F, "p32_flow_f17_no", routes=(F_THINKING,)),
    word(32, 33, "(GO TO F2 2)", F, "p32_flow_f20_no", routes=(F_THINKING,)),
    word(
        32,
        49,
        "(TURN TO PAGE 17. Gl)",
        F,
        "p32_flow_f24_no",
        routes=(F_THINKING,),
    ),
)


PAGE_34 = (
    tail(
        34,
        1,
        "SECTION G:",
        F,
        "p34_flow_section_g",
        note="Printed section G header opening the wife-work schedule.",
    ),
    word(34, 1, "WIFE ' S", R, "p34_role_wife_header", routes=(SEC_G,)),
    word(
        34,
        9,
        "(GO TO G4)",
        F,
        "p34_flow_g1_married",
        routes=(SEC_G,),
    ),
    word(
        34,
        10,
        "(GO TO G4)",
        F,
        "p34_flow_g1_divorced",
        routes=(SEC_G,),
    ),
    word(
        34,
        15,
        "(GO TO G4)",
        F,
        "p34_flow_g2_no",
        routes=(SEC_G,),
    ),
    block(34, 25, 31, P, "p34_g4_prompt", routes=(SEC_G,)),
    word(
        34,
        28,
        "l . :7IALE HEAD IS :HARRIED",
        F,
        "p34_flow_g4_eligible",
        routes=(SEC_G,),
    ),
    word(
        34,
        28,
        "5. ALL OTHERS",
        F,
        "p34_flow_g4_all_others",
        routes=(SEC_G,),
    ),
    word(
        34,
        33,
        "(TURN TO PAGE 20 , G33)",
        F,
        "p34_flow_g4_exit",
        routes=(G_ALL_OTHERS,),
    ),
    *paired(
        34,
        ("line", 36),
        "p34_g5_actual_work",
        routes=(G_ELIGIBLE,),
        note="G5 prints the wife's 1976 work attachment.",
    ),
    word(
        34,
        36,
        "(wife/f r iend)",
        R,
        "p34_role_wife_g5",
        routes=(G_ELIGIBLE,),
    ),
    word(
        34,
        38,
        "(TURN TO PAGE 19' G23)",
        F,
        "p34_flow_g5_no",
        routes=(G_ELIGIBLE,),
    ),
    *paired(
        34,
        ("line", 41),
        "p34_g6_occupation",
        routes=(G_ELIGIBLE,),
        note="G6 prints the wife's occupation.",
    ),
    *paired(
        34,
        ("line", 45),
        "p34_g7_industry",
        routes=(G_ELIGIBLE,),
        note="G7 prints the wife's industry.",
    ),
)


PAGE_36 = (
    *paired(
        36,
        ("block", 1, 2),
        "p36_g8_other_sick",
        routes=(G_ELIGIBLE,),
        note="G8 prints the wife's missed-work exposure.",
    ),
    word(
        36,
        1,
        "(wife/ friend)",
        R,
        "p36_role_wife_g8",
        routes=(G_ELIGIBLE,),
    ),
    word(36, 6, "(GO TO Gll)", F, "p36_flow_g8_no", routes=(G_ELIGIBLE,)),
    line(36, 9, P, "p36_g9_prompt", routes=(G_ELIGIBLE,)),
    *paired(
        36,
        ("line", 13),
        "p36_g10_other_sick_amount",
        routes=(G_ELIGIBLE,),
        note="G10 prints missed-work duration.",
    ),
    *paired(
        36,
        ("line", 17),
        "p36_g11_own_sick",
        routes=(G_ELIGIBLE,),
        note="G11 prints the wife's own-sickness exposure.",
    ),
    word(
        36,
        17,
        "(wife/friend)",
        R,
        "p36_role_wife_g11",
        routes=(G_ELIGIBLE,),
    ),
    word(36, 19, "(GO TO G13)", F, "p36_flow_g11_no", routes=(G_ELIGIBLE,)),
    *paired(
        36,
        ("block", 20, 22),
        "p36_g12_own_sick_amount",
        routes=(G_ELIGIBLE,),
        note="G12 prints own-sickness missed-work duration.",
    ),
    *paired(
        36,
        ("line", 25),
        "p36_g13_vacation",
        routes=(G_ELIGIBLE,),
        note="G13 prints the wife's vacation exposure.",
    ),
    word(
        36,
        25,
        "(wife/fr i end)",
        R,
        "p36_role_wife_g13",
        routes=(G_ELIGIBLE,),
    ),
    word(36, 27, "(GO TO Gl5)", F, "p36_flow_g13_no", routes=(G_ELIGIBLE,)),
    *paired(
        36,
        ("block", 29, 31),
        "p36_g14_vacation_amount",
        routes=(G_ELIGIBLE,),
        note="G14 prints vacation or time-off duration.",
    ),
    *paired(
        36,
        ("line", 35),
        "p36_g15_strike",
        routes=(G_ELIGIBLE,),
        note="G15 prints the wife's strike-related exposure.",
    ),
    word(
        36,
        35,
        "(wife/friend)",
        R,
        "p36_role_wife_g15",
        routes=(G_ELIGIBLE,),
    ),
    word(36, 37, "(GO TO Gl7)", F, "p36_flow_g15_no", routes=(G_ELIGIBLE,)),
    *paired(
        36,
        ("line", 42),
        "p36_g16_strike_amount",
        routes=(G_ELIGIBLE,),
        note="G16 prints strike-related missed-work duration.",
    ),
    *paired(
        36,
        ("block", 46, 47),
        "p36_g17_unemployment",
        routes=(G_ELIGIBLE,),
        note="G17 prints the wife's unemployment or layoff exposure.",
    ),
    word(
        36,
        46,
        "(wife/friend)",
        R,
        "p36_role_wife_g17",
        routes=(G_ELIGIBLE,),
    ),
    word(
        36,
        49,
        "(TURN TO PAGE 19~ G21)",
        F,
        "p36_flow_g17_no",
        routes=(G_ELIGIBLE,),
    ),
    *paired(
        36,
        ("line", 52),
        "p36_g18_unemployment_amount",
        routes=(G_ELIGIBLE,),
        note="G18 prints unemployment or layoff duration.",
    ),
    *paired(
        36,
        ("block", 55, 56),
        "p36_g19_unemployment_spells",
        routes=(G_ELIGIBLE,),
        note="G19 prints the unemployment-spell classification.",
    ),
    word(
        36,
        58,
        "1. ALL IN ONE STRETCH",
        F,
        "p36_flow_g19_one",
        routes=(G_ELIGIBLE,),
    ),
    word(
        36,
        58,
        "3 . TWO PERIODS",
        F,
        "p36_flow_g19_two",
        routes=(G_ELIGIBLE,),
    ),
    word(
        36,
        58,
        "5 . MORE TI:-IAN    r..;o",
        F,
        "p36_flow_g19_more_than_two",
        routes=(G_ELIGIBLE,),
    ),
    word(
        36,
        59,
        "(TUR..T\\1 TO PAGE 19, G21)",
        F,
        "p36_flow_g19_exit",
        routes=(G19_ONE, G19_TWO),
    ),
    *paired(
        36,
        ("line", 60),
        "p36_g20_unemployment_count",
        routes=(G19_MORE,),
        note="G20 prints the number of unemployment periods.",
    ),
)


PAGE_38 = (
    *paired(
        38,
        ("line", 16),
        "p38_g21_weeks",
        parents=("p38_job_main",),
        routes=(G_ELIGIBLE,),
        note="G21 prints weeks worked on the wife's main job.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        38,
        16,
        "main job",
        J,
        "p38_job_main",
        routes=(G_ELIGIBLE,),
        note="G21 establishes the wife's main job.",
    ),
    *paired(
        38,
        ("line", 18),
        "p38_g22_hours",
        parents=("p38_job_main",),
        routes=(G_ELIGIBLE,),
        note="G22 prints average weekly hours on the wife's main job.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        38,
        30,
        "CHILD/ CHILDREN UNDER 12",
        F,
        "p38_flow_g23_children",
        routes=(G_ELIGIBLE,),
    ),
    word(
        38,
        30,
        "5 . NO CHILDREN UNDER 12",
        F,
        "p38_flow_g23_no_children",
        routes=(G_ELIGIBLE,),
    ),
    *paired(
        38,
        ("line", 33),
        "p38_g24_current_work",
        routes=(G_CHILDREN,),
        note="G24 prints the wife's current-work assignment; child-care "
        "fields later on the screen remain outside R_Q.",
    ),
    word(
        38,
        33,
        "(wife/friend)",
        R,
        "p38_role_wife_g24",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        34,
        "(TURN TO PAGE 20 , G31)",
        F,
        "p38_flow_g24_no",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        45,
        "(GO TO G29)",
        F,
        "p38_flow_g27_no",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        56,
        "1. FAIRLY OFTEN ;",
        F,
        "p38_flow_g29_often",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        56,
        "2 . ONCE",
        F,
        "p38_flow_g29_monthly",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        56,
        "3. ONCE IN A",
        F,
        "p38_flow_g29_sometimes",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        56,
        "4 . RARELY ;",
        F,
        "p38_flow_g29_rarely",
        routes=(G_CHILDREN,),
    ),
    word(
        38,
        64,
        "(TURN TO PAGE 20, G31)",
        F,
        "p38_flow_g30_exit",
        routes=(G_CHILDREN,),
    ),
)


PAGE_46 = (
    tail(
        46,
        2,
        "SECTION H:",
        F,
        "p46_flow_section_h",
        note="Printed section H header opening the family income schedule.",
    ),
    word(
        46,
        15,
        "1 . FARMER, OR RANCHER",
        F,
        "p46_flow_h1_farmer",
        routes=(SEC_H,),
    ),
    word(
        46,
        15,
        "5 . NOT A FARMER OR RANCHER",
        F,
        "p46_flow_h1_not_farmer",
        routes=(SEC_H,),
    ),
    word(
        46,
        15,
        "<GO TO H5)",
        F,
        "p46_flow_h1_exit",
        routes=(H_NOT_FARMER,),
    ),
    *paired(
        46,
        ("block", 17, 18),
        "p46_h2_farm_receipts",
        anchor_kind=M,
        parents=("p46_farm_aggregate",),
        routes=(H_FARMER,),
        note="H2 prints total farm receipts.",
        parent_note=_FARM_PARENT,
    ),
    *paired(
        46,
        ("block", 20, 21),
        "p46_h3_farm_expenses",
        anchor_kind=M,
        parents=("p46_farm_aggregate",),
        routes=(H_FARMER,),
        note="H3 prints farm operating expenses as a signed component.",
        parent_note=_FARM_PARENT,
    ),
    word(
        46,
        23,
        "net income from farming",
        FA,
        "p46_farm_aggregate",
        routes=(H_FARMER,),
        note="H4 prints the net-farm-income aggregate.",
    ),
    line(46, 23, P, "p46_h4_prompt", routes=(H_FARMER,)),
    block(46, 27, 28, P, "p46_h5_prompt", routes=(SEC_H,)),
    *paired(
        46,
        ("block", 31, 32),
        "p46_h6_incorporation",
        parents=("p46_business_aggregate",),
        routes=(SEC_H,),
        note="H6 prints corporation versus unincorporated-business status.",
        parent_note=_BUSINESS_PARENT,
    ),
    word(
        46,
        31,
        "unincorporated business",
        BA,
        "p46_business_aggregate",
        routes=(SEC_H,),
        note="H6 prints the unincorporated-business aggregate label.",
    ),
    word(
        46,
        35,
        "II. CORPORATION I",
        F,
        "p46_flow_h6_corporation",
        routes=(SEC_H,),
    ),
    word(
        46,
        35,
        "GO TO H8)",
        F,
        "p46_flow_h6_corporation_exit",
        routes=(H_CORPORATION,),
    ),
    word(
        46,
        36,
        "2 UNINCORPORATED I",
        F,
        "p46_flow_h6_unincorporated",
        routes=(SEC_H,),
    ),
    word(46, 37, "3~ BOTHj", F, "p46_flow_h6_both", routes=(SEC_H,)),
    word(
        46,
        38,
        "( 8 . DON'T KNOW",
        F,
        "p46_flow_h6_dont_know",
        routes=(SEC_H,),
    ),
    *paired(
        46,
        ("block", 40, 42),
        "p46_h7_business_share",
        anchor_kind=M,
        parents=("p46_business_aggregate",),
        routes=(H_UNINCORPORATED, H_BOTH, H_DONT_KNOW),
        note="H7 prints the family share of unincorporated-business income.",
        parent_note=_BUSINESS_PARENT,
    ),
    *paired(
        46,
        ("block", 48, 49),
        "p46_h8_wages",
        anchor_kind=M,
        routes=(SEC_H,),
        note="H8 prints the head's 1976 wages and salaries.",
    ),
    word(46, 48, "HEAD", R, "p46_role_head_h8", routes=(SEC_H,)),
)


PAGE_49 = (
    *paired(
        49,
        ("block", 3, 4),
        "p49_h9_bonus_overtime_commission",
        anchor_kind=M,
        routes=(SEC_H,),
        note="H9 prints bonuses, overtime, and commissions as one component.",
    ),
    word(49, 9, "(GO TO Hll)", F, "p49_flow_h9_no", routes=(SEC_H,)),
    line(49, 11, P, "p49_h10_prompt", routes=(SEC_H,)),
    line(49, 13, P, "p49_h11_prompt", routes=(SEC_H,)),
    word(49, 13, "HEAD", R, "p49_role_head_h11", routes=(SEC_H,)),
    word(
        49,
        15,
        "a) professional practice or trade?",
        M,
        "p49_h11a_professional_trade",
        routes=(SEC_H,),
        note="H11a prints the professional-practice-or-trade component.",
    ),
    word(
        49,
        17,
        "b) farming or market gardening,",
        M,
        "p49_h11b_farming_gardening",
        routes=(SEC_H,),
        note="H11b prints farming or market gardening as a component.",
    ),
    word(
        49,
        18,
        "roomers or boarders?",
        M,
        "p49_h11b_roomers_boarders",
        routes=(SEC_H,),
        note="H11b's continuation prints roomers or boarders as a distinct "
        "component label.",
    ),
    word(
        49,
        47,
        "(TURN TO PAGE 25 , H14)",
        F,
        "p49_flow_h12_no",
        routes=(SEC_H,),
    ),
)


PAGE_53 = (
    word(
        53,
        4,
        "(GO TO Hl8)",
        F,
        "p53_flow_h14_no",
        routes=(SEC_H,),
    ),
    word(
        53,
        12,
        "(GO TO Hl7)",
        F,
        "p53_flow_h15_no",
        routes=(SEC_H,),
    ),
    line(53, 27, P, "p53_h18_prompt", routes=(SEC_H,)),
    word(53, 27, "HEAD", R, "p53_role_head_h18", routes=(SEC_H,)),
    word(
        53,
        27,
        "WIFE OR FEMALE FRIEND",
        R,
        "p53_role_wife_h18",
        routes=(SEC_H,),
    ),
    word(
        53,
        29,
        "I YES , f 'IFE/FRIEND IN FU I",
        F,
        "p53_flow_h18_wife_present",
        routes=(SEC_H,),
    ),
    word(
        53,
        29,
        "I NO WIFE/FRIEND IN FU OR FU )lAS FEMALE HEAD I",
        F,
        "p53_flow_h18_no_wife",
        routes=(SEC_H,),
    ),
    word(
        53,
        30,
        "(GO TO H24)",
        F,
        "p53_flow_h18_no_wife_exit",
        routes=(H_NO_WIFE,),
    ),
    *paired(
        53,
        ("line", 31),
        "p53_h19_wife_income_presence",
        routes=(H_WIFE,),
        note="H19 prints whether the wife or friend received any income; it "
        "is not a printed total-income amount.",
    ),
    word(
        53,
        31,
        "(wife/friend)",
        R,
        "p53_role_wife_h19",
        routes=(H_WIFE,),
    ),
    word(
        53,
        32,
        "( GO . TO H24)",
        F,
        "p53_flow_h19_no",
        routes=(H_WIFE,),
    ),
    *paired(
        53,
        ("line", 33),
        "p53_h20_income_source",
        routes=(H_WIFE,),
        note="H20 prints the wife-income source classification.",
    ),
    *paired(
        53,
        ("line", 36),
        "p53_h21_wife_income_amount",
        anchor_kind=M,
        routes=(H_WIFE,),
        note="H21 prints wife income before deductions.",
    ),
    word(
        53,
        40,
        "(GO TO H24)",
        F,
        "p53_flow_h22_no",
        routes=(H_WIFE,),
    ),
    *paired(
        53,
        ("block", 45, 48),
        "p53_h24_social_security",
        routes=(SEC_H,),
        note="H24 prints the Head/Wife Social Security-income checkpoint as "
        "public-retirement-system context.",
    ),
    word(53, 46, "HEAD", R, "p53_role_head_h24", routes=(SEC_H,)),
    word(53, 46, "WIFE", R, "p53_role_wife_h24", routes=(SEC_H,)),
    word(
        53,
        46,
        "1 . HEAD/WIFE HAS",
        F,
        "p53_flow_h24_social_security",
        routes=(SEC_H,),
    ),
    word(53, 46, "5. NO", F, "p53_flow_h24_no", routes=(SEC_H,)),
    word(
        53,
        46,
        "(TURN TO PAGE 26, H26)",
        F,
        "p53_flow_h24_no_exit",
        routes=(H24_NO,),
    ),
    *paired(
        53,
        ("line", 50),
        "p53_h25_medicare",
        routes=(H24_POSITIVE,),
        note="H25 prints Medicare-from-Social-Security participation context.",
    ),
    word(
        53,
        50,
        "wife/friend",
        R,
        "p53_role_wife_h25",
        routes=(H24_POSITIVE,),
    ),
)


PAGE_63 = (
    word(
        63,
        3,
        "SECTION J:",
        F,
        "p63_flow_section_j",
        note="Printed section J header opening the new-wife schedule.",
    ),
    word(
        63,
        3,
        "NEW WIFE",
        R,
        "p63_role_new_wife",
        routes=(SEC_J,),
    ),
    word(
        63,
        10,
        "HAS NEH (iVIFE/PERMAN:ENT I",
        F,
        "p63_flow_j1_new_wife",
        routes=(SEC_J,),
    ),
    word(
        63,
        10,
        "5. FU HAS SAME (WIFE/PERMANENT FRIEND) AS",
        F,
        "p63_flow_j1_same_wife",
        routes=(SEC_J,),
    ),
    word(63, 22, "(GO TO J8)", F, "p63_flow_j3_no", routes=(J_NEW_WIFE,)),
    word(63, 25, "(GO TO J8)", F, "p63_flow_j6_no", routes=(J_NEW_WIFE,)),
    word(63, 32, "(GO TO J8)", F, "p63_flow_j4_exit", routes=(J_NEW_WIFE,)),
    word(63, 34, "(GO TO J8)", F, "p63_flow_j7_exit", routes=(J_NEW_WIFE,)),
    *paired(
        63,
        ("line", 43),
        "p63_j10_years_worked",
        routes=(J_NEW_WIFE,),
        note="J10 prints the new wife's lifetime years-worked exposure.",
    ),
    word(
        63,
        45,
        "I 00. NONE I",
        F,
        "p63_flow_j10_none",
        routes=(J_NEW_WIFE,),
    ),
    word(
        63,
        45,
        "(TURN TO PAGE 31, Kl)",
        F,
        "p63_flow_j10_none_exit",
        routes=(J10_NONE,),
    ),
    *paired(
        63,
        ("line", 46),
        "p63_j11_years_full_time",
        routes=(J_NEW_WIFE,),
        note="J11 prints lifetime full-time years.",
    ),
    word(63, 48, "I ALL I", F, "p63_flow_j11_all", routes=(J_NEW_WIFE,)),
    word(
        63,
        48,
        "(TURN TO PAGE 31 , Kl)",
        F,
        "p63_flow_j11_all_exit",
        routes=(J11_ALL,),
    ),
    *paired(
        63,
        ("block", 50, 51),
        "p63_j12_part_time_share",
        routes=(J_NEW_WIFE,),
        note="J12 prints the share of non-full-time years worked.",
    ),
)


PAGE_65 = (
    word(
        65,
        3,
        "I 1. FU HAS A NEW HEAD THIS YEAR I",
        F,
        "p65_flow_k1_new_head",
        routes=((),),
    ),
    word(
        65,
        3,
        "I 5. THIS FU HAS THE SAME HEAD AS IN 1976",
        F,
        "p65_flow_k1_same_head",
        routes=((),),
    ),
    word(65, 3, "NEW HEAD", R, "p65_role_new_head", routes=(K_NEW_HEAD,)),
    word(
        65,
        4,
        "(TURN TO PAGE 3 OF COVER SHEET)",
        F,
        "p65_flow_k1_same_head_exit",
        routes=(K_SAME_HEAD,),
    ),
    *paired(
        65,
        ("line", 20),
        "p65_k4_first_job_occupation",
        parents=("p65_job_first_full_time",),
        routes=(K_NEW_HEAD,),
        note="K4 prints the occupation of the new head's first full-time "
        "regular job.",
        parent_note="Parent job is K4's first-full-time-job noun.",
    ),
    word(
        65,
        20,
        "(HEAD'S)",
        R,
        "p65_role_head_k4",
        routes=(K_NEW_HEAD,),
    ),
    word(
        65,
        20,
        "first full time regular job",
        J,
        "p65_job_first_full_time",
        routes=(K_NEW_HEAD,),
        note="K4 establishes the new head's first full-time regular job.",
    ),
    word(
        65,
        22,
        "(GO TO K6)",
        F,
        "p65_flow_k4_never_worked",
        routes=(K_NEW_HEAD,),
    ),
    *paired(
        65,
        ("block", 24, 25),
        "p65_k5_occupation_count",
        routes=(K_NEW_HEAD,),
        note="K5 prints occupational continuity and number-of-occupations "
        "work history.",
    ),
    word(65, 33, "(GO TO K9)", F, "p65_flow_k6_no", routes=(K_NEW_HEAD,)),
    word(
        65,
        47,
        "(TURN TO PAGE 3~. • Kll)",
        F,
        "p65_flow_k9_no",
        routes=(K_NEW_HEAD,),
    ),
)


PAGE_69 = (
    word(
        69,
        6,
        "I 00. NONE I",
        F,
        "p69_flow_k25_none",
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        6,
        "(GO TO K28)",
        F,
        "p69_flow_k25_none_exit",
        routes=(K25_NONE,),
    ),
    *paired(
        69,
        ("line", 7),
        "p69_k26_years_full_time",
        routes=(K_NEW_HEAD,),
        note="K26 prints the new head's lifetime full-time years.",
    ),
    word(
        69,
        9,
        "I ALL I",
        F,
        "p69_flow_k26_all",
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        9,
        "(GO TO K28)",
        F,
        "p69_flow_k26_all_exit",
        routes=(K26_ALL,),
    ),
    *paired(
        69,
        ("block", 10, 11),
        "p69_k27_part_time_share",
        routes=(K_NEW_HEAD,),
        note="K27 prints the share of non-full-time years worked.",
    ),
    word(
        69,
        32,
        "(GO TO K31)",
        F,
        "p69_flow_k29_no",
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        55,
        "(GO TO K37)",
        F,
        "p69_flow_k31_exit",
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        55,
        "(GO TO K37)",
        F,
        "p69_flow_k33_exit",
        1,
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        55,
        "(GO TO K37)",
        F,
        "p69_flow_k36_exit",
        2,
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        64,
        "(TURN TO PAGE 3 OF COVER SHEET)",
        F,
        "p69_flow_k38_exit",
        routes=(K_NEW_HEAD,),
    ),
    word(
        69,
        70,
        "(TURN TO PAGE 3 OF COVER SHEET)",
        F,
        "p69_flow_k39_exit",
        routes=(K_NEW_HEAD,),
    ),
)


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
    )


def _unresolved_repeat(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    note: str,
) -> dict[str, Any]:
    return spec(
        page,
        A,
        selector,
        key,
        note=note,
        relation=REPEAT,
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    )


CROSS_REFERENCES = (
    _xref(
        21,
        ("line", 35),
        "p21_xref_d59_to_d2_d3",
        ("p20_d59_occupation",),
        ("p11_d2_occupation",),
        "D59/D60 explicitly reuse the D2/D3 occupation instructions.",
    ),
    _unresolved_repeat(
        21,
        ("from", 40, "If R has more than one extra", 41, 0),
        "p21_repeat_extra_jobs",
        "The interviewer must obtain hourly pay for each separately reported "
        "extra job; equivalence is not inferred.",
    ),
    _xref(
        25,
        ("from", 9, "See the objectives for D2, D3; they apply", 10, 0),
        "p25_xref_e1_to_d2_d3",
        ("p24_e1_occupation",),
        ("p11_d2_occupation",),
        "E1 explicitly reuses the D2/D3 occupation instructions.",
    ),
    _xref(
        27,
        ("line", 5),
        "p27_xref_e15_to_d2_d3",
        ("p26_e15_occupation",),
        ("p11_d2_occupation",),
        "E15 explicitly reuses the D2/D3 occupation instructions.",
    ),
    _xref(
        27,
        ("line", 8),
        "p27_xref_e16_to_d4",
        ("p26_e16_industry",),
        ("p11_d4_industry",),
        "E16 explicitly reuses the D4 industry instructions.",
    ),
    _xref(
        27,
        ("line", 11),
        "p27_xref_e18_to_d28",
        ("p26_e18_job_outcome",),
        ("p16_d28_previous_job_outcome",),
        "E18 explicitly reuses the D28 prior-job disposition instructions.",
    ),
    _xref(
        27,
        ("line", 14),
        "p27_xref_e20_e21_to_d37_d39",
        ("p26_e20_vacation", "p26_e21_vacation_amount"),
        (
            "p16_d37_paid_vacation",
            "p16_d38_vacation",
            "p16_d39_vacation_amount",
        ),
        "The exact OCR label E2Q-21 cross-references D37-D39.",
    ),
    _xref(
        27,
        ("line", 16),
        "p27_xref_e22_e26_to_d32_d36",
        (
            "p26_e22_other_sick",
            "p26_e24_other_sick_amount",
            "p26_e25_own_sick",
            "p26_e26_own_sick_amount",
        ),
        (
            "p16_d32_other_sick",
            "p16_d34_other_sick_amount",
            "p16_d35_own_sick",
            "p16_d36_own_sick_amount",
        ),
        "E22-E26 explicitly reuse D32-D36.",
    ),
    _xref(
        29,
        ("line", 5),
        "p29_xref_e29_e32_to_d42_d45",
        (
            "p28_e29_unemployment",
            "p28_e30_unemployment_amount",
            "p28_e31_unemployment_spells",
            "p28_e32_unemployment_count",
        ),
        (
            "p18_d42_unemployment",
            "p18_d43_unemployment_amount",
            "p18_d44_unemployment_spells",
            "p18_d45_unemployment_count",
        ),
        "E29-E32 explicitly reuse D42-D45.",
    ),
    _xref(
        31,
        ("line", 17),
        "p31_xref_f6_to_d2_d3",
        ("p30_f6_occupation",),
        ("p11_d2_occupation",),
        "F6 explicitly reuses D2/D3 occupation instructions.",
    ),
    _xref(
        31,
        ("line", 20),
        "p31_xref_f7_to_d4",
        ("p30_f7_industry",),
        ("p11_d4_industry",),
        "F7 explicitly reuses D4 industry instructions.",
    ),
    _xref(
        35,
        ("line", 23),
        "p35_xref_g6_g7_to_d2_d3",
        ("p34_g6_occupation", "p34_g7_industry"),
        (),
        "The exact source says G6-7 reuse D2-3. D3 is not an anchor and the "
        "source does not name D4, so the endpoint is preserved unresolved.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        37,
        ("block", 5, 6),
        "p37_xref_g8_g20_to_head_sections",
        (
            "p36_g8_other_sick",
            "p36_g10_other_sick_amount",
            "p36_g11_own_sick",
            "p36_g12_own_sick_amount",
            "p36_g13_vacation",
            "p36_g14_vacation_amount",
            "p36_g15_strike",
            "p36_g16_strike_amount",
            "p36_g17_unemployment",
            "p36_g18_unemployment_amount",
            "p36_g19_unemployment_spells",
            "p36_g20_unemployment_count",
        ),
        (),
        "The exact OCR label GB-20 broadly reuses head D/E work-time detail; "
        "the source does not provide a one-to-one endpoint map.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        47,
        ("line", 8),
        "p47_xref_nonfarmer_farm_to_h11b",
        ("p49_h11b_farming_gardening",),
        ("p46_farm_aggregate",),
        "H1 routes nonfarmer farm income to H11b rather than H2-H4.",
    ),
    _xref(
        48,
        ("block", 18, 21),
        "p48_xref_h8_business_wages_to_h7",
        ("p46_h8_wages",),
        ("p46_h7_business_share",),
        "The H8 instruction routes an unincorporated owner's own pay to H7 "
        "and wages from another job to H8.",
    ),
    _xref(
        48,
        ("block", 23, 24),
        "p48_xref_h8_h7_no_double_count",
        ("p46_h8_wages",),
        ("p46_h7_business_share",),
        "The instruction explicitly prevents duplicating one amount in H7 "
        "and H8.",
    ),
    _xref(
        50,
        ("block", 4, 7),
        "p50_xref_h9_h10_to_h8_no_double_count",
        ("p49_h9_bonus_overtime_commission", "p46_h8_wages"),
        (),
        "H9-H10 explicitly prevent re-entering bonus, overtime, or "
        "commission income already included in H8.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        50,
        (
            "from",
            19,
            "This may already be included",
            21,
            0,
        ),
        "p50_xref_h11a_professional_to_h7_h8",
        (
            "p49_h11a_professional_trade",
            "p46_h7_business_share",
            "p46_h8_wages",
        ),
        (),
        "The professional-practice instruction conditionally prevents "
        "repeating an amount already included in H7 or H8.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        50,
        (
            "needle",
            26,
            "If included in H7 or H8, do not repeat it here.",
            0,
        ),
        "p50_xref_h11a_trade_to_h7_h8",
        (
            "p49_h11a_professional_trade",
            "p46_h7_business_share",
            "p46_h8_wages",
        ),
        (),
        "The trade instruction conditionally prevents repeating an amount "
        "already included in H7 or H8.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        50,
        ("block", 28, 32),
        "p50_xref_h11b_to_h2_h4",
        ("p49_h11b_farming_gardening",),
        (
            "p46_h2_farm_receipts",
            "p46_h3_farm_expenses",
            "p46_farm_aggregate",
        ),
        "H11b explicitly routes a primary farmer's income to H2-H4.",
    ),
    _xref(
        53,
        ("line", 45),
        "p53_xref_h24_to_h11f_h20",
        ("p53_h24_social_security", "p53_h20_income_source"),
        (),
        "H24 explicitly refers to H11f and H20; H11f is outside the retained "
        "work-income component set, so the partial local evidence remains "
        "unresolved and cannot collapse the distinct H24/H20 contexts.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        54,
        ("block", 38, 40),
        "p54_xref_h21_to_h7",
        ("p53_h21_wife_income_amount",),
        ("p46_h7_business_share",),
        "The wife-income instruction says family-business work income may "
        "already be included in H7.",
    ),
    _xref(
        54,
        ("block", 41, 45),
        "p54_xref_h20_h24_social_security_no_double_count",
        (
            "p53_h20_income_source",
            "p53_h21_wife_income_amount",
            "p53_h24_social_security",
        ),
        (),
        "The wife-income objective says Social or Supplemental Security "
        "checks must be recorded while identifying prior inclusion to avoid "
        "double counting. H11f and an OCR-lost continuation prevent complete "
        "document-local endpoint resolution.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        66,
        ("line", 24),
        "p66_xref_k4_to_d2_d3",
        ("p65_k4_first_job_occupation",),
        ("p11_d2_occupation",),
        "K4 explicitly reuses D2/D3 occupation instructions. This is a "
        "component-instruction link, not a job-identity assertion.",
    ),
)


REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_11,
    *PAGE_14,
    *PAGE_16,
    *PAGE_18,
    *PAGE_20,
    *PAGE_24,
    *PAGE_26,
    *PAGE_28,
    *PAGE_30,
    *PAGE_32,
    *PAGE_34,
    *PAGE_36,
    *PAGE_38,
    *PAGE_46,
    *PAGE_49,
    *PAGE_53,
    *PAGE_63,
    *PAGE_65,
    *PAGE_69,
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
            path = []
            for parent_key in route:
                if parent_key not in branch_ref_by_key:
                    raise SpecError(
                        f"{row['key']} routes through unresolved "
                        f"{parent_key}"
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
                "parent_resolution_note": row.get("parent_note")
                or (
                    "Parent job or aggregate is named in the same printed "
                    "question block."
                    if parents
                    else "No printed parent job or aggregate on this screen; "
                    "parenting is deferred to global assembly."
                ),
                "classification_status": "provisional_document_local",
            }
        )

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
        order = {
            spec_row["review_occurrence_id"]: position
            for position, spec_row in enumerate(occurrence_specs)
        }
        repeat_specs.append(
            {
                "review_occurrence_id": row["review_occurrence_id"],
                "relation": row["relation"],
                "alias_anchor_review_occurrence_ids": sorted(
                    set(alias_ids), key=order.__getitem__
                ),
                "canonical_anchor_review_occurrence_ids": sorted(
                    set(canonical_ids), key=order.__getitem__
                ),
                "evidence_review_occurrence_ids": sorted(
                    set(evidence), key=order.__getitem__
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
            "whole_page_review": (
                "all_74_pages_including_empty_occurrence_pages"
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
        f"document 19 source review: {len(review['occurrence_specs'])} "
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
