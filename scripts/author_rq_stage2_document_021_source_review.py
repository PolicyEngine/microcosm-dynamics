#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 21.

``fam1978_QxQs.pdf`` is a 95-page scan of the 1978 family instrument bound
together with its question-by-question interviewer objectives.  Page 1 is a
scanned collection divider, pages 2 and 3 open the interview, and from page 4
onwards every even page is a printed instrument screen and every odd page is
its facing objectives sheet.  Pages 15, 63 and 71 extract to zero bytes.  All
95 pages were read from the authenticated Poppler text before this file was
written, and the stage-1 candidate artifact is never opened here; the sealed
annotation builder joins candidates only after these reviewer rows exist.

Reviewer scope decisions recorded by this file:

* Occurrences are emitted only on printed *instrument* screens inside the
  retained employment, work-income, and lifetime-work-history regions.  The
  question-by-question objective pages are interviewer commentary keyed to a
  question; they restate worklike vocabulary and cross-refer between printed
  items ("E27.  See D2, D3; the same objectives apply here."), but they print
  no field, so they carry no source occurrence.  The sealed fam1976 sibling
  made one departure here because that manual prints its wives employment
  screens nowhere at all; fam1978 prints its own section G wife screens on
  pages 46-52, so the departure's motivating condition is absent and the
  fam1979/fam1980 rule is applied unchanged.
* Cover, children, transportation, housing, residential-mobility, housework,
  food and food-stamp, welfare, medical, disability, dependent-support, new-
  wife and new-head schooling, growing-up, and by-observation regions
  contribute no occurrence merely because nearby prose contains worklike
  words.
* A retained ``context_anchor`` must print a field that maps to a ratified
  section-19 field purpose (assignment, occupation, industry, employee/self,
  government level, incorporation, job identifier, reporting unit, or
  month/exposure).  Labour-union contract and membership, commuting, counter-
  factual labour supply, job-search effort and job-search help, training
  requirement, job-competition and gender-competition, residential-mobility
  willingness, health limitation, prospective retirement and job intention,
  transfer and public-assistance receipt, residual other-income, and
  schooling fields are printed work-adjacent questions that map to no such
  purpose and are rejected.
* A retained ``job_anchor`` establishes a distinct printed job for the role.
  A later back-reference to a job already established ("this job" at D19,
  "that job" at F21) is rejected rather than promoted to a second job or an
  inferred alias, and a printed job that parents no retained field ("the job
  you had before" at D20-D23) is rejected rather than emitted as an orphan.
* A screen is retained if and only if it prints at least one retained field.
  On a retained screen every legible printed routing directive and printed
  conditional label is also retained; on a screen that prints no retained
  field nothing is retained, including its routing directives.  Page 76 is
  the one screen where that costs something: it prints ``(TURN BACK AND ASK
  PAGE 32-33 FOR THESE ADDITIONAL HEMBERS)`` over the retained extra-earner
  grid, but every field it prints is a residual-income, welfare, or job-
  search field.  The instruction is not retained because the same repeat
  relation is already carried by the ``(GO TO H34 FOR NEXT PERSON LISTED)``
  directives printed on the retained pages 72 and 74.
* A printed universal-administration note (``(ASK EVERYONE)``, ``(ASK
  EVERYOHE)``) resolves no condition and opens no branch, so it is not a
  branch label.  A printed interviewer-checkpoint *instruction* line is a
  branch label only where the scan destroyed its answer boxes and the
  instruction itself carries the complete printed condition, which happens
  once, at H23 on page 68.
* A role anchor is retained once per screen per role that the screen's
  retained fields concern, at the earliest printed lexeme for that role whose
  bytes survive the scan intact.  Several screens that plainly concern the
  head or the wife therefore carry no role anchor, because the instrument
  addresses the respondent as "you" and prints no role lexeme at all.  The
  extra-earner grid on pages 72 and 74 prints ``HEAD`` only as the listing
  reference point for people who are neither section-19 role, so it carries
  no role anchor.
* An occurrence's applicable path set is the ancestry of the printed block in
  which it is administered: the section-header branch, extended by each
  printed conditional label (interviewer checkpoint or printed condition)
  that encloses it.  The section-header branch is the most recent *preceding*
  printed header for that section.  A printed forward routing atom is itself
  a branch label, but it does not re-parent the screen it jumps to, because
  that screen is administered identically on fall-through.
* This is an early scan and its OCR is lossy.  Destroyed printed bytes are
  never reconstructed.  A routing atom is retained only where the printed
  bytes still separate its directive verb from its target; the D60 checkpoint
  stem on page 26 and the J1 checkpoint labels on page 84 are retained only
  in the fragments that survive, and the D1 fall-through directive on page 12
  is spanned as the printed block that carries both its verb and its target.
* The 1978 pay-rate screen (page 22), the D5-D11 employer screen (page 16),
  and the extra-earner grids (pages 72 and 74) photograph two or three answer
  columns side by side.  No emitted span crosses a printed column gutter; an
  anchor on those screens is the exact contiguous printed run inside one
  column.
* Printed page 32 (document page 72) and printed page 33 (document page 74)
  print the same extra-earner grid twice, the second time for three further
  persons; page 75's objectives sheet calls it "a repetition of the previous
  one".  Each printing is a distinct printed occurrence at distinct
  coordinates and is annotated separately.  No local alias binds the second
  printing to the first, and the repeat instructions are handed off with
  ``target_scope: unresolved``; that equivalence is left entirely to global
  assembly.
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
import build_rq_stage2_document_021_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 95


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

    The 1978 instrument prints several question stems on a line that also
    carries a coder box or an unrelated answer token, so a whole-line span
    would swallow it.  This selector keeps the exact printed bytes from a
    named needle to the end of its physical line.
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

    The 1978 manual is an early scan whose answer columns are photographed
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
_EMPTY = (
    "Page emitted by the pinned Poppler derivation with zero text bytes; the "
    "scanned leaf carries no extractable printed unit, and its empty "
    "occurrence array is a reviewed result rather than an unreviewed page."
)
PAGE_NOTES: dict[int, str] = {
    1: _INSTRUMENT_OUT.format(
        "the scanned collection-instructions divider, whose four extracted "
        "lines are scan artefacts of a printed tab label"
    ),
    2: _INSTRUMENT_OUT.format(
        "the interviewer face sheet, office-use box, and section A children "
        "and schooling items A1-A4"
    ),
    3: _OBJECTIVES.format(
        "the section III identifying-information reminder and section A "
        "items A2-A4"
    ),
    4: _INSTRUMENT_OUT.format("section B transportation items B1-B5"),
    5: _OBJECTIVES.format("section B items B1-B5"),
    6: _INSTRUMENT_OUT.format(
        "section C housing, utility, and mortgage items C1-C10"
    ),
    7: _OBJECTIVES.format("section C items C1-C10"),
    8: _INSTRUMENT_OUT.format("section C rent and utility items C11-C19"),
    9: _OBJECTIVES.format("section C items C11-C19"),
    10: _INSTRUMENT_OUT.format("section C residential-mobility items C20-C25"),
    11: _OBJECTIVES.format("section C items C20-C25"),
    12: _INSTRUMENT_IN.format(
        "section D entry and head employment, occupation, and industry items "
        "D1-D4"
    ),
    13: _OBJECTIVES.format(
        "section D item D1, the D/E/F section-selection definitions, and "
        "items D2-D3"
    ),
    14: _OBJECTIVES.format(
        "the unacceptable-occupation-answer list and section D item D4"
    ),
    15: _EMPTY,
    16: _INSTRUMENT_IN.format(
        "section D head employer, government-level, union, and job-"
        "requirement items D5-D17"
    ),
    17: _OBJECTIVES.format("section D items D5-D11 and D15-D17"),
    18: _INSTRUMENT_IN.format(
        "section D head tenure, previous-job, and work-time exposure items "
        "D18-D29"
    ),
    19: _OBJECTIVES.format("section D items D18-D29"),
    20: _INSTRUMENT_IN.format(
        "section D head strike, unemployment, weeks, hours, and overtime "
        "exposure items D30-D37"
    ),
    21: _OBJECTIVES.format("section D items D32-D37"),
    22: _INSTRUMENT_IN.format(
        "section D head pay-form, wage-rate, and extra-job items D38-D51"
    ),
    23: _OBJECTIVES.format("section D items D40-D51"),
    24: _INSTRUMENT_NONE.format(
        "section D head work-availability and commuting items D52-D59",
        "a counterfactual labour-supply or commuting field that maps to no "
        "ratified section-19 field purpose",
    ),
    25: _OBJECTIVES.format("section D items D52-D59"),
    26: _INSTRUMENT_IN.format(
        "the section D head age checkpoint and first-job history items "
        "D60-D71"
    ),
    27: _OBJECTIVES.format("section D items D61 and D67"),
    28: _INSTRUMENT_IN.format(
        "section D head present-employer tenure and hiring-help items "
        "D72-D82"
    ),
    29: _OBJECTIVES.format("section D item D78"),
    30: _INSTRUMENT_NONE.format(
        "section D head retirement-expectation items D83-D89",
        "a prospective retirement-age, prospective benefit-eligibility, or "
        "expected-adequacy field that maps to no ratified section-19 field "
        "purpose",
    ),
    31: _OBJECTIVES.format("section D items D83-D86"),
    32: _INSTRUMENT_IN.format(
        "section E entry and head sought-job items E1-E13"
    ),
    33: _OBJECTIVES.format("section E items E1-E5"),
    34: _INSTRUMENT_IN.format(
        "the section E ever-had-a-job item, age checkpoint, and first-job "
        "history items E14-E26"
    ),
    35: _OBJECTIVES.format("section E item E22"),
    36: _INSTRUMENT_IN.format(
        "section E head last-job occupation, industry, and 1977 exposure "
        "items E27-E38"
    ),
    37: _OBJECTIVES.format("section E items E27-E36"),
    38: _INSTRUMENT_IN.format(
        "section E head unemployment exposure, weeks, hours, and commuting "
        "items E39-E45"
    ),
    39: _OBJECTIVES.format("section E items E39-E45"),
    40: _INSTRUMENT_IN.format(
        "section F entry, the retirement checkpoint, and head post-"
        "retirement money-work items F1-F9"
    ),
    41: _OBJECTIVES.format("section F items F2-F8"),
    42: _INSTRUMENT_IN.format(
        "section F head 1977 money-work occupation, industry, weeks, and "
        "hours items F10-F21"
    ),
    43: _OBJECTIVES.format("section F items F10-F21"),
    44: _INSTRUMENT_NONE.format(
        "section F head future-job items F22-F31",
        "a prospective job-intention, training-requirement, job-search, or "
        "reservation-wage field that maps to no ratified section-19 field "
        "purpose",
    ),
    45: _OBJECTIVES.format("section F items F22 and F31"),
    46: _INSTRUMENT_IN.format(
        "section G entry, the marital checkpoint, and wife money-work, "
        "occupation, and industry items G1-G7"
    ),
    47: _OBJECTIVES.format("section G items G1-G7"),
    48: _INSTRUMENT_IN.format(
        "section G wife sickness, vacation, strike, unemployment, weeks, and "
        "hours exposure items G8-G19"
    ),
    49: _OBJECTIVES.format("section G items G8-G18"),
    50: _INSTRUMENT_IN.format(
        "section G wife current money-work, commuting, age checkpoint, and "
        "employer-tenure items G20-G28"
    ),
    51: _OBJECTIVES.format(
        "no printed item; the sheet extracts only its printed page number"
    ),
    52: _INSTRUMENT_NONE.format(
        "section G wife hiring-help, retirement-expectation, and housework "
        "items G29-G39",
        "a job-search-help, prospective retirement, prospective benefit-"
        "eligibility, or housework field that maps to no ratified section-19 "
        "field purpose",
    ),
    53: _OBJECTIVES.format("section G items G29 and G39"),
    54: _INSTRUMENT_OUT.format("section G housework items G40-G45"),
    55: _OBJECTIVES.format("section G items G41 and G43-G44"),
    56: _INSTRUMENT_OUT.format(
        "section G current food-stamp and food-expenditure items G46-G58"
    ),
    57: _OBJECTIVES.format("section G items G47-G58"),
    58: _INSTRUMENT_OUT.format("section G 1977 food-stamp items G59-G62"),
    59: _OBJECTIVES.format("section G items G59-G62"),
    60: _INSTRUMENT_IN.format(
        "section H entry and the farm, business, and head wage-and-salary "
        "items H1-H8"
    ),
    61: _OBJECTIVES.format("section H items H1-H8"),
    62: _OBJECTIVES.format("the continuation of section H item H8"),
    63: _EMPTY,
    64: _INSTRUMENT_IN.format(
        "section H head supplementary-earnings and other-income-source items "
        "H9-H19"
    ),
    65: _OBJECTIVES.format("section H items H9-H11c"),
    66: _OBJECTIVES.format("section H items H11d-H15"),
    67: _OBJECTIVES.format("section H item H16"),
    68: _INSTRUMENT_IN.format(
        "section H head transfer items and the wife income, source, and "
        "amount items H20-H31"
    ),
    69: _OBJECTIVES.format("section H items H20a-H20g"),
    70: _OBJECTIVES.format("section H items H21-H31"),
    71: _EMPTY,
    72: _INSTRUMENT_IN.format(
        "the section H extra-earner checkpoint, listing, and income, source, "
        "work, and exposure items H32-H45"
    ),
    73: _OBJECTIVES.format("section H items H32-H45"),
    74: _INSTRUMENT_IN.format(
        "the reprinted section H extra-earner grid, which prints the same "
        "income, source, occupation, weeks, hours, and exposure fields for "
        "three further listed persons"
    ),
    75: _OBJECTIVES.format(
        "the reprinted extra-earner grid, which the sheet describes as a "
        "repetition of the previous page"
    ),
    76: _INSTRUMENT_NONE.format(
        "section H residual-income, welfare, medical, and family job-search "
        "items H46-H56",
        "a residual household-income, public-assistance, medical-programme, "
        "or job-search field that maps to no ratified section-19 field "
        "purpose; its printed turn-back directive over the retained extra-"
        "earner grid is therefore not retained either, and the same repeat "
        "relation is carried by the directives printed on pages 72 and 74",
    ),
    77: _OBJECTIVES.format("section H items H46-H51"),
    78: _INSTRUMENT_NONE.format(
        "section H lump-sum, outside-support, labour-union, and head "
        "disability items H57-H71",
        "a lump-sum receipt, outside-support, dependency, labour-union "
        "membership, or health-limitation field that maps to no ratified "
        "section-19 field purpose",
    ),
    79: _OBJECTIVES.format("section H items H59-H70"),
    80: _INSTRUMENT_NONE.format(
        "section H other-adult disability items H72-H80",
        "a health-limitation, care-burden, or extra-cost field that maps to "
        "no ratified section-19 field purpose",
    ),
    81: _OBJECTIVES.format(
        "no printed item; the sheet extracts only its printed page number"
    ),
    82: _INSTRUMENT_NONE.format(
        "section H under-18 disability items H81-H89",
        "a health-limitation, care-burden, or extra-cost field that maps to "
        "no ratified section-19 field purpose",
    ),
    83: _OBJECTIVES.format(
        "no printed item; the sheet extracts only its printed page number"
    ),
    84: _INSTRUMENT_IN.format(
        "section J entry, the new-wife checkpoint, and the wife schooling "
        "and lifetime work-history items J1-J12"
    ),
    85: _OBJECTIVES.format("section J items J1-J12"),
    86: _INSTRUMENT_IN.format(
        "section K entry, the new-head checkpoint, and the parental-"
        "background, first-job, and children items K1-K10"
    ),
    87: _OBJECTIVES.format("section K items K1-K10"),
    88: _INSTRUMENT_OUT.format(
        "section K new-head sibling, growing-up, mobility, parental-"
        "education, and veteran items K11-K24"
    ),
    89: _OBJECTIVES.format("section K items K11-K24"),
    90: _INSTRUMENT_IN.format(
        "the section K new-head lifetime work-history items K25-K27 and the "
        "schooling items K28-K36"
    ),
    91: _OBJECTIVES.format("section K items K27-K37"),
    92: _INSTRUMENT_OUT.format("section L by-observation items L1-L8"),
    93: _OBJECTIVES.format("section L items L1-L8"),
    94: _INSTRUMENT_OUT.format(
        "the thumbnail-sketch sheet, which extracts only its printed heading"
    ),
    95: _OBJECTIVES.format("the thumbnail-sketch sheet"),
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

SECTION_D = ("p12_flow_section_d",)
_JOB_PRESENT = (
    "Parent is the printed present-position job anchor, which governs the "
    "screen's tenure and start-month fields."
)
_JOB_MAIN = (
    "Parent is the printed main-job anchor, which governs the head's 1977 "
    "weeks, hours, overtime, and missed-work exposure fields."
)
_JOB_EXTRA = (
    "Parent is the screen's printed extra-job anchor, which governs its "
    "extra-job pay, weeks, and hours fields."
)
_COLUMN_NOTE = (
    "The 1978 screen photographs answer columns side by side, so this span "
    "is the exact contiguous printed run inside one column; no span is "
    "carried across the printed column gutter."
)
_NO_PARENT = (
    "No printed parent job or aggregate on this screen; parenting is "
    "deferred to global assembly."
)

# Page 12 - section D entry and head employment items D1-D4.
PAGE_12 = (
    line(
        12,
        1,
        F,
        "p12_flow_section_d",
        note="Printed section D header conditions the head employment "
        "schedule selected at D1.",
    ),
    block(
        12,
        5,
        6,
        C,
        "p12_d1_assignment",
        routes=(SECTION_D,),
        note="D1 prints the head labour-force assignment field that selects "
        "the D, E, or F schedule.",
    ),
    block(12, 5, 6, P, "p12_d1_prompt", routes=(SECTION_D,)),
    word(
        12,
        5,
        "HEAD",
        R,
        "p12_role_head_d1",
        routes=(SECTION_D,),
        note="Earliest printed head lexeme on the screen whose bytes survive "
        "the scan intact; the section header prints no role lexeme.",
    ),
    run(
        12,
        13,
        1,
        5,
        F,
        "p12_flow_d1_turn_section_f",
        routes=(SECTION_D,),
        note="D1 routing atom into the section F schedule, printed beside "
        "the permanently-disabled answer box.",
    ),
    line(
        12,
        14,
        F,
        "p12_flow_d1_turn_section_e",
        routes=(SECTION_D,),
        note="D1 routing atom into the section E schedule; the printed "
        "target item name prints on a separate physical line of the scanned "
        "answer column and is not spanned.",
    ),
    run(
        12,
        17,
        5,
        8,
        F,
        "p12_flow_d1_other_has_job",
        routes=(SECTION_D,),
        note="D1 conditional routing atom that continues the D schedule for "
        "an other-category respondent who holds a job.",
    ),
    block(
        12,
        19,
        20,
        F,
        "p12_flow_d1_other_no_job",
        routes=(SECTION_D,),
        note="D1 fall-through routing atom into section F; the directive "
        "verb and its printed target are photographed onto consecutive "
        "physical lines, so the retained span is the printed block that "
        "carries both.",
    ),
    line(
        12,
        24,
        C,
        "p12_d2_occupation",
        routes=(SECTION_D,),
        note="D2 prints the head main-occupation field.",
    ),
    line(12, 24, P, "p12_d2_prompt", routes=(SECTION_D,)),
    line(
        12,
        32,
        F,
        "p12_flow_d3_if_not_clear",
        routes=(SECTION_D,),
        note="Printed condition that governs the D3 occupation probe.",
    ),
    line(
        12,
        33,
        C,
        "p12_d3_occupation_detail",
        routes=(SECTION_D + ("p12_flow_d3_if_not_clear",),),
        note="D3 prints the head occupation-detail probe field, "
        "administered only under the printed not-clear condition.",
    ),
    line(
        12,
        33,
        P,
        "p12_d3_prompt",
        routes=(SECTION_D + ("p12_flow_d3_if_not_clear",),),
    ),
    line(
        12,
        38,
        C,
        "p12_d4_industry",
        routes=(SECTION_D,),
        note="D4 prints the head industry field.",
    ),
    line(12, 38, P, "p12_d4_prompt", routes=(SECTION_D,)),
)

# Page 16 - section D head employer and government-level items D5-D17.
PAGE_16 = (
    line(
        16,
        1,
        C,
        "p16_d5_employee_self_or_mixed",
        routes=(SECTION_D,),
        note="D5 prints the works-for-someone-else/self/both field.",
    ),
    line(16, 1, P, "p16_d5_prompt", routes=(SECTION_D,)),
    run(16, 4, 1, 3, F, "p16_flow_d5_self_only", routes=(SECTION_D,)),
    run(
        16,
        7,
        0,
        8,
        C,
        "p16_d6_government_level",
        routes=(SECTION_D,),
        note="D6 prints the federal/state/local government-level field for "
        "a head who works for someone else. " + _COLUMN_NOTE,
    ),
    run(16, 7, 0, 8, P, "p16_d6_prompt", routes=(SECTION_D,)),
    run(
        16,
        7,
        9,
        19,
        C,
        "p16_d9_government_level",
        routes=(SECTION_D,),
        note="D9 prints the government-level field for a head who works "
        "both for someone else and for self. " + _COLUMN_NOTE,
    ),
    run(16, 7, 9, 19, P, "p16_d9_prompt", routes=(SECTION_D,)),
    line(16, 20, F, "p16_flow_d7_go_to_d12", routes=(SECTION_D,)),
    line(16, 24, F, "p16_flow_d8_go_to_d12", routes=(SECTION_D,)),
    line(16, 31, F, "p16_flow_d11_go_to_d12", routes=(SECTION_D,)),
    line(16, 35, F, "p16_flow_d11_no_go_to_d12", routes=(SECTION_D,)),
    run(16, 48, 1, 3, F, "p16_flow_d13_go_to_d15", routes=(SECTION_D,)),
)

# Page 18 - section D head tenure and work-time exposure items D18-D29.
PAGE_18 = (
    word(
        18,
        2,
        "pre sent position",
        J,
        "p18_job_present_position",
        routes=(SECTION_D,),
        note="D18 prints the head's present-position job noun; the scan "
        "splits the printed word present and the span is retained verbatim.",
    ),
    line(
        18,
        2,
        C,
        "p18_d18_tenure",
        routes=(SECTION_D,),
        parents=("p18_job_present_position",),
        parent_note=_JOB_PRESENT,
        note="D18 prints the present-position tenure exposure field in "
        "printed months or years.",
    ),
    line(18, 2, P, "p18_d18_prompt", routes=(SECTION_D,)),
    run(
        18,
        7,
        0,
        4,
        F,
        "p18_flow_d18_less_than_year",
        routes=(SECTION_D,),
        note="D18 checkpoint branch A: present position held less than one "
        "year.",
    ),
    run(
        18,
        7,
        5,
        11,
        F,
        "p18_flow_d18_year_or_more",
        routes=(SECTION_D,),
        note="D18 checkpoint branch B: present position held one year or "
        "more, with its printed routing atom.",
    ),
    line(
        18,
        11,
        C,
        "p18_d19_start_month",
        routes=(SECTION_D + ("p18_flow_d18_less_than_year",),),
        parents=("p18_job_present_position",),
        parent_note=_JOB_PRESENT
        + "  The printed this job is a back-reference to that anchor and is "
        "not promoted to a second job.",
        note="D19 prints the start-month exposure field for the present "
        "position and is administered only under the D18 less-than-a-year "
        "branch.",
    ),
    line(
        18,
        11,
        P,
        "p18_d19_prompt",
        routes=(SECTION_D + ("p18_flow_d18_less_than_year",),),
    ),
    line(18, 17, F, "p18_flow_d20_no_previous_job", routes=(SECTION_D,)),
    run(18, 22, 6, 8, F, "p18_flow_d21_same", routes=(SECTION_D,)),
    line(18, 33, F, "p18_flow_d23_go_to_d24", routes=(SECTION_D,)),
    line(
        18,
        35,
        C,
        "p18_d24_missed_family_sick",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D24 prints a 1977 work-time exposure field for the head.",
    ),
    line(18, 35, P, "p18_d24_prompt", routes=(SECTION_D,)),
    run(18, 37, 5, 7, F, "p18_flow_d24_no", routes=(SECTION_D,)),
    line(
        18,
        39,
        C,
        "p18_d25_amount",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(18, 39, P, "p18_d25_prompt", routes=(SECTION_D,)),
    line(
        18,
        42,
        C,
        "p18_d26_missed_own_sick",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(18, 42, P, "p18_d26_prompt", routes=(SECTION_D,)),
    run(18, 44, 6, 8, F, "p18_flow_d26_no", routes=(SECTION_D,)),
    line(
        18,
        46,
        C,
        "p18_d27_amount",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(18, 46, P, "p18_d27_prompt", routes=(SECTION_D,)),
    line(
        18,
        49,
        C,
        "p18_d28_vacation",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(18, 49, P, "p18_d28_prompt", routes=(SECTION_D,)),
    run(18, 51, 6, 10, F, "p18_flow_d28_no", routes=(SECTION_D,)),
    line(
        18,
        53,
        C,
        "p18_d29_amount",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(18, 53, P, "p18_d29_prompt", routes=(SECTION_D,)),
)

# Page 20 - section D head strike, unemployment, weeks, hours, overtime.
PAGE_20 = (
    line(
        20,
        1,
        C,
        "p20_d30_strike",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D30 prints a strike work-time exposure field for the head.",
    ),
    line(20, 1, P, "p20_d30_prompt", routes=(SECTION_D,)),
    run(20, 3, 2, 4, F, "p20_flow_d30_no", routes=(SECTION_D,)),
    line(
        20,
        6,
        C,
        "p20_d31_amount",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(20, 6, P, "p20_d31_prompt", routes=(SECTION_D,)),
    line(
        20,
        10,
        C,
        "p20_d32_unemployed",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(20, 10, P, "p20_d32_prompt", routes=(SECTION_D,)),
    run(20, 12, 5, 7, F, "p20_flow_d32_no", routes=(SECTION_D,)),
    line(
        20,
        14,
        C,
        "p20_d33_amount",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(20, 14, P, "p20_d33_prompt", routes=(SECTION_D,)),
    line(
        20,
        18,
        C,
        "p20_d34_weeks_worked",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D34 prints the head's 1977 weeks-worked exposure field for "
        "the main job.",
    ),
    line(20, 18, P, "p20_d34_prompt", routes=(SECTION_D,)),
    word(20, 18, "main job", J, "p20_job_main_job", routes=(SECTION_D,)),
    line(
        20,
        22,
        C,
        "p20_d35_hours_per_week",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(20, 22, P, "p20_d35_prompt", routes=(SECTION_D,)),
    line(
        20,
        27,
        C,
        "p20_d36_overtime",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D36 prints an overtime work-time exposure field for the "
        "head's main job.",
    ),
    line(20, 27, P, "p20_d36_prompt", routes=(SECTION_D,)),
    run(20, 29, 7, 11, F, "p20_flow_d36_no", routes=(SECTION_D,)),
    line(
        20,
        31,
        C,
        "p20_d37_overtime_hours",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
    ),
    line(20, 31, P, "p20_d37_prompt", routes=(SECTION_D,)),
)

# Page 22 - section D head pay-form, wage-rate, and extra-job items D38-D51.
PAGE_22 = (
    line(
        22,
        2,
        C,
        "p22_d38_pay_form",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D38 prints the salaried/hourly pay-form field for the head's "
        "main job; the printed item identifier is scanned as D18 and is "
        "retained verbatim.",
    ),
    line(22, 2, P, "p22_d38_prompt", routes=(SECTION_D,)),
    run(
        22,
        6,
        0,
        5,
        M,
        "p22_d39_salary",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D39 salary component. " + _COLUMN_NOTE,
    ),
    run(
        22,
        6,
        6,
        12,
        M,
        "p22_d42_regular_wage_rate",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D42 regular-work hourly wage-rate component; the printed word "
        "rate prints on the next physical line of the same column and is "
        "not spanned. " + _COLUMN_NOTE,
    ),
    run(
        22,
        14,
        5,
        11,
        M,
        "p22_d43_overtime_wage_rate",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D43 overtime hourly wage-rate component. " + _COLUMN_NOTE,
    ),
    block(
        22,
        24,
        25,
        M,
        "p22_d41_overtime_hourly_pay",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D41 overtime hourly-pay component. " + _COLUMN_NOTE,
    ),
    line(22, 22, F, "p22_flow_d40_no_go_to_d46", routes=(SECTION_D,)),
    line(22, 26, F, "p22_flow_d41_go_to_d46", routes=(SECTION_D,)),
    block(
        22,
        27,
        29,
        M,
        "p22_d45_extra_hour_earnings",
        routes=(SECTION_D,),
        parents=("p20_job_main_job",),
        parent_note=_JOB_MAIN,
        note="D45 extra-hour earnings component. " + _COLUMN_NOTE,
    ),
    line(22, 34, F, "p22_flow_d44_go_to_d46", routes=(SECTION_D,)),
    line(22, 35, F, "p22_flow_d45_go_to_d46", routes=(SECTION_D,)),
    word(22, 40, "extra jobs", J, "p22_job_extra_jobs", routes=(SECTION_D,)),
    block(
        22,
        40,
        41,
        C,
        "p22_d46_extra_jobs",
        routes=(SECTION_D,),
        parents=("p22_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
        note="D46 prints the head extra-job assignment field.",
    ),
    block(22, 40, 41, P, "p22_d46_prompt", routes=(SECTION_D,)),
    run(22, 43, 2, 6, F, "p22_flow_d46_no", routes=(SECTION_D,)),
    line(
        22,
        45,
        C,
        "p22_d47_extra_job_occupation",
        routes=(SECTION_D,),
        parents=("p22_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
        note="D47 prints the extra-job occupation field.",
    ),
    line(22, 45, P, "p22_d47_prompt", routes=(SECTION_D,)),
    line(
        22,
        53,
        M,
        "p22_d49_extra_job_hourly_pay",
        routes=(SECTION_D,),
        parents=("p22_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
        note="D49 prints the extra-job hourly-pay component.",
    ),
    line(22, 53, P, "p22_d49_prompt", routes=(SECTION_D,)),
    line(
        22,
        55,
        C,
        "p22_d50_extra_job_weeks",
        routes=(SECTION_D,),
        parents=("p22_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
    ),
    line(22, 55, P, "p22_d50_prompt", routes=(SECTION_D,)),
    line(
        22,
        59,
        C,
        "p22_d51_extra_job_hours",
        routes=(SECTION_D,),
        parents=("p22_job_extra_jobs",),
        parent_note=_JOB_EXTRA,
    ),
    line(22, 59, P, "p22_d51_prompt", routes=(SECTION_D,)),
)

# Page 26 - the section D age checkpoint and first-job history D60-D71.
PAGE_26 = (
    run(
        26,
        8,
        0,
        4,
        F,
        "p26_flow_d60_under_45",
        routes=(SECTION_D,),
        note="D60 interviewer checkpoint branch 1: head is under 45.  The "
        "printed checkpoint stem on the preceding line is destroyed by the "
        "scan and is not reconstructed.",
    ),
    word(26, 8, "HEAD", R, "p26_role_head_d60", routes=(SECTION_D,)),
    run(
        26,
        8,
        5,
        11,
        F,
        "p26_flow_d60_45_to_64",
        routes=(SECTION_D,),
        note="D60 interviewer checkpoint branch 2: head is 45-64.",
    ),
    run(
        26,
        8,
        12,
        17,
        F,
        "p26_flow_d60_65_or_older",
        routes=(SECTION_D,),
        note="D60 interviewer checkpoint branch 3: head is 65 or older.",
    ),
    run(26, 11, 0, 4, F, "p26_flow_d60_turn_d83", routes=(SECTION_D,)),
    run(26, 11, 5, 9, F, "p26_flow_d60_turn_section_g", routes=(SECTION_D,)),
    word(
        26,
        14,
        "a regular or possibly permanent job",
        J,
        "p26_job_first_regular",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
        note="D61 prints the head's first regular or possibly permanent job "
        "noun.",
    ),
    line(
        26,
        23,
        C,
        "p26_d62_first_job_occupation",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
        parents=("p26_job_first_regular",),
        parent_note="Parent is the printed first regular or possibly "
        "permanent job anchor named in the same question block.",
        note="D62 prints the occupation of the head's first regular job; "
        "the printed item identifiers D62 and D63 are photographed onto "
        "separate physical lines above the printed question.",
    ),
    line(
        26,
        23,
        P,
        "p26_d62_prompt",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
    ),
    run(
        26,
        45,
        2,
        4,
        F,
        "p26_flow_d65_no",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
    ),
    run(
        26,
        64,
        2,
        4,
        F,
        "p26_flow_d68_no",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
    ),
    run(
        26,
        71,
        1,
        3,
        F,
        "p26_flow_d69_no",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
    ),
    line(
        26,
        78,
        F,
        "p26_flow_d70_go_to_d71",
        routes=(SECTION_D + ("p26_flow_d60_under_45",),),
    ),
)

# Page 28 - section D head present-employer items D72-D82.
PAGE_28 = (
    run(28, 4, 2, 6, F, "p28_flow_d72_same_employer", routes=(SECTION_D,)),
    line(
        28,
        7,
        C,
        "p28_d73_employer_tenure",
        routes=(SECTION_D,),
        parents=("p18_job_present_position",),
        parent_note=_JOB_PRESENT
        + "  The printed present employer is the reporting unit of that "
        "job, not a second printed job.",
        note="D73 prints the head's tenure-with-present-employer exposure "
        "field in printed years or months.",
    ),
    line(28, 7, P, "p28_d73_prompt", routes=(SECTION_D,)),
    run(28, 31, 2, 4, F, "p28_flow_d76_no", routes=(SECTION_D,)),
    run(28, 49, 1, 3, F, "p28_flow_d79_no", routes=(SECTION_D,)),
    run(28, 56, 2, 4, F, "p28_flow_d80_no", routes=(SECTION_D,)),
    line(28, 68, F, "p28_flow_d82_turn_section_g", routes=(SECTION_D,)),
)


SECTION_E = ("p32_flow_section_e",)
SECTION_F = ("p40_flow_section_f",)
_JOB_SOUGHT = (
    "Parent is the printed sought-job anchor named in the same question "
    "block."
)
_JOB_LAST = (
    "Parent is the screen's printed last-job anchor, which governs its "
    "occupation, industry, and 1977 exposure fields."
)
_JOB_FIRST = (
    "Parent is the printed first regular or possibly permanent job anchor "
    "named in the same question block."
)

# Page 32 - section E entry and head sought-job items E1-E13.
PAGE_32 = (
    run(
        32,
        1,
        0,
        9,
        F,
        "p32_flow_section_e",
        note="Printed section E header conditions the schedule administered "
        "when D1 selected looking-for-work or unemployed; the trailing "
        "printed coder box on the same line is not spanned.",
    ),
    word(32, 3, "job", J, "p32_job_sought", routes=(SECTION_E,)),
    line(
        32,
        3,
        C,
        "p32_e1_sought_occupation",
        routes=(SECTION_E,),
        parents=("p32_job_sought",),
        parent_note=_JOB_SOUGHT,
        note="E1 prints the sought-job occupation field.",
    ),
    line(32, 3, P, "p32_e1_prompt", routes=(SECTION_E,)),
    line(
        32,
        8,
        M,
        "p32_e2_expected_earnings",
        routes=(SECTION_E,),
        parents=("p32_job_sought",),
        parent_note=_JOB_SOUGHT,
        note="E2 prints the expected-earnings remuneration component for "
        "the sought job with its printed reporting-unit box.",
    ),
    line(32, 8, P, "p32_e2_prompt", routes=(SECTION_E,)),
    run(32, 20, 5, 7, F, "p32_flow_e4_no", routes=(SECTION_E,)),
    line(32, 48, F, "p32_flow_e9_go_to_e10", routes=(SECTION_E,)),
)

# Page 34 - section E ever-had-a-job, age checkpoint, first-job E14-E26.
PAGE_34 = (
    word(34, 2, "job", J, "p34_job_ever_had", routes=(SECTION_E,)),
    line(
        34,
        2,
        C,
        "p34_e14_ever_had_job",
        routes=(SECTION_E,),
        parents=("p34_job_ever_had",),
        parent_note="Parent is the printed job noun in the same question "
        "block.",
        note="E14 prints the ever-held-a-job assignment field.",
    ),
    line(34, 2, P, "p34_e14_prompt", routes=(SECTION_E,)),
    line(34, 14, F, "p34_flow_e14_no_turn_section_g", routes=(SECTION_E,)),
    run(
        34,
        19,
        0,
        5,
        F,
        "p34_flow_e15_under_45",
        routes=(SECTION_E,),
        note="E15 interviewer checkpoint branch 1: head is under 45; the "
        "printed role lexeme in this branch is destroyed by the scan.",
    ),
    word(34, 19, "HEAD", R, "p34_role_head_e15", routes=(SECTION_E,)),
    run(
        34,
        19,
        6,
        11,
        F,
        "p34_flow_e15_45_or_older",
        routes=(SECTION_E,),
        note="E15 interviewer checkpoint branch 2: head is 45 or older.",
    ),
    run(34, 19, 12, 16, F, "p34_flow_e15_turn_e27", routes=(SECTION_E,)),
    word(
        34,
        25,
        "a regular or possibly permanent job",
        J,
        "p34_job_first_regular",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
        note="E16 prints the head's first regular or possibly permanent job "
        "noun.",
    ),
    run(
        34,
        31,
        1,
        5,
        F,
        "p34_flow_e16_never_had_job",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
    ),
    run(
        34,
        34,
        0,
        11,
        C,
        "p34_e17_first_job_occupation",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
        parents=("p34_job_first_regular",),
        parent_note=_JOB_FIRST,
        note="E17 prints the occupation of the head's first regular job; "
        "the trailing printed rule and coder boxes on the same line are not "
        "spanned.",
    ),
    run(
        34,
        34,
        0,
        11,
        P,
        "p34_e17_prompt",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
    ),
    run(
        34,
        47,
        5,
        7,
        F,
        "p34_flow_e20_no",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
    ),
    run(
        34,
        62,
        5,
        7,
        F,
        "p34_flow_e23_no",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
    ),
    run(
        34,
        68,
        5,
        7,
        F,
        "p34_flow_e24_no",
        routes=(SECTION_E + ("p34_flow_e15_under_45",),),
    ),
)

# Page 36 - section E head last-job items E27-E38.
PAGE_36 = (
    word(36, 2, "last job", J, "p36_job_last", routes=(SECTION_E,)),
    line(
        36,
        2,
        C,
        "p36_e27_last_job_occupation",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E27 prints the occupation of the head's last job.",
    ),
    line(36, 2, P, "p36_e27_prompt", routes=(SECTION_E,)),
    line(
        36,
        7,
        C,
        "p36_e28_last_job_industry",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E28 prints the industry of the head's last job.",
    ),
    line(36, 7, P, "p36_e28_prompt", routes=(SECTION_E,)),
    line(
        36,
        18,
        C,
        "p36_e30_last_worked",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E30 prints the last-worked exposure field.",
    ),
    line(36, 18, P, "p36_e30_prompt", routes=(SECTION_E,)),
    run(
        36,
        20,
        0,
        4,
        F,
        "p36_flow_e30_1977_or_1978",
        routes=(SECTION_E,),
        note="E30 checkpoint branch A: the head last worked in 1977 or "
        "1978, which governs the remaining exposure items on this screen.",
    ),
    run(
        36,
        20,
        5,
        7,
        F,
        "p36_flow_e30_before_1977",
        routes=(SECTION_E,),
        note="E30 checkpoint branch B: the head last worked before 1977.",
    ),
    run(36, 20, 8, 12, F, "p36_flow_e30_turn_section_g", routes=(SECTION_E,)),
    line(
        36,
        22,
        C,
        "p36_e31_vacation",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        22,
        P,
        "p36_e31_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    run(
        36,
        25,
        1,
        3,
        F,
        "p36_flow_e31_no",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        27,
        C,
        "p36_e32_amount",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        27,
        P,
        "p36_e32_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        30,
        C,
        "p36_e33_missed_family_sick",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        30,
        P,
        "p36_e33_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    run(
        36,
        35,
        2,
        4,
        F,
        "p36_flow_e33_no",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        37,
        C,
        "p36_e34_amount",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        37,
        P,
        "p36_e34_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        40,
        C,
        "p36_e35_missed_own_sick",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        40,
        P,
        "p36_e35_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    run(
        36,
        44,
        2,
        4,
        F,
        "p36_flow_e35_no",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        46,
        C,
        "p36_e36_amount",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        46,
        P,
        "p36_e36_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        49,
        C,
        "p36_e37_strike",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(
        36,
        49,
        P,
        "p36_e37_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    run(
        36,
        54,
        2,
        6,
        F,
        "p36_flow_e37_no",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
    line(
        36,
        56,
        C,
        "p36_e38_amount",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E38 prints the strike exposure amount; the printed item "
        "identifier is scanned as E33 and is retained verbatim.",
    ),
    line(
        36,
        56,
        P,
        "p36_e38_prompt",
        routes=(SECTION_E + ("p36_flow_e30_1977_or_1978",),),
    ),
)

# Page 38 - section E unemployment exposure, weeks, hours E39-E45.
PAGE_38 = (
    line(
        38,
        2,
        C,
        "p38_e39_unemployed",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E39 prints the unemployment work-time exposure field; the "
        "printed question continues onto scan-destroyed bytes below and "
        "only the legible stem line is spanned.",
    ),
    line(38, 2, P, "p38_e39_prompt", routes=(SECTION_E,)),
    run(38, 7, 2, 4, F, "p38_flow_e39_no", routes=(SECTION_E,)),
    line(
        38,
        10,
        C,
        "p38_e40_amount",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(38, 10, P, "p38_e40_prompt", routes=(SECTION_E,)),
    line(
        38,
        14,
        C,
        "p38_e41_weeks_worked",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
        note="E41 prints the 1977 weeks-worked exposure field.",
    ),
    line(38, 14, P, "p38_e41_prompt", routes=(SECTION_E,)),
    line(
        38,
        18,
        C,
        "p38_e42_hours_per_week",
        routes=(SECTION_E,),
        parents=("p36_job_last",),
        parent_note=_JOB_LAST,
    ),
    line(38, 18, P, "p38_e42_prompt", routes=(SECTION_E,)),
    run(38, 26, 5, 9, F, "p38_flow_e43_none", routes=(SECTION_E,)),
    line(38, 45, F, "p38_flow_e45_turn_section_g", routes=(SECTION_E,)),
)

# Page 40 - section F entry and head post-retirement money work F1-F9.
PAGE_40 = (
    line(
        40,
        2,
        F,
        "p40_flow_section_f",
        note="Printed section F header conditions the schedule administered "
        "for a head who is retired, a housewife, a student, or permanently "
        "disabled.",
    ),
    run(
        40,
        10,
        0,
        1,
        F,
        "p40_flow_f1_retired",
        routes=(SECTION_F,),
        note="F1 interviewer checkpoint branch 1: the head is retired.",
    ),
    run(
        40,
        10,
        2,
        9,
        F,
        "p40_flow_f1_other",
        routes=(SECTION_F,),
        note="F1 interviewer checkpoint branch 2: the head is permanently "
        "disabled, a housewife, a student, or other.",
    ),
    line(40, 11, F, "p40_flow_f1_turn_f15", routes=(SECTION_F,)),
    run(
        40,
        16,
        0,
        5,
        F,
        "p40_flow_f2_less_than_20_years",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    run(
        40,
        16,
        6,
        11,
        F,
        "p40_flow_f2_20_or_more_years",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    run(
        40,
        16,
        13,
        19,
        F,
        "p40_flow_f2_turn_f15",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    line(
        40,
        30,
        F,
        "p40_flow_f4_planned_go_to_f6",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    line(
        40,
        31,
        F,
        "p40_flow_f4_unexpected_go_to_f6",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    line(
        40,
        50,
        C,
        "p40_f7_post_retirement_money_work",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
        parent_note=_NO_PARENT,
        note="F7 prints the post-retirement money-work assignment field; "
        "the printed item identifier is scanned as F1 and is retained "
        "verbatim.",
    ),
    line(
        40,
        50,
        P,
        "p40_f7_prompt",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
    run(
        40,
        63,
        2,
        7,
        F,
        "p40_flow_f8_no_turn_f10",
        routes=(SECTION_F + ("p40_flow_f1_retired",),),
    ),
)

# Page 42 - section F head 1977 money-work items F10-F21.
PAGE_42 = (
    run(42, 6, 1, 3, F, "p42_flow_f10_no", routes=(SECTION_F,)),
    line(
        42,
        30,
        C,
        "p42_f15_money_work",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
        note="F15 prints the 1977 money-work assignment field for a head "
        "outside the labour force.",
    ),
    line(42, 30, P, "p42_f15_prompt", routes=(SECTION_F,)),
    run(42, 32, 2, 6, F, "p42_flow_f15_no", routes=(SECTION_F,)),
    line(
        42,
        35,
        C,
        "p42_f16_occupation",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
        note="F16 prints the occupation of the head's 1977 money work; the "
        "screen prints no job noun, so no job anchor is emitted.",
    ),
    line(42, 35, P, "p42_f16_prompt", routes=(SECTION_F,)),
    line(
        42,
        40,
        C,
        "p42_f17_industry",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
        note="F17 prints the industry of the head's 1977 money work.",
    ),
    line(42, 40, P, "p42_f17_prompt", routes=(SECTION_F,)),
    line(
        42,
        42,
        C,
        "p42_f18_weeks_worked",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
    ),
    line(42, 42, P, "p42_f18_prompt", routes=(SECTION_F,)),
    line(
        42,
        45,
        C,
        "p42_f19_hours_per_week",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
    ),
    line(42, 45, P, "p42_f19_prompt", routes=(SECTION_F,)),
    line(
        42,
        48,
        C,
        "p42_f20_still_working",
        routes=(SECTION_F,),
        parent_note=_NO_PARENT,
        note="F20 prints the still-working assignment field; the printed "
        "that job at F21 is a back-reference and is not promoted to a "
        "second job.",
    ),
    line(42, 48, P, "p42_f20_prompt", routes=(SECTION_F,)),
    line(42, 53, F, "p42_flow_f20_turn_f22", routes=(SECTION_F,)),
)


SECTION_G = ("p46_flow_section_g",)
SECTION_H = ("p60_flow_section_h",)
_JOB_WIFE_MAIN = (
    "Parent is the printed wife main-job anchor, which governs the wife's "
    "1977 weeks, hours, and missed-work exposure fields."
)
_FARM_PARENT = "Parent is the screen's printed farm aggregate anchor."
_BUSINESS_PARENT = (
    "Parent is the screen's printed unincorporated-business aggregate "
    "anchor."
)

# Page 46 - section G entry, marital checkpoint, wife work items G1-G7.
PAGE_46 = (
    line(
        46,
        2,
        F,
        "p46_flow_section_g",
        note="Printed section G header conditions the wife work, housework, "
        "and food schedule; the printed role lexeme in the header is split "
        "by the scan and is not retained as a role anchor.",
    ),
    line(46, 15, F, "p46_flow_g1_married_go_to_g4", routes=(SECTION_G,)),
    line(46, 16, F, "p46_flow_g1_single_go_to_g4", routes=(SECTION_G,)),
    run(46, 23, 4, 6, F, "p46_flow_g2_no_go_to_g4", routes=(SECTION_G,)),
    line(
        46,
        34,
        F,
        "p46_flow_g4_wife_in_fu",
        routes=(SECTION_G,),
        note="G4 interviewer checkpoint branch 1: a male head is married "
        "with a wife in the FU, which governs the wife work items.",
    ),
    word(
        46,
        34,
        "WIFE",
        R,
        "p46_role_wife_g4",
        routes=(SECTION_G,),
        note="Earliest printed wife lexeme on the screen whose bytes "
        "survive the scan intact.",
    ),
    run(
        46,
        35,
        2,
        7,
        F,
        "p46_flow_g4_all_others",
        routes=(SECTION_G,),
        note="G4 interviewer checkpoint branch 2: all other family types.",
    ),
    run(
        46,
        36,
        0,
        6,
        F,
        "p46_flow_g4_female_friend",
        routes=(SECTION_G,),
        note="G4 interviewer checkpoint branch 1 alternative: a male head "
        "has lived with a female friend for one year or more.",
    ),
    run(46, 36, 7, 11, F, "p46_flow_g4_turn_g40", routes=(SECTION_G,)),
    line(
        46,
        40,
        C,
        "p46_g5_wife_money_work",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
        parent_note=_NO_PARENT,
        note="G5 prints the wife's 1977 money-work assignment field.",
    ),
    line(
        46,
        40,
        P,
        "p46_g5_prompt",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
    ),
    run(
        46,
        42,
        2,
        6,
        F,
        "p46_flow_g5_no",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
    ),
    line(
        46,
        45,
        C,
        "p46_g6_wife_occupation",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
        note="G6 prints the wife's occupation field.",
    ),
    line(
        46,
        45,
        P,
        "p46_g6_prompt",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
    ),
    line(
        46,
        49,
        C,
        "p46_g7_wife_industry",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
        note="G7 prints the wife's industry field.",
    ),
    line(
        46,
        49,
        P,
        "p46_g7_prompt",
        routes=(SECTION_G + ("p46_flow_g4_wife_in_fu",),),
    ),
)

# Page 48 - section G wife 1977 exposure items G8-G19.
PAGE_48 = (
    block(
        48,
        2,
        3,
        C,
        "p48_g8_missed_family_sick",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
        note="G8 prints a 1977 work-time exposure field for the wife.",
    ),
    block(48, 2, 3, P, "p48_g8_prompt", routes=(SECTION_G,)),
    run(48, 5, 4, 6, F, "p48_flow_g8_no", routes=(SECTION_G,)),
    line(
        48,
        10,
        C,
        "p48_g9_amount",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
        note="G9 prints the missed-work amount; the printed item identifier "
        "is photographed onto a separate physical line above the question.",
    ),
    line(48, 10, P, "p48_g9_prompt", routes=(SECTION_G,)),
    line(
        48,
        14,
        C,
        "p48_g10_missed_own_sick",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 14, P, "p48_g10_prompt", routes=(SECTION_G,)),
    run(48, 18, 1, 4, F, "p48_flow_g10_no", routes=(SECTION_G,)),
    line(
        48,
        21,
        C,
        "p48_g11_amount",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 21, P, "p48_g11_prompt", routes=(SECTION_G,)),
    line(
        48,
        26,
        C,
        "p48_g12_vacation",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 26, P, "p48_g12_prompt", routes=(SECTION_G,)),
    run(48, 30, 1, 3, F, "p48_flow_g12_no", routes=(SECTION_G,)),
    line(
        48,
        33,
        C,
        "p48_g13_amount",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 33, P, "p48_g13_prompt", routes=(SECTION_G,)),
    line(
        48,
        37,
        C,
        "p48_g14_strike",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 37, P, "p48_g14_prompt", routes=(SECTION_G,)),
    run(48, 41, 1, 3, F, "p48_flow_g14_no", routes=(SECTION_G,)),
    line(
        48,
        44,
        C,
        "p48_g15_amount",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 44, P, "p48_g15_prompt", routes=(SECTION_G,)),
    block(
        48,
        48,
        49,
        C,
        "p48_g16_unemployed",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    block(48, 48, 49, P, "p48_g16_prompt", routes=(SECTION_G,)),
    run(48, 54, 2, 4, F, "p48_flow_g16_no", routes=(SECTION_G,)),
    line(
        48,
        57,
        C,
        "p48_g17_amount",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 57, P, "p48_g17_prompt", routes=(SECTION_G,)),
    word(
        48,
        48,
        "(wife/friend)",
        R,
        "p48_role_wife_g16",
        routes=(SECTION_G,),
        note="Earliest printed wife lexeme on the screen whose bytes "
        "survive the scan intact; the G8-G14 stems print the same lexeme "
        "through scan-destroyed bytes.",
    ),
    word(48, 61, "her main job", J, "p48_job_wife_main", routes=(SECTION_G,)),
    line(
        48,
        61,
        C,
        "p48_g18_weeks_worked",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
        note="G18 prints the wife's 1977 weeks-worked exposure field for "
        "her main job; the printed item identifier is scanned as G13 and is "
        "retained verbatim.",
    ),
    line(48, 61, P, "p48_g18_prompt", routes=(SECTION_G,)),
    line(
        48,
        65,
        C,
        "p48_g19_hours_per_week",
        routes=(SECTION_G,),
        parents=("p48_job_wife_main",),
        parent_note=_JOB_WIFE_MAIN,
    ),
    line(48, 65, P, "p48_g19_prompt", routes=(SECTION_G,)),
)

# Page 50 - section G wife current work, age checkpoint, employer tenure.
PAGE_50 = (
    line(
        50,
        2,
        C,
        "p50_g20_wife_working_now",
        routes=(SECTION_G,),
        parent_note=_NO_PARENT,
        note="G20 prints the wife's current money-work assignment field; "
        "the printed item identifier is scanned as G2U and is retained "
        "verbatim.",
    ),
    line(50, 2, P, "p50_g20_prompt", routes=(SECTION_G,)),
    word(50, 2, "(wife/friend)", R, "p50_role_wife_g20", routes=(SECTION_G,)),
    run(50, 4, 2, 6, F, "p50_flow_g20_no", routes=(SECTION_G,)),
    run(50, 11, 5, 7, F, "p50_flow_g21_none", routes=(SECTION_G,)),
    run(
        50,
        29,
        0,
        4,
        F,
        "p50_flow_g24_under_45",
        routes=(SECTION_G,),
        note="G24 interviewer checkpoint branch 1: the wife or friend is "
        "under 45.",
    ),
    run(
        50,
        29,
        5,
        10,
        F,
        "p50_flow_g24_45_or_older",
        routes=(SECTION_G,),
        note="G24 interviewer checkpoint branch 2: the wife or friend is 45 "
        "or older.",
    ),
    line(50, 30, F, "p50_flow_g24_turn_g34", routes=(SECTION_G,)),
    line(
        50,
        33,
        C,
        "p50_g25_employer_tenure",
        routes=(SECTION_G + ("p50_flow_g24_under_45",),),
        parent_note=_NO_PARENT
        + "  The printed her present employer names a reporting unit rather "
        "than a job, and it is not bound to the 1977 main-job anchor.",
        note="G25 prints the wife's tenure-with-present-employer exposure "
        "field in printed months or years.",
    ),
    line(
        50,
        33,
        P,
        "p50_g25_prompt",
        routes=(SECTION_G + ("p50_flow_g24_under_45",),),
    ),
    run(
        50,
        60,
        0,
        4,
        F,
        "p50_flow_g27_turn_g33",
        routes=(SECTION_G + ("p50_flow_g24_under_45",),),
    ),
)

# Page 60 - section H entry, farm, business, and head wage total H1-H8.
PAGE_60 = (
    line(
        60,
        2,
        F,
        "p60_flow_section_h",
        note="Printed section H header opens the income schedule.",
    ),
    run(
        60,
        16,
        0,
        3,
        F,
        "p60_flow_h1_farmer",
        routes=(SECTION_H,),
        note="H1 interviewer checkpoint branch 1: the head is a farmer or "
        "rancher.",
    ),
    run(
        60,
        16,
        4,
        9,
        F,
        "p60_flow_h1_not_farmer",
        routes=(SECTION_H,),
        note="H1 interviewer checkpoint branch 2: the head is not a farmer "
        "or rancher.",
    ),
    run(60, 16, 10, 12, F, "p60_flow_h1_go_to_h5", routes=(SECTION_H,)),
    block(
        60,
        20,
        21,
        M,
        "p60_h2_farm_receipts",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
        parents=("p60_farm_aggregate",),
        parent_note=_FARM_PARENT,
        note="H2 prints the total farm receipts component; the printed word "
        "farming is scanned as faming and is retained verbatim.",
    ),
    block(
        60,
        20,
        21,
        P,
        "p60_h2_prompt",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
    ),
    block(
        60,
        23,
        24,
        M,
        "p60_h3_farm_expenses",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
        parents=("p60_farm_aggregate",),
        parent_note=_FARM_PARENT,
        note="H3 prints the farm operating-expense component.",
    ),
    block(
        60,
        23,
        24,
        P,
        "p60_h3_prompt",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
    ),
    line(
        60,
        26,
        P,
        "p60_h4_prompt",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
    ),
    word(
        60,
        26,
        "net income from farming",
        FA,
        "p60_farm_aggregate",
        routes=(SECTION_H + ("p60_flow_h1_farmer",),),
        note="H4 prints the net farm income aggregate.",
    ),
    block(
        60,
        30,
        31,
        C,
        "p60_h5_business_interest",
        routes=(SECTION_H,),
        parents=("p60_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="H5 prints the business-ownership assignment field.",
    ),
    block(60, 30, 31, P, "p60_h5_prompt", routes=(SECTION_H,)),
    run(60, 33, 2, 4, F, "p60_flow_h5_no", routes=(SECTION_H,)),
    block(60, 37, 38, P, "p60_h6_prompt", routes=(SECTION_H,)),
    run(
        60,
        37,
        7,
        9,
        BA,
        "p60_business_aggregate",
        routes=(SECTION_H,),
        note="H6 prints the unincorporated-business aggregate.",
    ),
    block(
        60,
        37,
        38,
        C,
        "p60_h6_incorporation",
        routes=(SECTION_H,),
        parents=("p60_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="H6 prints the incorporation field.",
    ),
    line(60, 45, F, "p60_flow_h6_corporation_go_to_h8", routes=(SECTION_H,)),
    block(
        60,
        48,
        49,
        M,
        "p60_h7_business_share",
        routes=(SECTION_H,),
        parents=("p60_business_aggregate",),
        parent_note=_BUSINESS_PARENT,
        note="H7 prints the family share of total business income.",
    ),
    block(60, 48, 49, P, "p60_h7_prompt", routes=(SECTION_H,)),
    block(
        60,
        58,
        59,
        T,
        "p60_h8_role_total",
        routes=(SECTION_H,),
        note="H8 prints the head's 1977 wage-and-salary role total; the "
        "printed item identifier is scanned as HS and is retained verbatim.",
    ),
    block(60, 58, 59, P, "p60_h8_prompt", routes=(SECTION_H,)),
    word(60, 58, "HEAD", R, "p60_role_head_h8", routes=(SECTION_H,)),
)

# Page 64 - section H head supplementary earnings and sources H9-H19.
PAGE_64 = (
    line(
        64,
        2,
        M,
        "p64_h9_bonus_overtime_commission",
        routes=(SECTION_H,),
        parent_note=_NO_PARENT,
        note="H9 prints the bonus, overtime, and commission component; the "
        "printed how-much probe on the following line restates the same "
        "component and is not emitted as a second atom.",
    ),
    line(64, 2, P, "p64_h9_prompt", routes=(SECTION_H,)),
    run(64, 4, 3, 5, F, "p64_flow_h9_yes_go_to_h11", routes=(SECTION_H,)),
    word(64, 9, "HEAD", R, "p64_role_head_h11", routes=(SECTION_H,)),
    run(
        64,
        11,
        0,
        5,
        F,
        "p64_flow_h11_if_yes",
        routes=(SECTION_H,),
        note="Printed H11 grid condition governing the amount probe; the "
        "printed ASK and ENTER continuations are photographed onto the two "
        "following physical lines of the same column and are the "
        "consequent of this label rather than separate branches.",
    ),
    run(
        64,
        11,
        6,
        10,
        M,
        "p64_h11a_professional_practice",
        routes=(SECTION_H,),
        parent_note=_NO_PARENT,
        note="H11a prints the professional-practice or trade component. "
        + _COLUMN_NOTE,
    ),
    run(
        64,
        13,
        0,
        4,
        M,
        "p64_h11b_farming_or_market_gardening",
        routes=(SECTION_H,),
        parent_note=_NO_PARENT,
        note="H11b prints the farming or market-gardening component for a "
        "head whose main source of income is not farming. " + _COLUMN_NOTE,
    ),
    run(
        64,
        15,
        0,
        2,
        M,
        "p64_h11b_roomers_or_boarders",
        routes=(SECTION_H,),
        parent_note=_NO_PARENT,
        note="H11b prints the roomers-or-boarders component on a separate "
        "printed line of the same item. " + _COLUMN_NOTE,
    ),
    run(
        64,
        16,
        0,
        6,
        F,
        "p64_flow_h11_if_no",
        routes=(SECTION_H,),
        note="Printed H11 grid condition for an item answered no.",
    ),
    run(64, 27, 7, 9, F, "p64_flow_h12_no_such_income", routes=(SECTION_H,)),
    run(64, 36, 2, 4, F, "p64_flow_h13_no", routes=(SECTION_H,)),
    run(64, 54, 4, 6, F, "p64_flow_h16_no", routes=(SECTION_H,)),
    line(
        64,
        59,
        F,
        "p64_flow_h18_turn_h20",
        routes=(SECTION_H,),
        note="H18 checkpoint routing atom; the printed target item name "
        "prints on a separate physical line of the scanned answer column "
        "and is not spanned.",
    ),
)

# Page 68 - section H transfer items and the wife income block H20-H31.
PAGE_68 = (
    run(68, 15, 3, 5, F, "p68_flow_h21_yes_go_to_h23", routes=(SECTION_H,)),
    line(
        68,
        19,
        F,
        "p68_flow_h23_wife_in_fu",
        routes=(SECTION_H,),
        note="H23 interviewer checkpoint; the scan destroyed its printed "
        "answer boxes, so the retained branch label is the printed "
        "checkpoint line itself, which carries the complete printed "
        "condition governing H24-H31.",
    ),
    line(
        68,
        24,
        C,
        "p68_h24_wife_income",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
        parent_note=_NO_PARENT,
        note="H24 prints the wife's 1977 income assignment field, which "
        "gates the printed source and amount fields below it.",
    ),
    line(
        68,
        24,
        P,
        "p68_h24_prompt",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
    word(
        68,
        24,
        "(wife/friend)",
        R,
        "p68_role_wife_h24",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
    run(
        68,
        26,
        4,
        8,
        F,
        "p68_flow_h24_no",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
    line(
        68,
        28,
        C,
        "p68_h25_income_source",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
        parent_note=_NO_PARENT,
        note="H25 prints the wife's remuneration-source field with its "
        "printed SOURCE answer columns.",
    ),
    line(
        68,
        28,
        P,
        "p68_h25_prompt",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
    line(
        68,
        32,
        T,
        "p68_h26_role_total",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
        note="H26 prints the wife's before-deductions 1977 income role "
        "total, whose printed source is classified at H25.",
    ),
    line(
        68,
        32,
        P,
        "p68_h26_prompt",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
    run(
        68,
        42,
        1,
        3,
        F,
        "p68_flow_h28_go_to_h29",
        routes=(SECTION_H + ("p68_flow_h23_wife_in_fu",),),
    ),
)


SECTION_J = ("p84_flow_section_j",)
SECTION_K = ("p86_flow_section_k",)
_EXTRA_EARNER = (
    "No printed parent job or aggregate on the extra-earner grid; the "
    "printed columns are keyed to a listed person rather than to a printed "
    "job, so parenting is deferred to global assembly."
)
_REPRINT_COLUMN = (
    "Printed answer-column field label on the reprinted extra-earner grid; "
    "the grid prints its question stems only on the preceding screen, so "
    "this span carries no printed prompt.  No local alias binds this "
    "printing to the first printing."
)

# Page 72 - section H extra-earner checkpoint, listing, and items H32-H45.
PAGE_72 = (
    run(
        72,
        4,
        2,
        6,
        F,
        "p72_flow_h32_at_least_one",
        routes=(SECTION_H,),
        note="H32 interviewer checkpoint branch 1: at least one listed "
        "person other than the current head or wife is over 13.",
    ),
    run(
        72,
        4,
        7,
        9,
        F,
        "p72_flow_h32_none",
        routes=(SECTION_H,),
        note="H32 interviewer checkpoint branch 2: no such person is over "
        "13.",
    ),
    run(72, 5, 8, 12, F, "p72_flow_h32_turn_h46", routes=(SECTION_H,)),
    block(
        72,
        7,
        8,
        A,
        "p72_repeat_list_all_persons",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="H33 prints the listing instruction that makes the extra-"
        "earner grid repeat once per listed person.",
    ),
    run(
        72,
        11,
        0,
        9,
        C,
        "p72_h34_extra_earner_income",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H34 prints the extra-earner income assignment field; the "
        "trailing printed coder box on the same line is not spanned.",
    ),
    run(
        72,
        11,
        0,
        9,
        P,
        "p72_h34_prompt",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
    ),
    line(
        72,
        12,
        A,
        "p72_repeat_h34_next_person",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed instruction to re-administer H34 for the next listed "
        "person; the printed target word PERSON LISTED prints on the "
        "following physical line and is not spanned.",
    ),
    line(
        72,
        15,
        M,
        "p72_h35_extra_earner_amount",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H35 prints the extra-earner 1977 amount component, whose "
        "printed source is classified at H36.",
    ),
    line(
        72,
        15,
        P,
        "p72_h35_prompt",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
    ),
    run(
        72,
        17,
        0,
        10,
        C,
        "p72_h36_income_source",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H36 prints the extra-earner remuneration-source field; the "
        "printed continuation and SOURCE column label print on the "
        "following physical line and are not spanned.",
    ),
    run(
        72,
        17,
        0,
        10,
        P,
        "p72_h36_prompt",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
    ),
    line(
        72,
        22,
        F,
        "p72_flow_h36_wages_or_business",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        note="Printed condition that governs the extra-earner work items "
        "H37-H42.",
    ),
    line(
        72,
        24,
        C,
        "p72_h37_occupation",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
        parent_note=_EXTRA_EARNER,
        note="H37 prints the extra-earner occupation field.",
    ),
    line(
        72,
        24,
        P,
        "p72_h37_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    line(
        72,
        27,
        C,
        "p72_h38_weeks_worked",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
        parent_note=_EXTRA_EARNER,
    ),
    line(
        72,
        27,
        P,
        "p72_h38_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    line(
        72,
        30,
        C,
        "p72_h39_hours_per_week",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
        parent_note=_EXTRA_EARNER,
    ),
    line(
        72,
        30,
        P,
        "p72_h39_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    run(
        72,
        33,
        2,
        6,
        F,
        "p72_flow_h40_if_dont_know",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    run(
        72,
        33,
        7,
        11,
        C,
        "p72_h40_more_than_half_time",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
                "p72_flow_h40_if_dont_know",
            ),
        ),
        parent_note=_EXTRA_EARNER,
        note="H40 prints the half-time exposure fallback field, "
        "administered only under the printed don't-know condition.",
    ),
    run(
        72,
        33,
        7,
        11,
        P,
        "p72_h40_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
                "p72_flow_h40_if_dont_know",
            ),
        ),
    ),
    block(
        72,
        35,
        36,
        C,
        "p72_h41_missed_work",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
        parent_note=_EXTRA_EARNER,
        note="H41 prints the extra-earner unemployment and strike exposure "
        "field.",
    ),
    block(
        72,
        35,
        36,
        P,
        "p72_h41_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    run(
        72,
        38,
        2,
        4,
        F,
        "p72_flow_h41_no",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    line(
        72,
        40,
        C,
        "p72_h42_amount",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
        parent_note=_EXTRA_EARNER,
        note="H42 prints the missed-work amount; the printed item "
        "identifier is scanned as H4.7. and is retained verbatim.",
    ),
    line(
        72,
        40,
        P,
        "p72_h42_prompt",
        routes=(
            SECTION_H
            + (
                "p72_flow_h32_at_least_one",
                "p72_flow_h36_wages_or_business",
            ),
        ),
    ),
    line(
        72,
        45,
        A,
        "p72_repeat_h34_next_person_second",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Second printed instruction to re-administer H34 for the next "
        "listed person, printed beside the H43 answer column.",
    ),
)

# Page 74 - the reprinted section H extra-earner grid.
PAGE_74 = (
    line(
        74,
        11,
        A,
        "p74_repeat_h34_next_person",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed instruction on the reprinted grid to re-administer "
        "H34 for the next listed person; the printed item identifier is "
        "scanned as ll34 and is retained verbatim.",
    ),
    run(
        74,
        19,
        0,
        2,
        M,
        "p74_h35_amount_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H35 amount column 1 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        19,
        3,
        5,
        M,
        "p74_h35_amount_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H35 amount column 2 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        19,
        6,
        8,
        M,
        "p74_h35_amount_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H35 amount column 3 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        22,
        0,
        0,
        C,
        "p74_h36_source_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H36 source column 1 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        22,
        1,
        1,
        C,
        "p74_h36_source_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H36 source column 2 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        22,
        2,
        2,
        C,
        "p74_h36_source_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H36 source column 3 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        26,
        0,
        0,
        C,
        "p74_h37_occupation_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H37 occupation column 1 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        26,
        1,
        1,
        C,
        "p74_h37_occupation_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H37 occupation column 2 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        26,
        2,
        2,
        C,
        "p74_h37_occupation_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H37 occupation column 3 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        29,
        0,
        0,
        C,
        "p74_h38_weeks_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H38 weeks column 1 on the reprinted grid; the printed word "
        "WEEKS is scanned as 1.JEEKS and is retained verbatim. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        29,
        1,
        1,
        C,
        "p74_h38_weeks_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H38 weeks column 2 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        29,
        2,
        2,
        C,
        "p74_h38_weeks_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H38 weeks column 3 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        32,
        0,
        0,
        C,
        "p74_h39_hours_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H39 hours column 1 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        32,
        1,
        1,
        C,
        "p74_h39_hours_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H39 hours column 2 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        32,
        2,
        2,
        C,
        "p74_h39_hours_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H39 hours column 3 on the reprinted grid. " + _REPRINT_COLUMN,
    ),
    run(
        74,
        47,
        0,
        2,
        C,
        "p74_h42_amount_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H42 missed-work exposure column 1 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        47,
        3,
        5,
        C,
        "p74_h42_amount_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H42 missed-work exposure column 2 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        47,
        6,
        8,
        C,
        "p74_h42_amount_column_3",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        parent_note=_EXTRA_EARNER,
        note="H42 missed-work exposure column 3 on the reprinted grid. "
        + _REPRINT_COLUMN,
    ),
    run(
        74,
        50,
        0,
        3,
        A,
        "p74_repeat_h34_next_person_column_1",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed instruction in reprinted column 1 to re-administer "
        "H34 for the next listed person.",
    ),
    run(
        74,
        50,
        4,
        7,
        A,
        "p74_repeat_h34_next_person_column_2",
        routes=(SECTION_H + ("p72_flow_h32_at_least_one",),),
        relation="explicit_repeat_instruction",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
        note="Printed instruction in reprinted column 2 to re-administer "
        "H34 for the next listed person.",
    ),
)

# Page 84 - section J entry and the new-wife lifetime work history J1-J12.
PAGE_84 = (
    line(
        84,
        4,
        F,
        "p84_flow_section_j",
        note="Printed section J header conditions the new-wife schedule.",
    ),
    run(
        84,
        13,
        0,
        2,
        F,
        "p84_flow_j1_new_wife_or_friend",
        routes=(SECTION_J,),
        note="J1 interviewer checkpoint branch 1: the FU has a new wife or "
        "permanent friend; the label's head bytes are photographed onto "
        "separate physical lines and only the surviving tail is spanned.",
    ),
    run(
        84,
        13,
        3,
        7,
        F,
        "p84_flow_j1_female_head",
        routes=(SECTION_J,),
        note="J1 interviewer checkpoint branch 2: the FU has a female head.",
    ),
    line(84, 17, F, "p84_flow_j1_turn_section_k", routes=(SECTION_J,)),
    run(
        84,
        31,
        6,
        8,
        F,
        "p84_flow_j3_no",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    line(
        84,
        37,
        F,
        "p84_flow_j6_no",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    run(
        84,
        42,
        0,
        2,
        F,
        "p84_flow_j7_go_to_j8",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    run(
        84,
        42,
        3,
        5,
        F,
        "p84_flow_j7_advanced_go_to_j8",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    line(
        84,
        48,
        C,
        "p84_j10_lifetime_work_years",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
        parent_note=_NO_PARENT,
        note="J10 prints the wife's lifetime years-worked-for-money "
        "exposure field.",
    ),
    line(
        84,
        48,
        P,
        "p84_j10_prompt",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    word(
        84,
        48,
        "(wife/friend)",
        R,
        "p84_role_wife_j10",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    run(
        84,
        51,
        7,
        11,
        F,
        "p84_flow_j10_none",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    line(
        84,
        53,
        C,
        "p84_j11_full_time_years",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
        parent_note=_NO_PARENT,
        note="J11 prints the wife's full-time years exposure field.",
    ),
    line(
        84,
        53,
        P,
        "p84_j11_prompt",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    run(
        84,
        55,
        5,
        9,
        F,
        "p84_flow_j11_all",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    line(
        84,
        57,
        C,
        "p84_j12_part_time_share",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
        parent_note=_NO_PARENT,
        note="J12 prints the wife's part-time work-share exposure field; "
        "the printed item identifier is scanned as ~12 and the printed "
        "closing word Hork prints on a later physical line that is not "
        "spanned.",
    ),
    line(
        84,
        57,
        P,
        "p84_j12_prompt",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
    line(
        84,
        65,
        F,
        "p84_flow_j12_turn_section_k",
        routes=(SECTION_J + ("p84_flow_j1_new_wife_or_friend",),),
    ),
)

# Page 86 - section K entry and the new-head first-job items K1-K10.
PAGE_86 = (
    line(
        86,
        1,
        F,
        "p86_flow_section_k",
        note="Printed section K header conditions the new-head schedule.",
    ),
    run(
        86,
        7,
        0,
        7,
        F,
        "p86_flow_k1_new_head",
        routes=(SECTION_K,),
        note="K1 interviewer checkpoint branch 1: the FU has a new head "
        "this year.",
    ),
    run(
        86,
        7,
        8,
        17,
        F,
        "p86_flow_k1_same_head",
        routes=(SECTION_K,),
        note="K1 interviewer checkpoint branch 2: the FU has the same head "
        "as in 1977.",
    ),
    line(86, 8, F, "p86_flow_k1_turn_cover_sheet", routes=(SECTION_K,)),
    run(
        86,
        30,
        6,
        9,
        J,
        "p86_job_first_full_time",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
        note="K4 prints the head's first full-time regular job noun.",
    ),
    word(
        86,
        30,
        "HEAD",
        R,
        "p86_role_head_k4",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    line(
        86,
        30,
        C,
        "p86_k4_first_job_occupation",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
        parents=("p86_job_first_full_time",),
        parent_note="Parent is the printed first full-time regular job "
        "anchor named in the same question block.",
        note="K4 prints the occupation of the head's first full-time "
        "regular job.",
    ),
    line(
        86,
        30,
        P,
        "p86_k4_prompt",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        86,
        33,
        0,
        2,
        F,
        "p86_flow_k4_never_worked",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        86,
        48,
        1,
        3,
        F,
        "p86_flow_k7_go_to_k9",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        86,
        58,
        4,
        8,
        F,
        "p86_flow_k9_no",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
)

# Page 90 - section K new-head lifetime work-history items K25-K27.
PAGE_90 = (
    line(
        90,
        1,
        C,
        "p90_k25_lifetime_work_years",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
        parent_note=_NO_PARENT,
        note="K25 prints the head's lifetime years-worked exposure field.",
    ),
    line(
        90,
        1,
        P,
        "p90_k25_prompt",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    word(
        90,
        1,
        "HEAD",
        R,
        "p90_role_head_k25",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        90,
        3,
        4,
        6,
        F,
        "p90_flow_k25_none",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    line(
        90,
        6,
        C,
        "p90_k26_full_time_years",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
        parent_note=_NO_PARENT,
        note="K26 prints the head's full-time years exposure field.",
    ),
    line(
        90,
        6,
        P,
        "p90_k26_prompt",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        90,
        10,
        4,
        6,
        F,
        "p90_flow_k26_all",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    line(
        90,
        13,
        C,
        "p90_k27_part_time_share",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
        parent_note=_NO_PARENT,
        note="K27 prints the head's part-time work-share exposure field.",
    ),
    line(
        90,
        13,
        P,
        "p90_k27_prompt",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        90,
        36,
        0,
        2,
        F,
        "p90_flow_k29_go_to_k31",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        90,
        36,
        3,
        5,
        F,
        "p90_flow_k32_go_to_k37",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
    run(
        90,
        45,
        0,
        2,
        F,
        "p90_flow_k33_go_to_k37",
        routes=(SECTION_K + ("p86_flow_k1_new_head",),),
    ),
)


REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_12,
    *PAGE_16,
    *PAGE_18,
    *PAGE_20,
    *PAGE_22,
    *PAGE_26,
    *PAGE_28,
    *PAGE_32,
    *PAGE_34,
    *PAGE_36,
    *PAGE_38,
    *PAGE_40,
    *PAGE_42,
    *PAGE_46,
    *PAGE_48,
    *PAGE_50,
    *PAGE_60,
    *PAGE_64,
    *PAGE_68,
    *PAGE_72,
    *PAGE_74,
    *PAGE_84,
    *PAGE_86,
    *PAGE_90,
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
                "all_95_pages_including_empty_occurrence_pages"
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
        f"document 21 source review: {len(review['occurrence_specs'])} "
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
