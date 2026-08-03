#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 27.

``fam1981_QxQs.pdf`` is a 122-page scan that interleaves the printed 1981
family instrument with its question-by-question interviewer objectives.  Every
page was read from the authenticated Poppler text before this file was
written, and the stage-1 candidate artifact is never opened here: the sealed
annotation builder joins candidates only after these reviewer rows exist.

Reviewer scope decisions recorded by this file:

* Occurrences are emitted only on printed *instrument* pages inside the
  retained employment, work-income, and lifetime-work-history regions.  The
  question-by-question objective pages are interviewer commentary keyed to a
  question; they restate worklike vocabulary but print no field, so they carry
  no source occurrence.
* Cover, thumbnail, transportation, housing/utilities, housework/food,
  food-stamp, other-FU-member, child-income, union/health, medical, dependent
  support, schooling, growing-up, and religion regions contribute no
  occurrence merely because nearby prose contains worklike words.
* A retained ``context_anchor`` must print a field that maps to a ratified
  §19 field purpose (assignment, occupation, industry, employee/self,
  government level, incorporation, job identifier, reporting unit, or
  month/exposure).  Union membership, commuting, health, and schooling fields
  are printed work-adjacent questions that map to no such purpose and are
  rejected.
* A retained ``job_anchor`` establishes a distinct job for the role.  Later
  references to an already-established job inside the same section are
  rejected rather than promoted to a second job or an inferred alias.
* OCR-destroyed answer labels and routing fragments are never reconstructed.
  A routing atom is retained only where the printed bytes still read as a
  directive.
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
import build_rq_stage2_document_025_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 114


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


def resolve(page_text: str, selector: Sequence[Any]) -> tuple[int, int]:
    mode = selector[0]
    if mode == "line":
        return resolve_line(page_text, selector[1])
    if mode == "block":
        return resolve_block(page_text, selector[1], selector[2])
    if mode == "needle":
        return resolve_needle(page_text, selector[1], selector[2], selector[3])
    raise SpecError(f"unknown selector mode {mode!r}")


_INSTRUMENT_OUT = (
    "Printed instrument screen for {}; read line by line and outside the "
    "R_Q employment, work-income, and work-history domain, so its worklike "
    "vocabulary retains no source occurrence."
)
_OBJECTIVES = (
    "Question-by-question interviewer objectives for {}; commentary keyed to "
    "printed questions rather than printed fields, so no source occurrence "
    "is retained."
)
_INSTRUMENT_IN = (
    "Printed instrument screen for {}; read line by line and retained as "
    "source for the R_Q occurrence domain."
)

_INSTRUMENT_NONE = (
    "Printed instrument screen for {}; read line by line inside the retained "
    "employment region, but every printed field is {}, so no source "
    "occurrence is retained."
)

PAGE_NOTES: dict[int, str] = {
    1: _INSTRUMENT_OUT.format("the interviewer face sheet and office-use box"),
    2: _OBJECTIVES.format("face-sheet items 1-7b"),
    3: _INSTRUMENT_OUT.format("the thumbnail sketch TN1-TN6"),
    4: _OBJECTIVES.format("thumbnail items TN1-TN6"),
    5: _INSTRUMENT_OUT.format("section A transportation A1-A9"),
    6: _OBJECTIVES.format("transportation items A1-A9"),
    7: _INSTRUMENT_OUT.format("section B housing B1-B13"),
    8: _OBJECTIVES.format("housing items B1-B13"),
    9: _INSTRUMENT_OUT.format("housing and utility items B14-B21"),
    10: _OBJECTIVES.format("housing and utility items B14-B20"),
    11: _INSTRUMENT_OUT.format("utility items B22-B30"),
    12: _OBJECTIVES.format("utility items B24-B30"),
    13: _INSTRUMENT_OUT.format("utility and moving items B31-B39"),
    14: _OBJECTIVES.format("utility and moving items B31-B39"),
    15: _INSTRUMENT_IN.format("section C employment of head, items C1-C6"),
    16: _OBJECTIVES.format("employment items C1-C6"),
    17: _INSTRUMENT_IN.format(
        "the first scan of head occupation, industry, and pay items C7-C17"
    ),
    18: _OBJECTIVES.format("occupation and industry items C7-C9"),
    19: _INSTRUMENT_IN.format(
        "the second scan of head occupation, industry, and pay items C7-C17"
    ),
    20: _OBJECTIVES.format("pay items C10-C17"),
    21: _INSTRUMENT_IN.format("head job-change items C18-C26"),
    22: _OBJECTIVES.format("job-change items C18-C26"),
    23: _INSTRUMENT_IN.format(
        "the first scan of head work-time items C27-C38b"
    ),
    24: _OBJECTIVES.format("work-time items C27-C37"),
    25: _INSTRUMENT_IN.format(
        "the second scan of head work-time items C27-C38b"
    ),
    26: _OBJECTIVES.format("work-time items C37-C39"),
    27: _INSTRUMENT_IN.format("head overtime and extra-job items C40-C48"),
    28: _OBJECTIVES.format("overtime and extra-job items C40-C48"),
    29: _INSTRUMENT_IN.format("head unemployment-spell items C49-C57"),
    30: _OBJECTIVES.format("unemployment-spell items C48-C57"),
    31: _INSTRUMENT_IN.format("head unemployment-spell items C58-C69"),
    32: _OBJECTIVES.format("unemployment-spell items C58-C67"),
    33: _INSTRUMENT_NONE.format(
        "head unemployment-benefit and return-to-work items C70-C79",
        "an unemployment-compensation transfer, a non-labor income probe, or "
        "an OCR-destroyed line",
    ),
    34: _OBJECTIVES.format("unemployment-benefit items C70-C79"),
    35: _INSTRUMENT_NONE.format(
        "the ask-everyone hours-constraint and commuting items C80-C89",
        "a counterfactual labor-supply preference or a commuting field that "
        "maps to no ratified purpose",
    ),
    36: _OBJECTIVES.format("hours-constraint and commuting items C80-C89"),
    37: _INSTRUMENT_IN.format("head job-search and retirement items C90-C95"),
    38: _OBJECTIVES.format("job-search and retirement items C90-C95"),
    39: _INSTRUMENT_IN.format("section D head looking for work, items D1-D12"),
    40: _OBJECTIVES.format("section D items D1-D12"),
    41: _INSTRUMENT_IN.format("head work-time items D13-D24b"),
    42: _OBJECTIVES.format("work-time items D13-D25"),
    43: _INSTRUMENT_IN.format("head unemployment-spell items D26-D35"),
    44: _OBJECTIVES.format("unemployment-spell items D26-D35"),
    45: _INSTRUMENT_IN.format("head unemployment-spell items D36-D48"),
    46: _OBJECTIVES.format("unemployment-spell items D36-D45"),
    47: _INSTRUMENT_NONE.format(
        "head unemployment-benefit and return-to-work items D48-D57",
        "an unemployment-compensation transfer, a non-labor income probe, or "
        "an OCR-destroyed line",
    ),
    48: _OBJECTIVES.format("unemployment-benefit items D48-D57"),
    49: _INSTRUMENT_IN.format(
        "head last-job commuting and retirement items D58-D65"
    ),
    50: _OBJECTIVES.format("last-job commuting items D58-D61"),
    51: _INSTRUMENT_IN.format(
        "section E head retired or out of the labor force, items E1-E15"
    ),
    52: _OBJECTIVES.format("section E items E1-E15"),
    53: _INSTRUMENT_IN.format(
        "section F employment of wife/friend, items F1-F7"
    ),
    54: _OBJECTIVES.format("section F items F1-F7"),
    55: _INSTRUMENT_IN.format(
        "wife occupation, industry, pay, and position items F8-F18"
    ),
    56: _OBJECTIVES.format("wife occupation and pay items F8-F18"),
    57: _INSTRUMENT_IN.format("wife work-time items F19-F30b"),
    58: _OBJECTIVES.format("wife work-time items F19-F31"),
    59: _INSTRUMENT_IN.format(
        "wife overtime, extra-job, and commuting items F32-F40"
    ),
    60: _OBJECTIVES.format("wife overtime and commuting items F32-F40"),
    61: _INSTRUMENT_IN.format("section G wife looking for work, items G1-G9"),
    62: _OBJECTIVES.format("section G items G1-G9"),
    63: _INSTRUMENT_IN.format("wife work-time items G10-G22"),
    64: _OBJECTIVES.format("wife work-time items G10-G22"),
    65: _INSTRUMENT_NONE.format(
        "wife last-job commuting items G23-G26",
        "a commuting field that maps to no ratified purpose",
    ),
    66: _OBJECTIVES.format("wife last-job commuting items G24-G26"),
    67: _INSTRUMENT_IN.format(
        "section H wife retired or out of the labor force, items H1-H12"
    ),
    68: _OBJECTIVES.format("section H items H1-H12"),
    69: _INSTRUMENT_OUT.format(
        "section J marital status and housework items J1-J8"
    ),
    70: _OBJECTIVES.format("housework items J1-J8"),
    71: _INSTRUMENT_OUT.format(
        "the first scan of housework-helper and food items J9-J22"
    ),
    72: _OBJECTIVES.format("food items J9-J18"),
    73: _INSTRUMENT_OUT.format(
        "the second scan of housework-helper and food items J9-J22"
    ),
    74: _OBJECTIVES.format("food items J19-J22"),
    75: _INSTRUMENT_OUT.format("food-stamp items J23-J30"),
    76: _OBJECTIVES.format("food-stamp items J23-J30"),
    77: _INSTRUMENT_IN.format(
        "the first scan of section K income items K1-K10"
    ),
    78: _OBJECTIVES.format("income items K1-K6"),
    79: _INSTRUMENT_IN.format(
        "the second scan of section K income items K1-K10"
    ),
    80: _OBJECTIVES.format("income items K7-K10"),
    81: _INSTRUMENT_IN.format(
        "the first scan of the other-income grid K11a-K11f"
    ),
    82: _OBJECTIVES.format("other-income items K11a-K11f"),
    83: _INSTRUMENT_IN.format(
        "the second scan of the other-income grid K11a-K11f"
    ),
    84: _OBJECTIVES.format("welfare items K11e-K11f"),
    85: _INSTRUMENT_OUT.format(
        "the first scan of the transfer-income grid K14a-K18"
    ),
    86: _OBJECTIVES.format("transfer-income items K14a-K14h"),
    87: _INSTRUMENT_OUT.format(
        "the second scan of the transfer-income grid K14a-K18"
    ),
    88: _OBJECTIVES.format("transfer-income items K14j-K18"),
    89: _INSTRUMENT_IN.format("wife income items K19-K29"),
    90: _OBJECTIVES.format("wife income items K19-K29"),
    91: _INSTRUMENT_OUT.format("the other-FU-member listing grid K30-K31"),
    92: _OBJECTIVES.format("the other-FU-member listing grid K30-K31"),
    93: _INSTRUMENT_OUT.format("the first other-FU-member section K32-K41"),
    94: _OBJECTIVES.format("other-FU-member items K32-K41"),
    95: _INSTRUMENT_OUT.format("the first other-FU-member section K42-K47"),
    96: _OBJECTIVES.format("other-FU-member items K42-K47"),
    97: _INSTRUMENT_OUT.format("the second other-FU-member section K32-K41"),
    98: _OBJECTIVES.format("other-FU-member items K32-K41"),
    99: _INSTRUMENT_OUT.format("the second other-FU-member section K42-K47"),
    100: _OBJECTIVES.format("other-FU-member items K42-K47"),
    101: _INSTRUMENT_OUT.format("the third other-FU-member section K32-K41"),
    102: _OBJECTIVES.format("other-FU-member items K32-K41"),
    103: _INSTRUMENT_OUT.format("the third other-FU-member section K42-K47"),
    104: _OBJECTIVES.format("other-FU-member items K42-K47"),
    105: _INSTRUMENT_OUT.format("child-income items K48-K53"),
    106: _OBJECTIVES.format("child-income items K48-K53"),
    107: _INSTRUMENT_OUT.format(
        "union-membership and head health items K54-K63"
    ),
    108: _OBJECTIVES.format("union-membership and health items K54-K63"),
    109: _INSTRUMENT_OUT.format("wife health items K64-K71"),
    110: _OBJECTIVES.format("wife health items K64-K71"),
    111: _INSTRUMENT_OUT.format(
        "medical-program, windfall, and dependent-support items K72-K80"
    ),
    112: _OBJECTIVES.format("medical-program and dependent items K72-K80"),
    113: _INSTRUMENT_IN.format(
        "section L new wife schooling and lifetime-work items L1-L12"
    ),
    114: _OBJECTIVES.format("section L items L1-L12"),
    115: _INSTRUMENT_IN.format(
        "section M new head background and first-job items M1-M5"
    ),
    116: _OBJECTIVES.format("section M items M1-M5"),
    117: _INSTRUMENT_OUT.format(
        "new-head children, siblings, and growing-up items M6-M18"
    ),
    118: _OBJECTIVES.format("new-head background items M6-M18"),
    119: _INSTRUMENT_IN.format(
        "new-head lifetime-work and schooling items M19-M36"
    ),
    120: _OBJECTIVES.format("new-head lifetime-work and schooling items"),
    121: _INSTRUMENT_OUT.format(
        "religious-preference and interview-close items M37-M42"
    ),
    122: _OBJECTIVES.format("religion and interview-close items M37-M42"),
}

_DEFAULT_NOTES = {
    F: "Exact printed routing atom retained with its reviewed ancestry.",
    R: "Exact printed role lexeme retained as the screen's role attachment.",
    J: "Exact printed job noun retained as an establishing job anchor.",
    M: "Exact printed remuneration component retained from the source line.",
    T: "Exact printed role-total remuneration anchor retained.",
    FA: "Exact printed farm aggregate anchor retained.",
    BA: "Exact printed business aggregate anchor retained.",
    C: "Exact printed contextual field retained for a ratified purpose.",
    P: "Exact printed question prompt retained for its source field.",
    A: "Exact printed repeat or cross-reference instruction retained.",
}

SECTION_C = ("p15_flow_section_c",)
_JOB_NOTE = (
    "Parent is the section's single printed current-job anchor, which governs "
    "this screen's occupation, industry, pay-form, tenure, and work-time "
    "fields."
)

# Page 15 - section C entry and items C1-C6.
PAGE_15 = (
    line(
        15,
        3,
        F,
        "p15_flow_section_c",
        note="Printed section C header conditions the head employment "
        "schedule selected at C1.",
    ),
    word(15, 3, "HEAD", R, "p15_role_head", routes=(SECTION_C,)),
    block(
        15,
        6,
        7,
        C,
        "p15_c1_assignment",
        routes=(SECTION_C,),
        note="C1 prints the head labor-force assignment field.",
    ),
    block(15, 6, 7, P, "p15_c1_prompt", routes=(SECTION_C,)),
    word(15, 6, "HEAD", R, "p15_role_head_c1", routes=(SECTION_C,)),
    line(
        15,
        12,
        F,
        "p15_flow_turn_section_d",
        routes=(SECTION_C,),
        note="C1 routing atom to the section D schedule.",
    ),
    line(
        15,
        17,
        F,
        "p15_flow_turn_section_e",
        routes=(SECTION_C,),
        note="C1 routing atom to the section E schedule.",
    ),
    line(
        15,
        37,
        C,
        "p15_c2_employee_self",
        routes=(SECTION_C,),
        note="C2 prints the employee/self-employed field.",
    ),
    line(15, 37, P, "p15_c2_prompt", routes=(SECTION_C,)),
    line(
        15,
        46,
        C,
        "p15_c3_government",
        routes=(SECTION_C,),
        note="C3 prints the federal/state/local government-level field.",
    ),
    line(15, 46, P, "p15_c3_prompt", routes=(SECTION_C,)),
    word(
        15,
        58,
        "present employer",
        J,
        "p15_c6_job",
        routes=(SECTION_C,),
        note="C6 prints the head's current employer, the establishing job "
        "anchor for the section C schedule.",
    ),
    line(
        15,
        58,
        C,
        "p15_c6_tenure",
        parents=("p15_c6_job",),
        routes=(SECTION_C,),
        note="C6 prints the tenure/exposure field for the current job.",
    ),
    line(15, 58, P, "p15_c6_prompt", routes=(SECTION_C,)),
)

# Page 17 - first scan of items C7-C17.
PAGE_17 = (
    line(
        17,
        3,
        C,
        "p17_c7_occupation",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C7 prints the head main-occupation field.",
    ),
    line(17, 3, P, "p17_c7_prompt", routes=(SECTION_C,)),
    line(
        17,
        14,
        C,
        "p17_c8_occupation_detail",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C8 prints the occupation elaboration field.",
    ),
    line(17, 14, P, "p17_c8_prompt", routes=(SECTION_C,)),
    block(
        17,
        40,
        45,
        P,
        "p17_c12_prompt",
        routes=(SECTION_C,),
        note="C12 prints the extra-hours pay-eligibility question.",
    ),
    block(
        17,
        53,
        55,
        M,
        "p17_c13_extra_hour_rate",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C13 prints the per-hour amount for extra hours on the current "
        "job.",
    ),
    block(17, 53, 55, P, "p17_c13_prompt", routes=(SECTION_C,)),
    block(
        17,
        62,
        64,
        M,
        "p17_c17_extra_hour_earnings",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C17 prints the extra-hour earnings amount.",
    ),
    block(17, 62, 64, P, "p17_c17_prompt", routes=(SECTION_C,)),
)

# Page 19 - second scan of items C7-C17.
PAGE_19 = (
    line(
        19,
        3,
        C,
        "p19_c7_occupation",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C7 prints the head main-occupation field on the second scan.",
    ),
    line(19, 3, P, "p19_c7_prompt", routes=(SECTION_C,)),
    line(
        19,
        9,
        C,
        "p19_c8_occupation_detail",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C8 prints the occupation elaboration field.",
    ),
    line(19, 9, P, "p19_c8_prompt", routes=(SECTION_C,)),
    line(
        19,
        14,
        C,
        "p19_c9_industry",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C9 prints the business-or-industry field.",
    ),
    line(19, 14, P, "p19_c9_prompt", routes=(SECTION_C,)),
    word(
        19,
        17,
        "main job",
        J,
        "p19_c10_main_job",
        routes=(SECTION_C,),
        note="C10 prints the head main job.",
    ),
    line(
        19,
        17,
        C,
        "p19_c10_pay_form",
        parents=("p19_c10_main_job",),
        routes=(SECTION_C,),
        note="C10 prints the salaried/hourly pay-form reporting unit for the "
        "main job.",
    ),
    line(19, 17, P, "p19_c10_prompt", routes=(SECTION_C,)),
    word(
        19,
        20,
        "salary",
        M,
        "p19_c11_salary",
        parents=("p19_c10_main_job",),
        routes=(SECTION_C,),
        note="C11 prints the salary component of the main job.",
    ),
    block(
        19,
        32,
        36,
        P,
        "p19_c12_prompt",
        routes=(SECTION_C,),
        note="C12 prints the extra-hours pay-eligibility question.",
    ),
    block(
        19,
        45,
        47,
        M,
        "p19_c13_extra_hour_rate",
        parents=("p19_c10_main_job",),
        routes=(SECTION_C,),
        note="C13 prints the per-hour amount for extra hours.",
    ),
    block(19, 45, 47, P, "p19_c13_prompt", routes=(SECTION_C,)),
    block(
        19,
        50,
        52,
        M,
        "p19_c17_extra_hour_earnings",
        parents=("p19_c10_main_job",),
        routes=(SECTION_C,),
        note="C17 prints the extra-hour earnings amount.",
    ),
    block(19, 50, 52, P, "p19_c17_prompt", routes=(SECTION_C,)),
)

# Page 21 - items C18-C26, head job change.
PAGE_21 = (
    word(21, 8, "HEAD", R, "p21_role_head", routes=(SECTION_C,)),
    line(
        21,
        8,
        F,
        "p21_flow_c19_a",
        routes=(SECTION_C,),
        note="C19 checkpoint alternative A conditions the C20-C21 block.",
    ),
    line(
        21,
        9,
        F,
        "p21_flow_c19_b",
        routes=(SECTION_C,),
        note="C19 checkpoint alternative B conditions the C22-C26 block.",
    ),
    line(
        21,
        13,
        C,
        "p21_c22_start_month",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(("p15_flow_section_c", "p21_flow_c19_b"),),
        note="C22 prints the start-month field for the present position.",
    ),
    line(
        21,
        13,
        P,
        "p21_c22_prompt",
        routes=(("p15_flow_section_c", "p21_flow_c19_b"),),
    ),
    block(
        21,
        55,
        56,
        P,
        "p21_c26_prompt",
        routes=(("p15_flow_section_c", "p21_flow_c19_b"),),
        note="C26 prints the pay comparison against the previous job.",
    ),
    line(
        21,
        61,
        F,
        "p21_flow_turn_c27",
        routes=(SECTION_C,),
        note="Routing atom from the C18-C26 block to C27.",
    ),
)

# Page 23 - first scan of head work-time items C27-C39.
PAGE_23 = (
    line(
        23,
        2,
        C,
        "p23_c27_missed_work",
        routes=(SECTION_C,),
        note="C27 prints the work-time-missed exposure field.",
    ),
    line(23, 2, P, "p23_c27_prompt", routes=(SECTION_C,)),
    line(
        23,
        9,
        F,
        "p23_flow_go_c29",
        routes=(SECTION_C,),
        note="C27 no-branch routing atom to C29.",
    ),
    line(
        23,
        15,
        C,
        "p23_c28_missed_amount",
        routes=(SECTION_C,),
        note="C28 prints the amount of work missed.",
    ),
    line(23, 15, P, "p23_c28_prompt", routes=(SECTION_C,)),
    line(
        23,
        30,
        F,
        "p23_flow_go_c31",
        routes=(SECTION_C,),
        note="C29 no-branch routing atom to C31.",
    ),
    line(
        23,
        31,
        C,
        "p23_c30_missed_amount",
        routes=(SECTION_C,),
        note="C30 prints the own-sickness work-time-missed amount.",
    ),
    line(23, 31, P, "p23_c30_prompt", routes=(SECTION_C,)),
    line(
        23,
        36,
        C,
        "p23_c31_vacation",
        routes=(SECTION_C,),
        note="C31 prints the vacation/time-off exposure field.",
    ),
    line(23, 36, P, "p23_c31_prompt", routes=(SECTION_C,)),
    line(
        23,
        37,
        F,
        "p23_flow_go_c33",
        routes=(SECTION_C,),
        note="C31 no-branch routing atom to C33.",
    ),
    line(
        23,
        40,
        C,
        "p23_c32_vacation_amount",
        routes=(SECTION_C,),
        note="C32 prints the vacation/time-off amount.",
    ),
    line(23, 40, P, "p23_c32_prompt", routes=(SECTION_C,)),
    line(
        23,
        46,
        C,
        "p23_c33_strike",
        routes=(SECTION_C,),
        note="C33 prints the strike work-time-missed field.",
    ),
    line(23, 46, P, "p23_c33_prompt", routes=(SECTION_C,)),
    line(
        23,
        48,
        F,
        "p23_flow_go_c35",
        routes=(SECTION_C,),
        note="C33 no-branch routing atom to C35.",
    ),
    line(
        23,
        52,
        C,
        "p23_c35_unemployment",
        routes=(SECTION_C,),
        note="C35 prints the unemployment/layoff work-time-missed field.",
    ),
    line(23, 52, P, "p23_c35_prompt", routes=(SECTION_C,)),
    line(
        23,
        54,
        F,
        "p23_flow_go_c37",
        routes=(SECTION_C,),
        note="C35 no-branch routing atom to C37.",
    ),
    line(
        23,
        56,
        C,
        "p23_c36_missed_amount",
        routes=(SECTION_C,),
        note="C36 prints the unemployment work-time-missed amount.",
    ),
    line(23, 56, P, "p23_c36_prompt", routes=(SECTION_C,)),
    word(
        23,
        63,
        "main job",
        J,
        "p23_c37_main_job",
        routes=(SECTION_C,),
        note="C37 prints the head main job for the 1980 work year.",
    ),
    line(
        23,
        63,
        C,
        "p23_c37_weeks",
        parents=("p23_c37_main_job",),
        routes=(SECTION_C,),
        note="C37 prints weeks actually worked on the main job.",
    ),
    line(23, 63, P, "p23_c37_prompt", routes=(SECTION_C,)),
    line(
        23,
        66,
        C,
        "p23_c39_hours",
        parents=("p23_c37_main_job",),
        routes=(SECTION_C,),
        note="C39 prints average hours per week on the main job.",
    ),
    line(23, 66, P, "p23_c39_prompt", routes=(SECTION_C,)),
)

# Page 25 - second scan of head work-time items C27-C39.
PAGE_25 = (
    line(
        25,
        4,
        C,
        "p25_c27_missed_work",
        routes=(SECTION_C,),
        note="C27 prints the work-time-missed exposure field.",
    ),
    line(25, 4, P, "p25_c27_prompt", routes=(SECTION_C,)),
    line(
        25,
        14,
        C,
        "p25_c28_missed_amount",
        routes=(SECTION_C,),
        note="C28 prints the amount of work missed.",
    ),
    line(25, 14, P, "p25_c28_prompt", routes=(SECTION_C,)),
    line(
        25,
        24,
        C,
        "p25_c29_own_sickness",
        routes=(SECTION_C,),
        note="C29 prints the own-sickness work-time-missed field.",
    ),
    line(25, 24, P, "p25_c29_prompt", routes=(SECTION_C,)),
    line(
        25,
        26,
        F,
        "p25_flow_go_c31",
        routes=(SECTION_C,),
        note="C29 no-branch routing atom to C31.",
    ),
    line(
        25,
        28,
        C,
        "p25_c30_missed_amount",
        routes=(SECTION_C,),
        note="C30 prints the own-sickness work-time-missed amount.",
    ),
    line(25, 28, P, "p25_c30_prompt", routes=(SECTION_C,)),
    block(
        25,
        36,
        41,
        C,
        "p25_c31_vacation",
        routes=(SECTION_C,),
        note="C31 prints the vacation/time-off exposure field across the "
        "scan's broken lines.",
    ),
    block(25, 36, 41, P, "p25_c31_prompt", routes=(SECTION_C,)),
    line(
        25,
        45,
        F,
        "p25_flow_go_c33",
        routes=(SECTION_C,),
        note="C31 no-branch routing atom to C33.",
    ),
    line(
        25,
        48,
        C,
        "p25_c32_vacation_amount",
        routes=(SECTION_C,),
        note="C32 prints the vacation/time-off amount.",
    ),
    line(25, 48, P, "p25_c32_prompt", routes=(SECTION_C,)),
    line(
        25,
        52,
        C,
        "p25_c33_strike",
        routes=(SECTION_C,),
        note="C33 prints the strike work-time-missed field.",
    ),
    line(25, 52, P, "p25_c33_prompt", routes=(SECTION_C,)),
    line(
        25,
        54,
        F,
        "p25_flow_go_c35",
        routes=(SECTION_C,),
        note="C33 no-branch routing atom to C35.",
    ),
    line(
        25,
        60,
        C,
        "p25_c35_unemployment",
        routes=(SECTION_C,),
        note="C35 prints the unemployment/layoff work-time-missed field.",
    ),
    line(25, 60, P, "p25_c35_prompt", routes=(SECTION_C,)),
    line(
        25,
        62,
        F,
        "p25_flow_go_c37",
        routes=(SECTION_C,),
        note="C35 no-branch routing atom to C37.",
    ),
    word(
        25,
        68,
        "main job",
        J,
        "p25_c37_main_job",
        routes=(SECTION_C,),
        note="C37 prints the head main job for the 1980 work year.",
    ),
    block(
        25,
        68,
        69,
        C,
        "p25_c37_weeks",
        parents=("p25_c37_main_job",),
        routes=(SECTION_C,),
        note="C37 prints weeks actually worked on the main job across the "
        "scan's inverted lines.",
    ),
    block(25, 68, 69, P, "p25_c37_prompt", routes=(SECTION_C,)),
)

# Page 27 - head overtime, extra jobs, and the C48 checkpoint.
PAGE_27 = (
    line(
        27,
        5,
        C,
        "p27_c40_overtime",
        parents=("p15_c6_job",),
        parent_note=_JOB_NOTE,
        routes=(SECTION_C,),
        note="C40 prints the uncounted-overtime exposure field.",
    ),
    line(27, 5, P, "p27_c40_prompt", routes=(SECTION_C,)),
    line(
        27,
        7,
        F,
        "p27_flow_go_c42",
        routes=(SECTION_C,),
        note="C40 no-branch routing atom to C42.",
    ),
    word(
        27,
        13,
        "extra jobs",
        J,
        "p27_c42_extra_jobs",
        routes=(SECTION_C,),
        note="C42 prints the head's extra jobs as a distinct job anchor.",
    ),
    line(27, 13, P, "p27_c42_prompt", routes=(SECTION_C,)),
    line(
        27,
        16,
        F,
        "p27_flow_go_c48",
        routes=(SECTION_C,),
        note="C42 no-branch routing atom to the C48 checkpoint.",
    ),
    line(
        27,
        22,
        C,
        "p27_c43_extra_occupation",
        parents=("p27_c42_extra_jobs",),
        routes=(SECTION_C,),
        note="C43 prints the extra-job occupation field.",
    ),
    line(27, 22, P, "p27_c43_prompt", routes=(SECTION_C,)),
    line(
        27,
        33,
        C,
        "p27_c46_extra_weeks",
        parents=("p27_c42_extra_jobs",),
        routes=(SECTION_C,),
        note="C46 prints weeks worked on the extra job(s).",
    ),
    line(27, 33, P, "p27_c46_prompt", routes=(SECTION_C,)),
    line(
        27,
        38,
        C,
        "p27_c47_extra_hours",
        parents=("p27_c42_extra_jobs",),
        routes=(SECTION_C,),
        note="C47 prints average hours per week on the extra job(s).",
    ),
    line(27, 38, P, "p27_c47_prompt", routes=(SECTION_C,)),
    line(
        27,
        45,
        A,
        "p27_c48_cross_reference",
        routes=(SECTION_C,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="C48 prints an explicit checkpoint cross-reference to the C36 "
        "work-time answer on printed page 10.",
    ),
    word(27, 48, "HEAD", R, "p27_role_head", routes=(SECTION_C,)),
    line(
        27,
        48,
        F,
        "p27_flow_c48_a",
        routes=(SECTION_C,),
        note="C48 checkpoint alternative A conditions the C49 series.",
    ),
    line(
        27,
        49,
        F,
        "p27_flow_c48_a_route",
        routes=(("p15_flow_section_c", "p27_flow_c48_a"),),
        note="C48 alternative A routing atom to C49.",
    ),
    line(
        27,
        51,
        F,
        "p27_flow_c48_all_others",
        routes=(SECTION_C,),
        note="C48 checkpoint all-others routing atom to C50 on printed "
        "page 15.",
    ),
)

# Page 29 - head unemployment-spell items C49-C57.
PAGE_29 = (
    block(
        29,
        3,
        4,
        C,
        "p29_c49_spell_start",
        routes=(SECTION_C,),
        note="C49 prints the month/year the last 1980 layoff spell began.",
    ),
    block(29, 3, 4, P, "p29_c49_prompt", routes=(SECTION_C,)),
    line(
        29,
        10,
        C,
        "p29_c50_spell_weeks",
        routes=(SECTION_C,),
        note="C50 prints weeks before returning to work.",
    ),
    line(29, 10, P, "p29_c50_prompt", routes=(SECTION_C,)),
    line(
        29,
        15,
        F,
        "p29_flow_go_c55",
        routes=(SECTION_C,),
        note="C50 routing atom to the C55 checkpoint.",
    ),
    line(
        29,
        46,
        A,
        "p29_c55_cross_reference",
        routes=(SECTION_C,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="C55 prints an explicit checkpoint cross-reference to C49.",
    ),
    line(
        29,
        48,
        F,
        "p29_flow_c55_a",
        routes=(SECTION_C,),
        note="C55 checkpoint alternative A conditions the C56 series.",
    ),
    word(29, 50, "HEAD'S", R, "p29_role_head", routes=(SECTION_C,)),
    line(
        29,
        50,
        F,
        "p29_flow_c55_b",
        routes=(SECTION_C,),
        note="C55 checkpoint alternative B routes out of the spell series.",
    ),
    line(
        29,
        53,
        C,
        "p29_c56_prior_spell",
        routes=(("p15_flow_section_c", "p29_flow_c55_a"),),
        note="C56 prints the earlier-1980 unemployment spell field.",
    ),
    line(
        29,
        53,
        P,
        "p29_c56_prompt",
        routes=(("p15_flow_section_c", "p29_flow_c55_a"),),
    ),
    line(
        29,
        56,
        F,
        "p29_flow_c56_no",
        routes=(("p15_flow_section_c", "p29_flow_c55_a"),),
        note="C56 no-branch routing atom to C70.",
    ),
    line(
        29,
        63,
        C,
        "p29_c57_spell_start",
        routes=(("p15_flow_section_c", "p29_flow_c55_a"),),
        note="C57 prints the month/year that earlier spell began.",
    ),
    line(
        29,
        63,
        P,
        "p29_c57_prompt",
        routes=(("p15_flow_section_c", "p29_flow_c55_a"),),
    ),
)

# Page 31 - head unemployment-spell items C58-C69.
PAGE_31 = (
    line(
        31,
        2,
        C,
        "p31_c58_spell_weeks",
        routes=(SECTION_C,),
        note="C58 prints weeks before returning to work.",
    ),
    line(31, 2, P, "p31_c58_prompt", routes=(SECTION_C,)),
    line(
        31,
        7,
        F,
        "p31_flow_go_c63_first",
        routes=(SECTION_C,),
        note="C58 routing atom to C63.",
    ),
    line(
        31,
        20,
        F,
        "p31_flow_go_c63_second",
        routes=(SECTION_C,),
        note="C59 branch routing atom to C63.",
    ),
    line(
        31,
        34,
        C,
        "p31_c63_prior_spell",
        routes=(
            SECTION_C,
            ("p15_flow_section_c", "p31_flow_go_c63_first"),
            ("p15_flow_section_c", "p31_flow_go_c63_second"),
        ),
        note="C63 prints the earlier-1980 unemployment spell field, reached "
        "by falling through the C59-C62 block or by either retained C63 "
        "routing atom, so it carries all three applicable paths.",
    ),
    line(
        31,
        34,
        P,
        "p31_c63_prompt",
        routes=(
            SECTION_C,
            ("p15_flow_section_c", "p31_flow_go_c63_first"),
            ("p15_flow_section_c", "p31_flow_go_c63_second"),
        ),
    ),
    line(
        31,
        45,
        C,
        "p31_c64_spell_start",
        routes=(SECTION_C,),
        note="C64 prints the month/year that spell began.",
    ),
    line(31, 45, P, "p31_c64_prompt", routes=(SECTION_C,)),
    line(
        31,
        49,
        C,
        "p31_c65_spell_weeks",
        routes=(SECTION_C,),
        note="C65 prints weeks before returning to work.",
    ),
    line(31, 49, P, "p31_c65_prompt", routes=(SECTION_C,)),
    line(
        31,
        56,
        F,
        "p31_flow_turn_c70_first",
        routes=(SECTION_C,),
        note="C65 routing atom to C70.",
    ),
    line(
        31,
        71,
        F,
        "p31_flow_turn_c70_second",
        routes=(SECTION_C,),
        note="C67 routing atom to C70.",
    ),
    line(
        31,
        77,
        F,
        "p31_flow_turn_c70_third",
        routes=(SECTION_C,),
        note="C68 routing atom to C70.",
    ),
    line(
        31,
        84,
        F,
        "p31_flow_turn_c70_fourth",
        routes=(SECTION_C,),
        note="C69 routing atom to C70.",
    ),
)

# Page 37 - head job-search and retirement items C90-C95.  Only the C92
# checkpoint routing to section F controls a retained R_Q path.
PAGE_37 = (
    line(
        37,
        15,
        F,
        "p37_flow_c92_a",
        routes=(SECTION_C,),
        note="C92 checkpoint alternative A routes the under-45 head to "
        "section F.",
    ),
    word(37, 17, "HEAD", R, "p37_role_head", routes=(SECTION_C,)),
    line(
        37,
        17,
        F,
        "p37_flow_c92_b",
        routes=(SECTION_C,),
        note="C92 checkpoint alternative B conditions the C93 retirement "
        "block.",
    ),
    line(
        37,
        43,
        F,
        "p37_flow_turn_section_f",
        routes=(SECTION_C,),
        note="Closing routing atom from section C to section F.",
    ),
)

SECTION_D = (
    "p15_flow_section_c",
    "p15_flow_turn_section_d",
    "p39_flow_section_d",
)

# Page 39 - section D entry and items D1-D12.
PAGE_39 = (
    line(
        39,
        3,
        F,
        "p39_flow_section_d",
        routes=(("p15_flow_section_c", "p15_flow_turn_section_d"),),
        note="Printed section D header conditions the unemployed-head "
        "schedule reached by the C1 routing atom.",
    ),
    word(39, 3, "HEAD", R, "p39_role_head", routes=(SECTION_D,)),
    word(
        39,
        5,
        "job",
        J,
        "p39_d1_sought_job",
        routes=(SECTION_D,),
        note="D1 prints the job the unemployed head is looking for.",
    ),
    line(
        39,
        5,
        C,
        "p39_d1_occupation",
        parents=("p39_d1_sought_job",),
        routes=(SECTION_D,),
        note="D1 prints the sought-job occupation field.",
    ),
    line(39, 5, P, "p39_d1_prompt", routes=(SECTION_D,)),
    line(
        39,
        10,
        M,
        "p39_d2_expected_earnings",
        parents=("p39_d1_sought_job",),
        routes=(SECTION_D,),
        note="D2 prints the expected earnings amount for the sought job.",
    ),
    line(39, 10, P, "p39_d2_prompt", routes=(SECTION_D,)),
    line(
        39,
        49,
        C,
        "p39_d7_search_duration",
        routes=(SECTION_D,),
        note="D7 prints how long the head has been looking for work.",
    ),
    line(39, 49, P, "p39_d7_prompt", routes=(SECTION_D,)),
    line(
        39,
        56,
        F,
        "p39_flow_d8_no",
        routes=(SECTION_D,),
        note="D8 no-branch routing atom to D62.",
    ),
    word(
        39,
        59,
        "last job",
        J,
        "p39_d9_last_job",
        routes=(SECTION_D,),
        note="D9 prints the head's last job as a distinct job anchor.",
    ),
    line(
        39,
        59,
        C,
        "p39_d9_occupation",
        parents=("p39_d9_last_job",),
        routes=(SECTION_D,),
        note="D9/D10 print the last-job occupation field.",
    ),
    line(39, 59, P, "p39_d9_prompt", routes=(SECTION_D,)),
    line(
        39,
        71,
        C,
        "p39_d12_last_worked",
        parents=("p39_d9_last_job",),
        routes=(SECTION_D,),
        note="D12 prints when the head last worked.",
    ),
    line(39, 71, P, "p39_d12_prompt", routes=(SECTION_D,)),
)

# Page 41 - section D work-time items D13-D24b.  Side-column calculation
# text merges into several scan lines, so the exact printed question is
# selected instead of the whole physical line.
PAGE_41 = (
    word(
        41,
        3,
        "Did you take any vacation or time off during 1980?",
        C,
        "p41_d13_vacation",
        routes=(SECTION_D,),
        note="D13 prints the vacation/time-off exposure field.",
    ),
    word(
        41,
        3,
        "Did you take any vacation or time off during 1980?",
        P,
        "p41_d13_prompt",
        routes=(SECTION_D,),
    ),
    word(
        41,
        9,
        "Dl4. How much vacation or time off did you take?",
        C,
        "p41_d14_vacation_amount",
        routes=(SECTION_D,),
        note="D14 prints the vacation/time-off amount.",
    ),
    word(
        41,
        9,
        "Dl4. How much vacation or time off did you take?",
        P,
        "p41_d14_prompt",
        routes=(SECTION_D,),
    ),
    line(
        41,
        13,
        C,
        "p41_d15_other_sickness",
        routes=(SECTION_D,),
        note="D15 prints the other-person-sickness work-time-missed field.",
    ),
    line(41, 13, P, "p41_d15_prompt", routes=(SECTION_D,)),
    line(
        41,
        19,
        C,
        "p41_d16_missed_amount",
        routes=(SECTION_D,),
        note="D16 prints the work-time-missed amount.",
    ),
    line(41, 19, P, "p41_d16_prompt", routes=(SECTION_D,)),
    line(
        41,
        24,
        C,
        "p41_d17_own_sickness",
        routes=(SECTION_D,),
        note="D17 prints the own-sickness work-time-missed field.",
    ),
    line(41, 24, P, "p41_d17_prompt", routes=(SECTION_D,)),
    line(
        41,
        29,
        F,
        "p41_flow_go_d19",
        routes=(SECTION_D,),
        note="D17 no-branch routing atom to D19.",
    ),
    line(
        41,
        30,
        C,
        "p41_d18_missed_amount",
        routes=(SECTION_D,),
        note="D18 prints the work-time-missed amount.",
    ),
    line(41, 30, P, "p41_d18_prompt", routes=(SECTION_D,)),
    line(
        41,
        35,
        C,
        "p41_d19_strike",
        routes=(SECTION_D,),
        note="D19 prints the strike work-time-missed field.",
    ),
    line(41, 35, P, "p41_d19_prompt", routes=(SECTION_D,)),
    line(
        41,
        40,
        F,
        "p41_flow_go_d21",
        routes=(SECTION_D,),
        note="D19 no-branch routing atom to D21.",
    ),
    line(
        41,
        41,
        C,
        "p41_d20_missed_amount",
        routes=(SECTION_D,),
        note="D20 prints the work-time-missed amount.",
    ),
    line(41, 41, P, "p41_d20_prompt", routes=(SECTION_D,)),
    line(
        41,
        45,
        C,
        "p41_d21_unemployment",
        routes=(SECTION_D,),
        note="D21 prints the unemployment/layoff work-time-missed field.",
    ),
    line(41, 45, P, "p41_d21_prompt", routes=(SECTION_D,)),
    line(
        41,
        47,
        F,
        "p41_flow_go_d23",
        routes=(SECTION_D,),
        note="D21 no-branch routing atom to D23.",
    ),
    line(
        41,
        53,
        C,
        "p41_d23_weeks",
        routes=(SECTION_D,),
        note="D23 prints weeks actually worked in 1980.",
    ),
    line(41, 53, P, "p41_d23_prompt", routes=(SECTION_D,)),
)

# Page 43 - section D unemployment-spell items D26-D35.
PAGE_43 = (
    line(
        43,
        2,
        A,
        "p43_d26_cross_reference",
        routes=(SECTION_D,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="D26 prints an explicit checkpoint cross-reference to the D22 "
        "work-time answer on printed page 18.",
    ),
    word(43, 4, "HEAD", R, "p43_role_head", routes=(SECTION_D,)),
    line(
        43,
        4,
        F,
        "p43_flow_d26_a",
        routes=(SECTION_D,),
        note="D26 checkpoint alternative A conditions the D27 series.",
    ),
    line(
        43,
        6,
        F,
        "p43_flow_d26_all_others",
        routes=(SECTION_D,),
        note="D26 checkpoint all-others routing atom to D59.",
    ),
    block(
        43,
        9,
        10,
        C,
        "p43_d27_spell_start",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d26_a",
            ),
        ),
        note="D27 prints the month/year the last 1980 layoff spell began.",
    ),
    block(
        43,
        9,
        10,
        P,
        "p43_d27_prompt",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d26_a",
            ),
        ),
    ),
    line(
        43,
        18,
        C,
        "p43_d28_spell_weeks",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d26_a",
            ),
        ),
        note="D28 prints weeks before returning to work.",
    ),
    line(
        43,
        18,
        P,
        "p43_d28_prompt",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d26_a",
            ),
        ),
    ),
    line(
        43,
        22,
        F,
        "p43_flow_go_d33",
        routes=(SECTION_D,),
        note="D28 routing atom to the D33 checkpoint.",
    ),
    line(
        43,
        49,
        A,
        "p43_d33_cross_reference",
        routes=(SECTION_D,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="D33 prints an explicit checkpoint cross-reference to D27.",
    ),
    line(
        43,
        51,
        F,
        "p43_flow_d33_a",
        routes=(SECTION_D,),
        note="D33 checkpoint alternative A conditions the D34 series.",
    ),
    word(43, 52, "HEAD'S", R, "p43_role_head_b", routes=(SECTION_D,)),
    line(
        43,
        52,
        F,
        "p43_flow_d33_b",
        routes=(SECTION_D,),
        note="D33 checkpoint alternative B routes out of the spell series.",
    ),
    line(
        43,
        58,
        C,
        "p43_d34_prior_spell",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d33_a",
            ),
        ),
        note="D34 prints the earlier-1980 unemployment spell field.",
    ),
    line(
        43,
        58,
        P,
        "p43_d34_prompt",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d33_a",
            ),
        ),
    ),
    line(
        43,
        62,
        F,
        "p43_flow_d34_no",
        routes=(SECTION_D,),
        note="D34 no-branch routing atom to D48.",
    ),
    line(
        43,
        64,
        C,
        "p43_d35_spell_start",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d33_a",
            ),
        ),
        note="D35 prints the month/year that earlier spell began.",
    ),
    line(
        43,
        64,
        P,
        "p43_d35_prompt",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_d",
                "p39_flow_section_d",
                "p43_flow_d33_a",
            ),
        ),
    ),
)

# Page 45 - section D unemployment-spell items D36-D48.
PAGE_45 = (
    line(
        45,
        2,
        C,
        "p45_d36_spell_weeks",
        routes=(SECTION_D,),
        note="D36 prints weeks before returning to work.",
    ),
    line(45, 2, P, "p45_d36_prompt", routes=(SECTION_D,)),
    line(
        45,
        6,
        F,
        "p45_flow_go_d41",
        routes=(SECTION_D,),
        note="D36 routing atom to D41.",
    ),
    line(
        45,
        41,
        C,
        "p45_d43_spell_weeks",
        routes=(SECTION_D,),
        note="D43 prints weeks before returning to work.",
    ),
    line(45, 41, P, "p45_d43_prompt", routes=(SECTION_D,)),
    line(
        45,
        59,
        F,
        "p45_flow_turn_d48_first",
        routes=(SECTION_D,),
        note="D44 branch routing atom to D48.",
    ),
    line(
        45,
        70,
        F,
        "p45_flow_turn_d48_second",
        routes=(SECTION_D,),
        note="D47 routing atom to D48.",
    ),
)

# Page 49 - only the section D routing atoms that reach section F and the
# printed age checkpoint alternative are retained; commuting and retirement
# expectation fields map to no ratified purpose.
PAGE_49 = (
    line(
        49,
        47,
        F,
        "p49_flow_d62_a",
        routes=(SECTION_D,),
        note="D62 checkpoint alternative A routes the under-45 head to "
        "section F.",
    ),
    word(49, 49, "HEAD", R, "p49_role_head", routes=(SECTION_D,)),
    line(
        49,
        49,
        F,
        "p49_flow_d62_c",
        routes=(SECTION_D,),
        note="D62 checkpoint alternative C conditions the D65 block.",
    ),
    line(
        49,
        61,
        F,
        "p49_flow_turn_section_f_first",
        routes=(SECTION_D,),
        note="D63 routing atom to section F.",
    ),
    line(
        49,
        70,
        F,
        "p49_flow_turn_section_f_second",
        routes=(SECTION_D,),
        note="D64 routing atom to section F.",
    ),
)

SECTION_E = (
    "p15_flow_section_c",
    "p15_flow_turn_section_e",
    "p51_flow_section_e",
)

# Page 51 - section E entry and items E1-E15.
PAGE_51 = (
    line(
        51,
        2,
        F,
        "p51_flow_section_e",
        routes=(("p15_flow_section_c", "p15_flow_turn_section_e"),),
        note="Printed section E header conditions the out-of-labor-force "
        "head schedule reached by the C1 routing atom.",
    ),
    word(51, 2, "HEAD", R, "p51_role_head", routes=(SECTION_E,)),
    line(
        51,
        5,
        F,
        "p51_flow_e1_retired",
        routes=(SECTION_E,),
        note="E1 checkpoint alternative for a retired head.",
    ),
    line(
        51,
        6,
        F,
        "p51_flow_e1_other",
        routes=(SECTION_E,),
        note="E1 checkpoint alternative for a disabled, housekeeping, or "
        "student head.",
    ),
    line(
        51,
        7,
        C,
        "p51_e2_retirement_year",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_e",
                "p51_flow_section_e",
                "p51_flow_e1_retired",
            ),
        ),
        note="E2 prints the retirement year, an exposure boundary field.",
    ),
    line(
        51,
        7,
        P,
        "p51_e2_prompt",
        routes=(
            (
                "p15_flow_section_c",
                "p15_flow_turn_section_e",
                "p51_flow_section_e",
                "p51_flow_e1_retired",
            ),
        ),
    ),
    line(
        51,
        9,
        C,
        "p51_e3_any_work",
        routes=(SECTION_E,),
        note="E3 prints the any-work-for-money assignment field for 1980.",
    ),
    line(51, 9, P, "p51_e3_prompt", routes=(SECTION_E,)),
    line(
        51,
        16,
        C,
        "p51_e4_occupation",
        routes=(SECTION_E,),
        note="E4 prints the occupation field for that work.",
    ),
    line(51, 16, P, "p51_e4_prompt", routes=(SECTION_E,)),
    line(
        51,
        20,
        C,
        "p51_e5_industry",
        routes=(SECTION_E,),
        note="E5 prints the business-or-industry field for that work.",
    ),
    line(51, 20, P, "p51_e5_prompt", routes=(SECTION_E,)),
    line(
        51,
        25,
        C,
        "p51_e6_weeks",
        routes=(SECTION_E,),
        note="E6 prints weeks worked last year.",
    ),
    line(51, 25, P, "p51_e6_prompt", routes=(SECTION_E,)),
    line(
        51,
        27,
        C,
        "p51_e7_hours",
        routes=(SECTION_E,),
        note="E7 prints hours per week worked.",
    ),
    line(51, 27, P, "p51_e7_prompt", routes=(SECTION_E,)),
    line(
        51,
        30,
        C,
        "p51_e8_still_working",
        routes=(SECTION_E,),
        note="E8 prints the still-working assignment field.",
    ),
    line(51, 30, P, "p51_e8_prompt", routes=(SECTION_E,)),
    line(
        51,
        47,
        F,
        "p51_flow_e10_no",
        routes=(SECTION_E,),
        note="E10 no-branch routing atom to section F.",
    ),
    word(
        51,
        54,
        "job",
        J,
        "p51_e12_prospective_job",
        routes=(SECTION_E,),
        note="E12 prints the prospective job the head has in mind.",
    ),
    line(
        51,
        54,
        C,
        "p51_e12_occupation",
        parents=("p51_e12_prospective_job",),
        routes=(SECTION_E,),
        note="E12 prints the prospective-job occupation field.",
    ),
    line(51, 54, P, "p51_e12_prompt", routes=(SECTION_E,)),
    line(
        51,
        66,
        F,
        "p51_flow_e14_no",
        routes=(SECTION_E,),
        note="E14 no-branch routing atom to section F.",
    ),
)

SECTION_F = ("p53_flow_section_f",)

# Page 53 - section F entry and items F1-F7.  F1 is the source-visible
# universal checkpoint reached from several head schedules, so it roots its
# own branch rather than nesting under one of them.
PAGE_53 = (
    line(
        53,
        2,
        F,
        "p53_flow_section_f",
        note="Printed section F header opens the wife/friend employment "
        "schedule for every head route.",
    ),
    word(53, 2, "WIFE", R, "p53_role_wife", routes=(SECTION_F,)),
    word(53, 6, "HEAD", R, "p53_role_head", routes=(SECTION_F,)),
    line(
        53,
        6,
        F,
        "p53_flow_f1_wife_present",
        routes=(SECTION_F,),
        note="F1 checkpoint alternative 1 conditions the wife schedule.",
    ),
    line(
        53,
        9,
        F,
        "p53_flow_f1_no_wife",
        routes=(SECTION_F,),
        note="F1 checkpoint alternative routing a wifeless male head out of "
        "the wife schedule.",
    ),
    line(
        53,
        11,
        F,
        "p53_flow_f1_female_head",
        routes=(SECTION_F,),
        note="F1 checkpoint alternative routing a female head out of the "
        "wife schedule.",
    ),
    block(
        53,
        14,
        15,
        C,
        "p53_f2_assignment",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
        note="F2 prints the wife labor-force assignment field.",
    ),
    block(
        53,
        14,
        15,
        P,
        "p53_f2_prompt",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
    ),
    word(
        53,
        21,
        "TURt, TO P. 28,",
        F,
        "p53_flow_turn_section_g",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
        note="F2 routing atom to the section G schedule; the scan merges the "
        "adjacent answer column, so the exact directive is selected.",
    ),
    line(
        53,
        44,
        C,
        "p53_f3_employee_self",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
        note="F3 prints the employee/self-employed field.",
    ),
    line(
        53,
        44,
        P,
        "p53_f3_prompt",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
    ),
    line(
        53,
        54,
        C,
        "p53_f4_government",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
        note="F4 prints the federal/state/local government-level field.",
    ),
    line(
        53,
        54,
        P,
        "p53_f4_prompt",
        routes=(("p53_flow_section_f", "p53_flow_f1_wife_present"),),
    ),
)

WIFE_PRESENT = ("p53_flow_section_f", "p53_flow_f1_wife_present")
_WIFE_JOB_NOTE = (
    "Parent is the wife schedule's single printed present-position anchor, "
    "which governs its occupation, industry, pay-form, and start-date fields."
)

# Page 55 - wife occupation, pay, and position items F8-F18.
PAGE_55 = (
    line(
        55,
        2,
        C,
        "p55_f8_occupation",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F8 prints the wife main-occupation field.",
    ),
    line(55, 2, P, "p55_f8_prompt", routes=(WIFE_PRESENT,)),
    line(
        55,
        7,
        C,
        "p55_f9_occupation_detail",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F9 prints the occupation elaboration field.",
    ),
    line(55, 7, P, "p55_f9_prompt", routes=(WIFE_PRESENT,)),
    line(
        55,
        12,
        C,
        "p55_f10_industry",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F10 prints the business-or-industry field.",
    ),
    line(55, 12, P, "p55_f10_prompt", routes=(WIFE_PRESENT,)),
    line(
        55,
        15,
        C,
        "p55_f11_pay_form",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F11 prints the salaried/hourly pay-form reporting unit.",
    ),
    line(55, 15, P, "p55_f11_prompt", routes=(WIFE_PRESENT,)),
    word(
        55,
        19,
        "salary",
        M,
        "p55_f12_salary",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F12 prints the wife salary component.",
    ),
    word(
        55,
        32,
        "present position",
        J,
        "p55_f15_job",
        routes=(WIFE_PRESENT,),
        note="F15 prints the wife's present position, the establishing job "
        "anchor for the section F schedule.",
    ),
    line(
        55,
        32,
        C,
        "p55_f15_tenure",
        parents=("p55_f15_job",),
        routes=(WIFE_PRESENT,),
        note="F15 prints the tenure/exposure field for the present position.",
    ),
    line(55, 32, P, "p55_f15_prompt", routes=(WIFE_PRESENT,)),
    word(55, 37, "WIFE", R, "p55_role_wife", routes=(WIFE_PRESENT,)),
    line(
        55,
        37,
        F,
        "p55_flow_f16_a",
        routes=(WIFE_PRESENT,),
        note="F16 checkpoint alternative A conditions the F17-F18 block.",
    ),
    line(
        55,
        39,
        F,
        "p55_flow_f16_b",
        routes=(WIFE_PRESENT,),
        note="F16 checkpoint alternative B routes to F19.",
    ),
    line(
        55,
        43,
        C,
        "p55_f17_start_month",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(
            (
                "p53_flow_section_f",
                "p53_flow_f1_wife_present",
                "p55_flow_f16_a",
            ),
        ),
        note="F17 prints the start-month field for the present position.",
    ),
    line(
        55,
        43,
        P,
        "p55_f17_prompt",
        routes=(
            (
                "p53_flow_section_f",
                "p53_flow_f1_wife_present",
                "p55_flow_f16_a",
            ),
        ),
    ),
)

# Page 57 - wife work-time items F19-F30b.
PAGE_57 = (
    word(57, 8, "wife", R, "p57_role_wife", routes=(WIFE_PRESENT,)),
    line(
        57,
        8,
        C,
        "p57_f21_own_sickness",
        routes=(WIFE_PRESENT,),
        note="F21 prints the own-sickness work-time-missed field.",
    ),
    line(57, 8, P, "p57_f21_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        9,
        F,
        "p57_flow_go_f23",
        routes=(WIFE_PRESENT,),
        note="F21 no-branch routing atom to F23.",
    ),
    line(
        57,
        15,
        C,
        "p57_f23_vacation",
        routes=(WIFE_PRESENT,),
        note="F23 prints the vacation/time-off exposure field.",
    ),
    line(57, 15, P, "p57_f23_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        19,
        C,
        "p57_f24_vacation_amount",
        routes=(WIFE_PRESENT,),
        note="F24 prints the vacation/time-off amount.",
    ),
    line(57, 19, P, "p57_f24_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        24,
        C,
        "p57_f25_strike",
        routes=(WIFE_PRESENT,),
        note="F25 prints the strike work-time-missed field.",
    ),
    line(57, 24, P, "p57_f25_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        26,
        F,
        "p57_flow_go_f27",
        routes=(WIFE_PRESENT,),
        note="F25 no-branch routing atom to F27.",
    ),
    line(
        57,
        28,
        C,
        "p57_f26_missed_amount",
        routes=(WIFE_PRESENT,),
        note="F26 prints the work-time-missed amount.",
    ),
    line(57, 28, P, "p57_f26_prompt", routes=(WIFE_PRESENT,)),
    block(
        57,
        35,
        36,
        C,
        "p57_f27_unemployment",
        routes=(WIFE_PRESENT,),
        note="F27 prints the unemployment/layoff work-time-missed field.",
    ),
    block(57, 35, 36, P, "p57_f27_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        41,
        F,
        "p57_flow_go_f29",
        routes=(WIFE_PRESENT,),
        note="F27 no-branch routing atom to F29.",
    ),
    line(
        57,
        43,
        C,
        "p57_f28_missed_amount",
        routes=(WIFE_PRESENT,),
        note="F28 prints the work-time-missed amount.",
    ),
    line(57, 43, P, "p57_f28_prompt", routes=(WIFE_PRESENT,)),
    line(
        57,
        48,
        C,
        "p57_f29_weeks",
        routes=(WIFE_PRESENT,),
        note="F29 prints weeks actually worked on the wife main job.",
    ),
    line(57, 48, P, "p57_f29_prompt", routes=(WIFE_PRESENT,)),
    block(
        57,
        52,
        53,
        C,
        "p57_f31_hours",
        routes=(WIFE_PRESENT,),
        note="F31 prints average hours per week worked.",
    ),
    block(57, 52, 53, P, "p57_f31_prompt", routes=(WIFE_PRESENT,)),
)

# Page 59 - wife overtime and extra-job items F32-F40.  Commuting fields map
# to no ratified purpose and are rejected.
PAGE_59 = (
    line(
        59,
        2,
        C,
        "p59_f32_overtime",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F32 prints the uncounted-overtime exposure field.",
    ),
    line(59, 2, P, "p59_f32_prompt", routes=(WIFE_PRESENT,)),
    line(
        59,
        9,
        C,
        "p59_f33_overtime_hours",
        parents=("p55_f15_job",),
        parent_note=_WIFE_JOB_NOTE,
        routes=(WIFE_PRESENT,),
        note="F33 prints annual overtime hours.",
    ),
    line(59, 9, P, "p59_f33_prompt", routes=(WIFE_PRESENT,)),
    word(
        59,
        15,
        "extra jobs",
        J,
        "p59_f34_extra_jobs",
        routes=(WIFE_PRESENT,),
        note="F34 prints the wife's extra jobs as a distinct job anchor.",
    ),
    block(59, 15, 16, P, "p59_f34_prompt", routes=(WIFE_PRESENT,)),
    line(
        59,
        20,
        C,
        "p59_f35_extra_occupation",
        parents=("p59_f34_extra_jobs",),
        routes=(WIFE_PRESENT,),
        note="F35 prints the extra-job occupation field.",
    ),
    line(59, 20, P, "p59_f35_prompt", routes=(WIFE_PRESENT,)),
    line(
        59,
        24,
        C,
        "p59_f36_extra_weeks",
        parents=("p59_f34_extra_jobs",),
        routes=(WIFE_PRESENT,),
        note="F36 prints weeks worked on the extra job.",
    ),
    line(59, 24, P, "p59_f36_prompt", routes=(WIFE_PRESENT,)),
    line(
        59,
        28,
        C,
        "p59_f37_extra_hours",
        parents=("p59_f34_extra_jobs",),
        routes=(WIFE_PRESENT,),
        note="F37 prints average hours per week on the extra job(s).",
    ),
    line(59, 28, P, "p59_f37_prompt", routes=(WIFE_PRESENT,)),
)

SECTION_G = (
    "p53_flow_section_f",
    "p53_flow_f1_wife_present",
    "p53_flow_turn_section_g",
    "p61_flow_section_g",
)

# Page 61 - section G entry and items G1-G9.
PAGE_61 = (
    line(
        61,
        3,
        F,
        "p61_flow_section_g",
        routes=(
            (
                "p53_flow_section_f",
                "p53_flow_f1_wife_present",
                "p53_flow_turn_section_g",
            ),
        ),
        note="Printed section G header conditions the unemployed-wife "
        "schedule reached by the F2 routing atom.",
    ),
    word(61, 3, "WIFE", R, "p61_role_wife", routes=(SECTION_G,)),
    word(
        61,
        5,
        "job",
        J,
        "p61_g1_sought_job",
        routes=(SECTION_G,),
        note="G1 prints the job the unemployed wife is looking for.",
    ),
    line(
        61,
        5,
        C,
        "p61_g1_occupation",
        parents=("p61_g1_sought_job",),
        routes=(SECTION_G,),
        note="G1 prints the sought-job occupation field.",
    ),
    line(61, 5, P, "p61_g1_prompt", routes=(SECTION_G,)),
    line(
        61,
        11,
        F,
        "p61_flow_go_g4",
        routes=(SECTION_G,),
        note="G2 no-branch routing atom to G4.",
    ),
    line(
        61,
        19,
        C,
        "p61_g4_search_duration",
        routes=(SECTION_G,),
        note="G4 prints how long the wife has been looking for work.",
    ),
    line(61, 19, P, "p61_g4_prompt", routes=(SECTION_G,)),
    line(
        61,
        29,
        C,
        "p61_g6_occupation",
        routes=(SECTION_G,),
        note="G6 prints the last-job occupation field.",
    ),
    line(61, 29, P, "p61_g6_prompt", routes=(SECTION_G,)),
    line(
        61,
        34,
        C,
        "p61_g7_industry",
        routes=(SECTION_G,),
        note="G7 prints the last-job business-or-industry field.",
    ),
    line(61, 34, P, "p61_g7_prompt", routes=(SECTION_G,)),
)

# Page 63 - section G work-time items G10-G22.
PAGE_63 = (
    word(63, 3, "wife", R, "p63_role_wife", routes=(SECTION_G,)),
    block(
        63,
        3,
        4,
        C,
        "p63_g10_vacation",
        routes=(SECTION_G,),
        note="G10 prints the vacation/time-off exposure field.",
    ),
    block(63, 3, 4, P, "p63_g10_prompt", routes=(SECTION_G,)),
    line(
        63,
        5,
        F,
        "p63_flow_go_g12",
        routes=(SECTION_G,),
        note="G10 no-branch routing atom to G12.",
    ),
    line(
        63,
        7,
        C,
        "p63_g11_vacation_amount",
        routes=(SECTION_G,),
        note="G11 prints the vacation/time-off amount.",
    ),
    line(63, 7, P, "p63_g11_prompt", routes=(SECTION_G,)),
    block(
        63,
        11,
        12,
        C,
        "p63_g12_other_sickness",
        routes=(SECTION_G,),
        note="G12 prints the other-person-sickness work-time-missed field.",
    ),
    block(63, 11, 12, P, "p63_g12_prompt", routes=(SECTION_G,)),
    line(
        63,
        17,
        C,
        "p63_g13_missed_amount",
        routes=(SECTION_G,),
        note="G13 prints the work-time-missed amount.",
    ),
    line(63, 17, P, "p63_g13_prompt", routes=(SECTION_G,)),
    line(
        63,
        23,
        C,
        "p63_g14_own_sickness",
        routes=(SECTION_G,),
        note="G14 prints the own-sickness work-time-missed field.",
    ),
    line(63, 23, P, "p63_g14_prompt", routes=(SECTION_G,)),
    line(
        63,
        28,
        F,
        "p63_flow_go_g16",
        routes=(SECTION_G,),
        note="G14 no-branch routing atom to G16.",
    ),
    line(
        63,
        30,
        C,
        "p63_g15_missed_amount",
        routes=(SECTION_G,),
        note="G15 prints the work-time-missed amount.",
    ),
    line(63, 30, P, "p63_g15_prompt", routes=(SECTION_G,)),
    line(
        63,
        38,
        C,
        "p63_g16_strike",
        routes=(SECTION_G,),
        note="G16 prints the strike work-time-missed field.",
    ),
    line(63, 38, P, "p63_g16_prompt", routes=(SECTION_G,)),
    line(
        63,
        42,
        C,
        "p63_g17_missed_amount",
        routes=(SECTION_G,),
        note="G17 prints the work-time-missed amount.",
    ),
    line(63, 42, P, "p63_g17_prompt", routes=(SECTION_G,)),
    block(
        63,
        47,
        48,
        C,
        "p63_g18_unemployment",
        routes=(SECTION_G,),
        note="G18 prints the unemployment/layoff work-time-missed field.",
    ),
    block(63, 47, 48, P, "p63_g18_prompt", routes=(SECTION_G,)),
    line(
        63,
        49,
        F,
        "p63_flow_go_g20",
        routes=(SECTION_G,),
        note="G18 no-branch routing atom to G20.",
    ),
    line(
        63,
        52,
        C,
        "p63_g19_missed_amount",
        routes=(SECTION_G,),
        note="G19 prints the work-time-missed amount.",
    ),
    line(63, 52, P, "p63_g19_prompt", routes=(SECTION_G,)),
    word(
        63,
        57,
        "main job",
        J,
        "p63_g20_main_job",
        routes=(SECTION_G,),
        note="G20 prints the wife's 1980 main job as a distinct job anchor "
        "inside the unemployed-wife schedule.",
    ),
    line(
        63,
        57,
        C,
        "p63_g20_weeks",
        parents=("p63_g20_main_job",),
        routes=(SECTION_G,),
        note="G20 prints weeks actually worked on that main job.",
    ),
    line(63, 57, P, "p63_g20_prompt", routes=(SECTION_G,)),
    line(
        63,
        61,
        C,
        "p63_g22_hours",
        parents=("p63_g20_main_job",),
        routes=(SECTION_G,),
        note="G22 prints average hours per week worked.",
    ),
    line(63, 61, P, "p63_g22_prompt", routes=(SECTION_G,)),
)

SECTION_H = ("p67_flow_section_h",)

# Page 67 - section H entry and items H1-H12.  The printed entry route from
# F2 is destroyed by the scan, so the header itself roots this branch.
PAGE_67 = (
    line(
        67,
        3,
        F,
        "p67_flow_section_h",
        note="Printed section H header conditions the out-of-labor-force "
        "wife schedule.",
    ),
    word(67, 3, "WIFE", R, "p67_role_wife", routes=(SECTION_H,)),
    line(
        67,
        7,
        F,
        "p67_flow_h1_retired",
        routes=(SECTION_H,),
        note="H1 checkpoint alternative for a retired wife.",
    ),
    line(
        67,
        9,
        F,
        "p67_flow_h1_other",
        routes=(SECTION_H,),
        note="H1 checkpoint alternative for a housekeeping, student, or "
        "disabled wife.",
    ),
    line(
        67,
        10,
        C,
        "p67_h2_retirement_year",
        routes=(("p67_flow_section_h", "p67_flow_h1_retired"),),
        note="H2 prints the wife retirement year, an exposure boundary "
        "field.",
    ),
    line(
        67,
        10,
        P,
        "p67_h2_prompt",
        routes=(("p67_flow_section_h", "p67_flow_h1_retired"),),
    ),
    line(
        67,
        12,
        C,
        "p67_h3_any_work",
        routes=(SECTION_H,),
        note="H3 prints the any-work-for-money assignment field for 1980.",
    ),
    line(67, 12, P, "p67_h3_prompt", routes=(SECTION_H,)),
    line(
        67,
        14,
        C,
        "p67_h4_occupation",
        routes=(SECTION_H,),
        note="H4 prints the occupation field for that work.",
    ),
    line(67, 14, P, "p67_h4_prompt", routes=(SECTION_H,)),
    line(
        67,
        18,
        C,
        "p67_h5_industry",
        routes=(SECTION_H,),
        note="H5 prints the business-or-industry field for that work.",
    ),
    line(67, 18, P, "p67_h5_prompt", routes=(SECTION_H,)),
    line(
        67,
        22,
        C,
        "p67_h6_weeks",
        routes=(SECTION_H,),
        note="H6 prints weeks worked last year.",
    ),
    line(67, 22, P, "p67_h6_prompt", routes=(SECTION_H,)),
    line(
        67,
        25,
        C,
        "p67_h7_hours",
        routes=(SECTION_H,),
        note="H7 prints hours per week worked.",
    ),
    line(67, 25, P, "p67_h7_prompt", routes=(SECTION_H,)),
    line(
        67,
        27,
        C,
        "p67_h8_still_working",
        routes=(SECTION_H,),
        note="H8 prints the still-working assignment field.",
    ),
    line(67, 27, P, "p67_h8_prompt", routes=(SECTION_H,)),
)

SECTION_K = ("p77_flow_section_k",)
K_FARMER = ("p77_flow_section_k", "p77_flow_k1a_farmer")

# Page 77 - first scan of section K income items K1-K10.
PAGE_77 = (
    line(
        77,
        2,
        F,
        "p77_flow_section_k",
        note="Printed section K header opens the universal income schedule.",
    ),
    block(
        77,
        8,
        9,
        A,
        "p77_k1_employment_cross_reference",
        routes=(SECTION_K,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="The K1 interviewer rule explicitly binds every K2-K11c dollar "
        "amount to work hours and weeks recorded in an employment section.",
    ),
    line(
        77,
        17,
        F,
        "p77_flow_k1a_farmer",
        routes=(SECTION_K,),
        note="K1a checkpoint alternative conditioning the K2-K4 farm block.",
    ),
    word(
        77,
        18,
        "FARMER",
        FA,
        "p77_k1a_farm_aggregate",
        routes=(SECTION_K,),
        note="K1a prints the farm/ranch operation that aggregates the K2-K4 "
        "farm amounts.",
    ),
    line(
        77,
        18,
        F,
        "p77_flow_k1a_not_farmer",
        routes=(SECTION_K,),
        note="K1a checkpoint alternative routing a nonfarm head to K5.",
    ),
    word(
        77,
        21,
        "total receipts",
        M,
        "p77_k2_farm_receipts",
        parents=("p77_k1a_farm_aggregate",),
        routes=(K_FARMER,),
        note="K2 prints total farm receipts as a farm remuneration "
        "component.",
    ),
    block(77, 21, 22, P, "p77_k2_prompt", routes=(K_FARMER,)),
    block(
        77,
        24,
        25,
        M,
        "p77_k3_farm_expenses",
        parents=("p77_k1a_farm_aggregate",),
        routes=(K_FARMER,),
        note="K3 prints total farm operating expenses, the deduction leg of "
        "the farm net amount.",
    ),
    block(77, 24, 25, P, "p77_k3_prompt", routes=(K_FARMER,)),
    block(77, 32, 33, P, "p77_k5_prompt", routes=(SECTION_K,)),
    word(
        77,
        37,
        "unincorporated business",
        BA,
        "p77_k6_business_aggregate",
        routes=(SECTION_K,),
        note="K6 prints the business enterprise that aggregates the K7 "
        "business amount.",
    ),
    line(
        77,
        37,
        C,
        "p77_k6_incorporation",
        parents=("p77_k6_business_aggregate",),
        routes=(SECTION_K,),
        note="K6 prints the incorporation-status field.",
    ),
    line(77, 37, P, "p77_k6_prompt", routes=(SECTION_K,)),
    block(
        77,
        42,
        43,
        M,
        "p77_k7_business_income",
        parents=("p77_k6_business_aggregate",),
        routes=(SECTION_K,),
        note="K7 prints the family share of total business income.",
    ),
    block(77, 42, 43, P, "p77_k7_prompt", routes=(SECTION_K,)),
    word(
        77,
        48,
        "wages and salaries",
        M,
        "p77_k8_wages",
        routes=(SECTION_K,),
        note="K8 prints the head's 1980 wage and salary component before "
        "deductions.",
    ),
    block(77, 48, 49, P, "p77_k8_prompt", routes=(SECTION_K,)),
    line(
        77,
        53,
        M,
        "p77_k9_bonuses",
        routes=(SECTION_K,),
        note="K9 prints the bonus, overtime, tip, and commission component.",
    ),
    line(77, 53, P, "p77_k9_prompt", routes=(SECTION_K,)),
    line(77, 59, P, "p77_k10_prompt", routes=(SECTION_K,)),
)

# Page 79 - second scan of section K income items K1-K10.
PAGE_79 = (
    block(
        79,
        8,
        9,
        A,
        "p79_k1_employment_cross_reference",
        routes=(SECTION_K,),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Second scan of the K1 interviewer rule binding K2-K11c dollars "
        "to employment-section work hours and weeks.",
    ),
    block(
        79,
        18,
        19,
        M,
        "p79_k2_farm_receipts",
        routes=(SECTION_K,),
        note="K2 prints total farm receipts on the second scan; the K1a farm "
        "checkpoint is absent from this scan, so no printed parent aggregate "
        "is bound here.",
    ),
    block(79, 18, 19, P, "p79_k2_prompt", routes=(SECTION_K,)),
    block(
        79,
        21,
        22,
        M,
        "p79_k3_farm_expenses",
        routes=(SECTION_K,),
        note="K3 prints total farm operating expenses on the second scan.",
    ),
    block(79, 21, 22, P, "p79_k3_prompt", routes=(SECTION_K,)),
    line(
        79,
        25,
        M,
        "p79_k4_farm_net",
        routes=(SECTION_K,),
        note="K4 prints the net farm amount as receipts minus operating "
        "expenses.",
    ),
    line(79, 25, P, "p79_k4_prompt", routes=(SECTION_K,)),
    block(79, 27, 28, P, "p79_k5_prompt", routes=(SECTION_K,)),
    word(
        79,
        33,
        "business",
        BA,
        "p79_k6_business_aggregate",
        routes=(SECTION_K,),
        note="Second scan of the K6 business enterprise anchor.",
    ),
    line(
        79,
        33,
        C,
        "p79_k6_incorporation",
        parents=("p79_k6_business_aggregate",),
        routes=(SECTION_K,),
        note="K6 prints the incorporation-status field.",
    ),
    line(79, 33, P, "p79_k6_prompt", routes=(SECTION_K,)),
    block(
        79,
        42,
        43,
        M,
        "p79_k7_business_income",
        parents=("p79_k6_business_aggregate",),
        routes=(SECTION_K,),
        note="K7 prints the family share of total business income.",
    ),
    block(79, 42, 43, P, "p79_k7_prompt", routes=(SECTION_K,)),
    word(
        79,
        48,
        "salaries",
        M,
        "p79_k8_salaries",
        routes=(SECTION_K,),
        note="K8 prints the head's 1980 salary component; this scan drops "
        "the leading wage lexeme, so the exact retained slice is the printed "
        "salaries token.",
    ),
    block(79, 48, 49, P, "p79_k8_prompt", routes=(SECTION_K,)),
    line(
        79,
        53,
        M,
        "p79_k9_bonuses",
        routes=(SECTION_K,),
        note="K9 prints the bonus, overtime, tip, and commission component.",
    ),
    line(79, 53, P, "p79_k9_prompt", routes=(SECTION_K,)),
    line(79, 59, P, "p79_k10_prompt", routes=(SECTION_K,)),
)

# Page 81 - first scan of the K11 other-income grid.  Only the work-linked
# items a, b, and c are remuneration components; the dividend, welfare, and
# supplemental-security rows are transfers or asset income.
PAGE_81 = (
    word(
        81,
        7,
        "professional practice or trade",
        M,
        "p81_k11a_professional_practice",
        routes=(SECTION_K,),
        note="K11a prints self-employed professional practice or trade "
        "income.",
    ),
    block(81, 6, 7, P, "p81_k11_prompt", routes=(SECTION_K,)),
    line(
        81,
        11,
        C,
        "p81_k13_duration",
        routes=(SECTION_K,),
        note="The grid's duration column prints how much of 1980 each "
        "retained K11 component was received.",
    ),
    line(81, 11, P, "p81_k13_prompt", routes=(SECTION_K,)),
    line(
        81,
        12,
        P,
        "p81_k12_prompt",
        routes=(SECTION_K,),
        note="The grid's amount column prints the how-much question for each "
        "retained K11 component.",
    ),
    block(
        81,
        21,
        22,
        M,
        "p81_k11b_farming",
        routes=(SECTION_K,),
        note="K11b prints farming or market-gardening income for a head "
        "whose main income is not farming.",
    ),
    block(81, 21, 22, P, "p81_k11b_prompt", routes=(SECTION_K,)),
    word(
        81,
        39,
        "roomers or boarders",
        M,
        "p81_k11c_roomers",
        routes=(SECTION_K,),
        note="K11c prints net roomer/boarder income, which the printed rule "
        "ties to employment-section work hours.",
    ),
    line(81, 39, P, "p81_k11c_prompt", routes=(SECTION_K,)),
)

# Page 83 - second scan of the K11 other-income grid.
PAGE_83 = (
    word(
        83,
        8,
        "professional practice or trade",
        M,
        "p83_k11a_professional_practice",
        routes=(SECTION_K,),
        note="Second scan of the K11a professional practice or trade "
        "component.",
    ),
    line(83, 8, P, "p83_k11_prompt", routes=(SECTION_K,)),
    line(
        83,
        10,
        C,
        "p83_k13_duration",
        routes=(SECTION_K,),
        note="Second scan of the grid duration column.",
    ),
    line(83, 10, P, "p83_k13_prompt", routes=(SECTION_K,)),
    line(
        83,
        11,
        P,
        "p83_k12_prompt",
        routes=(SECTION_K,),
        note="Second scan of the grid amount column.",
    ),
    block(
        83,
        27,
        28,
        M,
        "p83_k11b_farming",
        routes=(SECTION_K,),
        note="Second scan of the K11b farming or market-gardening "
        "component.",
    ),
    block(83, 27, 28, P, "p83_k11b_prompt", routes=(SECTION_K,)),
    word(
        83,
        38,
        "ro omers or boarders",
        M,
        "p83_k11c_roomers",
        routes=(SECTION_K,),
        note="Second scan of the K11c roomer/boarder component.",
    ),
    line(83, 38, P, "p83_k11c_prompt", routes=(SECTION_K,)),
)

# Page 89 - wife income items K19-K29.
PAGE_89 = (
    word(89, 5, "HEAD", R, "p89_role_head", routes=(SECTION_K,)),
    word(89, 5, "WIFE", R, "p89_role_wife", routes=(SECTION_K,)),
    line(
        89,
        5,
        F,
        "p89_flow_k19_a",
        routes=(SECTION_K,),
        note="K19 checkpoint alternative A conditions the wife income "
        "block.",
    ),
    line(
        89,
        7,
        F,
        "p89_flow_k19_b",
        routes=(SECTION_K,),
        note="K19 checkpoint alternative B routes past the wife income "
        "block.",
    ),
    line(
        89,
        8,
        F,
        "p89_flow_k19_c",
        routes=(SECTION_K,),
        note="K19 checkpoint alternative C routes past the wife income "
        "block.",
    ),
    line(
        89,
        11,
        T,
        "p89_k20_wife_total",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
        note="K20 prints the wife's total 1980 income, the role-total "
        "anchor of the wife income block.",
    ),
    line(
        89,
        11,
        P,
        "p89_k20_prompt",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
    ),
    line(
        89,
        13,
        F,
        "p89_flow_k20_no",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
        note="K20 no-branch routing atom past the wife income block.",
    ),
    line(
        89,
        24,
        M,
        "p89_k22_wife_amount",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
        note="K22 prints the wife's 1980 pre-deduction amount; the K21 stem "
        "naming its wage source is truncated by the scan, so the retained "
        "slice is the printed amount field the K21 rule binds to employment "
        "work hours.",
    ),
    line(
        89,
        24,
        P,
        "p89_k22_prompt",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
    ),
    block(
        89,
        16,
        17,
        A,
        "p89_k21_employment_cross_reference",
        routes=(("p77_flow_section_k", "p89_flow_k19_a"),),
        relation="explicit_cross_reference",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="The K21 interviewer rule explicitly binds every K21-K29 dollar "
        "amount to work hours and weeks in an employment section.",
    ),
)

SECTION_L = ("p113_flow_section_l",)
SECTION_M = ("p115_flow_section_m",)

# Page 113 - section L new wife.  Only the L11-L12 lifetime-work fields are
# R_Q source; the schooling items are outside the domain.
PAGE_113 = (
    line(
        113,
        3,
        F,
        "p113_flow_section_l",
        note="Printed section L header conditions the new-wife schedule.",
    ),
    word(113, 7, "HEAD", R, "p113_role_head", routes=(SECTION_L,)),
    word(113, 7, "WIFE", R, "p113_role_wife", routes=(SECTION_L,)),
    line(
        113,
        7,
        F,
        "p113_flow_l1_new_wife",
        routes=(SECTION_L,),
        note="L1 checkpoint alternative conditioning the new-wife schedule.",
    ),
    line(
        113,
        9,
        F,
        "p113_flow_l1_female_head",
        routes=(SECTION_L,),
        note="L1 checkpoint alternative routing a female head to section M.",
    ),
    line(
        113,
        11,
        F,
        "p113_flow_l1_no_wife",
        routes=(SECTION_L,),
        note="L1 checkpoint alternative routing a wifeless head to "
        "section M.",
    ),
    line(
        113,
        13,
        F,
        "p113_flow_l1_same_wife",
        routes=(SECTION_L,),
        note="L1 checkpoint alternative routing an unchanged wife to "
        "section M.",
    ),
    line(
        113,
        44,
        C,
        "p113_l11_full_time_years",
        routes=(("p113_flow_section_l", "p113_flow_l1_new_wife"),),
        note="L11 prints the wife's lifetime full-time work years.",
    ),
    line(
        113,
        44,
        P,
        "p113_l11_prompt",
        routes=(("p113_flow_section_l", "p113_flow_l1_new_wife"),),
    ),
    line(
        113,
        47,
        C,
        "p113_l12_part_year_work",
        routes=(("p113_flow_section_l", "p113_flow_l1_new_wife"),),
        note="L12 prints how much of each non-full-time year the wife "
        "worked.",
    ),
    line(
        113,
        47,
        P,
        "p113_l12_prompt",
        routes=(("p113_flow_section_l", "p113_flow_l1_new_wife"),),
    ),
)

# Page 115 - section M new head; M4 prints the head's first full-time job.
PAGE_115 = (
    line(
        115,
        3,
        F,
        "p115_flow_section_m",
        note="Printed section M header conditions the new-head schedule.",
    ),
    word(115, 7, "HEAD", R, "p115_role_head", routes=(SECTION_M,)),
    line(
        115,
        7,
        F,
        "p115_flow_m1_new_head",
        routes=(SECTION_M,),
        note="M1 checkpoint alternative conditioning the new-head schedule.",
    ),
    line(
        115,
        8,
        F,
        "p115_flow_m1_same_head",
        routes=(SECTION_M,),
        note="M1 checkpoint alternative routing an unchanged head out of "
        "the schedule.",
    ),
    word(
        115,
        41,
        "full-time regular job",
        J,
        "p115_m4_first_job",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M4 prints the head's first full-time regular job as a distinct "
        "lifetime job anchor.",
    ),
    line(
        115,
        41,
        C,
        "p115_m4_occupation",
        parents=("p115_m4_first_job",),
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M4 prints the first-job occupation field.",
    ),
    line(
        115,
        41,
        P,
        "p115_m4_prompt",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
    ),
    block(
        115,
        65,
        66,
        C,
        "p115_m5_occupation_history",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M5 prints whether the head held several occupations or stayed "
        "in one.",
    ),
    block(
        115,
        65,
        66,
        P,
        "p115_m5_prompt",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
    ),
)

# Page 119 - new-head lifetime-work items M26-M27.
PAGE_119 = (
    line(
        119,
        22,
        C,
        "p119_m26_full_time_years",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M26 prints the head's lifetime full-time work years.",
    ),
    line(
        119,
        22,
        P,
        "p119_m26_prompt",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
    ),
    word(
        119,
        24,
        "GO TO M28",
        F,
        "p119_flow_go_m28",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M26 routing atom to M28; the scan merges the answer column, so "
        "the exact directive is selected.",
    ),
    line(
        119,
        27,
        C,
        "p119_m27_part_year_work",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
        note="M27 prints how much of each non-full-time year the head "
        "worked.",
    ),
    line(
        119,
        27,
        P,
        "p119_m27_prompt",
        routes=(("p115_flow_section_m", "p115_flow_m1_new_head"),),
    ),
)

REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_15,
    *PAGE_17,
    *PAGE_19,
    *PAGE_21,
    *PAGE_23,
    *PAGE_25,
    *PAGE_27,
    *PAGE_29,
    *PAGE_31,
    *PAGE_37,
    *PAGE_39,
    *PAGE_41,
    *PAGE_43,
    *PAGE_45,
    *PAGE_49,
    *PAGE_51,
    *PAGE_53,
    *PAGE_55,
    *PAGE_57,
    *PAGE_59,
    *PAGE_61,
    *PAGE_63,
    *PAGE_67,
    *PAGE_77,
    *PAGE_79,
    *PAGE_81,
    *PAGE_83,
    *PAGE_89,
    *PAGE_113,
    *PAGE_115,
    *PAGE_119,
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
            if len(paths) != 1:
                raise SpecError(
                    f"{row['key']} is a multi-parent label; this review "
                    "records exactly one parent path per routing atom"
                )
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
                "all_114_pages_including_empty_occurrence_pages"
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
        f"document 27 source review: {len(review['occurrence_specs'])} "
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
