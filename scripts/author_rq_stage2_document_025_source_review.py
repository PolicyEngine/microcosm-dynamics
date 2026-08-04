#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 25.

``fam1980_QxQs.pdf`` is a 114-page scan that interleaves the printed 1980
family instrument with its question-by-question interviewer objectives: every
odd page is an instrument screen and every even page is the facing objectives
sheet.  All 114 pages were read from the authenticated Poppler text before
this file was written, and the stage-1 candidate artifact is never opened
here; the sealed annotation builder joins candidates only after these reviewer
rows exist.

Reviewer scope decisions recorded by this file:

* Occurrences are emitted only on printed *instrument* screens inside the
  retained employment, work-income, and lifetime-work-history regions.  The
  question-by-question objective pages are interviewer commentary keyed to a
  question; they restate worklike vocabulary but print no field, so they carry
  no source occurrence.
* Cover, transportation, housing/utility, residential-mobility, housework,
  food and food-stamp, extra-earner, other-family-member, medical, dependent
  support, emergency-help, savings, schooling, growing-up, religion, and
  observation regions contribute no occurrence merely because nearby prose
  contains worklike words.
* A retained ``context_anchor`` must print a field that maps to a ratified
  section-19 field purpose (assignment, occupation, industry, employee/self,
  government level, incorporation, job identifier, reporting unit, or
  month/exposure).  Labour-union membership, commuting, counterfactual
  labour-supply preference, job-search effort, training-requirement,
  residential-mobility willingness, health-limitation, and schooling fields
  are printed work-adjacent questions that map to no such purpose and are
  rejected.
* A retained ``job_anchor`` establishes a distinct printed job for the role.
  A later back-reference to a job already established on the same screen is
  rejected rather than promoted to a second job or an inferred alias.
* A screen is retained if and only if it prints at least one retained field.
  On a retained screen every legible printed routing directive and printed
  conditional label is also retained; on a screen that prints no retained
  field nothing is retained, including its routing directives.
* An occurrence's applicable path set is the ancestry of the printed block in
  which it is administered: the section-header branch, extended by each
  printed conditional label (interviewer checkpoint or printed condition) that
  encloses it.  A printed forward routing atom is itself a branch label, but
  it does not re-parent the screen it jumps to, because that screen is
  administered identically on fall-through.
* OCR-destroyed answer labels and routing fragments are never reconstructed.
  A routing atom is retained only where the printed bytes still separate its
  directive verb from its target.
* The 1980 manual reprints three instrument screens on continuation sheets
  that carry a printed ``(CON'T.)`` marker (pages 69, 73, and 77).  Each
  reprint is a distinct printed occurrence at distinct coordinates and is
  annotated separately; the reprinted section K header opens its own root
  branch, under which the reprinted screens resolve.
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


def resolve_tail(
    page_text: str, line_number: int, needle: str, occurrence: int = 0
) -> tuple[int, int]:
    """Span from a printed needle to the end of its physical line.

    The 1980 instrument prints its section headers on a line that also
    carries the printed screen number, so a whole-line span would swallow an
    unrelated token.  This selector keeps the exact printed header bytes.
    """

    start, _ = resolve_needle(page_text, line_number, needle, occurrence)
    return start, resolve_line(page_text, line_number)[1]


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
    1: _INSTRUMENT_OUT.format(
        "the interviewer face sheet, office-use box, and section A "
        "transportation items A1-A3"
    ),
    2: _OBJECTIVES.format("face-sheet items 1-7 and section A items A1-A3"),
    3: _INSTRUMENT_OUT.format("section A transportation items A4-A9"),
    4: _OBJECTIVES.format("section A items A4-A9"),
    5: _INSTRUMENT_OUT.format(
        "section B housing, utility, and mortgage items B1-B13"
    ),
    6: _OBJECTIVES.format("section B items B1-B13"),
    7: _INSTRUMENT_OUT.format("section B rent and utility items B14-B22"),
    8: _OBJECTIVES.format("section B items B14-B22"),
    9: _INSTRUMENT_OUT.format("section B residential-mobility items B23-B28"),
    10: _OBJECTIVES.format("section B items B23-B28"),
    11: _INSTRUMENT_IN.format(
        "the section C header and head employment items C1-C5"
    ),
    12: _OBJECTIVES.format("the section C header and item C1"),
    13: _INSTRUMENT_IN.format("head employment items C6-C15"),
    14: _OBJECTIVES.format("items C6-C15"),
    15: _INSTRUMENT_IN.format("head work-time items C16-C23"),
    16: _OBJECTIVES.format("items C16-C23"),
    17: _INSTRUMENT_IN.format("head work-time and main-job items C24-C29"),
    18: _OBJECTIVES.format("items C30-C37, whose instrument screen is absent"),
    19: _INSTRUMENT_IN.format("head extra-job items C38-C47"),
    20: _OBJECTIVES.format("items C38-C47"),
    21: _INSTRUMENT_NONE.format(
        "head items C48-C53",
        "a counterfactual labour-supply preference or a commuting field, "
        "neither of which maps to a ratified section-19 field purpose",
    ),
    22: _OBJECTIVES.format("items C48-C53"),
    23: _INSTRUMENT_NONE.format(
        "head items C54-C57",
        "a job-search intention or a residential-mobility willingness field, "
        "neither of which maps to a ratified section-19 field purpose",
    ),
    24: _OBJECTIVES.format("items C54-C57"),
    25: _INSTRUMENT_IN.format(
        "the section D header and head job-search items D1-D6"
    ),
    26: _OBJECTIVES.format("the section D header and items D1-D6"),
    27: _INSTRUMENT_IN.format("head last-job items D7-D15"),
    28: _OBJECTIVES.format("items D7-D14"),
    29: _INSTRUMENT_IN.format("head work-time items D16-D24"),
    30: _OBJECTIVES.format("items D16-D23"),
    31: _INSTRUMENT_IN.format("head work-time items D25-D31"),
    32: _OBJECTIVES.format("items D27-D31"),
    33: _INSTRUMENT_IN.format(
        "the section E header and head out-of-labour-force items E1-E9"
    ),
    34: _OBJECTIVES.format("the section E header and items E1-E9"),
    35: _INSTRUMENT_NONE.format(
        "head items E10-E15",
        "a future-job intention, a training-requirement, or a job-search "
        "effort field, none of which maps to a ratified section-19 field "
        "purpose",
    ),
    36: _OBJECTIVES.format("items E10-E15"),
    37: _INSTRUMENT_IN.format(
        "the section F header and wife/friend employment items F1-F6"
    ),
    38: _OBJECTIVES.format("the section F header and items F1-F6"),
    39: _INSTRUMENT_IN.format("wife/friend employment items F7-F13"),
    40: _OBJECTIVES.format("items F7-F13"),
    41: _INSTRUMENT_IN.format("wife/friend work-time items F14-F23"),
    42: _OBJECTIVES.format("items F14-F23"),
    43: _INSTRUMENT_IN.format("wife/friend work-time and pay items F24-F31"),
    44: _OBJECTIVES.format("items F24-F31"),
    45: _INSTRUMENT_IN.format("wife/friend extra-job items F32-F38"),
    46: _OBJECTIVES.format("items F32-F38"),
    47: _INSTRUMENT_IN.format(
        "the section G header and wife/friend job-search items G1-G9"
    ),
    48: _OBJECTIVES.format("the section G header and items G1-G9"),
    49: _INSTRUMENT_IN.format("wife/friend work-time items G10-G18"),
    50: _OBJECTIVES.format("items G10-G18"),
    51: _INSTRUMENT_IN.format("wife/friend work-time items G19-G25"),
    52: _OBJECTIVES.format("items G19-G25"),
    53: _INSTRUMENT_IN.format(
        "the section H header and wife/friend out-of-labour-force items H1-H9"
    ),
    54: _OBJECTIVES.format("the section H header and items H1-H9"),
    55: _INSTRUMENT_NONE.format(
        "wife/friend items H10-H12",
        "a future-job intention or a job-search effort field, neither of "
        "which maps to a ratified section-19 field purpose",
    ),
    56: _OBJECTIVES.format("items H10-H12"),
    57: _INSTRUMENT_OUT.format(
        "the section J header and marital-status and housework-hour items "
        "J1-J6"
    ),
    58: _OBJECTIVES.format("the section J header and items J1-J4"),
    59: _INSTRUMENT_OUT.format("section J housework-helper items J7-J11"),
    60: _OBJECTIVES.format("items J7-J11"),
    61: _INSTRUMENT_OUT.format("section J food-stamp and food items J12-J19"),
    62: _OBJECTIVES.format("items J12-J19"),
    63: _INSTRUMENT_OUT.format("section J food and food-stamp items J20-J26"),
    64: _OBJECTIVES.format("items J20-J26"),
    65: _INSTRUMENT_OUT.format(
        "section J food-stamp eligibility items J27-J31"
    ),
    66: _OBJECTIVES.format("items J27-J31"),
    67: _INSTRUMENT_IN.format(
        "the section K header and family work-income items K1-K10"
    ),
    68: _OBJECTIVES.format("the section K header and items K1-K6"),
    69: _INSTRUMENT_IN.format(
        "the reprinted section K header and items K1-K10, printed a second "
        'time under the "(CON\'T.)" screen marker'
    ),
    70: _OBJECTIVES.format("items K7-K10"),
    71: _INSTRUMENT_IN.format("other-income items K11-K17"),
    72: _OBJECTIVES.format("items K11-K13 and their lettered rows"),
    73: _INSTRUMENT_IN.format(
        'items K11-K17, printed a second time under the "(CON\'T.)" screen '
        "marker"
    ),
    74: _OBJECTIVES.format("items K11e-K11f and K15-K18"),
    75: _INSTRUMENT_NONE.format(
        "items K18-K24",
        "a transfer, welfare, pension, or outside-help receipt rather than a "
        "remuneration component or coverage context",
    ),
    76: _OBJECTIVES.format("items K18-K20 and their lettered rows"),
    77: _INSTRUMENT_NONE.format(
        'items K18-K24, printed a second time under the "(CON\'T.)" screen '
        "marker",
        "a transfer, welfare, pension, or outside-help receipt rather than a "
        "remuneration component or coverage context",
    ),
    78: _OBJECTIVES.format("items K20f-K24"),
    79: _INSTRUMENT_IN.format("wife/friend income items K25-K35"),
    80: _OBJECTIVES.format("items K26-K35"),
    81: _INSTRUMENT_OUT.format(
        "the extra-earner prelist grid and checkpoint items K36-K37, whose "
        "listed persons are neither the head nor the spouse role"
    ),
    82: _OBJECTIVES.format("the extra-earner grid items K36-K37"),
    83: _INSTRUMENT_OUT.format(
        "first extra-earner items K38-K47, whose subject is neither the head "
        "nor the spouse role"
    ),
    84: _OBJECTIVES.format("extra-earner items K38-K47"),
    85: _INSTRUMENT_OUT.format(
        "extra-earner items K48-K53, whose subject is neither the head nor "
        "the spouse role"
    ),
    86: _OBJECTIVES.format("extra-earner items K48-K52"),
    87: _INSTRUMENT_OUT.format(
        "other-family-member income items K54-K59, whose subjects are "
        "neither the head nor the spouse role"
    ),
    88: _OBJECTIVES.format("items K54-K59"),
    89: _INSTRUMENT_OUT.format(
        "medical-insurance and lump-sum receipt items K60-K65"
    ),
    90: _OBJECTIVES.format("items K60-K65"),
    91: _INSTRUMENT_OUT.format(
        "outside-dependent support and emergency-help items K66-K76"
    ),
    92: _OBJECTIVES.format("items K66-K76"),
    93: _INSTRUMENT_OUT.format("emergency-help items K77-K84"),
    94: _OBJECTIVES.format("items K78-K84"),
    95: _INSTRUMENT_OUT.format("savings and emergency-money items K85-K91"),
    96: _OBJECTIVES.format("items K85-K91"),
    97: _INSTRUMENT_OUT.format("loan and gift items K92-K97"),
    98: _OBJECTIVES.format("items K92-K97"),
    99: _INSTRUMENT_OUT.format(
        "loan, gift, and price-increase items K98-K106"
    ),
    100: _OBJECTIVES.format("items K98-K106"),
    101: _INSTRUMENT_NONE.format(
        "items K107-K113",
        "a retirement-expectation, labour-union membership, or "
        "work-limiting health field, none of which maps to a ratified "
        "section-19 field purpose",
    ),
    102: _OBJECTIVES.format("items K107-K113"),
    103: _INSTRUMENT_IN.format(
        "the section L header and new-wife items L1-L12"
    ),
    104: _OBJECTIVES.format("the section L header and items L1-L12"),
    105: _INSTRUMENT_IN.format(
        "the section M header and new-head items M1-M5"
    ),
    106: _OBJECTIVES.format("the section M header and items M1-M5"),
    107: _INSTRUMENT_OUT.format(
        "new-head fertility, sibling, and growing-up items M6-M16"
    ),
    108: _OBJECTIVES.format("items M6-M16"),
    109: _INSTRUMENT_IN.format("new-head items M17-M27"),
    110: _OBJECTIVES.format("items M17-M27"),
    111: _INSTRUMENT_OUT.format(
        "new-head schooling and religious-preference items M28-M40"
    ),
    112: _OBJECTIVES.format("items M28-M40"),
    113: _INSTRUMENT_OUT.format(
        "the section N observation-only items N1-N2 and the thumbnail sketch"
    ),
    114: _OBJECTIVES.format("the section N observation-only items"),
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

SECTION_C = ("p11_flow_section_c",)
C10_LESS = SECTION_C + ("p13_flow_c10_less_than_year",)
_JOB_NOTE = (
    "Parent is the section's single printed current-job anchor, which "
    "governs this screen's occupation, industry, tenure, and work-time "
    "fields."
)

# Page 11 - section C entry and head employment items C1-C5.
PAGE_11 = (
    tail(
        11,
        2,
        "SECTION C:",
        F,
        "p11_flow_section_c",
        note="Printed section C header conditions the head employment "
        "schedule selected at C1.",
    ),
    word(11, 2, "HEAD", R, "p11_role_head_header", routes=(SECTION_C,)),
    block(
        11,
        5,
        6,
        C,
        "p11_c1_assignment",
        routes=(SECTION_C,),
        note="C1 prints the head labour-force assignment field.",
    ),
    block(11, 5, 6, P, "p11_c1_prompt", routes=(SECTION_C,)),
    word(11, 5, "HEAD", R, "p11_role_head_c1", routes=(SECTION_C,)),
    word(
        11,
        18,
        "TURr~TO P. 14 ,",
        F,
        "p11_flow_c1_turn_section_d",
        routes=(SECTION_C,),
        note="C1 routing atom into the section D schedule.",
    ),
    tail(
        11,
        23,
        "TURN TO P. 18,",
        F,
        "p11_flow_c1_turn_section_e",
        routes=(SECTION_C,),
        note="C1 routing atom into the section E schedule.",
    ),
    tail(
        11,
        31,
        "GO TO C2",
        F,
        "p11_flow_c1_head_has_job",
        routes=(SECTION_C,),
        note="C1 conditional routing atom that predicates the remaining "
        "section C screens on the head holding a job.",
    ),
    tail(
        11,
        32,
        "TURN TO P. 18,",
        F,
        "p11_flow_c1_no_job_section_e",
        routes=(SECTION_C,),
    ),
    line(
        11,
        37,
        C,
        "p11_c2_employee_self",
        routes=(SECTION_C,),
        note="C2 prints the employee/self-employed field.",
    ),
    line(11, 37, P, "p11_c2_prompt", routes=(SECTION_C,)),
    tail(
        11,
        41,
        "TURN TO P. 7 , C6",
        F,
        "p11_flow_c2_self_only",
        routes=(SECTION_C,),
    ),
    block(
        11,
        44,
        45,
        C,
        "p11_c3_government",
        routes=(SECTION_C,),
        note="C3 prints the federal/state/local government-level field.",
    ),
    block(11, 44, 45, P, "p11_c3_prompt", routes=(SECTION_C,)),
    tail(
        11,
        57,
        "TURN   TO P. 7, C6",
        F,
        "p11_flow_c5_union_exit",
        routes=(SECTION_C,),
    ),
)

# Page 13 - head occupation, industry, tenure, and previous-job items.
PAGE_13 = (
    line(
        13,
        1,
        C,
        "p13_c6_occupation",
        routes=(SECTION_C,),
        note="C6 prints the head main-occupation field.",
    ),
    line(13, 1, P, "p13_c6_prompt", routes=(SECTION_C,)),
    line(13, 3, P, "p13_c6_probe_prompt", routes=(SECTION_C,)),
    line(
        13,
        8,
        C,
        "p13_c7_occupation_detail",
        routes=(SECTION_C,),
        note="C7 prints the occupation-detail probe field.",
    ),
    line(13, 8, P, "p13_c7_prompt", routes=(SECTION_C,)),
    line(
        13,
        13,
        C,
        "p13_c8_industry",
        routes=(SECTION_C,),
        note="C8 prints the business-or-industry field.",
    ),
    line(13, 13, P, "p13_c8_prompt", routes=(SECTION_C,)),
    line(
        13,
        17,
        C,
        "p13_c9_tenure",
        routes=(SECTION_C,),
        note="C9 prints the current-position tenure field.",
    ),
    line(13, 17, P, "p13_c9_prompt", routes=(SECTION_C,)),
    word(
        13,
        17,
        "present position",
        J,
        "p13_job_present_position",
        routes=(SECTION_C,),
        note="C9 names the head's current job by its printed job noun.",
    ),
    line(
        13,
        23,
        F,
        "p13_flow_c10_less_than_year",
        routes=(SECTION_C,),
        note="C10 checkpoint label opening the short-tenure block C11-C15.",
    ),
    line(
        13,
        24,
        F,
        "p13_flow_c10_one_year_or_more",
        routes=(SECTION_C,),
    ),
    word(13, 24, "HEAD", R, "p13_role_head_c10", routes=(SECTION_C,)),
    line(
        13,
        26,
        C,
        "p13_c11_start_month",
        routes=(C10_LESS,),
        parents=("p13_job_present_position",),
        parent_note=_JOB_NOTE,
        note="C11 prints the start-month exposure field of the current job.",
    ),
    line(13, 26, P, "p13_c11_prompt", routes=(C10_LESS,)),
    block(13, 28, 29, P, "p13_c12_prompt", routes=(C10_LESS,)),
    tail(
        13,
        33,
        "TURfl TO P. 8, Cl6",
        F,
        "p13_flow_c12_no_previous_job",
        routes=(C10_LESS,),
    ),
    block(13, 35, 36, P, "p13_c13_prompt", routes=(C10_LESS,)),
    line(13, 47, P, "p13_c15_prompt", routes=(C10_LESS,)),
)


_WORKTIME = "Prints a 1979 work-time exposure field for the head's main job."

# Page 15 - head 1979 work-time exposure items C16-C23.
PAGE_15 = (
    line(
        15,
        3,
        C,
        "p15_c16_missed_other_sick",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(15, 3, P, "p15_c16_prompt", routes=(SECTION_C,)),
    line(
        15,
        9,
        C,
        "p15_c17_missed_other_sick_amount",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(15, 9, P, "p15_c17_prompt", routes=(SECTION_C,)),
    word(15, 19, "GO   TO C20", F, "p15_flow_c18_no", routes=(SECTION_C,)),
    line(
        15,
        14,
        C,
        "p15_c18_missed_own_sick",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(15, 14, P, "p15_c18_prompt", routes=(SECTION_C,)),
    line(
        15,
        21,
        C,
        "p15_c19_missed_own_sick_amount",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(15, 21, P, "p15_c19_prompt", routes=(SECTION_C,)),
    line(15, 26, C, "p15_c20_vacation", routes=(SECTION_C,), note=_WORKTIME),
    line(15, 26, P, "p15_c20_prompt", routes=(SECTION_C,)),
    word(15, 31, "GO TO C22", F, "p15_flow_c20_no", routes=(SECTION_C,)),
    line(
        15,
        32,
        C,
        "p15_c21_vacation_amount",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(15, 32, P, "p15_c21_prompt", routes=(SECTION_C,)),
    line(15, 37, C, "p15_c22_strike", routes=(SECTION_C,), note=_WORKTIME),
    line(15, 37, P, "p15_c22_prompt", routes=(SECTION_C,)),
    word(
        15, 42, "TURN To P. 9, c24", F, "p15_flow_c22_no", routes=(SECTION_C,)
    ),
    line(
        15, 45, C, "p15_c23_strike_amount", routes=(SECTION_C,), note=_WORKTIME
    ),
    line(15, 45, P, "p15_c23_prompt", routes=(SECTION_C,)),
)

# Page 17 - head 1979 unemployment exposure and main-job work time C24-C29.
PAGE_17 = (
    block(
        17,
        3,
        4,
        C,
        "p17_c24_missed_unemployed",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    block(17, 3, 4, P, "p17_c24_prompt", routes=(SECTION_C,)),
    word(17, 9, "GO TO C26", F, "p17_flow_c24_no", routes=(SECTION_C,)),
    line(
        17,
        12,
        C,
        "p17_c25_missed_unemployed_amount",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(17, 12, P, "p17_c25_prompt", routes=(SECTION_C,)),
    line(
        17,
        18,
        C,
        "p17_c26_weeks_main_job",
        routes=(SECTION_C,),
        note="C26 prints the 1979 weeks-worked reporting-unit field.",
    ),
    line(17, 18, P, "p17_c26_prompt", routes=(SECTION_C,)),
    line(
        17,
        22,
        C,
        "p17_c27_hours_main_job",
        routes=(SECTION_C,),
        parents=("p17_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="C27 prints the 1979 hours-per-week reporting-unit field.",
    ),
    line(17, 22, P, "p17_c27_prompt", routes=(SECTION_C,)),
    word(
        17,
        22,
        "main job",
        J,
        "p17_job_main_job",
        routes=(SECTION_C,),
        note="C27 names the head's 1979 main job by its printed job noun.",
    ),
    line(
        17,
        27,
        C,
        "p17_c28_overtime_hours",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(17, 27, P, "p17_c28_prompt", routes=(SECTION_C,)),
    word(
        17,
        30,
        "TURN TO p . lO, C30",
        F,
        "p17_flow_c28_no",
        routes=(SECTION_C,),
    ),
    line(
        17,
        32,
        C,
        "p17_c29_overtime_amount",
        routes=(SECTION_C,),
        note=_WORKTIME,
    ),
    line(17, 32, P, "p17_c29_prompt", routes=(SECTION_C,)),
)

# Page 19 - head extra-job items C38-C43.
PAGE_19 = (
    block(
        19,
        3,
        4,
        C,
        "p19_c38_extra_jobs",
        routes=(SECTION_C,),
        parents=("p19_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="C38 prints the extra-job holding field.",
    ),
    block(19, 3, 4, P, "p19_c38_prompt", routes=(SECTION_C,)),
    word(
        19,
        3,
        "extra jobs",
        J,
        "p19_job_extra_jobs",
        routes=(SECTION_C,),
        note="C38 names the head's extra jobs by their printed job noun.",
    ),
    line(
        19,
        7,
        C,
        "p19_c39_extra_job_occupation",
        routes=(SECTION_C,),
        parents=("p19_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="C39 prints the extra-job occupation field.",
    ),
    line(19, 7, P, "p19_c39_prompt", routes=(SECTION_C,)),
    line(19, 11, P, "p19_c40_prompt", routes=(SECTION_C,)),
    word(
        19,
        15,
        "C41.   About how much did you make per hour at this?",
        M,
        "p19_c41_extra_job_hourly_pay",
        routes=(SECTION_C,),
        parents=("p19_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="C41 prints the extra-job hourly remuneration component.",
    ),
    word(
        19,
        15,
        "C41.   About how much did you make per hour at this?",
        P,
        "p19_c41_prompt",
        routes=(SECTION_C,),
    ),
    word(
        19,
        23,
        "C42.   And how many weeks did you work on your extra job(s) in 1979?",
        C,
        "p19_c42_extra_job_weeks",
        routes=(SECTION_C,),
        parents=("p19_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="C42 prints the extra-job weeks reporting-unit field.",
    ),
    word(
        19,
        23,
        "C42.   And how many weeks did you work on your extra job(s) in 1979?",
        P,
        "p19_c42_prompt",
        routes=(SECTION_C,),
    ),
    line(
        19,
        32,
        C,
        "p19_c43_extra_job_hours",
        routes=(SECTION_C,),
        parents=("p19_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="C43 prints the extra-job hours reporting-unit field.",
    ),
    line(19, 32, P, "p19_c43_prompt", routes=(SECTION_C,)),
    word(
        19,
        50,
        "TURN TO P. 12, C51",
        F,
        "p19_flow_c46_yes",
        routes=(SECTION_C,),
    ),
)


SECTION_D = SECTION_C + (
    "p11_flow_c1_turn_section_d",
    "p25_flow_section_d",
)
D16_WORKED = SECTION_D + ("p29_flow_d16_worked",)
SECTION_E = SECTION_C + (
    "p11_flow_c1_turn_section_e",
    "p33_flow_section_e",
)

# Page 25 - section D entry and head job-search items D1-D2.
PAGE_25 = (
    tail(
        25,
        3,
        "SECTION D:",
        F,
        "p25_flow_section_d",
        routes=(SECTION_C + ("p11_flow_c1_turn_section_d",),),
        note="Printed section D header, entered by the C1 routing atom.",
    ),
    word(25, 3, "HEAD", R, "p25_role_head_header", routes=(SECTION_D,)),
    line(
        25,
        7,
        C,
        "p25_d1_sought_occupation",
        routes=(SECTION_D,),
        parents=("p25_job_sought",),
        parent_note="Parent job is the printed sought-job noun on this "
        "screen.",
        note="D1 prints the sought-job occupation field.",
    ),
    line(25, 7, P, "p25_d1_prompt", routes=(SECTION_D,)),
    word(
        25,
        7,
        "job",
        J,
        "p25_job_sought",
        routes=(SECTION_D,),
        note="D1 names the head's sought job by its printed job noun.",
    ),
    line(
        25,
        12,
        M,
        "p25_d2_expected_earnings",
        routes=(SECTION_D,),
        parents=("p25_job_sought",),
        parent_note="Parent job is the printed sought-job noun on this "
        "screen.",
        note="D2 prints the expected-earnings remuneration component of the "
        "sought job.",
    ),
    line(25, 12, P, "p25_d2_prompt", routes=(SECTION_D,)),
    word(25, 24, "GO TO 06", F, "p25_flow_d4_no", routes=(SECTION_D,)),
)

# Page 27 - head last-job items D11-D15.
PAGE_27 = (
    line(27, 17, P, "p27_d11_prompt", routes=(SECTION_D,)),
    word(
        27,
        19,
        "TURN TO P. 20, SECTIDr'J F",
        F,
        "p27_flow_d11_never_worked",
        routes=(SECTION_D,),
    ),
    line(
        27,
        23,
        C,
        "p27_d12_last_job_occupation",
        routes=(SECTION_D,),
        parents=("p27_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="D12 prints the last-job occupation field.",
    ),
    line(27, 23, P, "p27_d12_prompt", routes=(SECTION_D,)),
    word(
        27,
        23,
        "last job",
        J,
        "p27_job_last_job",
        routes=(SECTION_D,),
        note="D12 names the head's last job by its printed job noun.",
    ),
    line(
        27,
        27,
        C,
        "p27_d13_last_job_industry",
        routes=(SECTION_D,),
        parents=("p27_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="D13 prints the last-job business-or-industry field.",
    ),
    line(27, 27, P, "p27_d13_prompt", routes=(SECTION_D,)),
    block(27, 31, 32, P, "p27_d14_prompt", routes=(SECTION_D,)),
    line(
        27,
        37,
        C,
        "p27_d15_last_worked",
        routes=(SECTION_D,),
        parents=("p27_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="D15 prints the last-worked exposure field.",
    ),
    line(27, 37, P, "p27_d15_prompt", routes=(SECTION_D,)),
)

_D_WORKTIME = "Prints a 1979 work-time exposure field for the head."

# Page 29 - D16 checkpoint and head 1979 work-time items D17-D24.
PAGE_29 = (
    line(
        29,
        4,
        F,
        "p29_flow_d16_worked",
        routes=(SECTION_D,),
        note="D16 checkpoint label opening the 1979 work-time block "
        "D17-D31.",
    ),
    word(29, 4, "HEAD", R, "p29_role_head_d16", routes=(SECTION_D,)),
    line(29, 5, F, "p29_flow_d16_not_worked", routes=(SECTION_D,)),
    line(29, 7, C, "p29_d17_vacation", routes=(D16_WORKED,), note=_D_WORKTIME),
    line(29, 7, P, "p29_d17_prompt", routes=(D16_WORKED,)),
    word(29, 9, "GO TO Dl9", F, "p29_flow_d17_no", routes=(D16_WORKED,)),
    line(
        29,
        13,
        C,
        "p29_d18_vacation_amount",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 13, P, "p29_d18_prompt", routes=(D16_WORKED,)),
    line(
        29,
        17,
        C,
        "p29_d19_missed_other_sick",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 17, P, "p29_d19_prompt", routes=(D16_WORKED,)),
    word(29, 22, "GO TO D21", F, "p29_flow_d19_no", routes=(D16_WORKED,)),
    line(
        29,
        24,
        C,
        "p29_d20_missed_other_sick_amount",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 24, P, "p29_d20_prompt", routes=(D16_WORKED,)),
    line(
        29,
        28,
        C,
        "p29_d21_missed_own_sick",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 28, P, "p29_d21_prompt", routes=(D16_WORKED,)),
    word(29, 33, "GO TO 023", F, "p29_flow_d21_no", routes=(D16_WORKED,)),
    line(
        29,
        35,
        C,
        "p29_d22_missed_own_sick_amount",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 35, P, "p29_d22_prompt", routes=(D16_WORKED,)),
    line(29, 39, C, "p29_d23_strike", routes=(D16_WORKED,), note=_D_WORKTIME),
    line(29, 39, P, "p29_d23_prompt", routes=(D16_WORKED,)),
    line(
        29,
        45,
        C,
        "p29_d24_strike_amount",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(29, 45, P, "p29_d24_prompt", routes=(D16_WORKED,)),
)

# Page 31 - head 1979 work-time items D25-D28.
PAGE_31 = (
    block(
        31,
        3,
        4,
        C,
        "p31_d25_missed_unemployed",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    block(31, 3, 4, P, "p31_d25_prompt", routes=(D16_WORKED,)),
    line(
        31,
        10,
        C,
        "p31_d26_missed_unemployed_amount",
        routes=(D16_WORKED,),
        note=_D_WORKTIME,
    ),
    line(31, 10, P, "p31_d26_prompt", routes=(D16_WORKED,)),
    word(31, 11, "GO TO D2 7", F, "p31_flow_d25_no", routes=(D16_WORKED,)),
    line(
        31,
        16,
        C,
        "p31_d27_weeks_worked",
        routes=(D16_WORKED,),
        note="D27 prints the 1979 weeks-worked reporting-unit field.",
    ),
    line(31, 16, P, "p31_d27_prompt", routes=(D16_WORKED,)),
    line(
        31,
        19,
        C,
        "p31_d28_hours_worked",
        routes=(D16_WORKED,),
        note="D28 prints the 1979 hours-per-week reporting-unit field.",
    ),
    line(31, 19, P, "p31_d28_prompt", routes=(D16_WORKED,)),
)

# Page 33 - section E entry and head out-of-labour-force items E1-E9.
PAGE_33 = (
    tail(
        33,
        3,
        "SECTION E:",
        F,
        "p33_flow_section_e",
        routes=(SECTION_C + ("p11_flow_c1_turn_section_e",),),
        note="Printed section E header, entered by the C1 routing atom.",
    ),
    word(33, 3, "HEAD", R, "p33_role_head_header", routes=(SECTION_E,)),
    line(33, 7, F, "p33_flow_e1_retired", routes=(SECTION_E,)),
    word(33, 7, "HEAD", R, "p33_role_head_e1", routes=(SECTION_E,)),
    line(33, 8, F, "p33_flow_e1_not_retired", routes=(SECTION_E,)),
    line(
        33,
        15,
        C,
        "p33_e3_work_for_money",
        routes=(SECTION_E,),
        note="E3 prints the 1979 work-for-money assignment field.",
    ),
    line(33, 15, P, "p33_e3_prompt", routes=(SECTION_E,)),
    word(
        33, 19, "TURN TO P. 19, ElO", F, "p33_flow_e3_no", routes=(SECTION_E,)
    ),
    line(
        33,
        21,
        C,
        "p33_e4_occupation",
        routes=(SECTION_E,),
        note="E4 prints the occupation field for the 1979 work-for-money "
        "activity.",
    ),
    line(33, 21, P, "p33_e4_prompt", routes=(SECTION_E,)),
    line(
        33,
        25,
        C,
        "p33_e5_industry",
        routes=(SECTION_E,),
        note="E5 prints the business-or-industry field.",
    ),
    line(33, 25, P, "p33_e5_prompt", routes=(SECTION_E,)),
    line(
        33,
        29,
        C,
        "p33_e6_weeks",
        routes=(SECTION_E,),
        note="E6 prints the 1979 weeks-worked reporting-unit field.",
    ),
    line(33, 29, P, "p33_e6_prompt", routes=(SECTION_E,)),
    line(
        33,
        33,
        C,
        "p33_e7_hours",
        routes=(SECTION_E,),
        note="E7 prints the 1979 hours-per-week reporting-unit field.",
    ),
    line(33, 33, P, "p33_e7_prompt", routes=(SECTION_E,)),
    line(
        33,
        36,
        C,
        "p33_e8_still_working",
        routes=(SECTION_E,),
        note="E8 prints the current-work assignment field.",
    ),
    line(33, 36, P, "p33_e8_prompt", routes=(SECTION_E,)),
    word(
        33, 39, "TURN TO P. 19, ElO", F, "p33_flow_e8_yes", routes=(SECTION_E,)
    ),
    block(33, 41, 42, P, "p33_e9_prompt", routes=(SECTION_E,)),
)


SECTION_F = ("p37_flow_section_f",)
F11_LESS = SECTION_F + ("p39_flow_f11_less_than_year",)
_F_WORKTIME = (
    "Prints a 1979 work-time exposure field for the wife/friend's main job."
)

# Page 37 - section F entry and wife/friend employment items F1-F4.
PAGE_37 = (
    tail(
        37,
        3,
        "SECTI ON F:",
        F,
        "p37_flow_section_f",
        note="Printed section F header conditions the wife/friend "
        "employment schedule selected at F2.",
    ),
    line(
        37,
        7,
        F,
        "p37_flow_f1_wife_present",
        routes=(SECTION_F,),
        note="F1 checkpoint label predicating the section on a wife or "
        "female friend in the FU.",
    ),
    word(37, 7, "HEAD", R, "p37_role_head_f1", routes=(SECTION_F,)),
    word(37, 8, "WIFE", R, "p37_role_wife_f1", routes=(SECTION_F,)),
    line(37, 9, F, "p37_flow_f1_no_wife", routes=(SECTION_F,)),
    line(37, 10, F, "p37_flow_f1_female_head", routes=(SECTION_F,)),
    block(
        37,
        16,
        17,
        C,
        "p37_f2_assignment",
        routes=(SECTION_F,),
        note="F2 prints the wife/friend labour-force assignment field.",
    ),
    block(37, 16, 17, P, "p37_f2_prompt", routes=(SECTION_F,)),
    word(
        37,
        25,
        "TURrJ TO P. 25 ,",
        F,
        "p37_flow_f2_turn_section_g",
        routes=(SECTION_F,),
        note="F2 routing atom into the section G schedule.",
    ),
    word(
        37,
        29,
        "TURt~ TO P. 28,",
        F,
        "p37_flow_f2_turn_section_h",
        routes=(SECTION_F,),
        note="F2 routing atom into the section H schedule.",
    ),
    tail(
        37,
        43,
        "GO TO F3",
        F,
        "p37_flow_f1_has_job",
        routes=(SECTION_F,),
    ),
    tail(
        37,
        44,
        "TURN TO P. 28 ,",
        F,
        "p37_flow_f1_no_job_section_h",
        routes=(SECTION_F,),
    ),
    line(
        37,
        48,
        C,
        "p37_f3_employee_self",
        routes=(SECTION_F,),
        note="F3 prints the employee/self-employed field.",
    ),
    line(37, 48, P, "p37_f3_prompt", routes=(SECTION_F,)),
    word(
        37,
        51,
        "TURN TO P. 21, F7",
        F,
        "p37_flow_f3_self_only",
        routes=(SECTION_F,),
    ),
    block(
        37,
        53,
        54,
        C,
        "p37_f4_government",
        routes=(SECTION_F,),
        note="F4 prints the federal/state/local government-level field.",
    ),
    block(37, 53, 54, P, "p37_f4_prompt", routes=(SECTION_F,)),
    word(
        37,
        64,
        "TURN TOP . 21, F7",
        F,
        "p37_flow_f5_union_exit",
        routes=(SECTION_F,),
    ),
)

# Page 39 - wife/friend occupation, industry, and tenure items F7-F13.
PAGE_39 = (
    line(
        39,
        3,
        C,
        "p39_f7_occupation",
        routes=(SECTION_F,),
        note="F7 prints the wife/friend main-occupation field.",
    ),
    line(39, 3, P, "p39_f7_prompt", routes=(SECTION_F,)),
    line(
        39,
        8,
        C,
        "p39_f8_occupation_detail",
        routes=(SECTION_F,),
        note="F8 prints the occupation-detail probe field.",
    ),
    line(39, 8, P, "p39_f8_prompt", routes=(SECTION_F,)),
    line(
        39,
        13,
        C,
        "p39_f9_industry",
        routes=(SECTION_F,),
        note="F9 prints the business-or-industry field.",
    ),
    line(39, 13, P, "p39_f9_prompt", routes=(SECTION_F,)),
    line(
        39,
        17,
        C,
        "p39_f10_tenure",
        routes=(SECTION_F,),
        parents=("p39_job_present_position",),
        parent_note="Parent job is the printed current-job noun on this "
        "screen.",
        note="F10 prints the current-position tenure field.",
    ),
    line(39, 17, P, "p39_f10_prompt", routes=(SECTION_F,)),
    word(
        39,
        17,
        "present position",
        J,
        "p39_job_present_position",
        routes=(SECTION_F,),
        note="F10 names the wife/friend's current job by its printed job "
        "noun.",
    ),
    line(
        39,
        27,
        F,
        "p39_flow_f11_less_than_year",
        routes=(SECTION_F,),
        note="F11 checkpoint label opening the short-tenure block F12-F13.",
    ),
    line(39, 29, F, "p39_flow_f11_one_year_or_more", routes=(SECTION_F,)),
    word(
        39,
        30,
        "TURN TO P. 22, Fl4",
        F,
        "p39_flow_f11_to_f14",
        routes=(SECTION_F,),
    ),
    line(
        39,
        33,
        C,
        "p39_f12_start_month",
        routes=(F11_LESS,),
        note="F12 prints the start-month exposure field of the current job.",
    ),
    line(39, 33, P, "p39_f12_prompt", routes=(F11_LESS,)),
    block(39, 37, 38, P, "p39_f13_prompt", routes=(F11_LESS,)),
)

# Page 41 - wife/friend 1979 work-time items F14-F23.
PAGE_41 = (
    block(
        41,
        3,
        4,
        C,
        "p41_f14_missed_other_sick",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    block(41, 3, 4, P, "p41_f14_prompt", routes=(SECTION_F,)),
    word(41, 7, "GO TO F16", F, "p41_flow_f14_no", routes=(SECTION_F,)),
    line(
        41,
        8,
        C,
        "p41_f15_missed_other_sick_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 8, P, "p41_f15_prompt", routes=(SECTION_F,)),
    line(
        41,
        12,
        C,
        "p41_f16_missed_own_sick",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 12, P, "p41_f16_prompt", routes=(SECTION_F,)),
    line(
        41,
        19,
        C,
        "p41_f17_missed_own_sick_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 19, P, "p41_f17_prompt", routes=(SECTION_F,)),
    word(41, 20, "GO   TO F18", F, "p41_flow_f16_no", routes=(SECTION_F,)),
    line(41, 27, C, "p41_f18_vacation", routes=(SECTION_F,), note=_F_WORKTIME),
    line(41, 27, P, "p41_f18_prompt", routes=(SECTION_F,)),
    line(
        41,
        34,
        C,
        "p41_f19_vacation_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 34, P, "p41_f19_prompt", routes=(SECTION_F,)),
    word(41, 35, "GO TO F20", F, "p41_flow_f18_no", routes=(SECTION_F,)),
    line(41, 42, C, "p41_f20_strike", routes=(SECTION_F,), note=_F_WORKTIME),
    line(41, 42, P, "p41_f20_prompt", routes=(SECTION_F,)),
    line(
        41,
        48,
        C,
        "p41_f21_strike_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 48, P, "p41_f21_prompt", routes=(SECTION_F,)),
    block(
        41,
        52,
        53,
        C,
        "p41_f22_missed_unemployed",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    block(41, 52, 53, P, "p41_f22_prompt", routes=(SECTION_F,)),
    word(
        41,
        55,
        "TURH TO P. 23 , F24",
        F,
        "p41_flow_f22_no",
        routes=(SECTION_F,),
    ),
    line(
        41,
        59,
        C,
        "p41_f23_missed_unemployed_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(41, 59, P, "p41_f23_prompt", routes=(SECTION_F,)),
)

# Page 43 - wife/friend main-job work time and pay form items F24-F31.
PAGE_43 = (
    block(
        43,
        3,
        4,
        C,
        "p43_f24_weeks_main_job",
        routes=(SECTION_F,),
        parents=("p43_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="F24 prints the 1979 weeks-worked reporting-unit field.",
    ),
    block(43, 3, 4, P, "p43_f24_prompt", routes=(SECTION_F,)),
    word(
        43,
        3,
        "main job",
        J,
        "p43_job_main_job",
        routes=(SECTION_F,),
        note="F24 names the wife/friend's 1979 main job by its printed job "
        "noun.",
    ),
    block(
        43,
        9,
        10,
        C,
        "p43_f25_hours_main_job",
        routes=(SECTION_F,),
        parents=("p43_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="F25 prints the 1979 hours-per-week reporting-unit field.",
    ),
    block(43, 9, 10, P, "p43_f25_prompt", routes=(SECTION_F,)),
    line(
        43,
        13,
        C,
        "p43_f26_overtime_hours",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(43, 13, P, "p43_f26_prompt", routes=(SECTION_F,)),
    word(43, 19, "GO TO f28", F, "p43_flow_f26_no", routes=(SECTION_F,)),
    line(
        43,
        21,
        C,
        "p43_f27_overtime_amount",
        routes=(SECTION_F,),
        note=_F_WORKTIME,
    ),
    line(43, 21, P, "p43_f27_prompt", routes=(SECTION_F,)),
    line(
        43,
        25,
        C,
        "p43_f28_pay_form",
        routes=(SECTION_F,),
        parents=("p43_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="F28 prints the salaried/hourly pay-form field.",
    ),
    line(43, 25, P, "p43_f28_prompt", routes=(SECTION_F,)),
    block(43, 31, 33, P, "p43_f29_f31_prompt", routes=(SECTION_F,)),
    word(
        43,
        32,
        "salary",
        M,
        "p43_f29_salary",
        routes=(SECTION_F,),
        parents=("p43_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="F29 prints the salary remuneration component.",
    ),
    word(
        43,
        31,
        "hourly wage",
        M,
        "p43_f30_hourly_wage",
        routes=(SECTION_F,),
        parents=("p43_job_main_job",),
        parent_note="Parent job is the printed main-job noun on this screen.",
        note="F30 prints the hourly wage-rate remuneration component.",
    ),
)

# Page 45 - wife/friend extra-job items F32-F35.
PAGE_45 = (
    block(
        45,
        4,
        5,
        C,
        "p45_f32_extra_jobs",
        routes=(SECTION_F,),
        parents=("p45_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun printed at F34 "
        "on this screen.",
        note="F32 prints the extra-job holding field.",
    ),
    block(45, 4, 5, P, "p45_f32_prompt", routes=(SECTION_F,)),
    line(
        45,
        8,
        C,
        "p45_f33_extra_job_occupation",
        routes=(SECTION_F,),
        parents=("p45_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun printed at F34 "
        "on this screen.",
        note="F33 prints the extra-job occupation field.",
    ),
    line(45, 8, P, "p45_f33_prompt", routes=(SECTION_F,)),
    line(
        45,
        14,
        C,
        "p45_f34_extra_job_weeks",
        routes=(SECTION_F,),
        parents=("p45_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="F34 prints the extra-job weeks reporting-unit field.",
    ),
    line(45, 14, P, "p45_f34_prompt", routes=(SECTION_F,)),
    word(
        45,
        14,
        "extra job(s)",
        J,
        "p45_job_extra_jobs",
        routes=(SECTION_F,),
        note="F34 names the wife/friend's extra jobs by their printed job "
        "noun; the F32 print of the same noun is broken by the scan and is "
        "not reconstructed.",
    ),
    line(
        45,
        17,
        C,
        "p45_f35_extra_job_hours",
        routes=(SECTION_F,),
        parents=("p45_job_extra_jobs",),
        parent_note="Parent job is the printed extra-job noun on this screen.",
        note="F35 prints the extra-job hours reporting-unit field.",
    ),
    line(45, 17, P, "p45_f35_prompt", routes=(SECTION_F,)),
    word(
        45,
        45,
        "TURN TO p. 30 , SECTION J",
        F,
        "p45_flow_f38_exit",
        routes=(SECTION_F,),
    ),
)


SECTION_G = SECTION_F + (
    "p37_flow_f2_turn_section_g",
    "p47_flow_section_g",
)
G10_WORKED = SECTION_G + ("p49_flow_g10_worked",)
SECTION_H = SECTION_F + (
    "p37_flow_f2_turn_section_h",
    "p53_flow_section_h",
)
_G_WORKTIME = "Prints a 1979 work-time exposure field for the wife/friend."

# Page 47 - section G entry and wife/friend last-job items G1-G9.
PAGE_47 = (
    tail(
        47,
        3,
        "SECTI ON G:",
        F,
        "p47_flow_section_g",
        routes=(SECTION_F + ("p37_flow_f2_turn_section_g",),),
        note="Printed section G header, entered by the F2 routing atom.",
    ),
    line(
        47,
        6,
        C,
        "p47_g1_sought_occupation",
        routes=(SECTION_G,),
        parents=("p47_job_sought",),
        parent_note="Parent job is the printed sought-job noun on this "
        "screen.",
        note="G1 prints the sought-job occupation field.",
    ),
    line(47, 6, P, "p47_g1_prompt", routes=(SECTION_G,)),
    word(
        47,
        6,
        "job",
        J,
        "p47_job_sought",
        routes=(SECTION_G,),
        note="G1 names the wife/friend's sought job by its printed job noun.",
    ),
    line(47, 25, P, "p47_g5_prompt", routes=(SECTION_G,)),
    word(
        47,
        30,
        "TURN TO P. 30, SECTION J",
        F,
        "p47_flow_g5_never_worked",
        routes=(SECTION_G,),
    ),
    block(
        47,
        32,
        33,
        C,
        "p47_g6_last_job_occupation",
        routes=(SECTION_G,),
        parents=("p47_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="G6 prints the last-job occupation field.",
    ),
    block(47, 32, 33, P, "p47_g6_prompt", routes=(SECTION_G,)),
    word(
        47,
        32,
        "last job",
        J,
        "p47_job_last_job",
        routes=(SECTION_G,),
        note="G6 names the wife/friend's last job by its printed job noun.",
    ),
    line(
        47,
        37,
        C,
        "p47_g7_last_job_industry",
        routes=(SECTION_G,),
        parents=("p47_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="G7 prints the last-job business-or-industry field.",
    ),
    line(47, 37, P, "p47_g7_prompt", routes=(SECTION_G,)),
    block(47, 41, 42, P, "p47_g8_prompt", routes=(SECTION_G,)),
    line(
        47,
        46,
        C,
        "p47_g9_last_worked",
        routes=(SECTION_G,),
        parents=("p47_job_last_job",),
        parent_note="Parent job is the printed last-job noun on this screen.",
        note="G9 prints the last-worked exposure field.",
    ),
    line(47, 46, P, "p47_g9_prompt", routes=(SECTION_G,)),
)

# Page 49 - G10 checkpoint and wife/friend 1979 work-time items G11-G18.
PAGE_49 = (
    line(
        49,
        4,
        F,
        "p49_flow_g10_worked",
        routes=(SECTION_G,),
        note="G10 checkpoint label opening the 1979 work-time block "
        "G11-G25.",
    ),
    word(49, 4, "WIFE", R, "p49_role_wife_g10", routes=(SECTION_G,)),
    line(49, 5, F, "p49_flow_g10_not_worked", routes=(SECTION_G,)),
    line(
        49, 10, C, "p49_g11_vacation", routes=(G10_WORKED,), note=_G_WORKTIME
    ),
    line(49, 10, P, "p49_g11_prompt", routes=(G10_WORKED,)),
    word(49, 12, "GO TO Gl3", F, "p49_flow_g11_no", routes=(G10_WORKED,)),
    line(
        49,
        13,
        C,
        "p49_g12_vacation_amount",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(49, 13, P, "p49_g12_prompt", routes=(G10_WORKED,)),
    block(
        49,
        17,
        18,
        C,
        "p49_g13_missed_other_sick",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    block(49, 17, 18, P, "p49_g13_prompt", routes=(G10_WORKED,)),
    line(
        49,
        24,
        C,
        "p49_g14_missed_other_sick_amount",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(49, 24, P, "p49_g14_prompt", routes=(G10_WORKED,)),
    line(
        49,
        28,
        C,
        "p49_g15_missed_own_sick",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(49, 28, P, "p49_g15_prompt", routes=(G10_WORKED,)),
    word(49, 30, "GO TO G17", F, "p49_flow_g15_no", routes=(G10_WORKED,)),
    line(
        49,
        34,
        C,
        "p49_g16_missed_own_sick_amount",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(49, 34, P, "p49_g16_prompt", routes=(G10_WORKED,)),
    line(49, 38, C, "p49_g17_strike", routes=(G10_WORKED,), note=_G_WORKTIME),
    line(49, 38, P, "p49_g17_prompt", routes=(G10_WORKED,)),
    line(
        49,
        44,
        C,
        "p49_g18_strike_amount",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(49, 44, P, "p49_g18_prompt", routes=(G10_WORKED,)),
)

# Page 51 - wife/friend 1979 work-time items G19-G22.
PAGE_51 = (
    block(
        51,
        3,
        4,
        C,
        "p51_g19_missed_unemployed",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    block(51, 3, 4, P, "p51_g19_prompt", routes=(G10_WORKED,)),
    word(51, 6, "GO TO G21", F, "p51_flow_g19_no", routes=(G10_WORKED,)),
    line(
        51,
        9,
        C,
        "p51_g20_missed_unemployed_amount",
        routes=(G10_WORKED,),
        note=_G_WORKTIME,
    ),
    line(51, 9, P, "p51_g20_prompt", routes=(G10_WORKED,)),
    line(
        51,
        13,
        C,
        "p51_g21_weeks_worked",
        routes=(G10_WORKED,),
        note="G21 prints the 1979 weeks-worked reporting-unit field.",
    ),
    line(51, 13, P, "p51_g21_prompt", routes=(G10_WORKED,)),
    line(
        51,
        16,
        C,
        "p51_g22_hours_worked",
        routes=(G10_WORKED,),
        note="G22 prints the 1979 hours-per-week reporting-unit field.",
    ),
    line(51, 16, P, "p51_g22_prompt", routes=(G10_WORKED,)),
    word(
        51,
        50,
        "TURN TOP . 30 , SECTION J",
        F,
        "p51_flow_g25_exit",
        routes=(G10_WORKED,),
    ),
)

# Page 53 - section H entry and wife/friend out-of-labour-force items H1-H9.
PAGE_53 = (
    tail(
        53,
        2,
        "SECTION H:",
        F,
        "p53_flow_section_h",
        routes=(SECTION_F + ("p37_flow_f2_turn_section_h",),),
        note="Printed section H header, entered by the F2 routing atom.",
    ),
    line(53, 6, F, "p53_flow_h1_retired", routes=(SECTION_H,)),
    word(53, 6, "WIFE", R, "p53_role_wife_h1", routes=(SECTION_H,)),
    line(53, 8, F, "p53_flow_h1_not_retired", routes=(SECTION_H,)),
    line(
        53,
        15,
        C,
        "p53_h3_work_for_money",
        routes=(SECTION_H,),
        note="H3 prints the 1979 work-for-money assignment field.",
    ),
    line(53, 15, P, "p53_h3_prompt", routes=(SECTION_H,)),
    word(
        53, 18, "TURN TO P. 29, HlO", F, "p53_flow_h3_no", routes=(SECTION_H,)
    ),
    line(
        53,
        20,
        C,
        "p53_h4_occupation",
        routes=(SECTION_H,),
        note="H4 prints the occupation field for the 1979 work-for-money "
        "activity.",
    ),
    line(53, 20, P, "p53_h4_prompt", routes=(SECTION_H,)),
    line(
        53,
        24,
        C,
        "p53_h5_industry",
        routes=(SECTION_H,),
        note="H5 prints the business-or-industry field.",
    ),
    line(53, 24, P, "p53_h5_prompt", routes=(SECTION_H,)),
    line(
        53,
        28,
        C,
        "p53_h6_weeks",
        routes=(SECTION_H,),
        note="H6 prints the 1979 weeks-worked reporting-unit field.",
    ),
    line(53, 28, P, "p53_h6_prompt", routes=(SECTION_H,)),
    line(
        53,
        31,
        C,
        "p53_h7_hours",
        routes=(SECTION_H,),
        note="H7 prints the 1979 hours-per-week reporting-unit field.",
    ),
    line(53, 31, P, "p53_h7_prompt", routes=(SECTION_H,)),
    line(
        53,
        34,
        C,
        "p53_h8_still_working",
        routes=(SECTION_H,),
        note="H8 prints the current-work assignment field.",
    ),
    line(53, 34, P, "p53_h8_prompt", routes=(SECTION_H,)),
    word(
        53, 37, "TURN TO P. 29, HlO", F, "p53_flow_h8_yes", routes=(SECTION_H,)
    ),
    block(53, 39, 40, P, "p53_h9_prompt", routes=(SECTION_H,)),
)


SECTION_K = ("p67_flow_section_k",)
SECTION_K_R = ("p69_flow_section_k_reprint",)
K1_FARMER = SECTION_K + ("p67_flow_k1_farmer",)
K1_FARMER_R = SECTION_K_R + ("p69_flow_k1_farmer",)
K25_WIFE = SECTION_K + ("p79_flow_k25_wife_in_fu",)
_FARM_PARENT = (
    "Parent aggregate is the printed net-farm-income anchor on this screen."
)
_BUSINESS_PARENT = (
    "Parent aggregate is the printed business anchor on this screen."
)

# Page 67 - section K entry and family work-income items K1-K10.
PAGE_67 = (
    tail(
        67,
        2,
        "SECTION K:",
        F,
        "p67_flow_section_k",
        note="Printed section K header opening the family income schedule.",
    ),
    line(
        67,
        7,
        F,
        "p67_flow_k1_farmer",
        routes=(SECTION_K,),
        note="K1 checkpoint label opening the farm-aggregate block K2-K4.",
    ),
    word(67, 7, "HEAD", R, "p67_role_head_k1", routes=(SECTION_K,)),
    line(67, 8, F, "p67_flow_k1_not_farmer", routes=(SECTION_K,)),
    block(
        67,
        12,
        13,
        M,
        "p67_k2_farm_receipts",
        routes=(K1_FARMER,),
        parents=("p67_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="K2 prints the total-farm-receipts remuneration component.",
    ),
    block(67, 12, 13, P, "p67_k2_prompt", routes=(K1_FARMER,)),
    block(
        67,
        14,
        15,
        M,
        "p67_k3_farm_expenses",
        routes=(K1_FARMER,),
        parents=("p67_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="K3 prints the farm operating-expense remuneration component.",
    ),
    block(67, 14, 15, P, "p67_k3_prompt", routes=(K1_FARMER,)),
    word(
        67,
        17,
        "net income from farming",
        FA,
        "p67_fa_net_farm_income",
        routes=(K1_FARMER,),
        note="K4 prints the farm aggregate by its printed net-farm-income "
        "label.",
    ),
    line(67, 17, P, "p67_k4_prompt", routes=(K1_FARMER,)),
    block(67, 20, 21, P, "p67_k5_prompt", routes=(SECTION_K,)),
    word(67, 23, "GO TO KB", F, "p67_flow_k5_no", routes=(SECTION_K,)),
    block(
        67,
        25,
        26,
        C,
        "p67_k6_incorporation",
        routes=(SECTION_K,),
        parents=("p67_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="K6 prints the business incorporation field.",
    ),
    block(67, 25, 26, P, "p67_k6_prompt", routes=(SECTION_K,)),
    word(
        67,
        25,
        "unincorporated business",
        BA,
        "p67_ba_unincorporated_business",
        routes=(SECTION_K,),
        note="K6 prints the business aggregate by its printed label.",
    ),
    word(
        67, 29, "GO TO KB", F, "p67_flow_k6_corporation", routes=(SECTION_K,)
    ),
    block(
        67,
        30,
        31,
        M,
        "p67_k7_business_share",
        routes=(SECTION_K,),
        parents=("p67_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="K7 prints the family business-income share remuneration "
        "component.",
    ),
    block(67, 30, 31, P, "p67_k7_prompt", routes=(SECTION_K,)),
    block(67, 36, 37, P, "p67_k8_prompt", routes=(SECTION_K,)),
    word(67, 36, "HEAD", R, "p67_role_head_k8", routes=(SECTION_K,)),
    word(
        67,
        36,
        "wages and salaries",
        M,
        "p67_k8_wages_and_salaries",
        routes=(SECTION_K,),
        note="K8 prints the head's 1979 wages-and-salaries remuneration "
        "component.",
    ),
    line(
        67,
        41,
        M,
        "p67_k9_bonuses_overtime_commissions",
        routes=(SECTION_K,),
        note="K9 prints the bonus, overtime, and commission remuneration "
        "component.",
    ),
    line(67, 41, P, "p67_k9_prompt", routes=(SECTION_K,)),
    word(
        67, 43, "TURri TOP. 36, Kll", F, "p67_flow_k9_no", routes=(SECTION_K,)
    ),
    line(67, 45, P, "p67_k10_prompt", routes=(SECTION_K,)),
)

# Page 69 - the reprinted section K screen, items K1-K10.
PAGE_69 = (
    tail(
        69,
        2,
        "SECTION K:",
        F,
        "p69_flow_section_k_reprint",
        note="Printed section K header, reprinted on the continuation sheet "
        'that carries the "(CON\'T.)" screen marker.',
    ),
    line(69, 10, F, "p69_flow_k1_farmer", routes=(SECTION_K_R,)),
    word(69, 10, "HEAD", R, "p69_role_head_k1", routes=(SECTION_K_R,)),
    line(69, 11, F, "p69_flow_k1_not_farmer", routes=(SECTION_K_R,)),
    block(
        69,
        15,
        16,
        M,
        "p69_k2_farm_receipts",
        routes=(K1_FARMER_R,),
        parents=("p69_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="K2 prints the total-farm-receipts remuneration component.",
    ),
    block(69, 15, 16, P, "p69_k2_prompt", routes=(K1_FARMER_R,)),
    block(
        69,
        18,
        19,
        M,
        "p69_k3_farm_expenses",
        routes=(K1_FARMER_R,),
        parents=("p69_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="K3 prints the farm operating-expense remuneration component.",
    ),
    block(69, 18, 19, P, "p69_k3_prompt", routes=(K1_FARMER_R,)),
    word(
        69,
        21,
        "net inc ome from farming",
        FA,
        "p69_fa_net_farm_income",
        routes=(K1_FARMER_R,),
        note="K4 prints the farm aggregate by its printed net-farm-income "
        "label.",
    ),
    line(69, 21, P, "p69_k4_prompt", routes=(K1_FARMER_R,)),
    block(69, 24, 25, P, "p69_k5_prompt", routes=(SECTION_K_R,)),
    word(69, 27, "Go To KB", F, "p69_flow_k5_no", routes=(SECTION_K_R,)),
    block(
        69,
        29,
        30,
        C,
        "p69_k6_incorporation",
        routes=(SECTION_K_R,),
        parents=("p69_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="K6 prints the business incorporation field.",
    ),
    block(69, 29, 30, P, "p69_k6_prompt", routes=(SECTION_K_R,)),
    word(
        69,
        29,
        "unincorporated business",
        BA,
        "p69_ba_unincorporated_business",
        routes=(SECTION_K_R,),
        note="K6 prints the business aggregate by its printed label.",
    ),
    block(
        69,
        34,
        35,
        M,
        "p69_k7_business_share",
        routes=(SECTION_K_R,),
        parents=("p69_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="K7 prints the family business-income share remuneration "
        "component.",
    ),
    block(69, 34, 35, P, "p69_k7_prompt", routes=(SECTION_K_R,)),
    block(69, 39, 40, P, "p69_k8_prompt", routes=(SECTION_K_R,)),
    word(69, 39, "HEAD", R, "p69_role_head_k8", routes=(SECTION_K_R,)),
    word(
        69,
        39,
        "wages and salaries",
        M,
        "p69_k8_wages_and_salaries",
        routes=(SECTION_K_R,),
        note="K8 prints the head's 1979 wages-and-salaries remuneration "
        "component.",
    ),
    line(
        69,
        44,
        M,
        "p69_k9_bonuses_overtime_commissions",
        routes=(SECTION_K_R,),
        note="K9 prints the bonus, overtime, and commission remuneration "
        "component.",
    ),
    line(69, 44, P, "p69_k9_prompt", routes=(SECTION_K_R,)),
    word(
        69, 49, "TURN TOP. 36, Kll", F, "p69_flow_k9_no", routes=(SECTION_K_R,)
    ),
    line(69, 51, P, "p69_k10_prompt", routes=(SECTION_K_R,)),
)

# Page 71 - other-income items K11a-K11c.
PAGE_71 = (
    block(71, 3, 5, P, "p71_k11_prompt", routes=(SECTION_K,)),
    word(71, 4, "HEAD", R, "p71_role_head_k11", routes=(SECTION_K,)),
    word(
        71,
        4,
        "professional practice or",
        M,
        "p71_k11a_professional_practice",
        routes=(SECTION_K,),
        note="K11a prints the professional-practice-or-trade remuneration "
        "component.",
    ),
    word(
        71,
        5,
        "(FOR EACH YES TO Kll, ASK Kl2 AND Kl 3. )",
        A,
        "p71_k11_repeat_instruction",
        routes=(SECTION_K,),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="K11 prints an explicit interviewer repeat instruction binding "
        "the K12 amount and K13 duration fields to every lettered K11 item.",
    ),
    line(71, 15, P, "p71_k12_k13_prompt", routes=(SECTION_K,)),
    block(
        71,
        22,
        23,
        M,
        "p71_k11b_farming_gardening",
        routes=(SECTION_K,),
        note="K11b prints the farming-or-market-gardening remuneration "
        "component.",
    ),
    word(
        71,
        25,
        "roomers or boarders",
        M,
        "p71_k11c_roomers_boarders",
        routes=(SECTION_K,),
        note="K11c prints the roomers-or-boarders remuneration component.",
    ),
    word(
        71,
        37,
        "TURiJ TO P. 37, K20",
        F,
        "p71_flow_k11_to_k20",
        routes=(SECTION_K,),
    ),
    line(71, 39, F, "p71_flow_k14_age_65_or_older", routes=(SECTION_K,)),
    word(71, 39, "HEAD", R, "p71_role_head_k14", routes=(SECTION_K,)),
    line(71, 40, F, "p71_flow_k14_under_65", routes=(SECTION_K,)),
)

# Page 73 - the reprinted other-income screen, items K11a-K11c.
PAGE_73 = (
    block(73, 4, 5, P, "p73_k11_prompt", routes=(SECTION_K_R,)),
    word(73, 4, "HEAD", R, "p73_role_head_k11", routes=(SECTION_K_R,)),
    word(
        73,
        4,
        "professional practice or",
        M,
        "p73_k11a_professional_practice",
        routes=(SECTION_K_R,),
        note="K11a prints the professional-practice-or-trade remuneration "
        "component.",
    ),
    word(
        73,
        5,
        '(FOR EACH "YES" TO Kll, ASK Kl2 AND Kl3.)',
        A,
        "p73_k11_repeat_instruction",
        routes=(SECTION_K_R,),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="K11 prints an explicit interviewer repeat instruction binding "
        "the K12 amount and K13 duration fields to every lettered K11 item.",
    ),
    line(73, 11, P, "p73_k12_k13_prompt", routes=(SECTION_K_R,)),
    word(
        73,
        20,
        "from farming or market",
        M,
        "p73_k11b_farming_gardening",
        routes=(SECTION_K_R,),
        note="K11b prints the farming-or-market-gardening remuneration "
        "component.",
    ),
    word(
        73,
        26,
        "roomers or boarders",
        M,
        "p73_k11c_roomers_boarders",
        routes=(SECTION_K_R,),
        note="K11c prints the roomers-or-boarders remuneration component.",
    ),
    word(
        73,
        40,
        "TURN TO P. 37, K20",
        F,
        "p73_flow_k11_to_k20",
        routes=(SECTION_K_R,),
    ),
    line(73, 42, F, "p73_flow_k14_age_65_or_older", routes=(SECTION_K_R,)),
    word(73, 42, "HEAD", R, "p73_role_head_k14", routes=(SECTION_K_R,)),
    line(73, 43, F, "p73_flow_k14_under_65", routes=(SECTION_K_R,)),
)

# Page 79 - K25 checkpoint and wife/friend income items K26-K28.
PAGE_79 = (
    line(
        79,
        4,
        F,
        "p79_flow_k25_wife_in_fu",
        routes=(SECTION_K,),
        note="K25 checkpoint label opening the wife/friend income block "
        "K26-K35.",
    ),
    word(79, 4, "HEAD", R, "p79_role_head_k25", routes=(SECTION_K,)),
    word(79, 4, "WIFE", R, "p79_role_wife_k25", routes=(SECTION_K,)),
    line(79, 5, F, "p79_flow_k25_no_wife", routes=(SECTION_K,)),
    line(79, 6, F, "p79_flow_k25_female_head", routes=(SECTION_K,)),
    line(
        79,
        8,
        T,
        "p79_k26_wife_total_income",
        routes=(K25_WIFE,),
        note="K26 prints the wife/friend total-income role total.",
    ),
    line(79, 8, P, "p79_k26_prompt", routes=(K25_WIFE,)),
    word(
        79, 10, "TURN TO P. 39, K36", F, "p79_flow_k26_no", routes=(K25_WIFE,)
    ),
    line(79, 12, P, "p79_k27_prompt", routes=(K25_WIFE,)),
    word(79, 14, "GO TO K29", F, "p79_flow_k27_no", routes=(K25_WIFE,)),
    line(
        79,
        16,
        M,
        "p79_k28_wife_earnings_from_work",
        routes=(K25_WIFE,),
        note="K28 prints the wife/friend earnings-from-work remuneration "
        "component.",
    ),
    line(79, 16, P, "p79_k28_prompt", routes=(K25_WIFE,)),
)


SECTION_L = ("p103_flow_section_l",)
L1_NEW_WIFE = SECTION_L + ("p103_flow_l1_new_wife",)
SECTION_M = ("p105_flow_section_m",)
M1_NEW_HEAD = SECTION_M + ("p105_flow_m1_new_head",)

# Page 103 - section L entry and new-wife lifetime work items L10-L12.
PAGE_103 = (
    tail(
        103,
        3,
        "SECTION L:",
        F,
        "p103_flow_section_l",
        note="Printed section L header opening the new-wife schedule.",
    ),
    line(
        103,
        6,
        F,
        "p103_flow_l1_new_wife",
        routes=(SECTION_L,),
        note="L1 checkpoint label predicating the section on a new wife or "
        "female friend.",
    ),
    word(103, 6, "HEAD", R, "p103_role_head_l1", routes=(SECTION_L,)),
    word(103, 6, "WIFE", R, "p103_role_wife_l1", routes=(SECTION_L,)),
    line(103, 8, F, "p103_flow_l1_female_head", routes=(SECTION_L,)),
    line(103, 9, F, "p103_flow_l1_no_wife", routes=(SECTION_L,)),
    line(103, 10, F, "p103_flow_l1_same_wife", routes=(SECTION_L,)),
    line(
        103,
        38,
        C,
        "p103_l10_years_worked",
        routes=(L1_NEW_WIFE,),
        note="L10 prints the lifetime years-worked exposure field.",
    ),
    line(103, 38, P, "p103_l10_prompt", routes=(L1_NEW_WIFE,)),
    line(
        103,
        43,
        C,
        "p103_l11_years_full_time",
        routes=(L1_NEW_WIFE,),
        note="L11 prints the lifetime full-time years exposure field.",
    ),
    line(103, 43, P, "p103_l11_prompt", routes=(L1_NEW_WIFE,)),
    word(
        103,
        47,
        "TURN TO P. 55 , SECTimJ f.1",
        F,
        "p103_flow_l11_exit",
        routes=(L1_NEW_WIFE,),
    ),
    block(
        103,
        49,
        50,
        C,
        "p103_l12_part_time_share",
        routes=(L1_NEW_WIFE,),
        note="L12 prints the part-time work-share exposure field.",
    ),
    block(103, 49, 50, P, "p103_l12_prompt", routes=(L1_NEW_WIFE,)),
)

# Page 105 - section M entry and new-head first-job items M4-M5.
PAGE_105 = (
    tail(
        105,
        4,
        "SECTION M:",
        F,
        "p105_flow_section_m",
        note="Printed section M header opening the new-head schedule.",
    ),
    line(
        105,
        9,
        F,
        "p105_flow_m1_new_head",
        routes=(SECTION_M,),
        note="M1 checkpoint label predicating the section on a new head.",
    ),
    word(105, 9, "HEAD", R, "p105_role_head_m1", routes=(SECTION_M,)),
    line(105, 11, F, "p105_flow_m1_same_head", routes=(SECTION_M,)),
    line(
        105,
        34,
        C,
        "p105_m4_first_job_occupation",
        routes=(M1_NEW_HEAD,),
        parents=("p105_job_first_full_time",),
        parent_note="Parent job is the printed first-job noun on this "
        "screen.",
        note="M4 prints the first-full-time-job occupation field.",
    ),
    line(105, 34, P, "p105_m4_prompt", routes=(M1_NEW_HEAD,)),
    word(105, 34, "HEAD", R, "p105_role_head_m4", routes=(M1_NEW_HEAD,)),
    word(
        105,
        34,
        "full-time regular job",
        J,
        "p105_job_first_full_time",
        routes=(M1_NEW_HEAD,),
        note="M4 names the head's first full-time regular job by its printed "
        "job noun.",
    ),
    word(
        105,
        37,
        "TURN TO P. 56, M6",
        F,
        "p105_flow_m4_never_worked",
        routes=(M1_NEW_HEAD,),
    ),
    block(
        105,
        40,
        41,
        C,
        "p105_m5_occupation_count",
        routes=(M1_NEW_HEAD,),
        note="M5 prints the number-of-occupations work-history field.",
    ),
    block(105, 40, 41, P, "p105_m5_prompt", routes=(M1_NEW_HEAD,)),
)

# Page 109 - new-head lifetime work items M25-M27.
PAGE_109 = (
    line(
        109,
        33,
        C,
        "p109_m25_years_worked",
        routes=(M1_NEW_HEAD,),
        note="M25 prints the lifetime years-worked exposure field.",
    ),
    line(109, 33, P, "p109_m25_prompt", routes=(M1_NEW_HEAD,)),
    line(
        109,
        37,
        C,
        "p109_m26_years_full_time",
        routes=(M1_NEW_HEAD,),
        note="M26 prints the lifetime full-time years exposure field.",
    ),
    line(109, 37, P, "p109_m26_prompt", routes=(M1_NEW_HEAD,)),
    word(
        109,
        39,
        "TURt~ TO P. 58, fl28",
        F,
        "p109_flow_m26_exit",
        routes=(M1_NEW_HEAD,),
    ),
    block(
        109,
        42,
        43,
        C,
        "p109_m27_part_time_share",
        routes=(M1_NEW_HEAD,),
        note="M27 prints the part-time work-share exposure field.",
    ),
    block(109, 42, 43, P, "p109_m27_prompt", routes=(M1_NEW_HEAD,)),
)

REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_11,
    *PAGE_13,
    *PAGE_15,
    *PAGE_17,
    *PAGE_19,
    *PAGE_25,
    *PAGE_27,
    *PAGE_29,
    *PAGE_31,
    *PAGE_33,
    *PAGE_37,
    *PAGE_39,
    *PAGE_41,
    *PAGE_43,
    *PAGE_45,
    *PAGE_47,
    *PAGE_49,
    *PAGE_51,
    *PAGE_53,
    *PAGE_67,
    *PAGE_69,
    *PAGE_71,
    *PAGE_73,
    *PAGE_79,
    *PAGE_103,
    *PAGE_105,
    *PAGE_109,
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
        f"document 25 source review: {len(review['occurrence_specs'])} "
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
