#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 15.

The authenticated source is the 74-page 1975 family question-by-question
manual, ``fam1975_QxQs.pdf``. Printed questionnaire screens alternate with
interviewer-objective pages. Every page was read from the independently
replayed Poppler 26.04.0 UTF-8 bytes before candidate adjudication.

The retained domain is deliberately narrow: head and spouse employment
attachment, job identity, occupation and industry, employee/self/government
context, work exposure, pay components, farm and unincorporated-business
aggregates, public-retirement context, and lifetime work history. Housing,
mobility, commuting, job-search effort, supervision, union, food, transfers,
assets, other-family-member income, health, education, and observation prose
do not enter merely because they contain worklike vocabulary.

Ordinary interviewer-objective prose is commentary rather than a printed
field. Only exact named cross-references and repeat instructions are retained
from objective pages. A job noun is retained only when it establishes a job
that parents a retained local field; later same-screen back-references do not
mint another job. H4 and H6 supply the farm and business aggregates. H11a and
H11b supply work-income components; H11c onward are nonwork income. H24 asks
only whether the wife had income, so the document prints no role-total amount.

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
import build_rq_stage2_document_015_annotation as annotation  # noqa: E402

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


_REJECTED = (
    "Every Poppler text line on page {page} was reviewed. The page prints "
    "{scope}, outside the retained R_Q employment, work-income, and "
    "work-history domain; worklike prose is not an occurrence."
)
_RETAINED = (
    "Every Poppler text line on page {page} was reviewed. The page prints "
    "{scope}; exact locatable R_Q atoms are retained and all other prose is "
    "rejected."
)
_OBJECTIVES = (
    "Every Poppler text line on page {page} was reviewed. This is "
    "question-by-question interviewer commentary for {scope}, not a printed "
    "field screen; only a listed exact cross-reference or repeat instruction "
    "is retained."
)

_PAGE_SCOPE: dict[int, tuple[str, str]] = {
    1: ("out", "the question-by-question objectives title"),
    2: ("out", "the cover sheet and section A child items"),
    3: ("objectives", "section A child items"),
    4: ("out", "section B transportation items"),
    5: ("objectives", "section B transportation items"),
    6: ("objectives", "section C housing items C1-C6"),
    7: ("out", "section C housing items C1-C6"),
    8: ("out", "section C housing and moving items C7-C16"),
    9: ("objectives", "housing items C7-C13"),
    10: ("objectives", "moving items C14-C16"),
    11: ("out", "an explicit blank-page marker"),
    12: ("out", "housing and residential-quality items C17-C27"),
    13: ("objectives", "moving and housing items C17-C38"),
    14: ("out", "residential-quality items C28-C39"),
    15: ("out", "an OCR-fragmented housing continuation"),
    16: ("in", "section D entry and head employment items D1-D13"),
    17: ("objectives", "section D assignment items D1-D13"),
    18: ("objectives", "occupation and industry items D2-D17"),
    19: ("out", "an explicit blank-page marker"),
    20: ("in", "head tenure and prior-job items D14-D23"),
    21: ("objectives", "head tenure and prior-job items D18-D23"),
    22: ("in", "head work-time items D24-D35"),
    23: ("objectives", "head work-time items D24-D35"),
    24: ("in", "head pay, pension, and extra-job items D36-D46"),
    25: ("objectives", "head pay and extra-job items D36-D46"),
    26: (
        "out",
        "counterfactual labor-supply, commuting, and job-change items",
    ),
    27: ("objectives", "counterfactual and commuting items D47-D54"),
    28: ("in", "section E sought-job, last-job, and work-time items E1-E14"),
    29: ("objectives", "section E items E1-E14"),
    30: ("out", "commuting, unacceptable-job, and mobility items E15-E23"),
    31: ("objectives", "commuting and mobility items E16-E23"),
    32: ("in", "section F actual-work and sought-job items F1-F14"),
    33: ("objectives", "section F items F1-F14"),
    34: ("in", "section G wife work items G1-G13"),
    35: ("objectives", "section G wife work items G1-G13"),
    36: ("out", "food and food-stamp items G14-G27"),
    37: ("objectives", "food and food-stamp items G14-G27"),
    38: ("in", "section H farm, business, and head wage items H1-H8"),
    39: ("objectives", "section H items H1-H6"),
    40: ("objectives", "section H business and wage items H7-H8"),
    41: ("out", "an explicit blank-page marker"),
    42: ("in", "head work-income and other-income items H9-H13"),
    43: ("objectives", "items H9-H13 and program background"),
    44: ("objectives", "work-income items H11a-H11b and nonwork income"),
    45: ("objectives", "nonwork transfer and pension items H11d-H11g"),
    46: ("objectives", "nonwork income items H11g-H13"),
    47: ("out", "an explicit blank-page marker"),
    48: ("in", "public-retirement checkpoints and wife income items H19-H26"),
    49: ("objectives", "welfare, public-retirement, and wife-income items"),
    50: ("out", "the other-family-member income grid H27-H39"),
    51: ("objectives", "the other-family-member income grid"),
    52: ("out", "continued other-family-member income columns"),
    53: ("objectives", "the repeated other-family-member grid"),
    54: ("out", "other-member income, transfers, and support items H40-H53"),
    55: ("objectives", "other-member income, transfers, and support items"),
    56: ("out", "assets, expectations, and union item H54-H59"),
    57: ("objectives", "asset and expectation items H54-H58"),
    58: ("out", "section J feelings items"),
    59: ("objectives", "section J feelings items"),
    60: ("out", "section K education items"),
    61: ("objectives", "section K education items"),
    62: ("in", "section L new-wife lifetime work-history items L1-L6"),
    63: ("objectives", "section L new-wife items"),
    64: ("in", "section M new-head and first-job items M1-M10"),
    65: ("objectives", "section M new-head items M1-M10"),
    66: ("out", "new-head family, religion, mobility, and education items"),
    67: ("objectives", "new-head background and mobility items M11-M25"),
    68: ("in", "new-head lifetime work-history and health items M26-M32"),
    69: ("objectives", "new-head work-history and health items M28-M32"),
    70: ("out", "section N interviewer-observation items"),
    71: ("objectives", "section N interviewer-observation items"),
    72: ("out", "the thumbnail-sketch title"),
    73: ("objectives", "thumbnail-sketch instructions"),
    74: ("out", "the exact empty final page"),
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


SEC_D = ("p16_flow_section_d",)
D_EMPLOYEE = SEC_D + ("p16_flow_d5_someone_else",)
D_BOTH = SEC_D + ("p16_flow_d5_both",)
D_SELF = SEC_D + ("p16_flow_d5_self",)
D_SHORT = SEC_D + ("p20_flow_d18_short",)
D22_BETTER = D_SHORT + ("p20_flow_d22_better",)
D22_WORSE = D_SHORT + ("p20_flow_d22_worse",)
D22_SAME = D_SHORT + ("p20_flow_d22_same",)
D_HOURLY = SEC_D + ("p24_flow_d38_hourly",)
D41_NO = SEC_D + ("p24_flow_d41_no",)
D25_YES = SEC_D + ("p22_flow_d25_yes",)
D27_YES = SEC_D + ("p22_flow_d27_yes",)
D29_YES = SEC_D + ("p22_flow_d29_yes",)
D34_YES = SEC_D + ("p22_flow_d34_yes",)
SEC_E = ("p28_flow_section_e",)
E13_NONE = SEC_E + ("p28_flow_e13_none",)
SEC_F = ("p32_flow_section_f",)
F1_NO = SEC_F + ("p32_flow_f1_no",)
F2_THINKING = F1_NO + ("p32_flow_f2_thinking",)
F7_THINKING = SEC_F + ("p32_flow_f7_thinking",)
SEC_G = ("p34_flow_section_g",)
G_WORKED = SEC_G + ("p34_flow_g2_worked",)
G_UNEMPLOYED = G_WORKED + ("p34_flow_g7_unemployed",)
SEC_H = ("p38_flow_section_h",)
H_FARMER = SEC_H + ("p38_flow_h1_farmer",)
H_NOT_FARMER = SEC_H + ("p38_flow_h1_not_farmer",)
H_CORPORATION = SEC_H + ("p38_flow_h6_corporation",)
H_UNINCORPORATED = SEC_H + ("p38_flow_h6_unincorporated",)
H_BOTH = SEC_H + ("p38_flow_h6_both",)
H_DONT_KNOW = SEC_H + ("p38_flow_h6_dont_know",)
H9_YES = SEC_H + ("p42_flow_h9_yes",)
H_SOCIAL_SECURITY = SEC_H + ("p48_flow_h19_social_security",)
H_WIFE = SEC_H + ("p48_flow_h23_wife",)
H_NO_WIFE = SEC_H + ("p48_flow_h23_no_wife",)
H24_YES = H_WIFE + ("p48_flow_h24_yes",)
SEC_L = ("p62_flow_section_l",)
L_NEW_WIFE = SEC_L + ("p62_flow_l1_new_wife",)
L_SAME_WIFE = SEC_L + ("p62_flow_l1_same_wife",)
L_NO_WIFE = SEC_L + ("p62_flow_l1_no_wife",)
L_FEMALE_HEAD = SEC_L + ("p62_flow_l1_female_head",)
L4_NONE = L_NEW_WIFE + ("p62_flow_l4_none",)
L5_ALL = L_NEW_WIFE + ("p62_flow_l5_all",)
SEC_M = ("p64_flow_section_m",)
M_NEW_HEAD = SEC_M + ("p64_flow_m1_new_head",)
M_SAME_HEAD = SEC_M + ("p64_flow_m1_same_head",)
M4_NEVER = M_NEW_HEAD + ("p64_flow_m4_never_worked",)
M26_NONE = M_NEW_HEAD + ("p68_flow_m26_none",)
M27_ALL = M_NEW_HEAD + ("p68_flow_m27_all",)

_MAIN_JOB_PARENT = (
    "Parent job is the establishing main-job noun on this screen."
)
_PRESENT_JOB_PARENT = (
    "Parent job is the establishing present-job noun on this screen."
)
_CURRENT_JOB_PARENT = (
    "Parent job is the establishing current-job noun on this screen."
)
_PREVIOUS_JOB_PARENT = (
    "Parent job is the distinct previous-job noun on this screen."
)
_EXTRA_JOB_PARENT = (
    "Parent job is the establishing extra-jobs noun on this screen."
)
_SOUGHT_JOB_PARENT = (
    "Parent job is the establishing sought-job noun on this screen."
)
_LAST_JOB_PARENT = (
    "Parent job is the establishing last-job noun on this screen."
)
_FARM_PARENT = "Parent aggregate is the printed net-farm-income anchor."
_BUSINESS_PARENT = (
    "Parent aggregate is the printed unincorporated-business anchor."
)


PAGE_16 = (
    tail(
        16,
        1,
        "SECTION D:",
        F,
        "p16_flow_section_d",
        note="Printed section D header opening the head employment schedule.",
    ),
    word(16, 5, "HEAD'S", R, "p16_role_head_d1", routes=(SEC_D,)),
    word(
        16,
        5,
        "present job",
        J,
        "p16_job_present",
        routes=(SEC_D,),
        note="D1 establishes the head's present job for the occupation, industry, and employment-arrangement fields on this screen.",
    ),
    *paired(
        16,
        ("block", 5, 6),
        "p16_d1_assignment",
        routes=(SEC_D,),
        note="D1 prints the head labor-force assignment field.",
    ),
    word(
        16,
        8,
        "1 . \\'l'ORKING NOW , _9R",
        F,
        "p16_flow_d1_working",
        routes=(SEC_D,),
    ),
    word(
        16,
        8,
        "2. LOOKING FOR i",
        F,
        "p16_flow_d1_looking",
        routes=(SEC_D,),
    ),
    word(16, 8, "3 . RETIRED I", F, "p16_flow_d1_retired", routes=(SEC_D,)),
    word(16, 13, "DISABLED", F, "p16_flow_d1_disabled", routes=(SEC_D,)),
    word(
        16,
        15,
        "4 . HOD SEWIFEj",
        F,
        "p16_flow_d1_housewife",
        routes=(SEC_D,),
    ),
    word(
        16, 17, "[ 5 . STUDENT    I", F, "p16_flow_d1_student", routes=(SEC_D,)
    ),
    word(16, 18, ")6 . OTHER", F, "p16_flow_d1_other", routes=(SEC_D,)),
    *paired(
        16,
        ("line", 23),
        "p16_d2_occupation",
        parents=("p16_job_present",),
        routes=(SEC_D,),
        note="D2 prints the head main-occupation field.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    line(16, 32, P, "p16_d3_prompt", routes=(SEC_D,)),
    *paired(
        16,
        ("line", 39),
        "p16_d4_industry",
        parents=("p16_job_present",),
        routes=(SEC_D,),
        note="D4 prints the kind-of-business industry field.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        16,
        ("line", 44),
        "p16_d5_employee_self",
        parents=("p16_job_present",),
        routes=(SEC_D,),
        note="D5 prints the employee, mixed, or self-employed arrangement.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(
        16,
        46,
        "1. SOMEONE ELSE",
        F,
        "p16_flow_d5_someone_else",
        routes=(SEC_D,),
    ),
    word(
        16,
        46,
        "i2.J30THSO~IEONE ELSE AND SELF",
        F,
        "p16_flow_d5_both",
        routes=(SEC_D,),
    ),
    word(16, 46, "3 . SELF ONLY", F, "p16_flow_d5_self", routes=(SEC_D,)),
    word(
        16,
        50,
        "Federal, State or",
        C,
        "p16_d6_government_level",
        parents=("p16_job_present",),
        routes=(D_EMPLOYEE,),
        note="Exact federal/state fragment of the column-split D6 government field.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(
        16,
        49,
        "Do you wo rk for the",
        P,
        "p16_d6_prompt",
        routes=(D_EMPLOYEE,),
    ),
    word(
        16,
        52,
        "inc orp or ated?",
        C,
        "p16_d7_incorporation",
        parents=("p16_job_present",),
        routes=(D_BOTH,),
        note="Exact locatable D7 incorporation field fragment.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(16, 52, "inc orp or ated?", P, "p16_d7_prompt", routes=(D_BOTH,)),
    word(16, 62, "(GO TO DlO)", F, "p16_flow_d8_no", routes=(D_BOTH,)),
    word(
        16,
        69,
        "St:~lte or 1ucal Government?",
        C,
        "p16_d10_government_level",
        parents=("p16_job_present",),
        routes=(D_BOTH,),
        note="Exact D10 state/local-government field fragment.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(
        16,
        67,
        "DlO . Hh:=n Y''u work for others, do",
        P,
        "p16_d10_prompt",
        routes=(D_BOTH,),
    ),
    *paired(
        16,
        ("from", 53, "Dll .     Is your busine ss", 54, 0),
        "p16_d11_incorporation",
        parents=("p16_job_present",),
        routes=(D_SELF,),
        note="D11 prints the incorporation field for the self-only branch.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
)


PAGE_20 = (
    *paired(
        20,
        ("line", 21),
        "p20_d18_job_tenure",
        parents=("p20_job_current",),
        routes=(SEC_D,),
        note="D18 prints tenure with the present employer, worded as tenure in 'this job' on the instrument.",
        parent_note=_CURRENT_JOB_PARENT,
    ),
    word(
        20,
        21,
        "this job",
        J,
        "p20_job_current",
        routes=(SEC_D,),
        note="D18 establishes the head's current job.",
    ),
    line(20, 23, F, "p20_flow_d18_long", routes=(SEC_D,)),
    line(20, 24, F, "p20_flow_d18_short", routes=(SEC_D,)),
    *paired(
        20,
        ("block", 29, 30),
        "p20_d20_previous_job_outcome",
        parents=("p20_job_previous",),
        routes=(D_SHORT,),
        note="D20 prints the disposition of the previous job.",
        parent_note=_PREVIOUS_JOB_PARENT,
    ),
    word(
        20,
        29,
        "the job you had before",
        J,
        "p20_job_previous",
        routes=(D_SHORT,),
        note="D20 establishes the distinct previous job.",
    ),
    *paired(
        20,
        ("line", 32),
        "p20_d21_pay_comparison",
        parents=("p20_job_current", "p20_job_previous"),
        routes=(D_SHORT,),
        note="D21 prints a current-versus-previous-job pay comparison.",
        parent_note="The printed comparison names the current and previous jobs.",
    ),
    *paired(
        20,
        ("block", 35, 36),
        "p20_d22_job_comparison",
        parents=("p20_job_current", "p20_job_previous"),
        routes=(D_SHORT,),
        note="D22 prints a current-versus-previous-job assignment comparison.",
        parent_note="The printed comparison names the current and previous jobs.",
    ),
    word(20, 38, "1 . BETTER", F, "p20_flow_d22_better", routes=(D_SHORT,)),
    word(20, 38, "5 . HORSE", F, "p20_flow_d22_worse", routes=(D_SHORT,)),
    word(20, 38, "3. SA£-fE", F, "p20_flow_d22_same", routes=(D_SHORT,)),
    word(
        20,
        38,
        "(TURN TO PAGE 9, D24)",
        F,
        "p20_flow_d22_same_exit",
        routes=(D22_SAME,),
    ),
    line(20, 41, P, "p20_d23_prompt", routes=(D22_BETTER, D22_WORSE)),
    word(
        20,
        46,
        "(TURN TO PAGE 9, D24)",
        F,
        "p20_flow_d23_exit",
        routes=(D22_BETTER, D22_WORSE),
    ),
)


PAGE_22 = (
    *paired(
        22,
        ("line", 1),
        "p22_d24_paid_vacation",
        routes=(SEC_D,),
        note="D24 prints paid-vacation weeks as work exposure.",
    ),
    *paired(
        22,
        ("line", 3),
        "p22_d25_took_vacation",
        routes=(SEC_D,),
        note="D25 prints 1974 vacation exposure.",
    ),
    word(22, 5, "IL YES", F, "p22_flow_d25_yes", routes=(SEC_D,)),
    word(22, 5, "(GO TO D27)", F, "p22_flow_d25_no", routes=(SEC_D,)),
    *paired(
        22,
        ("line", 8),
        "p22_d26_vacation_amount",
        routes=(D25_YES,),
        note="D26 prints the amount of vacation taken.",
    ),
    *paired(
        22,
        ("block", 11, 12),
        "p22_d27_sick_absence",
        routes=(SEC_D,),
        note="D27 prints 1974 sickness absence.",
    ),
    word(22, 14, "I 1. YES", F, "p22_flow_d27_yes", routes=(SEC_D,)),
    word(22, 14, "(GO TO D29)", F, "p22_flow_d27_no", routes=(SEC_D,)),
    *paired(
        22,
        ("line", 17),
        "p22_d28_sick_absence_amount",
        routes=(D27_YES,),
        note="D28 prints sickness absence duration.",
    ),
    *paired(
        22,
        ("line", 20),
        "p22_d29_unemployment_absence",
        routes=(SEC_D,),
        note="D29 prints unemployment or strike absence.",
    ),
    word(22, 22, "I 1. YES", F, "p22_flow_d29_yes", routes=(SEC_D,)),
    word(22, 22, "(GO TO D32)", F, "p22_flow_d29_no", routes=(SEC_D,)),
    *paired(
        22,
        ("line", 25),
        "p22_d30_unemployment_amount",
        routes=(D29_YES,),
        note="D30 prints unemployment absence duration.",
    ),
    *paired(
        22,
        ("block", 28, 29),
        "p22_d31_unemployment_spells",
        routes=(D29_YES,),
        note="D31 prints the number of unemployment periods.",
    ),
    *paired(
        22,
        ("line", 34),
        "p22_d32_weeks_worked",
        parents=("p22_job_main",),
        routes=(SEC_D,),
        note="D32 prints weeks worked on the main job.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        22,
        34,
        "main job",
        J,
        "p22_job_main",
        routes=(SEC_D,),
        note="D32 establishes the head's main job.",
    ),
    *paired(
        22,
        ("block", 37, 38),
        "p22_d33_hours_per_week",
        parents=("p22_job_main",),
        routes=(SEC_D,),
        note="D33 prints average weekly hours on the main job.",
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        22,
        ("line", 40),
        "p22_d34_overtime_excluded",
        routes=(SEC_D,),
        note="D34 prints whether overtime is excluded from average hours.",
    ),
    word(22, 42, "( ] YES", F, "p22_flow_d34_yes", routes=(SEC_D,)),
    word(
        22,
        42,
        "(TURN TO PAGE 10 , D36)",
        F,
        "p22_flow_d34_no",
        routes=(SEC_D,),
    ),
    *paired(
        22,
        ("line", 44),
        "p22_d35_overtime_hours",
        routes=(D34_YES,),
        note="D35 prints annual overtime hours.",
    ),
)


PAGE_24 = (
    *paired(
        24,
        ("block", 2, 3),
        "p24_d36_overtime_pay_eligibility",
        routes=(SEC_D,),
        note="D36 prints eligibility for extra-hours pay.",
    ),
    *paired(
        24,
        ("tail", 6, "'D37 .", 0),
        "p24_d37_overtime_hourly_rate",
        anchor_kind=M,
        routes=(SEC_D,),
        note="D37 prints the overtime hourly-rate remuneration component.",
    ),
    *paired(
        24,
        ("needle", 8, "rl38.    Do you have an hourly wage", 0),
        "p24_d38_hourly_basis",
        routes=(SEC_D,),
        note="D38 prints whether regular work has an hourly wage rate.",
    ),
    word(24, 11, "rl. YEs!", F, "p24_flow_d38_hourly", routes=(SEC_D,)),
    word(
        24,
        11,
        "I 5. NO J(GO TO D40)",
        F,
        "p24_flow_d38_not_hourly",
        routes=(SEC_D,),
    ),
    *paired(
        24,
        ("line", 15),
        "p24_d39_regular_hourly_rate",
        anchor_kind=M,
        routes=(D_HOURLY,),
        note="D39 prints the regular hourly-wage remuneration component.",
    ),
    *paired(
        24,
        ("line", 17),
        "p24_d40_retirement_plan",
        routes=(SEC_D,),
        note="D40 prints employer-retirement-plan coverage.",
    ),
    *paired(
        24,
        ("block", 19, 23),
        "p24_d41_extra_job_assignment",
        parents=("p24_job_extra_jobs",),
        routes=(SEC_D,),
        note="D41 prints whether the head had extra jobs in addition to the main job.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    word(
        24,
        19,
        "extra jobs",
        J,
        "p24_job_extra_jobs",
        routes=(SEC_D,),
        note="D41 establishes the head's extra-jobs source node.",
    ),
    *paired(
        24,
        ("line", 31),
        "p24_d42_extra_job_occupation",
        parents=("p24_job_extra_jobs",),
        routes=(SEC_D,),
        note="D42 prints the extra-job occupation field.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    word(24, 29, "i5.NOj", F, "p24_flow_d41_no", routes=(SEC_D,)),
    word(
        24,
        32,
        "(TURN TO PAGE 11, D47)",
        F,
        "p24_flow_d41_no_exit",
        routes=(D41_NO,),
    ),
    line(24, 37, P, "p24_d43_prompt", routes=(SEC_D,)),
    *paired(
        24,
        ("line", 39),
        "p24_d44_extra_job_hourly_pay",
        anchor_kind=M,
        parents=("p24_job_extra_jobs",),
        routes=(SEC_D,),
        note="D44 prints the per-hour extra-job remuneration component.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        24,
        ("line", 41),
        "p24_d45_extra_job_weeks",
        parents=("p24_job_extra_jobs",),
        routes=(SEC_D,),
        note="D45 prints weeks worked on the extra job.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        24,
        ("block", 43, 44),
        "p24_d46_extra_job_hours",
        parents=("p24_job_extra_jobs",),
        routes=(SEC_D,),
        note="D46 prints average weekly hours on the extra job.",
        parent_note=_EXTRA_JOB_PARENT,
    ),
)


PAGE_28 = (
    tail(
        28,
        1,
        "SECTION E :",
        F,
        "p28_flow_section_e",
        note="Printed section E header opening the unemployed-head schedule.",
    ),
    *paired(
        28,
        ("line", 4),
        "p28_e1_sought_occupation",
        parents=("p28_job_sought",),
        routes=(SEC_E,),
        note="E1 prints the sought-job occupation field.",
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    word(
        28,
        4,
        "job",
        J,
        "p28_job_sought",
        routes=(SEC_E,),
        note="E1 establishes the job being sought.",
    ),
    *paired(
        28,
        ("line", 7),
        "p28_e2_expected_earnings",
        anchor_kind=M,
        parents=("p28_job_sought",),
        routes=(SEC_E,),
        note="E2 prints expected earnings and reporting unit for the sought job.",
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    word(28, 15, "(GO TO E6)", F, "p28_flow_e4_nothing", routes=(SEC_E,)),
    *paired(
        28,
        ("line", 22),
        "p28_e6_last_job_occupation",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E6 prints the last-job occupation field.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        28,
        22,
        "last job",
        J,
        "p28_job_last",
        routes=(SEC_E,),
        note="E6 establishes the head's last job.",
    ),
    *paired(
        28,
        ("line", 28),
        "p28_e7_last_job_industry",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E7 prints the last-job industry field.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 36),
        "p28_e9_last_job_outcome",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E9 prints the disposition of the last job.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 41),
        "p28_e10_weeks_worked",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E10 prints weeks worked in 1974 on the last-job schedule.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(
        28,
        41,
        "00 . NONE     (GO TO El2)",
        F,
        "p28_flow_e10_none",
        routes=(SEC_E,),
    ),
    *paired(
        28,
        ("line", 46),
        "p28_e12_sick_weeks",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E12 prints 1974 sickness absence on the last-job schedule.",
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        28,
        ("line", 48),
        "p28_e13_unemployment_weeks",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E13 prints 1974 unemployment exposure on the last-job schedule.",
        parent_note=_LAST_JOB_PARENT,
    ),
    word(28, 48, "I 00. NONE l", F, "p28_flow_e13_none", routes=(SEC_E,)),
    from_word(
        28,
        49,
        "(TURN TO",
        50,
        F,
        "p28_flow_e13_none_exit",
        routes=(E13_NONE,),
    ),
    *paired(
        28,
        ("block", 51, 52),
        "p28_e14_unemployment_spells",
        parents=("p28_job_last",),
        routes=(SEC_E,),
        note="E14 prints the number of unemployment periods.",
        parent_note=_LAST_JOB_PARENT,
    ),
)


PAGE_32 = (
    tail(
        32,
        2,
        "SECTION F :",
        F,
        "p32_flow_section_f",
        note="Printed section F header opening the inactive-head schedule.",
    ),
    word(32, 6, "HEAD", R, "p32_role_head_f1", routes=(SEC_F,)),
    *paired(
        32,
        ("line", 6),
        "p32_f1_actual_work",
        routes=(SEC_F,),
        note="F1 prints whether the head did work for money in 1974.",
    ),
    word(32, 8, "I 5. NO I", F, "p32_flow_f1_no", routes=(SEC_F,)),
    word(32, 12, "1. YES I", F, "p32_flow_f2_thinking", routes=(F1_NO,)),
    word(32, 12, "5. NO I", F, "p32_flow_f2_not_thinking", routes=(F1_NO,)),
    *paired(
        32,
        ("line", 17),
        "p32_f3_occupation",
        routes=(SEC_F,),
        note="F3 prints the occupation of actual 1974 work.",
    ),
    *paired(
        32,
        ("line", 21),
        "p32_f4_industry",
        routes=(SEC_F,),
        note="F4 prints the industry of actual 1974 work.",
    ),
    *paired(
        32,
        ("line", 25),
        "p32_f5_weeks_worked",
        routes=(SEC_F,),
        note="F5 prints weeks worked in 1974.",
    ),
    *paired(
        32,
        ("line", 27),
        "p32_f6_hours_per_week",
        routes=(SEC_F,),
        note="F6 prints average weekly hours worked.",
    ),
    word(
        32,
        31,
        "1. YES       (GO TO F8)",
        F,
        "p32_flow_f7_thinking",
        routes=(SEC_F,),
    ),
    word(
        32,
        31,
        "Is . NQl   (TURN TO PAGE 15, Gl)",
        F,
        "p32_flow_f7_not_thinking",
        routes=(SEC_F,),
    ),
    *paired(
        32,
        ("line", 36),
        "p32_f8_sought_occupation",
        parents=("p32_job_sought",),
        routes=(F2_THINKING, F7_THINKING),
        note="F8 prints the occupation of the job in mind.",
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    word(
        32,
        36,
        "job",
        J,
        "p32_job_sought",
        routes=(F2_THINKING, F7_THINKING),
        note="F8 establishes the job the head has in mind.",
    ),
    *paired(
        32,
        ("line", 39),
        "p32_f9_expected_earnings",
        anchor_kind=M,
        parents=("p32_job_sought",),
        routes=(F2_THINKING, F7_THINKING),
        note="F9 prints expected earnings and reporting unit for the job in mind.",
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    word(32, 45, "(GO TO Fl3)", F, "p32_flow_f11_nothing", routes=(SEC_F,)),
    word(
        32, 54, "(TURN TO PAGE 15, Gl)", F, "p32_flow_f13_no", routes=(SEC_F,)
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
    word(34, 10, "\\HFE'S", R, "p34_role_wife_header", routes=(SEC_G,)),
    line(34, 4, P, "p34_g1_prompt", routes=(SEC_G,)),
    word(
        34, 8, "(TURN TO PAGE 16, Gl4)", F, "p34_flow_g1_exit", routes=(SEC_G,)
    ),
    *paired(
        34,
        ("line", 12),
        "p34_g2_actual_work",
        routes=(SEC_G,),
        note="G2 prints whether the wife did work for money in 1974.",
    ),
    word(34, 12, "wife", R, "p34_role_wife_g2", routes=(SEC_G,)),
    word(34, 14, "i 1. YES I", F, "p34_flow_g2_worked", routes=(SEC_G,)),
    word(
        34,
        14,
        "I 5 . NO I    (TURN TO PAGE 16, Gl4)",
        F,
        "p34_flow_g2_no",
        routes=(SEC_G,),
    ),
    *paired(
        34,
        ("line", 17),
        "p34_g3_occupation",
        routes=(G_WORKED,),
        note="G3 prints the wife's occupation field.",
    ),
    *paired(
        34,
        ("line", 20),
        "p34_g4_industry",
        routes=(G_WORKED,),
        note="G4 prints the wife's industry field.",
    ),
    *paired(
        34,
        ("line", 23),
        "p34_g5_weeks_worked",
        routes=(G_WORKED,),
        note="G5 prints the wife's 1974 weeks worked.",
    ),
    *paired(
        34,
        ("line", 25),
        "p34_g6_hours_per_week",
        routes=(G_WORKED,),
        note="G6 prints the wife's average weekly hours.",
    ),
    *paired(
        34,
        ("line", 27),
        "p34_g7_unemployment",
        routes=(G_WORKED,),
        note="G7 prints the wife's unemployment or strike absence.",
    ),
    word(34, 29, "il. YES", F, "p34_flow_g7_unemployed", routes=(G_WORKED,)),
    word(
        34,
        29,
        "I 5 . NO I       (GO TO G9)",
        F,
        "p34_flow_g7_no",
        routes=(G_WORKED,),
    ),
    *paired(
        34,
        ("line", 31),
        "p34_g8_unemployment_amount",
        routes=(G_UNEMPLOYED,),
        note="G8 prints the wife's unemployment absence duration.",
    ),
    word(
        34,
        44,
        "(TURN TO PAGE 16, Gl4)",
        F,
        "p34_flow_g11_none",
        routes=(G_WORKED,),
    ),
)


PAGE_38 = (
    tail(
        38,
        1,
        "SECTION H:",
        F,
        "p38_flow_section_h",
        note="Printed section H header opening the family income schedule.",
    ),
    word(
        38,
        13,
        "1. FARMER, OR RANCHER",
        F,
        "p38_flow_h1_farmer",
        routes=(SEC_H,),
    ),
    word(
        38,
        13,
        "5. NOT A FARMER OR RANCHER",
        F,
        "p38_flow_h1_not_farmer",
        routes=(SEC_H,),
    ),
    word(
        38,
        13,
        "(GO TO I-IS)",
        F,
        "p38_flow_h1_not_farmer_exit",
        routes=(H_NOT_FARMER,),
    ),
    *paired(
        38,
        ("block", 15, 16),
        "p38_h2_farm_receipts",
        anchor_kind=M,
        parents=("p38_farm_aggregate",),
        routes=(H_FARMER,),
        note="H2 prints total farm receipts.",
        parent_note=_FARM_PARENT,
    ),
    *paired(
        38,
        ("block", 18, 19),
        "p38_h3_farm_expenses",
        anchor_kind=M,
        parents=("p38_farm_aggregate",),
        routes=(H_FARMER,),
        note="H3 prints farm operating expenses as a signed component.",
        parent_note=_FARM_PARENT,
    ),
    word(
        38,
        21,
        "net income from farming",
        FA,
        "p38_farm_aggregate",
        routes=(H_FARMER,),
        note="H4 prints the net-farm-income aggregate.",
    ),
    line(38, 21, P, "p38_h4_prompt", routes=(H_FARMER,)),
    block(38, 25, 26, P, "p38_h5_prompt", routes=(SEC_H,)),
    word(38, 28, "(GO TO HS)", F, "p38_flow_h5_no", routes=(SEC_H,)),
    *paired(
        38,
        ("block", 31, 32),
        "p38_h6_incorporation",
        parents=("p38_business_aggregate",),
        routes=(SEC_H,),
        note="H6 prints corporation versus unincorporated-business status.",
        parent_note=_BUSINESS_PARENT,
    ),
    word(
        38,
        31,
        "unincorporated business",
        BA,
        "p38_business_aggregate",
        routes=(SEC_H,),
        note="H6 prints the unincorporated-business aggregate label.",
    ),
    word(
        38,
        34,
        "1.   CORPORATION",
        F,
        "p38_flow_h6_corporation",
        routes=(SEC_H,),
    ),
    word(
        38,
        34,
        "(GO TO I-18)",
        F,
        "p38_flow_h6_corporation_exit",
        routes=(H_CORPORATION,),
    ),
    word(
        38,
        42,
        "-rr-uNINCORPORATED j",
        F,
        "p38_flow_h6_unincorporated",
        routes=(SEC_H,),
    ),
    word(38, 43, "3 . BOTH J", F, "p38_flow_h6_both", routes=(SEC_H,)),
    word(
        38,
        44,
        "8.   DON'T KNOW /",
        F,
        "p38_flow_h6_dont_know",
        routes=(SEC_H,),
    ),
    *paired(
        38,
        ("block", 45, 47),
        "p38_h7_business_share",
        anchor_kind=M,
        parents=("p38_business_aggregate",),
        routes=(H_UNINCORPORATED, H_BOTH, H_DONT_KNOW),
        note="H7 prints the family share of unincorporated-business income.",
        parent_note=_BUSINESS_PARENT,
    ),
    *paired(
        38,
        ("block", 53, 54),
        "p38_h8_wages",
        anchor_kind=M,
        routes=(SEC_H,),
        note="H8 prints the head's 1974 wages and salaries.",
    ),
    word(38, 53, "HEAD", R, "p38_role_head_h8", routes=(SEC_H,)),
)


PAGE_42 = (
    *paired(
        42,
        ("block", 2, 3),
        "p42_h9_bonus_overtime_commission",
        anchor_kind=M,
        routes=(SEC_H,),
        note="H9 prints bonuses, overtime, and commissions as one component.",
    ),
    word(42, 5, "[ ] YES", F, "p42_flow_h9_yes", routes=(SEC_H,)),
    word(42, 5, "(GO TO Hll)", F, "p42_flow_h9_no", routes=(SEC_H,)),
    line(42, 8, P, "p42_h10_prompt", routes=(H9_YES,)),
    line(42, 9, P, "p42_h11_prompt", routes=(SEC_H,)),
    word(42, 9, "HEAD", R, "p42_role_head_h11", routes=(SEC_H,)),
    word(
        42,
        12,
        "a) professional practice or trade?",
        M,
        "p42_h11a_professional_trade",
        routes=(SEC_H,),
        note="H11a prints the professional-practice-or-trade component.",
    ),
    word(
        42,
        14,
        "b) farming or market gardening,",
        M,
        "p42_h11b_farming_gardening",
        routes=(SEC_H,),
        note="H11b prints farming or market gardening as a component.",
    ),
    word(
        42,
        16,
        "roomers or boarders?",
        M,
        "p42_h11b_roomers_boarders",
        routes=(SEC_H,),
        note="H11b's continuation prints roomers or boarders as a distinct component label.",
    ),
    word(
        42, 43, "(TURN TO PAGE 19, Hl4)", F, "p42_flow_h12_no", routes=(SEC_H,)
    ),
)


PAGE_48 = (
    word(48, 2, "(GO TO Hl9)", F, "p48_flow_h14_no", routes=(SEC_H,)),
    word(48, 6, "(Go TO Hl7)", F, "p48_flow_h15_no", routes=(SEC_H,)),
    word(48, 12, "(GO TO Hl9)", F, "p48_flow_h17_no", routes=(SEC_H,)),
    word(48, 14, "(GO TO Hl9)", F, "p48_flow_h18_exit", routes=(SEC_H,)),
    *paired(
        48,
        ("block", 17, 18),
        "p48_h19_social_security_checkpoint",
        routes=(SEC_H,),
        note="H19 prints the Social Security income checkpoint as public-retirement context.",
    ),
    word(
        48,
        18,
        "1 . INCONE FROM SOCIAL SECURITY I",
        F,
        "p48_flow_h19_social_security",
        routes=(SEC_H,),
    ),
    word(
        48,
        18,
        "( 5. NO SUCH INCOHE       (GO TO H23)",
        F,
        "p48_flow_h19_no_social_security",
        routes=(SEC_H,),
    ),
    word(
        48,
        25,
        "j s . No I(Go To H22)",
        F,
        "p48_flow_h20_no_ssi",
        routes=(H_SOCIAL_SECURITY,),
    ),
    word(
        48,
        31,
        "(GO TO H23)",
        F,
        "p48_flow_h22_exit",
        routes=(H_SOCIAL_SECURITY,),
    ),
    line(48, 34, P, "p48_h23_prompt", routes=(SEC_H,)),
    word(48, 34, "HEAD", R, "p48_role_head_h23", routes=(SEC_H,)),
    word(48, 34, "WIFE", R, "p48_role_wife_h23", routes=(SEC_H,)),
    word(
        48, 35, "[ ] YES, WIFE IN FU", F, "p48_flow_h23_wife", routes=(SEC_H,)
    ),
    word(
        48,
        35,
        "[ ] NO WIFE IN FU OR FU HAS FE~~LE HEAD",
        F,
        "p48_flow_h23_no_wife",
        routes=(SEC_H,),
    ),
    from_word(
        48,
        35,
        "(TURN TO",
        36,
        F,
        "p48_flow_h23_no_wife_exit",
        routes=(H_NO_WIFE,),
    ),
    *paired(
        48,
        ("line", 38),
        "p48_h24_wife_income_presence",
        routes=(H_WIFE,),
        note="H24 prints whether the wife had income; it is not a printed total-income amount.",
    ),
    word(48, 38, "wife", R, "p48_role_wife_h24", routes=(H_WIFE,)),
    word(48, 39, "[ ] YES", F, "p48_flow_h24_yes", routes=(H_WIFE,)),
    word(
        48,
        39,
        "[ ] NO   (TURN TO PAGE 20 , H27)",
        F,
        "p48_flow_h24_no",
        routes=(H_WIFE,),
    ),
    *paired(
        48,
        ("line", 41),
        "p48_h25_wife_income_source",
        routes=(H24_YES,),
        note="H25 prints the source classification for wife income.",
    ),
    *paired(
        48,
        ("line", 46),
        "p48_h26_wife_income_amount",
        anchor_kind=M,
        routes=(H24_YES,),
        note="H26 prints wife income before deductions as remuneration amount fields.",
    ),
)


PAGE_62 = (
    tail(
        62,
        6,
        "SECTION L:",
        F,
        "p62_flow_section_l",
        note="Printed section L header opening the new-wife work-history schedule.",
    ),
    word(62, 6, "WIFE", R, "p62_role_wife_header", routes=(SEC_L,)),
    line(62, 9, P, "p62_l1_prompt", routes=(SEC_L,)),
    word(
        62,
        12,
        "1. FU HAS NEW WIFE",
        F,
        "p62_flow_l1_new_wife",
        routes=(SEC_L,),
    ),
    word(
        62,
        12,
        "5 . FU HAS SAME WIFE AS IN 1974",
        F,
        "p62_flow_l1_same_wife",
        routes=(SEC_L,),
    ),
    word(
        62, 13, "OR FU HAS NO WIFE", F, "p62_flow_l1_no_wife", routes=(SEC_L,)
    ),
    word(
        62,
        14,
        "OR FU HAS FEHALE HEAD",
        F,
        "p62_flow_l1_female_head",
        routes=(SEC_L,),
    ),
    word(
        62,
        18,
        "(TURN TO PAGE E_~) Hl)",
        F,
        "p62_flow_l1_same_wife_exit",
        routes=(L_SAME_WIFE, L_NO_WIFE, L_FEMALE_HEAD),
    ),
    *paired(
        62,
        ("line", 32),
        "p62_l4_years_worked",
        routes=(L_NEW_WIFE,),
        note="L4 prints the new wife's lifetime years worked since age 18.",
    ),
    word(62, 36, "i 00 . NONE I", F, "p62_flow_l4_none", routes=(L_NEW_WIFE,)),
    from_word(
        62,
        36,
        "(TURN TO",
        37,
        F,
        "p62_flow_l4_none_exit",
        routes=(L4_NONE,),
    ),
    *paired(
        62,
        ("line", 38),
        "p62_l5_years_full_time",
        routes=(L_NEW_WIFE,),
        note="L5 prints the new wife's lifetime full-time years.",
    ),
    word(62, 43, "ALL I", F, "p62_flow_l5_all", routes=(L_NEW_WIFE,)),
    from_word(
        62,
        43,
        "(TURN TO",
        45,
        F,
        "p62_flow_l5_all_exit",
        routes=(L5_ALL,),
    ),
    *paired(
        62,
        ("block", 46, 47),
        "p62_l6_part_time_share",
        routes=(L_NEW_WIFE,),
        note="L6 prints the share of non-full-time years worked.",
    ),
)


PAGE_64 = (
    word(
        64,
        1,
        "SECTION M:   NEW HEAD",
        F,
        "p64_flow_section_m",
        note="Printed section M header opening the new-head schedule.",
    ),
    line(64, 2, P, "p64_m1_prompt", routes=(SEC_M,)),
    word(
        64,
        4,
        "1. FU HAS A NEW HEAD THIS YEAR",
        F,
        "p64_flow_m1_new_head",
        routes=(SEC_M,),
    ),
    word(
        64,
        4,
        "5 . THIS FU HAS THE SA}fE HEAD AS IN 1974",
        F,
        "p64_flow_m1_same_head",
        routes=(SEC_M,),
    ),
    word(
        64,
        5,
        "(TURN TO PAGE 3 OF COVER SHEET)",
        F,
        "p64_flow_m1_same_head_exit",
        routes=(M_SAME_HEAD,),
    ),
    *paired(
        64,
        ("line", 24),
        "p64_m4_first_job_occupation",
        parents=("p64_job_first_full_time",),
        routes=(M_NEW_HEAD,),
        note="M4 prints the first-full-time-regular-job occupation field.",
        parent_note="Parent job is the printed first-job noun on this screen.",
    ),
    word(64, 24, "HEAD ' S", R, "p64_role_head_m4", routes=(M_NEW_HEAD,)),
    word(
        64,
        24,
        "first full time regular job",
        J,
        "p64_job_first_full_time",
        routes=(M_NEW_HEAD,),
        note="M4 establishes the head's first full-time regular job.",
    ),
    word(
        64,
        25,
        "0. NEVER WORKED",
        F,
        "p64_flow_m4_never_worked",
        routes=(M_NEW_HEAD,),
    ),
    word(
        64,
        26,
        "(GO TO M6).",
        F,
        "p64_flow_m4_never_worked_exit",
        routes=(M4_NEVER,),
    ),
    *paired(
        64,
        ("block", 28, 29),
        "p64_m5_occupation_count",
        routes=(M_NEW_HEAD,),
        note="M5 prints the number-of-occupations work-history field.",
    ),
    word(64, 39, "(GO TO M9)", F, "p64_flow_m6_no", routes=(M_NEW_HEAD,)),
    word(
        64,
        47,
        "(TURN TO PAGE 28 , Hll)",
        F,
        "p64_flow_m9_no",
        routes=(M_NEW_HEAD,),
    ),
)


PAGE_68 = (
    *paired(
        68,
        ("line", 1),
        "p68_m26_years_worked",
        routes=(M_NEW_HEAD,),
        note="M26, whose identifier extracts as H26, prints lifetime years worked since age 18.",
    ),
    word(68, 1, "HEAD", R, "p68_role_head_m26", routes=(M_NEW_HEAD,)),
    word(68, 3, "00. NONE I", F, "p68_flow_m26_none", routes=(M_NEW_HEAD,)),
    word(
        68, 3, "(GO TO M29)", F, "p68_flow_m26_none_exit", routes=(M26_NONE,)
    ),
    *paired(
        68,
        ("line", 4),
        "p68_m27_years_full_time",
        routes=(M_NEW_HEAD,),
        note="M27 prints the new head's lifetime full-time years.",
    ),
    word(68, 4, "HEAD", R, "p68_role_head_m27", routes=(M_NEW_HEAD,)),
    word(68, 6, "AL_L", F, "p68_flow_m27_all", routes=(M_NEW_HEAD,)),
    word(68, 6, "(GO TO M29)", F, "p68_flow_m27_all_exit", routes=(M27_ALL,)),
    *paired(
        68,
        ("block", 8, 9),
        "p68_m28_part_time_share",
        routes=(M_NEW_HEAD,),
        note="M28 prints the share of non-full-time years worked.",
    ),
    word(68, 8, "HEAD", R, "p68_role_head_m28", routes=(M_NEW_HEAD,)),
    word(
        68,
        20,
        "5 . NO   (TU&~   TO PAGE 3 OF COVER SHEET)",
        F,
        "p68_flow_m29_no",
        routes=(M_NEW_HEAD,),
    ),
    word(
        68,
        36,
        "(TURN TO PAGE 3 OF COVER SHEET)",
        F,
        "p68_flow_m32_exit",
        routes=(M_NEW_HEAD,),
    ),
)


CROSS_REFERENCES = (
    _xref(
        25,
        ("line", 34),
        "p25_xref_d42_d43_to_d2_d3",
        ("p24_d42_extra_job_occupation",),
        ("p16_d2_occupation",),
        "D42-D43 explicitly reuse the D2-D3 occupation instructions.",
    ),
    _unresolved_repeat(
        25,
        ("line", 39),
        "p25_repeat_extra_jobs",
        "The interviewer must obtain hourly pay for each separately reported extra job; equivalence is not inferred.",
    ),
    _xref(
        29,
        ("line", 11),
        "p29_xref_e1_to_d2_d3",
        ("p28_e1_sought_occupation",),
        ("p16_d2_occupation",),
        "E1 explicitly reuses the D2-D3 occupation objectives.",
    ),
    _xref(
        29,
        ("line", 23),
        "p29_xref_e6_to_d2_d3",
        ("p28_e6_last_job_occupation",),
        ("p16_d2_occupation",),
        "E6 explicitly reuses the D2-D3 occupation objectives.",
    ),
    _xref(
        29,
        ("line", 25),
        "p29_xref_e7_to_d4",
        ("p28_e7_last_job_industry",),
        ("p16_d4_industry",),
        "E7 explicitly reuses the D4 industry objectives.",
    ),
    _xref(
        29,
        ("line", 31),
        "p29_xref_e9_to_d20",
        ("p28_e9_last_job_outcome",),
        ("p20_d20_previous_job_outcome",),
        "E9 explicitly reuses the D20 prior-job-disposition objectives.",
    ),
    _xref(
        33,
        ("line", 17),
        "p33_xref_f3_to_d2_d3",
        ("p32_f3_occupation",),
        ("p16_d2_occupation",),
        "F3 explicitly reuses the D2-D3 occupation objectives.",
    ),
    _xref(
        33,
        ("line", 19),
        "p33_xref_f4_to_d4",
        ("p32_f4_industry",),
        ("p16_d4_industry",),
        "F4 explicitly reuses the D4 industry objectives.",
    ),
    _xref(
        33,
        ("block", 30, 31),
        "p33_xref_f8_to_d2_d3",
        ("p32_f8_sought_occupation",),
        ("p16_d2_occupation",),
        "F8 explicitly points to the D2-D3 occupation instructions for the job the head has in mind.",
    ),
    _xref(
        35,
        ("line", 14),
        "p35_xref_g2_g4_to_d2_d4",
        ("p34_g3_occupation", "p34_g4_industry"),
        ("p16_d2_occupation", "p16_d4_industry"),
        "The G2-G4 objective binds the wife occupation and industry fields to the D2 and D4 head fields.",
    ),
    _xref(
        35,
        ("block", 17, 18),
        "p35_xref_g5_g6_to_e10_e11",
        ("p34_g5_weeks_worked", "p34_g6_hours_per_week"),
        (),
        "G5-G6 reuse E10-E11; E11's prompt is absent from the exact Poppler bytes, so the partial endpoint stays unresolved.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        35,
        ("line", 21),
        "p35_xref_g7_g8_to_d29_d30",
        ("p34_g7_unemployment", "p34_g8_unemployment_amount"),
        ("p22_d29_unemployment_absence", "p22_d30_unemployment_amount"),
        "G7-G8 explicitly reuse the D29-D30 unemployment objectives.",
    ),
    _xref(
        39,
        ("line", 11),
        "p39_xref_nonfarmer_farm_to_h11b",
        ("p42_h11b_farming_gardening",),
        ("p38_farm_aggregate",),
        "H1 routes nonfarmer farm income to H11b rather than H2-H4.",
    ),
    _unresolved_repeat(
        40,
        ("block", 4, 9),
        "p40_repeat_h7_separate_business_amounts",
        "H7 requires separately labeled salary, profit, and wife-wage amounts inside the family business report; no equivalence is inferred.",
    ),
    _xref(
        40,
        ("block", 22, 25),
        "p40_xref_h8_business_wages_to_h7",
        ("p38_h8_wages",),
        ("p38_h7_business_share",),
        "The H8 instruction routes an unincorporated owner's own pay to H7 and wages from another job to H8.",
    ),
    _xref(
        40,
        ("block", 26, 27),
        "p40_xref_h8_h7_no_double_count",
        ("p38_h8_wages",),
        ("p38_h7_business_share",),
        "The instruction explicitly prevents duplicating one amount in H7 and H8.",
    ),
    _unresolved_repeat(
        43,
        ("block", 4, 11),
        "p43_repeat_h9_h10_prior_inclusion",
        "H9-H10 prevent re-entering bonus, overtime, or commission income already included in a prior item whose identifier is OCR-destroyed.",
    ),
    _xref(
        43,
        ("block", 44, 51),
        "p43_xref_wife_public_payments_to_h25_h26",
        ("p48_h25_wife_income_source", "p48_h26_wife_income_amount"),
        (),
        "The objective explicitly routes wife Social Security and Supplemental Security checks from excluded H11f/H11k sources to H25-H26; the out-of-domain endpoints remain unresolved.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        44,
        ("block", 13, 17),
        "p44_xref_h11b_to_h2_h4",
        ("p42_h11b_farming_gardening",),
        ("p38_h2_farm_receipts", "p38_h3_farm_expenses", "p38_farm_aggregate"),
        "H11b explicitly routes a primary farmer's income to H2-H4 and forbids duplication.",
    ),
    _xref(
        49,
        ("block", 31, 36),
        "p49_xref_h26_to_h7",
        ("p48_h26_wife_income_amount",),
        ("p38_h7_business_share",),
        "The wife-income instruction says family-business work income may already be included in H7.",
    ),
    _xref(
        48,
        ("line", 17),
        "p48_xref_h19_to_h11f",
        ("p48_h19_social_security_checkpoint",),
        (),
        "H19 explicitly refers to H11f, whose Social Security row is outside the retained work-income component set, so the endpoint remains unresolved.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        65,
        ("line", 19),
        "p65_xref_m4_to_d2_d3",
        ("p64_m4_first_job_occupation",),
        ("p16_d2_occupation",),
        "M4 explicitly reuses the D2-D3 occupation instructions; this does not equate the printed jobs.",
    ),
    _xref(
        69,
        ("line", 6),
        "p69_xref_m28_to_l6",
        ("p68_m28_part_time_share",),
        ("p62_l6_part_time_share",),
        "M28 explicitly reuses the L6 part-time-share instruction.",
    ),
)


REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_16,
    *PAGE_20,
    *PAGE_22,
    *PAGE_24,
    *PAGE_28,
    *PAGE_32,
    *PAGE_34,
    *PAGE_38,
    *PAGE_42,
    *PAGE_48,
    *PAGE_62,
    *PAGE_64,
    *PAGE_68,
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
        if row["kind"] == F and len(paths) == 1:
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
            "whole_page_review": "all_74_pages_including_empty_occurrence_pages",
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
        f"document 15 source review: {len(review['occurrence_specs'])} "
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
