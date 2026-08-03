#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 11.

The authenticated source is the 68-page 1973 family question-by-question
manual, ``fam1973_QxQs.pdf``.  Every exact Poppler 26.04.0 UTF-8 page was read
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
import build_rq_stage2_document_011_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 68


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
    if mode == "bytes":
        start, end = selector[1], selector[2]
        raw = page_text.encode("utf-8")
        if not 0 <= start < end <= len(raw):
            raise SpecError(f"byte span {start}:{end} is outside the page")
        while start < end and raw[start : start + 1] in b" \t\r\n\f\v":
            start += 1
        while start < end and raw[end - 1 : end] in b" \t\r\n\f\v":
            end -= 1
        if start >= end:
            raise SpecError(f"byte span {selector[1]}:{selector[2]} is blank")
        raw[start:end].decode("utf-8", errors="strict")
        return start, end
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
    1: ("out", "the cover and section A child items"),
    2: ("out", "question-by-question objectives for child items"),
    3: ("out", "section B transportation items"),
    4: ("out", "question-by-question transportation prose"),
    5: ("out", "section C housing and moving items"),
    6: ("out", "housing prose with incidental work and pay examples"),
    7: ("out", "moving prose with incidental job examples"),
    8: ("out", "an explicit blank-page marker"),
    9: ("in", "section D head employment items D1-D9"),
    10: ("objectives", "section D employment-status assignment items"),
    11: ("objectives", "occupation and industry items D2-D3a"),
    12: ("objectives", "employment form, tenure, and prior-job items D4-D9"),
    13: ("in", "head work-exposure and hourly-pay items D10-D23"),
    14: ("objectives", "head work-exposure and hourly-pay items"),
    15: ("objectives", "hourly-rate items D21-D23"),
    16: ("out", "an explicit blank-page marker"),
    17: ("in", "head extra-job items D24-D29 and rejected labor-supply items"),
    18: (
        "objectives",
        "head extra-job items, with labor-supply preference prose rejected",
    ),
    19: ("in", "rejected commuting items and retained job-change item D37"),
    20: ("objectives", "commuting and contemplated-job-change items"),
    21: ("in", "section E sought-job, last-job, and work-time items"),
    22: ("objectives", "section E sought-job and last-job items"),
    23: (
        "in",
        "rejected commuting plus retained unacceptable-job and pay items",
    ),
    24: ("objectives", "rejected commuting plus retained pay-threshold items"),
    25: ("in", "section F actual-work and sought-job items"),
    26: ("objectives", "section F actual-work and sought-job items"),
    27: ("objectives", "section F unacceptable-job pay items"),
    28: ("out", "an explicit blank-page marker"),
    29: (
        "in",
        "section G wife employment items G1-G10, with G8 preference rejected",
    ),
    30: (
        "objectives",
        "wife employment items, with G8 preference prose rejected",
    ),
    31: ("out", "child-care items with incidental work references"),
    32: ("out", "child-care objective prose with work references"),
    33: ("out", "prospective child-care items with job references"),
    34: ("out", "question-by-question child-care prose"),
    35: ("out", "housework and household-help items"),
    36: ("out", "question-by-question housework prose"),
    37: ("in", "section H farm, business, and head-wage items"),
    38: ("objectives", "section H farm and business items"),
    39: ("objectives", "business and head-wage items"),
    40: ("out", "an explicit blank-page marker"),
    41: (
        "in",
        "head income items H9-H13; the incomplete H11 amount-entry fragment "
        "is not a flow branch",
    ),
    42: ("objectives", "head work-income and other-income items H9-H11"),
    43: (
        "objectives",
        "H11 dividend, interest, rent, trust, royalty, and welfare sources",
    ),
    44: ("objectives", "H11 welfare and Social Security sources"),
    45: (
        "objectives",
        "H11 retirement, pension, annuity, and compensation sources",
    ),
    46: ("objectives", "H11 remaining sources and H12-H13 family help"),
    47: ("in", "wife income-source and amount items H17-H20"),
    48: ("objectives", "welfare and wife-income items"),
    49: ("in", "other-family-member income items H21-H31"),
    50: ("objectives", "other-family-member income items"),
    51: ("in", "three repeated other-family-member income columns"),
    52: ("objectives", "the repeated other-family-member grid"),
    53: (
        "in",
        "retained other-member income and H34-H35 money, then rejected support items",
    ),
    54: ("objectives", "nonincome transfers and support items"),
    55: ("in", "new-wife education and section K new-head routing"),
    56: ("objectives", "new-wife education and new-head routing prose"),
    57: ("in", "new-head first-job work-history and background items"),
    58: ("objectives", "new-head first-job and background items"),
    59: (
        "out",
        "mobility, education, and veteran items with incidental job prose",
    ),
    60: ("out", "mobility and education objective prose with job references"),
    61: ("out", "education and veteran objective prose"),
    62: ("out", "an explicit blank-page marker"),
    63: ("out", "work-limiting health items"),
    64: ("out", "work-limiting health objective prose"),
    65: ("out", "interviewer-observation items"),
    66: ("out", "interviewer-observation objective prose"),
    67: ("out", "the thumbnail-sketch title"),
    68: ("out", "thumbnail-sketch instructions"),
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
D1_WORKING = SEC_D + ("p9_flow_d1_working",)
D1_OTHER = SEC_D + ("p9_flow_d1_other",)
D1_OTHER_HAS_JOB = D1_OTHER + ("p9_flow_d1_other_has_job",)
D2_PATHS = (D1_WORKING, D1_OTHER_HAS_JOB)
D3_PATHS = tuple(path + ("p9_flow_d3_probe",) for path in D2_PATHS)
D6_LONG_PATHS = tuple(path + ("p9_flow_d6_long",) for path in D2_PATHS)
D6_SHORT_PATHS = tuple(path + ("p9_flow_d6_short",) for path in D2_PATHS)
D9_BETTER_PATHS = tuple(
    path + ("p9_flow_d9_better",) for path in D6_SHORT_PATHS
)
D9_WORSE_PATHS = tuple(path + ("p9_flow_d9_worse",) for path in D6_SHORT_PATHS)
D9_SAME_PATHS = tuple(
    path + ("p9_flow_d9_same_exit",) for path in D6_SHORT_PATHS
)
D9_REASON_PATHS = D9_BETTER_PATHS + D9_WORSE_PATHS
D10_PATHS = D2_PATHS
D10_YES_PATHS = tuple(path + ("p13_flow_d10_yes",) for path in D10_PATHS)
D12_PATHS = D2_PATHS
D12_YES_PATHS = tuple(path + ("p13_flow_d12_yes",) for path in D12_PATHS)
D14_PATHS = D2_PATHS
D14_YES_PATHS = tuple(path + ("p13_flow_d14_yes",) for path in D14_PATHS)
D16_PATHS = D2_PATHS
D18_YES_PATHS = tuple(path + ("p13_flow_d18_yes",) for path in D16_PATHS)
D20_PATHS = D2_PATHS
D22_YES_PATHS = tuple(path + ("p13_flow_d22_yes",) for path in D20_PATHS)
D24_PATHS = D2_PATHS
D24_YES_PATHS = tuple(path + ("p15_flow_d24_yes",) for path in D24_PATHS)
D30_PATHS = D2_PATHS
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
G2_YES = G_WIFE_OCCUPATION + ("p25_flow_g2_yes",)
G2_NO = G_WIFE_OCCUPATION + ("p25_flow_g2_no",)
G9_WIFE_NOT_WORKING = G2_NO + ("p25_flow_g9_wife_not_working",)
SEC_H = ("p33_flow_section_h",)
H_FARMER = SEC_H + ("p33_flow_h1_farmer",)
H_NOT_FARMER = SEC_H + ("p33_flow_h1_not_farmer",)
H5_YES = SEC_H + ("p33_flow_h5_yes",)
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
_PREVIOUS_JOB_PARENT = "Parent job is D6's distinct previous-job noun."
_MAIN_JOB_PARENT = "Parent job is D16's printed main-job noun."
_EXTRA_JOB_PARENT = "Parent job is D24's printed extra-jobs noun."
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
        routes=(SEC_D,),
        note="D1 prints the head's current employment-status assignment.",
    ),
    word(9, 3, "(HEAD)", R, "p9_role_head_d1", routes=(SEC_D,)),
    word(9, 3, "present Job", J, "p9_job_present", routes=(SEC_D,)),
    word(
        9,
        6,
        "1. WORKING NOW",
        F,
        "p9_flow_d1_working",
        routes=(SEC_D,),
        note="Exact first-line atom for the answer that also includes temporary layoff.",
    ),
    word(
        9,
        6,
        "2. LOOKING FOR WORK",
        F,
        "p9_flow_d1_looking_exit",
        routes=(SEC_D,),
    ),
    word(9, 6, "3. RETIRED", F, "p9_flow_d1_retired", routes=(SEC_D,)),
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
        13,
        F,
        "p9_flow_d1_other",
        routes=(SEC_D,),
    ),
    span_words(
        9,
        13,
        "GO TO D2 IF HAS",
        14,
        "JOB",
        F,
        "p9_flow_d1_other_has_job",
        routes=(D1_OTHER,),
    ),
    from_word(
        9,
        14,
        "OTHERWISE",
        16,
        F,
        "p9_flow_d1_other_no_job_exit",
        routes=(D1_OTHER,),
    ),
    *paired(
        9,
        ("line", 18),
        "p9_d2_occupation",
        parents=("p9_job_present",),
        routes=D2_PATHS,
        note="D2 prints the main occupation of the present job.",
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(
        9,
        18,
        "main occupation",
        J,
        "p9_job_main_occupation",
        routes=D2_PATHS,
    ),
    word(9, 23, "(IF NOT CLEAR)", F, "p9_flow_d3_probe", routes=D2_PATHS),
    *paired(
        9,
        ("block", 23, 24),
        "p9_d3_occupation_detail",
        parents=("p9_job_present",),
        routes=D3_PATHS,
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 29),
        "p9_d4_industry",
        parents=("p9_job_present",),
        routes=D2_PATHS,
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 32),
        "p9_d5_employee_self",
        parents=("p9_job_present",),
        routes=D2_PATHS,
        parent_note=_PRESENT_JOB_PARENT,
    ),
    *paired(
        9,
        ("line", 35),
        "p9_d6_job_tenure",
        parents=("p9_job_present",),
        routes=D2_PATHS,
        parent_note=_PRESENT_JOB_PARENT,
    ),
    word(9, 35, "this job", J, "p9_job_tenure_noun", routes=D2_PATHS),
    line(9, 37, F, "p9_flow_d6_long", routes=D2_PATHS),
    line(9, 39, F, "p9_flow_d6_short", routes=D2_PATHS),
    *paired(
        9,
        ("block", 41, 42),
        "p9_d7_previous_job_outcome",
        parents=("p9_job_previous",),
        routes=D6_SHORT_PATHS,
        parent_note=_PREVIOUS_JOB_PARENT,
    ),
    word(
        9,
        41,
        "the job you had before",
        J,
        "p9_job_previous",
        routes=D6_SHORT_PATHS,
    ),
    *paired(
        9,
        ("line", 47),
        "p9_d8_relative_pay",
        parents=("p9_job_present", "p9_job_previous"),
        routes=D6_SHORT_PATHS,
        note="D7 prints a qualitative present-versus-previous-job pay comparison.",
        parent_note="The exact question names both compared jobs.",
    ),
    *paired(
        9,
        ("block", 50, 51),
        "p9_d9_job_comparison",
        parents=("p9_job_present", "p9_job_previous"),
        routes=D6_SHORT_PATHS,
        parent_note="The exact question names both compared jobs.",
    ),
    word(9, 47, "!1. BETTER I", F, "p9_flow_d9_better", routes=D6_SHORT_PATHS),
    word(9, 47, "[h}loRSE 1-", F, "p9_flow_d9_worse", routes=D6_SHORT_PATHS),
    tail(9, 47, "3. SAME", F, "p9_flow_d9_same_exit", routes=D6_SHORT_PATHS),
    *paired(
        9, ("line", 49), "p9_d10_comparison_reason", routes=D9_REASON_PATHS
    ),
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
        ("line", 2),
        "p13_d10_vacation_presence",
        routes=D10_PATHS,
    ),
    word(13, 4, "1. YES ]", F, "p13_flow_d10_yes", routes=D10_PATHS),
    word(
        13,
        5,
        "5 . NO I (GO TO Dl2)",
        F,
        "p13_flow_d10_no_exit",
        routes=D10_PATHS,
    ),
    *paired(
        13, ("line", 4), "p13_d11_vacation_duration", routes=D10_YES_PATHS
    ),
    *paired(
        13,
        ("block", 8, 9),
        "p13_d12_sick_absence_presence",
        routes=D12_PATHS,
    ),
    word(13, 11, "1. YES I", F, "p13_flow_d12_yes", routes=D12_PATHS),
    word(
        13,
        13,
        "5. NO I (GO TO Dl4)",
        F,
        "p13_flow_d12_no_exit",
        routes=D12_PATHS,
    ),
    *paired(
        13, ("line", 11), "p13_d13_sick_absence_duration", routes=D12_YES_PATHS
    ),
    *paired(
        13,
        ("line", 16),
        "p13_d14_unemployment_strike",
        routes=D14_PATHS,
        note="D14 prints unemployment-or-strike work absence.",
    ),
    word(13, 18, "1. YES I", F, "p13_flow_d14_yes", routes=D14_PATHS),
    word(
        13,
        19,
        "5. NO I (GO TO Dl6)",
        F,
        "p13_flow_d14_no_exit",
        routes=D14_PATHS,
    ),
    *paired(
        13,
        ("line", 18),
        "p13_d15_unemployment_duration",
        routes=D14_YES_PATHS,
    ),
    *paired(
        13,
        ("line", 22),
        "p13_d16_weeks_main_job",
        parents=("p13_job_main",),
        routes=D16_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 22, "main job", J, "p13_job_main", routes=D16_PATHS),
    *paired(
        13,
        ("block", 25, 26),
        "p13_d17_hours_main_job",
        parents=("p13_job_main",),
        routes=D16_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("line", 29),
        "p13_d18_overtime_presence",
        parents=("p13_job_main",),
        routes=D16_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(
        13,
        29,
        "overtime",
        M,
        "p13_d18_overtime_component",
        parents=("p13_job_main",),
        routes=D16_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 31, "[ ] YES", F, "p13_flow_d18_yes", routes=D16_PATHS),
    tail(13, 31, "[ ) NO", F, "p13_flow_d18_no_exit", routes=D16_PATHS),
    *paired(
        13,
        ("line", 34),
        "p13_d19_overtime_hours",
        parents=("p13_job_main",),
        routes=D18_YES_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("block", 38, 39),
        "p13_d20_extra_hours_pay",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=D20_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("needle", 44, "D21. What would be your hourly rate", 0),
        "p13_d21_overtime_rate",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=D20_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    *paired(
        13,
        ("needle", 44, "D22. Do you have an hourly wage rate", 0),
        "p13_d22_hourly_status",
        parents=("p13_job_main",),
        routes=D20_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
    word(13, 47, "11. YES I", F, "p13_flow_d22_yes", routes=D20_PATHS),
    word(
        13,
        47,
        "5 . NO",
        F,
        "p13_flow_d22_no_exit",
        routes=D20_PATHS,
    ),
    *paired(
        13,
        ("line", 51),
        "p13_d23_regular_hourly_rate",
        anchor_kind=M,
        parents=("p13_job_main",),
        routes=D22_YES_PATHS,
        parent_note=_MAIN_JOB_PARENT,
    ),
)


PAGE_14 = (
    *paired(14, ("block", 4, 6), "p14_employment_year_accounting"),
    word(14, 4, "head's", R, "p14_role_head_accounting"),
    word(14, 6, "main job", J, "p14_job_main_accounting"),
    *paired(14, ("block", 13, 17), "p14_d10_d11_vacation_purpose"),
    *paired(14, ("block", 21, 24), "p14_d12_d13_sick_leave_purpose"),
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
        17,
        ("block", 2, 3),
        "p15_d25_extra_jobs",
        parents=("p15_job_extra", "p13_job_main"),
        routes=D24_PATHS,
        parent_note="The question names both the extra-jobs source and main job.",
    ),
    word(17, 2, "extra jobs", J, "p15_job_extra", routes=D24_PATHS),
    word(17, 3, "main job", J, "p15_job_main_reference", routes=D24_PATHS),
    word(17, 5, "1. YES I", F, "p15_flow_d24_yes", routes=D24_PATHS),
    tail(17, 5, "5. NO I", F, "p15_flow_d24_no_exit", routes=D24_PATHS),
    *paired(
        17,
        ("line", 8),
        "p15_d26_occupation",
        parents=("p15_job_extra",),
        routes=D24_YES_PATHS,
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        17,
        ("line", 13),
        "p15_d27_anything_else",
        routes=D24_YES_PATHS,
        note="D26 is a probe for additional duties within D25's work description.",
    ),
    *paired(
        17,
        ("block", 15, 16),
        "p15_d28_extra_hourly_rate",
        anchor_kind=M,
        parents=("p15_job_extra",),
        routes=D24_YES_PATHS,
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        17,
        ("line", 17),
        "p15_d29_extra_weeks",
        parents=("p15_job_extra",),
        routes=D24_YES_PATHS,
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        17,
        ("line", 19),
        "p15_d30_extra_hours",
        parents=("p15_job_extra",),
        routes=D24_YES_PATHS,
        parent_note=_EXTRA_JOB_PARENT,
    ),
    *paired(
        17,
        ("block", 24, 25),
        "p15_d30_work_availability",
        parents=("p9_job_present", "p15_job_extra"),
        routes=D30_PATHS,
        parent_note="D30 explicitly names the current job or jobs.",
    ),
    word(17, 27, "I 1. YES I", F, "p15_flow_d30_yes_exit", routes=D30_PATHS),
    word(
        17,
        27,
        "I 5. NO OR DON'T KNOW I",
        F,
        "p15_flow_d30_no_exit",
        routes=D30_PATHS,
    ),
)


PAGE_16 = (
    *paired(18, ("block", 5, 6), "p16_d25_job_boundary"),
    word(18, 5, "second jobs", J, "p16_job_second"),
    span_words(
        18,
        5,
        "main",
        6,
        "job",
        J,
        "p16_job_main_previous_phrase",
    ),
    word(18, 6, "head's", R, "p16_role_head_current_employment"),
    *paired(
        18,
        ("block", 7, 14),
        "p16_d25_extra_income_scope",
        anchor_kind=M,
    ),
    word(18, 7, "irregular jobs", J, "p16_job_irregular"),
    *paired(
        18,
        ("block", 20, 23),
        "p16_d28_hourly_pay_purpose",
        anchor_kind=M,
    ),
    word(18, 22, "extra job", J, "p16_job_extra_rate"),
    *paired(18, ("block", 26, 29), "p16_d29_d30_time_purpose"),
    *paired(18, ("block", 32, 35), "p16_d30_availability_purpose"),
    word(18, 32, "head", R, "p16_role_head_availability"),
    word(18, 33, "present job(s)", J, "p16_job_present_availability"),
)


PAGE_17 = (
    *paired(19, ("block", 17, 18), "p17_d38_job_intention", routes=(SEC_D,)),
    word(19, 17, "new job", J, "p17_job_new", routes=(SEC_D,)),
    span_words(
        19,
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
    *paired(20, ("block", 25, 26), "p18_d38_new_job_definition"),
    word(20, 25, "new job", J, "p18_job_new"),
    word(20, 25, "same employer", J, "p18_job_same_employer"),
    word(20, 25, "different employer", J, "p18_job_different_employer"),
)


PAGE_19 = (
    tail(21, 1, "SECTION E:", F, "p19_flow_section_e"),
    *paired(21, ("line", 4), "p19_e1_sought_job", routes=(SEC_E,)),
    word(21, 4, "job", J, "p19_job_sought", routes=(SEC_E,)),
    *paired(
        21,
        ("line", 9),
        "p19_e2_expected_earnings",
        anchor_kind=M,
        parents=("p19_job_sought",),
        routes=(SEC_E,),
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    *paired(
        21,
        ("line", 12),
        "p19_e3_training",
        parents=("p19_job_sought",),
        routes=(SEC_E,),
        parent_note=_SOUGHT_JOB_PARENT,
    ),
    *paired(21, ("line", 17), "p19_e4_search_action", routes=(SEC_E,)),
    tail(21, 18, "5. NOTHING", F, "p19_flow_e4_nothing", routes=(SEC_E,)),
    *paired(21, ("line", 21), "p19_e5_search_places", routes=(SEC_E,)),
    *paired(
        21,
        ("line", 26),
        "p19_e6_last_job_occupation",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    word(21, 26, "last job", J, "p19_job_last", routes=(SEC_E,)),
    *paired(
        21,
        ("line", 29),
        "p19_e7_last_job_industry",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        21,
        ("block", 32, 33),
        "p19_e8_last_job_outcome",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(
        21,
        ("line", 38),
        "p19_e9_weeks_worked",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    tail(21, 38, "~0. NONE I", F, "p19_flow_e9_none", routes=(SEC_E,)),
    *paired(
        21,
        ("line", 41),
        "p19_e10_hours_worked",
        parents=("p19_job_last",),
        routes=(SEC_E,),
        parent_note=_LAST_JOB_PARENT,
    ),
    *paired(21, ("line", 43), "p19_e11_sick_weeks", routes=(SEC_E,)),
    *paired(21, ("line", 46), "p19_e12_unemployed_weeks", routes=(SEC_E,)),
)


PAGE_20 = (
    *paired(22, ("block", 5, 6), "p20_e1_occupation_purpose", routes=(SEC_E,)),
    *paired(
        22,
        ("line", 9),
        "p20_e2_pay_period_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
    *paired(22, ("block", 12, 13), "p20_e3_training_purpose", routes=(SEC_E,)),
    *paired(22, ("block", 17, 18), "p20_e4_search_purpose", routes=(SEC_E,)),
    *paired(22, ("block", 23, 24), "p20_e5_places_purpose", routes=(SEC_E,)),
    *paired(22, ("line", 44), "p20_e9_weeks_purpose", routes=(SEC_E,)),
    *paired(22, ("block", 47, 48), "p20_e10_hours_purpose", routes=(SEC_E,)),
    word(22, 47, "head", R, "p20_role_head_schedule", routes=(SEC_E,)),
    *paired(22, ("block", 50, 53), "p20_e11_sick_purpose", routes=(SEC_E,)),
    *paired(22, ("block", 54, 55), "p20_e12_year_check", routes=(SEC_E,)),
)


E15_PATHS = (SEC_E,)
E15_YES_PATHS = (SEC_E + ("p21_flow_e15_yes",),)
E17_PATHS = (SEC_E,)
E17_YES_PATHS = (SEC_E + ("p21_flow_e17_yes",),)

PAGE_21 = (
    *paired(23, ("line", 2), "p21_e11_work_checkpoint", routes=(SEC_E,)),
    word(
        23, 4, "[ ] WORKED IN 1972", F, "p21_flow_e11_worked", routes=(SEC_E,)
    ),
    word(
        23,
        4,
        "[]DID NOT '.JORK IN 1972",
        F,
        "p21_flow_e11_not_worked",
        routes=(SEC_E,),
    ),
    *paired(
        23, ("line", 20), "p21_e17_jobs_not_worth_taking", routes=E15_PATHS
    ),
    word(23, 20, "jobs available", J, "p21_job_available", routes=E15_PATHS),
    word(23, 22, "[t'     mf]", F, "p21_flow_e15_yes", routes=E15_PATHS),
    tail(23, 22, "I s. NO I", F, "p21_flow_e15_no", routes=E15_PATHS),
    *paired(
        23,
        ("line", 24),
        "p21_e18_unacceptable_pay",
        anchor_kind=M,
        parents=("p21_job_available",),
        routes=E15_YES_PATHS,
        parent_note="The amount applies to E15's jobs-available source.",
    ),
    *paired(
        23, ("block", 30, 31), "p21_e19_good_job_mobility", routes=E17_PATHS
    ),
    word(23, 31, "job there", J, "p21_job_good_mobility", routes=E17_PATHS),
    word(
        23,
        33,
        "1. YES, MAYBF,, OR DEPENDS",
        F,
        "p21_flow_e17_yes",
        routes=E17_PATHS,
    ),
    word(23, 35, "NO   !", F, "p21_flow_e17_no_exit", routes=E17_PATHS),
    spec(
        23,
        P,
        ("needle", 37, "El8. How much would a job have", 0),
        "p21_e18_required_pay_start_prompt",
        routes=E17_YES_PATHS,
        note="Exact first printed fragment of the split E18 amount prompt.",
    ),
    *paired(
        23,
        ("span", 38, "to pay for you", 39, "ing to move?", 0, 0),
        "p21_e18_required_pay_finish",
        anchor_kind=M,
        parents=("p21_job_good_mobility",),
        routes=E17_YES_PATHS,
        parent_note="The amount applies to the exact good-job mobility source.",
    ),
)


PAGE_22 = (
    *paired(
        24,
        ("block", 25, 28),
        "p22_e17_e18_unacceptable_pay_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
    span_words(
        24,
        26,
        "jobs in the",
        27,
        "area",
        J,
        "p22_job_jobs_in_area",
        routes=(SEC_E,),
    ),
    *paired(
        24,
        ("block", 35, 37),
        "p22_e20_pay_period_purpose",
        anchor_kind=M,
        routes=(SEC_E,),
    ),
)


PAGE_23 = (
    tail(25, 1, "SECTION F:", F, "p23_flow_section_f"),
    *paired(
        25,
        ("line", 4),
        "p23_f1_work_for_money",
        anchor_kind=M,
        routes=(SEC_F,),
    ),
    word(25, 4, "(HEAD)", R, "p23_role_head_f1", routes=(SEC_F,)),
    word(
        25, 4, "work for money", J, "p23_job_work_for_money", routes=(SEC_F,)
    ),
    *paired(25, ("line", 8), "p23_f2_future_work", routes=(SEC_F,)),
    word(25, 10, "1 . YES", F, "p23_flow_f2_yes", routes=(SEC_F,)),
    tail(25, 10, "5. NO I", F, "p23_flow_f2_no_exit", routes=(SEC_F,)),
    *paired(25, ("line", 14), "p23_f3_occupation", routes=(SEC_F,)),
    word(
        25, 14, "occupation", J, "p23_job_actual_occupation", routes=(SEC_F,)
    ),
    *paired(
        25,
        ("line", 18),
        "p23_f4_industry",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(
        25,
        ("line", 22),
        "p23_f5_weeks_worked",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(
        25,
        ("line", 24),
        "p23_f6_hours_worked",
        parents=("p23_job_actual_occupation",),
        routes=(SEC_F,),
        parent_note="F3's exact occupation is the local job parent.",
    ),
    *paired(25, ("line", 26), "p23_f7_new_job", routes=(SEC_F,)),
    word(25, 26, "new job", J, "p23_job_new", routes=(SEC_F,)),
    word(25, 27, "I l. YES I", F, "p23_flow_f7_yes", routes=(SEC_F,)),
    tail(25, 27, "I 5. NO I", F, "p23_flow_f7_no_exit", routes=(SEC_F,)),
    line(
        25,
        29,
        F,
        "p23_flow_f2_or_f7",
        routes=(F2_YES, F7_YES),
        note="Exact multiparent condition printed for affirmative F2 or F6.",
    ),
    *paired(
        25,
        ("line", 31),
        "p23_f8_job_in_mind",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    word(
        25,
        31,
        "job do you have in mind",
        J,
        "p23_job_in_mind",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        25,
        ("line", 35),
        "p23_f9_expected_earnings",
        anchor_kind=M,
        parents=("p23_job_in_mind",),
        routes=(F8_FROM_F2, F8_FROM_F7),
        parent_note="F7's job-in-mind noun is the local job parent.",
    ),
    *paired(
        25, ("line", 37), "p23_f10_training", routes=(F8_FROM_F2, F8_FROM_F7)
    ),
    *paired(
        25,
        ("line", 39),
        "p23_f11_search_action",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    tail(
        25,
        41,
        "5 . NOTHING",
        F,
        "p23_flow_f11_nothing",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        25,
        ("block", 43, 44),
        "p23_f12_search_places",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        25,
        ("line", 47),
        "p23_f13_jobs_not_worth_taking",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    word(
        25,
        47,
        "jobs around here",
        J,
        "p23_job_jobs_around_here",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    tail(
        25,
        48,
        "5. NO",
        F,
        "p23_flow_f13_no_exit",
        routes=(F8_FROM_F2, F8_FROM_F7),
    ),
    *paired(
        25,
        ("line", 51),
        "p23_f14_unacceptable_pay",
        anchor_kind=M,
        parents=("p23_job_jobs_around_here",),
        routes=(F8_FROM_F2, F8_FROM_F7),
        parent_note="F12's jobs-around-here noun is the local job parent.",
    ),
)


PAGE_24 = (
    *paired(26, ("block", 7, 9), "p24_f1_money_work_purpose", anchor_kind=M),
    word(26, 7, "heads", R, "p24_role_heads_f1"),
    word(26, 8, "full - time job", J, "p24_job_full_time_prior"),
    *paired(26, ("block", 12, 13), "p24_f2_work_timing_purpose"),
    *paired(26, ("block", 22, 25), "p24_f5_f6_hours_purpose"),
    word(26, 23, "heads", R, "p24_role_heads_hours"),
    *paired(26, ("block", 28, 30), "p24_f7_new_job_definition"),
    word(26, 28, '"New job"', J, "p24_job_new"),
    word(26, 28, "same employer", J, "p24_job_same_employer"),
    *paired(26, ("block", 33, 34), "p24_f8_job_in_mind_purpose"),
    word(26, 34, "job he has in mind", J, "p24_job_in_mind"),
    *paired(26, ("line", 37), "p24_f9_pay_period_purpose", anchor_kind=M),
    *paired(26, ("block", 40, 41), "p24_f10_training_purpose"),
    *paired(26, ("block", 44, 45), "p24_f11_search_purpose"),
    *paired(26, ("block", 48, 49), "p24_f12_places_purpose"),
    *paired(
        26,
        ("block", 52, 55),
        "p24_f13_f14_unacceptable_pay_purpose",
        anchor_kind=M,
    ),
    word(26, 53, "jobs around here", J, "p24_job_jobs_around_here"),
)


PAGE_25 = (
    tail(29, 2, "SECTION G:", F, "p25_flow_section_g"),
    *paired(29, ("line", 6), "p25_g1_marital_status", routes=(SEC_G,)),
    word(29, 8, "[i. MARRIED I", F, "p25_flow_g1_married", routes=(SEC_G,)),
    word(
        29,
        10,
        "2. SINGLE",
        F,
        "p25_flow_g1_single",
        routes=(SEC_G,),
    ),
    word(29, 10, "3. HIDOIV", F, "p25_flow_g1_other", routes=(SEC_G,)),
    word(
        29,
        10,
        "(TURN TO Gll, PAGE 12)",
        F,
        "p25_flow_g1_nonwife_exit",
        routes=(
            SEC_G + ("p25_flow_g1_single",),
            SEC_G + ("p25_flow_g1_other",),
        ),
    ),
    line(
        29,
        16,
        F,
        "p25_flow_wife_occupation_scope",
        routes=(G_MARRIED,),
    ),
    word(
        29,
        16,
        "WIFE ' s",
        R,
        "p25_role_wife_scope",
        routes=(G_WIFE_OCCUPATION,),
    ),
    *paired(
        29,
        ("block", 18, 21),
        "p25_g2_wife_work_for_money",
        anchor_kind=M,
        routes=(G_WIFE_OCCUPATION,),
    ),
    word(29, 21, "wife", R, "p25_role_wife_g2", routes=(G_WIFE_OCCUPATION,)),
    word(
        29,
        21,
        "work for money",
        J,
        "p25_job_wife_work",
        routes=(G_WIFE_OCCUPATION,),
    ),
    word(29, 18, "cpESj", F, "p25_flow_g2_yes", routes=(G_WIFE_OCCUPATION,)),
    tail(29, 23, "5 . NO", F, "p25_flow_g2_no", routes=(G_WIFE_OCCUPATION,)),
    *paired(
        29,
        ("line", 25),
        "p25_g3_wife_occupation",
        parents=("p25_job_wife_work",),
        routes=(G2_YES,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        29,
        ("line", 29),
        "p25_g4_wife_industry",
        parents=("p25_job_wife_work",),
        routes=(G2_YES,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        29,
        ("line", 35),
        "p25_g6_wife_hours",
        parents=("p25_job_wife_work",),
        routes=(G2_YES,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    *paired(
        29,
        ("block", 37, 38),
        "p25_g7_wife_work_availability",
        parents=("p25_job_wife_work",),
        routes=(G2_YES,),
        parent_note="G2's work-for-money noun is the local wife-job parent.",
    ),
    tail(
        29,
        40,
        "I!. YES]",
        F,
        "p25_flow_g7_yes_exit",
        routes=(G2_YES,),
    ),
    *paired(29, ("line", 44), "p25_g9_wife_work_checkpoint", routes=(G2_NO,)),
    word(
        29,
        45,
        "UNDER 65 AND DID NOT",
        F,
        "p25_flow_g9_wife_not_working",
        routes=(G2_NO,),
    ),
    tail(
        29,
        45,
        "[~]ALL OTHERS",
        F,
        "p25_flow_g9_all_others_exit",
        routes=(G2_NO,),
    ),
    *paired(
        29,
        ("block", 48, 49),
        "p25_g10_wife_future_work",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        29,
        48,
        "wife",
        R,
        "p25_role_wife_g10",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        29,
        51,
        "I 1. YES I",
        F,
        "p25_flow_g10_yes",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        29,
        51,
        "3. DEPENDS",
        F,
        "p25_flow_g10_depends",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        29,
        51,
        "js. NO",
        F,
        "p25_flow_g10_no",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
)


PAGE_26 = (
    *paired(
        30, ("block", 12, 14), "p26_g1_female_head_context", routes=(SEC_G,)
    ),
    word(30, 12, "female head", R, "p26_role_female_head", routes=(SEC_G,)),
    *paired(
        30,
        ("block", 31, 32),
        "p26_g10_wife_new_job_context",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        30,
        31,
        "wife",
        R,
        "p26_role_wife_new_job",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
    word(
        30,
        31,
        "a job",
        J,
        "p26_job_wife_new",
        routes=(G9_WIFE_NOT_WORKING,),
    ),
)


PAGE_27 = (
    *paired(31, ("line", 2), "p27_g13_wife_career_years", routes=(G_MARRIED,)),
    word(31, 2, "wife", R, "p27_role_wife_career", routes=(G_MARRIED,)),
    *paired(
        31, ("line", 7), "p27_g14_wife_full_time_years", routes=(G_MARRIED,)
    ),
    tail(31, 12, "I ALL I", F, "p27_flow_g14_all_exit", routes=(G_MARRIED,)),
    *paired(
        31,
        ("line", 13),
        "p27_g15_wife_part_time_fraction",
        routes=(G2_YES,),
    ),
)


PAGE_29 = (
    *paired(33, ("line", 3), "p29_g22_head_career_years", routes=(SEC_G,)),
    word(33, 3, "(HEAD)", R, "p29_role_head_career", routes=(SEC_G,)),
    tail(33, 5, "00. NONE", F, "p29_flow_g22_none", routes=(SEC_G,)),
    *paired(33, ("line", 7), "p29_g23_head_full_time_years", routes=(SEC_G,)),
    word(33, 7, "(HEAD)", R, "p29_role_head_full_time", routes=(SEC_G,)),
    tail(33, 9, "[A-i.x:-1", F, "p29_flow_g23_all_exit", routes=(SEC_G,)),
    *paired(
        33,
        ("block", 10, 11),
        "p29_g24_head_part_time_fraction",
        routes=(SEC_G,),
    ),
    word(33, 10, "(HEAD)", R, "p29_role_head_part_time", routes=(SEC_G,)),
)


PAGE_30 = (
    *paired(34, ("block", 5, 8), "p30_g24_fraction_purpose", routes=(SEC_G,)),
)


PAGE_33 = (
    tail(37, 2, "SECTION H:", F, "p33_flow_section_h"),
    *paired(37, ("block", 6, 7), "p33_income_preamble", routes=(SEC_H,)),
    *paired(
        37, ("block", 10, 12), "p33_h1_farmer_classification", routes=(SEC_H,)
    ),
    word(
        37,
        12,
        "1. FARMER, OR RANCHER I",
        F,
        "p33_flow_h1_farmer",
        routes=(SEC_H,),
    ),
    word(
        37,
        12,
        "1. FARMER, OR RANCHER",
        FA,
        "p33_farm_classification_aggregate",
        routes=(SEC_H,),
    ),
    tail(
        37,
        12,
        "5. NOT A FARMER OR RANCHER I",
        F,
        "p33_flow_h1_not_farmer",
        routes=(SEC_H,),
    ),
    *paired(
        37,
        ("block", 15, 16),
        "p33_h2_farm_receipts",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    word(37, 15, "farming", FA, "p33_farming_aggregate", routes=(H_FARMER,)),
    *paired(
        37,
        ("block", 18, 20),
        "p33_h3_farm_expenses",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        37,
        ("line", 21),
        "p33_h4_net_farm_income",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(H_FARMER,),
        parent_note=_FARM_PARENT,
    ),
    word(
        37,
        21,
        "net income from farming",
        FA,
        "p33_farm_aggregate",
        routes=(H_FARMER,),
    ),
    *paired(
        37, ("block", 25, 26), "p33_h5_business_interest", routes=(SEC_H,)
    ),
    word(
        37,
        25,
        "a business",
        BA,
        "p33_business_interest_aggregate",
        routes=(SEC_H,),
    ),
    word(37, 31, "4· YES", F, "p33_flow_h5_yes", routes=(SEC_H,)),
    tail(37, 28, "s. NO I", F, "p33_flow_h5_no_exit", routes=(SEC_H,)),
    *paired(
        37,
        ("block", 30, 31),
        "p33_h6_business_form",
        parents=("p33_business_aggregate",),
        routes=(H5_YES,),
        parent_note=_BUSINESS_PARENT,
    ),
    word(
        37,
        30,
        "unincorporated business",
        BA,
        "p33_business_aggregate",
        routes=(H5_YES,),
    ),
    word(
        37,
        38,
        "I 8. DON T KNOH I",
        F,
        "p33_flow_h6_dont_know",
        routes=(H5_YES,),
    ),
    *paired(
        37,
        ("block", 39, 42),
        "p33_h7_business_share",
        anchor_kind=M,
        parents=("p33_business_aggregate",),
        routes=(H5_YES,),
        parent_note=_BUSINESS_PARENT,
    ),
    *paired(
        37,
        ("block", 47, 48),
        "p33_h8_head_wages_total",
        anchor_kind=T,
        routes=(SEC_H,),
    ),
    word(37, 47, "(HEAD)", R, "p33_role_head_h8", routes=(SEC_H,)),
    word(
        37,
        47,
        "wages and salaries",
        M,
        "p33_h8_wages_component",
        routes=(SEC_H,),
    ),
)


PAGE_34 = (
    *paired(38, ("block", 7, 9), "p34_h1_farmer_definition", routes=(SEC_H,)),
    word(38, 7, "A farmer", FA, "p34_farmer_aggregate", routes=(SEC_H,)),
    *paired(
        38,
        ("block", 13, 25),
        "p34_h2_receipts_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        38,
        ("block", 28, 38),
        "p34_h3_expenses_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    *paired(
        38,
        ("block", 41, 43),
        "p34_h4_net_income_purpose",
        anchor_kind=M,
        parents=("p33_farm_aggregate",),
        routes=(SEC_H,),
        parent_note=_FARM_PARENT,
    ),
    word(
        38, 41, "Farm income", FA, "p34_farm_income_aggregate", routes=(SEC_H,)
    ),
    *paired(38, ("block", 46, 49), "p34_h5_business_purpose", routes=(SEC_H,)),
    word(
        38, 47, "The business", BA, "p34_business_aggregate", routes=(SEC_H,)
    ),
    *paired(
        38, ("block", 52, 55), "p34_h6_corporation_purpose", routes=(SEC_H,)
    ),
    word(
        38,
        53,
        '"corporation"',
        BA,
        "p34_corporation_aggregate",
        routes=(SEC_H,),
    ),
)


PAGE_35 = (
    *paired(
        39,
        ("block", 5, 9),
        "p35_h7_business_profit_purpose",
        anchor_kind=M,
        parents=("p33_business_aggregate",),
        routes=(SEC_H,),
        parent_note=_BUSINESS_PARENT,
    ),
    word(39, 5, "the business", BA, "p35_business_aggregate", routes=(SEC_H,)),
    word(39, 8, "wife", R, "p35_role_wife_business", routes=(SEC_H,)),
    *paired(
        39,
        ("block", 12, 14),
        "p35_h8_head_total_purpose",
        anchor_kind=T,
        routes=(SEC_H,),
    ),
    word(
        39,
        12,
        "1973 Head of the FU",
        R,
        "p35_role_head_total",
        routes=(SEC_H,),
    ),
    word(39, 14, "second job", J, "p35_job_second", routes=(SEC_H,)),
    *paired(
        39,
        ("block", 16, 21),
        "p35_fixed_salary_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        39,
        ("block", 22, 24),
        "p35_complicated_history_purpose",
        routes=(SEC_H,),
    ),
    word(39, 22, "several jobs", J, "p35_job_several", routes=(SEC_H,)),
    *paired(
        39,
        ("block", 25, 28),
        "p35_businessman_wage_allocation",
        anchor_kind=M,
        parents=("p35_job_other",),
        routes=(SEC_H,),
        parent_note="The prose explicitly assigns the included wages to another job.",
    ),
    word(
        39,
        25,
        "unincorporated business",
        BA,
        "p35_unincorporated_business_aggregate",
        routes=(SEC_H,),
    ),
    word(39, 27, "some other job", J, "p35_job_other", routes=(SEC_H,)),
)


PAGE_37 = (
    *paired(
        41,
        ("block", 2, 3),
        "p37_h9_bonus_overtime_commission",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    tail(41, 5, "[ ]NO", F, "p37_flow_h9_no", routes=(SEC_H,)),
    *paired(
        41, ("line", 10), "p37_h10_amount", anchor_kind=M, routes=(SEC_H,)
    ),
    *paired(41, ("line", 13), "p37_h11_other_income_header", routes=(SEC_H,)),
    word(41, 13, "(HEAD)", R, "p37_role_head_h11", routes=(SEC_H,)),
    *paired(
        41,
        ("needle", 15, "a) professional practice or trade?", 0),
        "p37_h11a_professional_trade",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 17, 19),
        "p37_h11b_farming_roomers",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        41,
        17,
        "farming or market gardening",
        FA,
        "p37_farming_market_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 21, 22),
        "p37_h11c_dividend_interest_rent",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41, ("line", 24), "p37_h11d_adc_afdc", anchor_kind=M, routes=(SEC_H,)
    ),
    *paired(
        41,
        ("line", 26),
        "p37_h11e_other_welfare",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("line", 28),
        "p37_h11f_social_security",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 29, 30),
        "p37_h11g_retirement_pension_annuity",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 31, 32),
        "p37_h11h_unemployment_workmens_comp",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("line", 34),
        "p37_h11i_alimony_child_support",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("line", 36),
        "p37_h11j_relatives",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        41,
        ("block", 38, 39),
        "p37_h11k_other",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(41, ("block", 42, 43), "p37_h12_outside_help", routes=(SEC_H,)),
    word(41, 45, "[ ]YES", F, "p37_flow_h12_yes", routes=(SEC_H,)),
    tail(41, 45, "[ ]NO", F, "p37_flow_h12_no_exit", routes=(SEC_H,)),
    *paired(
        41,
        ("block", 47, 48),
        "p37_h13_outside_help_amount",
        anchor_kind=M,
        routes=(H12_YES,),
    ),
)


PAGE_38 = (
    *paired(
        42,
        ("block", 9, 14),
        "p38_h11_periodicity_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 17, 25),
        "p38_h11a_professional_trade_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        42,
        19,
        "self employed doctors",
        BA,
        "p38_self_employed_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 28, 34),
        "p38_h11b_farming_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        42,
        28,
        "FARMING OR MARKET GARDENING",
        FA,
        "p38_farming_market_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 36, 38),
        "p38_h11b_roomers_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 41, 47),
        "p38_h11c_dividends_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        42,
        42,
        "small incorporated business",
        BA,
        "p38_incorporated_business_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 49, 51),
        "p38_h11c_interest_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        42,
        ("block", 53, 57),
        "p38_h11c_rent_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_39 = (
    *paired(
        43,
        ("block", 4, 6),
        "p39_h11c_trust_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        43,
        ("block", 8, 11),
        "p39_h11c_royalty_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        43,
        ("block", 14, 28),
        "p39_h11d_adc_afdc_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        43,
        ("block", 31, 48),
        "p39_h11e_other_welfare_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        43,
        ("block", 51, 53),
        "p39_h11f_social_security_start",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_40 = (
    *paired(
        44,
        ("block", 4, 15),
        "p40_h11f_social_security_continued",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        44,
        ("block", 18, 19),
        "p40_h11g_retirement_pay_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        44,
        ("block", 21, 38),
        "p40_h11g_pension_annuity_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(
        44,
        21,
        "previous employers",
        J,
        "p40_job_previous_employers",
        routes=(SEC_H,),
    ),
    *paired(
        44,
        ("block", 41, 48),
        "p40_h11h_unemployment_comp_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    span_words(
        44,
        47,
        "self-",
        48,
        "employed",
        BA,
        "p40_self_employed_aggregate",
        routes=(SEC_H,),
    ),
    *paired(
        44,
        ("block", 50, 55),
        "p40_h11h_workmens_comp_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(44, 53, "his job", J, "p40_job_injury_source", routes=(SEC_H,)),
)


PAGE_41 = (
    *paired(
        45,
        ("block", 5, 8),
        "p41_h11i_alimony_support_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        45,
        ("block", 11, 13),
        "p41_h11j_relative_help_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        45,
        ("block", 16, 19),
        "p41_h11k_training_allowance_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        45,
        ("block", 21, 22),
        "p41_h11k_illegal_income_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        45,
        ("block", 27, 29),
        "p41_h12_h13_family_help_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_43 = (
    word(
        47,
        7,
        "[ ] INCOME FROM WELFARE OR ADC, AFDC",
        F,
        "p43_flow_h14_welfare",
        routes=(SEC_H,),
    ),
    tail(
        47,
        7,
        "[ J NO SUCH INCOME",
        F,
        "p43_flow_h14_no_exit",
        routes=(SEC_H,),
    ),
    *paired(
        47,
        ("block", 10, 11),
        "p43_h15_non_cash_welfare",
        anchor_kind=M,
        routes=(H14_WELFARE,),
    ),
    word(47, 13, "[ ] YES", F, "p43_flow_h15_yes", routes=(H14_WELFARE,)),
    tail(47, 13, "[ ] NO", F, "p43_flow_h15_no_exit", routes=(H14_WELFARE,)),
    *paired(
        47,
        ("block", 15, 16),
        "p43_h16_welfare_amount",
        anchor_kind=M,
        routes=(H15_YES,),
    ),
    *paired(47, ("line", 19), "p43_h17_wife_checkpoint", routes=(SEC_H,)),
    word(47, 19, "HEAD", R, "p43_role_head_h17", routes=(SEC_H,)),
    word(47, 19, "WIFE", R, "p43_role_wife_h17", routes=(SEC_H,)),
    word(
        47,
        21,
        "[ ] YES, WIFE IN FU",
        F,
        "p43_flow_h17_wife",
        routes=(SEC_H,),
    ),
    tail(
        47,
        21,
        "[ ] NO WIFE IN FU",
        F,
        "p43_flow_h17_no_wife",
        routes=(SEC_H,),
    ),
    *paired(47, ("line", 23), "p43_h18_wife_income", routes=(H_WIFE,)),
    word(47, 23, "wife", R, "p43_role_wife_h18", routes=(H_WIFE,)),
    word(47, 24, "[t ] YES", F, "p43_flow_h18_yes", routes=(H_WIFE,)),
    tail(47, 24, "[ ] NO", F, "p43_flow_h18_no_exit", routes=(H_WIFE,)),
    *paired(47, ("line", 26), "p43_h19_wife_income_source", routes=(H18_YES,)),
    word(
        47,
        26,
        "wages, salary",
        M,
        "p43_h19_wage_salary_component",
        routes=(H18_YES,),
    ),
    word(
        47,
        26,
        "a business",
        BA,
        "p43_h19_business_aggregate",
        routes=(H18_YES,),
    ),
    *paired(
        47,
        ("block", 31, 32),
        "p43_h20_wife_income_total",
        anchor_kind=T,
        routes=(H18_YES,),
    ),
)


PAGE_44 = (
    *paired(
        48,
        ("block", 6, 16),
        "p44_h14_h16_welfare_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        48,
        ("block", 22, 27),
        "p44_wife_all_sources_purpose",
        anchor_kind=T,
        routes=(SEC_H,),
        note="H17-H20 defines the wife's complete all-source income total and stock-income boundary.",
    ),
    word(
        48, 22, "wife's income", R, "p44_role_wife_all_income", routes=(SEC_H,)
    ),
    word(
        48,
        29,
        "wife's income",
        R,
        "p44_role_wife_business_income",
        routes=(SEC_H,),
    ),
    span_words(
        48,
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
    *paired(49, ("block", 2, 6), "p45_h21_member_schedule", routes=(SEC_H,)),
    word(
        49,
        9,
        "RELATION TO HEAD",
        R,
        "p45_role_head_member_relation",
        routes=(SEC_H,),
    ),
    from_word(
        49,
        5,
        "IF NO SUCH PEOPLE",
        6,
        F,
        "p45_flow_h21_no_people_exit",
        routes=(SEC_H,),
    ),
    *paired(49, ("block", 8, 11), "p45_h22_member_income", routes=(SEC_H,)),
    word(49, 8, "[ ]YES", F, "p45_flow_h22_yes", routes=(SEC_H,)),
    word(
        49, 8, "[ ]NO (GO TO H22", F, "p45_flow_h22_no_loop", routes=(SEC_H,)
    ),
    *paired(
        49,
        ("line", 14),
        "p45_h23_member_income_amount",
        anchor_kind=M,
        routes=(H22_YES,),
    ),
    *paired(
        49,
        ("block", 16, 18),
        "p45_h24_member_income_source",
        routes=(H22_YES,),
    ),
    word(
        49,
        16,
        "wages , a pension",
        M,
        "p45_h24_wage_pension_component",
        routes=(H22_YES,),
    ),
    word(
        49,
        16,
        "a business",
        BA,
        "p45_h24_business_aggregate",
        routes=(H22_YES,),
    ),
    line(
        49,
        20,
        F,
        "p45_flow_h24_wages_business",
        routes=(H22_YES,),
    ),
    *paired(
        49, ("block", 23, 24), "p45_h25_member_occupation", routes=(H24_WORK,)
    ),
    word(
        49,
        24,
        "(OCCUPATION)",
        J,
        "p45_job_member_occupation",
        routes=(H24_WORK,),
    ),
    *paired(
        49,
        ("block", 25, 27),
        "p45_h26_member_weeks",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(
        49,
        ("block", 29, 30),
        "p45_h27_member_hours",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(
        49,
        ("line", 32),
        "p45_h28_member_half_time",
        parents=("p45_job_member_occupation",),
        routes=(H24_WORK,),
        parent_note="H25's exact occupation label is the local job parent.",
    ),
    *paired(49, ("block", 36, 40), "p45_h29_other_income", routes=(H22_YES,)),
    word(49, 37, "[ ]YES", F, "p45_flow_h29_yes", routes=(H22_YES,)),
    word(
        49,
        36,
        "[ ]NO (GO TO H22",
        F,
        "p45_flow_h29_no_loop",
        routes=(H22_YES,),
    ),
    *paired(
        49, ("block", 45, 47), "p45_h30_other_income_source", routes=(H29_YES,)
    ),
    *paired(
        49,
        ("block", 49, 50),
        "p45_h31_other_income_amount",
        anchor_kind=M,
        routes=(H29_YES,),
    ),
)


PAGE_46 = (
    *paired(
        50,
        ("block", 5, 13),
        "p46_h21_member_listing_purpose",
        routes=(SEC_H,),
        note="H21 defines the complete repeated-person population, including movers.",
    ),
    *paired(
        50,
        ("line", 20),
        "p46_h23_amount_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    *paired(
        50,
        ("block", 23, 26),
        "p46_h24_source_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(50, 24, "odd jobs", J, "p46_job_odd_jobs", routes=(SEC_H,)),
    *paired(
        50, ("block", 29, 30), "p46_h25_occupation_purpose", routes=(SEC_H,)
    ),
    word(50, 29, "occupation", J, "p46_job_occupation", routes=(SEC_H,)),
    word(50, 30, "heads", R, "p46_role_heads", routes=(SEC_H,)),
    word(50, 30, "wives", R, "p46_role_wives", routes=(SEC_H,)),
    *paired(
        50,
        ("block", 33, 35),
        "p46_h26_h28_irregular_hours_purpose",
        parents=("p46_job_occupation",),
        routes=(SEC_H,),
        parent_note="The explanatory block explicitly applies to H25's occupation.",
    ),
    *paired(
        50,
        ("block", 38, 39),
        "p46_h29_h31_total_income_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


H22_GRID_YES = tuple(
    SEC_H + (f"p47_flow_h22_yes_{column}",) for column in range(1, 4)
)
H29_GRID_YES = tuple(
    H22_GRID_YES[column - 1] + (f"p47_flow_h29_yes_{column}",)
    for column in range(1, 4)
)


PAGE_47_RELATION = tuple(
    row
    for column in range(3)
    for row in (
        *paired(
            51,
            ("needle", 6, "RELATION TO HEAD", column),
            f"p47_relation_{column + 1}",
            routes=(SEC_H,),
        ),
        word(
            51,
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
        51,
        ("needle", 17, "(SOURCE)", column),
        f"p47_source_1_{column + 1}",
        routes=(H22_GRID_YES[column],),
    )
)

PAGE_47_FIRST_AMOUNT = tuple(
    row
    for column, selector in enumerate(
        (("bytes", 843, 881), ("bytes", 918, 927), ("bytes", 964, 971))
    )
    for row in paired(
        51,
        selector,
        f"p47_h23_amount_{column + 1}",
        anchor_kind=M,
        routes=(H22_GRID_YES[column],),
    )
)

PAGE_47_OCCUPATION = tuple(
    row
    for column in range(3)
    for row in (
        *paired(
            51,
            ("needle", 22, "(OCCUPATION)", column),
            f"p47_occupation_{column + 1}",
            routes=(H22_GRID_YES[column],),
        ),
        word(
            51,
            22,
            "(OCCUPATION)",
            J,
            f"p47_job_occupation_{column + 1}",
            occurrence=column,
            routes=(H22_GRID_YES[column],),
        ),
    )
)

PAGE_47_WEEKS = tuple(
    row
    for column in range(3)
    for row in paired(
        51,
        ("needle", 25, "(WEEKS)", column),
        f"p47_weeks_{column + 1}",
        parents=(f"p47_job_occupation_{column + 1}",),
        routes=(H22_GRID_YES[column],),
        parent_note="The same repeated column's occupation is the local job parent.",
    )
)

PAGE_47_HOURS = tuple(
    row
    for column in range(3)
    for row in paired(
        51,
        ("needle", 28, "(HOURS)", column),
        f"p47_hours_{column + 1}",
        parents=(f"p47_job_occupation_{column + 1}",),
        routes=(H22_GRID_YES[column],),
        parent_note="The same repeated column's occupation is the local job parent.",
    )
)

PAGE_47_SECOND_SOURCE = tuple(
    row
    for column in range(3)
    for row in paired(
        51,
        ("needle", 45, "(SOURCE)", column),
        f"p47_source_2_{column + 1}",
        routes=(H29_GRID_YES[column],),
    )
)

PAGE_47_SECOND_AMOUNT = tuple(
    row
    for column, selector in enumerate(
        (
            ("bytes", 2512, 2550),
            ("bytes", 2558, 2595),
            ("bytes", 2607, 2641),
        )
    )
    for row in paired(
        51,
        selector,
        f"p47_h31_amount_{column + 1}",
        anchor_kind=M,
        routes=(H29_GRID_YES[column],),
    )
)

PAGE_47 = (
    *PAGE_47_RELATION,
    word(
        51, 8, "[ ]YES", F, "p47_flow_h22_yes_1", occurrence=0, routes=(SEC_H,)
    ),
    word(
        51,
        8,
        "[ ]NO (GO TO H22",
        F,
        "p47_flow_h22_no_1",
        occurrence=0,
        routes=(SEC_H,),
    ),
    word(
        51, 8, "[ ]YES", F, "p47_flow_h22_yes_2", occurrence=1, routes=(SEC_H,)
    ),
    word(
        51,
        8,
        "[ ]NO (GO TO H22",
        F,
        "p47_flow_h22_no_2",
        occurrence=1,
        routes=(SEC_H,),
    ),
    word(
        51, 8, "[ ]YES", F, "p47_flow_h22_yes_3", occurrence=2, routes=(SEC_H,)
    ),
    word(51, 8, "[ ]NO (GO TO H:22", F, "p47_flow_h22_no_3", routes=(SEC_H,)),
    _unresolved_repeat(
        51,
        ("bytes", 330, 837),
        "p47_repeat_h22_next_person_block",
        "The exact continuous row-major block prints all three H22-NO loops "
        "and their FOR NEXT PERSON LISTED continuations.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    *PAGE_47_FIRST_AMOUNT,
    *PAGE_47_FIRST_SOURCE,
    *PAGE_47_OCCUPATION,
    *PAGE_47_WEEKS,
    *PAGE_47_HOURS,
    word(
        51,
        35,
        "_r YES",
        F,
        "p47_flow_h29_yes_1",
        routes=(H22_GRID_YES[0],),
    ),
    word(
        51,
        36,
        "[ ]NO (GO TO",
        F,
        "p47_flow_h29_no_1",
        routes=(H22_GRID_YES[0],),
    ),
    word(
        51,
        37,
        "[r ES",
        F,
        "p47_flow_h29_yes_2",
        routes=(H22_GRID_YES[1],),
    ),
    word(
        51,
        37,
        "[ ]NO (GO TO",
        F,
        "p47_flow_h29_no_2",
        routes=(H22_GRID_YES[1],),
    ),
    word(
        51,
        39,
        "[ ]YES",
        F,
        "p47_flow_h29_yes_3",
        routes=(H22_GRID_YES[2],),
    ),
    word(
        51,
        39,
        "[ ]NO (GO TO",
        F,
        "p47_flow_h29_no_3",
        routes=(H22_GRID_YES[2],),
    ),
    _unresolved_repeat(
        51,
        ("bytes", 1980, 2241),
        "p47_repeat_h29_to_h22_block",
        "The exact row-major two-line block prints all three H29-NO to H22 "
        "loops; no noncontiguous per-column instruction was reconstructed.",
        routes=H22_GRID_YES,
    ),
    *PAGE_47_SECOND_SOURCE,
    *PAGE_47_SECOND_AMOUNT,
    line(51, 54, F, "p47_flow_repeated_schedule_exit", routes=(SEC_H,)),
)


PAGE_48 = (
    _repeat_relation(
        52,
        ("block", 6, 8),
        "p48_repeat_previous_page",
        (
            "p47_relation_1",
            "p47_relation_2",
            "p47_relation_3",
            "p47_role_head_label_1",
            "p47_role_head_label_2",
            "p47_role_head_label_3",
            "p47_h23_amount_1",
            "p47_h23_amount_2",
            "p47_h23_amount_3",
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
            "p47_h31_amount_1",
            "p47_h31_amount_2",
            "p47_h31_amount_3",
        ),
        (
            "p45_h21_member_schedule",
            "p45_role_head_member_relation",
            "p45_h22_member_income",
            "p45_h23_member_income_amount",
            "p45_h24_member_income_source",
            "p45_h24_wage_pension_component",
            "p45_h24_business_aggregate",
            "p45_h25_member_occupation",
            "p45_job_member_occupation",
            "p45_h26_member_weeks",
            "p45_h27_member_hours",
            "p45_h28_member_half_time",
            "p45_h29_other_income",
            "p45_h30_other_income_source",
            "p45_h31_other_income_amount",
        ),
        "The page explicitly says it repeats the previous member schedule; "
        "every repeated relation, amount, source, occupation, weeks, and hours "
        "anchor is tied to its establishing H21-H31 anchor without collapsing "
        "coordinates.",
        routes=(SEC_H,),
    ),
)


PAGE_49_RELATION = tuple(
    row
    for column, selector in enumerate(
        (("bytes", 248, 264), ("bytes", 281, 297), ("bytes", 308, 324)),
        start=1,
    )
    for row in (
        *paired(
            53,
            selector,
            f"p49_h33_relation_{column}",
            routes=(H32_YES,),
            note="H33 prints a separate relation-to-head field for this additional member.",
        ),
        spec(
            53,
            R,
            selector,
            f"p49_role_head_label_{column}",
            routes=(H32_YES,),
        ),
    )
)


PAGE_49 = (
    *paired(53, ("block", 6, 7), "p49_h32_additional_income", routes=(SEC_H,)),
    word(53, 8, "(J YES", F, "p49_flow_h32_yes", routes=(SEC_H,)),
    tail(53, 8, "[] No", F, "p49_flow_h32_no_exit", routes=(SEC_H,)),
    *paired(
        53,
        ("line", 11),
        "p49_h33_additional_member_identity",
        routes=(H32_YES,),
    ),
    *PAGE_49_RELATION,
    *paired(
        53,
        ("block", 20, 21),
        "p49_h34_other_money",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
    word(53, 23, "11. YES I", F, "p49_flow_h34_yes", routes=(SEC_H,)),
    tail(53, 23, "~(GO TO H36)", F, "p49_flow_h34_no_exit", routes=(SEC_H,)),
    *paired(
        53,
        ("block", 25, 26),
        "p49_h35_other_money_amount",
        anchor_kind=M,
        routes=(H34_YES,),
    ),
)


PAGE_50 = (
    *paired(
        54,
        ("block", 6, 13),
        "p50_h34_h35_nonincome_money_purpose",
        anchor_kind=M,
        routes=(SEC_H,),
    ),
)


PAGE_51 = (
    tail(55, 33, "SECTION K:", F, "p51_flow_section_k"),
    word(
        55,
        38,
        "1 . FU HAS A NEW HEAD THIS YEAR",
        F,
        "p51_flow_k1_new_head",
        routes=(SEC_K,),
    ),
    word(
        55,
        38,
        "HEAD",
        R,
        "p51_role_new_head",
        routes=(K_NEW_HEAD,),
    ),
    from_word(
        55,
        38,
        "I 5 . THIS FU HAS THE SAME HEAD AS IN 19 73",
        39,
        F,
        "p51_flow_k1_same_head",
        routes=(SEC_K,),
    ),
)


PAGE_56 = (
    *paired(
        56,
        ("block", 33, 37),
        "p56_k1_new_head_route_purpose",
        routes=(SEC_K,),
        note="K1 defines the new-head checkpoint and same-head exit.",
    ),
    word(56, 34, "Head", R, "p56_role_new_head", routes=(SEC_K,)),
)


PAGE_53 = (
    *paired(
        57,
        ("line", 3),
        "p53_k3_father_occupation",
        parents=("p53_job_father_occupation",),
        routes=(K_NEW_HEAD,),
        parent_note="The exact father's-usual-occupation noun is its local job parent.",
    ),
    word(
        57,
        3,
        "father's usual occupation",
        J,
        "p53_job_father_occupation",
        routes=(K_NEW_HEAD,),
    ),
    *paired(
        57,
        ("line", 6),
        "p53_k4_first_job_occupation",
        parents=("p53_job_first_full_time",),
        routes=(K_NEW_HEAD,),
        parent_note=_FIRST_JOB_PARENT,
    ),
    word(
        57, 6, "(HEAD's)", R, "p53_role_head_first_job", routes=(K_NEW_HEAD,)
    ),
    word(
        57,
        6,
        "first full time regular job",
        J,
        "p53_job_first_full_time",
        routes=(K_NEW_HEAD,),
    ),
    from_word(
        57,
        9,
        "I 0. NEVER HORKED I",
        11,
        F,
        "p53_flow_k4_never",
        routes=(K_NEW_HEAD,),
    ),
    *paired(
        57,
        ("block", 13, 14),
        "p53_k5_job_history",
        parents=("p53_job_different_kinds",),
        routes=(K_NEW_HEAD,),
        parent_note="K5's exact different-kinds-of-jobs noun is the local history parent.",
    ),
    word(
        57,
        13,
        "different kinds of jobs",
        J,
        "p53_job_different_kinds",
        routes=(K_NEW_HEAD,),
    ),
    word(
        57,
        14,
        "same occupation you started in",
        J,
        "p53_job_starting_occupation",
        routes=(K_NEW_HEAD,),
    ),
)


PAGE_54 = (
    *paired(
        58,
        ("block", 5, 7),
        "p54_k3_father_scope",
        parents=("p53_job_father_occupation",),
        routes=(K_NEW_HEAD,),
        note="K3 defines which father supplies the retained father-occupation field.",
        parent_note="The scope prose applies directly to K3's father-occupation field.",
    ),
    *paired(
        58,
        ("block", 13, 17),
        "p54_k5_occupation_history_purpose",
        routes=(K_NEW_HEAD,),
    ),
    word(
        58,
        13,
        "occupations the head",
        J,
        "p54_job_head_occupations",
        routes=(K_NEW_HEAD,),
    ),
    word(58, 13, "head", R, "p54_role_head_history", routes=(K_NEW_HEAD,)),
    word(
        58, 15, "part-time jobs", J, "p54_job_part_time", routes=(K_NEW_HEAD,)
    ),
)


CROSS_REFERENCES = (
    _xref(
        18,
        ("line", 17),
        "p16_xref_d26_d27_to_d2_d3",
        ("p15_d26_occupation",),
        ("p9_d2_occupation",),
        "D25-D26 explicitly reuse the D2-D3 occupation instructions.",
        routes=(SEC_D,),
    ),
    _xref(
        22,
        ("block", 5, 6),
        "p20_xref_e1_to_d2_d3",
        ("p19_e1_sought_job",),
        ("p9_d2_occupation",),
        "E1 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        22,
        ("line", 29),
        "p20_xref_e6_to_d2_d3",
        ("p19_e6_last_job_occupation",),
        ("p9_d2_occupation",),
        "E6 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        22,
        ("line", 34),
        "p20_xref_e7_to_d4",
        ("p19_e7_last_job_industry",),
        ("p9_d4_industry",),
        "E6a explicitly applies the D3a industry objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        22,
        ("line", 39),
        "p20_xref_e8_to_d7",
        ("p19_e8_last_job_outcome",),
        ("p9_d7_previous_job_outcome",),
        "E6b explicitly applies the D6 prior-job outcome objectives.",
        routes=(SEC_E,),
    ),
    _xref(
        26,
        ("line", 16),
        "p24_xref_f3_to_d2_d3",
        ("p23_f3_occupation",),
        ("p9_d2_occupation",),
        "F3 explicitly applies the D2-D3 occupation objectives.",
        routes=(SEC_F,),
    ),
    _xref(
        26,
        ("line", 19),
        "p24_xref_f4_to_d4",
        ("p23_f4_industry",),
        ("p9_d4_industry",),
        "F3a explicitly applies the D3a industry objectives.",
        routes=(SEC_F,),
    ),
    _xref(
        30,
        ("block", 17, 18),
        "p26_xref_g3_g4_to_d2_d4",
        ("p25_g3_wife_occupation", "p25_g4_wife_industry"),
        ("p9_d2_occupation", "p9_d4_industry"),
        "The G3-G4 wife occupation/industry fields explicitly reuse D2-D3a.",
        routes=(G2_YES,),
    ),
    _xref(
        30,
        ("block", 21, 23),
        "p26_xref_g5_g6_to_e9_e10",
        ("p25_g6_wife_hours",),
        ("p19_e10_hours_worked",),
        "The exact G5-G6 instruction survives, but the G5 instrument prompt "
        "does not; only the locatable G6-to-E8 work-time endpoint is linked.",
        routes=(G2_YES,),
    ),
    _xref(
        30,
        ("line", 26),
        "p26_xref_g7_g8_to_d30_d31",
        ("p25_g7_wife_work_availability",),
        ("p15_d30_work_availability",),
        "G7-G8 explicitly reuse D30-D31; the retained G7-to-D30 availability "
        "endpoints form the exact document-local portion of that instruction. "
        "Preference items G8 and D31 remain outside the retained source scope.",
        routes=(G2_YES,),
    ),
    _unresolved_repeat(
        38,
        ("line", 10),
        "p34_xref_nonfarmer_farm_to_h11b",
        "The instruction reallocates nonfarmer farm income to H11b; it is "
        "allocation evidence rather than a proved aggregate alias.",
        relation=XREF,
        alias=("p33_farm_aggregate",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        38,
        ("block", 54, 55),
        "p34_xref_corporation_to_h11c",
        "The H6 objective explicitly directs incorporated-business owners to H11c.",
        relation=XREF,
        alias=("p34_corporation_aggregate",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        39,
        ("block", 25, 28),
        "p35_xref_business_wages_h7_h8",
        "The prose allocates businessman wages between H7 and H8 without proving alias identity.",
        relation=XREF,
        alias=("p35_businessman_wage_allocation",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        39,
        ("block", 30, 31),
        "p35_no_double_count_h7_h8",
        "The exact instruction prevents the H7 and H8 figures from being recorded twice.",
        alias=("p33_h7_business_share", "p33_h8_head_wages_total"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        42,
        ("block", 4, 6),
        "p38_no_separate_h9_h10_from_h8",
        "The exact instruction preserves prior inclusion of H9-H10 sources in H8.",
        alias=("p37_h9_bonus_overtime_commission", "p33_h8_head_wages_total"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        42,
        ("block", 28, 34),
        "p38_no_duplicate_h11b_h2_h4",
        "The H11b objective explicitly prevents duplication with H2-H4 farm income.",
        alias=("p38_h11b_farming_purpose", "p33_h4_net_farm_income"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        42,
        ("line", 43),
        "p38_xref_salary_to_h8",
        "The printed objective sends a small incorporated-business owner's "
        "salary to H8; this preserves the exact allocation instruction.",
        relation=XREF,
        alias=("p38_h11c_dividends_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        45,
        ("line", 24),
        "p41_no_double_count_h11k",
        "The exact H11k instruction forbids double counting without naming a unique endpoint.",
        alias=("p41_h11k_illegal_income_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        47,
        ("line", 5),
        "p43_xref_h14_to_h11d_h11e",
        "H14 explicitly refers to H11d and H11e; this is routing/allocation evidence.",
        relation=XREF,
        alias=("p37_h11d_adc_afdc", "p37_h11e_other_welfare"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        48,
        ("block", 17, 18),
        "p44_xref_welfare_food_stamps",
        "The welfare objective explicitly directs missed food stamps back to G23-G33.",
        relation=XREF,
        routes=(SEC_H,),
    ),
    _repeat_relation(
        48,
        ("block", 22, 27),
        "p44_wife_all_sources_instruction",
        ("p44_wife_all_sources_purpose",),
        ("p43_h20_wife_income_total",),
        "The exact instruction requires the wife's income from every source and "
        "preserves possible prior stock-income inclusion.",
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        48,
        ("block", 29, 31),
        "p44_no_duplicate_wife_business_h7",
        "The exact instruction prevents wife family-business income from duplicating H7.",
        alias=("p43_h20_wife_income_total", "p33_h7_business_share"),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        49,
        ("block", 2, 6),
        "p45_repeat_member_schedule",
        "H21 explicitly creates the repeated member-income schedule for every listed person.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        49,
        ("bytes", 463, 747),
        "p45_repeat_h22_next_person",
        "The exact H22-NO block includes its FOR NEXT PERSON LISTED continuation.",
        alias=("p45_h22_member_income",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        49,
        ("bytes", 1685, 2033),
        "p45_repeat_h29_next_person",
        "The exact H29-NO block includes its FOR NEXT PERSON LISTED continuation.",
        alias=("p45_h22_member_income",),
        routes=(H22_YES,),
    ),
    _repeat_relation(
        50,
        ("block", 5, 13),
        "p46_repeat_member_listing_instruction",
        ("p46_h21_member_listing_purpose",),
        ("p45_h21_member_schedule",),
        "The objective explicitly defines complete repeated-person coverage, including movers.",
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        50,
        ("block", 38, 39),
        "p46_xref_additional_member_income",
        "The H29-H31 objective explicitly adds these amounts to prior member income.",
        relation=XREF,
        alias=("p46_h29_h31_total_income_purpose",),
        routes=(SEC_H,),
    ),
    _unresolved_repeat(
        53,
        ("line", 15),
        "p49_repeat_additional_members_h22_h31",
        "H33 explicitly sends each additional member through the complete "
        "document-local H22-H31 schedule without equating identity fields to "
        "the repeated measurements.",
        alias=(
            "p45_h22_member_income",
            "p45_h23_member_income_amount",
            "p45_h24_member_income_source",
            "p45_h24_wage_pension_component",
            "p45_h24_business_aggregate",
            "p45_h25_member_occupation",
            "p45_job_member_occupation",
            "p45_h26_member_weeks",
            "p45_h27_member_hours",
            "p45_h28_member_half_time",
            "p45_h29_other_income",
            "p45_h30_other_income_source",
            "p45_h31_other_income_amount",
        ),
        routes=(H32_YES,),
    ),
    _xref(
        58,
        ("line", 9),
        "p54_xref_k4_to_d2_d3",
        ("p53_k4_first_job_occupation",),
        ("p9_d2_occupation",),
        "K4 explicitly reuses D2-D3 occupation instructions; the exact local "
        "component link is to the D2 occupation field.",
        routes=(K_NEW_HEAD,),
    ),
)


_BASE_REVIEW_ROWS: tuple[dict[str, Any], ...] = (
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
    *PAGE_56,
    *PAGE_53,
    *PAGE_54,
    *CROSS_REFERENCES,
)

PORT_COORDS: dict[str, tuple[int, int, int]] = {
    "p10_d_sequence_role_scope": (10, 309, 581),
    "p10_d_sequence_role_scope_prompt": (10, 309, 581),
    "p10_flow_looking_definition": (10, 1183, 1259),
    "p10_flow_out_of_labor_force_definition": (10, 1680, 1762),
    "p10_flow_working_definition": (10, 584, 660),
    "p10_looking_definition": (10, 1260, 1677),
    "p10_looking_definition_prompt": (10, 1260, 1677),
    "p10_out_of_labor_force_definition": (10, 1763, 2343),
    "p10_out_of_labor_force_definition_prompt": (10, 1763, 2343),
    "p10_role_head_scope": (10, 361, 382),
    "p10_working_definition": (10, 661, 1180),
    "p10_working_definition_prompt": (10, 661, 1180),
    "p11_d2_d3_role_scope": (11, 36, 102),
    "p11_d2_d3_role_scope_prompt": (11, 36, 102),
    "p11_d3_probe_purpose": (11, 1392, 1510),
    "p11_d3_probe_purpose_prompt": (11, 1392, 1510),
    "p11_d4_industry_purpose": (11, 1514, 2330),
    "p11_d4_industry_purpose_prompt": (11, 1514, 2330),
    "p11_d5_required_classification": (11, 1514, 1580),
    "p11_d5_required_classification_prompt": (11, 1514, 1580),
    "p11_job_particular_occupation": (11, 1654, 1675),
    "p11_job_title_precision_purpose": (11, 661, 991),
    "p11_job_title_precision_purpose_prompt": (11, 661, 991),
    "p11_job_titles": (11, 686, 696),
    "p11_job_white_collar_occupations": (11, 439, 464),
    "p11_occupation_place_purpose": (11, 465, 660),
    "p11_occupation_place_purpose_prompt": (11, 465, 660),
    "p11_occupation_skill_purpose": (11, 132, 342),
    "p11_occupation_skill_purpose_prompt": (11, 132, 342),
    "p11_role_head_scope": (11, 111, 130),
    "p11_role_head_workplace": (11, 510, 514),
    "p12_d6_employer_tenure_purpose": (12, 129, 295),
    "p12_d6_employer_tenure_purpose_prompt": (12, 129, 295),
    "p12_d7_previous_job_purpose": (12, 299, 682),
    "p12_d7_previous_job_purpose_prompt": (12, 299, 682),
    "p12_d8_d10_change_purpose": (12, 686, 797),
    "p12_d8_d10_change_purpose_prompt": (12, 686, 797),
    "p12_job_change": (12, 764, 771),
    "p12_job_first": (12, 606, 616),
    "p12_job_present_employer": (12, 167, 184),
    "p12_role_head_first_job": (12, 599, 605),
    "p13_job_main": (13, 906, 914),
    "p14_employment_year_accounting": (14, 37, 257),
    "p14_employment_year_accounting_prompt": (14, 37, 257),
    "p14_fixed_and_overtime_pay": (14, 1702, 2192),
    "p14_fixed_and_overtime_pay_prompt": (14, 1702, 2192),
    "p14_full_year_check": (14, 1180, 1316),
    "p14_full_year_check_prompt": (14, 1180, 1316),
    "p14_hourly_rate_check": (15, 39, 245),
    "p14_hourly_rate_check_prompt": (15, 39, 245),
    "p14_hourly_salary_basis": (15, 249, 407),
    "p14_hourly_salary_basis_prompt": (15, 249, 407),
    "p14_job_main_accounting": (14, 242, 250),
    "p14_job_main_overtime": (14, 1126, 1135),
    "p14_job_main_unemployment": (14, 1126, 1135),
    "p14_main_job_overtime_definition": (14, 1321, 1538),
    "p14_main_job_overtime_definition_prompt": (14, 1321, 1538),
    "p14_role_head_accounting": (14, 118, 124),
    "p14_role_head_income": (14, 1753, 1759),
    "p14_unemployment_definition": (14, 942, 1176),
    "p14_unemployment_definition_prompt": (14, 942, 1176),
    "p15_d25_extra_jobs": (17, 0, 112),
    "p15_d25_extra_jobs_prompt": (17, 0, 112),
    "p15_d26_occupation": (17, 303, 333),
    "p15_d26_occupation_prompt": (17, 303, 333),
    "p15_d27_anything_else_prompt": (17, 338, 366),
    "p15_d28_extra_hourly_rate": (17, 368, 456),
    "p15_d28_extra_hourly_rate_prompt": (17, 368, 456),
    "p15_d29_extra_weeks": (17, 458, 548),
    "p15_d29_extra_weeks_prompt": (17, 458, 548),
    "p15_d30_extra_hours": (17, 550, 641),
    "p15_d30_extra_hours_prompt": (17, 550, 641),
    "p15_d30_work_availability": (17, 646, 781),
    "p15_d30_work_availability_prompt": (17, 646, 781),
    "p15_flow_d30_no_exit": (17, 832, 857),
    "p15_flow_d30_yes_exit": (17, 791, 809),
    "p15_job_extra": (17, 25, 35),
    "p15_job_main_reference": (17, 95, 103),
    "p16_d25_extra_income_scope": (18, 205, 846),
    "p16_d25_extra_income_scope_prompt": (18, 205, 846),
    "p16_d25_job_boundary": (18, 35, 204),
    "p16_d25_job_boundary_prompt": (18, 35, 204),
    "p16_d28_hourly_pay_purpose": (18, 904, 1176),
    "p16_d28_hourly_pay_purpose_prompt": (18, 904, 1176),
    "p16_d29_d30_time_purpose": (18, 1180, 1463),
    "p16_d29_d30_time_purpose_prompt": (18, 1180, 1463),
    "p16_d30_availability_purpose": (18, 1467, 1752),
    "p16_d30_availability_purpose_prompt": (18, 1467, 1752),
    "p16_job_extra_rate": (18, 1130, 1140),
    "p16_job_irregular": (18, 258, 273),
    "p16_job_main_previous_phrase": (18, 2130, 2145),
    "p16_job_present_availability": (18, 1567, 1582),
    "p16_job_second": (18, 69, 80),
    "p16_role_head_availability": (18, 1514, 1518),
    "p16_role_head_current_employment": (18, 168, 174),
    "p16_xref_d26_d27_to_d2_d3": (18, 850, 900),
    "p17_d38_job_intention": (19, 524, 624),
    "p17_d38_job_intention_prompt": (19, 524, 624),
    "p17_job_current": (19, 608, 624),
    "p17_job_new": (19, 709, 716),
    "p18_d38_new_job_definition": (20, 930, 1036),
    "p18_d38_new_job_definition_prompt": (20, 930, 1036),
    "p18_job_different_employer": (20, 908, 927),
    "p18_job_new": (20, 938, 945),
    "p18_job_same_employer": (20, 964, 978),
    "p19_e10_hours_worked": (21, 1466, 1551),
    "p19_e10_hours_worked_prompt": (21, 1466, 1551),
    "p19_e11_sick_weeks": (21, 1554, 1599),
    "p19_e11_sick_weeks_prompt": (21, 1554, 1599),
    "p19_e12_unemployed_weeks": (21, 1677, 1764),
    "p19_e12_unemployed_weeks_prompt": (21, 1677, 1764),
    "p19_e1_sought_job": (21, 274, 366),
    "p19_e1_sought_job_prompt": (21, 274, 366),
    "p19_e2_expected_earnings": (21, 371, 438),
    "p19_e2_expected_earnings_prompt": (21, 371, 438),
    "p19_e3_training": (21, 441, 522),
    "p19_e3_training_prompt": (21, 441, 522),
    "p19_e4_search_action": (21, 527, 574),
    "p19_e4_search_action_prompt": (21, 527, 574),
    "p19_e5_search_places": (21, 661, 748),
    "p19_e5_search_places_prompt": (21, 661, 748),
    "p19_e6_last_job_occupation": (21, 840, 932),
    "p19_e6_last_job_occupation_prompt": (21, 840, 932),
    "p19_e7_last_job_industry": (21, 1143, 1190),
    "p19_e7_last_job_industry_prompt": (21, 1143, 1190),
    "p19_e8_last_job_outcome": (21, 1264, 1367),
    "p19_e8_last_job_outcome_prompt": (21, 1264, 1367),
    "p19_e9_weeks_worked": (21, 1372, 1463),
    "p19_e9_weeks_worked_prompt": (21, 1372, 1463),
    "p19_flow_e4_nothing": (21, 631, 658),
    "p19_flow_e9_none": (21, 1446, 1463),
    "p19_flow_section_e": (21, 21, 75),
    "p19_job_last": (21, 885, 894),
    "p19_job_sought": (21, 296, 299),
    "p20_e10_hours_purpose": (22, 1040, 1212),
    "p20_e10_hours_purpose_prompt": (22, 1040, 1212),
    "p20_e11_sick_purpose": (22, 1215, 1485),
    "p20_e11_sick_purpose_prompt": (22, 1215, 1485),
    "p20_e12_year_check": (22, 1488, 1628),
    "p20_e12_year_check_prompt": (22, 1488, 1628),
    "p20_e1_occupation_purpose": (22, 97, 271),
    "p20_e1_occupation_purpose_prompt": (22, 97, 271),
    "p20_e2_pay_period_purpose": (22, 274, 338),
    "p20_e2_pay_period_purpose_prompt": (22, 274, 338),
    "p20_e3_training_purpose": (22, 374, 542),
    "p20_e3_training_purpose_prompt": (22, 374, 542),
    "p20_e4_search_purpose": (22, 545, 687),
    "p20_e4_search_purpose_prompt": (22, 545, 687),
    "p20_e5_places_purpose": (22, 690, 813),
    "p20_e5_places_purpose_prompt": (22, 690, 813),
    "p20_e9_weeks_purpose": (22, 963, 1037),
    "p20_e9_weeks_purpose_prompt": (22, 963, 1037),
    "p20_role_head_schedule": (22, 1276, 1280),
    "p20_xref_e1_to_d2_d3": (22, 97, 271),
    "p20_xref_e6_to_d2_d3": (22, 816, 863),
    "p20_xref_e7_to_d4": (22, 866, 912),
    "p20_xref_e8_to_d7": (22, 915, 960),
    "p21_e17_jobs_not_worth_taking": (23, 843, 919),
    "p21_e17_jobs_not_worth_taking_prompt": (23, 843, 919),
    "p21_e18_unacceptable_pay": (23, 983, 1088),
    "p21_e18_unacceptable_pay_prompt": (23, 983, 1088),
    "p21_e19_good_job_mobility": (23, 1176, 1285),
    "p21_e19_good_job_mobility_prompt": (23, 1176, 1285),
    "p21_flow_e17_no_exit": (23, 962, 981),
    "p21_job_available": (23, 861, 875),
    "p21_job_good_mobility": (23, 1275, 1285),
    "p22_e17_e18_unacceptable_pay_purpose": (24, 889, 1144),
    "p22_e17_e18_unacceptable_pay_purpose_prompt": (24, 889, 1144),
    "p22_e20_pay_period_purpose": (24, 1273, 1476),
    "p22_e20_pay_period_purpose_prompt": (24, 1273, 1476),
    "p22_job_jobs_in_area": (24, 1031, 1100),
    "p23_f10_training": (25, 1295, 1359),
    "p23_f10_training_prompt": (25, 1295, 1359),
    "p23_f11_search_action": (25, 1361, 1417),
    "p23_f11_search_action_prompt": (25, 1361, 1417),
    "p23_f12_search_places": (25, 1518, 1632),
    "p23_f12_search_places_prompt": (25, 1518, 1632),
    "p23_f13_jobs_not_worth_taking": (25, 1735, 1809),
    "p23_f13_jobs_not_worth_taking_prompt": (25, 1735, 1809),
    "p23_f14_unacceptable_pay": (25, 1892, 1976),
    "p23_f14_unacceptable_pay_prompt": (25, 1892, 1976),
    "p23_f1_work_for_money": (25, 92, 169),
    "p23_f1_work_for_money_prompt": (25, 92, 169),
    "p23_f2_future_work": (25, 173, 250),
    "p23_f2_future_work_prompt": (25, 173, 250),
    "p23_f3_occupation": (25, 554, 645),
    "p23_f3_occupation_prompt": (25, 554, 645),
    "p23_f4_industry": (25, 649, 705),
    "p23_f4_industry_prompt": (25, 649, 705),
    "p23_f5_weeks_worked": (25, 709, 765),
    "p23_f5_weeks_worked_prompt": (25, 709, 765),
    "p23_f6_hours_worked": (25, 767, 844),
    "p23_f6_hours_worked_prompt": (25, 767, 844),
    "p23_f7_new_job": (25, 846, 925),
    "p23_f7_new_job_prompt": (25, 846, 925),
    "p23_f8_job_in_mind": (25, 1050, 1105),
    "p23_f8_job_in_mind_prompt": (25, 1050, 1105),
    "p23_f9_expected_earnings": (25, 1209, 1293),
    "p23_f9_expected_earnings_prompt": (25, 1209, 1293),
    "p23_flow_f11_nothing": (25, 1490, 1516),
    "p23_flow_f13_no_exit": (25, 1860, 1890),
    "p23_flow_f2_no_exit": (25, 320, 350),
    "p23_flow_f2_or_f7": (25, 1011, 1048),
    "p23_flow_f2_yes": (25, 293, 299),
    "p23_flow_f7_no_exit": (25, 979, 1009),
    "p23_flow_f7_yes": (25, 1652, 1668),
    "p23_flow_section_f": (25, 21, 89),
    "p23_job_actual_occupation": (25, 633, 645),
    "p23_job_in_mind": (25, 1081, 1105),
    "p23_job_jobs_around_here": (25, 1762, 1778),
    "p23_job_new": (25, 894, 901),
    "p23_job_work_for_money": (25, 154, 169),
    "p23_role_head_f1": (25, 140, 146),
    "p24_f10_training_purpose": (26, 1373, 1553),
    "p24_f10_training_purpose_prompt": (26, 1373, 1553),
    "p24_f11_search_purpose": (26, 1556, 1705),
    "p24_f11_search_purpose_prompt": (26, 1556, 1705),
    "p24_f12_places_purpose": (27, 41, 160),
    "p24_f12_places_purpose_prompt": (27, 41, 160),
    "p24_f13_f14_unacceptable_pay_purpose": (27, 164, 355),
    "p24_f13_f14_unacceptable_pay_purpose_prompt": (27, 164, 355),
    "p24_f1_money_work_purpose": (26, 113, 341),
    "p24_f1_money_work_purpose_prompt": (26, 113, 341),
    "p24_f2_work_timing_purpose": (26, 345, 490),
    "p24_f2_work_timing_purpose_prompt": (26, 345, 490),
    "p24_f5_f6_hours_purpose": (26, 602, 906),
    "p24_f5_f6_hours_purpose_prompt": (26, 602, 906),
    "p24_f7_new_job_definition": (26, 910, 1113),
    "p24_f7_new_job_definition_prompt": (26, 910, 1113),
    "p24_f8_job_in_mind_purpose": (26, 1117, 1288),
    "p24_f8_job_in_mind_purpose_prompt": (26, 1117, 1288),
    "p24_f9_pay_period_purpose": (26, 1292, 1369),
    "p24_f9_pay_period_purpose_prompt": (26, 1292, 1369),
    "p24_job_full_time_prior": (26, 216, 229),
    "p24_job_in_mind": (26, 1254, 1264),
    "p24_job_jobs_around_here": (27, 309, 325),
    "p24_job_new": (26, 925, 934),
    "p24_job_same_employer": (26, 974, 988),
    "p24_role_heads_f1": (26, 137, 143),
    "p24_role_heads_hours": (26, 782, 789),
    "p24_xref_f3_to_d2_d3": (26, 494, 545),
    "p24_xref_f4_to_d4": (26, 548, 598),
    "p25_flow_g1_married": (29, 201, 209),
    "p25_flow_g1_nonwife_exit": (29, 255, 406),
    "p25_flow_g2_no": (29, 640, 695),
    "p25_flow_g7_yes_exit": (29, 1281, 1291),
    "p25_flow_section_g": (29, 144, 169),
    "p25_flow_wife_occupation_scope": (29, 407, 451),
    "p25_g1_marital_status": (29, 187, 253),
    "p25_g1_marital_status_prompt": (29, 187, 253),
    "p25_g2_wife_work_for_money": (29, 554, 604),
    "p25_g2_wife_work_for_money_prompt": (29, 554, 604),
    "p25_g3_wife_occupation": (29, 861, 906),
    "p25_g3_wife_occupation_prompt": (29, 861, 906),
    "p25_g4_wife_industry": (29, 910, 965),
    "p25_g4_wife_industry_prompt": (29, 910, 965),
    "p25_g6_wife_hours": (29, 1066, 1127),
    "p25_g6_wife_hours_prompt": (29, 1066, 1127),
    "p25_g7_wife_work_availability": (29, 1129, 1263),
    "p25_g7_wife_work_availability_prompt": (29, 1129, 1263),
    "p25_job_wife_work": (29, 581, 595),
    "p25_role_wife_g2": (29, 569, 573),
    "p25_role_wife_scope": (29, 433, 439),
    "p26_g10_wife_new_job_context": (30, 863, 1004),
    "p26_g10_wife_new_job_context_prompt": (30, 863, 1004),
    "p26_g1_female_head_context": (30, 345, 521),
    "p26_g1_female_head_context_prompt": (30, 345, 521),
    "p26_job_wife_new": (30, 922, 927),
    "p26_role_female_head": (30, 380, 391),
    "p26_role_wife_new_job": (30, 686, 690),
    "p26_xref_g3_g4_to_d2_d4": (30, 524, 584),
    "p26_xref_g5_g6_to_e9_e10": (30, 589, 800),
    "p26_xref_g7_g8_to_d30_d31": (30, 802, 858),
    "p33_business_aggregate": (37, 1468, 1492),
    "p33_business_interest_aggregate": (37, 1255, 1265),
    "p33_farm_aggregate": (37, 1141, 1164),
    "p33_farm_classification_aggregate": (37, 439, 457),
    "p33_farming_aggregate": (37, 524, 531),
    "p33_flow_h1_farmer": (37, 437, 457),
    "p33_flow_h1_not_farmer": (37, 430, 470),
    "p33_flow_h5_no_exit": (37, 1399, 1417),
    "p33_flow_h6_dont_know": (37, 1572, 1589),
    "p33_flow_section_h": (37, 151, 171),
    "p33_h1_farmer_classification": (37, 333, 470),
    "p33_h1_farmer_classification_prompt": (37, 333, 470),
    "p33_h2_farm_receipts": (37, 475, 733),
    "p33_h2_farm_receipts_prompt": (37, 475, 733),
    "p33_h3_farm_expenses": (37, 843, 1111),
    "p33_h3_farm_expenses_prompt": (37, 843, 1111),
    "p33_h4_net_farm_income": (37, 1112, 1216),
    "p33_h4_net_farm_income_prompt": (37, 1112, 1216),
    "p33_h5_business_interest": (37, 1220, 1351),
    "p33_h5_business_interest_prompt": (37, 1220, 1351),
    "p33_h6_business_form": (37, 1429, 1548),
    "p33_h6_business_form_prompt": (37, 1429, 1548),
    "p33_h7_business_share": (37, 1629, 1799),
    "p33_h7_business_share_prompt": (37, 1629, 1799),
    "p33_h8_head_wages_total": (37, 1845, 1993),
    "p33_h8_head_wages_total_prompt": (37, 1845, 1993),
    "p33_h8_wages_component": (37, 1890, 1911),
    "p33_income_preamble": (37, 189, 330),
    "p33_income_preamble_prompt": (37, 189, 330),
    "p33_role_head_h8": (37, 1870, 1876),
    "p34_business_aggregate": (38, 1769, 1783),
    "p34_corporation_aggregate": (38, 377, 388),
    "p34_farm_income_aggregate": (38, 1511, 1522),
    "p34_farmer_aggregate": (38, 39, 47),
    "p34_h1_farmer_definition": (38, 34, 238),
    "p34_h1_farmer_definition_prompt": (38, 34, 238),
    "p34_h2_receipts_purpose": (38, 303, 792),
    "p34_h2_receipts_purpose_prompt": (38, 303, 792),
    "p34_h3_expenses_purpose": (38, 942, 1501),
    "p34_h3_expenses_purpose_prompt": (38, 942, 1501),
    "p34_h4_net_income_purpose": (38, 1506, 1678),
    "p34_h4_net_income_purpose_prompt": (38, 1506, 1678),
    "p34_h5_business_purpose": (38, 1682, 1969),
    "p34_h5_business_purpose_prompt": (38, 1682, 1969),
    "p34_h6_corporation_purpose": (38, 1682, 1877),
    "p34_h6_corporation_purpose_prompt": (38, 1682, 1877),
    "p34_xref_corporation_to_h11c": (38, 1570, 1634),
    "p34_xref_nonfarmer_farm_to_h11b": (38, 239, 299),
    "p35_business_aggregate": (39, 365, 377),
    "p35_businessman_wage_allocation": (39, 1513, 1809),
    "p35_businessman_wage_allocation_prompt": (39, 1513, 1809),
    "p35_complicated_history_purpose": (39, 1316, 1511),
    "p35_complicated_history_purpose_prompt": (39, 1316, 1511),
    "p35_fixed_salary_purpose": (39, 909, 1314),
    "p35_fixed_salary_purpose_prompt": (39, 909, 1314),
    "p35_h7_business_profit_purpose": (39, 311, 699),
    "p35_h7_business_profit_purpose_prompt": (39, 311, 699),
    "p35_h8_head_total_purpose": (39, 703, 907),
    "p35_h8_head_total_purpose_prompt": (39, 703, 907),
    "p35_job_other": (39, 1753, 1767),
    "p35_job_second": (39, 876, 886),
    "p35_job_several": (39, 1374, 1381),
    "p35_no_double_count_h7_h8": (39, 1812, 1994),
    "p35_role_head_total": (39, 742, 762),
    "p35_role_wife_business": (39, 565, 569),
    "p35_unincorporated_business_aggregate": (39, 1599, 1616),
    "p35_xref_business_wages_h7_h8": (39, 1513, 1809),
    "p37_farming_market_aggregate": (41, 452, 480),
    "p37_flow_h12_no_exit": (41, 2037, 2065),
    "p37_flow_h12_yes": (41, 2012, 2018),
    "p37_flow_h9_no": (41, 149, 166),
    "p37_h10_amount": (41, 171, 229),
    "p37_h10_amount_prompt": (41, 171, 229),
    "p37_h11_other_income_header": (41, 233, 296),
    "p37_h11_other_income_header_prompt": (41, 233, 296),
    "p37_h11a_professional_trade": (41, 329, 363),
    "p37_h11a_professional_trade_prompt": (41, 329, 363),
    "p37_h11b_farming_roomers": (41, 418, 622),
    "p37_h11b_farming_roomers_prompt": (41, 418, 622),
    "p37_h11c_dividend_interest_rent": (41, 652, 802),
    "p37_h11c_dividend_interest_rent_prompt": (41, 652, 802),
    "p37_h11d_adc_afdc": (41, 824, 913),
    "p37_h11d_adc_afdc_prompt": (41, 824, 913),
    "p37_h11e_other_welfare": (41, 914, 1007),
    "p37_h11e_other_welfare_prompt": (41, 914, 1007),
    "p37_h11f_social_security": (41, 1009, 1099),
    "p37_h11f_social_security_prompt": (41, 1009, 1099),
    "p37_h11g_retirement_pension_annuity": (41, 1100, 1250),
    "p37_h11g_retirement_pension_annuity_prompt": (41, 1100, 1250),
    "p37_h11h_unemployment_workmens_comp": (41, 1251, 1491),
    "p37_h11h_unemployment_workmens_comp_prompt": (41, 1251, 1491),
    "p37_h11i_alimony_child_support": (41, 1492, 1583),
    "p37_h11i_alimony_child_support_prompt": (41, 1492, 1583),
    "p37_h11j_relatives": (41, 1585, 1680),
    "p37_h11j_relatives_prompt": (41, 1585, 1680),
    "p37_h11k_other": (41, 1682, 1839),
    "p37_h11k_other_prompt": (41, 1682, 1839),
    "p37_h12_outside_help": (41, 1842, 1998),
    "p37_h12_outside_help_prompt": (41, 1842, 1998),
    "p37_h13_outside_help_amount": (41, 2081, 2154),
    "p37_h13_outside_help_amount_prompt": (41, 2081, 2154),
    "p37_h9_bonus_overtime_commission": (41, 3, 110),
    "p37_h9_bonus_overtime_commission_prompt": (41, 3, 110),
    "p37_role_head_h11": (41, 251, 257),
    "p38_farming_market_aggregate": (42, 1415, 1444),
    "p38_h11_periodicity_purpose": (42, 243, 755),
    "p38_h11_periodicity_purpose_prompt": (42, 243, 755),
    "p38_h11a_professional_trade_purpose": (42, 759, 1399),
    "p38_h11a_professional_trade_purpose_prompt": (42, 759, 1399),
    "p38_h11b_farming_purpose": (42, 1614, 1866),
    "p38_h11b_farming_purpose_prompt": (42, 1614, 1866),
    "p38_h11b_roomers_purpose": (42, 1869, 2115),
    "p38_h11b_roomers_purpose_prompt": (42, 1869, 2115),
    "p38_h11c_dividends_purpose": (43, 0, 453),
    "p38_h11c_dividends_purpose_prompt": (43, 0, 453),
    "p38_h11c_interest_purpose": (43, 721, 991),
    "p38_h11c_interest_purpose_prompt": (43, 721, 991),
    "p38_h11c_rent_purpose": (43, 994, 1412),
    "p38_h11c_rent_purpose_prompt": (43, 994, 1412),
    "p38_incorporated_business_aggregate": (43, 237, 261),
    "p38_no_duplicate_h11b_h2_h4": (42, 1614, 1866),
    "p38_no_separate_h9_h10_from_h8": (42, 41, 239),
    "p38_self_employed_aggregate": (42, 928, 950),
    "p39_h11c_royalty_purpose": (43, 1674, 1956),
    "p39_h11c_royalty_purpose_prompt": (43, 1674, 1956),
    "p39_h11c_trust_purpose": (43, 1415, 1671),
    "p39_h11c_trust_purpose_prompt": (43, 1415, 1671),
    "p39_h11d_adc_afdc_purpose": (43, 1564, 2704),
    "p39_h11d_adc_afdc_purpose_prompt": (43, 1564, 2704),
    "p39_h11e_other_welfare_purpose": (44, 37, 1267),
    "p39_h11e_other_welfare_purpose_prompt": (44, 37, 1267),
    "p39_h11f_social_security_start": (44, 1369, 1640),
    "p39_h11f_social_security_start_prompt": (44, 1369, 1640),
    "p40_h11f_social_security_continued": (44, 1572, 2453),
    "p40_h11f_social_security_continued_prompt": (44, 1572, 2453),
    "p40_h11g_pension_annuity_purpose": (45, 198, 1307),
    "p40_h11g_pension_annuity_purpose_prompt": (45, 198, 1307),
    "p40_h11g_retirement_pay_purpose": (45, 35, 196),
    "p40_h11g_retirement_pay_purpose_prompt": (45, 35, 196),
    "p40_h11h_unemployment_comp_purpose": (45, 1311, 1953),
    "p40_h11h_unemployment_comp_purpose_prompt": (45, 1311, 1953),
    "p40_h11h_workmens_comp_purpose": (45, 1955, 2367),
    "p40_h11h_workmens_comp_purpose_prompt": (45, 1955, 2367),
    "p40_job_injury_source": (45, 2204, 2212),
    "p40_job_previous_employers": (45, 232, 254),
    "p40_self_employed_aggregate": (45, 169, 196),
    "p41_h11i_alimony_support_purpose": (45, 2412, 2690),
    "p41_h11i_alimony_support_purpose_prompt": (45, 2412, 2690),
    "p41_h11j_relative_help_purpose": (46, 38, 239),
    "p41_h11j_relative_help_purpose_prompt": (46, 38, 239),
    "p41_h11k_illegal_income_purpose": (46, 567, 694),
    "p41_h11k_illegal_income_purpose_prompt": (46, 567, 694),
    "p41_h11k_training_allowance_purpose": (46, 243, 565),
    "p41_h11k_training_allowance_purpose_prompt": (46, 243, 565),
    "p41_h12_h13_family_help_purpose": (46, 755, 952),
    "p41_h12_h13_family_help_purpose_prompt": (46, 755, 952),
    "p41_no_double_count_h11k": (46, 696, 750),
    "p43_flow_h14_no_exit": (47, 225, 253),
    "p43_flow_h14_welfare": (47, 175, 224),
    "p43_flow_h15_no_exit": (47, 420, 437),
    "p43_flow_h15_yes": (47, 400, 419),
    "p43_flow_h17_no_wife": (47, 704, 766),
    "p43_flow_h17_wife": (47, 677, 703),
    "p43_flow_h18_no_exit": (47, 942, 972),
    "p43_flow_h18_yes": (47, 919, 941),
    "p43_h15_non_cash_welfare": (47, 265, 379),
    "p43_h15_non_cash_welfare_prompt": (47, 265, 379),
    "p43_h16_welfare_amount": (47, 455, 610),
    "p43_h16_welfare_amount_prompt": (47, 455, 610),
    "p43_h17_wife_checkpoint": (47, 612, 664),
    "p43_h17_wife_checkpoint_prompt": (47, 612, 664),
    "p43_h18_wife_income": (47, 844, 903),
    "p43_h18_wife_income_prompt": (47, 844, 903),
    "p43_h19_business_aggregate": (47, 1031, 1042),
    "p43_h19_wage_salary_component": (47, 1016, 1030),
    "p43_h19_wife_income_source": (47, 974, 1051),
    "p43_h19_wife_income_source_prompt": (47, 974, 1051),
    "p43_h20_wife_income_total": (47, 1125, 1297),
    "p43_h20_wife_income_total_prompt": (47, 1125, 1297),
    "p43_role_head_h17": (47, 735, 739),
    "p43_role_wife_h17": (47, 707, 711),
    "p43_role_wife_h18": (47, 707, 711),
    "p43_xref_h14_to_h11d_h11e": (47, 98, 162),
    "p44_family_business_aggregate": (48, 1378, 1442),
    "p44_h14_h16_welfare_purpose": (48, 106, 931),
    "p44_h14_h16_welfare_purpose_prompt": (48, 106, 931),
    "p44_no_duplicate_wife_business_h7": (48, 1309, 1527),
    "p44_role_wife_all_income": (48, 963, 976),
    "p44_role_wife_business_income": (48, 1344, 1357),
    "p44_wife_all_sources_purpose": (48, 936, 1307),
    "p44_wife_all_sources_purpose_prompt": (48, 936, 1307),
    "p44_wife_all_sources_instruction": (48, 936, 1307),
    "p44_xref_welfare_food_stamps": (48, 810, 1006),
    "p45_flow_h21_no_people_exit": (49, 297, 387),
    "p45_flow_h22_no_loop": (49, 463, 479),
    "p45_flow_h22_yes": (49, 451, 457),
    "p45_flow_h24_wages_business": (49, 996, 1024),
    "p45_flow_h29_no_loop": (49, 1685, 1701),
    "p45_flow_h29_yes": (49, 1673, 1679),
    "p45_h21_member_schedule": (49, 58, 387),
    "p45_h21_member_schedule_prompt": (49, 58, 387),
    "p45_role_head_member_relation": (49, 359, 375),
    "p45_h22_member_income": (49, 389, 657),
    "p45_h22_member_income_prompt": (49, 389, 657),
    "p45_h23_member_income_amount": (49, 748, 831),
    "p45_h23_member_income_amount_prompt": (49, 748, 831),
    "p45_h24_business_aggregate": (49, 878, 888),
    "p45_h24_member_income_source": (49, 833, 994),
    "p45_h24_member_income_source_prompt": (49, 833, 994),
    "p45_h24_wage_pension_component": (49, 860, 877),
    "p45_h25_member_occupation": (49, 1121, 1249),
    "p45_h25_member_occupation_prompt": (49, 1121, 1249),
    "p45_h26_member_weeks": (49, 1250, 1412),
    "p45_h26_member_weeks_prompt": (49, 1250, 1412),
    "p45_h27_member_hours": (49, 1414, 1545),
    "p45_h27_member_hours_prompt": (49, 1414, 1545),
    "p45_h28_member_half_time": (49, 1547, 1606),
    "p45_h28_member_half_time_prompt": (49, 1547, 1606),
    "p45_h29_other_income": (49, 1610, 2033),
    "p45_h29_other_income_prompt": (49, 1610, 2033),
    "p45_h30_other_income_source": (49, 2035, 2148),
    "p45_h30_other_income_source_prompt": (49, 2035, 2148),
    "p45_h31_other_income_amount": (49, 2150, 2239),
    "p45_h31_other_income_amount_prompt": (49, 2150, 2239),
    "p45_job_member_occupation": (49, 1237, 1249),
    "p45_repeat_h22_next_person": (49, 463, 747),
    "p45_repeat_h29_next_person": (49, 1685, 2033),
    "p45_repeat_member_schedule": (49, 58, 387),
    "p46_h23_amount_purpose": (50, 849, 892),
    "p46_h23_amount_purpose_prompt": (50, 849, 892),
    "p46_h21_member_listing_purpose": (50, 40, 727),
    "p46_h21_member_listing_purpose_prompt": (50, 40, 727),
    "p46_h24_source_purpose": (50, 895, 1221),
    "p46_h24_source_purpose_prompt": (50, 895, 1221),
    "p46_h25_occupation_purpose": (50, 1224, 1333),
    "p46_h25_occupation_purpose_prompt": (50, 1224, 1333),
    "p46_h26_h28_irregular_hours_purpose": (50, 1336, 1549),
    "p46_h26_h28_irregular_hours_purpose_prompt": (50, 1336, 1549),
    "p46_h29_h31_total_income_purpose": (50, 1552, 1728),
    "p46_h29_h31_total_income_purpose_prompt": (50, 1552, 1728),
    "p46_job_occupation": (50, 1238, 1248),
    "p46_job_odd_jobs": (50, 993, 1002),
    "p46_repeat_member_listing_instruction": (50, 40, 727),
    "p46_role_heads": (50, 1317, 1322),
    "p46_role_wives": (50, 1327, 1333),
    "p46_xref_additional_member_income": (50, 1552, 1728),
    "p47_flow_h22_no_1": (51, 330, 346),
    "p47_flow_h22_no_2": (51, 375, 391),
    "p47_flow_h22_no_3": (51, 423, 439),
    "p47_flow_h22_yes_1": (51, 310, 316),
    "p47_flow_h22_yes_2": (51, 356, 362),
    "p47_flow_h22_yes_3": (51, 405, 411),
    "p47_flow_h29_no_1": (51, 2003, 2015),
    "p47_flow_h29_no_2": (51, 2003, 2015),
    "p47_flow_h29_no_3": (51, 2049, 2076),
    "p47_flow_h29_yes_1": (51, 2013, 2032),
    "p47_flow_h29_yes_2": (51, 2013, 2032),
    "p47_flow_h29_yes_3": (51, 2077, 2097),
    "p47_flow_repeated_schedule_exit": (51, 2785, 2857),
    "p47_hours_1": (51, 1859, 1883),
    "p47_hours_1_prompt": (51, 1859, 1883),
    "p47_hours_2": (51, 1859, 1883),
    "p47_hours_2_prompt": (51, 1859, 1883),
    "p47_hours_3": (51, 1859, 1883),
    "p47_hours_3_prompt": (51, 1859, 1883),
    "p47_job_occupation_1": (51, 1405, 1417),
    "p47_job_occupation_2": (51, 1405, 1417),
    "p47_job_occupation_3": (51, 1405, 1417),
    "p47_occupation_1": (51, 1405, 1417),
    "p47_occupation_1_prompt": (51, 1405, 1417),
    "p47_occupation_2": (51, 1405, 1417),
    "p47_occupation_2_prompt": (51, 1405, 1417),
    "p47_occupation_3": (51, 1405, 1417),
    "p47_occupation_3_prompt": (51, 1405, 1417),
    "p47_relation_1": (51, 157, 173),
    "p47_relation_1_prompt": (51, 157, 173),
    "p47_relation_2": (51, 203, 219),
    "p47_relation_2_prompt": (51, 203, 219),
    "p47_relation_3": (51, 252, 268),
    "p47_relation_3_prompt": (51, 252, 268),
    "p47_repeat_h22_next_person_block": (51, 330, 837),
    "p47_role_head_label_1": (51, 157, 173),
    "p47_role_head_label_2": (51, 203, 219),
    "p47_role_head_label_3": (51, 252, 268),
    "p47_source_1_1": (51, 1043, 1051),
    "p47_source_1_1_prompt": (51, 1043, 1051),
    "p47_source_1_2": (51, 1088, 1096),
    "p47_source_1_2_prompt": (51, 1088, 1096),
    "p47_source_1_3": (51, 1088, 1096),
    "p47_source_1_3_prompt": (51, 1088, 1096),
    "p47_source_2_1": (51, 2404, 2412),
    "p47_source_2_1_prompt": (51, 2404, 2412),
    "p47_source_2_2": (51, 2404, 2412),
    "p47_source_2_2_prompt": (51, 2404, 2412),
    "p47_source_2_3": (51, 2453, 2461),
    "p47_source_2_3_prompt": (51, 2453, 2461),
    "p47_weeks_1": (51, 1747, 1754),
    "p47_weeks_1_prompt": (51, 1747, 1754),
    "p47_weeks_2": (51, 1747, 1754),
    "p47_weeks_2_prompt": (51, 1747, 1754),
    "p47_weeks_3": (51, 1747, 1754),
    "p47_weeks_3_prompt": (51, 1747, 1754),
    "p48_repeat_previous_page": (52, 30, 169),
    "p49_flow_h32_no_exit": (53, 180, 196),
    "p49_flow_h32_yes": (53, 152, 158),
    "p49_flow_h34_no_exit": (53, 595, 606),
    "p49_flow_h34_yes": (53, 851, 859),
    "p49_h32_additional_income": (53, 26, 139),
    "p49_h32_additional_income_prompt": (53, 26, 139),
    "p49_h33_additional_member_identity": (53, 199, 233),
    "p49_h33_additional_member_identity_prompt": (53, 199, 233),
    "p49_h33_relation_1": (53, 248, 264),
    "p49_h33_relation_1_prompt": (53, 248, 264),
    "p49_h33_relation_2": (53, 281, 297),
    "p49_h33_relation_2_prompt": (53, 281, 297),
    "p49_h33_relation_3": (53, 308, 324),
    "p49_h33_relation_3_prompt": (53, 308, 324),
    "p49_role_head_label_1": (53, 248, 264),
    "p49_role_head_label_2": (53, 281, 297),
    "p49_role_head_label_3": (53, 308, 324),
    "p49_h34_other_money": (53, 418, 547),
    "p49_h34_other_money_prompt": (53, 418, 547),
    "p49_h35_other_money_amount": (53, 622, 764),
    "p49_h35_other_money_amount_prompt": (53, 622, 764),
    "p49_repeat_additional_members_h22_h31": (53, 331, 414),
    "p50_h34_h35_nonincome_money_purpose": (54, 39, 642),
    "p50_h34_h35_nonincome_money_purpose_prompt": (54, 39, 642),
    "p51_flow_k1_new_head": (55, 1261, 1291),
    "p51_flow_k1_same_head": (55, 1252, 1434),
    "p51_flow_section_k": (55, 1189, 1212),
    "p51_role_new_head": (55, 1277, 1281),
    "p53_flow_k4_never": (57, 430, 633),
    "p53_job_different_kinds": (57, 672, 696),
    "p53_job_father_occupation": (57, 145, 166),
    "p53_job_first_full_time": (57, 358, 386),
    "p53_job_starting_occupation": (57, 742, 773),
    "p53_k3_father_occupation": (57, 119, 192),
    "p53_k3_father_occupation_prompt": (57, 119, 192),
    "p53_k4_first_job_occupation": (57, 316, 429),
    "p53_k4_first_job_occupation_prompt": (57, 316, 429),
    "p53_k5_job_history": (57, 635, 782),
    "p53_k5_job_history_prompt": (57, 635, 782),
    "p53_role_head_first_job": (57, 349, 357),
    "p54_job_head_occupations": (58, 330, 351),
    "p54_job_part_time": (58, 502, 516),
    "p54_k3_father_scope": (58, 60, 224),
    "p54_k3_father_scope_prompt": (58, 60, 224),
    "p54_k5_occupation_history_purpose": (58, 280, 675),
    "p54_k5_occupation_history_purpose_prompt": (58, 280, 675),
    "p54_role_head_history": (58, 347, 351),
    "p54_xref_k4_to_d2_d3": (58, 227, 275),
    "p9_d10_comparison_reason": (9, 2428, 2457),
    "p9_d10_comparison_reason_prompt": (9, 2428, 2457),
    "p9_d1_employment_status": (9, 59, 203),
    "p9_d1_employment_status_prompt": (9, 59, 203),
    "p9_d2_occupation": (9, 1120, 1198),
    "p9_d2_occupation_prompt": (9, 1120, 1198),
    "p9_d3_occupation_detail": (9, 1379, 1461),
    "p9_d3_occupation_detail_prompt": (9, 1379, 1461),
    "p9_d4_industry": (9, 1466, 1510),
    "p9_d4_industry_prompt": (9, 1466, 1510),
    "p9_d5_employee_self": (9, 1514, 1574),
    "p9_d5_employee_self_prompt": (9, 1514, 1574),
    "p9_d6_job_tenure": (9, 1663, 1706),
    "p9_d6_job_tenure_prompt": (9, 1663, 1706),
    "p9_d7_previous_job_outcome": (9, 1913, 2024),
    "p9_d7_previous_job_outcome_prompt": (9, 1913, 2024),
    "p9_d8_relative_pay": (9, 2029, 2098),
    "p9_d8_relative_pay_prompt": (9, 2029, 2098),
    "p9_d9_job_comparison": (9, 2152, 2266),
    "p9_d9_job_comparison_prompt": (9, 2152, 2266),
    "p9_flow_d1_disabled": (9, 459, 491),
    "p9_flow_d1_housewife": (9, 655, 669),
    "p9_flow_d1_looking_exit": (9, 378, 398),
    "p9_flow_d1_other": (9, 743, 1119),
    "p9_flow_d1_student": (9, 730, 742),
    "p9_flow_d3_probe": (9, 1392, 1420),
    "p9_flow_d6_long": (9, 1794, 1880),
    "p9_flow_d6_short": (9, 1882, 1911),
    "p9_flow_d9_same_exit": (9, 2322, 2369),
    "p9_flow_d9_worse": (9, 2221, 2226),
    "p9_flow_section_d": (9, 32, 57),
    "p9_job_main_occupation": (9, 1145, 1161),
    "p9_job_present": (9, 2049, 2060),
    "p9_job_previous": (9, 1940, 1964),
    "p9_job_tenure_noun": (9, 1697, 1706),
    "p9_role_head_d1": (9, 129, 135),
}

PORT_COORDS.update(
    {
        "p9_job_present": (9, 107, 118),
        "p9_job_main_occupation": (9, 1145, 1160),
        "p9_job_tenure_noun": (9, 1697, 1705),
        "p9_job_previous": (9, 1940, 1962),
        "p9_flow_d1_working": (9, 212, 226),
        "p9_flow_d1_looking_exit": (9, 237, 256),
        "p9_flow_d1_retired": (9, 266, 276),
        "p9_flow_d1_disabled": (9, 459, 484),
        "p9_flow_d1_other": (9, 801, 811),
        "p9_flow_d1_other_has_job": (9, 824, 925),
        "p9_flow_d1_other_no_job_exit": (9, 927, 1119),
        "p9_flow_d3_probe": (9, 1392, 1406),
        "p9_d3_occupation_detail": (9, 1417, 1461),
        "p9_d3_occupation_detail_prompt": (9, 1417, 1461),
        "p9_flow_d9_better": (9, 2279, 2291),
        "p9_flow_d9_worse": (9, 2298, 2310),
        "p9_flow_d9_same_exit": (9, 2322, 2353),
        "p11_d5_required_classification": (12, 39, 126),
        "p11_d5_required_classification_prompt": (12, 39, 126),
        "p11_d2_d3_role_scope": (11, 36, 130),
        "p11_d2_d3_role_scope_prompt": (11, 36, 130),
        "p11_occupation_skill_purpose": (11, 132, 464),
        "p11_occupation_skill_purpose_prompt": (11, 132, 464),
        "p11_job_title_precision_purpose": (11, 661, 1391),
        "p11_job_title_precision_purpose_prompt": (11, 661, 1391),
        "p11_d4_industry_purpose": (11, 1514, 2788),
        "p11_d4_industry_purpose_prompt": (11, 1514, 2788),
        "p11_role_head_scope": (11, 111, 129),
        "p11_job_white_collar_occupations": (11, 439, 463),
        "p12_job_change": (12, 748, 771),
        "p12_job_present_employer": (12, 167, 183),
        "p12_job_first": (12, 606, 615),
        "p13_d10_vacation_presence": (13, 104, 150),
        "p13_d10_vacation_presence_prompt": (13, 104, 150),
        "p13_flow_d10_yes": (13, 159, 167),
        "p13_flow_d10_no_exit": (13, 223, 243),
        "p13_d11_vacation_duration": (13, 178, 214),
        "p13_d11_vacation_duration_prompt": (13, 178, 214),
        "p13_d12_sick_absence_presence": (13, 312, 427),
        "p13_d12_sick_absence_presence_prompt": (13, 312, 427),
        "p13_flow_d12_yes": (13, 436, 444),
        "p13_flow_d12_no_exit": (13, 590, 609),
        "p13_d13_sick_absence_duration": (13, 455, 487),
        "p13_d13_sick_absence_duration_prompt": (13, 455, 487),
        "p13_d14_unemployment_strike": (13, 612, 691),
        "p13_d14_unemployment_strike_prompt": (13, 612, 691),
        "p13_flow_d14_yes": (13, 700, 708),
        "p13_flow_d14_no_exit": (13, 760, 779),
        "p13_d15_unemployment_duration": (13, 719, 751),
        "p13_d15_unemployment_duration_prompt": (13, 719, 751),
        "p13_d16_weeks_main_job": (13, 848, 923),
        "p13_d16_weeks_main_job_prompt": (13, 848, 923),
        "p13_d17_hours_main_job": (13, 1025, 1121),
        "p13_d17_hours_main_job_prompt": (13, 1025, 1121),
        "p13_d18_overtime_presence": (13, 1124, 1187),
        "p13_d18_overtime_presence_prompt": (13, 1124, 1187),
        "p13_d18_overtime_component": (13, 1148, 1156),
        "p13_flow_d18_yes": (13, 1197, 1204),
        "p13_flow_d18_no_exit": (13, 1222, 1240),
        "p13_d19_overtime_hours": (13, 1253, 1317),
        "p13_d19_overtime_hours_prompt": (13, 1253, 1317),
        "p13_d20_extra_hours_pay": (13, 1404, 1527),
        "p13_d20_extra_hours_pay_prompt": (13, 1404, 1527),
        "p13_d21_overtime_rate": (13, 1540, 1575),
        "p13_d21_overtime_rate_prompt": (13, 1540, 1575),
        "p13_d22_hourly_status": (13, 1582, 1618),
        "p13_d22_hourly_status_prompt": (13, 1582, 1618),
        "p13_flow_d22_yes": (13, 1755, 1764),
        "p13_flow_d22_no_exit": (13, 1770, 1775),
        "p13_d23_regular_hourly_rate": (13, 1893, 1986),
        "p13_d23_regular_hourly_rate_prompt": (13, 1893, 1986),
        "p14_job_main_overtime": (14, 1371, 1379),
        "p14_job_main_unemployment": (14, 1126, 1134),
        "p14_employment_year_accounting": (14, 37, 331),
        "p14_employment_year_accounting_prompt": (14, 37, 331),
        "p14_d10_d11_vacation_purpose": (14, 336, 659),
        "p14_d10_d11_vacation_purpose_prompt": (14, 336, 659),
        "p14_d12_d13_sick_leave_purpose": (14, 663, 938),
        "p14_d12_d13_sick_leave_purpose_prompt": (14, 663, 938),
        "p14_main_job_overtime_definition": (14, 1321, 1698),
        "p14_main_job_overtime_definition_prompt": (14, 1321, 1698),
        "p15_flow_d24_yes": (17, 123, 131),
        "p15_flow_d24_no_exit": (17, 150, 170),
        "p15_d27_anything_else": (17, 338, 366),
        "p16_job_irregular": (18, 258, 272),
        "p16_job_extra_rate": (18, 1130, 1139),
        "p16_job_present_availability": (18, 1567, 1581),
        "p18_job_same_employer": (20, 964, 977),
        "p19_job_last": (21, 885, 893),
        "p16_job_main_previous_phrase": (18, 116, 128),
        "p17_job_current": (19, 600, 623),
        "p18_job_different_employer": (20, 981, 1005),
        "p19_e9_weeks_worked": (21, 1373, 1416),
        "p19_e9_weeks_worked_prompt": (21, 1373, 1416),
        "p19_flow_e9_none": (21, 1442, 1463),
        "p20_e2_pay_period_purpose": (22, 274, 371),
        "p20_e2_pay_period_purpose_prompt": (22, 274, 371),
        "p20_role_head_schedule": (22, 1058, 1064),
        "p21_e11_work_checkpoint": (23, 110, 164),
        "p21_e11_work_checkpoint_prompt": (23, 110, 164),
        "p21_flow_e11_worked": (23, 173, 191),
        "p21_flow_e11_not_worked": (23, 208, 245),
        "p21_e17_jobs_not_worth_taking": (23, 843, 920),
        "p21_e17_jobs_not_worth_taking_prompt": (23, 843, 920),
        "p21_flow_e15_yes": (23, 929, 940),
        "p21_flow_e15_no": (23, 960, 981),
        "p21_e18_unacceptable_pay": (23, 983, 1088),
        "p21_e18_unacceptable_pay_prompt": (23, 983, 1088),
        "p21_e19_good_job_mobility": (23, 1176, 1285),
        "p21_e19_good_job_mobility_prompt": (23, 1176, 1285),
        "p21_flow_e17_yes": (23, 1297, 1323),
        "p21_flow_e17_no_exit": (23, 1396, 1402),
        "p21_e18_required_pay_start_prompt": (23, 1502, 1532),
        "p21_e18_required_pay_finish": (23, 1580, 1634),
        "p21_e18_required_pay_finish_prompt": (23, 1580, 1634),
        "p21_job_good_mobility": (23, 1275, 1284),
        "p20_xref_e1_to_d2_d3": (22, 214, 271),
        "p23_flow_f2_yes": (25, 293, 314),
        "p23_flow_f2_no_exit": (25, 320, 350),
        "p23_flow_f7_yes": (25, 946, 967),
        "p23_flow_f7_no_exit": (25, 979, 1009),
        "p23_flow_f2_or_f7": (25, 1025, 1048),
        "p23_job_in_mind": (25, 1081, 1104),
        "p23_job_jobs_around_here": (25, 1762, 1778),
        "p23_job_work_for_money": (25, 154, 168),
        "p24_job_in_mind": (26, 1254, 1287),
        "p24_role_heads_f1": (26, 137, 142),
        "p24_role_heads_hours": (26, 784, 789),
        "p24_job_same_employer": (26, 974, 987),
        "p22_job_jobs_in_area": (24, 1040, 1056),
        "p25_flow_g1_married": (29, 261, 275),
        "p25_flow_g1_single": (29, 284, 296),
        "p25_flow_g1_other": (29, 306, 322),
        "p25_flow_g1_nonwife_exit": (29, 384, 406),
        "p25_flow_g2_yes": (29, 612, 617),
        "p25_flow_g2_no": (29, 640, 660),
        "p25_flow_g7_yes_exit": (29, 1281, 1364),
        "p26_g10_wife_new_job_context": (30, 863, 1066),
        "p26_g10_wife_new_job_context_prompt": (30, 863, 1066),
        "p26_role_wife_new_job": (30, 879, 883),
        "p25_g9_wife_work_checkpoint": (29, 1655, 1690),
        "p25_g9_wife_work_checkpoint_prompt": (29, 1655, 1690),
        "p25_flow_g9_wife_not_working": (29, 1700, 1744),
        "p25_flow_g9_all_others_exit": (29, 1761, 1797),
        "p25_g10_wife_future_work": (29, 1817, 1944),
        "p25_g10_wife_future_work_prompt": (29, 1817, 1944),
        "p25_role_wife_g10": (29, 1888, 1892),
        "p25_flow_g10_yes": (29, 1962, 1972),
        "p25_flow_g10_depends": (29, 1985, 1995),
        "p25_flow_g10_no": (29, 2011, 2017),
        "p33_flow_h1_farmer": (37, 385, 429),
        "p33_farm_classification_aggregate": (37, 385, 429),
        "p33_flow_h1_not_farmer": (37, 430, 470),
        "p33_flow_h5_yes": (37, 1361, 1368),
        "p33_flow_h5_no_exit": (37, 1397, 1417),
        "p33_flow_h6_dont_know": (37, 1572, 1589),
        "p33_business_aggregate": (37, 1468, 1491),
        "p34_business_aggregate": (38, 1771, 1783),
        "p34_h2_receipts_purpose": (38, 303, 938),
        "p34_h2_receipts_purpose_prompt": (38, 303, 938),
        "p34_h6_corporation_purpose": (39, 36, 307),
        "p34_h6_corporation_purpose_prompt": (39, 36, 307),
        "p34_corporation_aggregate": (39, 166, 177),
        "p34_xref_corporation_to_h11c": (39, 236, 307),
        "p35_job_several": (39, 1374, 1402),
        "p35_role_head_total": (39, 742, 761),
        "p35_unincorporated_business_aggregate": (39, 1571, 1616),
        "p37_farming_market_aggregate": (41, 452, 479),
        "p38_self_employed_aggregate": (42, 928, 949),
        "p38_farming_market_aggregate": (42, 1417, 1444),
        "p38_h11b_farming_purpose": (42, 1403, 1866),
        "p38_h11b_farming_purpose_prompt": (42, 1403, 1866),
        "p38_no_duplicate_h11b_h2_h4": (42, 1403, 1866),
        "p38_h11c_dividends_purpose": (43, 47, 719),
        "p38_h11c_dividends_purpose_prompt": (43, 47, 719),
        "p38_xref_salary_to_h8": (43, 237, 338),
        "p39_h11d_adc_afdc_purpose": (43, 1960, 3050),
        "p39_h11d_adc_afdc_purpose_prompt": (43, 1960, 3050),
        "p39_h11e_other_welfare_purpose": (44, 37, 1366),
        "p39_h11e_other_welfare_purpose_prompt": (44, 37, 1366),
        "p39_h11f_social_security_start": (44, 1369, 1641),
        "p39_h11f_social_security_start_prompt": (44, 1369, 1641),
        "p40_h11f_social_security_continued": (44, 1641, 2508),
        "p40_h11f_social_security_continued_prompt": (44, 1641, 2508),
        "p40_self_employed_aggregate": (45, 1885, 1898),
        "p40_h11h_workmens_comp_purpose": (45, 1955, 2410),
        "p40_h11h_workmens_comp_purpose_prompt": (45, 1955, 2410),
        "p43_flow_h14_welfare": (47, 171, 209),
        "p43_flow_h14_no_exit": (47, 221, 253),
        "p43_flow_h15_yes": (47, 396, 403),
        "p43_flow_h15_no_exit": (47, 416, 437),
        "p43_role_head_h17": (47, 642, 646),
        "p43_role_wife_h17": (47, 652, 657),
        "p43_flow_h17_wife": (47, 673, 693),
        "p43_flow_h17_no_wife": (47, 700, 766),
        "p43_role_wife_h18": (47, 868, 874),
        "p43_flow_h18_yes": (47, 919, 927),
        "p43_flow_h18_no_exit": (47, 938, 972),
        "p43_h19_wage_salary_component": (47, 1016, 1029),
        "p43_h19_business_aggregate": (47, 1031, 1041),
        "p44_h14_h16_welfare_purpose": (48, 37, 931),
        "p44_h14_h16_welfare_purpose_prompt": (48, 37, 931),
        "p44_family_business_aggregate": (48, 1392, 1407),
        "p45_flow_h21_no_people_exit": (49, 278, 325),
        "p45_h24_wage_pension_component": (49, 860, 876),
        "p46_role_wives": (50, 1327, 1332),
        "p47_h23_amount_1": (51, 843, 881),
        "p47_h23_amount_1_prompt": (51, 843, 881),
        "p47_h23_amount_2": (51, 918, 927),
        "p47_h23_amount_2_prompt": (51, 918, 927),
        "p47_h23_amount_3": (51, 964, 971),
        "p47_h23_amount_3_prompt": (51, 964, 971),
        "p47_source_1_1": (51, 993, 1001),
        "p47_source_1_1_prompt": (51, 993, 1001),
        "p47_source_1_2": (51, 1043, 1051),
        "p47_source_1_2_prompt": (51, 1043, 1051),
        "p47_source_1_3": (51, 1088, 1096),
        "p47_source_1_3_prompt": (51, 1088, 1096),
        "p47_occupation_1": (51, 1313, 1325),
        "p47_occupation_1_prompt": (51, 1313, 1325),
        "p47_job_occupation_1": (51, 1313, 1325),
        "p47_occupation_2": (51, 1356, 1371),
        "p47_occupation_2_prompt": (51, 1356, 1371),
        "p47_job_occupation_2": (51, 1356, 1371),
        "p47_occupation_3": (51, 1405, 1417),
        "p47_occupation_3_prompt": (51, 1405, 1417),
        "p47_job_occupation_3": (51, 1405, 1417),
        "p47_weeks_1": (51, 1747, 1754),
        "p47_weeks_1_prompt": (51, 1747, 1754),
        "p47_weeks_2": (51, 1791, 1798),
        "p47_weeks_2_prompt": (51, 1791, 1798),
        "p47_weeks_3": (51, 1835, 1842),
        "p47_weeks_3_prompt": (51, 1835, 1842),
        "p47_hours_1": (51, 1874, 1882),
        "p47_hours_1_prompt": (51, 1874, 1882),
        "p47_hours_2": (51, 1919, 1926),
        "p47_hours_2_prompt": (51, 1919, 1926),
        "p47_hours_3": (51, 1964, 1971),
        "p47_hours_3_prompt": (51, 1964, 1971),
        "p47_flow_h29_yes_1": (51, 1980, 1986),
        "p47_flow_h29_no_1": (51, 2003, 2008),
        "p47_flow_h29_yes_2": (51, 2026, 2032),
        "p47_flow_h29_no_2": (51, 2047, 2052),
        "p47_flow_h29_yes_3": (51, 2075, 2081),
        "p47_flow_h29_no_3": (51, 2096, 2101),
        "p47_repeat_h29_to_h22_block": (51, 1980, 2241),
        "p47_source_2_1": (51, 2404, 2412),
        "p47_source_2_1_prompt": (51, 2404, 2412),
        "p47_source_2_2": (51, 2453, 2461),
        "p47_source_2_2_prompt": (51, 2453, 2461),
        "p47_source_2_3": (51, 2498, 2506),
        "p47_source_2_3_prompt": (51, 2498, 2506),
        "p47_h31_amount_1": (51, 2512, 2550),
        "p47_h31_amount_1_prompt": (51, 2512, 2550),
        "p47_h31_amount_2": (51, 2558, 2595),
        "p47_h31_amount_2_prompt": (51, 2558, 2595),
        "p47_h31_amount_3": (51, 2607, 2641),
        "p47_h31_amount_3_prompt": (51, 2607, 2641),
        "p47_flow_repeated_schedule_exit": (51, 2835, 2857),
        "p49_flow_h34_yes": (53, 563, 569),
        "p49_flow_h34_no_exit": (53, 586, 606),
        "p51_flow_section_k": (55, 1189, 1212),
        "p51_flow_k1_new_head": (55, 1261, 1291),
        "p51_flow_k1_same_head": (55, 1303, 1434),
        "p56_k1_new_head_route_purpose": (56, 656, 974),
        "p56_k1_new_head_route_purpose_prompt": (56, 656, 974),
        "p56_role_new_head": (56, 727, 731),
        "p53_flow_k4_never": (57, 506, 633),
        "p53_job_first_full_time": (57, 358, 385),
        "p53_job_different_kinds": (57, 672, 695),
        "p53_job_starting_occupation": (57, 742, 772),
        "p54_job_part_time": (58, 502, 516),
    }
)

OMITTED_KEYS = {
    # The adjacent-wave welfare/food-stamp instruction is absent from page 48.
    "p44_xref_welfare_food_stamps",
    # Generic income-source examples do not establish local source jobs.
    "p40_job_previous_employers",
    "p40_job_injury_source",
    "p40_self_employed_aggregate",
    "p46_job_odd_jobs",
}

REVIEW_ROWS: tuple[dict[str, Any], ...] = tuple(
    {
        **row,
        "page": PORT_COORDS[row["key"]][0],
        "selector": (
            "bytes",
            PORT_COORDS[row["key"]][1],
            PORT_COORDS[row["key"]][2],
        ),
    }
    for row in _BASE_REVIEW_ROWS
    if row["key"] in PORT_COORDS and row["key"] not in OMITTED_KEYS
)


def _validate_scope() -> None:
    if set(PAGE_NOTES) != set(range(1, PAGE_COUNT + 1)):
        raise SpecError("page review notes do not cover every page")
    base_keys = [row["key"] for row in _BASE_REVIEW_ROWS]
    if (
        len(base_keys) != len(set(base_keys))
        or set(PORT_COORDS) != set(base_keys)
        or not OMITTED_KEYS <= set(base_keys)
    ):
        raise SpecError(
            "source-row, exact-coordinate, or omission domain drift"
        )
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
            "whole_page_review": "all_68_pages_including_empty_occurrence_pages",
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
        f"document 11 source review: {len(review['occurrence_specs'])} "
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
