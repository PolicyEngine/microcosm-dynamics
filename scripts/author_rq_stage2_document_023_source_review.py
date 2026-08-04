#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 23.

``fam1979_QxQs.pdf`` is a 122-page scan of the 1979 family instrument bound
together with its question-by-question interviewer objectives.  Pages 1, 3 and
4 are printed instrument screens, pages 2, 5 and 6 are objectives sheets, and
from page 7 onwards every odd page is an instrument screen and every even page
is its facing objectives sheet.  All 122 pages were read from the
authenticated Poppler text before this file was written, and the stage-1
candidate artifact is never opened here; the sealed annotation builder joins
candidates only after these reviewer rows exist.

Reviewer scope decisions recorded by this file:

* Occurrences are emitted only on printed *instrument* screens inside the
  retained employment, work-income, and lifetime-work-history regions.  The
  question-by-question objective pages are interviewer commentary keyed to a
  question; they restate worklike vocabulary but print no field, so they carry
  no source occurrence.
* Cover, transportation, housing/utility, residential-mobility, housework,
  food and food-stamp, child-care, medical, dependent-support, savings,
  schooling, growing-up, religion, and observation regions contribute no
  occurrence merely because nearby prose contains worklike words.
* A retained ``context_anchor`` must print a field that maps to a ratified
  section-19 field purpose (assignment, occupation, industry, employee/self,
  government level, incorporation, job identifier, reporting unit, or
  month/exposure).  Labour-union membership, commuting, counterfactual
  labour-supply preference, job-search effort, training requirement,
  residential-mobility willingness, health limitation, prospective
  job-intention, transfer-receipt, and schooling fields are printed
  work-adjacent questions that map to no such purpose and are rejected.
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
  encloses it.  The section-header branch is the most recent *preceding*
  printed header for that section.  A printed forward routing atom is itself a
  branch label, but it does not re-parent the screen it jumps to, because that
  screen is administered identically on fall-through.
* This is an early scan and its OCR is lossy.  Destroyed printed bytes are
  never reconstructed.  A routing atom is retained only where the printed
  bytes still separate its directive verb from its target, and a role anchor
  is retained only where the printed role lexeme survives the scan intact —
  which is why several screens that plainly concern the head or the wife carry
  no role anchor.
* Several instrument screens are photographed twice or three times, once
  before each objectives sheet that discusses them: pages 7/9, 17/19,
  21/23/25, 83/85, 87/89 and 91/93.  Each reprint is a distinct printed
  occurrence at distinct coordinates and is annotated separately.  The
  reprinted section K header opens its own branch, under which the reprinted
  and following K screens resolve.  No local alias binds a reprint to its
  first printing; that equivalence is left entirely to global assembly.
* The 1979 pay-rate screens photograph two answer columns side by side.  No
  emitted span crosses the printed column gutter; a component anchor on those
  screens is the exact contiguous printed run inside one column.
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
import build_rq_stage2_document_023_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 122


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


def resolve_run(
    page_text: str, line_number: int, first_token: int, last_token: int
) -> tuple[int, int]:
    """Span one contiguous printed token run inside a physical line.

    The 1979 manual is an early scan whose answer columns are photographed
    side by side, so a whole-line span can cross the printed column gutter
    and a multi-word needle depends on scan-dependent inter-word spacing.
    Addressing a printed run by its whitespace-delimited token positions
    keeps the emitted span an exact contiguous slice of the printed bytes.
    """

    line_start, line_end = resolve_line(page_text, line_number)
    raw = page_text.encode("utf-8")
    segment = raw[line_start:line_end]
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
    if not 0 <= first_token <= last_token < len(offsets):
        raise SpecError(
            f"token run {first_token}-{last_token} is outside line "
            f"{line_number}"
        )
    return (
        line_start + offsets[first_token][0],
        line_start + offsets[last_token][1],
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


_INSTRUMENT_OUT = (
    "Printed instrument screen for {}; read line by line and outside the "
    "employment, work-income, and work-history occurrence domain, so its "
    "worklike vocabulary retains no source occurrence."
)
_OBJECTIVES = (
    "Question-by-question interviewer objectives for {}; commentary keyed to "
    "printed questions rather than printed fields, so no source occurrence "
    "is retained."
)
_INSTRUMENT_IN = (
    "Printed instrument screen for {}; read line by line and retained as "
    "source for the section-19 occurrence domain."
)

_INSTRUMENT_NONE = (
    "Printed instrument screen for {}; read line by line inside the retained "
    "employment region, but every printed field is {}, so no source "
    "occurrence is retained."
)
PAGE_NOTES: dict[int, str] = {
    1: _INSTRUMENT_OUT.format(
        "the interviewer face sheet, office-use box, and section A "
        "transportation items A1-A2"
    ),
    2: _OBJECTIVES.format(
        "the questionnaire reminder, the editing-box note, and section A "
        "items A1-A2"
    ),
    3: _INSTRUMENT_OUT.format("section A transportation items A3-A8"),
    4: _INSTRUMENT_OUT.format("section A own-repair items A9-A17"),
    5: _OBJECTIVES.format("section A items A3-A8"),
    6: _OBJECTIVES.format("section A items A9-A17"),
    7: _INSTRUMENT_OUT.format(
        "section B housing, utility, and mortgage items B1-B11"
    ),
    8: _OBJECTIVES.format("section B items B1-B5"),
    9: _INSTRUMENT_OUT.format(
        "the reprinted section B housing, utility, and mortgage screen B1-B11"
    ),
    10: _OBJECTIVES.format("section B items B6-B11"),
    11: _INSTRUMENT_OUT.format("section B rent and utility items B12-B20"),
    12: _OBJECTIVES.format("section B items B12-B20"),
    13: _INSTRUMENT_OUT.format("section B residential-mobility items B21-B26"),
    14: _OBJECTIVES.format(
        "the you-(HEAD) convention and section B items B21-B26"
    ),
    15: _INSTRUMENT_OUT.format(
        "section B own-repair and remodelling items B27-B35"
    ),
    16: _OBJECTIVES.format("section B items B27-B35"),
    17: _INSTRUMENT_IN.format("section C head employment items C1-C5"),
    18: _OBJECTIVES.format(
        "section C item C1 and the working/unemployed/not-in-labour-force "
        "definitions"
    ),
    19: _INSTRUMENT_IN.format(
        "the reprinted section C head employment screen C1-C5"
    ),
    20: _OBJECTIVES.format("section C items C2-C5"),
    21: _INSTRUMENT_IN.format(
        "section C head occupation, industry, tenure, and job-change items "
        "C6-C15"
    ),
    22: _OBJECTIVES.format(
        "section C items C6 and C7 and the census occupation coding "
        "instructions"
    ),
    23: _INSTRUMENT_IN.format(
        "the first reprint of the section C occupation, industry, tenure, and "
        "job-change screen C6-C15"
    ),
    24: _OBJECTIVES.format(
        "section C items C6-C9 and the occupation and industry probe lists"
    ),
    25: _INSTRUMENT_IN.format(
        "the second reprint of the section C occupation, industry, tenure, "
        "and job-change screen C6-C15"
    ),
    26: _OBJECTIVES.format("section C items C10-C15"),
    27: _INSTRUMENT_IN.format(
        "section C head work-time exposure items C16-C23"
    ),
    28: _OBJECTIVES.format("section C items C16-C23"),
    29: _INSTRUMENT_IN.format(
        "section C head unemployment exposure, weeks, hours, and overtime "
        "items C24-C29"
    ),
    30: _OBJECTIVES.format("section C items C24-C29"),
    31: _INSTRUMENT_IN.format(
        "section C head pay-form, wage-rate, and extra-job items C30-C40"
    ),
    32: _OBJECTIVES.format("section C items C30-C40"),
    33: _INSTRUMENT_IN.format(
        "section C head extra-job pay and hours items C41-C50"
    ),
    34: _OBJECTIVES.format("section C items C41-C50"),
    35: _INSTRUMENT_NONE.format(
        "section C head commuting, job-search, and residential-mobility items "
        "C51-C57",
        "a commuting, job-search, or residential-mobility field that maps to "
        "no ratified section-19 field purpose",
    ),
    36: _OBJECTIVES.format("section C items C51-C57"),
    37: _INSTRUMENT_IN.format("section D head job-search items D1-D7"),
    38: _OBJECTIVES.format("section D items D1-D7"),
    39: _INSTRUMENT_IN.format(
        "section D head mobility and last-job items D8-D16"
    ),
    40: _OBJECTIVES.format("section D items D8-D16"),
    41: _INSTRUMENT_IN.format(
        "section D head work-time exposure items D17-D25"
    ),
    42: _OBJECTIVES.format("section D items D17-D25"),
    43: _INSTRUMENT_IN.format(
        "section D head unemployment exposure, weeks, hours, and commuting "
        "items D26-D32"
    ),
    44: _OBJECTIVES.format("section D items D26-D32"),
    45: _INSTRUMENT_IN.format(
        "section E head retirement and money-work items E1-E9"
    ),
    46: _OBJECTIVES.format("section E items E1-E9"),
    47: _INSTRUMENT_NONE.format(
        "section E head future-job intention items E10-E15",
        "a prospective job-intention, training-requirement, or job-search "
        "field that maps to no ratified section-19 field purpose",
    ),
    48: _OBJECTIVES.format("section E items E10-E15"),
    49: _INSTRUMENT_IN.format("section F wife employment items F1-F6"),
    50: _OBJECTIVES.format(
        "section F items F1-F6 and the parallel-to-C-D-E instruction"
    ),
    51: _INSTRUMENT_IN.format(
        "section F wife occupation, industry, tenure, and job-change items "
        "F7-F13"
    ),
    52: _OBJECTIVES.format("section F items F7-F13"),
    53: _INSTRUMENT_IN.format(
        "section F wife work-time exposure items F14-F23"
    ),
    54: _OBJECTIVES.format("section F items F14-F23"),
    55: _INSTRUMENT_IN.format(
        "section F wife weeks, hours, overtime, pay-form, and wage-rate items "
        "F24-F30"
    ),
    56: _OBJECTIVES.format("section F items F24-F30"),
    57: _INSTRUMENT_IN.format(
        "section F wife extra-job and commuting items F31-F37"
    ),
    58: _OBJECTIVES.format("section F items F31-F37"),
    59: _INSTRUMENT_IN.format(
        "section G wife job-search and last-job items G1-G9"
    ),
    60: _OBJECTIVES.format("section G items G1-G9"),
    61: _INSTRUMENT_IN.format(
        "section G wife work-time exposure items G10-G18"
    ),
    62: _OBJECTIVES.format("section G items G10-G18"),
    63: _INSTRUMENT_IN.format(
        "section G wife unemployment exposure, weeks, hours, and commuting "
        "items G19-G25"
    ),
    64: _OBJECTIVES.format("section G items G19-G25"),
    65: _INSTRUMENT_IN.format(
        "section H wife retirement and money-work items H1-H9"
    ),
    66: _OBJECTIVES.format("section H items H1-H9"),
    67: _INSTRUMENT_NONE.format(
        "section H wife future-job intention items H10-H12",
        "a prospective job-intention or job-search field that maps to no "
        "ratified section-19 field purpose",
    ),
    68: _OBJECTIVES.format("section H items H10-H12"),
    69: _INSTRUMENT_OUT.format(
        "section J marital-status and housework items J1-J6"
    ),
    70: _OBJECTIVES.format("section J items J1-J6"),
    71: _INSTRUMENT_OUT.format(
        "section J household-help housework items J7-J11"
    ),
    72: _OBJECTIVES.format("section J items J7-J11"),
    73: _INSTRUMENT_OUT.format(
        "section J current food-stamp and food-expenditure items J12-J20"
    ),
    74: _OBJECTIVES.format("section J items J12-J20"),
    75: _INSTRUMENT_OUT.format(
        "section J food-expenditure and 1978 food-stamp items J21-J28"
    ),
    76: _OBJECTIVES.format("section J items J21-J28"),
    77: _INSTRUMENT_OUT.format("section J home-raised-food items J29-J35"),
    78: _OBJECTIVES.format("section J items J29-J35"),
    79: _INSTRUMENT_OUT.format(
        "section J child-care checkpoint and arrangement items J36-J40"
    ),
    80: _OBJECTIVES.format("section J items J36-J40"),
    81: _INSTRUMENT_OUT.format("section J child-care cost items J41-J46"),
    82: _OBJECTIVES.format("section J items J41-J46"),
    83: _INSTRUMENT_IN.format(
        "section K farm, business, and wage-and-salary income items K1-K8"
    ),
    84: _OBJECTIVES.format(
        "the section K income-and-hours matching note and section K items "
        "K1-K3"
    ),
    85: _INSTRUMENT_IN.format(
        "the reprinted section K farm, business, and wage-and-salary income "
        "screen K1-K8"
    ),
    86: _OBJECTIVES.format("section K items K3-K8"),
    87: _INSTRUMENT_IN.format(
        "section K supplementary earnings and other-income-source items "
        "K9-K13"
    ),
    88: _OBJECTIVES.format("section K items K9-K11d"),
    89: _INSTRUMENT_IN.format(
        "the reprinted section K supplementary earnings and other-income- "
        "source screen K9-K13"
    ),
    90: _OBJECTIVES.format("section K items K11d-K13"),
    91: _INSTRUMENT_NONE.format(
        "section K welfare-detail and social-security, pension, and transfer "
        "items K14-K20",
        "a public-assistance, social-security, pension, or private-transfer "
        "receipt field rather than a remuneration or work-context field",
    ),
    92: _OBJECTIVES.format("section K items K14-K18b"),
    93: _INSTRUMENT_NONE.format(
        "the reprinted section K welfare-detail and transfer screen K14-K20",
        "a public-assistance, social-security, pension, or private-transfer "
        "receipt field rather than a remuneration or work-context field",
    ),
    94: _OBJECTIVES.format("section K items K18c-K20"),
    95: _INSTRUMENT_NONE.format(
        "section K outside-help and wife-income items K21-K33",
        "destroyed by the scan: the printed question and answer bytes on this "
        "screen do not survive Poppler extraction as legible printed units, "
        "and no span is reconstructed",
    ),
    96: _OBJECTIVES.format("section K items K21-K33"),
    97: _INSTRUMENT_IN.format(
        "the section K extra-earner listing and eligibility checkpoint "
        "K34-K35"
    ),
    98: _OBJECTIVES.format(
        "section K items K34-K35 and the extra-earner supplement instructions"
    ),
    99: _INSTRUMENT_IN.format(
        "the section K first extra-earner assignment, work, and earnings "
        "items K36-K44"
    ),
    100: _OBJECTIVES.format("section K items K36-K44"),
    101: _INSTRUMENT_IN.format(
        "the section K first extra-earner unemployment, schooling, and repeat "
        "checkpoint items K45-K50"
    ),
    102: _OBJECTIVES.format("section K items K45-K50"),
    103: _INSTRUMENT_NONE.format(
        "section K other-household-member income and medical-care items "
        "K51-K57",
        "a residual household-member income or medical-programme field rather "
        "than a remuneration or work-context field",
    ),
    104: _OBJECTIVES.format("section K items K51-K57"),
    105: _INSTRUMENT_NONE.format(
        "section K lump-sum, outside-support, and dependency items K58-K65",
        "a lump-sum receipt, outside-support, or dependency field rather than "
        "a remuneration or work-context field",
    ),
    106: _OBJECTIVES.format("section K items K58-K65"),
    107: _INSTRUMENT_NONE.format(
        "section K savings and inflation items K66-K74",
        "a savings, price-increase, or retirement-expectation field rather "
        "than a remuneration or work-context field",
    ),
    108: _OBJECTIVES.format("section K items K66-K73"),
    109: _INSTRUMENT_NONE.format(
        "section K labour-union and work-limitation items K75-K79",
        "a labour-union membership or health-limitation field that maps to no "
        "ratified section-19 field purpose",
    ),
    110: _OBJECTIVES.format(
        "section K items K75-K81 and the reprinted-page note"
    ),
    111: _INSTRUMENT_IN.format(
        "section L new-wife schooling and lifetime work-history items L1-L12"
    ),
    112: _OBJECTIVES.format("section L items L1-L12"),
    113: _INSTRUMENT_IN.format(
        "section M new-head background and first-job items M1-M5"
    ),
    114: _OBJECTIVES.format("section M items M1-M5"),
    115: _INSTRUMENT_OUT.format(
        "section M new-head children, sibling, and growing-up items M6-M16"
    ),
    116: _OBJECTIVES.format("section M items M6-M16"),
    117: _INSTRUMENT_IN.format(
        "section M new-head mobility, parental-background, and lifetime work- "
        "history items M17-M27"
    ),
    118: _OBJECTIVES.format("section M items M17-M27"),
    119: _INSTRUMENT_OUT.format(
        "section M new-head schooling, reading, and religious-preference "
        "items M28-M39"
    ),
    120: _OBJECTIVES.format("section M items M28-M39"),
    121: _INSTRUMENT_OUT.format(
        "the section N observation-only items N1-N2 and the thumbnail-sketch "
        "instruction"
    ),
    122: _OBJECTIVES.format(
        "the section N observation-only items and the thumbnail-sketch "
        "instruction"
    ),
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

SECTION_C = ("p17_flow_section_c",)
_JOB_PRESENT = (
    "Parent is the screen's printed present-position job anchor, which "
    "governs its occupation, industry, tenure, and start-month fields."
)
_JOB_MAIN = (
    "Parent is the screen's printed main-job anchor, which governs its "
    "weeks, hours, and overtime exposure fields."
)
_JOB_EXTRA = (
    "Parent is the screen's printed extra-job anchor, which governs its "
    "extra-job pay, weeks, and hours fields."
)
_COLUMN_NOTE = (
    "The 1979 pay-rate screen photographs two answer columns side by side, "
    "so this span is the exact contiguous printed run inside one column; no "
    "span is carried across the printed column gutter."
)

# Page 17 - section C entry and head employment items C1-C5.
PAGE_17 = (
    line(
        17,
        1,
        F,
        "p17_flow_section_c",
        note="Printed section C header conditions the head employment "
        "schedule selected at C1.",
    ),
    block(
        17,
        8,
        9,
        C,
        "p17_c1_assignment",
        routes=(SECTION_C,),
        note="C1 prints the head labour-force assignment field.",
    ),
    block(17, 8, 9, P, "p17_c1_prompt", routes=(SECTION_C,)),
    run(
        17,
        17,
        0,
        3,
        F,
        "p17_flow_c1_turn_section_d",
        routes=(SECTION_C,),
        note="C1 routing atom into the section D schedule; the printed "
        "target section name prints on a separate physical line of the "
        "scanned answer column and is not spanned.",
    ),
    run(
        17,
        21,
        0,
        4,
        F,
        "p17_flow_c1_turn_section_e",
        routes=(SECTION_C,),
        note="C1 routing atom into the section E schedule.",
    ),
    word(
        17,
        32,
        "HEAD",
        R,
        "p17_role_head_c1",
        routes=(SECTION_C,),
        note="Earliest legible printed HEAD lexeme on the screen; the "
        "section header and C1 stem print the same role through "
        "scan-destroyed bytes and are not retained as role anchors.",
    ),
    run(
        17,
        32,
        0,
        6,
        F,
        "p17_flow_c1_head_has_job",
        routes=(SECTION_C,),
        note="C1 conditional routing atom that predicates the remaining "
        "section C screens on the head holding a job.",
    ),
    run(
        17,
        33,
        0,
        4,
        F,
        "p17_flow_c1_otherwise_section_e",
        routes=(SECTION_C,),
    ),
    line(
        17,
        41,
        C,
        "p17_c2_employee_self",
        routes=(SECTION_C,),
        note="C2 prints the employee/self-employed field.",
    ),
    line(17, 41, P, "p17_c2_prompt", routes=(SECTION_C,)),
    run(17, 45, 0, 4, F, "p17_flow_c2_self_only", routes=(SECTION_C,)),
    block(
        17,
        48,
        49,
        C,
        "p17_c3_government",
        routes=(SECTION_C,),
        note="C3 prints the federal/state/local government-level field.",
    ),
    block(17, 48, 49, P, "p17_c3_prompt", routes=(SECTION_C,)),
    run(17, 56, 0, 5, F, "p17_flow_c4_no_union", routes=(SECTION_C,)),
)

# Page 19 - the reprinted section C screen C1-C5.
PAGE_19 = (
    block(
        19,
        1,
        2,
        C,
        "p19_c1_assignment",
        routes=(SECTION_C,),
        note="Reprinted C1 head labour-force assignment field at distinct "
        "printed coordinates.",
    ),
    block(19, 1, 2, P, "p19_c1_prompt", routes=(SECTION_C,)),
    run(19, 14, 0, 3, F, "p19_flow_c1_turn_section_d", routes=(SECTION_C,)),
    run(19, 17, 0, 4, F, "p19_flow_c1_turn_section_e", routes=(SECTION_C,)),
    run(
        19,
        27,
        0,
        6,
        F,
        "p19_flow_c1_head_has_job",
        routes=(SECTION_C,),
        note="Reprinted C1 conditional routing atom; its printed HEAD "
        "lexeme is scan-destroyed and carries no role anchor.",
    ),
    run(
        19,
        29,
        0,
        4,
        F,
        "p19_flow_c1_otherwise_section_e",
        routes=(SECTION_C,),
    ),
    line(19, 33, C, "p19_c2_employee_self", routes=(SECTION_C,)),
    line(19, 33, P, "p19_c2_prompt", routes=(SECTION_C,)),
    run(19, 37, 1, 5, F, "p19_flow_c2_self_only", routes=(SECTION_C,)),
    block(
        19,
        40,
        42,
        C,
        "p19_c3_government",
        routes=(SECTION_C,),
        note="Reprinted C3 government-level field; the printed identifier "
        "line carries a scan artifact that is retained verbatim.",
    ),
    block(19, 40, 42, P, "p19_c3_prompt", routes=(SECTION_C,)),
    run(19, 49, 3, 8, F, "p19_flow_c4_no_union", routes=(SECTION_C,)),
)

# Pages 21, 23, 25 - the section C occupation/industry/tenure screen and its
# two printed reprints.
PAGE_21 = (
    line(
        21,
        2,
        C,
        "p21_c6_occupation",
        routes=(SECTION_C,),
        parents=("p21_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="C6 prints the head main-occupation field.",
    ),
    line(21, 2, P, "p21_c6_prompt", routes=(SECTION_C,)),
    line(
        21,
        7,
        C,
        "p21_c7_occupation_detail",
        routes=(SECTION_C,),
        parents=("p21_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(21, 7, P, "p21_c7_prompt", routes=(SECTION_C,)),
    line(
        21,
        12,
        C,
        "p21_c8_industry",
        routes=(SECTION_C,),
        parents=("p21_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="C8 prints the head industry field.",
    ),
    line(21, 12, P, "p21_c8_prompt", routes=(SECTION_C,)),
    word(
        21,
        16,
        "present position",
        J,
        "p21_job_present_position",
        routes=(SECTION_C,),
    ),
    line(
        21,
        16,
        C,
        "p21_c9_tenure",
        routes=(SECTION_C,),
        parents=("p21_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="C9 prints the head present-position tenure field.",
    ),
    line(21, 16, P, "p21_c9_prompt", routes=(SECTION_C,)),
    line(
        21,
        24,
        F,
        "p21_flow_c10_less_than_year",
        routes=(SECTION_C,),
        note="C10 interviewer checkpoint branch A: present position held "
        "less than one year.",
    ),
    run(
        21,
        26,
        0,
        10,
        F,
        "p21_flow_c10_year_or_more",
        routes=(SECTION_C,),
        note="C10 interviewer checkpoint branch B: present position held "
        "one year or more.",
    ),
    run(21, 26, 11, 15, F, "p21_flow_c10_turn_c16", routes=(SECTION_C,)),
    line(
        21,
        27,
        C,
        "p21_c11_start_month",
        routes=(SECTION_C + ("p21_flow_c10_less_than_year",),),
        parents=("p21_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="C11 prints the start-month exposure field for the present "
        "position and is administered only under the C10 less-than-a-year "
        "checkpoint branch.",
    ),
    line(
        21,
        27,
        P,
        "p21_c11_prompt",
        routes=(SECTION_C + ("p21_flow_c10_less_than_year",),),
    ),
    run(
        21,
        34,
        0,
        4,
        F,
        "p21_flow_c12_no_previous_job",
        routes=(SECTION_C + ("p21_flow_c10_less_than_year",),),
    ),
)

PAGE_23 = (
    line(
        23,
        11,
        C,
        "p23_c7_occupation_detail",
        routes=(SECTION_C,),
        parents=("p23_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="Reprinted C7; the reprinted C6 stem on this screen is "
        "scan-destroyed beyond its printed identifier and is not retained.",
    ),
    line(23, 11, P, "p23_c7_prompt", routes=(SECTION_C,)),
    line(
        23,
        16,
        C,
        "p23_c8_industry",
        routes=(SECTION_C,),
        parents=("p23_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(23, 16, P, "p23_c8_prompt", routes=(SECTION_C,)),
    word(
        23,
        19,
        "present position",
        J,
        "p23_job_present_position",
        routes=(SECTION_C,),
    ),
    line(
        23,
        19,
        C,
        "p23_c9_tenure",
        routes=(SECTION_C,),
        parents=("p23_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(23, 19, P, "p23_c9_prompt", routes=(SECTION_C,)),
    run(
        23,
        30,
        0,
        10,
        F,
        "p23_flow_c10_year_or_more",
        routes=(SECTION_C,),
        note="Reprinted C10 checkpoint branch B; branch A prints on this "
        "screen through scan-destroyed bytes and is not retained.",
    ),
    run(23, 30, 11, 15, F, "p23_flow_c10_turn_c16", routes=(SECTION_C,)),
    run(
        23,
        33,
        1,
        8,
        C,
        "p23_c11_start_month",
        routes=(SECTION_C,),
        parents=("p23_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="Reprinted C11 start-month exposure field; the printed C10 "
        "branch A label that gates it is scan-destroyed on this screen, so "
        "only the retained section ancestry is claimed.",
    ),
    run(23, 33, 1, 8, P, "p23_c11_prompt", routes=(SECTION_C,)),
    run(23, 40, 0, 5, F, "p23_flow_c12_no_previous_job", routes=(SECTION_C,)),
)

PAGE_25 = (
    line(
        25,
        1,
        C,
        "p25_c6_occupation",
        routes=(SECTION_C,),
        parents=("p25_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(25, 1, P, "p25_c6_prompt", routes=(SECTION_C,)),
    line(
        25,
        6,
        C,
        "p25_c7_occupation_detail",
        routes=(SECTION_C,),
        parents=("p25_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(25, 6, P, "p25_c7_prompt", routes=(SECTION_C,)),
    line(
        25,
        12,
        C,
        "p25_c8_industry",
        routes=(SECTION_C,),
        parents=("p25_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(25, 12, P, "p25_c8_prompt", routes=(SECTION_C,)),
    word(
        25,
        16,
        "present position",
        J,
        "p25_job_present_position",
        routes=(SECTION_C,),
    ),
    line(
        25,
        16,
        C,
        "p25_c9_tenure",
        routes=(SECTION_C,),
        parents=("p25_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(25, 16, P, "p25_c9_prompt", routes=(SECTION_C,)),
    run(
        25,
        22,
        1,
        10,
        F,
        "p25_flow_c10_less_than_year",
        routes=(SECTION_C,),
    ),
    run(25, 23, 1, 10, F, "p25_flow_c10_year_or_more", routes=(SECTION_C,)),
    run(25, 23, 11, 15, F, "p25_flow_c10_turn_c16", routes=(SECTION_C,)),
    line(
        25,
        26,
        C,
        "p25_c11_start_month",
        routes=(SECTION_C + ("p25_flow_c10_less_than_year",),),
        parents=("p25_job_present_position",),
        parent_note=_JOB_PRESENT,
    ),
    line(
        25,
        26,
        P,
        "p25_c11_prompt",
        routes=(SECTION_C + ("p25_flow_c10_less_than_year",),),
    ),
    run(
        25,
        33,
        0,
        4,
        F,
        "p25_flow_c12_no_previous_job",
        routes=(SECTION_C + ("p25_flow_c10_less_than_year",),),
    ),
)

# Page 27 - section C head work-time exposure items C16-C23.
PAGE_27 = (
    line(
        27,
        3,
        C,
        "p27_c16_missed_family_sick",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C16 prints a 1978 work-time exposure field for the head.",
    ),
    line(27, 3, P, "p27_c16_prompt", routes=(SECTION_C,)),
    run(27, 6, 0, 3, F, "p27_flow_c16_no", routes=(SECTION_C,)),
    line(
        27,
        8,
        C,
        "p27_c17_amount",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(27, 8, P, "p27_c17_prompt", routes=(SECTION_C,)),
    line(
        27,
        14,
        C,
        "p27_c18_missed_own_sick",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(27, 14, P, "p27_c18_prompt", routes=(SECTION_C,)),
    run(27, 20, 3, 6, F, "p27_flow_c18_no", routes=(SECTION_C,)),
    line(
        27,
        22,
        C,
        "p27_c19_amount",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(27, 22, P, "p27_c19_prompt", routes=(SECTION_C,)),
    line(
        27,
        27,
        C,
        "p27_c20_vacation",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="Vacation and time-off exposure field; the printed item "
        "identifier is scanned as C40 and is retained verbatim.",
    ),
    line(27, 27, P, "p27_c20_prompt", routes=(SECTION_C,)),
    line(
        27,
        32,
        C,
        "p27_c21_amount",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(27, 32, P, "p27_c21_prompt", routes=(SECTION_C,)),
    line(
        27,
        40,
        C,
        "p27_c22_strike",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="Strike exposure field; the printed item identifier is scanned "
        "as C44 and is retained verbatim.",
    ),
    line(27, 40, P, "p27_c22_prompt", routes=(SECTION_C,)),
    run(27, 43, 0, 4, F, "p27_flow_c22_no", routes=(SECTION_C,)),
    line(
        27,
        45,
        C,
        "p27_c23_amount",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(27, 45, P, "p27_c23_prompt", routes=(SECTION_C,)),
)

# Page 29 - section C unemployment exposure, weeks, hours, overtime C24-C29.
PAGE_29 = (
    block(
        29,
        3,
        4,
        C,
        "p29_c24_unemployed",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    block(29, 3, 4, P, "p29_c24_prompt", routes=(SECTION_C,)),
    run(29, 6, 0, 3, F, "p29_flow_c24_no", routes=(SECTION_C,)),
    line(
        29,
        9,
        C,
        "p29_c25_amount",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(29, 9, P, "p29_c25_prompt", routes=(SECTION_C,)),
    line(
        29,
        15,
        C,
        "p29_c26_weeks_worked",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(29, 15, P, "p29_c26_prompt", routes=(SECTION_C,)),
    word(29, 19, "main job", J, "p29_job_main_job", routes=(SECTION_C,)),
    block(
        29,
        19,
        20,
        C,
        "p29_c27_hours_per_week",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    block(29, 19, 20, P, "p29_c27_prompt", routes=(SECTION_C,)),
    line(
        29,
        25,
        C,
        "p29_c28_overtime",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C28 prints an overtime work-time exposure field for the "
        "head's main job.",
    ),
    line(29, 25, P, "p29_c28_prompt", routes=(SECTION_C,)),
    run(29, 28, 3, 7, F, "p29_flow_c28_no", routes=(SECTION_C,)),
    line(
        29,
        30,
        C,
        "p29_c29_overtime_hours",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(29, 30, P, "p29_c29_prompt", routes=(SECTION_C,)),
)

# Page 31 - section C pay-form, wage-rate, and extra-job items C30-C40.
PAGE_31 = (
    line(
        31,
        1,
        C,
        "p31_c30_pay_form",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C30 prints the salaried/hourly pay-form field for the head's "
        "main job.",
    ),
    line(31, 1, P, "p31_c30_prompt", routes=(SECTION_C,)),
    run(
        31,
        9,
        0,
        0,
        M,
        "p31_c31_salary",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C31 salary component; " + _COLUMN_NOTE,
    ),
    run(
        31,
        9,
        1,
        3,
        M,
        "p31_c34_regular_wage_rate",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C34 regular-work hourly wage-rate component; the scan splits "
        "the printed word rate. " + _COLUMN_NOTE,
    ),
    run(
        31,
        22,
        0,
        1,
        M,
        "p31_c35_overtime_wage_rate",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C35 overtime hourly wage-rate component. " + _COLUMN_NOTE,
    ),
    run(
        31,
        30,
        9,
        14,
        M,
        "p31_c37_extra_hour_earnings",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C37 extra-hour earnings component. " + _COLUMN_NOTE,
    ),
    run(31, 32, 0, 3, F, "p31_flow_c32_go_to_c38", routes=(SECTION_C,)),
    run(
        31,
        34,
        0,
        4,
        M,
        "p31_c33_extra_hour_rate",
        routes=(SECTION_C,),
        parents=("p29_job_main_job",),
        parent_note=_JOB_MAIN,
        note="C33 extra-hours hourly-pay component. " + _COLUMN_NOTE,
    ),
    word(31, 44, "extra jobs", J, "p31_job_extra_jobs", routes=(SECTION_C,)),
    line(
        31,
        44,
        C,
        "p31_c38_extra_jobs",
        routes=(SECTION_C,),
        parents=("p31_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
        note="C38 prints the head extra-job assignment field.",
    ),
    line(31, 44, P, "p31_c38_prompt", routes=(SECTION_C,)),
    run(31, 49, 0, 4, F, "p31_flow_c38_turn_c44", routes=(SECTION_C,)),
)

# Page 33 - section C extra-job pay, weeks, and hours items C41-C50.
PAGE_33 = (
    line(
        33,
        2,
        M,
        "p33_c41_extra_job_hourly_pay",
        routes=(SECTION_C,),
        parents=("p33_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
        note="C41 prints the extra-job hourly-pay component.",
    ),
    line(33, 2, P, "p33_c41_prompt", routes=(SECTION_C,)),
    run(33, 6, 11, 14, J, "p33_job_extra_jobs", routes=(SECTION_C,)),
    line(
        33,
        6,
        C,
        "p33_c42_extra_job_weeks",
        routes=(SECTION_C,),
        parents=("p33_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
    ),
    line(33, 6, P, "p33_c42_prompt", routes=(SECTION_C,)),
    block(
        33,
        9,
        10,
        C,
        "p33_c43_extra_job_hours",
        routes=(SECTION_C,),
        parents=("p33_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
    ),
    block(33, 9, 10, P, "p33_c43_prompt", routes=(SECTION_C,)),
    run(33, 17, 2, 5, F, "p33_flow_c44_no", routes=(SECTION_C,)),
    run(33, 26, 0, 6, F, "p33_flow_c46_turn_c51", routes=(SECTION_C,)),
    run(33, 33, 0, 4, F, "p33_flow_c47_turn_c51", routes=(SECTION_C,)),
    run(33, 39, 0, 6, F, "p33_flow_c48_turn_c51", routes=(SECTION_C,)),
)


SECTION_D = ("p37_flow_section_d",)
SECTION_E = ("p45_flow_section_e",)
_JOB_SOUGHT = (
    "Parent is the printed sought-job anchor named in the same question "
    "block."
)
_JOB_LAST = (
    "Parent is the screen's printed last-job anchor, which governs its "
    "occupation, industry, and last-work exposure fields."
)
_JOB_MONEY_WORK = (
    "Parent is the printed 1978 money-work job anchor named in the same "
    "question block."
)

# Page 37 - section D entry and head job-search items D1-D7.
PAGE_37 = (
    line(
        37,
        1,
        F,
        "p37_flow_section_d",
        note="Printed section D header conditions the head job-search "
        "schedule on the unemployed assignment recorded at C1.",
    ),
    word(37, 1, "HEAD", R, "p37_role_head_header", routes=(SECTION_D,)),
    word(37, 6, "job", J, "p37_job_sought", routes=(SECTION_D,)),
    line(
        37,
        6,
        C,
        "p37_d1_sought_occupation",
        routes=(SECTION_D,),
        parents=("p37_job_sought",),
        parent_note=_JOB_SOUGHT,
        note="D1 prints the sought-job occupation field.",
    ),
    line(37, 6, P, "p37_d1_prompt", routes=(SECTION_D,)),
    line(
        37,
        11,
        M,
        "p37_d2_expected_earnings",
        routes=(SECTION_D,),
        parents=("p37_job_sought",),
        parent_note=_JOB_SOUGHT,
        note="D2 prints the expected-earnings remuneration component for "
        "the sought job.",
    ),
    line(37, 11, P, "p37_d2_prompt", routes=(SECTION_D,)),
    run(37, 21, 1, 2, F, "p37_flow_d4_no", routes=(SECTION_D,)),
    run(37, 36, 0, 4, F, "p37_flow_d6_no", routes=(SECTION_D,)),
)

# Page 39 - section D mobility, duration, and last-job items D8-D16.
PAGE_39 = (
    run(39, 24, 2, 7, F, "p39_flow_d12_never_had_job", routes=(SECTION_D,)),
    word(39, 21, "job", J, "p39_job_ever_had", routes=(SECTION_D,)),
    line(
        39,
        21,
        C,
        "p39_d12_ever_had_job",
        routes=(SECTION_D,),
        parents=("p39_job_ever_had",),
        parent_note=_JOB_LAST,
        note="D12 prints the ever-held-a-job assignment field that "
        "predicates the section D last-job block.",
    ),
    line(39, 21, P, "p39_d12_prompt", routes=(SECTION_D,)),
    word(39, 28, "last job", J, "p39_job_last", routes=(SECTION_D,)),
    line(
        39,
        28,
        C,
        "p39_d13_last_job_occupation",
        routes=(SECTION_D,),
        parents=("p39_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(39, 28, P, "p39_d13_prompt", routes=(SECTION_D,)),
    line(
        39,
        33,
        C,
        "p39_d14_last_job_industry",
        routes=(SECTION_D,),
        parents=("p39_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(39, 33, P, "p39_d14_prompt", routes=(SECTION_D,)),
    line(
        39,
        44,
        C,
        "p39_d16_last_worked",
        routes=(SECTION_D,),
        parents=("p39_job_last",),
        parent_note=_JOB_LAST,
        note="D16 prints the last-worked month/exposure field.",
    ),
    line(39, 44, P, "p39_d16_prompt", routes=(SECTION_D,)),
)

# Page 41 - section D head work-time exposure items D17-D25.
PAGE_41 = (
    line(
        41,
        3,
        F,
        "p41_flow_d17_worked",
        routes=(SECTION_D,),
        note="D17 interviewer checkpoint branch A: head worked in 1978 or "
        "1979.",
    ),
    run(
        41,
        5,
        0,
        8,
        F,
        "p41_flow_d17_did_not_work",
        routes=(SECTION_D,),
        note="D17 interviewer checkpoint branch B; the scan fuses the "
        "printed year with the routing verb, so the branch condition and "
        "its routing atom are spanned as the two printed runs that survive.",
    ),
    run(41, 5, 9, 13, F, "p41_flow_d17_turn_section_f", routes=(SECTION_D,)),
    word(41, 5, "HEAD", R, "p41_role_head_d17", routes=(SECTION_D,)),
    line(
        41,
        9,
        C,
        "p41_d18_vacation",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
        note="D18 prints a 1978 work-time exposure field administered under "
        "the D17 worked-in-1978-or-1979 checkpoint branch.",
    ),
    line(
        41,
        9,
        P,
        "p41_d18_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    run(
        41,
        11,
        3,
        6,
        F,
        "p41_flow_d18_no",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        14,
        C,
        "p41_d19_amount",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        14,
        P,
        "p41_d19_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        20,
        C,
        "p41_d20_missed_family_sick",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
        note="Family-sickness exposure field; the printed item identifier "
        "is scanned as V40 and is retained verbatim.",
    ),
    line(
        41,
        20,
        P,
        "p41_d20_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        24,
        C,
        "p41_d21_amount",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        24,
        P,
        "p41_d21_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        30,
        C,
        "p41_d22_missed_own_sick",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        30,
        P,
        "p41_d22_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        34,
        C,
        "p41_d23_amount",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        34,
        P,
        "p41_d23_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        40,
        C,
        "p41_d24_strike",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        40,
        P,
        "p41_d24_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    run(
        41,
        42,
        1,
        5,
        F,
        "p41_flow_d24_no",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        45,
        C,
        "p41_d25_amount",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
    line(
        41,
        45,
        P,
        "p41_d25_prompt",
        routes=(SECTION_D + ("p41_flow_d17_worked",),),
    ),
)

# Page 43 - section D unemployment exposure, weeks, and hours D26-D32.
PAGE_43 = (
    block(43, 1, 2, C, "p43_d26_unemployed", routes=(SECTION_D,)),
    block(43, 1, 2, P, "p43_d26_prompt", routes=(SECTION_D,)),
    run(43, 8, 0, 2, F, "p43_flow_d27_go_to_d28", routes=(SECTION_D,)),
    line(43, 7, C, "p43_d27_amount", routes=(SECTION_D,)),
    line(43, 7, P, "p43_d27_prompt", routes=(SECTION_D,)),
    word(43, 16, "job", J, "p43_job_1978", routes=(SECTION_D,)),
    line(
        43,
        16,
        C,
        "p43_d28_weeks_worked",
        routes=(SECTION_D,),
        parents=("p43_job_1978",),
        parent_note=_JOB_LAST,
    ),
    line(43, 16, P, "p43_d28_prompt", routes=(SECTION_D,)),
    line(
        43,
        19,
        C,
        "p43_d29_hours_per_week",
        routes=(SECTION_D,),
        parents=("p43_job_1978",),
        parent_note=_JOB_LAST,
    ),
    line(43, 19, P, "p43_d29_prompt", routes=(SECTION_D,)),
    run(43, 26, 1, 4, F, "p43_flow_d30_none", routes=(SECTION_D,)),
    run(43, 61, 1, 7, F, "p43_flow_d32_turn_section_f", routes=(SECTION_D,)),
)

# Page 45 - section E entry, retirement, and money-work items E1-E9.
PAGE_45 = (
    line(
        45,
        3,
        F,
        "p45_flow_section_e",
        note="Printed section E header conditions the not-in-labour-force "
        "schedule on the assignment recorded at C1.",
    ),
    word(45, 3, "HEAD", R, "p45_role_head_header", routes=(SECTION_E,)),
    line(
        45,
        9,
        F,
        "p45_flow_e1_retired",
        routes=(SECTION_E,),
        note="E1 interviewer checkpoint branch 1: head is retired.",
    ),
    block(
        45,
        11,
        12,
        F,
        "p45_flow_e1_other",
        routes=(SECTION_E,),
        note="E1 interviewer checkpoint branch 5 with its printed routing "
        "atom into E3.",
    ),
    line(
        45,
        16,
        C,
        "p45_e2_retirement_year",
        routes=(SECTION_E + ("p45_flow_e1_retired",),),
        note="E2 prints the retirement-year exposure field administered "
        "under the retired checkpoint branch.",
    ),
    line(
        45,
        16,
        P,
        "p45_e2_prompt",
        routes=(SECTION_E + ("p45_flow_e1_retired",),),
    ),
    line(
        45,
        21,
        C,
        "p45_e3_money_work",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
        note="E3 prints the 1978 money-work assignment field.",
    ),
    line(45, 21, P, "p45_e3_prompt", routes=(SECTION_E,)),
    run(45, 21, 6, 9, J, "p45_job_money_work", routes=(SECTION_E,)),
    run(45, 25, 0, 4, F, "p45_flow_e3_no", routes=(SECTION_E,)),
    line(
        45,
        27,
        C,
        "p45_e4_occupation",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
    ),
    line(45, 27, P, "p45_e4_prompt", routes=(SECTION_E,)),
    line(
        45,
        32,
        C,
        "p45_e5_industry",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
    ),
    line(45, 32, P, "p45_e5_prompt", routes=(SECTION_E,)),
    line(
        45,
        37,
        C,
        "p45_e6_weeks_worked",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
    ),
    line(45, 37, P, "p45_e6_prompt", routes=(SECTION_E,)),
    line(
        45,
        41,
        C,
        "p45_e7_hours_per_week",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
    ),
    line(45, 41, P, "p45_e7_prompt", routes=(SECTION_E,)),
    line(
        45,
        48,
        C,
        "p45_e8_still_working",
        routes=(SECTION_E,),
        parents=("p45_job_money_work",),
        parent_note=_JOB_MONEY_WORK,
    ),
    line(45, 48, P, "p45_e8_prompt", routes=(SECTION_E,)),
    run(45, 53, 0, 4, F, "p45_flow_e8_no", routes=(SECTION_E,)),
)


SECTION_F = ("p49_flow_section_f",)
SECTION_G = ("p59_flow_section_g",)
SECTION_H = ("p65_flow_section_h",)
_JOB_WIFE_PRESENT = (
    "Parent is the screen's printed wife present-position job anchor."
)
_JOB_WIFE_MAIN = "Parent is the screen's printed wife main-job anchor."
_JOB_WIFE_EXTRA = "Parent is the screen's printed wife extra-job anchor."
_JOB_WIFE_LAST = "Parent is the screen's printed wife last-job anchor."
_JOB_WIFE_MONEY = (
    "Parent is the printed 1978 money-work job anchor named in the same "
    "question block."
)

# Page 49 - section F entry and wife employment items F1-F6.
PAGE_49 = (
    line(
        49,
        1,
        F,
        "p49_flow_section_f",
        note="Printed section F header conditions the wife employment "
        "schedule selected at F2.",
    ),
    block(
        49,
        4,
        5,
        F,
        "p49_flow_f1_head_has_wife",
        routes=(SECTION_F,),
        note="F1 interviewer checkpoint branch 1: head is male with a wife "
        "in the family unit.",
    ),
    word(49, 4, "HEAD", R, "p49_role_head_f1", routes=(SECTION_F,)),
    word(49, 5, "WIFE", R, "p49_role_wife_f1", routes=(SECTION_F,)),
    run(49, 11, 1, 6, F, "p49_flow_f1_no_wife_turn_j", routes=(SECTION_F,)),
    run(
        49, 12, 5, 12, F, "p49_flow_f1_female_head_turn_j", routes=(SECTION_F,)
    ),
    block(
        49,
        13,
        14,
        C,
        "p49_f2_assignment",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
        note="F2 prints the wife labour-force assignment field.",
    ),
    block(
        49,
        13,
        14,
        P,
        "p49_f2_prompt",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    run(
        49,
        27,
        3,
        6,
        F,
        "p49_flow_f2_turn_section_h",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    run(
        49,
        37,
        0,
        6,
        F,
        "p49_flow_f2_has_job",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
        note="F2 conditional routing atom that predicates the remaining "
        "section F screens on the wife holding a job.",
    ),
    run(
        49,
        38,
        1,
        7,
        F,
        "p49_flow_f2_otherwise_section_h",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    line(
        49,
        40,
        C,
        "p49_f3_employee_self",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
        note="F3 prints the wife employee/self-employed field.",
    ),
    line(
        49,
        40,
        P,
        "p49_f3_prompt",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    run(
        49,
        44,
        0,
        4,
        F,
        "p49_flow_f3_self_only",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    block(
        49,
        47,
        48,
        C,
        "p49_f4_government",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
        note="F4 prints the wife government-level field.",
    ),
    block(
        49,
        47,
        48,
        P,
        "p49_f4_prompt",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
    run(
        49,
        56,
        1,
        5,
        F,
        "p49_flow_f5_no_union",
        routes=(SECTION_F + ("p49_flow_f1_head_has_wife",),),
    ),
)

# Page 51 - section F wife occupation, industry, tenure items F7-F13.
PAGE_51 = (
    block(
        51,
        1,
        2,
        C,
        "p51_f7_occupation",
        routes=(SECTION_F,),
        parents=("p51_job_present_position",),
        parent_note=_JOB_WIFE_PRESENT,
        note="F7 prints the wife main-occupation field; the printed item "
        "identifier is scanned as y·1 and is retained verbatim.",
    ),
    block(51, 1, 2, P, "p51_f7_prompt", routes=(SECTION_F,)),
    run(51, 18, 5, 5, R, "p51_role_wife_f10", routes=(SECTION_F,)),
    line(
        51,
        8,
        C,
        "p51_f8_occupation_detail",
        routes=(SECTION_F,),
        parents=("p51_job_present_position",),
        parent_note=_JOB_WIFE_PRESENT,
    ),
    line(51, 8, P, "p51_f8_prompt", routes=(SECTION_F,)),
    line(
        51,
        13,
        C,
        "p51_f9_industry",
        routes=(SECTION_F,),
        parents=("p51_job_present_position",),
        parent_note=_JOB_WIFE_PRESENT,
    ),
    line(51, 13, P, "p51_f9_prompt", routes=(SECTION_F,)),
    word(
        51,
        18,
        "present position",
        J,
        "p51_job_present_position",
        routes=(SECTION_F,),
    ),
    line(
        51,
        18,
        C,
        "p51_f10_tenure",
        routes=(SECTION_F,),
        parents=("p51_job_present_position",),
        parent_note=_JOB_WIFE_PRESENT,
    ),
    line(51, 18, P, "p51_f10_prompt", routes=(SECTION_F,)),
    line(
        51,
        25,
        F,
        "p51_flow_f11_less_than_year",
        routes=(SECTION_F,),
        note="F11 interviewer checkpoint branch A: present position held "
        "less than one year.",
    ),
    block(
        51,
        27,
        28,
        F,
        "p51_flow_f11_year_or_more",
        routes=(SECTION_F,),
        note="F11 interviewer checkpoint branch B with its printed routing "
        "atom into F14.",
    ),
    line(
        51,
        33,
        C,
        "p51_f12_start_month",
        routes=(SECTION_F + ("p51_flow_f11_less_than_year",),),
        parents=("p51_job_present_position",),
        parent_note=_JOB_WIFE_PRESENT,
        note="F12 prints the start-month exposure field for the wife's "
        "present position.",
    ),
    line(
        51,
        33,
        P,
        "p51_f12_prompt",
        routes=(SECTION_F + ("p51_flow_f11_less_than_year",),),
    ),
)

# Page 53 - section F wife work-time exposure items F14-F23.
PAGE_53 = (
    block(
        53,
        1,
        2,
        C,
        "p53_f14_missed_family_sick",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    block(53, 1, 2, P, "p53_f14_prompt", routes=(SECTION_F,)),
    run(53, 14, 4, 4, R, "p53_role_wife_f16", routes=(SECTION_F,)),
    run(53, 8, 2, 5, F, "p53_flow_f14_no", routes=(SECTION_F,)),
    line(53, 9, C, "p53_f15_amount", routes=(SECTION_F,)),
    line(53, 9, P, "p53_f15_prompt", routes=(SECTION_F,)),
    line(53, 14, C, "p53_f16_missed_own_sick", routes=(SECTION_F,)),
    line(53, 14, P, "p53_f16_prompt", routes=(SECTION_F,)),
    line(53, 21, C, "p53_f17_amount", routes=(SECTION_F,)),
    line(53, 21, P, "p53_f17_prompt", routes=(SECTION_F,)),
    line(53, 27, C, "p53_f18_vacation", routes=(SECTION_F,)),
    line(53, 27, P, "p53_f18_prompt", routes=(SECTION_F,)),
    run(53, 31, 2, 5, F, "p53_flow_f18_no", routes=(SECTION_F,)),
    line(53, 32, C, "p53_f19_amount", routes=(SECTION_F,)),
    line(53, 32, P, "p53_f19_prompt", routes=(SECTION_F,)),
    block(53, 38, 39, C, "p53_f20_strike", routes=(SECTION_F,)),
    block(53, 38, 39, P, "p53_f20_prompt", routes=(SECTION_F,)),
    run(53, 41, 3, 6, F, "p53_flow_f20_no", routes=(SECTION_F,)),
    line(53, 47, C, "p53_f21_amount", routes=(SECTION_F,)),
    line(53, 47, P, "p53_f21_prompt", routes=(SECTION_F,)),
    block(53, 53, 54, C, "p53_f22_unemployed", routes=(SECTION_F,)),
    block(53, 53, 54, P, "p53_f22_prompt", routes=(SECTION_F,)),
    run(53, 56, 1, 4, F, "p53_flow_f22_no", routes=(SECTION_F,)),
    line(53, 61, C, "p53_f23_amount", routes=(SECTION_F,)),
    line(53, 61, P, "p53_f23_prompt", routes=(SECTION_F,)),
)

# Page 55 - section F wife weeks, hours, overtime, and wage-rate F24-F30.
PAGE_55 = (
    run(55, 7, 2, 3, J, "p55_job_main_job", routes=(SECTION_F,)),
    block(
        55,
        1,
        2,
        C,
        "p55_f24_weeks_worked",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
        note="Wife weeks-worked exposure field; the printed item identifier "
        "is scanned as F44 and is retained verbatim.",
    ),
    block(55, 1, 2, P, "p55_f24_prompt", routes=(SECTION_F,)),
    block(
        55,
        6,
        7,
        C,
        "p55_f25_hours_per_week",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
        note="Wife hours-per-week exposure field; the printed item "
        "identifier is scanned as F45 and is retained verbatim.",
    ),
    block(55, 6, 7, P, "p55_f25_prompt", routes=(SECTION_F,)),
    line(
        55,
        10,
        C,
        "p55_f26_overtime",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(55, 10, P, "p55_f26_prompt", routes=(SECTION_F,)),
    run(55, 16, 4, 7, F, "p55_flow_f26_no", routes=(SECTION_F,)),
    line(
        55,
        18,
        C,
        "p55_f27_overtime_hours",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(55, 18, P, "p55_f27_prompt", routes=(SECTION_F,)),
    line(
        55,
        22,
        C,
        "p55_f28_pay_form",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
        note="F28 prints the salaried/hourly pay-form field for the wife's "
        "main job.",
    ),
    line(55, 22, P, "p55_f28_prompt", routes=(SECTION_F,)),
    run(
        55,
        29,
        0,
        0,
        M,
        "p55_f29_salary",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
        note="F29 salary component; the printed pay-rate answer columns are "
        "photographed side by side, so this span is the exact contiguous "
        "printed run inside one column.",
    ),
    run(
        55,
        29,
        1,
        2,
        M,
        "p55_f30_hourly_wage_rate",
        routes=(SECTION_F,),
        parents=("p55_job_main_job",),
        parent_note=_JOB_WIFE_MAIN,
        note="F30 regular-work hourly wage-rate component; the printed "
        "pay-rate answer columns are photographed side by side, so this "
        "span is the exact contiguous printed run inside one column.",
    ),
)

# Page 57 - section F wife extra-job items F31-F37.
PAGE_57 = (
    run(57, 3, 6, 7, J, "p57_job_extra_jobs", routes=(SECTION_F,)),
    block(
        57,
        3,
        4,
        C,
        "p57_f31_extra_jobs",
        routes=(SECTION_F,),
        parents=("p57_job_extra_jobs",),
        parent_note=_JOB_WIFE_EXTRA,
        note="F31 prints the wife extra-job assignment field.",
    ),
    block(57, 3, 4, P, "p57_f31_prompt", routes=(SECTION_F,)),
    line(
        57,
        8,
        C,
        "p57_f32_extra_job_occupation",
        routes=(SECTION_F,),
        parents=("p57_job_extra_jobs",),
        parent_note=_JOB_WIFE_EXTRA,
    ),
    line(57, 8, P, "p57_f32_prompt", routes=(SECTION_F,)),
    block(
        57,
        12,
        13,
        C,
        "p57_f33_extra_job_weeks",
        routes=(SECTION_F,),
        parents=("p57_job_extra_jobs",),
        parent_note=_JOB_WIFE_EXTRA,
    ),
    block(57, 12, 13, P, "p57_f33_prompt", routes=(SECTION_F,)),
    block(
        57,
        16,
        17,
        C,
        "p57_f34_extra_job_hours",
        routes=(SECTION_F,),
        parents=("p57_job_extra_jobs",),
        parent_note=_JOB_WIFE_EXTRA,
    ),
    block(57, 16, 17, P, "p57_f34_prompt", routes=(SECTION_F,)),
    run(57, 23, 0, 3, F, "p57_flow_f35_none", routes=(SECTION_F,)),
    run(57, 47, 1, 9, F, "p57_flow_f37_turn_section_j", routes=(SECTION_F,)),
)

# Page 59 - section G entry, job-search, and last-job items G1-G9.
PAGE_59 = (
    line(
        59,
        1,
        F,
        "p59_flow_section_g",
        note="Printed section G header conditions the wife job-search "
        "schedule on the unemployed assignment recorded at F2.",
    ),
    run(59, 11, 7, 7, R, "p59_role_wife_g3", routes=(SECTION_G,)),
    word(59, 4, "job", J, "p59_job_sought", routes=(SECTION_G,)),
    line(
        59,
        4,
        C,
        "p59_g1_sought_occupation",
        routes=(SECTION_G,),
        parents=("p59_job_sought",),
        parent_note="Parent is the printed sought-job anchor named in the "
        "same question block.",
        note="G1 prints the wife sought-job occupation field.",
    ),
    line(59, 4, P, "p59_g1_prompt", routes=(SECTION_G,)),
    run(59, 8, 1, 4, F, "p59_flow_g2_no", routes=(SECTION_G,)),
    word(59, 22, "job", J, "p59_job_ever_had", routes=(SECTION_G,)),
    line(
        59,
        22,
        C,
        "p59_g5_ever_had_job",
        routes=(SECTION_G,),
        parents=("p59_job_ever_had",),
        parent_note=_JOB_WIFE_LAST,
        note="G5 prints the ever-held-a-job assignment field that "
        "predicates the section G last-job block.",
    ),
    line(59, 22, P, "p59_g5_prompt", routes=(SECTION_G,)),
    run(59, 24, 0, 4, F, "p59_flow_g5_no", routes=(SECTION_G,)),
    run(59, 28, 11, 12, J, "p59_job_last", routes=(SECTION_G,)),
    block(
        59,
        28,
        29,
        C,
        "p59_g6_last_job_occupation",
        routes=(SECTION_G,),
        parents=("p59_job_last",),
        parent_note=_JOB_WIFE_LAST,
    ),
    block(59, 28, 29, P, "p59_g6_prompt", routes=(SECTION_G,)),
    line(
        59,
        39,
        C,
        "p59_g7_last_job_industry",
        routes=(SECTION_G,),
        parents=("p59_job_last",),
        parent_note=_JOB_WIFE_LAST,
    ),
    line(59, 39, P, "p59_g7_prompt", routes=(SECTION_G,)),
    line(
        59,
        50,
        C,
        "p59_g9_last_worked",
        routes=(SECTION_G,),
        parents=("p59_job_last",),
        parent_note=_JOB_WIFE_LAST,
    ),
    line(59, 50, P, "p59_g9_prompt", routes=(SECTION_G,)),
)

# Page 61 - section G wife work-time exposure items G10-G18.
PAGE_61 = (
    line(
        61,
        3,
        F,
        "p61_flow_g10_worked",
        routes=(SECTION_G,),
        note="G10 interviewer checkpoint branch A: wife worked in 1978 or "
        "1979.",
    ),
    run(61, 3, 1, 1, R, "p61_role_wife_g10", routes=(SECTION_G,)),
    run(
        61,
        5,
        0,
        8,
        F,
        "p61_flow_g10_did_not_work",
        routes=(SECTION_G,),
        note="G10 interviewer checkpoint branch B; the scan fuses the "
        "printed year with the routing verb, so the branch condition and "
        "its routing atom are spanned as the two printed runs that survive.",
    ),
    run(
        61,
        5,
        9,
        14,
        F,
        "p61_flow_g10_turn_section_j",
        routes=(SECTION_G,),
    ),
    line(
        61,
        10,
        C,
        "p61_g11_vacation",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        10,
        P,
        "p61_g11_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    run(
        61,
        12,
        2,
        5,
        F,
        "p61_flow_g11_no",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        15,
        C,
        "p61_g12_amount",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        15,
        P,
        "p61_g12_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    block(
        61,
        21,
        22,
        C,
        "p61_g13_missed_family_sick",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    block(
        61,
        21,
        22,
        P,
        "p61_g13_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    run(
        61,
        24,
        0,
        2,
        F,
        "p61_flow_g13_no",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        28,
        C,
        "p61_g14_amount",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        28,
        P,
        "p61_g14_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        34,
        C,
        "p61_g15_missed_own_sick",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        34,
        P,
        "p61_g15_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    run(
        61,
        36,
        2,
        5,
        F,
        "p61_flow_g15_no",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        37,
        C,
        "p61_g16_amount",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        37,
        P,
        "p61_g16_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        43,
        C,
        "p61_g17_strike",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        43,
        P,
        "p61_g17_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    run(
        61,
        45,
        0,
        4,
        F,
        "p61_flow_g17_no",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        48,
        C,
        "p61_g18_amount",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
    line(
        61,
        48,
        P,
        "p61_g18_prompt",
        routes=(SECTION_G + ("p61_flow_g10_worked",),),
    ),
)

# Page 63 - section G wife unemployment exposure, weeks, and hours G19-G25.
PAGE_63 = (
    block(63, 1, 2, C, "p63_g19_unemployed", routes=(SECTION_G,)),
    block(63, 1, 2, P, "p63_g19_prompt", routes=(SECTION_G,)),
    line(63, 9, C, "p63_g20_amount", routes=(SECTION_G,)),
    line(63, 9, P, "p63_g20_prompt", routes=(SECTION_G,)),
    run(63, 10, 2, 5, F, "p63_flow_g20_no", routes=(SECTION_G,)),
    run(63, 18, 11, 11, J, "p63_job_1978", routes=(SECTION_G,)),
    line(
        63,
        18,
        C,
        "p63_g21_weeks_worked",
        routes=(SECTION_G,),
        parents=("p63_job_1978",),
        parent_note=_JOB_WIFE_MAIN,
        note="Wife weeks-worked exposure field; the printed item identifier "
        "is scanned as G4l and is retained verbatim.",
    ),
    line(63, 18, P, "p63_g21_prompt", routes=(SECTION_G,)),
    line(
        63,
        22,
        C,
        "p63_g22_hours_per_week",
        routes=(SECTION_G,),
        parents=("p63_job_1978",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(63, 22, P, "p63_g22_prompt", routes=(SECTION_G,)),
    run(63, 29, 5, 12, F, "p63_flow_g23_none", routes=(SECTION_G,)),
    run(63, 51, 0, 6, F, "p63_flow_g25_turn_section_j", routes=(SECTION_G,)),
)

# Page 65 - section H entry, retirement, and money-work items H1-H9.
PAGE_65 = (
    block(
        65,
        1,
        2,
        F,
        "p65_flow_section_h",
        note="Printed section H header conditions the wife "
        "not-in-labour-force schedule on the assignment recorded at F2.",
    ),
    run(65, 7, 1, 1, R, "p65_role_wife_h1", routes=(SECTION_H,)),
    line(
        65,
        7,
        F,
        "p65_flow_h1_retired",
        routes=(SECTION_H,),
        note="H1 interviewer checkpoint branch 1: wife is retired.",
    ),
    block(
        65,
        9,
        10,
        F,
        "p65_flow_h1_other",
        routes=(SECTION_H,),
        note="H1 interviewer checkpoint branch 5 with its printed routing "
        "atom into H3.",
    ),
    line(
        65,
        15,
        C,
        "p65_h2_retirement_year",
        routes=(SECTION_H + ("p65_flow_h1_retired",),),
        note="H2 prints the wife retirement-year exposure field.",
    ),
    line(
        65,
        15,
        P,
        "p65_h2_prompt",
        routes=(SECTION_H + ("p65_flow_h1_retired",),),
    ),
    run(65, 20, 7, 10, J, "p65_job_money_work", routes=(SECTION_H,)),
    line(
        65,
        20,
        C,
        "p65_h3_money_work",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
        note="H3 prints the wife 1978 money-work assignment field.",
    ),
    line(65, 20, P, "p65_h3_prompt", routes=(SECTION_H,)),
    run(65, 24, 0, 5, F, "p65_flow_h3_no", routes=(SECTION_H,)),
    line(
        65,
        26,
        C,
        "p65_h4_occupation",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
    ),
    line(65, 26, P, "p65_h4_prompt", routes=(SECTION_H,)),
    line(
        65,
        31,
        C,
        "p65_h5_industry",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
    ),
    line(65, 31, P, "p65_h5_prompt", routes=(SECTION_H,)),
    line(
        65,
        36,
        C,
        "p65_h6_weeks_worked",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
    ),
    line(65, 36, P, "p65_h6_prompt", routes=(SECTION_H,)),
    line(
        65,
        40,
        C,
        "p65_h7_hours_per_week",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
    ),
    line(65, 40, P, "p65_h7_prompt", routes=(SECTION_H,)),
    line(
        65,
        46,
        C,
        "p65_h8_still_working",
        routes=(SECTION_H,),
        parents=("p65_job_money_work",),
        parent_note=_JOB_WIFE_MONEY,
    ),
    line(65, 46, P, "p65_h8_prompt", routes=(SECTION_H,)),
    run(65, 50, 0, 5, F, "p65_flow_h8_yes", routes=(SECTION_H,)),
)


SECTION_K = ("p83_flow_section_k",)
SECTION_K_R = ("p85_flow_section_k_reprint",)
SECTION_L = ("p111_flow_section_l",)
SECTION_M = ("p113_flow_section_m",)
_FARM_PARENT = (
    "Parent is the printed farm operation established by the K1 farmer "
    "checkpoint on the same screen."
)
_BUSINESS_PARENT = (
    "Parent is the printed business enterprise established at K5 on the "
    "same screen."
)
_EXTRA_EARNER_JOB = (
    "Parent is the printed extra-earner job anchor established at K37 on "
    "the same screen."
)

# Page 83 - section K entry, farm, business, and wage-and-salary K1-K8.
PAGE_83 = (
    line(
        83,
        1,
        F,
        "p83_flow_section_k",
        note="Printed section K header opens the income schedule.",
    ),
    line(
        83,
        10,
        F,
        "p83_flow_k1_farmer",
        routes=(SECTION_K,),
        note="K1 interviewer checkpoint branch 1: head is a farmer or "
        "rancher.",
    ),
    word(83, 10, "HEAD", R, "p83_role_head_k1", routes=(SECTION_K,)),
    run(83, 12, 0, 6, F, "p83_flow_k1_not_farmer", routes=(SECTION_K,)),
    run(83, 12, 7, 9, F, "p83_flow_k1_go_to_k5", routes=(SECTION_K,)),
    block(
        83,
        17,
        18,
        M,
        "p83_k2_farm_receipts",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
        parents=("p83_farm_aggregate",),
        parent_note=_FARM_PARENT,
        note="K2 prints the total farm receipts component.",
    ),
    block(
        83,
        17,
        18,
        P,
        "p83_k2_prompt",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
    ),
    block(
        83,
        19,
        20,
        M,
        "p83_k3_farm_expenses",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
        parents=("p83_farm_aggregate",),
        parent_note=_FARM_PARENT,
        note="K3 prints the farm operating-expense component.",
    ),
    block(
        83,
        19,
        20,
        P,
        "p83_k3_prompt",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
    ),
    run(
        83,
        22,
        5,
        8,
        FA,
        "p83_farm_aggregate",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
        note="K4 prints the net farm income aggregate.",
    ),
    line(
        83,
        22,
        P,
        "p83_k4_prompt",
        routes=(SECTION_K + ("p83_flow_k1_farmer",),),
    ),
    block(
        83,
        25,
        26,
        C,
        "p83_k5_business_interest",
        routes=(SECTION_K,),
        parents=("p83_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="K5 prints the business-ownership assignment field.",
    ),
    block(83, 25, 26, P, "p83_k5_prompt", routes=(SECTION_K,)),
    run(83, 29, 0, 5, F, "p83_flow_k5_no", routes=(SECTION_K,)),
    run(
        83,
        31,
        7,
        8,
        BA,
        "p83_business_aggregate",
        routes=(SECTION_K,),
        note="K6 prints the unincorporated-business aggregate.",
    ),
    block(
        83,
        31,
        32,
        C,
        "p83_k6_incorporation",
        routes=(SECTION_K,),
        parents=("p83_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="K6 prints the incorporation field.",
    ),
    block(83, 31, 32, P, "p83_k6_prompt", routes=(SECTION_K,)),
    run(83, 36, 0, 2, F, "p83_flow_k6_go_to_k8", routes=(SECTION_K,)),
    block(
        83,
        38,
        39,
        M,
        "p83_k7_business_share",
        routes=(SECTION_K,),
        parents=("p83_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="K7 prints the family share of total business income.",
    ),
    block(83, 38, 39, P, "p83_k7_prompt", routes=(SECTION_K,)),
    block(
        83,
        44,
        45,
        T,
        "p83_k8_role_total",
        routes=(SECTION_K,),
        note="K8 prints the head's 1978 wage-and-salary role total.",
    ),
    block(83, 44, 45, P, "p83_k8_prompt", routes=(SECTION_K,)),
)

# Page 85 - the reprinted section K farm/business/wage screen K1-K8.
PAGE_85 = (
    line(
        85,
        1,
        F,
        "p85_flow_section_k_reprint",
        note="Reprinted section K header at distinct printed coordinates; "
        "the reprinted screen resolves under it.",
    ),
    line(
        85,
        10,
        F,
        "p85_flow_k1_farmer",
        routes=(SECTION_K_R,),
    ),
    word(85, 10, "HEAD", R, "p85_role_head_k1", routes=(SECTION_K_R,)),
    run(85, 12, 0, 7, F, "p85_flow_k1_not_farmer", routes=(SECTION_K_R,)),
    run(85, 12, 8, 10, F, "p85_flow_k1_go_to_k5", routes=(SECTION_K_R,)),
    block(
        85,
        16,
        17,
        M,
        "p85_k2_farm_receipts",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
        parents=("p85_farm_aggregate",),
        parent_note=_FARM_PARENT,
        note="Reprinted total farm receipts component; the printed item "
        "identifier is scanned as K4 and is retained verbatim.",
    ),
    block(
        85,
        16,
        17,
        P,
        "p85_k2_prompt",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
    ),
    block(
        85,
        19,
        20,
        M,
        "p85_k3_farm_expenses",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
        parents=("p85_farm_aggregate",),
        parent_note=_FARM_PARENT,
    ),
    block(
        85,
        19,
        20,
        P,
        "p85_k3_prompt",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
    ),
    run(
        85,
        26,
        5,
        8,
        FA,
        "p85_farm_aggregate",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
    ),
    line(
        85,
        26,
        P,
        "p85_k4_prompt",
        routes=(SECTION_K_R + ("p85_flow_k1_farmer",),),
    ),
    block(
        85,
        30,
        31,
        C,
        "p85_k5_business_interest",
        routes=(SECTION_K_R,),
        parents=("p85_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
    ),
    block(85, 30, 31, P, "p85_k5_prompt", routes=(SECTION_K_R,)),
    run(
        85,
        36,
        8,
        9,
        BA,
        "p85_business_aggregate",
        routes=(SECTION_K_R,),
    ),
    block(
        85,
        36,
        37,
        C,
        "p85_k6_incorporation",
        routes=(SECTION_K_R,),
        parents=("p85_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
    ),
    block(85, 36, 37, P, "p85_k6_prompt", routes=(SECTION_K_R,)),
    run(85, 41, 0, 2, F, "p85_flow_k6_go_to_k8", routes=(SECTION_K_R,)),
    block(
        85,
        43,
        44,
        M,
        "p85_k7_business_share",
        routes=(SECTION_K_R,),
        parents=("p85_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
    ),
    block(85, 43, 44, P, "p85_k7_prompt", routes=(SECTION_K_R,)),
    block(
        85,
        50,
        51,
        T,
        "p85_k8_role_total",
        routes=(SECTION_K_R,),
        note="Reprinted head 1978 wage-and-salary role total.",
    ),
    block(85, 50, 51, P, "p85_k8_prompt", routes=(SECTION_K_R,)),
)

# Page 87 - section K supplementary earnings and other-source list K9-K13.
PAGE_87 = (
    block(
        87,
        1,
        2,
        M,
        "p87_k9_bonuses_overtime_commissions",
        routes=(SECTION_K_R,),
        note="K9 prints the bonuses/overtime/commissions component in "
        "addition to the K8 wage-and-salary total.",
    ),
    block(87, 1, 2, P, "p87_k9_prompt", routes=(SECTION_K_R,)),
    run(87, 8, 1, 3, F, "p87_flow_k9_no", routes=(SECTION_K_R,)),
    line(87, 7, C, "p87_k10_amount", routes=(SECTION_K_R,)),
    line(87, 7, P, "p87_k10_prompt", routes=(SECTION_K_R,)),
    run(
        87,
        16,
        10,
        11,
        M,
        "p87_k11a_professional_practice",
        routes=(SECTION_K_R,),
        note="K11 item a prints the professional-practice-or-trade "
        "component; the printed item continues on the following line.",
    ),
    block(87, 15, 17, P, "p87_k11_prompt", routes=(SECTION_K_R,)),
    run(
        87,
        17,
        2,
        9,
        A,
        "p87_k11_repeat_instruction",
        routes=(SECTION_K_R,),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed interviewer instruction to repeat K12 for each YES "
        "answer in the K11 item list.",
    ),
    run(
        87,
        32,
        1,
        4,
        M,
        "p87_k11b_farming_or_market_gardening",
        routes=(SECTION_K_R,),
        note="K11 item b prints the farming-or-market-gardening component.",
    ),
    run(
        87,
        36,
        1,
        3,
        M,
        "p87_k11c_roomers_or_boarders",
        routes=(SECTION_K_R,),
        note="K11 item c prints the roomers-or-boarders component.",
    ),
)

# Page 89 - the reprinted section K supplementary earnings screen K9-K13.
PAGE_89 = (
    block(
        89,
        2,
        3,
        M,
        "p89_k9_bonuses_overtime_commissions",
        routes=(SECTION_K_R,),
    ),
    block(89, 2, 3, P, "p89_k9_prompt", routes=(SECTION_K_R,)),
    run(89, 9, 1, 3, F, "p89_flow_k9_no", routes=(SECTION_K_R,)),
    line(89, 8, C, "p89_k10_amount", routes=(SECTION_K_R,)),
    line(89, 8, P, "p89_k10_prompt", routes=(SECTION_K_R,)),
    run(
        89,
        17,
        10,
        11,
        M,
        "p89_k11a_professional_practice",
        routes=(SECTION_K_R,),
    ),
    block(89, 16, 18, P, "p89_k11_prompt", routes=(SECTION_K_R,)),
    run(
        89,
        18,
        2,
        8,
        A,
        "p89_k11_repeat_instruction",
        routes=(SECTION_K_R,),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Reprinted interviewer instruction to repeat K12 for each YES "
        "answer in the K11 item list.",
    ),
    run(
        89,
        32,
        1,
        4,
        M,
        "p89_k11b_farming_or_market_gardening",
        routes=(SECTION_K_R,),
    ),
    run(
        89,
        35,
        1,
        3,
        M,
        "p89_k11c_roomers_or_boarders",
        routes=(SECTION_K_R,),
    ),
)

# Page 97 - the section K extra-earner listing and eligibility checkpoint.
PAGE_97 = (
    run(
        97,
        22,
        0,
        1,
        C,
        "p97_k34_extra_earner_unit",
        routes=(SECTION_K_R,),
        note="K34 prints the extra-earner reporting-unit column heading for "
        "the household listing grid.",
    ),
    run(
        97,
        34,
        0,
        4,
        F,
        "p97_flow_k35_eligible",
        routes=(SECTION_K_R,),
        note="K35 interviewer checkpoint branch: eligible persons listed.",
    ),
    block(
        97,
        34,
        35,
        A,
        "p97_k35_repeat_instruction",
        routes=(SECTION_K_R + ("p97_flow_k35_eligible",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed instruction to administer the K36-K50 extra-earner "
        "section once for each person listed in the K34 grid.",
    ),
    run(97, 37, 0, 6, F, "p97_flow_k35_none_eligible", routes=(SECTION_K_R,)),
)

# Page 99 - the first extra-earner assignment, work, and earnings K36-K44.
PAGE_99 = (
    run(
        99,
        6,
        0,
        2,
        C,
        "p99_extra_earner_unit",
        routes=(SECTION_K_R,),
        note="Printed first-extra-earner reporting-unit heading.",
    ),
    block(
        99,
        10,
        12,
        C,
        "p99_k36_assignment",
        routes=(SECTION_K_R,),
        note="K36 prints the extra-earner labour-force assignment field.",
    ),
    block(99, 10, 12, P, "p99_k36_prompt", routes=(SECTION_K_R,)),
    run(99, 26, 11, 11, J, "p99_job_extra_earner", routes=(SECTION_K_R,)),
    block(
        99,
        26,
        27,
        C,
        "p99_k37_full_or_part_time",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
        note="K37 prints the extra-earner full-time/part-time job field.",
    ),
    block(99, 26, 27, P, "p99_k37_prompt", routes=(SECTION_K_R,)),
    line(
        99,
        39,
        C,
        "p99_k38_weeks_worked",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
    ),
    line(99, 39, P, "p99_k38_prompt", routes=(SECTION_K_R,)),
    block(
        99,
        43,
        44,
        C,
        "p99_k39_hours_per_week",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
    ),
    block(99, 43, 44, P, "p99_k39_prompt", routes=(SECTION_K_R,)),
    line(
        99,
        49,
        C,
        "p99_k40_occupation",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
    ),
    line(99, 49, P, "p99_k40_prompt", routes=(SECTION_K_R,)),
    line(
        99,
        54,
        M,
        "p99_k41_earnings_from_work",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
        note="K41 prints the extra-earner earnings-from-work component.",
    ),
    line(99, 54, P, "p99_k41_prompt", routes=(SECTION_K_R,)),
    run(99, 60, 2, 8, F, "p99_flow_k42_no", routes=(SECTION_K_R,)),
)

# Page 101 - the first extra-earner unemployment and repeat checkpoint.
PAGE_101 = (
    block(
        101,
        1,
        2,
        C,
        "p101_k45_laid_off_or_looking",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
        note="K45 prints a 1978 unemployment exposure field for the extra "
        "earner; the printed item identifier is scanned as K1G and is "
        "retained verbatim.",
    ),
    block(101, 1, 2, P, "p101_k45_prompt", routes=(SECTION_K_R,)),
    run(101, 13, 0, 2, F, "p101_flow_k45_no", routes=(SECTION_K_R,)),
    line(
        101,
        15,
        C,
        "p101_k46_weeks",
        routes=(SECTION_K_R,),
        parents=("p99_job_extra_earner",),
        parent_note=_EXTRA_EARNER_JOB,
    ),
    line(101, 15, P, "p101_k46_prompt", routes=(SECTION_K_R,)),
    block(
        101,
        34,
        35,
        A,
        "p101_k50_repeat_instruction",
        routes=(SECTION_K_R,),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="K50 printed instruction routing to a second extra-earner "
        "section when more than one extra earner is listed at K34.",
    ),
    run(101, 37, 0, 11, F, "p101_flow_k50_only_one", routes=(SECTION_K_R,)),
)

# Page 111 - section L new-wife lifetime work-history items L10-L12.
PAGE_111 = (
    line(
        111,
        2,
        F,
        "p111_flow_section_l",
        note="Printed section L header conditions the new-wife schedule.",
    ),
    run(111, 2, 2, 3, R, "p111_role_new_wife_header", routes=(SECTION_L,)),
    block(
        111,
        7,
        8,
        F,
        "p111_flow_l1_new_wife",
        routes=(SECTION_L,),
        note="L1 interviewer checkpoint branch 1: head has a new wife this "
        "year.",
    ),
    run(111, 9, 5, 10, F, "p111_flow_l1_female_head", routes=(SECTION_L,)),
    run(111, 13, 8, 14, F, "p111_flow_l1_no_wife", routes=(SECTION_L,)),
    run(111, 16, 11, 15, F, "p111_flow_l1_same_wife", routes=(SECTION_L,)),
    block(
        111,
        47,
        48,
        C,
        "p111_l10_lifetime_work_years",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
        note="L10 prints the wife's lifetime years-worked-for-money "
        "exposure field.",
    ),
    block(
        111,
        47,
        48,
        P,
        "p111_l10_prompt",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
    ),
    line(
        111,
        52,
        F,
        "p111_flow_l10_none",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
    ),
    line(
        111,
        54,
        C,
        "p111_l11_full_time_years",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
        note="L11 prints the wife's full-time years exposure field.",
    ),
    line(
        111,
        54,
        P,
        "p111_l11_prompt",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
    ),
    line(
        111,
        56,
        F,
        "p111_flow_l11_turn_section_m",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
    ),
    block(
        111,
        60,
        61,
        C,
        "p111_l12_part_time_share",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
        note="L12 prints the wife's part-time work-share exposure field.",
    ),
    block(
        111,
        60,
        61,
        P,
        "p111_l12_prompt",
        routes=(SECTION_L + ("p111_flow_l1_new_wife",),),
    ),
)

# Page 113 - section M new-head first-job items M1-M5.
PAGE_113 = (
    line(
        113,
        2,
        F,
        "p113_flow_section_m",
        note="Printed section M header conditions the new-head schedule; "
        "the printed section letter is scanned as H and is retained "
        "verbatim.",
    ),
    run(113, 2, 2, 3, R, "p113_role_new_head_header", routes=(SECTION_M,)),
    line(
        113,
        7,
        F,
        "p113_flow_m1_new_head",
        routes=(SECTION_M,),
        note="M1 interviewer checkpoint branch 1: head is new this year.",
    ),
    run(113, 31, 5, 8, J, "p113_job_first_full_time", routes=(SECTION_M,)),
    line(
        113,
        31,
        C,
        "p113_m4_first_job_occupation",
        routes=(SECTION_M + ("p113_flow_m1_new_head",),),
        parents=("p113_job_first_full_time",),
        parent_note="Parent is the printed first full-time regular job "
        "anchor named in the same question block.",
        note="M4 prints the occupation of the head's first full-time "
        "regular job.",
    ),
    line(
        113,
        31,
        P,
        "p113_m4_prompt",
        routes=(SECTION_M + ("p113_flow_m1_new_head",),),
    ),
    run(
        113,
        34,
        0,
        4,
        F,
        "p113_flow_m4_never_worked",
        routes=(SECTION_M + ("p113_flow_m1_new_head",),),
    ),
)

# Page 117 - section M new-head lifetime work-history items M25-M27.
PAGE_117 = (
    line(
        117,
        36,
        C,
        "p117_m25_lifetime_work_years",
        routes=(SECTION_M,),
        note="M25 prints the head's lifetime years-worked exposure field.",
    ),
    line(117, 36, P, "p117_m25_prompt", routes=(SECTION_M,)),
    run(117, 39, 1, 9, F, "p117_flow_m25_none", routes=(SECTION_M,)),
    line(
        117,
        42,
        C,
        "p117_m26_full_time_years",
        routes=(SECTION_M,),
        note="M26 prints the head's full-time years exposure field.",
    ),
    line(117, 42, P, "p117_m26_prompt", routes=(SECTION_M,)),
    run(117, 44, 1, 5, F, "p117_flow_m26_turn_m28", routes=(SECTION_M,)),
    block(
        117,
        47,
        48,
        C,
        "p117_m27_part_time_share",
        routes=(SECTION_M,),
        note="M27 prints the head's part-time work-share exposure field.",
    ),
    block(117, 47, 48, P, "p117_m27_prompt", routes=(SECTION_M,)),
)


REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_17,
    *PAGE_19,
    *PAGE_21,
    *PAGE_23,
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
    *PAGE_49,
    *PAGE_51,
    *PAGE_53,
    *PAGE_55,
    *PAGE_57,
    *PAGE_59,
    *PAGE_61,
    *PAGE_63,
    *PAGE_65,
    *PAGE_83,
    *PAGE_85,
    *PAGE_87,
    *PAGE_89,
    *PAGE_97,
    *PAGE_99,
    *PAGE_101,
    *PAGE_111,
    *PAGE_113,
    *PAGE_117,
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
                "all_122_pages_including_empty_occurrence_pages"
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
        f"document 23 source review: {len(review['occurrence_specs'])} "
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
