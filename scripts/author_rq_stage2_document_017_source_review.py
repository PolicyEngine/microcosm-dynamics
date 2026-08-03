#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 17.

``fam1976_QxQs.pdf`` is a 101-page scan that binds two instruments and their
question-by-question interviewer objectives into one file: pages 1-75 are the
1976 heads questionnaire and pages 76-101 the wives questionnaire.  Inside each
instrument the printed screens and their facing objectives sheets alternate,
and the two are told apart by their printed page marker: an instrument screen
carries a bare arabic screen number and an objectives sheet carries the same
number between hyphens (``-5-``), sometimes with a lettered continuation
(``-5a-``, ``-24a-``).  All 101 pages were read from the authenticated Poppler
text before this file was written, and the stage-1 candidate artifact is never
opened here; the sealed annotation builder joins candidates only after these
reviewer rows exist.

Reviewer scope decisions recorded by this file:

* Anchors, field-purpose prompts, and flow labels are emitted only on printed
  *instrument* screens inside the retained employment, work-income, and
  lifetime-work-history regions.  An objectives sheet is interviewer
  commentary keyed to a question; it restates worklike vocabulary but prints
  no field, so it carries no anchor, prompt, or flow occurrence.
* One class of objectives text is retained, and it is the only stated
  departure from the sibling ``fam1980_QxQs`` shard's instrument-only rule: a
  printed *cross-reference or repeat instruction* that names printed items in
  the retained R_Q domain.  Section 19's catalog and alias law admits alias
  evidence only through ``repeat_or_alias_instruction`` occurrences, and in
  this document that evidence is printed almost entirely on objectives
  sheets.  Pages 94 and 95 are the extreme case: the wives employment,
  job-search, and out-of-labour-force screens were never printed at all
  ("We have not printed these sections for the wives questionnaires in order
  to save paper"), and the manual substitutes a directive to administer them
  from the heads pages.  Discarding that as commentary would delete the
  document's only printed evidence for the wife-role employment schedule.
  Objectives prose that merely restates an objective, defines a term, or
  gives coding examples is still rejected.
* Cover, children, transportation, housing, residential-mobility, commuting,
  housework, food and food-stamp, other-family-member income, transfer and
  asset income, medical, dependent-support, sibling, growing-up, schooling,
  religion, child-care, fertility, and by-observation regions contribute no
  occurrence merely because nearby prose contains worklike words.
* A retained ``context_anchor`` must print a field that maps to a ratified
  section-19 field purpose (assignment, occupation, industry, employee/self,
  government level, incorporation, job identifier, reporting unit,
  month/exposure, or public-retirement-system participation).  Supervision
  and supervised-headcount, labour-union coverage and membership, commuting
  time/distance/mode, training-requirement and time-to-qualify, skill
  under-use, counterfactual labour-supply preference, job-search effort,
  job-finding-chance and retirement intention, residential-mobility
  willingness, work-limiting health, and schooling fields are printed
  work-adjacent questions that map to no such purpose and are rejected.
* A retained ``job_anchor`` establishes a distinct printed job for the role by
  its printed job noun, and only where that noun is the establishing parent
  of a retained field on the same screen.  A later back-reference on the same
  screen to a job that screen already established ("this job", "your present
  job", "that job") is rejected rather than promoted to a second job or an
  inferred alias, and so is a printed job noun that parents no retained
  field: D22's "current job" sits in a rejected union item, F8's and E31's
  "last job" in rejected commuting items, and D64's "main job" refers back to
  a job established on an earlier screen.  Emitting those would hand global
  assembly job nodes that no retained field parents.  Two printed job nouns
  on different screens stay distinct; whether the 1976 "present position",
  "main job", and "present employer" resolve to one node is a global-assembly
  question and is not decided here.
* Section H prints the only aggregates.  H4's "net income from farming" is
  the farm aggregate and H6's "unincorporated business" is the business
  aggregate; H2, H3, and H7 are their printed component amounts.  Section D's
  incorporation items D16 and D19 print a property of the head's
  self-employment *job* rather than a business income aggregate, so they are
  retained as incorporation context and emit no aggregate.
* H23 is the wife's printed total-income question and is the document's only
  ``role_total_anchor``.  H11's lettered rows are split by subject matter:
  a) professional practice or trade and b) farming or market gardening,
  roomers or boarders are printed remuneration components, while c) through
  m) are transfer, asset, pension, and outside-help receipts that establish
  no remuneration component of any job.  Row b prints two distinct
  remuneration subject matters and each printed label is retained, because
  dropping either would delete a printed component label from the catalog
  the global stage assembles.
* A printed remuneration component is a *labelled amount row* -- printed
  text that labels its own money box.  An enumeration of sources inside one
  coded answer field is one component, not several: H24's "wages, salary, a
  business, or what?" is a coded ``(SOURCE)`` field whose amount is asked
  separately at H25, so the wife's income block prints one component (H25)
  and not three, while each of H11's lettered rows labels its own
  ``$ ___ per ___`` box and is therefore its own component.
* A screen is retained if and only if it prints at least one retained field.
  On a retained screen every legible printed routing directive and printed
  conditional label is also retained; on a screen that prints no retained
  field nothing is retained, including its routing directives.
* An occurrence's applicable path set is the ancestry of the printed block in
  which it is administered: the section-header branch, extended by each
  printed conditional label that encloses it.  A printed forward routing atom
  is itself a branch label, but it does not re-parent the screen it jumps to,
  because that screen is administered identically on fall-through.
* OCR-destroyed answer labels and routing fragments are never reconstructed.
  A routing atom is retained only where the printed bytes still separate its
  directive verb from its target, so the fused ``GOTOD55`` and ``GOTOH8``
  scans and the directive/target pairs split across two physical lines are
  rejected while ``(GO TO D41)`` and ``(TURN TO PAGE 9, D51)`` are retained.
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
import build_rq_stage2_document_017_annotation as annotation  # noqa: E402

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
PAGE_COUNT = 101


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


_OBJECTIVES_XREF = (
    "Question-by-question interviewer objectives for {}; the objective prose "
    "itself prints no field and retains no anchor, prompt, or flow "
    "occurrence, but {} is an explicit printed cross-reference between named "
    "items in the retained R_Q domain and is retained as alias evidence."
)

PAGE_NOTES: dict[int, str] = {
    1: _INSTRUMENT_OUT.format(
        "the heads face sheet, office-use box, and section A schooling items "
        "A1-A4"
    ),
    2: _OBJECTIVES.format(
        "the heads questionnaire reminder and section A items A2-A4"
    ),
    3: _INSTRUMENT_OUT.format("section B transportation items B1-B5"),
    4: _OBJECTIVES.format("section B items B1-B5"),
    5: _INSTRUMENT_OUT.format(
        "section C housing, value, and mortgage items C1-C11"
    ),
    6: _OBJECTIVES.format("section C items C1-C11"),
    7: _INSTRUMENT_OUT.format(
        "section C rent and residential-mobility items C12-C22"
    ),
    8: _OBJECTIVES.format("section C items C12-C22"),
    9: _INSTRUMENT_IN.format(
        "the section D header and head employment items D1-D4"
    ),
    10: _OBJECTIVES.format("the section D header and items D1-D4"),
    11: _OBJECTIVES.format(
        "items D2-D4, continued on the lettered -5a- objectives sheet"
    ),
    12: _INSTRUMENT_IN.format("head employment items D5-D24"),
    13: _OBJECTIVES.format("items D5-D21 and D24"),
    14: _INSTRUMENT_IN.format("head job-training and tenure items D25-D37"),
    15: _OBJECTIVES.format("items D25-D37"),
    16: _INSTRUMENT_IN.format("head 1975 work-time items D38-D50"),
    17: _OBJECTIVES.format("items D38-D50"),
    18: _INSTRUMENT_IN.format(
        "head work-time, pay-rate, and pension-coverage items D51-D63"
    ),
    19: _OBJECTIVES.format("items D51-D63"),
    20: _INSTRUMENT_IN.format("head extra-job items D64-D75"),
    21: _OBJECTIVES_XREF.format(
        "items D64-D75",
        'the D65-D66 objective "See D2, D3; the same instructions apply '
        'here."',
    ),
    22: _INSTRUMENT_NONE.format(
        "head items D76-D83",
        "a commuting time, distance, or mode field, a job-finding-chance "
        "assessment, or a retirement intention, none of which maps to a "
        "ratified section-19 field purpose",
    ),
    23: _OBJECTIVES.format("items D76-D83"),
    24: _INSTRUMENT_NONE.format(
        "head items D84-D88",
        "a residential-mobility willingness, a job-taking limitation, or a "
        "counterfactual labour-supply preference, none of which maps to a "
        "ratified section-19 field purpose",
    ),
    25: _OBJECTIVES.format("items D84-D88"),
    26: _INSTRUMENT_IN.format(
        "the section E header and head job-search and last-job items E1-E15"
    ),
    27: _OBJECTIVES_XREF.format(
        "the section E header and items E1-E15",
        'the E1, E12, and E13 objectives "See the objectives for D2, D3", '
        '"See D2, D3", and "See D4"',
    ),
    28: _INSTRUMENT_IN.format("head 1975 work-time items E16-E28"),
    29: _OBJECTIVES_XREF.format(
        "items E17-E28",
        'the printed objectives "See D44-45", "See D38-42", and '
        '"See D48-D50"',
    ),
    30: _INSTRUMENT_IN.format("head work-time and commuting items E29-E34"),
    31: _OBJECTIVES.format("items E29-E34"),
    32: _INSTRUMENT_IN.format(
        "the section F header and out-of-labour-force work items F1-F12"
    ),
    33: _OBJECTIVES_XREF.format(
        "the section F header and items F1-F11",
        'the F4 and F5 objectives "See D2-D3" and "See D4"',
    ),
    34: _INSTRUMENT_IN.format("head sought-job items F13-F27"),
    35: _OBJECTIVES.format("items F13, F16, F21, and F26"),
    36: _INSTRUMENT_NONE.format(
        "head items F28-F30",
        "a job-search effort or residential-mobility willingness field, "
        "neither of which maps to a ratified section-19 field purpose",
    ),
    37: _OBJECTIVES.format("items F29-F30"),
    38: _INSTRUMENT_IN.format(
        "the section G header and wife employment items G1-G6"
    ),
    39: _OBJECTIVES_XREF.format(
        "the section G header and items G1-G6",
        'the G2-G4 objective "See Section D, Qs. D2, D3, D4 for objectives"',
    ),
    40: _INSTRUMENT_OUT.format("section G housework items G7-G12"),
    41: _OBJECTIVES.format("items G7-G12"),
    42: _INSTRUMENT_OUT.format("section G food and food-stamp items G13-G26"),
    43: _OBJECTIVES.format("items G13-G26"),
    44: _INSTRUMENT_IN.format(
        "the section H header and family work-income items H1-H8"
    ),
    45: _OBJECTIVES_XREF.format(
        "the section H header and items H1-H8",
        'the H1 objective "Farm income for nonfarmers should be picked up in '
        'Hllb."',
    ),
    46: _OBJECTIVES_XREF.format(
        "item H8, continued on the lettered -23a- objectives sheet",
        'the printed instruction "Make sure if an amount is given for both '
        'H7 and H8 that it is not the same figure recorded twice"',
    ),
    47: _INSTRUMENT_IN.format("head other-income items H9-H13"),
    48: _OBJECTIVES.format("items H9-H11 and the S.S.I. program note"),
    49: _OBJECTIVES_XREF.format(
        "items H11a-H11d, continued on the lettered -24a- objectives sheet",
        'the H11b objective "his income should come in H2 - H4 and not be '
        'duplicated here"',
    ),
    50: _OBJECTIVES.format(
        "items H11d-H11g, continued on the lettered -24b- objectives sheet"
    ),
    51: _OBJECTIVES.format(
        "items H11g-H13, continued on the lettered -24c- objectives sheet"
    ),
    52: _INSTRUMENT_IN.format(
        "head welfare and Social Security checkpoints H14-H21 and the wife "
        "income items H22-H25"
    ),
    53: _OBJECTIVES.format("items H14-H25"),
    54: _INSTRUMENT_OUT.format(
        "the other-family-member income grid H26-H38, whose listed persons "
        "are neither the head nor the spouse role"
    ),
    55: _OBJECTIVES.format("the other-family-member grid items H26-H38"),
    56: _INSTRUMENT_OUT.format(
        "the other-family-member income grid H27-H38, printed a second time "
        "as a continuation sheet, whose listed persons are neither the head "
        "nor the spouse role"
    ),
    57: _OBJECTIVES.format("the repeated other-family-member grid"),
    58: _INSTRUMENT_OUT.format(
        "other-income, lump-sum receipt, outside-dependent support, "
        "labour-union membership, and work-limiting health items H39-H52"
    ),
    59: _OBJECTIVES.format("items H41-H52"),
    60: _INSTRUMENT_IN.format(
        "the section J header and head lifetime work-history items J1-J9"
    ),
    61: _OBJECTIVES.format("the section J header and items J3-J9"),
    62: _INSTRUMENT_IN.format("head return-to-work items J10-J17"),
    63: _OBJECTIVES.format("items J11-J17"),
    64: _INSTRUMENT_IN.format(
        "the section K header and new-head first-job items K1-K10"
    ),
    65: _OBJECTIVES_XREF.format(
        "the section K header and items K1-K10",
        'the K4 objective "See D2, D3; the same instructions apply here."',
    ),
    66: _INSTRUMENT_NONE.format(
        "new-head items K11-K24",
        "a sibling, growing-up, residential-mobility, parental-education, or "
        "veteran-status field, none of which maps to a ratified section-19 "
        "field purpose",
    ),
    67: _OBJECTIVES.format("items K11-K24"),
    68: _INSTRUMENT_OUT.format(
        "new-head schooling and religious-preference items K25-K36"
    ),
    69: _OBJECTIVES.format("items K25-K36"),
    70: _INSTRUMENT_OUT.format(
        "the section L header and new-wife schooling items L1-L7"
    ),
    71: _OBJECTIVES.format("the section L header and items L1-L5"),
    72: _INSTRUMENT_OUT.format(
        "the section M header and by-observation items M1-M8"
    ),
    73: _OBJECTIVES.format("the section M header and items M1-M2"),
    74: _INSTRUMENT_OUT.format("the heads thumbnail sketch sheet"),
    75: _OBJECTIVES.format("the heads thumbnail sketch sheet"),
    76: _INSTRUMENT_OUT.format(
        "the wives face sheet, office-use box, and section A background "
        "items A1-A3, whose printed occupations are the respondent's parents "
        "rather than the head or the spouse role"
    ),
    77: _OBJECTIVES.format(
        "the wives questionnaire reminder and section A items A1-A3"
    ),
    78: _INSTRUMENT_OUT.format(
        "section A sibling, growing-up, and parental-education items A4-A12"
    ),
    79: _OBJECTIVES.format("section A items A4-A12"),
    80: _INSTRUMENT_OUT.format(
        "section A schooling, marriage, religion, and work-limiting health "
        "items A13-A26"
    ),
    81: _OBJECTIVES.format("section A items A13-A26"),
    82: _INSTRUMENT_OUT.format(
        "the section B header and wife housework and child-presence items "
        "B1-B8"
    ),
    83: _OBJECTIVES.format("the section B header and items B1-B8"),
    84: _INSTRUMENT_IN.format(
        "wife employment item B9 and child-care items B10-B19"
    ),
    85: _OBJECTIVES.format("items B10-B19"),
    86: _INSTRUMENT_OUT.format(
        "counterfactual child-care arrangement items B20-B26"
    ),
    87: _OBJECTIVES.format("items B20-B26"),
    88: _INSTRUMENT_IN.format(
        "the section C header, child items C1-C4, and wife lifetime "
        "work-participation items C5-C14"
    ),
    89: _OBJECTIVES.format("the section C header and items C1-C14"),
    90: _INSTRUMENT_NONE.format(
        "wife items C15-C20",
        "a fertility expectation or a future-job plan, neither of which maps "
        "to a ratified section-19 field purpose",
    ),
    91: _OBJECTIVES.format("items C16-C20"),
    92: _INSTRUMENT_OUT.format(
        "husband-attitude items C21-C22, the C23 fertility checkpoint, and "
        "the C24 children's-schooling item"
    ),
    93: _OBJECTIVES.format("item C24"),
    94: _OBJECTIVES_XREF.format(
        "the wives sections D, E, and F, whose instrument screens this "
        "manual never prints",
        "the printed directive to administer them from the heads "
        "question-by-question objectives on pages 5-18",
    ),
    95: _OBJECTIVES.format(
        "the wives section D, E, and F headers, printed without their "
        "instrument screens"
    ),
    96: _INSTRUMENT_IN.format(
        "the wives section G header and lifetime work-history items G1-G11"
    ),
    97: _OBJECTIVES_XREF.format(
        "the wives section G header and items G3-G11",
        'the G4 objective "See D2-D3."',
    ),
    98: _INSTRUMENT_IN.format("wife return-to-work items G12-G20"),
    99: _OBJECTIVES.format("items G13-G20"),
    100: _INSTRUMENT_OUT.format("the wives thumbnail sketch sheet"),
    101: _OBJECTIVES.format("the wives thumbnail sketch sheet"),
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

XREF = "explicit_cross_reference"

# Printed section headers open the document's root branches; a printed
# conditional label inside a section extends its ancestry.
SEC_D = ("p9_flow_section_d",)
D_EMPLOYEE = SEC_D + ("p12_flow_d5_someone_else",)
D_BOTH = SEC_D + ("p12_flow_d5_both",)
D_SHORT_TENURE = SEC_D + ("p14_flow_d32_less_than_one_year",)
D_PAID_HOURLY = SEC_D + ("p18_flow_d55_paid_by_hour",)
SEC_E = ("p26_flow_section_e",)
SEC_F = ("p32_flow_section_f",)
F_WANTS_JOB = SEC_F + ("p34_flow_f15_yes_thinking",)
SEC_G = ("p38_flow_section_g",)
SEC_H = ("p44_flow_section_h",)
H_FARMER = SEC_H + ("p44_flow_h1_farmer",)
H_UNINCORPORATED = SEC_H + ("p44_flow_h6_unincorporated",)
H_BOTH_KINDS = SEC_H + ("p44_flow_h6_both",)
SEC_J = ("p60_flow_section_j",)
J_ONE_PERIOD = SEC_J + ("p60_flow_j5_one_period",)
J_SEVERAL_PERIODS = SEC_J + ("p60_flow_j5_several_periods",)
SEC_K = ("p64_flow_section_k",)
K_NEW_HEAD = SEC_K + ("p64_flow_k1_new_head",)
SEC_CW = ("p88_flow_section_c_wives",)
SEC_GW = ("p96_flow_section_g_wives",)
GW_ONE_PERIOD = SEC_GW + ("p96_flow_g7_one_period",)
GW_SEVERAL_PERIODS = SEC_GW + ("p96_flow_g7_several_periods",)

_WORKTIME_D = "Prints a 1975 work-time exposure field for the head's main job."
_WORKTIME_E = "Prints a 1975 work-time exposure field for the head's last job."
_MAIN_JOB_PARENT = (
    "Parent job is the printed main-job noun on this screen, which governs "
    "the screen's work-time fields."
)
_EXTRA_JOB_PARENT = "Parent job is the printed extra-job noun on this screen."
_SOUGHT_JOB_PARENT = (
    "Parent job is the printed sought-job noun on this screen."
)
_LAST_JOB_PARENT = "Parent job is the printed last-job noun on this screen."
_FARM_PARENT = (
    "Parent aggregate is the printed net-farm-income anchor on this screen."
)
_BUSINESS_PARENT = (
    "Parent aggregate is the printed unincorporated-business anchor on this "
    "screen."
)

# Page 9 - section D entry and head employment items D1-D4.
PAGE_9 = (
    tail(
        9,
        3,
        "SECTION D:",
        F,
        "p9_flow_section_d",
        note="Printed section D header opening the head employment schedule "
        "selected at D1.",
    ),
    word(9, 6, "HEAD", R, "p9_role_head_d1", routes=(SEC_D,)),
    block(
        9,
        6,
        7,
        C,
        "p9_d1_assignment",
        routes=(SEC_D,),
        note="D1 prints the head labour-force assignment field that selects "
        "the D, E, or F schedule.",
    ),
    block(9, 6, 7, P, "p9_d1_prompt", routes=(SEC_D,)),
    line(
        9,
        28,
        C,
        "p9_d2_occupation",
        routes=(SEC_D,),
        note="D2 prints the head main-occupation field.",
    ),
    line(9, 28, P, "p9_d2_prompt", routes=(SEC_D,)),
    line(9, 33, P, "p9_d3_prompt", routes=(SEC_D,)),
    line(
        9,
        38,
        C,
        "p9_d4_industry",
        routes=(SEC_D,),
        note="D4 prints the kind-of-business industry field.",
    ),
    line(9, 38, P, "p9_d4_prompt", routes=(SEC_D,)),
)

# Page 12 - head employer, self-employment, and tenure items D5-D24.
PAGE_12 = (
    tail(
        12,
        1,
        "D5.",
        C,
        "p12_d5_employee_self",
        routes=(SEC_D,),
        note="D5 prints the employee/self-employed/both field.",
    ),
    tail(12, 1, "D5.", P, "p12_d5_prompt", routes=(SEC_D,)),
    word(
        12,
        3,
        "SOMEONE ELSE",
        F,
        "p12_flow_d5_someone_else",
        routes=(SEC_D,),
        note="D5 answer label opening the employee-only block D6-D10.",
    ),
    word(
        12,
        3,
        "BOTH SOMEONE ELSE AND SELF",
        F,
        "p12_flow_d5_both",
        routes=(SEC_D,),
        note="D5 answer label opening the mixed employee/self block D11-D18.",
    ),
    word(
        12,
        6,
        "D6. Do you work for the",
        C,
        "p12_d6_government_level",
        routes=(D_EMPLOYEE,),
        note="D6 prints the federal/state/local government-level field.",
    ),
    word(
        12,
        6,
        "D6. Do you work for the",
        P,
        "p12_d6_prompt",
        routes=(D_EMPLOYEE,),
    ),
    word(
        12,
        6,
        "Dll . When you work for others, do",
        C,
        "p12_d11_government_level",
        routes=(D_BOTH,),
        note="D11 prints the government-level field for the employee side of "
        "a mixed employment arrangement.",
    ),
    word(
        12,
        6,
        "Dll . When you work for others, do",
        P,
        "p12_d11_prompt",
        routes=(D_BOTH,),
    ),
    word(
        12,
        6,
        "Dl9. Is your business",
        C,
        "p12_d19_incorporation",
        routes=(SEC_D,),
        note="D19 prints the incorporation field of the head's own business "
        "on the self-employed-only side of D5.",
    ),
    word(12, 6, "Dl9. Is your business", P, "p12_d19_prompt", routes=(SEC_D,)),
    word(12, 23, "GO TO DlO", F, "p12_flow_d7_no", routes=(D_EMPLOYEE,)),
    word(
        12,
        48,
        "Dl6. Is your own business in-",
        C,
        "p12_d16_incorporation",
        routes=(D_BOTH,),
        note="D16 prints the incorporation field of the head's own business "
        "on the mixed side of D5.",
    ),
    word(
        12,
        48,
        "Dl6. Is your own business in-",
        P,
        "p12_d16_prompt",
        routes=(D_BOTH,),
    ),
    word(12, 55, "GO TO 022", F, "p12_flow_d17_no", routes=(D_BOTH,)),
    word(12, 60, "(GO TO D22)", F, "p12_flow_d10_exit", routes=(D_EMPLOYEE,)),
    word(12, 60, "GO TO D22)", F, "p12_flow_d18_exit", 1, routes=(D_BOTH,)),
    word(
        12,
        60,
        "(TURN TO PAGE 7      D25)",
        F,
        "p12_flow_d21_exit",
        routes=(SEC_D,),
    ),
    line(
        12,
        66,
        C,
        "p12_d24_employer_tenure",
        routes=(SEC_D,),
        note="D24 prints the tenure-with-present-employer exposure field.",
    ),
    line(12, 66, P, "p12_d24_prompt", routes=(SEC_D,)),
)

# Page 14 - head tenure, start month, and previous-job items D25-D37.
PAGE_14 = (
    word(14, 9, "GO TO 028", F, "p14_flow_d26_no", routes=(SEC_D,)),
    word(14, 24, "GOTO 032", F, "p14_flow_d30_no", routes=(SEC_D,)),
    line(
        14,
        31,
        C,
        "p14_d32_position_tenure",
        routes=(SEC_D,),
        note="D32 prints the current-position tenure exposure field.",
    ),
    line(14, 31, P, "p14_d32_prompt", routes=(SEC_D,)),
    word(
        14,
        31,
        "present position",
        J,
        "p14_job_present_position",
        routes=(SEC_D,),
        note="D32 names the head's current job by its printed job noun.",
    ),
    word(
        14,
        33,
        "IF LESS THAN ONE YEAR",
        F,
        "p14_flow_d32_less_than_one_year",
        routes=(SEC_D,),
        note="D32 checkpoint label opening the short-tenure block D33-D37.",
    ),
    word(
        14,
        33,
        "IF ONE YEAR OR MORE",
        F,
        "p14_flow_d32_one_year_or_more",
        routes=(SEC_D,),
    ),
    word(
        14,
        33,
        "(TURN TO PAGE 8, D38)",
        F,
        "p14_flow_d32_long_tenure_exit",
        routes=(SEC_D,),
    ),
    line(
        14,
        36,
        C,
        "p14_d33_start_month",
        routes=(D_SHORT_TENURE,),
        parents=("p14_job_present_position",),
        parent_note="Parent job is the printed current-position noun on this "
        "screen.",
        note="D33 prints the start-month exposure field of the current job.",
    ),
    line(14, 36, P, "p14_d33_prompt", routes=(D_SHORT_TENURE,)),
    block(14, 37, 38, P, "p14_d34_prompt", routes=(D_SHORT_TENURE,)),
    word(
        14,
        41,
        "(TtJRN TO PAGE 8, D38)",
        F,
        "p14_flow_d34_no_previous_job",
        routes=(D_SHORT_TENURE,),
    ),
    block(14, 42, 43, P, "p14_d35_prompt", routes=(D_SHORT_TENURE,)),
    word(
        14, 45, "GO TD D37", F, "p14_flow_d35_worse", routes=(D_SHORT_TENURE,)
    ),
    line(14, 46, P, "p14_d36_prompt", routes=(D_SHORT_TENURE,)),
    line(14, 51, P, "p14_d37_prompt", routes=(D_SHORT_TENURE,)),
    word(
        14,
        55,
        "(TURN TO PAGE 8, 038)",
        F,
        "p14_flow_d37_exit",
        routes=(D_SHORT_TENURE,),
    ),
)

# Page 16 - head 1975 work-time exposure items D38-D50.
PAGE_16 = (
    line(
        16,
        1,
        C,
        "p16_d38_missed_other_sick",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 1, P, "p16_d38_prompt", routes=(SEC_D,)),
    word(16, 3, "(GO TO D41)", F, "p16_flow_d38_no", routes=(SEC_D,)),
    line(16, 6, P, "p16_d39_prompt", routes=(SEC_D,)),
    line(
        16,
        9,
        C,
        "p16_d40_missed_other_sick_amount",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 9, P, "p16_d40_prompt", routes=(SEC_D,)),
    line(
        16, 13, C, "p16_d41_missed_own_sick", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(16, 13, P, "p16_d41_prompt", routes=(SEC_D,)),
    word(16, 16, "(GO TO D43)", F, "p16_flow_d41_no", routes=(SEC_D,)),
    line(
        16,
        17,
        C,
        "p16_d42_missed_own_sick_amount",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 17, P, "p16_d42_prompt", routes=(SEC_D,)),
    line(
        16,
        20,
        C,
        "p16_d43_paid_vacation_weeks",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 20, P, "p16_d43_prompt", routes=(SEC_D,)),
    line(
        16, 22, C, "p16_d44_took_vacation", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(16, 22, P, "p16_d44_prompt", routes=(SEC_D,)),
    word(16, 25, "(GO TO D46)", F, "p16_flow_d44_no", routes=(SEC_D,)),
    line(
        16, 27, C, "p16_d45_vacation_amount", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(16, 27, P, "p16_d45_prompt", routes=(SEC_D,)),
    line(
        16, 30, C, "p16_d46_missed_strike", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(16, 30, P, "p16_d46_prompt", routes=(SEC_D,)),
    word(16, 32, "(GO TO D48)", F, "p16_flow_d46_no", routes=(SEC_D,)),
    line(
        16, 34, C, "p16_d47_strike_amount", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(16, 34, P, "p16_d47_prompt", routes=(SEC_D,)),
    line(
        16,
        37,
        C,
        "p16_d48_missed_unemployment",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 37, P, "p16_d48_prompt", routes=(SEC_D,)),
    word(
        16, 39, "(TURN TO PAGE 9, D51)", F, "p16_flow_d48_no", routes=(SEC_D,)
    ),
    line(
        16,
        41,
        C,
        "p16_d49_unemployment_amount",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(16, 41, P, "p16_d49_prompt", routes=(SEC_D,)),
    block(
        16,
        44,
        45,
        C,
        "p16_d50_unemployment_spells",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    block(16, 44, 45, P, "p16_d50_prompt", routes=(SEC_D,)),
)

# Page 18 - head work-time, pay-rate, and pension-coverage items D51-D63.
PAGE_18 = (
    line(
        18,
        1,
        C,
        "p18_d51_weeks_worked",
        routes=(SEC_D,),
        parents=("p18_job_main_job",),
        parent_note=_MAIN_JOB_PARENT,
        note="D51 prints the 1975 weeks-worked exposure field of the main "
        "job.",
    ),
    line(18, 1, P, "p18_d51_prompt", routes=(SEC_D,)),
    word(
        18,
        1,
        "main job",
        J,
        "p18_job_main_job",
        routes=(SEC_D,),
        note="D51 names the head's main job by its printed job noun.",
    ),
    line(
        18,
        4,
        C,
        "p18_d52_hours_per_week",
        routes=(SEC_D,),
        parents=("p18_job_main_job",),
        parent_note=_MAIN_JOB_PARENT,
        note="D52 prints the 1975 average weekly hours exposure field of the "
        "main job.",
    ),
    line(18, 4, P, "p18_d52_prompt", routes=(SEC_D,)),
    line(
        18,
        7,
        C,
        "p18_d53_overtime_excluded",
        routes=(SEC_D,),
        note=_WORKTIME_D,
    ),
    line(18, 7, P, "p18_d53_prompt", routes=(SEC_D,)),
    line(
        18, 11, C, "p18_d54_overtime_hours", routes=(SEC_D,), note=_WORKTIME_D
    ),
    line(18, 11, P, "p18_d54_prompt", routes=(SEC_D,)),
    line(
        18,
        17,
        C,
        "p18_d55_pay_reporting_unit",
        routes=(SEC_D,),
        note="D55 prints the salaried/hourly pay reporting-unit field.",
    ),
    line(18, 17, P, "p18_d55_prompt", routes=(SEC_D,)),
    word(
        18,
        19,
        "PAID BY HOUR",
        F,
        "p18_flow_d55_paid_by_hour",
        routes=(SEC_D,),
        note="D55 answer label opening the hourly-rate block D59-D60.",
    ),
    word(
        18,
        20,
        "D56 . How much is your salary?",
        M,
        "p18_d56_salary",
        routes=(SEC_D,),
        parents=("p18_job_main_job",),
        parent_note=_MAIN_JOB_PARENT,
        note="D56 prints the salary remuneration component of the main job.",
    ),
    word(
        18,
        20,
        "D56 . How much is your salary?",
        P,
        "p18_d56_prompt",
        routes=(SEC_D,),
    ),
    word(
        18,
        20,
        "D59 . What is your hourly",
        M,
        "p18_d59_regular_hourly_rate",
        routes=(D_PAID_HOURLY,),
        parents=("p18_job_main_job",),
        parent_note=_MAIN_JOB_PARENT,
        note="D59 prints the regular-time hourly wage-rate remuneration "
        "component.",
    ),
    word(
        18,
        20,
        "D59 . What is your hourly",
        P,
        "p18_d59_prompt",
        routes=(D_PAID_HOURLY,),
    ),
    word(18, 20, "061 . How is that?", P, "p18_d61_prompt", routes=(SEC_D,)),
    word(
        18,
        23,
        "D57 . If you were to work more",
        P,
        "p18_d57_prompt",
        routes=(SEC_D,),
    ),
    word(
        18,
        26,
        "D60 . What is your hourly",
        M,
        "p18_d60_overtime_hourly_rate",
        routes=(D_PAID_HOURLY,),
        parents=("p18_job_main_job",),
        parent_note=_MAIN_JOB_PARENT,
        note="D60 prints the overtime hourly wage-rate remuneration "
        "component.",
    ),
    word(
        18,
        26,
        "D60 . What is your hourly",
        P,
        "p18_d60_prompt",
        routes=(D_PAID_HOURLY,),
    ),
    word(18, 31, "D58 . About how much", P, "p18_d58_prompt", routes=(SEC_D,)),
    word(
        18, 36, "D62 . If you worked an", P, "p18_d62_prompt", routes=(SEC_D,)
    ),
    word(18, 47, "(GO TO D63)", F, "p18_flow_d58_exit", routes=(SEC_D,)),
    word(
        18,
        47,
        "GO TO D63)",
        F,
        "p18_flow_d60_exit",
        1,
        routes=(D_PAID_HOURLY,),
    ),
    word(18, 47, "GO TO D63)", F, "p18_flow_d62_exit", 2, routes=(SEC_D,)),
    block(
        18,
        50,
        51,
        C,
        "p18_d63_pension_coverage",
        routes=(SEC_D,),
        note="D63 prints the count of employee retirement or pension plans "
        "covering the head, including Social Security.",
    ),
    block(18, 50, 51, P, "p18_d63_prompt", routes=(SEC_D,)),
)

# Page 20 - head extra-job items D64-D75.
PAGE_20 = (
    tail(
        20,
        1,
        "D64.",
        P,
        "p20_d64_prompt",
        routes=(SEC_D,),
    ),
    word(
        20,
        1,
        "extra jobs",
        J,
        "p20_job_extra_jobs",
        routes=(SEC_D,),
        note="D64 names the head's extra jobs by their printed job noun.",
    ),
    word(20, 4, "(GO TO D70)", F, "p20_flow_d64_no", routes=(SEC_D,)),
    line(
        20,
        6,
        C,
        "p20_d65_extra_job_occupation",
        routes=(SEC_D,),
        parents=("p20_job_extra_jobs",),
        parent_note=_EXTRA_JOB_PARENT,
        note="D65 prints the extra-job occupation field.",
    ),
    line(20, 6, P, "p20_d65_prompt", routes=(SEC_D,)),
    line(20, 9, P, "p20_d66_prompt", routes=(SEC_D,)),
    line(
        20,
        12,
        M,
        "p20_d67_extra_job_hourly_pay",
        routes=(SEC_D,),
        parents=("p20_job_extra_jobs",),
        parent_note=_EXTRA_JOB_PARENT,
        note="D67 prints the per-hour pay remuneration component of the "
        "extra job.",
    ),
    line(20, 12, P, "p20_d67_prompt", routes=(SEC_D,)),
    line(
        20,
        14,
        C,
        "p20_d68_extra_job_weeks",
        routes=(SEC_D,),
        parents=("p20_job_extra_jobs",),
        parent_note=_EXTRA_JOB_PARENT,
        note="D68 prints the 1975 weeks-worked exposure field of the extra "
        "job.",
    ),
    line(20, 14, P, "p20_d68_prompt", routes=(SEC_D,)),
    line(
        20,
        17,
        C,
        "p20_d69_extra_job_hours",
        routes=(SEC_D,),
        parents=("p20_job_extra_jobs",),
        parent_note=_EXTRA_JOB_PARENT,
        note="D69 prints the average weekly hours exposure field of the "
        "extra job.",
    ),
    line(20, 17, P, "p20_d69_prompt", routes=(SEC_D,)),
    word(
        20,
        52,
        "(TURN TO PAGE 11, D76)",
        F,
        "p20_flow_d75_exit",
        routes=(SEC_D,),
    ),
)

# Page 26 - section E entry, job-search, and last-job items E1-E15.
PAGE_26 = (
    tail(
        26,
        1,
        "SECTION E:",
        F,
        "p26_flow_section_e",
        note="Printed section E header opening the job-search schedule "
        "selected at D1.",
    ),
    line(
        26,
        3,
        C,
        "p26_e1_sought_occupation",
        routes=(SEC_E,),
        parents=("p26_job_sought",),
        parent_note=_SOUGHT_JOB_PARENT,
        note="E1 prints the sought-job occupation field.",
    ),
    line(26, 3, P, "p26_e1_prompt", routes=(SEC_E,)),
    word(
        26,
        3,
        "job",
        J,
        "p26_job_sought",
        routes=(SEC_E,),
        note="E1 names the head's sought job by its printed job noun.",
    ),
    line(
        26,
        10,
        M,
        "p26_e3_expected_earnings",
        routes=(SEC_E,),
        parents=("p26_job_sought",),
        parent_note=_SOUGHT_JOB_PARENT,
        note="E3 prints the expected-earnings remuneration component of the "
        "sought job.",
    ),
    line(26, 10, P, "p26_e3_prompt", routes=(SEC_E,)),
    word(26, 14, "GO TO E7", F, "p26_flow_e5_no", routes=(SEC_E,)),
    word(26, 22, "GO TO E9", F, "p26_flow_e7_no", routes=(SEC_E,)),
    line(26, 31, P, "p26_e11_prompt", routes=(SEC_E,)),
    word(
        26,
        33,
        "TURN TO PAGE lS' E34",
        F,
        "p26_flow_e11_never_worked",
        routes=(SEC_E,),
    ),
    line(
        26,
        35,
        C,
        "p26_e12_last_job_occupation",
        routes=(SEC_E,),
        parents=("p26_job_last",),
        parent_note=_LAST_JOB_PARENT,
        note="E12 prints the last-job occupation field.",
    ),
    line(26, 35, P, "p26_e12_prompt", routes=(SEC_E,)),
    word(
        26,
        35,
        "last job",
        J,
        "p26_job_last",
        routes=(SEC_E,),
        note="E12 names the head's last job by its printed job noun.",
    ),
    line(
        26,
        38,
        C,
        "p26_e13_last_job_industry",
        routes=(SEC_E,),
        parents=("p26_job_last",),
        parent_note=_LAST_JOB_PARENT,
        note="E13 prints the last-job kind-of-business industry field.",
    ),
    line(26, 38, P, "p26_e13_prompt", routes=(SEC_E,)),
    block(26, 43, 44, P, "p26_e15_prompt", routes=(SEC_E,)),
)

# Page 28 - head 1975 work-time exposure items E16-E28.
PAGE_28 = (
    line(
        28,
        2,
        C,
        "p28_e16_last_worked",
        routes=(SEC_E,),
        note="E16 prints the last-worked exposure field.",
    ),
    line(28, 2, P, "p28_e16_prompt", routes=(SEC_E,)),
    word(
        28,
        4,
        "IF BEFORE 1975",
        F,
        "p28_flow_e16_before_1975",
        routes=(SEC_E,),
        note="E16 checkpoint label for a head who last worked before the "
        "1975 reference year.",
    ),
    word(
        28,
        4,
        "(TURN TO PAGE 15, E34)",
        F,
        "p28_flow_e16_before_1975_exit",
        routes=(SEC_E,),
    ),
    line(
        28, 10, C, "p28_e17_took_vacation", routes=(SEC_E,), note=_WORKTIME_E
    ),
    line(28, 10, P, "p28_e17_prompt", routes=(SEC_E,)),
    word(28, 12, "(GO       TO El9)", F, "p28_flow_e17_no", routes=(SEC_E,)),
    line(
        28, 15, C, "p28_e18_vacation_amount", routes=(SEC_E,), note=_WORKTIME_E
    ),
    line(28, 15, P, "p28_e18_prompt", routes=(SEC_E,)),
    line(
        28,
        17,
        C,
        "p28_e19_missed_other_sick",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    line(28, 17, P, "p28_e19_prompt", routes=(SEC_E,)),
    word(28, 19, "(GO TO E22)", F, "p28_flow_e19_no", routes=(SEC_E,)),
    line(28, 21, P, "p28_e20_prompt", routes=(SEC_E,)),
    line(
        28,
        24,
        C,
        "p28_e21_missed_other_sick_amount",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    line(28, 24, P, "p28_e21_prompt", routes=(SEC_E,)),
    line(
        28, 27, C, "p28_e22_missed_own_sick", routes=(SEC_E,), note=_WORKTIME_E
    ),
    line(28, 27, P, "p28_e22_prompt", routes=(SEC_E,)),
    word(28, 29, "(GO TO E24)", F, "p28_flow_e22_no", routes=(SEC_E,)),
    line(
        28,
        30,
        C,
        "p28_e23_missed_own_sick_amount",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    line(28, 30, P, "p28_e23_prompt", routes=(SEC_E,)),
    line(
        28, 36, C, "p28_e24_missed_strike", routes=(SEC_E,), note=_WORKTIME_E
    ),
    line(28, 36, P, "p28_e24_prompt", routes=(SEC_E,)),
    word(28, 38, "GO         TO E26)", F, "p28_flow_e24_no", routes=(SEC_E,)),
    line(
        28, 41, C, "p28_e25_strike_amount", routes=(SEC_E,), note=_WORKTIME_E
    ),
    line(28, 41, P, "p28_e25_prompt", routes=(SEC_E,)),
    line(
        28,
        43,
        C,
        "p28_e26_missed_unemployment",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    line(28, 43, P, "p28_e26_prompt", routes=(SEC_E,)),
    word(
        28, 45, "(TURN TO PAGE 15, E29)", F, "p28_flow_e26_no", routes=(SEC_E,)
    ),
    line(
        28,
        48,
        C,
        "p28_e27_unemployment_amount",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    line(28, 48, P, "p28_e27_prompt", routes=(SEC_E,)),
    block(
        28,
        50,
        51,
        C,
        "p28_e28_unemployment_spells",
        routes=(SEC_E,),
        note=_WORKTIME_E,
    ),
    block(28, 50, 51, P, "p28_e28_prompt", routes=(SEC_E,)),
)

# Page 30 - head work-time items E29-E30 and the section E exit.
PAGE_30 = (
    line(
        30,
        3,
        C,
        "p30_e29_weeks_worked",
        routes=(SEC_E,),
        note="E29 prints the 1975 weeks-worked exposure field of the last "
        "job.",
    ),
    line(30, 3, P, "p30_e29_prompt", routes=(SEC_E,)),
    line(
        30,
        6,
        C,
        "p30_e30_hours_per_week",
        routes=(SEC_E,),
        note="E30 prints the average weekly hours exposure field of the last "
        "job.",
    ),
    line(30, 6, P, "p30_e30_prompt", routes=(SEC_E,)),
    word(30, 12, "(GO TO E34)", F, "p30_flow_e31_none", routes=(SEC_E,)),
    word(
        30,
        37,
        "(TURN TO PAGE 19, Gl)",
        F,
        "p30_flow_e34_exit",
        routes=(SEC_E,),
    ),
)

# Page 32 - section F entry and out-of-labour-force work items F1-F12.
PAGE_32 = (
    tail(
        32,
        1,
        "SECTION F:",
        F,
        "p32_flow_section_f",
        note="Printed section F header opening the out-of-labour-force "
        "schedule selected at D1.",
    ),
    line(32, 3, P, "p32_f1_prompt", routes=(SEC_F,)),
    word(
        32,
        9,
        "TURN TO PAGE 17 , Fl5)",
        F,
        "p32_flow_f2_no",
        routes=(SEC_F,),
    ),
    word(
        32,
        11,
        "(TURN TO PAGE 17 , FlS)",
        F,
        "p32_flow_f3_exit",
        routes=(SEC_F,),
    ),
    line(
        32,
        15,
        C,
        "p32_f4_occupation",
        routes=(SEC_F,),
        note="F4 prints the occupation field of the work done during 1975.",
    ),
    line(32, 15, P, "p32_f4_prompt", routes=(SEC_F,)),
    line(
        32,
        18,
        C,
        "p32_f5_industry",
        routes=(SEC_F,),
        note="F5 prints the kind-of-business industry field.",
    ),
    line(32, 18, P, "p32_f5_prompt", routes=(SEC_F,)),
    line(
        32,
        19,
        C,
        "p32_f6_weeks_worked",
        routes=(SEC_F,),
        note="F6 prints the 1975 weeks-worked exposure field.",
    ),
    line(32, 19, P, "p32_f6_prompt", routes=(SEC_F,)),
    line(
        32,
        21,
        C,
        "p32_f7_hours_per_week",
        routes=(SEC_F,),
        note="F7 prints the average weekly hours exposure field.",
    ),
    line(32, 21, P, "p32_f7_prompt", routes=(SEC_F,)),
    word(32, 28, "(GO TO Fll)", F, "p32_flow_f8_none", routes=(SEC_F,)),
    block(32, 47, 48, P, "p32_f11_prompt", routes=(SEC_F,)),
    word(
        32,
        53,
        "Fl2. Why are you no longer working?",
        P,
        "p32_f12_prompt",
        routes=(SEC_F,),
    ),
)

# Page 34 - the F15 checkpoint and head sought-job items F18-F19.
PAGE_34 = (
    word(
        34,
        11,
        '1. "YES " TO THINKING',
        F,
        "p34_flow_f15_yes_thinking",
        routes=(SEC_F,),
        note="F15 checkpoint label opening the sought-job block F16-F23.",
    ),
    word(
        34,
        11,
        '5. "NO" TO THINKING',
        F,
        "p34_flow_f15_no_thinking",
        routes=(SEC_F,),
    ),
    word(34, 21, "(GO TO Fl8)", F, "p34_flow_f16_no", routes=(F_WANTS_JOB,)),
    word(
        34,
        24,
        "(TURN TO PAGE 19, Gl)",
        F,
        "p34_flow_f24_no",
        routes=(SEC_F,),
    ),
    line(
        34,
        33,
        C,
        "p34_f18_sought_occupation",
        routes=(F_WANTS_JOB,),
        parents=("p34_job_sought",),
        parent_note=_SOUGHT_JOB_PARENT,
        note="F18 prints the sought-job occupation field.",
    ),
    line(34, 33, P, "p34_f18_prompt", routes=(F_WANTS_JOB,)),
    word(
        34,
        33,
        "job",
        J,
        "p34_job_sought",
        routes=(F_WANTS_JOB,),
        note="F18 names the head's sought job by its printed job noun.",
    ),
    word(
        34,
        37,
        "Fl9. How much would you expect to earn?",
        M,
        "p34_f19_expected_earnings",
        routes=(F_WANTS_JOB,),
        parents=("p34_job_sought",),
        parent_note=_SOUGHT_JOB_PARENT,
        note="F19 prints the expected-earnings remuneration component of the "
        "sought job.",
    ),
    word(
        34,
        37,
        "Fl9. How much would you expect to earn?",
        P,
        "p34_f19_prompt",
        routes=(F_WANTS_JOB,),
    ),
    word(
        34,
        60,
        "(TURN TO PAGE 19__. Gl)",
        F,
        "p34_flow_f21_exit",
        routes=(F_WANTS_JOB,),
    ),
    word(
        34,
        65,
        "TURN TO PAGE 18 , F28)",
        F,
        "p34_flow_f23_exit",
        routes=(SEC_F,),
    ),
)

# Page 38 - section G entry and wife employment items G1-G6.
PAGE_38 = (
    tail(
        38,
        2,
        "SECTION G:",
        F,
        "p38_flow_section_g",
        note="Printed section G header opening the wife work schedule.",
    ),
    word(38, 2, "WIFE'S", R, "p38_role_wife_header", routes=(SEC_G,)),
    line(38, 7, P, "p38_g1_prompt", routes=(SEC_G,)),
    word(38, 15, "WIFE'S", R, "p38_role_wife_g2_g6", routes=(SEC_G,)),
    line(38, 17, P, "p38_g2_prompt", routes=(SEC_G,)),
    word(38, 17, "wife", R, "p38_role_wife_g2", routes=(SEC_G,)),
    word(38, 19, "TURN TO PAGE 20, G7)", F, "p38_flow_g2_no", routes=(SEC_G,)),
    line(
        38,
        23,
        C,
        "p38_g3_occupation",
        routes=(SEC_G,),
        note="G3 prints the wife's occupation field.",
    ),
    line(38, 23, P, "p38_g3_prompt", routes=(SEC_G,)),
    line(
        38,
        28,
        C,
        "p38_g4_industry",
        routes=(SEC_G,),
        note="G4 prints the wife's kind-of-business industry field.",
    ),
    line(38, 28, P, "p38_g4_prompt", routes=(SEC_G,)),
    line(
        38,
        33,
        C,
        "p38_g5_weeks_worked",
        routes=(SEC_G,),
        note="G5 prints the wife's 1975 weeks-worked exposure field.",
    ),
    line(38, 33, P, "p38_g5_prompt", routes=(SEC_G,)),
    line(
        38,
        35,
        C,
        "p38_g6_hours_per_week",
        routes=(SEC_G,),
        note="G6 prints the wife's average weekly hours exposure field.",
    ),
    line(38, 35, P, "p38_g6_prompt", routes=(SEC_G,)),
)

# Page 44 - section H entry and family work-income items H1-H8.
PAGE_44 = (
    line(
        44,
        1,
        F,
        "p44_flow_section_h",
        note="Printed section H header opening the family income schedule.",
    ),
    word(
        44,
        11,
        "1. FARMER, OR RANCHER",
        F,
        "p44_flow_h1_farmer",
        routes=(SEC_H,),
        note="H1 checkpoint label opening the farm-aggregate block H2-H4.",
    ),
    word(
        44,
        11,
        "5. NOT A FARMER OR RANCHER",
        F,
        "p44_flow_h1_not_farmer",
        routes=(SEC_H,),
    ),
    word(
        44, 11, "(GO TO H5)", F, "p44_flow_h1_not_farmer_exit", routes=(SEC_H,)
    ),
    block(
        44,
        14,
        15,
        M,
        "p44_h2_farm_receipts",
        routes=(H_FARMER,),
        parents=("p44_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="H2 prints the total-farm-receipts remuneration component.",
    ),
    block(44, 14, 15, P, "p44_h2_prompt", routes=(H_FARMER,)),
    block(
        44,
        17,
        18,
        M,
        "p44_h3_farm_expenses",
        routes=(H_FARMER,),
        parents=("p44_fa_net_farm_income",),
        parent_note=_FARM_PARENT,
        note="H3 prints the farm operating-expense remuneration component.",
    ),
    block(44, 17, 18, P, "p44_h3_prompt", routes=(H_FARMER,)),
    word(
        44,
        20,
        "net income from farming",
        FA,
        "p44_fa_net_farm_income",
        routes=(H_FARMER,),
        note="H4 prints the farm aggregate by its printed net-farm-income "
        "label.",
    ),
    line(44, 20, P, "p44_h4_prompt", routes=(H_FARMER,)),
    line(44, 23, P, "p44_h5_prompt", routes=(SEC_H,)),
    block(
        44,
        31,
        32,
        C,
        "p44_h6_incorporation",
        routes=(SEC_H,),
        parents=("p44_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="H6 prints the business incorporation field.",
    ),
    block(44, 31, 32, P, "p44_h6_prompt", routes=(SEC_H,)),
    word(
        44,
        31,
        "unincorporated business",
        BA,
        "p44_ba_unincorporated_business",
        routes=(SEC_H,),
        note="H6 prints the business aggregate by its printed label.",
    ),
    word(
        44,
        34,
        "1. CORPORATION",
        F,
        "p44_flow_h6_corporation",
        routes=(SEC_H,),
    ),
    word(
        44,
        34,
        "GO TO H8",
        F,
        "p44_flow_h6_corporation_exit",
        routes=(SEC_H,),
    ),
    word(
        44,
        35,
        "2. UNINCORPORATED",
        F,
        "p44_flow_h6_unincorporated",
        routes=(SEC_H,),
        note="H6 answer label opening the business-share item H7.",
    ),
    word(
        44,
        36,
        "3. BOTH",
        F,
        "p44_flow_h6_both",
        routes=(SEC_H,),
        note="H6 answer label opening the business-share item H7 for a "
        "family holding both kinds of interest.",
    ),
    block(
        44,
        39,
        41,
        M,
        "p44_h7_business_share",
        routes=(H_UNINCORPORATED, H_BOTH_KINDS),
        parents=("p44_ba_unincorporated_business",),
        parent_note=_BUSINESS_PARENT,
        note="H7 prints the family business-income share remuneration "
        "component; the printed H6 routing sends only the two "
        "non-corporation answers here, so both are applicable paths.",
    ),
    block(
        44,
        39,
        41,
        P,
        "p44_h7_prompt",
        routes=(H_UNINCORPORATED, H_BOTH_KINDS),
    ),
    block(
        44,
        47,
        48,
        M,
        "p44_h8_wages_and_salaries",
        routes=(SEC_H,),
        note="H8 prints the head's 1975 wages-and-salaries remuneration "
        "component.",
    ),
    block(44, 47, 48, P, "p44_h8_prompt", routes=(SEC_H,)),
    word(44, 47, "HEAD", R, "p44_role_head_h8", routes=(SEC_H,)),
)

# Page 47 - head other-income items H9-H13.
PAGE_47 = (
    block(
        47,
        2,
        3,
        M,
        "p47_h9_bonuses_overtime_commissions",
        routes=(SEC_H,),
        note="H9 prints the bonus, overtime, and commission remuneration "
        "component.",
    ),
    block(47, 2, 3, P, "p47_h9_prompt", routes=(SEC_H,)),
    word(47, 5, "GO        TO Hll)", F, "p47_flow_h9_no", routes=(SEC_H,)),
    line(47, 8, P, "p47_h10_prompt", routes=(SEC_H,)),
    line(47, 11, P, "p47_h11_prompt", routes=(SEC_H,)),
    word(47, 11, "HEAD", R, "p47_role_head_h11", routes=(SEC_H,)),
    word(
        47,
        13,
        "a) professional practice or trade?",
        M,
        "p47_h11a_professional_practice",
        routes=(SEC_H,),
        note="H11a prints the professional-practice-or-trade remuneration "
        "component.",
    ),
    word(
        47,
        14,
        "b) farming or market gardening,",
        M,
        "p47_h11b_farming_gardening",
        routes=(SEC_H,),
        note="H11b prints the farming-or-market-gardening remuneration "
        "component.",
    ),
    word(
        47,
        15,
        "roomers or boarders?",
        M,
        "p47_h11b_roomers_boarders",
        routes=(SEC_H,),
        note="The same H11b row prints a second remuneration component, "
        "roomers or boarders, on its continuation line.",
    ),
    word(
        47,
        44,
        "TURN TO PAGE 25, Hl4)",
        F,
        "p47_flow_h12_no",
        routes=(SEC_H,),
    ),
)

# Page 52 - welfare and Social Security checkpoints and wife income H22-H25.
PAGE_52 = (
    word(
        52, 3, "GO TO Hl7)", F, "p52_flow_h14_no_such_income", routes=(SEC_H,)
    ),
    word(52, 11, "(GO TO Hl7)", F, "p52_flow_h15_no", routes=(SEC_H,)),
    word(52, 18, "(GO TO Hl7)", F, "p52_flow_h16_exit", routes=(SEC_H,)),
    word(
        52,
        21,
        "(GO TO H22)",
        F,
        "p52_flow_h17_no_such_income",
        routes=(SEC_H,),
    ),
    word(52, 25, "(GO TO H20)", F, "p52_flow_h18_no", routes=(SEC_H,)),
    word(52, 39, "(GO TO H22", F, "p52_flow_h21_exit", routes=(SEC_H,)),
    line(52, 40, P, "p52_h22_prompt", routes=(SEC_H,)),
    word(52, 40, "HEAD", R, "p52_role_head_h22", routes=(SEC_H,)),
    word(52, 40, "WIFE", R, "p52_role_wife_h22", routes=(SEC_H,)),
    word(
        52,
        42,
        "NO WIFE IN FU OR FU HAS FEMALE HEAD",
        F,
        "p52_flow_h22_no_wife",
        routes=(SEC_H,),
        note="H22 checkpoint label for a family unit with no wife in it.",
    ),
    line(
        52,
        44,
        T,
        "p52_h23_wife_total_income",
        routes=(SEC_H,),
        note="H23 prints the wife's 1975 total-income role total.",
    ),
    line(52, 44, P, "p52_h23_prompt", routes=(SEC_H,)),
    word(52, 44, "wife", R, "p52_role_wife_h23", routes=(SEC_H,)),
    word(
        52,
        46,
        "(TURN TO PAGE 26, H26)",
        F,
        "p52_flow_h23_no",
        routes=(SEC_H,),
    ),
    line(52, 48, P, "p52_h24_prompt", routes=(SEC_H,)),
    line(
        52,
        53,
        M,
        "p52_h25_wife_income_amount",
        routes=(SEC_H,),
        note="H25 prints the before-deductions amount of the wife's income "
        "from the H24 source as a remuneration component.",
    ),
    line(52, 53, P, "p52_h25_prompt", routes=(SEC_H,)),
)

# Page 60 - section J entry and head lifetime work-history items J1-J8.
PAGE_60 = (
    line(
        60,
        2,
        F,
        "p60_flow_section_j",
        note="Printed section J header opening the head work-history "
        "schedule.",
    ),
    line(
        60,
        4,
        C,
        "p60_j1_years_worked",
        routes=(SEC_J,),
        note="J1 prints the lifetime years-worked-since-18 exposure field.",
    ),
    line(60, 4, P, "p60_j1_prompt", routes=(SEC_J,)),
    word(60, 4, "HEAD", R, "p60_role_head_j1", routes=(SEC_J,)),
    word(
        60,
        5,
        "(TURN TO PAGE 31, Kl)",
        F,
        "p60_flow_j1_never_worked",
        routes=(SEC_J,),
    ),
    line(
        60,
        7,
        C,
        "p60_j2_years_full_time",
        routes=(SEC_J,),
        note="J2 prints the lifetime full-time years exposure field.",
    ),
    line(60, 7, P, "p60_j2_prompt", routes=(SEC_J,)),
    block(
        60,
        13,
        14,
        C,
        "p60_j3_part_time_share",
        routes=(SEC_J,),
        note="J3 prints the part-time work-share exposure field.",
    ),
    block(60, 13, 14, P, "p60_j3_prompt", routes=(SEC_J,)),
    line(60, 17, P, "p60_j4_prompt", routes=(SEC_J,)),
    word(
        60,
        25,
        "(TURN TO PAGE 31, Kl)",
        F,
        "p60_flow_j4_no_interruption",
        routes=(SEC_J,),
    ),
    block(60, 29, 30, P, "p60_j5_prompt", routes=(SEC_J,)),
    word(
        60,
        32,
        "1. ONE PERIOD",
        F,
        "p60_flow_j5_one_period",
        routes=(SEC_J,),
        note="J5 answer label opening the single-interruption item J6.",
    ),
    word(
        60,
        32,
        "2. SEVERAL PERIODS",
        F,
        "p60_flow_j5_several_periods",
        routes=(SEC_J,),
        note="J5 answer label opening the most-recent-interruption item J7.",
    ),
    word(
        60,
        35,
        "J6. When was the period you",
        C,
        "p60_j6_interruption_dates",
        routes=(J_ONE_PERIOD,),
        note="J6 prints the month-and-year exposure field of the single "
        "not-working period.",
    ),
    word(
        60,
        35,
        "J6. When was the period you",
        P,
        "p60_j6_prompt",
        routes=(J_ONE_PERIOD,),
    ),
    word(
        60,
        35,
        "J7. What was the most recent period",
        C,
        "p60_j7_interruption_dates",
        routes=(J_SEVERAL_PERIODS,),
        note="J7 prints the month-and-year exposure field of the most recent "
        "not-working period.",
    ),
    word(
        60,
        35,
        "J7. What was the most recent period",
        P,
        "p60_j7_prompt",
        routes=(J_SEVERAL_PERIODS,),
    ),
    word(
        60,
        42,
        "IF BEFORE 1955, TURN TO PAGE 31, Kl",
        F,
        "p60_flow_j6_j7_before_1955",
        routes=(SEC_J,),
    ),
    line(60, 43, P, "p60_j8_prompt", routes=(SEC_J,)),
)

# Page 62 - head return-to-work items J10-J15.
PAGE_62 = (
    line(62, 5, P, "p62_j10_prompt", routes=(SEC_J,)),
    line(
        62,
        10,
        C,
        "p62_j11_same_kind_of_work",
        routes=(SEC_J,),
        note="J11 prints the occupation-continuity field of the job resumed "
        "after the interruption.",
    ),
    line(62, 10, P, "p62_j11_prompt", routes=(SEC_J,)),
    word(
        62,
        15,
        "Jl2 .   Was it the same job?",
        C,
        "p62_j12_same_job",
        routes=(SEC_J,),
        note="J12 prints the job-identifier field of the job resumed after "
        "the interruption.",
    ),
    word(
        62,
        15,
        "Jl2 .   Was it the same job?",
        P,
        "p62_j12_prompt",
        routes=(SEC_J,),
    ),
    line(
        62,
        34,
        M,
        "p62_j15_earnings_on_return",
        routes=(SEC_J,),
        note="J15 prints the earnings remuneration component of the job "
        "resumed after the interruption.",
    ),
    line(62, 34, P, "p62_j15_prompt", routes=(SEC_J,)),
)

# Page 64 - section K entry and new-head first-job items K1-K5.
PAGE_64 = (
    line(
        64,
        2,
        F,
        "p64_flow_section_k",
        note="Printed section K header opening the new-head schedule.",
    ),
    word(
        64,
        6,
        "1. FU HAS A NEW HEAD THIS YEAR",
        F,
        "p64_flow_k1_new_head",
        routes=(SEC_K,),
        note="K1 checkpoint label predicating the section on a new head.",
    ),
    word(
        64,
        6,
        "5. THIS FU HAS THE SAME HEAD AS IN 1975",
        F,
        "p64_flow_k1_same_head",
        routes=(SEC_K,),
    ),
    word(
        64,
        7,
        "(TURN TO PAGE 34. Ll)",
        F,
        "p64_flow_k1_same_head_exit",
        routes=(SEC_K,),
    ),
    line(
        64,
        23,
        C,
        "p64_k4_first_job_occupation",
        routes=(K_NEW_HEAD,),
        parents=("p64_job_first_full_time",),
        parent_note="Parent job is the printed first-job noun on this "
        "screen.",
        note="K4 prints the first-full-time-regular-job occupation field.",
    ),
    line(64, 23, P, "p64_k4_prompt", routes=(K_NEW_HEAD,)),
    word(64, 23, "HEAD'S", R, "p64_role_head_k4", routes=(K_NEW_HEAD,)),
    word(
        64,
        23,
        "first full time regular job",
        J,
        "p64_job_first_full_time",
        routes=(K_NEW_HEAD,),
        note="K4 names the head's first full-time regular job by its printed "
        "job noun.",
    ),
    word(
        64,
        25,
        "(GO TO K6)",
        F,
        "p64_flow_k4_never_worked",
        routes=(K_NEW_HEAD,),
    ),
    block(
        64,
        27,
        28,
        C,
        "p64_k5_occupation_count",
        routes=(K_NEW_HEAD,),
        note="K5 prints the number-of-occupations work-history field.",
    ),
    block(64, 27, 28, P, "p64_k5_prompt", routes=(K_NEW_HEAD,)),
    word(64, 35, "(GO TO K9)", F, "p64_flow_k6_no", routes=(K_NEW_HEAD,)),
    word(
        64,
        49,
        "(TURN TO PAGE 32, Kll)",
        F,
        "p64_flow_k9_no",
        routes=(K_NEW_HEAD,),
    ),
)

# Page 84 - wife employment item B9 and the child-care block's routing atoms.
PAGE_84 = (
    line(
        84,
        2,
        C,
        "p84_b9_assignment",
        routes=((),),
        parents=("p84_job_current",),
        parent_note="Parent job is the printed job noun on this screen.",
        note="B9 prints the wife's current-employment assignment field; the "
        "printed section B header governs housework items that retain no "
        "field, so this item is administered unconditionally.",
    ),
    line(84, 2, P, "p84_b9_prompt", routes=((),)),
    word(
        84,
        2,
        "a job",
        J,
        "p84_job_current",
        routes=((),),
        note="B9 names the wife's current job by its printed job noun.",
    ),
    word(84, 4, "TURN TO PAGE 6, B20", F, "p84_flow_b9_no", routes=((),)),
    word(84, 31, "(GO TO Bl8)", F, "p84_flow_b13_other", routes=((),)),
    word(84, 40, "(GO TO Bl8)", F, "p84_flow_b14_exit", routes=((),)),
    word(84, 41, "(GO TO Bl8)", F, "p84_flow_b17_exit", routes=((),)),
    word(84, 46, "(GO TO Bl8)", F, "p84_flow_b16_exit", routes=((),)),
    word(
        84, 65, "(TUR}T TO PAGE 7, Cl)", F, "p84_flow_b18_exit", routes=((),)
    ),
    word(
        84,
        74,
        "(TURN TO PAGE 7            Cl)",
        F,
        "p84_flow_b19_exit",
        routes=((),),
    ),
)

_WIFE_HISTORY = (
    "Prints a lifetime work-participation exposure field for the wife."
)

# Page 88 - section C entry and wife lifetime work-participation items C5-C14.
PAGE_88 = (
    line(
        88,
        3,
        F,
        "p88_flow_section_c_wives",
        note="Printed wives section C header opening the child and lifetime "
        "work-participation schedule.",
    ),
    word(
        88,
        13,
        "Cll . Before you were first married , did",
        C,
        "p88_c11_premarital_work",
        routes=(SEC_CW,),
        parents=("p88_job_c11_premarital",),
        parent_note="Parent job is the printed job noun in the same printed "
        "question.",
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        13,
        "Cll . Before you were first married , did",
        P,
        "p88_c11_prompt",
        routes=(SEC_CW,),
    ),
    word(
        88,
        14,
        "a job working for money?",
        J,
        "p88_job_c11_premarital",
        routes=(SEC_CW,),
        note="C11 names the wife's pre-marital job by its printed job noun.",
    ),
    word(
        88,
        17,
        "Cl2. Did you normally work full-time",
        C,
        "p88_c12_premarital_full_time",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        17,
        "Cl2. Did you normally work full-time",
        P,
        "p88_c12_prompt",
        routes=(SEC_CW,),
    ),
    word(
        88,
        25,
        "Cl3. Did you work for money during the",
        C,
        "p88_c13_early_marriage_work",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        25,
        "Cl3. Did you work for money during the",
        P,
        "p88_c13_prompt",
        routes=(SEC_CW,),
    ),
    block(
        88,
        27,
        28,
        C,
        "p88_c5_premarital_work",
        routes=(SEC_CW,),
        parents=("p88_job_c5_premarital",),
        parent_note="Parent job is the printed job noun in the same printed "
        "question.",
        note=_WIFE_HISTORY,
    ),
    block(88, 27, 28, P, "p88_c5_prompt", routes=(SEC_CW,)),
    word(
        88,
        28,
        "a job working for money?",
        J,
        "p88_job_c5_premarital",
        routes=(SEC_CW,),
        note="C5 names the wife's pre-marital job by its printed job noun on "
        "the child-bearing side of the C1 checkpoint.",
    ),
    word(
        88,
        35,
        "Cl4. Did you normally work full-time",
        C,
        "p88_c14_early_marriage_full_time",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        35,
        "Cl4. Did you normally work full-time",
        P,
        "p88_c14_prompt",
        routes=(SEC_CW,),
    ),
    word(
        88,
        36,
        "C6 . Did you normally work full-time",
        C,
        "p88_c6_premarital_full_time",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        36,
        "C6 . Did you normally work full-time",
        P,
        "p88_c6_prompt",
        routes=(SEC_CW,),
    ),
    block(
        88,
        44,
        45,
        C,
        "p88_c7_early_marriage_work",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    block(88, 44, 45, P, "p88_c7_prompt", routes=(SEC_CW,)),
    block(
        88,
        48,
        49,
        C,
        "p88_c8_early_marriage_full_time",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    block(88, 48, 49, P, "p88_c8_prompt", routes=(SEC_CW,)),
    word(
        88,
        54,
        "C9 . Did you ever work for money when you",
        C,
        "p88_c9_preschool_work",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    word(
        88,
        54,
        "C9 . Did you ever work for money when you",
        P,
        "p88_c9_prompt",
        routes=(SEC_CW,),
    ),
    word(
        88,
        54,
        "(TURN TO PAGE 8, Cl5)",
        F,
        "p88_flow_c14_exit",
        routes=(SEC_CW,),
    ),
    block(
        88,
        58,
        59,
        C,
        "p88_c10_preschool_full_time",
        routes=(SEC_CW,),
        note=_WIFE_HISTORY,
    ),
    block(88, 58, 59, P, "p88_c10_prompt", routes=(SEC_CW,)),
    word(
        88,
        61,
        "(TIDL~    TO PAGE 8, CIS)",
        F,
        "p88_flow_c10_exit",
        routes=(SEC_CW,),
    ),
)

# Page 96 - wives section G entry and lifetime work-history items G1-G10.
PAGE_96 = (
    line(
        96,
        2,
        F,
        "p96_flow_section_g_wives",
        note="Printed wives section G header opening the wife work-history "
        "schedule.",
    ),
    line(
        96,
        4,
        C,
        "p96_g1_years_worked",
        routes=(SEC_GW,),
        note="G1 prints the lifetime years-worked-since-18 exposure field.",
    ),
    line(96, 4, P, "p96_g1_prompt", routes=(SEC_GW,)),
    word(
        96,
        5,
        "TURN TO PAGE 26' Hl",
        F,
        "p96_flow_g1_never_worked",
        routes=(SEC_GW,),
    ),
    line(
        96,
        6,
        C,
        "p96_g2_years_full_time",
        routes=(SEC_GW,),
        note="G2 prints the lifetime full-time years exposure field.",
    ),
    line(96, 6, P, "p96_g2_prompt", routes=(SEC_GW,)),
    word(96, 8, "GO TO G4", F, "p96_flow_g2_all", routes=(SEC_GW,)),
    block(
        96,
        10,
        11,
        C,
        "p96_g3_part_time_share",
        routes=(SEC_GW,),
        note="G3 prints the part-time work-share exposure field.",
    ),
    block(96, 10, 11, P, "p96_g3_prompt", routes=(SEC_GW,)),
    line(
        96,
        15,
        C,
        "p96_g4_first_job_occupation",
        routes=(SEC_GW,),
        parents=("p96_job_first_full_time",),
        parent_note="Parent job is the printed first-job noun on this "
        "screen.",
        note="G4 prints the first-full-time-regular-job occupation field.",
    ),
    line(96, 15, P, "p96_g4_prompt", routes=(SEC_GW,)),
    word(
        96,
        15,
        "first full time, regular job",
        J,
        "p96_job_first_full_time",
        routes=(SEC_GW,),
        note="G4 names the wife's first full-time regular job by its printed "
        "job noun.",
    ),
    block(
        96,
        17,
        18,
        C,
        "p96_g5_occupation_count",
        routes=(SEC_GW,),
        note="G5 prints the number-of-occupations work-history field.",
    ),
    block(96, 17, 18, P, "p96_g5_prompt", routes=(SEC_GW,)),
    block(96, 23, 25, P, "p96_g6_prompt", routes=(SEC_GW,)),
    word(
        96,
        27,
        "TURN TO PAGE 26, Hl",
        F,
        "p96_flow_g6_no_interruption",
        routes=(SEC_GW,),
    ),
    block(96, 31, 32, P, "p96_g7_prompt", routes=(SEC_GW,)),
    word(
        96,
        34,
        "ONE PERIOD",
        F,
        "p96_flow_g7_one_period",
        routes=(SEC_GW,),
        note="G7 answer label opening the single-interruption item G8.",
    ),
    word(
        96,
        34,
        "SEVERAL PERIODS",
        F,
        "p96_flow_g7_several_periods",
        routes=(SEC_GW,),
        note="G7 answer label opening the most-recent-interruption item G9.",
    ),
    word(
        96,
        35,
        "G8. When was the period you were",
        C,
        "p96_g8_interruption_dates",
        routes=(GW_ONE_PERIOD,),
        note="G8 prints the month-and-year exposure field of the single "
        "not-working period.",
    ),
    word(
        96,
        35,
        "G8. When was the period you were",
        P,
        "p96_g8_prompt",
        routes=(GW_ONE_PERIOD,),
    ),
    word(
        96,
        35,
        "G9. When was the most recent",
        C,
        "p96_g9_interruption_dates",
        routes=(GW_SEVERAL_PERIODS,),
        note="G9 prints the month-and-year exposure field of the most recent "
        "not-working period.",
    ),
    word(
        96,
        35,
        "G9. When was the most recent",
        P,
        "p96_g9_prompt",
        routes=(GW_SEVERAL_PERIODS,),
    ),
    word(
        96,
        43,
        "IF BEFORE 1955, TURN TO PAGE 26, Hl",
        F,
        "p96_flow_g8_g9_before_1955",
        routes=(SEC_GW,),
    ),
    line(96, 45, P, "p96_g10_prompt", routes=(SEC_GW,)),
)

# Page 98 - wife return-to-work items G12-G17.
PAGE_98 = (
    line(98, 2, P, "p98_g12_prompt", routes=(SEC_GW,)),
    line(
        98,
        7,
        C,
        "p98_g13_same_kind_of_work",
        routes=(SEC_GW,),
        note="G13 prints the occupation-continuity field of the job resumed "
        "after the interruption.",
    ),
    line(98, 7, P, "p98_g13_prompt", routes=(SEC_GW,)),
    word(
        98,
        13,
        "Gl4. Was it the same job?",
        C,
        "p98_g14_same_job",
        routes=(SEC_GW,),
        note="G14 prints the job-identifier field of the job resumed after "
        "the interruption.",
    ),
    word(
        98,
        13,
        "Gl4. Was it the same job?",
        P,
        "p98_g14_prompt",
        routes=(SEC_GW,),
    ),
    line(
        98,
        29,
        M,
        "p98_g17_earnings_on_return",
        routes=(SEC_GW,),
        note="G17 prints the earnings remuneration component of the job "
        "resumed after the interruption.",
    ),
    line(98, 29, P, "p98_g17_prompt", routes=(SEC_GW,)),
)


def _xref(
    page: int,
    selector: tuple[Any, ...],
    key: str,
    alias: Sequence[str],
    canonical: Sequence[str],
    note: str,
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


# Printed cross-reference instructions.  Each names printed items inside the
# retained R_Q domain; both endpoints are retained anchors except on page 94,
# whose target instrument screens this manual never prints.
CROSS_REFERENCES = (
    _xref(
        21,
        ("line", 19),
        "p21_xref_d65_d66_to_d2_d3",
        ("p20_d65_extra_job_occupation",),
        ("p9_d2_occupation",),
        "The D65-D66 objective binds the extra-job occupation field to the "
        "D2 main-occupation field.",
    ),
    _xref(
        27,
        ("needle", 11, "See the objectives for D2, D3;   they apply", 0),
        "p27_xref_e1_to_d2_d3",
        ("p26_e1_sought_occupation",),
        ("p9_d2_occupation",),
        "The E1 objective binds the sought-job occupation field to the D2 "
        "main-occupation field.",
    ),
    _xref(
        27,
        ("line", 36),
        "p27_xref_e12_to_d2_d3",
        ("p26_e12_last_job_occupation",),
        ("p9_d2_occupation",),
        "The E12 objective binds the last-job occupation field to the D2 "
        "main-occupation field.",
    ),
    _xref(
        27,
        ("line", 39),
        "p27_xref_e13_to_d4",
        ("p26_e13_last_job_industry",),
        ("p9_d4_industry",),
        "The E13 objective binds the last-job industry field to the D4 "
        "industry field.",
    ),
    _xref(
        29,
        ("line", 5),
        "p29_xref_e17_e18_to_d44_d45",
        ("p28_e17_took_vacation", "p28_e18_vacation_amount"),
        ("p16_d44_took_vacation", "p16_d45_vacation_amount"),
        "The E17-E18 objective binds the section E vacation exposure fields "
        "to their section D counterparts.",
    ),
    _xref(
        29,
        ("line", 8),
        "p29_xref_e19_e23_to_d38_d42",
        (
            "p28_e19_missed_other_sick",
            "p28_e21_missed_other_sick_amount",
            "p28_e22_missed_own_sick",
            "p28_e23_missed_own_sick_amount",
        ),
        (
            "p16_d38_missed_other_sick",
            "p16_d40_missed_other_sick_amount",
            "p16_d41_missed_own_sick",
            "p16_d42_missed_own_sick_amount",
        ),
        "The printed objective binds the section E sick-time exposure fields "
        "to their section D counterparts; the printed range label reads "
        '"Dl9-23" in the source bytes and is preserved verbatim.',
    ),
    _xref(
        29,
        ("line", 11),
        "p29_xref_e26_e28_to_d48_d50",
        (
            "p28_e26_missed_unemployment",
            "p28_e27_unemployment_amount",
            "p28_e28_unemployment_spells",
        ),
        (
            "p16_d48_missed_unemployment",
            "p16_d49_unemployment_amount",
            "p16_d50_unemployment_spells",
        ),
        "The E26-E28 objective binds the section E unemployment exposure "
        "fields to their section D counterparts.",
    ),
    _xref(
        33,
        ("line", 19),
        "p33_xref_f4_to_d2_d3",
        ("p32_f4_occupation",),
        ("p9_d2_occupation",),
        "The F4 objective binds the section F occupation field to the D2 "
        "main-occupation field.",
    ),
    _xref(
        33,
        ("line", 22),
        "p33_xref_f5_to_d4",
        ("p32_f5_industry",),
        ("p9_d4_industry",),
        "The F5 objective binds the section F industry field to the D4 "
        "industry field.",
    ),
    _xref(
        39,
        ("line", 12),
        "p39_xref_g2_g4_to_d2_d4",
        ("p38_g3_occupation", "p38_g4_industry"),
        ("p9_d2_occupation", "p9_d4_industry"),
        "The G2-G4 objective binds the wife occupation and industry fields "
        "to the D2 and D4 head fields.",
    ),
    _xref(
        45,
        ("line", 7),
        "p45_xref_h11b_to_h4",
        ("p47_h11b_farming_gardening",),
        ("p44_fa_net_farm_income",),
        "The H1 objective routes a nonfarmer's farm income to H11b rather "
        "than to the H2-H4 farm aggregate.",
    ),
    _xref(
        46,
        ("line", 18),
        "p46_xref_h8_to_h7",
        ("p44_h8_wages_and_salaries",),
        ("p44_h7_business_share",),
        "The H8 objective warns that the H7 business share and the H8 "
        "wages-and-salaries component must not record the same figure twice.",
    ),
    _xref(
        49,
        ("block", 12, 16),
        "p49_xref_h11b_to_h2_h4",
        ("p47_h11b_farming_gardening",),
        ("p44_h2_farm_receipts", "p44_fa_net_farm_income"),
        "The H11b objective states that a primary farmer's income belongs in "
        "H2-H4 and must not be duplicated at H11b.",
    ),
    _xref(
        65,
        ("line", 26),
        "p65_xref_k4_to_d2_d3",
        ("p64_k4_first_job_occupation",),
        ("p9_d2_occupation",),
        "The K4 objective binds the new-head first-job occupation field to "
        "the D2 main-occupation field.",
    ),
    _xref(
        94,
        ("block", 14, 19),
        "p94_xref_wives_def_to_heads_pages_5_18",
        (),
        (),
        "The wives sections D, E, and F are administered from the heads "
        "question-by-question objectives on pages 5-18; this manual prints "
        "no wives instrument screen for them, so the alias target stays "
        "unresolved inside the document shard.",
        target_scope="unresolved",
        resolution_status="preserved_for_global_resolution",
    ),
    _xref(
        97,
        ("line", 17),
        "p97_xref_wives_g4_to_d2_d3",
        ("p96_g4_first_job_occupation",),
        ("p9_d2_occupation",),
        "The wives G4 objective binds the wife first-job occupation field to "
        "the D2 main-occupation field.",
    ),
)

REVIEW_ROWS: tuple[dict[str, Any], ...] = (
    *PAGE_9,
    *PAGE_12,
    *PAGE_14,
    *PAGE_16,
    *PAGE_18,
    *PAGE_20,
    *PAGE_26,
    *PAGE_28,
    *PAGE_30,
    *PAGE_32,
    *PAGE_34,
    *PAGE_38,
    *PAGE_44,
    *PAGE_47,
    *PAGE_52,
    *PAGE_60,
    *PAGE_62,
    *PAGE_64,
    *PAGE_84,
    *PAGE_88,
    *PAGE_96,
    *PAGE_98,
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
                    page_text, row["utf8_byte_start"], matched
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
                "all_101_pages_including_empty_occurrence_pages"
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
        f"document 17 source review: {len(review['occurrence_specs'])} "
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
